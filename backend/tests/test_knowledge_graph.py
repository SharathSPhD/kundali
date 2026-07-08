"""Knowledge graph structure + BPHS-derived functional nature."""
from __future__ import annotations

import pytest

from app.knowledge.graph import get_graph


@pytest.fixture(scope="module")
def kg():
    return get_graph()


def test_graph_has_all_core_node_kinds(kg):
    stats = kg.stats()["by_kind"]
    assert stats["graha"] == 9
    assert stats["rashi"] == 12
    assert stats["bhava"] == 12
    assert stats["nakshatra"] == 27
    assert stats["area"] >= 10


def test_every_edge_carries_a_source(kg):
    missing = [e for e in kg.edges if not e.source]
    assert missing == [], f"edges without provenance: {[(e.src, e.rel, e.dst) for e in missing[:5]]}"


def test_rashi_lordships_match_classical(kg):
    expected = {
        "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
        "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
        "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
        "Pisces": "Jupiter",
    }
    for sign, lord in expected.items():
        node = kg.node(f"rashi:{sign}")
        assert node is not None and node.attrs["lord"] == lord


def test_exaltation_signs_match_classical(kg):
    expected = {
        "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo",
        "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra",
    }
    for graha, sign in expected.items():
        edges = kg.edges_from(f"graha:{graha}", rel="exalted_in")
        assert edges and edges[0].dst == f"rashi:{sign}"


def test_vimshottari_nakshatra_lords_sum_correctly(kg):
    """Each vimshottari lord rules exactly 3 nakshatras."""
    counts: dict[str, int] = {}
    for graha in ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"):
        counts[graha] = len(kg.edges_from(f"graha:{graha}", rel="rules_nakshatra"))
    assert all(c == 3 for c in counts.values()), counts


def test_entity_extraction_finds_sanskrit_and_english(kg):
    ids = {n.id for n in kg.find_entities("Is shani in my seventh house bad for marriage?")}
    assert "graha:Saturn" in ids
    assert "bhava:7" in ids
    assert "area:relationships" in ids


@pytest.mark.parametrize(
    "graha,lagna,verdict",
    [
        ("Saturn", "Taurus", "yogakaraka"),   # 9L + 10L
        ("Saturn", "Libra", "yogakaraka"),    # 4L + 5L
        ("Mars", "Cancer", "yogakaraka"),     # 5L + 10L
        ("Mars", "Leo", "yogakaraka"),        # 4L + 9L
        ("Venus", "Capricorn", "yogakaraka"), # 5L + 10L
        ("Venus", "Aquarius", "yogakaraka"),  # 4L + 9L
        ("Jupiter", "Aries", "functional benefic"),   # 9L + 12L
        ("Saturn", "Cancer", "functional malefic"),   # 7L + 8L
        ("Mercury", "Aries", "functional malefic"),   # 3L + 6L
        ("Jupiter", "Taurus", "functional malefic"),  # 8L + 11L
    ],
)
def test_functional_nature_matches_bphs_34(kg, graha, lagna, verdict):
    assert kg.functional_nature(graha, lagna)["verdict"] == verdict


def test_functional_nature_marks_marakas(kg):
    # For Aries lagna Venus rules 2 and 7 — the classic maraka lord.
    fn = kg.functional_nature("Venus", "Aries")
    assert fn["maraka"] is True


def test_nodes_get_nodal_verdict(kg):
    assert kg.functional_nature("Rahu", "Aries")["verdict"] == "nodal"


def test_subgraph_focus_limits_nodes(kg):
    sub = kg.subgraph(focus="graha:Saturn", depth=1)
    ids = {n["id"] for n in sub["nodes"]}
    assert "graha:Saturn" in ids
    assert len(ids) < len(kg.nodes)
    for e in sub["edges"]:
        assert e["src"] in ids and e["dst"] in ids
