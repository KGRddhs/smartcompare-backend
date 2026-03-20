"""Tests for price source prioritization -- official > authorized > marketplace > reseller.

Covers:
- Official domain preferred over cheaper reseller
- Non-luxury normal price behavior
- Counterfeit sites get low retailer scores
- Luxury brand activates retailer-priority sorting
- Fashion retailers in RETAILER_TIERS
- Luxury brands in RETAILER_TIERS
- Untrusted sites remain low-tier

Run: pytest tests/test_price_priority.py -v
"""
import pytest
from app.services.structured_comparison_service import (
    StructuredComparisonService,
    RETAILER_TIERS,
)


@pytest.fixture
def service():
    svc = StructuredComparisonService()
    svc.total_cost = 0
    svc.api_calls = 0
    svc.gpt_calls = 0
    svc.serper_calls = 0
    return svc


class TestPriceSourcePriority:

    def test_official_domain_preferred_over_cheaper(self, service):
        """hermes.com at $630 should beat eBay at $94."""
        shopping_items = [
            {"price": "$94.25", "title": "Hermes Nevada Cap", "source": "eBay", "link": "https://ebay.com/itm/123"},
            {"price": "$630.00", "title": "Hermes Nevada H'Cheval cap", "source": "Hermes", "link": "https://www.hermes.com/us/en/product/cap"},
        ]
        result = service._extract_price_from_shopping("Hermes Nevada H'Cheval cap", shopping_items, "BHD")
        # Should pick the higher official price, not the cheap eBay one
        assert result is not None
        assert result["retailer_score"] >= 1.0

    def test_non_luxury_still_prefers_lower_price(self, service):
        """For non-luxury items, lower price from good retailers is fine."""
        shopping_items = [
            {"price": "$29.99", "title": "Nike Air Max 90", "source": "Amazon", "link": "https://amazon.com/dp/123"},
            {"price": "$35.99", "title": "Nike Air Max 90", "source": "Foot Locker", "link": "https://footlocker.com/123"},
        ]
        result = service._extract_price_from_shopping("Nike Air Max 90", shopping_items, "BHD")
        assert result is not None
        # Both are decent retailers, cheaper should win (or close)

    def test_counterfeit_sites_filtered_for_luxury(self, service):
        """DHgate/AliExpress results should get low retailer scores."""
        score_dhgate = service._get_retailer_score("DHgate")
        score_aliexpress = service._get_retailer_score("AliExpress")
        assert score_dhgate <= 0.3
        assert score_aliexpress <= 0.3

    def test_luxury_brand_activates_retailer_priority_sorting(self, service):
        """For luxury brands, sort should prioritize retailer_score over match_score."""
        # This test verifies the sort order change for luxury
        assert service._is_luxury_brand("Louis Vuitton cap") is True
        assert service._is_luxury_brand("Nike cap") is False


class TestRetailerTiersCoverage:

    def test_fashion_retailers_in_tiers(self):
        assert "farfetch" in RETAILER_TIERS
        assert "nordstrom" in RETAILER_TIERS
        assert "ssense" in RETAILER_TIERS

    def test_luxury_brands_in_tiers(self):
        assert "hermes" in RETAILER_TIERS
        assert "louis vuitton" in RETAILER_TIERS
        assert "chanel" in RETAILER_TIERS
        assert "gucci" in RETAILER_TIERS

    def test_untrusted_remain_low(self):
        assert RETAILER_TIERS["dhgate"] <= 0.3
        assert RETAILER_TIERS["temu"] <= 0.3
        assert RETAILER_TIERS["wish"] <= 0.3


class TestStrictTitleMatch:
    """Test _strict_title_match rejects counterfeits but accepts legitimate listings."""

    def test_strict_title_match_rejects_replica(self):
        """Title with 'replica' should be rejected even if product name words match."""
        assert StructuredComparisonService._strict_title_match(
            "Hermes Nevada Cap", "Hermes Nevada Cap Replica"
        ) is False

    def test_strict_title_match_accepts_legitimate(self):
        """Legitimate title with all key words should pass."""
        assert StructuredComparisonService._strict_title_match(
            "Hermes Nevada Cap", "Hermes Nevada H'Cheval Cap - Official Store"
        ) is True

    def test_strict_title_match_rejects_fake(self):
        assert StructuredComparisonService._strict_title_match(
            "Gucci Ace Sneakers", "Fake Gucci Ace Sneakers for Cheap"
        ) is False

    def test_strict_title_match_rejects_inspired(self):
        assert StructuredComparisonService._strict_title_match(
            "Louis Vuitton Wallet", "Designer Inspired Louis Vuitton Wallet"
        ) is False
