# Integration plan

## Additive module boundary and compatibility

`supportive_care_evidence` is a new, separately named domain area. It does not repurpose the existing herb/appetite tables, routes, or schemas, and it does not merge its claims, terminology, tables, or approval roles into the separate (currently unmerged) `ayurveda-oncology-support` proposal's `supportive_care` module. Where a *generic* primitive already exists in that proposal's design (source registry shape, evidence-card shape, immutable-version-plus-approval-record pattern, allowed-states-enum pattern), this module reuses the same generic shape rather than inventing a parallel one from scratch -- but with its own table names, its own allowed-states enum (which differs: this module adds `blocked_integrity` and `blocked_no_results`, states the Ayurveda proposal has no equivalent need for), and its own approval-role set. If the Ayurveda proposal merges first, this module's tables sit alongside it with no foreign-key dependency; if this module merges first, the reverse holds. Neither module cherry-picks or depends on the other's unmerged commits.

## Domain shape (additive, Phase 2)

- `homeopathy_sources` -- mirrors `source_registry.json`: id, url (nullable), title, source_type, publication_status, evidence_eligibility, canonical_work_id, occurrences, accessed_at, verification_status.
- `homeopathy_evidence_cards` -- mirrors `example_evidence_cards.json`, versioned and immutable per version (a new version is a new row).
- `homeopathy_card_approvals` -- one row per (card_version, role): `oncology_or_pharmacist`, `evidence_methodology_reviewer` required; `homeopathy_domain_reviewer` optional and structurally incapable of satisfying either required role or setting an evidence-elevating flag (enforced at the service layer the same way `check_publish_eligibility()` enforces it in the standalone validator).
- No diet/nutrition table of any kind is added by this module (see the root proposal README's "Nutrition scope decision").

## Roles and permission boundaries

Extends the role model with `oncology_clinician_or_pharmacist`, `evidence_methodology_reviewer`, and optional `homeopathy_domain_reviewer` -- each distinct from `researcher`, `editor`, `administrator`, and `product_owner`. Application code must reject an approval row whose granting role is not one of the two required roles, mirroring `DISALLOWED_APPROVER_ROLES` in the validator. This must exist at the database/service layer in Phase 2+, not only in the standalone Phase-1 validator script.

## API concepts

- **Public API:** read-only, published-only evidence cards; anonymous browsing by default; no field ever exposes a dose, a potency-selection instruction, a frequency, a repertorization result, a purchase link, or a clinic referral -- the same forbidden-key list the validator checks becomes a response-serializer denylist.
- **Staff API:** source intake, AI-assisted draft extraction (marked `untrusted_draft`, with page/section citations back to the source, until a human touches it), card editing, and approval-recording endpoints, each checking the caller's role server-side.

## UI

- Patient-facing: Hebrew RTL first, English second, unchanged product stance. Latin botanical/homeopathic-preparation names (e.g. *Conium maculatum*), study identifiers (e.g. PMID 16376071), and drug names render left-to-right within RTL flow via Unicode bidi isolation, matching the existing product's approach.
- Staff-facing: an evidence-review UI showing source comparison, positive/null/negative/retracted result display side by side (never averaged away), duplicate/integrity alerts (e.g. a banner if a cited source's `publication_status` changes to `retracted` after a card was approved), full audit trail, and approval controls that visibly distinguish "oncology/pharmacy approved," "evidence-methodology approved," and the optional "homeopathy-domain reviewed (description accuracy only)" badge so staff never mistake the third for a substitute for the first two.

## Surveillance, correction/retraction monitoring, and rollback

- Every create/edit/approve/reject/suspend/expire/retract/unpublish action is audit-logged (who, role, content version, when) -- `scripts/validate_homeopathy_proposal.py`'s `validate_audit_event_contract()` encodes the required action-type set now so Phase 6's real audit-log schema has a checklist to validate against.
- Sources carry `publication_status` and `verification_status` so a later retraction (as happened to the Frass 2020 paper five years after publication) or a registry-status change (as happened to NCT02190539) can trigger an automatic **emergency-suspension review** of every card citing that source, rather than the card silently going stale.
- A published card can be suspended (removed from public API responses) pending re-review; suspension is audited the same way as publication and is reversible without a destructive migration.
- Feature flag, default off, gates the public API and patient UI; rollback is a flag flip, since this module never touches existing tables.

## Testing

- **Contract tests (this proposal):** `backend/tests/test_homeopathy_knowledge_contract.py` against `scripts/validate_homeopathy_proposal.py` -- dependency-free, Phase-1-only.
- **Future phases:** service-layer tests re-running the same rules against a real database; content tests re-running the forbidden-phrase/forbidden-key scans against staff-authored content; accessibility tests on the patient education UI (Phase 5) covering RTL bidi-isolation of Latin terms and screen-reader labeling of evidence-state badges; end-to-end tests covering draft -> dual-approval -> publish -> public-API-visible, plus a negative end-to-end test that a single missing approval, or a post-publication retraction, correctly blocks/suspends the card.

## Metrics

Phase 6+ metrics should include: count of cards by state, count of sources by `publication_status`/`evidence_eligibility`, time-to-detection for a retraction/withdrawal affecting a published card, and count of staff-disclosed product-use events surfaced through the `clinician_discussion_only` pathway (a proxy for whether the disclosure messaging is actually being used, not a clinical outcome metric).
