"""Integration tests against the dev DB. Everything runs in ONE outer transaction that is rolled back."""

import uuid

import psycopg
import pytest
from fastapi import Header
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.auth.jwt import CurrentUser, current_user
from app.db import get_conn
from app.domain.status import TRANSITIONS
from app.main import create_app
from app.settings import get_settings

try:
    DB_URL = get_settings().database_url
except Exception:  # no .env / env vars
    DB_URL = None
pytestmark = pytest.mark.skipif(not DB_URL, reason="DATABASE_URL not set")


@pytest.fixture(scope="module")
def conn():
    with psycopg.connect(DB_URL, row_factory=dict_row) as c:
        yield c
        c.rollback()


@pytest.fixture(scope="module")
def users(conn):
    ids = {name: uuid.uuid4() for name in ("a", "b", "res", "res2", "admin")}
    for name, uid in ids.items():
        conn.execute("insert into auth.users (id, email) values (%s, %s)", (uid, f"pytest-{name}-{uid}@example.invalid"))
    conn.execute("update public.profiles set role = 'researcher' where id in (%s, %s)", (ids["res"], ids["res2"]))
    conn.execute("update public.profiles set role = 'admin' where id = %s", (ids["admin"],))
    return ids


@pytest.fixture(scope="module")
def client(conn, users):
    app = create_app(open_pool=False)

    # Same role lookup as production, but identity from a test header instead of a signed JWT.
    def test_user(x_test_user: str = Header()) -> CurrentUser:
        uid = uuid.UUID(x_test_user)
        return CurrentUser(uid, conn.execute("select role from public.profiles where id = %s", (uid,)).fetchone()["role"])

    app.dependency_overrides[get_conn] = lambda: conn
    app.dependency_overrides[current_user] = test_user
    with TestClient(app) as c:
        yield c


def as_(uid):
    return {"X-Test-User": str(uid)}


def submit(client, uid, herb="ג׳ינג׳ר", **extra):
    return client.post("/api/v1/requests", json={"herb_name": herb, **extra}, headers=as_(uid))


def simulate_worker(conn, rid):
    """What the Phase 3 worker will do: claim -> researching -> draft."""
    conn.execute("update public.requests set status = 'researching' where id = %s", (rid,))
    conn.execute("update public.requests set status = 'draft_ready' where id = %s", (rid,))
    conn.execute("insert into public.response_drafts (request_id, content) values (%s, '{\"draft\": 1}')", (rid,))


def test_transitions_mirror_db(conn):
    rows = conn.execute("select from_status::text f, to_status::text t from public.request_status_transitions").fetchall()
    assert {(r["f"], r["t"]) for r in rows} == {(f, t) for f, ts in TRANSITIONS.items() for t in ts}


def test_full_lifecycle(client, conn, users):
    r = submit(client, users["a"], preparation="תה")
    assert r.status_code == 201, r.text
    req = r.json()
    rid = req["id"]
    assert req["public_status"] == "in_progress"
    assert req["herb_id"] == conn.execute("select id from public.herbs where name_en = 'Ginger'").fetchone()["id"]
    assert "status" not in req and "assigned_researcher_id" not in req

    job = conn.execute("select * from public.research_jobs where request_id = %s", (rid,)).fetchone()
    assert job["idempotency_key"] == f"request:{rid}:research:1" and job["status"] == "queued"

    # admin assigns, worker produces a draft, researcher reviews
    assert client.post(f"/api/v1/admin/requests/{rid}/assign", json={"researcher_id": str(users["res"])},
                       headers=as_(users["admin"])).status_code == 204
    simulate_worker(conn, rid)
    assert client.post(f"/api/v1/staff/requests/{rid}/start-review", headers=as_(users["res"])).status_code == 204
    assert client.put(f"/api/v1/staff/requests/{rid}/draft", json={"content": {"draft": 2}},
                      headers=as_(users["res"])).status_code == 204

    # clarification round trip
    q = client.post(f"/api/v1/staff/requests/{rid}/clarifications", json={"text": "באיזו צורה?"}, headers=as_(users["res"]))
    assert q.status_code == 201
    mine = client.get(f"/api/v1/requests/{rid}", headers=as_(users["a"])).json()
    assert mine["public_status"] == "needs_clarification" and mine["clarifications"][0]["question"] == "באיזו צורה?"
    assert "drafts" not in mine and mine["response"] is None
    assert client.post(f"/api/v1/requests/{rid}/clarifications/{q.json()['id']}/answer", json={"text": "תה"},
                       headers=as_(users["b"])).status_code == 404          # not B's request
    assert client.post(f"/api/v1/requests/{rid}/clarifications/{q.json()['id']}/answer", json={"text": "תה"},
                       headers=as_(users["a"])).status_code == 204

    # only the assigned researcher approves; admin cannot
    assert client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": {"text": "x"}},
                       headers=as_(users["admin"])).status_code == 403
    assert client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": {"text": "תשובה"}},
                       headers=as_(users["res"])).status_code == 204

    mine = client.get(f"/api/v1/requests/{rid}", headers=as_(users["a"])).json()
    assert mine["public_status"] == "published" and mine["response"]["body"] == {"text": "תשובה"}

    detail = client.get(f"/api/v1/staff/requests/{rid}", headers=as_(users["res"])).json()
    assert detail["status"] == "published" and detail["drafts"][0]["content"] == {"draft": 2}
    assert [e["to_status"] for e in detail["events"]] == [
        "submitted", "researching", "draft_ready", "in_review", "awaiting_clarification", "in_review", "published"]
    assert detail["events"][-1]["actor_id"] == str(users["res"])


def test_isolation_and_roles(client, users):
    rid = submit(client, users["a"], herb="צמח לא קיים").json()["id"]
    assert client.get(f"/api/v1/requests/{rid}", headers=as_(users["b"])).status_code == 404
    assert rid not in [x["id"] for x in client.get("/api/v1/requests", headers=as_(users["b"])).json()]
    assert client.get("/api/v1/staff/requests", headers=as_(users["a"])).status_code == 403
    assert client.get("/api/v1/admin/users", headers=as_(users["res"])).status_code == 403
    assert client.get(f"/api/v1/staff/requests/{rid}", headers=as_(users["res2"])).status_code == 403   # unassigned
    assert rid in [x["id"] for x in client.get("/api/v1/staff/requests", headers=as_(users["admin"])).json()]
    assert rid not in [x["id"] for x in client.get("/api/v1/staff/requests", headers=as_(users["res2"])).json()]


def test_unknown_herb_and_withdraw(client, users):
    r = submit(client, users["b"], herb="צמח מסתורי").json()
    assert r["herb_id"] is None
    assert client.post(f"/api/v1/requests/{r['id']}/withdraw", headers=as_(users["b"])).status_code == 204
    again = client.post(f"/api/v1/requests/{r['id']}/withdraw", headers=as_(users["b"]))
    assert again.status_code == 409 and again.json()["error"]["code"] == "invalid_transition"


def test_invalid_transition_and_rerun(client, conn, users):
    rid = submit(client, users["b"]).json()["id"]
    r = client.post(f"/api/v1/staff/requests/{rid}/start-review", headers=as_(users["admin"]))
    assert r.status_code == 409                                    # submitted -> in_review not allowed
    assert client.post(f"/api/v1/staff/requests/{rid}/rerun", headers=as_(users["admin"])).status_code == 409
    conn.execute("update public.requests set status = 'researching' where id = %s", (rid,))
    conn.execute("update public.requests set status = 'research_failed' where id = %s", (rid,))
    assert client.post(f"/api/v1/staff/requests/{rid}/rerun", headers=as_(users["admin"])).status_code == 202
    keys = [j["idempotency_key"] for j in conn.execute(
        "select idempotency_key from public.research_jobs where request_id = %s order by id", (rid,)).fetchall()]
    assert keys == [f"request:{rid}:research:1", f"request:{rid}:research:2"]


def test_quota_open_requests(client, users):
    uid = users["res2"]   # fresh submitter: researchers can submit too
    codes = [submit(client, uid).status_code for _ in range(4)]
    assert codes == [201, 201, 201, 429]


def test_validation_and_admin(client, users):
    r = client.post("/api/v1/requests", json={"herb_name": "   "}, headers=as_(users["a"]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert client.patch(f"/api/v1/admin/users/{users['admin']}/role", json={"role": "user"},
                        headers=as_(users["admin"])).status_code == 409
    rid = submit(client, users["b"]).json()["id"]
    assert client.post(f"/api/v1/admin/requests/{rid}/assign", json={"researcher_id": str(users["a"])},
                       headers=as_(users["admin"])).status_code == 422


def test_security_headers(client):
    r = client.get("/api/v1/health")
    assert r.headers["content-security-policy"].startswith("default-src 'none'")
    assert r.headers["x-content-type-options"] == "nosniff"
