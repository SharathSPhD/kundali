"use client";

import { useEffect, useState } from "react";
import { KeyRound, ShieldCheck } from "lucide-react";
import {
  LLM_PROVIDERS,
  deleteCredential,
  getMyTier,
  listMyCredentials,
  saveCredential,
  supabaseConfigured,
  type AccountTier,
  type LlmCredential,
  type LlmProviderName,
} from "@/lib/account";

const TIER_COPY: Record<AccountTier, { label: string; desc: string }> = {
  admin: {
    label: "Admin",
    desc: "Unrestricted — chat runs on Kundali's GB10 inference with no key needed.",
  },
  guest: {
    label: "Guest",
    desc: "Added by an admin — chat runs on Kundali's GB10 inference with no key needed.",
  },
  paid: {
    label: "Paid",
    desc: "Chat runs on Kundali's GB10 inference via your subscription, no key needed.",
  },
  basic: {
    label: "Basic",
    desc: "No inference included yet — add your own API key below to enable chat, or ask an admin to upgrade your tier.",
  },
};

const PROVIDER_LABELS: Record<LlmProviderName, string> = {
  anthropic: "Anthropic (Claude)",
  openai: "OpenAI (GPT)",
  gemini: "Google Gemini",
  ollama: "Ollama (self-hosted)",
};

const PROVIDER_KEY_HINT: Record<LlmProviderName, string> = {
  anthropic: "sk-ant-...",
  openai: "sk-...",
  gemini: "AIza...",
  ollama: "optional — leave blank if your endpoint needs no key",
};

function ProviderRow({
  provider,
  existing,
  onSaved,
  onDeleted,
}: {
  provider: LlmProviderName;
  existing: LlmCredential | undefined;
  onSaved: (cred: LlmCredential) => void;
  onDeleted: () => void;
}) {
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(existing?.baseUrl ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(!existing);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const key = apiKey || existing?.apiKey || "";
      if (!key && provider !== "ollama") {
        setError("An API key is required for this provider.");
        return;
      }
      await saveCredential(provider, key, baseUrl || null);
      onSaved({ provider, apiKey: key, baseUrl: baseUrl || null });
      setApiKey("");
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setSaving(true);
    setError(null);
    try {
      await deleteCredential(provider);
      onDeleted();
      setEditing(true);
      setBaseUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-night-600/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-semibold text-slate-200">
          {PROVIDER_LABELS[provider]}
        </p>
        {existing && !editing && (
          <div className="flex items-center gap-2">
            <span className="chip border-gold-600/60 text-gold-300">
              key saved
            </span>
            <button
              className="text-xs text-slate-500 hover:text-gold-300"
              onClick={() => setEditing(true)}
            >
              Change
            </button>
            <button
              className="text-xs text-red-400 hover:text-red-300"
              onClick={handleDelete}
              disabled={saving}
            >
              Remove
            </button>
          </div>
        )}
      </div>

      {editing && (
        <div className="mt-3 space-y-2">
          <input
            type="password"
            className="input"
            placeholder={PROVIDER_KEY_HINT[provider]}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            autoComplete="off"
          />
          {provider === "ollama" && (
            <input
              type="text"
              className="input"
              placeholder="Base URL, e.g. https://my-ollama.example.com"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
            />
          )}
          <div className="flex items-center gap-2">
            <button
              className="btn-gold px-3 py-1.5 text-xs disabled:opacity-50"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Saving…" : "Save key"}
            </button>
            {existing && (
              <button
                className="btn-ghost px-3 py-1.5 text-xs"
                onClick={() => setEditing(false)}
              >
                Cancel
              </button>
            )}
          </div>
          {error && <p className="text-xs text-red-300">{error}</p>}
        </div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const [tier, setTier] = useState<AccountTier | null>(null);
  const [credentials, setCredentials] = useState<LlmCredential[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [t, c] = await Promise.all([getMyTier(), listMyCredentials()]);
      if (!cancelled) {
        setTier(t);
        setCredentials(c);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="font-display text-2xl font-bold text-slate-100">
        Account settings
      </h1>

      {!supabaseConfigured && (
        <p className="rounded-lg border border-night-600/60 bg-night-800/60 px-3 py-2 text-xs text-slate-400">
          Running in local mode — every session is unrestricted; BYOK keys
          aren&apos;t needed or stored.
        </p>
      )}

      {tier && (
        <div className="card animate-fade-up p-5">
          <h2 className="mb-1 flex items-center gap-2 font-display text-lg font-semibold text-gold-300">
            <ShieldCheck className="h-4 w-4 shrink-0" aria-hidden />
            Tier: <span className="capitalize">{TIER_COPY[tier].label}</span>
          </h2>
          <p className="text-sm text-slate-400">{TIER_COPY[tier].desc}</p>
        </div>
      )}

      {supabaseConfigured && (
        <div className="card animate-fade-up space-y-4 p-5">
          <div>
            <h2 className="flex items-center gap-2 font-display text-lg font-semibold text-gold-300">
              <KeyRound className="h-4 w-4 shrink-0" aria-hidden />
              Bring your own key
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Add a key for any provider to enable chat regardless of your
              tier — your key is stored only for your account (row-level
              security), never shared, and used only for your own requests.
            </p>
          </div>
          <div className="space-y-3">
            {LLM_PROVIDERS.map((p) => (
              <ProviderRow
                key={p}
                provider={p}
                existing={credentials.find((c) => c.provider === p)}
                onSaved={(cred) =>
                  setCredentials((prev) => [
                    ...prev.filter((c) => c.provider !== cred.provider),
                    cred,
                  ])
                }
                onDeleted={() =>
                  setCredentials((prev) => prev.filter((c) => c.provider !== p))
                }
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
