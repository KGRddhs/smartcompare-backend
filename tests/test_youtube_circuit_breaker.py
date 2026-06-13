"""L2.2 (plan-conformance) — YouTube circuit breaker, Firecrawl pattern.

Plan §L2.2: "circuit-breaker on the Firecrawl pattern." fetch_youtube_review_
signal must:
  - gate on is_circuit_closed("youtube") BEFORE any HTTP call (open -> None, no
    call, no quota spend),
  - record_failure("youtube") on a SERVICE-level failure (timeout / 5xx /
    connection error — a raised exception from the API call),
  - record_success("youtube") after a fully successful fetch (resets the
    failure count / closes a half-open breaker),
  - NOT record_failure on a clean "no videos found" (empty search is a valid
    zero-result, not a service failure — mirrors the Firecrawl "do NOT trip on
    404/403/200-no-price" rule).

All HTTP + Redis mocked; zero live spend.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("YOUTUBE_API_KEY", "test-yt-key")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Reuse the fixture-style helpers from the main service test module.
from tests.test_youtube_service import (
    _search_response, _videos_response, _FakeResponse, _mock_client,
)


@pytest.fixture(autouse=True)
def _no_live_cache():
    with patch("app.services.youtube_service.get_cached", return_value=None), \
         patch("app.services.youtube_service.set_cached", return_value=True):
        yield


@pytest.mark.asyncio
async def test_breaker_open_returns_none_no_http_call():
    """Circuit OPEN for youtube -> immediate None, NO http call, NO quota."""
    import app.services.youtube_service as yt

    cm, client = _mock_client(AsyncMock())
    with patch("app.services.youtube_service.is_circuit_closed", return_value=False), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    assert out is None
    client.get.assert_not_called()


@pytest.mark.asyncio
async def test_breaker_open_does_not_consume_quota():
    """Belt-and-braces: when the breaker is open we must not even reach the
    daily-quota check-and-increment."""
    import app.services.youtube_service as yt

    consume = MagicMock(return_value=True)
    cm, _ = _mock_client(AsyncMock())
    with patch("app.services.youtube_service.is_circuit_closed", return_value=False), \
         patch("app.services.youtube_service.try_consume_youtube_credit", new=consume), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    consume.assert_not_called()


@pytest.mark.asyncio
async def test_service_failure_records_failure():
    """A raised exception from the API call = service-level failure -> trips the
    breaker via record_failure('youtube')."""
    import app.services.youtube_service as yt

    async def boom(url, params=None, **kw):
        raise RuntimeError("youtube api 503")

    rec_fail = MagicMock()
    cm, _ = _mock_client(boom)
    with patch("app.services.youtube_service.is_circuit_closed", return_value=True), \
         patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.record_failure", new=rec_fail), \
         patch("app.services.youtube_service.record_success"), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    assert out is None
    rec_fail.assert_called_once_with("youtube")


@pytest.mark.asyncio
async def test_success_records_success():
    """A fully successful fetch records success (resets failure count)."""
    import app.services.youtube_service as yt

    async def get(url, params=None, **kw):
        if "search" in url:
            return _FakeResponse(_search_response(["v1"]))
        return _FakeResponse(_videos_response({"v1": (9_000, 100, 50)}))

    rec_ok = MagicMock()
    rec_fail = MagicMock()
    cm, _ = _mock_client(get)
    with patch("app.services.youtube_service.is_circuit_closed", return_value=True), \
         patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.record_success", new=rec_ok), \
         patch("app.services.youtube_service.record_failure", new=rec_fail), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    assert out is not None
    rec_ok.assert_called_once_with("youtube")
    rec_fail.assert_not_called()


@pytest.mark.asyncio
async def test_no_videos_found_is_not_a_failure():
    """Empty search result = valid zero, NOT a service failure -> no
    record_failure (Firecrawl 'do not trip on 404/no-result' rule)."""
    import app.services.youtube_service as yt

    async def get(url, params=None, **kw):
        return _FakeResponse({"items": []})  # search finds nothing

    rec_fail = MagicMock()
    rec_ok = MagicMock()
    cm, _ = _mock_client(get)
    with patch("app.services.youtube_service.is_circuit_closed", return_value=True), \
         patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.record_failure", new=rec_fail), \
         patch("app.services.youtube_service.record_success", new=rec_ok), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Nope", "XYZ", None, "other")

    assert out is None
    rec_fail.assert_not_called()  # zero result is not a failure
    rec_ok.assert_not_called()    # nor a "success" worth resetting the breaker
