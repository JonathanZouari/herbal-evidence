-- Phase 3: research worker support.
--  * drafts remember the job that produced them + internal metadata (queries, counts, AI flags)
--  * request_sources: literature gathered for a request (kept even if the AI step fails)
--  * evidence_reviews remember the published response they were saved from
--  * a job that dies (claim-side exhaustion or fail_job) moves its request researching -> research_failed
--  * claim_job never claims MOCK seed jobs and can be scoped to one request (tests on the shared dev DB)

-- ---------------------------------------------------------------- drafts
alter table public.response_drafts
  add column job_id bigint references public.research_jobs (id) on delete set null,
  add column meta   jsonb not null default '{}';
create unique index response_drafts_job_id_key on public.response_drafts (job_id) where job_id is not null;

-- ---------------------------------------------------------------- sources per request (staff only, D-011)
create table public.request_sources (
  request_id uuid not null references public.requests (id) on delete cascade,
  source_id  bigint not null references public.literature_sources (id),
  job_id     bigint references public.research_jobs (id) on delete set null,
  origin     text not null check (origin in ('pubmed', 'europepmc', 'review')),
  rank       int,
  added_at   timestamptz not null default now(),
  primary key (request_id, source_id)
);
create index request_sources_source_id_idx on public.request_sources (source_id);
create index request_sources_job_id_idx on public.request_sources (job_id);
alter table public.request_sources enable row level security;   -- no policies: backend only

-- ---------------------------------------------------------------- review provenance
alter table public.evidence_reviews
  add column source_response_id uuid references public.responses (id) on delete set null;
create index evidence_reviews_source_response_idx on public.evidence_reviews (source_response_id);

-- ---------------------------------------------------------------- dead job -> request research_failed
-- (inlined in both functions: callers such as service_role have no USAGE on schema private)

drop function public.claim_job(text, int);
create function public.claim_job(p_worker text, p_lease_seconds int default 60, p_request_id uuid default null)
returns setof public.research_jobs
language plpgsql set search_path = '' as $$
declare j public.research_jobs;
begin
  loop
    select * into j from public.research_jobs
     where ((status = 'queued' and run_after <= now())
         or (status = 'running' and lease_expires_at < now()))
       and coalesce(payload ->> 'mock', 'false') <> 'true'
       and (p_request_id is null or request_id = p_request_id)
     order by run_after, id
     for update skip locked
     limit 1;
    if not found then return; end if;

    if j.attempts >= j.max_attempts then
      update public.research_jobs
         set status = 'dead', locked_by = null, lease_expires_at = null, updated_at = now(),
             last_error = coalesce(last_error, '{}'::jsonb) || '{"code":"lease_expired_exhausted"}'
       where id = j.id;
      update public.requests set status = 'research_failed'
       where id = j.request_id and status = 'researching';
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

drop function public.fail_job(bigint, text, jsonb, boolean);
create function public.fail_job(p_job_id bigint, p_worker text, p_error jsonb, p_retryable boolean default true)
returns public.job_status
language plpgsql set search_path = '' as $$
declare s public.job_status; rid uuid;
begin
  update public.research_jobs
     set status = case when p_retryable and attempts < max_attempts then 'queued'::public.job_status
                       else 'dead'::public.job_status end,
         run_after = now() + least(interval '1 hour', interval '30 seconds' * power(2, attempts)),
         last_error = p_error, locked_by = null, lease_expires_at = null, updated_at = now()
   where id = p_job_id and status = 'running' and locked_by = p_worker
  returning status, request_id into s, rid;
  if s = 'dead' then
    update public.requests set status = 'research_failed' where id = rid and status = 'researching';
  end if;
  return s;
end $$;

revoke execute on function public.claim_job(text, int, uuid), public.fail_job(bigint, text, jsonb, boolean)
  from public, anon, authenticated;
grant execute on function public.claim_job(text, int, uuid), public.fail_job(bigint, text, jsonb, boolean)
  to service_role;
