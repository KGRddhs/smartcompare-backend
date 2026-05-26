"""B4 social login smoke — Bundle E test lane.

Mocks `sign_in_with_social` at the route boundary so we can exercise:
- Valid 3-part JWT id_token for provider=google → 200 + session shape
- Invalid token shape (no dots) → still routed through; service-level
  rejection returns 401
- Missing id_token field → 422 (Pydantic)
- Apple regression: provider=apple with valid token still succeeds (Path A
  R1 nonce drop must not regress Apple)

We do NOT call live Supabase. The route is gated by `sign_in_with_social`
in `app.api.auth_routes`; patch it.
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# Bypass slowapi rate limit (10/min on /social-login).
@pytest.fixture(autouse=True)
def _disable_limiter():
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prior


# A minimal-shape valid Google id_token: header.payload.signature.
# Real Google JWTs are much longer; tests only need 3 segments because the
# service-level token_segs trace counts dots.
VALID_GOOGLE_JWT = (
    "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMyJ9"
    ".eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJzdWIiOiIxIn0"
    ".sig-placeholder-not-verified-in-mocked-flow"
)
VALID_APPLE_JWT = (
    "eyJhbGciOiJSUzI1NiIsImtpZCI6IkFCQyJ9"
    ".eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIiwic3ViIjoiMSJ9"
    ".sig-placeholder"
)


# ---- Happy paths ----


def test_google_signin_valid_jwt_returns_200_with_session():
    """Valid 3-part Google JWT → 200 + AuthResponse-shaped body."""
    success_payload = {
        "success": True,
        "user": {
            "id": "00000000-0000-0000-0000-000000000001",
            "email": "u@gmail.com",
            "preferences_completed": False,
        },
        "session": {
            "access_token": "supabase-access-token",
            "refresh_token": "supabase-refresh-token",
            "expires_at": 1234567890,
        },
        "message": "Signed in with google",
    }
    with patch(
        "app.api.auth_routes.sign_in_with_social",
        new=AsyncMock(return_value=success_payload),
    ) as mock_signin:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/social-login",
            json={"provider": "google", "id_token": VALID_GOOGLE_JWT},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["user"]["id"] == "00000000-0000-0000-0000-000000000001"
        # Session at top-level (NOT nested under data) — matches login response
        # shape contract: access_token at session.access_token.
        assert body["session"]["access_token"] == "supabase-access-token"
        # Service was called with (provider, id_token, nonce) — Google flow
        # passes nonce=None (Apple-only field).
        mock_signin.assert_awaited_once()
        call_args = mock_signin.await_args
        assert call_args.args[0] == "google"
        assert call_args.args[1] == VALID_GOOGLE_JWT
        # third positional or kwarg `nonce` must be None for Google.
        nonce_val = call_args.args[2] if len(call_args.args) > 2 else call_args.kwargs.get("nonce")
        assert nonce_val is None


def test_apple_signin_valid_jwt_with_nonce_succeeds():
    """Apple regression — Path A R1 dropped FE nonce but Apple BE flow still
    accepts nonce kwarg. Verify Apple sign-in is not broken by Google fix."""
    success_payload = {
        "success": True,
        "user": {"id": "u-apple", "email": "u@privaterelay.appleid.com", "preferences_completed": True},
        "session": {"access_token": "atk", "refresh_token": "rtk", "expires_at": 999},
        "message": "Signed in with apple",
    }
    with patch(
        "app.api.auth_routes.sign_in_with_social",
        new=AsyncMock(return_value=success_payload),
    ) as mock_signin:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/social-login",
            json={
                "provider": "apple",
                "id_token": VALID_APPLE_JWT,
                "nonce": "raw-nonce-from-apple-sdk",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["user"]["email"].endswith("@privaterelay.appleid.com")
        # Apple flow MUST forward the nonce to the service so Supabase can
        # verify it against the JWT claim. Path A R1 dropped FE nonce; Apple
        # still relies on it server-side.
        call_args = mock_signin.await_args
        nonce_val = call_args.args[2] if len(call_args.args) > 2 else call_args.kwargs.get("nonce")
        assert nonce_val == "raw-nonce-from-apple-sdk"


# ---- Failure paths ----


def test_signin_invalid_token_shape_returns_401():
    """Token with 0 dots (opaque, not a JWT) — service rejects → 401 per route."""
    rejection = {"success": False, "error": "Invalid id_token (not a JWT)"}
    with patch(
        "app.api.auth_routes.sign_in_with_social",
        new=AsyncMock(return_value=rejection),
    ):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/social-login",
            json={"provider": "google", "id_token": "opaque-no-dots-here"},
        )
        # Route maps service success=False to 401.
        assert resp.status_code == 401, resp.text
        body = resp.json()
        # Unified error envelope from error_handler middleware OR FastAPI
        # legacy detail field — accept either.
        err_text = (body.get("error") or body.get("detail") or "").lower()
        assert "id_token" in err_text or "invalid" in err_text or "auth" in err_text


def test_signin_missing_id_token_returns_422():
    """Pydantic field validation — id_token is required."""
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/social-login",
        json={"provider": "google"},
    )
    # Pydantic-level missing field → 422 (validation). The error_handler
    # middleware preserves Pydantic 422s.
    assert resp.status_code == 422


def test_signin_invalid_provider_returns_422():
    """Provider Literal['google','apple'] — anything else → 422."""
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/social-login",
        json={"provider": "facebook", "id_token": VALID_GOOGLE_JWT},
    )
    assert resp.status_code == 422


# ---- Trace assertion (B4 diagnostic) ----


def test_signin_logs_social_login_trace_for_google(caplog):
    """The Bundle D Phase 3 [SOCIAL_LOGIN_TRACE] line must fire for Google.

    This is the diagnostic line backend lane keys off to triangulate B4 per
    design doc § 3.5 matrix. If it stops firing we lose all visibility.
    """
    success_payload = {
        "success": True,
        "user": {"id": "u-1", "email": "u@gmail.com", "preferences_completed": False},
        "session": {"access_token": "a", "refresh_token": "r", "expires_at": 1},
        "message": "ok",
    }
    # Patch only the Supabase boundary so the trace logger line fires from the
    # real `sign_in_with_social` function in auth_service.
    with patch(
        "app.services.auth_service.get_auth_client"
    ) as gac, patch("app.services.auth_service.get_admin_client") as gadmin:
        # Mock the auth client's sign_in_with_id_token to return a user+session
        mock_user = type("U", (), {"id": "u-1", "email": "u@gmail.com"})()
        mock_session = type(
            "S", (), {"access_token": "a", "refresh_token": "r", "expires_at": 1}
        )()
        mock_response = type("R", (), {"user": mock_user, "session": mock_session})()
        gac.return_value.auth.sign_in_with_id_token.return_value = mock_response
        # Admin client used to look up the user row + preferences_completed.
        existing = type("E", (), {"data": [{"id": "u-1"}]})()
        prefs = type("P", (), {"data": {"preferences_completed": False}})()
        gadmin.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = existing
        gadmin.return_value.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = prefs

        client = TestClient(app)
        with caplog.at_level("INFO", logger="app.services.auth_service"):
            resp = client.post(
                "/api/v1/auth/social-login",
                json={"provider": "google", "id_token": VALID_GOOGLE_JWT},
            )
        # Trace line presence is what we assert. The 200 is best-effort —
        # the enrichment path may short-circuit without affecting the trace.
        trace_lines = [
            r.getMessage() for r in caplog.records
            if "[SOCIAL_LOGIN_TRACE]" in r.getMessage()
        ]
        assert trace_lines, "Expected [SOCIAL_LOGIN_TRACE] log line for Google sign-in"
        line = trace_lines[0]
        assert "provider=google" in line
        # token_segs = dots + 1 = 3 for a proper JWT
        assert "token_segs=3" in line
        assert "nonce_present=False" in line
