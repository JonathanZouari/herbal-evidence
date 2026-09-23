"""Integration tests against the dev DB. Everything runs in ONE outer transaction that is rolled back."""

from app.domain.status import TRANSITIONS
from tests.conftest import as_, needs_db, submit
from tests.helpers import draft

pytestmark = needs_db


def simulate_worker(conn, rid):
    """Shortcut for the worker (tested in test_worker.py): researching -> draft_ready with a valid draft."""
    from psycopg.types.json import Jsonb
    conn.execute("update public.requests set status = 'researching' where id = %s", (rid,))
    conn.execute("update public.requests set status = 'draft_ready' where id = %s", (rid,))
    conn.execute("insert into public.response_drafts (request_id, content) values (%s, %s)", (rid, Jsonb(draft())))


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

    # the published body must match schema v1; only the assigned researcher approves; admin cannot
    bad = client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": {"text": "x"}}, headers=as_(users["res"]))
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "content_invalid"
    assert client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": draft()},
                       headers=as_(users["admin"])).status_code == 403
    assert client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": draft()},
                       headers=as_(users["res"])).status_code == 204

    mine = client.get(f"/api/v1/requests/{rid}", headers=as_(users["a"])).json()
    assert mine["public_status"] == "published" and mine["response"]["body"] == draft()

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
    assert conn.execute("select status from public.requests where id = %s", (rid,)).fetchone()["status"] == "researching"
    assert client.post(f"/api/v1/staff/requests/{rid}/rerun", headers=as_(users["admin"])).status_code == 409
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


def test_staff_views_and_reviews(client, conn, users):
    """herb/sources in the workspace, save-review rules, review repository, researcher list."""
    rid = submit(client, users["b"]).json()["id"]
    client.post(f"/api/v1/admin/requests/{rid}/assign", json={"researcher_id": str(users["res"])}, headers=as_(users["admin"]))
    simulate_worker(conn, rid)
    detail = client.get(f"/api/v1/staff/requests/{rid}", headers=as_(users["res"])).json()
    assert detail["herb"]["name_en"] == "Ginger" and detail["sources"] == []
    listed = next(x for x in client.get("/api/v1/staff/requests", headers=as_(users["admin"])).json() if x["id"] == rid)
    assert listed["herb_name_he"] and "assigned_researcher_name" in listed

    save = lambda who: client.post(f"/api/v1/staff/requests/{rid}/save-review", headers=as_(who))  # noqa: E731
    assert save(users["res"]).status_code == 409                          # not published yet
    client.post(f"/api/v1/staff/requests/{rid}/start-review", headers=as_(users["res"]))
    assert client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": draft()},
                       headers=as_(users["res"])).status_code == 204
    assert save(users["admin"]).status_code == 403                        # admin doesn't approve content
    first = save(users["res"]).json()
    again = save(users["res"])
    assert again.status_code == 409 and again.json()["error"]["code"] == "review_exists"   # one review per response

    reviews = client.get("/api/v1/staff/reviews", headers=as_(users["res"])).json()
    assert any(r["id"] == first["id"] and r["schema_version"] == "1" for r in reviews)
    one = client.get(f"/api/v1/staff/reviews/{first['id']}", headers=as_(users["res"])).json()
    assert "personal_context_he" not in one["content"] and one["content"]["appetite"] == draft()["appetite"]
    assert client.get("/api/v1/staff/reviews", headers=as_(users["a"])).status_code == 403

    researchers = client.get("/api/v1/admin/researchers", headers=as_(users["admin"])).json()
    assert {str(users["res"]), str(users["res2"])} <= {r["id"] for r in researchers}
    assert client.get("/api/v1/admin/researchers", headers=as_(users["res"])).status_code == 403


def test_set_herb_and_draft_size(client, conn, users):
    rid = submit(client, users["a"], herb="צמח מסתורי").json()["id"]
    ginger = conn.execute("select id from public.herbs where name_en = 'Ginger'").fetchone()["id"]
    assert client.patch(f"/api/v1/staff/requests/{rid}/herb", json={"herb_id": 999999999},
                        headers=as_(users["admin"])).json()["error"]["code"] == "unknown_herb"
    assert client.patch(f"/api/v1/staff/requests/{rid}/herb", json={"herb_id": ginger},
                        headers=as_(users["admin"])).status_code == 204
    simulate_worker(conn, rid)
    client.post(f"/api/v1/staff/requests/{rid}/start-review", headers=as_(users["admin"]))
    huge = client.put(f"/api/v1/staff/requests/{rid}/draft", json={"content": {"x": "א" * 150_000}},
                      headers=as_(users["admin"]))
    assert huge.status_code == 422 and huge.json()["error"]["code"] == "content_too_large"
    assert client.patch(f"/api/v1/staff/requests/{rid}/herb", json={"herb_id": ginger},
                        headers=as_(users["admin"])).status_code == 204     # still allowed in_review


def test_publish_requires_acknowledging_flags(client, conn, users):
    rid = submit(client, users["a"]).json()["id"]
    client.post(f"/api/v1/admin/requests/{rid}/assign", json={"researcher_id": str(users["res"])}, headers=as_(users["admin"]))
    simulate_worker(conn, rid)
    client.post(f"/api/v1/staff/requests/{rid}/start-review", headers=as_(users["res"]))
    body = draft()
    body["appetite"]["summary_he"] = "מומלץ ליטול 500 מ״ג"
    r = client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": body}, headers=as_(users["res"]))
    assert r.status_code == 409 and r.json()["error"] == {"code": "content_flags", "message": "dose,recommendation"}
    assert client.post(f"/api/v1/staff/requests/{rid}/publish", json={"body": body, "acknowledge_flags": True},
                       headers=as_(users["res"])).status_code == 204
