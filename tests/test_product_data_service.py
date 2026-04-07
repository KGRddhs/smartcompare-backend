"""Tests for product_data_service — L2 DB cache for specs, prices, reviews."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from app.services.product_data_service import (
    get_cached_specs,
    save_specs,
    get_cached_price,
    save_price,
    get_cached_reviews,
    save_reviews,
    SPECS_DB_TTL,
    PRICE_DB_TTL,
    REVIEWS_DB_TTL,
)


def _mock_supabase():
    """Create a mock Supabase client with chainable methods."""
    client = MagicMock()
    # Make table().select().eq()... chainable
    client.table.return_value = client
    client.select.return_value = client
    client.eq.return_value = client
    client.single.return_value = client
    client.order.return_value = client
    client.limit.return_value = client
    client.upsert.return_value = client
    client.insert.return_value = client
    return client


def _fresh_timestamp():
    return datetime.now(timezone.utc).isoformat()


def _stale_timestamp(ttl: timedelta):
    return (datetime.now(timezone.utc) - ttl - timedelta(hours=1)).isoformat()


# ============================================
# Specs tests
# ============================================

@pytest.mark.asyncio
async def test_get_cached_specs_returns_none_when_empty():
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data=None)
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        result = await get_cached_specs("specs:abc123def456")
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_specs_returns_data_when_fresh():
    specs_data = {"display": "6.1 inch", "battery": "3274 mAh"}
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data={
        "specs": specs_data,
        "fetched_at": _fresh_timestamp(),
    })
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        result = await get_cached_specs("specs:abc123def456")
    assert result == specs_data


@pytest.mark.asyncio
async def test_get_cached_specs_returns_none_when_stale():
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data={
        "specs": {"display": "6.1 inch"},
        "fetched_at": _stale_timestamp(SPECS_DB_TTL),
    })
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        result = await get_cached_specs("specs:abc123def456")
    assert result is None


@pytest.mark.asyncio
async def test_save_specs_upserts():
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data={})
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        await save_specs("specs:abc123", "Apple", "iPhone 15", None, "electronics", {"display": "6.1"})
    client.table.assert_called_with("product_specs")
    client.upsert.assert_called_once()
    upsert_data = client.upsert.call_args[0][0]
    assert upsert_data["product_key"] == "specs:abc123"
    assert upsert_data["brand"] == "Apple"
    assert upsert_data["specs"] == {"display": "6.1"}
    # Verify on_conflict for upsert behavior
    assert client.upsert.call_args[1]["on_conflict"] == "product_key"


# ============================================
# Price tests
# ============================================

@pytest.mark.asyncio
async def test_get_cached_price_returns_none_when_empty():
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data=[])
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        result = await get_cached_price("price:abc123def4", "bahrain")
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_price_returns_latest_when_fresh():
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data=[{
        "amount": "299.00",
        "currency": "BHD",
        "retailer": "amazon.sa",
        "url": "https://amazon.sa/product",
        "source_method": "local_bhd",
        "estimated": False,
        "fetched_at": _fresh_timestamp(),
    }])
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        result = await get_cached_price("price:abc123def4", "bahrain")
    assert result is not None
    assert result["amount"] == 299.0
    assert result["currency"] == "BHD"
    assert result["retailer"] == "amazon.sa"
    assert result["estimated"] is False


@pytest.mark.asyncio
async def test_get_cached_price_returns_none_when_stale():
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data=[{
        "amount": "299.00",
        "currency": "BHD",
        "retailer": "amazon.sa",
        "url": None,
        "source_method": "local_bhd",
        "estimated": False,
        "fetched_at": _stale_timestamp(PRICE_DB_TTL),
    }])
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        result = await get_cached_price("price:abc123def4", "bahrain")
    assert result is None


@pytest.mark.asyncio
async def test_save_price_appends_history():
    """Multiple saves should use insert (not upsert), creating multiple rows."""
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data={})
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        await save_price("price:abc123", "Apple", "iPhone 15", None, "bahrain", {
            "amount": 299, "currency": "BHD", "retailer": "amazon.sa",
        })
        await save_price("price:abc123", "Apple", "iPhone 15", None, "bahrain", {
            "amount": 289, "currency": "BHD", "retailer": "noon.com",
        })
    # Both calls should use insert (not upsert)
    assert client.insert.call_count == 2


# ============================================
# Reviews tests
# ============================================

@pytest.mark.asyncio
async def test_get_cached_reviews_returns_none_when_empty():
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data=None)
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        result = await get_cached_reviews("reviews:abc123def4")
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_reviews_returns_data_when_fresh():
    reviews_data = {"review_summary": {"overall": "Great phone"}, "highlights": []}
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data={
        "reviews": reviews_data,
        "fetched_at": _fresh_timestamp(),
    })
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        result = await get_cached_reviews("reviews:abc123def4")
    assert result == reviews_data


@pytest.mark.asyncio
async def test_get_cached_reviews_returns_none_when_stale():
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data={
        "reviews": {"review_summary": {}},
        "fetched_at": _stale_timestamp(REVIEWS_DB_TTL),
    })
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        result = await get_cached_reviews("reviews:abc123def4")
    assert result is None


@pytest.mark.asyncio
async def test_save_reviews_upserts():
    client = _mock_supabase()
    client.execute.return_value = MagicMock(data={})
    with patch("app.services.product_data_service.get_admin_supabase_client", return_value=client):
        await save_reviews("reviews:abc123", "Apple", "iPhone 15", None, {"overall": "Good"})
    client.table.assert_called_with("product_reviews")
    client.upsert.assert_called_once()
    assert client.upsert.call_args[1]["on_conflict"] == "product_key"


# ============================================
# Error handling
# ============================================

@pytest.mark.asyncio
async def test_all_functions_handle_db_errors_gracefully():
    """All functions should catch exceptions and return None / not raise."""
    with patch("app.services.product_data_service.get_admin_supabase_client", side_effect=Exception("DB down")):
        assert await get_cached_specs("key") is None
        assert await get_cached_price("key", "bahrain") is None
        assert await get_cached_reviews("key") is None
        # save functions should not raise
        await save_specs("key", "B", "N", None, None, {})
        await save_price("key", "B", "N", None, "bahrain", {})
        await save_reviews("key", "B", "N", None, {})


# ============================================
# Cache key consistency
# ============================================

def test_product_key_matches_redis_cache_key():
    """Verify generate_cache_key produces consistent keys for specs/prices/reviews."""
    from app.services.extraction_service import (
        get_specs_cache_key,
        get_price_cache_key,
        get_reviews_cache_key,
    )
    specs_key = get_specs_cache_key("Apple", "iPhone 15", "Pro Max")
    price_key = get_price_cache_key("Apple", "iPhone 15", "Pro Max", "bahrain")
    reviews_key = get_reviews_cache_key("Apple", "iPhone 15", "Pro Max")

    # Keys should be deterministic
    assert specs_key == get_specs_cache_key("Apple", "iPhone 15", "Pro Max")
    assert price_key == get_price_cache_key("Apple", "iPhone 15", "Pro Max", "bahrain")
    assert reviews_key == get_reviews_cache_key("Apple", "iPhone 15", "Pro Max")

    # Keys should have the right prefix
    assert specs_key.startswith("specs:")
    assert price_key.startswith("price:")
    assert reviews_key.startswith("reviews:")

    # Keys should be different for different data types
    assert specs_key != price_key
    assert specs_key != reviews_key
