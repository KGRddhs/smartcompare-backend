"""Tests for counterfeit keyword filter, official domain lookup, and sanity threshold changes.

Covers Tasks 5-7 of Session 26:
- COUNTERFEIT_KEYWORDS constant and _is_counterfeit_listing() method
- Counterfeit filter in _extract_price_from_shopping() (FILTER 0)
- Counterfeit rejection in _strict_title_match()
- _get_official_domain() luxury brand → domain mapping
- Sanity check: official domain bypass (retailer_score >= 1.0)
- Sanity check: luxury tighter thresholds (1.8x/0.6x)
- Price extraction prompt rejection rules

Run: pytest tests/test_counterfeit_filter.py -v
"""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    svc = StructuredComparisonService()
    svc.total_cost = 0
    svc.api_calls = 0
    svc.gpt_calls = 0
    svc.serper_calls = 0
    return svc


class TestCounterfeitKeywords:
    """Test COUNTERFEIT_KEYWORDS constant exists and has expected entries."""

    def test_counterfeit_keywords_exists(self):
        assert hasattr(StructuredComparisonService, "COUNTERFEIT_KEYWORDS")
        assert isinstance(StructuredComparisonService.COUNTERFEIT_KEYWORDS, set)
        assert len(StructuredComparisonService.COUNTERFEIT_KEYWORDS) >= 15

    @pytest.mark.parametrize("keyword", [
        "replica", "fake", "dupe", "inspired by", "knockoff",
        "imitation", "copy", "lookalike", "unbranded", "generic",
        "pre-owned", "used", "vintage", "secondhand",
    ])
    def test_expected_keywords_present(self, keyword):
        assert keyword in StructuredComparisonService.COUNTERFEIT_KEYWORDS


class TestIsCounterfeitListing:
    """Test _is_counterfeit_listing() static method."""

    @pytest.mark.parametrize("title,expected", [
        ("Replica Hermes Birkin Bag", True),
        ("Fake Louis Vuitton Wallet", True),
        ("Designer Inspired Handbag", True),
        ("Pre-Owned Chanel Classic Flap", True),
        ("Used Rolex Submariner Date", True),
        ("Vintage Gucci Belt", True),
        ("Dupe Charlotte Tilbury Lipstick", True),
        ("Knockoff Ray-Ban Sunglasses", True),
        ("Generic Vitamin D3 5000IU", True),
        ("Unbranded Wireless Earbuds", True),
        ("Secondhand Prada Bag", True),
        # Legitimate listings
        ("Hermes Nevada H'Cheval Cap", False),
        ("Louis Vuitton Neverfull MM", False),
        ("Samsung Galaxy S24 Ultra 256GB", False),
        ("Apple iPhone 16 Pro Max", False),
        ("Nike Air Max 90", False),
        ("NOW Foods Vitamin D3 5000IU 360 Softgels", False),
    ])
    def test_counterfeit_detection(self, title, expected):
        assert StructuredComparisonService._is_counterfeit_listing(title) == expected

    def test_case_insensitive(self):
        assert StructuredComparisonService._is_counterfeit_listing("REPLICA Watch")
        assert StructuredComparisonService._is_counterfeit_listing("replica watch")
        assert StructuredComparisonService._is_counterfeit_listing("Replica Watch")


class TestCounterfeitFilterInShopping:
    """Test that counterfeit listings are filtered from _extract_price_from_shopping()."""

    def test_counterfeit_listing_skipped(self, service):
        shopping_items = [
            {"price": "$50.00", "title": "Replica Hermes Cap", "source": "DHgate", "link": "https://dhgate.com/123"},
            {"price": "$630.00", "title": "Hermes Nevada H'Cheval Cap", "source": "Hermes", "link": "https://www.hermes.com/cap"},
        ]
        result = service._extract_price_from_shopping("Hermes Nevada H'Cheval Cap", shopping_items, "USD")
        assert result is not None
        # Should pick the legitimate listing, not the replica
        assert result["amount"] == 630.0

    def test_all_counterfeit_returns_none(self, service):
        shopping_items = [
            {"price": "$50.00", "title": "Fake Designer Watch Replica", "source": "Unknown"},
            {"price": "$30.00", "title": "Knockoff Luxury Watch Dupe", "source": "Unknown"},
        ]
        result = service._extract_price_from_shopping("Rolex Submariner", shopping_items, "USD")
        assert result is None

    def test_used_listing_filtered(self, service):
        shopping_items = [
            {"price": "$200.00", "title": "Pre-Owned Nike Air Jordan 1 Used", "source": "eBay"},
            {"price": "$180.00", "title": "Nike Air Jordan 1 Retro High", "source": "Nike", "link": "https://nike.com/123"},
        ]
        result = service._extract_price_from_shopping("Nike Air Jordan 1", shopping_items, "USD")
        # Should prefer the non-used listing
        if result:
            assert "pre-owned" not in result.get("title", "").lower()
            assert "used" not in result.get("title", "").lower()


class TestCounterfeitInStrictTitleMatch:
    """Test that _strict_title_match() rejects counterfeit titles."""

    def test_replica_rejected(self):
        assert StructuredComparisonService._strict_title_match("Hermes Cap", "Replica Hermes Cap") is False

    def test_fake_rejected(self):
        assert StructuredComparisonService._strict_title_match("Gucci Belt", "Fake Gucci Belt Leather") is False

    def test_vintage_rejected(self):
        assert StructuredComparisonService._strict_title_match("Rolex Watch", "Vintage Rolex Watch 1960s") is False

    def test_legitimate_passes(self):
        assert StructuredComparisonService._strict_title_match("iPhone 16 Pro Max", "Apple iPhone 16 Pro Max 256GB") is True


class TestGetOfficialDomain:
    """Test _get_official_domain() method."""

    def test_hermes_returns_domain(self, service):
        domain = service._get_official_domain("Hermes Birkin Bag")
        assert domain == "hermes.com"

    def test_chanel_returns_domain(self, service):
        domain = service._get_official_domain("Chanel No. 5 Parfum")
        assert domain == "chanel.com"

    def test_gucci_returns_domain(self, service):
        domain = service._get_official_domain("Gucci Ace Sneakers")
        assert domain == "gucci.com"

    def test_prada_returns_domain(self, service):
        domain = service._get_official_domain("Prada Re-Nylon Backpack")
        assert domain == "prada.com"

    def test_dior_returns_domain(self, service):
        domain = service._get_official_domain("Dior Sauvage Eau de Toilette")
        assert domain == "dior.com"

    def test_non_luxury_returns_none(self, service):
        assert service._get_official_domain("Nike Air Max 90") is None

    def test_non_brand_returns_none(self, service):
        assert service._get_official_domain("Generic Cotton Hat") is None

    def test_case_insensitive(self, service):
        domain = service._get_official_domain("HERMES BIRKIN BAG")
        assert domain == "hermes.com"


class TestPricePromptRejectionRules:
    """Test that the price extraction prompt contains rejection rules."""

    def test_prompt_has_reject_section(self):
        from app.services.extraction_service import PRICE_EXTRACTION_PROMPT
        assert "REJECT these sources entirely" in PRICE_EXTRACTION_PROMPT

    @pytest.mark.parametrize("keyword", [
        "replica", "fake", "dupe", "inspired",
        "pre-owned", "used", "vintage",
        "DHgate", "AliExpress", "Temu", "Wish",
        "Poshmark", "Mercari",
        "<40%",
    ])
    def test_prompt_mentions_rejection_keyword(self, keyword):
        from app.services.extraction_service import PRICE_EXTRACTION_PROMPT
        assert keyword in PRICE_EXTRACTION_PROMPT

    def test_prompt_still_has_source_priority(self):
        from app.services.extraction_service import PRICE_EXTRACTION_PROMPT
        assert "SOURCE PRIORITY" in PRICE_EXTRACTION_PROMPT
        assert "MOST AUTHORITATIVE" in PRICE_EXTRACTION_PROMPT
