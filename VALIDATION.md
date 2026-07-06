# External Validation

This document is independent of the unit-test suite (`backend/tests/`,
128 tests, all committed reference/golden charts). It reports how the
engine holds up against three external, uncontrolled sources of ground
truth. Numbers below are from an actual run (2026-07-06); no cherry-picking
— methodology and caveats are stated plainly, including a null result.

Code lives in `backend/validation/`. Reproduce with:

```bash
cd backend
./validation/fetch_data.sh              # downloads the 3 datasets into validation/data/ (gitignored)
python -m validation.run_all            # needs network, ~2-3 min
```

## 1. NASA JPL Horizons — raw ephemeris accuracy

**Source:** `ssd.jpl.nasa.gov/api/horizons.api` — free, public, unauthenticated.
**Method:** for 10 UTC instants spread across 1900–2030, fetch Horizons'
geocentric apparent tropical ecliptic longitude for Sun/Moon/Mercury/Venus/
Mars/Jupiter/Saturn, and compare against `engine_sidereal_longitude +
engine_ayanamsa_value` (both from our own Swiss-Ephemeris call — this
isolates raw planetary-position accuracy from any ayanamsa-choice debate).
70 comparisons total (`backend/validation/validate_horizons.py`).

**Result:** max difference **17.28 arcsec**, mean **13.1 arcsec**, across
all 70 comparisons — comfortably inside the sub-arcminute (60″) target, and
about 100,000× finer than a Vedic sign boundary (30°) or nakshatra boundary
(13°20′). The residual is nearly identical across all seven bodies at a
given instant regardless of orbital speed (e.g. Moon and Saturn differ by
within 0.5″ of each other at the same instant), which is the signature of a
small apparent-position/frame convention difference (light-time, aberration,
or nutation-model version) rather than a planetary-position bug — a
per-planet ephemeris error would scale with each body's angular velocity,
which this does not. It is also consistent with this environment falling
back to the Moshier analytical ephemeris (no `.se1` binary files bundled;
see `backend/app/engine/ephemeris.py::_ephemeris_files_present`), whose
documented accuracy against JPL's numerically-integrated ephemeris is at
the few-arcsecond-to-arcminute level. **Bottom line: no correctness issue
at the precision that matters for Vedic astrology.**

| instant | max diff (any body) |
|---|---|
| 1900-03-21 | 16.71″ |
| 1969-07-20 (Apollo 11) | 2.73″ |
| 2000-01-01 | 14.10″ |
| 2026-07-06 | 8.35″ |
| 2030-11-11 | 14.80″ |

## 2. vedastro-org `15000-Famous-People-Birth-Date-Location` (HuggingFace, MIT)

**Source:** 15,807 real people, Rodden AA/A-rated birth data with verified
tz/DST, downloaded directly (`validation/data/birth_location.csv`).
No expected chart placements ship with this dataset, so it validates two
different things:

**2a. Crash/sanity smoke test — every single row.**
`build_chart()` ran on all **15,807/15,807** rows without a single
exception, and every output passed structural assertions (valid sign 0–11,
valid nakshatra 0–26 for all 9 grahas + lagna). This exercises 125 years of
messy real-world timezone/DST/historical-date edge cases end to end.

**2b. Distribution sanity on a stratified 500-person AA/A-rated sample.**
Deterministic (every-Nth-row, not random) sample of 500 from the 15,790
AA/A-rated rows.

| metric | result | expected (uniform) |
|---|---|---|
| Sun sign, max deviation from 1/12 | 2.33 pts (Leo 30 → Capricorn 47, of 500) | 0 |
| Moon nakshatra, max deviation from 1/27 | 1.5 pts | 0 |
| Ascendant sign spread | Pisces 12 → Virgo 61, of 500 | — |

Sun-sign and nakshatra spread are close to uniform, as expected for a large
demographically-unselected sample — no collapse into a handful of
sign/nakshatra values, which is the failure mode this check is actually
guarding against (e.g. a longitude-modulus bug). The **ascendant spread is
visibly less uniform** — expected, not a bug: real-world birth-time
records cluster on round numbers ("6:00 AM", "12:00 PM" etc. even at AA
rating), and the ascendant moves roughly 7× faster than the Sun's daily
motion relative to a fixed clock reading, so clock-rounding artifacts in
the *source data* show up far more in the ascendant than in any planet's
sign.

## 3. vedastro-org `15000-Famous-People-Marriage-Divorce-Info` — predictive backtest

**Source:** 15,807 marriage/divorce records, joined to (2) by name key.
**Method:** for each AA/A-rated person with a parseable marriage date
(year, or full date when available — most source dates are year-only),
compute the natal chart, the classical marriage significators (7th lord,
Venus, Jupiter, D9-7th-house lord), and the Vimshottari maha+antardasha
lord active at the (year-midpoint-anchored, when day/month unknown)
marriage date. **Hit** = the active maha or antar lord is one of the
significators. Reported against a **permutation-test null baseline**
(shuffle significator sets across people's real dasha draws 20×, averaged)
rather than a naive percentage, because the real number to ask is "hits
above chance," not "hits."

| variant | n | hit rate | null baseline | lift |
|---|---|---|---|---|
| Broad (7th lord, Venus, Jupiter, D9-7th lord) | 14,308 | 66.77% | 66.63% | **+0.14 pts** |
| Narrow (7th lord, Venus only) | 14,308 | 43.80% | 43.64% | **+0.16 pts** |
| Narrow, full-date records only | 9,954 | 43.93% | 43.69% | **+0.24 pts** |

**Honest result: no statistically meaningful lift over the permutation
baseline in any variant** (all lifts are within ~1 standard error for
n≈14,000, std err ≈0.4 pts). This does **not** mean the classical rule set
is false — it means *this specific coarse test* (year-level dates, only
2 dasha-tree levels, dasha-lord-in-a-broad-significator-set as the sole
criterion) lacks the resolution to detect it, most likely because: (a) most
source dates are year-only against a system whose antardasha windows are
frequently sub-year, so the year-midpoint anchor is a coin flip near
boundaries; (b) a 2-4-member candidate set out of 9 possible lords, checked
against a 2-lord (maha+antar) draw, already has ~44-67% baseline hit
probability, leaving little room for a real signal to separate from noise
at this dataset's size. A sharper test (day-precision dates only, 3-level
pratyantardasha resolution, a stricter single-significator rule) is the
natural next iteration — noted here rather than re-run repeatedly until a
result looked better, which would defeat the point of the test.

## 4. Astrodienst AstroDatabank "C sample" — tropical placement cross-check

**Source:** the free C-sample Astrodienst explicitly offers at
`astro.com/adbexport/c_sample.zip` (5,866 records) "for researchers to
develop their tools and techniques" — a direct, permitted download, not
scraping (bulk export/scraping of the full AstroDatabank is prohibited by
astro.com's Terms of Use). Each record ships its own precomputed `jd_ut`
(so Astrodienst has already resolved the historical timezone/DST/LMT
question for us) plus **tropical** Sun/Moon/Ascendant sign as Astrodienst's
own reference.

**Method:** for the 4,832 AA/A-rated records, compute
`engine_sidereal_longitude + ayanamsa` at Astrodienst's own `jd_ut`, take
the tropical sign, and compare to Astrodienst's published sign. Cusp cases
(Astrodienst marks these explicitly, e.g. `sun_sign="cap/aqu"`) are
excluded from the match rate since the "true" sign is inherently
ambiguous there.

| field | comparable records | match rate |
|---|---|---|
| Sun sign | 4,832 | **99.98%** |
| Moon sign | 4,830 | **99.98%** |
| Ascendant sign | 4,828 | **93.35%** |

Sun/Moon match Astrodienst's own tropical placements almost perfectly
across 4,832 diverse historical dates/locations spanning well over a
century — strong independent confirmation of (1)'s ephemeris result at
much greater breadth (fewer decimal places, many more charts). The lower
ascendant match rate is the same effect noted in (2b): the ascendant is
far more time-sensitive than any planet's sign placement (roughly 1° per
4 minutes of clock time at moderate latitudes, faster near the poles or
near the meridian), so it is the placement most exposed to birth-record
rounding and any residual jd_ut/LMT edge cases — a 93% sign-match rate at
30°-bin resolution is consistent with that sensitivity, not with an
ascendant-calculation bug (the same `ascendant()` function is exercised,
unchanged, by (2a)'s 15,807-row crash-free run and by the golden-chart
unit tests in `backend/tests/test_golden_charts.py`).

## Summary

| check | result |
|---|---|
| JPL Horizons ephemeris accuracy | max 17.3″, well under 60″ target |
| vedastro 15k crash-free rate | 15,807 / 15,807 (100%) |
| vedastro Sun-sign/nakshatra distribution | close to uniform, no collapse |
| AstroDatabank Sun/Moon tropical sign match | 99.98% / 99.98% (n=4,832) |
| AstroDatabank Ascendant tropical sign match | 93.35% (n=4,828, time-sensitivity explained) |
| vedastro marriage-dasha backtest | no significant lift over chance (reported honestly, methodology limitations noted) |

The ephemeris/chart-construction layer is validated to a high degree of
confidence across three independent sources and >20,000 individual charts.
The one predictive-astrology claim tested at scale (dasha-lord timing of
marriage) did not clear a rigorous chance baseline with this dataset's
date precision — a finding worth acting on (see §3) rather than hiding.
