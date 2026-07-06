"""Rule-based intent classifier for deterministic chart Q&A (no LLM)."""
from __future__ import annotations

import re
from typing import TypedDict

INTENTS = (
    "dasha",
    "yogas",
    "health",
    "wealth",
    "career",
    "relationships",
    "family",
    "education",
    "transit",
    "shadbala",
    "jaimini",
    "rectification_help",
    "general",
)

# (intent, compiled pattern) — first match wins (order matters).
# More specific intents (jaimini, rectification) precede broad dasha/transit.
_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("rectification_help", re.compile(
        r"\b(rectif|birth\s*time|correct\s*time|time\s*correction)\b", re.I)),
    ("jaimini", re.compile(
        r"\b(jaimini|chara\s*dasha|chara\s*daśā|karaka|kāraka|atmakaraka)\b", re.I)),
    ("dasha", re.compile(
        r"\b(mahadasha|mahādaśā|antardasha|antardaśā|pratyantar|"
        r"planetary\s*period|current\s*period)\b|(?<!chara\s)\bdasha\b|(?<!chara\s)\bdaśā\b",
        re.I)),
    ("yogas", re.compile(r"\b(yoga|yogas|combination)\b", re.I)),
    ("transit", re.compile(r"\b(transit|gochara|gochar|sade\s*sati|sadesati)\b", re.I)),
    ("shadbala", re.compile(r"\b(shadbala|sha[dḍ]bala|planetary\s*strength|"
                            r"strength\s*of\s*(sun|moon|mars|mercury|jupiter|venus|saturn))\b", re.I)),
    ("career", re.compile(
        r"\b(career|job|profession|promotion|work|business|10th\s*house)\b", re.I)),
    ("wealth", re.compile(
        r"\b(wealth|money|finance|financial|income|prosperity|2nd\s*house|11th\s*house)\b", re.I)),
    ("health", re.compile(r"\b(health|illness|disease|medical|6th\s*house)\b", re.I)),
    ("relationships", re.compile(
        r"\b(marry|married|marriage|spouse|relationship|partner|love|7th\s*house)\b", re.I)),
    ("family", re.compile(r"\b(family|parents|mother|father|home|4th\s*house)\b", re.I)),
    ("education", re.compile(
        r"\b(study|studies|education|exam|exams|school|college|learning|5th\s*house|9th\s*house)\b", re.I)),
]


class IntentResult(TypedDict):
    intent: str
    matched_keywords: list[str]


def classify_intent(question: str) -> IntentResult:
    """Classify a free-text question into a known intent bucket."""
    q = (question or "").strip()
    if not q:
        return {"intent": "general", "matched_keywords": []}

    for intent, pattern in _RULES:
        m = pattern.search(q)
        if m:
            return {"intent": intent, "matched_keywords": [m.group(0)]}

    return {"intent": "general", "matched_keywords": []}
