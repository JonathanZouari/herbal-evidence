from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

pool: ConnectionPool | None = None


def open_pool(url: str) -> None:
    global pool
    # autocommit: reads never leave a connection "idle in transaction"; tx() is the only transaction boundary
    pool = ConnectionPool(url, min_size=1, max_size=10, kwargs={"row_factory": dict_row, "autocommit": True}, open=True)


def close_pool() -> None:
    if pool:
        pool.close()


def get_conn() -> Iterator[Connection]:
    """FastAPI dependency: one pooled connection per request (tests override this)."""
    assert pool, "pool not open"
    with pool.connection() as conn:
        yield conn


@contextmanager
def tx(conn: Connection, actor_id: UUID | None = None) -> Iterator[Connection]:
    """Transaction (savepoint if already inside one) with the actor recorded for request_events."""
    with conn.transaction():
        if actor_id:
            conn.execute("select set_config('app.actor_id', %s, true)", (str(actor_id),))
        yield conn
