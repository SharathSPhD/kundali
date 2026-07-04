"""Golden case study. Reads tests/fixtures/case_study.json; skips while the
fixture is still the placeholder (real birth data pending from the user)."""
import json
import os
from datetime import datetime

import pytest

from app.engine.chart import build_chart
from app.engine.dashas import active_path, build_vimshottari
from app.engine.ephemeris import BirthData, EngineConfig

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "case_study.json")


def _load_case():
    if not os.path.exists(FIXTURE):
        pytest.skip("case_study.json fixture not present")
    with open(FIXTURE) as f:
        case = json.load(f)
    if case.get("_placeholder") or "YYYY" in case["birth"]["date"]:
        pytest.skip("case_study.json is still a placeholder (birth data pending)")
    return case


@pytest.fixture(scope="module")
def case():
    return _load_case()


@pytest.fixture(scope="module")
def chart(case):
    birth = BirthData(**{k: v for k, v in case["birth"].items()
                         if k in ("date", "time", "lat", "lon", "tz_offset", "place_name")})
    return build_chart(birth, EngineConfig()), birth


def test_lagna(case, chart):
    natal, _ = chart
    a = case["assertions"]
    assert natal["lagna"]["sign_name"] == a["lagna_sign_name"]
    assert abs(natal["lagna"]["degree_in_sign"] - a["lagna_degree_approx"]) <= a["lagna_degree_tolerance"]
    assert natal["lagna"]["nakshatra"] == a["lagna_nakshatra"]


def test_moon_placement(case, chart):
    natal, _ = chart
    a = case["assertions"]
    assert natal["planets"]["Moon"]["sign_name"] == a["moon_sign_name"]
    assert natal["planets"]["Moon"]["house"] == a["moon_house"]


def test_dasha_periods(case, chart):
    natal, birth = chart
    tree = build_vimshottari(natal["planets"]["Moon"]["longitude"],
                             birth.local_datetime(), EngineConfig(), levels=3)
    for check in case["assertions"]["dasha_checks"]:
        on = datetime.fromisoformat(check["contains"])
        path = active_path(tree, on)
        assert len(path) >= 2, f"no active path on {check['contains']}"
        assert path[0]["lord"] == check["maha"], (
            f"{check['contains']}: expected maha {check['maha']}, got {path[0]['lord']}")
        assert path[1]["lord"] == check["antar"], (
            f"{check['contains']}: expected antar {check['antar']}, got {path[1]['lord']}")
