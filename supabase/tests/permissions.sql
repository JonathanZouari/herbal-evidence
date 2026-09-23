-- Permission + invariant tests. Runs in one transaction and ROLLS BACK: safe against the dev project.
--   supabase db query --linked -f supabase/tests/permissions.sql
-- Any failed assertion raises and aborts; success ends with the row `all_tests_passed`.
begin;

-- expect_error(sql): the statement must fail.
create function pg_temp.expect_error(p_sql text, p_label text) returns void language plpgsql as $$
begin
  execute p_sql;
  raise exception 'FAIL: expected error: %', p_label;
exception when others then
  if sqlerrm like 'FAIL:%' then raise; end if;
end $$;

create function pg_temp.check(p_ok boolean, p_label text) returns void language plpgsql as $$
begin
  if p_ok is not true then raise exception 'FAIL: %', p_label; end if;
end $$;

grant execute on function pg_temp.expect_error(text, text), pg_temp.check(boolean, text) to anon, authenticated;

-- ---------------------------------------------------------------- fixtures (as owner)
insert into auth.users (id, email) values
  ('00000000-0000-4000-a000-00000000000a', 'test-a@example.invalid'),
  ('00000000-0000-4000-a000-00000000000b', 'test-b@example.invalid'),
  ('00000000-0000-4000-a000-0000000000cc', 'test-researcher@example.invalid');

select pg_temp.check((select count(*) = 3 from public.profiles where id::text like '00000000-0000-4000-a000-%'
                      and role = 'user'), 'signup trigger creates profile with role user');
update public.profiles set role = 'researcher' where id = '00000000-0000-4000-a000-0000000000cc';

insert into public.herbs (name_he, name_en) values ('צמח בדיקה', 'Test Herb');
insert into public.requests (id, user_id, herb_name_input) values
  ('10000000-0000-4000-a000-00000000000a', '00000000-0000-4000-a000-00000000000a', 'ginger'),
  ('10000000-0000-4000-a000-00000000000b', '00000000-0000-4000-a000-00000000000b', 'ginseng');

select pg_temp.check((select count(*) = 1 from public.request_events
                      where request_id = '10000000-0000-4000-a000-00000000000a' and from_status is null
                        and to_status = 'submitted'), 'insert logs submitted event');

-- state machine
select pg_temp.expect_error($$insert into public.requests (user_id, herb_name_input, status)
  values ('00000000-0000-4000-a000-00000000000a', 'x', 'published')$$, 'insert must start as submitted');
select pg_temp.expect_error($$update public.requests set status = 'published'
  where id = '10000000-0000-4000-a000-00000000000a'$$, 'submitted -> published is invalid');
select pg_temp.expect_error($$insert into public.requests (user_id, herb_name_input)
  values ('00000000-0000-4000-a000-00000000000a', '   ')$$, 'blank herb name rejected');

select set_config('app.actor_id', '00000000-0000-4000-a000-0000000000cc', true);
update public.requests set status = 'researching' where id = '10000000-0000-4000-a000-00000000000a';
update public.requests set status = 'draft_ready' where id = '10000000-0000-4000-a000-00000000000a';
select pg_temp.check((select actor_id = '00000000-0000-4000-a000-0000000000cc' from public.request_events
                      where request_id = '10000000-0000-4000-a000-00000000000a' and to_status = 'draft_ready'),
                     'event records backend actor');

insert into public.response_drafts (request_id, content) values ('10000000-0000-4000-a000-00000000000a', '{"d":1}');
insert into public.clarifications (request_id, question) values ('10000000-0000-4000-a000-00000000000a', 'q?');
insert into public.clarifications (request_id, question) values ('10000000-0000-4000-a000-00000000000b', 'q-b?');
insert into public.responses (request_id, body, approved_by)
  values ('10000000-0000-4000-a000-00000000000a', '{"r":1}', '00000000-0000-4000-a000-0000000000cc');

-- ---------------------------------------------------------------- user A
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-4000-a000-00000000000a","role":"authenticated"}', true);

select pg_temp.check((select count(*) = 1 from public.profiles), 'user sees only own profile');
select pg_temp.check((select array_agg(id) = array['10000000-0000-4000-a000-00000000000a'::uuid]
                      from (select id from public.requests) s), 'user sees only own request');
select pg_temp.check((select public_status = 'in_progress' from public.requests), 'draft_ready shows as in_progress');
select pg_temp.expect_error('select status from public.requests', 'internal status column hidden');
select pg_temp.expect_error('select assigned_researcher_id from public.requests', 'assignment column hidden');
select pg_temp.check((select count(*) = 1 from public.clarifications), 'user sees only own clarification');
select pg_temp.check((select count(*) = 0 from public.responses), 'response hidden until published');
select pg_temp.check((select count(*) >= 1 from public.herbs), 'herbs readable');

select pg_temp.expect_error($$insert into public.requests (user_id, herb_name_input)
  values ('00000000-0000-4000-a000-00000000000a', 'x')$$, 'user cannot insert requests directly');
select pg_temp.expect_error($$update public.requests set herb_name_input = 'x'$$, 'user cannot update requests');
select pg_temp.expect_error($$delete from public.requests$$, 'user cannot delete requests');
select pg_temp.expect_error($$update public.profiles set role = 'admin'$$, 'user cannot change own role');
select pg_temp.expect_error($$update public.clarifications set answer = 'a'$$, 'user answers go through backend');
select pg_temp.expect_error('select * from public.response_drafts', 'drafts hidden');
select pg_temp.expect_error('select * from public.evidence_reviews', 'reviews hidden');
select pg_temp.expect_error('select * from public.literature_sources', 'sources hidden');
select pg_temp.expect_error('select * from public.research_jobs', 'jobs hidden');
select pg_temp.expect_error('select * from public.request_events', 'audit hidden');
select pg_temp.expect_error($$select public.claim_job('evil')$$, 'user cannot claim jobs');
select pg_temp.expect_error($$insert into public.herbs (name_he, name_en) values ('x', 'x')$$, 'user cannot add herbs');

-- ---------------------------------------------------------------- researcher: no direct table access either (D-011)
select set_config('request.jwt.claims', '{"sub":"00000000-0000-4000-a000-0000000000cc","role":"authenticated"}', true);
select pg_temp.check((select count(*) = 0 from public.requests), 'researcher has no direct request access');
select pg_temp.expect_error('select * from public.response_drafts', 'researcher reads drafts via backend only');

-- ---------------------------------------------------------------- anon
reset role;
set local role anon;
select set_config('request.jwt.claims', '{"role":"anon"}', true);
select pg_temp.check((select count(*) >= 1 from public.herbs), 'anon reads herbs');
select pg_temp.expect_error('select id from public.requests', 'anon cannot read requests');
select pg_temp.expect_error('select id from public.profiles', 'anon cannot read profiles');
reset role;

-- published response becomes visible to its owner only
update public.requests set status = 'in_review' where id = '10000000-0000-4000-a000-00000000000a';
update public.requests set status = 'published' where id = '10000000-0000-4000-a000-00000000000a';
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-4000-a000-00000000000a","role":"authenticated"}', true);
select pg_temp.check((select count(*) = 1 from public.responses), 'owner sees published response');
select pg_temp.check((select public_status = 'published' from public.requests), 'public status published');
select pg_temp.expect_error('select approved_by from public.responses', 'approver id hidden');
select set_config('request.jwt.claims', '{"sub":"00000000-0000-4000-a000-00000000000b","role":"authenticated"}', true);
select pg_temp.check((select count(*) = 0 from public.responses), 'other user cannot see response');
reset role;

-- ---------------------------------------------------------------- job queue (service role)
delete from public.research_jobs;  -- isolate from seeded jobs (rolled back at the end)
set local role service_role;
insert into public.research_jobs (kind, request_id, idempotency_key, max_attempts)
  values ('research', '10000000-0000-4000-a000-00000000000b', 'req-b:research:1', 2);
select pg_temp.expect_error($$insert into public.research_jobs (kind, idempotency_key)
  values ('research', 'req-b:research:1')$$, 'idempotency key unique');

create temp table j as select * from public.claim_job('w1', 60);
select pg_temp.check((select count(*) = 1 and bool_and(status = 'running' and attempts = 1 and locked_by = 'w1') from j),
                     'claim marks running');
select pg_temp.check((select count(*) = 0 from public.claim_job('w2')), 'leased job not claimable twice');
select pg_temp.check(public.heartbeat_job((select id from j), 'w1', 120), 'owner heartbeat');
select pg_temp.check(public.heartbeat_job((select id from j), 'w2') is null, 'foreign heartbeat ignored');

select pg_temp.check(public.fail_job((select id from j), 'w1', '{"e":"boom"}') = 'queued', 'retryable failure requeues');
select pg_temp.check((select run_after > now() from public.research_jobs where id = (select id from j)), 'backoff delays retry');
select pg_temp.check((select count(*) = 0 from public.claim_job('w1')), 'not claimable during backoff');

-- crash recovery: lease expired -> reclaimable; exhausted attempts -> dead
update public.research_jobs set run_after = now() - interval '1 second' where id = (select id from j);
select pg_temp.check((select attempts = 2 from public.claim_job('w1')), 'second attempt claimed');
update public.research_jobs set lease_expires_at = now() - interval '1 second' where id = (select id from j);
select pg_temp.check((select count(*) = 0 from public.claim_job('w3')), 'expired + exhausted job not re-run');
select pg_temp.check((select status = 'dead' from public.research_jobs where id = (select id from j)), 'exhausted job dead');

insert into public.research_jobs (kind, idempotency_key) values ('research', 'nonretry:1');
select pg_temp.check(public.fail_job((select id from public.claim_job('w1')), 'w1', '{"e":"not configured"}', false) = 'dead',
                     'non-retryable failure is dead');
insert into public.research_jobs (kind, idempotency_key) values ('research', 'ok:1');
select pg_temp.check(public.complete_job((select id from public.claim_job('w1')), 'w1'), 'complete job');
reset role;

-- ---------------------------------------------------------------- storage
select pg_temp.check((select public = false from storage.buckets where id = 'research-artifacts'), 'bucket private');
select pg_temp.check((select count(*) = 0 from pg_policies where schemaname = 'storage'
                      and qual ilike '%research-artifacts%'), 'no client storage policies on bucket');

select 'all_tests_passed' as result;
rollback;
