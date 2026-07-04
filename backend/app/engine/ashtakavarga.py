"""Ashtakavarga: Bhinnashtakavarga (BAV) per classical Parashari tables
(BPHS ch. 66) and Sarvashtakavarga (SAV).

Row totals: Sun 48, Moon 49, Mars 39, Mercury 54, Jupiter 56, Venus 52,
Saturn 39 — grand total 337. Verified by tests.

Table semantics: BENEFIC_HOUSES[target][contributor] is the set of houses,
counted inclusively from the contributor's natal sign (lagna counts too),
in which the target planet gives a bindu.
"""
from __future__ import annotations

from . import constants as K

CONTRIBUTORS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"]

BENEFIC_HOUSES = {
    "Sun": {
        "Sun": {1, 2, 4, 7, 8, 9, 10, 11},
        "Moon": {3, 6, 10, 11},
        "Mars": {1, 2, 4, 7, 8, 9, 10, 11},
        "Mercury": {3, 5, 6, 9, 10, 11, 12},
        "Jupiter": {5, 6, 9, 11},
        "Venus": {6, 7, 12},
        "Saturn": {1, 2, 4, 7, 8, 9, 10, 11},
        "Lagna": {3, 4, 6, 10, 11, 12},
    },
    "Moon": {
        "Sun": {3, 6, 7, 8, 10, 11},
        "Moon": {1, 3, 6, 7, 10, 11},
        "Mars": {2, 3, 5, 6, 9, 10, 11},
        "Mercury": {1, 3, 4, 5, 7, 8, 10, 11},
        "Jupiter": {1, 4, 7, 8, 10, 11, 12},
        "Venus": {3, 4, 5, 7, 9, 10, 11},
        "Saturn": {3, 5, 6, 11},
        "Lagna": {3, 6, 10, 11},
    },
    "Mars": {
        "Sun": {3, 5, 6, 10, 11},
        "Moon": {3, 6, 11},
        "Mars": {1, 2, 4, 7, 8, 10, 11},
        "Mercury": {3, 5, 6, 11},
        "Jupiter": {6, 10, 11, 12},
        "Venus": {6, 8, 11, 12},
        "Saturn": {1, 4, 7, 8, 9, 10, 11},
        "Lagna": {1, 3, 6, 10, 11},
    },
    "Mercury": {
        "Sun": {5, 6, 9, 11, 12},
        "Moon": {2, 4, 6, 8, 10, 11},
        "Mars": {1, 2, 4, 7, 8, 9, 10, 11},
        "Mercury": {1, 3, 5, 6, 9, 10, 11, 12},
        "Jupiter": {6, 8, 11, 12},
        "Venus": {1, 2, 3, 4, 5, 8, 9, 11},
        "Saturn": {1, 2, 4, 7, 8, 9, 10, 11},
        "Lagna": {1, 2, 4, 6, 8, 10, 11},
    },
    "Jupiter": {
        "Sun": {1, 2, 3, 4, 7, 8, 9, 10, 11},
        "Moon": {2, 5, 7, 9, 11},
        "Mars": {1, 2, 4, 7, 8, 10, 11},
        "Mercury": {1, 2, 4, 5, 6, 9, 10, 11},
        "Jupiter": {1, 2, 3, 4, 7, 8, 10, 11},
        "Venus": {2, 5, 6, 9, 10, 11},
        "Saturn": {3, 5, 6, 12},
        "Lagna": {1, 2, 4, 5, 6, 7, 9, 10, 11},
    },
    "Venus": {
        "Sun": {8, 11, 12},
        "Moon": {1, 2, 3, 4, 5, 8, 9, 11, 12},
        "Mars": {3, 5, 6, 9, 11, 12},
        "Mercury": {3, 5, 6, 9, 11},
        "Jupiter": {5, 8, 9, 10, 11},
        "Venus": {1, 2, 3, 4, 5, 8, 9, 10, 11},
        "Saturn": {3, 4, 5, 8, 9, 10, 11},
        "Lagna": {1, 2, 3, 4, 5, 8, 9, 11},
    },
    "Saturn": {
        "Sun": {1, 2, 4, 7, 8, 10, 11},
        "Moon": {3, 6, 11},
        "Mars": {3, 5, 6, 10, 11, 12},
        "Mercury": {6, 8, 9, 10, 11, 12},
        "Jupiter": {5, 6, 11, 12},
        "Venus": {6, 11, 12},
        "Saturn": {3, 5, 6, 11},
        "Lagna": {1, 3, 4, 6, 10, 11},
    },
}

ROW_TOTALS = {t: sum(len(v) for v in rows.values()) for t, rows in BENEFIC_HOUSES.items()}


def bav_for(target: str, contributor_signs: dict) -> list[int]:
    """Bindus for `target` planet in each of the 12 signs (index 0=Aries)."""
    table = BENEFIC_HOUSES[target]
    bindus = [0] * 12
    for sign in range(12):
        count = 0
        for contrib in CONTRIBUTORS:
            house = (sign - contributor_signs[contrib]) % 12 + 1
            if house in table[contrib]:
                count += 1
        bindus[sign] = count
    return bindus


def compute_ashtakavarga(chart: dict) -> dict:
    contributor_signs = {p: chart["planets"][p]["sign"] for p in K.CLASSICAL_PLANETS}
    contributor_signs["Lagna"] = chart["lagna"]["sign"]

    bav = {target: bav_for(target, contributor_signs) for target in BENEFIC_HOUSES}
    sav = [sum(bav[t][s] for t in bav) for s in range(12)]
    return {
        "bav": bav,
        "bav_totals": {t: sum(v) for t, v in bav.items()},
        "sav": sav,
        "sav_total": sum(sav),
        "sign_names": K.SIGN_NAMES,
    }


def transit_strength(ashtakavarga: dict, transit_sign: int,
                     planet: str | None = None) -> dict:
    """SAV (and optionally the planet's own BAV) bindus of the sign a
    transiting planet occupies. >= 28 SAV is conventionally strong,
    <= 22 weak."""
    sav = ashtakavarga["sav"][transit_sign]
    out = {
        "sign": transit_sign,
        "sign_name": K.SIGN_NAMES[transit_sign],
        "sav_bindus": sav,
        "sav_verdict": "strong" if sav >= 28 else ("weak" if sav <= 22 else "average"),
    }
    if planet and planet in ashtakavarga["bav"]:
        bav = ashtakavarga["bav"][planet][transit_sign]
        out["bav_bindus"] = bav
        out["bav_verdict"] = "strong" if bav >= 5 else ("weak" if bav <= 2 else "average")
    return out
