"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { interpret } from "@/lib/api";
import { getProfile } from "@/lib/profiles";
import type { BirthProfile } from "@/lib/types";
import { birthDataOf } from "@/lib/types";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
}

const SUGGESTIONS = [
  "What does my current dasha indicate?",
  "How is my career period looking?",
  "Which yogas are active in my chart?",
  "What should I know about the current transits?",
];

export default function ChatPage({ params }: { params: { id: string } }) {
  const [profile, setProfile] = useState<BirthProfile | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getProfile(params.id)
      .then((p) => {
        if (!p) setError("Profile not found.");
        setProfile(p);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load profile.")
      );
  }, [params.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(question: string) {
    const q = question.trim();
    if (!q || !profile || busy) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", content: q }]);
    setBusy(true);
    try {
      const res = await interpret(birthDataOf(profile), q);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.text || "(empty response)",
          citations: res.citations,
        },
      ]);
    } catch (err) {
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
    <div className="mx-auto flex h-[calc(100vh-10rem)] max-w-3xl flex-col">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-2xl font-bold text-slate-100">
          {profile ? `${profile.label} — Ask the chart` : "Ask the chart"}
        </h1>
        <Link
          href={`/dashboard/chart/${params.id}`}
          className="btn-ghost px-3 py-1.5 text-xs"
        >
          ← Chart
        </Link>
      </div>

      <p className="mb-4 rounded-lg border border-night-600/60 bg-night-800/50 px-3 py-2 text-xs text-slate-400">
        Answers are grounded strictly in your computed chart — daśās, transits
        and yogas from the deterministic engine. Every claim cites the engine
        fact it rests on; nothing is invented.
      </p>

      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}

      {/* Message list */}
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
                  : "bg-night-700/60 text-slate-200"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.citations && m.citations.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5 border-t border-night-600/60 pt-2">
                  {m.citations.map((c, j) => (
                    <span
                      key={j}
                      className="chip border-gold-700/50 text-[11px] text-gold-300"
                      title="Engine fact cited by this answer"
                    >
                      ⚓ {c}
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

      {/* Input */}
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
          className="btn-gold"
          disabled={!profile || busy || !input.trim()}
        >
          Ask
        </button>
      </form>
    </div>
  );
}
