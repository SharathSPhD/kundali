"""Declarative event-type rules for birth-time rectification.

Each canonical event type maps house significations and natural karakas used
to decide which grahas are "relevant" when scoring dasha lords at event dates.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventRule:
    houses: frozenset[int]
    karakas: frozenset[str]
    source: str
    generic: bool = False


CANONICAL_RULES: dict[str, EventRule] = {
    "marriage": EventRule(
        frozenset({7}),
        frozenset({"Venus"}),
        "classical house significations (7th marriage)",
    ),
    "childbirth": EventRule(
        frozenset({5}),
        frozenset({"Jupiter"}),
        "classical house significations (5th progeny)",
    ),
    "career": EventRule(
        frozenset({10}),
        frozenset({"Sun", "Saturn", "Mercury"}),
        "classical house significations (10th profession)",
    ),
    "relocation": EventRule(
        frozenset({4, 12}),
        frozenset(),
        "classical house significations (4th home, 12th displacement)",
    ),
    "foreign_travel": EventRule(
        frozenset({9, 12}),
        frozenset(),
        "classical house significations (9th foreign, 12th abroad)",
    ),
    "education": EventRule(
        frozenset({4, 5, 9}),
        frozenset({"Mercury", "Jupiter"}),
        "classical house significations (4th learning, 5th intellect, 9th higher)",
    ),
    "parent_death": EventRule(
        frozenset({4, 9}),
        frozenset({"Sun", "Moon"}),
        "classical house significations (4th mother, 9th father)",
    ),
    "father_death": EventRule(
        frozenset({9}),
        frozenset({"Sun"}),
        "classical house significations (9th father)",
    ),
    "mother_death": EventRule(
        frozenset({4}),
        frozenset({"Moon"}),
        "classical house significations (4th mother)",
    ),
    "accident": EventRule(
        frozenset({6, 8}),
        frozenset({"Mars", "Saturn"}),
        "classical house significations (6th injury, 8th trauma)",
    ),
    "health": EventRule(
        frozenset({6, 8}),
        frozenset({"Saturn"}),
        "classical house significations (6th disease, 8th chronic)",
    ),
    "other": EventRule(
        frozenset(),
        frozenset(),
        "generic fallback — no specific house/karaka assignment",
        generic=True,
    ),
}

# Alternate spellings / frontend keys -> canonical type
ALIASES: dict[str, str] = {
    "child": "childbirth",
    "child_birth": "childbirth",
    "job": "career",
    "career_start": "career",
    "promotion": "career",
    "health_event": "health",
    "marriage_date": "marriage",
    "travel": "foreign_travel",
    "death": "parent_death",
}

CANONICAL_TYPES = frozenset(CANONICAL_RULES.keys())

# Per-event maximum achievable score (non-generic).
# Dasha: antar 1.0 + maha 0.5 + pratyantar 0.3 = 1.8
# Transit corroboration (Saturn/Jupiter): 0.2 each = 0.4
# Ruling planets (vaara + Moon nakshatra lord): 0.15 each = 0.3
FULL_EVENT_MAX = 2.5
GENERIC_EVENT_MAX = 0.5  # down-weighted denominator for unrecognized/generic events


def resolve_event_type(raw: str) -> tuple[str, list[str]]:
    """Map a raw event type string to a canonical type and optional warnings."""
    key = raw.strip().lower() if raw else ""
    if key in CANONICAL_TYPES:
        return key, []
    if key in ALIASES:
        return ALIASES[key], []
    if not key:
        return "other", [f"Unknown event type '{raw}', scored as generic/low-signal 'other'"]
    return "other", [f"Unknown event type '{raw}', scored as generic/low-signal 'other'"]


def get_rule(canonical_type: str) -> EventRule:
    return CANONICAL_RULES[canonical_type]


def max_score_for_event(canonical_type: str) -> float:
    rule = get_rule(canonical_type)
    return GENERIC_EVENT_MAX if rule.generic else FULL_EVENT_MAX
