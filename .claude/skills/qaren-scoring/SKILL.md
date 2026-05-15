---
name: qaren-scoring
description: Use when touching deterministic scoring, scoring_service.py, value badges, tradeoff pairs, dimension winners, personalization caps (plus or minus 30/10/5 percent), prompt personalities, trust validation, behavioral profiles, behavior_service.py, scoring_method enum, or the three-layer personalization system.
last_verified: 2026-05-16
update_when_changing:
  - app/services/scoring_service.py
  - app/services/prompt_personalities.py
  - app/services/trust_validation_service.py
  - app/services/behavior_service.py
  - app/models/scoring_v2.py
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
- `scoring_method`: `category_weighted` (anon), `personalized` (explicit), `behavioral` (behavior/session active), `invitee_quiz` (referral landing).
- `VALID_PRIORITIES`: original 8 + 6 cohort enums (`quality_reliability`, `best_price`, `trusted_brand`, `warranty_support`, `design_aesthetics`, `value_for_money`). `VALID_BRAND_ATTITUDE` adds `trust_known_brands`.

## Bundle E scoring_v2 contract (Phase 1 backend foundation)

- `app/models/scoring_v2.py` — Pydantic `Dimension` + `OverallScore` + `ScoringV2` with evaluative-language validator (13 banned words: best/pick/excellent/great/recommend/winner/worst/better/worse/beats/smart/good/choose).
- **3-core-keys invariant** (price/reviews/value exact set) + max-6-dim invariant.
- `scoring_service.calibrate_score()` — 60-95 perceived-score curve with floor + honesty guard.
- `scoring_service.build_dimensions_v2()` — emits 3 core + 0-3 contextual; skips any dim where either product lacks data (no empty rows).
- `app/services/verdict_builder.py::build_factual_verdict()` — composes factual line from top 3 winning core deltas + conditional alternative ("If you want X, the Y fits").
- `fact_check_service.build_fact_check` no longer emits `overall_confidence` key by default; new `is_data_freshness_shaky()` predicate fires the pill only when ≥2 shakiness conditions met on BOTH products.
- `response_builder` emits `scoring_v2` alongside legacy `scoring` for one release cycle (legacy slated for removal in Bundle F).

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
