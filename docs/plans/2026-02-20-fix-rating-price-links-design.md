# Fix Rating & Price Links — Use Actual Product Page URLs

**Date:** 2026-02-20
**Status:** Approved
**Cost impact:** Zero additional API cost

## Problem

Rating and price links point to retailer search pages or Google Shopping searches instead of actual product pages.

**Root cause:** The Serper Shopping API `link` field — which contains the direct product page URL on the retailer's site — is available in the data but explicitly discarded. Instead, `_build_retailer_url()` generates generic retailer search URLs. The frontend then overrides even those with a hardcoded Google Shopping search.

**Current behavior:**
- Rating link for "NOW D3" → `https://www.walmart.com/search?q=NOW+D3` (search page)
- Price link for "Galaxy S25" → `https://www.google.com/search?tbm=shop&q=Samsung+Galaxy+S25` (Google)
- Frontend `openRatingSource()` always opens `google.com/search?q=...&tbm=shop`, ignoring `rating_source.url` entirely

## Solution: Approach A — Use Serper Shopping `link` field

Use the direct product URL already present in Serper Shopping results. Fall back to retailer search page URL when `link` is missing.

### Backend Changes (`app/services/structured_comparison_service.py`)

**1. Price URLs — `_extract_price_from_shopping()` (line 1046):**
```python
# Before
"url": self._build_retailer_url(retailer, product_name),
# After
"url": item.get("link") or self._build_retailer_url(retailer, product_name),
```

**2. Rating candidates — `_extract_rating_from_shopping()` (line 1601):**
Add `link` field to candidate dict:
```python
candidate = {
    ...
    "link": item.get("link"),  # NEW
    ...
}
```

**3. Consensus rating URL (line 1645):**
```python
# Before
"url": self._build_retailer_url(best["source"], product_name),
# After
"url": best.get("link") or self._build_retailer_url(best["source"], product_name),
```

**4. Tiered rating URL (line 1691):**
```python
# Before
"url": self._build_retailer_url(best["source"], product_name),
# After
"url": best.get("link") or self._build_retailer_url(best["source"], product_name),
```

**No changes needed for:**
- Tier 2/3 price backfill (no Serper Shopping data available)
- iHerb direct scrape (already returns real product URLs)
- GPT review aggregate fallback (no shopping data, `url: None` is correct)

### Frontend Changes (`SmartCompareApp/src/screens/ResultsScreen.tsx`)

**1. Fix `openRatingSource()` (lines 182-191):**
```tsx
// Before — always opens Google Shopping, ignoring backend URL
const query = encodeURIComponent(productName);
Linking.openURL(`https://www.google.com/search?q=${query}&tbm=shop`);

// After — prefer backend URL (now an actual product page)
if (source?.url) {
    Linking.openURL(source.url);
} else if (productName) {
    const query = encodeURIComponent(productName);
    Linking.openURL(`https://www.google.com/search?q=${query}&tbm=shop`);
}
```

**2. Add extract method handling in `getMethodLabel()`:**
- `google_shopping_consensus` → green "Verified"
- `gpt_review_aggregate` → gray "Unverified"

### Memory Fix

Correct the outdated note in MEMORY.md: Serper Shopping `link` field contains direct product page URLs, NOT Google redirects.

## Files Changed

| File | Change |
|------|--------|
| `app/services/structured_comparison_service.py` | Use `item.get("link")` in price and rating extraction |
| `SmartCompareApp/src/screens/ResultsScreen.tsx` | Fix `openRatingSource()`, add extract method badges |
| `MEMORY.md` | Correct Serper Shopping `link` documentation |

## Verification

Test with `?nocache=true`:
- `NOW D3 vs HealthAid D3` — supplement comparison
- `iPhone 16 vs Galaxy S25` — electronics comparison

Verify:
1. Rating `url` fields contain actual product page URLs (not search pages)
2. Price `url` fields contain actual product page URLs where available
3. Frontend rating tap opens the actual product page
4. Fallback to retailer search page when `link` is missing
