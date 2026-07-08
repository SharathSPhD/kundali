"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CalendarCheck,
  LogOut,
  Menu,
  Moon,
  ShieldCheck,
  Sliders,
  Users,
  X,
} from "lucide-react";
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
  const [menuOpen, setMenuOpen] = useState(false);

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

  interface NavGroup {
    label: string;
    links: Array<{ href: string; label: string; icon: typeof Moon }>;
  }

  const navGroups: NavGroup[] = [
    {
      label: "For you",
      links: [
        { href: "/dashboard", label: "Home", icon: Moon },
        { href: "/dashboard/muhurta", label: "Good days", icon: CalendarCheck },
        { href: "/dashboard/matching", label: "Matching", icon: Users },
        { href: "/dashboard/settings", label: "Settings", icon: Sliders },
      ],
    },
    {
      label: "Jyotishi",
      links: [
        { href: "/dashboard/knowledge", label: "Knowledge", icon: Moon },
        ...(tier === "admin"
          ? [{ href: "/dashboard/admin", label: "Admin", icon: ShieldCheck }]
          : []),
      ],
    },
  ];

  const allLinks = navGroups.flatMap((g) => g.links);

  return (
    <div className="min-h-screen">
      <LocalModeBanner />
      <header className="border-b border-night-600/50 bg-night-900/60 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <Link
            href="/dashboard"
            className="font-display text-lg font-bold text-gold-400"
          >
            Kundali
          </Link>

          {/* Desktop nav */}
          <nav className="hidden items-center gap-6 text-sm sm:flex">
            {navGroups.map((group) => (
              <div key={group.label} className="flex items-center gap-4">
                {group.links.map(({ href, label, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    className="flex items-center gap-1.5 text-slate-400 transition hover:text-gold-300"
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                    {label}
                  </Link>
                ))}
              </div>
            ))}
            {supabaseConfigured ? (
              <button onClick={signOut} className="btn-ghost px-3 py-1.5 text-xs">
                <LogOut className="h-3.5 w-3.5" aria-hidden />
                Sign out
              </button>
            ) : (
              <span className="chip">local mode</span>
            )}
          </nav>

          {/* Mobile menu toggle */}
          <button
            className="btn-ghost p-2 sm:hidden"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {/* Mobile nav drawer */}
        {menuOpen && (
          <nav className="animate-fade-up flex flex-col gap-4 border-t border-night-600/50 px-4 py-3 text-sm sm:hidden">
            {navGroups.map((group) => (
              <div key={group.label}>
                <p className="px-2 py-1 text-xs font-medium uppercase tracking-wider text-slate-500">
                  {group.label}
                </p>
                <div className="flex flex-col gap-1">
                  {group.links.map(({ href, label, icon: Icon }) => (
                    <Link
                      key={href}
                      href={href}
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-2 rounded-lg px-2 py-2 text-slate-300 transition hover:bg-night-700/50 hover:text-gold-300"
                    >
                      <Icon className="h-4 w-4" aria-hidden />
                      {label}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
            {supabaseConfigured ? (
              <button
                onClick={() => {
                  setMenuOpen(false);
                  signOut();
                }}
                className="btn-ghost mt-1 justify-start px-2 py-2 text-xs"
              >
                <LogOut className="h-3.5 w-3.5" aria-hidden />
                Sign out
              </button>
            ) : (
              <span className="chip mt-1 w-fit">local mode</span>
            )}
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}
