"""Prompt for the evidence-review draft. Output is a draft for a researcher, never shown to users as-is."""

import json

from app.ai.provider import DraftInput

MAX_SOURCES = 20
MAX_ABSTRACT_CHARS = 2500

INSTRUCTIONS = """\
You draft an evidence summary in Hebrew for a researcher, who will edit and approve it before a person with cancer
(or their caregiver) reads it. The person chose ONE herb and asked whether it may improve APPETITE.

Rules (all mandatory):
- Describe what the provided studies found. Never recommend, encourage or discourage use.
- No dosing, amounts, schedules or preparation instructions of any kind.
- No claims about treating, shrinking or curing cancer; antitumor effects are out of scope.
- No numeric scores, percentages of certainty or ratings. evidence_base is a category only.
- Appetite is the primary outcome (field "appetite"). Food intake, weight and quality of life go ONLY in
  "secondary", one section per outcome, and only when a provided study reports them.
- Use ONLY the provided sources. Every finding's source_ref must be one of the given refs. If the sources do not
  address an outcome, say so plainly instead of guessing. Distinguish human studies from animal / in-vitro work.
- safety_notes_he: known interactions or cautions reported in the sources (e.g. with chemotherapy, anticoagulants),
  stated generally; say when the sources report none. limitations_he: weaknesses of the evidence.
- personal_context_he: relate the person's stated preparation / cancer type / treatment to the evidence (e.g.
  "no study examined this preparation"), without advice. null if nothing was stated.
- consult_team_note_he: one or two sentences reminding them to discuss any herb with their treating team.
- Plain, calm Hebrew for non-experts. Latin/English names and study terms may stay in English.
"""


def build_input(inp: DraftInput) -> str:
    unknown = "לא ידוע"
    payload = {
        "herb": inp.herb,
        "person": {k: (inp.request.get(k) or unknown) for k in ("preparation", "cancer_type", "treatment")},
        "sources": [
            {"ref": s.ref, "title": s.title, "journal": s.journal, "year": s.pub_year,
             "abstract": (s.abstract or "")[:MAX_ABSTRACT_CHARS] or None}
            for s in inp.sources[:MAX_SOURCES]
        ],
    }
    return json.dumps(payload, ensure_ascii=False)
