"""Tests for JS rendering fallback in _fetch_page_price."""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
import app.services.structured_comparison_service as scs_module
from app.services.structured_comparison_service import (
    StructuredComparisonService, ENABLE_PAGE_SCRAPE, ENABLE_JS_RENDER,
)


class MockAsyncClient:
    """Mock httpx.AsyncClient that supports async context manager."""
    def __init__(self, mock_client):
        self._mock = mock_client
    def __call__(self, *args, **kwargs):
        return self
    async def __aenter__(self):
        return self._mock
    async def __aexit__(self, *args):
        pass


def _patch_httpx(mock_client):
    """Patch httpx module in structured_comparison_service with mock async client."""
    mock_httpx = MagicMock()
    mock_httpx.AsyncClient = MockAsyncClient(mock_client)
    return patch.object(scs_module, "httpx", mock_httpx)


# --- HTML fixtures (same as test_page_scraping.py) ---

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

SMALL_HTML = "<html><body>tiny</body></html>"

NO_PRICE_HTML = """<html><head><title>Browse Luxury</title></head>
<body><p>Shop our collection.</p></body></html>""" + " " * 1500  # Pad to >1KB


@pytest.fixture
def service():
    svc = StructuredComparisonService.__new__(StructuredComparisonService)
    svc.total_cost = 0
    svc.api_calls = 0
    svc._shopping_items_cache = {}
    return svc


class TestFetchRenderedHtml:
    """Tests for _fetch_rendered_html() — parallel JS rendering."""

    @pytest.mark.asyncio
    async def test_cloudflare_success(self, service):
        """Cloudflare returns valid HTML."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": JSONLD_PRODUCT_HTML}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "test123", "CLOUDFLARE_API_TOKEN": "tok", "RENDER_PROVIDER": "cloudflare"}):
            with _patch_httpx(mock_client):
                result = await service._fetch_rendered_html("https://louisvuitton.com/cap")
        assert result is not None
        assert len(result) > 1000
        assert "Louis Vuitton" in result

    @pytest.mark.asyncio
    async def test_microlink_success(self, service):
        """Microlink returns valid HTML."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"html": JSONLD_PRODUCT_HTML}}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        with patch.dict(os.environ, {"RENDER_PROVIDER": "microlink"}):
            with _patch_httpx(mock_client):
                result = await service._fetch_rendered_html("https://louisvuitton.com/cap")
        assert result is not None
        assert "Louis Vuitton" in result

    @pytest.mark.asyncio
    async def test_both_fail_returns_none(self, service):
        """Both providers fail -> returns None."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.post.return_value = mock_resp

        with patch.dict(os.environ, {"RENDER_PROVIDER": "both", "CLOUDFLARE_ACCOUNT_ID": "", "CLOUDFLARE_API_TOKEN": ""}):
            with _patch_httpx(mock_client):
                result = await service._fetch_rendered_html("https://louisvuitton.com/cap")
        assert result is None

    @pytest.mark.asyncio
    async def test_small_html_rejected(self, service):
        """HTML < 1000 bytes is treated as empty/blocked."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": SMALL_HTML}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "test", "CLOUDFLARE_API_TOKEN": "tok", "RENDER_PROVIDER": "cloudflare"}):
            with _patch_httpx(mock_client):
                result = await service._fetch_rendered_html("https://hermes.com/cap")
        assert result is None

    @pytest.mark.asyncio
    async def test_feature_flag_disabled(self, service):
        """ENABLE_JS_RENDER=false disables rendering."""
        with patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False):
            result = await service._fetch_rendered_html("https://louisvuitton.com/cap")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_cloudflare_credentials_skips(self, service):
        """Missing Cloudflare env vars -> returns None for cloudflare provider."""
        with patch.dict(os.environ, {"RENDER_PROVIDER": "cloudflare"}, clear=False):
            # Ensure CF vars are absent
            env = os.environ.copy()
            env.pop("CLOUDFLARE_ACCOUNT_ID", None)
            env.pop("CLOUDFLARE_API_TOKEN", None)
            with patch.dict(os.environ, env, clear=True):
                result = await service._fetch_rendered_html("https://louisvuitton.com/cap")
        assert result is None


class TestFetchPagePriceWithJsRender:
    """Integration: _fetch_page_price with JS rendering fallback."""

    @pytest.mark.asyncio
    async def test_curl_success_skips_js_render(self, service):
        """When curl_cffi finds a price, JS rendering is never called."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", True), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=JSONLD_PRODUCT_HTML), \
             patch.object(service, '_fetch_rendered_html', new_callable=AsyncMock) as mock_render:
            result = await service._fetch_page_price(
                "https://iherb.com/product", "Louis Vuitton Cap", "BHD"
            )
        assert result is not None
        assert result["amount"] == 340.0
        assert result["source_method"] == "page_scrape"  # NOT page_scrape_rendered
        mock_render.assert_not_called()

    @pytest.mark.asyncio
    async def test_curl_fails_triggers_js_render(self, service):
        """When curl_cffi returns no data, JS rendering is tried."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", True), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=None), \
             patch.object(service, '_fetch_rendered_html', new_callable=AsyncMock, return_value=JSONLD_PRODUCT_HTML):
            result = await service._fetch_page_price(
                "https://unknown-shop.com/product", "Louis Vuitton Cap", "BHD"
            )
        assert result is not None
        assert result["source_method"] == "page_scrape_rendered"

    @pytest.mark.asyncio
    async def test_js_only_domain_skips_curl(self, service):
        """JS_ONLY_DOMAINS skip curl_cffi entirely."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", True), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock) as mock_curl, \
             patch.object(service, '_fetch_rendered_html', new_callable=AsyncMock, return_value=JSONLD_PRODUCT_HTML):
            result = await service._fetch_page_price(
                "https://louisvuitton.com/cap", "Louis Vuitton Cap", "BHD"
            )
        mock_curl.assert_not_called()
        assert result is not None
        assert result["source_method"] == "page_scrape_rendered"

    @pytest.mark.asyncio
    async def test_both_fail_returns_none(self, service):
        """curl_cffi + JS render both fail -> None."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", True), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=None), \
             patch.object(service, '_fetch_rendered_html', new_callable=AsyncMock, return_value=None):
            result = await service._fetch_page_price(
                "https://unknown-shop.com/product", "Louis Vuitton Cap", "BHD"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_js_render_disabled_only_curl(self, service):
        """ENABLE_JS_RENDER=false -> only curl_cffi attempted."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", False), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=None), \
             patch.object(service, '_fetch_rendered_html', new_callable=AsyncMock) as mock_render:
            result = await service._fetch_page_price(
                "https://unknown-shop.com/product", "Louis Vuitton Cap", "BHD"
            )
        assert result is None
        mock_render.assert_not_called()

    @pytest.mark.asyncio
    async def test_rendered_html_no_price_returns_none(self, service):
        """JS render returns HTML but no structured price -> None."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch("app.services.structured_comparison_service.ENABLE_JS_RENDER", True), \
             patch.object(service, '_curl_fetch_html', new_callable=AsyncMock, return_value=None), \
             patch.object(service, '_fetch_rendered_html', new_callable=AsyncMock, return_value=NO_PRICE_HTML):
            result = await service._fetch_page_price(
                "https://louisvuitton.com/browse", "Louis Vuitton Cap", "BHD"
            )
        assert result is None


class TestJsOnlyDomains:
    """Verify JS_ONLY_DOMAINS constant."""

    def test_luxury_brands_in_js_only(self):
        """Key luxury brands are in JS_ONLY_DOMAINS."""
        domains = StructuredComparisonService.JS_ONLY_DOMAINS
        assert "louisvuitton.com" in domains
        assert "hermes.com" in domains
        assert "chanel.com" in domains
        assert "farfetch.com" in domains
        assert "nordstrom.com" in domains

    def test_non_luxury_not_in_js_only(self):
        """Non-luxury domains are NOT in JS_ONLY_DOMAINS."""
        domains = StructuredComparisonService.JS_ONLY_DOMAINS
        assert "iherb.com" not in domains
        assert "amazon.com" not in domains
        assert "bn.boots.com" not in domains
