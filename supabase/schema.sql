-- Kundali — Supabase schema (see ARCHITECTURE.md)
-- Run in the Supabase SQL editor (or `supabase db push`).
-- RLS: owner-only via auth.uid() = user_id; child tables via join to
-- birth_profiles.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- birth_profiles
-- ---------------------------------------------------------------------------
create table if not exists public.birth_profiles (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references auth.users (id) on delete cascade,
  label          text not null,
  birth_date     date not null,
  birth_time     time not null,
  tz_offset      numeric(4, 2) not null default 0
                 check (tz_offset >= -12 and tz_offset <= 14),
  place_name     text not null default '',
  lat            double precision not null
                 check (lat >= -90 and lat <= 90),
  lon            double precision not null
                 check (lon >= -180 and lon <= 180),
  rectified_time time,
  is_self        boolean not null default false,
  created_at     timestamptz not null default now()
);

create index if not exists birth_profiles_user_id_idx
  on public.birth_profiles (user_id);

alter table public.birth_profiles enable row level security;

drop policy if exists "birth_profiles owner select" on public.birth_profiles;
create policy "birth_profiles owner select"
  on public.birth_profiles for select
  using (auth.uid() = user_id);

drop policy if exists "birth_profiles owner insert" on public.birth_profiles;
create policy "birth_profiles owner insert"
  on public.birth_profiles for insert
  with check (auth.uid() = user_id);

drop policy if exists "birth_profiles owner update" on public.birth_profiles;
create policy "birth_profiles owner update"
  on public.birth_profiles for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "birth_profiles owner delete" on public.birth_profiles;
create policy "birth_profiles owner delete"
  on public.birth_profiles for delete
  using (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- life_events (child of birth_profiles)
-- ---------------------------------------------------------------------------
create table if not exists public.life_events (
  id          uuid primary key default gen_random_uuid(),
  profile_id  uuid not null references public.birth_profiles (id) on delete cascade,
  event_type  text not null check (event_type in (
    'marriage', 'child_birth', 'career_start', 'promotion',
    'relocation', 'parent_death', 'health_event', 'other'
  )),
  event_date  date not null,
  note        text
);

create index if not exists life_events_profile_id_idx
  on public.life_events (profile_id);

alter table public.life_events enable row level security;

drop policy if exists "life_events owner all" on public.life_events;
create policy "life_events owner all"
  on public.life_events for all
  using (
    exists (
      select 1 from public.birth_profiles bp
      where bp.id = life_events.profile_id
        and bp.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.birth_profiles bp
      where bp.id = life_events.profile_id
        and bp.user_id = auth.uid()
    )
  );

-- ---------------------------------------------------------------------------
-- readings (cached engine output per profile)
-- ---------------------------------------------------------------------------
create table if not exists public.readings (
  id          uuid primary key default gen_random_uuid(),
  profile_id  uuid not null references public.birth_profiles (id) on delete cascade,
  kind        text not null,           -- e.g. 'chart', 'vargas', 'dashas', 'predictions'
  payload     jsonb not null,
  created_at  timestamptz not null default now()
);

create index if not exists readings_profile_kind_idx
  on public.readings (profile_id, kind, created_at desc);

alter table public.readings enable row level security;

drop policy if exists "readings owner all" on public.readings;
create policy "readings owner all"
  on public.readings for all
  using (
    exists (
      select 1 from public.birth_profiles bp
      where bp.id = readings.profile_id
        and bp.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.birth_profiles bp
      where bp.id = readings.profile_id
        and bp.user_id = auth.uid()
    )
  );

-- ---------------------------------------------------------------------------
-- chat_messages (grounded interpretation transcript per profile)
-- ---------------------------------------------------------------------------
create table if not exists public.chat_messages (
  id          uuid primary key default gen_random_uuid(),
  profile_id  uuid not null references public.birth_profiles (id) on delete cascade,
  role        text not null check (role in ('user', 'assistant')),
  content     text not null,
  grounding   jsonb,                   -- citations back to engine facts
  created_at  timestamptz not null default now()
);

create index if not exists chat_messages_profile_created_idx
  on public.chat_messages (profile_id, created_at);

alter table public.chat_messages enable row level security;

drop policy if exists "chat_messages owner all" on public.chat_messages;
create policy "chat_messages owner all"
  on public.chat_messages for all
  using (
    exists (
      select 1 from public.birth_profiles bp
      where bp.id = chat_messages.profile_id
        and bp.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.birth_profiles bp
      where bp.id = chat_messages.profile_id
        and bp.user_id = auth.uid()
    )
  );

-- ---------------------------------------------------------------------------
-- user_tiers — account tier (admin/guest/paid/basic) per user.
-- basic: default, no inference without BYOK. paid: GB10 gateway via stored
-- app secret (no BYOK needed). guest: added by an admin, same access as
-- admin. admin: unrestricted, seeded for the app owner.
-- ---------------------------------------------------------------------------
do $$ begin
  create type public.account_tier as enum ('basic', 'paid', 'guest', 'admin');
exception
  when duplicate_object then null;
end $$;

create table if not exists public.user_tiers (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  tier       public.account_tier not null default 'basic',
  -- `on delete set null`, not cascade/restrict: deleting the admin who
  -- granted a tier must not block deleting them, nor delete the grantee's
  -- row.
  added_by   uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.user_tiers enable row level security;

-- security-definer helper avoids the self-referential-RLS-recursion problem
-- that would occur if the "is caller an admin" check were itself a normal
-- (RLS-checked) query against user_tiers.
create or replace function public.is_admin(uid uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1 from public.user_tiers where user_id = uid and tier = 'admin'
  );
$$;

drop policy if exists "user_tiers owner select" on public.user_tiers;
create policy "user_tiers owner select"
  on public.user_tiers for select
  using (auth.uid() = user_id);

drop policy if exists "user_tiers admin all" on public.user_tiers;
create policy "user_tiers admin all"
  on public.user_tiers for all
  using (public.is_admin(auth.uid()))
  with check (public.is_admin(auth.uid()));

-- New signups default to 'basic' automatically.
create or replace function public.handle_new_user_tier()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.user_tiers (user_id, tier) values (new.id, 'basic')
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_tier on auth.users;
create trigger on_auth_user_created_tier
  after insert on auth.users
  for each row execute function public.handle_new_user_tier();

-- Backfill any users created before this migration existed.
insert into public.user_tiers (user_id, tier)
select id, 'basic' from auth.users
on conflict (user_id) do nothing;

-- ---------------------------------------------------------------------------
-- user_llm_credentials — BYOK provider keys. Strictly owner-only: even
-- admins cannot read another user's stored API key through RLS (unlike
-- user_tiers, there is deliberately no admin-all policy here).
-- ---------------------------------------------------------------------------
create table if not exists public.user_llm_credentials (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  provider   text not null check (provider in ('anthropic', 'openai', 'gemini', 'ollama')),
  api_key    text,
  base_url   text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, provider)
);

create index if not exists user_llm_credentials_user_id_idx
  on public.user_llm_credentials (user_id);

alter table public.user_llm_credentials enable row level security;

drop policy if exists "user_llm_credentials owner all" on public.user_llm_credentials;
create policy "user_llm_credentials owner all"
  on public.user_llm_credentials for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- Admin RPCs — `auth.users` isn't exposed over PostgREST, so "look up a
-- user by email" and "set their tier" for the admin UI go through these
-- security-definer functions instead. Both self-check `is_admin(auth.uid())`
-- so a non-admin calling them directly gets a clean error, not just an RLS
-- no-op.
-- ---------------------------------------------------------------------------
create or replace function public.admin_lookup_tier_by_email(target_email text)
returns table (user_id uuid, email text, tier public.account_tier)
language plpgsql
security definer
set search_path = public, auth
as $$
begin
  if not public.is_admin(auth.uid()) then
    raise exception 'not authorized';
  end if;
  return query
    select u.id, u.email::text, coalesce(t.tier, 'basic'::public.account_tier)
    from auth.users u
    left join public.user_tiers t on t.user_id = u.id
    where u.email = target_email;
end;
$$;

grant execute on function public.admin_lookup_tier_by_email(text) to authenticated;

create or replace function public.admin_set_tier_by_email(target_email text, new_tier public.account_tier)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  target_id uuid;
begin
  if not public.is_admin(auth.uid()) then
    raise exception 'not authorized';
  end if;
  select id into target_id from auth.users where email = target_email;
  if target_id is null then
    raise exception 'no user found with that email';
  end if;
  insert into public.user_tiers (user_id, tier, added_by)
  values (target_id, new_tier, auth.uid())
  on conflict (user_id) do update
    set tier = excluded.tier, added_by = excluded.added_by, updated_at = now();
end;
$$;

grant execute on function public.admin_set_tier_by_email(text, public.account_tier) to authenticated;
