"""S2 I2.5 — review-content consultation from usage="review" registry sources.

`fetch_review_source_snippets()` runs ONE Serper site-filtered search across
the category's review sources (the Arabic GCC sources for beauty/fashion).
Budget-gated, cached 14d, returns [] on miss — never raises, never
critical-path.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, patch

from app.services.review_service import fetch_review_source_snippets


@pytest.mark.asyncio
async def test_returns_snippets_from_review_sources():
    async def fake_search_web(query, num_results=6):
        # The query must target the Arabic review sources for a makeup product.
        assert "site:sayidaty.net" in query or "site:gulfnews.com" in query
        return {
            "organic": [
                {
                    "title": "Best foundations for Gulf summer",
                    "snippet": "This foundation held up through a humid Bahrain afternoon without sliding.",
                    "link": "https://www.sayidaty.net/beauty/foundations",
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
    ), patch(
        "app.services.review_service.has_budget", return_value=True,
    ), patch(
        "app.services.review_service.record_usage", return_value=None,
    ):
        snippets = await fetch_review_source_snippets(
            "Maybelline", "Fit Me Foundation", None, "makeup"
        )

    assert len(snippets) == 1
    assert snippets[0]["domain"] == "sayidaty.net"
    assert "humid" in snippets[0]["text"]


@pytest.mark.asyncio
async def test_empty_for_category_without_review_sources():
    """electronics has no usage='review' registry source → no Serper call,
    returns []."""
    search_mock = AsyncMock()
    with patch("app.services.review_service.search_web", new=search_mock):
        snippets = await fetch_review_source_snippets(
            "Apple", "iPhone 15", None, "electronics"
        )
    assert snippets == []
    search_mock.assert_not_called()  # never spends a Serper credit


@pytest.mark.asyncio
async def test_empty_when_budget_exhausted():
    """Budget guard: no Serper call when serper budget is exhausted."""
    search_mock = AsyncMock()
    with patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.has_budget", return_value=False,
    ), patch("app.services.review_service.search_web", new=search_mock):
        snippets = await fetch_review_source_snippets(
            "Dior", "Sauvage", None, "fragrances"
        )
    assert snippets == []
    search_mock.assert_not_called()


@pytest.mark.asyncio
async def test_serper_failure_returns_empty_never_raises():
    async def boom(query, num_results=6):
        raise RuntimeError("serper down")

    with patch(
        "app.services.review_service.search_web", new=AsyncMock(side_effect=boom),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.has_budget", return_value=True,
    ):
        snippets = await fetch_review_source_snippets(
            "Chanel", "No 5", None, "fragrances"
        )
    assert snippets == []  # graceful — never raises


@pytest.mark.asyncio
async def test_cache_hit_skips_serper():
    search_mock = AsyncMock()
    cached = {"snippets": [{"domain": "gulfnews.com", "text": "A long enough cached review snippet here."}]}
    with patch(
        "app.services.review_service.get_cached", return_value=cached,
    ), patch("app.services.review_service.search_web", new=search_mock):
        snippets = await fetch_review_source_snippets(
            "L'Oreal", "True Match", None, "makeup"
        )
    assert snippets == cached["snippets"]
    search_mock.assert_not_called()


@pytest.mark.asyncio
async def test_short_snippets_filtered_out():
    async def fake_search_web(query, num_results=6):
        return {
            "organic": [
                {"snippet": "Too short.", "link": "https://gulfnews.com/x"},
                {
                    "snippet": "A sufficiently detailed editorial note about long-wear performance in heat.",
                    "link": "https://gulfnews.com/beauty",
                },
            ]
        }

    with patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ), patch(
        "app.services.review_service.has_budget", return_value=True,
    ), patch(
        "app.services.review_service.record_usage", return_value=None,
    ):
        snippets = await fetch_review_source_snippets(
            "NARS", "Foundation", None, "makeup"
        )
    assert len(snippets) == 1
    assert "long-wear" in snippets[0]["text"]
