from __future__ import annotations

from fastapi import APIRouter

from ..auth import UserDep
from ..engine.ashtakavarga import compute_ashtakavarga
from ..engine.chart import build_chart
from ..engine.vargas import compute_vargas
from ..engine.yogas import evaluate_yogas
from ..schemas import AshtakavargaRequest, ChartRequest, VargasRequest, YogasRequest
from ._common import to_birth, to_config

router = APIRouter(prefix="/api", tags=["charts"])


@router.post("/chart")
def chart(req: ChartRequest, user: dict = UserDep):
    return build_chart(to_birth(req.birth), to_config(req.config))


@router.post("/vargas")
def vargas(req: VargasRequest, user: dict = UserDep):
    natal = build_chart(to_birth(req.birth), to_config(req.config))
    return compute_vargas(natal, req.charts)


@router.post("/yogas")
def yogas(req: YogasRequest, user: dict = UserDep):
    natal = build_chart(to_birth(req.birth), to_config(req.config))
    return {"yogas": evaluate_yogas(natal)}


@router.post("/ashtakavarga")
def ashtakavarga(req: AshtakavargaRequest, user: dict = UserDep):
    natal = build_chart(to_birth(req.birth), to_config(req.config))
    return compute_ashtakavarga(natal)
