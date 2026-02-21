# Bahrain Pharmacy JSON-LD Price Extraction — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix wrong supplement prices for non-iHerb brands (HealthAid, Vitabiotics, etc.) by parsing JSON-LD structured data from Bahrain pharmacy product pages found via the existing Serper fallback search.

**Architecture:** After iHerb scrape fails and Serper BH pharmacy search runs (already existing), insert a new step that fetches pharmacy product pages from the Serper results and parses their JSON-LD `Product` schema for BHD prices. Falls through to existing GPT extraction if no JSON-LD found.

**Tech Stack:** Python 3.12, httpx (already imported), BeautifulSoup (already available), JSON-LD parsing (stdlib json)

---

### Task 1: Add `_extract_jsonld_price()` static method + tests

This is the pure parsing function — no HTTP, no async, easy to unit test.

**Files:**
- Modify: `app/services/structured_comparison_service.py` (add method after `_numbers_match` ~line 894)
- Create: `tests/test_pharmacy_jsonld.py`

**Step 1: Write the failing tests**

Create `tests/test_pharmacy_jsonld.py`:

```python
"""Tests for Bahrain pharmacy JSON-LD price extraction."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pharmacy_jsonld.py -v`
Expected: FAIL — `_extract_jsonld_price` does not exist yet

**Step 3: Implement `_extract_jsonld_price()`**

Add to `StructuredComparisonService` class, after `_numbers_match()` (~line 894):

```python
    @staticmethod
    def _extract_jsonld_price(html: str, brand: str, expected_currency: str) -> Optional[Dict[str, Any]]:
        """Parse JSON-LD Product schema from HTML for price data.

        Looks for <script type="application/ld+json"> containing a Product
        with offers.price in the expected currency. Verifies brand name
        appears in the product name.

        Returns price dict or None if no valid match found.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')
        ld_scripts = soup.find_all('script', type='application/ld+json')
        if not ld_scripts:
            return None

        brand_lower = brand.lower()
        best_price = None

        for script in ld_scripts:
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            # Collect Product objects (may be top-level, in @graph, or in a list)
            products = []
            if isinstance(data, dict):
                if data.get("@type") == "Product":
                    products.append(data)
                elif "@graph" in data:
                    for item in data["@graph"]:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            products.append(item)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        products.append(item)

            for product in products:
                # Verify brand in product name
                product_name = product.get("name", "")
                if brand_lower not in product_name.lower():
                    continue

                # Extract offers (single dict or list)
                offers = product.get("offers", {})
                if isinstance(offers, dict):
                    offers = [offers]
                elif not isinstance(offers, list):
                    continue

                for offer in offers:
                    if not isinstance(offer, dict):
                        continue
                    currency = offer.get("priceCurrency", "")
                    if currency.upper() != expected_currency.upper():
                        continue
                    try:
                        price_val = float(offer.get("price", 0))
                    except (ValueError, TypeError):
                        continue
                    if price_val <= 0:
                        continue

                    availability = offer.get("availability", "")
                    in_stock = "OutOfStock" not in availability

                    if best_price is None or price_val < best_price["amount"]:
                        best_price = {
                            "amount": price_val,
                            "currency": expected_currency,
                            "in_stock": in_stock,
                        }

        return best_price
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pharmacy_jsonld.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add tests/test_pharmacy_jsonld.py app/services/structured_comparison_service.py
git commit -m "feat: add JSON-LD price parser for pharmacy product pages"
```

---

### Task 2: Add `_fetch_pharmacy_price()` async method + integration test

This is the HTTP + coordination layer: filters Serper URLs, fetches pages, calls `_extract_jsonld_price()`.

**Files:**
- Modify: `app/services/structured_comparison_service.py` (add method after `_extract_jsonld_price`)
- Modify: `tests/test_pharmacy_jsonld.py` (add integration tests)

**Step 1: Write the failing tests**

Append to `tests/test_pharmacy_jsonld.py`:

```python
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock


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
    """Returns None when no Serper URLs match pharmacy domains."""
    serper_organic = [
        {"title": "Some result", "link": "https://www.amazon.com/something"},
    ]
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
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pharmacy_jsonld.py -v -k "fetch_pharmacy"`
Expected: FAIL — `_fetch_pharmacy_price` does not exist yet

**Step 3: Implement `_fetch_pharmacy_price()`**

Add to `StructuredComparisonService` class, right after `_extract_jsonld_price()`:

```python
    # Bahrain pharmacy domains that serve JSON-LD Product schema with BHD prices
    PHARMACY_DOMAINS = {
        "bolo.bh": "Bolo",
        "bn.boots.com": "Boots",
        "aldeerahpharmacy.com": "Al Deerah Pharmacy",
    }

    async def _fetch_pharmacy_price(
        self,
        serper_organic: List[Dict],
        brand: str,
        full_name: str,
        currency: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch BHD price from Bahrain pharmacy product pages via JSON-LD.

        Filters Serper organic results for known pharmacy domains, fetches
        each product page, and parses JSON-LD Product schema for price.
        Returns first valid match or None.
        """
        # Filter for pharmacy URLs
        pharmacy_urls = []
        for item in serper_organic:
            link = item.get("link", "")
            for domain, retailer_name in self.PHARMACY_DOMAINS.items():
                if domain in link:
                    pharmacy_urls.append((link, retailer_name))
                    break
        if not pharmacy_urls:
            logger.info(f"[PRICE] No pharmacy URLs in Serper results for {full_name}")
            return None

        logger.info(f"[PRICE] Found {len(pharmacy_urls)} pharmacy URLs, trying JSON-LD extraction")

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url, retailer_name in pharmacy_urls[:3]:
                try:
                    resp = await client.get(url, follow_redirects=True)
                    if resp.status_code != 200:
                        logger.info(f"[PRICE] Pharmacy {retailer_name}: HTTP {resp.status_code} for {url}")
                        continue

                    price_data = self._extract_jsonld_price(resp.text, brand, currency)
                    if price_data:
                        logger.info(f"[PRICE] Pharmacy JSON-LD: {currency} {price_data['amount']} from {retailer_name}")
                        return {
                            "amount": price_data["amount"],
                            "original_currency": currency,
                            "currency": currency,
                            "retailer": retailer_name,
                            "url": url,
                            "in_stock": price_data.get("in_stock", True),
                            "confidence": 1.0,
                            "estimated": False,
                        }
                    else:
                        logger.info(f"[PRICE] Pharmacy {retailer_name}: no valid JSON-LD price at {url}")

                except Exception as e:
                    logger.warning(f"[PRICE] Pharmacy {retailer_name} fetch failed: {e}")
                    continue

        return None
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pharmacy_jsonld.py -v`
Expected: All 11 tests PASS

**Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_pharmacy_jsonld.py
git commit -m "feat: add _fetch_pharmacy_price() for BH pharmacy JSON-LD extraction"
```

---

### Task 3: Integrate into `_get_price()` flow

Wire `_fetch_pharmacy_price()` into the supplement price pipeline between iHerb scrape and GPT extraction.

**Files:**
- Modify: `app/services/structured_comparison_service.py:584-601` (restructure supplement fallback)

**Step 1: Syntax-check before changes**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No errors (baseline)

**Step 2: Modify `_get_price()` supplement fallback**

Replace lines 584-601 (after iHerb scrape returns None, before GPT extraction):

Current code (lines 584-601):
```python
            return iherb_price

            # Direct scrape failed — search iHerb + Bahrain pharmacies in parallel
            logger.info(f"[PRICE] iHerb direct scrape failed, trying Serper + Bahrain pharmacy for {full_name}")
            iherb_task = search_web(f"{iherb_query} iherb price", num_results=5, country=iherb_cc)
            bh_pharmacy_task = search_web(f"{brand} {name} price", num_results=5, country="bh")
            iherb_results, bh_pharmacy_results = await asyncio.gather(iherb_task, bh_pharmacy_task)
            self._track_cost(0.002)  # 2 Serper calls
            iherb_organic = iherb_results.get("organic", [])
            bh_organic = bh_pharmacy_results.get("organic", [])
            # Combine results — iHerb first, then Bahrain pharmacies
            combined_organic = iherb_organic + bh_organic
            if combined_organic:
                logger.info(f"[PRICE] Supplement Serper: {len(iherb_organic)} iHerb + {len(bh_organic)} BH pharmacy results for {full_name}")
                organic_results = {"organic": combined_organic, "knowledge_graph": None}
            else:
                logger.info(f"[PRICE] No Serper results at all for {full_name}, falling to Tier 3")
                organic_results = {"organic": [], "knowledge_graph": None}
```

New code:
```python
            return iherb_price

            # Direct scrape failed — search iHerb + Bahrain pharmacies in parallel
            logger.info(f"[PRICE] iHerb direct scrape failed, trying Serper + Bahrain pharmacy for {full_name}")
            iherb_task = search_web(f"{iherb_query} iherb price", num_results=5, country=iherb_cc)
            bh_pharmacy_task = search_web(f"{brand} {name} price", num_results=5, country="bh")
            iherb_results, bh_pharmacy_results = await asyncio.gather(iherb_task, bh_pharmacy_task)
            self._track_cost(0.002)  # 2 Serper calls
            iherb_organic = iherb_results.get("organic", [])
            bh_organic = bh_pharmacy_results.get("organic", [])

            # NEW: Try JSON-LD extraction from Bahrain pharmacy product pages (FREE)
            pharmacy_price = await self._fetch_pharmacy_price(bh_organic, brand, full_name, currency)
            if pharmacy_price:
                pharmacy_price["_cached"] = False
                logger.info(f"[PRICE] Supplement: pharmacy JSON-LD price {currency} {pharmacy_price['amount']} for {full_name}")
                set_cached(cache_key, pharmacy_price, PRICE_CACHE_TTL)
                return pharmacy_price

            # Combine results for GPT extraction fallback
            combined_organic = iherb_organic + bh_organic
            if combined_organic:
                logger.info(f"[PRICE] Supplement Serper: {len(iherb_organic)} iHerb + {len(bh_organic)} BH pharmacy results for {full_name}")
                organic_results = {"organic": combined_organic, "knowledge_graph": None}
            else:
                logger.info(f"[PRICE] No Serper results at all for {full_name}, falling to Tier 3")
                organic_results = {"organic": [], "knowledge_graph": None}
```

The ONLY change is inserting the 6-line `pharmacy_price` block after the Serper calls and before the `combined_organic` assembly. Everything else is untouched.

**Step 3: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No errors

**Step 4: Run all existing tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS (existing URL extraction tests + new pharmacy tests)

**Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: integrate pharmacy JSON-LD into supplement price pipeline"
```

---

### Task 4: Production test and deploy

**Step 1: Local smoke test (if running locally)**

Run: `python -c "from app.services.structured_comparison_service import StructuredComparisonService; print('Import OK')"`
Expected: `Import OK`

**Step 2: Push to deploy**

```bash
git push origin main
```
Wait ~90s for Railway deploy.

**Step 3: Verify health**

Run: `curl https://smartcompare-backend-production.up.railway.app/health`
Expected: `{"status": "ok"}`

**Step 4: Test HealthAid D3 comparison**

Run:
```bash
curl -s "https://smartcompare-backend-production.up.railway.app/api/v1/text/compare?q=NOW+High+Potency+Vitamin+D-3+360+Softgels+vs+HealthAid+Vitamin+D3+1000IU&nocache=true" -o response_pharmacy_test.json
```

Verify:
```bash
python -c "import json; d=json.load(open('response_pharmacy_test.json')); p=[x for x in d['products'] if 'HealthAid' in x.get('brand','')][0]; print('Price:', p['price']['amount'], p['price']['currency'], 'Retailer:', p['price']['retailer'], 'Est:', p['price'].get('estimated', False)); print('Cost:', d['metadata']['total_cost'])"
```

Expected:
- HealthAid D3 price: ~BHD 9.00 from "Bolo" (not estimated)
- Total cost: ~$0.01 or lower

**Step 5: Commit test results to docs (if successful)**

No commit needed — just verify the fix works.

---

## Summary

| Task | What | Files | Tests |
|------|------|-------|-------|
| 1 | JSON-LD parser (pure function) | service.py, test_pharmacy_jsonld.py | 8 unit tests |
| 2 | HTTP fetcher + coordinator | service.py, test_pharmacy_jsonld.py | 3 integration tests |
| 3 | Wire into _get_price() | service.py (6 lines added) | Existing tests pass |
| 4 | Deploy + verify | Push + curl | Manual production test |
