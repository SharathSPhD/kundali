"""Predictions integration: shadbala weighting + varga corroboration facts."""
from datetime import datetime

import pytest

from app.engine.ephemeris import BirthData
from app.engine.predictions import _shadbala_multiplier, _varga_dignity, predict

BACHCHAN = BirthData(date="1942-10-11", time="16:00:00",
                     lat=25.45, lon=81.85, tz_offset=5.5)
ON = datetime(2026, 7, 3)


@pytest.fixture(scope="module")
def result():
    return predict(BACHCHAN, ON)


def test_shadbala_multiplier_bands():
    assert _shadbala_multiplier(None) == 1.0     # nodes: neutral
    assert _shadbala_multiplier(1.2) == 1.1      # strong amplifies
    assert _shadbala_multiplier(0.9) == 1.0      # borderline neutral
    assert _shadbala_multiplier(0.7) == 0.9      # weak dampens


def test_varga_dignity_states():
    # Venus: exalted Pisces(11), own Taurus(1)/Libra(6), debilitated Virgo(5).
    assert _varga_dignity("Venus", 11) == "exalted"
    assert _varga_dignity("Venus", 6) == "own"
    assert _varga_dignity("Venus", 5) == "debilitated"
    assert _varga_dignity("Venus", 0) is None


def test_dasha_facts_carry_shadbala(result):
    facts = [f for a in result["areas"] for f in a["substantiation"]
             if f.get("type") == "dasha_lord_natal_role"]
    assert facts
    classical = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
    for f in facts:
        if f["lord"] in classical:
            assert "shadbala_rupas" in f and "shadbala_multiplier" in f
            assert f["shadbala_multiplier"] in (0.9, 1.0, 1.1)
        else:  # nodes have no shadbala
            assert "shadbala_rupas" not in f


def test_varga_corroboration_facts(result):
    """Bachchan: Sun (7th lord from Aquarius lagna = Leo -> Sun) and Venus
    are both own-sign in navamsa -> two +0.1 relationship facts."""
    rel = next(a for a in result["areas"] if a["area"] == "relationships")
    vf = [f for f in rel["substantiation"] if f.get("type") == "varga_dignity"]
    assert {(f["planet"], f["varga"], f["dignity"]) for f in vf} == {
        ("Sun", "D9", "own"), ("Venus", "D9", "own")}
    for f in vf:
        assert f["delta"] == 0.1
        assert abs(f["delta"]) <= 0.1  # deltas stay small and cited


def test_payload_exposes_shadbala_and_jaimini(result):
    """The interpretation layer needs the full Shadbala + Jaimini data, not
    just the internal dasha-lord-weighting use of it, to ground
    Shadbala/Jaimini-specific questions."""
    assert "shadbala" in result and "planets" in result["shadbala"]
    classical = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
    assert classical <= result["shadbala"]["planets"].keys()
    for planet in classical:
        row = result["shadbala"]["planets"][planet]
        assert "total_rupas" in row and "required_rupas" in row and "ratio" in row

    assert "jaimini" in result
    assert len(result["jaimini"]["karakas"]) == 7
    assert {k["karaka"] for k in result["jaimini"]["karakas"]} == {
        "Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka",
        "Putrakaraka", "Gnatikaraka", "Darakaraka"}
    assert result["jaimini"]["chara_dasha"]["periods"]
    assert "chart" in result and "planets" in result["chart"] and "house_lords" in result["chart"]


def test_jaimini_chara_dasha_corroboration_facts_are_cited(result):
    """When present, Jaimini corroboration facts must stay small (+/-0.1,
    matching the varga-corroboration convention) and cite their source."""
    facts = [f for a in result["areas"] for f in a["substantiation"]
             if f.get("type") == "jaimini_chara_dasha_corroboration"]
    for f in facts:
        assert f["delta"] == 0.1
        assert "note" in f and f["note"]
