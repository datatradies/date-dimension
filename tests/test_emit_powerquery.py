import re
from nz_date_dimension.build import build_dataset, STABLE_COLUMNS
from nz_date_dimension.relative import RELATIVE_COLUMNS
from nz_date_dimension.emit_powerquery import emit_powerquery

def test_emit_powerquery_has_let_in_and_source_table():
    rows = build_dataset(2025, 2025)  # 365 rows
    m = emit_powerquery(rows, fiscal_start_month=4)
    assert m.strip().startswith("let")
    assert "#table(" in m
    assert "DateTime.LocalNow()" in m

def test_emit_powerquery_includes_every_stable_and_relative_column():
    rows = build_dataset(2025, 2025)
    m = emit_powerquery(rows)
    for col in STABLE_COLUMNS:
        assert f'"{col}"' in m, f"missing stable column header {col}"
    for col in RELATIVE_COLUMNS:
        assert f'"{col}"' in m, f"missing relative column {col}"
        assert f'Table.AddColumn(' in m

def test_emit_powerquery_row_count_matches_dataset():
    rows = build_dataset(2025, 2025)
    m = emit_powerquery(rows)
    date_keys = set(re.findall(r"\b\d{8}\b", m))
    assert len(date_keys) == 365

def test_emit_powerquery_last_step_is_the_final_relative_column():
    rows = build_dataset(2025, 2025)
    m = emit_powerquery(rows)
    last_line = m.strip().splitlines()[-1].strip()
    assert last_line == f"Add{RELATIVE_COLUMNS[-1]}"
