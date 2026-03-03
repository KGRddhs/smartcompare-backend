"""Tests for analytics service and admin endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


# ── Analytics service tests ──

def _mock_search_logs(records):
    """Create mock Supabase response for search_logs queries."""
    mock_response = MagicMock()
    mock_response.data = records
    return mock_response


def _make_log_record(
    query="iPhone 15 vs Galaxy S24",
    input_type="text",
    success=True,
    cost=0.01,
    duration_ms=5000,
    created_at=None,
    error_message=None,
):
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    record = {
        "query": query,
        "input_type": input_type,
        "success": success,
        "cost": cost,
        "duration_ms": duration_ms,
        "created_at": created_at,
        "products_found": ["Apple iPhone 15", "Samsung Galaxy S24"],
    }
    if error_message:
        record["error_message"] = error_message
    return record


@pytest.mark.asyncio
async def test_get_daily_stats_returns_structure():
    """get_daily_stats returns dict with expected keys."""
    mock_client = MagicMock()
    records = [_make_log_record(), _make_log_record(success=False, error_message="timeout")]
    mock_chain = MagicMock()
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_daily_stats
        result = await get_daily_stats(days=7)

    assert "total_comparisons" in result
    assert "success_count" in result
    assert "error_count" in result
    assert "daily_breakdown" in result


@pytest.mark.asyncio
async def test_get_popular_queries_returns_ranked_list():
    """get_popular_queries returns queries ranked by frequency."""
    mock_client = MagicMock()
    records = [
        _make_log_record(query="iPhone vs Galaxy"),
        _make_log_record(query="iPhone vs Galaxy"),
        _make_log_record(query="MacBook vs Dell"),
    ]
    mock_chain = MagicMock()
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value = mock_chain

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_popular_queries
        result = await get_popular_queries(limit=10)

    assert isinstance(result, list)
    assert len(result) > 0
    # Most popular first
    assert result[0]["count"] >= result[-1]["count"]


@pytest.mark.asyncio
async def test_get_cost_trends_returns_aggregation():
    """get_cost_trends returns cost aggregation data."""
    mock_client = MagicMock()
    records = [
        _make_log_record(cost=0.01),
        _make_log_record(cost=0.015),
        _make_log_record(cost=0.008),
    ]
    mock_chain = MagicMock()
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_cost_trends
        result = await get_cost_trends(days=7)

    assert "total_cost" in result
    assert "avg_cost_per_comparison" in result
    assert result["total_cost"] == pytest.approx(0.033, rel=0.01)


@pytest.mark.asyncio
async def test_get_error_stats_returns_error_breakdown():
    """get_error_stats returns error rate and breakdown."""
    mock_client = MagicMock()
    records = [
        _make_log_record(success=True),
        _make_log_record(success=True),
        _make_log_record(success=False, error_message="Comparison failed"),
    ]
    mock_chain = MagicMock()
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_error_stats
        result = await get_error_stats(days=7)

    assert "total_requests" in result
    assert "error_rate" in result
    assert result["error_rate"] == pytest.approx(0.333, rel=0.05)


@pytest.mark.asyncio
async def test_daily_stats_handles_empty_data():
    """get_daily_stats returns zeros when no search logs exist."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs([])
    mock_client.table.return_value.select.return_value.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs([])

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_daily_stats
        result = await get_daily_stats(days=7)

    assert result["total_comparisons"] == 0
    assert result["success_count"] == 0


@pytest.mark.asyncio
async def test_get_product_stats_returns_structure():
    """get_product_stats returns product category breakdown."""
    mock_client = MagicMock()
    records = [
        {"canonical_name": "iPhone 15", "brand": "Apple", "category": "electronics", "updated_at": "2026-03-01"},
        {"canonical_name": "Galaxy S24", "brand": "Samsung", "category": "electronics", "updated_at": "2026-03-01"},
        {"canonical_name": "Vitamin D3", "brand": "NOW", "category": "supplements", "updated_at": "2026-03-02"},
    ]
    mock_chain = MagicMock()
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value = mock_chain

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_product_stats
        result = await get_product_stats(limit=20)

    assert "total_products" in result
    assert result["total_products"] == 3
    assert "category_breakdown" in result
    assert result["category_breakdown"]["electronics"] == 2
    assert "top_brands" in result


@pytest.mark.asyncio
async def test_get_popular_queries_handles_empty_data():
    """get_popular_queries returns empty list when no logs exist."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.execute.return_value = _mock_search_logs([])
    mock_client.table.return_value.select.return_value = mock_chain

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_popular_queries
        result = await get_popular_queries(limit=10)

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_cost_trends_handles_zero_costs():
    """get_cost_trends handles records with zero or None cost."""
    mock_client = MagicMock()
    records = [
        _make_log_record(cost=0),
        _make_log_record(cost=None),
        _make_log_record(cost=0.01),
    ]
    mock_chain = MagicMock()
    mock_chain.gte.return_value = mock_chain
    mock_chain.execute.return_value = _mock_search_logs(records)
    mock_client.table.return_value.select.return_value.gte.return_value = mock_chain

    with patch("app.services.analytics_service.get_supabase_client", return_value=mock_client):
        from app.services.analytics_service import get_cost_trends
        result = await get_cost_trends(days=7)

    assert result["total_cost"] == pytest.approx(0.01, rel=0.01)
    assert result["comparison_count"] == 3


@pytest.mark.asyncio
async def test_analytics_handles_supabase_exception():
    """Analytics functions return safe defaults when Supabase raises."""
    with patch("app.services.analytics_service.get_supabase_client", side_effect=Exception("DB down")):
        from app.services.analytics_service import get_daily_stats, get_popular_queries, get_cost_trends, get_error_stats, get_product_stats

        daily = await get_daily_stats(days=7)
        assert daily["total_comparisons"] == 0

        popular = await get_popular_queries(limit=10)
        assert popular == []

        costs = await get_cost_trends(days=7)
        assert costs["total_cost"] == 0

        errors = await get_error_stats(days=7)
        assert errors["total_requests"] == 0

        products = await get_product_stats(limit=20)
        assert products["total_products"] == 0


# ── Admin endpoint tests ──

from starlette.testclient import TestClient


def _make_admin_app():
    """Create FastAPI app with admin routes for testing."""
    from fastapi import FastAPI
    from app.api.admin_routes import router
    import os
    os.environ["ADMIN_API_KEY"] = "test-admin-key-123"

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/admin")
    return test_app


def test_admin_valid_key_succeeds():
    """Valid admin key returns 200."""
    app = _make_admin_app()
    client = TestClient(app)
    with patch("app.api.admin_routes.get_daily_stats", return_value={"total_comparisons": 0}):
        response = client.get(
            "/api/v1/admin/stats/daily",
            headers={"X-Admin-Key": "test-admin-key-123"},
        )
    assert response.status_code == 200


def test_admin_invalid_key_returns_403():
    """Invalid admin key returns 403."""
    app = _make_admin_app()
    client = TestClient(app)
    response = client.get(
        "/api/v1/admin/stats/daily",
        headers={"X-Admin-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_admin_missing_key_returns_422():
    """Missing X-Admin-Key header returns 422."""
    app = _make_admin_app()
    client = TestClient(app)
    response = client.get("/api/v1/admin/stats/daily")
    assert response.status_code == 422


def test_admin_empty_env_key_returns_403():
    """Empty ADMIN_API_KEY env var rejects all requests."""
    from fastapi import FastAPI
    from app.api.admin_routes import router
    import os
    os.environ["ADMIN_API_KEY"] = ""

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/admin")
    client = TestClient(test_app)
    response = client.get(
        "/api/v1/admin/stats/daily",
        headers={"X-Admin-Key": "anything"},
    )
    assert response.status_code == 403


def test_admin_popular_queries_endpoint():
    """GET /stats/popular returns data with valid key."""
    app = _make_admin_app()
    client = TestClient(app)
    with patch("app.api.admin_routes.get_popular_queries", return_value=[{"query": "test", "count": 1}]):
        response = client.get(
            "/api/v1/admin/stats/popular",
            headers={"X-Admin-Key": "test-admin-key-123"},
        )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_admin_cost_trends_endpoint():
    """GET /stats/costs returns data with valid key."""
    app = _make_admin_app()
    client = TestClient(app)
    with patch("app.api.admin_routes.get_cost_trends", return_value={"total_cost": 0.5}):
        response = client.get(
            "/api/v1/admin/stats/costs",
            headers={"X-Admin-Key": "test-admin-key-123"},
        )
    assert response.status_code == 200


def test_admin_error_stats_endpoint():
    """GET /stats/errors returns data with valid key."""
    app = _make_admin_app()
    client = TestClient(app)
    with patch("app.api.admin_routes.get_error_stats", return_value={"error_rate": 0.0}):
        response = client.get(
            "/api/v1/admin/stats/errors",
            headers={"X-Admin-Key": "test-admin-key-123"},
        )
    assert response.status_code == 200


def test_admin_product_stats_endpoint():
    """GET /stats/products returns data with valid key."""
    app = _make_admin_app()
    client = TestClient(app)
    with patch("app.api.admin_routes.get_product_stats", return_value={"total_products": 0}):
        response = client.get(
            "/api/v1/admin/stats/products",
            headers={"X-Admin-Key": "test-admin-key-123"},
        )
    assert response.status_code == 200


def test_admin_daily_stats_with_days_param():
    """GET /stats/daily respects days query parameter."""
    app = _make_admin_app()
    client = TestClient(app)
    with patch("app.api.admin_routes.get_daily_stats", return_value={"total_comparisons": 0}) as mock_fn:
        response = client.get(
            "/api/v1/admin/stats/daily?days=7",
            headers={"X-Admin-Key": "test-admin-key-123"},
        )
    assert response.status_code == 200
    mock_fn.assert_called_once_with(7)


def test_admin_daily_stats_invalid_days_rejected():
    """GET /stats/daily rejects days < 1 or > 365."""
    app = _make_admin_app()
    client = TestClient(app)
    response = client.get(
        "/api/v1/admin/stats/daily?days=0",
        headers={"X-Admin-Key": "test-admin-key-123"},
    )
    assert response.status_code == 422

    response = client.get(
        "/api/v1/admin/stats/daily?days=999",
        headers={"X-Admin-Key": "test-admin-key-123"},
    )
    assert response.status_code == 422
