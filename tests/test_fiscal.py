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

def test_calendar_year_fiscal_start_month_1():
    # start_month=1 is a plain calendar year: FY label = the calendar year,
    # and the year ends 31 Dec (not 31 Dec of the *following* year).
    f = fiscal_columns(date(2025, 6, 1), start_month=1)
    assert f["FiscalYear"] == 2025
    assert f["FiscalYearLabel"] == "FY2025"
    assert f["FiscalStartOfYear"] == date(2025, 1, 1)
    assert f["FiscalEndOfYear"] == date(2025, 12, 31)
    assert fiscal_year(date(2025, 6, 1), start_month=1) == 2025

def test_australian_fiscal_start_month_7():
    # start_month=7 (AU convention): 1 Aug 2025 falls in the fiscal year
    # that starts 1 Jul 2025 and ends 30 Jun 2026, i.e. FY2026.
    f = fiscal_columns(date(2025, 8, 1), start_month=7)
    assert f["FiscalYear"] == 2026
    assert f["FiscalYearLabel"] == "FY2026"
    assert f["FiscalStartOfYear"] == date(2025, 7, 1)
    assert f["FiscalEndOfYear"] == date(2026, 6, 30)
    assert fiscal_year(date(2025, 8, 1), start_month=7) == 2026
