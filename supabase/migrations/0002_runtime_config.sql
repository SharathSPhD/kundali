-- Non-secret deployment configuration readable by any client role.
-- Written only via service role / migrations (no anon/authenticated write
-- policies). This is how the Vercel backend discovers the GB10 Ollama
-- gateway without anyone setting dashboard env vars: the GB10 box (or an
-- operator) upserts `ollama_gateway_url` / `gb10_default_model` here and
-- `backend/app/interpretation/gateway.py::_runtime_config` picks it up.
create table if not exists public.runtime_config (
  key text primary key,
  value text not null,
  updated_at timestamptz not null default now()
);

alter table public.runtime_config enable row level security;

drop policy if exists "runtime_config is readable by everyone" on public.runtime_config;
create policy "runtime_config is readable by everyone"
  on public.runtime_config for select
  to anon, authenticated
  using (true);
