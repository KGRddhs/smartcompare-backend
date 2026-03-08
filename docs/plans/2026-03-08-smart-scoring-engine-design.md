# Smart Scoring Engine — Design Document

**Date:** 2026-03-08 (Session 20)
**Approach:** B — Smart Scoring Engine
**Goal:** Make comparisons faster, add explainable scoring, collect feedback, fix TS issues.

## Problem Statement

1. **Perceived latency** ~30s (likely cold starts + no streaming + sequential rendering)
2. **No explainable scoring** — GPT gives opinions, not reproducible numbers
3. **No feedback loop** — no way to know if recommendations are useful
4. **5 TS errors** + ResultsScreen type divergence from types.ts
5. **No event tracking** — can't measure success signals (saves, shares, clicks)

## Architecture Overview

```
Current:  query → parse → [specs+price || reviews+rating] → GPT verdict → response
Proposed: query → parse → [specs+price || reviews+rating] → SCORING → GPT verdict → SSE stream → feedback
                                                              ↑                                      ↓
                                                        deterministic                          Supabase events
                                                        (no API cost)                          (fire-and-forget)
```

### Key Principle: Separate Extraction from Scoring

- **GPT** extracts facts (specs, prices, reviews) — subjective, non-reproducible
- **Scoring service** computes numbers from structured data — deterministic, explainable
- **GPT verdict** receives scores as input, writes human-readable recommendation
- Scores are **reproducible**: same data + same preferences = same scores

## Component Design

### 1. Scoring Service (`app/services/scoring_service.py`)

Pure Python, zero API calls. Computes per-product scores from structured data.

**Input:** extracted specs, price, reviews, user preferences (optional)
**Output:** per-product scores with breakdown

#### Score Dimensions (6):
| Dimension | Source | Weight (default) |
|-----------|--------|-------------------|
| price_score | price.amount normalized vs competitor | 25% |
| spec_score | category-specific spec comparison | 25% |
| review_score | verified_rating + review sentiment | 20% |
| value_score | spec_score / price_score ratio | 15% |
| reliability_score | fact_check confidence + source count | 10% |
| popularity_score | review_count + source_ratings count | 5% |

#### Personalized Weights:
Preferences map to weight adjustments:
- `priority: "price"` → price_score weight +15%, spec_score -10%, value_score +5%
- `priority: "quality"` → spec_score +15%, review_score +5%, price_score -15%
- `priority: "brand_reputation"` → reliability_score +10%, popularity_score +10%, value_score -15%
- `budget: "budget"` → price_score +10%, value_score +10%, spec_score -10%
- `budget: "premium"` → spec_score +10%, review_score +5%, price_score -10%

Anonymous users get default weights. Multiple priorities stack (capped at 100% total).

#### Normalization:
- Prices: lower = better. `score = 1 - (price / max_price)` (0-1 range)
- Specs: category-specific. Electronics: higher RAM/storage = better. Grocery: lower sugar = better.
- Reviews: `score = rating / 5.0` (0-1 range)
- All scores normalized to 0-100 for display

#### Output Format:
```json
{
  "scores": {
    "product_1": {
      "overall": 78,
      "breakdown": {
        "price_score": 85,
        "spec_score": 72,
        "review_score": 80,
        "value_score": 90,
        "reliability_score": 65,
        "popularity_score": 70
      },
      "weights_used": {
        "price_score": 0.35,
        "spec_score": 0.20,
        "...": "..."
      }
    }
  },
  "winner_index": 0,
  "win_margin": 12,
  "scoring_method": "personalized"
}
```

### 2. SSE Streaming (`app/api/text_routes.py`)

Replace single JSON response with Server-Sent Events stream.

**Event sequence:**
1. `event: status` — "Parsing query..."
2. `event: status` — "Fetching specs and prices..."
3. `event: specs` — specs data for both products (Phase 1 complete)
4. `event: status` — "Analyzing reviews..."
5. `event: reviews` — review data for both products (Phase 2 complete)
6. `event: scores` — scoring breakdown (computed instantly after Phase 2)
7. `event: verdict` — GPT comparison + recommendation (streams as GPT generates)
8. `event: complete` — full response JSON (for caching/history)

**Fallback:** Keep existing `GET /api/v1/text/compare` as non-streaming endpoint. Add `GET /api/v1/text/compare/stream` for SSE. Or use `Accept: text/event-stream` header to switch.

**Frontend:** `EventSource` or fetch with `ReadableStream` in React Native. Progressive tab rendering — show Specs tab immediately when `specs` event arrives.

### 3. Feedback System

#### Backend:
- **Table:** `comparison_feedback` (user_id, comparison_id, useful bool, mattered_most text[], change_suggestion text, created_at)
- **Table:** `user_events` (user_id nullable, event_type, event_data JSONB, comparison_id, created_at)
- **Endpoints:** `POST /api/v1/feedback` (auth optional), event tracking via existing `log_search()` pattern
- Event types: `save`, `share`, `source_click`, `tab_switch`, `feedback_submit`, `result_view_duration`

#### Frontend:
- FeedbackCard component shown below results (not a separate page — reduces friction)
- 3 questions: "Was this useful?" (thumbs up/down), "What mattered most?" (multi-select chips from score dimensions), "What would you change?" (optional text)
- Event tracking: fire-and-forget on user interactions (tap rating source, switch tab, save comparison)

### 4. TypeScript Fixes

5 pre-existing errors:
1. `App.tsx(87,9)` — ResultsScreenProps type mismatch → fix navigation params
2. `CameraScreen.tsx(61,22)` — `pickFromGallery` hoisting → move function before usage
3. `ForgotPasswordScreen.tsx(18,10)` — Missing `requestPasswordReset` export → add to authService
4. `ResultsScreen.tsx(16,26)` — `@expo/vector-icons` import → fix import path

Plus: Remove all local type definitions from ResultsScreen.tsx [DONE in commit 454a07b], import from `types.ts` instead. Add new scoring types to `types.ts`.

## Latency Reduction Summary

| Layer | Change | Impact |
|-------|--------|--------|
| Perceived | SSE streaming + progressive rendering | First data in ~2s vs 4-5s wait |
| Actual | Score computation is instant (no API call) | +0ms (replaces GPT opinion with math) |
| Infrastructure | Health check ping every 5 min | Eliminates cold start (~10-20s) |
| Frontend | Show skeleton → specs → reviews → scores → verdict | Continuous visual progress |

## Real-time vs Async vs Precompute Split

| Data | Strategy | Rationale |
|------|----------|-----------|
| Specs | Cache 7d, fetch on miss | Specs rarely change |
| Prices | Cache 24h, fetch on miss | Daily price fluctuation |
| Reviews | Cache 7d, fetch on miss | Reviews accumulate slowly |
| Scores | Real-time compute | Depends on user preferences (personalized) |
| Verdict | Real-time stream | Depends on scores + preferences |
| Feedback | Async fire-and-forget | Non-blocking, like current logging |
| Events | Async fire-and-forget | Non-blocking telemetry |

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| SSE not supported in React Native Expo | Medium | Use fetch + ReadableStream instead of EventSource; test on both platforms |
| Score normalization edge cases (missing data) | Low | Default to 50/100 for missing dimensions, flag in response |
| Feedback fatigue (users ignore feedback card) | Low | Make it optional, 1-tap minimum (thumbs up/down), show only after 2nd comparison |
| Rate limits with agent teams during implementation | High | 2 agents per phase, checkpoint files, sequential not parallel phases |

## What We're NOT Building (YAGNI)

- ML prediction models (no user volume yet)
- Warranty data scraping (no reliable source)
- YouTube/social sentiment analysis (high latency, low ROI)
- A/B testing infrastructure (premature)
- Real-time price alerts (different product)
- Precomputation pipeline (comparisons are dynamic)

## Success Criteria

1. First data visible in <2.5s (streaming)
2. Full comparison in <6s (same or better than current)
3. Scoring produces identical results for identical inputs (deterministic)
4. 80%+ test coverage on new code
5. Zero new TS errors (fix existing 5)
6. Feedback collection rate >10% of comparisons (after launch)
