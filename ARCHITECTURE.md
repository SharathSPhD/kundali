# Kundali — Vedic Astrology (South Indian) Full-Stack App

## Goal
A rigorous, deterministic jyotisha engine first; LLM narration second (grounded strictly in engine output). User-focused: auth, saved birth profiles, on-demand predictions, extensible chat.

## Stack & Hosting
| Layer | Tech | Hosting |
|---|---|---|
| Frontend | Next.js 14 (App Router, TS, Tailwind) | Vercel |
| Auth + DB | Supabase (Postgres, RLS, @supabase/ssr) | Supabase cloud (free tier) |
| Calc engine + API | Python 3.11, FastAPI, pyswisseph | Render (free, Docker); Railway/Fly alternatives |
| LLM (later) | Provider interface: Ollama (local) / Anthropic API | co-located service |

**Licensing note:** pyswisseph/Swiss Ephemeris is AGPLv3 (or paid commercial license). Fine for a personal/open project; if closed-source SaaS later, buy the Astrodienst license.

## Repo layout (monorepo)
```
kundali/
  backend/
    app/
      main.py            # FastAPI app, CORS, routers
      auth.py            # Supabase JWT verify (JWKS ES256, HS256 fallback)
      schemas.py         # Pydantic request/response models
      routers/           # charts, dashas, transits, predictions, interpret
      engine/            # THE deterministic core (pure functions, no I/O)
        constants.py     # signs, planets, nakshatras, dignities, friendships
        ephemeris.py     # swisseph wrapper; EngineConfig(ayanamsa, node_type, dasha_year)
        chart.py         # natal chart, whole-sign houses, lagna, dignity, combustion, retro
        vargas.py        # all 16 shodasha vargas (BPHS rules)
        dashas.py        # Vimshottari maha→antar→pratyantar (recursive; year length configurable)
        transits.py      # gochara from Moon (3-6-11 / 5-7-9-11), Sade Sati, double transit on a house
        yogas.py         # rule evaluator over yoga_rules.py data (~30 yogas)
        ashtakavarga.py  # BAV (337-point tables) + SAV
        rectification.py # event-based birth-time scan (dasha-lord relevance scoring)
        predictions.py   # deterministic synthesis: active dasha lords × transits × natal promise → scored indications per life area
      interpretation/
        base.py          # InterpretationProvider ABC; strict grounding contract
        template_provider.py  # deterministic text (default, no LLM)
        ollama_provider.py    # local LLM
        anthropic_provider.py # hosted LLM
    tests/               # pytest; golden case study + convention checks
    Dockerfile, requirements.txt, render.yaml
  app/                   # Next.js 14 (App Router); proxies API via /api/py/* rewrites (no CORS)
    dashboard/ (profiles, chart/[id], ask/[id], predictions, chat, rectify)
    lib/ (supabase clients, api client, chart geometry)
    components/ (SouthIndianChart SVG, DashaTree, ProfileForm, …)
  supabase/schema.sql    # tables + RLS
  DEPLOYMENT.md, README.md
```

## Engine conventions (defaults, all configurable via EngineConfig)
- **Ayanamsa:** Lahiri (`swe.SIDM_LAHIRI`) — matches Drik Panchang / Indian govt ephemeris.
- **Houses:** whole-sign from sidereal lagna. (Placidus from old code dropped.)
- **Nodes:** mean node default (classical); true node option.
- **Ephemeris:** `FLG_MOSEPH` (Moshier, no data files, ≤ arcsec-level error) by default; auto-upgrades to `FLG_SWIEPH` if .se1 files present.
- **Vimshottari year:** 365.25 days default (matches consumer tools); 360-day savana option. Balance from Moon's nakshatra fraction; sub-periods recursive proportional (lord_years/120), sequence starts at parent lord.
- **Vargas:** BPHS standard mappings; D2 classical Parashari hora; D30 asymmetric rule.
- **Transits:** Moon-reference rashi rules, Sade Sati (12/1/2 from Moon with phases), Ashtama/Kantaka Shani, Jupiter-Saturn double-transit detection per house.
- **Ashtakavarga:** classical Parashari tables (Sun48/Moon49/Mars39/Merc54/Jup56/Ven52/Sat39 = 337); SAV excl. lagna BAV.

## API contract (FastAPI, all POST unless noted)
```
GET  /health
POST /api/chart        {birth: {date,time,lat,lon,tz_offset}, config?} → positions, lagna, houses, nakshatras, dignities
POST /api/vargas       {birth, charts?: ["D9","D10",...]} → varga placements
POST /api/dashas       {birth, levels?: 3, from?, to?} → nested dasha tree + currently active path
POST /api/transits     {birth, on?: date} → gochara table, sade_sati, double_transit
POST /api/yogas        {birth} → [{name, present, factors, strength}]
POST /api/ashtakavarga {birth} → BAV per planet + SAV
POST /api/predictions  {birth, on?: date} → deterministic scored indications per area (career/wealth/health/relationships/family/education) with substantiation trail
POST /api/rectify      {birth, window_minutes, events: [{type, date}]} → ranked candidate times
POST /api/interpret    {birth, question?, provider?} → narrated reading grounded ONLY in engine JSON (template provider default)
```
Auth: `Authorization: Bearer <supabase JWT>`; verified via project JWKS (cached), `aud=authenticated`.

## Database (Supabase, RLS: owner-only)
```sql
birth_profiles(id, user_id → auth.users, label, birth_date, birth_time, tz_offset,
               place_name, lat, lon, rectified_time, is_self, created_at)
life_events(id, profile_id, event_type, event_date, note)
readings(id, profile_id, kind, payload jsonb, created_at)   -- cached engine output
chat_messages(id, profile_id, role, content, grounding jsonb, created_at)

-- account tiers + BYOK (see "LLM access tiers" below)
user_tiers(user_id → auth.users, tier enum[basic|paid|guest|admin], added_by, created_at, updated_at)
user_llm_credentials(id, user_id → auth.users, provider enum[anthropic|openai|gemini|ollama],
                      api_key, base_url, created_at, updated_at)  -- unique(user_id, provider)
```
`user_tiers` gets a default `basic` row via an `on auth.users insert` trigger. Admin tier
changes for *other* users go through `security definer` RPCs (`admin_lookup_tier_by_email`,
`admin_set_tier_by_email`) that self-check the caller's own tier — this sidesteps the
self-referential-RLS-recursion problem of a normal admin-all policy needing to read the very
table its own policy is protecting.

## LLM access tiers + BYOK
Four tiers, resolved per-request by `backend/app/interpretation/gateway.py::resolve_provider()`
(never inside the MCP server — see the plugin section):
1. **BYOK** (any tier): a `user_llm_credentials` row exists for the requested/any provider → use it directly.
2. **admin / guest** (no BYOK needed): routed to the GB10-hosted Ollama gateway with a trusted server-to-server secret (`GB10_INTERNAL_SECRET`).
3. **paid** (no BYOK needed): routed to the same GB10 gateway with a stored app-level secret (`GB10_PAID_SECRET`).
4. **basic**, no BYOK: blocked — the resolver raises `ProviderBlocked` with an upgrade/BYOK hint rather than silently answering.

The resolver fetches the caller's *own* tier/credentials by forwarding their bearer token to
Supabase REST — RLS naturally scopes results to that user, so no service-role key is needed here.

## LLM grounding contract
Providers receive: engine JSON + user question (+ optional multi-turn `history`). Prompt forbids inventing positions/dates; every claim must cite an element of the payload (dasha period, transit, yoga, shadbala, jaimini). The deterministic `template_provider` is default so the app is fully functional with zero LLM.

## Deployment
1. Supabase project → run `supabase/schema.sql`; copy URL + anon key.
2. Backend → Render (Docker) with `SUPABASE_URL`, `SUPABASE_JWKS_URL`; or `docker compose up` locally.
3. Frontend → Vercel; env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `API_BASE_URL` (server-side only; route handlers proxy).

## Validation strategy
- Convention tests: sidereal positions vs independently published values; ayanamsa sanity; nakshatra boundaries.
- Golden case study (user's chart): Taurus lagna ~15° (Rohini), Moon in Sagittarius (8th), Moon–Venus antardasha ⊇ 2009-06-18, Mars–Mercury ⊇ 2014-06-07, Rahu–Mercury active mid-2026. Exact birth data to be supplied.
- Structural tests: dasha tree sums to 120y, varga math per BPHS worked examples, BAV row totals (48/49/39/54/56/52/39), yoga rule unit tests.
```
