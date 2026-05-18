# Bundle C v1 — Test Backlog (RED tests deferred to v1.1)

> Drafted by `test-bundle-c` for the D.9 v1.1 backlog memory update at
> Bundle C ship. After v1 merges, this file tracks which RED tests remain
> and which v1.1 backend task each one expects.

**Current sweep (post-A.4.7 retarget commit `892daad`):**

```
backend Bundle C: 122 GREEN / 27 RED / 2 skipped (Tier 3 v1.1)
frontend Bundle C: 26 GREEN + 7 snapshots / 0 RED
tsc: 0 errors
test_security_regression.py: 98/98
pre-existing fails on main HEAD: 8 (test_personalization model_dump trio,
  test_share_routes strips_personalization, test_backend_cleanup
  unused_imports — verified identical on main HEAD per commit baseline)
```

---

## RED tests grouped by triggering v1.1 backend task

### Group A — `_classify_value_match` (8 RED) — spec §4d
File: `tests/test_value_math.py`
- `test_classify_value_match[mid-mid-in_range]`
- `test_classify_value_match[mid-premium-above_range]`
- `test_classify_value_match[mid-budget-below_range]`
- `test_classify_value_match[mid-luxury-above_range]`
- `test_classify_value_match[mid-top_tier-above_range]`
- `test_classify_value_match[luxury-budget-below_range]`
- `test_classify_value_match[budget-top_tier-above_range]`
- `test_classify_value_match[top_tier-top_tier-in_range]`

**v1.1 trigger:** ship `app.services.scoring_service._classify_value_match(
*, user_budget, product_tier) -> 'in_range' | 'above_range' | 'below_range'`.
Compares user's stated budget tier vs detected product price tier (3f
geometric-mean sub-scale aware via `_detect_price_tier`). Pure function,
no I/O.

### Group B — `build_value_match_caption` (4 RED) — spec §4d
File: `tests/test_value_math.py`
- `test_value_match_caption_in_range_is_silent`
- `test_value_match_caption_one_tier_above`
- `test_value_match_caption_one_tier_below`
- `test_value_match_caption_two_plus_tier_above_appends_tradeoff`

**v1.1 trigger:** ship `app.services.response_builder.build_value_match_caption(
match_state, *, tier_delta=1, key_tradeoff=None) -> str`. Returns "" (silent)
for in_range, "Above your usual range" for 1-tier-above, "Within your range"
for 1-tier-below, "Above your usual range — but here's why" for 2+-tier-above
with tradeoff appended.

### Group C — `build_value_delta_text` (4 RED) — spec §4b
File: `tests/test_value_math.py`
- `test_delta_text_price_percentage_format` ("40% less")
- `test_delta_text_rating_stars_format` ("0.9 stars higher")
- `test_delta_text_value_with_priority_match_copy` ("Better value for your priority")
- `test_delta_text_value_no_priority_match_copy` ("Stronger value ratio")

**v1.1 trigger:** ship `app.services.response_builder.build_value_delta_text(
*, price_a=None, price_b=None, rating_a=None, rating_b=None, signal,
priority_match=False) -> str`. Per-signal formatter; replaces the existing
inline `f"{da} DPI vs {db} DPI"` patterns in `scoring_service.py:1818+`.

### Group D — `_classify_budget_mismatch` + prompt wiring (8 RED) — spec §4e
File: `tests/test_value_math.py`
- `test_classify_budget_mismatch[budget-product_tiers0-above]`
- `test_classify_budget_mismatch[budget-product_tiers1-above]`
- `test_classify_budget_mismatch[luxury-product_tiers2-below]`
- `test_classify_budget_mismatch[top_tier-product_tiers3-below]`
- `test_classify_budget_mismatch[mid-product_tiers4-None]`
- `test_classify_budget_mismatch[mid-product_tiers5-None]`
- `test_classify_budget_mismatch[premium-product_tiers6-None]`
- `test_budget_mismatch_passes_to_preferences_prompt`

**v1.1 trigger:** (a) ship `app.services.extraction_service._classify_budget_mismatch(
user_budget, product_tiers) -> 'above' | 'below' | None` — returns 'above'
only when ALL products above user tier, 'below' only when ALL below; None
when spans. (b) extend `_build_preferences_prompt(budget_mismatch=None)` to
inject natural-acknowledgement instruction when set (per spec §4e, NO UI
banner directive — prompt context only).

### Group E — response_builder integration shape (3 RED)
Files: `tests/test_structured_comparison_service.py`, `tests/test_personalization_bundle_c.py`
- `test_comparison_quality_in_response_metadata_payload`
- `test_full_response_payload_audit_no_magnitude_keys`
- `test_applied_shifts_list_is_default_empty_when_no_priorities`

**v1.1 trigger:** `build_comparison_response` currently takes 19 positional
kwargs (`product_data`, `comparison`, `scoring_result`, `product_names`, ...).
My tests use a simpler convenience signature (`products`, `comparison`,
`metadata={comparison_quality}`, `personalization={applied_shifts}`). v1.1
options: (a) add a convenience builder wrapper that round-trips
`metadata.comparison_quality` + `personalization.applied_shifts` through
the full kwarg interface, or (b) retarget my 3 tests to construct the
full 19-kwarg payload. Option (b) is cheap (~15min). Marking these as
pending until decision.

### Group F — Tier 3 v1.1 (2 SKIPPED — already deferred)
File: `tests/test_extraction_prompt_bundle_c.py`
- `test_inference_source_flag_internal_only` (`@pytest.mark.skip`)
- `test_response_builder_strips_inference_source` (`pytest.skip()`)

**v1.1 trigger:** ship A.4.8 — Tier 3 GPT-4o knowledge synthesis with
`inference_source='model_knowledge'` tagging. Remove `skip` markers + the
tests should pass once Tier 3 emits the flag in telemetry but strips it
from user-facing `specs[]`.

---

## What's GREEN at v1 ship

- All §2a missing-data None propagation (A.4.1).
- All §2c calibration band preserved.
- All §2g fabricated-defaults removal source-audit (A.4.2).
- All §2b last-resort `caption_key=limited_data` row (A.4.4).
- All §2h silent omission for null-both dims (A.4.9).
- All §3 PRICE_TIERS_BY_CATEGORY 5-tier breakpoints (A.5.1-5.5).
- All §3f geometric-mean `other` sub-scale.
- All §3b/3d Pydantic Literal 5-tier accept + 3-tier legacy backwards-compat.
- All §4a VALUE_FORMULA_BY_PRIORITY 8-row coefficients (A.6.1).
- All §5a confidence threshold loosening (A.7.1).
- §1b factual_verdict builder restoration (A.3.2).
- §1a pros/cons fix via response_format=json_object (A.3.1).
- §1c price pipeline gl=us fallback + Serper meter instrumentation (A.3.3-fix-1/-2).
- §2e comparison_quality detector + verdict-prompt instruction (A.4.5).
- §2f A.4.7 Tier 2 spec fallback (Serper+GPT-mini per missing non-negotiable).
- §7b personalization.applied_shifts qualitative-only contract (A.9.1).
- All frontend §3c BudgetPicker 5-tier (B.3).
- All frontend §5b 3-pill ConfidencePills + §5c hide-on-estimated (B.7).
- All frontend §6 DimensionBars hero + silent omission (B.5).
- All frontend §7a PersonalizationChip render (B.8).

## Infra patterns confirmed (lift candidates for v1.1)

1. **Module-level flag-cache reset fixture.** `_reset_flag_cache()` helper
   in `test_bundle_c_feature_flag.py` + `test_scoring_calibration_bundle_c.py`.
   Pattern: `monkeypatch.setenv(...)` + `monkeypatch.setattr(module,
   "_CACHED_FLAG", None, raising=False)` on setup AND teardown. Applies to
   any module-level cached env-var (e.g., the 4 A.2.x diagnostic flags
   `_PROS_CONS_DIAG_FLAG`, `_FACTUAL_VERDICT_DIAG_FLAG`,
   `_PRICE_PIPELINE_DIAG_FLAG` × 2). Backend already uses this in
   `tests/test_diagnostics_flag_gated.py` (A.10.1).

2. **Lazy-import + name-flexible test wrapper.** `_import_non_negotiable()`
   + `_import_preferred()` in `test_extraction_prompt_bundle_c.py` accept
   either spec-text canonical name (`NON_NEGOTIABLE_FIELDS_BY_CATEGORY`)
   or backend's actual name (`CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE`).
   Reduces test brittleness across cross-section naming drift.

3. **Frontend assertion helpers without @types/react-test-renderer.**
   `__tests__/_bundle_c_helpers.ts` uses `type ReactTestInstance = unknown`
   local alias instead of importing from `react-test-renderer` (no @types
   pkg installed). Helper passes opaque `unknown` tree to serialise step,
   no real loss of safety.
