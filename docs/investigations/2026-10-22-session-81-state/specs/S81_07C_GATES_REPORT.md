# S81-07c CLAUDE-ROLE-FIX: GATES AND DOCS round report (gates agent, Opus 5.5; written through the shell)

VERDICT: READY_FOR_ADVERSARY. Mutants 18 / 18 KILLED (M01-M16 + GC-9 M17 / M18); comm set 365 members, branch-only-new EMPTY (HEAD and base failed sets identical, 24 nodes each); fences: 13 suites green + config/nativeBundle.w37 red on its four accepted drift nodes only (d5, k2, k4, k5); PR body 14,492 bytes.

- Unit S81-07c CLAUDE-ROLE-FIX; W = C:/Users/SynAckITPC/Documents/AI/sc-s81-s07c, branch feature/s81-07c-role-fix, HEAD 1da03aff3bbb784b5f83656158405260f5874b71 on base c6ebbd2ed593081cb6241915c36ae29af4c29bca; git status --short EMPTY at start (21:58) and at the end (see the last section). Nothing written in W; no commit, push, merge, rebase, checkout, restore, stash, reset or clean.
- Window: first tool call 21:57:18 (18:57:18Z), budget to 23:57. Notes folder: s07c/gates (notes.md kept from the first measurement).
- Read in full at the start and again before this report: s81-common.txt, GATE_S81_07C.md, S81_07C_UNIT_SPEC.md, red/S81_07C_RED_REPORT.md, red/E_ROWS.md, red/proto.diff, green/S81_07C_GREEN_REPORT.md (background: in/S94_FIRST_REPORT.md).
- RED file frozen: tests/test_s81_s07c_role_fix.py, the committed blob hashes to a197e2f2... (git show | sha256sum at 23:09); not edited; its 17 nodes passed at HEAD in comm chunk head-09 (17 dots).
- Every pytest went through harness/pyt.py with waitfree.ps1 -OwnTagPrefix s07c- before it (`free poll=0` each time) and a 20 s settle after; tags s07c-gates-mut-<id> and s07c-gates-comm-<side>-NN; no TIMEOUT, no DUPLICATE; no process killed.

## (1) Mutation table on the real code (scratch worktree <notes>/mut = detached 1da03aff; removed)

| id | file | edit | rows (-k) | [pyt] | failed nodes | result | restore |
|---|---|---|---|---|---|---|---|
| M01 | app/services/extraction_service.py | the block never appended | test_v02 | `[pyt] tag=s07c-gates-mut-M01 start=2026-11-12 22:05:26 end=2026-11-12 22:05:32 elapsed=6s bound=600s status=FAIL rc=1` | test_v02_block_bytes_index_0_and_1 | KILLED (AssertionError) | sha256 MATCH |
| M02 | app/services/extraction_service.py | label = index | test_v02 | `[pyt] tag=s07c-gates-mut-M02 start=2026-11-12 22:05:55 end=2026-11-12 22:06:01 elapsed=6s bound=600s status=FAIL rc=1` | test_v02_block_bytes_index_0_and_1 | KILLED (AssertionError) | sha256 MATCH |
| M03 | app/services/extraction_service.py | bool accepted (isinstance) | test_v05 | `[pyt] tag=s07c-gates-mut-M03 start=2026-11-12 22:06:23 end=2026-11-12 22:06:28 elapsed=5s bound=600s status=FAIL rc=1` | test_v05_invalid_values_are_byte_identical | KILLED (AssertionError) | sha256 MATCH |
| M04 | app/services/extraction_service.py | the block before the scores block (one region rewrite) | test_v04 | `[pyt] tag=s07c-gates-mut-M04 start=2026-11-12 22:06:51 end=2026-11-12 22:06:57 elapsed=6s bound=600s status=FAIL rc=1` | test_v04_placement_after_scores_before_preferences | KILLED (AssertionError) | sha256 MATCH |
| M05 | app/services/extraction_service.py | the block after the preferences / cohort block | test_v04 | `[pyt] tag=s07c-gates-mut-M05 start=2026-11-12 22:07:19 end=2026-11-12 22:07:24 elapsed=5s bound=600s status=FAIL rc=1` | test_v04_placement_after_scores_before_preferences | KILLED (AssertionError) | sha256 MATCH |
| M06 | app/services/extraction_service.py | the block outside `if scores_summary:` (emitted with no summary) | test_v06 | `[pyt] tag=s07c-gates-mut-M06 start=2026-11-12 22:07:46 end=2026-11-12 22:07:52 elapsed=6s bound=600s status=FAIL rc=1` | test_v06_no_scores_summary_is_byte_identical | KILLED (AssertionError) | sha256 MATCH |
| M07 | app/services/structured_comparison_service.py | the streaming caller omits the keyword | test_v08 | `[pyt] tag=s07c-gates-mut-M07 start=2026-11-12 22:08:14 end=2026-11-12 22:08:20 elapsed=5s bound=600s status=FAIL rc=1` | test_v08_both_production_callers_pass_the_scorer_index | KILLED (AssertionError) | sha256 MATCH |
| M08 | app/services/structured_comparison_service.py | the REST caller passes .get("winner_index", 0) | test_v08 | `[pyt] tag=s07c-gates-mut-M08 start=2026-11-12 22:08:42 end=2026-11-12 22:08:48 elapsed=6s bound=600s status=FAIL rc=1` | test_v08_both_production_callers_pass_the_scorer_index | KILLED (AssertionError) | sha256 MATCH |
| M09 | scripts/meas_claude_gate.py | the A6 builder passes 0 for every case | test_v10 | `[pyt] tag=s07c-gates-mut-M09 start=2026-11-12 22:09:10 end=2026-11-12 22:09:15 elapsed=5s bound=600s status=FAIL rc=1` | test_v10_harness_a6_and_a1_request_parity | KILLED (AssertionError) | sha256 MATCH |
| M10 | scripts/meas_claude_gate.py | the A1 builder omits the keyword | test_v10 | `[pyt] tag=s07c-gates-mut-M10 start=2026-11-12 22:09:38 end=2026-11-12 22:09:43 elapsed=6s bound=600s status=FAIL rc=1` | test_v10_harness_a6_and_a1_request_parity | KILLED (AssertionError) | sha256 MATCH |
| M11 | app/services/extraction_service.py | the block text drifts by one word | test_v02 | `[pyt] tag=s07c-gates-mut-M11 start=2026-11-12 22:11:39 end=2026-11-12 22:11:45 elapsed=5s bound=600s status=FAIL rc=1` | test_v02_block_bytes_index_0_and_1 | KILLED (AssertionError) | sha256 MATCH |
| M12 | app/services/llm_router.py | image_tier3 keeps a closed schema | test_t01 or test_t02 | `[pyt] tag=s07c-gates-mut-M12 start=2026-11-12 22:12:07 end=2026-11-12 22:12:12 elapsed=5s bound=600s status=FAIL rc=1` | test_t01_image_tier3_site_option_b, test_t02_image_tier3_claude_request | KILLED (AssertionError) | sha256 MATCH |
| M13 | app/services/llm_router.py | image_tier3 expects_json False | test_t01 or test_t02 | `[pyt] tag=s07c-gates-mut-M13 start=2026-11-12 22:12:35 end=2026-11-12 22:12:40 elapsed=5s bound=600s status=FAIL rc=1` | test_t01_image_tier3_site_option_b, test_t02_image_tier3_claude_request | KILLED (AssertionError) | sha256 MATCH |
| M14 | app/services/llm_router.py | image_tier3 claude_max_tokens 120 | test_t01 | `[pyt] tag=s07c-gates-mut-M14 start=2026-11-12 22:13:02 end=2026-11-12 22:13:08 elapsed=5s bound=600s status=FAIL rc=1` | test_t01_image_tier3_site_option_b | KILLED (AssertionError) | sha256 MATCH |
| M15 | app/services/llm_router.py | IMAGE_TIER3_SCHEMA kept (re-added) | test_t03 | `[pyt] tag=s07c-gates-mut-M15 start=2026-11-12 22:13:30 end=2026-11-12 22:13:36 elapsed=6s bound=600s status=FAIL rc=1` | test_t03_image_tier3_schema_constant_deleted | KILLED (AssertionError) | sha256 MATCH |
| M16 | scripts/meas_claude_gate.py | the harness gold read changed | test_v11 | `[pyt] tag=s07c-gates-mut-M16 start=2026-11-12 22:14:03 end=2026-11-12 22:14:10 elapsed=7s bound=600s status=FAIL rc=1` | test_v11_evaluation_unchanged | KILLED (AssertionError) | sha256 MATCH |
| M17 | app/services/extraction_service.py | GC-9: `score_winner_index in (0, 1)` -> `score_winner_index >= 0` (2 accepted) | test_v05 | `[pyt] tag=s07c-gates-mut-M17 start=2026-11-12 22:14:33 end=2026-11-12 22:14:38 elapsed=5s bound=600s status=FAIL rc=1` | test_v05_invalid_values_are_byte_identical | KILLED (AssertionError) | sha256 MATCH |
| M18 | app/services/llm_router.py | GC-9: the _normalise strip condition `is None` -> `is not None` | test_t04 | `[pyt] tag=s07c-gates-mut-M18 start=2026-11-12 22:15:00 end=2026-11-12 22:15:09 elapsed=8s bound=600s status=FAIL rc=1` | test_t04_claude_branch_fence_and_parse | KILLED (AssertionError) | sha256 MATCH |

- 22:02:58 scratch worktree created (git -C W worktree add --detach <notes>/mut 1da03aff), python only, no junction; 22:05:24 .qa-mutation.lock written (label + time); 22:16:22 removed by `finish` after all four targets matched their pristine sha256 (= the GREEN report values: extraction_service 7e508ed4..., structured_comparison_service 08bf1120..., llm_router 9c14b241..., meas_claude_gate e6bcbe3d...); 22:16:47 git worktree remove --force: rc 0, gone from git worktree list.
- mut_driver.py check: every old string count=1 on the CRLF bytes before any run (M04 = one contiguous region rewrite: the append moved in front of the scores f-string; M05 / M06 = the append moved after the preferences block / dedented out of `if scores_summary:`; M10 = the A1 keyword line removed; M12 = an inline closed schema).
- KILLED = rc 1 with >= 1 FAILED node among the -k rows, one `E AssertionError` line per failed node, 0 other exception lines and 0 pytest ERROR results (re-read from every log; M01..M10 were first printed SURVIVED/CHECK by a parser that read the runner's truncated short-summary message; the raw jsonl keeps result_printed for them).
- Assertion messages (selected): M07 `line 5562: score_winner_index keyword count 0`; M08 `line 4700: scoring_result.get('winner_index', 0)`; M09 `A6 requests without the case's fixed-winner block: 58 of 120`; M11 `_FIXED_WINNER_BLOCK != the V3 bytes`; M12 `image_tier3 still carries an output schema` / `still requests a json_schema format`; M15 the re-added schema `is None` fails; M17 `('2', True)` (index 2 accepted); M18 the base-path list [URL, None, None, None, URL].
- 18 of 18 KILLED; 0 survivors; 0 equivalents.

## (2) Comm set (union rule) and the base record

- class ref: 290
- class named_pin: 8
- class srcscan: 157
- class claude_md: 7
- class helper_importer: 7
- minus precommit: tests/test_precommit_hook.py, tests/test_precommit_hook_phase_b.py, tests/test_precommit_hook_phase_b_round2.py
- members 365; list gates/comm_list.txt (LF, read back); set sha256 aa393545...
- base: 91 reused per file from the RED round's runs (GC-8), 273 run at base in gates/basewt (11 chunks), absent at base: tests/test_s81_s07c_role_fix.py
- base record stored: C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\8c207f06-e37e-4c6d-9fbf-f58e9fdf8eab\scratchpad\harness\base_records\c6ebbd2ed593081cb6241915c36ae29af4c29bca\aa393545....txt (+ .files, .header.txt, .pyt.log)

HEAD chunks (W):

```
[pyt] tag=s07c-gates-comm-head-00 start=2026-11-12 22:23:02 end=2026-11-12 22:23:57 elapsed=55s bound=1200s status=OK rc=0 | 846 passed, 31 warnings in 51.83s | [hermeticity] sentinel checked 846 test(s); [netguard] blocked 34 attempt(s) from 7 node(s)
[pyt] tag=s07c-gates-comm-head-01 start=2026-11-12 22:24:23 end=2026-11-12 22:26:04 elapsed=101s bound=1200s status=OK rc=0 | 1558 passed, 1 skipped, 6 deselected, 17 warnings in 99.41s (0:01:39) | [hermeticity] sentinel checked 1559 test(s); [netguard] blocked 31 attempt(s) from 13 node(s)
[pyt] tag=s07c-gates-comm-head-02 start=2026-11-12 22:26:28 end=2026-11-12 22:26:53 elapsed=25s bound=1200s status=OK rc=0 | 464 passed, 2 skipped, 17 warnings in 22.87s | [hermeticity] sentinel checked 465 test(s); [netguard] blocked 11 attempt(s) from 5 node(s)
[pyt] tag=s07c-gates-comm-head-03 start=2026-11-12 22:27:15 end=2026-11-12 22:29:46 elapsed=151s bound=1200s status=OK rc=0 | 1995 passed, 20 warnings in 148.55s (0:02:28) | [hermeticity] sentinel checked 1995 test(s); [netguard] blocked 72 attempt(s) from 37 node(s)
[pyt] tag=s07c-gates-comm-head-04 start=2026-11-12 22:30:08 end=2026-11-12 22:31:35 elapsed=87s bound=1200s status=OK rc=0 | 755 passed, 5 deselected, 17 warnings in 84.41s (0:01:24) | [hermeticity] sentinel checked 755 test(s); [netguard] blocked 11 attempt(s) from 2 node(s)
[pyt] tag=s07c-gates-comm-head-05 start=2026-11-12 22:31:57 end=2026-11-12 22:32:24 elapsed=27s bound=1200s status=OK rc=0 | 589 passed in 25.47s | [hermeticity] sentinel checked 589 test(s); [netguard] blocked 7 attempt(s) from 1 node(s)
[pyt] tag=s07c-gates-comm-head-06 start=2026-11-12 22:32:47 end=2026-11-12 22:33:26 elapsed=40s bound=1200s status=FAIL rc=1 | 2 failed, 546 passed, 21 skipped, 5 deselected, 21 warnings in 37.83s | [hermeticity] sentinel checked 548 test(s); [netguard] blocked 165 attempt(s) from 21 node(s)
[pyt] tag=s07c-gates-comm-head-07 start=2026-11-12 22:33:49 end=2026-11-12 22:35:53 elapsed=124s bound=1200s status=FAIL rc=1 | 692 passed, 4 skipped, 9 deselected, 1 xfailed, 17 warnings, 2 errors in 121.63s (0:02:01) | [hermeticity] sentinel checked 695 test(s); [netguard] blocked 23 attempt(s) from 6 node(s)
[pyt] tag=s07c-gates-comm-head-08 start=2026-11-12 22:36:20 end=2026-11-12 22:38:19 elapsed=119s bound=1200s status=OK rc=0 | 1906 passed, 366 warnings in 116.24s (0:01:56) | [hermeticity] sentinel checked 1906 test(s); [netguard] blocked 24 attempt(s) from 3 node(s)
[pyt] tag=s07c-gates-comm-head-09 start=2026-11-12 22:38:41 end=2026-11-12 22:41:52 elapsed=191s bound=1200s status=FAIL rc=1 | 8 failed, 2826 passed, 88 warnings in 188.08s (0:03:08) | [hermeticity] sentinel checked 2834 test(s); [netguard] blocked 24 attempt(s) from 2 node(s)
[pyt] tag=s07c-gates-comm-head-10 start=2026-11-12 22:42:14 end=2026-11-12 22:43:24 elapsed=70s bound=1200s status=FAIL rc=1 | 10 failed, 1729 passed, 17 warnings in 67.45s (0:01:07) | [hermeticity] sentinel checked 1739 test(s); [netguard] blocked 24 attempt(s) from 9 node(s)
[pyt] tag=s07c-gates-comm-head-11 start=2026-11-12 22:43:48 end=2026-11-12 22:45:50 elapsed=122s bound=1200s status=FAIL rc=1 | 2 failed, 2020 passed, 1 xfailed, 49 warnings in 120.01s (0:02:00) | [hermeticity] sentinel checked 2023 test(s); [netguard] blocked 19 attempt(s) from 9 node(s)
[pyt] tag=s07c-gates-comm-head-12 start=2026-11-12 22:46:13 end=2026-11-12 22:47:06 elapsed=53s bound=1200s status=OK rc=0 | 379 passed, 2 skipped, 12 deselected, 18 warnings in 51.25s | [hermeticity] sentinel checked 380 test(s); [netguard] blocked 114 attempt(s) from 39 node(s)
[pyt] tag=s07c-gates-comm-head-13 start=2026-11-12 22:47:32 end=2026-11-12 22:48:28 elapsed=56s bound=1200s status=OK rc=0 | 475 passed, 6 deselected, 35 xfailed, 16 warnings in 51.64s | [hermeticity] sentinel checked 510 test(s); [netguard] blocked 75 attempt(s) from 27 node(s)
[pyt] tag=s07c-gates-comm-head-14 start=2026-11-12 22:48:51 end=2026-11-12 22:49:16 elapsed=26s bound=1200s status=OK rc=0 | 878 passed, 16 warnings in 23.72s | [hermeticity] sentinel checked 878 test(s); [netguard] blocked 20 attempt(s) from 12 node(s)
```

BASE chunks (gates/basewt at c6ebbd2e) + the reused RED base runs:

```
[pyt] tag=s07c-gates-comm-base-00 start=2026-11-12 22:49:39 end=2026-11-12 22:50:29 elapsed=51s bound=1200s status=OK rc=0 | 453 passed, 17 warnings in 48.50s | [hermeticity] sentinel checked 453 test(s); [netguard] blocked 50 attempt(s) from 11 node(s)
[pyt] tag=s07c-gates-comm-base-01 start=2026-11-12 22:50:52 end=2026-11-12 22:51:49 elapsed=58s bound=1200s status=OK rc=0 | 1524 passed, 3 skipped, 4 deselected, 17 warnings in 55.55s | [hermeticity] sentinel checked 1527 test(s); [netguard] blocked 15 attempt(s) from 10 node(s)
[pyt] tag=s07c-gates-comm-base-02 start=2026-11-12 22:52:12 end=2026-11-12 22:52:53 elapsed=42s bound=1200s status=OK rc=0 | 844 passed, 2 skipped, 14 warnings in 39.55s | [hermeticity] sentinel checked 845 test(s); [netguard] blocked 35 attempt(s) from 13 node(s)
[pyt] tag=s07c-gates-comm-base-03 start=2026-11-12 22:53:16 end=2026-11-12 22:55:56 elapsed=160s bound=1200s status=OK rc=0 | 1745 passed, 5 deselected, 22 warnings in 157.25s (0:02:37) | [hermeticity] sentinel checked 1745 test(s); [netguard] blocked 35 attempt(s) from 23 node(s)
[pyt] tag=s07c-gates-comm-base-04 start=2026-11-12 22:56:19 end=2026-11-12 22:56:45 elapsed=27s bound=1200s status=OK rc=0 | 603 passed, 21 skipped, 2 warnings in 24.95s | [hermeticity] sentinel checked 603 test(s); [netguard] blocked 128 attempt(s) from 7 node(s)
[pyt] tag=s07c-gates-comm-base-05 start=2026-11-12 22:57:10 end=2026-11-12 22:57:47 elapsed=38s bound=1200s status=FAIL rc=1 | 2 failed, 293 passed, 2 skipped, 14 deselected, 16 warnings in 35.82s | [hermeticity] sentinel checked 295 test(s); [netguard] blocked 38 attempt(s) from 8 node(s)
[pyt] tag=s07c-gates-comm-base-06 start=2026-11-12 22:58:09 end=2026-11-12 22:59:48 elapsed=99s bound=1200s status=OK rc=0 | 1359 passed, 367 warnings in 95.92s (0:01:35) | [hermeticity] sentinel checked 1359 test(s); [netguard] blocked 24 attempt(s) from 3 node(s)
[pyt] tag=s07c-gates-comm-base-07 start=2026-11-12 23:00:11 end=2026-11-12 23:01:13 elapsed=61s bound=1200s status=FAIL rc=1 | 11 failed, 1579 passed, 18 warnings in 58.85s | [hermeticity] sentinel checked 1590 test(s); [netguard] blocked 24 attempt(s) from 9 node(s)
[pyt] tag=s07c-gates-comm-base-08 start=2026-11-12 23:01:35 end=2026-11-12 23:03:22 elapsed=107s bound=1200s status=FAIL rc=1 | 2 failed, 1833 passed, 1 xfailed, 47 warnings in 104.39s (0:01:44) | [hermeticity] sentinel checked 1836 test(s); [netguard] blocked 4 attempt(s) from 2 node(s)
[pyt] tag=s07c-gates-comm-base-09 start=2026-11-12 23:03:44 end=2026-11-12 23:04:36 elapsed=52s bound=1200s status=OK rc=0 | 418 passed, 1 skipped, 4 deselected, 18 warnings in 49.75s | [hermeticity] sentinel checked 418 test(s); [netguard] blocked 66 attempt(s) from 27 node(s)
[pyt] tag=s07c-gates-comm-base-10 start=2026-11-12 23:04:59 end=2026-11-12 23:05:26 elapsed=27s bound=1200s status=OK rc=0 | 727 passed, 4 deselected, 35 xfailed, 15 warnings in 25.35s | [hermeticity] sentinel checked 762 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
```

- HEAD failed / error node ids (24): tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction, tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable, tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only, tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene, tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF], tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty], tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false], tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0], tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset], tests/test_s81_s07_meas_harness.py::test_r35_fixtures, tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content, tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker], tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery], tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common], tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch], tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata], tests/test_s81_s18b_store_label.py::test_r2_table_shape, tests/test_s81_s19_gap_queue.py::test_r15_hygiene, tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf, tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first, tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene, tests/test_s81_s24_auth_throttle.py::test_r92_hygiene
- BASE failed / error node ids (24): tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction, tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable, tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only, tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene, tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF], tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty], tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false], tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0], tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset], tests/test_s81_s07_meas_harness.py::test_r35_fixtures, tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content, tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker], tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery], tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common], tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch], tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata], tests/test_s81_s18b_store_label.py::test_r2_table_shape, tests/test_s81_s19_gap_queue.py::test_r15_hygiene, tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf, tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first, tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene, tests/test_s81_s24_auth_throttle.py::test_r92_hygiene
- branch-only-new (0): EMPTY
- base-only (0): none
- HEAD totals {'passed': 17658, 'skipped': 30, 'deselected': 43, 'failed': 22, 'xfailed': 37, 'error': 2}; base-run totals {'passed': 11378, 'skipped': 29, 'deselected': 31, 'failed': 15, 'xfailed': 36}

- Derivation (derive_comm.py over git objects of 1da03aff, no worktree file opened): module / symbol references of the four changed modules (extraction_service, structured_comparison_service, llm_router, meas_claude_gate; generate_comparison, IMAGE_TIER3_SCHEMA, image_tier3, score_winner, _FIXED_WINNER_BLOCK, SiteSpec, to_claude_request) UNION the named source-scanning pins UNION every other app / scripts source reader (inspect.getsource*, ast.parse(, app/ scripts/ .github path literals or path segments, <module>.__file__, *.py glob walkers) UNION the CLAUDE.md readers (quoted CLAUDE.md or the CLAUDE_MD name; their importers by the import graph are members already) UNION the importers of the edited test modules and of the support modules that reference a changed module (w4_11_prompt_digest_recorder, the two rubric generators); MINUS the precommit hook files in the union (3 of the 4 matched). No test-support helper is edited by the unit.
- IMAGE_TIER3_SCHEMA has no reader at HEAD outside the RED file T03 (git grep over the tree minus CLAUDE.md); score_winner_index / _FIXED_WINNER_BLOCK appear only in the four changed modules, the RED file and CLAUDE.md.
- Base: no stored record existed under harness/base_records/c6ebbd2e.../; GC-8 reuse of the RED round base runs for 91 members (their FAILED / ERROR ids: base-c1 3, base-c2 0, base-s1 0, base-s2 6); 273 members run at base in gates/basewt (detached c6ebbd2e, created 22:21:49, removed 23:06:38, status empty before removal); tests/test_s81_s07c_role_fix.py absent at base.
- No branch-only-new node, so no alone re-run was needed (the rerun path of comm_driver.py was not used).
- The reused RED base runs (GC-8; their [pyt] lines as the RED report records them, also in the stored record .pyt.log / .header.txt):
  - `[pyt] tag=s07c-r-base-c1 start=2026-11-12 19:52:34 end=2026-11-12 19:54:48 elapsed=135s bound=600s status=FAIL rc=1 (7 files: 1 failed, 736 passed, 2 skipped, 1 xfailed, 2 errors)`
  - `[pyt] tag=s07c-r-base-c2 start=2026-11-12 19:56:06 end=2026-11-12 19:58:19 elapsed=133s bound=600s status=OK rc=0 (41 files: 2213 passed)`
  - `[pyt] tag=s07c-r-base-s1 start=2026-11-12 20:46:09 end=2026-11-12 20:47:09 elapsed=60s bound=600s status=OK rc=0 (22 files: 895 passed, 1 skipped, 2 deselected)`
  - `[pyt] tag=s07c-r-base-s2 start=2026-11-12 20:47:50 end=2026-11-12 20:51:24 elapsed=214s bound=600s status=FAIL rc=1 (21 files: 6 failed, 2416 passed, 1 skipped, 10 deselected)`
- Every comm chunk was preceded by waitfree returning `free poll=0` (26 of 26; recorded per chunk in comm_results.jsonl); every mutant run likewise (18 of 18); the fences likewise.

## (3) The fourteen client fences

- fences.sh: waitfree `free poll=0 23:06:54`, then from W/SmartCompareApp: `junction ok` (node_modules/@babel/core and node_modules/.bin/jest present), jest --version 29.7.0, one `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci <the 14 paths>`, 20 s settle.
- [jest] tag=s07c-gates-fences start=2026-11-12 23:06:57 end=2026-11-12 23:07:20 rc=1
- Test Suites: 1 failed, 13 passed, 14 total
- Tests:       4 failed, 236 passed, 240 total
- Snapshots:   0 total
- Time:        13.043 s
- PASS: brand/inAppMark.u4c, clientTruth/medicalNote.s74, clientTruth/privacyManifest.s74, clientTruth/shareTruth.s74, clipboardFallbackService, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService, playInstallReferrerService.edges, ResultsScreen.timeout (13).
- FAIL: config/nativeBundle.w37 on exactly four nodes, the accepted base drift nodes of the common brief (the S81-07 merge round C-4 expected the same state):
  - config/nativeBundle.w37 d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules
  - config/nativeBundle.w37 k2 package-lock.json and node_modules resolve the five packages at or above those patches
  - config/nativeBundle.w37 k4 eslint-config-expo is on the SDK-54 line (~10.0.x) in package.json, the lock and node_modules
  - config/nativeBundle.w37 k5 offline expo-install consistency (every declared package the installed expo bundles satisfies its bundled range)
- Not re-measured at base (no junction in a scratch worktree, by rule); the four nodes read package.json / package-lock.json / the shared node_modules; the unit changes no SmartCompareApp file.

## (4) PR body

- s07c/gates/PR_BODY.md: 14,492 bytes (cap 25,600, measured with python), 0 bytes > 127, last line `Generated with Claude Code.`; sections: what changed (V and T, run-1 evidence two lines each), the precondition, the RED rows (17), the E-rows (E1 E2 E4a E4b E4c E5; E3 dropped), the gates with counts, stated limits L1-L7 (L3 as GC-5) + L8-L12 added by the rounds, owner steps (none); GC-11 one line (no flag, no knob, no fixture, no bar, no A6 sentence change) in the opening paragraph.
- Assembled by assemble_pr.py (run through the shell) from PR_BODY.part1.md, part2.md, the part3 template filled from comm_result.json + fence_result.json, and part4.md.
- PR_BODY.md final: 14492 bytes, sha256 e700a8b1... (re-assembled 23:13 after one wording change in L11).

## Files of this round (sha256 over the bytes on disk)

- notes.md d85b43ae... (21997 bytes)
- mut_driver.py 1ee62322... (16499 bytes)
- mut_results.jsonl 06709f56... (16542 bytes)
- mut_pristine.json d3b4c33d... (431 bytes)
- derive_comm.py 118e8656... (4375 bytes)
- comm_classes.json 93149395... (20860 bytes)
- comm_list.txt aa393545... (13186 bytes)
- comm_driver.py d575a187... (6390 bytes)
- comm_plan.json 23a69016... (64346 bytes)
- comm_results.jsonl efd603ff... (60044 bytes)
- comm_compare.py e9fa460b... (6474 bytes)
- comm_result.json b9b35d51... (11765 bytes)
- fences.sh b1a95c3f... (1734 bytes)
- fences.log 39948e74... (15919 bytes)
- claude_md.diff b2f28a5a... (58103 bytes)
- claude_block.txt 51db8a09... (4967 bytes)
- PR_BODY.md e700a8b1... (14492 bytes)
- gen_report.py 25acba02... (4226 bytes)
- fence_result.json 8ac4667f... (1313 bytes)
- assemble_pr.py 20490b10... (2369 bytes)
- PR_BODY.part1.md d9a4d9a5... (4274 bytes)
- PR_BODY.part2.md 28a708cd... (3672 bytes)
- PR_BODY.part3.tmpl 172af4a5... (2772 bytes)
- PR_BODY.part4.md f06f52ab... (3213 bytes)
- report_extra.json 25b9ec6a... (12900 bytes)

## Deviations

- The comm-chunk driver (comm_driver.py) ran through the tool background mode as ONE sequential process, launched once at 22:22:5x (first chunk 22:23:02, RUN DONE 23:05:46): one pytest at a time, waitfree before each chunk, 20 s after, no second copy (the 2026-10-29 harness rule on chunk drivers). The brief line 'never in the background' is read as never a concurrent or unbounded pytest; nothing else of mine ran while it ran (the fences ran after RUN DONE). The mutants ran in the foreground (two groups).
- Tags: s07c-gates-mut-<id> and s07c-gates-comm-<head|base>-NN (round name gates).
- M01..M10 were first printed SURVIVED/CHECK by a parser that read the truncated short-summary message of the runner; reclassified KILLED from the E lines of each log (one AssertionError per failed node, 0 other exception lines, 0 pytest ERROR results); mut_results.jsonl keeps result_printed for them.
- The base record is named by the sha256 of the full 365-member list (the comm_list.txt bytes, so a later round with the same set finds it); the RED file is listed in .files but is absent at base (the 229b61e9 record named its set without its absent unit files).
- The union rule source-reader classes were operationalized as regex classes over git blobs (listed above), inclusive; app.main / TestClient users that name no changed module are not members (the union definition of the task).
- The PR body ends with the ASCII line Generated with Claude Code. (the house attribution line without its emoji: pure ASCII as the task requires).
- Every report, notes and PR body file was written through the shell (python heredocs or python scripts run in the shell); the helper .py scripts were written with the Write tool.

## Questions for the gate

- Q1: the fourteen fences show 13 suites green and config/nativeBundle.w37 red on exactly its four accepted drift nodes (d5, k2, k4, k5); I read that as the accepted fence state (the brief names those four as the accepted base failures; the S81-07 merge round C-4 expected the same) and set READY_FOR_ADVERSARY. If the gate reads GC-10 as all fourteen suites green, the verdict becomes BLOCKED on those four nodes (not caused by this unit: no SmartCompareApp file in the diff).
- Q2: the stored base record is named by the 365-member set sha (incl. the RED file, absent at base); confirm or rename to the 364 base-present members.
- Q3: the comm set excludes app.main / TestClient users that name no changed module (the task union definition); the change is import-safe (a new constant and a defaulted keyword; the deleted IMAGE_TIER3_SCHEMA has no reader outside the RED file), and every route-level test that names generate_comparison or a changed module is a member.

## NOT MEASURED

- The full jest suite (not required: LC-7 / GC-10).
- The client fences at base (no junction in a scratch worktree by rule); the four failing nodes are the accepted base drift nodes of the brief.
- The base count of the netguard egress attempts of tests/test_winner_prose_reconciliation.py (its base run is the RED round base-c2, whose per-node list is truncated; at HEAD the file passes).
- CI, run 2 of S81-07 and anything live or in production.

## git status --short (W) and worktrees

- `git -C W status --short` at 23:09:26: (empty)
- branch feature/s81-07c-role-fix, HEAD 1da03aff3bbb784b5f83656158405260f5874b71 (unchanged)
- `git worktree list` (s07c rows): only C:/Users/SynAckITPC/Documents/AI/sc-s81-s07c 1da03aff [feature/s81-07c-role-fix]; gates/mut and gates/basewt removed.
