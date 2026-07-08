import Link from "next/link";
import { ArrowRight, LogIn } from "lucide-react";

export default function Hero() {
  return (
    <section className="relative px-4 py-20 sm:px-6 sm:py-28">
      {/* Subtle gradient backdrop */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-gold-600/5 via-transparent to-transparent" />

      <div className="relative mx-auto max-w-3xl text-center">
        {/* Tagline */}
        <p className="mb-6 animate-fade-up text-sm font-medium uppercase tracking-widest text-gold-400">
          ॐ · Vedic Astrology You Can Verify
        </p>

        {/* Main headline */}
        <h1 className="animate-fade-up font-display text-5xl font-bold leading-tight tracking-tight text-slate-100 sm:text-6xl md:text-7xl" style={{ animationDelay: "60ms" }}>
          Your Birth Chart,
          <span className="block text-gold-400">Computed & Proven</span>
        </h1>

        {/* Subheading */}
        <p className="mx-auto mt-8 max-w-2xl animate-fade-up text-lg leading-relaxed text-slate-300 sm:text-xl" style={{ animationDelay: "120ms" }}>
          Deterministic Swiss Ephemeris calculations validated against NASA JPL Horizons. Every answer traces back to a computed fact, cited from classical rules. No guessing. No vagueness.
        </p>

        {/* CTA buttons */}
        <div className="mt-12 flex animate-fade-up flex-col items-center justify-center gap-4 sm:flex-row" style={{ animationDelay: "180ms" }}>
          <Link
            href="/dashboard"
            className="btn-gold inline-flex w-full items-center justify-center gap-2 px-8 py-4 text-lg font-semibold sm:w-auto"
          >
            View Your Chart
            <ArrowRight className="h-5 w-5" aria-hidden />
          </Link>
          <Link
            href="/login"
            className="btn-ghost inline-flex w-full items-center justify-center gap-2 px-8 py-4 text-lg font-semibold sm:w-auto"
          >
            <LogIn className="h-5 w-5" aria-hidden />
            Sign In
          </Link>
        </div>
      </div>
    </section>
  );
}
