"""Tier-aware provider resolution: BYOK > admin/guest GB10 > paid GB10 >
blocked. Network calls (Supabase REST, provider construction) are avoided
by monkeypatching the two lookup functions directly."""
from __future__ import annotations

import pytest

from app.interpretation import gateway
from app.interpretation.anthropic_provider import AnthropicProvider
from app.interpretation.ollama_provider import OllamaProvider


def _user(token="tok-abc"):
    return {"sub": "user-1", "token": token}


def test_byok_wins_over_tier(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential",
                         lambda token, name: {"api_key": "sk-test", "base_url": None}
                         if name == "anthropic" else None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token: "basic")

    provider, via = gateway.resolve_provider(_user())

    assert isinstance(provider, AnthropicProvider)
    assert provider.api_key == "sk-test"
    assert "Anthropic" in via


def test_admin_tier_uses_gb10_gateway_without_byok(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential", lambda token, name: None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token: "admin")
    monkeypatch.setenv("OLLAMA_GATEWAY_URL", "https://gb10.example.com")
    monkeypatch.setenv("GB10_INTERNAL_SECRET", "internal-secret")

    provider, via = gateway.resolve_provider(_user())

    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "https://gb10.example.com"
    assert provider.api_key == "internal-secret"
    assert "GB10" in via


def test_paid_tier_uses_gb10_gateway_with_stored_secret(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential", lambda token, name: None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token: "paid")
    monkeypatch.setenv("OLLAMA_GATEWAY_URL", "https://gb10.example.com")
    monkeypatch.setenv("GB10_PAID_SECRET", "paid-secret")

    provider, via = gateway.resolve_provider(_user())

    assert isinstance(provider, OllamaProvider)
    assert provider.api_key == "paid-secret"


def test_basic_tier_no_byok_no_gateway_is_blocked(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential", lambda token, name: None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token: "basic")
    monkeypatch.delenv("OLLAMA_GATEWAY_URL", raising=False)

    with pytest.raises(gateway.ProviderBlocked):
        gateway.resolve_provider(_user())


def test_admin_tier_without_gateway_url_configured_is_blocked(monkeypatch):
    monkeypatch.setattr(gateway, "get_user_credential", lambda token, name: None)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token: "admin")
    monkeypatch.delenv("OLLAMA_GATEWAY_URL", raising=False)

    with pytest.raises(gateway.ProviderBlocked):
        gateway.resolve_provider(_user())


def test_requested_provider_restricts_byok_lookup_to_that_provider(monkeypatch):
    seen = []

    def fake_cred(token, name):
        seen.append(name)
        return None

    monkeypatch.setattr(gateway, "get_user_credential", fake_cred)
    monkeypatch.setattr(gateway, "get_user_tier", lambda token: "basic")

    with pytest.raises(gateway.ProviderBlocked):
        gateway.resolve_provider(_user(), requested_provider="openai")

    assert seen == ["openai"]
