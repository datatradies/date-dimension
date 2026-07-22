from datetime import date
from .countries import CountryConfig

def build_regional(country: CountryConfig, start_year: int, end_year: int) -> dict:
    return {
        code: country.holidays_class(subdiv=code, years=range(start_year, end_year + 1),
                                      observed=True)
        for code in country.subdivisions
    }

def regional_columns(d: date, regional: dict, prefix: str = None) -> dict:
    """IsHoliday_<CODE> = public holiday in that subdivision (national + its
    own regional day). `prefix` country-prefixes the column names
    (IsHoliday_<PREFIX>_<CODE>) for Combined mode, where NZ's Taranaki and
    AU's Tasmania would otherwise collide on the shared code "TAS".
    """
    def key(code: str) -> str:
        return f"IsHoliday_{prefix}_{code}" if prefix else f"IsHoliday_{code}"
    return {key(code): (d in hol) for code, hol in regional.items()}
