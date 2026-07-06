"""Knowledge-layer YAML rule catalog (documentation / claim grounding).

This module loads human-readable rule definitions from YAML files. It does
NOT replace the runtime scoring tables in ``predictions.py`` — those remain
the authoritative computation path. The catalog exists for LLM grounding,
claim verification context, and future formalization work.
"""
from __future__ import annotations

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


def load_rules(name: str) -> dict | list:
    """Load and validate a named rules file from ``rules/<name>.yaml``."""
    path = _RULES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"rules file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    validator = _VALIDATORS.get(name)
    if validator:
        validator(data)
    return data
