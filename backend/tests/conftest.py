"""Integration fixtures against the dev DB. Each test module runs in ONE outer transaction that is rolled back."""

import uuid

import psycopg
import pytest
from fastapi import Header
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.auth.jwt import CurrentUser, current_user
from app.db import get_conn
from app.main import create_app
from app.settings import get_settings

try:
    DB_URL = get_settings().database_url
except Exception:  # no .env / env vars
    DB_URL = None
needs_db = pytest.mark.skipif(not DB_URL, reason="DATABASE_URL not set")


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
