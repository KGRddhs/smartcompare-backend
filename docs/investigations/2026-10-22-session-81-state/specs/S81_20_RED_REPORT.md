# S81-20 RED REPORT (B2-RESULT-GATE-V2, ENABLE_RESULT_GATE) - RED agent, Opus 5.5, 2026-11-05

Base 6869a3e655805afd3adbba43f99578dd79585934. Real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s20 (HEAD == base; git status: only `?? tests/test_s81_s20_result_gate.py`). Written through the shell (python), per the harness rule.

## RED file
- tests/test_s81_s20_result_gate.py: sha256 13aa83ade66d14759278e6da14668f60d48dabdcb1002b4d7bb29c0a88c0180c, 72464 bytes, pure ASCII (0 bytes > 127), LF (0 CRLF), ruff E9/F63/F7/F82 clean. No hex literal and no constant named with a gitleaks keyword; the device fingerprint is built at run time (_fp(); the S81-09 FP is imported).
- 80 test functions / 166 nodes: 59 RED functions (122 nodes), 21 PIN functions (44 nodes).
- Base run (real worktree): [pyt] tag=s20red-base-unit start=2026-11-05 09:20:02 end=2026-11-05 09:20:16 elapsed=14s bound=600s status=FAIL rc=1 ; 122 failed, 44 passed. Every failure an AssertionError (classify.py: 120 parsed sections AssertionError; the two ' TRUE ' param nodes read by hand: AssertionError); no ImportError / AttributeError / setup error; every PIN function green, every RED function red.
- RED nodes failing at base (122):
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table[' TRUE ']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['0']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['1']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['On']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['false']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['garbage']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['no']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['off']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['true']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table['yes']
  - tests/test_s81_s20_result_gate.py::test_r01_flag_reader_table[None]
  - tests/test_s81_s20_result_gate.py::test_r02_constants
  - tests/test_s81_s20_result_gate.py::test_r03_gate_reason_lane1_supported[fashion]
  - tests/test_s81_s20_result_gate.py::test_r03_gate_reason_lane1_supported[grocery]
  - tests/test_s81_s20_result_gate.py::test_r03_gate_reason_lane1_supported[haircare]
  - tests/test_s81_s20_result_gate.py::test_r03_gate_reason_lane1_supported[iphone15_vs_galaxys24]
  - tests/test_s81_s20_result_gate.py::test_r03_gate_reason_lane1_supported[makeup]
  - tests/test_s81_s20_result_gate.py::test_r03_gate_reason_lane1_supported[now_vs_solgar]
  - tests/test_s81_s20_result_gate.py::test_r03_gate_reason_lane1_supported[other]
  - tests/test_s81_s20_result_gate.py::test_r03_gate_reason_lane1_supported[skincare]
  - tests/test_s81_s20_result_gate.py::test_r03_gate_reason_lane1_supported[tomford_vs_creed]
  - tests/test_s81_s20_result_gate.py::test_r04_v09_placeholder
  - tests/test_s81_s20_result_gate.py::test_r05_same_identity
  - tests/test_s81_s20_result_gate.py::test_r06_category
  - tests/test_s81_s20_result_gate.py::test_r07_corpus
  - tests/test_s81_s20_result_gate.py::test_r08_mapping_completeness
  - tests/test_s81_s20_result_gate.py::test_r09_totality
  - tests/test_s81_s20_result_gate.py::test_r10_url_gate_synthetic
  - tests/test_s81_s20_result_gate.py::test_r11_url_string_reading[1e400]
  - tests/test_s81_s20_result_gate.py::test_r11_url_string_reading[abc]
  - tests/test_s81_s20_result_gate.py::test_r11_url_string_reading[arabic_indic]
  - tests/test_s81_s20_result_gate.py::test_r11_url_string_reading[bool]
  - tests/test_s81_s20_result_gate.py::test_r11_url_string_reading[long]
  - tests/test_s81_s20_result_gate.py::test_r11_url_string_reading[nan]
  - tests/test_s81_s20_result_gate.py::test_r11_url_string_reading[neg]
  - tests/test_s81_s20_result_gate.py::test_r11_url_string_reading[zero]
  - tests/test_s81_s20_result_gate.py::test_r12_url_one_sided
  - tests/test_s81_s20_result_gate.py::test_r13_camera_gate_table
  - tests/test_s81_s20_result_gate.py::test_r14_camera_snapshot
  - tests/test_s81_s20_result_gate.py::test_r15_camera_features_ignored
  - tests/test_s81_s20_result_gate.py::test_r16_refusal_body_shape
  - tests/test_s81_s20_result_gate.py::test_r17_refusal_flag_first
  - tests/test_s81_s20_result_gate.py::test_r18_log_message
  - tests/test_s81_s20_result_gate.py::test_r20_text_post_v09_refused[w413_off]
  - tests/test_s81_s20_result_gate.py::test_r20_text_post_v09_refused[w413_on]
  - tests/test_s81_s20_result_gate.py::test_r21_text_get_v07_refused
  - tests/test_s81_s20_result_gate.py::test_r22_text_post_v10_no_evidence
  - tests/test_s81_s20_result_gate.py::test_r23_real_orchestrator_v10
  - tests/test_s81_s20_result_gate.py::test_r24_real_orchestrator_v10_both_flags
  - tests/test_s81_s20_result_gate.py::test_r25_category_conflict_b2_alone
  - tests/test_s81_s20_result_gate.py::test_r26_category_conflict_both_flags
  - tests/test_s81_s20_result_gate.py::test_r27_supported_real_orchestrator_stamp
  - tests/test_s81_s20_result_gate.py::test_r28_anonymous_text_refusal
  - tests/test_s81_s20_result_gate.py::test_r29_hard_cap_partials
  - tests/test_s81_s20_result_gate.py::test_r30_device_quota_keys[image]
  - tests/test_s81_s20_result_gate.py::test_r30_device_quota_keys[text_get]
  - tests/test_s81_s20_result_gate.py::test_r30_device_quota_keys[text_post]
  - tests/test_s81_s20_result_gate.py::test_r30_device_quota_keys[text_stream]
  - tests/test_s81_s20_result_gate.py::test_r30_device_quota_keys[url_post]
  - tests/test_s81_s20_result_gate.py::test_r30b_stream_no_fingerprint_stash
  - tests/test_s81_s20_result_gate.py::test_r31_fragrance_gate_counts_result_gate_refusal
  - tests/test_s81_s20_result_gate.py::test_r32_text_info_line[get]
  - tests/test_s81_s20_result_gate.py::test_r32_text_info_line[post]
  - tests/test_s81_s20_result_gate.py::test_r32_text_info_line[url]
  - tests/test_s81_s20_result_gate.py::test_r33_g3_tail_no_evidence
  - tests/test_s81_s20_result_gate.py::test_r34_g3_tail_identity_classes[conflict]
  - tests/test_s81_s20_result_gate.py::test_r34_g3_tail_identity_classes[same]
  - tests/test_s81_s20_result_gate.py::test_r35_refusal_counted_on_budget[camera]
  - tests/test_s81_s20_result_gate.py::test_r35_refusal_counted_on_budget[stream]
  - tests/test_s81_s20_result_gate.py::test_r35_refusal_counted_on_budget[text_get]
  - tests/test_s81_s20_result_gate.py::test_r35_refusal_counted_on_budget[text_post]
  - tests/test_s81_s20_result_gate.py::test_r35_refusal_counted_on_budget[url]
  - tests/test_s81_s20_result_gate.py::test_r36_refusal_budget_spent_keeps_credit[camera]
  - tests/test_s81_s20_result_gate.py::test_r36_refusal_budget_spent_keeps_credit[stream]
  - tests/test_s81_s20_result_gate.py::test_r36_refusal_budget_spent_keeps_credit[text_get]
  - tests/test_s81_s20_result_gate.py::test_r36_refusal_budget_spent_keeps_credit[text_post]
  - tests/test_s81_s20_result_gate.py::test_r36_refusal_budget_spent_keeps_credit[url]
  - tests/test_s81_s20_result_gate.py::test_r37_refusal_gate_off_refunded_uncounted[camera]
  - tests/test_s81_s20_result_gate.py::test_r37_refusal_gate_off_refunded_uncounted[stream]
  - tests/test_s81_s20_result_gate.py::test_r37_refusal_gate_off_refunded_uncounted[text_get]
  - tests/test_s81_s20_result_gate.py::test_r37_refusal_gate_off_refunded_uncounted[text_post]
  - tests/test_s81_s20_result_gate.py::test_r37_refusal_gate_off_refunded_uncounted[url]
  - tests/test_s81_s20_result_gate.py::test_r40_stream_refusal_frames_and_accounting[w413_off]
  - tests/test_s81_s20_result_gate.py::test_r40_stream_refusal_frames_and_accounting[w413_on]
  - tests/test_s81_s20_result_gate.py::test_r41_stream_refusal_not_persisted_under_echo
  - tests/test_s81_s20_result_gate.py::test_r50_camera_same_identity
  - tests/test_s81_s20_result_gate.py::test_r51_camera_low_confidence[LOW1]
  - tests/test_s81_s20_result_gate.py::test_r51_camera_low_confidence[V04]
  - tests/test_s81_s20_result_gate.py::test_r52_camera_two_placeholders
  - tests/test_s81_s20_result_gate.py::test_r53_camera_one_placeholder_is_error[PH0]
  - tests/test_s81_s20_result_gate.py::test_r53_camera_one_placeholder_is_error[PH1]
  - tests/test_s81_s20_result_gate.py::test_r54_camera_enrichment_evasion[ENRICH]
  - tests/test_s81_s20_result_gate.py::test_r54_camera_enrichment_evasion[ENRICH_BRAND]
  - tests/test_s81_s20_result_gate.py::test_r55_camera_category_conflict_v2
  - tests/test_s81_s20_result_gate.py::test_r56_camera_v2_features_same_identity
  - tests/test_s81_s20_result_gate.py::test_r57_camera_anon_refund_keys
  - tests/test_s81_s20_result_gate.py::test_r59_camera_info_line
  - tests/test_s81_s20_result_gate.py::test_r60_camera_fragrance_gate_order
  - tests/test_s81_s20_result_gate.py::test_r61_camera_category_not_live_wins
  - tests/test_s81_s20_result_gate.py::test_r62_stream_error_then_refusal_terminal
  - tests/test_s81_s20_result_gate.py::test_r70_url_v09_refused[w413_off]
  - tests/test_s81_s20_result_gate.py::test_r70_url_v09_refused[w413_on]
  - tests/test_s81_s20_result_gate.py::test_r71_url_no_evidence
  - tests/test_s81_s20_result_gate.py::test_r72_url_same_identity
  - tests/test_s81_s20_result_gate.py::test_r73_url_info_line_and_v2_arm[url_v1]
  - tests/test_s81_s20_result_gate.py::test_r73_url_info_line_and_v2_arm[url_v2]
  - tests/test_s81_s20_result_gate.py::test_r80_envelope_passthrough
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity[' TRUE ']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['0']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['1']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['On']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['false']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['garbage']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['no']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['off']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['true']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity['yes']
  - tests/test_s81_s20_result_gate.py::test_r81_reader_and_vocab_parity[None]
  - tests/test_s81_s20_result_gate.py::test_r82_surface_reason_on
  - tests/test_s81_s20_result_gate.py::test_r90_builder_stamp_b2_alone
- PIN functions green at base: p00 (fixture statuses through the real assess_result), p01 (6 OFF spellings x W4-13 both, full config + the three recorders + the label sequence), p02, p03 (W4-13 both), p04, p05, p06 (OFF/ON), p07, p08, p09, p10, p11 (bh/ae/v03), p12, p13 (9 lane1), p14, p15, p16, p17, p18, p19 (R-S20-39: V1 stub conflict delivered), p20.

## Rows vs the spec (amended by RULINGS_S81_20)
R1-R18, R20-R29, R30 parametrized text_post / text_get / text_stream / url_post / image with ENABLE_DEVICE_DAILY_QUOTA ON through the S81-09 FakeRedis (R30 + R58 + R-S20-32: refund keys == consumed {daily, device_daily}, ONE DEVICE_REFUND_SCRIPT EVAL, lifetime 0, history 0), R30b (no-fingerprint STREAM: {daily} only, one refund EVAL over [daily] from the generator's finally, R-S20-32), R31 (re-cut by R-S20-38: counted once), R32 (param post / get / url, R-S20-35), R33, R34 (conflict / same), R35 / R36 / R37 (R-S20-38 counted / spent / gate OFF on text_post, text_get, stream, url, camera), R40, R41, R50-R57, R59, R60 (re-cut: counted once), R61 (R-S20-31 / M39), R62 (R-S20-33), R70-R73, R80-R82, R90; P1-P18 + P0 + P19 + P20. R55 is the V2-only conflict row (R-S20-39). R11 carries the Arabic-Indic digit case (R-S20-36). Anonymous rows (R28, R57) set ENABLE_COMPARE_AUTH_REQUIRED=false explicitly (R-S20-11).

## E-rows (GREEN's; anchors measured at 6869a3e6)
- E1 tests/test_s75_fanout_identity.py:60 UNIT_ENV
- E2 tests/test_retro_w2_1.py:173 _clean_flags (tuple :174-179, delenv :180)
- E3 tests/test_s71_u13_compare_auth_required.py:76 CLEAN_ENV
- E4 tests/test_paid_route_metering.py:244 _CLEAN_ENV
- E5 tests/test_w4_13_measurement_truth.py:154 _clean_flags (delenv :160)
- E6 tests/test_s80_b1.py:52 CLEAR
- E7 tests/test_s80_b3_vision_identity_v2.py:79 UNIT_ENV
- E8+ candidates: tests/test_s81_s03_llm_ledger_v2.py:102 UNIT_ENV; tests/test_s81_s06_anthropic_router.py:338-341 (inline delenv loop); tests/test_s81_s09_device_quota.py:97 CLEAN_ENV; tests/test_s81_s10_fragrance_gate.py:500 _CLEAR_ENV; tests/test_s81_s10_gate_rows.py:252 / :288; tests/test_s81_s10b_links_gate.py (no list; delenv lines :426 / :565 / :1052-1055 / :1183; a new line in its autouse fixture); tests/test_s81_s18_kb_first_serve.py:82 CLEARED_ENV. Not swept here (GREEN's local-.env sweep, R-S20-27).

## Prototype (scratch worktree <scratchpad>/s20p, detached at 6869a3e6, backend-only, no junction; REMOVED with git worktree remove --force, absent from git worktree list)
- Diff S81-20_red/prototype.diff (29304 B); files S81-20_red/prototype_files/ (sha256 result_gate 9b510456..., response_builder 97558b83..., error_handler ef206fae..., text_routes d8c6dea4..., image_routes 0f4ac24e..., url_routes 000c6a6a...). git diff --stat content-only: image_routes 56, text_routes 86, url_routes 28, error_handler 15, response_builder 6, result_gate 176 (360+/7-), CRLF preserved. result_gate.py 0 bytes > 127, none of the P11 substrings; B1 P10/P11 on the prototype: [pyt] tag=s20red-proto-b1p11 start=2026-11-05 09:36:11 end=2026-11-05 09:36:21 elapsed=10s bound=600s status=OK rc=0 (4 passed).
- proto_apply.py. Design beyond the spec text: R-S20-38 at every refusal exit (fragrance gate ON: budget_state_async spent -> keep the credit; else record_refusal_async then refund; gate OFF untouched): text/stream via an async _result_gate_keeps_credit(request, user), URL on `gate_route is not None`, camera on _gate_on/_gate_subject; so _result_gate_exit is ASYNC. Camera categories per R-S20-39: V2 _category only on _is_product dicts, else None (no classify stub, no extraction_service import). _URL_NUMBER_RE with re.ASCII (R-S20-36). Camera via the module attribute _rg.camera_gate_reason (R-S20-30).
- Unit file on the prototype (flag unset): [pyt] tag=s20red-proto-on6 start=2026-11-05 09:19:40 end=2026-11-05 09:19:47 elapsed=7s bound=600s status=OK rc=0 (166 passed).
- With ENABLE_RESULT_GATE=true exported for the call: [pyt] tag=s20red-proto-flagtrue start=2026-11-05 09:21:46 end=2026-11-05 09:21:52 elapsed=7s bound=600s status=OK rc=0 (166 passed).
- Iterations on1..on5 (test-harness fixes only) under S81-20_red/proto_on*.log.

## Mutation table (byte copy, exact-once edit, whole unit file via pyt.py bound 600, restore, sha256 equal for all 47; mutation lock created and removed)
| id | mutant | file | result | failing nodes | first killers | [pyt] |
|---|---|---|---|---|---|---|
| M1 | flag read after the assessment in result_gate_refusal | app/services/result_gate.py | KILLED | 17 AssertionError | test_p01_off_text_post_v09_delivered[-w413_off], test_p01_off_text_post_v09_delivered[-w413_on], test_p01_off_text_post_v09_delivered[0-w413_off], test_p01_off_text_post_v09_delivered[0-w413_on] | [pyt] tag=s20red-M1 start=2026-11-05 09:24:29 end=2026-11-05 09:24:37 elapsed=8s bound=600s status=FAIL rc=1 |
| M2 | text refund moved below _surface_comparison_failure(refusal) | app/api/text_routes.py | KILLED | 13 AssertionError | test_r20_text_post_v09_refused[w413_off], test_r20_text_post_v09_refused[w413_on], test_r21_text_get_v07_refused, test_r22_text_post_v10_no_evidence | [pyt] tag=s20red-M2 start=2026-11-05 09:24:38 end=2026-11-05 09:24:53 elapsed=16s bound=600s status=FAIL rc=1 |
| M3 | stream S81-20 branch condition forced False | app/api/text_routes.py | KILLED | 7 AssertionError | test_r30_device_quota_keys[text_stream], test_r30b_stream_no_fingerprint_stash, test_r35_refusal_counted_on_budget[stream], test_r36_refusal_budget_spent_keeps_credit[stream] | [pyt] tag=s20red-M3 start=2026-11-05 09:24:54 end=2026-11-05 09:25:02 elapsed=8s bound=600s status=FAIL rc=1 |
| M4 | _result_gate_exit schedules save_comparison_and_track_cohort before raising | app/api/text_routes.py | KILLED | 15 AssertionError | test_r20_text_post_v09_refused[w413_off], test_r20_text_post_v09_refused[w413_on], test_r21_text_get_v07_refused, test_r22_text_post_v10_no_evidence | [pyt] tag=s20red-M4 start=2026-11-05 09:25:02 end=2026-11-05 09:25:13 elapsed=11s bound=600s status=FAIL rc=1 |
| M5 | the reason arm deleted in _surface_comparison_failure | app/api/text_routes.py | KILLED | 21 AssertionError | test_r20_text_post_v09_refused[w413_off], test_r20_text_post_v09_refused[w413_on], test_r21_text_get_v07_refused, test_r22_text_post_v10_no_evidence | [pyt] tag=s20red-M5 start=2026-11-05 09:25:13 end=2026-11-05 09:25:25 elapsed=12s bound=600s status=FAIL rc=1 |
| M6 | the error-handler block deleted | app/middleware/error_handler.py | KILLED | 21 AssertionError | test_r20_text_post_v09_refused[w413_off], test_r20_text_post_v09_refused[w413_on], test_r21_text_get_v07_refused, test_r22_text_post_v10_no_evidence | [pyt] tag=s20red-M6 start=2026-11-05 09:25:26 end=2026-11-05 09:25:48 elapsed=21s bound=600s status=FAIL rc=1 |
| M7 | the camera block not run before the compare (disabled pre-compare) | app/api/image_routes.py | KILLED | 17 AssertionError | test_r30_device_quota_keys[image], test_r35_refusal_counted_on_budget[camera], test_r36_refusal_budget_spent_keeps_credit[camera], test_r37_refusal_gate_off_refunded_uncounted[camera] | [pyt] tag=s20red-M7 start=2026-11-05 09:25:48 end=2026-11-05 09:25:58 elapsed=9s bound=600s status=FAIL rc=1 |
| M8 | gate_reason returns no_evidence when no reason maps | app/services/result_gate.py | KILLED | 26 AssertionError | test_p10_on_supported_text_delivered, test_p12_on_stream_supported_delivered, test_p13_on_lane1_all_delivered[fashion], test_p13_on_lane1_all_delivered[grocery] | [pyt] tag=s20red-M8 start=2026-11-05 09:25:58 end=2026-11-05 09:26:22 elapsed=23s bound=600s status=FAIL rc=1 |
| M9 | text refund without keys | app/api/text_routes.py | KILLED | 5 AssertionError | test_r20_text_post_v09_refused[w413_off], test_r20_text_post_v09_refused[w413_on], test_r21_text_get_v07_refused, test_r30_device_quota_keys[text_get] | [pyt] tag=s20red-M9 start=2026-11-05 09:26:22 end=2026-11-05 09:26:33 elapsed=11s bound=600s status=FAIL rc=1 |
| M10 | the text log row removed | app/api/text_routes.py | KILLED | 14 AssertionError | test_r20_text_post_v09_refused[w413_off], test_r20_text_post_v09_refused[w413_on], test_r21_text_get_v07_refused, test_r22_text_post_v10_no_evidence | [pyt] tag=s20red-M10 start=2026-11-05 09:26:36 end=2026-11-05 09:26:46 elapsed=10s bound=600s status=FAIL rc=1 |
| M11 | camera any-low -> both-low | app/services/result_gate.py | KILLED | 2 AssertionError | test_r13_camera_gate_table, test_r51_camera_low_confidence[LOW1] | [pyt] tag=s20red-M11 start=2026-11-05 09:26:47 end=2026-11-05 09:27:00 elapsed=13s bound=600s status=FAIL rc=1 |
| M12 | the _is_product marker check removed (V1 low gated) | app/services/result_gate.py | KILLED | 2 AssertionError | test_p14_on_camera_v1_low_compares, test_r13_camera_gate_table | [pyt] tag=s20red-M12 start=2026-11-05 09:27:02 end=2026-11-05 09:27:14 elapsed=12s bound=600s status=FAIL rc=1 |
| M13 | the pre-enrichment snapshot not passed | app/api/image_routes.py | KILLED | 2 AssertionError | test_r54_camera_enrichment_evasion[ENRICH], test_r54_camera_enrichment_evasion[ENRICH_BRAND] | [pyt] tag=s20red-M13 start=2026-11-05 09:27:14 end=2026-11-05 09:27:23 elapsed=9s bound=600s status=FAIL rc=1 |
| M14 | the builder stamp gated on B1 only | app/services/response_builder.py | KILLED | 4 AssertionError | test_r25_category_conflict_b2_alone, test_r27_supported_real_orchestrator_stamp, test_r34_g3_tail_identity_classes[conflict], test_r90_builder_stamp_b2_alone | [pyt] tag=s20red-M14 start=2026-11-05 09:27:23 end=2026-11-05 09:27:34 elapsed=10s bound=600s status=FAIL rc=1 |
| M15 | URL uses the strict reading (gate_reason) | app/services/result_gate.py | KILLED | 4 AssertionError | test_p11_on_url_priced_pairs_delivered[ae], test_p11_on_url_priced_pairs_delivered[bh], test_p11_on_url_priced_pairs_delivered[v03], test_r17_refusal_flag_first | [pyt] tag=s20red-M15 start=2026-11-05 09:27:34 end=2026-11-05 09:27:43 elapsed=9s bound=600s status=FAIL rc=1 |
| M16 | the URL string reading removed (numeric only) | app/services/result_gate.py | KILLED | 10 AssertionError | test_p11_on_url_priced_pairs_delivered[ae], test_p11_on_url_priced_pairs_delivered[bh], test_r11_url_string_reading[1e400], test_r11_url_string_reading[abc] | [pyt] tag=s20red-M16 start=2026-11-05 09:27:43 end=2026-11-05 09:27:55 elapsed=11s bound=600s status=FAIL rc=1 |
| M17 | URL price fact and -> or | app/services/result_gate.py | KILLED | 9 AssertionError | test_r11_url_string_reading[1e400], test_r11_url_string_reading[abc], test_r11_url_string_reading[arabic_indic], test_r11_url_string_reading[bool] | [pyt] tag=s20red-M17 start=2026-11-05 09:27:55 end=2026-11-05 09:28:12 elapsed=17s bound=600s status=FAIL rc=1 |
| M18 | URL placeholder tested on side 0 only | app/services/result_gate.py | KILLED | 1 AssertionError | test_r12_url_one_sided | [pyt] tag=s20red-M18 start=2026-11-05 09:28:13 end=2026-11-05 09:28:32 elapsed=19s bound=600s status=FAIL rc=1 |
| M19 | the handler vocabulary check removed | app/middleware/error_handler.py | KILLED | 1 AssertionError | test_r80_envelope_passthrough | [pyt] tag=s20red-M19 start=2026-11-05 09:28:33 end=2026-11-05 09:28:56 elapsed=23s bound=600s status=FAIL rc=1 |
| M20 | stream refusal applied to the first terminal only | app/api/text_routes.py | KILLED | 7 AssertionError | test_r30_device_quota_keys[text_stream], test_r30b_stream_no_fingerprint_stash, test_r35_refusal_counted_on_budget[stream], test_r36_refusal_budget_spent_keeps_credit[stream] | [pyt] tag=s20red-M20 start=2026-11-05 09:29:03 end=2026-11-05 09:29:26 elapsed=23s bound=600s status=FAIL rc=1 |
| M21 | stream refund without keys | app/api/text_routes.py | KILLED | 4 AssertionError | test_r30_device_quota_keys[text_stream], test_r30b_stream_no_fingerprint_stash, test_r40_stream_refusal_frames_and_accounting[w413_off], test_r40_stream_refusal_frames_and_accounting[w413_on] | [pyt] tag=s20red-M21 start=2026-11-05 09:29:26 end=2026-11-05 09:29:47 elapsed=20s bound=600s status=FAIL rc=1 |
| M22 | the stream branch also calls record_lifetime_comparison | app/api/text_routes.py | KILLED | 7 AssertionError | test_r30_device_quota_keys[text_stream], test_r30b_stream_no_fingerprint_stash, test_r35_refusal_counted_on_budget[stream], test_r36_refusal_budget_spent_keeps_credit[stream] | [pyt] tag=s20red-M22 start=2026-11-05 09:29:47 end=2026-11-05 09:30:10 elapsed=23s bound=600s status=FAIL rc=1 |
| M23 | the elif restored to if | app/api/text_routes.py | KILLED | 7 AssertionError | test_r30_device_quota_keys[text_stream], test_r30b_stream_no_fingerprint_stash, test_r35_refusal_counted_on_budget[stream], test_r36_refusal_budget_spent_keeps_credit[stream] | [pyt] tag=s20red-M23 start=2026-11-05 09:30:11 end=2026-11-05 09:30:35 elapsed=24s bound=600s status=FAIL rc=1 |
| M24 | _GATE_REASON_BY_ASSESS drops unsupported_category | app/services/result_gate.py | KILLED | 1 AssertionError | test_r06_category | [pyt] tag=s20red-M24 start=2026-11-05 09:30:38 end=2026-11-05 09:30:58 elapsed=20s bound=600s status=FAIL rc=1 |
| M25 | strip / casefold removed from the low test | app/services/result_gate.py | KILLED | 2 AssertionError | test_r13_camera_gate_table, test_r51_camera_low_confidence[LOW1] | [pyt] tag=s20red-M25 start=2026-11-05 09:30:58 end=2026-11-05 09:31:17 elapsed=19s bound=600s status=FAIL rc=1 |
| M26 | URL refund after the surface call | app/api/url_routes.py | KILLED | 5 AssertionError | test_r30_device_quota_keys[url_post], test_r35_refusal_counted_on_budget[url], test_r37_refusal_gate_off_refunded_uncounted[url], test_r70_url_v09_refused[w413_off] | [pyt] tag=s20red-M26 start=2026-11-05 09:31:18 end=2026-11-05 09:31:26 elapsed=9s bound=600s status=FAIL rc=1 |
| M27 | the camera log row removed | app/api/image_routes.py | KILLED | 6 AssertionError/IndexError | test_r35_refusal_counted_on_budget[camera], test_r36_refusal_budget_spent_keeps_credit[camera], test_r37_refusal_gate_off_refunded_uncounted[camera], test_r50_camera_same_identity | [pyt] tag=s20red-M27 start=2026-11-05 09:31:27 end=2026-11-05 09:31:35 elapsed=8s bound=600s status=FAIL rc=1 |
| M28 | camera placeholder tested on side 0 only | app/services/result_gate.py | KILLED | 2 AssertionError | test_r13_camera_gate_table, test_r53_camera_one_placeholder_is_error[PH1] | [pyt] tag=s20red-M28 start=2026-11-05 09:31:36 end=2026-11-05 09:31:47 elapsed=11s bound=600s status=FAIL rc=1 |
| M29 | camera low tested on side 0 only | app/services/result_gate.py | KILLED | 2 AssertionError | test_r13_camera_gate_table, test_r51_camera_low_confidence[LOW1] | [pyt] tag=s20red-M29 start=2026-11-05 09:31:48 end=2026-11-05 09:31:55 elapsed=8s bound=600s status=FAIL rc=1 |
| M30 | the builder stamp not gated | app/services/response_builder.py | KILLED | 2 AssertionError | test_FY25_flag_off_compare_identity_matches_main, test_p08_off_builder_no_categories | [pyt] tag=s20red-M30 start=2026-11-05 09:31:56 end=2026-11-05 09:32:06 elapsed=11s bound=600s status=FAIL rc=1 |
| M31 | the surface reason arm not gated | app/api/text_routes.py | KILLED | 1 AssertionError | test_p09_off_surface_detail_two_keys | [pyt] tag=s20red-M31 start=2026-11-05 09:32:07 end=2026-11-05 09:32:17 elapsed=10s bound=600s status=FAIL rc=1 |
| M32 | the text INFO line removed | app/api/text_routes.py | KILLED | 2 AssertionError | test_r32_text_info_line[get], test_r32_text_info_line[post] | [pyt] tag=s20red-M32 start=2026-11-05 09:32:17 end=2026-11-05 09:32:25 elapsed=8s bound=600s status=FAIL rc=1 |
| M32b | the text INFO line given the query | app/api/text_routes.py | KILLED | 2 AssertionError | test_r32_text_info_line[get], test_r32_text_info_line[post] | [pyt] tag=s20red-M32b start=2026-11-05 09:32:26 end=2026-11-05 09:32:34 elapsed=8s bound=600s status=FAIL rc=1 |
| M33 | the features view re-added | app/services/result_gate.py | KILLED | 2 AssertionError | test_r15_camera_features_ignored, test_r56_camera_v2_features_same_identity | [pyt] tag=s20red-M33 start=2026-11-05 09:32:35 end=2026-11-05 09:32:47 elapsed=12s bound=600s status=FAIL rc=1 |
| M34 | camera reserved refund without keys | app/api/image_routes.py | KILLED | 2 AssertionError | test_r30_device_quota_keys[image], test_r50_camera_same_identity | [pyt] tag=s20red-M34 start=2026-11-05 09:32:47 end=2026-11-05 09:33:12 elapsed=25s bound=600s status=FAIL rc=1 |
| M35 | URL keys_out not passed | app/api/url_routes.py | KILLED | 3 AssertionError | test_r30_device_quota_keys[url_post], test_r70_url_v09_refused[w413_off], test_r70_url_v09_refused[w413_on] | [pyt] tag=s20red-M35 start=2026-11-05 09:33:13 end=2026-11-05 09:33:22 elapsed=8s bound=600s status=FAIL rc=1 |
| M36 | one placeholder answers need_second_product | app/api/image_routes.py | KILLED | 5 AssertionError | test_r52_camera_two_placeholders, test_r53_camera_one_placeholder_is_error[PH0], test_r53_camera_one_placeholder_is_error[PH1], test_r54_camera_enrichment_evasion[ENRICH] | [pyt] tag=s20red-M36 start=2026-11-05 09:33:22 end=2026-11-05 09:33:34 elapsed=12s bound=600s status=FAIL rc=1 |
| M37a | R-S20-38: the text / stream refusal not counted on the budget | app/api/text_routes.py | KILLED | 4 AssertionError | test_r31_fragrance_gate_counts_result_gate_refusal, test_r35_refusal_counted_on_budget[stream], test_r35_refusal_counted_on_budget[text_get], test_r35_refusal_counted_on_budget[text_post] | [pyt] tag=s20red-M37a start=2026-11-05 09:33:35 end=2026-11-05 09:33:43 elapsed=8s bound=600s status=FAIL rc=1 |
| M37b | R-S20-38: the camera refusal not counted on the budget | app/api/image_routes.py | KILLED | 2 AssertionError | test_r35_refusal_counted_on_budget[camera], test_r60_camera_fragrance_gate_order | [pyt] tag=s20red-M37b start=2026-11-05 09:33:43 end=2026-11-05 09:33:52 elapsed=8s bound=600s status=FAIL rc=1 |
| M37c | R-S20-38: the URL refusal not counted on the budget | app/api/url_routes.py | KILLED | 1 AssertionError | test_r35_refusal_counted_on_budget[url] | [pyt] tag=s20red-M37c start=2026-11-05 09:33:52 end=2026-11-05 09:34:00 elapsed=8s bound=600s status=FAIL rc=1 |
| M38 | the URL rating range check dropped | app/services/result_gate.py | KILLED | 8 AssertionError | test_r11_url_string_reading[1e400], test_r11_url_string_reading[abc], test_r11_url_string_reading[arabic_indic], test_r11_url_string_reading[bool] | [pyt] tag=s20red-M38 start=2026-11-05 09:34:01 end=2026-11-05 09:34:09 elapsed=9s bound=600s status=FAIL rc=1 |
| M39 | the camera block moved BEFORE the S81-10 pair gate (R-S20-31) | app/api/image_routes.py | KILLED | 9 AssertionError/IndexError | test_r30_device_quota_keys[image], test_r35_refusal_counted_on_budget[camera], test_r36_refusal_budget_spent_keeps_credit[camera], test_r37_refusal_gate_off_refunded_uncounted[camera] | [pyt] tag=s20red-M39 start=2026-11-05 09:34:10 end=2026-11-05 09:34:18 elapsed=8s bound=600s status=FAIL rc=1 |
| M40 | R-S20-38: a spent budget still refunds (credit not kept) | app/api/text_routes.py | KILLED | 3 AssertionError | test_r36_refusal_budget_spent_keeps_credit[stream], test_r36_refusal_budget_spent_keeps_credit[text_get], test_r36_refusal_budget_spent_keeps_credit[text_post] | [pyt] tag=s20red-M40 start=2026-11-05 09:34:19 end=2026-11-05 09:34:28 elapsed=9s bound=600s status=FAIL rc=1 |
| M41 | R-S20-38: the refusal counted with the fragrance gate OFF | app/api/text_routes.py | KILLED | 3 AssertionError | test_r37_refusal_gate_off_refunded_uncounted[stream], test_r37_refusal_gate_off_refunded_uncounted[text_get], test_r37_refusal_gate_off_refunded_uncounted[text_post] | [pyt] tag=s20red-M41 start=2026-11-05 09:34:29 end=2026-11-05 09:34:37 elapsed=8s bound=600s status=FAIL rc=1 |
| M42 | R-S20-33: `not had_error` dropped from the stream first branch | app/api/text_routes.py | KILLED | 1 AssertionError | test_r62_stream_error_then_refusal_terminal | [pyt] tag=s20red-M42 start=2026-11-05 09:34:37 end=2026-11-05 09:34:46 elapsed=8s bound=600s status=FAIL rc=1 |
| EQ1 | result_gate_refusal ignores success | app/services/result_gate.py | EQUIVALENT (survived) | 0  |  | [pyt] tag=s20red-EQ1 start=2026-11-05 09:34:47 end=2026-11-05 09:34:54 elapsed=7s bound=600s status=OK rc=0 |
| EQ2 | R-S20-33: the `complete_response is _s20_refusal` operand dropped | app/api/text_routes.py | EQUIVALENT (survived) | 0  |  | [pyt] tag=s20red-EQ2 start=2026-11-05 09:34:54 end=2026-11-05 09:35:01 elapsed=7s bound=600s status=OK rc=0 |

Counts: 45 KILLED (M1-M42 incl. M32b, M37a/b/c), 0 survivors, 2 equivalents. M27 / M39 kill sets also hold IndexError nodes beside AssertionError ones. EQ1 (result_gate_refusal ignores success): equivalent (RC8: gate_reason / url_gate_reason return None unless success is True). EQ2 (`complete_response is _s20_refusal` dropped): equivalent per R-S20-33 (the first terminal latches complete_response to the refusal object). M30 also ran test_s75_fanout_identity.py. M37 re-cut by R-S20-38 (the mutant = the refusal NOT counted). M40/M41/M42 added for R-S20-38 / R-S20-33. M7 is the camera block disabled pre-compare (the move itself is not an exact edit).

## Not-measured files, CI-order set, secret scan (real worktree, base)
- [hermeticity] sentinel checked 223 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | [pyt] tag=s20red-base-nm start=2026-11-05 09:36:30 end=2026-11-05 09:37:20 elapsed=51s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-base-nm.log
- [pyt] tag=s20red-base-ci-order start=2026-11-05 09:37:21 end=2026-11-05 09:42:11 elapsed=289s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-base-ci-order.log
- [hermeticity] sentinel checked 31 test(s) | [netguard] blocked 0 attempt(s) from 0 node(s) | [pyt] tag=s20red-base-secretscan start=2026-11-05 09:42:11 end=2026-11-05 09:42:35 elapsed=24s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-base-secretscan.log
  - nm (test_sentry_channels_u8d, test_history_routes, test_home_routes, test_shutdown_drain, test_m13_04_full_stream_deadline): green (223 checked).
  - CI-order (RED file + E1-E7 + the 4.2 list incl. the R-S20-37 additions, 54 files): 123 failed / 3947 passed / 1 deselected = the 122 RED nodes + test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (environmental CRLF).
  - test_secret_scan_static.py alone: 31 passed.
- NOT MEASURED here: T23 OpenAPI snapshot with the flag exported (GREEN). NOT RUN (GREEN's): corpus gate, the fourteen client fences. R8 pair / paid-route metering: the spec 1.10 [pyt] lines reused (r1, r2).

## Comm set (the LAST step) and base record
- Re-derived ONCE by the union rule (the spec's comm_set.py) over the real worktree: 389 = the spec's 388 (sha256 97218ca801416b02...) + the new RED file (excluded: it is the unit). R-S20-37 names present. Precommit hook files: 0. Lists: S81-20_red/COMM_SET.txt (388), S81-20_red/comm_reasons.tsv, S81-20_red/derive/comm_set_summary.json.
- Base record: <scratchpad>/harness/base_records/6869a3e655805afd3adbba43f99578dd79585934/97218ca801416b02b4e5d4ab085a4e5a4410a60742327c51723332cf9cc58b18.{txt,files,pyt.log,header.txt}.
- Split: 40 reused from the spec 1.10 runs at 6869a3e6; 131 reused from stored records (e1491c97/4b65c5db 81, 0b19de5b/90b85603 38, 00e4120d/9a85c0b0 12); 217 RUN at base in the real worktree (9 chunks <= 25 alphabetical files, bound 1200, + test_secret_scan_static.py alone). Reuse rule (reuse.py): own file and imported tests modules unchanged since the record sha; no reference to a changed app/scripts/tests stem, CLAUDE.md, SmartCompareApp, nor app.main / TestClient when a route / middleware file changed; not a glob/walk/listdir/iterdir reader.
- [pyt] tag=s20red-comm-base-00 start=2026-11-05 09:42:35 end=2026-11-05 09:43:42 elapsed=67s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-comm-base-00.log
- [hermeticity] sentinel checked 317 test(s) | [netguard] blocked 10 attempt(s) from 4 node(s) | [pyt] tag=s20red-comm-base-01 start=2026-11-05 09:43:43 end=2026-11-05 09:44:32 elapsed=49s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-comm-base-01.log
- [pyt] tag=s20red-comm-base-02 start=2026-11-05 09:44:32 end=2026-11-05 09:46:39 elapsed=126s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-comm-base-02.log
- [hermeticity] sentinel checked 399 test(s) | [netguard] blocked 2 attempt(s) from 2 node(s) | [pyt] tag=s20red-comm-base-03 start=2026-11-05 09:46:39 end=2026-11-05 09:47:07 elapsed=28s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-comm-base-03.log
- [pyt] tag=s20red-comm-base-04 start=2026-11-05 09:47:07 end=2026-11-05 09:48:22 elapsed=75s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-comm-base-04.log
- [pyt] tag=s20red-comm-base-05 start=2026-11-05 09:48:23 end=2026-11-05 09:51:03 elapsed=160s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-comm-base-05.log
- [pyt] tag=s20red-comm-base-06 start=2026-11-05 09:51:04 end=2026-11-05 09:52:13 elapsed=69s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-comm-base-06.log
- [pyt] tag=s20red-comm-base-07 start=2026-11-05 09:52:13 end=2026-11-05 09:53:39 elapsed=86s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-comm-base-07.log
- [pyt] tag=s20red-comm-base-08 start=2026-11-05 09:53:40 end=2026-11-05 09:54:36 elapsed=56s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\03431011-0c7e-4ecd-b0ce-08ff47f4af10\scratchpad\S81-20_red\base_logs\s20red-comm-base-08.log
- Sorted FAILED node set at base (17), each pre-existing noise present in stored records or the known list:
  - tests/test_auth_interceptor.py::test_sign_in_with_social_exception
  - tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
  - tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
  - tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
  - tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
  - tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
  - tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
  - tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
  - tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
  - tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
  - tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
  - tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
  - tests/test_s81_s19_gap_queue.py::test_r15_hygiene
  (r06 + d17 r9: autocrlf CRLF; prompt_truth pair: cold tiktoken (reused); s16 r27 x5, d16 r10, s19 r15: hygiene nodes of the 00e4120d / e1491c97 records; auth_interceptor x2, page_scraping x2, personalization_bundle_c x2: in the 0b19de5b and older records.) No TIMEOUT; nothing in the comm set NOT MEASURED.

## Deviations from the spec
- R31 / R60 / M37 re-cut by R-S20-38: a result-gate refusal under ENABLE_FRAGRANCE_ONLY_GATE is COUNTED once; a spent budget keeps the credit. The budget is observed by recorders on category_gate.budget_state_async / record_refusal_async (module attributes), not by a refusal-budget EVAL on a FakeRedis.
- R9 vs R7: the spec keeps w412 row 6 (a product-less success body) -> placeholder_identity in R7 but lists 'products missing -> None' in R9; the RED file follows R7 and the 2.2 definition (gate_reason maps assess_result) and pins 'products missing -> None' for url_gate_reason only.
- R55 V1 half -> P19 PIN per R-S20-39 (the stub conflict under V1 is delivered); the prototype's _camera_gate_categories uses V2 _category only (the spec 2.6 classify stub fallback is not used).
- _result_gate_exit is async in the prototype (the R-S20-38 budget read/record is awaited).
- R7 checks every success:True corpus row (>= 20) against its mapped first assessment reason, not a hand-kept subset.
- R33/R34 observe the G3 tail through a recorder on scs._fire_and_forget (label kb_ingest) + a build_job wrapper, not a run_job recorder in the thread.
- R62's RED half is a trailing GATE_CODE symbol assertion; its had_error-precedence assertions already hold at base.
- P1-P5 compare the delivered body with the JSON round trip of the fixture read from disk (+ comparison_id under echo ON), not a recorded digest.
- FY_V10 rating leaf returns {rating None, review_count 0} (a None leaf crashes _fetch_product_data at scs :6703, measured).
- The fy rows hit the get_user_demographics neutralized.supabase.invalid sentinel (the existing baseline class); not stubbed.

## Open questions
- R-S20-38 spent budget: should a refusal at a spent budget still be counted? The prototype does not count it; no row pins either choice.
- Stream R-S20-38: the budget read/record runs inside the generator's finally (await in an async-generator finally); no row pins the client-cancel case.
- R9 vs R7: confirm gate_reason may answer placeholder_identity for a product-less success body.

## Restore check
- Real worktree HEAD 6869a3e6; `git status --short` = `?? tests/test_s81_s20_result_gate.py` only; `git diff --stat` empty. Scratch worktree removed (0 s20p rows in git worktree list). No pytest left running.

Files: <scratchpad>/S81-20_red/ (RED_REPORT.md, COMM_SET.txt, comm_reasons.tsv, reuse_plan.json, prototype.diff, prototype_files/, mutants/, mutate.py, proto_apply.py, reuse.py, base_driver.py, base_logs/, progress.txt, notes.md); copy at <scratchpad>/S81-20_RED_REPORT.md.
