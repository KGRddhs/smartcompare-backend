# S81-04c REFUSAL-LOG-HYGIENE - RED REPORT (Opus 5.5, 2026-11-11)

Base a74caba7e3ff66b12e94178c912197c845ccbd14. Flag: NONE (log-only, R-A1 b). Spec sha 5d052c5a... verified.
File written (the only one in the worktree): tests/test_s81_s04c_refusal_log_hygiene.py, 31077 B,
sha256 774e3e61a7b416299d735281e2a14d7c801d662fa7122568be665b1a56ee4fac; ASCII-only, LF, black 26.5.1 clean,
ruff E9/F63/F7/F82 clean. 102 nodes: RED 23 (R1 x7, R2, R3 x8, R4 x4, R5, R6, R7), PIN 79 (P0 1, P1 21, P2 16, P3 32, P4 4, P5 1, P6 4).

## Runs ([pyt] lines)
- step 2 (review's not-measured list): EMPTY in the task text; nothing run.
- base, scratch: [pyt] tag=s04c-red-scr0 elapsed=10s status=FAIL rc=1 -> 23 failed, 79 passed
- base, REAL worktree: [pyt] tag=s04c-red-base start=2026-11-11 18:10:34 end=2026-11-11 18:10:45 elapsed=11s bound=600s status=FAIL rc=1; 23 failed, 79 passed; every failure AssertionError (23/23); only test_r* nodes failed; [hermeticity] sentinel checked 102; [netguard] blocked 0
- R7 repeats at base: [pyt] tag=s04c-red-r7-rep1 elapsed=9s status=FAIL rc=1; [pyt] tag=s04c-red-r7-rep2 elapsed=9s status=FAIL rc=1 (both {'active': True, 'marker': 1, 'arm': 1, 'dispatches': 0}): deterministic, FREEZABLE
- prototype (RED file + E1-edited test_s81_s06_router_gate_rows.py): [pyt] tag=s04c-red-proto elapsed=11s status=OK rc=0 -> 183 passed (no flag: one state; PIN rows = the identity)
- prototype, spec set A files: [pyt] tag=s04c-red-proto-seta elapsed=52s bound=1200s status=OK rc=0 -> 1443 passed
- CI-order set at base (s20_result_gate first as the lifespan user, then s03, s04, s04c, s04d, s05, s06 x2): [pyt] tag=s04c-red-ciorder elapsed=58s bound=1200s status=FAIL rc=1 -> 23 failed, 1344 passed; FAILED set == the RED set; [netguard] blocked 48 from 11 nodes (supabase.invalid sentinels in s20 / s04, base noise)
- tests/test_secret_scan_static.py at base: [pyt] tag=s04c-red-secretscan elapsed=7s status=OK rc=0 -> 31 passed
- url_mode_v2 re-run alone at base: [pyt] tag=s04c-red-urlv2-rerun elapsed=10s status=OK rc=0 -> 456 passed

## Mutation table (prototype byte copies, one exact edit each, unit file via pyt.py bound 600, restored + sha256-verified)
- M1: KILLED test_r1_class_refusal_warns_by_type_role_off[parse], test_r3_subclass_prints_its_own_name[parse], test_r6_spend_refusal_warns_by_type_after_the_spend_line, test_r7_no_sentry_event_for_a_refusal | [pyt] tag=s04c-red-m1 start=2026-11-11 18:04:14 end=2026-11-11 18:04:26 elapsed=12s bound=600s status=FAIL rc=1
- M2: KILLED test_r1_class_refusal_warns_by_type_role_off[verdict], test_r3_subclass_prints_its_own_name[verdict] | [pyt] tag=s04c-red-m2 start=2026-11-11 18:04:26 end=2026-11-11 18:04:36 elapsed=10s bound=600s status=FAIL rc=1
- M3: KILLED test_r2_camera_refusal_warns_by_type_role_off, test_r3_subclass_prints_its_own_name[camera], test_r5_vision_v2_no_content_warns_by_type | [pyt] tag=s04c-red-m3 start=2026-11-11 18:04:37 end=2026-11-11 18:04:48 elapsed=11s bound=600s status=FAIL rc=1
- M4: KILLED test_r1_class_refusal_warns_by_type_role_off[url_extract], test_r3_subclass_prints_its_own_name[url_extract] | [pyt] tag=s04c-red-m4 start=2026-11-11 18:04:48 end=2026-11-11 18:04:58 elapsed=10s bound=600s status=FAIL rc=1
- M5: KILLED test_r1_class_refusal_warns_by_type_role_off[specs], test_r3_subclass_prints_its_own_name[specs], test_r4_group_b_role_on_warns_by_type[specs] | [pyt] tag=s04c-red-m5 start=2026-11-11 18:04:58 end=2026-11-11 18:05:09 elapsed=11s bound=600s status=FAIL rc=1
- M6: KILLED test_r1_class_refusal_warns_by_type_role_off[price], test_r3_subclass_prints_its_own_name[price], test_r4_group_b_role_on_warns_by_type[price] | [pyt] tag=s04c-red-m6 start=2026-11-11 18:05:09 end=2026-11-11 18:05:19 elapsed=10s bound=600s status=FAIL rc=1
- M7: KILLED test_r1_class_refusal_warns_by_type_role_off[price_training], test_r3_subclass_prints_its_own_name[price_training], test_r4_group_b_role_on_warns_by_type[price_training] | [pyt] tag=s04c-red-m7 start=2026-11-11 18:05:20 end=2026-11-11 18:05:30 elapsed=10s bound=600s status=FAIL rc=1
- M8: KILLED test_r1_class_refusal_warns_by_type_role_off[reviews], test_r3_subclass_prints_its_own_name[reviews], test_r4_group_b_role_on_warns_by_type[reviews] | [pyt] tag=s04c-red-m8 start=2026-11-11 18:05:30 end=2026-11-11 18:05:43 elapsed=13s bound=600s status=FAIL rc=1
- M9: KILLED test_r1_class_refusal_warns_by_type_role_off[parse], test_r3_subclass_prints_its_own_name[parse], test_r6_spend_refusal_warns_by_type_after_the_spend_line | [pyt] tag=s04c-red-m9 start=2026-11-11 18:05:44 end=2026-11-11 18:05:59 elapsed=15s bound=600s status=FAIL rc=1
- M10: KILLED test_r1_class_refusal_warns_by_type_role_off[reviews], test_r3_subclass_prints_its_own_name[reviews], test_r4_group_b_role_on_warns_by_type[reviews] | [pyt] tag=s04c-red-m10 start=2026-11-11 18:06:05 end=2026-11-11 18:06:18 elapsed=13s bound=600s status=FAIL rc=1
- M11: KILLED test_r2_camera_refusal_warns_by_type_role_off, test_r3_subclass_prints_its_own_name[camera], test_r5_vision_v2_no_content_warns_by_type | [pyt] tag=s04c-red-m11 start=2026-11-11 18:06:18 end=2026-11-11 18:06:38 elapsed=20s bound=600s status=FAIL rc=1
- M12: KILLED test_r1_class_refusal_warns_by_type_role_off[specs], test_r3_subclass_prints_its_own_name[specs], test_r4_group_b_role_on_warns_by_type[specs] | [pyt] tag=s04c-red-m12 start=2026-11-11 18:06:38 end=2026-11-11 18:06:54 elapsed=16s bound=600s status=FAIL rc=1
- M13: KILLED test_p1_non_class_record_byte_identical[parse-off-, test_p1_non_class_record_byte_identical[parse-off-0], test_p1_non_class_record_byte_identical[parse-off-None], test_p1_non_class_record_byte_identical[parse-off-], test_p1_non_class_record_byte_identical[parse-off-false], test_p1_non_class_record_byte_identical[parse-off-off], test_p1_non_class_record_byte_identical[parse-on-None] | [pyt] tag=s04c-red-m13 start=2026-11-11 18:06:55 end=2026-11-11 18:07:08 elapsed=14s bound=600s status=FAIL rc=1
- M14: KILLED test_p1_non_class_record_byte_identical[price-off-None], test_p1_non_class_record_byte_identical[price-on-None] | [pyt] tag=s04c-red-m14 start=2026-11-11 18:07:09 end=2026-11-11 18:07:21 elapsed=13s bound=600s status=FAIL rc=1
- M15: KILLED test_r3_subclass_prints_its_own_name[verdict] | [pyt] tag=s04c-red-m15 start=2026-11-11 18:07:22 end=2026-11-11 18:07:33 elapsed=11s bound=600s status=FAIL rc=1
- M16: KILLED test_r3_subclass_prints_its_own_name[camera] | [pyt] tag=s04c-red-m16 start=2026-11-11 18:07:33 end=2026-11-11 18:07:45 elapsed=12s bound=600s status=FAIL rc=1
- M17: KILLED test_p2_delivery_identity[verdict-off] | [pyt] tag=s04c-red-m17 start=2026-11-11 18:07:46 end=2026-11-11 18:07:57 elapsed=11s bound=600s status=FAIL rc=1
- M18: KILLED test_p2_delivery_identity[url_extract-off] | [pyt] tag=s04c-red-m18 start=2026-11-11 18:07:57 end=2026-11-11 18:08:08 elapsed=11s bound=600s status=FAIL rc=1
- M19: KILLED test_p4_camera_refunds_and_status[runtime-off], test_p4_camera_refunds_and_status[runtime-on], test_p4_camera_refunds_and_status[w13-off], test_p4_camera_refunds_and_status[w13-on] | [pyt] tag=s04c-red-m19 start=2026-11-11 18:08:15 end=2026-11-11 18:08:25 elapsed=10s bound=600s status=FAIL rc=1
- M20: KILLED test_p5_camera_anon_refund | [pyt] tag=s04c-red-m20 start=2026-11-11 18:08:25 end=2026-11-11 18:08:34 elapsed=10s bound=600s status=FAIL rc=1
- M21: SURVIVED - | [pyt] tag=s04c-red-m21 start=2026-11-11 18:08:35 end=2026-11-11 18:08:44 elapsed=9s bound=600s status=OK rc=0
- M22: KILLED test_p3_any_role_read_sequence[parse-runtime-off], test_p3_any_role_read_sequence[parse-runtime-on], test_p3_any_role_read_sequence[parse-w13-off], test_p3_any_role_read_sequence[parse-w13-on] | [pyt] tag=s04c-red-m22 start=2026-11-11 18:08:44 end=2026-11-11 18:08:55 elapsed=11s bound=600s status=FAIL rc=1
- M23: KILLED test_p3_any_role_read_sequence[specs-runtime-off], test_p3_any_role_read_sequence[specs-runtime-on], test_p3_any_role_read_sequence[specs-w13-off], test_p3_any_role_read_sequence[specs-w13-on] | [pyt] tag=s04c-red-m23 start=2026-11-11 18:08:55 end=2026-11-11 18:09:05 elapsed=10s bound=600s status=FAIL rc=1
- M24: KILLED test_p2_delivery_identity[verdict-on], test_p3_any_role_read_sequence[verdict-w13-off], test_p3_any_role_read_sequence[verdict-w13-on], test_p6_role_on_class_rows_unchanged[verdict] | [pyt] tag=s04c-red-m24 start=2026-11-11 18:09:05 end=2026-11-11 18:09:15 elapsed=10s bound=600s status=FAIL rc=1
- M25: KILLED test_p1_non_class_record_byte_identical[camera-off-None], test_p1_non_class_record_byte_identical[camera-on-None], test_p4_camera_refunds_and_status[runtime-off], test_p4_camera_refunds_and_status[runtime-on] | [pyt] tag=s04c-red-m25 start=2026-11-11 18:09:15 end=2026-11-11 18:09:25 elapsed=10s bound=600s status=FAIL rc=1
- M21 SURVIVED = EQUIVALENT by R-04C-22 (the two latches are mutually exclusive); M19 and M20 (one refund DROPPED each) KILLED. Totals: 24 KILLED, 1 SURVIVED (equivalent).

## Comm set (R-04C-26)
- list: s04c_red/comm_set.txt (375 = spec 368 UNION 7 re-derived: test_cache_service_bounded_transport, test_compare_timeout_graceful, test_m13_04_full_stream_deadline, test_m18_region_guard_prescoring, test_scoring_calibration_bundle_c, test_w4_13_flag_off_ledger + the RED file); reasons s04c_red/comm_reasons.tsv; reuse plan s04c_red/comm_plan.tsv
- GC-9 reuse: 1 member reused (90d4ed74/1f35353b...); 373 run at a74caba7 in 15 chunks; the RED file from s04c-red-base
  - chunk 00 (25 files): 2 failed, 1072 passed, 31 warnings in 34.48s | [pyt] tag=s04c-red-comm-00 start=2026-11-11 18:15:42 end=2026-11-11 18:16:18 elapsed=36s bound=1200s status=FAIL rc=1
  - chunk 01 (25 files): 1066 passed, 5 deselected, 13 warnings in 29.88s | [pyt] tag=s04c-red-comm-01 start=2026-11-11 18:16:18 end=2026-11-11 18:16:49 elapsed=31s bound=1200s status=OK rc=0
  - chunk 02 (25 files): 1021 passed, 1 skipped, 2 deselected, 13 warnings in 28.21s | [pyt] tag=s04c-red-comm-02 start=2026-11-11 18:16:55 end=2026-11-11 18:17:24 elapsed=30s bound=1200s status=OK rc=0
  - chunk 03 (25 files): 989 passed, 2 skipped, 11 warnings in 64.67s (0:01:04) | [pyt] tag=s04c-red-comm-03 start=2026-11-11 18:17:25 end=2026-11-11 18:18:37 elapsed=72s bound=1200s status=OK rc=0
  - chunk 04 (25 files): 675 passed, 1 skipped, 18 warnings in 85.50s (0:01:25) | [pyt] tag=s04c-red-comm-04 start=2026-11-11 18:18:37 end=2026-11-11 18:20:05 elapsed=88s bound=1200s status=OK rc=0
  - chunk 05 (25 files): 401 passed, 1 skipped, 2 deselected, 12 warnings in 23.66s | [pyt] tag=s04c-red-comm-05 start=2026-11-11 18:20:05 end=2026-11-11 18:20:30 elapsed=25s bound=1200s status=OK rc=0
  - chunk 06 (25 files): 3675 passed, 22 skipped, 6 deselected, 14 warnings in 33.39s | [pyt] tag=s04c-red-comm-06 start=2026-11-11 18:20:31 end=2026-11-11 18:21:07 elapsed=37s bound=1200s status=OK rc=0
  - chunk 07 (25 files): 742 passed, 8 skipped, 11 deselected, 1 xfailed, 17 warnings, 2 errors in 30.64s | [pyt] tag=s04c-red-comm-07 start=2026-11-11 18:21:08 end=2026-11-11 18:21:39 elapsed=32s bound=1200s status=FAIL rc=1
  - chunk 08 (25 files): 1006 passed, 261 warnings in 169.90s (0:02:49) | [pyt] tag=s04c-red-comm-08 start=2026-11-11 18:21:40 end=2026-11-11 18:24:32 elapsed=172s bound=1200s status=OK rc=0
  - chunk 09 (25 files): 8 failed, 2398 passed, 14 warnings in 133.91s (0:02:13) | [pyt] tag=s04c-red-comm-09 start=2026-11-11 18:24:38 end=2026-11-11 18:26:54 elapsed=136s bound=1200s status=FAIL rc=1
  - chunk 10 (25 files): 6 failed, 2792 passed, 63 warnings in 87.90s (0:01:27) | [pyt] tag=s04c-red-comm-10 start=2026-11-11 18:26:54 end=2026-11-11 18:28:24 elapsed=90s bound=1200s status=FAIL rc=1
  - chunk 11 (25 files): 6 failed, 1844 passed, 1 xfailed, 44 warnings in 60.98s (0:01:00) | [pyt] tag=s04c-red-comm-11 start=2026-11-11 18:28:24 end=2026-11-11 18:29:27 elapsed=63s bound=1200s status=FAIL rc=1
  - chunk 12 (25 files): 890 passed, 1 skipped, 15 warnings in 52.51s | [pyt] tag=s04c-red-comm-12 start=2026-11-11 18:29:27 end=2026-11-11 18:30:22 elapsed=54s bound=1200s status=OK rc=0
  - chunk 13 (25 files): 658 passed, 6 skipped, 2 deselected, 35 xfailed, 18 warnings in 71.41s (0:01:11) | [pyt] tag=s04c-red-comm-13 start=2026-11-11 18:30:26 end=2026-11-11 18:31:39 elapsed=73s bound=1200s status=OK rc=0
  - chunk 14 (23 files): 858 passed, 1 skipped, 13 warnings in 18.91s | [pyt] tag=s04c-red-comm-14 start=2026-11-11 18:31:39 end=2026-11-11 18:31:59 elapsed=20s bound=1200s status=OK rc=0
- BASE RECORD stored LAST: harness/base_records/a74caba7e3ff66b12e94178c912197c845ccbd14/0a224f4866414586f16136461268f3cc8f72e1337345c02b068bdb2525d20cad.{files,txt,header.txt,pyt.log} (complete, not PARTIAL): 47 FAILED/ERROR ids = RED 23 + 24 pre-existing (23 of them also in the 90d4ed74 record; NEW one = test_s80_url_mode_v2.py::test_deadline_yields_timeout_503[POST], a wall-clock flake 2.06 s vs 0.6 s in chunk 09, passes alone)

## L2 (R-04C-21), measured by code read at a74caba7 (not by a request run)
- specs: scs._fetch_product_data cleans with _clean_specs (structured_comparison_service.py:6467), whose meta_keys hold 'error' (:3501): the B1 str(e) is stripped before the response.
- price: Tier-2 extract_price's error dict has amount None, so it never returns (:8884 only an amount continues); Tier-3 failure returns a fresh {'amount': None, 'currency', '_cached': False} (~:9151), not the error dict. The B2 / B3 str(e) does not reach a body on these paths. Not traced: the :6599 / :6632 / :6663 specs reassignments. Proposal: L2 leaves the stated limits (or stays with 'code-read only').

## Deviations
- P0 added (R-04C-17 synthetic-text constraint as a PIN row); P4 also asserts anon_refunds == []; R7 child neutralises dotenv.load_dotenv before importing app (no .env read) and also asserts active / dispatches == 0 / delivery.
- P3 re-measured under the FULL config (R-04C-18): equals the spec's literals (A1/A2/A4 one read before the record, group B none, camera two). No literal change.
- 'CI-order set' defined as above (the RED file's alphabetical neighbours with the lifespan user first).

## Restore
- scratch worktree (no junction) removed; git worktree list clean of it; sha256 of all 3567 tracked files identical before/after (1378af22...); git status: only ?? tests/test_s81_s04c_refusal_log_hygiene.py; no pytest of this agent alive.
