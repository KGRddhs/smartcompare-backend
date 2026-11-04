# S81-G3 RED REPORT (G3 KB-INGEST: S81-17 KB-INGEST + D05 FIELD-STATUS, D14 LIVE-ROBOTS)

Agent: the G3 RED agent (Opus 5.5), 2026-11-04. Base 744616e37d031923e522e30740b687de76482ee9 (real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g3). Written through the shell (python), as the harness refuses a subagent Write of a report .md. Spec sha256 cbeb3cb6fa4b082c5a634d09e8aa9ae0c1beff43b9934c1f42de630c5dd9fb93 (measured); rulings RULINGS_S81_G3 R-G3-1..18 applied.

## 1. Files written (the ONLY changes in the real worktree; untracked)

| file | bytes | sha256 | bytes>127 | CR |
|---|---|---|---|---|
| tests/test_s81_d14_live_robots.py | 50467 | 542cd25984632308b7b1321753438c09abfe139d5fe9f653681277c7246147b9 | 0 | 0 |
| tests/test_s81_s17_kb_ingest.py | 54300 | 547cdb741bcf03483a586888fed42d6b82addf1ecb8ee8fbfbafd498f5959f63 | 0 | 0 |
| tests/fixtures/s81_d14_flag_off_golden.json | 5128 | 55851c046262be9812abf3ac7fc70034fc4503e4d01da85e633f7acb5cff5c4f | 0 | 0 |
| tests/fixtures/s81_s17_flag_off_golden.json | 8178 | 514d1cd29252c321c4cae1a7cbbe753a3d9c4b0875e3be36d53a2294cea69a98 | 0 | 0 |

Golden sha256s: tests/fixtures/s81_d14_flag_off_golden.json = 55851c046262be9812abf3ac7fc70034fc4503e4d01da85e633f7acb5cff5c4f (recorded twice at base, identical: d14_golden_try1/2.json); tests/fixtures/s81_s17_flag_off_golden.json = 514d1cd29252c321c4cae1a7cbbe753a3d9c4b0875e3be36d53a2294cea69a98 (recorded at base; identical over re-records try3..try6 after the hermetic refusal-log patch). Recorder: `python -m tests.<module> <out.json>` at the base sha, cwd the worktree, .venv-qaren, dotenv disabled, network blocked (the FY25 recorder preamble).

## 2. Rows and node counts

D14 (tests/test_s81_d14_live_robots.py): RED L1 (2 nodes), L2 (20 cases), L2b (20), L3 (4 nodes: refresh once off-loop; failing refresh keeps last good until MAX_STALE; records_snapshot age-aware (R-G3-5); no running loop decides from the memo and never raises (R-G3-5)), L4 (10: curl, same_site initial, same_site hop, shopify, woo, algolia harvest, algolia explicit, url base, url v2 initial, url v2 hop), L5 (8 args byte-identical to the golden + 3 outcome nodes ok/fail/challenge), L6 (1), L7 (1), L8 (2 rest/stream + 2 nothing-attempted / health-off), L9 (2), L10 (1), L11 (1) = 77 RED nodes; PIN P1 (8 fetchers x 4 OFF spellings = 32), P2 (2: REST + stream FY25 digests + _PROVIDER_ATTEMPTS contents + transport, R-G3-9), P3 (1) = 35 PIN nodes.

S81-17 (tests/test_s81_s17_kb_ingest.py): RED S1 (2), S2 (1), S3 (12), S4 (2; the closed 2.2 vocabulary, R-G3-6), S5 (1), S6 (4: REST refusal, stream refusal, parse failure, timeout partial; each with a positive control), S7 (2; order recorder moderate < ff:kb_ingest < return / settle_complete, R-G3-10), S8 (2), S9 (2), S10 (1), S11 (4), S12 (10 refusals + 1 allowed), S13 (1), S14 (1 allowed + 3 refusals), S15 (2), S16 (1), S17 (6: per-field rows, needs_operator, CAS wins / CAS lost, GAP_MAX, hygiene in each), S18 (1), S19 (1), S20 (1; elapsed_ms, R-G3-7), S21 (3) = 63 RED nodes; PIN P1 (4 OFF spellings x ENABLE_SYNC_DB_OFFLOAD both ways = 8), P2 (3 literals) = 11 PIN nodes.

Totals: 140 RED nodes (all fail at base on AssertionError), 46 PIN nodes (all green at base).

## 3. Base runs (real worktree, flags unset)

```
# d14_base1.log
[hermeticity] sentinel checked 112 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
77 failed, 35 passed, 11 warnings in 7.25s
# s17_base3.log
[hermeticity] sentinel checked 74 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
63 failed, 11 passed, 11 warnings in 8.31s
# final_base.log
[hermeticity] sentinel checked 186 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
140 failed, 46 passed, 11 warnings in 12.86s
# ci_base.log
[hermeticity] sentinel checked 1758 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
1 failed, 1757 passed, 11 warnings in 33.70s
# secret_scan_base.log
[hermeticity] sentinel checked 31 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
31 passed, 1 warning in 10.32s
```

final_base: 140 failed / 46 passed; every failure an AssertionError (140 / 140 parsed per node, red_node_proof.json); no PIN node failed. CI-order set of 12.2 at base (its 13 existing members, OFF): 1757 passed, 1 failed = tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (a pre-existing box failure: the autocrlf checkout makes data/fragrance_lexicon.json CRLF; it fails identically on the prototype). tests/test_secret_scan_static.py alone at base: 31 passed.

### AssertionError proof per RED node (node -> first E-line type, final_base.log)

```
AssertionError  test_L10_gate_error_is_a_skip
AssertionError  test_L11_log_lines_carry_hosts_and_constants_only
AssertionError  test_L1_readers[health_flush_enabled-ENABLE_LIVE_ROBOTS_HEALTH_FLUSH]
AssertionError  test_L1_readers[live_robots_enabled-ENABLE_LIVE_ROBOTS_REGISTRY]
AssertionError  test_L2_verdict_table[allow]
AssertionError  test_L2_verdict_table[bad_url_ftp]
AssertionError  test_L2_verdict_table[bad_url_no_host]
AssertionError  test_L2_verdict_table[bad_url_non_str]
AssertionError  test_L2_verdict_table[denied_row]
AssertionError  test_L2_verdict_table[denied_url]
AssertionError  test_L2_verdict_table[no_record_empty]
AssertionError  test_L2_verdict_table[no_record_no_origin]
AssertionError  test_L2_verdict_table[no_row]
AssertionError  test_L2_verdict_table[not_live_blocked]
AssertionError  test_L2_verdict_table[not_live_candidate]
AssertionError  test_L2_verdict_table[origin_http]
AssertionError  test_L2_verdict_table[origin_www]
AssertionError  test_L2_verdict_table[robots_challenge_parked]
AssertionError  test_L2_verdict_table[robots_disallow_state]
AssertionError  test_L2_verdict_table[robots_expired]
AssertionError  test_L2_verdict_table[robots_qarenbot_disallows]
AssertionError  test_L2_verdict_table[robots_star_disallows]
AssertionError  test_L2_verdict_table[robots_truncated]
AssertionError  test_L2_verdict_table[robots_unreadable]
AssertionError  test_L2b_parity_with_g2_gate[allow]
AssertionError  test_L2b_parity_with_g2_gate[bad_url_ftp]
AssertionError  test_L2b_parity_with_g2_gate[bad_url_no_host]
AssertionError  test_L2b_parity_with_g2_gate[bad_url_non_str]
AssertionError  test_L2b_parity_with_g2_gate[denied_row]
AssertionError  test_L2b_parity_with_g2_gate[denied_url]
AssertionError  test_L2b_parity_with_g2_gate[no_record_empty]
AssertionError  test_L2b_parity_with_g2_gate[no_record_no_origin]
AssertionError  test_L2b_parity_with_g2_gate[no_row]
AssertionError  test_L2b_parity_with_g2_gate[not_live_blocked]
AssertionError  test_L2b_parity_with_g2_gate[not_live_candidate]
AssertionError  test_L2b_parity_with_g2_gate[origin_http]
AssertionError  test_L2b_parity_with_g2_gate[origin_www]
AssertionError  test_L2b_parity_with_g2_gate[robots_challenge_parked]
AssertionError  test_L2b_parity_with_g2_gate[robots_disallow_state]
AssertionError  test_L2b_parity_with_g2_gate[robots_expired]
AssertionError  test_L2b_parity_with_g2_gate[robots_qarenbot_disallows]
AssertionError  test_L2b_parity_with_g2_gate[robots_star_disallows]
AssertionError  test_L2b_parity_with_g2_gate[robots_truncated]
AssertionError  test_L2b_parity_with_g2_gate[robots_unreadable]
AssertionError  test_L3_failing_refresh_keeps_last_good_until_max_stale
AssertionError  test_L3_no_running_loop_decides_from_memo_and_never_raises
AssertionError  test_L3_records_snapshot_is_age_aware
AssertionError  test_L3_refresh_reads_once_off_loop
AssertionError  test_L4_skip_per_fetcher[algolia_explicit]
AssertionError  test_L4_skip_per_fetcher[algolia_harvest]
AssertionError  test_L4_skip_per_fetcher[curl]
AssertionError  test_L4_skip_per_fetcher[same_site]
AssertionError  test_L4_skip_per_fetcher[same_site_hop]
AssertionError  test_L4_skip_per_fetcher[shopify]
AssertionError  test_L4_skip_per_fetcher[url_base]
AssertionError  test_L4_skip_per_fetcher[url_v2]
AssertionError  test_L4_skip_per_fetcher[url_v2_hop]
AssertionError  test_L4_skip_per_fetcher[woo]
AssertionError  test_L5_allow_passes_byte_identical_args[algolia_explicit]
AssertionError  test_L5_allow_passes_byte_identical_args[algolia_harvest]
AssertionError  test_L5_allow_passes_byte_identical_args[curl]
AssertionError  test_L5_allow_passes_byte_identical_args[same_site]
AssertionError  test_L5_allow_passes_byte_identical_args[shopify]
AssertionError  test_L5_allow_passes_byte_identical_args[url_base]
AssertionError  test_L5_allow_passes_byte_identical_args[url_v2]
AssertionError  test_L5_allow_passes_byte_identical_args[woo]
AssertionError  test_L5_outcomes_counted[200-headers0-ok]
AssertionError  test_L5_outcomes_counted[403-headers2-challenge]
AssertionError  test_L5_outcomes_counted[404-headers1-fail]
AssertionError  test_L6_gate_never_fetches
AssertionError  test_L7_seam_answers_the_record_under_the_flag
AssertionError  test_L8_flush_once_per_compare[rest]
AssertionError  test_L8_flush_once_per_compare[stream]
AssertionError  test_L8_no_pipeline_without_attempts_or_health[health_off]
AssertionError  test_L8_no_pipeline_without_attempts_or_health[nothing_attempted]
AssertionError  test_L9_flush_failure_is_one_warning[rest]
AssertionError  test_L9_flush_failure_is_one_warning[stream]
AssertionError  test_S10_builder_only_writes
AssertionError  test_S11_confidence_gates[high]
AssertionError  test_S11_confidence_gates[low]
AssertionError  test_S11_confidence_gates[medium]
AssertionError  test_S11_confidence_gates[unresolved]
AssertionError  test_S12_offer_allowed
AssertionError  test_S12_offer_refusals[converted_usd]
AssertionError  test_S12_offer_refusals[deny_host]
AssertionError  test_S12_offer_refusals[estimated]
AssertionError  test_S12_offer_refusals[expired_record]
AssertionError  test_S12_offer_refusals[non_registry_host]
AssertionError  test_S12_offer_refusals[origin_mismatch]
AssertionError  test_S12_offer_refusals[region_not_bahrain]
AssertionError  test_S12_offer_refusals[render_tier]
AssertionError  test_S12_offer_refusals[robots_disallow]
AssertionError  test_S12_offer_refusals[row_blocked]
AssertionError  test_S13_re_observation_is_one_update
AssertionError  test_S14_image_allowed
AssertionError  test_S14_image_refusals[deny_host_image]
AssertionError  test_S14_image_refusals[disallow_host]
AssertionError  test_S14_image_refusals[http_image]
AssertionError  test_S15_reviews_channel1_only[jsonld]
AssertionError  test_S15_reviews_channel1_only[provider]
AssertionError  test_S16_no_specs_and_misses_become_gaps
AssertionError  test_S17_existing_gap_compare_and_set[cas_lost]
AssertionError  test_S17_existing_gap_compare_and_set[cas_wins]
AssertionError  test_S17_gap_max_bounds_the_rows
AssertionError  test_S17_gap_needs_operator_on_blocked_host
AssertionError  test_S17_gap_rows_per_unknown_field
AssertionError  test_S18_idempotent
AssertionError  test_S19_job_calls_no_llm_serper_or_fetcher
AssertionError  test_S1_readers[field_status_metadata_enabled-ENABLE_FIELD_STATUS_METADATA]
AssertionError  test_S1_readers[kb_ingest_enabled-ENABLE_KB_INGEST]
AssertionError  test_S20_one_ints_only_log_line
AssertionError  test_S21_ingest_does_not_change_the_body[camera_full]
AssertionError  test_S21_ingest_does_not_change_the_body[rest_full]
AssertionError  test_S21_ingest_does_not_change_the_body[stream_full]
AssertionError  test_S2_field_status_full_product
AssertionError  test_S3_field_status_misses[converted_usd_rung]
AssertionError  test_S3_field_status_misses[derived_rating]
AssertionError  test_S3_field_status_misses[estimated]
AssertionError  test_S3_field_status_misses[no_image]
AssertionError  test_S3_field_status_misses[no_review_count]
AssertionError  test_S3_field_status_misses[no_size]
AssertionError  test_S3_field_status_misses[only_tier3_specs]
AssertionError  test_S3_field_status_misses[placeholder_identity]
AssertionError  test_S3_field_status_misses[platform_rung]
AssertionError  test_S3_field_status_misses[served_from_cache]
AssertionError  test_S3_field_status_misses[tier3_concentration]
AssertionError  test_S3_field_status_misses[unmarked]
AssertionError  test_S4_exposure_rest_and_stream[rest]
AssertionError  test_S4_exposure_rest_and_stream[stream]
AssertionError  test_S5_exposure_camera
AssertionError  test_S6_no_key_off_the_success_exits[rest_parse_fail]
AssertionError  test_S6_no_key_off_the_success_exits[rest_refusal]
AssertionError  test_S6_no_key_off_the_success_exits[rest_timeout_partial]
AssertionError  test_S6_no_key_off_the_success_exits[stream_refusal]
AssertionError  test_S7_one_job_per_compare_after_moderation[rest]
AssertionError  test_S7_one_job_per_compare_after_moderation[stream]
AssertionError  test_S8_job_never_awaited[rest]
AssertionError  test_S8_job_never_awaited[stream]
AssertionError  test_S9_job_failure_never_reaches_the_caller[rest]
AssertionError  test_S9_job_failure_never_reaches_the_caller[stream]
```

## 4. Prototype (scratch worktree C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G3_red/wt, detached at the base sha, no junction; REMOVED and verified gone)

Diff: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G3_red/prototype.diff (the six hooked app files + tests/test_s81_kb_schema.py E1/E2 + the two new modules); files: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G3_red/prototype_files/. Never committed; the real worktree's app/, scripts/, tests/test_s81_kb_schema.py and CLAUDE.md untouched. Text pins: no `robots_registry` text in live_robots.py / kb_ingest.py, no `kb_merchants` text in the hooked fetchers, fetch_page byte-unchanged (hook at the caller).

```
# proto_off2.log
[hermeticity] sentinel checked 186 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
186 passed, 11 warnings in 12.46s
# proto_on1.log
[hermeticity] sentinel checked 186 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
186 passed, 11 warnings in 12.74s
# proto_ci_off.log
[hermeticity] sentinel checked 1758 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
1 failed, 1757 passed, 11 warnings in 34.65s
# proto_ci_on.log
[hermeticity] sentinel checked 1758 test(s)
[netguard] blocked 244 attempt(s) from 235 node(s)
209 failed, 1549 passed, 13 warnings in 43.42s
```

Both RED files: 186 passed OFF (ambient flags unset) and 186 passed with the four flags exported (each row sets its own flags). CI-order existing members on the prototype: OFF 1757 passed / 1 failed (the same r06 box failure as base); ON (four flags exported) 209 failed: test_s80_url_mode_v2.py 180, test_shopify_pdp_json.py 17, test_woocommerce_adapter.py 9, test_algolia_service.py 1, test_s75_fanout_identity.py 1, r06 1 -- EXPECTED by the contract (deviation DV-1).

## 5. Mutation table (byte copies in the scratch worktree, the unit file through pyt.py bound 600, restore + sha256)

| id | mutant | result | killing nodes (first 3) | [pyt] |
|---|---|---|---|---|
| D14-M1 | gate returns True before the flag decision (skip never happens) | KILLED | test_L4_skip_per_fetcher[algolia_explicit], test_L4_skip_per_fetcher[algolia_harvest], test_L4_skip_per_fetcher[curl] | [pyt] tag=g3red-d14-m1 start=2026-11-04 11:36:26 end=2026-11-04 11:36:41 elapsed=15s bound=600s status=FAIL rc=1 |
| D14-M2 | the flag check removed (gate always evaluates; curl hook unguarded) | KILLED | test_P1_flag_off_fetcher_identity[curl-OFF], test_P1_flag_off_fetcher_identity[curl-false], test_P1_flag_off_fetcher_identity[curl-pad0] | [pyt] tag=g3red-d14-m2 start=2026-11-04 11:36:41 end=2026-11-04 11:36:51 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M3 | the rules.star check dropped (the verdict sees star = qarenbot) | KILLED | test_L2_verdict_table[robots_star_disallows], test_L2b_parity_with_g2_gate[robots_star_disallows] | [pyt] tag=g3red-d14-m3 start=2026-11-04 11:36:51 end=2026-11-04 11:37:00 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M4 | the origin comparison removed | KILLED | test_L2_verdict_table[origin_http], test_L2_verdict_table[origin_www], test_L2b_parity_with_g2_gate[origin_http] | [pyt] tag=g3red-d14-m4 start=2026-11-04 11:37:00 end=2026-11-04 11:37:09 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M5 | the expired-record test inverted (in rating_host_allowed, the verdict's expiry rule) | KILLED | test_L2_verdict_table[allow], test_L2_verdict_table[robots_expired] | [pyt] tag=g3red-d14-m5 start=2026-11-04 11:37:10 end=2026-11-04 11:37:19 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M6 | the _fetch_page_v2 hop gate removed (initial only) | KILLED | test_L4_skip_per_fetcher[url_v2_hop] | [pyt] tag=g3red-d14-m6 start=2026-11-04 11:37:19 end=2026-11-04 11:37:28 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M7 | the shopify per-hop gate moved before _hop_is_allowed_async and returns on allow | KILLED | test_L4_skip_per_fetcher[shopify], test_L5_allow_passes_byte_identical_args[shopify] | [pyt] tag=g3red-d14-m7 start=2026-11-04 11:37:29 end=2026-11-04 11:37:38 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M8 | the flush called per fetch instead of per compare | KILLED | test_L8_flush_once_per_compare[rest], test_L8_flush_once_per_compare[stream], test_L8_no_pipeline_without_attempts_or_health[health_off] | [pyt] tag=g3red-d14-m8 start=2026-11-04 11:37:38 end=2026-11-04 11:37:47 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M9 | flush_attempts ignores health_flush_enabled | KILLED | test_L8_no_pipeline_without_attempts_or_health[health_off] | [pyt] tag=g3red-d14-m9 start=2026-11-04 11:37:47 end=2026-11-04 11:37:56 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M10 | robots_entry_lookup ignores the flag | KILLED | test_L7_seam_answers_the_record_under_the_flag | [pyt] tag=g3red-d14-m10 start=2026-11-04 11:37:57 end=2026-11-04 11:38:06 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M11 | the memo select widened to * | KILLED | test_L3_refresh_reads_once_off_loop | [pyt] tag=g3red-d14-m11 start=2026-11-04 11:38:06 end=2026-11-04 11:38:15 elapsed=9s bound=600s status=FAIL rc=1 |
| D14-M12 | the skip log line carries the full URL | KILLED | test_L11_log_lines_carry_hosts_and_constants_only | [pyt] tag=g3red-d14-m12 start=2026-11-04 11:38:15 end=2026-11-04 11:38:24 elapsed=9s bound=600s status=FAIL rc=1 |
| S17-M1 | _kb_ingest_tail called BEFORE the moderation pass (REST) | KILLED | test_S6_no_key_off_the_success_exits[rest_refusal], test_S7_one_job_per_compare_after_moderation[rest] | [pyt] tag=g3red-s17-m1 start=2026-11-04 11:38:24 end=2026-11-04 11:38:34 elapsed=9s bound=600s status=FAIL rc=1 |
| S17-M2 | the stream hook after the settle_complete yield | KILLED | test_S7_one_job_per_compare_after_moderation[stream] | [pyt] tag=g3red-s17-m2 start=2026-11-04 11:38:34 end=2026-11-04 11:38:43 elapsed=9s bound=600s status=FAIL rc=1 |
| S17-M3 | the flag check removed (the job always built and scheduled) | KILLED | test_P1_flag_off_identity[OFF-offload_off], test_P1_flag_off_identity[OFF-offload_on], test_P1_flag_off_identity[false-offload_off] | [pyt] tag=g3red-s17-m3 start=2026-11-04 11:38:43 end=2026-11-04 11:38:51 elapsed=8s bound=600s status=FAIL rc=1 |
| S17-M4 | the job run inline (awaited on the response path) instead of fire-and-forget | KILLED | test_S7_one_job_per_compare_after_moderation[rest], test_S7_one_job_per_compare_after_moderation[stream], test_S8_job_never_awaited[rest] | [pyt] tag=g3red-s17-m4 start=2026-11-04 11:38:51 end=2026-11-04 11:39:15 elapsed=24s bound=600s status=FAIL rc=1 |
| S17-M5 | the cards gate == high widened to high or medium | KILLED | test_S11_confidence_gates[medium] | [pyt] tag=g3red-s17-m5 start=2026-11-04 11:39:15 end=2026-11-04 11:39:24 elapsed=9s bound=600s status=FAIL rc=1 |
| S17-M6 | the robots verdict skipped for offers | KILLED | test_S12_offer_refusals[expired_record], test_S12_offer_refusals[origin_mismatch], test_S12_offer_refusals[robots_disallow] | [pyt] tag=g3red-s17-m6 start=2026-11-04 11:39:25 end=2026-11-04 11:39:34 elapsed=9s bound=600s status=FAIL rc=1 |
| S17-M7 | converted_usd admitted to offers | SURVIVED | - | [pyt] tag=g3red-s17-m7 start=2026-11-04 11:39:34 end=2026-11-04 11:39:42 elapsed=8s bound=600s status=OK rc=0 |
| S17-M8 | the CAS .eq(demand_count, n) dropped | KILLED | test_S17_existing_gap_compare_and_set[cas_lost], test_S17_existing_gap_compare_and_set[cas_wins] | [pyt] tag=g3red-s17-m8 start=2026-11-04 11:39:42 end=2026-11-04 11:39:52 elapsed=9s bound=600s status=FAIL rc=1 |
| S17-M9 | the pdp_ guard dropped and the gap fields renamed into the pdp_ namespace | KILLED | test_S17_existing_gap_compare_and_set[cas_lost], test_S17_existing_gap_compare_and_set[cas_wins], test_S17_gap_max_bounds_the_rows | [pyt] tag=g3red-s17-m9 start=2026-11-04 11:39:52 end=2026-11-04 11:40:01 elapsed=9s bound=600s status=FAIL rc=1 |
| S17-M10 | ignore_duplicates=True dropped (overwrite) | KILLED | test_S10_builder_only_writes, test_S18_idempotent | [pyt] tag=g3red-s17-m10 start=2026-11-04 11:40:01 end=2026-11-04 11:40:10 elapsed=9s bound=600s status=FAIL rc=1 |
| S17-M11 | field_status written with the exposure flag OFF (ingest ON) | KILLED | test_S21_ingest_does_not_change_the_body[camera_full], test_S21_ingest_does_not_change_the_body[rest_full], test_S21_ingest_does_not_change_the_body[stream_full] | [pyt] tag=g3red-s17-m11 start=2026-11-04 11:40:11 end=2026-11-04 11:40:21 elapsed=10s bound=600s status=FAIL rc=1 |
| S17-M12 | kb_specs written from verified LLM specs | KILLED | test_S16_no_specs_and_misses_become_gaps | [pyt] tag=g3red-s17-m12 start=2026-11-04 11:40:24 end=2026-11-04 11:40:43 elapsed=19s bound=600s status=FAIL rc=1 |
| S17-M7b | converted_usd admitted to offers WITH a rung (page_evidence): the builder belt cannot stop it | KILLED | test_S12_offer_refusals[converted_usd] | [pyt] tag=g3red-s17-m7b start=2026-11-04 11:41:16 end=2026-11-04 11:41:25 elapsed=9s bound=600s status=FAIL rc=1 |

All prototype files sha256-equal to the pre-mutation snapshot after the run (proto_sha_before_mut.txt, 0 mismatches); the mutation lock .qa-mutation.lock was created and removed in the scratch worktree.
S17-M7 as written SURVIVED: equivalent in the prototype, because build_offer_row refuses evidence_rung None (rung_for(converted_usd) is None), so the builder belt drops the row; S17-M7b (converted_usd admitted WITH a rung) is KILLED by S12[converted_usd]. A ruling may call M7 equivalent.

## 6. Comm set and the base record at 744616e3 (R-G3-12, LC-6)

Derivation: tools/comm_plan.py re-ran the spec's union rule (module/symbol grep over 17 module names UNION the source-scanning patterns UNION the common-brief pins UNION the CLAUDE.md readers) at base and unioned the spec list: 609 files, 0 added, 0 dropped; sha256 ba26af35866801b40d145a9735a7797b0677efacf71e2154b8bb18b4a70093ec (== g3spec/comm_final2.txt). List: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G3_red/COMM_SET.txt; reasons: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G3_red/comm_reasons.tsv. The four test_precommit_hook*.py excluded; the 4 NETWORK_FLAKY_EXCLUDE nodes deselected where present; the two RED files are not members.

Reuse split: 188 REUSED (90d45c0b/d6b146d5 x60, a513ea3b/aec54326 x88, c6fb6533/3e2570e2 x10, eaccd550/406b86f4 x30), 421 RUN at base in 17 chunks (+ tests/test_secret_scan_static.py alone). Stored: harness/base_records/744616e37d031923e522e30740b687de76482ee9/ba26af35866801b40d145a9735a7797b0677efacf71e2154b8bb18b4a70093ec.{txt,files,pyt.log,header.txt}. FAILED/ERROR node ids in the record: 14.

```
tests/test_auth_interceptor.py::test_sign_in_with_social_exception
tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
```

[pyt] lines (comm chunks + secret scan):

```
2026-11-04 11:46:32 [pyt] tag=g3red-comm-00 start=2026-11-04 11:45:55 end=2026-11-04 11:46:32 elapsed=37s bound=1200s status=FAIL rc=1
2026-11-04 11:47:09 [pyt] tag=g3red-comm-01 start=2026-11-04 11:46:32 end=2026-11-04 11:47:09 elapsed=37s bound=1200s status=OK rc=0
2026-11-04 11:48:05 [pyt] tag=g3red-comm-02 start=2026-11-04 11:47:09 end=2026-11-04 11:48:05 elapsed=56s bound=1200s status=OK rc=0
2026-11-04 11:48:18 [pyt] tag=g3red-comm-03 start=2026-11-04 11:48:05 end=2026-11-04 11:48:18 elapsed=12s bound=1200s status=OK rc=0
2026-11-04 11:48:50 [pyt] tag=g3red-comm-04 start=2026-11-04 11:48:18 end=2026-11-04 11:48:50 elapsed=32s bound=1200s status=OK rc=0
2026-11-04 11:49:20 [pyt] tag=g3red-comm-05 start=2026-11-04 11:48:51 end=2026-11-04 11:49:20 elapsed=29s bound=1200s status=OK rc=0
2026-11-04 11:49:50 [pyt] tag=g3red-comm-06 start=2026-11-04 11:49:20 end=2026-11-04 11:49:50 elapsed=29s bound=1200s status=OK rc=0
2026-11-04 11:50:05 [pyt] tag=g3red-comm-07 start=2026-11-04 11:49:50 end=2026-11-04 11:50:05 elapsed=15s bound=1200s status=OK rc=0
2026-11-04 11:50:34 [pyt] tag=g3red-comm-08 start=2026-11-04 11:50:06 end=2026-11-04 11:50:34 elapsed=28s bound=1200s status=FAIL rc=1
2026-11-04 11:51:07 [pyt] tag=g3red-comm-09 start=2026-11-04 11:50:35 end=2026-11-04 11:51:07 elapsed=32s bound=1200s status=FAIL rc=1
2026-11-04 11:51:24 [pyt] tag=g3red-comm-10 start=2026-11-04 11:51:07 end=2026-11-04 11:51:24 elapsed=17s bound=1200s status=OK rc=0
2026-11-04 11:54:10 [pyt] tag=g3red-comm-11 start=2026-11-04 11:51:24 end=2026-11-04 11:54:10 elapsed=166s bound=1200s status=OK rc=0
2026-11-04 11:55:54 [pyt] tag=g3red-comm-12 start=2026-11-04 11:54:10 end=2026-11-04 11:55:54 elapsed=103s bound=1200s status=FAIL rc=1
2026-11-04 11:56:51 [pyt] tag=g3red-comm-13 start=2026-11-04 11:55:54 end=2026-11-04 11:56:51 elapsed=57s bound=1200s status=OK rc=0
2026-11-04 11:57:35 [pyt] tag=g3red-comm-14 start=2026-11-04 11:56:51 end=2026-11-04 11:57:35 elapsed=43s bound=1200s status=OK rc=0
2026-11-04 11:58:20 [pyt] tag=g3red-comm-15 start=2026-11-04 11:57:35 end=2026-11-04 11:58:20 elapsed=45s bound=1200s status=OK rc=0
2026-11-04 11:58:50 [pyt] tag=g3red-comm-16 start=2026-11-04 11:58:20 end=2026-11-04 11:58:49 elapsed=29s bound=1200s status=OK rc=0
```

## 7. Deviations from the spec / for the gate

- DV-1 (12.2 / R-G3-13 gate definition): the CI-order set "with the four flags ON" cannot be green for the existing fetcher pins: D14 is fail-closed (a cold memo skips every gated fetch, R-W "missing = skip"), so with ENABLE_LIVE_ROBOTS_REGISTRY exported every existing test that fetches through a hooked fetcher without seeding the memo goes red (prototype ON: test_s80_url_mode_v2.py 180, test_shopify_pdp_json.py 17, test_woocommerce_adapter.py 9, test_algolia_service.py 1), and FY25 moves under ENABLE_FIELD_STATUS_METADATA (an additive key, by design). Proposed gate: the existing members OFF only; the two RED files OFF and ON.
- DV-2 (S6 / P2 parse failure): the FY25 "rest_q_parse_fail_shape" query ("just one thing") is NOT a parse failure under the FY25 fake parse (it returns two products, a full success body). The RED file drives the parse-failure exit with a fake parse returning ONE product (the PRODUCT_PARSE_FAILURE_MESSAGE body).
- DV-3 (S6 / P2 hermeticity): the moderation-refusal path fires audit_service.log_content_blocked (a Supabase write, blocked by the netguard sentinel); the RED file patches app.services.audit_service.log_content_blocked with a recorder.
- DV-4 (contract assumptions fixed by the RED file, GREEN must satisfy them): the memo clock is live_robots._monotonic() (seconds) and the verdict clock live_robots._now() (aware datetime); live_robots._admin_client / _redis_client and kb_ingest._admin_client are seams the tests replace with an object that is both the client and callable (either use works); the aggregator is the dict on live_robots._ATTEMPTS_CTX keyed (source, normalized host, outcome) -> int; fetcher labels curl / curl_same_site / shopify / woo / algolia / url_extraction (the V2 path also url_extraction); load_records_sync(client) returns {host: view} and stores the good load; build_job(result, product_data, *, product_categories, region, vision, captured_at) is called directly by the job rows (captured_at an aware datetime) and run_job(snap) reads kb_ingest._admin_client() and live_robots.records_snapshot(); field_status(product_data, result, *, captured_at) without a vision argument reads identity source parse, and the identity item keeps its source (vision / parse) when its state is unknown (S5 asserts vision on both items).
- DV-5 (S3): 12 nodes, not 11: the spec's last case (platform method -> platform_api; converted_usd -> rung None) is split into two nodes.
- DV-6 (L5): the outcome counting (ok / fail / challenge) is pinned on curl_fetch_html only (3 nodes); the spec's 2.3 table does not name an outcome record for the Algolia and URL-mode hooks, so the args-identity half covers all 8 golden fetchers and the outcome half curl only.
- DV-7 (L4): asserts at least one "[LIVE_ROBOTS] skip" INFO line per skip and exactly one robots_skip count for the skipped host with the fetcher label; for the two hop cases the allowed initial URL is fetched once and the skipped hop URL never.
- DV-8 (mutants): D14-M2 is applied at TWO sites (the gate's own flag check AND the curl hook's flag guard): with the hook-site guard in place, removing only the in-gate check is equivalent. D14-M5 is applied to the expiry test in jsonld_widen.rating_host_allowed (the verdict delegates expiry to it; live_robots carries no expiry code of its own). S17-M2's killer is S7 (the order recorder), not S4: the settle_complete event holds the same dict object, so a tail after the yield still shows field_status in the recorded event. S17-M4 is applied as an inline synchronous run_job call (the tail is a sync method; an await is not expressible). S17-M7 as written is equivalent (builder belt); S17-M7b added and killed.
- DV-9 (base noise, this box): the CRLF autocrlf checkout of the real worktree reddens the LF-pinning hygiene rows: tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (data/fragrance_lexicon.json) and the five tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[...] nodes (the G2 scripts read as CRLF); none is a G3 failure; they are in the stored base record so the HEAD comm reads them as baseline. The other 8 record failures are the known box nodes (test_prompt_truth x2 cold tiktoken; test_auth_interceptor x2, test_page_scraping x2, test_personalization_bundle_c x2, all present in earlier stored records).
- DV-10 (reuse rule): the per-file reuse was applied STRICTER than R-G3-12's letter: besides the module-stem rule, a member is re-run when the file itself changed since the record's sha, when it names a changed data / fixture / railway file, when it reads CLAUDE.md (changed since every record), or when it imports app.main / uses TestClient and an app/api or app/middleware file changed since the record (routes are reached without naming them).
- DV-11 (goldens): the two golden JSON files carry sha256 hex digests (and the base sha) that contain digit runs of 8 or more; they are digests, not personal data (the same shape as the S81-10b golden). The Algolia explicit-store header value is recorded as <redacted> (any header name containing "key").

## 8. Open questions

- Q1 (DV-1): rule the GREEN gate for 12.2: existing members OFF only, the RED files OFF and ON?
- Q2: should the Algolia and URL-mode hooks record ok / fail / challenge outcomes (the health counters would then cover them), or only robots_skip as the 2.3 table reads?
- Q3 (S13 / R-G3-11 re-observation): PostgREST returns numeric amount as a number while build_offer_row sends a 3-place string; matching inserted rows back to sent rows must normalise the amount (the prototype uses Decimal.normalize), else every offer is re-updated. GREEN should state its matching rule.
- Q4: S17-M7 as written is equivalent through the builder belt (evidence_rung None is refused); is the belt accepted as the converted_usd guard, or must the job also refuse converted_usd explicitly (the spec's text; the prototype does both)?

## 9. Restore check

- git rev-parse HEAD: 744616e37d031923e522e30740b687de76482ee9
- git status --short (only the four new untracked files):
    ?? tests/fixtures/s81_d14_flag_off_golden.json
    ?? tests/fixtures/s81_s17_flag_off_golden.json
    ?? tests/test_s81_d14_live_robots.py
    ?? tests/test_s81_s17_kb_ingest.py
- git diff --stat against HEAD (tracked files): '' (empty = every tracked file equals the base)
- tracked-file hash check: git diff --quiet exit 0 (0 = no tracked change)
- scratch worktree: git worktree list entries under S81-G3_red = 0; directory present = 0

Not run by this agent (by the brief): the corpus gate (spec base SHA 601338261705718a85c8c4ff281cefd47368a8c7aa1b12c2aad501baae18a1ef stands), the fourteen client fences.
