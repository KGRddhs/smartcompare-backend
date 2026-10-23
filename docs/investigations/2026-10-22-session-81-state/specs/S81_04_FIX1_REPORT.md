# S81-04 SPEND-BREAKER: fix round 1 report (FIX agent, Opus 5.5)

| Header | Value |
|---|---|
| Unit | S81-04 SPEND-BREAKER, `ENABLE_LLM_SPEND_BREAKER` (lane B) |
| Worktree / branch | `C:/Users/SynAckITPC/Documents/AI/sc-s81-s04`, `feature/s81-s04-spend-breaker` |
| Start | HEAD `b5f29e352bfbe786ab67728c921cf4ba9ef053c0` verified, `git status --short` empty, RED file `1e389248...56de1` verified (2026-10-23 22:42) |
| End | ONE commit `f1b29405c06e6b5e3e6a49992450e4353b61ef08` on the branch (through the pre-commit hook, no `--no-verify`, no push / rebase / stash); `git status --short` empty |
| Measurement base | `e1878dd8` (the GREEN base and its comm base record); the rebase onto `98d85433` is the NEXT step |
| Rulings applied | RULINGS_FIX1_S81_04 F1-1..F1-11 (F1-8 partially, see deviation D1) |
| Notes | `<scratchpad>/S81-04_fix1/` (notes.md, before/ byte copies + SHA256SUMS.json, red/, logs, mut_*.json, mut_table.md, comm/, comm_table.md, leaf_functional.diff, fix1_commit.diff, PR_BODY.md) |

## 1. RED step (rows appended BEFORE any app edit; the pre-fix bytes were HEAD)

- RED file after the step: `5f09b519840c565f6943f1ff93ff43a7e00614bdfe50868ea2fba390cb7a2eda`; final RED file (after the GREEN-phase row additions below): `d9bb55b5237f7dba9ecc06fdd273ef596f94f29e48670452720a32f8564bb7cd` (104,455 B, LF, 0 bytes > 127).
- `[pyt] tag=s04f1-red start=2026-10-23 23:02:02 end=2026-10-23 23:02:20 elapsed=18s bound=600s status=FAIL rc=1` : 28 failed / 237 passed; 28 `E AssertionError`, no other class (`[hermeticity] sentinel checked 265 test(s)`, `[netguard] blocked 24 attempt(s) from 2 node(s)`: r42 + p08 sentinel only).
- Final RED file on a SCRATCH COPY of `b5f29e35` (`git worktree add --detach <notes>/pre_b5f2 b5f29e35`, the final unit file copied in, removed with `git worktree remove --force`, `git worktree list` clean): `[pyt] tag=s04f1-prefix-red start=2026-10-23 23:42:04 end=2026-10-23 23:42:24 elapsed=20s bound=600s status=FAIL rc=1` : **29 failed (29 AssertionError, no other class) / 238 passed** (`[hermeticity] sentinel checked 267 test(s)`, `[netguard] blocked 24 attempt(s) from 2 node(s)`).
  - 22 new RED nodes: r47, r47b, r48, r49, r51, r52, r52b, r53, r54, r54b, r55 x2, r56 x2, r57 x8.
  - 7 re-pinned existing nodes red at pre-fix (the F1 API): r06 (settle ticket), r07 x4 (image_big, image_small, image_mini, image_nomodel: model id), r28[image] (mini 37,000), r40b (settle ticket).
  - 2 new PIN rows green at pre-fix: r50 (two overlapping records; kills M50 + A02), r58 (sync stalled read; kills M30s).
  - Every other existing row green and byte-identical except the named re-pins (r06, r07, r18 loses its `-1` case to r48, r28, r33 allows `llm_spend_late_records`, r40b).
- Rows added after the first RED measurement (all measured in the scratch-copy run above): r50's between-landings check (M50 survived without it: the in-flight entry is popped when its count reaches 0), r58 (M30s survived), r54's sync `record` line and r54b (N14b / N13b survived).

## 2. GREEN (what changed)

| Path | +/- | sha256 after |
|---|---|---|
| `app/services/llm_spend_breaker.py` | +563 / -153 (incl. the black reformat; functional hunks: `<notes>/leaf_functional.diff` = black(pre-fix) vs HEAD) | `802cb806cbbbc9b39ab24092af3e867fbbcce8562c5f2959cb2dee05f26ee230` |
| `app/services/structured_comparison_service.py` | +9 / -7 (the two entry checks read `chokepoint_lane()`, comments) | `43871533f653463bc56997f9d162d0cca09aeaa1b5a0136791bb42a3d4d8a6dd` |
| `app/main.py` | +3 / -2 (the snapshot docstring names the late counter; no code change) | `df9ed83ad464fe478118dd51544b4d0a25a9cc11dca17ecdf1de9f1a219226ab` |
| `.github/black-clean-paths.txt` | +1 (`app/services/llm_spend_breaker.py`) | `8a353e36f492280ecbbbabd3a65569f8e9630d037c42e0fe2179ee1456e3479b` |
| `CLAUDE.md` | +2 / -2 (the S81-04 row rewritten in place; the Feature Flags pointer names the row) | `d0c65579e45d5869dd0749a554f13c609b598a3d9fa03dbe5c39d13f27b5c701` |
| `tests/test_s81_s04_spend_breaker.py` | +492 / -18 | `d9bb55b5237f7dba9ecc06fdd273ef596f94f29e48670452720a32f8564bb7cd` |

Per ruling:
- F1-1: `ReserveTicket(lane, bound_usd, day, expireat)`; `reserve` returns it (None on a fail-open); `settle(ticket, actual)` applies `actual - bound` to `spend_key(lane, ticket.day)` with `ticket.expireat`; a non-ticket raises ValueError; `_read_spent` clamps a negative stored total to 0 with ONE rate-limited WARNING per key (`[SPEND] stored spend negative (key=<key>) -- read as 0`); NaN / inf / garbage still fail open. Leaf docstring point 4 and the CLAUDE.md row name the ticket as the binding contract for S81-16 / S81-21 / S81-22.
- F1-2: per-lane write sequence `_WRITE_SEQ` bumped by every EVAL observation; `_observe_read(lane, day, total, seq0)` keeps `max(base, total)` when a write landed after the GET was submitted; in-flight deltas settled once (unchanged, now pinned).
- F1-3: `_run_bounded_sync(..., on_cancelled=)` registers a done-callback; the sync `record` passes `_record_cancelled` (settles the flight, counts the fail-open).
- F1-4: (a) `_RecordWatch` on each flight; an awaiter timeout marks `gave_up`; the job reports a late landing as `llm_spend_late_records` + one INFO `[SPEND] late record landed -- recorded after its bound expired` (the line before the counter), a late failure as a fail-open; `/health` gains `llm_spend_late_records` (ON only, via the snapshot); (b) `_shared_read` = one in-flight GET per (lane, day), every waiter bounded on its own follower future (`_follow`; a waiter's timeout never cancels the shared GET, a closed loop is ignored); (c) `_FAILOPEN_WINDOW` per lane = the memo window after a read failure / timeout; admit, entry and both records fail open without a hop inside it, counted once per window (the same rate-limited WARNING text).
- F1-5: `_valid_bound` (positive) for admit bounds; `_valid_usd` unchanged for actuals (settle with 0 releases the whole bound).
- F1-6: both entry checks call `_llm_spend_breaker.entry_refuses_async(_llm_spend_breaker.chokepoint_lane())`.
- F1-7: `OPENAI_MINI_IMAGE_TOKENS_UPPER = 37_000` (source comment, UNVERIFIED, S81-07); `prompt_token_upper_bound(..., model=None)`; an OpenAI id priced at the 4o rate row (= the most expensive OpenAI row, no model literal in the leaf) keeps 1,445, every other OpenAI id (mini rows, unpriced, None) 37,000, Anthropic 4,784, an unknown provider the largest; the chokepoint threads the model. R07 / R28 re-pinned per model id.
- F1-8: the leaf black-formatted (black 26.5.1, AST-equal modulo docstring whitespace, measured) and added to the ratchet. See D1 for `llm_pricing.py`.
- F1-9: `_cents` comment "0.07 * 100 is not exactly 7 (measured)".
- F1-10 / F1-11: leaf opening line ("every dispatch through guarded_llm_create", the two scripts named); "bounded by" (async wait_for, sync future.result(timeout)); CLAUDE.md row limits (1) stall cost + herd thresholds + window, (3) EVAL / GET visibility, (5) degraded BILLED 200, (7) per-model bound, (11) interpreter exit waits, (16) the two scripts, the rollback sentence (RO18), the canary item; the PR body's net-0 non-ASCII sentence, the row-named pointer, the r38 extract wording.

## 3. Runs (every pytest through pyt.py, one at a time)

| Run | Result | [pyt] |
|---|---|---|
| unit file, flag unset (final bytes) | 267 passed | `[pyt] tag=s04f1-unit-off4 start=2026-10-23 23:40:40 end=2026-10-23 23:40:49 elapsed=9s bound=600s status=OK rc=0` |
| unit file, `ENABLE_LLM_SPEND_BREAKER=true` (final bytes) | 267 passed | `[pyt] tag=s04f1-unit-on2 start=2026-10-24 00:11:22 end=2026-10-24 00:11:33 elapsed=11s bound=600s status=OK rc=0` |
| (earlier, 265 nodes) unit OFF / ON | 265 / 265 passed; no never-awaited / never-retrieved / closed-loop lines | `[pyt] tag=s04f1-unit-off2 start=2026-10-23 23:10:22 end=2026-10-23 23:10:30 elapsed=8s bound=600s status=OK rc=0`; `[pyt] tag=s04f1-unit-on start=2026-10-23 23:10:32 end=2026-10-23 23:10:41 elapsed=8s bound=600s status=OK rc=0` |
| CI-order set (24 files), flag unset, chunks of 8 | 219 + 478 + 1074 = 1771 passed (1745 GREEN + 26 new unit nodes) | `[pyt] tag=s04f1-ci-off-1 start=2026-10-23 23:43:39 end=2026-10-23 23:43:55 elapsed=16s bound=1200s status=OK rc=0`; `[pyt] tag=s04f1-ci-off-2 start=2026-10-23 23:43:57 end=2026-10-23 23:44:23 elapsed=25s bound=1200s status=OK rc=0` (`[netguard] blocked 141 attempt(s) from 7 node(s)`: the pre-existing test_openai_breaker / test_retro_w1_3 baseline nodes); `[pyt] tag=s04f1-ci-off-3 start=2026-10-23 23:44:26 end=2026-10-23 23:45:16 elapsed=50s bound=1200s status=OK rc=0` (`[netguard] blocked 24 attempt(s) from 2 node(s)`) |
| the same set, flag exported ON (limit 15) | 34 failed = 6 `test_retro_w0_4_efg` + 7 `test_s77_redis_offloop` + 21 `test_s81_s03_llm_ledger_v2`; the failed-node list is IDENTICAL to the GREEN's `ci_order_on.log` (diff empty); FY25 nine digests, W4-13 flag-OFF ledger, T23 (test_s71_u13), U3c, both CLAUDE.md readers and the unit file green ON | `[pyt] tag=s04f1-ci-on-1 start=2026-10-23 23:45:56 end=2026-10-23 23:46:10 elapsed=13s bound=1200s status=OK rc=0`; `[pyt] tag=s04f1-ci-on-2 start=2026-10-23 23:46:12 end=2026-10-23 23:46:36 elapsed=24s bound=1200s status=FAIL rc=1`; `[pyt] tag=s04f1-ci-on-3 start=2026-10-23 23:46:38 end=2026-10-23 23:47:32 elapsed=54s bound=1200s status=FAIL rc=1` |
| FY25 OFF / ON | the whole `tests/test_s75_fanout_identity.py` (incl. the nine-digest node) green in ci-off-3 and ci-on-3 | (as above) |
| W4-13 / T23 / CLAUDE.md readers | `test_w4_13_flag_off_ledger`, `test_s71_u13_compare_auth_required`, `test_ci_gates` (incl. `test_black_allowlist_entries_are_actually_clean` with the new entry) + `test_behavior_dimension_translation` + r38 green OFF and ON | (as above) |
| hook `-k black` nodes (4 hook files, own runner call) | 4 passed, 323 deselected | `[pyt] tag=s04f1-hook-black start=2026-10-24 00:18:31 end=2026-10-24 00:22:45 elapsed=254s bound=1200s status=OK rc=0` |

Comm set at HEAD (`comm_set.txt` = the GREEN's 335-file `comm_green.txt`, re-checked: the only new reader of an edited path is `tests/test_precommit_hook.py` (reads `.github/black-clean-paths.txt`), a hook file excluded by rule and covered by the hook run above), 14 chunks, the GREEN runner with s04f1 tags, the 4 NETWORK_FLAKY_EXCLUDE nodes deselected:

| Chunk | Files | Summary | [pyt] |
|---|---|---|---|
| 01 | 24 | 2 failed, 845 passed | `[pyt] tag=s04f1-comm-head-01 start=2026-10-23 23:49:23 end=2026-10-23 23:50:02 elapsed=39s bound=1200s status=FAIL rc=1` |
| 02 | 24 | 1226 passed, 5 deselected | `[pyt] tag=s04f1-comm-head-02 start=2026-10-23 23:50:03 end=2026-10-23 23:50:48 elapsed=46s bound=1200s status=OK rc=0` |
| 03 | 24 | 997 passed, 1 skipped, 12 deselected | `[pyt] tag=s04f1-comm-head-03 start=2026-10-23 23:50:50 end=2026-10-23 23:51:58 elapsed=68s bound=1200s status=OK rc=0` |
| 04 | 24 | 919 passed, 1 skipped | `[pyt] tag=s04f1-comm-head-04 start=2026-10-23 23:51:59 end=2026-10-23 23:52:38 elapsed=39s bound=1200s status=OK rc=0` |
| 05 | 24 | 1563 passed, 5 deselected | `[pyt] tag=s04f1-comm-head-05 start=2026-10-23 23:53:03 end=2026-10-23 23:54:55 elapsed=112s bound=1200s status=OK rc=0` |
| 06 | 24 | 366 passed | `[pyt] tag=s04f1-comm-head-06 start=2026-10-23 23:54:57 end=2026-10-23 23:55:39 elapsed=42s bound=1200s status=OK rc=0` |
| 07 | 24 | 574 passed | `[pyt] tag=s04f1-comm-head-07 start=2026-10-23 23:55:40 end=2026-10-23 23:56:05 elapsed=25s bound=1200s status=OK rc=0` |
| 08 | 24 | 2 failed, 501 passed, 7 deselected | `[pyt] tag=s04f1-comm-head-08 start=2026-10-23 23:56:06 end=2026-10-23 23:56:53 elapsed=46s bound=1200s status=FAIL rc=1` |
| 09 | 24 | 642 passed, 3 skipped, 2 deselected, 1 xfailed, 2 errors | `[pyt] tag=s04f1-comm-head-09 start=2026-10-23 23:57:22 end=2026-10-23 23:59:05 elapsed=103s bound=1200s status=FAIL rc=1` |
| 10 | 24 | 1127 passed | `[pyt] tag=s04f1-comm-head-10 start=2026-10-23 23:59:06 end=2026-10-24 00:01:39 elapsed=153s bound=1200s status=OK rc=0` |
| 11 | 24 | 2967 passed (GREEN head 2941 + 26 new unit nodes) | `[pyt] tag=s04f1-comm-head-11 start=2026-10-24 00:02:05 end=2026-10-24 00:04:26 elapsed=141s bound=1200s status=OK rc=0` |
| 12 | 24 | 622 passed, 2 skipped, 11 deselected | `[pyt] tag=s04f1-comm-head-12 start=2026-10-24 00:04:28 end=2026-10-24 00:05:58 elapsed=91s bound=1200s status=OK rc=0` |
| 13 | 24 | 463 passed, 8 deselected | `[pyt] tag=s04f1-comm-head-13 start=2026-10-24 00:06:26 end=2026-10-24 00:07:23 elapsed=57s bound=1200s status=OK rc=0` |
| 14 | 23 | 1204 passed, 9 skipped, 35 xfailed | `[pyt] tag=s04f1-comm-head-14 start=2026-10-24 00:07:24 end=2026-10-24 00:08:45 elapsed=81s bound=1200s status=OK rc=0` |

HEAD failed nodes (6): the 4 `tests/.pre_impl_failures.txt` rows (test_auth_interceptor x2, test_page_scraping x2) + the 2 cold-tiktoken ERRORs of test_prompt_truth = the GREEN head set. **`comm -13 <GREEN base_failed> <head_failed>` = EMPTY** (base-only: the ST1 timing row, as in the GREEN).

Non-pytest gates: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on the 4 changed python files: All checks passed; `--select F401,F841` on the leaf + unit file: All checks passed; `py_compile` of the 4: ok; `black --check --config pyproject.toml` on the leaf: unchanged; the pre-commit hook on the commit: passed (its ruff + black-allowlist steps printed clean); added-line sweep (@gmail, +973, 8-digit runs, sk- / JWT / credentialed-URL / PEM shapes): 0 hits; non-ASCII in added lines: 22 characters = the 66 pre-existing bytes of the re-added Feature Flags line (net 0); CRLF kept on every CRLF file (0 bare LF), the leaf and the unit file LF as at b5f29e35.

## 4. Mutation table (fix bytes; byte copy -> exact edit -> the FULL unit file with `-x` -> restore -> sha256 compare; `.qa-mutation.lock` created and removed)

45 mutants: 44 KILLED (42 by an AssertionError incl. pytest's `DID NOT RAISE`; M39 by a TypeError, M30 by the un-bounded read's LLMUnavailableError), 1 SURVIVED (M51, the test-reset generation guard, ruled EQUIVALENT by F1-2). The 20 re-run mutants were measured on the final unit file; N01-N19 on the file before r54's sync-record line and r54b (both then added to kill N14b / N13b, re-measured in `mut_batch2b.json`). Full rows with every [pyt] line: `<notes>/mut_table.md` and `mut_final_rerun.json`, `mut_batch2.json`, `mut_batch2b.json`.

| # | Mutant | Status | First killer |
|---|---|---|---|
| M33 | reserve without the check | KILLED | r40 |
| M40 | settle sign reversed | KILLED | r40b |
| M29 | memo never stale | KILLED | r39 |
| M35 | local delta not added | KILLED (DID NOT RAISE) | r39b |
| M50 | in-flight delta never settled (GREEN survivor) | KILLED | r50 |
| A02 | EVAL observation lowers the base (adversary survivor) | KILLED | r50 |
| M51 | generation guard removed | SURVIVED (EQUIVALENT, F1-2) | - |
| M39 | admit bound not sanitised | KILLED (TypeError) | r19b |
| M41 | bool accepted as an amount | KILLED | r15 |
| M20 | reads take the live key for every lane | KILLED | r10 |
| M31 | reads on another executor | KILLED | r22 |
| M30 | async read bound removed | KILLED (LLMUnavailableError) | r22b |
| M30s | sync read bound removed | KILLED | r58 |
| M36 | no-client short-circuit removed | KILLED | r22c |
| M07 | record_soon inline on the loop | KILLED | r22 |
| M08 | image part counted as json bytes | KILLED | r07 |
| M16 | snapshot keys before the breaker ran | KILLED | p05 |
| M34 | amounts on /health | KILLED | r33 |
| M43a / M43b | fail-open counter not counted (`_fail_open` / `_read_failed`) | KILLED | r34b / r54 |
| N01 / N01b | F1-1 settle on today's key / today's EXPIREAT | KILLED | r47 |
| N02a / N02b / N02c | F1-1 clamp removed (negative returned / negative fails open / WARNING not per key) | KILLED | r48 |
| N03 | F1-1 reserve returns True | KILLED | r47 |
| N04 / N05 | F1-2 GET after a landed write replaces the base / the sequence never moves | KILLED | r49 |
| N06 | F1-3 no cancelled-record settle | KILLED | r51 |
| N07 / N08 / N09 | F1-4a late record as fail-open / counter frozen / /health key absent | KILLED | r52 |
| N10 | F1-4b no single flight | KILLED | r53 |
| N11 / N12 / N13 / N13b / N14 / N14b | F1-4c no window / global window / in-window counted / every waiter counted / record_soon or sync record ignore the window | KILLED | r54 (N13b: r54b) |
| N15 | F1-5 zero bound admitted (A25 inverted) | KILLED | r55 |
| N16 / N16b | F1-6 REST / stream entry on LANE_LIVE | KILLED | r56 |
| N17 / N18 / N19 | F1-7 mini uses the 4o bound / unknown provider Anthropic cap / model not threaded | KILLED | r07 / r57 / r28 |

## 5. Deviations

- D1 (F1-8, MEASURED premise refuted): the ruling says both files are "black-clean per the GREEN's check"; black 26.5.1 `--check --config pyproject.toml` measured BOTH as "would reformat" (diffs `<notes>/black_leaf.diff`, 204 +/- lines, and `black_llm_pricing.diff`, 346; the engineering adversary m9 had said so for the leaf). The leaf (this unit's new file) was black-formatted (AST-equal modulo docstring whitespace, measured) and joined the ratchet. `app/services/llm_pricing.py` was NOT reformatted and does NOT join: it is S81-03's merged leaf, outside this unit's change list, it has line-based source pins in `tests/test_s81_s03_llm_ledger_v2.py` (the stray-model scan per line), and S81-06 builds on it (a whole-file reformat is a rebase collision). Question Q1.
- D2: the leaf diff of this commit mixes the black reformat with the functional hunks; `<notes>/leaf_functional.diff` is black(b5f29e35 leaf) vs HEAD for review.
- D3 (F1-7 classification): no model-id literal may live in the leaf (R01), so the 1,445 bound applies to an OpenAI id whose price row equals the most expensive row of the OpenAI table (the three 4o ids today); every other OpenAI id, an unpriced or missing id gets 37,000; an unknown provider now takes the largest bound (37,000; it was the Anthropic 4,784). A future OpenAI row costlier than 4o would take 1,445 and drop 4o to 37,000 (S81-07 owns the per-model table).
- D4 (F1-4c scope): the window opens on a READ failure or timeout only (a record timeout is a late record, a record error a plain fail-open); records inside an open window are not sent (an undercount for that window, stated in row limit 1); `reserve` / `settle` are not windowed (not named by the ruling; off the hot path).
- D5 (F1-5): "`_valid_usd` rejects 0 for an admit bound" is implemented as a separate `_valid_bound` (positive) used by `_sanitized_bound`; `_valid_usd` keeps 0 so a 0 ACTUAL stays valid (pinned by r47b: settle(ticket, 0.0) releases the whole bound). `record(lane, 0)` with no admitted bound still records nothing (R15 unchanged).
- D6 (RED-file edits beyond appended rows): r06, r40b (settle ticket API, F1-1), r18 (its `-1` case moved to r48, F1-1 clamp), r07 / r28 (per model id, F1-7), r33 (the new /health key, F1-4) are re-pinned; every other existing row is byte-identical (`<notes>/red/red_file_amendments.diff` is the RED-step diff; later additions are r50's check, r54's sync record line, r54b, r58).
- D7: the rulings file has no section titled "Procedure for the fix agent"; the task text's order was followed (RED, GREEN, docs, gates, one commit).
- D8: `app/main.py` gained a docstring-only edit (the snapshot names the late counter); no code change there (the key comes through the leaf snapshot).
- D9: the PR body keeps the session attribution line, whose emoji is the only non-ASCII content of that scratch file (4 bytes).

## 6. Questions for the gate

- Q1 (D1): should `app/services/llm_pricing.py` be black-formatted and join the ratchet (a separate pure-format unit after S81-06 lands, re-running S81-03's pins), or stay off the list?
- Q2 (D3): accept the price-row classification of the 4o image rule, or move a per-model image table into `openai_pricing` (with S81-07)?
- Q3 (D4): records inside a fail-open window are dropped as ruled; should a windowed record keep its delta in the local memo instead (it would raise the local view without Redis)?
- Q4: the comm set was not re-run at base: the GREEN base record (`S81-04_green/comm/base_failed.txt`, 7 nodes) was used as ruled.

## 7. NOT MEASURED

- Upstash's real EVAL / GET latency and the Lua acceptance (canary items).
- The herd thresholds AFTER the fix (the row cites the engineering adversary's pre-fix measurement and states what the fix changes; single flight is pinned by r53, the window by r54 / r54b).
- The gpt-4o-mini image token rule (no web read; UNVERIFIED, S81-07).
- The 323 hook nodes outside `-k black` (CI covers them; the unit edits no `.githooks`).

## 8. Final state

- `git status --short`: empty. HEAD `f1b29405c06e6b5e3e6a49992450e4353b61ef08` on `feature/s81-s04-spend-breaker` (3 commits on `e1878dd8`). Not pushed, no PR, no rebase.
- No `.qa-mutation.lock`; the scratch worktree removed (`git worktree list` has no `pre_b5f2`); no `.env` in the notes folder; no pytest process of this agent alive.
- PR body: `<scratchpad>/S81-04_fix1/PR_BODY.md`.
