"""Personalized muhurta scan: tara bala math, activity tables, ranking."""
from __future__ import annotations

import datetime

import pytest

from app.engine.chart import BirthData
from app.engine.muhurta import _tara, activities, resolve_activity, scan_muhurta


@pytest.fixture(scope="module")
def birth():
    return BirthData(date="1990-05-15", time="10:30", tz_offset=5.5, lat=12.97, lon=77.59)


def test_activity_tables_are_complete():
    acts = activities()
    assert set(acts) >= {"marriage", "new_venture", "travel", "education", "housewarming", "medical"}
    for name, spec in acts.items():
        assert spec.get("nakshatras"), name
        assert spec.get("varas"), name
        assert spec.get("avoid_tithis"), name


def test_activity_aliases_resolve():
    assert resolve_activity("wedding") == "marriage"
    assert resolve_activity("griha pravesh") == "housewarming"
    assert resolve_activity("TRIP") == "travel"
    assert resolve_activity("unknown thing") is None


def test_tara_cycle_from_janma():
    # Same nakshatra = Janma (1); next = Sampat (2); 7th = Naidhana.
    assert _tara(0, 0)["name"] == "Janma"
    assert _tara(0, 1)["name"] == "Sampat"
    assert _tara(0, 6)["name"] == "Naidhana"
    assert _tara(0, 6)["favorable"] is False
    # Cycle repeats mod 9 across all 27.
    assert _tara(0, 9)["name"] == "Janma"
    assert _tara(20, 20)["name"] == "Janma"


def test_scan_returns_ranked_days_with_reasons(birth):
    r = scan_muhurta(birth, "travel", datetime.date(2026, 7, 9), days=30)
    assert r["activity"] == "travel"
    assert len(r["all"]) == 30
    assert len(r["best"]) == 7
    scores = [d["score"] for d in r["best"]]
    assert scores == sorted(scores, reverse=True)
    top = r["best"][0]
    factors = {reason["factor"] for reason in top["reasons"]}
    assert factors == {"tara_bala", "chandra_bala", "tithi", "vara", "nakshatra"}
    for reason in top["reasons"]:
        assert reason["source"]


def test_scan_is_personalized_to_janma_nakshatra(birth):
    other = BirthData(date="1985-01-01", time="06:00", tz_offset=5.5, lat=28.6, lon=77.2)
    r1 = scan_muhurta(birth, "marriage", datetime.date(2026, 7, 9), days=20)
    r2 = scan_muhurta(other, "marriage", datetime.date(2026, 7, 9), days=20)
    assert r1["janma_nakshatra"] != r2["janma_nakshatra"]
    # Same calendar days, different personal scores somewhere.
    diffs = [
        (a["date"], a["score"], b["score"])
        for a, b in zip(r1["all"], r2["all"])
        if a["score"] != b["score"]
    ]
    assert diffs, "tara/chandra bala must differentiate two different births"


def test_unknown_activity_raises(birth):
    with pytest.raises(ValueError, match="unknown activity"):
        scan_muhurta(birth, "sorcery", datetime.date(2026, 7, 9), days=5)


def test_days_clamped(birth):
    r = scan_muhurta(birth, "travel", datetime.date(2026, 7, 9), days=500)
    assert r["days"] == 120
