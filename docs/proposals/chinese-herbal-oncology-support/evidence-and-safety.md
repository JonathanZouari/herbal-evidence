# Evidence and safety model

## Source hierarchy

1. Current oncology guidelines, government/regulator evidence reviews, pharmacovigilance sources, and official nutrition guidance (NCCIH, NCI PDQs, FDA-equivalent regulators, ESPEN, ASCO, IARC) -- for baseline safety and care standards.
2. Current systematic reviews with transparent methods and risk-of-bias assessment (Milazzo-style rigor; Cochrane CD007731; Chung et al. 2015, flagged stale).
3. Registered randomized human trials of an exact, reproducible intervention for the exact clinical question (McCulloch 2006, Barton 2013).
4. Nonrandomized human studies -- preliminary evidence only, explicit confounding/bias notes.
5. Case reports -- safety signals or hypothesis generation only.
6. Trial registries -- protocol/status only, never efficacy unless verified results are posted.
7. Narrative reviews, hospital/provider pages, patient-advocacy pages, conference abstracts, commercial pages, and encyclopedias -- context or discovery leads only.
8. Cell, animal, network-pharmacology, molecular-docking, omics, and in-silico studies -- preclinical research only, never patient benefit.

PubMed/PMC indexing, peer review, a university/hospital affiliation, use in a Chinese hospital, regulatory availability elsewhere, statistical significance, or a plausible mechanism do not by themselves establish clinically meaningful benefit. `scripts/validate_chinese_herbal_proposal.py` structurally enforces this: any card whose cited sources are entirely tertiary/commercial/provider/advocacy/narrative-review types cannot carry a state stronger than `research_only`/`insufficient_evidence`/`avoid`/`general_education` -- it can never reach `clinician_discussion_only` on that basis alone.

## Allowed states -- no autonomous "recommended," "effective," "proven," "safe," or "supported" state

| State | Meaning |
|---|---|
| `avoid` | Known or credibly suspected harm outweighs any proposed benefit (e.g. aristolochic acid, thunder god vine self-use) |
| `blocked_unsupported` | No qualifying evidence identified for the claimed use (e.g. TCM as a system-wide cancer treatment, Essiac) |
| `blocked_integrity` | The supporting publication is retracted or otherwise integrity-compromised |
| `insufficient_evidence` | Evidence exists but does not clear the bar for a claim |
| `preclinical_research_only` | Cell/animal/mechanistic evidence only; human inference prohibited |
| `research_only` | Preliminary human evidence, or preclinical evidence approaching human relevance; awareness only |
| `clinician_discussion_only` | **Means specifically:** disclose an already-used or contemplated exact product to the oncology team for a risk-benefit and interaction review. It is not an instruction to start the product. |
| `general_education` | Factual/context information with no efficacy claim attached |
| `out_of_scope_adjacent` | Registered for completeness (e.g. animal/mineral patent medicines) but explicitly outside this module's herb-recommendation model pending dedicated review |

Even where "a current authoritative regulator and oncology guideline recognize the exact standardized intervention for the exact jurisdiction and indication" (per the proposal brief's own carve-out), the resulting content is presented only as **jurisdiction-specific clinician information, never self-treatment advice** -- see `card-psk-resected-gi-cancer`.

## Intervention and identity taxonomy -- non-equivalence is structural

Every card's `intervention` block requires: cultural system and origin (TCM vs. Kampo vs. Korean medicine vs. another tradition vs. Western herbalism vs. commercial supplement vs. unclear); exact formula name in pinyin and Chinese characters when reliable, plus English translation; whether classical, modified, individualized, fixed, proprietary/patent, hospital-made, or investigational; every known ingredient with accepted Latin name, plant part, and Chinese materia-medica name; explicit flagging of non-botanical ingredients (fungi, minerals, insects, animal products) so they are never mislabeled "herbs"; preparation, route, and manufacturer/batch/jurisdiction when known; and co-interventions. A required `non_equivalence_note` field on every card states what the finding does and does not generalize to.

Concretely enforced non-equivalences in this proposal's fixtures: American ginseng (*Panax quinquefolius*) never inherits evidence from Asian ginseng (*Panax ginseng*); PSK (a Japanese pharmaceutical-grade *Trametes versicolor* extract) never inherits from or lends evidence to culinary turkey-tail mushroom or generic supplements; YIV-906/PHY906 (a standardized investigational product) never equated with a homemade Huang Qin Tang decoction; culinary turmeric, curcumin extract, and piperine-enhanced curcumin are three separate records; culinary ginger and concentrated ginger product are two separate records; food garlic and garlic supplement are two separate records; ordinary green tea beverage and concentrated EGCG extract carry different interaction certainty; and soursop/graviola's fruit, leaf, bark, seed, and extract forms carry different (and in the concentrated forms' case, materially higher) risk.

## Forbidden claim language

Patient-facing text may never assert or imply: cure, treatment, prevention, tumor control, or survival benefit; "side-effect free"; "non-toxic"; detox; blood purification; vague immune-boosting; "cancer-fighting," "anti-cancer spice," or "toxic to cancer cells" framing; or that a traditional intervention can replace or delay standard oncology care. The validator's forbidden-phrase scan deliberately exempts each card's `safety.never_imply` field (a staff-facing registry of banned phrases, quoting them to document what must not appear elsewhere is not the same as using them) -- everywhere else, the same phrases are rejected. This distinction itself needed two rounds of fixture wording correction during this proposal's own build (see commit history), which is evidence the check functions as intended rather than being a rubber stamp.

## Product-quality, toxic-ingredient, and substitution safety

A product is never labeled safe merely because of a long history of use, a food-like appearance, a "natural" label, hospital use in another country, or sale as a supplement. This proposal's fixtures encode specific, independently verified high-risk findings: **aristolochic acid** (IARC Group 1 human carcinogen, documented nephrotoxin, with a real species-substitution/adulteration risk even when not labeled) is a structural `avoid` -- the validator scans ingredient text for `Aristolochia`/`Asarum`/aristolochic-acid markers and fails the build if a matching card is not `avoid`. **Thunder god vine** (*Tripterygium wilfordii*) raw herb/extract carries documented multiorgan toxicity and is `avoid` for self-use, with its isolated investigational compounds (triptolide, celastrol) kept in a separate `preclinical_research_only` record. **Injectable proprietary Chinese medicines** (Aidi, Shenqi Fuzheng, Kanglaite, Compound Kushen, Brucea javanica oil) are registered as a category requiring individual, product-specific review -- never pooled, never treated as an oral herb equivalent. **Animal- and mineral-containing patent medicines** (HuaChanSu/toad-venom-derived products, Pien Tze Huang) are explicitly excluded from the herb-recommendation model pending dedicated toxicology and identity review; the validator flags any card whose ingredient text contains a known non-botanical marker (fungus, toad, musk, gallstone) that lacks an explicit `non_botanical_ingredients` classification.

## Prominent, structural care-delay warning

Every card carries two required, non-empty safety fields checked on every single card regardless of state: `care_delay_warning` and `standard_care_statement`.

## Quadruple-approval gate (triple for herb/formula content, oncology-dietitian for nutrition)

No herb/formula content is patient-visible until a card has an oncology-qualified clinician or oncology pharmacist approval, an independent evidence-methodology reviewer approval, **and** a properly credentialed Chinese medicine practitioner approval (for the intended launch jurisdiction), all on the same immutable content version. No diet template is patient-visible until it separately has an oncology-dietitian approval. `check_publish_eligibility_card()`/`check_publish_eligibility_diet()` enforce that **no role may satisfy a slot it is not named for** -- a TCM practitioner cannot fill the oncology/pharmacy or evidence-methodology slot, and cannot substitute for an oncology dietitian on a nutrition template, exactly matching the brief's "a TCM practitioner cannot substitute for an oncology dietitian, pharmacist, oncologist, or evidence reviewer." AI, researchers, editors, administrators, product owners, and practitioners of any kind cannot create, waive, imitate, or override these approvals. Every card and template shipped in this proposal is a draft fixture with no approvals recorded, and the test suite proves each one fails the publish gate.

## Special-handling requirements this proposal's validator enforces by name

- **Essiac** is structurally kept non-TCM (`validate_essiac_non_tcm()` fails the build if its `cultural_system` field doesn't explicitly say "not TCM") and structurally `blocked_unsupported`.
- **PMC11734505** cannot, alone, support anything stronger than `preclinical_research_only` (`validate_pmc11734505_handling()`), and its verified unsafe surgery-related statement is an explicit forbidden phrase, never reproduced.
- **The Memorial Healthcare System spice page** must be registered `evidence_eligibility=provider_education` (`validate_mhs_spice_page_handling()`) and can never alone justify an efficacy, dosing, or interaction-management claim.
- **PMC5073821** must be registered `evidence_eligibility=observational_use_survey` (`validate_pmc5073821_handling()`), and any card relying on it alone (or alongside only the MSK graviola monograph) is capped at a non-efficacy state.
- **Wikipedia** (`src-wikipedia-altmed-list`) is permanently `ineligible_tertiary_or_encyclopedia` and cannot support any claim (`validate_wikipedia_ineligible()`).
