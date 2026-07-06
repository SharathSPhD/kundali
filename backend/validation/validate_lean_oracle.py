#!/usr/bin/env python3
"""Differential test: Python engine vs Lean `oracle` executable.

Run from repository root:
  python backend/validation/validate_lean_oracle.py

Or from backend/:
  python validation/validate_lean_oracle.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Repo layout: backend/validation/this_file.py -> repo root is parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]
LEAN_DIR = REPO_ROOT / "formal" / "lean-kundali"
ORACLE_BIN = LEAN_DIR / ".lake" / "build" / "bin" / "oracle"

sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.engine import constants as K  # noqa: E402
from app.engine import vargas  # noqa: E402


def dasha_balance(moon_longitude: float) -> dict:
    """Inline mirror of `dashas.dasha_balance` without ephemeris import."""
    lon = moon_longitude % 360.0
    nak_index = int(lon / K.NAKSHATRA_SPAN) % 27
    elapsed_fraction = (lon - nak_index * K.NAKSHATRA_SPAN) / K.NAKSHATRA_SPAN
    lord = K.NAKSHATRA_LORDS[nak_index]
    years = K.VIMSHOTTARI_YEARS[lord]
    return {
        "nakshatra_index": nak_index,
        "lord": lord,
        "balance_years": years * (1.0 - elapsed_fraction),
    }

VARGA_NAMES = ["D1", "D2", "D3", "D9", "D10", "D12"]
VARGA_FUNCS = {
    "D1": vargas.d1,
    "D2": vargas.d2,
    "D3": vargas.d3,
    "D9": vargas.d9,
    "D10": vargas.d10,
    "D12": vargas.d12,
}


def python_expected(moon_lon: float, maha_dur: float = 120.0) -> dict:
    lon = moon_lon % 360.0
    nak_index = int(lon / K.NAKSHATRA_SPAN) % 27
    pada_index = int((lon - nak_index * K.NAKSHATRA_SPAN) / K.PADA_SPAN) % 4
    bal = dasha_balance(lon)
    antar_sum = sum(
        maha_dur * K.VIMSHOTTARI_YEARS[l] / K.VIMSHOTTARI_TOTAL_YEARS
        for l in K.VIMSHOTTARI_ORDER
    )
    return {
        "nakshatra_index": nak_index,
        "pada_index": pada_index,
        "vimshottari_first_lord": bal["lord"],
        "vimshottari_balance_years": bal["balance_years"],
        "antardasha_duration_sum": antar_sum,
        "vargas": {name: VARGA_FUNCS[name](lon) for name in VARGA_NAMES},
    }


TEST_VECTORS: list[tuple[str, float]] = [
    ("aries_10", 10.0),
    ("taurus_15", 45.0),
    ("gemini_29", 89.0),
    ("grid_0", 0.0),
    ("grid_123_456", 123.456),
    ("near_wrap", 359.999),
]


def run_oracle(payload: dict) -> dict:
    tmp = LEAN_DIR / ".oracle_input.json"
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    cmd = ["lake", "env", "lake", "exe", "oracle", str(tmp)]
    proc = subprocess.run(
        cmd,
        cwd=LEAN_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"oracle failed (exit {proc.returncode}):\n{proc.stderr or proc.stdout}"
        )
    line = proc.stdout.strip().splitlines()[-1]
    return json.loads(line)


def near(a: float, b: float, tol: float = 1e-3) -> bool:
    return abs(a - b) <= tol


def compare(label: str, moon_lon: float, maha_dur: float = 120.0) -> None:
    micro = int(round(moon_lon * 1_000_000))
    dur_micro = int(round(maha_dur * 1_000_000))
    payload = {
        "label": label,
        "moon_longitude_microdeg": micro,
        "mahadasha_duration_micro": dur_micro,
        "vargas_to_compute": VARGA_NAMES,
    }
    py = python_expected(moon_lon, maha_dur)
    lean = run_oracle(payload)

    mismatches: list[str] = []
    for key in ("nakshatra_index", "pada_index", "vimshottari_first_lord"):
        if lean.get(key) != py[key]:
            mismatches.append(f"{key}: lean={lean.get(key)!r} python={py[key]!r}")
    if not near(float(lean.get("vimshottari_balance_years", 0)), py["vimshottari_balance_years"]):
        mismatches.append(
            f"vimshottari_balance_years: lean={lean.get('vimshottari_balance_years')} "
            f"python={py['vimshottari_balance_years']}"
        )
    if not near(float(lean.get("antardasha_duration_sum", 0)), py["antardasha_duration_sum"]):
        mismatches.append(
            f"antardasha_duration_sum: lean={lean.get('antardasha_duration_sum')} "
            f"python={py['antardasha_duration_sum']}"
        )
    lean_v = lean.get("vargas") or {}
    for name in VARGA_NAMES:
        if lean_v.get(name) != py["vargas"][name]:
            mismatches.append(
                f"vargas.{name}: lean={lean_v.get(name)!r} python={py['vargas'][name]!r}"
            )

    if mismatches:
        print(f"FAIL {label} @ moon={moon_lon}:")
        for m in mismatches:
            print(f"  - {m}")
        raise SystemExit(1)
    print(f"PASS {label} @ moon={moon_lon}")


def main() -> None:
    if not ORACLE_BIN.exists():
        print(f"Building oracle in {LEAN_DIR} …")
        build = subprocess.run(
            ["lake", "build", "oracle"],
            cwd=LEAN_DIR,
            check=False,
        )
        if build.returncode != 0 or not ORACLE_BIN.exists():
            raise SystemExit(
                "Lean oracle binary not found. Install elan/Lean and run "
                "`lake build oracle` in formal/lean-kundali/"
            )

    for label, lon in TEST_VECTORS:
        compare(label, lon)

    print(f"All {len(TEST_VECTORS)} vectors matched Python engine.")


if __name__ == "__main__":
    main()
