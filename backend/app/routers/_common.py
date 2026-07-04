from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException

from ..engine.ephemeris import BirthData, EngineConfig
from ..schemas import BirthDataModel, EngineConfigModel


def to_birth(m: BirthDataModel) -> BirthData:
    return BirthData(date=m.date, time=m.time, lat=m.lat, lon=m.lon,
                     tz_offset=m.tz_offset, place_name=m.place_name)


def to_config(m: Optional[EngineConfigModel]) -> EngineConfig:
    if m is None:
        return EngineConfig()
    try:
        return EngineConfig(ayanamsa=m.ayanamsa, node_type=m.node_type,
                            dasha_year_days=m.dasha_year_days)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def parse_on(on: Optional[str]) -> datetime:
    if not on:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(on)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"bad date: {on}") from exc
