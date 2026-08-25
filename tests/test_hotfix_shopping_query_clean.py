"""
Bundle C HOTFIX-2 round 2 regression — strip operator-style tail noise
from Serper Shopping queries.

Root cause (team-lead T+~50min diagnosis):
  PRODUCT_PARSER_PROMPT tells GPT to emit an "optimized search query
  for price searches", so GPT appends "price" (and sometimes "buy",
  country names, currency codes). These trailing tokens cause Google
  Shopping to return ZERO items even when the underlying product is
  popular. Direct curl proves it:
    q="Apple iPhone 16 price" gl=us → 0 items
    q="iPhone 16"             gl=us → 20 items

Fix: defensive strip at search_product_prices entry, plus prompt
update at extraction_service.py PRODUCT_PARSER_PROMPT.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.serper_service import (
    _clean_shopping_query,
    search_product_prices,
)


# #60 — this module asserts QUERY-CLEANING behaviour, not budget behaviour.
# Stub the Redis counter read so the serper budget gate is deterministically
# OPEN and no assertion here depends on the live Upstash lifetime counter.
@pytest.fixture(autouse=True)
def _budget_gate_open():
    from app.services import api_budget_service

    with patch.object(api_budget_service, "_redis_get", return_value=None):
        yield


@pytest.fixture(autouse=True)
def _clean_shopping_primary_allowlist(monkeypatch):
    monkeypatch.delenv("SERPER_SHOPPING_PRIMARY_COUNTRIES", raising=False)


class TestCleanShoppingQuery:
    """Pure-function regression for the defensive cleaner."""

    def test_strips_trailing_price(self):
        assert _clean_shopping_query("Apple iPhone 16 price") == "Apple iPhone 16"

    def test_passthrough_clean_query(self):
        assert _clean_shopping_query("iPhone 16") == "iPhone 16"

    def test_preserves_product_essentials(self):
        # "Pro" and "Max" are NOT in the noise list — they are part of
        # the product name and MUST be preserved.
        assert _clean_shopping_query("iPhone 16 Pro Max") == "iPhone 16 Pro Max"
        assert _clean_shopping_query("iPhone 16 Pro") == "iPhone 16 Pro"

    def test_strips_multiple_trailing_tokens(self):
        assert _clean_shopping_query("iPhone 16 Pro buy best price") == "iPhone 16 Pro"

    def test_strips_country_currency_pollution(self):
        assert (
            _clean_shopping_query("Samsung Galaxy S24 price Bahrain BHD buy")
            == "Samsung Galaxy S24"
        )
        assert (
            _clean_shopping_query("NOW Foods Vitamin D3 5000 IU price Saudi Arabia SAR")
            == "NOW Foods Vitamin D3 5000 IU"
        )

    def test_strips_retailer_pollution(self):
        assert (
            _clean_shopping_query("Centrum buy on sale amazon noon") == "Centrum"
        )

    def test_idempotent(self):
        # Calling twice = calling once.
        q = "Samsung Galaxy S24 price Bahrain BHD buy"
        once = _clean_shopping_query(q)
        twice = _clean_shopping_query(once)
        assert once == twice == "Samsung Galaxy S24"

    def test_empty_input(self):
        assert _clean_shopping_query("") == ""

    def test_all_noise_input_returns_original(self):
        # If the query is ENTIRELY noise we keep the original rather
        # than send Serper an empty query (no Serper credits wasted on
        # a guaranteed-empty call upstream still happens, but the
        # function contract is non-empty in → non-empty out).
        assert _clean_shopping_query("price") == "price"

    def test_case_insensitive(self):
        assert (
            _clean_shopping_query("iPhone 16 PRICE BUY") == "iPhone 16"
        )


class TestSearchProductPricesIntegration:
    """Verify the cleaner is wired at search_product_prices entry so the
    Serper Shopping call gets the cleaned string, not the GPT-emitted
    dirty one."""

    @pytest.mark.asyncio
    async def test_cleaner_runs_before_serper_call(self, monkeypatch):
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        import importlib
        from app.services import serper_service
        importlib.reload(serper_service)

        observed_queries = []

        async def fake_do_serper(product, gl):
            observed_queries.append((product, gl))
            return {"shopping": [{"title": "iPhone 16", "price": "$799"}]}

        monkeypatch.setattr(serper_service, "_do_serper_shopping", fake_do_serper)

        result = await serper_service.search_product_prices(
            "Apple iPhone 16 price", country="bh"
        )

        # Cleaned query must hit Serper, not the dirty one. (#60 drops the
        # always-empty gl=<gcc> primary by default, so gl=us is the leg that
        # fires; the CLEANING contract under test is per-call and unchanged.)
        assert observed_queries, "no Serper shopping call fired"
        assert all(p == "Apple iPhone 16" for p, _gl in observed_queries)
        assert ("Apple iPhone 16", "us") in observed_queries
        # Output query field also reflects cleaned form (helpful for
        # downstream cache keys).
        assert result["query"] == "Apple iPhone 16"

    @pytest.mark.asyncio
    async def test_clean_query_passes_through_unchanged(self, monkeypatch):
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        import importlib
        from app.services import serper_service
        importlib.reload(serper_service)

        observed_queries = []

        async def fake_do_serper(product, gl):
            observed_queries.append((product, gl))
            return {"shopping": [{"title": "iPhone 16 Pro Max", "price": "$1199"}]}

        monkeypatch.setattr(serper_service, "_do_serper_shopping", fake_do_serper)

        await serper_service.search_product_prices(
            "iPhone 16 Pro Max", country="bh"
        )

        # No mutation — Pro/Max preserved on every fired call. (#60: gl=us is
        # the single default leg for a GCC country.)
        assert observed_queries, "no Serper shopping call fired"
        assert all(p == "iPhone 16 Pro Max" for p, _gl in observed_queries)
        assert ("iPhone 16 Pro Max", "us") in observed_queries

    @pytest.mark.asyncio
    async def test_us_fallback_uses_cleaned_query(self, monkeypatch):
        """When GCC primary is empty + us_fallback fires, the fallback
        call must ALSO get the cleaned string (not the dirty GPT one).

        #60 made the gl=<gcc> primary opt-in, so this two-leg scenario is
        reached via the SERPER_SHOPPING_PRIMARY_COUNTRIES rollback flip."""
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("SERPER_SHOPPING_PRIMARY_COUNTRIES", "bh")
        import importlib
        from app.services import serper_service
        importlib.reload(serper_service)

        observed_queries = []

        async def fake_do_serper(product, gl):
            observed_queries.append((product, gl))
            if gl == "bh":
                return {"shopping": []}  # GCC empty
            return {"shopping": [{"title": "iPhone 16", "price": "$799"}]}  # US fallback hits

        monkeypatch.setattr(serper_service, "_do_serper_shopping", fake_do_serper)

        result = await serper_service.search_product_prices(
            "Apple iPhone 16 price Bahrain BHD",
            country="bh",
        )

        # Both calls saw the cleaned string. (Order is non-deterministic since the
        # 2026-06-27 starvation fix fires gl=bh + gl=us concurrently — assert as a
        # set, not an ordered list.)
        assert set(observed_queries) == {
            ("Apple iPhone 16", "bh"),
            ("Apple iPhone 16", "us"),
        }
        assert result["shopping_region"] == "us_fallback"
        assert len(result["shopping"]) == 1


class TestExtractionPromptHardened:
    """Negative-assertion regression — the GPT prompt must NOT instruct
    the model to append 'price' or similar operator-style tokens."""

    def test_prompt_forbids_price_suffix(self):
        from app.services import extraction_service
        prompt = extraction_service.PRODUCT_PARSER_PROMPT
        # Negative: the old guidance must be gone.
        assert "optimized search query for this product" not in prompt
        assert "search_query should be specific for price searches" not in prompt
        # Positive: explicit DO-NOT directive present.
        assert "DO NOT add words like 'price'" in prompt
        # Worked example present so GPT has a pattern to copy.
        assert "iPhone 16 Pro 256GB" in prompt
