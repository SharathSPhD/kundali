"""Flatten engine payload into dotted-path facts for claim verification.

Key naming convention (stable contract for verify_claims):
- lagna.sign_name
- moon.sign_name, moon.nakshatra
- dasha.mahadasha_lord, dasha.antardasha_lord, dasha.mahadasha_start/end, ...
  (also dasha.pratyantardasha_lord, dasha.sookshma_lord, dasha.prana_lord
  when the engine's dasha_path is deep enough to include them)
- dasha.active_lords — list of every lord active at any level right now
  (the set a "current dasha lord is X" claim should be checked against)
- areas.<area>.score, areas.<area>.favorability_label, areas.<area>.trend
- yogas.active — list of active yoga name strings
- shadbala.<planet>.total_rupas
- jaimini.karakas.<karaka> — planet name
- planets.<planet>.sign_name — natal placement
"""
from __future__ import annotations

from typing import Any


def export_facts(engine_payload: dict) -> dict[str, Any]:
    facts: dict[str, Any] = {}

    ctx = engine_payload.get("context") or {}
    if ctx.get("lagna"):
        facts["lagna.sign_name"] = ctx["lagna"].get("sign_name")
    moon = ctx.get("moon") or {}
    if moon:
        facts["moon.sign_name"] = moon.get("sign_name")
        facts["moon.nakshatra"] = moon.get("nakshatra")

    _DASHA_LEVEL_NAMES = ["mahadasha", "antardasha", "pratyantardasha", "sookshma", "prana"]
    path = engine_payload.get("dasha_path") or []
    active_lords: list[str] = []
    for node in path:
        level = node.get("level")
        lvl = (node.get("level_name") or "").lower()
        if not lvl and isinstance(level, int) and 1 <= level <= len(_DASHA_LEVEL_NAMES):
            lvl = _DASHA_LEVEL_NAMES[level - 1]
        if lvl not in _DASHA_LEVEL_NAMES:
            continue
        facts[f"dasha.{lvl}_lord"] = node.get("lord")
        facts[f"dasha.{lvl}_start"] = node.get("start")
        facts[f"dasha.{lvl}_end"] = node.get("end")
        if node.get("lord"):
            active_lords.append(node["lord"])
    facts["dasha.active_lords"] = active_lords

    for area in engine_payload.get("areas") or []:
        name = area.get("area")
        if not name:
            continue
        facts[f"areas.{name}.score"] = area.get("score")
        facts[f"areas.{name}.favorability_label"] = area.get("favorability_label")
        facts[f"areas.{name}.trend"] = area.get("trend")

    facts["yogas.active"] = list(ctx.get("active_yogas") or [])

    sb = engine_payload.get("shadbala", {}).get("planets") or {}
    for planet, row in sb.items():
        facts[f"shadbala.{planet}.total_rupas"] = row.get("total_rupas")

    jm = engine_payload.get("jaimini") or {}
    for k in jm.get("karakas") or []:
        facts[f"jaimini.karakas.{k['karaka']}"] = k.get("planet")

    chart = engine_payload.get("chart") or {}
    for planet, pos in (chart.get("planets") or {}).items():
        facts[f"planets.{planet}.sign_name"] = pos.get("sign_name")

    return facts
