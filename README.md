# NZ Date Dimension

A parameterised Python generator that produces a correct, tested New Zealand
date dimension (calendar table) and emits it to **six formats** — the kind
of "done properly" date dimension every NZ data warehouse eventually needs,
built once and open-sourced instead of rebuilt badly by every team.

## Why this is "done properly"

Most home-grown NZ date dimensions get the easy 80% right and quietly get
the rest wrong. This one doesn't cut those corners:

- **Matariki**, New Zealand's newest public holiday, correctly present from
  its first observance in **2022** through to **2052** (the last year the
  date is currently gazetted) — and correctly *absent* before 2022.
- **Mondayisation** handled properly: when Waitangi Day or ANZAC Day falls
  on a weekend, the Monday "observed" holiday is flagged via `IsObserved`,
  and `IsBusinessDay` accounts for it.
- **NZ fiscal year**, 1 April – 31 March, labelled by the year it **ends**
  (`FY2026` = 1 Apr 2025 – 31 Mar 2026) — not the US/calendar convention.
- **17 regional public holiday flags** — one `IsHoliday_<CODE>` column per
  NZ subdivision, so "is this a public holiday in Auckland vs. Wellington"
  is a single boolean lookup, not a lookup table you have to build yourself.
- **Relative / time-intelligence columns** (`IsToday`, `IsCalendarYTD`,
  `IsRolling12Months`, offsets, ...) — always computed *live* against the
  query engine's clock in every dynamic format, never frozen into a stale
  static file. See [Relative columns](#relative--time-intelligence-columns)
  below.
- All holiday logic comes from [`python-holidays`](https://github.com/vacanza/holidays)
  (actively maintained, MIT licensed) rather than a hand-rolled and
  inevitably-stale holiday table.

## Download

Just want the data? Grab the ready-made **2015–2050** CSV directly — no Python required:

**⬇ [`outputs/nz-date-dimension.csv`](outputs/nz-date-dimension.csv)** — 13,149 rows, one per day.

Or generate a custom date range yourself with the quick start below.

## Quick start

Works the same on Windows (PowerShell/cmd) and bash/zsh — run from inside
`generator/`, writing back out to the repo-root `outputs/` folder:

```bash
pip install -r requirements.txt

cd generator
python -m nz_date_dimension.cli --out ../outputs/nz-date-dimension.csv
```

This writes the full 2015–2050 date dimension to
[`outputs/nz-date-dimension.csv`](outputs/nz-date-dimension.csv) — the same
ready-made file that's committed to this repo (see [Download](#download)).

Prefer running from the repo root instead? Point `PYTHONPATH` at the
`generator/` package for your shell:

| Shell | Command |
|---|---|
| bash / zsh | `PYTHONPATH=generator python -m nz_date_dimension.cli` |
| PowerShell | `$env:PYTHONPATH="generator"; python -m nz_date_dimension.cli` |
| cmd.exe | `set PYTHONPATH=generator && python -m nz_date_dimension.cli` |

CLI flags:

| Flag | Default | Description |
|---|---|---|
| `--start-year` | `2015` | First calendar year included (inclusive). |
| `--end-year` | `2050` | Last calendar year included (inclusive). Values beyond `2052` emit a warning that Matariki is not gazetted that far out. |
| `--out` | per-format (see [Formats](#formats)) | Output path. Ignored when `--format all` or `--format dbt` (they always write to their fixed default paths since they produce more than one file). |
| `--fiscal-start-month` | `4` | First month of the NZ fiscal year (1 = January … 12 = December). |
| `--format` | `csv` | One of `csv`, `tsql`, `snowflake`, `databricks`, `powerquery`, `dbt`, `all`. `all` writes every format in one run. |

Examples:

```bash
# Snowflake SQL (CREATE TABLE + INSERT + a relative-columns VIEW)
python -m nz_date_dimension.cli --format snowflake --out ../outputs/nz-date-dimension.snowflake.sql

# Power Query (M) — a single query, ready to paste into Get Data > Blank Query
python -m nz_date_dimension.cli --format powerquery --out ../outputs/nz-date-dimension.pq

# Everything at once, into outputs/ (and outputs/dbt/ for the dbt model + seed)
python -m nz_date_dimension.cli --format all
```

## Formats

Every format is emitted from the **same** Python-computed dataset — one
generator, per-format emitters, no per-format drift — guarded by a
cross-format consistency test in `tests/test_cross_format_consistency.py`.

| Format | Status | Emitter | Notes |
|---|---|---|---|
| CSV | ✅ Available | `emit_csv.py` | Stable columns only + a `GeneratedOn` stamp. The ready-made download above. |
| T-SQL (SQL Server) | ✅ Available | `emit_tsql.py` | `CREATE TABLE` + batched `INSERT`s of the stable rows, plus a `CREATE VIEW` deriving the relative columns from `GETDATE()`. |
| Snowflake SQL | ✅ Available | `emit_snowflake.py` | Same shape as T-SQL, Snowflake-native types/functions (`BOOLEAN`, `CURRENT_DATE()`, `DAYOFWEEKISO`). |
| Databricks SQL | ✅ Available | `emit_databricks.py` | Same shape again, Spark SQL functions (`current_date()`, `dayofweek()`-derived ISO weekday). |
| Power Query (M) | ✅ Available | `emit_powerquery.py` | A single `let...in` query: the stable rows as a `#table` literal, plus the relative columns computed live via `DateTime.LocalNow()` on every refresh — no separate view needed. |
| dbt model | ✅ Available | `emit_dbt.py` | `dbt_utils.date_spine` generates the calendar spine; a seed (`nz_date_dimension_holidays.csv`) carries the holiday/Matariki/provincial lookup; relative columns via `current_date()`. Snowflake-flavoured SQL — see the model's own header comment. |
| Power BI (`.pbit`/`.pbix`) | 🔜 Fast-follow | — | Not in this repo yet — see [Roadmap](#roadmap). |

### Relative / time-intelligence columns

`DayOffset`, `WeekOffset`, `MonthOffset`, `QuarterOffset`, `YearOffset`,
`FiscalYearOffset`, `FiscalQuarterOffset`, `IsToday`, `IsCurrentWeek`,
`IsCurrentMonth`, `IsCurrentQuarter`, `IsCurrentYear`,
`IsCurrentFiscalYear`, `IsCalendarYTD`, `IsFiscalYTD`, `IsMonthToDate`,
`IsQuarterToDate`, `IsLast7Days`, `IsLast30Days`, `IsLast90Days`,
`IsPriorMonth`, `IsPriorYear`, `IsRolling12Months`.

These are **dynamic** — always "as of today" — so they are **deliberately
not in the static CSV** (a frozen `IsCalendarYTD` would be wrong the next
day). They live in:

- `generator/nz_date_dimension/relative.py` — the reference Python
  implementation (tested against an injectable `today` so results are
  deterministic).
- The **Power Query** output directly (computed via `DateTime.LocalNow()`).
- A companion **`CREATE VIEW`** in each SQL format (derived from
  `CURRENT_DATE`/`GETDATE()`/`current_date()`).
- The **dbt model** (derived from `current_date()`, recomputed every run).

**Timezone caveat:** "today" resolves via the query engine's clock — the
session/warehouse timezone, not necessarily NZ time. For `IsToday` /
`IsCalendarYTD` to align to NZ midnight, run the dynamic formats in an
NZ-timezone session/context.

## Columns

Every row is one calendar date. See
[`docs/column-dictionary.md`](docs/column-dictionary.md) for the full list —
calendar columns, fiscal-year columns, national holiday columns, the 17
per-region `IsHoliday_<CODE>` flags, and the relative/time-intelligence
columns — with type and description for each.

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

`requirements-dev.txt` pulls in the runtime dependency (`holidays==0.101`)
plus `pytest`; `requirements.txt` alone (used by the quick start above) is
runtime-only.

## Attribution

Public-holiday and Matariki dates are © New Zealand Government, reused
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Holiday
computation via [`python-holidays`](https://github.com/vacanza/holidays)
(MIT licence).

## Licences

- **Code**: MIT — see [`LICENSE`](LICENSE).
- **Generated data files**: CC BY 4.0 — see [`DATA-LICENSE`](DATA-LICENSE).

## Roadmap

**Plan A** (core generator + CSV) and **Plan B** (relative/time-intelligence
columns, T-SQL/Snowflake/Databricks/Power Query/dbt emitters, and the
cross-format consistency test) are both done — see [Formats](#formats).

Still ahead:

- A Power BI template (`.pbit`)/`.pbix` fast-follow with DAX measures
  (gated / email-capture piece).
- Expanding beyond Aotearoa New Zealand to the wider Pacific (the generator
  already parameterises country/region and fiscal-year-start for this).
