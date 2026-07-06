"""Claim parser: dasha/yoga/shadbala regex extraction, incl. yoga-name drift."""
import inspect
import re

from app.engine import yogas as yogas_module
from app.oracle.claim_parser import _yoga_names_from_engine, parse_claims


def _fixed_name_yogas_in_engine() -> set[str]:
    """Every plain-string-literal name passed to `_yoga(...)` in
    engine/yogas.py — i.e. every yoga whose name has no per-chart dynamic
    suffix, so a claim naming it exactly should always be parseable."""
    src = inspect.getsource(yogas_module)
    return set(re.findall(r'_yoga\(\s*"([^"{}]+)"', src))


def test_claim_parser_yoga_list_covers_every_fixed_name_engine_yoga():
    known = set(_yoga_names_from_engine())
    fixed_engine_names = _fixed_name_yogas_in_engine()
    missing = fixed_engine_names - known
    assert not missing, (
        f"claim_parser._yoga_names_from_engine() is missing fixed-name "
        f"yogas that engine/yogas.py can emit: {sorted(missing)}"
    )


def test_previously_missing_yogas_now_parse():
    for name in ("Shakata Yoga", "Lakshmi Yoga", "Sunapha Yoga", "Anapha Yoga",
                 "Durudhara Yoga"):
        claims = parse_claims(f"{name} is present in this chart.")
        assert any(c["type"] == "yoga_present" and c["yoga_name"] == name for c in claims), name


def test_dasha_lord_matches_period_of_phrasing():
    claims = parse_claims("The period of Saturn is currently active.")
    assert claims == [{"type": "dasha_lord", "raw_text": "period of Saturn", "lord": "Saturn"}]


def test_shadbala_claim_parses_value():
    claims = parse_claims("Shadbala of Jupiter is 6.24.")
    assert claims[0] == {
        "type": "shadbala_claim", "raw_text": "Shadbala of Jupiter is 6.24",
        "planet": "Jupiter", "value": 6.24,
    }
