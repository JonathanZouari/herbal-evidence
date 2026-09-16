#!/usr/bin/env python3
"""Dependency-free validator for the homeopathy-oncology-evidence proposal's
machine-readable knowledge fixtures (knowledge/homeopathy-oncology/).

This validates the PROPOSAL's fixtures and contracts only. It does not touch
the existing one-herb/appetite production data model, nor the separate
(unmerged) ayurveda-oncology-support proposal's tables or terminology.
"""

import json
import sys
from pathlib import Path

ALLOWED_STATES = {
    "avoid",
    "blocked_unsupported",
    "blocked_integrity",
    "blocked_no_results",
    "insufficient_evidence",
    "research_only",
    "clinician_discussion_only",
    "general_education",
}

# Source types that, alone, can never support a state implying real clinical
# discussion-worthiness (clinician_discussion_only) or anything stronger.
NON_EFFICACY_SOURCE_TYPES = {
    "preclinical_animal",
    "preclinical_in_vitro",
    "case_report",
    "narrative_review",
    "conference_handout",
    "provider_page",
    "trial_registry",
    "duplicate_pointer",
    "out_of_scope_adjacent",
    "institutional_regulatory_context",
}

STATES_ALLOWED_FOR_NON_EFFICACY_ONLY_CARDS = {
    "research_only",
    "avoid",
    "blocked_unsupported",
    "blocked_no_results",
    "general_education",
    "insufficient_evidence",
}

INELIGIBLE_EVIDENCE_VALUES = {"ineligible_retracted", "ineligible_withdrawn_no_results", "ineligible_commercial_or_advocacy"}

REQUIRED_STATE_FOR_RETRACTED_SOURCE = {"blocked_integrity", "avoid"}
REQUIRED_STATE_FOR_WITHDRAWN_SOURCE = {"blocked_no_results", "avoid"}

FORBIDDEN_PHRASES = [
    "cures cancer",
    "cure for cancer",
    "treats cancer",
    "prevents cancer",
    "kills cancer",
    "shrinks tumor",
    "shrinks tumour",
    "side-effect free",
    "side effect free",
    "non-toxic",
    "nontoxic",
    "detox",
    "blood purification",
    "blood-purification",
    "immune boosting",
    "immune-boosting",
    "boosts immunity",
    "clinically proven",
    "proven to cure",
    "instead of chemotherapy",
    "instead of standard treatment",
    "in place of standard care",
    "replace chemotherapy",
    "replace radiotherapy",
    "replace surgery",
    "stop your treatment",
    "skip chemotherapy",
    "delay chemotherapy",
]

FORBIDDEN_KEYS = [
    "recommended_dose",
    "potency_selection",
    "dosing_frequency",
    "frequency_instructions",
    "treatment_protocol_instructions",
    "repertorization",
    "repertory_selection",
    "self_treatment_instructions",
    "product_purchase_link",
    "purchase_link",
    "clinic_referral",
    "clinic_referral_link",
    "diet_template",
    "meal_plan",
    "nutrition_recommendation",
    "homeopathic_diet",
    "calorie_calculator",
    "protein_calculator",
]

REQUIRED_CARD_FIELDS = [
    "cancer_context",
    "disease_state",
    "treatment_context",
    "population",
    "claim_or_purpose_studied",
    "intervention",
    "comparator",
    "sample_size",
    "outcomes_prespecified",
    "outcome_type",
    "result_direction",
    "evidence",
    "limitations",
    "what_was_not_shown",
    "publication_integrity",
    "safety",
    "state",
]

REQUIRED_INTERVENTION_FIELDS = [
    "formulation_category",
    "ingredients_known",
    "potency_as_study_metadata",
    "route",
    "carrier_excipients",
    "co_interventions",
    "formulation_generalization_note",
]

REQUIRED_SOURCE_FIELDS = [
    "source_type",
    "publication_status",
    "evidence_eligibility",
    "accessed_at",
    "canonical_work_id",
]

REQUIRED_APPROVALS = {"oncology_or_pharmacist", "evidence_methodology_reviewer"}
DISALLOWED_APPROVER_ROLES = {
    "ai",
    "researcher",
    "editor",
    "administrator",
    "product_owner",
    "homeopathy_practitioner",
    "homeopathy_domain_reviewer",
}

AUDIT_EVENT_TYPES_REQUIRED = {
    "create", "edit", "approve", "reject", "suspend", "expire", "retract", "unpublish",
}


def _iter_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v)


def _has_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return True
        return any(_has_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_key(v, key) for v in obj)
    return False


def check_forbidden_phrases(record, errors, where):
    text = " ".join(_iter_strings(record)).lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            errors.append(f"{where}: forbidden phrase '{phrase}' found in patient-facing text")


def check_forbidden_keys(record, errors, where):
    for key in FORBIDDEN_KEYS:
        if _has_key(record, key):
            errors.append(f"{where}: forbidden field '{key}' is not permitted")


def canonicalize_urls(urls):
    """Given a raw, possibly-repeated list of supplied URLs, return
    {url: occurrence_count}, preserving duplicate counts."""
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

        if src.get("source_type") == "commercial" and src.get("evidence_eligibility") == "eligible":
            errors.append(f"{sid}: a commercial source cannot have evidence_eligibility=eligible")

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


def validate_local_handout_status(registry):
    for src in registry.get("sources", []):
        if src.get("id") == "src-local-apha-handout":
            status = src.get("status")
            if status not in ("awaiting_upload", "found_and_audited"):
                return [
                    f"local APHA handout status must be 'awaiting_upload' or "
                    f"'found_and_audited', got '{status!r}'"
                ]
            return []
    return ["local APHA handout source entry is missing from the registry"]


def validate_herbal_out_of_scope(registry):
    for src in registry.get("sources", []):
        if src.get("id") == "src-ovid-herbal-review-out-of-scope":
            if src.get("evidence_eligibility") != "out_of_scope" or src.get("source_type") != "out_of_scope_adjacent":
                return ["the herbal-medicine review source must be marked out_of_scope_adjacent / evidence_eligibility=out_of_scope"]
            return []
    return ["the herbal-medicine review source entry is missing from the registry"]


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
                f"(there is no autonomous recommended/effective/proven/supported state)"
            )

        check_forbidden_keys(card, errors, cid)
        check_forbidden_phrases(card, errors, cid)

        safety = card.get("safety", {})
        if not safety.get("care_delay_warning"):
            errors.append(f"{cid}: safety.care_delay_warning is required and must be non-empty")
        if not safety.get("standard_care_statement"):
            errors.append(f"{cid}: safety.standard_care_statement is required and must be non-empty")

        cited_ids = card.get("evidence", {}).get("source_ids", [])
        cited_source_types = set()
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

            if src.get("evidence_eligibility") == "ineligible_retracted" and state not in REQUIRED_STATE_FOR_RETRACTED_SOURCE:
                errors.append(
                    f"{cid}: cites a retracted source but state '{state}' is not in {sorted(REQUIRED_STATE_FOR_RETRACTED_SOURCE)}"
                )
            if src.get("evidence_eligibility") == "ineligible_withdrawn_no_results" and state not in REQUIRED_STATE_FOR_WITHDRAWN_SOURCE:
                errors.append(
                    f"{cid}: cites a withdrawn-no-results source but state '{state}' is not in {sorted(REQUIRED_STATE_FOR_WITHDRAWN_SOURCE)}"
                )

        if cited_ids and cited_source_types and cited_source_types.issubset(NON_EFFICACY_SOURCE_TYPES):
            if state not in STATES_ALLOWED_FOR_NON_EFFICACY_ONLY_CARDS:
                errors.append(
                    f"{cid}: all cited sources are non-efficacy source types {sorted(cited_source_types)}, "
                    f"so state '{state}' (implying real clinical discussion-worthiness or stronger) is not permitted"
                )

    return errors


def check_publish_eligibility(record):
    """Return (eligible, reasons). Publishing requires BOTH
    oncology_or_pharmacist AND evidence_methodology_reviewer approvals on the
    same immutable version. An optional homeopathy_domain_reviewer entry may
    exist but can never satisfy a required role or elevate certainty."""
    reasons = []
    approvals = record.get("approvals", {})
    version = record.get("version")

    for role in REQUIRED_APPROVALS:
        entry = approvals.get(role)
        if not entry:
            reasons.append(f"missing {role} approval")
            continue
        if entry.get("version") != version:
            reasons.append(f"{role} approval version mismatch: {entry.get('version')!r} != {version!r}")
        if entry.get("approved_by_role") in DISALLOWED_APPROVER_ROLES:
            reasons.append(f"{role} approval cannot be granted by role '{entry.get('approved_by_role')}'")

    homeopathy_entry = approvals.get("homeopathy_domain_reviewer")
    if homeopathy_entry:
        if homeopathy_entry.get("elevates_certainty") or homeopathy_entry.get("overrides_required_approval"):
            reasons.append(
                "homeopathy_domain_reviewer entry attempts to elevate evidence certainty or override a "
                "required approval, which is not permitted"
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
    return registry, cards_doc


def run_all_checks(registry, cards_doc):
    errors = []

    src_errors, sources_by_id = validate_source_registry(registry)
    errors += src_errors
    errors += validate_local_handout_status(registry)
    errors += validate_herbal_out_of_scope(registry)

    check_forbidden_keys(cards_doc, errors, "example_evidence_cards.json (document-level)")

    cards = cards_doc.get("cards", [])
    errors += validate_cards(cards, sources_by_id)

    for card in cards:
        eligible, _reasons = check_publish_eligibility(card)
        if eligible:
            errors.append(
                f"{card.get('id')}: draft card unexpectedly satisfied the publish-eligibility "
                f"gate (a draft with no recorded approvals must never pass)"
            )

    return errors, cards, list(sources_by_id.values())


def main():
    root = Path(__file__).resolve().parents[1]
    kb_dir = root / "knowledge" / "homeopathy-oncology"

    registry, cards_doc = load_fixtures(kb_dir)
    errors, cards, sources = run_all_checks(registry, cards_doc)

    if errors:
        print(f"FAIL: {len(errors)} issue(s) found")
        for e in errors:
            print(f" - {e}")
        return 1

    print(f"OK: {len(cards)} cards, {len(sources)} sources validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
