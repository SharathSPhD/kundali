"""BPHS worked examples for the shodasha vargas."""
from app.engine.vargas import (
    VARGA_FUNCS, compute_vargas, d2, d3, d9, d10, d27, d30, d60,
)
from conftest import make_chart

# Sign indices: 0 Aries, 1 Taurus, 2 Gemini, 3 Cancer, 4 Leo, 5 Virgo,
# 6 Libra, 7 Scorpio, 8 Sagittarius, 9 Capricorn, 10 Aquarius, 11 Pisces


def lon(sign, deg):
    return sign * 30.0 + deg


def test_d9_bphs_worked_example_vargottama():
    # 15 deg Taurus: fixed sign -> count from 9th (Capricorn); 15 deg is the
    # 5th navamsa (3deg20' each); 5th from Capricorn = Taurus -> vargottama.
    assert d9(lon(1, 15.0)) == 1
    # 5 deg Aries (movable, from same sign): 2nd navamsa -> Taurus
    assert d9(lon(0, 5.0)) == 1
    # 29 deg Gemini (dual, from 5th = Libra): 9th navamsa -> Gemini (vargottama)
    assert d9(lon(2, 29.0)) == 2


def test_d2_classical_hora():
    assert d2(lon(0, 10.0)) == 4   # odd sign, first half -> Leo
    assert d2(lon(0, 20.0)) == 3   # odd sign, second half -> Cancer
    assert d2(lon(1, 10.0)) == 3   # even sign, first half -> Cancer
    assert d2(lon(1, 20.0)) == 4   # even sign, second half -> Leo


def test_d3_drekkana():
    assert d3(lon(0, 5.0)) == 0    # 1st drekkana -> same sign
    assert d3(lon(0, 15.0)) == 4   # 2nd -> 5th from Aries = Leo
    assert d3(lon(0, 25.0)) == 8   # 3rd -> 9th = Sagittarius
    assert d3(lon(2, 25.0)) == 10  # Gemini 3rd drekkana -> Aquarius


def test_d10_dashamsa():
    assert d10(lon(0, 1.0)) == 0    # odd sign: from itself
    assert d10(lon(0, 29.0)) == 9   # 10th part -> Capricorn
    assert d10(lon(1, 1.0)) == 9    # even sign: from 9th (Capricorn)
    assert d10(lon(1, 29.0)) == 6   # 10th part from Capricorn -> Libra


def test_d27_element_starts():
    assert d27(lon(0, 0.5)) == 0    # fire -> from Aries
    assert d27(lon(1, 0.5)) == 3    # earth -> from Cancer
    assert d27(lon(2, 0.5)) == 6    # air -> from Libra
    assert d27(lon(3, 0.5)) == 9    # water -> from Capricorn


def test_d30_asymmetric_spans_odd():
    # Odd sign: Mars 0-5 (Aries), Saturn 5-10 (Aquarius), Jupiter 10-18 (Sag),
    # Mercury 18-25 (Gemini), Venus 25-30 (Libra)
    assert d30(lon(0, 3.0)) == 0
    assert d30(lon(0, 7.0)) == 10
    assert d30(lon(0, 12.0)) == 8
    assert d30(lon(0, 20.0)) == 2
    assert d30(lon(0, 27.0)) == 6


def test_d30_asymmetric_spans_even():
    # Even sign: Venus 0-5 (Taurus), Mercury 5-12 (Virgo), Jupiter 12-20
    # (Pisces), Saturn 20-25 (Capricorn), Mars 25-30 (Scorpio)
    assert d30(lon(1, 3.0)) == 1
    assert d30(lon(1, 8.0)) == 5
    assert d30(lon(1, 15.0)) == 11
    assert d30(lon(1, 22.0)) == 9
    assert d30(lon(1, 27.0)) == 7


def test_d60_formula():
    # offset = floor(deg*2) mod 12 from the natal sign
    assert d60(lon(1, 15.0)) == (1 + (30 % 12)) % 12   # Taurus 15 -> Scorpio
    assert d60(lon(0, 0.4)) == 0                        # offset 0 -> same sign
    assert d60(lon(0, 29.9)) == (0 + (59 % 12)) % 12    # offset 11 -> Pisces


def test_all_16_vargas_produce_valid_signs():
    chart = make_chart(lagna=(1, 15.0))
    result = compute_vargas(chart)
    assert set(result["vargas"].keys()) == set(VARGA_FUNCS.keys())
    for v, data in result["vargas"].items():
        assert 0 <= data["lagna"]["sign"] <= 11
        assert len(data["planets"]) == 9
        for p in data["planets"].values():
            assert 0 <= p["sign"] <= 11


def test_vargottama_detection():
    # Lagna at 15 deg Taurus is vargottama (see worked example above)
    chart = make_chart(lagna=(1, 15.0))
    result = compute_vargas(chart)
    assert "Lagna" in result["vargottama"]
