"""Static jyotisha data: signs, planets, nakshatras, dignities, friendships, aspects.

Sign indices are 0-based: 0=Aries ... 11=Pisces.
House counts are 1-based and inclusive ("7th from X" == offset 6).
"""

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Modality: 0=movable (chara), 1=fixed (sthira), 2=dual (dvisvabhava)
def sign_modality(sign: int) -> int:
    return sign % 3

# Element: 0=fire, 1=earth, 2=air, 3=water
def sign_element(sign: int) -> int:
    return sign % 4

ODD_SIGNS = {0, 2, 4, 6, 8, 10}      # Aries, Gemini, Leo, Libra, Sagittarius, Aquarius
EVEN_SIGNS = {1, 3, 5, 7, 9, 11}

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
CLASSICAL_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
NODES = ["Rahu", "Ketu"]

SIGN_LORDS = [
    "Mars",     # Aries
    "Venus",    # Taurus
    "Mercury",  # Gemini
    "Moon",     # Cancer
    "Sun",      # Leo
    "Mercury",  # Virgo
    "Venus",    # Libra
    "Mars",     # Scorpio
    "Jupiter",  # Sagittarius
    "Saturn",   # Capricorn
    "Saturn",   # Aquarius
    "Jupiter",  # Pisces
]

# Signs owned by each planet
OWN_SIGNS = {
    "Sun": {4},
    "Moon": {3},
    "Mars": {0, 7},
    "Mercury": {2, 5},
    "Jupiter": {8, 11},
    "Venus": {1, 6},
    "Saturn": {9, 10},
    # Nodes: common convention (co-lordship); noted as a convention decision.
    "Rahu": {10},
    "Ketu": {7},
}

# Exaltation: planet -> (sign, deep exaltation degree within sign)
EXALTATION = {
    "Sun": (0, 10.0),       # Aries 10
    "Moon": (1, 3.0),       # Taurus 3
    "Mars": (9, 28.0),      # Capricorn 28
    "Mercury": (5, 15.0),   # Virgo 15
    "Jupiter": (3, 5.0),    # Cancer 5
    "Venus": (11, 27.0),    # Pisces 27
    "Saturn": (6, 20.0),    # Libra 20
    "Rahu": (1, 20.0),      # Taurus (common convention)
    "Ketu": (7, 20.0),      # Scorpio (common convention)
}

# Debilitation is the 7th sign from exaltation, same degree.
DEBILITATION = {p: ((s + 6) % 12, d) for p, (s, d) in EXALTATION.items()}

# Moolatrikona: planet -> (sign, start_deg, end_deg)
MOOLATRIKONA = {
    "Sun": (4, 0.0, 20.0),        # Leo 0-20
    "Moon": (1, 3.0, 30.0),       # Taurus 3-30
    "Mars": (0, 0.0, 12.0),       # Aries 0-12
    "Mercury": (5, 15.0, 20.0),   # Virgo 15-20
    "Jupiter": (8, 0.0, 10.0),    # Sagittarius 0-10
    "Venus": (6, 0.0, 15.0),      # Libra 0-15
    "Saturn": (10, 0.0, 20.0),    # Aquarius 0-20
}

# Natural friendships (classical Parashari). planet -> {"friends": set, "enemies": set}
# Anything not listed and not the planet itself is neutral.
NATURAL_FRIENDS = {
    "Sun": {"friends": {"Moon", "Mars", "Jupiter"}, "enemies": {"Venus", "Saturn"}},
    "Moon": {"friends": {"Sun", "Mercury"}, "enemies": set()},
    "Mars": {"friends": {"Sun", "Moon", "Jupiter"}, "enemies": {"Mercury"}},
    "Mercury": {"friends": {"Sun", "Venus"}, "enemies": {"Moon"}},
    "Jupiter": {"friends": {"Sun", "Moon", "Mars"}, "enemies": {"Mercury", "Venus"}},
    "Venus": {"friends": {"Mercury", "Saturn"}, "enemies": {"Sun", "Moon"}},
    "Saturn": {"friends": {"Mercury", "Venus"}, "enemies": {"Sun", "Moon", "Mars"}},
    # Nodes: treated like Saturn (Rahu) / Mars (Ketu) — a common convention.
    "Rahu": {"friends": {"Mercury", "Venus", "Saturn"}, "enemies": {"Sun", "Moon", "Mars"}},
    "Ketu": {"friends": {"Sun", "Moon", "Mars"}, "enemies": {"Mercury", "Venus"}},
}

def natural_relation(planet: str, other: str) -> str:
    rel = NATURAL_FRIENDS.get(planet)
    if rel is None or other == planet:
        return "neutral"
    if other in rel["friends"]:
        return "friend"
    if other in rel["enemies"]:
        return "enemy"
    return "neutral"

# ---------------------------------------------------------------------------
# Nakshatras
# ---------------------------------------------------------------------------
NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

NAKSHATRA_SPAN = 360.0 / 27.0          # 13°20'
PADA_SPAN = NAKSHATRA_SPAN / 4.0       # 3°20'

# Vimshottari dasha lords, in sequence, with years. Total 120.
VIMSHOTTARI_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIMSHOTTARI_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}
VIMSHOTTARI_TOTAL_YEARS = 120
assert sum(VIMSHOTTARI_YEARS.values()) == VIMSHOTTARI_TOTAL_YEARS

def nakshatra_lord(nak_index: int) -> str:
    return VIMSHOTTARI_ORDER[nak_index % 9]

NAKSHATRA_LORDS = [nakshatra_lord(i) for i in range(27)]

# ---------------------------------------------------------------------------
# Graha drishti (full aspects). Offsets are houses counted from the planet,
# inclusive: an aspect on the "7th" house is offset 7.
# ---------------------------------------------------------------------------
GRAHA_DRISHTI = {
    "Sun": (7,),
    "Moon": (7,),
    "Mars": (4, 7, 8),
    "Mercury": (7,),
    "Jupiter": (5, 7, 9),
    "Venus": (7,),
    "Saturn": (3, 7, 10),
    # Nodes given only the 7th by default (special 5/9 node aspects are a
    # school-dependent option, not enabled).
    "Rahu": (7,),
    "Ketu": (7,),
}

def aspects_sign(planet: str, from_sign: int, to_sign: int) -> bool:
    """True if `planet` placed in `from_sign` casts graha drishti on `to_sign`."""
    offset = (to_sign - from_sign) % 12 + 1
    return offset in GRAHA_DRISHTI.get(planet, (7,))

# ---------------------------------------------------------------------------
# Natural benefic / malefic classification (static; Moon/Mercury conditional
# rules are applied where a specific yoga demands them).
# ---------------------------------------------------------------------------
NATURAL_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
NATURAL_MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}
DUSTHANA_HOUSES = {6, 8, 12}
UPACHAYA_HOUSES = {3, 6, 10, 11}

# Combustion orbs in degrees; tuples are (direct, retrograde).
COMBUSTION_ORBS = {
    "Moon": (12.0, 12.0),
    "Mars": (17.0, 17.0),
    "Mercury": (14.0, 12.0),
    "Jupiter": (11.0, 11.0),
    "Venus": (10.0, 8.0),
    "Saturn": (15.0, 15.0),
}

# Gochara (transit-from-Moon) favourable houses, classical.
GOCHARA_FAVOURABLE = {
    "Sun": {3, 6, 10, 11},
    "Moon": {1, 3, 6, 7, 10, 11},
    "Mars": {3, 6, 11},
    "Mercury": {2, 4, 6, 8, 10, 11},
    "Jupiter": {2, 5, 7, 9, 11},
    "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12},
    "Saturn": {3, 6, 11},
    "Rahu": {3, 6, 10, 11},
    "Ketu": {3, 6, 11},
}

# Natural karakas used by rectification / predictions.
KARAKAS = {
    "father": "Sun",
    "mother": "Moon",
    "spouse": "Venus",
    "children": "Jupiter",
    "career": "Saturn",
    "intellect": "Mercury",
}
