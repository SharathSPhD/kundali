"""AstroDatabank "C sample" cross-check.

Astrodienst's C sample (astro.com/adbexport, ~5,866 records, offered
explicitly for "researchers to develop their tools and techniques" — not
scraped) ships each entry with:
- a precomputed `jd_ut` (Julian Day, UT) — Astrodienst has already resolved
  the birth timezone/DST/LMT convention for us, so we use it directly and
  skip our own tz handling entirely for this check;
- `slati`/`slong` (birthplace lat/lon, e.g. "48n52", "2e20");
- **tropical** Sun/Moon/Ascendant sign as Astrodienst's own reference
  ("positions" element, e.g. `sun_sign="lib"`).

This validates the same thing as the Horizons check (raw ephemeris +
ayanamsa-reconversion correctness) but at *sign* resolution, across ~5,800
diverse historical dates/locations instead of 10 manually chosen instants —
good breadth, coarser precision. A sign-boundary case (Astrodienst marks
these explicitly, e.g. `sun_sign="cap/aqu"`) is excluded from the strict
match rate since the "true" sign is inherently ambiguous there.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from app.engine.chart import assemble_chart
from app.engine.constants import SIGN_NAMES
from app.engine.ephemeris import EngineConfig, ascendant, ayanamsa_value, planet_longitudes

DATA_PATH = Path(__file__).parent / "data" / "c_sample" / "c_sample.xml"

_SIGN_ABBR = {
    "ari": "Aries", "tau": "Taurus", "gem": "Gemini", "can": "Cancer",
    "leo": "Leo", "vir": "Virgo", "lib": "Libra", "sco": "Scorpio",
    "sag": "Sagittarius", "cap": "Capricorn", "aqu": "Aquarius", "pis": "Pisces",
}

_COORD_RE = re.compile(r"^(\d+)([nsew])(\d+)$")


def _parse_coord(raw: str) -> float | None:
    m = _COORD_RE.match((raw or "").strip().lower())
    if not m:
        return None
    deg, hemi, minute = int(m[1]), m[2], int(m[3])
    val = deg + minute / 60.0
    return -val if hemi in ("s", "w") else val


def _iter_entries():
    for _event, elem in ET.iterparse(DATA_PATH):
        if elem.tag == "adb_entry":
            yield elem
            elem.clear()


def _extract(entry) -> dict | None:
    pd = entry.find("public_data")
    if pd is None:
        return None
    bdata = pd.find("bdata")
    rodden = pd.findtext("roddenrating")
    if bdata is None:
        return None
    sbtime = bdata.find("sbtime")
    place = bdata.find("place")
    positions = bdata.find("positions")
    if sbtime is None or place is None or positions is None:
        return None
    jd_ut = sbtime.get("jd_ut")
    lat = _parse_coord(place.get("slati"))
    lon = _parse_coord(place.get("slong"))
    if not jd_ut or lat is None or lon is None:
        return None
    return {
        "adb_id": entry.get("adb_id"),
        "rodden": rodden,
        "jd_ut": float(jd_ut),
        "lat": lat,
        "lon": lon,
        "sun_sign": positions.get("sun_sign"),
        "moon_sign": positions.get("moon_sign"),
        "asc_sign": positions.get("asc_sign"),
    }


def _sign_matches(abbr: str | None, computed_sign_name: str) -> bool | None:
    """None when the record itself is ambiguous (cusp) or absent."""
    if not abbr or "/" in abbr:
        return None
    expected = _SIGN_ABBR.get(abbr)
    if expected is None:
        return None
    return expected == computed_sign_name


def run(rodden_filter: tuple[str, ...] = ("AA", "A")) -> dict:
    config = EngineConfig(ayanamsa="lahiri")
    totals = {"sun": [0, 0], "moon": [0, 0], "asc": [0, 0]}  # [matches, comparable]
    n_total = 0
    n_eligible = 0
    n_engine_error = 0
    mismatches = []

    for entry in _iter_entries():
        n_total += 1
        row = _extract(entry)
        if row is None or row["rodden"] not in rodden_filter:
            continue
        n_eligible += 1
        try:
            jd = row["jd_ut"]
            planets = planet_longitudes(jd, config)
            ayan = ayanamsa_value(jd, config)
            lagna = ascendant(jd, row["lat"], row["lon"], config)
            sun_tropical_sign = SIGN_NAMES[int((planets["Sun"]["longitude"] + ayan) % 360 // 30)]
            moon_tropical_sign = SIGN_NAMES[int((planets["Moon"]["longitude"] + ayan) % 360 // 30)]
            asc_tropical_sign = SIGN_NAMES[int((lagna["longitude"] + ayan) % 360 // 30)]
        except Exception:  # noqa: BLE001
            n_engine_error += 1
            continue

        for key, computed, abbr_key in (
            ("sun", sun_tropical_sign, "sun_sign"),
            ("moon", moon_tropical_sign, "moon_sign"),
            ("asc", asc_tropical_sign, "asc_sign"),
        ):
            m = _sign_matches(row[abbr_key], computed)
            if m is None:
                continue
            totals[key][1] += 1
            if m:
                totals[key][0] += 1
            elif len(mismatches) < 20:
                mismatches.append({
                    "adb_id": row["adb_id"], "field": key,
                    "expected": row[abbr_key], "computed": computed,
                })

    return {
        "total_records_in_sample": n_total,
        "eligible_aa_a_rated": n_eligible,
        "engine_errors": n_engine_error,
        "sun_sign_match_rate": round(totals["sun"][0] / totals["sun"][1], 4) if totals["sun"][1] else None,
        "moon_sign_match_rate": round(totals["moon"][0] / totals["moon"][1], 4) if totals["moon"][1] else None,
        "asc_sign_match_rate": round(totals["asc"][0] / totals["asc"][1], 4) if totals["asc"][1] else None,
        "sun_comparable": totals["sun"][1], "moon_comparable": totals["moon"][1],
        "asc_comparable": totals["asc"][1],
        "mismatch_examples": mismatches,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
