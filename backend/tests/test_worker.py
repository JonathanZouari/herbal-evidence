"""Research worker against the dev DB. Each test runs in a savepoint that is always rolled back; claims are scoped
to the test's own request (claim_job p_request_id) so seeded or other queued jobs are never touched."""

import httpx
import pytest
from psycopg.types.json import Jsonb

from app.ai.provider import NullProvider
from app.ai.schema import Analysis, DraftContent, draft_to_review
from app.jobs.research import Deps
from app.jobs.worker import Worker
from app.research.http import SafeClient
from app.settings import Settings
from tests.conftest import as_, needs_db, submit
from tests.helpers import analysis, draft, failing_transport, literature_transport

pytestmark = needs_db
S = Settings(supabase_url="https://x.supabase.co", database_url="postgresql://x", _env_file=None,
             worker_lease_seconds=60, literature_max_results=5)


@pytest.fixture(autouse=True)
def isolated(conn):
    with conn.transaction(force_rollback=True):
        yield


class FakeProvider:
    """Test double only: returns a valid analysis citing the first gathered source."""
    name, model = "fake", "fake-1"

    def __init__(self):
        self.calls = []

    def generate(self, inp):
        self.calls.append(inp)
        return Analysis.model_validate(analysis([inp.sources[0].ref]))


class ExplodingProvider:
    name, model = "boom", "x"

    def generate(self, inp):
        raise AssertionError("AI must not be called")


def worker(provider=None, transport=None) -> Worker:
    http = SafeClient(transport=transport or literature_transport())
    return Worker(S, None, Deps(http=http, provider=provider or NullProvider(), settings=S))


def state(conn, rid):
    req = conn.execute("select status from public.requests where id = %s", (rid,)).fetchone()
    job = conn.execute("select * from public.research_jobs where request_id = %s order by id desc limit 1",
                       (rid,)).fetchone()
    return req["status"], job


def test_no_ai_key_fails_structurally_but_keeps_sources(client, conn, users):
    rid = submit(client, users["a"]).json()["id"]
    assert worker().run_once(conn, rid) == "failed:ai_not_configured:dead"
    status, job = state(conn, rid)
    assert status == "research_failed" and job["status"] == "dead"
    assert job["last_error"]["code"] == "ai_not_configured" and job["last_error"]["stage"] == "generate"
    n = conn.execute("select count(*) as n from public.request_sources where request_id = %s", (rid,)).fetchone()["n"]
    assert n == 3                                            # PubMed 2 + Europe PMC 2, one duplicate merged
    assert conn.execute("select count(*) as n from public.response_drafts where request_id = %s",
                        (rid,)).fetchone()["n"] == 0         # never mock content
    mine = client.get(f"/api/v1/requests/{rid}", headers=as_(users["a"])).json()
    assert mine["public_status"] == "in_progress" and "last_error" not in str(mine)
    events = [e["to_status"] for e in conn.execute(
        "select to_status, actor_id from public.request_events where request_id = %s order by id", (rid,)).fetchall()]
    assert events == ["submitted", "researching", "research_failed"]


def test_happy_path_creates_validated_draft(client, conn, users):
    rid = submit(client, users["a"], cancer_type="שד").json()["id"]
    fake = FakeProvider()
    assert worker(fake).run_once(conn, rid) == "draft_ready"
    status, job = state(conn, rid)
    assert status == "draft_ready" and job["status"] == "succeeded"
    d = conn.execute("select * from public.response_drafts where request_id = %s", (rid,)).fetchone()
    content = DraftContent.model_validate(d["content"])
    assert d["job_id"] == job["id"] and d["ai_provider"] == "fake" and d["evidence_review_id"] is None
    assert [s.ref for s in content.sources] == ["pmid:11111111"]            # only cited sources listed
    assert d["meta"]["counts"] == {"pubmed": 2, "europepmc": 2, "deduped": 3} and d["meta"]["ai_flags"] == []
    assert fake.calls[0].request["cancer_type"] == "שד"


def test_no_literature_gives_deterministic_none_found(client, conn, users):
    rid = submit(client, users["a"]).json()["id"]
    empty = httpx.MockTransport(lambda r: httpx.Response(
        200, json={"esearchresult": {"idlist": []}} if r.url.host == "eutils.ncbi.nlm.nih.gov" else {"resultList": {"result": []}}))
    assert worker(ExplodingProvider(), empty).run_once(conn, rid) == "draft_ready"
    d = conn.execute("select content, ai_provider from public.response_drafts where request_id = %s", (rid,)).fetchone()
    assert d["content"]["evidence_base"] == "none_found" and d["ai_provider"] is None


def test_reuses_approved_review_without_ai_or_http(client, conn, users):
    herb = conn.execute("select id from public.herbs where name_en = 'Turmeric'").fetchone()["id"]
    review = draft_to_review(DraftContent.model_validate(draft()))
    rev_id = conn.execute(
        """insert into public.evidence_reviews (herb_id, version, content, approved_by, approved_at)
           values (%s, (select coalesce(max(version), 0) + 1 from public.evidence_reviews where herb_id = %s), %s, %s, now())
           returning id""", (herb, herb, Jsonb(review.model_dump(mode="json")), users["res"])).fetchone()["id"]
    rid = submit(client, users["a"], herb="כורכום").json()["id"]
    assert worker(ExplodingProvider(), failing_transport()).run_once(conn, rid) == "draft_ready"
    d = conn.execute("select * from public.response_drafts where request_id = %s", (rid,)).fetchone()
    assert d["evidence_review_id"] == rev_id and d["ai_provider"] is None and d["content"]["personal_context_he"] is None

    # still needs the assigned researcher's own approval
    client.post(f"/api/v1/admin/requests/{rid}/assign", json={"researcher_id": str(users["res"])}, headers=as_(users["admin"]))
    client.post(f"/api/v1/staff/requests/{rid}/start-review", headers=as_(users["res"]))
    assert client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": d["content"]},
                       headers=as_(users["admin"])).status_code == 403
    assert client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": d["content"]},
                       headers=as_(users["res"])).status_code == 204
    assert conn.execute("select evidence_review_id from public.responses where request_id = %s",
                        (rid,)).fetchone()["evidence_review_id"] == rev_id

    # rerun is refused after publish
    assert client.post(f"/api/v1/staff/requests/{rid}/rerun", json={"fresh": True},
                       headers=as_(users["res"])).status_code == 409


def test_mock_review_and_mock_jobs_ignored(client, conn, users):
    rid = submit(client, users["a"], herb="חילבה").json()["id"]         # Fenugreek has a MOCK review in the seed
    assert worker().run_once(conn, rid) == "failed:ai_not_configured:dead"   # searched, not reused
    conn.execute("""insert into public.research_jobs (kind, request_id, idempotency_key, payload)
                    values ('research', %s, 'mock:test', '{"mock": true}')""", (rid,))
    assert worker().run_once(conn, rid) is None


def test_withdrawn_before_claim_is_noop(client, conn, users):
    rid = submit(client, users["a"]).json()["id"]
    client.post(f"/api/v1/requests/{rid}/withdraw", headers=as_(users["a"]))
    assert worker(ExplodingProvider(), failing_transport()).run_once(conn, rid) == "noop:withdrawn"
    status, job = state(conn, rid)
    assert status == "withdrawn" and job["status"] == "succeeded"


def test_unknown_herb_then_staff_sets_herb_and_reruns(client, conn, users):
    rid = submit(client, users["a"], herb="צמח מסתורי").json()["id"]
    assert worker().run_once(conn, rid) == "failed:herb_unidentified:dead"
    ginger = conn.execute("select id from public.herbs where name_en = 'Ginger'").fetchone()["id"]
    assert client.patch(f"/api/v1/staff/requests/{rid}/herb", json={"herb_id": ginger},
                        headers=as_(users["admin"])).status_code == 204
    assert client.post(f"/api/v1/staff/requests/{rid}/rerun", headers=as_(users["admin"])).status_code == 202
    assert worker(FakeProvider()).run_once(conn, rid) == "draft_ready"


def test_retryable_failure_backs_off_then_dies(client, conn, users):
    rid = submit(client, users["a"]).json()["id"]
    down = literature_transport(pubmed_status=503, epmc_status=503)
    assert worker(transport=down).run_once(conn, rid) == "failed:literature_unavailable:queued"
    status, job = state(conn, rid)
    assert status == "researching" and job["status"] == "queued" and job["last_error"]["stage"] == "search"
    assert worker(transport=down).run_once(conn, rid) is None                      # still in backoff
    conn.execute("update public.research_jobs set run_after = now(), max_attempts = 2 where id = %s", (job["id"],))
    assert worker(transport=down).run_once(conn, rid) == "failed:literature_unavailable:dead"
    assert state(conn, rid)[0] == "research_failed"


@pytest.mark.parametrize("start", ["submitted", "researching"])
def test_expired_exhausted_lease_fails_request(client, conn, users, start):
    rid = submit(client, users["a"]).json()["id"]
    if start == "researching":
        conn.execute("update public.requests set status = 'researching' where id = %s", (rid,))
    conn.execute("""update public.research_jobs set status = 'running', attempts = max_attempts, locked_by = 'crashed',
                    lease_expires_at = now() - interval '1 minute' where request_id = %s""", (rid,))
    assert worker().run_once(conn, rid) is None
    status, job = state(conn, rid)
    assert status == "research_failed" and job["status"] == "dead" and job["last_error"]["code"] == "lease_expired_exhausted"


def test_lost_lease_writes_nothing(client, conn, users):
    rid = submit(client, users["a"]).json()["id"]

    class StealsLease(FakeProvider):
        def generate(self, inp):   # another worker reclaims the job mid-flight
            conn.execute("update public.research_jobs set locked_by = 'other' where request_id = %s", (rid,))
            return super().generate(inp)
    assert worker(StealsLease()).run_once(conn, rid) == "lease_lost"
    assert conn.execute("select count(*) as n from public.response_drafts where request_id = %s",
                        (rid,)).fetchone()["n"] == 0
    assert state(conn, rid)[0] == "researching"


def test_fresh_rerun_from_review_keeps_old_draft(client, conn, users):
    rid = submit(client, users["a"]).json()["id"]
    assert worker(FakeProvider()).run_once(conn, rid) == "draft_ready"
    client.post(f"/api/v1/staff/requests/{rid}/start-review", headers=as_(users["admin"]))
    assert client.post(f"/api/v1/staff/requests/{rid}/rerun", json={"fresh": True},
                       headers=as_(users["admin"])).status_code == 202
    job = state(conn, rid)[1]
    assert job["payload"]["fresh"] is True
    assert worker(FakeProvider()).run_once(conn, rid) == "draft_ready"
    assert conn.execute("select count(*) as n from public.response_drafts where request_id = %s",
                        (rid,)).fetchone()["n"] == 2


def test_outage_with_no_hits_is_retried_not_none_found(client, conn, users):
    rid = submit(client, users["a"]).json()["id"]
    t = httpx.MockTransport(lambda r: httpx.Response(503) if r.url.host == "eutils.ncbi.nlm.nih.gov"
                            else httpx.Response(200, json={"resultList": {"result": []}}))
    assert worker(ExplodingProvider(), t).run_once(conn, rid) == "failed:literature_unavailable:queued"
    assert conn.execute("select count(*) as n from public.response_drafts where request_id = %s",
                        (rid,)).fetchone()["n"] == 0


def test_partial_search_is_flagged(client, conn, users):
    rid = submit(client, users["a"]).json()["id"]
    assert worker(FakeProvider(), literature_transport(pubmed_status=503)).run_once(conn, rid) == "draft_ready"
    meta = conn.execute("select meta from public.response_drafts where request_id = %s", (rid,)).fetchone()["meta"]
    assert "partial_search" in meta["ai_flags"] and meta["search_errors"]["pubmed"]["code"] == "upstream_unavailable"


def test_rerun_cannot_hijack_review_in_progress(client, conn, users):
    """A job left over for a request that is now in_review completes as a no-op instead of taking it over."""
    rid = submit(client, users["a"]).json()["id"]
    assert worker(FakeProvider()).run_once(conn, rid) == "draft_ready"
    client.post(f"/api/v1/staff/requests/{rid}/start-review", headers=as_(users["admin"]))
    conn.execute("""insert into public.research_jobs (kind, request_id, idempotency_key, payload)
                    values ('research', %s, %s, '{}')""", (rid, f"stale:{rid}"))
    assert worker(ExplodingProvider(), failing_transport()).run_once(conn, rid) == "noop:in_review"
    assert state(conn, rid)[0] == "in_review"
