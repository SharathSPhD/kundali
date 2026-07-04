"use client";

// Unified profile store: Supabase tables when configured, localStorage in
// local mode. All functions are safe to call from client components only.

import { createClient, supabaseConfigured } from "./supabase/client";
import {
  deleteLocalProfile,
  getLocalProfile,
  listLocalProfiles,
  saveLocalProfile,
} from "./localProfiles";
import type { BirthProfile, BirthProfileInput, LifeEvent } from "./types";

export { supabaseConfigured };

function rowToProfile(row: any): BirthProfile {
  return {
    id: row.id,
    label: row.label ?? "",
    birth_date: row.birth_date ?? "",
    birth_time: (row.birth_time ?? "").slice(0, 5),
    tz_offset: Number(row.tz_offset ?? 0),
    place_name: row.place_name ?? "",
    lat: Number(row.lat ?? 0),
    lon: Number(row.lon ?? 0),
    is_self: Boolean(row.is_self),
    rectified_time: row.rectified_time ?? null,
    events: Array.isArray(row.life_events)
      ? row.life_events.map(
          (e: any): LifeEvent => ({
            id: e.id,
            event_type: e.event_type,
            event_date: e.event_date,
            note: e.note ?? undefined,
          })
        )
      : [],
  };
}

export async function listProfiles(): Promise<BirthProfile[]> {
  const supabase = createClient();
  if (!supabase) return listLocalProfiles();
  const { data, error } = await supabase
    .from("birth_profiles")
    .select("*, life_events(*)")
    .order("created_at", { ascending: true });
  if (error) throw new Error(error.message);
  return (data ?? []).map(rowToProfile);
}

export async function getProfile(id: string): Promise<BirthProfile | null> {
  const supabase = createClient();
  if (!supabase) return getLocalProfile(id);
  const { data, error } = await supabase
    .from("birth_profiles")
    .select("*, life_events(*)")
    .eq("id", id)
    .maybeSingle();
  if (error) throw new Error(error.message);
  return data ? rowToProfile(data) : null;
}

export async function saveProfile(
  input: BirthProfileInput
): Promise<BirthProfile> {
  const supabase = createClient();
  if (!supabase) return saveLocalProfile(input);

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("Not signed in.");

  const record = {
    user_id: user.id,
    label: input.label,
    birth_date: input.birth_date,
    birth_time: input.birth_time,
    tz_offset: input.tz_offset,
    place_name: input.place_name,
    lat: input.lat,
    lon: input.lon,
    is_self: input.is_self,
  };

  let profileId = input.id;
  if (profileId) {
    const { error } = await supabase
      .from("birth_profiles")
      .update(record)
      .eq("id", profileId);
    if (error) throw new Error(error.message);
  } else {
    const { data, error } = await supabase
      .from("birth_profiles")
      .insert(record)
      .select("id")
      .single();
    if (error) throw new Error(error.message);
    profileId = data.id as string;
  }

  // Replace life events wholesale (simple + correct for small lists).
  const { error: delErr } = await supabase
    .from("life_events")
    .delete()
    .eq("profile_id", profileId);
  if (delErr) throw new Error(delErr.message);
  const events = (input.events ?? []).filter((e) => e.event_date);
  if (events.length > 0) {
    const { error: insErr } = await supabase.from("life_events").insert(
      events.map((e) => ({
        profile_id: profileId,
        event_type: e.event_type,
        event_date: e.event_date,
        note: e.note ?? null,
      }))
    );
    if (insErr) throw new Error(insErr.message);
  }

  const saved = await getProfile(profileId!);
  if (!saved) throw new Error("Profile save failed.");
  return saved;
}

export async function deleteProfile(id: string): Promise<void> {
  const supabase = createClient();
  if (!supabase) {
    deleteLocalProfile(id);
    return;
  }
  const { error } = await supabase.from("birth_profiles").delete().eq("id", id);
  if (error) throw new Error(error.message);
}
