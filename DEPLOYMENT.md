# Deployment

Three services: Supabase (auth+DB), Render (Python API), Vercel (Next.js). All have free tiers.

## 1. Supabase
1. Create a project at supabase.com → SQL Editor → run `supabase/schema.sql`.
2. Note: Project URL, anon key (Settings → API).
3. New projects sign JWTs with ES256; the API verifies via JWKS — no secret sharing needed.

## 2. Backend → Render
1. Push this repo to GitHub.
2. Render → New → Blueprint (uses `backend/render.yaml`) or New Web Service → Docker, root `backend/`.
3. Env vars:
   - `SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/jwks`
   - `ALLOWED_ORIGINS=https://<your-app>.vercel.app`
   - (`AUTH_DISABLED=1` only for testing, never production)
4. Free tier sleeps after inactivity → first request ~30–60 s cold start. Upgrade or ping-keep-alive if that bothers you. Alternatives: Railway (usage-billed, nicer DX), Fly.io (cheap always-on).

## 3. Frontend → Vercel
1. Vercel → Import repo, root directory `frontend/`.
2. Env vars:
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `API_BASE_URL=https://<render-service>.onrender.com` (server-side; the app proxies via route handlers, so no CORS from the browser)
3. Deploy. Unset Supabase vars = local mode (no accounts, localStorage profiles).

## 4. Later: local LLM
Run Ollama beside the API (same private network on Render/Railway/Fly, or on your own machine) and set on the backend:
`INTERPRET_PROVIDER=ollama`, `OLLAMA_URL=http://<host>:11434`, `OLLAMA_MODEL=llama3.1` (or any). For hosted: `INTERPRET_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=...` (add `anthropic` to requirements). Default is the deterministic template provider — the app is fully functional with zero LLM.

## Upgrade ephemeris precision (optional)
Moshier mode is arcsecond-level. For full Swiss Ephemeris, download `sepl_18.se1` + `semo_18.se1` (~30 MB, astro.com) into `backend/ephe/` and set `SE_EPHE_PATH=/app/ephe` — the engine auto-detects.
