"""Ashtakoota matching + Mangal dosha tests."""
import pytest

from app.engine.ephemeris import BirthData, EngineConfig
from app.engine import matching as M

CFG = EngineConfig()

GROOM = BirthData(date="1990-05-15", time="06:30", lat=12.9716, lon=77.5946,
                  tz_offset=5.5)
BRIDE = BirthData(date="1992-11-02", time="14:45", lat=28.6139, lon=77.2090,
                  tz_offset=5.5)

SYMMETRIC_KUTAS = {"Vashya", "Tara", "Yoni", "Graha Maitri", "Gana",
                   "Bhakoot", "Nadi"}


def _kuta(result, name):
    return next(k for k in result["kutas"] if k["name"] == name)


def test_output_shape_and_bounds():
    r = M.match(GROOM, BRIDE, CFG)
    assert len(r["kutas"]) == 8
    assert [k["name"] for k in r["kutas"]] == [
        "Varna", "Vashya", "Tara", "Yoni", "Graha Maitri", "Gana",
        "Bhakoot", "Nadi"]
    for k in r["kutas"]:
        assert 0 <= k["points"] <= k["max"], k
    assert r["max_total"] == 36
    assert abs(r["total"] - sum(k["points"] for k in r["kutas"])) < 1e-9
    assert r["verdict"] in {"excellent", "very good", "acceptable",
                            "not recommended"}
    assert "mangal_dosha" in r
    for side in ("groom", "bride"):
        md = r["mangal_dosha"][side]
        assert isinstance(md["manglik"], bool)
        assert 1 <= md["mars_house_from_lagna"] <= 12
        assert 1 <= md["mars_house_from_moon"] <= 12


def test_same_nakshatra_pair_nadi_zero():
    """Identical births -> same nakshatra -> same nadi -> 0 points."""
    r = M.match(GROOM, GROOM, CFG)
    assert _kuta(r, "Nadi")["points"] == 0
    # Same-chart sanity: identical moon signs / ganas / lords score full.
    assert _kuta(r, "Varna")["points"] == 1
    assert _kuta(r, "Vashya")["points"] == 2
    assert _kuta(r, "Gana")["points"] == 6
    assert _kuta(r, "Graha Maitri")["points"] == 5
    assert _kuta(r, "Bhakoot")["points"] == 7
    # Same nakshatra -> same yoni animal AND gender -> 3 (not 4).
    assert _kuta(r, "Yoni")["points"] == 3


def test_symmetric_kutas_are_symmetric():
    ab = M.match(GROOM, BRIDE, CFG)
    ba = M.match(BRIDE, GROOM, CFG)
    for name in SYMMETRIC_KUTAS:
        assert _kuta(ab, name)["points"] == _kuta(ba, name)["points"], name


def test_sworn_enemy_yoni_zero():
    # Cow (Uttara Phalguni) vs Tiger (Chitra) are sworn enemies.
    assert M._yoni_points("Uttara Phalguni", "Chitra")[0] == 0
    # Horse (Ashwini) vs Buffalo (Hasta).
    assert M._yoni_points("Ashwini", "Hasta")[0] == 0
    # Serpent (Rohini) vs Mongoose (Uttara Ashadha).
    assert M._yoni_points("Rohini", "Uttara Ashadha")[0] == 0
    # Opposite genders of the same animal score the full 4.
    assert M._yoni_points("Ashwini", "Shatabhisha")[0] == 4  # Horse M x Horse F


def test_hand_checked_full_example():
    """Groom Moon Rohini (Taurus), bride Moon Hasta (Virgo) — hand-scored.

    Varna: Taurus/Virgo both Vaishya -> 1.
    Vashya: Chatushpada vs Manava -> 0 (per our published-table convention).
    Tara: Rohini(3)->Hasta(12): count 10, tara 1 (malefic); reverse count 19,
      tara 1 (malefic) -> 0.
    Yoni: Serpent (M) x Buffalo (F) -> matrix 1.
    Graha Maitri: Venus & Mercury are mutual friends -> 5.
    Gana: Manushya x Deva -> 5.
    Bhakoot: Taurus->Virgo distance 5 (5-9 pair) -> 0.
    Nadi: Rohini Antya, Hasta Adi -> 8.  Total = 20 ('acceptable').
    """
    g = {"sign": 1, "sign_name": "Taurus", "degree_in_sign": 10.0,
         "nakshatra": "Rohini", "nakshatra_index": 3, "pada": 1,
         "sign_lord": "Venus"}
    b = {"sign": 5, "sign_name": "Virgo", "degree_in_sign": 10.0,
         "nakshatra": "Hasta", "nakshatra_index": 12, "pada": 1,
         "sign_lord": "Mercury"}
    kutas = M.compute_kutas(g, b)
    points = {k["name"]: k["points"] for k in kutas}
    assert points == {
        "Varna": 1, "Vashya": 0, "Tara": 0, "Yoni": 1, "Graha Maitri": 5,
        "Gana": 5, "Bhakoot": 0, "Nadi": 8,
    }
    total = sum(points.values())
    assert total == 20
    assert M.verdict_for(total) == "acceptable"


def test_verdict_bands():
    assert M.verdict_for(36) == "excellent"
    assert M.verdict_for(32) == "excellent"
    assert M.verdict_for(31.5) == "very good"
    assert M.verdict_for(25) == "very good"
    assert M.verdict_for(24.5) == "acceptable"
    assert M.verdict_for(18) == "acceptable"
    assert M.verdict_for(17.5) == "not recommended"


def test_mangal_dosha_mutual_cancellation():
    r = M.match(GROOM, GROOM, CFG)
    md = r["mangal_dosha"]
    # Same chart on both sides: either both manglik (mutual) or neither.
    if md["groom"]["effective"]:
        assert md["mutual_cancellation"] and md["compatible"]
    else:
        assert md["compatible"]


def test_yoni_matrix_symmetric_and_bounded():
    for i in range(14):
        for j in range(14):
            v = M._YONI_MATRIX[i][j]
            assert 0 <= v <= 4
            assert v == M._YONI_MATRIX[j][i]


def test_nakshatra_partitions_complete():
    from app.engine import constants as K
    assert set(M.YONI_OF_NAKSHATRA) == set(K.NAKSHATRA_NAMES)
    ganas = {M._gana_of(n) for n in K.NAKSHATRA_NAMES}
    assert ganas == {"Deva", "Manushya", "Rakshasa"}
    assert sum(1 for n in K.NAKSHATRA_NAMES if M._gana_of(n) == "Deva") == 9
    assert sum(1 for n in K.NAKSHATRA_NAMES if M._nadi_of(n) == "Adi") == 9
    assert sum(1 for n in K.NAKSHATRA_NAMES if M._nadi_of(n) == "Madhya") == 9
    assert sum(1 for n in K.NAKSHATRA_NAMES if M._nadi_of(n) == "Antya") == 9
