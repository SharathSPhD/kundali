"""Golden famous charts (fixtures/golden_charts.json).

Each case carries its own ayanamsa and tolerance; degree-level checks use
the ayanamsa the published chart was cast with (Raman for B.V. Raman's
'Notable Horoscopes' charts), sign-level checks are also run under Lahiri.
Timezone decisions (LMT vs Madras Time) are documented in the fixture.
"""
import json
from pathlib import Path

import pytest

from app.engine.ephemeris import (
    BirthData, EngineConfig, ascendant, julian_day_from_utc, planet_longitudes,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_charts.json").read_text()
)

PARAMS = [
    (case, check)
    for case in FIXTURE["cases"]
    for check in case["checks"]
]
IDS = [f"{c['name']}-{chk['ayanamsa']}" for c, chk in PARAMS]


@pytest.mark.parametrize("case,check", PARAMS, ids=IDS)
def test_golden_chart(case, check):
    birth = BirthData(**case["birth"])
    cfg = EngineConfig(ayanamsa=check["ayanamsa"])
    jd = julian_day_from_utc(birth.utc_datetime())
    positions = planet_longitudes(jd, cfg)
    lagna = ascendant(jd, birth.lat, birth.lon, cfg)

    exp_lagna = check["lagna"]
    assert lagna["sign_name"] == exp_lagna["sign"], (
        f"{case['name']} lagna sign: got {lagna['sign_name']} "
        f"{lagna['degree_in_sign']:.2f}, expected {exp_lagna['sign']}")
    if "deg" in exp_lagna:
        assert abs(lagna["degree_in_sign"] - exp_lagna["deg"]) <= exp_lagna["tol"], (
            f"{case['name']} lagna deg: got {lagna['degree_in_sign']:.2f}, "
            f"expected {exp_lagna['deg']} +/- {exp_lagna['tol']}")

    for graha, exp in check.get("planets", {}).items():
        got = positions[graha]
        assert got["sign_name"] == exp["sign"], (
            f"{case['name']} {graha} sign: got {got['sign_name']} "
            f"{got['degree_in_sign']:.2f}, expected {exp['sign']}")
        if "deg" in exp:
            assert abs(got["degree_in_sign"] - exp["deg"]) <= exp["tol"], (
                f"{case['name']} {graha} deg: got {got['degree_in_sign']:.2f}, "
                f"expected {exp['deg']} +/- {exp['tol']}")
        if "nakshatra" in exp:
            assert got["nakshatra"] == exp["nakshatra"]
