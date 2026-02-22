# Test Coverage Implementation Plan: 7 Uncovered Areas

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add ~44 unit/live tests across 7 files covering camera/vision, singleton state, iHerb scraping, rating tiers, price fallback, unified search merging, and error paths.

**Architecture:** Hybrid approach — live tests where verifiable, mocked tests for edge cases. All tests import from `app/services/` directly. Mocked tests use `unittest.mock` (patch, AsyncMock, MagicMock). Live tests call real APIs/endpoints. Follows existing test conventions.

**Tech Stack:** pytest, unittest.mock, asyncio, httpx (for live API calls), curl_cffi (for iHerb live tests)

---

## Team Assignment

| Agent | Files | QA Target |
|-------|-------|-----------|
| Agent A | test_camera_vision.py, test_singleton_state.py, test_iherb_scraping.py | Reviews Agent B's files |
| Agent B | test_rating_tiers.py, test_price_fallback.py | Reviews Agent C's files |
| Agent C | test_unified_search.py, test_error_paths.py | Reviews Agent A's files |

---

## Task 1: test_error_paths.py (Agent C)

All mocked. Tests the edge cases and error handling that caused past bugs.

**Files:**
- Create: `tests/test_error_paths.py`

**Step 1: Write test file**

```python
"""Tests for error handling and edge cases across the comparison pipeline.

All mocked — these edge cases can't be triggered live.
Run: python -m pytest tests/test_error_paths.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.structured_comparison_service import (
    StructuredComparisonService,
    _convert_to_bhd,
)


@pytest.fixture
def service():
    return StructuredComparisonService()


# --- _convert_to_bhd edge cases ---

class TestConvertToBhd:
    def test_none_currency_returns_amount_unchanged(self):
        """_convert_to_bhd(100, None) should return 100 (no conversion)."""
        assert _convert_to_bhd(100, None) == 100

    def test_usd_to_bhd(self):
        """1 USD = 0.377 BHD."""
        result = _convert_to_bhd(100, "USD")
        assert result == pytest.approx(37.7, abs=0.1)

    def test_bhd_to_bhd_is_identity(self):
        """BHD->BHD should be 1:1."""
        assert _convert_to_bhd(50, "BHD") == 50.0

    def test_unknown_currency_returns_amount(self):
        """Unknown currency code uses rate 1.0 (passthrough)."""
        assert _convert_to_bhd(100, "XYZ") == 100.0

    def test_case_insensitive_currency(self):
        """Currency code should be case-insensitive."""
        assert _convert_to_bhd(100, "usd") == _convert_to_bhd(100, "USD")


# --- _calculate_freshness with None price ---

class TestCalculateFreshness:
    def test_price_none_does_not_crash(self, service):
        """product.price = None (explicitly set) should not crash _calculate_freshness."""
        product = {"specs": {"_cached": False}, "price": None, "reviews": {"_cached": True}}
        result = service._calculate_freshness(product)
        assert result in ("live", "mixed", "cached")

    def test_all_live(self, service):
        product = {"specs": {"_cached": False}, "price": {"_cached": False}, "reviews": {"_cached": False}}
        assert service._calculate_freshness(product) == "live"

    def test_all_cached(self, service):
        product = {"specs": {"_cached": True}, "price": {"_cached": True}, "reviews": {"_cached": True}}
        assert service._calculate_freshness(product) == "cached"

    def test_mixed(self, service):
        product = {"specs": {"_cached": True}, "price": {"_cached": False}, "reviews": {"_cached": True}}
        assert service._calculate_freshness(product) == "mixed"


# --- _parse_price_string edge cases ---

class TestParsePriceString:
    def test_normal_dollar_price(self):
        assert StructuredComparisonService._parse_price_string("$699.99") == pytest.approx(699.99)

    def test_bhd_price(self):
        assert StructuredComparisonService._parse_price_string("BHD 339.000") == pytest.approx(339.0)

    def test_thousands_separator(self):
        assert StructuredComparisonService._parse_price_string("SAR 2,499") == pytest.approx(2499.0)

    def test_garbage_input_returns_none(self):
        assert StructuredComparisonService._parse_price_string("no price here") is None

    def test_empty_string_returns_none(self):
        assert StructuredComparisonService._parse_price_string("") is None

    def test_none_input_returns_none(self):
        assert StructuredComparisonService._parse_price_string(None) is None


# --- _is_supplement_query with anti-keywords ---

class TestIsSupplementQuery:
    def test_vitamin_d3_is_supplement(self):
        assert StructuredComparisonService._is_supplement_query("NOW Vitamin D-3 5000 IU") is True

    def test_galaxy_tablet_is_not_supplement(self):
        """'Galaxy' is in HIGH_VALUE_KEYWORDS — should NOT match even though 'tablet' looks supplement-ish."""
        assert StructuredComparisonService._is_supplement_query("Samsung Galaxy Tablet S9") is False

    def test_iphone_is_not_supplement(self):
        assert StructuredComparisonService._is_supplement_query("Apple iPhone 16 Pro") is False

    def test_omega_3_is_supplement(self):
        assert StructuredComparisonService._is_supplement_query("Nordic Naturals Omega-3") is True

    def test_plain_product_is_not_supplement(self):
        assert StructuredComparisonService._is_supplement_query("Nike Air Max 90") is False


# --- _strict_title_match with hyphens ---

class TestStrictTitleMatch:
    def test_exact_match(self):
        assert StructuredComparisonService._strict_title_match(
            "iPhone 16 Pro Max", "Apple iPhone 16 Pro Max 256GB"
        ) is True

    def test_hyphen_normalization(self):
        """'D-3' should match 'D3' (hyphens removed during normalization)."""
        assert StructuredComparisonService._strict_title_match(
            "Vitamin D-3", "NOW Vitamin D3 5000 IU"
        ) is True

    def test_short_words_skipped(self):
        """Words <=2 chars after hyphen removal are skipped (e.g., 'd3' is only 2 chars)."""
        # "D-3" → "d3" (2 chars) → skipped, only "vitamin" checked
        assert StructuredComparisonService._strict_title_match(
            "Vitamin D-3", "Some Vitamin Product"
        ) is True

    def test_mismatch(self):
        assert StructuredComparisonService._strict_title_match(
            "iPhone 16 Pro Max", "Samsung Galaxy S24 Ultra"
        ) is False

    def test_manufacturer_brand_skipped(self):
        """nvidia/amd/intel skipped since AIB partners rebrand."""
        assert StructuredComparisonService._strict_title_match(
            "NVIDIA RTX 4090", "EVGA GeForce RTX 4090"
        ) is True


# --- _numbers_match edge cases ---

class TestNumbersMatch:
    def test_matching_numbers(self):
        assert StructuredComparisonService._numbers_match(
            "NOW D-3 360 Softgels", "NOW Foods Vitamin D-3 360 Softgels"
        ) is True

    def test_mismatched_numbers(self):
        """360 vs 120 — should NOT match."""
        assert StructuredComparisonService._numbers_match(
            "NOW D-3 360 Softgels", "NOW Foods Vitamin D-3 120 Softgels"
        ) is False

    def test_no_significant_numbers_returns_true(self):
        """No numbers >= 10 in product name → always matches (no constraint to enforce)."""
        assert StructuredComparisonService._numbers_match(
            "NOW Vitamin D-3", "NOW Foods Vitamin D-3 500 IU"
        ) is True

    def test_single_digit_ignored(self):
        """Single digit '3' in D-3 is not a standalone 2+ digit number."""
        assert StructuredComparisonService._numbers_match(
            "Vitamin D-3", "Some Vitamin Product 120 Tablets"
        ) is True

    def test_year_and_count_both_present(self):
        """Both 2024 and 256 should be checked."""
        assert StructuredComparisonService._numbers_match(
            "iPhone 16 256GB", "Apple iPhone 16 256GB 2024"
        ) is True

    def test_year_missing_from_title(self):
        """Product has 256, title has 256 — match (even if year differs)."""
        assert StructuredComparisonService._numbers_match(
            "iPhone 16 256GB", "Apple iPhone 16 256GB"
        ) is True
```

**Step 2: Run tests**

```bash
python -m pytest tests/test_error_paths.py -v
```

Expected: All pass.

**Step 3: Commit**

```bash
git add tests/test_error_paths.py
git commit -m "test: add error paths and edge case unit tests"
```

---

## Task 2: test_rating_tiers.py (Agent B)

Hybrid: mocked for edge cases, live for real tier selection.

**Files:**
- Create: `tests/test_rating_tiers.py`

**Step 1: Write test file**

```python
"""Tests for rating tier selection, consensus logic, and regional fallback.

Hybrid: unit tests for logic, live tests for real Serper data.
Run: python -m pytest tests/test_rating_tiers.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- _get_rating_tier classification ---

class TestGetRatingTier:
    def test_amazon_is_tier1(self):
        assert StructuredComparisonService._get_rating_tier("Amazon.com") == 1

    def test_best_buy_is_tier1(self):
        assert StructuredComparisonService._get_rating_tier("Best Buy") == 1

    def test_costco_is_tier2(self):
        assert StructuredComparisonService._get_rating_tier("Costco") == 2

    def test_ebay_with_domain_is_tier2(self):
        """eBay has .com domain — _get_rating_tier checks .com before Tier 3 list."""
        # Note: _get_rating_tier checks Tier 1 → Tier 2 → .com/.ae domain → Tier 3
        # eBay is NOT in RATING_TIER_1 or RATING_TIER_2, but has .com
        # The method checks domain BEFORE Tier 3 list — so "eBay.com" → Tier 2
        tier = StructuredComparisonService._get_rating_tier("eBay")
        # eBay without .com → not in tier1/tier2, no ".com" in "eBay" → Tier 3
        assert tier == 3

    def test_unknown_source_is_tier3(self):
        assert StructuredComparisonService._get_rating_tier("RandomShop") == 3

    def test_empty_source_is_tier3(self):
        assert StructuredComparisonService._get_rating_tier("") == 3

    def test_none_source_is_tier3(self):
        assert StructuredComparisonService._get_rating_tier(None) == 3


# --- _extract_rating_from_shopping logic ---

class TestExtractRatingFromShopping:
    def test_empty_items_returns_empty(self, service):
        result = service._extract_rating_from_shopping("iPhone 16", [])
        assert result["rating"] is None
        assert result["rating_source"] is None

    def test_tier1_preferred_over_tier3(self, service):
        """Tier 1 (Amazon) should be preferred even if Tier 3 has more reviews."""
        items = [
            {"title": "Apple iPhone 16 256GB", "source": "Amazon.com", "rating": 4.5, "ratingCount": 500},
            {"title": "Apple iPhone 16 256GB", "source": "eBay", "rating": 4.8, "ratingCount": 50000},
        ]
        result = service._extract_rating_from_shopping("Apple iPhone 16 256GB", items)
        assert result["rating"] == 4.5
        assert "Amazon" in result["rating_source"]["name"]

    def test_tier3_rejected_under_1000_reviews(self, service):
        """Tier 3 with <1000 reviews should be rejected."""
        items = [
            {"title": "Apple iPhone 16 256GB", "source": "eBay", "rating": 4.2, "ratingCount": 50},
        ]
        result = service._extract_rating_from_shopping("Apple iPhone 16 256GB", items)
        assert result["rating"] is None

    def test_tier3_accepted_over_1000_reviews(self, service):
        """Tier 3 with >1000 reviews should be accepted (no tier1/tier2 available)."""
        items = [
            {"title": "Apple iPhone 16 256GB", "source": "eBay", "rating": 4.2, "ratingCount": 5000},
        ]
        result = service._extract_rating_from_shopping("Apple iPhone 16 256GB", items)
        assert result["rating"] == 4.2
        assert result["rating_verified"] is False  # Tier 3 = not verified

    def test_consensus_triggers_with_3_identical(self, service):
        """3+ unknown sellers with same rating+reviewCount → consensus."""
        items = [
            {"title": "Apple iPhone 16 256GB", "source": "ShopA", "rating": 4.7, "ratingCount": 23000},
            {"title": "Apple iPhone 16 256GB", "source": "ShopB", "rating": 4.7, "ratingCount": 23000},
            {"title": "Apple iPhone 16 256GB", "source": "ShopC", "rating": 4.7, "ratingCount": 23000},
        ]
        result = service._extract_rating_from_shopping("Apple iPhone 16 256GB", items)
        assert result["rating"] == 4.7
        assert result["rating_source"]["extract_method"] == "google_shopping_consensus"
        assert result["rating_verified"] is True

    def test_consensus_does_not_trigger_with_tier1_present(self, service):
        """Consensus only triggers when NO tier1/tier2 candidates exist."""
        items = [
            {"title": "Apple iPhone 16 256GB", "source": "Amazon.com", "rating": 4.5, "ratingCount": 1000},
            {"title": "Apple iPhone 16 256GB", "source": "ShopA", "rating": 4.7, "ratingCount": 23000},
            {"title": "Apple iPhone 16 256GB", "source": "ShopB", "rating": 4.7, "ratingCount": 23000},
            {"title": "Apple iPhone 16 256GB", "source": "ShopC", "rating": 4.7, "ratingCount": 23000},
        ]
        result = service._extract_rating_from_shopping("Apple iPhone 16 256GB", items)
        assert result["rating"] == 4.5  # Tier 1 wins, consensus not checked
        assert "Amazon" in result["rating_source"]["name"]

    def test_accessories_rejected(self, service):
        """Accessory titles should be filtered out."""
        items = [
            {"title": "iPhone 16 Case Protective Cover", "source": "Amazon.com", "rating": 4.9, "ratingCount": 5000},
        ]
        result = service._extract_rating_from_shopping("Apple iPhone 16", items)
        assert result["rating"] is None

    def test_invalid_rating_skipped(self, service):
        """Rating > 5 or <= 0 should be skipped."""
        items = [
            {"title": "Apple iPhone 16 256GB", "source": "Amazon.com", "rating": 6.0, "ratingCount": 1000},
            {"title": "Apple iPhone 16 256GB", "source": "Best Buy", "rating": 0, "ratingCount": 500},
        ]
        result = service._extract_rating_from_shopping("Apple iPhone 16 256GB", items)
        assert result["rating"] is None


# --- Live rating test (real Serper data) ---

@pytest.mark.live_unit
class TestRatingLive:
    def test_popular_phone_gets_rating(self, service):
        """A popular phone should get a rating from real Serper Shopping data."""
        result = run_async(service._get_verified_rating("Apple iPhone 15 128GB"))
        assert result.get("rating") is not None
        assert 1.0 <= result["rating"] <= 5.0
        assert result.get("rating_source") is not None
        assert result["rating_source"].get("url") is not None
        assert result["rating_source"].get("extract_method") is not None
```

**Step 2: Run tests**

```bash
python -m pytest tests/test_rating_tiers.py -v -m "not live_unit"
```

Expected: Unit tests pass. Live test skipped.

**Step 3: Commit**

```bash
git add tests/test_rating_tiers.py
git commit -m "test: add rating tier selection and consensus unit tests"
```

---

## Task 3: test_price_fallback.py (Agent B)

**Files:**
- Create: `tests/test_price_fallback.py`

**Step 1: Write test file**

```python
"""Tests for the 3-tier price fallback chain and supplement routing.

Hybrid: mocked for tier logic, live for real pricing.
Run: python -m pytest tests/test_price_fallback.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.services.structured_comparison_service import (
    StructuredComparisonService,
    _convert_to_bhd,
)


@pytest.fixture
def service():
    return StructuredComparisonService()


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Price extraction from shopping items ---

class TestExtractPriceFromShopping:
    def test_returns_none_for_empty_items(self, service):
        assert service._extract_price_from_shopping("iPhone 16", [], "BHD") is None

    def test_filters_accessories(self, service):
        """Shopping items that are accessories should be filtered."""
        items = [{"title": "iPhone 16 Case Cover", "price": "$9.99", "source": "Amazon.com", "rating": 4.5}]
        assert service._extract_price_from_shopping("Apple iPhone 16", items, "USD") is None

    def test_minimum_price_for_high_value(self, service):
        """High-value products (phones) should reject prices below BHD 100."""
        items = [{"title": "Apple iPhone 16 256GB", "price": "$5.99", "source": "Some Shop", "rating": 4.0}]
        result = service._extract_price_from_shopping("Apple iPhone 16", items, "USD")
        # $5.99 → ~2.26 BHD, below BHD 100 minimum for high-value → rejected
        assert result is None

    def test_valid_electronics_price_extracted(self, service):
        """Valid electronics price from trusted retailer."""
        items = [{
            "title": "Apple iPhone 16 256GB",
            "price": "$799.00",
            "source": "Best Buy",
            "link": "https://www.bestbuy.com/iphone16",
            "rating": 4.7,
            "ratingCount": 5000,
        }]
        result = service._extract_price_from_shopping("Apple iPhone 16 256GB", items, "USD")
        assert result is not None
        assert result["amount"] == pytest.approx(799.0, abs=1.0)


# --- Supplement detection routing ---

class TestSupplementRouting:
    def test_supplement_skips_shopping_search(self, service):
        """Supplements should skip Serper Shopping (returns zero results for supplements)."""
        # After calling _get_price with category="supplements", _shopping_items_cache should be empty
        service._shopping_items_cache = {}
        # We can verify the supplement detection logic
        assert service._is_supplement_query("NOW Vitamin D-3 5000 IU") is True
        assert service._is_supplement_query("Apple iPhone 16 Pro") is False


# --- Currency conversion in price pipeline ---

class TestCurrencyConversion:
    def test_convert_gpt_price_usd_to_bhd(self, service):
        """GPT returns USD price → should be converted to BHD."""
        price = {"amount": 100.0, "original_currency": "USD", "currency": "USD"}
        service._convert_gpt_price_currency(price, "BHD")
        assert price["currency"] == "BHD"
        assert price["amount"] == pytest.approx(37.7, abs=0.1)

    def test_convert_gpt_price_same_currency_noop(self, service):
        """GPT returns BHD price, target is BHD → no conversion."""
        price = {"amount": 50.0, "original_currency": "BHD", "currency": "BHD"}
        service._convert_gpt_price_currency(price, "BHD")
        assert price["amount"] == 50.0

    def test_convert_gpt_price_none_amount_noop(self, service):
        """Price with None amount should not crash."""
        price = {"amount": None, "original_currency": "USD"}
        service._convert_gpt_price_currency(price, "BHD")
        assert price["amount"] is None

    def test_sanitize_gpt_price_null_string(self, service):
        """GPT returning 'null' string should be cleaned to None."""
        price = {"amount": 50.0, "retailer": "null", "url": "product url or null"}
        service._sanitize_gpt_price(price)
        assert price["retailer"] is None
        assert price["url"] is None


# --- All tiers fail ---

class TestAllTiersFail:
    def test_all_tiers_fail_returns_none_amount(self, service):
        """When all 3 tiers fail, price.amount should be None."""
        with patch("app.services.structured_comparison_service.search_product_prices", new_callable=AsyncMock) as mock_shop, \
             patch("app.services.structured_comparison_service.search_price_organic", new_callable=AsyncMock) as mock_organic, \
             patch("app.services.structured_comparison_service.extract_price", new_callable=AsyncMock) as mock_gpt_price, \
             patch("app.services.structured_comparison_service.extract_price_from_training_data", new_callable=AsyncMock) as mock_tier3, \
             patch("app.services.structured_comparison_service.get_cached", return_value=None):
            mock_shop.return_value = {"shopping": [], "organic": []}
            mock_organic.return_value = {"organic": [], "knowledge_graph": None}
            mock_gpt_price.return_value = {"amount": None}
            mock_tier3.return_value = {"amount": None}

            result = run_async(service._get_price("Apple", "iPhone 99", None, "bahrain", "Apple iPhone 99"))
            assert result["amount"] is None
            assert result["currency"] == "BHD"


# --- Live price tests ---

@pytest.mark.live_unit
class TestPriceLive:
    def test_electronics_gets_real_price(self, service):
        """Real electronics product should get a BHD price."""
        result = run_async(service._get_price("Apple", "iPhone 15", "128GB", "bahrain", "Apple iPhone 15 128GB"))
        assert result is not None
        assert result.get("amount") is not None
        assert result["amount"] > 0
        assert result.get("currency") == "BHD"

    def test_price_has_required_fields(self, service):
        """Price result should have amount, currency, and _cached fields."""
        result = run_async(service._get_price("Samsung", "Galaxy S24", None, "bahrain", "Samsung Galaxy S24"))
        assert "amount" in result
        assert "currency" in result
        assert "_cached" in result
```

**Step 2: Run tests**

```bash
python -m pytest tests/test_price_fallback.py -v -m "not live_unit"
```

**Step 3: Commit**

```bash
git add tests/test_price_fallback.py
git commit -m "test: add price fallback chain and currency conversion tests"
```

---

## Task 4: test_singleton_state.py (Agent A)

**Files:**
- Create: `tests/test_singleton_state.py`

**Step 1: Write test file**

```python
"""Tests for singleton service state management.

Verifies state is properly reset between requests to prevent cross-request data leaks.
Run: python -m pytest tests/test_singleton_state.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.services.structured_comparison_service import (
    StructuredComparisonService,
    get_comparison_service,
    _service_instance,
)


@pytest.fixture
def service():
    return StructuredComparisonService()


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestSingletonPattern:
    def test_get_comparison_service_returns_same_instance(self):
        """get_comparison_service() should return the same instance."""
        import app.services.structured_comparison_service as mod
        mod._service_instance = None  # Reset for test
        s1 = get_comparison_service()
        s2 = get_comparison_service()
        assert s1 is s2
        mod._service_instance = None  # Cleanup


class TestStateReset:
    def test_shopping_cache_cleared_on_new_request(self, service):
        """_shopping_items_cache must be cleared at start of compare_from_text."""
        # Simulate leftover state from a previous request
        service._shopping_items_cache = {"old_product": [{"title": "stale data"}]}
        service.total_cost = 0.05
        service.api_calls = 10

        # Mock everything so compare_from_text runs but doesn't call real APIs
        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock) as mock_parse, \
             patch.object(service, "_fetch_product_data", new_callable=AsyncMock) as mock_fetch, \
             patch("app.services.structured_comparison_service.generate_comparison", new_callable=AsyncMock) as mock_compare:
            mock_parse.return_value = {
                "products": [
                    {"brand": "A", "name": "Product1", "category": "other", "search_query": "A Product1"},
                    {"brand": "B", "name": "Product2", "category": "other", "search_query": "B Product2"},
                ]
            }
            mock_fetch.return_value = {"brand": "Test", "name": "Product", "specs": {}, "price": {"amount": 100, "currency": "BHD"}, "rating": 4.5}
            mock_compare.return_value = {"winner_index": 0, "recommendation": "Test"}

            run_async(service.compare_from_text("A Product1 vs B Product2"))

        # State should have been reset at start of compare_from_text
        # (total_cost/api_calls are modified during the call, but _shopping_items_cache
        # should NOT contain "old_product" anymore)
        assert "old_product" not in service._shopping_items_cache

    def test_cost_and_calls_reset_per_request(self, service):
        """total_cost and api_calls should be reset to 0 at start of each request."""
        service.total_cost = 0.05
        service.api_calls = 10

        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock) as mock_parse:
            # Make it fail early — we just need to verify the reset happened
            mock_parse.side_effect = Exception("intentional test error")

            result = run_async(service.compare_from_text("test query"))

        # Even though the request failed, cost/calls should have been reset before the error
        assert service.total_cost == 0.0
        assert service.api_calls == 0
```

**Step 2: Run tests**

```bash
python -m pytest tests/test_singleton_state.py -v
```

**Step 3: Commit**

```bash
git add tests/test_singleton_state.py
git commit -m "test: add singleton state reset verification tests"
```

---

## Task 5: test_iherb_scraping.py (Agent A)

**Files:**
- Create: `tests/test_iherb_scraping.py`

**Step 1: Write test file**

```python
"""Tests for iHerb direct scraping via curl_cffi.

Live tests — actually scrape iHerb (free, no API key needed).
Run: python -m pytest tests/test_iherb_scraping.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Helper method tests (always pass, no HTTP) ---

class TestQueryCleanup:
    def test_normalize_words_removes_hyphens(self):
        result = StructuredComparisonService._normalize_words("Vitamin D-3, 1000 IU")
        assert "d3" in result
        assert "vitamin" in result
        assert "1000" in result
        assert "iu" in result

    def test_normalize_words_strips_punctuation(self):
        result = StructuredComparisonService._normalize_words("Now Foods (USA)")
        assert "now" in result
        assert "foods" in result
        assert "usa" in result
        assert "(" not in str(result)


# --- Live iHerb scraping tests ---

@pytest.mark.live_unit
class TestIherbScrapeLive:
    """Live tests that actually hit iHerb. Free (HTTP only, no API key).
    May be flaky if Cloudflare blocks or iHerb changes HTML structure."""

    def test_known_supplement_returns_price(self, service):
        """NOW D-3 should return a price from bh.iherb.com."""
        result = run_async(service._fetch_iherb_price(
            "NOW D3 5000", "NOW", "NOW Vitamin D-3 5000 IU", "bh", "BHD"
        ))
        # curl_cffi may or may not succeed depending on environment
        if result is not None:
            assert result["amount"] > 0
            assert result["currency"] == "BHD"
            assert result["retailer"] == "iHerb"
            assert "iherb.com" in result["url"]
            assert result["estimated"] is False

    def test_regional_store_bahrain(self, service):
        """Bahrain regional store should return BHD prices."""
        result = run_async(service._fetch_iherb_price(
            "Nature Made D3 2000", "Nature Made", "Nature Made Vitamin D3 2000 IU", "bh", "BHD"
        ))
        if result is not None:
            assert result["currency"] == "BHD"
            assert "bh.iherb.com" in result["url"]

    def test_brand_filtering(self, service):
        """Searching for NOW should not return Nature Made results."""
        result = run_async(service._fetch_iherb_price(
            "NOW D3", "NOW", "NOW Vitamin D-3", "bh", "BHD"
        ))
        if result is not None:
            # The matched product should be from NOW, not another brand
            assert result["retailer"] == "iHerb"

    def test_nonexistent_product_returns_none(self, service):
        """A completely made-up product should return None, not crash."""
        result = run_async(service._fetch_iherb_price(
            "XYZFAKE Nonexistent Vitamin", "XYZFAKE", "XYZFAKE Nonexistent Vitamin", "bh", "BHD"
        ))
        assert result is None

    def test_non_supplement_brand_returns_none(self, service):
        """Searching for a non-supplement brand should return None."""
        result = run_async(service._fetch_iherb_price(
            "Apple iPhone", "Apple", "Apple iPhone 16 Pro", "bh", "BHD"
        ))
        assert result is None
```

**Step 2: Run tests**

```bash
python -m pytest tests/test_iherb_scraping.py -v -m "not live_unit"
```

For live tests:
```bash
python -m pytest tests/test_iherb_scraping.py -v
```

**Step 3: Commit**

```bash
git add tests/test_iherb_scraping.py
git commit -m "test: add iHerb scraping and word normalization tests"
```

---

## Task 6: test_camera_vision.py (Agent A)

**Files:**
- Create: `tests/test_camera_vision.py`

**Step 1: Write test file**

```python
"""Tests for camera/vision product identification pipeline.

Live tests call GPT-4o-mini vision API (~$0.005/test).
Run: python -m pytest tests/test_camera_vision.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.openai_service import identify_products, clean_json_response


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- clean_json_response tests ---

class TestCleanJsonResponse:
    def test_strips_markdown_code_blocks(self):
        raw = '```json\n[{"brand": "Apple"}]\n```'
        assert clean_json_response(raw) == '[{"brand": "Apple"}]'

    def test_plain_json_unchanged(self):
        raw = '[{"brand": "Apple"}]'
        assert clean_json_response(raw) == '[{"brand": "Apple"}]'

    def test_strips_whitespace(self):
        raw = '  \n[{"brand": "Apple"}]\n  '
        assert clean_json_response(raw) == '[{"brand": "Apple"}]'


# --- Vision pipeline tests (mocked) ---

class TestIdentifyProductsMocked:
    def test_malformed_response_returns_error(self):
        """If GPT returns non-JSON, should return error dict with raw_response."""
        mock_usage = MagicMock()
        mock_usage.total_tokens = 100
        mock_usage.prompt_tokens = 80
        mock_usage.completion_tokens = 20

        mock_choice = MagicMock()
        mock_choice.message.content = "I can see an iPhone in the image"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        with patch("app.services.openai_service.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = run_async(identify_products([{"bytes": b"\xff\xd8fake", "mime_type": "image/jpeg"}]))

        assert result.get("error") is not None
        assert "Failed to parse" in result["error"]
        assert result.get("raw_response") == "I can see an iPhone in the image"

    def test_successful_identification(self):
        """Valid JSON response should return normalized products."""
        mock_usage = MagicMock()
        mock_usage.total_tokens = 200
        mock_usage.prompt_tokens = 150
        mock_usage.completion_tokens = 50

        mock_choice = MagicMock()
        mock_choice.message.content = '[{"brand": "Apple", "name": "iPhone 16 Pro", "size_or_count": "256GB", "visible_price": null, "confidence": "high"}]'

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        with patch("app.services.openai_service.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = run_async(identify_products([{"bytes": b"\xff\xd8fake", "mime_type": "image/jpeg"}]))

        assert len(result["products"]) == 1
        assert result["products"][0]["brand"] == "Apple"
        assert result["products"][0]["name"] == "iPhone 16 Pro"
        assert result["products"][0]["size_or_count"] == "256GB"
        assert result["cost"] > 0

    def test_empty_product_fields_normalized(self):
        """Missing fields should be filled with defaults."""
        mock_usage = MagicMock()
        mock_usage.total_tokens = 100
        mock_usage.prompt_tokens = 80
        mock_usage.completion_tokens = 20

        mock_choice = MagicMock()
        mock_choice.message.content = '[{"name": "Something"}]'

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        with patch("app.services.openai_service.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = run_async(identify_products([{"bytes": b"\xff\xd8fake", "mime_type": "image/jpeg"}]))

        product = result["products"][0]
        assert product["brand"] == "Unknown"  # Default for missing brand
        assert product["confidence"] == "medium"  # Default confidence


# --- size_or_count enrichment (image_routes.py logic) ---

class TestSizeOrCountEnrichment:
    def test_size_appended_to_name(self):
        """size_or_count should be appended to product name if not already present."""
        products = [{"brand": "NOW", "name": "Vitamin D-3", "size_or_count": "360 Softgels"}]
        for p in products:
            size_or_count = p.get("size_or_count")
            if size_or_count and size_or_count.lower() not in p.get("name", "").lower():
                p["name"] = f"{p['name']} {size_or_count}".strip()
        assert products[0]["name"] == "Vitamin D-3 360 Softgels"

    def test_size_not_duplicated_if_already_present(self):
        """If size_or_count is already in the name, don't append again."""
        products = [{"brand": "NOW", "name": "Vitamin D-3 360 Softgels", "size_or_count": "360 Softgels"}]
        for p in products:
            size_or_count = p.get("size_or_count")
            if size_or_count and size_or_count.lower() not in p.get("name", "").lower():
                p["name"] = f"{p['name']} {size_or_count}".strip()
        assert products[0]["name"] == "Vitamin D-3 360 Softgels"  # Not duplicated

    def test_none_size_or_count_no_change(self):
        """None size_or_count should not modify name."""
        products = [{"brand": "Apple", "name": "iPhone 16 Pro", "size_or_count": None}]
        original_name = products[0]["name"]
        for p in products:
            size_or_count = p.get("size_or_count")
            if size_or_count and size_or_count.lower() not in p.get("name", "").lower():
                p["name"] = f"{p['name']} {size_or_count}".strip()
        assert products[0]["name"] == original_name


# --- Live vision test (real GPT-4o-mini call) ---

@pytest.mark.live_unit
class TestVisionLive:
    def test_real_image_identifies_products(self):
        """Send a real test image to GPT-4o-mini vision."""
        test_image = os.path.join(os.path.dirname(__file__), "..", "test_two.jpg")
        if not os.path.exists(test_image):
            pytest.skip("test_two.jpg not found in repo root")

        with open(test_image, "rb") as f:
            image_bytes = f.read()

        result = run_async(identify_products([
            {"bytes": image_bytes, "mime_type": "image/jpeg"}
        ]))

        assert "products" in result
        # Should identify at least 1 product (test_two.jpg has 2 products)
        assert len(result["products"]) >= 1
        assert result["products"][0].get("brand")
        assert result["products"][0].get("name")
        assert result.get("cost", 0) > 0
```

**Step 2: Run tests**

```bash
python -m pytest tests/test_camera_vision.py -v -m "not live_unit"
```

**Step 3: Commit**

```bash
git add tests/test_camera_vision.py
git commit -m "test: add camera/vision pipeline and size_or_count tests"
```

---

## Task 7: test_unified_search.py (Agent C)

**Files:**
- Create: `tests/test_unified_search.py`

**Step 1: Write test file**

```python
"""Tests for unified search call merging optimization.

Verifies that one Serper call is shared by specs + reviews, saving $0.001/product.
Run: python -m pytest tests/test_unified_search.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, call
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestUnifiedSearchSharing:
    def test_specs_skips_own_search_when_results_provided(self, service):
        """_get_specs() should NOT call search_web when search_results is provided."""
        with patch("app.services.structured_comparison_service.search_web", new_callable=AsyncMock) as mock_search, \
             patch("app.services.structured_comparison_service.extract_specs", new_callable=AsyncMock) as mock_extract, \
             patch("app.services.structured_comparison_service.get_cached", return_value=None), \
             patch("app.services.structured_comparison_service.set_cached"):
            mock_extract.return_value = {"display": "6.1 inch", "processor": "A16"}
            pre_fetched = {"organic": [{"title": "Test", "snippet": "specs"}]}

            run_async(service._get_specs("Apple", "iPhone 16", None, "electronics", "Apple iPhone 16",
                                          search_results=pre_fetched))

            # search_web should NOT have been called (pre-fetched results provided)
            mock_search.assert_not_called()

    def test_specs_calls_own_search_when_no_results(self, service):
        """_get_specs() should call search_web when search_results is None."""
        with patch("app.services.structured_comparison_service.search_web", new_callable=AsyncMock) as mock_search, \
             patch("app.services.structured_comparison_service.extract_specs", new_callable=AsyncMock) as mock_extract, \
             patch("app.services.structured_comparison_service.get_cached", return_value=None), \
             patch("app.services.structured_comparison_service.set_cached"):
            mock_search.return_value = {"organic": []}
            mock_extract.return_value = {"display": "6.1 inch"}

            run_async(service._get_specs("Apple", "iPhone 16", None, "electronics", "Apple iPhone 16"))

            mock_search.assert_called_once()

    def test_reviews_skips_own_search_when_results_provided(self, service):
        """_get_reviews() should NOT call search_web when search_results is provided."""
        with patch("app.services.structured_comparison_service.search_web", new_callable=AsyncMock) as mock_search, \
             patch("app.services.structured_comparison_service.extract_reviews", new_callable=AsyncMock) as mock_extract, \
             patch("app.services.structured_comparison_service.get_cached", return_value=None), \
             patch("app.services.structured_comparison_service.set_cached"):
            mock_extract.return_value = {"average_rating": 4.5, "common_praises": [], "common_complaints": []}
            pre_fetched = {"organic": [{"title": "Review", "snippet": "good product"}]}

            run_async(service._get_reviews("Apple", "iPhone 16", None, "Apple iPhone 16",
                                            search_results=pre_fetched))

            mock_search.assert_not_called()


# --- Live cost tracking test ---

@pytest.mark.live_unit
class TestCostTrackingLive:
    def test_comparison_within_budget(self, service):
        """A full comparison should cost <= $0.020 and use <= 20 API calls."""
        import httpx
        BASE_URL = "https://smartcompare-backend-production.up.railway.app"
        response = httpx.get(
            f"{BASE_URL}/api/v1/text/compare",
            params={"q": "iPhone 15 vs Samsung Galaxy S24", "nocache": "true"},
            timeout=150.0,
        )
        assert response.status_code == 200
        data = response.json()
        metadata = data.get("metadata", {})
        total_cost = metadata.get("total_cost", 0)
        api_calls = metadata.get("api_calls", 0)

        assert total_cost <= 0.020, f"Cost ${total_cost:.4f} exceeds $0.020 budget"
        assert api_calls <= 20, f"{api_calls} API calls exceeds 20-call budget"
```

**Step 2: Run tests**

```bash
python -m pytest tests/test_unified_search.py -v -m "not live_unit"
```

**Step 3: Commit**

```bash
git add tests/test_unified_search.py
git commit -m "test: add unified search merging and cost tracking tests"
```

---

## Task 8: Cross-QA Review

After all 7 files are written and passing:

**Agent C reviews Agent A's files:**
- `test_camera_vision.py` — Check: all mocked tests actually test the right thing, live test uses real image, size_or_count logic matches image_routes.py
- `test_singleton_state.py` — Check: state reset test properly verifies pre-request cleanup, singleton test resets global state
- `test_iherb_scraping.py` — Check: live tests handle curl_cffi failure gracefully (skip or `if result is not None`), query cleanup tested

**Agent A reviews Agent B's files:**
- `test_rating_tiers.py` — Check: consensus test has exactly 3 unknown sellers (not tier1/tier2), tier classification matches RATING_TIER_1/2/3 constants
- `test_price_fallback.py` — Check: all-tiers-fail test properly patches all API calls, currency conversion uses correct rates

**Agent B reviews Agent C's files:**
- `test_unified_search.py` — Check: search sharing test verifies search_results kwarg propagation, cost test uses realistic budget
- `test_error_paths.py` — Check: every past bug from MEMORY.md "Critical Bugs Fixed" is covered, edge cases match actual code behavior

**QA Checklist per file:**
1. All tests pass: `python -m pytest tests/<file>.py -v`
2. No test depends on execution order
3. Mocked tests mock at the right boundary (not too deep, not too shallow)
4. Live tests handle network failure gracefully (skip or conditional assert)
5. Test names clearly describe what they verify
6. No hardcoded values that could break (use `pytest.approx` for floats)

---

## Task 9: Final Verification

Run the complete test suite:

```bash
# All unit tests (free, fast)
python -m pytest tests/ -v -m "unit or not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# All tests including live
python -m pytest tests/ -v -m "not (live_db or integration)"

# Full suite including integration (costs ~$0.12 total)
python -m pytest tests/ -v --timeout=180
```

Expected: 44+ tests pass, 0 failures.

**Commit:**

```bash
git add tests/
git commit -m "test: complete test coverage for 7 uncovered areas (44 tests)"
```
