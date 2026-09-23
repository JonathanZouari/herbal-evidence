-- Herbal Evidence — initial schema (Phase 1).
-- Access model (D-011): every write goes through the backend with the service-role key.
-- anon/authenticated get read-only RLS on their OWN rows only; drafts, reviews, sources,
-- jobs and audit rows have RLS enabled with NO policies (service role only).

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

-- ---------------------------------------------------------------- enums
create type public.app_role as enum ('user', 'researcher', 'admin');

create type public.request_status as enum (
  'submitted',              -- waiting for research to start
  'researching',            -- literature/AI job running
  'research_failed',        -- job exhausted retries; staff may retry or close
  'draft_ready',            -- AI draft waiting for a researcher
  'in_review',              -- researcher editing
  'awaiting_clarification', -- researcher asked the user a question
  'published',              -- approved response visible to the user
  'withdrawn',              -- user withdrew
  'closed'                  -- staff closed (e.g. out of scope)
);

create type public.job_status as enum ('queued', 'running', 'succeeded', 'dead');

-- ---------------------------------------------------------------- profiles
create table public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  role         public.app_role not null default 'user',
  display_name text check (char_length(display_name) <= 100),
  created_at   timestamptz not null default now()
);

-- New auth user -> profile with role 'user'. Role is never taken from user_metadata.
create function private.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id) values (new.id);
  return new;
end $$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function private.handle_new_user();

-- ---------------------------------------------------------------- herbs
create table public.herbs (
  id          bigint generated always as identity primary key,
  name_he     text not null,
  name_en     text not null,
  latin_name  text,
  aliases     text[] not null default '{}',   -- lower-case spellings used by herb identification
  created_at  timestamptz not null default now(),
  unique (name_en)
);

-- ---------------------------------------------------------------- requests
create table public.requests (
  id                     uuid primary key default gen_random_uuid(),
  user_id                uuid not null references auth.users (id) on delete cascade,
  herb_name_input        text not null check (char_length(btrim(herb_name_input)) between 1 and 200),
  herb_id                bigint references public.herbs (id),
  -- optional fields: NULL = "I don't know" / not provided
  preparation            text check (char_length(preparation) <= 500),
  cancer_type            text check (char_length(cancer_type) <= 200),
  treatment              text check (char_length(treatment) <= 500),
  status                 public.request_status not null default 'submitted',
  -- coarse status shown to the user; internal states never leak (no drafts, no failures, no queue info)
  public_status          text generated always as (
    case status
      when 'awaiting_clarification' then 'needs_clarification'
      when 'published' then 'published'
      when 'withdrawn' then 'withdrawn'
      when 'closed' then 'closed'
      else 'in_progress'
    end) stored,
  assigned_researcher_id uuid references auth.users (id) on delete set null,  -- D-005
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);
create index requests_user_id_idx on public.requests (user_id);
create index requests_status_idx on public.requests (status);
create index requests_assigned_idx on public.requests (assigned_researcher_id);
create index requests_herb_id_idx on public.requests (herb_id);

-- Allowed status transitions: the DB is the last guard; the backend state machine mirrors this table.
create table public.request_status_transitions (
  from_status public.request_status not null,
  to_status   public.request_status not null,
  primary key (from_status, to_status)
);
insert into public.request_status_transitions (from_status, to_status) values
  ('submitted', 'researching'), ('submitted', 'withdrawn'), ('submitted', 'closed'),
  ('researching', 'draft_ready'), ('researching', 'research_failed'), ('researching', 'withdrawn'),
  ('research_failed', 'researching'), ('research_failed', 'withdrawn'), ('research_failed', 'closed'),
  ('draft_ready', 'in_review'), ('draft_ready', 'withdrawn'), ('draft_ready', 'closed'),
  ('in_review', 'awaiting_clarification'), ('in_review', 'published'), ('in_review', 'researching'),
  ('in_review', 'withdrawn'), ('in_review', 'closed'),
  ('awaiting_clarification', 'in_review'), ('awaiting_clarification', 'withdrawn'),
  ('awaiting_clarification', 'closed'),
  ('published', 'withdrawn');

-- Audit trail of every status change (Phase 6 audit UI reads this).
create table public.request_events (
  id          bigint generated always as identity primary key,
  request_id  uuid not null references public.requests (id) on delete cascade,
  from_status public.request_status,
  to_status   public.request_status not null,
  actor_id    uuid,   -- auth.uid(), or the backend's `app.actor_id` setting when using the service role
  created_at  timestamptz not null default now()
);
create index request_events_request_id_idx on public.request_events (request_id);

create function private.guard_request_status() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'UPDATE' then
    new.updated_at := now();
    if new.status is distinct from old.status then
      if not exists (select 1 from public.request_status_transitions t
                     where t.from_status = old.status and t.to_status = new.status) then
        raise exception 'invalid request status transition % -> %', old.status, new.status
          using errcode = 'check_violation';
      end if;
    else
      return new;
    end if;
  elsif new.status <> 'submitted' then
    raise exception 'new requests must start as submitted' using errcode = 'check_violation';
  end if;

  insert into public.request_events (request_id, from_status, to_status, actor_id)
  values (new.id, case when tg_op = 'UPDATE' then old.status end, new.status,
          coalesce(auth.uid(), nullif(current_setting('app.actor_id', true), '')::uuid));
  return new;
end $$;

-- BEFORE for validation, but the event row needs the request to exist -> split insert/update.
create trigger requests_status_guard
  before update on public.requests
  for each row execute function private.guard_request_status();
create trigger requests_status_insert
  after insert on public.requests
  for each row execute function private.guard_request_status();

-- ---------------------------------------------------------------- clarifications
create table public.clarifications (
  id          bigint generated always as identity primary key,
  request_id  uuid not null references public.requests (id) on delete cascade,
  question    text not null check (char_length(question) <= 2000),
  asked_by    uuid references auth.users (id) on delete set null,
  asked_at    timestamptz not null default now(),
  answer      text check (char_length(answer) <= 2000),
  answered_at timestamptz
);
create index clarifications_request_id_idx on public.clarifications (request_id);

-- ---------------------------------------------------------------- literature + reviews (staff only)
create table public.literature_sources (
  id         bigint generated always as identity primary key,
  pmid       text unique,
  pmcid      text unique,
  doi        text unique,
  title      text not null,
  journal    text,
  pub_year   int,
  abstract   text,
  url        text,
  fetched_at timestamptz not null default now()
);

-- Reusable evidence review per herb; each personalized response still needs its own approval.
create table public.evidence_reviews (
  id          uuid primary key default gen_random_uuid(),
  herb_id     bigint not null references public.herbs (id),
  version     int not null default 1,
  content     jsonb not null,
  approved_by uuid references auth.users (id) on delete set null,
  approved_at timestamptz,
  created_at  timestamptz not null default now(),
  unique (herb_id, version)
);
create index evidence_reviews_approved_by_idx on public.evidence_reviews (approved_by);

create table public.review_sources (
  review_id uuid not null references public.evidence_reviews (id) on delete cascade,
  source_id bigint not null references public.literature_sources (id),
  primary key (review_id, source_id)
);
create index review_sources_source_id_idx on public.review_sources (source_id);

-- AI-assisted drafts: never visible to users.
create table public.response_drafts (
  id                 uuid primary key default gen_random_uuid(),
  request_id         uuid not null references public.requests (id) on delete cascade,
  evidence_review_id uuid references public.evidence_reviews (id),
  content            jsonb not null,
  ai_provider        text,
  ai_model           text,
  edited_by          uuid references auth.users (id) on delete set null,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);
create index response_drafts_request_id_idx on public.response_drafts (request_id);
create index response_drafts_review_idx on public.response_drafts (evidence_review_id);
create index response_drafts_edited_by_idx on public.response_drafts (edited_by);

-- Approved, published response: one per request, one researcher approval.
create table public.responses (
  id                 uuid primary key default gen_random_uuid(),
  request_id         uuid not null unique references public.requests (id) on delete cascade,
  evidence_review_id uuid references public.evidence_reviews (id),
  body               jsonb not null,
  approved_by        uuid not null references auth.users (id),
  published_at       timestamptz not null default now()
);
create index responses_review_idx on public.responses (evidence_review_id);
create index responses_approved_by_idx on public.responses (approved_by);

-- ---------------------------------------------------------------- job queue (D-010)
create table public.research_jobs (
  id               bigint generated always as identity primary key,
  kind             text not null,
  request_id       uuid references public.requests (id) on delete cascade,
  payload          jsonb not null default '{}',
  idempotency_key  text not null unique,
  status           public.job_status not null default 'queued',
  attempts         int not null default 0,
  max_attempts     int not null default 5 check (max_attempts > 0),
  run_after        timestamptz not null default now(),
  locked_by        text,
  lease_expires_at timestamptz,
  last_error       jsonb,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
create index research_jobs_ready_idx on public.research_jobs (run_after) where status = 'queued';
create index research_jobs_lease_idx on public.research_jobs (lease_expires_at) where status = 'running';
create index research_jobs_request_id_idx on public.research_jobs (request_id);

-- Claim one job: ready queued jobs, or running jobs whose lease expired (crash recovery).
-- A reclaimed job whose attempts are exhausted goes to 'dead' instead of running again.
create function public.claim_job(p_worker text, p_lease_seconds int default 60)
returns setof public.research_jobs
language plpgsql set search_path = '' as $$
declare j public.research_jobs;
begin
  loop
    select * into j from public.research_jobs
     where (status = 'queued' and run_after <= now())
        or (status = 'running' and lease_expires_at < now())
     order by run_after, id
     for update skip locked
     limit 1;
    if not found then return; end if;

    if j.attempts >= j.max_attempts then
      update public.research_jobs
         set status = 'dead', locked_by = null, lease_expires_at = null, updated_at = now(),
             last_error = coalesce(last_error, '{}'::jsonb) || '{"reason":"lease expired, attempts exhausted"}'
       where id = j.id;
      continue;
    end if;

    return query
      update public.research_jobs
         set status = 'running', attempts = attempts + 1, locked_by = p_worker,
             lease_expires_at = now() + make_interval(secs => p_lease_seconds), updated_at = now()
       where id = j.id
      returning *;
    return;
  end loop;
end $$;

create function public.heartbeat_job(p_job_id bigint, p_worker text, p_lease_seconds int default 60)
returns boolean language sql set search_path = '' as $$
  update public.research_jobs
     set lease_expires_at = now() + make_interval(secs => p_lease_seconds), updated_at = now()
   where id = p_job_id and status = 'running' and locked_by = p_worker
  returning true;
$$;

create function public.complete_job(p_job_id bigint, p_worker text)
returns boolean language sql set search_path = '' as $$
  update public.research_jobs
     set status = 'succeeded', locked_by = null, lease_expires_at = null, updated_at = now()
   where id = p_job_id and status = 'running' and locked_by = p_worker
  returning true;
$$;

-- Failure: retry with exponential backoff (30s * 2^attempts, capped at 1h) until max_attempts, then 'dead'.
-- p_retryable = false (e.g. "AI provider not configured") goes straight to 'dead'.
create function public.fail_job(p_job_id bigint, p_worker text, p_error jsonb, p_retryable boolean default true)
returns public.job_status language sql set search_path = '' as $$
  update public.research_jobs
     set status = case when p_retryable and attempts < max_attempts then 'queued'::public.job_status
                       else 'dead'::public.job_status end,
         run_after = now() + least(interval '1 hour', interval '30 seconds' * power(2, attempts)),
         last_error = p_error, locked_by = null, lease_expires_at = null, updated_at = now()
   where id = p_job_id and status = 'running' and locked_by = p_worker
  returning status;
$$;

revoke execute on function public.claim_job(text, int), public.heartbeat_job(bigint, text, int),
  public.complete_job(bigint, text), public.fail_job(bigint, text, jsonb, boolean)
  from public, anon, authenticated;
grant execute on function public.claim_job(text, int), public.heartbeat_job(bigint, text, int),
  public.complete_job(bigint, text), public.fail_job(bigint, text, jsonb, boolean)
  to service_role;

-- ---------------------------------------------------------------- RLS
alter table public.profiles                   enable row level security;
alter table public.herbs                      enable row level security;
alter table public.requests                   enable row level security;
alter table public.request_status_transitions enable row level security;
alter table public.request_events             enable row level security;
alter table public.clarifications             enable row level security;
alter table public.literature_sources         enable row level security;
alter table public.evidence_reviews           enable row level security;
alter table public.review_sources             enable row level security;
alter table public.response_drafts            enable row level security;
alter table public.responses                  enable row level security;
alter table public.research_jobs              enable row level security;

-- Clients are read-only: strip the default Supabase write grants, re-grant SELECT where a policy exists.
revoke all on all tables in schema public from anon, authenticated;

grant select on public.herbs to anon, authenticated;
create policy "herbs are public" on public.herbs for select to anon, authenticated using (true);

grant select on public.profiles to authenticated;
create policy "read own profile" on public.profiles for select to authenticated
  using (id = (select auth.uid()));

-- Column grant: users never see internal status or assignment.
grant select (id, herb_name_input, herb_id, preparation, cancer_type, treatment, public_status,
              created_at, updated_at) on public.requests to authenticated;
create policy "read own requests" on public.requests for select to authenticated
  using (user_id = (select auth.uid()));

grant select (id, request_id, question, asked_at, answer, answered_at) on public.clarifications to authenticated;
create policy "read own clarifications" on public.clarifications for select to authenticated
  using (exists (select 1 from public.requests r
                 where r.id = request_id and r.user_id = (select auth.uid())));

grant select (id, request_id, body, published_at) on public.responses to authenticated;
create policy "read own responses" on public.responses for select to authenticated
  using (exists (select 1 from public.requests r
                 where r.id = request_id and r.user_id = (select auth.uid())
                   and r.status = 'published'));

-- Future tables must opt in explicitly.
alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke execute on functions from public, anon, authenticated;

-- ---------------------------------------------------------------- storage
-- Private bucket for staff artifacts (exports, source files). No storage policies = service role only.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('research-artifacts', 'research-artifacts', false, 20971520,
        array['application/pdf', 'text/plain', 'application/json', 'text/csv']);
