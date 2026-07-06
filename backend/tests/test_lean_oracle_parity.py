"""Pytest wrapper for Lean oracle differential testing.

Note: when Swiss Ephemeris is not installed, the parent ``backend/tests/conftest.py``
may fail to load before this module is collected. Run with ``--noconftest`` or invoke
``backend/validation/validate_lean_oracle.py`` directly (as CI does).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAN_DIR = REPO_ROOT / "formal" / "lean-kundali"
ORACLE_BIN = LEAN_DIR / ".lake" / "build" / "bin" / "oracle"
VALIDATE_SCRIPT = REPO_ROOT / "backend" / "validation" / "validate_lean_oracle.py"


def _lean_available() -> bool:
    if os.environ.get("LEAN_ORACLE_AVAILABLE", "").lower() in ("1", "true", "yes"):
        return True
    if ORACLE_BIN.exists():
        return True
    # Try building once
    if not (LEAN_DIR / "lakefile.toml").exists():
        return False
    try:
        proc = subprocess.run(
            ["lake", "build", "oracle"],
            cwd=LEAN_DIR,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        # `lake` isn't on PATH — the standard backend-tests CI job doesn't
        # install the Lean toolchain (that's the separate lean-verification
        # job's job), so this is an expected skip there, not a failure.
        return False
    return proc.returncode == 0 and ORACLE_BIN.exists()


@pytest.mark.skipif(
    not _lean_available(),
    reason="Lean toolchain/oracle binary not available (set LEAN_ORACLE_AVAILABLE=1 to force)",
)
def test_lean_oracle_parity():
    import subprocess
    import sys

    if not _lean_available():
        pytest.skip("Lean toolchain/oracle binary not available")

    proc = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT)],
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert proc.returncode == 0, "validate_lean_oracle.py reported mismatches"
