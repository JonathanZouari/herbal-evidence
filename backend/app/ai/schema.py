"""Draft / response / review content, schema_version "1".

Product rules encoded here: appetite is the primary outcome; food intake, weight and quality of life are reported
separately; the evidence base is a category, never a number; every finding cites a gathered source.
The same shape is a draft (response_drafts.content), a published body (responses.body) and, minus the personal
fields, a reusable review (evidence_reviews.content)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

StudyType = Literal["systematic_review", "rct", "controlled_trial", "observational", "case_series",
                    "animal", "in_vitro", "other"]
EvidenceBase = Literal["none_found", "preclinical_only", "limited_human", "mixed_human", "consistent_human"]
SecondaryOutcome = Literal["food_intake", "weight", "quality_of_life"]

ShortText = Annotated[str, Field(min_length=1, max_length=500)]
CONSULT_TEAM_NOTE = ("המידע כאן מסכם מחקרים ואינו המלצה טיפולית. לפני שימוש בכל צמח או תוסף, "
                     "חשוב להתייעץ עם הצוות המטפל, במיוחד בזמן טיפול אונקולוגי.")
NONE_FOUND_SUMMARY = "בחיפוש שערכנו במאגרי הספרות הרפואית לא נמצאו מחקרים שבדקו את הצמח הזה ואת השפעתו על התיאבון."


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HerbRef(Strict):
    name_he: str = Field(max_length=200)
    name_en: str | None = Field(max_length=200)
    latin_name: str | None = Field(max_length=200)


class Finding(Strict):
    source_ref: str = Field(max_length=200)
    study_type: StudyType
    population_he: str = Field(min_length=1, max_length=400)
    result_he: str = Field(min_length=1, max_length=800)


class OutcomeSection(Strict):
    summary_he: str = Field(min_length=1, max_length=1500)
    findings: list[Finding] = Field(max_length=20)


class SecondarySection(OutcomeSection):
    outcome: SecondaryOutcome


class SourceRef(Strict):
    ref: str = Field(max_length=200)
    title: str = Field(min_length=1, max_length=1000)
    journal: str | None = Field(max_length=500)
    year: int | None
    url: str | None = Field(max_length=500, pattern=r"^https://")


class Analysis(Strict):
    """What the AI writes. Herb, sources and schema_version are attached by the backend, never by the model."""
    evidence_base: EvidenceBase
    appetite: OutcomeSection
    secondary: list[SecondarySection] = Field(max_length=3)
    safety_notes_he: list[ShortText] = Field(max_length=10)
    limitations_he: list[ShortText] = Field(max_length=10)
    personal_context_he: str | None = Field(max_length=1500)
    consult_team_note_he: str = Field(min_length=1, max_length=600)


def _all_findings(m) -> list[Finding]:
    return [*m.appetite.findings, *(f for s in m.secondary for f in s.findings)]


class ReviewContent(Strict):
    schema_version: Literal["1"]
    herb: HerbRef
    evidence_base: EvidenceBase
    appetite: OutcomeSection
    secondary: list[SecondarySection] = Field(max_length=3)
    safety_notes_he: list[ShortText] = Field(max_length=10)
    limitations_he: list[ShortText] = Field(max_length=10)
    sources: list[SourceRef] = Field(max_length=40)

    @model_validator(mode="after")
    def _consistent(self, info: ValidationInfo):
        outcomes = [s.outcome for s in self.secondary]
        if len(outcomes) != len(set(outcomes)):
            raise ValueError("secondary outcomes must be unique")
        refs = {s.ref for s in self.sources}
        allowed = (info.context or {}).get("refs")
        for f in _all_findings(self):
            if f.source_ref not in refs:
                raise ValueError(f"finding cites unknown source {f.source_ref}")
            if allowed is not None and f.source_ref not in allowed:
                raise ValueError(f"finding cites a source that was not gathered: {f.source_ref}")
        if self.evidence_base == "none_found" and _all_findings(self):
            raise ValueError("none_found cannot have findings")
        return self


class DraftContent(ReviewContent):
    personal_context_he: str | None = Field(max_length=1500)
    consult_team_note_he: str = Field(min_length=1, max_length=600)


# ------------------------------------------------------------------ builders


def assemble_draft(herb: HerbRef, analysis: Analysis, sources: list[SourceRef]) -> DraftContent:
    """AI analysis + backend-owned fields. Only cited sources are listed in the draft."""
    cited = {f.source_ref for f in _all_findings(analysis)}
    return DraftContent(schema_version="1", herb=herb, sources=[s for s in sources if s.ref in cited],
                        **analysis.model_dump())


def none_found_draft(herb: HerbRef) -> DraftContent:
    """No literature at all: a deterministic statement, not AI content. Still reviewed by a researcher."""
    return DraftContent(
        schema_version="1", herb=herb, evidence_base="none_found",
        appetite=OutcomeSection(summary_he=NONE_FOUND_SUMMARY, findings=[]), secondary=[],
        safety_notes_he=[], limitations_he=["החיפוש כלל את PubMed ו-Europe PMC בלבד."], sources=[],
        personal_context_he=None, consult_team_note_he=CONSULT_TEAM_NOTE,
    )


def review_to_draft(review: ReviewContent) -> DraftContent:
    return DraftContent(**review.model_dump(), personal_context_he=None, consult_team_note_he=CONSULT_TEAM_NOTE)


def draft_to_review(draft: DraftContent) -> ReviewContent:
    """Herb-level content only: the personal context never enters a reusable review."""
    return ReviewContent(**draft.model_dump(exclude={"personal_context_he", "consult_team_note_he"}))


# ------------------------------------------------------------------ JSON schema for strict structured output

_DROP = {"title", "default", "minLength", "maxLength", "minItems", "maxItems", "pattern", "description"}


def _strictify(node):
    if isinstance(node, list):
        return [_strictify(x) for x in node]
    if not isinstance(node, dict):
        return node
    out = {k: _strictify(v) for k, v in node.items() if k not in _DROP and k != "properties"}
    if "properties" in node:   # property *names* are data, not keywords: never filter them
        out["properties"] = {k: _strictify(v) for k, v in node["properties"].items()}
    if out.get("type") == "object" and "properties" in out:
        out["additionalProperties"] = False
        out["required"] = list(out["properties"])
    return out


class HerbGuess(Strict):
    """What the AI returns for a herb photo. Names shown to the user come from `herbs` when `match` is a listed id."""
    is_plant: bool
    match: str                       # a listed herb id, or "none"
    latin_name: str | None = Field(max_length=200)
    name_he: str | None = Field(max_length=200)
    certainty: Literal["high", "medium", "low"]   # a category, never a number


def herb_guess_json_schema(ids: list[str]) -> dict:
    schema = _strictify(HerbGuess.model_json_schema())
    schema["properties"]["match"] = {"type": "string", "enum": [*ids, "none"]}
    return schema


def analysis_json_schema(refs: list[str]) -> dict:
    """Strict-mode schema (every key required, no extra keys); source_ref limited to the gathered refs.
    Length limits are enforced by Pydantic after the call, not by the provider."""
    schema = _strictify(Analysis.model_json_schema())
    schema["$defs"]["Finding"]["properties"]["source_ref"] = {"type": "string", "enum": refs}
    return schema
