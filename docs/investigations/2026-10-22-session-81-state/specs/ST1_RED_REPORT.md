# ST1 RED report: LOOP-STALL (ENABLE_USAGE_PATH_OFFLOOP)

- Unit: ST1 LOOP-STALL, flag `ENABLE_USAGE_PATH_OFFLOOP`, lane B for files (R-ST1-5). Agent: RED, Opus 5.5. 2026-10-23 01:45-03:10 AST.
- Real worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-st1`, HEAD 95cf6f864b4e70980ca191daa064c0118e223c13 before and after.
- Inputs read in full: s81-common.txt; RULINGS_ST1.md (whole); spec copy sha e4830eb3 (= the worktree spec); review copy sha 058677bf; PLAN_S81 standing constraints + M1 ST1 text; RULINGS_R0 R0-6/R0-7.
- Notes folder: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/ST1_red/` (notes.md, every log, literals, prototype diff `proto.diff`, mutation harness `mutate.py` + `mutants.py`, `mut_table.md`, comm set `comm/`).

## File written (the only change in the real worktree)

| path | bytes | sha256 |
|---|---|---|
| tests/test_s81_st1_usage_path_offloop.py | 114275 | feb447667a1fd2f5d239b4ae4e0eb3a7ddba13644030bdcec2262800e7a05cc5 |

Pure ASCII (0 bytes > 127), LF only, no 8-digit run, no sk-/eyJ/PEM/credentialed-URL shape. py_compile + ruff E9,F63,F7,F82 clean. Hermetic: fakes only; R33 talks to a loopback stub only; synthetic ids (`u-synthetic-1`); every flag the rows depend on set or deleted explicitly (autouse deletes ENABLE_USAGE_PATH_OFFLOOP, ENABLE_SYNC_DB_OFFLOAD, ENABLE_ASYNC_REDIS_OFFLOAD, ENABLE_PRICE_PATH_REDIS_OFFLOOP, REDIS_OFFLOOP_MAX_WORKERS, ENABLE_SUPABASE_CLIENT_REUSE, ENABLE_REVIEW_SOURCE_CONSULT, ENABLE_UNIFIED_SEARCH_BOUND, ENABLE_YOUTUBE_SOURCE; drops every redis-offloop pool before and after).

## Step 2: files the review listed as not measured

The computed list was EMPTY (the review's NOT MEASURED section names no test file). Nothing to run.

## Step 4: the unit file at base (real worktree)

`[pyt] tag=st1red-unit-base-final start=2026-10-23 02:41:01 end=2026-10-23 02:41:30 elapsed=30s bound=600s status=FAIL rc=1`
`232 failed, 281 passed`; `[hermeticity] sentinel checked 513 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
Exception types (recorded by a pytest hook on every failed phase): 232 x `call:AssertionError`, nothing else (no setup error, no ImportError/AttributeError). Failed node ids: `ST1_red/base_failed_final.txt`.
(An earlier run of a previous file revision: `[pyt] tag=st1red-unit-base start=2026-10-23 02:14:42 end=2026-10-23 02:15:20 elapsed=38s bound=600s status=FAIL rc=1`, same 232/281, all AssertionError.)

### Rows (RED = fails at base, PIN = passes at base; node counts)

| row | nodes | RED | PIN | what |
|---|---|---|---|---|
| r01 helpers exist, no run_db_offloop | 1 | 1 | 0 | R-ST1-1 |
| r02 flag reader truth table | 16 | 16 | 0 | |
| r03a pool dispatch independent of S77, shared pool, ctx copy, one build log | 2 | 2 | 0 | |
| r03b durable queued write lands after caller cancel | 1 | 1 | 0 | |
| r03c non-durable queued read dropped on cancel | 1 | 1 | 0 | S77 semantics |
| r05 get_usage_status ON placement (11 states x 8 combos), exact op multiset | 88 | 88 | 0 | GETs on pool; DB on main (sync OFF) / worker (sync ON) |
| r06 loop freeze (OP 0.15 s): sync OFF < 0.45 s, sync ON < 0.09 s | 2 | 2 | 0 | |
| r07 one gather: sync ON 4 reads overlap + wall < 0.40 s; sync OFF GETs overlap | 2 | 2 | 0 | |
| r08 ON == OFF == base literal (key order), both fns x 11 states | 22 | 0 | 22 | R-ST1-3 |
| r09 OFF base op sequence + threads, rotating OFF spellings, no pool, dispatcher spies 0 | 88 | 0 | 88 | B1 rule |
| r10 check_usage_allowed ON placement + base result | 88 | 88 | 0 | L6 multiset |
| r11 check ON reads both date-key counters on lifetime-free | 1 | 1 | 0 | |
| r12 consume unchanged (ops, threads, result) ON vs OFF == base literals | 88 | 0 | 88 | correction 3 |
| r13 refund unchanged (keyed + legacy) | 4 | 0 | 4 | |
| r14 dispatch failure fallback, sync_raise + async_raise, exact WARNING template | 4 | 4 | 0 | correction 4 |
| r15 cancel propagates, no fallback, no inline op after cancel | 2 | 2 | 0 | |
| r16 existing-helper full query chains (incl. update keys) == base | 18 | 0 | 18 | B2, R-ST1-2 |
| r17 ON path awaits _get_user_tier_info / _get_active_referral_bonus once | 4 | 0 | 4 | R-ST1-2 |
| r18 reviews L1 read ON on pool | 2 | 1 (s77_off) | 1 (s77_on) | correction 5 |
| r19 post-extraction write on pool, payload, save args | 2 | 2 | 0 | |
| r19b write dispatch failure logged once by type + swallowed | 1 | 1 | 0 | spec 2.6 template |
| r20 L2-promotion write inline + loop-atomic | 2 | 0 | 2 | RO17 |
| r21 three writes in order (first slowest), snapshot payloads | 1 | 1 | 0 | chain + deepcopy |
| r22 race cancel + request-loop end: queued write still lands, save ran | 1 | 1 | 0 | shield |
| r23 reviews OFF base sequence (3 paths x 2 S77) | 6 | 0 | 6 | B1 rule |
| r24 nocache reads no L1/L2 | 2 | 0 | 2 | |
| r25a source inventory | 1 | 1 | 0 | |
| r25b frozen AST digests (28 functions) | 28 | 0 | 28 | spec 2.7 + 4 additions |
| r25c db_offload gains no helper | 1 | 0 | 1 | R-ST1-1 |
| r26 /health shows the existing pool key after an ON read | 2 | 1 (on) | 1 (off) | |
| r27 /api/v1/usage/status bytes == base byte literal ON and OFF (4 states) | 8 | 0 | 8 | correction 1 |
| r28 flag read per call | 1 | 1 | 0 | |
| r28b reviews flag read once per call (mid-call flip) | 2 | 1 (on_then_off) | 1 (off_then_on) | |
| r30 GET keys are the date keys | 4 | 0 | 4 | |
| r31 probe-D saturation: 4 x 1.0 s jobs, 0.5 s cap, reviews returned, write lands after | 2 | 2 | 0 | R-ST1-4 |
| r32 write stores the snapshot though caller mutates (top + nested) | 1 | 1 | 0 | R-ST1-4 |
| r33 16 threads x 50 run_db calls, real admin factory, loopback stub (reuse off/on) | 2 | 0 | 2 | R-ST1-6, MEASURED green |
| r34 W4-13 45-scenario ledger unchanged with ST1 ON | 1 | 0 | 1 | R-ST1-3 |
| r35 one compute body: pure, == base literals, called once per call both states | 11 | 11 | 0 | R-ST1-3 |
| total | 513 | 232 | 281 | |

## Step 5: prototype (scratch worktree, thrown away; diff kept at `ST1_red/proto.diff`)

Design per the rulings: `ro.usage_path_offloop_enabled` + `ro.run_redis_offloop_pool` (shared pool, ctx copy, durable shield); `us._usage_reads_offloop` = keys on the loop, then `asyncio.gather(_get_user_tier_info, _get_active_referral_bonus, run_redis_offloop_pool(_get_redis_count, daily_key), run_redis_offloop_pool(_get_redis_count, monthly_key))`; `_usage_status_body` / `_usage_allowed_body` pure, called by both flag states; fork `except Exception` -> WARNING `[USAGE-OFFLOOP] dispatch failed fn=<fn> type=<T> -- inline fallback`; `rs._reviews_l1_write_offloop(cache_key, reviews, prev)` = deepcopy snapshot, a fire_and_forget task that waits for `prev` then `run_redis_offloop_pool(set_cached, ..., durable=True)`, dispatch failure logged by type; `get_reviews` reads the flag once, ON read via the pool, L2 save scheduled before the write, promotion write inline.

- flag unset: `[pyt] tag=st1red-proto-final-off start=2026-10-23 02:41:46 end=2026-10-23 02:42:02 elapsed=16s bound=600s status=OK rc=0` 513 passed; `[hermeticity] sentinel checked 513 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- flag exported on the runner call: `[pyt] tag=st1red-proto-final-on-env start=2026-10-23 02:42:04 end=2026-10-23 02:42:21 elapsed=16s bound=600s status=OK rc=0` 513 passed (the file sets every flag itself; ambient env inert).
- Earlier prototype runs: `[pyt] tag=st1red-proto-off ... 02:17:32 ... elapsed=18s status=OK rc=0`, `[pyt] tag=st1red-proto-on-env ... 02:18:02 ... elapsed=18s status=OK rc=0`, `[pyt] tag=st1red-proto2-off ... 02:21:33 ... elapsed=16s status=OK rc=0` (513 passed each).
- Prototype findings: (a) the sync-raise fallback leaves the two helper coroutine objects un-awaited (RuntimeWarning "coroutine ... was never awaited"); harmless, not pinned; GREEN may close them. (b) Under a NON-awaited write the race cancel never reaches the write task; the only thing that cancels it is the request loop's end (asyncio.run teardown in the test, process shutdown in production), so r22 kills "not shielded" through that path. (c) Under the non-awaited design the L2-save-before-write order has no suspension point to protect (M32 equivalent, Q1).

## Step 6: mutation table (37 mutants on byte copies of the prototype; whole unit file per mutant, bound 600; restore + sha256 verified every time; `.qa-mutation.lock` held in the scratch worktree)

Mutants M01-M37 ran on RED file revision 2b08d8de; the final file feb44766 differs only by the exception capture in r14 / r19b, so every mutant whose killers include r14 or r19b (M02, M08, M10, M15, M16, M23, M24, M34, M35) was re-run on the final file: identical kill sets (M15 and M34 now kill on AssertionError only). 35 KILLED, 2 SURVIVED (M21 equivalent by R-ST1-7; M32 for a ruling). Every kill is an AssertionError in the call phase.

| id | file | mutation | failed nodes | killing rows | verdict |
|---|---|---|---|---|---|
| M01 | redis_offloop.py | flag reader always True (not gated) | 106 | r02, r09, r23, r26, r28, r28b | KILLED |
| M02 | redis_offloop.py | flag reader always False | 206 | r02, r05, r06, r07, r10, r11, r14, r15, r18, r19, r19b, r21, r22, r26, r28, r28b, r31, r32 | KILLED |
| M03 | redis_offloop.py | drop .strip().lower() | 3 | r02 | KILLED |
| M04 | redis_offloop.py | run_redis_offloop_pool delegates to S77-gated run_redis_offloop | 105 | r03a, r03b, r03c, r05, r06, r07, r10, r15, r18, r19, r21, r22, r26, r28, r28b, r31 | KILLED |
| M05 | redis_offloop.py | no contextvars copy | 2 | r03a | KILLED |
| M06 | redis_offloop.py | durable branch without shield | 2 | r03b, r22 | KILLED |
| M07 | redis_offloop.py | private pool instead of the shared one | 5 | r03a, r03b, r03c, r26 | KILLED |
| M08 | usage_service.py | GETs via _get_redis_count_async | 189 | r05, r06, r07, r10, r14, r15, r25a, r26, r28 | KILLED |
| M09 | usage_service.py | Supabase reads dispatched to the redis pool (twin-like) | 88 | r05, r10 | KILLED |
| M10 | usage_service.py | four sequential awaits instead of one gather | 4 | r07, r14 | KILLED |
| M11 | usage_service.py | status body drops the lifetime-free display rule | 30 | r05, r08, r09, r27, r35 | KILLED |
| M12 | usage_service.py | status body monthly cap without bonus | 30 | r05, r08, r09, r27, r35 | KILLED |
| M13 | usage_service.py | allowed body daily > instead of >= | 14 | r08, r09, r10, r35 | KILLED |
| M14 | usage_service.py | fork catches BaseException | 2 | r15 | KILLED |
| M15 | usage_service.py | fork without try/except | 2 | r14 | KILLED |
| M16 | usage_service.py | fork logs the exception text | 2 | r14 | KILLED |
| M17 | usage_service.py | flag read once per process (hoisted) | 46 | r09, r26, r28 | KILLED |
| M18 | usage_service.py | consume gathers via _usage_reads_offloop | 89 | r12, r25b[consume_comparison_credit] | KILLED |
| M19 | usage_service.py | check ON returns _usage_status_body | 113 | r08, r10, r11, r17, r35 | KILLED |
| M20 | usage_service.py | OFF tail computes inline (second compute copy) | 11 | r35 | KILLED |
| M21 | usage_service.py | date keys computed inside the pool job | 0 | - | SURVIVED, EQUIVALENT by R-ST1-7 |
| M22 | usage_service.py | both GETs read the daily key | 215 | r05, r06, r07, r08, r10, r11, r17, r27, r30, r35 | KILLED |
| M23 | usage_service.py | check fork condition negated | 135 | r09, r10, r11, r14 | KILLED |
| M24 | usage_service.py | flag read not first (a counter read before it) | 143 | r05, r06, r07, r09, r14, r15, r25a, r28, r30 | KILLED |
| M25 | usage_service.py | bonus query drops consumed_at IS NULL (B2) | 19 | r16, r25b[_get_active_referral_bonus] | KILLED |
| M26 | usage_service.py | tier query drops .single() (B2) | 19 | r16, r25b[_get_user_tier_info] | KILLED |
| M27 | review_service.py | post-extraction write awaited | 3 | r31, r32 | KILLED |
| M28 | review_service.py | no per-request chain | 1 | r21 | KILLED |
| M29 | review_service.py | no deepcopy (live dict written) | 6 | r19, r21, r31, r32 | KILLED |
| M30 | review_service.py | shallow copy | 1 | r32 | KILLED |
| M31 | review_service.py | write not durable (no shield) | 2 | r22, r25a | KILLED |
| M32 | review_service.py | L2 save scheduled after the write dispatch (spec M25) | 0 | - | SURVIVED (equivalent under the non-awaited design; for a ruling) |
| M33 | review_service.py | L2-promotion write moved to the pool | 5 | r20, r23, r25a | KILLED |
| M34 | review_service.py | ON L1 read ignores nocache | 2 | r19b, r24 | KILLED |
| M35 | review_service.py | write dispatch failure not swallowed/logged | 1 | r19b | KILLED |
| M36 | review_service.py | flag read twice (second read at the write site) | 2 | r28b | KILLED |
| M37 | review_service.py | ON L1 read through S77-gated run_redis_offloop | 3 | r18, r25a, r28b | KILLED |

Mutant [pyt] lines: 46 runs, all `status=FAIL rc=1` except M21 and M32 (`status=OK rc=0`), none TIMEOUT; full list `ST1_red/mut_pyt_lines.txt` and `ST1_red/all_pyt_lines.txt` (e.g. `[pyt] tag=st1red-mut-M01 start=2026-10-23 02:24:03 end=2026-10-23 02:24:25 elapsed=21s bound=600s status=FAIL rc=1`).

## Step 7: comm set at base (real worktree)

List `ST1_red/comm/comm_list.txt` (152 files, sha256 prefix 3ef806f92cfb8706), reasons `ST1_red/comm/comm_why.tsv`, builder `ST1_red/comm_build.py`: module grep (usage_service, review_service, redis_offloop, db_offload) UNION symbol grep (incl. consume / refund) UNION /health readers UNION source-scanning pins (named list, test_start_command*, every app/-by-path reader, the review adversary's globbers) UNION test_paid_route_metering.py UNION CLAUDE.md readers (test_ci_gates.py, test_behavior_dimension_translation.py + every test naming CLAUDE.md) UNION the W4-13 ledger pair; MINUS the four test_precommit_hook*.py and the new RED file; NETWORK_FLAKY_EXCLUDE nodes are in none of the files; no SmartCompareApp scanner (no client-visible change). Superset of the spec's 119 (+33).

| chunk | [pyt] | result | hermeticity | netguard |
|---|---|---|---|---|
| 00 | `[pyt] tag=st1red-comm-base-00 start=2026-10-23 02:50:23 end=2026-10-23 02:51:40 elapsed=78s bound=1200s status=OK rc=0` | 739 passed, 1 deselected | 739 | blocked 18 attempt(s) from 6 node(s) |
| 01 | `[pyt] tag=st1red-comm-base-01 start=2026-10-23 02:52:10 end=2026-10-23 02:55:33 elapsed=203s bound=1200s status=OK rc=0` | 1037 passed | 1037 | blocked 57 attempt(s) from 34 node(s) |
| 02 | `[pyt] tag=st1red-comm-base-02 start=2026-10-23 02:56:04 end=2026-10-23 02:56:35 elapsed=31s bound=1200s status=OK rc=0` | 579 passed, 4 deselected | 579 | blocked 2 attempt(s) from 2 node(s) |
| 03 | `[pyt] tag=st1red-comm-base-03 start=2026-10-23 02:56:46 end=2026-10-23 02:58:45 elapsed=119s bound=1200s status=FAIL rc=1` | 1063 passed, 26 skipped, 2 deselected, 1 xfailed, 2 errors | 1066 | blocked 2 attempt(s) from 2 node(s) |
| 04 | `[pyt] tag=st1red-comm-base-04 start=2026-10-23 02:59:07 end=2026-10-23 03:00:11 elapsed=64s bound=1200s status=OK rc=0` | 1722 passed, 1 skipped, 2 deselected | 1722 | blocked 20 attempt(s) from 8 node(s) |
| 05 | `[pyt] tag=st1red-comm-base-05 start=2026-10-23 03:00:16 end=2026-10-23 03:00:58 elapsed=42s bound=1200s status=OK rc=0` | 1049 passed, 10 skipped, 14 deselected, 35 xfailed | 1094 | blocked 65 attempt(s) from 21 node(s) |
| 06 | `[pyt] tag=st1red-comm-base-06 start=2026-10-23 03:01:05 end=2026-10-23 03:01:12 elapsed=7s bound=1200s status=OK rc=0` | 28 passed | 28 | blocked 0 attempt(s) from 0 node(s) |

Totals: 6217 passed, 37 skipped, 23 deselected, 36 xfailed, 2 ERROR. Base FAILED/ERROR set (`ST1_red/comm/base_failed.txt`) = exactly the two known cold-tiktoken nodes the spec 1.10 names: `tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable`, `tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence`. No FAILED node. The netguard blocks are the ratchet-baseline sentinel/egress class (e.g. `neutralized.supabase.invalid:443`, `api.openai.com:443`).

## Step 8: restore check

- sha256 of all 3410 tracked files of the real worktree at 03:03 == the 01:51 snapshot (`tracked_sha_before.txt` vs `tracked_sha_after.txt`, byte-identical).
- `git status --short` of the real worktree: `?? tests/test_s81_st1_usage_path_offloop.py` only; HEAD 95cf6f86.
- Scratch worktree `ST1_red/st1_scratch` (detached at 95cf6f86, no node_modules junction, no .env, lock removed) removed with `git worktree remove --force`; absent from `git worktree list`.
- No pytest process carrying an st1red tag is alive.

## Deviations from the spec (rulings applied; each a deliberate change to spec section 5/6)

1. Spec R4 (run_db_offloop) dropped (R-ST1-1); replaced by r01's absence assert, r25c (db_offload keeps exactly run_db + sync_db_offload_enabled) and r25a (usage_service keeps its 4 to_thread calls, no run_db_offloop).
2. Spec R16/R17 (twins) dropped (R-ST1-2); r16 is now the existing-helper chain PIN (full chains incl. the reset-update keys), r17 replaces the inverted spec R29 (the ON path awaits the existing helpers, PIN).
3. r05/r10 expect the Supabase reads on the loop thread with sync offload OFF and on a worker with it ON (R-ST1-1), plus the exact op multiset per state (B2).
4. r06 thresholds: sync OFF < 0.45 s (only the two Supabase reads stay inline), sync ON < 0.09 s; r07 split by sync state.
5. r19/r21/r22 rewritten for NON-awaited writes; new r31 (probe D) and r32 (snapshot); r22 reaches the write task through the request-loop end because a race cancel does not reach a non-awaited task.
6. r25a does not pin a write-helper name (the rulings give none): it pins "every run_redis_offloop_pool(set_cached, ...) is durable" module-wide, one non-durable pool read in get_reviews, the S77 read dispatch and the 4 direct set_cached calls, the flag check as the first statement of both usage functions, and accepts a lambda counter read (so M21 survives as ruled equivalent). The OFF-tail digest of correction 2 is dropped (R-ST1-3).
7. r25b adds four digests beyond spec 2.7 (`_atomic_consume_async`, `_get_redis_count_async`, `_bump_counters_async`, `_retrieve_quietly`); digests are 32 hex chars written in 4-char groups (no 8-digit run in the file).
8. r14 and r19b keep the spec 2.6 templates the rulings did not delete (`[USAGE-OFFLOOP] dispatch failed fn=<fn> type=RuntimeError -- inline fallback`, `[USAGE-OFFLOOP] reviews L1 write dispatch failed type=RuntimeError`), exactly one record each, no exception text in the log.
9. r27 extended to the free_lifetime and free_reset_past byte literals; r03c and r35 are new; r34 binds the W4-13 module's autouse guards as class-level staticmethods (class-scoped).
10. Comm set 152 files (spec 119 + 33) by the union rule.

## Open questions for the gate

- Q1 M32 (L2 save scheduled after the write dispatch) survives: no suspension point separates the two schedulings under a non-awaited write. Rule it equivalent, or ask for an ordering pin.
- Q2 R-ST1-4 says the response is never delayed. With consult/YouTube ON a design whose re-cache write awaits the previous handle INLINE would delay the response; the file pins only the baseline (consult OFF) saturation row. Rule whether a consult-ON saturation row is wanted.
- Q3 Accept the four extra r25b digests (consume / S77 internals ST1 must not touch).
- Q4 r35 binds the body signature positionally to (user_info, bonus, daily_used, monthly_used) and requires exactly one body call per public call in both states, including the OFF lifetime-free path of check_usage_allowed (the prototype passes 0, 0 there).
- Q5 r06 / r07 / r31 are timing rows (OP 0.15 s; 0.45 / 0.40 / 0.09 s bounds; four 1.0 s blockers vs a 0.5 s cap); green on this box with margin, a slow CI runner could need a ruling.
- Q6 The sync-raise fallback leaves two coroutine objects un-awaited (RuntimeWarning); not pinned.

## NOT MEASURED

- The comm set at HEAD and the local-env hazard run (GREEN's gates).
- Nothing timed out.
