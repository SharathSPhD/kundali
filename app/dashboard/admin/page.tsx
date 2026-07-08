"use client";

import { useEffect, useState } from "react";
import { Search, Users, Zap } from "lucide-react";
import Button from "@/components/ui/Button";
import {
  ACCOUNT_TIERS,
  adminLookupUserByEmail,
  adminSetTierByEmail,
  getMyTier,
  type AccountTier,
} from "@/lib/account";
import { createClient } from "@/lib/supabase/client";

export default function AdminPage() {
  const [myTier, setMyTier] = useState<AccountTier | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [looking, setLooking] = useState(false);
  const [found, setFound] = useState<{ email: string; tier: AccountTier } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  // GB10 Ollama gateway state
  const [ollamaUrl, setOllamaUrl] = useState("");
  const [ollamaDefaultModel, setOllamaDefaultModel] = useState("");
  const [ollamaLoading, setOllamaLoading] = useState(true);
  const [olllamaError, setOllamaError] = useState<string | null>(null);
  const [ollamaNotice, setOllamaNotice] = useState<string | null>(null);
  const [olllamaSaving, setOlllamaSaving] = useState(false);
  const [ollamaReachable, setOllamaReachable] = useState<boolean | null>(null);
  const [olllamaTesting, setOlllamaTesting] = useState(false);

  useEffect(() => {
    (async () => {
      const tier = await getMyTier();
      setMyTier(tier);
      setLoading(false);

      // Load runtime config for GB10 Ollama
      if (tier === "admin") {
        const supabase = createClient();
        if (supabase) {
          try {
            const { data, error: queryError } = await supabase
              .from("runtime_config")
              .select("key,value");
            if (queryError) throw queryError;
            if (data) {
              const urlConfig = data.find((r) => r.key === "ollama_gateway_url");
              const modelConfig = data.find(
                (r) => r.key === "gb10_default_model"
              );
              setOllamaUrl(urlConfig?.value ?? "");
              setOllamaDefaultModel(modelConfig?.value ?? "");
            }
          } catch (err) {
            console.error("Failed to load runtime config:", err);
          }
          setOllamaLoading(false);
        }
      }
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

  async function saveOllamaConfig(key: string, value: string) {
    setOlllamaSaving(true);
    setOllamaError(null);
    setOllamaNotice(null);
    try {
      const supabase = createClient();
      if (!supabase) throw new Error("Supabase not configured");

      const { error } = await supabase.rpc("admin_set_runtime_config", {
        cfg_key: key,
        cfg_value: value.trim() || null,
      });

      if (error) throw error;
      setOllamaNotice(
        value.trim()
          ? `${key} saved.`
          : `${key} deleted.`
      );
    } catch (err) {
      setOllamaError(err instanceof Error ? err.message : "Failed to save.");
    } finally {
      setOlllamaSaving(false);
    }
  }

  async function testOllamaGateway() {
    if (!ollamaUrl.trim()) {
      setOllamaError("Please enter a gateway URL first.");
      return;
    }

    setOlllamaTesting(true);
    setOllamaError(null);
    setOllamaReachable(null);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${ollamaUrl.trim()}/healthz`, {
        mode: "cors",
        signal: controller.signal,
      });

      clearTimeout(timeout);
      setOllamaReachable(true);
    } catch (err) {
      setOllamaReachable(false);
    } finally {
      setOlllamaTesting(false);
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  if (myTier !== "admin") {
    return (
      <div className="card p-6">
        <p className="text-sm text-red-300">
          This page is restricted to admin accounts.
        </p>
        <Button href="/dashboard" size="sm" className="mt-4 inline-flex">
          ← Back to profiles
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="flex items-center gap-2 font-display text-2xl font-bold text-slate-100">
        <Users className="h-5 w-5 shrink-0 text-gold-400" aria-hidden />
        Admin
      </h1>

      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-300">User management</h2>
        <p className="text-xs text-slate-500">
          Look up a user by email and set their tier. There is no separate
          guest signup flow — a guest is simply an existing account an admin
          has upgraded here.
        </p>
      </div>

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
            <Search className="h-3.5 w-3.5 shrink-0" aria-hidden />
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

      <div className="space-y-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-300">
          <Zap className="h-4 w-4 shrink-0" aria-hidden />
          GB10 Ollama gateway
        </h2>
        <p className="text-xs text-slate-500">
          This is how the deployed app reaches Ollama running on GB10. Run{" "}
          <code className="rounded bg-night-800 px-1 py-0.5 text-[11px] font-mono text-gold-300">
            gb10-gateway/deploy-local.sh
          </code>{" "}
          on GB10, expose it with{" "}
          <code className="rounded bg-night-800 px-1 py-0.5 text-[11px] font-mono text-gold-300">
            tailscale funnel --bg --https=8443 8100
          </code>
          , then set the URL here (e.g.{" "}
          <code className="rounded bg-night-800 px-1 py-0.5 text-[11px] font-mono text-gold-300">
            https://spark-5208.tailec14b1.ts.net:8443
          </code>
          ). Default model must be on the gateway allow-list (default:{" "}
          <code className="rounded bg-night-800 px-1 py-0.5 text-[11px] font-mono text-gold-300">
            qwen2.5:14b
          </code>
          ).
        </p>
      </div>

      {!ollamaLoading && (
        <div className="card space-y-4 p-5">
          <div className="space-y-2">
            <label className="label" htmlFor="ollama-url">
              Gateway URL
            </label>
            <div className="flex gap-2">
              <input
                id="ollama-url"
                type="url"
                className="input"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                placeholder="https://spark-5208.tailec14b1.ts.net:8443"
                disabled={olllamaSaving}
              />
              <button
                className="btn-gold px-4 text-sm disabled:opacity-50"
                onClick={() => saveOllamaConfig("ollama_gateway_url", ollamaUrl)}
                disabled={olllamaSaving}
              >
                {olllamaSaving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <label className="label" htmlFor="ollama-model">
              Default model
            </label>
            <div className="flex gap-2">
              <input
                id="ollama-model"
                type="text"
                className="input"
                value={ollamaDefaultModel}
                onChange={(e) => setOllamaDefaultModel(e.target.value)}
                placeholder="qwen2.5:14b"
                disabled={olllamaSaving}
              />
              <button
                className="btn-gold px-4 text-sm disabled:opacity-50"
                onClick={() =>
                  saveOllamaConfig("gb10_default_model", ollamaDefaultModel)
                }
                disabled={olllamaSaving}
              >
                {olllamaSaving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              className="btn-ghost px-3 py-1.5 text-xs"
              onClick={testOllamaGateway}
              disabled={olllamaTesting || !ollamaUrl.trim()}
            >
              {olllamaTesting ? "Testing…" : "Test gateway"}
            </button>
            {ollamaReachable !== null && (
              <span
                className={`chip ${
                  ollamaReachable
                    ? "border-gold-600/60 text-gold-300"
                    : "border-red-600/60 text-red-300"
                }`}
              >
                {ollamaReachable ? "Reachable" : "Unreachable"}
              </span>
            )}
          </div>

          {olllamaError && (
            <p className="text-sm text-red-300">{olllamaError}</p>
          )}
          {ollamaNotice && (
            <p className="text-sm text-gold-300">{ollamaNotice}</p>
          )}
        </div>
      )}
    </div>
  );
}
