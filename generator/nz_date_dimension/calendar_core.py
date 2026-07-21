from datetime import date, timedelta

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _end_of_month(d: date) -> date:
    first_next = date(d.year + (d.month // 12), (d.month % 12) + 1, 1)
    return first_next - timedelta(days=1)

def calendar_columns(d: date) -> dict:
    iso_year, iso_week, iso_weekday = d.isocalendar()
    quarter = (d.month - 1) // 3 + 1
    q_start_month = (quarter - 1) * 3 + 1
    start_of_quarter = date(d.year, q_start_month, 1)
    end_of_quarter = _end_of_month(date(d.year, q_start_month + 2, 1))
    return {
        "Date": d,
        "DateKey": d.year * 10000 + d.month * 100 + d.day,
        "Year": d.year,
        "Quarter": quarter,
        "QuarterName": f"Q{quarter}",
        "Month": d.month,
        "MonthName": MONTH_NAMES[d.month],
        "MonthShort": MONTH_NAMES[d.month][:3],
        "Day": d.day,
        "DayOfYear": d.timetuple().tm_yday,
        "DayOfWeek": iso_weekday,
        "DayName": DAY_NAMES[iso_weekday - 1],
        "DayShort": DAY_NAMES[iso_weekday - 1][:3],
        "ISOWeek": iso_week,
        "ISOWeekYear": iso_year,
        "IsWeekend": iso_weekday >= 6,
        "IsWeekday": iso_weekday < 6,
        "StartOfMonth": date(d.year, d.month, 1),
        "EndOfMonth": _end_of_month(d),
        "StartOfQuarter": start_of_quarter,
        "EndOfQuarter": end_of_quarter,
        "StartOfYear": date(d.year, 1, 1),
        "EndOfYear": date(d.year, 12, 31),
    }
