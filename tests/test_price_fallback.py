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
        # 1 USD = 0.376 BHD (currency-pegged); see FALLBACK_RATES.
        assert price["amount"] == pytest.approx(37.6, abs=0.1)

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
            mock_gpt_price.return_value = ({"amount": None}, {"prompt_tokens": 0, "completion_tokens": 0})
            mock_tier3.return_value = ({"amount": None}, {"prompt_tokens": 0, "completion_tokens": 0})

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
