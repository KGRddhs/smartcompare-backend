"""L2.1 — youtube_service.fetch_youtube_review_signal()

YouTube Data API v3 client for a CITED review signal. Two calls:
  1. search.list (type=video) — find the top product-review videos.
  2. videos.list (part=statistics,snippet) — read viewCount / likeCount /
     commentCount for those video IDs (statistics fields are JSON STRINGS).

Returns a dict
  {review_count_signal, top_video_title, top_channel, video_url,
   total_views, video_count}
or None on miss / error / no key. NEVER raises. Mirrors the curl_cffi
graceful-None pattern + the S2 I2.5 consult skeleton (budget-gated, cached,
None-on-miss, never critical-path).

All tests MOCK httpx — zero live quota spend.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("YOUTUBE_API_KEY", "test-yt-key")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def _no_live_cache():
    """Isolate every test from a live Redis. fetch_youtube_review_signal does a
    get_cached() lookup BEFORE the budget/http logic — with a real .env (live
    Upstash) that would return a stale signal and mask the miss/error/budget
    paths these tests assert. Default get_cached->None + set_cached->no-op for
    the whole module; the two cache-specific tests re-patch get_cached inside
    their own `with` block, which takes precedence while active."""
    with patch("app.services.youtube_service.get_cached", return_value=None), \
         patch("app.services.youtube_service.set_cached", return_value=True):
        yield


# ---------------------------------------------------------------------------
# Realistic YouTube Data API v3 response fixtures (shapes verified against the
# official docs: search.list item = {id:{videoId}, snippet:{title,channelTitle,
# channelId,publishedAt}}; videos.list statistics fields are STRINGS).
# ---------------------------------------------------------------------------

def _search_response(video_ids):
    return {
        "kind": "youtube#searchListResponse",
        "items": [
            {
                "kind": "youtube#searchResult",
                "id": {"kind": "youtube#video", "videoId": vid},
                "snippet": {
                    "publishedAt": "2025-09-20T14:00:00Z",
                    "channelId": f"UC_{vid}",
                    "title": f"{vid} — Full Review After 30 Days",
                    "description": "Hands-on review.",
                    "channelTitle": f"Channel {vid}",
                },
            }
            for vid in video_ids
        ],
    }


def _videos_response(stats_by_id):
    """stats_by_id: {videoId: (viewCount, likeCount, commentCount)} as ints;
    rendered as the STRING-typed statistics the real API returns."""
    items = []
    for vid, (views, likes, comments) in stats_by_id.items():
        stats = {"viewCount": str(views)}
        if likes is not None:
            stats["likeCount"] = str(likes)
        if comments is not None:
            stats["commentCount"] = str(comments)
        items.append({
            "kind": "youtube#video",
            "id": vid,
            "snippet": {
                "title": f"{vid} — Full Review After 30 Days",
                "channelTitle": f"Channel {vid}",
                "publishedAt": "2025-09-20T14:00:00Z",
            },
            "statistics": stats,
        })
    return {"kind": "youtube#videoListResponse", "items": items}


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
        self.text = "ok"

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                "err", request=MagicMock(), response=MagicMock(status_code=self.status_code)
            )


def _mock_client(get_side_effect):
    """Build an async-context-manager mock for httpx.AsyncClient whose .get
    dispatches via get_side_effect(url, params)."""
    client = MagicMock()
    client.get = AsyncMock(side_effect=get_side_effect)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm, client


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_signal_with_top_video_and_counts():
    """search.list → 2 video IDs; videos.list → stats. The signal aggregates
    total views/comments and surfaces the TOP (most-viewed) video's title +
    channel + url."""
    import app.services.youtube_service as yt

    async def get(url, params=None, **kw):
        if "search" in url:
            return _FakeResponse(_search_response(["vidA", "vidB"]))
        if "videos" in url:
            return _FakeResponse(_videos_response({
                "vidA": (50_000, 1_200, 300),
                "vidB": (1_048_576, 40_000, 5_000),  # most-viewed → top
            }))
        return _FakeResponse({}, status_code=404)

    cm, _ = _mock_client(get)
    with patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    assert out is not None
    # Top video is the most-viewed (vidB).
    assert out["top_video_title"] == "vidB — Full Review After 30 Days"
    assert out["top_channel"] == "Channel vidB"
    assert out["video_url"] == "https://www.youtube.com/watch?v=vidB"
    # review_count_signal = aggregate engagement proxy (comments across videos).
    assert out["review_count_signal"] == 5_300  # 300 + 5000 comments
    assert out["total_views"] == 1_098_576
    assert out["video_count"] == 2


@pytest.mark.asyncio
async def test_missing_like_comment_counts_default_zero():
    """Some videos disable likes/comments → those stat keys are ABSENT. The
    aggregation must treat absent as 0, never KeyError."""
    import app.services.youtube_service as yt

    async def get(url, params=None, **kw):
        if "search" in url:
            return _FakeResponse(_search_response(["v1"]))
        return _FakeResponse(_videos_response({"v1": (9_000, None, None)}))

    cm, _ = _mock_client(get)
    with patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Sony", "WH-1000XM5", None, "electronics")

    assert out is not None
    assert out["review_count_signal"] == 0
    assert out["total_views"] == 9_000
    assert out["top_video_title"] == "v1 — Full Review After 30 Days"


# ---------------------------------------------------------------------------
# Miss / error / config — all return None, never raise
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_api_key_returns_none(monkeypatch):
    monkeypatch.setattr("app.services.youtube_service.YOUTUBE_API_KEY", None)
    out = await __import__("app.services.youtube_service", fromlist=["x"]).fetch_youtube_review_signal(
        "Apple", "iPhone 16", None, "electronics"
    )
    assert out is None


@pytest.mark.asyncio
async def test_search_returns_no_videos_returns_none():
    import app.services.youtube_service as yt

    async def get(url, params=None, **kw):
        if "search" in url:
            return _FakeResponse({"items": []})  # nothing found
        return _FakeResponse({"items": []})

    cm, client = _mock_client(get)
    with patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Nonexistent", "Product XYZ", None, "other")

    assert out is None
    # videos.list must NOT be called when search found nothing (save the 1 unit).
    assert client.get.call_count == 1


@pytest.mark.asyncio
async def test_http_error_returns_none_never_raises():
    import app.services.youtube_service as yt

    async def get(url, params=None, **kw):
        raise RuntimeError("youtube api down")

    cm, _ = _mock_client(get)
    with patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    assert out is None  # graceful — never raises


@pytest.mark.asyncio
async def test_budget_exhausted_returns_none_no_call():
    """When the YouTube daily quota guard says no, NO http call is made."""
    import app.services.youtube_service as yt

    cm, client = _mock_client(AsyncMock())
    with patch("app.services.youtube_service.try_consume_youtube_credit", return_value=False), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    assert out is None
    client.get.assert_not_called()  # zero quota spend when exhausted


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_hit_skips_api():
    import app.services.youtube_service as yt

    cached = {
        "review_count_signal": 5300, "top_video_title": "Cached Review",
        "top_channel": "Cached Channel",
        "video_url": "https://www.youtube.com/watch?v=cached",
        "total_views": 1_000_000, "video_count": 2,
    }
    cm, client = _mock_client(AsyncMock())
    with patch("app.services.youtube_service.get_cached", return_value=cached), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    assert out == cached
    client.get.assert_not_called()  # cache hit = zero quota


@pytest.mark.asyncio
async def test_cache_written_on_miss():
    import app.services.youtube_service as yt

    async def get(url, params=None, **kw):
        if "search" in url:
            return _FakeResponse(_search_response(["v1"]))
        return _FakeResponse(_videos_response({"v1": (9_000, 100, 50)}))

    set_calls = []
    cm, _ = _mock_client(get)
    with patch("app.services.youtube_service.get_cached", return_value=None), \
         patch("app.services.youtube_service.set_cached",
               side_effect=lambda k, v, ttl: set_calls.append((k, v, ttl))), \
         patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        out = await yt.fetch_youtube_review_signal("Apple", "iPhone 16", None, "electronics")

    assert out is not None
    assert set_calls, "result must be cached on a miss"
    key, value, ttl = set_calls[0]
    assert ttl == yt.YOUTUBE_CACHE_TTL == 14 * 24 * 60 * 60  # 14d


# ---------------------------------------------------------------------------
# Quota discipline: prefer videos.list (1u) — only ONE search.list per call
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exactly_one_search_and_one_videos_call():
    """Per design: ONE search.list (100u) + ONE batched videos.list (1u) — the
    video IDs are batched into a single videos.list, never one call per video."""
    import app.services.youtube_service as yt

    urls = []

    async def get(url, params=None, **kw):
        urls.append(url)
        if "search" in url:
            return _FakeResponse(_search_response(["a", "b", "c"]))
        return _FakeResponse(_videos_response({
            "a": (1, 1, 1), "b": (2, 2, 2), "c": (3, 3, 3),
        }))

    cm, _ = _mock_client(get)
    with patch("app.services.youtube_service.has_budget", return_value=True), \
         patch("app.services.youtube_service.record_usage"), \
         patch("app.services.youtube_service.try_consume_youtube_credit", return_value=True), \
         patch("app.services.youtube_service.httpx.AsyncClient", return_value=cm):
        await yt.fetch_youtube_review_signal("X", "Y", None, "electronics")

    search_calls = [u for u in urls if "search" in u]
    videos_calls = [u for u in urls if "videos" in u]
    assert len(search_calls) == 1
    assert len(videos_calls) == 1  # batched, not 3
