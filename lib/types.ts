// Shared domain types for profiles and the engine API contract (see ARCHITECTURE.md).

export const LIFE_EVENT_TYPES = [
  "marriage",
  "child_birth",
  "career_start",
  "promotion",
  "relocation",
  "parent_death",
  "health_event",
  "other",
] as const;

export type LifeEventType = (typeof LIFE_EVENT_TYPES)[number];

export interface LifeEvent {
  id?: string;
  event_type: LifeEventType;
  event_date: string; // YYYY-MM-DD
  note?: string;
}

export interface BirthProfile {
  id: string;
  label: string;
  birth_date: string; // YYYY-MM-DD
  birth_time: string; // HH:MM (24h)
  tz_offset: number; // hours east of UTC, e.g. 5.5
  place_name: string;
  lat: number;
  lon: number;
  is_self: boolean;
  rectified_time?: string | null;
  events: LifeEvent[];
}

export type BirthProfileInput = Omit<BirthProfile, "id"> & { id?: string };

/** Engine API birth payload — matches POST /api/chart et al. */
export interface BirthData {
  date: string;
  time: string;
  lat: number;
  lon: number;
  tz_offset: number;
}

export function birthDataOf(p: BirthProfile): BirthData {
  return {
    date: p.birth_date,
    time: p.birth_time,
    lat: p.lat,
    lon: p.lon,
    tz_offset: p.tz_offset,
  };
}
