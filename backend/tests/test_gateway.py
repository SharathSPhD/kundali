"""Tier-aware provider resolution: BYOK > admin/guest GB10 > paid GB10 >
blocked. Network calls (Supabase REST, provider construction) are avoided
by monkeypatching the two lookup functions directly."""
from __future__ import annotations

import ipaddress
import socket as socket_module

import pytest

from app.interpretation import base as base_module
from app.interpretation import gateway
from app.interpretation.anthropic_provider import AnthropicProvider
from app.interpretation.ollama_provider import OllamaProvider


def _user(token="tok-abc"):
    return {"sub": "user-1", "token": token}


@pytest.fixture(autouse=True)
def _fake_public_dns(monkeypatch):
    """Every BYOK base_url in this file resolves through
    `assert_safe_user_base_url`'s DNS check; stub it to a fake public
    resolver so tests don't depend on live network access, except where a
    test explicitly wants to exercise a private/loopback rejection (those
    tests use literal IPs, which skip DNS resolution entirely)."""
    def _getaddrinfo(host, *_a, **_kw):
        if host == "localhost":
            return [(socket_module.AF_INET, socket_module.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass  # not a literal IP — fall through to the fake public resolution below
        else:
            return [(socket_module.AF_INET, socket_module.SOCK_STREAM, 6, "", (host, 0))]
        return [(socket_module.AF_INET, socket_module.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
    monkeypatch.setattr(base_module.socket, "getaddrinfo", _getaddrinfo)


def test_byok_wins_over_tier(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential",
                         lambda token, name: {"api_key": "sk-test", "base_url": None}
                         if name == "anthropic" else None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "basic")

    provider, via = gateway.resolve_provider(_user())

    assert isinstance(provider, AnthropicProvider)
    assert provider.api_key == "sk-test"
    assert "Anthropic" in via


def test_admin_tier_uses_gb10_gateway_without_byok(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential", lambda token, name: None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "admin")
    monkeypatch.setenv("OLLAMA_GATEWAY_URL", "https://gb10.example.com")
    monkeypatch.setenv("GB10_INTERNAL_SECRET", "internal-secret")

    provider, via = gateway.resolve_provider(_user())

    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "https://gb10.example.com"
    assert provider.api_key == "internal-secret"
    assert "GB10" in via


def test_paid_tier_uses_gb10_gateway_with_stored_secret(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential", lambda token, name: None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "paid")
    monkeypatch.setenv("OLLAMA_GATEWAY_URL", "https://gb10.example.com")
    monkeypatch.setenv("GB10_PAID_SECRET", "paid-secret")

    provider, via = gateway.resolve_provider(_user())

    assert isinstance(provider, OllamaProvider)
    assert provider.api_key == "paid-secret"


def test_basic_tier_no_byok_no_gateway_is_blocked(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential", lambda token, name: None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "basic")
    monkeypatch.delenv("OLLAMA_GATEWAY_URL", raising=False)

    with pytest.raises(gateway.ProviderBlocked):
        gateway.resolve_provider(_user())


def test_admin_tier_without_gateway_url_configured_is_blocked(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential", lambda token, name: None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "admin")
    monkeypatch.delenv("OLLAMA_GATEWAY_URL", raising=False)

    with pytest.raises(gateway.ProviderBlocked):
        gateway.resolve_provider(_user())


def test_requested_provider_restricts_byok_lookup_to_that_provider(monkeypatch):
    seen = []

    def fake_cred(token, name):
        seen.append(name)
        return None

    monkeypatch.setattr(gateway, "get_user_credential", fake_cred)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "basic")

    with pytest.raises(gateway.ProviderBlocked):
        gateway.resolve_provider(_user(), requested_provider="openai")

    assert seen == ["openai"]


def test_get_user_tier_filters_rest_query_by_own_user_id(monkeypatch):
    """`user_tiers` has a permissive admin-all-rows RLS policy alongside the
    owner-only select policy; since Postgres OR-combines permissive
    policies, an admin caller who queries without a `user_id` filter would
    get every row in the table back (see supabase/schema.sql). Guard against
    regressing back to that by asserting the REST call is always scoped to
    the caller's own id."""
    seen_params = {}

    def fake_rest_get(path, token, params):
        seen_params.update(params)
        return [{"tier": "admin"}]

    monkeypatch.setattr(gateway, "_rest_get", fake_rest_get)

    tier = gateway.get_user_tier("tok-abc", "user-1")

    assert tier == "admin"
    assert seen_params.get("user_id") == "eq.user-1"


def test_get_user_tier_without_user_id_defaults_to_basic(monkeypatch):
    def fake_rest_get(path, token, params):
        raise AssertionError("should not hit REST without a user_id")

    monkeypatch.setattr(gateway, "_rest_get", fake_rest_get)

    assert gateway.get_user_tier("tok-abc", None) == "basic"


def test_ollama_byok_accepts_base_url_without_api_key(monkeypatch):
    monkeypatch.setattr(
        gateway,
        "get_user_credential",
        lambda token, name: {"api_key": "", "base_url": "https://my-ollama.example.com"}
        if name == "ollama"
        else None,
    )
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "basic")

    provider, via = gateway.resolve_provider(_user())

    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "https://my-ollama.example.com"
    assert provider.api_key == ""
    assert "Ollama" in via


def test_byok_base_url_pointing_at_loopback_is_rejected(monkeypatch):
    """SSRF guard: this backend makes the outbound request itself, so a
    stored base_url resolving to loopback/private/link-local must be
    refused rather than silently dialed."""
    monkeypatch.setattr(
        gateway,
        "get_user_credential",
        lambda token, name: {"api_key": "", "base_url": "http://localhost:11434"}
        if name == "ollama"
        else None,
    )
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "basic")

    with pytest.raises(gateway.ProviderBlocked, match="not usable"):
        gateway.resolve_provider(_user())


def test_byok_base_url_pointing_at_cloud_metadata_ip_is_rejected(monkeypatch):
    monkeypatch.setattr(
        gateway,
        "get_user_credential",
        lambda token, name: {"api_key": "sk-test", "base_url": "http://169.254.169.254/latest/"}
        if name == "openai"
        else None,
    )
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "basic")

    with pytest.raises(gateway.ProviderBlocked, match="not usable"):
        gateway.resolve_provider(_user(), requested_provider="openai")


def test_byok_base_url_non_http_scheme_is_rejected(monkeypatch):
    monkeypatch.setattr(
        gateway,
        "get_user_credential",
        lambda token, name: {"api_key": "", "base_url": "file:///etc/passwd"}
        if name == "ollama"
        else None,
    )
    monkeypatch.setattr(gateway, "get_user_tier", lambda token, user_id: "basic")

    with pytest.raises(gateway.ProviderBlocked, match="not usable"):
        gateway.resolve_provider(_user())
