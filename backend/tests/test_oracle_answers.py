"""Intent classifier and deterministic answer packet tests."""
from datetime import datetime

import pytest

from app.engine.ephemeris import BirthData
from app.engine.predictions import predict
from app.oracle.answers import build_answer_packet
from app.oracle.intent import INTENTS, classify_intent

BACHCHAN = BirthData(date="1942-10-11", time="16:00:00",
                     lat=25.45, lon=81.85, tz_offset=5.5)
ON = datetime(2026, 7, 3)


@pytest.fixture(scope="module")
def engine_payload():
    return predict(BACHCHAN, ON)


_INTENT_QUESTIONS = {
    "dasha": "What does my current mahadasha indicate?",
    "yogas": "Which yogas are active?",
    "health": "How is my health looking?",
    "wealth": "Will I have financial prosperity?",
    "career": "How is my career and job prospects?",
    "relationships": "When will I get married?",
    "family": "What about my family and parents?",
    "education": "How are my studies and exams?",
    "transit": "Tell me about current transits and gochara",
    "shadbala": "Is Jupiter strong by shadbala?",
    "jaimini": "What does Jaimini chara dasha say?",
    "rectification_help": "Can you rectify my birth time?",
}


@pytest.mark.parametrize("intent,question", list(_INTENT_QUESTIONS.items()))
def test_classify_intent_per_category(intent, question):
    result = classify_intent(question)
    assert result["intent"] == intent
    assert result["matched_keywords"]


def test_general_fallback():
    result = classify_intent("Hello there")
    assert result["intent"] == "general"


@pytest.mark.parametrize("intent", [i for i in INTENTS if i != "general"])
def test_build_answer_packet_has_text_and_citations(intent, engine_payload):
    question = _INTENT_QUESTIONS.get(intent, f"question about {intent}")
    packet = build_answer_packet(intent, engine_payload, question)
    assert packet["text"]
    if intent == "rectification_help":
        assert packet["citations"] == []
    else:
        assert isinstance(packet["citations"], list)


def test_dasha_answer_cites_dasha_path(engine_payload):
    packet = build_answer_packet("dasha", engine_payload, "current dasha?")
    assert any(c.startswith("dasha:") for c in packet["citations"])


def test_career_answer_cites_area(engine_payload):
    packet = build_answer_packet("career", engine_payload, "career?")
    assert any("area: career" in c for c in packet["citations"])


def test_areas_have_favorability_label(engine_payload):
    for area in engine_payload["areas"]:
        assert area.get("favorability_label")


def test_yoga_answer_grounds_known_yoga_with_registry_source():
    payload = {
        "context": {"active_yogas": ["Gaja Kesari Yoga"]},
        "areas": [],
        "dasha_path": [],
    }
    packet = build_answer_packet("yogas", payload, "which yogas are active?")
    assert "Gaja Kesari Yoga" in packet["text"]
    assert "Jupiter in a kendra" in packet["text"]
    assert any("Gaja Kesari Yoga —" in c for c in packet["citations"])


def test_yoga_answer_handles_unknown_yoga_gracefully():
    payload = {
        "context": {"active_yogas": ["Some Unregistered Yoga"]},
        "areas": [],
        "dasha_path": [],
    }
    packet = build_answer_packet("yogas", payload, "which yogas are active?")
    assert "Some Unregistered Yoga" in packet["text"]
    assert any(c == "yoga: Some Unregistered Yoga" for c in packet["citations"])


def test_career_answer_cites_registry_house_source(engine_payload):
    packet = build_answer_packet("career", engine_payload, "career?")
    assert any("classical house significations" in c for c in packet["citations"])
