# Source assessment

Machine-readable form: `knowledge/ayurveda-oncology/source_registry.json`. This document is the human-readable narrative version, plus the full audit of the local diet-chart PDF.

## Local diet chart — found and audited

**File:** `LIFE SUPPORT DIET for Cancer Patients - OPD Diet Chart - LIFE SUPPORT DIET for Cancer Patients - OPD Diet Chart.pdf`, found on the local Desktop. **Not** registered as `awaiting_upload` — it was located and read.

- **Format:** 2-page bilingual (English/Hindi) PDF handout, structured as three "Plates."
- **Author / institution / publication date / version:** none present anywhere in the extracted text. No letterhead, byline, clinic name, or revision marker was recoverable from the PDF's text layer. Provenance is therefore **unverified** — it reads as a patient/caregiver handout of the kind circulated informally (e.g. via WhatsApp) rather than an institutionally authored clinical document.
- **Traditional vs. clinical vs. commercial:** The document is framed in absolute, unqualified terms ("can work wonders," "you won't need the other plates") rather than as either a sourced traditional text or a cited clinical guideline. It contains no citations, no clinician sign-off, and no commercial branding/purchase links — it does not fall cleanly into any of the three categories and is treated here as an **unverified lay handout**, tier 4, not eligible for any efficacy claim.

### Content summary

- **Plate A ("The Rescuer"):** soaked raw nuts (almonds, walnuts, figs); raw leafy greens (radish, mint, coriander, spinach, rocket, lettuce, kale, lemongrass, wheatgrass, spirulina); steamed vegetables; specific fruits; salad vegetables; multiple daily raw vegetable/fruit juices and soups; a "green juice" and "red juice" taken in specified volumes multiple times daily; raw legume/bean sprouts; herbal teas (fennel/coriander/cumin decoction; plain green tea); a suggestion to add spirulina, moringa, and "Green Essentials" capsules "for better results."
- **Plate B ("The Oxymoronic"):** boiled rice/millets, missi roti with raw fenugreek leaves — explicitly framed as only to be eaten after Plate A, in smaller quantity.
- **Plate C (Strictly Prohibited):** dairy and dairy products, refined sugar, packaged/processed/fried/bakery products, oats, corn flakes, aerated drinks, cashews and pistachios specifically, and non-vegetarian food — with an instruction to avoid it "completely."

### Safety audit against oncology-nutrition and food-safety concerns

| Concern | Finding |
|---|---|
| **Malnutrition risk** | Plate C eliminates dairy and all non-vegetarian protein sources outright, with no compensating protein target elsewhere in the document. For a cancer patient — a population at elevated risk of treatment-related malnutrition and sarcopenia — a blanket elimination of two major protein/calorie categories with no individualized calorie/protein plan is a credible malnutrition risk, not a neutral preference. |
| **Food safety / neutropenia** | Raw soaked nuts, raw sprouted legumes (green lentils, chana, bean sprouts, fenugreek), and multiple raw vegetable/fruit juices taken several times daily are exactly the item categories oncology food-safety guidance (ACS, ESPEN) flags as higher infection risk during neutropenia. The document contains **no neutropenia screening or caveat** before recommending these items. |
| **Diabetes** | Multiple sweet-fruit juices (pomegranate, apple, beetroot) taken multiple times daily, plus jaggery-adjacent fruit-forward "red juice," with no glycemic guidance — a concern for any patient with diabetes or steroid-induced hyperglycemia (common during cancer treatment). |
| **Renal / hepatic / cardiac restrictions** | No screening or caveats for renal potassium/fluid restriction (multiple potassium-rich juices and coconut water in volume), hepatic protein handling, or cardiac fluid/sodium restriction. |
| **Dysphagia / mucositis** | Raw, fibrous, and acidic items (raw salad vegetables, citrus-adjacent juices) are contraindicated during mucositis or swallowing difficulty; the document does not address this population subgroup at all. |
| **Obstruction** | High-fiber raw vegetables and legumes in volume are inappropriate during partial bowel obstruction; no screening present. |
| **Diarrhea** | The heavy raw-produce, high-fiber, juice-forward pattern could worsen treatment-related diarrhea; no branch or caveat for this symptom exists in the document. |
| **Interactions** | No acknowledgment that spirulina, moringa, or concentrated fennel/coriander/cumin decoctions could interact with anticoagulants, thyroid medication, or chemotherapy; no interaction discussion at all. |
| **Supplement doses** | "Spirulina Capsules, Moringa Capsules, Green Essentials – 1 each ... for Better Results" is an unsupervised supplement-dosing suggestion layered onto an already-restrictive diet — exactly the `recommended_dose`-style pattern this proposal's validator rejects outright. |
| **Raw foods generally** | The document's core structure (Plate A) is built around raw juices, raw sprouts, and raw soaked nuts as the primary recommendation, which is the opposite of the "well-cooked foods during immunosuppression" guidance this proposal's neutropenia template follows. |
| **Fasting / cleansing** | Not an explicit fast, but the "you won't need the other plates" framing and strict Plate C prohibition function as a de facto restrictive/elimination regimen, which this proposal's scope explicitly excludes (see `evidence-and-safety.md`, "Unknowns are unknown, not safe," and the constipation template's explicit exclusion of cleansing regimens). |

**Disposition:** registered in `source_registry.json` as `src-local-desktop-diet-chart`, `type: local_upload_commercial_style_handout`, `tier: 4`, `eligible_for_efficacy_claims: false`, `status: found_and_audited`. Its raw-juice/raw-sprout/supplement-capsule pattern is explicitly called out and **not reproduced** in `diet_template_examples.json`'s neutropenia template (`audit_note_from_local_diet_chart` field). None of its content is used to support any claim.

## Supplied URLs

All 18 supplied URLs (including the multiple-myeloma URL supplied twice, preserved via `occurrences: 2` on one canonical entry rather than two separate ids) plus the named authoritative anchors and PubMed IDs are classified in `knowledge/ayurveda-oncology/source_registry.json`. Summary:

- **Tier 1 (authoritative, eligible for efficacy/safety baseline claims):** Cancer Research UK's Ayurvedic-medicine page, NCCIH's Ayurveda overview, NCI's curcumin PDQ and dietary-interactions PDQ, the ESPEN clinical-nutrition-in-cancer guideline, ACS's food-safety-during-immunosuppression page, and the (URL-pending) MSK "About Herbs" monographs for ashwagandha/turmeric/boswellia/ginger.
- **Tier 2–3 (candidate clinical evidence, currently `verification_status: pending_manual_verification`, not yet eligible to support a claim):** the six named PubMed IDs (boswellia/RT edema pilot; ashwagandha/breast-chemo fatigue; whole-systems-Ayurveda survivorship feasibility; two ginger/CINV trials, one positive one null; the 6-gingerol phase II trial), plus the two bare PMC article links and the JAIMS journal link, which need their own design/population/outcome classification before use.
- **Tier 4 (commercial/clinic/hospital/video, context only, never sufficient for a claim):** all `planetayurveda.*` pages, `ayurvaid.com`, `oneworldayurveda.com`, `dmhospital.org`, `alwaysayurveda.com` (a direct product-purchase page), `aryavaidyasala.com`'s in-house research announcement, `jeenasikho.com`'s diet-plan blog, and the YouTube video. These are the basis for `card-commercial-multiherb-packs-blocked` (`blocked_unsupported`) — they were **not** used to construct or support any efficacy claim, only to document that they were reviewed and excluded.

No herb-to-cancer mapping was invented from a commercial or narrative source alone; where no qualifying human evidence was identified for a claimed use, the corresponding card is `blocked_unsupported` rather than filled in.
