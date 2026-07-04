"use client";

// South Indian rāśi chart: fixed 4×4 grid, signs never move.
// Layout (row, col):
//   Pisces(12) Aries(1)   Taurus(2)  Gemini(3)
//   Aquarius(11)  [ center 2×2 ]     Cancer(4)
//   Capricorn(10) [        ]         Leo(5)
//   Sagittarius(9) Scorpio(8) Libra(7) Virgo(6)
// Lagna is marked with a diagonal stroke in its sign box.

import { fmtDegMin, signName } from "@/lib/jyotisha";

export interface ChartPlanet {
  abbr: string;
  deg?: number;
  retro?: boolean;
}

export interface SignPlacement {
  sign: number; // 1-12
  planets: ChartPlanet[];
}

interface Props {
  placements: SignPlacement[];
  lagnaSign: number;
  title?: string;
  subtitle?: string;
}

// sign number (1-12) -> [row, col] in the fixed South Indian grid
const GRID: Record<number, [number, number]> = {
  1: [0, 1], // Aries
  2: [0, 2], // Taurus
  3: [0, 3], // Gemini
  4: [1, 3], // Cancer
  5: [2, 3], // Leo
  6: [3, 3], // Virgo
  7: [3, 2], // Libra
  8: [3, 1], // Scorpio
  9: [3, 0], // Sagittarius
  10: [2, 0], // Capricorn
  11: [1, 0], // Aquarius
  12: [0, 0], // Pisces
};

const CELL = 110;
const SIZE = CELL * 4;

export default function SouthIndianChart({
  placements,
  lagnaSign,
  title,
  subtitle,
}: Props) {
  const bySign = new Map<number, ChartPlanet[]>();
  for (const p of placements) {
    const sign = ((p.sign - 1) % 12 + 12) % 12 + 1;
    bySign.set(sign, [...(bySign.get(sign) ?? []), ...p.planets]);
  }

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="h-auto w-full max-w-md"
      role="img"
      aria-label={title ? `${title} chart` : "South Indian chart"}
    >
      {/* outer frame */}
      <rect
        x={1}
        y={1}
        width={SIZE - 2}
        height={SIZE - 2}
        rx={6}
        className="fill-night-900/80 stroke-gold-600/70"
        strokeWidth={2}
      />

      {Array.from({ length: 12 }, (_, i) => i + 1).map((sign) => {
        const [row, col] = GRID[sign];
        const x = col * CELL;
        const y = row * CELL;
        const planets = bySign.get(sign) ?? [];
        const isLagna = sign === lagnaSign;
        return (
          <g key={sign}>
            <rect
              x={x}
              y={y}
              width={CELL}
              height={CELL}
              className={
                isLagna
                  ? "fill-gold-600/10 stroke-gold-600/60"
                  : "fill-transparent stroke-night-500"
              }
              strokeWidth={1}
            />
            {/* lagna diagonal stroke (top-left corner) */}
            {isLagna && (
              <line
                x1={x}
                y1={y + CELL * 0.32}
                x2={x + CELL * 0.32}
                y2={y}
                className="stroke-gold-400"
                strokeWidth={2}
              />
            )}
            {/* sign label */}
            <text
              x={x + CELL - 6}
              y={y + CELL - 6}
              textAnchor="end"
              className="fill-slate-600"
              fontSize={9}
            >
              {signName(sign).slice(0, 3)}
            </text>
            {/* planets: 2-column layout inside the cell */}
            {planets.map((pl, i) => {
              const pcol = i % 2;
              const prow = Math.floor(i / 2);
              const label = `${pl.abbr}${pl.retro ? "(R)" : ""}`;
              return (
                <text
                  key={`${pl.abbr}-${i}`}
                  x={x + 12 + pcol * 52}
                  y={y + 24 + prow * 20}
                  className={
                    pl.retro ? "fill-gold-300 italic" : "fill-slate-200"
                  }
                  fontSize={14}
                  fontWeight={600}
                >
                  <title>
                    {`${pl.abbr}${pl.retro ? " (retrograde)" : ""} — ${signName(
                      sign
                    )}${pl.deg !== undefined ? ` ${fmtDegMin(pl.deg)}` : ""}`}
                  </title>
                  {label}
                </text>
              );
            })}
          </g>
        );
      })}

      {/* center title block (2×2) */}
      <g>
        <rect
          x={CELL}
          y={CELL}
          width={CELL * 2}
          height={CELL * 2}
          className="fill-night-950/60 stroke-night-500"
          strokeWidth={1}
        />
        <text
          x={SIZE / 2}
          y={SIZE / 2 - 6}
          textAnchor="middle"
          className="fill-gold-400"
          fontSize={20}
          fontWeight={700}
          fontFamily="Georgia, serif"
        >
          {title ?? "Rāśi"}
        </text>
        {subtitle && (
          <text
            x={SIZE / 2}
            y={SIZE / 2 + 16}
            textAnchor="middle"
            className="fill-slate-500"
            fontSize={11}
          >
            {subtitle}
          </text>
        )}
      </g>
    </svg>
  );
}
