"use client";

import { supabaseConfigured } from "@/lib/supabase/client";

export default function LocalModeBanner() {
  if (supabaseConfigured) return null;
  return (
    <div className="border-b border-gold-700/40 bg-gold-600/10 px-4 py-2 text-center text-xs text-gold-300">
      Local mode — profiles are stored in this browser only. Connect Supabase
      for accounts &amp; sync (set{" "}
      <code className="font-mono">NEXT_PUBLIC_SUPABASE_URL</code>).
    </div>
  );
}
