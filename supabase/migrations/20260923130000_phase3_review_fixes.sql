-- Phase 3 review fixes.
--  * a job can die before the worker moved its request out of `submitted` -> allow submitted -> research_failed
--    and fail requests in either state when their job dies (no request stuck in `submitted` forever)
--  * one reusable review per published response
--  * DOIs are stored lower-case, so the unique index doubles as the lookup index

insert into public.request_status_transitions (from_status, to_status) values ('submitted', 'research_failed')
on conflict do nothing;

create or replace function public.claim_job(p_worker text, p_lease_seconds int default 60, p_request_id uuid default null)
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
       where id = j.request_id and status in ('submitted', 'researching');
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

create or replace function public.fail_job(p_job_id bigint, p_worker text, p_error jsonb, p_retryable boolean default true)
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
    update public.requests set status = 'research_failed'
     where id = rid and status in ('submitted', 'researching');
  end if;
  return s;
end $$;

-- `create or replace` keeps existing grants; re-state them for clarity.
revoke execute on function public.claim_job(text, int, uuid), public.fail_job(bigint, text, jsonb, boolean)
  from public, anon, authenticated;
grant execute on function public.claim_job(text, int, uuid), public.fail_job(bigint, text, jsonb, boolean)
  to service_role;

drop index public.evidence_reviews_source_response_idx;
create unique index evidence_reviews_source_response_key on public.evidence_reviews (source_response_id)
  where source_response_id is not null;

update public.literature_sources set doi = lower(doi) where doi <> lower(doi);
alter table public.literature_sources add constraint literature_sources_doi_lower check (doi = lower(doi));
