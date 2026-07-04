"""Interpretation provider contract.

Providers turn engine JSON into human-readable text. The grounding contract:
use ONLY facts present in the engine payload; every claim must cite a payload
element (dasha period, transit, yoga, score). Providers must never invent
positions, dates, or outcomes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

GROUNDING_CONTRACT = (
    "You are narrating a Vedic astrology reading. You are given a JSON payload "
    "produced by a deterministic calculation engine, and optionally a user "
    "question. STRICT RULES: (1) Use ONLY facts present in the JSON payload — "
    "never invent planetary positions, dates, periods, yogas, or scores. "
    "(2) Every claim you make must cite the payload element it comes from, "
    "e.g. [dasha: Rahu-Mercury 2024-2027], [transit: Sade Sati peak], "
    "[yoga: Gaja Kesari]. (3) If the payload lacks information to answer the "
    "question, say so explicitly. (4) Do not give medical, legal, or financial "
    "directives; frame indications as tendencies. Respond in clear English "
    "paragraphs."
)


class InterpretationProvider(ABC):
    """ABC: interpret(engine_payload, question) -> {text, citations[]}."""

    name: str = "base"

    @abstractmethod
    def interpret(self, engine_payload: dict[str, Any],
                  question: Optional[str] = None) -> dict:
        """Return {"text": str, "citations": [str], "provider": str}."""
        raise NotImplementedError
