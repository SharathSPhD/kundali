# Kundali — Rigorous Vedic Astrology (South Indian)

Deterministic jyotisha engine + full-stack app. Every prediction is computed (Swiss Ephemeris, Lahiri ayanamsa, whole-sign houses) and carries a machine-readable substantiation trail; the optional LLM layer only narrates engine output — it never invents positions or dates.

## What's inside
- `backend/` — Python calculation engine + FastAPI. All 16 shodasha vargas, Vimshottari dasha tree (maha→antar→pratyantar+), gochara transits with Sade Sati and Jupiter–Saturn double transit (K.N. Rao), ~28 classical yogas, full Ashtakavarga (BPHS Ch.66), Panchanga (tithi/vara/nakshatra/yoga/karana, sunrise-based vara), 36-point Ashtakoota matching + Mangal dosha, full Shadbala (six-fold strength, Raman conventions, cross-validated against PyJHora), Jaimini chara karakas + K.N. Rao's Chara Dasha, event-based birth-time rectification, deterministic prediction synthesis (shadbala-weighted, varga-corroborated), pluggable interpretation providers (template / Ollama / Anthropic).

Validation: 128 unit tests, all passing (`backend/tests/`) — golden charts (Einstein/Vivekananda/Nehru/Bose from AA-rated birth data; Raman-ayanamsa degree-level checks), a Drik Panchang position capture matched to <2 arcmin, B.V. Raman's Standard Horoscope Shadbala pinned against PyJHora, and Amitabh Bachchan's Chara Dasha reproducing K.N. Rao's published sequence. Beyond the unit suite, an independent **bulk validation** against NASA JPL Horizons, the open vedastro 15k-people HuggingFace datasets, and the Astrodienst AstroDatabank C-sample lives in `backend/validation/` — see [VALIDATION.md](VALIDATION.md) for full methodology and results.
- `app/`, `components/`, `lib/` (repo root) — Next.js 14 (App Router, TS, Tailwind). Supabase auth, birth profiles + life events, South Indian SVG chart, varga selector, dasha timeline, prediction cards with substantiation, grounded chat. Runs without Supabase in local mode (localStorage).
- `supabase/schema.sql` — tables + row-level security.
- `ARCHITECTURE.md` — design decisions and API contract. `DEPLOYMENT.md` — hosting steps. `VALIDATION.md` — external validation methodology and results.

## Run locally
Backend (Python 3.11+ — pyswisseph needs a C compiler + Python headers, e.g. `apt install build-essential python3-dev`, or run inside the provided-pattern Docker image):
```bash
cd backend
pip install -r requirements.txt
AUTH_DISABLED=1 uvicorn app.main:app --port 8000
```
Frontend (Node 18+, run from the repo root — there is no `frontend/` subdirectory):
```bash
npm install
npm run dev           # http://localhost:3000 (local mode, no Supabase needed)
```
Tests: `cd backend && pytest` — 128 passing (all golden-case tests, including the 3 in `test_case_study.py`, run against real committed birth data in `tests/fixtures/case_study.json`). CI runs this on every push (`.github/workflows/backend-tests.yml`).

## Engine defaults (all configurable per request)
Lahiri (Chitrapaksha) ayanamsa (Raman / Krishnamurti / True Chitra selectable) · whole-sign houses · mean node · Vimshottari year = 365.25d (360d savana available) · Moshier ephemeris (no data files; drop `.se1` files in and it auto-upgrades to full Swiss Ephemeris) · birth times accept seconds (HH:MM:SS).

Live: https://kundali-five.vercel.app (Vercel: Next.js + Python function) · Supabase project `kundali` (auth + RLS).

## Licensing note
pyswisseph / Swiss Ephemeris are AGPLv3 (or Astrodienst commercial license). Fine for personal/open use; a closed-source SaaS would need the paid license.
