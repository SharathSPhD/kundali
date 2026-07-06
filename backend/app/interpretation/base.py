"""Interpretation provider contract.

Providers turn engine JSON into human-readable text. The grounding contract:
use ONLY facts present in the engine payload; every claim must cite a payload
element (dasha period, transit, yoga, score). Providers must never invent
positions, dates, or outcomes.
"""
from __future__ import annotations

import ipaddress
import socket
from abc import ABC, abstractmethod
from typing import Any, Optional
from urllib.parse import urlparse

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


class UnsafeBaseUrlError(ValueError):
    """Raised when a user-supplied BYOK `base_url` resolves to a
    non-public address (SSRF guard)."""


def assert_safe_user_base_url(url: str) -> None:
    """Reject a user-controlled `base_url` (BYOK credential) unless it is a
    plain http(s) URL that resolves to a public, non-reserved IP address.

    This backend runs server-side and makes the outbound request itself, so
    an attacker-controlled `base_url` here is a classic SSRF vector: cloud
    metadata endpoints (169.254.169.254), localhost/loopback, and other
    private/link-local ranges must never be reachable via a stored BYOK
    credential. This check only applies to user-supplied URLs — operator-
    controlled defaults (env vars like OLLAMA_URL, the GB10 gateway URL)
    never pass through it.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeBaseUrlError(f"base_url must be http(s), got: {parsed.scheme or '(none)'}")
    host = parsed.hostname
    if not host:
        raise UnsafeBaseUrlError("base_url has no hostname")
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise UnsafeBaseUrlError(f"base_url host could not be resolved: {host}") from exc
    for addr in addrs:
        ip = ipaddress.ip_address(addr)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise UnsafeBaseUrlError(
                f"base_url host '{host}' resolves to a non-public address ({addr}); "
                "BYOK endpoints must be reachable at a public address."
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
