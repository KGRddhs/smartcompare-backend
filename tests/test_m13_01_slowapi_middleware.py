"""M13-01 — the blanket `default_limits` throttle for the 21 previously-
undecorated routes is gated behind the default-OFF ENABLE_DEFAULT_RATE_LIMITS
flag (closeout finding A), and the two credential-checking PUT routes get a tight
explicit limit plus the login-style account-lockout treatment (LIVE, unflagged —
decorator-driven, independent of the gated middleware).

Closeout dispatcher-gate: the front-door wave originally registered
SlowAPIMiddleware unflagged, which — under the shipped ENABLE_PROXY_AWARE_RATELIMIT
OFF default — keys the blanket 10/min on the shared Railway edge-proxy IP, i.e.
ONE deployment-wide bucket per URL path. That 429s the hot app-open reads
(/app/version, /usage/status, /auth/me, /auth/verify) and infra (/health, /,
/favicon.ico) for every user once aggregate path traffic tops 10/min. So the
blanket default is gated behind a NEW default-OFF flag; flag-OFF is byte-identical
to 674034e (no middleware, no default limit).

Free-tier only: no network. The slowapi limiter uses in-memory storage and the
conftest autouse `_reset_rate_limiter` fixture gives each test a clean window.
"""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app
from app.api.auth_routes import get_current_user


@pytest.fixture()
def client():
    return TestClient(app)


def test_default_rate_limits_gated_off_by_default():
    """Shipped default (flag unset): SlowAPIMiddleware is NOT registered, so the
    blanket default_limits are inert — byte-identical to 674034e. This is the
    guard that keeps the deployment-wide-per-path availability regression from
    shipping live."""
    from slowapi.middleware import SlowAPIMiddleware
    from app.middleware.rate_limiter import _default_rate_limits_enabled

    assert _default_rate_limits_enabled() is False, (
        "ENABLE_DEFAULT_RATE_LIMITS must default OFF"
    )
    classes = [m.cls for m in app.user_middleware]
    assert SlowAPIMiddleware not in classes, (
        "SlowAPIMiddleware must NOT be registered when the gate is OFF — the "
        "blanket 10/min default would be a deployment-wide per-path cap under "
        "the shared proxy IP"
    )


def test_undecorated_route_not_throttled_when_gate_off(client):
    """Byte-identity: with the gate OFF an undecorated hot read route
    (GET /app/version) returns 200 forever — never 429 — exactly as at 674034e.
    (The reviewers' regression: this route 429ing all users deployment-wide.)"""
    statuses = [client.get("/api/v1/app/version").status_code for _ in range(15)]
    assert all(s == 200 for s in statuses), (
        f"undecorated route must not be throttled when the gate is OFF: {statuses}"
    )


def test_default_limits_fire_when_gate_on(monkeypatch):
    """Gate ON: SlowAPIMiddleware makes default_limits fire on an undecorated
    route — 200 x N then 429. Proven on a minimal app wired to the SAME limiter
    (avoids reloading app.main), which is exactly the registration app.main does
    when ENABLE_DEFAULT_RATE_LIMITS is set."""
    monkeypatch.setenv("ENABLE_DEFAULT_RATE_LIMITS", "1")
    from fastapi import FastAPI
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from app.middleware.rate_limiter import limiter, _default_rate_limits_enabled

    assert _default_rate_limits_enabled() is True

    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @test_app.get("/undecorated")
    async def _undecorated(request: Request):  # no @limiter.limit — default only
        return {"ok": True}

    test_app.add_middleware(SlowAPIMiddleware)

    with TestClient(test_app) as tc:
        statuses = [tc.get("/undecorated").status_code for _ in range(15)]
    assert statuses[0] == 200, statuses
    assert 429 in statuses, (
        f"default_limits never fired with the gate ON + middleware present: {statuses}"
    )
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
