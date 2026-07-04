from __future__ import annotations

from fastapi import APIRouter

from ..auth import UserDep
from ..engine.predictions import predict
from ..engine.rectification import rectify
from ..schemas import PredictionsRequest, RectifyRequest
from ._common import parse_on, to_birth, to_config

router = APIRouter(prefix="/api", tags=["predictions"])


@router.post("/predictions")
def predictions(req: PredictionsRequest, user: dict = UserDep):
    return predict(to_birth(req.birth), parse_on(req.on), to_config(req.config))


@router.post("/rectify")
def rectify_endpoint(req: RectifyRequest, user: dict = UserDep):
    events = [e.model_dump() for e in req.events]
    return rectify(to_birth(req.birth), req.window_minutes, events,
                   to_config(req.config), step_minutes=req.step_minutes)
