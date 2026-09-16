# Alternative-medicine discovery scope map

Machine-readable form: `knowledge/chinese-herbal-oncology/alternative_modality_screening.json`. This is a **discovery/screening inventory**, not a clinical determination -- a `screen_decision` here never by itself authorizes patient-visible content.

## Source and methodology

Snapshot: `https://en.wikipedia.org/wiki/List_of_forms_of_alternative_medicine`, accessed 2026-09-17. Wikipedia's own evidence eligibility is `ineligible_tertiary_or_encyclopedia` (`source_registry.json`) -- it is used exclusively as a taxonomy/discovery aid, never to substantiate safety, efficacy, mechanism, cultural origin, or nutrition advice for any entry.

Every modality named on the page falls into one of two buckets, so that coverage is auditable without an unnecessary ~250-row transcription of the source page:

1. **Non-ingestible group exclusions** -- energy practices, manipulation/bodywork, divination/spiritual practices, devices/diagnostic systems/pseudo-diagnoses, exercise/movement/mind-body practices, and other procedures/devices. Each group has a documented reason (no ingestible botanical, fungus, tea, food, diet, culinary practice, dietary supplement, or plant-derived product) and named representative examples. Acupuncture, tai chi, qigong, moxibustion, massage, and other mind-body/manual practices are explicitly excluded here even where culturally associated with TCM, per instruction -- this proposal is scoped to ingestible interventions only.
2. **Ingestible candidates** -- every entry that does involve ingestion gets its own row with a `screen_decision`.

A third list, **brief-mandated additions**, covers categories the proposal brief explicitly requires screening for but which are not individually named as their own entries on the Wikipedia page (medicinal mushrooms as a category, Essiac, mistletoe, cannabis, laetrile/apricot kernels, Gerson-style diets, ketogenic diets, fasting-mimicking diets, raw-food/juice regimens, high-dose antioxidants).

## Key screening decisions

- **Chinese herbology / Chinese herbal medicine / Chinese food therapy** -- `in_scope_this_module` / `in_scope_this_module_nutrition_context_only`. The core subject of this proposal.
- **Medicinal mushrooms generally** -- `in_scope_this_module_herb_adjacent`, modeled with strict species/extract/product non-equivalence (see `card-ganoderma-mixed-cancers`, `card-psk-resected-gi-cancer`).
- **Ayurveda; Homeopathy/Bach flower remedies** -- `separate_module_link` to the sibling, currently unmerged proposals. Not conflated with TCM.
- **Japanese Kampo, Traditional Korean medicine, Tibetan medicine/Sowa Rigpa, Mongolian medicine, Unani, Siddha, African traditional medicine, Bush medicine, Curandero, Jamu, Vietnamese traditional medicine, Naturopathy, Western herbalism** -- `out_of_scope_adjacent`. Each is a distinct medical system or eclectic practice; none is relabeled as TCM, and none has a module in this repository yet.
- **Macrobiotic lifestyle** -- `avoid_as_cancer_treatment_diet` (no qualifying human oncology evidence; strict versions risk nutritional inadequacy).
- **Alkaline diet** -- `blocked_unsupported`.
- **Detoxification/foot detox/charcoal cleanse, coffee enema, colloidal silver, Jilly Juice, MMS, camel urine, black salve, Kambo** -- all `avoid`, each with a documented harm rationale independent of any cancer question.
- **Orthomolecular medicine/megavitamin therapy, high-dose antioxidant supplementation** -- `caution_pharmacist_review` (potential interference with radiotherapy/chemotherapy oxidative mechanisms).
- **Fasting (general), dietary supplements (generic)** -- routed to a separate specialist pathway or the herb/supplement interaction workflow respectively, never generic cancer nutrition content.

## Brief-mandated additions not individually named on the Wikipedia page

- **Essiac/Flor Essence** -- `adjacent_formula_blocked_as_cancer_treatment`, explicitly non-TCM (see `card-essiac-any-cancer`).
- **Mistletoe (injection vs. tea vs. food)** -- `separate_regulated_pathway`; anthroposophic medicine, not TCM; injectable extract is a distinct regulated pharmaceutical product in some jurisdictions, never equivalent to tea.
- **Cannabis/cannabinoids** -- `separate_regulated_pathway`; a regulated pharmacologic topic, not an ordinary herb or food, out of scope for this ingestible-herb/nutrition module.
- **Laetrile/amygdalin, apricot kernels** -- `avoid`; cyanide-toxicity risk, no efficacy evidence, never a food recommendation despite apricot kernels' food-adjacent appearance.
- **Gerson-style diet/protocol** -- `avoid`; coffee enemas, extreme restriction, large-volume raw juicing.
- **Ketogenic diet (therapeutic, cancer-specific), fasting-mimicking diets** -- `separate_specialist_pathway`; cannot become generic cancer nutrition content in this module.
- **Raw-food/juice-only regimens** -- `avoid_as_sole_dietary_pattern`; food-safety and malnutrition risk, especially during neutropenia.

## What this screen does not do

It does not add any patient-visible content for any screened item. Every `avoid`/`blocked_unsupported`/`separate_regulated_pathway`/`separate_specialist_pathway`/`out_of_scope_adjacent` decision here is a boundary marker, not a completed safety or evidence review -- a future dedicated module for any of these (e.g. a cannabis-in-oncology module, or a Kampo module) would need its own full source assessment, evidence cards, and approval gate, exactly like this one.
