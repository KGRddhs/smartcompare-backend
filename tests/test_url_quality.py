"""Tests for URL quality — no search-page fallbacks as product links."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.structured_comparison_service import StructuredComparisonService


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
