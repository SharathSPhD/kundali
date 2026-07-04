import os
import sys

os.environ.setdefault("AUTH_DISABLED", "1")

# Make `app` importable when pytest runs from the backend dir or repo root.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest  # noqa: E402

from app.engine.ephemeris import EngineConfig, _position_dict  # noqa: E402
from app.engine.chart import assemble_chart  # noqa: E402


@pytest.fixture(scope="session")
def config():
    return EngineConfig()


def make_position(sign: int, deg: float, speed: float = 1.0) -> dict:
    return _position_dict(sign * 30.0 + deg, speed)


def make_chart(lagna=(0, 15.0), placements=None) -> dict:
    """Synthetic chart builder for yoga/varga tests.

    placements: {planet: (sign, deg) | (sign, deg, speed)}. Missing grahas get
    spread-out defaults chosen to avoid accidental conjunctions with Sun.
    """
    defaults = {
        "Sun": (4, 10.0), "Moon": (7, 20.0), "Mars": (1, 5.0),
        "Mercury": (5, 12.0), "Jupiter": (8, 8.0), "Venus": (6, 18.0),
        "Saturn": (10, 25.0), "Rahu": (2, 15.0), "Ketu": (8, 15.0),
    }
    placements = {**defaults, **(placements or {})}
    planets = {}
    for name, spec in placements.items():
        sign, deg = spec[0], spec[1]
        speed = spec[2] if len(spec) > 2 else 1.0
        planets[name] = make_position(sign, deg, speed)
    lagna_pos = make_position(lagna[0], lagna[1])
    return assemble_chart(lagna_pos, planets)
