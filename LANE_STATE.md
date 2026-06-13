# LANE_STATE — L5 (carried bugs + engine-error adjudication)

**Branch:** `feature/s3-l5-carried-bugs`
**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l5`
**Owner:** L5 (Opus)

## Current task
L5.3 — lever-1 orphaned price task cancel cleanup (structured cancellation / try-finally).

## Last commit SHA
- L5.1 `575cacf` — fetch_retailer_quotes Serper budget double-count fixed (manual `record_usage` removed; search_web owns meter). 10/10 green.
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
