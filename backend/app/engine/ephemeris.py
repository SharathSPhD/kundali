"""Swiss Ephemeris wrapper: sidereal longitudes, ascendant, nakshatra math.

Empirically verified lagna method (see tests): `swe.houses_ex(jd, lat, lon,
b'W', swe.FLG_SIDEREAL)` returns the sidereal ascendant in ascmc[0]. This was
cross-checked against tropical houses minus `swe.get_ayanamsa_ut(jd)` and the
two agree to < 0.005 deg (residual is nutation handling inside swisseph).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import swisseph as swe

from . import constants as K

AYANAMSA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,           # 1  — default; matches Drik Panchang
    "raman": swe.SIDM_RAMAN,             # 3
    "krishnamurti": swe.SIDM_KRISHNAMURTI,  # 5 (KP)
    "true_chitra": swe.SIDM_TRUE_CITRA,  # 27 — Chitra at exactly 180°
    "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
}

_PLANET_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}


def _ephemeris_files_present(path: str) -> bool:
    if not path or not os.path.isdir(path):
        return False
    return any(f.endswith(".se1") for f in os.listdir(path))


@dataclass
class EngineConfig:
    ayanamsa: str = "lahiri"
    node_type: str = "mean"          # 'mean' | 'true'
    dasha_year_days: float = 365.25  # or 360.0 (savana)
    ephe_path: Optional[str] = None
    ephe_flag: int = field(default=0)

    def __post_init__(self):
        if self.ayanamsa not in AYANAMSA_MODES:
            raise ValueError(f"unknown ayanamsa: {self.ayanamsa}")
        if self.node_type not in ("mean", "true"):
            raise ValueError(f"node_type must be 'mean' or 'true', got {self.node_type}")
        if not self.ephe_flag:
            path = self.ephe_path or os.environ.get("SE_EPHE_PATH", "")
            if _ephemeris_files_present(path):
                swe.set_ephe_path(path)
                self.ephe_flag = swe.FLG_SWIEPH
            else:
                self.ephe_flag = swe.FLG_MOSEPH

    @property
    def sid_mode(self) -> int:
        return AYANAMSA_MODES[self.ayanamsa]

    @property
    def calc_flags(self) -> int:
        return self.ephe_flag | swe.FLG_SIDEREAL | swe.FLG_SPEED

    @property
    def node_id(self) -> int:
        return swe.MEAN_NODE if self.node_type == "mean" else swe.TRUE_NODE

    def apply_sid_mode(self) -> None:
        swe.set_sid_mode(self.sid_mode, 0, 0)


@dataclass
class BirthData:
    date: str            # 'YYYY-MM-DD' (local)
    time: str            # 'HH:MM' or 'HH:MM:SS' (local)
    lat: float
    lon: float
    tz_offset: float     # hours east of UTC
    place_name: Optional[str] = None

    def local_datetime(self) -> datetime:
        parts = self.time.split(":")
        h, m = int(parts[0]), int(parts[1])
        s = int(parts[2]) if len(parts) > 2 else 0
        y, mo, d = (int(x) for x in self.date.split("-"))
        return datetime(y, mo, d, h, m, s)

    def utc_datetime(self) -> datetime:
        return self.local_datetime() - timedelta(hours=self.tz_offset)


def julian_day_from_utc(dt_utc: datetime) -> float:
    return swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )


def julian_day(date: str, time: str, tz_offset: float) -> float:
    """Julian day (UT) from local civil date/time and timezone offset in hours."""
    b = BirthData(date=date, time=time, lat=0.0, lon=0.0, tz_offset=tz_offset)
    return julian_day_from_utc(b.utc_datetime())


def jd_to_utc_datetime(jd: float) -> datetime:
    y, mo, d, h = swe.revjul(jd)
    hh = int(h)
    mm = int((h - hh) * 60)
    ss = int(round(((h - hh) * 60 - mm) * 60))
    if ss >= 60:
        ss -= 60
        mm += 1
    if mm >= 60:
        mm -= 60
        hh += 1
    return datetime(y, mo, d, min(hh, 23), min(mm, 59), min(ss, 59))


def ayanamsa_value(jd: float, config: EngineConfig) -> float:
    config.apply_sid_mode()
    return swe.get_ayanamsa_ut(jd)


def nakshatra_of(longitude: float) -> dict:
    lon = longitude % 360.0
    idx = int(lon / K.NAKSHATRA_SPAN) % 27
    within = lon - idx * K.NAKSHATRA_SPAN
    pada = int(within / K.PADA_SPAN) + 1
    fraction = within / K.NAKSHATRA_SPAN  # 0..1 elapsed within the nakshatra
    return {
        "index": idx,
        "name": K.NAKSHATRA_NAMES[idx],
        "pada": min(pada, 4),
        "lord": K.NAKSHATRA_LORDS[idx],
        "fraction": fraction,
    }


def _position_dict(lon: float, speed: float) -> dict:
    lon = lon % 360.0
    sign = int(lon // 30)
    nak = nakshatra_of(lon)
    return {
        "longitude": round(lon, 6),
        "speed": round(speed, 6),
        "retrograde": speed < 0,
        "sign": sign,
        "sign_name": K.SIGN_NAMES[sign],
        "degree_in_sign": round(lon % 30.0, 4),
        "nakshatra": nak["name"],
        "nakshatra_index": nak["index"],
        "pada": nak["pada"],
        "nakshatra_lord": nak["lord"],
    }


def planet_longitudes(jd: float, config: EngineConfig) -> dict:
    """Sidereal longitudes + speeds of the 9 grahas. Ketu = Rahu + 180."""
    config.apply_sid_mode()
    flags = config.calc_flags
    out = {}
    for name, pid in _PLANET_IDS.items():
        pos, _ = swe.calc_ut(jd, pid, flags)
        out[name] = _position_dict(pos[0], pos[3])
    rahu, _ = swe.calc_ut(jd, config.node_id, flags)
    out["Rahu"] = _position_dict(rahu[0], rahu[3])
    out["Ketu"] = _position_dict(rahu[0] + 180.0, rahu[3])
    return out


def ascendant(jd: float, lat: float, lon: float, config: EngineConfig) -> dict:
    """Sidereal ascendant via whole-sign houses_ex with FLG_SIDEREAL."""
    config.apply_sid_mode()
    _cusps, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
    return _position_dict(ascmc[0], 0.0)
