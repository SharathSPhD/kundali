"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, Database, Wifi } from "lucide-react";
import Card from "@/components/ui/Card";
import Tabs from "@/components/ui/Tabs";
import {
  fetchKnowledgeGraph,
  fetchKnowledgeStats,
  fetchKnowledgeNode,
  type KnowledgeGraphSubgraph,
  type KnowledgeStats,
  type KnowledgeNode,
} from "@/lib/api";

interface NodeEntry {
  id: string;
  kind: string;
  name: string;
}

const NODE_KIND_ORDER: Record<string, number> = {
  graha: 0,
  bhava: 1,
  rashi: 2,
  nakshatra: 3,
  area: 4,
  yoga: 5,
};

function sortNodesByKind(nodes: NodeEntry[]): NodeEntry[] {
  return nodes.sort((a, b) => {
    const aOrder = NODE_KIND_ORDER[a.kind] ?? 99;
    const bOrder = NODE_KIND_ORDER[b.kind] ?? 99;
    if (aOrder !== bOrder) return aOrder - bOrder;
    return a.name.localeCompare(b.name);
  });
}

function groupNodesByKind(nodes: NodeEntry[]): Record<string, NodeEntry[]> {
  const grouped: Record<string, NodeEntry[]> = {};
  for (const node of sortNodesByKind(nodes)) {
    const kindLabel = node.kind.charAt(0).toUpperCase() + node.kind.slice(1) + "s";
    if (!grouped[kindLabel]) grouped[kindLabel] = [];
    grouped[kindLabel].push(node);
  }
  return grouped;
}

function NodeBrowser({
  nodes,
  selectedId,
  onSelect,
  loading,
}: {
  nodes: NodeEntry[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}) {
  const [searchText, setSearchText] = useState("");
  const grouped = useMemo(() => {
    let filtered = nodes;
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      filtered = nodes.filter(
        (n) => n.name.toLowerCase().includes(q) || n.id.toLowerCase().includes(q)
      );
    }
    return groupNodesByKind(filtered);
  }, [nodes, searchText]);

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="sticky top-0 z-10 space-y-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            className="input pl-9 w-full"
            placeholder="Search nodes…"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2">
        {Object.entries(grouped).map(([kindLabel, nodeList]) => (
          <div key={kindLabel}>
            <p className="px-2 text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">
              {kindLabel}
            </p>
            <div className="space-y-1">
              {nodeList.map((node) => (
                <button
                  key={node.id}
                  onClick={() => onSelect(node.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                    selectedId === node.id
                      ? "bg-gold-600/20 border border-gold-600/50 text-gold-200"
                      : "hover:bg-night-700/50 text-slate-300 hover:text-slate-100"
                  }`}
                  disabled={loading}
                >
                  {node.name}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EdgeGroup({
  label,
  edges,
  onNavigate,
}: {
  label: string;
  edges: Array<{ rel: string; target: string; source: string }>;
  onNavigate: (nodeId: string) => void;
}) {
  if (!edges.length) return null;
  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-wider text-slate-500 font-semibold">
        {label}
      </p>
      <div className="space-y-1">
        {edges.map((edge, i) => (
          <button
            key={i}
            onClick={() => onNavigate(edge.target)}
            className="group w-full text-left flex items-center justify-between px-3 py-2 rounded-lg text-sm bg-night-700/30 hover:bg-night-700/60 text-slate-300 hover:text-gold-300 transition gap-2"
          >
            <span>
              <span className="text-slate-500">{edge.rel}:</span> {edge.target}
            </span>
            {edge.source && (
              <span className="text-[10px] text-slate-600 group-hover:text-slate-500 shrink-0">
                {edge.source}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function NodeRadialView({ node }: { node: KnowledgeNode }) {
  // Simple radial SVG showing focused node + 1-hop neighbors
  const outgoing = node.edges_out.length;
  const incoming = node.edges_in.length;
  const total = outgoing + incoming;

  const cx = 100,
    cy = 100,
    radius = 40;

  const center = { x: cx, y: cy, label: node.name };
  const points: Array<{ x: number; y: number; label: string; type: "out" | "in" }> = [];

  // Distribute neighbors around the center
  let angle = -Math.PI / 2;
  const angleStep = (2 * Math.PI) / Math.max(total, 1);
  const neighborRadius = 70;

  for (const e of node.edges_out) {
    const x = cx + neighborRadius * Math.cos(angle);
    const y = cy + neighborRadius * Math.sin(angle);
    points.push({
      x,
      y,
      label: (e.dst.split(":")[1] || e.dst).slice(0, 10),
      type: "out",
    });
    angle += angleStep;
  }
  for (const e of node.edges_in) {
    const x = cx + neighborRadius * Math.cos(angle);
    const y = cy + neighborRadius * Math.sin(angle);
    points.push({
      x,
      y,
      label: (e.src.split(":")[1] || e.src).slice(0, 10),
      type: "in",
    });
    angle += angleStep;
  }

  return (
    <svg
      viewBox="0 0 200 200"
      className="w-full max-w-xs mx-auto bg-night-700/20 rounded-lg border border-night-600/50"
    >
      {/* Edges */}
      {points.map((p, i) => (
        <line
          key={`edge-${i}`}
          x1={center.x}
          y1={center.y}
          x2={p.x}
          y2={p.y}
          stroke="rgba(212, 171, 74, 0.2)"
          strokeWidth="1"
        />
      ))}

      {/* Neighbor nodes */}
      {points.map((p, i) => (
        <circle
          key={`point-${i}`}
          cx={p.x}
          cy={p.y}
          r="6"
          fill={p.type === "out" ? "rgba(212, 171, 74, 0.3)" : "rgba(100, 150, 255, 0.2)"}
          stroke={p.type === "out" ? "rgba(212, 171, 74, 0.6)" : "rgba(100, 150, 255, 0.5)"}
        />
      ))}

      {/* Center node */}
      <circle cx={center.x} cy={center.y} r="8" fill="rgba(212, 171, 74, 0.6)" />
      <text
        x={center.x}
        y={center.y + 15}
        textAnchor="middle"
        fontSize="10"
        fill="rgba(239, 221, 162, 0.8)"
        fontWeight="bold"
      >
        {center.label.slice(0, 12)}
      </text>
    </svg>
  );
}

function NodeDetail({
  node,
  loading,
  onNavigate,
}: {
  node: KnowledgeNode | null;
  loading: boolean;
  onNavigate: (nodeId: string) => void;
}) {
  const outEdges = useMemo(
    () =>
      node?.edges_out.map((e) => ({
        rel: e.rel,
        target: e.dst,
        source: e.attrs?.source as string,
      })) || [],
    [node]
  );

  const inEdges = useMemo(
    () =>
      node?.edges_in.map((e) => ({
        rel: e.rel,
        target: e.src,
        source: e.attrs?.source as string,
      })) || [],
    [node]
  );

  if (!node) {
    return (
      <div className="text-center text-slate-500 py-12">
        <Wifi className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">Select a node to view details</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 overflow-y-auto">
      <Card title={node.name} subtitle={`Kind: ${node.kind}`}>
        <div className="space-y-2 text-sm">
          {Object.entries(node.attrs).map(([key, value]) => {
            if (key === "aliases" || key.startsWith("_")) return null;
            const displayValue =
              typeof value === "string"
                ? value
                : Array.isArray(value)
                  ? value.join(", ")
                  : String(value);
            if (displayValue.length > 100) return null; // Skip very long attrs
            return (
              <div key={key} className="flex gap-2">
                <span className="w-32 font-semibold text-slate-400 capitalize">
                  {key.replace(/_/g, " ")}:
                </span>
                <span className="text-slate-200">{displayValue}</span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Radial neighbor view */}
      <div className="px-4 py-2">
        <p className="mb-2 text-xs uppercase tracking-wider text-slate-500 font-semibold">
          1-Hop Neighborhood
        </p>
        <NodeRadialView node={node} />
      </div>

      {/* Outgoing edges */}
      <Card>
        <EdgeGroup
          label="Outgoing Relations"
          edges={outEdges}
          onNavigate={onNavigate}
        />
      </Card>

      {/* Incoming edges */}
      {inEdges.length > 0 && (
        <Card>
          <EdgeGroup
            label="Incoming Relations"
            edges={inEdges}
            onNavigate={onNavigate}
          />
        </Card>
      )}
    </div>
  );
}

export default function KnowledgePage() {
  const [allNodes, setAllNodes] = useState<NodeEntry[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [nodeLoading, setNodeLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const [graphRes, statsRes] = await Promise.all([
          fetchKnowledgeGraph(),
          fetchKnowledgeStats(),
        ]);
        if (!cancelled) {
          setAllNodes(
            graphRes.nodes.map((n) => ({
              id: n.id,
              kind: n.kind,
              name: n.name,
            }))
          );
          setStats(statsRes);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load knowledge graph");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!selectedNodeId) {
      setSelectedNode(null);
      return;
    }
    (async () => {
      try {
        setNodeLoading(true);
        const [kind, name] = selectedNodeId.split(":");
        const node = await fetchKnowledgeNode(kind, name);
        if (!cancelled) {
          setSelectedNode(node);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load node");
        }
      } finally {
        if (!cancelled) setNodeLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedNodeId]);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-2xl font-bold text-slate-100">
          Knowledge Graph Explorer
        </h1>
        {stats && (
          <div className="flex flex-wrap gap-3 text-sm">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Database className="h-4 w-4 text-gold-500" aria-hidden />
              <span>
                <span className="font-semibold text-slate-200">{stats.n_nodes}</span> nodes
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-400">
              <Wifi className="h-4 w-4 text-gold-500" aria-hidden />
              <span>
                <span className="font-semibold text-slate-200">{stats.n_edges}</span> relations
              </span>
            </div>
          </div>
        )}
      </div>

      <p className="rounded-lg border border-night-600/60 bg-night-800/50 px-3 py-2 text-xs text-slate-400">
        Browse the rule system governing Vedic interpretation. Click any node to explore
        its attributes and relationships. Outgoing edges (gold) and incoming edges (blue)
        show how this node connects to the rest of the graph.
      </p>

      {error && <p className="text-sm text-red-300">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-[20rem_1fr]">
        {/* Left: Node browser */}
        <div className="card p-4 h-[600px] overflow-hidden">
          <NodeBrowser
            nodes={allNodes}
            selectedId={selectedNodeId}
            onSelect={setSelectedNodeId}
            loading={nodeLoading}
          />
        </div>

        {/* Right: Node details */}
        <div className="card p-4 h-[600px] overflow-hidden">
          <NodeDetail
            node={selectedNode}
            loading={nodeLoading}
            onNavigate={(id) => setSelectedNodeId(id)}
          />
        </div>
      </div>
    </div>
  );
}
