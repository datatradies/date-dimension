from datetime import date, timedelta
from .calendar_core import calendar_columns
from .fiscal import fiscal_columns
from .holidays_nz import build_national, national_holiday_columns, warn_if_beyond_matariki, NZ_SUBDIVISIONS
from .regional import build_regional, regional_columns

STABLE_COLUMNS = [
    "Date", "DateKey", "Year", "Quarter", "QuarterName", "Month", "MonthName",
    "MonthShort", "Day", "DayOfYear", "DayOfWeek", "DayName", "DayShort",
    "ISOWeek", "ISOWeekYear", "IsWeekend", "IsWeekday",
    "StartOfMonth", "EndOfMonth", "StartOfQuarter", "EndOfQuarter",
    "StartOfYear", "EndOfYear",
    "FiscalYear", "FiscalYearLabel", "FiscalQuarter", "FiscalMonth",
    "FiscalDayOfYear", "FiscalStartOfYear", "FiscalEndOfYear",
    "IsHoliday", "HolidayName", "IsObserved", "IsBusinessDay",
] + [f"IsHoliday_{code}" for code in NZ_SUBDIVISIONS]

def build_dataset(start_year: int, end_year: int, fiscal_start_month: int = 4) -> list:
    warn_if_beyond_matariki(end_year)
    national = build_national(start_year, end_year)
    regional = build_regional(start_year, end_year)
    rows = []
    d = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    while d <= end:
        cal = calendar_columns(d)
        row = {}
        row.update(cal)
        row.update(fiscal_columns(d, fiscal_start_month))
        row.update(national_holiday_columns(d, national, is_weekend=cal["IsWeekend"]))
        row.update(regional_columns(d, regional))
        rows.append(row)
        d += timedelta(days=1)
    return rows
