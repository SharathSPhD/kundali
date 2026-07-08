/**
 * Pure SVG starfield — decorative south-indian astrology theme
 * using CSS variables for theme colors. No dependencies.
 */
export default function StarField() {
  // Generate pseudo-random star positions and sizes
  // using a seeded approach so they're consistent across renders
  const stars = Array.from({ length: 12 }, (_, i) => ({
    id: i,
    cx: (i * 17 + 7) % 100,
    cy: (i * 23 + 13) % 100,
    r: 0.4 + ((i * 7) % 5) * 0.1,
    opacity: 0.3 + ((i * 3) % 7) * 0.1,
  }));

  return (
    <div className="relative h-64 w-full overflow-hidden rounded-2xl border border-night-600/30 bg-gradient-to-br from-night-900 to-night-800">
      <svg
        viewBox="0 0 100 100"
        className="h-full w-full"
        preserveAspectRatio="xMidYMid slice"
      >
        {/* Subtle radial gradient for depth */}
        <defs>
          <radialGradient id="depth" cx="50%" cy="30%">
            <stop offset="0%" stopColor="rgba(228, 199, 120, 0.08)" />
            <stop offset="100%" stopColor="rgba(228, 199, 120, 0)" />
          </radialGradient>
        </defs>

        {/* Background depth gradient */}
        <circle cx="50" cy="50" r="60" fill="url(#depth)" />

        {/* Stars */}
        {stars.map((star) => (
          <circle
            key={star.id}
            cx={star.cx}
            cy={star.cy}
            r={star.r}
            fill="currentColor"
            className="text-gold-400"
            opacity={star.opacity}
          />
        ))}

        {/* Decorative rashi chakra outline (simplified) */}
        <circle
          cx="50"
          cy="50"
          r="35"
          fill="none"
          stroke="currentColor"
          className="text-gold-600"
          strokeWidth="0.5"
          opacity="0.15"
        />
        <circle
          cx="50"
          cy="50"
          r="25"
          fill="none"
          stroke="currentColor"
          className="text-gold-600"
          strokeWidth="0.4"
          opacity="0.1"
        />

        {/* Inner point */}
        <circle
          cx="50"
          cy="50"
          r="2"
          fill="currentColor"
          className="text-gold-400"
          opacity="0.6"
        />
      </svg>
    </div>
  );
}
