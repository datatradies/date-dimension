from datetime import date
from nz_date_dimension.calendar_core import calendar_columns

def test_calendar_columns_for_a_known_wednesday():
    c = calendar_columns(date(2025, 7, 23))  # a Wednesday
    assert c["Date"] == date(2025, 7, 23)
    assert c["DateKey"] == 20250723
    assert c["Year"] == 2025
    assert c["Quarter"] == 3 and c["QuarterName"] == "Q3"
    assert c["Month"] == 7 and c["MonthName"] == "July" and c["MonthShort"] == "Jul"
    assert c["Day"] == 23 and c["DayOfYear"] == 204
    assert c["DayOfWeek"] == 3 and c["DayName"] == "Wednesday" and c["DayShort"] == "Wed"
    assert c["IsWeekday"] is True and c["IsWeekend"] is False
    assert c["StartOfMonth"] == date(2025, 7, 1) and c["EndOfMonth"] == date(2025, 7, 31)
    assert c["StartOfQuarter"] == date(2025, 7, 1) and c["EndOfQuarter"] == date(2025, 9, 30)
    assert c["StartOfYear"] == date(2025, 1, 1) and c["EndOfYear"] == date(2025, 12, 31)

def test_weekend_flag():
    assert calendar_columns(date(2025, 7, 26))["IsWeekend"] is True  # Saturday
