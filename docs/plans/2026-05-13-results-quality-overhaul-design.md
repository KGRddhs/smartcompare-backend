# Bundle E — Results Quality Overhaul + Scatter-Gather Pipeline

**Status:** Design approved, awaiting implementation plan
**Date:** 2026-05-13
**Owner:** Ahmed
**Brand:** Qaren (قارن)
**Predecessor:** Bundle B/C/D (merged 2026-05-12, PR #4)

---

## Problem Statement

End-to-end tester walkthrough of "Glorious Model O mouse vs Ducky One 2 Mini keyboard" surfaced 9 distinct quality issues that compound into a single bad impression: **the result feels untrustworthy, slow, and apologetic.**

Observed:

| # | Symptom | Root cause |
|---|---|---|
| 1 | 84.5s end-to-end | Sequential scraper tiers + 30s Firecrawl timeout fires only after curl_cffi fails |
| 2 | "Low confidence data" pill shown by default | `fact_check.overall_confidence` rendered without context, framed apologetically |
| 3 | Scores panel: Price / Specs / Popularity bars empty | `scoring_service.CATEGORY_DIMENSIONS` emits category-specific keys; frontend hardcodes universal labels — labels mismatch → 0-width bars |
| 4 | "Why we picked this — wins with higher value score of 82.0" | GPT verdict parrots an internal score number that means nothing to the user |
| 5 | "Best Pick" badge | Evaluative endorsement — exposes Qaren to false-endorsement claims under GCC consumer law |
| 6 | "What's next?" button → NAVIGATE error | `navigation.navigate('Home')` — route doesn't exist; tab is `'HomeTab'` |
| 7 | "Save" button | Redundant with auto-save to History; adds visual noise + decision fatigue |
| 8 | History tap → white screen + render error `Cannot read property 'comparison_id' of undefined` | `ResultsScreen.tsx:210` — `(result as any).comparison_id` missing optional chaining |
| 9 | Cross-category comparison (mouse vs keyboard) allowed but produced garbage | Architecture is correct (we want compare-anything) — symptoms above are the failure |

The "compare anything" feature is correct. The fix is to make Results never expose missing/simulated/apologetic data — regardless of what the user compares.

---

## Design Principles (locked)

1. **Compare-anything stays.** Users can compare any two products. The work is to make Results always look complete and honest.
2. **No empty bars, no simulated numbers, no apologetic copy.** If we can't compute it, we don't render the row. If we can compute it, the number is real.
3. **Positivity in calibration, honesty in math.** A product on a real retailer shelf with 4.0 stars is objectively good. Showing 64/100 is bad calibration, not honesty. Re-baseline to 70+.
4. **Legally safe framing.** Qaren never claims a product *is* better. It presents facts, attributes opinions to sources, and matches data to user-stated priorities. The user picks.
5. **No missing pieces.** Fan-out beats fallback chains. Every scraper fires at T=0, in parallel. Settle window swaps in higher-trust data after first paint. User always sees a complete result.
6. **≤15s perceived latency.** First paint at ≤13s. Settle window upgrades silently to 25s. Hard cap at 25s.

---

## Decision 1 — History crash + dead routes (P0 bug fixes)

### 1a. History → Results crash

`SmartCompareApp/src/screens/ResultsScreen.tsx:210`:

```ts
// Before
const sharableComparisonId =
  (result as any).comparison_id || (metadata as any)?.comparison_id;

// After
const sharableComparisonId =
  (result as any)?.comparison_id || (metadata as any)?.comparison_id;
```

Add a defensive early-return at the top of the component when `result` is undefined — render an empty-state card with a "Back to history" CTA rather than crashing.

### 1b. "What's next?" NAVIGATE error

Removed entirely per Decision 6. No route fix needed.

---

## Decision 2 — Backend `dimensions[]` contract

Replace category-specific dimension keys with a self-describing array. Backend decides what's scoreable for each comparison pair; frontend renders whatever it receives, in order.

### Response shape

```jsonc
{
  "scoring": {
    "overall_score": {
      "product_a": 87,        // calibrated 70-95 range (Decision 4)
      "product_b": 82
    },
    "win_margin": 5,
    "dimensions": [           // ordered, frontend renders top to bottom
      {
        "key": "price",
        "label": "Price",
        "score_a": 88,
        "score_b": 72,
        "delta_text": "BHD 30 less",      // factual, no superlatives
        "confidence": "high",
        "is_core": true                    // shown on hero card
      },
      {
        "key": "reviews",
        "label": "Reviews",
        "score_a": 82,
        "score_b": 78,
        "delta_text": "0.2★ higher",
        "confidence": "high",
        "is_core": true
      },
      {
        "key": "value",
        "label": "Value",
        "score_a": 90,
        "score_b": 76,
        "delta_text": "Better ratio of features to cost",
        "confidence": "high",
        "is_core": true
      },
      {
        "key": "build_quality",
        "label": "Build",
        "score_a": 80,
        "score_b": 88,
        "delta_text": "PBT keycaps, metal frame",
        "confidence": "medium",
        "is_core": false
      }
      // 0-3 contextual extras follow
    ]
  }
}
```

### Contract guarantees

- **Always 3 core dimensions** (`is_core: true`): Price, Reviews, Value.
  - Every product has a price (or `estimated`), every product can be reviewed (or marked "limited reviews"), Value is deterministic from the other two.
- **0-3 contextual dimensions** (`is_core: false`), added when meaningful:
  - **Build/Reliability** — when brand reputation + warranty signals exist on BOTH products
  - **Popularity** — when review_count > 50 on BOTH products
  - **Category-specific** — DPI for mice, RGB for keyboards, etc. — only when BOTH products have the spec
- **A dimension is never emitted if either product lacks the data.** No empty bars. Ever.
- **`delta_text`** is the only string surface for that row in copy — backend phrases it factually, no evaluative words.
- **`confidence`** values: `high` (2+ sources agree within 5%), `medium` (single trusted source), `low` (estimate or unverified). Frontend renders a subtle dot — never an apologetic banner.

### Backward compatibility

- Old clients reading legacy keys (`price_score`, `spec_score`, etc.) keep working — backend continues to emit them ALONGSIDE the new `dimensions[]` for one release cycle.
- After App Store accepts v1.1 (Bundle E), remove legacy keys in Bundle F.

---

## Decision 3 — Hero rings + bars layout

### Anatomy of the new Results "answer" card

```
┌─────────────────────────────────────────────────┐
│  Top match                          [share icon]│
│                                                 │
│  ╭───────╮       vs       ╭───────╮             │
│  │  87   │                │  82   │             │
│  │ ring  │                │ ring  │             │
│  ╰───────╯                ╰───────╯             │
│  Glorious                  Ducky                │
│  Model O                   One 2 Mini           │
│                                                 │
│  BHD 30 less, 0.2★ higher, 12g lighter          │
│                                                 │
│  ▰▰▰▰▰▰▰▱▱▱  Price          ▰▰▰▰▰▱▱▱▱▱         │
│  ▰▰▰▰▰▰▱▱▱▱  Reviews        ▰▰▰▰▰▰▱▱▱▱         │
│  ▰▰▰▰▰▰▰▰▱▱  Value          ▰▰▰▰▰▰▱▱▱▱         │
│  ▰▰▰▰▰▰▱▱▱▱  Build          ▰▰▰▰▰▰▰▰▱▱         │
└─────────────────────────────────────────────────┘
```

### Rings

- **Two SVG radial rings, side by side.** Each shows the product's overall calibrated score (70-95 range).
- **Emerald fill on the top-match ring** (whichever score is higher). Neutral gray fill on the other — **never orange or red**. Orange/red on a score is psychological poison.
- **Stroke width 8px, diameter 88px** on phone width.
- **Animated fill** from 0 → score on reveal (Reanimated worklet, 600ms ease-out, fires after the ~3.2s loading sequence).
- **Center label:** the number, then `/100` in a smaller weight below.
- **No adjective labels** ("Great", "Excellent") — number stands alone.

### Top-match badge

- One word: **"Top match"** (English) / **"الأنسب لك"** (Arabic). Pill above the higher-scoring ring.
- Emerald background, white text. No trophy icon (too "winner-y").

### Delta line

- Single line under both rings: `"BHD 30 less, 0.2★ higher, 12g lighter"`.
- Pulled directly from `dimensions[].delta_text` for the top 3 core dimensions where the top-match wins.
- If top-match wins on fewer than 3 dimensions, show what it has — minimum 1.

### Dimension bars (below rings)

- One row per dimension from `dimensions[]` (3-6 rows total).
- Two horizontal bars per row (one per product, left-and-right with the product's column above).
- Bar color: **emerald for higher score, neutral gray for lower** — never orange.
- Label on the left in Inter Medium, score number on the right in tabular figures.
- `confidence: "low"` dimensions: bar opacity 0.6 + small gray "≈" prefix on the score number. No banner.

### Removed visual elements

- The current "Best Pick" trophy badge → replaced with "Top match" pill.
- The "Low confidence data" red pill at the top → deleted entirely (see Decision 7).
- The "Why we picked this" subtitle text → replaced with "How they compare" (see Decision 5).
- The "Default weights applied" footer text → deleted (it's confusing and unnecessary).
- "Save" button at bottom → deleted (Decision 6).
- "What's next?" button at bottom → deleted (Decision 6).
- "Share" button stays, repositioned to the top-right of the hero card as an icon.

---

## Decision 4 — Honest score re-calibration (70+ baseline)

### The current problem

`scoring_service.py` outputs 0-100 with an implicit "50 = average" assumption inherited from school grading. But a product on a real retailer's shelf with 4.0/5 stars from real consumers is, by definition, above-average commercial-grade. Scoring it 64/100 is a calibration error, not honesty.

### New calibration

| Score range | Meaning | Frequency |
|---|---|---|
| 90-95 | Best-in-class signals (top-quartile reviews, completeness, price-fit) | ~10% of products |
| 80-89 | Above-average commercial-grade — the default for a well-rated product | ~60% |
| 70-79 | Acceptable but with notable gaps (limited reviews, partial specs, premium price for category) | ~25% |
| <70 | Real red flags only (1-2★ reviews, counterfeit risk, missing critical specs) | ~5% |

### Implementation

`app/services/scoring_service.py`:

- Add a calibration layer at the end of `score_products()`: `display_score = clamp(70 + (raw_score - 50) * 0.5, 60, 95)`.
  - Raw 50 (today's "average") → display 70.
  - Raw 70 (today's "good") → display 80.
  - Raw 90 (today's "excellent") → display 90.
  - Raw 30 (today's "poor") → display 60.
- Calibrate **per-product overall score** (the hero ring number) AND per-dimension scores (the bar values).
- The win_margin calculation uses calibrated scores → typical winners are 4-12 points ahead instead of today's 5-20 point swings.

### Validation

- 100 historical comparisons re-run through new calibration → measure distribution. Target: 60% of overall scores fall in 80-89 band, <10% below 70.
- Snapshot tests in `tests/test_scoring_service.py` updated to reflect new ranges.

### Honesty guard

A product with **all raw signals below 40** (bad reviews, missing data, suspicious price) must score below 70 even after calibration. Calibration is for "the common case looks honest," not for "everything looks fine."

---

## Decision 5 — Legal-safe copy framing

### Banned vocabulary (frontend i18n lint rule, both EN + AR)

| Banned | Pattern | Replacement |
|---|---|---|
| Best Pick / Best Choice / Winner | absolute superlative | "Top match" |
| Excellent / Great / Good / Smart pick | evaluative adjective on overall fit | number only, no adjective |
| Choose this / Get this / This is right | imperative endorsement | "If you prioritize X, this fits" |
| Better / Worse / Beats | comparative judgment | factual delta — "BHD 30 less", "0.2★ higher" |
| Why we picked this | Qaren-made-the-choice framing | "How they compare" |
| We recommend | first-person endorsement | "Reviewers note..." or remove |

### Approved patterns (all copy must match one)

1. **Match-based** — frames choice as user-personal, not universal:
   - "Top match for **you**"
   - "Closer to your priorities"
   - "Matches what you said you wanted"

2. **Fact-based** — verifiable, no judgment:
   - "BHD 30 less"
   - "12g lighter"
   - "Available in Bahrain"
   - "5-year warranty vs 2-year"

3. **Attributed** — opinions belong to a named source:
   - "Reviewers at rtings.com note..."
   - "According to Noon listing..."
   - "Users on techpowerup.com say..."

4. **Conditional** — user-driven choice, no Qaren endorsement:
   - "If you want X, pick the first one"
   - "Pick the other one if Y matters more"

### "How they compare" verdict generation

Replace `overview.winner.reason` from GPT with a deterministic builder in `app/services/response_builder.py`:

```python
def build_factual_verdict(scoring, products, lang="en"):
    """
    Compose verdict from dimension deltas, never from GPT-invented scores.

    Returns 2 sentences max:
      Line 1: factual deltas — "BHD 30 less, 0.2★ higher, 12g lighter"
      Line 2: conditional alternative — "If you want PBT keycaps, the other fits."
    """
    top_match_idx = scoring["overall_score"]["winner_idx"]
    deltas = [d for d in scoring["dimensions"]
              if d["is_core"] and winner_of(d) == top_match_idx][:3]
    line1 = ", ".join(d["delta_text"] for d in deltas)

    runner_wins = [d for d in scoring["dimensions"] if winner_of(d) != top_match_idx]
    line2 = (f"If you want {runner_wins[0]['label'].lower()}, "
             f"the {products[1-top_match_idx]['name'].split()[0]} fits.")

    return f"{line1}. {line2}"
```

GPT verdict (4o-mini) still generates **per-product `best_for` lines** ("Ideal for…") since those are conditional + product-positive — both products get one, neither is "the loser." No numbers in those lines.

### i18n lint enforcement

Add ESLint rule + pytest test that scans `en.json`, `ar.json`, and all `t('...')` call sites for banned patterns. Build fails on banned vocabulary. Approved-vocab whitelist lives at `SmartCompareApp/src/i18n/.copy-policy.json`.

---

## Decision 6 — Remove "What's next?" + "Save"

Both buttons deleted from `ResultsScreen.tsx`. The trailing action row becomes Share only, repositioned as an icon in the top-right of the hero card.

- **"What's next?"** — currently broken (NAVIGATE error). The tab bar already provides navigation home. Re-engagement nudges, if needed, will be added later as a single contextual card based on cohort signals — not a dead button.
- **"Save"** — redundant with auto-save to History. Removing reduces decision fatigue and visual clutter.

History remains the canonical "saved comparisons" surface. No data migration needed.

---

## Decision 7 — Drop "Low confidence data" default pill

Currently `fact_check.overall_confidence: "low"` triggers a red pill at the top of Results — apologetic and unexplained.

New behavior:

- Pill **never shown by default.**
- When a comparison has genuinely shaky data (≥2 of: no real prices on either, no reviews on either, all-estimated specs), show a **subtle gray inline notice** at the bottom of the dimension bars list:
  > "Fresh listing — some data still settling. Tap to refresh."
- Positive framing. Tap → re-runs the pipeline with `nocache=true`.
- The pill is also removed from the i18n strings; replaced with `results.dataFreshness.settling` key.

Per-dimension `confidence: "low"` is communicated visually via the bar opacity + "≈" prefix, not a separate banner.

---

## Decision 8 — Scatter-gather scraping pipeline

### Current architecture (sequential tiers)

```
Tier 1   Serper Shopping      ─ 2-3s  → fail
Tier 1.5 Curl page scrape     ─ 3-5s  → fail
Tier 1.5a Firecrawl render    ─ 10-30s → fail
Tier 1.5d Scrape.do residential ─ 5-15s → fail
Tier 2   GPT organic extract  ─ 2-3s
Tier 3   GPT training estimate ─ 1-2s
                              Total: up to 45s+ on cold luxury
```

### New architecture (fan-out + settle)

```
T=0   ─ Fan-out (all concurrent):
        ├─ Serper Shopping        ~2-3s
        ├─ GPT product parse      ~2-3s
        ├─ Page scrape curl_cffi  ~3-5s   [free, always]
        ├─ Firecrawl render       ~10-25s [conditional in soft mode]
        ├─ Scrape.do residential  ~5-15s  [conditional in soft mode]
        └─ Redis + L2 DB cache    ~150ms  [served immediately if hit]

T=3-5s ─ Serper + parse done → downstream parallel:
        ├─ GPT specs extraction   ~2-3s
        ├─ GPT review extraction  ~2-3s
        ├─ Rating consensus       ~1-2s
        └─ Verdict streaming      ~2-4s

T=10-13s ─ FIRST PAINT
          Render with best-available data from every source that returned.
          Frontend marks late-arriving fields with subtle pulse.

T=13-25s ─ SETTLE WINDOW
          SSE stays open. Late scrapers reconcile via quality ranker.
          Higher-trust prices swap in via fade. Confidence dots go green.

T=25s ─ Hard cap. Stream completes. Whatever's in is final.
```

### Quality ranker

When multiple sources return different values for the same field:

```python
PRICE_SOURCE_RANK = [
    ("confirmed_multi_source", 100),    # 2+ sources agree within 5%
    ("firecrawl_brand_domain", 90),     # official brand site, rendered
    ("page_scrape_jsonld", 85),         # structured data on indexed page
    ("serper_shopping", 75),            # Google Shopping direct
    ("scrapedo_rendered", 70),          # residential proxy
    ("gpt_organic_extract", 60),        # GPT from search snippets
    ("gpt_training_estimate", 40),      # last resort, flagged
]
```

Highest-ranked price wins. Others stored in `alternate_listings[]` (tappable in UI to show all retailers).

### Cancellation

When confirmed price lands (rank ≥85 OR 2 sources agree), still-running scrapers for **that product's price** get cancelled to save credits. Other fields (reviews, specs) continue independently.

### Modes

Controlled by `SCRAPING_MODE` env var on Railway:

- **`hard`** (default for next 30 days, tester phase): always fan out everything. Highest data quality, fastest. Burns ~30 Firecrawl/Scrape.do credits per cold comparison.
- **`soft`** (default at App Store launch): always fan out Serper + page scrape + GPT (free/cheap). Fan out Firecrawl + Scrape.do **conditionally** — when pre-classified luxury domain (`OFFICIAL_BRAND_DOMAINS` + SPA list) OR when Serper returns suspicious data within 5s (price >2x median, missing entirely). ~3-5 Firecrawl credits per cold comparison.

Switch is one env var, zero code change. Circuit breakers in `api_budget_service.py` already gate runaway burn (3 failures → 10-min cooldown).

### Frontend SSE handling

`ResultsScreen.tsx` already uses `streamComparison()`. New SSE event types:

- `first_paint` — all core dimensions ready, render the full UI.
- `settle_update` — a higher-trust value arrived for a specific field. Frontend fades the new value in over 400ms. Examples: `{ field: "products[0].price", new_value: {...}, source_rank: 90 }`.
- `settle_complete` — settle window closed, no more updates.
- `confidence_upgrade` — dimension confidence improved (e.g., 2nd source confirmed price). Frontend pops the confidence dot from gray to emerald.

---

## Decision 9 — Latency targets

| Scenario | First paint target | Fully settled | % traffic |
|---|---|---|---|
| Warm cache | 2-3s | 2-3s | ~30% |
| Cold, no luxury | 8-12s | 8-12s | ~65% |
| Cold + luxury | 12-13s | 15-22s | ~5% |
| Worst case (hard mode, slow network) | 13s | 25s (hard cap) | <1% |

**Hard cap:** Backend kills the SSE stream at 25s regardless of in-flight work. Frontend treats stream-end as final.

**Perceived latency target:** ≤15s for the user to see a complete-looking Results screen, in 99% of cases.

Phase 2 (deferred 2 weeks): **Pre-warmed cache for top 500 GCC pairs** via nightly background worker. Brings warm-cache rate from ~30% to ~55% for high-volume queries.

---

## Files Touched

### Backend (`app/`)

| File | Change |
|---|---|
| `app/services/scoring_service.py` | Add calibration layer (70+ baseline). Emit new `dimensions[]` array alongside legacy keys. Helper `winner_of()` for dimension comparison. |
| `app/services/structured_comparison_service.py` | Refactor `compare_from_text_streaming()` to scatter-gather pattern. New `asyncio.gather` block for parallel scraper fan-out. Add settle-window loop after first paint. |
| `app/services/price_service.py` | Quality ranker `select_best_price(candidates)`. Each tier now returns a `{value, source_method, rank, raw_data}` tuple instead of a price directly. |
| `app/services/firecrawl_service.py` | Add cancellable wrapper. Pre-classification helper `should_fan_out(url)` for soft mode. |
| `app/services/scrapedo_service.py` | Same cancellation + classification additions. |
| `app/services/response_builder.py` | New `build_factual_verdict()` — deterministic 2-sentence verdict from `dimensions[]`. Replaces GPT-generated `overview.winner.reason` for the main verdict (per-product `best_for` lines stay GPT). |
| `app/services/fact_check_service.py` | Confidence levels emitted per-dimension (not overall). Drop `overall_confidence` from response. |
| `app/api/text_routes.py` | New SSE event types: `first_paint`, `settle_update`, `settle_complete`, `confidence_upgrade`. Backward-compat: existing `complete` event still fired at settle_complete. |
| `app/main.py` | Read `SCRAPING_MODE` env var. Pass to service factory. |

### Frontend (`SmartCompareApp/src/`)

| File | Change |
|---|---|
| `screens/ResultsScreen.tsx` | Defensive `result?` guards (1a). Hero rings + bars layout (Decision 3). Remove "Save" + "What's next" buttons + "Low confidence" pill. New SSE event handlers for settle window. |
| `components/results/HeroRings.tsx` | NEW. Two radial rings, animated fill, emerald-for-winner, gray-for-other. |
| `components/results/DimensionBars.tsx` | NEW. Renders `dimensions[]` array. One row per dimension. Confidence opacity + "≈" prefix. |
| `components/results/TopMatchBadge.tsx` | NEW. Replaces trophy. Single pill, emerald, "Top match" / "الأنسب لك". |
| `components/results/FactualVerdict.tsx` | NEW. 2-line text — Line 1 from delta_text, Line 2 conditional alternative. |
| `services/api.ts` | New SSE handler branches for `settle_update`, `confidence_upgrade`. In-place data merge into result state. |
| `types/index.ts` | New `Dimension`, `ScoringV2` types. Keep `ScoringResult` legacy for backward compat. |
| `i18n/en.json` + `i18n/ar.json` | Remove evaluative keys (`results.bestPick`, `results.smartPick`, etc.). Add `results.topMatch`, `results.howTheyCompare`, `results.dataFreshness.settling`. Arabic AI-proofread. |
| `i18n/.copy-policy.json` | NEW. Banned vocabulary list + approved patterns. Loaded by ESLint rule. |
| `eslint.config.js` | New rule `qaren/no-evaluative-copy` that scans i18n + t() calls against `.copy-policy.json`. Build fails on violation. |

### Tests

- `tests/test_scoring_service.py` — snapshot tests updated for new calibration. New test for `dimensions[]` contract (always emits 3 core; never emits incomplete-data dimension).
- `tests/test_response_builder.py` — NEW. `build_factual_verdict()` produces no evaluative language; pulls correct deltas; handles 1-dim winners.
- `tests/test_scatter_gather.py` — NEW. Fan-out timing test (mocks scrapers with controlled delays, verifies first_paint at ≤13s). Cancellation test (confirmed price cancels in-flight scrapers).
- `tests/test_security_regression.py` — verify no regression on the 98 existing tests.
- `SmartCompareApp/__tests__/results/HeroRings.test.tsx` — NEW. Snapshot + ring fill animation.
- `SmartCompareApp/__tests__/results/no-evaluative-copy.test.tsx` — NEW. Scans all rendered text against banned vocab.

---

## Migration / Rollout

**Build sequence:**

1. **Backend foundation** — `dimensions[]` contract + calibration + `build_factual_verdict()`. Ships with legacy keys preserved. Backward compatible.
2. **Backend pipeline** — scatter-gather + quality ranker + new SSE events. Tested behind `SCRAPING_MODE=hard`.
3. **Frontend hero + bars** — new components, new SSE handlers. Reads `dimensions[]` if present, falls back to legacy keys.
4. **Frontend copy + i18n** — banned-vocab lint, new keys, AI-proofread Arabic.
5. **Frontend defensive fixes** — `result?` guards, button removal.
6. **QA pass** — cross-category (mouse/keyboard), same-category (two mice), luxury (LV bag vs Hermès), supplements, edge case (cold cache, no Firecrawl credits).
7. **Soft mode test on Railway preview** — verify credit conservation works as designed.

**Rollout:** behind `BUNDLE_E_NEW_RESULTS` feature flag on backend, `CANARY_NEW_RESULTS_PERCENT` on frontend (defaults 100 for tester build per `qaren-canary-onboarding.md`).

**Backward compatibility window:** 1 release cycle (Bundle F removes legacy `price_score`/`spec_score` keys + legacy SSE `complete` event).

**Database:** no migration. New behavior is response-shape only.

---

## Open Questions (none blocking)

1. **Pre-warmed cache for top 500 pairs** — deferred to Phase 2 (2 weeks out). Requires nightly cron + ~$5/mo Redis storage.
2. **Per-cohort calibration** — should the 70+ baseline shift based on user's stated price-range (budget vs premium)? Deferred until we have cohort signal data post-launch.
3. **Settle-window UX research** — does the "fade-in late data" actually feel premium, or does it confuse users? A/B test in Phase 2.
4. **Hard-mode credit drain** — if testers run >50 comparisons in a week, Firecrawl free tier exhausts. Monitor `api_budget_service` daily. Switch to soft mode early if needed.
5. **Arabic line length** — "الأنسب لك" is 8 chars vs "Top match" 9. Hero pill width should be `auto` not fixed.
6. **"common.or" i18n key** — pre-existing bug from CLAUDE.md known list, fold into this bundle since we're touching i18n anyway.

---

## Success Criteria

This bundle is "done" when:

- Comparing mouse vs keyboard (the original failure case) produces:
  - First paint at ≤13s ✓
  - Hero rings showing 80+ scores on both products ✓
  - 4 dimension bars (Price, Reviews, Value + 1 contextual) all populated, none empty ✓
  - Verdict text contains zero numbers from a score, zero evaluative words ✓
  - No "Low confidence" pill ✓
  - No "Save" or "What's next" buttons ✓
- Comparing two iPhones (warm cache, same category) hits ≤3s first paint.
- History → tap any comparison → renders without crash, including legacy v1 rows.
- Lint rule `qaren/no-evaluative-copy` catches every banned word in CI.
- 100 historical comparisons re-run through new calibration show ≥60% of overall scores in 80-89 band.
- All 792 jest + 144 pytest tests still pass.

---

**Next step:** invoke `superpowers:writing-plans` to produce the implementation plan with task-level granularity.
