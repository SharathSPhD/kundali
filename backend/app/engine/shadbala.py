"""Shadbala — six-fold planetary strength in virupas (60 virupas = 1 rupa).

Follows B.V. Raman ("Graha and Bhava Balas") / BPHS conventions; where the
tradition forks, the Raman/PyJHora variant is chosen and documented inline.
Computed for the 7 classical planets only (nodes have no shadbala).

Fork decisions (summary — details at each function):
- Saptavargaja uses the Raman score table (moolatrikona 45 ... great-enemy
  1.875) with compound (panchadha) friendship: natural + temporal, temporal
  relations taken from the D1 (rasi) positions and applied to all vargas.
- Nathonnata uses local mean time (longitude-based) midnight distance.
- Abda/Masa lords use the simplified 360-day-year Kali ahargana method
  (PyJHora-style): each 360-day "year" advances the year lord by 3 weekdays,
  each 30-day "month" by 2.
- Ayana bala uses 30*(23.45 + effective_declination)/23.45 with Raman's
  planet rules (Sun/Mars/Jupiter/Venus north-strong, Moon/Saturn
  south-strong, Mercury always strong); Sun's value doubled.
- Cheshta bala for Mars..Saturn is a documented discrete approximation of
  the seeghrocha method (exact method needs mean longitudes); Sun's cheshta
  = its ayana bala, Moon's = its paksha bala (Raman convention).
- Drik bala replicates PyJHora's sputa-drishti piecewise curve including its
  additive special aspects (Mars 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th)
  for cross-tool parity; benefic aspects add, malefic subtract, net / 4.
- Yuddha (planetary war) bala is NOT implemented — it is rare, requires
  disc-diameter tables, and Raman treats it as a correction; documented gap.
"""
from __future__ import annotations

import math
from datetime import timedelta

import swisseph as swe

from . import constants as K
from . import vargas as V
from .chart import build_chart
from .ephemeris import BirthData, EngineConfig, julian_day_from_utc
from .panchanga import VARA_LORDS, _sun_rise_or_set, most_recent_sunrise

PLANETS7 = list(K.CLASSICAL_PLANETS)  # Sun..Saturn

# Minimum required strength in rupas (B.V. Raman, Graha and Bhava Balas).
REQUIRED_RUPAS = {
    "Sun": 6.5, "Moon": 6.0, "Mars": 5.0, "Mercury": 7.0,
    "Jupiter": 6.5, "Venus": 5.5, "Saturn": 5.0,
}

# Naisargika (natural) bala in virupas — fixed classical sequence.
NAISARGIKA = {
    "Sun": 60.0, "Moon": 51.4286, "Venus": 42.8571, "Jupiter": 34.2857,
    "Mercury": 25.7143, "Mars": 17.1429, "Saturn": 8.5714,
}

# Dig bala: house (from lagna, whole-sign) where each planet is strongest.
DIG_STRONG_HOUSE = {
    "Jupiter": 1, "Mercury": 1,   # lagna
    "Sun": 10, "Mars": 10,        # 10th
    "Saturn": 7,                  # 7th
    "Moon": 4, "Venus": 4,        # 4th
}

# Saptavargaja: the seven vargas and the Raman dignity score table (virupas).
SAPTAVARGA = ("D1", "D2", "D3", "D7", "D9", "D12", "D30")
SAPTAVARGAJA_SCORES = {
    "moolatrikona": 45.0, "own": 30.0, "great_friend": 22.5, "friend": 15.0,
    "neutral": 7.5, "enemy": 3.75, "great_enemy": 1.875,
}

# Temporal (tatkalika) friend: occupies 2,3,4,10,11 or 12 from the planet.
_TEMPORAL_FRIEND_OFFSETS = {2, 3, 4, 10, 11, 12}

# Compound (panchadha) relation: natural x temporal.
_COMPOUND = {
    ("friend", "friend"): "great_friend",
    ("neutral", "friend"): "friend",
    ("enemy", "friend"): "neutral",
    ("friend", "enemy"): "neutral",
    ("neutral", "enemy"): "enemy",
    ("enemy", "enemy"): "great_enemy",
}

# Mean daily motions (deg/day) — commonly cited averages, used only by the
# discrete cheshta approximation.
MEAN_SPEED = {
    "Mars": 0.5240, "Mercury": 1.3833, "Jupiter": 0.0831,
    "Venus": 1.2000, "Saturn": 0.0334,
}

# Chaldean descending order for hora succession (first hora = vara lord).
_CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]

# Kali epoch: JD 588465.5 (Feb 18, 3102 BCE), traditionally a Friday.
_KALI_EPOCH_JD = 588465.5
_KALI_EPOCH_WEEKDAY = 5  # Friday (0=Sunday in VARA_LORDS indexing)

_OBLIQUITY = 23.45  # mean obliquity used by the classical ayana formula


def _fold180(x: float) -> float:
    """Fold an angle into 0..180 (angular distance)."""
    x = abs(x) % 360.0
    return 360.0 - x if x > 180.0 else x


# ---------------------------------------------------------------------------
# 1. Sthana bala
# ---------------------------------------------------------------------------

def uccha_bala(planet: str, lon: float) -> float:
    """Exaltation strength: folded distance from the deep-debilitation point
    / 3. 60 at deep exaltation, 0 at deep debilitation."""
    deb_sign, deb_deg = K.DEBILITATION[planet]
    deb_lon = deb_sign * 30.0 + deb_deg
    return _fold180(lon - deb_lon) / 3.0


def temporal_relations(chart: dict) -> dict:
    """planet -> set of temporal friends, from D1 sign positions.

    A planet in the 2nd,3rd,4th,10th,11th,12th sign from another is that
    planet's temporal friend; all others (incl. co-tenants) are temporal
    enemies (BPHS)."""
    signs = {p: chart["planets"][p]["sign"] for p in PLANETS7}
    out: dict[str, set] = {}
    for p in PLANETS7:
        friends = set()
        for o in PLANETS7:
            if o == p:
                continue
            offset = (signs[o] - signs[p]) % 12 + 1
            if offset in _TEMPORAL_FRIEND_OFFSETS:
                friends.add(o)
        out[p] = friends
    return out


def compound_relation(planet: str, other: str, temp_friends: dict) -> str:
    natural = K.natural_relation(planet, other)
    temporal = "friend" if other in temp_friends[planet] else "enemy"
    return _COMPOUND[(natural, temporal)]


def saptavargaja_bala(planet: str, lon: float, temp_friends: dict) -> dict:
    """Dignity score summed over D1,D2,D3,D7,D9,D12,D30 (Raman table).

    Convention: moolatrikona is degree-checked in D1 only; in the other six
    vargas a hit on the moolatrikona *sign* is scored as moolatrikona
    (sign-level check — degrees have no meaning in a varga sign). Compound
    friendship uses natal (D1) temporal relations for all vargas (BPHS)."""
    mt = K.MOOLATRIKONA.get(planet)
    per_varga = {}
    total = 0.0
    for v in SAPTAVARGA:
        vsign = V.VARGA_FUNCS[v](lon)
        if mt and vsign == mt[0] and (
                v != "D1" or mt[1] <= (lon % 30.0) < mt[2]):
            key = "moolatrikona"
        elif vsign in K.OWN_SIGNS.get(planet, set()):
            key = "own"
        else:
            key = compound_relation(planet, K.SIGN_LORDS[vsign], temp_friends)
        per_varga[v] = {"sign": vsign, "dignity": key,
                        "virupas": SAPTAVARGAJA_SCORES[key]}
        total += SAPTAVARGAJA_SCORES[key]
    return {"total": total, "vargas": per_varga}


def ojayugma_bala(planet: str, lon: float) -> float:
    """Sun/Mars/Jupiter/Mercury/Saturn: +15 each for odd rasi and odd
    navamsa; Moon/Venus: +15 each for even. Max 30."""
    rasi = int((lon % 360.0) // 30)
    nav = V.d9(lon)
    wants_odd = planet in {"Sun", "Mars", "Jupiter", "Mercury", "Saturn"}
    score = 0.0
    for s in (rasi, nav):
        odd = s in K.ODD_SIGNS
        if odd == wants_odd:
            score += 15.0
    return score


def kendradi_bala(house: int) -> float:
    if house in K.KENDRA_HOUSES:
        return 60.0
    if house in {2, 5, 8, 11}:  # panapara
        return 30.0
    return 15.0                 # apoklima


def drekkana_bala(planet: str, degree_in_sign: float) -> float:
    """1st decanate: Sun/Mars/Jupiter (male); 2nd: Mercury/Saturn (neuter);
    3rd: Moon/Venus (female) — 15 virupas each."""
    dec = min(int(degree_in_sign // 10.0), 2)
    groups = {0: {"Sun", "Mars", "Jupiter"}, 1: {"Mercury", "Saturn"},
              2: {"Moon", "Venus"}}
    return 15.0 if planet in groups[dec] else 0.0


# ---------------------------------------------------------------------------
# 2. Dig bala
# ---------------------------------------------------------------------------

def dig_bala(planet: str, lon: float, lagna_sign: int) -> float:
    """Directional strength: folded angular distance from the weakest point
    / 3. Whole-sign convention: the weakest point is the midpoint (15 deg) of
    the sign occupying the house opposite the planet's strength house."""
    strong = DIG_STRONG_HOUSE[planet]
    opp_house = (strong + 5) % 12 + 1  # strong + 6, 1-based
    opp_sign = (lagna_sign + opp_house - 1) % 12
    weakest = opp_sign * 30.0 + 15.0
    return _fold180(lon - weakest) / 3.0


# ---------------------------------------------------------------------------
# 3. Kala bala
# ---------------------------------------------------------------------------

def nathonnata_bala(lmt_hours: float) -> dict:
    """Diurnal/nocturnal strength from local-mean-time distance to midnight.
    t = |hours from LMT midnight| * 15 in 0..180. Sun/Jupiter/Venus (diurnal)
    get t/3 (strong at noon); Moon/Mars/Saturn (nocturnal) get (180-t)/3;
    Mercury always 60. Convention: LMT = UT + longitude/15 (classical texts
    predate timezones)."""
    t = min(lmt_hours % 24.0, 24.0 - lmt_hours % 24.0) * 15.0
    out = {}
    for p in PLANETS7:
        if p == "Mercury":
            out[p] = 60.0
        elif p in {"Sun", "Jupiter", "Venus"}:
            out[p] = t / 3.0
        else:
            out[p] = (180.0 - t) / 3.0
    return out


def paksha_bala(sun_lon: float, moon_lon: float) -> dict:
    """d = folded Moon-Sun elongation (0..180). Benefics get d/3, malefics
    (180-d)/3. Simplified benefic set (documented): Jupiter, Venus, Mercury
    always; Moon when waxing. Moon's value is doubled (BPHS/Raman)."""
    elong = (moon_lon - sun_lon) % 360.0
    waxing = elong < 180.0
    d = _fold180(elong)
    out = {}
    for p in PLANETS7:
        benefic = p in {"Jupiter", "Venus", "Mercury"} or (p == "Moon" and waxing)
        val = d / 3.0 if benefic else (180.0 - d) / 3.0
        if p == "Moon":
            val *= 2.0
        out[p] = val
    return out


def tribhaga_bala(jd: float, sunrise_jd, sunset_jd, next_sunrise_jd) -> dict:
    """Day (sunrise-sunset) thirds are lorded by Mercury/Sun/Saturn; night
    thirds by Moon/Venus/Mars. The lord of the birth third gets 60; Jupiter
    always gets 60. Polar fallback: only Jupiter scores."""
    out = {p: 0.0 for p in PLANETS7}
    out["Jupiter"] = 60.0
    if sunrise_jd is None or sunset_jd is None:
        return out
    if jd < sunset_jd:  # daytime (sunrise_jd <= jd by construction)
        part = min(int((jd - sunrise_jd) / (sunset_jd - sunrise_jd) * 3.0), 2)
        lord = ["Mercury", "Sun", "Saturn"][part]
    else:               # night: sunset -> next sunrise
        if next_sunrise_jd is None:
            return out
        part = min(int((jd - sunset_jd) / (next_sunrise_jd - sunset_jd) * 3.0), 2)
        lord = ["Moon", "Venus", "Mars"][part]
    out[lord] = max(out[lord], 60.0)
    return out


def abda_masa_lords(jd: float) -> tuple[str, str]:
    """Year (abda) and month (masa) lords via the simplified 360-day-year
    Kali ahargana method (PyJHora-style): the lord is the weekday lord of the
    first day of the current 360-day year / 30-day month counted from the
    Kali epoch (JD 588465.5, a Friday)."""
    ahargana = int(math.floor(jd - _KALI_EPOCH_JD))
    year_start = ahargana - ahargana % 360
    month_start = ahargana - ahargana % 30
    abda = VARA_LORDS[(_KALI_EPOCH_WEEKDAY + year_start) % 7]
    masa = VARA_LORDS[(_KALI_EPOCH_WEEKDAY + month_start) % 7]
    return abda, masa


def vara_hora_lords(jd: float, sunrise_jd, tz_offset: float,
                    birth_local_dt) -> tuple[str, str]:
    """Vara lord = weekday lord of the most recent sunrise (Vedic day runs
    sunrise to sunrise). Hora lord: 1-hour horas from sunrise, first hora
    lorded by the vara lord, succession in Chaldean descending order."""
    from .ephemeris import jd_to_utc_datetime
    if sunrise_jd is None:  # polar fallback: civil local date weekday
        vara_idx = (birth_local_dt.weekday() + 1) % 7
        hora_idx = birth_local_dt.hour
    else:
        local_rise = jd_to_utc_datetime(sunrise_jd) + timedelta(hours=tz_offset)
        vara_idx = (local_rise.weekday() + 1) % 7
        hora_idx = int((jd - sunrise_jd) * 24.0)
    vara_lord = VARA_LORDS[vara_idx]
    hora_lord = _CHALDEAN[(_CHALDEAN.index(vara_lord) + hora_idx) % 7]
    return vara_lord, hora_lord


def declinations(jd: float, config: EngineConfig) -> dict:
    """True equatorial declination (degrees) per classical planet."""
    from .ephemeris import _PLANET_IDS
    flags = config.ephe_flag | swe.FLG_EQUATORIAL  # tropical equatorial
    out = {}
    for name in PLANETS7:
        pos, _ = swe.calc_ut(jd, _PLANET_IDS[name], flags)
        out[name] = pos[1]
    return out


def ayana_bala(decls: dict) -> dict:
    """30*(23.45 + effective_declination)/23.45, clamped to 0..60.
    Raman rules: Sun/Mars/Jupiter/Venus strong with north declination;
    Moon/Saturn strong with south; Mercury always strong (|decl|).
    Sun's ayana bala is doubled (BPHS/Raman)."""
    out = {}
    for p in PLANETS7:
        d = decls[p]
        if p == "Mercury":
            eff = abs(d)
        elif p in {"Moon", "Saturn"}:
            eff = -d
        else:
            eff = d
        val = 30.0 * (_OBLIQUITY + eff) / _OBLIQUITY
        val = max(0.0, min(60.0, val))
        if p == "Sun":
            val *= 2.0
        out[p] = val
    return out


# ---------------------------------------------------------------------------
# 4. Cheshta bala
# ---------------------------------------------------------------------------

def cheshta_bala_approx(planet: str, speed: float) -> float:
    """Discrete retrograde-aware approximation (documented; the exact
    seeghrocha kendra method needs mean longitudes, out of scope):
    - retrograde: 60 (vakra)
    - near-stationary (|speed| < 10% of mean): 30 (per task spec)
    - slow direct (<= mean speed): 15 + 15*(speed/mean)  -> 16.5..30
    - fast direct (> mean): 30 + 15*min(speed/mean - 1, 1) -> 30..45
    The stationary/slow discontinuity is an artifact of the discrete bands
    and is accepted as part of the approximation."""
    mean = MEAN_SPEED[planet]
    if speed < 0:
        return 60.0
    ratio = speed / mean
    if ratio < 0.1:
        return 30.0
    if ratio <= 1.0:
        return 15.0 + 15.0 * ratio
    return 30.0 + 15.0 * min(ratio - 1.0, 1.0)


# ---------------------------------------------------------------------------
# 6. Drik bala
# ---------------------------------------------------------------------------

def sputa_drishti(angle: float, aspecting: str) -> float:
    """Graduated (sputa) graha drishti in virupas for the directed angle
    aspecting -> aspected (0..360). Base piecewise per BPHS ch.26 with
    PyJHora's ADDITIVE special-aspect bonuses (Mars +15 in the 4th/8th bands,
    Jupiter +30 in the 5th/9th, Saturn +45 in the 3rd/10th), reproducing 60
    at the exact special angles. Matches PyJHora __drik_bala_calc_1 (values
    may exceed 60 inside special bands; kept uncapped for parity)."""
    a = angle % 360.0
    if a < 30.0:
        v = 0.0
    elif a < 60.0:
        v = 0.5 * (a - 30.0)
    elif a < 90.0:
        v = (a - 60.0) + 15.0
        if aspecting == "Saturn":
            v += 45.0
    elif a < 120.0:
        v = 0.5 * (120.0 - a) + 30.0
        if aspecting == "Mars":
            v += 15.0
    elif a < 150.0:
        v = 150.0 - a
        if aspecting == "Jupiter":
            v += 30.0
    elif a < 180.0:
        v = 2.0 * (a - 150.0)
    elif a < 300.0:
        v = 0.5 * (300.0 - a)
        if aspecting == "Mars" and 210.0 <= a < 240.0:
            v += 15.0
        elif aspecting == "Jupiter" and 240.0 <= a < 270.0:
            v += 30.0
        elif aspecting == "Saturn" and 270.0 <= a < 300.0:
            v += 45.0
    else:
        v = 0.0
    return v


def drik_benefics(chart: dict) -> set:
    """Benefic set for drik bala (PVR/PyJHora method: Jupiter+Venus natural;
    Moon benefic when waxing; Mercury benefic when alone in its sign or with
    more benefics than malefics, malefic with more malefics, tie broken by
    the nearest-in-longitude co-tenant). Nodes excluded."""
    sun = chart["planets"]["Sun"]["longitude"]
    moon = chart["planets"]["Moon"]["longitude"]
    waxing = (moon - sun) % 360.0 < 180.0
    benefics = {"Jupiter", "Venus"}
    malefics = {"Sun", "Mars", "Saturn"}
    (benefics if waxing else malefics).add("Moon")

    merc_sign = chart["planets"]["Mercury"]["sign"]
    mates = [p for p in PLANETS7
             if p != "Mercury" and chart["planets"][p]["sign"] == merc_sign]
    b_count = sum(1 for p in mates if p in benefics)
    m_count = len(mates) - b_count
    if not mates or b_count > m_count:
        benefics.add("Mercury")
    elif m_count > b_count:
        malefics.add("Mercury")
    else:  # tie: nearest co-tenant by longitude decides
        merc_lon = chart["planets"]["Mercury"]["longitude"]
        nearest = min(mates, key=lambda p: abs(
            chart["planets"][p]["longitude"] - merc_lon))
        (benefics if nearest in benefics else malefics).add("Mercury")
    return benefics


def drik_bala(chart: dict) -> dict:
    """Net aspectual strength: (sum of benefic sputa drishti on the planet -
    sum of malefic) / 4. Only the 7 classical planets aspect; self-aspect is
    zero by construction (angle 0)."""
    benefics = drik_benefics(chart)
    lons = {p: chart["planets"][p]["longitude"] for p in PLANETS7}
    out = {}
    for target in PLANETS7:
        pos = neg = 0.0
        for asp in PLANETS7:
            if asp == target:
                continue
            angle = (lons[target] - lons[asp]) % 360.0
            v = sputa_drishti(angle, asp)
            if asp in benefics:
                pos += v
            else:
                neg += v
        out[target] = (pos - neg) / 4.0
    return out


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def compute_shadbala(birth: BirthData, config: EngineConfig | None = None,
                     chart: dict | None = None) -> dict:
    config = config or EngineConfig()
    chart = chart or build_chart(birth, config)
    jd = chart.get("jd") or julian_day_from_utc(birth.utc_datetime())
    lagna_sign = chart["lagna"]["sign"]

    # Shared astronomical context.
    sunrise_jd = most_recent_sunrise(jd, birth.lat, birth.lon, config)
    sunset_jd = next_sunrise_jd = None
    if sunrise_jd is not None:
        sunset_jd = _sun_rise_or_set(sunrise_jd + 1e-3, swe.CALC_SET,
                                     birth.lat, birth.lon, config)
        next_sunrise_jd = _sun_rise_or_set(jd, swe.CALC_RISE,
                                           birth.lat, birth.lon, config)
    utc = birth.utc_datetime()
    lmt_hours = (utc.hour + utc.minute / 60.0 + utc.second / 3600.0
                 + birth.lon / 15.0) % 24.0

    temp_friends = temporal_relations(chart)
    decls = declinations(jd, config)
    ayana = ayana_bala(decls)
    natho = nathonnata_bala(lmt_hours)
    paksha = paksha_bala(chart["planets"]["Sun"]["longitude"],
                         chart["planets"]["Moon"]["longitude"])
    tribhaga = tribhaga_bala(jd, sunrise_jd, sunset_jd, next_sunrise_jd)
    abda_lord, masa_lord = abda_masa_lords(jd)
    vara_lord, hora_lord = vara_hora_lords(jd, sunrise_jd, birth.tz_offset,
                                           birth.local_datetime())
    drik = drik_bala(chart)

    planets_out = {}
    for p in PLANETS7:
        pos = chart["planets"][p]
        lon = pos["longitude"]

        uccha = uccha_bala(p, lon)
        sapta = saptavargaja_bala(p, lon, temp_friends)
        oja = ojayugma_bala(p, lon)
        kendradi = kendradi_bala(pos["house"])
        drekkana = drekkana_bala(p, pos["degree_in_sign"])
        sthana = uccha + sapta["total"] + oja + kendradi + drekkana

        dig = dig_bala(p, lon, lagna_sign)

        kala_parts = {
            "nathonnata": natho[p],
            "paksha": paksha[p],
            "tribhaga": tribhaga[p],
            "abda": 15.0 if p == abda_lord else 0.0,
            "masa": 30.0 if p == masa_lord else 0.0,
            "vara": 45.0 if p == vara_lord else 0.0,
            "hora": 60.0 if p == hora_lord else 0.0,
            "ayana": ayana[p],
            # Yuddha (planetary war) bala not implemented — documented gap.
        }
        kala = sum(kala_parts.values())

        # Cheshta: Sun's = its ayana bala (as reported, i.e. doubled);
        # Moon's = its paksha bala (as reported, i.e. doubled). Raman
        # convention ("the ayana/paksha bala serves as motional strength").
        if p == "Sun":
            cheshta = ayana[p]
        elif p == "Moon":
            cheshta = paksha[p]
        else:
            cheshta = cheshta_bala_approx(p, pos["speed"])

        naisargika = NAISARGIKA[p]
        total = sthana + dig + kala + cheshta + naisargika + drik[p]
        rupas = total / 60.0
        required = REQUIRED_RUPAS[p]
        planets_out[p] = {
            "sthana": round(sthana, 2),
            "dig": round(dig, 2),
            "kala": round(kala, 2),
            "cheshta": round(cheshta, 2),
            "naisargika": round(naisargika, 4),
            "drik": round(drik[p], 2),
            "total_virupas": round(total, 2),
            "total_rupas": round(rupas, 3),
            "required_rupas": required,
            "ratio": round(rupas / required, 3),
            "sufficient": rupas >= required,
            "components": {
                "sthana": {
                    "uccha": round(uccha, 2),
                    "saptavargaja": round(sapta["total"], 3),
                    "saptavargaja_detail": sapta["vargas"],
                    "ojayugma": oja,
                    "kendradi": kendradi,
                    "drekkana": drekkana,
                },
                "kala": {k: round(v, 2) for k, v in kala_parts.items()},
                "declination": round(decls[p], 4),
            },
        }

    return {
        "planets": planets_out,
        "context": {
            "abda_lord": abda_lord,
            "masa_lord": masa_lord,
            "vara_lord": vara_lord,
            "hora_lord": hora_lord,
            "benefics_for_drik": sorted(drik_benefics(chart)),
            "yuddha_bala": "not_implemented",
            "ayanamsa": config.ayanamsa,
        },
    }
