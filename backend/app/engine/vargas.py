"""All 16 shodasha vargas per BPHS.

Each varga function takes an absolute sidereal longitude and returns the varga
sign index (0=Aries..11=Pisces).
"""
from __future__ import annotations

import math

from . import constants as K

VARGA_NAMES = ["D1", "D2", "D3", "D4", "D7", "D9", "D10", "D12",
               "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"]

_EPS = 1e-9  # guard floating-point at part boundaries


def _sign_deg(lon: float):
    lon = lon % 360.0
    return int(lon // 30), lon % 30.0


def _part(deg: float, span: float, nparts: int) -> int:
    return min(int((deg + _EPS) / span), nparts - 1)


def d1(lon: float) -> int:
    return _sign_deg(lon)[0]


def d2(lon: float) -> int:
    """Classical Parashari hora: odd sign 0-15 -> Leo, 15-30 -> Cancer;
    even sign reversed (0-15 -> Cancer, 15-30 -> Leo)."""
    sign, deg = _sign_deg(lon)
    first_half = deg < 15.0
    if sign in K.ODD_SIGNS:
        return 4 if first_half else 3   # Leo / Cancer
    return 3 if first_half else 4       # Cancer / Leo


def d3(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 10.0, 3)
    return (sign + part * 4) % 12       # same, 5th, 9th


def d4(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 7.5, 4)
    return (sign + part * 3) % 12       # 1st, 4th, 7th, 10th


def d7(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 30.0 / 7.0, 7)
    start = sign if sign in K.ODD_SIGNS else (sign + 6) % 12
    return (start + part) % 12


def d9(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 30.0 / 9.0, 9)
    modality = K.sign_modality(sign)
    if modality == 0:       # movable: from same sign
        start = sign
    elif modality == 1:     # fixed: from 9th
        start = (sign + 8) % 12
    else:                   # dual: from 5th
        start = (sign + 4) % 12
    return (start + part) % 12


def d10(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 3.0, 10)
    start = sign if sign in K.ODD_SIGNS else (sign + 8) % 12   # odd same, even 9th
    return (start + part) % 12


def d12(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 2.5, 12)
    return (sign + part) % 12


def d16(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 30.0 / 16.0, 16)
    start = {0: 0, 1: 4, 2: 8}[K.sign_modality(sign)]  # movable Aries, fixed Leo, dual Sag
    return (start + part) % 12


def d20(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 1.5, 20)
    start = {0: 0, 1: 8, 2: 4}[K.sign_modality(sign)]  # movable Aries, fixed Sag, dual Leo
    return (start + part) % 12


def d24(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 1.25, 24)
    start = 4 if sign in K.ODD_SIGNS else 3            # odd Leo, even Cancer
    return (start + part) % 12


def d27(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 30.0 / 27.0, 27)
    start = {0: 0, 1: 3, 2: 6, 3: 9}[K.sign_element(sign)]  # fire Aries, earth Cancer, air Libra, water Capricorn
    return (start + part) % 12


# D30 trimshamsha: (upper_bound, sign) spans
_D30_ODD = [(5.0, 0), (10.0, 10), (18.0, 8), (25.0, 2), (30.0, 6)]   # Mars, Sat, Jup, Merc, Ven
_D30_EVEN = [(5.0, 1), (12.0, 5), (20.0, 11), (25.0, 9), (30.0, 7)]  # Ven, Merc, Jup, Sat, Mars


def d30(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    spans = _D30_ODD if sign in K.ODD_SIGNS else _D30_EVEN
    for upper, vsign in spans:
        if deg < upper + _EPS:
            return vsign
    return spans[-1][1]


def d40(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 0.75, 40)
    start = 0 if sign in K.ODD_SIGNS else 6            # odd Aries, even Libra
    return (start + part) % 12


def d45(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    part = _part(deg, 30.0 / 45.0, 45)
    start = {0: 0, 1: 4, 2: 8}[K.sign_modality(sign)]  # movable Aries, fixed Leo, dual Sag
    return (start + part) % 12


def d60(lon: float) -> int:
    sign, deg = _sign_deg(lon)
    offset = int(math.floor(deg * 2.0 + _EPS)) % 12
    return (sign + offset) % 12


VARGA_FUNCS = {
    "D1": d1, "D2": d2, "D3": d3, "D4": d4, "D7": d7, "D9": d9, "D10": d10,
    "D12": d12, "D16": d16, "D20": d20, "D24": d24, "D27": d27, "D30": d30,
    "D40": d40, "D45": d45, "D60": d60,
}


def compute_vargas(chart: dict, charts: list[str] | None = None) -> dict:
    """Varga sign placements for lagna + 9 grahas from a natal chart dict."""
    wanted = charts or VARGA_NAMES
    out = {}
    for v in wanted:
        fn = VARGA_FUNCS.get(v)
        if fn is None:
            raise ValueError(f"unknown varga: {v}")
        lagna_sign = fn(chart["lagna"]["longitude"])
        placements = {}
        for name, p in chart["planets"].items():
            s = fn(p["longitude"])
            placements[name] = {"sign": s, "sign_name": K.SIGN_NAMES[s]}
        out[v] = {
            "lagna": {"sign": lagna_sign, "sign_name": K.SIGN_NAMES[lagna_sign]},
            "planets": placements,
        }

    # Vargottama: same sign in D1 and D9 (computed regardless of `wanted`)
    vargottama = []
    if d9(chart["lagna"]["longitude"]) == d1(chart["lagna"]["longitude"]):
        vargottama.append("Lagna")
    for name, p in chart["planets"].items():
        if d9(p["longitude"]) == d1(p["longitude"]):
            vargottama.append(name)
    return {"vargas": out, "vargottama": vargottama}
