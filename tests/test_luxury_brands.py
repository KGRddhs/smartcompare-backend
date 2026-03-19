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
