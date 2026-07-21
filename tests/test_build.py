from datetime import date
from nz_date_dimension.build import build_dataset, STABLE_COLUMNS

def test_dataset_spans_every_day_inclusive():
    rows = build_dataset(2024, 2024)
    assert len(rows) == 366          # 2024 is a leap year
    assert rows[0]["Date"] == date(2024, 1, 1)
    assert rows[-1]["Date"] == date(2024, 12, 31)

def test_rows_carry_all_stable_columns():
    row = build_dataset(2025, 2025)[0]
    for col in STABLE_COLUMNS:
        assert col in row, f"missing {col}"

def test_business_day_false_on_christmas():
    rows = {r["Date"]: r for r in build_dataset(2025, 2025)}
    assert rows[date(2025, 12, 25)]["IsBusinessDay"] is False

def test_warns_beyond_2052(recwarn):
    build_dataset(2052, 2053)
    assert any("Matariki" in str(w.message) for w in recwarn.list)
