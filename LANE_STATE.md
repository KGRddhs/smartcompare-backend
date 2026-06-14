# LANE_STATE — L5 / QA (genuine-cascade regression net)

**Branch:** `feature/s3-qa-genuine-cascade` (synced from origin/main @ 41365a1)
**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l5`
**Owner:** L5 (Opus)
**Prior:** L5 carried-bugs lane MERGED to main (`59ec212`); fan_out F1 fix shipped.

## Current task
**ROLLBACK (2026-06-14): genuine-BH merge REVERTED (main=3db3ddc) for a prod-latency regression.** Rebased onto rolled-back main. Added the A5 LIVENESS invariant (team-lead's high-value ask) — the guard that would've caught the regression. Net: 11 passed, 5 xfailed. Holding for L1's consolidated re-merge (fix-A + fix-B + ce0a78e).

## Rollback context (the lesson)
My Q1 CONTRACT net (ORDER/labels, 7/7) was correct at the contract level but a MOCKED unit net structurally CAN'T catch a prod-RUNTIME bug: the re-order escalated genuine-BH scraping to rendering GLOBAL pages (samsung.com/us, amazon.ae), blew the 15s Phase-1 price-race timeout, and returned None (no price) instead of the parked converted price. Regression: price→no-price on electronics. **Fix = the A5 liveness invariant below (belongs in the cross-cutting net so it can't recur).** Saved to memory [[feedback_mock_hides_bug_layer_false_green]] family.

## Status

## Status
- **NET STATE on rolled-back main (3db3ddc): 11 passed, 5 xfailed.** `tests/test_cascade_order_regression_qa.py`.
- **A1/A2/A3/A4a contract invariants → GREEN** on the rolled-back (pre-genuine-BH) base. A2 mutation-tested (force local_bhd on converted path → RED → restore green = real discriminating power).
- **A5 LIVENESS invariant → GREEN + MUTATION-PROVEN (the rollback lesson, team-lead's high-value ask).** 3 tests: escalation fan_out TIMES OUT / RAISES → `_get_price` still returns a non-None price (Tier-2 converted OR Tier-3 estimate), NEVER `{amount: None}`. Mutation-tested: injected the regression shape (timeout handler → `return {amount: None}`) and BOTH timeout liveness tests went RED → restored green. So it genuinely catches the exact prod regression the contract net missed. Mocked at `_get_price` but exercises the REAL escalation→fallthrough control path. Aligns with tasks #22 (fix-A) + #24 (prod-latency never-None).
- **A4b is_render_only + Fix-B (6 tests) → ALL xfail-strict** — the genuine-BH merge was fully reverted (field + 5 domains + two-wave `_build_escalation_scrapers(wave=...)` split gone from main). The set flips green TOGETHER when L1's consolidated re-merge lands. Contract pinned: (i) field, (ii) helper sig incl. sharafdg-False, (iii)a curl-skip=0, (iii)b render=2, **+ (Fix B) `test_render_wave_skips_global_url_fix_b`: a GLOBAL url (samsung.com/us) → 0 render scrapers** — THE prod regression's fix (render-on-global blew the 15s cap → None). 
- **VERIFIED AGAINST L1's fast-follow `5a4f614`** (NOT yet on main; team-lead re-merging): checked out L1's full branch tree, ran my net → **16/16 with --runxfail** (all 6 is_render_only/Fix-B xfails flip to real green; A1-A5 stay green). So the contract is pinned to L1's ACTUAL code, not a guess. (Recovered cleanly to my branch — used a transient detached-checkout; one stash use to swap, fully reversed + dropped. NOTE next time: use temp-file copy, not stash, to stay strictly no-stash.)
- **Q4 baseline** — security regression **103/104** (the deferred GOOGLE-DIAG console.log, unrelated frontend).
- **Q2** (team-lead self-runs the smoke20 gate) — I feed cascade-contract failures.
- **Q3** (reactive) — supplement-timeout watch HELD per team-lead until L1's fix-A+B lands.
- **NEXT:** when L1's consolidated branch re-merges TO MAIN: (1) rebase, (2) re-run full Q1 net + A5 liveness as the live regression guard, (3) the 6 strict-xfails flip to loud xpass → drop all 6 markers + confirm real green, (4) report. (Don't drop markers against the unmerged feature branch — wait for main, the canonical ref.)

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
