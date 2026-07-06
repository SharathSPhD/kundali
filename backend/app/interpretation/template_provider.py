"""Deterministic template provider — composes readable English paragraphs
from the predictions payload with zero LLM involvement. Default provider."""
from __future__ import annotations

from typing import Any, Optional

from .base import InterpretationProvider

_TREND_PHRASE = {
    "improving": "conditions are supportive and improving",
    "stable": "conditions are broadly stable",
    "challenging": "conditions call for patience and care",
}


def _score_phrase(score: float) -> str:
    if score >= 0.5:
        return "strongly favourable"
    if score >= 0.15:
        return "moderately favourable"
    if score > -0.15:
        return "mixed"
    if score > -0.5:
        return "somewhat strained"
    return "notably strained"


class TemplateProvider(InterpretationProvider):
    name = "template"

    def interpret(self, engine_payload: dict[str, Any],
                  question: Optional[str] = None,
                  history: Optional[list[dict]] = None) -> dict:
        paragraphs = []
        citations = []

        path = engine_payload.get("dasha_path", [])
        if path:
            lords = " – ".join(n["lord"] for n in path)
            deepest = path[-1]
            para = (
                f"The operative planetary period is {lords} "
                f"(active {deepest['start'][:10]} to {deepest['end'][:10]})."
            )
            paragraphs.append(para)
            citations.append(f"dasha: {lords} [{deepest['start'][:10]}..{deepest['end'][:10]}]")

        ctx = engine_payload.get("context", {})
        if ctx.get("lagna"):
            paragraphs.append(
                f"The chart rises in {ctx['lagna']['sign_name']} with the Moon in "
                f"{ctx['moon']['sign_name']} ({ctx['moon']['nakshatra']} nakshatra)."
            )
            citations.append(f"lagna: {ctx['lagna']['sign_name']}")
            citations.append(f"moon: {ctx['moon']['sign_name']} / {ctx['moon']['nakshatra']}")

        ss = ctx.get("sade_sati") or {}
        if ss.get("active"):
            span = ""
            if ss.get("start") and ss.get("end"):
                span = f" (approximately {ss['start'][:10]} to {ss['end'][:10]})"
            paragraphs.append(
                f"Saturn's Sade Sati is currently active in its {ss['phase']}{span}; "
                "this classically asks for discipline, endurance and realistic pacing."
            )
            citations.append(f"transit: Sade Sati {ss['phase']}")

        dt = ctx.get("double_transit") or []
        if dt:
            houses = ", ".join(str(h["house"]) for h in dt)
            paragraphs.append(
                f"Jupiter and Saturn jointly influence house(s) {houses} by transit — "
                "a classical marker of concrete developments in those life areas."
            )
            citations.append(f"transit: double transit on houses {houses}")

        yg = ctx.get("active_yogas") or []
        if yg:
            paragraphs.append("Natal yogas active in this chart: " + ", ".join(yg) + ".")
            citations.extend(f"yoga: {y}" for y in yg)

        for area in engine_payload.get("areas", []):
            windows = area.get("windows") or []
            wtxt = ""
            if windows:
                w = windows[0]
                wtxt = f" The nearest operative window is {w['from'][:10]} to {w['to'][:10]} ({w['why']})."
            paragraphs.append(
                f"{area['area'].capitalize()}: the indications are "
                f"{_score_phrase(area['score'])} (score {area['score']:+.2f}); "
                f"{_TREND_PHRASE.get(area['trend'], area['trend'])}.{wtxt}"
            )
            citations.append(f"area: {area['area']} score {area['score']:+.2f} trend {area['trend']}")

        if question:
            paragraphs.append(
                "Regarding your question: the deterministic engine does not answer "
                "free-form questions; the indications above are the grounded facts "
                "available. Configure an LLM provider for narrative Q&A."
            )

        return {
            "text": "\n\n".join(paragraphs),
            "citations": citations,
            "provider": self.name,
        }
