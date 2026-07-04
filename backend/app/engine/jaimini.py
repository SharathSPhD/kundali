"""Jaimini utilities per the K.N. Rao school: chara karakas (7-karaka
scheme) and Chara Dasha (Rao variant).

Convention decisions (documented against Rao, "Predicting Through Jaimini's
Chara Dasha", validated against his published Amitabh Bachchan table):

1. Karakas: SEVEN karakas from the seven classical planets only (no Rahu —
   Rao's school), ranked by degree-in-sign descending.

2. Chara dasha sequence direction (savya/apasavya) is decided ONCE for the
   whole chart from the 9th sign from lagna: 9th in {Aries, Leo, Virgo,
   Libra, Aquarius, Pisces} -> direct; in {Taurus, Gemini, Cancer, Scorpio,
   Sagittarius, Capricorn} -> reverse. The sequence starts from the lagna
   sign and proceeds in that direction.

3. Dasha LENGTH counting: from the sign to the sign its lord occupies,
   counted zodiacally for vishama-pada signs (Aries, Taurus, Gemini, Libra,
   Scorpio, Sagittarius) and anti-zodiacally for sama-pada signs (Cancer,
   Leo, Virgo, Capricorn, Aquarius, Pisces), inclusive minus one; lord in
   its own sign -> 12 years. NOTE: the task brief suggested counting in the
   chart's direction, but only pada-class counting reproduces Rao's
   published Bachchan lengths (Leo 11, Virgo 12, Libra 11) — see
   tests/fixtures/chara_bachchan.json; pada-class counting is what Rao's
   book actually prescribes, so it is used here.

4. Scorpio (Mars/Ketu) and Aquarius (Saturn/Rahu) co-lordship: if one lord
   is IN the sign use the other lord's position; both in -> 12 years;
   neither -> the stronger lord (more co-tenant grahas in its sign; tie ->
   higher degree-in-sign, plain degrees, no 30-x for Rahu/Ketu — plain
   degrees are what reproduce Rao's Bachchan table).

5. Antardashas: 12 equal parts; the sub-sequence starts from the NEXT sign
   from the mahadasha sign in the chart's direction, with the mahadasha
   sign itself LAST (Rao/Raman convention).

6. Two full cycles are generated with identical lengths (the second-cycle
   "12 minus x" variant is not applied — documented simplification), capped
   at 120 years from birth.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import constants as K
from .ephemeris import EngineConfig

KARAKA_NAMES = [
    "Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka",
    "Putrakaraka", "Gnatikaraka", "Darakaraka",
]
KARAKA_ABBR = ["AK", "AmK", "BK", "MK", "PK", "GK", "DK"]

# 9th-sign groups for the whole-chart direction (Rao variant).
_DIRECT_NINTH = {0, 4, 5, 6, 10, 11}    # Aries, Leo, Virgo, Libra, Aqu, Pis

# Pada-class groups for dasha-length counting.
_VISHAMA_PADA = {0, 1, 2, 6, 7, 8}      # Ari, Tau, Gem, Lib, Sco, Sag (count direct)

# Dual lordships (sign -> primary, secondary).
_DUAL_LORDS = {7: ("Mars", "Ketu"), 10: ("Saturn", "Rahu")}


def chara_karakas(chart: dict) -> list[dict]:
    """Rao 7-karaka scheme: rank Sun..Saturn by degree-in-sign descending.
    Ties (sub-arcsecond, practically impossible) break by classical planet
    order for determinism."""
    order = {p: i for i, p in enumerate(K.CLASSICAL_PLANETS)}
    ranked = sorted(
        K.CLASSICAL_PLANETS,
        key=lambda p: (-chart["planets"][p]["degree_in_sign"], order[p]),
    )
    out = []
    for i, p in enumerate(ranked):
        pos = chart["planets"][p]
        out.append({
            "karaka": KARAKA_NAMES[i],
            "abbr": KARAKA_ABBR[i],
            "planet": p,
            "degree_in_sign": pos["degree_in_sign"],
            "sign": pos["sign"],
            "sign_name": pos["sign_name"],
        })
    return out


def _count(from_sign: int, to_sign: int, direction: int) -> int:
    """Signs from from_sign to to_sign inclusive, counted in `direction`
    (+1 zodiacal / -1 anti-zodiacal), minus one. 0 when same sign."""
    return (direction * (to_sign - from_sign)) % 12


def _effective_lord_sign(sign: int, chart: dict) -> tuple[str, int, int | None]:
    """(lord_used, lord_sign, years_override) for a dasha sign, applying the
    Scorpio/Aquarius co-lordship rules (see module docstring #4)."""
    planets = chart["planets"]
    if sign not in _DUAL_LORDS:
        lord = K.SIGN_LORDS[sign]
        return lord, planets[lord]["sign"], None
    a, b = _DUAL_LORDS[sign]
    a_in = planets[a]["sign"] == sign
    b_in = planets[b]["sign"] == sign
    if a_in and b_in:
        return f"{a}+{b}", sign, 12
    if a_in:
        return b, planets[b]["sign"], None
    if b_in:
        return a, planets[a]["sign"], None
    # Neither in the sign: stronger lord = more co-tenant grahas (all 9
    # grahas counted); tie -> higher degree-in-sign (plain degrees).
    def strength(lord: str):
        lsign = planets[lord]["sign"]
        conj = sum(1 for q, pos in planets.items()
                   if q != lord and pos["sign"] == lsign)
        return (conj, planets[lord]["degree_in_sign"])
    lord = a if strength(a) >= strength(b) else b
    return lord, planets[lord]["sign"], None


def dasha_years(sign: int, chart: dict) -> dict:
    """Chara dasha length in years for `sign` (pada-class counting)."""
    lord, lord_sign, override = _effective_lord_sign(sign, chart)
    if override is not None:
        return {"lord": lord, "lord_sign": lord_sign, "years": override,
                "count_direction": 0}
    direction = 1 if sign in _VISHAMA_PADA else -1
    n = _count(sign, lord_sign, direction)
    years = 12 if n == 0 else n
    return {"lord": lord, "lord_sign": lord_sign, "years": years,
            "count_direction": direction}


def build_chara_dasha(chart: dict, birth_dt: datetime,
                      config: EngineConfig | None = None,
                      cycles: int = 2) -> dict:
    config = config or EngineConfig()
    year_days = config.dasha_year_days
    lagna_sign = chart["lagna"]["sign"]
    ninth = (lagna_sign + 8) % 12
    direction = 1 if ninth in _DIRECT_NINTH else -1
    horizon = birth_dt + timedelta(days=120 * year_days)

    sequence = [(lagna_sign + direction * i) % 12 for i in range(12)]
    lengths = {s: dasha_years(s, chart) for s in sequence}

    periods = []
    start = birth_dt
    for _cycle in range(cycles):
        for sign in sequence:
            if start >= horizon:
                break
            info = lengths[sign]
            days = info["years"] * year_days
            end = start + timedelta(days=days)
            # Antardashas: 12 equal parts, starting from the NEXT sign in
            # the chart's direction; the mahadasha sign itself comes LAST.
            sub_signs = [(sign + direction * j) % 12 for j in range(1, 12)] + [sign]
            sub_days = days / 12.0
            children = []
            sub_start = start
            for ss in sub_signs:
                sub_end = sub_start + timedelta(days=sub_days)
                children.append({
                    "sign": ss,
                    "sign_name": K.SIGN_NAMES[ss],
                    "level": 2,
                    "level_name": "antardasha",
                    "start": sub_start.isoformat(),
                    "end": sub_end.isoformat(),
                })
                sub_start = sub_end
            periods.append({
                "sign": sign,
                "sign_name": K.SIGN_NAMES[sign],
                "level": 1,
                "level_name": "mahadasha",
                "years": info["years"],
                "lord": info["lord"],
                "lord_sign_name": K.SIGN_NAMES[info["lord_sign"]],
                "start": start.isoformat(),
                "end": end.isoformat(),
                "children": children,
            })
            start = end
        if start >= horizon:
            break

    return {
        "system": "chara_dasha_kn_rao",
        "direction": "direct" if direction == 1 else "reverse",
        "ninth_sign": K.SIGN_NAMES[ninth],
        "lagna_sign": K.SIGN_NAMES[lagna_sign],
        "birth": birth_dt.isoformat(),
        "horizon": horizon.isoformat(),
        "periods": periods,
    }


def active_path(tree: dict, on_date: datetime) -> list[dict]:
    """[mahadasha, antardasha] nodes active on `on_date` (empty if outside
    the generated horizon)."""
    iso = on_date.isoformat()
    path = []
    nodes = tree["periods"]
    while nodes:
        hit = next((n for n in nodes if n["start"] <= iso < n["end"]), None)
        if hit is None:
            break
        path.append({k: hit[k] for k in
                     ("sign", "sign_name", "level", "level_name", "start", "end")})
        nodes = hit.get("children", [])
    return path


def compute_jaimini(chart: dict, birth_dt: datetime,
                    config: EngineConfig | None = None,
                    on: datetime | None = None) -> dict:
    """Karakas + chara dasha + active path, from a natal chart dict."""
    tree = build_chara_dasha(chart, birth_dt, config)
    on = on or datetime.utcnow()
    return {
        "karakas": chara_karakas(chart),
        "chara_dasha": tree,
        "active": active_path(tree, on),
        "on": on.isoformat(),
    }
