from __future__ import annotations

import time

import jwt
import pytest

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_returns_non_plaintext():
    h = hash_password("hunter2")
    assert h != "hunter2"
    assert len(h) > 20


def test_hash_password_each_call_is_unique():
    a = hash_password("samepass")
    b = hash_password("samepass")
    assert a != b


def test_verify_password_accepts_correct():
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h) is True


def test_verify_password_rejects_incorrect():
    h = hash_password("correct")
    assert verify_password("wrong", h) is False


def test_verify_password_rejects_empty():
    h = hash_password("real")
    assert verify_password("", h) is False


def test_hash_unicode_password():
    """Bcrypt should handle utf-8 input."""
    pw = "пароль-тест-😀"
    h = hash_password(pw)
    assert verify_password(pw, h) is True
    assert verify_password("другой", h) is False


def test_access_token_is_decodable():
    token = create_access_token("user-123")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload
    assert "iat" in payload


def test_access_tokens_have_unique_jti():
    a = decode_token(create_access_token("u"))
    b = decode_token(create_access_token("u"))
    assert a["jti"] != b["jti"]


def test_access_token_with_wrong_secret_returns_none():
    token = create_access_token("u")
    bad = jwt.decode

    payload = decode_token(token)
    forged = jwt.encode(payload, "different-secret", algorithm=settings.jwt_algorithm)
    assert decode_token(forged) is None


def test_access_token_rejects_garbage():
    assert decode_token("not-a-token") is None
    assert decode_token("") is None
    assert decode_token("a.b.c") is None


def test_refresh_token_type_is_refresh():
    token = create_refresh_token("user-9")
    payload = decode_token(token)
    assert payload is not None
    assert payload["type"] == "refresh"
    assert payload["sub"] == "user-9"


def test_refresh_token_lives_longer_than_access_token():
    a_payload = decode_token(create_access_token("u"))
    r_payload = decode_token(create_refresh_token("u"))
    assert r_payload["exp"] > a_payload["exp"]


def test_access_token_expires_within_configured_window():
    payload = decode_token(create_access_token("u"))
    now = int(time.time())
    expected_exp = now + settings.access_token_expire_minutes * 60
    assert abs(payload["exp"] - expected_exp) < 5


def test_refresh_and_access_have_different_types():
    access = decode_token(create_access_token("u"))
    refresh = decode_token(create_refresh_token("u"))
    assert access["type"] != refresh["type"]


def test_decode_returns_none_for_expired_token():
    expired_payload = {
        "sub": "u",
        "type": "access",
        "jti": "x",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    assert decode_token(token) is None


@pytest.mark.parametrize("user_id", ["short", "long-uuid-style-id-1234567890abcdef", "with spaces"])
def test_access_token_roundtrip_various_user_ids(user_id):
    payload = decode_token(create_access_token(user_id))
    assert payload["sub"] == user_id
