# Herbal Evidence (ראיות צמחים)

Hebrew-first (RTL) web platform where people with cancer and their caregivers submit a claim about a **single herb and appetite improvement**. The system prepares an AI-assisted evidence-review draft; a **human researcher checks, edits, and approves** every personalized response before it is published to the user's account.

The platform does **not** recommend which herb to take, does not prescribe doses, and does not approve combinations with treatment.

## Monorepo layout

| Path | Purpose |
|------|---------|
| `frontend/` | Static HTML/CSS/JS site (own Railway service) |
| `backend/` | FastAPI + Uvicorn API, research/AI workflow, Postgres-backed job queue (own Railway service) |
| `supabase/` | Supabase CLI config, migrations, mock seed |
| `docs/` | Architecture, decisions, data model, deployment, researcher guide, privacy |

## Environments

| Env | Git branch | Railway env | Supabase project |
|-----|-----------|-------------|------------------|
| dev | `dev` | `dev` | `herbal-evidence-dev` |
| production | `main` | `production` | `herbal-evidence-prod` |

Details and setup steps: see `docs/deployment.md`. Development status per phase is tracked in the project's Obsidian vault (`HERBAL_EVIDENCE_PROJECT/`).

## Local development (filled in as phases complete)

1. Database: cloud dev project, no Docker (D-014). `supabase link --project-ref vtcmicxlujahurhetcaa`, then `supabase db push --linked`; tests: `supabase db query --linked -f supabase/tests/permissions.sql`. See `docs/data-model.md`.
2. Backend: `cd backend && uv sync && uv run pytest -q && uv run uvicorn app.main:app --reload` (needs `backend/.env`, see `.env.example`). See `docs/architecture.md`.
3. Frontend: copy `frontend/.env.example` to `frontend/.env` (public values only), then `python frontend/dev_server.py` → http://localhost:8080. Same CSP/headers as the Caddy container; `js/config.js` is generated from `.env`. Start the backend with `WORKER_ENABLED=true` to process research jobs. See `frontend/README.md`.

## Status

Phases 3 (research worker + AI) and 4 (Hebrew RTL frontend) — done, pending review. See `docs/decisions.md` for engineering choices.
