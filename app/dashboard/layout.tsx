"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import LocalModeBanner from "@/components/LocalModeBanner";
import { createClient, supabaseConfigured } from "@/lib/supabase/client";
import { getMyTier, type AccountTier } from "@/lib/account";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [tier, setTier] = useState<AccountTier | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMyTier().then((t) => {
      if (!cancelled) setTier(t);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function signOut() {
    const supabase = createClient();
    if (supabase) {
      await supabase.auth.signOut();
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <div className="min-h-screen">
      <LocalModeBanner />
      <header className="border-b border-night-600/50 bg-night-900/60 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link
            href="/dashboard"
            className="font-display text-lg font-bold text-gold-400"
          >
            Kundali
          </Link>
          <nav className="flex items-center gap-3 text-sm">
            <Link
              href="/dashboard"
              className="text-slate-400 transition hover:text-gold-300"
            >
              Profiles
            </Link>
            <Link
              href="/dashboard/matching"
              className="text-slate-400 transition hover:text-gold-300"
            >
              Matching
            </Link>
            <Link
              href="/dashboard/settings"
              className="text-slate-400 transition hover:text-gold-300"
            >
              Settings
            </Link>
            {tier === "admin" && (
              <Link
                href="/dashboard/admin"
                className="text-slate-400 transition hover:text-gold-300"
              >
                Admin
              </Link>
            )}
            {supabaseConfigured ? (
              <button
                onClick={signOut}
                className="btn-ghost px-3 py-1.5 text-xs"
              >
                Sign out
              </button>
            ) : (
              <span className="chip">local mode</span>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
