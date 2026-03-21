# Design: Luxury & Supplement Price Extraction Fix

**Date:** 2026-03-21
**Problem:** Luxury brand prices (LV, Hermès, Chanel) and some supplement prices show wrong/estimated numbers despite having access to correct source URLs. An LV cap at ~340 BHD shows as ~50-160 BHD.

## Root Cause

The price pipeline has 4 tiers. Luxury brands fall through all of them because:

1. **Tier 1 (Serper Shopping):** Official luxury sites are JS-rendered — Google Shopping doesn't index their prices.
2. **Tier 1.5 (Official Domain Search):** Searches `site:hermes.com` but only reads Serper **snippets**, not the actual page. JS-rendered pages have no prices in snippets.
3. **Tier 2 (GPT from organic):** May find a marketplace price, but the **Tier 2 sanity check** (lines ~1089-1115) uses hardcoded 2.0x/0.5x thresholds for ALL non-supplement products — unlike Tier 1's sanity check (lines ~930-934) which already has luxury-aware 1.8x/0.6x thresholds. This means Tier 2 rejects valid high luxury prices.
4. **Tier 3 (GPT estimate):** Falls back to training data guess. Often far too low for luxury items.

**The correct price was never extracted.** We have the right URLs but never actually fetch the pages.

## Solution Overview

Three-part fix using only the current stack (Serper + GPT + curl_cffi):

1. **New `_fetch_page_price()` method** — Generic page scraper that extracts prices from structured data (reusing existing `_extract_jsonld_price()` for JSON-LD, plus OpenGraph and microdata fallbacks).
2. **Enhanced Tier 1.5 with sub-tiers** — Official brand → authorized retailers → GCC retailers, each with page scraping.
3. **Bug fixes** — Tier 2 luxury sanity thresholds + frontend estimated/retailer display.

**Feature flag:** `ENABLE_PAGE_SCRAPE` env var (default `true`). Set to `false` to disable all page scraping without redeploying.

## Detailed Design

### 1. `_fetch_page_price(url, product_name, currency)` Method

A single generic method in `structured_comparison_service.py` that fetches any product page and extracts the price from structured data.

**Location:** `app/services/structured_comparison_service.py`, new method on `StructuredComparisonService`

**Signature:**
```python
async def _fetch_page_price(self, url: str, product_name: str, currency: str = "BHD") -> Optional[dict]:
```

**Extraction priority (same page, first match wins):**
1. **JSON-LD** — Reuse existing `_extract_jsonld_price()` method (line ~1555) which already handles `@type: Product` schema parsing, brand matching, currency verification, offer extraction, and out-of-stock detection. Pass the fetched HTML to it.
2. **OpenGraph meta** — `<meta property="og:price:amount">` + `<meta property="og:price:currency">`
3. **Product meta** — `<meta property="product:price:amount">`
4. **Microdata** — `[itemprop="price"]` content attribute

**Implementation details:**
- Uses `curl_cffi` with `impersonate="chrome"` (matches existing iHerb scraping pattern)
- 10-second timeout per fetch (`PAGE_SCRAPE_TIMEOUT` constant)
- Parses HTML with `BeautifulSoup` (already a dependency via `bs4`)
- JSON-LD step delegates to existing `_extract_jsonld_price()` — no code duplication
- Currency detection from page data → conversion to BHD using existing `_convert_gpt_price_currency()` logic
- Returns `{ amount, currency, retailer: domain_name, url, source_method: "page_scrape" }` or `None`
- Logs: domain, extraction method used, price found (or failure reason)

**Error handling:**
- HTTP errors (403, 404, 500) → return None, log warning
- Timeout → return None, log warning
- No structured price data found → return None
- Invalid/zero price → return None

### 2. Enhanced Tier 1.5 Orchestration

Replace the current single-step Tier 1.5 with a cascading sub-tier system. Total budget timeout: **20 seconds** across all sub-tiers to prevent excessive latency in the SSE streaming flow.

```
If Tier 1 (Shopping) fails AND _is_luxury_brand(product_name):

  Tier 1.5a — Official Brand Site:
    1. official_domain = _get_official_domain(product_name)  # existing method
    2. results = search_web(f"{product_name} site:{official_domain}")  # existing Serper call
    3. For top 2 result URLs:
       price = await _fetch_page_price(url, product_name, currency)  # NEW
       If price found → return (retailer_score=1.0, skip sanity check)
    4. Cost: $0.001 (Serper) + 1-2 HTTP fetches (free)

  Tier 1.5b — Authorized Retailers (only if 1.5a failed):
    1. AUTHORIZED_LUXURY_RETAILERS = {
         "farfetch.com", "ssense.com", "net-a-porter.com",
         "mytheresa.com", "matchesfashion.com", "nordstrom.com"
       }
    2. Search each domain individually (NOT OR-joined, to avoid query length issues):
       Pick top 2 domains by relevance → 1 Serper call per domain (max 2 calls)
       OR: Single Serper call with "product_name farfetch OR ssense OR net-a-porter"
       (Validate during implementation which approach works better with Serper)
    3. For top 3 result URLs (parallel with asyncio.gather):
       prices = await asyncio.gather(*[
           self._fetch_page_price(url, product_name, currency) for url in urls[:3]
       ])
    4. Cross-validation: if 2+ non-None prices where max/min <= 1.15 → use lowest
       If only 1 price found → use it (retailer_score=0.85)
    5. Cost: $0.001-0.002 (1-2 Serper calls) + 1-3 HTTP fetches (free)

  Tier 1.5c — GCC Retailers (only if 1.5b failed):
    1. GCC_LUXURY_RETAILERS = {
         "ounass.ae", "namshi.com", "bloomingdales.ae",
         "level-shoes.com"
       }
    2. results = search_web(f"{product_name} ounass OR bloomingdales dubai")
    3. For top 2 result URLs:
       price = await _fetch_page_price(url, product_name, currency)
       Convert AED → BHD (1 AED ≈ 0.1025 BHD, existing conversion)
    4. If price found → return (retailer_score=0.85)
    5. Cost: $0.001 (Serper) + 1-2 HTTP fetches (free)
```

**Maximum cost for worst case (all sub-tiers tried):** $0.004 (3-4 Serper calls) + 7 HTTP fetches. This only happens for luxury brands when Tier 1 Shopping completely fails.

**Typical cost for luxury:** $0.001-0.002 (1-2 Serper calls). Most luxury items will be found on authorized retailers (Tier 1.5b).

**Streaming latency note:** The 20-second budget timeout ensures the SSE `prices` event fires within reasonable time. Each sub-tier checks remaining budget before starting. If budget exhausted, falls through to Tier 2/3 immediately.

### 3. Supplement Price Enhancement

The iHerb scraping pipeline already works for most supplements. For non-iHerb brands, the pharmacy JSON-LD pipeline exists. The enhancement:

**Insertion point:** In the supplement branch of `_get_price()`, after iHerb scraping fails and before GPT extraction (~line 1040), iterate Serper organic result URLs and try `_fetch_page_price()` on URLs from known pharmacy/retailer domains.

- Check if the organic result URL domain is in `PHARMACY_DOMAINS` or known supplement retailers
- If yes → `await _fetch_page_price(url, product_name, currency)`
- This reuses `_extract_jsonld_price()` internally, which is the same pattern as `_fetch_pharmacy_price()` but generalized
- No new Serper calls needed — piggyback on existing unified search results
- If page scrape succeeds → use that price (skips GPT extraction, saves ~$0.002)

### 4. Bug Fixes

#### 4a. Tier 2 Sanity Check — Add Luxury Thresholds

**Context:** Tier 1's sanity check (lines ~930-934) already has luxury-aware thresholds:
```python
# Tier 1 sanity — ALREADY CORRECT
if self._is_luxury_brand(full_name):
    high_threshold = 1.8; low_threshold = 0.6
else:
    high_threshold = 2.0; low_threshold = 0.5
```

**Bug:** Tier 2's sanity check (lines ~1089-1115) does NOT have this — it uses hardcoded 2.0/0.5 for ALL products:

```python
# Tier 2 sanity — CURRENT (missing luxury thresholds)
if tier2_bhd > tier3_bhd * 2:
    price = tier3_estimate  # Downgrades valid luxury price
```

**Fix:** Add the same luxury threshold logic to Tier 2:

```python
# Tier 2 sanity — FIXED
if self._is_luxury_brand(full_name):
    high_threshold = 1.8
    low_threshold = 0.6
else:
    high_threshold = 2.0
    low_threshold = 0.5

if tier2_bhd > tier3_bhd * high_threshold:
    price = tier3_estimate
elif tier2_bhd < tier3_bhd * low_threshold:
    price = tier3_estimate
```

#### 4b. Frontend — Estimated Price Indicator

**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

When `price.estimated === true` or `price.source_method === "estimated"`, show "(estimated)" label below the price in a muted style. This sets user expectations correctly.

The new `source_method: "page_scrape"` does NOT need a special frontend indicator — it's a real price from a real source. It should display the same as any other real price with retailer attribution.

#### 4c. Frontend — Retailer Attribution

**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

Debug and fix why retailer name doesn't show for some products. The code at line 378-380 already handles this — investigate whether the backend isn't populating `retailer` for some code paths (especially Tier 2 and Tier 3).

### 5. Constants and Configuration

**New constants in `structured_comparison_service.py`:**

```python
AUTHORIZED_LUXURY_RETAILERS = {
    "farfetch.com", "ssense.com", "net-a-porter.com",
    "mytheresa.com", "matchesfashion.com", "nordstrom.com",
}

GCC_LUXURY_RETAILERS = {
    "ounass.ae", "namshi.com", "bloomingdales.ae",
    "level-shoes.com",
}

PAGE_SCRAPE_TIMEOUT = 10  # seconds per fetch
TIER_15_BUDGET_TIMEOUT = 20  # seconds total across all Tier 1.5 sub-tiers
```

**Environment variable:**
- `ENABLE_PAGE_SCRAPE` (default: `"true"`) — Set to `"false"` to disable all page scraping without redeploying. Checked at the top of `_fetch_page_price()`.

### 6. Caching

- Page-scraped prices cached with same TTL as Tier 1 prices (24h)
- Cache key includes URL domain to distinguish sources
- `source_method: "page_scrape"` tag for analytics

### 7. Logging

Each sub-tier logs:
- Which tier attempted and result (found/failed/timeout)
- Domain scraped, extraction method (JSON-LD/OG/microdata)
- Price found (amount + currency) or failure reason
- Total latency for the scrape
- Remaining budget timeout

## Cost Impact

| Scenario | Current Cost | New Cost | Delta |
|----------|-------------|----------|-------|
| Non-luxury product | $0.010 | $0.010 | $0 |
| Luxury, Tier 1 works | $0.010 | $0.010 | $0 |
| Luxury, Tier 1.5a works | $0.011 | $0.011 | $0 (same Serper call, but now gets real price) |
| Luxury, needs 1.5b | $0.011 | $0.012-0.013 | +$0.001-0.002 |
| Luxury, needs 1.5c | $0.011 | $0.013-0.014 | +$0.002-0.003 |
| Worst case (all fail) | $0.011 | $0.015 | +$0.004 |

All within the $0.015 budget target.

## Testing Strategy

**Unit tests (free, mocked):**
- `test_page_scraping.py` — 15+ tests:
  - JSON-LD extraction via `_extract_jsonld_price()` delegation (valid Product schema, nested offers, multiple products)
  - OpenGraph meta extraction
  - Microdata extraction
  - Currency detection + conversion (AED → BHD, USD → BHD, EUR → BHD)
  - Timeout handling, HTTP errors (403/404/500), empty pages
  - No structured data found → returns None
  - Feature flag disabled → returns None immediately
- `test_luxury_price_tiers.py` — 10+ tests:
  - Tier 1.5a → 1.5b → 1.5c cascade (each sub-tier only when previous fails)
  - Budget timeout enforcement (20s across all sub-tiers)
  - Cross-validation logic: 2+ prices where `max/min <= 1.15` → use lowest
  - Cross-validation: prices too far apart → use single best
  - GCC currency conversion (AED → BHD)
  - Retailer score assignment per tier (1.0, 0.9, 0.85)
- Update `test_luxury_brands.py` — 5+ new tests:
  - Tier 2 sanity check now uses 1.8x/0.6x for luxury (bug fix)
  - Tier 1 sanity check still uses 1.8x/0.6x (no regression)
  - Official domain bypass still works (retailer_score >= 1.0)

**Target:** 80%+ coverage on new code, all existing 944 tests still pass.

## Files Changed

| File | Changes |
|------|---------|
| `app/services/structured_comparison_service.py` | `_fetch_page_price()`, enhanced Tier 1.5 orchestration, Tier 2 bug fix, new constants, feature flag |
| `SmartCompareApp/src/screens/ResultsScreen.tsx` | Estimated price indicator, retailer display fix |
| `tests/test_page_scraping.py` | NEW — 15+ tests for page scraping |
| `tests/test_luxury_price_tiers.py` | NEW — 10+ tests for tier cascade |
| `tests/test_luxury_brands.py` | 5+ new tests for Tier 2 bug fix |

## Implementation Team (4 Opus Agents)

1. **Backend Agent** — Implements `_fetch_page_price()`, enhanced Tier 1.5 orchestration, Tier 2 bug fix, constants, feature flag
2. **Frontend Agent** — Implements estimated price indicator, retailer display fix, debug retailer attribution
3. **Test Agent** — Writes all new tests (red-green), ensures 80%+ coverage on new code
4. **QA Agent** — Reviews each agent's work, sends back subpar work, validates integration, runs full test suite

**Cross-QA rule:** Each member QAs another's work before the team disbands. Idle members write red-green tests or wait for QA results.

## Success Criteria

1. LV cap comparison returns ~340 BHD (not ~50-160 BHD) from official/authorized source
2. Hermès products return official prices from hermes.com or authorized retailers
3. All luxury brands get real prices when available, estimated only as last resort
4. "Estimated" flag visible in frontend when price is Tier 3
5. Retailer name always displayed when available
6. All 944+ existing tests pass (no regressions)
7. New tests achieve 80%+ coverage on new code
8. Cost stays within $0.015/comparison budget
9. Feature flag `ENABLE_PAGE_SCRAPE=false` disables all scraping cleanly
