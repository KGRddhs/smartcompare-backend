# Design: Bahrain Pharmacy JSON-LD Price Extraction

**Date:** 2026-02-21
**Status:** Approved
**Cost impact:** $0.000 extra per comparison

## Problem

Supplements not sold on iHerb (e.g., HealthAid, Vitabiotics) get wrong prices. The iHerb scraper either matches a wrong product or returns nothing, and the GPT fallback produces inconsistent estimates (BHD 3.77, 5.66, 7.71 across tests vs real price of BHD 9.00).

**Root cause:** HealthAid and similar UK/GCC brands are sold at Bahrain pharmacies (bolo.bh, Boots, Nasser Pharmacy), not iHerb. The existing Serper fallback finds these URLs but relies on GPT to extract prices from search snippets, which is unreliable.

## Solution

Parse JSON-LD structured data from Bahrain pharmacy product pages. Most pharmacy sites embed `Product` schema with exact BHD prices in their HTML, even when the rest of the page is SPA-rendered.

### Validated pharmacy JSON-LD support

| Pharmacy | Domain | JSON-LD Price | Verified |
|---|---|---|---|
| Bolo.bh | bolo.bh | Yes (BHD 9.00) | Yes |
| Boots Bahrain | bn.boots.com | Yes (BHD 6.30) | Yes |
| Al Deerah | aldeerahpharmacy.com | Unknown | Not tested |
| Nasser Pharmacy | nasserpharmacy.com | No (full SPA) | Yes |

### Updated supplement price pipeline

```
1. iHerb direct scrape (existing, works for iHerb brands)
   | no brand match
   v
2. Serper BH pharmacy search (existing, line 589)
   | gets organic results with pharmacy URLs
   v
3. NEW: Fetch pharmacy product pages -> parse JSON-LD
   | For each URL matching PHARMACY_DOMAINS:
   |   - HTTP GET product page
   |   - Find <script type="application/ld+json">
   |   - Parse Product.offers.price where priceCurrency == "BHD"
   |   - Verify brand name in product title
   |   - Return first match with retailer name + direct URL
   | no JSON-LD found
   v
4. GPT extraction from snippets (existing fallback)
   | GPT fails
   v
5. Tier 3 GPT estimate (existing)
```

### New function: `_fetch_pharmacy_price()`

```python
PHARMACY_DOMAINS = {
    "bolo.bh": "Bolo",
    "bn.boots.com": "Boots",
    "aldeerahpharmacy.com": "Al Deerah Pharmacy",
}

async def _fetch_pharmacy_price(
    self,
    serper_organic: List[Dict],  # Already-fetched Serper results
    brand: str,
    full_name: str,
    currency: str
) -> Optional[Dict[str, Any]]:
```

**Logic:**
1. Filter Serper organic results for URLs matching `PHARMACY_DOMAINS`
2. For each matching URL (max 3 attempts):
   - Fetch page with `httpx` (10s timeout, no TLS bypass needed)
   - Parse all `<script type="application/ld+json">` tags
   - Find `@type: "Product"` with `offers.price` and `priceCurrency == "BHD"`
   - Verify brand name appears in JSON-LD product name
   - Return price dict with retailer name and product URL
3. Return `None` if no match

**Returns:**
```python
{
    "amount": 9.00,
    "currency": "BHD",
    "original_currency": "BHD",
    "retailer": "Bolo",
    "url": "https://www.bolo.bh/products/KO0076KF628-healthaid-vitamin-d3...",
    "in_stock": True,
    "confidence": 1.0,
    "estimated": False,
}
```

### Integration point

In `_get_price()`, after iHerb scrape fails (line 584), restructure so the Serper BH pharmacy search runs first, then pharmacy JSON-LD parsing uses those results, then GPT extraction uses the remaining results.

### Edge cases

- **Multiple offers:** use lowest `price` in offers array
- **Currency mismatch:** skip if `priceCurrency != "BHD"`
- **Product mismatch:** verify brand name in JSON-LD `name` field
- **Timeout:** 10s per fetch, fail gracefully
- **No Serper pharmacy URLs:** skip straight to GPT extraction

### Cost impact

$0.000 extra. The Serper search already happens (line 589). Pharmacy page fetches are free HTTP requests. JSON-LD parsing is local string parsing.

### What doesn't change

- iHerb scraping (unmodified)
- Rating pipeline (unmodified)
- Spec extraction (unmodified)
- Review extraction (unmodified)
- Cost target remains ~$0.01 per comparison
