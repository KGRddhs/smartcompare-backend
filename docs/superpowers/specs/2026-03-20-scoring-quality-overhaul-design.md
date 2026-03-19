# Scoring & Quality Overhaul — Session 26

**Date:** 2026-03-20
**Status:** Revised (v2 — reviewer fixes applied)
**Scope:** Full overhaul of scoring engine, price pipeline, review quality, ratings, and verdict generation

## Problem Statement

Luxury product comparisons (Hermes cap vs LV cap, designer fashion) produce broken results:
- **Prices wrong:** Counterfeit/replica prices slip through; official brand sites (me.louisvuitton.com, hermes.com) not prioritized
- **Reviews contain garbage:** "Learn more about condition", positive points in criticisms, navigation text
- **Ratings empty:** Luxury products have no Google Shopping ratings; system shows nothing
- **Scores look fake:** Value score is naive `(spec + price) / 2`; expensive = bad; no category or tier awareness
- **Verdict is shallow:** Just "premium vs budget" with no data-backed reasoning

These issues compound: wrong prices feed wrong scores, which contradict the verdict, making the entire output feel unreliable.

## Design

### 1. Scoring Engine Overhaul

**File:** `app/services/scoring_service.py`

#### 1A. Category-Specific Weight Profiles

Replace single `DEFAULT_WEIGHTS` with per-category profiles. Rationale from Consumer Reports / RTINGS research: weight what matters most for each product type.

```python
CATEGORY_WEIGHTS = {
    "electronics":  {"price_score": 0.20, "spec_score": 0.25, "review_score": 0.20, "value_score": 0.15, "reliability_score": 0.15, "popularity_score": 0.05},
    "supplements":  {"price_score": 0.10, "spec_score": 0.15, "review_score": 0.25, "value_score": 0.15, "reliability_score": 0.30, "popularity_score": 0.05},
    "fashion":      {"price_score": 0.10, "spec_score": 0.15, "review_score": 0.25, "value_score": 0.15, "reliability_score": 0.10, "popularity_score": 0.25},
    "fragrances":   {"price_score": 0.10, "spec_score": 0.10, "review_score": 0.30, "value_score": 0.15, "reliability_score": 0.10, "popularity_score": 0.25},
    "grocery":      {"price_score": 0.25, "spec_score": 0.10, "review_score": 0.25, "value_score": 0.25, "reliability_score": 0.10, "popularity_score": 0.05},
    "makeup":       {"price_score": 0.15, "spec_score": 0.15, "review_score": 0.30, "value_score": 0.15, "reliability_score": 0.10, "popularity_score": 0.15},
    "skincare":     {"price_score": 0.15, "spec_score": 0.15, "review_score": 0.25, "value_score": 0.15, "reliability_score": 0.20, "popularity_score": 0.10},
    "haircare":     {"price_score": 0.20, "spec_score": 0.10, "review_score": 0.30, "value_score": 0.20, "reliability_score": 0.10, "popularity_score": 0.10},
    "other":        {"price_score": 0.20, "spec_score": 0.20, "review_score": 0.25, "value_score": 0.15, "reliability_score": 0.10, "popularity_score": 0.10},
}
```

- Fashion/Fragrances: popularity & reviews dominate (brand perception drives purchases)
- Supplements: reliability is king (safety, certifications)
- Grocery: value & price matter most (daily purchases)
- Electronics: specs & reliability balanced (performance + longevity)
- Personalization still applies on top (capped at 30% shift via `MAX_WEIGHT_SHIFT_RATIO`)

**Implementation:** In `compute_scores()`, look up `CATEGORY_WEIGHTS[category]` instead of `DEFAULT_WEIGHTS`. Fall back to `CATEGORY_WEIGHTS["other"]` for unknown categories. Delete `DEFAULT_WEIGHTS` — `CATEGORY_WEIGHTS["other"]` is the universal fallback.

**Personalization cap fix:** `MAX_WEIGHT_SHIFT_RATIO` must be calculated relative to the active category weights, NOT the old `DEFAULT_WEIGHTS`. In `_personalize_weights()`, the base for computing the ±30% shift cap must be `CATEGORY_WEIGHTS[category][dim]`, not a global default. Example: fashion `price_score=0.10`, so max shift = ±0.03 (30% of 0.10), not ±0.075 (30% of the old default 0.25).

#### 1B. Price Tier Detection

New function in `scoring_service.py`:

```python
PRICE_TIERS = {
    "budget":    (0, 11),       # < BHD 11 (~$30)
    "mid":       (11, 57),      # BHD 11-57 (~$30-150)
    "premium":   (57, 189),     # BHD 57-189 (~$150-500)
    "luxury":    (189, float("inf")),  # BHD 189+ (~$500+)
}

def _detect_price_tier(self, price_bhd: float) -> str:
    for tier, (low, high) in self.PRICE_TIERS.items():
        if low <= price_bhd < high:
            return tier
    return "luxury"

def _is_cross_tier(self, tiers: list[str]) -> bool:
    return len(set(tiers)) > 1
```

#### 1C. Value Score Redesign

Replace naive average with tier-aware formula:

```python
TIER_EXPECTATIONS = {"budget": 0.6, "mid": 0.7, "premium": 0.8, "luxury": 0.85}

def _compute_value_score(self, spec_score, price_score, price_tier, is_cross_tier):
    if spec_score == MISSING_SCORE and price_score == MISSING_SCORE:
        return MISSING_SCORE

    # Handle partial missing data
    if spec_score == MISSING_SCORE and price_score != MISSING_SCORE:
        return price_score  # Only price data available
    if price_score == MISSING_SCORE and spec_score != MISSING_SCORE:
        return spec_score  # Only spec data available

    if is_cross_tier:
        # Cross-tier: how well does each product deliver for its tier?
        expected = self.TIER_EXPECTATIONS[price_tier] * 100
        delivery = spec_score
        value = 50 + (delivery - expected) * 0.8  # Centered at 50
        return round(max(0, min(100, value)), 1)
    else:
        # Same-tier: spec quality weighted heavier than raw price
        return round(spec_score * 0.6 + price_score * 0.4, 1)
```

Hermes cap delivering luxury quality → ~65 value (meeting tier expectations).
Local cap delivering mid quality at budget price → ~70 value (exceeding tier expectations).
Neither gets absurd scores.

#### 1D. Spec Coverage Penalty — Category-Aware

Replace fixed 0.5 threshold:

```python
CATEGORY_MIN_COVERAGE = {
    "electronics": 0.5,
    "fashion":     0.3,
    "fragrances":  0.3,
    "supplements": 0.4,
    "makeup":      0.35,
    "skincare":    0.35,
    "haircare":    0.35,
    "grocery":     0.3,
    "other":       0.3,
}
```

In `_score_specs()`, use `CATEGORY_MIN_COVERAGE[category]` instead of hardcoded 0.5.

#### 1E. Dimension Winners Computation

New method in `scoring_service.py`, called after `compute_scores()`:

```python
def compute_dimension_winners(self, scoring_result: dict, product_names: list[str]) -> dict:
    scores = scoring_result["scores"]
    dimensions = ["price_score", "spec_score", "review_score", "value_score", "reliability_score", "popularity_score"]
    winners = {}
    for dim in dimensions:
        s0 = scores[0]["breakdown"].get(dim, 0)
        s1 = scores[1]["breakdown"].get(dim, 0)
        margin = abs(s0 - s1)
        # Both missing = N/A, not a tie
        if s0 == MISSING_SCORE and s1 == MISSING_SCORE:
            winners[dim] = {"winner": "N/A", "margin": None}
            continue
        if margin < 2.0:  # < 2 point difference = tie
            winners[dim] = {"winner": "tie", "margin": 0}
        elif s0 > s1:
            winners[dim] = {"winner": product_names[0], "margin": round(margin, 1)}
        else:
            winners[dim] = {"winner": product_names[1], "margin": round(margin, 1)}
    return winners
```

Added to the `scoring_result` dict before it's returned from `compute_scores()`.

---

### 2. Price Pipeline Fixes

**File:** `app/services/structured_comparison_service.py`

#### 2A. Counterfeit Keyword Filter

```python
COUNTERFEIT_KEYWORDS = {
    "replica", "fake", "dupe", "inspired by", "inspired",
    "knockoff", "knock-off", "imitation", "copy",
    "look alike", "lookalike", "designer inspired",
    "unbranded", "generic", "homage", "alternative",
    "pre-owned", "used", "vintage", "secondhand", "second hand",
}

@staticmethod
def _is_counterfeit_listing(title: str) -> bool:
    title_lower = title.lower()
    return any(kw in title_lower for kw in StructuredComparisonService.COUNTERFEIT_KEYWORDS)
```

Applied in:
- `_extract_price_from_shopping()` — add as **first filter inside the shopping items loop** (before accessory check at ~line 1694). If `_is_counterfeit_listing(title)` returns True, `continue` to skip the item.
- `_strict_title_match()` — add counterfeit check as first condition: if `_is_counterfeit_listing(title)` returns True, return False immediately (no match).

#### 2B. Official Domain Targeted Search for Luxury

When `_is_luxury_brand()` is True AND Tier 1 (Shopping) produces no credible price (retailer_score < 0.8):

**Reuse existing `OFFICIAL_BRAND_DOMAINS`** (already has 25+ domains). No new regional mapping needed — Serper handles regional routing via the existing region parameter.

**New helper** `_get_official_domain(product_name: str) -> Optional[str]`:
- Uses same matching logic as existing `_is_luxury_brand()` (substring match against `LUXURY_BRAND_KEYWORDS`)
- When a keyword matches, looks up the corresponding domain from `OFFICIAL_BRAND_DOMAINS`
- Returns first matching domain or None

**Integration point:** In `_get_price()` method (~line 890-920), between the Tier 1 Shopping extraction and the Tier 2 GPT organic extraction:

```python
# After Tier 1 fails or is rejected by sanity check (~line 920):
if not price and self._is_luxury_brand(full_name):
    official_domain = self._get_official_domain(full_name)
    if official_domain:
        # Targeted site search (1 Serper credit)
        official_results = await search_web(f"{full_name} site:{official_domain}")
        if official_results.get("organic"):
            # Reuse existing extract_price() from extraction_service.py
            price, usage = await extract_price(
                full_name, official_results["organic"], region_info
            )
            if price:
                price["source_method"] = "converted_usd"  # Keep existing taxonomy
                price["retailer"] = official_domain
                price["retailer_score"] = 1.0  # Official domain = max trust
                # Skip Tier 2 organic — we have official price
```

**source_method stays in existing taxonomy** (`local_bhd` / `converted_usd` / `estimated`). No new `official_site` value — instead, the `retailer` field and `retailer_score=1.0` indicate official source. This avoids breaking `price_method_mismatch` logic.

**Error handling:** If official site search returns results but GPT price extraction fails, fall through to Tier 2 (existing organic GPT extraction) normally.

Cost: +$0.001 per luxury comparison (1 Serper call) only when Tier 1 fails. Non-luxury unchanged.

#### 2C. Smarter Sanity Thresholds for Luxury

Two changes:
1. **Skip sanity check when retailer_score == 1.0** (official brand domains). If the price comes from hermes.com, it's the real price — don't second-guess it with a GPT estimate.
2. **Tighter thresholds for non-official luxury sources:**

```python
if price.get("retailer_score", 0) >= 1.0:
    # Official domain — trust it, skip sanity check
    pass
elif self._is_luxury_brand(full_name):
    high_threshold = 1.8   # was 2.0 — slightly tighter but not so tight it rejects authentic retailers
    low_threshold = 0.6    # was 0.5 — counterfeits are typically 60%+ cheaper
else:
    high_threshold = 2.0
    low_threshold = 0.5
```

#### 2D. Price Extraction Prompt Hardening

Add to the GPT price extraction prompt in `extraction_service.py`:

```
REJECT these sources entirely:
- Reseller/marketplace listings (eBay individual sellers, Poshmark, Mercari, Vestiaire)
- Known counterfeit platforms (DHgate, AliExpress, Temu, Wish)
- Listings with "pre-owned", "used", "vintage" unless the query explicitly asks for used
- Any listing where the price is <40% of typical retail for luxury brands
- Listings with "replica", "fake", "dupe", "inspired" in the title or URL
```

---

### 3. Review & Rating Fixes

**Files:** `extraction_service.py`, `structured_comparison_service.py`

#### 3A. GPT Review Prompt Hardening

Add to `REVIEWS_EXTRACTION_PROMPT` in `extraction_service.py`:

```
NEVER include these in praise OR complaints:
- Navigation text: "learn more", "see details", "click here", "read more", "shop now"
- Boilerplate: "free shipping", "easy returns", "available in stores"
- Condition disclaimers: "learn more about condition", "see seller notes"
- Marketing copy: "best seller", "limited edition" (unless substantiated by a review)
- Generic filler: sentences under 8 words with no specific product claim

Each praise/complaint MUST be a specific, substantive claim about the product itself.
BAD: "Learn more about condition"
BAD: "Great product"
GOOD: "The leather feels premium and holds its shape well [snippet_3]"
GOOD: "Stitching came loose after 2 months of daily wear [snippet_5]"

For complaints specifically:
- Only include NEGATIVE observations. A positive statement is NOT a criticism.
- If a snippet mentions both positive and negative aspects, extract ONLY the negative part.
```

#### 3B. Backend Post-Processing Filter

New function `_clean_review_content()` in `structured_comparison_service.py` (sibling to existing `_clean_review_citations()`):

```python
GARBAGE_PATTERNS = [
    r"learn more about",
    r"see (full |more )?details",
    r"click (here|to)",
    r"read more",
    r"shop now",
    r"free (shipping|delivery|returns)",
    r"add to (cart|bag|wishlist)",
    r"available (in|at) (stores|select)",
    r"sign up for",
    r"join (our|the) (newsletter|waitlist)",
]

NEGATIVE_INDICATORS = {"bad", "poor", "disappointing", "issue", "problem", "broke", "broken",
    "flimsy", "cheap", "overpriced", "uncomfortable", "fragile", "peeling",
    "fading", "cracking", "defect", "flaw", "mediocre", "underwhelming",
    "lacking", "missing", "difficult", "annoying", "frustrating", "worse", "worst"}

POSITIVE_INDICATORS = {"great", "excellent", "premium", "beautiful", "perfect", "love",
    "amazing", "wonderful", "fantastic", "superb", "outstanding", "impressive",
    "comfortable", "luxurious", "elegant", "sturdy", "durable", "quality"}

def _clean_review_content(self, reviews: dict) -> dict:
    for section in ["common_praises", "detailed_praises", "common_complaints", "detailed_complaints"]:
        items = reviews.get(section, [])
        if not items:
            continue
        cleaned = []
        for item in items:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            # Skip garbage patterns
            if any(re.search(p, text, re.IGNORECASE) for p in GARBAGE_PATTERNS):
                continue
            # Skip too-short items
            if len(text.split()) < 8:
                continue
            # Sentiment alignment: positive text in complaints section → remove
            if "complaint" in section:
                words = set(text.lower().split())
                has_negative = bool(words & NEGATIVE_INDICATORS)
                has_positive = bool(words & POSITIVE_INDICATORS)
                if has_positive and not has_negative:
                    continue  # Positive statement misclassified as complaint
            cleaned.append(item)
        reviews[section] = cleaned
    return reviews
```

**Call order:** Called BEFORE `_clean_review_citations()`. Logical flow:
1. `_get_reviews()` — raw GPT extraction
2. `_clean_review_content()` — remove garbage/short/misclassified items (new)
3. `_clean_review_citations()` — replace [snippet_N] with domain names (existing)

Applied in both streaming and non-streaming paths, at the same point where `_clean_review_citations()` is currently called (~line 778 in `_fetch_product_data()`).

#### 3C. Derived Ratings When No Real Ratings Exist

**Timing:** After scoring is computed (line ~282) but before response assembly (line ~333). This is a display-only value — it does NOT feed back into the scoring engine. The scoring engine already computed `review_score` with whatever data was available (possibly MISSING_SCORE). The derived rating is purely for the frontend to show something instead of empty.

```python
def _derive_rating_from_scores(self, overall_score: float) -> float:
    """Derive a display rating from the overall score when no real ratings exist.
    Maps overall score (0-100) to a 2.5-4.8 star scale.
    Does NOT feed back into scoring — display only."""
    # Use overall score (already computed from all dimensions)
    # Range 2.5-4.8: allows low scores for bad products, but caps below 5.0
    rating = 2.5 + (overall_score / 100) * 2.3
    return round(min(rating, 4.8), 1)
```

**Integration point:** In `compare_from_text()`, after `compute_scores()` returns at ~line 282, loop products:

```python
for i, product in enumerate(products):
    if product.get("rating") is None:
        overall = scoring_result["scores"][i]["overall"]
        product["rating"] = self._derive_rating_from_scores(overall)
        product["rating_source"] = {
            "name": "Product analysis",
            "url": None,
            "extract_method": "score_derived",
        }
```

Per user requirement — shown same as real ratings, no "estimated" label in the UI. The `extract_method: "score_derived"` is backend metadata only (not displayed).

#### 3D. Verdict Prompt Overhaul

Replace the current scoring context injection in `extraction_service.py` with a structured, scoring-aware prompt:

```
## Scoring Context

Product A: {name}
  Overall: {score}/100 | Price: {price_score} | Specs: {spec_score} | Reviews: {review_score} | Value: {value_score} | Reliability: {reliability_score} | Popularity: {popularity_score}
  Price tier: {tier} | Category: {category}

Product B: {name}
  Overall: {score}/100 | Price: {price_score} | Specs: {spec_score} | Reviews: {review_score} | Value: {value_score} | Reliability: {reliability_score} | Popularity: {popularity_score}
  Price tier: {tier} | Category: {category}

Cross-tier comparison: {yes/no}
Dimension winners: {dim_winners_summary}
Category weight profile: {weights_summary}

## Verdict Requirements

1. RECOMMENDATION: State the winner with the score margin. Explain WHO should buy which product and WHY based on the dimension scores.
2. KEY DIFFERENCES: 3-5 data-backed differences. Reference actual specs, prices, and review findings. Cite which dimension each difference relates to.
3. VALUE ANALYSIS: Explain the value proposition of each product. If cross-tier, acknowledge that each serves a different market segment — do NOT penalize luxury for being expensive.
4. BEST FOR: One sentence per product describing the ideal buyer.

Your verdict MUST be consistent with the scores. If Product A wins on reviews, your text must reflect that. Do NOT contradict the scoring data.
If this is a cross-tier comparison, frame it as "different products for different needs" rather than "expensive vs cheap."
```

Also update `build_scores_summary()` in `scoring_service.py` to include tier and dimension winner data.

---

### 4. API Response Changes

**File:** `app/services/structured_comparison_service.py` (response assembly, lines 333-358)

#### 4A. New Fields in scoring Object

```json
{
  "scoring": {
    "scores": [...],
    "winner_index": 0,
    "win_margin": 12.5,
    "scoring_method": "category_weighted_v2",
    "dimension_winners": {
      "price_score":      {"winner": "Local Brand Cap", "margin": 60},
      "spec_score":       {"winner": "Hermes Nevada Cap", "margin": 12},
      "review_score":     {"winner": "Hermes Nevada Cap", "margin": 18},
      "value_score":      {"winner": "Local Brand Cap", "margin": 5},
      "reliability_score": {"winner": "tie", "margin": 0},
      "popularity_score": {"winner": "Hermes Nevada Cap", "margin": 35}
    },
    "category_weights": {"price_score": 0.10, "spec_score": 0.15, ...},
    "price_tiers": {"Hermes Nevada Cap": "luxury", "Local Brand Cap": "budget"},
    "cross_tier": true
  }
}
```

#### 4B. Tier Context String

```json
"tier_context": "Comparing a luxury product against a budget product. Scores reflect quality within each price tier."
```

Only present when `cross_tier: true`. Frontend can display as info banner.

#### 4C. SSE Streaming

The `scores` SSE event already sends the full `scoring_result` dict. The new fields (dimension_winners, category_weights, price_tiers, cross_tier) are included automatically since they're part of the dict. No streaming protocol changes needed.

---

### 5. Edge Cases

| Scenario | Handling |
|----------|----------|
| Both products luxury (Hermes vs Gucci) | Same tier → `cross_tier: false`, value uses same-tier formula, fashion weights apply |
| "Other" category + luxury brand | Luxury brand detection is category-independent. Price guardrails still apply. `CATEGORY_WEIGHTS["other"]` used for scoring. |
| No price found at all | `price_score = MISSING_SCORE`, value score falls back to spec-only (Section 1C partial missing handling), dimension_winners shows `{"winner": "N/A", "margin": null}` |
| Both products same price | `price_score = 75` for both (existing behavior), value score uses spec difference |
| Products with identical scores | `dimension_winners` shows "tie" with margin 0 |
| Both scores MISSING for a dimension | `dimension_winners` shows `{"winner": "N/A", "margin": null}` (not "tie") |
| Personalized + category weights | Category weights applied first, then personalization shifts capped at ±30% **of the category weight** (not old DEFAULT_WEIGHTS) |
| Budget-preference user, cross-tier | Budget preferences still apply normally. Cross-tier value formula runs independently; user's budget weight adjustment affects how much value_score contributes to overall, but doesn't change the value formula itself. |
| Official domain price found | `retailer_score=1.0`, sanity check skipped, falls through to response assembly |
| Official search finds results but GPT extraction fails | Falls through to Tier 2 (existing organic GPT extraction) normally |

---

### 6. Files Changed

| File | Changes |
|------|---------|
| `app/services/scoring_service.py` | `CATEGORY_WEIGHTS`, `PRICE_TIERS`, `TIER_EXPECTATIONS`, `CATEGORY_MIN_COVERAGE`, `_detect_price_tier()`, `_is_cross_tier()`, redesigned `_compute_value_score()`, `compute_dimension_winners()`, updated `compute_scores()`, updated `build_scores_summary()` |
| `app/services/structured_comparison_service.py` | `COUNTERFEIT_KEYWORDS`, `_is_counterfeit_listing()`, `_get_official_domain()`, `_clean_review_content()`, `_derive_rating_from_scores()`, smarter sanity thresholds (skip for official domains), counterfeit filtering in `_extract_price_from_shopping()` and `_strict_title_match()`, official domain targeted search in `_get_price()`, new fields in response assembly |
| `app/services/extraction_service.py` | Hardened `REVIEWS_EXTRACTION_PROMPT`, hardened price extraction prompt, overhauled verdict prompt structure, updated `build_scores_summary()` call |

### 7. Tests Required (80%+ coverage target)

| Test File | Tests |
|-----------|-------|
| `tests/test_scoring_service.py` | Category weight selection, price tier detection, cross-tier value score, same-tier value score, dimension winners, tie handling, category-specific coverage thresholds, personalization on top of category weights |
| `tests/test_luxury_brands.py` | Counterfeit keyword filter, official domain lookup, tighter sanity thresholds, official domain targeted search flow |
| `tests/test_review_cleanup.py` (new) | Garbage pattern filtering, short text rejection, sentiment misclassification in complaints, derived ratings from scores, clean_review_content integration |
| `tests/test_review_prompt_quality.py` | Verify new prompt rules present (garbage text, sentiment alignment) |
| `tests/test_price_priority.py` | Counterfeit listing rejection in title matching |

### 8. Cost Impact

- Non-luxury comparisons: **$0.000 extra** (all logic/prompt changes, same API calls)
- Luxury comparisons (Tier 1 fails): **+$0.001** (one Serper organic call for official domain)
- Test suite: **$0** (all unit tests with mocks)

### 9. Team Execution Plan

**4 Opus agents**, all `bypassPermissions`:

| Agent | Responsibility | Files |
|-------|---------------|-------|
| **scoring-agent** | Scoring engine overhaul (Sections 1 + 4) | `scoring_service.py`, response assembly in `structured_comparison_service.py` |
| **price-agent** | Price pipeline fixes (Section 2) | `structured_comparison_service.py` (price methods only) |
| **review-agent** | Review/rating fixes (Section 3) | `extraction_service.py` prompts, `structured_comparison_service.py` (review methods only) |
| **test-agent** | Red-green tests for all features, QA cross-check | All test files |

**Workflow:**
1. All 4 agents work in parallel on their assigned files
2. Test-agent writes red tests first (failing), then waits for implementations
3. As each agent completes, test-agent verifies green tests
4. Each agent QAs another's work before the team is disbanded
5. QA failures send work back to the originating agent
6. Idle agents write additional tests to hit 80%+ coverage

### 10. Not In Scope

- Frontend changes (deferred to frontend phase)
- Database schema changes (none needed)
- Cache invalidation (logic fixes refresh naturally with `nocache=true`)
- Fine-tuning GPT (deferred per discussion; prompt + post-processing first)
- RAG / knowledge base (deferred; Approach B for future consideration)
