"""Tier-aware provider resolution.

Priority, per user (any tier may have BYOK; tier only matters when there's
no BYOK credential):

    1. BYOK           — a `user_llm_credentials` row exists for the
                         requested (or any) provider -> use it. Works for
                         every tier, including `basic`.
    2. admin / guest   — call the GB10 gateway server-to-server (trusted
                         internal secret, no per-user key needed).
    3. paid            — call the GB10 gateway with a stored app-level
                         secret (placeholder until the real one is
                         supplied; the hook is what matters now).
    4. basic, no BYOK  — blocked; caller renders an upgrade/BYOK prompt.

This module never makes an LLM call itself — it only decides which
`InterpretationProvider` to construct (or raises `ProviderBlocked`). It
resolves the caller's own tier/credentials by forwarding their own bearer
token to Supabase REST, so Postgres RLS naturally scopes results to that
user — no service-role key is needed here, matching how the frontend
already talks to Supabase directly for birth profiles.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

from ..auth import _supabase_url
from . import get_provider
from .base import InterpretationProvider

PROVIDER_PRIORITY = ["anthropic", "openai", "gemini", "ollama"]
_TIMEOUT = 10.0


class ProviderBlocked(Exception):
    """Raised when no inference path is available for this user/request."""

    def __init__(self, reason: str, upgrade_hint: str):
        self.reason = reason
        self.upgrade_hint = upgrade_hint
        super().__init__(reason)


def _anon_key() -> str:
    return (
        os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
    )


def _rest_get(path: str, token: str, params: dict) -> list[dict]:
    base, anon = _supabase_url(), _anon_key()
    if not base or not anon or not token:
        return []
    resp = httpx.get(
        f"{base}/rest/v1/{path}",
        headers={"apikey": anon, "Authorization": f"Bearer {token}"},
        params=params,
        timeout=_TIMEOUT,
    )
    if resp.status_code != 200:
        return []
    return resp.json()


def get_user_tier(token: Optional[str]) -> str:
    if not token:
        return "basic"
    rows = _rest_get("user_tiers", token, {"select": "tier"})
    if rows and rows[0].get("tier"):
        return str(rows[0]["tier"])
    return "basic"


def get_user_credential(token: Optional[str], provider: str) -> Optional[dict]:
    if not token:
        return None
    rows = _rest_get(
        "user_llm_credentials", token,
        {"select": "api_key,base_url", "provider": f"eq.{provider}"},
    )
    return rows[0] if rows else None


def _gb10_provider(secret: str) -> Optional[InterpretationProvider]:
    gateway_url = os.environ.get("OLLAMA_GATEWAY_URL")
    if not gateway_url:
        return None
    return get_provider(
        "ollama",
        base_url=gateway_url,
        api_key=secret,
        model=os.environ.get("GB10_MODEL"),
    )


def resolve_provider(
    user: dict, requested_provider: Optional[str] = None
) -> tuple[InterpretationProvider, str]:
    """Returns `(provider, via)` where `via` is a short human-readable
    description of the resolved path (e.g. "your Anthropic key", "Kundali
    (GB10)") for the frontend to display. Raises `ProviderBlocked` if no
    path is available.
    """
    token = user.get("token")

    candidates = [requested_provider] if requested_provider else PROVIDER_PRIORITY
    for name in candidates:
        if not name or name in ("template",):
            continue
        cred = get_user_credential(token, name)
        if cred and cred.get("api_key"):
            provider = get_provider(name, api_key=cred["api_key"], base_url=cred.get("base_url"))
            return provider, f"your {name.capitalize()} key"

    tier = get_user_tier(token)

    if tier in ("admin", "guest"):
        provider = _gb10_provider(os.environ.get("GB10_INTERNAL_SECRET", ""))
        if provider:
            return provider, "Kundali (GB10)"

    if tier == "paid":
        provider = _gb10_provider(os.environ.get("GB10_PAID_SECRET", ""))
        if provider:
            return provider, "Kundali (GB10)"

    raise ProviderBlocked(
        reason=(
            f"Your account ({tier}) has no inference access configured. "
            "Add your own Anthropic/OpenAI/Gemini/Ollama API key, or ask an "
            "admin to upgrade your tier."
        ),
        upgrade_hint="byok_or_upgrade",
    )
