from datetime import date
import holidays
from .holidays_nz import NZ_SUBDIVISIONS

def build_regional(start_year: int, end_year: int) -> dict:
    return {
        code: holidays.NewZealand(subdiv=code, years=range(start_year, end_year + 1),
                                  observed=True)
        for code in NZ_SUBDIVISIONS
    }

def regional_columns(d: date, regional: dict) -> dict:
    # IsHoliday_<CODE> = public holiday in that subdivision (national + its anniversary)
    return {f"IsHoliday_{code}": (d in hol) for code, hol in regional.items()}
