"""Phase 3 unit tests: fetcher safety, literature parsing, dedupe, schema, OpenAI adapter, content flags. No DB."""

import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.ai.guard import flag_content
from app.ai.openai import OpenAIProvider, parse_response
from app.ai.provider import DraftInput, NullProvider, ProviderError, ProviderNotConfigured, get_provider
from app.ai.schema import Analysis, DraftContent, analysis_json_schema, draft_to_review, review_to_draft
from app.research import europepmc, pubmed
from app.research.http import FetchError, RateLimiter, SafeClient, check_url
from app.research.sources import ResearchError, Source, build_terms, dedupe, pubmed_query
from app.settings import Settings
from tests.helpers import FIXTURES, analysis, draft, literature_transport, openai_body


def settings(**kw) -> Settings:
    return Settings(supabase_url="https://x.supabase.co", database_url="postgresql://x", _env_file=None, **kw)


# ------------------------------------------------------------------ fetcher


@pytest.mark.parametrize("url", [
    "http://eutils.ncbi.nlm.nih.gov/x",               # not https
    "https://evil.example.com/x",                     # not allowlisted
    "https://user:pw@www.ebi.ac.uk/x",                # credentials
    "https://www.ebi.ac.uk:8443/x",                   # port
    "https://169.254.169.254/latest/meta-data",       # metadata IP
    "https://eutils.ncbi.nlm.nih.gov.evil.com/x",     # suffix trick
])
def test_url_blocked(url):
    with pytest.raises(FetchError) as e:
        check_url(url)
    assert e.value.code == "url_blocked" and not e.value.retryable


def test_redirect_blocked_and_size_cap():
    redirect = httpx.MockTransport(lambda r: httpx.Response(302, headers={"location": "https://evil.example.com"}))
    with pytest.raises(FetchError) as e:
        SafeClient(transport=redirect).get("https://www.ebi.ac.uk/x")
    assert e.value.code == "redirect_blocked"

    big = httpx.MockTransport(lambda r: httpx.Response(200, content=b"x" * 2000))
    with pytest.raises(FetchError) as e:
        SafeClient(transport=big, max_bytes=1000).get("https://www.ebi.ac.uk/x")
    assert e.value.code == "response_too_large"

    ok = httpx.MockTransport(lambda r: httpx.Response(200, json={"a": 1}))
    assert SafeClient(transport=ok).get("https://www.ebi.ac.uk/x").json() == {"a": 1}


def test_gzip_body_decoded_once():
    import gzip
    t = httpx.MockTransport(lambda r: httpx.Response(200, headers={"content-encoding": "gzip"},
                                                     content=gzip.compress(b'{"ok": true}')))
    assert SafeClient(transport=t).get("https://www.ebi.ac.uk/x").json() == {"ok": True}


@pytest.mark.parametrize("status,code,retryable", [(500, "upstream_unavailable", True),
                                                   (429, "upstream_unavailable", True),
                                                   (400, "upstream_rejected", False)])
def test_status_mapping(status, code, retryable):
    t = httpx.MockTransport(lambda r: httpx.Response(status))
    with pytest.raises(FetchError) as e:
        SafeClient(transport=t).get("https://www.ebi.ac.uk/x")
    assert (e.value.code, e.value.retryable) == (code, retryable)


def test_transport_error_hides_url_with_key():
    def boom(r):
        raise httpx.ConnectError(f"cannot connect to {r.url}")
    with pytest.raises(FetchError) as e:
        SafeClient(transport=httpx.MockTransport(boom)).get("https://eutils.ncbi.nlm.nih.gov/x",
                                                            params={"api_key": "SECRET123"})
    assert e.value.retryable and "SECRET123" not in str(e.value)


def test_rate_limiter_spacing():
    t = [0.0]
    slept = []
    lim = RateLimiter(3, clock=lambda: t[0], sleep=slept.append)
    for _ in range(3):
        lim.wait()
    assert slept == pytest.approx([1 / 3, 2 / 3])


# ------------------------------------------------------------------ literature


def test_pubmed_parse():
    out = pubmed.parse_efetch((FIXTURES / "efetch.xml").read_bytes())
    a, b = out
    assert a.pmid == "11111111" and a.doi == "10.1000/abc.123" and a.pmcid == "PMC9999999"
    assert a.title.startswith("Ginger for chemotherapy-related") and a.pub_year == 2021
    assert a.abstract == "BACKGROUND: Appetite loss is common.\nRESULTS: No significant difference in appetite scores."
    assert b.pub_year == 2019 and b.abstract is None and b.url == "https://pubmed.ncbi.nlm.nih.gov/22222222/"


def test_pubmed_search_sends_key_and_tool():
    calls = []
    client = SafeClient(transport=literature_transport(calls))
    out = pubmed.search(client, "q", 5, api_key="K", tool="t", email="e@x.org")
    assert len(out) == 2 and "api_key=K" in calls[0] and "tool=t" in calls[0] and "efetch" in calls[1]


def test_europepmc_parse_and_dedupe():
    client = SafeClient(transport=literature_transport())
    epmc = europepmc.search(client, "q", 10)
    assert len(epmc) == 2                                  # the record without identifiers is dropped
    merged = dedupe(epmc + pubmed.parse_efetch((FIXTURES / "efetch.xml").read_bytes()))
    assert len(merged) == 3
    first = next(s for s in merged if s.pmid == "11111111")
    assert first.origin == "pubmed" and first.journal == "Supportive Care in Cancer"   # PubMed wins
    assert next(s for s in merged if s.doi == "10.2000/preprint.9").ref == "doi:10.2000/preprint.9"


def test_dedupe_fills_gaps_from_other_source():
    a = Source(title="A", origin="pubmed", pmid="1")
    b = Source(title="A'", origin="europepmc", pmid="1", doi="10.1/X", abstract="abs")
    (m,) = dedupe([b, a])
    assert m.origin == "pubmed" and m.title == "A" and m.doi == "10.1/X" and m.abstract == "abs"


def test_build_terms():
    herb = {"name_en": "Ginger", "latin_name": "Zingiber officinale"}
    assert build_terms(herb, "ג׳ינג׳ר") == ["Ginger", "Zingiber officinale"]
    assert build_terms(None, "Ashwagandha") == ["Ashwagandha"]
    assert build_terms({"name_en": 'Gin"seng[x]', "latin_name": None}, "") == ["Ginsengx"]   # no query injection
    with pytest.raises(ResearchError):
        build_terms(None, 'Ginseng"] OR (x')
    with pytest.raises(ResearchError) as e:
        build_terms(None, "צמח מסתורי")
    assert e.value.code == "herb_unidentified" and not e.value.retryable
    q = pubmed_query(["Ginger"])
    assert '"Ginger"[tiab]' in q and '"appetite"[tiab]' in q and "neoplasms[mh]" in q


# ------------------------------------------------------------------ schema


def test_schema_valid_and_round_trips():
    d = DraftContent.model_validate(draft())
    review = draft_to_review(d)
    assert "personal_context_he" not in review.model_dump()
    assert review_to_draft(review).appetite == d.appetite


@pytest.mark.parametrize("mutate,msg", [
    (lambda d: d.update(extra=1), "extra"),
    (lambda d: d["appetite"]["findings"][0].update(source_ref="pmid:999"), "unknown source"),
    (lambda d: d.update(evidence_base="none_found"), "none_found"),
    (lambda d: d.update(evidence_base=0.8), "evidence_base"),
    (lambda d: d["secondary"].append(dict(d["secondary"][0])), "unique"),
    (lambda d: d["sources"][0].update(url="javascript:alert(1)"), "url"),
])
def test_schema_rejects(mutate, msg):
    d = draft()
    mutate(d)
    with pytest.raises(ValidationError):
        DraftContent.model_validate(d)


def test_schema_context_refs():
    with pytest.raises(ValidationError):
        DraftContent.model_validate(draft(), context={"refs": {"pmid:2"}})
    DraftContent.model_validate(draft(), context={"refs": {"pmid:11111111"}})


def test_strict_json_schema():
    schema = analysis_json_schema(["pmid:1", "doi:10.1/x"])

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            assert not {"maxLength", "default", "title"} & set(node) - {"properties"}
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(schema)
    assert schema["$defs"]["Finding"]["properties"]["source_ref"]["enum"] == ["pmid:1", "doi:10.1/x"]


# ------------------------------------------------------------------ AI provider

INP = DraftInput(herb={"name_he": "ג׳ינג׳ר", "name_en": "Ginger", "latin_name": None},
                 request={"preparation": None, "cancer_type": "שד", "treatment": None},
                 sources=[Source(title="T", origin="pubmed", pmid="11111111", abstract="x" * 5000)])


def _provider(handler) -> OpenAIProvider:
    return OpenAIProvider(SafeClient(transport=httpx.MockTransport(handler)), "sk-test-SECRET", "some-model")


def test_openai_request_and_success():
    seen = {}

    def handler(r: httpx.Request):
        seen["auth"], seen["body"] = r.headers["authorization"], json.loads(r.content)
        return httpx.Response(200, json=openai_body(analysis(["pmid:11111111"])))
    out = _provider(handler).generate(INP)
    assert isinstance(out, Analysis) and out.appetite.findings[0].source_ref == "pmid:11111111"
    body = seen["body"]
    assert seen["auth"] == "Bearer sk-test-SECRET" and body["model"] == "some-model" and body["store"] is False
    assert body["text"]["format"]["strict"] is True and body["text"]["format"]["type"] == "json_schema"
    person = json.loads(body["input"])["person"]
    assert person == {"preparation": "לא ידוע", "cancer_type": "שד", "treatment": "לא ידוע"}
    assert len(json.loads(body["input"])["sources"][0]["abstract"]) == 2500


@pytest.mark.parametrize("response,code,retryable", [
    (httpx.Response(401), "ai_auth_failed", False),
    (httpx.Response(429), "ai_unavailable", True),
    (httpx.Response(503), "ai_unavailable", True),
    (httpx.Response(400), "ai_request_rejected", False),
    (httpx.Response(200, json=openai_body(refusal=True)), "ai_refused", False),
    (httpx.Response(200, json=openai_body(text="{not json")), "ai_bad_output", True),
    (httpx.Response(200, json=openai_body(analysis(["pmid:404"]))), "ai_bad_output", True),
    (httpx.Response(200, json={"status": "incomplete", "output": []}), "ai_bad_output", True),
])
def test_openai_errors(response, code, retryable):
    with pytest.raises(ProviderError) as e:
        _provider(lambda r: response).generate(INP)
    assert (e.value.code, e.value.retryable) == (code, retryable)
    assert "SECRET" not in str(e.value) and "SECRET" not in repr(_provider(lambda r: response))


def test_parse_response_ignores_non_message_items():
    assert parse_response(json.dumps(openai_body(analysis([]))).encode(), set()).evidence_base == "none_found"


def test_get_provider_falls_back_to_null():
    http = SafeClient()
    assert isinstance(get_provider(settings(ai_provider="none"), http), NullProvider)
    assert isinstance(get_provider(settings(ai_provider="openai", ai_model="m"), http), NullProvider)       # no key
    assert isinstance(get_provider(settings(ai_provider="openai", ai_api_key=SecretStr("k")), http), NullProvider)
    assert isinstance(get_provider(settings(ai_provider="openai", ai_model="m", ai_api_key=SecretStr("k")), http),
                      OpenAIProvider)
    with pytest.raises(ProviderNotConfigured):
        NullProvider().generate(INP)


def test_flag_content():
    d = DraftContent.model_validate(draft())
    assert flag_content(d) == []
    bad = draft()
    bad["appetite"]["summary_he"] = "מומלץ ליטול 500 מ״ג פעמיים ביום"
    assert flag_content(DraftContent.model_validate(bad)) == ["dose", "recommendation"]
    ok = draft()
    ok["appetite"]["findings"][0]["population_he"] = "2 groups of patients"   # "2 g" is not a dose
    assert flag_content(DraftContent.model_validate(ok)) == []
