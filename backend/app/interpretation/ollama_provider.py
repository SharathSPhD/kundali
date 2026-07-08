"""Ollama provider: POSTs to a local Ollama server's /api/chat with the
grounding contract as the system prompt."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx

from .base import GROUNDING_CONTRACT, InterpretationProvider, history_to_messages


class OllamaProvider(InterpretationProvider):
    """Talks to raw Ollama (`/api/chat`) for local dev, or to the GB10
    tunnel gateway (see `backend/app/interpretation/gateway.py`) when
    `base_url`/`api_key` point there — the gateway speaks the same
    Ollama-shaped `/api/chat` contract behind its own bearer-token check."""

    name = "ollama"

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None,
                 timeout: float = 120.0, api_key: Optional[str] = None, **_ignored):
        self.base_url = (base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.1")
        self.timeout = timeout
        self.api_key = api_key

    def interpret(self, engine_payload: dict[str, Any],
                  question: Optional[str] = None,
                  history: Optional[list[dict]] = None) -> dict:
        user_content = (
            "Engine payload (the ONLY source of truth):\n"
            + json.dumps(engine_payload, default=str)
            + "\n\nQuestion: "
            + (question or "Give a general reading for the current period.")
        )
        body = {
            "model": self.model,
            "stream": False,
            "messages": (
                [{"role": "system", "content": GROUNDING_CONTRACT}]
                + history_to_messages(history)
                + [{"role": "user", "content": user_content}]
            ),
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            resp = httpx.post(f"{self.base_url}/api/chat", json=body, headers=headers,
                              timeout=self.timeout)
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"The Ollama gateway at {self.base_url} is unreachable — the GB10 "
                "machine may be offline or its tunnel down. Try again shortly, or "
                "use the deterministic Ask mode which needs no AI server."
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"The Ollama gateway timed out (model '{self.model}' may still be "
                "loading into memory). Retry in a minute."
            ) from exc
        if resp.status_code in (401, 403):
            raise RuntimeError(
                "The Ollama gateway rejected this account's credentials "
                f"(HTTP {resp.status_code}: {resp.text[:200]})."
            )
        if resp.status_code == 400:
            raise RuntimeError(f"The Ollama gateway refused the request: {resp.text[:300]}")
        resp.raise_for_status()
        text = resp.json().get("message", {}).get("content", "")
        return {"text": text, "citations": _extract_citations(text), "provider": self.name}


def _extract_citations(text: str) -> list[str]:
    """Pull [ ... ] style citations the contract asks the model to emit."""
    import re
    return list(dict.fromkeys(re.findall(r"\[([^\[\]]{3,80})\]", text)))
