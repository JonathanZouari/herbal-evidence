# Review request: Jonathan Zouari product/merge confirmation

This proposal branch (`proposal/ayurveda-oncology-support`) is ready for your product/merge review. This is **not** a request for clinical sign-off — the module cannot go live without separate oncology-clinician/pharmacist, Ayurveda-clinician, and oncology-dietitian approvals as described in `evidence-and-safety.md`, and none of that has happened yet.

## What you're being asked to confirm

1. **Scope:** that `supportive_care` as an additive module (Ayurveda oncology supportive-care evidence cards + general Indian-food nutrition templates) is the right next area for Herbal Evidence to extend into, alongside the existing one-herb/appetite workflow.
2. **Safety boundaries:** that the allowed-states model, forbidden-claim list, and dual/triple-approval gate in `evidence-and-safety.md` match your intent — in particular, that there is deliberately no "recommended" state and no AI/staff bypass of clinical approval.
3. **Source handling:** that excluding commercial marketing pages from efficacy support (`source-assessment.md`) and flagging six literature sources as `pending_manual_verification` rather than fabricating verified-looking summaries is the right call.
4. **The local diet chart's disposition:** that auditing and setting aside its restrictive/raw-food/supplement-dosing pattern (rather than adapting it into a template) is correct — see the safety-audit table in `source-assessment.md`.
5. **Open items in `interview-decisions.md` (P-007 through P-010):** literature re-verification, jurisdiction, credential-verification process, and your exact GitHub handle for reviewer assignment.

## What is explicitly not being asked

- Not asking you to approve any patient-visible content — none exists yet; everything shipped here is a draft fixture that the test suite proves cannot pass the publish gate.
- Not asking for clinical sign-off — that requires the three credentialed roles described above, independent of this review.

## Next step if confirmed

Phase 2 (additive database/domain foundation) per `implementation-phases.md`, with its own review stop before Phase 3.
