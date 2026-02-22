# Fact-Checking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add zero-cost fact-checking via cross-validation and self-citation prompts

**Architecture:** Modify GPT prompts to require citations, then verify citations against actual search data. Cross-validate specs/prices/reviews against Serper Shopping data already fetched. Assemble a `fact_check` object per product.

**Tech Stack:** Python, GPT-4o-mini prompts, existing Serper Shopping data

---

## Agent A: Spec Fact-Checking

### Task 1: Modify spec extraction prompt to require citations

**Files:**
- Modify: `app/services/extraction_service.py:95-132` (`_build_specs_prompt()`)

**Changes:**
1. Add citation instruction to the prompt — for each spec field, GPT must also return a `_source` field indicating which search snippet (by index) the value came from, or `"training"` if from GPT's own knowledge.

2. Modify the prompt template to add after `CRITICAL RULES:`:
```
- For EACH spec field, also include a "{field}_source" field with the snippet number (e.g. "snippet_1") where you found this value, or "training" if from your own knowledge
- Example: "battery": "4422 mAh", "battery_source": "snippet_2"
```

3. Number the search snippets in `search_context` so GPT can reference them: prefix each snippet with `[snippet_N]`.

### Task 2: Add snippet numbering to search context

**Files:**
- Modify: `app/services/extraction_service.py` (where `search_context` is built)
- Also check: `app/services/structured_comparison_service.py` (where search results are passed to extraction)

**Changes:**
Number each search result snippet so GPT can cite them:
```python
# When building search_context from organic results
numbered_context = ""
for i, result in enumerate(search_results.get("organic", []), 1):
    numbered_context += f"[snippet_{i}] {result.get('title', '')} - {result.get('snippet', '')}\n"
```

This must happen in the function that formats search results into the context string passed to `_build_specs_prompt()`.

### Task 3: Verify citations after GPT returns specs

**Files:**
- Modify: `app/services/structured_comparison_service.py` (after `extract_specs()` returns, before storing in product dict)

**Changes:**
Add a `_verify_spec_citations()` method to `StructuredComparisonService`:
```python
def _verify_spec_citations(self, specs: Dict, search_snippets: List[str]) -> Dict[str, str]:
    """Verify GPT spec citations against actual search snippets.

    Returns dict mapping spec_field -> confidence:
      'verified': citation matches snippet text AND/OR cross-checks with shopping
      'likely': citation provided but can't cross-check
      'unverified': no citation or citation doesn't match
    """
    confidence = {}
    for key, value in specs.items():
        if key.endswith("_source") or key in ("brand", "model", "variant", "category"):
            continue
        source_key = f"{key}_source"
        source = specs.get(source_key)

        if not source or source == "training":
            confidence[key] = "unverified"
        elif source.startswith("snippet_"):
            # Verify the cited snippet actually contains related text
            try:
                idx = int(source.split("_")[1]) - 1
                if 0 <= idx < len(search_snippets):
                    snippet_text = search_snippets[idx].lower()
                    value_str = str(value).lower()
                    # Check if key terms from the value appear in the snippet
                    terms = [t for t in value_str.split() if len(t) > 2]
                    matches = sum(1 for t in terms if t in snippet_text)
                    confidence[key] = "verified" if matches >= len(terms) * 0.5 else "likely"
                else:
                    confidence[key] = "unverified"
            except (ValueError, IndexError):
                confidence[key] = "unverified"
        else:
            confidence[key] = "unverified"

    return confidence
```

### Task 4: Cross-validate specs against Serper Shopping titles

**Files:**
- Modify: `app/services/structured_comparison_service.py`

**Changes:**
Add `_cross_validate_specs_with_shopping()`:
```python
def _cross_validate_specs_with_shopping(self, specs: Dict, shopping_items: List[Dict]) -> Dict[str, str]:
    """Cross-check spec values against Serper Shopping product titles/descriptions.

    Upgrades 'likely' to 'verified' if shopping data confirms.
    Downgrades to 'flagged' if shopping data contradicts.
    """
    if not shopping_items:
        return {}

    # Combine all shopping titles into one searchable text
    shopping_text = " ".join(
        f"{item.get('title', '')} {item.get('description', '')}"
        for item in shopping_items
    ).lower()

    flags = {}
    # Check key spec fields that commonly appear in shopping titles
    checkable = ["storage", "ram", "display", "processor", "count", "dosage", "form"]
    for key in checkable:
        value = specs.get(key)
        if not value or value == "N/A":
            continue
        value_str = str(value).lower()
        # Extract numbers from spec value
        import re
        numbers = re.findall(r'\d+', value_str)
        if numbers:
            # Check if any key number appears in shopping text
            found = any(n in shopping_text for n in numbers if len(n) >= 2)
            if found:
                flags[key] = "verified"
            # Don't flag as contradicted unless we find a DIFFERENT number for same spec

    return flags
```

### Task 5: Strip `_source` fields from final specs, store confidence separately

**Files:**
- Modify: `app/services/structured_comparison_service.py` (in `_clean_specs()` or after it)

**Changes:**
After verification, strip all `_source` fields from specs (frontend doesn't need them) and store confidence in a separate dict:
```python
# After _verify_spec_citations and _cross_validate_specs_with_shopping
spec_confidence = {}
for key in list(specs.keys()):
    if key.endswith("_source"):
        del specs[key]
    elif key not in ("brand", "model", "variant", "category"):
        spec_confidence[key] = final_confidence.get(key, "unverified")

# Store for fact_check assembly
result["_spec_confidence"] = spec_confidence
```

---

## Agent B: Review + Price Fact-Checking

### Task 6: Preserve user_quotes source field in reviews

**Files:**
- Modify: `app/services/extraction_service.py:503-522` (`_normalize_review_response()`)

**Changes:**
The `user_quotes` field is already preserved (not dropped). However, ensure each quote dict has the `source` field defaulted:
```python
# In _normalize_review_response, after the existing defaults
quotes = data.get("user_quotes", [])
for quote in quotes:
    quote.setdefault("source", "unknown")
    quote.setdefault("sentiment", "mixed")
    quote.setdefault("aspect", "general")
data["user_quotes"] = quotes
```

### Task 7: Cross-validate review sentiment against Serper ratings

**Files:**
- Modify: `app/services/structured_comparison_service.py` (after reviews and ratings are both fetched, in Phase 2 assembly)

**Changes:**
Add `_verify_review_sentiment()`:
```python
def _verify_review_sentiment(self, reviews: Dict, source_ratings: List[Dict]) -> Dict:
    """Cross-check GPT review sentiment against real Serper ratings.

    Returns:
      sentiment_consistent: bool
      gpt_rating: float or None
      serper_avg_rating: float or None
      deviation: float or None
    """
    gpt_rating = reviews.get("average_rating")
    if not source_ratings or gpt_rating is None:
        return {"sentiment_consistent": None, "gpt_rating": gpt_rating, "serper_avg_rating": None, "deviation": None}

    # Calculate weighted average from source_ratings
    total_weight = 0
    weighted_sum = 0
    for sr in source_ratings:
        rating = sr.get("rating")
        count = sr.get("review_count", 1) or 1
        if rating and isinstance(rating, (int, float)):
            weighted_sum += rating * count
            total_weight += count

    if total_weight == 0:
        return {"sentiment_consistent": None, "gpt_rating": gpt_rating, "serper_avg_rating": None, "deviation": None}

    serper_avg = round(weighted_sum / total_weight, 2)
    deviation = abs(gpt_rating - serper_avg)
    consistent = deviation <= 0.8  # Allow 0.8 point tolerance

    return {
        "sentiment_consistent": consistent,
        "gpt_rating": gpt_rating,
        "serper_avg_rating": serper_avg,
        "deviation": round(deviation, 2)
    }
```

### Task 8: Price cross-check against Serper Shopping median

**Files:**
- Modify: `app/services/structured_comparison_service.py` (after price is finalized)

**Changes:**
Add `_verify_price()`:
```python
def _verify_price(self, price: Dict, shopping_items: List[Dict]) -> Dict:
    """Cross-check final price against Serper Shopping prices.

    Returns:
      price_verified: bool
      deviation_pct: float or None
      source_count: int
    """
    if not price or not shopping_items:
        return {"price_verified": price and not price.get("estimated", False), "deviation_pct": None, "source_count": 0}

    final_amount = price.get("amount")
    if not final_amount:
        return {"price_verified": False, "deviation_pct": None, "source_count": 0}

    # Collect valid prices from shopping items
    shopping_prices = []
    for item in shopping_items:
        p = item.get("price")
        if isinstance(p, (int, float)) and p > 0:
            shopping_prices.append(p)
        elif isinstance(p, str):
            import re
            nums = re.findall(r'[\d.]+', p.replace(',', ''))
            if nums:
                try:
                    shopping_prices.append(float(nums[0]))
                except ValueError:
                    pass

    if not shopping_prices:
        return {"price_verified": not price.get("estimated", False), "deviation_pct": None, "source_count": 0}

    median = sorted(shopping_prices)[len(shopping_prices) // 2]
    deviation_pct = abs(final_amount - median) / median * 100 if median > 0 else None

    return {
        "price_verified": deviation_pct is not None and deviation_pct <= 30 and not price.get("estimated", False),
        "deviation_pct": round(deviation_pct, 1) if deviation_pct else None,
        "source_count": len(shopping_prices)
    }
```

---

## Agent C: Response Assembly + Tests

### Task 9: Assemble `fact_check` object per product

**Files:**
- Modify: `app/services/structured_comparison_service.py` (in `_fetch_product_data()` or `compare_from_text()`, after all data is gathered)

**Changes:**
Add `_build_fact_check()` method and call it during product assembly:
```python
def _build_fact_check(self, product: Dict) -> Dict:
    """Assemble fact_check object from per-field verification results."""
    spec_confidence = product.pop("_spec_confidence", {})
    review_verification = product.pop("_review_verification", {})
    price_verification = product.pop("_price_verification", {})

    specs_verified = sum(1 for v in spec_confidence.values() if v == "verified")
    specs_likely = sum(1 for v in spec_confidence.values() if v == "likely")
    specs_flagged = sum(1 for v in spec_confidence.values() if v == "flagged")
    specs_unverified = sum(1 for v in spec_confidence.values() if v == "unverified")

    price_verified = price_verification.get("price_verified", False)
    sentiment_consistent = review_verification.get("sentiment_consistent")

    # Overall confidence
    if specs_flagged > 0 or (sentiment_consistent is False):
        overall = "low"
    elif specs_unverified > specs_verified + specs_likely:
        overall = "medium"
    elif price_verified and (sentiment_consistent is True or sentiment_consistent is None):
        overall = "high"
    else:
        overall = "medium"

    return {
        "specs_verified": specs_verified,
        "specs_likely": specs_likely,
        "specs_flagged": specs_flagged,
        "specs_unverified": specs_unverified,
        "price_verified": price_verified,
        "price_deviation_pct": price_verification.get("deviation_pct"),
        "review_sentiment_consistent": sentiment_consistent,
        "review_rating_deviation": review_verification.get("deviation"),
        "overall_confidence": overall
    }
```

Call it in the product assembly section (around line 303-444):
```python
product["fact_check"] = self._build_fact_check(product)
```

### Task 10: Write unit tests for all fact-checking logic

**Files:**
- Create: `tests/test_fact_checking.py`

**Tests:**
```python
# Spec citation verification
- test_verified_citation_matches_snippet
- test_unverified_when_no_citation
- test_unverified_when_training_source
- test_likely_when_partial_match

# Spec shopping cross-validation
- test_shopping_confirms_storage_spec
- test_no_shopping_returns_empty
- test_numbers_in_shopping_titles

# Review sentiment verification
- test_consistent_when_ratings_close
- test_inconsistent_when_ratings_diverge
- test_none_when_no_source_ratings

# Price verification
- test_verified_when_within_30pct
- test_not_verified_when_estimated
- test_not_verified_when_deviation_high

# fact_check assembly
- test_high_confidence_all_verified
- test_low_confidence_when_flagged
- test_medium_confidence_mixed
```

### Task 11: Integration — wire everything together

**Files:**
- Modify: `app/services/structured_comparison_service.py` (in `_fetch_product_data()`)

**Changes:**
Wire the verification calls into the existing data pipeline. After Phase 1 (specs + price) and Phase 2 (reviews + rating):

1. After specs are extracted, call `_verify_spec_citations()` and `_cross_validate_specs_with_shopping()`
2. After reviews are extracted, call `_verify_review_sentiment()`
3. After price is finalized, call `_verify_price()`
4. Store results as `_spec_confidence`, `_review_verification`, `_price_verification` on the product dict
5. Call `_build_fact_check()` during final assembly
6. Strip `_source` fields from specs

This must be done carefully to avoid breaking existing functionality. All verification is additive — it only ADDS the `fact_check` field, never modifies existing fields.

---

## Team Assignments

| Agent | Tasks | QAs |
|-------|-------|-----|
| Agent A | Tasks 1-5 (spec fact-checking) | Agent B's work |
| Agent B | Tasks 6-8 (review + price fact-checking) | Agent C's work |
| Agent C | Tasks 9-11 (assembly + tests + wiring) | Agent A's work |

## Success Criteria
- Every product in API response has a `fact_check` object
- Spec `_source` fields stripped from final response (not leaked to frontend)
- Review `user_quotes` have `source` field preserved
- All 120 existing tests pass
- New fact-checking unit tests pass
- Zero additional API calls (cost stays at ~$0.010)
- `python -m py_compile` passes for all modified files
