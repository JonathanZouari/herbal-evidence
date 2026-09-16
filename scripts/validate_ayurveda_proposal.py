#!/usr/bin/env python3
"""Dependency-free validator for the ayurveda-oncology-support proposal's
machine-readable knowledge fixtures (knowledge/ayurveda-oncology/).

This validates the PROPOSAL's fixtures and contracts only. It does not touch
the existing one-herb/appetite production data model or tables.
"""

import json
import sys
from pathlib import Path

ALLOWED_STATES = {
    "avoid",
    "blocked_unsupported",
    "insufficient_evidence",
    "research_only",
    "clinician_discussion_only",
    "general_education",
}

FORBIDDEN_PHRASES = [
    "side-effect free",
    "side effect free",
    "blood purification",
    "blood-purification",
    "immune boosting",
    "immune-boosting",
    "boosts immunity",
    "detox",
    "cures cancer",
    "cure for cancer",
    "treats cancer",
    "kills cancer",
    "shrinks tumor",
    "shrinks tumour",
    "prevents cancer",
]

REQUIRED_CARD_FIELDS = [
    "cancer_context",
    "disease_state",
    "treatment_context",
    "population",
    "herb",
    "supportive_care_purpose",
    "evidence",
    "limitations",
    "safety",
    "state",
]

REQUIRED_DIET_TEMPLATE_FIELDS = [
    "goal",
    "may_apply_when",
    "unsuitable_when",
    "flexible_food_pattern",
    "indian_food_examples",
    "ayurvedic_tradition_context",
    "biomedical_rationale",
    "herb_supplement_note",
    "red_flags_requiring_escalation",
    "sources",
]

REQUIRED_APPROVALS_HERB = {"oncology_or_pharmacist", "ayurveda_clinician"}
REQUIRED_APPROVALS_DIET = {"oncology_dietitian"}

DISALLOWED_APPROVER_ROLES = {"ai", "researcher", "editor", "administrator"}


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


def canonicalize_urls(urls):
    """Given a raw, possibly-repeated list of supplied URLs, return
    {url: occurrence_count}, preserving duplicate counts rather than
    silently collapsing them."""
    counts = {}
    for u in urls:
        counts[u] = counts.get(u, 0) + 1
    return counts


def validate_source_registry(registry):
    errors = []
    sources = registry.get("sources", [])
    seen_ids = set()
    url_to_ids = {}

    for src in sources:
        sid = src.get("id")
        if not sid:
            errors.append("source entry missing 'id'")
            continue
        if sid in seen_ids:
            errors.append(f"duplicate source id: {sid}")
        seen_ids.add(sid)

        url = src.get("url")
        if url:
            url_to_ids.setdefault(url, []).append(sid)

        stype = src.get("type") or ""
        if "commercial" in stype and src.get("eligible_for_efficacy_claims") is True:
            errors.append(
                f"{sid}: commercial source cannot have eligible_for_efficacy_claims=true"
            )

    for url, ids in url_to_ids.items():
        if len(ids) > 1:
            errors.append(
                f"unrecorded duplicate URL across distinct source ids "
                f"(must canonicalize to one id with an 'occurrences' count): {url} -> {ids}"
            )

    return errors, seen_ids


def validate_local_chart_status(registry):
    for src in registry.get("sources", []):
        if src.get("id") == "src-local-desktop-diet-chart":
            status = src.get("status")
            if status not in ("awaiting_upload", "found_and_audited"):
                return [
                    f"local diet chart status must be 'awaiting_upload' or "
                    f"'found_and_audited', got '{status!r}'"
                ]
            return []
    return ["local diet chart source entry is missing from the registry"]


def validate_cards(cards, known_source_ids):
    errors = []
    for card in cards:
        cid = card.get("id", "<missing id>")

        for field in REQUIRED_CARD_FIELDS:
            if field not in card:
                errors.append(f"{cid}: missing required field '{field}'")

        state = card.get("state")
        if state not in ALLOWED_STATES:
            errors.append(
                f"{cid}: state '{state}' is not an allowed state "
                f"(an autonomous 'recommended' state or any unknown state is rejected)"
            )

        if _has_key(card, "recommended_dose"):
            errors.append(f"{cid}: 'recommended_dose' is not permitted on a herb card")

        evidence = card.get("evidence", {})
        for sid in evidence.get("source_ids", []):
            if sid not in known_source_ids:
                errors.append(f"{cid}: references unknown source id '{sid}'")

        check_forbidden_phrases(card, errors, cid)

    return errors


def validate_diet_templates(templates, known_source_ids):
    errors = []
    for tpl in templates:
        tid = tpl.get("id", "<missing id>")

        for field in REQUIRED_DIET_TEMPLATE_FIELDS:
            if field not in tpl:
                errors.append(f"{tid}: missing required field '{field}'")

        if _has_key(tpl, "recommended_dose"):
            errors.append(f"{tid}: 'recommended_dose' is not permitted on a diet template")
        if _has_key(tpl, "calorie_calculator") or _has_key(tpl, "protein_calculator"):
            errors.append(f"{tid}: automatic calorie/protein calculators are not permitted")

        for sid in tpl.get("sources", []):
            if sid not in known_source_ids:
                errors.append(f"{tid}: references unknown source id '{sid}'")

        check_forbidden_phrases(tpl, errors, tid)

    return errors


def check_publish_eligibility(record, record_type):
    """Return (eligible, reasons). A herb_card additionally requires
    oncology_or_pharmacist AND ayurveda_clinician approvals on the SAME
    immutable version; a diet_template requires oncology_dietitian approval.
    No AI/researcher/editor/administrator role may satisfy these."""
    reasons = []
    approvals = record.get("approvals", {})
    version = record.get("version")

    required = REQUIRED_APPROVALS_HERB if record_type == "herb_card" else REQUIRED_APPROVALS_DIET
    for role in required:
        entry = approvals.get(role)
        if not entry:
            reasons.append(f"missing {role} approval")
            continue
        if entry.get("version") != version:
            reasons.append(
                f"{role} approval version mismatch: {entry.get('version')!r} != {version!r}"
            )
        if entry.get("approved_by_role") in DISALLOWED_APPROVER_ROLES:
            reasons.append(
                f"{role} approval cannot be granted by role '{entry.get('approved_by_role')}'"
            )

    return (len(reasons) == 0, reasons)


def load_fixtures(kb_dir: Path):
    registry = json.loads((kb_dir / "source_registry.json").read_text())
    cards_doc = json.loads((kb_dir / "example_cards.json").read_text())
    templates_doc = json.loads((kb_dir / "diet_template_examples.json").read_text())
    return registry, cards_doc, templates_doc


def run_all_checks(registry, cards_doc, templates_doc):
    errors = []

    src_errors, known_ids = validate_source_registry(registry)
    errors += src_errors
    errors += validate_local_chart_status(registry)

    cards = cards_doc.get("cards", [])
    templates = templates_doc.get("templates", [])

    errors += validate_cards(cards, known_ids)
    errors += validate_diet_templates(templates, known_ids)

    for card in cards:
        eligible, _reasons = check_publish_eligibility(card, "herb_card")
        if eligible:
            errors.append(
                f"{card.get('id')}: draft card unexpectedly satisfied the publish-eligibility "
                f"gate (a draft with no recorded approvals must never pass)"
            )

    for tpl in templates:
        eligible, _reasons = check_publish_eligibility(tpl, "diet_template")
        if eligible:
            errors.append(
                f"{tpl.get('id')}: draft template unexpectedly satisfied the publish-eligibility gate"
            )

    return errors, cards, templates, registry.get("sources", [])


def main():
    root = Path(__file__).resolve().parents[1]
    kb_dir = root / "knowledge" / "ayurveda-oncology"

    registry, cards_doc, templates_doc = load_fixtures(kb_dir)
    errors, cards, templates, sources = run_all_checks(registry, cards_doc, templates_doc)

    if errors:
        print(f"FAIL: {len(errors)} issue(s) found")
        for e in errors:
            print(f" - {e}")
        return 1

    print(
        f"OK: {len(cards)} cards, {len(templates)} diet templates, "
        f"{len(sources)} sources validated"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
