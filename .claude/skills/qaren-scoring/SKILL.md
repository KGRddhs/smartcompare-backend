---
name: qaren-scoring
description: Use when touching deterministic scoring, scoring_service.py, value badges, tradeoff pairs, dimension winners, personalization caps (plus or minus 30/10/5 percent), prompt personalities, trust validation, behavioral profiles, behavior_service.py, scoring_method enum, or the three-layer personalization system.
last_verified: 2026-05-17
update_when_changing:
  - app/services/scoring_service.py
  - app/services/prompt_personalities.py
  - app/services/trust_validation_service.py
  - app/services/behavior_service.py
  - app/models/scoring_v2.py
  - app/services/response_builder.py
  - app/services/extraction_service.py (3-tier spec fallback, verdict prompt)
---

# Qaren Scoring + Personalization System

## Deterministic scoring (zero cost)

`scoring_service.py` computes **category-specific scores** from structured data — pure math, no API calls.
- Each of 9 categories has its own 6 dimensions via `CATEGORY_DIMENSIONS`. Old universal keys (`price_score`, `spec_score`) NO LONGER EXIST except in `other`.
- Price tiers: budget(<11 BHD), mid(11-57), premium(57-189), luxury(189+). Cross-tier uses expectations formula; same-tier uses spec/price blend.
- Personalization caps: explicit ±30%, behavioral ±10%, session ±5%.
- Outputs: dimension scores, value badges, tradeoff pairs, confidence indicators, dimension winners.
- Rollback V1 system in `docs/ROLLBACK_SCORING_V1.md`.

## Prompt personalities + trust validation

Each category gets unique GPT verdict tone via `build_personality_prompt(category)` — zero extra cost. `validate_verdict()` cross-checks GPT claims against deterministic scores (returns `winner_aligned`, `claims_flagged`, `confidence_adjustment`).

## Personalization (zero extra cost)

4 preference dimensions (collected once after first login): priorities (1-3 of 8 + 6 cohort-derived), budget (budget/mid/premium), lifestyle (0+ of 11 tags), brand attitude. Stored as JSONB in `public.users.preferences` with `_sources` sub-object marking each field `user_stated` or `inferred`. `GET/PUT /api/v1/auth/preferences`.
- **Three-layer system:** Explicit prefs (±30%) → Behavioral profile (±10%, decay-weighted 30-day half-life) → Session signals (±5%) → Category defaults.
- `_build_preferences_prompt()` appends to verdict prompt — zero extra API cost.
- `behavior_service.py`: category affinity, price range, winner agreement, dimension sensitivity. Fire-and-forget update after each comparison.
- `scoring_method` enum: `category_weighted` (anon), `personalized` (explicit), `behavioral` (behavior/session active), `cohort` (cohort priors moved the weights), `default` (`_empty_result` — fewer than 2 products), `invitee_quiz` (referral landing).
- **M20 #103 — `ENABLE_BEHAVIORAL_DIM_TRANSLATION` (default OFF)** gates two coupled fixes. (a) Stored profiles carry the LEGACY universal sensitivity keys `spec_score`/`review_score`/`price_score` (emitted by `behavior_service.TAB_DIMENSION_MAP`), which intersect the category dimension sets in exactly ONE place (`review_score` in `other`) — so the ±10% middle tier was dead for 8 of 9 categories. Flag ON, `apply_behavioral_adjustments(weights, profile, category)` re-keys legacy key → raw signal → the dim carrying that signal (inverting `_DIMENSION_SIGNAL_MAP`, one primary dim per key: `spec` never also `spec_secondary`). Translation happens at APPLICATION time, never at emission — rewriting the emitter would strand every profile already in the DB. (b) `scoring_method` is derived from what actually MOVED the weights (rounded to 4 decimals, the same rounding `weights_used` uses), precedence `personalized` > `behavioral` > `cohort` > `category_weighted`; a profile that changed nothing is no longer labelled `behavioral`, and an explicit preference is no longer shadowed by an inert profile. Flag OFF, both halves are byte-identical to the presence-keyed legacy behavior (guarded by `tests/fixtures/behavioral_flag_off_golden.json`).
- Behavioral price tiering (`behavior_service._compute_price_range`) uses the same category-aware `_detect_price_tier` / `PRICE_TIERS_BY_CATEGORY` ladder as scoring — UNFLAGGED. This is a real behavior change, NOT a no-op: the old flat 11/57/189 ladder called every electronics comparison over 189 BHD a `luxury` shopper while scoring puts electronics `luxury` at 2000. A row with no `category_used` passes `"other"` → the `other_light` sub-scale, which is 11/57/189/**500**/inf — so it is the legacy ladder only below 500 BHD; an uncategorized row at or above 500 now lands in `top_tier` where the flat ladder said `luxury`, and `tier_distribution` always carries the 5th `top_tier` key. Safe to ship unflagged because `price_range_preference` is WRITE-ONLY — it is persisted to `users.behavior_profile` and has zero readers in `app/` or `SmartCompareApp/src/`, so no score, verdict or client surface consumes it. Re-check that before giving it a reader.
- `VALID_PRIORITIES`: original 8 + 6 cohort enums (`quality_reliability`, `best_price`, `trusted_brand`, `warranty_support`, `design_aesthetics`, `value_for_money`). `VALID_BRAND_ATTITUDE` adds `trust_known_brands`.

## Bundle E scoring_v2 contract (Phase 1 backend foundation)

- `app/models/scoring_v2.py` — Pydantic `Dimension` + `OverallScore` + `ScoringV2` with evaluative-language validator (13 banned words: best/pick/excellent/great/recommend/winner/worst/better/worse/beats/smart/good/choose).
- **3-core-keys invariant** (price/reviews/value exact set) + max-6-dim invariant.
- `scoring_service.calibrate_score()` — 60-95 perceived-score curve with floor + honesty guard.
- `scoring_service.build_dimensions_v2()` — emits 3 core + 0-3 contextual; skips any dim where either product lacks data (no empty rows).
- `app/services/verdict_builder.py::build_factual_verdict()` — composes factual line from top 3 winning core deltas + conditional alternative ("If you want X, the Y fits").
- `fact_check_service.build_fact_check` no longer emits `overall_confidence` key by default; new `is_data_freshness_shaky()` predicate fires the pill only when ≥2 shakiness conditions met on BOTH products.
- `response_builder` emits `scoring_v2` alongside legacy `scoring` for one release cycle (legacy slated for removal in Bundle F).

## Bundle C design patterns (Session 51 brainstorm — plan-pending, NOT yet implemented)

**Calibrated honesty** is the score-rendering north star: never punish a product for sparse data, never invent a low score, never apologize. Low/weird scores ONLY when the comparison itself is genuinely weird (cross-category, severe data gaps, 10×+ price spread).

- **5-tier budget enum:** `budget | mid | premium | luxury | top_tier` (Migration 024 extends `users.preferences.budget` CHECK). `TIER_EXPECTATIONS` adds `luxury: 0.88, top_tier: 0.90`.
- **`PRICE_TIERS_BY_CATEGORY`** replaces the flat `PRICE_TIERS` — category-aware breakpoints per electronics/supplements/fashion/fragrances/skincare/haircare/makeup/grocery.
- **`other` runtime sub-scale:** geometric-mean detection (`other_light` <30 / `other_mid` 30-300 / `other_high` 300-5000 / `other_ultra` 5000+) so a car comparison (gm=5477 → `other_ultra`) maps "budget" semantic to <5000 BHD, not <11 BHD. `_detect_price_tier(price, category, *, comparison_prices=None)`.
- **3-tier spec fallback** (gap-fill for non-negotiable specs): Tier 1 primary → Tier 2 targeted Serper+GPT-mini per missing field → Tier 3 GPT-4o knowledge synthesis batched. Stays inside `STREAM_HARD_CAP_SECONDS=25`. Output flag `inference_source="model_knowledge"` is QA-only, never user-visible.
- **Kill missing-data floor of 30** — `None` propagation instead of `MISSING_SCORE=50`. Dims with `null` scores silently omitted from `dimensions[]` (no "—" pill spam).
- **Dynamic value formula by priority** — `VALUE_FORMULA_BY_PRIORITY` dict: `price`=0.4 spec/0.6 price; `quality`=0.7/0.3; default=0.6/0.4. Coefficients NEVER exposed in API responses.
- **`comparison_quality` flag:** `"normal" | "weak" | "weird"`. When `weird`, verdict text carries context (no forced winner); hero suppressed; NO banner.
- **`personalization.applied_shifts[]`** carries direction (`up`/`down`) ONLY — never magnitude or coefficients.
- **`build_dimensions_v2` becomes thin adapter** sourced from `CATEGORY_DIMENSIONS` (drops hand-coded `_dim_dpi/_dim_popularity/_dim_build_quality`).
- **Confidence widget loosening:** drop `verified=True` requirement; `rating_strong` at `review_count >= 100`; `price_strong` accepts `shopping_count >= 3` even when one product estimated; `specs_strong` at `verified_pct >= 40` OR `citation_count >= 8`. Replace single-word banner with 3-leg pill row + tap-reveal "What we know" sheet. Price pill HIDDEN entirely when `source_method == "estimated"`.

**Three rules absorbed during brainstorm (apply to ALL scoring + personalization UI):**
1. No info banners — per-element microcopy only (`memory/feedback_no_info_banners.md`).
2. No backend internals in user-facing reveals (`memory/feedback_no_backend_internals_in_reveals.md`).
3. Never use "estimated" / "reference price" / "indicative" in UI — backend enum stays, UI silent on price provenance, disclosure in Terms (`memory/feedback_no_estimated_word_in_ui.md`).

Spec: `docs/superpowers/specs/2026-05-17-bundle-c-scoring-quality-design.md`. Plan: `docs/superpowers/plans/2026-05-17-bundle-c-scoring-quality.md` (170 tasks, 4-Opus team).

## Sources (verify against current code before recommending changes)

- `app/services/scoring_service.py` — `CATEGORY_DIMENSIONS`, `calibrate_score()`, `build_dimensions_v2()`, value badge logic
- `app/services/prompt_personalities.py` — `build_personality_prompt(category)`
- `app/services/trust_validation_service.py` — `validate_verdict()` → `{winner_aligned, claims_flagged, confidence_adjustment}`
- `app/services/behavior_service.py` — decay-weighted profiles (30-day half-life), category affinity, price range, dimension sensitivity
- `app/services/verdict_builder.py` — `build_factual_verdict()`, top-3 winning-delta composition
- `app/models/scoring_v2.py` — Pydantic models + banned-word validator
- Rollback V1: `docs/ROLLBACK_SCORING_V1.md`
- Design: `docs/plans/2026-05-13-results-quality-overhaul-design.md`, `docs/superpowers/specs/2026-03-08-smart-scoring-engine-design.md`
- Bundle E context: `docs/SESSION_BUNDLES.md` (Bundle E section, Phase 1)
