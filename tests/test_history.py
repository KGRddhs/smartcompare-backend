"""Tests for history save/load/delete pipeline."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


MOCK_FULL_RESPONSE = {
    "success": True,
    "products": [
        {"brand": "Apple", "name": "iPhone 15", "price": {"amount": 299.0, "currency": "BHD"}},
        {"brand": "Samsung", "name": "Galaxy S24", "price": {"amount": 269.0, "currency": "BHD"}},
    ],
    "comparison": {
        "winner_index": 0,
        "recommendation": "iPhone 15 wins",
        "key_differences": ["Better camera", "Higher price"],
    },
    "metadata": {"query": "iphone 15 vs galaxy s24", "total_cost": 0.01},
}


def test_save_comparison_extracts_product_names():
    """save_comparison extracts product_names (name-only, first 2) from full_response.

    Bundle A §5.2 contract change: product_names is now `[p["name"] for p in
    products[:2]]` — name-only, capped at 2. The brand prefix was dropped
    because (a) brand is already in full_response.products[i].brand for any
    UI that needs it, and (b) the new History card design renders brand and
    name separately rather than as a single concatenated label.
    """
    mock_response = MagicMock()
    mock_response.data = [{"id": "abc-123"}]

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import save_comparison
        result = run_async(save_comparison(
            full_response=MOCK_FULL_RESPONSE,
            query="iphone 15 vs galaxy s24",
            input_type="text",
            user_id="user-123",
        ))

    assert result == {"id": "abc-123"}
    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["product_names"] == ["iPhone 15", "Galaxy S24"]
    assert insert_arg["query"] == "iphone 15 vs galaxy s24"
    assert insert_arg["input_type"] == "text"
    assert insert_arg["user_id"] == "user-123"
    assert insert_arg["full_response"] == MOCK_FULL_RESPONSE
    # Bundle A §5.2: persisted rows are always schema_version=2.
    assert insert_arg["schema_version"] == 2


def test_save_comparison_no_user_id():
    """save_comparison omits user_id when None (anonymous)."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "abc-456"}]

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import save_comparison
        result = run_async(save_comparison(
            full_response=MOCK_FULL_RESPONSE,
            query="test query",
        ))

    insert_arg = mock_table.insert.call_args[0][0]
    assert "user_id" not in insert_arg


def test_save_comparison_returns_none_on_error():
    """save_comparison returns None on error (fire-and-forget)."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB down")

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import save_comparison
        result = run_async(save_comparison(
            full_response=MOCK_FULL_RESPONSE,
            query="test",
            user_id="user-123",
        ))

    assert result is None


def test_save_comparison_rejects_payload_with_no_products():
    """save_comparison rejects (does NOT persist) payloads that fail _validate_renderable.

    Bundle A §5.2: rows that ResultsScreen can't render must never reach the
    history table — they were the root cause of the History "Cannot read
    property 'products' of undefined" crash. A payload like {"success": True}
    has no products array and no metadata.query, so the validator rejects it
    and save_comparison returns None without touching the DB.
    """
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import save_comparison
        result = run_async(save_comparison(full_response={"success": True}, query="test"))

    assert result is None
    # The DB layer must not have been engaged at all.
    mock_client.table.assert_not_called()
    mock_table.insert.assert_not_called()


def test_save_comparison_camera_input_type():
    """save_comparison stores camera input_type correctly."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "cam-123"}]

    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_response

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_supabase_client", return_value=mock_client):
        from app.services.database_service import save_comparison
        result = run_async(save_comparison(
            full_response=MOCK_FULL_RESPONSE,
            query="iPhone 15 vs Galaxy S24",
            input_type="camera",
            user_id="user-456",
        ))

    assert result == {"id": "cam-123"}
    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["input_type"] == "camera"


def test_get_user_comparisons_with_search():
    """get_user_comparisons filters by search term."""
    mock_table = MagicMock()
    mock_query = MagicMock()
    mock_table.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.ilike.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"id": "1"}])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_admin_supabase_client", return_value=mock_client):
        from app.services.database_service import get_user_comparisons
        result = run_async(get_user_comparisons("user-123", search="iphone"))

    mock_query.ilike.assert_called_once_with("query", "%iphone%")
    assert result == [{"id": "1"}]


def test_get_user_comparisons_without_search():
    """get_user_comparisons skips ilike when no search term."""
    mock_table = MagicMock()
    mock_query = MagicMock()
    mock_table.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"id": "1"}])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_admin_supabase_client", return_value=mock_client):
        from app.services.database_service import get_user_comparisons
        result = run_async(get_user_comparisons("user-123"))

    mock_query.ilike.assert_not_called()


def test_delete_comparison_own():
    """delete_comparison succeeds for own comparison."""
    mock_table = MagicMock()
    mock_query = MagicMock()
    mock_table.delete.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"id": "comp-1"}])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_admin_supabase_client", return_value=mock_client):
        from app.services.database_service import delete_comparison
        result = run_async(delete_comparison("comp-1", "user-123"))

    assert result is True


def test_delete_comparison_not_found():
    """delete_comparison returns False when comparison not found or not owned."""
    mock_table = MagicMock()
    mock_query = MagicMock()
    mock_table.delete.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.services.database_service.get_admin_supabase_client", return_value=mock_client):
        from app.services.database_service import delete_comparison
        result = run_async(delete_comparison("comp-999", "user-123"))

    assert result is False


def test_delete_comparison_handles_error():
    """delete_comparison returns False on DB error."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB error")

    with patch("app.services.database_service.get_admin_supabase_client", return_value=mock_client):
        from app.services.database_service import delete_comparison
        result = run_async(delete_comparison("comp-1", "user-123"))

    assert result is False
