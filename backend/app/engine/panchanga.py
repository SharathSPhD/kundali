"""Panchanga (five limbs of the Vedic day) for a birth moment.

Conventions (documented decisions):
- Tithi   = floor(((Moon - Sun) mod 360) / 12) + 1  (1..30).
- Vara    = weekday of the most recent sunrise at or before the birth moment
            (the Vedic day runs sunrise to sunrise). A birth at 01:25 local
            therefore belongs to the *previous* civil day's vara.
- Sunrise = swe.rise_trans with SE_CALC_RISE and default flags, i.e. the
            Swiss Ephemeris default of upper-limb rising with standard
            atmospheric refraction (Drik Panchang uses the same convention;
            disc-center vs upper-limb differs by ~1 minute and never changes
            the vara in practice).
- Yoga    = floor(((Sun + Moon) mod 360) / 13°20') + 1  (1..27).
- Karana  = half-tithi: K = floor(((Moon - Sun) mod 360) / 6), K in 0..59.
            K=0 Kimstughna; K=57 Shakuni, 58 Chatushpada, 59 Naga (fixed);
            K=1..56 cycle through the 7 movable karanas starting with Bava.
- Sunrise/sunset are returned as local-time ISO strings using tz_offset.
  In polar conditions (no rise/set) they are null and the vara falls back
  to the local civil date's weekday.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

import swisseph as swe

from . import constants as K
from .ephemeris import (
    BirthData,
    EngineConfig,
    jd_to_utc_datetime,
    julian_day_from_utc,
    nakshatra_of,
    planet_longitudes,
)

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi",
]  # 15th of Shukla = Purnima; 30th (15th of Krishna) = Amavasya

VARA_NAMES = [
    "Ravivara", "Somavara", "Mangalavara", "Budhavara",
    "Guruvara", "Shukravara", "Shanivara",
]
VARA_LORDS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shoola", "Ganda", "Vriddhi",
    "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata",
    "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha",
    "Shukla", "Brahma", "Indra", "Vaidhriti",
]

MOVABLE_KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
FIXED_KARANAS = {0: "Kimstughna", 57: "Shakuni", 58: "Chatushpada", 59: "Naga"}


def tithi_of(elongation: float) -> dict:
    """Tithi from Moon-Sun elongation in degrees (0..360)."""
    elong = elongation % 360.0
    number = int(elong / 12.0) + 1
    if number > 30:  # guard against elong == 360 float edge
        number = 30
    if number == 15:
        name = "Purnima"
    elif number == 30:
        name = "Amavasya"
    else:
        name = TITHI_NAMES[(number - 1) % 15]
    paksha = "Shukla" if number <= 15 else "Krishna"
    return {"number": number, "name": name, "paksha": paksha,
            "elongation": round(elong, 4)}


def yoga_of(sum_longitude: float) -> dict:
    """Yoga from (Sun + Moon) longitude sum in degrees."""
    s = sum_longitude % 360.0
    number = int(s / K.NAKSHATRA_SPAN) + 1
    if number > 27:
        number = 27
    return {"number": number, "name": YOGA_NAMES[number - 1]}


def karana_of(elongation: float) -> dict:
    """Karana (half-tithi) from Moon-Sun elongation in degrees."""
    elong = elongation % 360.0
    idx = int(elong / 6.0)
    if idx > 59:
        idx = 59
    if idx in FIXED_KARANAS:
        name = FIXED_KARANAS[idx]
    else:
        name = MOVABLE_KARANAS[(idx - 1) % 7]
    return {"number": idx, "name": name}


def _sun_rise_or_set(jd_start: float, rsmi: int, lat: float, lon: float,
                     config: EngineConfig) -> Optional[float]:
    """Next Sun rise/set (JD UT) strictly after jd_start, or None (polar)."""
    geopos = (lon, lat, 0.0)
    try:
        res, tret = swe.rise_trans(jd_start, swe.SUN, rsmi, geopos,
                                   0.0, 0.0, config.ephe_flag)
    except TypeError:  # older pyswisseph signature without flags kwarg
        res, tret = swe.rise_trans(jd_start, swe.SUN, rsmi, geopos)
    if res != 0:
        return None
    return tret[0]


def most_recent_sunrise(jd: float, lat: float, lon: float,
                        config: EngineConfig) -> Optional[float]:
    """JD (UT) of the last sunrise at or before jd at the given location."""
    t = jd - 2.0
    last = None
    for _ in range(8):
        r = _sun_rise_or_set(t, swe.CALC_RISE, lat, lon, config)
        if r is None:
            return last
        if r > jd + 1e-9:
            break
        last = r
        t = r + 1e-3
    return last


def _local_iso(jd_ut: float, tz_offset: float) -> str:
    dt = jd_to_utc_datetime(jd_ut) + timedelta(hours=tz_offset)
    return dt.replace(microsecond=0).isoformat()


def compute_panchanga(birth: BirthData, config: Optional[EngineConfig] = None) -> dict:
    config = config or EngineConfig()
    jd = julian_day_from_utc(birth.utc_datetime())

    positions = planet_longitudes(jd, config)
    sun = positions["Sun"]["longitude"]
    moon = positions["Moon"]["longitude"]
    elong = (moon - sun) % 360.0

    tithi = tithi_of(elong)
    yoga = yoga_of(sun + moon)
    karana = karana_of(elong)
    nak = nakshatra_of(moon)
    nakshatra = {
        "index": nak["index"],
        "name": nak["name"],
        "pada": nak["pada"],
        "lord": nak["lord"],
    }

    # Vara: weekday of the most recent sunrise (sunrise-to-sunrise day).
    sunrise_jd = most_recent_sunrise(jd, birth.lat, birth.lon, config)
    if sunrise_jd is not None:
        vara_local = jd_to_utc_datetime(sunrise_jd) + timedelta(hours=birth.tz_offset)
        sunset_jd = _sun_rise_or_set(sunrise_jd + 1e-3, swe.CALC_SET,
                                     birth.lat, birth.lon, config)
        sunrise_iso = _local_iso(sunrise_jd, birth.tz_offset)
        sunset_iso = (_local_iso(sunset_jd, birth.tz_offset)
                      if sunset_jd is not None else None)
    else:
        # Polar fallback: use the local civil date's weekday.
        vara_local = birth.local_datetime()
        sunrise_iso = None
        sunset_iso = None
    # Python weekday(): Monday=0 .. Sunday=6 -> Ravivara(=Sunday) index 0.
    vara_index = (vara_local.weekday() + 1) % 7
    vara = {"index": vara_index, "name": VARA_NAMES[vara_index],
            "lord": VARA_LORDS[vara_index]}

    return {
        "tithi": tithi,
        "vara": vara,
        "nakshatra": nakshatra,
        "yoga": yoga,
        "karana": karana,
        "sunrise": sunrise_iso,
        "sunset": sunset_iso,
        "sun_longitude": round(sun, 6),
        "moon_longitude": round(moon, 6),
        "jd": jd,
        "ayanamsa": config.ayanamsa,
    }
