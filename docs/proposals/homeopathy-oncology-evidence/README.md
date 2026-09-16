# Proposal: Homeopathy oncology evidence and safety module

**Status:** proposal, evidence-model, and safety-governance branch (`proposal/homeopathy-oncology-evidence`). Not approval to ship a live medical feature, recommend a homeopathic remedy, or represent homeopathy as cancer treatment. Nothing here has been merged, deployed, or clinically approved.

## The evidence conclusion this proposal preserves

Current reliable evidence (NCCIH, Cancer Research UK, Macmillan, the FDA's homeopathic-products guidance, and the Milazzo 2006 and Wagenknecht 2022 systematic reviews) **does not show that homeopathy prevents, treats, controls, shrinks, or cures cancer.** The available supportive-care literature is heterogeneous, generally low quality, and insufficient to support any remedy recommendation. This module's purpose is to let the app **explain what was studied, what was not shown, the risks, and why certain claims are blocked** -- it is an evidence-education module, not a treatment-recommendation module.

## What this is

An **additive** module, `supportive_care_evidence`, separately named from and not conflated with the existing app or with the separate (currently unmerged) `ayurveda-oncology-support` proposal. It represents:

- **Cancer-context evidence cards** describing what was studied, the result, the limitations, the evidence status, and the safety implications for specific homeopathic products/preparations in specific cancer/treatment contexts.
- No nutrition content of any kind (see "Nutrition scope decision" below).

## What this is not

- Not a replacement for the existing app or the unmerged herbal/Ayurveda proposal. Terminology, tables, and claims are kept separate across all three.
- Not "recommended homeopathy." There is no autonomous `recommended`, `effective`, `proven`, or `supported` state anywhere in this system.
- Not remedy selection by cancer type, dosing, potency selection, frequency, repertorization, constitutional prescribing, or a self-treatment workflow.
- Not a claim that homeopathy can replace or permit delaying, interrupting, reducing the dose of, or refusing surgery, radiotherapy, chemotherapy, endocrine therapy, immunotherapy, targeted therapy, transplantation, palliative care, prescribed supportive medicines, or clinical follow-up.
- Not medical approval. Jonathan Zouari's confirmation on the eventual PR is a **product/merge gate**, distinct from and no substitute for the oncology/pharmacy and evidence-methodology approvals described in `evidence-and-safety.md`.

## Nutrition scope decision

**No nutrition content, diet templates, meal plans, or a "homeopathic cancer diet" module is included, and none should be added later under this proposal's scope.** No distinct, evidence-based homeopathic cancer diet was identified during source review. Some mixed integrative-care sources (e.g. the `jeenasikho.com`-style pages seen in the separate herbal proposal, and incidental dietary asides in homeopathy provider material) contain dietary advice that is not itself homeopathy and cannot be attributed to it. Any such incidental content is registered as `out_of_scope_adjacent_content`, never converted into patient guidance. This is a deliberate omission, not a gap to fill later inside this module -- general oncology nutrition, if it belongs anywhere, belongs in a nutrition-specific proposal with its own dietitian review, not bootstrapped from homeopathy source material.

## Documents in this proposal

| File | Purpose |
|---|---|
| `evidence-and-safety.md` | Allowed states, forbidden claims, modality/formulation taxonomy, dual-approval model |
| `source-assessment.md` | Classification of every supplied source, the duplicate-publication canonicalization, the retraction and withdrawn-trial findings, and the full audit of the local APHA handout |
| `clinical-evidence-map.md` | The 13 cancer-context evidence cards in prose |
| `integration-plan.md` | Additive domain/DB shape, roles, API concepts, RTL UI, surveillance/audit, compatibility with the unmerged Ayurveda proposal |
| `interview-decisions.md` | Open product/scope decisions and the safe defaults used in their absence |
| `implementation-phases.md` | Seven phases, each ending in a human review stop |
| `review-request-for-jonathan.md` | The specific ask for product/merge confirmation |

Machine-readable fixtures live under `knowledge/homeopathy-oncology/` and are exercised by `scripts/validate_homeopathy_proposal.py` and `backend/tests/test_homeopathy_knowledge_contract.py`.

## Relationship to the existing product and the unmerged Ayurveda proposal

The existing app scopes Herbal Evidence to a single herb and appetite improvement, human-reviewed before publication. The separate `ayurveda-oncology-support` proposal (branch `proposal/ayurveda-oncology-support`, **not yet merged into `main`**) extends that model to Ayurveda oncology supportive care and Indian nutrition. This proposal branches independently from `origin/main` rather than depending on that unmerged branch, per instruction, and reuses the same *generic* evidence/provenance/review/safety primitives (source registries, evidence cards, dual-approval gates, allowed-states enums) without conflating homeopathy with Ayurveda or herbal medicine -- they are different systems of belief and practice with different products, different literatures, and different risk profiles, and this module's registry explicitly marks herbal-medicine sources `out_of_scope_adjacent_content` rather than importing them.
