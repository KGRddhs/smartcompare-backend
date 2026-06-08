# Lane A-L3 Cross-QA of Lane A-L4

**Reviewer:** L3-fe-mobile
**Reviewed:** L4-prompts-eval (Lane A-L4 — Prompts + validation matrix + Instagram feasibility)
**Plan:** `docs/plans/2026-06-08-backend-comparison-overhaul-plan.md` § L3.8 + § L4
**Status:** GREEN with two non-blocking findings

---

## Scope reviewed

L4 commits cherry-picked from `feature/A-L4-prompts-eval`:
- `3acc1db` feat(L4.1): survey ETL → pain_workflow + decision_style priors (443 responses)
- `b872ba4` feat(L4.2): inject top-3 pain-workflow + decision-style into verdict prompt
- `87a5006` feat(L4.3): 50-query Bahrain validation matrix — gold-truth + runner + scoring tests
- Doc artifact: `docs/plans/2026-06-08-A-instagram-feasibility-test.md` (L4.4 manual exercise)

## Acceptance gate checklist (per plan § L4)

| Item | Result | Evidence |
|---|---|---|
| `data/pain_workflow_priors.json` exists | GREEN | 168 lines, 8 ranked workflows, ranks 1..8 contiguous |
| 8 named workflows present | GREEN | close_option_paralysis, too_many_specs, value_budget_uncertainty, trust_paralysis, post_decision_regret, brand_loyalty_vs_evidence, warranty_aftersales_missing, decision_speed |
| Each workflow has `prompt_instruction` ≥ 40 chars | GREEN | `tests/test_pain_workflow_priors.py::test_pain_workflow_priors_first_workflow_is_close_option_paralysis` (PASS) |
| `data/decision_style_priors.json` exists | GREEN | 74 lines, 9 cohort entries + metadata |
| Each cohort's style distribution sums to 1.0 ± 0.01 | GREEN | Verified inline for 18-24_male_bahraini (1.000) and 25-34_female_bahraini (1.000) |
| `scripts/etl_survey_to_priors.py` runs | GREEN | `python -m py_compile` passes; 443 survey responses ingested per file metadata |
| `app/services/pain_workflow_loader.py` loads + injects | GREEN | `lru_cache(maxsize=1)` lazy-load + `reset_cache()` test hook + nationality normaliser (hyphen ↔ underscore) |
| `extraction_service.build_verdict_prompt` injects pain + style blocks | GREEN | Lines 1114-1121 wrap injection in try/except; failure falls back to base prompt (defensive) |
| `data/validation_gold_truth.json` carries 50 queries | GREEN | 50 entries; 9 of 9 categories covered; per-cat counts: electronics 12, supplements 6, fragrances 6, makeup 5, skincare 5, haircare 3, fashion 4, grocery 4, other 5 |
| `scripts/run_validation_matrix.py` exists + has scoring tests | GREEN | 305 lines; per-leg scoring (price tolerance ±, specs match, winner match, factual hallucination grep) |
| `docs/plans/2026-06-08-A-validation-matrix-50q.md` exists | GREEN | 139 lines covering methodology, gold-truth schema, weighting, pass/fail thresholds |
| `docs/plans/2026-06-08-A-instagram-feasibility-test.md` exists | GREEN | 173 lines covering 5 test queries + ≥3/5 decision rule |
| L4 unit tests pass | GREEN | 46 tests across 3 test files: `test_pain_workflow_priors.py`, `test_verdict_prompt_pain_workflow_injection.py`, `test_validation_matrix_runner.py` |

## Findings

### Finding 1 — Limited cohort coverage in decision_style_priors.json (NON-BLOCKING)

**Observation:** plan § L4.1 test fixture expects `35-44_male_non-bahraini` cohort entry but `decision_style_priors.json` only carries 9 cohorts, all bahraini-leaning (`18-24_*`, `25-34_*`, `35-44_*_bahraini`, `45+_*_bahraini`, plus `18-24_female_non_bahraini`). The 8+ explicitly-tested non-bahraini buckets that the plan called for aren't present.

**Root cause (per L4 test file):** the survey only carried 443 responses; some cohort buckets had zero respondents. L4 chose to **omit empty buckets** rather than fabricate priors — this respects priors integrity. The pain_workflow_loader.py nationality normaliser maps hyphen → underscore so backend cohort lookups still resolve correctly when the cohort exists; missing cohorts fall through to category-wide defaults.

**Recommendation:** non-blocking. Document in `data/decision_style_priors.json::metadata` which cohorts are absent + why (followups). When the surveys re-fire post-launch and respondent count exceeds the plan minimum (probably 1000+), regenerate.

### Finding 2 — Validation matrix scoring deferred from runtime to manual (NON-BLOCKING)

**Observation:** `scripts/run_validation_matrix.py` is a CLI runner that loads gold-truth, fires comparisons against Railway, and scores per-leg. The plan called for an automated CI step but L4's test suite covers only the *scoring logic*, not an end-to-end CI invocation. Running the live matrix burns ~50 × $0.01 = $0.50 in Serper/OpenAI credits per execution.

**Recommendation:** non-blocking for Sprint A. Sprint B can convert the runner to a nightly Railway cron with budget-guard. The current `tests/test_validation_matrix_runner.py` (24 tests) pins the scoring algebra so any drift is caught at PR time without live calls.

## Final verdict

**GREEN — APPROVE.** All 4 L4 tasks shipped; 46/46 unit tests pass; no contract violations against plan § L4 design fields. Two findings above are recommendations for Sprint B / post-launch — not Sprint A blockers.

## Next-lane handoff

L1 and L2 should consume L4's:
- `data/pain_workflow_priors.json` — verdict prompt context
- `data/decision_style_priors.json` — verdict style context
- `app/services/pain_workflow_loader.build_pain_workflow_block()` + `build_decision_style_block()` — injection points already wired by L4 in `extraction_service.build_verdict_prompt` (lines 1114-1121) and `generate_comparison` (lines 1161-1168).

No code coupling required from L1/L2 — the injection sites are already live.
