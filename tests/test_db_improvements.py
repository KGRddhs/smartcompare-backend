"""Tests for database improvements -- log_search, upsert_product."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_log_search_success():
    """log_search writes correct fields."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import log_search
        await log_search(
            query="iphone vs samsung",
            input_type="text",
            user_id="user-123",
            products_found=["Apple iPhone 15", "Samsung Galaxy S24"],
            success=True,
            cost=0.01,
            duration_ms=5000,
        )

    mock_client.table.assert_called_with("search_logs")
    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["query"] == "iphone vs samsung"
    assert insert_arg["user_id"] == "user-123"
    assert insert_arg["products_found"] == ["Apple iPhone 15", "Samsung Galaxy S24"]
    assert insert_arg["success"] is True
    assert insert_arg["cost"] == 0.01
    assert insert_arg["duration_ms"] == 5000


@pytest.mark.asyncio
async def test_log_search_no_user():
    """log_search omits user_id when None."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import log_search
        await log_search(query="test", success=True)

    insert_arg = mock_table.insert.call_args[0][0]
    assert "user_id" not in insert_arg


@pytest.mark.asyncio
async def test_log_search_with_error():
    """log_search includes error_message when provided."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import log_search
        await log_search(
            query="bad query",
            success=False,
            error_message="Could not parse products",
        )

    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["success"] is False
    assert insert_arg["error_message"] == "Could not parse products"


@pytest.mark.asyncio
async def test_log_search_swallows_errors():
    """log_search never raises -- fire-and-forget."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB unreachable")

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import log_search
        # Should not raise
        await log_search(query="test", success=True)


@pytest.mark.asyncio
async def test_upsert_product_new():
    """upsert_product creates new product and returns ID."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "prod-123"}]

    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_product
        result = await upsert_product(
            canonical_name="Apple iPhone 15",
            brand="Apple",
            category="electronics",
        )

    assert result == "prod-123"
    upsert_arg = mock_table.upsert.call_args[0][0]
    assert upsert_arg["canonical_name"] == "Apple iPhone 15"
    assert upsert_arg["brand"] == "Apple"
    assert upsert_arg["category"] == "electronics"


@pytest.mark.asyncio
async def test_upsert_product_uses_conflict():
    """upsert_product uses on_conflict=canonical_name."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "prod-456"}]

    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_product
        await upsert_product(canonical_name="Test Product")

    _, kwargs = mock_table.upsert.call_args
    assert kwargs["on_conflict"] == "canonical_name"


@pytest.mark.asyncio
async def test_upsert_product_handles_error():
    """upsert_product returns None on error."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB error")

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_product
        result = await upsert_product(canonical_name="Test")

    assert result is None


@pytest.mark.asyncio
async def test_upsert_products_from_comparison():
    """upsert_products_from_comparison processes all products."""
    mock_response = MagicMock()
    call_count = [0]

    def mock_upsert(*args, **kwargs):
        call_count[0] += 1
        mock = MagicMock()
        mock.execute.return_value = MagicMock(data=[{"id": f"prod-{call_count[0]}"}])
        return mock

    mock_table = MagicMock()
    mock_table.upsert = mock_upsert

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    full_response = {
        "products": [
            {"brand": "Apple", "name": "iPhone 15", "category": "electronics"},
            {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics"},
        ]
    }

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_products_from_comparison
        ids = await upsert_products_from_comparison(full_response)

    assert len(ids) == 2


@pytest.mark.asyncio
async def test_upsert_products_skips_empty_names():
    """upsert_products_from_comparison skips products with empty names."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "prod-1"}]

    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    full_response = {
        "products": [
            {"brand": "", "name": "", "category": "unknown"},
            {"brand": "Apple", "name": "iPhone 15"},
        ]
    }

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import upsert_products_from_comparison
        ids = await upsert_products_from_comparison(full_response)

    # Only the second product should be upserted
    assert len(ids) == 1
