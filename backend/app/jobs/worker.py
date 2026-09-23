"""Job consumer: one daemon thread inside the backend process (D-010, D-019). Postgres is the queue:
claim_job (SKIP LOCKED + lease), heartbeat while working, complete/fail. A crashed worker's lease expires and the
job is reclaimed; exhausted attempts end as `dead` and the request as `research_failed`."""

import logging
import os
import socket
import threading
import uuid
from contextlib import nullcontext
from dataclasses import replace

from psycopg import Connection
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.ai.provider import get_provider
from app.db import tx
from app.jobs.research import Deps, process_research_job
from app.research.http import SafeClient
from app.settings import Settings

log = logging.getLogger("app.worker")


class Heartbeat:
    """Extends the lease every lease/3 seconds on its own connection; `lost` once the job isn't ours any more."""

    def __init__(self, pool: ConnectionPool, job_id: int, worker: str, lease: int):
        self._pool, self._job, self._worker, self._lease = pool, job_id, worker, lease
        self._stop = threading.Event()
        self.lost = False
        self._thread = threading.Thread(target=self._run, name=f"heartbeat-{job_id}", daemon=True)

    def __enter__(self) -> "Heartbeat":
        self._thread.start()
        return self

    def __exit__(self, *_) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(self._lease / 3):
            try:
                with self._pool.connection() as conn:
                    ok = conn.execute("select public.heartbeat_job(%s, %s, %s) as ok",
                                      (self._job, self._worker, self._lease)).fetchone()["ok"]
                if not ok:
                    self.lost = True
                    return
            except Exception:
                log.warning("heartbeat for job %s failed; retrying", self._job, exc_info=True)


class Worker:
    def __init__(self, settings: Settings, pool: ConnectionPool | None, deps: Deps | None = None):
        self.settings, self.pool = settings, pool
        self.id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
        if deps is None:
            http = SafeClient()
            deps = Deps(http=http, provider=get_provider(settings, http), settings=settings)
        self.deps = deps
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------ lifecycle

    def start(self) -> None:
        log.info("worker %s starting (provider=%s)", self.id, self.deps.provider.name)
        self._thread = threading.Thread(target=self._loop, name="research-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10) -> None:
        """Stops claiming. A job still running after `timeout` is abandoned; its lease expires and it is reclaimed."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        if self._thread and self._thread.is_alive():
            log.warning("worker %s still busy at shutdown; the job will be reclaimed after its lease", self.id)
        else:
            self.deps.http.close()

    def _loop(self) -> None:
        idle = self.settings.worker_poll_seconds
        while not self._stop.is_set():
            try:
                if self.pool is None:
                    raise RuntimeError("worker loop needs a connection pool")
                with self.pool.connection() as conn:
                    worked = self.run_once(conn) is not None
                delay = 0 if worked else idle
            except Exception:
                log.exception("worker loop error; backing off")
                delay = min(60, idle * 4)
            if delay:
                self._stop.wait(delay)

    # ------------------------------------------------------------ one job

    def run_once(self, conn: Connection, request_id=None) -> str | None:
        """Claim and process at most one job. Returns the outcome, or None if nothing was ready."""
        lease = self.settings.worker_lease_seconds
        with tx(conn):
            job = conn.execute("select * from public.claim_job(%s, %s, %s)", (self.id, lease, request_id)).fetchone()
        if not job:
            return None
        if job["kind"] != "research":
            log.error("job %s has unknown kind %r", job["id"], job["kind"])
            with tx(conn):
                conn.execute("select public.fail_job(%s, %s, %s, false)",
                             (job["id"], self.id, Jsonb({"code": "unknown_kind"})))
            return "failed:unknown_kind"
        beat = Heartbeat(self.pool, job["id"], self.id, lease) if self.pool else nullcontext()
        with beat as hb:
            deps = replace(self.deps, lease_ok=(lambda: not hb.lost) if hb else (lambda: True))
            outcome = process_research_job(conn, job, self.id, deps)
        log.info("job %s (request %s): %s", job["id"], job["request_id"], outcome)
        return outcome
