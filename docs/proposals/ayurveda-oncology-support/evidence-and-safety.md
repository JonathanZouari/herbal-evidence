# Evidence and safety model

## Source hierarchy

1. Current guidelines, government/regulator evidence reviews, authoritative oncology safety resources (NCCIH, NCI PDQ, ESPEN, ACS, MSK herb monographs).
2. Systematic reviews and randomized human trials.
3. Nonrandomized human studies and single-arm pilots.
4. Narrative reviews, case reports, preclinical/animal work, classical texts, hospital service pages, clinic blogs, commercial pages, videos, testimonials — **context or discovery leads only, never sufficient alone for a patient efficacy claim.**

A hospital affiliation, peer-review label, mechanistic result, animal result, or traditional-use history does not by itself establish patient benefit. See `source-assessment.md` for how every supplied source was classified against this hierarchy.

## Allowed states (no autonomous "recommended" state exists)

| State | Meaning |
|---|---|
| `avoid` | Known or credibly suspected harm outweighs any proposed benefit in this context |
| `blocked_unsupported` | No qualifying evidence identified (e.g. commercial-only sourcing); registered so the gap is explicit, not silently filled |
| `insufficient_evidence` | Evidence exists but does not clear the bar for a claim (null trials, single conflicting study, formulation heterogeneity) |
| `research_only` | Preliminary human evidence exists; appropriate for research awareness, not clinical guidance |
| `clinician_discussion_only` | Evidence is meaningful enough to raise with the patient's own oncology team, never to act on unilaterally |
| `general_education` | Factual/context information (e.g. feasibility of a program) with no efficacy claim attached |

`scripts/validate_ayurveda_proposal.py` rejects any state outside this set, so an attempt to introduce a `recommended` (or any other unlisted) state fails validation rather than silently passing through.

## Card contract

Every cancer-context evidence card must carry: the exact cancer, disease state, treatment context, population, herb species and preparation (culinary food, tea, powder, crude herb, standardized extract, isolated constituent, and multi-herb formulation are treated as **non-equivalent** and must be distinguished), supportive-care purpose, evidence (with source references and certainty), limitations, safety fields, and state. No card may carry a `recommended_dose` field; the validator scans recursively for that key and fails the build if present, since dosing is a clinical decision this module never makes.

Positive, negative, null, and mixed findings for the same herb/context are recorded as **separate cards or explicit sub-fields**, never averaged or merged away — see `card-ginger-cinv-general` (mixed/positive) versus `card-ginger-ac-null` (null, specific regimen) in `knowledge/ayurveda-oncology/example_cards.json`.

## Forbidden claim language

Patient-facing text (and the fixtures that model it) may never assert: cure or treatment of cancer, "side-effect free," detox, blood purification, or vague immune-boosting claims. Traditional-use statements are kept in a separately labeled `ayurvedic_tradition_context` field, explicitly not evidence of biomedical efficacy or safety.

## Dual/triple approval gate

No content is patient-visible until:

- A herb/supportive-care card has **both** an oncology-qualified clinician or oncology pharmacist approval **and** a qualified Ayurveda-clinician approval, recorded against the **same immutable content version**.
- A diet template additionally has an **oncology-dietitian** approval.
- No approval may be granted by (or on behalf of) an AI system, researcher, editor, or administrator role — `check_publish_eligibility()` in the validator explicitly rejects those roles as approvers, and rejects any version mismatch between the approval and the content it's supposed to cover.

Every card and template shipped in this proposal is a **draft fixture with no approvals recorded**, and the test suite (`test_shipped_draft_fixtures_all_correctly_fail_the_publish_gate`) asserts they all correctly fail the publish gate — proving a draft cannot slip through by omission.

## Interactions, contraindications, and product-quality concerns

Each card's `safety` block is expected to cover, where applicable: drug/herb interactions, contraindications, toxicity, perioperative and transplant/immunotherapy timing, pregnancy/pediatric exclusions (out of scope for this adult-oncology-focused pass but must not be silently assumed safe), organ-function considerations, and — for any future non-culinary preparation — heavy-metal, adulteration, microbial, pesticide, and batch/identity concerns typical of unregulated herbal products. None of the example cards assert these are fully resolved; `review_status: pending_oncology_and_ayurveda_approval` on every card is the explicit marker that this analysis is not yet clinically signed off.

## Unknowns are unknown, not safe

Where an interaction or safety profile has not been established, cards say so explicitly rather than defaulting to "no known interactions." This is why every example card carries a nonempty `known_concerns` or `never_imply` list rather than an empty one.
