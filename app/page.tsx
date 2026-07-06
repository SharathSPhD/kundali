import Link from "next/link";
import {
  ArrowRight,
  Calculator,
  Grid3x3,
  MessageCircleQuestion,
  Moon,
  Sparkles,
  Telescope,
  type LucideIcon,
} from "lucide-react";

const FEATURES: Array<{ title: string; body: string; icon: LucideIcon }> = [
  {
    title: "Deterministic engine",
    body: "Swiss Ephemeris sidereal positions (Lahiri), whole-sign houses, dignities, combustion and retrogression — computed, never guessed.",
    icon: Calculator,
  },
  {
    title: "Shodasha vargas",
    body: "All 16 divisional charts per BPHS — navamsha for dharma and marriage, dashamsha for career, and the rest.",
    icon: Grid3x3,
  },
  {
    title: "Vimshottari dashas",
    body: "Full maha → antar → pratyantar tree with the active path highlighted and exact dates.",
    icon: Moon,
  },
  {
    title: "Gochara & Sade Sati",
    body: "Moon-reference transits, Sade Sati phases, Jupiter–Saturn double-transit detection.",
    icon: Telescope,
  },
  {
    title: "Grounded predictions",
    body: "Scored indications per life area with a full substantiation trail back to engine facts.",
    icon: Sparkles,
  },
  {
    title: "Ask your chart",
    body: "A chat that answers only from the computed chart — every claim cites a dasha, transit or yoga.",
    icon: MessageCircleQuestion,
  },
];

export default function LandingPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-14 sm:px-6 sm:py-20">
      <div className="text-center">
        <p className="mb-4 text-sm uppercase tracking-[0.3em] text-gold-500">
          ॐ · Jyotisha, computed
        </p>
        <h1 className="font-display text-5xl font-bold tracking-tight text-slate-100 sm:text-6xl">
          Kundali
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-400">
          A rigorous Vedic astrology engine — South Indian charts, all sixteen
          vargas, Vimshottari dashas, transits, yogas and predictions — every
          statement traceable to a deterministic calculation. Narration is
          grounded strictly in engine output, never invented.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/dashboard"
            className="btn-gold w-full px-6 py-3 text-base sm:w-auto"
          >
            Open dashboard <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link
            href="/login"
            className="btn-ghost w-full px-6 py-3 text-base sm:w-auto"
          >
            Sign in
          </Link>
        </div>
      </div>

      <div className="mt-24 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <div
            key={f.title}
            className="card animate-fade-up p-6 shadow-glow transition-transform hover:-translate-y-0.5"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <f.icon className="h-6 w-6 text-gold-500" aria-hidden />
            <h3 className="mt-3 font-display text-lg font-semibold text-gold-300">
              {f.title}
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">
              {f.body}
            </p>
          </div>
        ))}
      </div>

      <p className="mt-20 text-center text-xs text-slate-600">
        Lahiri ayanamsa · whole-sign houses · Vimshottari 365.25d — all
        configurable in the engine.
      </p>
    </main>
  );
}
