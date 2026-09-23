# Architecture

```
browser (static HTML/JS, Phase 4)
   │  supabase-js: sign-in only → access token (ES256 JWT)
   ▼
backend (FastAPI, /api/v1)  ──── direct Postgres (session pooler, psycopg) ───►  Supabase Postgres
   │  verifies JWT via JWKS, reads role from profiles                              RLS: clients read-only
   └─ enqueues research_jobs  ◄── Phase 3 worker thread claims them (claim_job)
```

## Backend (`backend/`, Phase 2)

| File | Role |
|------|------|
| `app/main.py` | app factory: lifespan (DB pool), CORS, security headers, per-IP limiter, error envelope |
| `app/settings.py` | env config (`.env` locally, Railway vars in cloud) |
| `app/db.py` | psycopg pool; `tx(conn, actor_id)` = transaction + `app.actor_id` for the audit trigger |
| `app/auth/jwt.py` | token verification (ES256, JWKS, iss/aud/exp/sub), `User` / `Staff` / `Admin` dependencies |
| `app/domain/status.py` | transition table mirror (tested equal to the DB table) |
| `app/domain/herbs.py` | herb identification: normalized exact match on names + aliases |
| `app/services/requests.py` | lifecycle actions; each is one transaction with a row lock |
| `app/api/v1.py` | routes + request models |

**Sync on purpose:** sync psycopg and sync routes, run in FastAPI's threadpool. Async psycopg does not work on Windows' default event loop, and the sync version is simpler. The Phase 3 worker runs as a thread in the same process (D-010).

### Auth and authorization
- Tokens are verified locally against the project JWKS (`/auth/v1/.well-known/jwks.json`, ES256). HS256 is rejected.
- The role is read from `profiles.role` on every request, never from the token, so role changes apply immediately (D-017).
- `user`: only their own requests. Another user's request returns **404**, so its existence isn't revealed.
- `researcher`: only requests assigned to them. Only the assigned researcher can **publish** (one approval).
- `admin`: everything else (all requests, assigning, roles), but can't approve a response and can't change their own role.

### API (`/api/v1`)
- Public: `GET /health`, `GET /herbs`. Signed in: `GET /me`.
- User: `POST/GET /requests`, `GET /requests/{id}`, `POST /requests/{id}/withdraw`, `POST /requests/{id}/clarifications/{cid}/answer`.
- Staff: `GET /staff/requests[?status=]`, `GET /staff/requests/{id}` (incl. `herb`, `sources`, `drafts`, `jobs`, `events`), `POST …/start-review`, `PUT …/draft`, `POST …/clarifications`, `POST …/publish` (body must match schema v1), `POST …/close`, `POST …/rerun` `{fresh?}`, `PATCH …/herb` `{herb_id}`, `POST …/save-review`, `GET /staff/reviews[?herb_id=]`, `GET /staff/reviews/{id}`.
- Admin: `POST /admin/requests/{id}/assign`, `GET /admin/researchers`, `GET /admin/users`, `PATCH /admin/users/{id}/role`.
- Errors: `{"error": {"code", "message"}}`. Codes: `missing_token`, `invalid_token`, `forbidden`, `not_found`, `invalid_transition` (409), `quota_daily` / `quota_open` / `rate_limited` (429), `validation_error` / `content_invalid` / `content_too_large` / `unknown_herb` (422), `not_published` / `herb_required` / `review_exists` / `job_pending` / `content_flags` (409), and others. `content_flags`: the published body contains wording flagged as dose / recommendation / cure claim / score; the researcher must re-submit with `acknowledge_flags: true`. The frontend maps codes to Hebrew.
- Interactive docs are served at `/docs`, except in production.

### Request → research (Phase 3)
`POST /requests` inserts the request (`submitted`) and a `research_jobs` row in one transaction, with key `request:{id}:research:{n}`. `rerun` (from `in_review` / `research_failed`) moves the request to `researching` and enqueues job `n+1` in one transaction; it is refused with `job_pending` while a job is queued/running. `payload.fresh` skips review reuse.

The **worker** (`app/jobs/`, D-019) is one daemon thread in the backend process, started in the lifespan only when `WORKER_ENABLED=true`. Loop: `claim_job` → heartbeat thread (lease/3) → `process_research_job` → `complete_job` / `fail_job`.

1. Lock the request; a job only starts from `submitted` or `researching`. Anything else (withdrawn, closed, or a review already in progress) → the job completes as a no-op, so a late job can never take over a review.
2. **Reuse** (D-020): if the herb has an approved review in schema v1, the draft is built from it deterministically — no AI, no HTTP — and still needs the assigned researcher's approval.
3. **Search**: PubMed (esearch → efetch) and Europe PMC with herb English/Latin names × appetite/cachexia/food intake/weight/QoL × cancer. A Hebrew-only unknown herb fails `herb_unidentified` until staff set the herb (`PATCH …/herb`) and rerun. One source failing is tolerated (flagged `partial_search`); both failing, or a failure with no hits at all → `literature_unavailable` (retryable) — an outage never becomes a "none found" draft.
4. Dedupe (pmid → doi → pmcid, PubMed wins), upsert `literature_sources`, link `request_sources` — committed on its own so staff see sources even if the AI step fails.
5. **Draft**: no sources → a fixed "none found" statement (no AI). Otherwise the AI provider returns an `Analysis`; the backend attaches herb, cited sources and `schema_version`, validates `DraftContent`, and records soft `ai_flags` (dose / recommendation / cure / score wording) in `response_drafts.meta`.
6. One transaction: re-lock, insert draft (`job_id`, provider, model, meta), → `draft_ready`, `complete_job`. A lost lease rolls everything back.

The pool runs in autocommit, so `tx()` is the only transaction boundary and no connection stays idle-in-transaction during HTTP. Failures are stored as `research_jobs.last_error = {code, stage, message, at}`; a dead job moves the request to `research_failed` (in SQL). Users only ever see `in_progress`.

**AI provider** (D-008): `AI_PROVIDER=openai` + `AI_MODEL` + `AI_API_KEY` → `OpenAIProvider` (Responses API over the SafeClient, strict JSON schema, `store: false`); anything missing → `NullProvider` → `ai_not_configured` (non-retryable). Never mock content.

**Outbound HTTP** (`app/research/http.py`): https only, host allowlist (`eutils.ncbi.nlm.nih.gov`, `www.ebi.ac.uk`, `api.openai.com`), no redirects, 5 MB decoded-body cap, timeouts, NCBI rate limit 3/s (10/s with `NCBI_API_KEY`); keys never appear in errors.

**Content schema v1** (`app/ai/schema.py`): `evidence_base` (category, never a number), `appetite` (primary), `secondary[]` (food_intake / weight / quality_of_life, separate), `safety_notes_he[]`, `limitations_he[]`, `sources[]`, plus `personal_context_he` and `consult_team_note_he` for personalized content. Every finding cites a listed source. The same shape is a draft, a published body and (without the personal fields) a reusable review.

### Limits (D-018)
- Per user, counted in the DB: 5 submissions per 24h, and at most 3 open requests.
- Per IP, in memory: 120 requests/min, keyed on `X-Real-IP`. This only works with a single replica.

### Security headers
`Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`, `nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, plus HSTS in production. CORS allows only the exact origins in `CORS_ALLOWED_ORIGINS`.

## Frontend (`frontend/`, Phase 4)

Plain HTML + CSS + ES modules, no build step (D-003), Hebrew RTL (`<html lang="he" dir="rtl">`).

| Page | Who | Purpose |
|------|-----|---------|
| `index.html` | public | what the service does and does not do |
| `evidence.html[?s=]` | public | evidence map by symptom: studied herbs with evidence level, and known cautions (static demo data in `js/evidence-demo.js`, no API) |
| `auth.html?mode=login\|signup\|reset\|update\|verified` | public | Supabase Auth (PKCE); messages never reveal whether an email exists |
| `requests.html`, `new.html`, `request.html?id=` | user | my requests, new request (herb list + free text, "לא ידוע" per optional field), detail with clarification answers, the approved response, withdraw |
| `staff.html`, `staff-request.html?id=` | researcher / admin | queue (admins assign), workspace: job error, herb fix, sources, structured draft editor, clarification, rerun, publish (assigned researcher only), save as reusable review |
| `reviews.html[?id=]` | researcher / admin | repository of reusable reviews |
| `admin.html` | admin | users and roles |

- `js/dom.js` builds DOM with `createElement`/`textContent` only (no `innerHTML`); links only for http(s) URLs; user text, Latin names, PMIDs and DOIs are wrapped in `<bdi>`.
- `js/i18n.js` maps every backend error code, public/internal status, job error code, study type and outcome to Hebrew.
- `js/render/response.js` renders schema-v1 content (appetite first, secondary outcomes separately, evidence base in words); `js/render/editor.js` edits it, with citations restricted to the request's gathered sources.
- Runtime config `js/config.js` (`API_BASE_URL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `APP_ENV`, all public) is written at container start by `docker-entrypoint.sh` (validated) or served by `dev_server.py` locally.
- `supabase-js` 2.117.0 UMD and Noto Sans Hebrew are vendored (`js/vendor/`, `fonts/`); versions and hashes are in `frontend/README.md`.
- Serving: Caddy (`frontend/Caddyfile`, `frontend/Dockerfile`). CSP `default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' <API> <Supabase>; frame-ancestors 'none'`, plus nosniff, no-referrer, Permissions-Policy and HSTS. No inline scripts or styles.
- a11y: skip link, labelled fields, error summary that takes focus, `aria-live` announcements, `<dialog>` confirmations, 44px targets, status shown as icon + text (never colour alone), `prefers-reduced-motion`.

## Running locally
```
cd backend
uv sync
uv run pytest -q                      # unit + integration (dev DB, rolled back); keep WORKER_ENABLED=false meanwhile
uv run uvicorn app.main:app --reload  # needs backend/.env (see .env.example)
# with the worker: WORKER_ENABLED=true uv run uvicorn app.main:app
```
