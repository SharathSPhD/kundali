"""Natal chart assembly: whole-sign houses, dignity, combustion, retrograde,
house lords. Pure functions — `assemble_chart` is reusable for synthetic
charts in tests; `build_chart` adds the ephemeris step."""
from __future__ import annotations

from dataclasses import asdict

from . import constants as K
from .ephemeris import (
    BirthData, EngineConfig, ascendant, ayanamsa_value,
    julian_day_from_utc, planet_longitudes,
)


def dignity_of(planet: str, sign: int, degree_in_sign: float) -> str:
    """exalted / moolatrikona / own / friend / neutral / enemy / debilitated."""
    ex = K.EXALTATION.get(planet)
    if ex and ex[0] == sign:
        return "exalted"
    de = K.DEBILITATION.get(planet)
    if de and de[0] == sign:
        return "debilitated"
    mt = K.MOOLATRIKONA.get(planet)
    if mt and mt[0] == sign and mt[1] <= degree_in_sign < mt[2]:
        return "moolatrikona"
    if sign in K.OWN_SIGNS.get(planet, set()):
        return "own"
    return natural_relation_dignity(planet, K.SIGN_LORDS[sign])


def natural_relation_dignity(planet: str, sign_lord: str) -> str:
    rel = K.natural_relation(planet, sign_lord)
    return rel  # friend / neutral / enemy


def _angular_distance(a: float, b: float) -> float:
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def combustion_flags(planets: dict) -> dict:
    """planet -> bool, using orbs from constants (retro orbs where defined)."""
    sun_lon = planets["Sun"]["longitude"]
    out = {}
    for name, p in planets.items():
        if name in ("Sun", "Rahu", "Ketu"):
            out[name] = False
            continue
        direct_orb, retro_orb = K.COMBUSTION_ORBS[name]
        orb = retro_orb if p.get("retrograde") else direct_orb
        out[name] = _angular_distance(p["longitude"], sun_lon) <= orb
    return out


def house_of(planet_sign: int, lagna_sign: int) -> int:
    return (planet_sign - lagna_sign) % 12 + 1


def assemble_chart(lagna: dict, planets: dict, config: EngineConfig | None = None,
                   meta: dict | None = None) -> dict:
    """Build the chart dict from precomputed lagna/planet position dicts
    (each as produced by ephemeris._position_dict, minimally requiring
    longitude/sign/degree_in_sign)."""
    lagna_sign = lagna["sign"]
    combust = combustion_flags(planets)

    chart_planets = {}
    for name, p in planets.items():
        entry = dict(p)
        entry["house"] = house_of(p["sign"], lagna_sign)
        entry["combust"] = combust[name]
        entry["dignity"] = dignity_of(name, p["sign"], p["degree_in_sign"])
        chart_planets[name] = entry

    houses = []
    house_lords = {}
    for h in range(1, 13):
        sign = (lagna_sign + h - 1) % 12
        lord = K.SIGN_LORDS[sign]
        occupants = [n for n, p in chart_planets.items() if p["house"] == h]
        houses.append({
            "house": h,
            "sign": sign,
            "sign_name": K.SIGN_NAMES[sign],
            "lord": lord,
            "occupants": occupants,
        })
        house_lords[h] = {
            "lord": lord,
            "placed_house": chart_planets[lord]["house"],
            "placed_sign": chart_planets[lord]["sign"],
            "placed_sign_name": chart_planets[lord]["sign_name"],
            "dignity": chart_planets[lord]["dignity"],
        }

    chart = {
        "lagna": dict(lagna),
        "planets": chart_planets,
        "houses": houses,
        "house_lords": house_lords,
    }
    if meta:
        chart.update(meta)
    if config is not None:
        chart["config"] = {
            "ayanamsa": config.ayanamsa,
            "node_type": config.node_type,
            "dasha_year_days": config.dasha_year_days,
        }
    return chart


def build_chart(birth: BirthData, config: EngineConfig | None = None) -> dict:
    config = config or EngineConfig()
    jd = julian_day_from_utc(birth.utc_datetime())
    planets = planet_longitudes(jd, config)
    lagna = ascendant(jd, birth.lat, birth.lon, config)
    meta = {
        "jd": jd,
        "ayanamsa_value": round(ayanamsa_value(jd, config), 6),
        "birth": asdict(birth),
    }
    return assemble_chart(lagna, planets, config, meta)
