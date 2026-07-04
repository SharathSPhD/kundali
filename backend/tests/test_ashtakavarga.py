from app.engine.ashtakavarga import (
    BENEFIC_HOUSES, ROW_TOTALS, compute_ashtakavarga, transit_strength,
)
from conftest import make_chart

EXPECTED_TOTALS = {
    "Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54,
    "Jupiter": 56, "Venus": 52, "Saturn": 39,
}


def test_table_row_totals():
    assert ROW_TOTALS == EXPECTED_TOTALS
    assert sum(ROW_TOTALS.values()) == 337


def test_bav_totals_invariant_for_any_chart():
    """Each BAV distributes exactly its row total across the 12 signs,
    regardless of the chart; SAV always totals 337."""
    for lagna in [(0, 5.0), (7, 22.0)]:
        chart = make_chart(lagna=lagna)
        av = compute_ashtakavarga(chart)
        assert av["bav_totals"] == EXPECTED_TOTALS
        assert av["sav_total"] == 337
        assert sum(av["sav"]) == 337
        for planet, bindus in av["bav"].items():
            assert len(bindus) == 12
            assert all(0 <= b <= 8 for b in bindus)


def test_contributors_are_eight():
    for target, rows in BENEFIC_HOUSES.items():
        assert set(rows.keys()) == {"Sun", "Moon", "Mars", "Mercury",
                                    "Jupiter", "Venus", "Saturn", "Lagna"}


def test_transit_strength_helper():
    chart = make_chart()
    av = compute_ashtakavarga(chart)
    ts = transit_strength(av, 3, "Saturn")
    assert ts["sav_bindus"] == av["sav"][3]
    assert ts["sav_verdict"] in ("strong", "average", "weak")
    assert "bav_bindus" in ts
