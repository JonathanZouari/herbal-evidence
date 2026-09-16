# Nutrition content proposal

Machine-readable form: `knowledge/ayurveda-oncology/diet_template_examples.json`. This document is the prose walkthrough of the same six templates and the design rules behind them.

## Design rules

- Templates are **general and flexible**, not personalized meal plans. No automatic calorie or protein calculator is included — the validator explicitly rejects a `calorie_calculator`/`protein_calculator` field.
- Oncology nutrition and food-safety guidance (ESPEN, ACS, NCI) is the primary source for each template's biomedical rationale; culturally familiar Indian foods and substitutions are layered on top; any Ayurvedic tradition framing is kept in its own labeled field, explicitly not presented as biomedical evidence.
- During active treatment, the priority order is adequate energy, protein, fluids, symptom tolerance, and food safety — in that order — never a restrictive elimination pattern.
- No template includes a herbal laxative, purgative, fasting, forced-vomiting, enema, *basti*, *virechana*, or juice-cleanse recommendation. Where the local diet chart's raw-juice/raw-sprout/restrictive pattern overlaps a template's territory (appetite, neutropenia), the template explicitly departs from it — see the `audit_note_from_local_diet_chart` field on the neutropenia template.

## The six templates

1. **Poor appetite / unintentional weight loss** — small frequent energy- and protein-dense meals/snacks, fortifying usual foods (ghee, nut pastes, dal, dairy or dairy-alternative) rather than eliminating food groups. Unsuitable where obstruction or dysphagia is present, or where a dietitian workup for rapid weight loss is already underway. No appetite-herb dose is included; any future ginger/appetite herb card would be linked as a separate, independently approved item, never folded into the food pattern.
2. **Nausea during treatment** — bland, small, frequent, low-aroma intake alongside prescribed antiemetics; never a substitute for them. Ginger is deliberately *not* dosed here — it is addressed only in the separate, still-unresolved evidence cards (`card-ginger-cinv-general`, `card-ginger-ac-null`).
3. **Oral mucositis / dry mouth / painful swallowing** — soft, moist, lukewarm textures; explicitly excludes anyone with a suspected aspiration risk or a diagnosed dysphagia plan, which must be deferred entirely to a speech-and-swallow therapist.
4. **Diarrhea during treatment** — temporary low-insoluble-fiber, low-fat pattern with oral fluid/electrolyte replacement; explicit red flags (fever, blood in stool, suspected neutropenic sepsis) route to urgent clinical contact rather than dietary self-management.
5. **Constipation, with obstruction screened first** — the template's first instruction is the obstruction red-flag screen; only if none apply does the flexible fiber/fluid pattern proceed. Explicitly excludes any laxative-herb or purgation practice.
6. **Food safety during neutropenia** — well-cooked-only pattern that directly supersedes traditional raw-juice/raw-sprout practice for the duration of neutropenia, regardless of tradition. This is the template most directly informed by (and contrasted against) the audited local diet chart.

## What is deliberately absent

- Any single "cancer diet" presented as sufficient on its own (the local diet chart's core defect).
- Any claim that following a template affects tumor behavior, recurrence, or survival — every template's stated goal is symptom tolerance, safety, or feasibility, never disease outcome.
- Any oncology-dietitian-unapproved template reaching a patient. Every template in this proposal is `review_status: draft_pending_oncology_dietitian_approval`.
