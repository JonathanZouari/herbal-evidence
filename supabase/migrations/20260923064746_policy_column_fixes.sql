-- Policies on clarifications/responses subquery requests; authenticated needs the columns they read.
grant select (user_id) on public.requests to authenticated;

drop policy "read own responses" on public.responses;
create policy "read own responses" on public.responses for select to authenticated
  using (exists (select 1 from public.requests r
                 where r.id = request_id and r.user_id = (select auth.uid())
                   and r.public_status = 'published'));

-- advisor: unindexed foreign key
create index clarifications_asked_by_idx on public.clarifications (asked_by);
