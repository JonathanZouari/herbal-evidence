"""Contract tests for the homeopathy-oncology-evidence PROPOSAL's knowledge
fixtures and validator (scripts/validate_homeopathy_proposal.py). Additive:
does not touch the existing one-herb/appetite tests, nor the separate
(unmerged) ayurveda-oncology-support proposal's fixtures or validator.

Only synthetic fixtures are used for negative-path tests; the real proposal
fixtures under knowledge/homeopathy-oncology/ are used for the positive-path
"the shipped fixtures are clean" tests.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_homeopathy_proposal.py"

_spec = importlib.util.spec_from_file_location("validate_homeopathy_proposal", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = validator
_spec.loader.exec_module(validator)


class CanonicalizeUrlsTests(unittest.TestCase):
    def test_literal_duplicate_url_counted(self):
        counts = validator.canonicalize_urls(["https://a.example/", "https://a.example/", "https://b.example/"])
        self.assertEqual(counts["https://a.example/"], 2)
        self.assertEqual(len(counts), 2)


class SourceRegistryTests(unittest.TestCase):
    def test_shipped_registry_has_no_errors(self):
        registry, _cards = validator.load_fixtures(REPO_ROOT / "knowledge" / "homeopathy-oncology")
        errors, sources_by_id = validator.validate_source_registry(registry)
        self.assertEqual(errors, [])
        self.assertIn("src-local-apha-handout", sources_by_id)

    def test_milazzo_duplicate_publisher_urls_share_one_canonical_work(self):
        registry, _cards = validator.load_fixtures(REPO_ROOT / "knowledge" / "homeopathy-oncology")
        sources = {s["id"]: s for s in registry["sources"]}
        primary = sources["src-milazzo-2006-ejc"]
        duplicate = sources["src-ejcancer-duplicate-pointer"]
        self.assertEqual(primary["canonical_work_id"], "src-milazzo-2006-ejc")
        self.assertEqual(duplicate["canonical_work_id"], "src-milazzo-2006-ejc")
        self.assertNotEqual(primary["url"], duplicate["url"])  # different publisher URLs, same work
        self.assertGreaterEqual(primary["occurrences"], 2)  # both supplied occurrences preserved

    def test_cards_may_not_cite_a_duplicate_pointer_directly(self):
        registry, _cards = validator.load_fixtures(REPO_ROOT / "knowledge" / "homeopathy-oncology")
        _errs, sources_by_id = validator.validate_source_registry(registry)
        card = {
            "id": "card-x", "evidence": {"source_ids": ["src-ejcancer-duplicate-pointer"]},
            "state": "insufficient_evidence", "safety": {"care_delay_warning": "x", "standard_care_statement": "x"},
        }
        errors = validator.validate_cards([card], sources_by_id)
        self.assertTrue(any("duplicate pointer" in e for e in errors))

    def test_rejects_duplicate_source_id(self):
        registry = {"sources": [
            {"id": "dup", "url": "https://a.example/", "source_type": "provider_page", "publication_status": "active", "evidence_eligibility": "context_only", "accessed_at": "2026-09-17", "canonical_work_id": "dup"},
            {"id": "dup", "url": "https://b.example/", "source_type": "provider_page", "publication_status": "active", "evidence_eligibility": "context_only", "accessed_at": "2026-09-17", "canonical_work_id": "dup"},
        ]}
        errors, _ = validator.validate_source_registry(registry)
        self.assertTrue(any("duplicate source id" in e for e in errors))

    def test_rejects_unrecorded_duplicate_url_across_two_ids(self):
        registry = {"sources": [
            {"id": "a", "url": "https://same.example/", "source_type": "provider_page", "publication_status": "active", "evidence_eligibility": "context_only", "accessed_at": "2026-09-17", "canonical_work_id": "a"},
            {"id": "b", "url": "https://same.example/", "source_type": "provider_page", "publication_status": "active", "evidence_eligibility": "context_only", "accessed_at": "2026-09-17", "canonical_work_id": "b"},
        ]}
        errors, _ = validator.validate_source_registry(registry)
        self.assertTrue(any("unrecorded duplicate URL" in e for e in errors))

    def test_requires_core_source_fields(self):
        registry = {"sources": [{"id": "incomplete", "url": "https://x.example/"}]}
        errors, _ = validator.validate_source_registry(registry)
        for field in validator.REQUIRED_SOURCE_FIELDS:
            self.assertTrue(any(field in e for e in errors), f"missing-field check not raised for {field}")

    def test_local_handout_status_must_be_awaiting_upload_or_found_and_audited(self):
        good = {"sources": [{"id": "src-local-apha-handout", "status": "found_and_audited"}]}
        self.assertEqual(validator.validate_local_handout_status(good), [])
        bad = {"sources": [{"id": "src-local-apha-handout", "status": "fabricated_placeholder"}]}
        self.assertTrue(validator.validate_local_handout_status(bad))
        missing = {"sources": []}
        self.assertTrue(validator.validate_local_handout_status(missing))

    def test_herbal_review_marked_out_of_scope(self):
        registry, _cards = validator.load_fixtures(REPO_ROOT / "knowledge" / "homeopathy-oncology")
        self.assertEqual(validator.validate_herbal_out_of_scope(registry), [])
        bad = {"sources": [{"id": "src-ovid-herbal-review-out-of-scope", "source_type": "systematic_review", "evidence_eligibility": "eligible"}]}
        self.assertTrue(validator.validate_herbal_out_of_scope(bad))


class EvidenceCardTests(unittest.TestCase):
    def _minimal_card(self, **overrides):
        card = {
            "id": "card-x",
            "cancer_context": "x", "disease_state": "x", "treatment_context": "x", "population": "x",
            "claim_or_purpose_studied": "x",
            "intervention": {
                "formulation_category": "x", "ingredients_known": "x", "potency_as_study_metadata": "x",
                "route": "x", "carrier_excipients": "x", "co_interventions": "x", "formulation_generalization_note": "x",
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

    def test_shipped_cards_have_no_errors(self):
        registry, cards_doc = validator.load_fixtures(REPO_ROOT / "knowledge" / "homeopathy-oncology")
        _errs, sources_by_id = validator.validate_source_registry(registry)
        errors = validator.validate_cards(cards_doc["cards"], sources_by_id)
        self.assertEqual(errors, [])

    def test_missing_required_field_is_rejected(self):
        card = self._minimal_card()
        del card["disease_state"]
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("missing required field 'disease_state'" in e for e in errors))

    def test_missing_intervention_field_is_rejected(self):
        card = self._minimal_card()
        del card["intervention"]["route"]
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("intervention missing required field 'route'" in e for e in errors))

    def test_autonomous_recommended_state_is_rejected(self):
        for bad_state in ["recommended", "effective", "proven", "supported"]:
            card = self._minimal_card(state=bad_state)
            errors = validator.validate_cards([card], {})
            self.assertTrue(any("not an allowed state" in e for e in errors), f"{bad_state} was not rejected")

    def test_forbidden_fields_are_rejected(self):
        for key in ["recommended_dose", "potency_selection", "repertorization", "product_purchase_link",
                    "clinic_referral", "diet_template", "homeopathic_diet", "calorie_calculator"]:
            card = self._minimal_card()
            card["evidence"][key] = "x"
            errors = validator.validate_cards([card], {})
            self.assertTrue(any(f"forbidden field '{key}'" in e for e in errors), f"{key} was not rejected")

    def test_cure_and_vague_claim_phrases_are_rejected(self):
        for phrase in ["this treats cancer", "side-effect free remedy", "a gentle detox", "boosts immunity naturally", "clinically proven remedy"]:
            card = self._minimal_card(claim_or_purpose_studied=phrase)
            errors = validator.validate_cards([card], {})
            self.assertTrue(any("forbidden phrase" in e for e in errors), f"phrase not caught: {phrase}")

    def test_missing_care_delay_warning_is_rejected(self):
        card = self._minimal_card(safety={"standard_care_statement": "x"})
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("care_delay_warning is required" in e for e in errors))

    def test_missing_standard_care_statement_is_rejected(self):
        card = self._minimal_card(safety={"care_delay_warning": "x"})
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("standard_care_statement is required" in e for e in errors))

    def test_unknown_source_reference_is_rejected(self):
        card = self._minimal_card(evidence={"summary": "x", "source_ids": ["src-does-not-exist"], "certainty": "low"})
        errors = validator.validate_cards([card], {})
        self.assertTrue(any("unknown source id" in e for e in errors))

    def test_retracted_source_requires_blocked_integrity_or_avoid_state(self):
        sources_by_id = {"src-retracted": {"id": "src-retracted", "source_type": "rct_retracted", "evidence_eligibility": "ineligible_retracted", "canonical_work_id": "src-retracted"}}
        card = self._minimal_card(evidence={"summary": "x", "source_ids": ["src-retracted"], "certainty": "none"}, state="research_only")
        errors = validator.validate_cards([card], sources_by_id)
        self.assertTrue(any("cites a retracted source" in e for e in errors))

        card_ok = self._minimal_card(evidence={"summary": "x", "source_ids": ["src-retracted"], "certainty": "none"}, state="blocked_integrity")
        errors_ok = validator.validate_cards([card_ok], sources_by_id)
        self.assertFalse(any("cites a retracted source" in e for e in errors_ok))

    def test_withdrawn_no_results_source_requires_blocked_no_results_or_avoid_state(self):
        sources_by_id = {"src-withdrawn": {"id": "src-withdrawn", "source_type": "trial_registry", "evidence_eligibility": "ineligible_withdrawn_no_results", "canonical_work_id": "src-withdrawn"}}
        card = self._minimal_card(evidence={"summary": "x", "source_ids": ["src-withdrawn"], "certainty": "none"}, state="general_education")
        errors = validator.validate_cards([card], sources_by_id)
        self.assertTrue(any("cites a withdrawn-no-results source" in e for e in errors))

    def test_animal_and_cell_and_case_report_and_narrative_sources_cannot_alone_justify_clinician_discussion(self):
        for source_type in ["preclinical_animal", "preclinical_in_vitro", "case_report", "narrative_review", "conference_handout", "provider_page", "trial_registry"]:
            sources_by_id = {"src-1": {"id": "src-1", "source_type": source_type, "evidence_eligibility": "context_only", "canonical_work_id": "src-1"}}
            card = self._minimal_card(evidence={"summary": "x", "source_ids": ["src-1"], "certainty": "low"}, state="clinician_discussion_only")
            errors = validator.validate_cards([card], sources_by_id)
            self.assertTrue(any("non-efficacy source types" in e for e in errors), f"{source_type} incorrectly allowed to justify clinician_discussion_only")

    def test_null_negative_mixed_and_retracted_findings_all_exist_in_shipped_cards(self):
        _registry, cards_doc = validator.load_fixtures(REPO_ROOT / "knowledge" / "homeopathy-oncology")
        result_directions = {c["result_direction"] for c in cards_doc["cards"]}
        for expected in ["null", "retracted", "mixed", "negative_safety_signal"]:
            self.assertIn(expected, result_directions)


class PublishGateTests(unittest.TestCase):
    def test_draft_without_approvals_cannot_publish(self):
        eligible, reasons = validator.check_publish_eligibility({"version": "0.1.0"})
        self.assertFalse(eligible)
        self.assertTrue(reasons)

    def test_disallowed_roles_cannot_satisfy_approval(self):
        for bad_role in validator.DISALLOWED_APPROVER_ROLES:
            record = {
                "version": "0.1.0",
                "approvals": {
                    "oncology_or_pharmacist": {"version": "0.1.0", "approved_by_role": bad_role},
                    "evidence_methodology_reviewer": {"version": "0.1.0", "approved_by_role": "evidence_methodology_reviewer"},
                },
            }
            eligible, reasons = validator.check_publish_eligibility(record)
            self.assertFalse(eligible, f"{bad_role} incorrectly allowed to satisfy an approval")

    def test_homeopathy_domain_reviewer_cannot_elevate_certainty_or_override(self):
        record = {
            "version": "0.1.0",
            "approvals": {
                "oncology_or_pharmacist": {"version": "0.1.0", "approved_by_role": "oncology_or_pharmacist"},
                "evidence_methodology_reviewer": {"version": "0.1.0", "approved_by_role": "evidence_methodology_reviewer"},
                "homeopathy_domain_reviewer": {"version": "0.1.0", "approved_by_role": "homeopathy_domain_reviewer", "elevates_certainty": True},
            },
        }
        eligible, reasons = validator.check_publish_eligibility(record)
        self.assertFalse(eligible)
        self.assertTrue(any("elevate evidence certainty" in r for r in reasons))

    def test_properly_dual_approved_card_can_publish(self):
        record = {
            "version": "0.1.0",
            "approvals": {
                "oncology_or_pharmacist": {"version": "0.1.0", "approved_by_role": "oncology_or_pharmacist"},
                "evidence_methodology_reviewer": {"version": "0.1.0", "approved_by_role": "evidence_methodology_reviewer"},
            },
        }
        eligible, reasons = validator.check_publish_eligibility(record)
        self.assertTrue(eligible, reasons)

    def test_shipped_draft_cards_all_correctly_fail_the_publish_gate(self):
        _registry, cards_doc = validator.load_fixtures(REPO_ROOT / "knowledge" / "homeopathy-oncology")
        for card in cards_doc["cards"]:
            eligible, _ = validator.check_publish_eligibility(card)
            self.assertFalse(eligible, f"{card['id']} should not be publish-eligible as a draft")


class AuditEventContractTests(unittest.TestCase):
    def test_complete_declared_set_passes(self):
        self.assertEqual(validator.validate_audit_event_contract(validator.AUDIT_EVENT_TYPES_REQUIRED), [])

    def test_incomplete_declared_set_is_rejected(self):
        incomplete = validator.AUDIT_EVENT_TYPES_REQUIRED - {"retract"}
        errors = validator.validate_audit_event_contract(incomplete)
        self.assertTrue(any("retract" in e for e in errors))


class NoNutritionContentTests(unittest.TestCase):
    def test_no_nutrition_or_diet_keys_anywhere_in_shipped_fixtures(self):
        registry, cards_doc = validator.load_fixtures(REPO_ROOT / "knowledge" / "homeopathy-oncology")
        for forbidden in ["diet_template", "meal_plan", "nutrition_recommendation", "homeopathic_diet"]:
            self.assertFalse(validator._has_key(registry, forbidden))
            self.assertFalse(validator._has_key(cards_doc, forbidden))

    def test_no_nutrition_fixture_file_exists(self):
        kb_dir = REPO_ROOT / "knowledge" / "homeopathy-oncology"
        names = {p.name for p in kb_dir.glob("*.json")}
        self.assertEqual(names, {"source_registry.json", "example_evidence_cards.json"})


class FullValidatorRunTests(unittest.TestCase):
    def test_main_returns_zero_on_shipped_fixtures(self):
        self.assertEqual(validator.main(), 0)


if __name__ == "__main__":
    unittest.main()
