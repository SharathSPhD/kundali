"""Pydantic v2 request/response models."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class BirthDataModel(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD (local civil date)")
    time: str = Field(..., description="HH:MM or HH:MM:SS (local civil time)")
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    tz_offset: float = Field(..., ge=-14, le=14, description="hours east of UTC")
    place_name: Optional[str] = None

    @field_validator("date")
    @classmethod
    def _check_date(cls, v: str) -> str:
        parts = v.split("-")
        if (len(parts) != 3 or not all(p.isdigit() for p in parts)
                or len(parts[0]) != 4
                or not 1 <= int(parts[1]) <= 12
                or not 1 <= int(parts[2]) <= 31):
            raise ValueError("date must be YYYY-MM-DD")
        return v

    @field_validator("time")
    @classmethod
    def _check_time(cls, v: str) -> str:
        parts = v.split(":")
        if (len(parts) not in (2, 3) or not all(p.isdigit() for p in parts)
                or int(parts[0]) > 23 or int(parts[1]) > 59
                or (len(parts) == 3 and int(parts[2]) > 59)):
            raise ValueError("time must be HH:MM or HH:MM:SS")
        return v


class EngineConfigModel(BaseModel):
    ayanamsa: str = "lahiri"
    node_type: str = "mean"
    dasha_year_days: float = 365.25


class ChartRequest(BaseModel):
    birth: BirthDataModel
    config: Optional[EngineConfigModel] = None


class VargasRequest(BaseModel):
    birth: BirthDataModel
    charts: Optional[list[str]] = None
    config: Optional[EngineConfigModel] = None


class DashasRequest(BaseModel):
    birth: BirthDataModel
    levels: int = Field(default=3, ge=1, le=5)
    on: Optional[str] = Field(default=None, description="ISO date for active path")
    config: Optional[EngineConfigModel] = None


class TransitsRequest(BaseModel):
    birth: BirthDataModel
    on: Optional[str] = None
    config: Optional[EngineConfigModel] = None


class YogasRequest(BaseModel):
    birth: BirthDataModel
    config: Optional[EngineConfigModel] = None


class AshtakavargaRequest(BaseModel):
    birth: BirthDataModel
    config: Optional[EngineConfigModel] = None


class PanchangaRequest(BaseModel):
    birth: BirthDataModel
    config: Optional[EngineConfigModel] = None


class MatchingRequest(BaseModel):
    groom: BirthDataModel
    bride: BirthDataModel
    config: Optional[EngineConfigModel] = None


class ShadbalaRequest(BaseModel):
    birth: BirthDataModel
    config: Optional[EngineConfigModel] = None


class JaiminiRequest(BaseModel):
    birth: BirthDataModel
    on: Optional[str] = Field(default=None, description="ISO date for active chara path")
    config: Optional[EngineConfigModel] = None


class PredictionsRequest(BaseModel):
    birth: BirthDataModel
    on: Optional[str] = None
    config: Optional[EngineConfigModel] = None


class LifeEvent(BaseModel):
    type: str
    date: str = Field(..., description="YYYY-MM-DD")
    note: Optional[str] = None


# The frontend's own UI caps window at 360 and step at 1, i.e. at most
# 2*360/1 + 1 = 721 candidates — each a full chart+dasha recomputation.
# window_minutes is capped to match here (was 720, doubling worst-case
# compute per request for no product benefit — nothing in the app ever
# requests more).
class RectifyRequest(BaseModel):
    birth: BirthDataModel
    window_minutes: int = Field(default=60, ge=1, le=360)
    step_minutes: int = Field(default=2, ge=1, le=30)
    events: list[LifeEvent] = Field(..., min_length=1, max_length=25)
    config: Optional[EngineConfigModel] = None


class ChatTurn(BaseModel):
    """One prior Q&A pair, oldest-first, for lightweight multi-turn context."""
    question: str
    answer: str


class InterpretRequest(BaseModel):
    birth: BirthDataModel
    question: Optional[str] = None
    # None = tier/BYOK auto-resolution (see interpretation/gateway.py);
    # "template" = always-on deterministic narration, no gating, no LLM.
    # Any other explicit name (anthropic/openai/gemini/ollama) restricts
    # auto-resolution to that provider's BYOK credential only.
    provider: Optional[str] = None
    history: Optional[list[ChatTurn]] = None
    on: Optional[str] = None
    config: Optional[EngineConfigModel] = None


class InterpretResponse(BaseModel):
    text: str
    citations: list[str] = []
    provider: str
    via: Optional[str] = None
    blocked: bool = False
    upgrade_hint: Optional[str] = None
    engine_payload: Optional[dict[str, Any]] = None
    verified: Optional[bool] = None
    rejected_claims: list[dict[str, Any]] = []
    verification_warnings: list[str] = []
    # Knowledge-graph Q&A: the derivation chain behind a deterministic
    # answer — each step binds a cited classical rule to a computed chart
    # fact ({claim, rule, source, facts}).
    derivation: list[dict[str, Any]] = []
    answer_kind: Optional[str] = None
