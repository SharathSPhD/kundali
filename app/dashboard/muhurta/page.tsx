"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CalendarCheck, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import Card from "@/components/ui/Card";
import { fetchMuhurta, type MuhurtaDay, type MuhurtaResult } from "@/lib/api";
import { listProfiles } from "@/lib/profiles";
import { birthDataOf, type BirthProfile } from "@/lib/types";

const ACTIVITIES = [
  { key: "marriage", label: "Marriage / engagement" },
  { key: "new_venture", label: "New venture / launch" },
  { key: "travel", label: "Travel / journey" },
  { key: "education", label: "Education / admission" },
  { key: "housewarming", label: "Housewarming (griha pravesh)" },
  { key: "medical", label: "Medical procedure" },
];

function scoreColor(score: number): string {
  if (score >= 1.5) return "text-gold-300 border-gold-500/40 bg-gold-500/10";
  if (score >= 0) return "text-slate-200 border-night-500 bg-night-700/40";
  return "text-rose-300 border-rose-500/30 bg-rose-500/10";
}

function DayCard({ day, rank }: { day: MuhurtaDay; rank: number }) {
  const [open, setOpen] = useState(false);
  const d = new Date(day.date + "T12:00:00");
  const pretty = d.toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex h-8 w-8 items-center justify-center rounded-full border text-sm font-semibold ${scoreColor(day.score)}`}
            title={`score ${day.score.toFixed(2)}`}
          >
            {rank}
          </span>
          <div>
            <div className="font-medium text-slate-100">{pretty}</div>
            <div className="text-xs text-slate-400">
              {day.tithi} tithi · {day.nakshatra} nakshatra · {day.tara} tara
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {day.favorable && (
            <span className="chip border-gold-500/40 text-gold-300">
              <Sparkles className="h-3 w-3" aria-hidden /> favorable
            </span>
          )}
          <button
            className="btn-ghost px-2 py-1 text-xs"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            why
          </button>
        </div>
      </div>
      {open && (
        <ul className="mt-3 space-y-1.5 border-t border-night-600/50 pt-3 text-sm">
          {day.reasons.map((r, i) => (
            <li key={i} className="flex flex-wrap items-baseline gap-x-2">
              <span
                className={
                  r.verdict === "favorable"
                    ? "text-gold-300"
                    : r.verdict === "unfavorable"
                      ? "text-rose-300"
                      : "text-slate-400"
                }
              >
                {r.verdict === "favorable" ? "✓" : r.verdict === "unfavorable" ? "✕" : "○"}
              </span>
              <span className="text-slate-300">{r.detail}</span>
              <span className="text-xs italic text-slate-500">{r.source}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function MuhurtaPage() {
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [profileId, setProfileId] = useState("");
  const [activity, setActivity] = useState("new_venture");
  const [days, setDays] = useState(30);
  const [result, setResult] = useState<MuhurtaResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProfiles().then((ps) => {
      setProfiles(ps);
      const self = ps.find((p) => p.is_self) ?? ps[0];
      if (self) setProfileId(self.id);
    });
  }, []);

  const profile = useMemo(
    () => profiles.find((p) => p.id === profileId) ?? null,
    [profiles, profileId]
  );

  async function run() {
    if (!profile) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await fetchMuhurta(birthDataOf(profile), activity, undefined, days));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Muhurta scan failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <CalendarCheck className="h-6 w-6 text-gold-400" aria-hidden />
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-100">Good days</h1>
          <p className="text-sm text-slate-400">
            Personalized electional timing (muhurta): upcoming days ranked for your
            undertaking, from your own janma nakshatra — every verdict shows its
            classical reason.
          </p>
        </div>
      </header>

      <Card className="p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Person</span>
            <select
              className="input w-full"
              value={profileId}
              onChange={(e) => setProfileId(e.target.value)}
            >
              {profiles.length === 0 && <option value="">— no profiles yet —</option>}
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label} ({p.birth_date})
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Undertaking</span>
            <select
              className="input w-full"
              value={activity}
              onChange={(e) => setActivity(e.target.value)}
            >
              {ACTIVITIES.map((a) => (
                <option key={a.key} value={a.key}>
                  {a.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Horizon</span>
            <select
              className="input w-full"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              <option value={14}>Next 2 weeks</option>
              <option value={30}>Next 30 days</option>
              <option value={60}>Next 60 days</option>
              <option value={90}>Next 90 days</option>
            </select>
          </label>
          <div className="flex items-end">
            <button className="btn-gold w-full justify-center" onClick={run} disabled={!profile || loading}>
              {loading ? "Scanning…" : "Find good days"}
            </button>
          </div>
        </div>
        {profiles.length === 0 && (
          <p className="mt-3 text-sm text-slate-400">
            Add a birth profile first on the{" "}
            <Link href="/dashboard" className="text-gold-300 underline">
              Home page
            </Link>
            .
          </p>
        )}
      </Card>

      {error && (
        <Card className="border-rose-500/30 p-4 text-sm text-rose-300">{error}</Card>
      )}

      {result && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-display text-lg font-semibold text-slate-100">
              Best days for {ACTIVITIES.find((a) => a.key === result.activity)?.label ?? result.activity}
            </h2>
            <span className="text-xs text-slate-500">
              janma nakshatra: {result.janma_nakshatra}
            </span>
          </div>
          <div className="space-y-3">
            {result.best.map((d, i) => (
              <DayCard key={d.date} day={d} rank={i + 1} />
            ))}
          </div>
          <p className="text-xs leading-relaxed text-slate-500">{result.note}</p>
        </section>
      )}
    </div>
  );
}
