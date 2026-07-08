"""KG-backed deterministic Q&A: every answer must be grounded (derivation
steps citing sources, facts drawn from the payload — nothing invented)."""
from __future__ import annotations

import datetime

import pytest

from app.engine.chart import BirthData
from app.engine.predictions import predict
from app.oracle.kg_answers import answer_question


@pytest.fixture(scope="module")
def payload():
    birth = BirthData(date="1990-05-15", time="10:30", tz_offset=5.5, lat=12.97, lon=77.59)
    return predict(birth, datetime.datetime(2026, 7, 8, 12, 0))


def test_area_question_produces_derivation_chain(payload):
    a = answer_question("How is my career looking?", payload)
    assert a["answer_kind"] == "area"
    assert len(a["derivation"]) >= 3
    for step in a["derivation"]:
        assert step["claim"] and step["rule"]
    # The 10th lord from the payload must actually appear in the text.
    lord = payload["chart"]["house_lords"][10]["lord"]
    assert lord in a["text"]


def test_timing_question_includes_windows_or_periods(payload):
    a = answer_question("When will my career improve?", payload)
    assert a["answer_kind"] == "area"
    assert "Timing" in a["text"] or "window" in a["text"].lower()


def test_graha_entity_answer_grounds_in_chart(payload):
    a = answer_question("What does Saturn mean in my chart?", payload)
    assert a["answer_kind"] == "entity"
    sat = payload["chart"]["planets"]["Saturn"]
    assert sat["sign_name"] in a["text"]
    assert sat["nakshatra"] in a["text"]
    assert "karaka" in a["text"].lower()


def test_bhava_entity_answer(payload):
    a = answer_question("Tell me about my 7th house", payload)
    assert a["answer_kind"] == "entity"
    assert "marriage" in a["text"].lower()


def test_remedy_answer_targets_weakest_planet_and_disclaims(payload):
    a = answer_question("What gemstone should I wear?", payload)
    assert a["answer_kind"] == "remedy"
    assert "Gemstone" in a["text"]
    assert "not medical" in a["text"]
    # Rationale must be stated (weakest shadbala ratio).
    assert "lowest shadbala" in a["text"]


def test_remedy_answer_respects_explicit_graha(payload):
    a = answer_question("Which mantra pacifies Saturn?", payload)
    assert "Saturn" in a["text"] and ("shanaishcharaya" in a["text"] or "Shani" in a["text"])


def test_strength_question_ranks_planets(payload):
    a = answer_question("Which is my strongest planet?", payload)
    assert a["answer_kind"] == "strength"
    assert "strongest" in a["text"]
    assert "shadbala" in " ".join(c.lower() for c in a["citations"]) or "shadbala" in a["text"].lower()


def test_relationship_question_uses_seventh_house(payload):
    a = answer_question("Will my marriage be happy?", payload)
    assert a["answer_kind"] == "area"
    assert "7th" in a["text"]
    assert "Venus" in a["text"]  # kalatra karaka always assessed


def test_legacy_intents_still_answered(payload):
    a = answer_question("What is my current dasha?", payload)
    assert a["text"]
    assert a["citations"]


def test_general_question_falls_back_gracefully(payload):
    a = answer_question("How are things overall?", payload)
    assert a["text"]


def test_no_hallucinated_signs(payload):
    """Every sign name mentioned for the 10th lord must match the payload."""
    a = answer_question("How is my career looking?", payload)
    lord_entry = payload["chart"]["house_lords"][10]
    assert lord_entry["placed_sign_name"] in a["text"]
