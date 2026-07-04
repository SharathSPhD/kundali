from __future__ import annotations

from fastapi import APIRouter

from ..auth import UserDep
from ..engine.chart import build_chart
from ..engine.transits import compute_transits
from ..schemas import TransitsRequest
from ._common import parse_on, to_birth, to_config

router = APIRouter(prefix="/api", tags=["transits"])


@router.post("/transits")
def transits(req: TransitsRequest, user: dict = UserDep):
    config = to_config(req.config)
    natal = build_chart(to_birth(req.birth), config)
    return compute_transits(natal, parse_on(req.on), config)
