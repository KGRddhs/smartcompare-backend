"""Tests for share route endpoints (POST create, GET view) and DB functions."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth_routes import get_current_user


MOCK_USER = {"id": "user-123", "email": "test@example.com"}
MOCK_OTHER_USER = {"id": "user-999", "email": "other@example.com"}

MOCK_COMPARISON = {
    "id": "comp-abc",
    "query": "iPhone 15 vs Galaxy S24",
    "product_names": ["Apple iPhone 15", "Samsung Galaxy S24"],
    "input_type": "text",
    "user_id": "user-123",
    "share_token": None,
    "full_response": {
        "success": True,
        "products": [{"brand": "Apple", "name": "iPhone 15"}],
        "personalized": True,
        "personalization_factors": ["price", "quality"],
    },
    "created_at": "2026-03-18T10:00:00Z",
}

MOCK_SHARED = {
    "id": "comp-abc",
    "query": "iPhone 15 vs Galaxy S24",
    "product_names": ["Apple iPhone 15", "Samsung Galaxy S24"],
    "input_type": "text",
    "full_response": {
        "success": True,
        "products": [{"brand": "Apple", "name": "iPhone 15"}],
    },
    "created_at": "2026-03-18T10:00:00Z",
}


def _get_client_with_user(user=MOCK_USER):
    """Create test client with dependency override for auth."""
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    return client


def _cleanup_overrides():
    """Remove dependency overrides."""
    app.dependency_overrides.clear()


# ============================================
# POST /api/v1/share/{comparison_id}
# ============================================


def test_share_requires_auth():
    """POST /share/{id} without auth returns 401."""
    _cleanup_overrides()
    client = TestClient(app)
    resp = client.post("/api/v1/share/comp-abc")
    assert resp.status_code == 401


@patch("app.api.share_routes.create_share_token", new_callable=AsyncMock, return_value="abc12xyz")
def test_share_success(mock_create):
    """POST /share/{id} returns share token and URL."""
    client = _get_client_with_user()
    try:
        resp = client.post("/api/v1/share/comp-abc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["share_token"] == "abc12xyz"
        assert "abc12xyz" in data["share_url"]
    finally:
        _cleanup_overrides()


@patch("app.api.share_routes.create_share_token", new_callable=AsyncMock, side_effect=PermissionError("Not authorized"))
def test_share_forbidden(mock_create):
    """POST /share/{id} returns 403 if not owner."""
    client = _get_client_with_user()
    try:
        resp = client.post("/api/v1/share/comp-abc")
        assert resp.status_code == 403
    finally:
        _cleanup_overrides()


@patch("app.api.share_routes.create_share_token", new_callable=AsyncMock, return_value=None)
def test_share_not_found(mock_create):
    """POST /share/{id} returns 404 if comparison doesn't exist."""
    client = _get_client_with_user()
    try:
        resp = client.post("/api/v1/share/nonexistent")
        assert resp.status_code == 404
    finally:
        _cleanup_overrides()


# ============================================
# GET /api/v1/share/{token}
# ============================================


@patch("app.api.share_routes.get_shared_comparison", new_callable=AsyncMock, return_value=MOCK_SHARED)
def test_view_shared_success(mock_get):
    """GET /share/{token} returns comparison without auth."""
    _cleanup_overrides()
    client = TestClient(app)
    resp = client.get("/api/v1/share/abc12xyz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["comparison"]["query"] == "iPhone 15 vs Galaxy S24"
    # Personalization fields should be stripped
    assert "personalized" not in data["comparison"].get("full_response", {})
    assert "personalization_factors" not in data["comparison"].get("full_response", {})


@patch("app.api.share_routes.get_shared_comparison", new_callable=AsyncMock, return_value=None)
def test_view_shared_invalid_token(mock_get):
    """GET /share/{token} returns 404 for invalid token."""
    _cleanup_overrides()
    client = TestClient(app)
    resp = client.get("/api/v1/share/invalid_token")
    assert resp.status_code == 404


def test_view_shared_no_auth_needed():
    """GET /share/{token} doesn't require Authorization header."""
    _cleanup_overrides()
    client = TestClient(app)
    # Should not return 401 (may return 404 since token doesn't exist)
    resp = client.get("/api/v1/share/sometoken")
    assert resp.status_code != 401


@patch("app.api.share_routes.create_share_token", new_callable=AsyncMock, return_value="xyz789ab")
def test_share_url_contains_base_url(mock_create):
    """POST /share/{id} returns share_url with correct base URL."""
    client = _get_client_with_user()
    try:
        resp = client.post("/api/v1/share/comp-abc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["share_url"].startswith("https://web-production-58776.up.railway.app/api/v1/share/")
        assert data["share_url"].endswith("xyz789ab")
    finally:
        _cleanup_overrides()


# ============================================
# DB function tests
# ============================================


def test_get_shared_comparison_strips_personalization():
    """get_shared_comparison removes personalization keys from full_response."""
    mock_response = MagicMock()
    mock_response.data = {
        "id": "comp-abc",
        "query": "test",
        "product_names": [],
        "input_type": "text",
        "full_response": {
            "products": [],
            "personalized": True,
            "personalization_factors": ["price"],
            "personalization_prompt": "some prompt",
        },
        "created_at": "2026-01-01",
    }

    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import get_shared_comparison
        result = asyncio.get_event_loop().run_until_complete(get_shared_comparison("token123"))

    assert result is not None
    fr = result["full_response"]
    assert "personalized" not in fr
    assert "personalization_factors" not in fr
    assert "personalization_prompt" not in fr
    assert "products" in fr  # Non-personalization fields preserved


def test_create_share_token_ownership_check():
    """create_share_token raises PermissionError for wrong user."""
    mock_comparison = {
        "id": "comp-abc",
        "user_id": "user-123",
        "share_token": None,
    }

    with patch("app.services.database_service.get_comparison_by_id", new_callable=AsyncMock, return_value=mock_comparison):
        from app.services.database_service import create_share_token
        with pytest.raises(PermissionError):
            asyncio.get_event_loop().run_until_complete(
                create_share_token("comp-abc", "wrong-user")
            )


def test_create_share_token_returns_existing():
    """create_share_token returns existing token if already shared."""
    mock_comparison = {
        "id": "comp-abc",
        "user_id": "user-123",
        "share_token": "existing_tok",
    }

    with patch("app.services.database_service.get_comparison_by_id", new_callable=AsyncMock, return_value=mock_comparison):
        from app.services.database_service import create_share_token
        result = asyncio.get_event_loop().run_until_complete(
            create_share_token("comp-abc", "user-123")
        )
        assert result == "existing_tok"


def test_create_share_token_not_found():
    """create_share_token returns None if comparison doesn't exist."""
    with patch("app.services.database_service.get_comparison_by_id", new_callable=AsyncMock, return_value=None):
        from app.services.database_service import create_share_token
        result = asyncio.get_event_loop().run_until_complete(
            create_share_token("nonexistent", "user-123")
        )
        assert result is None
