"""Contract tests for the chinese-herbal-oncology-support PROPOSAL's knowledge
fixtures and validator (scripts/validate_chinese_herbal_proposal.py). Additive:
does not touch the existing one-herb/appetite tests, nor the separate
(unmerged) ayurveda-oncology-support or homeopathy-oncology-evidence
proposals' fixtures or validators.

Only synthetic fixtures are used for negative-path tests; the real proposal
fixtures under knowledge/chinese-herbal-oncology/ are used for the
positive-path "the shipped fixtures are clean" tests.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_chinese_herbal_proposal.py"
KB_DIR = REPO_ROOT / "knowledge" / "chinese-herbal-oncology"

_spec = importlib.util.spec_from_file_location("validate_chinese_herbal_proposal", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = validator
_spec.loader.exec_module(validator)


def _minimal_source(sid, **overrides):
    src = {
        "id": sid, "url": f"https://example.org/{sid}", "source_type": "provider_page",
        "publisher": "x", "publication_status": "active", "integrity_status": "no_concern_identified",
        "evidence_eligibility": "context_only", "access_status": "accessible", "accessed_at": "2026-09-17",
        "canonical_work_id": sid, "occurrences": 1,
    }
    src.update(overrides)
    return src


def _minimal_card(**overrides):
    card = {
        "id": "card-x", "cancer_context": "x", "disease_state": "x", "treatment_context": "x", "population": "x",
        "claim_or_purpose_studied": "x", "outcome_category": "x",
        "intervention": {
            "cultural_system": "x", "formula_or_product_name_english": "x", "formula_type": "x",
            "ingredients_known": None, "non_botanical_ingredients": None, "species_and_plant_part": "x",
            "preparation_and_route": "x", "manufacturer_batch_jurisdiction": "x", "co_interventions": "x",
            "non_equivalence_note": "x",
        },
        "comparator": "x", "sample_size": 1, "outcomes_prespecified": ["x"], "outcome_type": "x",
        "result_direction": "null",
        "evidence": {"summary": "x", "source_ids": [], "certainty": "low"},
        "limitations": "x", "what_was_not_shown": "x",
        "publication_integrity": {"status": "active"},
        "safety": {"care_delay_warning": "x", "standard_care_statement": "x"},
        "state": "insufficient_evidence",
    }
    card.update(overrides)
    return card


class SourceRegistryTests(unittest.TestCase):
    def test_shipped_registry_has_no_errors(self):
        registry, _cards, _tpls, _screen = validator.load_fixtures(KB_DIR)
        errors, sources_by_id = validator.validate_source_registry(registry)
        self.assertEqual(errors, [])
        self.assertIn("src-pmc11734505", sources_by_id)

    def test_rejects_duplicate_source_id(self):
        registry = {"sources": [_minimal_source("dup"), _minimal_source("dup")]}
        errors, _ = validator.validate_source_registry(registry)
        self.assertTrue(any("duplicate source id" in e for e in errors))

    def test_rejects_unrecorded_duplicate_url(self):
        a = _minimal_source("a", url="https://same.example/")
        b = _minimal_source("b", url="https://same.example/")
        errors, _ = validator.validate_source_registry({"sources": [a, b]})
        self.assertTrue(any("unrecorded duplicate URL" in e for e in errors))

    def test_requires_core_source_fields(self):
        errors, _ = validator.validate_source_registry({"sources": [{"id": "incomplete"}]})
        for field in validator.REQUIRED_SOURCE_FIELDS:
            self.assertTrue(any(field in e for e in errors), f"missing-field check not raised for {field}")

    def test_wikipedia_source_is_ineligible(self):
        registry, _c, _t, _s = validator.load_fixtures(KB_DIR)
        self.assertEqual(validator.validate_wikipedia_ineligible(registry), [])
        bad = {"sources": [{"id": "src-wikipedia-altmed-list", "evidence_eligibility": "eligible"}]}
        self.assertTrue(validator.validate_wikipedia_ineligible(bad))

    def test_mhs_spice_page_classified_provider_education(self):
        registry, _c, _t, _s = validator.load_fixtures(KB_DIR)
        self.assertEqual(validator.validate_mhs_spice_page_handling(registry), [])
        bad = {"sources": [{"id": "src-mhs-cancer-fighting-spices", "evidence_eligibility": "eligible"}]}
        self.assertTrue(validator.validate_mhs_spice_page_handling(bad))


class ScreeningCoverageTests(unittest.TestCase):
    def test_shipped_screening_has_full_coverage(self):
        _r, _c, _t, screening = validator.load_fixtures(KB_DIR)
        self.assertEqual(validator.validate_screening_coverage(screening), [])

    def test_missing_screen_decision_is_rejected(self):
        bad = {
            "non_ingestible_group_exclusions": [{"group_label": "x"}],
            "ingestible_candidates": [{"modality": "y", "screen_decision": "out_of_scope_adjacent"}],
            "brief_mandated_additions_not_individually_named_on_the_wikipedia_page": [],
        }
        errors = validator.validate_screening_coverage(bad)
        self.assertTrue(any("missing a screen_decision" in e for e in errors))
        self.assertTrue(any("brief_mandated_additions" in e for e in errors))


class EvidenceCardTests(unittest.TestCase):
    def test_shipped_cards_have_no_errors(self):
        registry, cards_doc, _t, _s = validator.load_fixtures(KB_DIR)
        _errs, sources_by_id = validator.validate_source_registry(registry)
        errors = validator.validate_cards(cards_doc["cards"], sources_by_id)
        self.assertEqual(errors, [])

    def test_missing_required_field_is_rejected(self):
        card = _minimal_card()
        del card["disease_state"]
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("missing required field 'disease_state'" in e for e in errors))

    def test_missing_intervention_field_is_rejected(self):
        card = _minimal_card()
        del card["intervention"]["species_and_plant_part"]
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("intervention missing required field" in e for e in errors))

    def test_autonomous_states_are_rejected(self):
        for bad_state in ["recommended", "effective", "proven", "safe", "supported"]:
            card = _minimal_card(state=bad_state)
            errors = validator.validate_cards([card], {})
            self.assertTrue(any("not an allowed state" in e for e in errors), f"{bad_state} was not rejected")

    def test_forbidden_fields_are_rejected(self):
        for key in ["recommended_dose", "formula_selection", "syndrome_diagnosis", "pulse_diagnosis",
                    "product_purchase_link", "clinic_referral", "cancer_specific_diet"]:
            card = _minimal_card()
            card["evidence"][key] = "x"
            errors = validator.validate_cards([card], {})
            self.assertTrue(any(f"forbidden field '{key}'" in e for e in errors), f"{key} was not rejected")

    def test_forbidden_phrases_are_rejected(self):
        for phrase in ["this treats cancer", "a gentle detox", "boosts immunity naturally",
                       "cancer-fighting spice", "toxic to cancer cells", "most powerful anti-cancer remedy"]:
            card = _minimal_card(claim_or_purpose_studied=phrase)
            errors = validator.validate_cards([card], {})
            self.assertTrue(any("forbidden phrase" in e for e in errors), f"phrase not caught: {phrase}")

    def test_never_imply_field_is_exempt_from_phrase_scan(self):
        card = _minimal_card()
        card["safety"]["never_imply"] = ["cancer-fighting", "detox"]
        errors = validator.validate_cards([card], {})
        self.assertFalse(any("forbidden phrase" in e for e in errors))

    def test_missing_care_delay_or_standard_care_statement_is_rejected(self):
        card = _minimal_card(safety={"standard_care_statement": "x"})
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("care_delay_warning is required" in e for e in errors))
        card2 = _minimal_card(safety={"care_delay_warning": "x"})
        errors2 = validator.validate_cards([card2], {})
        self.assertTrue(any("standard_care_statement is required" in e for e in errors2))

    def test_unknown_source_reference_is_rejected(self):
        card = _minimal_card(evidence={"summary": "x", "source_ids": ["src-nope"], "certainty": "low"})
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("unknown source id" in e for e in errors))

    def test_tertiary_or_provider_source_alone_cannot_justify_strong_state(self):
        sources_by_id = {"src-1": {"id": "src-1", "source_type": "tertiary_encyclopedia", "evidence_eligibility": "context_only", "canonical_work_id": "src-1"}}
        card = _minimal_card(evidence={"summary": "x", "source_ids": ["src-1"], "certainty": "low"}, state="clinician_discussion_only")
        errors = validator.validate_cards([card], sources_by_id)
        self.assertTrue(any("can never alone substantiate" in e or "non-efficacy source types" in e for e in errors))

    def test_high_risk_ingredient_requires_avoid_state(self):
        card = _minimal_card(state="research_only")
        card["intervention"]["ingredients_known"] = ["Aristolochia fangchi root"]
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("aristolochia" in e for e in errors))

    def test_non_botanical_marker_requires_explicit_classification(self):
        card = _minimal_card()
        card["intervention"]["ingredients_known"] = ["Ganoderma lucidum extract"]
        card["intervention"]["non_botanical_ingredients"] = None
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("non-botanical marker" in e for e in errors))

    def test_essiac_is_correctly_classified_and_blocked(self):
        _r, cards_doc, _t, _s = validator.load_fixtures(KB_DIR)
        self.assertEqual(validator.validate_essiac_non_tcm(cards_doc["cards"]), [])

    def test_essiac_mislabeled_as_tcm_is_rejected(self):
        bad_cards = [{"id": "card-essiac-any-cancer", "intervention": {"cultural_system": "TCM"}, "state": "blocked_unsupported"}]
        errors = validator.validate_essiac_non_tcm(bad_cards)
        self.assertTrue(errors)

    def test_pmc11734505_sole_reliance_requires_preclinical_state(self):
        registry, _c, _t, _s = validator.load_fixtures(KB_DIR)
        bad_card = _minimal_card(id="card-y", evidence={"summary": "x", "source_ids": ["src-pmc11734505"], "certainty": "low"}, state="research_only")
        errors = validator.validate_pmc11734505_handling(registry, [bad_card])
        self.assertTrue(any("preclinical_research_only" in e for e in errors))

    def test_no_pii_like_patterns_in_shipped_cards(self):
        _r, cards_doc, _t, _s = validator.load_fixtures(KB_DIR)
        errors = []
        for card in cards_doc["cards"]:
            validator.check_no_pii(card, errors, card["id"])
        self.assertEqual(errors, [])

    def test_result_directions_show_variety_not_just_positive(self):
        _r, cards_doc, _t, _s = validator.load_fixtures(KB_DIR)
        directions = {c["result_direction"] for c in cards_doc["cards"]}
        self.assertTrue(len(directions) >= 8, f"expected wide variety of result_direction values, got {directions}")
        self.assertIn("harm_established", directions)
        self.assertIn("unavailable_with_animal_harm_signal", directions)


class DietTemplateTests(unittest.TestCase):
    def test_shipped_templates_have_no_errors(self):
        registry, _c, templates_doc, _s = validator.load_fixtures(KB_DIR)
        _errs, sources_by_id = validator.validate_source_registry(registry)
        errors = validator.validate_diet_templates(templates_doc["templates"], set(sources_by_id.keys()))
        self.assertEqual(errors, [])

    def test_cancer_specific_diet_field_is_rejected(self):
        tpl = {"id": "tpl-x", "cancer_context": "breast cancer", "source_ids": [], "chinese_food_examples_and_substitutions": []}
        errors = validator.validate_diet_templates([tpl], set())
        self.assertTrue(any("cancer-type-specific" in e for e in errors))

    def test_banned_food_example_keywords_are_rejected(self):
        for keyword in ["ginseng", "astragalus", "reishi", "medicated congee", "herbal soup"]:
            tpl = {"id": "tpl-x", "chinese_food_examples_and_substitutions": [f"Soup with {keyword}"], "source_ids": []}
            errors = validator.validate_diet_templates([tpl], set())
            self.assertTrue(any(keyword in e for e in errors), f"{keyword} was not rejected")

    def test_no_diet_template_has_a_cancer_context(self):
        _r, _c, templates_doc, _s = validator.load_fixtures(KB_DIR)
        for tpl in templates_doc["templates"]:
            self.assertNotIn("cancer_context", tpl)
            self.assertNotIn("cancer_type", tpl)

    def test_eight_required_symptom_templates_present(self):
        _r, _c, templates_doc, _s = validator.load_fixtures(KB_DIR)
        ids = {t["id"] for t in templates_doc["templates"]}
        self.assertEqual(len(ids), 8)


class PublishGateTests(unittest.TestCase):
    def test_card_draft_without_approvals_cannot_publish(self):
        eligible, reasons = validator.check_publish_eligibility_card({"version": "0.1.0"})
        self.assertFalse(eligible)
        self.assertTrue(reasons)

    def test_tcm_practitioner_cannot_satisfy_oncology_or_evidence_slot(self):
        record = {
            "version": "0.1.0",
            "approvals": {
                "oncology_or_pharmacist": {"version": "0.1.0", "approved_by_role": "tcm_practitioner"},
                "evidence_methodology_reviewer": {"version": "0.1.0", "approved_by_role": "evidence_methodology_reviewer"},
                "tcm_practitioner": {"version": "0.1.0", "approved_by_role": "tcm_practitioner"},
            },
        }
        eligible, reasons = validator.check_publish_eligibility_card(record)
        self.assertFalse(eligible)
        self.assertTrue(any("may not satisfy a slot it is not named for" in r for r in reasons))

    def test_properly_triple_approved_card_can_publish(self):
        record = {
            "version": "0.1.0",
            "approvals": {
                "oncology_or_pharmacist": {"version": "0.1.0", "approved_by_role": "oncology_or_pharmacist"},
                "evidence_methodology_reviewer": {"version": "0.1.0", "approved_by_role": "evidence_methodology_reviewer"},
                "tcm_practitioner": {"version": "0.1.0", "approved_by_role": "tcm_practitioner"},
            },
        }
        eligible, reasons = validator.check_publish_eligibility_card(record)
        self.assertTrue(eligible, reasons)

    def test_diet_template_requires_oncology_dietitian_not_tcm_practitioner(self):
        record = {"version": "0.1.0", "approvals": {"oncology_dietitian": {"version": "0.1.0", "approved_by_role": "tcm_practitioner"}}}
        eligible, reasons = validator.check_publish_eligibility_diet(record)
        self.assertFalse(eligible)
        self.assertTrue(any("cannot substitute for an oncology dietitian" in r for r in reasons))

    def test_diet_template_with_proper_dietitian_approval_can_publish(self):
        record = {"version": "0.1.0", "approvals": {"oncology_dietitian": {"version": "0.1.0", "approved_by_role": "oncology_dietitian"}}}
        eligible, reasons = validator.check_publish_eligibility_diet(record)
        self.assertTrue(eligible, reasons)

    def test_all_shipped_cards_and_templates_fail_the_publish_gate_as_drafts(self):
        _r, cards_doc, templates_doc, _s = validator.load_fixtures(KB_DIR)
        for card in cards_doc["cards"]:
            eligible, _ = validator.check_publish_eligibility_card(card)
            self.assertFalse(eligible, f"{card['id']} should not be publish-eligible as a draft")
        for tpl in templates_doc["templates"]:
            eligible, _ = validator.check_publish_eligibility_diet(tpl)
            self.assertFalse(eligible, f"{tpl['id']} should not be publish-eligible as a draft")


class AuditEventContractTests(unittest.TestCase):
    def test_complete_declared_set_passes(self):
        self.assertEqual(validator.validate_audit_event_contract(validator.AUDIT_EVENT_TYPES_REQUIRED), [])

    def test_incomplete_declared_set_is_rejected(self):
        incomplete = validator.AUDIT_EVENT_TYPES_REQUIRED - {"translate", "verify"}
        errors = validator.validate_audit_event_contract(incomplete)
        self.assertTrue(any("translate" in e for e in errors))


class FullValidatorRunTests(unittest.TestCase):
    def test_main_returns_zero_on_shipped_fixtures(self):
        self.assertEqual(validator.main(), 0)


if __name__ == "__main__":
    unittest.main()
