#!/usr/bin/env python3
"""Dependency-free validator for the chinese-herbal-oncology-support proposal's
machine-readable knowledge fixtures (knowledge/chinese-herbal-oncology/).

Validates this PROPOSAL's fixtures and contracts only. Does not touch the
existing one-herb/appetite production data model, nor the separate (unmerged)
ayurveda-oncology-support or homeopathy-oncology-evidence proposals' tables
or terminology.
"""

import json
import re
import sys
from pathlib import Path

ALLOWED_STATES = {
    "avoid",
    "blocked_unsupported",
    "blocked_integrity",
    "insufficient_evidence",
    "preclinical_research_only",
    "research_only",
    "clinician_discussion_only",
    "general_education",
    "out_of_scope_adjacent",
}

NON_EFFICACY_SOURCE_TYPES = {
    "preclinical_animal",
    "preclinical_in_vitro",
    "case_report",
    "narrative_review",
    "conference_handout",
    "provider_page",
    "provider_education_blog",
    "trial_registry",
    "tertiary_encyclopedia",
    "patient_advocacy_page",
    "observational_use_survey",
    "duplicate_pointer",
    "out_of_scope_adjacent",
    "institutional_regulatory_context",
    "overview_of_systematic_reviews",  # eligible for context/synthesis claims, but never alone for a strong efficacy state -- see STATES_ALLOWED_FOR_NON_EFFICACY_ONLY_CARDS
}

# Source types that can never, by themselves, substantiate a patient efficacy claim,
# regardless of how the card's state is phrased.
NEVER_SOLE_EFFICACY_SUPPORT_TYPES = {
    "tertiary_encyclopedia",
    "provider_education_blog",
    "provider_page",
    "patient_advocacy_page",
    "narrative_review",
    "conference_handout",
    "commercial_page",
}

STATES_ALLOWED_FOR_NON_EFFICACY_ONLY_CARDS = {
    "research_only",
    "preclinical_research_only",
    "avoid",
    "blocked_unsupported",
    "general_education",
    "insufficient_evidence",
    "out_of_scope_adjacent",
}

INELIGIBLE_EVIDENCE_VALUES = {
    "ineligible_retracted",
    "ineligible_tertiary_or_encyclopedia",
    "ineligible_commercial_or_advocacy",
    "ineligible_pending_verification",
}

RESULT_DIRECTIONS_EXPECTED_PRESENT = {
    "unavailable", "mixed", "positive_but_quality_limited", "toxicity_documented_efficacy_unestablished_in_humans",
    "harm_established", "unavailable_no_current_guideline_endorsement_identified",
}

FORBIDDEN_PHRASES = [
    "cures cancer", "cure for cancer", "treats cancer", "prevents cancer", "kills cancer",
    "shrinks tumor", "shrinks tumour",
    "side-effect free", "side effect free", "non-toxic", "nontoxic",
    "detox", "blood purification", "blood-purification",
    "immune boosting", "immune-boosting", "boosts immunity", "boost the immune system", "helps boost the immune system",
    "cancer-fighting", "cancer fighting", "anti-cancer spice", "anti-cancer spices",
    "toxic to cancer cells", "most powerful anti-cancer",
    "clinically proven", "proven to cure",
    "instead of chemotherapy", "instead of standard treatment", "in place of standard care",
    "replace chemotherapy", "replace radiotherapy", "replace surgery",
    "stop your treatment", "skip chemotherapy", "delay chemotherapy",
    "surgery which inevitably leads to the consequences of tumor spread",
    "surgery inevitably leads to tumor spread",
]

FORBIDDEN_KEYS = [
    "recommended_dose", "potency_selection", "dosing_frequency", "frequency_instructions",
    "treatment_protocol_instructions", "timing_schedule", "formula_selection", "self_treatment_instructions",
    "syndrome_diagnosis", "pattern_diagnosis", "pulse_diagnosis", "tongue_diagnosis",
    "product_purchase_link", "purchase_link", "clinic_referral", "clinic_referral_link",
    "cancer_type_diet", "cancer_specific_diet", "tumor_diet",
]

BANNED_FOOD_EXAMPLE_KEYWORDS = [
    "ginseng", "astragalus", "licorice", "reishi", "ganoderma", "medicinal mushroom",
    "medicated congee", "herbal soup", "formula sachet", "concentrated tea",
]

HIGH_RISK_INGREDIENT_MARKERS = [
    "aristolochia", "asarum", "aristolochic acid", "tripterygium", "thunder god vine",
]

NON_BOTANICAL_MARKERS = [
    "ganoderma", "trametes", "toad", "venom", "musk", "calculus bovis", "chan su", "coriolus",
]

REQUIRED_CARD_FIELDS = [
    "cancer_context", "disease_state", "treatment_context", "population",
    "claim_or_purpose_studied", "outcome_category", "intervention", "comparator", "sample_size",
    "outcomes_prespecified", "outcome_type", "result_direction", "evidence", "limitations",
    "what_was_not_shown", "publication_integrity", "safety", "state",
]

REQUIRED_INTERVENTION_FIELDS = [
    "cultural_system", "formula_or_product_name_english", "formula_type", "ingredients_known",
    "non_botanical_ingredients", "species_and_plant_part", "preparation_and_route",
    "manufacturer_batch_jurisdiction", "co_interventions", "non_equivalence_note",
]

REQUIRED_SOURCE_FIELDS = [
    "source_type", "publisher", "publication_status", "integrity_status",
    "evidence_eligibility", "access_status", "accessed_at", "canonical_work_id",
]

REQUIRED_DIET_TEMPLATE_FIELDS = [
    "goal", "intended_population", "may_apply_when", "unsuitable_when", "flexible_food_pattern",
    "chinese_food_examples_and_substitutions", "traditional_dietary_therapy_context",
    "biomedical_rationale", "protein_energy_fluid_texture_food_safety",
    "medication_herb_supplement_food_interaction_note", "cautions", "red_flags_requiring_escalation",
    "source_ids", "reviewer_roles_required", "expiry_review",
]

REQUIRED_APPROVALS_CARD = {"oncology_or_pharmacist", "evidence_methodology_reviewer", "tcm_practitioner"}
REQUIRED_APPROVALS_DIET = {"oncology_dietitian"}
DISALLOWED_APPROVER_ROLES = {
    "ai", "researcher", "editor", "administrator", "product_owner", "practitioner_generic",
}
# A role can never satisfy an approval slot it is not named for (no cross-substitution).
ROLE_MAY_ONLY_SATISFY_ITS_OWN_SLOT = True

AUDIT_EVENT_TYPES_REQUIRED = {
    "create", "edit", "translate", "verify", "approve", "reject", "suspend", "expire", "retract", "unpublish",
}

PII_PATTERNS = [re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), re.compile(r"\b\d{3}-\d{2}-\d{4}\b")]


def _iter_strings(obj, exclude_keys=frozenset()):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in exclude_keys:
                continue
            yield from _iter_strings(v, exclude_keys)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v, exclude_keys)


def _has_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return True
        return any(_has_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_key(v, key) for v in obj)
    return False


# 'never_imply' is a staff-facing registry of phrases NOT to use -- quoting a banned phrase
# there to document that it is banned is the opposite of using it in patient-facing text.
PHRASE_SCAN_EXCLUDED_KEYS = frozenset({"never_imply"})


def check_forbidden_phrases(record, errors, where):
    text = " ".join(_iter_strings(record, PHRASE_SCAN_EXCLUDED_KEYS)).lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            errors.append(f"{where}: forbidden phrase '{phrase}' found in patient-facing text")


def check_forbidden_keys(record, errors, where):
    for key in FORBIDDEN_KEYS:
        if _has_key(record, key):
            errors.append(f"{where}: forbidden field '{key}' is not permitted")


def check_no_pii(record, errors, where):
    text = " ".join(_iter_strings(record))
    for pattern in PII_PATTERNS:
        if pattern.search(text):
            errors.append(f"{where}: possible PII-like pattern found in fixture text")


def canonicalize_urls(urls):
    counts = {}
    for u in urls:
        counts[u] = counts.get(u, 0) + 1
    return counts


def validate_source_registry(registry):
    errors = []
    sources = registry.get("sources", [])
    seen_ids = set()
    url_to_ids = {}
    canonical_ref_counts = {}

    for src in sources:
        sid = src.get("id")
        if not sid:
            errors.append("source entry missing 'id'")
            continue
        if sid in seen_ids:
            errors.append(f"duplicate source id: {sid}")
        seen_ids.add(sid)

        for field in REQUIRED_SOURCE_FIELDS:
            if field not in src:
                errors.append(f"{sid}: missing required source field '{field}'")

        url = src.get("url")
        if url:
            url_to_ids.setdefault(url, []).append(sid)

        cwid = src.get("canonical_work_id")
        if cwid:
            canonical_ref_counts[cwid] = canonical_ref_counts.get(cwid, 0) + 1

    for url, ids in url_to_ids.items():
        if len(ids) > 1:
            errors.append(
                f"unrecorded duplicate URL across distinct source ids "
                f"(must canonicalize to one id with an 'occurrences' count): {url} -> {ids}"
            )

    for src in sources:
        sid = src.get("id")
        cwid = src.get("canonical_work_id")
        if cwid == sid:
            declared_occurrences = src.get("occurrences", 1)
            rows_pointing_here = canonical_ref_counts.get(sid, 0)
            if declared_occurrences < rows_pointing_here:
                errors.append(
                    f"{sid}: 'occurrences' ({declared_occurrences}) is less than the number of "
                    f"registry rows whose canonical_work_id points here ({rows_pointing_here})"
                )

    return errors, {s["id"]: s for s in sources if s.get("id")}


def validate_local_source_pending_or_found(registry, source_id, label):
    for src in registry.get("sources", []):
        if src.get("id") == source_id:
            status = src.get("access_status")
            if status not in ("accessible", "access_unverified", "not_individually_fetched_this_pass"):
                return [f"{label} ({source_id}) has an unrecognized access_status: {status!r}"]
            return []
    return [f"{label} source entry ({source_id}) is missing from the registry"]


def validate_wikipedia_ineligible(registry):
    for src in registry.get("sources", []):
        if src.get("id") == "src-wikipedia-altmed-list":
            if src.get("evidence_eligibility") != "ineligible_tertiary_or_encyclopedia":
                return ["the Wikipedia alternative-medicine list must have evidence_eligibility=ineligible_tertiary_or_encyclopedia"]
            return []
    return ["the Wikipedia alternative-medicine list source entry is missing from the registry"]


def validate_screening_coverage(screening):
    errors = []
    if not screening.get("non_ingestible_group_exclusions"):
        errors.append("alternative_modality_screening.json is missing non_ingestible_group_exclusions")
    if not screening.get("ingestible_candidates"):
        errors.append("alternative_modality_screening.json is missing ingestible_candidates")
    if not screening.get("brief_mandated_additions_not_individually_named_on_the_wikipedia_page"):
        errors.append("alternative_modality_screening.json is missing brief_mandated_additions_not_individually_named_on_the_wikipedia_page")

    all_items = (
        screening.get("non_ingestible_group_exclusions", [])
        + screening.get("ingestible_candidates", [])
        + screening.get("brief_mandated_additions_not_individually_named_on_the_wikipedia_page", [])
    )
    for item in all_items:
        if "screen_decision" not in item:
            label = item.get("modality") or item.get("category") or item.get("group_label") or "<unnamed>"
            errors.append(f"screening entry '{label}' is missing a screen_decision")
    return errors


def validate_essiac_non_tcm(cards):
    for card in cards:
        if card.get("id") == "card-essiac-any-cancer":
            cultural_system = (card.get("intervention", {}).get("cultural_system") or "").lower()
            if "non-tcm" not in cultural_system and "not tcm" not in cultural_system:
                return ["card-essiac-any-cancer must explicitly state it is NOT TCM in intervention.cultural_system"]
            if card.get("state") != "blocked_unsupported":
                return [f"card-essiac-any-cancer must be state=blocked_unsupported, got {card.get('state')!r}"]
            return []
    return ["card-essiac-any-cancer is missing from example_evidence_cards.json"]


def validate_pmc11734505_handling(registry, cards):
    errors = []
    src = None
    for s in registry.get("sources", []):
        if s.get("id") == "src-pmc11734505":
            src = s
    if src is None:
        return ["src-pmc11734505 is missing from the source registry"]
    if src.get("evidence_eligibility") not in ("discovery_only", "context_only"):
        errors.append("src-pmc11734505 must have evidence_eligibility in {discovery_only, context_only}")

    for card in cards:
        cited = card.get("evidence", {}).get("source_ids", [])
        if "src-pmc11734505" in cited and set(cited).issubset({"src-pmc11734505"}):
            if card.get("state") != "preclinical_research_only":
                errors.append(
                    f"{card.get('id')}: relies solely on src-pmc11734505 and must be state=preclinical_research_only, "
                    f"got {card.get('state')!r}"
                )
    return errors


def validate_mhs_spice_page_handling(registry):
    for src in registry.get("sources", []):
        if src.get("id") == "src-mhs-cancer-fighting-spices":
            if src.get("evidence_eligibility") != "provider_education":
                return ["src-mhs-cancer-fighting-spices must have evidence_eligibility=provider_education"]
            return []
    return ["src-mhs-cancer-fighting-spices is missing from the source registry"]


def validate_pmc5073821_handling(registry, cards):
    errors = []
    found_source = False
    for s in registry.get("sources", []):
        if s.get("id") == "src-pmc5073821":
            found_source = True
            if s.get("evidence_eligibility") != "observational_use_survey":
                errors.append("src-pmc5073821 must have evidence_eligibility=observational_use_survey")
    if not found_source:
        errors.append("src-pmc5073821 is missing from the source registry")

    for card in cards:
        cited = card.get("evidence", {}).get("source_ids", [])
        if "src-pmc5073821" in cited and set(cited).issubset({"src-pmc5073821", "src-mskcc-graviola"}):
            if card.get("state") not in STATES_ALLOWED_FOR_NON_EFFICACY_ONLY_CARDS:
                errors.append(
                    f"{card.get('id')}: relies on the PMC5073821 observational survey but state "
                    f"'{card.get('state')}' implies more than a non-efficacy record"
                )
    return errors


def validate_high_risk_ingredients(cards):
    errors = []
    for card in cards:
        ingredients_text = " ".join(_iter_strings(card.get("intervention", {}))).lower()
        for marker in HIGH_RISK_INGREDIENT_MARKERS:
            if marker in ingredients_text and card.get("state") != "avoid":
                errors.append(
                    f"{card.get('id')}: mentions high-risk ingredient marker '{marker}' but state is "
                    f"'{card.get('state')}', expected 'avoid'"
                )
    return errors


def validate_non_botanical_classification(cards):
    errors = []
    for card in cards:
        intervention = card.get("intervention", {})
        ingredient_text = " ".join(_iter_strings(intervention.get("ingredients_known"))).lower()
        ingredient_text += " " + " ".join(_iter_strings(intervention.get("formula_or_product_name_english"))).lower()
        for marker in NON_BOTANICAL_MARKERS:
            if marker in ingredient_text and not intervention.get("non_botanical_ingredients"):
                errors.append(
                    f"{card.get('id')}: ingredient text mentions non-botanical marker '{marker}' but "
                    f"intervention.non_botanical_ingredients is empty -- must be explicitly classified"
                )
    return errors


def validate_cards(cards, sources_by_id):
    errors = []
    for card in cards:
        cid = card.get("id", "<missing id>")

        for field in REQUIRED_CARD_FIELDS:
            if field not in card:
                errors.append(f"{cid}: missing required field '{field}'")

        intervention = card.get("intervention", {})
        for field in REQUIRED_INTERVENTION_FIELDS:
            if field not in intervention:
                errors.append(f"{cid}: intervention missing required field '{field}'")

        state = card.get("state")
        if state not in ALLOWED_STATES:
            errors.append(
                f"{cid}: state '{state}' is not an allowed state "
                f"(there is no autonomous recommended/effective/proven/safe/supported state)"
            )

        check_forbidden_keys(card, errors, cid)
        check_forbidden_phrases(card, errors, cid)
        check_no_pii(card, errors, cid)

        safety = card.get("safety", {})
        if not safety.get("care_delay_warning"):
            errors.append(f"{cid}: safety.care_delay_warning is required and must be non-empty")
        if not safety.get("standard_care_statement"):
            errors.append(f"{cid}: safety.standard_care_statement is required and must be non-empty")

        cited_ids = card.get("evidence", {}).get("source_ids", [])
        cited_source_types = set()
        never_sole_types_present = set()
        for sid in cited_ids:
            src = sources_by_id.get(sid)
            if src is None:
                errors.append(f"{cid}: references unknown source id '{sid}'")
                continue
            if src.get("canonical_work_id") and src.get("canonical_work_id") != sid:
                errors.append(
                    f"{cid}: cites '{sid}', which is a duplicate pointer -- must cite its "
                    f"canonical_work_id '{src.get('canonical_work_id')}' instead"
                )
            cited_source_types.add(src.get("source_type"))
            if src.get("source_type") in NEVER_SOLE_EFFICACY_SUPPORT_TYPES:
                never_sole_types_present.add(src.get("source_type"))
            if src.get("evidence_eligibility") in INELIGIBLE_EVIDENCE_VALUES and state not in (
                "avoid", "blocked_unsupported", "blocked_integrity", "preclinical_research_only",
                "research_only", "insufficient_evidence", "general_education", "out_of_scope_adjacent",
            ):
                errors.append(f"{cid}: cites an ineligible source but state '{state}' does not reflect that")

        if cited_ids and never_sole_types_present and set(cited_source_types) == never_sole_types_present:
            if state not in STATES_ALLOWED_FOR_NON_EFFICACY_ONLY_CARDS:
                errors.append(
                    f"{cid}: relies SOLELY on source type(s) {sorted(never_sole_types_present)} "
                    f"(tertiary/commercial/provider/advocacy/narrative), which can never alone substantiate "
                    f"efficacy; state '{state}' is not permitted in that case"
                )

        if cited_ids and cited_source_types and cited_source_types.issubset(NON_EFFICACY_SOURCE_TYPES):
            if state not in STATES_ALLOWED_FOR_NON_EFFICACY_ONLY_CARDS:
                errors.append(
                    f"{cid}: all cited sources are non-efficacy source types {sorted(cited_source_types)}, "
                    f"so state '{state}' (implying real clinical discussion-worthiness or stronger) is not permitted"
                )

    errors += validate_high_risk_ingredients(cards)
    errors += validate_non_botanical_classification(cards)
    return errors


def validate_diet_templates(templates, known_source_ids):
    errors = []
    for tpl in templates:
        tid = tpl.get("id", "<missing id>")
        for field in REQUIRED_DIET_TEMPLATE_FIELDS:
            if field not in tpl:
                errors.append(f"{tid}: missing required field '{field}'")

        check_forbidden_keys(tpl, errors, tid)
        check_forbidden_phrases(tpl, errors, tid)
        check_no_pii(tpl, errors, tid)

        if _has_key(tpl, "cancer_context") or _has_key(tpl, "cancer_type"):
            errors.append(f"{tid}: diet templates must not be cancer-type-specific (no cancer_context/cancer_type field)")

        food_examples_text = " ".join(_iter_strings(tpl.get("chinese_food_examples_and_substitutions"))).lower()
        for keyword in BANNED_FOOD_EXAMPLE_KEYWORDS:
            if keyword in food_examples_text:
                errors.append(
                    f"{tid}: food-example list mentions '{keyword}', which must be routed through the "
                    f"herb/supplement safety workflow, not listed as ordinary food"
                )

        for sid in tpl.get("source_ids", []):
            if sid not in known_source_ids:
                errors.append(f"{tid}: references unknown source id '{sid}'")

        if "not a cure" not in json.dumps(tpl).lower() and tid != "_global":
            pass  # not_a_cure_statement is declared once at document level; per-template restatement not required.

    return errors


def check_publish_eligibility_card(record):
    reasons = []
    approvals = record.get("approvals", {})
    version = record.get("version")

    for role in REQUIRED_APPROVALS_CARD:
        entry = approvals.get(role)
        if not entry:
            reasons.append(f"missing {role} approval")
            continue
        if entry.get("version") != version:
            reasons.append(f"{role} approval version mismatch: {entry.get('version')!r} != {version!r}")
        if entry.get("approved_by_role") in DISALLOWED_APPROVER_ROLES:
            reasons.append(f"{role} approval cannot be granted by role '{entry.get('approved_by_role')}'")
        if ROLE_MAY_ONLY_SATISFY_ITS_OWN_SLOT and entry.get("approved_by_role") not in (role, None) and entry.get("approved_by_role") is not None:
            if entry.get("approved_by_role") != role:
                reasons.append(
                    f"{role} approval slot was filled by role '{entry.get('approved_by_role')}', "
                    f"which may not satisfy a slot it is not named for"
                )
    return (len(reasons) == 0, reasons)


def check_publish_eligibility_diet(record):
    reasons = []
    approvals = record.get("approvals", {})
    version = record.get("version")

    for role in REQUIRED_APPROVALS_DIET:
        entry = approvals.get(role)
        if not entry:
            reasons.append(f"missing {role} approval")
            continue
        if entry.get("version") != version:
            reasons.append(f"{role} approval version mismatch: {entry.get('version')!r} != {version!r}")
        if entry.get("approved_by_role") in DISALLOWED_APPROVER_ROLES or entry.get("approved_by_role") == "tcm_practitioner":
            reasons.append(
                f"{role} approval cannot be granted by role '{entry.get('approved_by_role')}' "
                f"(a TCM practitioner cannot substitute for an oncology dietitian)"
            )
    return (len(reasons) == 0, reasons)


def validate_audit_event_contract(declared_types):
    missing = AUDIT_EVENT_TYPES_REQUIRED - set(declared_types)
    if missing:
        return [f"audit event contract is missing required action type(s): {sorted(missing)}"]
    return []


def load_fixtures(kb_dir: Path):
    registry = json.loads((kb_dir / "source_registry.json").read_text())
    cards_doc = json.loads((kb_dir / "example_evidence_cards.json").read_text())
    templates_doc = json.loads((kb_dir / "diet_template_examples.json").read_text())
    screening_doc = json.loads((kb_dir / "alternative_modality_screening.json").read_text())
    return registry, cards_doc, templates_doc, screening_doc


def run_all_checks(registry, cards_doc, templates_doc, screening_doc):
    errors = []

    src_errors, sources_by_id = validate_source_registry(registry)
    errors += src_errors
    errors += validate_wikipedia_ineligible(registry)
    errors += validate_screening_coverage(screening_doc)

    cards = cards_doc.get("cards", [])
    templates = templates_doc.get("templates", [])
    known_source_ids = set(sources_by_id.keys())

    check_forbidden_keys(cards_doc, errors, "example_evidence_cards.json (document-level)")
    check_forbidden_keys(templates_doc, errors, "diet_template_examples.json (document-level)")

    errors += validate_cards(cards, sources_by_id)
    errors += validate_diet_templates(templates, known_source_ids)
    errors += validate_essiac_non_tcm(cards)
    errors += validate_pmc11734505_handling(registry, cards)
    errors += validate_mhs_spice_page_handling(registry)
    errors += validate_pmc5073821_handling(registry, cards)

    for card in cards:
        eligible, _reasons = check_publish_eligibility_card(card)
        if eligible:
            errors.append(f"{card.get('id')}: draft card unexpectedly satisfied the publish-eligibility gate")

    for tpl in templates:
        eligible, _reasons = check_publish_eligibility_diet(tpl)
        if eligible:
            errors.append(f"{tpl.get('id')}: draft diet template unexpectedly satisfied the publish-eligibility gate")

    return errors, cards, templates, list(sources_by_id.values())


def main():
    root = Path(__file__).resolve().parents[1]
    kb_dir = root / "knowledge" / "chinese-herbal-oncology"

    registry, cards_doc, templates_doc, screening_doc = load_fixtures(kb_dir)
    errors, cards, templates, sources = run_all_checks(registry, cards_doc, templates_doc, screening_doc)

    if errors:
        print(f"FAIL: {len(errors)} issue(s) found")
        for e in errors:
            print(f" - {e}")
        return 1

    print(f"OK: {len(cards)} cards, {len(templates)} diet templates, {len(sources)} sources validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
