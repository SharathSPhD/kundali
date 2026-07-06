"""Adversarial and positive claim verification tests."""
from datetime import datetime

import pytest

from app.engine.ephemeris import BirthData
from app.engine.predictions import predict
from app.oracle.claim_parser import parse_claims
from app.oracle.export import export_facts
from app.oracle.verify_claims import verify_claims

BACHCHAN = BirthData(date="1942-10-11", time="16:00:00",
                     lat=25.45, lon=81.85, tz_offset=5.5)
ON = datetime(2026, 7, 3)


@pytest.fixture(scope="module")
def engine_payload():
    return predict(BACHCHAN, ON)


@pytest.fixture(scope="module")
def facts(engine_payload):
    return export_facts(engine_payload)


def test_export_facts_covers_required_keys(facts, engine_payload):
    assert facts.get("lagna.sign_name")
    assert facts.get("moon.sign_name")
    assert facts.get("moon.nakshatra")
    assert "dasha.mahadasha_lord" in facts
    for area in ("career", "wealth", "health", "relationships", "family", "education"):
        assert f"areas.{area}.score" in facts
        assert f"areas.{area}.favorability_label" in facts
    assert isinstance(facts.get("yogas.active"), list)
    assert facts.get("shadbala.Jupiter.total_rupas") is not None


def test_wrong_moon_sign_rejected(facts, engine_payload):
    moon = engine_payload["context"]["moon"]["sign_name"]
    wrong = "Pisces" if moon != "Pisces" else "Aries"
    text = f"The Moon is in {wrong} in this chart."
    claims = parse_claims(text)
    result = verify_claims(claims, facts)
    assert result["verified"] is False
    assert result["rejected_claims"]


def test_correct_moon_sign_passes(facts, engine_payload):
    moon = engine_payload["context"]["moon"]["sign_name"]
    text = f"The Moon is in {moon} in this chart."
    claims = parse_claims(text)
    result = verify_claims(claims, facts)
    assert result["verified"] is True


def test_wrong_dasha_lord_rejected(facts, engine_payload):
    maha = engine_payload["dasha_path"][0]["lord"]
    wrong = "Mars" if maha != "Mars" else "Saturn"
    text = f"The mahadasha of {wrong} is currently active."
    claims = parse_claims(text)
    assert claims
    result = verify_claims(claims, facts)
    assert result["verified"] is False


def test_correct_dasha_lord_passes(facts, engine_payload):
    lord = engine_payload["dasha_path"][0]["lord"]
    text = f"The mahadasha of {lord} is currently active."
    claims = parse_claims(text)
    result = verify_claims(claims, facts)
    assert result["verified"] is True


def test_invented_yoga_rejected(facts, engine_payload):
    active = set(engine_payload["context"]["active_yogas"])
    for candidate in ("Gaja Kesari Yoga", "Kemadruma Yoga", "Kala Sarpa Yoga"):
        if candidate not in active:
            break
    else:
        pytest.skip("all candidate yogas active in fixture")
    text = f"{candidate} is present in this chart."
    claims = parse_claims(text)
    assert claims
    result = verify_claims(claims, facts)
    assert result["verified"] is False


def test_active_yoga_claim_passes_when_present(facts, engine_payload):
    yogas = engine_payload["context"]["active_yogas"]
    if not yogas:
        pytest.skip("no active yogas in fixture chart")
    name = yogas[0]
    text = f"{name} is present in this chart."
    claims = parse_claims(text)
    assert claims
    result = verify_claims(claims, facts)
    assert result["verified"] is True


def test_fabricated_shadbala_rejected(facts):
    text = "Shadbala of Jupiter is 99.99 rupas."
    claims = parse_claims(text)
    assert claims
    result = verify_claims(claims, facts)
    assert result["verified"] is False


def test_correct_shadbala_passes(facts):
    jup = facts["shadbala.Jupiter.total_rupas"]
    text = f"Shadbala of Jupiter is {jup}."
    claims = parse_claims(text)
    assert claims
    result = verify_claims(claims, facts)
    assert result["verified"] is True


def test_no_checkable_claims_returns_none(facts):
    text = (
        "This is a reflective period calling for patience and inner growth. "
        "Trust the process and stay grounded."
    )
    claims = parse_claims(text)
    result = verify_claims(claims, facts)
    assert result["verified"] is None
