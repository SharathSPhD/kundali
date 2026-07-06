"""Guard against AUTH_DISABLED=1 accidentally shipping to a deployed env."""
import pytest

from app.auth import _guard_auth_disabled_in_deployed_env


def test_auth_disabled_without_deploy_markers_is_fine(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "1")
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    _guard_auth_disabled_in_deployed_env()  # must not raise


def test_auth_disabled_on_vercel_raises(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "1")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("RENDER", raising=False)
    with pytest.raises(RuntimeError, match="AUTH_DISABLED"):
        _guard_auth_disabled_in_deployed_env()


def test_auth_disabled_on_render_raises(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "1")
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("VERCEL", raising=False)
    with pytest.raises(RuntimeError, match="AUTH_DISABLED"):
        _guard_auth_disabled_in_deployed_env()


def test_auth_enabled_on_vercel_is_fine(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("VERCEL", "1")
    _guard_auth_disabled_in_deployed_env()  # must not raise
