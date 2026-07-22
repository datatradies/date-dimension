# Plan B — Independent Code Review

**Scope:** the 9 unpushed commits `origin/main..main` (Plan B additions to the
NZ date-dimension generator). Plan A is the baseline. Reviewer read the real
code and the emitted output; `python -m pytest` → **74 passed**. No live
SQL Server / Snowflake / Databricks / Power BI / dbt engine was available, so
dialect correctness is argued from reading + reproduced emitter output.

---

## Verdict: **fix-first**

**Why:** The shared relative-column SQL (`relative_select_sql`) is **not
Snowflake-safe**. It references the base table's quoted, mixed-case columns
(`t.Year`, `t.Date`, …) *without quoting*, so on Snowflake — where quoted
identifiers are case-sensitive — the companion relative **VIEW** and the
(Snowflake-flavoured) **dbt model** fail to compile with *invalid identifier*.
Two of the six headline formats' dynamic layer will not run as shipped. The
CSV/T-SQL/Databricks/Power-Query *stable* layer, the Python relative logic, the
architecture, and the test suite are otherwise sound.

Counts: **2 Critical · 3 Important · 4 Minor.**

Must-fix before ship: **C1, C2** (Snowflake/dbt won't compile); strongly
recommended: **I1, I2, I3**.

---

## Critical

### C1 — Snowflake relative view + dbt model reference base columns unquoted → won't compile on Snowflake
`generator/nz_date_dimension/sql_common.py:190-230`

`create_table_sql` emits **quoted, case-sensitive** column names on Snowflake:

```
CREATE TABLE "NZDateDimension" (
    "Date" DATE NOT NULL,
    "Year" NUMBER(9,0) NOT NULL,
    "Quarter" NUMBER(9,0) NOT NULL,
    "DayOfWeek" NUMBER(9,0) NOT NULL,
    "FiscalQuarter" NUMBER(9,0) NOT NULL,
    ...
```

But `relative_select_sql` builds the derived columns with **unquoted**
references:

```
(t.Year - c.TodayYear) * 12 + (t.Month - c.TodayMonth) AS "MonthOffset",
... t.Date ... t.DayOfWeek ... t.Quarter ... t.FiscalYear ... t.FiscalQuarter ...
```

On Snowflake an unquoted `t.Year` folds to `T.YEAR`, but the column is literally
`Year` (case preserved by the quotes). `YEAR ≠ Year` → **`invalid identifier
'T.YEAR'`**. Every `t.<Column>` reference in lines 190-230 breaks the same way,
so the whole `SELECT` (and therefore `CREATE VIEW vw_NZDateDimensionRelative`)
fails. The base `CREATE TABLE`/`INSERT`s are fine — only the relative view dies.

This is **case-insensitive-engine-only-safe** code: T-SQL and Spark/Databricks
resolve identifiers case-insensitively, so they happen to work; Snowflake does
not. The unit tests only assert `col in view` (string presence), so they can't
catch it, and no Snowflake engine was run.

Because the dbt model ends in `select * from relative` (the reused
`relative_select_sql("with_holidays", "snowflake", …)` fragment), the **dbt
model inherits the identical failure** — and dbt is explicitly
Snowflake-flavoured, so it won't build at all.

**Fix:** quote every base-table reference with the dialect quoter. e.g. add a
helper `tq = lambda c: f"t.{q(c)}"` and use `tq('Year')`, `tq('Date')`,
`tq('DayOfWeek')`, `tq('Quarter')`, `tq('Month')`, `tq('FiscalYear')`,
`tq('FiscalQuarter')` throughout lines 190-230. That yields `t."Date"`
(Snowflake), `t.[Date]` (T-SQL), `` t.`Date` `` (Databricks) — correct on all
three. The `c.Today*` CTE side is already internally consistent (declared and
referenced unquoted) and needs no change.

### C2 — dbt `with_holidays` CTE: unquoted declaration vs quoted reference → invalid identifier on Snowflake
`generator/nz_date_dimension/emit_dbt.py:154` (declaration) and `:166` (`relative_select_sql("with_holidays", "snowflake", fsm)`)

The final holiday CTE is declared **unquoted**:

```
with_holidays as (
    select fiscal_final.*, ... from fiscal_final left join holidays ...
)
```

but `relative_select_sql` renders its `table_name` through the Snowflake quoter,
producing `FROM "with_holidays" AS t`. Unquoted `with_holidays` → canonical
`WITH_HOLIDAYS`; quoted `"with_holidays"` → literal `with_holidays`. They don't
match → **`invalid identifier 'with_holidays'` / object does not exist**. This
is a *second, independent* Snowflake compile failure in the dbt model (the raw
Snowflake emitter avoids it because its table name `"NZDateDimension"` is quoted
consistently on both sides).

**Fix:** declare the CTE quoted to match the reference — change line 154
`with_holidays as (` → `"with_holidays" as (`. (It is referenced only by the
relative fragment, so no other reference needs updating.) Verify together with
C1.

---

## Important

### I1 — Snowflake `int_div` uses `/`, which is decimal division → fractional `TodayFiscalQuarter` / decimal `WeekOffset`
`generator/nz_date_dimension/sql_common.py:74`

```
"int_div": lambda a, b: f"(({a}) / {b})",
```

Snowflake `/` never truncates — `7/3 → 2.333333`. Two consumers break once C1/C2
are fixed:

- `TodayFiscalQuarter = (((MOD(MOD(MONTH(CURRENT_DATE()) - 4,12)+12,12)+1) - 1) / 3) + 1`
  is fractional for 8 months of the year (any month that is the 2nd/3rd of a
  fiscal quarter). e.g. May → fiscal_month 2 → `(2-1)/3 = 0.333` →
  `TodayFiscalQuarter = 1.333`, so `FiscalQuarterOffset` comes out fractional
  (spec §4.5 types it **int**). This also flows into the dbt model.
- `WeekOffset = (… )/7` is exact (numerator is always a multiple of 7) but is
  typed as a decimal, not an int.

The author *knew* Snowflake needs an explicit floor — `emit_dbt.py:141` uses
`floor(("FiscalMonth" - 1) / 3) + 1` for the stable column — but the shared
`int_div` helper doesn't. T-SQL (`/` on INT truncates) and Databricks (`DIV`,
confirmed in output) are correct.

**Fix:** `"int_div": lambda a, b: f"FLOOR(({a}) / {b})"` for the Snowflake
dialect only.

### I2 — Power Query `TodayFiscalMonth` uses raw `Number.Mod` (no positive-modulo guard) → wrong fiscal quarter when refreshed in fiscal Q4
`generator/nz_date_dimension/emit_powerquery.py:129-130`

```
TodayFiscalMonth = Number.Mod(Date.Month(Today) - FiscalStartMonth, 12) + 1,
TodayFiscalQuarter = Number.IntegerDivide(TodayFiscalMonth - 1, 3) + 1,
```

M's `Number.Mod` follows the dividend's sign (`Number.Mod(x,y) = x - y*
IntegerDivide(x,y)`, and `IntegerDivide` truncates toward zero) — hence the
well-known `Number.Mod(Number.Mod(x,n)+n,n)` idiom. For a default April fiscal
start, a refresh in **Jan/Feb/Mar** gives `Date.Month(Today) - 4 < 0`:
January → `Number.Mod(-3,12) = -3` → `TodayFiscalMonth = -2` →
`TodayFiscalQuarter = IntegerDivide(-3,3)+1 = 0` (correct value is 4). So
`FiscalQuarterOffset` is wrong by 4 for every row during those months.

Python (`%` is non-negative) and the SQL emitters (`pos_mod`) both guard this;
Power Query is the only format that skips it. Note the materialised *stable*
`FiscalMonth`/`FiscalQuarter` columns are Python-computed and correct — only the
live `Today…` derivation is affected.

**Fix:** wrap in the positive-modulo idiom:
`TodayFiscalMonth = Number.Mod(Number.Mod(Date.Month(Today) - FiscalStartMonth, 12) + 12, 12) + 1`.

### I3 — dbt `date_spine` boundary is (per current dbt_utils) **exclusive** of `end_date`; the model claims inclusive and the "boundary test" only checks a comment
`generator/nz_date_dimension/emit_dbt.py:82,181-186,198` · `tests/test_emit_dbt.py:36-39`

The model passes `end_date = cast('2050-12-31' as date)` and the header asserts
the pin `>=1.1.0,<2.0.0` is *inclusive*. But dbt_utils' `date_spine` generates
`dateadd(day, row_number-1, start_date)` for `row_number in 1..datediff(start,
end)`, i.e. `start … start + (datediff-1) = end_date - 1`, filtered `<=
end_date`. That is the widely-documented **exclusive** behaviour: the last spine
row is `end_date - 1` (2050-12-30), so the dbt output would **drop the final
day** that CSV/T-SQL/Snowflake/M all include — a cross-format inconsistency and
a spec §11 violation.

Spec §11 explicitly requires asserting "the `date_spine` output's **last row**
equals the intended `end_date`". The actual test only does:

```python
def test_dbt_model_has_boundary_note_about_inclusive_end_date():
    sql = build_dbt_model_sql()
    assert "inclusive" in sql.lower()   # only checks a comment exists
    assert "end_date" in sql
```

That is **vacuous** as a boundary guard — it never runs `date_spine`, so it
cannot detect an off-by-one. (I could not run dbt here to settle the
inclusive/exclusive question empirically — flagging as must-verify.)

**Fix:** verify against the pinned dbt_utils on a real warehouse. If exclusive
(the documented default), set `end_date` to `cast('<end_year+1>-01-01' as
date)` (relying on the `<= end_date` filter) or add one day, and correct the
"inclusive" comment. Replace the comment-presence test with a real last-row
assertion in a warehouse-backed test (or clearly mark it as un-runnable here).

---

## Minor

### M1 — dbt seed CSV is hand-joined without CSV escaping
`generator/nz_date_dimension/emit_dbt.py:35-49`

`build_dbt_seed_csv` does `",".join(values)` with no quoting, unlike
`emit_csv.py` which uses `csv.writer`. Safe *today* — python-holidays joins
same-day names with `"; "` (e.g. `"Anzac Day (observed); Easter Monday"`), never
a comma — but a single comma in any future `HolidayName` would silently corrupt
the seed's column alignment. Prefer `csv.writer`/`io.StringIO`.

### M2 — Cross-format test's T-SQL row regex breaks on `)` inside a value
`tests/test_cross_format_consistency.py:114-122,141-143`

`_extract_row_tokens` matches T-SQL rows with a non-greedy `.*?)` that stops at
the first `)`. The chosen `SAMPLE_DATES` are all non-observed, so no
`HolidayName` contains `"(observed)"`; but swapping in any Mondayised date (e.g.
`2021-02-08 "Waitangi Day (observed)"`) would make the regex truncate the row
early and misalign token indices. Harden the extractor (it already tracks paren
depth in `_split_top_level`) or keep a comment pinning the sample invariant.

### M3 — Databricks `PRIMARY KEY` constraint is a hard error outside Unity Catalog
`generator/nz_date_dimension/sql_common.py:123`

`CONSTRAINT PK_… PRIMARY KEY (…)` is only accepted on Unity-Catalog tables
(informational, non-enforced). On a Hive-metastore/`spark_catalog` target it is
a syntax error, so the Databricks script won't run there. The inline comment
notes it's informational but not that it can fail to parse. Consider omitting it
for Databricks, or documenting the UC requirement.

### M4 — Snowflake offset columns are decimal-typed, not int (spec §4.5 says int)
`generator/nz_date_dimension/sql_common.py:74`

A consequence of I1's `/`: even after fixing `TodayFiscalQuarter`, `WeekOffset`
(and any `/`-derived offset) surfaces as `NUMBER(x,6)` (e.g. `-3.000000`) on
Snowflake rather than a clean integer. Cosmetic, but a Kiwi analyst opening the
view sees `-3.000000`. `FLOOR(...)` (the I1 fix) resolves it.

---

## What's correct (verified)

- **CSV regression clean.** `outputs/`, `emit_csv.py`, `build.py`,
  `calendar_core.py`, `fiscal.py`, `holidays_nz.py`, `regional.py`, and
  `STABLE_COLUMNS` are **not** in the `origin/main..main` diff — the static CSV
  and all stable columns are byte-for-byte Plan A. Relative columns are never
  written to the CSV (spec §7 honoured).
- **`relative.py` is faithful and correct.** Offsets and every boolean check
  out against a concrete `today` (2026-07-22): week-offset via Monday anchors,
  YTD/MTD/QTD `d <= today` gating, `IsLast7/30/90` inclusive lower bounds,
  `IsPriorMonth/Year`, and the rolling-12-months window (incl. the "exclude
  future days in the current month" rule). `test_relative.py` boundary tests are
  strong and non-vacuous, including calendar-vs-fiscal-year divergence and the
  `fiscal_start_month=1` path.
- **T-SQL relative view is dialect-correct.** The DATEFIRST-independent ISO
  weekday `((DATEPART(WEEKDAY,x)+@@DATEFIRST-2)%7)+1` is equivalent to the
  standard `(…+@@DATEFIRST+5)%7+1` (−2 ≡ 5 mod 7) and verified for
  DATEFIRST 1 and 7; `/` truncates INTs correctly; `GO` batching puts
  `CREATE VIEW` alone in its batch; `NVARCHAR(60)` comfortably fits the longest
  name (`"Day after New Year's Day (observed)"`, 35 chars); batch size 1000
  respects the T-SQL VALUES limit.
- **Databricks relative view is dialect-correct.** `(((dayofweek(x)+5)%7)+1)`
  correctly converts Spark Sun=1..Sat=7 to ISO Mon=1..Sun=7; `DIV` gives integer
  fiscal quarter (confirmed in output); `datediff(end,start)` argument order is
  correctly swapped; case-insensitive engine so the unquoted refs are harmless.
- **Power Query logic is faithful** (aside from I2): `DateTime.LocalNow()` live
  refresh, `Date.StartOfWeek(…, Day.Monday)` week anchoring, and
  `Number.IntegerDivide` correctly used for the fiscal quarter; the last query
  step is the final relative column.
- **Cross-format consistency test is genuinely non-vacuous.** It builds a real
  365-row dataset, emits real T-SQL and M, regex-extracts each sampled row,
  splits literals respecting quote-doubling and `#date(...)` paren nesting, and
  decodes per-dialect literal syntax to compare CSV vs T-SQL vs M vs source for
  every stable column. (It covers CSV/T-SQL/M; Snowflake/Databricks/dbt are not
  round-tripped — a coverage gap, not a vacuity.)
- **Single-source-of-truth architecture holds.** Every format derives from
  `build_dataset` rows; SQL/dbt are pure materialisation + a relative view/model
  that re-expresses `relative.py`'s logic natively; `relative_select_sql` is
  reused verbatim by the Snowflake emitter and the dbt tail so those two can't
  drift.
- **`IsBusinessDay` consistent** between Python (`not weekend and not holiday`,
  with observed days flagged `IsHoliday` via python-holidays' `(observed)`
  entries) and the dbt model (`"IsWeekday" and not IsHoliday`).
- **CLI wiring correct.** `--format {csv,tsql,snowflake,databricks,powerquery,
  dbt,all}`; CSV remains the default; `--out` sensibly ignored for `all`/dbt;
  dbt writes model + seed; `all` writes all seven artefacts (verified end-to-end,
  exit 0). stdlib-only; no new runtime dependency beyond `python-holidays`.
</content>
</invoke>
