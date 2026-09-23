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
- Staff: `GET /staff/requests[?status=]`, `GET /staff/requests/{id}`, `POST …/start-review`, `PUT …/draft`, `POST …/clarifications`, `POST …/publish`, `POST …/close`, `POST …/rerun`.
- Admin: `POST /admin/requests/{id}/assign`, `GET /admin/users`, `PATCH /admin/users/{id}/role`.
- Errors: `{"error": {"code", "message"}}`. Codes: `missing_token`, `invalid_token`, `forbidden`, `not_found`, `invalid_transition` (409), `quota_daily` / `quota_open` / `rate_limited` (429), `validation_error` (422), and others. The frontend maps codes to Hebrew.
- Interactive docs are served at `/docs`, except in production.

### Request → research
`POST /requests` inserts the request (`submitted`) and a `research_jobs` row in one transaction, with key `request:{id}:research:{n}`. The Phase 3 worker claims the job and moves the request to `researching`. `rerun` only enqueues job `n+1`.

### Limits (D-018)
- Per user, counted in the DB: 5 submissions per 24h, and at most 3 open requests.
- Per IP, in memory: 120 requests/min, keyed on `X-Real-IP`. This only works with a single replica.

### Security headers
`Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`, `nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, plus HSTS in production. CORS allows only the exact origins in `CORS_ALLOWED_ORIGINS`.

## Running locally
```
cd backend
uv sync
uv run pytest -q                      # unit + integration (dev DB, rolled back)
uv run uvicorn app.main:app --reload  # needs backend/.env (see .env.example)
```
