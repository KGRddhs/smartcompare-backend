# LANE_STATE — L5 / QA (genuine-cascade regression net)

**Branch:** `feature/s3-qa-genuine-cascade` (synced from origin/main @ 41365a1)
**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l5`
**Owner:** L5 (Opus)
**Prior:** L5 carried-bugs lane MERGED to main (`59ec212`); fan_out F1 fix shipped.

## Current task
Q1 — integrated cascade-reorder regression net (failing-test-first). team-lead self-runs the smoke20 gate; I do NOT block measurement.

## Mission (S3 reopened — genuine BH pricing)
L1 (`feature/s3-genuine-price-cascade`) re-orders the price cascade (BH→web→US-converted→estimate-last), kills the gl=us→local_bhd mislabel (`b82af2a`), fixes supplement timeout. Big surface change to price_service.py / structured_comparison_service.py. **Regressions are the risk.**

- **Q1** (MINE, active): integrated end-to-end ORDER-invariant net over `_get_price`. Complementary to L1's per-fix TDD (do NOT duplicate `test_converted_price_before_estimate_t1`, `test_shopping_source_method_t2`, `test_price_plausibility_guard`).
  - A1 ORDER: genuine BH (local_bhd/shopify_json/page_scrape) preferred over converted_usd over estimated; estimate never wins if a real source returned.
  - A2 gl=us never stamped local_bhd (integration-level cross-check of b82af2a): original_currency != region currency -> converted_usd.
  - A3 estimated only when shopping + escalation + broader-search ALL empty/rejected.
  - A4 is_render_only (usage="review") sources stay OUT of the curl-harvest pool.
- **Q2** (team-lead self-runs): smoke20 gate when L1 says ready. I feed cascade-contract failures.
- **Q3** (reactive): watch supplement timeout under 30s cap (was ~50% timeout).
- **Q4**: security regression (103/104) + v2 invariants stay green — final full-net run.

## Key code anchors (post round-1 merge, pre-L1-reorder)
- `structured_comparison_service.py:3232-3236` — source_method honesty: `converted_usd` if original_currency != currency, else `local_bhd`.
- `:3268-3273` + `:3308-3318` — estimate-last stamping (`estimated` only after real sources fail).
- `price_service.py` source_methods: local_bhd(634,1451), page_scrape(838,861,882), shopify_json(1157), converted_usd(1364, iHerb).
- `source_router.get_sources_for_category(usage="price")` / `source_usage(url,cat)` — render-only exclusion (usage="review").

## Blockers
None. CREDIT GATE: NO live/smoke20/full-200 runs (team-lead owns the gate + OpenAI just refunded $5, be sparing). Fixtures/mocks only.

## Discipline
TDD failing-first; path-restricted commits; push-per-commit; no-stash; ACK every team-lead message; coordinate with L1 (no duplicate TDD).
