"""Shared parsing helpers for the validation datasets."""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from datetime import datetime

from app.engine.ephemeris import BirthData

_STDTIME_RE = re.compile(
    r"^(?P<h>\d{2}):(?P<m>\d{2}) (?P<d>\d{2})/(?P<mo>\d{2})/(?P<y>\d{4}) "
    r"(?P<sign>[+-])(?P<tzh>\d{2}):(?P<tzm>\d{2})$"
)


@dataclass
class VedastroPerson:
    row_key: str
    name: str
    rodden: str | None
    birth: BirthData


def parse_vedastro_birthtime(row_key: str, name: str, birth_time_json: str,
                              notes: str) -> VedastroPerson | None:
    """Parse one vedastro `PersonList-15k.csv` row into a BirthData.

    `BirthTime` is a JSON blob: `{"StdTime": "HH:MM DD/MM/YYYY +TZ:00",
    "Location": {"Name", "Longitude", "Latitude"}}`. Returns None for rows
    that fail to parse (malformed dates from the wild, kept out of the
    engine input rather than guessed at).
    """
    try:
        blob = json.loads(birth_time_json)
    except (json.JSONDecodeError, TypeError):
        return None
    std_time = blob.get("StdTime")
    loc = blob.get("Location") or {}
    m = _STDTIME_RE.match(std_time or "")
    if not m or "Longitude" not in loc or "Latitude" not in loc:
        return None
    tz = (1 if m["sign"] == "+" else -1) * (int(m["tzh"]) + int(m["tzm"]) / 60.0)
    date = f"{m['y']}-{m['mo']}-{m['d']}"
    time = f"{m['h']}:{m['m']}"
    try:
        rodden = ast.literal_eval(notes).get("rodden") if notes else None
    except (ValueError, SyntaxError):
        rodden = None
    return VedastroPerson(
        row_key=row_key,
        name=name,
        rodden=rodden,
        birth=BirthData(date=date, time=time, lat=float(loc["Latitude"]),
                        lon=float(loc["Longitude"]), tz_offset=tz,
                        place_name=loc.get("Name")),
    )


_MARRIAGE_DATE_RE = re.compile(r"^(?:(?P<d>\d{2})/(?P<m>\d{2})/)?(?P<y>\d{4})$")


def parse_marriage_date(raw: str) -> tuple[int, int | None, int | None] | None:
    """(year, month, day) — month/day are None when the source only gave a year."""
    m = _MARRIAGE_DATE_RE.match((raw or "").strip())
    if not m:
        return None
    return int(m["y"]), (int(m["m"]) if m["d"] else None), (int(m["d"]) if m["d"] else None)


def parse_marriage_info(info_json: str) -> list[dict]:
    try:
        blob = json.loads(info_json)
    except (json.JSONDecodeError, TypeError):
        return []
    return blob.get("marriages", [])


def approx_marriage_datetime(year: int, month: int | None, day: int | None) -> datetime:
    """Mid-year when only a year is known, else the exact date — noon UTC
    either way (dasha-lord resolution is day-level, not hour-level)."""
    return datetime(year, month or 7, day or 1, 12, 0, 0)
