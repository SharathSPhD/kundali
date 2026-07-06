"""Nyaya syllogism well-formedness — mirrors `Kundali/Nyaya.lean`.

Lean definition (keep in sync):
  wellFormed s := hasAllMembers s && s.vyapti_stated && s.drstanta_present && s.hetvabhasa.isNone

This checks argument FORM only — never astrological or worldly truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Syllogism:
    pratijna: str
    hetu: str
    udaharana: str
    upanaya: str
    nigamana: str
    vyapti_stated: bool = False
    drstanta_present: bool = False
    hetvabhasa: Optional[str] = None
    fallacies: list[str] = field(default_factory=list)


def _nonempty(s: str) -> bool:
    return bool(s.strip())


def has_all_members(s: Syllogism) -> bool:
    return all(_nonempty(x) for x in (s.pratijna, s.hetu, s.upanaya, s.nigamana))


def well_formed(s: Syllogism) -> bool:
    """Must match `Kundali.Nyaya.wellFormed` in formal/lean-kundali/Kundali/Nyaya.lean."""
    return (
        has_all_members(s)
        and s.vyapti_stated
        and s.drstanta_present
        and s.hetvabhasa is None
    )
