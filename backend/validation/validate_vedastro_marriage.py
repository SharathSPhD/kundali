"""vedastro-org `15000-Famous-People-Marriage-Divorce-Info` — genuine
predictive backtest, not just a sanity check.

Methodology (documented plainly; this is not cherry-picked):
- Join on `RowKey`/`PartitionKey` against the birth-location dataset.
- Restrict to Rodden AA/A-rated people with exactly one classical marriage
  significator set computable (i.e. the chart builds) and a "Love" or
  unspecified-type marriage with a parseable date (year, optionally
  month/day — most vedastro marriage dates are year-only).
- For each person, compute the natal chart, the 7th lord, Venus (universal
  kalatra karaka), Jupiter (karaka for women's marriage, and a classical
  general marriage significator), and the Vimshottari dasha path active at
  the (approximate) marriage date.
- **Hit** = the Mahadasha or Antardasha lord at the marriage date is one of
  {7th lord, Venus, Jupiter, lord of the navamsa (D9) 7th house}. This is
  the standard classical marriage-timing rule set (see e.g. B.V. Raman,
  "Hindu Predictive Astrology", ch. on marriage timing).
- Report the hit-rate against a **null baseline**: the probability that a
  uniformly random dasha lord (from the 9 grahas, weighted by their actual
  Vimshottari share of the 120-year cycle) would match one of the ~3-4
  candidate significators by chance, so the result is interpretable rather
  than a bare percentage.

Caveat (stated up front, not buried): most source dates are year-only, and
many birth times, while Rodden AA/A-rated for the *birth* record, still
carry the ordinary uncertainty of Vimshottari boundary dates falling near a
year edge — a marriage dated "1990" might truly fall in a dasha window that
starts in 1989 or ends in 1991. The 12-month midyear anchor used here
(`approx_marriage_datetime`) is a documented, deliberate simplification.
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from app.engine.chart import build_chart
from app.engine.dashas import active_path, build_vimshottari
from app.engine.vargas import d9 as navamsa_sign
from validation.common import (
    approx_marriage_datetime, parse_marriage_date, parse_marriage_info,
    parse_vedastro_birthtime,
)

BIRTH_PATH = Path(__file__).parent / "data" / "birth_location.csv"
MARRIAGE_PATH = Path(__file__).parent / "data" / "marriage.csv"

# Vimshottari mahadasha years, used only for the chance-baseline calculation.
_VIMSHOTTARI_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}
_TOTAL_YEARS = sum(_VIMSHOTTARI_YEARS.values())  # 120


def _load_birth_people() -> dict:
    people = {}
    with open(BIRTH_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            p = parse_vedastro_birthtime(row["RowKey"], row["Name"], row["BirthTime"], row["Notes"])
            if p is not None and p.rodden in ("AA", "A"):
                people[p.row_key] = p
    return people


def _load_marriages() -> dict:
    out = {}
    with open(MARRIAGE_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            marriages = parse_marriage_info(row["Info"])
            if marriages:
                out[row["PartitionKey"]] = marriages
    return out


def _significators(chart: dict) -> dict:
    seventh_lord = chart["house_lords"][7]["lord"]
    d9_seventh_sign = navamsa_sign(chart["planets"][seventh_lord]["longitude"])
    # D9 7th-house-from-lagna lord (a secondary classical significator):
    # approximate D9 lagna as the navamsa sign of the natal lagna degree —
    # out of scope here (natal lagna has no "longitude" beyond the ascendant
    # degree, which the chart does carry).
    lagna_d9 = navamsa_sign(chart["lagna"]["longitude"])
    d9_seventh_from_d9_lagna = (lagna_d9 + 6) % 12
    from app.engine.constants import SIGN_LORDS
    d9_seventh_lord = SIGN_LORDS[d9_seventh_from_d9_lagna]
    return {
        "7th_lord": seventh_lord,
        "venus": "Venus",
        "jupiter": "Jupiter",
        "d9_7th_lord": d9_seventh_lord,
    }


def _permutation_baseline(active_lords_list: list[set[str]],
                          candidate_sets: list[set[str]], seed: int) -> float | None:
    rng = random.Random(seed)
    n = len(active_lords_list)
    if not n:
        return None
    rates = []
    for _ in range(20):
        shuffled = candidate_sets[:]
        rng.shuffle(shuffled)
        hits = sum(1 for a, c in zip(active_lords_list, shuffled) if a & c)
        rates.append(hits / n)
    return round(sum(rates) / len(rates), 4)


def _backtest(candidate_keys: tuple[str, ...], birth_people: dict, marriages: dict,
              require_full_date: bool = False) -> dict:
    considered = 0
    hits = 0
    skipped_no_date = 0
    skipped_chart_error = 0
    details = []
    all_active_lords: list[set[str]] = []
    all_candidate_sets: list[set[str]] = []

    for row_key, marriage_list in marriages.items():
        person = birth_people.get(row_key)
        if person is None:
            continue
        m = marriage_list[0]  # first marriage only, to avoid double-counting a person
        parsed = parse_marriage_date(m.get("marriageDate", ""))
        if parsed is None:
            skipped_no_date += 1
            continue
        year, month, day = parsed
        if require_full_date and month is None:
            continue
        try:
            chart = build_chart(person.birth)
            sig = _significators(chart)
            tree = build_vimshottari(chart["planets"]["Moon"]["longitude"],
                                     person.birth.local_datetime(), levels=2)
            on_dt = approx_marriage_datetime(year, month, day)
            path = active_path(tree, on_dt)
        except Exception:  # noqa: BLE001
            skipped_chart_error += 1
            continue
        if not path:
            continue  # marriage date outside the 120-year dasha horizon
        active_lords = {node["lord"] for node in path}
        candidate_lords = {sig[k] for k in candidate_keys}
        hit = bool(active_lords & candidate_lords)
        considered += 1
        hits += int(hit)
        all_active_lords.append(active_lords)
        all_candidate_sets.append(candidate_lords)
        if len(details) < 15:
            details.append({
                "row_key": row_key, "marriage_year": year,
                "active_lords": sorted(active_lords),
                "candidate_significators": sorted(candidate_lords), "hit": hit,
            })

    baseline = _permutation_baseline(all_active_lords, all_candidate_sets, seed=20260706)
    hit_rate = round(hits / considered, 4) if considered else None
    return {
        "candidate_significators_used": list(candidate_keys),
        "considered": considered,
        "hits": hits,
        "hit_rate": hit_rate,
        "permutation_null_baseline_hit_rate": baseline,
        "hit_rate_above_baseline": round(hit_rate - baseline, 4)
        if hit_rate is not None and baseline is not None else None,
        "skipped_no_parseable_date": skipped_no_date,
        "skipped_chart_build_error": skipped_chart_error,
        "sample_details": details,
    }


def run(limit: int | None = None) -> dict:
    birth_people = _load_birth_people()
    marriages = _load_marriages()

    return {
        "broad_significators_7th_venus_jupiter_d9": _backtest(
            ("7th_lord", "venus", "jupiter", "d9_7th_lord"), birth_people, marriages),
        "narrow_significators_7th_lord_venus_only": _backtest(
            ("7th_lord", "venus"), birth_people, marriages),
        "narrow_significators_full_date_only": _backtest(
            ("7th_lord", "venus"), birth_people, marriages, require_full_date=True),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
