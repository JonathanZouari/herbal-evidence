# Nutrition content proposal

Machine-readable form: `knowledge/chinese-herbal-oncology/diet_template_examples.json`. This document is the prose walkthrough of the same eight templates and the design rules behind them.

## No cancer-specific diet

No universal "Chinese cancer diet" and no cancer-type-specific diet is included, because no current oncology guideline was identified in this pass supporting a distinct diet for any exact disease/treatment context. If such evidence is identified in a future pass, it would be added as its own guideline-cited template -- never inferred from survey, traditional-use, or provider-blog material. `scripts/validate_chinese_herbal_proposal.py` structurally enforces this: no diet template may carry a `cancer_context` or `cancer_type` field.

## Design rules

- Templates are symptom- or treatment-oriented, general, and flexible -- never a rigid menu, never an automatic individualized calorie/protein calculator.
- Oncology nutrition and food-safety guidance (ESPEN, NCI, ASCO) is the primary source for biomedical rationale; culturally familiar Chinese food examples are optional additions, gated on oncology-dietitian review; traditional Chinese dietary-therapy concepts (e.g. Pi-Wei/spleen-stomach framing, warming/cooling food concepts) are kept in their own labeled field, explicitly not biomedical rationale.
- Herbal soups, medicinal teas, medicated congee, mushrooms, ginseng, Astragalus, licorice, and formula sachets are never presented as ordinary food -- any such item is routed to the herb/supplement safety workflow in `example_evidence_cards.json` instead. The validator scans every template's food-example list for these keywords and fails the build if one appears.
- Spices appear only as optional flavoring when tolerated, never described as cancer-fighting, immune-boosting, chemopreventive, or tumor-toxic; concentrated/enhanced spice products are routed through the herb/supplement interaction workflow, not the nutrition templates.
- No fasting, juice-only regimens, raw-food protocols, coffee enemas, laxative cleanses, extreme restriction, or automatic supplement stacks appear in any template.

## The eight templates

1. **Poor appetite, early satiety, or unintentional weight loss** -- small frequent energy/protein-dense meals; congee, steamed egg, soft tofu with protein additions as examples; unsuitable with suspected obstruction or dysphagia (routed elsewhere).
2. **Nausea or vomiting during treatment** -- bland, low-aroma, small frequent intake alongside prescribed antiemetics; ordinary culinary ginger is a food/tolerance question, never an antiemetic substitute.
3. **Oral mucositis, dry mouth, chewing difficulty, or painful swallowing** -- soft, moist, lukewarm textures; excludes diagnosed dysphagia/aspiration risk, deferred to a speech-and-swallow plan.
4. **Diarrhea during treatment** -- temporary low-insoluble-fiber, low-fat pattern with fluid/electrolyte replacement; fever or blood in stool routes to urgent care, not diet management.
5. **Constipation, with obstruction and impaction red flags** -- explicit red-flag screen (no bowel movement/gas passage with worsening pain, distension with vomiting, severe colicky pain, suspected impaction) runs *before* any fiber/fluid advice; excludes any laxative herb or cleansing regimen.
6. **Altered taste or smell** -- trial-and-adjust flavor/temperature strategy; no concentrated spice/herb product presented as a taste-restoring intervention.
7. **Food safety during neutropenia, stem-cell transplantation, or substantial immunosuppression** -- well-cooked-only pattern; explicitly supersedes any raw-food/raw-juice tradition for the duration of the immunosuppressed window; medicinal mushrooms and raw herbal preparations are explicitly excluded during this period.
8. **Survivorship healthy eating, only when nutritionally stable** -- general ASCO-guideline-aligned healthy-eating pattern; explicitly not usable as a stand-in for any of the symptom-specific templates above, and not a recurrence-prevention claim for any specific food.

Every template's stated goal is symptom tolerance, safety, or general long-term health -- never a disease-outcome or cure claim. Every template is `review_status: draft_pending_oncology_dietitian_approval`, and the test suite proves each one fails the publish gate as shipped.
