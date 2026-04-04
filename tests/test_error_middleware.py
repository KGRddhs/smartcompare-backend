"""Tests for unified error response middleware."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth_routes import get_current_user


def _get_test_client():
    return TestClient(app)


# ============================================
# Error format validation
# ============================================


def test_explicit_404_returns_unified_format():
    """Explicit HTTPException(404) returns unified error format."""
    # Trigger a real 404 from an endpoint (history GET with nonexistent ID)
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1", "email": "t@t.com"}
    try:
        with patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None):
            client = _get_test_client()
            resp = client.get("/api/v1/comparisons/00000000-0000-0000-0000-000000000000")
            assert resp.status_code == 404
            data = resp.json()
            assert data["success"] is False
            assert data["code"] == "NOT_FOUND"
            assert "error" in data
            assert "request_id" in data
    finally:
        app.dependency_overrides.clear()


def test_422_validation_error_format():
    """Invalid request body returns VALIDATION_ERROR code."""
    client = _get_test_client()
    # POST to compare with invalid body (missing required fields)
    resp = client.post("/api/v1/text/compare", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert data["success"] is False
    assert data["code"] == "VALIDATION_ERROR"
    assert "request_id" in data


def test_401_returns_auth_required():
    """Auth-required endpoint without token returns AUTH_REQUIRED."""
    app.dependency_overrides.clear()
    client = _get_test_client()
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert data["success"] is False
    assert data["code"] == "AUTH_REQUIRED"


def test_error_response_has_request_id():
    """Error responses from explicit HTTPException include request_id."""
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1", "email": "t@t.com"}
    try:
        with patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None):
            client = _get_test_client()
            resp = client.get("/api/v1/comparisons/00000000-0000-0000-0000-000000000000")
            data = resp.json()
            assert "request_id" in data
            assert data["request_id"] != "unknown"
    finally:
        app.dependency_overrides.clear()


def test_403_forbidden_format():
    """Unauthorized access returns 404 (merged 403/404 to prevent enumeration)."""
    mock_comparison = {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "user_id": "other-user", "query": "test",
        "product_names": [], "input_type": "text", "full_response": {}, "created_at": "2026-01-01"
    }
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1", "email": "t@t.com"}
    try:
        with patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=mock_comparison):
            client = _get_test_client()
            resp = client.get("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
            assert resp.status_code == 404
            data = resp.json()
            assert data["success"] is False
            assert data["code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_not_affected():
    """Health check still returns normal response (not error format)."""
    client = _get_test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    # Should NOT have error format fields
    assert "code" not in data


def test_error_format_fields_on_explicit_404():
    """Error responses have exactly: success, error, code, request_id."""
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1", "email": "t@t.com"}
    try:
        with patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None):
            client = _get_test_client()
            resp = client.get("/api/v1/comparisons/00000000-0000-0000-0000-000000000000")
            data = resp.json()
            expected_keys = {"success", "error", "code", "request_id"}
            assert set(data.keys()) == expected_keys
    finally:
        app.dependency_overrides.clear()


# ============================================
# Rate limit error format
# ============================================


def test_rate_limit_error_format():
    """Verify rate limit handler produces correct format."""
    from app.middleware.error_handler import _build_error_response
    import json
    resp = _build_error_response(429, "Rate limit exceeded", "test-id")
    data = json.loads(resp.body.decode())
    assert data["success"] is False
    assert data["code"] == "RATE_LIMITED"
    assert data["request_id"] == "test-id"


def test_build_error_response_unknown_status():
    """Unknown status codes default to SERVER_ERROR."""
    from app.middleware.error_handler import _build_error_response
    import json
    resp = _build_error_response(418, "I'm a teapot", "test-id")
    data = json.loads(resp.body.decode())
    assert data["code"] == "SERVER_ERROR"
    assert data["error"] == "I'm a teapot"


def test_build_error_response_all_status_codes():
    """Verify all mapped status codes produce correct error codes."""
    from app.middleware.error_handler import _build_error_response, STATUS_CODE_MAP
    import json
    for status, code in STATUS_CODE_MAP.items():
        resp = _build_error_response(status, "test", "req-1")
        data = json.loads(resp.body.decode())
        assert data["code"] == code, f"Status {status} should map to {code}"
