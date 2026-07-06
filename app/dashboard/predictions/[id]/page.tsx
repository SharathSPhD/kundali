"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Briefcase,
  Coins,
  Heart,
  HeartPulse,
  House,
  Sparkles,
  TrendingDown,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import {
  fetchJaimini,
  fetchPredictions,
  fetchTransits,
  fetchYogas,
  type JaiminiData,
  type Prediction,
  type TransitData,
  type Yoga,
} from "@/lib/api";
import { getProfile } from "@/lib/profiles";
import { getLatestReading, saveReading } from "@/lib/readings";
import type { BirthProfile } from "@/lib/types";
import { birthDataOf } from "@/lib/types";
import { fmtDate, signName } from "@/lib/jyotisha";

interface PredictionsReadingCache {
  predictions: Prediction[];
  transits: TransitData | null;
  yogas: Yoga[];
  jaimini: JaiminiData | null;
}

function isPredictionsReadingCache(v: unknown): v is PredictionsReadingCache {
  return !!v && typeof v === "object" && "predictions" in v;
}

const AREA_ICONS: Record<string, LucideIcon> = {
  career: Briefcase,
  wealth: Coins,
  health: HeartPulse,
  relationships: Heart,
  family: House,
};

function TrendBadge({ trend }: { trend: string }) {
  const t = trend.toLowerCase();
  const rising = ["rising", "up", "improving", "ascending", "positive"].some((k) =>
    t.includes(k)
  );
  const falling = ["falling", "down", "declining", "descending", "negative"].some(
    (k) => t.includes(k)
  );
  const Icon = rising ? TrendingUp : falling ? TrendingDown : null;
  return (
    <span
      className={`chip gap-1 ${
        rising
          ? "border-gold-600/60 text-gold-300"
          : falling
            ? "border-red-800/60 text-red-300"
            : ""
      }`}
    >
      {Icon && <Icon className="h-3 w-3" aria-hidden />} {trend}
    </span>
  );
}

function FavorabilityBadge({ label }: { label: string }) {
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
  return <span className={`chip ${className}`}>{label}</span>;
}

function PredictionCard({ prediction }: { prediction: Prediction }) {
  const AreaIcon = AREA_ICONS[prediction.area.toLowerCase()] ?? Sparkles;
  return (
    <div className="card animate-fade-up p-5 transition-transform hover:-translate-y-0.5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="flex items-center gap-2 font-display text-lg font-semibold capitalize text-slate-100">
            <AreaIcon className="h-4 w-4 shrink-0 text-gold-500" aria-hidden />
            {prediction.area}
          </h3>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <FavorabilityBadge label={prediction.favorabilityLabel} />
            <TrendBadge trend={prediction.trend} />
          </div>
        </div>
      </div>

      {prediction.windows.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {prediction.windows.map((w, i) => (
            <span key={i} className="chip">
              {w.start ? fmtDate(w.start) : ""}
              {w.end ? ` → ${fmtDate(w.end)}` : ""}
              {w.label && (!w.start || w.label !== w.start) ? ` ${w.label}` : ""}
            </span>
          ))}
        </div>
      )}

      {(prediction.substantiation.length > 0 || prediction.score !== 0) && (
        <details className="mt-4 group">
          <summary className="cursor-pointer text-xs font-medium text-gold-400 hover:underline">
            Why this score?
          </summary>
          <div className="mt-2 space-y-2 border-l border-gold-700/40 pl-3">
            <p className="text-xs text-slate-400">
              Engine score:{" "}
              <span className="font-mono text-slate-300">
                {prediction.score >= 0 ? "+" : ""}
                {prediction.score.toFixed(2)}
              </span>{" "}
              (range −1 to +1)
            </p>
            {prediction.substantiation.length > 0 && (
              <ul className="space-y-1.5">
                {prediction.substantiation.map((s, i) => (
                  <li key={i} className="text-xs leading-relaxed text-slate-400">
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </details>
      )}
    </div>
  );
}

export default function PredictionsPage({
  params,
}: {
  params: { id: string };
}) {
  const [profile, setProfile] = useState<BirthProfile | null>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [transits, setTransits] = useState<TransitData | null>(null);
  const [yogas, setYogas] = useState<Yoga[]>([]);
  const [jaimini, setJaimini] = useState<JaiminiData | null>(null);
  const [showAbsent, setShowAbsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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

        const cached = await getLatestReading(p.id, "predictions");
        if (!cancelled && isPredictionsReadingCache(cached)) {
          setPredictions(cached.predictions ?? []);
          setTransits(cached.transits ?? null);
          setYogas(cached.yogas ?? []);
          setJaimini(cached.jaimini ?? null);
          setLoading(false);
        }

        const birth = birthDataOf(p);
        const [predRes, transitRes, yogaRes, jaiminiRes] =
          await Promise.allSettled([
            fetchPredictions(birth),
            fetchTransits(birth),
            fetchYogas(birth),
            fetchJaimini(birth),
          ]);
        if (cancelled) return;
        if (predRes.status === "fulfilled") setPredictions(predRes.value);
        else if (!cached)
          setError(predRes.reason?.message ?? "Prediction engine failed.");
        if (transitRes.status === "fulfilled") setTransits(transitRes.value);
        if (yogaRes.status === "fulfilled") setYogas(yogaRes.value);
        if (jaiminiRes.status === "fulfilled") setJaimini(jaiminiRes.value);
        if (predRes.status === "fulfilled")
          void saveReading(p.id, "predictions", {
            predictions: predRes.value,
            transits: transitRes.status === "fulfilled" ? transitRes.value : null,
            yogas: yogaRes.status === "fulfilled" ? yogaRes.value : [],
            jaimini: jaiminiRes.status === "fulfilled" ? jaiminiRes.value : null,
          } satisfies PredictionsReadingCache);
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

  if (loading) {
    return <p className="text-sm text-slate-500">Synthesizing indications…</p>;
  }

  const presentYogas = yogas.filter((y) => y.present);
  const absentYogas = yogas.filter((y) => !y.present);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-2xl font-bold text-slate-100">
          {profile?.label} — Predictions
        </h1>
        <Button href={`/dashboard/chart/${params.id}`} size="sm">
          ← Chart
        </Button>
      </div>

      <p className="text-xs text-slate-500">
        Deterministic synthesis: active daśā lords × current transits × natal
        promise. Every card carries its substantiation trail — no claims
        without engine facts.
      </p>

      {error && predictions.length === 0 && (
        <div className="card p-6">
          <p className="text-sm text-red-300">{error}</p>
          <p className="mt-1 text-xs text-slate-500">
            Is the calculation engine running? (API_BASE_URL, default
            http://localhost:8000)
          </p>
        </div>
      )}

      {/* Sade Sati banner */}
      {transits?.sadeSati.active && (
        <div className="rounded-xl border border-gold-600/60 bg-gradient-to-r from-gold-600/20 to-night-800 p-4">
          <p className="flex items-center gap-2 font-display text-lg font-semibold text-gold-300">
            <AlertTriangle className="h-5 w-5 shrink-0" aria-hidden />
            Sade Sati is active
            {transits.sadeSati.phase ? ` — ${transits.sadeSati.phase} phase` : ""}
          </p>
          <p className="mt-1 text-sm text-slate-300">
            Saturn is transiting the 12th, 1st or 2nd from the natal Moon.
            {transits.sadeSati.start &&
              ` From ${fmtDate(transits.sadeSati.start)}`}
            {transits.sadeSati.end && ` until ${fmtDate(transits.sadeSati.end)}`}
            .
          </p>
        </div>
      )}

      {/* Prediction cards */}
      {predictions.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {predictions.map((p, i) => (
            <PredictionCard key={`${p.area}-${i}`} prediction={p} />
          ))}
        </div>
      )}

      {/* Chara Dasha (Jaimini, K.N. Rao school) */}
      {jaimini && (jaimini.activeMaha || jaimini.karakas.length > 0) && (
        <div className="card p-5">
          <h2 className="mb-1 font-display text-lg font-semibold text-gold-300">
            Chara Daśā (Jaimini — K.N. Rao)
          </h2>
          <p className="mb-3 text-xs text-slate-500">
            Sign-based dasha, {jaimini.direction || "direct"} sequence.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {jaimini.activeMaha && (
              <span className="rounded-lg border border-gold-600/60 bg-gold-600/10 px-3 py-1.5 text-sm text-gold-200">
                <span className="font-semibold">
                  {jaimini.activeMaha.signName}
                </span>{" "}
                mahādaśā
                <span className="ml-2 text-xs text-slate-400">
                  {fmtDate(jaimini.activeMaha.start)} →{" "}
                  {fmtDate(jaimini.activeMaha.end)}
                  {jaimini.activeMaha.years
                    ? ` · ${jaimini.activeMaha.years}y`
                    : ""}
                </span>
              </span>
            )}
            {jaimini.activeAntar && (
              <span className="rounded-lg border border-night-500 bg-night-800 px-3 py-1.5 text-sm text-slate-200">
                <span className="font-semibold">
                  {jaimini.activeAntar.signName}
                </span>{" "}
                antardaśā
                <span className="ml-2 text-xs text-slate-500">
                  {fmtDate(jaimini.activeAntar.start)} →{" "}
                  {fmtDate(jaimini.activeAntar.end)}
                </span>
              </span>
            )}
          </div>
          {jaimini.karakas.length > 0 && (
            <div className="mt-4">
              <p className="mb-1.5 text-xs uppercase tracking-wider text-slate-500">
                Chara kārakas
              </p>
              <div className="flex flex-wrap gap-1.5">
                {jaimini.karakas.map((k) => (
                  <span
                    key={k.karaka}
                    className="chip"
                    title={`${k.karaka}: ${k.planet} ${signName(k.sign)} ${k.degInSign.toFixed(2)}°`}
                  >
                    <span className="font-semibold text-gold-400">
                      {k.abbr}
                    </span>
                    &nbsp;{k.planet}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Gochara snapshot */}
      {transits && transits.gochara.length > 0 && (
        <div className="card p-5">
          <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
            Gochara (transits from Moon)
          </h2>
          <div className="flex flex-wrap gap-2">
            {transits.gochara.map((g, i) => (
              <span
                key={`${g.planet}-${i}`}
                className={`chip ${
                  g.favorable === true
                    ? "border-gold-600/60 text-gold-300"
                    : g.favorable === false
                      ? "border-red-800/60 text-red-300"
                      : ""
                }`}
                title={g.note}
              >
                {g.planet}
                {g.sign ? ` in ${signName(g.sign)}` : ""}
                {g.houseFromMoon ? ` (${g.houseFromMoon} from Moon)` : ""}
              </span>
            ))}
          </div>
          {transits.doubleTransit.length > 0 && (
            <p className="mt-3 text-sm text-slate-300">
              <span className="font-semibold text-gold-400">
                Jupiter–Saturn double transit:
              </span>{" "}
              {transits.doubleTransit.join("; ")}
            </p>
          )}
        </div>
      )}

      {/* Yogas */}
      {yogas.length > 0 && (
        <div className="card p-5">
          <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
            Yogas
          </h2>
          {presentYogas.length === 0 && (
            <p className="text-sm text-slate-500">
              No evaluated yogas are present in this chart.
            </p>
          )}
          <div className="space-y-3">
            {presentYogas.map((y, i) => (
              <div
                key={`${y.name}-${i}`}
                className="rounded-lg border border-gold-700/40 bg-gold-600/5 p-4"
              >
                <p className="font-semibold text-gold-300">
                  {y.name}
                  {y.strength && (
                    <span className="chip ml-2">{y.strength}</span>
                  )}
                </p>
                {y.factors.length > 0 && (
                  <ul className="mt-2 space-y-1 pl-4">
                    {y.factors.map((f, j) => (
                      <li
                        key={j}
                        className="list-disc text-xs leading-relaxed text-slate-400"
                      >
                        {f}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
          {absentYogas.length > 0 && (
            <div className="mt-4">
              <button
                className="text-xs font-medium text-slate-500 hover:text-slate-300"
                onClick={() => setShowAbsent((v) => !v)}
              >
                {showAbsent ? "Hide" : "Show"} {absentYogas.length} yogas not
                present
              </button>
              {showAbsent && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {absentYogas.map((y, i) => (
                    <span key={`${y.name}-${i}`} className="chip opacity-60">
                      {y.name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
