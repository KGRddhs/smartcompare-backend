# S81-G5 RED REPORT (D22 NIGHTLY-LEARNING) - RED agent, Opus 5.5, 2026-11-05

Base ec747b496953869c0370e4f28bf025c6f694a97d. Real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g5: ONE new untracked file, tests/test_s81_d22_nightly_learning.py (74,868 B, sha256 98b2bafced383455edc4d6cc9c8690d1bea5c3193a042a0d760ddf0eb5d08656, ASCII, LF, 0 bytes > 127; no 8-digit run, no 64-hex, no '@' outside the AT_SIGN constant and decorators, no '+973' in its text). Nothing else added or edited there. Spec sha256 0b5c27f4... read in full with RULINGS_S81_G5 R-G5-1..16 (binding). This report was written through the shell (python), as the harness refuses a subagent Write of a report .md.

## 1. RED file rows and node counts

R1-R29 + P1-P7 (section 5 as amended): 50 nodes = 43 RED nodes (R1, R2 x9 [unset, '', 'false', ' FALSE ', '0', 'off', 'no', 'garbage', 'dry'], R3 x5 ['true', ' TRUE ', '1', 'yes', 'On'], R4 x2 ['apply', ' APPLY '], R5-R17, R18 x2 [raises, none], R19-R29) + 7 PIN nodes (P1-P7). The spec estimated about 45 + 9; measured 43 + 7.

Fake client: the D17 recorder form with filter EVALUATION (gte / lt / in_), order sorting, range slicing and column PROJECTION (an alias:json-path item is served from the seeded alias key), seeded through main(argv, client=fake). Module access through find_spec + assert; every main call through _call(), which turns any raise (SystemExit included) into an AssertionError; the report accessor asserts the file was written. Autouse fixture: the flag + five knobs deleted, common._now pinned to 2026-11-05 03:00 UTC (default day 2026-11-04, window [2026-10-29, 2026-11-05)). B1: R2, R11 (bad --day), R18 and P2 run with the FULL configuration (five knobs + SUPABASE_URL + the service-role name, synthetic values built at run time) and recorders (the raising _admin_client stub, the kb_leaf spy, a touch-recording client). R4 wraps the real leaf builder in a spy (keyword-only calls, day == date(2026,11,4)).

Default seeded world literals: buckets price_wrong 5/3, spec_wrong 7/4, identity_wrong 0/0, verdict_wrong 2/2, verdict_unsupported 2/2, spec_missing 2/0; learning.actors 8; 10 clusters, 2 systematic (A fragrances/page_scrape/price 3/2; fragrances/kb/concentration 3/2 with one cited grounding row); exemplar candidates fragrances 4 + electronics 1 (the email-shaped one dropped); 6 eval candidates; context abandon 3/2, confirm 3/1, searches failed 2 of 4; rows on both window edges (start inclusive, end exclusive) and before the start.

## 2. Base run (RED file alone, real worktree)

    [pyt] tag=g5red-base-unit3 start=2026-11-05 03:58:28 end=2026-11-05 03:58:34 elapsed=5s bound=600s status=FAIL rc=1
    43 failed, 7 passed, 1 warning; [hermeticity] sentinel checked 50 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
    earlier iterations of the file: g5red-base-unit (03:46:08-03:46:14, 6s, FAIL rc=1, 43 / 7), g5red-base-unit2 (03:53:09-03:53:29, 20s, FAIL rc=1, 43 / 7)

All 43 failures are AssertionError (log scan: 43 x 'E AssertionError'; zero ImportError / AttributeError / other). The 7 passes are P1-P7. Per-node proof (first E line):

- test_r10_knobs_move_the_rule: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r11_window_and_day: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r12_proposals: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r13_exemplar_candidates: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r14_report_log_and_rows_are_deidentified: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r15_eval_candidates: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r16_absent_kb_tables_are_counted_skips: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r17_one_table_error_isolated: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r18_client_failure_exits_one[none]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r18_client_failure_exits_one[raises]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r19_unwritable_report_keeps_the_log: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r1_module_and_seams: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r20_metric_names_closed_and_valid: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r21_apply_is_idempotent_per_day: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r22_db_only_no_llm_no_network: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r23_never_writes_data_dir: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r24_railway_config: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r25_script_hygiene: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r26_rotation_cron_retired: E AssertionError: scripts/cron_few_shot_rotation.py still exists (E2)
- test_r27_verdict_unsupported_threshold: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r28_context_metrics: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r29_log_templates: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r2_off_is_one_line_and_nothing_else[' FALSE ']: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r2_off_is_one_line_and_nothing_else['']: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r2_off_is_one_line_and_nothing_else['0']: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r2_off_is_one_line_and_nothing_else['dry']: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r2_off_is_one_line_and_nothing_else['false']: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r2_off_is_one_line_and_nothing_else['garbage']: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r2_off_is_one_line_and_nothing_else['no']: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r2_off_is_one_line_and_nothing_else['off']: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r2_off_is_one_line_and_nothing_else[unset]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r3_dry_reads_and_never_writes[ TRUE ]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r3_dry_reads_and_never_writes[1]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r3_dry_reads_and_never_writes[On]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r3_dry_reads_and_never_writes[true]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r3_dry_reads_and_never_writes[yes]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r4_apply_one_upsert_through_the_builder[ APPLY ]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r4_apply_one_upsert_through_the_builder[apply]: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r5_cli_dry_run_downgrades_apply: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r6_read_discipline: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r7_paging_and_cap: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r8_bucket_counts: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)
- test_r9_clusters_and_systematic_rule: E AssertionError: scripts/cron_learning.py does not exist (D22 not implemented)

## 3. Prototype (own detached scratch worktree, removed)

Scratch <scratchpad>/g5x via `git -c core.longpaths=true worktree add --detach <path> ec747b49`, scripts-only (no junction), removed with `git worktree remove --force` and verified gone. Prototype = scripts/cron_learning.py (NEW) + railway.learning.json (NEW, the 3.2 object) + E1 (tests/test_s81_kb_schema.py P02_ALLOWED: the comment + the two cron_learning rows after the cron_kb_coverage rows, CRLF kept) + the E2 / E3 deletions. Saved: <scratchpad>/S81-G5_red/prototype.diff (1,411 lines; its only bytes > 127 sit inside the DELETED rotation files) + <scratchpad>/S81-G5_red/prototype_files/. Never committed; the real worktree's scripts/, tests/test_s81_kb_schema.py and CLAUDE.md untouched.

    [pyt] tag=g5red-proto-3 start=2026-11-05 03:58:36 end=2026-11-05 03:58:45 elapsed=8s bound=600s status=OK rc=0   (final RED bytes: 50 passed, flag unset in the runner env)
    [pyt] tag=g5red-proto-1 start=2026-11-05 03:49:42 end=2026-11-05 03:49:53 elapsed=11s bound=600s status=OK rc=0   (first RED bytes: 50 passed)
    [pyt] tag=g5red-proto-2 start=2026-11-05 03:53:32 end=2026-11-05 03:53:51 elapsed=19s bound=600s status=OK rc=0   (50 passed)
    [pyt] tag=g5red-proto-amb-true start=2026-11-05 03:50:05 end=2026-11-05 03:50:24 elapsed=19s bound=600s status=OK rc=0   (ENABLE_LEARNING_JOB=true in the runner env: 50 passed)
    [pyt] tag=g5red-proto-amb-apply start=2026-11-05 03:50:25 end=2026-11-05 03:50:54 elapsed=29s bound=600s status=OK rc=0   (ENABLE_LEARNING_JOB=apply in the runner env: 50 passed)
    [pyt] tag=g5red-proto-pins start=2026-11-05 03:51:04 end=2026-11-05 03:51:44 elapsed=40s bound=1200s status=FAIL rc=1   (kb_schema with E1, exemplar_contamination, s16b, s05, s08b, legal_s78, legal_disclosure_s77, retro_w1_2b, u3c, secret_scan, d17: 1 failed / 1083 passed; the 1 = the d17 test_r9 CRLF baseline)
    every prototype run: [hermeticity] sentinel checked 50 test(s) (1084 for the pins run); [netguard] blocked 0 attempt(s) from 0 node(s)

Flag OFF / DRY / APPLY: each row sets the flag itself (R2 OFF spellings, R3 DRY, R4 / R12 / R16 / R21 APPLY, R5 APPLY + --dry-run), and the ambient runs prove the autouse fixture isolates them. The prototype found no spec row wrong; section 8 lists what the rows fix beyond the spec text.

## 4. Mutation table (byte copies of the prototype in the scratch worktree; .qa-mutation.lock held; restored + sha256-verified after each; final sha ok)

| M | mutation | spec killers | result | killing nodes (measured) | pyt |
|---|---|---|---|---|---|
| M1 | client built before the OFF check | R2, R18 | KILLED (assertion) | test_r11_window_and_day, test_r18_client_failure_exits_one[raises], test_r2_off_is_one_line_and_nothing_else[', test_r2_off_is_one_line_and_nothing_else[''], test_r2_off_is_one_line_and_nothing_else['0'], test_r2_off_is_one_line_and_nothing_else['dry'], test_r2_off_is_one_line_and_nothing_else['false'], test_r2_off_is_one_line_and_nothing_else['garbage'], test_r2_off_is_one_line_and_nothing_else['no'], test_r2_off_is_one_line_and_nothing_else['off'], test_r2_off_is_one_line_and_nothing_else[unset] | [pyt] tag=g5red-mut-M1 start=2026-11-05 03:58:54 end=2026-11-05 03:59:15 elapsed=22s bound=600s status=FAIL rc=1; 11 failed, 39 passed, 2 warnings in 19.85s |
| M2 | run_mode -> house_flag semantics (truthy writes) | R3, R4 | KILLED (assertion) | test_r11_window_and_day, test_r12_proposals, test_r14_report_log_and_rows_are_deidentified, test_r16_absent_kb_tables_are_counted_skips, test_r1_module_and_seams, test_r21_apply_is_idempotent_per_day, test_r23_never_writes_data_dir, test_r29_log_templates, test_r3_dry_reads_and_never_writes[, test_r3_dry_reads_and_never_writes[1], test_r3_dry_reads_and_never_writes[On], test_r3_dry_reads_and_never_writes[true], test_r3_dry_reads_and_never_writes[yes], test_r4_apply_one_upsert_through_the_builder[, test_r4_apply_one_upsert_through_the_builder[apply], test_r5_cli_dry_run_downgrades_apply, test_r7_paging_and_cap | [pyt] tag=g5red-mut-M2 start=2026-11-05 03:59:16 end=2026-11-05 03:59:25 elapsed=9s bound=600s status=FAIL rc=1; 17 failed, 33 passed, 2 warnings in 8.09s |
| M3 | drop .order(id) from the windowed read | R6, R7 | KILLED (assertion) | test_r6_read_discipline, test_r7_paging_and_cap | [pyt] tag=g5red-mut-M3 start=2026-11-05 03:59:26 end=2026-11-05 03:59:37 elapsed=11s bound=600s status=FAIL rc=1; 2 failed, 48 passed, 2 warnings in 9.87s |
| M4 | .lt(window end) -> .lte | R8, R11 | KILLED (assertion) | test_r12_proposals, test_r17_one_table_error_isolated, test_r28_context_metrics, test_r6_read_discipline, test_r8_bucket_counts, test_r9_clusters_and_systematic_rule | [pyt] tag=g5red-mut-M4 start=2026-11-05 03:59:37 end=2026-11-05 03:59:53 elapsed=16s bound=600s status=FAIL rc=1; 6 failed, 44 passed, 2 warnings in 12.37s |
| M5 | actors >= min_devices -> cases >= min_devices | R9, R10 | KILLED (assertion) | test_r12_proposals, test_r9_clusters_and_systematic_rule | [pyt] tag=g5red-mut-M5 start=2026-11-05 03:59:53 end=2026-11-05 04:00:03 elapsed=9s bound=600s status=FAIL rc=1; 2 failed, 48 passed, 2 warnings in 8.08s |
| M6 | change_suggestion added to FEEDBACK_COLUMNS | R6, R14 | KILLED (assertion) | test_r1_module_and_seams, test_r6_read_discipline | [pyt] tag=g5red-mut-M6 start=2026-11-05 04:00:03 end=2026-11-05 04:00:20 elapsed=17s bound=600s status=FAIL rc=1; 2 failed, 48 passed, 2 warnings in 12.41s |
| M7 | de-identification screen skipped | R14 | KILLED (assertion) | test_r12_proposals, test_r13_exemplar_candidates, test_r14_report_log_and_rows_are_deidentified | [pyt] tag=g5red-mut-M7 start=2026-11-05 04:00:26 end=2026-11-05 04:01:01 elapsed=35s bound=600s status=FAIL rc=1; 3 failed, 47 passed, 2 warnings in 31.60s |
| M8 | upsert also in DRY | R3 | KILLED (assertion) | test_r3_dry_reads_and_never_writes[, test_r3_dry_reads_and_never_writes[1], test_r3_dry_reads_and_never_writes[On], test_r3_dry_reads_and_never_writes[true], test_r3_dry_reads_and_never_writes[yes], test_r5_cli_dry_run_downgrades_apply | [pyt] tag=g5red-mut-M8 start=2026-11-05 04:01:02 end=2026-11-05 04:01:24 elapsed=23s bound=600s status=FAIL rc=1; 6 failed, 44 passed, 2 warnings in 21.04s |
| M9 | on_conflict "day,metric" -> "metric" | R4, R21 | KILLED (assertion) | test_r21_apply_is_idempotent_per_day, test_r4_apply_one_upsert_through_the_builder[, test_r4_apply_one_upsert_through_the_builder[apply] | [pyt] tag=g5red-mut-M9 start=2026-11-05 04:01:25 end=2026-11-05 04:01:45 elapsed=20s bound=600s status=FAIL rc=1; 3 failed, 47 passed, 2 warnings in 18.67s |
| M10 | a kb table read error raises instead of a counted skip | R16, R17 | KILLED (assertion) | test_r16_absent_kb_tables_are_counted_skips, test_r20_metric_names_closed_and_valid, test_r29_log_templates | [pyt] tag=g5red-mut-M10 start=2026-11-05 04:01:46 end=2026-11-05 04:01:55 elapsed=9s bound=600s status=FAIL rc=1; 3 failed, 47 passed, 2 warnings in 8.13s |
| M11 | exemplars_per_category default 5 -> 10, clamp removed | R13 | KILLED (assertion) | test_r13_exemplar_candidates, test_r1_module_and_seams | [pyt] tag=g5red-mut-M11 start=2026-11-05 04:01:55 end=2026-11-05 04:02:05 elapsed=9s bound=600s status=FAIL rc=1; 2 failed, 48 passed, 2 warnings in 8.22s |
| M12 | < CRITIQUE_THRESHOLD -> <= | R27 | KILLED (assertion) | test_r12_proposals, test_r17_one_table_error_isolated, test_r27_verdict_unsupported_threshold, test_r8_bucket_counts, test_r9_clusters_and_systematic_rule | [pyt] tag=g5red-mut-M12 start=2026-11-05 04:02:05 end=2026-11-05 04:02:14 elapsed=9s bound=600s status=FAIL rc=1; 5 failed, 45 passed, 2 warnings in 7.86s |
| M13 | HINT_PREFIX filter removed on kb_gaps | R8 | KILLED (assertion) | test_r17_one_table_error_isolated, test_r8_bucket_counts, test_r9_clusters_and_systematic_rule | [pyt] tag=g5red-mut-M13 start=2026-11-05 04:02:15 end=2026-11-05 04:02:24 elapsed=9s bound=600s status=FAIL rc=1; 3 failed, 47 passed, 2 warnings in 7.79s |
| M14 | client failure returns 0 | R18 | KILLED (assertion) | test_r18_client_failure_exits_one[none], test_r18_client_failure_exits_one[raises] | [pyt] tag=g5red-mut-M14 start=2026-11-05 04:02:24 end=2026-11-05 04:02:33 elapsed=9s bound=600s status=FAIL rc=1; 2 failed, 48 passed, 2 warnings in 7.82s |
| M15 | judge_state "pending" -> "agreed" on proposals | R12 | KILLED (assertion) | test_r12_proposals | [pyt] tag=g5red-mut-M15 start=2026-11-05 04:02:34 end=2026-11-05 04:02:43 elapsed=9s bound=600s status=FAIL rc=1; 1 failed, 49 passed, 2 warnings in 7.89s |

15 / 15 KILLED, 0 survivors, no equivalence ruling needed. Every kill is an assertion failure (M14's E lines are `assert 0 == 1`; truncated node ids like `test_r3_...[` are the ' TRUE ' / ' FALSE ' / ' APPLY ' parameters). A first round on the earlier RED bytes also killed 15 / 15 (its M2 had TypeError side-kills, removed by the asserting report accessor); this table is the final-bytes round.

## 5. Other base gates (real worktree, RED file present)

    [pyt] tag=g5red-base-secretscan start=2026-11-05 04:03:50 end=2026-11-05 04:04:12 elapsed=23s bound=600s status=OK rc=0   (tests/test_secret_scan_static.py ALONE: 31 passed; [hermeticity] 31; [netguard] blocked 0)
    [pyt] tag=g5red-base-ciorder start=2026-11-05 04:04:21 end=2026-11-05 04:04:50 elapsed=28s bound=1200s status=FAIL rc=1   (CI-order set 12.1: the RED file, test_s81_kb_schema, test_exemplar_contamination, test_s81_d17_coverage, test_s81_s16b_kb_brands, test_legal_docs_u8, test_ci_gates: 44 failed / 792 passed = the 43 RED nodes + tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene (CRLF baseline); [hermeticity] 836; [netguard] blocked 0)
    The corpus gate NOT run (no price_service edit). The fourteen client jest fences NOT run (GREEN's duty).

## 6. Comm set derivation and base record (the LAST pytest step)

Union rule re-derived once at ec747b49: the reference grep = exactly the spec's 24 files; the house pins (10); the scripts/ walkers; the railway glob reader (test_s81_s16b only); the CLAUDE.md path readers (exactly the spec's 5; about 33 other files only mention CLAUDE.md in prose); the gate rows (g2, g4). The spec's 44-file list is reproduced exactly (sha256 803bde0ca1b911bb... over the sorted LF-terminated list). ADDITIONS (stated): tests/test_domain_s76.py (rglob over app/ + scripts/ text for retired hosts) and tests/test_s81_d08_jsonld_widen.py (rglob over app/ + scripts/ text for judgeme_service): both will scan the new scripts/cron_learning.py. Set = 46 files, sha256 c636b9d554cb6766c65b1103a8fddaa9065219a7e8999d5fb9e46fe302bf33b4. Excluded: the four precommit hook files (none matched); no NETWORK_FLAKY node is a member. The RED file is not a member at base. Files: <scratchpad>/S81-G5_red/COMM_SET.txt, comm_reasons.tsv (per-file reason + base source), comm_plan.json.

GC-9 per-file reuse: 11 REUSED (test_cron_few_shot_rotation.py, test_exemplar_contamination.py, test_exemplar_injection_content.py, test_m21_brand_dedup_and_verdict_copy.py, test_openai_key_log_hygiene_s69.py, test_per_category_anti_patterns.py, test_prompt_fence.py, test_shadow_experiments.py, test_start_command.py, test_verdict_prompt_exemplar_injection.py, test_verdict_prompt_forbidden_words_audit.py); 35 RUN at base (tests/test_secret_scan_static.py from its ALONE run; tests/test_s81_g4_gate_rows.py moved to RUN although its text passes the rule, because it imports scripts.cron_kb_enrich -> kb_seed_common, which changed at ec747b49; tests/test_verdict_exemplar_loader.py is in no stored record; the rest name kb_service / kb_seed_common / seed_kb_brands_wikidata / CLAUDE.md or are glob walkers). The 34 non-secret-scan run members went in 2 alphabetical chunks (25 + 9), one pytest at a time, in the REAL worktree.

    [pyt] tag=g5red-comm-base-00 start=2026-11-05 04:08:48 end=2026-11-05 04:11:52 elapsed=184s bound=1200s status=FAIL rc=1   (25 files: 2 failed, 2248 passed; the [netguard] lines name only the known passing pins: test_hermeticity_pins' example.com probe and two s04 rows hitting the neutralized.supabase.invalid sentinel)
    [pyt] tag=g5red-comm-base-01 start=2026-11-05 04:11:56 end=2026-11-05 04:13:35 elapsed=100s bound=1200s status=FAIL rc=1   (9 files: 6 failed, 631 passed; [hermeticity] 637; [netguard] blocked 0)
    + g5red-base-secretscan (section 5)

Stored (LC-6): <scratchpad>/harness/base_records/ec747b496953869c0370e4f28bf025c6f694a97d/c636b9d554cb6766c65b1103a8fddaa9065219a7e8999d5fb9e46fe302bf33b4.txt + .files + .header.txt + .pyt.log (reused-vs-run split in the header). Base FAILED set (8; all are the known CRLF working-copy hygiene nodes, identical to the same members of the stored e1491c97 record; the reused members contribute 0):
- tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
- tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
- tests/test_s81_s19_gap_queue.py::test_r15_hygiene

The deleted tests/test_cron_few_shot_rotation.py has an EMPTY base failed set (reused; green at e1491c97), so comm -23 stays meaningful at head. Known noise: d17 test_r9 (CRLF) recorded; the tiktoken egress line of test_exemplar_injection_content lives in the reused record; test_prompt_truth is not a member.

## 7. Restore check

sha256 of all 3,497 tracked files in the real worktree before (03:45) and after (04:14) the run: identical (tree digest eb0dd407c208...). HEAD ec747b49; `git status --porcelain` = `?? tests/test_s81_d22_nightly_learning.py` only. The scratch worktree is removed and absent from `git worktree list`; no .qa-mutation.lock; no g5red pytest process alive. No git write in an existing worktree; no package manager; no .env read; no network.

## 8. Deviations from the spec (the rulings applied; no row weakened)

- Fixture: 8 comparisons (fragrances x5 incl. the email-shaped C8, electronics x2 incl. a padded 'Electronics ', one without a category) instead of the spec narrative's 6: cluster C needs 2 cases and a case collapses per comparison, so C needs two electronics comparisons.
- M1 / M10 kill by assertion: every main() call goes through _call() (a raise or SystemExit out of main becomes an AssertionError) and R2 / R11's _admin_client stubs raise AssertionError (still a raising stub, still recorded). R16 asserts a '[LEARNING] table=kb_gaps read failed (_PgErr)' WARNING (the type name of the seeded error).
- R8 also seeds one kb_feedback identity + wrong row in a second run (R-G5-5: identity_wrong 1/1, cluster fragrances/kb/identity); the default literal stays 0/0. R8 also pins actor_basis to the 2.4 dict.
- R25 needle list widened to the whole 1.9 table (adds device_key_pepper, x-ai-consent-version, header_state); needles with personal / brand shapes built at run time.
- R6 pins the by-id reads: comparisons in_('id', sorted de-duplicated ids) == C1..C8; kb_specs in_('product_id') == the spec_wrong kb case products only {acme-rose-edp, birch-oud-edt} (2.3: 'the product_ids of kb_feedback spec cases'); order('id') on every read incl. the by-id ones.
- R23's 'no data path segment' is read as no data/ path literal and no '/ "data"' join (the response attribute getattr(resp, 'data') is allowed, the D17 idiom).
- R12 adds a run with LEARNING_MIN_CASES=1 / MIN_DEVICES=1 pinning the whole 2.5 action map (needs_operator for kb price, specs/specs, electronics specs; no_action for both verdict buckets).
- R13 pins the cap with a world of 8 clean fragrance candidates (default 5, knob 1 -> 3, 4 -> 4, 9 -> 5), the first exemplar entry exactly, and the version prefix '2026-11-04.'.
- R27 runs 8 one-critique worlds: (bias, missing) = (8,6)->1, (6,8)->1, (7,7)->0, (None,None)->0, (None,6)->1, (6,None)->1, (7,None)->0, (None,7)->0.
- R29 also pins: the header line is the first record, exactly one totals line (the last), and one 'table=' line per READ_TABLES entry even for a table that was not read (kb_specs / comparisons with no ids).
- R18 has a second node: _admin_client returning None also exits 1 with one ERROR line of the template (type name not pinned there).
- Comm set: +2 scripts/ walkers (test_domain_s76, test_s81_d08_jsonld_widen) -> 46 files at base; test_s81_g4_gate_rows run instead of reused (transitive kb_seed_common); test_secret_scan_static from its ALONE run.
- Contract details the rows fix beyond the spec text (GREEN must match): cluster keys bucket/category/source/field/cases/actors/demand/systematic; bucket keys cases/actors/inputs/note; tables entries {rows, status, error}; confirmed_prices = {product_0: null, product_1: null} when price_correct is not 'correct'; eval_candidates sorted by (category, n0, n1); exemplars per category sorted by (n0, n1); the report's metrics are [name, value, n] triples and equal the logged metric names.

## 9. Open questions for the gate

- R15 keeps the eval candidate of the comparison whose winner_reason carries an email shape (C8): the eval shape holds no winner_reason, so 2.5's screen leaves it clean (6 eval candidates pinned). Confirm, or rule that a row dropped as an exemplar is also dropped as an eval candidate.
- Two different users reporting the same comparison collapse to one case (2.4); whether both count as actors is unspecified. The fixture avoids it (only a same-user duplicate, f01/f02, and a same-pair duplicate confirmed row).
- Order of the de-identification screen vs the per-category cut is unpinned (R14's world has 6 raw fragrance candidates; its assertions hold either way). The prototype screens before the cut.
- Grounding is built (and its unclean entries counted in learning.dropped.deidentify) only for systematic kb spec_wrong clusters in the prototype; the rows pin dropped >= 1 only.
- test_s81_d16_operator_ingest::test_r10_runbook_names_only fails at base on this box (CRLF working copy of docs/runbooks/2026-11-kb-operator-ingest.md); recorded identically, as in the e1491c97 record.
