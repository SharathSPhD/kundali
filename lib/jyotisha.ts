// Small pure helpers/constants for jyotisha display logic.

export const SIGN_NAMES = [
  "Aries",
  "Taurus",
  "Gemini",
  "Cancer",
  "Leo",
  "Virgo",
  "Libra",
  "Scorpio",
  "Sagittarius",
  "Capricorn",
  "Aquarius",
  "Pisces",
] as const;

export const PLANET_ABBR: Record<string, string> = {
  sun: "Su",
  moon: "Mo",
  mars: "Ma",
  mercury: "Me",
  jupiter: "Ju",
  venus: "Ve",
  saturn: "Sa",
  rahu: "Ra",
  ketu: "Ke",
  ascendant: "As",
  lagna: "As",
};

export function planetAbbr(name: string): string {
  const key = name.trim().toLowerCase();
  if (PLANET_ABBR[key]) return PLANET_ABBR[key];
  // Already an abbreviation like "Su"?
  if (name.length <= 2) return name;
  return name.slice(0, 2);
}

/** 1-based sign number -> name. */
export function signName(sign: number): string {
  return SIGN_NAMES[((sign - 1) % 12 + 12) % 12] ?? `Sign ${sign}`;
}

/** Accepts a sign as number (1-12) or a name and returns 1-12 (0 if unknown). */
export function signNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return ((Math.round(value) - 1) % 12 + 12) % 12 + 1;
  }
  if (typeof value === "string") {
    const asNum = Number(value);
    if (Number.isFinite(asNum) && value.trim() !== "") return signNumber(asNum);
    const idx = SIGN_NAMES.findIndex(
      (s) => s.toLowerCase() === value.trim().toLowerCase()
    );
    if (idx >= 0) return idx + 1;
  }
  return 0;
}

/** Format degrees within a sign as 15°32'. */
export function fmtDegMin(deg: number): string {
  const d = Math.floor(deg);
  const m = Math.floor((deg - d) * 60);
  return `${d}°${String(m).padStart(2, "0")}'`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export const ALL_VARGAS = [
  "D1",
  "D2",
  "D3",
  "D4",
  "D7",
  "D9",
  "D10",
  "D12",
  "D16",
  "D20",
  "D24",
  "D27",
  "D30",
  "D40",
  "D45",
  "D60",
] as const;

export const VARGA_LABELS: Record<string, string> = {
  D1: "Rāśi (body, self)",
  D2: "Horā (wealth)",
  D3: "Drekkāṇa (siblings)",
  D4: "Chaturthāṁśa (fortune, home)",
  D7: "Saptāṁśa (children)",
  D9: "Navāṁśa (marriage, dharma)",
  D10: "Daśāṁśa (career)",
  D12: "Dvādaśāṁśa (parents)",
  D16: "Ṣoḍaśāṁśa (vehicles, comfort)",
  D20: "Viṁśāṁśa (spiritual life)",
  D24: "Chaturviṁśāṁśa (learning)",
  D27: "Saptaviṁśāṁśa (strength)",
  D30: "Triṁśāṁśa (misfortune)",
  D40: "Khavedāṁśa (maternal karma)",
  D45: "Akṣavedāṁśa (paternal karma)",
  D60: "Ṣaṣṭyāṁśa (past life)",
};
