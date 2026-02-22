# Fact-Checking & Data Accuracy Design

**Date**: 2026-02-22
**Status**: Approved
**Cost**: $0 extra (built into existing API calls)

## Goal

Add a fact-checking system that cross-validates GPT-extracted data against real sources we already fetch. Every data point gets a confidence tag (verified/likely/unverified). Zero additional API calls.

## Approach

Combine two strategies:
- **Cross-validation (A)**: Use Serper Shopping data we already have to validate GPT outputs
- **Self-citation (B)**: Modify GPT prompts to require citations, then verify citations match actual search snippets

## Design

### 1. Spec Fact-Checking

**Prompt changes**: Modify spec extraction prompt to require GPT to cite which search snippet each spec came from. Each spec field gets a `_source` companion:
```json
{
  "battery": "4422 mAh",
  "battery_source": "snippet_3",
  "processor": "A16 Bionic",
  "processor_source": "snippet_1"
}
```

**Cross-validation**: After GPT returns specs, validate against Serper Shopping data:
- Shopping titles often contain key specs (storage, RAM, screen size)
- Shopping descriptions contain specs too
- If GPT says "256GB" but shopping titles say "128GB", flag it

**Confidence tags per spec field**:
- `verified` — GPT citation matches actual search snippet AND cross-checks with shopping data
- `likely` — GPT cited a snippet but no shopping data to cross-check
- `unverified` — no citation or citation doesn't match

### 2. Review Fact-Checking

**Prompt fix**: `_normalize_review_response()` currently drops the `source` field from user quotes. Fix it to preserve source attribution.

**Cross-validation**: Compare GPT's `average_rating` against real `source_ratings` from Serper Shopping:
- If GPT says 4.8 but Serper retailers average 3.5, flag review sentiment as inconsistent
- Add `sentiment_verified` boolean

### 3. Price Fact-Checking

Already mostly implemented (`estimated: true` flag). Add one cross-check:
- If Serper Shopping has multiple prices, compare GPT Tier 2 price against Serper median
- Flag if deviation > 30%

### 4. Response Structure

Add `fact_check` object per product in API response:
```json
{
  "fact_check": {
    "specs_verified": 8,
    "specs_flagged": 1,
    "specs_unverified": 2,
    "price_verified": true,
    "review_sentiment_consistent": true,
    "overall_confidence": "high"
  }
}
```

`overall_confidence` logic:
- `high` — all specs verified/likely, price verified, sentiment consistent
- `medium` — some specs unverified OR price estimated OR minor sentiment mismatch
- `low` — specs flagged (contradictions found) OR price wildly off OR sentiment inconsistent

## What's Already Implemented (no changes needed)
- Price `estimated: true` flag (Tier 3)
- Rating `extract_method` + `confidence` (high/medium/low)
- Rating `verified` vs `unverified`
- `rating_source` with name, url, method
- Aggregate `source_ratings` per retailer
- Data freshness indicator

## Files to Modify
- `app/services/extraction_service.py` — GPT prompts (add citation requirement), `_normalize_review_response()` (preserve source)
- `app/services/structured_comparison_service.py` — cross-validation logic, `fact_check` object assembly, price cross-check
- `app/api/text_routes.py` — include `fact_check` in response (if not auto-included)

## Team Structure

3 Opus agents with cross-QA:

| Agent | Owns | QAs |
|-------|------|-----|
| Agent A | Spec fact-checking (prompt + cross-validation + confidence tags) | Agent B's work |
| Agent B | Review fact-checking (preserve source, sentiment cross-validation) + Price cross-check | Agent C's work |
| Agent C | Response structure (`fact_check` object assembly, overall_confidence logic) + Tests | Agent A's work |

## Success Criteria
- All specs have confidence tags (verified/likely/unverified)
- GPT citations verified against actual search snippets
- Review sentiment cross-checked against Serper ratings
- Price cross-check flags >30% deviations
- `fact_check` object in every API response
- Zero additional API calls (cost stays at ~$0.010)
- All existing 120 tests still pass
- New unit tests for fact-checking logic
