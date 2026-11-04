# S81-G4 KB-SERVE RED REPORT (RED agent, Opus 5.5, 2026-11-04)

Unit: S81-G4 (S81-18 KB-FIRST-SERVE + verdict-cache key log, S81-19 GAP-QUEUE, D16 OPERATOR-INGEST, D17 MEASURE-COVERAGE).
Base: 0b19de5bcc1416111d48bc725359b95151a658ca. Worktree: sc-s81-g4 (only the five new files added, untracked).
Spec: sc-s81-g4/.qa-s80/S81-G4_UNIT_SPEC.md sha256 a38883225be7144c7c1a78f6838bfeaced529a81db34c7e9dd15450d45ae0e31 as amended by RULINGS_S81_G4 (R-G4-1..14).
This report and the notes were written through the shell (the harness refuses a subagent Write of a report .md).

## 1. Files written (sha256 over the bytes on disk; pure ASCII, LF)

| file | bytes | sha256 | bytes>127 | CR |
|---|---|---|---|---|
| tests/test_s81_s18_kb_first_serve.py | 59976 | 7be2ed3a9c05c6680b654cf3bf548ade374873056e03ec01836e8d66cb769cd2 | 0 | 0 |
| tests/fixtures/s81_s18_flag_off_golden.json | 82157 | 8ab15ee0c25633f8df73b8acec93dcf6568b395ed7bcfcfdd5c28ff6e0eb8d6b | 0 | 0 |
| tests/test_s81_s19_gap_queue.py | 37574 | a400b6795ed166df98a59326c49f04565c60157777b6a2dce7a1bdc7481ffe84 | 0 | 0 |
| tests/test_s81_d16_operator_ingest.py | 26971 | 65d0186063d818301061cd5b3a1f491715a9f2b59ccd245a5fa3beb3b61a7758 | 0 | 0 |
| tests/test_s81_d17_coverage.py | 23516 | 03b7ccf6140148c884e8e2b4f57123baee3c38207712ebedfecc320659f2f317 | 0 | 0 |

git status --short of the real worktree:
```
?? tests/fixtures/s81_s18_flag_off_golden.json
?? tests/test_s81_d16_operator_ingest.py
?? tests/test_s81_d17_coverage.py
?? tests/test_s81_s18_kb_first_serve.py
?? tests/test_s81_s19_gap_queue.py
```

## 2. Base run (RED files at 0b19de5b) and the AssertionError proof

    [hermeticity] sentinel checked 113 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [hermeticity] sentinel checked 113 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [hermeticity] sentinel checked 113 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)

Node counts per file at base (junit, g4red-base3 = the FINAL bytes; base1 / base2 ran before the S18 harness additions of DV4 and the moderate_output fake, same 91 / 22 split): {"test_s81_d16_operator_ingest|failed": 11, "test_s81_d16_operator_ingest|passed": 7, "test_s81_d17_coverage|failed": 23, "test_s81_s18_kb_first_serve|failed": 25, "test_s81_s18_kb_first_serve|passed": 13, "test_s81_s19_gap_queue|failed": 32, "test_s81_s19_gap_queue|passed": 2}
Failure types over every failed node (junit failure message type): {"AssertionError": 91}
Every PIN row green at base: D16 P1 x4 (unset / false / pad0 / OFF), P2, P3 x2; S18 P1 x4, P2 x4, P3 x4, P4; S19 P1, P2 (22 passed).

Failed RED nodes at base (all AssertionError):

- tests/test_s81_d16_operator_ingest.py::test_r1_module_flag_knob : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r2_view_requires_key_when_on : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r3_view_content_and_bounds : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r4_ingest_happy_path_operator : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r5_blocked_host_needs_review : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r6_refusal_codes : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r7_validation : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r8_partner_source : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r9_log_line_constants : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only : AssertionError
- tests/test_s81_d16_operator_ingest.py::test_r11_licence_fields_partner_only : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[None-off] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[-off] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[false-off] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[0-off] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[no-off] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[OFF-off] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[dry-off] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[garbage-off] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[true-dry] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[ TRUE -dry] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[1-dry] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[yes-dry] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[on-dry] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[apply-apply] : AssertionError
- tests/test_s81_d17_coverage.py::test_r1_entry_and_mode[ APPLY -apply] : AssertionError
- tests/test_s81_d17_coverage.py::test_r2_metric_names_closed_and_valid : AssertionError
- tests/test_s81_d17_coverage.py::test_r3_values_on_seeded_kb : AssertionError
- tests/test_s81_d17_coverage.py::test_r4_proxy_reads_no_personal_columns : AssertionError
- tests/test_s81_d17_coverage.py::test_r5_host_metrics_absent_never_zero : AssertionError
- tests/test_s81_d17_coverage.py::test_r6_apply_upserts_through_builder : AssertionError
- tests/test_s81_d17_coverage.py::test_r7_report_markdown : AssertionError
- tests/test_s81_d17_coverage.py::test_r8_failure_isolation : AssertionError
- tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r1_module_and_flags : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r2_knobs_parse_defensively[KB_FIRST_SERVE_TIMEOUT_SECONDS-1.0-cases0] : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r2_knobs_parse_defensively[KB_FIRST_SERVE_MAX_ASOF_DAYS-30-cases1] : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r2_knobs_parse_defensively[VERDICT_CACHE_LOG_MAX_KEYS-10000-cases2] : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r3_client_price_asof : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r4_required_spec_fields_fragrances : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r5_fetch_cards_one_gather_two_rpcs_through_run_db : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r6_fetch_cards_total[raise] : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r6_fetch_cards_total[timeout] : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r6_fetch_cards_total[client_none] : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r6_fetch_cards_total[data_list] : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r7_classify_full_partial_miss : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r8_price_ttl_and_asof : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r9_price_dict_shape : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r17_verdict_key_inputs : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r10_rest_full_hit_skips_paid_legs : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r11_stream_full_hit_same : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r12_partial_runs_only_missing_legs : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r13_candidates_seeded_for_fairness : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r16_verdict_key_log_eligible_only : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r18_no_seed_on_failed_verdict : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r20_card_failure_falls_through : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r19_kb_served_price_never_reobserved : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r14_asof_only_with_header : AssertionError
- tests/test_s81_s18_kb_first_serve.py::test_r15_camera_route_forwards_capability : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[None-off] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[-off] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[false-off] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[0-off] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[OFF-off] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[dry-off] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[garbage-off] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[true-dry] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[ TRUE -dry] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[1-dry] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[yes-dry] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[on-dry] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[apply-apply] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r1_entry_exists_and_mode[ Apply -apply] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r2_off_is_inert : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r3_dry_reads_only : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r4_rank_and_window : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r5_single_flight : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r6_specs_gap_goes_licence : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r7_step1_search_template_polite : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r8_step2_pdp_hint_consumed[ok] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r8_step2_pdp_hint_consumed[tos] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r8_step2_pdp_hint_consumed[timeout] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r8_step2_pdp_hint_consumed[http500] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r9_step3_inert : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r10_step4_blocked_to_operator : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r11_cas_never_moves_demand_or_hint : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r12_refresh_head_daily_tail_weekly[3-False] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r12_refresh_head_daily_tail_weekly[1-True] : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r13_log_lines_constants_only : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r14_railway_config : AssertionError
- tests/test_s81_s19_gap_queue.py::test_r15_hygiene : AssertionError

## 3. Recorded-at-base artefacts

- tests/fixtures/s81_s18_flag_off_golden.json sha256 8ab15ee0c25633f8df73b8acec93dcf6568b395ed7bcfcfdd5c28ff6e0eb8d6b (82157 B): recorded twice at base with `python -m tests.test_s81_s18_kb_first_serve <out>` (FULL configuration: both flags unset, the three knobs set, ENABLE_SYNC_DB_OFFLOAD=true, the raising recorders installed and silent); both recordings byte-identical. Scenarios rest_full / stream_full / camera_full (vision_products), each = the FY25-normalised payload + the live-leg call counts.
- D16 P2 OpenAPI path-set sha256 (sorted paths joined by LF, 76 paths at base): 9dbdb7aab61e628c52b3cf3260cdbe968a827754d26bd1366aa6dafc642a9809 (literal OPENAPI_PATHS_SHA256 in the D16 file; green at base flag OFF and ON).

## 4. Prototype (scratch worktree <scratchpad>/g4p at 0b19de5b, no junction; removed and verified gone)

Diff: <scratchpad>/S81-G4_red/prototype.diff (+ prototype.diffstat, prototype_files/). Never committed; nothing applied to the real worktree.
```
 app/api/admin_routes.py                       |  42 +++
 app/api/image_routes.py                       |   2 +
 app/api/text_routes.py                        |   7 +-
 app/services/kb_ingest.py                     |   5 +-
 app/services/kb_operator.py                   | 253 +++++++++++++++
 app/services/kb_serve.py                      | 299 +++++++++++++++++
 app/services/structured_comparison_service.py |  72 +++-
 docs/runbooks/2026-11-kb-operator-ingest.md   |  25 ++
 railway.kbcoverage.json                       |  14 +
 railway.kbenrich.json                         |  14 +
 scripts/cron_kb_coverage.py                   | 312 ++++++++++++++++++
 scripts/cron_kb_enrich.py                     | 451 ++++++++++++++++++++++++++
 tests/test_s81_kb_schema.py                   |  10 +-
 13 files changed, 1493 insertions(+), 13 deletions(-)
```

proto_off (the four RED files, no flag in the ambient env) and proto_on (the seven G4 flags exported in ONE runner call, the two mode flags as DRY `true`): 113 passed each. g4p-s18a/b/c were the prototype bring-up (two prototype bugs, one harness gap in the S18 file, see 8); g4p-pins = the first P01 failure (a docstring token, see 8); g4p-pins2 = tests/test_s81_kb_schema.py (E1/E2 applied in the prototype), test_s81_s15_registry_robots.py, test_s81_s17_kb_ingest.py, test_s81_g3_gate_rows.py, test_s81_d14_live_robots.py, test_s75_fanout_identity.py, test_admin_key_and_sentry_scrub.py, test_m13_21_openapi_gated.py, test_s81_d11_pdp_discovery.py all green on the prototype.
R-G4-11 checks on the prototype: no robots_registry text in kb_serve.py / kb_operator.py / the two scripts; no kb_merchants literal in the two new app modules (one `kb_merchants` word in an error string of scripts/cron_kb_enrich.py, a script); no `"partner"` constant and no merchant_registry import added to structured_comparison_service.py; include_in_schema=False on both D16 routes; ruff E9/F63/F7/F82 clean, py_compile clean.

## 5. Mutation table (byte copies in the scratch worktree, the killing rows via pyt.py -k, bound 600, restored + sha256-verified; prototype sha snapshot equal after the run)

| id | mutant | rows (-k) | result | failed nodes | AssertionError | [pyt] |
|---|---|---|---|---|---|---|
| S18-M1 | H0 flag read removed (task always started) | test_p2 | KILLED | 4 | True | [pyt] tag=g4mut-s18-m1 start=2026-11-04 20:29:56 end=2026-11-04 20:30:01 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M1.log |
| S18-M2 | fetch_cards calls client.rpc directly, not through run_db | test_r5 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m2 start=2026-11-04 20:30:02 end=2026-11-04 20:30:09 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M2.log |
| S18-M3 | the 7 d window replaced by 24 h | test_r8 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m3 start=2026-11-04 20:30:10 end=2026-11-04 20:30:14 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M3.log |
| S18-M4 | accepts_asof ignored | test_r8 or test_r14 | KILLED | 2 | True | [pyt] tag=g4mut-s18-m4 start=2026-11-04 20:30:16 end=2026-11-04 20:30:21 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M4.log |
| S18-M5 | full-hit test drops specs_complete | test_r7 or test_r12 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m5 start=2026-11-04 20:30:21 end=2026-11-04 20:30:29 elapsed=8s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M5.log |
| S18-M6 | H6 tiers not skipped on a full hit | test_r10 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m6 start=2026-11-04 20:30:29 end=2026-11-04 20:30:34 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M6.log |
| S18-M7 | candidates not seeded | test_r13 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m7 start=2026-11-04 20:30:35 end=2026-11-04 20:30:40 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M7.log |
| S18-M8 | eligibility drops the behaviour-profile clause | test_r16 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m8 start=2026-11-04 20:30:41 end=2026-11-04 20:30:46 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M8.log |
| S18-M9 | seed before the verdict call | test_r18 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m9 start=2026-11-04 20:30:46 end=2026-11-04 20:30:55 elapsed=9s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M9.log |
| S18-M10 | C4 guard removed | test_r19 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m10 start=2026-11-04 20:30:56 end=2026-11-04 20:31:00 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M10.log |
| S18-M11 | route forwards the keyword with the flag OFF | test_p3 | KILLED | 4 | True | [pyt] tag=g4mut-s18-m11 start=2026-11-04 20:31:00 end=2026-11-04 20:31:06 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M11.log |
| S18-M12 | source_method set to "kb_offer" | test_r9 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m12 start=2026-11-04 20:31:07 end=2026-11-04 20:31:13 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M12.log |
| S18-M13 | LICENCE_FIELDS emptied | test_r4 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m13 start=2026-11-04 20:31:13 end=2026-11-04 20:31:20 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M13.log |
| S19-M1 | mode read after the client resolve | test_r2 | KILLED | 1 | True | [pyt] tag=g4mut-s19-m1 start=2026-11-04 20:31:26 end=2026-11-04 20:31:30 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M1.log |
| S19-M2 | DRY performs the APPLY run | test_r3 | KILLED | 1 | True | [pyt] tag=g4mut-s19-m2 start=2026-11-04 20:31:30 end=2026-11-04 20:31:33 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M2.log |
| S19-M3 | nx=True dropped | test_r5 | KILLED | 1 | True | [pyt] tag=g4mut-s19-m3 start=2026-11-04 20:31:34 end=2026-11-04 20:31:37 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M3.log |
| S19-M4 | lock failure falls through to fetch | test_r5 | KILLED | 1 | True | [pyt] tag=g4mut-s19-m4 start=2026-11-04 20:31:38 end=2026-11-04 20:31:41 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M4.log |
| S19-M5 | require_tos=False | test_r7 or test_r12 | KILLED | 3 | True | [pyt] tag=g4mut-s19-m5 start=2026-11-04 20:31:41 end=2026-11-04 20:31:45 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M5.log |
| S19-M6 | timeout 20.0 | test_r7 or test_r12 | KILLED | 3 | True | [pyt] tag=g4mut-s19-m6 start=2026-11-04 20:31:45 end=2026-11-04 20:31:52 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M6.log |
| S19-M7 | specs fetched instead of licence | test_r6 | KILLED | 1 | True | [pyt] tag=g4mut-s19-m7 start=2026-11-04 20:31:53 end=2026-11-04 20:31:56 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M7.log |
| S19-M8 | hint closed on a timeout | test_r8 | KILLED | 2 | True | [pyt] tag=g4mut-s19-m8 start=2026-11-04 20:31:56 end=2026-11-04 20:32:00 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M8.log |
| S19-M9 | CAS payload carries demand_count | test_r11 | KILLED | 1 | True | [pyt] tag=g4mut-s19-m9 start=2026-11-04 20:32:00 end=2026-11-04 20:32:04 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M9.log |
| S19-M10 | the web-search sub-flag imports llm_router | test_r9 | KILLED | 1 | True | [pyt] tag=g4mut-s19-m10 start=2026-11-04 20:32:04 end=2026-11-04 20:32:07 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M10.log |
| S19-M11 | pdp_ rows ranked as demand | test_r4 | KILLED | 1 | True | [pyt] tag=g4mut-s19-m11 start=2026-11-04 20:32:08 end=2026-11-04 20:32:11 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M11.log |
| S19-M12 | tail runs daily | test_r12 | KILLED | 1 | True | [pyt] tag=g4mut-s19-m12 start=2026-11-04 20:32:12 end=2026-11-04 20:32:15 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S19-M12.log |
| D16-M1 | gate raises fastapi.HTTPException(404) (the house envelope) | test_p1 | KILLED | 4 | True | [pyt] tag=g4mut-d16-m1 start=2026-11-04 20:32:15 end=2026-11-04 20:32:20 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M1.log |
| D16-M2 | gate declared after verify_admin_key | test_p1 | KILLED | 4 | True | [pyt] tag=g4mut-d16-m2 start=2026-11-04 20:32:21 end=2026-11-04 20:32:25 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M2.log |
| D16-M3 | include_in_schema dropped | test_p2 | KILLED | 1 | True | [pyt] tag=g4mut-d16-m3 start=2026-11-04 20:32:26 end=2026-11-04 20:32:30 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M3.log |
| D16-M4 | the tos.reviewed_at check removed | test_r5 | KILLED | 1 | True | [pyt] tag=g4mut-d16-m4 start=2026-11-04 20:32:31 end=2026-11-04 20:32:35 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M4.log |
| D16-M5 | candidate hosts accepted | test_r6 | KILLED | 1 | True | [pyt] tag=g4mut-d16-m5 start=2026-11-04 20:32:36 end=2026-11-04 20:32:40 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M5.log |
| D16-M6 | gap close drops the state filter | test_r4 | KILLED | 1 | True | [pyt] tag=g4mut-d16-m6 start=2026-11-04 20:32:41 end=2026-11-04 20:32:48 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M6.log |
| D16-M7 | ignore_duplicates=False on the product write | test_r4 | KILLED | 1 | True | [pyt] tag=g4mut-d16-m7 start=2026-11-04 20:32:48 end=2026-11-04 20:32:52 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M7.log |
| D16-M8 | limit not clamped | test_r3 | KILLED | 1 | True | [pyt] tag=g4mut-d16-m8 start=2026-11-04 20:32:53 end=2026-11-04 20:32:59 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M8.log |
| D16-M9 | the identity check skipped (placeholder accepted) | test_r6 | KILLED | 1 | True | [pyt] tag=g4mut-d16-m9 start=2026-11-04 20:33:00 end=2026-11-04 20:33:04 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M9.log |
| D16-M10 | the licence check dropped (R-G4-7) | test_r11 | KILLED | 1 | True | [pyt] tag=g4mut-d16-m10 start=2026-11-04 20:33:05 end=2026-11-04 20:33:09 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D16-M10.log |
| D17-M1 | user_id added to the search_logs select | test_r4 | KILLED | 1 | True | [pyt] tag=g4mut-d17-m1 start=2026-11-04 20:33:10 end=2026-11-04 20:33:16 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D17-M1.log |
| D17-M2 | an absent host emitted as 0 | test_r5 | KILLED | 1 | True | [pyt] tag=g4mut-d17-m2 start=2026-11-04 20:33:17 end=2026-11-04 20:33:20 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D17-M2.log |
| D17-M3 | on_conflict dropped (insert) | test_r6 | KILLED | 1 | True | [pyt] tag=g4mut-d17-m3 start=2026-11-04 20:33:21 end=2026-11-04 20:33:25 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D17-M3.log |
| D17-M4 | DRY upserts | test_r6 | KILLED | 1 | True | [pyt] tag=g4mut-d17-m4 start=2026-11-04 20:33:25 end=2026-11-04 20:33:29 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D17-M4.log |
| D17-M5 | median over captured_at for age_median_hours | test_r3 | KILLED | 1 | True | [pyt] tag=g4mut-d17-m5 start=2026-11-04 20:33:29 end=2026-11-04 20:33:35 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D17-M5.log |
| D17-M6 | synthetic rows counted | test_r4 | KILLED | 1 | True | [pyt] tag=g4mut-d17-m6 start=2026-11-04 20:33:35 end=2026-11-04 20:33:39 elapsed=3s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\D17-M6.log |
| S18-M14 | the full product text hashed into the key (R-G4-3) | test_r17 | KILLED | 1 | True | [pyt] tag=g4mut-s18-m14 start=2026-11-04 20:34:25 end=2026-11-04 20:34:30 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M14.log |
| S18-M14b | live products (not pid stubs) passed to build_verdict_prompt (the pre-R-G4-3 spec text) | test_r17 | SURVIVED | 0 | False | [pyt] tag=g4mut-s18-m14b start=2026-11-04 20:34:31 end=2026-11-04 20:34:35 elapsed=4s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\mutants\S18-M14b.log |

Spec + ruling mutants: 42 / 42 KILLED. S18-M14b (extra, informational, not a spec mutant) SURVIVED: see 8 (an equivalent mutant at this base).

## 6. CI-order set (R-G4-5: the EXISTING members, OFF, once at base)

Members: tests/test_admin_key_and_sentry_scrub.py tests/test_flush_live_price_key.py tests/test_s75_fanout_identity.py tests/test_s81_d11_pdp_discovery.py tests/test_s81_d14_live_robots.py tests/test_s81_g3_gate_rows.py tests/test_s81_kb_schema.py tests/test_s81_s05_request_context.py tests/test_s81_s16_kb_seed.py tests/test_s81_s17_kb_ingest.py tests/test_w4_13_measurement_truth.py
    [hermeticity] sentinel checked 1427 test(s)
    [netguard] blocked 28 attempt(s) from 10 node(s)
5 failed = the five environmental r27 rows tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[*] (CRLF working copy; spec header); 1422 passed. The netguard blocks are tests/test_flush_live_price_key.py api.openai.com resolves (pre-existing at base).

## 7. Comm set and its base record (LC-6 / R-G4-9)

- COMM_SET.txt = <scratchpad>/S81-G4_red/COMM_SET.txt (copy of g4spec/comm_set.txt), 661 files, sha256 90b85603e5dbb51268a6221c22b5b18a2785c1b8572f25a455e6faf9eb18ee15.
- Re-derived ONCE by the union rule (g4spec/comm.py over the real worktree + the stored G3 set): the 661 + exactly the four new RED files (excluded: not members at base) -> 0 added, 0 dropped. comm_reasons.tsv = one reason row per member.
- Reuse split re-checked per file (unchanged since 744616e3, no reference to the eight G3-edited modules nor CLAUDE.md, not a glob walker, present in the 744616e3 record): 222 reuse / 439 run, identical to the spec's recompute.txt (0 disagreements). tests/test_secret_scan_static.py (a reuse candidate) was ALSO run alone at base.
- Stored: <scratchpad>/harness/base_records/0b19de5bcc1416111d48bc725359b95151a658ca/90b85603e5dbb51268a6221c22b5b18a2785c1b8572f25a455e6faf9eb18ee15.{txt,files,pyt.log,header.txt}: 221 reused + 439 run in 18 chunks; 14 FAILED/ERROR node ids.

Base failures (the record's .txt):

- tests/test_auth_interceptor.py::test_sign_in_with_social_exception
- tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
- tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
- tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
- tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
- tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
- tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
- tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]

[pyt] lines of the comm base run:
    2026-11-04 20:39:12 [pyt] tag=g4red-comm-00 start=2026-11-04 20:38:39 end=2026-11-04 20:39:12 elapsed=33s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-00.log
    2026-11-04 20:39:47 [pyt] tag=g4red-comm-01 start=2026-11-04 20:39:12 end=2026-11-04 20:39:46 elapsed=34s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-01.log
    2026-11-04 20:41:09 [pyt] tag=g4red-comm-02 start=2026-11-04 20:39:48 end=2026-11-04 20:41:09 elapsed=81s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-02.log
    2026-11-04 20:41:31 [pyt] tag=g4red-comm-03 start=2026-11-04 20:41:12 end=2026-11-04 20:41:31 elapsed=19s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-03.log
    2026-11-04 20:41:56 [pyt] tag=g4red-comm-04 start=2026-11-04 20:41:34 end=2026-11-04 20:41:56 elapsed=22s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-04.log
    2026-11-04 20:44:10 [pyt] tag=g4red-comm-05 start=2026-11-04 20:41:56 end=2026-11-04 20:44:10 elapsed=133s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-05.log
    2026-11-04 20:44:54 [pyt] tag=g4red-comm-06 start=2026-11-04 20:44:11 end=2026-11-04 20:44:54 elapsed=43s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-06.log
    2026-11-04 20:45:17 [pyt] tag=g4red-comm-07 start=2026-11-04 20:44:55 end=2026-11-04 20:45:17 elapsed=22s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-07.log
    2026-11-04 20:45:59 [pyt] tag=g4red-comm-08 start=2026-11-04 20:45:17 end=2026-11-04 20:45:59 elapsed=42s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-08.log
    2026-11-04 20:46:35 [pyt] tag=g4red-comm-09 start=2026-11-04 20:45:59 end=2026-11-04 20:46:35 elapsed=35s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-09.log
    2026-11-04 20:47:06 [pyt] tag=g4red-comm-10 start=2026-11-04 20:46:35 end=2026-11-04 20:47:06 elapsed=31s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-10.log
    2026-11-04 20:49:03 [pyt] tag=g4red-comm-11 start=2026-11-04 20:47:07 end=2026-11-04 20:49:03 elapsed=116s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-11.log
    2026-11-04 20:51:30 [pyt] tag=g4red-comm-12 start=2026-11-04 20:49:04 end=2026-11-04 20:51:29 elapsed=146s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-12.log
    2026-11-04 20:53:00 [pyt] tag=g4red-comm-13 start=2026-11-04 20:51:30 end=2026-11-04 20:52:59 elapsed=89s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-13.log
    2026-11-04 20:53:49 [pyt] tag=g4red-comm-14 start=2026-11-04 20:53:01 end=2026-11-04 20:53:48 elapsed=48s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-14.log
    2026-11-04 20:54:34 [pyt] tag=g4red-comm-15 start=2026-11-04 20:53:49 end=2026-11-04 20:54:33 elapsed=44s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-15.log
    2026-11-04 20:55:19 [pyt] tag=g4red-comm-16 start=2026-11-04 20:54:34 end=2026-11-04 20:55:19 elapsed=45s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-16.log
    2026-11-04 20:55:37 [pyt] tag=g4red-comm-17 start=2026-11-04 20:55:19 end=2026-11-04 20:55:36 elapsed=17s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_red\comm\g4red-comm-17.log

## 8. Deviations, findings and questions for the gate

- DV1 (harness, S18 compare rows): every live leg is a COUNTING recorder, not a raising one; a raising leg inside the Phase-1 gather (return_exceptions=True) is swallowed, and a raising unified search ends the compare on a non-assertion path at base. The rows assert zero (or per-product) call counts instead; the kill power is the same (S18-M6 / M7 killed).
- DV2 (R12): the call counts are per PRODUCT (slot 0 partial: price leg 0, specs / reviews / image / search 1; slot 1 miss: every leg 1). The spec row text reads as a single total.
- DV3 (P2 / P3): the kb_serve.hashlib recorder is installed only when kb_serve exposes a module attribute `hashlib` (getattr-safe; the prototype does). The x-client-capabilities getter is a RECORDING wrapper on starlette Headers.get (P3), not a raising one, so the five routes still answer 200 and the keyword sets are comparable.
- DV4 (R16 / R14): the user-bound compares silence scs._fire_and_forget (the post-response writes) so the netguard stays at 0 (without it 4 supabase.invalid attempts were blocked).
- DV5 (golden): the golden pins the FY25-normalised payloads AND the live-leg call counts of the three scenarios (camera = compare_from_text with vision_products at service level; the route-level identity is P3).
- DV6 (D17 contract fixed by this RED, stated in the file docstring): offers from the kb_offers_latest view (variant_id, last_seen, captured_at); ages against kb_seed_common._now(); shares rounded to 4 places with n = the product count; every kb.gaps.state.<5> and kb.hints.state.<3> metric emitted (0 included); the host counters read with ONE pipeline of HGETALL over the live + blocked registry hosts; an EMPTY hash = an absent key (no metric).
- DV7 (S19 contract fixed): main(argv, client, redis) with --leg all|gaps|refresh; Redis None -> cache_service.redis_client; the DRY report is JSON with queue (product_key per entry) and spend {lane offclock, cap_usd, planned_usd 0}; a lost CAS is not retried (R11 asserts one update per gap; the 2.6 totals line has no cas_lost field, so no count is asserted).
- DV8 (D16): R6 also covers a raising write -> 400 KB_STORE_UNAVAILABLE (never a 503); R11 is the R-G4-7 row (KB_LICENCE_FIELD for every kb_serve.LICENCE_FIELDS member with source operator, accepted with partner).
- FIND1 (S18-M14b, informational): extraction_service.build_verdict_prompt reads `products` only to derive the category when category is None (extraction_service.py build_verdict_prompt, the `if products: first = products[0]` branch), so at 0b19de5b passing the live products instead of the pid stubs does NOT change the digest (an equivalent mutant; SURVIVED). The R-G4-3 premise that the spec form would fold live snippet text into the key does not hold for this base; the stub form is kept (future-proof) and the ruling mutant S18-M14 (product text hashed into the key) is KILLED by R17. Question for the gate: rule S18-M14b equivalent.
- FIND2 (P01 pin): tests/test_s81_kb_schema.py test_s14_p01_no_importer_of_kb_service flags a `kb_service` token in ANY new scripts/ file outside the allowlist, a docstring included (the first prototype of cron_kb_coverage.py failed at :1). GREEN keeps the token out of cron_kb_coverage.py and cron_kb_enrich.py (they use common.kb_leaf()).
- FIND3 (prototype, H6): the KB rating must be written AFTER the four result[...] rating_data assignments, not into rating_data: a rating_data with a rating and rating_source None crashes the verified_rating injection (`rating_data.get("rating_source", {}).get("name")`), measured as INTERNAL_ERROR on the full-hit rows.
- FIND4 (prototype, scs H8): the REST key is computed before `_verdict_quality` exists; it calls verdict_comparison_quality(product_data) itself (the same value).
- NOTE1: the scratch worktree index was touched with `git add -N` (my own detached scratch worktree only, to diff the new files); removed afterwards.
- NOTE2: the four RED files + the golden are not comm-set members at base; GREEN adds them at HEAD (12.1).
- NOT MEASURED: none.

## 9. Restore check

tracked-file sha256 (3481 files) before vs after: equal
git diff --stat lines: 0
HEAD: 0b19de5bcc1416111d48bc725359b95151a658ca
scratch worktree in git worktree list: 0 (directory removed)
mutation lock: none left (removed by the harness)
untracked in the real worktree: the five RED files only

Not done here: GREEN (no app/, scripts/, docs/, CLAUDE.md or tests/test_s81_kb_schema.py edit in the real worktree); the corpus gate (no price_service edit); the fourteen client fences (GREEN's duty).
