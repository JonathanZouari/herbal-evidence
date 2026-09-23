"""One research job: request -> (reuse an approved review | search literature -> AI draft) -> draft_ready.

Rules: no HTTP inside a DB transaction; every state change re-locks the request and re-checks its status
(it may have been withdrawn/closed meanwhile); a dead job moves the request to research_failed (in SQL, fail_job)."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from psycopg import Connection
from psycopg.types.json import Jsonb
from pydantic import ValidationError

from app.ai.guard import flag_content
from app.ai.provider import AIProvider, DraftInput, ProviderError, ProviderNotConfigured
from app.ai.schema import DraftContent, HerbRef, ReviewContent, SourceRef, assemble_draft, none_found_draft, review_to_draft
from app.db import tx
from app.research import europepmc, pubmed, wikimedia
from app.research.http import FetchError, SafeClient
from app.research.sources import (ResearchError, Source, build_terms, dedupe, europepmc_query, link_request_sources,
                                  pubmed_query, upsert_sources)
from app.research.storage import upload_herb_image
from app.settings import Settings

log = logging.getLogger("app.jobs")

# A job only starts from these: `submitted` (first job) or `researching` (rerun already moved it there, or a retry
# after a failed attempt / crashed worker). in_review / research_failed never: a late job must not take over a review.
STARTABLE = {"submitted", "researching"}


class JobError(Exception):
    def __init__(self, code: str, retryable: bool, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.retryable, self.detail = code, retryable, detail


class LeaseLost(Exception):
    pass


@dataclass
class Deps:
    http: SafeClient
    provider: AIProvider
    settings: Settings
    lease_ok: Callable[[], bool] = field(default=lambda: True)


# ------------------------------------------------------------------ small DB helpers


def _lock_request(conn: Connection, rid) -> dict | None:
    return conn.execute("select * from public.requests where id = %s for update", (rid,)).fetchone()


def _set_status(conn: Connection, rid, status: str) -> None:
    conn.execute("update public.requests set status = %s where id = %s", (status, rid))


def _complete(conn: Connection, job: dict, worker: str) -> None:
    ok = conn.execute("select public.complete_job(%s, %s) as ok", (job["id"], worker)).fetchone()["ok"]
    if not ok:
        raise LeaseLost()


def _fail(conn: Connection, job: dict, worker: str, code: str, stage: str, retryable: bool, detail: str) -> str:
    error = {"code": code, "stage": stage, "message": detail[:300], "at": datetime.now(UTC).isoformat()}
    with tx(conn):
        row = conn.execute("select public.fail_job(%s, %s, %s, %s) as s",
                           (job["id"], worker, Jsonb(error), retryable)).fetchone()
    return f"failed:{code}:{row['s'] or 'lease_lost'}"


def _herb_ref(herb: dict | None, req: dict) -> HerbRef:
    if herb:
        return HerbRef(name_he=herb["name_he"], name_en=herb["name_en"], latin_name=herb["latin_name"])
    return HerbRef(name_he=req["herb_name_input"], name_en=req["herb_name_input"], latin_name=None)


def _source_ref(s: Source) -> SourceRef:
    return SourceRef(ref=s.ref, title=s.title[:1000], journal=(s.journal or None) and s.journal[:500],
                     year=s.pub_year, url=s.url if (s.url or "").startswith("https://") else None)


def _insert_draft(conn: Connection, req: dict, job: dict, content: DraftContent, provider: str | None,
                  model: str | None, meta: dict, review_id=None) -> None:
    conn.execute(
        """insert into public.response_drafts (request_id, evidence_review_id, content, ai_provider, ai_model, job_id, meta)
           values (%s, %s, %s, %s, %s, %s, %s)""",
        (req["id"], review_id, Jsonb(content.model_dump(mode="json")), provider, model or None, job["id"], Jsonb(meta)),
    )


# ------------------------------------------------------------------ stages


def _start(conn: Connection, job: dict, worker: str) -> tuple[dict | None, dict | None, str | None]:
    """Lock the request and move it to researching. Returns (request, herb, noop_outcome)."""
    with tx(conn):
        req = _lock_request(conn, job["request_id"])
        if not req or req["status"] not in STARTABLE:
            _complete(conn, job, worker)
            return None, None, f"noop:{req['status'] if req else 'missing'}"
        if req["status"] != "researching":
            _set_status(conn, req["id"], "researching")
        herb = conn.execute("select id, name_he, name_en, latin_name, image_status from public.herbs where id = %s",
                            (req["herb_id"],)).fetchone() if req["herb_id"] else None
    return req, herb, None


def _mark_image(conn: Connection, herb_id: int, status: str, path: str | None = None,
                attribution: str | None = None, source_url: str | None = None) -> None:
    with tx(conn):
        conn.execute(
            """update public.herbs set image_status = %s, image_path = %s, image_attribution = %s,
                  image_source_url = %s, image_fetched_at = now()
               where id = %s and image_status = 'pending'""",
            (status, path, attribution, source_url, herb_id),
        )


def _ensure_herb_image(conn: Connection, deps: Deps, herb: dict | None) -> None:
    """Best-effort, once per herb (pending -> found|not_found): a broken image fetch must never fail the
    request's own job. HTTP happens here, outside any transaction; only the short status update is a tx."""
    if not herb or herb["image_status"] != "pending":
        return
    try:
        result = wikimedia.fetch_plant_image(deps.http, herb["name_en"], herb["latin_name"])
        if result is None:
            return _mark_image(conn, herb["id"], "not_found")
        key = deps.settings.supabase_secret_key
        if not key:
            log.warning("herb %s: image found but SUPABASE_SECRET_KEY not configured", herb["id"])
            return _mark_image(conn, herb["id"], "not_found")
        path = upload_herb_image(deps.http, deps.settings.supabase_url, key.get_secret_value(), herb["id"],
                                 result.content, result.content_type)
        _mark_image(conn, herb["id"], "found", path, result.attribution, result.source_url)
    except Exception:
        log.warning("herb %s: image fetch failed", herb["id"], exc_info=True)
        _mark_image(conn, herb["id"], "not_found")


def _reusable_review(conn: Connection, herb_id: int) -> tuple[dict, ReviewContent] | None:
    row = conn.execute(
        """select id, version, content from public.evidence_reviews
            where herb_id = %s and approved_at is not null and content ->> 'schema_version' = '1'
            order by version desc limit 1""",
        (herb_id,),
    ).fetchone()
    if not row:
        return None
    try:
        return row, ReviewContent.model_validate(row["content"])
    except ValidationError:
        log.warning("evidence review %s is not valid schema v1; not reused", row["id"])
        return None


def _finish(conn: Connection, job: dict, worker: str, write: Callable[[dict], None]) -> str:
    """Re-lock, re-check, write the draft, draft_ready, complete - all or nothing."""
    with tx(conn):
        req = _lock_request(conn, job["request_id"])
        if not req or req["status"] != "researching":   # withdrawn meanwhile: keep nothing
            _complete(conn, job, worker)
            return f"noop:{req['status'] if req else 'missing'}"
        write(req)
        _set_status(conn, req["id"], "draft_ready")
        _complete(conn, job, worker)
    return "draft_ready"


def _reuse(conn: Connection, job: dict, worker: str, row: dict, review: ReviewContent) -> str:
    def write(req: dict) -> None:
        links = conn.execute("select source_id from public.review_sources where review_id = %s order by source_id",
                             (row["id"],)).fetchall()
        link_request_sources(conn, req["id"], job["id"], [(x["source_id"], "review") for x in links])
        _insert_draft(conn, req, job, review_to_draft(review), None, None,
                      {"reused_review_id": str(row["id"]), "reused_review_version": row["version"]}, row["id"])
    return _finish(conn, job, worker, write)


def _search(deps: Deps, terms: list[str]) -> tuple[list[Source], dict]:
    s = deps.settings
    key = s.ncbi_api_key.get_secret_value() if s.ncbi_api_key else None
    queries = {"pubmed": pubmed_query(terms), "europepmc": europepmc_query(terms)}
    runs = {
        "pubmed": lambda: pubmed.search(deps.http, queries["pubmed"], s.literature_max_results, key, s.ncbi_tool,
                                        s.ncbi_email),
        "europepmc": lambda: europepmc.search(deps.http, queries["europepmc"], s.literature_max_results),
    }
    found, counts, errors = [], {}, {}
    for name, run in runs.items():
        try:
            hits = run()
            counts[name] = len(hits)
            found += hits
        except (FetchError, ResearchError) as e:
            errors[name] = {"code": e.code, "retryable": e.retryable}
    if len(errors) == len(runs):
        raise JobError("literature_unavailable", any(e["retryable"] for e in errors.values()), ",".join(
            f"{k}={v['code']}" for k, v in errors.items()))
    sources = dedupe(found)
    if errors and not sources:   # an outage must never look like "no studies exist"
        raise JobError("literature_unavailable", True, ",".join(f"{k}={v['code']}" for k, v in errors.items()))
    return sources, {"terms": terms, "queries": queries, "counts": {**counts, "deduped": len(sources)},
                     "search_errors": errors}


# ------------------------------------------------------------------ entry point


def process_research_job(conn: Connection, job: dict, worker: str, deps: Deps) -> str:
    stage = "start"
    try:
        req, herb, noop = _start(conn, job, worker)
        if noop:
            return noop

        stage = "image"
        _ensure_herb_image(conn, deps, herb)

        stage = "reuse"
        if herb and not (job.get("payload") or {}).get("fresh"):
            found = _reusable_review(conn, herb["id"])
            if found:
                return _reuse(conn, job, worker, *found)

        stage = "search"
        terms = build_terms(herb, req["herb_name_input"])
        sources, meta = _search(deps, terms)

        stage = "store_sources"
        with tx(conn):   # committed on its own: staff see the sources even if the AI step fails
            ids = upsert_sources(conn, sources)
            link_request_sources(conn, req["id"], job["id"], [(i, s.origin) for i, s in zip(ids, sources)])

        stage = "generate"
        herb_ref = _herb_ref(herb, req)
        if not sources:
            draft, provider, model = none_found_draft(herb_ref), None, None
        else:
            if not deps.lease_ok():
                raise LeaseLost()
            inp = DraftInput(herb=herb_ref.model_dump(), sources=sources,
                             request={k: req[k] for k in ("preparation", "cancer_type", "treatment")})
            analysis = deps.provider.generate(inp)
            draft = assemble_draft(herb_ref, analysis, [_source_ref(s) for s in sources])
            provider, model = deps.provider.name, deps.provider.model
        meta["ai_flags"] = flag_content(draft) + (["partial_search"] if meta["search_errors"] else [])

        stage = "store_draft"
        return _finish(conn, job, worker, lambda r: _insert_draft(conn, r, job, draft, provider, model, meta))
    except LeaseLost:
        log.warning("job %s: lease lost at %s; another worker owns it now", job["id"], stage)
        return "lease_lost"
    except ProviderNotConfigured as e:
        return _fail(conn, job, worker, e.code, stage, False, "AI provider not configured")
    except (JobError, ResearchError, ProviderError, FetchError) as e:
        return _fail(conn, job, worker, e.code, stage, e.retryable, e.detail)
    except ValidationError as e:
        return _fail(conn, job, worker, "ai_bad_output", stage, True, f"{e.error_count()} schema errors")
    except Exception as e:
        log.exception("job %s failed unexpectedly at %s", job["id"], stage)
        return _fail(conn, job, worker, "internal", stage, True, type(e).__name__)
