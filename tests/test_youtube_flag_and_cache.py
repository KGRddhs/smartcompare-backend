"""L2.5 — ENABLE_YOUTUBE_SOURCE flag (default OFF) + 14d cache + inert-when-OFF.

Consolidates the flag-default + cache-TTL contract and proves the ENTIRE
YouTube chain is inert when the flag is OFF: the dispatcher returns None without
calling the API client, the verdict block is empty, and the response/streaming
surfaces carry None. Privacy: the signal is titles + public counts only.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("YOUTUBE_API_KEY", "test-yt-key")

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

import app.services.youtube_service as yt
import app.services.review_service as rs
from app.services.extraction_service import _build_youtube_signal_block
from app.services.response_builder import _youtube_signal_for_response


_SIGNAL = {
    "review_count_signal": 5300, "top_video_title": "Review",
    "top_channel": "MKBHD", "video_url": "https://www.youtube.com/watch?v=abc",
    "total_views": 1_000_000, "video_count": 5,
}


def _product():
    return {"reviews": {"review_summary": {}, "youtube_review_signal": _SIGNAL}}


# ---------------------------------------------------------------------------
# Flag default + cache TTL
# ---------------------------------------------------------------------------

def test_flag_default_off(monkeypatch):
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    assert rs.youtube_source_enabled() is False


def test_cache_ttl_is_14_days():
    assert yt.YOUTUBE_CACHE_TTL == 14 * 24 * 60 * 60


# ---------------------------------------------------------------------------
# Flag OFF => the WHOLE chain is inert
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_off_dispatcher_no_api_call(monkeypatch):
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    fetch = AsyncMock()
    with patch("app.services.review_service.fetch_youtube_review_signal", new=fetch):
        out = await rs.consult_youtube_source("Apple", "iPhone 16", None, "electronics")
    assert out is None
    fetch.assert_not_called()


def test_off_verdict_block_empty(monkeypatch):
    """Even if a stale signal is on the product (14d cache), the verdict block
    is empty when OFF — because generate_comparison only builds the block under
    the flag, and the scrub strips the json.dumps payload. Here we assert the
    builder-level contract: the block fn returns content only from present
    signals, and the flag-gating happens at the call site; the scrub makes the
    product carry nothing. We verify the scrub+build composition is empty."""
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    from app.services.extraction_service import _scrub_youtube_signal_if_off
    p = _scrub_youtube_signal_if_off(_product())
    assert _build_youtube_signal_block(p, None) == ""


def test_off_response_surface_none(monkeypatch):
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    assert _youtube_signal_for_response(_product()) is None


def test_on_response_surface_present(monkeypatch):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    assert _youtube_signal_for_response(_product()) == _SIGNAL


# ---------------------------------------------------------------------------
# Streaming parity: the SSE reviews event uses the same flag-gated helper
# ---------------------------------------------------------------------------

def test_streaming_reviews_event_uses_helper():
    """Structural guard: structured_comparison_service imports + uses
    _youtube_signal_for_response so the streaming reviews SSE event carries the
    same flag-gated signal as the non-streaming response. (Pins the import so a
    refactor that drops streaming parity is caught.)"""
    import app.services.structured_comparison_service as scs
    assert hasattr(scs, "_youtube_signal_for_response")
    # And the streaming reviews event references the key (source-level pin).
    import inspect
    src = inspect.getsource(scs)
    assert '"youtube_review_signal": _youtube_signal_for_response(pd)' in src


# ---------------------------------------------------------------------------
# Privacy: the signal carries only public titles/counts, no user data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_signal_contains_only_public_fields(monkeypatch):
    """The cached/returned signal keys are a fixed public allow-list — no user
    id / device / PII can ride along."""
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")

    async def get(url, params=None, **kw):
        class R:
            status_code = 200
            text = "ok"
            def json(self):
                if "search" in url:
                    return {"items": [{"id": {"videoId": "v1"},
                                       "snippet": {"title": "t", "channelTitle": "c"}}]}
                return {"items": [{"id": "v1",
                                   "snippet": {"title": "t", "channelTitle": "c"},
                                   "statistics": {"viewCount": "100", "commentCount": "5"}}]}
            def raise_for_status(self): pass
        return R()

    from unittest.mock import MagicMock
    client = MagicMock()
    client.get = AsyncMock(side_effect=get)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.youtube_service.get_cached", return_value=None), \
         patch("app.services.youtube_service.set_cached"), \
         patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        signal = await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    assert signal is not None
    allowed = {
        "review_count_signal", "top_video_title", "top_channel",
        "video_url", "total_views", "video_count",
    }
    assert set(signal.keys()) == allowed, f"unexpected keys leaked: {set(signal) - allowed}"
