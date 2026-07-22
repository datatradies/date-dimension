# Fix Wave — Response to PLAN-B-REVIEW.md

**Scope:** the 2 Critical / 3 Important / 4 Minor findings from the
independent review of the Plan B additions (`PLAN-B-REVIEW.md`), applied on
top of the 9 unpushed Plan B commits. Followed TDD throughout: for every
finding, a regression test was written and confirmed to **fail against the
unfixed code** (red) before the fix was made (green). All 9 findings are
resolved; nothing was skipped.

---

## C1 (Critical) — Snowflake/dbt relative SQL referenced base columns unquoted

**Where:** `generator/nz_date_dimension/sql_common.py` — `relative_select_sql()`

`create_table_sql()` emits quoted, case-preserved columns (`"Year"`,
`"Date"`, ...), but the relative-columns SQL referenced them unquoted
(`t.Year`, `t.Date`, `t.DayOfWeek`, `t.Month`, `t.Quarter`, `t.FiscalYear`,
`t.FiscalQuarter`). On Snowflake, unquoted `t.Year` folds to `T.YEAR`, which
does not match the quoted `"Year"` column → `invalid identifier`. Since the
dbt model's tail reuses `relative_select_sql(..., "snowflake", ...)`
verbatim, the dbt model inherited the identical failure.

**TDD:** added `test_relative_select_sql_quotes_all_base_table_column_references`
to `tests/test_sql_common.py` — for every dialect, regex-scans the generated
SQL for any `t.<word>` not immediately followed by that dialect's own quote
character. Confirmed failing first: **42 unquoted refs found** across all
three dialects (T-SQL and Databricks share the same unquoted code path, so
the bug wasn't Snowflake-only in the source even though only Snowflake is
case-sensitive enough to break on it).

**Fix:** added `tq = lambda c: f"t.{q(c)}"` inside `relative_select_sql()`
and replaced every bare `t.<Column>` with `tq('Column')`, applied
consistently across all three dialects (T-SQL `t.[Date]`, Snowflake
`t."Date"`, Databricks `` t.`Date` ``) per the review's recommendation, not
just Snowflake.

## C2 (Critical) — dbt `with_holidays` CTE declared unquoted, referenced quoted

**Where:** `generator/nz_date_dimension/emit_dbt.py`

The final holiday CTE was declared `with_holidays as (` (unquoted), but
`relative_select_sql("with_holidays", "snowflake", fsm)` renders its
`table_name` argument through the Snowflake quoter, producing
`FROM "with_holidays" AS t`. Unquoted `with_holidays` canonicalises to
`WITH_HOLIDAYS`; quoted `"with_holidays"` stays literal — they don't match →
a second, independent Snowflake compile failure.

**TDD:** added
`test_dbt_model_with_holidays_cte_declaration_matches_relative_fragment_reference`
to `tests/test_emit_dbt.py`, asserting both the quoted declaration and the
quoted `FROM` reference are present. Confirmed failing first (declaration
was unquoted).

**Fix:** changed the CTE declaration to `"with_holidays" as (` so it matches
the reference. No other reference needed updating (the `holidays` CTE stays
unquoted on both sides — internally consistent, not part of this bug).

## I1 (Important) — Snowflake `int_div` used decimal `/` instead of integer division

**Where:** `generator/nz_date_dimension/sql_common.py` — Snowflake dialect's `int_div`

Snowflake `/` never truncates (`7/3 → 2.333...`). `TodayFiscalQuarter` came
out fractional for 8 months of the year, and `WeekOffset` surfaced as a
decimal instead of the int the spec requires (§4.5) — even though the
author already knew to floor for the dbt model's *stable* `FiscalQuarter`
column, the shared `int_div` helper (used for the *relative* columns) did
not.

**TDD:** added `test_snowflake_int_div_floors_to_integer` and
`test_relative_select_sql_snowflake_fiscal_quarter_offset_is_floored` to
`tests/test_sql_common.py`. Confirmed failing first (`int_div("a","b")` →
`"((a) / b)"`, no `FLOOR`).

**Fix:** `"int_div": lambda a, b: f"FLOOR(({a}) / {b})"` for the Snowflake
dialect only (T-SQL's `/` already truncates on `INT`; Databricks already
uses `DIV`). This also resolves **M4** (decimal-typed offset columns) as a
side effect, per the review's note that the two share a root cause.

## I2 (Important) — Power Query fiscal quarter wrong in Jan–Mar (April fiscal start)

**Where:** `generator/nz_date_dimension/emit_powerquery.py`

M's `Number.Mod` follows the dividend's sign (`IntegerDivide` truncates
toward zero), so `Number.Mod(Date.Month(Today) - FiscalStartMonth, 12)`
goes negative for Jan/Feb/Mar under the default April fiscal start — e.g.
January: `Number.Mod(-3, 12) = -3` → `TodayFiscalMonth = -2` →
`TodayFiscalQuarter = IntegerDivide(-3, 3) + 1 = 0` (should be 4),
corrupting `FiscalQuarterOffset` by 4 for every row during a refresh in
those months.

**TDD:** added `test_today_fiscal_month_uses_positive_modulo_guard` to
`tests/test_emit_powerquery.py`, asserting the exact positive-modulo
expression is present (and the naive bare form is not, anchored on the
binding name to avoid a false match against the fixed expression's own
nested `Number.Mod(...) + 12`). Confirmed failing first.

**Fix:** wrapped in the positive-modulo idiom:
`TodayFiscalMonth = Number.Mod(Number.Mod(Date.Month(Today) - FiscalStartMonth, 12) + 12, 12) + 1`.

## I3 (Important) — dbt `date_spine` boundary relied on unverified inclusivity

**Where:** `generator/nz_date_dimension/emit_dbt.py` — `build_dbt_model_sql()`

The model passed `end_date` straight into `dbt_utils.date_spine()` and
claimed (in a comment) that the pinned version is inclusive of it. The old
"boundary test" only checked that the word `"inclusive"` appeared somewhere
in the generated SQL — it never inspected the spine logic itself, so it
could never catch an off-by-one, and the inclusivity claim couldn't be
verified without a live warehouse.

**TDD:** replaced the vacuous test with
`test_dbt_model_filters_spine_to_exact_range_regardless_of_date_spine_boundary`
in `tests/test_emit_dbt.py`, asserting: (a) an explicit
`where date_day between ...` filter exists, (b) `date_spine()` is called
with a distinct `spine_end_date`, not the intended `end_date` directly, and
(c) both the extended spine bound (`2051-01-01`) and the true intended
`end_date` (`2050-12-31`) are present. Confirmed failing first (no filter
existed; `date_spine` was called with `end_date` directly). Kept a second
test, `test_dbt_model_still_documents_intended_inclusive_range`, asserting
the model still documents the *intended* semantics for a human reader.

**Fix:** made the model boundary-robust instead of boundary-trusting:

- `spine_raw` now calls `dbt_utils.date_spine()` with `spine_end_date` — one
  day **past** the intended `end_date` (e.g. `2051-01-01` for an intended
  `2050-12-31` end) — so the raw spine is guaranteed to reach the intended
  last day whether `date_spine`'s own `end_date` argument is inclusive or
  exclusive.
- A new `spine` CTE then explicitly filters:
  `select * from spine_raw where date_day between {{ start_date }} and {{ end_date }}`,
  clipping back to the exact intended `[start_date, end_date]` range
  regardless of that boundary behaviour.
- Updated the header's BOUNDARY NOTE and the `DBT_UTILS_VERSION_PIN` comment
  to describe this explicit-filter guarantee instead of an unverified
  inclusivity claim, and kept the recommendation that a live check against
  the pinned `dbt_utils` version is still worthwhile before first
  production run (this could not be verified here — no live warehouse
  available).

## M1 (Minor) — dbt seed CSV hand-joined without escaping

**Where:** `generator/nz_date_dimension/emit_dbt.py` — `build_dbt_seed_csv()`

Values were joined with a bare `",".join(...)`, unlike `emit_csv.py` (which
already uses `csv.writer`). Safe today only because python-holidays never
puts a comma in a `HolidayName` — an accidental invariant, not a guarantee.

**TDD:** added `test_seed_csv_escapes_values_containing_commas` to
`tests/test_emit_dbt.py`, injecting a synthetic `HolidayName = "Foo, Bar Day"`
and asserting it round-trips through `csv.DictReader` unchanged. Confirmed
failing first (`reader[0]["HolidayName"] == "Foo"`, split at the comma).

**Fix:** rewrote `build_dbt_seed_csv()` to use `csv.writer` over an
`io.StringIO` buffer (matching `emit_csv.py`'s pattern), with
`lineterminator="\n"` to preserve the function's existing platform-
independent string output and leave `write_dbt_seed()`'s file-writing
behaviour unchanged.

## M2 (Minor) — Cross-format test's T-SQL row extractor broke on embedded `)`

**Where:** `tests/test_cross_format_consistency.py` — `_extract_row_tokens()`

The row extractor used a non-greedy regex (`.*?` + close char) that stopped
at the **first** `)` in the text — including one embedded inside a quoted
`HolidayName` like `"Anzac Day (observed)"`. None of `SAMPLE_DATES` happened
to hit an observed/Mondayised date, so the test suite never exercised this,
but it was one config change away from silently misaligning every column
after the first observed row it hit.

**TDD:** added
`test_extract_row_tokens_handles_holiday_name_containing_close_paren`,
which pulls a real observed holiday directly from `build_dataset()` (rather
than hardcoding a year/date, since which years have Mondayised holidays is
a `holidays` library fact, not a project constant) and asserts the full row
extracts with the correct token count and an unmangled `HolidayName`.
Confirmed failing first empirically: **32 tokens extracted instead of 51**,
`HolidayName` truncated to `"'Anzac Day (observed"` (unterminated).

**Fix:** rewrote `_extract_row_tokens()` to scan forward from the row start
tracking quote state (with doubled-quote escaping, matching
`_split_top_level`'s own convention) so only a `close_char` **outside** any
quoted literal ends the row — a `)` inside `'...(observed)...'` is now
correctly skipped.

## M3 (Minor) — Databricks `PRIMARY KEY` is a hard error outside Unity Catalog

**Where:** `generator/nz_date_dimension/sql_common.py` — `create_table_sql()`

The `CONSTRAINT PK_... PRIMARY KEY (...)` clause is informational-only even
inside Unity Catalog, and a hard syntax error on a Hive-metastore/
`spark_catalog` target outside it. The inline comment only noted the
"informational" part, not that it could fail to parse at all.

**TDD:** added
`test_databricks_create_table_has_no_enforced_primary_key_constraint` and
`test_tsql_and_snowflake_create_table_still_declare_primary_key` to
`tests/test_sql_common.py`. Confirmed the Databricks test failing first.

**Fix:** `create_table_sql()` now branches on `dialect == "databricks"`:
emits the natural key as a leading `-- ` documentation comment instead of a
real `CONSTRAINT ... PRIMARY KEY` clause. T-SQL and Snowflake are
unaffected (PRIMARY KEY is fully supported and unenforced-risk-free there).

---

## Verification

**Full suite:**

```
python -m pytest -v
```

**84 passed** — 74 from the original baseline (unmodified, run first to
confirm a clean starting point), plus **10 net-new tests**: 9 regression
tests, one per finding (5 in `test_sql_common.py` for C1/I1/M3, 3 in
`test_emit_dbt.py` for C2/I3/M1, 1 in `test_emit_powerquery.py` for I2, 1 in
`test_cross_format_consistency.py` for M2), plus 1 non-regression test
(`test_dbt_model_still_documents_intended_inclusive_range`, replacing half
of the old vacuous I3 test, asserting the model still documents intended
range semantics for a human reader — it was never expected to fail, since
it doesn't test the bug). Each of the 9 regression tests was confirmed
**failing against the pre-fix code** before its corresponding fix landed
(TDD red → green): a full run immediately after writing all 9 tests but
before any fix showed exactly `9 failed, 75 passed`, one failure per
finding.

**End-to-end smoke test:** ran `python -m nz_date_dimension.cli --format all
--start-year 2025 --end-year 2026` against an isolated scratch copy of the
generator (not the tracked repo tree) — exit 0, all 7 artefacts written
(730 rows each), and spot-checked the generated Snowflake relative view and
dbt model text to confirm every `t.*` base-column reference is now quoted,
`FLOOR(...)` appears around the fiscal-quarter/week math, the dbt spine's
explicit `where date_day between ...` filter is present, and the seed CSV
contains real `(observed)` holiday rows without corruption.

## Remaining concern requiring a live warehouse

**I3's underlying premise — `dbt_utils.date_spine`'s actual inclusive/
exclusive behaviour at the pinned version (`>=1.1.0, <2.0.0`) — was not, and
could not be, verified here** (no live dbt/Snowflake environment available
in this environment, same limitation the original review flagged). The fix
makes the model **correct regardless of which behaviour is true** (the
explicit post-spine filter guarantees the exact intended range either way),
so this is now a defence-in-depth item rather than a blocking risk — but a
one-time live run against the pinned `dbt_utils` version, checking that the
model's row count for a small range matches the expected day count, is
still recommended before first production use, per the review's original
"must-verify" flag.
