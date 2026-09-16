# Integration plan

## Additive module boundary and compatibility

`supportive_care_evidence` (Chinese-herbal branch) is a new, separately named domain area. It does not repurpose the existing herb/appetite tables, routes, or schemas, and does not merge its claims, terminology, tables, or approval roles into either sibling (currently unmerged) proposal -- `ayurveda-oncology-support` or `homeopathy-oncology-evidence`. Where a *generic* primitive already exists in either sibling's design (source registry shape, evidence-card shape, immutable-version-plus-approval-record pattern, allowed-states-enum pattern), this module reuses the same generic shape with its own table names and its own allowed-states enum (this module's set differs from both siblings': it adds `preclinical_research_only` and `out_of_scope_adjacent`, states the others don't need in the same way) and its own approval-role set (`oncology_or_pharmacist`, `evidence_methodology_reviewer`, `tcm_practitioner`, plus `oncology_dietitian` for nutrition -- four distinct roles, none of which may substitute for another). Whichever of the three proposals merges first, the others sit alongside it with no foreign-key dependency.

## Domain shape (additive, Phase 2)

- `chinese_herbal_sources` -- mirrors `source_registry.json`.
- `chinese_herbal_evidence_cards` -- mirrors `example_evidence_cards.json`, versioned and immutable per version.
- `chinese_herbal_card_approvals` -- one row per (card_version, role): `oncology_or_pharmacist`, `evidence_methodology_reviewer`, `tcm_practitioner` all required; no role may satisfy another's slot.
- `chinese_herbal_diet_templates` and `chinese_herbal_diet_template_approvals` -- same pattern, requiring `oncology_dietitian` specifically (a `tcm_practitioner` approval never substitutes).
- `alternative_modality_screening_records` -- mirrors `alternative_modality_screening.json`; staff-only visibility (see interview-decisions.md, H2-006), auditable but never itself a publish path.

## Roles and permission boundaries

Extends the role model with `oncology_clinician_or_pharmacist`, `evidence_methodology_reviewer`, `tcm_practitioner` (credentialed per intended launch jurisdiction), and `oncology_dietitian` -- four distinct approval-granting roles, each structurally incapable of satisfying another's slot. Application code must reject an approval row whose granting role does not exactly match the slot it's filling, mirroring `check_publish_eligibility_card()`/`check_publish_eligibility_diet()`'s no-cross-substitution rule. This must exist at the database/service layer in Phase 2+, not only in the standalone Phase-1 validator.

## API concepts

- **Staff API (this proposal's only near-term concept):** source intake, AI-assisted draft extraction (marked `untrusted_draft`, with page/section/table citations, and a translation-needed flag for non-English sources), card/template editing, approval-recording endpoints, and the alternative-modality screening record view -- all staff-only.
- **Future restricted patient API (Phase 6+):** read-only, published-only cards and templates; no field ever exposes a dose, formula-selection instruction, syndrome/pulse/tongue-diagnosis result, purchase link, or clinic referral -- the same forbidden-key list the validator checks becomes a response-serializer denylist.

## UI

- Patient-facing (Phase 6+): Hebrew RTL first, English second. Chinese characters, pinyin, Latin botanical/formula names, study identifiers, and drug names render left-to-right within RTL flow via Unicode bidi isolation.
- Staff-facing: an evidence-review UI showing formula composition (with the ingredient/plant-part/preparation taxonomy), human-vs-preclinical separation, positive/null/negative/retracted result display side by side, interaction alerts, integrity flags, the alternative-modality screening table, full audit trail, and approval controls that visibly distinguish all four approval-granting roles so staff never mistake a TCM-practitioner review for oncology, pharmacy, evidence-methodology, or dietitian sign-off.

## Surveillance, correction/retraction monitoring, and rollback

- Every create/edit/translate/verify/approve/reject/suspend/expire/retract/unpublish action is audit-logged -- `scripts/validate_chinese_herbal_proposal.py`'s `validate_audit_event_contract()` encodes the required action-type set (a superset of the sibling proposals' sets, adding `translate` and `verify` for this module's bilingual-source-handling needs).
- Sources carry `publication_status`, `integrity_status`, and `access_status` so a later retraction, correction, or access change (e.g. the HealthTree page's `access_unverified` status resolving one way or the other) can trigger a suspension review of every card citing that source.
- A published card/template can be suspended pending re-review; suspension is audited the same way as publication and is reversible without a destructive migration.
- Feature flag, default off, gates any future patient API/UI; rollback is a flag flip, since this module never touches existing tables.

## Testing

- **Contract tests (this proposal):** `backend/tests/test_chinese_herbal_knowledge_contract.py` against `scripts/validate_chinese_herbal_proposal.py` -- dependency-free, Phase-1-only.
- **Future phases:** service-layer tests re-running the same rules against a real database; content tests re-running the forbidden-phrase/forbidden-key/high-risk-ingredient scans against staff-authored content; accessibility tests on the patient education UI covering RTL bidi-isolation of Chinese characters, pinyin, and Latin terms; end-to-end tests covering draft -> quadruple-approval (or oncology-dietitian-only for nutrition) -> publish -> staff/public-API-visible, plus a negative end-to-end test that a single missing approval, or a post-publication retraction/access-status change, correctly blocks/suspends the card.

## Metrics

Phase 7+ metrics should include: count of cards by state, count of sources by `publication_status`/`evidence_eligibility`/`access_status`, count of alternative-modality screening records by `screen_decision`, time-to-detection for a retraction/correction/access-status change affecting a published card, and count of staff-disclosed product-use events surfaced through the `clinician_discussion_only` pathway.
