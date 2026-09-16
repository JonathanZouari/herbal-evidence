# Implementation phases

Each phase ends in a human review stop, matching the existing project's phased-work convention (`docs/decisions.md` D-013). No phase after this proposal branch is authorized to start without that review.

| Phase | Scope | Review stop |
|---|---|---|
| 1 | Proposal reconciliation and machine-readable contracts (this branch: `README.md` through `review-request-for-jonathan.md`, `knowledge/ayurveda-oncology/*.json`, `scripts/validate_ayurveda_proposal.py`, `backend/tests/test_ayurveda_knowledge_contract.py`) | Jonathan Zouari product/merge confirmation |
| 2 | Additive database/domain foundation (`supportive_care_*` tables, roles, migrations) — no patient-visible surface | Engineering review of schema/migration safety |
| 3 | Source intake and AI-assisted extraction as `untrusted_draft` rows only | Confirm AI drafts cannot reach `published` without human action |
| 4 | Staff verification, safety review, dual/triple approvals, immutable publishing | Confirm the approval gate cannot be bypassed (contract tests + service-layer tests both pass) |
| 5 | Patient education UI and general diet templates, behind a feature flag, default off | Clinical + product review of actual rendered patient copy, RTL included |
| 6 | Evidence surveillance, suspension workflow, audit logging, operations | Confirm a suspension can happen and is itself audited |
| 7 | Independent release validation | Final go/no-go before the feature flag is ever turned on for any real user |

Phase 1 is the only phase this branch implements. Phases 2–7 are described in `integration-plan.md` but not built here.
