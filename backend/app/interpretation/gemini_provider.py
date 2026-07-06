"""Gemini provider: plain REST call to the Generative Language API
(generateContent) — no SDK dependency, same pattern as OllamaProvider /
OpenAIProvider. Supports BYOK."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx

from .base import GROUNDING_CONTRACT, InterpretationProvider
from .ollama_provider import _extract_citations


class GeminiProvider(InterpretationProvider):
    name = "gemini"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None,
                 base_url: Optional[str] = None, timeout: float = 60.0, **_ignored):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set (and no BYOK key supplied)")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self.timeout = timeout

    def interpret(self, engine_payload: dict[str, Any],
                  question: Optional[str] = None,
                  history: Optional[list[dict]] = None) -> dict:
        user_content = (
            "Engine payload (the ONLY source of truth):\n"
            + json.dumps(engine_payload, default=str)
            + "\n\nQuestion: "
            + (question or "Give a general reading for the current period.")
        )
        contents = []
        for turn in history or []:
            q, a = (turn.get("question") or "").strip(), (turn.get("answer") or "").strip()
            if q:
                contents.append({"role": "user", "parts": [{"text": q}]})
            if a:
                contents.append({"role": "model", "parts": [{"text": a}]})
        contents.append({"role": "user", "parts": [{"text": user_content}]})

        resp = httpx.post(
            f"{self.base_url}/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={
                "systemInstruction": {"parts": [{"text": GROUNDING_CONTRACT}]},
                "contents": contents,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(p.get("text", "") for p in parts)
        return {"text": text, "citations": _extract_citations(text), "provider": self.name}
