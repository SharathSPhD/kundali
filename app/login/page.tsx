"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { createClient, supabaseConfigured } from "@/lib/supabase/client";

/** Same-origin relative path only, to avoid open redirects. */
function safeNext(raw: string | null): string {
  if (raw && raw.startsWith("/") && !raw.startsWith("//")) return raw;
  return "/dashboard";
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = safeNext(searchParams.get("next"));

  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Surface auth-callback failures redirected here as ?error=...
  useEffect(() => {
    const e = searchParams.get("error");
    if (e) setError(e);
  }, [searchParams]);

  if (!supabaseConfigured) {
    return (
      <main className="mx-auto max-w-md px-6 py-24 text-center">
        <h1 className="font-display text-3xl font-bold text-slate-100">
          Local mode
        </h1>
        <p className="mt-4 text-sm leading-relaxed text-slate-400">
          Supabase is not configured, so accounts are disabled. Profiles are
          stored in this browser&apos;s localStorage. Set{" "}
          <code className="font-mono text-gold-400">
            NEXT_PUBLIC_SUPABASE_URL
          </code>{" "}
          and{" "}
          <code className="font-mono text-gold-400">
            NEXT_PUBLIC_SUPABASE_ANON_KEY
          </code>{" "}
          to enable sign-in &amp; sync.
        </p>
        <Link href="/dashboard" className="btn-gold mt-8">
          Continue to dashboard →
        </Link>
      </main>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setBusy(true);
    const supabase = createClient()!;
    try {
      if (mode === "signin") {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        router.push(next);
        router.refresh();
      } else {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(
              next
            )}`,
          },
        });
        if (error) throw error;
        setNotice(
          "Account created. Check your email to confirm — the link signs you in automatically."
        );
        setMode("signin");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleMagicLink() {
    setError(null);
    setNotice(null);
    if (!email) {
      setError("Enter your email first.");
      return;
    }
    setBusy(true);
    const supabase = createClient()!;
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(
          next
        )}`,
      },
    });
    setBusy(false);
    if (error) setError(error.message);
    else setNotice("Magic link sent — check your inbox.");
  }

  return (
    <main className="mx-auto max-w-md px-6 py-24">
      <div className="text-center">
        <Link href="/" className="font-display text-2xl font-bold text-gold-400">
          Kundali
        </Link>
        <h1 className="mt-6 font-display text-3xl font-bold text-slate-100">
          {mode === "signin" ? "Sign in" : "Create account"}
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="card mt-8 space-y-4 p-6">
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            required
            minLength={6}
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && (
          <p className="rounded-lg border border-red-800/60 bg-red-950/40 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        )}
        {notice && (
          <p className="rounded-lg border border-gold-700/50 bg-gold-600/10 px-3 py-2 text-sm text-gold-300">
            {notice}
          </p>
        )}

        <button type="submit" className="btn-gold w-full" disabled={busy}>
          {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Sign up"}
        </button>
        <button
          type="button"
          className="btn-ghost w-full"
          onClick={handleMagicLink}
          disabled={busy}
        >
          Email me a magic link
        </button>

        <p className="text-center text-sm text-slate-500">
          {mode === "signin" ? (
            <>
              No account?{" "}
              <button
                type="button"
                className="text-gold-400 hover:underline"
                onClick={() => setMode("signup")}
              >
                Sign up
              </button>
            </>
          ) : (
            <>
              Already registered?{" "}
              <button
                type="button"
                className="text-gold-400 hover:underline"
                onClick={() => setMode("signin")}
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </form>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-md px-6 py-24 text-center text-sm text-slate-500">
          Loading…
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
