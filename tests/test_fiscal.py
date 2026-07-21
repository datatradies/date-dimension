from datetime import date
from nz_date_dimension.fiscal import fiscal_columns, fiscal_year

def test_april_is_start_of_fiscal_year():
    f = fiscal_columns(date(2025, 4, 1))
    assert f["FiscalYear"] == 2026            # FY ending 31 Mar 2026
    assert f["FiscalYearLabel"] == "FY2026"
    assert f["FiscalQuarter"] == 1 and f["FiscalMonth"] == 1
    assert f["FiscalDayOfYear"] == 1
    assert f["FiscalStartOfYear"] == date(2025, 4, 1)
    assert f["FiscalEndOfYear"] == date(2026, 3, 31)

def test_march_is_end_of_fiscal_year():
    f = fiscal_columns(date(2026, 3, 31))
    assert f["FiscalYear"] == 2026 and f["FiscalMonth"] == 12 and f["FiscalQuarter"] == 4

def test_fiscal_year_helper():
    assert fiscal_year(date(2025, 12, 1)) == 2026
    assert fiscal_year(date(2025, 1, 1)) == 2025
