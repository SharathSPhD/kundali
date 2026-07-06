"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Anchor,
  ArrowLeft,
  Briefcase,
  Coins,
  Heart,
  HeartPulse,
  House,
  GraduationCap,
  Send,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import SouthIndianChart, {
  type SignPlacement,
} from "@/components/SouthIndianChart";
import Button from "@/components/ui/Button";
import Tabs from "@/components/ui/Tabs";
import {
  fetchChart,
  fetchVargas,
  interpret,
  type ChartData,
  type VargaChart,
} from "@/lib/api";
import { getProfile } from "@/lib/profiles";
import type { BirthProfile } from "@/lib/types";
import { birthDataOf } from "@/lib/types";
import {
  ALL_VARGAS,
  VARGA_LABELS,
  fmtDate,
  fmtDegMin,
  signName,
} from "@/lib/jyotisha";

const SUGGESTIONS = [
  "What does my current dasha indicate?",
  "How is my career period looking?",
  "Which yogas are active in my chart?",
  "What should I know about the current transits?",
];

const AREA_ICONS: Record<string, LucideIcon> = {
  career: Briefcase,
  wealth: Coins,
  health: HeartPulse,
  relationships: Heart,
  family: House,
  education: GraduationCap,
};

const QUICK_VARGAS = ["D1", "D9", "D10"] as const;
const PAGE_TABS = ["Answer", "Chart details"] as const;

interface EngineArea {
  area: string;
  score: number;
  favorability_label?: string;
  favorabilityLabel?: string;
  trend?: string;
  windows?: Array<{
    start?: string | null;
    end?: string | null;
    from?: string | null;
    to?: string | null;
    label?: string;
    why?: string;
  }>;
}

interface EnginePayload {
  dasha_path?: Array<{ lord: string; level_name?: string; start?: string; end?: string }>;
  areas?: EngineArea[];
}

function chartToPlacements(chart: ChartData): SignPlacement[] {
  const map = new Map<number, SignPlacement>();
  for (const p of chart.positions) {
    const entry = map.get(p.sign) ?? { sign: p.sign, planets: [] };
    entry.planets.push({ abbr: p.abbr, deg: p.degInSign, retro: p.retrograde });
    map.set(p.sign, entry);
  }
  return Array.from(map.values());
}

function vargaToPlacements(v: VargaChart): SignPlacement[] {
  const map = new Map<number, SignPlacement>();
  for (const p of v.placements) {
    const entry = map.get(p.sign) ?? { sign: p.sign, planets: [] };
    entry.planets.push({ abbr: p.abbr, retro: p.retrograde });
    map.set(p.sign, entry);
  }
  return Array.from(map.values());
}

function favorabilityLabel(area: EngineArea): string {
  return (
    area.favorability_label ??
    area.favorabilityLabel ??
    "mixed"
  );
}

function isFavourableLabel(label: string): boolean {
  const lower = label.toLowerCase();
  return lower.includes("favourable") || lower.includes("favorable");
}

function windowStart(w: NonNullable<EngineArea["windows"]>[number]): string | null {
  return w.start ?? w.from ?? null;
}

function windowEnd(w: NonNullable<EngineArea["windows"]>[number]): string | null {
  return w.end ?? w.to ?? null;
}

function windowLabel(w: NonNullable<EngineArea["windows"]>[number]): string {
  return w.label ?? w.why ?? "";
}

function nextFavorableWindow(
  areas: EngineArea[] | undefined
): { area: string; start: string; end: string | null; label: string } | null {
  if (!areas?.length) return null;
  const now = Date.now();
  let best: { area: string; start: string; end: string | null; label: string; ts: number } | null =
    null;

  for (const area of areas) {
    const label = favorabilityLabel(area);
    if (!isFavourableLabel(label) || (area.score ?? 0) <= 0) continue;
    for (const w of area.windows ?? []) {
      const start = windowStart(w);
      if (!start) continue;
      const ts = new Date(start).getTime();
      if (Number.isNaN(ts) || ts < now) continue;
      if (!best || ts < best.ts) {
        best = {
          area: area.area,
          start,
          end: windowEnd(w),
          label: windowLabel(w),
          ts,
        };
      }
    }
  }
  if (!best) return null;
  return {
    area: best.area,
    start: best.start,
    end: best.end,
    label: best.label,
  };
}

function FavorabilityChip({ label }: { label: string }) {
  const lower = label.toLowerCase();
  const favourable = lower.includes("favourable") || lower.includes("favorable");
  const mixed = lower === "mixed";
  const strained = lower.includes("strained");
  const className = favourable
    ? "border-gold-600/60 bg-gold-600/10 text-gold-300"
    : mixed
      ? "border-amber-700/60 bg-amber-900/20 text-amber-200"
      : strained
        ? "border-red-800/60 bg-red-900/20 text-red-300"
        : "border-night-500 text-slate-300";
  return <span className={`chip text-[11px] ${className}`}>{label}</span>;
}

export default function AskPage({ params }: { params: { id: string } }) {
  const [profile, setProfile] = useState<BirthProfile | null>(null);
  const [pageTab, setPageTab] = useState<(typeof PAGE_TABS)[number]>("Answer");
  const [summaryText, setSummaryText] = useState("");
  const [citations, setCitations] = useState<string[]>([]);
  const [provider, setProvider] = useState<string>("template");
  const [enginePayload, setEnginePayload] = useState<EnginePayload | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chart, setChart] = useState<ChartData | null>(null);
  const [vargas, setVargas] = useState<VargaChart[]>([]);
  const [selectedVarga, setSelectedVarga] = useState("D1");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const p = await getProfile(params.id);
        if (!p) {
          if (!cancelled) {
            setError("Profile not found.");
            setLoading(false);
          }
          return;
        }
        if (cancelled) return;
        setProfile(p);
        const birth = birthDataOf(p);
        const [interpretRes, chartRes, vargasRes] = await Promise.allSettled([
          interpret(birth, "", "template"),
          fetchChart(birth),
          fetchVargas(birth, [...ALL_VARGAS]),
        ]);
        if (cancelled) return;
        if (interpretRes.status === "fulfilled") {
          const res = interpretRes.value;
          setSummaryText(res.text || "");
          setCitations(res.citations ?? []);
          setProvider(res.provider);
          setEnginePayload((res.enginePayload as EnginePayload) ?? null);
        } else {
          setError(interpretRes.reason?.message ?? "Interpretation failed.");
        }
        if (chartRes.status === "fulfilled") setChart(chartRes.value);
        if (vargasRes.status === "fulfilled") setVargas(vargasRes.value);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  const displayed = useMemo(() => {
    if (!chart) return null;
    if (selectedVarga === "D1") {
      return {
        placements: chartToPlacements(chart),
        lagnaSign: chart.lagna.sign,
        title: "Rāśi (D1)",
      };
    }
    const v = vargas.find(
      (x) => x.name.toUpperCase() === selectedVarga.toUpperCase()
    );
    if (!v) return null;
    return {
      placements: vargaToPlacements(v),
      lagnaSign: v.lagnaSign,
      title: selectedVarga,
    };
  }, [chart, vargas, selectedVarga]);

  const favorableWindow = useMemo(
    () => nextFavorableWindow(enginePayload?.areas),
    [enginePayload]
  );

  async function ask(question: string) {
    const q = question.trim();
    if (!q || !profile || busy) return;
    setInput("");
    setError(null);
    setBusy(true);
    try {
      const res = await interpret(birthDataOf(profile), q, "template");
      setSummaryText(res.text || "(empty response)");
      setCitations(res.citations ?? []);
      setProvider(res.provider);
      if (res.enginePayload) {
        setEnginePayload(res.enginePayload as EnginePayload);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question failed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Loading deterministic answers…</p>;
  }

  const dashaPath = enginePayload?.dasha_path ?? [];
  const areas = enginePayload?.areas ?? [];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-2xl font-bold text-slate-100">
            {profile ? `${profile.label} — Instant answers` : "Instant answers"}
          </h1>
          <span className="chip border-gold-700/50 text-[11px] text-gold-300">
            {provider === "template_qa"
              ? "Deterministic Q&A"
              : "Deterministic summary"}
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button href={`/dashboard/chat/${params.id}`} size="sm" icon={Sparkles}>
            LLM chat
          </Button>
          <Button href={`/dashboard/chart/${params.id}`} size="sm" icon={ArrowLeft}>
            Full chart
          </Button>
        </div>
      </div>

      <p className="rounded-lg border border-night-600/60 bg-night-800/50 px-3 py-2 text-xs text-slate-400">
        Zero-LLM, always-on answers grounded in your computed chart. Ask a
        question for cited Q&A, or read the default summary below. Chart tables
        are on the secondary tab.
      </p>

      {error && <p className="text-sm text-red-300">{error}</p>}

      <Tabs
        options={[...PAGE_TABS]}
        value={pageTab}
        onChange={(v) => setPageTab(v as (typeof PAGE_TABS)[number])}
      />

      {pageTab === "Answer" ? (
        <>
          {(areas.length > 0 || dashaPath.length > 0) && (
            <div className="card space-y-4 p-4">
              {areas.length > 0 && (
                <div>
                  <p className="mb-2 text-xs uppercase tracking-wider text-slate-500">
                    Life areas (engine favourability)
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {areas.map((a) => {
                      const Icon = AREA_ICONS[a.area.toLowerCase()] ?? Sparkles;
                      return (
                        <span
                          key={a.area}
                          className="chip gap-1.5 capitalize"
                          title={`Score ${a.score >= 0 ? "+" : ""}${a.score?.toFixed(2) ?? "?"}`}
                        >
                          <Icon className="h-3 w-3 text-gold-500" aria-hidden />
                          {a.area}
                          <FavorabilityChip label={favorabilityLabel(a)} />
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {dashaPath.length > 0 && (
                <div>
                  <p className="mb-2 text-xs uppercase tracking-wider text-slate-500">
                    Active daśā path
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {dashaPath.map((node, i) => (
                      <span
                        key={`${node.lord}-${i}`}
                        className="chip border-gold-700/40 text-gold-200"
                      >
                        <span className="font-semibold">{node.lord}</span>
                        {node.level_name ? (
                          <span className="text-slate-400"> · {node.level_name}</span>
                        ) : null}
                        {node.start && node.end ? (
                          <span className="ml-1 text-[10px] text-slate-500">
                            {fmtDate(node.start)} → {fmtDate(node.end)}
                          </span>
                        ) : null}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {favorableWindow ? (
                <div className="rounded-lg border border-gold-700/40 bg-gold-600/5 px-3 py-2">
                  <p className="text-xs uppercase tracking-wider text-gold-400">
                    Next favourable window (best-effort from daśā periods)
                  </p>
                  <p className="mt-1 text-sm text-slate-200">
                    <span className="capitalize">{favorableWindow.area}</span>
                    {favorableWindow.label ? ` — ${favorableWindow.label}` : ""}
                    {": "}
                    {fmtDate(favorableWindow.start)}
                    {favorableWindow.end
                      ? ` → ${fmtDate(favorableWindow.end)}`
                      : ""}
                  </p>
                  <p className="mt-1 text-[11px] text-slate-500">
                    Derived client-side from upcoming antardaśā/pratyantardaśā
                    windows in areas with favourable scores — not a separate
                    engine forecast.
                  </p>
                </div>
              ) : areas.some((a) => isFavourableLabel(favorabilityLabel(a))) ? (
                <p className="text-xs text-slate-500">
                  No upcoming daśā window start date found in favourable areas;
                  current periods may already be active.
                </p>
              ) : null}
            </div>
          )}

          <div className="card p-5">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
              {summaryText || "No summary available."}
            </p>
            {citations.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1.5 border-t border-night-600/60 pt-3">
                {citations.map((c, j) => (
                  <span
                    key={j}
                    className="chip gap-1 border-gold-700/50 text-[11px] text-gold-300"
                    title="Engine fact cited by this answer"
                  >
                    <Anchor className="h-3 w-3 shrink-0" aria-hidden /> {c}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                className="chip transition hover:border-gold-600/60 hover:text-gold-300"
                onClick={() => ask(s)}
                disabled={!profile || busy}
              >
                {s}
              </button>
            ))}
          </div>

          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              ask(input);
            }}
          >
            <input
              className="input flex-1"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about this chart…"
              disabled={!profile || busy}
            />
            <button
              type="submit"
              className="btn-gold shrink-0"
              disabled={!profile || busy || !input.trim()}
              aria-label="Ask"
            >
              <Send className="h-4 w-4 sm:hidden" aria-hidden />
              <span className="hidden sm:inline">Ask</span>
            </button>
          </form>
          {busy && (
            <p className="text-sm text-slate-500">Consulting the engine…</p>
          )}
        </>
      ) : (
        <div className="grid gap-8 lg:grid-cols-[minmax(0,26rem)_1fr]">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Tabs
                options={QUICK_VARGAS}
                value={selectedVarga as (typeof QUICK_VARGAS)[number]}
                onChange={setSelectedVarga}
              />
              <select
                className="input w-auto py-1.5 text-xs"
                value={selectedVarga}
                onChange={(e) => setSelectedVarga(e.target.value)}
                aria-label="Select varga"
              >
                {ALL_VARGAS.map((v) => (
                  <option key={v} value={v}>
                    {v} — {VARGA_LABELS[v]}
                  </option>
                ))}
              </select>
            </div>
            {displayed ? (
              <SouthIndianChart
                placements={displayed.placements}
                lagnaSign={displayed.lagnaSign}
                title={displayed.title}
                subtitle={profile?.place_name}
              />
            ) : (
              <div className="card flex aspect-square max-w-md items-center justify-center p-8">
                <p className="text-sm text-slate-500">
                  {chart
                    ? `No data for ${selectedVarga}.`
                    : "Chart data unavailable."}
                </p>
              </div>
            )}
          </div>

          <div className="card overflow-x-auto p-4">
            <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
              Graha positions
            </h2>
            {chart ? (
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-night-600 text-xs uppercase tracking-wider text-slate-500">
                    <th className="py-2 pr-3">Graha</th>
                    <th className="py-2 pr-3">Sign</th>
                    <th className="py-2 pr-3">Degree</th>
                    <th className="py-2 pr-3">Nakshatra</th>
                    <th className="py-2">Dignity</th>
                  </tr>
                </thead>
                <tbody>
                  {chart.positions.map((p) => (
                    <tr
                      key={p.planet}
                      className="border-b border-night-700/50 last:border-0"
                    >
                      <td className="py-2 pr-3 font-semibold text-slate-200">
                        {p.planet}{" "}
                        <span className="text-xs text-slate-500">{p.abbr}</span>
                      </td>
                      <td className="py-2 pr-3">{signName(p.sign)}</td>
                      <td className="py-2 pr-3 font-mono text-slate-300">
                        {fmtDegMin(p.degInSign)}
                      </td>
                      <td className="py-2 pr-3 text-slate-300">
                        {p.nakshatra || "—"}
                        {p.pada ? (
                          <span className="text-slate-500"> · {p.pada}</span>
                        ) : null}
                      </td>
                      <td className="py-2 capitalize text-slate-300">
                        {p.dignity ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-sm text-slate-500">Chart table unavailable.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
