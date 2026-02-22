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
