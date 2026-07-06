import type { AshtakavargaData } from "@/lib/api";
import { SIGN_NAMES } from "@/lib/jyotisha";

const PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"];

function heatClass(bindus: number, max: number): string {
  if (max <= 0) return "text-slate-500";
  const ratio = bindus / max;
  if (ratio >= 0.8) return "bg-gold-600/30 text-gold-200 font-semibold";
  if (ratio >= 0.55) return "bg-gold-600/10 text-gold-300";
  if (ratio <= 0.15) return "text-slate-600";
  return "text-slate-300";
}

/**
 * Bhinnashtakavarga (per-planet bindus) + Sarvashtakavarga (combined) grid.
 * Signs run Aries..Pisces left to right; bindu counts are shaded so strong
 * signs (classically >=28 SAV, >=5 BAV for transits) pop visually.
 */
export default function AshtakavargaTable({ data }: { data: AshtakavargaData }) {
  const savMax = Math.max(...data.sav, 1);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[42rem] text-center text-sm">
        <thead>
          <tr className="border-b border-night-600 text-xs uppercase tracking-wider text-slate-500">
            <th className="py-2 pr-3 text-left">Graha</th>
            {SIGN_NAMES.map((s) => (
              <th key={s} className="px-1.5 py-2" title={s}>
                {s.slice(0, 2)}
              </th>
            ))}
            <th className="py-2 pl-3 text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {PLANET_ORDER.filter((p) => data.bav[p]).map((planet) => {
            const row = data.bav[planet];
            const rowMax = Math.max(...row, 1);
            return (
              <tr key={planet} className="border-b border-night-700/50 last:border-0">
                <td className="py-1.5 pr-3 text-left font-medium text-slate-200">{planet}</td>
                {row.map((bindus, i) => (
                  <td key={i} className={`px-1.5 py-1.5 font-mono ${heatClass(bindus, rowMax)}`}>
                    {bindus}
                  </td>
                ))}
                <td className="py-1.5 pl-3 text-right font-mono text-slate-400">
                  {data.bavTotals[planet] ?? row.reduce((a, b) => a + b, 0)}
                </td>
              </tr>
            );
          })}
          <tr className="border-t border-night-500">
            <td className="py-2 pr-3 text-left font-semibold text-gold-400">
              Sarva (SAV)
            </td>
            {data.sav.map((bindus, i) => (
              <td
                key={i}
                className={`px-1.5 py-2 font-mono font-semibold ${heatClass(bindus, savMax)}`}
              >
                {bindus}
              </td>
            ))}
            <td className="py-2 pl-3 text-right font-mono font-semibold text-gold-300">
              {data.savTotal}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
