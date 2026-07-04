// localStorage-backed profile store used in "local mode"
// (when NEXT_PUBLIC_SUPABASE_URL is not configured).

import type { BirthProfile, BirthProfileInput } from "./types";

const KEY = "kundali:profiles";

function makeId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function readAll(): BirthProfile[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as BirthProfile[]) : [];
  } catch {
    return [];
  }
}

function writeAll(profiles: BirthProfile[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(profiles));
}

export function listLocalProfiles(): BirthProfile[] {
  return readAll();
}

export function getLocalProfile(id: string): BirthProfile | null {
  return readAll().find((p) => p.id === id) ?? null;
}

export function saveLocalProfile(input: BirthProfileInput): BirthProfile {
  const profiles = readAll();
  const events = (input.events ?? []).map((e) => ({
    ...e,
    id: e.id ?? makeId(),
  }));
  if (input.id) {
    const idx = profiles.findIndex((p) => p.id === input.id);
    const updated: BirthProfile = { ...input, id: input.id, events };
    if (idx >= 0) profiles[idx] = updated;
    else profiles.push(updated);
    writeAll(profiles);
    return updated;
  }
  const created: BirthProfile = { ...input, id: makeId(), events };
  profiles.push(created);
  writeAll(profiles);
  return created;
}

export function deleteLocalProfile(id: string): void {
  writeAll(readAll().filter((p) => p.id !== id));
}
