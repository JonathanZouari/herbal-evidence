"""Soft content flags for the researcher (stored in response_drafts.meta.ai_flags). Never edits content:
the researcher decides; the flags only point at wording the product rules forbid."""

import re

from app.ai.schema import DraftContent

_RULES = {
    "dose": re.compile(r"\d+\s*(mg\b|g\b|ml\b|מ\"ג|מ״ג|מ\"ל|מ״ל|גרם|מיליגרם)|מינון|כפית|כפות|פעמים ביום|mg/kg", re.I),
    "recommendation": re.compile(r"מומלץ|אנו ממליצים|כדאי ל|יש ליטול|מומלץ ליטול|recommend", re.I),
    "cure_claim": re.compile(r"מרפא את הסרטן|מכווץ גידול|נוגד סרטן|הורג תאי סרטן|antitumou?r|cures? cancer", re.I),
    "numeric_score": re.compile(r"\d+\s*%|\d+\s*/\s*10|ציון", re.I),
}


def _texts(d: DraftContent) -> list[str]:
    sections = [d.appetite, *d.secondary]
    out = [s.summary_he for s in sections]
    out += [t for s in sections for f in s.findings for t in (f.population_he, f.result_he)]
    out += [*d.safety_notes_he, *d.limitations_he, d.personal_context_he or "", d.consult_team_note_he]
    return out


def flag_content(d: DraftContent) -> list[str]:
    text = "\n".join(_texts(d))
    return sorted(name for name, rx in _RULES.items() if rx.search(text))
