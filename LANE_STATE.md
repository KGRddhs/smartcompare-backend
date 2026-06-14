# LANE_STATE — L5 / QA (genuine-cascade regression net)

**Branch:** `feature/s3-qa-genuine-cascade` (synced from origin/main @ 41365a1)
**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l5`
**Owner:** L5 (Opus)
**Prior:** L5 carried-bugs lane MERGED to main (`59ec212`); fan_out F1 fix shipped.

## Current task
Q1 net DONE incl. A4b (L1 contract confirmed). **REBASED onto merged main (b58abc8 — L1's cascade re-order + L4 KPI).** Regression-guard GREEN. Holding for L1's fast-follow (curl-skip + helper) → 2 strict-xfail flip green. team-lead self-runs the smoke20 gate.

## Status
- **REGRESSION-GUARD GREEN (team-lead's ask)** — rebased my QA branch onto `origin/main` b58abc8 (L1's cascade re-order `e33e13e` + locale-filter + 5 BH curl sources + L4 KPI now merged). Re-ran the full Q1 net against the merged code: **7/7 cascade-contract invariants still hold** (A1 order / A2 honest-label / A3 estimate-last / A4a usage=review). L1's re-order introduced NO regression to the cascade contract.
- **Q1 A1-A3 + A4a DONE** — all green; **mutation-tested** the A2 guard (force local_bhd on converted path → RED → restore green = real discriminating power, not a tautology). Complementary to L1's per-fix TDD.
- **A4b DONE (L1 contract confirmed 2026-06-14):** `is_render_only` is DISTINCT from `usage="review"` — 5 SPA sources (alosra/nasserpharmacy/bn.boots/bolo/**megamart** — 5 not 4) HAVE BH prices but need JS render. NUANCE: render-only is NOT excluded from `_harvest_candidate_urls`; the two-sided split is in `_build_escalation_scrapers(wave=...)` — wave="curl" SKIPS the curl scraper, wave="render" emits Firecrawl/Scrape.do. Merged-state split:
  - (i) `Source.is_render_only` field + 5 domains → ON MAIN → 2 tests GREEN.
  - (ii) `is_render_only_domain()` helper → NOT on main (L1 fast-follow ce0a78e, built+unpushed) → 1 test **xfail strict**. L1 final sig: bare-domain OR URL → bool; sharafdg URL → False (curl-tier). Test pins both.
  - (iii)a curl-EXCLUSION: `_build_escalation_scrapers(wave="curl")` emits 0 for render-only → NOT on main (fast-follow) → **xfail strict** (verified REAL `expected 0 got 1` via --runxfail). Control (non-render keeps curl scraper) GREEN.
  - (iii)b render-INCLUSION: `wave="render"` emits 2 (firecrawl+scrapedo) for render-only → **GREEN on main already** (render wave gated by should_fan_out, NOT by is_render_only). Pins the OTHER side of the two-sided contract — guards against a future change dropping render-only out of the render tier (= no price path at all).
  - **13 tests total: 11 passed, 2 xfailed.** L1's fast-follow built (ce0a78e, holding for team-lead go); L1 pings the merge SHA → I drop the 2 strict-xfail markers + confirm the loud-flip green.
- **Q4 baseline** — security regression **103/104** green = the EXPECTED baseline (team-lead's number). The 1 failure is pre-existing + unrelated: `authService.ts:480 console.log('[GOOGLE-DIAG]')` — the deferred Google-Sign-In diagnostic instrumentation (CLAUDE.md known-bug), a frontend .ts file my backend-test-only branch cannot have touched. My net coexists with on-main cascade/source/fan_out tests: 35/35.
- **Q2** (team-lead self-runs the smoke20 gate) — I feed cascade-contract failures.
- **Q3** (reactive) — supplement-timeout watch when L1's timeout fix lands.
- **NEXT:** when L1's re-order merges to main, re-run the Q1 net against it as the live regression guard; report any RED to team-lead immediately.

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
