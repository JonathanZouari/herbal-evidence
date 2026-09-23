"""Reusable evidence reviews (herb-level, versioned). Saving one is an explicit researcher approval of the herb-level
content; each later personalized response built from it still needs its own approval (publish)."""

from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Jsonb

from app.ai.schema import HerbRef, draft_to_review
from app.auth.jwt import CurrentUser
from app.db import tx
from app.errors import AppError, not_found
from app.services.requests import _staff_locked, validate_content


def save_review(conn: Connection, user: CurrentUser, rid: UUID) -> dict:
    """Turn a published response into the next review version for its herb."""
    with tx(conn, user.id):
        req = _staff_locked(conn, user, rid, researcher_only=True)
        if req["status"] != "published":
            raise AppError(409, "not_published")
        if not req["herb_id"]:
            raise AppError(409, "herb_required")
        resp = conn.execute("select id, body from public.responses where request_id = %s", (rid,)).fetchone()
        # serialize versions per herb; the review is filed under the request's herb, so its content says so too
        herb = conn.execute("select name_he, name_en, latin_name from public.herbs where id = %s for update",
                            (req["herb_id"],)).fetchone()
        review = draft_to_review(validate_content(resp["body"])).model_copy(update={"herb": HerbRef(**herb)})
        if conn.execute("select 1 from public.evidence_reviews where source_response_id = %s", (resp["id"],)).fetchone():
            raise AppError(409, "review_exists")
        version = conn.execute("select coalesce(max(version), 0) + 1 as v from public.evidence_reviews where herb_id = %s",
                               (req["herb_id"],)).fetchone()["v"]
        row = conn.execute(
            """insert into public.evidence_reviews (herb_id, version, content, approved_by, approved_at, source_response_id)
               values (%s, %s, %s, %s, now(), %s) returning id, version""",
            (req["herb_id"], version, Jsonb(review.model_dump(mode="json")), user.id, resp["id"]),
        ).fetchone()
        cited = [s.ref for s in review.sources]
        conn.execute(
            """insert into public.review_sources (review_id, source_id)
               select %s, s.id from public.request_sources rs join public.literature_sources s on s.id = rs.source_id
                where rs.request_id = %s
                  and (('pmid:' || s.pmid) = any(%s) or ('doi:' || lower(s.doi)) = any(%s) or ('pmcid:' || s.pmcid) = any(%s))
               on conflict do nothing""",
            (row["id"], rid, cited, cited, cited),
        )
    return row


def list_reviews(conn: Connection, herb_id: int | None) -> list[dict]:
    return conn.execute(
        """select r.id, r.herb_id, h.name_he as herb_name_he, h.name_en as herb_name_en, r.version, r.approved_at,
                  p.display_name as approved_by_name, r.content ->> 'schema_version' as schema_version,
                  r.content ->> 'evidence_base' as evidence_base,
                  (select count(*) from public.review_sources rs where rs.review_id = r.id) as source_count
             from public.evidence_reviews r
             join public.herbs h on h.id = r.herb_id
             left join public.profiles p on p.id = r.approved_by
            where %(herb)s::bigint is null or r.herb_id = %(herb)s::bigint
            order by h.name_he, r.version desc""",
        {"herb": herb_id},
    ).fetchall()


def get_review(conn: Connection, review_id: UUID) -> dict:
    row = conn.execute(
        """select r.id, r.herb_id, h.name_he as herb_name_he, r.version, r.content, r.approved_at,
                  p.display_name as approved_by_name, r.source_response_id, r.created_at
             from public.evidence_reviews r join public.herbs h on h.id = r.herb_id
             left join public.profiles p on p.id = r.approved_by
            where r.id = %s""",
        (review_id,),
    ).fetchone()
    if not row:
        raise not_found()
    row["sources"] = conn.execute(
        """select s.id, s.pmid, s.pmcid, s.doi, s.title, s.journal, s.pub_year, s.url
             from public.review_sources rs join public.literature_sources s on s.id = rs.source_id
            where rs.review_id = %s order by s.pub_year desc nulls last""",
        (review_id,),
    ).fetchall()
    return row


def list_researchers(conn: Connection) -> list[dict]:
    return conn.execute(
        """select p.id, p.display_name, u.email,
                  (select count(*) from public.requests r
                    where r.assigned_researcher_id = p.id
                      and r.status not in ('published', 'withdrawn', 'closed')) as open_assigned
             from public.profiles p join auth.users u on u.id = p.id
            where p.role = 'researcher' order by p.display_name nulls last, u.email"""
    ).fetchall()
