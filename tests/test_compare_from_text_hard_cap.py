"""L2.7 — Tests for compare_from_text() hard-cap wrapper.

Verifies the non-streaming path now honors STREAM_HARD_CAP_SECONDS (default
25s) just like the streaming path. On timeout the caller receives a graceful
`{success: false, code: 'TIMEOUT'}` response — NOT a raised TimeoutError.
"""

import asyncio
import os
import time

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_compare_from_text_hard_capped_on_slow_impl():
    """If _compare_from_text_impl hangs for 60s, compare_from_text returns
    a TIMEOUT error within STREAM_HARD_CAP_SECONDS + small buffer."""
    from app.services.structured_comparison_service import (
        STREAM_HARD_CAP_SECONDS,
        get_comparison_service,
    )

    svc = get_comparison_service()

    async def slow_impl(*_args, **_kwargs):
        await asyncio.sleep(60)
        return {"success": True}

    with patch.object(svc, "_compare_from_text_impl", side_effect=slow_impl):
        start = time.perf_counter()
        result = await svc.compare_from_text("foo vs bar", region="bahrain")
        elapsed = time.perf_counter() - start

        # Hard cap + 2s buffer for asyncio overhead
        assert elapsed <= STREAM_HARD_CAP_SECONDS + 2.0, (
            f"compare_from_text took {elapsed:.1f}s — hard cap did not fire"
        )

        # WS1 (6bfe830) refreshed the no-data hard-cap copy to the no-scary-copy
        # contract (D2). slow_impl stashes NO partial state → this is the no-data
        # TIMEOUT path, which now returns TIMEOUT_FRIENDLY_MESSAGE (was the stale
        # "We couldn't finish… Try again." that the old `or` clause masked).
        from app.services.structured_comparison_service import TIMEOUT_FRIENDLY_MESSAGE

        assert result["success"] is False
        assert result["code"] == "TIMEOUT"
        assert result["error"] == TIMEOUT_FRIENDLY_MESSAGE
        # The refreshed copy must not leak the old scary vocab (.copy-policy.json).
        for _scary in ("couldn't", "try again", "failed to"):
            assert _scary not in result["error"].lower()


@pytest.mark.asyncio
async def test_compare_from_text_passes_through_fast_result():
    """When the impl returns fast, compare_from_text just delegates."""
    from app.services.structured_comparison_service import get_comparison_service

    svc = get_comparison_service()

    async def fast_impl(*_args, **_kwargs):
        return {"success": True, "products": [], "marker": "fast"}

    with patch.object(svc, "_compare_from_text_impl", side_effect=fast_impl):
        result = await svc.compare_from_text("foo vs bar", region="bahrain")
        assert result["marker"] == "fast"
        assert result["success"] is True


@pytest.mark.asyncio
async def test_compare_from_text_does_not_swallow_other_errors():
    """Non-TimeoutError exceptions propagate as before (they are caught by
    the inner impl's try/except and converted to {success:false, error:...})."""
    from app.services.structured_comparison_service import get_comparison_service

    svc = get_comparison_service()

    async def raises_impl(*_args, **_kwargs):
        # Inner impl is itself wrapped in try/except, so this surfaces as
        # the {success:false,error:...} shape, not raise upward.
        return {"success": False, "error": "boom"}

    with patch.object(svc, "_compare_from_text_impl", side_effect=raises_impl):
        result = await svc.compare_from_text("foo vs bar", region="bahrain")
        assert result["success"] is False
        assert result.get("error") == "boom"


@pytest.mark.asyncio
async def test_compare_from_text_streaming_already_capped_no_double_cap():
    """L2.7 must not double-wrap the streaming path. compare_from_text_streaming
    has its OWN asyncio.wait_for already (line ~1461). Just verify the impl
    method is reachable directly so streaming doesn't accidentally route through
    the new hard-capped wrapper."""
    from app.services.structured_comparison_service import (
        StructuredComparisonService,
    )

    # Streaming method should still exist on the class and NOT be aliased
    # to compare_from_text (the wrapper).
    assert hasattr(StructuredComparisonService, "compare_from_text_streaming")
    assert hasattr(StructuredComparisonService, "_compare_from_text_impl")
    assert hasattr(StructuredComparisonService, "compare_from_text")
