# Engineering Decisions (changeable implementation choices)

These entries are **implementation defaults**, not previously approved product decisions. Product-level binding decisions live in the specification (sections 1–2) and are not restated here.

| # | Date | Decision | Rationale | Status |
|---|------|----------|-----------|--------|
| D-001 | 2026-09-16 | Working name **Herbal Evidence** (Hebrew UI: ראיות צמחים). Hebrew RTL first, structured for future localization (string tables, `dir` attributes, bidi isolation). | Spec §3 | default |
| D-002 | 2026-09-16 | Backend: Python 3.13, FastAPI, Uvicorn, `uv` for dependency management. | Spec §3; uv installed locally | default |
| D-003 | 2026-09-16 | Frontend: plain HTML/CSS/JS, no framework. Served by a static server (Caddy) in its own Railway service. | Spec §3 | default |
| D-004 | 2026-09-16 | Auth: Supabase Auth, email/password, email verification, password reset. Backend validates Supabase JWTs (iss/aud/exp). | Spec §3 | default |
| D-005 | 2026-09-16 | Admin manually assigns requests to researchers. Simple `assigned_researcher_id` column; replaceable. | Spec §3, open business decision | default |
| D-006 | 2026-09-16 | No request-update emails in v1. | Spec §3 | default |
| D-007 | 2026-09-16 | Separate Supabase projects `herbal-evidence-dev` and `herbal-evidence-prod`, in a **new Supabase organization** created for this product. | Spec §3, §12; user choice during planning | default |
| D-008 | 2026-09-16 | AI provider interface is replaceable; first concrete adapter targets **OpenAI**. Model and key via `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY`. Without a key the provider raises a structured "not configured" job failure — never mock content. | Spec §3; user choice during planning | default |
| D-009 | 2026-09-16 | Literature adapters: PubMed E-utilities (esearch/efetch) + Europe PMC REST. Optional `NCBI_API_KEY` for higher rate limits. | Spec §6 | default |
| D-010 | 2026-09-16 | Durable job queue in Postgres (`research_jobs`), claimed with `FOR UPDATE SKIP LOCKED`, lease + heartbeat, bounded retries, idempotency key; consumer runs inside the backend process lifespan. No Redis, no third service. | Spec §8 | default |
| D-011 | 2026-09-16 | Drafts and staff artifacts have **no** RLS policies for `anon`/`authenticated`; they are reachable only through the backend using the service-role key with explicit server-side authorization. | Spec §9–10 | default |
| D-012 | 2026-09-16 | Design created in Google Stitch (project `12444680124780591192`, design system asset `602809031577218080`). Screen IDs in `docs/design/stitch.md`. | Spec §11 | default |
| D-013 | 2026-09-16 | Work is executed in phases (0–6) with a review stop after each; progress logged in Obsidian `HERBAL_EVIDENCE_PROJECT/`. | User instruction | default |
| D-014 | 2026-09-23 | No Docker / no local Supabase stack. Development runs against the cloud dev project `herbal-evidence-dev` (ref `vtcmicxlujahurhetcaa`) in a dedicated org "Herbal Evidence" (`ipdahvxxgtynawcioskz`), created in Phase 1 via CLI. Migrations: `supabase db push --linked`; tests/seed: `supabase db query --linked -f`. | User choice 2026-09-23 | default |
| D-015 | 2026-09-23 | Clients are read-only at the DB level: all writes (including answering clarifications) go through the backend; `requests.status` and assignment are hidden via column grants, users see a generated `public_status`. | Keeps state machine + authz in one place | default |
| D-016 | 2026-09-23 | Backend talks to Postgres **directly** (psycopg, sync, session pooler) — not PostgREST/supabase-py — so actor, transition and job enqueue share one transaction. JWTs verified locally with the project's **ES256 JWKS**. | Atomic lifecycle; no shared JWT secret | default |
| D-017 | 2026-09-23 | Role is read from `profiles.role` on every request (never from JWT claims). Only the assigned researcher may publish; admins assign/manage but do not approve. | Immediate role changes; one researcher approval | default |
| D-018 | 2026-09-23 | Limits: 5 submissions / 24h and max 3 open requests per user (DB-counted); 120 req/min per IP in memory (single replica). | Abuse control without extra infra | default |
| D-019 | 2026-09-23 | Research worker = one daemon thread in the backend process, opt-in via `WORKER_ENABLED` (off in tests). HTTP never runs inside a DB transaction; each state change re-locks the request. Outbound HTTP only through an allowlisted, no-redirect, size-capped client. | D-010 without a third service; SSRF safety | default |
| D-020 | 2026-09-23 | Reusing an approved evidence review is deterministic (no AI call) and still requires the assigned researcher's approval per response. Only schema-v1 reviews are reused; no literature at all yields a fixed "none found" draft, not AI text. `fresh` rerun skips reuse. | One approval per response; no invented content | default |
