# Proposal: Chinese herbal oncology evidence and nutrition module

**Status:** proposal, knowledge-model, safety-governance, and review branch (`proposal/chinese-herbal-oncology-support`). Not approval to ship a live medical feature, prescribe a formula, or represent traditional Chinese medicine (TCM) as a cancer treatment. Nothing here has been merged, deployed, or clinically approved.

## The evidence distinctions this proposal preserves

- Traditional use and cultural context are not proof of biomedical efficacy.
- Laboratory mechanisms are not proof of benefit in people.
- An isolated compound is not equivalent to a plant, food, formula, extract, injection, or commercial supplement.
- Supportive-care outcomes are not tumor-control outcomes.
- No herb, formula, mushroom, tea, supplement, or dietary pattern may replace or delay evidence-based oncology care.

## What this is

An **additive** module, `supportive_care_evidence`, separately named from and not silently merged into the existing app, the (unmerged) `ayurveda-oncology-support` proposal, the (unmerged) `homeopathy-oncology-evidence` proposal, or any conventional-treatment module. It represents:

- **Cancer-context evidence cards** stating what exact intervention was studied, what result was observed, the limitations, the evidence state, and the safety implications -- never a recommendation list.
- **Symptom- and treatment-oriented oncology nutrition templates** with optional, dietitian-gated, culturally familiar Chinese food examples -- never a "Chinese cancer diet."
- **A discovery-only alternative-medicine screening inventory**, built from a Wikipedia taxonomy snapshot, used to keep the boundary between this TCM-focused module and adjacent modalities/systems auditable.

## What this is not

- Not "recommended Chinese herbs for cancer." There is no autonomous `recommended`, `effective`, `proven`, `safe`, or `supported` state anywhere in this system.
- Not individualized formula selection, TCM pattern/syndrome diagnosis, tongue or pulse diagnosis, constitution matching, dosing, preparation instructions, treatment schedules, product shopping, or self-treatment workflows.
- Not a claim that TCM, a practitioner consultation, an herb, formula, mushroom, tea, food, diet, or supplement can replace or permit delaying, interrupting, reducing the dose of, or refusing surgery, radiotherapy, chemotherapy, endocrine therapy, immunotherapy, targeted therapy, transplantation, palliative care, prescribed supportive medicines, nutrition support, or clinical follow-up.
- Not medical approval. Jonathan Zouari's confirmation on the eventual PR is a **product/merge gate**, distinct from and no substitute for the oncology/pharmacy, evidence-methodology, TCM-practitioner, and (for nutrition) oncology-dietitian approvals described in `evidence-and-safety.md`.

## Documents in this proposal

| File | Purpose |
|---|---|
| `evidence-and-safety.md` | Allowed states, forbidden claims, intervention/identity taxonomy, quadruple-approval model |
| `source-assessment.md` | Classification of every supplied source (including the Essiac, PMC11734505, Memorial Healthcare System, and PMC5073821 special-handling requirements) plus additional authoritative anchors |
| `clinical-evidence-map.md` | The 21 cancer-context evidence cards in prose |
| `alternative-medicine-scope-map.md` | The Wikipedia-derived discovery screen: methodology, group exclusions, and individual ingestible-candidate decisions |
| `nutrition-content.md` | The 8 symptom-oriented diet templates and the "no cancer-specific diet" policy |
| `integration-plan.md` | Additive domain/DB shape, roles, API concepts, RTL UI, surveillance/audit, compatibility with the other unmerged proposals |
| `interview-decisions.md` | Open product/scope decisions and the safe defaults used in their absence |
| `implementation-phases.md` | Seven phases, each ending in a human review stop |
| `review-request-for-jonathan.md` | The specific ask for product/merge confirmation |

Machine-readable fixtures live under `knowledge/chinese-herbal-oncology/` and are exercised by `scripts/validate_chinese_herbal_proposal.py` and `backend/tests/test_chinese_herbal_knowledge_contract.py`.

## Relationship to the existing product and the other unmerged proposals

Neither `proposal/ayurveda-oncology-support` nor `proposal/homeopathy-oncology-evidence` is merged into `origin/main` as of this branch's creation (verified via `git log origin/main`). This proposal branches independently from `origin/main`, does not depend on, cherry-pick, or reference specific unmerged commits from either sibling branch, and reuses only the same *generic* evidence/provenance/review/safety primitive shapes (source registries, evidence cards, immutable-version-plus-approval-record pattern, allowed-states enums) they each independently established -- while keeping TCM, Ayurveda, and homeopathy as clearly separated medical systems with their own terminology, tables, and approval-role sets. Should any of these branches merge before another, no foreign-key or terminology dependency exists between them.

## Language-access limitation, disclosed honestly

No claim of a comprehensive Chinese-language literature search is made. ChiCTR, SinoMed, CNKI, and Wanfang were not searched in this pass, and no qualified bilingual clinical reviewer was available to interpret Chinese-language primary sources. This is recorded as an open item (`interview-decisions.md`, H2-007) rather than papered over.
