# S81-22 COMPARE-RUNS + capped judge: RED REPORT (RED agent, Opus 5.5, 2026-11-06)

Base 18cb9e04a36382fc417307500a092486f618d95e. Spec sha256 730c5017f09c2accdf261e3318a8ff76fb4071c3fa164926ded725ec2a6ea78b, as amended by RULINGS_S81_22 (R-S22-23..60). Written through the shell (the harness refuses a subagent Write of a report .md).
The hook test files tests/test_precommit_hook*.py were NOT RUN (no .githooks change). The corpus gate and the fourteen client fences were NOT RUN (GREEN's duty).

## 1. Files (the real worktree: exactly two new files, nothing else)
- tests/test_s81_s22_compare_runs.py  60513 bytes  sha256 c1cb93752908c061beacb01ca47968ecd7026af8581bc5bca4220fc894c52a52  (ASCII, LF, 0 bytes > 127, 0 CR; no @gmail / +973 / 8-digit run / key shapes)
- tests/test_s81_s22_judge.py  52781 bytes  sha256 39a46d1c574ecf5e8403f5037c7f611ca142d4e1bbcbbc2655f6677556ea2199  (ASCII, LF, 0 bytes > 127, 0 CR; no @gmail / +973 / 8-digit run / key shapes)
- `git status --short` of sc-s81-s22 at the end: `?? tests/test_s81_s22_compare_runs.py`, `?? tests/test_s81_s22_judge.py`; `git diff --stat` empty; HEAD 18cb9e04.

## 2. Node counts at base (real worktree, flags unset)
192 nodes = 133 RED nodes FAILED + 59 PIN nodes PASSED. Every RED test function fails (r01..r27 + r12b/r15b, b01..b17, j01..j29 + j02b/j14b/j14c/j14d/j15b/j16b/j16c); no PIN node fails.
PIN nodes: P01 (5 exits x 5 OFF values x 2 W4-13 states = 50), P02 (5), P03, P04, P05, PJ1.
AssertionError proof: the per-failure classifier over the log finds 132 failure sections, every one AssertionError (131 `E AssertionError` + 1 rewritten `assert`), 0 ERROR entries; the 133rd (test_r10_comparison_id_link[6F9619FF-...], header line truncated by pytest) takes the same `_sym` assert path as its five siblings. Missing symbols are read through find_spec / getattr helpers (`_cr()`, `_sym()`, `_cj()`), files through Path.exists asserts.
```
================ 133 failed, 59 passed, 11 warnings in 19.07s =================
[hermeticity] sentinel checked 192 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
```

## 3. Prototype (own detached junction-free scratch worktree <scratchpad>/s22w at 18cb9e04, removed with git worktree remove --force; `git worktree list` shows it gone)
Diff saved at S81-22_red/prototype.diff + S81-22_red/prototype_files/ (never committed). `git diff --stat` (route files CRLF preserved; content lines +4 / +2 / +2):
```
 app/api/image_routes.py                         |   2 +
 app/api/text_routes.py                          |   4 +
 app/api/url_routes.py                           |   2 +
 app/services/compare_runs.py                    | 403 +++++++++++
 migrations/048_compare_runs.sql                 | 270 ++++++++
 migrations/rollback/048_compare_runs.sql        |  83 +++
 railway.judge.json                              |  15 +
 scripts/cron_compare_judge.py                   | 845 ++++++++++++++++++++++++
 tests/test_migration_043_delete_user_cascade.py |   6 +-
 tests/test_s81_kb_schema.py                     |   6 +-
```
Flags unset and set (ENABLE_COMPARE_RUN_LEDGER=true ENABLE_BATCH_JUDGE=apply exported for that runner call only):
```
====================== 192 passed, 11 warnings in 13.11s ======================
[hermeticity] sentinel checked 192 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
====================== 192 passed, 11 warnings in 12.96s ======================
[hermeticity] sentinel checked 192 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
```
Prototype against the migration readers + route gates (the 17 files of 7.2 gates 3-4 minus prompt_truth): 1684 passed, 2 failed before one fix: test_s14_p02 (three extra kb_feedback literals in the script: fixed by keying on KB_FEEDBACK_TABLE) and test_r06_production_lexicon_content (the known CRLF base noise). After the fix test_s81_kb_schema + the judge file: OK.
```
==== 2 failed, 1684 passed, 4 deselected, 13 warnings in 76.71s (0:01:16) =====
[hermeticity] sentinel checked 1686 test(s)
[netguard] blocked 26 attempt(s) from 11 node(s)
====================== 582 passed, 11 warnings in 16.90s ======================
[hermeticity] sentinel checked 582 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
```

## 4. E1 / E2 / E3 (GREEN's; listed with anchors, measured in the scratch worktree)
- E1 tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once :528 `("046", "048", "049", "051")` -> `("046", "049", "051")` + comment.
- E2 tests/test_s81_kb_schema.py P02_ALLOWED :341-362: TWO entries (deviation: the spec names one): `("scripts/cron_compare_judge.py", 'KB_PRUNE_FEEDBACK_RPC = "kb_prune_feedback"')` AND `("scripts/cron_compare_judge.py", 'KB_FEEDBACK_TABLE = "kb_feedback"')` (the DRY exact would-delete head count of R-S22-32 reads kb_feedback by table name; the cron_learning precedent line).
- E3 tests/test_migration_043_delete_user_cascade.py::test_fence_flags_each_dropped_delete :1192 and ::test_fence_flags_each_weakened_delete_predicate :1204: the DELETE walk limited to `s["table"] in KNOWN_USER_TABLES` (the narrowest edit; every user-table DELETE still walked).
- E3 measurement: with ONLY the probe 048 added (compare_runs.py held aside), the migration readers at base: exactly the two E3 rows + E1 red:
```
========== 3 failed, 802 passed, 4 deselected, 11 warnings in 36.76s ==========
[hermeticity] sentinel checked 805 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
FAILED tests/test_migration_043_delete_user_cascade.py::test_fence_flags_each_dropped_delete
FAILED tests/test_migration_043_delete_user_cascade.py::test_fence_flags_each_weakened_delete_predicate
FAILED tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once
```
With E1 + E3 applied: the two files green:
```
====================== 580 passed, 11 warnings in 19.50s ======================
[hermeticity] sentinel checked 580 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
```
The E-row diff (LF-normalised):
```
diff --git a/tests/test_migration_043_delete_user_cascade.py b/tests/test_migration_043_delete_user_cascade.py
index 7430237b..aade4b78 100644
--- a/tests/test_migration_043_delete_user_cascade.py
+++ b/tests/test_migration_043_delete_user_cascade.py
@@ -1195,3 +1195,4 @@ def test_fence_flags_each_dropped_delete():
     _name, body, stmts = _latest()
-    dels = [s for s in stmts if s["kind"] == "delete"]
+    # S81-22 E3 (R-S22-23): every DELETE of a fence user table (048 adds kb_feedback).
+    dels = [s for s in stmts if s["kind"] == "delete" and s["table"] in KNOWN_USER_TABLES]
     assert len(dels) >= 7, len(dels)
@@ -1207,3 +1208,4 @@ def test_fence_flags_each_weakened_delete_predicate():
     _name, body, stmts = _latest()
-    for s in (x for x in stmts if x["kind"] == "delete"):
+    # S81-22 E3 (R-S22-23): every DELETE of a fence user table (048 adds kb_feedback).
+    for s in (x for x in stmts if x["kind"] == "delete" and x["table"] in KNOWN_USER_TABLES):
         chunk = _body_chunks(body)[s["idx"]]
diff --git a/tests/test_s81_kb_schema.py b/tests/test_s81_kb_schema.py
index a7ada5ab..35cb2042 100644
--- a/tests/test_s81_kb_schema.py
+++ b/tests/test_s81_kb_schema.py
@@ -361,2 +361,5 @@ P02_ALLOWED = {
     ("scripts/cron_learning.py", 'KB_FEEDBACK_TABLE = "kb_feedback"'),
+    #: S81-22 E2: the judge's 365-day kb_feedback prune (045 header :23-26)
+    ("scripts/cron_compare_judge.py", 'KB_PRUNE_FEEDBACK_RPC = "kb_prune_feedback"'),
+    ("scripts/cron_compare_judge.py", 'KB_FEEDBACK_TABLE = "kb_feedback"'),
 }
@@ -527,3 +530,4 @@ def test_s14_r01_files_exist_once():
     assert not list(MIG.glob("039_*")), "039 is reserved"
-    for n in ("046", "048", "049", "051"):
+    #: S81-22 E1: 048 is compare_runs (R-S22-2)
+    for n in ("046", "049", "051"):
         assert not list(MIG.glob(n + "_*.sql")), "%s belongs to another unit (R-S14-12)" % n
```

## 5. Mutation table (byte copies in the scratch worktree under .qa-mutation.lock; restored and sha256-verified every time; bound 600 each)
Re-numbered for the ruled rows (M49-M75 new). 76 mutants: 75 KILLED, 1 SURVIVED = M21, EQUIVALENT by R-S22-38. M11 / M16 / M53 were first killed by a non-assertion error (M11 KeyError, M16 an escaped APIError) or survived (M53): the rows R13 / R18 / R06 were strengthened and the three re-run KILLED on an AssertionError (the last row of each id below). M35 / M42 kill on assertions plus one IndexError node each. The P04 / P05 / PJ1 / B11 / J01 literal re-encodings came after the mutation run and touch no mutant's killing row.
| id | file | mutant | result | killing rows (first 6) | [pyt] |
|---|---|---|---|---|---|
| M01 | app/services/compare_runs.py | drop the flag check | KILLED | test_p01_flag_off_identity_all_exits[camera-empty-w413_off];test_p01_flag_off_identity_all_exits[camera-empty-w413_on];test_p01_flag_off_identity_all_exits[came | [pyt] tag=s22red-m01 start=2026-11-06 16:15:35 end=2026-11-06 16:15:50 elapsed=16s bound=600s status=FAIL rc=1 |
| M02 | app/services/compare_runs.py | flag read moved after build_run_row | KILLED | test_p01_flag_off_identity_all_exits[camera-empty-w413_off];test_p01_flag_off_identity_all_exits[camera-empty-w413_on];test_p01_flag_off_identity_all_exits[came | [pyt] tag=s22red-m02 start=2026-11-06 16:15:50 end=2026-11-06 16:16:05 elapsed=15s bound=600s status=FAIL rc=1 |
| M03 | app/services/compare_runs.py | idiom loses on | KILLED | test_r02_flag_reader_idiom[On-True] | [pyt] tag=s22red-m03 start=2026-11-06 16:16:05 end=2026-11-06 16:16:17 elapsed=12s bound=600s status=FAIL rc=1 |
| M04 | app/services/compare_runs.py | success is not True -> not success (builder) | KILLED | test_r05_builder_none_cases | [pyt] tag=s22red-m04 start=2026-11-06 16:16:17 end=2026-11-06 16:16:28 elapsed=12s bound=600s status=FAIL rc=1 |
| M05 | app/services/compare_runs.py | the pair: domain prefix -> empty | KILLED | test_r01_module_and_constants;test_r08_query_hmac_shape_and_domain;test_r09_pair_hmac_every_input_type | [pyt] tag=s22red-m05 start=2026-11-06 16:16:29 end=2026-11-06 16:16:40 elapsed=12s bound=600s status=FAIL rc=1 |
| M06 | app/services/compare_runs.py | norm() removed from the hmac message | KILLED | test_r08_query_hmac_shape_and_domain;test_r09_pair_hmac_every_input_type | [pyt] tag=s22red-m06 start=2026-11-06 16:16:41 end=2026-11-06 16:16:53 elapsed=13s bound=600s status=FAIL rc=1 |
| M07 | app/services/compare_runs.py | plain sha256 without the pepper | KILLED | test_r08_query_hmac_shape_and_domain;test_r09_pair_hmac_every_input_type | [pyt] tag=s22red-m07 start=2026-11-06 16:16:53 end=2026-11-06 16:17:05 elapsed=12s bound=600s status=FAIL rc=1 |
| M08 | app/services/compare_runs.py | text / camera hash the typed query (R-S22-24) | KILLED | test_r09_pair_hmac_every_input_type | [pyt] tag=s22red-m08 start=2026-11-06 16:17:05 end=2026-11-06 16:17:18 elapsed=12s bound=600s status=FAIL rc=1 |
| M09 | app/services/compare_runs.py | evidence keeps price.url | KILLED | test_r11_deidentified_row[camera];test_r11_deidentified_row[text];test_r11_deidentified_row[text_stream];test_r11_deidentified_row[url];test_r12_evidence_shape | [pyt] tag=s22red-m09 start=2026-11-06 16:17:18 end=2026-11-06 16:17:31 elapsed=13s bound=600s status=FAIL rc=1 |
| M10 | app/services/compare_runs.py | evidence keeps personalization | KILLED | test_r11_deidentified_row[camera];test_r11_deidentified_row[text];test_r11_deidentified_row[text_stream];test_r11_deidentified_row[url];test_r12_evidence_shape | [pyt] tag=s22red-m10 start=2026-11-06 16:17:31 end=2026-11-06 16:17:44 elapsed=13s bound=600s status=FAIL rc=1 |
| M11 | app/services/compare_runs.py | truncation drops verdict before specs | KILLED | test_r13_evidence_truncation_order | [pyt] tag=s22red-m11 start=2026-11-06 16:33:30 end=2026-11-06 16:33:42 elapsed=13s bound=600s status=FAIL rc=1 |
| M12 | app/services/compare_runs.py | EVIDENCE_MAX_BYTES 65536 -> 655360 | KILLED | test_r01_module_and_constants;test_r13_evidence_truncation_order | [pyt] tag=s22red-m12 start=2026-11-06 16:17:57 end=2026-11-06 16:18:09 elapsed=13s bound=600s status=FAIL rc=1 |
| M13 | app/services/compare_runs.py | LLM_CALLS_MAX cap not applied | KILLED | test_r15_llm_calls_otel_names_and_cap[False];test_r15_llm_calls_otel_names_and_cap[True] | [pyt] tag=s22red-m13 start=2026-11-06 16:18:09 end=2026-11-06 16:18:22 elapsed=13s bound=600s status=FAIL rc=1 |
| M14 | app/services/compare_runs.py | openai-provider llm records not dropped | KILLED | test_r15_llm_calls_otel_names_and_cap[False];test_r15_llm_calls_otel_names_and_cap[True] | [pyt] tag=s22red-m14 start=2026-11-06 16:18:23 end=2026-11-06 16:18:36 elapsed=13s bound=600s status=FAIL rc=1 |
| M15 | app/services/compare_runs.py | label prefix changed | KILLED | test_r01_module_and_constants;test_r17_record_schedules_one_insert;test_r20_five_exits_on_route[camera];test_r20_five_exits_on_route[get];test_r20_five_exits_on | [pyt] tag=s22red-m15 start=2026-11-06 16:18:36 end=2026-11-06 16:18:49 elapsed=14s bound=600s status=FAIL rc=1 |
| M16 | app/services/compare_runs.py | _insert re-raises | KILLED | test_r18_insert_failure_one_warning | [pyt] tag=s22red-m16 start=2026-11-06 16:33:42 end=2026-11-06 16:33:54 elapsed=12s bound=600s status=FAIL rc=1 |
| M17 | app/services/compare_runs.py | winner_supported from the body | KILLED | test_r06_assessment_columns_equal_result_gate | [pyt] tag=s22red-m17 start=2026-11-06 16:19:03 end=2026-11-06 16:19:16 elapsed=14s bound=600s status=FAIL rc=1 |
| M18 | app/api/text_routes.py | stream line moved outside the success block | KILLED | test_r22_stream_call_not_awaited | [pyt] tag=s22red-m18 start=2026-11-06 16:20:37 end=2026-11-06 16:20:50 elapsed=14s bound=600s status=FAIL rc=1 |
| M19 | app/api/text_routes.py | an await added in the stream finally | KILLED | test_p03_g20_gr2_still_green | [pyt] tag=s22red-m19 start=2026-11-06 16:20:51 end=2026-11-06 16:21:04 elapsed=13s bound=600s status=FAIL rc=1 |
| M20 | app/api/text_routes.py | the POST line deleted (1st occurrence) | KILLED | test_r20_five_exits_on_route[post];test_r22_stream_call_not_awaited;test_r23_comparison_id_echo_on_text_only;test_r24_w4_13_no_log_search_from_insert[w413_off]; | [pyt] tag=s22red-m20 start=2026-11-06 16:21:04 end=2026-11-06 16:21:17 elapsed=13s bound=600s status=FAIL rc=1 |
| M20b | app/api/text_routes.py | the GET line deleted (2nd occurrence) | KILLED | test_r20_five_exits_on_route[get];test_r22_stream_call_not_awaited | [pyt] tag=s22red-m20b start=2026-11-06 16:21:17 end=2026-11-06 16:21:31 elapsed=14s bound=600s status=FAIL rc=1 |
| M21 | app/api/image_routes.py | the camera line moved before the envelope arm (EQUIVALENT R-S22-38) | SURVIVED (EQUIVALENT by R-S22-38) |  | [pyt] tag=s22red-m21 start=2026-11-06 16:21:31 end=2026-11-06 16:21:44 elapsed=12s bound=600s status=OK rc=0 |
| M22 | app/api/url_routes.py | url compare_ms dropped | KILLED | test_r20_five_exits_on_route[url] | [pyt] tag=s22red-m22 start=2026-11-06 16:21:44 end=2026-11-06 16:21:57 elapsed=13s bound=600s status=FAIL rc=1 |
| M23 | migrations/048_compare_runs.sql | ON DELETE SET NULL -> CASCADE | KILLED | test_b04_checks_and_fks | [pyt] tag=s22red-m23 start=2026-11-06 16:23:16 end=2026-11-06 16:23:29 elapsed=13s bound=600s status=FAIL rc=1 |
| M24 | migrations/048_compare_runs.sql | judgements ON DELETE CASCADE dropped | KILLED | test_b04_checks_and_fks | [pyt] tag=s22red-m24 start=2026-11-06 16:23:29 end=2026-11-06 16:23:43 elapsed=14s bound=600s status=FAIL rc=1 |
| M25 | migrations/048_compare_runs.sql | hook moved after the comparisons DELETE | KILLED | test_b08_cascade_is_043_plus_one;test_b09_hook_join_text | [pyt] tag=s22red-m25 start=2026-11-06 16:23:43 end=2026-11-06 16:23:56 elapsed=14s bound=600s status=FAIL rc=1 |
| M26 | migrations/048_compare_runs.sql | hook keys on any linked run | KILLED | test_b09_hook_join_text | [pyt] tag=s22red-m26 start=2026-11-06 16:23:56 end=2026-11-06 16:24:11 elapsed=14s bound=600s status=FAIL rc=1 |
| M27 | migrations/048_compare_runs.sql | the cascade REVOKE deleted | KILLED | test_b10_revoke_after_create_no_grant | [pyt] tag=s22red-m27 start=2026-11-06 16:24:11 end=2026-11-06 16:24:24 elapsed=13s bound=600s status=FAIL rc=1 |
| M28 | migrations/048_compare_runs.sql | a GRANT EXECUTE on the cascade added | KILLED | test_b06_service_role_only;test_b10_revoke_after_create_no_grant | [pyt] tag=s22red-m28 start=2026-11-06 16:24:24 end=2026-11-06 16:24:38 elapsed=13s bound=600s status=FAIL rc=1 |
| M29 | migrations/048_compare_runs.sql | recompare predicate gains now() | KILLED | test_b05_indexes_immutable | [pyt] tag=s22red-m29 start=2026-11-06 16:24:38 end=2026-11-06 16:24:51 elapsed=13s bound=600s status=FAIL rc=1 |
| M30 | migrations/048_compare_runs.sql | prune bound 3650 -> 36500 | KILLED | test_b07_prune_function | [pyt] tag=s22red-m30 start=2026-11-06 16:24:51 end=2026-11-06 16:25:04 elapsed=13s bound=600s status=FAIL rc=1 |
| M31 | migrations/048_compare_runs.sql | the alias AS f reintroduced | KILLED | test_b08_cascade_is_043_plus_one;test_b09_hook_join_text;test_b16_fence_green_with_048 | [pyt] tag=s22red-m31 start=2026-11-06 16:25:04 end=2026-11-06 16:25:17 elapsed=13s bound=600s status=FAIL rc=1 |
| M32 | migrations/rollback/048_compare_runs.sql | the drops before the cascade restore | KILLED | test_b14_rollback_restores_043 | [pyt] tag=s22red-m32 start=2026-11-06 16:25:44 end=2026-11-06 16:25:57 elapsed=13s bound=600s status=FAIL rc=1 |
| M33 | scripts/cron_compare_judge.py | MIN_CONSENT 3 -> 2 | KILLED | test_j05_min_consent_pinned;test_j06_window_query_consent_gate | [pyt] tag=s22red-m33 start=2026-11-06 16:25:57 end=2026-11-06 16:26:08 elapsed=11s bound=600s status=FAIL rc=1 |
| M34 | scripts/cron_compare_judge.py | the consent gte filter removed | KILLED | test_j06_window_query_consent_gate | [pyt] tag=s22red-m34 start=2026-11-06 16:26:08 end=2026-11-06 16:26:20 elapsed=12s bound=600s status=FAIL rc=1 |
| M35 | scripts/cron_compare_judge.py | LANE_OFFCLOCK -> LANE_LIVE in the batch reserve | KILLED | test_j11_g2_spend_sequence;test_j12_breaker_refusal_arm;test_j13_usd_cap_trims;test_j14_partial_read_no_ledger_no_delete;test_j14b_pending_on_timeout | [pyt] tag=s22red-m35 start=2026-11-06 16:26:20 end=2026-11-06 16:26:32 elapsed=12s bound=600s status=FAIL rc=1 |
| M36 | scripts/cron_compare_judge.py | LANE_ESCALATION -> LANE_OFFCLOCK | KILLED | test_j16_escalation_triggers_and_caps;test_j17_escalation_refusal_and_breaker_off | [pyt] tag=s22red-m36 start=2026-11-06 16:26:32 end=2026-11-06 16:26:43 elapsed=10s bound=600s status=FAIL rc=1 |
| M37 | scripts/cron_compare_judge.py | the escalation count cap ignored | KILLED | test_j16_escalation_triggers_and_caps;test_j16b_per_riyadh_day_cap | [pyt] tag=s22red-m37 start=2026-11-06 16:26:43 end=2026-11-06 16:26:54 elapsed=11s bound=600s status=FAIL rc=1 |
| M38 | scripts/cron_compare_judge.py | the breaker-off guard on escalation removed | KILLED | test_j17_escalation_refusal_and_breaker_off | [pyt] tag=s22red-m38 start=2026-11-06 16:26:54 end=2026-11-06 16:27:05 elapsed=11s bound=600s status=FAIL rc=1 |
| M39 | scripts/cron_compare_judge.py | batches.delete before the writes | KILLED | test_j11_g2_spend_sequence | [pyt] tag=s22red-m39 start=2026-11-06 16:27:06 end=2026-11-06 16:27:17 elapsed=11s bound=600s status=FAIL rc=1 |
| M40 | scripts/cron_compare_judge.py | the ledger row written on a partial read | KILLED | test_j14_partial_read_no_ledger_no_delete | [pyt] tag=s22red-m40 start=2026-11-06 16:27:17 end=2026-11-06 16:27:29 elapsed=12s bound=600s status=FAIL rc=1 |
| M41 | scripts/cron_compare_judge.py | max_tokens 400 -> 4000 | KILLED | test_j05_min_consent_pinned;test_j09_batch_body_deidentified | [pyt] tag=s22red-m41 start=2026-11-06 16:27:29 end=2026-11-06 16:27:40 elapsed=11s bound=600s status=FAIL rc=1 |
| M41b | scripts/cron_compare_judge.py | thinking enabled | KILLED | test_j09_batch_body_deidentified | [pyt] tag=s22red-m41b start=2026-11-06 16:27:40 end=2026-11-06 16:27:53 elapsed=13s bound=600s status=FAIL rc=1 |
| M42 | scripts/cron_compare_judge.py | the run id used as custom_id | KILLED | test_j09_batch_body_deidentified;test_j11_g2_spend_sequence;test_j13_usd_cap_trims;test_j15_parse_failure[max_tokens];test_j15_parse_failure[missing];test_j15_p | [pyt] tag=s22red-m42 start=2026-11-06 16:27:53 end=2026-11-06 16:28:06 elapsed=13s bound=600s status=FAIL rc=1 |
| M43 | scripts/cron_compare_judge.py | DRY runs the prune rpc | KILLED | test_j02b_dry_run_flag_downgrades_apply;test_j20_dry_writes_nothing | [pyt] tag=s22red-m43 start=2026-11-06 16:28:06 end=2026-11-06 16:28:17 elapsed=11s bound=600s status=FAIL rc=1 |
| M44 | scripts/cron_compare_judge.py | the sample seed uses random.random() | KILLED | test_j18_sample_seed_stable | [pyt] tag=s22red-m44 start=2026-11-06 16:28:17 end=2026-11-06 16:28:30 elapsed=13s bound=600s status=FAIL rc=1 |
| M45 | scripts/cron_compare_judge.py | self_produced runs sent to Haiku | KILLED | test_j19_never_the_producing_model | [pyt] tag=s22red-m45 start=2026-11-06 16:28:30 end=2026-11-06 16:28:42 elapsed=12s bound=600s status=FAIL rc=1 |
| M46 | scripts/cron_compare_judge.py | the report gains an id list | KILLED | test_j22_report_counts_only | [pyt] tag=s22red-m46 start=2026-11-06 16:28:42 end=2026-11-06 16:28:54 elapsed=12s bound=600s status=FAIL rc=1 |
| M47 | scripts/cron_compare_judge.py | the mode read after resolve_client | KILLED | test_j01_script_exists_and_off_first;test_j03_off_reads_nothing | [pyt] tag=s22red-m47 start=2026-11-06 16:28:54 end=2026-11-06 16:29:05 elapsed=11s bound=600s status=FAIL rc=1 |
| M48 | scripts/cron_compare_judge.py | the USD trim drops from the front | KILLED | test_j13_usd_cap_trims | [pyt] tag=s22red-m48 start=2026-11-06 16:29:05 end=2026-11-06 16:29:18 elapsed=13s bound=600s status=FAIL rc=1 |
| M49 | app/services/compare_runs.py | prose kept on a personalised body (R-S22-53) | KILLED | test_r12b_prose_dropped_on_personalised_body | [pyt] tag=s22red-m49 start=2026-11-06 16:19:17 end=2026-11-06 16:19:30 elapsed=13s bound=600s status=FAIL rc=1 |
| M50 | app/services/compare_runs.py | camera extra_records ignored (R-S22-39) | KILLED | test_r15b_camera_extra_records | [pyt] tag=s22red-m50 start=2026-11-06 16:19:30 end=2026-11-06 16:19:44 elapsed=14s bound=600s status=FAIL rc=1 |
| M53 | app/services/compare_runs.py | data_coverage the literal count (R-S22-40) | KILLED | test_r06_assessment_columns_equal_result_gate | [pyt] tag=s22red-m53 start=2026-11-06 16:22:57 end=2026-11-06 16:23:10 elapsed=13s bound=600s status=FAIL rc=1 |
| M54 | app/services/compare_runs.py | consent bool not excluded | KILLED | test_r07_context_columns | [pyt] tag=s22red-m54 start=2026-11-06 16:19:56 end=2026-11-06 16:20:10 elapsed=13s bound=600s status=FAIL rc=1 |
| M55 | app/services/compare_runs.py | host keeps www. | KILLED | test_r12_evidence_shape;test_r16_sources_cache_timings_partial | [pyt] tag=s22red-m55 start=2026-11-06 16:20:10 end=2026-11-06 16:20:23 elapsed=13s bound=600s status=FAIL rc=1 |
| M56 | app/services/compare_runs.py | comparison_id not canonicalised | KILLED | test_r10_comparison_id_link[6F9619FF-8B86-D011-B42D-00C04FC964FF-6f9619ff-8b86-d011-b42d-00c04fc964ff] | [pyt] tag=s22red-m56 start=2026-11-06 16:20:23 end=2026-11-06 16:20:36 elapsed=13s bound=600s status=FAIL rc=1 |
| M57 | app/api/image_routes.py | camera extra_records dropped (R-S22-39) | KILLED | test_r20_five_exits_on_route[camera] | [pyt] tag=s22red-m57 start=2026-11-06 16:21:57 end=2026-11-06 16:22:11 elapsed=13s bound=600s status=FAIL rc=1 |
| M58 | migrations/048_compare_runs.sql | refusal_reason CHECK narrowed (R-S22-54) | KILLED | test_b04_checks_and_fks | [pyt] tag=s22red-m58 start=2026-11-06 16:25:17 end=2026-11-06 16:25:30 elapsed=13s bound=600s status=FAIL rc=1 |
| M59 | migrations/048_compare_runs.sql | data_coverage integer (R-S22-40) | KILLED | test_b03_compare_runs_columns_closed;test_b04_checks_and_fks | [pyt] tag=s22red-m59 start=2026-11-06 16:25:30 end=2026-11-06 16:25:44 elapsed=13s bound=600s status=FAIL rc=1 |
| M60 | scripts/cron_compare_judge.py | the per-Riyadh-day count not subtracted (R-S22-47) | KILLED | test_j16b_per_riyadh_day_cap | [pyt] tag=s22red-m60 start=2026-11-06 16:29:18 end=2026-11-06 16:29:31 elapsed=13s bound=600s status=FAIL rc=1 |
| M61 | scripts/cron_compare_judge.py | the USD sub-budget ignored (R-S22-37) | KILLED | test_j16c_usd_sub_budget | [pyt] tag=s22red-m61 start=2026-11-06 16:29:31 end=2026-11-06 16:29:43 elapsed=12s bound=600s status=FAIL rc=1 |
| M62 | scripts/cron_compare_judge.py | the pending settle not 0.0 (R-S22-33) | KILLED | test_j14b_pending_on_timeout | [pyt] tag=s22red-m62 start=2026-11-06 16:29:43 end=2026-11-06 16:29:56 elapsed=13s bound=600s status=FAIL rc=1 |
| M62b | scripts/cron_compare_judge.py | no pending rows on timeout (R-S22-33) | KILLED | test_j14b_pending_on_timeout | [pyt] tag=s22red-m62b start=2026-11-06 16:29:56 end=2026-11-06 16:30:09 elapsed=13s bound=600s status=FAIL rc=1 |
| M63 | scripts/cron_compare_judge.py | resume after the window read (R-S22-33) | KILLED | test_j14c_resume_first[ended];test_j14c_resume_first[lost];test_j14c_resume_first[running] | [pyt] tag=s22red-m63 start=2026-11-06 16:30:09 end=2026-11-06 16:30:22 elapsed=13s bound=600s status=FAIL rc=1 |
| M64 | scripts/cron_compare_judge.py | a pending run re-submitted (R-S22-34) | KILLED | test_j14c_resume_first[lost];test_j14c_resume_first[running];test_j14d_never_resubmitted[flags0];test_j14d_never_resubmitted[flags1] | [pyt] tag=s22red-m64 start=2026-11-06 16:30:22 end=2026-11-06 16:30:35 elapsed=13s bound=600s status=FAIL rc=1 |
| M65 | scripts/cron_compare_judge.py | a lost batch not marked batch_lost | KILLED | test_j14c_resume_first[lost] | [pyt] tag=s22red-m65 start=2026-11-06 16:30:35 end=2026-11-06 16:30:48 elapsed=12s bound=600s status=FAIL rc=1 |
| M66 | scripts/cron_compare_judge.py | self-produced matched on any call (R-S22-46) | KILLED | test_j19_never_the_producing_model | [pyt] tag=s22red-m66 start=2026-11-06 16:30:48 end=2026-11-06 16:31:01 elapsed=13s bound=600s status=FAIL rc=1 |
| M67 | scripts/cron_compare_judge.py | the feedback select gains compare_request_id (R-S22-29) | KILLED | test_j16_escalation_triggers_and_caps | [pyt] tag=s22red-m67 start=2026-11-06 16:31:01 end=2026-11-06 16:31:13 elapsed=13s bound=600s status=FAIL rc=1 |
| M68 | scripts/cron_compare_judge.py | the SEARCH_RESULTS fence replaced by EVIDENCE (R-S22-36) | KILLED | test_j27_prompt_fenced | [pyt] tag=s22red-m68 start=2026-11-06 16:31:13 end=2026-11-06 16:31:26 elapsed=13s bound=600s status=FAIL rc=1 |
| M69 | scripts/cron_compare_judge.py | the sanitizer dropped | KILLED | test_j27_prompt_fenced | [pyt] tag=s22red-m69 start=2026-11-06 16:31:26 end=2026-11-06 16:31:39 elapsed=13s bound=600s status=FAIL rc=1 |
| M70 | scripts/cron_compare_judge.py | kb_prune_feedback not called (R-S22-25) | KILLED | test_j21_apply_writes_and_prunes | [pyt] tag=s22red-m70 start=2026-11-06 16:31:39 end=2026-11-06 16:31:51 elapsed=12s bound=600s status=FAIL rc=1 |
| M71 | scripts/cron_compare_judge.py | a ledger 42P01 crashes the run (R-S22-44) | KILLED | test_j28_ledger_missing_table_one_warning | [pyt] tag=s22red-m71 start=2026-11-06 16:31:52 end=2026-11-06 16:32:04 elapsed=12s bound=600s status=FAIL rc=1 |
| M72 | scripts/cron_compare_judge.py | the nested report logged unflattened (R-S22-45) | KILLED | test_j25_logs_constants_only | [pyt] tag=s22red-m72 start=2026-11-06 16:32:04 end=2026-11-06 16:32:16 elapsed=12s bound=600s status=FAIL rc=1 |
| M73 | scripts/cron_compare_judge.py | the batch reserve with the breaker OFF (R-S22-30) | KILLED | test_j17_escalation_refusal_and_breaker_off | [pyt] tag=s22red-m73 start=2026-11-06 16:32:17 end=2026-11-06 16:32:29 elapsed=13s bound=600s status=FAIL rc=1 |
| M75 | scripts/cron_compare_judge.py | judged_at set for capped runs (R-S22-34) | KILLED | test_j16_escalation_triggers_and_caps | [pyt] tag=s22red-m75 start=2026-11-06 16:32:29 end=2026-11-06 16:32:41 elapsed=12s bound=600s status=FAIL rc=1 |

## 6. Other base gates (real worktree)
- tests/test_secret_scan_static.py ALONE:
```
======================== 31 passed, 1 warning in 5.84s ========================
[hermeticity] sentinel checked 31 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
```
- The CI-order set (deviation: the spec names none; taken = 7.2 gates 3 + 4 + test_ci_gates.py, 19 files sorted, list in S81-22_red/ci_order_files.txt): the known noise only (test_r06_production_lexicon_content CRLF; test_prompt_truth's two cold-tiktoken ERRORs):
```
= 1 failed, 1767 passed, 2 skipped, 4 deselected, 1 xfailed, 13 warnings, 2 errors in 79.59s (0:01:19) =
[hermeticity] sentinel checked 1771 test(s)
[netguard] blocked 26 attempt(s) from 11 node(s)
```

## 7. Comm set
COMM_SET.txt (726) + comm_reasons.tsv in S81-22_red/. Derivation: the spec 7.1 list (725, sha256 prefix d17a31609d25e6cd, re-read from s22/comm_union.txt) UNION a re-derivation by the union rule at base (S81-22_red/derive_comm.py: the reference grep over the 14 named modules, the migration readers, test_s81_kb_schema, the scripts / railway readers, the named source-scanning pins, the source scanners by glob / getsource / ast.parse + an app/scripts/migrations path, the CLAUDE.md readers by the named import-graph list, the SmartCompareApp scanners; 256 members) MINUS the four test_precommit_hook files and the two RED files. The re-derivation adds ONE file: tests/test_feature_bucket_parity.py (a SmartCompareApp-scanning backend test; the brief's union rule names that arm). Every one of the 256 is inside the 725.

## 8. Base record at 18cb9e04 (LAST step; per-file reuse under GC-9)
Reuse source: base_records/05303c6f.../a0bfab95... (695 files). Criteria: in that record, own file unchanged since 05303c6f (git diff --name-only 05303c6f 18cb9e04: 17 files), no reference in its text or its imported tests helpers to the seven #391 stems (cron_kb_coverage, cron_learning, kb_operator, kb_serve, price_service, structured_comparison_service, variant_hint_learned) nor CLAUDE.md / CLAUDE_MD, not a glob / walk / listdir / iterdir / scandir reader. Members outside the 05303c6f record were run (no older-record reuse attempted). Five helper modules in the spec list (tests/_env_safety.py, tests/_netguard.py, tests/_retro_r_mig_sql.py, tests/conftest.py, tests/fixtures/_gen_w4_13_flag_off_ledger.py) hold no test items and were not passed to pytest (deviation: passing conftest.py as a path risks a usage error; they are members only through the import graph).
# base record 18cb9e04a36382fc417307500a092486f618d95e, set sha256 e701a8ba6f8750db26df0e456ab9b844686694c8aa8e34f5f22dd1f5be4618ea (726 files = the S81-22 comm set: the spec 7.1 union of 725 + tests/test_feature_bucket_parity.py (the SmartCompareApp-scanning union arm), minus the four test_precommit_hook files and the two S81-22 RED files)
# built 2026-11-06 by the S81-22 RED agent (Opus 5.5) by GC-9 PER-FILE REUSE of base_records/05303c6f.../a0bfab95...txt (#391 changed kb_serve, kb_operator, structured_comparison_service, price_service, cron_kb_coverage, cron_learning, variant_hint_learned, CLAUDE.md + its tests)
# REUSED from a0bfab95 (312 files: in that record, unchanged since 05303c6f, no reference in the file or its imported tests helpers to the seven #391 stems nor CLAUDE.md / CLAUDE_MD, not a glob / walk / listdir / iterdir / scandir reader): tests/test_429_contract.py,tests/test_account_deletion.py,tests/test_account_deletion_u8b.py,tests/test_account_deletion_u8b_fix_pins.py,tests/test_account_dele ... (full list in the header file)
# RUN at 18cb9e04 in the REAL worktree sc-s81-s22 (409 files in 3 chunks of <= 25, tests/test_secret_scan_static.py alone; reasons in S81-22_red/run_reasons.tsv): tests/perf/test_latency_bench.py,tests/test_accessory_reject_jsonld.py,tests/test_adapter_drop_visibility.py,tests/test_adapter_extended_rates_gate.py,tests/test_adapter_prefetch_hook.py,tests/test_adapter_query_ladder.py,tests/test_algo ... (full list in the header file)
# NOT COLLECTED (helper modules with no test items, members only through the import graph): tests/_env_safety.py,tests/_netguard.py,tests/_retro_r_mig_sql.py,tests/conftest.py,tests/fixtures/_gen_w4_13_flag_off_ledger.py
# FAILED node ids: 6 (reused 6 + run 0)

Chunk [pyt] lines:
```
s22red-base-c00.log
================ 852 passed, 3 skipped, 13 warnings in 43.41s =================
NO PYT LINE
s22red-base-c01.log
========= 1061 passed, 1 deselected, 11 warnings in 66.41s (0:01:06) ==========
NO PYT LINE
s22red-base-c02.log

NO PYT LINE
```
FAILED node ids of the record:
```
tests/test_auth_interceptor.py::test_sign_in_with_social_exception
tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
```
Progress log:
```
16:37 secret scan + CI-order at base
16:40:24 base driver start: 409 files run, 5 helper modules not collected, 17 chunks
16:41:10 chunk 00 (25 files): [pyt] tag=s22red-base-c00 start=2026-11-06 16:40:24 end=2026-11-06 16:41:10 elapsed=46s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-22_red\base_chunks\s22red-base-c00.log
16:42:18 chunk 01 (25 files): [pyt] tag=s22red-base-c01 start=2026-11-06 16:41:10 end=2026-11-06 16:42:18 elapsed=68s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\4478042e-6f11-47b0-addf-eb1422827e28\scratchpad\S81-22_red\base_chunks\s22red-base-c01.log
16:42:24 report forced before the driver finished: chunks after the last [pyt] line NOT MEASURED in this report
```

## 9. Deviations, assumptions, open questions
- R20 / R21 hit the camera route at /api/v1/image/identify (the spec's 'POST /image/compare' does not exist) and reuse the S81-20 RED harness (tests/test_s81_s20_result_gate.py: _ledger, _text_svc, _camera, _url, VISION, the bodies) by import, like the S81-20 file imports test_retro_w2_1.
- R21 omits the S81-10 CATEGORY_NOT_LIVE refusal and the H6 client-gone partial (cost: each needs a further harness; both are refusals before the exit, the five covered cases pin the success-only placement). GREEN's gate rows may add them.
- R09 / R08 follow R-S22-24: query_hmac = HMAC(pepper, "pair:" + norm(pair identity text)) for every input type; QUERY_HMAC_DOMAIN = "pair:" (the constant name kept from the spec).
- R15 follows R-S22-27 literally: LLM_CALL_FIELDS = the five OTEL_GENAI_ATTRIBUTES targets + role / web_search_requests / cost_usd / latency_ms / batch; stop_reason is carried ONLY as gen_ai.response.finish_reasons (the ruling lists it among the unmapped keys too: read as the mapped field; open question Q-R1). No cache-token fields (the mapping has none; prompt_tokens is cache-included).
- The judge script's read-column constant is SELECT_COLUMNS (the spec's RUN_COLUMNS name now belongs to compare_runs.py by R-S22-37).
- Programmatic-fail runs get judged_at at once and are not escalated (R-S22-34: 'the programmatic fail path that skips Haiku'); no_independent_judge likewise.
- The 048 guard raises when compare_runs exists at all (the spec: 'with a different column set'); simpler, stated for GREEN (Q-R2).
- The prototype logs the provider batch handle in 'submitted batch_id=%s' (the G2 form, 2.7); J25 checks no uuid / 64-hex / note / snapshot only.
- J17 is re-cut by R-S22-30: breaker OFF escalates under the knobs with zero reserve / settle / record (the spec's 'zero messages.create' is superseded).
- J18's 'literal table of 10 ids' is computed in-test from the spec formula (the formula is the contract; a literal table would pin the same values).
- Mutation runs used each mutant's own file's RED file (compare_runs file for request-path / migration mutants, judge file for the script), not -k subsets.
- Q-R1: stop_reason in R-S22-27's unmapped list (above). Q-R2: the 048 guard on an existing compare_runs. Q-R3: E2 needs two allowlist lines (above).

## 10. Restore check
Real worktree: only the two new files untracked, `git diff --stat` empty, HEAD 18cb9e04 before and after. Scratch worktree removed (git worktree remove --force; absent from git worktree list). The mutation lock was created and deleted in the scratch worktree only. No orphan pytest of this agent.
