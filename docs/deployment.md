# Deployment (Railway)

Project **herbal-evidence** (workspace "Jonathan Zouari's Projects"): https://railway.com/project/ed17e932-3622-4b74-b51d-9e6d808d879a
Provisioned 2026-09-23 with the `railway-provision` skill. Both services build from their own `Dockerfile`.

| Environment | Branch | Service | Root dir | Public URL | Supabase |
|-------------|--------|---------|----------|------------|----------|
| staging | `dev` | backend | `/backend` | https://backend-staging-ba03.up.railway.app | herbal-evidence-dev |
| staging | `dev` | frontend | `/frontend` | https://frontend-staging-1151.up.railway.app | herbal-evidence-dev |
| production | `main` | backend | `/backend` | https://backend-production-af6a3.up.railway.app | herbal-evidence-prod (not created yet) |
| production | `main` | frontend | `/frontend` | https://frontend-production-f7b1.up.railway.app | herbal-evidence-prod (not created yet) |

IDs: backend `a7e0ca14-c1e9-4c90-895e-dc89bd6d521e`, frontend `e5468d20-d3f1-4e46-aa82-d0e4e14c8e9d`, staging env `6d6d68d7-2ac7-4989-8be1-f450a2eeeaa4`, production env `dcf6dfc2-0b5f-473e-aaeb-8040267c07d7`.

All four service/env combinations: region **europe-west4** (next to Supabase eu-central-1), 1 replica, restart `ON_FAILURE` (max 5), healthcheck `/api/v1/health` (backend, 60 s) and `/` (frontend).

## Variables

**frontend** (all public; validated by `docker-entrypoint.sh`, which exits if one is missing): `APP_ENV` (`dev|production`), `API_BASE_URL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`. `PORT` is injected by Railway.

**backend**: `APP_ENV`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `DATABASE_URL` (**secret**, session pooler), `CORS_ALLOWED_ORIGINS` (= the frontend URL), `FRONTEND_ORIGIN`, `LOG_LEVEL`, `WORKER_ENABLED=true`, `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY` (**secret**), `NCBI_API_KEY` (optional secret), `NCBI_EMAIL`. Secrets are set by the owner, never committed:
```
railway variables -e staging -s backend --set "DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
```

## Status (2026-09-23)
- `dev` merged into `main` (PR #4, `b3ebd88`).
- staging frontend: serving (200; CSP, HSTS, runtime config verified with curl).
- staging backend: image builds; exits at start until `DATABASE_URL` is set (health 502).
- production: both images build from `main`. Set: `APP_ENV=production`, `API_BASE_URL`, `CORS_ALLOWED_ORIGINS`, `FRONTEND_ORIGIN`, `LOG_LEVEL`, `WORKER_ENABLED`, `AI_PROVIDER`. Missing: everything Supabase (`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `DATABASE_URL`), because the prod Supabase project doesn't exist yet (B-3) → containers exit at start, by design. Stale `dev` deployments left from the environment copy were removed.

## Still to do (Phase 5)
- Set `DATABASE_URL` on staging (B-10), then verify `/api/v1/health`, the worker log line and `X-Real-IP` (B-8).
- Supabase Auth URL configuration: add `https://frontend-staging-1151.up.railway.app/**` (and `http://localhost:8080/**`) as redirect URLs (B-12).
- Production: create the Supabase prod project, `db push`, variables, domains, then merge `dev` → `main`.
