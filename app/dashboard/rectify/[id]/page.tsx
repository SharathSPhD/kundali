"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock3 } from "lucide-react";
import {
  fetchRectification,
  type RectificationCandidate,
  type RectificationResult,
} from "@/lib/api";
import { getProfile, setRectifiedTime } from "@/lib/profiles";
import type { BirthProfile } from "@/lib/types";
import { RECTIFICATION_EVENT_TYPE, birthDataOf } from "@/lib/types";
import { signName } from "@/lib/jyotisha";

const EVENT_LABELS: Record<string, string> = {
  marriage: "Marriage",
  child_birth: "Child birth",
  career_start: "Career start",
  promotion: "Promotion",
  relocation: "Relocation",
  parent_death: "Parent's death",
  health_event: "Health event",
  other: "Other",
};

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (score / max) * 100)) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-night-700">
      <div
        className="h-full rounded-full bg-gradient-to-r from-gold-600 to-gold-400"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function CandidateCard({
  candidate,
  rank,
  isApplied,
  onApply,
  applying,
}: {
  candidate: RectificationCandidate;
  rank: number;
  isApplied: boolean;
  onApply: () => void;
  applying: boolean;
}) {
  const [open, setOpen] = useState(false);
  const matchedEvents = candidate.events.filter((e) => e.matched.length > 0);
  const vs = candidate.vargaSensitivity;
  const vargaFlagged = vs?.nearD9Boundary || vs?.nearD10Boundary;
  return (
    <div
      className={`card animate-fade-up p-5 ${
        rank === 0 ? "border-gold-500/70 bg-gold-600/5" : ""
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-display text-xl font-semibold text-slate-100">
            {candidate.time.slice(0, 5)}
            {rank === 0 && (
              <span className="badge-gold ml-2 align-middle">best match</span>
            )}
            {isApplied && (
              <span className="chip ml-2 border-gold-600/60 text-gold-300">
                applied
              </span>
            )}
            {vargaFlagged && (
              <span
                className="chip ml-2 border-amber-700/60 text-amber-300"
                title={`Within ${vs.proximityMinutes} min of a ${
                  vs.nearD9Boundary && vs.nearD10Boundary
                    ? "D9/D10"
                    : vs.nearD9Boundary
                      ? "D9 (navamsa)"
                      : "D10 (dashamsa)"
                } lagna-sign boundary — small timing errors could flip the divisional chart here.`}
              >
                near varga boundary
              </span>
            )}
          </p>
          <p className="text-xs text-slate-500">
            {candidate.offsetMinutes === 0
              ? "as recorded"
              : `${candidate.offsetMinutes > 0 ? "+" : ""}${candidate.offsetMinutes} min from recorded time`}
            {" · "}
            Lagna {signName(candidate.lagnaSign)} {candidate.lagnaDegree.toFixed(2)}°
          </p>
        </div>
        <button
          className="btn-gold px-3 py-1.5 text-xs disabled:opacity-50"
          onClick={onApply}
          disabled={applying || isApplied}
        >
          {isApplied ? "Applied" : applying ? "Applying…" : "Use this time"}
        </button>
      </div>

      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
          <span>Event-match score</span>
          <span>
            {candidate.score.toFixed(2)} / {candidate.maxScore.toFixed(2)}
          </span>
        </div>
        <ScoreBar score={candidate.score} max={candidate.maxScore} />
      </div>

      {candidate.events.length > 0 && (
        <div className="mt-3">
          <button
            className="text-xs font-medium text-gold-400 hover:underline"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Hide" : "Show"} per-event detail ({matchedEvents.length}/
            {candidate.events.length} events matched)
          </button>
          {open && (
            <ul className="mt-2 space-y-2 border-l border-gold-700/40 pl-3">
              {candidate.events.map((e, i) => (
                <li key={i} className="text-xs leading-relaxed text-slate-400">
                  <span className="font-semibold text-slate-300">
                    {e.event}
                  </span>{" "}
                  {e.generic && (
                    <span
                      className="chip mr-1 border-amber-700/60 py-0 text-[10px] text-amber-300"
                      title="Unrecognized event type — scored generically, low-signal"
                    >
                      generic
                    </span>
                  )}
                  ({e.date}) — active {e.activeMahadasha ?? "?"}
                  {e.activeAntardasha ? `-${e.activeAntardasha}` : ""}
                  {e.activePratyantardasha ? `-${e.activePratyantardasha}` : ""} dasha.{" "}
                  {e.matched.length > 0 ? (
                    <span className="text-gold-400">
                      {e.matched.join("; ")}
                    </span>
                  ) : (
                    <span className="text-slate-600">no dasha-lord match</span>
                  )}
                  {e.whyRelevant.length > 0 && (
                    <span className="text-slate-600">
                      {" "}
                      (relevant: {e.whyRelevant.join("; ")})
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default function RectifyPage({ params }: { params: { id: string } }) {
  const [profile, setProfile] = useState<BirthProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [windowMinutes, setWindowMinutes] = useState(60);
  const [stepMinutes, setStepMinutes] = useState(2);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RectificationResult | null>(null);
  const [applyingTime, setApplyingTime] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const p = await getProfile(params.id);
        if (!cancelled) {
          if (!p) setError("Profile not found.");
          else setProfile(p);
        }
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

  async function runRectification() {
    if (!profile) return;
    setRunning(true);
    setError(null);
    setNotice(null);
    try {
      const birth = birthDataOf(profile);
      const events = profile.events
        .filter((e) => e.event_date)
        .map((e) => ({
          type: RECTIFICATION_EVENT_TYPE[e.event_type] ?? "other",
          date: e.event_date,
          note: e.note,
        }));
      const res = await fetchRectification(
        birth,
        windowMinutes,
        events,
        stepMinutes
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rectification failed.");
    } finally {
      setRunning(false);
    }
  }

  async function applyTime(time: string) {
    if (!profile) return;
    setApplyingTime(time);
    setError(null);
    try {
      const updated = await setRectifiedTime(profile.id, time);
      setProfile(updated);
      setNotice(
        `Rectified time ${time.slice(0, 5)} applied — charts, dashas and predictions for this profile now use it.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply time.");
    } finally {
      setApplyingTime(null);
    }
  }

  async function clearRectifiedTime() {
    if (!profile) return;
    setApplyingTime("__clear__");
    try {
      const updated = await setRectifiedTime(profile.id, null);
      setProfile(updated);
      setNotice("Rectified time cleared — the recorded birth time is used again.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear.");
    } finally {
      setApplyingTime(null);
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;
  if (!profile) {
    return (
      <div className="card p-6">
        <p className="text-sm text-red-300">{error ?? "Profile not found."}</p>
        <Link href="/dashboard" className="btn-ghost mt-4 inline-block px-3 py-1.5 text-xs">
          ← Back to profiles
        </Link>
      </div>
    );
  }

  const eventsWithDates = profile.events.filter((e) => e.event_date);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="flex items-center gap-2 font-display text-2xl font-bold text-slate-100">
          <Clock3 className="h-5 w-5 shrink-0 text-gold-400" aria-hidden />
          {profile.label} — Birth-time rectification
        </h1>
        <Link href="/dashboard" className="btn-ghost px-3 py-1.5 text-xs">
          ← Profiles
        </Link>
      </div>

      <p className="text-xs leading-relaxed text-slate-500">
        Scans candidate birth times around the recorded time and scores each
        one by how well its Vimshottari daśā periods explain your life
        events (marriage in a 7th-house/Venus period, career milestones in a
        10th-house period, etc). This corroborates — it does not replace —
        an accurate memory or birth record; treat a clear winner as a strong
        hint, not proof.
      </p>

      <div className="card p-5">
        <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
          Current birth time
        </h2>
        <p className="text-sm text-slate-300">
          Recorded: <span className="font-semibold">{profile.birth_time}</span>
          {profile.rectified_time && (
            <>
              {" · "}Rectified:{" "}
              <span className="font-semibold text-gold-300">
                {profile.rectified_time.slice(0, 5)}
              </span>{" "}
              (used by chart/predictions/chat for this profile)
            </>
          )}
        </p>
        {profile.rectified_time && (
          <button
            className="btn-ghost mt-3 px-3 py-1.5 text-xs text-red-400 hover:border-red-800"
            onClick={clearRectifiedTime}
            disabled={applyingTime === "__clear__"}
          >
            {applyingTime === "__clear__" ? "Clearing…" : "Clear rectified time"}
          </button>
        )}
      </div>

      <div className="card p-5">
        <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
          Life events used for scoring
        </h2>
        {eventsWithDates.length === 0 ? (
          <p className="text-sm text-slate-500">
            No life events on this profile yet. Add at least one (marriage,
            career start, relocation, etc.) on the{" "}
            <Link href="/dashboard" className="text-gold-400 hover:underline">
              profile edit form
            </Link>{" "}
            — rectification has nothing to score against without them.
          </p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {eventsWithDates.map((e, i) => (
              <li key={e.id ?? i} className="chip">
                {EVENT_LABELS[e.event_type] ?? e.event_type} — {e.event_date}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card p-5">
        <h2 className="mb-3 font-display text-lg font-semibold text-gold-300">
          Search window
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="rect-window">
              Window (± minutes)
            </label>
            <input
              id="rect-window"
              type="number"
              className="input"
              min={2}
              max={360}
              value={windowMinutes}
              onChange={(e) => setWindowMinutes(Number(e.target.value))}
            />
          </div>
          <div>
            <label className="label" htmlFor="rect-step">
              Step (minutes)
            </label>
            <input
              id="rect-step"
              type="number"
              className="input"
              min={1}
              max={30}
              value={stepMinutes}
              onChange={(e) => setStepMinutes(Number(e.target.value))}
            />
          </div>
          <div className="flex items-end">
            <button
              className="btn-gold w-full disabled:opacity-50"
              onClick={runRectification}
              disabled={running || eventsWithDates.length === 0}
            >
              {running ? "Scanning…" : "Run rectification"}
            </button>
          </div>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Scans {windowMinutes * 2 / stepMinutes + 1 || 0} candidate times,
          &plusmn;{windowMinutes} minutes around {profile.birth_time} in{" "}
          {stepMinutes}-minute steps.
        </p>
      </div>

      {error && (
        <p className="rounded-lg border border-red-800/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}
      {notice && (
        <p className="rounded-lg border border-gold-600/60 bg-gold-600/10 px-3 py-2 text-sm text-gold-200">
          {notice}
        </p>
      )}

      {result && (
        <div className="space-y-4">
          {result.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-700/50 bg-amber-950/20 px-3 py-2 text-xs text-amber-300">
              <p className="font-semibold">
                {result.ignoredEventCount} event
                {result.ignoredEventCount === 1 ? "" : "s"} scored generically:
              </p>
              <ul className="mt-1 list-inside list-disc space-y-0.5">
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span>
              Confidence:{" "}
              <span
                className={
                  result.confidence >= 0.5
                    ? "font-semibold text-emerald-400"
                    : result.confidence >= 0.2
                      ? "font-semibold text-amber-400"
                      : "font-semibold text-red-400"
                }
              >
                {(result.confidence * 100).toFixed(0)}%
              </span>
            </span>
            {result.tieCount > 1 && (
              <span className="chip border-amber-700/60 text-amber-300">
                {result.tieCount} candidates tied at the top score
              </span>
            )}
            {result.sensitivityToStep.likelyChangesTop && (
              <span title={result.sensitivityToStep.note} className="chip border-amber-700/60 text-amber-300">
                sensitive to step size
              </span>
            )}
          </div>
          <h2 className="font-display text-lg font-semibold text-slate-100">
            {result.candidates.length} ranked candidate
            {result.candidates.length === 1 ? "" : "s"}
          </h2>
          {result.candidates.map((c, i) => (
            <CandidateCard
              key={`${c.time}-${c.offsetMinutes}`}
              candidate={c}
              rank={i}
              isApplied={
                !!profile.rectified_time &&
                profile.rectified_time.slice(0, 8) === c.time.slice(0, 8)
              }
              onApply={() => applyTime(c.time)}
              applying={applyingTime === c.time}
            />
          ))}
        </div>
      )}
    </div>
  );
}
