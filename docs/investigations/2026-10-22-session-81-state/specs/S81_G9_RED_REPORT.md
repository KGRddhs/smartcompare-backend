# S81-G9 RED REPORT (G9 FOLLOWUPS: S81-16c + D17c (+ D17d PINs) + S81-22d + S81-23b)

Agent: RED, Opus 5.5 (claude-opus-5-5). Base 39ac80ba437760d1a77eaac9670faeea505f08f4. Real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g9 (only the four new RED files added). Written through the shell (python), per the harness rule; copies at <scratchpad>/S81-G9_red/RED_REPORT.md and <scratchpad>/S81-G9_RED_REPORT.md. Binding inputs read: s81-common.txt, the spec (sha f94aaf71...), RULINGS_S81_G9 R-G9-1..10.

## 1. RED files (final bytes)

| file | bytes | sha256 | bytes>127 | CR |
|---|---|---|---|---|
| tests/test_s81_s16c_wdqs_exemption.py | 12906 | 8dca75163ca4c2c0aaf1ae47bbd2dfcb03b95aca0b25a001dce359a289711e94 | 0 | 0 |
| tests/test_s81_d17c_coverage_hosts.py | 9864 | 8a6ced21d2a7bc27d67e2bdbdd5fbde89c52de567150bd914d3c767800464488 | 0 | 0 |
| tests/test_s81_s22d_ledger_pins.py | 4913 | 6faeecc8c05ce6809d19c4b4ee70d5bf8e9c205022e4677e7364925153ea519b | 0 | 0 |
| tests/test_s81_s23b_scrapedo_super_retire.py | 6460 | af7012844356d8a73fc415626a63194fdcce32695ecc30bf0db88e0bdda0d92e | 0 | 0 |

ruff --select E9,F63,F7,F82: All checks passed. Gitleaks rule: the hex pins are named ROBOTS_EVAL_LF_SHA, SEED_COMMON_LF_SHA, S22_LF_SHA (no keyword). Synthetic values only (example.com hosts, run-time token words).

## 2. Rows per unit and the base run

- S81-16c (tests/test_s81_s16c_wdqs_exemption.py): RED R1, R1b (R-G9-4 reordered LIVE body proceeds), R2 x3, R3, R4 (reordered == None per R-G9-4; QarenBot group == named_group), R5, R5b (R-G9-4 Q-16c-2: no hint -> sleeps [2.0, 120.0, 2.0]), R6, R7 x2 (header 30 / HTTP-date + body 45), R7b x2 (R-G9-4 Q-16c-3: Retry-After 999 and body 'retry in 300 seconds' -> GIVE UP: 2 fetches, sleeps == [2.0], nothing written, one INFO with status=429 and retries=0, no 999 / 300 / http), R8 = 15 nodes; PIN P1 x3, P2 (QarenBot-group body only, R-G9-4), P3 x3, P4, P5, P6 x6 = 15 nodes.
- D17c (tests/test_s81_d17c_coverage_hosts.py): RED R1, R2, R3 x2 (1 and 2 hosts, the M4 variant), R4, R4b (R-G9-2: a failing NON-hosts family, kb_reviews raising RuntimeError -> WARNING 'family=reviews read failed (RuntimeError)', not_built=1, rc 0; main wrapped by _go so any raise is an AssertionError) = 6 nodes; PIN P1, P2, P3, P4 (coverage -I process exits, threads=[]), P5 (enrich) = 5 nodes.
- S81-22d (tests/test_s81_s22d_ledger_pins.py): RED R1 (AST: first non-docstring statement of both rows deletes the flag), R2 x4 (the S03 row functions called directly with the flag set true; _row turns any non-assert raise into an AssertionError), R3 (the literal occurs exactly twice, both inside the two rows) = 6 nodes; PIN P1 x4, P2 (three S22 frozen LF shas) = 5 nodes.
- S81-23b (tests/test_s81_s23b_scrapedo_super_retire.py): RED R1 x2, R2 (recording os stand-in: the legacy name read 0 times, the new name read), R3, R4, R5 (AST census app/ + scripts/) = 6 nodes; PIN P1 x4, P2 x4, P3, P4 = 10 nodes.

Totals: RED 33 nodes, PIN 35 nodes (68).

Base run (flags unset): `[pyt] tag=g9red-base4 start=2026-11-07 11:46:42 end=2026-11-07 11:46:53 elapsed=11s bound=600s status=FAIL rc=1`  -> 33 failed, 35 passed, 12 warnings in 10.50s

AssertionError proof per RED node (the first E line of each failure section, red_base.log):

- test_r1_live_body_exempt_two_fetches: AssertionError
- test_r1b_reordered_live_body_exempt: AssertionError
- test_r2_slash_and_extra_rules_refuse[slash]: AssertionError
- test_r2_slash_and_extra_rules_refuse[empty]: AssertionError
- test_r2_slash_and_extra_rules_refuse[allow]: AssertionError
- test_r3_qarenbot_group_refuses: AssertionError
- test_r4_helper_url_and_rules: AssertionError
- test_r5_429_then_200_one_retry: AssertionError
- test_r5b_429_no_hint_waits_the_cap: AssertionError
- test_r6_429_twice_gives_up: AssertionError
- test_r7_retry_after_header_and_body[header30]: AssertionError
- test_r7_retry_after_header_and_body[date_body45]: AssertionError
- test_r7b_hint_above_cap_gives_up[header999]: AssertionError
- test_r7b_hint_above_cap_gives_up[body300]: AssertionError
- test_r8_exemption_only_in_this_script: AssertionError
- test_r1_zero_hosts_no_pipeline_sdk: AssertionError
- test_r2_zero_hosts_no_pipeline_fake: AssertionError
- test_r3_400_counts_the_family[1]: AssertionError
- test_r3_400_counts_the_family[2]: AssertionError
- test_r4_exec_raise_counts_the_family: AssertionError
- test_r4b_failed_non_hosts_family_counts: AssertionError
- test_r1_rows_name_the_flag: AssertionError
- test_r2_rows_green_with_flag_exported[i2-false]: AssertionError
- test_r2_rows_green_with_flag_exported[i2-None]: AssertionError
- test_r2_rows_green_with_flag_exported[i6off-None]: AssertionError
- test_r2_rows_green_with_flag_exported[i6off-false]: AssertionError
- test_r3_flag_named_only_in_the_two_rows: AssertionError
- test_r1_legacy_alone_is_off[true]: AssertionError (assert rewrite: assert True is False)
- test_r1_legacy_alone_is_off[TRUE]: AssertionError (assert rewrite: assert True is False)
- test_r2_legacy_name_never_read: AssertionError
- test_r3_legacy_alone_routes_no_super_row: AssertionError
- test_r4_legacy_alone_render_params_plain: AssertionError
- test_r5_no_code_names_the_legacy: AssertionError

Every PIN node PASSED at base (35). 22d + S03 with ENABLE_COMPARE_RUN_LEDGER=true exported at base: `[pyt] tag=g9red-base-22d-exp start=2026-11-07 11:47:21 end=2026-11-07 11:47:34 elapsed=14s bound=600s status=FAIL rc=1` -> 10 failed, 216 passed, 13 warnings in 12.59s (the 6 22d RED nodes + the 4 S03 i2 / i6-off nodes; 22d P1 x4 + P2 green).

## 3. Prototype (scratch worktree <scratchpad>/g9p at 39ac80ba, backend-only, no junction; removed)

Applied by <scratchpad>/S81-G9_red/proto_apply.py (CRLF-preserving exact replacements, byte copies first): app/services/scrapedo_service.py, scripts/ab_render_providers.py, scripts/cron_kb_coverage.py, scripts/seed_kb_brands_wikidata.py, tests/test_fragrance_content_quality.py, tests/test_s81_s03_llm_ledger_v2.py, tests/test_s81_s23_bypass_retire.py. `git diff --stat`: 7 files changed, 110 insertions(+), 21 deletions(-) (hunks only, no whole-file diff). Diff: <scratchpad>/S81-G9_red/prototype.diff; the edited files: <scratchpad>/S81-G9_red/prototype_files/ (never committed; GREEN re-derives every hunk). CLAUDE.md and the two docs files NOT edited.

Summary of the prototype hunks: 16c = the WDQS_* constants + _RETRY_IN_RE / _RETRY_DIGITS_RE, wdqs_exemption_check (url by scheme / netloc / path / fragment, named_group by token-in-UA, rule_set by SORTED list equality for QARENBOT_UA and '*', fail closed), _retry_wait (Retry-After digits, else the body hint in the first 2,000 chars, else the cap; a hint above the cap -> None = give up), _pause (fetcher._polite._sleep), the gate and the GET hunks of _run (give-up line '%s query status=%d; hint above the cap; giving up retries=0'), one docstring sentence; D17c = PIPELINE_REFUSED + _PipelineRefused(RuntimeError), families_not_built counted in guarded for EVERY family (R-G9-2), the 0-host skip INFO before the pipeline, the AttributeError of the run() call re-raised as _PipelineRefused, not_built += families_not_built before the totals line; 22d = EK1 (two delenv lines); 23b = the legacy return deleted (unset -> False), the module docstring sentence, ab_render_providers.py legacy write dropped WITHOUT setting ENABLE_SCRAPEDO_SUPER (R-G9-6) + the :33 comment, EK2 (P1_CASES true/TRUE -> False; r3 / p3 / p4 start from NEW_FLAG), EK3 (7 one-token edits). Not prototyped (GREEN's, no test reads them): the source_router / structured_comparison_service comment rewording (R-G9-6 Q-23b-3), the 16c / 23b comment blocks beyond the docstring sentence.

- RED files at the prototype, flags unset: `[pyt] tag=g9red-proto4-off start=2026-11-07 11:55:35 end=2026-11-07 11:55:46 elapsed=11s bound=600s status=OK rc=0` -> 68 passed, 10 warnings in 9.85s
- RED files + the S03 file with ENABLE_KB_BRANDS=true ENABLE_KB_COVERAGE_ROLLUP=true ENABLE_COMPARE_RUN_LEDGER=true exported in the runner call only: `[pyt] tag=g9red-proto-exported start=2026-11-07 11:55:55 end=2026-11-07 11:56:13 elapsed=18s bound=600s status=OK rc=0` -> 283 passed, 12 warnings in 17.11s (netguard neutralized 3 supabase.invalid connects in S03 i1 / i3 / i4, as at base)
- The CI-order set (spec 12.1) at the prototype, flags unset: `[pyt] tag=g9red-proto-ciorder start=2026-11-07 11:56:23 end=2026-11-07 11:57:51 elapsed=88s bound=1200s status=FAIL rc=1` -> 7 failed, 1622 passed, 15 warnings in 86.04s (0:01:26); the 7 failures are the CRLF working-copy class only (s16 r27 x5, d17 r9, s22 b02: `b'\r' not in <bytes>`).

## 4. Mutation tables (byte copies in the scratch worktree, .qa-mutation.lock, the unit's RED file through pyt.py bound 600, restored and sha256-verified after each)

| M | mutation | killed | killing rows | [pyt] |
|---|---|---|---|---|
| 16c-M1 | the url check removed | KILLED | test_r4_helper_url_and_rules | [pyt] tag=g9red-16c-M1 start=2026-11-07 11:58:13 end=2026-11-07 11:58:17 elapsed=4s bound=600s status=FAIL rc=1 |
| 16c-M2 | the named-group check removed | KILLED | test_p2_named_group_body_refuses, test_r3_qarenbot_group_refuses, test_r4_helper_url_and_rules | [pyt] tag=g9red-16c-M2 start=2026-11-07 11:58:18 end=2026-11-07 11:58:22 elapsed=5s bound=600s status=FAIL rc=1 |
| 16c-M3 | rule-set equality relaxed to subset | KILLED | test_p1_r24_shapes_still_refuse[disallow], test_r4_helper_url_and_rules | [pyt] tag=g9red-16c-M3 start=2026-11-07 11:58:22 end=2026-11-07 11:58:27 elapsed=5s bound=600s status=FAIL rc=1 |
| 16c-M4 | order-SENSITIVE comparison (R-G9-4) | KILLED | test_r1b_reordered_live_body_exempt, test_r4_helper_url_and_rules | [pyt] tag=g9red-16c-M4 start=2026-11-07 11:58:27 end=2026-11-07 11:58:32 elapsed=5s bound=600s status=FAIL rc=1 |
| 16c-M5 | only the QarenBot rule set compared (not '*') | SURVIVED | - | [pyt] tag=g9red-16c-M5 start=2026-11-07 11:58:32 end=2026-11-07 11:58:36 elapsed=4s bound=600s status=OK rc=0 |
| 16c-M6 | no retry | KILLED | test_r5_429_then_200_one_retry, test_r5b_429_no_hint_waits_the_cap, test_r6_429_twice_gives_up, test_r7_retry_after_header_and_body[date_body45], test_r7_retry_after_header_and_body[header30], test_r7b_hint_above_cap_gives_up[body300], test_r7b_hint_above_cap_gives_up[header999] | [pyt] tag=g9red-16c-M6 start=2026-11-07 11:58:36 end=2026-11-07 11:58:40 elapsed=5s bound=600s status=FAIL rc=1 |
| 16c-M7 | two retries (a loop) | KILLED | test_r6_429_twice_gives_up | [pyt] tag=g9red-16c-M7 start=2026-11-07 11:58:41 end=2026-11-07 11:58:45 elapsed=4s bound=600s status=FAIL rc=1 |
| 16c-M8 | the cap removed | KILLED | test_r7b_hint_above_cap_gives_up[body300], test_r7b_hint_above_cap_gives_up[header999] | [pyt] tag=g9red-16c-M8 start=2026-11-07 11:58:45 end=2026-11-07 11:58:50 elapsed=5s bound=600s status=FAIL rc=1 |
| 16c-M9 | Retry-After ignored | KILLED | test_r7_retry_after_header_and_body[header30], test_r7b_hint_above_cap_gives_up[header999] | [pyt] tag=g9red-16c-M9 start=2026-11-07 11:58:50 end=2026-11-07 11:58:55 elapsed=5s bound=600s status=FAIL rc=1 |
| 16c-M10 | retry on 500 too | KILLED | test_p5_non_retry_failure_line | [pyt] tag=g9red-16c-M10 start=2026-11-07 11:58:55 end=2026-11-07 11:58:59 elapsed=5s bound=600s status=FAIL rc=1 |
| 16c-M11 | the exemption line logged on an allowed body | KILLED | test_p4_allowed_body_byte_identical, test_r1_live_body_exempt_two_fetches, test_r1b_reordered_live_body_exempt | [pyt] tag=g9red-16c-M11 start=2026-11-07 11:58:59 end=2026-11-07 11:59:04 elapsed=5s bound=600s status=FAIL rc=1 |
| 16c-M12 | the refusal suffix dropped | KILLED | test_r2_slash_and_extra_rules_refuse[allow], test_r2_slash_and_extra_rules_refuse[empty], test_r2_slash_and_extra_rules_refuse[slash], test_r3_qarenbot_group_refuses | [pyt] tag=g9red-16c-M12 start=2026-11-07 11:59:04 end=2026-11-07 11:59:09 elapsed=5s bound=600s status=FAIL rc=1 |
| d17c-M1 | the 0-host guard removed | KILLED | test_r1_zero_hosts_no_pipeline_sdk, test_r2_zero_hosts_no_pipeline_fake | [pyt] tag=g9red-d17c-M1 start=2026-11-07 11:59:09 end=2026-11-07 11:59:16 elapsed=7s bound=600s status=FAIL rc=1 |
| d17c-M2 | guard len(hosts) <= 1 | KILLED | test_p1_one_host_body_shape, test_r3_400_counts_the_family[1], test_r4_exec_raise_counts_the_family | [pyt] tag=g9red-d17c-M2 start=2026-11-07 11:59:16 end=2026-11-07 11:59:23 elapsed=7s bound=600s status=FAIL rc=1 |
| d17c-M3 | the family not counted | KILLED | test_r3_400_counts_the_family[1], test_r3_400_counts_the_family[2], test_r4_exec_raise_counts_the_family, test_r4b_failed_non_hosts_family_counts | [pyt] tag=g9red-d17c-M3 start=2026-11-07 11:59:23 end=2026-11-07 11:59:30 elapsed=7s bound=600s status=FAIL rc=1 |
| d17c-M4 | counted per host | KILLED | test_r3_400_counts_the_family[2] | [pyt] tag=g9red-d17c-M4 start=2026-11-07 11:59:30 end=2026-11-07 11:59:37 elapsed=7s bound=600s status=FAIL rc=1 |
| d17c-M5 | the skip counts as not_built | KILLED | test_r1_zero_hosts_no_pipeline_sdk | [pyt] tag=g9red-d17c-M5 start=2026-11-07 11:59:37 end=2026-11-07 11:59:44 elapsed=7s bound=600s status=FAIL rc=1 |
| d17c-M6 | the label applied to every exception | KILLED | test_r4_exec_raise_counts_the_family, test_r4b_failed_non_hosts_family_counts | [pyt] tag=g9red-d17c-M6 start=2026-11-07 11:59:44 end=2026-11-07 11:59:51 elapsed=7s bound=600s status=FAIL rc=1 |
| d17c-M7 | skip line omitted | KILLED | test_r1_zero_hosts_no_pipeline_sdk, test_r2_zero_hosts_no_pipeline_fake | [pyt] tag=g9red-d17c-M7 start=2026-11-07 11:59:51 end=2026-11-07 11:59:59 elapsed=7s bound=600s status=FAIL rc=1 |
| d17c-M8 | only the hosts family counted (R-G9-2) | KILLED | test_r4b_failed_non_hosts_family_counts | [pyt] tag=g9red-d17c-M8 start=2026-11-07 11:59:59 end=2026-11-07 12:00:06 elapsed=8s bound=600s status=FAIL rc=1 |
| 22d-M1 | EK1 in i2 only | KILLED | test_r1_rows_name_the_flag, test_r2_rows_green_with_flag_exported[i6off-None], test_r2_rows_green_with_flag_exported[i6off-false], test_r3_flag_named_only_in_the_two_rows | [pyt] tag=g9red-22d-M1 start=2026-11-07 12:00:06 end=2026-11-07 12:00:12 elapsed=5s bound=600s status=FAIL rc=1 |
| 22d-M2 | the flag added to UNIT_ENV instead | KILLED | test_r1_rows_name_the_flag, test_r2_rows_green_with_flag_exported[i2-None], test_r2_rows_green_with_flag_exported[i2-false], test_r2_rows_green_with_flag_exported[i6off-None], test_r2_rows_green_with_flag_exported[i6off-false], test_r3_flag_named_only_in_the_two_rows | [pyt] tag=g9red-22d-M2 start=2026-11-07 12:00:12 end=2026-11-07 12:00:18 elapsed=6s bound=600s status=FAIL rc=1 |
| 22d-M3 | setenv(LEDGER_FLAG, 'true') in the rows | KILLED | test_p1_rows_green_with_flag_unset[i2-None], test_p1_rows_green_with_flag_unset[i2-false], test_p1_rows_green_with_flag_unset[i6off-None], test_p1_rows_green_with_flag_unset[i6off-false], test_r1_rows_name_the_flag, test_r2_rows_green_with_flag_exported[i2-None], test_r2_rows_green_with_flag_exported[i2-false], test_r2_rows_green_with_flag_exported[i6off-None], test_r2_rows_green_with_flag_exported[i6off-false] | [pyt] tag=g9red-22d-M3 start=2026-11-07 12:00:18 end=2026-11-07 12:00:24 elapsed=6s bound=600s status=FAIL rc=1 |
| 23b-M1 | the legacy branch kept | KILLED | test_r1_legacy_alone_is_off[TRUE], test_r1_legacy_alone_is_off[true], test_r2_legacy_name_never_read, test_r3_legacy_alone_routes_no_super_row, test_r4_legacy_alone_render_params_plain, test_r5_no_code_names_the_legacy | [pyt] tag=g9red-23b-M1 start=2026-11-07 12:00:24 end=2026-11-07 12:00:29 elapsed=5s bound=600s status=FAIL rc=1 |
| 23b-M2 | unset -> True | KILLED | test_p2_production_state_off_identity[unset], test_r1_legacy_alone_is_off[TRUE], test_r1_legacy_alone_is_off[true], test_r3_legacy_alone_routes_no_super_row, test_r4_legacy_alone_render_params_plain | [pyt] tag=g9red-23b-M2 start=2026-11-07 12:00:29 end=2026-11-07 12:00:35 elapsed=5s bound=600s status=FAIL rc=1 |
| 23b-M3 | the legacy read moved to os.getenv | KILLED | test_r1_legacy_alone_is_off[TRUE], test_r1_legacy_alone_is_off[true], test_r2_legacy_name_never_read, test_r3_legacy_alone_routes_no_super_row, test_r4_legacy_alone_render_params_plain, test_r5_no_code_names_the_legacy | [pyt] tag=g9red-23b-M3 start=2026-11-07 12:00:35 end=2026-11-07 12:00:40 elapsed=5s bound=600s status=FAIL rc=1 |
| 23b-M4 | the strip dropped | KILLED | test_p1_new_name_truthy_on[ON_padded] | [pyt] tag=g9red-23b-M4 start=2026-11-07 12:00:40 end=2026-11-07 12:00:45 elapsed=5s bound=600s status=FAIL rc=1 |
| 23b-M5 | _super_enabled stops delegating (returns False) | KILLED | test_p1_new_name_truthy_on[1], test_p1_new_name_truthy_on[ON_padded], test_p1_new_name_truthy_on[true], test_p1_new_name_truthy_on[yes] | [pyt] tag=g9red-23b-M5 start=2026-11-07 12:00:45 end=2026-11-07 12:00:51 elapsed=6s bound=600s status=FAIL rc=1 |

Result: 27 of 28 KILLED (every kill an AssertionError). 16c-M5 SURVIVED and is EQUIVALENT (asks a ruling): with no group whose token occurs in the QarenBot UA, robots_eval.rules_for_agent(groups, QARENBOT_UA) merges exactly the '*' groups, so the QarenBot and '*' rule sets are identical; any body where they differ carries a named group, which the named_group check refuses first. The spec's 'killed by R2 Allow: /x' cannot hold (that rule lands in both sets). Restored shas after the run: seed 13fc01ea..., cron_kb_coverage 72bd0914..., scrapedo_service 1531958f... (the prototype bytes).

## 5. Corpus gate (scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_SCRAPEDO_SUPER,ENABLE_KB_BRANDS,ENABLE_KB_COVERAGE_ROLLUP, every flag unset, never beside a pytest)

- corpus_base (start 11:48:07 rc=0 end 11:54:59): RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656 / OVERALL SHA256 cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c
- corpus_proto (start 12:01:25 rc=0 end 12:08:17): RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656 / OVERALL SHA256 cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c

EQUAL (measured both, never inferred): cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c at base (= the spec's value) and at the prototype HEAD.

## 6. Other base gates

- CI-order set at base (one call, bound 1200, flags unset, the four RED files included): `[pyt] tag=g9red-base-ciorder start=2026-11-07 12:08:50 end=2026-11-07 12:10:17 elapsed=87s bound=1200s status=FAIL rc=1` -> 40 failed, 1589 passed, 17 warnings in 84.88s (0:01:24); failed = the 33 RED nodes (by design) + the 7 CRLF-class nodes (list: <scratchpad>/S81-G9_red/base_ciorder_failed.txt).
- tests/test_secret_scan_static.py alone at base: `[pyt] tag=g9red-base-secretscan start=2026-11-07 12:12:20 end=2026-11-07 12:12:26 elapsed=6s bound=600s status=OK rc=0` -> 31 passed, 1 warning in 5.58s
- The fourteen client fences + b3a/nativeStrings: NOT RUN (GREEN's, through the junction the orchestrator creates).
- The four hook test files (tests/test_precommit_hook*.py): NOT RUN (no .githooks change).

## 7. Comm set (R-G9-9) and its base record at 39ac80ba

Derivation <scratchpad>/S81-G9_red/comm2.py: the spec's comm.py rule executed unchanged over the real worktree at 39ac80ba (the four RED files dropped from the set), EXTENDED by (1) the four RED files' harness imports (test_s81_s16_kb_seed, test_s81_d17_coverage, test_s81_s03_llm_ledger_v2, test_s81_s23_bypass_retire: all already members), (2) the transitive test-module importer closure by AST (any test importing a member test module, recursively), (3) the scripts/ walkers, (4) the railway config readers; MINUS the four hook files.

- members: 673 (COMM_SET.txt, sorted LF list sha256 fe55771e5c6d54c32868e215f3ec9e0b0e31ed04aae80aafb61f18522ac0ffea); overlap with the spec's 669: 669; additions 4: tests/test_migration_044_apple_siwa_tokens.py, tests/test_retro_w1_3.py, tests/test_s81_s10_gate_rows.py, tests/test_w4_13_flag_off_ledger.py; removals 0.
- inclusion reason counts: {"app.main": 140, "claude_md": 38, "closure": 625, "forced": 16, "importer_closure": 4, "railway_reader": 14, "red_harness": 4, "scripts_walker": 19, "source_scan": 144, "symbol": 51}
- GC-9 split: REUSE 251 (all from daf86d32/ea0d2f1b...: bytes unchanged daf86d32 -> 39ac80ba, naming none of the eight #394 stems nor CLAUDE.md nor data/, no app.main / app.api / TestClient user, no glob / dir walker); RUN 422 at 39ac80ba (reason counts {"app_main_or_testclient": 162, "bytes_changed_daf86d32": 4, "names": 373, "not_in_daf86d32_records": 4, "walker": 41}). The spec's first split was 365 / 304: this run is wider because the data/ and app.api clauses are matched textually.
- the reused FAILED ids carried over: 4 (tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable, tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene, tests/test_s81_s19_gap_queue.py::test_r15_hygiene)
- record stored: <scratchpad>/harness/base_records/39ac80ba437760d1a77eaac9670faeea505f08f4/fe55771e5c6d54c32868e215f3ec9e0b0e31ed04aae80aafb61f18522ac0ffea.{files,header.txt,txt,pyt.log}; FAILED ids 25; COMPLETE

Every comm [pyt] line:

- `[pyt] tag=g9red-comm-c00 start=2026-11-07 12:47:46 end=2026-11-07 12:48:25 elapsed=39s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9red-comm-c01 start=2026-11-07 12:48:26 end=2026-11-07 12:49:07 elapsed=41s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c02 start=2026-11-07 12:49:08 end=2026-11-07 12:50:13 elapsed=65s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c03 start=2026-11-07 12:50:13 end=2026-11-07 12:50:31 elapsed=18s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c04 start=2026-11-07 12:50:32 end=2026-11-07 12:51:51 elapsed=79s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c05 start=2026-11-07 12:51:51 end=2026-11-07 12:52:30 elapsed=38s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c06 start=2026-11-07 12:52:31 end=2026-11-07 12:52:57 elapsed=26s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c07 start=2026-11-07 12:52:58 end=2026-11-07 12:53:26 elapsed=28s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9red-comm-c08 start=2026-11-07 12:53:27 end=2026-11-07 12:54:09 elapsed=43s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9red-comm-c09 start=2026-11-07 12:54:10 end=2026-11-07 12:55:38 elapsed=88s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c10 start=2026-11-07 12:55:40 end=2026-11-07 12:57:45 elapsed=125s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c11 start=2026-11-07 12:57:46 end=2026-11-07 12:59:26 elapsed=101s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9red-comm-c12 start=2026-11-07 12:59:28 end=2026-11-07 13:01:06 elapsed=98s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9red-comm-c13 start=2026-11-07 13:01:07 end=2026-11-07 13:02:36 elapsed=89s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c14 start=2026-11-07 13:02:37 end=2026-11-07 13:03:25 elapsed=48s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c15 start=2026-11-07 13:03:26 end=2026-11-07 13:04:09 elapsed=43s bound=1200s status=OK rc=0`
- `[pyt] tag=g9red-comm-c16 start=2026-11-07 13:04:10 end=2026-11-07 13:04:50 elapsed=40s bound=1200s status=OK rc=0`

Base FAILED set (sorted):

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
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
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

## 8. Every other [pyt] line

- `[pyt] tag=g9red-base4 start=2026-11-07 11:46:42 end=2026-11-07 11:46:53 elapsed=11s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-base-22d-exp start=2026-11-07 11:47:21 end=2026-11-07 11:47:34 elapsed=14s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-proto4-off start=2026-11-07 11:55:35 end=2026-11-07 11:55:46 elapsed=11s bound=600s status=OK rc=0`
- `[pyt] tag=g9red-proto-exported start=2026-11-07 11:55:55 end=2026-11-07 11:56:13 elapsed=18s bound=600s status=OK rc=0`
- `[pyt] tag=g9red-proto-ciorder start=2026-11-07 11:56:23 end=2026-11-07 11:57:51 elapsed=88s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9red-base-ciorder start=2026-11-07 12:08:50 end=2026-11-07 12:10:17 elapsed=87s bound=1200s status=FAIL rc=1`
- `[pyt] tag=g9red-base-secretscan start=2026-11-07 12:12:20 end=2026-11-07 12:12:26 elapsed=6s bound=600s status=OK rc=0`
- `[pyt] tag=g9red-16c-M1 start=2026-11-07 11:58:13 end=2026-11-07 11:58:17 elapsed=4s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M2 start=2026-11-07 11:58:18 end=2026-11-07 11:58:22 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M3 start=2026-11-07 11:58:22 end=2026-11-07 11:58:27 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M4 start=2026-11-07 11:58:27 end=2026-11-07 11:58:32 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M5 start=2026-11-07 11:58:32 end=2026-11-07 11:58:36 elapsed=4s bound=600s status=OK rc=0`
- `[pyt] tag=g9red-16c-M6 start=2026-11-07 11:58:36 end=2026-11-07 11:58:40 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M7 start=2026-11-07 11:58:41 end=2026-11-07 11:58:45 elapsed=4s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M8 start=2026-11-07 11:58:45 end=2026-11-07 11:58:50 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M9 start=2026-11-07 11:58:50 end=2026-11-07 11:58:55 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M10 start=2026-11-07 11:58:55 end=2026-11-07 11:58:59 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M11 start=2026-11-07 11:58:59 end=2026-11-07 11:59:04 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-16c-M12 start=2026-11-07 11:59:04 end=2026-11-07 11:59:09 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-d17c-M1 start=2026-11-07 11:59:09 end=2026-11-07 11:59:16 elapsed=7s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-d17c-M2 start=2026-11-07 11:59:16 end=2026-11-07 11:59:23 elapsed=7s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-d17c-M3 start=2026-11-07 11:59:23 end=2026-11-07 11:59:30 elapsed=7s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-d17c-M4 start=2026-11-07 11:59:30 end=2026-11-07 11:59:37 elapsed=7s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-d17c-M5 start=2026-11-07 11:59:37 end=2026-11-07 11:59:44 elapsed=7s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-d17c-M6 start=2026-11-07 11:59:44 end=2026-11-07 11:59:51 elapsed=7s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-d17c-M7 start=2026-11-07 11:59:51 end=2026-11-07 11:59:59 elapsed=7s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-d17c-M8 start=2026-11-07 11:59:59 end=2026-11-07 12:00:06 elapsed=8s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-22d-M1 start=2026-11-07 12:00:06 end=2026-11-07 12:00:12 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-22d-M2 start=2026-11-07 12:00:12 end=2026-11-07 12:00:18 elapsed=6s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-22d-M3 start=2026-11-07 12:00:18 end=2026-11-07 12:00:24 elapsed=6s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-23b-M1 start=2026-11-07 12:00:24 end=2026-11-07 12:00:29 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-23b-M2 start=2026-11-07 12:00:29 end=2026-11-07 12:00:35 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-23b-M3 start=2026-11-07 12:00:35 end=2026-11-07 12:00:40 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-23b-M4 start=2026-11-07 12:00:40 end=2026-11-07 12:00:45 elapsed=5s bound=600s status=FAIL rc=1`
- `[pyt] tag=g9red-23b-M5 start=2026-11-07 12:00:45 end=2026-11-07 12:00:51 elapsed=6s bound=600s status=FAIL rc=1`

## 9. Deviations

- 16c R7 split per R-G9-4: the spec's 999 -> 120 case moved to R7b (GIVE UP: 2 fetches, sleeps == [2.0], nothing written, one INFO with status=429 and retries=0); R7b also carries a body hint above the cap ('retry in 300 seconds') since the ruling says 'a hint ABOVE the cap'. The give-up INFO's exact wording is the GREEN's; the row pins only 'status=429', 'retries=0' and constants-only (no 999 / 300 / http).
- 16c R1b (new, R-G9-4) and R5b (new, Q-16c-2) added; R4's reordered case asserts None; P2 keeps only the QarenBot-group body; R4 also asserts the named-group body == 'named_group' and LIVE + 'Disallow: /' == 'rule_set'.
- 16c P6 runs with client=None so a reached resolve_client would record a factory call (the Rig patches common._admin_client); P5 asserts the exact base line '[KB_BRANDS] query failed status=500' and no report.
- 16c M5 ('only the QarenBot rule set compared') is EQUIVALENT (survivor): rules_for_agent(QARENBOT_UA) == rules_for_agent('*') whenever no named group exists, and a named group is refused first. The spec's killer (R2 Allow: /x) cannot kill it.
- 16c M4 is the R-G9-4 'order-SENSITIVE comparison' mutant (killed by R1b + R4); M3 ('subset') is killed by R4's one-rule body and P1[disallow].
- D17c: R-G9-2 'every failed family counted' is pinned by R4b (kb_reviews raising) plus an added mutant d17c-M8 ('only the hosts family counted', killed by R4b). R3 is parametrized over 1 and 2 hosts (the M4 'counted per host' killer the spec asked for).
- D17c P1 / P2 / R1 / R3 use the REAL upstash_redis.Redis with _http._client replaced by an httpx MockTransport recorder (the spec probe's construction; a private SDK attribute: a SDK bump that renames it turns these rows red loudly). P2 uses rest_encoding=None. KB_COVERAGE_MAX_HOSTS=500 is set in every row (full configuration).
- D17c P4 / P5 run each cron main in a 'python -I' subprocess with every UPSTASH* / SUPABASE* / ENABLE_* name removed from the child env (timeout 60 s), asserting rc=0 and threads=[]; the subprocess has no netguard but makes no socket call (MockTransport, chain fake client).
- 22d R2 / P1 call the S03 row functions directly with this file's own monkeypatch; the S03 autouse _unit_env is replayed by this file's autouse fixture. At base the 4 R2 nodes fail on the S03 rows' own `assert not _called(calls)` (AssertionError), no wrapper needed; _row still converts any other raise to an AssertionError.
- 22d R3 counts the literal by TEXT lines (the EK1 comment text names no flag, so EK1 as specified passes).
- 23b R2 replaces scrapedo_service.os with a recording stand-in (getenv / environ.get / __getitem__ / __contains__ recorded, everything else delegated) and also asserts the new name WAS read (a vacuity guard).
- 23b P2 covers unset / 'false' / '0' / '' with the legacy unset; P1 asserts params + sephora routing for 'true' / '1' / 'yes' / ' ON '.
- Comm set: 673 = the spec's 669 + 4 importer-closure additions (test_migration_044_apple_siwa_tokens, test_retro_w1_3, test_s81_s10_gate_rows, test_w4_13_flag_off_ledger); 0 removals. The reuse split is 251 REUSE / 422 RUN (the spec's first split 304 / 365): my clause matching (data/ textual, app.api) is wider, so more members ran at base (conservative).
- Comm driver: the first launch's foreign-pytest detector matched the stall_monitor command line ('--pytest-max'); that driver (mine, waiting, no pytest child) was stopped with taskkill and relaunched once with the narrowed pattern; no chunk had started.
- Not prototyped (no test reads them; GREEN's): the source_router / structured_comparison_service comment rewording (R-G9-6 Q-23b-3), the scrapedo_service transition comment block :42-57, the docs files and CLAUDE.md.
- Base FAILED set at 39ac80ba = 25 = the 24 known environmental ids of the daf86d32 records + tests/test_s81_s18b_store_label.py::test_r2_table_shape (a G8 file new on main; the CRLF working-copy class: `b'' not in` over data/merchant_labels.json, the assertion names 048_compare_runs.sql in its loop); the other three G8 files are green at base.
- pyt.py writes its [pyt] summary line to stdout only (not into --log): every [pyt] line in this report is the captured stdout (other_pyt_lines.txt, comm_pyt_lines.txt).

## 10. Open questions for the gate

- Rule 16c-M5 equivalent (no killing row possible while the named_group check stands first)?
- The 16c give-up INFO wording (R-G9-4 Q-16c-3): the RED pins 'status=429' + 'retries=0' + constants-only; the prototype used '[KB_BRANDS] query status=429; hint above the cap; giving up retries=0'. Confirm retries=0 is the intended count (no retry was made).
- D17c rows touch upstash_redis' private Redis._http._client (as the spec's probe did): acceptable as the SDK seam?

## 11. Restore check

Real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g9 at 39ac80ba437760d1a77eaac9670faeea505f08f4.
git status --short:
    ?? tests/test_s81_d17c_coverage_hosts.py
    ?? tests/test_s81_s16c_wdqs_exemption.py
    ?? tests/test_s81_s22d_ledger_pins.py
    ?? tests/test_s81_s23b_scrapedo_super_retire.py
git diff --stat HEAD (tracked files vs base): '' (empty = every tracked file equals the base); git ls-files -m: ''
Scratch worktree <scratchpad>/g9p: removed with git worktree remove --force at 12:08; git worktree list grep g9p: '0' matches; directory exists: no.
Mutation lock: removed by the harness after the last restore (no .qa-mutation.lock left; the scratch worktree is gone).
Orphan pytest of mine: 0 processes with a g9red tag.
Comm drivers: launch 1 stopped (its foreign-pytest pattern matched stall_monitor's --pytest-max; no chunk started); launch 2 stopped while WAITING (no child) to remove its 1800 s wait cap; launch 3 completed all 17 chunks (it re-ran c00-c05 because the resume check read the log, which holds no [pyt] line: the latest run of each chunk is the record, duplicates dropped by tag).

