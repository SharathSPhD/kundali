"use client";

import { useEffect, useRef, useState } from "react";
import { Anchor, ArrowLeft, CheckCircle2, KeyRound, Send, ShieldAlert } from "lucide-react";
import Button from "@/components/ui/Button";
import { interpret, type ChatTurn } from "@/lib/api";
import {
  getMyTier,
  listMyCredentials,
  type AccountTier,
  type LlmCredential,
} from "@/lib/account";
import { getProfile } from "@/lib/profiles";
import {
  appendChatMessage,
  getChatMessages,
  supabaseConfigured,
} from "@/lib/readings";
import type { BirthProfile } from "@/lib/types";
import { birthDataOf } from "@/lib/types";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  via?: string | null;
  blocked?: boolean;
  upgradeHint?: string | null;
  provider?: string;
  verified?: boolean | null;
  rejectedClaims?: unknown[];
  verificationWarnings?: string[];
}

const SUGGESTIONS = [
  "What does my current dasha indicate?",
  "How is my career period looking?",
  "Which yogas are active in my chart?",
  "What should I know about the current transits?",
];

const HISTORY_WINDOW = 6;

function hasUsableInferencePath(
  tier: AccountTier,
  creds: LlmCredential[]
): boolean {
  if (!supabaseConfigured) return false;
  if (tier !== "basic") return true;
  return creds.some(
    (c) =>
      Boolean(c.apiKey?.trim()) ||
      (c.provider === "ollama" && Boolean(c.baseUrl?.trim()))
  );
}

function modeLabel(provider: string | null | undefined): string | null {
  if (!provider || provider === "blocked") return null;
  if (provider === "template") return "Deterministic summary";
  if (provider === "template_qa") return "Deterministic Q&A";
  return "LLM narrative + verified";
}

export default function ChatPage({ params }: { params: { id: string } }) {
  const [profile, setProfile] = useState<BirthProfile | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [defaultProvider, setDefaultProvider] = useState<string | undefined>(
    undefined
  );
  const [lastMode, setLastMode] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [p, tier, creds, stored] = await Promise.all([
          getProfile(params.id),
          getMyTier(),
          listMyCredentials(),
          getChatMessages(params.id),
        ]);
        if (cancelled) return;
        if (!p) {
          setError("Profile not found.");
          return;
        }
        setProfile(p);
        if (stored.length > 0) {
          setMessages(stored);
          const lastAssistant = [...stored]
            .reverse()
            .find((m) => m.role === "assistant");
          if (lastAssistant?.provider) {
            setLastMode(modeLabel(lastAssistant.provider));
          }
        }
        if (!hasUsableInferencePath(tier, creds)) {
          setDefaultProvider("template");
        }
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load profile.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function historyForRequest(): ChatTurn[] {
    const turns: ChatTurn[] = [];
    for (let i = 0; i < messages.length - 1; i++) {
      if (messages[i].role === "user" && messages[i + 1]?.role === "assistant") {
        turns.push({ question: messages[i].content, answer: messages[i + 1].content });
      }
    }
    return turns.slice(-HISTORY_WINDOW);
  }

  async function send(question: string, provider?: string) {
    const q = question.trim();
    if (!q || !profile || busy) return;
    setInput("");
    setError(null);
    const history = historyForRequest();
    const resolvedProvider = provider ?? defaultProvider;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setBusy(true);
    try {
      const res = await interpret(birthDataOf(profile), q, resolvedProvider, history);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: res.blocked
          ? res.upgradeHint || "No inference is available for your account yet."
          : res.text || "(empty response)",
        citations: res.citations,
        via: res.via,
        blocked: res.blocked,
        upgradeHint: res.upgradeHint,
        provider: res.provider,
        verified: res.verified,
        rejectedClaims: res.rejectedClaims,
        verificationWarnings: res.verificationWarnings,
      };
      setMessages((m) => [...m, assistantMsg]);
      setLastMode(modeLabel(res.provider));

      void appendChatMessage(params.id, "user", q);
      void appendChatMessage(params.id, "assistant", assistantMsg.content, {
        citations: res.citations,
        provider: res.provider,
        verified: res.verified,
        rejectedClaims: res.rejectedClaims,
        verificationWarnings: res.verificationWarnings,
      });
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "The interpretation engine could not be reached. Ensure the backend is running (API_BASE_URL, default http://localhost:8000).",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100dvh-9rem)] max-w-3xl flex-col sm:h-[calc(100vh-10rem)]">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-2xl font-bold text-slate-100">
            {profile ? `${profile.label} — Ask the chart` : "Ask the chart"}
          </h1>
          {lastMode && (
            <span className="chip border-gold-700/50 text-[11px] text-gold-300">
              {lastMode}
            </span>
          )}
        </div>
        <Button href={`/dashboard/chart/${params.id}`} size="sm" icon={ArrowLeft}>
          Chart
        </Button>
      </div>

      <p className="mb-4 rounded-lg border border-night-600/60 bg-night-800/50 px-3 py-2 text-xs text-slate-400">
        Answers are grounded strictly in your computed chart — daśās,
        transits, yogas, Shadbala strength and Jaimini Chara Daśā from the
        deterministic engine. Every claim cites the engine fact it rests
        on; nothing is invented.
      </p>

      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}

      <div className="card flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <p className="text-sm text-slate-500">
              Ask a question about this chart.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="chip transition hover:border-gold-600/60 hover:text-gold-300"
                  onClick={() => send(s)}
                  disabled={!profile || busy}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
          >
            <div
              className={`max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-gold-600/20 text-gold-100"
                  : m.blocked
                    ? "border border-gold-700/50 bg-night-800/80 text-slate-300"
                    : "bg-night-700/60 text-slate-200"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.blocked && (
                <div className="mt-3 flex flex-wrap gap-2 border-t border-night-600/60 pt-2">
                  <Button href="/dashboard/settings" variant="gold" size="sm" icon={KeyRound}>
                    Add an API key
                  </Button>
                  <button
                    className="btn-ghost px-3 py-1 text-xs"
                    onClick={() => {
                      const lastQuestion = [...messages]
                        .slice(0, i)
                        .reverse()
                        .find((mm) => mm.role === "user");
                      if (lastQuestion) send(lastQuestion.content, "template");
                    }}
                  >
                    Use deterministic summary instead
                  </button>
                </div>
              )}
              {m.role === "assistant" && !m.blocked && m.verified === true && (
                <span className="mt-2 inline-flex items-center gap-1 rounded-full border border-emerald-700/50 bg-emerald-900/20 px-2 py-0.5 text-[11px] text-emerald-300">
                  <CheckCircle2 className="h-3 w-3" aria-hidden /> verified
                </span>
              )}
              {m.role === "assistant" &&
                !m.blocked &&
                (m.rejectedClaims?.length ?? 0) > 0 && (
                  <span className="mt-2 inline-flex items-center gap-1 rounded-full border border-amber-700/50 bg-amber-900/20 px-2 py-0.5 text-[11px] text-amber-200">
                    <ShieldAlert className="h-3 w-3" aria-hidden />{" "}
                    {m.rejectedClaims!.length} claim(s) unverified
                  </span>
                )}
              {m.via && !m.blocked && (
                <p className="mt-2 text-[11px] uppercase tracking-wide text-slate-500">
                  via {m.via}
                </p>
              )}
              {m.citations && m.citations.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5 border-t border-night-600/60 pt-2">
                  {m.citations.map((c, j) => (
                    <span
                      key={j}
                      className="chip gap-1 border-gold-700/50 text-[11px] text-gold-300"
                      title="Engine fact cited by this answer"
                    >
                      <Anchor className="h-3 w-3 shrink-0" aria-hidden /> {c}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="rounded-xl bg-night-700/60 px-4 py-3 text-sm text-slate-400">
              Consulting the engine…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          className="input flex-1"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            profile ? "e.g. When does my next favorable career window open?" : "Loading profile…"
          }
          disabled={!profile || busy}
        />
        <button
          type="submit"
          className="btn-gold shrink-0"
          disabled={!profile || busy || !input.trim()}
          aria-label="Ask"
        >
          <Send className="h-4 w-4 sm:hidden" aria-hidden />
          <span className="hidden sm:inline">Ask</span>
        </button>
      </form>
    </div>
  );
}
