"""Knowledge-graph explorer endpoints (read-only rule system).

The graph itself is static, versioned data — the same for every user — so
these endpoints require auth (consistent with the rest of the API surface)
but return no user data at all.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from ..auth import UserDep
from ..knowledge.graph import get_graph

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/stats")
def stats(user: dict = UserDep) -> dict:
    return get_graph().stats()


@router.get("/graph")
def graph(focus: Optional[str] = None, depth: int = 1, user: dict = UserDep) -> dict:
    """Whole graph (no focus) or a neighborhood around `focus` node id
    (e.g. `graha:Saturn`, `area:career`, `bhava:10`)."""
    kg = get_graph()
    if focus is not None and kg.node(focus) is None:
        raise HTTPException(status_code=404, detail=f"unknown node: {focus}")
    return kg.subgraph(focus=focus, depth=max(0, min(depth, 3)))


@router.get("/node/{kind}/{name}")
def node(kind: str, name: str, user: dict = UserDep) -> dict:
    kg = get_graph()
    node_id = f"{kind}:{name}"
    n = kg.node(node_id)
    if n is None:
        raise HTTPException(status_code=404, detail=f"unknown node: {node_id}")
    return {
        "id": n.id,
        "kind": n.kind,
        "name": n.name,
        "attrs": n.attrs,
        "edges_out": [
            {"rel": e.rel, "dst": e.dst, "attrs": e.attrs} for e in kg.edges_from(node_id)
        ],
        "edges_in": [
            {"rel": e.rel, "src": e.src, "attrs": e.attrs} for e in kg.edges_to(node_id)
        ],
    }
