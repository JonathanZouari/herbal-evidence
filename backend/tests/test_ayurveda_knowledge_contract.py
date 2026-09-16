"""Contract tests for the ayurveda-oncology-support PROPOSAL's knowledge fixtures
and validator (scripts/validate_ayurveda_proposal.py). These are additive: they
do not touch the existing one-herb/appetite production tests or data model.

Only synthetic fixtures are used for the negative-path tests; the real
proposal fixtures under knowledge/ayurveda-oncology/ are used for the
positive-path "the shipped fixtures are clean" test.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_ayurveda_proposal.py"

_spec = importlib.util.spec_from_file_location("validate_ayurveda_proposal", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = validator
_spec.loader.exec_module(validator)


SUPPLIED_URLS = [
    "https://www.planetayurveda.com/ayurvedic-treatment-of-leukemia-blood-cancer/",
    "https://www.planetayurveda.eu/cancer/",
    "https://www.cancerresearchuk.org/about-cancer/treatment/complementary-alternative-therapies/individual-therapies/ayurvedic-medicine",
    "https://www.planetayurveda.com/treat-breast-cancer-in-men-naturally/",
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC10307689/",
    "https://www.youtube.com/watch?v=HRcnD_V6ZaA",
    "https://ayurvaid.com/specialities/oncology/",
    "https://www.planetayurveda.com/library/ayurvedic-treatment-for-bartholin-gland-cancer/",
    "https://oneworldayurveda.com/blog/cancer-care-in-ayurveda-a-holistic-approach-to-healing/",
    "https://www.planetayurveda.net/tag/cancer-treatment-supportive-care-tips/",
    "https://jaims.in/jaims/article/view/2482/3433",
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC3111701/",
    "https://www.planetayurveda.com/library/all-about-multiple-myeloma-and-its-ayurvedic-treatment/",
    "https://www.planetayurveda.com/library/all-about-multiple-myeloma-and-its-ayurvedic-treatment/",
    "https://www.dmhospital.org/specialty-details/INTEGRATIVE-CANCER-CARE",
    "https://alwaysayurveda.com/store/products/cancer-care-pack/",
    "https://www.aryavaidyasala.com/blogs/two-plants-in-cancer-treatment-breakthrough-in-arya-vaidya-salas-research/",
    "https://jeenasikho.com/diet-plan-for-cancer-patients/",
]


class CanonicalizeUrlsTests(unittest.TestCase):
    def test_duplicate_multiple_myeloma_url_preserved_as_count_two(self):
        counts = validator.canonicalize_urls(SUPPLIED_URLS)
        mm_url = "https://www.planetayurveda.com/library/all-about-multiple-myeloma-and-its-ayurvedic-treatment/"
        self.assertEqual(counts[mm_url], 2)
        self.assertEqual(len(counts), 17)  # 18 supplied, one duplicate collapses to one canonical entry


class SourceRegistryTests(unittest.TestCase):
    def test_shipped_registry_has_no_errors(self):
        registry, _cards, _templates = validator.load_fixtures(
            REPO_ROOT / "knowledge" / "ayurveda-oncology"
        )
        errors, known_ids = validator.validate_source_registry(registry)
        self.assertEqual(errors, [])
        self.assertIn("src-local-desktop-diet-chart", known_ids)

    def test_rejects_duplicate_source_id(self):
        registry = {"sources": [
            {"id": "dup", "url": "https://a.example/", "type": "commercial_clinic_page", "eligible_for_efficacy_claims": False},
            {"id": "dup", "url": "https://b.example/", "type": "commercial_clinic_page", "eligible_for_efficacy_claims": False},
        ]}
        errors, _ = validator.validate_source_registry(registry)
        self.assertTrue(any("duplicate source id" in e for e in errors))

    def test_rejects_unrecorded_duplicate_url_across_two_ids(self):
        registry = {"sources": [
            {"id": "a", "url": "https://same.example/", "type": "commercial_clinic_page", "eligible_for_efficacy_claims": False},
            {"id": "b", "url": "https://same.example/", "type": "commercial_clinic_page", "eligible_for_efficacy_claims": False},
        ]}
        errors, _ = validator.validate_source_registry(registry)
        self.assertTrue(any("unrecorded duplicate URL" in e for e in errors))

    def test_rejects_commercial_source_marked_eligible_for_efficacy_claims(self):
        registry = {"sources": [
            {"id": "bad", "url": "https://shop.example/pack", "type": "commercial_product_page", "eligible_for_efficacy_claims": True},
        ]}
        errors, _ = validator.validate_source_registry(registry)
        self.assertTrue(any("commercial source cannot have eligible_for_efficacy_claims=true" in e for e in errors))

    def test_local_chart_status_must_be_awaiting_upload_or_found_and_audited(self):
        good = {"sources": [{"id": "src-local-desktop-diet-chart", "status": "found_and_audited"}]}
        self.assertEqual(validator.validate_local_chart_status(good), [])

        bad = {"sources": [{"id": "src-local-desktop-diet-chart", "status": "fabricated_placeholder"}]}
        self.assertTrue(validator.validate_local_chart_status(bad))

        missing = {"sources": []}
        self.assertTrue(validator.validate_local_chart_status(missing))


class HerbCardTests(unittest.TestCase):
    def _minimal_valid_card(self, **overrides):
        card = {
            "id": "card-x",
            "cancer_context": "x",
            "disease_state": "x",
            "treatment_context": "x",
            "population": "x",
            "herb": {"species": "x", "preparation": "x"},
            "supportive_care_purpose": "x",
            "evidence": {"summary": "x", "source_ids": ["src-1"], "certainty": "low"},
            "limitations": "x",
            "safety": {"never_imply": [], "known_concerns": [], "red_flags_requiring_escalation": []},
            "state": "research_only",
        }
        card.update(overrides)
        return card

    def test_shipped_cards_have_no_errors(self):
        registry, cards_doc, _templates = validator.load_fixtures(
            REPO_ROOT / "knowledge" / "ayurveda-oncology"
        )
        _src_errors, known_ids = validator.validate_source_registry(registry)
        errors = validator.validate_cards(cards_doc["cards"], known_ids)
        self.assertEqual(errors, [])

    def test_missing_required_field_is_rejected(self):
        card = self._minimal_valid_card()
        del card["disease_state"]
        errors = validator.validate_cards([card], {"src-1"})
        self.assertTrue(any("missing required field 'disease_state'" in e for e in errors))

    def test_autonomous_recommended_state_is_rejected(self):
        card = self._minimal_valid_card(state="recommended")
        errors = validator.validate_cards([card], {"src-1"})
        self.assertTrue(any("not an allowed state" in e for e in errors))

    def test_recommended_dose_field_is_rejected_anywhere_in_the_card(self):
        card = self._minimal_valid_card()
        card["herb"]["recommended_dose"] = "500mg twice daily"
        errors = validator.validate_cards([card], {"src-1"})
        self.assertTrue(any("recommended_dose' is not permitted" in e for e in errors))

    def test_unknown_source_reference_is_rejected(self):
        card = self._minimal_valid_card()
        card["evidence"]["source_ids"] = ["src-does-not-exist"]
        errors = validator.validate_cards([card], {"src-1"})
        self.assertTrue(any("unknown source id" in e for e in errors))

    def test_cure_and_vague_claim_phrases_are_rejected(self):
        for phrase in ["this herb cures cancer", "side-effect free supplement", "a natural detox", "immune boosting formula"]:
            card = self._minimal_valid_card(supportive_care_purpose=phrase)
            errors = validator.validate_cards([card], {"src-1"})
            self.assertTrue(any("forbidden phrase" in e for e in errors), f"phrase not caught: {phrase}")

    def test_null_and_mixed_evidence_cards_are_kept_separate_not_merged(self):
        _registry, cards_doc, _templates = validator.load_fixtures(
            REPO_ROOT / "knowledge" / "ayurveda-oncology"
        )
        ids = {c["id"] for c in cards_doc["cards"]}
        self.assertIn("card-ginger-cinv-general", ids)   # mixed/positive evidence
        self.assertIn("card-ginger-ac-null", ids)         # null-result evidence, separate context
        null_card = next(c for c in cards_doc["cards"] if c["id"] == "card-ginger-ac-null")
        self.assertEqual(null_card["state"], "insufficient_evidence")


class DietTemplateTests(unittest.TestCase):
    def test_shipped_templates_have_no_errors(self):
        registry, _cards, templates_doc = validator.load_fixtures(
            REPO_ROOT / "knowledge" / "ayurveda-oncology"
        )
        _src_errors, known_ids = validator.validate_source_registry(registry)
        errors = validator.validate_diet_templates(templates_doc["templates"], known_ids)
        self.assertEqual(errors, [])

    def test_calculator_fields_are_rejected(self):
        tpl = {
            "id": "tpl-x", "goal": "x", "may_apply_when": [], "unsuitable_when": [],
            "flexible_food_pattern": "x", "indian_food_examples": [], "ayurvedic_tradition_context": "x",
            "biomedical_rationale": "x", "herb_supplement_note": "x", "red_flags_requiring_escalation": [],
            "sources": [], "calorie_calculator": True,
        }
        errors = validator.validate_diet_templates([tpl], set())
        self.assertTrue(any("calculator" in e for e in errors))


class PublishGateTests(unittest.TestCase):
    def test_draft_without_approvals_cannot_publish(self):
        eligible, reasons = validator.check_publish_eligibility({"version": "0.1.0"}, "herb_card")
        self.assertFalse(eligible)
        self.assertTrue(reasons)

    def test_ai_role_cannot_satisfy_approval(self):
        record = {
            "version": "0.1.0",
            "approvals": {
                "oncology_or_pharmacist": {"version": "0.1.0", "approved_by_role": "ai"},
                "ayurveda_clinician": {"version": "0.1.0", "approved_by_role": "ayurveda_clinician"},
            },
        }
        eligible, reasons = validator.check_publish_eligibility(record, "herb_card")
        self.assertFalse(eligible)
        self.assertTrue(any("cannot be granted by role 'ai'" in r for r in reasons))

    def test_mismatched_version_approval_rejected(self):
        record = {
            "version": "0.2.0",
            "approvals": {
                "oncology_or_pharmacist": {"version": "0.1.0", "approved_by_role": "oncology_or_pharmacist"},
                "ayurveda_clinician": {"version": "0.2.0", "approved_by_role": "ayurveda_clinician"},
            },
        }
        eligible, reasons = validator.check_publish_eligibility(record, "herb_card")
        self.assertFalse(eligible)
        self.assertTrue(any("version mismatch" in r for r in reasons))

    def test_properly_dual_approved_herb_card_can_publish(self):
        record = {
            "version": "0.1.0",
            "approvals": {
                "oncology_or_pharmacist": {"version": "0.1.0", "approved_by_role": "oncology_or_pharmacist"},
                "ayurveda_clinician": {"version": "0.1.0", "approved_by_role": "ayurveda_clinician"},
            },
        }
        eligible, reasons = validator.check_publish_eligibility(record, "herb_card")
        self.assertTrue(eligible, reasons)

    def test_diet_template_requires_oncology_dietitian_approval(self):
        record = {"version": "0.1.0", "approvals": {}}
        eligible, reasons = validator.check_publish_eligibility(record, "diet_template")
        self.assertFalse(eligible)
        self.assertTrue(any("oncology_dietitian" in r for r in reasons))

    def test_shipped_draft_fixtures_all_correctly_fail_the_publish_gate(self):
        _registry, cards_doc, templates_doc = validator.load_fixtures(
            REPO_ROOT / "knowledge" / "ayurveda-oncology"
        )
        for card in cards_doc["cards"]:
            eligible, _ = validator.check_publish_eligibility(card, "herb_card")
            self.assertFalse(eligible, f"{card['id']} should not be publish-eligible as a draft")
        for tpl in templates_doc["templates"]:
            eligible, _ = validator.check_publish_eligibility(tpl, "diet_template")
            self.assertFalse(eligible, f"{tpl['id']} should not be publish-eligible as a draft")


class FullValidatorRunTests(unittest.TestCase):
    def test_main_returns_zero_on_shipped_fixtures(self):
        self.assertEqual(validator.main(), 0)


if __name__ == "__main__":
    unittest.main()
