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
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
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
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
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
        # access_token is now threaded through from Authorization header
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["user_id"] == "user-123"
        assert call_kwargs["limit"] == 20
        assert call_kwargs["offset"] == 0
        assert call_kwargs["search"] == "iphone"
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
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["user_id"] == "user-123"
        assert call_kwargs["limit"] == 5
        assert call_kwargs["offset"] == 10
        assert call_kwargs["search"] is None
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
    resp = client.get("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    assert resp.status_code == 401


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_get_comparison_success(mock_get):
    """GET /comparisons/{id} returns full comparison with full_response."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["comparison"]["id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert "full_response" in data["comparison"]
        assert data["comparison"]["full_response"]["success"] is True
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None)
def test_get_comparison_not_found(mock_get):
    """GET /comparisons/{id} returns 404 if not found."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_get_comparison_forbidden(mock_get):
    """GET /comparisons/{id} returns 404 (not 403) if not owner — merged to prevent enumeration."""
    client = _get_client_with_user(MOCK_OTHER_USER)
    try:
        resp = client.get("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert resp.status_code == 404
    finally:
        _cleanup_overrides()


# ============================================
# DELETE /api/v1/comparisons/{id}
# ============================================


def test_delete_comparison_requires_auth():
    """DELETE /comparisons/{id} without auth returns 401."""
    _cleanup_overrides()
    client = TestClient(app)
    resp = client.delete("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    assert resp.status_code == 401


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=True)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_comparison_success(mock_get, mock_del):
    """DELETE /comparisons/{id} deletes owned comparison."""
    client = _get_client_with_user()
    try:
        resp = client.delete("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        call_args = mock_del.call_args
        assert call_args[0][0] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert call_args[0][1] == "user-123"
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None)
def test_delete_comparison_not_found(mock_get):
    """DELETE /comparisons/{id} returns 404 if not found."""
    client = _get_client_with_user()
    try:
        resp = client.delete("/api/v1/comparisons/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_comparison_forbidden(mock_get):
    """DELETE /comparisons/{id} returns 404 (not 403) if not owner — merged to prevent enumeration."""
    client = _get_client_with_user(MOCK_OTHER_USER)
    try:
        resp = client.delete("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert resp.status_code == 404
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=False)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_comparison_db_failure(mock_get, mock_del):
    """DELETE /comparisons/{id} returns 500 if DB delete fails."""
    client = _get_client_with_user()
    try:
        resp = client.delete("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert resp.status_code == 500
    finally:
        _cleanup_overrides()


# ---------- Bundle A §5.2 — DELETE must reach v1 rows (Task 1.9) ----------


MOCK_V1_COMPARISON = {
    **MOCK_COMPARISON,
    "schema_version": 1,
}


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=True)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_V1_COMPARISON)
def test_delete_comparison_works_for_v1_rows(mock_get, mock_del):
    """DELETE on a v1 row must succeed — users still need to clean up stale history."""
    client = _get_client_with_user()
    try:
        resp = client.delete("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # The route should request the row WITH include_legacy=True.
        called_kwargs = mock_get.call_args.kwargs
        assert called_kwargs.get("include_legacy") is True
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=None)
def test_get_comparison_returns_404_for_v1_row(mock_get):
    """GET on a v1 row returns 404 (database layer hides it; route sees None)."""
    client = _get_client_with_user()
    try:
        resp = client.get(
            "/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )
        assert resp.status_code == 404
        # GET should NOT use include_legacy (or pass False)
        called_kwargs = mock_get.call_args.kwargs
        assert called_kwargs.get("include_legacy", False) is False
    finally:
        _cleanup_overrides()


# ---------- Task 2.6.B.4 — winner_index on list response (frontend per-row VS card) ----------


MOCK_LIST_WITH_WINNER_INDEX_SHAPES = [
    # Row 1 — winner_index lives at full_response.metadata.winner_index
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "query": "iPhone 15 vs Galaxy S24",
        "product_names": ["Apple iPhone 15", "Samsung Galaxy S24"],
        "input_type": "text",
        "user_id": "user-123",
        "full_response": {
            "metadata": {"winner_index": 1},
        },
        "created_at": "2026-03-18T10:00:00Z",
    },
    # Row 2 — winner_index lives at full_response.comparison.winner_index
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "query": "Pixel 9 vs Galaxy S24",
        "product_names": ["Google Pixel 9", "Samsung Galaxy S24"],
        "input_type": "text",
        "user_id": "user-123",
        "full_response": {
            "comparison": {"winner_index": 0},
        },
        "created_at": "2026-03-17T10:00:00Z",
    },
    # Row 3 — full_response present but neither path has winner_index → null
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "query": "Coffee A vs Coffee B",
        "product_names": ["Coffee A", "Coffee B"],
        "input_type": "text",
        "user_id": "user-123",
        "full_response": {"products": []},
        "created_at": "2026-03-16T10:00:00Z",
    },
    # Row 4 — full_response missing entirely → null
    {
        "id": "44444444-4444-4444-4444-444444444444",
        "query": "Pen X vs Pen Y",
        "product_names": ["Pen X", "Pen Y"],
        "input_type": "text",
        "user_id": "user-123",
        "full_response": None,
        "created_at": "2026-03-15T10:00:00Z",
    },
]


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=4)
@patch(
    "app.api.history_routes.get_user_comparisons",
    new_callable=AsyncMock,
    return_value=MOCK_LIST_WITH_WINNER_INDEX_SHAPES,
)
def test_list_history_winner_index_from_metadata(mock_get, mock_count):
    """Row with full_response.metadata.winner_index exposes that value."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/history")
        assert resp.status_code == 200
        rows = resp.json()["comparisons"]
        assert rows[0]["id"] == "11111111-1111-1111-1111-111111111111"
        assert rows[0]["winner_index"] == 1
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=4)
@patch(
    "app.api.history_routes.get_user_comparisons",
    new_callable=AsyncMock,
    return_value=MOCK_LIST_WITH_WINNER_INDEX_SHAPES,
)
def test_list_history_winner_index_fallback_to_comparison(mock_get, mock_count):
    """Row missing metadata.winner_index falls back to full_response.comparison.winner_index."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/history")
        assert resp.status_code == 200
        rows = resp.json()["comparisons"]
        assert rows[1]["id"] == "22222222-2222-2222-2222-222222222222"
        assert rows[1]["winner_index"] == 0
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=4)
@patch(
    "app.api.history_routes.get_user_comparisons",
    new_callable=AsyncMock,
    return_value=MOCK_LIST_WITH_WINNER_INDEX_SHAPES,
)
def test_list_history_winner_index_null_when_neither_present(mock_get, mock_count):
    """Row with full_response present but no winner_index in either path → null."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/history")
        assert resp.status_code == 200
        rows = resp.json()["comparisons"]
        assert rows[2]["id"] == "33333333-3333-3333-3333-333333333333"
        assert rows[2]["winner_index"] is None
    finally:
        _cleanup_overrides()


@patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=4)
@patch(
    "app.api.history_routes.get_user_comparisons",
    new_callable=AsyncMock,
    return_value=MOCK_LIST_WITH_WINNER_INDEX_SHAPES,
)
def test_list_history_winner_index_null_when_full_response_missing(mock_get, mock_count):
    """Row with full_response=None → winner_index null, never raises."""
    client = _get_client_with_user()
    try:
        resp = client.get("/api/v1/comparisons/history")
        assert resp.status_code == 200
        rows = resp.json()["comparisons"]
        assert rows[3]["id"] == "44444444-4444-4444-4444-444444444444"
        assert rows[3]["winner_index"] is None
    finally:
        _cleanup_overrides()


# ============================================
# Wave 2 — image_url extension on /history list
# Locked shape with L2 (b565a38): top-level per-row winner_image_url +
# runner_up_image_url (string|null) derived server-side using winner_index.
# Same _safe_image_url contract as /home/smart-pick + /profile/recent-decisions.
# ============================================


def _history_row_with_image(
    *, row_id: str, winner_idx, p0_image, p1_image, full_response_extra=None,
):
    """Build a comparisons history row with image_url on each product slot.

    winner_idx is placed at full_response.metadata.winner_index to match the
    canonical write path (build_comparison_response). Pass full_response_extra
    to override the wrapper for edge-case tests (e.g., None full_response,
    missing products array).
    """
    full = {
        "metadata": {"winner_index": winner_idx} if winner_idx is not None else {},
        "products": [
            {"brand": "Apple", "name": "iPhone 15", "image_url": p0_image},
            {"brand": "Samsung", "name": "Galaxy S24", "image_url": p1_image},
        ],
    }
    if full_response_extra is not None:
        full = full_response_extra
    return {
        "id": row_id,
        "query": "iPhone 15 vs Galaxy S24",
        "product_names": ["Apple iPhone 15", "Samsung Galaxy S24"],
        "input_type": "text",
        "user_id": "user-123",
        "full_response": full,
        "created_at": "2026-05-23T10:00:00Z",
    }


def test_list_history_image_urls_present_when_both_products_have_image_url():
    rows = [_history_row_with_image(
        row_id="r1", winner_idx=0,
        p0_image="https://cdn.apple.com/i15.jpg",
        p1_image="https://cdn.samsung.com/s24.jpg",
    )]
    with patch("app.api.history_routes.get_user_comparison_count",
               new_callable=AsyncMock, return_value=1), \
         patch("app.api.history_routes.get_user_comparisons",
               new_callable=AsyncMock, return_value=rows):
        client = _get_client_with_user()
        try:
            resp = client.get("/api/v1/comparisons/history")
            assert resp.status_code == 200
            row = resp.json()["comparisons"][0]
            assert row["winner_image_url"] == "https://cdn.apple.com/i15.jpg"
            assert row["runner_up_image_url"] == "https://cdn.samsung.com/s24.jpg"
        finally:
            _cleanup_overrides()


def test_list_history_image_urls_respect_winner_index_swap():
    """When winner_index=1, winner_image_url must come from products[1]."""
    rows = [_history_row_with_image(
        row_id="r2", winner_idx=1,
        p0_image="https://cdn.apple.com/i15.jpg",
        p1_image="https://cdn.samsung.com/s24.jpg",
    )]
    with patch("app.api.history_routes.get_user_comparison_count",
               new_callable=AsyncMock, return_value=1), \
         patch("app.api.history_routes.get_user_comparisons",
               new_callable=AsyncMock, return_value=rows):
        client = _get_client_with_user()
        try:
            resp = client.get("/api/v1/comparisons/history")
            row = resp.json()["comparisons"][0]
            # winner_idx=1 → winner is Samsung, runner_up is Apple
            assert row["winner_image_url"] == "https://cdn.samsung.com/s24.jpg"
            assert row["runner_up_image_url"] == "https://cdn.apple.com/i15.jpg"
        finally:
            _cleanup_overrides()


def test_list_history_image_urls_null_when_absent():
    """Pre-A3-deploy rows have no image_url field → response ships None."""
    rows = [_history_row_with_image(
        row_id="r3", winner_idx=0, p0_image=None, p1_image=None,
    )]
    with patch("app.api.history_routes.get_user_comparison_count",
               new_callable=AsyncMock, return_value=1), \
         patch("app.api.history_routes.get_user_comparisons",
               new_callable=AsyncMock, return_value=rows):
        client = _get_client_with_user()
        try:
            resp = client.get("/api/v1/comparisons/history")
            row = resp.json()["comparisons"][0]
            assert row["winner_image_url"] is None
            assert row["runner_up_image_url"] is None
        finally:
            _cleanup_overrides()


def test_list_history_image_urls_reject_non_http_scheme():
    """Defense vs malformed legacy rows holding garbage strings / dangerous URIs."""
    rows = [_history_row_with_image(
        row_id="r4", winner_idx=0,
        p0_image="javascript:alert(1)",
        p1_image="data:image/png;base64,abc",
    )]
    with patch("app.api.history_routes.get_user_comparison_count",
               new_callable=AsyncMock, return_value=1), \
         patch("app.api.history_routes.get_user_comparisons",
               new_callable=AsyncMock, return_value=rows):
        client = _get_client_with_user()
        try:
            resp = client.get("/api/v1/comparisons/history")
            row = resp.json()["comparisons"][0]
            assert row["winner_image_url"] is None
            assert row["runner_up_image_url"] is None
        finally:
            _cleanup_overrides()


def test_list_history_image_urls_null_when_winner_index_missing():
    """Without winner_index, we can't derive winner vs runner_up — both null.
    Mirrors the existing winner_index null behavior (rows[2]/[3] in MOCK_LIST_WITH_WINNER_INDEX_SHAPES)."""
    rows = [_history_row_with_image(
        row_id="r5", winner_idx=None,
        p0_image="https://cdn.apple.com/i15.jpg",
        p1_image="https://cdn.samsung.com/s24.jpg",
        full_response_extra={
            "products": [
                {"brand": "Apple", "name": "iPhone 15", "image_url": "https://cdn.apple.com/i15.jpg"},
                {"brand": "Samsung", "name": "Galaxy S24", "image_url": "https://cdn.samsung.com/s24.jpg"},
            ],
            # No metadata.winner_index AND no comparison.winner_index
        },
    )]
    with patch("app.api.history_routes.get_user_comparison_count",
               new_callable=AsyncMock, return_value=1), \
         patch("app.api.history_routes.get_user_comparisons",
               new_callable=AsyncMock, return_value=rows):
        client = _get_client_with_user()
        try:
            resp = client.get("/api/v1/comparisons/history")
            row = resp.json()["comparisons"][0]
            assert row["winner_index"] is None
            assert row["winner_image_url"] is None
            assert row["runner_up_image_url"] is None
        finally:
            _cleanup_overrides()


def test_list_history_image_urls_null_when_full_response_missing():
    """Row with full_response=None must not raise + both image_url null."""
    rows = [_history_row_with_image(
        row_id="r6", winner_idx=0, p0_image=None, p1_image=None,
        full_response_extra=None,  # use default
    )]
    # Override to None
    rows[0]["full_response"] = None
    with patch("app.api.history_routes.get_user_comparison_count",
               new_callable=AsyncMock, return_value=1), \
         patch("app.api.history_routes.get_user_comparisons",
               new_callable=AsyncMock, return_value=rows):
        client = _get_client_with_user()
        try:
            resp = client.get("/api/v1/comparisons/history")
            assert resp.status_code == 200
            row = resp.json()["comparisons"][0]
            assert row["winner_image_url"] is None
            assert row["runner_up_image_url"] is None
        finally:
            _cleanup_overrides()


# ============================================
# Wave 2 (c) — SmartPick stale-after-delete fix via cache invalidation
# Device walk image #13: "Today's Tailored Pick" tile shows iPhone 14
# (deleted from History) instead of newer iPhone 17.
#
# Root cause: /home/smart-pick + /profile/recent-decisions each cache for
# 5min per-user in Redis (home_routes.py:486 + profile_routes.py:133).
# Supabase .delete() at database_service.py:288 is a HARD delete — the row
# IS gone — but the cached pick/recent-list is NOT busted, so stale rows
# render until the 5min TTL expires.
#
# Fix: DELETE /comparisons/{id} must invalidate both cache keys after a
# successful delete. Tests pin both `home:smart_pick:{user_id}` and
# `profile_recent:{user_id}` bust patterns.
# ============================================


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=True)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_busts_home_smart_pick_cache(mock_get, mock_del):
    """DELETE /comparisons/{id} must invalidate home:smart_pick:{user_id}."""
    with patch("app.api.history_routes.delete_cached") as mock_delete_cached:
        client = _get_client_with_user()
        try:
            resp = client.delete("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
            assert resp.status_code == 200
            # delete_cached must have been called with the home/smart_pick key
            called_keys = [c.args[0] for c in mock_delete_cached.call_args_list]
            assert "home:smart_pick:user-123" in called_keys, (
                f"home:smart_pick cache not busted; delete_cached called with: {called_keys}"
            )
        finally:
            _cleanup_overrides()


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=True)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_busts_profile_recent_cache(mock_get, mock_del):
    """DELETE /comparisons/{id} must invalidate profile_recent:{user_id}."""
    with patch("app.api.history_routes.delete_cached") as mock_delete_cached:
        client = _get_client_with_user()
        try:
            resp = client.delete("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
            assert resp.status_code == 200
            called_keys = [c.args[0] for c in mock_delete_cached.call_args_list]
            assert "profile_recent:user-123" in called_keys, (
                f"profile_recent cache not busted; delete_cached called with: {called_keys}"
            )
        finally:
            _cleanup_overrides()


@patch("app.api.history_routes.delete_comparison", new_callable=AsyncMock, return_value=False)
@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_failure_does_not_bust_cache(mock_get, mock_del):
    """When the DB delete fails, the cache MUST NOT be busted — otherwise
    we'd nuke a valid cache for no reason. Pin the invariant: cache bust
    runs ONLY after delete_comparison returns True."""
    with patch("app.api.history_routes.delete_cached") as mock_delete_cached:
        client = _get_client_with_user()
        try:
            resp = client.delete("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
            assert resp.status_code == 500
            assert mock_delete_cached.call_count == 0
        finally:
            _cleanup_overrides()


@patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock, return_value=MOCK_COMPARISON)
def test_delete_forbidden_does_not_bust_cache(mock_get):
    """When the user doesn't own the row (404), no cache invalidation
    fires — wrong user's cache must not be touched."""
    with patch("app.api.history_routes.delete_cached") as mock_delete_cached:
        client = _get_client_with_user(MOCK_OTHER_USER)
        try:
            resp = client.delete("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
            assert resp.status_code == 404
            assert mock_delete_cached.call_count == 0
        finally:
            _cleanup_overrides()
