"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { MessageCircleQuestion, Sparkles, Grid3x3 } from "lucide-react";
import SouthIndianChart, {
  type SignPlacement,
} from "@/components/SouthIndianChart";
import DashaTree from "@/components/DashaTree";
import AshtakavargaTable from "@/components/AshtakavargaTable";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Tabs from "@/components/ui/Tabs";
import {
  fetchAshtakavarga,
  fetchChart,
  fetchDashas,
  fetchPanchanga,
  fetchShadbala,
  fetchVargas,
  type AshtakavargaData,
  type ChartData,
  type DashaPeriod,
  type PanchangaData,
  type ShadbalaRow,
  type VargaChart,
} from "@/lib/api";
import { getProfile } from "@/lib/profiles";
import { getLatestReading, saveReading } from "@/lib/readings";
import type { BirthProfile } from "@/lib/types";
import { birthDataOf } from "@/lib/types";
import {
  ALL_VARGAS,
  VARGA_LABELS,
  fmtDegMin,
  signName,
} from "@/lib/jyotisha";

const QUICK_VARGAS = ["D1", "D9", "D10"] as const;

interface ChartReadingCache {
  chart: ChartData | null;
  vargas: VargaChart[];
  dashas: DashaPeriod[];
  panchanga: PanchangaData | null;
  shadbala: ShadbalaRow[];
  ashtakavarga: AshtakavargaData | null;
}

function isChartReadingCache(v: unknown): v is ChartReadingCache {
  return !!v && typeof v === "object" && "chart" in v;
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

export default function ChartPage({ params }: { params: { id: string } }) {
  const [profile, setProfile] = useState<BirthProfile | null>(null);
  const [chart, setChart] = useState<ChartData | null>(null);
  const [vargas, setVargas] = useState<VargaChart[]>([]);
  const [dashas, setDashas] = useState<DashaPeriod[]>([]);
  const [panchanga, setPanchanga] = useState<PanchangaData | null>(null);
  const [shadbala, setShadbala] = useState<ShadbalaRow[]>([]);
  const [ashtakavarga, setAshtakavarga] = useState<AshtakavargaData | null>(null);
  const [selectedVarga, setSelectedVarga] = useState("D1");
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

        // Instant-hydrate from the last cached reading (if any) so the page
        // isn't blank while the live computation round-trips; overwritten
        // below once the fresh engine data lands.
        const cached = await getLatestReading(p.id, "chart");
        if (!cancelled && isChartReadingCache(cached)) {
          setChart(cached.chart);
          setVargas(cached.vargas ?? []);
          setDashas(cached.dashas ?? []);
          setPanchanga(cached.panchanga ?? null);
          setShadbala(cached.shadbala ?? []);
          setAshtakavarga(cached.ashtakavarga ?? null);
          setLoading(false);
        }

        const birth = birthDataOf(p);
        const [chartRes, vargasRes, dashasRes, panchangaRes, shadbalaRes, ashtakavargaRes] =
          await Promise.allSettled([
            fetchChart(birth),
            fetchVargas(birth, [...ALL_VARGAS]),
            fetchDashas(birth, 3),
            fetchPanchanga(birth),
            fetchShadbala(birth),
            fetchAshtakavarga(birth),
          ]);
        if (cancelled) return;
        const fresh: ChartReadingCache = {
          chart: chartRes.status === "fulfilled" ? chartRes.value : null,
          vargas: vargasRes.status === "fulfilled" ? vargasRes.value : [],
          dashas: dashasRes.status === "fulfilled" ? dashasRes.value : [],
          panchanga: panchangaRes.status === "fulfilled" ? panchangaRes.value : null,
          shadbala: shadbalaRes.status === "fulfilled" ? shadbalaRes.value : [],
          ashtakavarga:
            ashtakavargaRes.status === "fulfilled" ? ashtakavargaRes.value : null,
        };
        if (chartRes.status === "fulfilled") setChart(chartRes.value);
        else if (!cached) setError(chartRes.reason?.message ?? "Chart computation failed.");
        if (vargasRes.status === "fulfilled") setVargas(vargasRes.value);
        if (dashasRes.status === "fulfilled") setDashas(dashasRes.value);
        if (panchangaRes.status === "fulfilled") setPanchanga(panchangaRes.value);
        if (shadbalaRes.status === "fulfilled") setShadbala(shadbalaRes.value);
        if (ashtakavargaRes.status === "fulfilled") setAshtakavarga(ashtakavargaRes.value);
        if (chartRes.status === "fulfilled") void saveReading(p.id, "chart", fresh);
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

  if (loading) {
    return <p className="text-sm text-slate-500">Computing chart…</p>;
  }

  if (error && !chart) {
    return (
      <div className="card p-8 text-center">
        <p className="text-red-300">{error}</p>
        <p className="mt-2 text-sm text-slate-500">
          Ensure the calculation engine is running (API_BASE_URL, default
          http://localhost:8000).
        </p>
        <Link href="/dashboard" className="btn-ghost mt-4">
          ← Back to profiles
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-100">
            {profile?.label} — Chart
          </h1>
          {chart && (
            <p className="mt-1 text-sm text-slate-400">
              Lagna: {signName(chart.lagna.sign)}{" "}
              {fmtDegMin(chart.lagna.degInSign)}
              {chart.lagna.nakshatra && ` · ${chart.lagna.nakshatra}`}
              {chart.lagna.pada ? ` pada ${chart.lagna.pada}` : ""}
            </p>
          )}
          {profile?.rectified_time && (
            <p className="mt-1 text-xs text-gold-400">
              Using rectified time {profile.rectified_time.slice(0, 5)} (recorded:{" "}
              {profile.birth_time}) —{" "}
              <Link
                href={`/dashboard/rectify/${params.id}`}
                className="underline hover:text-gold-300"
              >
                review
              </Link>
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button href={`/dashboard/predictions/${params.id}`} size="sm" icon={Sparkles}>
            Predictions
          </Button>
          <Button href={`/dashboard/chat/${params.id}`} size="sm" icon={MessageCircleQuestion}>
            Ask the chart
          </Button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,26rem)_1fr]">
        {/* Chart + varga selector */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Tabs options={QUICK_VARGAS} value={selectedVarga as (typeof QUICK_VARGAS)[number]} onChange={setSelectedVarga} />
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
                {vargas.length === 0
                  ? "Varga data unavailable — engine did not return divisional charts."
                  : `No data for ${selectedVarga}.`}
              </p>
            </div>
          )}
          {selectedVarga !== "D1" && (
            <p className="text-xs text-slate-500">
              {VARGA_LABELS[selectedVarga] ?? ""}
            </p>
          )}
        </div>

        {/* Planet table */}
        <div className="card overflow-x-auto p-4">
          <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
            Graha positions
          </h2>
          {chart && (
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead>
                <tr className="border-b border-night-600 text-xs uppercase tracking-wider text-slate-500">
                  <th className="py-2 pr-3">Graha</th>
                  <th className="py-2 pr-3">Sign</th>
                  <th className="py-2 pr-3">Degree</th>
                  <th className="py-2 pr-3">Nakshatra</th>
                  <th className="py-2 pr-3">Dignity</th>
                  <th className="py-2">Flags</th>
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
                    <td className="py-2 pr-3 capitalize text-slate-300">
                      {p.dignity ?? "—"}
                    </td>
                    <td className="py-2">
                      <span className="flex gap-1">
                        {p.retrograde && (
                          <span className="badge-gold">retro</span>
                        )}
                        {p.combust && (
                          <span className="chip border-red-800/60 text-red-300">
                            combust
                          </span>
                        )}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Panchanga */}
      {panchanga && (
        <div className="card p-5">
          <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
            Panchāṅga at birth
          </h2>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3 lg:grid-cols-6">
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">
                Tithi
              </dt>
              <dd className="mt-0.5 text-slate-200">
                {panchanga.tithi.paksha} {panchanga.tithi.name}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">
                Vara
              </dt>
              <dd className="mt-0.5 text-slate-200">
                {panchanga.vara.name}
                {panchanga.vara.lord && (
                  <span className="text-xs text-slate-500">
                    {" "}
                    · {panchanga.vara.lord}
                  </span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">
                Nakshatra
              </dt>
              <dd className="mt-0.5 text-slate-200">
                {panchanga.nakshatra.name}
                {panchanga.nakshatra.pada
                  ? ` · pada ${panchanga.nakshatra.pada}`
                  : ""}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">
                Yoga
              </dt>
              <dd className="mt-0.5 text-slate-200">{panchanga.yoga.name}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">
                Karana
              </dt>
              <dd className="mt-0.5 text-slate-200">{panchanga.karana.name}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-slate-500">
                Sunrise / Sunset
              </dt>
              <dd className="mt-0.5 font-mono text-xs text-slate-300">
                {panchanga.sunrise ? panchanga.sunrise.slice(11, 16) : "—"} /{" "}
                {panchanga.sunset ? panchanga.sunset.slice(11, 16) : "—"}
              </dd>
            </div>
          </dl>
        </div>
      )}

      {/* Shadbala strength bars */}
      {shadbala.length > 0 && (
        <div className="card p-5">
          <h2 className="mb-1 font-display text-lg font-semibold text-gold-300">
            Shadbala — six-fold strength
          </h2>
          <p className="mb-4 text-xs text-slate-500">
            Total strength in rupas vs. the classical minimum per graha
            (B.V. Raman convention). Green: sufficient; amber: borderline
            (&ge;80% of required); red: weak.
          </p>
          <div className="space-y-3">
            {shadbala.map((row) => {
              const barPct = Math.min((row.totalRupas / 10) * 100, 100);
              const reqPct = Math.min((row.requiredRupas / 10) * 100, 100);
              const barColor = row.sufficient
                ? "bg-emerald-500"
                : row.ratio >= 0.8
                  ? "bg-amber-500"
                  : "bg-red-500";
              return (
                <div key={row.planet} className="flex items-center gap-3">
                  <span className="w-16 shrink-0 text-sm font-semibold text-slate-200">
                    {row.planet}
                  </span>
                  <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-night-700">
                    <div
                      className={`h-full rounded-full ${barColor}`}
                      style={{ width: `${barPct}%` }}
                    />
                    <div
                      className="absolute inset-y-0 w-0.5 bg-slate-300/70"
                      style={{ left: `${reqPct}%` }}
                      title={`Required: ${row.requiredRupas} rupas`}
                    />
                  </div>
                  <span className="w-28 shrink-0 text-right font-mono text-xs text-slate-400">
                    {row.totalRupas.toFixed(2)} / {row.requiredRupas.toFixed(1)}{" "}
                    <span
                      className={
                        row.sufficient ? "text-emerald-400" : "text-red-300"
                      }
                    >
                      ({row.ratio.toFixed(2)}×)
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-[11px] text-slate-600">
            Sthana · Dig · Kala · Cheshta · Naisargika · Drik — 60 virupas = 1
            rupa. Tick marks the required minimum.
          </p>
        </div>
      )}

      {/* Ashtakavarga */}
      {ashtakavarga && (
        <Card
          icon={Grid3x3}
          title="Aṣṭakavarga"
          subtitle="Bindus per graha per sign (BAV), plus the combined Sarvāṣṭakavarga (SAV) row — ≥28 SAV or ≥5 BAV is classically strong for a transit."
        >
          <AshtakavargaTable data={ashtakavarga} />
        </Card>
      )}

      {/* Dasha tree */}
      <div className="card p-5">
        <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
          Vimśottarī daśās
        </h2>
        <DashaTree periods={dashas} />
      </div>
    </div>
  );
}
