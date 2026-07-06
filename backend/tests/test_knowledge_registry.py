"""Knowledge-catalog loader and lookup helpers."""
import pytest

from app.knowledge.registry import area_info, load_rules, yoga_info


def test_load_rules_yogas_validates():
    data = load_rules("yogas")
    names = {entry["name"] for entry in data["yogas"]}
    assert "Gaja Kesari Yoga" in names


def test_load_rules_area_house_polarity_validates():
    data = load_rules("area_house_polarity")
    assert "career" in data["areas"]
    assert "houses" in data["areas"]["career"]


def test_load_rules_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_rules("does_not_exist")


def test_yoga_info_exact_match():
    info = yoga_info("Gaja Kesari Yoga")
    assert info is not None
    assert "Jupiter" in info["rule_description"]
    assert info["source"]


def test_yoga_info_case_insensitive_match():
    info = yoga_info("gaja kesari yoga")
    assert info is not None
    assert info["name"] == "Gaja Kesari Yoga"


def test_yoga_info_unknown_returns_none():
    assert yoga_info("Some Made Up Yoga") is None


def test_area_info_known_area():
    info = area_info("career")
    assert info is not None
    assert info["houses"][10] == 1.0


def test_area_info_unknown_area_returns_none():
    assert area_info("not_a_real_area") is None
