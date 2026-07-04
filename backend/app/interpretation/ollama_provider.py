"""Ollama provider: POSTs to a local Ollama server's /api/chat with the
grounding contract as the system prompt."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx

from .base import GROUNDING_CONTRACT, InterpretationProvider


class OllamaProvider(InterpretationProvider):
    name = "ollama"

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None,
                 timeout: float = 120.0):
        self.base_url = (base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.1")
        self.timeout = timeout

    def interpret(self, engine_payload: dict[str, Any],
                  question: Optional[str] = None) -> dict:
        user_content = (
            "Engine payload (the ONLY source of truth):\n"
            + json.dumps(engine_payload, default=str)
            + "\n\nQuestion: "
            + (question or "Give a general reading for the current period.")
        )
        body = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": GROUNDING_CONTRACT},
                {"role": "user", "content": user_content},
            ],
        }
        resp = httpx.post(f"{self.base_url}/api/chat", json=body, timeout=self.timeout)
        resp.raise_for_status()
        text = resp.json().get("message", {}).get("content", "")
        return {"text": text, "citations": _extract_citations(text), "provider": self.name}


def _extract_citations(text: str) -> list[str]:
    """Pull [ ... ] style citations the contract asks the model to emit."""
    import re
    return list(dict.fromkeys(re.findall(r"\[([^\[\]]{3,80})\]", text)))
