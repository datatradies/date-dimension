from datetime import date
from nz_date_dimension.holidays_nz import build_national, national_holiday_columns, NZ_SUBDIVISIONS

def cols(d, y0, y1):
    nat = build_national(y0, y1)
    return national_holiday_columns(d, nat, is_weekend=d.isoweekday() >= 6)

def test_christmas_is_holiday_and_not_business_day():
    c = cols(date(2025, 12, 25), 2025, 2025)
    assert c["IsHoliday"] is True and c["IsBusinessDay"] is False
    assert "Christmas" in c["HolidayName"]

def test_waitangi_mondayisation_2021():
    # 6 Feb 2021 was a Saturday -> observed Monday 8 Feb 2021
    observed = cols(date(2021, 2, 8), 2021, 2021)
    assert observed["IsHoliday"] is True
    assert observed["IsObserved"] is True
    assert observed["IsBusinessDay"] is False

def test_waitangi_actual_weekend_date_is_not_observed():
    # 6 Feb 2021 was a Saturday: the holiday is present that day, but
    # IsObserved is only true on the transferred (Monday) day, per the
    # pinned "(observed)" detection in holidays_nz.py.
    actual = cols(date(2021, 2, 6), 2021, 2021)
    assert actual["IsHoliday"] is True
    assert actual["IsObserved"] is False
    assert actual["IsBusinessDay"] is False  # still a weekend

def test_new_year_mondayisation_2022():
    # Verified against holidays==0.101: NewZealand(years=2022, observed=True) ->
    # 2022-01-01 (Sat) "New Year's Day", 2022-01-02 (Sun) "Day after New Year's Day",
    # 2022-01-03 (Mon) "New Year's Day (observed)", 2022-01-04 (Tue) "Day after
    # New Year's Day (observed)".
    for observed_day in (date(2022, 1, 3), date(2022, 1, 4)):
        c = cols(observed_day, 2022, 2022)
        assert c["IsHoliday"] is True
        assert c["IsObserved"] is True
        assert c["IsBusinessDay"] is False

def test_christmas_boxing_mondayisation_2021():
    # Verified against holidays==0.101: NewZealand(years=2021, observed=True) ->
    # 2021-12-25 (Sat) "Christmas Day", 2021-12-26 (Sun) "Boxing Day",
    # 2021-12-27 (Mon) "Christmas Day (observed)", 2021-12-28 (Tue) "Boxing Day (observed)".
    for observed_day in (date(2021, 12, 27), date(2021, 12, 28)):
        c = cols(observed_day, 2021, 2021)
        assert c["IsHoliday"] is True
        assert c["IsObserved"] is True
        assert c["IsBusinessDay"] is False
    # The actual weekend dates carry the holiday but are not the observed day.
    assert cols(date(2021, 12, 25), 2021, 2021)["IsObserved"] is False
    assert cols(date(2021, 12, 26), 2021, 2021)["IsObserved"] is False

def test_matariki_2022():
    assert cols(date(2022, 6, 24), 2022, 2022)["IsHoliday"] is True

def test_matariki_not_before_2022():
    assert cols(date(2021, 6, 24), 2021, 2021)["IsHoliday"] is False

def test_qe2_memorial_one_off_2022():
    assert cols(date(2022, 9, 26), 2022, 2022)["IsHoliday"] is True

def test_ordinary_weekday_is_business_day():
    c = cols(date(2025, 7, 23), 2025, 2025)
    assert c["IsHoliday"] is False and c["IsBusinessDay"] is True

def test_there_are_17_subdivisions():
    assert len(NZ_SUBDIVISIONS) == 17
