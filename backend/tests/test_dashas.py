from datetime import datetime, timedelta

import pytest

from app.engine import constants as K
from app.engine.dashas import active_path, build_vimshottari, dasha_balance
from app.engine.ephemeris import EngineConfig

BIRTH = datetime(1990, 5, 15, 6, 30)


def _dur_days(node):
    return (datetime.fromisoformat(node["end"]) - datetime.fromisoformat(node["start"])).total_seconds() / 86400.0


def test_balance_hand_computed():
    # Moon at 20.0 deg = halfway through Bharani (13.3333..26.6667), lord Venus (20y)
    bal = dasha_balance(20.0)
    assert bal["nakshatra"] == "Bharani"
    assert bal["lord"] == "Venus"
    assert abs(bal["elapsed_fraction"] - 0.5) < 1e-9
    assert abs(bal["balance_years"] - 10.0) < 1e-9


def test_balance_at_nakshatra_start():
    bal = dasha_balance(0.0)
    assert bal["lord"] == "Ketu"
    assert abs(bal["balance_years"] - 7.0) < 1e-9


def test_tree_sums_to_120_years():
    cfg = EngineConfig()
    tree = build_vimshottari(20.0, BIRTH, cfg, levels=3)
    total = sum(_dur_days(m) for m in tree["periods"])
    assert abs(total - 120 * 365.25) < 0.01
    # First maha is the balance of Venus: 10 years remain
    first = tree["periods"][0]
    assert first["lord"] == "Venus"
    assert abs(_dur_days(first) - 10 * 365.25) < 0.01


def test_sequence_and_antardasha_proportions():
    cfg = EngineConfig()
    tree = build_vimshottari(20.0, BIRTH, cfg, levels=3)
    # Maha sequence follows Vimshottari order from Venus
    lords = [m["lord"] for m in tree["periods"][:9]]
    assert lords == ["Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter",
                     "Saturn", "Mercury", "Ketu"]
    # Second maha (Sun, unclipped): 9 children, starting with Sun itself
    sun_maha = tree["periods"][1]
    kids = sun_maha["children"]
    assert len(kids) == 9
    assert kids[0]["lord"] == "Sun"
    assert [k["lord"] for k in kids[:3]] == ["Sun", "Moon", "Mars"]
    # Proportions: antar duration = maha_duration * lord_years / 120
    maha_days = 6 * 365.25
    for k in kids:
        expected = maha_days * K.VIMSHOTTARI_YEARS[k["lord"]] / 120.0
        assert abs(_dur_days(k) - expected) < 0.01
    # Antars sum to the maha
    assert abs(sum(_dur_days(k) for k in kids) - maha_days) < 0.01


def test_first_maha_children_computed_from_notional_start():
    cfg = EngineConfig()
    tree = build_vimshottari(20.0, BIRTH, cfg, levels=2)
    first = tree["periods"][0]  # Venus maha, half elapsed at birth
    kids = first["children"]
    # 10 of 20 Venus years elapsed: Venus antar (40mo) + Sun (12) + Moon (20)
    # + Mars (14) = 86 months = 7.1667y < 10y, so the first visible child is
    # inside Rahu antar (Venus-Rahu spans 7.1667..10.1667y).
    assert kids[0]["lord"] == "Rahu"
    assert kids[0]["start"] == first["start"]  # clipped to birth


def test_active_path_levels():
    cfg = EngineConfig()
    tree = build_vimshottari(20.0, BIRTH, cfg, levels=3)
    on = BIRTH + timedelta(days=15 * 365.25)
    path = active_path(tree, on)
    assert len(path) == 3
    assert path[0]["level_name"] == "mahadasha"
    assert path[1]["level_name"] == "antardasha"
    assert path[2]["level_name"] == "pratyantardasha"
    # 15y after birth with Venus balance 10y -> Sun maha (10..16y)
    assert path[0]["lord"] == "Sun"
    for parent, child in zip(path, path[1:]):
        assert parent["start"] <= child["start"] and child["end"] <= parent["end"]


def test_360_day_year_option():
    cfg = EngineConfig(dasha_year_days=360.0)
    tree = build_vimshottari(20.0, BIRTH, cfg, levels=1)
    total = sum(_dur_days(m) for m in tree["periods"])
    assert abs(total - 120 * 360.0) < 0.01


def test_levels_4_and_5():
    cfg = EngineConfig()
    tree = build_vimshottari(20.0, BIRTH, cfg, levels=5)
    path = active_path(tree, BIRTH + timedelta(days=20 * 365.25))
    assert len(path) == 5
    assert path[3]["level_name"] == "sookshma"
    assert path[4]["level_name"] == "prana"
