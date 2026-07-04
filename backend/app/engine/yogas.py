"""Yoga evaluator. Each rule returns
{name, sanskrit_category, present, factors[], strength} — factors are
machine-readable strings substantiating the finding.
"""
from __future__ import annotations

from . import constants as K

_DIGNITY_STRENGTH = {
    "exalted": 1.0, "moolatrikona": 0.9, "own": 0.8, "friend": 0.6,
    "neutral": 0.5, "enemy": 0.3, "debilitated": 0.15,
}


def _yoga(name, category, present, factors=None, strength=0.0):
    return {
        "name": name,
        "sanskrit_category": category,
        "present": bool(present),
        "factors": factors or [],
        "strength": round(strength if present else 0.0, 3),
    }


def _house_from(sign: int, ref_sign: int) -> int:
    return (sign - ref_sign) % 12 + 1


def _mutual_aspect(chart, p1, p2) -> bool:
    s1 = chart["planets"][p1]["sign"]
    s2 = chart["planets"][p2]["sign"]
    return K.aspects_sign(p1, s1, s2) and K.aspects_sign(p2, s2, s1)


def _parivartana(chart, p1, p2) -> bool:
    s1 = chart["planets"][p1]["sign"]
    s2 = chart["planets"][p2]["sign"]
    return s1 in K.OWN_SIGNS.get(p2, set()) and s2 in K.OWN_SIGNS.get(p1, set())


def _lords_of(chart, houses) -> set:
    return {chart["house_lords"][h]["lord"] for h in houses}


# ---------------------------------------------------------------------------
# Pancha Mahapurusha
# ---------------------------------------------------------------------------
_MAHAPURUSHA = {
    "Mars": "Ruchaka", "Mercury": "Bhadra", "Jupiter": "Hamsa",
    "Venus": "Malavya", "Saturn": "Shasha",
}


def pancha_mahapurusha(chart) -> list[dict]:
    out = []
    for planet, yname in _MAHAPURUSHA.items():
        p = chart["planets"][planet]
        qualified = p["dignity"] in ("exalted", "own", "moolatrikona")
        in_kendra = p["house"] in K.KENDRA_HOUSES
        present = qualified and in_kendra
        factors = []
        if present:
            factors = [
                f"{planet} is {p['dignity']} in {p['sign_name']}",
                f"{planet} occupies kendra house {p['house']} from lagna",
            ]
        out.append(_yoga(f"{yname} Yoga", "Pancha Mahapurusha", present, factors,
                         _DIGNITY_STRENGTH.get(p["dignity"], 0.5)))
    return out


def gaja_kesari(chart) -> dict:
    jup = chart["planets"]["Jupiter"]
    moon_sign = chart["planets"]["Moon"]["sign"]
    h = _house_from(jup["sign"], moon_sign)
    present = h in K.KENDRA_HOUSES
    factors = [f"Jupiter in house {h} from Moon"] if present else []
    if present:
        factors.append(f"Jupiter dignity: {jup['dignity']}")
    return _yoga("Gaja Kesari Yoga", "Chandra yoga", present, factors,
                 _DIGNITY_STRENGTH.get(jup["dignity"], 0.5))


def budhaditya(chart) -> dict:
    sun = chart["planets"]["Sun"]
    mer = chart["planets"]["Mercury"]
    present = sun["sign"] == mer["sign"]
    factors = []
    if present:
        factors.append(f"Sun and Mercury conjunct in {sun['sign_name']} (house {sun['house']})")
        if mer["combust"]:
            factors.append("Mercury is combust (reduces strength)")
    strength = 0.7 if not mer["combust"] else 0.4
    return _yoga("Budhaditya Yoga", "Surya yoga", present, factors, strength)


def chandra_mangala(chart) -> dict:
    moon = chart["planets"]["Moon"]
    mars = chart["planets"]["Mars"]
    present = moon["sign"] == mars["sign"]
    factors = [f"Moon and Mars conjunct in {moon['sign_name']} (house {moon['house']})"] if present else []
    return _yoga("Chandra-Mangala Yoga", "Chandra yoga", present, factors, 0.6)


def viparita_raja(chart) -> list[dict]:
    names = {6: "Harsha", 8: "Sarala", 12: "Vimala"}
    out = []
    for h, yname in names.items():
        hl = chart["house_lords"][h]
        present = hl["placed_house"] in K.DUSTHANA_HOUSES
        factors = []
        if present:
            factors.append(
                f"{h}th lord {hl['lord']} placed in dusthana house {hl['placed_house']}")
        out.append(_yoga(f"{yname} (Viparita Raja) Yoga", "Viparita Raja",
                         present, factors, 0.6))
    return out


def kemadruma(chart) -> dict:
    moon_sign = chart["planets"]["Moon"]["sign"]
    others = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]  # excl Sun, Moon, nodes
    support = []
    for p in others:
        h = _house_from(chart["planets"][p]["sign"], moon_sign)
        if h in (1, 2, 12):
            support.append(f"{p} in house {h} from Moon")
    present = not support
    factors = ["No classical planet (other than Sun) in 2nd/12th from Moon or with Moon"] if present else support
    cancellations = []
    if present:
        for p in others + ["Sun"]:
            h = _house_from(chart["planets"][p]["sign"], moon_sign)
            if h in K.KENDRA_HOUSES and p != "Sun":
                cancellations.append(f"{p} in kendra from Moon")
        if chart["planets"]["Moon"]["house"] in K.KENDRA_HOUSES:
            cancellations.append("Moon in kendra from lagna")
    if cancellations:
        present = False
        factors = factors + [f"CANCELLED: {c}" for c in cancellations]
        return _yoga("Kemadruma Yoga", "Chandra dosha (cancelled)", False, factors, 0.0)
    return _yoga("Kemadruma Yoga", "Chandra dosha", present, factors, 0.7)


def shakata(chart) -> dict:
    moon = chart["planets"]["Moon"]
    jup_sign = chart["planets"]["Jupiter"]["sign"]
    h = _house_from(moon["sign"], jup_sign)
    present = h in (6, 8, 12)
    factors = [f"Moon in house {h} from Jupiter"] if present else []
    if present and moon["house"] in K.KENDRA_HOUSES:
        factors.append("CANCELLED: Moon in kendra from lagna")
        return _yoga("Shakata Yoga", "Chandra dosha (cancelled)", False, factors, 0.0)
    return _yoga("Shakata Yoga", "Chandra dosha", present, factors, 0.5)


def adhi(chart) -> dict:
    moon_sign = chart["planets"]["Moon"]["sign"]
    factors = []
    count = 0
    for p in ("Jupiter", "Venus", "Mercury"):
        h = _house_from(chart["planets"][p]["sign"], moon_sign)
        if h in (6, 7, 8):
            count += 1
            factors.append(f"{p} in house {h} from Moon")
    present = count >= 2  # convention: at least two of the three benefics
    return _yoga("Adhi Yoga", "Chandra yoga", present, factors, count / 3.0)


def _sun_moon_flank(chart, ref_planet: str, exclude: set):
    ref_sign = chart["planets"][ref_planet]["sign"]
    second, twelfth = [], []
    for p in K.CLASSICAL_PLANETS:
        if p in exclude:
            continue
        h = _house_from(chart["planets"][p]["sign"], ref_sign)
        if h == 2:
            second.append(p)
        elif h == 12:
            twelfth.append(p)
    return second, twelfth


def solar_yogas(chart) -> list[dict]:
    second, twelfth = _sun_moon_flank(chart, "Sun", exclude={"Sun", "Moon"})
    vesi = _yoga("Vesi Yoga", "Surya yoga", bool(second) and not twelfth,
                 [f"{p} in 2nd from Sun" for p in second], 0.4)
    vosi = _yoga("Vosi Yoga", "Surya yoga", bool(twelfth) and not second,
                 [f"{p} in 12th from Sun" for p in twelfth], 0.4)
    ubhaya = _yoga("Ubhayachari Yoga", "Surya yoga", bool(second) and bool(twelfth),
                   [f"{p} in 2nd from Sun" for p in second] +
                   [f"{p} in 12th from Sun" for p in twelfth], 0.6)
    return [vesi, vosi, ubhaya]


def lunar_yogas(chart) -> list[dict]:
    second, twelfth = _sun_moon_flank(chart, "Moon", exclude={"Sun", "Moon"})
    sunapha = _yoga("Sunapha Yoga", "Chandra yoga", bool(second) and not twelfth,
                    [f"{p} in 2nd from Moon" for p in second], 0.5)
    anapha = _yoga("Anapha Yoga", "Chandra yoga", bool(twelfth) and not second,
                   [f"{p} in 12th from Moon" for p in twelfth], 0.5)
    durudhara = _yoga("Durudhara Yoga", "Chandra yoga", bool(second) and bool(twelfth),
                      [f"{p} in 2nd from Moon" for p in second] +
                      [f"{p} in 12th from Moon" for p in twelfth], 0.7)
    return [sunapha, anapha, durudhara]


def kala_sarpa(chart) -> dict:
    rahu = chart["planets"]["Rahu"]["longitude"]
    ketu = chart["planets"]["Ketu"]["longitude"]

    def within_arc(lon, start, end):
        return (lon - start) % 360.0 <= (end - start) % 360.0

    inside_rk = all(within_arc(chart["planets"][p]["longitude"], rahu, ketu)
                    for p in K.CLASSICAL_PLANETS)
    inside_kr = all(within_arc(chart["planets"][p]["longitude"], ketu, rahu)
                    for p in K.CLASSICAL_PLANETS)
    present = inside_rk or inside_kr
    factors = []
    if present:
        direction = "Rahu-to-Ketu (zodiacal)" if inside_rk else "Ketu-to-Rahu (zodiacal)"
        factors.append(f"All 7 classical planets within the {direction} arc")
        factors.append(f"Rahu {chart['planets']['Rahu']['sign_name']}, "
                       f"Ketu {chart['planets']['Ketu']['sign_name']}")
    return _yoga("Kala Sarpa Yoga", "Nabhasa/dosha", present, factors, 0.7)


def neecha_bhanga(chart) -> list[dict]:
    out = []
    moon_sign = chart["planets"]["Moon"]["sign"]
    lagna_sign = chart["lagna"]["sign"]
    for planet, p in chart["planets"].items():
        if p["dignity"] != "debilitated" or planet in K.NODES:
            continue
        deb_sign = p["sign"]
        dispositor = K.SIGN_LORDS[deb_sign]
        exalt_lord = K.SIGN_LORDS[K.EXALTATION[planet][0]]
        cancels = []
        for ref_name, ref_sign in (("lagna", lagna_sign), ("Moon", moon_sign)):
            if _house_from(chart["planets"][dispositor]["sign"], ref_sign) in K.KENDRA_HOUSES:
                cancels.append(f"dispositor {dispositor} in kendra from {ref_name}")
            if _house_from(chart["planets"][exalt_lord]["sign"], ref_sign) in K.KENDRA_HOUSES:
                cancels.append(f"exaltation-sign lord {exalt_lord} in kendra from {ref_name}")
        for other, op in chart["planets"].items():
            if other != planet and op["sign"] == deb_sign and op["dignity"] == "exalted":
                cancels.append(f"conjunct exalted {other}")
        present = bool(cancels)
        factors = [f"{planet} debilitated in {p['sign_name']}"] + sorted(set(cancels))
        out.append(_yoga(f"Neecha Bhanga ({planet})", "Neecha Bhanga Raja",
                         present, factors if present else [], 0.6))
    return out


def raja_yogas(chart) -> list[dict]:
    kendra_lords = _lords_of(chart, K.KENDRA_HOUSES)
    trikona_lords = _lords_of(chart, K.TRIKONA_HOUSES)
    out = []
    seen = set()
    for kl in sorted(kendra_lords):
        for tl in sorted(trikona_lords):
            if kl == tl or (kl, tl) in seen or (tl, kl) in seen:
                continue
            seen.add((kl, tl))
            links = []
            if chart["planets"][kl]["sign"] == chart["planets"][tl]["sign"]:
                links.append("conjunction")
            if _mutual_aspect(chart, kl, tl):
                links.append("mutual aspect")
            if _parivartana(chart, kl, tl):
                links.append("parivartana (exchange)")
            if links:
                factors = [
                    f"{kl} (kendra lord) and {tl} (trikona lord): {', '.join(links)}",
                    f"{kl} in {chart['planets'][kl]['sign_name']}, "
                    f"{tl} in {chart['planets'][tl]['sign_name']}",
                ]
                strength = 0.5 + 0.15 * len(links)
                out.append(_yoga(f"Raja Yoga ({kl}-{tl})", "Raja", True, factors,
                                 min(strength, 1.0)))
    if not out:
        out.append(_yoga("Raja Yoga", "Raja", False, [], 0.0))
    return out


def dhana_yogas(chart) -> list[dict]:
    wealth_lords = _lords_of(chart, {2, 11})
    lakshmi_lords = _lords_of(chart, {5, 9})
    out = []
    seen = set()

    def link(p1, p2):
        links = []
        if chart["planets"][p1]["sign"] == chart["planets"][p2]["sign"]:
            links.append("conjunction")
        if _parivartana(chart, p1, p2):
            links.append("parivartana")
        if _mutual_aspect(chart, p1, p2):
            links.append("mutual aspect")
        return links

    pairs = [(w, l) for w in sorted(wealth_lords) for l in sorted(lakshmi_lords)]
    l2, l11 = chart["house_lords"][2]["lord"], chart["house_lords"][11]["lord"]
    if l2 != l11:
        pairs.append((l2, l11))
    for p1, p2 in pairs:
        if p1 == p2 or (p1, p2) in seen or (p2, p1) in seen:
            continue
        seen.add((p1, p2))
        links = link(p1, p2)
        if links:
            out.append(_yoga(f"Dhana Yoga ({p1}-{p2})", "Dhana", True,
                             [f"{p1} and {p2} linked by {', '.join(links)}"], 0.6))
    if not out:
        out.append(_yoga("Dhana Yoga", "Dhana", False, [], 0.0))
    return out


def lakshmi(chart) -> dict:
    ninth = chart["house_lords"][9]
    lord_ok = (ninth["placed_house"] in (K.KENDRA_HOUSES | K.TRIKONA_HOUSES)
               and ninth["dignity"] in ("own", "exalted", "moolatrikona"))
    venus = chart["planets"]["Venus"]
    venus_ok = (not venus["combust"]
                and venus["dignity"] not in ("debilitated", "enemy")
                and (venus["house"] in (K.KENDRA_HOUSES | K.TRIKONA_HOUSES)
                     or venus["dignity"] in ("own", "exalted", "moolatrikona")))
    present = lord_ok and venus_ok
    factors = []
    if present:
        factors = [
            f"9th lord {ninth['lord']} ({ninth['dignity']}) in house {ninth['placed_house']}",
            f"Venus {venus['dignity']} in house {venus['house']}",
        ]
    return _yoga("Lakshmi Yoga", "Dhana", present, factors, 0.8)


def evaluate_yogas(chart: dict) -> list[dict]:
    results = []
    results.extend(pancha_mahapurusha(chart))
    results.append(gaja_kesari(chart))
    results.append(budhaditya(chart))
    results.append(chandra_mangala(chart))
    results.extend(viparita_raja(chart))
    results.append(kemadruma(chart))
    results.append(shakata(chart))
    results.append(adhi(chart))
    results.extend(solar_yogas(chart))
    results.extend(lunar_yogas(chart))
    results.append(kala_sarpa(chart))
    results.extend(neecha_bhanga(chart))
    results.extend(raja_yogas(chart))
    results.extend(dhana_yogas(chart))
    results.append(lakshmi(chart))
    return results
