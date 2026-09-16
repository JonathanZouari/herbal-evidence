# Proposal: Ayurveda oncology supportive-care and Indian nutrition module

**Status:** proposal / knowledge-model branch (`proposal/ayurveda-oncology-support`). Not approved to ship as a live medical feature. Nothing here has been merged, deployed, or clinically approved.

## What this is

An **additive** module proposal, `supportive_care`, that extends Herbal Evidence beyond its current single-herb/appetite claim workflow to cover:

- Ayurveda oncology *supportive-care* context (never cancer treatment) for specific cancer/treatment/population combinations, represented as **evidence cards** rather than recommendations.
- General, flexible Indian-food-friendly **nutrition templates** for common on-treatment symptoms (poor appetite, nausea, mucositis, diarrhea, constipation, neutropenic food safety).

## What this is not

- Not a replacement for the existing app, its one-herb/appetite screens, routes, schemas, or tests. All of that is preserved untouched.
- Not a personalized herbal regimen, individualized meal plan, diagnosis, treatment selection, or dose calculator.
- Not a claim that any herb, Ayurvedic system, diet, cleanse, fast, or supplement treats, controls, prevents, shrinks, kills, or cures cancer.
- Not an autonomous "recommended" state for any herb — see `evidence-and-safety.md` for the allowed states.
- Not medical approval. Jonathan Zouari's confirmation on the eventual PR is a **product/merge gate**, distinct from and no substitute for the clinical approvals described below.

## Documents in this proposal

| File | Purpose |
|---|---|
| `evidence-and-safety.md` | Evidence hierarchy, allowed states, safety rules, dual-approval model |
| `source-assessment.md` | Classification of every supplied URL plus the audited local diet-chart PDF |
| `nutrition-content.md` | The six symptom-oriented diet templates, in prose |
| `integration-plan.md` | Additive domain/DB shape, roles, API concepts, RTL UI, surveillance/audit |
| `interview-decisions.md` | Open product/scope decisions log for this proposal, in the style of `docs/decisions.md` |
| `implementation-phases.md` | Seven phases, each ending in a human review stop |
| `review-request-for-jonathan.md` | The specific ask for product/merge confirmation |

Machine-readable fixtures and checks live under `knowledge/ayurveda-oncology/` and are exercised by `scripts/validate_ayurveda_proposal.py` and `backend/tests/test_ayurveda_knowledge_contract.py`.

## Relationship to the existing product

The current spec scopes Herbal Evidence to a single herb and appetite improvement, with a human researcher checking, editing, and approving every personalized response (see root `README.md`). This proposal keeps that model's spirit — human review before anything patient-visible — but widens the *evidence domain* it can eventually cover, under a stricter multi-role approval gate than the current one-researcher model, because supportive-care/nutrition claims for people undergoing active cancer treatment carry materially higher safety stakes (drug interactions, neutropenic food safety, malnutrition risk) than an appetite claim about a single herb.
