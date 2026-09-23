import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.auth.jwt import verify_token
from app.domain.herbs import normalize
from app.domain.status import TRANSITIONS, can_transition
from app.errors import AppError

ISS = "https://example.supabase.co/auth/v1"
KEY = ec.generate_private_key(ec.SECP256R1())


def token(**over):
    claims = {"sub": str(uuid.uuid4()), "aud": "authenticated", "iss": ISS, "exp": int(time.time()) + 60} | over
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, KEY, algorithm="ES256")


def test_valid_token():
    sub = str(uuid.uuid4())
    assert str(verify_token(token(sub=sub), KEY.public_key(), ISS)) == sub


@pytest.mark.parametrize("bad", [
    {"exp": int(time.time()) - 10},       # expired
    {"aud": "anon"},                      # wrong audience
    {"iss": "https://evil.example/auth/v1"},
    {"sub": None},                        # missing sub
    {"sub": "not-a-uuid"},
])
def test_rejected_tokens(bad):
    with pytest.raises(AppError) as e:
        verify_token(token(**bad), KEY.public_key(), ISS)
    assert e.value.status == 401


def test_wrong_signature():
    other = ec.generate_private_key(ec.SECP256R1())
    forged = jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated", "iss": ISS,
                         "exp": int(time.time()) + 60}, other, algorithm="ES256")
    with pytest.raises(AppError):
        verify_token(forged, KEY.public_key(), ISS)


def test_hs256_not_accepted():
    hs = jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated", "iss": ISS,
                     "exp": int(time.time()) + 60}, "secret-that-is-long-enough-for-hs256", algorithm="HS256")
    with pytest.raises(AppError):
        verify_token(hs, KEY.public_key(), ISS)


def test_transitions():
    assert can_transition("submitted", "researching")
    assert can_transition("in_review", "published")
    assert not can_transition("submitted", "published")      # no publish without review
    assert not can_transition("draft_ready", "published")
    assert not TRANSITIONS["withdrawn"] and not TRANSITIONS["closed"]
    assert all(dst in TRANSITIONS for dsts in TRANSITIONS.values() for dst in dsts)


@pytest.mark.parametrize("raw,expected", [
    ("  Ginger ", "ginger"),
    ("ג׳ינג׳ר", "ג'ינג'ר"),     # Hebrew geresh
    ("ג’ינג’ר", "ג'ינג'ר"),     # typographic apostrophe
    ("Panax   Ginseng", "panax ginseng"),
])
def test_normalize(raw, expected):
    assert normalize(raw) == expected
