# Lean 4 formal verification for Kundali

Machine-checked proofs for a **representative slice** of the Python jyotisha engine
(`backend/app/engine/{constants,vargas,dashas,yogas}.py`), plus a differential-testing
oracle and a Nyaya/pramana argument-form scaffold.

> **Verified arithmetic kernel, not verified astrology.** Lean proves properties of the
> *specified computational rules* and the *logical form* of syllogisms. It does not and
> cannot validate predictive or interpretive astrological claims. See `docs/lean-kundali.md`.

## Toolchain

| Component | Version |
|-----------|---------|
| Lean | `leanprover/lean4:v4.31.0` (see `lean-toolchain`) |
| mathlib | `v4.31.0` via Lake (`lakefile.toml`) |
| Prebuilt cache | `lake exe cache get` (recommended before first build) |

Build:

```bash
source ~/.elan/env
cd formal/lean-kundali
lake exe cache get   # once, fetches mathlib binaries
lake build
lake exe oracle formal/schemas/chart_oracle_v1.json  # example path
```

## What is proved (theorem inventory)

### `Kundali/Longitude.lean`
- `fullCircle_pos` — full circle is positive
- `normalize_range` — normalized longitude in `[0, 360)`
- `normalize_idempotent` — `normalize (normalize x) = normalize x`

### `Kundali/Nakshatra.lean`
- `nakshatra_cover` / `pada_cover` — 27×4 partition spans the circle
- `nakshatraIndex_valid` / `padaIndex_valid` — indices in range
- `nakshatra_exhaustive` / `pada_exhaustive` — totality
- `nakshatra_partition_covers` / `pada_partition_covers` — interval cover bounds
- `nakshatra_disjoint` — ordered non-overlap of nakshatra slots

### `Kundali/Vimshottari.lean`
- `vimshottari_sum_120` — nine mahadasha weights sum to 120
- `antardasha_durations_sum` — proportional antardashas sum to parent `D`
- `durations_prefix_succ` / `antardasha_consecutive` — gap-free prefix tiling
- `vimshottari_antardasha_partition` — instantiated partition for nine antardashas
- `vimshottari_mahadasha_partition` — 120-year mahadasha cycle sum

### `Kundali/Vargas.lean`
- `part_lt` / `part_clamp_redundant` — `_part` codomain membership
- `d1_total` … `d12_total` — D1,D2,D3,D9,D10,D12 return `Fin 12`

### `Kundali/Yogas.lean`
- `kemadruma_final_def` — final = raw ∧ ¬cancelled
- `kemadruma_cancelled_implies_not` — cancellation suppresses yoga
- `kemadruma_present_implies_moon_not_kendra` — consistency meta-theorem
- `gaja_kesari_example` — sample Gaja Kesari chart

### `Kundali/Nyaya.lean`
- `nyaya_valid_example` / `nyaya_missing_vyapti` / `nyaya_with_fallacy` — form checker cases

## Numeric model

Longitudes use exact rationals (`ℚ`) with `normalize` for `[0,360)`. Varga `_part` uses
`eps = 1/10⁹` matching Python `_EPS`. This proves the **rule as specified**, not IEEE
float bit equality.

## Oracle & Python bridge

JSON contract: `formal/schemas/chart_oracle_v1.json`

```bash
python backend/validation/validate_lean_oracle.py
pytest backend/tests/test_lean_oracle_parity.py -v   # skips if Lean absent
```

## Not covered (honest scope limits)

- Remaining vargas (D4,D7,D16,D20,D24,D27,D30,D40,D45,D60) — not in Lean v1
- Full yoga corpus, shadbala, dasha timelines with datetime clipping
- Full Nyaya hetvābhāsa taxonomy or semantic vyāpti verification
- Swiss Ephemeris / ephemeris correctness (only rule-level parity on test vectors)

## Nyaya bridge

Python mirror: `backend/app/oracle/nyaya_bridge.py` — `well_formed` matches
`Kundali.Nyaya.wellFormed` (form only).
