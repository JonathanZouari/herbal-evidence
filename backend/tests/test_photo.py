"""Herb photo identification (D-021): image validation, quota, OpenAI adapter, resolving to listed herbs. No DB."""

import base64
import json
import uuid

import httpx
import pytest

from app.ai.openai import OpenAIProvider, parse_identify_response
from app.ai.provider import NullProvider, ProviderError
from app.ai.schema import HerbGuess
from app.auth.jwt import CurrentUser
from app.errors import AppError
from app.research.http import SafeClient
from app.services import photo
from tests.helpers import openai_body

JPEG = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"x" * 100).decode()
HERBS = [{"id": 1, "name_he": "ג׳ינג׳ר", "name_en": "Ginger", "latin_name": "Zingiber officinale"},
         {"id": 2, "name_he": "כורכום", "name_en": "Turmeric", "latin_name": "Curcuma longa"}]


def guess(**kw) -> HerbGuess:
    return HerbGuess(**({"is_plant": True, "match": "1", "latin_name": "Zingiber officinale", "name_he": "ג׳ינג׳ר",
                         "certainty": "high"} | kw))


class FakeConn:
    def execute(self, *_):
        return self

    def fetchall(self):
        return HERBS


class FakeProvider:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def identify_herb(self, image, herbs):
        self.calls.append(image)
        if self.error:
            raise self.error
        return self.result


USER = CurrentUser(uuid.uuid4(), "user")


# ------------------------------------------------------------------ image validation


def test_decode_image_ok():
    assert photo.decode_image(JPEG) == JPEG
    png = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 10).decode()
    webp = "data:image/webp;base64," + base64.b64encode(b"RIFF\x00\x00\x00\x00WEBPVP8 ").decode()
    assert photo.decode_image(png) == png and photo.decode_image(webp) == webp


@pytest.mark.parametrize("bad", [
    "not a data url",
    "data:image/gif;base64,R0lGODlh",                                          # type not allowed
    "data:image/svg+xml;base64,PHN2Zz4=",                                      # svg: never
    "data:image/jpeg;base64,@@@@",                                             # not base64
    "data:image/jpeg;base64," + base64.b64encode(b"hello world").decode(),     # not a jpeg
    "data:image/webp;base64," + base64.b64encode(b"RIFF\x00\x00\x00\x00AVI ").decode(),
])
def test_decode_image_invalid(bad):
    with pytest.raises(AppError) as e:
        photo.decode_image(bad)
    assert (e.value.status, e.value.code) == (422, "image_invalid")


def test_decode_image_too_large():
    big = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff" + b"x" * photo.MAX_IMAGE_BYTES).decode()
    with pytest.raises(AppError) as e:
        photo.decode_image(big)
    assert e.value.code == "image_too_large"


def test_hourly_quota():
    now = [0.0]
    q = photo.HourlyQuota(clock=lambda: now[0])
    uid, other = uuid.uuid4(), uuid.uuid4()
    assert all(q.take(uid, 3) for _ in range(3))
    assert not q.take(uid, 3) and q.take(other, 3)
    now[0] = 3601
    assert q.take(uid, 3)


# ------------------------------------------------------------------ resolve / identify


def test_resolve_listed_herb_uses_db_names():
    r = photo.resolve(guess(match="2", name_he="שם שהמודל המציא", latin_name="Wrong"), HERBS)
    assert r == {"herb_id": 2, "name_he": "כורכום", "name_en": "Turmeric", "latin_name": "Curcuma longa",
                 "certainty": "high", "in_list": True}


def test_resolve_unlisted_herb():
    r = photo.resolve(guess(match="none", name_he="מרווה", latin_name="Salvia officinalis", certainty="medium"), HERBS)
    assert r == {"herb_id": None, "name_he": "מרווה", "name_en": None, "latin_name": "Salvia officinalis",
                 "certainty": "medium", "in_list": False}


@pytest.mark.parametrize("g", [guess(match="none", is_plant=False), guess(match="none", name_he=None, latin_name=None)])
def test_resolve_not_identified(g):
    with pytest.raises(AppError) as e:
        photo.resolve(g, HERBS)
    assert (e.value.status, e.value.code) == (422, "herb_not_identified")


def test_identify_happy_path():
    p = FakeProvider(guess())
    r = photo.identify(FakeConn(), USER, JPEG, provider=p, quota=photo.HourlyQuota())
    assert r["herb_id"] == 1 and r["in_list"] and p.calls == [JPEG]


@pytest.mark.parametrize("error,status,code", [
    (None, 503, "ai_not_configured"),                                      # NullProvider
    (ProviderError("ai_refused", False), 422, "herb_not_identified"),
    (ProviderError("ai_unavailable", True), 502, "photo_identify_failed"),
    (ProviderError("ai_bad_output", True), 502, "photo_identify_failed"),
])
def test_identify_errors(error, status, code):
    p = FakeProvider(error=error) if error else NullProvider()
    with pytest.raises(AppError) as e:
        photo.identify(FakeConn(), USER, JPEG, provider=p, quota=photo.HourlyQuota())
    assert (e.value.status, e.value.code) == (status, code)


def test_identify_quota_and_invalid_image_not_counted():
    q, p = photo.HourlyQuota(), FakeProvider(guess())
    with pytest.raises(AppError):
        photo.identify(FakeConn(), USER, "data:image/gif;base64,AAAA", provider=p, quota=q)
    for _ in range(20):
        photo.identify(FakeConn(), USER, JPEG, provider=p, quota=q)
    with pytest.raises(AppError) as e:
        photo.identify(FakeConn(), USER, JPEG, provider=p, quota=q)
    assert (e.value.status, e.value.code) == (429, "quota_photo") and len(p.calls) == 20


# ------------------------------------------------------------------ OpenAI adapter


def test_openai_identify_request():
    seen = {}

    def handler(r: httpx.Request):
        seen["body"] = json.loads(r.content)
        return httpx.Response(200, json=openai_body(guess().model_dump()))
    p = OpenAIProvider(SafeClient(transport=httpx.MockTransport(handler)), "sk-test-SECRET", "some-model")
    assert p.identify_herb(JPEG, HERBS) == guess()
    body = seen["body"]
    assert body["store"] is False and body["text"]["format"]["strict"] is True
    content = body["input"][0]["content"]
    assert content[1] == {"type": "input_image", "image_url": JPEG}
    assert "Zingiber officinale" in content[0]["text"]
    assert body["text"]["format"]["schema"]["properties"]["match"]["enum"] == ["1", "2", "none"]
    assert set(body["text"]["format"]["schema"]["required"]) == set(HerbGuess.model_fields)


@pytest.mark.parametrize("payload,code", [
    (openai_body(guess(match="99").model_dump()), "ai_bad_output"),           # not a listed id
    (openai_body(text="{not json"), "ai_bad_output"),
    (openai_body(guess().model_dump() | {"certainty": "87%"}), "ai_bad_output"),
    (openai_body(refusal=True), "ai_refused"),
])
def test_parse_identify_errors(payload, code):
    with pytest.raises(ProviderError) as e:
        parse_identify_response(json.dumps(payload).encode(), {"1", "2"})
    assert e.value.code == code


def test_parse_identify_none():
    g = parse_identify_response(json.dumps(openai_body(guess(match="none").model_dump())).encode(), {"1"})
    assert g.match == "none"
