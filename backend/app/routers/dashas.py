from __future__ import annotations

from fastapi import APIRouter

from ..auth import UserDep
from ..engine.chart import build_chart
from ..engine.dashas import active_path, build_vimshottari
from ..schemas import DashasRequest
from ._common import parse_on, to_birth, to_config

router = APIRouter(prefix="/api", tags=["dashas"])


@router.post("/dashas")
def dashas(req: DashasRequest, user: dict = UserDep):
    birth = to_birth(req.birth)
    config = to_config(req.config)
    natal = build_chart(birth, config)
    tree = build_vimshottari(natal["planets"]["Moon"]["longitude"],
                             birth.local_datetime(), config, levels=req.levels)
    on = parse_on(req.on)
    return {"tree": tree, "active": active_path(tree, on), "on": on.isoformat()}
