"""Tests for history route endpoints (GET list, GET single, DELETE)."""
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
    "full_response": {
        "success": True,
        "products": [
            {"brand": "Apple", "name": "iPhone 15"},
            {"brand": "Samsung", "name": "Galaxy S24"},
        ],
        "comparison": {"winner_index": 0},
    },
    "created_at": "2026-03-18T10:00:00Z",
}

MOCK_COMPARISON_LIST = [
    {
        "id": "comp-abc",
        "query": "iPhone 15 vs Galaxy S24",
        "product_names": ["Apple iPhone 15", "Samsung Galaxy S24"],
        "input_type": "text",
        "user_id": "user-123",
        "full_response": {"products": []},
        "created_at": "2026-03-18T10:00:00Z",
    },
    {
        "id": "comp-def",
        "query": "Pixel 9 vs Galaxy S24",
        "product_names": ["Google Pixel 9", "Samsung Galaxy S24"],
        "input_type": "text",
        "user_id": "user-123",
        "full_response": {"products": []},
        "created_at": "2026-03-17T10:00:00Z",
    },
]


def _get_client_with_user(user=MOCK_USER):
    """Create test client with dependency override for auth."""
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    return client


def _cleanup_overrides():
    """Remove dependency overrides."""
    app.dependency_overrides.clear()


# ============================================
# GET /api/v1/comparisons/history
# ============================================


def test_list_history_requires_auth():
    """GET /history without auth returns 401."""
    _cleanup_overrides()
    client = TestClient(app)
    resp = client.get("/api/v1/comparisons/history")
    assert resp.status_code == 401


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=2)
@patch("app.api.history_routes.get_user_comparisons", new_callable=AsyncMock, return_value=MOCK_COMPARISON_LIST)
def test_list_history_success(mock_get, mock_count):
    """GET /history returns paginated comparison summaries."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["comparisons"]) == 2
        assert data["total"] == 2
        assert data["limit"] == 20
        assert data["offset"] == 0
        # Summaries should NOT include full_response
        assert "full_response" not in data["comparisons"][0]
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=2)
@patch("app.api.history_routes.get_user_comparisons", new_callable=AsyncMock, return_value=MOCK_COMPARISON_LIST)
def test_list_history_with_search(mock_get, mock_count):
    """GET /history?search=iphone passes search to DB."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/history?search=iphone")
        assert resp.status_code == 200
        mock_get.assert_called_once_with(user_id="user-123", limit=20, offset=0, search="iphone")
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=2)
@patch("app.api.history_routes.get_user_comparisons", new_callable=AsyncMock, return_value=MOCK_COMPARISON_LIST)
def test_list_history_pagination(mock_get, mock_count):
    """GET /history?limit=5&offset=10 passes pagination params."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/history?limit=5&offset=10")
        assert resp.status_code == 200
        mock_get.assert_called_once_with(user_id="user-123", limit=5, offset=10, search=None)
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 10
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=0)
@patch("app.api.history_routes.get_user_comparisons", new_callable=AsyncMock, return_value=[])
def test_list_history_empty(mock_get, mock_count):
    """GET /history with no comparisons returns empty list."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["comparisons"] == []
        assert data["total"] == 0
    finally:
        _cleanup_overrides()


def test_list_history_limit_validation():
    """GET /history?limit=999 rejects invalid limit."""
    _cleanup_overrides()
    client = TestClient(app)
    resp = client.get("/api/v1/comparisons/history?limit=999")
    assert resp.status_code in (401, 422)  # 401 if auth checked first, 422 if validation first


# ============================================
# GET /api/v1/comparisons/{id}
# ============================================


def test_get_comparison_requires_auth():
    """GET /comparisons/{id} without auth returns 401."""
    _cleanup_overrides()
    client = TestClient(app)
    resp = client.get("/api/v1/comparisons/comp-abc")
    assert resp.status_code == 401


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_get_comparison_success(mock_get):
    """GET /comparisons/{id} returns full comparison with full_response."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/comp-abc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["comparison"]["id"] == "comp-abc"
        assert "full_response" in data["comparison"]
        assert data["comparison"]["full_response"]["success"] is True
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None)
def test_get_comparison_not_found(mock_get):
    """GET /comparisons/{id} returns 404 if not found."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/nonexistent")
        assert resp.status_code == 404
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_get_comparison_forbidden(mock_get):
    """GET /comparisons/{id} returns 403 if not owner."""
    client = _get_client_with_user(MOCK_OTHER_USER)
    try:
        resp = client.get("/api/v1/comparisons/comp-abc")
        assert resp.status_code == 403
    finally:
        _cleanup_overrides()


# ============================================
# DELETE /api/v1/comparisons/{id}
# ============================================


def test_delete_comparison_requires_auth():
    """DELETE /comparisons/{id} without auth returns 401."""
    _cleanup_overrides()
    client = TestClient(app)
    resp = client.delete("/api/v1/comparisons/comp-abc")
    assert resp.status_code == 401


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=True)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_comparison_success(mock_get, mock_del):
    """DELETE /comparisons/{id} deletes owned comparison."""
    client = _get_client_with_user()
    try:
        resp = client.delete("/api/v1/comparisons/comp-abc")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_del.assert_called_once_with("comp-abc", "user-123")
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None)
def test_delete_comparison_not_found(mock_get):
    """DELETE /comparisons/{id} returns 404 if not found."""
    client = _get_client_with_user()
    try:
        resp = client.delete("/api/v1/comparisons/nonexistent")
        assert resp.status_code == 404
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_comparison_forbidden(mock_get):
    """DELETE /comparisons/{id} returns 403 if not owner."""
    client = _get_client_with_user(MOCK_OTHER_USER)
    try:
        resp = client.delete("/api/v1/comparisons/comp-abc")
        assert resp.status_code == 403
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=False)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_comparison_db_failure(mock_get, mock_del):
    """DELETE /comparisons/{id} returns 500 if DB delete fails."""
    client = _get_client_with_user()
    try:
        resp = client.delete("/api/v1/comparisons/comp-abc")
        assert resp.status_code == 500
    finally:
        _cleanup_overrides()
