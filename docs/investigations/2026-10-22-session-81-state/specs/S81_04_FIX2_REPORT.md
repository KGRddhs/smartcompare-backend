# S81-04 SPEND-BREAKER: fix round 2 report (FIX agent, Opus 5.5)

| Header | Value |
|---|---|
| Unit | S81-04 SPEND-BREAKER, `ENABLE_LLM_SPEND_BREAKER` (lane B) |
| Worktree / branch | `C:/Users/SynAckITPC/Documents/AI/sc-s81-s04`, `feature/s81-s04-spend-breaker` |
| Start | HEAD `f1b29405c06e6b5e3e6a49992450e4353b61ef08` verified, `git status --short` empty, RED file `d9bb55b5237f7dba9ecc06fdd273ef596f94f29e48670452720a32f8564bb7cd` verified, leaf `802cb806...ee230` (2026-10-24 01:46 AST) |
| End | ONE commit `04a1ba9fa85cb1b9ea0ee20de97def3ebb5fe23e` on the branch (through the pre-commit hook, no `--no-verify`, no push / rebase / stash); `git status --short` empty |
| Measurement base | `e1878dd8` (the GREEN base and its comm base record, ruling F2-7); the rebase onto the moving main (`98d85433` with S81-05, or newer) is the NEXT step |
| Rulings applied | RULINGS_FIX2_S81_04 F2-1..F2-7 (amending RULINGS_FIX1_S81_04 / GATE_S81_04 / RULINGS_S81_04) |
| Notes | `<scratchpad>/S81-04_fix2/` (notes.md, before/ byte copies, red/ (RED-step file + amendments diff), red_unit.log, prefix_red.log, unit_*.log, mutate_fix2.py, mut_batch1.json, mut_batch2.json, mut_batch3_k.json, mut_table.md, mut_logs/, ci_off_*.log, ci_on_*.log, ci_on_failed.txt, comm/ (head_NN.log, head_summary.json, head_failed.txt), comm_pyt_lines.txt, hook_black.log, fix2_commit.diff, added_lines.txt, commit_msg.txt, commit.log, row_before.txt / row_after.txt, PR_BODY.md) |

## 1. RED step (rows appended BEFORE any app edit; the pre-fix bytes were HEAD `f1b29405`)

- RED file after the step: `7a384057a5ea21e275bfbd4a50e8b264a2ca0bdf4d47041b1f7644ae01292609`; FINAL RED file (r62c / r62d added after the first RED measurement): `01d61e7fbf4e0777d5923ccbe4a831601ef8735fdd3e7215e586f84b3eb9c00c` (LF, 2,862 lines, 0 bytes > 127).
- `[pyt] tag=s04f2-red start=2026-10-24 02:07:21 end=2026-10-24 02:07:34 elapsed=13s bound=600s status=FAIL rc=1`: 18 failed / 259 passed; every failure an AssertionError (16 `E AssertionError`, the rest `E assert`; no other class); `[hermeticity] sentinel checked 277 test(s)`, `[netguard] blocked 24 attempt(s) from 2 node(s)` (r42 + p08, the `neutralized.supabase.invalid:443` sentinel only).
- Final RED file on a SCRATCH COPY of `f1b29405` (`git worktree add --detach <notes>/pre_f1b2 f1b29405...`; its leaf, LF-normalised, = `802cb806...`; the final unit file copied in; removed with `git worktree remove --force`; `git worktree list` clean; no node_modules there): `[pyt] tag=s04f2-prefix-red start=2026-10-24 02:47:21 end=2026-10-24 02:48:36 elapsed=75s bound=600s status=FAIL rc=1` : **20 failed (all AssertionError, each section's first E line read) / 259 passed**; `[hermeticity] sentinel checked 279 test(s)`, `[netguard] blocked 24 attempt(s) from 2 node(s)`.
  - 9 new RED nodes: r59, r59b, r60[after_the_new_day_get], r60[inside_the_new_day_get], r60b, r62, r62b, r62c, r62d.
  - 11 re-pinned nodes red at pre-fix (F2-3, the 37,000 literal): r07[image_mini], r07[image_nomodel], r28[image], r57 x8 (all 8 assert the constant first).
  - 3 new PIN rows green at pre-fix: r61 (kills A03), r63 (kills X1), r64 (kills X6).
- Re-pins of existing rows (deviation D1 below): r54 (two in-window record lines removed + docstring), r57 / r07 / r28 (37,000 -> 49,000 at 8 tiles). `git diff -U0` of the unit file shows exactly those hunks plus the appended block after r57 (every other row byte-identical).

## 2. GREEN (what changed)

| Path | numstat (+/-) | sha256 after (working copy) |
|---|---|---|
| `app/services/llm_spend_breaker.py` | +90 / -52 | `050a8743e269b03bf0a20adb7eb900e76f28064dae5c153427c15a7549c542f3` (LF) |
| `tests/test_s81_s04_spend_breaker.py` | +433 / -17 | `01d61e7fbf4e0777d5923ccbe4a831601ef8735fdd3e7215e586f84b3eb9c00c` (LF) |
| `CLAUDE.md` | +1 / -1 (the S81-04 row, line 492, rewritten in place) | `ef96b6368d06203f62d426e9018c3e4dcb9b49b5b8665a14e11c286cfcd020ff` (CRLF kept, 955 CRLF, bytes > 127 unchanged at 3,952; the row has 0 non-ASCII) |

No other file (`app/main.py`, `structured_comparison_service.py`, `.github/black-clean-paths.txt` untouched).

Per ruling:
- F2-1: `_observe_write_locked` returns (setting only `_STATE['ran']`) when the lane's memo entry is of a LATER day (`entry["day"] > day`, ISO strings), before the write sequence or the memo move; an EVAL total below 0 is clamped to 0 (`total = max(total, 0.0)`). `_observe_read` returns `total + _inflight_sum(lane, day)` to its own caller without touching a later-day entry. `/health` `exhausted` code unchanged (already current-day only), now pinned (r61). Leaf docstring and the row state the exact invariant (same-day max, older-day never replaces a later-day entry, below-0 observed as 0); the overclaim is gone.
- F2-2: the window check removed from `record` and `record_soon`; `_record_job`'s failure arm no longer settles the delta (it stays in `_INFLIGHT` for its day); new `_record_failed(lane, reason)` + `_RECORD_FAIL_COUNTED` (per-lane counting window = memo window): counts a record failure at most once per lane per window, not again while the lane's read window is open, never opens the read window; used by `_record_finished` (late failure), `_record_gave_up` (already-failed arm), `_record_cancelled` (F1-3), `record` and `_record_task` except arms; `_reset_spend_breaker_state` clears it.
- F2-3: `OPENAI_MINI_IMAGE_TOKENS_UPPER = 49_000` with the 8-tile derivation comment (UNVERIFIED, S81-07; "over-bounding only refuses earlier ... only at THIS constant").
- F2-4: rows r63 / r64 (PIN).
- F2-5 / F2-6: row limits 1, 10, 11 (and the PR body limits 1, 7, 10).
- F2-7: nothing to change (llm_pricing.py off the ratchet; the price-row image rule stands; the GREEN base comm record reused).

## 3. Runs (every pytest through pyt.py, one at a time)

| Run | Result | [pyt] |
|---|---|---|
| unit file, flag unset (after the leaf hunks, 277 nodes) | 277 passed | `[pyt] tag=s04f2-unit-off start=2026-10-24 02:11:09 end=2026-10-24 02:11:22 elapsed=13s bound=600s status=OK rc=0` |
| unit file, flag ON (277 nodes) | 277 passed | `[pyt] tag=s04f2-unit-on start=2026-10-24 02:11:34 end=2026-10-24 02:11:47 elapsed=13s bound=600s status=OK rc=0` |
| the timing-sensitive rows x3 (`-k` r51-r54, r59-r64, 16 nodes) | 16 passed each | `[pyt] tag=s04f2-new-rows-1 start=2026-10-24 02:12:03 end=2026-10-24 02:12:12 elapsed=9s bound=600s status=OK rc=0`; `-2 start=02:12:15 end=02:12:24 elapsed=10s status=OK rc=0`; `-3 start=02:12:28 end=02:12:38 elapsed=11s status=OK rc=0` |
| unit file, flag unset (279 nodes, before the CLAUDE.md edit) | 279 passed | `[pyt] tag=s04f2-unit-off2 start=2026-10-24 02:14:37 end=2026-10-24 02:14:50 elapsed=13s bound=600s status=OK rc=0` |
| unit file, flag unset, FINAL bytes | 279 passed (`[hermeticity] sentinel checked 279 test(s)`, `[netguard] blocked 24 attempt(s) from 2 node(s)`) | `[pyt] tag=s04f2-unit-off3 start=2026-10-24 02:43:41 end=2026-10-24 02:44:04 elapsed=23s bound=600s status=OK rc=0` |
| unit file, flag ON, FINAL bytes | 279 passed (same guard lines; 0 never-awaited / destroyed / never-retrieved lines in either log) | `[pyt] tag=s04f2-unit-on2 start=2026-10-24 02:44:07 end=2026-10-24 02:44:33 elapsed=26s bound=600s status=OK rc=0` |
| CI-order set (the 24 files, CI order), flag unset, chunks of 8 | 219 + 478 + 1086 = 1783 passed (1771 + the 12 new unit nodes); guards: `[netguard] blocked 0 attempt(s) from 0 node(s)` / `141 attempt(s) from 7 node(s)` (the baseline test_openai_breaker / test_retro_w1_3 nodes) / `24 attempt(s) from 2 node(s)` | `[pyt] tag=s04f2-ci-off-1 start=2026-10-24 02:51:54 end=2026-10-24 02:52:29 elapsed=35s bound=1200s status=OK rc=0`; `[pyt] tag=s04f2-ci-off-2 start=2026-10-24 02:52:35 end=2026-10-24 02:53:03 elapsed=29s bound=1200s status=OK rc=0`; `[pyt] tag=s04f2-ci-off-3 start=2026-10-24 02:53:14 end=2026-10-24 02:54:44 elapsed=91s bound=1200s status=OK rc=0` |
| the same set, flag exported ON (limit 15) | 34 failed = 6 `test_retro_w0_4_efg` + 7 `test_s77_redis_offloop` + 21 `test_s81_s03_llm_ledger_v2`; the failed-node list is IDENTICAL node for node (diff empty) to fix 1's `ci_on_failed.txt` (= the GREEN's); FY25 (`test_s75_fanout_identity`, incl. the nine digests), W4-13 (`test_w4_13_flag_off_ledger`), T23 (`test_s71_u13_compare_auth_required`), U3c, K1, both CLAUDE.md readers (`test_ci_gates`, `test_behavior_dimension_translation`) and r38 green ON and OFF | `[pyt] tag=s04f2-ci-on-1 start=2026-10-24 02:55:29 end=2026-10-24 02:55:39 elapsed=10s bound=1200s status=OK rc=0`; `[pyt] tag=s04f2-ci-on-2 start=2026-10-24 02:55:45 end=2026-10-24 02:56:03 elapsed=19s bound=1200s status=FAIL rc=1`; `[pyt] tag=s04f2-ci-on-3 start=2026-10-24 02:56:08 end=2026-10-24 02:57:00 elapsed=51s bound=1200s status=FAIL rc=1` |
| hook test files ALONE, `-k black` | 4 passed, 323 deselected | `[pyt] tag=s04f2-hook-black start=2026-10-24 03:20:00 end=2026-10-24 03:23:25 elapsed=205s bound=1200s status=OK rc=0` |

Comm set at HEAD (`comm_set.txt` = the GREEN's 335-file set, unchanged: the only new readers of an edited path are prose mentions of "CLAUDE.md" in 8 files, none reads the file; the 4 NETWORK_FLAKY nodes deselected; 14 chunks of <= 24, bound 1200, flag unset):
- 01: 24 files, 2 failed, 845 passed: `[pyt] tag=s04f2-comm-head-01 start=2026-10-24 02:58:31 end=2026-10-24 02:59:36 elapsed=66s bound=1200s status=FAIL rc=1`
- 02: 24 files, 1226 passed, 5 deselected: `[pyt] tag=s04f2-comm-head-02 start=2026-10-24 02:59:37 end=2026-10-24 03:00:30 elapsed=53s bound=1200s status=OK rc=0`
- 03: 24 files, 997 passed, 1 skipped, 12 deselected: `[pyt] tag=s04f2-comm-head-03 start=2026-10-24 03:00:33 end=2026-10-24 03:01:47 elapsed=74s bound=1200s status=OK rc=0`
- 04: 24 files, 919 passed, 1 skipped: `[pyt] tag=s04f2-comm-head-04 start=2026-10-24 03:01:49 end=2026-10-24 03:02:39 elapsed=50s bound=1200s status=OK rc=0`
- 05: 24 files, 1563 passed, 5 deselected: `[pyt] tag=s04f2-comm-head-05 start=2026-10-24 03:02:41 end=2026-10-24 03:04:57 elapsed=136s bound=1200s status=OK rc=0`
- 06: 24 files, 366 passed: `[pyt] tag=s04f2-comm-head-06 start=2026-10-24 03:05:00 end=2026-10-24 03:05:43 elapsed=43s bound=1200s status=OK rc=0`
- 07: 24 files, 574 passed: `[pyt] tag=s04f2-comm-head-07 start=2026-10-24 03:05:44 end=2026-10-24 03:06:13 elapsed=29s bound=1200s status=OK rc=0`
- 08: 24 files, 2 failed, 501 passed, 7 deselected: `[pyt] tag=s04f2-comm-head-08 start=2026-10-24 03:06:15 end=2026-10-24 03:07:01 elapsed=46s bound=1200s status=FAIL rc=1`
- 09: 24 files, 642 passed, 3 skipped, 2 deselected, 1 xfailed, 2 errors (cold tiktoken): `[pyt] tag=s04f2-comm-head-09 start=2026-10-24 03:07:04 end=2026-10-24 03:08:51 elapsed=107s bound=1200s status=FAIL rc=1`
- 10: 24 files, 1127 passed: `[pyt] tag=s04f2-comm-head-10 start=2026-10-24 03:08:52 end=2026-10-24 03:11:38 elapsed=166s bound=1200s status=OK rc=0`
- 11: 24 files, 2979 passed (fix-1 2967 + the 12 new unit nodes): `[pyt] tag=s04f2-comm-head-11 start=2026-10-24 03:11:40 end=2026-10-24 03:14:37 elapsed=176s bound=1200s status=OK rc=0`
- 12: 24 files, 622 passed, 2 skipped, 11 deselected: `[pyt] tag=s04f2-comm-head-12 start=2026-10-24 03:14:40 end=2026-10-24 03:16:00 elapsed=80s bound=1200s status=OK rc=0`
- 13: 24 files, 463 passed, 8 deselected: `[pyt] tag=s04f2-comm-head-13 start=2026-10-24 03:16:04 end=2026-10-24 03:17:26 elapsed=82s bound=1200s status=OK rc=0`
- 14: 23 files, 1204 passed, 9 skipped, 35 xfailed: `[pyt] tag=s04f2-comm-head-14 start=2026-10-24 03:17:27 end=2026-10-24 03:18:45 elapsed=78s bound=1200s status=OK rc=0`

Comm guard lines (per chunk, every one the ratchet-baseline egress class or the r42 / p08 sentinel): `[netguard] blocked` 4/2, 7/1, 16/5, 20/12, 24/3, 25/7, 35/30, 37/9, 42/16, 53/17, 73/23, 98/11, 122/47, 156/21 (attempts / nodes); one `[hermeticity] sentinel checked N test(s)` line per chunk.

HEAD failed nodes (6): the 4 `tests/.pre_impl_failures.txt` rows (test_auth_interceptor x2, test_page_scraping x2) + the 2 cold-tiktoken ERRORs of test_prompt_truth. Python set difference against the GREEN base record (`S81-04_green/comm/base_failed.txt`, 7 nodes): **branch-only-new EMPTY**; base-only = the ST1 timing row `test_r07_usage_status_on_reads_in_one_gather[sync_on]` (as in the GREEN, fix 1 and the re-verifier). (A first shell `comm` over the CRLF-written head file showed every line as different: a line-ending artefact of `Path.write_text` on Windows, not a result; the Python set difference is the measurement.)

Non-pytest gates: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on the leaf and the unit file: All checks passed; `--select F401,F841`: All checks passed; `py_compile` of both: ok; `black --check --config pyproject.toml` (26.5.1) on the leaf: "1 file would be left unchanged"; `git diff --check`: clean; added-line sweep (524 added lines: @gmail, +973, 8-digit runs, sk- / JWT / PEM / credentialed-URL shapes): 0 hits; bytes > 127 in added lines: 0; the pre-commit hook on the commit: passed (its ruff step "All checks passed!", its black-allowlist step "1 file would be left unchanged").

## 4. Mutation table (fix-2 bytes; `<notes>/mutate_fix2.py`: byte copy -> exact edit matching once -> the FULL unit file `-x` -> restore -> sha256 compare = restored every time (leaf `050a8743...` before and after both batches); `.qa-mutation.lock` created and removed)

36 mutants: **35 KILLED** (every one by an AssertionError), **1 SURVIVED** (M51, EQUIVALENT by ruling F1-2).

| # | Mutant | Status | First killer | [pyt] |
|---|---|---|---|---|
| A02 | EVAL observation lowers the base (no max) | KILLED | r50 | `[pyt] tag=s04f2-a02 start=2026-10-24 02:16:19 end=2026-10-24 02:16:59 elapsed=40s bound=600s status=FAIL rc=1` |
| N04 | F1-2 a GET after a landed write replaces the base | KILLED | r49 | `[pyt] tag=s04f2-n04 start=2026-10-24 02:17:04 end=2026-10-24 02:17:44 elapsed=41s bound=600s status=FAIL rc=1` |
| N05 | F1-2 the write sequence never moves | KILLED | r49 | `[pyt] tag=s04f2-n05 start=2026-10-24 02:17:47 end=2026-10-24 02:18:22 elapsed=34s bound=600s status=FAIL rc=1` |
| M50 | in-flight delta never settled | KILLED | r50 | `[pyt] tag=s04f2-m50 start=2026-10-24 02:18:27 end=2026-10-24 02:18:58 elapsed=31s bound=600s status=FAIL rc=1` |
| M51 | generation guard removed | SURVIVED (EQUIVALENT, F1-2) | - | `[pyt] tag=s04f2-m51 start=2026-10-24 02:19:00 end=2026-10-24 02:19:40 elapsed=40s bound=600s status=OK rc=0` |
| M29 | memo never stale | KILLED | r39 | `[pyt] tag=s04f2-m29 start=2026-10-24 02:19:42 end=2026-10-24 02:20:14 elapsed=32s bound=600s status=FAIL rc=1` |
| M35 | local delta not added to the memo | KILLED | r39b | `[pyt] tag=s04f2-m35 start=2026-10-24 02:20:15 end=2026-10-24 02:20:50 elapsed=34s bound=600s status=FAIL rc=1` |
| Y1 | F2-1 an older-day EVAL replaces the memo (the ruled mutant) | KILLED | r59 (also r60 x2 with `-k`) | `[pyt] tag=s04f2-y1 start=2026-10-24 02:20:52 end=2026-10-24 02:21:36 elapsed=44s bound=600s status=FAIL rc=1` |
| Y1b | F2-1 every other-day EVAL ignored (a later day too) | KILLED | r59 | `[pyt] tag=s04f2-y1b start=2026-10-24 02:21:38 end=2026-10-24 02:22:22 elapsed=44s bound=600s status=FAIL rc=1` |
| Y2 | F2-1 an older-day GET replaces the memo | KILLED | r60b | `[pyt] tag=s04f2-y2 start=2026-10-24 02:22:24 end=2026-10-24 02:23:03 elapsed=40s bound=600s status=FAIL rc=1` |
| Y3 | F2-1 an EVAL total below 0 observed as is | KILLED | r59b | `[pyt] tag=s04f2-y3 start=2026-10-24 02:23:05 end=2026-10-24 02:23:46 elapsed=41s bound=600s status=FAIL rc=1` |
| A03 | /health exhausted ignores the memo day (X3) | KILLED | r61 | `[pyt] tag=s04f2-a03 start=2026-10-24 02:23:48 end=2026-10-24 02:24:22 elapsed=35s bound=600s status=FAIL rc=1` |
| A04 | /health ignores the in-flight deltas (X4) | KILLED | r62b | `[pyt] tag=s04f2-a04 start=2026-10-24 02:24:24 end=2026-10-24 02:24:55 elapsed=31s bound=600s status=FAIL rc=1` |
| A05 | admin snapshot ignores the in-flight deltas (X5) | KILLED | r50 | `[pyt] tag=s04f2-a05 start=2026-10-24 02:24:58 end=2026-10-24 02:25:33 elapsed=35s bound=600s status=FAIL rc=1` |
| N11 | F1-4c no fail-open window | KILLED | r54 | `[pyt] tag=s04f2-n11 start=2026-10-24 02:25:36 end=2026-10-24 02:26:20 elapsed=44s bound=600s status=FAIL rc=1` |
| N12 | F1-4c one global window | KILLED | r54 | `[pyt] tag=s04f2-n12 start=2026-10-24 02:26:21 end=2026-10-24 02:27:03 elapsed=41s bound=600s status=FAIL rc=1` |
| N13 | F1-4c an in-window call counted again | KILLED | r54 | `[pyt] tag=s04f2-n13 start=2026-10-24 02:27:04 end=2026-10-24 02:28:06 elapsed=61s bound=600s status=FAIL rc=1` |
| N13b | F1-4c every waiter of one failed GET counted | KILLED | r54b | `[pyt] tag=s04f2-n13b start=2026-10-24 02:28:09 end=2026-10-24 02:29:10 elapsed=61s bound=600s status=FAIL rc=1` |
| Y4 | F2-2 record_soon windowed (the ruled "records windowed" mutant) | KILLED | r62 (also r62c, r62d with `-k`) | `[pyt] tag=s04f2-y4 start=2026-10-24 02:30:04 end=2026-10-24 02:30:52 elapsed=48s bound=600s status=FAIL rc=1` |
| Y4b | F2-2 the sync record windowed | KILLED | r62c | `[pyt] tag=s04f2-y4b start=2026-10-24 02:30:54 end=2026-10-24 02:31:45 elapsed=50s bound=600s status=FAIL rc=1` |
| Y5 | F2-2 a failed record drops its delta | KILLED | r62b | `[pyt] tag=s04f2-y5 start=2026-10-24 02:31:51 end=2026-10-24 02:32:41 elapsed=49s bound=600s status=FAIL rc=1` |
| Y6 | F2-2 every failed record counted | KILLED | r62b | `[pyt] tag=s04f2-y6 start=2026-10-24 02:32:44 end=2026-10-24 02:33:53 elapsed=69s bound=600s status=FAIL rc=1` |
| Y7 | F2-2 a record failure opens the read window | KILLED | r62b | `[pyt] tag=s04f2-y7 start=2026-10-24 02:33:59 end=2026-10-24 02:35:16 elapsed=77s bound=600s status=FAIL rc=1` |
| Y8 | F2-2 a record failure inside the read window counted again | KILLED | r62d | `[pyt] tag=s04f2-y8 start=2026-10-24 02:35:22 end=2026-10-24 02:36:02 elapsed=40s bound=600s status=FAIL rc=1` |
| Y10 | F1-3 a cancelled queued sync record keeps its delta | KILLED | r51 | `[pyt] tag=s04f2-y10 start=2026-10-24 02:36:03 end=2026-10-24 02:36:27 elapsed=23s bound=600s status=FAIL rc=1` |
| X1 | `_spent_async` awaits `wrap_future(shared GET)` | KILLED | r63 | `[pyt] tag=s04f2-x1 start=2026-10-24 02:36:28 end=2026-10-24 02:36:55 elapsed=28s bound=600s status=FAIL rc=1` |
| X6 | `_record_gave_up` drops a failure finished before the give-up | KILLED | r64 | `[pyt] tag=s04f2-x6 start=2026-10-24 02:36:58 end=2026-10-24 02:37:17 elapsed=19s bound=600s status=FAIL rc=1` |
| A09 | record shield removed (X2) | KILLED | r52 | `[pyt] tag=s04f2-a09 start=2026-10-24 02:37:18 end=2026-10-24 02:37:33 elapsed=16s bound=600s status=FAIL rc=1` |
| N06 | F1-3 a cancelled sync record never settles its flight | KILLED | r51 | `[pyt] tag=s04f2-n06 start=2026-10-24 02:37:35 end=2026-10-24 02:37:55 elapsed=20s bound=600s status=FAIL rc=1` |
| N07 | F1-4a a late record counted as a fail-open | KILLED | r52 | `[pyt] tag=s04f2-n07 start=2026-10-24 02:37:57 end=2026-10-24 02:38:18 elapsed=20s bound=600s status=FAIL rc=1` |
| N08 | F1-4a the late counter never moves | KILLED | r52 | `[pyt] tag=s04f2-n08 start=2026-10-24 02:38:20 end=2026-10-24 02:38:37 elapsed=17s bound=600s status=FAIL rc=1` |
| N10 | F1-4b no single flight | KILLED | r53 | `[pyt] tag=s04f2-n10 start=2026-10-24 02:38:39 end=2026-10-24 02:38:57 elapsed=18s bound=600s status=FAIL rc=1` |
| N17 | F1-7 mini uses the 4o bound | KILLED | r07[image_mini] | `[pyt] tag=s04f2-n17 start=2026-10-24 02:39:00 end=2026-10-24 02:39:07 elapsed=7s bound=600s status=FAIL rc=1` |
| N18 | F1-7 an unknown provider takes the Anthropic cap | KILLED | r57[None-mistral-49000] | `[pyt] tag=s04f2-n18 start=2026-10-24 02:39:10 end=2026-10-24 02:39:24 elapsed=14s bound=600s status=FAIL rc=1` |
| N19 | F1-7 the chokepoint does not thread the model | KILLED | r28[image_4o] | `[pyt] tag=s04f2-n19 start=2026-10-24 02:39:26 end=2026-10-24 02:39:35 elapsed=10s bound=600s status=FAIL rc=1` |
| Y9 | F2-3 the mini bound back at 37,000 | KILLED | r07[image_mini] | `[pyt] tag=s04f2-y9 start=2026-10-24 02:39:37 end=2026-10-24 02:39:45 elapsed=8s bound=600s status=FAIL rc=1` |

Second-killer check (`S04F2_K` over the new rows only): Y1 killed by r59, r60[after_the_new_day_get], r60[inside_the_new_day_get] (`[pyt] tag=s04f2-y1-k start=2026-10-24 02:40:28 end=2026-10-24 02:40:37 elapsed=9s bound=600s status=FAIL rc=1`); Y2 by r60b (`[pyt] tag=s04f2-y2-k start=2026-10-24 02:40:38 end=2026-10-24 02:40:58 elapsed=20s bound=600s status=FAIL rc=1`); Y4 by r62, r62c, r62d (`[pyt] tag=s04f2-y4-k start=2026-10-24 02:40:59 end=2026-10-24 02:41:12 elapsed=13s bound=600s status=FAIL rc=1`); A04 by r62b (`[pyt] tag=s04f2-a04-k start=2026-10-24 02:41:13 end=2026-10-24 02:41:22 elapsed=9s bound=600s status=FAIL rc=1`).

## 5. Every round-1 survivor and its fate

| Survivor | Fate on the fix-2 bytes |
|---|---|
| A02 (EVAL observation lowers the base) | KILLED by r50 (since fix 1; re-run) |
| A03 (/health exhausted ignores the memo day; re-verifier X3) | KILLED by the new PIN r61 (F2-1) |
| A04 (/health ignores the in-flight deltas; X4) | Stated limit by F2-5 (row limit 10, PR body limit 10). Additionally KILLED by r62b: F2-2 keeps a failed record's delta for the day, so the in-flight sum is now observable on /health (`exhausted` must reflect it) |
| A05 (admin snapshot ignores the in-flight deltas; X5) | KILLED by r50 (since fix 1; re-run) |
| A09 (record shield removed; X2) | KILLED by r52 (since fix 1; re-run) |
| M50 (in-flight delta never settled) | KILLED by r50 (since fix 1; re-run) |
| M51 (test-reset generation guard removed) | SURVIVED, EQUIVALENT by ruling F1-2 (test hygiene only) |
| X1 (`wrap_future` instead of `_follow`) | KILLED by the new PIN r63 (F2-4) |
| X6 (`_record_gave_up` already-failed arm dropped) | KILLED by the new PIN r64 (F2-4) |

## 6. Deviations

- D1 (RED-file edits beyond appended rows, forced by the rulings): r54 loses its two in-window record lines and its docstring is reworded (F2-2 supersedes F1-4c for records; the r54 lines encoded the old rule and the read-window assertions are unchanged); the 37,000 literal moves to 49,000 in r07[image_mini, image_nomodel] and r28[image] (and the r28 comment) besides the named r57 (F2-3 changes the constant those rows pin). Every other existing row is byte-identical (`<notes>/red/red_file_amendments.diff` = the RED-step diff; r62c / r62d were appended after it).
- D2 (F2-2 vs F1-3, question Q1): F2-2 says a record that "fails or times out keeps its delta"; F1-3 (pinned by the frozen r51) cancels a sync record still QUEUED at its bound and settles its delta. F1-3 is kept: r51 is frozen and F2-2 names no change to it. So a cancelled queued sync record is the one record that can be dropped; the row and the PR body say so ("no spend is dropped on the request path": the chokepoint uses `record_soon` only, the sync `record` has no production caller). The sync record is not made non-awaited either (it keeps its bounded wait; the F2-2 adjectives "shielded, non-awaited" describe `record_soon`).
- D3 (F2-2 counting design, question Q2): "counts once per window" is implemented with a separate per-lane counting window (`_RECORD_FAIL_COUNTED`, the memo window): a record failure is counted unless the lane's read window or a counted record failure's window is open, and it never opens the read window. Opening the read window from a record failure was rejected because an EVAL-only failure (for example Upstash refusing the Lua) would then blind the reads while records still fail, defeating the kept local deltas (pinned by r62b's second GET and mutant Y7).
- D4: `record_soon` called with no running loop (a caller bug; no EVAL attempted) keeps its pre-fix handling (delta settled, one plain fail-open); question Q3.
- D5: the reverifier's m1 scenario ran a SYNC admit in a thread; the rows use the async admit with the same gated GET (same leaf code path `_observe_read`), plus the extra `_observe_read` row r60b (a pre-midnight GET returning after a new-day read) so the read-side guard has its own killer (Y2), and r59b for the below-0 clamp (Y3). r62c / r62d were added so the sync-record and in-window counting halves of F2-2 have killers (Y4b, Y8).
- D6: `git commit -F <notes>/commit_msg.txt -- <paths>` was used instead of an inline `-m` (the message carries no backtick and needed no shell quoting); the trailer is `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- D7: as in round 1, the rulings file has no section titled "Procedure for the fix agent"; the task text's order was followed (RED, GREEN, docs, gates, one commit).

## 7. Questions for the gate

- Q1 (D2): keep F1-3 for a sync record still queued at its bound (dropped, delta settled), or make the sync record shielded / non-awaited so it is never dropped (r51 would then be re-pinned)?
- Q2 (D3): confirm the separate record-failure counting window (no read window opened by a record failure).
- Q3 (D4): should `record_soon` with no running loop also keep its delta (a caller bug path, no EVAL attempted)?
- Q4: the comm set was not re-run at base; the GREEN base record was reused as ruled (F2-7).

## 8. NOT MEASURED

- Upstash's real EVAL / GET latency and its acceptance of the two Lua scripts (canary items); the production Railway-to-Upstash RTT (the congestion threshold scales with it; r62 uses a 0.1 s fake at a 0.2 s bound).
- The gpt-4o-mini image token rule (no web read; UNVERIFIED, S81-07).
- The 323 hook-file nodes outside `-k black` (CI covers them; the unit edits no `.githooks`).
- The comm set at base (the GREEN base record reused, F2-7).

## 9. Final state

- `git status --short`: empty. HEAD `04a1ba9fa85cb1b9ea0ee20de97def3ebb5fe23e` on `feature/s81-s04-spend-breaker` (4 commits on `e1878dd8`: c4490e91, b5f29e35, f1b29405, 04a1ba9f). Not pushed, no PR, no rebase.
- No `.qa-mutation.lock`; the scratch worktree `pre_f1b2` removed and absent from `git worktree list`; no `.env` anywhere in `<scratchpad>/S81-04_fix2/` (find: none); no pytest process of this agent alive.
- PR body: `<scratchpad>/S81-04_fix2/PR_BODY.md` (fix-1 body + the "Fix round 2" section, updated bullets, node table, pin changes and limits; ASCII except the attribution emoji).
