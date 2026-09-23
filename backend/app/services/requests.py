"""Request lifecycle. Every action = one transaction: lock row -> authorize -> change -> (DB trigger audits) -> enqueue."""

import json
from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from app.ai.guard import flag_content
from app.ai.schema import DraftContent
from app.auth.jwt import CurrentUser
from app.db import tx
from app.domain import herbs
from app.domain.herbs import image_url as herb_image_url
from app.domain.status import RERUNNABLE, can_transition
from app.errors import AppError, forbidden, not_found
from app.settings import get_settings

MAX_DRAFT_BYTES = 200_000
# Columns a user may see (matches the column grants in the DB). Never status/assignment/drafts.
PUBLIC_COLS = "id, herb_name_input, herb_id, preparation, cancer_type, treatment, public_status, created_at, updated_at"


def _transition(conn: Connection, req: dict, dst: str) -> None:
    if not can_transition(req["status"], dst):
        raise AppError(409, "invalid_transition", f"{req['status']} -> {dst}")
    conn.execute("update public.requests set status = %s where id = %s", (dst, req["id"]))
    req["status"] = dst


def _enqueue_research(conn: Connection, request_id: UUID, fresh: bool = False) -> None:
    n = conn.execute(
        "select count(*) + 1 as n from public.research_jobs where request_id = %s and kind = 'research'",
        (request_id,),
    ).fetchone()["n"]
    conn.execute(
        """insert into public.research_jobs (kind, request_id, idempotency_key, payload)
           values ('research', %s, %s, %s) on conflict (idempotency_key) do nothing""",
        (request_id, f"request:{request_id}:research:{n}", Jsonb({"request_id": str(request_id), "fresh": fresh})),
    )


# ------------------------------------------------------------------ user


def create_request(conn: Connection, user: CurrentUser, herb_name: str, preparation: str | None,
                   cancer_type: str | None, treatment: str | None) -> dict:
    s = get_settings()
    with tx(conn, user.id):
        # serialize this user's submissions so the quota can't be raced
        conn.execute("select 1 from public.profiles where id = %s for update", (user.id,))
        q = conn.execute(
            """select count(*) filter (where created_at > now() - interval '1 day') as today,
                      count(*) filter (where status not in ('published', 'withdrawn', 'closed')) as open
                 from public.requests where user_id = %s""",
            (user.id,),
        ).fetchone()
        if q["today"] >= s.max_requests_per_day:
            raise AppError(429, "quota_daily")
        if q["open"] >= s.max_open_requests:
            raise AppError(429, "quota_open")
        req = conn.execute(
            f"""insert into public.requests (user_id, herb_name_input, herb_id, preparation, cancer_type, treatment)
                values (%s, %s, %s, %s, %s, %s) returning {PUBLIC_COLS}""",
            (user.id, herb_name.strip(), herbs.identify(conn, herb_name), preparation, cancer_type, treatment),
        ).fetchone()
        _enqueue_research(conn, req["id"])
    return req


def list_requests(conn: Connection, user: CurrentUser) -> list[dict]:
    return conn.execute(
        f"select {PUBLIC_COLS} from public.requests where user_id = %s order by created_at desc", (user.id,)
    ).fetchall()


def get_request(conn: Connection, user: CurrentUser, rid: UUID) -> dict:
    req = conn.execute(
        f"select {PUBLIC_COLS} from public.requests where id = %s and user_id = %s", (rid, user.id)
    ).fetchone()
    if not req:
        raise not_found()
    req["clarifications"] = conn.execute(
        "select id, question, asked_at, answer, answered_at from public.clarifications where request_id = %s order by id",
        (rid,),
    ).fetchall()
    req["response"] = (
        conn.execute("select body, published_at from public.responses where request_id = %s", (rid,)).fetchone()
        if req["public_status"] == "published" else None
    )
    herb = conn.execute(
        """select image_path, image_attribution, image_source_url from public.herbs
            where id = %s and image_status = 'found'""",
        (req["herb_id"],),
    ).fetchone() if req["herb_id"] else None
    if herb:
        req["herb_image_url"] = herb_image_url(get_settings().supabase_url, herb["image_path"])
        req["herb_image_attribution"] = herb["image_attribution"]
        req["herb_image_source_url"] = herb["image_source_url"]
    return req


def _own_locked(conn: Connection, user: CurrentUser, rid: UUID) -> dict:
    req = conn.execute(
        "select id, status from public.requests where id = %s and user_id = %s for update", (rid, user.id)
    ).fetchone()
    if not req:
        raise not_found()  # someone else's request looks the same as a missing one
    return req


def withdraw(conn: Connection, user: CurrentUser, rid: UUID) -> None:
    with tx(conn, user.id):
        _transition(conn, _own_locked(conn, user, rid), "withdrawn")


def answer_clarification(conn: Connection, user: CurrentUser, rid: UUID, cid: int, answer: str) -> None:
    with tx(conn, user.id):
        req = _own_locked(conn, user, rid)
        if req["status"] != "awaiting_clarification":
            raise AppError(409, "not_awaiting_clarification")
        row = conn.execute(
            """update public.clarifications set answer = %s, answered_at = now()
                where id = %s and request_id = %s and answer is null returning id""",
            (answer.strip(), cid, rid),
        ).fetchone()
        if not row:
            raise not_found()
        still_open = conn.execute(
            "select 1 from public.clarifications where request_id = %s and answer is null", (rid,)
        ).fetchone()
        if not still_open:
            _transition(conn, req, "in_review")


# ------------------------------------------------------------------ staff


def _staff_locked(conn: Connection, user: CurrentUser, rid: UUID, researcher_only: bool = False) -> dict:
    req = conn.execute("select * from public.requests where id = %s for update", (rid,)).fetchone()
    if not req:
        raise not_found()
    assigned = req["assigned_researcher_id"] == user.id
    if researcher_only and not (user.role == "researcher" and assigned):
        raise forbidden()
    if user.role == "researcher" and not assigned:
        raise forbidden()
    return req


def validate_content(content: dict) -> DraftContent:
    """Publishable/reviewable content must match schema v1 (appetite first, cited sources, no scores)."""
    try:
        return DraftContent.model_validate(content)
    except ValidationError as e:
        first = e.errors()[0]
        raise AppError(422, "content_invalid", f"{'.'.join(map(str, first['loc']))}: {first['msg']}") from None


def staff_list(conn: Connection, user: CurrentUser, status: str | None) -> list[dict]:
    return conn.execute(
        """select r.id, r.herb_name_input, r.herb_id, h.name_he as herb_name_he, r.status,
                  r.assigned_researcher_id, p.display_name as assigned_researcher_name, r.created_at, r.updated_at
             from public.requests r
             left join public.herbs h on h.id = r.herb_id
             left join public.profiles p on p.id = r.assigned_researcher_id
            where (%(admin)s or r.assigned_researcher_id = %(uid)s)
              and (%(status)s::public.request_status is null or r.status = %(status)s::public.request_status)
            order by r.created_at""",
        {"admin": user.role == "admin", "uid": user.id, "status": status},
    ).fetchall()


def staff_get(conn: Connection, user: CurrentUser, rid: UUID) -> dict:
    with tx(conn):
        req = _staff_locked(conn, user, rid)
    for key, sql in {
        "drafts": "select * from public.response_drafts where request_id = %s order by created_at",
        "clarifications": "select * from public.clarifications where request_id = %s order by id",
        "events": "select from_status, to_status, actor_id, created_at from public.request_events where request_id = %s order by id",
        "jobs": "select id, kind, status, attempts, max_attempts, run_after, last_error, created_at from public.research_jobs where request_id = %s order by id",
        "response": "select * from public.responses where request_id = %s",
        "sources": """select s.id, s.pmid, s.pmcid, s.doi, s.title, s.journal, s.pub_year, s.url, s.abstract,
                             rs.origin, rs.rank
                        from public.request_sources rs join public.literature_sources s on s.id = rs.source_id
                       where rs.request_id = %s order by rs.job_id desc nulls last, rs.rank""",
    }.items():
        req[key] = conn.execute(sql, (rid,)).fetchall()
    req["herb"] = conn.execute("select id, name_he, name_en, latin_name from public.herbs where id = %s",
                               (req["herb_id"],)).fetchone() if req["herb_id"] else None
    return req


def start_review(conn: Connection, user: CurrentUser, rid: UUID) -> None:
    with tx(conn, user.id):
        _transition(conn, _staff_locked(conn, user, rid), "in_review")


def save_draft(conn: Connection, user: CurrentUser, rid: UUID, content: dict) -> None:
    with tx(conn, user.id):
        req = _staff_locked(conn, user, rid)
        if req["status"] != "in_review":
            raise AppError(409, "not_in_review")
        if len(json.dumps(content, ensure_ascii=False).encode()) > MAX_DRAFT_BYTES:
            raise AppError(422, "content_too_large")
        updated = conn.execute(
            """update public.response_drafts set content = %s, edited_by = %s, updated_at = now()
                where id = (select id from public.response_drafts where request_id = %s
                             order by created_at desc, job_id desc nulls last limit 1)
            returning id""",
            (Jsonb(content), user.id, rid),
        ).fetchone()
        if not updated:
            conn.execute(
                "insert into public.response_drafts (request_id, content, edited_by) values (%s, %s, %s)",
                (rid, Jsonb(content), user.id),
            )


def ask_clarification(conn: Connection, user: CurrentUser, rid: UUID, question: str) -> int:
    with tx(conn, user.id):
        req = _staff_locked(conn, user, rid)
        _transition(conn, req, "awaiting_clarification")
        return conn.execute(
            "insert into public.clarifications (request_id, question, asked_by) values (%s, %s, %s) returning id",
            (rid, question.strip(), user.id),
        ).fetchone()["id"]


def publish(conn: Connection, user: CurrentUser, rid: UUID, body: dict, acknowledge_flags: bool = False) -> None:
    """One researcher approval per personalized response, even when reusing an approved review.
    The reused review id comes from the latest draft, never from the client. Wording that may break the product
    rules (dose, recommendation, cure claim, score) must be explicitly acknowledged by the researcher."""
    content = validate_content(body)
    flags = flag_content(content)
    if flags and not acknowledge_flags:
        raise AppError(409, "content_flags", ",".join(flags))
    with tx(conn, user.id):
        req = _staff_locked(conn, user, rid, researcher_only=True)
        _transition(conn, req, "published")
        draft = conn.execute(
            """select evidence_review_id from public.response_drafts where request_id = %s
                order by created_at desc, job_id desc nulls last limit 1""",
            (rid,),
        ).fetchone()
        evidence_review_id = draft["evidence_review_id"] if draft else None
        conn.execute(
            """insert into public.responses (request_id, evidence_review_id, body, approved_by)
               values (%s, %s, %s, %s)""",
            (rid, evidence_review_id, Jsonb(content.model_dump(mode="json")), user.id),
        )


def close(conn: Connection, user: CurrentUser, rid: UUID) -> None:
    with tx(conn, user.id):
        _transition(conn, _staff_locked(conn, user, rid), "closed")


def rerun(conn: Connection, user: CurrentUser, rid: UUID, fresh: bool = False) -> None:
    """fresh=True skips reusing an approved review and searches the literature again."""
    with tx(conn, user.id):
        req = _staff_locked(conn, user, rid)
        if req["status"] not in RERUNNABLE:
            raise AppError(409, "invalid_transition", f"cannot rerun from {req['status']}")
        pending = conn.execute(
            "select 1 from public.research_jobs where request_id = %s and status in ('queued', 'running')", (rid,)
        ).fetchone()
        if pending:
            raise AppError(409, "job_pending")
        # the request leaves in_review/research_failed now, so a late job can never take over a review in progress
        _transition(conn, req, "researching")
        _enqueue_research(conn, rid, fresh)


HERB_EDITABLE = {"submitted", "research_failed", "in_review"}


def set_herb(conn: Connection, user: CurrentUser, rid: UUID, herb_id: int) -> None:
    """Staff resolve an unidentified herb (then rerun)."""
    with tx(conn, user.id):
        req = _staff_locked(conn, user, rid)
        if req["status"] not in HERB_EDITABLE:
            raise AppError(409, "invalid_transition", f"cannot change herb in {req['status']}")
        if not conn.execute("select 1 from public.herbs where id = %s", (herb_id,)).fetchone():
            raise AppError(422, "unknown_herb")
        conn.execute("update public.requests set herb_id = %s where id = %s", (herb_id, rid))


# ------------------------------------------------------------------ admin


def assign(conn: Connection, admin: CurrentUser, rid: UUID, researcher_id: UUID) -> None:
    with tx(conn, admin.id):
        _staff_locked(conn, admin, rid)
        r = conn.execute("select role from public.profiles where id = %s", (researcher_id,)).fetchone()
        if not r or r["role"] != "researcher":
            raise AppError(422, "not_a_researcher")
        conn.execute("update public.requests set assigned_researcher_id = %s where id = %s", (researcher_id, rid))


def list_users(conn: Connection) -> list[dict]:
    return conn.execute(
        """select p.id, u.email, p.role, p.display_name, p.created_at
             from public.profiles p join auth.users u on u.id = p.id order by p.created_at"""
    ).fetchall()


def set_role(conn: Connection, admin: CurrentUser, uid: UUID, role: str) -> None:
    if uid == admin.id:
        raise AppError(409, "cannot_change_own_role")  # avoids locking the last admin out
    with tx(conn, admin.id):
        if not conn.execute("update public.profiles set role = %s where id = %s returning id", (role, uid)).fetchone():
            raise not_found()
