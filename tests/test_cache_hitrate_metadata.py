"""Phase 1 Task 1.6 — cache hit-rate observability.

Response `metadata` carries:
  - `cache_hit`: True iff ANY product's price was served from cache (_cached).
  - `genuine_from_cache`: True iff a GENUINE-BH price was served from cache —
    the dial that proves the warmer is doing its job (genuine prices served at
    $0 instead of re-scraped).

`_compute_cache_observability(product_data)` is the pure helper, tested in
isolation. The eval/admin layer aggregates these counters separately
(record_price_outcome / get_real_price_coverage already exist on /admin/costs;
this adds the per-RESPONSE cache signal).
"""

import pytest

from app.services.response_builder import _compute_cache_observability


def _pd(amount, source_method, cached):
    return {"price": {"amount": amount, "source_method": source_method, "_cached": cached}}


class TestCacheObservability:
    def test_genuine_from_cache_true(self):
        pd = [_pd(80.0, "page_scrape_jsonld", True), _pd(95.0, "local_bhd", True)]
        obs = _compute_cache_observability(pd)
        assert obs["cache_hit"] is True
        assert obs["genuine_from_cache"] is True

    def test_cache_hit_but_not_genuine(self):
        # Both served from cache, but converted/estimated → cache_hit yes,
        # genuine_from_cache no.
        pd = [_pd(85.0, "converted_usd", True), _pd(70.0, "estimated", True)]
        obs = _compute_cache_observability(pd)
        assert obs["cache_hit"] is True
        assert obs["genuine_from_cache"] is False

    def test_genuine_but_fresh_not_from_cache(self):
        # A genuine price freshly scraped (_cached False) is NOT genuine_from_cache.
        pd = [_pd(80.0, "page_scrape_jsonld", False), _pd(95.0, "local_bhd", False)]
        obs = _compute_cache_observability(pd)
        assert obs["cache_hit"] is False
        assert obs["genuine_from_cache"] is False

    def test_mixed_one_cached_one_fresh(self):
        pd = [_pd(80.0, "local_bhd", True), _pd(95.0, "page_scrape_jsonld", False)]
        obs = _compute_cache_observability(pd)
        assert obs["cache_hit"] is True
        assert obs["genuine_from_cache"] is True  # the cached one is genuine

    def test_cached_genuine_plus_cached_converted(self):
        pd = [_pd(80.0, "local_bhd", True), _pd(85.0, "converted_usd", True)]
        obs = _compute_cache_observability(pd)
        assert obs["cache_hit"] is True
        assert obs["genuine_from_cache"] is True

    def test_no_prices(self):
        obs = _compute_cache_observability([{}, {}])
        assert obs["cache_hit"] is False
        assert obs["genuine_from_cache"] is False

    def test_empty_product_data(self):
        obs = _compute_cache_observability([])
        assert obs["cache_hit"] is False
        assert obs["genuine_from_cache"] is False

    def test_price_none_safe(self):
        obs = _compute_cache_observability([{"price": None}, {"price": None}])
        assert obs["cache_hit"] is False
        assert obs["genuine_from_cache"] is False

    def test_pending_price_cached_not_genuine(self):
        # A cached price-pending shape (no source_method) is a cache hit but not
        # genuine_from_cache.
        pd = [{"price": {"amount": None, "unavailable": True, "_cached": True}}]
        obs = _compute_cache_observability(pd)
        assert obs["cache_hit"] is True
        assert obs["genuine_from_cache"] is False


class TestMetadataIntegration:
    def test_keys_present_in_built_response_metadata(self):
        """The two keys appear in a built response's metadata block."""
        from app.services.response_builder import build_comparison_response
        product_data = [
            {
                "brand": "Apple", "name": "iPhone 15",
                "price": {"amount": 80.0, "currency": "BHD",
                          "source_method": "page_scrape_jsonld", "_cached": True},
                "specs": {"display": "6.1"}, "reviews": {},
            },
            {
                "brand": "Samsung", "name": "Galaxy S24",
                "price": {"amount": 95.0, "currency": "BHD",
                          "source_method": "local_bhd", "_cached": True},
                "specs": {"display": "6.2"}, "reviews": {},
            },
        ]
        comparison = {"winner_index": 0, "winner_declaration": "iPhone 15",
                      "winner_reason": "x", "specs_comparison": {}}
        resp = build_comparison_response(
            query="iPhone 15 vs Galaxy S24",
            product_data=product_data,
            comparison=comparison,
            scoring_result={},
            category_used="electronics",
            region="bahrain",
            elapsed_seconds=1.0,
            api_calls=0, total_cost=0.0, gpt_calls=0, serper_calls=0,
            from_cache=True,
        )
        meta = resp["metadata"]
        assert "cache_hit" in meta
        assert "genuine_from_cache" in meta
        assert meta["cache_hit"] is True
        assert meta["genuine_from_cache"] is True
