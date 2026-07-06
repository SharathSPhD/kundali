// Typed client for the jyotisha engine. Calls go to /api/py/* — same-origin:
// in production Vercel routes this to the Python function (vercel.json);
// in dev, next.config.mjs rewrites it to the local FastAPI server. The
// Supabase access token is attached as a Bearer header when signed in.
//
// The engine contract is defined in ARCHITECTURE.md. Responses are
// normalized defensively so minor backend field-name variations don't
// break the UI.

import type { BirthData } from "./types";
import { planetAbbr, signNumber } from "./jyotisha";
import { createClient as createSupabaseClient } from "./supabase/client";

// ---------------------------------------------------------------------------
// Normalized view-model types
// ---------------------------------------------------------------------------

export interface PlanetPosition {
  planet: string;
  abbr: string;
  longitude: number;
  sign: number; // 1-12
  degInSign: number;
  nakshatra: string;
  pada: number | null;
  dignity: string | null;
  retrograde: boolean;
  combust: boolean;
  house: number | null;
}

export interface LagnaInfo {
  longitude: number;
  sign: number;
  degInSign: number;
  nakshatra: string;
  pada: number | null;
}

export interface ChartData {
  lagna: LagnaInfo;
  positions: PlanetPosition[];
}

export interface VargaPlacement {
  planet: string;
  abbr: string;
  sign: number;
  retrograde: boolean;
}

export interface VargaChart {
  name: string;
  lagnaSign: number;
  placements: VargaPlacement[];
}

export interface DashaPeriod {
  lord: string;
  start: string;
  end: string;
  level: number; // 1 maha, 2 antar, 3 pratyantar
  active: boolean;
  children: DashaPeriod[];
}

export interface TimeWindow {
  start: string | null;
  end: string | null;
  label: string;
}

export interface Prediction {
  area: string;
  score: number; // 0-100
  trend: string;
  windows: TimeWindow[];
  substantiation: string[];
}

export interface SadeSati {
  active: boolean;
  phase: string | null;
  start: string | null;
  end: string | null;
}

export interface GocharaEntry {
  planet: string;
  sign: number;
  houseFromMoon: number | null;
  favorable: boolean | null;
  note: string;
}

export interface TransitData {
  gochara: GocharaEntry[];
  sadeSati: SadeSati;
  doubleTransit: string[];
}

export interface Yoga {
  name: string;
  present: boolean;
  factors: string[];
  strength: string | null;
}

export interface Interpretation {
  text: string;
  citations: string[];
}

export interface PanchangaData {
  tithi: { number: number; name: string; paksha: string };
  vara: { name: string; lord: string };
  nakshatra: { name: string; pada: number | null; lord: string };
  yoga: { number: number; name: string };
  karana: { number: number; name: string };
  sunrise: string | null;
  sunset: string | null;
}

export interface KutaScore {
  name: string;
  points: number;
  max: number;
  details: string;
}

export interface MangalDoshaSide {
  manglik: boolean;
  effective: boolean;
  houseFromLagna: number | null;
  houseFromMoon: number | null;
  cancellations: string[];
}

export interface MoonSummary {
  signName: string;
  nakshatra: string;
  pada: number | null;
}

export interface MatchingData {
  kutas: KutaScore[];
  total: number;
  maxTotal: number;
  verdict: string;
  mangalDosha: {
    groom: MangalDoshaSide;
    bride: MangalDoshaSide;
    compatible: boolean;
    note: string;
  };
  groom: MoonSummary;
  bride: MoonSummary;
}

export interface ShadbalaRow {
  planet: string;
  abbr: string;
  sthana: number;
  dig: number;
  kala: number;
  cheshta: number;
  naisargika: number;
  drik: number;
  totalVirupas: number;
  totalRupas: number;
  requiredRupas: number;
  ratio: number;
  sufficient: boolean;
}

export interface CharaKaraka {
  karaka: string;
  abbr: string; // AK, AmK, BK, MK, PK, GK, DK
  planet: string;
  planetAbbr: string;
  sign: number; // 1-12
  degInSign: number;
}

export interface CharaPeriod {
  sign: number; // 1-12
  signName: string;
  level: number; // 1 maha, 2 antar
  years: number | null;
  lord: string;
  start: string;
  end: string;
  active: boolean;
  children: CharaPeriod[];
}

export interface JaiminiData {
  karakas: CharaKaraka[];
  direction: string;
  mahadashas: CharaPeriod[];
  activeMaha: CharaPeriod | null;
  activeAntar: CharaPeriod | null;
}

export interface RectificationEventMatch {
  event: string;
  date: string;
  activeMahadasha: string | null;
  activeAntardasha: string | null;
  relevantLords: string[];
  whyRelevant: string[];
  matched: string[];
  score: number;
}

export interface RectificationCandidate {
  time: string; // HH:MM:SS
  date: string;
  offsetMinutes: number;
  score: number;
  maxScore: number;
  lagnaSign: number; // 1-12
  lagnaSignName: string;
  lagnaDegree: number;
  events: RectificationEventMatch[];
}

export interface RectificationResult {
  inputTime: string;
  windowMinutes: number;
  stepMinutes: number;
  nCandidates: number;
  candidates: RectificationCandidate[];
}

export interface RectificationEventInput {
  type: string;
  date: string;
  note?: string;
}

// ---------------------------------------------------------------------------
// Low-level fetch through the proxy
// ---------------------------------------------------------------------------

export class EngineError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function post(path: string, body: unknown): Promise<any> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  // Attach the Supabase access token when signed in (the engine verifies it).
  try {
    const supabase = createSupabaseClient();
    if (supabase) {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }
    }
  } catch {
    /* local mode / no session */
  }
  const res = await fetch(`/api/py/${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let json: any = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    /* non-JSON error body */
  }
  if (!res.ok) {
    const detail =
      (json && (json.detail || json.error || json.message)) ||
      text ||
      `Engine request failed (${res.status})`;
    throw new EngineError(
      typeof detail === "string" ? detail : JSON.stringify(detail),
      res.status
    );
  }
  return json;
}

// ---------------------------------------------------------------------------
// Normalization helpers (defensive against key-name variations)
// ---------------------------------------------------------------------------

function num(v: unknown, fallback = 0): number {
  const n = typeof v === "string" ? Number(v) : (v as number);
  return typeof n === "number" && Number.isFinite(n) ? n : fallback;
}

function str(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}

function bool(v: unknown): boolean {
  return v === true || v === "true" || v === 1;
}

function pick(obj: any, ...keys: string[]): any {
  if (!obj || typeof obj !== "object") return undefined;
  for (const k of keys) {
    if (obj[k] !== undefined && obj[k] !== null) return obj[k];
  }
  return undefined;
}

function asArray(v: unknown): any[] {
  return Array.isArray(v) ? v : [];
}

function normalizePosition(raw: any, fallbackName: string): PlanetPosition {
  const planet = str(pick(raw, "planet", "name", "body"), fallbackName);
  const longitude = num(pick(raw, "longitude", "lon", "sidereal_longitude"));
  let sign = signNumber(pick(raw, "sign", "rashi", "sign_number", "sign_name"));
  if (!sign) sign = Math.floor((((longitude % 360) + 360) % 360) / 30) + 1;
  const degInSign = num(
    pick(raw, "deg_in_sign", "degree_in_sign", "degrees_in_sign", "sign_degree"),
    ((longitude % 30) + 30) % 30
  );
  const nakRaw = pick(raw, "nakshatra", "star");
  const nakshatra =
    typeof nakRaw === "string" ? nakRaw : str(pick(nakRaw, "name"));
  const padaRaw = pick(raw, "pada", "nakshatra_pada") ?? pick(nakRaw, "pada");
  const dignityRaw = pick(raw, "dignity", "dignity_status", "status");
  return {
    planet,
    abbr: planetAbbr(planet),
    longitude,
    sign,
    degInSign,
    nakshatra,
    pada: padaRaw !== undefined ? num(padaRaw) : null,
    dignity: dignityRaw !== undefined ? str(dignityRaw, null as any) : null,
    retrograde: bool(pick(raw, "retrograde", "retro", "is_retrograde")),
    combust: bool(pick(raw, "combust", "is_combust", "combusted")),
    house: pick(raw, "house", "bhava") !== undefined ? num(pick(raw, "house", "bhava")) : null,
  };
}

function normalizeChart(raw: any): ChartData {
  const posRaw = pick(raw, "positions", "planets", "grahas") ?? {};
  const positions: PlanetPosition[] = Array.isArray(posRaw)
    ? posRaw.map((p: any, i: number) => normalizePosition(p, `Planet ${i + 1}`))
    : Object.entries(posRaw).map(([name, p]) => normalizePosition(p, name));
  const lagnaRaw = pick(raw, "lagna", "ascendant", "asc") ?? {};
  const lagLon = num(pick(lagnaRaw, "longitude", "lon"));
  let lagSign = signNumber(pick(lagnaRaw, "sign", "rashi", "sign_name"));
  if (!lagSign) lagSign = Math.floor((((lagLon % 360) + 360) % 360) / 30) + 1;
  const lagNak = pick(lagnaRaw, "nakshatra");
  return {
    lagna: {
      longitude: lagLon,
      sign: lagSign,
      degInSign: num(
        pick(lagnaRaw, "deg_in_sign", "degree_in_sign"),
        ((lagLon % 30) + 30) % 30
      ),
      nakshatra: typeof lagNak === "string" ? lagNak : str(pick(lagNak, "name")),
      pada: pick(lagnaRaw, "pada") !== undefined ? num(pick(lagnaRaw, "pada")) : null,
    },
    positions: positions.filter(
      (p) => !["ascendant", "lagna", "as"].includes(p.planet.toLowerCase())
    ),
  };
}

function normalizeVargaChart(name: string, raw: any): VargaChart {
  const placementsRaw =
    pick(raw, "placements", "positions", "planets", "grahas") ?? raw ?? {};
  const entries: Array<[string, any]> = Array.isArray(placementsRaw)
    ? placementsRaw.map((p: any, i: number) => [
        str(pick(p, "planet", "name", "body"), `P${i + 1}`),
        p,
      ])
    : Object.entries(placementsRaw);
  const placements: VargaPlacement[] = [];
  const lagnaRaw = pick(raw, "lagna_sign", "lagna", "ascendant_sign", "lagna_rasi");
  let lagnaSign =
    lagnaRaw && typeof lagnaRaw === "object"
      ? signNumber(pick(lagnaRaw, "sign", "rashi", "sign_number", "sign_name"))
      : signNumber(lagnaRaw);
  for (const [pname, p] of entries) {
    const sign =
      typeof p === "number" || typeof p === "string"
        ? signNumber(p)
        : signNumber(pick(p, "sign", "rashi", "sign_number", "sign_name"));
    if (!sign) continue;
    if (["ascendant", "lagna", "as"].includes(pname.toLowerCase())) {
      lagnaSign = sign;
      continue;
    }
    placements.push({
      planet: pname,
      abbr: planetAbbr(pname),
      sign,
      retrograde: bool(pick(p, "retrograde", "retro")),
    });
  }
  return { name, lagnaSign: lagnaSign || 1, placements };
}

function normalizeVargas(raw: any): VargaChart[] {
  const charts = pick(raw, "charts", "vargas") ?? raw ?? {};
  if (Array.isArray(charts)) {
    return charts.map((c: any, i: number) =>
      normalizeVargaChart(str(pick(c, "name", "chart", "varga"), `D${i}`), c)
    );
  }
  return Object.entries(charts)
    .filter(([k]) => /^D\d+$/i.test(k))
    .map(([k, v]) => normalizeVargaChart(k.toUpperCase(), v));
}

function normalizeDashaNode(raw: any, level: number, now: Date): DashaPeriod {
  const start = str(pick(raw, "start", "from", "start_date", "begin"));
  const end = str(pick(raw, "end", "to", "end_date"));
  const childrenRaw = asArray(
    pick(raw, "children", "sub", "sub_periods", "antardashas", "periods")
  );
  const explicitActive = pick(raw, "active", "is_active", "current");
  const startD = new Date(start);
  const endD = new Date(end);
  const inRange =
    !Number.isNaN(startD.getTime()) &&
    !Number.isNaN(endD.getTime()) &&
    now >= startD &&
    now < endD;
  return {
    lord: str(pick(raw, "lord", "planet", "name"), "?"),
    start,
    end,
    level,
    active: explicitActive !== undefined ? bool(explicitActive) : inRange,
    children: childrenRaw.map((c) => normalizeDashaNode(c, level + 1, now)),
  };
}

function normalizeDashas(raw: any): DashaPeriod[] {
  const now = new Date();
  // The engine returns { tree: { periods: [...] }, active, on }. Unwrap the
  // tree object first, then read its periods; fall back to a flat array shape.
  const treeRaw = pick(raw, "tree", "dashas", "mahadashas") ?? raw;
  const periods = asArray(
    pick(treeRaw, "periods", "mahadashas", "children") ?? treeRaw
  );
  return periods.map((n) => normalizeDashaNode(n, 1, now));
}

function normalizeWindow(raw: any): TimeWindow {
  if (typeof raw === "string") return { start: raw, end: null, label: raw };
  return {
    start: str(pick(raw, "start", "from", "begin"), null as any),
    end: str(pick(raw, "end", "to"), null as any),
    label: str(pick(raw, "label", "description", "reason")),
  };
}

function normalizePrediction(raw: any): Prediction {
  let score = num(pick(raw, "score", "value", "rating"), 0);
  if (score > 0 && score <= 1) score = Math.round(score * 100);
  score = Math.max(0, Math.min(100, Math.round(score)));
  const subsRaw = asArray(
    pick(raw, "substantiation", "facts", "evidence", "indications", "trail")
  );
  const substantiation = subsRaw.map((s) =>
    typeof s === "string"
      ? s
      : str(
          pick(s, "text", "fact", "description", "detail", "reason"),
          JSON.stringify(s)
        )
  );
  return {
    area: str(pick(raw, "area", "life_area", "domain", "category"), "general"),
    score,
    trend: str(pick(raw, "trend", "direction"), "steady"),
    windows: asArray(pick(raw, "windows", "time_windows", "periods")).map(
      normalizeWindow
    ),
    substantiation,
  };
}

function normalizePredictions(raw: any): Prediction[] {
  const list = pick(raw, "predictions", "indications", "areas") ?? raw;
  if (Array.isArray(list)) return list.map(normalizePrediction);
  if (list && typeof list === "object") {
    return Object.entries(list).map(([area, v]: [string, any]) =>
      normalizePrediction({ area, ...(typeof v === "object" ? v : { score: v }) })
    );
  }
  return [];
}

function normalizeTransits(raw: any): TransitData {
  const gocharaRaw = pick(raw, "gochara", "transits", "table") ?? [];
  const gochara: GocharaEntry[] = (
    Array.isArray(gocharaRaw) ? gocharaRaw : Object.entries(gocharaRaw).map(
      ([planet, v]: [string, any]) => ({ planet, ...(typeof v === "object" ? v : { sign: v }) })
    )
  ).map((g: any) => {
    const favRaw = pick(g, "favorable", "is_favorable", "benefic");
    const houseRaw = pick(g, "house_from_moon", "from_moon", "moon_house");
    return {
      planet: str(pick(g, "planet", "name", "body"), "?"),
      sign: signNumber(pick(g, "sign", "rashi", "sign_name")),
      houseFromMoon: houseRaw !== undefined ? num(houseRaw) : null,
      favorable: favRaw !== undefined ? bool(favRaw) : null,
      note: str(pick(g, "note", "result", "effect", "description")),
    };
  });
  const ssRaw = pick(raw, "sade_sati", "sadesati", "sadeSati") ?? {};
  const sadeSati: SadeSati = {
    active: bool(pick(ssRaw, "active", "is_active", "in_sade_sati")),
    phase: str(pick(ssRaw, "phase", "stage"), null as any),
    start: str(pick(ssRaw, "start", "from"), null as any),
    end: str(pick(ssRaw, "end", "to"), null as any),
  };
  const dtRaw = pick(raw, "double_transit", "doubleTransit") ?? [];
  const doubleTransit = asArray(dtRaw).map((d) =>
    typeof d === "string"
      ? d
      : `House ${num(pick(d, "house"))}${
          str(pick(d, "note", "description")) ? ` — ${str(pick(d, "note", "description"))}` : ""
        }`
  );
  return { gochara, sadeSati, doubleTransit };
}

function normalizeYogas(raw: any): Yoga[] {
  const list = asArray(pick(raw, "yogas", "results") ?? raw);
  return list.map((y: any) => ({
    name: str(pick(y, "name", "yoga"), "Unknown yoga"),
    present: bool(pick(y, "present", "is_present", "active")),
    factors: asArray(pick(y, "factors", "conditions", "reasons")).map((f) =>
      typeof f === "string" ? f : JSON.stringify(f)
    ),
    strength:
      pick(y, "strength", "grade") !== undefined
        ? String(pick(y, "strength", "grade"))
        : null,
  }));
}

function normalizeInterpretation(raw: any): Interpretation {
  const text = str(
    pick(raw, "text", "answer", "reading", "narration", "content"),
    typeof raw === "string" ? raw : ""
  );
  const citations = asArray(pick(raw, "citations", "grounding", "sources")).map(
    (c) =>
      typeof c === "string"
        ? c
        : str(pick(c, "text", "label", "fact", "id"), JSON.stringify(c))
  );
  return { text, citations };
}

function normalizePanchanga(raw: any): PanchangaData {
  const tithi = pick(raw, "tithi") ?? {};
  const vara = pick(raw, "vara", "weekday") ?? {};
  const nak = pick(raw, "nakshatra", "star") ?? {};
  const yoga = pick(raw, "yoga") ?? {};
  const karana = pick(raw, "karana") ?? {};
  return {
    tithi: {
      number: num(pick(tithi, "number", "index")),
      name: str(pick(tithi, "name"), "—"),
      paksha: str(pick(tithi, "paksha"), ""),
    },
    vara: {
      name: str(pick(vara, "name"), "—"),
      lord: str(pick(vara, "lord"), ""),
    },
    nakshatra: {
      name: str(pick(nak, "name"), "—"),
      pada: pick(nak, "pada") !== undefined ? num(pick(nak, "pada")) : null,
      lord: str(pick(nak, "lord"), ""),
    },
    yoga: { number: num(pick(yoga, "number")), name: str(pick(yoga, "name"), "—") },
    karana: {
      number: num(pick(karana, "number")),
      name: str(pick(karana, "name"), "—"),
    },
    sunrise: str(pick(raw, "sunrise"), null as any),
    sunset: str(pick(raw, "sunset"), null as any),
  };
}

function normalizeMangalSide(raw: any): MangalDoshaSide {
  const hl = pick(raw, "mars_house_from_lagna", "house_from_lagna");
  const hm = pick(raw, "mars_house_from_moon", "house_from_moon");
  return {
    manglik: bool(pick(raw, "manglik", "is_manglik")),
    effective: bool(pick(raw, "effective", "effective_manglik")),
    houseFromLagna: hl !== undefined ? num(hl) : null,
    houseFromMoon: hm !== undefined ? num(hm) : null,
    cancellations: asArray(pick(raw, "cancellations", "cancellation_reasons")).map(
      (c) => (typeof c === "string" ? c : JSON.stringify(c))
    ),
  };
}

function normalizeMoonSummary(raw: any): MoonSummary {
  return {
    signName: str(pick(raw, "sign_name", "signName", "moon_sign"), "—"),
    nakshatra: str(pick(raw, "nakshatra"), "—"),
    pada: pick(raw, "pada") !== undefined ? num(pick(raw, "pada")) : null,
  };
}

function normalizeMatching(raw: any): MatchingData {
  const kutas: KutaScore[] = asArray(pick(raw, "kutas", "gunas")).map((k: any) => ({
    name: str(pick(k, "name", "kuta"), "?"),
    points: num(pick(k, "points", "score")),
    max: num(pick(k, "max", "max_points"), 0),
    details: str(pick(k, "details", "detail", "description")),
  }));
  const md = pick(raw, "mangal_dosha", "mangalDosha") ?? {};
  return {
    kutas,
    total: num(pick(raw, "total", "total_points")),
    maxTotal: num(pick(raw, "max_total", "maxTotal"), 36),
    verdict: str(pick(raw, "verdict", "recommendation"), ""),
    mangalDosha: {
      groom: normalizeMangalSide(pick(md, "groom") ?? {}),
      bride: normalizeMangalSide(pick(md, "bride") ?? {}),
      compatible: bool(pick(md, "compatible")),
      note: str(pick(md, "note", "summary")),
    },
    groom: normalizeMoonSummary(pick(raw, "groom") ?? {}),
    bride: normalizeMoonSummary(pick(raw, "bride") ?? {}),
  };
}

const PLANET_ORDER = [
  "Sun",
  "Moon",
  "Mars",
  "Mercury",
  "Jupiter",
  "Venus",
  "Saturn",
];

function normalizeShadbala(raw: any): ShadbalaRow[] {
  const planetsRaw = pick(raw, "planets", "table", "shadbala") ?? {};
  const entries: Array<[string, any]> = Array.isArray(planetsRaw)
    ? planetsRaw.map((p: any, i: number) => [
        str(pick(p, "planet", "name"), `P${i + 1}`),
        p,
      ])
    : Object.entries(planetsRaw);
  const rows = entries.map(([name, p]): ShadbalaRow => {
    const totalRupas = num(pick(p, "total_rupas", "totalRupas", "rupas"));
    const requiredRupas = num(
      pick(p, "required_rupas", "requiredRupas", "required"),
      5
    );
    const ratioRaw = pick(p, "ratio", "strength_ratio");
    return {
      planet: name,
      abbr: planetAbbr(name),
      sthana: num(pick(p, "sthana", "sthana_bala")),
      dig: num(pick(p, "dig", "dig_bala")),
      kala: num(pick(p, "kala", "kala_bala")),
      cheshta: num(pick(p, "cheshta", "cheshta_bala")),
      naisargika: num(pick(p, "naisargika", "naisargika_bala")),
      drik: num(pick(p, "drik", "drik_bala")),
      totalVirupas: num(
        pick(p, "total_virupas", "totalVirupas"),
        totalRupas * 60
      ),
      totalRupas,
      requiredRupas,
      ratio:
        ratioRaw !== undefined
          ? num(ratioRaw)
          : requiredRupas > 0
            ? totalRupas / requiredRupas
            : 0,
      sufficient:
        pick(p, "sufficient") !== undefined
          ? bool(pick(p, "sufficient"))
          : totalRupas >= requiredRupas,
    };
  });
  rows.sort(
    (a, b) => PLANET_ORDER.indexOf(a.planet) - PLANET_ORDER.indexOf(b.planet)
  );
  return rows;
}

function normalizeCharaPeriod(raw: any, level: number, now: Date): CharaPeriod {
  const start = str(pick(raw, "start", "from"));
  const end = str(pick(raw, "end", "to"));
  const startD = new Date(start);
  const endD = new Date(end);
  const inRange =
    !Number.isNaN(startD.getTime()) &&
    !Number.isNaN(endD.getTime()) &&
    now >= startD &&
    now < endD;
  const yearsRaw = pick(raw, "years", "duration_years");
  return {
    sign: signNumber(pick(raw, "sign", "rashi", "sign_name")),
    signName: str(pick(raw, "sign_name", "signName"), "?"),
    level: num(pick(raw, "level"), level),
    years: yearsRaw !== undefined ? num(yearsRaw) : null,
    lord: str(pick(raw, "lord", "dasha_lord")),
    start,
    end,
    active: inRange,
    children: asArray(pick(raw, "children", "antardashas", "sub")).map((c) =>
      normalizeCharaPeriod(c, level + 1, now)
    ),
  };
}

function normalizeJaimini(raw: any): JaiminiData {
  const now = new Date();
  const karakas: CharaKaraka[] = asArray(pick(raw, "karakas", "chara_karakas")).map(
    (k: any) => ({
      karaka: str(pick(k, "karaka", "name"), "?"),
      abbr: str(pick(k, "abbr", "short"), "?"),
      planet: str(pick(k, "planet", "graha"), "?"),
      planetAbbr: planetAbbr(str(pick(k, "planet", "graha"), "?")),
      sign: signNumber(pick(k, "sign", "sign_name")),
      degInSign: num(pick(k, "degree_in_sign", "deg_in_sign", "degree")),
    })
  );
  const tree = pick(raw, "chara_dasha", "charaDasha", "dasha") ?? {};
  const mahadashas = asArray(pick(tree, "periods", "mahadashas")).map((p) =>
    normalizeCharaPeriod(p, 1, now)
  );
  const activeRaw = asArray(pick(raw, "active", "active_path"));
  const activeMaha =
    activeRaw.length > 0
      ? normalizeCharaPeriod(activeRaw[0], 1, now)
      : mahadashas.find((m) => m.active) ?? null;
  const activeAntar =
    activeRaw.length > 1
      ? normalizeCharaPeriod(activeRaw[1], 2, now)
      : activeMaha?.children.find((c) => c.active) ?? null;
  return {
    karakas,
    direction: str(pick(tree, "direction"), ""),
    mahadashas,
    activeMaha,
    activeAntar,
  };
}

function normalizeRectificationCandidate(raw: any): RectificationCandidate {
  return {
    time: str(pick(raw, "time")),
    date: str(pick(raw, "date")),
    offsetMinutes: num(pick(raw, "offset_minutes", "offsetMinutes")),
    score: num(pick(raw, "score")),
    maxScore: num(pick(raw, "max_score", "maxScore"), 1),
    lagnaSign: signNumber(pick(raw, "lagna_sign_name", "lagna_sign")),
    lagnaSignName: str(pick(raw, "lagna_sign_name", "lagnaSignName")),
    lagnaDegree: num(pick(raw, "lagna_degree", "lagnaDegree")),
    events: asArray(pick(raw, "events")).map(
      (e: any): RectificationEventMatch => ({
        event: str(pick(e, "event", "type")),
        date: str(pick(e, "date")),
        activeMahadasha: str(pick(e, "active_mahadasha"), null as any),
        activeAntardasha: str(pick(e, "active_antardasha"), null as any),
        relevantLords: asArray(pick(e, "relevant_lords")).map((l) => str(l)),
        whyRelevant: asArray(pick(e, "why_relevant")).map((w) => str(w)),
        matched: asArray(pick(e, "matched")).map((m) => str(m)),
        score: num(pick(e, "score")),
      })
    ),
  };
}

function normalizeRectification(raw: any): RectificationResult {
  return {
    inputTime: str(pick(raw, "input_time", "inputTime")),
    windowMinutes: num(pick(raw, "window_minutes", "windowMinutes")),
    stepMinutes: num(pick(raw, "step_minutes", "stepMinutes")),
    nCandidates: num(pick(raw, "n_candidates", "nCandidates")),
    candidates: asArray(pick(raw, "candidates")).map(
      normalizeRectificationCandidate
    ),
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function fetchChart(birth: BirthData): Promise<ChartData> {
  return normalizeChart(await post("chart", { birth }));
}

export async function fetchVargas(
  birth: BirthData,
  charts?: string[]
): Promise<VargaChart[]> {
  return normalizeVargas(await post("vargas", { birth, charts }));
}

export async function fetchDashas(
  birth: BirthData,
  levels = 3
): Promise<DashaPeriod[]> {
  return normalizeDashas(await post("dashas", { birth, levels }));
}

export async function fetchTransits(
  birth: BirthData,
  on?: string
): Promise<TransitData> {
  return normalizeTransits(await post("transits", { birth, on }));
}

export async function fetchYogas(birth: BirthData): Promise<Yoga[]> {
  return normalizeYogas(await post("yogas", { birth }));
}

export async function fetchPredictions(
  birth: BirthData,
  on?: string
): Promise<Prediction[]> {
  return normalizePredictions(await post("predictions", { birth, on }));
}

export async function fetchPanchanga(birth: BirthData): Promise<PanchangaData> {
  return normalizePanchanga(await post("panchanga", { birth }));
}

export async function fetchMatching(
  groom: BirthData,
  bride: BirthData
): Promise<MatchingData> {
  return normalizeMatching(await post("matching", { groom, bride }));
}

export async function fetchShadbala(birth: BirthData): Promise<ShadbalaRow[]> {
  return normalizeShadbala(await post("shadbala", { birth }));
}

export async function fetchJaimini(
  birth: BirthData,
  on?: string
): Promise<JaiminiData> {
  return normalizeJaimini(await post("jaimini", { birth, on }));
}

export async function fetchRectification(
  birth: BirthData,
  windowMinutes: number,
  events: RectificationEventInput[],
  stepMinutes = 2
): Promise<RectificationResult> {
  return normalizeRectification(
    await post("rectify", {
      birth,
      window_minutes: windowMinutes,
      step_minutes: stepMinutes,
      events,
    })
  );
}

export async function interpret(
  birth: BirthData,
  question: string,
  provider?: string
): Promise<Interpretation> {
  return normalizeInterpretation(
    await post("interpret", { birth, question, provider })
  );
}
