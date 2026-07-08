"use client";

import { useEffect, useState } from "react";
import {
  Clock3,
  MessageCircleQuestion,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import ProfileForm from "@/components/ProfileForm";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import {
  deleteProfile,
  listProfiles,
  saveProfile,
} from "@/lib/profiles";
import {
  fetchDashas,
  fetchPanchanga,
  fetchPredictions,
  type DashaPeriod,
  type PanchangaData,
  type Prediction,
} from "@/lib/api";
import { getLatestReading, saveReading } from "@/lib/readings";
import type { BirthProfile, BirthProfileInput } from "@/lib/types";
import { birthDataOf } from "@/lib/types";
import { fmtDate } from "@/lib/jyotisha";

interface TodayReadingCache {
  dashas: DashaPeriod[];
  panchanga: PanchangaData | null;
  predictions: Prediction[];
}

function isTodayReadingCache(v: unknown): v is TodayReadingCache {
  return !!v && typeof v === "object" && "dashas" in v;
}

function getActiveDashaPath(dashas: DashaPeriod[]): DashaPeriod[] {
  const path: DashaPeriod[] = [];
  let current: DashaPeriod | undefined = dashas.find((d) => d.active);
  if (!current) return path;
  path.push(current);

  while (current?.children.length) {
    const child: DashaPeriod | undefined = current.children.find((c) => c.active);
    if (!child) break;
    path.push(child);
    current = child;
  }
  return path;
}

function getTopPredictions(predictions: Prediction[]): Prediction[] {
  return predictions
    .sort((a, b) => Math.abs(b.score) - Math.abs(a.score))
    .slice(0, 3);
}

function ScoreChip({ score }: { score: number }) {
  const isPositive = score >= 0;
  const intensity = Math.abs(score);
  const bgClass = isPositive
    ? intensity > 0.5
      ? "bg-gold-600/20 border-gold-600/60 text-gold-300"
      : intensity > 0.15
        ? "bg-gold-600/10 border-gold-600/40 text-gold-200"
        : "bg-amber-900/10 border-amber-700/40 text-amber-200"
    : intensity > 0.5
      ? "bg-red-900/20 border-red-800/60 text-red-300"
      : intensity > 0.15
        ? "bg-red-900/10 border-red-800/40 text-red-200"
        : "bg-amber-900/10 border-amber-700/40 text-amber-200";
  return (
    <span className={`chip ${bgClass}`}>
      {score >= 0 ? "+" : ""}
      {score.toFixed(2)}
    </span>
  );
}

function LoadingPulse() {
  return <div className="h-12 animate-pulse rounded bg-night-700" />;
}

export default function DashboardPage() {
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [profilesLoading, setProfilesLoading] = useState(true);
  const [profilesError, setProfilesError] = useState<string | null>(null);

  const [todayData, setTodayData] = useState<TodayReadingCache | null>(null);
  const [todayLoading, setTodayLoading] = useState(false);
  const [todayError, setTodayError] = useState<string | null>(null);

  const [editing, setEditing] = useState<BirthProfile | null>(null);
  const [creating, setCreating] = useState(false);

  async function refresh() {
    try {
      const list = await listProfiles();
      setProfiles(list);
      setProfilesError(null);

      const primary = list.find((p) => p.is_self) || list[0];
      if (primary) {
        await loadTodayData(primary);
      }
    } catch (err) {
      setProfilesError(
        err instanceof Error ? err.message : "Failed to load profiles."
      );
    } finally {
      setProfilesLoading(false);
    }
  }

  async function loadTodayData(profile: BirthProfile) {
    setTodayLoading(true);
    setTodayError(null);
    try {
      const cached = await getLatestReading(profile.id, "today");
      if (isTodayReadingCache(cached)) {
        setTodayData(cached);
        setTodayLoading(false);
      }

      const birth = birthDataOf(profile);
      // Panchanga is computed for the moment it's given — for the "Today"
      // card that must be *now* at the profile's place, not the birth moment.
      const now = new Date();
      const utcMs = now.getTime() + now.getTimezoneOffset() * 60_000;
      const local = new Date(utcMs + birth.tz_offset * 3_600_000);
      const todayProbe = {
        ...birth,
        date: local.toISOString().slice(0, 10),
        time: local.toISOString().slice(11, 16),
      };
      const [dashasRes, panchangaRes, predictionsRes] =
        await Promise.allSettled([
          fetchDashas(birth, 2),
          fetchPanchanga(todayProbe),
          fetchPredictions(birth),
        ]);

      const dashas =
        dashasRes.status === "fulfilled" ? dashasRes.value : [];
      const panchanga =
        panchangaRes.status === "fulfilled" ? panchangaRes.value : null;
      const predictions =
        predictionsRes.status === "fulfilled" ? predictionsRes.value : [];

      const data: TodayReadingCache = { dashas, panchanga, predictions };
      setTodayData(data);

      void saveReading(profile.id, "today", data);
    } catch (err) {
      setTodayError(
        err instanceof Error ? err.message : "Failed to load today's data."
      );
    } finally {
      setTodayLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleSave(input: BirthProfileInput) {
    await saveProfile(input);
    setCreating(false);
    setEditing(null);
    await refresh();
  }

  async function handleDelete(p: BirthProfile) {
    if (!window.confirm(`Delete profile "${p.label}"?`)) return;
    await deleteProfile(p.id);
    await refresh();
  }

  const showForm = creating || editing !== null;
  const primaryProfile = profiles.find((p) => p.is_self) || profiles[0];
  const activeDashaPath = todayData ? getActiveDashaPath(todayData.dashas) : [];
  const topPredictions = todayData
    ? getTopPredictions(todayData.predictions)
    : [];

  return (
    <div className="space-y-8">
      {primaryProfile && (
        <div className="space-y-4">
          <h2 className="font-display text-lg font-semibold text-gold-300">
            Today's snapshot
            {primaryProfile.is_self && (
              <span className="badge-gold ml-2 align-middle">self</span>
            )}
          </h2>

          {todayError && !todayData && (
            <div className="card p-4">
              <p className="text-sm text-slate-400">{todayError}</p>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Card title="Active dasha path" className="sm:col-span-1">
              {todayLoading && !todayData ? (
                <LoadingPulse />
              ) : activeDashaPath.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {activeDashaPath.map((dasha, i) => (
                    <div key={i}>
                      <span
                        className={`inline-flex items-center rounded-lg px-3 py-1.5 text-sm font-semibold ${
                          i === 0
                            ? "border border-gold-600/60 bg-gold-600/10 text-gold-200"
                            : "border border-night-500 bg-night-800 text-slate-200"
                        }`}
                      >
                        {dasha.lord}
                      </span>
                      {i < activeDashaPath.length - 1 && (
                        <span className="mx-1.5 text-slate-500">›</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500">No dasha data available.</p>
              )}
              {activeDashaPath[0] && (
                <p className="mt-2 text-xs text-slate-500">
                  Ends {fmtDate(activeDashaPath[0].end)}
                </p>
              )}
            </Card>

            <Card title="Panchanga" className="sm:col-span-1">
              {todayLoading && !todayData ? (
                <LoadingPulse />
              ) : todayData?.panchanga ? (
                <div className="space-y-2 text-sm">
                  <div>
                    <p className="text-xs text-slate-500">Tithi</p>
                    <p className="text-slate-200">
                      {todayData.panchanga.tithi.name}{" "}
                      <span className="text-slate-500">
                        ({todayData.panchanga.tithi.paksha})
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Nakshatra</p>
                    <p className="text-slate-200">
                      {todayData.panchanga.nakshatra.name}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Vara</p>
                    <p className="text-slate-200">
                      {todayData.panchanga.vara.name}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500">
                  No panchanga data available.
                </p>
              )}
            </Card>

            <Card
              title="Top life areas"
              className="sm:col-span-2 lg:col-span-1"
            >
              {todayLoading && !todayData ? (
                <LoadingPulse />
              ) : topPredictions.length > 0 ? (
                <div className="space-y-2">
                  {topPredictions.map((pred, i) => (
                    <div key={i} className="flex items-center justify-between gap-2">
                      <span className="text-sm capitalize text-slate-300">
                        {pred.area}
                      </span>
                      <ScoreChip score={pred.score} />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500">
                  No prediction data available.
                </p>
              )}
            </Card>
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="font-display text-2xl font-bold text-slate-100">
            Birth profiles
          </h1>
          {!showForm && (
            <Button
              variant="gold"
              icon={Plus}
              onClick={() => setCreating(true)}
            >
              New profile
            </Button>
          )}
        </div>

        {profilesError && (
          <p className="rounded-lg border border-red-800/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
            {profilesError}
          </p>
        )}

        {showForm && (
          <ProfileForm
            initial={editing}
            onSave={handleSave}
            onCancel={() => {
              setCreating(false);
              setEditing(null);
            }}
          />
        )}

        {profilesLoading ? (
          <p className="text-sm text-slate-500">Loading profiles...</p>
        ) : profiles.length === 0 && !showForm ? (
          <div className="card p-10 text-center">
            <p className="mb-2 font-display text-lg text-slate-200">
              Welcome to Kundali
            </p>
            <p className="text-slate-400">
              Add your birth details to get started with personalized
              astrological insights.
            </p>
            <Button
              variant="gold"
              icon={Plus}
              className="mt-4"
              onClick={() => setCreating(true)}
            >
              Add your birth details
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {profiles.map((p) => (
              <div key={p.id} className="card animate-fade-up p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-display text-lg font-semibold text-slate-100">
                      {p.label}
                      {p.is_self && (
                        <span className="badge-gold ml-2 align-middle">
                          self
                        </span>
                      )}
                    </h2>
                    <p className="mt-1 text-sm text-slate-400">
                      {fmtDate(p.birth_date)} ·{" "}
                      {p.rectified_time ? (
                        <>
                          <span className="text-slate-600 line-through">
                            {p.birth_time}
                          </span>{" "}
                          <span className="font-semibold text-gold-300">
                            {p.rectified_time.slice(0, 5)} (rectified)
                          </span>
                        </>
                      ) : (
                        p.birth_time
                      )}{" "}
                      (UTC
                      {p.tz_offset >= 0 ? "+" : ""}
                      {p.tz_offset})
                    </p>
                    <p className="text-xs text-slate-500">
                      {p.place_name || "—"} · {p.lat.toFixed(4)},{" "}
                      {p.lon.toFixed(4)}
                      {p.events.length > 0 &&
                        ` · ${p.events.length} life event${
                          p.events.length > 1 ? "s" : ""
                        }`}
                    </p>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    href={`/dashboard/ask/${p.id}`}
                    variant="gold"
                    size="sm"
                  >
                    Instant answers
                  </Button>
                  <Button href={`/dashboard/chart/${p.id}`} size="sm">
                    Chart
                  </Button>
                  <Button
                    href={`/dashboard/predictions/${p.id}`}
                    size="sm"
                    icon={Sparkles}
                  >
                    Guidance
                  </Button>
                  <Button
                    href={`/dashboard/chat/${p.id}`}
                    size="sm"
                    icon={MessageCircleQuestion}
                  >
                    LLM chat
                  </Button>
                  <Button
                    href={`/dashboard/rectify/${p.id}`}
                    size="sm"
                    icon={Clock3}
                  >
                    Rectify time
                  </Button>
                  <Button
                    size="sm"
                    icon={Pencil}
                    onClick={() => {
                      setCreating(false);
                      setEditing(p);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    icon={Trash2}
                    onClick={() => handleDelete(p)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
