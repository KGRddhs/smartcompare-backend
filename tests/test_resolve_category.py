"""Tests for classify_category_llm() — A2b.

classify_category_llm(texts) is a classify-only gpt-4o-mini call (NOT
parse_product_query) that returns one canonical category key, "other" on any
error / timeout / unknown output.

NOTE (CLEANUP-1): the old `resolve_category` precedence ladder was deleted as
prod-dead — the live resolver is `_resolve_pair_category` in
structured_comparison_service. Its precedence coverage (incl. the cases this file
used to assert) now lives in tests/test_explicit_pair_category.py
(`_resolve_pair_category` direct tests, both parser_path branches).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================
# A2b: classify_category_llm (bounded gpt-4o-mini, classify-only)
# ============================================

def _mock_openai_response(content: str):
    """Build a fake OpenAI chat.completions response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.mark.asyncio
async def test_classify_category_llm_returns_canonical():
    from app.services import extraction_service
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response("fragrances")
    )
    with patch.object(extraction_service, "get_client", return_value=fake_client):
        result = await extraction_service.classify_category_llm(
            ["Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"]
        )
    assert result == "fragrances"


@pytest.mark.asyncio
async def test_classify_category_llm_canonicalizes_messy_output():
    from app.services import extraction_service
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response("  Fragrances  ")
    )
    with patch.object(extraction_service, "get_client", return_value=fake_client):
        result = await extraction_service.classify_category_llm(["X", "Y"])
    assert result == "fragrances"


@pytest.mark.asyncio
async def test_classify_category_llm_error_returns_other():
    from app.services import extraction_service
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))
    with patch.object(extraction_service, "get_client", return_value=fake_client):
        result = await extraction_service.classify_category_llm(["X", "Y"])
    assert result == "other"


@pytest.mark.asyncio
async def test_classify_category_llm_unknown_output_returns_other():
    from app.services import extraction_service
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response("kitchenware")
    )
    with patch.object(extraction_service, "get_client", return_value=fake_client):
        result = await extraction_service.classify_category_llm(["X", "Y"])
    assert result == "other"


@pytest.mark.asyncio
async def test_classify_category_llm_empty_input_returns_other_without_calling_openai():
    # The empty-input short-circuit returns "other" and must NOT spend a GPT call.
    from app.services import extraction_service
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response("fragrances")
    )
    with patch.object(extraction_service, "get_client", return_value=fake_client):
        assert await extraction_service.classify_category_llm([]) == "other"
        assert await extraction_service.classify_category_llm(None) == "other"
        # all-whitespace / non-str entries are dropped -> still empty -> "other"
        assert await extraction_service.classify_category_llm(["  ", 123, None]) == "other"
    fake_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_classify_category_llm_times_out_to_other():
    """CLEANUP-4(a): a hung OpenAI create() must not block the blind path — the
    wait_for cap fires and returns 'other' (latency hygiene)."""
    import asyncio as _asyncio
    from app.services import extraction_service

    async def _hang(*a, **k):
        await _asyncio.sleep(5.0)  # longer than the (patched-tiny) cap
        return _mock_openai_response("fragrances")

    fake_client = MagicMock()
    fake_client.chat.completions.create = _hang
    with patch.object(extraction_service, "get_client", return_value=fake_client), \
         patch.object(extraction_service, "_CLASSIFY_LLM_TIMEOUT", 0.05):
        result = await extraction_service.classify_category_llm(["Mystery A", "Mystery B"])
    assert result == "other"
