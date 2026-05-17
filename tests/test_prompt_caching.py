"""D2 Intervention 2 — extraction prompts must have static-prefix >1024 tokens
to engage OpenAI gpt-4o-mini auto-caching."""
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import tiktoken

from app.services.extraction_service import _build_specs_prompt
# Add imports for other prompt builders as they exist


enc = tiktoken.encoding_for_model("gpt-4o-mini")
MIN_CACHEABLE_TOKENS = 1024


def _static_prefix(system_prompt: str) -> str:
    """Extract the static prefix — everything BEFORE the first dynamic
    interpolation marker (CATEGORY, BAHRAIN DRUG DATABASE, schema fields)."""
    for marker in ("CATEGORY:", "BAHRAIN DRUG DATABASE", "REQUIRED SCHEMA"):
        if marker in system_prompt:
            return system_prompt.split(marker)[0]
    return system_prompt


def test_specs_prompt_electronics_static_prefix_cacheable():
    """Specs prompt for electronics must have >=1024-token static prefix."""
    p = _build_specs_prompt("Apple", "iPhone 17", None, "electronics", "snippets")
    static = _static_prefix(p["system"])
    tokens = len(enc.encode(static))
    assert tokens >= MIN_CACHEABLE_TOKENS, (
        f"Specs/electronics static prefix is {tokens} tokens "
        f"(need >={MIN_CACHEABLE_TOKENS} for OpenAI auto-caching)"
    )


def test_specs_prompt_supplements_static_prefix_cacheable():
    """Specs prompt for supplements must have >=1024-token static prefix
    (drug_context is dynamic, but the prefix before it must still cache)."""
    p = _build_specs_prompt("Centrum", "Adults", None, "supplements", "snippets", drug_context="drug data")
    static = _static_prefix(p["system"])
    tokens = len(enc.encode(static))
    assert tokens >= MIN_CACHEABLE_TOKENS, (
        f"Specs/supplements static prefix is {tokens} tokens "
        f"(need >={MIN_CACHEABLE_TOKENS})"
    )


def test_specs_prompt_static_prefix_is_identical_across_categories():
    """The static prefix must be byte-identical across category variations
    so OpenAI's cache prefix-matching engages."""
    p_electronics = _build_specs_prompt("X", "Y", None, "electronics", "ctx")
    p_supplements = _build_specs_prompt("X", "Y", None, "supplements", "ctx")

    prefix_e = _static_prefix(p_electronics["system"])
    prefix_s = _static_prefix(p_supplements["system"])

    assert prefix_e == prefix_s, (
        "Static prefix differs across categories — cache won't engage. "
        f"First difference: {next((i for i, (a, b) in enumerate(zip(prefix_e, prefix_s)) if a != b), len(prefix_e))}"
    )


@pytest.mark.asyncio
async def test_prompt_caching_hit_is_logged(caplog):
    """When OpenAI response includes usage.prompt_tokens_cached > 0 (or the
    nested prompt_tokens_details.cached_tokens path on SDK 2.x), a
    [OPENAI_CACHE] log line must fire."""
    caplog.set_level(logging.INFO)

    # Mock OpenAI client response. SDK 2.x exposes cached tokens at
    # response.usage.prompt_tokens_details.cached_tokens (NOT the flat
    # response.usage.prompt_tokens_cached). Telemetry helper uses a
    # getattr fallback to support both shapes.
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"ram": "12 GB"}'))]
    usage = MagicMock(
        prompt_tokens=2000,
        completion_tokens=50,
    )
    # SDK 2.x nested shape: prompt_tokens_details.cached_tokens
    prompt_tokens_details = MagicMock(cached_tokens=1500)
    usage.prompt_tokens_details = prompt_tokens_details
    # Explicitly remove the flat attribute so getattr fallback exercises
    # the nested path (mimics SDK 2.x reality).
    del usage.prompt_tokens_cached
    mock_response.usage = usage

    with patch("app.services.openai_service.get_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_factory.return_value = mock_client

        from app.services.openai_service import extract_specs_targeted
        await extract_specs_targeted(
            brand="Apple", name="iPhone 17", variant=None,
            category="electronics", fields=["ram"], context="snippets",
        )

    # Assert telemetry log fired
    cache_logs = [r for r in caplog.records if "[OPENAI_CACHE]" in r.message]
    assert cache_logs, (
        f"Expected [OPENAI_CACHE] log line for cached_tokens=1500. "
        f"Got: {[r.message for r in caplog.records]}"
    )
    assert "1500" in cache_logs[0].message, (
        f"Log should mention cached token count: {cache_logs[0].message}"
    )
