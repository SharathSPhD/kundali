"""Knowledge-layer YAML rule catalog (documentation / claim grounding).

This module loads human-readable rule definitions from YAML files. It does
NOT replace the runtime scoring tables in ``predictions.py`` — those remain
the authoritative computation path. The catalog exists for LLM grounding,
claim verification context, and future formalization work.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_RULES_DIR = Path(__file__).resolve().parent / "rules"


def _validate_area_house_polarity(data: dict) -> None:
    if "areas" not in data:
        raise ValueError("area_house_polarity.yaml: missing 'areas' key")
    seen: set[str] = set()
    for area, spec in data["areas"].items():
        if area in seen:
            raise ValueError(f"duplicate area: {area}")
        seen.add(area)
        if "houses" not in spec:
            raise ValueError(f"area {area}: missing 'houses'")
        if "source" not in spec:
            raise ValueError(f"area {area}: missing 'source'")


def _validate_yogas(data: dict) -> None:
    if "yogas" not in data:
        raise ValueError("yogas.yaml: missing 'yogas' key")
    seen: set[str] = set()
    for entry in data["yogas"]:
        name = entry.get("name")
        if not name:
            raise ValueError("yoga entry missing 'name'")
        if name in seen:
            raise ValueError(f"duplicate yoga name: {name}")
        seen.add(name)
        for key in ("sanskrit_category", "rule_description", "source"):
            if key not in entry:
                raise ValueError(f"yoga {name}: missing '{key}'")


_VALIDATORS = {
    "area_house_polarity": _validate_area_house_polarity,
    "yogas": _validate_yogas,
}


@lru_cache(maxsize=None)
def load_rules(name: str) -> dict | list:
    """Load and validate a named rules file from ``rules/<name>.yaml``.

    Cached: these files are read-only at runtime and re-parsed on every call
    otherwise (this is invoked per-request from the answer-packet/claim
    grounding path below).
    """
    path = _RULES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"rules file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    validator = _VALIDATORS.get(name)
    if validator:
        validator(data)
    return data


@lru_cache(maxsize=None)
def _yoga_catalog() -> dict[str, dict[str, Any]]:
    try:
        data = load_rules("yogas")
    except FileNotFoundError:
        return {}
    return {entry["name"]: entry for entry in data.get("yogas", [])}


def yoga_info(name: str) -> dict[str, Any] | None:
    """Look up a yoga's rule description + textual provenance by name.

    Matches loosely (case-insensitive, ignoring a trailing "Yoga"/"Dosha")
    since engine-reported yoga names don't always match the catalog's
    canonical title casing exactly.
    """
    catalog = _yoga_catalog()
    if name in catalog:
        return catalog[name]

    def _norm(s: str) -> str:
        # Engine emits parameterized instances like "Neecha Bhanga (Venus)"
        # or "Raja Yoga (Mars-Moon)"; the catalog describes the family.
        s = re.sub(r"\s*\([^)]*\)", "", s)
        s = re.sub(r"\s+(yoga|dosha)$", "", s.strip(), flags=re.I)
        return s.strip().lower()

    key = _norm(name)
    for cname, entry in catalog.items():
        if _norm(cname) == key:
            return entry
    return None


def area_info(area: str) -> dict[str, Any] | None:
    """Look up an area's governing houses + textual provenance by name."""
    try:
        data = load_rules("area_house_polarity")
    except FileNotFoundError:
        return None
    return (data.get("areas") or {}).get(area)
