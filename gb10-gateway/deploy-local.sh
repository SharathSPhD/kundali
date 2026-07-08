#!/usr/bin/env bash
# Install (or update) the GB10 gateway as a systemd user service on this
# machine and expose it publicly via Tailscale Funnel on port 8443.
#
# Idempotent: re-run after changing main.py to redeploy. Secrets are
# generated once and kept in ~/.local/share/kundali-gb10-gateway/gateway.env.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$HOME/.local/share/kundali-gb10-gateway"
ENV_FILE="$RUN_DIR/gateway.env"
UNIT_DIR="$HOME/.config/systemd/user"

mkdir -p "$RUN_DIR" "$UNIT_DIR"
cp "$SRC_DIR/main.py" "$SRC_DIR/requirements.txt" "$RUN_DIR/"
# deploy_config.json gives main.py its zero-config Supabase URL fallback.
if [ -f "$SRC_DIR/../deploy_config.json" ]; then
  cp "$SRC_DIR/../deploy_config.json" "$RUN_DIR/../deploy_config.json" 2>/dev/null || true
fi

if [ ! -d "$RUN_DIR/.venv" ]; then
  python3 -m venv "$RUN_DIR/.venv"
fi
"$RUN_DIR/.venv/bin/pip" install -q -r "$RUN_DIR/requirements.txt"

if [ ! -f "$ENV_FILE" ]; then
  {
    echo "GB10_INTERNAL_SECRET=$(openssl rand -hex 32)"
    echo "GB10_PAID_SECRET=$(openssl rand -hex 32)"
  } > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi

# Non-secret settings are rewritten on every deploy (idempotent).
grep -v -E '^(OLLAMA_URL|GB10_ALLOWED_MODELS|GB10_ALLOWED_TIERS|SUPABASE_URL|SUPABASE_ANON_KEY)=' "$ENV_FILE" > "$ENV_FILE.tmp" || true
{
  cat "$ENV_FILE.tmp"
  echo "OLLAMA_URL=http://localhost:11434"
  echo "GB10_ALLOWED_MODELS=${GB10_ALLOWED_MODELS:-qwen2.5:14b,llama3.1:8b,gemma2:9b,qwen2.5:7b}"
  echo "GB10_ALLOWED_TIERS=admin,guest,paid"
  echo "SUPABASE_URL=${SUPABASE_URL:-https://mcnknhbtipvclirawhxw.supabase.co}"
  echo "SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY:-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1jbmtuaGJ0aXB2Y2xpcmF3aHh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMwOTkzNDUsImV4cCI6MjA5ODY3NTM0NX0.mnkJTXA6zXWIB70DXb8vpLO4SdBDs2soxrKLlcDA1fo}"
} > "$ENV_FILE.new"
mv "$ENV_FILE.new" "$ENV_FILE"
rm -f "$ENV_FILE.tmp"
chmod 600 "$ENV_FILE"

cp "$SRC_DIR/kundali-gb10-gateway.service" "$UNIT_DIR/"
systemctl --user daemon-reload
systemctl --user enable --now kundali-gb10-gateway
systemctl --user restart kundali-gb10-gateway

# Public HTTPS ingress: Tailscale Funnel on :8443 (stable URL, no account
# interaction needed once funnel is enabled on the tailnet). Kept as a
# separate opt-in step so installing the local service never implicitly
# exposes anything.
if [ "${EXPOSE_FUNNEL:-0}" = "1" ]; then
  tailscale funnel --bg --https=8443 8100 >/dev/null
else
  if ! tailscale funnel status 2>/dev/null | grep -q ':8443'; then
    echo "NOTE: gateway is local-only. Expose it with: tailscale funnel --bg --https=8443 8100"
  fi
fi

sleep 2
echo "--- healthz (local) ---"
curl -sf http://127.0.0.1:8100/healthz && echo
echo "--- funnel status ---"
tailscale funnel status | sed -n '1,12p'
echo "Gateway public URL: https://$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))'):8443"
