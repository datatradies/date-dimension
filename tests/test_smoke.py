import holidays

def test_python_holidays_has_new_zealand():
    nz = holidays.NewZealand(years=2025)
    # Christmas is a fixed anchor that must exist
    from datetime import date
    assert date(2025, 12, 25) in nz
