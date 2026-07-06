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
import {
  deleteProfile,
  listProfiles,
  saveProfile,
} from "@/lib/profiles";
import type { BirthProfile, BirthProfileInput } from "@/lib/types";
import { fmtDate } from "@/lib/jyotisha";

export default function DashboardPage() {
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<BirthProfile | null>(null);
  const [creating, setCreating] = useState(false);

  async function refresh() {
    try {
      setProfiles(await listProfiles());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profiles.");
    } finally {
      setLoading(false);
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
    if (!window.confirm(`Delete profile “${p.label}”?`)) return;
    await deleteProfile(p.id);
    await refresh();
  }

  const showForm = creating || editing !== null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-slate-100">
          Birth profiles
        </h1>
        {!showForm && (
          <Button variant="gold" icon={Plus} onClick={() => setCreating(true)}>
            New profile
          </Button>
        )}
      </div>

      {error && (
        <p className="rounded-lg border border-red-800/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
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

      {loading ? (
        <p className="text-sm text-slate-500">Loading profiles…</p>
      ) : profiles.length === 0 && !showForm ? (
        <div className="card p-10 text-center">
          <p className="text-slate-400">
            No birth profiles yet. Add one to compute a chart.
          </p>
          <Button
            variant="gold"
            icon={Plus}
            className="mt-4"
            onClick={() => setCreating(true)}
          >
            Create your first profile
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
                      <span className="badge-gold ml-2 align-middle">self</span>
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
                <Button href={`/dashboard/chart/${p.id}`} variant="gold" size="sm">
                  Chart
                </Button>
                <Button href={`/dashboard/predictions/${p.id}`} size="sm" icon={Sparkles}>
                  Predictions
                </Button>
                <Button href={`/dashboard/chat/${p.id}`} size="sm" icon={MessageCircleQuestion}>
                  Ask
                </Button>
                <Button href={`/dashboard/rectify/${p.id}`} size="sm" icon={Clock3}>
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
  );
}
