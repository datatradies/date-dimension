from datetime import date
from nz_date_dimension.sql_common import (
    column_kind, sql_literal, create_table_sql, insert_statements_sql,
    relative_view_sql, DIALECTS,
)
from nz_date_dimension.build import STABLE_COLUMNS, build_dataset

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
