# Data model

Source of truth: `supabase/migrations/`. Dev project: `herbal-evidence-dev` (ref `vtcmicxlujahurhetcaa`, org "Herbal Evidence", eu-central-1).

## Access model

- **All writes go through the backend** using the service-role key (D-011, D-015). Clients have no INSERT/UPDATE/DELETE grants on any table.
- `authenticated` gets **read-only** RLS on its own rows only; `anon` can read `herbs` only.
- Staff (researcher/admin) have **no** direct table access either: the backend authorizes them from `profiles.role`.
- Roles live in `profiles.role` (`user | researcher | admin`), never in `user_metadata`. A trigger creates a `user` profile on signup; only the backend promotes.

## Tables

| Table | Purpose | Client access |
|-------|---------|---------------|
| `profiles` | role + display name per auth user | own row (select) |
| `herbs` | reference herbs + `aliases` for herb identification | anon + authenticated (select) |
| `requests` | the user's claim: herb (required), preparation / cancer type / treatment (NULL = "I don't know") | own rows, **selected columns only** (no `status`, no `assigned_researcher_id`) |
| `request_status_transitions` | allowed status changes (data, mirrored by backend) | none |
| `request_events` | audit log of every status change, with actor | none |
| `clarifications` | researcher question ↔ user answer | own requests (select; answers written via backend) |
| `literature_sources` | PubMed / Europe PMC records | none |
| `evidence_reviews` | reusable, versioned review per herb | none |
| `review_sources` | review ↔ source links | none |
| `response_drafts` | AI-assisted drafts; never shown to users | none |
| `responses` | the approved, published response (one per request, `approved_by` required) | own request, only when published; `approved_by` hidden |
| `research_jobs` | durable job queue (D-010) | none |

Storage: private bucket `research-artifacts` (PDF/text/JSON/CSV, 20 MB), no storage policies → service role only.

## Request status

`public_status` is a generated column: users see only `in_progress`, `needs_clarification`, `published`, `withdrawn`, `closed` — no drafts, failures, or queue position.

```
submitted ──► researching ──► draft_ready ──► in_review ──► published
   │              │   ▲                         │  ▲  │
   │              ▼   │                         │  │  └──► researching (re-run)
   │        research_failed                     ▼  │
   │                                 awaiting_clarification
   └── any non-terminal ──► withdrawn (user) / closed (staff);  published ──► withdrawn
```

A trigger rejects any transition not in `request_status_transitions`, forces new rows to start as `submitted`, and writes `request_events`. Actor = `auth.uid()`, or the backend sets `select set_config('app.actor_id', '<uuid>', true)` in the same transaction.

## Job queue

Functions (service role only): `claim_job(worker, lease_seconds)`, `heartbeat_job(id, worker, lease_seconds)`, `complete_job(id, worker)`, `fail_job(id, worker, error, retryable)`.

- Claim uses `FOR UPDATE SKIP LOCKED`; also reclaims `running` jobs whose lease expired (crash recovery).
- Failure: backoff `30s × 2^attempts` (max 1h) until `max_attempts` (default 5), then `dead`. `retryable = false` (e.g. AI provider not configured) → `dead` immediately.
- `idempotency_key` is unique: enqueue with `on conflict (idempotency_key) do nothing`.

## Seed and tests

- `supabase/seed.sql`: reference herbs + MOCK users/requests in every public status. Mock users have no password (cannot log in). `supabase db query --linked -f supabase/seed.sql` (idempotent).
- `supabase/tests/permissions.sql`: RLS, column grants, state machine, job queue, storage. Runs in a transaction and rolls back. `supabase db query --linked -f supabase/tests/permissions.sql` → `all_tests_passed`.
