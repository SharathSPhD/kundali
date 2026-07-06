"""Deterministic answer packets keyed by classified intent."""
from __future__ import annotations

from typing import Any

from ..engine.scoring_labels import favorability_label
from ..interpretation.template_provider import _TREND_PHRASE
from ..knowledge.registry import area_info, yoga_info

_AREA_INTENTS = frozenset({
    "health", "wealth", "career", "relationships", "family", "education",
})


def _area_entry(payload: dict, area: str) -> dict | None:
    for row in payload.get("areas", []):
        if row.get("area") == area:
            return row
    return None


def _format_substantiation(facts: list[dict], limit: int = 3) -> str:
    lines = []
    for f in facts[:limit]:
        if f.get("type") == "dasha_lord_natal_role":
            lines.append(
                f"{f.get('lord')} ({f.get('level')}) {f.get('role')} "
                f"[{f.get('dignity')}] Δ{f.get('delta', 0):+.3f}"
            )
        elif f.get("type") == "sade_sati":
            lines.append(f"Sade Sati {f.get('phase')} Δ{f.get('delta', 0):+.3f}")
        elif f.get("type") == "double_transit":
            lines.append(f"Double transit on house {f.get('house')}")
        else:
            lines.append(str(f.get("type", "fact")))
    return "; ".join(lines)


def _generic_summary(payload: dict) -> tuple[str, list[str]]:
    """Short fallback summary (subset of TemplateProvider narrative)."""
    paragraphs: list[str] = []
    citations: list[str] = []

    path = payload.get("dasha_path", [])
    if path:
        lords = " – ".join(n["lord"] for n in path)
        deepest = path[-1]
        paragraphs.append(
            f"The operative planetary period is {lords} "
            f"(active {deepest['start'][:10]} to {deepest['end'][:10]})."
        )
        citations.append(
            f"dasha: {lords} [{deepest['start'][:10]}..{deepest['end'][:10]}]"
        )

    ctx = payload.get("context", {})
    if ctx.get("lagna"):
        paragraphs.append(
            f"The chart rises in {ctx['lagna']['sign_name']} with the Moon in "
            f"{ctx['moon']['sign_name']} ({ctx['moon']['nakshatra']} nakshatra)."
        )
        citations.append(f"lagna: {ctx['lagna']['sign_name']}")
        citations.append(f"moon: {ctx['moon']['sign_name']} / {ctx['moon']['nakshatra']}")

    for area in payload.get("areas", [])[:3]:
        label = area.get("favorability_label") or favorability_label(area["score"])
        paragraphs.append(
            f"{area['area'].capitalize()}: {label} "
            f"(score {area['score']:+.2f}); "
            f"{_TREND_PHRASE.get(area['trend'], area['trend'])}."
        )
        citations.append(
            f"area: {area['area']} score {area['score']:+.2f} trend {area['trend']}"
        )

    return "\n\n".join(paragraphs), citations


def build_answer_packet(intent: str, engine_payload: dict, question: str) -> dict:
    """Compose a cited deterministic answer for the given intent."""
    citations: list[str] = []
    parts: list[str] = []

    if intent == "dasha":
        path = engine_payload.get("dasha_path", [])
        if path:
            lords = " – ".join(n["lord"] for n in path)
            deepest = path[-1]
            parts.append(
                f"Your current daśā sequence is {lords}. "
                f"The deepest active level is {deepest['level_name']} of "
                f"{deepest['lord']}, running {deepest['start'][:10]} to "
                f"{deepest['end'][:10]}."
            )
            citations.append(
                f"dasha: {lords} [{deepest['start'][:10]}..{deepest['end'][:10]}]"
            )
        else:
            parts.append("No active daśā path was computed for this date.")

    elif intent == "yogas":
        yg = engine_payload.get("context", {}).get("active_yogas") or []
        if yg:
            parts.append("Active natal yogas in this chart: " + ", ".join(yg) + ".")
            for y in yg:
                info = yoga_info(y)
                if info:
                    parts.append(f"{y}: {info['rule_description']} (source: {info['source']}).")
                    citations.append(f"yoga: {y} — {info['source']}")
                else:
                    citations.append(f"yoga: {y}")
        else:
            parts.append("No evaluated yogas are presently active in this chart.")

    elif intent in _AREA_INTENTS:
        area = _area_entry(engine_payload, intent)
        if area:
            label = area.get("favorability_label") or favorability_label(area["score"])
            subst = area.get("substantiation") or []
            fact_txt = _format_substantiation(subst)
            parts.append(
                f"{intent.capitalize()} indications are {label} "
                f"(score {area['score']:+.2f}, trend {area['trend']})."
            )
            if fact_txt:
                parts.append(f"Key engine facts: {fact_txt}.")
            info = area_info(intent)
            if info:
                parts.append(f"Governing houses per {info['source']}.")
            citations.append(
                f"area: {area['area']} score {area['score']:+.2f} trend {area['trend']}"
                + (f" — {info['source']}" if info else "")
            )
        else:
            parts.append(f"No {intent} area data is available in the engine payload.")

    elif intent == "transit":
        ctx = engine_payload.get("context", {})
        ss = ctx.get("sade_sati") or {}
        if ss.get("active"):
            span = ""
            if ss.get("start") and ss.get("end"):
                span = f" ({ss['start'][:10]} to {ss['end'][:10]})"
            parts.append(
                f"Sade Sati is active in its {ss['phase']} phase{span}."
            )
            citations.append(f"transit: Sade Sati {ss['phase']}")
        dt = ctx.get("double_transit") or []
        if dt:
            houses = ", ".join(str(h["house"]) for h in dt)
            parts.append(
                f"Jupiter and Saturn jointly influence house(s) {houses} by transit."
            )
            citations.append(f"transit: double transit on houses {houses}")
        if not parts:
            parts.append("No major transit markers (Sade Sati / double transit) are active now.")

    elif intent == "shadbala":
        sb = engine_payload.get("shadbala", {}).get("planets", {})
        if sb:
            summaries = []
            for planet, row in sb.items():
                rupas = row.get("total_rupas")
                ratio = row.get("ratio")
                verdict = "sufficient" if row.get("sufficient") else "below required"
                rupas_txt = f"{rupas:.2f}" if isinstance(rupas, (int, float)) else "unknown"
                summaries.append(f"{planet}: {rupas_txt} rupas ({verdict}, ratio {ratio})")
                citations.append(f"shadbala: {planet} {rupas_txt} rupas")
            parts.append("Planetary strength (Shadbala): " + "; ".join(summaries) + ".")
        else:
            parts.append("Shadbala data is not available in the engine payload.")

    elif intent == "jaimini":
        jm = engine_payload.get("jaimini", {})
        karakas = jm.get("karakas") or []
        active = jm.get("active") or []
        if karakas:
            ktxt = ", ".join(f"{k['karaka']}={k['planet']}" for k in karakas[:4])
            parts.append(f"Chara kārakas include {ktxt}.")
            for k in karakas:
                citations.append(f"jaimini: {k['karaka']} {k['planet']}")
        if active:
            maha = active[0]
            parts.append(
                f"Active Chara daśā: {maha['sign_name']} {maha['level_name']} "
                f"({maha['start'][:10]} to {maha['end'][:10]})."
            )
            citations.append(f"jaimini: chara {maha['sign_name']} {maha['level_name']}")
        if not parts:
            parts.append("Jaimini data is not available for this chart.")

    elif intent == "rectification_help":
        parts.append(
            "Birth-time rectification is not performed in chat. "
            "Use the Rectify flow (/dashboard/rectify) to compare life events "
            "against candidate birth times and review confidence diagnostics."
        )

    else:
        text, cites = _generic_summary(engine_payload)
        parts.append(text or "No grounded chart facts are available.")
        citations.extend(cites)

    if question and intent != "rectification_help":
        q = question.strip().rstrip("?")
        parts.insert(0, f"Regarding your question about {q}:")

    return {
        "text": " ".join(parts),
        "citations": citations,
    }
