"""Literature records: search terms, queries, dedupe, and persistence (literature_sources + request_sources)."""

import re
from dataclasses import dataclass, replace

from psycopg import Connection


class ResearchError(Exception):
    def __init__(self, code: str, retryable: bool, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.retryable, self.detail = code, retryable, detail


@dataclass(frozen=True)
class Source:
    title: str
    origin: str                      # pubmed | europepmc | review
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    journal: str | None = None
    pub_year: int | None = None
    abstract: str | None = None
    url: str | None = None

    @property
    def ref(self) -> str:
        """Stable citation key the AI and the editor use ("pmid:123" / "doi:10.x/y" / "pmcid:PMC1")."""
        if self.pmid:
            return f"pmid:{self.pmid}"
        if self.doi:
            return f"doi:{self.doi.lower()}"
        return f"pmcid:{self.pmcid}"


_LATIN = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,80}$")
_UNSAFE = re.compile(r'["\[\]()]')

OUTCOME_TERMS = ["appetite", "anorexia", "cachexia", "food intake", "body weight", "quality of life"]
CANCER_TERMS = ["cancer", "neoplasm", "oncology", "tumor", "chemotherapy"]


def build_terms(herb: dict | None, input_text: str) -> list[str]:
    """English/Latin search terms. Literature is indexed in English, so a Hebrew-only unknown herb can't be searched."""
    terms = [t for t in ((herb or {}).get("name_en"), (herb or {}).get("latin_name")) if t]
    if not terms and _LATIN.match(input_text.strip()):
        terms = [input_text.strip()]
    terms = [_UNSAFE.sub("", t).strip() for t in terms]
    terms = list(dict.fromkeys(t for t in terms if t))
    if not terms:
        raise ResearchError("herb_unidentified", False, "no English/Latin name to search")
    return terms


def _any(terms: list[str], field: str) -> str:
    return "(" + " OR ".join(f'"{t}"{field}' for t in terms) + ")"


def pubmed_query(terms: list[str]) -> str:
    return (f"{_any(terms, '[tiab]')} AND {_any(OUTCOME_TERMS, '[tiab]')} "
            f"AND (neoplasms[mh] OR {_any(CANCER_TERMS, '[tiab]')[1:-1]})")


def europepmc_query(terms: list[str]) -> str:
    herb = "(" + " OR ".join(f'"{t}"' for t in terms) + ")"
    outcomes = "(" + " OR ".join(f'"{t}"' for t in OUTCOME_TERMS) + ")"
    cancer = "(" + " OR ".join(CANCER_TERMS) + ")"
    return f"{herb} AND {outcomes} AND {cancer}"


def _keys(s: Source) -> list[str]:
    return [k for k in (f"pmid:{s.pmid}" if s.pmid else None,
                        f"doi:{s.doi.lower()}" if s.doi else None,
                        f"pmcid:{s.pmcid}" if s.pmcid else None) if k]


def _merge(a: Source, b: Source) -> Source:
    """a wins; b only fills gaps."""
    return replace(a, **{f: getattr(b, f) for f in ("pmid", "pmcid", "doi", "journal", "pub_year", "abstract", "url")
                         if getattr(a, f) is None and getattr(b, f) is not None})


def dedupe(sources: list[Source]) -> list[Source]:
    """Same article from PubMed and Europe PMC -> one record (PubMed first, gaps filled from the other)."""
    ordered = sorted(sources, key=lambda s: s.origin != "pubmed")
    out: list[Source] = []
    index: dict[str, int] = {}
    for s in ordered:
        hit = next((index[k] for k in _keys(s) if k in index), None)
        if hit is None:
            out.append(s)
            hit = len(out) - 1
        else:
            out[hit] = _merge(out[hit], s)
        for k in _keys(out[hit]):
            index[k] = hit
    return [s for s in out if _keys(s)]


def upsert_sources(conn: Connection, sources: list[Source]) -> list[int]:
    ids = []
    for s in sources:
        doi = s.doi.lower() if s.doi else None
        row = conn.execute(
            "select id from public.literature_sources where pmid = %s or doi = %s or pmcid = %s order by id limit 1",
            (s.pmid, doi, s.pmcid),
        ).fetchone()
        if row:
            # fill gaps only with identifiers no other row owns (two partial records must not collide)
            conn.execute(
                """update public.literature_sources t set
                     pmid = coalesce(t.pmid, (select %(pmid)s::text where not exists
                              (select 1 from public.literature_sources x where x.pmid = %(pmid)s))),
                     pmcid = coalesce(t.pmcid, (select %(pmcid)s::text where not exists
                              (select 1 from public.literature_sources x where x.pmcid = %(pmcid)s))),
                     doi = coalesce(t.doi, (select %(doi)s::text where not exists
                              (select 1 from public.literature_sources x where x.doi = %(doi)s))),
                     journal = coalesce(t.journal, %(journal)s), pub_year = coalesce(t.pub_year, %(year)s),
                     abstract = coalesce(t.abstract, %(abstract)s), url = coalesce(t.url, %(url)s), fetched_at = now()
                   where t.id = %(id)s""",
                {"pmid": s.pmid, "pmcid": s.pmcid, "doi": doi, "journal": s.journal, "year": s.pub_year,
                 "abstract": s.abstract, "url": s.url, "id": row["id"]},
            )
            ids.append(row["id"])
        else:
            ids.append(conn.execute(
                """insert into public.literature_sources (pmid, pmcid, doi, title, journal, pub_year, abstract, url)
                   values (%s, %s, %s, %s, %s, %s, %s, %s) returning id""",
                (s.pmid, s.pmcid, doi, s.title, s.journal, s.pub_year, s.abstract, s.url),
            ).fetchone()["id"])
    return ids


def link_request_sources(conn: Connection, request_id, job_id: int | None, links: list[tuple[int, str]]) -> None:
    for rank, (source_id, origin) in enumerate(links, start=1):
        conn.execute(
            """insert into public.request_sources (request_id, source_id, job_id, origin, rank)
               values (%s, %s, %s, %s, %s) on conflict (request_id, source_id) do nothing""",
            (request_id, source_id, job_id, origin, rank),
        )
