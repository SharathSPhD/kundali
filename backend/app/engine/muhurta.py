"""Personalized muhurta (electional timing) scan.

For each day in a horizon, computes the panchanga at that day's sunrise for
the person's location and scores its suitability for a chosen activity by
combining, per the standard Muhurta Chintamani / Parijata tradition:

- **Tara bala** — the day nakshatra counted from the person's own janma
  nakshatra (cycle of 9; Sampat/Kshema/Sadhana/Mitra/Parama-Mitra favor).
- **Chandra bala** — the transit Moon's sign counted from the janma rashi
  (6th, 8th and 12th positions avoided).
- **Tithi class** — rikta tithis (4/9/14) and amavasya avoided.
- **Vara** — activity-appropriate weekdays.
- **Nakshatra list** — the activity's classical electional nakshatras.

Every reason is reported so the ranking is auditable. This is a day-level
screen, not a full lagna-level muhurta — the output says so.
"""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from .chart import BirthData, build_chart
from .ephemeris import EngineConfig
from .panchanga import compute_panchanga
from .constants import NAKSHATRA_NAMES

_DATA = Path(__file__).resolve().parent.parent / "knowledge" / "graph_data" / "muhurta.yaml"

# compute_panchanga reports vara by index (0=Sunday) with Sanskrit names;
# the activity tables use English weekday names.
_VARA_ENGLISH = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


@lru_cache(maxsize=1)
def _tables() -> dict:
    with _DATA.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def activities() -> dict[str, dict]:
    return _tables().get("activities") or {}


def resolve_activity(name: str) -> Optional[str]:
    name = (name or "").strip().lower()
    for key, spec in activities().items():
        if name == key or name in (spec.get("aliases") or []):
            return key
    return None


def _tara(janma_idx: int, day_idx: int) -> dict:
    count = (day_idx - janma_idx) % 27 % 9 + 1
    spec = (_tables().get("tara_bala") or {}).get(count, {})
    return {"count": count, "name": spec.get("name", "?"),
            "favorable": bool(spec.get("favorable")), "note": spec.get("note", "")}


def scan_muhurta(
    birth: BirthData,
    activity: str,
    start: date,
    days: int = 30,
    config: Optional[EngineConfig] = None,
) -> dict:
    """Rank the next `days` days for `activity`, personalized to `birth`."""
    key = resolve_activity(activity)
    if key is None:
        raise ValueError(
            f"unknown activity '{activity}'; known: {sorted(activities().keys())}"
        )
    spec = activities()[key]
    config = config or EngineConfig()

    natal = build_chart(birth, config)
    janma_nak_idx = natal["planets"]["Moon"]["nakshatra_index"]
    janma_rashi = natal["planets"]["Moon"]["sign"]

    days = max(1, min(days, 120))
    results = []
    for offset in range(days):
        d = start + timedelta(days=offset)
        # Panchanga at local noon-ish anchor; compute_panchanga uses the most
        # recent sunrise for vara, and tithi/nakshatra at the given moment.
        probe = BirthData(
            date=d.isoformat(), time="12:00", tz_offset=birth.tz_offset,
            lat=birth.lat, lon=birth.lon,
        )
        pan = compute_panchanga(probe, config)
        day_nak = pan["nakshatra"]["name"]
        day_nak_idx = pan["nakshatra"]["index"]
        tithi_num = pan["tithi"]["number"]
        vara = _VARA_ENGLISH[pan["vara"]["index"] % 7]
        vara_sanskrit = pan["vara"]["name"]
        moon_sign = int(pan["moon_longitude"] // 30) if "moon_longitude" in pan else None

        score = 0.0
        reasons: list[dict] = []

        tara = _tara(janma_nak_idx, day_nak_idx)
        score += 1.0 if tara["favorable"] else (-1.5 if tara["count"] == 7 else -1.0)
        reasons.append({
            "factor": "tara_bala",
            "verdict": "favorable" if tara["favorable"] else "unfavorable",
            "detail": f"{day_nak} is your {tara['name']} tara ({tara['note']})",
            "source": "Muhurta Chintamani tara bala cycle",
        })

        if moon_sign is not None:
            chandra_pos = (moon_sign - janma_rashi) % 12 + 1
            bad = chandra_pos in (6, 8, 12)
            score += -1.0 if bad else 0.5
            reasons.append({
                "factor": "chandra_bala",
                "verdict": "unfavorable" if bad else "favorable",
                "detail": f"transit Moon is {chandra_pos} from your janma rashi",
                "source": "standard chandra bala rule (6/8/12 avoided)",
            })

        tithi_avoid = set(spec.get("avoid_tithis") or [])
        tithi_bad = tithi_num in tithi_avoid or (tithi_num % 15 in (4, 9, 14) and tithi_num % 15 != 0)
        rikta = tithi_num % 15 in (4, 9, 14)
        score += -1.0 if tithi_bad else 0.5
        reasons.append({
            "factor": "tithi",
            "verdict": "unfavorable" if tithi_bad else "favorable",
            "detail": f"tithi {tithi_num} ({pan['tithi']['name']})"
            + (" — rikta class, avoided for auspicious starts" if rikta else ""),
            "source": "Muhurta tithi classes",
        })

        vara_ok = vara in (spec.get("varas") or [])
        score += 0.5 if vara_ok else -0.25
        reasons.append({
            "factor": "vara",
            "verdict": "favorable" if vara_ok else "neutral",
            "detail": f"{vara}" + ("" if vara_ok else f" (classical days for {key}: {', '.join(spec.get('varas') or [])})"),
            "source": "Muhurta vara tables",
        })

        nak_ok = day_nak in (spec.get("nakshatras") or [])
        score += 1.0 if nak_ok else -0.25
        reasons.append({
            "factor": "nakshatra",
            "verdict": "favorable" if nak_ok else "neutral",
            "detail": f"{day_nak}" + ("" if nak_ok else f" is not among the classical {key} nakshatras"),
            "source": "Muhurta electional nakshatra lists",
        })

        results.append({
            "date": d.isoformat(),
            "score": round(score, 2),
            "vara": vara,
            "vara_sanskrit": vara_sanskrit,
            "tithi": pan["tithi"]["name"],
            "nakshatra": day_nak,
            "tara": tara["name"],
            "favorable": score >= 1.5,
            "reasons": reasons,
        })

    ranked = sorted(results, key=lambda r: r["score"], reverse=True)
    return {
        "activity": key,
        "from": start.isoformat(),
        "days": days,
        "janma_nakshatra": NAKSHATRA_NAMES[janma_nak_idx],
        "note": (
            "Day-level screen using tara bala, chandra bala, tithi, vara and "
            "nakshatra. A full muhurta also fixes the lagna/hora for the exact "
            "moment — consult the Chart tools or a practitioner for that step."
            + (f" {spec.get('note')}" if spec.get("note") else "")
        ),
        "best": ranked[:7],
        "all": results,
    }
