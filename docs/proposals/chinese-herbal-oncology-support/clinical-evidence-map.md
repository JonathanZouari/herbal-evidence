# Clinical evidence map

Machine-readable form: `knowledge/chinese-herbal-oncology/example_evidence_cards.json` (21 cards). Prose summary, grouped as in the proposal brief.

## System-wide and heterogeneous claims

1. **Any cancer, TCM/Chinese herbal medicine generally** (`blocked_unsupported`) -- no system-wide efficacy claim is justified; never replace or delay oncology care.
2. **Mixed advanced/palliative cancers, heterogeneous formulas, QoL/survival/toxicity** (`insufficient_evidence`) -- Chung et al. 2015's possible QoL signal is undercut by contributory-review methodology limits and a search that stopped in 2014.

## Named formula/species cards

3. **Advanced NSCLC + platinum chemotherapy, Astragalus-containing formulas** (`research_only`) -- McCulloch 2006's positive pooled signal (RR 0.67 death at 12mo, RR 1.34 tumor response) is explicitly flagged by its own authors as needing confirmation in well-designed trials; never mapped to "Astragalus alone."
4. **Cancer-related fatigue, American ginseng (*Panax quinquefolius*)** (`clinician_discussion_only`) -- ASCO-SIO 2024 conditional, low-quality-evidence recommendation for active treatment only; species-specific, never inherited by Asian ginseng.
5. **Cancer-related fatigue, Asian/Korean ginseng (*Panax ginseng*)** (`insufficient_evidence`) -- does not inherit the American-ginseng guideline endorsement; no dedicated literature review performed in this pass.
6. **Mixed cancers, Ganoderma/reishi extract** (`insufficient_evidence`) -- Cochrane's uncertain, small, Chinese-population-only evidence; does not support first-line use; never generalized to culinary reishi.
7. **Resected gastric/colorectal cancer, PSK (Trametes versicolor extract)** (`research_only`) -- historical Japanese adjuvant-regimen evidence, era- and regimen-limited; PSK is a standardized pharmaceutical, never equated with culinary turkey-tail or generic mushroom powder.
8. **Hepatocellular/GI cancers, YIV-906/PHY906 (investigational, from Huang Qin Tang)** (`research_only`) -- standardized investigational product; registry verification pending; never equated with a homemade decoction.

## Preclinical and immunotherapy-context cards

9. **PMC11734505's immunotherapy-formulation claims (breast, thyroid, osteosarcoma, colorectal, liver)** (`preclinical_research_only`) -- predominantly cell/animal/mechanistic; the source's unsafe surgery-spread statement is explicitly recorded and refused.
10. **Immunotherapy patients, immune-active herbs generally** (`insufficient_evidence`, safety-caution record) -- "boosting immunity" claims do not establish benefit and may be clinically inappropriate with checkpoint inhibitors, transplantation, or autoimmune disease.

## Adjacent-formula and toxicity records

11. **Any cancer, Essiac/Flor Essence** (`blocked_unsupported`) -- explicitly non-TCM; no controlled human evidence; Flor Essence has an animal-model tumor-promotion signal.
12. **Thunder god vine (*Tripterygium wilfordii*), triptolide, celastrol** (`avoid` for raw herb/self-use; `preclinical_research_only` for isolated compounds) -- documented multiorgan toxicity for the raw herb, kept distinct from investigational-compound preclinical promise.
13. **Aristolochia/Asarum and aristolochic-acid substitution risk** (`avoid`) -- IARC Group 1 carcinogen, documented nephrotoxin; structural `avoid` enforced by the validator on any card mentioning these ingredient markers.
14. **Multiple myeloma + bortezomib, green tea/EGCG** (`clinician_discussion_only`) -- NCI-documented interaction concern; ordinary beverage exposure and concentrated extract kept as distinct certainty levels.
15. **Injectable proprietary Chinese medicines (Aidi, Shenqi Fuzheng, Kanglaite, Compound Kushen, Brucea javanica oil)** (`research_only`, registered as a category) -- never foods or interchangeable "herbs"; each requires its own product-specific review.
16. **Animal/mineral-containing patent medicines (HuaChanSu, Pien Tze Huang)** (`out_of_scope_adjacent`) -- explicitly kept outside the herb-recommendation model pending dedicated toxicology/identity review.

## Culinary spice non-equivalence cards

17. **Turmeric/curcumin** (`insufficient_evidence`) -- food, extract, and piperine-enhanced formulation kept as three distinct records; no cancer claim; liver-injury signal noted for highly bioavailable formulations; preliminary oral-mucositis signal kept as its own formulation-uncertain sub-question.
18. **Ginger** (`insufficient_evidence`) -- food/tea vs. concentrated extract kept distinct; no cancer-protection claim; nausea-adjunct evidence uncertain, never a prescribed-antiemetic substitute.
19. **Garlic** (`insufficient_evidence`) -- food vs. supplement kept distinct; no stomach-cancer risk reduction shown; supplements carry a bleeding-risk flag.

## Caribbean-survey-derived cards

20. **Graviola/soursop** (`insufficient_evidence`) -- fruit/leaf/bark/seed/extract kept as distinct exposure levels; MSK-documented annonacin/atypical-Parkinsonism signal for concentrated leaf/seed/bark forms.
21. **PMC5073821 observational-use-survey record** (`general_education`) -- registered strictly as a use/belief/disclosure-pattern record; explicitly not converted into a cancer-type recommendation for any reported item.

## What every card answers

Per card: exact cancer/stage/disease-state/population/conventional-treatment context; cancer-control vs. supportive-symptom purpose; exact formula/product/species/plant-part/preparation/route/batch; comparator, sample size, allocation, blinding, duration, co-interventions; prespecified/objective-vs-patient-reported outcomes; result direction (positive/null/negative/mixed/conflicting/unavailable/preclinical/integrity-blocked); risk-of-bias and generalizability concerns; publication-integrity status; what was **not** shown; product-quality/toxicity/interaction/food-vs-supplement/care-delay/cultural-attribution safety issues; and the safer action (continue standard care, use proven supportive care, see an oncology dietitian, disclose the exact product to the oncology team). `scripts/validate_chinese_herbal_proposal.py` enforces the presence of every one of these fields on every card.
