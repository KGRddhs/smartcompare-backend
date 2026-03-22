# Personalization & AI Model Redesign — Design Spec

**Date:** 2026-03-22
**Status:** Approved
**Approach:** Full Vision (A+B) — Restructured AI model + behavioral learning + adaptive personalization

---

## Problem Statement

User survey findings reveal five critical pain points:

1. **Reviews scare users** — fragmented lists with conflicting individual voices erode trust
2. **Too much time comparing** — results need to be quick, concise, distraction-free
3. **Bias fear** — users want a clear winner but don't want the decision made for them
4. **Trust deficit** — fear of buying the wrong product and experiencing buyer's remorse
5. **Personalization gap** — different users have different priorities; one-size-fits-all doesn't work

### Design Principles (from survey)

- **Cut to the chase** — no walls of text, no distractions
- **Lower hesitance, not add information** — we're solving a problem, not writing a report
- **Show the winner without bias** — transparent reasoning, not selling
- **Build trust through integrity** — explain why, show tradeoffs, show data confidence
- **Personalization flavors, not overrides** — preferences influence but don't override objective data

---

## Section 1: Restructured Verdict (AI Model)

### Current State
GPT generates a free-form 2-3 sentence recommendation + separate `key_differences[]` list + separate `best_for` grid. Pros/cons generated in the same call but feel disconnected.

### New Structured Verdict Format

GPT outputs these fields with strict constraints:

```json
{
  "winner_declaration": "iPhone 15 Pro",
  "winner_reason": "Stronger specs across 4 of 6 dimensions at a similar price",
  "key_tradeoff": "Galaxy S24 has a brighter display (+18%) and longer software support",
  "value_context": "You get flagship specs at 12% below the category average",
  "best_for": {
    "product_0": "Best if you prioritize camera quality and ecosystem integration",
    "product_1": "Best if you want the best display and longer update support"
  },
  "product_0_pros": ["A16 chip benchmarks 22% faster", "48MP camera with 5x optical zoom", ...],
  "product_0_cons": ["Heavier at 221g vs 195g", "No charger in box", ...],
  "product_1_pros": [...],
  "product_1_cons": [...]
}
```

### Key Changes
- **No free-form paragraphs** — every field has a purpose and max length
- `winner_reason`: ONE sentence, under 20 words
- `key_tradeoff`: explicitly names the losing product's strongest advantage
- `value_badge`: deterministic from scoring (NOT GPT-generated) — GPT only writes `value_context`
- `best_for`: personalization-aware — if logged in, references user priorities ("Best if you prioritize camera quality — **which you do**")
- `confidence`: deterministic from existing data (NOT GPT-generated)
- Pros/cons: 4-6 pros, 2-4 cons per product, each MUST include a specific number/fact

### Prompt Changes
- Temperature stays 0.2 (low creativity)
- Scoring context injection stays (GPT must align with scores)
- New constraint: "Your winner_reason must be ONE sentence under 20 words"
- New constraint: "key_tradeoff must name the losing product's strongest advantage"
- Personalized `best_for`: if user preferences exist, append "(which you do)" or "(which aligns with your priorities)" where applicable

### Files Modified
- `app/services/extraction_service.py`: `COMPARISON_PROMPT`, `generate_comparison()`

---

## Section 2: Restructured Reviews (AI Model)

### Current State
GPT extracts fragmented data: `common_praises[]`, `common_complaints[]`, `detailed_praises[]`, `detailed_complaints[]`, `user_quotes[]`, `summary`. Individual attributions like "Per reddit.com:" appear. Users find this noisy and trust-eroding.

### New Review Output Format

```json
{
  "review_summary": {
    "overall_sentiment": "positive",
    "consensus": "Most users praise the battery life and camera quality. Build quality is consistently rated excellent. The main criticism is the price increase over last generation.",
    "highlights": [
      { "point": "Battery easily lasts 2 full days of heavy use", "sentiment": "positive" },
      { "point": "Camera night mode is best-in-class", "sentiment": "positive" },
      { "point": "Noticeable price jump from previous model", "sentiment": "negative" },
      { "point": "Heavier than competitors at 221g", "sentiment": "negative" }
    ],
    "review_volume": "high",
    "agreement_level": "strong"
  }
}
```

### Key Changes
- **No individual voices** — no "Ali said" or "Per reddit.com:". Consensus is the voice.
- **`consensus`**: 2-3 sentence paragraph that reads like a professional product brief
- **`highlights`**: clean bullet-ready points with sentiment tags, no citation prefixes
- **`review_volume`**: high (500+), moderate (50-500), low (10-50), minimal (<10) — trust signal
- **`agreement_level`**: strong/moderate/divided — if "divided", consensus paragraph explains the split
- **Dropped**: `detailed_praises`, `detailed_complaints`, `user_quotes`, `category_scores` — added noise without building trust
- **Kept internally**: `average_rating` and source citations still extracted for fact-checking backend logic, not exposed in review UI structure

### Prompt Changes
- "Write as if you are a professional product analyst summarizing findings for a buyer"
- "Never attribute to individual users or websites"
- "If reviewers disagree, state both sides neutrally"
- Sentiment alignment rules stay (positive can't appear in negative highlights)

### Files Modified
- `app/services/extraction_service.py`: `REVIEWS_EXTRACTION_PROMPT`, `extract_reviews()`, `_normalize_review_response()`
- `app/services/structured_comparison_service.py`: review post-processing pipeline

---

## Section 3: Scoring Service Additions (Deterministic, $0)

All additions are pure math — zero API calls.

### Value Badges

Deterministic mapping from `value_score` + `price_tier`:

| Condition | Badge |
|-----------|-------|
| value_score >= 75 AND tier != "luxury" | `great_value` |
| value_score >= 75 AND tier == "luxury" | `fair_price` |
| value_score 50-74 | `fair_price` |
| value_score 25-49 | `premium_price` |
| value_score < 25 | `overpriced` |

Returned per product: `product.value_badge`

### Tradeoff Pairs

Built from existing `dimension_winners`. For each dimension where Product A wins, pair with Product B's strongest winning dimension:

```json
{
  "tradeoffs": [
    {
      "winner_wins": { "dimension": "battery", "product": "iPhone 15 Pro", "margin": "+40%" },
      "loser_wins": { "dimension": "display", "product": "Galaxy S24", "margin": "+18%" }
    }
  ]
}
```

- Only include dimensions where margin > 5%
- Max 3 tradeoff pairs (most impactful)

### Confidence Indicators

Assembled from existing data:

```json
{
  "confidence": {
    "price": {
      "source_count": 3,
      "method": "retailer_verified | converted | estimated",
      "freshness": "live | cached_24h | cached_7d"
    },
    "rating": {
      "review_count": 1247,
      "source": "Amazon",
      "verified": true
    },
    "specs": {
      "verified_pct": 85,
      "citation_count": 12
    },
    "overall": "high | medium | low"
  }
}
```

`overall`: high = all three strong, medium = one weak, low = two+ weak.

### Files Modified
- `app/services/scoring_service.py`: `compute_value_badge()`, `compute_tradeoff_pairs()`, `compute_confidence()`

---

## Section 4: Behavioral Learning System

### Three-Layer Personalization Stack

#### Layer 1: Explicit Preferences (existing, enhanced)
Same 4 dimensions (priorities, budget, lifestyle, brand_attitude). Enhancement: `best_for` line in verdicts references these directly.

#### Layer 2: Behavioral Profile (new)

JSONB column on `users` table: `behavior_profile`

```json
{
  "category_affinity": {
    "electronics": 0.45,
    "fragrances": 0.30,
    "fashion": 0.25
  },
  "price_range_preference": {
    "avg_price_viewed": 85.5,
    "tier_distribution": { "budget": 0.1, "mid": 0.5, "premium": 0.3, "luxury": 0.1 }
  },
  "winner_agreement": {
    "agreed": 14,
    "disagreed": 3,
    "agreement_rate": 0.82
  },
  "dimension_sensitivity": {
    "spec_score": 0.35,
    "price_score": 0.25,
    "review_score": 0.20
  },
  "comparison_count": 17,
  "last_updated": "2026-03-22T..."
}
```

**Data sources (all existing):**
- `category_affinity` — from `comparisons` table (count per category)
- `price_range_preference` — from comparison result prices
- `winner_agreement` — from `comparison_feedback`. Current schema has `useful` (boolean) — interpret `useful=true` as agreed with winner, `useful=false` as disagreed. No new feedback signal needed.
- `dimension_sensitivity` — from `user_events` tab dwell patterns. Formula: normalize dwell time per tab proportionally (e.g., specs 8000ms out of 13000ms total = 0.62 → maps to `spec_score` weight affinity). Only tabs with >2s dwell count.
- Recalculated after each comparison via `update_behavior_profile()`

#### Layer 3: In-Session Signals (new)

Tracked within a single comparison session via existing `user_events`:

```json
{
  "first_tab_viewed": "specs",
  "tab_dwell_ms": { "overview": 3000, "specs": 8000, "reviews": 2000 },
  "price_checked_first": true,
  "shared_result": false,
  "feedback_given": "positive"
}
```

Read back on the next comparison to slightly adjust weights.

### Weight Resolution (priority order)

```
1. Explicit preferences   → max ±30% shift (user said it directly)
2. Behavioral profile     → max ±10% shift (inferred from patterns)
3. In-session signals     → max ±5% shift  (single session, might be noise)
4. Category defaults      → fallback
```

```python
final_weights = category_weights.copy()
apply_explicit_preferences(final_weights, user.preferences)    # max ±30%
apply_behavioral_adjustments(final_weights, user.behavior_profile)  # max ±10%
apply_session_signals(final_weights, session_signals)           # max ±5%
normalize(final_weights)  # sum to 1.0
```

Total max shift from category defaults: ~45% — still grounded in category logic.

### Behavioral Decay
- 30-day half-life using exponential decay: `weight = 0.5 ^ (days_ago / 30)`
- Applied at read-time when aggregating (not at write-time), so raw data is preserved
- A comparison from 60 days ago: `0.5 ^ (60/30) = 0.25` (25% weight)
- Prevents stale behavior from dominating if preferences change

### Files Modified/Created
- `app/services/scoring_service.py`: `apply_behavioral_adjustments()`, `apply_session_signals()`
- `app/services/behavior_service.py` (new): `update_behavior_profile()`, `get_behavior_profile()`, `compute_session_signals()`
- Supabase migration: add `behavior_profile JSONB` column to `users` table

---

## Section 5: API Response Restructure

### Current State
Flat blob — comparison data, scoring, products, reviews, personalization all mixed. Frontend picks through it.

### New Structure (organized by screen purpose)

```json
{
  "query": "iPhone 15 Pro vs Galaxy S24",
  "category": "electronics",
  "category_switched": false,

  "overview": {
    "winner": {
      "product_index": 0,
      "name": "iPhone 15 Pro",
      "declaration": "iPhone 15 Pro",
      "reason": "Stronger specs across 4 of 6 dimensions at a similar price",
      "key_tradeoff": "Galaxy S24 has a brighter display (+18%) and longer software support",
      "margin": 8.5
    },
    "products": [
      {
        "brand": "Apple",
        "name": "iPhone 15 Pro",
        "price": { "amount": 349.9, "currency": "BHD", "retailer": "Amazon", "source_method": "local_bhd" },
        "rating": 4.6,
        "review_count": 1247,
        "overall_score": 78.3,
        "value_badge": "great_value",
        "value_context": "Flagship specs at 12% below category average",
        "pros": ["A16 chip benchmarks 22% faster", "48MP camera with 5x optical zoom"],
        "cons": ["Heavier at 221g vs 195g", "No charger in box"],
        "best_for": "Best if you prioritize camera quality and ecosystem integration"
      }
    ],
    "tradeoffs": [
      {
        "winner_wins": { "dimension": "camera", "product": "iPhone 15 Pro", "margin": "+40%" },
        "loser_wins": { "dimension": "display", "product": "Galaxy S24", "margin": "+18%" }
      }
    ],
    "confidence": {
      "price": { "source_count": 3, "method": "retailer_verified" },
      "rating": { "review_count": 1247, "source": "Amazon", "verified": true },
      "specs": { "verified_pct": 85, "citation_count": 12 },
      "overall": "high"
    }
  },

  "specs": {
    "products": [
      {
        "brand": "Apple",
        "name": "iPhone 15 Pro",
        "specs": { "processor": "A17 Pro", "ram": "8GB" },
        "spec_advantages": ["22% faster processor", "5x optical zoom vs 3x"]
      }
    ],
    "specs_comparison": {}
  },

  "reviews": {
    "products": [
      {
        "brand": "Apple",
        "name": "iPhone 15 Pro",
        "rating": 4.6,
        "review_count": 1247,
        "rating_source": { "name": "Amazon", "url": "..." },
        "review_summary": {
          "overall_sentiment": "positive",
          "consensus": "Most users praise the camera and battery life...",
          "highlights": [
            { "point": "Battery easily lasts 2 full days", "sentiment": "positive" },
            { "point": "Noticeable price jump from previous model", "sentiment": "negative" }
          ],
          "review_volume": "high",
          "agreement_level": "strong"
        }
      }
    ]
  },

  "scoring": {
    "scores": {},
    "dimension_winners": {},
    "price_tiers": {},
    "is_cross_tier": false,
    "scoring_method": "personalized",
    "category_weights": {}
  },

  "personalization": {
    "personalized": true,
    "factors": ["priority_quality", "budget_mid", "lifestyle_tech_enthusiast"],
    "behavior_influence": {
      "category_affinity": "electronics",
      "agreement_rate": 0.82,
      "weight_adjustments": { "spec_score": "+8%", "price_score": "-3%" }
    }
  },

  "metadata": {
    "elapsed_ms": 7200,
    "api_calls": 4,
    "total_cost": 0.0098,
    "cached": false,
    "fact_check": {}
  }
}
```

### Key Structural Changes
- **`overview`** — everything the first screen needs, no digging
- **`specs`** and **`reviews`** — self-contained per-tab payloads
- **`scoring`** — separate (power users / debug), not mixed into overview
- **`personalization`** — clearly shows what was applied including behavioral influence
- **`metadata`** — debug/cost info separated from main result

### Backward Compatibility
- Old fields (`comparison.recommendation`, `comparison.key_differences`) kept as aliases during migration, then removed.
- Review fields (`detailed_praises`, `detailed_complaints`, `user_quotes`) are dropped in the new format. Since frontend is updated simultaneously and old stored comparisons in history are served as-is (stored blobs), no backward compat shim needed — history displays whatever format was stored at comparison time.
- `specs_comparison` field preserved from current implementation (populated by GPT `generate_comparison()` call). Not restructured in this spec.

### Files Modified
- `app/services/structured_comparison_service.py`: response assembly in `compare_from_text()` and `compare_from_text_streaming()`
- `app/routes/text_routes.py`: response serialization

---

## Section 6: SSE Streaming Updates

### New Event Flow (same 10 events, enriched data)

```
Event 1:  status   → { "step": "parsing", "progress": 10 }
Event 2:  status   → { "step": "fetching", "progress": 20 }
Event 3:  specs    → { "specs": { products: [...] } }
Event 4:  prices   → { "overview": { products: [{ price, value_badge, value_context }] } }
Event 5:  status   → { "step": "reviews", "progress": 50 }
Event 6:  reviews  → { "reviews": { products: [...] } }
Event 7:  scores   → { "scoring": {...}, "confidence": {...} }
Event 8:  status   → { "step": "verdict", "progress": 80 }
Event 9:  verdict  → { "overview": { winner, tradeoffs, pros, cons, best_for } }
Event 10: complete → Full response (canonical, overwrites partial state)
```

### Changes
- **`progress` percentage** on status events — enables real progress bar
- **Prices event** includes `value_badge` and `value_context` (deterministic)
- **Reviews event** delivers new `review_summary` format
- **Scores event** includes `confidence` indicators
- **Verdict event** delivers structured verdict (not free-form text)
- **Complete event** stays as canonical full response

### Progressive Rendering
- Specs tab usable at ~3s
- Prices visible at ~4s
- Reviews tab usable at ~6s
- Full verdict at ~8s

### Files Modified
- `app/services/structured_comparison_service.py`: streaming generator
- `SmartCompareApp/src/services/api.ts`: `streamComparison()` event handling

---

## Section 7: Implementation Team Structure

### Team: 4 Opus Agents

| Agent | Primary Work | QA Target |
|-------|-------------|-----------|
| **backend-ai** | Verdict prompt, review prompt, extraction_service.py | QAs **backend-scoring** |
| **backend-scoring** | Value badges, tradeoffs, confidence, behavioral profile in scoring_service.py | QAs **backend-ai** |
| **backend-api** | Response restructure, SSE streaming, behavioral service, DB schema. **Sole owner of `structured_comparison_service.py`** — backend-scoring only modifies `scoring_service.py`. | QAs **frontend** |
| **frontend** | ResultsScreen (Overview/Specs/Reviews), streaming consumption, progressive rendering | QAs **backend-api** |

### Workflow Rules
1. **Delegation**: Each agent owns their files — no two agents edit the same file
2. **Cross-QA**: When finished, QA the assigned target. Subpar or incomplete work gets sent back with specific issues.
3. **Idle time**: Write red-green tests targeting 80%+ coverage while waiting for QA
4. **No disassembly until**: All 4 agents confirm their QA target passes. Every agent must sign off.
5. **Feature completeness**: 100% of this design must be implemented — no partial shipping

### Dependency Order

```
Phase 1 (parallel):
  - backend-scoring: value badges, tradeoffs, confidence
  - backend-ai: verdict prompt + review prompt

Phase 2 (after Phase 1):
  - backend-api: response restructure + behavioral learning
  - frontend: type definitions + skeleton (parallel with backend-api)

Phase 3 (after Phase 2):
  - backend-api + frontend: integration + SSE streaming
  - Cross-QA round begins

Phase 4:
  - All agents: QA + test coverage → 80%+
  - Fix QA rejections
  - Final sign-off from all 4
```

---

## Cost Impact

| Component | API Cost | Infrastructure Cost |
|-----------|---------|-------------------|
| Verdict prompt restructure | $0 (same GPT call, different format) | None |
| Review prompt restructure | $0 (same GPT call, different format) | None |
| Value badges | $0 (deterministic math) | None |
| Tradeoff pairs | $0 (deterministic math) | None |
| Confidence indicators | $0 (assembled from existing data) | None |
| Behavioral profile | $0 (Supabase reads/writes) | Negligible storage |
| In-session signals | $0 (existing event tracking) | None |
| Response restructure | $0 (same data, different shape) | None |
| **Total** | **$0 additional** | **~0** |

Target comparison cost stays at ~$0.010.

---

## Files Inventory

### Modified
- `app/services/extraction_service.py` — verdict + review prompts, output parsing
- `app/services/scoring_service.py` — value badges, tradeoffs, confidence, behavioral weight adjustments
- `app/services/structured_comparison_service.py` — response assembly, SSE events, behavioral profile trigger
- `app/routes/text_routes.py` — response serialization
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — overview/specs/reviews restructure
- `SmartCompareApp/src/services/api.ts` — streaming event handling, type updates

### New
- `app/services/behavior_service.py` — behavioral profile CRUD, session signal computation, decay logic

### Database
- Supabase migration: `ALTER TABLE users ADD COLUMN behavior_profile JSONB DEFAULT '{}'`
