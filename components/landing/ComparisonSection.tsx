import { Check } from "lucide-react";

/**
 * Highlights what makes Kundali different from typical astrology apps
 */
export default function ComparisonSection() {
  const features = [
    {
      category: "Accuracy",
      kundali: "Arcsecond-validated calculations (NASA JPL Horizons)",
      other: "Generic approximations, often off by degrees",
    },
    {
      category: "Trustworthiness",
      kundali: "Every claim cites a rule, a varga, a dasha, or a transit",
      other: "Vague AI text without grounding",
    },
    {
      category: "Completeness",
      kundali: "All 16 divisional charts, both dashas, full Shadbala, yogas, matching",
      other: "Basic rashi chart + generic predictions",
    },
    {
      category: "Privacy",
      kundali: "Your birth data stays in your account or fully deterministic (no AI)",
      other: "Data sent to APIs; unclear data handling",
    },
    {
      category: "Verification",
      kundali: "Formal proofs in Lean 4; crash-tested on 15,807 real charts",
      other: "No formal validation or scale testing",
    },
  ];

  return (
    <section className="px-4 py-20 sm:px-6 sm:py-28">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-16 text-center">
          <h2 className="font-display text-4xl font-bold tracking-tight text-slate-100 sm:text-5xl">
            The Difference
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-400">
            Kundali is built for rigor. We don't approximate. We don't guess.
          </p>
        </div>

        {/* Comparison table */}
        <div className="space-y-4">
          {features.map((feat, i) => (
            <div
              key={i}
              className="animate-fade-up grid grid-cols-1 gap-4 rounded-xl border border-night-600/30 bg-night-800/40 p-6 sm:grid-cols-3"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              {/* Category */}
              <div className="sm:col-span-1">
                <h3 className="font-display text-lg font-semibold text-gold-300">
                  {feat.category}
                </h3>
              </div>

              {/* Kundali */}
              <div className="flex gap-3 sm:col-span-1">
                <Check className="h-5 w-5 shrink-0 text-gold-400" aria-hidden />
                <p className="text-slate-300">{feat.kundali}</p>
              </div>

              {/* Other */}
              <div className="sm:col-span-1">
                <p className="text-slate-500 line-through">{feat.other}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
