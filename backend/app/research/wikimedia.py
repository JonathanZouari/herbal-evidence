"""Wikipedia/Wikimedia Commons: resolve a plant's lead image and license attribution, for local caching.

No API key needed. Uses the MediaWiki Action API (not the REST summary endpoint) because SafeClient
blocks HTTP redirects and a common plant name is frequently a redirect to its canonical species title;
`redirects=1` resolves that server-side instead."""

import re
from dataclasses import dataclass
from urllib.parse import unquote

from app.research.http import SafeClient

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_TAG = re.compile(r"<[^>]+>")


@dataclass
class ImageResult:
    content: bytes
    content_type: str
    attribution: str
    source_url: str


def _first_page(payload: dict) -> dict | None:
    try:
        pages = payload["query"]["pages"]
    except (KeyError, TypeError):
        return None
    return next(iter(pages.values()), None)


def _resolve_page_image(client: SafeClient, title: str) -> tuple[str, str, str] | None:
    """(image_url, "File:x.jpg", page_url), or None if the page or its lead image doesn't exist."""
    r = client.get(WIKIPEDIA_API, params={"action": "query", "titles": title, "redirects": 1,
                                          "prop": "pageimages|info", "piprop": "original", "inprop": "url",
                                          "format": "json"})
    try:
        page = _first_page(r.json())
    except ValueError:
        return None
    if not page or "missing" in page or "original" not in page:
        return None
    image_url = page["original"]["source"]
    file_title = "File:" + unquote(image_url.rsplit("/", 1)[-1])
    return image_url, file_title, page.get("fullurl", f"https://en.wikipedia.org/wiki/{title}")


def _attribution(client: SafeClient, file_title: str) -> str:
    r = client.get(COMMONS_API, params={"action": "query", "titles": file_title, "prop": "imageinfo",
                                        "iiprop": "extmetadata", "format": "json"})
    try:
        page = _first_page(r.json())
        meta = page["imageinfo"][0]["extmetadata"]
    except (ValueError, KeyError, IndexError, TypeError):
        return "Wikimedia Commons"
    artist = _TAG.sub("", (meta.get("Artist") or {}).get("value", "")).strip()
    license_name = (meta.get("LicenseShortName") or {}).get("value", "")
    return " / ".join(p for p in (artist, license_name) if p) or "Wikimedia Commons"


def fetch_plant_image(client: SafeClient, name_en: str, latin_name: str | None) -> ImageResult | None:
    """Tries the scientific name first (most precise species match), then the common name. None = no image
    found anywhere, a normal outcome for callers, not an error (FetchError still propagates on real
    transport/HTTP failures)."""
    for title in filter(None, (latin_name, name_en)):
        resolved = _resolve_page_image(client, title)
        if not resolved:
            continue
        image_url, file_title, page_url = resolved
        img = client.get(image_url)
        return ImageResult(content=img.content, content_type=img.headers.get("content-type", "image/jpeg"),
                           attribution=_attribution(client, file_title), source_url=page_url)
    return None
