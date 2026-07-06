"""Flatten engine payload into dotted-path facts for claim verification.

Key naming convention (stable contract for verify_claims):
- lagna.sign_name
- moon.sign_name, moon.nakshatra
- dasha.mahadasha_lord, dasha.antardasha_lord, dasha.mahadasha_start/end, ...
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

    path = engine_payload.get("dasha_path") or []
    for node in path:
        lvl = (node.get("level_name") or "").lower()
        if lvl == "mahadasha" or node.get("level") == 1:
            facts["dasha.mahadasha_lord"] = node.get("lord")
            facts["dasha.mahadasha_start"] = node.get("start")
            facts["dasha.mahadasha_end"] = node.get("end")
        elif lvl == "antardasha" or node.get("level") == 2:
            facts["dasha.antardasha_lord"] = node.get("lord")
            facts["dasha.antardasha_start"] = node.get("start")
            facts["dasha.antardasha_end"] = node.get("end")

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
