"""vedastro-org `15000-Famous-People-Birth-Date-Location` validation.

Two checks, since this dataset ships no expected chart placements (it's a
birth-data corpus, not a chart-answer key):

1. **Crash/sanity smoke test** — every one of the 15,807 rows must produce a
   structurally valid chart (valid sign 0-11, valid nakshatra 0-26, lagna
   present, all 9 grahas present) with no exceptions. This is a robustness
   check across 125 years of real, messy, historical tz/DST data.
2. **Statistical sanity on the AA-rated stratum** — Sun-sign and Moon-nakshatra
   distributions should be close to the ~uniform spread expected from a
   large, demographically-unselected sample (no astrological claim is being
   tested here, only "does the engine produce a sane, non-degenerate spread
   of outputs" — e.g. a bug that always computed sidereal longitude modulo
   the wrong period would collapse everything into a handful of signs).
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from app.engine.chart import build_chart
from app.engine.constants import SIGN_NAMES
from validation.common import parse_vedastro_birthtime

DATA_PATH = Path(__file__).parent / "data" / "birth_location.csv"


def load_people():
    with open(DATA_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            person = parse_vedastro_birthtime(row["RowKey"], row["Name"],
                                              row["BirthTime"], row["Notes"])
            if person is not None:
                yield person


def smoke_test() -> dict:
    total = 0
    crashed = []
    for person in load_people():
        total += 1
        try:
            chart = build_chart(person.birth)
            assert 0 <= chart["lagna"]["sign"] <= 11
            for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                        "Saturn", "Rahu", "Ketu"):
                p = chart["planets"][name]
                assert 0 <= p["sign"] <= 11
                assert 0 <= p["nakshatra_index"] <= 26
        except Exception as exc:  # noqa: BLE001 - deliberately broad for a smoke test
            crashed.append({"row_key": person.row_key, "error": f"{type(exc).__name__}: {exc}"})
    return {"total_rows": total, "crashed": len(crashed), "crash_examples": crashed[:10]}


def distribution_sanity(sample_size: int = 500, rodden_filter: tuple[str, ...] = ("AA", "A")) -> dict:
    people = [p for p in load_people() if p.rodden in rodden_filter]
    # Deterministic stratified sample: every Nth record, not random, so
    # results are reproducible across runs.
    step = max(1, len(people) // sample_size)
    sample = people[::step][:sample_size]

    sun_signs = Counter()
    moon_nakshatras = Counter()
    lagna_signs = Counter()
    for person in sample:
        chart = build_chart(person.birth)
        sun_signs[SIGN_NAMES[chart["planets"]["Sun"]["sign"]]] += 1
        moon_nakshatras[chart["planets"]["Moon"]["nakshatra"]] += 1
        lagna_signs[SIGN_NAMES[chart["lagna"]["sign"]]] += 1

    n = len(sample)
    expected_sign_frac = 1 / 12
    expected_nak_frac = 1 / 27
    max_sign_dev = max(abs(c / n - expected_sign_frac) for c in sun_signs.values()) if n else None
    max_nak_dev = max(abs(c / n - expected_nak_frac) for c in moon_nakshatras.values()) if n else None

    return {
        "eligible_rodden_aa_a": len(people),
        "sample_size": n,
        "sun_sign_counts": dict(sun_signs.most_common()),
        "lagna_sign_counts": dict(lagna_signs.most_common()),
        "moon_nakshatra_counts": dict(moon_nakshatras.most_common()),
        "max_deviation_from_uniform_sun_sign": round(max_sign_dev, 4) if max_sign_dev else None,
        "max_deviation_from_uniform_nakshatra": round(max_nak_dev, 4) if max_nak_dev else None,
    }


if __name__ == "__main__":
    result = {"smoke_test": smoke_test(), "distribution_sanity": distribution_sanity()}
    print(json.dumps(result, indent=2))
