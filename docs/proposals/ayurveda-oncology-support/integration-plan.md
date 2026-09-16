# Integration plan

## Additive module boundary

`supportive_care` is a new, separately named domain area. It does not repurpose the existing herb/appetite tables, routes, or schemas for new clinical meanings — it adds its own tables, endpoints, and screens alongside them. The existing one-herb/appetite request → AI draft → researcher review → publish workflow (see root `README.md`, `docs/decisions.md` D-001–D-013) is unchanged by this proposal.

## Domain shape (additive, Phase 2)

New tables, distinct from the existing herb/appetite request tables:

- `supportive_care_sources` — mirrors `source_registry.json`'s shape: id, url (nullable for named-but-unlinked sources), type, tier, verification_status, eligible_for_efficacy_claims, occurrences, notes.
- `supportive_care_cards` — mirrors `example_cards.json`'s shape, versioned (immutable per version — a new version is a new row, never an in-place edit of an approved version).
- `supportive_care_card_approvals` — one row per (card_version, role), enforcing the dual-approval rule at the data layer, not just in application code.
- `supportive_care_diet_templates` and `supportive_care_diet_template_approvals` — same pattern, with the additional `oncology_dietitian` role requirement.

## Roles and permission boundaries

Extends the existing role model with: `oncology_clinician_or_pharmacist`, `ayurveda_clinician`, `oncology_dietitian` — each an *approval-granting* role distinct from `researcher`, `editor`, and `administrator`. Application code must reject an approval row where the granting role is not one of the three above, mirroring `check_publish_eligibility()`'s `DISALLOWED_APPROVER_ROLES` check. This is a defense-in-depth requirement: the check must exist at the database/service layer, not only in the proposal's standalone validator script.

## API concepts

- **Public API:** read-only, published-only cards and templates; anonymous browsing by default, consistent with the platform's data-minimization stance; no field ever exposes a dose, a purchase link, or a personalized plan.
- **Staff API:** source intake, AI-assisted draft extraction (marked `untrusted_draft` until a human touches it), card/template editing, and the approval-recording endpoints (each approval endpoint checks the caller's role server-side against the three approval-granting roles above).

## UI

- Patient-facing: Hebrew RTL first, English second — unchanged product stance. Latin botanical names (e.g. *Withania somnifera*) and drug names must render left-to-right within the RTL flow via Unicode bidi isolation (`<span dir="ltr">` / `⁦…⁩`), the same technique implied for the existing product by D-001.
- Staff-facing: a review queue surfacing cards/templates by approval state, so a partially-approved item (e.g. oncology sign-off present, Ayurveda sign-off pending) is visibly incomplete rather than ambiguous.

## Surveillance, audit, and staleness

- Every approval and publish action is audit-logged: who, which role, which content version, when.
- Sources carry a freshness concept (`verification_status`, and eventually a re-check interval) so that a null/negative trial published after a card's approval can trigger a suspension review rather than the card silently going stale.
- A published card/template can be suspended (removed from public API responses) pending re-review if new contradicting evidence surfaces; suspension is logged the same way as publication.

## Testing

- **Contract tests** (this proposal): `backend/tests/test_ayurveda_knowledge_contract.py` against `scripts/validate_ayurveda_proposal.py` — proposal-stage, dependency-free.
- **Future phases:** once the additive tables exist, the same validation rules move into the service layer with real DB-backed tests; content tests re-run the forbidden-phrase and required-field checks against actual staff-authored content; end-to-end tests cover the full draft → dual-approval → publish → public-API-visible path, including a negative end-to-end test that a single missing approval blocks publication.

## Feature flags and rollback

The public API and patient UI for `supportive_care` ship behind a feature flag, default off, so the additive tables and staff workflow can be built and reviewed (phases 1–4) well before any patient-visible surface exists (phase 5). Rollback is a flag flip plus (if needed) a table-level data freeze — no destructive migration is required to disable the feature, since it never touches the existing herb/appetite tables.
