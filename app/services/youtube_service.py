"""YouTube Service — Bundle B S3 L2.

A CITED review signal sourced from the YouTube Data API v3. NOT a price or
spec source — it answers "how much real-world review attention does this
product have, and what's the top review video?" so the reviews section can
surface a cited line like "1.2k YouTube reviews — Channel X".

Two API calls per product (cache-miss only):
  1. search.list (type=video) — find the top product-review videos.
     Quota cost 100 units (the expensive one — capped hard by the daily guard).
  2. videos.list (part=statistics,snippet) — batched read of viewCount /
     likeCount / commentCount for those video IDs. Quota cost 1 unit.
     NOTE: the statistics fields come back as JSON STRINGS ("1048576").

Design contract (mirrors the S2 I2.5 consult skeleton + the curl_cffi
graceful-None pattern):
  - Budget-gated: try_consume_youtube_credit() guards the expensive search.list
    BEFORE any HTTP call; record_usage("youtube") meters on success.
  - Cached 14d (review signals are stable) — a cache hit spends zero quota.
  - Returns a dict on hit, None on miss / error / no-key / budget-exhausted.
    NEVER raises — any failure yields None so the reviews race degrades
    gracefully (the caller wraps this in asyncio.wait_for + treats None as
    "no YouTube signal").
  - NEVER critical-path: a slow or failed call drops out without affecting
    price / specs / the persisted review extraction.

Privacy: video titles + public counts only — no user data ever touches this.
"""
import os
import logging
from typing import Optional, Dict, Any, List

import httpx

from app.services.cache_service import get_cached, set_cached
from app.services.api_budget_service import (
    has_budget,
    record_usage,
    try_consume_youtube_credit,
)

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"

# 14d cache — a product's review-video landscape barely shifts day to day, and
# the search.list call is the single most expensive external unit in the whole
# pipeline (100 quota units) so we cache aggressively.
YOUTUBE_CACHE_TTL = 14 * 24 * 60 * 60

# How many top videos to pull stats for. 5 keeps the videos.list payload small
# and the aggregate engagement representative without over-counting long-tail
# noise. search.list maxResults is capped here too.
_TOP_N_VIDEOS = 5

# Per-call HTTP timeout. Short — this is a best-effort enrichment, never
# critical-path; the reviews-race wait_for cap is the real ceiling, this just
# stops a single hung socket from sitting at the OS default.
_HTTP_TIMEOUT = 6.0


def _cache_key(brand: str, name: str, variant: Optional[str], category: str) -> str:
    parts = [brand or "", name or "", variant or "", category or ""]
    return "youtube_review_signal:" + "|".join(p.strip().lower() for p in parts)


def _to_int(value: Any) -> int:
    """YouTube statistics fields are JSON strings ("1048576"); some are absent
    when the uploader disables likes/comments. Coerce safely to int, defaulting
    absent / malformed to 0 — never raises."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


async def _search_review_videos(query: str) -> List[str]:
    """search.list (type=video) → up to _TOP_N_VIDEOS videoIds, most-relevant
    first. Returns [] on error / empty. Records the 100-unit usage on success."""
    params = {
        "key": YOUTUBE_API_KEY,
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": _TOP_N_VIDEOS,
        "order": "relevance",
        "relevanceLanguage": "en",
    }
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.get(f"{YOUTUBE_BASE_URL}/search", params=params)
        resp.raise_for_status()
        # search.list = 100 units. Meter it on success only (HTTP 200).
        record_usage("youtube", count=100)
        data = resp.json()

    ids: List[str] = []
    for item in (data.get("items") or []):
        vid = (item.get("id") or {}).get("videoId")
        if vid:
            ids.append(vid)
    return ids


async def _video_stats(video_ids: List[str]) -> List[Dict[str, Any]]:
    """videos.list (part=statistics,snippet) — ONE batched call for all IDs.
    Returns a list of {video_id, title, channel, views, likes, comments}.
    Records the 1-unit usage on success."""
    if not video_ids:
        return []
    params = {
        "key": YOUTUBE_API_KEY,
        "part": "statistics,snippet",
        "id": ",".join(video_ids),
        "maxResults": _TOP_N_VIDEOS,
    }
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.get(f"{YOUTUBE_BASE_URL}/videos", params=params)
        resp.raise_for_status()
        record_usage("youtube", count=1)  # videos.list = 1 unit
        data = resp.json()

    out: List[Dict[str, Any]] = []
    for item in (data.get("items") or []):
        stats = item.get("statistics") or {}
        snippet = item.get("snippet") or {}
        out.append({
            "video_id": item.get("id", ""),
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "views": _to_int(stats.get("viewCount")),
            "likes": _to_int(stats.get("likeCount")),
            "comments": _to_int(stats.get("commentCount")),
        })
    return out


async def fetch_youtube_review_signal(
    brand: str,
    name: str,
    variant: Optional[str],
    category: str,
) -> Optional[Dict[str, Any]]:
    """Fetch a cited YouTube review signal for one product.

    Returns
        {review_count_signal, top_video_title, top_channel, video_url,
         total_views, video_count}
    or None on miss / error / no-key / budget-exhausted. NEVER raises.

    review_count_signal = aggregate comment count across the top videos — a
    proxy for "how many people are actively reviewing/discussing this." Views
    are surfaced separately (total_views) for the "N YouTube reviews" copy.
    """
    if not YOUTUBE_API_KEY:
        logger.info("[YOUTUBE] no YOUTUBE_API_KEY — skipping signal")
        return None

    cache_key = _cache_key(brand, name, variant, category)
    cached = get_cached(cache_key)
    if cached and isinstance(cached, dict):
        return cached

    # Budget guard BEFORE the expensive search.list (100 units). This is the
    # check-and-increment for the daily YouTube quota — fail-open on Redis down
    # (we'd rather spend a unit than silently lose the signal), hard-stop when
    # the daily cap is hit. has_budget("youtube") is a secondary belt-and-braces
    # check (lifetime/daily ceiling) consistent with the other providers.
    if not try_consume_youtube_credit():
        logger.info("[YOUTUBE] daily quota exhausted — skipping signal")
        return None
    if not has_budget("youtube"):
        logger.info("[YOUTUBE] youtube budget exhausted — skipping signal")
        return None

    query = f"{brand} {name} {variant or ''} review".strip()

    try:
        video_ids = await _search_review_videos(query)
        if not video_ids:
            # Nothing found — do NOT spend the videos.list unit. Return None.
            return None
        stats = await _video_stats(video_ids)
    except Exception as e:  # noqa: BLE001 — best-effort; any failure → None
        logger.warning("[YOUTUBE] signal fetch failed for %r: %s", query, e)
        return None

    if not stats:
        return None

    # Top video = most-viewed of the pulled set (the canonical "review everyone
    # watched"). Aggregate engagement across all pulled videos.
    top = max(stats, key=lambda s: s["views"])
    total_views = sum(s["views"] for s in stats)
    total_comments = sum(s["comments"] for s in stats)

    signal = {
        "review_count_signal": total_comments,
        "top_video_title": top["title"],
        "top_channel": top["channel"],
        "video_url": f"https://www.youtube.com/watch?v={top['video_id']}",
        "total_views": total_views,
        "video_count": len(stats),
    }

    set_cached(cache_key, signal, YOUTUBE_CACHE_TTL)
    return signal
