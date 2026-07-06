# Kundali GB10 gateway

A thin, API-key-gated FastAPI process that sits in front of the local
Ollama install on this machine (GB10) and gives the Vercel-hosted backend
a stable, authenticated way to reach it. Vercel serverless functions can't
otherwise reach a box on this network, so a [Cloudflare
Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
gives this gateway a public HTTPS URL without opening any inbound port on
this machine.

Two trust paths share the same endpoint (`POST /api/chat`), matching the
tier-resolution logic in `backend/app/interpretation/gateway.py`:

- **`GB10_INTERNAL_SECRET`** — sent by the Vercel backend on behalf of
  `admin`/`guest` users (server-to-server trust, no per-user key check).
- **`GB10_PAID_SECRET`** — sent by the Vercel backend on behalf of `paid`
  tier users using a stored app-level credential (this is a **placeholder**
  until the real production secret is supplied — rotate it before relying
  on the `paid` tier for anything real).

This gateway does not know or care which tier is calling; the tier
decision already happened in the Vercel backend before either secret was
sent. It only checks "is this one of our two valid secrets" and proxies to
Ollama — this is not user-level auth, it's service-level auth for a
trusted backend-to-gateway hop.

## Why GB10 stays off-limits to heavy load right now

`nvidia-smi` shows this GPU already running another job at high
utilization. Until that clears, only modest models (`llama3.1:8b`,
`qwen2.5:14b` — never the 65-86GB models also pulled here) are on the
gateway's allow-list, and the public tunnel should stay **off** unless
you've confirmed headroom. See "Going live" below.

## Local setup

```bash
cd gb10-gateway
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export GB10_INTERNAL_SECRET="$(openssl rand -hex 32)"
export GB10_PAID_SECRET="$(openssl rand -hex 32)"          # placeholder until the real one lands
export GB10_ALLOWED_MODELS="llama3.1:8b,qwen2.5:14b"        # comma-separated allow-list
export OLLAMA_URL="http://localhost:11434"                  # default, only needed if Ollama is elsewhere

uvicorn main:app --host 127.0.0.1 --port 8100
```

Smoke test:

```bash
curl http://127.0.0.1:8100/healthz

curl -X POST http://127.0.0.1:8100/api/chat \
  -H "Authorization: Bearer $GB10_INTERNAL_SECRET" -H "Content-Type: application/json" \
  -d '{"model":"llama3.1:8b","stream":false,"messages":[{"role":"user","content":"say hi"}]}'
```

Run the test suite (mocks the Ollama call — no GPU load):

```bash
python -m pytest -q
```

## Running persistently (systemd, optional)

`kundali-gb10-gateway.service` is a template unit file. Copy it, fill in
the real secrets/paths, and enable it:

```bash
cp kundali-gb10-gateway.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now kundali-gb10-gateway
```

## Exposing it publicly (Cloudflare Tunnel)

**Quick tunnel (no Cloudflare account needed, ephemeral URL — good for a
one-off connectivity test):**

```bash
cloudflared tunnel --url http://127.0.0.1:8100
# prints a random https://<random>.trycloudflare.com URL, torn down when
# you Ctrl-C the process — do not point production traffic at this.
```

**Named tunnel on a `technektar.com` subdomain (stable URL, requires a
one-time interactive login to the Cloudflare account that owns the
`technektar.com` zone — this step needs a human with dashboard access, the
same kind of manual step as the earlier Vercel GitHub App permission
grant):**

```bash
cloudflared tunnel login                      # opens a browser, pick technektar.com
cloudflared tunnel create kundali-gb10        # writes a credentials file under ~/.cloudflared/
cloudflared tunnel route dns kundali-gb10 gb10.technektar.com
```

Then point `config.yml` (see the template in this directory) at the
gateway's local port and run:

```bash
cloudflared tunnel --config config.yml run kundali-gb10
```

## Going live (wiring Vercel to this gateway)

Once the tunnel is up and you've confirmed GB10 has headroom for
sustained/production load, set these on the Vercel project (Python
function environment — same place as `SUPABASE_URL` etc.):

| Env var               | Value                                              |
| ---------------------- | --------------------------------------------------- |
| `OLLAMA_GATEWAY_URL`   | `https://gb10.technektar.com` (or your tunnel URL)  |
| `GB10_INTERNAL_SECRET` | must match this gateway's `GB10_INTERNAL_SECRET`    |
| `GB10_PAID_SECRET`     | must match this gateway's `GB10_PAID_SECRET`        |
| `GB10_MODEL`           | e.g. `llama3.1:8b` — the model the backend requests |

Until these are set, `backend/app/interpretation/gateway.py::resolve_provider`
simply finds no `OLLAMA_GATEWAY_URL` and falls through to `ProviderBlocked`
for admin/guest/paid users with no BYOK key — the app fails safe (a clear
upgrade/BYOK prompt), not silently.
