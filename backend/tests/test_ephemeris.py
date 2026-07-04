"""Sidereal positions vs independently published values; ayanamsa sanity;
nakshatra boundaries; empirical lagna-method cross-check."""
import swisseph as swe

from app.engine.ephemeris import (
    EngineConfig, ascendant, ayanamsa_value, julian_day, nakshatra_of,
    planet_longitudes,
)

JD_REF = julian_day("2026-07-03", "12:00", 0.0)  # 2026-07-03 12:00 UT
CFG = EngineConfig()


def test_reference_positions_2026_07_03():
    pos = planet_longitudes(JD_REF, CFG)
    assert abs(pos["Sun"]["longitude"] - 77.36) < 0.1
    assert abs(pos["Moon"]["longitude"] - 296.25) < 0.1
    assert abs(pos["Rahu"]["longitude"] - 308.22) < 0.1  # mean node
    # Ketu is exactly opposite Rahu
    assert abs((pos["Ketu"]["longitude"] - pos["Rahu"]["longitude"]) % 360.0 - 180.0) < 1e-9


def test_ayanamsa_lahiri_2026():
    assert abs(ayanamsa_value(JD_REF, CFG) - 24.227) < 0.01


def test_speed_and_retrograde_flags():
    pos = planet_longitudes(JD_REF, CFG)
    assert pos["Sun"]["speed"] > 0 and not pos["Sun"]["retrograde"]
    assert pos["Rahu"]["speed"] < 0 and pos["Rahu"]["retrograde"]  # mean node regresses


def test_nakshatra_boundaries():
    assert nakshatra_of(0.0)["name"] == "Ashwini"
    assert nakshatra_of(0.0)["pada"] == 1
    assert nakshatra_of(0.0)["lord"] == "Ketu"
    assert nakshatra_of(13.3333)["name"] == "Ashwini"      # just below boundary
    assert nakshatra_of(13.3334)["name"] == "Bharani"      # just above
    assert nakshatra_of(13.3334)["lord"] == "Venus"
    assert nakshatra_of(93.3334)["name"] == "Pushya"
    assert nakshatra_of(93.3334)["lord"] == "Saturn"
    assert nakshatra_of(359.9)["name"] == "Revati"
    assert nakshatra_of(359.9)["pada"] == 4
    assert nakshatra_of(360.0)["name"] == "Ashwini"        # wraps
    # pada boundary: 3°20' into Ashwini -> pada 2
    assert nakshatra_of(3.3334)["pada"] == 2


def test_sidereal_lagna_method_cross_check():
    """houses_ex(..., FLG_SIDEREAL) must agree with tropical asc minus
    ayanamsa (the two independent computations of the sidereal lagna)."""
    lat, lon = 28.6139, 77.2090  # Delhi
    asc = ascendant(JD_REF, lat, lon, CFG)
    CFG.apply_sid_mode()
    _cusps, ascmc = swe.houses(JD_REF, lat, lon, b"W")
    manual = (ascmc[0] - swe.get_ayanamsa_ut(JD_REF)) % 360.0
    diff = abs((asc["longitude"] - manual + 180.0) % 360.0 - 180.0)
    assert diff < 0.01


def test_julian_day_tz_offset():
    # 17:30 IST (+5.5) == 12:00 UT
    assert abs(julian_day("2026-07-03", "17:30", 5.5) - JD_REF) < 1e-9
