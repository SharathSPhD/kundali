"""The Vedic-rule knowledge graph.

Loads the YAML catalogs under ``graph_data/`` into a typed in-memory graph:

- **Nodes** — grahas, rashis, bhavas, nakshatras, life areas and yogas,
  each with aliases (English + Sanskrit) for entity extraction and a
  textual ``source`` for provenance.
- **Edges** — typed relations (``rules``, ``exalted_in``, ``karaka_for``,
  ``governed_by`` …), each carrying the classical source they derive from.

The graph is deliberately embedded (no external DB): the rule system is
versioned data, identical for every user, and must be available inside a
serverless function with zero configuration. Everything downstream —
deterministic Q&A (``oracle/kg_answers.py``), the knowledge-explorer API,
LLM grounding — reads from this one structure.

Functional benefic/malefic status is *derived* (``functional_nature``)
from BPHS ch. 34 principles rather than hand-encoded per lagna, so every
verdict can cite the rule that produced it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

_DATA_DIR = Path(__file__).resolve().parent / "graph_data"
_RULES_DIR = Path(__file__).resolve().parent / "rules"

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}
DUSTHANA = {6, 8, 12}
TRISHADAYA = {3, 6, 11}
MARAKA_HOUSES = {2, 7}


@dataclass
class Node:
    id: str            # e.g. "graha:Saturn", "bhava:10", "area:career"
    kind: str          # graha | rashi | bhava | nakshatra | area | yoga
    name: str          # display name ("Saturn", "10", "career")
    attrs: dict[str, Any] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)


@dataclass
class Edge:
    src: str
    rel: str
    dst: str
    attrs: dict[str, Any] = field(default_factory=dict)

    @property
    def source(self) -> str:
        return str(self.attrs.get("source", ""))


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self._out: dict[str, list[Edge]] = {}
        self._in: dict[str, list[Edge]] = {}
        self._alias_index: dict[str, str] = {}
        self._load()

    # ------------------------------------------------------------- loading

    def _add_node(self, node: Node) -> None:
        self.nodes[node.id] = node
        for alias in [node.name, *node.aliases]:
            key = str(alias).strip().lower()
            if key and key not in self._alias_index:
                self._alias_index[key] = node.id

    def _add_edge(self, src: str, rel: str, dst: str, **attrs: Any) -> None:
        edge = Edge(src=src, rel=rel, dst=dst, attrs=attrs)
        self.edges.append(edge)
        self._out.setdefault(src, []).append(edge)
        self._in.setdefault(dst, []).append(edge)

    @staticmethod
    def _load_yaml(directory: Path, name: str) -> dict:
        path = directory / f"{name}.yaml"
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    def _load(self) -> None:
        rashis = self._load_yaml(_DATA_DIR, "rashis")
        rashi_source = rashis.get("source", "")
        for name, spec in (rashis.get("rashis") or {}).items():
            self._add_node(Node(
                id=f"rashi:{name}", kind="rashi", name=name,
                attrs={**spec, "source": rashi_source},
                aliases=[spec.get("sanskrit", ""), *(spec.get("aliases") or [])],
            ))

        grahas = self._load_yaml(_DATA_DIR, "grahas")
        for name, spec in (grahas.get("grahas") or {}).items():
            self._add_node(Node(
                id=f"graha:{name}", kind="graha", name=name,
                attrs=spec,
                aliases=[spec.get("sanskrit", ""), *(spec.get("aliases") or [])],
            ))

        bhavas = self._load_yaml(_DATA_DIR, "bhavas")
        for num, spec in (bhavas.get("bhavas") or {}).items():
            self._add_node(Node(
                id=f"bhava:{num}", kind="bhava", name=str(num),
                attrs=spec,
                aliases=[spec.get("sanskrit", ""), *(spec.get("aliases") or [])],
            ))

        nakshatras = self._load_yaml(_DATA_DIR, "nakshatras")
        nak_source = nakshatras.get("source", "")
        for name, spec in (nakshatras.get("nakshatras") or {}).items():
            self._add_node(Node(
                id=f"nakshatra:{name}", kind="nakshatra", name=name,
                attrs={**spec, "source": nak_source},
                aliases=list(spec.get("aliases") or []),
            ))

        areas = self._load_yaml(_DATA_DIR, "areas")
        for name, spec in (areas.get("areas") or {}).items():
            self._add_node(Node(
                id=f"area:{name}", kind="area", name=name,
                attrs=spec,
                aliases=list(spec.get("aliases") or []),
            ))

        # Yogas ride the existing curated catalog under rules/.
        yogas = self._load_yaml(_RULES_DIR, "yogas")
        for entry in yogas.get("yogas") or []:
            name = entry.get("name")
            if not name:
                continue
            self._add_node(Node(
                id=f"yoga:{name}", kind="yoga", name=name,
                attrs=entry,
                aliases=[name.replace(" Yoga", "").replace(" Dosha", "")],
            ))

        self._build_edges(rashi_source, nak_source)

    def _build_edges(self, rashi_source: str, nak_source: str) -> None:
        for node in list(self.nodes.values()):
            if node.kind == "rashi":
                lord = node.attrs.get("lord")
                if lord:
                    self._add_edge(f"graha:{lord}", "rules", node.id, source=rashi_source)
            elif node.kind == "graha":
                a = node.attrs
                for rel, spec in (
                    ("exalted_in", a.get("exaltation")),
                    ("debilitated_in", a.get("debilitation")),
                    ("moolatrikona_in", a.get("moolatrikona")),
                ):
                    if spec and spec.get("sign"):
                        self._add_edge(node.id, rel, f"rashi:{spec['sign']}",
                                       source="BPHS dignities", **{
                                           k: v for k, v in spec.items() if k != "sign"
                                       })
                maitri_src = "BPHS naisargika maitri"
                for friend in a.get("friends") or []:
                    self._add_edge(node.id, "friend_of", f"graha:{friend}", source=maitri_src)
                for enemy in a.get("enemies") or []:
                    self._add_edge(node.id, "enemy_of", f"graha:{enemy}", source=maitri_src)
            elif node.kind == "nakshatra":
                lord = node.attrs.get("lord")
                if lord:
                    self._add_edge(f"graha:{lord}", "rules_nakshatra", node.id, source=nak_source)
            elif node.kind == "bhava":
                for karaka in node.attrs.get("karakas") or []:
                    self._add_edge(f"graha:{karaka}", "karaka_for_bhava", node.id,
                                   source=node.attrs.get("source", ""))
            elif node.kind == "area":
                a = node.attrs
                for h in a.get("primary_houses") or []:
                    self._add_edge(node.id, "governed_by", f"bhava:{h}",
                                   role="primary", source=a.get("source", ""))
                for h in a.get("supporting_houses") or []:
                    self._add_edge(node.id, "governed_by", f"bhava:{h}",
                                   role="supporting", source=a.get("source", ""))
                for k in a.get("karakas") or []:
                    self._add_edge(node.id, "karaka", f"graha:{k}", source=a.get("source", ""))

    # ------------------------------------------------------------- queries

    def node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def edges_from(self, node_id: str, rel: Optional[str] = None) -> list[Edge]:
        return [e for e in self._out.get(node_id, []) if rel is None or e.rel == rel]

    def edges_to(self, node_id: str, rel: Optional[str] = None) -> list[Edge]:
        return [e for e in self._in.get(node_id, []) if rel is None or e.rel == rel]

    def find_entities(self, text: str) -> list[Node]:
        """Longest-match alias scan over free text (case-insensitive,
        word-boundary aware). Returns unique nodes in order of appearance."""
        found: list[tuple[int, Node]] = []
        lowered = (text or "").lower()
        taken: list[tuple[int, int]] = []
        for alias in sorted(self._alias_index, key=len, reverse=True):
            if len(alias) < 3:
                continue
            for m in re.finditer(rf"\b{re.escape(alias)}\b", lowered):
                span = (m.start(), m.end())
                if any(s < span[1] and span[0] < e for s, e in taken):
                    continue
                taken.append(span)
                found.append((m.start(), self.nodes[self._alias_index[alias]]))
        seen: set[str] = set()
        out: list[Node] = []
        for _pos, node in sorted(found, key=lambda t: t[0]):
            if node.id not in seen:
                seen.add(node.id)
                out.append(node)
        return out

    # --------------------------------------------- functional nature (BPHS 34)

    def houses_ruled(self, graha: str, lagna_sign_name: str) -> list[int]:
        try:
            lagna_idx = SIGN_NAMES.index(lagna_sign_name)
        except ValueError:
            return []
        ruled = []
        for house in range(1, 13):
            sign = SIGN_NAMES[(lagna_idx + house - 1) % 12]
            rn = self.node(f"rashi:{sign}")
            if rn and rn.attrs.get("lord") == graha:
                ruled.append(house)
        return ruled

    def functional_nature(self, graha: str, lagna_sign_name: str) -> dict[str, Any]:
        """Derive functional benefic/malefic status for `graha` with respect
        to the given lagna, per BPHS ch. 34 principles. Returns a verdict
        plus the reasons (each independently citable)."""
        node = self.node(f"graha:{graha}")
        if node is None:
            return {"verdict": "unknown", "reasons": [], "houses_ruled": []}
        if not node.attrs.get("own_signs"):  # Rahu/Ketu
            return {
                "verdict": "nodal",
                "houses_ruled": [],
                "reasons": [
                    "Rahu/Ketu give results per their sign dispositor and conjunctions (BPHS ch. 34)"
                ],
                "source": "BPHS ch. 34",
            }
        ruled = self.houses_ruled(graha, lagna_sign_name)
        reasons: list[str] = []
        benefic = malefic = False
        maraka = False
        natural_benefic = node.attrs.get("nature", {}).get("class") == "natural_benefic"

        if any(h in TRIKONA and h != 1 for h in ruled):
            benefic = True
            reasons.append(f"rules trikona house {[h for h in ruled if h in TRIKONA and h != 1]} — trikona lords give auspicious results")
        if 1 in ruled:
            benefic = True
            reasons.append("lagna lord — protects the body and life direction")
        trishadaya = [h for h in ruled if h in TRISHADAYA]
        if trishadaya:
            malefic = True
            reasons.append(f"rules trishadaya house {trishadaya} — lords of 3/6/11 give inauspicious results")
        if 8 in ruled and 1 not in ruled and graha not in ("Sun", "Moon"):
            malefic = True
            reasons.append("rules the 8th — randhresha affliction")
        if any(h in MARAKA_HOUSES for h in ruled):
            maraka = True
            reasons.append(f"rules maraka house {[h for h in ruled if h in MARAKA_HOUSES]} — vitality needs care in its periods")
        kendras = [h for h in ruled if h in KENDRA and h != 1]
        if kendras and natural_benefic:
            reasons.append(f"natural benefic ruling kendra {kendras} — kendradhipati dosha dilutes its benefic promise")

        yogakaraka = bool({h for h in ruled if h in KENDRA} and {h for h in ruled if h in TRIKONA and h != 1})
        if yogakaraka:
            reasons.append("rules both a kendra and a trikona — yogakaraka for this lagna")

        if yogakaraka:
            verdict = "yogakaraka"
        elif benefic and not malefic:
            verdict = "functional benefic"
        elif malefic and not benefic:
            verdict = "functional malefic"
        elif benefic and malefic:
            verdict = "mixed"
        else:
            verdict = "neutral"
        return {
            "verdict": verdict,
            "maraka": maraka,
            "houses_ruled": ruled,
            "reasons": reasons,
            "source": "BPHS ch. 34 (functional lordship principles)",
        }

    # ------------------------------------------------------------- export

    def subgraph(self, focus: Optional[str] = None, depth: int = 1) -> dict:
        """JSON-serializable neighborhood (or the whole graph when no focus)
        for the knowledge-explorer UI."""
        if focus is None or focus not in self.nodes:
            node_ids: Iterable[str] = self.nodes.keys()
        else:
            frontier = {focus}
            node_ids_set = {focus}
            for _ in range(max(depth, 0)):
                nxt: set[str] = set()
                for nid in frontier:
                    for e in self._out.get(nid, []) + self._in.get(nid, []):
                        nxt.update((e.src, e.dst))
                nxt -= node_ids_set
                node_ids_set |= nxt
                frontier = nxt
            node_ids = node_ids_set
        node_ids = set(node_ids)
        return {
            "nodes": [
                {"id": n.id, "kind": n.kind, "name": n.name, "attrs": n.attrs}
                for nid in sorted(node_ids)
                if (n := self.nodes.get(nid))
            ],
            "edges": [
                {"src": e.src, "rel": e.rel, "dst": e.dst, "attrs": e.attrs}
                for e in self.edges
                if e.src in node_ids and e.dst in node_ids
            ],
        }

    def stats(self) -> dict:
        by_kind: dict[str, int] = {}
        for n in self.nodes.values():
            by_kind[n.kind] = by_kind.get(n.kind, 0) + 1
        return {"nodes": len(self.nodes), "edges": len(self.edges), "by_kind": by_kind}


@lru_cache(maxsize=1)
def get_graph() -> KnowledgeGraph:
    return KnowledgeGraph()
