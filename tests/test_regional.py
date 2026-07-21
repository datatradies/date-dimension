from datetime import date
from nz_date_dimension.regional import build_regional, regional_columns
from nz_date_dimension.holidays_nz import NZ_SUBDIVISIONS

def test_one_column_per_subdivision():
    reg = build_regional(2025, 2025)
    c = regional_columns(date(2025, 7, 23), reg)
    for code in NZ_SUBDIVISIONS:
        assert f"IsHoliday_{code}" in c

def test_auckland_anniversary_flags_auckland_only():
    # Auckland Anniversary 2025 = Monday 27 Jan 2025
    reg = build_regional(2025, 2025)
    c = regional_columns(date(2025, 1, 27), reg)
    assert c["IsHoliday_AUK"] is True
    assert c["IsHoliday_WGN"] is False   # not Wellington's anniversary

def test_national_holiday_flags_all_regions():
    reg = build_regional(2025, 2025)
    c = regional_columns(date(2025, 12, 25), reg)  # Christmas = national
    assert c["IsHoliday_AUK"] is True and c["IsHoliday_WGN"] is True
