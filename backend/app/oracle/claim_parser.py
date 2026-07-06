"""Best-effort regex/keyword claim extraction from LLM free text.

This is intentionally heuristic — it will not catch every phrasing. Claims
that cannot be parsed are simply not checked (see verify_claims).
"""
from __future__ import annotations

import re

from ..engine import constants as K


def _yoga_names_from_engine() -> list[str]:
    """Yoga name strings matching evaluate_yogas output."""
    return [
        "Gaja Kesari Yoga",
        "Budhaditya Yoga",
        "Chandra-Mangala Yoga",
        "Kemadruma Yoga",
        "Kala Sarpa Yoga",
        "Neecha Bhanga (Sun)",
        "Neecha Bhanga (Moon)",
        "Neecha Bhanga (Mars)",
        "Neecha Bhanga (Mercury)",
        "Neecha Bhanga (Jupiter)",
        "Neecha Bhanga (Venus)",
        "Neecha Bhanga (Saturn)",
        "Raja Yoga",
        "Dhana Yoga",
        "Viparita Raja Yoga",
        "Adhi Yoga",
        "Amala Yoga",
        "Parivartana Yoga",
        "Shubha Kartari Yoga",
        "Papa Kartari Yoga",
        "Vesi Yoga",
        "Vosi Yoga",
        "Ubhayachari Yoga",
        "Hamsa Yoga",
        "Malavya Yoga",
        "Ruchaka Yoga",
        "Bhadra Yoga",
        "Shasha Yoga",
    ]


_SIGN_ALT = "|".join(re.escape(s) for s in K.SIGN_NAMES)
_PLANET_ALT = "|".join(re.escape(p) for p in K.PLANETS)

_PLANET_SIGN = re.compile(
    rf"\b({_PLANET_ALT})\s+(?:is\s+)?(?:in|placed\s+in|located\s+in)\s+({_SIGN_ALT})\b",
    re.I,
)
_DASHA_LORD = re.compile(
    rf"\b(?:mahadasha|mahādaśā|antardasha|antardaśā|dasha|daśā|period)\s+of\s+({_PLANET_ALT})\b",
    re.I,
)
_SCORE_CLAIM = re.compile(
    r"\b(career|wealth|health|relationships|family|education)\s+score\s+(?:is\s+)?([-+]?\d*\.?\d+)\b",
    re.I,
)
_SHADBALA_CLAIM = re.compile(
    rf"\b(?:shadbala|strength)\s+of\s+({_PLANET_ALT})\s+(?:is\s+)?(\d+\.?\d*)\b",
    re.I,
)


def parse_claims(text: str) -> list[dict]:
    claims: list[dict] = []
    if not text or not text.strip():
        return claims

    for m in _PLANET_SIGN.finditer(text):
        claims.append({
            "type": "planet_in_sign",
            "raw_text": m.group(0),
            "planet": _normalize_planet(m.group(1)),
            "sign": _normalize_sign(m.group(2)),
        })

    for m in _DASHA_LORD.finditer(text):
        claims.append({
            "type": "dasha_lord",
            "raw_text": m.group(0),
            "lord": _normalize_planet(m.group(1)),
        })

    for name in _yoga_names_from_engine():
        pat = re.compile(
            rf"\b{re.escape(name)}\b(?:\s+yoga)?\s+(?:is\s+)?(?:present|active|formed|exists)\b",
            re.I,
        )
        m = pat.search(text)
        if m:
            claims.append({
                "type": "yoga_present",
                "raw_text": m.group(0),
                "yoga_name": name,
            })

    for m in _SCORE_CLAIM.finditer(text):
        claims.append({
            "type": "score_claim",
            "raw_text": m.group(0),
            "area": m.group(1).lower(),
            "value": float(m.group(2)),
        })

    for m in _SHADBALA_CLAIM.finditer(text):
        claims.append({
            "type": "shadbala_claim",
            "raw_text": m.group(0),
            "planet": _normalize_planet(m.group(1)),
            "value": float(m.group(2)),
        })

    return claims


def _normalize_planet(name: str) -> str:
    return name.strip().title().replace("  ", " ")


def _normalize_sign(name: str) -> str:
    for s in K.SIGN_NAMES:
        if s.lower() == name.strip().lower():
            return s
    return name.strip().title()
