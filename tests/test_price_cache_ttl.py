"""Phase 1 Task 1.1 — long-TTL for genuine-BH prices.

LOCKED decisions (MANIFEST):
  - genuine-BH price cache TTL = 7 DAYS
  - estimated / converted / converted_fallback = 24h (unchanged)
  - negative-cache structural dead-ends = 30 DAYS (Task 1.3, covered here for the
    constant only; the sentinel behaviour lives in test_negative_cache_structural_gap.py)

The genuine source-method set is `_GENUINE_BH_SOURCE_METHODS` (kept in eval
parity by tests/test_eval_genuine_methods_parity.py). A price carrying one of
those methods is a real Bahrain shelf price worth caching for a week; a
converted/estimated figure is short-lived and keeps the 24h TTL so it refreshes
toward a genuine price sooner.

`price_cache_ttl(price)` is the single point that branches the TTL on
`source_method` — used at every price `set_cached` call site so the policy is
not duplicated across the ~12 cascade write points.
"""

import pytest

from app.services.price_service import (
    PRICE_CACHE_TTL,
    GENUINE_PRICE_CACHE_TTL,
    NEGATIVE_PRICE_CACHE_TTL,
    price_cache_ttl,
    _GENUINE_BH_SOURCE_METHODS,
)


# ------------------------------------------------------------- constants ---

class TestTTLConstants:
    def test_genuine_ttl_is_7_days(self):
        assert GENUINE_PRICE_CACHE_TTL == 7 * 24 * 60 * 60

    def test_short_ttl_is_24h(self):
        assert PRICE_CACHE_TTL == 24 * 60 * 60

    def test_negative_ttl_is_30_days(self):
        assert NEGATIVE_PRICE_CACHE_TTL == 30 * 24 * 60 * 60

    def test_genuine_ttl_strictly_longer_than_short(self):
        assert GENUINE_PRICE_CACHE_TTL > PRICE_CACHE_TTL


# ----------------------------------------------------- genuine → 7 days ---

class TestGenuineMethodsGetLongTTL:
    @pytest.mark.parametrize("method", sorted(_GENUINE_BH_SOURCE_METHODS))
    def test_every_genuine_method_caches_7d(self, method):
        price = {"amount": 80.0, "currency": "BHD", "source_method": method}
        assert price_cache_ttl(price) == GENUINE_PRICE_CACHE_TTL

    def test_local_bhd_caches_7d(self):
        price = {"amount": 244.99, "currency": "BHD", "source_method": "local_bhd"}
        assert price_cache_ttl(price) == GENUINE_PRICE_CACHE_TTL

    def test_page_scrape_jsonld_caches_7d(self):
        price = {"amount": 79.5, "currency": "BHD", "source_method": "page_scrape_jsonld"}
        assert price_cache_ttl(price) == GENUINE_PRICE_CACHE_TTL

    def test_shopify_json_caches_7d(self):
        price = {"amount": 399.0, "currency": "BHD", "source_method": "shopify_json"}
        assert price_cache_ttl(price) == GENUINE_PRICE_CACHE_TTL


# ----------------------------------------- converted / estimated → 24h ---

class TestNonGenuineMethodsKeepShortTTL:
    def test_converted_usd_keeps_24h(self):
        price = {"amount": 85.0, "currency": "BHD", "source_method": "converted_usd"}
        assert price_cache_ttl(price) == PRICE_CACHE_TTL

    def test_converted_fallback_keeps_24h(self):
        price = {"amount": 85.0, "currency": "BHD", "source_method": "converted_fallback"}
        assert price_cache_ttl(price) == PRICE_CACHE_TTL

    def test_estimated_keeps_24h(self):
        price = {"amount": 70.0, "currency": "BHD", "source_method": "estimated"}
        assert price_cache_ttl(price) == PRICE_CACHE_TTL

    def test_gpt_training_estimate_keeps_24h(self):
        price = {"amount": 70.0, "currency": "BHD", "source_method": "gpt_training_estimate"}
        assert price_cache_ttl(price) == PRICE_CACHE_TTL


# --------------------------------------------------------- robustness ---

class TestEdgeCases:
    def test_missing_source_method_keeps_short_ttl(self):
        # No method → not trustworthy as genuine → short TTL.
        assert price_cache_ttl({"amount": 80.0, "currency": "BHD"}) == PRICE_CACHE_TTL

    def test_none_price_keeps_short_ttl(self):
        assert price_cache_ttl(None) == PRICE_CACHE_TTL

    def test_empty_dict_keeps_short_ttl(self):
        assert price_cache_ttl({}) == PRICE_CACHE_TTL

    def test_non_dict_keeps_short_ttl(self):
        assert price_cache_ttl("local_bhd") == PRICE_CACHE_TTL

    def test_converted_substring_never_genuine(self):
        # Defense-in-depth: anything containing "converted" must not get 7d even
        # if a future method string sneaks the token in.
        price = {"amount": 85.0, "currency": "BHD", "source_method": "page_scrape_converted"}
        assert price_cache_ttl(price) == PRICE_CACHE_TTL

    def test_estimate_substring_never_genuine(self):
        price = {"amount": 85.0, "currency": "BHD", "source_method": "scrape_estimated"}
        assert price_cache_ttl(price) == PRICE_CACHE_TTL


# ----------------------------------------------- L2 (DB) freshness window ---
# The L2 price cache (product_data_service) must honor the same source_method
# policy: a genuine row stays fresh for 7d, a converted/estimated row for 24h.
# `_price_row_fresh(source_method, age)` is the pure freshness decision the
# async get_cached_price uses, tested without touching Supabase.

from datetime import timedelta

from app.services.product_data_service import (
    _price_row_fresh,
    PRICE_DB_TTL,
    GENUINE_PRICE_DB_TTL,
)


class TestL2FreshnessWindow:
    def test_genuine_db_ttl_is_7_days(self):
        assert GENUINE_PRICE_DB_TTL == timedelta(days=7)

    def test_short_db_ttl_is_1_day(self):
        assert PRICE_DB_TTL == timedelta(days=1)

    def test_genuine_row_3_days_old_is_fresh(self):
        # A genuine BH price 3 days old is still fresh under the 7d window —
        # the OLD flat-24h window would have wrongly rejected it (the bug).
        assert _price_row_fresh("page_scrape_jsonld", timedelta(days=3)) is True

    def test_genuine_row_8_days_old_is_stale(self):
        assert _price_row_fresh("local_bhd", timedelta(days=8)) is False

    def test_converted_row_3_days_old_is_stale(self):
        # A converted figure older than 24h is stale (refresh toward genuine).
        assert _price_row_fresh("converted_usd", timedelta(days=3)) is False

    def test_converted_row_12h_old_is_fresh(self):
        assert _price_row_fresh("converted_usd", timedelta(hours=12)) is True

    def test_estimated_row_2_days_old_is_stale(self):
        assert _price_row_fresh("estimated", timedelta(days=2)) is False

    def test_missing_method_uses_short_window(self):
        assert _price_row_fresh(None, timedelta(days=3)) is False
        assert _price_row_fresh(None, timedelta(hours=12)) is True
