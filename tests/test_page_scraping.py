"""Tests for _fetch_page_price() — generic page scraping with structured data extraction."""
import sys
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.structured_comparison_service import StructuredComparisonService, ENABLE_PAGE_SCRAPE


# Ensure curl_cffi is available as a mock module so the local import inside
# _curl_fetch_html doesn't raise ModuleNotFoundError.
_mock_curl_get = MagicMock()
_mock_curl_requests = MagicMock()
_mock_curl_requests.get = _mock_curl_get
_mock_curl_cffi = MagicMock()
_mock_curl_cffi.requests = _mock_curl_requests
if "curl_cffi" not in sys.modules:
    sys.modules["curl_cffi"] = _mock_curl_cffi
    sys.modules["curl_cffi.requests"] = _mock_curl_requests


# --- HTML fixtures ---

JSONLD_PRODUCT_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Louis Vuitton Vers Mesh Cap",
  "brand": {"@type": "Brand", "name": "Louis Vuitton"},
  "offers": {
    "@type": "Offer",
    "price": "340.000",
    "priceCurrency": "BHD",
    "availability": "https://schema.org/InStock"
  }
}
</script>
</head><body></body></html>
"""

JSONLD_USD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Hermes Nevada Cap",
  "brand": {"@type": "Brand", "name": "Hermes"},
  "offers": {
    "@type": "Offer",
    "price": "700.00",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock"
  }
}
</script>
</head><body></body></html>
"""

JSONLD_OUT_OF_STOCK_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Louis Vuitton Cap",
  "brand": {"@type": "Brand", "name": "Louis Vuitton"},
  "offers": {
    "@type": "Offer",
    "price": "340.000",
    "priceCurrency": "BHD",
    "availability": "https://schema.org/OutOfStock"
  }
}
</script>
</head><body></body></html>
"""

JSONLD_NESTED_OFFERS_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Gucci Belt",
  "brand": {"@type": "Brand", "name": "Gucci"},
  "offers": [
    {"@type": "Offer", "price": "450.00", "priceCurrency": "USD"},
    {"@type": "Offer", "price": "425.00", "priceCurrency": "USD"}
  ]
}
</script>
</head><body></body></html>
"""

OG_META_HTML = """
<html><head>
<meta property="og:price:amount" content="280.00">
<meta property="og:price:currency" content="AED">
<meta property="og:title" content="Louis Vuitton Cap">
</head><body></body></html>
"""

PRODUCT_META_HTML = """
<html><head>
<meta property="product:price:amount" content="650.00">
<meta property="product:price:currency" content="USD">
</head><body></body></html>
"""

MICRODATA_HTML = """
<html><body>
<div itemscope itemtype="https://schema.org/Product">
  <span itemprop="name">Hermes Cap</span>
  <span itemprop="priceCurrency" content="EUR">EUR</span>
  <span itemprop="price" content="590.00">590,00 EUR</span>
</div>
</body></html>
"""

NO_PRICE_HTML = """
<html><head><title>Browse Luxury Caps</title></head>
<body><p>Shop our collection of luxury accessories.</p></body></html>
"""

EMPTY_HTML = ""


@pytest.fixture
def service():
    svc = StructuredComparisonService.__new__(StructuredComparisonService)
    svc.total_cost = 0
    svc.api_calls = 0
    svc._shopping_items_cache = {}
    return svc


class TestFetchPagePriceJsonLD:
    """Tests for JSON-LD extraction (Priority 1)."""

    @pytest.mark.asyncio
    async def test_jsonld_bhd_product(self, service):
        """JSON-LD with BHD currency extracts correctly without conversion."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=JSONLD_PRODUCT_HTML):
            result = await service._fetch_page_price(
                "https://shop.example.com/cap", "Louis Vuitton Vers Mesh Cap", "BHD"
            )
        assert result is not None
        assert result["amount"] == 340.0
        assert result["source_method"] == "page_scrape"
        assert result["retailer"] == "shop.example.com"
        assert result["estimated"] is False
        assert result["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_jsonld_usd_conversion(self, service):
        """JSON-LD with USD triggers currency conversion to BHD."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=JSONLD_USD_HTML):
            result = await service._fetch_page_price(
                "https://shop.example.com/cap", "Hermes Nevada Cap", "BHD"
            )
        assert result is not None
        # USD 700 should be converted to BHD (approx 263.9 at 0.377 rate)
        assert result["amount"] > 0
        assert result["source_method"] == "page_scrape"

    @pytest.mark.asyncio
    async def test_jsonld_out_of_stock(self, service):
        """Out-of-stock products still return price but in_stock=False."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=JSONLD_OUT_OF_STOCK_HTML):
            result = await service._fetch_page_price(
                "https://shop.example.com/cap", "Louis Vuitton Cap", "BHD"
            )
        assert result is not None
        assert result["in_stock"] is False
        assert result["amount"] == 340.0

    @pytest.mark.asyncio
    async def test_jsonld_nested_offers_picks_lowest(self, service):
        """Multiple offers picks the lowest price (handled by _extract_jsonld_price)."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=JSONLD_NESTED_OFFERS_HTML):
            result = await service._fetch_page_price(
                "https://shop.example.com/belt", "Gucci Belt", "USD"
            )
        assert result is not None
        assert result["amount"] == 425.0


class TestFetchPagePriceOpenGraph:
    """Tests for OpenGraph meta extraction (Priority 2)."""

    @pytest.mark.asyncio
    async def test_og_meta_extraction(self, service):
        """OpenGraph meta tags extract price and currency."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=OG_META_HTML):
            result = await service._fetch_page_price(
                "https://ounass.ae/lv-cap", "Louis Vuitton Cap", "BHD"
            )
        assert result is not None
        assert result["amount"] > 0
        assert result["source_method"] == "page_scrape"
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_product_meta_fallback(self, service):
        """product:price:amount meta tags work as OG fallback."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=PRODUCT_META_HTML):
            result = await service._fetch_page_price(
                "https://shop.example.com/lv", "Louis Vuitton Cap", "BHD"
            )
        assert result is not None
        assert result["amount"] > 0


class TestFetchPagePriceMicrodata:
    """Tests for microdata extraction (Priority 3)."""

    @pytest.mark.asyncio
    async def test_microdata_extraction(self, service):
        """itemprop=price microdata extracts correctly."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=MICRODATA_HTML):
            result = await service._fetch_page_price(
                "https://shop.example.com/cap", "Hermes Cap", "BHD"
            )
        assert result is not None
        assert result["amount"] > 0
        assert result["confidence"] == 0.8


class TestFetchPagePriceEdgeCases:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_no_structured_data_returns_none(self, service):
        """Pages with no structured price data return None."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=NO_PRICE_HTML):
            result = await service._fetch_page_price(
                "https://shop.example.com/browse", "Hermes Cap", "BHD"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self, service):
        """HTTP 403/404/500 returns None gracefully (curl_fetch_html returns None)."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=None):
            result = await service._fetch_page_price(
                "https://shop.example.com/cap", "Hermes Cap", "BHD"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self, service):
        """Network timeout returns None gracefully (curl_fetch_html handles it)."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=None):
            result = await service._fetch_page_price(
                "https://shop.example.com/cap", "Hermes Cap", "BHD"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_html_returns_none(self, service):
        """Empty HTML returns None."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=EMPTY_HTML):
            result = await service._fetch_page_price(
                "https://shop.example.com/cap", "Hermes Cap", "BHD"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_feature_flag_disabled(self, service):
        """Feature flag ENABLE_PAGE_SCRAPE=false disables scraping entirely."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", False):
            result = await service._fetch_page_price(
                "https://shop.example.com/cap", "Hermes Cap", "BHD"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_zero_price_returns_none(self, service):
        """JSON-LD with price=0 is rejected by _extract_jsonld_price."""
        html = JSONLD_PRODUCT_HTML.replace('"340.000"', '"0"')
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=html):
            result = await service._fetch_page_price(
                "https://shop.example.com/cap", "Louis Vuitton Cap", "BHD"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_domain_extracted_from_url(self, service):
        """Retailer name is the domain extracted from URL with www. stripped."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=JSONLD_PRODUCT_HTML):
            result = await service._fetch_page_price(
                "https://www.shop.example.com/products/cap", "Louis Vuitton Cap", "BHD"
            )
        assert result is not None
        assert result["retailer"] == "shop.example.com"  # www. stripped

    @pytest.mark.asyncio
    async def test_url_preserved_in_result(self, service):
        """The original URL is preserved in the result."""
        url = "https://shop.example.com/products/cap-123"
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=JSONLD_PRODUCT_HTML):
            result = await service._fetch_page_price(
                url, "Louis Vuitton Vers Mesh Cap", "BHD"
            )
        assert result is not None
        assert result["url"] == url
