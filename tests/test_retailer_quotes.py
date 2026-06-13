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


# ---------------------------------------------------------------------------
# L5.1 (Bundle B S3) — Serper budget double-count
# ---------------------------------------------------------------------------
# Carried bug (S2 leak ledger §5, "dormant"): fetch_retailer_quotes() called
# record_usage("serper") manually AFTER search_web(), but search_web already
# records the budget meter internally on success (serper_service.py:94). So
# every successful retailer Serper call was metered TWICE against the
# 2200-credit lifetime budget — identical to the F4/G2 bug that was fixed in
# the sibling fetch_review_source_snippets (commit 9ee695c). 3 retailers x 2
# products = 6 calls per compare → the budget burns at 2x the real rate, which
# would silently false-trip the 80%-burn alert + lifetime ceiling.
#
# The pre-existing tests below mocked search_web AWAY (so the internal meter
# never fired) and asserted the MANUAL call — they encoded the buggy behavior.
# F4's fix contract: search_web OWNS the budget meter; fetch_retailer_quotes
# must NOT call record_usage itself. track_serper_cost_fn (the separate
# per-request cost tracker, not the budget meter) stays.


@pytest.mark.asyncio
async def test_fetch_does_not_double_count_serper_budget():
    """L5.1 — fetch_retailer_quotes must NOT call record_usage itself.

    search_web records the budget meter internally on success
    (serper_service.py:94). A manual record_usage("serper") here would
    double-count every credit. This test spies record_usage as imported into
    review_service and asserts it is NEVER called from the quote fetcher — the
    meter is owned by search_web exactly once per real call.
    """
    record_usage_calls = []

    async def fake_search_web(query, num_results=5):
        # Stands in for search_web's success path WITHOUT its internal meter,
        # so any record_usage we observe here is the (buggy) manual call.
        return {"organic": [{"title": "x", "snippet": "x" * 30}]}

    def spy_record_usage(provider, count=1):
        record_usage_calls.append((provider, count))

    with patch(
        "app.services.review_service.has_budget", return_value=True,
    ), patch(
        "app.services.review_service.record_usage", side_effect=spy_record_usage,
    ), patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ):
        quotes = await fetch_retailer_quotes("Apple", "iPhone 15", None)

        # 3 successful retailer searches still produce quotes...
        assert len(quotes) == 3
        # ...but the budget meter is NOT double-incremented here. search_web
        # owns it; fetch_retailer_quotes adds zero manual records.
        assert record_usage_calls == [], (
            "fetch_retailer_quotes double-counted the Serper budget: "
            f"search_web already meters internally, manual calls={record_usage_calls}"
        )


# ---------------------------------------------------------------------------
# B0-C-2 — has_budget("serper") gate
# ---------------------------------------------------------------------------
# Security + ops audit MED #4: fetch_retailer_quotes() fires 3 Serper site-
# filter calls per product (Amazon/Noon/X), 6 per compare. Unconditional. If
# any future caller activates this in the hot path, the 2200-credit lifetime
# Serper quota drains in ~2 days at 200 cache-miss compares/day. The fix
# gates each call behind `has_budget("serper")`; the budget DECREMENT is owned
# by search_web's internal record_usage (serper_service.py:94) — NOT a manual
# call here (L5.1: a manual call double-counts).
#
# Invariant pinned: when has_budget returns False (quota exhausted), zero
# Serper calls happen and the function returns [] cleanly — no partial
# results, no exception, no Sentry noise.


@pytest.mark.asyncio
async def test_fetch_returns_empty_when_serper_budget_exhausted():
    """All 3 Serper site-searches return None when has_budget('serper') == False."""
    fake_search = AsyncMock()
    fake_record_usage = AsyncMock()

    with patch(
        "app.services.review_service.has_budget", return_value=False,
    ), patch(
        "app.services.review_service.record_usage", new=fake_record_usage,
    ), patch(
        "app.services.review_service.search_web", new=fake_search,
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ):
        quotes = await fetch_retailer_quotes("Apple", "iPhone 15", None)

        assert quotes == []
        fake_search.assert_not_called()
        fake_record_usage.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_delegates_budget_meter_to_search_web_on_success():
    """L5.1 — the budget meter is owned by search_web, not fetch_retailer_quotes.

    Was `test_fetch_records_usage_after_each_successful_serper_call` (asserted
    3 MANUAL record_usage calls — the double-count bug). search_web records the
    meter internally on success (serper_service.py:94), so the quote fetcher
    must add ZERO manual records even when all 3 retailers succeed.
    """
    record_usage_calls = []

    async def fake_search_web(query, num_results=5):
        return {"organic": [{"title": "x", "snippet": "x" * 30}]}

    def fake_record_usage(provider, count=1):
        record_usage_calls.append((provider, count))

    with patch(
        "app.services.review_service.has_budget", return_value=True,
    ), patch(
        "app.services.review_service.record_usage", side_effect=fake_record_usage,
    ), patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ):
        await fetch_retailer_quotes("Apple", "iPhone 15", None)

        assert record_usage_calls == []


@pytest.mark.asyncio
async def test_fetch_failed_serper_call_records_no_budget():
    """When a Serper site-search raises, no budget record happens for it.

    Was `test_fetch_failed_serper_call_does_not_record_usage` (asserted 2
    manual records). Post-L5.1, fetch_retailer_quotes never records manually;
    search_web only meters after raise_for_status() (so a raising call is never
    metered there either). Net: zero manual records regardless of outcome.
    """
    record_usage_calls = []

    async def fake_search_web(query, num_results=5):
        if "noon.com" in query:
            raise RuntimeError("serper 503")
        return {"organic": [{"title": "x", "snippet": "x" * 30}]}

    def fake_record_usage(provider, count=1):
        record_usage_calls.append((provider, count))

    with patch(
        "app.services.review_service.has_budget", return_value=True,
    ), patch(
        "app.services.review_service.record_usage", side_effect=fake_record_usage,
    ), patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ):
        await fetch_retailer_quotes("Apple", "iPhone 15", None)

        # fetch_retailer_quotes adds zero manual records (the bug was a manual
        # record_usage per successful call → double-count).
        assert record_usage_calls == []
