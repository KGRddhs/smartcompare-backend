# LANE_STATE — L5 (carried bugs + engine-error adjudication)

**Branch:** `feature/s3-l5-carried-bugs`
**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l5`
**Owner:** L5 (Opus)

## Current task
ALL 4 L5 ITEMS DISPOSITIONED — gate-ready. L5.4 re-defer awaiting team-lead ratification. ADJUDICATION below.

## Commits (all pushed to origin/feature/s3-l5-carried-bugs)
- `575cacf` L5.1 — fetch_retailer_quotes Serper budget double-count (manual record_usage removed)
- `700b575` L5.2 — by_source subdomain attribution verified wired + end-to-end tests
- `b386be8` L5.3 — lever-1 orphaned price task cancel cleanup (try/except → _cleanup_orphan_price_task)
- `d9ba97c` L5.4 — engine-error adjudication (re-defer the elec-003 502 transient, evidence-complete)

## Regression evidence (gate-ready)
- 3 touched test files together: 33/33 green.
- Broader batch (streaming, phase1 guards, per-race timeouts, wall caps, tier15 route/registry, source router, settle window, cost dashboard): 95/95 green.
- KNOWN pre-existing flake (NOT mine): `test_phase1_runs_reviews_in_parallel_with_specs_price` (<1.2s wall) — fails identically on clean HEAD; dummy-key 401 network-retry noise on un-mocked image/rating siblings (no .env in worktree). Load-sensitive-wall caveat.

### L5.4 adjudication (evidence-complete)
S2 full-200 = `C:/Users/SynAckITPC/Documents/ai/smartcompare/.qa-bias-rerun/s2_exit_full200.jsonl`. 11 error rows of 200:
- **10× http_400** — ALL category `other`, ALL home-appliances (blenders/kettles/water-heaters/vacuums/IPL/irons/fans/microwaves/air-coolers), ALL wall ≈30.3-30.6s (at cap), contiguous block other-007→other-019. = the **Serper counter/key outage**: Sentry PYTHON-FASTAPI-6 shows 480 events of "Search error: 400 Bad Request google.serper.dev/search" (culprit get_gcc_prices). Depleted key → Serper 400 → both products no data → service returns success:false (INSUFFICIENT_DATA) → text_routes.py:171 raises HTTPException(400). By-design graceful degrade under outage, NOT an engine defect.
- **1× http_502** — `elec-003` (Dyson V15 vs Shark Stratos), wall 17.3s (UNDER cap). = the lone TRUE engine error.

**Root-cause of the 502 → isolated non-reproducible transient (gateway-level), re-defer (no code fix):**
1. Healthy neighbors both sides: elec-001/002/004/005/006 all http 200, 15-19s, weighted up to 1.0 — engine healthy at that point in the run.
2. NO captured in-app exception in Sentry (no Python unhandled/OOM/worker-crash issue exists; only the Serper-400 + an unrelated auth-refresh). A 502 with no `before_send` capture = the Railway proxy returned it because the worker connection dropped / upstream hiccup, not an app raise.
3. NO product-specific deterministic crash: a near-identical Dyson-vs-Shark query **other-002 (Dyson Airwrap vs Shark FlexStyle) passed http 200 cleanly at 19s**. If V15/Stratos triggered a code crash, other-002 would crash too.
4. Position = query 3 of 200 → the L5.3 orphan-leak theory doesn't apply (no accumulation yet).

Defensive coverage already shipped/present: L5.3 orphan-cancel hardens the cancel-path engine-error class; INSUFFICIENT_DATA 400-handling covers the all-MISSING path. Recommend: monitor for 502 recurrence in S3 full-200; if it reproduces deterministically on elec-003, open a focused crash investigation then. Fabricating a fix now = a fix for a hypothetical bug (feedback_curl_test_vs_production_code anti-pattern).

## Last commit SHA
- L5.1 `575cacf` — fetch_retailer_quotes Serper budget double-count fixed (manual `record_usage` removed; search_web owns meter). 10/10 green.
- L5.2 `700b575` — by_source subdomain attribution verified already-wired both sides + 2 end-to-end round-trip tests. 21/21 green.
- L5.3 DONE (committing) — lever-1 (`_price_task = ensure_future(...)` at ssc:2207) had NO orphan cleanup. Between the speculative kickoff and the Phase-1 gather, a raise (unified search / drug lookup) OR external cancel (outer STREAM_HARD_CAP wait_for) left the price task running in background (scrapers burning). Fix: wrapped the pre-gather window + gather in `try/except BaseException` → `_cleanup_orphan_price_task()` (cancel+drain if not done) then re-raise. No-op on happy path (task already done at gather return → byte-identical behavior). TDD: 2 RED→GREEN tests (raise-in-window + parent-cancel) in `tests/test_lever1_orphan_cancel_i56.py`; I5.6 latency-stack 4/4 still green. NOTE: `test_phase1_runs_reviews_in_parallel_with_specs_price` fails on THIS box but PROVEN pre-existing (fails identically on clean HEAD — dummy-key 401 network-retry noise on un-mocked image/rating siblings pushes wall >1.2s; load-sensitive-wall caveat).
- L5.2 DONE (committing) — VERIFIED already-wired on both sides, no re-wire needed:
  - WRITE: `record_tier15_hit` (cache_service.py:144-145) calls `match_registry_apex` on raw host before incrementing.
  - READ: `_aggregate_source_hits` probes apex keys via `_registry_domains()`.
  - CALLER: structured_comparison_service.py:2900 passes un-normalized retailer host (only www. stripped) → normalization is real.
  - Existing tests pinned write-norm + read-apex SEPARATELY; added 2 END-TO-END round-trip tests (uae.sharafdg.com→sharafdg.com, www.noon.com→noon.com) chaining write→read through the real reader. 21/21 green in test_tier15_hit_rate_metric.py.

## Mission (4 carried bugs, TDD)
- **L5.1** `fetch_retailer_quotes` double-count. NOTE: function lives in `app/services/review_service.py:304` (NOT price_service.py). `tests/test_retailer_quotes.py` already pins 3-distinct-retailer behavior at the function level → double-count is likely at a CALLER aggregation site or how quotes feed review counts. Investigate callers first.
- **L5.2** verify `match_registry_apex` (source_router.py:151) wired at `by_source` write+read.
  - WRITE: `record_tier15_hit` (cache_service.py:144-145) DOES call `match_registry_apex`. ✓
  - READ: `_aggregate_source_hits` (cache_service.py:265) probes apex keys via `_registry_domains()`. ✓
  - CALLER: `structured_comparison_service.py:2900` passes un-normalized `win_domain` (only `www.` stripped) → normalization happens at write. ✓
  - DISPOSITION: appears already-wired both sides → pin with integration test (uae.sharafdg.com → sharafdg.com end-to-end). Confirm no gap.
- **L5.3** lever-1 orphaned price task cancel cleanup. `fan_out_price_lookup` under `asyncio.wait_for(timeout=12.0)` at structured_comparison_service.py:2881. Add structured cancellation / try-finally. Test cancel path.
- **L5.4** adjudicate 1 TRUE engine error from S2 full-200. Source JSONL = `C:/Users/SynAckITPC/Documents/ai/smartcompare/.qa-bias-rerun/s2_exit_full200.jsonl` (54 KB, Jun 12 13:06). 10/11 errors = counter/key outage; find the 1 true one.

## Blockers
None. CREDIT GATE: no full-200 / live-Serper runs without team-lead GO — using fixtures/unit tests.

## Handoff notes
- Ring cross-QA: L5 → L4 → L2 → L3 → L1 → L5. I QA L4's merge; L1 QAs mine.
- Discipline: TDD, path-restricted commits, push-per-commit, no-stash, ACK every team-lead message.
