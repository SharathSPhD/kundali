"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProfileForm from "@/components/ProfileForm";
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
          <button className="btn-gold" onClick={() => setCreating(true)}>
            + New profile
          </button>
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
          <button className="btn-gold mt-4" onClick={() => setCreating(true)}>
            Create your first profile
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {profiles.map((p) => (
            <div key={p.id} className="card p-5">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="font-display text-lg font-semibold text-slate-100">
                    {p.label}
                    {p.is_self && (
                      <span className="badge-gold ml-2 align-middle">self</span>
                    )}
                  </h2>
                  <p className="mt-1 text-sm text-slate-400">
                    {fmtDate(p.birth_date)} · {p.birth_time} (UTC
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
                <Link
                  href={`/dashboard/chart/${p.id}`}
                  className="btn-gold px-3 py-1.5 text-xs"
                >
                  Chart
                </Link>
                <Link
                  href={`/dashboard/predictions/${p.id}`}
                  className="btn-ghost px-3 py-1.5 text-xs"
                >
                  Predictions
                </Link>
                <Link
                  href={`/dashboard/chat/${p.id}`}
                  className="btn-ghost px-3 py-1.5 text-xs"
                >
                  Ask
                </Link>
                <button
                  className="btn-ghost px-3 py-1.5 text-xs"
                  onClick={() => {
                    setCreating(false);
                    setEditing(p);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  Edit
                </button>
                <button
                  className="btn-ghost px-3 py-1.5 text-xs text-red-400 hover:border-red-800"
                  onClick={() => handleDelete(p)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
