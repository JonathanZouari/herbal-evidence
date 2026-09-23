"""Herb identification from a photo (D-021). The photo is sent to the AI provider and then discarded: it is never
written to the DB, Storage or logs. The answer only pre-fills the herb name on the request form."""

import base64
import binascii
import logging
import re
import time
from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock
from uuid import UUID

from psycopg import Connection

from app.ai.provider import AIProvider, ProviderError, ProviderNotConfigured, get_provider
from app.ai.schema import HerbGuess
from app.auth.jwt import CurrentUser
from app.errors import AppError
from app.research.http import SafeClient
from app.settings import get_settings

log = logging.getLogger("app.photo")

MAX_IMAGE_BYTES = 2_000_000
_DATA_URL = re.compile(r"data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/]+={0,2})")
_MAGIC = {"image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG\r\n\x1a\n",), "image/webp": (b"RIFF",)}


def decode_image(data_url: str) -> str:
    """Validated data URL (jpeg/png/webp, real image bytes, <= 2 MB decoded)."""
    m = _DATA_URL.fullmatch(data_url)
    if not m:
        raise AppError(422, "image_invalid")
    mime, b64 = m.groups()
    if len(b64) * 3 // 4 > MAX_IMAGE_BYTES + 2:
        raise AppError(422, "image_too_large")
    try:
        data = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise AppError(422, "image_invalid") from None
    if len(data) > MAX_IMAGE_BYTES:
        raise AppError(422, "image_too_large")
    if not data.startswith(_MAGIC[mime]) or (mime == "image/webp" and data[8:12] != b"WEBP"):
        raise AppError(422, "image_invalid")
    return data_url


class HourlyQuota:
    """ponytail: in-memory per-user sliding window, like the per-IP limiter; only correct with ONE backend replica."""

    def __init__(self, clock=time.monotonic):
        self._hits: dict[UUID, deque] = defaultdict(deque)
        self._lock, self._clock = Lock(), clock

    def take(self, user_id: UUID, limit: int) -> bool:
        now = self._clock()
        with self._lock:
            q = self._hits[user_id]
            while q and now - q[0] > 3600:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


_quota = HourlyQuota()


@lru_cache
def _provider() -> AIProvider:
    return get_provider(get_settings(), SafeClient())


def resolve(guess: HerbGuess, herbs: list[dict]) -> dict:
    """Listed herb -> names from the DB (never the model's text). Otherwise the model's own name, marked in_list=False."""
    herb = next((h for h in herbs if str(h["id"]) == guess.match), None)
    if herb:
        return {"herb_id": herb["id"], "name_he": herb["name_he"], "name_en": herb["name_en"],
                "latin_name": herb["latin_name"], "certainty": guess.certainty, "in_list": True}
    if not guess.is_plant or not (guess.name_he or guess.latin_name):
        raise AppError(422, "herb_not_identified")
    return {"herb_id": None, "name_he": guess.name_he, "name_en": None, "latin_name": guess.latin_name,
            "certainty": guess.certainty, "in_list": False}


def identify(conn: Connection, user: CurrentUser, image: str, provider: AIProvider | None = None,
             quota: HourlyQuota | None = None) -> dict:
    data_url = decode_image(image)
    if not (quota or _quota).take(user.id, get_settings().photo_identify_per_hour):
        raise AppError(429, "quota_photo")
    # read before the AI call; the pool is autocommit, so no transaction stays open during HTTP (D-019)
    herbs = conn.execute("select id, name_he, name_en, latin_name from public.herbs order by id").fetchall()
    try:
        guess = (provider or _provider()).identify_herb(data_url, herbs)
    except ProviderNotConfigured:
        raise AppError(503, "ai_not_configured") from None
    except ProviderError as e:
        if e.code == "ai_refused":
            raise AppError(422, "herb_not_identified") from None
        log.warning("photo identification failed: %s", e.code)   # the code only, never the image
        raise AppError(502, "photo_identify_failed") from None
    return resolve(guess, herbs)
