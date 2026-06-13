"""L2.3 — YouTube as a reviews-race participant (must NOT extend p95).

`consult_youtube_source()` is the flag-gated, wait_for-capped dispatcher that
runs INSIDE review_service.get_reviews() AFTER the extraction is persisted
(F3/G2 persist-first ordering). A slow / failed / flag-off YouTube call yields
None and the persisted reviews ship unchanged — YouTube can never drag the
reviews race past its budget.

Mirrors the S2 I2.5 consult_review_sources contract + tests.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("YOUTUBE_API_KEY", "test-yt-key")

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

import app.services.review_service as rs
from app.services.review_service import (
    consult_youtube_source,
    youtube_source_enabled,
)


_SIGNAL = {
    "review_count_signal": 5300,
    "top_video_title": "iPhone 16 — Full Review After 30 Days",
    "top_channel": "MKBHD",
    "video_url": "https://www.youtube.com/watch?v=abc",
    "total_views": 1_098_576,
    "video_count": 2,
}


# ---------------------------------------------------------------------------
# Flag (ENABLE_YOUTUBE_SOURCE) — default OFF
# ---------------------------------------------------------------------------

def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    assert youtube_source_enabled() is False


@pytest.mark.parametrize("val,expected", [
    ("true", True), ("1", True), ("on", True), ("TRUE", True), ("yes", True),
    ("", False), ("false", False), ("off", False), ("0", False), ("nope", False),
])
def test_flag_parsing(monkeypatch, val, expected):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", val)
    assert youtube_source_enabled() is expected


# ---------------------------------------------------------------------------
# consult_youtube_source dispatcher
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consult_off_returns_none_no_fetch(monkeypatch):
    """Flag OFF → instant None, the API client is never even called."""
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    fetch_mock = AsyncMock()
    with patch("app.services.review_service.fetch_youtube_review_signal", new=fetch_mock):
        out = await consult_youtube_source("Apple", "iPhone 16", None, "electronics")
    assert out is None
    fetch_mock.assert_not_called()  # OFF spends nothing


@pytest.mark.asyncio
async def test_consult_on_returns_signal(monkeypatch):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    with patch(
        "app.services.review_service.fetch_youtube_review_signal",
        new=AsyncMock(return_value=_SIGNAL),
    ):
        out = await consult_youtube_source("Apple", "iPhone 16", None, "electronics")
    assert out == _SIGNAL


@pytest.mark.asyncio
async def test_consult_timeout_yields_none(monkeypatch):
    """p95 GUARD: a slow YouTube call is capped by the inner wait_for and drops
    out as None — it never blocks past `timeout`."""
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")

    async def slow_fetch(*a, **k):
        await asyncio.sleep(5)
        return _SIGNAL

    with patch("app.services.review_service.fetch_youtube_review_signal", new=slow_fetch):
        out = await consult_youtube_source(
            "Apple", "iPhone 16", None, "electronics", timeout=0.05,
        )
    assert out is None  # capped, never blocks


@pytest.mark.asyncio
async def test_consult_error_yields_none_never_raises(monkeypatch):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")

    async def boom(*a, **k):
        raise RuntimeError("youtube blew up")

    with patch("app.services.review_service.fetch_youtube_review_signal", new=boom):
        out = await consult_youtube_source("Apple", "iPhone 16", None, "electronics")
    assert out is None  # graceful — never raises


@pytest.mark.asyncio
async def test_consult_miss_yields_none(monkeypatch):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    with patch(
        "app.services.review_service.fetch_youtube_review_signal",
        new=AsyncMock(return_value=None),
    ):
        out = await consult_youtube_source("Obscure", "Thing", None, "other")
    assert out is None


# ---------------------------------------------------------------------------
# get_reviews integration — persist-BEFORE-consult + attach + cancel-safety
# ---------------------------------------------------------------------------

async def _extract(brand, name, variant, ctx, category="other"):
    return ({"review_summary": {"highlights": []}}, {"total_tokens": 10})


@pytest.mark.asyncio
async def test_get_reviews_attaches_youtube_signal(monkeypatch):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    # Keep the I2.5 review-source consult OFF so it doesn't interfere.
    monkeypatch.delenv("ENABLE_REVIEW_SOURCE_CONSULT", raising=False)

    with patch("app.services.review_service.get_cached", return_value=None), \
         patch("app.services.review_service.set_cached", return_value=True), \
         patch("app.services.review_service.extract_reviews", new=AsyncMock(side_effect=_extract)), \
         patch("app.services.review_service.fetch_youtube_review_signal",
               new=AsyncMock(return_value=_SIGNAL)), \
         patch("app.services.product_data_service.get_cached_reviews", new=AsyncMock(return_value=None)), \
         patch("app.services.product_data_service.save_reviews", new=AsyncMock()):
        reviews = await rs.get_reviews(
            "Apple", "iPhone 16", None, "Apple iPhone 16",
            nocache=True, category="electronics",
            search_results={"organic": []},
        )

    assert reviews.get("youtube_review_signal") == _SIGNAL


@pytest.mark.asyncio
async def test_get_reviews_persists_extraction_before_youtube_consult(monkeypatch):
    """ORDER pin: set_cached (extraction persist) MUST run BEFORE the YouTube
    consult — so a wait_for-cancel mid-consult can't lose finished reviews."""
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    monkeypatch.delenv("ENABLE_REVIEW_SOURCE_CONSULT", raising=False)

    order = []

    def _set_cached(key, value, ttl):
        order.append("set_cached")
        return True

    async def _consult_yt(*a, **k):
        order.append("youtube_consult")
        return _SIGNAL

    with patch("app.services.review_service.get_cached", return_value=None), \
         patch("app.services.review_service.set_cached", side_effect=_set_cached), \
         patch("app.services.review_service.extract_reviews", new=AsyncMock(side_effect=_extract)), \
         patch("app.services.review_service.consult_youtube_source", new=AsyncMock(side_effect=_consult_yt)), \
         patch("app.services.product_data_service.get_cached_reviews", new=AsyncMock(return_value=None)), \
         patch("app.services.product_data_service.save_reviews", new=AsyncMock()):
        await rs.get_reviews(
            "Apple", "iPhone 16", None, "Apple iPhone 16",
            nocache=True, category="electronics",
            search_results={"organic": []},
        )

    assert "set_cached" in order and "youtube_consult" in order
    assert order.index("set_cached") < order.index("youtube_consult"), (
        f"extraction must persist BEFORE youtube consult; got {order}"
    )


@pytest.mark.asyncio
async def test_get_reviews_youtube_failure_does_not_break_reviews(monkeypatch):
    """A YouTube consult that raises must NOT bubble — reviews still return,
    just without the signal."""
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    monkeypatch.delenv("ENABLE_REVIEW_SOURCE_CONSULT", raising=False)

    async def boom(*a, **k):
        raise RuntimeError("youtube exploded")

    with patch("app.services.review_service.get_cached", return_value=None), \
         patch("app.services.review_service.set_cached", return_value=True), \
         patch("app.services.review_service.extract_reviews", new=AsyncMock(side_effect=_extract)), \
         patch("app.services.review_service.consult_youtube_source", new=AsyncMock(side_effect=boom)), \
         patch("app.services.product_data_service.get_cached_reviews", new=AsyncMock(return_value=None)), \
         patch("app.services.product_data_service.save_reviews", new=AsyncMock()):
        reviews = await rs.get_reviews(
            "Apple", "iPhone 16", None, "Apple iPhone 16",
            nocache=True, category="electronics",
            search_results={"organic": []},
        )

    # reviews returned fine; no youtube signal attached.
    assert reviews is not None
    assert "youtube_review_signal" not in reviews or reviews["youtube_review_signal"] is None


@pytest.mark.asyncio
async def test_get_reviews_flag_off_no_youtube_key_in_payload(monkeypatch):
    """Flag OFF → get_reviews never attaches a youtube_review_signal key."""
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    monkeypatch.delenv("ENABLE_REVIEW_SOURCE_CONSULT", raising=False)
    fetch_mock = AsyncMock()

    with patch("app.services.review_service.get_cached", return_value=None), \
         patch("app.services.review_service.set_cached", return_value=True), \
         patch("app.services.review_service.extract_reviews", new=AsyncMock(side_effect=_extract)), \
         patch("app.services.review_service.fetch_youtube_review_signal", new=fetch_mock), \
         patch("app.services.product_data_service.get_cached_reviews", new=AsyncMock(return_value=None)), \
         patch("app.services.product_data_service.save_reviews", new=AsyncMock()):
        reviews = await rs.get_reviews(
            "Apple", "iPhone 16", None, "Apple iPhone 16",
            nocache=True, category="electronics",
            search_results={"organic": []},
        )

    assert "youtube_review_signal" not in reviews
    fetch_mock.assert_not_called()  # OFF = zero quota
