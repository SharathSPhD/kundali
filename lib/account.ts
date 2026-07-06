"use client";

// Account tier + BYOK credential storage. Both tables are RLS-scoped to the
// caller's own row (see supabase/schema.sql), so plain `.from()`/`.rpc()`
// calls through the logged-in user's own Supabase session are safe — no
// backend round-trip needed for reads/writes the user is allowed to make.
//
// Local mode (no Supabase configured) has no multi-user concept at all, so
// every local session is treated as an unrestricted admin and BYOK storage
// is a no-op — there's nothing to gate and nowhere safe to persist a key.

import { createClient, supabaseConfigured } from "./supabase/client";

export const ACCOUNT_TIERS = ["basic", "paid", "guest", "admin"] as const;
export type AccountTier = (typeof ACCOUNT_TIERS)[number];

export const LLM_PROVIDERS = ["anthropic", "openai", "gemini", "ollama"] as const;
export type LlmProviderName = (typeof LLM_PROVIDERS)[number];

export interface LlmCredential {
  provider: LlmProviderName;
  apiKey: string;
  baseUrl: string | null;
}

export async function getMyTier(): Promise<AccountTier> {
  const supabase = createClient();
  if (!supabase) return "admin"; // local mode: unrestricted, single-user
  const { data, error } = await supabase
    .from("user_tiers")
    .select("tier")
    .maybeSingle();
  if (error || !data) return "basic";
  return data.tier as AccountTier;
}

export async function listMyCredentials(): Promise<LlmCredential[]> {
  const supabase = createClient();
  if (!supabase) return [];
  const { data, error } = await supabase
    .from("user_llm_credentials")
    .select("provider, api_key, base_url");
  if (error || !data) return [];
  return data.map((r: any) => ({
    provider: r.provider,
    apiKey: r.api_key ?? "",
    baseUrl: r.base_url ?? null,
  }));
}

export async function saveCredential(
  provider: LlmProviderName,
  apiKey: string,
  baseUrl?: string | null
): Promise<void> {
  const supabase = createClient();
  if (!supabase) {
    throw new Error("BYOK keys require a Supabase-backed account (not available in local mode).");
  }
  const { data: auth } = await supabase.auth.getUser();
  const user = auth?.user;
  if (!user) throw new Error("Not signed in.");
  const { error } = await supabase.from("user_llm_credentials").upsert(
    {
      user_id: user.id,
      provider,
      api_key: apiKey,
      base_url: baseUrl || null,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "user_id,provider" }
  );
  if (error) throw new Error(error.message);
}

export async function deleteCredential(provider: LlmProviderName): Promise<void> {
  const supabase = createClient();
  if (!supabase) return;
  const { error } = await supabase
    .from("user_llm_credentials")
    .delete()
    .eq("provider", provider);
  if (error) throw new Error(error.message);
}

export interface AdminUserLookup {
  userId: string;
  email: string;
  tier: AccountTier;
}

/** Admin-only: looks up a user's current tier by email via the
 * `admin_lookup_tier_by_email` RPC, which self-checks the caller's own
 * admin status server-side (see supabase/schema.sql) — a non-admin calling
 * this throws, it never silently returns someone else's data. */
export async function adminLookupUserByEmail(
  email: string
): Promise<AdminUserLookup | null> {
  const supabase = createClient();
  if (!supabase) throw new Error("Admin tools require a Supabase-backed account.");
  const { data, error } = await supabase.rpc("admin_lookup_tier_by_email", {
    target_email: email,
  });
  if (error) throw new Error(error.message);
  const row = Array.isArray(data) ? data[0] : null;
  if (!row) return null;
  return { userId: row.user_id, email: row.email, tier: row.tier };
}

/** Admin-only: sets another user's tier by email via the
 * `admin_set_tier_by_email` RPC (same self-check as the lookup above). */
export async function adminSetTierByEmail(
  email: string,
  tier: AccountTier
): Promise<void> {
  const supabase = createClient();
  if (!supabase) throw new Error("Admin tools require a Supabase-backed account.");
  const { error } = await supabase.rpc("admin_set_tier_by_email", {
    target_email: email,
    new_tier: tier,
  });
  if (error) throw new Error(error.message);
}

export { supabaseConfigured };
