"""Thin API-key-gated gateway in front of local Ollama.

Vercel serverless functions can't reach this machine directly, so this
process runs on GB10 itself, sits in front of raw Ollama (which has no
native API-key auth), and is exposed publicly only via a Cloudflare Tunnel
(see README.md) — never by opening an inbound port.

Two trust paths share the same endpoints; both are just "does the caller
hold one of our two valid secrets", not "which tier is this":
  - GB10_INTERNAL_SECRET — sent by the Vercel backend for admin/guest users
    (server-to-server trust, no per-user key).
  - GB10_PAID_SECRET — sent by the Vercel backend for paid-tier users on
    stored app credentials (placeholder value until the real one is
    supplied; the hook is what matters now).
The *tier* decision already happened in `backend/app/interpretation/
gateway.py` before either secret is ever sent here — this process only
proxies to Ollama and refuses anyone without a valid secret.
"""
from __future__ import annotations

import hmac
import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Response

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
INTERNAL_SECRET = os.environ.get("GB10_INTERNAL_SECRET", "")
PAID_SECRET = os.environ.get("GB10_PAID_SECRET", "")
# Modest models only (see plan) — never the 65-86GB models already pulled.
ALLOWED_MODELS = {
    m.strip()
    for m in os.environ.get("GB10_ALLOWED_MODELS", "llama3.1:8b,qwen2.5:14b").split(",")
    if m.strip()
}
_TIMEOUT = httpx.Timeout(180.0, connect=10.0)

app = FastAPI(title="Kundali GB10 gateway", version="1.0")


def _valid_secret(token: str) -> bool:
    for secret in (INTERNAL_SECRET, PAID_SECRET):
        if secret and hmac.compare_digest(token, secret):
            return True
    return False


def _require_auth(authorization: str) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not _valid_secret(token):
        raise HTTPException(status_code=401, detail="invalid gateway credential")


@app.get("/healthz")
def healthz() -> dict:
    # Deliberately minimal: this endpoint is unauthenticated (uptime
    # monitors need it to be), so it must not leak infrastructure details
    # (upstream URL, model allow-list) that would aid reconnaissance.
    return {"ok": True}


@app.post("/api/chat")
async def chat(body: dict[str, Any], authorization: str = Header(default="")) -> Response:
    """Proxies to Ollama's own `/api/chat` shape — `OllamaProvider` in the
    Vercel backend talks to this exact endpoint whether it's pointed at
    localhost (dev) or this gateway (prod), just with a different
    `base_url`/`api_key`."""
    _require_auth(authorization)
    model = body.get("model")
    if ALLOWED_MODELS and model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"model '{model}' is not on this gateway's allow-list: {sorted(ALLOWED_MODELS)}",
        )
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(f"{OLLAMA_URL}/api/chat", json=body)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"upstream Ollama error: {exc}") from exc
    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "application/json"),
        status_code=resp.status_code,
    )
