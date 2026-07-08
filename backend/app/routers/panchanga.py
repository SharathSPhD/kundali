from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from ..auth import UserDep
from ..engine.matching import match
from ..engine.muhurta import scan_muhurta
from ..engine.panchanga import compute_panchanga
from ..schemas import MatchingRequest, MuhurtaRequest, PanchangaRequest
from ._common import to_birth, to_config

router = APIRouter(prefix="/api", tags=["panchanga"])


@router.post("/panchanga")
def panchanga(req: PanchangaRequest, user: dict = UserDep):
    return compute_panchanga(to_birth(req.birth), to_config(req.config))


@router.post("/matching")
def matching(req: MatchingRequest, user: dict = UserDep):
    return match(to_birth(req.groom), to_birth(req.bride), to_config(req.config))


@router.post("/muhurta")
def muhurta(req: MuhurtaRequest, user: dict = UserDep):
    """Personalized electional scan: rank upcoming days for an activity
    using tara bala / chandra bala from the caller's own janma nakshatra."""
    try:
        start = date.fromisoformat(req.from_date) if req.from_date else date.today()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"bad from_date: {req.from_date}") from exc
    try:
        return scan_muhurta(
            to_birth(req.birth), req.activity, start, req.days, to_config(req.config)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
