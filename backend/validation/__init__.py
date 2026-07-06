"""Independent validation suite for the Kundali engine.

Not part of the pytest unit-test suite (those validate internal consistency
against hand-computed / published reference charts). This package validates
against three *external* sources of ground truth:

- NASA JPL Horizons (raw ephemeris accuracy)
- vedastro-org HuggingFace datasets (statistical sanity + predictive backtest)
- Astrodienst AstroDatabank "C sample" (tropical placement cross-check)

Run via `python -m validation.run_all` from `backend/`. Requires network
access for the Horizons check and the dataset downloads (cached locally
under `validation/data/` after first run).
"""
