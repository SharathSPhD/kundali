"""Synthetic charts triggering / not triggering key yogas."""
from app.engine.yogas import evaluate_yogas
from conftest import make_chart


def get(yogas, name):
    for y in yogas:
        if y["name"] == name:
            return y
    raise AssertionError(f"yoga {name} not in results")


def any_present(yogas, prefix):
    return any(y["present"] for y in yogas if y["name"].startswith(prefix))


def test_ruchaka_present():
    # Mars exalted in Capricorn, 10th from Aries lagna
    chart = make_chart(lagna=(0, 10.0), placements={"Mars": (9, 28.0)})
    y = get(evaluate_yogas(chart), "Ruchaka Yoga")
    assert y["present"]
    assert any("exalted" in f for f in y["factors"])


def test_ruchaka_absent_outside_kendra():
    # Same Mars but from Taurus lagna it falls in the 9th house
    chart = make_chart(lagna=(1, 10.0), placements={"Mars": (9, 28.0)})
    assert not get(evaluate_yogas(chart), "Ruchaka Yoga")["present"]


def test_gaja_kesari():
    chart = make_chart(placements={"Moon": (3, 10.0), "Jupiter": (6, 12.0)})
    assert get(evaluate_yogas(chart), "Gaja Kesari Yoga")["present"]  # 4th from Moon
    chart2 = make_chart(placements={"Moon": (3, 10.0), "Jupiter": (7, 12.0)})
    assert not get(evaluate_yogas(chart2), "Gaja Kesari Yoga")["present"]


def test_budhaditya():
    chart = make_chart(placements={"Sun": (4, 10.0), "Mercury": (4, 20.0)})
    y = get(evaluate_yogas(chart), "Budhaditya Yoga")
    assert y["present"]
    chart2 = make_chart(placements={"Sun": (4, 10.0), "Mercury": (5, 20.0)})
    assert not get(evaluate_yogas(chart2), "Budhaditya Yoga")["present"]


def test_chandra_mangala():
    chart = make_chart(placements={"Moon": (7, 10.0), "Mars": (7, 22.0)})
    assert get(evaluate_yogas(chart), "Chandra-Mangala Yoga")["present"]


def test_viparita_harsha():
    # Aries lagna: 6th lord Mercury placed in the 8th (Scorpio)
    chart = make_chart(lagna=(0, 10.0), placements={"Mercury": (7, 12.0)})
    y = get(evaluate_yogas(chart), "Harsha (Viparita Raja) Yoga")
    assert y["present"]


def test_kemadruma_present_and_cancelled():
    placements = {
        "Sun": (3, 10.0), "Moon": (0, 10.0), "Mars": (2, 5.0),
        "Mercury": (4, 12.0), "Jupiter": (5, 8.0), "Venus": (8, 18.0),
        "Saturn": (7, 25.0),
    }
    # Taurus lagna: Moon in 12th house (not kendra) -> Kemadruma holds
    chart = make_chart(lagna=(1, 5.0), placements=placements)
    assert get(evaluate_yogas(chart), "Kemadruma Yoga")["present"]
    # Aries lagna: Moon in 1st house (kendra from lagna) -> cancelled
    chart2 = make_chart(lagna=(0, 5.0), placements=placements)
    y2 = get(evaluate_yogas(chart2), "Kemadruma Yoga")
    assert not y2["present"]
    assert any("CANCELLED" in f for f in y2["factors"])


def test_shakata_and_cancellation():
    placements = {"Jupiter": (0, 10.0), "Moon": (5, 10.0)}  # Moon 6th from Jupiter
    chart = make_chart(lagna=(1, 5.0), placements=placements)  # Moon in house 5
    assert get(evaluate_yogas(chart), "Shakata Yoga")["present"]
    chart2 = make_chart(lagna=(5, 5.0), placements=placements)  # Moon in house 1
    assert not get(evaluate_yogas(chart2), "Shakata Yoga")["present"]


def test_adhi():
    chart = make_chart(placements={
        "Moon": (0, 10.0), "Jupiter": (5, 5.0), "Venus": (6, 5.0),
        "Mercury": (7, 5.0), "Sun": (2, 10.0),
    })
    y = get(evaluate_yogas(chart), "Adhi Yoga")
    assert y["present"]
    assert y["strength"] == 1.0


def test_vesi_and_sunapha():
    chart = make_chart(placements={
        "Sun": (4, 10.0), "Venus": (5, 5.0), "Mercury": (5, 25.0),
        "Moon": (7, 20.0), "Mars": (8, 5.0), "Jupiter": (8, 8.0),
        "Saturn": (10, 25.0),
    })
    yogas = evaluate_yogas(chart)
    assert get(yogas, "Vesi Yoga")["present"]       # Venus+Mercury 2nd from Sun
    assert get(yogas, "Sunapha Yoga")["present"]    # Mars+Jupiter 2nd from Moon
    assert not get(yogas, "Kemadruma Yoga")["present"]


def test_kala_sarpa():
    chart = make_chart(placements={
        "Rahu": (0, 10.0), "Ketu": (6, 10.0),
        "Sun": (1, 0.0), "Moon": (2, 0.0), "Mars": (3, 0.0),
        "Mercury": (1, 15.0), "Jupiter": (4, 0.0), "Venus": (5, 0.0),
        "Saturn": (6, 0.0),
    })
    y = get(evaluate_yogas(chart), "Kala Sarpa Yoga")
    assert y["present"]
    assert any("Rahu-to-Ketu" in f or "Ketu-to-Rahu" in f for f in y["factors"])
    # Default spread chart: planets on both sides of the axis -> absent
    assert not get(evaluate_yogas(make_chart()), "Kala Sarpa Yoga")["present"]


def test_neecha_bhanga():
    # Jupiter debilitated in Capricorn; dispositor Saturn in Cancer = kendra
    # (4th) from Aries lagna -> bhanga applies
    chart = make_chart(lagna=(0, 10.0), placements={
        "Jupiter": (9, 10.0), "Saturn": (3, 5.0), "Moon": (7, 20.0),
    })
    y = get(evaluate_yogas(chart), "Neecha Bhanga (Jupiter)")
    assert y["present"]
    # Venus debilitated in Virgo with no cancellation factors
    chart2 = make_chart(lagna=(0, 10.0), placements={
        "Venus": (5, 10.0), "Mercury": (1, 5.0), "Jupiter": (7, 3.0),
        "Moon": (8, 25.0), "Sun": (4, 10.0), "Saturn": (10, 25.0),
    })
    y2 = get(evaluate_yogas(chart2), "Neecha Bhanga (Venus)")
    assert not y2["present"]


def test_raja_yoga_kendra_trikona_conjunction():
    # Aries lagna: Moon lords 4th (kendra), Sun lords 5th (trikona); conjunct
    chart = make_chart(lagna=(0, 10.0), placements={
        "Moon": (2, 10.0), "Sun": (2, 5.0),
    })
    yogas = evaluate_yogas(chart)
    assert any_present(yogas, "Raja Yoga (")


def test_dhana_yoga():
    # Aries lagna: 2nd lord Venus conjunct 9th lord Jupiter
    chart = make_chart(lagna=(0, 10.0), placements={
        "Venus": (3, 10.0), "Jupiter": (3, 20.0),
    })
    assert any_present(evaluate_yogas(chart), "Dhana Yoga (")


def test_lakshmi_yoga():
    # Aries lagna: 9th lord Jupiter own-sign in the 9th; Venus own-sign in 7th
    chart = make_chart(lagna=(0, 10.0), placements={
        "Jupiter": (8, 5.0), "Venus": (6, 18.0),
    })
    assert get(evaluate_yogas(chart), "Lakshmi Yoga")["present"]


def test_output_shape():
    for y in evaluate_yogas(make_chart()):
        assert set(y.keys()) == {"name", "sanskrit_category", "present",
                                 "factors", "strength"}
        assert isinstance(y["factors"], list)
        assert 0.0 <= y["strength"] <= 1.0 or not y["present"]
