from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from psycopg import Connection
from pydantic import BaseModel, Field

from app.auth.jwt import Admin, Staff, User
from app.db import get_conn
from app.services import requests as svc
from app.services import photo, reviews

router = APIRouter(prefix="/api/v1")
Conn = Annotated[Connection, Depends(get_conn)]

# NULL = "I don't know" / not provided
Optional200 = Annotated[str | None, Field(default=None, max_length=200)]
Optional500 = Annotated[str | None, Field(default=None, max_length=500)]
Status = Literal["submitted", "researching", "research_failed", "draft_ready", "in_review",
                 "awaiting_clarification", "published", "withdrawn", "closed"]


class NewRequest(BaseModel):
    herb_name: str = Field(min_length=1, max_length=200, pattern=r"\S")
    preparation: Optional500
    cancer_type: Optional200
    treatment: Optional500


class Text(BaseModel):
    text: str = Field(min_length=1, max_length=2000, pattern=r"\S")


class Content(BaseModel):
    content: dict


class Publish(BaseModel):
    body: dict                       # validated against schema v1 in the service (content_invalid)
    acknowledge_flags: bool = False  # researcher confirms flagged wording was reviewed (content_flags)


class Photo(BaseModel):
    image: str = Field(max_length=2_800_000)   # data URL; decoded size is checked in the service (2 MB)


class Rerun(BaseModel):
    fresh: bool = False  # True: skip reusing an approved review, search the literature again


class SetHerb(BaseModel):
    herb_id: int = Field(gt=0)


class Assign(BaseModel):
    researcher_id: UUID


class Role(BaseModel):
    role: Literal["user", "researcher", "admin"]


# ------------------------------------------------------------------ public / self


@router.get("/health")
def health(conn: Conn):
    conn.execute("select 1")
    return {"status": "ok"}


@router.get("/me")
def me(conn: Conn, user: User):
    return conn.execute(
        "select id, role, display_name from public.profiles where id = %s", (user.id,)
    ).fetchone()


@router.get("/herbs")
def herbs(conn: Conn):
    return conn.execute("select id, name_he, name_en, latin_name from public.herbs order by name_he").fetchall()


@router.post("/herbs/identify")
def identify_herb(body: Photo, conn: Conn, user: User):
    """Most likely herb in a photo, to pre-fill the request form. The photo is not stored (D-021)."""
    return photo.identify(conn, user, body.image)


# ------------------------------------------------------------------ user


@router.post("/requests", status_code=201)
def create_request(body: NewRequest, conn: Conn, user: User):
    return svc.create_request(conn, user, body.herb_name, body.preparation, body.cancer_type, body.treatment)


@router.get("/requests")
def list_requests(conn: Conn, user: User):
    return svc.list_requests(conn, user)


@router.get("/requests/{rid}")
def get_request(rid: UUID, conn: Conn, user: User):
    return svc.get_request(conn, user, rid)


@router.post("/requests/{rid}/withdraw", status_code=204)
def withdraw(rid: UUID, conn: Conn, user: User):
    svc.withdraw(conn, user, rid)


@router.post("/requests/{rid}/clarifications/{cid}/answer", status_code=204)
def answer(rid: UUID, cid: int, body: Text, conn: Conn, user: User):
    svc.answer_clarification(conn, user, rid, cid, body.text)


# ------------------------------------------------------------------ staff (researcher: assigned only; admin: all)


@router.get("/staff/requests")
def staff_list(conn: Conn, user: Staff, status: Status | None = None):
    return svc.staff_list(conn, user, status)


@router.get("/staff/requests/{rid}")
def staff_get(rid: UUID, conn: Conn, user: Staff):
    return svc.staff_get(conn, user, rid)


@router.post("/staff/requests/{rid}/start-review", status_code=204)
def start_review(rid: UUID, conn: Conn, user: Staff):
    svc.start_review(conn, user, rid)


@router.put("/staff/requests/{rid}/draft", status_code=204)
def save_draft(rid: UUID, body: Content, conn: Conn, user: Staff):
    svc.save_draft(conn, user, rid, body.content)


@router.post("/staff/requests/{rid}/clarifications", status_code=201)
def ask(rid: UUID, body: Text, conn: Conn, user: Staff):
    return {"id": svc.ask_clarification(conn, user, rid, body.text)}


@router.post("/staff/requests/{rid}/publish", status_code=204)
def publish(rid: UUID, body: Publish, conn: Conn, user: Staff):
    svc.publish(conn, user, rid, body.body, body.acknowledge_flags)


@router.post("/staff/requests/{rid}/close", status_code=204)
def close(rid: UUID, conn: Conn, user: Staff):
    svc.close(conn, user, rid)


@router.post("/staff/requests/{rid}/rerun", status_code=202)
def rerun(rid: UUID, conn: Conn, user: Staff, body: Rerun | None = None):
    svc.rerun(conn, user, rid, bool(body and body.fresh))


@router.patch("/staff/requests/{rid}/herb", status_code=204)
def set_herb(rid: UUID, body: SetHerb, conn: Conn, user: Staff):
    svc.set_herb(conn, user, rid, body.herb_id)


@router.post("/staff/requests/{rid}/save-review", status_code=201)
def save_review(rid: UUID, conn: Conn, user: Staff):
    return reviews.save_review(conn, user, rid)


@router.get("/staff/reviews")
def list_reviews(conn: Conn, user: Staff, herb_id: int | None = None):
    return reviews.list_reviews(conn, herb_id)


@router.get("/staff/reviews/{review_id}")
def get_review(review_id: UUID, conn: Conn, user: Staff):
    return reviews.get_review(conn, review_id)


# ------------------------------------------------------------------ admin


@router.post("/admin/requests/{rid}/assign", status_code=204)
def assign(rid: UUID, body: Assign, conn: Conn, admin: Admin):
    svc.assign(conn, admin, rid, body.researcher_id)


@router.get("/admin/researchers")
def researchers(conn: Conn, admin: Admin):
    return reviews.list_researchers(conn)


@router.get("/admin/users")
def users(conn: Conn, admin: Admin):
    return svc.list_users(conn)


@router.patch("/admin/users/{uid}/role", status_code=204)
def set_role(uid: UUID, body: Role, conn: Conn, admin: Admin):
    svc.set_role(conn, admin, uid, body.role)
