"""Shared test builders: valid schema-v1 content and a fake literature/AI HTTP layer (httpx.MockTransport)."""

import json
from pathlib import Path

import httpx

from app.ai.schema import CONSULT_TEAM_NOTE

FIXTURES = Path(__file__).parent / "fixtures"


def analysis(refs: list[str]) -> dict:
    return {
        "evidence_base": "limited_human" if refs else "none_found",
        "appetite": {
            "summary_he": "נמצא מחקר אחד בבני אדם שבדק תיאבון; לא נמצא הבדל מובהק.",
            "findings": [{"source_ref": r, "study_type": "rct", "population_he": "מטופלים בכימותרפיה",
                          "result_he": "לא נמצא הבדל בתיאבון."} for r in refs[:1]],
        },
        "secondary": [{"outcome": "weight", "summary_he": "לא נבדק במחקרים שנמצאו.", "findings": []}],
        "safety_notes_he": ["דווח על אינטראקציה אפשרית עם מדללי דם."],
        "limitations_he": ["מספר קטן של משתתפים."],
        "personal_context_he": None,
        "consult_team_note_he": CONSULT_TEAM_NOTE,
    }


def draft(refs: list[str] | None = None) -> dict:
    refs = ["pmid:11111111"] if refs is None else refs
    return {
        "schema_version": "1",
        "herb": {"name_he": "ג׳ינג׳ר", "name_en": "Ginger", "latin_name": "Zingiber officinale"},
        **analysis(refs),
        "sources": [{"ref": r, "title": f"Study {r}", "journal": "J", "year": 2021,
                     "url": "https://pubmed.ncbi.nlm.nih.gov/11111111/"} for r in refs],
    }


def openai_body(payload: dict | None = None, *, refusal: bool = False, text: str | None = None) -> dict:
    part = {"type": "refusal", "refusal": "no"} if refusal else \
        {"type": "output_text", "text": text if text is not None else json.dumps(payload, ensure_ascii=False)}
    return {"status": "completed", "output": [{"type": "reasoning"}, {"type": "message", "content": [part]}]}


def literature_transport(calls: list | None = None, *, pubmed_status: int = 200, epmc_status: int = 200,
                         pubmed_ids: list[str] | None = None) -> httpx.MockTransport:
    """PubMed esearch/efetch + Europe PMC search from fixtures; anything else is a test failure."""
    ids = ["11111111", "22222222"] if pubmed_ids is None else pubmed_ids

    def handler(req: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(req.url))
        path = req.url.path
        if req.url.host == "eutils.ncbi.nlm.nih.gov":
            if pubmed_status != 200:
                return httpx.Response(pubmed_status)
            if path.endswith("esearch.fcgi"):
                return httpx.Response(200, json={"esearchresult": {"idlist": ids}})
            if path.endswith("efetch.fcgi"):
                return httpx.Response(200, content=(FIXTURES / "efetch.xml").read_bytes())
        if req.url.host == "www.ebi.ac.uk":
            if epmc_status != 200:
                return httpx.Response(epmc_status)
            return httpx.Response(200, content=(FIXTURES / "europepmc.json").read_bytes())
        raise AssertionError(f"unexpected request {req.url}")

    return httpx.MockTransport(handler)


def failing_transport() -> httpx.MockTransport:
    def handler(req: httpx.Request) -> httpx.Response:
        raise AssertionError(f"no HTTP expected, got {req.url}")
    return httpx.MockTransport(handler)
