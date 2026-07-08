import { BookOpen, Brain, CheckCircle } from "lucide-react";

/**
 * Shows how Kundali derives an answer through 3 steps:
 * 1. Rule (from classical text)
 * 2. Source computation (from your chart)
 * 3. Conclusion
 */
export default function DerivationShowcase() {
  const steps = [
    {
      icon: BookOpen,
      title: "Classical Rule",
      description:
        "Jupiter in the 7th house indicates a supportive partner. (BPHS 24.15)",
      example: "Rule from Brihat Parashara Hora Shastra",
    },
    {
      icon: Brain,
      title: "Computed Fact",
      description:
        "Your Jupiter is at 23° Libra, in your 7th whole-sign house, with 7 strength points.",
      example: "Derived from Swiss Ephemeris + your birth data",
    },
    {
      icon: CheckCircle,
      title: "Verified Derivation",
      description:
        "Based on your chart geometry, this classical rule applies. Benefit expected in marriage & partnership.",
      example: "Step-by-step trace you can audit",
    },
  ];

  return (
    <section className="px-4 py-20 sm:px-6 sm:py-28">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-16 text-center">
          <h2 className="font-display text-4xl font-bold tracking-tight text-slate-100 sm:text-5xl">
            Answers You Can Trace
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-400">
            Every prediction is three verifiable steps: a classical rule, a
            computed fact from your chart, and the conclusion that bridges them.
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-6 lg:grid lg:grid-cols-3 lg:gap-8 lg:space-y-0">
          {steps.map((step, i) => {
            const Icon = step.icon;
            return (
              <div
                key={i}
                className="animate-fade-up rounded-2xl border border-night-600/50 bg-night-800/40 p-8 backdrop-blur-sm transition-all hover:border-gold-600/30 hover:bg-night-800/60"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                {/* Step number + icon */}
                <div className="mb-6 flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gold-600/20">
                    <Icon className="h-6 w-6 text-gold-400" aria-hidden />
                  </div>
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-gold-600/30 font-display text-lg font-semibold text-gold-200">
                    {i + 1}
                  </span>
                </div>

                {/* Title & description */}
                <h3 className="font-display text-xl font-semibold text-gold-300">
                  {step.title}
                </h3>
                <p className="mt-3 text-slate-400">{step.description}</p>

                {/* Example tag */}
                <p className="mt-6 inline-block rounded-lg bg-night-700/50 px-3 py-1 text-xs font-medium text-slate-500">
                  {step.example}
                </p>
              </div>
            );
          })}
        </div>

        {/* Bottom callout */}
        <div className="mt-16 rounded-2xl border border-gold-600/20 bg-gold-600/5 px-8 py-6 text-center">
          <p className="text-slate-300">
            No black boxes. No "the AI said so." Every insight carries
            <span className="font-semibold text-gold-300"> machine-readable provenance</span>
            — trace it back to the rule, the source text, and your computed facts.
          </p>
        </div>
      </div>
    </section>
  );
}
