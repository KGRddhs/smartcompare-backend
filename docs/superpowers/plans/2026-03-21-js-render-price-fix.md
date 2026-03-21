# JS Rendering for Luxury Price Extraction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JS rendering fallback (Cloudflare Browser Rendering + Microlink) to `_fetch_page_price()` so luxury brand prices are extracted from fully-rendered HTML instead of empty JS shells.

**Architecture:** Refactor `_fetch_page_price()` into three parts: `_curl_fetch_html()` (existing HTTP fetch), `_extract_price_from_html()` (shared extraction logic), and `_fetch_rendered_html()` (new JS rendering). When curl_cffi finds no data, fire both renderers in parallel and use the first valid result.

**Tech Stack:** Python 3.12, httpx (existing), asyncio.gather, Cloudflare Browser Rendering REST API, Microlink REST API

**Spec:** `docs/superpowers/specs/2026-03-21-js-render-price-fix-design.md`

**Team:** 2 Opus agents — Implementer + QA. Cross-QA before disband.

---

## File Structure

| File | Role | Action |
|------|------|--------|
| `app/services/structured_comparison_service.py` | Core service — price pipeline | Modify (refactor `_fetch_page_price`, add `_extract_price_from_html`, `_curl_fetch_html`, `_fetch_rendered_html`, new constants) |
| `tests/test_js_rendering.py` | Unit tests for JS rendering | Create |
| `tests/test_page_scraping.py` | Existing page scraping tests | Modify (update for refactored method signatures) |

---

## Task 1: Add Constants, Feature Flag, and `JS_ONLY_DOMAINS`

**Owner:** Implementer
**Files:**
- Modify: `app/services/structured_comparison_service.py:34` (add `ENABLE_JS_RENDER` next to `ENABLE_PAGE_SCRAPE`)
- Modify: `app/services/structured_comparison_service.py:1350-1351` (add class attributes, reduce `PAGE_SCRAPE_TIMEOUT`)

- [ ] **Step 1: Add `ENABLE_JS_RENDER` module-level constant**

After line 34 (`ENABLE_PAGE_SCRAPE = ...`), add:

```python
ENABLE_JS_RENDER = os.environ.get("ENABLE_JS_RENDER", "true").lower() != "false"
```

- [ ] **Step 2: Add class attributes after `TIER_15_BUDGET_TIMEOUT` (line 1351)**

```python
    # Domains known to block curl_cffi or serve JS shells — skip straight to JS render
    JS_ONLY_DOMAINS = {
        "louisvuitton.com", "hermes.com", "chanel.com", "gucci.com",
        "prada.com", "dior.com", "farfetch.com", "net-a-porter.com",
        "nordstrom.com", "neimanmarcus.com", "ssense.com", "mytheresa.com",
        "burberry.com", "balenciaga.com", "fendi.com", "valentino.com",
    }

    JS_RENDER_TIMEOUT = 8  # seconds per JS rendering provider
```

- [ ] **Step 3: Reduce `PAGE_SCRAPE_TIMEOUT` from 10 to 5**

Change line 1350 from:
```python
    PAGE_SCRAPE_TIMEOUT = 10  # seconds per individual page fetch
```
To:
```python
    PAGE_SCRAPE_TIMEOUT = 5  # seconds per curl_cffi page fetch (reduced; JS render has separate timeout)
```

- [ ] **Step 4: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat(price): add JS rendering constants, ENABLE_JS_RENDER flag, JS_ONLY_DOMAINS"
```

---

## Task 2: Extract `_extract_price_from_html()` and `_curl_fetch_html()` Helpers

**Owner:** Implementer
**Files:**
- Modify: `app/services/structured_comparison_service.py:1870-1999` (refactor `_fetch_page_price`)

**Context:** The current `_fetch_page_price()` (lines 1870-1999) does both HTTP fetching AND HTML parsing in one method. We need to split these so the same extraction logic can be reused for JS-rendered HTML. The extraction logic (lines 1912-1993) moves to `_extract_price_from_html()`. The curl_cffi fetch (lines 1892-1910) moves to `_curl_fetch_html()`.

- [ ] **Step 1: Add `_curl_fetch_html()` method before `_fetch_page_price` (before line 1870)**

```python
    async def _curl_fetch_html(self, url: str) -> Optional[str]:
        """Fetch raw HTML via curl_cffi (no JS rendering). Returns HTML string or None."""
        try:
            from curl_cffi import requests as curl_requests
            resp = await asyncio.to_thread(
                lambda: curl_requests.get(
                    url,
                    impersonate="chrome",
                    timeout=self.PAGE_SCRAPE_TIMEOUT,
                    allow_redirects=True,
                )
            )
            if resp.status_code != 200:
                domain = urlparse(url).netloc.replace("www.", "")
                logger.info(f"[PRICE] Page scrape: HTTP {resp.status_code} for {domain}")
                return None
            return resp.text
        except Exception as e:
            logger.warning(f"[PRICE] curl_cffi fetch failed for {url}: {e}")
            return None
```

- [ ] **Step 2: Add `_extract_price_from_html()` method after `_curl_fetch_html`**

```python
    def _extract_price_from_html(
        self, html: str, product_name: str, currency: str, domain: str, url: str
    ) -> Optional[Dict[str, Any]]:
        """Extract price from HTML using structured data (JSON-LD, OG, microdata).

        Sync helper — no I/O, just HTML parsing. Reuses existing
        _extract_jsonld_price() for JSON-LD, adds OG and microdata fallbacks.
        """
        from bs4 import BeautifulSoup
        brand = product_name.split()[0] if product_name else ""

        # Priority 1: JSON-LD (reuse existing method)
        price_data = self._extract_jsonld_price(html, brand, currency)
        if not price_data:
            # Try USD — convert later
            price_data = self._extract_jsonld_price(html, brand, "USD")
            if price_data:
                price_data["_needs_conversion"] = True

        if price_data and price_data.get("amount"):
            logger.info(f"[PRICE] Page scrape: JSON-LD price {price_data['amount']} {price_data.get('currency', currency)} from {domain}")
            result = {
                "amount": price_data["amount"],
                "original_currency": price_data.get("currency", currency),
                "currency": price_data.get("currency", currency),
                "retailer": domain,
                "url": url,
                "in_stock": price_data.get("in_stock", True),
                "confidence": 1.0,
                "estimated": False,
                "source_method": "page_scrape",
            }
            if price_data.get("_needs_conversion") or result["currency"].upper() != currency.upper():
                self._convert_gpt_price_currency(result, currency)
            return result

        # Priority 2: OpenGraph meta tags
        soup = BeautifulSoup(html, 'html.parser')
        og_price = soup.find('meta', property='og:price:amount')
        og_currency = soup.find('meta', property='og:price:currency')
        if not og_price:
            og_price = soup.find('meta', property='product:price:amount')
            og_currency = soup.find('meta', property='product:price:currency')

        if og_price and og_price.get('content'):
            try:
                amount = float(og_price['content'])
                if amount > 0:
                    detected_currency = og_currency['content'] if og_currency and og_currency.get('content') else "USD"
                    logger.info(f"[PRICE] Page scrape: OG meta price {amount} {detected_currency} from {domain}")
                    result = {
                        "amount": amount, "original_currency": detected_currency,
                        "currency": detected_currency, "retailer": domain, "url": url,
                        "in_stock": True, "confidence": 0.9, "estimated": False,
                        "source_method": "page_scrape",
                    }
                    if detected_currency.upper() != currency.upper():
                        self._convert_gpt_price_currency(result, currency)
                    return result
            except (ValueError, TypeError):
                pass

        # Priority 3: Microdata itemprop="price"
        price_elem = soup.find(attrs={"itemprop": "price"})
        if price_elem:
            price_val = price_elem.get("content") or price_elem.get_text(strip=True)
            try:
                amount = float(price_val.replace(",", "").replace("$", "").replace("£", "").replace("€", ""))
                if amount > 0:
                    currency_elem = soup.find(attrs={"itemprop": "priceCurrency"})
                    detected_currency = currency_elem.get("content", "USD") if currency_elem else "USD"
                    logger.info(f"[PRICE] Page scrape: microdata price {amount} {detected_currency} from {domain}")
                    result = {
                        "amount": amount, "original_currency": detected_currency,
                        "currency": detected_currency, "retailer": domain, "url": url,
                        "in_stock": True, "confidence": 0.8, "estimated": False,
                        "source_method": "page_scrape",
                    }
                    if detected_currency.upper() != currency.upper():
                        self._convert_gpt_price_currency(result, currency)
                    return result
            except (ValueError, TypeError):
                pass

        return None
```

- [ ] **Step 3: Replace `_fetch_page_price()` body (lines 1870-1999) with thin orchestrator**

Replace the entire method body with:

```python
    async def _fetch_page_price(
        self,
        url: str,
        product_name: str,
        currency: str = "BHD",
    ) -> Optional[Dict[str, Any]]:
        """Fetch a product page and extract price from structured data.

        Two-stage approach:
        1. curl_cffi (fast, free) — skipped for JS_ONLY_DOMAINS
        2. JS rendering fallback (Cloudflare/Microlink in parallel)

        Extraction uses _extract_price_from_html() for both stages.
        Gated by ENABLE_PAGE_SCRAPE feature flag.
        """
        if not ENABLE_PAGE_SCRAPE:
            return None

        domain = urlparse(url).netloc.replace("www.", "")

        # Fast path: skip curl_cffi for known JS-only domains
        if domain not in self.JS_ONLY_DOMAINS:
            html = await self._curl_fetch_html(url)
            if html:
                price = self._extract_price_from_html(html, product_name, currency, domain, url)
                if price:
                    logger.info(f"[PRICE] Page scrape: curl_cffi price {currency} {price['amount']} from {domain}")
                    return price
                logger.info(f"[PRICE] Page scrape: curl_cffi no structured data from {domain}, trying JS render")
        else:
            logger.info(f"[PRICE] Page scrape: skipping curl_cffi for {domain} (JS_ONLY_DOMAINS)")

        # JS rendering fallback
        if ENABLE_JS_RENDER:
            start = time.monotonic()
            rendered_html = await self._fetch_rendered_html(url)
            elapsed = time.monotonic() - start
            if rendered_html:
                logger.info(f"[PRICE] JS render: got {len(rendered_html)//1024}KB HTML in {elapsed:.1f}s from {domain}")
                price = self._extract_price_from_html(rendered_html, product_name, currency, domain, url)
                if price:
                    price["source_method"] = "page_scrape_rendered"
                    logger.info(f"[PRICE] JS render: extracted price {currency} {price['amount']} from {domain} ({elapsed:.1f}s)")
                    return price
                else:
                    logger.info(f"[PRICE] JS render: HTML rendered but no structured price from {domain}")
            else:
                logger.info(f"[PRICE] JS render: providers failed for {domain} ({elapsed:.1f}s)")

        logger.info(f"[PRICE] Page scrape: no price found from {domain}")
        return None
```

- [ ] **Step 4: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 5: Run existing page scraping tests to verify refactor doesn't break them**

Run: `python -m pytest tests/test_page_scraping.py -v`
Expected: All 15 tests PASS (the refactored methods have the same behavior)

Note: Some tests may need minor adjustments because they mock `curl_cffi.requests.get` directly — now they need to mock `_curl_fetch_html` or the underlying import. Fix any failures in-place.

- [ ] **Step 6: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "refactor(price): extract _extract_price_from_html and _curl_fetch_html from _fetch_page_price"
```

---

## Task 3: Implement `_fetch_rendered_html()` Method

**Owner:** Implementer
**Files:**
- Modify: `app/services/structured_comparison_service.py` (add method after `_curl_fetch_html`)

**Context:** This method fires Cloudflare Browser Rendering and Microlink in parallel, returns the first valid HTML. Uses `httpx.AsyncClient` (already imported at line 11). Provider selection via `RENDER_PROVIDER` env var.

- [ ] **Step 1: Add `_fetch_rendered_html()` method after `_curl_fetch_html()`**

```python
    async def _fetch_rendered_html(self, url: str) -> Optional[str]:
        """Render a URL via headless browser API and return the HTML.

        Fires Cloudflare Browser Rendering and/or Microlink in parallel.
        Returns the first valid (>1KB) HTML response, or None.
        Provider selected by RENDER_PROVIDER env var: "cloudflare", "microlink", or "both".
        """
        provider = os.environ.get("RENDER_PROVIDER", "both")

        async def _render_cloudflare(render_url: str) -> Optional[str]:
            cf_account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
            cf_token = os.environ.get("CLOUDFLARE_API_TOKEN")
            if not cf_account or not cf_token:
                return None
            try:
                async with httpx.AsyncClient(timeout=self.JS_RENDER_TIMEOUT) as client:
                    resp = await client.post(
                        f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/browser-rendering/render",
                        headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                        json={"url": render_url, "waitFor": 3000},
                    )
                    if resp.status_code == 200:
                        # Response may be JSON {"result": "<html>"} or raw HTML
                        try:
                            data = resp.json()
                            html = data.get("result", "") or data.get("html", "")
                        except Exception:
                            html = resp.text
                        if html and len(html) > 1000:
                            logger.info(f"[PRICE] JS render: cloudflare returned {len(html)//1024}KB for {render_url}")
                            return html
                    else:
                        logger.info(f"[PRICE] JS render: cloudflare HTTP {resp.status_code} for {render_url}")
            except Exception as e:
                logger.warning(f"[PRICE] JS render: cloudflare failed: {e}")
            return None

        async def _render_microlink(render_url: str) -> Optional[str]:
            try:
                headers = {}
                ml_key = os.environ.get("MICROLINK_API_KEY")
                if ml_key:
                    headers["x-api-key"] = ml_key
                async with httpx.AsyncClient(timeout=self.JS_RENDER_TIMEOUT) as client:
                    resp = await client.get(
                        "https://api.microlink.io",
                        params={"url": render_url, "prerender": "true"},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        html = data.get("data", {}).get("html", "")
                        if html and len(html) > 1000:
                            logger.info(f"[PRICE] JS render: microlink returned {len(html)//1024}KB for {render_url}")
                            return html
                    else:
                        logger.info(f"[PRICE] JS render: microlink HTTP {resp.status_code} for {render_url}")
            except Exception as e:
                logger.warning(f"[PRICE] JS render: microlink failed: {e}")
            return None

        if provider == "cloudflare":
            return await _render_cloudflare(url)
        elif provider == "microlink":
            return await _render_microlink(url)
        else:  # "both" — parallel race, first valid result wins
            results = await asyncio.gather(
                _render_cloudflare(url),
                _render_microlink(url),
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, str) and len(r) > 1000:
                    return r
            return None
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat(price): add _fetch_rendered_html with Cloudflare + Microlink parallel JS rendering"
```

---

## Task 4: Write Tests for JS Rendering

**Owner:** Implementer (or QA if idle)
**Files:**
- Create: `tests/test_js_rendering.py`

- [ ] **Step 1: Create the test file**

```python
"""Tests for JS rendering fallback in _fetch_page_price."""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.structured_comparison_service import (
    StructuredComparisonService, ENABLE_PAGE_SCRAPE, ENABLE_JS_RENDER,
)


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
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident.</body></html>
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

        with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "test123", "CLOUDFLARE_API_TOKEN": "tok", "RENDER_PROVIDER": "cloudflare"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_resp
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

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

        with patch.dict(os.environ, {"RENDER_PROVIDER": "microlink"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_resp
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

                result = await service._fetch_rendered_html("https://louisvuitton.com/cap")
        assert result is not None
        assert "Louis Vuitton" in result

    @pytest.mark.asyncio
    async def test_both_fail_returns_none(self, service):
        """Both providers fail → returns None."""
        with patch.dict(os.environ, {"RENDER_PROVIDER": "both"}):
            with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "", "CLOUDFLARE_API_TOKEN": ""}):
                mock_resp = MagicMock()
                mock_resp.status_code = 500
                mock_resp.json.return_value = {}

                with patch("httpx.AsyncClient") as mock_client_cls:
                    mock_client = AsyncMock()
                    mock_client.get.return_value = mock_resp
                    mock_client.post.return_value = mock_resp
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock(return_value=False)
                    mock_client_cls.return_value = mock_client

                    result = await service._fetch_rendered_html("https://louisvuitton.com/cap")
        assert result is None

    @pytest.mark.asyncio
    async def test_small_html_rejected(self, service):
        """HTML < 1000 bytes is treated as empty/blocked."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": SMALL_HTML}

        with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": "test", "CLOUDFLARE_API_TOKEN": "tok", "RENDER_PROVIDER": "cloudflare"}):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_resp
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client

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
        """Missing Cloudflare env vars → returns None for cloudflare provider."""
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
        """curl_cffi + JS render both fail → None."""
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
        """ENABLE_JS_RENDER=false → only curl_cffi attempted."""
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
        """JS render returns HTML but no structured price → None."""
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
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_js_rendering.py -v`
Expected: All PASS

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All existing tests PASS + new tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_js_rendering.py
git commit -m "test: add 14 unit tests for JS rendering fallback"
```

---

## Task 5: QA Review and Full Verification

**Owner:** QA Agent
**Files:** All modified/created files

- [ ] **Step 1: Run all free unit tests**

```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
```
Expected: All tests PASS, zero regressions

- [ ] **Step 2: Run key test files specifically**

```bash
python -m pytest tests/test_js_rendering.py tests/test_page_scraping.py tests/test_luxury_price_tiers.py tests/test_luxury_brands.py tests/test_price_fallback.py -v
```

- [ ] **Step 3: Syntax check**

```bash
python -m py_compile app/services/structured_comparison_service.py
```

- [ ] **Step 4: Cross-QA the implementation**

Read and review `app/services/structured_comparison_service.py`:
1. Verify `_extract_price_from_html()` contains ALL the extraction logic from the old `_fetch_page_price()` (JSON-LD with brand + USD fallback, OG meta, microdata)
2. Verify `_curl_fetch_html()` handles HTTP errors and exceptions
3. Verify `_fetch_rendered_html()` fires both providers in parallel when `RENDER_PROVIDER=both`
4. Verify `_fetch_page_price()` skips curl for `JS_ONLY_DOMAINS`
5. Verify `ENABLE_JS_RENDER` flag is at module level (line ~35)
6. Verify `JS_ONLY_DOMAINS` and `JS_RENDER_TIMEOUT` are class attributes
7. Verify `PAGE_SCRAPE_TIMEOUT` is now 5 (was 10)
8. Verify `source_method` is `"page_scrape_rendered"` for JS-rendered prices
9. Verify logging follows `[PRICE]` pattern

If any issues: send back to implementer with specific feedback.

- [ ] **Step 5: Commit QA fixes if any**

```bash
git add -A
git commit -m "fix: address QA feedback for JS rendering implementation"
```

---

## Execution Order and Dependencies

```
Task 1 (Constants) → Task 2 (Refactor helpers) → Task 3 (JS rendering method)
                                                         ↓
Task 4 (Tests) ← after Task 3
                    ↓
Task 5 (QA) ← after Task 4
```

**Agent assignments:**
- **Implementer:** Tasks 1 → 2 → 3 → 4 (sequential)
- **QA Agent:** Task 5 (after implementer finishes all tasks)
- **Cross-QA:** QA reviews implementer's work. If subpar, sends back. Implementer reviews QA's test additions (if any).
