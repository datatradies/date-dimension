from datetime import date, timedelta

def _fiscal_start_of_year(d: date, start_month: int = 4) -> date:
    """The most recent (start_month, 1) on or before d."""
    year = d.year if d.month >= start_month else d.year - 1
    return date(year, start_month, 1)

def _fiscal_end_of_year(start: date) -> date:
    """One day before the next fiscal year's start (start + 1 year - 1 day)."""
    return date(start.year + 1, start.month, 1) - timedelta(days=1)

def fiscal_year(d: date, start_month: int = 4) -> int:
    """Year the fiscal year ENDS in (FY2026 = 1 Apr 2025 - 31 Mar 2026).

    Consistent for any start_month (1-12): FiscalYear is always derived
    from FiscalEndOfYear.year, so the label can never disagree with the
    computed start/end dates.
    """
    start = _fiscal_start_of_year(d, start_month)
    return _fiscal_end_of_year(start).year

def fiscal_columns(d: date, start_month: int = 4) -> dict:
    start = _fiscal_start_of_year(d, start_month)
    end = _fiscal_end_of_year(start)
    fy = end.year
    fiscal_month = (d.month - start_month) % 12 + 1
    return {
        "FiscalYear": fy,
        "FiscalYearLabel": f"FY{fy}",
        "FiscalQuarter": (fiscal_month - 1) // 3 + 1,
        "FiscalMonth": fiscal_month,
        "FiscalDayOfYear": (d - start).days + 1,
        "FiscalStartOfYear": start,
        "FiscalEndOfYear": end,
    }
