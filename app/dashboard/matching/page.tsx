"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchMatching,
  type MangalDoshaSide,
  type MatchingData,
} from "@/lib/api";
import { listProfiles } from "@/lib/profiles";
import type { BirthData, BirthProfile } from "@/lib/types";
import { birthDataOf } from "@/lib/types";

const MANUAL = "__manual__";

interface ManualBirth {
  date: string;
  time: string;
  lat: string;
  lon: string;
  tz_offset: string;
}

const EMPTY_MANUAL: ManualBirth = {
  date: "",
  time: "",
  lat: "",
  lon: "",
  tz_offset: "5.5",
};

function manualToBirth(m: ManualBirth): BirthData | null {
  if (!m.date || !m.time) return null;
  const lat = Number(m.lat);
  const lon = Number(m.lon);
  const tz = Number(m.tz_offset);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || !Number.isFinite(tz))
    return null;
  return { date: m.date, time: m.time, lat, lon, tz_offset: tz };
}

function PersonPicker({
  label,
  profiles,
  selected,
  onSelect,
  manual,
  onManual,
}: {
  label: string;
  profiles: BirthProfile[];
  selected: string;
  onSelect: (v: string) => void;
  manual: ManualBirth;
  onManual: (m: ManualBirth) => void;
}) {
  return (
    <div className="card space-y-3 p-4">
      <h3 className="font-display text-sm font-semibold uppercase tracking-wider text-gold-300">
        {label}
      </h3>
      <select
        className="input w-full text-sm"
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
        aria-label={`${label} profile`}
      >
        <option value="">— select profile —</option>
        {profiles.map((p) => (
          <option key={p.id} value={p.id}>
            {p.label} ({p.birth_date})
          </option>
        ))}
        <option value={MANUAL}>Manual entry…</option>
      </select>
      {selected === MANUAL && (
        <div className="grid grid-cols-2 gap-2 text-sm">
          <label className="col-span-1 text-xs text-slate-400">
            Date
            <input
              type="date"
              className="input mt-1 w-full"
              value={manual.date}
              onChange={(e) => onManual({ ...manual, date: e.target.value })}
            />
          </label>
          <label className="col-span-1 text-xs text-slate-400">
            Time
            <input
              type="time"
              step={1}
              className="input mt-1 w-full"
              value={manual.time}
              onChange={(e) => onManual({ ...manual, time: e.target.value })}
            />
          </label>
          <label className="text-xs text-slate-400">
            Latitude
            <input
              className="input mt-1 w-full"
              placeholder="12.9716"
              value={manual.lat}
              onChange={(e) => onManual({ ...manual, lat: e.target.value })}
            />
          </label>
          <label className="text-xs text-slate-400">
            Longitude
            <input
              className="input mt-1 w-full"
              placeholder="77.5946"
              value={manual.lon}
              onChange={(e) => onManual({ ...manual, lon: e.target.value })}
            />
          </label>
          <label className="col-span-2 text-xs text-slate-400">
            UTC offset (hours)
            <input
              className="input mt-1 w-full"
              placeholder="5.5"
              value={manual.tz_offset}
              onChange={(e) =>
                onManual({ ...manual, tz_offset: e.target.value })
              }
            />
          </label>
        </div>
      )}
    </div>
  );
}

function ScoreGauge({ total, max }: { total: number; max: number }) {
  const pct = max > 0 ? Math.max(0, Math.min(1, total / max)) : 0;
  const color =
    total >= 25 ? "bg-gold-400" : total >= 18 ? "bg-amber-600" : "bg-red-700";
  return (
    <div>
      <div className="flex items-baseline gap-2">
        <span className="font-display text-4xl font-bold text-gold-300">
          {total}
        </span>
        <span className="text-sm text-slate-400">/ {max} guna</span>
      </div>
      <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-night-700">
        <div
          className={`h-full rounded-full ${color} transition-all`}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
    </div>
  );
}

function MangalPanel({
  side,
  label,
}: {
  side: MangalDoshaSide;
  label: string;
}) {
  return (
    <div className="rounded-lg border border-night-600/60 p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-200">{label}</span>
        {side.effective ? (
          <span className="chip border-red-800/60 text-red-300">manglik</span>
        ) : side.manglik ? (
          <span className="badge-gold">cancelled</span>
        ) : (
          <span className="chip">no dosha</span>
        )}
      </div>
      <p className="mt-1 text-xs text-slate-400">
        Mars in house {side.houseFromLagna ?? "—"} from lagna
        {side.houseFromMoon ? `, ${side.houseFromMoon} from Moon` : ""}
      </p>
      {side.cancellations.length > 0 && (
        <ul className="mt-1 list-inside list-disc text-xs text-slate-500">
          {side.cancellations.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function MatchingPage() {
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [groomSel, setGroomSel] = useState("");
  const [brideSel, setBrideSel] = useState("");
  const [groomManual, setGroomManual] = useState<ManualBirth>(EMPTY_MANUAL);
  const [brideManual, setBrideManual] = useState<ManualBirth>(EMPTY_MANUAL);
  const [result, setResult] = useState<MatchingData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listProfiles()
      .then(setProfiles)
      .catch(() => setProfiles([]));
  }, []);

  const groomBirth = useMemo((): BirthData | null => {
    if (groomSel === MANUAL) return manualToBirth(groomManual);
    const p = profiles.find((x) => x.id === groomSel);
    return p ? birthDataOf(p) : null;
  }, [groomSel, groomManual, profiles]);

  const brideBirth = useMemo((): BirthData | null => {
    if (brideSel === MANUAL) return manualToBirth(brideManual);
    const p = profiles.find((x) => x.id === brideSel);
    return p ? birthDataOf(p) : null;
  }, [brideSel, brideManual, profiles]);

  async function runMatch() {
    if (!groomBirth || !brideBirth) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await fetchMatching(groomBirth, brideBirth));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Matching failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-100">
          Kundali matching
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Ashtakoota (36-guna) compatibility with Mangal dosha analysis.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <PersonPicker
          label="Groom"
          profiles={profiles}
          selected={groomSel}
          onSelect={setGroomSel}
          manual={groomManual}
          onManual={setGroomManual}
        />
        <PersonPicker
          label="Bride"
          profiles={profiles}
          selected={brideSel}
          onSelect={setBrideSel}
          manual={brideManual}
          onManual={setBrideManual}
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          className="btn-gold px-4 py-2 text-sm disabled:opacity-50"
          onClick={runMatch}
          disabled={!groomBirth || !brideBirth || loading}
        >
          {loading ? "Matching…" : "Compute match"}
        </button>
        {error && <p className="text-sm text-red-300">{error}</p>}
      </div>

      {result && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          {/* Kuta table */}
          <div className="card overflow-x-auto p-4">
            <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
              Guna Milan
            </h2>
            <table className="w-full min-w-[28rem] text-left text-sm">
              <thead>
                <tr className="border-b border-night-600 text-xs uppercase tracking-wider text-slate-500">
                  <th className="py-2 pr-3">Kuta</th>
                  <th className="py-2 pr-3">Points</th>
                  <th className="py-2">Detail</th>
                </tr>
              </thead>
              <tbody>
                {result.kutas.map((k) => (
                  <tr
                    key={k.name}
                    className="border-b border-night-700/50 last:border-0"
                  >
                    <td className="py-2 pr-3 font-semibold text-slate-200">
                      {k.name}
                    </td>
                    <td className="py-2 pr-3 font-mono">
                      <span
                        className={
                          k.points === k.max
                            ? "text-gold-300"
                            : k.points === 0
                              ? "text-red-300"
                              : "text-slate-300"
                        }
                      >
                        {k.points}
                      </span>
                      <span className="text-slate-500"> / {k.max}</span>
                    </td>
                    <td className="py-2 text-xs text-slate-400">{k.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Score + dosha */}
          <div className="space-y-4">
            <div className="card p-5">
              <ScoreGauge total={result.total} max={result.maxTotal} />
              <p className="mt-3 text-sm capitalize text-slate-200">
                Verdict:{" "}
                <span className="font-semibold text-gold-300">
                  {result.verdict}
                </span>
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Groom Moon: {result.groom.signName} · {result.groom.nakshatra}
                {result.groom.pada ? ` ${result.groom.pada}` : ""}
                <br />
                Bride Moon: {result.bride.signName} · {result.bride.nakshatra}
                {result.bride.pada ? ` ${result.bride.pada}` : ""}
              </p>
            </div>
            <div className="card space-y-3 p-5">
              <h2 className="font-display text-lg font-semibold text-gold-300">
                Mangal dosha
              </h2>
              <MangalPanel side={result.mangalDosha.groom} label="Groom" />
              <MangalPanel side={result.mangalDosha.bride} label="Bride" />
              <p className="text-xs text-slate-400">{result.mangalDosha.note}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
