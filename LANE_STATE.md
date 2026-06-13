# LANE_STATE — L5 (carried bugs + engine-error adjudication)

**Branch:** `feature/s3-l5-carried-bugs`
**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l5`
**Owner:** L5 (Opus)

## Current task
GATE FINDINGS BEING FIXED (2026-06-13). Gate found ZERO confirmed bugs in finders+adversarial-verify; completeness critic caught 1 real MEDIUM (F1) + 2 LOW framing (F2/F3). F1 REPRODUCED + FIXED (verify-first per team-lead). F2/F3 reframed. Awaiting focused re-review on the delta, then L5 merges first.

## Disposition table (team-lead rulings ACK'd 2026-06-13; gate findings folded in)
| Item | Disposition | team-lead ruling | Evidence |
|---|---|---|---|
| L5.1 | **FIXED** (`575cacf`) + **F2 reframe** | gate F2 LOW: reframe as LATENT/dormant hygiene, not active 2x drain | manual `record_usage` removed from `fetch_retailer_quotes` (ZERO prod callers; rating_service.py:296 is a correct single-count direct-POST); RED→GREEN `test_fetch_does_not_double_count_serper_budget` |
| L5.2 | **VERIFY + CLOSE** (`700b575`) | "if genuinely wired at BOTH sites, do NOT re-wire; pin with e2e test = valid VERIFY+CLOSE" | write apex-normalizes (cache_service.py:144-145) + read probes apex; 2 e2e round-trip tests prove uae.sharafdg.com→sharafdg.com record+read |
| L5.3 | **FIXED** (`b386be8` + **F1 fan_out fix**) | gate F1 MEDIUM fix-before-merge: the `_price_task.cancel()` was ABSORBED inside fan_out's as_completed loop (price_service.py:1221 `except CancelledError: continue`) → scrapers ran to completion. VERIFIED (real-fan_out repro) + FIXED | `_cleanup_orphan_price_task` (ssc) + **fan_out distinguishes outer cancel via `current_task().cancelling()>0` → cancels remaining scrapers + re-raises**; 3 new real-fan_out tests (2 were RED, now GREEN) + confirmation-cancel regression guard GREEN; full-chain through `wait_for(fan_out)` verified (propagates, settle 0.000s, scrapers stop) |
| L5.4 | **RE-DEFER RATIFIED** (`d9ba97c`) — #12 CLOSED + **F3 caveat** | team-lead ratified; gate F3 LOW: note "non-reproducible" is ASSERTED not demonstrated, flag elec-003 for specific S3 watch | elec-003 502 = isolated gateway transient (healthy neighbors, no Sentry capture, other-002 Dyson/Shark passed 200, query 3/200). CAVEAT: elec-003 never returned 200 in EITHER run (400 S1 / 502 S2); credit gate blocked an isolated re-run → non-reproducibility is inferred, not proven. WATCH elec-003 specifically at S3 full-200. |

## Commits (all pushed to origin/feature/s3-l5-carried-bugs)
- `575cacf` L5.1 — fetch_retailer_quotes Serper budget double-count (manual record_usage removed)
- `700b575` L5.2 — by_source subdomain attribution verified wired + end-to-end tests
- `b386be8` L5.3 — lever-1 orphaned price task cancel cleanup (try/except → _cleanup_orphan_price_task)
- `d9ba97c` L5.4 — engine-error adjudication (re-defer the elec-003 502 transient, evidence-complete)
- `b6585bd` **GATE F1 fix** — fan_out absorbs outer cancel → distinguish via `current_task().cancelling()`, cancel remaining scrapers + re-raise. + F2/F3 reframes.

## Regression evidence (post-gate-F1)
- All L5 test files + ALL fan_out consumers: **65/65 green** (test_lever1_orphan_cancel_i56, test_retailer_quotes, test_tier15_hit_rate_metric, test_scatter_gather_price [Bundle-E Task 2.2 invariants], test_fan_out_integration, test_wall_caps_i57, test_tier15_route_trace, test_tier15_timing).
- Streaming + phase1 batch: **37/37 green**.
- F1 full-chain proof: outer cancel through real `wait_for(fan_out)` propagates, settles 0.000s (was ~4.7s), both scrapers cancelled (neither completed).
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

**Gate F3 caveat (honest framing):** "non-reproducible" is ASSERTED, not demonstrated. elec-003 never returned 200 in EITHER measured run (400 in S1, 502 in S2) and the credit gate blocked an isolated cold re-run, so I could not positively show a 200. The evidence (healthy neighbors, no in-app Sentry capture, near-identical other-002 passing, query 3/200) makes a deterministic code crash unlikely but does not PROVE non-reproducibility. → **elec-003 is flagged for SPECIFIC watch at the S3 full-200**; a second 502/400 there escalates to a focused crash investigation.

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
