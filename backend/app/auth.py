"""Supabase JWT verification.

- Primary: JWKS (cached 1h), ES256/RS256. URL from SUPABASE_JWKS_URL, or
  derived from SUPABASE_URL, or from deploy_config.json at the repo root
  (Vercel deployments, where no env vars are configured).
- Fallback A: HS256 with SUPABASE_JWT_SECRET (legacy projects).
- Fallback B: token introspection against Supabase /auth/v1/user (legacy
  HS256 tokens without a shared secret) — result cached briefly.
- AUTH_DISABLED=1 bypasses verification (local dev / tests).
Audience must be 'authenticated'.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request

_JWKS_CACHE: dict = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL = 3600.0
_INTROSPECT_CACHE: dict = {}
_INTROSPECT_TTL = 300.0


def _auth_disabled() -> bool:
    return os.environ.get("AUTH_DISABLED", "0") in ("1", "true", "yes")


def _guard_auth_disabled_in_deployed_env() -> None:
    """Refuse to import this module (and thus start the app) if someone
    mis-sets AUTH_DISABLED=1 on a real deployment. Vercel sets `VERCEL=1`
    for every deployment including previews (not just production) — a
    preview URL is still reachable over the public internet, so any
    detected deployment is treated as unsafe, not just VERCEL_ENV=='production'.
    """
    if not _auth_disabled():
        return
    if os.environ.get("VERCEL") or os.environ.get("RENDER"):
        raise RuntimeError(
            "AUTH_DISABLED=1 is set in a deployed environment (VERCEL/RENDER "
            "detected) — refusing to start. This would allow unauthenticated "
            "access to every engine/interpret endpoint. AUTH_DISABLED is for "
            "local dev/tests only; unset it in this environment's variables."
        )


_guard_auth_disabled_in_deployed_env()


def _supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
    if url:
        return url.rstrip("/")
    # deploy_config.json lives at the repo root (one level above backend/).
    here = os.path.dirname(os.path.abspath(__file__))
    for up in ("../..", "../../.."):
        cfg = os.path.normpath(os.path.join(here, up, "deploy_config.json"))
        if os.path.exists(cfg):
            try:
                with open(cfg) as f:
                    return str(json.load(f).get("supabase_url", "")).rstrip("/")
            except Exception:  # noqa: BLE001
                pass
    return ""


def _jwks_url() -> str:
    explicit = os.environ.get("SUPABASE_JWKS_URL", "")
    if explicit:
        return explicit
    base = _supabase_url()
    return f"{base}/auth/v1/.well-known/jwks.json" if base else ""


def _introspect(token: str) -> dict:
    """Validate a token by asking Supabase who it belongs to."""
    base = _supabase_url()
    if not base:
        raise HTTPException(status_code=401, detail="Cannot verify token (no Supabase URL)")
    now = time.time()
    cached = _INTROSPECT_CACHE.get(token)
    if cached and now - cached["at"] < _INTROSPECT_TTL:
        return cached["claims"]
    resp = httpx.get(
        f"{base}/auth/v1/user",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Token rejected by Supabase")
    user = resp.json()
    claims = {"sub": user.get("id"), "email": user.get("email"), "role": "authenticated"}
    if len(_INTROSPECT_CACHE) > 512:
        _INTROSPECT_CACHE.clear()
    _INTROSPECT_CACHE[token] = {"claims": claims, "at": now}
    return claims


def _get_jwks(url: str) -> dict:
    now = time.time()
    if _JWKS_CACHE["keys"] is not None and now - _JWKS_CACHE["fetched_at"] < _JWKS_TTL:
        return _JWKS_CACHE["keys"]
    resp = httpx.get(url, timeout=10.0)
    resp.raise_for_status()
    jwks = resp.json()
    _JWKS_CACHE.update(keys=jwks, fetched_at=now)
    return jwks


def _verify_token(token: str) -> dict:
    import jwt as pyjwt  # PyJWT
    from jwt import PyJWK

    header = pyjwt.get_unverified_header(token)
    alg = header.get("alg", "")
    jwks_url = _jwks_url()

    if alg in ("ES256", "RS256") and jwks_url:
        jwks = _get_jwks(jwks_url)
        kid = header.get("kid")
        key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key_data is None:
            # kid rotation: force refetch once
            _JWKS_CACHE["fetched_at"] = 0.0
            jwks = _get_jwks(jwks_url)
            key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key_data is None:
            raise HTTPException(status_code=401, detail="Unknown signing key")
        key = PyJWK.from_dict(key_data).key
        return pyjwt.decode(token, key=key, algorithms=[alg], audience="authenticated")

    secret = os.environ.get("SUPABASE_JWT_SECRET", "")
    if alg == "HS256" and secret:
        return pyjwt.decode(token, key=secret, algorithms=["HS256"], audience="authenticated")

    # Last resort: introspection (works for any Supabase-issued token).
    return _introspect(token)


async def require_user(request: Request) -> dict:
    """FastAPI dependency: returns JWT claims (or a stub when disabled).

    The raw bearer token is included as `claims["token"]` so downstream code
    (see `interpretation/gateway.py`) can forward it to Supabase REST and get
    RLS-scoped results for exactly this user — no service-role key needed to
    resolve a user's own tier/credentials.
    """
    if _auth_disabled():
        return {"sub": "dev-user", "role": "authenticated", "auth": "disabled", "token": None}

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.removeprefix("Bearer ").strip()
    try:
        claims = _verify_token(token)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — any decode error is a 401
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
    claims["token"] = token
    return claims


UserDep = Depends(require_user)
