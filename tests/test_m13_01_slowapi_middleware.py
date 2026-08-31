"""M13-01 — SlowAPIMiddleware is registered so the 21 previously-undecorated
routes are throttled, and the two credential-checking PUT routes get a tight
explicit limit plus the login-style account-lockout treatment.

Baseline (674034e) behaviour that these pins reproduce as failures:
  * `SlowAPIMiddleware` is never added, so `default_limits` fire on nothing and
    GET /api/v1/app/version (undecorated) returns 200 forever.
  * PUT /auth/password + PUT /auth/email have no rate limit and never consult
    `check_account_locked`, so a token-bearing attacker can guess
    `current_password` at network speed.

Free-tier only: no network. The slowapi limiter uses in-memory storage and the
conftest autouse `_reset_rate_limiter` fixture gives each test a clean window.
"""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth_routes import get_current_user


@pytest.fixture()
def client():
    return TestClient(app)


def test_slowapi_middleware_is_registered():
    """The middleware that makes `default_limits` fire must be in the stack."""
    from slowapi.middleware import SlowAPIMiddleware

    classes = [m.cls for m in app.user_middleware]
    assert SlowAPIMiddleware in classes, (
        "SlowAPIMiddleware not registered — default_limits are dead config and "
        "the 21 undecorated routes have no rate limit"
    )


def test_previously_undecorated_route_now_429s(client):
    """GET /api/v1/app/version had no decorator; with the middleware added the
    default per-minute limit now fires. Pins the security lane's proof shape:
    a previously-undecorated route returns 200 x N then 429."""
    statuses = [client.get("/api/v1/app/version").status_code for _ in range(15)]
    assert statuses[0] == 200, f"first call should succeed, got {statuses[0]}"
    assert 429 in statuses, (
        f"undecorated route never rate-limited across 15 calls: {statuses}"
    )
    # Every response before the first 429 is a success (no spurious early reject).
    first_429 = statuses.index(429)
    assert all(s == 200 for s in statuses[:first_429]), statuses


def test_change_password_has_tight_explicit_limit(client, monkeypatch):
    """PUT /auth/password now carries an explicit 5/minute limit (tighter than
    the 10/min default) so credential guessing cannot run at network speed."""
    monkeypatch.setattr(
        "app.api.auth_routes.change_user_password",
        AsyncMock(return_value={"success": True, "message": "ok"}),
    )
    monkeypatch.setattr(
        "app.api.auth_routes.check_account_locked",
        AsyncMock(return_value={"locked": False, "retry_after": 0}),
    )
    monkeypatch.setattr(
        "app.api.auth_routes.track_failed_login", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.api.auth_routes.clear_failed_logins", AsyncMock(return_value=None)
    )
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "u1",
        "email": "u1@example.com",
        "access_token": "tok",
    }
    try:
        body = {"current_password": "whatever", "new_password": "NewPassw0rd"}
        statuses = [
            client.put("/api/v1/auth/password", json=body).status_code
            for _ in range(7)
        ]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert statuses[:5] == [200, 200, 200, 200, 200], statuses
    assert 429 in statuses[5:], f"6th credential attempt not throttled: {statuses}"


def test_change_password_respects_account_lockout(client, monkeypatch):
    """A locked account (the same counter POST /login uses) must 429 with
    ACCOUNT_LOCKED before the password is ever checked."""
    verify = AsyncMock(return_value={"success": True, "message": "ok"})
    monkeypatch.setattr("app.api.auth_routes.change_user_password", verify)
    monkeypatch.setattr(
        "app.api.auth_routes.check_account_locked",
        AsyncMock(return_value={"locked": True, "retry_after": 300}),
    )
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "u1",
        "email": "locked@example.com",
        "access_token": "tok",
    }
    try:
        resp = client.put(
            "/api/v1/auth/password",
            json={"current_password": "x", "new_password": "NewPassw0rd"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 429, resp.text
    assert resp.json().get("code") == "ACCOUNT_LOCKED", resp.text
    verify.assert_not_awaited()  # password never checked while locked


def test_update_email_respects_account_lockout(client, monkeypatch):
    """PUT /auth/email gets the same lockout treatment as PUT /auth/password."""
    verify = AsyncMock(return_value={"success": True, "message": "ok"})
    monkeypatch.setattr("app.api.auth_routes.update_user_email", verify)
    monkeypatch.setattr(
        "app.api.auth_routes.check_account_locked",
        AsyncMock(return_value={"locked": True, "retry_after": 300}),
    )
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "u1",
        "email": "locked@example.com",
        "access_token": "tok",
    }
    try:
        resp = client.put(
            "/api/v1/auth/email",
            json={"new_email": "new@example.com", "current_password": "x"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 429, resp.text
    assert resp.json().get("code") == "ACCOUNT_LOCKED", resp.text
    verify.assert_not_awaited()
