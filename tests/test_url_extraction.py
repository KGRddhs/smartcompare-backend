"""Tests for Serper Shopping link URL extraction in price and rating pipelines.

Verifies that _extract_price_from_shopping() and _extract_rating_from_shopping()
use the Serper Shopping `link` field (direct product page URL) as the primary URL,
falling back to _build_retailer_url() (retailer search page) when link is missing.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


# --- Price URL tests ---

def test_price_url_uses_serper_link_when_present(service):
    """When a Serper Shopping item has a `link` field, the price URL should use it."""
    items = [{
        "title": "Apple iPhone 16 256GB",
        "price": "$799.00",
        "source": "Best Buy",
        "link": "https://www.bestbuy.com/site/apple-iphone-16/12345.p",
        "rating": 4.7,
        "ratingCount": 23000,
    }]
    result = service._extract_price_from_shopping("Apple iPhone 16", items, "USD")
    assert result is not None
    assert result["url"] == "https://www.bestbuy.com/site/apple-iphone-16/12345.p"


def test_price_url_falls_back_to_retailer_search_when_no_link(service):
    """When a Serper Shopping item has no `link` field, fall back to retailer search URL."""
    items = [{
        "title": "Apple iPhone 16 256GB",
        "price": "$799.00",
        "source": "Best Buy",
        "rating": 4.7,
        "ratingCount": 23000,
    }]
    result = service._extract_price_from_shopping("Apple iPhone 16", items, "USD")
    assert result is not None
    assert "bestbuy.com" in result["url"]
    assert "searchpage" in result["url"]  # retailer search page, not product page


def test_price_url_falls_back_when_link_is_empty_string(service):
    """When `link` is an empty string, fall back to retailer search URL."""
    items = [{
        "title": "Apple iPhone 16 256GB",
        "price": "$799.00",
        "source": "Best Buy",
        "link": "",
        "rating": 4.7,
        "ratingCount": 23000,
    }]
    result = service._extract_price_from_shopping("Apple iPhone 16", items, "USD")
    assert result is not None
    assert "bestbuy.com" in result["url"]
    assert "searchpage" in result["url"]


def test_price_url_falls_back_when_link_is_none(service):
    """When `link` is explicitly None, fall back to retailer search URL."""
    items = [{
        "title": "Apple iPhone 16 256GB",
        "price": "$799.00",
        "source": "Best Buy",
        "link": None,
        "rating": 4.7,
        "ratingCount": 23000,
    }]
    result = service._extract_price_from_shopping("Apple iPhone 16", items, "USD")
    assert result is not None
    assert "bestbuy.com" in result["url"]


# --- Rating URL tests ---

def test_rating_url_uses_serper_link_when_present(service):
    """When a Serper Shopping item has a `link` field, the rating source URL should use it."""
    items = [{
        "title": "Apple iPhone 16 256GB",
        "price": "$799.00",
        "source": "Best Buy",
        "link": "https://www.bestbuy.com/site/apple-iphone-16/12345.p",
        "rating": 4.7,
        "ratingCount": 23000,
    }]
    result = service._extract_rating_from_shopping("Apple iPhone 16", items)
    assert result["rating"] == 4.7
    assert result["rating_source"]["url"] == "https://www.bestbuy.com/site/apple-iphone-16/12345.p"


def test_rating_url_falls_back_to_retailer_search_when_no_link(service):
    """When no `link` field, rating source URL should fall back to retailer search."""
    items = [{
        "title": "Apple iPhone 16 256GB",
        "price": "$799.00",
        "source": "Best Buy",
        "rating": 4.7,
        "ratingCount": 23000,
    }]
    result = service._extract_rating_from_shopping("Apple iPhone 16", items)
    assert result["rating"] == 4.7
    assert "bestbuy.com" in result["rating_source"]["url"]
    assert "searchpage" in result["rating_source"]["url"]


def test_rating_consensus_url_uses_serper_link(service):
    """Consensus rating (3+ unknown sellers same rating) should use the link from the best candidate.

    Consensus only triggers when NO tier1/tier2 candidates exist — all must be unknown/tier3
    with review_count > 1000 and 3+ sharing the same (rating, review_count).
    """
    # All unknown retailers (not in RETAILER_TIERS) with same rating+count → consensus
    items = [
        {
            "title": "Apple iPhone 16",
            "price": "$799.00",
            "source": "ShopXYZ",
            "link": "https://shopxyz.com/iphone16",
            "rating": 4.7,
            "ratingCount": 23000,
        },
        {
            "title": "Apple iPhone 16",
            "price": "$810.00",
            "source": "MegaDeals",
            "link": "https://megadeals.com/iphone16",
            "rating": 4.7,
            "ratingCount": 23000,
        },
        {
            "title": "Apple iPhone 16",
            "price": "$820.00",
            "source": "TechMart",
            "link": "https://techmart.com/iphone16",
            "rating": 4.7,
            "ratingCount": 23000,
        },
    ]
    result = service._extract_rating_from_shopping("Apple iPhone 16", items)
    assert result["rating"] == 4.7
    assert result["rating_source"]["extract_method"] == "google_shopping_consensus"
    # URL should be one of the Serper links (not a Google Shopping fallback)
    assert result["rating_source"]["url"] in [
        "https://shopxyz.com/iphone16",
        "https://megadeals.com/iphone16",
        "https://techmart.com/iphone16",
    ]


def test_rating_consensus_url_falls_back_when_no_link(service):
    """Consensus rating with no link fields should return None URL for unknown retailers."""
    # All unknown retailers, no link fields → consensus path, no URL
    items = [
        {
            "title": "Apple iPhone 16",
            "price": "$799.00",
            "source": "ShopXYZ",
            "rating": 4.7,
            "ratingCount": 23000,
        },
        {
            "title": "Apple iPhone 16",
            "price": "$810.00",
            "source": "MegaDeals",
            "rating": 4.7,
            "ratingCount": 23000,
        },
        {
            "title": "Apple iPhone 16",
            "price": "$820.00",
            "source": "TechMart",
            "rating": 4.7,
            "ratingCount": 23000,
        },
    ]
    result = service._extract_rating_from_shopping("Apple iPhone 16", items)
    assert result["rating"] == 4.7
    assert result["rating_source"]["extract_method"] == "google_shopping_consensus"
    # No link + unknown retailers → URL should be None (no fake Google fallback)
    assert result["rating_source"]["url"] is None
