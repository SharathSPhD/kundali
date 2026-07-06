"""Opt-in cross-check against NASA JPL Horizons (needs network + is slow:
~70 API calls with a politeness delay). Skipped by default so the main
suite stays hermetic and CI-safe; run explicitly with:

    RUN_HORIZONS_CHECK=1 pytest tests/test_horizons_cross_check.py -v -s

See `backend/validation/validate_horizons.py` for the full methodology and
`VALIDATION.md` for a committed run's results.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_HORIZONS_CHECK"),
    reason="opt-in, network-dependent (set RUN_HORIZONS_CHECK=1 to run)",
)


def test_horizons_agreement_within_one_arcminute():
    from validation.validate_horizons import run, summarize

    results = run(sleep_between_calls=1.0)
    summary = summarize(results)
    assert summary["n_comparisons"] > 0
    # Sub-arcminute target (see VALIDATION.md); Moshier-fallback + apparent-
    # position convention differences typically land well under this.
    assert summary["max_diff_arcsec"] < 60.0, summary["worst"]
