"""PubMed E-utilities: esearch (ids) -> efetch (records). https://www.ncbi.nlm.nih.gov/books/NBK25497/"""

import xml.etree.ElementTree as ET

from app.research.http import RateLimiter, SafeClient
from app.research.sources import ResearchError, Source

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# NCBI: 3 requests/s without an API key, 10 with one. One limiter per process (single backend replica).
_limiters = {False: RateLimiter(3), True: RateLimiter(10)}


def _params(api_key: str | None, tool: str, email: str) -> dict:
    p = {"db": "pubmed", "tool": tool}
    if email:
        p["email"] = email
    if api_key:
        p["api_key"] = api_key
    return p


def search(client: SafeClient, query: str, retmax: int, api_key: str | None = None,
           tool: str = "herbal-evidence", email: str = "") -> list[Source]:
    limiter = _limiters[bool(api_key)]
    base = _params(api_key, tool, email)
    r = client.get(f"{BASE}/esearch.fcgi", limiter=limiter,
                   params={**base, "term": query, "retmax": retmax, "retmode": "json", "sort": "relevance"})
    try:
        ids = r.json()["esearchresult"]["idlist"]
    except (ValueError, KeyError) as e:
        raise ResearchError("pubmed_bad_response", True, type(e).__name__) from None
    if not ids:
        return []
    r = client.get(f"{BASE}/efetch.fcgi", limiter=limiter,
                   params={**base, "id": ",".join(ids), "retmode": "xml", "rettype": "abstract"})
    return parse_efetch(r.content)


def _text(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    t = "".join(el.itertext()).strip()
    return t or None


def _year(article: ET.Element) -> int | None:
    for path in (".//JournalIssue/PubDate/Year", ".//ArticleDate/Year", ".//JournalIssue/PubDate/MedlineDate"):
        t = _text(article.find(path))
        if t and t[:4].isdigit():
            return int(t[:4])
    return None


def parse_efetch(xml: bytes) -> list[Source]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        raise ResearchError("pubmed_bad_response", True, "xml") from None
    out = []
    for art in root.iter("PubmedArticle"):
        pmid = _text(art.find(".//MedlineCitation/PMID"))
        title = _text(art.find(".//Article/ArticleTitle"))
        if not pmid or not title:
            continue
        ids = {i.get("IdType"): _text(i) for i in art.findall(".//PubmedData/ArticleIdList/ArticleId")}
        parts = []
        for a in art.findall(".//Article/Abstract/AbstractText"):
            label, text = a.get("Label"), _text(a)
            if text:
                parts.append(f"{label}: {text}" if label else text)
        doi = ids.get("doi")
        out.append(Source(
            title=title, origin="pubmed", pmid=pmid, pmcid=ids.get("pmc"), doi=doi.lower() if doi else None,
            journal=_text(art.find(".//Article/Journal/Title")), pub_year=_year(art),
            abstract="\n".join(parts) or None, url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        ))
    return out
