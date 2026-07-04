"""Shadbala validation against B.V. Raman's Standard Horoscope.

Strategy (documented): we do not chase virupa-exact equality with the book
(fork-heavy territory). We assert STRUCTURAL truths — component ranges,
exact naisargika, plausible total band, ranking sanity — plus a regression
pin: computed totals are recorded into fixtures/shadbala_raman.json on first
run and must stay within 0.5 rupa afterwards.

Drik bala is additionally cross-checked against the PyJHora-derived research
reference for this chart (tolerance 3 virupas).
"""
import json
import math
import os

import pytest

from app.engine.ephemeris import BirthData, EngineConfig
from app.engine.shadbala import (
    NAISARGIKA, PLANETS7, REQUIRED_RUPAS, compute_shadbala, dig_bala,
    paksha_bala, sputa_drishti, uccha_bala,
)

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures",
                            "shadbala_raman.json")

# B.V. Raman's Standard Horoscope: 1918-10-16, 14:22:16 IST, Bangalore.
RAMAN_BIRTH = BirthData(date="1918-10-16", time="14:22:16",
                        lat=13.0, lon=77.5833, tz_offset=5.5)

# PyJHora cross-check reference for drik bala (Sun..Saturn), virupas.
DRIK_REFERENCE = [15.86, -21.73, 0.95, 15.64, -16.04, 18.47, 7.21]

# Component maxima given the implemented conventions:
# sthana: uccha 60 + saptavargaja 7*45 + ojayugma 30 + kendradi 60 + drekkana 15
_STHANA_MAX = 60 + 7 * 45 + 30 + 60 + 15
# kala: nathonnata 60 + paksha 120 (Moon doubled) + tribhaga 60 + abda 15
#       + masa 30 + vara 45 + hora 60 + ayana 120 (Sun doubled)
_KALA_MAX = 60 + 120 + 60 + 15 + 30 + 45 + 60 + 120


@pytest.fixture(scope="module")
def raman_shadbala():
    return compute_shadbala(RAMAN_BIRTH, EngineConfig(ayanamsa="raman"))


def test_all_classical_planets_present(raman_shadbala):
    assert set(raman_shadbala["planets"].keys()) == set(PLANETS7)


def test_component_ranges(raman_shadbala):
    for p, row in raman_shadbala["planets"].items():
        assert 0 <= row["sthana"] <= _STHANA_MAX, p
        assert 0 <= row["dig"] <= 60, p
        assert 0 <= row["kala"] <= _KALA_MAX, p
        assert 0 <= row["cheshta"] <= 120, p  # Moon paksha / Sun ayana doubled
        assert -180 <= row["drik"] <= 180, p
        comp = row["components"]
        assert 0 <= comp["sthana"]["uccha"] <= 60
        assert 7 * 1.875 <= comp["sthana"]["saptavargaja"] <= 7 * 45
        assert comp["sthana"]["ojayugma"] in (0.0, 15.0, 30.0)
        assert comp["sthana"]["kendradi"] in (15.0, 30.0, 60.0)
        assert comp["sthana"]["drekkana"] in (0.0, 15.0)


def test_naisargika_exact(raman_shadbala):
    for p, row in raman_shadbala["planets"].items():
        assert row["naisargika"] == pytest.approx(NAISARGIKA[p], abs=1e-4)


def test_totals_in_plausible_band(raman_shadbala):
    for p, row in raman_shadbala["planets"].items():
        assert 4.0 <= row["total_rupas"] <= 10.0, (p, row["total_rupas"])
        assert row["total_virupas"] == pytest.approx(row["total_rupas"] * 60,
                                                     abs=0.5)


def test_required_ratio_sufficient(raman_shadbala):
    for p, row in raman_shadbala["planets"].items():
        assert row["required_rupas"] == REQUIRED_RUPAS[p]
        assert row["ratio"] == pytest.approx(
            row["total_rupas"] / row["required_rupas"], abs=0.01)
        assert row["sufficient"] == (row["total_rupas"] >= row["required_rupas"])


def test_ranking_sanity(raman_shadbala):
    """Computed-pin (not a book claim): in the Standard Horoscope Mercury is
    conspicuously strong (swakshetra in Virgo, exalted region) and Mars is
    the weakest of the seven. PyJHora agrees on both extremes."""
    rupas = {p: r["total_rupas"] for p, r in raman_shadbala["planets"].items()}
    assert max(rupas, key=rupas.get) == "Mercury"
    assert min(rupas, key=rupas.get) == "Mars"


def test_drik_vs_pyjhora_reference(raman_shadbala):
    """Cross-check drik bala against the PyJHora research reference for this
    chart (computed with jhora 4.x, RAMAN ayanamsa). Tolerance 3 virupas."""
    for p, ref in zip(PLANETS7, DRIK_REFERENCE):
        got = raman_shadbala["planets"][p]["drik"]
        assert math.isclose(got, ref, abs_tol=3.0), (p, got, ref)


def test_regression_pin(raman_shadbala):
    """Record computed totals into the fixture on first run; afterwards the
    engine must reproduce them within 0.5 rupa."""
    computed = {
        p: {k: row[k] for k in ("sthana", "dig", "kala", "cheshta",
                                "naisargika", "drik", "total_rupas", "ratio")}
        for p, row in raman_shadbala["planets"].items()
    }
    if not os.path.exists(FIXTURE_PATH):
        payload = {
            "_source": "computed by app.engine.shadbala (regression pin, "
                       "NOT B.V. Raman's book values)",
            "birth": {"date": "1918-10-16", "time": "14:22:16", "lat": 13.0,
                      "lon": 77.5833, "tz_offset": 5.5, "ayanamsa": "raman"},
            "planets": computed,
        }
        with open(FIXTURE_PATH, "w") as f:
            json.dump(payload, f, indent=2)
        pytest.skip("fixture recorded on first run")
    with open(FIXTURE_PATH) as f:
        pinned = json.load(f)["planets"]
    for p in PLANETS7:
        assert abs(computed[p]["total_rupas"] - pinned[p]["total_rupas"]) <= 0.5, p


# ---------------------------------------------------------------------------
# Unit checks of individual formulas
# ---------------------------------------------------------------------------

def test_uccha_bala_extremes():
    # Sun deep exaltation Aries 10 -> 60; deep debilitation Libra 10 -> 0.
    assert uccha_bala("Sun", 10.0) == pytest.approx(60.0)
    assert uccha_bala("Sun", 190.0) == pytest.approx(0.0)
    # Saturn deb point 20 deg Aries (abs 20).
    assert uccha_bala("Saturn", 20.0) == pytest.approx(0.0)
    assert uccha_bala("Saturn", 200.0) == pytest.approx(60.0)


def test_dig_bala_extremes():
    # Aries lagna; Sun strongest in the 10th (Capricorn), weakest point is
    # the 4th sign's midpoint (Cancer 15 = 105 abs). Sun at Capricorn 15
    # (285 abs) -> 60; Sun at Cancer 15 -> 0.
    assert dig_bala("Sun", 285.0, 0) == pytest.approx(60.0)
    assert dig_bala("Sun", 105.0, 0) == pytest.approx(0.0)
    # Jupiter strongest in lagna: at lagna-sign midpoint -> 60.
    assert dig_bala("Jupiter", 15.0, 0) == pytest.approx(60.0)


def test_paksha_bala_near_full_moon():
    # Moon 179 deg from Sun: waxing, d=179. Benefics ~ 59.67; Moon doubled;
    # malefics ~ 0.33.
    pb = paksha_bala(0.0, 179.0)
    assert pb["Jupiter"] == pytest.approx(179.0 / 3.0)
    assert pb["Moon"] == pytest.approx(2 * 179.0 / 3.0)
    assert pb["Saturn"] == pytest.approx((180.0 - 179.0) / 3.0)


def test_sputa_drishti_landmarks():
    # Full 7th aspect for everyone.
    assert sputa_drishti(180.0, "Sun") == pytest.approx(60.0)
    # No aspect inside 30 deg.
    assert sputa_drishti(15.0, "Sun") == 0.0
    # Special full aspects at exact angles.
    assert sputa_drishti(90.0, "Mars") == pytest.approx(60.0)     # 4th
    assert sputa_drishti(210.0, "Mars") == pytest.approx(60.0)    # 8th
    assert sputa_drishti(120.0, "Jupiter") == pytest.approx(60.0)  # 5th
    assert sputa_drishti(240.0, "Jupiter") == pytest.approx(60.0)  # 9th
    assert sputa_drishti(60.0, "Saturn") == pytest.approx(60.0)   # 3rd
    assert sputa_drishti(270.0, "Saturn") == pytest.approx(60.0)  # 10th
    # Non-special planets get the base curve at those angles.
    assert sputa_drishti(90.0, "Venus") == pytest.approx(45.0)
    assert sputa_drishti(60.0, "Venus") == pytest.approx(15.0)
