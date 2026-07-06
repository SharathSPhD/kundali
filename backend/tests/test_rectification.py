"""Tests for event-based birth-time rectification."""
from datetime import datetime

import pytest

from app.engine.dashas import active_path, build_vimshottari
from app.engine.ephemeris import BirthData
from app.engine.rectification import rectify
from app.engine.rectification_rules import (
    CANONICAL_RULES,
    resolve_event_type,
)

# Delhi — stable lat/lon for ephemeris-backed tests
BIRTH = BirthData(
    date="1990-05-15",
    time="06:30:00",
    lat=28.6139,
    lon=77.2090,
    tz_offset=5.5,
    place_name="Delhi",
)

FRONTEND_EVENT_TYPES = {
    "marriage": "marriage",
    "childbirth": "childbirth",
    "career": "career",
    "relocation": "relocation",
    "parent_death": "parent_death",
    "health": "health",
    "other": "other",
}


def _rectify(events, window_minutes=30, step_minutes=2, top_n=20, birth=BIRTH):
    return rectify(birth, window_minutes, events, step_minutes=step_minutes, top_n=top_n)


def test_resolve_frontend_event_types_without_warnings():
    for raw, expected in FRONTEND_EVENT_TYPES.items():
        canonical, warnings = resolve_event_type(raw)
        assert canonical == expected
        assert warnings == []


def test_unrecognized_event_falls_back_to_other_with_warning():
    canonical, warnings = resolve_event_type("spiritual_awakening")
    assert canonical == "other"
    assert len(warnings) == 1
    assert "spiritual_awakening" in warnings[0]
    assert "other" in warnings[0]


def test_canonical_other_has_no_warning():
    canonical, warnings = resolve_event_type("other")
    assert canonical == "other"
    assert warnings == []


def test_every_canonical_type_has_non_empty_relevant_lords(config):
    """Each non-generic canonical type must yield house/karaka lords for scoring."""
    from app.engine.chart import build_chart
    from app.engine.rectification import _relevant_lords

    chart = build_chart(BIRTH, config)
    for name, rule in CANONICAL_RULES.items():
        if rule.generic:
            continue
        lords, reasons = _relevant_lords(chart, name)
        assert lords, f"{name} produced empty relevant-lord set"
        assert reasons


def test_every_canonical_type_scores_in_rectify(config):
    """Smoke: each non-generic type produces non-zero max_score for one event."""
    for name, rule in CANONICAL_RULES.items():
        if rule.generic:
            continue
        result = _rectify([{"type": name, "date": "2015-06-15"}], window_minutes=4)
        detail = result["candidates"][0]["events"][0]
        assert detail["max_score"] > 0
        assert detail["canonical_type"] == name
        assert len(detail["relevant_lords"]) > 0


def test_unrecognized_event_in_rectify_response(config):
    result = _rectify([
        {"type": "marriage", "date": "2015-02-10"},
        {"type": "spiritual_awakening", "date": "2018-01-01"},
    ])
    assert result["ignored_event_count"] == 1
    assert any("spiritual_awakening" in w for w in result["warnings"])
    types = [e["canonical_type"] for e in result["candidates"][0]["events"]]
    assert types == ["marriage", "other"]
    other_detail = result["candidates"][0]["events"][1]
    assert other_detail["generic"] is True


def test_pratyantardasha_contributes_to_score(config):
    from app.engine.chart import build_chart
    from app.engine.rectification import _relevant_lords

    birth = BIRTH
    base_dt = birth.local_datetime()
    chart = build_chart(birth, config)
    tree = build_vimshottari(
        chart["planets"]["Moon"]["longitude"], base_dt, config, levels=3,
    )

    found = None
    for year in range(1995, 2025):
        for month in (1, 4, 7, 10):
            ev_dt = datetime(year, month, 15)
            path = active_path(tree, ev_dt)
            if len(path) < 3:
                continue
            pratyantar_lord = path[2]["lord"]
            for ev_type in ("marriage", "career", "health", "childbirth", "education"):
                relevant, _ = _relevant_lords(chart, ev_type)
                if pratyantar_lord in relevant:
                    found = (ev_type, ev_dt.date().isoformat(), pratyantar_lord)
                    break
            if found:
                break
        if found:
            break

    assert found, "could not find pratyantar lord in any event relevant set"
    ev_type, ev_date, pratyantar_lord = found
    result = _rectify([{"type": ev_type, "date": ev_date}], window_minutes=0, step_minutes=2)
    detail = result["candidates"][0]["events"][0]
    assert detail["active_pratyantardasha"] == pratyantar_lord
    assert any("pratyantardasha" in m for m in detail["matched"])
    assert detail["score"] >= 0.3


def test_diagnostics_fields_present(config):
    result = _rectify([
        {"type": "marriage", "date": "2015-02-10"},
        {"type": "unknown_xyz", "date": "2016-03-01"},
    ])
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["tie_count"] >= 1
    assert result["ignored_event_count"] == 1
    assert "sensitivity_to_step" in result
    assert "likely_changes_top" in result["sensitivity_to_step"]
    assert "note" in result["sensitivity_to_step"]


def test_varga_sensitivity_on_candidates(config):
    result = _rectify(
        [{"type": "marriage", "date": "2015-02-10"}],
        window_minutes=60,
        step_minutes=1,
    )
    for cand in result["candidates"]:
        vs = cand["varga_sensitivity"]
        assert isinstance(vs, dict)
        assert isinstance(vs["near_d9_boundary"], bool)
        assert isinstance(vs["near_d10_boundary"], bool)
        assert vs["proximity_minutes"] == 3


def test_backward_compatible_top_level_keys(config):
    result = _rectify([{"type": "marriage", "date": "2015-02-10"}])
    for key in ("input_time", "window_minutes", "step_minutes", "n_candidates", "candidates"):
        assert key in result
    assert result["input_time"] == BIRTH.time
    assert result["n_candidates"] >= 1
    assert result["candidates"][0]["score"] >= result["candidates"][-1]["score"]


def test_max_score_reflects_full_scoring(config):
    result = _rectify([{"type": "marriage", "date": "2015-02-10"}])
    assert result["candidates"][0]["max_score"] == 2.5


def test_generic_other_max_score_lower(config):
    result = _rectify([{"type": "other", "date": "2015-02-10"}])
    assert result["candidates"][0]["max_score"] == 0.5
