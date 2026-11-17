# INC-H2 RED REPORT (RED agent, Opus 5.5, 2026-11-17)

Unit: INC-H2 STORED-ROW GUARDS (part A unflagged; part B ENABLE_SMART_PICK_BHD_ONLY, default OFF).
Base: 8bb97fe0edd692445f18580491f4aa54e3a6d501 (PR #418 head); real worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-h2 (detached; clean before and after except the new file).
Notes: C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-H2\red\notes.md

## Test file
- tests/test_inc_h2_smart_pick_guard.py sha256 e0bbb9958a493d4a2a02d20293a65c425df720485e5d263a670cb30dd92371c1, 20190 bytes, 0 bytes > 127, 0 CR; py_compile and ruff E9/F63/F7/F82 clean.
- 101 nodes. RED 66: A1 x2, A2 x2, A5 x6, A6 x1, B0 x13, B1 x30, B4 x6, B5 x1, B6 x1, R1 x2, R1b x1, R1c x1. PIN 35: A3 x2, A4 x6, B2 x18, B3 x5, R2 x4.
- Reader name pinned: home_routes.smart_pick_bhd_only_enabled (H2R-4 caption-reader shape: os.environ.get(NAME, '').strip().lower() in ('1', 'true', 'yes', 'on')).

## Step 2 (review not-measured files)
- none listed (no review: SMALL, H2R-1). Nothing run.

## [pyt] lines (unit file at base, prototype OFF / ON, fresh comm chunk)
- [pyt] tag=inc-h2-red-base start=2026-11-17 09:25:22 end=2026-11-17 09:25:27 elapsed=5s bound=600s status=FAIL rc=1  (66 failed, 35 passed; [hermeticity] sentinel checked 101 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
- [pyt] tag=inc-h2-red-proto-off start=2026-11-17 09:25:59 end=2026-11-17 09:26:03 elapsed=4s bound=600s status=OK rc=0  (101 passed; hermeticity 101; netguard 0)
- [pyt] tag=inc-h2-red-proto-on start=2026-11-17 09:26:10 end=2026-11-17 09:26:13 elapsed=4s bound=600s status=OK rc=0  (101 passed; hermeticity 101; netguard 0)
- [pyt] tag=inc-h2-red-comm-c01 start=2026-11-17 09:29:33 end=2026-11-17 09:29:45 elapsed=11s bound=1200s status=OK rc=0  (62 passed, 1 skipped, 9 deselected; hermeticity 63; netguard 0)

Base: 66 failed / 35 passed; the log holds 66 'E AssertionError' lines and no other exception class (C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-H2\red\base_unit.log). Every RED row fails on an AssertionError only; every PIN row is green.

## Prototype (scratch worktree, thrown away; C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-H2\red\proto.py)
- smart_pick_bhd_only_enabled() and _smart_pick_non_bhd(winner, loser) (the flag first, then currency != 'BHD' on either side, no normalisation); `if _pair_price_sizes_differ(full): continue` right after the status skip; `if _smart_pick_non_bhd(winner, loser): continue` after the amount test.
- Ambient OFF and ON runs: 101 passed each (every row sets or deletes the flag itself; the autouse fixture wipes the ambient value, which the two runs show).

## Mutation table (each on a byte copy of the prototype; restored and sha-verified after each)
| mutant | result | failing nodes | killing rows | summary | [pyt] |
|---|---|---|---|---|---|
| M01_drop_A | KILLED | 14 | test_a1_stamped_row_alone_is_no_pick, test_a2_older_unstamped_row_is_picked, test_a5_marker_skip_holds_under_every_flag, test_a6_marker_read_right_after_the_status_skip, test_r1_route_skips_the_stamped_row, test_r1b_route_stamped_only_is_empty_state | 14 failed, 87 passed, 15 warnings in 3.57s | [pyt] tag=inc-h2-red-m01-drop-a start=2026-11-17 09:26:41 end=2026-11-17 09:26:46 elapsed=4s bound=600s status=FAIL rc=1 |
| M02_invert_mode | KILLED | 58 | test_a1_stamped_row_alone_is_no_pick, test_a2_older_unstamped_row_is_picked, test_a3_same_size_stamp_picked_as_today, test_a4_malformed_marker_picked_as_today, test_a5_marker_skip_holds_under_every_flag, test_a6_marker_read_right_after_the_status_skip, test_b2_flag_off_picked_as_today, test_b3_flag_on_bhd_pair_picked_as_today, test_b4_flag_on_older_bhd_row_is_picked, test_b5_flag_read_per_call, test_b6_flag_on_reads_both_currencies, test_r1_route_skips_the_stamped_row, test_r1b_route_stamped_only_is_empty_state, test_r1c_route_flag_on_skips_the_usd_row, test_r2_route_flag_off_byte_identical | 58 failed, 43 passed, 15 warnings in 3.95s | [pyt] tag=inc-h2-red-m02-invert-mode start=2026-11-17 09:26:53 end=2026-11-17 09:26:57 elapsed=5s bound=600s status=FAIL rc=1 |
| M03_flag_at_import | KILLED | 39 | test_b1_flag_on_skips_a_non_bhd_pair, test_b4_flag_on_older_bhd_row_is_picked, test_b5_flag_read_per_call, test_b6_flag_on_reads_both_currencies, test_r1c_route_flag_on_skips_the_usd_row | 39 failed, 62 passed, 15 warnings in 3.78s | [pyt] tag=inc-h2-red-m03-flag-at-import start=2026-11-17 09:27:04 end=2026-11-17 09:27:08 elapsed=4s bound=600s status=FAIL rc=1 |
| M03b_flag_once_per_call_before_loop | SURVIVED | 0 | - | 101 passed, 15 warnings in 2.81s | [pyt] tag=inc-h2-red-m03b-flag-once-per-call-before-loop start=2026-11-17 09:27:15 end=2026-11-17 09:27:19 elapsed=4s bound=600s status=OK rc=0 |
| M04_or_instead_of_and | KILLED | 39 | test_b1_flag_on_skips_a_non_bhd_pair, test_b4_flag_on_older_bhd_row_is_picked, test_b5_flag_read_per_call, test_b6_flag_on_reads_both_currencies, test_r1c_route_flag_on_skips_the_usd_row | 39 failed, 62 passed, 15 warnings in 3.80s | [pyt] tag=inc-h2-red-m04-or-instead-of-and start=2026-11-17 09:27:26 end=2026-11-17 09:27:30 elapsed=4s bound=600s status=FAIL rc=1 |
| M05_casefold_currency | KILLED | 12 | test_b1_flag_on_skips_a_non_bhd_pair, test_b4_flag_on_older_bhd_row_is_picked | 12 failed, 89 passed, 15 warnings in 3.55s | [pyt] tag=inc-h2-red-m05-casefold-currency start=2026-11-17 09:27:37 end=2026-11-17 09:27:41 elapsed=4s bound=600s status=FAIL rc=1 |
| M06_marker_before_status | KILLED | 1 | test_a6_marker_read_right_after_the_status_skip | 1 failed, 100 passed, 15 warnings in 3.47s | [pyt] tag=inc-h2-red-m06-marker-before-status start=2026-11-17 09:27:48 end=2026-11-17 09:27:52 elapsed=4s bound=600s status=FAIL rc=1 |
| M07_default_on | KILLED | 10 | test_b0_reader_exists_and_parses_like_the_caption_reader, test_b2_flag_off_picked_as_today, test_b5_flag_read_per_call, test_r2_route_flag_off_byte_identical | 10 failed, 91 passed, 15 warnings in 3.51s | [pyt] tag=inc-h2-red-m07-default-on start=2026-11-17 09:27:59 end=2026-11-17 09:28:03 elapsed=4s bound=600s status=FAIL rc=1 |
| M08_missing_currency_passes | KILLED | 6 | test_b1_flag_on_skips_a_non_bhd_pair, test_b4_flag_on_older_bhd_row_is_picked | 6 failed, 95 passed, 15 warnings in 3.48s | [pyt] tag=inc-h2-red-m08-missing-currency-passes start=2026-11-17 09:28:10 end=2026-11-17 09:28:14 elapsed=4s bound=600s status=FAIL rc=1 |
| M09_currency_read_before_flag | KILLED | 22 | test_b2_flag_off_picked_as_today, test_r2_route_flag_off_byte_identical | 22 failed, 79 passed, 15 warnings in 3.63s | [pyt] tag=inc-h2-red-m09-currency-read-before-flag start=2026-11-17 09:28:21 end=2026-11-17 09:28:25 elapsed=4s bound=600s status=FAIL rc=1 |
| M10_A_behind_bhd_flag | KILLED | 11 | test_a1_stamped_row_alone_is_no_pick, test_a2_older_unstamped_row_is_picked, test_a5_marker_skip_holds_under_every_flag, test_a6_marker_read_right_after_the_status_skip, test_r1_route_skips_the_stamped_row, test_r1b_route_stamped_only_is_empty_state | 11 failed, 90 passed, 15 warnings in 3.52s | [pyt] tag=inc-h2-red-m10-a-behind-bhd-flag start=2026-11-17 09:28:32 end=2026-11-17 09:28:36 elapsed=4s bound=600s status=FAIL rc=1 |
| M11_A_behind_price_not_lost | KILLED | 11 | test_a1_stamped_row_alone_is_no_pick, test_a2_older_unstamped_row_is_picked, test_a5_marker_skip_holds_under_every_flag, test_a6_marker_read_right_after_the_status_skip, test_r1_route_skips_the_stamped_row, test_r1b_route_stamped_only_is_empty_state | 11 failed, 90 passed, 15 warnings in 3.64s | [pyt] tag=inc-h2-red-m11-a-behind-price-not-lost start=2026-11-17 09:28:43 end=2026-11-17 09:28:47 elapsed=4s bound=600s status=FAIL rc=1 |
| M12_reader_no_strip | KILLED | 8 | test_b0_reader_exists_and_parses_like_the_caption_reader, test_b1_flag_on_skips_a_non_bhd_pair | 8 failed, 93 passed, 15 warnings in 3.53s | [pyt] tag=inc-h2-red-m12-reader-no-strip start=2026-11-17 09:28:54 end=2026-11-17 09:28:58 elapsed=4s bound=600s status=FAIL rc=1 |
| M13_drop_B | KILLED | 39 | test_b1_flag_on_skips_a_non_bhd_pair, test_b4_flag_on_older_bhd_row_is_picked, test_b5_flag_read_per_call, test_b6_flag_on_reads_both_currencies, test_r1c_route_flag_on_skips_the_usd_row | 39 failed, 62 passed, 15 warnings in 3.88s | [pyt] tag=inc-h2-red-m13-drop-b start=2026-11-17 09:29:05 end=2026-11-17 09:29:10 elapsed=5s bound=600s status=FAIL rc=1 |

Killed 13 of 14. SURVIVOR M03b (flag read once per _select_smart_pick call, before the loop, instead of inside the predicate): behaviourally equivalent (still per call; still no currency read when OFF); proposed EQUIVALENT for a ruling. The spec's 'read the flag outside the predicate' is also represented by M03 (captured at import), KILLED.
Spec mutants: drop A = M01; invert the mode test = M02; flag outside the predicate = M03 (+ M03b); OR instead of AND = M04; casefold = M05; order (marker before status) = M06; default-ON = M07; missing-currency pass = M08. Extra: M09 currency read before the flag test, M10 / M11 part A wrongly flagged (behind the H2 flag / behind ENABLE_PRICE_NOT_LOST), M12 reader without strip, M13 drop B.

## Comm set (base, real worktree)
- list: C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-H2\red\comm_list.txt (195 files); per-file reasons: C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-H2\red\comm_reasons.tsv
- union: the reference grep (home_routes, _select_smart_pick, smart_pick, smart-pick, _pair_price_sizes_differ, _result_status_supported, ENABLE_SMART_PICK: 12 files); the CLAUDE.md readers (grep + import graph); the source scanners (rglob / os.walk / listdir / scandir / getsource / ast.parse / glob); the app path readers; the named pins; the black-clean readers; the INC-P2 trio. EXCLUDED: tests/test_precommit_hook.py, tests/test_precommit_hook_phase_b.py (the only precommit files the union hit). app/api/home_routes.py is not in .github/black-clean-paths.txt.
- REUSED (H2R-7): 191 files from <SP>/INC-P2_rb2/comm/inc-p2-rb2-c01..c31.xml, measured at the SAME sha 8bb97fe0 (rb2 head_start = head_end = 8bb97fe0, status_end empty), so their bytes are identical. Reused list: C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-H2\red\comm_reused.txt; their [pyt] lines: <SP>/INC-P2_rb2/comm_pyt_lines.txt.
- RUN FRESH: 6 files (C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-H2\red\comm_torun.txt): 4 absent from rb2 (test_migration_042_search_logs_is_synthetic, test_regression_gate_diff, test_skill_frontmatter, test_sqlfluff_config) and 2 with zero cases in the rb2 XML (test_cohort_personalization_load, test_sse_settle_window): 0 failed (the comm-c01 line above).
- Base failures in the comm set (23 nodes, all from the reused XMLs; the spec has no section 1.10, so this is the recorded base list):
  - tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
  - tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
  - tests/test_retro_w0_4.py::test_cpu_bound_parse_keeps_the_max_loop_gap_bounded_under_flag[scs._fetch_page_price]
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
- Client fences (spec: 'the fourteen client fences once, by path'): NOT RUN in RED (no client change, base bytes unchanged; the RED procedure unions SmartCompareApp scanners only for a client-visible change). DEFERRED TO GREEN.

## Restore check
- real worktree HEAD 8bb97fe0; `git status --porcelain --untracked-files=all` = only '?? tests/test_inc_h2_smart_pick_guard.py'; `git diff --stat HEAD` empty; app/api/home_routes.py sha256 5d59f74d5c52a9a136a56636044a7487a9c54b8e1fcba20e5dfc972d762fbfca = the base copy.
- scratch worktree restored to base bytes, its mutation lock removed, `git worktree remove --force` done, absent from `git worktree list`; no inc-h2 pytest process alive.

## Deviations and notes for the gate
- D1: B2's 'flag-OFF body digests over 6 fixtures' is realised as frozen literal goldens compared by json.dumps byte identity (stronger than a digest; no 64-hex literal for the hygiene sweep); R2 also pins the cached Redis bytes, key and TTL.
- D2: rows beyond the spec list: A6 (status-then-marker order recorder: the only row that kills the order mutant, which is otherwise equivalent), B0 (reader exists + parse table), B5 (per-call read through a module spy), B6 (ON reads both currencies), R1b (route empty state for a stamped-only history), R1c (route, flag ON, USD newest). Each is RED at base on an AssertionError.
- D3: the reader NAME smart_pick_bhd_only_enabled is pinned by B0 / B5 (H2R-4 fixes only the shape); GREEN uses that name or the gate re-rules B0 / B5.
- D4: A6 requires `_pair_price_sizes_differ` to be called through the module global after `_result_status_supported` and never for a status-skipped row (the spec's 'right after the status skip').
- D5: the spec names no section 1.10 base-failure list; the 23 comm base failures above are the record.
- Open: the M03b equivalence ruling; the client fences deferred to GREEN.
- Hermetic measurement only: this is not the production proof (the owner's phone is).
