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
    "question. The payload includes: dasha-lord natal-role facts, transit "
    "facts, yogas, varga (divisional-chart) corroboration, full Shadbala "
    "(payload.shadbala — six-fold strength in rupas per planet, with the "
    "required-rupas threshold and ratio) and Jaimini data (payload.jaimini — "
    "7 chara karakas including Atmakaraka/Darakaraka, and K.N. Rao's Chara "
    "Dasha with the currently active sign-period). STRICT RULES: (1) Use "
    "ONLY facts present in the JSON payload — never invent planetary "
    "positions, dates, periods, yogas, scores, or strength values. "
    "(2) Every claim you make must cite the payload element it comes from, "
    "e.g. [dasha: Rahu-Mercury 2024-2027], [transit: Sade Sati peak], "
    "[yoga: Gaja Kesari], [shadbala: Jupiter 6.2/5.0 rupas], [jaimini: "
    "Darakaraka Venus, Chara Dasha Libra]. (3) If the payload lacks "
    "information to answer the question, say so explicitly — do not "
    "estimate or approximate a missing Shadbala/Jaimini figure. (4) Do not "
    "give medical, legal, or financial directives; frame indications as "
    "tendencies. Respond in clear English paragraphs."
)


class InterpretationProvider(ABC):
    """ABC: interpret(engine_payload, question, history) -> {text, citations[]}."""

    name: str = "base"

    @abstractmethod
    def interpret(self, engine_payload: dict[str, Any],
                  question: Optional[str] = None,
                  history: Optional[list[dict]] = None) -> dict:
        """Return {"text": str, "citations": [str], "provider": str}.

        `history` is an optional list of prior turns as
        `{"question": str, "answer": str}` pairs (oldest first) — providers
        that support multi-turn context should fold these in ahead of the
        current question; providers that don't may safely ignore it.
        """
        raise NotImplementedError


def history_to_messages(history: Optional[list[dict]]) -> list[dict]:
    """Normalize `{"question", "answer"}` turn pairs into a chat-style
    alternating user/assistant message list, shared by every provider that
    talks to a `messages`-shaped chat API (Anthropic, OpenAI, Ollama)."""
    messages: list[dict] = []
    for turn in history or []:
        q = (turn.get("question") or "").strip()
        a = (turn.get("answer") or "").strip()
        if q:
            messages.append({"role": "user", "content": q})
        if a:
            messages.append({"role": "assistant", "content": a})
    return messages
