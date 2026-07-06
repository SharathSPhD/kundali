from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

import main as gateway_main


@pytest.fixture(autouse=True)
def _secrets(monkeypatch):
    monkeypatch.setattr(gateway_main, "INTERNAL_SECRET", "internal-test-secret")
    monkeypatch.setattr(gateway_main, "PAID_SECRET", "paid-test-secret")
    monkeypatch.setattr(gateway_main, "ALLOWED_MODELS", {"llama3.1:8b"})


@pytest.fixture
def client():
    return TestClient(gateway_main.app)


def test_healthz_needs_no_auth(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_chat_without_auth_is_rejected(client):
    resp = client.post("/api/chat", json={"model": "llama3.1:8b"})
    assert resp.status_code == 401


def test_chat_with_wrong_secret_is_rejected(client):
    resp = client.post(
        "/api/chat",
        json={"model": "llama3.1:8b"},
        headers={"Authorization": "Bearer not-a-real-secret"},
    )
    assert resp.status_code == 401


def test_chat_rejects_disallowed_model(client):
    resp = client.post(
        "/api/chat",
        json={"model": "nemotron-3-super:120b"},
        headers={"Authorization": "Bearer internal-test-secret"},
    )
    assert resp.status_code == 400
    assert "not on this gateway" in resp.json()["detail"]


def test_chat_proxies_to_ollama_for_internal_secret(client, monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        content = b'{"message": {"content": "hi"}}'
        headers = {"content-type": "application/json"}

    class FakeAsyncClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(gateway_main.httpx, "AsyncClient", FakeAsyncClient)

    resp = client.post(
        "/api/chat",
        json={"model": "llama3.1:8b", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": "Bearer internal-test-secret"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": {"content": "hi"}}
    assert captured["url"].endswith("/api/chat")


def test_chat_accepts_paid_secret_too(client, monkeypatch):
    class FakeResponse:
        status_code = 200
        content = b"{}"
        headers = {"content-type": "application/json"}

    class FakeAsyncClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            return FakeResponse()

    monkeypatch.setattr(gateway_main.httpx, "AsyncClient", FakeAsyncClient)

    resp = client.post(
        "/api/chat",
        json={"model": "llama3.1:8b"},
        headers={"Authorization": "Bearer paid-test-secret"},
    )
    assert resp.status_code == 200


def test_upstream_failure_returns_502(client, monkeypatch):
    class FakeAsyncClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(gateway_main.httpx, "AsyncClient", FakeAsyncClient)

    resp = client.post(
        "/api/chat",
        json={"model": "llama3.1:8b"},
        headers={"Authorization": "Bearer internal-test-secret"},
    )
    assert resp.status_code == 502
