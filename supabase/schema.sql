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
