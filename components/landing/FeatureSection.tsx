import type { ElementType } from "react";

interface FeatureSectionProps {
  title: string;
  description: string;
  points: string[];
  icon: ElementType;
  index: number;
  visual?: React.ReactNode;
}

/**
 * Alternating layout feature section:
 * - Even indexes: icon/visual on left, text on right
 * - Odd indexes: text on left, icon/visual on right
 */
export default function FeatureSection({
  title,
  description,
  points,
  icon: Icon,
  index,
  visual,
}: FeatureSectionProps) {
  const isEven = index % 2 === 0;
  const animationDelay = index * 100;

  return (
    <section className="px-4 py-16 sm:px-6 sm:py-20">
      <div className="mx-auto max-w-5xl">
        <div
          className={`grid items-center gap-12 lg:grid-cols-2 ${
            isEven ? "" : "lg:[direction:rtl]"
          }`}
        >
          {/* Visual side */}
          <div
            className="animate-fade-up"
            style={{ animationDelay: `${animationDelay}ms` }}
          >
            {visual || (
              <div className="flex h-80 items-center justify-center rounded-2xl border border-night-600/30 bg-night-800/40">
                <Icon className="h-24 w-24 text-gold-600/40" aria-hidden />
              </div>
            )}
          </div>

          {/* Text side */}
          <div
            className="animate-fade-up space-y-6"
            style={{ animationDelay: `${animationDelay + 60}ms` }}
          >
            <div>
              <div className="mb-3 inline-flex items-center gap-3 rounded-lg bg-gold-600/10 px-4 py-2">
                <Icon className="h-5 w-5 text-gold-400" aria-hidden />
                <span className="text-sm font-semibold uppercase tracking-wider text-gold-300">
                  Feature
                </span>
              </div>
              <h2 className="font-display text-4xl font-bold tracking-tight text-slate-100 sm:text-5xl">
                {title}
              </h2>
            </div>

            <p className="text-lg leading-relaxed text-slate-300">
              {description}
            </p>

            <ul className="space-y-3">
              {points.map((point, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="mt-1 inline-block h-2 w-2 shrink-0 rounded-full bg-gold-500" />
                  <span className="text-slate-400">{point}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
