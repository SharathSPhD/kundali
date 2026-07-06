"use client";

import { supabaseConfigured } from "@/lib/supabase/client";

export default function LocalModeBanner() {
  if (supabaseConfigured) return null;
  return (
    <div
      className="border-b border-gold-600/50 bg-gradient-to-r from-gold-600/15 to-night-900 px-4 py-2.5 text-center text-sm text-gold-200"
      role="status"
    >
      <span className="font-semibold text-gold-300">Local mode</span>
      <span className="mx-2 text-gold-600">·</span>
      Profiles stay in this browser only. Set{" "}
      <code className="rounded bg-night-800 px-1 font-mono text-xs">
        NEXT_PUBLIC_SUPABASE_URL
      </code>{" "}
      and{" "}
      <code className="rounded bg-night-800 px-1 font-mono text-xs">
        NEXT_PUBLIC_SUPABASE_ANON_KEY
      </code>{" "}
      for accounts &amp; sync.
    </div>
  );
}
