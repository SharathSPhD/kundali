"""Event-based birth-time rectification.

Scans candidate birth times in +/- window at a fixed step; for each candidate
computes the lagna-dependent house lords and the Vimshottari tree, then scores
how many life events fall in an antardasha (or mahadasha, half weight) of a
lord relevant to the event type. Returns ranked candidates with per-event
substantiation.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import constants as K
from .chart import build_chart
from .dashas import active_path, build_vimshottari
from .ephemeris import BirthData, EngineConfig

# event type -> (house numbers whose lords are relevant, extra karaka planets)
EVENT_RULES = {
    "marriage": ({7}, {"Venus"}),
    "child": ({5}, {"Jupiter"}),
    "childbirth": ({5}, {"Jupiter"}),
    "career": ({10}, {"Sun", "Saturn", "Mercury"}),
    "job": ({10}, {"Sun", "Saturn", "Mercury"}),
    "relocation": ({4, 12}, set()),
    "foreign_travel": ({9, 12}, set()),
    "education": ({4, 5, 9}, {"Mercury", "Jupiter"}),
    "parent_death": ({4, 9}, {"Sun", "Moon"}),
    "father_death": ({9}, {"Sun"}),
    "mother_death": ({4}, {"Moon"}),
    "accident": ({6, 8}, {"Mars", "Saturn"}),
    "health": ({6, 8}, {"Saturn"}),
}


def _relevant_lords(chart: dict, event_type: str) -> tuple[set, list[str]]:
    houses, karakas = EVENT_RULES.get(event_type, (set(), set()))
    lords = set()
    reasons = []
    for h in houses:
        lord = chart["house_lords"][h]["lord"]
        lords.add(lord)
        reasons.append(f"{lord} lords house {h}")
        # 8th-from-house activation for death-type events (maraka chain)
        if event_type in ("parent_death", "father_death", "mother_death"):
            eighth_from = (chart["houses"][h - 1]["sign"] + 7) % 12
            l8 = K.SIGN_LORDS[eighth_from]
            lords.add(l8)
            reasons.append(f"{l8} lords the 8th sign from house {h}")
    for kp in karakas:
        lords.add(kp)
        reasons.append(f"{kp} is karaka for {event_type}")
    return lords, reasons


def _score_candidate(chart: dict, tree: dict, events: list[dict]) -> tuple[float, list[dict]]:
    score = 0.0
    details = []
    for ev in events:
        ev_type = ev["type"]
        ev_dt = datetime.fromisoformat(ev["date"]) if isinstance(ev["date"], str) else ev["date"]
        relevant, reasons = _relevant_lords(chart, ev_type)
        path = active_path(tree, ev_dt)
        maha = path[0]["lord"] if len(path) > 0 else None
        antar = path[1]["lord"] if len(path) > 1 else None
        ev_score = 0.0
        matched = []
        if antar in relevant:
            ev_score += 1.0
            matched.append(f"antardasha lord {antar} relevant")
        if maha in relevant:
            ev_score += 0.5
            matched.append(f"mahadasha lord {maha} relevant")
        score += ev_score
        details.append({
            "event": ev_type,
            "date": ev_dt.date().isoformat(),
            "active_mahadasha": maha,
            "active_antardasha": antar,
            "relevant_lords": sorted(relevant),
            "why_relevant": reasons,
            "matched": matched,
            "score": ev_score,
        })
    return score, details


def rectify(birth: BirthData, window_minutes: int, events: list[dict],
            config: EngineConfig | None = None, step_minutes: int = 2,
            top_n: int = 10) -> dict:
    config = config or EngineConfig()
    base_dt = birth.local_datetime()
    candidates = []
    n_steps = int(window_minutes // step_minutes)
    for i in range(-n_steps, n_steps + 1):
        cand_dt = base_dt + timedelta(minutes=i * step_minutes)
        cand_birth = BirthData(
            date=cand_dt.date().isoformat(),
            time=cand_dt.strftime("%H:%M:%S"),
            lat=birth.lat, lon=birth.lon, tz_offset=birth.tz_offset,
            place_name=birth.place_name,
        )
        chart = build_chart(cand_birth, config)
        tree = build_vimshottari(chart["planets"]["Moon"]["longitude"],
                                 cand_dt, config, levels=2)
        score, details = _score_candidate(chart, tree, events)
        candidates.append({
            "time": cand_dt.strftime("%H:%M:%S"),
            "date": cand_dt.date().isoformat(),
            "offset_minutes": i * step_minutes,
            "score": round(score, 3),
            "max_score": round(1.5 * len(events), 3),
            "lagna_sign": chart["lagna"]["sign"],
            "lagna_sign_name": chart["lagna"]["sign_name"],
            "lagna_degree": chart["lagna"]["degree_in_sign"],
            "events": details,
        })

    ranked = sorted(candidates, key=lambda c: (-c["score"], abs(c["offset_minutes"])))
    return {
        "input_time": birth.time,
        "window_minutes": window_minutes,
        "step_minutes": step_minutes,
        "n_candidates": len(candidates),
        "candidates": ranked[:top_n],
    }
