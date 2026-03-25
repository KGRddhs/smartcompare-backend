"""Tests for Firecrawl/Scrape.do integration in the price cascade.

Replaces old Cloudflare/Microlink JS rendering tests (removed Session 31).
_fetch_page_price is now curl_cffi only. JS rendering (Firecrawl/Scrape.do)
is handled at the cascade level in _get_price().
"""
import pytest
from unittest.mock import patch, AsyncMock
from app.services.structured_comparison_service import StructuredComparisonService


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
</head><body>Full rendered page content here with lots of text to exceed 1KB threshold.
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore
et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut
aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident.
Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.
Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.</body></html>
"""

NO_PRICE_HTML = """<html><head><title>Browse Luxury</title></head>
<body><p>Shop our collection.</p></body></html>""" + " " * 1500


@pytest.fixture
def service():
    svc = StructuredComparisonService.__new__(StructuredComparisonService)
    svc.total_cost = 0
    svc.api_calls = 0
    svc._shopping_items_cache = {}
    return svc


class TestFetchPagePriceCurlOnly:
    """_fetch_page_price is now curl_cffi only — no JS render fallback."""

    @pytest.mark.asyncio
    async def test_curl_success_returns_price(self, service):
        """When curl_cffi finds a price, it returns it directly."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=JSONLD_PRODUCT_HTML):
            result = await service._fetch_page_price(
                "https://ounass.ae/product/cap", "Louis Vuitton Cap", "BHD"
            )
        assert result is not None
        assert result["amount"] == 340.0
        assert result["source_method"] == "page_scrape"

    @pytest.mark.asyncio
    async def test_curl_html_no_price_returns_got_html(self, service):
        """curl_cffi gets HTML but no price -> returns _got_html marker for Scrape.do."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=NO_PRICE_HTML):
            result = await service._fetch_page_price(
                "https://ounass.ae/product/cap", "Louis Vuitton Cap", "BHD"
            )
        assert result is not None
        assert result.get("_got_html") is True

    @pytest.mark.asyncio
    async def test_curl_fails_returns_none(self, service):
        """curl_cffi fails entirely -> None (not a Scrape.do candidate)."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=None):
            result = await service._fetch_page_price(
                "https://ounass.ae/product/cap", "Louis Vuitton Cap", "BHD"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_page_scrape_disabled(self, service):
        """ENABLE_PAGE_SCRAPE=False -> None immediately."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", False):
            result = await service._fetch_page_price(
                "https://ounass.ae/product/cap", "Louis Vuitton Cap", "BHD"
            )
        assert result is None


class TestDeadCodeRemoved:
    """Verify old Cloudflare/Microlink code is completely removed."""

    def test_no_fetch_rendered_html_method(self):
        """_fetch_rendered_html is deleted."""
        svc = StructuredComparisonService.__new__(StructuredComparisonService)
        assert not hasattr(svc, '_fetch_rendered_html')

    def test_no_js_only_domains(self):
        """JS_ONLY_DOMAINS set is deleted."""
        assert not hasattr(StructuredComparisonService, 'JS_ONLY_DOMAINS')

    def test_no_js_render_timeout(self):
        """JS_RENDER_TIMEOUT constant is deleted."""
        import app.services.structured_comparison_service as mod
        assert not hasattr(mod, 'JS_RENDER_TIMEOUT')

    def test_no_enable_js_render_flag(self):
        """ENABLE_JS_RENDER flag is deleted."""
        import app.services.structured_comparison_service as mod
        assert not hasattr(mod, 'ENABLE_JS_RENDER')

    def test_no_render_provider_references(self):
        """RENDER_PROVIDER env var no longer used in service code."""
        import app.services.structured_comparison_service as mod
        import inspect
        source = inspect.getsource(mod)
        assert "RENDER_PROVIDER" not in source

    def test_no_cloudflare_references_in_service(self):
        """No CLOUDFLARE_ACCOUNT_ID/API_TOKEN references in service code."""
        import app.services.structured_comparison_service as mod
        import inspect
        source = inspect.getsource(mod)
        assert "CLOUDFLARE_ACCOUNT_ID" not in source
        assert "CLOUDFLARE_API_TOKEN" not in source

    def test_no_microlink_references_in_service(self):
        """No MICROLINK_API_KEY references in service code."""
        import app.services.structured_comparison_service as mod
        import inspect
        source = inspect.getsource(mod)
        assert "MICROLINK_API_KEY" not in source


class TestNewServicesImported:
    """Verify Firecrawl and Scrape.do services are properly imported."""

    def test_firecrawl_service_imported(self):
        import app.services.structured_comparison_service as mod
        assert hasattr(mod, 'firecrawl_service')

    def test_scrapedo_service_imported(self):
        import app.services.structured_comparison_service as mod
        assert hasattr(mod, 'scrapedo_service')

    def test_budget_functions_imported(self):
        import app.services.structured_comparison_service as mod
        assert hasattr(mod, 'has_budget')
        assert hasattr(mod, 'record_usage')
        assert hasattr(mod, 'record_failure')
        assert hasattr(mod, 'record_success')
        assert hasattr(mod, 'is_circuit_closed')
