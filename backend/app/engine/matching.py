"""Ashtakoota (Guna Milan, 36 points) marriage matching + Mangal dosha.

Conventions (documented decisions; where published sources differ we follow
the Maitreya8/Maitreya9 open-source tables and note it):

1. Varna (1): moon-sign class Brahmin{Cancer,Scorpio,Pisces} > Kshatriya
   {Aries,Leo,Sagittarius} > Vaishya{Taurus,Virgo,Capricorn} > Shudra
   {Gemini,Libra,Aquarius}. 1 point when the groom's rank >= bride's rank.
2. Vashya (2): moon sign (with the split signs Sagittarius 0-15/15-30 and
   Capricorn 0-15/15-30) grouped as Chatushpada/Manava/Jalachara/Vanachara/
   Keeta. Same group 2; Manava-Jalachara, Manava-Keeta, Jalachara-Keeta 1;
   Chatushpada-Vanachara 0.5; anything else 0 (per the spec used here; some
   published tables also give Chatushpada-Manava 1 — not adopted).
3. Tara (3): counted both ways from each nakshatra; tara = count mod 9
   (0 -> 9); benefic taras {2,4,6,8,9}. Both benefic 3, one 1.5, none 0.
4. Yoni (4): the standard 14-animal symmetric matrix (Maitreya convention).
   Same animal different gender 4, same animal same gender 3, sworn enemies 0.
5. Graha Maitri (5): natural (Parashari) friendship between the two moon-sign
   lords evaluated in both directions.
6. Gana (6): symmetric scoring — same gana 6, Deva-Manushya 5,
   Manushya-Rakshasa 1, Deva-Rakshasa 0. (Some traditions score
   groom-Rakshasa/bride-Deva differently from the reverse; we use the
   symmetric convention.)
7. Bhakoot (7): moon-sign mutual distance. {1-1, 3-11, 4-10, 7-7} -> 7;
   {2-12, 5-9, 6-8} -> 0.
8. Nadi (8): Adi/Madhya/Antya by nakshatra; different nadi 8, same nadi 0.

Mangal dosha: Mars in houses {1,2,4,7,8,12} counted from the lagna (the
primary convention; the from-Moon placement is also reported). Cancellations
considered: Mars in own sign (Aries/Scorpio) or exalted (Capricorn); Jupiter
conjunct Mars or casting graha drishti on Mars's sign; and mutual dosha
(both partners manglik).
"""
from __future__ import annotations

from typing import Optional

from . import constants as K
from .chart import build_chart
from .ephemeris import BirthData, EngineConfig

# ---------------------------------------------------------------------------
# 1. Varna
# ---------------------------------------------------------------------------
_VARNA_OF_SIGN = {
    3: "Brahmin", 7: "Brahmin", 11: "Brahmin",       # Cancer, Scorpio, Pisces
    0: "Kshatriya", 4: "Kshatriya", 8: "Kshatriya",  # Aries, Leo, Sagittarius
    1: "Vaishya", 5: "Vaishya", 9: "Vaishya",        # Taurus, Virgo, Capricorn
    2: "Shudra", 6: "Shudra", 10: "Shudra",          # Gemini, Libra, Aquarius
}
_VARNA_RANK = {"Brahmin": 4, "Kshatriya": 3, "Vaishya": 2, "Shudra": 1}

# ---------------------------------------------------------------------------
# 2. Vashya
# ---------------------------------------------------------------------------
def _vashya_group(sign: int, degree: float) -> str:
    if sign in (0, 1):                      # Aries, Taurus
        return "Chatushpada"
    if sign == 8:                           # Sagittarius: 0-15 Manava, 15-30 Chatushpada
        return "Manava" if degree < 15.0 else "Chatushpada"
    if sign == 9:                           # Capricorn: 0-15 Chatushpada, 15-30 Jalachara
        return "Chatushpada" if degree < 15.0 else "Jalachara"
    if sign in (2, 5, 6, 10):               # Gemini, Virgo, Libra, Aquarius
        return "Manava"
    if sign in (3, 11):                     # Cancer, Pisces
        return "Jalachara"
    if sign == 4:                           # Leo
        return "Vanachara"
    return "Keeta"                          # Scorpio

_VASHYA_ONE_POINT = {
    frozenset({"Manava", "Jalachara"}),
    frozenset({"Manava", "Keeta"}),
    frozenset({"Jalachara", "Keeta"}),
}

def _vashya_points(a: str, b: str) -> float:
    if a == b:
        return 2.0
    pair = frozenset({a, b})
    if pair in _VASHYA_ONE_POINT:
        return 1.0
    if pair == frozenset({"Chatushpada", "Vanachara"}):
        return 0.5
    return 0.0

# ---------------------------------------------------------------------------
# 3. Tara
# ---------------------------------------------------------------------------
_BENEFIC_TARAS = {2, 4, 6, 8, 9}

def _tara_of(from_nak: int, to_nak: int) -> int:
    count = ((to_nak - from_nak) % 27) + 1
    tara = count % 9
    return 9 if tara == 0 else tara

# ---------------------------------------------------------------------------
# 4. Yoni — nakshatra -> (animal, gender), plus the 14x14 symmetric matrix.
# Matrix source: the widely published classical table as implemented in
# Maitreya (values 0-4; diagonal is the same-animal case, refined below to
# 4 for opposite genders / 3 for the same gender).
# ---------------------------------------------------------------------------
YONI_OF_NAKSHATRA = {
    "Ashwini": ("Horse", "M"), "Bharani": ("Elephant", "M"),
    "Krittika": ("Sheep", "F"), "Rohini": ("Serpent", "M"),
    "Mrigashira": ("Serpent", "F"), "Ardra": ("Dog", "F"),
    "Punarvasu": ("Cat", "F"), "Pushya": ("Sheep", "M"),
    "Ashlesha": ("Cat", "M"), "Magha": ("Rat", "M"),
    "Purva Phalguni": ("Rat", "F"), "Uttara Phalguni": ("Cow", "M"),
    "Hasta": ("Buffalo", "F"), "Chitra": ("Tiger", "F"),
    "Swati": ("Buffalo", "M"), "Vishakha": ("Tiger", "M"),
    "Anuradha": ("Deer", "F"), "Jyeshtha": ("Deer", "M"),
    "Mula": ("Dog", "M"), "Purva Ashadha": ("Monkey", "M"),
    "Uttara Ashadha": ("Mongoose", "M"), "Shravana": ("Monkey", "F"),
    "Dhanishta": ("Lion", "F"), "Shatabhisha": ("Horse", "F"),
    "Purva Bhadrapada": ("Lion", "M"), "Uttara Bhadrapada": ("Cow", "F"),
    "Revati": ("Elephant", "F"),
}

_YONI_ANIMALS = ["Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat",
                 "Cow", "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion"]

# Sworn-enemy (0) pairs: Cow-Tiger, Elephant-Lion, Horse-Buffalo, Dog-Deer,
# Serpent-Mongoose, Cat-Rat, Monkey-Sheep.
_YONI_MATRIX = [
    #  Hor Ele She Ser Dog Cat Rat Cow Buf Tig Dee Mon Mng Lio
    [4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1],  # Horse
    [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0],  # Elephant
    [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],  # Sheep
    [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],  # Serpent
    [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1],  # Dog
    [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],  # Cat
    [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2],  # Rat
    [1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],  # Cow
    [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],  # Buffalo
    [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1],  # Tiger
    [3, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1],  # Deer
    [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2],  # Monkey
    [2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2],  # Mongoose
    [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 2, 4],  # Lion
]
assert all(_YONI_MATRIX[i][j] == _YONI_MATRIX[j][i]
           for i in range(14) for j in range(14)), "yoni matrix must be symmetric"

def _yoni_points(nak_a: str, nak_b: str) -> tuple[float, str]:
    animal_a, gender_a = YONI_OF_NAKSHATRA[nak_a]
    animal_b, gender_b = YONI_OF_NAKSHATRA[nak_b]
    if animal_a == animal_b:
        pts = 4.0 if gender_a != gender_b else 3.0
    else:
        i, j = _YONI_ANIMALS.index(animal_a), _YONI_ANIMALS.index(animal_b)
        pts = float(_YONI_MATRIX[i][j])
    detail = f"{animal_a} ({gender_a}) x {animal_b} ({gender_b})"
    return pts, detail

# ---------------------------------------------------------------------------
# 5. Graha Maitri
# ---------------------------------------------------------------------------
def _maitri_points(lord_a: str, lord_b: str) -> float:
    if lord_a == lord_b:
        return 5.0
    r_ab = K.natural_relation(lord_a, lord_b)
    r_ba = K.natural_relation(lord_b, lord_a)
    rels = frozenset({r_ab, r_ba}) if r_ab != r_ba else frozenset({r_ab})
    if rels == frozenset({"friend"}):
        return 5.0
    if rels == frozenset({"friend", "neutral"}):
        return 4.0
    if rels == frozenset({"neutral"}):
        return 3.0
    if rels == frozenset({"friend", "enemy"}):
        return 1.0
    if rels == frozenset({"neutral", "enemy"}):
        return 0.5
    return 0.0  # mutual enemies

# ---------------------------------------------------------------------------
# 6. Gana
# ---------------------------------------------------------------------------
_DEVA = {"Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Swati",
         "Anuradha", "Shravana", "Revati"}
_MANUSHYA = {"Bharani", "Rohini", "Ardra", "Purva Phalguni", "Uttara Phalguni",
             "Purva Ashadha", "Uttara Ashadha", "Purva Bhadrapada",
             "Uttara Bhadrapada"}

def _gana_of(nak: str) -> str:
    if nak in _DEVA:
        return "Deva"
    if nak in _MANUSHYA:
        return "Manushya"
    return "Rakshasa"

def _gana_points(a: str, b: str) -> float:
    if a == b:
        return 6.0
    pair = frozenset({a, b})
    if pair == frozenset({"Deva", "Manushya"}):
        return 5.0
    if pair == frozenset({"Manushya", "Rakshasa"}):
        return 1.0
    return 0.0  # Deva-Rakshasa

# ---------------------------------------------------------------------------
# 8. Nadi
# ---------------------------------------------------------------------------
_ADI = {"Ashwini", "Ardra", "Punarvasu", "Uttara Phalguni", "Hasta",
        "Jyeshtha", "Mula", "Shatabhisha", "Purva Bhadrapada"}
_MADHYA = {"Bharani", "Mrigashira", "Pushya", "Purva Phalguni", "Chitra",
           "Anuradha", "Purva Ashadha", "Dhanishta", "Uttara Bhadrapada"}

def _nadi_of(nak: str) -> str:
    if nak in _ADI:
        return "Adi"
    if nak in _MADHYA:
        return "Madhya"
    return "Antya"

# ---------------------------------------------------------------------------
# Mangal dosha
# ---------------------------------------------------------------------------
_MANGAL_HOUSES = {1, 2, 4, 7, 8, 12}

def _house_from(sign_from: int, sign_of: int) -> int:
    return (sign_of - sign_from) % 12 + 1

def mangal_dosha(chart: dict) -> dict:
    mars = chart["planets"]["Mars"]
    jup = chart["planets"]["Jupiter"]
    moon_sign = chart["planets"]["Moon"]["sign"]
    lagna_sign = chart["lagna"]["sign"]
    house_lagna = _house_from(lagna_sign, mars["sign"])
    house_moon = _house_from(moon_sign, mars["sign"])
    from_lagna = house_lagna in _MANGAL_HOUSES
    from_moon = house_moon in _MANGAL_HOUSES

    cancellations = []
    if mars["sign"] in K.OWN_SIGNS["Mars"]:
        cancellations.append("Mars in own sign")
    if mars["sign"] == K.EXALTATION["Mars"][0]:
        cancellations.append("Mars exalted")
    if jup["sign"] == mars["sign"]:
        cancellations.append("Jupiter conjunct Mars")
    elif K.aspects_sign("Jupiter", jup["sign"], mars["sign"]):
        cancellations.append("Jupiter aspects Mars")

    manglik = from_lagna  # primary convention: judged from lagna
    return {
        "manglik": manglik,
        "mars_house_from_lagna": house_lagna,
        "mars_house_from_moon": house_moon,
        "manglik_from_lagna": from_lagna,
        "manglik_from_moon": from_moon,
        "cancellations": cancellations,
        "effective": manglik and not cancellations,
    }

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def _moon_facts(chart: dict) -> dict:
    moon = chart["planets"]["Moon"]
    return {
        "sign": moon["sign"],
        "sign_name": moon["sign_name"],
        "degree_in_sign": moon["degree_in_sign"],
        "nakshatra": moon["nakshatra"],
        "nakshatra_index": moon["nakshatra_index"],
        "pada": moon["pada"],
        "sign_lord": K.SIGN_LORDS[moon["sign"]],
    }


def verdict_for(total: float) -> str:
    if total >= 32:
        return "excellent"
    if total >= 25:
        return "very good"
    if total >= 18:
        return "acceptable"
    return "not recommended"


def compute_kutas(g: dict, b: dict) -> list[dict]:
    """The 8 kutas from groom/bride moon-facts dicts (see _moon_facts)."""
    kutas = []

    # 1. Varna
    varna_g = _VARNA_OF_SIGN[g["sign"]]
    varna_b = _VARNA_OF_SIGN[b["sign"]]
    varna_pts = 1.0 if _VARNA_RANK[varna_g] >= _VARNA_RANK[varna_b] else 0.0
    kutas.append({"name": "Varna", "points": varna_pts, "max": 1,
                  "details": f"groom {varna_g}, bride {varna_b}"})

    # 2. Vashya
    vg = _vashya_group(g["sign"], g["degree_in_sign"])
    vb = _vashya_group(b["sign"], b["degree_in_sign"])
    kutas.append({"name": "Vashya", "points": _vashya_points(vg, vb), "max": 2,
                  "details": f"groom {vg}, bride {vb}"})

    # 3. Tara
    tara_gb = _tara_of(g["nakshatra_index"], b["nakshatra_index"])
    tara_bg = _tara_of(b["nakshatra_index"], g["nakshatra_index"])
    n_benefic = sum(1 for t in (tara_gb, tara_bg) if t in _BENEFIC_TARAS)
    tara_pts = {2: 3.0, 1: 1.5, 0: 0.0}[n_benefic]
    kutas.append({"name": "Tara", "points": tara_pts, "max": 3,
                  "details": f"tara groom->bride {tara_gb}, bride->groom {tara_bg}"})

    # 4. Yoni
    yoni_pts, yoni_detail = _yoni_points(g["nakshatra"], b["nakshatra"])
    kutas.append({"name": "Yoni", "points": yoni_pts, "max": 4,
                  "details": yoni_detail})

    # 5. Graha Maitri
    maitri_pts = _maitri_points(g["sign_lord"], b["sign_lord"])
    kutas.append({"name": "Graha Maitri", "points": maitri_pts, "max": 5,
                  "details": f"lords {g['sign_lord']} & {b['sign_lord']}"})

    # 6. Gana
    gana_g, gana_b = _gana_of(g["nakshatra"]), _gana_of(b["nakshatra"])
    kutas.append({"name": "Gana", "points": _gana_points(gana_g, gana_b),
                  "max": 6, "details": f"groom {gana_g}, bride {gana_b}"})

    # 7. Bhakoot
    dist = _house_from(g["sign"], b["sign"])
    bhakoot_pts = 7.0 if dist in (1, 3, 4, 7, 10, 11) else 0.0
    kutas.append({"name": "Bhakoot", "points": bhakoot_pts, "max": 7,
                  "details": f"moon signs {g['sign_name']} & {b['sign_name']} "
                             f"({dist}/{_house_from(b['sign'], g['sign'])})"})

    # 8. Nadi
    nadi_g, nadi_b = _nadi_of(g["nakshatra"]), _nadi_of(b["nakshatra"])
    nadi_pts = 8.0 if nadi_g != nadi_b else 0.0
    kutas.append({"name": "Nadi", "points": nadi_pts, "max": 8,
                  "details": f"groom {nadi_g}, bride {nadi_b}"})
    return kutas


def match(groom_birth: BirthData, bride_birth: BirthData,
          config: Optional[EngineConfig] = None) -> dict:
    config = config or EngineConfig()
    groom_chart = build_chart(groom_birth, config)
    bride_chart = build_chart(bride_birth, config)
    g, b = _moon_facts(groom_chart), _moon_facts(bride_chart)

    kutas = compute_kutas(g, b)
    total = round(sum(k["points"] for k in kutas), 2)

    md_groom = mangal_dosha(groom_chart)
    md_bride = mangal_dosha(bride_chart)
    both = md_groom["effective"] and md_bride["effective"]
    if both:
        note = "Both partners are manglik — the dosha is mutually cancelled."
    elif md_groom["effective"] or md_bride["effective"]:
        who = "groom" if md_groom["effective"] else "bride"
        note = f"Only the {who} has an uncancelled Mangal dosha — traditionally a concern."
    else:
        note = "No effective Mangal dosha for either partner."
    mangal = {
        "groom": md_groom,
        "bride": md_bride,
        "mutual_cancellation": both,
        "compatible": both or not (md_groom["effective"] or md_bride["effective"]),
        "note": note,
    }

    return {
        "kutas": kutas,
        "total": total,
        "max_total": 36,
        "verdict": verdict_for(total),
        "mangal_dosha": mangal,
        "groom": g,
        "bride": b,
    }
