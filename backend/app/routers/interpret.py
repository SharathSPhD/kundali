from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..auth import UserDep
from ..engine.predictions import predict
from ..interpretation import get_provider
from ..interpretation.gateway import ProviderBlocked, resolve_provider
from ..schemas import InterpretRequest, InterpretResponse
from ._common import parse_on, to_birth, to_config

router = APIRouter(prefix="/api", tags=["interpret"])


@router.post("/interpret", response_model=InterpretResponse)
def interpret(req: InterpretRequest, user: dict = UserDep):
    payload = predict(to_birth(req.birth), parse_on(req.on), to_config(req.config))
    history = [turn.model_dump() for turn in (req.history or [])]

    if req.provider == "template":
        # Always-on, ungated, zero-LLM narration — never goes through tier
        # resolution so it stays available to every account, always.
        provider, via = get_provider("template"), "template"
    else:
        try:
            provider, via = resolve_provider(user, req.provider)
        except ProviderBlocked as exc:
            return InterpretResponse(
                text="",
                citations=[],
                provider="blocked",
                blocked=True,
                upgrade_hint=exc.reason,
                engine_payload=payload,
            )
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        result = provider.interpret(payload, req.question, history)
    except Exception as exc:  # provider/network failure -> 502
        raise HTTPException(status_code=502, detail=f"provider error: {exc}") from exc
    result["engine_payload"] = payload
    result["via"] = via
    return result
