import re
from nz_date_dimension.build import build_dataset, STABLE_COLUMNS
from nz_date_dimension.emit_databricks import emit_databricks

def test_emit_databricks_has_create_table_insert_and_view():
    rows = build_dataset(2025, 2025)
    sql = emit_databricks(rows, fiscal_start_month=4)
    assert "CREATE TABLE" in sql
    assert "INSERT INTO" in sql
    assert "CREATE VIEW" in sql
    for col in STABLE_COLUMNS:
        assert col in sql, f"missing column {col}"
    date_keys = set(re.findall(r"\b\d{8}\b", sql))
    assert len(date_keys) == 365

def test_emit_databricks_uses_backtick_identifiers_and_native_booleans():
    rows = build_dataset(2025, 2025)
    sql = emit_databricks(rows)
    assert "`Date`" in sql
    assert "TRUE" in sql and "FALSE" in sql
    assert "current_date()" in sql
    assert "dayofweek(" in sql
