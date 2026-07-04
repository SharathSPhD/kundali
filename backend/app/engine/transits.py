"""Transits (gochara): positions on a date, favourability from natal Moon,
Sade Sati / Ashtama / Kantaka Shani, Jupiter+Saturn double transit."""
from __future__ import annotations

from datetime import datetime, timedelta

import swisseph as swe

from . import constants as K
from .ephemeris import EngineConfig, julian_day_from_utc, planet_longitudes


def _house_from(sign: int, reference_sign: int) -> int:
    return (sign - reference_sign) % 12 + 1


def transit_positions(on_dt_utc: datetime, config: EngineConfig | None = None) -> dict:
    config = config or EngineConfig()
    jd = julian_day_from_utc(on_dt_utc)
    return planet_longitudes(jd, config)


def gochara_table(natal_moon_sign: int, positions: dict) -> list[dict]:
    rows = []
    for planet in K.PLANETS:
        p = positions[planet]
        house = _house_from(p["sign"], natal_moon_sign)
        rows.append({
            "planet": planet,
            "sign": p["sign"],
            "sign_name": p["sign_name"],
            "degree_in_sign": p["degree_in_sign"],
            "retrograde": p["retrograde"],
            "house_from_moon": house,
            "favourable": house in K.GOCHARA_FAVOURABLE[planet],
        })
    return rows


def _saturn_sign(jd: float, config: EngineConfig) -> int:
    config.apply_sid_mode()
    pos, _ = swe.calc_ut(jd, swe.SATURN, config.calc_flags)
    return int((pos[0] % 360.0) // 30)


def _scan_saturn_span(on_dt_utc: datetime, natal_moon_sign: int,
                      config: EngineConfig, in_zone, years: int = 10) -> tuple:
    """Approximate (start, end) of the contiguous span around `on_dt_utc`
    where `in_zone(saturn_house_from_moon)` holds. Coarse 10-day scan with
    1-day refinement; returns (None, None) if not currently in zone."""
    jd0 = julian_day_from_utc(on_dt_utc)

    def in_zone_at(jd: float) -> bool:
        return in_zone(_house_from(_saturn_sign(jd, config), natal_moon_sign))

    if not in_zone_at(jd0):
        return None, None

    def edge(direction: int) -> float:
        jd = jd0
        limit = jd0 + direction * years * 365.25
        step = direction * 10.0
        while in_zone_at(jd) and (jd - limit) * direction < 0:
            jd += step
        # refine to ~1 day
        lo = jd - step
        for _ in range(15):
            mid = (lo + jd) / 2.0
            if in_zone_at(mid):
                lo = mid
            else:
                jd = mid
        return lo

    start_jd, end_jd = edge(-1), edge(+1)
    from .ephemeris import jd_to_utc_datetime
    return jd_to_utc_datetime(start_jd), jd_to_utc_datetime(end_jd)


def sade_sati(on_dt_utc: datetime, natal_moon_sign: int,
              config: EngineConfig | None = None, positions: dict | None = None) -> dict:
    config = config or EngineConfig()
    positions = positions or transit_positions(on_dt_utc, config)
    sat_house = _house_from(positions["Saturn"]["sign"], natal_moon_sign)
    active = sat_house in (12, 1, 2)
    result = {
        "active": active,
        "saturn_house_from_moon": sat_house,
        "phase": {12: "rising (first dhaiya)", 1: "peak (second dhaiya)",
                  2: "setting (third dhaiya)"}.get(sat_house),
        "start": None,
        "end": None,
        "ashtama_shani": sat_house == 8,
        "kantaka_shani": sat_house in (4, 7),
    }
    if active:
        start, end = _scan_saturn_span(on_dt_utc, natal_moon_sign, config,
                                       lambda h: h in (12, 1, 2))
        result["start"] = start.isoformat() if start else None
        result["end"] = end.isoformat() if end else None
    return result


def double_transit(natal_lagna_sign: int, positions: dict) -> list[dict]:
    """Houses (from lagna) receiving BOTH Saturn's and Jupiter's presence or
    graha drishti."""
    sat_sign = positions["Saturn"]["sign"]
    jup_sign = positions["Jupiter"]["sign"]
    hits = []
    for h in range(1, 13):
        sign = (natal_lagna_sign + h - 1) % 12
        sat = sat_sign == sign or K.aspects_sign("Saturn", sat_sign, sign)
        jup = jup_sign == sign or K.aspects_sign("Jupiter", jup_sign, sign)
        if sat and jup:
            hits.append({
                "house": h,
                "sign": sign,
                "sign_name": K.SIGN_NAMES[sign],
                "saturn": "occupies" if sat_sign == sign else "aspects",
                "jupiter": "occupies" if jup_sign == sign else "aspects",
            })
    return hits


def compute_transits(natal_chart: dict, on_dt_utc: datetime,
                     config: EngineConfig | None = None) -> dict:
    config = config or EngineConfig()
    positions = transit_positions(on_dt_utc, config)
    moon_sign = natal_chart["planets"]["Moon"]["sign"]
    lagna_sign = natal_chart["lagna"]["sign"]
    return {
        "on": on_dt_utc.isoformat(),
        "positions": positions,
        "gochara": gochara_table(moon_sign, positions),
        "sade_sati": sade_sati(on_dt_utc, moon_sign, config, positions),
        "double_transit": double_transit(lagna_sign, positions),
    }
