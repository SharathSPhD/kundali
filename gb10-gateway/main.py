"""Gateway in front of local Ollama, with two independent auth paths.

Vercel serverless functions can't reach this machine directly, so this
process runs on GB10 itself, sits in front of raw Ollama (which has no
native API-key auth), and is exposed publicly only via a secure tunnel
(Tailscale Funnel or Cloudflare Tunnel — see README.md) — never by
opening an inbound port.

Auth paths, tried in order on every request:

1. **Shared secrets** — `GB10_INTERNAL_SECRET` (admin/guest traffic from
   the Vercel backend) and `GB10_PAID_SECRET` (paid tier). Service-level
   trust: the tier decision already happened in
   `backend/app/interpretation/gateway.py` before the secret was sent.
2. **Supabase user JWT** — the Vercel backend forwards the *caller's own*
   session token when it has no shared secret configured. This gateway
   verifies the token against Supabase (`/auth/v1/user`, cached) and then
   reads the caller's tier from `user_tiers` via Supabase REST using that
   same token (RLS scopes it to their own row). Tiers `admin`, `guest`
   and `paid` are allowed. This path needs zero secret coordination
   between Vercel and this box — it is what makes chat work out of the
   box for admin/guest accounts.
"""
from __future__ import annotations

import hmac
import json
import os
import time
from typing import Any, Optional

import anyio.to_thread
import httpx
from fastapi import FastAPI, Header, HTTPException, Response

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
INTERNAL_SECRET = os.environ.get("GB10_INTERNAL_SECRET", "")
PAID_SECRET = os.environ.get("GB10_PAID_SECRET", "")
# Modest models only while the GPU is shared — never the 65-86GB models
# also pulled on this box.
ALLOWED_MODELS = {
    m.strip()
    for m in os.environ.get(
        "GB10_ALLOWED_MODELS", "qwen2.5:14b,llama3.1:8b,gemma2:9b,qwen2.5:7b"
    ).split(",")
    if m.strip()
}
# JWT tiers allowed to use this gateway (comma-separated, overridable).
ALLOWED_TIERS = {
    t.strip()
    for t in os.environ.get("GB10_ALLOWED_TIERS", "admin,guest,paid").split(",")
    if t.strip()
}


def _supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if url:
        return url
    # Fall back to the repo's public deploy_config.json (same convention as
    # backend/app/auth.py) so the JWT path works with zero env config.
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = os.path.normpath(os.path.join(here, "..", "deploy_config.json"))
    if os.path.exists(cfg):
        try:
            with open(cfg) as f:
                return str(json.load(f).get("supabase_url", "")).rstrip("/")
        except Exception:  # noqa: BLE001
            pass
    return ""


SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

_TIMEOUT = httpx.Timeout(180.0, connect=10.0)
_AUTH_TIMEOUT = 10.0
_TIER_CACHE: dict[str, dict] = {}
_TIER_TTL = 300.0

app = FastAPI(title="Kundali GB10 gateway", version="2.0")


def _valid_secret(token: str) -> bool:
    for secret in (INTERNAL_SECRET, PAID_SECRET):
        if secret and hmac.compare_digest(token, secret):
            return True
    return False


def _jwt_tier(token: str) -> Optional[str]:
    """Validate `token` as a Supabase user JWT and return the caller's tier,
    or None if the token is not a valid Supabase session.

    Uses introspection (`/auth/v1/user`) rather than local JWKS verification
    so this stays dependency-light; results are cached briefly. The tier
    lookup rides the same token, so RLS returns only the caller's own row.
    """
    base = _supabase_url()
    if not base or not token or token.count(".") != 2:
        return None
    now = time.time()
    cached = _TIER_CACHE.get(token)
    if cached and now - cached["at"] < _TIER_TTL:
        return cached["tier"]
    try:
        user_resp = httpx.get(
            f"{base}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                **({"apikey": SUPABASE_ANON_KEY} if SUPABASE_ANON_KEY else {}),
            },
            timeout=_AUTH_TIMEOUT,
        )
        if user_resp.status_code != 200:
            return None
        user_id = user_resp.json().get("id")
        if not user_id:
            return None
        tier = "basic"
        if SUPABASE_ANON_KEY:
            tier_resp = httpx.get(
                f"{base}/rest/v1/user_tiers",
                headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"},
                params={"select": "tier", "user_id": f"eq.{user_id}"},
                timeout=_AUTH_TIMEOUT,
            )
            if tier_resp.status_code == 200:
                rows = tier_resp.json()
                if rows and rows[0].get("tier"):
                    tier = str(rows[0]["tier"])
    except httpx.HTTPError:
        return None
    if len(_TIER_CACHE) > 512:
        _TIER_CACHE.clear()
    _TIER_CACHE[token] = {"tier": tier, "at": now}
    return tier


async def _require_auth(authorization: str) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if _valid_secret(token):
        return
    # _jwt_tier does synchronous HTTP (introspection + tier lookup, cached);
    # run it in a worker thread so it never blocks the event loop under
    # concurrent chat requests.
    tier = await anyio.to_thread.run_sync(_jwt_tier, token)
    if tier in ALLOWED_TIERS:
        return
    if tier is not None:
        raise HTTPException(
            status_code=403,
            detail=f"tier '{tier}' has no gateway access (needs one of {sorted(ALLOWED_TIERS)})",
        )
    raise HTTPException(status_code=401, detail="invalid gateway credential")


@app.get("/healthz")
def healthz() -> dict:
    # Deliberately minimal: this endpoint is unauthenticated (uptime
    # monitors need it to be), so it must not leak infrastructure details
    # (upstream URL, model allow-list) that would aid reconnaissance.
    return {"ok": True}


@app.get("/api/models")
async def models(authorization: str = Header(default="")) -> dict:
    """Authenticated: which models this gateway will serve (for pickers)."""
    await _require_auth(authorization)
    return {"models": sorted(ALLOWED_MODELS)}


@app.post("/api/chat")
async def chat(body: dict[str, Any], authorization: str = Header(default="")) -> Response:
    """Proxies to Ollama's own `/api/chat` shape — `OllamaProvider` in the
    Vercel backend talks to this exact endpoint whether it's pointed at
    localhost (dev) or this gateway (prod), just with a different
    `base_url`/`api_key`."""
    await _require_auth(authorization)
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
