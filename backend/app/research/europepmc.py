"""Europe PMC REST search. https://europepmc.org/RestfulWebService"""

from app.research.http import RateLimiter, SafeClient
from app.research.sources import ResearchError, Source

URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_limiter = RateLimiter(5)


def search(client: SafeClient, query: str, page_size: int) -> list[Source]:
    r = client.get(URL, limiter=_limiter,
                   params={"query": query, "format": "json", "resultType": "core", "pageSize": page_size})
    try:
        results = r.json()["resultList"]["result"]
    except (ValueError, KeyError) as e:
        raise ResearchError("europepmc_bad_response", True, type(e).__name__) from None
    return [s for s in map(parse_result, results) if s]


def parse_result(x: dict) -> Source | None:
    title = (x.get("title") or "").strip()
    pmid, pmcid, doi = x.get("pmid"), x.get("pmcid"), x.get("doi")
    if not title or not (pmid or pmcid or doi):
        return None
    year = x.get("pubYear")
    journal = ((x.get("journalInfo") or {}).get("journal") or {}).get("title") or x.get("journalTitle")
    if pmid:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    elif pmcid:
        url = f"https://europepmc.org/article/PMC/{pmcid}"
    else:
        url = f"https://doi.org/{doi}"
    return Source(
        title=title, origin="europepmc", pmid=pmid, pmcid=pmcid, doi=doi.lower() if doi else None,
        journal=journal, pub_year=int(year) if str(year or "").isdigit() else None,
        abstract=(x.get("abstractText") or "").strip() or None, url=url,
    )
