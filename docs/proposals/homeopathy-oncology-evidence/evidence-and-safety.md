# Evidence and safety model

## Source hierarchy

1. Current government/regulator guidance, oncology guidance, and high-quality clinical-practice guidance (NCCIH, FDA, Cancer Research UK, Macmillan, MSK, Balneaves et al. CPG) -- for safety and baseline conclusions.
2. Current systematic reviews with transparent methods (Milazzo 2006, Wagenknecht 2022, Cochrane CD004845 -- flagged stale, search last run 2008) -- for evidence synthesis.
3. Relevant randomized human trials -- for exact intervention-and-outcome questions.
4. Nonrandomized human studies -- preliminary evidence only, with explicit confounding/bias notes.
5. Case reports -- primarily for safety signals or hypothesis generation, never efficacy.
6. Trial registries -- protocol and status only, never efficacy unless verified results are posted.
7. Narrative reviews, conference handouts, surveys, provider pages, and practitioner materials -- context or discovery leads only.
8. Cell and animal studies -- preclinical research only, never patient benefit.

A hospital affiliation, peer-review label, mechanistic hypothesis, statistical significance, or a positive abstract does not by itself establish clinical benefit. PubMed indexing does not imply methodological quality.

## Allowed states -- no autonomous "recommended," "effective," "proven," or "supported" state

| State | Meaning |
|---|---|
| `avoid` | Known or credibly suspected harm (typically treatment substitution/delay) outweighs any proposed benefit |
| `blocked_unsupported` | No qualifying evidence identified for the claimed use |
| `blocked_integrity` | The supporting publication is retracted, or otherwise integrity-compromised, and cannot be relied upon at all |
| `blocked_no_results` | The cited trial is withdrawn/terminated with no results posted |
| `insufficient_evidence` | Evidence exists but does not clear the bar for a claim (null/mixed/heterogeneous, high risk of bias) |
| `research_only` | Preliminary human or preclinical evidence; awareness only, never guidance |
| `clinician_discussion_only` | **Means specifically:** disclose an already-used product and its exact label to the oncology team. It never means a clinician is being prompted to recommend the product. |
| `general_education` | Factual/context information with no efficacy claim attached |

`clinician_discussion_only` cannot be reached by a card whose only cited sources are animal, in-vitro, case-report, narrative-review, conference-handout, provider-page, or registry-only evidence -- `scripts/validate_homeopathy_proposal.py`'s `validate_cards()` enforces this by source-type check, not just by convention.

## Modality and product taxonomy -- non-equivalence is structural, not a style note

Every card's `intervention` block must state, when known: formulation category (individualized classical vs. fixed protocol; single remedy vs. complex/combination product; high dilution, low dilution, mother tincture, topical botanical, mineral/chemical or animal-derived source, nosode, or unclear preparation), ingredients, potency **as a bibliographic study detail, never an instruction**, route (oral pellets/drops, mouth rinse, cream/ointment, injection, other), carrier/excipients, and co-interventions (lengthy consultation, herbs, supplements, acupuncture, counseling, diet, conventional supportive care). A `formulation_generalization_note` field is required on every card specifically to state what the result does and does not generalize to -- e.g. Cocculine's null CINV result says nothing about individualized classical homeopathy; a topical Calendula preparation's preliminary radiodermatitis signal says nothing about ultra-dilute remedies; mother-tincture Arnica and high-dilution Arnica are different interventions studied in different trials. A result for one exact formulation, route, or bundled consultation cannot be generalized to another.

## Forbidden claim language

Patient-facing text may never assert or imply: cure, treatment, prevention, tumor control, tumor shrinkage, or survival benefit from a homeopathic product; "side-effect free"; "non-toxic"; detox; blood purification; vague immune-boosting; or that homeopathy can replace, delay, interrupt, reduce the dose of, or justify refusing any standard oncology treatment. `scripts/validate_homeopathy_proposal.py` scans all patient-facing text fields for a defined forbidden-phrase list and fails the build if one appears (the validator's own list required rewording one internal draft sentence during this proposal's own build -- see the commit history -- which is itself a demonstration that the check works, not a bypass of it).

Homeopathic principles and terminology (e.g. potentization, succussion, "like cures like," miasm theory) are described neutrally and accurately as **beliefs or principles of the system**, kept structurally separate (a distinct `formulation_category`/theory-context framing, never merged into `evidence.summary`) from established biomedical mechanisms and clinical evidence.

## Product-quality and toxic-source-substance safety

A product is never labeled safe merely because it is called homeopathic. The local APHA handout audit (`source-assessment.md`) independently surfaced concrete precedent: *Aristolochia* species (aristolochic acid is a recognized human carcinogen and nephrotoxin, banned in multiple countries) used in an in-vitro preparation; kava and comfrey, both hepatotoxic and banned or restricted in several jurisdictions; the FDA's 2010-2017 Hyland's teething-tablet action over inconsistent belladonna dilution causing infant toxicity; and a cited study finding toxic organic substances, excessive heavy metals, or microbial contamination in more than 74 integrative-medicine preparations (Ben-Arye et al., per the handout). Every card's `safety.known_concerns` must speak to product-quality risk where the source material raises it, not only to the dilution/mechanism question.

## Prominent, structural care-delay warning

Every card carries two required, non-empty safety fields, checked by the validator on every single card regardless of state: `care_delay_warning` (homeopathy must never replace, delay, interrupt, reduce the dose of, or be used to refuse standard oncology care) and `standard_care_statement` (continue prescribed treatment; disclose the exact product label to the oncology team). This is not conditional on the card's evidence state -- even a `general_education` card carries both.

## Dual-approval gate; no elevation by a homeopathy-domain reviewer

No content is patient-visible until a card has **both** an oncology-qualified clinician or oncology pharmacist approval **and** an independent evidence-methodology reviewer approval, recorded against the same immutable content version. A qualified homeopathy-informed clinician may separately review whether the modality is described accurately (terminology, principles), but cannot elevate evidence certainty, approve an efficacy claim, or satisfy either required approval -- `check_publish_eligibility()` explicitly rejects a `homeopathy_domain_reviewer` role from filling a required slot and rejects any attempt to set an `elevates_certainty` or `overrides_required_approval` flag. AI, researchers, editors, administrators, product owners, and homeopathy practitioners cannot create, waive, imitate, or override the required approvals. Every card shipped in this proposal is a draft fixture with no approvals recorded, and the test suite proves each one fails the publish gate.

## Retraction, withdrawal, and integrity surveillance

Two of the highest-stakes items in this proposal were independently re-verified live rather than taken on faith from the brief:

- The 2020 Frass et al. NSCLC add-on-homeopathy survival paper (DOI 10.1002/onco.13548) **is retracted** (2025-11-24), after the Austrian Agency for Research Integrity found evidence of data falsification/manipulation (reported 2022); five co-authors had already requested withdrawal of their own authorship. `card-nsclc-addon-homeopathy-retracted` is `blocked_integrity`, and the validator structurally requires that state (or `avoid`) whenever a card cites this source.
- NCT02190539, the Banerji-protocol advanced-breast-cancer feasibility study, **is withdrawn** with reason "not able to recruit patients," no results posted. `card-banerji-protocol-breast-feasibility` is `blocked_no_results`, structurally enforced the same way.

Ongoing surveillance for corrections, retractions, expressions of concern, and registry-status changes is a Phase 6 concern (`integration-plan.md`), not something a static proposal branch can perform continuously -- but the contract (a `publication_status` field required on every source, and a validator rule tying `evidence_eligibility` to that status) is built now so Phase 6 has something to enforce against.
