"""Dynamic column derivation (spec §7 resolution: "the refactor must derive
columns dynamically from the dataset/country config" -- STABLE_COLUMNS/
SEED_COLUMNS used to hardcode NZ_SUBDIVISIONS and were imported by every
emitter; this module is now the single source of truth those emitters (and
build.py) derive their column list from, for NZ, AU, or Combined.

Single-country outputs (NZ or AU) keep bare `IsHoliday_<code>` flags -- this
is what makes the NZ CSV byte-identical after the refactor. Combined output
country-prefixes the flags (`IsHoliday_NZ_<code>` / `IsHoliday_AU_<code>`)
to avoid the TAS collision (NZ Taranaki vs AU Tasmania share the code "TAS").
"""
from typing import List, Sequence
from .countries import get_country

# The country-agnostic calendar/fiscal/national-holiday columns, identical
# for every country and shared unchanged between single-country and
# Combined datasets. Order is significant -- this is the pre-refactor
# STABLE_COLUMNS list verbatim, minus the regional flags (which are now
# derived separately by country) and minus the Combined-only Country column
# (inserted by stable_columns() below, only when there's more than one
# country in play).
BASE_COLUMNS: List[str] = [
    "Date", "DateKey", "Year", "Quarter", "QuarterName", "Month", "MonthName",
    "MonthShort", "Day", "DayOfYear", "DayOfWeek", "DayName", "DayShort",
    "ISOWeek", "ISOWeekYear", "IsWeekend", "IsWeekday",
    "StartOfMonth", "EndOfMonth", "StartOfQuarter", "EndOfQuarter",
    "StartOfYear", "EndOfYear",
    "FiscalYear", "FiscalYearLabel", "FiscalQuarter", "FiscalMonth",
    "FiscalDayOfYear", "FiscalStartOfYear", "FiscalEndOfYear",
    "IsHoliday", "HolidayName", "IsObserved", "IsBusinessDay",
]

def regional_flag_columns(country_codes: Sequence[str]) -> List[str]:
    """The IsHoliday_<code> regional/state flag columns for the given
    country code(s). A single country keeps its codes bare (NZ stays
    byte-identical); more than one country gets each code prefixed with
    its own country code (avoids the NZ Taranaki / AU Tasmania "TAS"
    collision in Combined mode).
    """
    if len(country_codes) <= 1:
        if not country_codes:
            return []
        country = get_country(country_codes[0])
        return [f"IsHoliday_{code}" for code in country.subdivisions]
    cols: List[str] = []
    for cc in country_codes:
        country = get_country(cc)
        cols.extend(f"IsHoliday_{cc}_{code}" for code in country.subdivisions)
    return cols

def stable_columns(country_codes: Sequence[str]) -> List[str]:
    """Full STABLE_COLUMNS-equivalent list for the given country code(s).

    - `["NZ"]` -> the exact pre-refactor NZ STABLE_COLUMNS list (regression
      guard: NZ CSV output must stay byte-identical).
    - `["AU"]` -> the same base columns + AU's 8 bare state flags.
    - `["NZ", "AU"]` (Combined) -> base columns with a `Country` column
      inserted right after `DateKey` (adjacent to `Date`, matching the
      Combined SQL composite PK `(Date, Country)`), plus the country-
      prefixed union of both countries' regional flags.
    """
    cols = list(BASE_COLUMNS)
    if len(country_codes) > 1:
        cols = cols[:2] + ["Country"] + cols[2:]
    cols += regional_flag_columns(country_codes)
    return cols

def seed_columns(country_codes: Sequence[str]) -> List[str]:
    """The dbt seed's column list -- the holiday/regional lookup only (no
    calendar/fiscal columns, which the dbt model derives itself from the
    date_spine). Mirrors stable_columns()'s Country-insertion and flag-
    prefixing rules for consistency.
    """
    cols = ["Date"]
    if len(country_codes) > 1:
        cols.append("Country")
    cols += ["IsHoliday", "HolidayName", "IsObserved"]
    cols += regional_flag_columns(country_codes)
    return cols
