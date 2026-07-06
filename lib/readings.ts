"use client";

import { createClient, supabaseConfigured } from "./supabase/client";

export async function saveReading(
  profileId: string,
  kind: string,
  payload: unknown
): Promise<void> {
  const supabase = createClient();
  if (!supabase) return;
  const { error } = await supabase.from("readings").insert({
    profile_id: profileId,
    kind,
    payload,
  });
  if (error) console.warn("saveReading failed:", error.message);
}

export async function getLatestReading(
  profileId: string,
  kind: string
): Promise<unknown | null> {
  const supabase = createClient();
  if (!supabase) return null;
  const { data, error } = await supabase
    .from("readings")
    .select("payload")
    .eq("profile_id", profileId)
    .eq("kind", kind)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) {
    console.warn("getLatestReading failed:", error.message);
    return null;
  }
  return data?.payload ?? null;
}

export async function appendChatMessage(
  profileId: string,
  role: "user" | "assistant",
  content: string,
  grounding?: Record<string, unknown>
): Promise<void> {
  const supabase = createClient();
  if (!supabase) return;
  const { error } = await supabase.from("chat_messages").insert({
    profile_id: profileId,
    role,
    content,
    grounding: grounding ?? null,
  });
  if (error) console.warn("appendChatMessage failed:", error.message);
}

export interface StoredChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  provider?: string;
  verified?: boolean | null;
  rejectedClaims?: unknown[];
  verificationWarnings?: string[];
}

export async function getChatMessages(
  profileId: string
): Promise<StoredChatMessage[]> {
  const supabase = createClient();
  if (!supabase) return [];
  const { data, error } = await supabase
    .from("chat_messages")
    .select("role, content, grounding")
    .eq("profile_id", profileId)
    .order("created_at", { ascending: true });
  if (error) {
    console.warn("getChatMessages failed:", error.message);
    return [];
  }
  return (data ?? []).map((row: any) => {
    const g = row.grounding ?? {};
    return {
      role: row.role as "user" | "assistant",
      content: row.content ?? "",
      citations: Array.isArray(g.citations) ? g.citations : undefined,
      provider: typeof g.provider === "string" ? g.provider : undefined,
      verified: g.verified ?? undefined,
      rejectedClaims: g.rejectedClaims ?? undefined,
      verificationWarnings: g.verificationWarnings ?? undefined,
    };
  });
}

export { supabaseConfigured };
