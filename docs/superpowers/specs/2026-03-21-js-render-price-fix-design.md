# Design: JS Rendering for Luxury Price Extraction

**Date:** 2026-03-21
**Problem:** Session 27 added page scraping via `curl_cffi` for luxury brand prices, but a comprehensive retailer audit of 21 URLs across 16 domains showed that **zero luxury retailers** expose structured price data (JSON-LD, OpenGraph, microdata) in raw HTML. Official brand sites return 403s; authorized retailers serve empty JS shells or bot-detection pages. The only site with real JSON-LD was iHerb (already working).

**Root Cause:** Luxury retail sites are JavaScript SPAs that render prices client-side. `curl_cffi` fetches raw HTML without executing JavaScript, so prices are never present in the response.

## Solution Overview

Add a JS rendering fallback to the existing `_fetch_page_price()` method. When `curl_cffi` finds no structured price data, render the page using a headless browser API (Cloudflare Browser Rendering + Microlink in parallel) and extract prices from the fully-rendered HTML using the same JSON-LD/OG/microdata logic.

**Key principle:** The extraction logic doesn't change. Only the HTML source upgrades from raw HTTP response to JS-rendered response.

## Detailed Design

### 0. Module-level Constants and Feature Flags

Add near the existing `ENABLE_PAGE_SCRAPE` (line 34 of `structured_comparison_service.py`):

```python
ENABLE_JS_RENDER = os.environ.get("ENABLE_JS_RENDER", "true").lower() != "false"
```

Add as class attributes on `StructuredComparisonService` (after `TIER_15_BUDGET_TIMEOUT` at line ~1351):

```python
    JS_ONLY_DOMAINS = {
        "louisvuitton.com", "hermes.com", "chanel.com", "gucci.com",
        "prada.com", "dior.com", "farfetch.com", "net-a-porter.com",
        "nordstrom.com", "neimanmarcus.com", "ssense.com", "mytheresa.com",
        "burberry.com", "balenciaga.com", "fendi.com", "valentino.com",
    }

    JS_RENDER_TIMEOUT = 8  # seconds per provider
```

Reduce existing class attribute:
```python
    PAGE_SCRAPE_TIMEOUT = 5  # seconds per curl_cffi fetch (was 10)
```

**No new pip dependencies.** `httpx` is already in `requirements.txt`.

### 1. New Method: `_fetch_rendered_html(url)`

A single method that renders a URL via headless browser and returns the HTML string.

**Location:** `app/services/structured_comparison_service.py`, new method on `StructuredComparisonService`

**Signature:**
```python
async def _fetch_rendered_html(self, url: str) -> Optional[str]:
```

**Provider strategy — parallel race:**
- Fire both Cloudflare Browser Rendering and Microlink simultaneously via `asyncio.gather()`
- Return the first valid (non-None, non-empty) HTML response
- 8-second timeout per provider

**Cloudflare Browser Rendering (primary):**
- Direct REST API: `POST https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/render`
- Headers: `Authorization: Bearer {CLOUDFLARE_API_TOKEN}`, `Content-Type: application/json`
- Body: `{"url": url, "waitFor": 3000}` (3s for JS to render prices)
- **Response format**: JSON with `{"success": true, "result": "<html>..."}`. Extract HTML via `resp.json()["result"]`.
- Free tier: 10 min/day (~100-200 pages)
- **IMPORTANT**: The implementer should verify the exact Cloudflare response schema against [Cloudflare Browser Rendering docs](https://developers.cloudflare.com/browser-rendering/) before finalizing. The `result` key may vary. Add a fallback: if response is not JSON, try `resp.text` directly.

**Microlink (fallback):**
- REST API: `GET https://api.microlink.io?url={url}&prerender=true` (note: `prerender=true` enables JS rendering, NOT `javascript=true`)
- Response: JSON with `data.html` containing rendered HTML
- Free tier: 250 requests/day
- Optional: `x-api-key` header for higher limits
- **IMPORTANT**: The implementer should verify the Microlink response format against [Microlink docs](https://microlink.io/docs/api/getting-started/overview). If `data.html` is not populated, try `data.content` or fetch the URL returned in `data.url` directly.

**Implementation:**
```python
async def _fetch_rendered_html(self, url: str) -> Optional[str]:
    if not ENABLE_JS_RENDER:
        return None

    provider = os.environ.get("RENDER_PROVIDER", "both")

    async def _render_cloudflare(render_url: str) -> Optional[str]:
        cf_account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        cf_token = os.environ.get("CLOUDFLARE_API_TOKEN")
        if not cf_account or not cf_token:
            return None
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(
                    f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/browser-rendering/render",
                    headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                    json={"url": render_url, "waitFor": 3000}
                )
                if resp.status_code == 200:
                    # Response may be JSON {"result": "<html>"} or raw HTML
                    try:
                        data = resp.json()
                        html = data.get("result", "") or data.get("html", "")
                    except Exception:
                        html = resp.text  # Fallback: raw HTML response
                    if html and len(html) > 1000:  # Sanity: real pages are >1KB
                        return html
        except Exception as e:
            logger.warning(f"[PRICE] JS render: cloudflare failed for {render_url}: {e}")
        return None

    async def _render_microlink(render_url: str) -> Optional[str]:
        try:
            headers = {}
            ml_key = os.environ.get("MICROLINK_API_KEY")
            if ml_key:
                headers["x-api-key"] = ml_key
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    "https://api.microlink.io",
                    params={"url": render_url, "prerender": "true"},
                    headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
                    html = data.get("data", {}).get("html", "")
                    if len(html) > 1000:
                        return html
        except Exception as e:
            logger.warning(f"[PRICE] JS render: microlink failed for {render_url}: {e}")
        return None

    if provider == "cloudflare":
        return await _render_cloudflare(url)
    elif provider == "microlink":
        return await _render_microlink(url)
    else:  # "both" — parallel race
        results = await asyncio.gather(
            _render_cloudflare(url),
            _render_microlink(url),
            return_exceptions=True
        )
        for r in results:
            if isinstance(r, str) and len(r) > 1000:
                return r
        return None
```

### 2. Refactored `_fetch_page_price()`

The existing method is refactored to:
1. Extract HTML parsing into `_extract_price_from_html()` helper (shared by curl_cffi and rendered HTML)
2. Add JS rendering fallback after curl_cffi fails

**New helper method — `_extract_price_from_html()` (synchronous):**

Extracted from the existing `_fetch_page_price()` method. Contains the JSON-LD → OG → microdata extraction logic. Called by both the curl_cffi path and the JS render path.

```python
def _extract_price_from_html(
    self, html: str, product_name: str, currency: str, domain: str, url: str
) -> Optional[Dict[str, Any]]:
    """Extract price from HTML using structured data (JSON-LD, OG, microdata).

    This is a sync helper — no I/O, just HTML parsing. Reuses existing
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

**New helper method — `_curl_fetch_html()` (async):**

Extracted from the existing `_fetch_page_price()` curl_cffi fetch logic:

```python
async def _curl_fetch_html(self, url: str) -> Optional[str]:
    """Fetch raw HTML via curl_cffi (no JS rendering). Returns HTML string or None."""
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                url, impersonate="chrome",
                timeout=self.PAGE_SCRAPE_TIMEOUT,
                allow_redirects=True,
            )
        )
        if resp.status_code != 200:
            return None
        return resp.text
    except Exception:
        return None
```

**Updated `_fetch_page_price()` — now a thin orchestrator:**
```python
async def _fetch_page_price(self, url, product_name, currency="BHD"):
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

    return None
```

### 3. Speed Optimizations

**`JS_ONLY_DOMAINS` — skip curl_cffi for known-blocked sites:**
```python
JS_ONLY_DOMAINS = {
    "louisvuitton.com", "hermes.com", "chanel.com", "gucci.com",
    "prada.com", "dior.com", "farfetch.com", "net-a-porter.com",
    "nordstrom.com", "neimanmarcus.com", "ssense.com", "mytheresa.com",
    "burberry.com", "balenciaga.com", "fendi.com", "valentino.com",
}
```
For these domains, jump straight to JS rendering — saves 3-5 seconds of wasted curl_cffi time.

**Parallel provider race:**
Both Cloudflare and Microlink fire simultaneously. First valid HTML wins. Typical latency: 3-5 seconds.

**Tight timeouts:**
- `curl_cffi`: 5 seconds (down from 10 — reduced in `PAGE_SCRAPE_TIMEOUT`)
- Each JS render provider: 8 seconds
- Total worst case for a single URL: 5s (curl) + 8s (render) = 13s
- Fits within existing 20-second Tier 1.5 budget

**Caching:**
Rendered prices cached with same 24h TTL as other prices. A luxury product rendered once won't trigger rendering again for 24 hours.

### 4. Latency Scenarios

| Scenario | Time | Cost |
|----------|------|------|
| curl_cffi finds price (iHerb, pharmacy, non-luxury) | ~1-2s | $0 |
| JS_ONLY_DOMAINS → parallel render → price found | ~3-5s | $0 (free tier) |
| Unknown domain → curl_cffi fails → parallel render | ~6-8s | $0 (free tier) |
| Both renderers fail → fall through to Tier 2/3 | ~8-10s | $0 (free tier) |

### 5. Constants and Configuration

All constants defined in Section 0 above. Summary:
- `ENABLE_JS_RENDER` — module-level flag (near `ENABLE_PAGE_SCRAPE`)
- `JS_ONLY_DOMAINS` — class attribute on `StructuredComparisonService`
- `JS_RENDER_TIMEOUT = 8` — class attribute
- `PAGE_SCRAPE_TIMEOUT` reduced from 10 to 5

**Environment variables (new):**
- `ENABLE_JS_RENDER` (default `"true"`) — Kill switch for JS rendering
- `RENDER_PROVIDER` (default `"both"`) — `"cloudflare"`, `"microlink"`, or `"both"`
- `CLOUDFLARE_ACCOUNT_ID` — Cloudflare account ID for Browser Rendering API
- `CLOUDFLARE_API_TOKEN` — Cloudflare API token with Browser Rendering permission
- `MICROLINK_API_KEY` (optional) — For higher Microlink rate limits

**Existing env var change:**
- `PAGE_SCRAPE_TIMEOUT` reduced from 10 to 5 seconds (curl_cffi only)

### 6. Error Handling

- Each provider returns `None` on any failure (timeout, HTTP error, empty/small response)
- `asyncio.gather(return_exceptions=True)` — one provider failing doesn't affect the other
- HTML < 1000 bytes treated as empty/blocked (sanity check)
- All errors logged as warnings, never raise exceptions

### 7. Logging

Every JS render attempt logs:
- Provider name (cloudflare/microlink)
- Domain being rendered
- HTML size returned (KB)
- Latency (seconds)
- Whether price was extracted or not
- Extraction method used (JSON-LD/OG/microdata)

Format: `[PRICE] JS render: {provider} {result} for {domain} ({latency}s)`

### 8. `source_method` Tags

| Tag | Meaning |
|-----|---------|
| `page_scrape` | Price from curl_cffi raw HTML (existing) |
| `page_scrape_rendered` | Price from JS-rendered HTML (new) |
| `local_bhd` | Direct BHD Shopping price (existing) |
| `converted_usd` | USD→BHD conversion (existing) |
| `estimated` | GPT training data guess (existing) |

Frontend treats `page_scrape_rendered` same as `page_scrape` — real price, no special indicator needed.

## Cost Impact

| Scenario | Current Cost | New Cost | Delta |
|----------|-------------|----------|-------|
| Non-luxury, Tier 1 works | $0.010 | $0.010 | $0 |
| Luxury, curl_cffi finds price | $0.010 | $0.010 | $0 |
| Luxury, JS render finds price | $0.011 | $0.011 | $0 (free tier) |
| Luxury, JS render fails | $0.011 | $0.011 | $0 (free tier) |

**Monthly cost**: $0 on free tiers (Cloudflare 10 min/day + Microlink 250 req/day covers ~100-200 luxury comparisons/day). Paid tiers only if volume exceeds free limits.

## Testing Strategy

**Unit tests (free, mocked):**
- `test_js_rendering.py` — 12+ tests:
  - `_fetch_rendered_html()`: Cloudflare success, Microlink success, both fail, parallel race (first wins), timeout handling, feature flag disabled, provider selection ("cloudflare"/"microlink"/"both")
  - `_extract_price_from_html()`: JSON-LD, OG, microdata, no data, zero price
  - `_fetch_page_price()` integration: curl_cffi success skips JS render, curl_cffi fails triggers JS render, JS_ONLY_DOMAINS skips curl_cffi, both paths fail returns None
  - Feature flags: `ENABLE_JS_RENDER=false` skips rendering, `RENDER_PROVIDER` switching

**Existing tests must pass:** All existing tests unchanged (run full suite to verify zero regressions).

## Files Changed

| File | Changes |
|------|---------|
| `app/services/structured_comparison_service.py` | Refactor `_fetch_page_price()`, add `_fetch_rendered_html()`, add `_extract_price_from_html()`, add `JS_ONLY_DOMAINS`, add `ENABLE_JS_RENDER` flag, reduce `PAGE_SCRAPE_TIMEOUT` to 5 |
| `tests/test_js_rendering.py` | NEW — 12+ tests for JS rendering and refactored extraction |

## Success Criteria

1. LV/Hermes/Chanel products return real prices from rendered pages (not estimated)
2. `source_method: "page_scrape_rendered"` visible in API response for rendered prices
3. Latency for JS-rendered prices: < 8 seconds
4. All existing tests still pass (zero regressions)
5. New tests achieve 80%+ coverage on new code
6. Feature flags (`ENABLE_JS_RENDER`, `RENDER_PROVIDER`) work correctly
7. Free tier limits sufficient for current volume (~50 comparisons/day)
8. Graceful fallback: if both renderers fail, prices fall through to Tier 2/3 as before
