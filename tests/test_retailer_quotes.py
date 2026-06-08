"""L2.11 — Tests for the per-retailer review-quote fetcher.

`fetch_retailer_quotes()` runs 3 parallel Serper site-filtered searches
(Amazon, Noon, X) per product and returns up to 3 `{retailer, rating, text}`
quote dicts. Cached 14 days per product.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, patch

from app.services.review_service import (
    RETAILER_QUOTE_SITES,
    fetch_retailer_quotes,
)


def test_retailer_quote_sites_priority_ordering():
    """Amazon -> Noon -> X is the design priority."""
    labels = [name for name, _ in RETAILER_QUOTE_SITES]
    assert labels[:3] == ["Amazon", "Noon", "X"]


@pytest.mark.asyncio
async def test_fetch_returns_3_quotes_when_all_retailers_have_data():
    """All 3 site-filtered searches return at least one organic with a snippet
    long enough — caller gets 3 entries (rating may be None)."""

    async def fake_search_web(query, num_results=5):
        if "amazon.com" in query:
            return {
                "organic": [
                    {
                        "title": "iPhone 15 review",
                        "snippet": "Battery actually lasts a full day, even with heavy use.",
                        "richSnippet": {"top": {"detected_extensions": {"rating": 5}}},
                    }
                ]
            }
        if "noon.com" in query:
            return {
                "organic": [
                    {
                        "title": "Customer review",
                        "snippet": "Camera in low light is the best I've used at this price.",
                        "richSnippet": {"top": {"detected_extensions": {"rating": 4}}},
                    }
                ]
            }
        return {
            "organic": [
                {
                    "title": "tweet",
                    "snippet": "Switched from Android after 4 years. No regrets so far.",
                }
            ]
        }

    with patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ):
        quotes = await fetch_retailer_quotes("Apple", "iPhone 15", None)
        assert len(quotes) == 3
        assert {q["retailer"] for q in quotes} == {"Amazon", "Noon", "X"}
        amazon = next(q for q in quotes if q["retailer"] == "Amazon")
        assert amazon["rating"] == 5
        assert "Battery actually lasts" in amazon["text"]
        x = next(q for q in quotes if q["retailer"] == "X")
        assert x["rating"] is None  # No richSnippet
        assert len(x["text"]) > 20


@pytest.mark.asyncio
async def test_fetch_drops_short_snippets():
    """A snippet under 20 chars is too noisy to display — fetcher skips it."""

    async def fake_search_web(query, num_results=5):
        return {"organic": [{"title": "x", "snippet": "good"}]}  # <20 chars

    with patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ):
        quotes = await fetch_retailer_quotes("Apple", "iPhone 15", None)
        assert quotes == []


@pytest.mark.asyncio
async def test_fetch_uses_cache_on_hit():
    """When the per-product cache is warm, no Serper calls happen."""
    cached_quotes = [
        {"retailer": "Amazon", "rating": 5, "text": "x" * 30},
    ]

    fake_search = AsyncMock()
    with patch(
        "app.services.review_service.get_cached",
        return_value={"quotes": cached_quotes},
    ), patch(
        "app.services.review_service.search_web", new=fake_search,
    ):
        quotes = await fetch_retailer_quotes("Apple", "iPhone 15", None)
        assert quotes == cached_quotes
        fake_search.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_survives_one_retailer_failure():
    """If one Serper call fails, the other two still return quotes."""

    async def fake_search_web(query, num_results=5):
        if "noon.com" in query:
            raise RuntimeError("serper outage")
        return {
            "organic": [
                {"title": "review", "snippet": "x" * 30}
            ]
        }

    with patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ):
        quotes = await fetch_retailer_quotes("Apple", "iPhone 15", None)
        assert len(quotes) == 2  # Amazon + X, not Noon
        retailers = {q["retailer"] for q in quotes}
        assert "Noon" not in retailers


@pytest.mark.asyncio
async def test_fetch_calls_serper_cost_tracker_per_retailer():
    """Cost tracker fires once per successful retailer query, not per quote."""
    track_calls = []

    async def fake_search_web(query, num_results=5):
        return {"organic": [{"title": "x", "snippet": "x" * 30}]}

    def track():
        track_calls.append(1)

    with patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ):
        await fetch_retailer_quotes("Apple", "iPhone 15", None, track_serper_cost_fn=track)
        # 3 retailers, each one Serper call -> 3 tracked calls
        assert len(track_calls) == 3
