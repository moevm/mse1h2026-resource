from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app, raise_server_exceptions=True)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_route_without_token_returns_401():
    client = TestClient(app)
    r = client.get("/api/v1/graph/full")
    assert r.status_code == 401


def test_protected_route_with_invalid_token_returns_401():
    client = TestClient(app)
    r = client.get(
        "/api/v1/graph/full",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r.status_code == 401


def test_login_with_invalid_email_format_returns_422():
    client = TestClient(app)
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "whatever"},
    )
    assert r.status_code == 422
    detail = r.json().get("detail")
    assert detail  # pydantic returns an array of validation errors


def test_register_with_short_password_returns_422():
    client = TestClient(app)
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "x@y.com", "username": "user1", "password": "ab"},
    )
    assert r.status_code == 422


def test_register_with_long_password_returns_422():
    client = TestClient(app)
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "x@y.com", "username": "user1", "password": "a" * 200},
    )
    assert r.status_code == 422


def test_openapi_schema_exposed():
    client = TestClient(app)
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json().get("openapi", "").startswith("3.")
