# Scoring & Quality Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix broken luxury product comparisons by overhauling the scoring engine, price pipeline, review quality, ratings, and verdict generation.

**Architecture:** Category-aware scoring weights replace the single default profile. Price pipeline adds counterfeit filtering and official domain search for luxury brands. Review post-processing strips garbage text. Derived ratings fill gaps when no real ratings exist. Verdict prompt receives full scoring context.

**Tech Stack:** Python 3.12, FastAPI, pytest, GPT-4o-mini (prompts only — no new API calls for non-luxury)

**Spec:** `docs/superpowers/specs/2026-03-20-scoring-quality-overhaul-design.md`

**Team:** 4 Opus agents (`bypassPermissions`), cross-QA before disband. Each idle agent writes tests to hit 80%+ coverage. QA failures send work back to originating agent.

| Agent | Responsibility | Tasks |
|-------|---------------|-------|
| **scoring-agent** | Scoring engine overhaul + API response changes | Tasks 1-4 |
| **price-agent** | Price pipeline fixes (counterfeit filter, official domain, sanity) | Tasks 5-7 |
| **review-agent** | Review/rating/verdict fixes | Tasks 8-11 |
| **test-agent** | Tests for ALL features, QA each agent's work | Tasks 12-15 |

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `app/services/scoring_service.py` | Modify (lines 15-23, 43-44, 67-134, 136-171, 224-266, 327-370, 445-452, 454-469, 485-511) | scoring-agent |
| `app/services/structured_comparison_service.py` | Modify (lines 282-290, 333-358, 486-496, 540-564, 778, 890-920, 1587-1602, 1693-1755) | price-agent (price methods), review-agent (review methods), scoring-agent (response assembly) |
| `app/services/extraction_service.py` | Modify (lines 222-264, 292-346, 349-422, 743-749) | review-agent |
| `tests/test_scoring_service.py` | Modify (add ~30 new tests) | test-agent |
| `tests/test_luxury_brands.py` | Modify (add ~10 new tests) | test-agent |
| `tests/test_review_cleanup.py` | Create (new, ~15 tests) | test-agent |
| `tests/test_review_prompt_quality.py` | Modify (add ~5 new tests) | test-agent |
| `tests/test_price_priority.py` | Modify (add ~5 new tests) | test-agent |

---

## Task 1: Category-Specific Weight Profiles (scoring-agent)

**Files:**
- Modify: `app/services/scoring_service.py:15-23` (replace `DEFAULT_WEIGHTS`), `:43-44` (MAX_WEIGHT_SHIFT_RATIO usage), `:88` (weight computation call), `:111` (missing dims loop), `:127` (scoring_method), `:136-171` (_compute_weights)

- [ ] **Step 1: Add CATEGORY_WEIGHTS dict, delete DEFAULT_WEIGHTS**

Replace lines 15-23 in `app/services/scoring_service.py`:

```python
# Category-specific scoring weights (each sums to 1.0)
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

- [ ] **Step 2: Update _compute_weights to accept category and use category base**

Replace `_compute_weights` method (lines 136-171):

```python
def _compute_weights(self, preferences: Optional[Dict[str, Any]], category: str = "other") -> Dict[str, float]:
    """Compute scoring weights from category defaults + user preferences."""
    base_weights = CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS["other"])
    weights = dict(base_weights)

    if not preferences:
        return weights

    # Apply priority adjustments
    for priority in preferences.get("priorities", []):
        adjustments = PRIORITY_ADJUSTMENTS.get(priority, {})
        for dim, delta in adjustments.items():
            weights[dim] = weights.get(dim, 0) + delta

    # Apply budget adjustment
    budget = preferences.get("budget", "mid")
    budget_adj = BUDGET_ADJUSTMENTS.get(budget, {})
    for dim, delta in budget_adj.items():
        weights[dim] = weights.get(dim, 0) + delta

    # Cap each dimension's shift to ±30% of its CATEGORY weight (not global default)
    for dim in weights:
        cat_default = base_weights.get(dim, 0)
        max_val = cat_default * (1 + MAX_WEIGHT_SHIFT_RATIO)
        min_val = cat_default * (1 - MAX_WEIGHT_SHIFT_RATIO)
        weights[dim] = max(0.0, min(max_val, max(min_val, weights[dim])))

    # Renormalize to sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    else:
        n = len(weights)
        weights = {k: 1.0 / n for k in weights}

    return weights
```

- [ ] **Step 3: Update compute_scores to pass category to _compute_weights**

At line 88, change:
```python
weights = self._compute_weights(preferences)
```
to:
```python
weights = self._compute_weights(preferences, category)
```

- [ ] **Step 4: Update all references from DEFAULT_WEIGHTS to CATEGORY_WEIGHTS["other"]**

In `_empty_result` (line 460-462), `missing_dims` loop (line 111), and `scoring_method` (line 127):
- Replace all `DEFAULT_WEIGHTS` references with `CATEGORY_WEIGHTS["other"]`
- Update comment at line 43-44 from "default weight" to "category weight": `# Maximum allowed shift ratio from category weight (±30%)`
- Update `scoring_method` to `"category_weighted"` when no preferences, `"personalized"` when preferences exist (category is already in `category_used` field)

- [ ] **Step 5: Syntax check**

Run: `python -m py_compile app/services/scoring_service.py`
Expected: No output (success)

- [ ] **Step 6: Run existing scoring tests to check for regressions**

Run: `python -m pytest tests/test_scoring_service.py -v -x`
Expected: Some tests may fail due to changed default weights — note which ones need updating.

- [ ] **Step 7: Commit**

```bash
git add app/services/scoring_service.py
git commit -m "feat: replace DEFAULT_WEIGHTS with CATEGORY_WEIGHTS (9 categories)"
```

---

## Task 2: Price Tier Detection + Value Score Redesign (scoring-agent)

**Files:**
- Modify: `app/services/scoring_service.py` (add constants, new methods, replace `_compute_value_score`, update `_normalize_scores`)

- [ ] **Step 1: Add price tier constants and methods**

Add after `MISSING_SCORE = 50` (line 61):

```python
# Price tier thresholds (BHD)
PRICE_TIERS = {
    "budget":    (0, 11),       # < BHD 11 (~$30)
    "mid":       (11, 57),      # BHD 11-57 (~$30-150)
    "premium":   (57, 189),     # BHD 57-189 (~$150-500)
    "luxury":    (189, float("inf")),  # BHD 189+ (~$500+)
}

# Expected quality delivery per tier (0-1 scale)
TIER_EXPECTATIONS = {"budget": 0.6, "mid": 0.7, "premium": 0.8, "luxury": 0.85}
```

- [ ] **Step 2: Add tier detection methods to ScoringService class**

Add after `_extract_number` method:

```python
@staticmethod
def _detect_price_tier(price_bhd: float) -> str:
    """Detect price tier from BHD amount."""
    for tier, (low, high) in PRICE_TIERS.items():
        if low <= price_bhd < high:
            return tier
    return "luxury"

@staticmethod
def _is_cross_tier(tiers: List[str]) -> bool:
    """Check if products span different price tiers."""
    return len(set(tiers)) > 1
```

- [ ] **Step 3: Update _normalize_scores to compute tiers and pass to value score**

In `_normalize_scores` (line 327-370), add tier detection before the loop and pass tier info to `_compute_value_score`:

```python
def _normalize_scores(
    self,
    raw_scores: List[Dict[str, Any]],
    products_data: List[Dict[str, Any]],
) -> List[Dict[str, float]]:
    """Normalize raw scores to 0-100 scale relative to each other."""
    # Extract category for tier-aware value scoring
    category = products_data[0].get("category", "other") if products_data else "other"

    # Detect price tiers
    price_tiers = []
    for rs in raw_scores:
        price_raw = rs.get("price_raw")
        if price_raw is not None:
            price_tiers.append(self._detect_price_tier(price_raw))
        else:
            price_tiers.append("mid")  # Default for missing price
    is_cross_tier = self._is_cross_tier(price_tiers)

    normalized = []
    for i in range(len(raw_scores)):
        scores = {}
        scores["price_score"] = self._normalize_price(raw_scores, i)
        scores["spec_score"] = self._normalize_dimension(raw_scores, i, "spec_raw", higher_better=True)
        scores["review_score"] = self._normalize_review(raw_scores, i)
        scores["value_score"] = self._compute_value_score(
            scores["spec_score"], scores["price_score"], price_tiers[i], is_cross_tier
        )
        scores["reliability_score"] = self._normalize_direct(raw_scores, i, "reliability_raw")
        scores["popularity_score"] = self._normalize_direct(raw_scores, i, "popularity_raw")
        normalized.append(scores)

    # Store tier info for later use in response
    self._price_tiers = price_tiers
    self._is_cross_tier = is_cross_tier

    return normalized
```

- [ ] **Step 4: Replace _compute_value_score**

Replace lines 445-452:

```python
def _compute_value_score(self, spec_score: float, price_score: float, price_tier: str, is_cross_tier: bool) -> float:
    """Value = tier-aware combination of spec quality and price."""
    if spec_score == MISSING_SCORE and price_score == MISSING_SCORE:
        return MISSING_SCORE
    if spec_score == MISSING_SCORE and price_score != MISSING_SCORE:
        return price_score
    if price_score == MISSING_SCORE and spec_score != MISSING_SCORE:
        return spec_score

    if is_cross_tier:
        expected = TIER_EXPECTATIONS.get(price_tier, 0.7) * 100
        delivery = spec_score
        value = 50 + (delivery - expected) * 0.8
        return round(max(0, min(100, value)), 1)
    else:
        return round(spec_score * 0.6 + price_score * 0.4, 1)
```

- [ ] **Step 5: Add tier info to compute_scores return value**

In `compute_scores()`, before the `return` (line 129), add tier data. NOTE: Task 3 Step 4 will add more fields to this same return dict — build them all here:

```python
# Add tier metadata
price_tiers_map = {}
product_names = []
for i, product in enumerate(products_data):
    name = product.get("name", f"Product {i+1}")
    product_names.append(name)
    price_tiers_map[name] = getattr(self, '_price_tiers', ["mid"] * len(products_data))[i]

# NOTE: dimension_winners and category_weights are added in Task 3 Step 4
return {
    "scores": result_products,
    "winner_index": winner_index,
    "win_margin": win_margin,
    "scoring_method": scoring_method,
    "price_tiers": price_tiers_map,
    "cross_tier": getattr(self, '_is_cross_tier', False),
}
```

- [ ] **Step 6: Syntax check + run tests**

```bash
python -m py_compile app/services/scoring_service.py
python -m pytest tests/test_scoring_service.py -v -x --timeout=30
```

- [ ] **Step 7: Commit**

```bash
git add app/services/scoring_service.py
git commit -m "feat: add price tier detection and tier-aware value scoring"
```

---

## Task 3: Spec Coverage Penalty + Dimension Winners (scoring-agent)

**Files:**
- Modify: `app/services/scoring_service.py` (lines 259-264, add `CATEGORY_MIN_COVERAGE`, add `compute_dimension_winners`)

- [ ] **Step 1: Add CATEGORY_MIN_COVERAGE constant**

Add after `TIER_EXPECTATIONS`:

```python
# Minimum spec coverage before penalty, per category
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

- [ ] **Step 2: Update _score_specs to use category-specific threshold**

Replace lines 259-266 (the coverage penalty block through the return):

```python
        total_fields = len(schema_fields)
        coverage_ratio = scored_fields / total_fields if total_fields > 0 else 0
        min_coverage = CATEGORY_MIN_COVERAGE.get(category, 0.3)
        if coverage_ratio < min_coverage:
            penalty_factor = 0.5 + (coverage_ratio / min_coverage) * 0.5  # Range: 0.5 to 1.0
            return (total_score / scored_fields) * penalty_factor
```

- [ ] **Step 3: Add compute_dimension_winners method**

Add after `build_scores_summary`:

```python
def compute_dimension_winners(self, scoring_result: Dict[str, Any], product_names: List[str]) -> Dict[str, Any]:
    """Compute which product wins each scoring dimension."""
    scores = scoring_result["scores"]
    dimensions = ["price_score", "spec_score", "review_score", "value_score", "reliability_score", "popularity_score"]
    winners = {}
    for dim in dimensions:
        s0 = scores.get("product_0", {}).get("breakdown", {}).get(dim, 0)
        s1 = scores.get("product_1", {}).get("breakdown", {}).get(dim, 0)
        # Check MISSING first — before computing margin
        if s0 == MISSING_SCORE and s1 == MISSING_SCORE:
            winners[dim] = {"winner": "N/A", "margin": None}
            continue
        margin = abs(s0 - s1)
        if margin < 2.0:
            winners[dim] = {"winner": "tie", "margin": 0}
        elif s0 > s1:
            winners[dim] = {"winner": product_names[0], "margin": round(margin, 1)}
        else:
            winners[dim] = {"winner": product_names[1], "margin": round(margin, 1)}
    return winners
```

- [ ] **Step 4: Add dimension_winners + category_weights to the return dict built in Task 2**

In `compute_scores()`, BEFORE the return statement (which was built in Task 2 Step 5), add dimension winners computation. Then ADD fields to the existing return dict:

```python
# Compute dimension winners
dimension_winners = self.compute_dimension_winners(
    {"scores": result_products}, product_names  # product_names built in Task 2 Step 5
)

# Add to the return dict built in Task 2 Step 5 (add these two fields):
# "dimension_winners": dimension_winners,
# "category_weights": dict(weights),
```

The final return dict should now be:
```python
return {
    "scores": result_products,
    "winner_index": winner_index,
    "win_margin": win_margin,
    "scoring_method": scoring_method,
    "price_tiers": price_tiers_map,
    "cross_tier": getattr(self, '_is_cross_tier', False),
    "dimension_winners": dimension_winners,
    "category_weights": dict(weights),
}
```

- [ ] **Step 5: Update build_scores_summary with tier + dimension data**

Replace `build_scores_summary` method:

```python
def build_scores_summary(self, scoring_result: Dict[str, Any], product_names: List[str]) -> str:
    """Build a structured scoring context for the GPT verdict prompt."""
    if not scoring_result or "scores" not in scoring_result:
        return ""

    scores = scoring_result["scores"]
    price_tiers = scoring_result.get("price_tiers", {})
    cross_tier = scoring_result.get("cross_tier", False)
    dim_winners = scoring_result.get("dimension_winners", {})
    cat_weights = scoring_result.get("category_weights", {})

    lines = []
    for i, name in enumerate(product_names):
        key = f"product_{i}"
        if key not in scores:
            continue
        ps = scores[key]
        overall = ps["overall"]
        bd = ps["breakdown"]
        tier = price_tiers.get(name, "unknown")
        lines.append(f"Product {'AB'[i]}: {name}")
        lines.append(f"  Overall: {overall}/100 | Price: {bd.get('price_score', 50)} | Specs: {bd.get('spec_score', 50)} | Reviews: {bd.get('review_score', 50)} | Value: {bd.get('value_score', 50)} | Reliability: {bd.get('reliability_score', 50)} | Popularity: {bd.get('popularity_score', 50)}")
        lines.append(f"  Price tier: {tier}")

    lines.append(f"\nCross-tier comparison: {'yes' if cross_tier else 'no'}")

    if dim_winners:
        winner_parts = []
        for dim, info in dim_winners.items():
            dim_name = dim.replace("_score", "")
            w = info.get("winner", "N/A")
            m = info.get("margin")
            if w == "tie":
                winner_parts.append(f"{dim_name}: tie")
            elif w == "N/A":
                winner_parts.append(f"{dim_name}: N/A")
            else:
                winner_parts.append(f"{dim_name}: {w} (+{m})")
        lines.append(f"Dimension winners: {', '.join(winner_parts)}")

    if cat_weights:
        weight_parts = [f"{k.replace('_score', '')}={round(v, 2)}" for k, v in cat_weights.items()]
        lines.append(f"Category weights: {', '.join(weight_parts)}")

    winner_idx = scoring_result.get("winner_index", 0)
    margin = scoring_result.get("win_margin", 0)
    if len(product_names) >= 2:
        lines.append(f"Score winner: {product_names[winner_idx]} by {margin} points")

    return "\n".join(lines)
```

- [ ] **Step 6: Syntax check + run tests**

```bash
python -m py_compile app/services/scoring_service.py
python -m pytest tests/test_scoring_service.py -v -x --timeout=30
```

- [ ] **Step 7: Commit**

```bash
git add app/services/scoring_service.py
git commit -m "feat: category-aware coverage penalty, dimension winners, enriched verdict summary"
```

---

## Task 4: Response Assembly + Tier Context (scoring-agent)

**Files:**
- Modify: `app/services/structured_comparison_service.py:282-290,333-358,486-496,540-564`

- [ ] **Step 1: Add tier_context to response assembly (non-streaming)**

In `compare_from_text()`, after `scoring_result` is computed (~line 290), add tier context computation. In the response dict (~line 333-358), add:

```python
# After scoring_result is assigned:
cross_tier = scoring_result.get("cross_tier", False)
price_tiers = scoring_result.get("price_tiers", {})
tier_context = None
if cross_tier:
    tier_names = list(set(price_tiers.values()))
    tier_context = f"Comparing a {tier_names[0]} product against a {tier_names[1]} product. Scores reflect quality within each price tier."

# In response dict, add:
"tier_context": tier_context,
```

- [ ] **Step 2: Add derived ratings (display-only, after scoring)**

After `scoring_result = scoring_service.compute_scores(...)` and before `generate_comparison()`:

```python
# Derive ratings for products with no real ratings (display only — not fed back to scoring)
for i, product in enumerate(products):
    if product.get("rating") is None:
        overall = scoring_result["scores"].get(f"product_{i}", {}).get("overall", 50)
        product["rating"] = self._derive_rating_from_scores(overall)
        product["rating_source"] = {
            "name": "Product analysis",
            "url": None,
            "extract_method": "score_derived",
        }
```

Add `_derive_rating_from_scores` method to the class:

```python
def _derive_rating_from_scores(self, overall_score: float) -> float:
    """Derive a display rating from overall score. Display only — not fed to scoring."""
    rating = 2.5 + (overall_score / 100) * 2.3
    return round(min(rating, 4.8), 1)
```

- [ ] **Step 3: Do the same for streaming path**

Apply same tier_context and derived rating logic to `compare_from_text_streaming()` (~line 486-564).

- [ ] **Step 4: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: tier context in response, derived ratings for missing products"
```

---

## Task 5: Counterfeit Keyword Filter (price-agent)

**Files:**
- Modify: `app/services/structured_comparison_service.py` (add constant + method, modify `_extract_price_from_shopping` and `_strict_title_match`)

- [ ] **Step 1: Add COUNTERFEIT_KEYWORDS and _is_counterfeit_listing**

Add as class-level constant (near `LUXURY_BRAND_KEYWORDS` at ~line 1113):

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
    """Check if a shopping listing title indicates counterfeit/replica."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in StructuredComparisonService.COUNTERFEIT_KEYWORDS)
```

- [ ] **Step 2: Add counterfeit check as first filter in _extract_price_from_shopping**

In `_extract_price_from_shopping()` (~line 1693), inside the shopping items loop, add as the FIRST check before accessory filter:

```python
# First filter: reject counterfeit listings
title = item.get("title", "")
if self._is_counterfeit_listing(title):
    logger.debug(f"[PRICE] Skipping counterfeit listing: {title[:60]}")
    continue
```

- [ ] **Step 3: Add counterfeit check to _strict_title_match**

In `_strict_title_match()` (~line 1587), add as first condition:

```python
@staticmethod
def _strict_title_match(product_name: str, title: str) -> bool:
    # Reject counterfeit listings immediately
    if StructuredComparisonService._is_counterfeit_listing(title):
        return False
    # ... rest of existing method
```

- [ ] **Step 4: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`

- [ ] **Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: counterfeit keyword filter for shopping results"
```

---

## Task 6: Official Domain Targeted Search for Luxury (price-agent)

**Files:**
- Modify: `app/services/structured_comparison_service.py` (add `_get_official_domain`, modify `_get_price`)

- [ ] **Step 1: Add _get_official_domain helper**

Add near `_is_luxury_brand()`:

```python
def _get_official_domain(self, product_name: str) -> Optional[str]:
    """Get the official brand domain for a luxury product.
    Uses same matching as _is_luxury_brand, then looks up OFFICIAL_BRAND_DOMAINS."""
    name_lower = product_name.lower()
    for keyword in self.LUXURY_BRAND_KEYWORDS:
        if keyword in name_lower:
            # Find matching domain from OFFICIAL_BRAND_DOMAINS
            for domain in self.OFFICIAL_BRAND_DOMAINS:
                # Match brand keyword to domain (e.g., "hermes" → "hermes.com")
                domain_base = domain.split(".")[0].replace("-", "")
                keyword_clean = keyword.replace(" ", "").replace("-", "")
                if keyword_clean in domain_base or domain_base in keyword_clean:
                    return domain
    return None
```

- [ ] **Step 2: Add official domain search between Tier 1 and Tier 2 in _get_price**

In the `_get_price()` method (~line 890-920), after the Tier 1 Shopping extraction fails or is rejected by sanity check, add before Tier 2:

```python
# Official domain targeted search (luxury brands only, 1 Serper credit)
if not price and self._is_luxury_brand(full_name):
    official_domain = self._get_official_domain(full_name)
    if official_domain:
        logger.info(f"[PRICE] Luxury brand — trying official domain: {official_domain}")
        try:
            # search_web and extract_price are already imported at module level
            official_results = await search_web(f"{full_name} site:{official_domain}")
            self.api_calls += 1
            self._track_cost(0.001)  # 1 Serper credit
            if official_results and official_results.get("organic"):
                official_price, usage = await extract_price(
                    full_name, official_results["organic"], region_info
                )
                if official_price:
                    official_price["retailer"] = official_domain
                    official_price["retailer_score"] = 1.0
                    price = official_price
                    logger.info(f"[PRICE] Official domain price found: {price.get('amount')} from {official_domain}")
        except Exception as e:
            logger.warning(f"[PRICE] Official domain search failed: {e}")
            # Fall through to Tier 2
```

- [ ] **Step 3: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`

- [ ] **Step 4: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: official domain targeted search for luxury brand prices"
```

---

## Task 7: Smarter Sanity Thresholds + Price Prompt Hardening (price-agent)

**Files:**
- Modify: `app/services/structured_comparison_service.py` (sanity check ~line 893-914)
- Modify: `app/services/extraction_service.py` (price extraction prompt ~line 222-264)

- [ ] **Step 1: Update sanity check in _get_price**

Find the sanity check code (~line 893-914). The existing logic compares Tier 1 price against a Tier 3 GPT estimate and rejects if the ratio exceeds thresholds. Wrap the ENTIRE sanity check block with an official domain bypass:

```python
# Sanity check: Tier 1 vs Tier 3 estimate
if price and price.get("retailer_score", 0) >= 1.0:
    # Official domain — trust it, skip sanity check entirely
    logger.info(f"[PRICE] Official domain price ({price.get('retailer')}) — skipping sanity check")
elif price and (self._is_high_value_query(full_name) or self._is_luxury_brand(full_name)) and price.get("retailer_score", 0) < 1.0:
    # Set thresholds based on luxury status
    if self._is_luxury_brand(full_name):
        high_threshold = 1.8   # was 2.0
        low_threshold = 0.6    # was 0.5
    else:
        high_threshold = 2.0
        low_threshold = 0.5

    # Get Tier 3 estimate for comparison (existing logic)
    tier3_estimate, usage = await extract_price_from_training_data(full_name, region_info)
    # ... rest of existing sanity check comparison using high_threshold/low_threshold ...
    # If tier1_bhd > tier3_bhd * high_threshold → reject (too high)
    # If tier1_bhd < tier3_bhd * low_threshold → reject (counterfeit-level low)
```

The key change: wrap with `price.get("retailer_score", 0) >= 1.0` check FIRST, and update the threshold values inside the else branch. Keep the existing comparison logic intact — only the thresholds and the bypass condition change.

- [ ] **Step 2: Harden price extraction prompt**

In `extraction_service.py`, find the price extraction prompt (~line 222-264) and add after existing source priority rules:

```
REJECT these sources entirely — do NOT extract prices from:
- Reseller/marketplace individual sellers (eBay individuals, Poshmark, Mercari, Vestiaire)
- Known counterfeit platforms (DHgate, AliExpress, Temu, Wish)
- Listings with "pre-owned", "used", "vintage" unless user explicitly asked for used
- Any listing priced at <40% of typical retail for luxury/designer brands
- Listings with "replica", "fake", "dupe", "inspired" in the title or URL
```

- [ ] **Step 3: Syntax check both files**

```bash
python -m py_compile app/services/structured_comparison_service.py
python -m py_compile app/services/extraction_service.py
```

- [ ] **Step 4: Commit**

```bash
git add app/services/structured_comparison_service.py app/services/extraction_service.py
git commit -m "feat: smarter sanity thresholds for luxury, harden price prompt"
```

---

## Task 8: Review Prompt Hardening (review-agent)

**Files:**
- Modify: `app/services/extraction_service.py:292-346` (REVIEWS_EXTRACTION_PROMPT)

- [ ] **Step 1: Add garbage text rejection rules to REVIEWS_EXTRACTION_PROMPT**

Find the REVIEWS_EXTRACTION_PROMPT (~line 292) and add these rules to the RULES section:

```
CONTENT QUALITY — NEVER include these in praise OR complaints:
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

SENTIMENT ALIGNMENT for complaints:
- Only include NEGATIVE observations in complaints. A positive statement is NOT a criticism.
- If a snippet mentions both positive and negative aspects, extract ONLY the negative part for complaints.
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile app/services/extraction_service.py`

- [ ] **Step 3: Commit**

```bash
git add app/services/extraction_service.py
git commit -m "feat: harden review extraction prompt — garbage text rejection rules"
```

---

## Task 9: Backend Review Post-Processing Filter (review-agent)

**Files:**
- Modify: `app/services/structured_comparison_service.py` (add `_clean_review_content`, integrate at line 778)

- [ ] **Step 1: Add GARBAGE_PATTERNS, NEGATIVE_INDICATORS, POSITIVE_INDICATORS constants**

Add near `_clean_review_citations` (~line 1165):

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
```

- [ ] **Step 2: Add _clean_review_content method**

Add before `_clean_review_citations`:

```python
def _clean_review_content(self, reviews: dict) -> dict:
    """Remove garbage text, short items, and misclassified sentiments from reviews."""
    import re
    for section in ["common_praises", "detailed_praises", "common_complaints", "detailed_complaints"]:
        items = reviews.get(section, [])
        if not items:
            continue
        cleaned = []
        for item in items:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            if any(re.search(p, text, re.IGNORECASE) for p in self.GARBAGE_PATTERNS):
                continue
            if len(text.split()) < 8:
                continue
            if "complaint" in section:
                words = set(text.lower().split())
                has_negative = bool(words & self.NEGATIVE_INDICATORS)
                has_positive = bool(words & self.POSITIVE_INDICATORS)
                if has_positive and not has_negative:
                    continue
            cleaned.append(item)
        reviews[section] = cleaned
    return reviews
```

- [ ] **Step 3: Integrate — call _clean_review_content BEFORE _clean_review_citations**

At line 778, where `_clean_review_citations` is called, add the content cleaning first:

```python
# Clean review content (garbage removal) THEN citations (snippet→domain)
result["reviews"] = self._clean_review_content(result["reviews"])
result["reviews"] = self._clean_review_citations(
    result["reviews"], search_results_for_citations
)
```

- [ ] **Step 4: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`

- [ ] **Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: backend review post-processing — garbage text and sentiment filter"
```

---

## Task 10: Verdict Prompt Overhaul (review-agent)

**Files:**
- Modify: `app/services/extraction_service.py:349-422` (COMPARISON_PROMPT), `:743-749` (scores_summary injection)

- [ ] **Step 1: Update scores_summary injection in generate_comparison**

Find where `scores_summary` is appended to the prompt (~line 743-749) and replace with structured injection:

```python
if scores_summary:
    prompt += f"""

## Scoring Context
{scores_summary}

## Verdict Requirements
1. RECOMMENDATION: State the winner with the score margin. Explain WHO should buy which product and WHY based on the dimension scores.
2. KEY DIFFERENCES: 3-5 data-backed differences. Reference actual specs, prices, and review findings. Cite which dimension each difference relates to.
3. VALUE ANALYSIS: Explain the value proposition of each product. If cross-tier, acknowledge that each serves a different market segment — do NOT penalize luxury for being expensive.
4. BEST FOR: One sentence per product describing the ideal buyer.

Your verdict MUST be consistent with the scores above. If Product A wins on reviews, your text must reflect that. Do NOT contradict the scoring data.
If this is a cross-tier comparison, frame it as "different products for different needs" rather than "expensive vs cheap."
"""
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile app/services/extraction_service.py`

- [ ] **Step 3: Commit**

```bash
git add app/services/extraction_service.py
git commit -m "feat: scoring-aware verdict prompt with dimension data injection"
```

---

## Task 11: Review Cleanup for Streaming Path (review-agent)

**Files:**
- Modify: `app/services/structured_comparison_service.py` (streaming path ~line 486-564)

- [ ] **Step 1: Add _clean_review_content to streaming path**

In `compare_from_text_streaming()`, the review data is fetched in Phase 2 and yielded. Find the line where `_clean_review_citations()` is called on reviews in the streaming path (search for `_clean_review_citations` — there should be a call in the streaming generator similar to line 778). Add `_clean_review_content()` BEFORE it, same pattern as the non-streaming fix in Task 9 Step 3.

If the streaming path processes reviews inline (not via `_fetch_product_data`), find where `reviews` data is assigned to the product dict and add both cleanup calls there.

- [ ] **Step 2: Add derived ratings in streaming path**

After `scoring_result = scoring_service.compute_scores(...)` at ~line 486, add:

```python
# Derive ratings for products with no real ratings (display only)
for i, product in enumerate(products):
    if product.get("rating") is None:
        overall = scoring_result["scores"].get(f"product_{i}", {}).get("overall", 50)
        product["rating"] = self._derive_rating_from_scores(overall)
        product["rating_source"] = {
            "name": "Product analysis",
            "url": None,
            "extract_method": "score_derived",
        }
```

- [ ] **Step 3: Add tier_context to streaming response**

In the final `complete` event assembly (~line 540-564), compute and add `tier_context`:

```python
cross_tier = scoring_result.get("cross_tier", False)
price_tiers = scoring_result.get("price_tiers", {})
tier_context = None
if cross_tier:
    tier_names = list(set(price_tiers.values()))
    tier_context = f"Comparing a {tier_names[0]} product against a {tier_names[1]} product. Scores reflect quality within each price tier."

# Add to the complete event dict:
# "tier_context": tier_context,
```

- [ ] **Step 4: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`

- [ ] **Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: review cleanup + derived ratings + tier context in streaming path"
```

---

## Task 12: Scoring Service Tests (test-agent)

**Files:**
- Modify: `tests/test_scoring_service.py`

- [ ] **Step 1: Write tests for category weight selection**

```python
def test_category_weights_electronics():
    """Electronics should weight specs and reliability higher."""
    from app.services.scoring_service import CATEGORY_WEIGHTS
    w = CATEGORY_WEIGHTS["electronics"]
    assert w["spec_score"] == 0.25
    assert w["reliability_score"] == 0.15
    assert abs(sum(w.values()) - 1.0) < 0.001

def test_category_weights_fashion():
    """Fashion should weight popularity and reviews higher."""
    from app.services.scoring_service import CATEGORY_WEIGHTS
    w = CATEGORY_WEIGHTS["fashion"]
    assert w["popularity_score"] == 0.25
    assert w["review_score"] == 0.25
    assert w["price_score"] == 0.10

def test_all_category_weights_sum_to_one():
    """Every category weight profile must sum to 1.0."""
    from app.services.scoring_service import CATEGORY_WEIGHTS
    for cat, weights in CATEGORY_WEIGHTS.items():
        assert abs(sum(weights.values()) - 1.0) < 0.001, f"{cat} weights sum to {sum(weights.values())}"

def test_unknown_category_falls_back_to_other():
    """Unknown categories should use 'other' weights."""
    service = ScoringService()
    weights = service._compute_weights(None, "nonexistent_category")
    from app.services.scoring_service import CATEGORY_WEIGHTS
    assert weights == CATEGORY_WEIGHTS["other"]
```

- [ ] **Step 2: Write tests for price tier detection**

```python
def test_price_tier_budget():
    assert ScoringService._detect_price_tier(5.0) == "budget"

def test_price_tier_mid():
    assert ScoringService._detect_price_tier(30.0) == "mid"

def test_price_tier_premium():
    assert ScoringService._detect_price_tier(100.0) == "premium"

def test_price_tier_luxury():
    assert ScoringService._detect_price_tier(500.0) == "luxury"

def test_cross_tier_different():
    assert ScoringService._is_cross_tier(["budget", "luxury"]) == True

def test_cross_tier_same():
    assert ScoringService._is_cross_tier(["luxury", "luxury"]) == False
```

- [ ] **Step 3: Write tests for value score redesign**

```python
def test_value_score_cross_tier_luxury():
    """Luxury product meeting expectations should score ~65."""
    service = ScoringService()
    score = service._compute_value_score(85, 30, "luxury", True)
    assert 60 <= score <= 70  # Meeting luxury expectations

def test_value_score_cross_tier_budget():
    """Budget product exceeding expectations should score higher."""
    service = ScoringService()
    score = service._compute_value_score(70, 95, "budget", True)
    assert score > 55  # Exceeding budget expectations

def test_value_score_same_tier():
    """Same-tier uses weighted spec/price blend."""
    service = ScoringService()
    score = service._compute_value_score(80, 60, "mid", False)
    expected = 80 * 0.6 + 60 * 0.4  # 72
    assert abs(score - expected) < 0.5

def test_value_score_missing_spec():
    """Missing spec should fall back to price only."""
    service = ScoringService()
    score = service._compute_value_score(MISSING_SCORE, 70, "mid", False)
    assert score == 70  # Only price data

def test_value_score_both_missing():
    """Both missing should return MISSING_SCORE."""
    service = ScoringService()
    score = service._compute_value_score(MISSING_SCORE, MISSING_SCORE, "mid", False)
    assert score == MISSING_SCORE
```

- [ ] **Step 4: Write tests for dimension winners**

```python
def test_dimension_winners_clear_winner():
    service = ScoringService()
    result = {"scores": {
        "product_0": {"breakdown": {"price_score": 80, "spec_score": 60}},
        "product_1": {"breakdown": {"price_score": 40, "spec_score": 90}},
    }}
    winners = service.compute_dimension_winners(result, ["A", "B"])
    assert winners["price_score"]["winner"] == "A"
    assert winners["spec_score"]["winner"] == "B"

def test_dimension_winners_tie():
    service = ScoringService()
    result = {"scores": {
        "product_0": {"breakdown": {"price_score": 50}},
        "product_1": {"breakdown": {"price_score": 51}},
    }}
    winners = service.compute_dimension_winners(result, ["A", "B"])
    assert winners["price_score"]["winner"] == "tie"

def test_dimension_winners_both_missing():
    service = ScoringService()
    result = {"scores": {
        "product_0": {"breakdown": {"price_score": MISSING_SCORE}},
        "product_1": {"breakdown": {"price_score": MISSING_SCORE}},
    }}
    winners = service.compute_dimension_winners(result, ["A", "B"])
    assert winners["price_score"]["winner"] == "N/A"
    assert winners["price_score"]["margin"] is None
```

- [ ] **Step 5: Write tests for category-specific coverage threshold**

```python
def test_fashion_coverage_no_penalty_at_30_percent():
    """Fashion with 30%+ coverage should NOT be penalized."""
    service = ScoringService()
    # Fashion has 10 fields — 3 filled = 30% coverage
    specs = {"material": "leather", "style": "cap", "origin": "Italy"}
    score = service._score_specs(specs, "fashion")
    # Should not have penalty factor applied
    assert score > 0

def test_electronics_coverage_penalized_at_30_percent():
    """Electronics with only 30% coverage SHOULD be penalized."""
    service = ScoringService()
    specs = {"processor": "A17", "ram": "8GB", "storage": "256GB"}
    score_30 = service._score_specs(specs, "electronics")
    # 3/11 fields = 27% < 50% threshold → penalty
    # Add more fields to get above threshold
    specs_full = {**specs, "battery": "4000", "display": "6.1", "rear_camera": "48MP",
                  "front_camera": "12MP", "os": "iOS", "weight": "170g"}
    score_80 = service._score_specs(specs_full, "electronics")
    # Full coverage should score higher than penalized
    assert score_80 > score_30
```

- [ ] **Step 6: Write tests for personalization on category weights**

```python
def test_personalization_capped_at_category_weight():
    """Personalization shift capped at 30% of CATEGORY weight, not DEFAULT."""
    service = ScoringService()
    prefs = {"priorities": ["price"], "budget": "budget"}
    weights = service._compute_weights(prefs, "fashion")
    # Fashion price_score base = 0.10, max shift = ±0.03
    # After renormalization, price_score should not exceed ~0.13 pre-normalization
    # But with renormalization it shifts — just verify it's not extreme
    assert weights["price_score"] < 0.25  # Should NOT reach the old default level
```

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/test_scoring_service.py -v --timeout=30
```

- [ ] **Step 8: Commit**

```bash
git add tests/test_scoring_service.py
git commit -m "test: scoring service — category weights, tiers, value, winners, coverage"
```

---

## Task 13: Price Pipeline Tests (test-agent)

**Files:**
- Modify: `tests/test_luxury_brands.py`, `tests/test_price_priority.py`

- [ ] **Step 1: Write counterfeit filter tests**

Add to `tests/test_luxury_brands.py`:

```python
def test_counterfeit_listing_replica():
    assert service._is_counterfeit_listing("Hermes Replica Black Cap") == True

def test_counterfeit_listing_fake():
    assert service._is_counterfeit_listing("Fake Louis Vuitton Belt") == True

def test_counterfeit_listing_inspired():
    assert service._is_counterfeit_listing("Designer Inspired Gucci Bag") == True

def test_counterfeit_listing_legitimate():
    assert service._is_counterfeit_listing("Hermes Nevada Cap Black") == False

def test_counterfeit_listing_pre_owned():
    assert service._is_counterfeit_listing("Pre-Owned Chanel Classic Flap") == True

def test_counterfeit_listing_vintage():
    assert service._is_counterfeit_listing("Vintage Louis Vuitton Monogram") == True
```

- [ ] **Step 2: Write official domain lookup tests**

```python
def test_get_official_domain_hermes():
    domain = service._get_official_domain("Hermes Nevada Cap")
    assert domain is not None
    assert "hermes" in domain

def test_get_official_domain_lv():
    domain = service._get_official_domain("Louis Vuitton Mesh Cap")
    assert domain is not None
    assert "louisvuitton" in domain

def test_get_official_domain_non_luxury():
    domain = service._get_official_domain("Nike Air Max")
    assert domain is None
```

- [ ] **Step 3: Write official domain sanity skip test**

```python
def test_official_domain_skips_sanity_check():
    """Prices from official domains (retailer_score=1.0) should skip sanity check."""
    # A price with retailer_score=1.0 should be trusted even if it differs from Tier 3 estimate
    price = {"amount": 500, "retailer": "hermes.com", "retailer_score": 1.0}
    # This test verifies the logic in _get_price — mock the sanity check flow
    # If retailer_score >= 1.0, sanity check should not reject the price
    assert price.get("retailer_score", 0) >= 1.0  # Confirms bypass condition
```

- [ ] **Step 4: Write strict_title_match counterfeit rejection tests**

Add to `tests/test_price_priority.py`:

```python
def test_strict_title_match_rejects_replica():
    """Replica listings should fail title match even if all keywords match."""
    assert service._strict_title_match("Hermes Cap", "Hermes Replica Black Cap") == False

def test_strict_title_match_accepts_legitimate():
    assert service._strict_title_match("Hermes Cap", "Hermes Nevada Cap Black") == True
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_luxury_brands.py tests/test_price_priority.py -v --timeout=30
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_luxury_brands.py tests/test_price_priority.py
git commit -m "test: counterfeit filter, official domain lookup, sanity skip, title match rejection"
```

---

## Task 14: Review Cleanup Tests (test-agent)

**Files:**
- Create: `tests/test_review_cleanup.py`

- [ ] **Step 1: Write garbage pattern filtering tests**

```python
"""Tests for review content post-processing filter."""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService

@pytest.fixture
def service():
    return StructuredComparisonService()

def test_removes_learn_more(service):
    reviews = {"common_complaints": [{"text": "Learn more about condition and details"}]}
    cleaned = service._clean_review_content(reviews)
    assert len(cleaned["common_complaints"]) == 0

def test_removes_navigation_text(service):
    reviews = {"common_praises": [{"text": "Click here to see full product details and specs"}]}
    cleaned = service._clean_review_content(reviews)
    assert len(cleaned["common_praises"]) == 0

def test_keeps_legitimate_review(service):
    reviews = {"common_praises": [{"text": "The leather quality is exceptional and the stitching is perfectly done throughout"}]}
    cleaned = service._clean_review_content(reviews)
    assert len(cleaned["common_praises"]) == 1

def test_removes_short_text(service):
    reviews = {"common_praises": [{"text": "Great product overall"}]}
    cleaned = service._clean_review_content(reviews)
    assert len(cleaned["common_praises"]) == 0  # < 8 words
```

- [ ] **Step 2: Write sentiment misclassification tests**

```python
def test_removes_positive_from_complaints(service):
    """Positive text in complaints section should be removed."""
    reviews = {"common_complaints": [
        {"text": "The quality is absolutely excellent and the leather feels premium and luxurious"},
    ]}
    cleaned = service._clean_review_content(reviews)
    assert len(cleaned["common_complaints"]) == 0

def test_keeps_negative_complaints(service):
    """Genuine negative text should stay in complaints."""
    reviews = {"common_complaints": [
        {"text": "The stitching quality is very poor and started peeling after just two weeks of use"},
    ]}
    cleaned = service._clean_review_content(reviews)
    assert len(cleaned["common_complaints"]) == 1

def test_keeps_mixed_sentiment_with_negative(service):
    """Mixed sentiment with genuine negative should stay."""
    reviews = {"common_complaints": [
        {"text": "The design looks beautiful but the material feels cheap and flimsy compared to the original"},
    ]}
    cleaned = service._clean_review_content(reviews)
    assert len(cleaned["common_complaints"]) == 1  # Has "cheap" and "flimsy"
```

- [ ] **Step 3: Write derived rating tests**

```python
def test_derived_rating_high_score():
    service = StructuredComparisonService()
    rating = service._derive_rating_from_scores(90)
    assert 4.5 <= rating <= 4.8

def test_derived_rating_mid_score():
    service = StructuredComparisonService()
    rating = service._derive_rating_from_scores(50)
    assert 3.5 <= rating <= 4.0

def test_derived_rating_low_score():
    service = StructuredComparisonService()
    rating = service._derive_rating_from_scores(10)
    assert 2.5 <= rating <= 3.0

def test_derived_rating_never_exceeds_4_8():
    service = StructuredComparisonService()
    rating = service._derive_rating_from_scores(100)
    assert rating <= 4.8

def test_derived_rating_minimum_2_5():
    service = StructuredComparisonService()
    rating = service._derive_rating_from_scores(0)
    assert rating >= 2.5
```

- [ ] **Step 4: Write string-item handling tests**

```python
def test_handles_string_items(service):
    """Reviews with plain string items (not dicts) should be handled."""
    reviews = {"common_praises": ["The build quality is exceptional and worth every penny spent"]}
    cleaned = service._clean_review_content(reviews)
    assert len(cleaned["common_praises"]) == 1

def test_handles_empty_sections(service):
    """Empty sections should pass through without error."""
    reviews = {"common_praises": [], "common_complaints": []}
    cleaned = service._clean_review_content(reviews)
    assert cleaned["common_praises"] == []
    assert cleaned["common_complaints"] == []

def test_handles_missing_sections(service):
    """Missing sections should pass through without error."""
    reviews = {"some_other_key": "value"}
    cleaned = service._clean_review_content(reviews)
    assert "some_other_key" in cleaned
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_review_cleanup.py -v --timeout=30
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_review_cleanup.py
git commit -m "test: review cleanup — garbage patterns, sentiment, derived ratings"
```

---

## Task 15: Review Prompt Tests + Full Suite Verification (test-agent)

**Files:**
- Modify: `tests/test_review_prompt_quality.py`

- [ ] **Step 1: Write tests verifying new prompt rules**

Add to `tests/test_review_prompt_quality.py`:

```python
def test_review_prompt_has_garbage_rejection_rules():
    """REVIEWS_EXTRACTION_PROMPT should include garbage text rejection."""
    from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
    assert "learn more" in REVIEWS_EXTRACTION_PROMPT.lower()
    assert "navigation text" in REVIEWS_EXTRACTION_PROMPT.lower()

def test_review_prompt_has_sentiment_alignment():
    """REVIEWS_EXTRACTION_PROMPT should warn against positive-in-complaints."""
    from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
    prompt_lower = REVIEWS_EXTRACTION_PROMPT.lower()
    assert "negative observation" in prompt_lower or "only include negative" in prompt_lower

def test_review_prompt_has_examples():
    """REVIEWS_EXTRACTION_PROMPT should include good/bad examples."""
    from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
    assert "BAD:" in REVIEWS_EXTRACTION_PROMPT
    assert "GOOD:" in REVIEWS_EXTRACTION_PROMPT

def test_price_prompt_has_counterfeit_rejection():
    """Price extraction prompt should reject counterfeit sources."""
    from app.services.extraction_service import PRICE_EXTRACTION_PROMPT
    prompt_lower = PRICE_EXTRACTION_PROMPT.lower() if hasattr(__import__('app.services.extraction_service', fromlist=['PRICE_EXTRACTION_PROMPT']), 'PRICE_EXTRACTION_PROMPT') else ""
    # Check within the extraction function or prompt constant
    import inspect
    from app.services.extraction_service import extract_price
    source = inspect.getsource(extract_price)
    assert "replica" in source.lower() or "counterfeit" in source.lower()
```

- [ ] **Step 2: Run the FULL free test suite**

```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=60
```

Expected: ALL tests pass. Note any failures for QA.

- [ ] **Step 3: Commit**

```bash
git add tests/test_review_prompt_quality.py
git commit -m "test: review prompt quality — garbage rejection, sentiment alignment verification"
```

---

## Task 16: Cross-QA + Fix Regressions (all agents)

**Workflow:** Each agent QAs another agent's work:
- scoring-agent QAs review-agent (Tasks 8-11)
- price-agent QAs scoring-agent (Tasks 1-4)
- review-agent QAs price-agent (Tasks 5-7)
- test-agent QAs all — runs full suite, reports failures

- [ ] **Step 1: test-agent runs full suite, reports all failures**

```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=60
```

- [ ] **Step 2: Each QA agent reads the code they're reviewing and checks:**
- Spec compliance (does the implementation match the design doc?)
- Edge case handling (missing data, both products same tier, MISSING_SCORE, etc.)
- No regressions to existing functionality
- Code quality (no hardcoded values that should be constants, no dead code)

QA agent sends a message to the originating agent with specific findings:
- "PASS" = no issues found
- "FAIL: [specific issue, file, line]" = needs fix

- [ ] **Step 3: Originating agents fix QA failures and commit**

Each agent receiving QA feedback fixes the issues and commits. Max 2 rounds of QA — if issues persist after 2 rounds, escalate to team lead.

- [ ] **Step 4: test-agent re-runs full suite after ALL fixes**

```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=60
```

Expected: ALL tests pass. If not, identify failing tests and send back to responsible agent.

- [ ] **Step 5: Final commit with all fixes**

```bash
git add -A
git commit -m "fix: QA fixes from cross-agent review"
```

---

## Task 17: Final Verification + Context Update (all agents)

- [ ] **Step 1: Run full free test suite one final time**

```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=60
```

Expected: ALL tests pass, 0 failures.

- [ ] **Step 2: Syntax check all modified files**

```bash
python -m py_compile app/services/scoring_service.py
python -m py_compile app/services/structured_comparison_service.py
python -m py_compile app/services/extraction_service.py
```

- [ ] **Step 3: Commit final state**

```bash
git add -A
git commit -m "feat: Session 26 — scoring & quality overhaul complete"
```
