import re
from nz_date_dimension.build import build_dataset, STABLE_COLUMNS
from nz_date_dimension.emit_tsql import emit_tsql
from nz_date_dimension.columns import stable_columns

def test_emit_tsql_has_create_table_insert_and_view():
    rows = build_dataset(2025, 2025)  # 365 rows
    sql = emit_tsql(rows, fiscal_start_month=4)
    assert "CREATE TABLE" in sql
    assert "INSERT INTO" in sql
    assert "CREATE VIEW" in sql
    for col in STABLE_COLUMNS:
        assert col in sql, f"missing column {col}"
    # DateKey values are unique 8-digit ints -> reliable per-row row-count check.
    date_keys = set(re.findall(r"\b\d{8}\b", sql))
    assert len(date_keys) == 365

def test_emit_tsql_uses_bracket_quoted_identifiers_and_go_batches():
    rows = build_dataset(2025, 2025)
    sql = emit_tsql(rows)
    assert "[Date]" in sql
    assert "\nGO\n" in sql

def test_emit_tsql_christmas_row_is_holiday_and_not_business_day():
    rows = build_dataset(2025, 2025)
    sql = emit_tsql(rows)
    # Christmas 2025 row: DateKey 20251225, IsHoliday true (1), IsBusinessDay false (0).
    assert "'2025-12-25'" in sql

def test_emit_tsql_au_uses_au_table_name_and_columns():
    rows = build_dataset(2025, 2025, country="AU")
    au_cols = stable_columns(["AU"])
    sql = emit_tsql(rows, table_name="AUDateDimension", fiscal_start_month=7, columns=au_cols)
    assert "[AUDateDimension]" in sql
    assert "[IsHoliday_WA]" in sql
    assert "[IsHoliday_AUK]" not in sql

def test_emit_tsql_combined_uses_composite_primary_key():
    rows = build_dataset(2025, 2025, country="combined")
    combined_cols = stable_columns(["NZ", "AU"])
    sql = emit_tsql(rows, table_name="ANZDateDimension", columns=combined_cols,
                     primary_key=["Date", "Country"])
    pk_line = next(line for line in sql.splitlines() if "PRIMARY KEY" in line)
    assert "[Date]" in pk_line and "[Country]" in pk_line
    assert "[IsHoliday_NZ_AUK]" in sql and "[IsHoliday_AU_WA]" in sql
