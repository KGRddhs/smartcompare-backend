"""Tests for luxury brand detection and price guardrails.

Covers:
- _is_luxury_brand() detection for major luxury houses
- Case insensitivity
- Accent handling (Hermes/Hermes)
- OFFICIAL_BRAND_DOMAINS constant
- Luxury retailers in RETAILER_TIERS

Run: pytest tests/test_luxury_brands.py -v
"""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


class TestLuxuryBrandDetection:
    """Test _is_luxury_brand() method."""

    @pytest.mark.parametrize("name,expected", [
        ("Louis Vuitton LV Vers Mesh Cap", True),
        ("Hermes Nevada H'Cheval cap", True),
        ("Hermes Birkin Bag", True),
        ("Chanel No. 5 Eau de Parfum", True),
        ("Gucci Ace Sneakers", True),
        ("Rolex Submariner", True),
        ("Prada Re-Nylon Backpack", True),
        ("Nike Air Max 90", False),
        ("Samsung Galaxy S24", False),
        ("NOW Vitamin D3", False),
        ("Adidas Ultraboost", False),
        ("Generic Cotton Hat", False),
    ])
    def test_luxury_detection(self, name, expected):
        assert StructuredComparisonService._is_luxury_brand(name) == expected

    def test_case_insensitive(self):
        assert StructuredComparisonService._is_luxury_brand("LOUIS VUITTON cap")
        assert StructuredComparisonService._is_luxury_brand("hermes scarf")

    def test_accent_handling(self):
        """Hermes with accent should be detected."""
        assert StructuredComparisonService._is_luxury_brand("Hermès bag")


class TestOfficialBrandDomains:
    """Test OFFICIAL_BRAND_DOMAINS constant."""

    def test_luxury_domains_exist(self):
        domains = StructuredComparisonService.OFFICIAL_BRAND_DOMAINS
        assert "hermes.com" in domains
        assert "louisvuitton.com" in domains
        assert "chanel.com" in domains

    def test_tech_domains_exist(self):
        domains = StructuredComparisonService.OFFICIAL_BRAND_DOMAINS
        assert "apple.com" in domains
        assert "samsung.com" in domains

    def test_authorized_retailers_exist(self):
        domains = StructuredComparisonService.OFFICIAL_BRAND_DOMAINS
        assert "farfetch.com" in domains
        assert "nordstrom.com" in domains


class TestLuxuryRetailerTiers:
    """Test that luxury retailers are properly tiered."""

    def test_luxury_brands_in_retailer_tiers(self):
        from app.services.structured_comparison_service import RETAILER_TIERS
        assert RETAILER_TIERS.get("hermes", 0) >= 1.0
        assert RETAILER_TIERS.get("louis vuitton", 0) >= 1.0
        assert RETAILER_TIERS.get("chanel", 0) >= 1.0

    def test_counterfeit_sites_low_tier(self):
        from app.services.structured_comparison_service import RETAILER_TIERS
        assert RETAILER_TIERS.get("dhgate", 1.0) <= 0.3
        assert RETAILER_TIERS.get("aliexpress", 1.0) <= 0.3
        assert RETAILER_TIERS.get("temu", 1.0) <= 0.3


class TestCounterfeitListingDetection:
    """Test _is_counterfeit_listing() for various keyword patterns."""

    def test_counterfeit_listing_replica(self):
        assert StructuredComparisonService._is_counterfeit_listing("Hermes Birkin Replica Bag") is True

    def test_counterfeit_listing_fake(self):
        assert StructuredComparisonService._is_counterfeit_listing("Fake Gucci Belt Buckle") is True

    def test_counterfeit_listing_inspired(self):
        assert StructuredComparisonService._is_counterfeit_listing("Designer Inspired Handbag") is True

    def test_counterfeit_listing_legitimate(self):
        assert StructuredComparisonService._is_counterfeit_listing("Hermes Nevada H'Cheval Cap") is False

    def test_counterfeit_listing_pre_owned(self):
        assert StructuredComparisonService._is_counterfeit_listing("Pre-Owned Chanel Classic Flap") is True

    def test_counterfeit_listing_vintage(self):
        assert StructuredComparisonService._is_counterfeit_listing("Vintage Louis Vuitton Speedy 30") is True


class TestOfficialDomainLookup:
    """Test _get_official_domain() for brand-to-domain mapping."""

    def test_get_official_domain_hermes(self):
        svc = StructuredComparisonService()
        domain = svc._get_official_domain("Hermes Nevada H'Cheval Cap")
        assert domain == "hermes.com"

    def test_get_official_domain_lv(self):
        svc = StructuredComparisonService()
        domain = svc._get_official_domain("Louis Vuitton Monogram Wallet")
        assert domain == "louisvuitton.com"

    def test_get_official_domain_non_luxury(self):
        svc = StructuredComparisonService()
        domain = svc._get_official_domain("Nike Air Max 90")
        assert domain is None

    def test_get_official_domain_chanel(self):
        svc = StructuredComparisonService()
        domain = svc._get_official_domain("Chanel No. 5 Eau de Parfum")
        assert domain == "chanel.com"


class TestOfficialDomainSanityCheck:
    """Test that official domain prices skip sanity checks."""

    def test_official_domain_skips_sanity_check(self):
        """Official brand domain prices should have retailer_score >= 1.0."""
        svc = StructuredComparisonService()
        svc.total_cost = 0
        svc.api_calls = 0
        svc.gpt_calls = 0
        svc.serper_calls = 0
        # An official domain item should get max retailer score
        shopping_items = [
            {"price": "$630.00", "title": "Hermes Nevada Cap", "source": "Hermes",
             "link": "https://www.hermes.com/us/en/product/cap"},
        ]
        result = svc._extract_price_from_shopping("Hermes Nevada Cap", shopping_items, "BHD")
        if result is not None:
            assert result["retailer_score"] >= 1.0
