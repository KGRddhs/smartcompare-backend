"""Tests for URL quality — no search-page fallbacks as product links."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.structured_comparison_service import StructuredComparisonService, get_comparison_service


@pytest.fixture
def service():
    return StructuredComparisonService()


class TestBuildRetailerUrl:
    """_build_retailer_url should return None for unknown retailers instead of Google fallback."""

    def test_known_retailer_returns_search_url(self, service):
        """Known retailers should still get a search URL."""
        url = service._build_retailer_url("Amazon", "iPhone 15")
        assert url is not None
        assert "amazon.com" in url

    def test_unknown_retailer_returns_none(self, service):
        """Unknown retailers should return None, not a Google Shopping fallback."""
        url = service._build_retailer_url("Random Unknown Store", "iPhone 15")
        assert url is None

    def test_empty_source_returns_none(self, service):
        """Empty source should return None."""
        url = service._build_retailer_url("", "iPhone 15")
        assert url is None


class TestShoppingUrlExtraction:
    """Price extraction should use Serper link directly when available."""

    def test_serper_link_used_directly(self, service):
        """When Serper provides a link, use it as-is."""
        items = [{
            "title": "iPhone 15 128GB",
            "price": "$799.00",
            "source": "Amazon",
            "link": "https://www.amazon.com/dp/B0CHBNQN5T"
        }]
        result = service._extract_price_from_shopping("iPhone 15", items, "USD")
        assert result is not None
        assert result["url"] == "https://www.amazon.com/dp/B0CHBNQN5T"

    def test_no_link_gets_retailer_search_url(self, service):
        """When Serper has no link, known retailer gets search URL."""
        items = [{
            "title": "iPhone 15 128GB",
            "price": "$799.00",
            "source": "Amazon",
            "link": ""
        }]
        result = service._extract_price_from_shopping("iPhone 15", items, "USD")
        assert result is not None
        assert "amazon.com" in result["url"]

    def test_no_link_unknown_retailer_gets_none_url(self, service):
        """When Serper has no link and retailer is unknown, URL should be None."""
        items = [{
            "title": "iPhone 15 128GB",
            "price": "$799.00",
            "source": "Some Random Shop",
            "link": ""
        }]
        result = service._extract_price_from_shopping("iPhone 15", items, "USD")
        assert result is not None
        # URL should be None for unknown retailer with no link
        assert result["url"] is None


class TestBuildRetailerUrlEdgeCases:
    """Additional edge cases for _build_retailer_url return type and behavior."""

    def test_return_type_is_optional_str(self, service):
        """Return type must be Optional[str], not str."""
        import inspect
        hints = inspect.get_annotations(service._build_retailer_url)
        assert hints.get("return") in (str | None, "Optional[str]") or "Optional" in str(hints.get("return", ""))

    def test_case_insensitive_retailer_match(self, service):
        """Retailer matching should be case-insensitive."""
        url = service._build_retailer_url("AMAZON", "Galaxy S24")
        assert url is not None
        assert "amazon.com" in url

    def test_bestbuy_with_space(self, service):
        """'Best Buy' (with space) should match."""
        url = service._build_retailer_url("Best Buy", "iPhone 15")
        assert url is not None
        assert "bestbuy.com" in url

    def test_gcc_retailer_noon(self, service):
        """GCC retailer 'Noon' should match."""
        url = service._build_retailer_url("Noon", "Galaxy S24")
        assert url is not None
        assert "noon.com" in url

    def test_gcc_retailer_jarir(self, service):
        """GCC retailer 'Jarir' should match."""
        url = service._build_retailer_url("Jarir Bookstore", "MacBook Pro")
        assert url is not None
        assert "jarir.com" in url

    def test_product_name_encoded_in_url(self, service):
        """Product name with spaces should be URL-encoded."""
        url = service._build_retailer_url("Amazon", "iPhone 15 Pro Max 256GB")
        assert url is not None
        assert "iPhone+15+Pro+Max+256GB" in url or "iPhone%2015%20Pro%20Max%20256GB" in url

    def test_whitespace_only_source_returns_none(self, service):
        """Whitespace-only source should return None."""
        url = service._build_retailer_url("   ", "iPhone 15")
        assert url is None

    def test_none_never_contains_google(self, service):
        """No unknown retailer should ever produce a google.com URL."""
        unknowns = ["RandomShop", "TechMart", "ShopXYZ", "MegaDeals", "  ", ""]
        for name in unknowns:
            url = service._build_retailer_url(name, "iPhone 15")
            if url is not None:
                assert "google.com" not in url, f"'{name}' produced Google fallback: {url}"

    def test_has_retailer_url_matches_build(self, service):
        """_has_retailer_url should return True iff _build_retailer_url returns non-None."""
        test_cases = [
            ("Amazon", True),
            ("Best Buy", True),
            ("Noon", True),
            ("Random Unknown", False),
            ("", False),
        ]
        for source, expected in test_cases:
            has = service._has_retailer_url(source)
            url = service._build_retailer_url(source, "test product")
            assert has == (url is not None), f"Mismatch for '{source}': _has={has}, url={url}"


class TestRatingUrlWithNullFallback:
    """Rating extraction should handle None URLs from _build_retailer_url."""

    def test_known_retailer_rating_has_url(self, service):
        """Rating from known retailer (Amazon) should have a URL."""
        items = [{
            "title": "Apple iPhone 16 256GB",
            "price": "$799.00",
            "source": "Amazon",
            "rating": 4.7,
            "ratingCount": 23000,
        }]
        result = service._extract_rating_from_shopping("Apple iPhone 16", items)
        assert result is not None
        assert result["rating_source"]["url"] is not None
        assert "amazon.com" in result["rating_source"]["url"]

    def test_unknown_retailer_rating_url_is_none_without_link(self, service):
        """Rating from unknown retailer without Serper link should have None URL."""
        items = [{
            "title": "Apple iPhone 16 256GB",
            "price": "$799.00",
            "source": "TechMart",
            "rating": 4.7,
            "ratingCount": 23000,
        }]
        result = service._extract_rating_from_shopping("Apple iPhone 16", items)
        assert result is not None
        assert result["rating_source"]["url"] is None

    def test_unknown_retailer_rating_uses_serper_link_when_present(self, service):
        """Rating from unknown retailer WITH Serper link should use that link."""
        items = [{
            "title": "Apple iPhone 16 256GB",
            "price": "$799.00",
            "source": "TechMart",
            "link": "https://techmart.com/iphone-16",
            "rating": 4.7,
            "ratingCount": 23000,
        }]
        result = service._extract_rating_from_shopping("Apple iPhone 16", items)
        assert result is not None
        assert result["rating_source"]["url"] == "https://techmart.com/iphone-16"


class TestPharmacyRetailerUrls:
    """Test pharmacy domains are in RETAILER_SEARCH_URLS."""

    def test_boots_url_generated(self):
        service = get_comparison_service()
        url = service._build_retailer_url("Boots Bahrain", "Vitamin D3 1000 IU")
        assert url is not None
        assert "bn.boots.com" in url
        assert "Vitamin" in url or "vitamin" in url.lower()

    def test_al_deerah_url_generated(self):
        service = get_comparison_service()
        url = service._build_retailer_url("Al Deerah Pharmacy", "HealthAid Vitamin D")
        assert url is not None
        assert "aldeerahpharmacy.com" in url

    def test_iherb_url_already_exists(self):
        service = get_comparison_service()
        url = service._build_retailer_url("iHerb", "NOW Vitamin D3")
        assert url is not None
        assert "iherb.com" in url

    def test_bolo_returns_none(self):
        """bolo.bh is a Vue SPA — should NOT have a search URL."""
        service = get_comparison_service()
        url = service._build_retailer_url("Bolo Pharmacy", "Vitamin D")
        assert url is None
