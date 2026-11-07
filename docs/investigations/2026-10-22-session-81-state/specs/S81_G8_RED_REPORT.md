# S81-G8 RED REPORT (B1b URL-TELEMETRY + S81-11b RESULT-AGGREGATES + S81-18b STORE-LABEL)

Agent: Opus 5.5 (claude-opus-5-5), 2026-11-07 06:25-07:20 AST. Base daf86d32d222a885c42dc537e83c25483527a83b (origin/main after #393).
Real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g8 (detached at the base; only the four new files untracked).
Spec .qa-s80/S81-G8_UNIT_SPEC.md (sha 1005724c...) as amended by RULINGS_S81_G8 R-G8-1..13. Written through the shell (the harness refuses a subagent Write of a report .md).

## 1. Files written (real worktree, new, untracked)
| file | sha256 | bytes |
|---|---|---|
| tests/test_s81_b1b_url_telemetry.py | 7dc7f8aa9f79ba0d241bfebf9ce5486c1f0a307f75b53741ac82d666355cee71 | 16498 |
| tests/test_s81_s11b_result_aggregates.py | 957020e30f9a88358c43e00db3fd4293b98271d3c3cb6c483bbae8c3ef4a0cf0 | 15346 |
| tests/test_s81_s18b_store_label.py | 4fc4b3996834e09626a712aa68d88319f5139414aac845ee2d9511123b048adf | 19577 |
| tests/fixtures/s81_g8_flag_off_golden.json | 497754da580815222767a5138226cf2d16bc2e981bcac3dff462ea86fc15eb8f | 219028 |
All four: bytes > 127 = 0, CR = 0 (checked after every write); ruff E9,F63,F7,F82 clean on the three test files; no constant named with a gitleaks keyword; synthetic hosts only.

## 2. Rows and node counts
- B1b (tests/test_s81_b1b_url_telemetry.py): RED R1 keyword, R2 bh JSON-LD pair tags, R3 ae pair tags, R4 string ratings only, R5 same identity, R6 URL route tags (through tests.test_s80_b1._url = the r18 harness over tests.test_paid_route_metering._stub_url_leaves / _post_compare), R7 compare_runs.build_run_row over the bh URL envelope with input_type url (R-G8-3); PIN P1 OFF x4 spellings x4 bodies x4 inputs (raising assess_result recorder), P2 text/text_stream/camera tags byte-equal on a body whose readings differ + call-shape recorder, P3 assess_result default values (20 bodies, literals measured at base), P4 url_gate_reason / result_gate_refusal(url_mode=True) unchanged, P5 URL body unstamped + strict price_showable_a/b (R-G8-2), P6 result_gate purity. 7 RED + 6 PIN = 13 nodes.
- S81-11b (tests/test_s81_s11b_result_aggregates.py): RED R1 reader, R2 helper (2 hosts, newest d-1, key order), R3 nulls / zero (R-G8-5), R4 builder kwarg + stamp (signature asserted first), R5 orchestrator REST + stream, R6 partial builder, R7 flag read first (raising kb_views list; one WARNING when the helper raises); PIN P1 the shared golden (4 OFF spellings x W4-13 {unset, true}, KB ON with both cards, B1 ON, the result gate ON; REST / stream / camera / REST lang ar; raising recorders on the helpers), P2 KB OFF = the S18 golden, P3 classify shapes. 7 RED + 3 PIN = 10 nodes.
- S81-18b (tests/test_s81_s18b_store_label.py): RED R1 leaf + reader, R2 the table shape (33-host seed, ASCII, sorted, normalised keys, KB_HOST_REGEX, no URL, no diacritic), R3 label_for (lang, www/port normalisation, url-host second lookup R-G8-7, fallback, None), R4 builder pass both surfaces + no mutation of the original price objects (exact gate false and true), R5 orchestrator KB slot 0 + live slot 1 (REST en, REST ar, stream ar, camera en), R6 partial lang from ctx, R7 fail-safe table (missing / invalid / diacritic: one WARNING per file state over two builds), R8 flag read first (raising LABELS_PATH OFF; one WARNING when label_prices raises); PIN P1 the shared golden, P2 classify price dict, P3 SSE prices frame OFF == ON. 8 RED + 3 PIN = 11 nodes.
- Totals: 22 RED + 12 PIN = 34 nodes (as briefed); P1 rows loop the OFF spellings inside one node.

## 3. At base (AssertionError proof)
- [pyt] tag=g8red-b1b-base1 start=2026-11-07 06:35:28 end=2026-11-07 06:35:34 elapsed=6s bound=600s status=FAIL rc=1  | 8 failed, 8 passed, 11 warnings in 4.44s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-base-units start=2026-11-07 06:39:09 end=2026-11-07 06:39:16 elapsed=7s bound=600s status=FAIL rc=1  | 22 failed, 12 passed, 11 warnings in 6.30s | [netguard] blocked 0 attempt(s) from 0 node(s)
- g8red-base-units: exactly the 22 RED nodes failed, the 12 PIN nodes passed; the log has 22 terminal `tests\...py:<line>: AssertionError` lines and no other exception type (no ImportError / AttributeError / TypeError / setup error). Missing symbols: getattr / find_spec / inspect.signature asserted first (11b R4 / R7 and 18b R4 / R7 / R8 assert the kwarg before any call carrying it; B1b R6 asserts the coverage tag before recomputing with url_mode).

## 4. The golden
tests/fixtures/s81_g8_flag_off_golden.json recorded at daf86d32 by `python -m tests.test_s81_s11b_result_aggregates <out.json>` (cwd = the real worktree, network blocked, dotenv neutralised; re-recordable only at a base sha). Recipe: for W4-13 ENABLE_SEARCH_LOG_TRUTH in {unset -> key truth_unset, true -> truth_true}: S18 _full_config(flag ENABLE_KB_FIRST_SERVE=true) + ENABLE_RESULT_STATUS_METADATA=true + ENABLE_RESULT_GATE=true, the S18 _CardClient with _card(P0) and _card_b(), scenarios rest_full / stream_full / camera_full (S18 VISION) / rest_ar (output_lang ar), each payload through S18 _normalize plus the live-leg call counts. Recorded twice: byte-identical (deterministic). Both W4-13 states produce equal scenarios; kb_hit [full, full], result_status supported_result, zero live legs. sha256 497754da580815222767a5138226cf2d16bc2e981bcac3dff462ea86fc15eb8f, 219,028 bytes, ASCII, LF, base field = daf86d32.

## 5. Prototype (scratch worktree <scratchpad>/g8p at daf86d32, detached, no junction; REMOVED, verified with git worktree list)
Diff saved: <scratchpad>/S81-G8_red/prototype.diff (13,647 B) + prototype_files/ (apply.py, store_labels.py, merchant_labels.json, app_services/ copies). `git diff --stat`: compare_runs.py 3 (+2 -1), kb_serve.py +34, response_builder.py +18, result_gate.py 26 (+18 -8), sentry_service.py 5 (+4 -1), structured_comparison_service.py +8; 6 files, 84 insertions, 10 deletions (hunks only, CRLF preserved) + NEW app/services/store_labels.py + data/merchant_labels.json (33 rows, AR = EN, ASCII, LF, sorted). CLAUDE.md not edited.
Hunks: result_gate _facts(url_mode) / _corroborated(url_mode) / assess_result(url_mode: bool = False) computing facts through _facts(..., url_mode=url_mode); sentry_service the one call with **({"url_mode": True} if input_type == "url" else {}); R-G8-3 hunk: compare_runs.build_run_row's _rg.assess_result call gains the same conditional kwarg (the known rebase seam with S81-22, nothing else); kb_serve result_aggregates_enabled + AGGREGATE_FIELDS + result_aggregates; response_builder two leaf imports, kwargs kb_views / output_lang, the stamp after the S81-20 block, the pass after the D08 block; scs kb_views= / output_lang= at the three call sites + the conditional output_lang entry in both _partial_build_ctx literals.
- [pyt] tag=g8red-proto-off start=2026-11-07 06:46:57 end=2026-11-07 06:47:03 elapsed=7s bound=600s status=FAIL rc=1  | 2 failed, 32 passed, 11 warnings in 5.89s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-proto-18b start=2026-11-07 06:47:23 end=2026-11-07 06:47:27 elapsed=4s bound=600s status=FAIL rc=1  | 1 failed, 1 passed, 9 deselected, 11 warnings in 3.26s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-proto-18b2 start=2026-11-07 06:47:38 end=2026-11-07 06:47:41 elapsed=4s bound=600s status=OK rc=0  | 1 passed, 10 deselected, 10 warnings in 2.65s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-proto-off2 start=2026-11-07 06:47:50 end=2026-11-07 06:47:55 elapsed=6s bound=600s status=OK rc=0  | 34 passed, 11 warnings in 4.96s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-proto-on start=2026-11-07 06:47:56 end=2026-11-07 06:48:02 elapsed=6s bound=600s status=OK rc=0  | 34 passed, 11 warnings in 5.07s | [netguard] blocked 0 attempt(s) from 0 node(s)
- proto-off (first run) showed two test defects, fixed in the RED file before the final runs (see deviations D2, D3); final: flags unset 34 passed (proto-off2), ENABLE_RESULT_STATUS_METADATA=true ENABLE_RESULT_AGGREGATES=true ENABLE_STORE_LABEL=true exported in the runner call 34 passed (proto-on).
- CI-order set of spec 12.1 at the prototype, flags unset (informational for R-G8-9: no existing pin reddens): [pyt] tag=g8red-ciorder-proto start=2026-11-07 06:59:14 end=2026-11-07 07:00:41 elapsed=87s bound=1200s status=FAIL rc=1  | 1 failed, 1716 passed, 18 warnings in 84.88s (0:01:24) | [netguard]   tests/test_hermeticity_pins.py::test_non_loopback_lookup_is_blocked_without_the_marker [egress] socket.getaddrinfo example.com:80 ; the one failure is s10 r06 (known CRLF environmental, also failing at base).

## 6. Mutation table (byte copies in the scratch worktree, .qa-mutation.lock, each mutant = one run of the three unit files, bound 600; restored and sha-verified after each, and proto_sha.txt re-verified OK after all 24)
| id | mutation | killed by (failing rows) | exception kinds |
|---|---|---|---|
| B1b-M1 | capture never passes url_mode | test_r2_bh_jsonld_pair_tags, test_r3_ae_jsonld_pair_tags, test_r4_string_ratings_only, test_r5_same_identity_keeps_needs_identification, test_r6_url_route_tags_follow_the_url_reading | AssertionError |
| B1b-M2 | url_mode=True for every input type | test_p2_text_camera_stream_tags_byte_equal | AssertionError |
| B1b-M3 | url_mode swaps the price reader only (ratings strict) | test_r4_string_ratings_only | AssertionError |
| B1b-M4 | url_mode swaps the rating reader only (price strict) | test_r2_bh_jsonld_pair_tags, test_r3_ae_jsonld_pair_tags, test_r5_same_identity_keeps_needs_identification, test_r6_url_route_tags_follow_the_url_reading, test_r7_compare_runs_row_follows_the_url_reading | AssertionError |
| B1b-M5 | _corroborated not url-aware | test_r2_bh_jsonld_pair_tags, test_r3_ae_jsonld_pair_tags | AssertionError |
| B1b-M6 | url_mode applied to the strict reading only | test_r2_bh_jsonld_pair_tags, test_r3_ae_jsonld_pair_tags | AssertionError |
| B1b-M7 | the default flipped (url_mode: bool = True) | test_p2_text_camera_stream_tags_byte_equal, test_p3_assess_result_default_unchanged, test_r1_assess_result_url_mode_keyword, test_r7_compare_runs_row_follows_the_url_reading | AssertionError |
| B1b-M8 | the compare_runs call never passes url_mode | test_r7_compare_runs_row_follows_the_url_reading | AssertionError |
| 11b-M1 | the stamp drops the flag read | test_p1_flag_off_golden_full_config, test_p2_kb_off_bodies_unchanged, test_r4_builder_stamps_under_the_flag, test_r7_flag_read_first | AssertionError |
| 11b-M2 | store_count = len(candidates) | test_r2_helper_hosts_and_newest, test_r3_helper_nulls_and_zero, test_r4_builder_stamps_under_the_flag, test_r5_orchestrator_rest_and_stream, test_r6_partial_builder_carries_it | AssertionError |
| 11b-M3 | price_checked_at = the OLDEST as_of | test_r2_helper_hosts_and_newest, test_r3_helper_nulls_and_zero, test_r4_builder_stamps_under_the_flag, test_r5_orchestrator_rest_and_stream | AssertionError |
| 11b-M4 | price_checked_at = candidates[-1] | test_r2_helper_hosts_and_newest, test_r3_helper_nulls_and_zero, test_r4_builder_stamps_under_the_flag, test_r5_orchestrator_rest_and_stream | AssertionError |
| 11b-M5 | a miss view counted as 0 instead of null | test_r3_helper_nulls_and_zero | AssertionError |
| 11b-M6 | the stream call site does not pass kb_views | test_r5_orchestrator_rest_and_stream | AssertionError |
| 11b-M7 | the partial site does not pass kb_views | test_r6_partial_builder_carries_it | AssertionError |
| 11b-M8 | the flag read after result_aggregates(kb_views) | test_p1_flag_off_golden_full_config, test_p2_kb_off_bodies_unchanged, test_r7_flag_read_first | AssertionError,RuntimeError |
| 18b-M1 | the pass drops the flag read | test_p1_flag_off_golden_full_config, test_p2_kb_off_bodies_unchanged, test_r4_builder_pass_both_surfaces, test_r8_flag_read_first | AssertionError |
| 18b-M2 | the fallback is None instead of the retailer | test_r3_label_for_lookup_and_lang, test_r7_fail_safe_table | AssertionError |
| 18b-M3 | lang ignored (always en) | test_r3_label_for_lookup_and_lang, test_r4_builder_pass_both_surfaces, test_r5_orchestrator_kb_and_live, test_r6_partial_builder_lang_from_ctx | AssertionError |
| 18b-M4 | the key not normalised (raw retailer lookup) | test_r3_label_for_lookup_and_lang | AssertionError |
| 18b-M5 | only products[i] labelled (overview missed) | test_r4_builder_pass_both_surfaces, test_r5_orchestrator_kb_and_live, test_r6_partial_builder_lang_from_ctx, test_r7_fail_safe_table | AssertionError |
| 18b-M6 | the price object mutated in place | test_r4_builder_pass_both_surfaces | AssertionError |
| 18b-M7 | the partial site passes no lang | test_r6_partial_builder_lang_from_ctx | AssertionError |
| 18b-M8 | the diacritic check dropped from the table validation | test_r7_fail_safe_table | AssertionError |
24 / 24 KILLED, 0 survivors, no equivalence ruling needed. 11b-M8 (the helper called before the flag read) kills P1 / P2 by AssertionError (the raising recorder) and R7's OFF half by the raising kb_views (RuntimeError).
Mutant [pyt] lines (tags g8red-<id>): g8red-b1b-m1 FAIL 7s; g8red-b1b-m2 FAIL 7s; g8red-b1b-m3 FAIL 7s; g8red-b1b-m4 FAIL 7s; g8red-b1b-m5 FAIL 7s; g8red-b1b-m6 FAIL 7s; g8red-b1b-m7 FAIL 6s; g8red-b1b-m8 FAIL 7s; g8red-11b-m1 FAIL 7s; g8red-11b-m2 FAIL 7s; g8red-11b-m3 FAIL 7s; g8red-11b-m4 FAIL 6s; g8red-11b-m5 FAIL 7s; g8red-11b-m6 FAIL 7s; g8red-11b-m7 FAIL 7s; g8red-11b-m8 FAIL 8s; g8red-18b-m1 FAIL 9s; g8red-18b-m2 FAIL 7s; g8red-18b-m3 FAIL 10s; g8red-18b-m4 FAIL 7s; g8red-18b-m5 FAIL 7s; g8red-18b-m6 FAIL 7s; g8red-18b-m7 FAIL 7s; g8red-18b-m8 FAIL 7s

## 7. Corpus gate (scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_RESULT_AGGREGATES,ENABLE_STORE_LABEL,ENABLE_RESULT_STATUS_METADATA, in the scratch worktree, never beside a pytest)
- base (before the edits): OVERALL SHA256 200474dfcecf2bcc625eb66b3c3fbe65a4a66f2d35b51037aaf5a6b13351dc3f
- prototype HEAD (every flag OFF): OVERALL SHA256 200474dfcecf2bcc625eb66b3c3fbe65a4a66f2d35b51037aaf5a6b13351dc3f
- EQUAL (measured). Logs: S81-G8_red/corpus_base.log, corpus_head.log.

## 8. Comm set (R-G8-11) and the base record
Re-derived ONCE at daf86d32 by the spec's comm.py run read-only over the real worktree with app.services.compare_runs and app.services.store_labels added to EDITED_MODS, store_labels to the symbols, and the three G8 RED files excluded (HEAD-only): <scratchpad>/S81-G8_red/comm_red.py. Result 712 files (COMM_SET.txt, sorted LF list sha256 ea0d2f1beeeec1668aae965d6514dd51ce0d3771919fd9d5b888f08c049b46f5), closure 110 modules (the spec's 104 + compare_runs, store_labels, scripts.cron_compare_judge, and push_service / referral_service / scripts.cron_expire_bonuses which now import a closure module after SF1). vs the spec's 700: 0 removed, 12 added:
  - tests/test_push_service.py
  - tests/test_referral_full_response_column.py
  - tests/test_referral_loop2.py
  - tests/test_referral_service.py
  - tests/test_referral_service_internals.py
  - tests/test_referral_share_status_lifetime.py
  - tests/test_s81_s22_compare_runs.py
  - tests/test_s81_s22_gate_rows.py
  - tests/test_s81_s22_judge.py
  - tests/test_s81_sf1_gate_rows.py
  - tests/test_s81_sf1_surfaces_be.py
  - tests/test_u3c_referral_push_name.py
The named source-scanning pins (test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69) are members (forced list); the CLAUDE.md readers by the import graph are members; data/ readers: none at daf86d32 beyond the spec's measurement (no backend test walks data/); SmartCompareApp-scanning backend tests joined through the source / walker reasons; the four test_precommit_hook*.py files EXCLUDED and NOT RUN (no .githooks change). Per-file reasons: comm_reasons.tsv (member, union reasons, reuse source / run reasons).
Base record (LC-6, GC-9 per-file reuse) STORED: <scratchpad>/harness/base_records/daf86d32d222a885c42dc537e83c25483527a83b/ea0d2f1beeeec1668aae965d6514dd51ce0d3771919fd9d5b888f08c049b46f5.{files,header.txt,txt,pyt.log} (complete, not PARTIAL):
- REUSED from 05ccaed2/48158306... : 501 members (8 FAILED ids carried); REUSED from 18cb9e04 records: 2 members (0 FAILED); RUN at daf86d32 in the real worktree: 209 members (reasons: app.main / app.api / TestClient user 160, walker 41, CLAUDE.md 33+, database_service / text_routes / image_routes / url_routes / referral / feedback / SmartCompareApp / compare_runs names, bytes changed 6 / 8, not in a record 8 / 5; full counts in the header), 9 chunks:
  - [pyt] tag=g8red-comm-c00 start=2026-11-07 07:03:17 end=2026-11-07 07:03:53 elapsed=36s bound=1200s status=FAIL rc=1  | 2 failed, 991 passed, 31 warnings in 34.29s | [netguard]   tests/test_bh_gcc_cascade_wiring.py::TestNewAdapterCascadeWiring::test_new_adapter_miss_falls_through [egress] socket.getaddrinfo api.openai.com:443
  - [pyt] tag=g8red-comm-c01 start=2026-11-07 07:03:53 end=2026-11-07 07:04:23 elapsed=30s bound=1200s status=OK rc=0  | 503 passed, 1 skipped, 8 deselected, 13 warnings in 28.83s | [netguard]   tests/test_category_selection.py::TestCategorySwitchingResponse::test_each_new_category_in_response [sentinel] socket.create_connection neutralized.supabase.invalid:443
  - [pyt] tag=g8red-comm-c02 start=2026-11-07 07:04:23 end=2026-11-07 07:05:39 elapsed=76s bound=1200s status=OK rc=0  | 749 passed, 18 warnings in 74.44s (0:01:14) | [netguard]   ... 1 more node(s) in the report
  - [pyt] tag=g8red-comm-c03 start=2026-11-07 07:05:39 end=2026-11-07 07:06:18 elapsed=39s bound=1200s status=OK rc=0  | 867 passed, 4 skipped, 5 deselected, 17 warnings in 37.72s | [netguard]   tests/test_referral_e2e.py::test_e2e_admin_referrals_dashboard_returns_metrics [sentinel] socket.create_connection neutralized.supabase.invalid:443
  - [pyt] tag=g8red-comm-c04 start=2026-11-07 07:06:18 end=2026-11-07 07:08:55 elapsed=157s bound=1200s status=OK rc=0  | 1053 passed, 263 warnings in 155.32s (0:02:35) | [netguard]   tests/test_referral_routes.py::TestPostInviteQuiz::test_route_is_registered [sentinel] socket.create_connection neutralized.supabase.invalid:443
  - [pyt] tag=g8red-comm-c05 start=2026-11-07 07:08:55 end=2026-11-07 07:10:48 elapsed=113s bound=1200s status=FAIL rc=1  | 6 failed, 3287 passed, 64 warnings in 110.76s (0:01:50) | [netguard]   tests/test_s81_s04_spend_breaker.py::test_p08_on_with_headroom_changes_no_response_field [sentinel] socket.create_connection neutralized.supabase.invalid:443
  - [pyt] tag=g8red-comm-c06 start=2026-11-07 07:10:48 end=2026-11-07 07:12:14 elapsed=86s bound=1200s status=FAIL rc=1  | 8 failed, 2819 passed, 45 warnings in 83.83s (0:01:23) | [netguard]   tests/test_s81_s20_result_gate.py::test_r34_g3_tail_identity_classes[same] [sentinel] socket.create_connection neutralized.supabase.invalid:443
  - [pyt] tag=g8red-comm-c07 start=2026-11-07 07:12:14 end=2026-11-07 07:13:30 elapsed=75s bound=1200s status=OK rc=0  | 897 passed, 10 deselected, 19 warnings in 72.50s (0:01:12) | [netguard]   ... 26 more node(s) in the report
  - [pyt] tag=g8red-comm-c08 start=2026-11-07 07:13:30 end=2026-11-07 07:14:00 elapsed=30s bound=1200s status=OK rc=0  | 576 passed, 9 skipped, 35 xfailed, 12 warnings in 28.79s | [netguard]   tests/test_w49_extraction_catch_redaction.py::test_r2c_share_payload_carries_no_raw_text [sentinel] socket.create_connection neutralized.supabase.invalid:443
- Base FAILED set = 24 ids: the 22 known environmental ones + 2 S81-22 CRLF working-copy hygiene rows recorded identically at base (tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf on migrations/048_compare_runs.sql; tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first on railway.judge.json: `b'\r' not in <bytes>` of the CRLF working copy).
  run-measured:
    tests/test_auth_interceptor.py::test_sign_in_with_social_exception
    tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
    tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
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
    tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
    tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
  reused:
    tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
    tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
    tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
    tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
    tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
    tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
    tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
    tests/test_s81_s19_gap_queue.py::test_r15_hygiene

## 9. Other base gates
- [pyt] tag=g8red-ciorder-base start=2026-11-07 07:00:48 end=2026-11-07 07:02:12 elapsed=84s bound=1200s status=FAIL rc=1  | 23 failed, 1694 passed, 18 warnings in 81.94s (0:01:21) | [netguard]   tests/test_hermeticity_pins.py::test_non_loopback_lookup_is_blocked_without_the_marker [egress] socket.getaddrinfo example.com:80
- [pyt] tag=g8red-secretscan-base start=2026-11-07 07:02:12 end=2026-11-07 07:02:19 elapsed=7s bound=600s status=OK rc=0  | 31 passed, 1 warning in 6.06s | [netguard] blocked 0 attempt(s) from 0 node(s)
- ciorder-base failures = the 22 RED nodes + tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (known CRLF environmental). Fourteen client fences + b3a/nativeStrings NOT run (GREEN's, through the orchestrator's junction). The four hook test files NOT RUN (no .githooks change).

## 10. Deviations from the spec (rows adjusted, reasons)
- D1 (11b / 18b counts): the P1 rows loop the OFF spellings (and W4-13 states) inside ONE node each, and B1b R2 / R3 are two functions, so the node count is exactly 22 RED / 12 PIN = 34 as briefed (spec rows map 1:1 to nodes).
- D2 (18b R4): the spec's 'the input product_data price objects carry no store_label' is asserted on the ORIGINAL price objects captured before the build. With ENABLE_EXACT_PRICE_GATE false the builder's products[i] IS the input product dict, so the contract's `products[i]["price"] = {**price, "store_label": ...}` (a new price dict, as the spec prescribes) rebinds the price key on the caller's product dict; the price OBJECT is never mutated (M6 is killed by this row). GREEN should know the product dict is shared under exact-gate OFF (base behaviour, not introduced here).
- D3 (18b R5): the spec's slot-1 live price (amount 9.5, source_method page_scrape) is PENDED by the exact-price chokepoint under the S18 identity (retailer None, reason pending_genuine), so no label could be asserted; the row uses the S18 harness's own live shape (amount 55.0, source_method local_bhd, title x) with retailer store-b.example.com and url https://store-b.example.com/p/1, and asserts the retailer pair [store-a, store-b] before the labels.
- D4 (B1b P2): the spec says the lane1 tomford_vs_creed body; the BUILT body pends both prices (pending_genuine), so P2 uses the raw lane1 response (prices with source_method, which the row strips) to keep the two readings different; P3's lane1 entries use the built bodies (tests.test_s80_b1._build_row) with the measured base literals.
- D5 (B1b R7, R-G8-3): beside the URL row it also asserts input_type text keeps partial_no_winner / 0 on the same envelope (so the hunk is conditional); winner_supported True is asserted with the status.
- D6 (comm set): 712 files, not 700: the 12 additions above (the S81-22 importers named by the brief + SF1's referral / push closure growth).
- No existing pin reddened on the prototype (R-G8-9): the CI-order set at the prototype shows only the known s10 r06. The new flags are not in the FY UNIT_ENV (untouched).

## 11. Open questions for the gate
- Q1: D2: is rebinding products[i]["price"] on a product dict shared with product_data (exact gate OFF) acceptable, or should label_prices copy the product dict too? (The spec's M6 targets the price object only; the prototype follows the spec.)
- Q2: the base record counts the two S81-22 CRLF rows as environmental base failures; GREEN's comm -13 treats them as base noise.

## 12. Restore check
- Real worktree: HEAD daf86d32 (unchanged), `git status --short` = exactly the four new files (?? tests/fixtures/s81_g8_flag_off_golden.json, ?? tests/test_s81_b1b_url_telemetry.py, ?? tests/test_s81_s11b_result_aggregates.py, ?? tests/test_s81_s18b_store_label.py); no tracked file modified (git diff empty). No git write in an existing worktree.
- Scratch worktree <scratchpad>/g8p removed with `git worktree remove --force`; `git worktree list` shows no g8p entry; the directory is gone. No orphan pytest of mine (every runner call returned; the mutation lock removed).
- No flag set in any .env or the OS environment; flags exported only in the runner call of proto-on; no .env read; no network; no package manager.

## 13. Every [pyt] line (from the harness ledger, tags g8red-*)
- [pyt] tag=g8red-b1b-base1 start=2026-11-07 06:35:28 end=2026-11-07 06:35:34 elapsed=6s bound=600s status=FAIL rc=1  | 8 failed, 8 passed, 11 warnings in 4.44s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-base-units start=2026-11-07 06:39:09 end=2026-11-07 06:39:16 elapsed=7s bound=600s status=FAIL rc=1  | 22 failed, 12 passed, 11 warnings in 6.30s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-proto-off start=2026-11-07 06:46:57 end=2026-11-07 06:47:03 elapsed=7s bound=600s status=FAIL rc=1  | 2 failed, 32 passed, 11 warnings in 5.89s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-proto-18b start=2026-11-07 06:47:23 end=2026-11-07 06:47:27 elapsed=4s bound=600s status=FAIL rc=1  | 1 failed, 1 passed, 9 deselected, 11 warnings in 3.26s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-proto-18b2 start=2026-11-07 06:47:38 end=2026-11-07 06:47:41 elapsed=4s bound=600s status=OK rc=0  | 1 passed, 10 deselected, 10 warnings in 2.65s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-proto-off2 start=2026-11-07 06:47:50 end=2026-11-07 06:47:55 elapsed=6s bound=600s status=OK rc=0  | 34 passed, 11 warnings in 4.96s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-proto-on start=2026-11-07 06:47:56 end=2026-11-07 06:48:02 elapsed=6s bound=600s status=OK rc=0  | 34 passed, 11 warnings in 5.07s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-b1b-m1 start=2026-11-07 06:49:02 end=2026-11-07 06:49:09 elapsed=7s bound=600s status=FAIL rc=1  | 5 failed, 29 passed, 11 warnings in 6.39s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-b1b-m2 start=2026-11-07 06:49:09 end=2026-11-07 06:49:16 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 5.76s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-b1b-m3 start=2026-11-07 06:49:16 end=2026-11-07 06:49:23 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 5.70s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-b1b-m4 start=2026-11-07 06:49:23 end=2026-11-07 06:49:30 elapsed=7s bound=600s status=FAIL rc=1  | 5 failed, 29 passed, 11 warnings in 5.68s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-b1b-m5 start=2026-11-07 06:49:30 end=2026-11-07 06:49:36 elapsed=7s bound=600s status=FAIL rc=1  | 2 failed, 32 passed, 11 warnings in 5.65s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-b1b-m6 start=2026-11-07 06:49:36 end=2026-11-07 06:49:43 elapsed=7s bound=600s status=FAIL rc=1  | 2 failed, 32 passed, 11 warnings in 5.72s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-b1b-m7 start=2026-11-07 06:49:43 end=2026-11-07 06:49:50 elapsed=6s bound=600s status=FAIL rc=1  | 4 failed, 30 passed, 11 warnings in 5.65s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-b1b-m8 start=2026-11-07 06:49:50 end=2026-11-07 06:49:57 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 5.66s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-11b-m1 start=2026-11-07 06:49:57 end=2026-11-07 06:50:03 elapsed=7s bound=600s status=FAIL rc=1  | 5 failed, 29 passed, 11 warnings in 5.66s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-11b-m2 start=2026-11-07 06:50:03 end=2026-11-07 06:50:10 elapsed=7s bound=600s status=FAIL rc=1  | 5 failed, 29 passed, 11 warnings in 5.98s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-11b-m3 start=2026-11-07 06:50:10 end=2026-11-07 06:50:17 elapsed=7s bound=600s status=FAIL rc=1  | 4 failed, 30 passed, 11 warnings in 5.79s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-11b-m4 start=2026-11-07 06:50:17 end=2026-11-07 06:50:24 elapsed=6s bound=600s status=FAIL rc=1  | 4 failed, 30 passed, 11 warnings in 5.59s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-11b-m5 start=2026-11-07 06:50:24 end=2026-11-07 06:50:31 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 5.70s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-11b-m6 start=2026-11-07 06:50:31 end=2026-11-07 06:50:37 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 5.83s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-11b-m7 start=2026-11-07 06:50:38 end=2026-11-07 06:50:45 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 6.06s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-11b-m8 start=2026-11-07 06:50:45 end=2026-11-07 06:50:52 elapsed=8s bound=600s status=FAIL rc=1  | 4 failed, 30 passed, 11 warnings in 6.51s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-18b-m1 start=2026-11-07 06:50:52 end=2026-11-07 06:51:01 elapsed=9s bound=600s status=FAIL rc=1  | 5 failed, 29 passed, 11 warnings in 7.33s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-18b-m2 start=2026-11-07 06:51:01 end=2026-11-07 06:51:08 elapsed=7s bound=600s status=FAIL rc=1  | 2 failed, 32 passed, 11 warnings in 5.89s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-18b-m3 start=2026-11-07 06:51:08 end=2026-11-07 06:51:18 elapsed=10s bound=600s status=FAIL rc=1  | 4 failed, 30 passed, 11 warnings in 8.83s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-18b-m4 start=2026-11-07 06:51:18 end=2026-11-07 06:51:25 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 5.82s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-18b-m5 start=2026-11-07 06:51:25 end=2026-11-07 06:51:32 elapsed=7s bound=600s status=FAIL rc=1  | 4 failed, 30 passed, 11 warnings in 5.94s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-18b-m6 start=2026-11-07 06:51:32 end=2026-11-07 06:51:39 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 5.84s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-18b-m7 start=2026-11-07 06:51:39 end=2026-11-07 06:51:46 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 6.19s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-18b-m8 start=2026-11-07 06:51:46 end=2026-11-07 06:51:53 elapsed=7s bound=600s status=FAIL rc=1  | 1 failed, 33 passed, 11 warnings in 5.85s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-ciorder-proto start=2026-11-07 06:59:14 end=2026-11-07 07:00:41 elapsed=87s bound=1200s status=FAIL rc=1  | 1 failed, 1716 passed, 18 warnings in 84.88s (0:01:24) | [netguard]   tests/test_hermeticity_pins.py::test_non_loopback_lookup_is_blocked_without_the_marker [egress] socket.getaddrinfo example.com:80
- [pyt] tag=g8red-ciorder-base start=2026-11-07 07:00:48 end=2026-11-07 07:02:12 elapsed=84s bound=1200s status=FAIL rc=1  | 23 failed, 1694 passed, 18 warnings in 81.94s (0:01:21) | [netguard]   tests/test_hermeticity_pins.py::test_non_loopback_lookup_is_blocked_without_the_marker [egress] socket.getaddrinfo example.com:80
- [pyt] tag=g8red-secretscan-base start=2026-11-07 07:02:12 end=2026-11-07 07:02:19 elapsed=7s bound=600s status=OK rc=0  | 31 passed, 1 warning in 6.06s | [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=g8red-comm-c00 start=2026-11-07 07:03:17 end=2026-11-07 07:03:53 elapsed=36s bound=1200s status=FAIL rc=1  | 2 failed, 991 passed, 31 warnings in 34.29s | [netguard]   tests/test_bh_gcc_cascade_wiring.py::TestNewAdapterCascadeWiring::test_new_adapter_miss_falls_through [egress] socket.getaddrinfo api.openai.com:443
- [pyt] tag=g8red-comm-c01 start=2026-11-07 07:03:53 end=2026-11-07 07:04:23 elapsed=30s bound=1200s status=OK rc=0  | 503 passed, 1 skipped, 8 deselected, 13 warnings in 28.83s | [netguard]   tests/test_category_selection.py::TestCategorySwitchingResponse::test_each_new_category_in_response [sentinel] socket.create_connection neutralized.supabase.invalid:443
- [pyt] tag=g8red-comm-c02 start=2026-11-07 07:04:23 end=2026-11-07 07:05:39 elapsed=76s bound=1200s status=OK rc=0  | 749 passed, 18 warnings in 74.44s (0:01:14) | [netguard]   ... 1 more node(s) in the report
- [pyt] tag=g8red-comm-c03 start=2026-11-07 07:05:39 end=2026-11-07 07:06:18 elapsed=39s bound=1200s status=OK rc=0  | 867 passed, 4 skipped, 5 deselected, 17 warnings in 37.72s | [netguard]   tests/test_referral_e2e.py::test_e2e_admin_referrals_dashboard_returns_metrics [sentinel] socket.create_connection neutralized.supabase.invalid:443
- [pyt] tag=g8red-comm-c04 start=2026-11-07 07:06:18 end=2026-11-07 07:08:55 elapsed=157s bound=1200s status=OK rc=0  | 1053 passed, 263 warnings in 155.32s (0:02:35) | [netguard]   tests/test_referral_routes.py::TestPostInviteQuiz::test_route_is_registered [sentinel] socket.create_connection neutralized.supabase.invalid:443
- [pyt] tag=g8red-comm-c05 start=2026-11-07 07:08:55 end=2026-11-07 07:10:48 elapsed=113s bound=1200s status=FAIL rc=1  | 6 failed, 3287 passed, 64 warnings in 110.76s (0:01:50) | [netguard]   tests/test_s81_s04_spend_breaker.py::test_p08_on_with_headroom_changes_no_response_field [sentinel] socket.create_connection neutralized.supabase.invalid:443
- [pyt] tag=g8red-comm-c06 start=2026-11-07 07:10:48 end=2026-11-07 07:12:14 elapsed=86s bound=1200s status=FAIL rc=1  | 8 failed, 2819 passed, 45 warnings in 83.83s (0:01:23) | [netguard]   tests/test_s81_s20_result_gate.py::test_r34_g3_tail_identity_classes[same] [sentinel] socket.create_connection neutralized.supabase.invalid:443
- [pyt] tag=g8red-comm-c07 start=2026-11-07 07:12:14 end=2026-11-07 07:13:30 elapsed=75s bound=1200s status=OK rc=0  | 897 passed, 10 deselected, 19 warnings in 72.50s (0:01:12) | [netguard]   ... 26 more node(s) in the report
- [pyt] tag=g8red-comm-c08 start=2026-11-07 07:13:30 end=2026-11-07 07:14:00 elapsed=30s bound=1200s status=OK rc=0  | 576 passed, 9 skipped, 35 xfailed, 12 warnings in 28.79s | [netguard]   tests/test_w49_extraction_catch_redaction.py::test_r2c_share_payload_carries_no_raw_text [sentinel] socket.create_connection neutralized.supabase.invalid:443
