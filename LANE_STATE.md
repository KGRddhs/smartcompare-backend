# LANE_STATE — L5 (carried bugs + engine-error adjudication)

**Branch:** `feature/s3-l5-carried-bugs`
**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l5`
**Owner:** L5 (Opus)

## Current task
L5.2 — verify `match_registry_apex` wired at by_source write+read; pin integration test.

## Last commit SHA
L5.1 DONE (committing) — double-count was a manual `record_usage("serper")` at review_service.py:338, on top of search_web's internal meter (serper_service.py:94). Same class as F4/G2 (9ee695c) but in the dormant `fetch_retailer_quotes`. Removed manual call; kept `has_budget` gate + `track_serper_cost_fn`. New RED→GREEN test `test_fetch_does_not_double_count_serper_budget`; rewrote 2 stale tests that encoded the buggy 3-manual-record behavior. 10/10 green.

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
