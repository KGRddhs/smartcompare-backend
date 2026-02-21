"""Tests for Bahrain pharmacy JSON-LD price extraction."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


# --- JSON-LD parsing tests ---

def test_extracts_price_from_valid_product_jsonld(service):
    """Standard Product JSON-LD with offers.price."""
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@type": "Product", "name": "HealthAid Vitamin D3 1000iu Tablet Pack of 120",
     "offers": {"@type": "Offer", "price": 9, "priceCurrency": "BHD",
                "availability": "https://schema.org/InStock"}}
    </script>
    </head><body></body></html>
    '''
    result = service._extract_jsonld_price(html, "HealthAid", "BHD")
    assert result is not None
    assert result["amount"] == 9.0
    assert result["currency"] == "BHD"
    assert result["in_stock"] is True


def test_extracts_price_from_offers_array(service):
    """Product with offers as array — pick lowest BHD price."""
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@type": "Product", "name": "HealthAid Vitamin D3 1000IU",
     "offers": [
       {"@type": "Offer", "price": 12.5, "priceCurrency": "BHD"},
       {"@type": "Offer", "price": 9.0, "priceCurrency": "BHD"}
     ]}
    </script>
    </head><body></body></html>
    '''
    result = service._extract_jsonld_price(html, "HealthAid", "BHD")
    assert result["amount"] == 9.0


def test_skips_wrong_currency(service):
    """Skip offers with non-BHD currency."""
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@type": "Product", "name": "HealthAid D3",
     "offers": {"@type": "Offer", "price": 5.99, "priceCurrency": "USD"}}
    </script>
    </head><body></body></html>
    '''
    result = service._extract_jsonld_price(html, "HealthAid", "BHD")
    assert result is None


def test_skips_wrong_brand(service):
    """Skip if brand name not in JSON-LD product name."""
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@type": "Product", "name": "NOW Foods Vitamin D-3 360 Softgels",
     "offers": {"@type": "Offer", "price": 4.5, "priceCurrency": "BHD"}}
    </script>
    </head><body></body></html>
    '''
    result = service._extract_jsonld_price(html, "HealthAid", "BHD")
    assert result is None


def test_matches_brand_with_spaces(service):
    """'HealthAid' should match 'Health Aid' (space-insensitive)."""
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@type": "Product", "name": "Health Aid Vitamin D3 1000iu 30 Tablets",
     "offers": {"@type": "Offer", "price": 6.3, "priceCurrency": "BHD"}}
    </script>
    </head><body></body></html>
    '''
    result = service._extract_jsonld_price(html, "HealthAid", "BHD")
    assert result is not None
    assert result["amount"] == 6.3


def test_returns_none_for_no_jsonld(service):
    """No JSON-LD on page."""
    html = '<html><head></head><body><p>No data</p></body></html>'
    result = service._extract_jsonld_price(html, "HealthAid", "BHD")
    assert result is None


def test_handles_nested_graph_jsonld(service):
    """Some sites wrap Product in @graph array."""
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@graph": [
      {"@type": "WebSite", "name": "Bolo"},
      {"@type": "Product", "name": "HealthAid D3 1000IU 120 Tablets",
       "offers": {"@type": "Offer", "price": 9.0, "priceCurrency": "BHD"}}
    ]}
    </script>
    </head><body></body></html>
    '''
    result = service._extract_jsonld_price(html, "HealthAid", "BHD")
    assert result is not None
    assert result["amount"] == 9.0


def test_handles_string_price(service):
    """Price as string '9.00' instead of number."""
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@type": "Product", "name": "HealthAid D3",
     "offers": {"@type": "Offer", "price": "9.00", "priceCurrency": "BHD"}}
    </script>
    </head><body></body></html>
    '''
    result = service._extract_jsonld_price(html, "HealthAid", "BHD")
    assert result["amount"] == 9.0


def test_detects_out_of_stock(service):
    """OutOfStock availability."""
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@type": "Product", "name": "HealthAid D3",
     "offers": {"@type": "Offer", "price": 9.0, "priceCurrency": "BHD",
                "availability": "https://schema.org/OutOfStock"}}
    </script>
    </head><body></body></html>
    '''
    result = service._extract_jsonld_price(html, "HealthAid", "BHD")
    assert result is not None
    assert result["in_stock"] is False


# --- _fetch_pharmacy_price tests ---

BOLO_HTML = '''
<html><head>
<script type="application/ld+json">
{"@type": "Product", "name": "HealthAid Vitamin D3 1000iu Tablet Pack of 120",
 "offers": {"@type": "Offer", "price": 9, "priceCurrency": "BHD",
            "availability": "https://schema.org/InStock"}}
</script>
</head><body></body></html>
'''


def test_fetch_pharmacy_price_finds_bolo_url(service):
    """Finds bolo.bh URL in Serper results and extracts JSON-LD price."""
    serper_organic = [
        {"title": "Some irrelevant result", "link": "https://www.google.com/shopping/123"},
        {"title": "HealthAid Vitamin D3 1000IU", "link": "https://www.bolo.bh/products/healthaid-d3"},
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = BOLO_HTML

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = asyncio.get_event_loop().run_until_complete(
            service._fetch_pharmacy_price(serper_organic, "HealthAid", "HealthAid Vitamin D3 1000IU", "BHD")
        )

    assert result is not None
    assert result["amount"] == 9.0
    assert result["retailer"] == "Bolo"
    assert result["url"] == "https://www.bolo.bh/products/healthaid-d3"
    assert result["estimated"] is False


def test_fetch_pharmacy_price_returns_none_for_no_pharmacy_urls(service):
    """Returns None when no Serper URLs match pharmacy domains and site search also fails."""
    serper_organic = [
        {"title": "Some result", "link": "https://www.amazon.com/something"},
    ]
    with patch("app.services.structured_comparison_service.search_web", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"organic": []}
        result = asyncio.get_event_loop().run_until_complete(
            service._fetch_pharmacy_price(serper_organic, "HealthAid", "HealthAid D3", "BHD")
        )
    assert result is None


def test_fetch_pharmacy_price_skips_failed_fetches(service):
    """Skips pharmacy URLs that return non-200 or timeout."""
    serper_organic = [
        {"title": "HealthAid D3", "link": "https://www.bolo.bh/products/healthaid-d3"},
    ]

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = asyncio.get_event_loop().run_until_complete(
            service._fetch_pharmacy_price(serper_organic, "HealthAid", "HealthAid D3", "BHD")
        )

    assert result is None
