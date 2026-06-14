"""S3-genuine (team-lead live probe, 2026-06-14) — longer curl timeout for
BH-registry domains.

WRINKLE 1: gcc.luluhypermarket.com is 3.4s warm but the global
PAGE_SCRAPE_TIMEOUT=5 CLIPPED it cold (curl(28) timeout) — so the keystone broad
BH source intermittently returned nothing. Bahrain-tier registry curls get a
longer ~10s timeout; non-BH scrapes stay at 5s (don't slow the whole cascade).

The timeout is selected INSIDE curl_fetch_html from the URL's domain (every
caller unchanged). Tested via the pure selector + a mocked curl call asserting
the timeout that gets passed.
"""

import pytest

from app.services.price_service import (
    PAGE_SCRAPE_TIMEOUT,
    BH_REGISTRY_CURL_TIMEOUT,
    _curl_timeout_for_url,
)


class TestTimeoutSelector:
    def test_bahrain_registry_domain_gets_long_timeout(self):
        # gcc.lulu / sharafdg / extra are bahrain-tier registry rows.
        assert _curl_timeout_for_url(
            "https://gcc.luluhypermarket.com/en-bh/x/p/1"
        ) == BH_REGISTRY_CURL_TIMEOUT
        assert _curl_timeout_for_url(
            "https://bahrain.sharafdg.com/product/iphone-15/"
        ) == BH_REGISTRY_CURL_TIMEOUT

    def test_non_bh_domain_gets_default_timeout(self):
        assert _curl_timeout_for_url(
            "https://www.amazon.com/dp/B0XXX"
        ) == PAGE_SCRAPE_TIMEOUT
        assert _curl_timeout_for_url(
            "https://www.walmart.com/ip/123"
        ) == PAGE_SCRAPE_TIMEOUT

    def test_bh_timeout_is_longer(self):
        assert BH_REGISTRY_CURL_TIMEOUT > PAGE_SCRAPE_TIMEOUT
        assert BH_REGISTRY_CURL_TIMEOUT >= 10


class TestCurlFetchUsesSelectedTimeout:
    @pytest.mark.asyncio
    async def test_curl_fetch_passes_bh_timeout(self, monkeypatch):
        """curl_fetch_html must pass the BH timeout for a bahrain-registry URL."""
        from app.services import price_service as ps

        captured = {}

        class _Resp:
            status_code = 200
            text = "<html></html>"

        def _fake_get(url, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return _Resp()

        # Patch the curl_cffi requests.get used inside curl_fetch_html.
        import curl_cffi
        monkeypatch.setattr(curl_cffi.requests, "get", _fake_get)

        await ps.curl_fetch_html("https://gcc.luluhypermarket.com/en-bh/x/p/1")
        assert captured["timeout"] == BH_REGISTRY_CURL_TIMEOUT

    @pytest.mark.asyncio
    async def test_curl_fetch_passes_default_timeout_for_non_bh(self, monkeypatch):
        from app.services import price_service as ps

        captured = {}

        class _Resp:
            status_code = 200
            text = "<html></html>"

        def _fake_get(url, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return _Resp()

        import curl_cffi
        monkeypatch.setattr(curl_cffi.requests, "get", _fake_get)

        await ps.curl_fetch_html("https://www.amazon.com/dp/B0XXX")
        assert captured["timeout"] == PAGE_SCRAPE_TIMEOUT
