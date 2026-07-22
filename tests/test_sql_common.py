import re
from datetime import date
from nz_date_dimension.sql_common import (
    column_kind, sql_literal, create_table_sql, insert_statements_sql,
    relative_view_sql, relative_select_sql, DIALECTS,
)
from nz_date_dimension.build import STABLE_COLUMNS, build_dataset
from nz_date_dimension.columns import stable_columns

def test_column_kind_classification():
    assert column_kind("Date") == "date"
    assert column_kind("FiscalStartOfYear") == "date"
    assert column_kind("DateKey") == "int"
    assert column_kind("FiscalYear") == "int"
    assert column_kind("MonthName") == "str"
    assert column_kind("HolidayName") == "str"
    assert column_kind("IsWeekend") == "bool"
    assert column_kind("IsHoliday_AUK") == "bool"
    assert column_kind("IsHoliday_WTC") == "bool"

def test_sql_literal_null_and_types():
    assert sql_literal(None, "str", "tsql") == "NULL"
    assert sql_literal(True, "bool", "tsql") == "1"
    assert sql_literal(False, "bool", "tsql") == "0"
    assert sql_literal(True, "bool", "snowflake") == "TRUE"
    assert sql_literal(False, "bool", "databricks") == "FALSE"
    assert sql_literal(date(2025, 12, 25), "date", "tsql") == "'2025-12-25'"
    assert sql_literal(20251225, "int", "snowflake") == "20251225"
    assert sql_literal("O'Brien", "str", "tsql") == "'O''Brien'"

def test_create_table_has_every_stable_column_for_each_dialect():
    for dialect in DIALECTS:
        ddl = create_table_sql("NZDateDimension", dialect)
        assert "CREATE TABLE" in ddl
        for col in STABLE_COLUMNS:
            assert col in ddl, f"{dialect} DDL missing {col}"
        assert "HolidayName" in ddl

def test_insert_statements_cover_every_row_and_batch_correctly():
    rows = build_dataset(2025, 2025)  # 365 rows
    for dialect in DIALECTS:
        stmts = insert_statements_sql(rows, "NZDateDimension", dialect, batch_size=150)
        assert len(stmts) == 3  # 150 + 150 + 65 rows => ceil(365/150) == 3
        total_row_tuples = sum(s.count("),\n(") + 1 for s in stmts)
        assert total_row_tuples == 365
        for s in stmts:
            assert s.strip().startswith("INSERT INTO")
            assert s.strip().endswith(";")

def test_relative_view_sql_references_base_table_and_current_date():
    for dialect in DIALECTS:
        view = relative_view_sql("NZDateDimension", "vw_NZDateDimensionRelative", dialect,
                                  fiscal_start_month=4)
        assert "CREATE VIEW" in view
        assert "NZDateDimension" in view
        for col in ["DayOffset", "WeekOffset", "MonthOffset", "QuarterOffset", "YearOffset",
                    "FiscalYearOffset", "FiscalQuarterOffset", "IsToday", "IsCurrentWeek",
                    "IsCurrentMonth", "IsCurrentQuarter", "IsCurrentYear",
                    "IsCurrentFiscalYear", "IsCalendarYTD", "IsFiscalYTD", "IsMonthToDate",
                    "IsQuarterToDate", "IsLast7Days", "IsLast30Days", "IsLast90Days",
                    "IsPriorMonth", "IsPriorYear", "IsRolling12Months"]:
            assert col in view, f"{dialect} view missing {col}"

def test_relative_select_sql_quotes_all_base_table_column_references():
    """Regression for review finding C1: create_table_sql() emits quoted,
    case-preserved column names (e.g. "Year" on Snowflake). An unquoted
    t.Year reference in the companion relative view/model folds to T.YEAR
    on Snowflake, which does NOT match the quoted "Year" column -> invalid
    identifier, and the whole relative SELECT fails to compile. Every
    t.<Column> reference must go through the dialect's own quoter, for all
    three SQL dialects (kept consistent even though only Snowflake is
    case-sensitive).
    """
    for dialect in DIALECTS:
        q = DIALECTS[dialect]["quote"]
        quote_char = q("X")[0]  # dialect's opening quote char: " [ `
        sql = relative_select_sql("NZDateDimension", dialect, fiscal_start_month=4)
        # A bare "t.<word>" not immediately followed by the dialect's own
        # quote character is an unquoted, dialect-unsafe base-table
        # reference. "t.*" is fine (wildcard, no identifier to quote).
        bare_refs = re.findall(rf"\bt\.(?!\*)(?!{re.escape(quote_char)})\w+", sql)
        assert not bare_refs, f"{dialect}: unquoted base-table column refs: {bare_refs}"

def test_snowflake_int_div_floors_to_integer():
    """Regression for review finding I1: Snowflake '/' is decimal division
    (7/3 -> 2.333333), unlike T-SQL/Databricks integer division, so
    TodayFiscalQuarter (and any offset built from int_div, e.g.
    WeekOffset) surfaces fractional/decimal instead of the spec's required
    int (spec section 4.5) unless explicitly floored.
    """
    expr = DIALECTS["snowflake"]["int_div"]("a", "b")
    assert expr.upper().startswith("FLOOR("), f"snowflake int_div not floored: {expr}"

def test_relative_select_sql_snowflake_fiscal_quarter_offset_is_floored():
    sql = relative_select_sql("NZDateDimension", "snowflake", fiscal_start_month=4)
    assert "FLOOR(" in sql

def test_databricks_create_table_has_no_enforced_primary_key_constraint():
    """Regression for review finding M3: PRIMARY KEY is a hard syntax error
    on Databricks outside Unity Catalog (and merely informational/
    unenforced even inside it) -- must not appear as a real constraint,
    only (optionally) as a documentation comment.
    """
    ddl = create_table_sql("NZDateDimension", "databricks")
    assert "PRIMARY KEY" not in ddl
    assert "CONSTRAINT" not in ddl

def test_tsql_and_snowflake_create_table_still_declare_primary_key():
    # Unaffected by M3 -- T-SQL and Snowflake PRIMARY KEY is valid there.
    for dialect in ("tsql", "snowflake"):
        ddl = create_table_sql("NZDateDimension", dialect)
        assert "PRIMARY KEY" in ddl

# --- dynamic columns (spec §7 resolution 1: emitters must not hardcode NZ) ---

def test_column_kind_classifies_country_as_string():
    assert column_kind("Country") == "str"

def test_create_table_sql_uses_the_columns_argument_not_stable_columns():
    au_cols = stable_columns(["AU"])
    ddl = create_table_sql("AUDateDimension", "snowflake", columns=au_cols)
    assert '"IsHoliday_WA"' in ddl
    assert '"IsHoliday_AUK"' not in ddl  # NZ-only column must not leak into AU DDL

def test_create_table_sql_combined_includes_country_column():
    combined_cols = stable_columns(["NZ", "AU"])
    ddl = create_table_sql("ANZDateDimension", "tsql", columns=combined_cols)
    assert "[Country]" in ddl
    assert "[IsHoliday_NZ_AUK]" in ddl
    assert "[IsHoliday_AU_WA]" in ddl

def test_insert_statements_sql_uses_the_columns_argument():
    rows = build_dataset(2025, 2025, country="AU")
    au_cols = stable_columns(["AU"])
    stmts = insert_statements_sql(rows, "AUDateDimension", "tsql", batch_size=1000, columns=au_cols)
    assert len(stmts) == 1
    assert "[IsHoliday_WA]" in stmts[0] or '"IsHoliday_WA"' in stmts[0]

def test_create_table_sql_default_columns_unchanged_for_nz_backward_compat():
    # No columns= argument -> must still default to STABLE_COLUMNS (NZ),
    # preserving every existing call site's behaviour.
    ddl = create_table_sql("NZDateDimension", "snowflake")
    for col in STABLE_COLUMNS:
        assert col in ddl

# --- composite primary key for Combined mode (spec §7 resolution 5) ---

def test_create_table_sql_default_primary_key_is_still_just_date():
    for dialect in ("tsql", "snowflake"):
        ddl = create_table_sql("NZDateDimension", dialect)
        assert re.search(r"PRIMARY KEY \(.\bDate\b.\)", ddl)

def test_create_table_sql_composite_primary_key_for_combined():
    combined_cols = stable_columns(["NZ", "AU"])
    for dialect in ("tsql", "snowflake"):
        ddl = create_table_sql("ANZDateDimension", dialect, columns=combined_cols,
                                primary_key=["Date", "Country"])
        assert "PRIMARY KEY" in ddl
        # both key columns present in the same constraint clause
        pk_line = next(line for line in ddl.splitlines() if "PRIMARY KEY" in line)
        assert "Date" in pk_line and "Country" in pk_line

def test_databricks_create_table_composite_key_still_has_no_constraint():
    combined_cols = stable_columns(["NZ", "AU"])
    ddl = create_table_sql("ANZDateDimension", "databricks", columns=combined_cols,
                            primary_key=["Date", "Country"])
    assert "PRIMARY KEY" not in ddl
    assert "CONSTRAINT" not in ddl
    assert "Date" in ddl and "Country" in ddl  # documented in the informational comment
