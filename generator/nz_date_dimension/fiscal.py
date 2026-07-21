from datetime import date, timedelta

def fiscal_year(d: date, start_month: int = 4) -> int:
    """Year the NZ fiscal year ENDS in (FY2026 = 1 Apr 2025 - 31 Mar 2026)."""
    return d.year + 1 if d.month >= start_month else d.year

def fiscal_columns(d: date, start_month: int = 4) -> dict:
    fy = fiscal_year(d, start_month)
    fiscal_month = (d.month - start_month) % 12 + 1
    start = date(fy - 1, start_month, 1)
    end = date(fy, start_month, 1) - timedelta(days=1)
    return {
        "FiscalYear": fy,
        "FiscalYearLabel": f"FY{fy}",
        "FiscalQuarter": (fiscal_month - 1) // 3 + 1,
        "FiscalMonth": fiscal_month,
        "FiscalDayOfYear": (d - start).days + 1,
        "FiscalStartOfYear": start,
        "FiscalEndOfYear": end,
    }
