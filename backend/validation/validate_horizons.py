"""Cross-check the engine's sidereal ephemeris against NASA JPL Horizons.

Horizons returns *tropical* geocentric apparent ecliptic longitude. Our
engine works in sidereal (Lahiri by default). To compare on the same
footing: tropical_longitude = engine_sidereal_longitude + ayanamsa_value
(engine's own `swe.get_ayanamsa_ut`, i.e. this checks raw planetary
ephemeris agreement, not ayanamsa choice — ayanamsa is a separate,
well-established constant we take from Swiss Ephemeris itself).

Horizons is free, public, and unauthenticated: no API key required.
https://ssd-api.jpl.nasa.gov/doc/horizons.html
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime

from app.engine.ephemeris import EngineConfig, ayanamsa_value, julian_day_from_utc, planet_longitudes

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Horizons body codes (geocentric, "@399" observer = Earth centre body).
HORIZONS_IDS = {
    "Sun": "10",
    "Moon": "301",
    "Mercury": "199",
    "Venus": "299",
    "Mars": "499",
    "Jupiter": "599",
    "Saturn": "699",
}

# A spread of UTC instants across the ephemeris range the app actually
# serves (1900-2030), not clustered around "now".
SAMPLE_INSTANTS = [
    datetime(1900, 3, 21, 12, 0, 0),
    datetime(1925, 7, 4, 6, 0, 0),
    datetime(1947, 8, 15, 0, 0, 0),
    datetime(1969, 7, 20, 20, 17, 0),
    datetime(1984, 12, 1, 15, 30, 0),
    datetime(2000, 1, 1, 0, 0, 0),
    datetime(2010, 6, 15, 9, 45, 0),
    datetime(2020, 2, 29, 3, 0, 0),
    datetime(2026, 7, 6, 12, 0, 0),
    datetime(2030, 11, 11, 18, 0, 0),
]


@dataclass
class HorizonsResult:
    planet: str
    instant: str
    engine_tropical_lon: float
    horizons_tropical_lon: float
    diff_arcsec: float


def _fetch_horizons_longitude(body_id: str, jd: float) -> float:
    """Geocentric apparent ecliptic longitude (deg) at exactly `jd` (TDB~UT
    is close enough at arcsecond precision for this cross-check)."""
    params = {
        "format": "json",
        "COMMAND": f"'{body_id}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'500@399'",
        "QUANTITIES": "'31'",  # 31 = Obs ecliptic lon & lat
        "TLIST": f"'{jd}'",
        "CAL_FORMAT": "JD",
    }
    url = HORIZONS_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read())
    text = data["result"]
    m = re.search(r"\$\$SOE\s*\n(.+?)\n\$\$EOE", text, re.DOTALL)
    if not m:
        raise RuntimeError(f"Horizons response missing ephemeris block: {text[:400]}")
    line = m.group(1).strip().splitlines()[0]
    # Whitespace-separated columns: JDUT, ObsEcLon, ObsEcLat
    parts = line.split()
    lon = float(parts[1])
    return lon % 360.0


def run(sleep_between_calls: float = 1.5) -> list[HorizonsResult]:
    config = EngineConfig(ayanamsa="lahiri")
    results = []
    for instant in SAMPLE_INSTANTS:
        jd = julian_day_from_utc(instant)
        ayan = ayanamsa_value(jd, config)
        planets = planet_longitudes(jd, config)
        for name, body_id in HORIZONS_IDS.items():
            engine_sidereal = planets[name]["longitude"]
            engine_tropical = (engine_sidereal + ayan) % 360.0
            horizons_tropical = _fetch_horizons_longitude(body_id, jd)
            diff = (engine_tropical - horizons_tropical + 180.0) % 360.0 - 180.0
            results.append(HorizonsResult(
                planet=name, instant=instant.isoformat(),
                engine_tropical_lon=round(engine_tropical, 6),
                horizons_tropical_lon=round(horizons_tropical, 6),
                diff_arcsec=round(abs(diff) * 3600.0, 2),
            ))
            time.sleep(sleep_between_calls)  # be polite to a free public API
    return results


def summarize(results: list[HorizonsResult]) -> dict:
    diffs = [r.diff_arcsec for r in results]
    return {
        "n_comparisons": len(results),
        "max_diff_arcsec": max(diffs) if diffs else None,
        "mean_diff_arcsec": round(sum(diffs) / len(diffs), 3) if diffs else None,
        "worst": max(results, key=lambda r: r.diff_arcsec) if results else None,
    }


if __name__ == "__main__":
    out = run()
    summary = summarize(out)
    print(json.dumps({
        "summary": {k: (asdict(v) if isinstance(v, HorizonsResult) else v)
                    for k, v in summary.items()},
        "results": [asdict(r) for r in out],
    }, indent=2))
