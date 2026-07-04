"use client";

import { useState } from "react";
import type { DashaPeriod } from "@/lib/api";
import { fmtDate } from "@/lib/jyotisha";

const LEVEL_NAMES = ["Mahādaśā", "Antardaśā", "Pratyantardaśā"];

function DashaNode({ node }: { node: DashaPeriod }) {
  // Active branches start expanded so the current path is visible.
  const [open, setOpen] = useState(node.active);
  const hasChildren = node.children.length > 0;

  return (
    <div className={node.level > 1 ? "ml-4 border-l border-night-600/60 pl-3" : ""}>
      <button
        type="button"
        onClick={() => hasChildren && setOpen((v) => !v)}
        className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition ${
          node.active
            ? "bg-gold-600/15 text-gold-200"
            : "text-slate-300 hover:bg-night-700/50"
        } ${hasChildren ? "cursor-pointer" : "cursor-default"}`}
      >
        {hasChildren ? (
          <span className="w-3 text-xs text-slate-500">{open ? "▾" : "▸"}</span>
        ) : (
          <span className="w-3" />
        )}
        <span className={`font-semibold ${node.active ? "text-gold-300" : ""}`}>
          {node.lord}
        </span>
        <span className="text-xs text-slate-500">
          {fmtDate(node.start)} → {fmtDate(node.end)}
        </span>
        {node.active && <span className="badge-gold ml-auto">active</span>}
      </button>
      {open && hasChildren && (
        <div className="mt-1 space-y-0.5">
          {node.children.map((c, i) => (
            <DashaNode key={`${c.lord}-${i}`} node={c} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DashaTree({ periods }: { periods: DashaPeriod[] }) {
  if (periods.length === 0) {
    return <p className="text-sm text-slate-500">No dasha data.</p>;
  }
  return (
    <div>
      <p className="mb-2 text-xs text-slate-500">
        {LEVEL_NAMES.join(" → ")} · Vimśottarī · active path highlighted
      </p>
      <div className="space-y-0.5">
        {periods.map((p, i) => (
          <DashaNode key={`${p.lord}-${i}`} node={p} />
        ))}
      </div>
    </div>
  );
}
