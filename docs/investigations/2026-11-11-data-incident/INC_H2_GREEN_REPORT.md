# INC-H2 GREEN REPORT (GREEN agent, Opus 5.5, 2026-11-17)

Unit: INC-H2 STORED-ROW GUARDS (part A unflagged; part B ENABLE_SMART_PICK_BHD_ONLY default OFF) + INC-T0 CONFTEST-BREAKER-RESET (H2R-14).
Worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-h2, branch fix/inc-h2-smart-pick-guard (already existed at 7f672cfe; no checkout -b run).
Base = main 7f672cfef1445233b58c323a08515baec7aae4bd (#418 merge). HEAD = 623993126836d75979d70ed6ed71c83c134e6974 (one commit, hook passed). Not pushed, no PR.
RED file re-hash first and last: tests/test_inc_h2_smart_pick_guard.py e0bbb9958a493d4a2a02d20293a65c425df720485e5d263a670cb30dd92371c1 (also the committed blob bytes) = OK.
Byte copies before edit: <SP>/INC-H2_green_before/ (SHA256.tsv).

## Files (git show --numstat HEAD)
| file | + | - | sha256 before | sha256 after |
|---|---|---|---|---|
| app/api/home_routes.py | 25 | 0 | 5d59f74d5c52a9a136a56636044a7487a9c54b8e1fcba20e5dfc972d762fbfca | 688e07e293ee7a81230686efad880579b07da3a50c1b208384c902711b683f21 |
| tests/conftest.py | 18 | 0 | e8ca16ee9c9dc8a01bf3b09579ce3802ec4fb15f34dd984d5d2c84e987ac9db4 | 8af68629e9567e9252ac4e9fc5bd28a6a7f8322fbd5d1ada0d3e389fbf4e77e3 |
| CLAUDE.md | 7 | 1 | 30e2dc337d79140feec84dbc7004a909c81ec8d931d3d3c8dd3a085376021f17 | 2c4b8fd71864ba1f3bac1ece794a1cf95d6a057a1d11b35bd5b898f6c8d99259 |
| tests/test_inc_h2_smart_pick_guard.py (frozen RED, new) | 465 | 0 | e0bbb995... | e0bbb9958a493d4a2a02d20293a65c425df720485e5d263a670cb30dd92371c1 |
| tests/test_inc_t0_conftest_breaker_reset.py (new) | 63 | 0 | - | a7e25335744f4b8ceb4631e7bb42382ed4447f5a92abda6e3718ab4d01744586 |
Working copies: home_routes.py / conftest.py / CLAUDE.md keep CRLF; the two new test files LF; added lines 0 bytes > 127.

## Code
- home_routes.smart_pick_bhd_only_enabled(): os.environ.get("ENABLE_SMART_PICK_BHD_ONLY", "").strip().lower() in ("1","true","yes","on") (the caption reader's shape, H2R-4 / H2R-11).
- home_routes._smart_pick_not_bhd_pair(winner, loser): FIRST statement `if not smart_pick_bhd_only_enabled(): return False`; then (winner.get("price") or {}).get("currency") != "BHD" or (loser...) != "BHD" (the :210 rule, no normalisation). H2R-10: the flag is read as the predicate's first statement (per call, per candidate row reaching the amount test), not once before the loop.
- _select_smart_pick: `if _pair_price_sizes_differ(full): continue` right after the _result_status_supported skip (module-global call, A6); `if _smart_pick_not_bhd_pair(winner, loser): continue` right after the amount test.
- tests/conftest.py::_reset_llm_process_latches (autouse): yield, then import-guarded llm_spend_breaker._reset_spend_breaker_state() and llm_router._reset_router_state().
- CLAUDE.md: the Feature Flags pointer sentence after the ENABLE_PRICE_NOT_LOST pointer; the unit block "INCIDENT LANE unit (INC-H2 STORED-ROW GUARDS + INC-T0 ...)" placed immediately before ## Tests (after the INC-U1 block, which follows the INC-P2 block: merge order).

## Runs (BOX_GO present 10:25:23; every pytest via harness/pyt.py with [pyt] tag=inc-h2-green-t0-base start=2026-11-17 10:25:35 end=2026-11-17 10:25:40 elapsed=5s bound=600s status=FAIL rc=1  (before the conftest edit: 2 failed (T0-1b, T0-2b, AssertionError only), 2 passed; hermeticity 4; netguard 0)
[pyt] tag=inc-h2-green-unit-off start=2026-11-17 10:25:58 end=2026-11-17 10:26:02 elapsed=4s bound=600s status=OK rc=0  (105 passed; hermeticity 105; netguard 0)
[pyt] tag=inc-h2-green-unit-on start=2026-11-17 10:26:03 end=2026-11-17 10:26:07 elapsed=4s bound=600s status=OK rc=0  (ENABLE_SMART_PICK_BHD_ONLY=true; 105 passed; hermeticity 105; netguard 0)
[pyt] tag=inc-h2-green-pins start=2026-11-17 10:26:14 end=2026-11-17 10:26:58 elapsed=44s bound=600s status=FAIL rc=1  (15 files; 1 failed = the base node test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content, 1821 passed; netguard blocked 13 sentinel attempts)
[pyt] tag=inc-h2-green-c01 start=2026-11-17 10:27:41 end=2026-11-17 10:28:15 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c02 start=2026-11-17 10:28:16 end=2026-11-17 10:29:00 elapsed=44s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c03 start=2026-11-17 10:29:01 end=2026-11-17 10:31:19 elapsed=138s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c04 start=2026-11-17 10:31:20 end=2026-11-17 10:31:51 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c05 start=2026-11-17 10:31:51 end=2026-11-17 10:33:18 elapsed=87s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c06 start=2026-11-17 10:33:19 end=2026-11-17 10:35:08 elapsed=109s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c07 start=2026-11-17 10:35:09 end=2026-11-17 10:37:27 elapsed=137s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c08 start=2026-11-17 10:37:27 end=2026-11-17 10:38:16 elapsed=49s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c09 start=2026-11-17 10:38:17 end=2026-11-17 10:39:18 elapsed=61s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c10 start=2026-11-17 10:39:19 end=2026-11-17 10:39:31 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-tree start=2026-11-17 10:39:32 end=2026-11-17 10:56:51 elapsed=1039s bound=1800s status=FAIL rc=1  (whole tests/ tree, ONE alphabetical process: 21 failed, 31928 passed, 56 skipped, 124 deselected, 39 xfailed, 2 errors in 1030.77s)
[pyt] tag=inc-h2-green-e27-rerun start=2026-11-17 10:57:43 end=2026-11-17 10:58:17 elapsed=34s bound=600s status=OK rc=0  (tests/test_inc_i2a_picture_not_cut.py alone at HEAD: 67 passed)
[jest] tag=inc-h2-green-fences start=2026-11-17 10:56:52 end=2026-11-17 10:56:58 rc=1  (jest 29.7.0; 15 suites / 250 tests: 4 failed = the accepted config/nativeBundle.w37 drift nodes d5 / k2 / k4 / k5, 246 passed)_VIA_GATE=1)
```
[pyt] tag=inc-h2-green-t0-base start=2026-11-17 10:25:35 end=2026-11-17 10:25:40 elapsed=5s bound=600s status=FAIL rc=1  (before the conftest edit: 2 failed (T0-1b, T0-2b, AssertionError only), 2 passed; hermeticity 4; netguard 0)
[pyt] tag=inc-h2-green-unit-off start=2026-11-17 10:25:58 end=2026-11-17 10:26:02 elapsed=4s bound=600s status=OK rc=0  (105 passed; hermeticity 105; netguard 0)
[pyt] tag=inc-h2-green-unit-on start=2026-11-17 10:26:03 end=2026-11-17 10:26:07 elapsed=4s bound=600s status=OK rc=0  (ENABLE_SMART_PICK_BHD_ONLY=true; 105 passed; hermeticity 105; netguard 0)
[pyt] tag=inc-h2-green-pins start=2026-11-17 10:26:14 end=2026-11-17 10:26:58 elapsed=44s bound=600s status=FAIL rc=1  (15 files; 1 failed = the base node test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content, 1821 passed; netguard blocked 13 sentinel attempts)
[pyt] tag=inc-h2-green-c01 start=2026-11-17 10:27:41 end=2026-11-17 10:28:15 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c02 start=2026-11-17 10:28:16 end=2026-11-17 10:29:00 elapsed=44s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c03 start=2026-11-17 10:29:01 end=2026-11-17 10:31:19 elapsed=138s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c04 start=2026-11-17 10:31:20 end=2026-11-17 10:31:51 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c05 start=2026-11-17 10:31:51 end=2026-11-17 10:33:18 elapsed=87s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c06 start=2026-11-17 10:33:19 end=2026-11-17 10:35:08 elapsed=109s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c07 start=2026-11-17 10:35:09 end=2026-11-17 10:37:27 elapsed=137s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c08 start=2026-11-17 10:37:27 end=2026-11-17 10:38:16 elapsed=49s bound=1200s status=FAIL rc=1
[pyt] tag=inc-h2-green-c09 start=2026-11-17 10:38:17 end=2026-11-17 10:39:18 elapsed=61s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-c10 start=2026-11-17 10:39:19 end=2026-11-17 10:39:31 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=inc-h2-green-tree start=2026-11-17 10:39:32 end=2026-11-17 10:56:51 elapsed=1039s bound=1800s status=FAIL rc=1  (whole tests/ tree, ONE alphabetical process: 21 failed, 31928 passed, 56 skipped, 124 deselected, 39 xfailed, 2 errors in 1030.77s)
[pyt] tag=inc-h2-green-e27-rerun start=2026-11-17 10:57:43 end=2026-11-17 10:58:17 elapsed=34s bound=600s status=OK rc=0  (tests/test_inc_i2a_picture_not_cut.py alone at HEAD: 67 passed)
[jest] tag=inc-h2-green-fences start=2026-11-17 10:56:52 end=2026-11-17 10:56:58 rc=1  (jest 29.7.0; 15 suites / 250 tests: 4 failed = the accepted config/nativeBundle.w37 drift nodes d5 / k2 / k4 / k5, 246 passed)
```
- INC-T0 RED-first: before the conftest edit the T0 file gave 2 failed / 2 passed, both failures AssertionError (T0-1: ['llm_spend', 'llm_spend_fail_open', 'llm_spend_late_records'] leaked; T0-2: anthropic_breaker leaked). After the edit: green in unit-off / unit-on.
- Unit: 105/105 flag OFF and 105/105 flag ON (the H2 file sets / deletes the flag per row; both ambient states measured).
- Identity pins (the spec has no section 4.2; used the home_routes / smart_pick reference set + the INC-P2 trio, 15 files, <SP>/INC-H2_green/identity_pins.txt): 1821 passed, 1 failed = the recorded base node test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content.
- ruff (repo blocking tier E9,F63,F7,F82) clean on home_routes.py, conftest.py, both test files; py_compile clean. The full default ruff ruleset reports 4 pre-existing findings in home_routes.py (F401 HTTPException, 3x B008 Depends) on base lines, none on added lines.

## Comm set
- List: <SP>/INC-H2_green/comm_list.txt (234 files), reasons comm_reasons.tsv, builder build_comm.py. Union: the RED list (195, all retained) + re-derived greps at HEAD (home_routes / smart_pick / _smart_pick_not_bhd_pair refs, CLAUDE.md readers, source scanners, app path readers, black-clean readers) + /health readers (GATE 4) + latch users (llm_spend_breaker / llm_router / the reset helpers) + conftest readers + the named pins (incl. the CLAUDE.md readers by import graph) + the INC-P2 trio + the two unit files; EXCLUDED tests/test_precommit_hook.py, tests/test_precommit_hook_phase_b.py.
- 10 chunks (<= 25 files, bound 1200), one at a time. HEAD failures (22 ids):
  - tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
  - tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
  - tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
  - tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
  - tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
  - tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
  - tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
  - tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
  - tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
  - tests/test_s81_s07_meas_harness.py::test_r35_fixtures
  - tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
  - tests/test_s81_s18b_store_label.py::test_r2_table_shape
  - tests/test_s81_s19_gap_queue.py::test_r15_hygiene
  - tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
  - tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
  - tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene
  - tests/test_s81_s24_auth_throttle.py::test_r92_hygiene
- Base record = the RED report's 23 nodes (comm_reused_failed.txt, at 8bb97fe0). branch-only-NEW (HEAD minus base) = EMPTY. Base-only: test_retro_w0_4.py::test_cpu_bound_parse_keeps_the_max_loop_gap_bounded_under_flag[scs._fetch_page_price] (timing node, passed at HEAD).
- Whole tests/ tree in ONE alphabetical process (GATE 4; the CI-order set of this unit; --ignore tests/test_integration.py + the four test_precommit_hook*.py; the 8 .pre_impl_failures.txt nodes deselected; bound 1800): 21 failed + 2 errors = the 22 base ids above + tests/test_inc_i2a_picture_not_cut.py::test_e27_elapsed_includes_the_wait (AssertionError (0.41, 0.421): elapsed_seconds rounded to 2 decimals vs the bind wait in ms). Classified BASE FLAKE: on the identical base tree (629b21ca^{tree} == 7f672cfe^{tree} == 95b2556c) it failed 2/2 standalone in INC-P2's m3 round (inc-p2-m3-e27-1 / -2, (0.42, 0.421)); at HEAD it passed in comm chunk and in the standalone re-run (inc-h2-green-e27-rerun, 67 passed). No conftest-reset interaction: the node touches neither latch.
- Client fences (the fourteen, 15 suites, by path, jest 29.7.0, the probe empty before start): 4 failed = config/nativeBundle.w37 d5 / k2 / k4 / k5 (the accepted drift nodes; identical to INC-P2 rb2), 246 passed.

## Deviations
- D1 commit trailer "Co-Authored-By: Claude Opus 5.5" (GATE_INC_H2 section 4 + common brief H12 (a) + the agent's real model) instead of the prompt's "Claude Fable 5.1".
- D2 the CLAUDE.md unit block sits after the INC-U1 block (the newest, directly before ## Tests), not directly after the INC-P2 block: INC-U1 (#417) merged after the spec was written and blocks union in merge order.
- D3 the spec has no section 4.2 nor 8.1: identity pins = the home_routes reference set + INC-P2 trio; the CLAUDE.md row = the Feature Flags pointer + the unit block (house format, names only).
- D4 INC-T0 file holds two paired rows as four test functions (setter 1a / 2a, reader 1b / 2b); the setters are green at base, the readers RED. A reader run alone is vacuous (stated in its docstring).
- D5 the CI-order set is the whole tree in one process (GATE 4 wins over the prompt's 1200 s CI-order set), bound 1800 (the ceiling); it ran 1039 s.
- D6 branch-only-NEW is computed against the RED base record (8bb97fe0), not a fresh 7f672cfe record: every HEAD comm failure is in that record, so the moved base (93c6da3a P2R-39 + #417) adds no question; the one tree-only id is classified by the m3 measurements on the identical tree.
- D7 R0 rulings path: <SP>/INC-H2_RED_REPORT.md is byte-identical to <SP>/INC-H2/red/INC-H2_RED_REPORT.md.

## Open questions for the gate
- Q1 add tests/test_inc_t0_conftest_breaker_reset.py to .github/black-clean-paths.txt like the other inc test files? Not done (not in the change list).
- Q2 the e27 rounding flake of test_inc_i2a_picture_not_cut.py (one-process run) belongs to the I2a owner (S96 main lane); not touched here.

## git status --short (worktree, after commit)
(empty)

PR body draft: <SP>/INC-H2_green/PR_BODY.md (11,129 bytes; ends with the Generated-with line).
Hermetic measurement only; not the production proof (the owner's phone is).
