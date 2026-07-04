from __future__ import annotations

from fastapi import APIRouter

from ..auth import UserDep
from ..engine.chart import build_chart
from ..engine.jaimini import compute_jaimini
from ..engine.shadbala import compute_shadbala
from ..schemas import JaiminiRequest, ShadbalaRequest
from ._common import parse_on, to_birth, to_config

router = APIRouter(prefix="/api", tags=["strength"])


@router.post("/shadbala")
def shadbala(req: ShadbalaRequest, user: dict = UserDep):
    return compute_shadbala(to_birth(req.birth), to_config(req.config))


@router.post("/jaimini")
def jaimini(req: JaiminiRequest, user: dict = UserDep):
    birth = to_birth(req.birth)
    config = to_config(req.config)
    chart = build_chart(birth, config)
    return compute_jaimini(chart, birth.local_datetime(), config,
                           on=parse_on(req.on))
