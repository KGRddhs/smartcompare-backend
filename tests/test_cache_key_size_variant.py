"""Phase 1 Task 1.4 — fairness-correct cache keys.

F1.4: two SIZE/STORAGE variants of the same product must NOT collide on one
price cache key — otherwise an "iPhone 15 128GB" price pollutes the "iPhone 15
256GB" slot (the wrong-fairness symptom). The electronics prod fixture proved
storage often lands in the SPECS, with `variant=None` on the product — so the
plain (brand,name,variant,region) key collapses both storage tiers today.

`size_variant_token(text)` extracts a stable normalized size/variant token
(storage GB, fragrance ml, supplement count, weight/volume) from a product's
identity text, reusing the same unit extractors `CATEGORY_FAIRNESS` uses. The
price cache key folds that token in so distinct sizes get distinct keys, while
two listings of the SAME size still share a key (cache hits preserved).
"""

import pytest

from app.services.price_service import (
    size_variant_token,
    build_size_aware_price_cache_key,
)


# ------------------------------------------------------- the token itself ---

class TestSizeVariantToken:
    def test_storage_gb_token(self):
        assert size_variant_token("iPhone 15 256GB") == "256gb"

    def test_storage_tb_normalized_to_gb(self):
        # 1TB == 1024GB — normalized so "1TB" and "1024GB" map to one token.
        assert size_variant_token("MacBook Pro 1TB") == size_variant_token("MacBook Pro 1024GB")

    def test_distinct_storage_distinct_token(self):
        assert size_variant_token("iPhone 15 256GB") != size_variant_token("iPhone 15 128GB")

    def test_fragrance_ml_token(self):
        assert size_variant_token("Tom Ford Ombré Leather 100ml") == "100ml"

    def test_distinct_ml_distinct_token(self):
        assert size_variant_token("Creed Aventus 50ml") != size_variant_token("Creed Aventus 100ml")

    def test_supplement_count_token(self):
        # Count-only listing (no GB/ml/weight) → count token.
        assert size_variant_token("NOW Foods Vitamin D3 240 softgels") == "240ct"

    def test_no_size_returns_empty(self):
        # No size mention anywhere → empty token (key falls back to identity only).
        assert size_variant_token("Sony WH-1000XM5") == ""

    def test_empty_and_none_safe(self):
        assert size_variant_token("") == ""
        assert size_variant_token(None) == ""

    def test_token_is_case_insensitive(self):
        assert size_variant_token("iPhone 15 256GB") == size_variant_token("iphone 15 256gb")


# ------------------------------------------------ the size-aware cache key ---

class TestSizeAwarePriceCacheKey:
    def test_storage_variants_get_distinct_keys(self):
        k256 = build_size_aware_price_cache_key("Apple", "iPhone 15", None, "bahrain", "iPhone 15 256GB")
        k128 = build_size_aware_price_cache_key("Apple", "iPhone 15", None, "bahrain", "iPhone 15 128GB")
        assert k256 != k128

    def test_same_size_same_key(self):
        # Two callers for the same size (token in name vs in search_query) must
        # produce the SAME key so genuine cache hits are preserved.
        k_a = build_size_aware_price_cache_key("Apple", "iPhone 15 256GB", None, "bahrain", "")
        k_b = build_size_aware_price_cache_key("Apple", "iPhone 15", None, "bahrain", "iPhone 15 256GB")
        assert k_a == k_b

    def test_fragrance_sizes_distinct(self):
        k50 = build_size_aware_price_cache_key("Creed", "Aventus", None, "bahrain", "Creed Aventus 50ml")
        k100 = build_size_aware_price_cache_key("Creed", "Aventus", None, "bahrain", "Creed Aventus 100ml")
        assert k50 != k100

    def test_no_size_matches_plain_key(self):
        # When NO size is present, the size-aware key must equal the legacy
        # plain key — backward compatible, no cache-warm invalidation for
        # sizeless products.
        from app.services.extraction_service import get_price_cache_key
        plain = get_price_cache_key("Sony", "WH-1000XM5", None, "bahrain")
        aware = build_size_aware_price_cache_key("Sony", "WH-1000XM5", None, "bahrain", "Sony WH-1000XM5")
        assert aware == plain

    def test_region_still_separates(self):
        k_bh = build_size_aware_price_cache_key("Apple", "iPhone 15", None, "bahrain", "iPhone 15 256GB")
        k_uae = build_size_aware_price_cache_key("Apple", "iPhone 15", None, "uae", "iPhone 15 256GB")
        assert k_bh != k_uae

    def test_key_prefix_is_price(self):
        k = build_size_aware_price_cache_key("Apple", "iPhone 15", None, "bahrain", "iPhone 15 256GB")
        assert k.startswith("price:")
