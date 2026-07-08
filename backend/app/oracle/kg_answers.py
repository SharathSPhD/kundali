"""Knowledge-graph-backed deterministic question answering.

Replaces the regex-intent → canned-paragraph pipeline with genuine
reasoning over two sources of truth:

1. **The knowledge graph** (``knowledge/graph.py``) — the Vedic rule
   system: which houses/karakas govern an area, what a graha signifies,
   functional lordship for the chart's lagna, nakshatra lore — every edge
   carrying its classical source.
2. **The engine payload** — this chart's computed facts (positions,
   dignities, house lords, shadbala, dasha path, transit markers, scored
   life areas with substantiation).

An answer is a *derivation*: a chain of steps where each step binds a
graph rule (cited) to a chart fact (computed). The scored engine verdicts
remain authoritative for favorability; the graph explains *why* and adds
the interpretive layer (functional nature, karaka condition, timing
hooks). No LLM anywhere in this path.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from ..knowledge.graph import KnowledgeGraph, get_graph
from .intent import classify_intent
from . import answers as legacy_answers

_ORDINAL = {1: "1st", 2: "2nd", 3: "3rd"}


def _ord(n: int) -> str:
    return _ORDINAL.get(n, f"{n}th")


# --------------------------------------------------------------- questions

_TIMING_RE = re.compile(r"\b(when|which year|what year|how long|until|till|by when|timeline|time frame)\b", re.I)
_REMEDY_RE = re.compile(r"\b(remed(y|ies)|gemstone|gem|stone|mantra|upaya|donat(e|ion)|fast(ing)?|puja|worship|pacif)\b", re.I)
_STRENGTH_RE = re.compile(r"\b(strongest|weakest|how strong|how weak|strength of|shadbala)\b", re.I)
_MEANING_RE = re.compile(r"\b(what (is|does|about)|tell me about|meaning|means|explain|significance|signify)\b", re.I)


def _question_kind(question: str, entities: list, intent: str) -> str:
    if _REMEDY_RE.search(question):
        return "remedy"
    if _STRENGTH_RE.search(question):
        return "strength"
    has_area = any(n.kind == "area" for n in entities)
    has_thing = any(n.kind in ("graha", "bhava", "nakshatra", "rashi", "yoga") for n in entities)
    if _TIMING_RE.search(question) and (has_area or intent in legacy_answers._AREA_INTENTS):
        return "timing"
    # "Tell me about / what does X mean" about a concrete chart entity wins
    # over the broad area keywords ("7th house" would otherwise route to
    # the relationships area).
    if has_thing and _MEANING_RE.search(question):
        return "entity"
    if has_area or intent in legacy_answers._AREA_INTENTS:
        return "area"
    if has_thing and intent == "general":
        return "entity"
    if intent in ("dasha", "yogas", "transit", "shadbala", "jaimini", "rectification_help"):
        return intent
    if has_thing:
        return "entity"
    return "general"


# --------------------------------------------------------------- chart facts

def _planet(payload: dict, name: str) -> dict:
    return (payload.get("chart", {}).get("planets") or {}).get(name) or {}


def _house_lord(payload: dict, house: int) -> Optional[str]:
    lords = payload.get("chart", {}).get("house_lords") or {}
    entry = lords.get(house)
    if entry is None:
        entry = lords.get(str(house))
    if isinstance(entry, dict):
        return entry.get("lord")
    return entry


def _occupants(payload: dict, house: int) -> list[str]:
    return [
        name
        for name, p in (payload.get("chart", {}).get("planets") or {}).items()
        if p.get("house") == house
    ]


def _lagna_sign(payload: dict) -> str:
    return payload.get("context", {}).get("lagna", {}).get("sign_name") or \
        payload.get("chart", {}).get("lagna", {}).get("sign_name") or ""


def _area_row(payload: dict, area: str) -> Optional[dict]:
    for row in payload.get("areas") or []:
        if row.get("area") == area:
            return row
    return None


def _shadbala(payload: dict, planet: str) -> dict:
    return (payload.get("shadbala", {}).get("planets") or {}).get(planet) or {}


def _dasha_lords(payload: dict) -> list[dict]:
    return payload.get("dasha_path") or []


def _describe_placement(name: str, p: dict) -> str:
    bits = [f"{name} is in {p.get('sign_name', '?')}"]
    if p.get("house"):
        bits.append(f"in your {_ord(p['house'])} house")
    if p.get("nakshatra"):
        bits.append(f"({p['nakshatra']} nakshatra)")
    dignity = p.get("dignity")
    if dignity and dignity not in ("neutral",):
        bits.append(f"— {dignity}")
    if p.get("retrograde"):
        bits.append("retrograde")
    if p.get("combust"):
        bits.append("combust")
    return " ".join(bits)


_DIGNITY_QUALITY = {
    "exalted": "at its strongest expression",
    "moolatrikona": "very strong",
    "own": "strong and stable",
    "friend": "comfortable",
    "neutral": "middling",
    "enemy": "under strain",
    "debilitated": "at its weakest and needing support",
}


# --------------------------------------------------------------- derivation

class _Answer:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.citations: list[str] = []
        self.derivation: list[dict] = []

    def say(self, text: str) -> None:
        self.parts.append(text)

    def step(self, claim: str, rule: str, source: str, facts: Optional[list[str]] = None) -> None:
        self.derivation.append({
            "claim": claim, "rule": rule, "source": source, "facts": facts or [],
        })
        if source:
            self.citations.append(f"{rule} — {source}" if rule else source)

    def cite(self, c: str) -> None:
        self.citations.append(c)

    def packet(self, kind: str) -> dict:
        # De-dup citations, preserve order.
        seen: set[str] = set()
        cites = [c for c in self.citations if not (c in seen or seen.add(c))]
        return {
            "text": "\n\n".join(p for p in self.parts if p),
            "citations": cites,
            "derivation": self.derivation,
            "answer_kind": kind,
        }


# --------------------------------------------------------------- area answers

def _dasha_connection(
    kg: KnowledgeGraph, payload: dict, houses: list[int], karakas: list[str], ans: _Answer
) -> None:
    lords = {h: _house_lord(payload, h) for h in houses}
    occupants = {h: _occupants(payload, h) for h in houses}
    relevant = set(filter(None, lords.values())) | set(karakas)
    for h, occ in occupants.items():
        relevant |= set(occ)
    for node in _dasha_lords(payload):
        lord = node.get("lord")
        level = node.get("level_name") or node.get("level")
        if lord in relevant:
            roles = []
            for h, l in lords.items():
                if l == lord:
                    roles.append(f"lord of your {_ord(h)} house")
            if lord in karakas:
                roles.append("the natural karaka for this area")
            for h, occ in occupants.items():
                if lord in occ:
                    roles.append(f"placed in your {_ord(h)} house")
            span = f"{node.get('start', '')[:10]} to {node.get('end', '')[:10]}"
            ans.say(
                f"Timing: your current {level} lord {lord} is {', and '.join(roles)} — "
                f"this period directly activates the area ({span})."
            )
            ans.step(
                claim=f"{level} of {lord} activates this area",
                rule="a dasha lord gives results of the houses it rules, occupies and signifies",
                source="BPHS dasha-phala principles",
                facts=[f"{level}: {lord} [{span}]"] + roles,
            )


def _area_answer(kg: KnowledgeGraph, area_name: str, payload: dict, timing: bool) -> dict:
    ans = _Answer()
    node = kg.node(f"area:{area_name}")
    if node is None:
        return legacy_answers.build_answer_packet(area_name, payload, "")
    attrs = node.attrs
    primary = list(attrs.get("primary_houses") or [])
    supporting = list(attrs.get("supporting_houses") or [])
    karakas = list(attrs.get("karakas") or [])
    lagna = _lagna_sign(payload)

    row = _area_row(payload, area_name)
    if row:
        label = row.get("favorability_label") or ""
        ans.say(
            f"Overall, {area_name} indications are {label} right now "
            f"(engine score {row.get('score', 0):+.2f}, trend: {row.get('trend', 'stable')})."
        )
        ans.cite(f"area: {area_name} score {row.get('score', 0):+.2f} trend {row.get('trend')}")

    houses_txt = " and ".join(_ord(h) for h in primary)
    ans.step(
        claim=f"{area_name} is judged from the {houses_txt} house(s), with {', '.join(karakas)} as karaka",
        rule=f"{houses_txt} house governs {area_name}; supporting houses {supporting}",
        source=str(attrs.get("source", "")),
        facts=[],
    )

    for h in primary:
        lord = _house_lord(payload, h)
        if not lord:
            continue
        p = _planet(payload, lord)
        quality = _DIGNITY_QUALITY.get(p.get("dignity", ""), "")
        fn = kg.functional_nature(lord, lagna)
        fn_txt = f" As {fn['verdict']} for your {lagna} lagna, its influence here matters." if fn.get("verdict") not in ("unknown", "neutral", "nodal") else ""
        ans.say(
            f"The {_ord(h)} lord {lord} sits in your {_ord(p.get('house', 0))} house in "
            f"{p.get('sign_name', '?')} ({p.get('dignity', 'neutral')} dignity"
            + (", retrograde" if p.get("retrograde") else "")
            + (", combust" if p.get("combust") else "")
            + f") — {quality or 'a middling condition'}.{fn_txt}"
        )
        ans.step(
            claim=f"{_ord(h)} lord {lord} condition shapes {area_name}",
            rule="the house lord's placement and dignity carry the house's promise",
            source="BPHS judgement of houses; ch. 34 lordship principles",
            facts=[
                _describe_placement(lord, p),
                f"functional nature for {lagna} lagna: {fn.get('verdict')}"
                + (f" ({'; '.join(fn.get('reasons') or [])})" if fn.get("reasons") else ""),
            ],
        )
        occ = _occupants(payload, h)
        if occ:
            occ_txt = ", ".join(f"{o} ({_planet(payload, o).get('dignity', 'neutral')})" for o in occ)
            ans.say(f"Your {_ord(h)} house itself holds {occ_txt}.")
            ans.step(
                claim=f"occupants of the {_ord(h)} house color {area_name}",
                rule="planets in a house directly modify its results",
                source="BPHS judgement of houses",
                facts=[f"house {h}: {occ_txt}"],
            )

    for k in karakas:
        p = _planet(payload, k)
        if not p:
            continue
        sb = _shadbala(payload, k)
        sb_txt = ""
        if sb:
            verdict = "carries sufficient strength" if sb.get("sufficient") else "is below its required strength"
            sb_txt = f" In shadbala it {verdict} ({sb.get('total_rupas', 0):.2f} of {sb.get('required_rupas', 0):.1f} rupas required)."
        ans.say(f"The karaka {k}: {_describe_placement(k, p)}.{sb_txt}")
        ans.step(
            claim=f"karaka {k} condition underwrites {area_name}",
            rule=f"{k} is the natural significator here",
            source=str(attrs.get("source", "")),
            facts=[_describe_placement(k, p)] + ([f"shadbala {sb.get('total_rupas', 0):.2f}/{sb.get('required_rupas', 0):.1f} rupas"] if sb else []),
        )

    _dasha_connection(kg, payload, primary + supporting, karakas, ans)

    if timing and row:
        windows = row.get("windows") or []
        if windows:
            w_txt = "; ".join(
                f"{w.get('from', '')[:10]} → {w.get('to', '')[:10]} ({w.get('why', '')})"
                for w in windows[:3]
            )
            ans.say(f"Favorable/operative windows the engine computed for {area_name}: {w_txt}.")
            ans.cite(f"windows: {w_txt}")
        else:
            ans.say(
                f"No distinct {area_name} window stands out in the current dasha span; "
                "the general indications above apply across the running periods."
            )

    varga = attrs.get("varga")
    if varga:
        ans.say(
            f"For a deeper look a jyotishi would corroborate this in the {varga} divisional chart "
            f"({attrs.get('varga_reason', '')}) — see the Chart page's varga selector."
        )
    return ans.packet("area")


# --------------------------------------------------------------- entity answers

def _graha_answer(kg: KnowledgeGraph, node: Any, payload: dict) -> dict:
    ans = _Answer()
    name = node.name
    p = _planet(payload, name)
    lagna = _lagna_sign(payload)
    karakas = node.attrs.get("karaka_of") or []
    if p:
        ans.say(f"In your chart: {_describe_placement(name, p)}.")
        quality = _DIGNITY_QUALITY.get(p.get("dignity", ""), "")
        if quality:
            ans.say(f"That dignity means {name} is {quality} here.")
        ans.step(
            claim=f"{name}'s condition in this chart",
            rule="sign, house, nakshatra and dignity set a graha's capacity to deliver",
            source="BPHS graha placement principles",
            facts=[_describe_placement(name, p)],
        )
        nak = p.get("nakshatra")
        nak_node = kg.node(f"nakshatra:{nak}") if nak else None
        if nak_node:
            a = nak_node.attrs
            ans.say(
                f"Its nakshatra {nak} (ruled by {a.get('lord')}, deity {a.get('deity')}) carries "
                f"the flavor of {a.get('nature', '')}."
            )
            ans.step(
                claim=f"{name} expresses through {nak}",
                rule=f"{nak}: symbol {a.get('symbol')}, gana {a.get('gana')}, motivation {a.get('motivation')}",
                source=str(a.get("source", "")),
                facts=[f"{name} at {p.get('degree_in_sign', 0):.1f}° {p.get('sign_name')}, pada {p.get('pada')}"],
            )
    if karakas:
        ans.say(f"{name} is the natural karaka (significator) of: {', '.join(map(str, karakas[:7]))}.")
        ans.step(
            claim=f"what {name} signifies",
            rule=f"karaka of {', '.join(map(str, karakas))}",
            source=str(node.attrs.get("karaka_source", "")),
        )
    fn = kg.functional_nature(name, lagna)
    if fn.get("verdict") not in ("unknown",):
        ruled = fn.get("houses_ruled") or []
        ruled_txt = f" It rules your {' and '.join(_ord(h) for h in ruled)} house(s)." if ruled else ""
        ans.say(f"For your {lagna} lagna, {name} acts as a {fn['verdict']}.{ruled_txt}")
        ans.step(
            claim=f"{name} is {fn['verdict']} for {lagna} lagna",
            rule="; ".join(fn.get("reasons") or []) or "nodal — results per dispositor and conjunctions",
            source=str(fn.get("source", "")),
        )
    sb = _shadbala(payload, name)
    if sb:
        verdict = "sufficient" if sb.get("sufficient") else "below required"
        ans.say(
            f"Shadbala: {sb.get('total_rupas', 0):.2f} rupas against {sb.get('required_rupas', 0):.1f} "
            f"required — {verdict}."
        )
        ans.cite(f"shadbala: {name} {sb.get('total_rupas', 0):.2f} rupas ({verdict})")
    for dn in _dasha_lords(payload):
        if dn.get("lord") == name:
            ans.say(
                f"Note: you are currently running {name}'s {dn.get('level_name')} "
                f"({dn.get('start', '')[:10]} to {dn.get('end', '')[:10]}), so these themes are live right now."
            )
            ans.cite(f"dasha: {name} {dn.get('level_name')}")
            break
    return ans.packet("entity")


def _bhava_answer(kg: KnowledgeGraph, node: Any, payload: dict) -> dict:
    ans = _Answer()
    h = int(node.name)
    attrs = node.attrs
    sig = ", ".join(map(str, attrs.get("significations") or []))
    ans.say(f"The {_ord(h)} house ({attrs.get('sanskrit')}) governs: {sig}.")
    ans.step(
        claim=f"what the {_ord(h)} house means",
        rule=f"significations: {sig}",
        source=str(attrs.get("source", "")),
    )
    lord = _house_lord(payload, h)
    if lord:
        p = _planet(payload, lord)
        ans.say(f"In your chart its lord is {lord}: {_describe_placement(lord, p)}.")
        ans.step(
            claim=f"{_ord(h)} lord condition",
            rule="the house lord's placement carries the house's promise",
            source="BPHS judgement of houses",
            facts=[_describe_placement(lord, p)],
        )
    occ = _occupants(payload, h)
    if occ:
        ans.say("Occupants: " + ", ".join(f"{o} ({_planet(payload, o).get('dignity', 'neutral')})" for o in occ) + ".")
    else:
        ans.say("No planet occupies this house; its lord's condition dominates.")
    return ans.packet("entity")


def _nakshatra_answer(kg: KnowledgeGraph, node: Any, payload: dict) -> dict:
    ans = _Answer()
    a = node.attrs
    ans.say(
        f"{node.name}: ruled by {a.get('lord')}, deity {a.get('deity')}, symbol {a.get('symbol')}; "
        f"gana {a.get('gana')}, motivation {a.get('motivation')}. Its nature: {a.get('nature', '')}."
    )
    ans.step(
        claim=f"{node.name} lore",
        rule=f"deity {a.get('deity')}, symbol {a.get('symbol')}, gana {a.get('gana')}",
        source=str(a.get("source", "")),
    )
    for pname, p in (payload.get("chart", {}).get("planets") or {}).items():
        if p.get("nakshatra") == node.name:
            ans.say(f"Your {pname} occupies {node.name}" + (" — this is your janma nakshatra." if pname == "Moon" else "."))
            ans.cite(f"{pname} in {node.name}")
    return ans.packet("entity")


def _yoga_answer(kg: KnowledgeGraph, node: Any, payload: dict) -> dict:
    ans = _Answer()
    a = node.attrs
    active = node.name in (payload.get("context", {}).get("active_yogas") or [])
    ans.say(
        f"{node.name} ({a.get('sanskrit_category', '')}): {a.get('rule_description', '')} "
        + (f"Effects: {a.get('effects')}" if a.get("effects") else "")
    )
    ans.say("This yoga IS present in your chart." if active else "This yoga is not active in your chart.")
    ans.step(
        claim=f"{node.name} {'present' if active else 'absent'} in this chart",
        rule=str(a.get("rule_description", "")),
        source=str(a.get("source", "")),
    )
    return ans.packet("entity")


# --------------------------------------------------------------- other kinds

def _remedy_answer(kg: KnowledgeGraph, entities: list, payload: dict) -> dict:
    ans = _Answer()
    target: Optional[str] = next((n.name for n in entities if n.kind == "graha"), None)
    reason = ""
    if target is None:
        # Weakest classical planet by shadbala ratio, preferring insufficient.
        planets = payload.get("shadbala", {}).get("planets") or {}
        if planets:
            weakest = min(planets.items(), key=lambda kv: kv[1].get("ratio", 9.9))
            target = weakest[0]
            ratio = weakest[1].get("ratio")
            reason = (
                f"Chosen because {target} has the lowest shadbala ratio in your chart ({ratio})"
                + ("" if weakest[1].get("sufficient") else " and is below its required strength")
                + "."
            )
    if target is None:
        ans.say("No graha could be identified to suggest remedies for.")
        return ans.packet("remedy")
    node = kg.node(f"graha:{target}")
    rem = (node.attrs.get("remedies") or {}) if node else {}
    if reason:
        ans.say(reason)
    p = _planet(payload, target)
    if p:
        ans.say(f"Context: {_describe_placement(target, p)}.")
    lines = []
    for label, key in (("Gemstone", "gemstone"), ("Mantra", "mantra"), ("Charity (dana)", "dana"), ("Fast day", "fast_day")):
        if rem.get(key):
            lines.append(f"{label}: {rem[key]}")
    if lines:
        ans.say(f"Classical remedial attributions for {target} — " + "; ".join(lines) + ".")
        ans.step(
            claim=f"remedies attributed to {target}",
            rule="; ".join(lines),
            source=str(rem.get("source", "")),
            facts=[_describe_placement(target, p)] if p else [],
        )
        ans.say(
            "These are the traditional textual attributions, offered for reference — "
            "not medical, financial or psychological advice, and no outcome is guaranteed."
        )
    else:
        ans.say(f"No remedial attributions are cataloged for {target}.")
    return ans.packet("remedy")


def _strength_answer(payload: dict) -> dict:
    ans = _Answer()
    planets = payload.get("shadbala", {}).get("planets") or {}
    if not planets:
        ans.say("Shadbala data is not available for this chart.")
        return ans.packet("strength")
    ranked = sorted(planets.items(), key=lambda kv: kv[1].get("ratio", 0), reverse=True)
    strongest, s_row = ranked[0]
    weakest, w_row = ranked[-1]
    ans.say(
        f"By shadbala (six-fold strength), your strongest planet is {strongest} "
        f"({s_row.get('total_rupas', 0):.2f} rupas, {s_row.get('ratio', 0):.2f}× its requirement) and the "
        f"weakest is {weakest} ({w_row.get('total_rupas', 0):.2f} rupas, {w_row.get('ratio', 0):.2f}×)."
    )
    table = "; ".join(
        f"{name} {row.get('total_rupas', 0):.2f}r ({'ok' if row.get('sufficient') else 'low'})"
        for name, row in ranked
    )
    ans.say(f"Full ranking: {table}.")
    ans.step(
        claim="planetary strength ranking",
        rule="shadbala compares each graha's six-fold strength to its required threshold",
        source="BPHS shadbala chapters (Raman convention)",
        facts=[table],
    )
    return ans.packet("strength")


# --------------------------------------------------------------- entrypoint

def answer_question(question: str, payload: dict) -> dict:
    """Best-effort deterministic answer with derivation chain. Always returns
    a packet; falls back to the legacy intent packets for kinds the graph
    doesn't improve on (dasha listing, transit report, jaimini...)."""
    kg = get_graph()
    q = (question or "").strip()
    entities = kg.find_entities(q)
    intent = classify_intent(q)["intent"]
    kind = _question_kind(q, entities, intent)

    if kind == "area" or kind == "timing":
        area_node = next((n for n in entities if n.kind == "area"), None)
        area_name = area_node.name if area_node else (intent if intent in legacy_answers._AREA_INTENTS else None)
        if area_name:
            return _area_answer(kg, area_name, payload, timing=(kind == "timing"))
    if kind == "entity" and entities:
        node = next((n for n in entities if n.kind in ("graha", "bhava", "nakshatra", "rashi", "yoga")), None)
        if node is not None:
            if node.kind == "graha":
                return _graha_answer(kg, node, payload)
            if node.kind == "bhava":
                return _bhava_answer(kg, node, payload)
            if node.kind == "nakshatra":
                return _nakshatra_answer(kg, node, payload)
            if node.kind == "yoga":
                return _yoga_answer(kg, node, payload)
            if node.kind == "rashi":
                # Answer via the graha ruling it + who is placed there.
                lord = node.attrs.get("lord")
                ans = _Answer()
                ans.say(
                    f"{node.name} ({node.attrs.get('sanskrit')}) is a {node.attrs.get('tattva')} sign, "
                    f"{node.attrs.get('mobility')} in quality, ruled by {lord}."
                )
                ans.step(
                    claim=f"{node.name} characteristics",
                    rule=f"tattva {node.attrs.get('tattva')}, mobility {node.attrs.get('mobility')}, lord {lord}",
                    source=str(node.attrs.get("source", "")),
                )
                placed = [
                    pname for pname, p in (payload.get("chart", {}).get("planets") or {}).items()
                    if p.get("sign_name") == node.name
                ]
                if placed:
                    ans.say(f"In your chart, {', '.join(placed)} occupy {node.name}.")
                return ans.packet("entity")
    if kind == "remedy":
        return _remedy_answer(kg, entities, payload)
    if kind == "strength":
        return _strength_answer(payload)

    # Legacy packets for the remaining kinds (already well-grounded).
    packet = legacy_answers.build_answer_packet(intent, payload, q)
    packet.setdefault("derivation", [])
    packet.setdefault("answer_kind", intent)
    return packet
