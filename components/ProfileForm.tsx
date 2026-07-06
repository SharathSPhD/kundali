"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";
import type {
  BirthProfile,
  BirthProfileInput,
  LifeEvent,
  LifeEventType,
} from "@/lib/types";
import { LIFE_EVENT_TYPES } from "@/lib/types";

const EVENT_LABELS: Record<LifeEventType, string> = {
  marriage: "Marriage",
  child_birth: "Child birth",
  career_start: "Career start",
  promotion: "Promotion",
  relocation: "Relocation",
  parent_death: "Parent's death",
  health_event: "Health event",
  other: "Other",
};

interface Props {
  initial?: BirthProfile | null;
  onSave: (input: BirthProfileInput) => Promise<void>;
  onCancel: () => void;
}

export default function ProfileForm({ initial, onSave, onCancel }: Props) {
  const [label, setLabel] = useState(initial?.label ?? "");
  const [birthDate, setBirthDate] = useState(initial?.birth_date ?? "");
  const [birthTime, setBirthTime] = useState(initial?.birth_time ?? "");
  const [tzOffset, setTzOffset] = useState(
    initial ? String(initial.tz_offset) : "5.5"
  );
  const [placeName, setPlaceName] = useState(initial?.place_name ?? "");
  const [lat, setLat] = useState(initial ? String(initial.lat) : "");
  const [lon, setLon] = useState(initial ? String(initial.lon) : "");
  const [isSelf, setIsSelf] = useState(initial?.is_self ?? false);
  const [events, setEvents] = useState<LifeEvent[]>(initial?.events ?? []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateEvent(idx: number, patch: Partial<LifeEvent>) {
    setEvents((evs) => evs.map((e, i) => (i === idx ? { ...e, ...patch } : e)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const latN = Number(lat);
    const lonN = Number(lon);
    const tzN = Number(tzOffset);
    if (!label.trim()) return setError("Label is required.");
    if (!birthDate) return setError("Birth date is required.");
    if (!birthTime) return setError("Birth time is required.");
    if (!Number.isFinite(tzN) || tzN < -12 || tzN > 14)
      return setError("Timezone offset must be between -12 and +14 hours.");
    if (!Number.isFinite(latN) || latN < -90 || latN > 90)
      return setError("Latitude must be between -90 and 90.");
    if (!Number.isFinite(lonN) || lonN < -180 || lonN > 180)
      return setError("Longitude must be between -180 and 180.");

    setSaving(true);
    try {
      await onSave({
        id: initial?.id,
        label: label.trim(),
        birth_date: birthDate,
        birth_time: birthTime,
        tz_offset: tzN,
        place_name: placeName.trim(),
        lat: latN,
        lon: lonN,
        is_self: isSelf,
        // Rectification is a separate flow (/dashboard/rectify/[id]); a
        // routine profile edit here must not clobber an existing result.
        // If the raw birth time changes, the old rectification no longer
        // applies to it, so it's cleared rather than silently carried over.
        rectified_time:
          initial && birthTime === initial.birth_time
            ? initial.rectified_time
            : null,
        events: events.filter((ev) => ev.event_date),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card space-y-5 p-6">
      <h2 className="font-display text-xl font-semibold text-gold-300">
        {initial ? "Edit profile" : "New birth profile"}
      </h2>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="label" htmlFor="pf-label">Label</label>
          <input
            id="pf-label"
            className="input"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. Self, Amma, Client — R.S."
          />
        </div>
        <div>
          <label className="label" htmlFor="pf-date">Birth date</label>
          <input
            id="pf-date"
            type="date"
            className="input"
            value={birthDate}
            onChange={(e) => setBirthDate(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="pf-time">Birth time (local, 24h)</label>
          <input
            id="pf-time"
            type="time"
            className="input"
            value={birthTime}
            onChange={(e) => setBirthTime(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="pf-tz">Timezone offset (hours)</label>
          <input
            id="pf-tz"
            type="number"
            step="0.25"
            min={-12}
            max={14}
            className="input"
            value={tzOffset}
            onChange={(e) => setTzOffset(e.target.value)}
          />
          <p className="mt-1 text-xs text-slate-500">
            Offset from UTC at birth, e.g. 5.5 for IST, -5 for EST.
          </p>
        </div>
        <div>
          <label className="label" htmlFor="pf-place">Place name</label>
          <input
            id="pf-place"
            className="input"
            value={placeName}
            onChange={(e) => setPlaceName(e.target.value)}
            placeholder="e.g. Bengaluru, India"
          />
        </div>
        <div>
          <label className="label" htmlFor="pf-lat">Latitude</label>
          <input
            id="pf-lat"
            type="number"
            step="any"
            className="input"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            placeholder="12.9716"
          />
        </div>
        <div>
          <label className="label" htmlFor="pf-lon">Longitude</label>
          <input
            id="pf-lon"
            type="number"
            step="any"
            className="input"
            value={lon}
            onChange={(e) => setLon(e.target.value)}
            placeholder="77.5946"
          />
          <p className="mt-1 text-xs text-slate-500">
            Look up coordinates on any map app (right-click → copy
            coordinates). East &amp; North are positive.
          </p>
        </div>
        <div className="flex items-center gap-2 self-end pb-2">
          <input
            id="pf-self"
            type="checkbox"
            checked={isSelf}
            onChange={(e) => setIsSelf(e.target.checked)}
            className="h-4 w-4 accent-gold-500"
          />
          <label htmlFor="pf-self" className="text-sm text-slate-300">
            This is my own chart
          </label>
        </div>
      </div>

      {/* Life events — used by rectification & prediction validation */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="label mb-0">
            Life events{" "}
            <span className="normal-case text-slate-500">
              (optional — helps birth-time rectification)
            </span>
          </span>
          <button
            type="button"
            className="btn-ghost flex items-center gap-1 px-2 py-1 text-xs"
            onClick={() =>
              setEvents((evs) => [
                ...evs,
                { event_type: "other", event_date: "", note: "" },
              ])
            }
          >
            <Plus className="h-3.5 w-3.5" aria-hidden />
            Add event
          </button>
        </div>
        <div className="space-y-2">
          {events.map((ev, i) => (
            <div
              key={ev.id ?? i}
              className="grid gap-2 rounded-lg border border-night-600/60 p-3 sm:grid-cols-[1fr_1fr_2fr_auto]"
            >
              <select
                className="input"
                value={ev.event_type}
                onChange={(e) =>
                  updateEvent(i, {
                    event_type: e.target.value as LifeEventType,
                  })
                }
                aria-label="Event type"
              >
                {LIFE_EVENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {EVENT_LABELS[t]}
                  </option>
                ))}
              </select>
              <input
                type="date"
                className="input"
                value={ev.event_date}
                onChange={(e) => updateEvent(i, { event_date: e.target.value })}
                aria-label="Event date"
              />
              <input
                className="input"
                value={ev.note ?? ""}
                onChange={(e) => updateEvent(i, { note: e.target.value })}
                placeholder="Note (optional)"
                aria-label="Event note"
              />
              <button
                type="button"
                className="btn-ghost px-2 py-1 text-xs"
                onClick={() =>
                  setEvents((evs) => evs.filter((_, j) => j !== i))
                }
                aria-label="Remove event"
              >
                <X className="h-3.5 w-3.5" aria-hidden />
              </button>
            </div>
          ))}
          {events.length === 0 && (
            <p className="text-xs text-slate-600">No events added.</p>
          )}
        </div>
      </div>

      {error && (
        <p className="rounded-lg border border-red-800/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <div className="flex gap-3">
        <button type="submit" className="btn-gold" disabled={saving}>
          {saving ? "Saving…" : "Save profile"}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
