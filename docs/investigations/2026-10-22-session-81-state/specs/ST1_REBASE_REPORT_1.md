# ST1 LOOP-STALL (ENABLE_USAGE_PATH_OFFLOOP): rebase-and-gates report

- Unit ST1, rebase-and-gates step. Agent: REBASE-AND-GATES, Opus 5.5 (claude-opus-5-5). 2026-10-23 12:00 AST start.
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-st1`, branch `feature/s81-st1-usage-path-offloop`. Start: HEAD `e0ffed64986a69a9d33b54f43f579c8d84ba5b42` verified, branch verified, `git status --short` empty.
- Notes folder `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/ST1_pr/` (notes.md, snap.py + snap_pre/ + snap_post_rebase/ byte copies with SHA256SUMS.json, resolve.py, verify_claude.py, docs_edit.py + CLAUDE.md.before_docs_edit, commit_msg.txt, comm_build_pr.py, run_chunk_pr.py, comm/ (comm_list.txt, comm_why.tsv, comm_delta.txt, comm_chunk_00..06.txt, head_/base_NN.log, head_/base_NN_failed.txt, head_/base_failed_all.txt, flush_head/base.log), ci_order.txt, pins28.txt, *.log, PR_BODY.md).
- Inputs read: s81-common.txt (start and end), RULINGS_FIX1_ST1, GATE_ST1, RULINGS_ST1, ST1_FIX1_REPORT, ST1_FIX1_REVERIFY, the fix agent's PR_BODY.md, session-80 prod_evidence.json findings[7] (for MIN-RV-4).

## Result

- Base: origin/main `84c861f68ba3b23606c69ce2d1f78597e2f3037b` (fetched 12:05; = the task's base).
- New HEAD: `d19360c5b7ac81dfb122f5dff1d63ed0410a72e6` on `feature/s81-st1-usage-path-offloop` (not pushed). Commits on the base: `72763dca` (GREEN feb39dc0 replayed), `dc94a454` (fix round 1 e0ffed64 replayed), `d19360c5` (docs: the three wording closures; through the pre-commit hook, ~40 s, rc 0; trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`).
- `git diff --stat origin/main...HEAD`: CLAUDE.md 7, app/services/review_service.py 73, app/services/usage_service.py 97, app/utils/redis_offloop.py 30, tests/test_s81_st1_usage_path_offloop.py 2768; 5 files, 2960 insertions, 15 deletions; no whole-file diff; no other file.
- `git status --short` at the end: empty (13:40).

## Conflicts and resolutions

| # | replayed commit | file | ours (upstream side) | theirs (branch side) | resolution |
|---|---|---|---|---|---|
| 1 | feb39dc0 (GREEN) | CLAUDE.md, one region at line 479 (after the SESSION 80 B3 row + blank) | B4 header + `ENABLE_URL_MODE_V2` row, blank, D03 header + `ENABLE_DATA_GUARDS_V2` row | ST1 header + `ENABLE_USAGE_PATH_OFFLOOP` row (GREEN text) | UNION in session order B3, B4, D03, ST1: ours, one blank, theirs (resolve.py union, binary, CRLF kept) |
| 2 | e0ffed64 (fix round 1) | CLAUDE.md, one region at line 479 | B4 block, blank, D03 block, blank, GREEN ST1 block | fix-round ST1 header + row (the in-place rewrite) | B4 + D03 kept; the GREEN ST1 two lines replaced by the fix-round ST1 two lines (resolve.py replace; exactly one ST1 header checked on each side) |

- The fix-round's other CLAUDE.md hunks (the M13-05 `ENABLE_SYNC_DB_OFFLOAD` row and the S77 row parenthetical) auto-merged.
- Proof (verify_claude.py): main = base + 6 inserted lines at base line 479 (pure insertion); the resolved CLAUDE.md LF sha256 `bb68a1c1f1667a2525e5c56eef922a74be6bf8a52dcf3f2d3b84503379d72737` = the pre-rebase branch blob with those 6 lines inserted before the ST1 header: MATCH; B3 / B4 / D03 / ST1 headers once each; CRLF 949 / 949.
- `git diff --check origin/main 72763dca` rc 0 after continue 1; `git diff --check origin/main HEAD` rc 0 after continue 2 and at the end; `grep -rln '^<<<<<<<\|^>>>>>>>' CLAUDE.md app tests` empty.
- review_service.py auto-merged with D03: line 21 `from app.utils.redis_offloop import run_redis_offloop, run_redis_offloop_pool, usage_path_offloop_enabled`, line 24 `from app.services.deny_hosts import data_guards_v2_enabled, is_denied_url` (both names sets present; D03 call sites :181 / :334 present). The `+`/`-` lines of `git diff origin/main HEAD` for review_service.py and for CLAUDE.md (before the docs commit) are IDENTICAL to those of `git diff 95cf6f86 e0ffed64`.
- Blobs unchanged by the rebase: usage_service.py `2e15e081...`, redis_offloop.py `4637d087...`, the RED file `68871bc2...` (= e0ffed64's blobs).
- No test file conflicted. No `git rebase --abort` needed.

## Files (sha256 of the bytes on disk at the end)

| path | working copy sha256 | note |
|---|---|---|
| CLAUDE.md | 8dd852db3541b8e1c930d16ece46be1ad2ec3ef60cd53825246cf5e0b2a43c6f | LF sha 90af5754fd50509ce7724c635870f8eeb69361e101cd4e2835437202c09cf3e0; CRLF 949/949; bytes > 127: 3952 (unchanged); the ST1 row 0 |
| app/services/review_service.py | 781eec79c671ce52f84c34f1fa24b86ecf59be19c975fddbc7475be0d5a9f770 | CRLF 1172/1172; = main + ST1 hunks |
| app/services/usage_service.py | 6940fddd7f6cb2cc3bb78d9569251b24aee5e08b315f6dfcc16abc9949e7c89d | unchanged |
| app/utils/redis_offloop.py | 955e25e5ce9b1841a8649153851d7530f158afd69186e6cfdf796106125704e7 | unchanged |
| tests/test_s81_st1_usage_path_offloop.py | ad0b9726a5af043a20d280c4430f2231d28d5c67ed640b38e98534183bece1eb (CRLF working copy) | committed blob / LF sha 65088fa52c15ec652bcc2ac8bb340443883a05efaef8a5df846223cf1a7b7cbf = unchanged (the rebase re-checked the file out under core.autocrlf=true, so the working copy is now CRLF; the blob is the same) |

## Wording closures (docs only; no pin row, no test edit, no mutant this step)

Edited in place in the CLAUDE.md ST1 row (docs_edit.py: exact-once byte replacements inside the row, a byte copy first, ASCII checked) and the same edits in the PR body:

- MIN-RV-4: "Production showed `usage_status` p50 4.2 s with child I/O under 0.8 s (...)" -> "p50 4,164 ms in the 14-day Sentry trace search, and the single trace 5915a2b6 showed a `usage_status` of 4,266 ms whose child I/O summed to under 0.8 s (session-80 prod_evidence findings 8/9)" (checked against prod_evidence.json findings[7] evidence[0] / [1]).
- MIN-RV-2: "Fix round 1 pins (all with the flag set inside the row)" -> "(every ON-path case sets the flag inside the row; r39[direct_cancelled] drives `run_redis_offloop_pool` directly and sets no flag, the dispatcher being flag-independent)".
- MIN-RV-1: the canary "the `[USAGE-OFFLOOP]` WARNING count (expect 0)" -> names both families: the usage dispatch failures (`dispatch failed fn=<fn>`) AND the reviews L1 write failures (`reviews L1 write dispatch failed type=<Type>`: a deepcopy snapshot failure or an exception inside the pool write, as r41 and r39[reviews_write] pin; `set_cached` swallows its own errors, so the in-pool case is near-unreachable in production); a compute-body failure is not counted since fix round 1. Code checked: review_service.py `_reviews_l1_write_offloop` logs that template in the deepcopy except arm and in the in-task except arm; cache_service.py `set_cached` wraps its write in try/except and returns False.
- RED file: sha 65088fa5... unchanged (no new row: the task's PIN ROWS item is DOCS ONLY for this unit).
- Added-line sweep on the docs commit (@gmail, +973, 8-digit runs, sk-/eyJ/AKIA/xox, PEM, credentialed URL): 0 hits; 0 bytes > 127.

## Gates at the rebased HEAD d19360c5 (every pytest through pyt.py, one process at a time, foreground; flags unset unless stated)

1. Unit file:
   - `[pyt] tag=st1pr-unit-off start=2026-10-23 12:23:08 end=2026-10-23 12:23:30 elapsed=21s bound=600s status=OK rc=0` 531 passed, 43 warnings; `[hermeticity] sentinel checked 531 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
   - `[pyt] tag=st1pr-unit-on-exported start=2026-10-23 12:23:52 end=2026-10-23 12:24:30 elapsed=38s bound=600s status=OK rc=0` (ENABLE_USAGE_PATH_OFFLOOP=true exported) 531 passed, 21 warnings; hermeticity 531; netguard 0. The autouse `_st1_env` fixture deletes the flag per node, so this re-measures OFF; the ON evidence is the rows that set the flag. The warning count differs from the OFF run (43 vs 21; the fix round saw 43 both ways): every warning in both runs is a DeprecationWarning of the same three classes (FastAPI `on_event`, supabase-py `verify` / `timeout`, "no current event loop"); the difference is the per-node attribution of the supabase-py client-build warnings in r33; no `never awaited` / `never retrieved` line in either log.
   - Extra: `[pyt] tag=st1pr-d03-alone start=2026-10-23 12:27:26 end=2026-10-23 12:28:06 elapsed=41s bound=600s status=OK rc=0` tests/test_s81_d03_deny_and_guards.py alone: 292 passed; hermeticity 292; netguard 0.
2. Conflicted test files alone: none (only CLAUDE.md conflicted).
3. R8 pair: `[pyt] tag=st1pr-r8-pair start=2026-10-23 12:28:18 end=2026-10-23 12:28:45 elapsed=27s bound=600s status=OK rc=0` 272 passed; hermeticity 272; netguard 0.
4. Metering:
   - `[pyt] tag=st1pr-metering-unset start=2026-10-23 12:29:02 end=2026-10-23 12:29:07 elapsed=5s bound=600s status=OK rc=0` 21 passed; hermeticity 21; `[netguard] blocked 2 attempt(s) from 2 node(s)` (test_camera_success_consumes_once_and_never_refunds, test_url_compare_saves_history_with_input_type_url: the sentinel pair of the base record).
   - `[pyt] tag=st1pr-metering-on start=2026-10-23 12:29:09 end=2026-10-23 12:29:31 elapsed=21s bound=600s status=OK rc=0` (ENABLE_PAID_ROUTE_METERING=true) 21 passed; hermeticity 21; netguard 2 (same pair).
   - `[pyt] tag=st1pr-metering-st1-exported start=2026-10-23 12:29:33 end=2026-10-23 12:29:45 elapsed=12s bound=600s status=OK rc=0` (ENABLE_USAGE_PATH_OFFLOOP=true) 21 passed; hermeticity 21; netguard 2 (same pair).
5. CI-order set (31 files, sorted, list sha256 960d39d9... = ST1_green/ci_order.txt): `[pyt] tag=st1pr-ci-order start=2026-10-23 12:30:34 end=2026-10-23 12:31:52 elapsed=77s bound=1200s status=OK rc=0` 1518 passed; hermeticity 1518; netguard 2 (the metering pair).
   - Extra: the 28-file pin set (the 31 minus the RED file and the two CLAUDE.md readers) flag exported: `[pyt] tag=st1pr-pins-on-exported start=2026-10-23 12:58:46 end=2026-10-23 13:00:35 elapsed=109s bound=1200s status=FAIL rc=1` 9 failed / 899 passed; hermeticity 908; netguard 2. The 9 = CLAUDE.md limit (13) node by node: test_review_source_consult.py::test_get_reviews_extraction_persisted_even_if_consult_cancels, ::test_get_reviews_persists_extraction_before_consult; test_s77_redis_offloop.py::test_off_call_shapes_exact[S6], ::test_off_no_new_suspension_on_hit_paths[s6_l1_hit-off], ::test_parity_s6[nocache], ::test_s6_post_extraction_write_stays_inline_on, ::test_s6_reviews_l1_read_placement[off], ::test_s6_reviews_l2_promotion_set_stays_inline[off]; test_youtube_reviews_race.py::test_get_reviews_persists_extraction_before_youtube_consult.
6. Comm set re-derived at the rebased HEAD (comm_build_pr.py = the RED builder + the module-path clause + the explicit members): TRUE MEMBER COUNT 162 = the fix round's 157 (0 dropped) + tests/test_s80_url_mode_v2.py (B4), tests/test_s81_d03_deny_and_guards.py (D03), tests/test_cache_service_bounded_transport.py, tests/test_limiter_endpoint_key.py (both `spec_from_file_location(..., real.__file__)`), tests/test_content_blocklist_arabic_parity.py (`Path(css.__file__)` to app/data). Chunks 00-05 of 25, 06 of 12; bound 1200. HEAD:
   - `[pyt] tag=st1pr-comm-head-00 start=2026-10-23 12:34:24 end=2026-10-23 12:35:16 elapsed=52s bound=1200s status=OK rc=0` 1276 passed, 1 deselected; hermeticity 1276; netguard 18 / 6
   - `[pyt] tag=st1pr-comm-head-01 start=2026-10-23 12:35:18 end=2026-10-23 12:35:58 elapsed=40s bound=1200s status=OK rc=0` 933 passed; hermeticity 933; netguard 35 / 13
   - `[pyt] tag=st1pr-comm-head-02 start=2026-10-23 12:36:16 end=2026-10-23 12:37:59 elapsed=102s bound=1200s status=OK rc=0` 659 passed, 4 deselected; hermeticity 659; netguard 24 / 23
   - `[pyt] tag=st1pr-comm-head-03 start=2026-10-23 12:38:01 end=2026-10-23 12:38:36 elapsed=36s bound=1200s status=FAIL rc=1` 855 passed, 26 skipped, 2 deselected, 1 xfailed, 2 errors; hermeticity 858; netguard 2 / 2
   - `[pyt] tag=st1pr-comm-head-04 start=2026-10-23 12:38:39 end=2026-10-23 12:40:55 elapsed=137s bound=1200s status=OK rc=0` 2356 passed; hermeticity 2356; netguard 0 / 0
   - `[pyt] tag=st1pr-comm-head-05 start=2026-10-23 12:41:07 end=2026-10-23 12:41:55 elapsed=48s bound=1200s status=OK rc=0` 684 passed, 2 skipped, 16 deselected, 35 xfailed; hermeticity 720; netguard 85 / 29
   - `[pyt] tag=st1pr-comm-head-06 start=2026-10-23 12:41:57 end=2026-10-23 12:42:29 elapsed=33s bound=1200s status=OK rc=0` 883 passed, 9 skipped; hermeticity 892; netguard 0 / 0
   Base (detached scratch worktree `<notes>/base_wt` at 84c861f6, no node_modules, no .env, `git status --short` empty before removal; removed with `git worktree remove --force`, absent from `git worktree list`, directory gone):
   - `[pyt] tag=st1pr-comm-base-00 start=2026-10-23 12:43:30 end=2026-10-23 12:44:49 elapsed=79s bound=1200s status=OK rc=0` 1276 passed, 1 deselected; hermeticity 1276; netguard 18 / 6
   - `[pyt] tag=st1pr-comm-base-01 start=2026-10-23 12:44:52 end=2026-10-23 12:45:52 elapsed=60s bound=1200s status=OK rc=0` 933 passed; hermeticity 933; netguard 32 / 12
   - `[pyt] tag=st1pr-comm-base-02 start=2026-10-23 12:46:00 end=2026-10-23 12:48:47 elapsed=167s bound=1200s status=OK rc=0` 659 passed, 4 deselected; hermeticity 659; netguard 24 / 23
   - `[pyt] tag=st1pr-comm-base-03 start=2026-10-23 12:49:12 end=2026-10-23 12:49:49 elapsed=36s bound=1200s status=FAIL rc=1` 855 passed, 26 skipped, 2 deselected, 1 xfailed, 2 errors; hermeticity 858; netguard 2 / 2
   - `[pyt] tag=st1pr-comm-base-04 start=2026-10-23 12:49:51 end=2026-10-23 12:52:15 elapsed=144s bound=1200s status=OK rc=0` 2356 passed; hermeticity 2356; netguard 0 / 0
   - `[pyt] tag=st1pr-comm-base-05 start=2026-10-23 12:52:17 end=2026-10-23 12:53:04 elapsed=47s bound=1200s status=OK rc=0` 684 passed, 2 skipped, 16 deselected, 35 xfailed; hermeticity 720; netguard 85 / 29
   - `[pyt] tag=st1pr-comm-base-06 start=2026-10-23 12:53:07 end=2026-10-23 12:53:33 elapsed=26s bound=1200s status=OK rc=0` 883 passed, 9 skipped; hermeticity 892; netguard 0 / 0
   FAILED/ERROR node-id sets: HEAD = base = {tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable} (the cold-tiktoken pair, identical both sides). `comm -13` EMPTY; `comm -23` EMPTY.
   Netguard difference, chunk 01 (HEAD 35 / 13 vs base 32 / 12): one extra node `tests/test_flush_live_price_key.py::test_flag_off_body_is_the_legacy_shape_exactly [egress] socket.getaddrinfo api.openai.com:443` (the file's nine other nodes show the same blocked resolve on both sides). The file alone, both sides: `[pyt] tag=st1pr-flush-head start=2026-10-23 12:56:29 end=2026-10-23 12:56:48 elapsed=19s bound=600s status=OK rc=0` 45 passed, hermeticity 45, netguard 28 / 10; `[pyt] tag=st1pr-flush-base start=2026-10-23 12:56:51 end=2026-10-23 12:57:12 elapsed=21s bound=600s status=OK rc=0` 45 passed, hermeticity 45, netguard 28 / 10; node lists identical (the node included on both sides): run-order timing, not a regression.
7. CLAUDE.md readers after the docs commit: `[pyt] tag=st1pr-claude-readers start=2026-10-23 12:22:48 end=2026-10-23 12:22:58 elapsed=10s bound=600s status=OK rc=0` tests/test_ci_gates.py + tests/test_behavior_dimension_translation.py: 79 passed; hermeticity 79; netguard 0. (Both are also inside the CI-order set and comm chunks, green there.)
8. Static: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on review_service.py, usage_service.py, redis_offloop.py, the RED file: `All checks passed!`; `py_compile` rc 0 on the same four.
9. Hook files (the unit touches no `.githooks` file: `git diff --name-only origin/main HEAD -- .githooks` is empty; the hook itself passed on the docs commit): the four tests/test_precommit_hook*.py ALONE, `-k "not dash"` (167 selected / 160 deselected of 327): `[pyt] tag=st1pr-hook-notdash start=2026-10-23 13:04:13 end=2026-10-23 13:34:17 elapsed=1804s bound=1800s status=TIMEOUT rc=124` - 51 passed (31 test_precommit_hook.py + 20 test_precommit_hook_phase_b.py), 0 failed before the bound; about 35 s per node; the pyt runner killed the tree; afterwards the only python.exe on the box was the orchestrator's stall_monitor.py (no orphan of mine). The Bash tool moved this one foreground call to the background at its 600 s tool cap; it stayed the only pytest process of mine and I waited for its [pyt] line before anything else ran. The once-alone re-run and the `-k dash` half (160 nodes) were NOT run: at the measured rate each half needs about 95 minutes, so neither can complete in 1800 s, and either run would end past the 2-hour budget (14:00).

Box: `node -e 0` 1.22 s, venv `python -c 0` 1.30 s at 13:02.

## NOT MEASURED

- The pre-commit hook test files: `-k "not dash"` TIMEOUT once (51 / 167 passed, 0 failed; the one [pyt] line above); the once-alone re-run not run; `-k dash` not run: both halves NOT MEASURED (budget and the measured per-node rate; the unit edits no .githooks file).
- The full-file ON state in CI terms beyond the rows that set the flag (by design: the autouse fixture; limit 13).
- The comm set with the flag exported (only the 28-file pin set was measured ON).
- Mutants: none this step (docs only; no row added).
- Production / Railway / Supabase / providers: never touched; no .env read, copied or printed; flags set only in the environment of single runner calls.

## Deviations

- None in the file set (only the five named files differ from origin/main).
- The comm set has 5 more members than the fix round's 157 (the two main-added files the task names + three module-path users the wider regex found); over-inclusion is stricter, not looser.
- Extra gates beyond the list: the D03 file alone (asked as an extra), the metering file with the ST1 flag exported, the 28-file pin set with the flag exported, the flush-live-price file alone at HEAD and base (netguard check).
- Hook gate: the TIMEOUT re-run and the dash half were not run (budget; reason above). The hook-gate runner call was moved to the background by the Bash tool's 600 s cap (not by me); it was still one process and nothing else ran until its [pyt] line was written (I waited with a file-checking loop).
- The PR body carries the sweep's pattern names in its static bullet (@gmail, +973, sk- / eyJ / AKIA / xox); the only 8-digit run in it is inside the RED file's sha256 hex digest (as in the fix draft).

## Final state

- sc-s81-st1: HEAD `d19360c5b7ac81dfb122f5dff1d63ed0410a72e6` on `feature/s81-st1-usage-path-offloop` (verified 13:40), `git status --short` EMPTY, no `.qa-mutation.lock`, not pushed.
- Base scratch worktree removed (absent from `git worktree list`, directory gone). No pytest of mine alive.
- PR body: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/ST1_pr/PR_BODY.md` (pure ASCII, no generation trailer: the orchestrator appends it).
- Git writes made (all inside the task's exception, in this worktree only): `git fetch origin main`, `git rebase origin/main`, `git add CLAUDE.md` + `GIT_EDITOR=true git rebase --continue` twice, `git add CLAUDE.md` + one `git commit -F <msg> -- CLAUDE.md` through the hook; plus the brief's allowed detached scratch worktree add / remove. One `git merge-tree --write-tree` dry run before the rebase (writes a tree object to the object store; no ref).
