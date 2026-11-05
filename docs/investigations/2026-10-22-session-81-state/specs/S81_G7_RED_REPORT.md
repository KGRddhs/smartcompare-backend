# S81-G7 RED REPORT (D16b + D17b + D22c + D22d), RED agent Opus 5.5, 2026-11-05

Base 6869a3e655805afd3adbba43f99578dd79585934 (real worktree sc-s81-g7, HEAD unchanged). Spec sha cdb7e4f5...; rulings RULINGS_S81_G7 R-G7-1..12 applied (flag ENABLE_BEHAVIOR_PROFILE_REBUILD per R-G7-3).
Report files written through the shell (python): this file, S81-G7_red/RED_REPORT.md, COMM_SET.txt, comm_reasons.tsv.

## Files (real worktree, untracked, nothing else touched)
```
6fd81d37592f2ad5b5633a19dda5ee090c1ab623222e344af815f020e61e8039 *tests/test_s81_d16b_operator_dates.py
927dc06086283fd811542031713e6843e3a4cef20774e97af48677b017c3845b *tests/test_s81_d17b_coverage_paging.py
ff9b45da58387ac83d052669f4886d20fe168b7a3bf2f0c16152aeb9361bb3a1 *tests/test_s81_d22c_profile_select.py
79a333725ebbb2c76b9c46dc06063aa623d39f27e6f757bc101cd144c111a587 *tests/test_s81_d22c_varhint_retire.py
15c5dc0fe0c92d72c18f95a0962edf4e9deb41cddb39ec24503ea06e48b0adf2 *tests/test_s81_d22d_learning_hardening.py
8c793a16b1bbb1bffd789dd96a3c88d214deee2adc46d125f1efa48cd17eff0a *tests/fixtures/s81_d22c_flag_off_golden.json
13024 tests/test_s81_d16b_operator_dates.py
11608 tests/test_s81_d17b_coverage_paging.py
19677 tests/test_s81_d22c_profile_select.py
 6826 tests/test_s81_d22c_varhint_retire.py
12368 tests/test_s81_d22d_learning_hardening.py
 3804 tests/fixtures/s81_d22c_flag_off_golden.json
67307 total
```
Pure ASCII, LF, 0 bytes > 127, 0 CR in all six. No 8-digit run, no at sign, no key shape; the constants REPORT_SHA256_BASE / UPSERT_SHA256_BASE / GOLDEN_DIGEST / BEHAVIOR_SERVICE_SHA256_BASE / MD_SHA256_BASE carry no gitleaks keyword and every 64-hex is split.

## Rows per unit (RED fails at base on AssertionError only; PIN green at base, full configuration + recorders)
- D16b tests/test_s81_d16b_operator_dates.py: RED R1-R8 (8); PIN P1 (x4 OFF spellings, no-key 404 not 403), P2, P3, P4.
- D17b tests/test_s81_d17b_coverage_paging.py: RED R1-R3 (3); PIN P1 (upstash exec/execute recorder), P2 (report + upsert sha at base), P3 (x6 OFF spellings).
- D22c(1) tests/test_s81_d22c_profile_select.py: RED R1-R5 (5); PIN P1 (x5 OFF spellings vs the golden), P2, P3, P4.
- D22c(2) tests/test_s81_d22c_varhint_retire.py: RED V1-V4 (4); PIN P5.
- D22d tests/test_s81_d22d_learning_hardening.py: RED R1-R6 (6); PIN P1-P4, P5 (x6 OFF spellings).
- Golden tests/fixtures/s81_d22c_flag_off_golden.json: recorded at base through record_golden() (S81-G7_red/record_golden.py, sort_keys, indent=1): A live-like 1 run_db + 1 WARNING + no update; B permissive 4 run_db + 1 update; C events-raise 3 run_db + 1 WARNING.
Node counts: 26 RED nodes failed and 34 PIN nodes passed at base (60); prototype 60/60 with the flag unset and with it ON.

## AssertionError proof per RED node (base_final2.log, the final bytes)
```
test_r1_skew_constant AssertionError | E       AssertionError: None
test_r2_future_captured_at_refused AssertionError | E       AssertionError: (200, '{"success":true,"written":{"products":1,"variants":1,"offers":1,"images":1,"specs":2,"gaps_closed":2,"not_bui
test_r3_skew_boundary AssertionError | E       AssertionError: (200, '{"success":true,"written":{"products":1,"variants":1,"offers":1,"images":1,"specs":2,"gaps_closed":2,"not_bui
test_r4_naive_future_refused AssertionError | E       AssertionError: (200, '{"success":true,"written":{"products":1,"variants":1,"offers":1,"images":1,"specs":2,"gaps_closed":2,"not_bui
test_r5_reads_the_now_seam AssertionError | E       AssertionError: (200, '{"success":true,"written":{"products":1,"variants":1,"offers":1,"images":1,"specs":2,"gaps_closed":2,"not_bui
test_r6_classify_future_only_is_unknown AssertionError | E       AssertionError: {'amount': 42.5, 'currency': 'BHD', 'retailer': 'store-a.example.com', 'url': 'https://store-a.example.com/products/
test_r7_classify_future_never_shadows AssertionError | E       AssertionError: {'amount': 99.0, 'currency': 'BHD', 'retailer': 'store-a.example.com', 'url': 'https://store-a.example.com/products/
test_r8_coverage_future_not_fresh_not_aged AssertionError | E       AssertionError: {'kb.products.total': ('2', 2), 'kb.products.identity_high_share': ('1.0', 2), 'kb.field.offer_share': ('1.0', 2), '
test_r1_every_page_ordered_by_id AssertionError | E               AssertionError: ('kb_products', [])
test_r2_unordered_store_paged_completely AssertionError | E       AssertionError: duplicate or missing ids: 1126 distinct
test_r3_redis_py_pipeline_executes AssertionError | E       AssertionError: ['kb.field.complete_share', 'kb.field.concentration_share', 'kb.field.image_share', 'kb.field.offer_fresh_share', 'k
test_r1_reader_spellings AssertionError | E       AssertionError: structured_comparison_service.behavior_profile_rebuild_enabled is missing (D22c)
test_r2_on_selects_live_columns AssertionError | E       AssertionError: ['category_used, products, created_at']
test_r3_on_writes_a_profile AssertionError | E       AssertionError: ['Failed to update behavior profile: column comparisons.category_used does not exist']
test_r4_on_null_payloads_do_not_raise AssertionError | E       AssertionError: ['Failed to update behavior profile: column comparisons.category_used does not exist']
test_r5_flag_read_per_call AssertionError | E       AssertionError: ['category_used, products, created_at']
test_v1_dead_symbols_gone AssertionError | E       AssertionError: price_service._varhint_append_learned still exists
test_v2_data_file_gone AssertionError | E       AssertionError: data/variant_hint_learned.json still exists
test_v3_no_suppression_left AssertionError | E       AssertionError: tests/test_variant_llm_hint_b3b.py still carries no_learned_write
test_v4_on_path_writes_no_file AssertionError | E       AssertionError: [('variant_hint_reference.json', 'r'), ('variant_hint_learned.json', 'r')]
test_r1_specs_grounding_survives_paging AssertionError | E       AssertionError: [{'bucket': 'spec_wrong', 'cases': 3, 'category': 'fragrances', 'distinct_actors': 3, ...}]
test_r2_specs_pages_ranges AssertionError | E       AssertionError: [((0, 799), [('id', False)])]
test_r3_specs_cap_across_pages AssertionError | E       AssertionError: [((0, 799), [('id', False)])]
test_r4_unclean_field_counted AssertionError | E           AssertionError: ('true', 0)
test_r5_control_chars_escaped_on_render AssertionError | E           AssertionError: '[LEARNING] forged || Dune\x1b[2J\\u2028x'
test_r6_render_helper AssertionError | E       AssertionError: scripts.cron_learning._render is missing (D22d)
```

## [pyt] lines
```
[pyt] tag=g7red-base-units start=2026-11-05 13:00:00 end=2026-11-05 13:00:08 elapsed=8s bound=600s status=FAIL rc=1 (26 failed, 34 passed; first V4 recorder, superseded)
[pyt] tag=g7red-base-units2 start=2026-11-05 13:01:00 end=2026-11-05 13:01:10 elapsed=10s bound=600s status=FAIL rc=1 (26 failed, 34 passed)
[pyt] tag=g7red-proto-off start=2026-11-05 13:01:45 end=2026-11-05 13:01:53 elapsed=7s bound=600s status=OK rc=0 (60 passed)
[pyt] tag=g7red-proto-on start=2026-11-05 13:02:01 end=2026-11-05 13:02:08 elapsed=7s bound=600s status=OK rc=0 (60 passed; ENABLE_BEHAVIOR_PROFILE_REBUILD=true in the runner call only)
[pyt] tag=g7red-proto-pins start=2026-11-05 13:02:17 end=2026-11-05 13:03:22 elapsed=65s bound=1200s status=FAIL rc=1 (3 failed = d16 r10 / d17 r9 / s19 r15, known env CRLF nodes of the stored record; 946 passed; 14 touched pin files incl. E1 b3b + E2 g5 on the prototype)
[pyt] tag=g7red-D16b-M1 .. g7red-D22d-M8: 31 mutant runs, bound 600 each (S81-G7_red/mut_*.log)
[pyt] tag=g7red-ciorder-base start=2026-11-05 13:18:52 end=2026-11-05 13:21:08 elapsed=137s bound=1200s status=FAIL rc=1 (29 failed = 26 RED + 3 known env; 1135 passed; hermeticity 1164; netguard blocked 22 from 21 nodes, all tests/test_hermeticity_pins.py by design)
[pyt] tag=g7red-secretscan-base start=2026-11-05 13:21:18 end=2026-11-05 13:21:50 elapsed=33s bound=600s status=OK rc=0 (31 passed)
[pyt] tag=g7red-base-final start=2026-11-05 13:22:16 end=2026-11-05 13:22:29 elapsed=13s bound=600s status=FAIL rc=1 (26 failed, 34 passed)
[pyt] tag=g7red-proto-off-final start=2026-11-05 13:22:31 end=2026-11-05 13:22:42 elapsed=11s bound=600s status=OK rc=0 (60 passed)
[pyt] tag=g7red-proto-on-final start=2026-11-05 13:22:44 end=2026-11-05 13:22:55 elapsed=11s bound=600s status=OK rc=0 (60 passed)
[pyt] tag=g7red-base-final2 start=2026-11-05 13:26:17 end=2026-11-05 13:26:27 elapsed=9s bound=600s status=FAIL rc=1 (26 failed, 34 passed; hermeticity 60; netguard 0)  <- FINAL bytes
[pyt] tag=g7red-proto-off-final2 start=2026-11-05 13:26:28 end=2026-11-05 13:26:37 elapsed=9s bound=600s status=OK rc=0 (60 passed; netguard 0)  <- FINAL bytes
[pyt] tag=g7red-proto-on-final2 start=2026-11-05 13:26:39 end=2026-11-05 13:26:47 elapsed=8s bound=600s status=OK rc=0 (60 passed; netguard 0)  <- FINAL bytes
[pyt] tag=g7red-secretscan-final start=2026-11-05 13:28:34 end=2026-11-05 13:28:59 elapsed=25s bound=600s status=OK rc=0 (31 passed; netguard 0)  <- FINAL bytes
```

## Corpus gate (R-G7-6: measured at base before the edits and at the prototype HEAD, never inferred)
scripts/verify_flag_byte_identity.py --proof-root .../sc-scraper-proof/_proof --flags ENABLE_VARIANT_LLM_HINT,ENABLE_BEHAVIOR_PROFILE_REBUILD, run in the scratch worktree, never beside a pytest.
- base: RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656; OVERALL SHA256 d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf (gate_base.log)
- prototype HEAD (every flag OFF): RECORDS n=414 calls=1656; OVERALL SHA256 d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf (gate_head.log)
- EQUAL. It differs from the G3 6013...a1ef only because the digest payload carries the --flags list; GREEN must pass the same two flags.

## Prototype
Scratch worktree <scratchpad>/g7r detached at 6869a3e6, no junction, no .env; proto_apply.py applied all four units + E1 + E2 (CRLF preserved; git diff --stat 9 files, 121+/76-, no whole-file diff). Diff: S81-G7_red/prototype.diff (533 lines) + prototype_files/ (8 files). Removed with git worktree remove --force (recreated once for the final runs after the golden re-record, the diff byte-equal to prototype.diff, removed again); verified gone.

## Mutation table (byte copies in the scratch prototype, .qa-mutation.lock, restore sha256-verified)
| M | mutation | file | result |
|---|---|---|---|
| D16b-M1 | validator > -> >= (300 s refused) | app/services/kb_operator.py | KILLED by test_r3_skew_boundary |
| D16b-M2 | validator reads the wall clock, not _now() | app/services/kb_operator.py | KILLED by test_r2_future_captured_at_refused, test_r3_skew_boundary, test_r4_naive_future_refused, test_r5_reads_the_now_seam |
| D16b-M3 | validator drops the naive-to-UTC branch | app/services/kb_operator.py | KILLED by test_r4_naive_future_refused |
| D16b-M4 | FUTURE_SKEW_SECONDS = 0 | app/services/kb_serve.py | KILLED by test_p3_within_skew_classify_unchanged, test_r1_skew_constant, test_r3_skew_boundary |
| D16b-M5 | classify future check removed | app/services/kb_serve.py | KILLED by test_r6_classify_future_only_is_unknown, test_r7_classify_future_never_shadows |
| D16b-M6 | classify future check sets seen = now | app/services/kb_serve.py | KILLED by test_r6_classify_future_only_is_unknown, test_r7_classify_future_never_shadows |
| D16b-M7 | coverage _past in _ages only (_field_shares reads _ts) | scripts/cron_kb_coverage.py | KILLED by test_r8_coverage_future_not_fresh_not_aged |
| D16b-M8 | coverage _past returns _ts unconditionally | scripts/cron_kb_coverage.py | KILLED by test_r8_coverage_future_not_fresh_not_aged |
| D17b-M1 | order call removed | scripts/cron_kb_coverage.py | KILLED by test_r1_every_page_ordered_by_id, test_r2_unordered_store_paged_completely |
| D17b-M2 | order desc=True | scripts/cron_kb_coverage.py | KILLED by test_r1_every_page_ordered_by_id |
| D17b-M3 | order on the first page only | scripts/cron_kb_coverage.py | KILLED by test_r2_unordered_store_paged_completely |
| D17b-M4 | fallback reversed (execute preferred) | scripts/cron_kb_coverage.py | KILLED by test_p1_upstash_pipeline_uses_exec_never_queueing_execute |
| D17b-M5 | fallback removed (pipe.exec only) | scripts/cron_kb_coverage.py | KILLED by test_r3_redis_py_pipeline_executes |
| D17b-M6 | PAGE_ORDER_COLUMN = created_at | scripts/cron_kb_coverage.py | KILLED by test_r1_every_page_ordered_by_id |
| D22c-M1 | ON events select keeps metadata | app/services/structured_comparison_service.py | KILLED by test_r2_on_selects_live_columns, test_r3_on_writes_a_profile, test_r4_on_null_payloads_do_not_raise, test_r5_flag_read_per_call |
| D22c-M2 | ON comparisons select keeps the phantom columns | app/services/structured_comparison_service.py | KILLED by test_r2_on_selects_live_columns, test_r3_on_writes_a_profile, test_r4_on_null_payloads_do_not_raise, test_r5_flag_read_per_call |
| D22c-M3 | reader drops .strip() | app/services/structured_comparison_service.py | KILLED by test_r1_reader_spellings |
| D22c-M4 | flag cached at import | app/services/structured_comparison_service.py | KILLED by test_r2_on_selects_live_columns, test_r3_on_writes_a_profile, test_r4_on_null_payloads_do_not_raise, test_r5_flag_read_per_call |
| D22c-M5 | ON normalisation removed | app/services/structured_comparison_service.py | KILLED by test_r4_on_null_payloads_do_not_raise |
| D22c-M6 | flag inverted (OFF uses the V2 strings) | app/services/structured_comparison_service.py | KILLED by test_p1_flag_off_golden[OFF], test_p1_flag_off_golden[empty], test_p1_flag_off_golden[false], test_p1_flag_off_golden[pad0], test_p1_flag_off_golden[unset], test_r2_on_selects_live_columns, test_r3_on_writes_a_profile, test_r4_on_null_payloads_do_not_raise, test_r5_flag_read_per_call |
| D22c-M7 | _fire_and_forget label changed (first site) | app/services/structured_comparison_service.py | KILLED by test_p3_label_and_call_sites_unchanged |
| D22c-M8 | VARHINT: the call kept with a no-op stub | app/services/price_service.py | KILLED by test_v1_dead_symbols_gone |
| D22c-M9 | VARHINT: the Redis verdict write dropped with the deletion | app/services/price_service.py | KILLED by test_v4_on_path_writes_no_file |
| D22d-M1 | _read_by keeps one page per chunk | scripts/cron_learning.py | KILLED by test_r1_specs_grounding_survives_paging, test_r2_specs_pages_ranges |
| D22d-M2 | page end off by one | scripts/cron_learning.py | KILLED by test_r2_specs_pages_ranges, test_r3_specs_cap_across_pages |
| D22d-M3 | cap ignored inside a chunk | scripts/cron_learning.py | KILLED by test_r3_specs_cap_across_pages |
| D22d-M4 | counter per distinct field instead of per row | scripts/cron_learning.py | KILLED by test_r4_unclean_field_counted |
| D22d-M5 | counter also counts clean off-vocabulary names | scripts/cron_learning.py | KILLED by test_p3_clean_off_vocabulary_not_counted |
| D22d-M6 | _render applied to the markdown line only | scripts/cron_learning.py | KILLED by test_r5_control_chars_escaped_on_render |
| D22d-M7 | _render escapes a backslash too (EQUIVALENT by R-G7-9) | scripts/cron_learning.py | SURVIVED (EQUIVALENT by R-G7-9: no base product name carries a backslash) |
| D22d-M8 | _render misses U+2028 | scripts/cron_learning.py | KILLED by test_r5_control_chars_escaped_on_render |

30 KILLED (every kill an AssertionError; D17b-M4 re-run after P1 gained an assertion-first membership check, D22c-M1..M7 re-run after the golden re-record), 1 equivalent (D22d-M7).

## Comm set (R-G7-10)
Re-derivation (S81-G7_red/comm_rederive.py = the spec's comm.py plus the renamed flag, behavior_profile_rebuild_enabled, FUTURE_SKEW_SECONDS, PAGE_ORDER_COLUMN, _kb_field_world, no_learned_write, kb_seed_common, classify(, _hosts, pipeline( and all four test_precommit_hook*.py excluded): 529 grep members, ALL inside the stored 691; members added = 0. The named pins tests/test_migration_index_predicate_immutability.py and tests/test_openai_key_log_hygiene_s69.py are already members. The stored base record ab9758eddc0c5c7c7546425ac6e8bceaaaa105b793f313c624db44e4e1d2f8fa at 6869a3e6 is REUSED unchanged (LC-6); no base comm run was made; base FAILED set = its 17 environmental nodes. COMM_SET.txt (691) and comm_reasons.tsv (163 members carry the spec's closure-importer reason). GREEN runs the 691 + the 5 RED files at HEAD.

## Deviations
- V4 (spec: no open() whose path contains data): the consult path legitimately READS data/variant_hint_reference.json (the curated B3a reference), which stays after GREEN; V4 asserts instead that the learned file is never opened and no data/ path is opened in a write mode (the recorder refuses both, so base never writes the tracked file).
- Corpus expected value: base measured d2e16d30... (not 6013...a1ef): the digest includes the --flags list; equal at the prototype HEAD.
- D22c golden synthetic user id 'u-synthetic-a' (the spec's 'u-' + '0'*8 would put an 8-digit run into the committed fixture).
- D16b P1: no dependency-override recorder (as the spec says); a no-key request must be 404 (not 403) and client.table() is never called.
- D16b R8 also asserts the age median value (24.0); the D16b / D17b / D22d files reuse the frozen D16 / S18 / D17 / D22 / G5 helpers by import.
- Prototype choices GREEN may refine: kb_operator and cron_kb_coverage._past import kb_serve function-locally (D17 R1's OFF no-app-import row stays green since _past runs only inside a run).

## Open questions
- None blocking. D22d-M7 recorded equivalent per R-G7-9.

## Restore check
Real worktree: HEAD 6869a3e6; git status --short shows only the 6 new untracked files; git diff --stat HEAD empty; data/variant_hint_learned.json present; scratch worktree removed (git worktree list has no g7r); no pytest of this agent alive; .qa-mutation.lock removed. record_golden.py ran the base code in the real worktree and wrote only the untracked fixture.

The fourteen client fences were NOT run (GREEN's duty).
