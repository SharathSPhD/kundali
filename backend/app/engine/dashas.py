"""Vimshottari dasha tree: maha -> antar -> pratyantar (recursive, 3-5 levels).

Convention: the first mahadasha's sub-periods are computed from its *notional*
start (birth minus the elapsed fraction of the Moon's nakshatra), then clipped
to birth — this matches how consumer tools report the running antardasha at
birth. Year length (365.25 or 360 days) comes from EngineConfig.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import constants as K
from .ephemeris import EngineConfig

LEVEL_NAMES = ["mahadasha", "antardasha", "pratyantardasha", "sookshma", "prana"]


def dasha_balance(moon_longitude: float) -> dict:
    """Starting lord and remaining fraction of its mahadasha at birth."""
    lon = moon_longitude % 360.0
    nak_index = int(lon / K.NAKSHATRA_SPAN) % 27
    elapsed_fraction = (lon - nak_index * K.NAKSHATRA_SPAN) / K.NAKSHATRA_SPAN
    lord = K.NAKSHATRA_LORDS[nak_index]
    years = K.VIMSHOTTARI_YEARS[lord]
    return {
        "nakshatra_index": nak_index,
        "nakshatra": K.NAKSHATRA_NAMES[nak_index],
        "lord": lord,
        "elapsed_fraction": elapsed_fraction,
        "balance_years": years * (1.0 - elapsed_fraction),
    }


def _sequence_from(lord: str) -> list[str]:
    i = K.VIMSHOTTARI_ORDER.index(lord)
    return [K.VIMSHOTTARI_ORDER[(i + j) % 9] for j in range(9)]


def _expand(lord: str, start: datetime, duration_days: float, level: int,
            max_level: int, clip_start: datetime, horizon: datetime) -> dict | None:
    end = start + timedelta(days=duration_days)
    if end <= clip_start or start >= horizon:
        return None
    node = {
        "lord": lord,
        "level": level,
        "level_name": LEVEL_NAMES[level - 1],
        "start": max(start, clip_start).isoformat(),
        "end": min(end, horizon).isoformat(),
    }
    if level < max_level:
        children = []
        child_start = start
        for sub in _sequence_from(lord):
            child_days = duration_days * K.VIMSHOTTARI_YEARS[sub] / K.VIMSHOTTARI_TOTAL_YEARS
            child = _expand(sub, child_start, child_days, level + 1,
                            max_level, clip_start, horizon)
            if child:
                children.append(child)
            child_start += timedelta(days=child_days)
        node["children"] = children
    return node


def build_vimshottari(moon_longitude: float, birth_dt: datetime,
                      config: EngineConfig | None = None, levels: int = 3) -> dict:
    """Full tree covering 120 years from birth. `birth_dt` is local civil time
    (all returned dates are in the same frame)."""
    config = config or EngineConfig()
    levels = max(1, min(levels, 5))
    year = config.dasha_year_days
    bal = dasha_balance(moon_longitude)

    horizon = birth_dt + timedelta(days=K.VIMSHOTTARI_TOTAL_YEARS * year)
    first_lord = bal["lord"]
    first_years = K.VIMSHOTTARI_YEARS[first_lord]
    notional_start = birth_dt - timedelta(days=bal["elapsed_fraction"] * first_years * year)

    periods = []
    start = notional_start
    seq = _sequence_from(first_lord)
    i = 0
    while start < horizon:
        lord = seq[i % 9]
        days = K.VIMSHOTTARI_YEARS[lord] * year
        node = _expand(lord, start, days, 1, levels, birth_dt, horizon)
        if node:
            periods.append(node)
        start += timedelta(days=days)
        i += 1

    return {
        "balance": bal,
        "birth": birth_dt.isoformat(),
        "horizon": horizon.isoformat(),
        "year_days": year,
        "levels": levels,
        "periods": periods,
    }


def active_path(tree: dict, on_date: datetime) -> list[dict]:
    """[maha, antar, pratyantar, ...] nodes active on `on_date`."""
    iso = on_date.isoformat()
    path = []
    nodes = tree["periods"]
    while nodes:
        hit = None
        for n in nodes:
            if n["start"] <= iso < n["end"]:
                hit = n
                break
        if hit is None:
            break
        path.append({k: hit[k] for k in ("lord", "level", "level_name", "start", "end")})
        nodes = hit.get("children", [])
    return path
