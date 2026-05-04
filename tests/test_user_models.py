from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.user import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


def test_register_request_valid():
    r = RegisterRequest(email="alice@example.com", username="alice", password="secret123")
    assert r.email == "alice@example.com"
    assert r.username == "alice"


def test_register_rejects_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", username="alice", password="secret")


def test_register_rejects_too_short_username():
    with pytest.raises(ValidationError):
        RegisterRequest(email="x@y.com", username="ab", password="secret")


def test_register_rejects_too_long_username():
    with pytest.raises(ValidationError):
        RegisterRequest(email="x@y.com", username="a" * 33, password="secret")


def test_register_rejects_too_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email="x@y.com", username="alice", password="ab")


def test_register_rejects_password_over_72_chars():
    with pytest.raises(ValidationError):
        RegisterRequest(email="x@y.com", username="alice", password="a" * 73)


def test_register_accepts_password_at_72_chars():
    r = RegisterRequest(email="x@y.com", username="alice", password="a" * 72)
    assert len(r.password) == 72


def test_register_accepts_password_at_min_length():
    r = RegisterRequest(email="x@y.com", username="alice", password="abcde")
    assert r.password == "abcde"


def test_login_valid():
    r = LoginRequest(email="alice@example.com", password="anything")
    assert r.email == "alice@example.com"


def test_login_rejects_invalid_email_format():
    with pytest.raises(ValidationError):
        LoginRequest(email="alice", password="x")


def test_login_rejects_empty_password():
    with pytest.raises(ValidationError):
        LoginRequest(email="x@y.com", password="")


def test_login_rejects_password_over_72():
    with pytest.raises(ValidationError):
        LoginRequest(email="x@y.com", password="a" * 73)


def test_user_response_defaults():
    u = UserResponse(user_id="u1", email="x@y.com", username="bob")
    assert u.is_active is True
    assert u.created_at is None


def test_token_response_default_token_type_is_bearer():
    t = TokenResponse(access_token="a.b.c", refresh_token="r.r.r")
    assert t.token_type == "bearer"


def test_refresh_token_request():
    r = RefreshTokenRequest(refresh_token="abcd")
    assert r.refresh_token == "abcd"


def test_refresh_token_request_rejects_missing_field():
    with pytest.raises(ValidationError):
        RefreshTokenRequest()  # type: ignore[call-arg]
