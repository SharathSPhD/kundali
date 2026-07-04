"""Anthropic provider: same grounding contract via the anthropic SDK.
The SDK is imported lazily so the dependency stays optional."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from .base import GROUNDING_CONTRACT, InterpretationProvider
from .ollama_provider import _extract_citations


class AnthropicProvider(InterpretationProvider):
    name = "anthropic"

    def __init__(self, model: Optional[str] = None, max_tokens: int = 1500):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        self.max_tokens = max_tokens

    def interpret(self, engine_payload: dict[str, Any],
                  question: Optional[str] = None) -> dict:
        import anthropic  # lazy import

        client = anthropic.Anthropic()
        user_content = (
            "Engine payload (the ONLY source of truth):\n"
            + json.dumps(engine_payload, default=str)
            + "\n\nQuestion: "
            + (question or "Give a general reading for the current period.")
        )
        msg = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=GROUNDING_CONTRACT,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return {"text": text, "citations": _extract_citations(text), "provider": self.name}
