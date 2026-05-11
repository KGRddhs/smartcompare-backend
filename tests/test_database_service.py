"""Tests for app/services/database_service.py — Bundle A §1.3 / §1.4 / §1.5."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.database_service import (
    _validate_renderable,
    get_comparison_by_id,
    get_user_comparison_count,
    get_user_comparisons,
    save_comparison,
)


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


# ---------- Task 1.5: history list filters schema_version=2 ----------


def _build_chain_mock(final_data):
    """Build a fluent Supabase query chain that returns `final_data` on execute()."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.ilike.return_value = chain
    chain.range.return_value = chain
    chain.single.return_value = chain
    execute_result = MagicMock()
    execute_result.data = final_data
    execute_result.count = (
        len(final_data) if isinstance(final_data, list) else 1
    )
    chain.execute.return_value = execute_result
    return chain


@pytest.mark.asyncio
async def test_get_user_comparisons_filters_schema_version_2():
    """get_user_comparisons should call .eq('schema_version', 2)."""
    chain = _build_chain_mock(final_data=[])
    mock_client = MagicMock()
    mock_client.table.return_value = chain
    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        await get_user_comparisons(user_id="u1")

    eq_calls = [c.args for c in chain.eq.call_args_list]
    assert ("user_id", "u1") in eq_calls
    assert ("schema_version", 2) in eq_calls


@pytest.mark.asyncio
async def test_get_user_comparison_count_filters_schema_version_2():
    """get_user_comparison_count should call .eq('schema_version', 2)."""
    chain = _build_chain_mock(final_data=[])
    mock_client = MagicMock()
    mock_client.table.return_value = chain
    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        await get_user_comparison_count(user_id="u1")

    eq_calls = [c.args for c in chain.eq.call_args_list]
    assert ("user_id", "u1") in eq_calls
    assert ("schema_version", 2) in eq_calls


@pytest.mark.asyncio
async def test_get_comparison_by_id_returns_none_for_v1_row():
    """get_comparison_by_id returns None when row.schema_version < 2."""
    row = {
        "id": "c1",
        "user_id": "u1",
        "schema_version": 1,
        "full_response": {"products": []},
    }
    chain = _build_chain_mock(final_data=row)
    mock_client = MagicMock()
    mock_client.table.return_value = chain
    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        result = await get_comparison_by_id("c1")
    assert result is None


@pytest.mark.asyncio
async def test_get_comparison_by_id_returns_v2_row():
    """get_comparison_by_id returns the row when schema_version=2."""
    row = {
        "id": "c2",
        "user_id": "u1",
        "schema_version": 2,
        "full_response": {
            "overview": {"products": [{"name": "A"}, {"name": "B"}]},
            "metadata": {"query": "A vs B"},
        },
    }
    chain = _build_chain_mock(final_data=row)
    mock_client = MagicMock()
    mock_client.table.return_value = chain
    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        result = await get_comparison_by_id("c2")
    assert result == row


@pytest.mark.asyncio
async def test_get_comparison_by_id_include_legacy_returns_v1_row():
    """When include_legacy=True the v1-filter is bypassed (used by DELETE flow)."""
    row = {
        "id": "c1",
        "user_id": "u1",
        "schema_version": 1,
        "full_response": {"products": []},
    }
    chain = _build_chain_mock(final_data=row)
    mock_client = MagicMock()
    mock_client.table.return_value = chain
    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        result = await get_comparison_by_id("c1", include_legacy=True)
    assert result == row


# ---------- Task 1.9: idle-work coverage on edge cases ----------


@pytest.mark.asyncio
async def test_get_comparison_by_id_missing_schema_version_treated_as_v1():
    """A row without schema_version (legacy DB state) must be hidden by default."""
    row = {"id": "c1", "user_id": "u1", "full_response": {"products": []}}
    chain = _build_chain_mock(final_data=row)
    mock_client = MagicMock()
    mock_client.table.return_value = chain
    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        result = await get_comparison_by_id("c1")
    assert result is None


@pytest.mark.asyncio
async def test_get_comparison_by_id_handles_supabase_exception_returns_none():
    """Any exception from the supabase call collapses to None (caller maps to 404)."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute.side_effect = RuntimeError("transient blip")
    mock_client = MagicMock()
    mock_client.table.return_value = chain
    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        result = await get_comparison_by_id("c1")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_comparisons_search_param_preserves_v2_filter():
    """When search is supplied, the schema_version=2 filter MUST still be applied."""
    chain = _build_chain_mock(final_data=[])
    mock_client = MagicMock()
    mock_client.table.return_value = chain
    with patch(
        "app.services.database_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        await get_user_comparisons(user_id="u1", search="iphone")
    eq_calls = [c.args for c in chain.eq.call_args_list]
    assert ("schema_version", 2) in eq_calls
    chain.ilike.assert_called()
    ilike_args = chain.ilike.call_args.args
    assert ilike_args[0] == "query"
    assert "iphone" in ilike_args[1]


@pytest.mark.asyncio
async def test_save_comparison_skips_payload_with_blank_query():
    """A payload with two products but no metadata.query must be rejected."""
    payload = {
        "overview": {"products": [{"name": "A"}, {"name": "B"}]},
        "metadata": {"query": ""},  # blank
    }
    with patch("app.services.database_service.get_supabase_client") as m:
        result = await save_comparison(
            full_response=payload, query="A vs B", user_id="u1"
        )
        m.assert_not_called()
    assert result is None
