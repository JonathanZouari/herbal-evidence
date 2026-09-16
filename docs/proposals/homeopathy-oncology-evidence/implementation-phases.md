# Implementation phases

Each phase ends in a human review stop, matching the existing project's phased-work convention (`docs/decisions.md` D-013) and the sibling Ayurveda proposal's approach.

| Phase | Scope | Review stop |
|---|---|---|
| 1 | Repository reconciliation and source-integrity audit; machine-readable contracts (this branch: all `docs/proposals/homeopathy-oncology-evidence/*.md`, `knowledge/homeopathy-oncology/*.json`, `scripts/validate_homeopathy_proposal.py`, `backend/tests/test_homeopathy_knowledge_contract.py`) | Jonathan Zouari product/merge confirmation |
| 2 | Machine-readable contracts made durable: additive DB/domain foundation (`homeopathy_*` tables, roles, migrations) -- no patient-visible surface | Engineering review of schema/migration safety |
| 3 | Source intake and AI-assisted extraction into `untrusted_draft` rows only, with page/section citations; no automatic claim publication | Confirm AI drafts cannot reach `published` without human action |
| 4 | Evidence and safety review: independent study appraisal, exact-formulation matching, safety checks, integrity screening, oncology/pharmacy review, evidence-methodology review, optional homeopathy-domain description review | Confirm the dual-approval gate cannot be bypassed (contract tests + service-layer tests both pass) |
| 5 | Staff review experience: source comparison, positive/null/negative/retracted result display, duplicate/integrity alerts, audit trail, approval controls | Confirm staff cannot mistake a homeopathy-domain review for an oncology/evidence-methodology approval |
| 6 | Restricted patient education, only after separate approval: neutral "what evidence shows" cards, prominent non-substitution warnings, care-team disclosure guidance, accessibility and RTL validation -- no remedy selection or dosing | Clinical + product review of actual rendered patient copy, RTL included |
| 7 | Surveillance and release validation: correction/retraction monitoring, expiry, emergency unpublish, rollback, independent clinical validation, post-release safety monitoring | Final go/no-go before the feature flag is ever turned on for any real user |

Phase 1 is the only phase this branch implements. Phases 2-7 are described in `integration-plan.md` but not built here, and no production feature is implemented on this branch.
