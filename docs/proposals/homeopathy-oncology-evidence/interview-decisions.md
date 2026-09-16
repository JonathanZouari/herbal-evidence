# Interview decisions and safe defaults

This proposal was built non-interactively (no blocking questions were asked before creating the branch, per instruction) using the safest defaults below. Every assumption is recorded here rather than silently baked into the design.

## Questions that would materially change the proposal, and the default taken

| # | Question | Safe default applied | Status |
|---|---|---|---|
| H-001 | Should a future first release be staff-only, or may it show carefully reviewed patient education? | **Staff-only** for the first release; patient education is Phase 6, its own separately gated review. | open -- needs product confirmation |
| H-002 | What launch jurisdictions must be covered (Israel, India, UK, US, other)? | None assumed; the FDA and CCRH India sources are registered for regulatory *context*, not as a jurisdiction commitment. Patient-facing claim language must be re-checked per actual launch jurisdiction before Phase 6. | open -- needs product decision |
| H-003 | Is the first scope adults only? | **Yes, adults only.** No card in this proposal addresses pediatric dosing/use, even though the source material (e.g. the German pediatric survey, parental-use statistics in the local handout) discusses children. | default, adults-only |
| H-004 | Who will fill the oncology/pharmacy, evidence-methodology, and optional homeopathy-domain review roles? | Unfilled; recorded as **TBD** in every approval record's schema. No card can pass the publish gate until named. | open -- needs product decision |
| H-005 | Has the Ayurveda proposal been merged, or should this remain independent? | **Confirmed not merged** (`origin/main` has no Ayurveda content as of this branch's creation; the Ayurveda branch is a separate open PR). This proposal branches independently from `origin/main` and does not depend on, cherry-pick, or reference specific unmerged commits from `proposal/ayurveda-oncology-support`. | resolved for this branch; re-check before Phase 2 in case Ayurveda merges first |
| H-006 | Can the exact local APHA handout be made available if not found? | Not needed -- **the exact file was found** at `~/Downloads` and fully audited (see `source-assessment.md`). | resolved |

## Additional open items surfaced during source review

| # | Decision | Rationale | Status |
|---|---|---|---|
| H-007 | Six-plus literature items (PMC1948867, the JAIMS-style items if any, the Traumeel replication trials, the Calendula/radiodermatitis current-guideline check, and the Arnica perioperative synthesis) remain `pending_manual_verification` and are not cited to support any claim. | Full-text re-verification of every item was out of scope for a single non-interactive pass; two highest-stakes items (the retraction, the withdrawn trial) and the duplicate-publication claim were verified live instead, since they determine which `blocked_*` states apply. | open -- literature-review pass needed before Phase 4 |
| H-008 | The handout's "Kalra 2016" cure/prevented/palliated/improved percentage table was **not** reproduced anywhere in this proposal. | The primary source for that table was not independently located; presenting cure/prevention percentages from an unverified table is exactly the pattern this module exists to block. | resolved -- deliberately omitted |
| H-009 | No jurisdiction/regulatory-claims framework has been chosen (see H-002). | Not specified in the proposal brief. | open |
| H-010 | Exact credentialing/verification process for the `oncology_clinician_or_pharmacist`, `evidence_methodology_reviewer`, and `homeopathy_domain_reviewer` roles is undefined. | Not specified in the proposal brief; mirrors the same open item in the sibling Ayurveda proposal. | open -- needs product + legal decision before Phase 4 |
| H-011 | Reviewer identity for the pull request: "Jonathan Zouari" is named as the confirming reviewer. This repository is in fact a fork of `JonathanZouari/herbal-evidence` on GitHub (confirmed via repository metadata), so the identity is real, but he is not a collaborator on this fork and no reviewer request could be issued without either adding him as a collaborator or using a comment mention -- the same situation resolved for the sibling Ayurveda PR. | Avoid guessing a handle; the identity was in fact verifiable this time via fork metadata, unlike the initial Ayurveda pass. | resolved -- use the same comment-mention approach as PR #1 unless told otherwise |
| H-012 | No nutrition/diet content was added, and this is a deliberate, permanent omission for this module (see root proposal README). | No distinct evidence-based homeopathic cancer diet was identified; incidental diet content in mixed sources is not homeopathy and is out of scope. | resolved -- by design, enforced by `NoNutritionContentTests` in the contract test suite |

Do not block Phase 1 completion on H-001, H-002, H-004, H-007, H-009, or H-010 -- they are recorded here and in the pull request for Jonathan's and future reviewers' attention, per instruction to use safe defaults and continue.
