# ST1 LOOP-STALL (ENABLE_USAGE_PATH_OFFLOOP): rebase-and-gates report, step 2 (onto dfc6502f)

- Unit ST1, second rebase-and-gates step. Agent: REBASE-AND-GATES, Opus 5.5 (claude-opus-5-5). 2026-10-23 13:43 AST start (first tool call).
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-st1`, branch `feature/s81-st1-usage-path-offloop`. Start: HEAD `d19360c5b7ac81dfb122f5dff1d63ed0410a72e6` verified, branch verified, `git status --short` empty.
- Notes folder `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/ST1_pr2/` (notes.md, snap.py + snap_pre/ + snap_post_rebase/ byte copies with SHA256SUMS.json, resolve.py, verify_claude.py, the five CLAUDE.md blobs base / main / green / fix / branch (LF), CLAUDE.md.conflict1 / .conflict2 (the two conflicted working copies), st1_block_d19360c5.txt, s03_block_main.txt, pm_new.txt / pm_old.txt, comm_build_pr2.py, run_chunk_pr2.py, comm/ (comm_list.txt, comm_why.tsv, comm_delta.txt, comm_chunk_00..06.txt, head_/base_NN.log, head_/base_NN_failed.txt, head_/base_failed_all.txt), ci_order.txt, *.log, PR_BODY.md, this report).
- Inputs read: s81-common.txt (start and end), PLAN_S81 (standing constraints, VERIFY corrections, the ST1 unit text, build and flip order), RULINGS_ST1, GATE_ST1, RULINGS_FIX1_ST1, the previous step's REBASE_REPORT.md, notes.md, helper scripts and PR_BODY.md.

## Result

- Base: origin/main `dfc6502f791cdccbf0a620041f66888a734015d3` (fetched 13:46; = the task's base; 84c861f6..dfc6502f = #369 S81-03: 0197ec1a, 21b37039, 73285fee, merge dfc6502f; it touches CLAUDE.md (+3), admin_routes, image_routes, share_routes, llm_pricing (new), model_router_service, openai_service, response_builder, structured_comparison_service, costs.html, migrations/050 + rollback, tests/test_s75_fanout_identity.py, tests/test_s81_s03_llm_ledger_v2.py (new); no ST1 module).
- New HEAD: `8e663581cc1890b4ea9e9300200f176c2e1312f4` on `feature/s81-st1-usage-path-offloop` (not pushed). Commits on the base: `af674ee7b33e646c676a3a8d78b9e045d9d7d943` (72763dca = GREEN feb39dc0 replayed), `91691999f7ab86e677c45f736560b8d46dd299d3` (dc94a454 = fix round 1 e0ffed64 replayed), `8e663581` (d19360c5 docs commit replayed, auto-merged). Messages and trailers kept (`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` on all three). No new commit of my own (no pin rows).
- `git diff --stat origin/main...HEAD`: CLAUDE.md 7, app/services/review_service.py 73, app/services/usage_service.py 97, app/utils/redis_offloop.py 30, tests/test_s81_st1_usage_path_offloop.py 2768; 5 files, 2960 insertions, 15 deletions; no whole-file diff; no other file.
- `git status --short` at the end: empty (15:12).

## Conflicts and resolutions

Dry run first: `git merge-tree --write-tree --name-only --messages origin/main HEAD` -> CLAUDE.md the only conflict (writes a tree object, no ref).

| # | replayed commit | file | ours (upstream side) | theirs (branch side) | resolution |
|---|---|---|---|---|---|
| 1 | 72763dca (GREEN) -> af674ee7 | CLAUDE.md, one region at line 485 (after the D03 row + blank) | S81-03 header + `ENABLE_LLM_LEDGER_V2` row | ST1 header + `ENABLE_USAGE_PATH_OFFLOOP` row (GREEN text) | UNION in session order B1, B3, B4, D03, S81-03, ST1: ours, one blank, theirs (resolve.py union, binary, CRLF kept) |
| 2 | dc94a454 (fix round 1) -> 91691999 | CLAUDE.md, one region at line 485 | S81-03 block, blank, GREEN ST1 block | fix-round ST1 header + row (the in-place rewrite) | S81-03 kept; the GREEN ST1 two lines replaced by the fix-round ST1 two lines (resolve.py replace; exactly one ST1 header on each side checked) |
| - | d19360c5 (docs) -> 8e663581 | - | - | - | auto-merged, no conflict |

- The fix round's other CLAUDE.md hunks (the M13-05 `ENABLE_SYNC_DB_OFFLOAD` row and the S77 row parenthetical) auto-merged.
- Proof (verify_claude.py after each replay): main = base 84c861f6 + 3 inserted lines at base line 485 (pure insertion: S81-03 header, row, blank); the resolved CLAUDE.md = that commit's pre-rebase blob with those 3 lines inserted before the ST1 header: MATCH after replay 1 (LF sha 0d137673...), replay 2 (LF sha c8208c64...) and at HEAD (LF sha `1d89bfba99d5b30e9976ce80bfa38753e1b01d54474d1b67af25e9783884db1d`, raw `edb9422d4c3fc5afcc51318d77b9e6ed391b8faf2ebffc36fad0244b479b2358`). Headers once each, in order B1, B3, B4, D03, S81-03 (line 485), ST1 (line 488); CRLF 952 / 952; bytes > 127: 3952 (unchanged).
- The ST1 header + row at HEAD equal the d19360c5 bytes (st1_block_d19360c5.txt, sha c5bda1ae... over the two LF lines, 0 bytes > 127): True. The S81-03 header + row equal main's: True.
- `git diff --check origin/main HEAD` rc 0 after continue 1 (on af674ee7), `git diff --check 91691999~1 91691999` rc 0 after continue 2, `git diff --check origin/main HEAD` rc 0 at the end; `grep -rln '^<<<<<<<\|^>>>>>>>' CLAUDE.md app tests` empty (rc 1).
- The `+` / `-` lines of `git diff origin/main HEAD` for CLAUDE.md + review_service.py are IDENTICAL to those of `git diff 84c861f6 d19360c5` (80 lines, cmp equal).
- Blobs unchanged by the rebase (HEAD = d19360c5): review_service.py `9559d5c5...`, usage_service.py `2e15e081...`, redis_offloop.py `4637d087...`, the RED file `68871bc2...`. tests/test_s75_fanout_identity.py HEAD = main `8b13710a...` (main's version; ST1 does not touch it); tests/test_s81_s03_llm_ledger_v2.py HEAD = main `cb0ae7a2...`.
- No test file conflicted. No `git rebase --abort` needed. `git diff --name-only origin/main HEAD -- .githooks` empty.

## Pin rows and mutants

- NONE (as the task states): no test row, no code change, no docs change beyond the conflict resolution. RED file: committed blob / LF sha256 `65088fa52c15ec652bcc2ac8bb340443883a05efaef8a5df846223cf1a7b7cbf` unchanged (working copy CRLF sha ad0b9726a5af043a20d280c4430f2231d28d5c67ed640b38e98534183bece1eb, unchanged from the start of this step). No mutant run; no `.qa-mutation.lock` created.

## Files (sha256 of the bytes on disk at the end)

| path | working copy sha256 | note |
|---|---|---|
| CLAUDE.md | edb9422d4c3fc5afcc51318d77b9e6ed391b8faf2ebffc36fad0244b479b2358 | LF sha 1d89bfba99d5b30e9976ce80bfa38753e1b01d54474d1b67af25e9783884db1d; CRLF 952/952; gt127 3952 |
| app/services/review_service.py | 781eec79c671ce52f84c34f1fa24b86ecf59be19c975fddbc7475be0d5a9f770 | unchanged |
| app/services/usage_service.py | 6940fddd7f6cb2cc3bb78d9569251b24aee5e08b315f6dfcc16abc9949e7c89d | unchanged |
| app/utils/redis_offloop.py | 955e25e5ce9b1841a8649153851d7530f158afd69186e6cfdf796106125704e7 | unchanged |
| tests/test_s81_st1_usage_path_offloop.py | ad0b9726a5af043a20d280c4430f2231d28d5c67ed640b38e98534183bece1eb | LF / blob 65088fa5... unchanged |
| tests/test_s75_fanout_identity.py | ef4f981e17545ed56faf3a7645b6392cd4237be62ca24d46beb4b18d7650146f | main's version (LF f00cd11c...) |

## Gates at the rebased HEAD 8e663581 (every pytest through pyt.py, one process at a time; flags unset unless stated)

Box at 13:52: `node -e 0` 2.58 s, venv `python -c 0` 3.17 s (slow spawn; one other python.exe on the box).

8. Static (first): ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on review_service.py, usage_service.py, redis_offloop.py, the RED file: `All checks passed!`; `py_compile` rc 0 on the same four (13:54).
7. CLAUDE.md readers: `[pyt] tag=st1pr2-claude-readers start=2026-10-23 13:54:54 end=2026-10-23 13:55:06 elapsed=12s bound=600s status=OK rc=0` tests/test_ci_gates.py + tests/test_behavior_dimension_translation.py: 79 passed; `[hermeticity] sentinel checked 79 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
1. Unit file:
   - `[pyt] tag=st1pr2-unit-off start=2026-10-23 13:57:35 end=2026-10-23 13:58:00 elapsed=25s bound=600s status=OK rc=0` 531 passed, 43 warnings; hermeticity 531; netguard 0.
   - `[pyt] tag=st1pr2-unit-on-exported start=2026-10-23 13:58:34 end=2026-10-23 13:58:58 elapsed=24s bound=600s status=OK rc=0` (ENABLE_USAGE_PATH_OFFLOOP=true exported) 531 passed, 43 warnings; hermeticity 531; netguard 0. The autouse `_st1_env` fixture deletes the flag per node, so this re-measures OFF; the ON evidence is the rows that set the flag. No `never awaited` / `never retrieved` line in either log.
2. Conflicted test files alone: none (only CLAUDE.md conflicted).
3. R8 pair: `[pyt] tag=st1pr2-r8-pair start=2026-10-23 13:59:33 end=2026-10-23 13:59:54 elapsed=21s bound=600s status=OK rc=0` 272 passed; hermeticity 272; netguard 0.
4. Metering (tests/test_paid_route_metering.py):
   - `[pyt] tag=st1pr2-metering-unset start=2026-10-23 14:00:10 end=2026-10-23 14:00:15 elapsed=5s bound=600s status=OK rc=0` 21 passed; hermeticity 21; `[netguard] blocked 2 attempt(s) from 2 node(s)` (test_camera_success_consumes_once_and_never_refunds, test_url_compare_saves_history_with_input_type_url: the `neutralized.supabase.invalid` sentinel pair of the base record).
   - `[pyt] tag=st1pr2-metering-st1-exported start=2026-10-23 14:00:17 end=2026-10-23 14:00:23 elapsed=5s bound=600s status=OK rc=0` (ENABLE_USAGE_PATH_OFFLOOP=true) 21 passed; hermeticity 21; netguard 2 (same pair).
   - `[pyt] tag=st1pr2-metering-on start=2026-10-23 14:00:25 end=2026-10-23 14:00:30 elapsed=5s bound=600s status=OK rc=0` (ENABLE_PAID_ROUTE_METERING=true) 21 passed; hermeticity 21; netguard 2 (same pair).
5. CI-order set (31 files, list sha256 960d39d9... = ST1_pr/ci_order.txt = the GREEN list): `[pyt] tag=st1pr2-ci-order start=2026-10-23 14:00:57 end=2026-10-23 14:02:01 elapsed=65s bound=1200s status=OK rc=0` 1518 passed; hermeticity 1518; netguard 2 (the metering pair).
   - Extra: the 28-file pin set (ST1_pr/pins28.txt, sha256 f94b042d...; the 31 minus the RED file and the two CLAUDE.md readers) flag exported: `[pyt] tag=st1pr2-pins-on-exported start=2026-10-23 15:08:43 end=2026-10-23 15:10:38 elapsed=115s bound=1200s status=FAIL rc=1` 9 failed / 899 passed; hermeticity 908; netguard 2 (the metering pair). The 9 = CLAUDE.md limit (13), node for node the same as at d19360c5 (diff of the sorted lists empty): test_review_source_consult.py::test_get_reviews_extraction_persisted_even_if_consult_cancels, ::test_get_reviews_persists_extraction_before_consult; test_s77_redis_offloop.py::test_off_call_shapes_exact[S6], ::test_off_no_new_suspension_on_hit_paths[s6_l1_hit-off], ::test_parity_s6[nocache], ::test_s6_post_extraction_write_stays_inline_on, ::test_s6_reviews_l1_read_placement[off], ::test_s6_reviews_l2_promotion_set_stays_inline[off]; test_youtube_reviews_race.py::test_get_reviews_persists_extraction_before_youtube_consult.
6. Comm set re-derived at the rebased HEAD (comm_build_pr2.py = the previous step's builder, unchanged; inputs: ST1_red/comm/comm_why.tsv for the 31 globbers, ST1_pr/comm/comm_list.txt as the old list). TRUE MEMBER COUNT 163 = the previous 162 (0 dropped) + tests/test_s81_s03_llm_ledger_v2.py, selected by the rule itself (mod:usage_service: line 71 `from app.services import usage_service`, line 1713-1714 patches `consume_comparison_credit` on it; plus pin:astsrc, pin:srcscan, sym:consume_comparison_credit, sym:refund_comparison_credit). Chunks 00-05 of 25, 06 of 13; bound 1200; all ENABLE_* names stripped from the runner env. HEAD:
   - `[pyt] tag=st1pr2-comm-head-00 start=2026-10-23 14:02:24 end=2026-10-23 14:03:00 elapsed=36s bound=1200s status=OK rc=0` 1276 passed, 1 deselected; hermeticity 1276; netguard 18 / 6
   - `[pyt] tag=st1pr2-comm-head-01 start=2026-10-23 14:03:02 end=2026-10-23 14:03:49 elapsed=46s bound=1200s status=OK rc=0` 933 passed; hermeticity 933; netguard 35 / 13
   - `[pyt] tag=st1pr2-comm-head-02 start=2026-10-23 14:03:51 end=2026-10-23 14:05:28 elapsed=97s bound=1200s status=OK rc=0` 659 passed, 4 deselected; hermeticity 659; netguard 24 / 23
   - `[pyt] tag=st1pr2-comm-head-03 start=2026-10-23 14:05:41 end=2026-10-23 14:06:17 elapsed=36s bound=1200s status=FAIL rc=1` 856 passed, 26 skipped, 2 deselected, 1 xfailed, 2 errors; hermeticity 859; netguard 2 / 2
   - `[pyt] tag=st1pr2-comm-head-04 start=2026-10-23 14:06:19 end=2026-10-23 14:08:41 elapsed=142s bound=1200s status=OK rc=0` 2560 passed; hermeticity 2560; netguard 0 / 0
   - `[pyt] tag=st1pr2-comm-head-05 start=2026-10-23 14:08:43 end=2026-10-23 14:09:32 elapsed=49s bound=1200s status=OK rc=0` 695 passed, 2 skipped, 16 deselected; hermeticity 696; netguard 85 / 29
   - `[pyt] tag=st1pr2-comm-head-06 start=2026-10-23 14:09:34 end=2026-10-23 14:10:05 elapsed=31s bound=1200s status=OK rc=0` 883 passed, 9 skipped, 35 xfailed; hermeticity 927; netguard 0 / 0
   Base (detached scratch worktree `<notes>/base_wt` at dfc6502f, added 14:10, no node_modules, no .env, no junction, `git status --short` empty before removal; removed 14:22 with `git worktree remove --force`, absent from `git worktree list`, directory gone):
   - `[pyt] tag=st1pr2-comm-base-00 start=2026-10-23 14:10:46 end=2026-10-23 14:11:26 elapsed=40s bound=1200s status=OK rc=0` 1276 passed, 1 deselected; hermeticity 1276; netguard 18 / 6
   - `[pyt] tag=st1pr2-comm-base-01 start=2026-10-23 14:11:28 end=2026-10-23 14:12:14 elapsed=45s bound=1200s status=OK rc=0` 933 passed; hermeticity 933; netguard 35 / 13
   - `[pyt] tag=st1pr2-comm-base-02 start=2026-10-23 14:12:16 end=2026-10-23 14:13:55 elapsed=99s bound=1200s status=OK rc=0` 659 passed, 4 deselected; hermeticity 659; netguard 24 / 23
   - `[pyt] tag=st1pr2-comm-base-03 start=2026-10-23 14:14:09 end=2026-10-23 14:14:47 elapsed=38s bound=1200s status=FAIL rc=1` 856 passed, 26 skipped, 2 deselected, 1 xfailed, 2 errors; hermeticity 859; netguard 2 / 2
   - `[pyt] tag=st1pr2-comm-base-04 start=2026-10-23 14:14:49 end=2026-10-23 14:18:19 elapsed=210s bound=1200s status=OK rc=0` 2560 passed; hermeticity 2560; netguard 0 / 0
   - `[pyt] tag=st1pr2-comm-base-05 start=2026-10-23 14:18:21 end=2026-10-23 14:19:11 elapsed=50s bound=1200s status=OK rc=0` 695 passed, 2 skipped, 16 deselected; hermeticity 696; netguard 85 / 29
   - `[pyt] tag=st1pr2-comm-base-06 start=2026-10-23 14:19:14 end=2026-10-23 14:19:40 elapsed=26s bound=1200s status=OK rc=0` 883 passed, 9 skipped, 35 xfailed; hermeticity 927; netguard 0 / 0
   FAILED/ERROR node-id sets: HEAD = base = {tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable} (the cold-tiktoken pair, identical both sides); no tests/.pre_impl_failures.txt node in either set. `comm -13` EMPTY; `comm -23` EMPTY. Netguard counts identical per chunk on both sides (the previous step's chunk-01 timing difference did not recur). 7,862 passed per side.
9. Hook files (the unit touches no `.githooks` file: `git diff --name-only origin/main HEAD -- .githooks` empty; `git diff --stat d19360c5 HEAD -- .githooks tests/test_precommit_hook*.py .gitleaks.toml scripts/setup_hooks.sh` empty, so the hook and its tests are byte-identical to the previous step's run): the four files ALONE, `-k "not dash"` (167 selected / 160 deselected of 327), launched 14:22 in the foreground (the Bash tool moved the call to the background at its 600 s cap; it stayed my only pytest process and nothing else ran until it ended):
   - `[pyt] tag=st1pr2-hook-notdash start=2026-10-23 14:22:53 end=2026-10-23 14:53:03 elapsed=1810s bound=1800s status=TIMEOUT rc=124` (the [pyt] lines are in hook_notdash.out; the log holds the pytest stream): 29 nodes ran, 21 passed, 8 failed (progress `................FFFFF.....FFF`), about 62 s per node; no pytest summary (killed by the bound). Collection order (`[pyt] tag=st1pr2-hook-collect start=2026-10-23 15:02:04 end=2026-10-23 15:02:21 elapsed=17s bound=600s status=OK rc=0`, `--collect-only`, 167/327 collected) maps the failures to positions 17-21 and 27-29, all in tests/test_precommit_hook.py::TestPreCommitHook::test_scenario: [sh-red_skill_md_without_description_refused], [sh-red_failing_run_on_nested_path_leaves_nothing_behind], [sh-red_staged_ok_with_broken_working_copy_passes], [sh-red_path_with_space_passes], [sh-red_non_ascii_path_passes], [sh-pin_musk_slug_passes], [sh-pin_clean_change_passes], [sh-pin_credurl_11_char_password_on_test_host_passes] (hook_failed_nodes.txt).
   - Diagnostic, two of them alone with `-v -rf`: `[pyt] tag=st1pr2-hook-failed2 start=2026-10-23 15:03:25 end=2026-10-23 15:05:52 elapsed=147s bound=600s status=FAIL rc=1`: [sh-pin_clean_change_passes] hit pytest-timeout's `--timeout=120` (`+++ Timeout +++` dump; stack in run_hook -> subprocess.run(..., timeout=90) -> communicate, i.e. waiting for the hook process), which ended the pytest process (no summary; [sh-red_path_with_space_passes] did not run). Not an AssertionError.
   - Box: `node -e 0` 2.58 s at 13:52 and 9.30 s at 15:07 (slow-spawn state; one python.exe = the orchestrator's stall_monitor.py besides my runs). The previous step ran the same first 51 nodes on byte-identical files at 13:04-13:34 with 0 failures.
   - The once-alone re-run and the `-k dash` half (160 nodes) were NOT run: at about 62 s per node neither can complete inside 1800 s, and either would end past the 2-hour budget (15:43).
   - After the TIMEOUT: no orphan (Win32_Process python.exe list = stall_monitor.py only, 15:01).

## NOT MEASURED

- The pre-commit hook test files: `-k "not dash"` TIMEOUT once (21 passed / 8 failed of the 29 nodes reached; one [pyt] line above); one failure diagnosed as a per-test Timeout (environmental), the other seven failure reasons NOT captured (unclassified; environmental by the evidence above, not proven node by node); the once-alone re-run not run; `-k dash` not run: both halves NOT MEASURED. The unit edits no .githooks file and no hook-test input.
- The full-file ON state in CI terms beyond the rows that set the flag (by design: the autouse fixture; limit 13).
- The comm set with the flag exported (only the 28-file pin set was measured ON).
- Mutants: none this step (no row added; the task's PIN ROWS item is NONE).
- Production / Railway / Supabase / providers: never touched; no .env read, copied or printed; flags set only in the environment of single runner calls.

## Deviations

- None in the file set (only the five named files differ from origin/main).
- Task premise corrected: tests/test_s81_s03_llm_ledger_v2.py is NOT free of ST1 modules: it imports `usage_service` (line 71) and patches `consume_comparison_credit` on it, so the builder's rule selects it (163 members, not 162).
- The comm chunk runner run_chunk_pr2.py was made from the previous step's run_chunk_pr.py with `cp` plus a one-token `sed -i` tag rename (st1pr- -> st1pr2-), not with the Write/Edit tool; the edited line was checked with grep (notes-folder script only, ASCII).
- Extra gate beyond the list: the metering file with ENABLE_PAID_ROUTE_METERING exported (as the previous step).
- Extra gates beyond the list: the 28-file pin set with the flag exported (to re-measure limit 13 at the new HEAD), the hook collect-only and the two-node hook diagnostic.
- Hook gate: the TIMEOUT re-run and the dash half were not run (budget; reason above). The hook-gate runner call was moved to the background by the Bash tool's 600 s cap (not by me); it remained one process and no other pytest ran until it ended. My first wait loop polled the log instead of the runner's stdout file for the [pyt] line, which cost about 6 minutes of idle wall time (14:53-14:59).
- The 8-digit run `91691999` in the PR body and this report is the hex short sha of the replayed fix commit, not a personal value; the other 8+-digit run is inside the RED file's sha256 digest.

## Final state

- sc-s81-st1: HEAD `8e663581cc1890b4ea9e9300200f176c2e1312f4` on `feature/s81-st1-usage-path-offloop`, `git status --short` EMPTY (verified 15:12), no `.qa-mutation.lock`, not pushed.
- Base scratch worktree removed (absent from `git worktree list`, directory gone). No pytest of mine alive at 15:12; the two pyt.py processes on the box then (tag s05e-comm-c12, cwd scratchpad/S81-05_adv_engineering) belong to a sibling agent and were left alone (they also explain the box load).
- PR body: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/ST1_pr2/PR_BODY.md` (pure ASCII, no generation trailer: the orchestrator appends it).
- Git writes made (all inside the task's exception, in this worktree only): `git fetch origin main`, `git rebase origin/main`, `git add CLAUDE.md` + `GIT_EDITOR=true git rebase --continue` twice (the third replay auto-merged); no `git commit` (no pin rows); plus the brief's allowed detached scratch worktree add / remove; one `git merge-tree --write-tree` dry run before the rebase (a tree object, no ref).
