from datetime import date
from nz_date_dimension.regional import build_regional, regional_columns
from nz_date_dimension.countries import NZ, AU, NZ_SUBDIVISIONS, AU_SUBDIVISIONS

# --- NZ (unchanged behaviour, now via the country-parameterised API) ---

def test_one_column_per_subdivision():
    reg = build_regional(NZ, 2025, 2025)
    c = regional_columns(date(2025, 7, 23), reg)
    for code in NZ_SUBDIVISIONS:
        assert f"IsHoliday_{code}" in c

def test_auckland_anniversary_flags_auckland_only():
    # Auckland Anniversary 2025 = Monday 27 Jan 2025
    reg = build_regional(NZ, 2025, 2025)
    c = regional_columns(date(2025, 1, 27), reg)
    assert c["IsHoliday_AUK"] is True
    assert c["IsHoliday_WGN"] is False   # not Wellington's anniversary

def test_national_holiday_flags_all_regions():
    reg = build_regional(NZ, 2025, 2025)
    c = regional_columns(date(2025, 12, 25), reg)  # Christmas = national
    assert c["IsHoliday_AUK"] is True and c["IsHoliday_WGN"] is True

# --- AU: 8 states, bare flags for single-country output ---

def test_au_one_column_per_state():
    reg = build_regional(AU, 2025, 2025)
    c = regional_columns(date(2025, 7, 23), reg)
    for code in AU_SUBDIVISIONS:
        assert f"IsHoliday_{code}" in c
    assert len(AU_SUBDIVISIONS) == 8

def test_au_melbourne_cup_flags_vic_only():
    # Melbourne Cup 2025 = 1st Tue Nov = 4 Nov 2025, VIC-only.
    reg = build_regional(AU, 2025, 2025)
    c = regional_columns(date(2025, 11, 4), reg)
    assert c["IsHoliday_VIC"] is True
    for code in AU_SUBDIVISIONS:
        if code != "VIC":
            assert c[f"IsHoliday_{code}"] is False, f"{code} should not observe Melbourne Cup"

def test_au_wa_labour_day_flags_wa_only():
    # WA Labour Day 2025 = 1st Mon Mar = 3 Mar 2025. No other state's
    # Labour Day (or any national holiday) falls on that date in 2025.
    reg = build_regional(AU, 2025, 2025)
    c = regional_columns(date(2025, 3, 3), reg)
    assert c["IsHoliday_WA"] is True
    for code in AU_SUBDIVISIONS:
        if code != "WA":
            assert c[f"IsHoliday_{code}"] is False, f"{code} should not be a holiday on WA Labour Day"

def test_au_national_holiday_flags_all_states():
    reg = build_regional(AU, 2025, 2025)
    c = regional_columns(date(2025, 12, 25), reg)  # Christmas = national
    for code in AU_SUBDIVISIONS:
        assert c[f"IsHoliday_{code}"] is True

# --- Combined: country-prefixed flags (spec §7 resolution: TAS collision) ---

def test_prefix_produces_country_prefixed_column_names():
    reg = build_regional(NZ, 2025, 2025)
    c = regional_columns(date(2025, 1, 27), reg, prefix="NZ")
    assert "IsHoliday_NZ_AUK" in c
    assert "IsHoliday_AUK" not in c  # bare form must not also appear
    assert c["IsHoliday_NZ_AUK"] is True

def test_prefix_avoids_tas_collision_between_nz_and_au():
    # NZ's Taranaki and AU's Tasmania both use the code "TAS" -- prefixing
    # keeps them distinct columns.
    nz_reg = build_regional(NZ, 2025, 2025)
    au_reg = build_regional(AU, 2025, 2025)
    nz_c = regional_columns(date(2025, 3, 10), nz_reg, prefix="NZ")
    au_c = regional_columns(date(2025, 3, 10), au_reg, prefix="AU")
    assert "IsHoliday_NZ_TAS" in nz_c
    assert "IsHoliday_AU_TAS" in au_c
    combined = {**nz_c, **au_c}
    assert "IsHoliday_NZ_TAS" in combined and "IsHoliday_AU_TAS" in combined
    assert len(combined) == len(nz_c) + len(au_c)  # no key collision
