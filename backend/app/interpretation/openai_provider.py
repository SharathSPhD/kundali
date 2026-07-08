"""OpenAI provider: plain REST call to /v1/chat/completions (no SDK
dependency needed — mirrors the httpx approach already used by
OllamaProvider). Supports BYOK: `api_key` is required, either from
OPENAI_API_KEY or a per-user stored key threaded in by the gateway."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx

from .base import GROUNDING_CONTRACT, InterpretationProvider, history_to_messages, slim_payload_for_prompt
from .ollama_provider import _extract_citations


class OpenAIProvider(InterpretationProvider):
    name = "openai"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None,
                 base_url: Optional[str] = None, timeout: float = 60.0, **_ignored):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set (and no BYOK key supplied)")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout

    def interpret(self, engine_payload: dict[str, Any],
                  question: Optional[str] = None,
                  history: Optional[list[dict]] = None) -> dict:
        user_content = (
            "Engine payload (the ONLY source of truth):\n"
            + json.dumps(slim_payload_for_prompt(engine_payload), default=str)
            + "\n\nQuestion: "
            + (question or "Give a general reading for the current period.")
        )
        messages = (
            [{"role": "system", "content": GROUNDING_CONTRACT}]
            + history_to_messages(history)
            + [{"role": "user", "content": user_content}]
        )
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": messages},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return {"text": text, "citations": _extract_citations(text), "provider": self.name}
