"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ACCOUNT_TIERS,
  adminLookupUserByEmail,
  adminSetTierByEmail,
  getMyTier,
  type AccountTier,
} from "@/lib/account";

export default function AdminPage() {
  const [myTier, setMyTier] = useState<AccountTier | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [looking, setLooking] = useState(false);
  const [found, setFound] = useState<{ email: string; tier: AccountTier } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    (async () => {
      setMyTier(await getMyTier());
      setLoading(false);
    })();
  }, []);

  async function lookup() {
    setLooking(true);
    setError(null);
    setNotice(null);
    setFound(null);
    try {
      const result = await adminLookupUserByEmail(email.trim());
      if (!result) setError("No user found with that email.");
      else setFound({ email: result.email, tier: result.tier });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lookup failed.");
    } finally {
      setLooking(false);
    }
  }

  async function setTier(tier: AccountTier) {
    if (!found) return;
    setUpdating(true);
    setError(null);
    try {
      await adminSetTierByEmail(found.email, tier);
      setFound({ ...found, tier });
      setNotice(`${found.email} is now ${tier}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update tier.");
    } finally {
      setUpdating(false);
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  if (myTier !== "admin") {
    return (
      <div className="card p-6">
        <p className="text-sm text-red-300">
          This page is restricted to admin accounts.
        </p>
        <Link href="/dashboard" className="btn-ghost mt-4 inline-block px-3 py-1.5 text-xs">
          ← Back to profiles
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="font-display text-2xl font-bold text-slate-100">
        Manage users
      </h1>
      <p className="text-xs text-slate-500">
        Look up a user by email and set their tier. There is no separate
        guest signup flow — a guest is simply an existing account an admin
        has upgraded here.
      </p>

      <div className="card space-y-3 p-5">
        <label className="label" htmlFor="admin-email">
          User email
        </label>
        <div className="flex gap-2">
          <input
            id="admin-email"
            type="email"
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@example.com"
            onKeyDown={(e) => e.key === "Enter" && lookup()}
          />
          <button
            className="btn-gold px-4 text-sm disabled:opacity-50"
            onClick={lookup}
            disabled={looking || !email.trim()}
          >
            {looking ? "Looking up…" : "Look up"}
          </button>
        </div>

        {error && <p className="text-sm text-red-300">{error}</p>}
        {notice && <p className="text-sm text-gold-300">{notice}</p>}

        {found && (
          <div className="mt-2 rounded-lg border border-night-600/60 p-4">
            <p className="text-sm text-slate-300">
              <span className="font-semibold">{found.email}</span> — current
              tier:{" "}
              <span className="font-semibold capitalize text-gold-300">
                {found.tier}
              </span>
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {ACCOUNT_TIERS.map((t) => (
                <button
                  key={t}
                  className={`chip capitalize ${
                    t === found.tier
                      ? "border-gold-600/60 text-gold-300"
                      : "hover:border-gold-600/60"
                  }`}
                  onClick={() => setTier(t)}
                  disabled={updating || t === found.tier}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
