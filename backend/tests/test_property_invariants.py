"""Property-based fuzz tests cross-checking Lean formalized invariants.

Mirrors claims in formal/lean-kundali/Kundali/{Longitude,Nakshatra,Vargas}.lean
and Vimshottari proportional subdivision (dashas.py).
"""
from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine import constants as K
from app.engine import vargas
from app.engine.dashas import _sequence_from
from app.engine.ephemeris import nakshatra_of

# Same normalization as ephemeris._position_dict / nakshatra_of / vargas._sign_deg
def normalize_longitude(lon: float) -> float:
    n = lon % 360.0
    # Python % can yield exactly 360.0 for tiny negative inputs (float edge case).
    return 0.0 if n == 360.0 else n


FORMAL_VARGAS = {
    "D1": vargas.d1,
    "D2": vargas.d2,
    "D3": vargas.d3,
    "D9": vargas.d9,
    "D10": vargas.d10,
    "D12": vargas.d12,
}

finite_lon = st.floats(
    min_value=-1e6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
)

bounded_lon = st.floats(
    min_value=0.0,
    max_value=360.0,
    allow_nan=False,
    allow_infinity=False,
)

positive_duration = st.floats(
    min_value=1e-6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
)


@settings(max_examples=200)
@given(finite_lon)
def test_longitude_normalize_range_and_idempotent(lon: float):
    """Lean: normalize_range, normalize_idempotent."""
    n1 = normalize_longitude(lon)
    assert 0.0 <= n1 < 360.0
    n2 = normalize_longitude(n1)
    assert n1 == pytest.approx(n2)


@settings(max_examples=200)
@given(bounded_lon)
def test_nakshatra_pada_indices_total(lon: float):
    """Lean: nakshatra_exhaustive / pada_exhaustive (0-based pada index)."""
    nak = nakshatra_of(lon)
    assert 0 <= nak["index"] < 27
    assert 1 <= nak["pada"] <= 4
    pada_zero = nak["pada"] - 1
    assert 0 <= pada_zero < 4


@settings(max_examples=200)
@given(bounded_lon)
def test_varga_sign_indices_total(lon: float):
    """Lean: d1_total … d12_total."""
    for name, fn in FORMAL_VARGAS.items():
        sign = fn(lon)
        assert 0 <= sign < 12, f"{name} returned {sign} for lon={lon}"


@settings(max_examples=200)
@given(positive_duration)
def test_vimshottari_subdurations_sum_to_parent(duration_days: float):
    """Lean: antardasha_durations_sum — proportional split sums to parent."""
    lord = K.VIMSHOTTARI_ORDER[0]
    subs = _sequence_from(lord)
    parts = [
        duration_days * K.VIMSHOTTARI_YEARS[sub] / K.VIMSHOTTARI_TOTAL_YEARS
        for sub in subs
    ]
    assert len(parts) == 9
    assert math.isclose(sum(parts), duration_days, rel_tol=1e-9, abs_tol=1e-6)
