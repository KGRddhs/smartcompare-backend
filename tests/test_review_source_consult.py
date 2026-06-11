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

from app.services.review_service import (
    consult_review_sources,
    fetch_review_source_snippets,
    passive_review_snippets,
    review_source_consult_mode,
)


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


# ---------------------------------------------------------------------------
# Flag + mode dispatcher (ENABLE_REVIEW_SOURCE_CONSULT)
# ---------------------------------------------------------------------------

def test_mode_off_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_REVIEW_SOURCE_CONSULT", raising=False)
    assert review_source_consult_mode() is None


@pytest.mark.parametrize("val,expected", [
    ("active", "active"), ("true", "active"), ("1", "active"), ("on", "active"),
    ("passive", "passive"),
    ("", None), ("nope", None), ("off", None),
])
def test_mode_parsing(monkeypatch, val, expected):
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", val)
    assert review_source_consult_mode() == expected


@pytest.mark.asyncio
async def test_consult_off_returns_empty_no_serper(monkeypatch):
    monkeypatch.delenv("ENABLE_REVIEW_SOURCE_CONSULT", raising=False)
    search_mock = AsyncMock()
    with patch("app.services.review_service.search_web", new=search_mock):
        out = await consult_review_sources(
            "Dior", "Sauvage", None, "fragrances",
            {"organic": [{"link": "https://gulfnews.com/x", "snippet": "x" * 40}]},
        )
    assert out == []
    search_mock.assert_not_called()  # OFF spends nothing


@pytest.mark.asyncio
async def test_consult_passive_reads_existing_organic(monkeypatch):
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", "passive")
    search_mock = AsyncMock()
    organic = {
        "organic": [
            {"link": "https://amazon.ae/p", "snippet": "A retailer listing, not a review source."},
            {"link": "https://www.gulfnews.com/beauty/article",
             "snippet": "Editorial: this foundation survived a humid Gulf afternoon beautifully."},
        ]
    }
    with patch("app.services.review_service.search_web", new=search_mock):
        out = await consult_review_sources(
            "Maybelline", "Fit Me", None, "makeup", organic,
        )
    assert len(out) == 1
    assert out[0]["domain"] == "gulfnews.com"  # only the review-source hit
    search_mock.assert_not_called()  # passive = zero extra Serper


def test_passive_helper_ignores_non_review_domains():
    organic = {"organic": [
        {"link": "https://noon.com/p", "snippet": "Retailer snippet long enough to pass."},
        {"link": "https://sayidaty.net/x", "snippet": "Review-source editorial snippet here."},
    ]}
    out = passive_review_snippets(organic, "makeup")
    assert len(out) == 1
    assert out[0]["domain"] == "sayidaty.net"


def test_passive_empty_for_non_review_category():
    organic = {"organic": [{"link": "https://gulfnews.com/x", "snippet": "x" * 40}]}
    # electronics has no usage="review" sources -> []
    assert passive_review_snippets(organic, "electronics") == []


@pytest.mark.asyncio
async def test_consult_active_dispatches_dedicated_call(monkeypatch):
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", "active")

    async def fake_search_web(query, num_results=6):
        return {"organic": [{"link": "https://sayidaty.net/a",
                             "snippet": "Active-mode dedicated fetch review snippet, long enough."}]}

    with patch(
        "app.services.review_service.search_web", new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ), patch(
        "app.services.review_service.has_budget", return_value=True,
    ), patch(
        "app.services.review_service.record_usage", return_value=None,
    ):
        out = await consult_review_sources(
            "Maybelline", "Fit Me", None, "makeup", None,
        )
    assert len(out) == 1
    assert out[0]["domain"] == "sayidaty.net"


@pytest.mark.asyncio
async def test_consult_active_timeout_yields_empty(monkeypatch):
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", "active")

    async def slow_fetch(*a, **k):
        import asyncio as _a
        await _a.sleep(5)
        return [{"domain": "x", "text": "y"}]

    with patch(
        "app.services.review_service.fetch_review_source_snippets", new=slow_fetch,
    ):
        out = await consult_review_sources(
            "X", "Y", None, "makeup", None, timeout=0.05,
        )
    assert out == []  # capped, never blocks
