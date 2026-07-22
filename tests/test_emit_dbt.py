import csv
import io
import re
import pytest
from nz_date_dimension.build import build_dataset, STABLE_COLUMNS
from nz_date_dimension.relative import RELATIVE_COLUMNS
from nz_date_dimension.countries import NZ_SUBDIVISIONS, AU_SUBDIVISIONS
from nz_date_dimension.columns import seed_columns
from nz_date_dimension.emit_dbt import build_dbt_model_sql, build_dbt_seed_csv, SEED_COLUMNS

def test_seed_csv_has_holiday_and_regional_columns_only():
    rows = build_dataset(2025, 2025)  # 365 rows
    csv_text = build_dbt_seed_csv(rows)
    reader = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(reader) == 365
    assert reader[0].keys() == set(SEED_COLUMNS)
    assert "Date" in SEED_COLUMNS and "IsHoliday" in SEED_COLUMNS
    assert "HolidayName" in SEED_COLUMNS and "IsObserved" in SEED_COLUMNS
    for code in NZ_SUBDIVISIONS:
        assert f"IsHoliday_{code}" in SEED_COLUMNS
    # calendar/fiscal columns are NOT duplicated into the seed -- the dbt
    # model derives them from the date_spine itself.
    assert "Year" not in SEED_COLUMNS and "FiscalYear" not in SEED_COLUMNS

def test_seed_csv_christmas_row_is_a_holiday():
    rows = build_dataset(2025, 2025)
    csv_text = build_dbt_seed_csv(rows)
    reader = list(csv.DictReader(io.StringIO(csv_text)))
    xmas = next(r for r in reader if r["Date"] == "2025-12-25")
    assert xmas["IsHoliday"] == "true"
    assert "Christmas" in xmas["HolidayName"]

def test_dbt_model_uses_date_spine_and_pins_dbt_utils_version():
    sql = build_dbt_model_sql(start_year=2015, end_year=2050, fiscal_start_month=4)
    assert "dbt_utils.date_spine" in sql
    assert "dbt_utils" in sql and "1.1" in sql  # version pin comment

def test_dbt_model_filters_spine_to_exact_range_regardless_of_date_spine_boundary():
    """Regression for review finding I3: dbt_utils.date_spine's end_date
    inclusivity has varied by version (documented as exclusive in some
    releases -- last spine row = end_date - 1), so relying on it silently
    drops (or leaks) the final day. The old test only checked that the word
    "inclusive" appeared in a comment, which can never catch an off-by-one
    since it never inspects the actual spine boundary logic. The model must
    instead: (1) call date_spine with an end bound one interval PAST the
    intended end_date, so the raw spine covers the intended end_date under
    either inclusive or exclusive semantics, and (2) explicitly filter the
    spine to the intended [start_date, end_date] range afterwards.
    """
    sql = build_dbt_model_sql(start_year=2015, end_year=2050)
    # explicit structural range filter, not just a comment
    assert "where date_day between" in sql.lower()
    # the date_spine() call itself must NOT be given the intended end_date
    # directly -- it must use a distinct, later bound (spine_end_date) so
    # an exclusive-of-end_date spine still reaches the real end_date.
    assert 'end_date=spine_end_date' in sql.replace(" ", "")
    assert "2051-01-01" in sql  # spine bound: one day past 2050-12-31
    assert "2050-12-31" in sql  # intended end_date, used by the filter

def test_dbt_model_still_documents_intended_inclusive_range():
    sql = build_dbt_model_sql()
    assert "inclusive" in sql.lower()
    assert "end_date" in sql

def test_dbt_model_references_the_holiday_seed():
    sql = build_dbt_model_sql()
    assert "ref('nz_date_dimension_holidays')" in sql

def test_dbt_model_uses_current_date_for_relative_columns():
    sql = build_dbt_model_sql()
    assert "current_date()" in sql.lower()

def test_dbt_model_includes_every_stable_and_relative_column():
    sql = build_dbt_model_sql()
    for col in STABLE_COLUMNS:
        assert col in sql, f"missing stable column {col}"
    for col in RELATIVE_COLUMNS:
        assert col in sql, f"missing relative column {col}"

def test_dbt_model_has_no_dangling_trailing_commas():
    # A trailing comma immediately before FROM or a closing CTE paren is a
    # syntax error in Snowflake SQL -- guards against string-templating
    # bugs in the column lists (e.g. the 17 regional-flag columns).
    sql = build_dbt_model_sql()
    assert not re.search(r",\s*\n\s*from\b", sql, re.IGNORECASE)
    assert not re.search(r",\s*\n\)", sql)

def test_dbt_model_with_holidays_cte_declaration_matches_relative_fragment_reference():
    """Regression for review finding C2: relative_select_sql() renders its
    table_name argument through the Snowflake quoter, so the model's tail
    references `FROM "with_holidays" AS t` (quoted). The with_holidays CTE
    itself must therefore be DECLARED quoted too -- an unquoted
    `with_holidays as (` canonicalises to WITH_HOLIDAYS on Snowflake and no
    longer matches the quoted reference -> 'invalid identifier' /
    'object does not exist'.
    """
    sql = build_dbt_model_sql()
    assert '"with_holidays" as (' in sql
    assert 'from "with_holidays" as t' in sql.lower()

def test_seed_csv_escapes_values_containing_commas():
    """Regression for review finding M1: build_dbt_seed_csv hand-joins
    values with a bare ','.join and no CSV quoting/escaping. python-holidays
    currently never puts a comma in a HolidayName (same-day names are
    joined with '; '), but that's an accidental invariant, not a guarantee
    -- a single comma in any future seed value would silently misalign
    every column after it. Assert a comma-containing value round-trips
    correctly through a real CSV reader.
    """
    rows = build_dataset(2025, 2025)
    injected = dict(rows[0])
    injected["IsHoliday"] = True
    injected["HolidayName"] = "Foo, Bar Day"
    injected["IsObserved"] = False
    csv_text = build_dbt_seed_csv([injected] + rows[1:])
    reader = list(csv.DictReader(io.StringIO(csv_text)))
    assert reader[0]["HolidayName"] == "Foo, Bar Day"
    assert set(reader[0].keys()) == set(SEED_COLUMNS)

# --- AU (spec §7: emitters must derive columns from the country config) ---

def test_au_seed_csv_uses_au_state_flags_not_nz():
    rows = build_dataset(2025, 2025, country="AU")
    au_seed_cols = seed_columns(["AU"])
    csv_text = build_dbt_seed_csv(rows, columns=au_seed_cols)
    reader = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(reader) == 365
    assert reader[0].keys() == set(au_seed_cols)
    for code in AU_SUBDIVISIONS:
        assert f"IsHoliday_{code}" in au_seed_cols
    for code in NZ_SUBDIVISIONS:
        if code not in AU_SUBDIVISIONS:  # "TAS" is a valid code in both (AU's Tasmania)
            assert f"IsHoliday_{code}" not in au_seed_cols

def test_au_dbt_model_uses_au_fiscal_start_month_by_default():
    sql = build_dbt_model_sql(start_year=2025, end_year=2026, country="AU")
    # fiscal_start_month should default to AU's 7, not NZ's 4, without the
    # caller having to pass it explicitly (spec §7 resolution).
    assert 'when "Month" >= 7' in sql

def test_au_dbt_model_uses_au_state_flags_and_seed_ref():
    sql = build_dbt_model_sql(country="AU")
    for code in AU_SUBDIVISIONS:
        assert f'"IsHoliday_{code}"' in sql
    for code in NZ_SUBDIVISIONS:
        if code not in AU_SUBDIVISIONS:  # TAS is a valid code in both
            assert f'"IsHoliday_{code}"' not in sql
    assert "ref('au_date_dimension_holidays')" in sql

def test_dbt_model_default_country_is_still_nz():
    sql = build_dbt_model_sql()
    assert "ref('nz_date_dimension_holidays')" in sql
    assert 'when "Month" >= 4' in sql

def test_dbt_model_combined_is_explicitly_unsupported():
    # Per-row country-dependent fiscal year isn't expressible in this
    # hand-authored single-model SQL -- Combined dbt emission is out of
    # scope for this refactor; must fail loudly and clearly, not silently
    # produce wrong SQL.
    with pytest.raises((NotImplementedError, ValueError), match="(?i)combined"):
        build_dbt_model_sql(country="combined")
