"""Unit tests for the panchanga limbs (pure math + sunrise-based vara)."""
import pytest

from app.engine.ephemeris import BirthData, EngineConfig
from app.engine import panchanga as P


# ---------------------------------------------------------------------------
# Static name tables
# ---------------------------------------------------------------------------
def test_name_table_lengths():
    assert len(P.TITHI_NAMES) == 14           # + Purnima and Amavasya specials
    assert P.tithi_of(14 * 12 + 1)["name"] == "Purnima"
    assert P.tithi_of(29 * 12 + 1)["name"] == "Amavasya"
    assert len(P.VARA_NAMES) == 7
    assert len(P.VARA_LORDS) == 7
    assert len(P.YOGA_NAMES) == 27
    assert len(P.MOVABLE_KARANAS) == 7
    assert set(P.FIXED_KARANAS) == {0, 57, 58, 59}


# ---------------------------------------------------------------------------
# Tithi
# ---------------------------------------------------------------------------
def test_tithi_basics():
    assert P.tithi_of(0.0) == {"number": 1, "name": "Pratipada",
                               "paksha": "Shukla", "elongation": 0.0}
    assert P.tithi_of(11.99)["number"] == 1
    assert P.tithi_of(12.0)["number"] == 2
    t = P.tithi_of(180.0)
    assert t["number"] == 16 and t["paksha"] == "Krishna" and t["name"] == "Pratipada"


def test_tithi_elongation_near_360():
    t = P.tithi_of(359.9999)
    assert t["number"] == 30 and t["name"] == "Amavasya"
    assert P.tithi_of(360.0)["number"] == 1  # wraps to Pratipada
    assert P.tithi_of(-1.0)["number"] == 30  # negative elongation wraps


# ---------------------------------------------------------------------------
# Yoga
# ---------------------------------------------------------------------------
def test_yoga_edges():
    assert P.yoga_of(0.0)["name"] == "Vishkambha"
    assert P.yoga_of(13.34)["name"] == "Priti"
    assert P.yoga_of(359.999)["name"] == "Vaidhriti"
    assert P.yoga_of(360.0)["number"] == 1


# ---------------------------------------------------------------------------
# Karana edge cases: K = 0, 57, 58, 59, and the movable cycle
# ---------------------------------------------------------------------------
def test_karana_fixed():
    assert P.karana_of(0.0) == {"number": 0, "name": "Kimstughna"}
    assert P.karana_of(57 * 6 + 0.1) == {"number": 57, "name": "Shakuni"}
    assert P.karana_of(58 * 6 + 0.1) == {"number": 58, "name": "Chatushpada"}
    assert P.karana_of(59 * 6 + 0.1) == {"number": 59, "name": "Naga"}
    assert P.karana_of(359.9999)["name"] == "Naga"


def test_karana_movable_cycle():
    assert P.karana_of(6.1)["name"] == "Bava"       # K=1
    assert P.karana_of(12.1)["name"] == "Balava"    # K=2
    assert P.karana_of(48.1)["name"] == "Bava"      # K=8 -> cycle repeats
    assert P.karana_of(56 * 6 + 0.1)["name"] == "Vishti"  # K=56, last movable


# ---------------------------------------------------------------------------
# Vara: pre-sunrise birth belongs to the previous civil day's vara
# ---------------------------------------------------------------------------
WATFORD = dict(lat=51.656, lon=-0.396, tz_offset=1.0)


def test_vara_before_sunrise_is_previous_day():
    # 2026-07-04 is a Saturday; 01:25 is before the ~04:49 sunrise.
    pre = BirthData(date="2026-07-04", time="01:25:34", **WATFORD)
    p = P.compute_panchanga(pre, EngineConfig())
    assert p["vara"]["name"] == "Shukravara"          # Friday's Vedic day
    assert p["vara"]["lord"] == "Venus"
    assert p["sunrise"].startswith("2026-07-03T")


def test_vara_after_sunrise_is_same_day():
    post = BirthData(date="2026-07-04", time="12:00", **WATFORD)
    p = P.compute_panchanga(post, EngineConfig())
    assert p["vara"]["name"] == "Shanivara"           # Saturday
    assert p["vara"]["lord"] == "Saturn"
    assert p["sunrise"].startswith("2026-07-04T")
    assert p["sunset"].startswith("2026-07-04T")


def test_compute_panchanga_shape():
    b = BirthData(date="1990-05-15", time="06:30", lat=12.9716, lon=77.5946,
                  tz_offset=5.5)
    p = P.compute_panchanga(b, EngineConfig())
    assert 1 <= p["tithi"]["number"] <= 30
    assert p["vara"]["name"] in P.VARA_NAMES
    assert 1 <= p["nakshatra"]["pada"] <= 4
    assert 1 <= p["yoga"]["number"] <= 27
    assert 0 <= p["karana"]["number"] <= 59
    assert p["sunrise"] and p["sunset"]
