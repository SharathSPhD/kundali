"""Tier-aware provider resolution.

Priority, per user (any tier may have BYOK; tier only matters when there's
no BYOK credential):

    1. BYOK           — a `user_llm_credentials` row exists for the
                         requested (or any) provider -> use it. Works for
                         every tier, including `basic`. Ollama accepts either
                         an api_key OR a base_url (local instances often need
                         no key).
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
from .base import InterpretationProvider, UnsafeBaseUrlError, assert_safe_user_base_url

PROVIDER_PRIORITY = ["anthropic", "openai", "gemini", "ollama"]
_TIMEOUT = 10.0
_RUNTIME_CONFIG_CACHE: dict = {"values": None, "fetched_at": 0.0}
_RUNTIME_CONFIG_TTL = 300.0


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


def get_user_tier(token: Optional[str], user_id: Optional[str]) -> str:
    if not token or not user_id:
        return "basic"
    # `user_tiers` has a permissive "admin can see/edit all rows" policy
    # (see supabase/schema.sql) that combines with the owner-select policy
    # via OR, so an admin caller who doesn't filter by their own id would
    # get every row in the table back instead of just theirs. Filter
    # explicitly rather than relying on RLS to narrow this to one row.
    rows = _rest_get("user_tiers", token, {"select": "tier", "user_id": f"eq.{user_id}"})
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


def _runtime_config() -> dict[str, str]:
    """Non-secret deployment config stored in Supabase (`runtime_config`
    table, anon-readable). This is how the gateway URL and default model
    reach a Vercel deployment without anyone touching dashboard env vars —
    the GB10 box registers itself and every serverless instance picks it
    up here. Env vars, when present, still win (see callers)."""
    import time

    now = time.time()
    if (
        _RUNTIME_CONFIG_CACHE["values"] is not None
        and now - _RUNTIME_CONFIG_CACHE["fetched_at"] < _RUNTIME_CONFIG_TTL
    ):
        return _RUNTIME_CONFIG_CACHE["values"]
    base, anon = _supabase_url(), _anon_key()
    values: dict[str, str] = {}
    if base and anon:
        try:
            resp = httpx.get(
                f"{base}/rest/v1/runtime_config",
                headers={"apikey": anon, "Authorization": f"Bearer {anon}"},
                params={"select": "key,value"},
                timeout=_TIMEOUT,
            )
            if resp.status_code == 200:
                values = {row["key"]: row["value"] for row in resp.json()}
        except httpx.HTTPError:
            values = {}
    _RUNTIME_CONFIG_CACHE.update(values=values, fetched_at=now)
    return values


def _gb10_provider(secret: str) -> Optional[InterpretationProvider]:
    gateway_url = os.environ.get("OLLAMA_GATEWAY_URL") or _runtime_config().get(
        "ollama_gateway_url"
    )
    if not gateway_url or not secret:
        return None
    return get_provider(
        "ollama",
        base_url=gateway_url,
        api_key=secret,
        model=os.environ.get("GB10_MODEL") or _runtime_config().get("gb10_default_model"),
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
    user_id = user.get("sub")

    candidates = [requested_provider] if requested_provider else PROVIDER_PRIORITY
    for name in candidates:
        if not name or name in ("template",):
            continue
        cred = get_user_credential(token, name)
        if not cred:
            continue
        base_url = cred.get("base_url")
        if base_url:
            try:
                assert_safe_user_base_url(base_url)
            except UnsafeBaseUrlError as exc:
                # This backend makes the outbound request itself, so a
                # stored base_url pointing at a private/link-local/metadata
                # address is an SSRF vector, not just a bad user setting.
                # Refuse explicitly rather than silently falling through to
                # another provider or a confusing generic "blocked" message.
                raise ProviderBlocked(
                    reason=f"Your {name} base URL is not usable: {exc}",
                    upgrade_hint="invalid_base_url",
                ) from exc
        if name == "ollama":
            if cred.get("api_key") or base_url:
                provider = get_provider(
                    name,
                    api_key=cred.get("api_key") or "",
                    base_url=base_url,
                )
                return provider, f"your {name.capitalize()} key"
        elif cred.get("api_key"):
            provider = get_provider(name, api_key=cred["api_key"], base_url=base_url)
            return provider, f"your {name.capitalize()} key"

    tier = get_user_tier(token, user_id)

    # Shared secret when configured; otherwise forward the caller's own
    # Supabase JWT — the gateway verifies it and checks the tier itself
    # (see gb10-gateway/main.py), so admin/guest/paid chat works with zero
    # secret coordination between this deployment and the GB10 box.
    if tier in ("admin", "guest"):
        secret = os.environ.get("GB10_INTERNAL_SECRET", "") or (token or "")
        provider = _gb10_provider(secret)
        if provider:
            return provider, "Kundali (GB10)"

    if tier == "paid":
        secret = os.environ.get("GB10_PAID_SECRET", "") or (token or "")
        provider = _gb10_provider(secret)
        if provider:
            return provider, "Kundali (GB10)"

    if tier in ("admin", "guest", "paid"):
        # This tier *should* have gateway access — the block is a deployment
        # gap (no gateway URL registered), not a account limitation. Say so.
        raise ProviderBlocked(
            reason=(
                f"Your account tier ({tier}) includes AI chat, but no GB10 "
                "gateway is registered. An admin should start the gateway on "
                "GB10 (gb10-gateway/deploy-local.sh + tailscale funnel) and "
                "set its URL under Admin → GB10 gateway. Deterministic Ask "
                "answers still work meanwhile."
            ),
            upgrade_hint="gateway_not_configured",
        )
    raise ProviderBlocked(
        reason=(
            f"Your account ({tier}) has no inference access configured. "
            "Add your own Anthropic/OpenAI/Gemini/Ollama API key, or ask an "
            "admin to upgrade your tier."
        ),
        upgrade_hint="byok_or_upgrade",
    )
