# S81-22 GREEN REPORT (GREEN agent, Opus 5.5 = claude-opus-5-5, 2026-11-06; the hook test files NOT RUN: no .githooks change; the FULL jest NOT run, LC-7)

Written through the shell (python heredoc), not the Write tool. Model note: the brief addressed the agent as "Fable" and its commit template named "Claude Fable 5.1"; this agent runs on Opus 5.5, so the commit trailer names Opus 5.5 (the common brief: the trailer names the committing agent's own model).

## 0. Result
- Branch `feature/s81-s22-compare-runs` from 18cb9e04; ONE commit through the hook: HEAD `0d588d0b52a6532359a051d85ae89698e452cd63` (15 files, 4616 insertions, 4 deletions). No push, no PR, no rebase. `git status --short` after the commit: empty.
- Frozen RED files re-hashed first and last: c1cb93752908c061beacb01ca47968ecd7026af8581bc5bca4220fc894c52a52 / 39a46d1c574ecf5e8403f5037c7f611ca142d4e1bbcbbc2655f6677556ea2199 (byte-identical; committed with GREEN's files).
- Byte copies of every edited existing file: S81-22_green_before/ + SHA256SUMS.txt.

## 1. Unit gates ([pyt] lines; logs under S81-22_green/logs/)
- RED OFF: 192 passed. [pyt] tag=s22g-red-off start=2026-11-06 17:09:02 end=2026-11-06 17:09:18 elapsed=16s bound=600s status=OK rc=0 ([hermeticity] 192, [netguard] blocked 0)
- RED ON (ENABLE_COMPARE_RUN_LEDGER=true ENABLE_BATCH_JUDGE=apply in the runner env only): 192 passed. [pyt] tag=s22g-red-on start=2026-11-06 17:09:28 end=2026-11-06 17:09:44 elapsed=16s bound=600s status=OK rc=0
- gate rows: 9 passed. [pyt] tag=s22g-gr start=2026-11-06 17:10:41 end=2026-11-06 17:10:47 elapsed=6s bound=600s status=OK rc=0
- final bytes (after E4 + CLAUDE.md), RED + gate rows: OFF 201 passed [pyt] tag=s22g-final-off start=2026-11-06 17:57:44 end=2026-11-06 17:57:54 elapsed=10s bound=600s status=OK rc=0; ON 201 passed [pyt] tag=s22g-final-on start=2026-11-06 17:57:55 end=2026-11-06 17:58:05 elapsed=10s bound=600s status=OK rc=0
- gate-row inverse edits (gr_mutants.tsv; lock .qa-mutation.lock created and removed; every restore sha-verified): GR1a (await on the stream call) 2 failed; GR1b (camera line removed) 1 failed; GR1c (url capture line removed) 1 failed; GR2a (bare to_regclass raise re-added) 2 failed; GR2b (a judgements column dropped from the guard set) 1 failed; GR3a (one E2 entry removed) 1 failed; GR3b (a kb_products literal added to the judge) 1 failed: all AssertionError, status=FAIL rc=1, tags s22g-mut-gr1a..gr3b (17:11:17-17:12:05).
- route pins OFF (23 files incl. the RED + gate rows): 2027 passed, 1 failed (test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content, CRLF noise), 2 errors (test_prompt_truth cold tiktoken). [pyt] tag=s22g-pins-route-off2 start=2026-11-06 17:14:55 end=2026-11-06 17:16:26 elapsed=91s bound=1200s status=FAIL rc=1. The first run (s22g-pins-route-off, 17:12:36-17:13:57) also had test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app red -> E4 (section 3).
- route pins ON: 2023 passed, 5 failed = r06 + test_s81_s03_llm_ledger_v2.py::test_i2_camera_flag_off_no_metadata_llm[false|None], ::test_i6_off_camera_real_compare_total_cost_is_base[None|false] (they count llm_pricing calls; under ON compare_runs reads openai_entry_record / price_call; no body change; OFF green), 2 tiktoken errors. [pyt] tag=s22g-pins-route-on start=2026-11-06 17:16:35 end=2026-11-06 17:18:06 elapsed=92s bound=1200s status=FAIL rc=1. U13 (test_s71_u13_compare_auth_required) + test_m13_21_openapi_gated green in both states (GC-9: identical, no re-record).
- migration readers + E-row files (11 files) OFF: 957 passed [pyt] tag=s22g-pins-mig-off start=2026-11-06 17:19:00 end=2026-11-06 17:19:51 elapsed=51s bound=1200s status=OK rc=0; ON: 957 passed [pyt] tag=s22g-pins-mig-on start=2026-11-06 17:20:55 end=2026-11-06 17:21:46 elapsed=51s bound=1200s status=OK rc=0
- CI-order set (19 files): 1768 passed, 1 failed (r06), 2 errors (tiktoken) = the base noise. [pyt] tag=s22g-ciorder start=2026-11-06 17:22:08 end=2026-11-06 17:23:36 elapsed=88s bound=1200s status=FAIL rc=1 (base: 1767 passed, same three nodes)

## 2. Base record completion (GC-6) and the comm set
### base driver (scratch worktree <scratchpad>/g22b at 18cb9e04, junction-free, removed with git worktree remove --force; git worktree list shows it gone)
```
17:23:19 driver start: 17 red chunks, 242 files to run
17:23:20 chunk 00 waiting for a foreign pytest
17:24:40 chunk 00 (14 of 25 files): [pyt] tag=s22g-base-c00 start=2026-11-06 17:24:22 end=2026-11-06 17:24:40 elapsed=18s bound=1200s status=OK rc=0
17:25:41 chunk 01 (17 of 25 files): [pyt] tag=s22g-base-c01 start=2026-11-06 17:24:41 end=2026-11-06 17:25:41 elapsed=60s bound=1200s status=OK rc=0
17:26:04 chunk 02 (22 of 25 files): [pyt] tag=s22g-base-c02 start=2026-11-06 17:25:43 end=2026-11-06 17:26:04 elapsed=21s bound=1200s status=OK rc=0
17:26:25 chunk 03 (14 of 25 files): [pyt] tag=s22g-base-c03 start=2026-11-06 17:26:05 end=2026-11-06 17:26:25 elapsed=19s bound=1200s status=OK rc=0
17:26:45 chunk 04 (14 of 25 files): [pyt] tag=s22g-base-c04 start=2026-11-06 17:26:27 end=2026-11-06 17:26:45 elapsed=19s bound=1200s status=OK rc=0
17:27:33 chunk 05 (20 of 25 files): [pyt] tag=s22g-base-c05 start=2026-11-06 17:26:47 end=2026-11-06 17:27:33 elapsed=46s bound=1200s status=OK rc=0
17:27:53 chunk 06 (17 of 25 files): [pyt] tag=s22g-base-c06 start=2026-11-06 17:27:35 end=2026-11-06 17:27:53 elapsed=19s bound=1200s status=OK rc=0
17:28:20 chunk 07 (12 of 25 files): [pyt] tag=s22g-base-c07 start=2026-11-06 17:27:55 end=2026-11-06 17:28:19 elapsed=24s bound=1200s status=OK rc=0
17:29:02 chunk 08 (18 of 25 files): [pyt] tag=s22g-base-c08 start=2026-11-06 17:28:21 end=2026-11-06 17:29:02 elapsed=41s bound=1200s status=FAIL rc=1
17:29:36 chunk 09 (21 of 25 files): [pyt] tag=s22g-base-c09 start=2026-11-06 17:29:04 end=2026-11-06 17:29:35 elapsed=32s bound=1200s status=OK rc=0
17:30:04 chunk 10 (10 of 25 files): [pyt] tag=s22g-base-c10 start=2026-11-06 17:29:37 end=2026-11-06 17:30:04 elapsed=26s bound=1200s status=OK rc=0
17:30:10 chunk 11 (1 of 25 files): [pyt] tag=s22g-base-c11 start=2026-11-06 17:30:05 end=2026-11-06 17:30:10 elapsed=4s bound=1200s status=OK rc=0
17:30:22 chunk 12 (6 of 25 files): [pyt] tag=s22g-base-c12 start=2026-11-06 17:30:11 end=2026-11-06 17:30:22 elapsed=10s bound=1200s status=OK rc=0
17:31:16 chunk 13 (20 of 25 files): [pyt] tag=s22g-base-c13 start=2026-11-06 17:30:24 end=2026-11-06 17:31:16 elapsed=52s bound=1200s status=OK rc=0
17:31:51 chunk 14 (16 of 25 files): [pyt] tag=s22g-base-c14 start=2026-11-06 17:31:18 end=2026-11-06 17:31:51 elapsed=33s bound=1200s status=OK rc=0
17:32:09 chunk 15 (14 of 25 files): [pyt] tag=s22g-base-c15 start=2026-11-06 17:31:53 end=2026-11-06 17:32:09 elapsed=16s bound=1200s status=OK rc=0
17:32:26 chunk 16 (6 of 9 files): [pyt] tag=s22g-base-c16 start=2026-11-06 17:32:10 end=2026-11-06 17:32:26 elapsed=16s bound=1200s status=OK rc=0
17:32:26 driver done
```
### head driver (real worktree)
```
17:32:52 head driver start: 729 members, 724 test files, 30 chunks
17:33:44 chunk 00 (25 files): [pyt] tag=s22g-head-c00 start=2026-11-06 17:32:54 end=2026-11-06 17:33:44 elapsed=50s bound=1200s status=OK rc=0
17:34:28 chunk 01 (25 files): [pyt] tag=s22g-head-c01 start=2026-11-06 17:33:46 end=2026-11-06 17:34:28 elapsed=42s bound=1200s status=FAIL rc=1
17:35:04 chunk 02 (25 files): [pyt] tag=s22g-head-c02 start=2026-11-06 17:34:30 end=2026-11-06 17:35:04 elapsed=35s bound=1200s status=OK rc=0
17:36:14 chunk 03 (25 files): [pyt] tag=s22g-head-c03 start=2026-11-06 17:35:06 end=2026-11-06 17:36:14 elapsed=68s bound=1200s status=OK rc=0
17:37:06 chunk 04 (25 files): [pyt] tag=s22g-head-c04 start=2026-11-06 17:36:16 end=2026-11-06 17:37:05 elapsed=50s bound=1200s status=OK rc=0
17:37:28 chunk 05 (25 files): [pyt] tag=s22g-head-c05 start=2026-11-06 17:37:07 end=2026-11-06 17:37:28 elapsed=21s bound=1200s status=OK rc=0
17:37:54 chunk 06 (25 files): [pyt] tag=s22g-head-c06 start=2026-11-06 17:37:30 end=2026-11-06 17:37:54 elapsed=24s bound=1200s status=OK rc=0
17:38:30 chunk 07 (25 files): [pyt] tag=s22g-head-c07 start=2026-11-06 17:37:56 end=2026-11-06 17:38:30 elapsed=34s bound=1200s status=OK rc=0
17:40:23 chunk 08 (25 files): [pyt] tag=s22g-head-c08 start=2026-11-06 17:38:32 end=2026-11-06 17:40:23 elapsed=111s bound=1200s status=OK rc=0
17:40:58 chunk 09 (25 files): [pyt] tag=s22g-head-c09 start=2026-11-06 17:40:24 end=2026-11-06 17:40:58 elapsed=34s bound=1200s status=OK rc=0
17:41:55 chunk 10 (25 files): [pyt] tag=s22g-head-c10 start=2026-11-06 17:41:00 end=2026-11-06 17:41:55 elapsed=55s bound=1200s status=OK rc=0
17:42:20 chunk 11 (25 files): [pyt] tag=s22g-head-c11 start=2026-11-06 17:41:57 end=2026-11-06 17:42:20 elapsed=23s bound=1200s status=OK rc=0
17:42:42 chunk 12 (25 files): [pyt] tag=s22g-head-c12 start=2026-11-06 17:42:21 end=2026-11-06 17:42:42 elapsed=20s bound=1200s status=OK rc=0
17:43:24 chunk 13 (25 files): [pyt] tag=s22g-head-c13 start=2026-11-06 17:42:44 end=2026-11-06 17:43:24 elapsed=40s bound=1200s status=OK rc=0
17:43:55 chunk 14 (25 files): [pyt] tag=s22g-head-c14 start=2026-11-06 17:43:25 end=2026-11-06 17:43:55 elapsed=30s bound=1200s status=FAIL rc=1
17:44:41 chunk 15 (25 files): [pyt] tag=s22g-head-c15 start=2026-11-06 17:43:56 end=2026-11-06 17:44:41 elapsed=45s bound=1200s status=FAIL rc=1
17:45:05 chunk 16 (25 files): [pyt] tag=s22g-head-c16 start=2026-11-06 17:44:43 end=2026-11-06 17:45:05 elapsed=23s bound=1200s status=FAIL rc=1
17:45:21 chunk 17 (25 files): [pyt] tag=s22g-head-c17 start=2026-11-06 17:45:07 end=2026-11-06 17:45:21 elapsed=15s bound=1200s status=OK rc=0
17:48:15 chunk 18 (25 files): [pyt] tag=s22g-head-c18 start=2026-11-06 17:45:22 end=2026-11-06 17:48:15 elapsed=173s bound=1200s status=OK rc=0
17:49:40 chunk 19 (25 files): [pyt] tag=s22g-head-c19 start=2026-11-06 17:48:16 end=2026-11-06 17:49:40 elapsed=84s bound=1200s status=OK rc=0
17:50:47 chunk 20 (25 files): [pyt] tag=s22g-head-c20 start=2026-11-06 17:49:42 end=2026-11-06 17:50:47 elapsed=65s bound=1200s status=FAIL rc=1
17:52:29 chunk 21 (25 files): [pyt] tag=s22g-head-c21 start=2026-11-06 17:50:48 end=2026-11-06 17:52:29 elapsed=101s bound=1200s status=FAIL rc=1
17:52:52 chunk 22 (25 files): [pyt] tag=s22g-head-c22 start=2026-11-06 17:52:30 end=2026-11-06 17:52:52 elapsed=22s bound=1200s status=OK rc=0
17:53:55 chunk 23 (25 files): [pyt] tag=s22g-head-c23 start=2026-11-06 17:52:54 end=2026-11-06 17:53:55 elapsed=61s bound=1200s status=OK rc=0
17:54:19 chunk 24 (25 files): [pyt] tag=s22g-head-c24 start=2026-11-06 17:53:56 end=2026-11-06 17:54:19 elapsed=24s bound=1200s status=OK rc=0
17:55:13 chunk 25 (25 files): [pyt] tag=s22g-head-c25 start=2026-11-06 17:54:21 end=2026-11-06 17:55:13 elapsed=53s bound=1200s status=OK rc=0
17:56:00 chunk 26 (25 files): [pyt] tag=s22g-head-c26 start=2026-11-06 17:55:14 end=2026-11-06 17:56:00 elapsed=46s bound=1200s status=OK rc=0
17:56:29 chunk 27 (25 files): [pyt] tag=s22g-head-c27 start=2026-11-06 17:56:01 end=2026-11-06 17:56:29 elapsed=28s bound=1200s status=OK rc=0
17:56:49 chunk 28 (23 files): [pyt] tag=s22g-head-c28 start=2026-11-06 17:56:31 end=2026-11-06 17:56:49 elapsed=18s bound=1200s status=OK rc=0
17:56:55 chunk 29 (1 files): [pyt] tag=s22g-head-c29 start=2026-11-06 17:56:50 end=2026-11-06 17:56:55 elapsed=5s bound=1200s status=OK rc=0
17:56:55 head driver done
```

- Record: harness/base_records/18cb9e04a36382fc417307500a092486f618d95e/e701a8ba6f8750db26df0e456ab9b844686694c8aa8e34f5f22dd1f5be4618ea.{txt,files,pyt.log,header.txt}: 726 files, 22 FAILED ids. Split: 312 reused by the RED per file from a0bfab95 (6 ids); 167 reused per file outright from the SF1 record 4345a784... at the same sha (14 ids); 242 RUN by GREEN (the RED's 17 alphabetical chunks with the SF1-held members removed: all 17 chunks ran, 1 to 22 members each; 2 ids, both in c08: tests/test_page_scraping.py); 5 helper modules not collected. The RED's c00-c03 logs carry no [pyt] status line, so NONE was reused (stated). PARTIAL_e701a8ba... kept as evidence.
- HEAD comm set: 729 files (HEAD_COMM_SET.txt = the RED's 726 + tests/test_s81_s22_compare_runs.py, tests/test_s81_s22_judge.py, tests/test_s81_s22_gate_rows.py); the union-rule re-check found no new member (every glob / walk / listdir reader and railway-config reader already in the 726; the E4 file test_s81_s05_request_context.py is a member; importers of test_s81_kb_schema / test_migration_043 / test_s81_s05 are members or the S81-22 files). 30 chunks (29 of <= 25 + test_secret_scan_static.py alone: 31 passed), no TIMEOUT, no NOT MEASURED.
- comm -13 (HEAD-only FAILED) = EMPTY; comm -23 (base-only) = EMPTY. The 22 shared ids:
```
tests/test_auth_interceptor.py::test_sign_in_with_social_exception
tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
tests/test_s81_s19_gap_queue.py::test_r15_hygiene
```

## 3. Deliberate pin changes
- E1 tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once: ("046", "048", "049", "051") -> ("046", "049", "051") + `#: S81-22 E1` comment.
- E2 tests/test_s81_kb_schema.py P02_ALLOWED: + ("scripts/cron_compare_judge.py", 'KB_PRUNE_FEEDBACK_RPC = "kb_prune_feedback"') and ("scripts/cron_compare_judge.py", 'KB_FEEDBACK_TABLE = "kb_feedback"') with the comment.
- E3 tests/test_migration_043_delete_user_cascade.py::test_fence_flags_each_dropped_delete and ::test_fence_flags_each_weakened_delete_predicate: the DELETE walk limited to KNOWN_USER_TABLES (the narrowest edit, R-S22-23).
- E4 (NEW, as the brief directs when the census goes red) tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app, anchors `_ALLOWED_CTX_FILES` (+ "app/services/compare_runs.py") and `_CTX_CONSUMER_ATTRS` (+ `_RUNS_CTX_ATTRS` = {consent_version, compare_request_id, device_fingerprint, device_key, PEPPER_ENV}); compare_runs.py imports the leaf as `from app.utils import request_context as _request_context` (the pinned S81-06 E9 shape) and carries no needle string (its docstring says "the S81-05 pepper", not the variable name).
- No other pin moved.

## 4. Other gates
- ruff --select E9,F63,F7,F82 --no-cache (7 py files): All checks passed; full ruff on compare_runs.py + cron_compare_judge.py clean (4 C420 fixed with dict.fromkeys); py_compile OK; hook ruff / black / sqlfluff passed at commit.
- sqlfluff lint --config .sqlfluff: 048 + rollback + the three APPLY files: clean.
- railway.judge.json: json.loads OK (ASCII, LF, the railway.learning.json form + app/services/compare_runs.py in watchPatterns).
- bytes > 127 = 0 and CR = 0 in every new file; git diff --stat: hunks only (+4 / +2 / +2 on the routes, CLAUDE.md +7 -1, CRLF kept on every edited file).
- 64-hex literal: none; keyword-named constant beside a hex literal: none; added-line sweep (@gmail, +973, 8-digit runs, sk-, eyJ): no hit.
- Corpus gate (GC-8): scripts/verify_flag_byte_identity.py --proof-root .../sc-scraper-proof/_proof --flags ENABLE_COMPARE_RUN_LEDGER: base (scratch worktree) and HEAD both "RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656", OVERALL SHA256 b39211c74dae1eb6cfc33bc56d8006b693909a01bbe474affbb562b9c0384935: EQUAL.
- Fourteen client fences by path (node v24.11.1, jest 29.7.0, from sc-s81-s22/SmartCompareApp through the orchestrator's junction, untouched; timeout 1800): [jest] tag=s22g-fences start=17:57:25 end=17:57:31: Test Suites 1 failed, 13 passed, 14 total; Tests 4 failed, 236 passed = exactly the four config/nativeBundle.w37 drift nodes (d5, k2, k4, k5).
- Box discipline: every pytest waited on a PowerShell probe for a foreign `-m pytest` process; none was killed; no DUPLICATE tag.

## 5. Files (sha256 over the bytes on disk after the commit)
| path | sha256 |
|---|---|
| CLAUDE.md | f713d6ab9f31a6ce02d261a1aa5a811b469eb6c66ce3a363619c91187c17eddc |
| app/api/image_routes.py | 5eac7998c6ace9db87b009848ddb385436c95f84cf5e9d83a83930b252337ae8 |
| app/api/text_routes.py | f6540988d8185a0387659a59ff8eac6953ebbdde1b5f101a1ac60bc1c5a6b5ba |
| app/api/url_routes.py | 0c83d2d265c2a13cc5824ee609ab61108859ad0c8b36393976328d31cca5197b |
| app/services/compare_runs.py | 3113b7af65328d3a64c9284a4c4ecb57bed5833625c1f0a9f37a420007cf4159 |
| migrations/048_compare_runs.sql | 91e931875ac533482226265496c81e7c09ef9de715430d6fbbb2d5ee7448e634 |
| migrations/rollback/048_compare_runs.sql | f9bc4451502b5bf5e917bd2eb9ed819cc430634d480403d28e203cfc191090bb |
| railway.judge.json | 347ad7ab37b7dc295c82c570d13ea955ced4e2c8a8cc4739b7c331fc6d240c69 |
| scripts/cron_compare_judge.py | 7a917293cd7e6cbf418e39e86a80af7c28867d6a6939060c53459a16d77ae276 |
| tests/test_migration_043_delete_user_cascade.py | ad72b0cd221eceb46632a2276dd65c0b20056a9c3d7298a20909185af20ed55d |
| tests/test_s81_kb_schema.py | 60a0da0b5dcd47d69340c19c71a78c7e85c5e922ce07ab4eb2840d108888e2c5 |
| tests/test_s81_s05_request_context.py | c5e36dc54ea0e3448a64a09d08cc767c57c1aa54410a336a7e968244adae047b |
| tests/test_s81_s22_compare_runs.py | c1cb93752908c061beacb01ca47968ecd7026af8581bc5bca4220fc894c52a52 |
| tests/test_s81_s22_gate_rows.py | 6f5463b9a0de5e4d32e526f8d24bef5ea4da33bdd02515aca9b6945ba6fc4e51 |
| tests/test_s81_s22_judge.py | 39a46d1c574ecf5e8403f5037c7f611ca142d4e1bbcbbc2655f6677556ea2199 |

Notes folder (S81-22_green/): PR_BODY.md (13.8 KB, ASCII except the 4-byte robot emoji of the required attribution line), APPLY_048_1_PRECHECK.sql / APPLY_048_2_ONE_PASTE.sql (byte-identical to 048, sha256 91e93187...) / APPLY_048_3_POSTCHECK.sql under apply/, gen048.py (the 048 generator: the cascade text derived from 043's own bytes), gr_mutate.py + gr_mutants.tsv, base_driver.py / head_driver.py / finish_record.py, HEAD_COMM_SET.txt, head_failed.txt, base_chunks/, head_chunks/, logs/.

## 6. Deviations and choices (each stated)
- D1 GC-5 guard: implemented as array_agg over information_schema.columns (names only) per table compared with @> and <@ to the exact created column set; no bare exists raise (pinned by G22-GR2); every RAISE starts '048 guard:'.
- D2 E4 added (the consumer census went red, as the brief foresaw); the leaf alias is `_request_context` (the pinned import shape), not `_rc`.
- D3 the camera line is one long line (+2 for image_routes per GC-13) with `extra_records=vision_ledger`.
- D4 base record: chunk membership = the RED's chunks minus the SF1-held members (per-file reuse outright and the same chunk boundaries); the RED's c00-c03 logs were not reused (no [pyt] status line in the .log; the lines live only in progress.txt).
- D5 judge vs the prototype: the prior-judgement read moved inside the guarded read block (a 42P01 there is counted, return 0); the Riyadh midnight is computed from the breaker's day key and RIYADH_UTC_OFFSET_HOURS instead of from the key expiry; the batch / prune steps are factored into helpers; behaviour otherwise as the frozen rows pin it.
- D6 compare_runs `_llm_calls`: an extra record that already carries a non-openai `provider` passes through as a record (the Anthropic record shape, R-S22-39); OpenAI ledger entries map through openai_entry_record; de-duplication by object identity.
- D7 trailer: Opus 5.5 (the agent's own model), not the brief template's Fable 5.1.
- D8 PR body: the required final attribution line carries the 4-byte emoji; everything else ASCII.

## 7. Open questions for the gate
- Q1 the S81-03 isolation pins i2 / i6 go red only with ENABLE_COMPARE_RUN_LEDGER exported (they count llm_pricing calls; compare_runs reads the ledger through llm_pricing). CI runs flags unset (green). Rule whether a later flip-window unit amends those pins or whether it stays a stated observation.
- Q2 the SF1 lane's E1 edit of the same reserved tuple: the second rebase unions to ("051",) by hand (GC-3).

## 8. NOT MEASURED
- Nothing in the gate list. Not run by design: tests/test_precommit_hook*.py (no .githooks change), the FULL jest suite (LC-7).
