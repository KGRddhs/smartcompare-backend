# ST1 LOOP-STALL (ENABLE_USAGE_PATH_OFFLOOP): correctness adversary report

- Unit ST1, lens correctness, agent: adversary (Opus 5.5), 2026-10-23 07:03-08:15 AST.
- HEAD verified: `feb39dc08cf4b5fb2405a71d2a4d80d27812c695` on `feature/s81-st1-usage-path-offloop` (unit worktree `sc-s81-st1`, `git status --short` empty at start and end; never written).
- Scratch: detached worktree `<scratchpad>/ST1_adv_correctness` at the same sha (no junction, no .env), removed at the end. Notes and logs: `<scratchpad>/ST1_adv/corr_*` (the `ST1_adv` folder also holds the earlier SPEC adversary's files, untouched).
- Inputs read: s81-common.txt, PLAN_S81 (standing constraints, VERIFY corrections, M1 ST1, flip order), RULINGS_ST1, GATE_ST1, GREEN report, PR_BODY draft, the CLAUDE.md diff, the RED file rows r19-r35.

## Verdict: SOUND (0 blocking, 0 major, 7 minor)

No behaviour defect found in the GREEN bytes. Flag OFF is byte-identical on every path the rows pin, and the OFF pins bite (my block-move C09 and spec mutants M01 / M17 are killed by r09 / r23 / r28). Under ON the usage reads run in one gather of the two unchanged helpers plus two pool GETs, the compute body is shared, the reviews writes are durable, non-awaited, chained snapshots, and FY19 holds at runtime (measured with the flag exported). The minors are pin gaps and documentation truth items; MIN-1 deserves an additive row in the fix round.

## Hashes (frozen RED file)

- RED file at HEAD: sha256 `b5ba0bab8586d75ed5fcc21075f0f440d72c7e754350d4d28a2255f4fa8f8337` (116,678 B, index blob LF); its first 114,275 bytes hash to the frozen `feb447667a1fd2f5d239b4ae4e0eb3a7ddba13644030bdcec2262800e7a05cc5` (prefix byte-identical; only r31b appended, GT-2). Re-hashed at start and end: unchanged. A fresh checkout writes it CRLF (autocrlf); the blob is LF.
- App files at HEAD = GREEN report: redis_offloop `955e25e5...`, usage_service `ec0492a1...`, review_service `5ec6eba6...`, CLAUDE.md `d5830ccf...`, db_offload `a61545c8...` (untouched, R-ST1-1).

## Runs (every pytest through pyt.py, one at a time, scratch worktree)

- `[pyt] tag=st1advc-unit-off start=2026-10-23 07:10:20 end=2026-10-23 07:10:52 elapsed=32s bound=600s status=OK rc=0` 515 passed; `[hermeticity] sentinel checked 515 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- `[pyt] tag=st1advc-unit-on start=2026-10-23 07:11:12 end=2026-10-23 07:11:37 elapsed=24s bound=600s status=OK rc=0` (flag exported) 515 passed; hermeticity 515; netguard 0. See MIN-6: this export is neutralised by the file's autouse fixture.
- `[pyt] tag=st1advc-r14-werror start=2026-10-23 07:49:34 end=2026-10-23 07:49:55 elapsed=21s bound=600s status=OK rc=0` (`-k "r14 or r15 or r19b" -W error::RuntimeWarning -W error::pytest.PytestUnraisableExceptionWarning`) 7 passed; hermeticity 7; netguard 0 (GT-6 verified).
- `[pyt] tag=st1advc-pins-on start=2026-10-23 07:50:21 end=2026-10-23 07:52:39 elapsed=138s bound=1200s status=FAIL rc=1` (GREEN's 28-file pin set, flag exported) 9 failed / 899 passed; hermeticity 908; `[netguard] blocked 2 attempt(s) from 2 node(s)` (the two test_paid_route_metering sentinel nodes of the base record). The 9 failed ids are EXACTLY the 9 listed in CLAUDE.md limit (13) and the PR body (verified node by node).
- `[pyt] tag=st1advc-fy19-on-green start=2026-10-23 07:28:51 end=2026-10-23 07:28:58 elapsed=7s bound=600s status=OK rc=0` (`tests/test_s75_fanout_starve.py -k FY19`, flag exported, GREEN bytes) 3 passed; hermeticity 3; netguard 0.
- `[pyt] tag=st1advc-probe start=2026-10-23 07:48:58 end=2026-10-23 07:49:05 elapsed=7s bound=600s status=OK rc=0` (my probe file in the scratch only) 6 passed; hermeticity 6; netguard 0. Results in `corr_probe_out.jsonl` (MIN-2, MIN-3).
- No `never awaited` / `never retrieved` line in either unit log (0 / 0).

## Mutation table (31 runs on sha-verified byte copies in the scratch; `.qa-mutation.lock` per mutant; restore sha256-identical every time; final scratch shas = HEAD)

Spec mutants re-applied (GREEN's definitions read as data, applied by my harness `corr_mutate.py`, whole unit file): all 11 KILLED by AssertionError only, kill counts identical to GREEN's table.

| id | mutation | result | rows | pyt |
|---|---|---|---|---|
| M01 | flag reader always True | KILLED 106 | r02 r09 r23 r26 r28 r28b | `[pyt] tag=st1advc-mut-M01 start=2026-10-23 07:55:18 end=2026-10-23 07:55:50 elapsed=31s bound=600s status=FAIL rc=1` |
| M04 | pool dispatcher delegates to the S77-gated helper | KILLED 106 | r03a-c r05 r06 r07 r10 r15 r18 r19 r21 r22 r26 r28 r28b r31 r31b | `[pyt] tag=st1advc-mut-M04 start=2026-10-23 07:55:56 end=2026-10-23 07:56:32 elapsed=36s bound=600s status=FAIL rc=1` |
| M06 | durable branch without shield | KILLED 2 | r03b r22 | `[pyt] tag=st1advc-mut-M06 start=2026-10-23 07:56:48 end=2026-10-23 07:57:28 elapsed=39s bound=600s status=FAIL rc=1` |
| M08 | counter GETs via the ASYNC_REDIS-gated helper | KILLED 189 | r05 r06 r07 r10 r14 r15 r25a r26 r28 | `[pyt] tag=st1advc-mut-M08 start=2026-10-23 07:57:33 end=2026-10-23 07:58:12 elapsed=39s bound=600s status=FAIL rc=1` |
| M10 | four sequential awaits | KILLED 2 | r07 | `[pyt] tag=st1advc-mut-M10 start=2026-10-23 07:58:26 end=2026-10-23 07:58:58 elapsed=32s bound=600s status=FAIL rc=1` |
| M17 | flag hoisted (read once per process) | KILLED 46 | r09 r26 r28 | `[pyt] tag=st1advc-mut-M17 start=2026-10-23 08:00:14 end=2026-10-23 08:01:01 elapsed=47s bound=600s status=FAIL rc=1` |
| M24 | flag read not first | KILLED 143 | r05 r06 r07 r09 r14 r15 r25a r28 r30 | `[pyt] tag=st1advc-mut-M24 start=2026-10-23 08:01:10 end=2026-10-23 08:02:13 elapsed=63s bound=600s status=FAIL rc=1` |
| M27 | write awaited on the response path | KILLED 5 | r31 r31b r32 | `[pyt] tag=st1advc-mut-M27 start=2026-10-23 08:02:28 end=2026-10-23 08:02:49 elapsed=21s bound=600s status=FAIL rc=1` |
| M31 | write not durable | KILLED 2 | r22 r25a | `[pyt] tag=st1advc-mut-M31 start=2026-10-23 08:02:55 end=2026-10-23 08:03:19 elapsed=24s bound=600s status=FAIL rc=1` |
| M33 | L2-promotion write to the pool (RO17) | KILLED 5 | r20 r23 r25a | `[pyt] tag=st1advc-mut-M33 start=2026-10-23 08:03:26 end=2026-10-23 08:03:46 elapsed=20s bound=600s status=FAIL rc=1` |
| M38 | re-cache awaits the previous handle inline (GT-2) | KILLED 2 | r31b | `[pyt] tag=st1advc-mut-M38 start=2026-10-23 08:04:32 end=2026-10-23 08:05:01 elapsed=29s bound=600s status=FAIL rc=1` |

Independent mutants (my own exact-once edits). "X19": no X19 mutant exists for ST1 (the brief's phrase is the `wf_unit_green.js` template leftover named in RULINGS_FIX1_S81_03 R-F1-C); I applied four hand block-moves in its place (C01, C02, C03, C09).

| id | mutation | result | rows / note | pyt |
|---|---|---|---|---|
| C01 (block move) | check_usage_allowed: a tier-info read placed before the ON fork | KILLED 143 | r09 r10 r14 r16 r17 r25a | `[pyt] tag=st1advc-mut-C01 start=2026-10-23 07:21:33 end=2026-10-23 07:23:27 elapsed=114s bound=600s status=FAIL rc=1` |
| C02 (block move) | get_reviews ON: the baseline L1 write moved OUT of the FY19 / error persist guard | SURVIVED (unit file) -> MIN-1 | killed only by `test_FY19_unified_timeout_writes_no_specs_or_reviews_cache` with the flag exported; green with it unset | `[pyt] tag=st1advc-mut-C02 start=2026-10-23 07:24:05 end=2026-10-23 07:26:00 elapsed=116s bound=600s status=OK rc=0`; `[pyt] tag=st1advc-mut-C02-on-fy19 start=2026-10-23 07:29:11 end=2026-10-23 07:29:22 elapsed=12s bound=600s status=FAIL rc=1`; `[pyt] tag=st1advc-mut-C02-fy19off start=2026-10-23 07:29:30 end=2026-10-23 07:29:37 elapsed=7s bound=600s status=OK rc=0` |
| C03 (block move) | deepcopy snapshot moved into the background task | KILLED 8 | r19 r21 r31 r31b r32 | `[pyt] tag=st1advc-mut-C03 start=2026-10-23 07:26:12 end=2026-10-23 07:26:56 elapsed=43s bound=600s status=FAIL rc=1` |
| C09 (block move) | check_usage_allowed OFF: counter reads above the lifetime-free return | KILLED 8 | r09 | `[pyt] tag=st1advc-mut-C09 start=2026-10-23 07:27:03 end=2026-10-23 07:27:36 elapsed=33s bound=600s status=FAIL rc=1` |
| C04 | tier-info / bonus swapped in the gather (would be masked by the except fallback) | KILLED 204 | r05 r06 r07 r10 r16 r17 r28 r30 r35 | `[pyt] tag=st1advc-mut-C04 start=2026-10-23 07:18:43 end=2026-10-23 07:19:41 elapsed=59s bound=600s status=FAIL rc=1` |
| C05 | daily / monthly GETs swapped | KILLED 164 | r05 r06 r07 r08 r10 r17 r27 r35 | `[pyt] tag=st1advc-mut-C05 start=2026-10-23 07:29:53 end=2026-10-23 07:30:28 elapsed=35s bound=600s status=FAIL rc=1` |
| C06 | `asyncio.ensure_future` instead of `fire_and_forget` (write task out of the drain registry) | SURVIVED -> MIN-4 | no row | `[pyt] tag=st1advc-mut-C06 start=2026-10-23 07:30:37 end=2026-10-23 07:31:19 elapsed=41s bound=600s status=OK rc=0` |
| C07 | durable branch of run_redis_offloop_pool drops `_retrieve_quietly` | SURVIVED -> MIN-5 | no row | `[pyt] tag=st1advc-mut-C07 start=2026-10-23 07:36:56 end=2026-10-23 07:38:05 elapsed=69s bound=600s status=OK rc=0` |
| C08 | write helper returns `prev` (chain skips a link) | KILLED 1 | r21 | `[pyt] tag=st1advc-mut-C08 start=2026-10-23 07:31:55 end=2026-10-23 07:33:15 elapsed=80s bound=600s status=FAIL rc=1` |
| C10 | ON fork drops its `return` | KILLED 110 | r05 r06 r07 r16 r17 r28 r30 r35 | `[pyt] tag=st1advc-mut-C10 start=2026-10-23 07:33:31 end=2026-10-23 07:34:16 elapsed=45s bound=600s status=FAIL rc=1` |
| C11 | consult re-cache not chained | KILLED 1 | r21 | `[pyt] tag=st1advc-mut-C11 start=2026-10-23 07:34:31 end=2026-10-23 07:35:21 elapsed=51s bound=600s status=FAIL rc=1` |
| C12 | YouTube re-cache not chained | KILLED 1 | r21 | `[pyt] tag=st1advc-mut-C12 start=2026-10-23 07:38:23 end=2026-10-23 07:39:07 elapsed=45s bound=600s status=FAIL rc=1` |
| C13 | reader accepts only "true" | KILLED 4 | r02 | `[pyt] tag=st1advc-mut-C13 start=2026-10-23 07:39:13 end=2026-10-23 07:40:01 elapsed=48s bound=600s status=FAIL rc=1` |
| C14 | check_usage_allowed fallback without the WARNING | KILLED 2 | r14 | `[pyt] tag=st1advc-mut-C14 start=2026-10-23 07:40:21 end=2026-10-23 07:41:51 elapsed=90s bound=600s status=FAIL rc=1` |
| C15 | in-task write failure re-raised | KILLED 1 | r19b | `[pyt] tag=st1advc-mut-C15 start=2026-10-23 07:42:10 end=2026-10-23 07:43:19 elapsed=69s bound=600s status=FAIL rc=1` |
| C16 | ON bypasses the whole persist guard (`if offloop or (...)`) | SURVIVED (unit file) -> MIN-1 | killed by FY19 with the flag exported only | `[pyt] tag=st1advc-mut-C16 start=2026-10-23 07:43:38 end=2026-10-23 07:44:53 elapsed=75s bound=600s status=OK rc=0`; `[pyt] tag=st1advc-mut-C16-on-fy19 start=2026-10-23 07:46:41 end=2026-10-23 07:47:17 elapsed=37s bound=600s status=FAIL rc=1` |
| C17 | GT-6 close loop `except BaseException` -> `except Exception` | SURVIVED, EQUIVALENT (nothing can raise a BaseException while building four coroutine objects) | - | `[pyt] tag=st1advc-mut-C17 start=2026-10-23 07:45:01 end=2026-10-23 07:46:02 elapsed=61s bound=600s status=OK rc=0` |

Counts: 31 runs; on the unit file 24 KILLED, 5 SURVIVED (C02, C16 non-equivalent pin gap; C06, C07 unpinned claims; C17 equivalent); the three FY19 cross-checks behave as stated. Every kill is an AssertionError (checked per log; no other exception type).

## Claims probed against the code (hold unless a minor says otherwise)

- Flag-OFF identity: OFF `get_usage_status` / `check_usage_allowed` call the same helpers in the base order (lifetime-free OFF reads no counter: C09 killed by r09), `get_reviews` OFF is the base code path (the only OFF change is a local `l1_write = None` and the `if not offloop:` wrappers around unchanged calls); r23 / r27 / r34 green in my runs. Holds.
- Reader idiom, read per call, first statement of both public functions, once per get_reviews call: verified at `redis_offloop.py:119`, `usage_service.py:661/775`, `review_service.py:722`; M17 / M24 / C01 killed.
- R-ST1-1 / R-ST1-2: no new to_thread, no DB twin, the two helpers byte-unchanged (r25b 28 digests counted at RED file lines 1032-1059); db_offload.py untouched.
- Error-handler mapping and the contract freeze (PLAN_S80 section 0 via the common brief): no new key, status or code on any route; an ON failure re-raises the base exception from the inline fallback, so the envelope is unchanged (probe: TypeError in both states). The only additive surface is `/health redis_offloop_pool` appearing once the pool exists (ST1 ON can build it with S77 OFF; r26).
- Billing R-A3: `consume_comparison_credit`, `_refund_credit_sync`, `refund_comparison_credit`, the key helpers and `_atomic_consume*` are AST-digest pinned (r25b) and unedited; `check_usage_allowed` has no production caller (grep of app/: only `usage_routes.py` imports `get_usage_status`). Holds.
- FY19 under ON (GREEN bytes, flag exported): the D5-timeout context writes no reviews L1 / L2 row and the honest Serper-failure payload still writes (3 passed). Holds at runtime; unpinned in CI (MIN-1).
- CLAUDE.md limit (13) node list: exact (9 / 9).
- GREEN report anchors (`redis_offloop.py:119/126`, `usage_service.py:17/619/650/689/768/792`, `review_service.py:8/21/664/722`), the commit trailer (Opus 5.5) and the four direct `set_cached` in get_reviews: verified.
- D03 on origin/main 84c861f6 adds only the import line and two hunks in `clean_review_citations` / `build_retailer_quotes_from_reviews` to review_service.py; nothing in get_reviews or the ST1 helper: the rebase is a pure import-block union, no semantic interaction.

## Blocking: none. Major: none.

## Minor (documentation / hygiene rulings for the orchestrator)

- MIN-1 (pin gap, non-equivalent survivors C02 / C16): no ST1 row pins that the ON post-extraction L1 write respects the FY19 / error persist guard (`if reviews and not reviews.get("error") and not unified_search_timed_out(...)`). Moving the ON write outside the guard (C02) or bypassing the guard under ON (C16) keeps all 515 unit nodes green; the only killer is `tests/test_s75_fanout_starve.py::test_FY19_unified_timeout_writes_no_specs_or_reviews_cache` WITH the flag exported, which CI never does (CI runs the flag unset, and the ST1 file is the only CI home of the ON path). A regression here would plant a 7-day empty-context reviews L1 row once ST1 is flipped. The GREEN bytes are correct (FY19 3 passed ON). Proposed additive PIN row (fix round): ST1 ON, the r19 harness, (a) `search_results` marked by `unified_search_timed_out` and (b) an extraction returning `{"error": ...}`: after awaiting every `reviews.l1_write` task (or `_BACKGROUND_TASKS`) and a pool flush, no L1 landing and no `save_reviews`; (c) the honest Serper-failure payload still lands one L1 write. Kills C02 and C16 without the flag export.
- MIN-2 (documentation truth, measured): CLAUDE.md limit (8) and PR body limit 8 ("two concurrent first reads after a past `reset_at` can both issue the reset UPDATE under ON (measured 2 vs 1 OFF)") are FALSE for the shipped R-ST1-1 design. Probe (two concurrent `get_usage_status`, a past `referral_bonus_reset_at`, a blocking fake client): UPDATEs = 1 with ENABLE_SYNC_DB_OFFLOAD OFF in BOTH ST1 states, and 2 with it ON in BOTH ST1 states. With sync offload OFF the tier-info task runs its select and UPDATE inline in one task step, so no interleave; the 2-vs-1 figure was measured for the spec's run_db_offloop design that R-ST1-1 dropped. The double UPDATE is a property of ENABLE_SYNC_DB_OFFLOAD (already true at base when it is ON), not of ST1. Rewrite the limit in place (CLAUDE.md row and PR body; RULINGS correction 8 is superseded by R-ST1-1).
- MIN-3 (scope of the ON except arm, measured): the fork wraps the compute body in the same `try` as the reads (`return _usage_status_body(*(await _usage_reads_offloop(uid)))`), so a compute failure is logged as `[USAGE-OFFLOOP] dispatch failed fn=get_usage_status type=TypeError -- inline fallback` and every read runs a second time before the same exception propagates (probe with a NULL `lifetime_comparisons_used`, a nullable `INT DEFAULT 0` column: OFF 1 users select, TypeError; ON 2 selects + the WARNING, same TypeError). The response is unchanged, but R-ST1-2 says the except "covers only a pool dispatch failure", and the canary reads the WARNING count as dispatch health. Suggested hygiene: `try: reads = await _usage_reads_offloop(uid) except Exception: log; else: return body(*reads)` in both functions (no row changes needed except possibly a new one), or reword the limit / canary item.
- MIN-4 (unpinned claim, survivor C06): the CLAUDE.md row and the PR body say the write runs in a `fire_and_forget` task "so the shutdown drain awaits it"; replacing it with `asyncio.ensure_future` keeps all nodes green. One assertion in r19 / r21 that the write task is in `app.utils.async_utils._BACKGROUND_TASKS` (or named `reviews.l1_write`) closes it.
- MIN-5 (unpinned claim, survivor C07): "durable=True shielded + quietly retrieved" (PR body): dropping `_retrieve_quietly` from `run_redis_offloop_pool`'s durable branch keeps all nodes green (r03b covers landing, not retrieval). Hygiene only (a failed durable write after a cancel would log "Future exception was never retrieved").
- MIN-6 (prove-nothing gate rows): the unit file's autouse `_st1_env` fixture deletes ENABLE_USAGE_PATH_OFFLOOP before every node, so GREEN's `st1green-unit-on` (and my `st1advc-unit-on`) is the OFF measurement again (only the r34 class sets the flag itself); the ON evidence lives inside the rows that set the flag. The GREEN report and PR body list "unit file ON (flag exported) 515 passed" as a separate gate: reword (e.g. "the flag export is neutralised by the file's fixture"). Also prove-nothing for the ON path in CI: every existing pin that would see an ON regression (FY19, the S77 / consult / YouTube placement pins) runs only with the flag exported.
- MIN-7 (observation, inferred from asyncio task scheduling, not measured): with ENABLE_SYNC_DB_OFFLOAD OFF (the production shape) the gather's first two tasks (the inline Supabase reads) complete inside their first step before the two GET tasks are first stepped, so the pool GETs never overlap the Supabase RTTs; listing the two `run_redis_offloop_pool` GETs first would overlap them at no correctness cost (r07 / r17 would need to accept the order). R-ST1-2 fixed the order literally; a latency ruling, not a defect. Plus the process note: the brief's "X19 block-move mutant" is the template leftover again (R-F1-C said it would be removed from wf_unit_green.js; it reached this adversary brief).

## Answers to GREEN's questions (correctness view)

- Q1 M40: keep the guard (base `set_cached` swallows its own errors, so a deepcopy failure must not fail the reviews leg) and pin it in the fix round with a non-deepcopyable payload row; it is defensive parity, not dead code.
- Q5 limit 14: true and harmless (both writes are full extractions of the same key); adding it to the row is optional.

## NOT MEASURED

- The comm set, CI-order set, ruff / py_compile, the CLAUDE.md readers and the hook tests (engineering lens).
- MIN-7's latency effect (inferred only).
- Production / Railway / Supabase: never touched; no .env read; flag state not needed for this lens.

## Final state

- Scratch worktree `<scratchpad>/ST1_adv_correctness` removed with `git worktree remove --force` (verified absent in `git worktree list`); my probe file lived only there.
- Unit worktree: HEAD `feb39dc0...`, `git status --short` empty, RED file sha `b5ba0bab...` (prefix `feb44766...`) unchanged.
