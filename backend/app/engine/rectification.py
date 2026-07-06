"""Event-based birth-time rectification.

Scans candidate birth times in +/- window at a fixed step; for each candidate
computes the lagna-dependent house lords and a 3-level Vimshottari tree, then
scores life events via dasha-lord relevance, pratyantardasha, event-date
transits, and ruling planets. Returns ranked candidates with per-event
substantiation plus overall confidence / tie diagnostics.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import constants as K
from .chart import build_chart
from .dashas import active_path, build_vimshottari
from .ephemeris import BirthData, EngineConfig
from .rectification_rules import (
    FULL_EVENT_MAX,
    get_rule,
    max_score_for_event,
    resolve_event_type,
)
from .transits import _house_from, transit_positions
from .vargas import d9, d10

# Scoring weights (additive per event)
WEIGHT_ANTARDASHA = 1.0
WEIGHT_MAHADASHA = 0.5
WEIGHT_PRATYANTARDASHA = 0.3
WEIGHT_TRANSIT = 0.2
WEIGHT_RULING_PLANET = 0.15

# Vaara (weekday) lords: Python weekday() Monday=0 .. Sunday=6
VAARA_LORDS = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]

DEATH_EVENT_TYPES = frozenset({"parent_death", "father_death", "mother_death"})


def _parse_event_date(ev: dict) -> datetime:
    d = ev["date"]
    if isinstance(d, str):
        if "T" in d:
            return datetime.fromisoformat(d)
        return datetime.fromisoformat(f"{d}T00:00:00")
    return d


def _relevant_lords(chart: dict, canonical_type: str) -> tuple[set[str], list[str]]:
    rule = get_rule(canonical_type)
    lords: set[str] = set()
    reasons: list[str] = []
    for h in rule.houses:
        lord = chart["house_lords"][h]["lord"]
        lords.add(lord)
        reasons.append(f"{lord} lords house {h}")
        if canonical_type in DEATH_EVENT_TYPES:
            eighth_from = (chart["houses"][h - 1]["sign"] + 7) % 12
            l8 = K.SIGN_LORDS[eighth_from]
            lords.add(l8)
            reasons.append(f"{l8} lords the 8th sign from house {h}")
    for kp in rule.karakas:
        lords.add(kp)
        reasons.append(f"{kp} is karaka for {canonical_type}")
    if rule.generic:
        reasons.append("generic event type — no specific house/karaka assignment")
    return lords, reasons


def _transit_corroboration(
    chart: dict,
    ev_dt_local: datetime,
    tz_offset: float,
    relevant_houses: set[int],
    config: EngineConfig,
) -> tuple[float, list[str]]:
    if not relevant_houses:
        return 0.0, []
    ev_utc = ev_dt_local - timedelta(hours=tz_offset)
    positions = transit_positions(ev_utc, config)
    lagna_sign = chart["lagna"]["sign"]
    score = 0.0
    matched: list[str] = []
    for planet in ("Saturn", "Jupiter"):
        transit_sign = positions[planet]["sign"]
        house = _house_from(transit_sign, lagna_sign)
        if house in relevant_houses:
            score += WEIGHT_TRANSIT
            matched.append(
                f"transiting {planet} in house {house} "
                f"({K.SIGN_NAMES[transit_sign]}) relevant to event houses"
            )
    return score, matched


def _ruling_planet_corroboration(
    ev_dt_local: datetime,
    tz_offset: float,
    relevant: set[str],
    config: EngineConfig,
) -> tuple[float, list[str]]:
    if not relevant:
        return 0.0, []
    score = 0.0
    matched: list[str] = []
    day_lord = VAARA_LORDS[ev_dt_local.weekday()]
    if day_lord in relevant:
        score += WEIGHT_RULING_PLANET
        matched.append(f"vaara lord {day_lord} relevant on {ev_dt_local.date().isoformat()}")
    ev_utc = ev_dt_local - timedelta(hours=tz_offset)
    positions = transit_positions(ev_utc, config)
    moon_lon = positions["Moon"]["longitude"]
    nak_index = int(moon_lon // K.NAKSHATRA_SPAN) % 27
    moon_nak_lord = K.NAKSHATRA_LORDS[nak_index]
    if moon_nak_lord in relevant:
        score += WEIGHT_RULING_PLANET
        matched.append(
            f"Moon nakshatra lord {moon_nak_lord} at event "
            f"({K.NAKSHATRA_NAMES[nak_index]}) relevant"
        )
    return score, matched


def _score_candidate(
    chart: dict,
    tree: dict,
    events: list[dict],
    tz_offset: float,
    config: EngineConfig,
) -> tuple[float, float, list[dict]]:
    score = 0.0
    max_score = 0.0
    details: list[dict] = []
    for ev in events:
        canonical = ev["_canonical_type"]
        ev_type_raw = ev.get("type", canonical)
        ev_dt = _parse_event_date(ev)
        relevant, reasons = _relevant_lords(chart, canonical)
        rule = get_rule(canonical)
        event_max = max_score_for_event(canonical)
        max_score += event_max

        path = active_path(tree, ev_dt)
        maha = path[0]["lord"] if len(path) > 0 else None
        antar = path[1]["lord"] if len(path) > 1 else None
        pratyantar = path[2]["lord"] if len(path) > 2 else None

        ev_score = 0.0
        matched: list[str] = []
        if antar in relevant:
            ev_score += WEIGHT_ANTARDASHA
            matched.append(f"antardasha lord {antar} relevant")
        if maha in relevant:
            ev_score += WEIGHT_MAHADASHA
            matched.append(f"mahadasha lord {maha} relevant")
        if pratyantar in relevant:
            ev_score += WEIGHT_PRATYANTARDASHA
            matched.append(f"pratyantardasha lord {pratyantar} relevant")

        transit_score, transit_matched = _transit_corroboration(
            chart, ev_dt, tz_offset, set(rule.houses), config,
        )
        ev_score += transit_score
        matched.extend(transit_matched)

        rp_score, rp_matched = _ruling_planet_corroboration(
            ev_dt, tz_offset, relevant, config,
        )
        ev_score += rp_score
        matched.extend(rp_matched)

        score += ev_score
        details.append({
            "event": ev_type_raw,
            "canonical_type": canonical,
            "generic": rule.generic,
            "date": ev_dt.date().isoformat(),
            "active_mahadasha": maha,
            "active_antardasha": antar,
            "active_pratyantardasha": pratyantar,
            "relevant_lords": sorted(relevant),
            "why_relevant": reasons,
            "matched": matched,
            "score": round(ev_score, 3),
            "max_score": round(event_max, 3),
        })
    return score, max_score, details


def _varga_boundary_offsets(
    candidates_meta: list[dict],
    step_minutes: int,
    proximity_minutes: int,
) -> tuple[set[int], set[int]]:
    """Return offset sets near D9 / D10 lagna sign boundaries within the scan."""
    d9_boundaries: set[int] = set()
    d10_boundaries: set[int] = set()
    for i in range(len(candidates_meta) - 1):
        cur, nxt = candidates_meta[i], candidates_meta[i + 1]
        if cur["d9_lagna"] != nxt["d9_lagna"]:
            d9_boundaries.add(cur["offset_minutes"])
            d9_boundaries.add(nxt["offset_minutes"])
        if cur["d10_lagna"] != nxt["d10_lagna"]:
            d10_boundaries.add(cur["offset_minutes"])
            d10_boundaries.add(nxt["offset_minutes"])

    def near_boundary(offset: int, boundaries: set[int]) -> bool:
        return any(abs(offset - b) <= proximity_minutes for b in boundaries)

    d9_near = {c["offset_minutes"] for c in candidates_meta
               if near_boundary(c["offset_minutes"], d9_boundaries)}
    d10_near = {c["offset_minutes"] for c in candidates_meta
                if near_boundary(c["offset_minutes"], d10_boundaries)}
    return d9_near, d10_near


def _compute_confidence(
    ranked: list[dict],
    tie_count: int,
) -> float:
    """Heuristic 0..1 confidence from top-vs-second gap and tie density.

    confidence = gap_ratio * tie_penalty, where gap_ratio is
    (top_score - second_score) / top_max_score (0 when tied at top or only one
    candidate), and tie_penalty = 1 / tie_count.
    """
    if not ranked:
        return 0.0
    top = ranked[0]
    top_max = top.get("max_score") or FULL_EVENT_MAX
    gap_ratio = 0.0
    if tie_count <= 1 and len(ranked) >= 2:
        gap = top["score"] - ranked[1]["score"]
        gap_ratio = max(0.0, gap / top_max) if top_max > 0 else 0.0
    tie_penalty = 1.0 / tie_count
    return round(min(1.0, gap_ratio * tie_penalty), 3)


def _sensitivity_to_step_note(ranked: list[dict], step_minutes: int, tie_count: int) -> dict:
    """Approximate whether halving step size could change the top candidate."""
    if not ranked:
        return {"likely_changes_top": False, "note": "no candidates scanned"}
    top_score = ranked[0]["score"]
    near_top = sum(1 for c in ranked if abs(c["score"] - top_score) < 1e-9)
    dense = near_top >= 3 or tie_count > 1
    varga_sensitive = any(
        c.get("varga_sensitivity", {}).get("near_d9_boundary")
        or c.get("varga_sensitivity", {}).get("near_d10_boundary")
        for c in ranked[:5]
    )
    likely = dense or (varga_sensitive and tie_count > 1)
    note = (
        f"{near_top} candidate(s) tied or within epsilon of top score at "
        f"{step_minutes}-minute steps"
    )
    if varga_sensitive:
        note += "; top candidates near D9/D10 lagna boundary"
    if likely:
        note += " — finer step may change ranking"
    return {"likely_changes_top": likely, "note": note}


def rectify(
    birth: BirthData,
    window_minutes: int,
    events: list[dict],
    config: EngineConfig | None = None,
    step_minutes: int = 2,
    top_n: int = 10,
) -> dict:
    config = config or EngineConfig()
    base_dt = birth.local_datetime()

    warnings: list[str] = []
    resolved_events: list[dict] = []
    ignored_event_count = 0
    for ev in events:
        raw_type = ev.get("type", "")
        canonical, ev_warnings = resolve_event_type(raw_type)
        if ev_warnings:
            warnings.extend(ev_warnings)
            ignored_event_count += 1
        resolved = dict(ev)
        resolved["_canonical_type"] = canonical
        resolved_events.append(resolved)

    proximity = step_minutes * 3
    candidates_meta: list[dict] = []
    candidates: list[dict] = []
    n_steps = int(window_minutes // step_minutes)

    for i in range(-n_steps, n_steps + 1):
        offset = i * step_minutes
        cand_dt = base_dt + timedelta(minutes=offset)
        cand_birth = BirthData(
            date=cand_dt.date().isoformat(),
            time=cand_dt.strftime("%H:%M:%S"),
            lat=birth.lat,
            lon=birth.lon,
            tz_offset=birth.tz_offset,
            place_name=birth.place_name,
        )
        chart = build_chart(cand_birth, config)
        lagna_lon = chart["lagna"]["longitude"]
        candidates_meta.append({
            "offset_minutes": offset,
            "d9_lagna": d9(lagna_lon),
            "d10_lagna": d10(lagna_lon),
        })

        tree = build_vimshottari(
            chart["planets"]["Moon"]["longitude"],
            cand_dt,
            config,
            levels=3,
        )
        score, max_score, details = _score_candidate(
            chart, tree, resolved_events, birth.tz_offset, config,
        )
        candidates.append({
            "time": cand_dt.strftime("%H:%M:%S"),
            "date": cand_dt.date().isoformat(),
            "offset_minutes": offset,
            "score": round(score, 3),
            "max_score": round(max_score, 3),
            "lagna_sign": chart["lagna"]["sign"],
            "lagna_sign_name": chart["lagna"]["sign_name"],
            "lagna_degree": chart["lagna"]["degree_in_sign"],
            "events": details,
            "_meta_index": len(candidates_meta) - 1,
        })

    d9_near, d10_near = _varga_boundary_offsets(candidates_meta, step_minutes, proximity)
    for cand in candidates:
        off = cand["offset_minutes"]
        cand["varga_sensitivity"] = {
            "near_d9_boundary": off in d9_near,
            "near_d10_boundary": off in d10_near,
            "proximity_minutes": proximity,
        }
        del cand["_meta_index"]

    ranked = sorted(candidates, key=lambda c: (-c["score"], abs(c["offset_minutes"])))
    top_score = ranked[0]["score"] if ranked else 0.0
    tie_count = sum(1 for c in ranked if abs(c["score"] - top_score) < 1e-9) if ranked else 0
    confidence = _compute_confidence(ranked, tie_count)
    step_sensitivity = _sensitivity_to_step_note(ranked, step_minutes, tie_count)

    return {
        "input_time": birth.time,
        "window_minutes": window_minutes,
        "step_minutes": step_minutes,
        "n_candidates": len(candidates),
        "candidates": ranked[:top_n],
        "warnings": warnings,
        "ignored_event_count": ignored_event_count,
        "confidence": confidence,
        "tie_count": tie_count,
        "sensitivity_to_step": step_sensitivity,
    }
