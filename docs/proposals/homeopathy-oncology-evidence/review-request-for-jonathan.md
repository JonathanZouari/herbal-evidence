# Review request: Jonathan Zouari product/merge confirmation

This proposal branch (`proposal/homeopathy-oncology-evidence`) is ready for your product/merge review. This is **not** a request for clinical or evidence-methodology sign-off -- the module cannot go live without separate oncology-clinician/pharmacist and independent evidence-methodology approvals as described in `evidence-and-safety.md`, and none of that has happened yet. A homeopathy-domain review may separately confirm the modality is described accurately, but cannot substitute for either required approval.

## What you're being asked to confirm

1. **Scope:** that `supportive_care_evidence` -- an evidence-education module explaining what was and was not shown about homeopathy in oncology, never a recommendation engine -- is the right next area to propose, kept structurally separate from the existing app and from the sibling (unmerged) Ayurveda proposal.
2. **Safety boundaries:** that the allowed-states model (including `blocked_integrity` and `blocked_no_results`, which the Ayurveda proposal doesn't need), the forbidden-claim list, the formulation non-equivalence rules, and the dual-approval gate in `evidence-and-safety.md` match your intent -- in particular, that a homeopathy-domain reviewer can never elevate evidence certainty or satisfy a required approval.
3. **The retraction and withdrawal findings:** that `card-nsclc-addon-homeopathy-retracted` (`blocked_integrity`, the 2020 Frass et al. NSCLC paper retracted 2025-11-24 for data falsification) and `card-banerji-protocol-breast-feasibility` (`blocked_no_results`, NCT02190539 withdrawn with no results) are handled correctly -- both were independently re-verified live for this proposal, not taken on faith.
4. **The local APHA handout's disposition:** that it was found, fully audited, and its most safety-relevant claim -- a retrospective case series describing homeopathy as a metastatic patient's sole anti-cancer treatment with a "no adverse effects" claim -- was surfaced as its own `avoid`-state card (`card-psorinum-sole-treatment-case-series`) rather than reproduced as evidence. See `source-assessment.md`.
5. **The nutrition omission:** that deliberately adding **no** diet/nutrition content to this module -- because no distinct evidence-based homeopathic cancer diet was identified -- is correct, rather than filling the gap with generic oncology nutrition (which belongs, if anywhere, in its own dietitian-reviewed proposal).
6. **Open items in `interview-decisions.md` (H-001, H-002, H-004, H-007, H-009, H-010):** staff-only-vs-patient-education launch scope, jurisdiction, reviewer-credentialing process, and the remaining literature items still `pending_manual_verification`.

## What is explicitly not being asked

- Not asking you to approve any patient-visible content -- none exists; every card is a draft fixture the test suite proves cannot pass the publish gate.
- Not asking for clinical or evidence-methodology sign-off -- that requires the two required credentialed roles, independent of this review.

## A note on how this reached you

You're being asked because this repository is a fork of `JonathanZouari/herbal-evidence` (confirmed via GitHub repository metadata) -- the same reason you were asked to review the sibling Ayurveda proposal (PR #1). You are not currently a collaborator on this fork, so this PR is opened without a formal reviewer request; you'll be notified via an @-mention comment instead, consistent with how PR #1 was handled.

## Next step if confirmed

Phase 2 (durable machine-readable contracts / additive database foundation) per `implementation-phases.md`, with its own review stop before Phase 3.
