"""Engine vs an independent Drik Panchang capture (Lahiri, mean nodes).

Reference: 2026-07-04 01:25:34 local (UTC+1), Watford UK. Fixture:
fixtures/drik_panchang_20260704.json. Grahas must agree within 2 arcmin,
lagna within 0.5 deg; the panchanga limbs must match values derived
arithmetically from the reference longitudes (see fixture notes).
"""
import json
from pathlib import Path

import pytest

from app.engine.ephemeris import (
    BirthData, EngineConfig, ascendant, julian_day_from_utc, planet_longitudes,
)
from app.engine.panchanga import compute_panchanga

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "drik_panchang_20260704.json").read_text()
)


@pytest.fixture(scope="module")
def computed():
    b = BirthData(**FIXTURE["birth"])
    cfg = EngineConfig(ayanamsa="lahiri", node_type="mean")
    jd = julian_day_from_utc(b.utc_datetime())
    return {
        "positions": planet_longitudes(jd, cfg),
        "lagna": ascendant(jd, b.lat, b.lon, cfg),
        "panchanga": compute_panchanga(b, cfg),
    }


def _angdiff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


@pytest.mark.parametrize("graha", list(FIXTURE["positions_deg"].keys()))
def test_graha_within_two_arcmin(computed, graha):
    expected = FIXTURE["positions_deg"][graha]
    got = computed["positions"][graha]["longitude"]
    tol = FIXTURE["tolerances"]["planet_deg"]
    assert _angdiff(got, expected) <= tol, f"{graha}: {got} vs {expected}"


def test_mercury_retrograde(computed):
    for graha in FIXTURE["retrograde"]:
        assert computed["positions"][graha]["retrograde"]
    assert not computed["positions"]["Sun"]["retrograde"]
    assert not computed["positions"]["Moon"]["retrograde"]


def test_lagna(computed):
    lag = computed["lagna"]
    assert lag["sign_name"] == FIXTURE["lagna"]["sign_name"]
    assert abs(lag["degree_in_sign"] - FIXTURE["lagna"]["degree_in_sign"]) \
        <= FIXTURE["tolerances"]["lagna_deg"]


def test_panchanga_matches_reference(computed):
    p = computed["panchanga"]
    ref = FIXTURE["panchanga"]
    assert p["nakshatra"]["name"] == ref["nakshatra"]
    assert p["nakshatra"]["pada"] == ref["pada"]
    assert p["tithi"]["number"] == ref["tithi_number"]
    assert p["tithi"]["name"] == ref["tithi_name"]
    assert p["tithi"]["paksha"] == ref["paksha"]
    assert p["yoga"]["number"] == ref["yoga_number"]
    assert p["yoga"]["name"] == ref["yoga_name"]
    assert p["karana"]["number"] == ref["karana_number"]
    assert p["karana"]["name"] == ref["karana_name"]
    assert p["vara"]["name"] == ref["vara"]
