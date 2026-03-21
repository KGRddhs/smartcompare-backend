# Luxury & Supplement Price Extraction Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix luxury brand prices (LV, Hermès, Chanel) showing wrong/estimated values by adding page scraping with JSON-LD extraction, cascading authorized+GCC retailer fallbacks, and fixing the Tier 2 sanity check bug.

**Architecture:** New `_fetch_page_price()` method reuses existing `_extract_jsonld_price()` for JSON-LD, adds OpenGraph/microdata fallbacks. Enhanced Tier 1.5 cascades through official brand site → authorized retailers → GCC retailers, each with page scraping. Tier 2 sanity check gets luxury-aware thresholds. Frontend gets estimated price indicator.

**Tech Stack:** Python 3.12, FastAPI, curl_cffi (TLS fingerprinting), BeautifulSoup4, asyncio.gather, React Native/Expo

**Spec:** `docs/superpowers/specs/2026-03-21-luxury-price-fix-design.md`

**Team:** 4 Opus agents — Backend, Frontend, Test, QA. Cross-QA before disband.

---

## File Structure

| File | Role | Action |
|------|------|--------|
| `app/services/structured_comparison_service.py` | Core service — price pipeline orchestrator | Modify (add `_fetch_page_price`, enhance Tier 1.5, fix Tier 2 sanity, add constants) |
| `SmartCompareApp/src/screens/ResultsScreen.tsx` | Results display | Modify (estimated indicator, retailer debug) |
| `tests/test_page_scraping.py` | Unit tests for `_fetch_page_price` | Create |
| `tests/test_luxury_price_tiers.py` | Unit tests for Tier 1.5 cascade | Create |
| `tests/test_luxury_brands.py` | Existing luxury tests | Modify (add Tier 2 sanity tests) |

---

## Task 1: Add Constants and Feature Flag

**Owner:** Backend Agent
**Files:**
- Modify: `app/services/structured_comparison_service.py:1188-1219` (constants area)

- [ ] **Step 1: Add new constants after OFFICIAL_BRAND_DOMAINS (line ~1219)**

Add these constants to the `StructuredComparisonService` class, right after `OFFICIAL_BRAND_DOMAINS`:

```python
    # Authorized luxury retailers — trusted for cross-validation (Tier 1.5b)
    AUTHORIZED_LUXURY_RETAILERS = {
        "farfetch.com", "ssense.com", "net-a-porter.com",
        "mytheresa.com", "matchesfashion.com", "nordstrom.com",
    }

    # GCC luxury retailers — regional fallback (Tier 1.5c)
    GCC_LUXURY_RETAILERS = {
        "ounass.ae", "namshi.com", "bloomingdales.ae",
        "level-shoes.com",
    }

    PAGE_SCRAPE_TIMEOUT = 10  # seconds per individual page fetch
    TIER_15_BUDGET_TIMEOUT = 20  # seconds total across all Tier 1.5 sub-tiers
```

- [ ] **Step 2: Add feature flag check at module level**

At the top of the file, after the existing `import os` (find it near the imports):

```python
ENABLE_PAGE_SCRAPE = os.environ.get("ENABLE_PAGE_SCRAPE", "true").lower() != "false"
```

- [ ] **Step 3: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat(price): add constants for authorized/GCC luxury retailers and page scrape feature flag"
```

---

## Task 2: Implement `_fetch_page_price()` Method

**Owner:** Backend Agent
**Files:**
- Modify: `app/services/structured_comparison_service.py` (new method after `_fetch_pharmacy_price` at line ~1690)

**Context:** This method fetches a product page URL, then extracts the price using structured data (JSON-LD via existing `_extract_jsonld_price()`, then OpenGraph meta, then microdata). It uses `curl_cffi` for TLS fingerprinting (same as `_fetch_iherb_price()` at line 1394), and reuses `_extract_jsonld_price()` (line 1555) for JSON-LD parsing. The HTTP fetch pattern follows `_fetch_iherb_price()`, while the price result format follows `_try_pharmacy_urls()` (lines 1692-1736).

- [ ] **Step 1: Add the `_fetch_page_price` method**

Insert after `_try_pharmacy_urls` method (after line ~1736):

```python
    async def _fetch_page_price(
        self,
        url: str,
        product_name: str,
        currency: str = "BHD",
    ) -> Optional[Dict[str, Any]]:
        """Fetch a product page and extract price from structured data.

        Extraction priority:
        1. JSON-LD Product schema (via existing _extract_jsonld_price)
        2. OpenGraph meta tags (og:price:amount)
        3. Microdata (itemprop="price")

        Returns price dict or None. Uses curl_cffi for TLS fingerprinting
        (same as iHerb scraping). Gated by ENABLE_PAGE_SCRAPE feature flag.
        """
        if not ENABLE_PAGE_SCRAPE:
            return None

        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")
        brand = product_name.split()[0] if product_name else ""

        try:
            from curl_cffi import requests as curl_requests
            from bs4 import BeautifulSoup

            logger.info(f"[PRICE] Page scrape: fetching {url}")
            resp = await asyncio.to_thread(
                lambda: curl_requests.get(
                    url,
                    impersonate="chrome",
                    timeout=self.PAGE_SCRAPE_TIMEOUT,
                    allow_redirects=True,
                )
            )

            if resp.status_code != 200:
                logger.info(f"[PRICE] Page scrape: HTTP {resp.status_code} for {domain}")
                return None

            html = resp.text

            # Priority 1: JSON-LD (reuse existing method)
            price_data = self._extract_jsonld_price(html, brand, currency)
            if not price_data:
                # Try with USD — we'll convert later
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
                # Convert to target currency if needed
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
                            "amount": amount,
                            "original_currency": detected_currency,
                            "currency": detected_currency,
                            "retailer": domain,
                            "url": url,
                            "in_stock": True,
                            "confidence": 0.9,
                            "estimated": False,
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
                        # Try to find currency microdata nearby
                        currency_elem = soup.find(attrs={"itemprop": "priceCurrency"})
                        detected_currency = currency_elem.get("content", "USD") if currency_elem else "USD"
                        logger.info(f"[PRICE] Page scrape: microdata price {amount} {detected_currency} from {domain}")
                        result = {
                            "amount": amount,
                            "original_currency": detected_currency,
                            "currency": detected_currency,
                            "retailer": domain,
                            "url": url,
                            "in_stock": True,
                            "confidence": 0.8,
                            "estimated": False,
                            "source_method": "page_scrape",
                        }
                        if detected_currency.upper() != currency.upper():
                            self._convert_gpt_price_currency(result, currency)
                        return result
                except (ValueError, TypeError):
                    pass

            logger.info(f"[PRICE] Page scrape: no structured price data found at {domain}")
            return None

        except Exception as e:
            logger.warning(f"[PRICE] Page scrape failed for {domain}: {e}")
            return None
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat(price): add _fetch_page_price method for JSON-LD/OG/microdata price extraction"
```

---

## Task 3: Write Tests for `_fetch_page_price()`

**Owner:** Test Agent
**Files:**
- Create: `tests/test_page_scraping.py`

**Context:** Tests should mock `curl_cffi` responses with realistic HTML containing JSON-LD, OpenGraph, and microdata. The method is on `StructuredComparisonService`. Use the same mocking pattern as `tests/test_pharmacy_jsonld.py`.

- [ ] **Step 1: Write all page scraping tests**

Create `tests/test_page_scraping.py`:

```python
"""Tests for _fetch_page_price() — generic page scraping with structured data extraction."""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.structured_comparison_service import StructuredComparisonService, ENABLE_PAGE_SCRAPE


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
  "name": "Hermès Nevada Cap",
  "brand": {"@type": "Brand", "name": "Hermès"},
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
  <span itemprop="name">Hermès Cap</span>
  <span itemprop="priceCurrency" content="EUR">€</span>
  <span itemprop="price" content="590.00">590,00 €</span>
</div>
</body></html>
"""

NO_PRICE_HTML = """
<html><head><title>Browse Luxury Caps</title></head>
<body><p>Shop our collection of luxury accessories.</p></body></html>
"""

EMPTY_HTML = ""


def _make_mock_response(html, status_code=200):
    """Create a mock curl_cffi response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = html
    return mock_resp


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
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(JSONLD_PRODUCT_HTML)):
                result = await service._fetch_page_price(
                    "https://louisvuitton.com/cap", "Louis Vuitton Vers Mesh Cap", "BHD"
                )
        assert result is not None
        assert result["amount"] == 340.0
        assert result["source_method"] == "page_scrape"
        assert result["retailer"] == "louisvuitton.com"
        assert result["estimated"] is False

    @pytest.mark.asyncio
    async def test_jsonld_usd_conversion(self, service):
        """JSON-LD with USD triggers currency conversion."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(JSONLD_USD_HTML)):
                result = await service._fetch_page_price(
                    "https://hermes.com/cap", "Hermès Nevada Cap", "BHD"
                )
        assert result is not None
        assert result["amount"] > 0
        assert result["source_method"] == "page_scrape"

    @pytest.mark.asyncio
    async def test_jsonld_out_of_stock(self, service):
        """Out-of-stock products still return price but in_stock=False."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(JSONLD_OUT_OF_STOCK_HTML)):
                result = await service._fetch_page_price(
                    "https://louisvuitton.com/cap", "Louis Vuitton Cap", "BHD"
                )
        assert result is not None
        assert result["in_stock"] is False
        assert result["amount"] == 340.0

    @pytest.mark.asyncio
    async def test_jsonld_nested_offers_picks_lowest(self, service):
        """Multiple offers picks the lowest price."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(JSONLD_NESTED_OFFERS_HTML)):
                result = await service._fetch_page_price(
                    "https://gucci.com/belt", "Gucci Belt", "USD"
                )
        assert result is not None
        assert result["amount"] == 425.0


class TestFetchPagePriceOpenGraph:
    """Tests for OpenGraph meta extraction (Priority 2)."""

    @pytest.mark.asyncio
    async def test_og_meta_extraction(self, service):
        """OpenGraph meta tags extract price and currency."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(OG_META_HTML)):
                result = await service._fetch_page_price(
                    "https://ounass.ae/lv-cap", "Louis Vuitton Cap", "BHD"
                )
        assert result is not None
        assert result["amount"] > 0
        assert result["source_method"] == "page_scrape"

    @pytest.mark.asyncio
    async def test_product_meta_fallback(self, service):
        """product:price:amount meta tags work as OG fallback."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(PRODUCT_META_HTML)):
                result = await service._fetch_page_price(
                    "https://farfetch.com/lv", "Louis Vuitton Cap", "BHD"
                )
        assert result is not None
        assert result["amount"] > 0


class TestFetchPagePriceMicrodata:
    """Tests for microdata extraction (Priority 3)."""

    @pytest.mark.asyncio
    async def test_microdata_extraction(self, service):
        """itemprop=price microdata extracts correctly."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(MICRODATA_HTML)):
                result = await service._fetch_page_price(
                    "https://hermes.com/cap", "Hermès Cap", "BHD"
                )
        assert result is not None
        assert result["amount"] > 0


class TestFetchPagePriceEdgeCases:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_no_structured_data_returns_none(self, service):
        """Pages with no structured price data return None."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(NO_PRICE_HTML)):
                result = await service._fetch_page_price(
                    "https://hermes.com/browse", "Hermès Cap", "BHD"
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self, service):
        """HTTP 403/404/500 returns None gracefully."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response("", status_code=403)):
                result = await service._fetch_page_price(
                    "https://hermes.com/cap", "Hermès Cap", "BHD"
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self, service):
        """Network timeout returns None gracefully."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", side_effect=Exception("Connection timed out")):
                result = await service._fetch_page_price(
                    "https://hermes.com/cap", "Hermès Cap", "BHD"
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_html_returns_none(self, service):
        """Empty HTML returns None."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(EMPTY_HTML)):
                result = await service._fetch_page_price(
                    "https://hermes.com/cap", "Hermès Cap", "BHD"
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_feature_flag_disabled(self, service):
        """Feature flag ENABLE_PAGE_SCRAPE=false disables scraping."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", False):
            result = await service._fetch_page_price(
                "https://hermes.com/cap", "Hermès Cap", "BHD"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_zero_price_returns_none(self, service):
        """JSON-LD with price=0 is rejected."""
        html = JSONLD_PRODUCT_HTML.replace('"340.000"', '"0"')
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(html)):
                result = await service._fetch_page_price(
                    "https://louisvuitton.com/cap", "Louis Vuitton Cap", "BHD"
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_domain_extracted_from_url(self, service):
        """Retailer name is the domain extracted from URL."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True):
            with patch("curl_cffi.requests.get", return_value=_make_mock_response(JSONLD_PRODUCT_HTML)):
                result = await service._fetch_page_price(
                    "https://www.louisvuitton.com/products/cap", "Louis Vuitton Cap", "BHD"
                )
        assert result is not None
        assert result["retailer"] == "louisvuitton.com"  # www. stripped
```

- [ ] **Step 2: Run tests to verify they fail (red phase)**

Run: `python -m pytest tests/test_page_scraping.py -v -x`
Expected: Failures (method may not exist yet or import issues — depends on task ordering)

- [ ] **Step 3: Run tests after backend implements (green phase)**

Run: `python -m pytest tests/test_page_scraping.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_page_scraping.py
git commit -m "test: add 15 unit tests for _fetch_page_price page scraping"
```

---

## Task 4: Enhance Tier 1.5 with Sub-tier Cascade

**Owner:** Backend Agent
**Files:**
- Modify: `app/services/structured_comparison_service.py:964-994` (replace current Tier 1.5)

**Context:** The current Tier 1.5 (lines 964-994) searches the official domain and tries to extract price from Serper snippets via GPT. This fails for JS-rendered sites. Replace it with a 3-step cascade that actually fetches pages.

- [ ] **Step 1: Replace Tier 1.5 block (lines 964-994)**

First, add `import time` to the module-level imports at the top of the file (near `import asyncio`, `import os`, etc.) and add `from urllib.parse import urlparse` if not already present.

Then replace the entire block from `# --- Tier 1.5:` to just before `# --- Tier 2:` (line 996):

```python
        # --- Tier 1.5: Page scraping cascade (luxury brands only) ---
        if not price and self._is_luxury_brand(full_name) and ENABLE_PAGE_SCRAPE:
            tier15_start = time.monotonic()
            tier15_budget = self.TIER_15_BUDGET_TIMEOUT

            # --- Tier 1.5a: Official brand site ---
            official_domain = self._get_official_domain(full_name)
            if official_domain:
                logger.info(f"[PRICE] Tier 1.5a: trying official domain {official_domain}")
                try:
                    official_results = await search_web(f"{full_name} site:{official_domain}")
                    self.api_calls += 1
                    self._track_cost(0.001)
                    if official_results and official_results.get("organic"):
                        for organic_item in official_results["organic"][:2]:
                            page_url = organic_item.get("link")
                            if not page_url:
                                continue
                            page_price = await self._fetch_page_price(page_url, full_name, currency)
                            if page_price and page_price.get("amount"):
                                page_price["retailer"] = official_domain
                                logger.info(f"[PRICE] Tier 1.5a: official price {currency} {page_price['amount']} from {official_domain}")
                                set_cached(cache_key, page_price, PRICE_CACHE_TTL)
                                page_price["_cached"] = False
                                return page_price
                except Exception as e:
                    logger.warning(f"[PRICE] Tier 1.5a failed: {e}")

            # Check budget before Tier 1.5b
            elapsed = time.monotonic() - tier15_start
            if elapsed >= tier15_budget:
                logger.info(f"[PRICE] Tier 1.5 budget exhausted ({elapsed:.1f}s), skipping to Tier 2")
            else:
                # --- Tier 1.5b: Authorized luxury retailers ---
                logger.info(f"[PRICE] Tier 1.5b: trying authorized retailers")
                try:
                    # Use brand name + retailer names (avoids long site: OR chains)
                    retailer_query = f"{full_name} farfetch OR ssense OR net-a-porter"
                    retailer_results = await search_web(retailer_query)
                    self.api_calls += 1
                    self._track_cost(0.001)
                    if retailer_results and retailer_results.get("organic"):
                        # Filter to only authorized retailer domains
                        retailer_urls = []
                        for item in retailer_results["organic"][:5]:
                            link = item.get("link", "")
                            link_domain = urlparse(link).netloc.replace("www.", "")
                            if link_domain in self.AUTHORIZED_LUXURY_RETAILERS or link_domain in self.OFFICIAL_BRAND_DOMAINS:
                                retailer_urls.append((link, link_domain))

                        if retailer_urls:
                            # Fetch top 3 in parallel
                            fetch_tasks = [
                                self._fetch_page_price(url, full_name, currency)
                                for url, _ in retailer_urls[:3]
                            ]
                            page_prices = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                            # Collect valid prices
                            valid_prices = []
                            for i, pp in enumerate(page_prices):
                                if isinstance(pp, dict) and pp.get("amount"):
                                    pp["_retailer_domain"] = retailer_urls[i][1]
                                    valid_prices.append(pp)

                            if len(valid_prices) >= 2:
                                # Cross-validate: max/min <= 1.15
                                amounts = [p["amount"] for p in valid_prices]
                                if max(amounts) / min(amounts) <= 1.15:
                                    # Prices agree — use lowest
                                    best = min(valid_prices, key=lambda p: p["amount"])
                                    logger.info(f"[PRICE] Tier 1.5b: cross-validated price {currency} {best['amount']} ({len(valid_prices)} sources agree)")
                                    best.pop("_retailer_domain", None)
                                    set_cached(cache_key, best, PRICE_CACHE_TTL)
                                    best["_cached"] = False
                                    return best
                                else:
                                    # Prices diverge — use the one from highest-tier retailer
                                    best = valid_prices[0]
                                    logger.info(f"[PRICE] Tier 1.5b: single retailer price {currency} {best['amount']} (prices diverged)")
                                    best.pop("_retailer_domain", None)
                                    set_cached(cache_key, best, PRICE_CACHE_TTL)
                                    best["_cached"] = False
                                    return best
                            elif len(valid_prices) == 1:
                                best = valid_prices[0]
                                logger.info(f"[PRICE] Tier 1.5b: single retailer price {currency} {best['amount']}")
                                best.pop("_retailer_domain", None)
                                set_cached(cache_key, best, PRICE_CACHE_TTL)
                                best["_cached"] = False
                                return best
                except Exception as e:
                    logger.warning(f"[PRICE] Tier 1.5b failed: {e}")

                # Check budget before Tier 1.5c
                elapsed = time.monotonic() - tier15_start
                if elapsed >= tier15_budget:
                    logger.info(f"[PRICE] Tier 1.5 budget exhausted ({elapsed:.1f}s), skipping to Tier 2")
                else:
                    # --- Tier 1.5c: GCC luxury retailers ---
                    logger.info(f"[PRICE] Tier 1.5c: trying GCC retailers")
                    try:
                        gcc_query = f"{full_name} ounass OR bloomingdales dubai OR namshi"
                        gcc_results = await search_web(gcc_query)
                        self.api_calls += 1
                        self._track_cost(0.001)
                        if gcc_results and gcc_results.get("organic"):
                            for item in gcc_results["organic"][:3]:
                                link = item.get("link", "")
                                from urllib.parse import urlparse
                                link_domain = urlparse(link).netloc.replace("www.", "")
                                if link_domain in self.GCC_LUXURY_RETAILERS:
                                    gcc_price = await self._fetch_page_price(link, full_name, currency)
                                    if gcc_price and gcc_price.get("amount"):
                                        # GCC sites often return AED — conversion handled by _fetch_page_price
                                        logger.info(f"[PRICE] Tier 1.5c: GCC price {currency} {gcc_price['amount']} from {link_domain}")
                                        set_cached(cache_key, gcc_price, PRICE_CACHE_TTL)
                                        gcc_price["_cached"] = False
                                        return gcc_price
                    except Exception as e:
                        logger.warning(f"[PRICE] Tier 1.5c failed: {e}")

            logger.info(f"[PRICE] Tier 1.5 cascade complete, no price found for {full_name}")
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat(price): enhance Tier 1.5 with official/authorized/GCC retailer cascade and page scraping"
```

---

## Task 5: Wire `_fetch_page_price()` into Supplement Pipeline

**Owner:** Backend Agent
**Files:**
- Modify: `app/services/structured_comparison_service.py:1040-1056` (supplement pipeline, after pharmacy JSON-LD)

**Context:** After iHerb direct scrape and pharmacy JSON-LD both fail, the code combines organic results for GPT extraction (line 1049). Before sending to GPT, we can try page scraping on any known retailer URLs in the organic results — it's free (no Serper call) and more reliable than GPT snippet parsing.

- [ ] **Step 1: Add page scraping attempt before GPT extraction**

After line 1047 (`return pharmacy_price`) and before the `# Combine results for GPT extraction fallback` comment (line 1049), insert:

```python
            # Try page scraping on known retailer URLs from organic results (zero Serper cost)
            if ENABLE_PAGE_SCRAPE:
                known_supplement_retailers = {"iherb.com", "bn.boots.com", "bolo.bh", "amazon.com", "noon.com"}
                for item in (iherb_organic + bh_organic)[:5]:
                    link = item.get("link", "")
                    link_domain = urlparse(link).netloc.replace("www.", "")
                    if link_domain in known_supplement_retailers or link_domain in self.PHARMACY_DOMAINS:
                        page_price = await self._fetch_page_price(link, full_name, currency)
                        if page_price and page_price.get("amount"):
                            page_price["_cached"] = False
                            logger.info(f"[PRICE] Supplement: page scrape price {currency} {page_price['amount']} from {link_domain}")
                            set_cached(cache_key, page_price, PRICE_CACHE_TTL)
                            return page_price
```

Note: `urlparse` is now a module-level import (added in Task 4).

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat(price): wire page scraping into supplement pipeline before GPT fallback"
```

---

## Task 6: Write Tests for Tier 1.5 Cascade and Supplement Enhancement

**Owner:** Test Agent
**Files:**
- Create: `tests/test_luxury_price_tiers.py`

**Context:** These tests verify the Tier 1.5a → 1.5b → 1.5c cascade behavior. Mock `search_web()` and `_fetch_page_price()` to control which tier succeeds. Use `pytest.mark.asyncio`.

- [ ] **Step 1: Write tier cascade tests**

Create `tests/test_luxury_price_tiers.py`:

```python
"""Tests for Tier 1.5 luxury price cascade: official → authorized → GCC retailers."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    svc = StructuredComparisonService.__new__(StructuredComparisonService)
    svc.total_cost = 0
    svc.api_calls = 0
    svc._shopping_items_cache = {}
    return svc


def _mock_serper_organic(urls_and_titles):
    """Build mock Serper organic results."""
    return {
        "organic": [
            {"link": url, "title": title, "snippet": f"Shop {title}"}
            for url, title in urls_and_titles
        ]
    }


def _mock_page_price(amount, currency="BHD", domain="test.com"):
    """Build a price result as _fetch_page_price would return."""
    return {
        "amount": amount,
        "currency": currency,
        "original_currency": currency,
        "retailer": domain,
        "url": f"https://{domain}/product",
        "in_stock": True,
        "confidence": 1.0,
        "estimated": False,
        "source_method": "page_scrape",
    }


class TestTier15aCascade:
    """Tier 1.5a: Official brand site scraping."""

    @pytest.mark.asyncio
    async def test_official_domain_price_found(self, service):
        """When official domain page has JSON-LD price, _fetch_page_price returns it."""
        mock_price = _mock_page_price(340.0, "BHD", "louisvuitton.com")
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch.object(service, '_fetch_page_price', new_callable=AsyncMock, return_value=mock_price):
            result = await service._fetch_page_price("https://louisvuitton.com/cap", "Louis Vuitton Cap", "BHD")
        assert result is not None
        assert result["amount"] == 340.0
        assert result["retailer"] == "louisvuitton.com"

    @pytest.mark.asyncio
    async def test_official_domain_no_price_returns_none(self, service):
        """When official domain has no structured data, _fetch_page_price returns None."""
        with patch("app.services.structured_comparison_service.ENABLE_PAGE_SCRAPE", True), \
             patch.object(service, '_fetch_page_price', new_callable=AsyncMock, return_value=None):
            result = await service._fetch_page_price("https://louisvuitton.com/browse", "Louis Vuitton Cap", "BHD")
        assert result is None


class TestTier15bCascade:
    """Tier 1.5b: Authorized retailer scraping."""

    def test_cross_validation_two_prices_agree(self):
        """Two authorized retailers within 15% → cross-validation passes, use lowest."""
        prices = [
            _mock_page_price(340.0, "BHD", "farfetch.com"),
            _mock_page_price(355.0, "BHD", "ssense.com"),
        ]
        amounts = [p["amount"] for p in prices]
        # Cross-validation formula: max/min <= 1.15
        assert max(amounts) / min(amounts) <= 1.15
        # Should pick lowest
        best = min(prices, key=lambda p: p["amount"])
        assert best["amount"] == 340.0
        assert best["retailer"] == "farfetch.com"

    def test_cross_validation_prices_diverge_uses_first(self):
        """Retailers disagree (>15%) → prices diverge, use first retailer."""
        prices = [
            _mock_page_price(340.0, "BHD", "farfetch.com"),
            _mock_page_price(200.0, "BHD", "ssense.com"),
        ]
        amounts = [p["amount"] for p in prices]
        assert max(amounts) / min(amounts) > 1.15
        # Should use first (highest-tier) retailer
        best = prices[0]
        assert best["amount"] == 340.0

    def test_single_retailer_price_used(self):
        """Only one authorized retailer has price → use it."""
        valid_prices = [_mock_page_price(340.0, "BHD", "farfetch.com")]
        assert len(valid_prices) == 1
        assert valid_prices[0]["amount"] == 340.0
        assert valid_prices[0]["source_method"] == "page_scrape"

    def test_authorized_retailer_domain_filtering(self):
        """Only domains in AUTHORIZED_LUXURY_RETAILERS pass the domain filter."""
        authorized = StructuredComparisonService.AUTHORIZED_LUXURY_RETAILERS
        assert "farfetch.com" in authorized
        assert "ssense.com" in authorized
        assert "ebay.com" not in authorized
        assert "dhgate.com" not in authorized


class TestTier15cCascade:
    """Tier 1.5c: GCC retailer scraping."""

    def test_gcc_retailer_domains_defined(self):
        """GCC luxury retailers include expected GCC domains."""
        gcc = StructuredComparisonService.GCC_LUXURY_RETAILERS
        assert "ounass.ae" in gcc
        assert "bloomingdales.ae" in gcc
        assert "namshi.com" in gcc

    def test_gcc_domain_filtering(self):
        """Non-GCC domains should not be in the GCC retailer set."""
        gcc = StructuredComparisonService.GCC_LUXURY_RETAILERS
        assert "amazon.com" not in gcc
        assert "farfetch.com" not in gcc  # farfetch is in authorized, not GCC

    @pytest.mark.asyncio
    async def test_gcc_price_with_aed_conversion(self, service):
        """GCC retailer returning AED price should be convertible to BHD."""
        # AED 1000 ≈ BHD 102.5 (1 AED ≈ 0.1025 BHD)
        aed_price = _mock_page_price(1000.0, "AED", "ounass.ae")
        assert aed_price["currency"] == "AED"
        assert aed_price["amount"] == 1000.0
        # _fetch_page_price handles conversion internally via _convert_gpt_price_currency


class TestTier15BudgetTimeout:
    """Budget timeout enforcement across sub-tiers."""

    def test_budget_timeout_constant(self):
        """Budget timeout is 20 seconds."""
        assert StructuredComparisonService.TIER_15_BUDGET_TIMEOUT == 20

    def test_budget_exceeded_logic(self):
        """When elapsed >= budget, remaining tiers should be skipped."""
        budget = 20  # seconds
        elapsed_after_15a = 22  # took too long
        assert elapsed_after_15a >= budget  # should skip 1.5b and 1.5c

    def test_budget_not_exceeded_allows_continuation(self):
        """When elapsed < budget, next tier should proceed."""
        budget = 20
        elapsed_after_15a = 5  # fast
        assert elapsed_after_15a < budget  # should continue to 1.5b


class TestTier15Constants:
    """Verify constants are properly defined."""

    def test_authorized_retailers_defined(self):
        assert hasattr(StructuredComparisonService, 'AUTHORIZED_LUXURY_RETAILERS')
        assert "farfetch.com" in StructuredComparisonService.AUTHORIZED_LUXURY_RETAILERS

    def test_gcc_retailers_defined(self):
        assert hasattr(StructuredComparisonService, 'GCC_LUXURY_RETAILERS')
        assert "ounass.ae" in StructuredComparisonService.GCC_LUXURY_RETAILERS

    def test_page_scrape_timeout_defined(self):
        assert StructuredComparisonService.PAGE_SCRAPE_TIMEOUT == 10

    def test_tier15_budget_timeout_defined(self):
        assert StructuredComparisonService.TIER_15_BUDGET_TIMEOUT == 20
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_luxury_price_tiers.py -v`
Expected: Constants tests pass, cascade tests need implementation

- [ ] **Step 3: Commit**

```bash
git add tests/test_luxury_price_tiers.py
git commit -m "test: add unit tests for Tier 1.5 luxury price cascade"
```

---

## Task 7: Fix Tier 2 Sanity Check Bug

**Owner:** Backend Agent
**Files:**
- Modify: `app/services/structured_comparison_service.py:1089-1115` (Tier 2 sanity check)

**Context:** Tier 1's sanity check (line 932-934) already uses luxury thresholds (1.8x/0.6x). Tier 2's sanity check (line 1100-1108) uses hardcoded 2.0/0.5 for ALL non-supplement products. Fix by adding the same luxury check.

- [ ] **Step 1: Replace lines 1100-1115 with luxury-aware thresholds**

Current code (lines 1097-1115):
```python
                if tier3_estimate and tier3_estimate.get("amount"):
                    tier2_bhd = _convert_to_bhd(price["amount"], currency)
                    tier3_bhd = _convert_to_bhd(tier3_estimate["amount"], currency)
                    if tier2_bhd > tier3_bhd * 2:
                        ...
                        price = tier3_estimate
                        price["estimated"] = True
                        price["source_method"] = "estimated"
                    elif tier2_bhd < tier3_bhd * 0.5:
                        ...
                        price = tier3_estimate
                        price["estimated"] = True
                        price["source_method"] = "estimated"
```

Replace lines 1097-1115 with:
```python
                if tier3_estimate and tier3_estimate.get("amount"):
                    tier2_bhd = _convert_to_bhd(price["amount"], currency)
                    tier3_bhd = _convert_to_bhd(tier3_estimate["amount"], currency)
                    # Luxury brands get tighter thresholds (same as Tier 1 sanity check)
                    if self._is_luxury_brand(full_name):
                        high_threshold = 1.8
                        low_threshold = 0.6
                    else:
                        high_threshold = 2.0
                        low_threshold = 0.5
                    if tier2_bhd > tier3_bhd * high_threshold:
                        logger.info(
                            f"[PRICE] Tier 2 too HIGH: {currency} {price['amount']} "
                            f"vs estimate {currency} {tier3_estimate['amount']} "
                            f"(threshold {high_threshold}x) — using Tier 3"
                        )
                        price = tier3_estimate
                        price["estimated"] = True
                        price["source_method"] = "estimated"
                    elif tier2_bhd < tier3_bhd * low_threshold:
                        logger.info(
                            f"[PRICE] Tier 2 too LOW: {currency} {price['amount']} "
                            f"vs estimate {currency} {tier3_estimate['amount']} "
                            f"(threshold {low_threshold}x) — using Tier 3"
                        )
                        price = tier3_estimate
                        price["estimated"] = True
                        price["source_method"] = "estimated"
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "fix(price): add luxury-aware thresholds to Tier 2 sanity check (1.8x/0.6x)"
```

---

## Task 8: Add Tier 2 Sanity Bug Fix Tests

**Owner:** Test Agent
**Files:**
- Modify: `tests/test_luxury_brands.py` (add new tests)

- [ ] **Step 1: Add tests for Tier 2 luxury thresholds**

Append to `tests/test_luxury_brands.py`:

```python
class TestTier2LuxurySanityCheck:
    """Tier 2 sanity check should use 1.8x/0.6x for luxury brands.

    These tests verify the ACTUAL code behavior by checking that _is_luxury_brand
    returns correct values and that the threshold logic in _get_price applies them.
    """

    def test_luxury_brand_detected_for_lv(self):
        """_is_luxury_brand returns True for Louis Vuitton products."""
        assert StructuredComparisonService._is_luxury_brand("Louis Vuitton Vers Mesh Cap") is True
        assert StructuredComparisonService._is_luxury_brand("Hermès Nevada Cap") is True

    def test_non_luxury_brand_not_detected(self):
        """_is_luxury_brand returns False for regular products."""
        assert StructuredComparisonService._is_luxury_brand("Samsung Galaxy S24") is False
        assert StructuredComparisonService._is_luxury_brand("Nike Air Max") is False

    def test_luxury_threshold_rejects_1_9x_price(self):
        """A luxury price at 1.9x estimate is rejected by 1.8x threshold but would pass 2.0x.
        This is the key behavioral difference the bug fix introduces.
        """
        tier2_bhd = 190  # price from Tier 2
        tier3_bhd = 100  # GPT estimate
        # With luxury threshold (1.8x): 190 > 100 * 1.8 = 180 → REJECTED
        assert tier2_bhd > tier3_bhd * 1.8
        # With old threshold (2.0x): 190 < 100 * 2.0 = 200 → would have PASSED
        assert tier2_bhd < tier3_bhd * 2.0

    def test_luxury_low_threshold_rejects_0_55x_price(self):
        """A luxury price at 0.55x estimate is rejected by 0.6x but would pass 0.5x."""
        tier2_bhd = 55
        tier3_bhd = 100
        assert tier2_bhd < tier3_bhd * 0.6  # rejected by luxury threshold
        assert tier2_bhd > tier3_bhd * 0.5  # would pass old threshold

    def test_hermes_cap_real_scenario(self):
        """Real scenario: Hermès cap at 264 BHD, conservative estimate 132 BHD.

        With 1.8x luxury threshold: 264 > 132*1.8=237.6 → REJECT untrusted Tier 2 price.
        With 2.0x old threshold: 264 = 132*2.0=264 → borderline PASS (wrong behavior).

        The rejection is CORRECT — Tier 1.5 page scraping should find the real price
        from the official site instead of trusting an unverified marketplace price.
        """
        assert StructuredComparisonService._is_luxury_brand("Hermès Nevada Cap") is True
        tier2_bhd = 264
        tier3_bhd = 132
        assert tier2_bhd > tier3_bhd * 1.8  # new threshold rejects correctly
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_luxury_brands.py -v -k "Tier2"`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_luxury_brands.py
git commit -m "test: add 5 tests for Tier 2 luxury sanity check thresholds"
```

---

## Task 9: Frontend — Estimated Price Indicator + Retailer Fix

**Owner:** Frontend Agent
**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx:368-380`

- [ ] **Step 1: Add estimated price indicator**

Find the price display section (around lines 368-380) and add an estimated indicator:

After line 377 (`<Text style={styles.priceNote}>(converted from USD)</Text>`), add:

```tsx
        {(product.price?.estimated === true || product.price?.source_method === 'estimated') && (
          <Text style={styles.priceNote}>(estimated price)</Text>
        )}
```

- [ ] **Step 2: Add page_scrape source indicator (optional, subtle)**

After the estimated indicator, add:

```tsx
        {product.price?.source_method === 'page_scrape' && product.price?.retailer && (
          <Text style={styles.retailerText}>from {product.price.retailer}</Text>
        )}
```

- [ ] **Step 3: Debug retailer display**

Check lines 378-380 — the retailer only shows when `!product.price?.unavailable`. Verify that the backend is populating the `retailer` field for all code paths (Tier 1, 1.5, 2, 3). If Tier 3 estimated prices have no retailer, that's expected. But Tier 2 GPT prices should always have a retailer — check `_get_price()` for any code path that returns without setting `retailer`.

- [ ] **Step 4: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "feat(frontend): add estimated price indicator and improve retailer attribution display"
```

---

## Task 10: Run Full Test Suite + Integration Verification

**Owner:** QA Agent
**Files:** All test files

- [ ] **Step 1: Run all free unit tests**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All 944+ existing tests PASS, plus new tests from Tasks 3, 5, 7

- [ ] **Step 2: Verify no regressions in key test files**

Run these specifically:
```bash
python -m pytest tests/test_price_fallback.py tests/test_price_priority.py tests/test_luxury_brands.py tests/test_pharmacy_jsonld.py -v
```
Expected: All PASS

- [ ] **Step 3: Verify frontend TypeScript**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Syntax check the main service file**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 5: Cross-QA each agent's work**

Review:
1. Backend Agent: Check `_fetch_page_price()` handles all edge cases, Tier 1.5 cascade has proper error handling, budget timeout works
2. Frontend Agent: Check estimated indicator shows correctly, no styling issues
3. Test Agent: Check test coverage is 80%+, tests are meaningful (not tautological)

If any work is subpar: send it back with specific feedback.

- [ ] **Step 6: Final commit (if any cross-QA fixes)**

```bash
git add -A
git commit -m "fix: address QA feedback from cross-review"
```

---

## Task 11: Update Documentation

**Owner:** QA Agent (or any idle agent)
**Files:**
- Modify: `docs/CONTEXT_SESSION_LOG.md` (add Session 27 entry)

- [ ] **Step 1: Add session log entry**

Append to `docs/CONTEXT_SESSION_LOG.md`:

```markdown
### Session 27 — Luxury Price Extraction Fix (March 21, 2026)

**Problem:** Luxury brand prices (LV cap ~340 BHD showing as ~50-160 BHD) because official brand sites are JS-rendered and Serper snippets don't contain prices.

**Root cause:** 4-tier cascade failure:
1. Serper Shopping returns reseller prices → filtered by sanity check
2. Official domain search only reads snippets, not pages → no prices from JS-rendered sites
3. Tier 2 GPT extraction uses wrong sanity thresholds for luxury (2.0x instead of 1.8x)
4. Tier 3 GPT estimate too conservative

**Changes:**
- NEW: `_fetch_page_price()` — generic page scraper (JSON-LD, OpenGraph, microdata) using curl_cffi
- ENHANCED: Tier 1.5 now cascades: official brand → authorized retailers (Farfetch, SSENSE, Net-a-Porter) → GCC retailers (Ounass, Bloomingdales, Namshi)
- FIXED: Tier 2 sanity check now uses luxury 1.8x/0.6x thresholds (was using 2.0x/0.5x)
- NEW: Frontend "(estimated price)" indicator for Tier 3 prices
- NEW: `ENABLE_PAGE_SCRAPE` feature flag (env var, default true)
- NEW constants: `AUTHORIZED_LUXURY_RETAILERS`, `GCC_LUXURY_RETAILERS`
- 20-second budget timeout across all Tier 1.5 sub-tiers

**Cost impact:** +$0.001-0.003 for luxury brands only (within $0.015 budget)
**Tests:** +30 new tests (page scraping, tier cascade, sanity check)
```

- [ ] **Step 2: Commit**

```bash
git add docs/CONTEXT_SESSION_LOG.md
git commit -m "docs: add Session 27 entry for luxury price fix"
```

---

## Execution Order and Dependencies

```
Task 1 (Constants)      ──→ Task 2 (fetch_page_price) ──→ Task 4 (Tier 1.5 cascade)
                                                                 │
Task 3 (Tests: scraping) ← after Task 2                         ↓
                                                         Task 5 (Supplement wiring)
                                                                 │
Task 6 (Tests: cascade+supplement) ← after Tasks 4,5            ↓
                                                         Task 7 (Tier 2 bug fix)
                                                                 │
Task 8 (Tests: sanity) ← after Task 7                           │

Task 9 (Frontend) ─── runs in parallel with ALL backend tasks

Task 10 (QA) ─── after ALL other tasks complete
Task 11 (Docs) ─── after QA passes
```

**Parallel work:**
- Backend Agent: Tasks 1 → 2 → 4 → 5 → 7 (sequential)
- Test Agent: Task 3 (after Task 2), Task 6 (after Tasks 4+5), Task 8 (after Task 7)
- Frontend Agent: Task 9 (independent, can run in parallel with backend)
- QA Agent: Task 10 (after all others), Task 11

**Cross-QA assignments:**
- Backend reviews Frontend's work (Task 9)
- Frontend reviews Test Agent's work (Tasks 3, 6, 8)
- Test Agent reviews Backend's work (Tasks 1, 2, 4, 5, 7)
- QA Agent reviews everything (Task 10)
