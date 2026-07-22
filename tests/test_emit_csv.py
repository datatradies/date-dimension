import csv
from datetime import date
from nz_date_dimension.build import build_dataset
from nz_date_dimension.emit_csv import write_csv
from nz_date_dimension.columns import stable_columns

def test_write_csv_roundtrip(tmp_path):
    rows = build_dataset(2025, 2025)
    out = tmp_path / "nz.csv"
    write_csv(rows, str(out), generated_on=date(2026, 7, 22))
    with open(out, newline="", encoding="utf-8") as f:
        read = list(csv.DictReader(f))
    assert len(read) == 365
    assert read[0]["Date"] == "2025-01-01"
    assert read[0]["GeneratedOn"] == "2026-07-22"
    xmas = next(r for r in read if r["Date"] == "2025-12-25")
    assert xmas["IsBusinessDay"] == "false" and xmas["IsHoliday"] == "true"

def test_write_csv_honours_explicit_columns_argument_for_au(tmp_path):
    rows = build_dataset(2025, 2025, country="AU")
    cols = stable_columns(["AU"])
    out = tmp_path / "au.csv"
    write_csv(rows, str(out), generated_on=date(2026, 7, 22), columns=cols)
    with open(out, newline="", encoding="utf-8") as f:
        read = list(csv.DictReader(f))
    assert len(read) == 365
    assert "IsHoliday_WA" in read[0]
    assert "IsHoliday_AUK" not in read[0]  # NZ-only column absent from AU CSV

def test_write_csv_honours_explicit_columns_argument_for_combined(tmp_path):
    rows = build_dataset(2025, 2025, country="combined")
    cols = stable_columns(["NZ", "AU"])
    out = tmp_path / "anz.csv"
    write_csv(rows, str(out), generated_on=date(2026, 7, 22), columns=cols)
    with open(out, newline="", encoding="utf-8") as f:
        read = list(csv.DictReader(f))
    assert len(read) == 730
    assert "Country" in read[0]
    assert {r["Country"] for r in read} == {"NZ", "AU"}
