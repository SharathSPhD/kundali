"""Deterministic prediction synthesis.

For a given date: active dasha lords -> their natal roles (lordships,
occupancy, dignity, yogas) -> base themes per life area; modulated by current
transits (Sade Sati, double transit, gochara of the dasha lords) and SAV
bindus of transited signs. Every contribution is recorded as a
machine-readable substantiation fact. No prose here.
"""
from __future__ import annotations

import math
from datetime import datetime

from . import constants as K
from .scoring_labels import favorability_label
from .ashtakavarga import compute_ashtakavarga, transit_strength
from .chart import build_chart
from .dashas import active_path, build_vimshottari
from .ephemeris import BirthData, EngineConfig
from .jaimini import compute_jaimini
from .shadbala import compute_shadbala
from .transits import compute_transits
from .vargas import d9 as _navamsa_sign, d10 as _dashamsa_sign
from .yogas import evaluate_yogas

AREAS = ["career", "wealth", "health", "relationships", "family", "education"]

# house -> polarity weight per area. Positive: activation of the house helps
# the area; negative: activation of the house stresses the area.
AREA_HOUSE_POLARITY = {
    "career": {10: 1.0, 11: 0.5, 6: 0.3, 8: -0.4, 12: -0.4},
    "wealth": {2: 1.0, 11: 1.0, 9: 0.4, 12: -0.5, 8: -0.3},
    "health": {1: 1.0, 6: -1.0, 8: -0.8, 12: -0.4},
    "relationships": {7: 1.0, 5: 0.4, 1: 0.3, 6: -0.4, 8: -0.4},
    "family": {4: 1.0, 2: 0.6, 9: 0.3, 8: -0.4},
    "education": {5: 1.0, 9: 0.6, 4: 0.4, 2: 0.3},
}

DASHA_LEVEL_WEIGHTS = {1: 0.5, 2: 0.3, 3: 0.2, 4: 0.1, 5: 0.05}

# Shadbala weighting of dasha-lord contributions (documented convention):
# a lord proven strong by shadbala (ratio >= 1) amplifies |contribution| by
# 10%; a weak lord (ratio < 0.8) dampens by 10%; the 0.8..1.0 band is
# neutral. Nodes (Rahu/Ketu) have no shadbala and stay neutral.
def _shadbala_multiplier(ratio: float | None) -> float:
    if ratio is None:
        return 1.0
    if ratio >= 1.0:
        return 1.1
    if ratio < 0.8:
        return 0.9
    return 1.0


def _varga_dignity(planet: str, varga_sign: int) -> str | None:
    """Sign-level dignity in a divisional chart: exalted / own / debilitated
    (None otherwise). Degree-based states (moolatrikona) have no meaning at
    varga-sign level and are not evaluated."""
    ex = K.EXALTATION.get(planet)
    if ex and ex[0] == varga_sign:
        return "exalted"
    if varga_sign in K.OWN_SIGNS.get(planet, set()):
        return "own"
    de = K.DEBILITATION.get(planet)
    if de and de[0] == varga_sign:
        return "debilitated"
    return None

_DIGNITY_QUALITY = {
    "exalted": 1.0, "moolatrikona": 0.8, "own": 0.7, "friend": 0.4,
    "neutral": 0.1, "enemy": -0.3, "debilitated": -0.7,
}


def _lord_profile(chart: dict, yogas: list[dict], lord: str) -> dict:
    p = chart["planets"][lord]
    lorded = [h for h in range(1, 13) if chart["house_lords"][h]["lord"] == lord]
    quality = _DIGNITY_QUALITY.get(p["dignity"], 0.0)
    notes = []
    if p["dignity"] == "debilitated":
        for y in yogas:
            if y["present"] and y["name"] == f"Neecha Bhanga ({lord})":
                quality = 0.2
                notes.append("neecha_bhanga_cancels_debilitation")
    if p["combust"]:
        quality -= 0.3
        notes.append("combust")
    if p["house"] in K.DUSTHANA_HOUSES:
        quality -= 0.2
        notes.append(f"occupies_dusthana_{p['house']}")
    elif p["house"] in (K.KENDRA_HOUSES | K.TRIKONA_HOUSES):
        quality += 0.15
        notes.append(f"occupies_kendra_trikona_{p['house']}")
    participating_yogas = [
        y["name"] for y in yogas
        if y["present"] and any(lord in f for f in y["factors"] + [y["name"]])
    ]
    if participating_yogas:
        quality += 0.1
    return {
        "lord": lord,
        "houses_lorded": lorded,
        "occupied_house": p["house"],
        "dignity": p["dignity"],
        "retrograde": p["retrograde"],
        "combust": p["combust"],
        "quality": round(max(-1.0, min(1.0, quality)), 3),
        "notes": notes,
        "yogas": participating_yogas,
    }


def _dasha_contributions(profile: dict, weight: float, level_name: str):
    """Yield (area, delta, fact) for every area house this lord activates."""
    activated = set(profile["houses_lorded"]) | {profile["occupied_house"]}
    q = profile["quality"]
    for area in AREAS:
        polarity_map = AREA_HOUSE_POLARITY[area]
        for h in activated:
            pol = polarity_map.get(h)
            if pol is None:
                continue
            if pol > 0:
                delta = weight * pol * q
            else:
                # Dusthana activation stresses the area; a weak/afflicted lord
                # makes it worse, a strong lord softens it.
                delta = weight * pol * max(0.3, 1.0 - max(q, 0.0))
            role = "lords" if h in profile["houses_lorded"] else "occupies"
            yield area, delta, {
                "type": "dasha_lord_natal_role",
                "level": level_name,
                "lord": profile["lord"],
                "role": f"{role} house {h}",
                "dignity": profile["dignity"],
                "quality": q,
                "house": h,
                "polarity": pol,
                "delta": round(delta, 4),
                "yogas": profile["yogas"],
                "notes": profile["notes"],
            }


def predict(birth: BirthData, on_dt: datetime,
            config: EngineConfig | None = None) -> dict:
    config = config or EngineConfig()
    chart = build_chart(birth, config)
    yogas = evaluate_yogas(chart)
    tree = build_vimshottari(chart["planets"]["Moon"]["longitude"],
                             birth.local_datetime(), config, levels=3)
    path = active_path(tree, on_dt)
    on_utc = on_dt  # treated as UT for transit purposes (day-level resolution)
    transits = compute_transits(chart, on_utc, config)
    av = compute_ashtakavarga(chart)
    shadbala = compute_shadbala(birth, config, chart=chart)
    jaimini = compute_jaimini(chart, birth.local_datetime(), config, on=on_dt)

    scores = {a: 0.0 for a in AREAS}
    subst = {a: [] for a in AREAS}
    transit_net = {a: 0.0 for a in AREAS}

    # --- dasha lords -> natal promise -----------------------------------
    # Each lord's contribution is weighted by its shadbala sufficiency (see
    # _shadbala_multiplier) and the lord's shadbala rupas are recorded in
    # the substantiation trail.
    profiles = {}
    for node in path:
        weight = DASHA_LEVEL_WEIGHTS.get(node["level"], 0.05)
        prof = _lord_profile(chart, yogas, node["lord"])
        profiles[node["lord"]] = (prof, weight, node)
        sb_row = shadbala["planets"].get(node["lord"])
        mult = _shadbala_multiplier(sb_row["ratio"] if sb_row else None)
        for area, delta, fact in _dasha_contributions(prof, weight, node["level_name"]):
            delta *= mult
            fact["delta"] = round(delta, 4)
            if sb_row:
                fact["shadbala_rupas"] = sb_row["total_rupas"]
                fact["shadbala_required"] = sb_row["required_rupas"]
                fact["shadbala_ratio"] = sb_row["ratio"]
                fact["shadbala_multiplier"] = mult
            scores[area] += delta
            subst[area].append(fact)

    # --- varga corroboration (small, cited deltas of +/-0.1) -------------
    # Relationships: 7th lord and Venus judged in the navamsa (D9);
    # career: 10th lord judged in the dasamsa (D10). Own/exalted adds,
    # debilitated subtracts.
    seventh_lord = chart["house_lords"][7]["lord"]
    for planet in dict.fromkeys([seventh_lord, "Venus"]):
        dig = _varga_dignity(planet, _navamsa_sign(chart["planets"][planet]["longitude"]))
        if dig is None:
            continue
        delta = 0.1 if dig in ("exalted", "own") else -0.1
        scores["relationships"] += delta
        subst["relationships"].append({
            "type": "varga_dignity", "varga": "D9", "planet": planet,
            "role": "7th lord" if planet == seventh_lord else "Venus (kalatra karaka)",
            "dignity": dig, "delta": delta,
        })
    tenth_lord = chart["house_lords"][10]["lord"]
    dig = _varga_dignity(tenth_lord, _dashamsa_sign(chart["planets"][tenth_lord]["longitude"]))
    if dig is not None:
        delta = 0.1 if dig in ("exalted", "own") else -0.1
        scores["career"] += delta
        subst["career"].append({
            "type": "varga_dignity", "varga": "D10", "planet": tenth_lord,
            "role": "10th lord", "dignity": dig, "delta": delta,
        })

    # --- Jaimini chara-dasha corroboration (K.N. Rao school) -------------
    # A small, cited delta (+/-0.1) when the currently-active Jaimini chara
    # dasha sign IS the house whose classical significations it should
    # activate (7th=relationships, 10th=career, 2nd/11th=wealth), i.e. the
    # Rashi (sign-based) dasha system agrees with the Vimshottari (nakshatra
    # -based) dasha lords already scored above. Absence of the sign in the
    # active path is not penalised (it is a corroboration bonus, not an
    # independent claim).
    lagna_sign = chart["lagna"]["sign"]
    darakaraka = next(k["planet"] for k in jaimini["karakas"] if k["karaka"] == "Darakaraka")
    active_chara_signs = {node["sign"] for node in jaimini["active"]}
    _CHARA_HOUSE_AREA = {7: "relationships", 10: "career", 2: "wealth", 11: "wealth"}
    for house, area in _CHARA_HOUSE_AREA.items():
        house_sign = (lagna_sign + house - 1) % 12
        if house_sign in active_chara_signs:
            scores[area] += 0.1
            subst[area].append({
                "type": "jaimini_chara_dasha_corroboration", "house": house,
                "sign": K.SIGN_NAMES[house_sign], "delta": 0.1,
                "note": f"active chara dasha sign is the {house}th house from lagna",
            })
    darakaraka_sign = chart["planets"][darakaraka]["sign"]
    if darakaraka_sign in active_chara_signs:
        scores["relationships"] += 0.1
        subst["relationships"].append({
            "type": "jaimini_chara_dasha_corroboration", "karaka": "Darakaraka",
            "planet": darakaraka, "sign": K.SIGN_NAMES[darakaraka_sign], "delta": 0.1,
            "note": "active chara dasha sign is the Darakaraka's (spouse significator) sign",
        })

    # --- transit modulation ----------------------------------------------
    ss = transits["sade_sati"]
    if ss["active"]:
        for area, hit in (("health", -0.2), ("career", -0.15), ("family", -0.15)):
            scores[area] += hit
            transit_net[area] += hit
            subst[area].append({
                "type": "sade_sati", "phase": ss["phase"], "delta": hit,
                "start": ss["start"], "end": ss["end"],
            })
    if ss["ashtama_shani"]:
        scores["health"] += -0.2
        transit_net["health"] += -0.2
        subst["health"].append({"type": "ashtama_shani", "delta": -0.2})
    if ss["kantaka_shani"]:
        for area in ("career", "relationships"):
            scores[area] += -0.1
            transit_net[area] += -0.1
            subst[area].append({
                "type": "kantaka_shani", "delta": -0.1,
                "saturn_house_from_moon": ss["saturn_house_from_moon"],
            })

    for hit in transits["double_transit"]:
        for area in AREAS:
            pol = AREA_HOUSE_POLARITY[area].get(hit["house"], 0)
            if pol > 0:
                delta = 0.15 * pol
                scores[area] += delta
                transit_net[area] += delta
                subst[area].append({
                    "type": "double_transit", "house": hit["house"],
                    "saturn": hit["saturn"], "jupiter": hit["jupiter"],
                    "delta": round(delta, 4),
                })

    gochara = {row["planet"]: row for row in transits["gochara"]}
    for lord, (prof, weight, node) in profiles.items():
        row = gochara[lord]
        g_delta = 0.1 * weight * (1 if row["favourable"] else -1)
        ts = transit_strength(av, row["sign"], lord if lord in av["bav"] else None)
        sav_delta = {"strong": 0.05, "weak": -0.05, "average": 0.0}[ts["sav_verdict"]] * weight
        relevant_areas = {a for a, _, _ in _dasha_contributions(prof, weight, node["level_name"])}
        for area in (relevant_areas or set(AREAS)):
            scores[area] += g_delta + sav_delta
            transit_net[area] += g_delta + sav_delta
            subst[area].append({
                "type": "gochara_of_dasha_lord", "lord": lord,
                "level": node["level_name"],
                "house_from_moon": row["house_from_moon"],
                "favourable": row["favourable"],
                "sav_bindus": ts["sav_bindus"], "sav_verdict": ts["sav_verdict"],
                "delta": round(g_delta + sav_delta, 4),
            })

    # --- windows -----------------------------------------------------------
    windows = []
    for node in path[1:]:  # antar + pratyantar
        windows.append({
            "from": node["start"], "to": node["end"],
            "why": f"{node['lord']} {node['level_name']}",
        })
    if ss["active"] and ss["start"]:
        windows.append({"from": ss["start"], "to": ss["end"],
                        "why": f"Sade Sati {ss['phase']}"})

    areas_out = []
    for area in AREAS:
        raw = scores[area]
        score = math.tanh(raw * 1.5)  # squash into [-1, 1]
        tn = transit_net[area]
        trend = "improving" if tn > 0.05 else ("challenging" if tn < -0.05 else "stable")
        areas_out.append({
            "area": area,
            "score": round(score, 3),
            "raw_score": round(raw, 4),
            "favorability_label": favorability_label(score),
            "trend": trend,
            "windows": windows,
            "substantiation": subst[area],
        })

    return {
        "on": on_dt.isoformat(),
        "dasha_path": path,
        "areas": areas_out,
        "context": {
            "lagna": {"sign": chart["lagna"]["sign"],
                      "sign_name": chart["lagna"]["sign_name"]},
            "moon": {"sign": chart["planets"]["Moon"]["sign"],
                     "sign_name": chart["planets"]["Moon"]["sign_name"],
                     "nakshatra": chart["planets"]["Moon"]["nakshatra"]},
            "sade_sati": ss,
            "double_transit": transits["double_transit"],
            "active_yogas": [y["name"] for y in yogas if y["present"]],
        },
        # Full six-fold strength (Raman conventions) and Jaimini karakas +
        # K.N. Rao Chara Dasha, exposed in full (not just used internally
        # for the dasha-lord weighting above) so the interpretation layer
        # can ground Shadbala/Jaimini-specific questions ("is Jupiter
        # strong enough to give results?", "what does my chara dasha say?")
        # in real computed facts instead of declining to answer or, worse,
        # inventing numbers.
        "shadbala": shadbala,
        "jaimini": jaimini,
        "chart": {
            "lagna": chart["lagna"],
            "planets": chart["planets"],
            "house_lords": chart["house_lords"],
        },
    }
