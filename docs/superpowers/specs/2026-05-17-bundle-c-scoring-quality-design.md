# Bundle C — Scoring + Personalization Quality Pass (Design)

**Status:** Approved 2026-05-17 (Session 51 brainstorm). Plan-pending.
**Branch:** `feature/bundle-c-scoring`
**Authors:** Ahmed + Claude (brainstorming skill)
**Predecessors:** Bundle E (`docs/plans/2026-05-13-results-quality-overhaul-design.md`) ships scoring_v2 + dimensions[] contract + calibrate_score band. Bundle C replaces, deepens, and corrects parts of it.

---

## 0 — Score-rendering principle (cross-cutting anchor)

This is the design's north star. Every visible number, pill, bar, or piece of copy in Bundle C must obey it.

> **Calibrated honesty.** The Qaren scoring engine never punishes a product for sparse data, never invents a low score, never apologizes for itself. Low or weird scores appear ONLY when the comparison is genuinely weird (cross-category, severe data gaps after 3-tier fallback, or 10×+ price spread). Default state always looks respectable: real data → honest within `[60, 95]` band; missing data → fight to fill it (3-tier fallback), then silent omission; pricing fallback → silent on provenance; tier mismatch → math handles it silently. The user never sees an info banner, never reads "estimated" or "reference price", never sees a fabricated default.

**Where it applies:** dimension bars, hero overall score, value/price/reviews dims, confidence pills, personalization chip, value-match captions, verdict text, every i18n key touched in Bundle C.

**Three project-wide rules absorbed during brainstorm:**

1. **No info banners in user-facing UI** — per-element microcopy only (pills, captions, verdict text). `memory/feedback_no_info_banners.md`.
2. **No backend internals in user-facing diagnostic reveals** — qualitative arrows/labels, never coefficients, cap percentages, or shift math. `memory/feedback_no_backend_internals_in_reveals.md`.
3. **Never use "estimated" in user-facing UI** — backend keeps `source_method="estimated"` enum, but UI is silent on price provenance. Disclosure shifts to Terms. `memory/feedback_no_estimated_word_in_ui.md`.

---

## 1 — Bug fixes (gate for the rest of the bundle)

These bugs MUST be diagnosed via captured evidence BEFORE any fix ships. No speculative patches.

### 1a. Pros/cons empty on every comparison

Cold-cache probes (2026-05-17) returned `pros: []` and `cons: []` on:
- iPhone 16 vs Galaxy S25 (electronics, Bahrain, `nocache=true`).
- CeraVe vs Cetaphil Moisturizing Cream (skincare, Bahrain, `nocache=true`).

Suspects (`structured_comparison_service.py:704-712`, `extraction_service.py:580-587`, verdict GPT call):
- Verdict JSON dropping `product_0_pros`/`product_1_pros` keys, silently swallowed by `comparison.pop(..., [])`.
- gpt-4o (`model_router.get_model(priority="high")`) at `temperature=0.1` paired with long preference + cohort block omits fields.
- `validate_verdict` (line 700-701) strips fields before pop.

**Diagnostic-first plan:**
1. Log raw `response.choices[0].message.content` from `generate_comparison` (`extraction_service.py:1085+`) when `len(comparison.get("product_0_pros", [])) == 0`.
2. Run 6 cold-cache probes across electronics / skincare / supplements / fashion / fragrances / grocery.
3. Inspect logs to identify which suspect is firing.
4. Patch only the root cause. Re-test all 6 probes show non-empty pros/cons.

**No fallback re-prompt unless diagnosis proves it.** Targeted re-prompts trade cost + latency for completeness; require evidence.

### 1b. `scoring_v2.factual_verdict` is None on every probe

`_build_scoring_v2` (`response_builder.py:36`) calls a builder that never emits `line1` / `line2`. Pure template fix from existing fields:
- `line1` = winner declaration with the strongest factual delta (price gap, rating gap, or top dim margin).
- `line2` = the runner-up's strongest counter-fact.

Zero GPT cost. Trace the missing builder, add it, regression-test that scoring_v2 always populates factual_verdict.

### 1c. Price pipeline regression — mainstream queries fall to estimated

Both cold-cache probes hit `source_method="estimated"` for products that should hit Tier 1 Serper Shopping. Diagnostic-first:

1. Enable `DEBUG_STAGE_TIMINGS=true` on Railway.
2. Run 6 fresh `?nocache=true` comparisons (same 6 categories as 1a).
3. Log per call:
   - Raw Serper Shopping response sizes per product.
   - `source_method` resolution per product per tier (1 → 1.5a → 1.5d → 2 → 3).
   - Firecrawl + Scrape.do invocation counts (MEMORY note Session 51 already flagged "Firecrawl never fires in production" for fragrances).
   - `api_budget_service` credit state per call (Firecrawl 450 lifetime, Scrape.do 900/mo, Serper 2200 lifetime).
   - Circuit-breaker state (3 failures → 10min cooldown).
4. Identify which tier each product traverses + where it falls.

**Likely root causes (rank by prior plausibility):**
- Serper Shopping regional gap (Bahrain coverage thin for flagship products).
- `api_budget_service` reporting exhausted Firecrawl credits.
- Circuit breakers tripped from earlier failures.
- `_validate_price_query` rejecting queries.
- `_extract_price_from_html` parser regression.

Fix is small once root cause confirmed. The diagnostic IS the hard part. `DEBUG_STAGE_TIMINGS=true` window must be disabled after evidence captured (per project measure-before-optimize rule).

---

## 2 — Calibration philosophy + missing-data handling

### 2a. Kill the missing-data floor of 30

`scoring_service._compute_raw_scores` and `_normalize_*` currently inject `MISSING_SCORE=50` when a signal is missing, which calibrates to 60 and creates phantom score gaps (probe evidence: iPhone perf/build/feature all forced to 30 raw → display 60; legacy overall 37.6 vs 77.5 was a data-sparsity artifact, not a real product gap).

**Change:** missing signals propagate as `None`. `build_dimensions_v2` skips the dim entirely. Legacy `breakdown` shows `null`. Downstream display rules (Section 2b/h) decide what user sees.

### 2b. "Insufficient data" row in DimensionBars — last-resort only

Reserved for the rare case where, after 3-tier fallback (2f), BOTH products lack the underlying signal AND the dim cannot be silently omitted (single-dim scenarios). Renders as: dimension label + neutral muted row + caption "Limited data". No bar fill, no emerald, no gray. Most missing dims should never reach this state — they get silently omitted per 2h.

### 2c. Keep calibration band `[60, 95]` for populated signals

`calibrate_score` formula unchanged for signals with data. Floor=60, ceiling=95, honesty guard for raw_signals < 40 → display ≤69. Real product differences live in a stable visual band.

### 2d. Hero overall score — no "Limited data" pill

Hero shows its calibrated number cleanly. If data is genuinely sparse across many dims, the verdict text + silent dim omission carry context. No pill, no apology.

### 2e. "Weird comparison" detector — verdict-text only, no banner

Backend emits `comparison_quality: "normal" | "weak" | "weird"` on the response. Triggers `weird` when:
- Products span unrelated categories (`category_used` mismatch).
- >50% of one product's specs are missing AFTER 3-tier fallback.
- Prices differ by 10×+ order of magnitude.

When `weird`:
- Verdict GPT prompt receives the flag and rewrites `winner_declaration` + `winner_reason` (no forced winner pick): e.g., "These products serve different purposes — Cetaphil for daily moisture, La Mer for premium skincare experience."
- DimensionBars render only dims with signal; others silently omitted per 2h.
- Hero overall score suppressed (rendered as `—`); verdict text carries meaning.
- **No banner, no warning bar, no top-of-screen apology.**

### 2f. 3-tier spec fallback (specs should not have missing fields)

Split `CRITICAL_SCHEMA_FIELDS` (`extraction_service.py:180`) into two layers:

| Category | Non-negotiable (must-have or 3-tier hard) | Preferred (try once, accept missing) |
|---|---|---|
| `electronics` | `battery`, `processor`, `ram`, `rear_camera` | `front_camera`, `water_resistance`, `os`, `weight` |
| `supplements` | `dosage`, `form` | `count`, `serving_size`, `active_ingredient` |
| `fragrances` | `concentration`, `longevity` | `sillage`, `notes_top/heart/base`, `season` |
| `fashion` | `material` | `origin`, `style`, `closure_type`, `care_instructions` |
| `skincare` | `volume`, `ingredients` | `skin_type`, `active_ingredient`, `spf` |
| `haircare` | `volume`, `ingredients` | `hair_type`, `scent`, `sulfate_free` |
| `makeup` | `volume`, `shade_range` | `finish`, `coverage`, `cruelty_free`, `spf` |
| `grocery` | `weight`, `ingredients` | `nutrition_*`, `origin`, `organic` |
| `other` | (none — all preferred) | per existing schema |

**Tier 1** (primary, existing): smart-fallback within D2 `[:6] / 5s` budget.
**Tier 2** (new): targeted Serper+GPT-mini per still-missing non-negotiable. Parallel, 4s wall, 1 retry per field, 0.5s per-field budget.
**Tier 3** (new): GPT-4o knowledge synthesis — single batched call with ALL remaining gap fields, returns best-inference values. Internal flag `inference_source="model_knowledge"` (QA/dashboards only, NEVER user-visible). 3s wall.

Total budget stays inside `STREAM_HARD_CAP_SECONDS=25` because tiers 2 + 3 fire only when non-negotiables remain blank, and they run parallel within the existing post-Phase-1 window.

### 2g. Eliminate fabricated defaults

`_dim_value` (`scoring_service.py:1247`) does `ra = a.get("rating") or 4.0` — silently fabricates B+ ratings when missing. Replace with `None` propagation; dim emits `null` instead. Audit + remove any other `or <number>` silent defaults in scoring (`price or 0.1`, `warranty or 1`, etc.). Every fallback becomes explicit (Tier 3 inference at extraction layer) or the dim drops.

### 2h. Silent omission of dims with truly-missing data

After Section 2f (3-tier fallback), if a non-negotiable spec is STILL missing:
- Field omitted from `response.products[].specs` entirely. Frontend already filters nulls; the user sees a complete-looking specs table.
- Dependent dimension omitted from `dimensions[]`. No "—", no pill, no copy.
- The system fails silent on missing data rather than apologizing.

### 2i. Legal disclosure

Append to `app/legal/terms_of_service.md` and Arabic translation:

> "AI extraction is approximate. Specifications, prices, and ratings may contain inaccuracies. Always verify critical details with the retailer before purchase."

Same clause added to `privacy_policy.md` data-quality section if one exists. This covers the disclosure obligation that user-facing UI silently bypasses (per project rule "Never use 'estimated' in user-facing UI").

---

## 3 — Budget tier expansion (GCC-anchored)

### 3a. 5-tier system replacing the current 3

| Tier | Label EN / AR | Anchor examples |
|---|---|---|
| `budget` | Budget-savvy / موفّر | snacks, OTC supplements |
| `mid` | Mid-range / متوسط | mass-market skincare, mid Android |
| `premium` | Premium / مميّز | flagship Android, designer cosmetics |
| `luxury` | Luxury / فاخر | iPhone Pro, designer bags, niche fragrances |
| `top_tier` | Top-tier / الأعلى | luxury watches, haute couture, 1000+ BHD shoppers |

### 3b. Backend changes

- `scoring_service.PRICE_TIERS` (the existing flat map) replaced by `PRICE_TIERS_BY_CATEGORY` — see 3e.
- `TIER_EXPECTATIONS` extended: `budget: 0.60, mid: 0.70, premium: 0.80, luxury: 0.88, top_tier: 0.90` (today's luxury=0.85 re-splits to 0.88/0.90).
- `CATEGORY_BUDGET_ADJUSTMENTS` extended per-category for the two new tiers: `luxury` mirrors `premium` with slightly steeper spec emphasis; `top_tier` adds +0.05 to the category's headline spec dim (e.g., `craft_score` for fashion, `performance_score` for electronics).
- Pydantic `BudgetValue` Literal extends `'budget' | 'mid' | 'premium' | 'luxury' | 'top_tier'`.
- Cohort enum (`VALID_PRIORITIES`, `cohort_priors.json` keys) — Migration 024 adds tier strings.

### 3c. Frontend changes

- `BudgetPicker.tsx` (used by `EditPreferencesFlow`) + `Step09Budget.tsx` (onboarding): 5 tier cards instead of 3.
- i18n EN/AR keys: `onboarding.s9.luxury`, `onboarding.s9.luxury_range`, `onboarding.s9.top_tier`, `onboarding.s9.top_tier_range`.
- Visual treatment: `premium / luxury / top_tier` cards get a subtle dark accent + serif label weight (Geist Display Medium for `top_tier`) so the picker doesn't read as "down-bucket premium". Restrained editorial; no gaudy gold.
- Onboarding picker shows GENERAL guidance ranges (today's flat numbers per the `other_light` sub-scale) with a single-line caveat "varies by category". Per-category re-anchoring happens server-side, invisible to the user.

### 3d. Migration safety

- Migration 024 adds `top_tier` to `users.preferences.budget` CHECK constraint. Existing rows with `budget='premium'` stay valid. Rollback at `migrations/rollback/024_*.sql`.
- New users default to `mid`.
- Backwards-compat: API still accepts old 3-tier values for older clients.

### 3e. Category-scaled tier breakpoints (`PRICE_TIERS_BY_CATEGORY`)

The 5 labels are **semantic**. BHD ranges anchor per-category to real market reality:

| Category | budget | mid | premium | luxury | top_tier |
|---|---|---|---|---|---|
| `electronics` | <100 | 100–400 | 400–800 | 800–2000 | 2000+ |
| `supplements` | <11 | 11–30 | 30–60 | 60+ (fold) | (fold into luxury) |
| `fashion` | <30 | 30–150 | 150–500 | 500–2000 | 2000+ |
| `fragrances` | <30 | 30–80 | 80–180 | 180–500 | 500+ |
| `skincare` | <11 | 11–40 | 40–100 | 100–300 | 300+ |
| `haircare` | <15 | 15–40 | 40–100 | 100–200 | 200+ |
| `makeup` | <15 | 15–50 | 50–120 | 120–300 | 300+ |
| `grocery` | <5 | 5–15 | 15–50 | 50+ (fold) | (fold into luxury) |
| `other` (sub-scale via runtime detection) | see 3f | | | | |

### 3f. `other` runtime sub-scale detection (geometric-mean basis)

Detect comparison-level price magnitude via `gm = sqrt(p1 × p2)`. Pick sub-scale:

| Sub-scale | Trigger (gm) | budget / mid / premium / luxury / top_tier (BHD) |
|---|---|---|
| `other_light` | < 30 | <11 / 11–57 / 57–189 / 189–500 / 500+ |
| `other_mid` | 30 – 300 | <30 / 30–120 / 120–400 / 400–1000 / 1000+ |
| `other_high` | 300 – 5000 | <300 / 300–1500 / 1500–5000 / 5000–15000 / 15000+ |
| `other_ultra` | 5000+ | <5000 / 5000–15000 / 15000–40000 / 40000–100000 / 100000+ |

Cars (~5000 + 8000 BHD → gm=6324 → `other_ultra`) → budget tier means <5000, top_tier means 100,000+. User picking "budget" + searching cars finds the cheapest car in scope, not "products under 11 BHD".

Implementation: `_detect_price_tier(price, category, *, comparison_prices=None)`. When `category == "other"` and `comparison_prices` provided, derive sub-scale from gm; else fall back to `other_light`.

### 3g. V2 path (documented, not shipped)

Logarithmic auto-scaling around the geometric mean: breakpoints = `gm × {0.4, 0.8, 1.5, 3.0}`. Always relative to comparison prices. The pure-math answer; works for any category including ones not yet thought of (boats, real estate, jewelry). Deferred because:
- Makes deterministic testing harder.
- Picker's general-guidance ranges desync from the engine.
- Static map (3e + 3f) covers known categories cleanly.

Architecture leaves space: `_detect_price_tier` is the swap point.

---

## 4 — Value math (dynamic + delta hero)

### 4a. Dynamic same-tier value formula by user priority

Replace `scoring_service._compute_value_score` constant `0.6 spec + 0.4 price` with priority-driven coefficients:

| User's top priority (first match in priorities list) | spec | price |
|---|---|---|
| `price` | 0.40 | 0.60 |
| `quality` | 0.70 | 0.30 |
| `durability` / `latest_features` / `brand_reputation` | 0.65 | 0.35 |
| (no explicit priority — default) | 0.60 | 0.40 |
| `eco_friendly` / `ease_of_use` | 0.55 | 0.45 |

New dict `VALUE_FORMULA_BY_PRIORITY` in `scoring_service.py`. Function reads `preferences.get("priorities", [])` first-match wins.

Cross-tier path (`is_cross_tier=True`) keeps `TIER_EXPECTATIONS` formula but `delivery * 0.8` becomes `0.9` for `price` priority and `0.7` for `quality` priority.

**Internal coefficients are never exposed in API responses** (per "no backend internals" rule). Only the qualitative chip (Section 7) hints at direction.

### 4b. Delta-text promoted to hero

`DimensionBars.tsx` value/price row layout:
- Row label (left): "Value" / "Price" — typography.body.
- **Delta hero** (center, large): "**40% less**" or "**0.9 stars higher**" — typography.title, emerald when winner, neutral when tie.
- Score numbers shrink to caption to the right of each bar.

Backend `delta_text` strings get richer:
- Price: "`40% less`" (was "BHD 3.76 less" — kept as secondary).
- Reviews: "`0.9 stars higher`" (unchanged).
- Value (with matched priority): "`Better value for your priority`" (was "Stronger value ratio").
- Value (no priority match): "`Stronger value ratio`" (unchanged).

### 4c. Cross-tier value framing copy

When `is_cross_tier=True`: value-row delta text reads "`Different tier — held to higher bar`" with no winner-emerald (both products muted). Avoids "Cetaphil wins on value" framing when comparing a 5 BHD vs 50 BHD product.

### 4d. Value-match score (surfaced via copy, not number)

Backend computes `value_match: "in_range" | "above_range" | "below_range"` per product by comparing product's detected tier (3f) vs. user's stated budget preference.

Per-row caption rendering:
- Exact match → `in_range` → no copy (silent confirmation).
- 1 tier above user's preference → `above_range` → caption: "Above your usual range".
- 1 tier below → `below_range` → caption: "Within your range".
- 2+ tiers off in either direction → caption: "Above your usual range — but here's why" + `key_tradeoff` snippet.

### 4e. Tier-mismatch handling (math only, no banner)

The runtime sub-scale detection (3f) IS the basis. Deterministic, category-aware. No banner surfaces it.

**Case 1 — both products above user's stated tier** (e.g., user picked `top_tier`, comparing entry-level cars):
- Value formula + budget adjustments respect user's priority unchanged.
- Per-row caption may say "Below your usual range" only when the per-row signal is genuinely diagnostic; otherwise silent.

**Case 2 — both products below user's stated tier** (the car example: user picked `budget`, comparing 5000 + 6000 BHD cars):
- **Semantic preservation:** user said "budget" = "cheapest reasonable option I'm looking at".
- `CATEGORY_BUDGET_ADJUSTMENTS["budget"]` price-heavier weights stay active.
- Value formula keeps priority-driven coefficients.
- Cheaper product gets the value lift naturally via math.
- Per-row caption: "Cheaper of the two" on the lower-price product if the dim isn't already self-explanatory.

**Case 3 — tier match:** silent.

**Verdict prompt:** `budget_mismatch: "above" | "below" | null` passes to `_build_preferences_prompt` (`extraction_service.py:870+`). Adds instruction: "When budget_mismatch is set, acknowledge naturally in best_for / value_context that products are outside the user's usual range, but still help them decide between the options shown." No UI banner.

---

## 5 — Confidence widget

### 5a. Threshold tightening

In `scoring_service.compute_confidence`:
- `rating_strong`: drop `verified=True`. New rule: `review_count >= 100`. 1200 aggregated reviews IS strong signal even when `rating_verified` is False.
- `price_strong`: drop `method != "estimated"` blocker IF at least one product's `source_method` in `{official_brand, page_scrape, firecrawl, scrapedo_rendered, local_bhd}` OR `shopping_count >= 3`. Real Serper Shopping coverage is strong signal even when fallback hit one product.
- `specs_strong`: lower `verified_pct >= 60` to `verified_pct >= 40` OR `citation_count >= 8`. Citation count alone is signal.
- Overall threshold unchanged (3 strong = high, 2 = medium, ≤1 = low).

### 5b. Per-leg pills with diagnostic tap

Replace single-word banner on `ResultsScreen.tsx:737` with:
- 3 small pills horizontal row: 💰 Price · ⭐ Reviews · 📋 Specs.
- Colors: emerald (strong), amber (acceptable), gray-muted (weak).
- Tap → bottom sheet "What we know" listing 2-3 factual lines per leg:
  - "Reviews: 1200 reviews aggregated from Amazon, Best Buy, Google. Source verification pending."
  - "Specs: 23 of 30 fields verified against manufacturer sources."
- No threshold numbers. No coefficient exposure. Just countable facts.

### 5c. Price pill silent on fallback provenance

When ANY product's `source_method == "estimated"`, the **Price confidence pill is hidden entirely**. No tap-reveal, no copy, no provenance language anywhere in the UI.
- Price number still renders in Price/Value dim bars — silently.
- Reviews + Specs pills render normally.
- Disclosure obligation handled by Section 2i legal clause.

### 5d. No overall single-word label

The 3 pills tell the story together. Legacy `overall: "low"` field stays in API for backwards-compat but isn't rendered.

---

## 6 — DimensionBars overhaul

### 6a. Dimension contract sourced from CATEGORY_DIMENSIONS

Replace `_dim_dpi / _dim_popularity / _dim_build_quality` builders with category-driven legacy 6-dim breakdown already computed by `scoring_service.compute_scores`. `build_dimensions_v2` becomes a thin adapter:
- For each dim in `CATEGORY_DIMENSIONS[category]`, emit a `dimensions[]` entry if BOTH products have non-null score for it.
- Order: 3 cross-category core dims first (Price, Reviews, Value — built from existing signal pipeline), then up to 3 category-specific dims (e.g., Performance, Build Quality, Future-proofing for electronics).

### 6b. Hero + expand UI

`ResultsScreen.tsx` scoring_v2 section renders:
- **Hero card** — top 3-4 dimensions visible immediately (Price · Reviews · Value · one category-best signal). No tap required.
- **"See full breakdown" expand row** — tappable, expands inline to show all dims as bars. Closed by default. Animated height transition.
- Dim labels via `DIMENSION_DISPLAY_NAMES` (`scoring_service.py:248`).

### 6c. Calibration + missing-data rules apply uniformly

Per Section 2:
- Any dim with `score_a === null || score_b === null` is silently omitted from `dimensions[]` per 2h.
- Only the rare last-resort case (Section 2b) renders the "—" row.
- Fully-populated dims promote to hero. The hero card naturally adapts to whatever subset survives.

### 6d. Contract violation node stays

Existing `DimensionBars.tsx:53-69` zero-score detector remains as a dev-mode regression catcher. Backend per Section 2 should never emit zero-score dims; the node is a safety net.

---

## 7 — Personalization chip

### 7a. Compact qualitative chip below the verdict

Single line, no expand, no tap:

> *Weighted ↑ Performance · ↑ Build · ↓ Brand recognition (based on your priorities)*

- Up to 3 arrows — 3 strongest shifts vs. category defaults.
- Arrow direction (↑/↓) ONLY. Never percentages, never coefficients, never cap math.
- Dim names from `DIMENSION_DISPLAY_NAMES`.
- If no priorities set OR no significant shifts → chip hidden entirely.

### 7b. Backend contract

New field `response.personalization.applied_shifts: [{dim_display: "performance", direction: "up"}, ...]`.

Computed in `scoring_service.compute_scores` by comparing `weights_used` vs. `CATEGORY_DIMENSION_WEIGHTS[category]`. Direction = sign of delta. Magnitude hidden. Sorted by absolute magnitude (largest 3).

### 7c. i18n

New EN keys:
- `results.personalization.chip_template`: `"Weighted {{arrows_list}} (based on your priorities)"`.
- `results.personalization.arrow_up`: `"↑ {{dim}}"`.
- `results.personalization.arrow_down`: `"↓ {{dim}}"`.

Same in Arabic.

### 7d. Cohort attribution stays separate

Existing `CohortBadge` (peer count + governorate) remains its own component. No merging — cohort is statistical context, personalization chip is explicit-preference attribution.

---

## 8 — Migrations, rollout, tests

### 8a. Schema + enum migrations

- **Migration 024** — adds `top_tier` to `users.preferences.budget` CHECK enum + cohort_priors.json key compatibility. Existing rows untouched. Rollback at `migrations/rollback/024_*.sql`.
- **Pydantic Literal** — `BudgetValue` extends to 5 values.
- **`PRICE_TIERS_BY_CATEGORY` dict** — pure Python in `scoring_service.py`, no DB.
- **`TIER_EXPECTATIONS` extension** — adds luxury 0.88, top_tier 0.90.
- **`comparisons.scoring_v2` JSONB shape change** — adds `personalization.applied_shifts[]`, `comparison_quality`, `value_match`. Older rows render gracefully (frontend defaults to empty arrays).
- **Legal docs** — Section 2i clause added EN + AR.

### 8b. Feature flag rollout

- New flag: `ENABLE_BUNDLE_C_SCORING` (Railway env, default `false` in code).
- When `true`: all scoring/calibration/fallback/value/confidence/personalization changes activate together.
- When `false`: legacy Bundle E behavior.
- Iteration-phase discipline: flag stays OFF in code, flipped ON in Railway during testing.
- Tier expansion + budget picker UI ships **ungated** — purely additive, no harm in being live.

### 8c. Canary phasing

- <10 testers currently → canary 100% in Railway.
- Drop to 10% only at App Store soft-launch.
- Ramp 10 → 50 → 100 per `docs/runbooks/qaren-canary-onboarding.md`.

### 8d. Tests

**Unit:**
- `scoring_service` formula changes (1c, 2a, 2g, 4a, 4d, 4e).
- Tier detection per category (3e).
- Geometric-mean sub-scale picker for `other` (3f).
- Calibration band edge cases (2c).
- Missing-data omission (2h).
- Personalization shift detection (7b).
- Confidence threshold loosening (5a).

**Integration (6-category cold-cache probe suite):**
- electronics / skincare / supplements / fashion / fragrances / grocery + 1 `other` car-like comparison.
- Run with `?nocache=true` against staging.
- Verify: real prices land (not `estimated`), pros/cons populate, `dimensions[]` emits expected count per category, confidence pills render correctly, `value_match` captions fire when expected.

**Regression:**
- `test_security_regression.py`, `test_scoring_*.py`, `test_personalization_*.py` all pass.

**Frontend snapshots:**
- DimensionBars hero+expand (6b).
- Confidence pills 3-leg horizontal row (5b).
- Personalization chip with 3-arrow template (7a).
- Budget picker 5-tier (3c).

### 8e. Rollback path

- Single env var flip (`ENABLE_BUNDLE_C_SCORING=false`) reverts all scoring/UI changes.
- Migration 024 has rollback SQL.
- Tier expansion UI is non-destructive (additive), so persisted `top_tier` preferences degrade gracefully to `premium` if the picker reverts.

### 8f. Post-deploy verification

- 6-category probe suite as in 8d-integration, run against production with `?nocache=true`.
- Results captured into `docs/SESSION_BUNDLES.md` as Bundle C ship evidence.
- `DEBUG_STAGE_TIMINGS=true` enabled during the verification window, disabled after.

---

## 9 — Out of scope (intentionally deferred)

- **Bucket B (two-input UX redesign)** — text + URL compare with paired input boxes. Separate dedicated brainstorm.
- **V2 logarithmic auto-scaling** for `other` category (3g). Architecture leaves the swap point.
- **Cohort badge merge with personalization chip** (7d). Stays separate.
- **Targeted verdict re-prompt fallback** for empty pros/cons (1a). Only ships if diagnostic proves the verdict model genuinely can't fit all fields.
- **Top-up of API budget credits** (1c potential fix). Operational not design.

---

## 10 — File-level change manifest (anticipated)

### Backend
- `app/services/scoring_service.py` — most surface area (2a-h, 3e-f, 4a-e, 7b).
- `app/services/extraction_service.py` — 1a diagnostic, 2f Tier 2-3 fallback, 4e verdict prompt.
- `app/services/structured_comparison_service.py` — 1a logging, 2f orchestration, 2e weird detector.
- `app/services/response_builder.py` — 1b factual_verdict builder, 7b applied_shifts.
- `app/services/trust_validation_service.py` — possibly minor (verdict-validation order vs pros-cons pop).
- `app/services/firecrawl_service.py` / `scrapedo_service.py` — 1c diagnostic logging only, no behavior change.
- `app/services/api_budget_service.py` — 1c diagnostic surfaces.
- `app/utils/prompt_sanitizer.py` — unchanged (sanity check).
- `migrations/024_*.sql` + rollback.
- `app/legal/terms_of_service.md` + Arabic — 2i clause.
- `app/legal/privacy_policy.md` + Arabic — 2i clause if applicable.

### Frontend
- `SmartCompareApp/src/components/BudgetPicker.tsx` — 5-tier expansion.
- `SmartCompareApp/src/screens/onboarding/Step09Budget.tsx` — 5-tier expansion.
- `SmartCompareApp/src/screens/EditPreferencesFlow.tsx` — 5-tier prop pass-through.
- `SmartCompareApp/src/components/results/DimensionBars.tsx` — 6a-d (hero+expand, omission handling).
- `SmartCompareApp/src/components/results/HeroRings.tsx` — minor copy adjustments.
- `SmartCompareApp/src/components/results/FactualVerdict.tsx` — 1b builder contract.
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — 5b 3-pill row, 7a personalization chip, 4b delta hero layout, 4d/4e captions.
- `SmartCompareApp/src/types.ts` — TypeScript additions for new fields (applied_shifts, value_match, comparison_quality, top_tier).
- `SmartCompareApp/src/i18n/{en,ar}.json` — new keys (3c, 4b, 5b, 7c).

### Tests
- `tests/test_scoring_service.py` — formula changes.
- `tests/test_scoring_service_personalization.py` — applied_shifts.
- `tests/test_extraction_service.py` — Tier 2-3 fallback.
- `tests/test_structured_comparison_service.py` — orchestration.
- `tests/test_confidence_thresholds.py` — new.
- `tests/test_tier_detection.py` — new.
- `tests/test_value_math.py` — new.
- `tests/test_bundle_c_integration.py` — new, 6-category probe suite.
- `SmartCompareApp/src/components/results/__snapshots__/` — frontend snapshots.

---

## 11 — Brainstorm provenance

This design absorbed 3 project-wide rules during brainstorm (saved as memory):

- **No info banners in UI** — per-element microcopy only.
- **No backend internals in user-facing diagnostic reveals** — qualitative only.
- **Never use "estimated" in user-facing UI** — backend enum stays, UI silent, disclosure in Terms.

Two cold-cache probes captured during brainstorm proved:
- Pros/cons empty system-wide (Section 1a).
- `factual_verdict` always None (Section 1b).
- Prices fall to `estimated` for mainstream products (Section 1c).
- Missing-data floor of 30 creates phantom score gaps (Section 2a).
- `scoring_v2.dimensions[]` only emits 3-4 sparse dims (Section 6a).
- Confidence thresholds too strict in practice (Section 5a).

All 9 sections approved 2026-05-17 in turn-by-turn confirmation with Ahmed.
