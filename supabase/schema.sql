-- ================================================================
-- Shelter Intake Triage — Supabase Schema (no-auth version)
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ================================================================

create extension if not exists "uuid-ossp";

-- ── Intakes ──────────────────────────────────────────────────────
create table public.intakes (
  id              uuid primary key default uuid_generate_v4(),
  intake_code     text not null unique,
  submitted_by    uuid not null,           -- fixed anonymous UUID, no FK

  species         text not null,
  estimated_age   text,
  breed           text,
  sex             text,
  intake_source   text not null,

  observed_behavior   text not null,
  medical_notes       text,
  additional_context  text,

  deleted_at      timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- ── Triage Reports ───────────────────────────────────────────────
create table public.triage_reports (
  id              uuid primary key default uuid_generate_v4(),
  intake_id       uuid not null unique references public.intakes(id) on delete cascade,

  urgency_tier        smallint not null check (urgency_tier in (1, 2, 3)),
  urgency_reason      text not null,
  placement_type      text not null,
  placement_icon      text,
  placement_description text not null,
  behavioral_flags    jsonb not null default '[]',
  medical_flags       jsonb not null default '[]',
  next_steps          jsonb not null default '[]',
  summary             text not null,

  model_used      text not null default 'llama3.1:8b',
  latency_ms      integer,
  created_at      timestamptz not null default now()
);

-- ── Indexes ──────────────────────────────────────────────────────
create index idx_intakes_created_at   on public.intakes(created_at desc);
create index idx_intakes_deleted_at   on public.intakes(deleted_at) where deleted_at is null;
create index idx_reports_urgency      on public.triage_reports(urgency_tier);

-- ── Updated-at trigger ───────────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger intakes_updated_at
  before update on public.intakes
  for each row execute procedure public.set_updated_at();

-- ── RLS: open read/write for service_role (backend uses service key)
-- No user-level auth — the backend is the only writer.
alter table public.intakes        enable row level security;
alter table public.triage_reports enable row level security;

-- Allow full access via service_role key (used by FastAPI backend)
create policy "intakes_service_all"
  on public.intakes for all
  using (true)
  with check (true);

create policy "reports_service_all"
  on public.triage_reports for all
  using (true)
  with check (true);
