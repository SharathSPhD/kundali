from __future__ import annotations

from fastapi import APIRouter

from ..auth import UserDep
from ..engine.matching import match
from ..engine.panchanga import compute_panchanga
from ..schemas import MatchingRequest, PanchangaRequest
from ._common import to_birth, to_config

router = APIRouter(prefix="/api", tags=["panchanga"])


@router.post("/panchanga")
def panchanga(req: PanchangaRequest, user: dict = UserDep):
    return compute_panchanga(to_birth(req.birth), to_config(req.config))


@router.post("/matching")
def matching(req: MatchingRequest, user: dict = UserDep):
    return match(to_birth(req.groom), to_birth(req.bride), to_config(req.config))
