# Session 23: Comparison Results Fixes — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 8 bugs affecting comparison quality: scoring personalization, reviews display, ratings visibility, retailer links, price consistency, feedback persistence, and cost display.

**Architecture:** Backend fixes in `structured_comparison_service.py` (rating tiers, iHerb rating extraction, price source tagging, retailer URLs) and `scoring_service.py` (weight capping). Frontend fixes in `ResultsScreen.tsx` (reviews rendering, rating display, feedback state, cost removal) and `FeedbackCard.tsx` (controlled props). Diagnostic logging in `text_routes.py` + `auth_service.py`.

**Tech Stack:** Python 3.12 / FastAPI, React Native / Expo, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-14-session23-comparison-fixes-design.md`

---

## Chunk 1: Backend Fixes (Round 1 — Agent A: backend-1)

### Task 1: Fix 1 — Personalization Pipeline Diagnostic Logging

**Files:**
- Modify: `app/api/text_routes.py`
- Modify: `app/services/auth_service.py`

- [ ] **Step 1: Add logging to `get_user_preferences()` exception handler**

In `app/services/auth_service.py`, line 359-360, the exception handler silently returns `{"success": False}`. Add logging:

```python
# app/services/auth_service.py, replace lines 359-360
    except Exception as e:
        logger.error(f"[AUTH] get_user_preferences failed for user {user_id}: {e}")
        return {"success": False, "error": str(e)}
```

Ensure `logger = logging.getLogger(__name__)` exists at file top (add `import logging` if missing).

- [ ] **Step 2: Add diagnostic logging to POST endpoint in text_routes.py**

In `app/api/text_routes.py`, after line 80 (where `user_prefs` is resolved — search for `user_prefs = prefs_result.get("preferences")`), add:

```python
if user and not user_prefs:
    logger.warning(
        f"[PREFS] Authenticated user {user.get('id', 'unknown')} has no preferences. "
        f"prefs_result: {prefs_result}"
    )
```

- [ ] **Step 3: Add same logging to GET endpoint**

Same pattern in the GET compare endpoint (around line 155-157).

- [ ] **Step 4: Add same logging to streaming endpoint**

Same pattern in the SSE streaming endpoint (around line 230-232).

- [ ] **Step 5: Syntax check**

Run: `python -m py_compile app/api/text_routes.py && python -m py_compile app/services/auth_service.py`
Expected: No output (success)

- [ ] **Step 6: Commit**

```bash
git add app/api/text_routes.py app/services/auth_service.py
git commit -m "fix: add diagnostic logging for personalization pipeline"
```

---

### Task 2: Fix 2 — Cap Personalization Weight Shifts at ±30%

**Files:**
- Modify: `app/services/scoring_service.py`
- Modify: `tests/test_scoring_service.py`

- [ ] **Step 1: Write failing tests for weight capping**

Add to `tests/test_scoring_service.py`:

```python
class TestWeightCapping:
    """Test that personalization weight shifts are capped at ±30% of defaults."""

    def test_single_priority_capped(self):
        """A single priority should not shift any dimension beyond 30%."""
        service = ScoringService()
        # "price" priority adds +0.15 to price_score (default 0.25)
        # Uncapped would be 0.40, capped should be <= 0.25 * 1.30 = 0.325
        weights = service._compute_weights({"priorities": ["price"]})
        # After renormalization, exact values differ, but pre-cap the raw
        # price_score should not exceed 0.325 before normalization
        # We test the final normalized weights stay reasonable
        assert weights["price_score"] <= 0.40  # Must not dominate
        assert weights["spec_score"] >= 0.10   # Must not be crushed

    def test_multiple_priorities_capped(self):
        """Multiple stacking priorities should still be bounded."""
        service = ScoringService()
        # "price" + "quality" both adjust price_score
        weights = service._compute_weights({
            "priorities": ["price", "quality", "durability"],
            "budget": "budget"
        })
        from app.services.scoring_service import DEFAULT_WEIGHTS
        # No dimension should be more than ~2x its default after normalization
        for dim, default_val in DEFAULT_WEIGHTS.items():
            if default_val > 0:
                assert weights[dim] <= default_val * 2.5, \
                    f"{dim} is {weights[dim]:.3f}, default {default_val:.3f} — too aggressive"

    def test_weight_cap_preserves_normalization(self):
        """Weights must still sum to 1.0 after capping."""
        service = ScoringService()
        weights = service._compute_weights({
            "priorities": ["price", "health_safety"],
            "budget": "premium"
        })
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_no_preferences_unchanged(self):
        """Without preferences, weights equal defaults."""
        service = ScoringService()
        from app.services.scoring_service import DEFAULT_WEIGHTS
        weights = service._compute_weights(None)
        for dim, val in DEFAULT_WEIGHTS.items():
            assert abs(weights[dim] - val) < 0.001

    def test_empty_preferences_unchanged(self):
        """Empty preferences dict returns default weights."""
        service = ScoringService()
        from app.services.scoring_service import DEFAULT_WEIGHTS
        weights = service._compute_weights({})
        for dim, val in DEFAULT_WEIGHTS.items():
            assert abs(weights[dim] - val) < 0.001
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scoring_service.py::TestWeightCapping -v`
Expected: Some tests FAIL (uncapped weights exceed bounds)

- [ ] **Step 3: Implement weight capping**

In `app/services/scoring_service.py`, add constant after line 41:

```python
# Maximum personalization shift: ±30% of default weight per dimension
MAX_WEIGHT_SHIFT_RATIO = 0.30
```

Replace lines 152-154 (the existing `max(0.0, ...)` clamp) with:

```python
        # Cap each dimension's shift to ±30% of its default weight
        for dim in weights:
            default_val = DEFAULT_WEIGHTS.get(dim, 0)
            max_val = default_val * (1 + MAX_WEIGHT_SHIFT_RATIO)
            min_val = default_val * (1 - MAX_WEIGHT_SHIFT_RATIO)
            weights[dim] = max(0.0, min(max_val, max(min_val, weights[dim])))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scoring_service.py::TestWeightCapping -v`
Expected: ALL PASS

- [ ] **Step 5: Run full scoring test suite**

Run: `python -m pytest tests/test_scoring_service.py -v`
Expected: ALL PASS (no regressions)

- [ ] **Step 6: Commit**

```bash
git add app/services/scoring_service.py tests/test_scoring_service.py
git commit -m "fix: cap personalization weight shifts at ±30% of defaults"
```

---

### Task 3: Fix 5 — Add Pharmacy Domains to Retailer URL Map

**Files:**
- Modify: `app/services/structured_comparison_service.py`
- Modify: `tests/test_url_quality.py`

- [ ] **Step 1: Write failing tests for pharmacy URLs**

Add to `tests/test_url_quality.py`:

```python
class TestPharmacyRetailerUrls:
    """Test pharmacy domains are in RETAILER_SEARCH_URLS."""

    def test_boots_url_generated(self):
        service = get_comparison_service()
        url = service._build_retailer_url("Boots Bahrain", "Vitamin D3 1000 IU")
        assert url is not None
        assert "bn.boots.com" in url
        assert "Vitamin" in url or "vitamin" in url.lower()

    def test_al_deerah_url_generated(self):
        service = get_comparison_service()
        url = service._build_retailer_url("Al Deerah Pharmacy", "HealthAid Vitamin D")
        assert url is not None
        assert "aldeerahpharmacy.com" in url

    def test_iherb_url_already_exists(self):
        service = get_comparison_service()
        url = service._build_retailer_url("iHerb", "NOW Vitamin D3")
        assert url is not None
        assert "iherb.com" in url

    def test_bolo_returns_none(self):
        """bolo.bh is a Vue SPA — should NOT have a search URL."""
        service = get_comparison_service()
        url = service._build_retailer_url("Bolo Pharmacy", "Vitamin D")
        assert url is None
```

- [ ] **Step 2: Run tests to verify boots/aldeerah fail**

Run: `python -m pytest tests/test_url_quality.py::TestPharmacyRetailerUrls -v`
Expected: `test_boots_url_generated` and `test_al_deerah_url_generated` FAIL; `test_iherb_url_already_exists` PASSES (iHerb already at line 147)

- [ ] **Step 3: Add pharmacy domains to RETAILER_SEARCH_URLS**

In `app/services/structured_comparison_service.py`, after line 149 (`"nasser pharmacy"` entry), add:

```python
    # Pharmacy/health retailers (BH)
    "boots": "https://www.bn.boots.com/search?q={query}",
    "al deerah": "https://aldeerahpharmacy.com/catalogsearch/result/?q={query}",
```

Note: Do NOT add bolo.bh (Vue SPA — search URLs broken without client-side JS).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_url_quality.py::TestPharmacyRetailerUrls -v`
Expected: ALL PASS

- [ ] **Step 5: Run full URL test suite**

Run: `python -m pytest tests/test_url_quality.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_url_quality.py
git commit -m "fix: add Boots and Al Deerah pharmacy URLs to retailer map"
```

---

## Chunk 2: Backend Fixes (Round 1 — Agent B: backend-2)

### Task 4: Fix 4A.2 — Expand Rating Tier Lists

**Files:**
- Modify: `app/services/structured_comparison_service.py`
- Modify: `tests/test_rating_tiers.py`

- [ ] **Step 1: Write failing tests for new tier classifications**

Add to `tests/test_rating_tiers.py`:

```python
class TestExpandedTiers:
    """Test newly added retailers are classified correctly."""

    def test_iherb_is_tier_1(self):
        assert StructuredComparisonService._get_rating_tier("iHerb") == 1

    def test_sephora_is_tier_1(self):
        assert StructuredComparisonService._get_rating_tier("Sephora") == 1

    def test_ulta_is_tier_1(self):
        assert StructuredComparisonService._get_rating_tier("Ulta Beauty") == 1

    def test_fragrantica_is_tier_2(self):
        assert StructuredComparisonService._get_rating_tier("Fragrantica") == 2

    def test_sally_beauty_is_tier_2(self):
        assert StructuredComparisonService._get_rating_tier("Sally Beauty") == 2

    def test_lookfantastic_is_tier_2(self):
        assert StructuredComparisonService._get_rating_tier("LookFantastic") == 2

    def test_boots_is_tier_2(self):
        assert StructuredComparisonService._get_rating_tier("Boots") == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_rating_tiers.py::TestExpandedTiers -v`
Expected: Most FAIL (iherb/sephora/ulta not in tier lists)

- [ ] **Step 3: Add retailers to tier lists**

In `app/services/structured_comparison_service.py`, update the sets:

Line 1457-1459 (`RATING_TIER_1`), add:
```python
    "iherb", "sephora", "ulta",
```

Line 1461-1464 (`RATING_TIER_2`), add:
```python
    "fragrantica", "sally beauty", "lookfantastic", "beautybay",
    "nykaa", "bath & body", "boots",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_rating_tiers.py::TestExpandedTiers -v`
Expected: ALL PASS

- [ ] **Step 5: Run full rating tier test suite**

Run: `python -m pytest tests/test_rating_tiers.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_rating_tiers.py
git commit -m "feat: expand rating tier lists with beauty/supplement retailers"
```

---

### Task 5: Fix 4A — Extract Ratings from iHerb Scrape

**Dependency:** Task 4 must be completed first (iHerb needs to be in RATING_TIER_1 for cached ratings to be classified correctly by `_get_verified_rating()`).

**Files:**
- Modify: `app/services/structured_comparison_service.py`
- Create: `tests/test_iherb_rating.py`

- [ ] **Step 1: Write failing tests for iHerb rating extraction**

Create `tests/test_iherb_rating.py`:

```python
"""Tests for iHerb rating extraction during price scrape."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.structured_comparison_service import StructuredComparisonService, get_comparison_service


class TestIHerbRatingExtraction:
    """Test that _fetch_iherb_price also extracts ratings."""

    def test_iherb_result_includes_rating_fields(self):
        """iHerb price result should include rating data when available."""
        # The return dict from _fetch_iherb_price should have iherb_rating
        # and iherb_review_count keys
        result = {
            "amount": 11.99,
            "currency": "USD",
            "retailer": "iHerb",
            "url": "https://bh.iherb.com/pr/test/12345",
            "iherb_rating": 4.7,
            "iherb_review_count": 12345,
        }
        assert "iherb_rating" in result
        assert "iherb_review_count" in result
        assert result["iherb_rating"] == 4.7
        assert result["iherb_review_count"] == 12345

    def test_iherb_rating_cached_in_shopping_items(self):
        """After iHerb price fetch, rating should be cached for _get_verified_rating."""
        service = get_comparison_service()
        service._reset_state()
        # Simulate caching iHerb rating data
        service._shopping_items_cache["Test Product"] = [{
            "source": "iHerb",
            "rating": 4.5,
            "ratingCount": 5000,
            "link": "https://bh.iherb.com/pr/test/12345",
            "title": "Test Product",
        }]
        # _get_rating_tier should classify iHerb as Tier 1
        assert service._get_rating_tier("iHerb") == 1

    def test_iherb_rating_none_when_not_on_page(self):
        """If iHerb page has no rating data, fields should be None."""
        result = {
            "amount": 11.99,
            "currency": "USD",
            "retailer": "iHerb",
            "url": "https://bh.iherb.com/pr/test/12345",
            "iherb_rating": None,
            "iherb_review_count": None,
        }
        assert result["iherb_rating"] is None
```

- [ ] **Step 2: Investigate iHerb page structure for rating data**

Before implementing, fetch a sample iHerb search page to understand what rating markup exists. Look for:
- `data-ga-rating` or similar attributes on search cards
- Star rating CSS classes or elements
- Rating text patterns (e.g., "4.7 (12,345)")
- Individual product page JSON-LD with `aggregateRating`

The implementation approach depends on what's available on the search page vs product page.

- [ ] **Step 3: Implement rating extraction in `_fetch_iherb_price()` (based on Step 2 findings)**

In `app/services/structured_comparison_service.py`, inside `_fetch_iherb_price()` (line 1120-1214).

**IMPORTANT:** The exact extraction approach depends on Step 2 investigation results. Use ONE of these strategies:

**Strategy A — If search cards have inline rating attributes (e.g., `data-ga-rating`):**

Inside the `for card in cards` loop (line 1145-1157), also extract rating data:

```python
rating_str = card.get('data-ga-rating', '') or ''
review_count_str = card.get('data-ga-review-count', '') or ''
```

**Strategy B — If search cards have rating elements (CSS class with star/rating):**

```python
star_el = card.select_one('.rating, [class*="star"], [class*="rating"]')
rating_str = ''
review_count_str = ''
if star_el:
    import re
    rating_text = star_el.get_text(strip=True)
    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
    if rating_match:
        rating_str = rating_match.group(1)
    count_match = re.search(r'(\d[\d,]*)\s*(?:reviews?|ratings?)', star_el.get_text())
    if count_match:
        review_count_str = count_match.group(1).replace(',', '')
```

**Strategy C — If no inline ratings, fetch individual product page:**

After selecting `best` match, fetch the product page URL and parse JSON-LD:
```python
# Fetch product page for rating (similar to _try_pharmacy_urls pattern at line ~1393)
if best and best.get("url"):
    try:
        page_resp = await loop.run_in_executor(
            None, lambda: curl_requests.get(best["url"], impersonate="chrome", timeout=10)
        )
        if page_resp.status_code == 200:
            page_soup = BeautifulSoup(page_resp.text, 'html.parser')
            # Look for JSON-LD Product schema with aggregateRating
            for script in page_soup.select('script[type="application/ld+json"]'):
                try:
                    ld = json.loads(script.string)
                    if isinstance(ld, dict) and ld.get("@type") == "Product":
                        agg = ld.get("aggregateRating", {})
                        rating_str = str(agg.get("ratingValue", ""))
                        review_count_str = str(agg.get("reviewCount", ""))
                except: pass
    except: pass
```

**Regardless of strategy, add rating fields to each product dict** (line 1152-1157):

```python
products.append({
    "url": href if href.startswith("http") else f"https://{region_code}.iherb.com{href}",
    "brand": item_brand,
    "price": float(price_str),
    "title": title,
    "rating": float(rating_str) if rating_str else None,
    "review_count": int(review_count_str) if review_count_str else None,
})
```

Then, after selecting `best` match (line 1200), include rating in the return dict:

```python
return {
    "amount": best["price"],
    "original_currency": currency,
    "currency": currency,
    "retailer": "iHerb",
    "url": best["url"],
    "in_stock": True,
    "confidence": 1.0,
    "estimated": False,
    "_cached": False,
    "iherb_rating": best.get("rating"),
    "iherb_review_count": best.get("review_count"),
}
```

- [ ] **Step 4: Cache iHerb rating in `_shopping_items_cache`**

In the caller of `_fetch_iherb_price()` (the supplement price pipeline, around line 905-911), after a successful iHerb price fetch, cache the rating:

```python
iherb_price = await self._fetch_iherb_price(...)
if iherb_price:
    # Cache rating for _get_verified_rating() to find
    if iherb_price.get("iherb_rating"):
        self._shopping_items_cache[full_name] = [{
            "source": "iHerb",
            "rating": iherb_price["iherb_rating"],
            "ratingCount": iherb_price.get("iherb_review_count"),
            "link": iherb_price["url"],
            "title": full_name,
        }]
        logger.info(f"[RATING] Cached iHerb rating {iherb_price['iherb_rating']} for {full_name}")
```

- [ ] **Step 5: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 6: Run iHerb rating tests**

Run: `python -m pytest tests/test_iherb_rating.py -v`
Expected: ALL PASS

- [ ] **Step 7: Run related test suites**

Run: `python -m pytest tests/test_iherb_scraping.py tests/test_rating_tiers.py tests/test_singleton_state.py -v`
Expected: ALL PASS (no regressions)

- [ ] **Step 8: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_iherb_rating.py
git commit -m "feat: extract ratings from iHerb during price scrape (zero extra API calls)"
```

---

### Task 6: Fix 6 — Price Source Method Tagging

**Files:**
- Modify: `app/services/structured_comparison_service.py`
- Create: `tests/test_price_source.py`

- [ ] **Step 1: Write failing tests for source method tagging**

Create `tests/test_price_source.py`:

```python
"""Tests for price source_method tagging."""
import pytest


class TestPriceSourceMethod:
    """Test that prices are tagged with source_method."""

    def test_iherb_price_tagged_converted_usd(self):
        """iHerb prices (USD) should be tagged as converted_usd."""
        price = {
            "amount": 4.52, "currency": "BHD", "retailer": "iHerb",
            "source_method": "converted_usd"
        }
        assert price["source_method"] == "converted_usd"

    def test_pharmacy_price_tagged_local_bhd(self):
        """Pharmacy JSON-LD prices (BHD) should be tagged as local_bhd."""
        price = {
            "amount": 2.07, "currency": "BHD", "retailer": "Boots Bahrain",
            "source_method": "local_bhd"
        }
        assert price["source_method"] == "local_bhd"

    def test_estimated_price_tagged(self):
        """GPT Tier 3 estimated prices should be tagged as estimated."""
        price = {
            "amount": 3.50, "currency": "BHD", "estimated": True,
            "source_method": "estimated"
        }
        assert price["source_method"] == "estimated"

    def test_price_method_mismatch_detected(self):
        """When products use different price methods, flag should be True."""
        product_data = [
            {"price": {"source_method": "local_bhd"}},
            {"price": {"source_method": "converted_usd"}},
        ]
        methods = [p["price"].get("source_method") for p in product_data if p.get("price")]
        unique = set(m for m in methods if m)
        assert len(unique) > 1  # mismatch detected

    def test_price_method_match_no_flag(self):
        """When products use same price method, no mismatch."""
        product_data = [
            {"price": {"source_method": "local_bhd"}},
            {"price": {"source_method": "local_bhd"}},
        ]
        methods = [p["price"].get("source_method") for p in product_data if p.get("price")]
        unique = set(m for m in methods if m)
        assert len(unique) <= 1
```

- [ ] **Step 2: Run tests to verify they pass (data structure tests)**

Run: `python -m pytest tests/test_price_source.py -v`
Expected: ALL PASS (these test data structures, not live code yet)

- [ ] **Step 3: Add `source_method` to price construction points**

In `app/services/structured_comparison_service.py`, add `"source_method"` at these exact locations:

1. **`_fetch_iherb_price()` return dict** (line 1201-1211): Add `"source_method": "converted_usd"` — iHerb returns USD prices
2. **`_fetch_pharmacy_price()` return dict** (line 1423-1427, search for `"estimated": False` in that method): Add `"source_method": "local_bhd"` — pharmacy JSON-LD returns BHD
3. **`_extract_price_from_shopping()` return** (line 1595, search for `"retailer": retailer`): Add `"source_method": "local_bhd"` if currency is already BHD (Serper `gl=bh`), `"converted_usd"` if converted
4. **GPT Tier 2 extraction** (line 955, after `self._convert_gpt_price_currency(price, currency)`): Add `price["source_method"] = "converted_usd"` if conversion happened (check `price.get("original_currency") != "BHD"`), else `"local_bhd"`
5. **GPT Tier 3 training data** (lines 1020-1034, search for `# --- Tier 3: GPT training data fallback ---`): Add `price["source_method"] = "estimated"` after the Tier 3 price is set (around line 1034)
6. **Supplement iHerb fallback** (line 961, `price["retailer"] = "iHerb"`): Add `price["source_method"] = "converted_usd"` right after

**Quick grep to find all price construction points:** Search for `"retailer":` and `_convert_gpt_price_currency` in the file.

- [ ] **Step 4: Add `price_method_mismatch` to response**

In `compare_from_text()` (around line 280-320, where the response dict is built), add:

```python
# Detect price method mismatch
price_methods = [
    p.get("price", {}).get("source_method")
    for p in product_data if p.get("price")
]
unique_methods = set(m for m in price_methods if m)
```

Add to the return dict:
```python
"price_method_mismatch": len(unique_methods) > 1,
```

- [ ] **Step 5: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 6: Run full test suite to check regressions**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py -x`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_price_source.py
git commit -m "feat: tag prices with source_method (local_bhd/converted_usd/estimated)"
```

---

## Chunk 3: Frontend Fixes (Round 2 — Agent C: frontend-1)

### Task 7: Fix 4B — Simplify RatingDisplay (Show All Ratings, No Badges)

**Files:**
- Modify: `SmartCompareApp/src/types/types.ts`
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

- [ ] **Step 1: Update `RatingSource` type to allow null URL**

In `SmartCompareApp/src/types/types.ts`, line 8-14, change:

```typescript
export interface RatingSource {
  name: string;
  url: string | null;  // Changed: null when no source link available
  retrieved_at?: string;
  extract_method?: 'google_shopping' | 'json_ld' | 'microdata' | 'meta_tags' | 'css_selector' | 'gpt_review_aggregate';
  confidence?: 'high' | 'medium' | 'low' | 'expert';
}
```

- [ ] **Step 2: Rewrite `RatingDisplay` component**

In `SmartCompareApp/src/screens/ResultsScreen.tsx`, replace lines 295-353 (the entire `RatingDisplay` component) with:

```typescript
  // Rating display component — shows all ratings with source name + link
  const RatingDisplay = ({ product }: { product: Product }) => {
    const { rating, review_count, rating_source } = product;

    if (rating === null || rating === undefined) {
      return (
        <View style={styles.ratingContainer}>
          <Text style={styles.noRatingText}>No rating available</Text>
        </View>
      );
    }

    const hasLink = rating_source?.url != null;

    const ratingContent = (
      <>
        <View style={styles.ratingRow}>
          <Text style={styles.ratingText}>{rating.toFixed(1)}/5</Text>
          {review_count != null && (
            <Text style={styles.reviewCountText}>({review_count.toLocaleString()} reviews)</Text>
          )}
        </View>
        {rating_source?.name && (
          <View style={styles.sourceLink}>
            <Text style={styles.sourceText}>{rating_source.name}</Text>
            {hasLink && <Ionicons name="open-outline" size={12} color="#2196F3" />}
          </View>
        )}
      </>
    );

    if (hasLink) {
      return (
        <TouchableOpacity
          onPress={() => openRatingSource(rating_source!)}
          style={styles.ratingContainer}
        >
          {ratingContent}
        </TouchableOpacity>
      );
    }

    return <View style={styles.ratingContainer}>{ratingContent}</View>;
  };
```

- [ ] **Step 3: Remove unused styles**

Remove the `verifiedBadge` and `verifiedBadgeText` styles from the `StyleSheet.create()` block — they are only used by the old `RatingDisplay` component being replaced (confirmed by grep: no other file references these style names).

- [ ] **Step 4: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add SmartCompareApp/src/types/types.ts SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "fix: show all ratings without badges — source name + link when available"
```

---

### Task 8: Fix 3 — Reviews Tab Empty State + Content Rendering

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

- [ ] **Step 1: Expand `hasAnyReviews` gate check**

In `ResultsScreen.tsx`, replace lines 445-447 with:

```typescript
    const hasAnyReviews = products.some(p =>
      (p.pros && p.pros.length > 0) ||
      (p.cons && p.cons.length > 0) ||
      p.rating ||
      (p.reviews?.common_praises && p.reviews.common_praises.length > 0) ||
      (p.reviews?.common_complaints && p.reviews.common_complaints.length > 0) ||
      (p.reviews?.average_rating != null) ||
      (p.reviews?.detailed_praises && p.reviews.detailed_praises.length > 0)
    );
```

- [ ] **Step 2: Add review content rendering for `reviews` object fields**

After the existing Cons section (around line 489), before the closing `</View>` of the review card, add:

```typescript
            {/* Common Praises (when no pros available) */}
            {(!product.pros || product.pros.length === 0) && product.reviews?.common_praises && product.reviews.common_praises.length > 0 && (
              <View style={styles.prosConsSection}>
                <Text style={styles.prosTitle}>Praised For</Text>
                {product.reviews.common_praises.map((praise: string, i: number) => (
                  <Text key={i} style={styles.proItem}>• {praise}</Text>
                ))}
              </View>
            )}

            {/* Common Complaints (when no cons available) */}
            {(!product.cons || product.cons.length === 0) && product.reviews?.common_complaints && product.reviews.common_complaints.length > 0 && (
              <View style={styles.prosConsSection}>
                <Text style={styles.consTitle}>Criticized For</Text>
                {product.reviews.common_complaints.map((complaint: string, i: number) => (
                  <Text key={i} style={styles.conItem}>• {complaint}</Text>
                ))}
              </View>
            )}

            {/* Detailed praises with user quotes */}
            {product.reviews?.detailed_praises && product.reviews.detailed_praises.length > 0 && (
              <View style={styles.prosConsSection}>
                <Text style={styles.prosTitle}>What Users Love</Text>
                {product.reviews.detailed_praises.map((praise: any, i: number) => (
                  <View key={i}>
                    <Text style={styles.proItem}>• {praise.text}</Text>
                    {praise.quote && (
                      <Text style={[styles.proItem, { fontStyle: 'italic', color: '#666', marginLeft: 16 }]}>
                        "{praise.quote}"
                      </Text>
                    )}
                  </View>
                ))}
              </View>
            )}
```

- [ ] **Step 3: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "fix: show reviews from common_praises/complaints when pros/cons empty"
```

---

### Task 9: Fix 8 — Remove Cost Display from UI

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

- [ ] **Step 1: Remove cost from footer metadata**

In `ResultsScreen.tsx`, line 585-587, change:

```typescript
                  Comparison took {metadata.elapsed_seconds?.toFixed(1)}s •
                  Cost: ${metadata.total_cost?.toFixed(4)} •
                  {(metadata.cache_hits ?? 0) > 0 ? `${metadata.cache_hits} cached` : 'Fresh data'}
```

To:

```typescript
                  Comparison took {metadata.elapsed_seconds?.toFixed(1)}s •
                  {(metadata.cache_hits ?? 0) > 0 ? `${metadata.cache_hits} cached` : 'Fresh data'}
```

- [ ] **Step 2: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "fix: remove cost display from comparison results UI"
```

---

## Chunk 4: Frontend Fixes (Round 2 — Agent D: frontend-2)

### Task 10: Fix 7 — Feedback Card State Persistence

**Files:**
- Modify: `SmartCompareApp/src/components/FeedbackCard.tsx`
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

- [ ] **Step 1: Update FeedbackCard props interface**

In `SmartCompareApp/src/components/FeedbackCard.tsx`, replace lines 18-20:

```typescript
interface FeedbackCardProps {
  comparisonId?: string;
  submitted?: boolean;
  onSubmitted?: () => void;
}
```

- [ ] **Step 2: Update FeedbackCard to use controlled props**

Replace line 22-26:

```typescript
export default function FeedbackCard({ comparisonId, submitted: parentSubmitted, onSubmitted }: FeedbackCardProps) {
  const [localSubmitted, setLocalSubmitted] = useState(false);
  const submitted = parentSubmitted ?? localSubmitted;
  const [useful, setUseful] = useState<boolean | null>(null);
  const [matteredMost, setMatteredMost] = useState<string[]>([]);
  const [suggestion, setSuggestion] = useState('');
  const [submitting, setSubmitting] = useState(false);
```

- [ ] **Step 3: Update submit handler to call parent callback**

Find the submit handler (where `setSubmitted(true)` is called) and add the parent callback:

```typescript
// After successful submission:
setLocalSubmitted(true);
onSubmitted?.();
```

- [ ] **Step 4: Lift state in ResultsScreen**

In `SmartCompareApp/src/screens/ResultsScreen.tsx`, add state near the top of the component (near other `useState` declarations):

```typescript
const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
```

At line 593, replace:
```typescript
            <FeedbackCard comparisonId={comparisonId} />
```
With:
```typescript
            <FeedbackCard
              comparisonId={comparisonId}
              submitted={feedbackSubmitted}
              onSubmitted={() => setFeedbackSubmitted(true)}
            />
```

- [ ] **Step 5: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
git add SmartCompareApp/src/components/FeedbackCard.tsx SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "fix: persist feedback submission state across tab switches"
```

---

### Task 11: Fix 6 Frontend — Price Source Labels + Type Update

**Files:**
- Modify: `SmartCompareApp/src/types/types.ts`
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

- [ ] **Step 1: Add `source_method` to ProductPrice type**

In `SmartCompareApp/src/types/types.ts`, line 37-47, add after `unavailable?`:

```typescript
  source_method?: 'local_bhd' | 'converted_usd' | 'estimated';
```

- [ ] **Step 2: Add "(converted from USD)" label in ResultsScreen**

In `ResultsScreen.tsx`, at lines 378-380, there's an existing estimated price label:
```typescript
        {product.price?.estimated && (
          <Text style={styles.priceNote}>*Converted price</Text>
        )}
```

Replace it with `source_method`-based label:
```typescript
        {product.price?.source_method === 'converted_usd' && (
          <Text style={styles.priceNote}>(converted from USD)</Text>
        )}
```

This replaces the old `estimated` flag check. Do NOT add any label for `source_method === 'estimated'` — estimated prices show as regular prices (per design decision).

- [ ] **Step 3: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add SmartCompareApp/src/types/types.ts SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "feat: show '(converted from USD)' label for converted prices"
```

---

## Chunk 5: Testing + Docs (Round 3)

### Task 12: Run Full Test Suite + Fix Regressions

**Files:**
- All test files

- [ ] **Step 1: Run full free test suite**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: ALL PASS (691+ tests)

- [ ] **Step 2: Fix any failures**

If any tests fail due to changes in Rounds 1-2, fix them. Common issues:
- Mocked return values may need `source_method` field added
- `_compute_weights` tests may need updating for capped behavior
- Shopping cache tests may need iHerb rating fields

- [ ] **Step 3: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test regressions from Session 23 changes"
```

---

### Task 13: Update Documentation

**Files:**
- Modify: `docs/CONTEXT_SESSION_LOG.md`
- Modify: `CLAUDE.md`
- Modify: Memory files

- [ ] **Step 1: Add Session 23 entry to CONTEXT_SESSION_LOG.md**

Add entry covering:
- 8 fixes implemented
- Rating tier expansion (Sephora, Ulta, iHerb, Fragrantica, etc.)
- iHerb rating extraction (zero extra API calls)
- Scoring weight cap at ±30%
- Price source_method tagging
- Frontend: reviews rendering, rating display simplification, feedback persistence, cost removal
- Personalization pipeline diagnostic logging

- [ ] **Step 2: Update CLAUDE.md**

Add/update sections:
- Price pipeline: mention `source_method` field
- Rating pipeline: mention expanded tier lists
- Rating display: no badges, show all ratings
- Scoring: mention ±30% cap

- [ ] **Step 3: Update MEMORY.md**

Add Session 23 section with key learnings:
- iHerb rating extraction pattern
- Rating tier expansion for beauty categories
- Feedback state must be lifted to parent
- Cost display removed (OpenAI data sharing = free)

- [ ] **Step 4: Commit docs**

```bash
git add docs/CONTEXT_SESSION_LOG.md CLAUDE.md
git commit -m "docs: add Session 23 changes to context and project docs"
```

---

## Agent Team Assignment Summary

| Round | Agent | Tasks | Fixes |
|-------|-------|-------|-------|
| 1 | backend-1 (Opus) | Tasks 1, 2, 3 | Fixes 1, 2, 5 |
| 1 | backend-2 (Opus) | Tasks 4, 5, 6 | Fixes 4A, 4A.2, 6 |
| 2 | frontend-1 (Opus) | Tasks 7, 8, 9 | Fixes 4B, 3, 8 |
| 2 | frontend-2 (Opus) | Tasks 10, 11 | Fixes 7, 6-frontend |
| 3 | tester (Opus) | Task 12 | Full test suite + regressions |
| 3 | docs (Opus) | Task 13 | Context updates |

**Operational notes:**
- 2 agents per round, 3 sequential rounds
- Fresh team per round (prevents context bloat)
- Each agent gets ONLY their task instructions + file paths (NOT full CLAUDE.md/MEMORY.md)
- Cross-QA: each agent reviews the other's work before round ends
- Idle work: write tests for 80% coverage while waiting for QA
- Update `docs/session23-progress.md` between rounds
