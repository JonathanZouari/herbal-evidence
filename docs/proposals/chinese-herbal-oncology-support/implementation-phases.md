# Implementation phases

Each phase ends in a human review stop, matching the existing project's phased-work convention (`docs/decisions.md` D-013) and both sibling proposals' approach.

| Phase | Scope | Review stop |
|---|---|---|
| 1 | Repository reconciliation and source/integrity audit; inventory of every supplied source; the alternative-modality discovery screen; machine-readable contracts (this branch: all `docs/proposals/chinese-herbal-oncology-support/*.md`, `knowledge/chinese-herbal-oncology/*.json`, `scripts/validate_chinese_herbal_proposal.py`, `backend/tests/test_chinese_herbal_knowledge_contract.py`) | Jonathan Zouari product/merge confirmation |
| 2 | Machine-readable contracts made durable: additive DB/domain foundation (`chinese_herbal_*` tables, roles, migrations) -- no patient-visible surface | Engineering review of schema/migration safety |
| 3 | Source intake and AI-assisted extraction into `untrusted_draft` rows only, with precise page/section/table citations; automatic claim publication prevented; translation needs flagged for non-English sources | Confirm AI drafts cannot reach `published` without human action, and that untranslated sources are flagged rather than silently interpreted |
| 4 | Evidence, identity, interaction, and safety review: exact-product/botanical-identity verification, trial-method appraisal, interaction/contamination/jurisdiction review, oncology/pharmacy + evidence-methodology + TCM-practitioner review | Confirm the triple-approval gate cannot be bypassed and no role satisfies another's slot |
| 5 | Staff review experience: source comparison, formula composition display, human-vs-preclinical separation, positive/null/negative/retracted result display, interaction alerts, integrity flags, alternative-modality screening view, audit trail, approval controls | Confirm staff cannot mistake a TCM-practitioner review for oncology/pharmacy/evidence-methodology/dietitian sign-off |
| 6 | Restricted patient education and nutrition, only after separate approval: neutral "what evidence shows" cards, non-substitution warnings, product-disclosure guidance, oncology-dietitian-approved symptom templates, accessibility, and RTL validation -- no formula selection or dosing | Clinical + product review of actual rendered patient copy, RTL included, across Hebrew and English |
| 7 | Surveillance and independent release validation: correction/retraction monitoring, safety-alert and pharmacovigilance monitoring, source expiry, regulatory-change tracking, emergency unpublish, rollback, independent clinical validation, post-release safety monitoring | Final go/no-go before the feature flag is ever turned on for any real user |

Phase 1 is the only phase this branch implements. Phases 2-7 are described in `integration-plan.md` but not built here, and no production feature is implemented on this branch.
