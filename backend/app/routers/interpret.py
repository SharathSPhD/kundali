from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..auth import UserDep
from ..engine.predictions import predict
from ..interpretation import get_provider
from ..interpretation.gateway import ProviderBlocked, resolve_provider
from ..oracle.answers import build_answer_packet
from ..oracle.claim_parser import parse_claims
from ..oracle.export import export_facts
from ..oracle.intent import classify_intent
from ..oracle.verify_claims import verify_claims
from ..schemas import InterpretRequest, InterpretResponse
from ._common import parse_on, to_birth, to_config

router = APIRouter(prefix="/api", tags=["interpret"])


def _run_claim_verification(text: str, payload: dict) -> dict:
    claims = parse_claims(text)
    facts = export_facts(payload)
    return verify_claims(claims, facts)


@router.post("/interpret", response_model=InterpretResponse)
def interpret(req: InterpretRequest, user: dict = UserDep):
    payload = predict(to_birth(req.birth), parse_on(req.on), to_config(req.config))
    history = [turn.model_dump() for turn in (req.history or [])]
    question = (req.question or "").strip()

    if req.provider == "template":
        if question:
            intent_result = classify_intent(question)
            packet = build_answer_packet(
                intent_result["intent"], payload, question
            )
            result = {
                "text": packet["text"],
                "citations": packet["citations"],
                "provider": "template_qa",
            }
            via = None
        else:
            provider, via = get_provider("template"), "template"
            try:
                result = provider.interpret(payload, req.question, history)
            except Exception as exc:
                raise HTTPException(
                    status_code=502, detail=f"provider error: {exc}"
                ) from exc
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
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"provider error: {exc}"
            ) from exc

    result["engine_payload"] = payload
    result["via"] = via

    # Claim verification for real LLM responses only.
    if result.get("provider") not in ("template", "template_qa", "blocked"):
        verification = _run_claim_verification(result.get("text", ""), payload)
        result["verified"] = verification["verified"]
        result["rejected_claims"] = verification["rejected_claims"]
        result["verification_warnings"] = verification["verification_warnings"]

    return result
