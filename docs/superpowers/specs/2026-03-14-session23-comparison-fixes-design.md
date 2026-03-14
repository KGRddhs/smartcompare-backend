# Session 23: Comparison Results Fixes — Design Spec

**Date:** 2026-03-14
**Issues:** 8 fixes affecting comparison quality for supplements (and likely other categories)

---

## Issues Summary

| # | Issue | Severity | Area |
|---|-------|----------|------|
| 1 | Personalization not applied ("Default weights applied" despite being logged in with prefs) | High | Backend pipeline / DB |
| 2 | Scoring weights too aggressive when personalization IS applied | Medium | scoring_service.py |
| 3 | Reviews tab shows "Reviews not available" when review data exists | High | Frontend (ResultsScreen.tsx) |
| 4 | Unverified ratings (GPT aggregate) hidden instead of shown with label | Medium | Frontend + Backend |
| 5 | Rating source links missing for pharmacy/unknown retailers | Medium | Backend (structured_comparison_service.py) |
| 6 | Supplement prices inconsistent (local BHD vs USD conversion) | High | Backend price pipeline |
| 7 | Feedback card reappears after tab switch | Low | Frontend (FeedbackCard state) |
| 8 | Cost display removed | Low | Frontend (ResultsScreen.tsx) |

---

## Fix 1: Personalization Pipeline — Diagnostic + Defensive Fix

**Problem:** User is logged in with preferences set, but response shows "Default weights applied."

**Investigation:** The code pipeline is correct — `text_routes.py` → `compare_from_text()` → `compute_scores(preferences=...)` all pass preferences. The issue is one of:
- `get_user_preferences()` returning `{"success": False}` due to Supabase error (silently caught)
- `preferences_completed` is `false` in DB despite user completing onboarding
- Auth token valid but user ID lookup in `public.users` returns no preferences row

**Fix:**
1. Add `logger.warning()` in `text_routes.py` (all 3 endpoints) when authenticated user has `user_prefs = None`:
   ```python
   if user and not user_prefs:
       logger.warning(f"Authenticated user {user['id']} has no preferences loaded. "
                      f"prefs_result: {prefs_result}")
   ```
2. In `get_user_preferences()` (`auth_service.py`): add `logger.error()` in the exception handler (currently returns `{"success": False}` silently)
3. **Defensive fix:** In `text_routes.py`, if `user_prefs` is `None` but user is authenticated, still pass `user_preferences=None` (current behavior) BUT log the raw `prefs_result` so we can diagnose from Railway logs
4. **This is diagnostic-only.** The actual root cause will be identified from production logs after deploy. A follow-up fix will address the DB/auth issue once the logs reveal the cause.

**Files:** `app/api/text_routes.py`, `app/services/auth_service.py`

---

## Fix 2: Cap Personalization Weight Shifts at ±30%

**Problem:** When personalization IS working, priority deltas stack without bounds. Multiple priorities can shift dimensions aggressively, making personalization feel like a replacement for objective data rather than an enhancement.

**Fix in `scoring_service.py` `_compute_weights()`, replacing lines 152-154 (the existing `max(0.0, ...)` clamp):**

```python
# Cap each dimension's shift to ±30% of its default weight
# This replaces the existing clamp at line 152-154
MAX_SHIFT_RATIO = 0.30
for dim in weights:
    default_val = DEFAULT_WEIGHTS.get(dim, 0)
    max_val = default_val * (1 + MAX_SHIFT_RATIO)
    min_val = default_val * (1 - MAX_SHIFT_RATIO)
    # Also floor at 0 (a dimension can't have negative weight)
    weights[dim] = max(0.0, min(max_val, max(min_val, weights[dim])))

# Then renormalize to sum to 1.0 (existing lines 157-163 stay as-is)
```

**Note:** The cap is applied BEFORE renormalization. After renormalization, relative ratios may shift slightly beyond 30%, but the absolute weight values going into normalization are bounded. This is intentional — renormalization preserves the ratio relationships while ensuring weights sum to 1.0.

**Files:** `app/services/scoring_service.py`

---

## Fix 3: Reviews Tab — Fix Empty State Detection + Add Review Content Rendering

**Problem:** Frontend `hasAnyReviews` (line 445-447 of `ResultsScreen.tsx`) only checks `p.pros`, `p.cons`, `p.rating`. Supplements often have `reviews.common_praises/complaints` but no top-level `pros/cons`, causing a false empty state.

**Fix Part A — Gate check (line 445-447):**
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

**Fix Part B — Add rendering for `reviews` object fields in the Reviews tab (after the existing Pros/Cons sections, lines 472-489):**

```typescript
{/* Common Praises (from reviews object) */}
{!product.pros?.length && product.reviews?.common_praises?.length > 0 && (
    <View style={styles.prosConsSection}>
        <Text style={styles.prosTitle}>Praised For</Text>
        {product.reviews.common_praises.map((praise, i) => (
            <Text key={i} style={styles.proItem}>• {praise}</Text>
        ))}
    </View>
)}

{/* Common Complaints (from reviews object) */}
{!product.cons?.length && product.reviews?.common_complaints?.length > 0 && (
    <View style={styles.prosConsSection}>
        <Text style={styles.consTitle}>Criticized For</Text>
        {product.reviews.common_complaints.map((complaint, i) => (
            <Text key={i} style={styles.conItem}>• {complaint}</Text>
        ))}
    </View>
)}

{/* Detailed praises with quotes */}
{product.reviews?.detailed_praises?.length > 0 && (
    <View style={styles.prosConsSection}>
        <Text style={styles.prosTitle}>What Users Love</Text>
        {product.reviews.detailed_praises.map((praise, i) => (
            <View key={i}>
                <Text style={styles.proItem}>• {praise.text}</Text>
                {praise.quote && (
                    <Text style={styles.quoteText}>"{praise.quote}"</Text>
                )}
            </View>
        ))}
    </View>
)}
```

**Logic:** Show `common_praises/complaints` only when `pros/cons` are empty (avoid duplication). Show `detailed_praises` always (they contain richer content with quotes).

**Files:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

---

## Fix 4: Show Unverified Ratings + iHerb Rating Extraction

**Problem:** `RatingDisplay` component (line 300) hides ratings when `!rating_verified || !rating_source?.url`. This hides useful GPT-aggregated ratings entirely. For supplements specifically, Serper Shopping returns ZERO results, so the rating pipeline always falls to the GPT aggregate fallback — even though iHerb pages (already scraped for prices in Phase 1) have real ratings and review counts.

### Fix 4A — Extract ratings from iHerb during existing scrape (ZERO extra API calls)

**Problem:** `_fetch_iherb_price()` (line ~1120) already scrapes iHerb search pages using `curl_cffi`. It extracts `data-ga-brand-name`, `data-ga-discount-price`, `title`, `href` — but ignores any rating data on the page.

**Fix in `structured_comparison_service.py`:**
1. In `_fetch_iherb_price()`, also look for rating attributes on the iHerb search result cards (e.g., `data-ga-rating`, star rating elements, or rating text patterns)
2. If iHerb search cards don't have inline ratings, fetch the individual product page URL (already available from `href`) and parse for JSON-LD `Product` schema or star rating markup — similar to the existing `_try_pharmacy_urls()` pattern (line ~1393)
3. Return rating data alongside price:
   ```python
   return {
       "amount": best["price"],
       "currency": currency,
       "retailer": "iHerb",
       "url": best["url"],
       "iherb_rating": extracted_rating,        # NEW (float, e.g., 4.7)
       "iherb_review_count": extracted_count,    # NEW (int, e.g., 12345)
   }
   ```
4. Store the rating in `_shopping_items_cache` so `_get_verified_rating()` can find it:
   ```python
   self._shopping_items_cache[product_name] = [{
       "source": "iHerb",
       "rating": extracted_rating,
       "ratingCount": extracted_count,
       "link": best["url"],
       "title": best["title"],
   }]
   ```
5. `_get_verified_rating()` (line ~1934) already checks `_shopping_items_cache` first (Step 1, line ~1943). With iHerb data cached, it will find a Tier 1 rating immediately — no Serper Shopping call needed.

**Result for supplements:**
- **Before:** `rating_verified: false`, confidence: `"low"`, extract_method: `"gpt_review_aggregate"`
- **After:** `rating_verified: true`, confidence: `"high"`, source: `"iHerb"`, with real review count and clickable link

**Note:** If iHerb page doesn't have ratings (rare), fall through to GPT aggregate as before. Also, for non-iHerb brands (HealthAid, Vitabiotics), pharmacy pages (bn.boots.com) may also have ratings — the existing `_try_pharmacy_urls()` JSON-LD parser could extract `aggregateRating` from the `Product` schema. Add this as a secondary fallback.

### Fix 4A.2 — Expand Rating Tier Lists + Selective Scraping for Beauty/Fragrance

**Problem:** The rating pipeline is identical for ALL categories — no category-specific logic. Beauty categories (makeup, skincare, haircare, fragrances) face the same unverified-rating problem as supplements because:
- Serper Shopping (BH) returns sparse/zero results for beauty products
- US Shopping fallback often returns results from Sephora, Ulta, Fragrantica — but these are NOT in RATING_TIER_1 or TIER_2, so they're classified as Tier 3 (unverified)

**Fix Part 1 — Add missing retailers to tier lists (`structured_comparison_service.py`):**
```python
RATING_TIER_1 = [
    # ... existing ...
    "iherb",          # THE supplement retailer
    "sephora",        # Major beauty retailer
    "ulta",           # Major beauty retailer
]

RATING_TIER_2 = [
    # ... existing ...
    "fragrantica",    # Major fragrance review site
    "sally beauty",   # Haircare/beauty retailer
    "bath & body",    # Personal care
    "lookfantastic",  # Beauty retailer (UK/GCC)
    "nykaa",          # Beauty retailer (popular in GCC)
    "beautybay",      # Beauty retailer
    "boots",          # Pharmacy + beauty (BH presence)
]
```

This is a **zero-code-change** fix — just adding strings to existing lists. The US Shopping fallback (Step 2) already searches these retailers; they just weren't being classified at the right tier.

**Fix Part 2 — Selective scraping for Sephora and Fragrantica (future-proofing):**

For products where US Shopping returns Sephora/Fragrantica URLs but no inline rating:
1. Fetch the product page URL (similar to `_try_pharmacy_urls()` pattern)
2. Parse JSON-LD `Product` schema for `aggregateRating` (Sephora uses JSON-LD)
3. Parse Fragrantica page for rating markup (structured data)
4. Cache in `_shopping_items_cache` for reuse

**Scope for this session:** Implement Part 1 (tier list expansion) fully. Part 2 (selective scraping) only for iHerb (Fix 4A) and pharmacy JSON-LD `aggregateRating`. Sephora/Fragrantica scraping is deferred to a future session if tier list expansion doesn't achieve >70% verified rates for beauty categories.

### Fix 4B — Frontend: Show ALL ratings (no badges, no verified/unverified distinction)

**Design decision:** No "Verified" / "Estimated" / "Unverified" badges in the UI. The distinction between rating sources and confidence levels is covered in the Terms & Conditions. The UI simply shows any rating that exists, with the source name and a clickable link when available.

**Fix Part A — Update `RatingSource` type in `types.ts` (line 8-14):**
```typescript
export interface RatingSource {
    name: string;
    url: string | null;  // Changed from `string` — null when no source link available
    retrieved_at?: string;
    extract_method?: 'google_shopping' | 'json_ld' | 'microdata' | 'meta_tags' | 'css_selector' | 'gpt_review_aggregate';
    confidence?: 'high' | 'medium' | 'low' | 'expert';
}
```

**Fix Part B — Simplify `RatingDisplay` logic (replace lines 299-353):**
```typescript
const RatingDisplay = ({ product }: { product: Product }) => {
    const { rating, review_count, rating_source } = product;

    // No rating at all
    if (rating === null || rating === undefined) {
        return (
            <View style={styles.ratingContainer}>
                <Text style={styles.noRatingText}>No rating available</Text>
            </View>
        );
    }

    // Has rating — show it with source name + link if available
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

    // Wrap in TouchableOpacity only if there's a clickable link
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

**Key change:** Removed `!rating_verified` and `!rating_source?.url` from the gate condition. Any non-null rating is displayed. No badges. Source name shown as plain text, clickable only when URL exists.

**Files:** `SmartCompareApp/src/screens/ResultsScreen.tsx`, `SmartCompareApp/src/types/types.ts`

---

## Fix 5: Add Pharmacy + iHerb Domains to Retailer URL Map

**Problem:** `_build_retailer_url()` returns `None` for pharmacy retailers. They exist in `PHARMACY_DOMAINS` but NOT in `RETAILER_SEARCH_URLS`.

**Fix in `structured_comparison_service.py` — add to `RETAILER_SEARCH_URLS` dict:**
```python
"boots": "https://www.bn.boots.com/search?q={query}",
"al deerah": "https://aldeerahpharmacy.com/catalogsearch/result/?q={query}",
"iherb": "https://www.iherb.com/search?kw={query}",
```

**Note:** `bolo.bh` is EXCLUDED because it's a Vue.js SPA — search URLs don't work without client-side JS rendering. The CLAUDE.md/MEMORY.md document this: "bolo.bh NOT indexed by Google (Vue.js SPA)." Adding a broken URL is worse than no URL.

**Also:** When URL is truly unavailable (no Serper link, no template match), Fix 4's `RatingDisplay` already handles showing ratings without a link (the rating shows with badge but no link icon/clickability).

**Files:** `app/services/structured_comparison_service.py`

---

## Fix 6: BHD-First Price Strategy with Conversion Fallback

**Problem:** Supplement prices mix local BHD prices with USD→BHD conversions. HealthAid at 2.07 BHD (local Boots) vs NOW at 4.388 BHD (converted from iHerb USD) makes comparisons misleading.

**Current conversion logic location:** `_convert_gpt_price_currency()` in `structured_comparison_service.py` uses `CURRENCY_TO_BHD` map (line 2406: `"USD": 0.377`).

**Fix Part A — Add `source_method` field to price objects:**

Every price construction point in `structured_comparison_service.py` must tag the source:
- **`local_bhd`:** Price found directly in BHD (Serper Shopping `gl=bh`, pharmacy JSON-LD from bn.boots.com/bolo.bh, direct BHD extraction)
- **`converted_usd`:** Price originally in USD, converted via `CURRENCY_TO_BHD["USD"]` (iHerb scrape, US Serper Shopping, GPT extraction from USD sources)

Specific code paths:
- `_fetch_iherb_price()` returns USD → after conversion = `"converted_usd"`
- `_fetch_pharmacy_price()` returns BHD (JSON-LD from .bh domains) = `"local_bhd"`
- Serper Shopping `gl=bh` with BHD currency = `"local_bhd"`
- Serper Shopping without region, USD detected = `"converted_usd"`
- GPT Tier 2 extraction: depends on snippet currency → tag accordingly
- GPT Tier 3 training data: = `"estimated"` (new third value)

**Fix Part B — Add `price_method_mismatch` to top-level response:**
```python
# In compare_from_text(), after price extraction for both products:
methods = [p["price"].get("source_method") for p in product_data if p.get("price")]
unique_methods = set(m for m in methods if m)  # exclude None
result["price_method_mismatch"] = len(unique_methods) > 1
```

**Fix Part C — Update TypeScript `ProductPrice` interface (`types.ts` line 37-47):**
```typescript
export interface ProductPrice {
    amount: number | null;
    currency: string;
    retailer?: string;
    url?: string;
    in_stock?: boolean;
    estimated?: boolean;
    confidence?: number;
    note?: string;
    unavailable?: boolean;
    source_method?: 'local_bhd' | 'converted_usd' | 'estimated';  // NEW
}
```

**Fix Part D — Frontend label (`ResultsScreen.tsx`):**
When `product.price.source_method === 'converted_usd'`, show a small gray text "(converted from USD)" below the price. When `source_method === 'estimated'`, do NOT show any label — estimated prices are acceptable as a last resort but should not be flagged to the user. The `estimated` field stays in the backend for internal tracking only.

Also remove any existing UI display of the `estimated` flag (if the frontend currently shows "Estimated price" or similar).

**Conversion rate:** Keep existing `0.377` in `CURRENCY_TO_BHD` (line 2406). This matches the Central Bank of Bahrain peg rate.

**Files:** `app/services/structured_comparison_service.py`, `SmartCompareApp/src/types/types.ts`, `SmartCompareApp/src/screens/ResultsScreen.tsx`

---

## Fix 7: Feedback Card State Persistence Across Tab Switches

**Problem:** `FeedbackCard` uses local `useState` for `submitted` (line 26). Tab switching re-mounts the component, resetting state.

**Fix Part A — Update `FeedbackCardProps` interface (`FeedbackCard.tsx` line 18-20):**
```typescript
interface FeedbackCardProps {
    comparisonId?: string;
    submitted?: boolean;       // NEW: controlled from parent
    onSubmitted?: () => void;  // NEW: callback to parent
}
```

**Fix Part B — Update FeedbackCard to use props when provided:**
```typescript
export default function FeedbackCard({ comparisonId, submitted: parentSubmitted, onSubmitted }: FeedbackCardProps) {
    const [localSubmitted, setLocalSubmitted] = useState(false);
    const submitted = parentSubmitted ?? localSubmitted;
    // ... existing logic, but when submission succeeds:
    // setLocalSubmitted(true);
    // onSubmitted?.();
```

**Fix Part C — In `ResultsScreen.tsx`, lift state:**
```typescript
const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

// In Overview tab rendering:
<FeedbackCard
    comparisonId={comparisonId}
    submitted={feedbackSubmitted}
    onSubmitted={() => setFeedbackSubmitted(true)}
/>
```

**Files:** `SmartCompareApp/src/components/FeedbackCard.tsx`, `SmartCompareApp/src/screens/ResultsScreen.tsx`

---

## Fix 8: Remove Cost Display from UI

**Problem:** The "$0.0249" cost shown is an internal estimate, not actual billing. Misleading for users.

**Fix:** Remove the cost display from the footer text in `ResultsScreen.tsx`. The `total_cost` field stays in the API response for admin/internal tracking — just don't render it in the UI.

Find the footer text that shows `Cost: $X.XXXX` and remove just the cost portion. Keep the timing and cache status.

**Files:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

---

## Team Execution Plan

### Operational Constraints (Pro Subscription)
- **2 agents per round, 3 sequential rounds** (proven Session 22 pattern)
- **Fresh team per round** to prevent context bloat — each round creates a NEW team
- **Minimal agent prompts** — each agent gets ONLY the specific fix instructions + file paths, NOT full CLAUDE.md/MEMORY.md (these are huge and cause 60% token usage on load)
- **Progress file** updated between rounds at `docs/session23-progress.md`
- All agents are **Opus** (not Sonnet/Haiku)
- **Cross-QA mandatory** — each agent reviews the other's work before round ends
- **Idle work** — while waiting for QA, agents write tests targeting 80% coverage on their changes

### Round 1: Backend Fixes (Agent A: backend-1, Agent B: backend-2)

**Agent A (backend-1):** Fixes 1, 2, 5
- Fix 1: Add diagnostic logging to personalization pipeline in `text_routes.py` + `auth_service.py`
- Fix 2: Cap weight shifts at ±30% in `scoring_service.py` (replace lines 152-154)
- Fix 5: Add boots/iherb/aldeerah to `RETAILER_SEARCH_URLS` (NOT bolo.bh — Vue SPA)
- Write tests: weight capping edge cases, pharmacy URL generation
- QA Agent B's price changes when done

**Agent B (backend-2):** Fix 4A (iHerb ratings + tier expansion) + Fix 6 (backend parts)
- Fix 4A: Extract ratings from iHerb scrape, cache in `_shopping_items_cache`, extract `aggregateRating` from pharmacy JSON-LD
- Fix 4A.2: Add Sephora, Ulta, iHerb to RATING_TIER_1; add Fragrantica, Sally Beauty, LookFantastic, Boots, etc. to RATING_TIER_2
- Fix 6: Tag all price construction points with `source_method: 'local_bhd' | 'converted_usd' | 'estimated'`
- Add `price_method_mismatch` flag to response
- Write tests: iHerb rating extraction, tier classification for new retailers, source method tagging, mismatch detection
- QA Agent A's scoring + URL changes when done

**End of Round 1:** Update `docs/session23-progress.md`, commit

### Round 2: Frontend Fixes (Agent C: frontend-1, Agent D: frontend-2)

**Agent C (frontend-1):** Fixes 3, 4, 8
- Fix 3: Expand `hasAnyReviews` gate + add `common_praises/complaints` rendering
- Fix 4: Rewrite `RatingDisplay` to show unverified with "Estimated" badge. Update `RatingSource` type in `types.ts`
- Fix 8: Remove cost display from footer
- Run `npx tsc --noEmit` — must pass with 0 errors
- QA Agent D's changes when done

**Agent D (frontend-2):** Fixes 7, 6-frontend
- Fix 7: Lift feedback state to ResultsScreen, update `FeedbackCardProps`
- Fix 6 frontend: Add `source_method` to `ProductPrice` type, show "(converted from USD)" label
- Run `npx tsc --noEmit` — must pass with 0 errors
- QA Agent C's changes when done

**End of Round 2:** Update `docs/session23-progress.md`, commit

### Round 3: Testing + Docs (Agent E: tester, Agent F: docs)

**Agent E (tester):**
- Run full free test suite: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
- Fix any test failures from Rounds 1-2
- Verify new tests pass and no regressions
- QA Agent F's doc updates for accuracy

**Agent F (docs):**
- Update `docs/CONTEXT_SESSION_LOG.md` with Session 23 changes
- Update `CLAUDE.md` with any architecture changes (price source_method, rating display logic)
- Update `MEMORY.md` with Session 23 learnings
- Verify all changes committed
- QA Agent E's test coverage

**End of Round 3:** Final commit, verify all passing

---

## Success Criteria

1. Reviews tab shows review data when `reviews.common_praises/complaints` exist (not just `pros/cons`)
2. Supplement ratings extracted from iHerb pages (zero extra API calls) — Tier 1
3. Non-iHerb supplement ratings extracted from pharmacy JSON-LD `aggregateRating` when available
4. Beauty category retailers (Sephora, Ulta, etc.) added to Tier 1/2 for verified ratings
5. ALL ratings shown (no badges, no verified/unverified distinction in UI — covered by T&C)
6. Rating source name + clickable link when URL available
4. Scoring weights capped at ±30% shift from defaults per dimension
5. Personalization pipeline logs diagnostic info when prefs are `None` for authenticated users
6. Pharmacy retailer links work (boots, iherb, al deerah — NOT bolo.bh)
7. Prices tagged with `source_method` (`local_bhd` / `converted_usd` / `estimated`)
8. "(converted from USD)" label shown in frontend for converted prices
9. `price_method_mismatch` flag in response when products use different price methods
10. Feedback card state persists across tab switches
11. Cost display removed from UI
12. All existing tests pass + new tests for fixes 2, 5, 6
13. `npx tsc --noEmit` passes with 0 errors

---

## Files Modified

### Backend
- `app/services/scoring_service.py` — weight capping (replace lines 152-154)
- `app/services/structured_comparison_service.py` — retailer URLs, price `source_method` tagging, `price_method_mismatch`
- `app/api/text_routes.py` — preference pipeline diagnostic logging
- `app/services/auth_service.py` — preference fetch error logging

### Frontend
- `SmartCompareApp/src/types/types.ts` — `RatingSource.url` nullable, `ProductPrice.source_method`, `RatingSource.extract_method` add `gpt_review_aggregate`
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — reviews gate + rendering, `RatingDisplay` rewrite, cost removal, price source labels, feedback state lift
- `SmartCompareApp/src/components/FeedbackCard.tsx` — accept `submitted`/`onSubmitted` props

### Tests
- `tests/test_scoring_service.py` — weight capping tests (existing file, add tests)
- `tests/test_url_quality.py` — pharmacy URL tests (existing file, add tests)
- New: `tests/test_price_source.py` — price source method tagging + mismatch detection

### Docs
- `docs/CONTEXT_SESSION_LOG.md` — Session 23 log entry
- `docs/session23-progress.md` — inter-round progress tracking (new file)
- `CLAUDE.md` — update price pipeline docs with `source_method`
- `MEMORY.md` — Session 23 learnings
