from nz_date_dimension.columns import (
    BASE_COLUMNS, stable_columns, regional_flag_columns, seed_columns,
)
from nz_date_dimension.countries import NZ_SUBDIVISIONS, AU_SUBDIVISIONS

# The exact original STABLE_COLUMNS list (pre-refactor), used to prove the
# NZ-only case is byte-for-byte unchanged after the dynamic-columns refactor.
_ORIGINAL_NZ_STABLE_COLUMNS = [
    "Date", "DateKey", "Year", "Quarter", "QuarterName", "Month", "MonthName",
    "MonthShort", "Day", "DayOfYear", "DayOfWeek", "DayName", "DayShort",
    "ISOWeek", "ISOWeekYear", "IsWeekend", "IsWeekday",
    "StartOfMonth", "EndOfMonth", "StartOfQuarter", "EndOfQuarter",
    "StartOfYear", "EndOfYear",
    "FiscalYear", "FiscalYearLabel", "FiscalQuarter", "FiscalMonth",
    "FiscalDayOfYear", "FiscalStartOfYear", "FiscalEndOfYear",
    "IsHoliday", "HolidayName", "IsObserved", "IsBusinessDay",
] + [f"IsHoliday_{code}" for code in NZ_SUBDIVISIONS]

def test_regional_flag_columns_single_country_is_bare():
    cols = regional_flag_columns(["NZ"])
    assert cols == [f"IsHoliday_{code}" for code in NZ_SUBDIVISIONS]
    cols = regional_flag_columns(["AU"])
    assert cols == [f"IsHoliday_{code}" for code in AU_SUBDIVISIONS]

def test_regional_flag_columns_combined_is_country_prefixed():
    cols = regional_flag_columns(["NZ", "AU"])
    assert cols == (
        [f"IsHoliday_NZ_{code}" for code in NZ_SUBDIVISIONS]
        + [f"IsHoliday_AU_{code}" for code in AU_SUBDIVISIONS]
    )
    # No bare (unprefixed) IsHoliday_<code> columns leak into combined mode.
    for col in cols:
        assert col.startswith("IsHoliday_NZ_") or col.startswith("IsHoliday_AU_")

def test_stable_columns_nz_is_byte_identical_to_pre_refactor_list():
    assert stable_columns(["NZ"]) == _ORIGINAL_NZ_STABLE_COLUMNS

def test_stable_columns_nz_has_no_country_column():
    assert "Country" not in stable_columns(["NZ"])

def test_stable_columns_au_has_8_bare_state_flags_and_no_country_column():
    cols = stable_columns(["AU"])
    assert "Country" not in cols
    for code in AU_SUBDIVISIONS:
        assert f"IsHoliday_{code}" in cols
    assert len(AU_SUBDIVISIONS) == 8

def test_stable_columns_combined_has_country_right_after_datekey():
    cols = stable_columns(["NZ", "AU"])
    assert cols[0] == "Date"
    assert cols[1] == "DateKey"
    assert cols[2] == "Country"
    assert cols[3] == "Year"

def test_stable_columns_combined_has_union_of_prefixed_regional_flags():
    cols = stable_columns(["NZ", "AU"])
    for code in NZ_SUBDIVISIONS:
        assert f"IsHoliday_NZ_{code}" in cols
        assert f"IsHoliday_{code}" not in cols  # bare form must not also be present
    for code in AU_SUBDIVISIONS:
        assert f"IsHoliday_AU_{code}" in cols

def test_base_columns_do_not_include_regional_or_country():
    assert "Country" not in BASE_COLUMNS
    assert not any(c.startswith("IsHoliday_") for c in BASE_COLUMNS)
    assert "IsHoliday" in BASE_COLUMNS  # the core (non-regional) holiday column stays

def test_seed_columns_single_country_nz_matches_legacy_shape():
    cols = seed_columns(["NZ"])
    assert cols == (
        ["Date", "IsHoliday", "HolidayName", "IsObserved"]
        + [f"IsHoliday_{code}" for code in NZ_SUBDIVISIONS]
    )

def test_seed_columns_combined_includes_country():
    cols = seed_columns(["NZ", "AU"])
    assert cols[:5] == ["Date", "Country", "IsHoliday", "HolidayName", "IsObserved"]
    assert f"IsHoliday_NZ_{NZ_SUBDIVISIONS[0]}" in cols
    assert f"IsHoliday_AU_{AU_SUBDIVISIONS[0]}" in cols
