"""Tests for app/services/database_service.py — Bundle A §1.3 / §1.4."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.database_service import _validate_renderable, save_comparison


class TestValidateRenderable:
    def test_passes_new_format_with_overview(self):
        payload = {
            "overview": {"products": [{"name": "A"}, {"name": "B"}]},
            "metadata": {"query": "A vs B"},
        }
        assert _validate_renderable(payload) is True

    def test_passes_legacy_alias_format(self):
        payload = {
            "products": [{"name": "A"}, {"name": "B"}],
            "metadata": {"query": "A vs B"},
        }
        assert _validate_renderable(payload) is True

    def test_fails_when_fewer_than_two_products(self):
        payload = {
            "overview": {"products": [{"name": "A"}]},
            "metadata": {"query": "solo"},
        }
        assert _validate_renderable(payload) is False

    def test_fails_when_product_name_missing(self):
        payload = {
            "overview": {"products": [{"name": "A"}, {}]},
            "metadata": {"query": "broken"},
        }
        assert _validate_renderable(payload) is False

    def test_fails_when_query_missing(self):
        payload = {
            "overview": {"products": [{"name": "A"}, {"name": "B"}]},
            "metadata": {},
        }
        assert _validate_renderable(payload) is False

    def test_fails_when_payload_empty(self):
        assert _validate_renderable({}) is False

    def test_fails_when_not_a_dict(self):
        assert _validate_renderable(None) is False
        assert _validate_renderable([]) is False
        assert _validate_renderable("x") is False


# ---------- save_comparison tests (Task 1.4) ----------


@pytest.mark.asyncio
async def test_save_comparison_skips_when_not_renderable(caplog):
    payload = {"products": []}  # invalid — no products
    with patch("app.services.database_service.get_supabase_client") as m:
        result = await save_comparison(
            full_response=payload, query="q", user_id="u1"
        )
        m.assert_not_called()
    assert result is None
    assert any(
        "renderable" in r.message.lower() or "skip" in r.message.lower()
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_save_comparison_populates_product_names_and_v2():
    payload = {
        "overview": {
            "products": [{"name": "iPhone 15"}, {"name": "Galaxy S24"}]
        },
        "metadata": {"query": "iPhone vs Galaxy"},
    }
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "c1"}]
    )
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch(
        "app.services.database_service.get_supabase_client",
        return_value=mock_client,
    ):
        await save_comparison(
            full_response=payload,
            query="iPhone vs Galaxy",
            user_id="u1",
        )

    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["schema_version"] == 2
    assert insert_arg["product_names"] == ["iPhone 15", "Galaxy S24"]
    assert insert_arg["full_response"] == payload
    assert insert_arg["user_id"] == "u1"


@pytest.mark.asyncio
async def test_save_comparison_legacy_alias_products_also_writes_v2():
    """Legacy `products` (no overview wrapper) is still renderable -> v2 row."""
    payload = {
        "products": [{"name": "X"}, {"name": "Y"}],
        "metadata": {"query": "X vs Y"},
    }
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "c2"}]
    )
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch(
        "app.services.database_service.get_supabase_client",
        return_value=mock_client,
    ):
        await save_comparison(
            full_response=payload, query="X vs Y", user_id="u2"
        )

    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["schema_version"] == 2
    assert insert_arg["product_names"] == ["X", "Y"]
