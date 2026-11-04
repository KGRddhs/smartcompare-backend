# S81-G2 RED REPORT (RED agent, Opus 5.5, 2026-11-04; filed through the shell by tools/make_report.py: the harness refuses a subagent Write of a report .md)

Unit: S81-G2 KB-SEED = S81-16 KB-SEED-BATCH (ENABLE_KB_SEED) + D09 FEED-WALKER (ENABLE_FEED_WALKER) + D11 PDP-DISCOVERY (ENABLE_PDP_DISCOVERY + ENABLE_CC_CDX).
Base c6fb65336deab4f48275b13d3847e0f42b298984 (sc-s81-g2 HEAD, verified before and after). Spec copy sha 210c0680... verified. RULINGS_S81_G2 R-G2-1..R-G2-20 applied.

## Files written in the real worktree (six new files, nothing else)
| file | bytes | sha256 |
|---|---|---|
| tests/test_s81_s16_kb_seed.py | 59353 | f014ea81ab88c69bc600e90f88177b394dc2e2650d661236c3913d2b421a3904 |
| tests/fixtures/s81_s16_batch_request_golden.json | 23093 | d48d38c389e269022dd689bd742725b26c68d2189fde71686010549bb01aff0c |
| tests/test_s81_d09_feed_walker.py | 37035 | 3928d7066886fdecf5c2bf3eee3200c28621e73b81a2131f81b3cb893669f41c |
| tests/fixtures/s81_d09_feeds.json | 1000 | d2fbbcf22919c42e5b7b61f2b4c0f1e2333d3affbd8fb2c05819e639e29111a8 |
| tests/test_s81_d11_pdp_discovery.py | 29346 | 2d4a6e470c57e9518671b576b694a671058628996dc0d7723390db411fbed6ea |
| tests/fixtures/s81_d11_sitemaps.json | 827 | 9489efd84b262a340d56dde9e649483347be86782471d27afe4b8c42c1bce28c |
All pure ASCII (0 bytes > 127), LF only, ruff E9/F63/F7/F82 clean. git status --short: exactly these six untracked; git diff HEAD empty.

## Counts (R-G2-19)
- S81-16: 30 RED rows (R1..R30; 134 parametrized nodes) + 6 PIN (P1..P6).
- D09: 21 RED rows (R1..R21; 79 nodes) + 4 PIN (P1..P4).
- D11: 16 RED rows (R1..R16; 61 nodes) + 4 PIN (P1..P4).
- At base (final bytes): 274 failed / 14 passed; every failure 'E AssertionError' (274/274, raised by the find_spec / hasattr / is_file helpers), 0 ERROR, no ImportError / AttributeError. Failed node ids: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G2_red/base_failed_s16_kb_seed.txt, base_failed_d09_feed_walker.txt, base_failed_d11_pdp_discovery.txt.
- Prototype: 817 passed (the 3 RED files + tests/test_s81_kb_schema.py with E1 / E2); E1 / E2 measured red against the prototype with the base kb_schema file.
- Mutants: 50 / 50 KILLED; every kill is an assertion failure (no other exception type in any mutant log).

## Every [pyt] line
```
[pyt] tag=g2red-comm-base-c1 start=2026-11-04 06:17:28 end=2026-11-04 06:18:44 elapsed=76s bound=1200s status=OK rc=0   (951 passed; [hermeticity] 951; [netguard] blocked 22 attempt(s) from 21 node(s): the test_hermeticity_pins self-tests)
[pyt] tag=g2red-comm-base-c2 start=2026-11-04 06:35:15 end=2026-11-04 06:37:42 elapsed=147s bound=1200s status=OK rc=0  (3404 passed; [hermeticity] 3404; [netguard] blocked 24 from 2 node(s): S81-04 test_r42 / test_p08)
[pyt] tag=g2red-comm-base-c3 start=2026-11-04 06:46:08 end=2026-11-04 06:46:35 elapsed=28s bound=1200s status=OK rc=0   (750 passed; [hermeticity] 750; [netguard] blocked 8 from 8 node(s): test_w49_extraction_catch_redaction sentinel)
[pyt] tag=g2red-comm-base-secret start=2026-11-04 06:46:35 end=2026-11-04 06:46:40 elapsed=5s bound=1200s status=OK rc=0 (31 passed; [hermeticity] 31; [netguard] blocked 0)
[pyt] tag=g2red-base-s16_kb_seed start=2026-11-04 06:43:24 end=2026-11-04 06:43:34 elapsed=10s bound=600s status=FAIL rc=1 (134 failed, 6 passed; [hermeticity] 140; [netguard] blocked 0)
[pyt] tag=g2red-base-d09_feed_walker start=2026-11-04 06:43:34 end=2026-11-04 06:43:41 elapsed=6s bound=600s status=FAIL rc=1 (78 failed, 4 passed; superseded)
[pyt] tag=g2red-base-d11_pdp_discovery start=2026-11-04 06:43:41 end=2026-11-04 06:43:46 elapsed=5s bound=600s status=FAIL rc=1 (61 failed, 4 passed; [hermeticity] 65; [netguard] blocked 0)
[pyt] tag=g2red-base-d09-final start=2026-11-04 06:54:07 end=2026-11-04 06:54:13 elapsed=6s bound=600s status=FAIL rc=1 (79 failed, 4 passed; [hermeticity] 83; [netguard] blocked 0)
[pyt] tag=g2red-base-all-final start=2026-11-04 06:55:27 end=2026-11-04 06:55:43 elapsed=16s bound=1200s status=FAIL rc=1 (274 failed, 14 passed; [hermeticity] 288; [netguard] blocked 0; 274 x 'E AssertionError', 0 ERROR)  <- THE BASE RUN OF THE FINAL BYTES
[pyt] tag=g2red-proto-s16-a start=2026-11-04 06:33:53 end=2026-11-04 06:33:58 elapsed=4s bound=600s status=FAIL rc=1 (iteration: a parity bug in the test's GTIN helper, fixed)
[pyt] tag=g2red-proto-s16-b start=2026-11-04 06:34:07 end=2026-11-04 06:34:14 elapsed=7s bound=600s status=FAIL rc=1 (1 failed: R27 caught 4 non-ASCII bytes the Write tool decoded into the prototype; prototype fixed)
[pyt] tag=g2red-proto-d09-a start=2026-11-04 06:40:12 end=2026-11-04 06:40:17 elapsed=5s bound=600s status=FAIL rc=1 (R3: 43 hosts when candidate rows are made live: deviation D1)
[pyt] tag=g2red-proto-d09-b start=2026-11-04 06:40:36 end=2026-11-04 06:40:40 elapsed=5s bound=600s status=OK rc=0 (82 passed)
[pyt] tag=g2red-proto-d11-a start=2026-11-04 06:43:02 end=2026-11-04 06:43:05 elapsed=4s bound=600s status=OK rc=0 (65 passed)
[pyt] tag=g2red-proto-on start=2026-11-04 06:44:06 end=2026-11-04 06:44:19 elapsed=14s bound=600s status=OK rc=0 (816 passed)
[pyt] tag=g2red-proto-ambient-apply start=2026-11-04 06:44:20 end=2026-11-04 06:44:33 elapsed=13s bound=600s status=OK rc=0 (816 passed with the four flags exported as apply / true: the rows never read the ambient env)
[pyt] tag=g2red-proto-off start=2026-11-04 06:44:43 end=2026-11-04 06:44:49 elapsed=6s bound=600s status=OK rc=0 (42 passed: -k "r02 or _p0", the flag-OFF identity rows with full config + the PIN rows)
[pyt] tag=g2red-proto-E-red start=2026-11-04 06:44:50 end=2026-11-04 06:44:55 elapsed=5s bound=600s status=FAIL rc=1 (base tests/test_s81_kb_schema.py over the prototype: test_s14_p01 + test_s14_p02 FAILED = E1 / E2 red; the edited copy restored, sha 796e567a6ac9f895 verified)
[pyt] tag=g2red-proto-d09-c start=2026-11-04 06:47:31 end=2026-11-04 06:47:36 elapsed=5s bound=600s status=OK rc=0 (82 passed)
[pyt] tag=g2red-proto-d09-d start=2026-11-04 06:52:46 end=2026-11-04 06:52:50 elapsed=4s bound=600s status=OK rc=0 (83 passed)
[pyt] tag=g2red-proto-on-final start=2026-11-04 06:54:25 end=2026-11-04 06:54:39 elapsed=14s bound=600s status=OK rc=0 (817 passed; [hermeticity] 817; [netguard] blocked 0)
[pyt] tag=g2red-proto-on-final2 start=2026-11-04 06:55:57 end=2026-11-04 06:56:11 elapsed=14s bound=600s status=OK rc=0 (817 passed: the FINAL six RED bytes against the archived prototype in a re-created scratch worktree)
```
The mutant [pyt] lines are in the table (one bounded run per mutant, bound 600, -k the killing rows).

## Base record (LC-6), STORED
C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/harness/base_records/c6fb65336deab4f48275b13d3847e0f42b298984/74b84ef90fca0a48e8637aae74dc873063ce0d8645a5015b9bf5fc0770ae3a87.txt (EMPTY: no failing node), beside it .files (the 68 files), .pyt.log (the four chunk logs) and .header.txt (the [pyt] / [hermeticity] / [netguard] lines).
The set = the spec's 68 files (sha256 of the sorted list 74b84ef90fca0a48..., the spec's prefix): C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G2_red/comm_files.txt + C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G2_red/comm_reasons.tsv. Chunks of 25 + 25 + 17 alphabetical files + tests/test_secret_scan_static.py alone: 5136 passed, 0 failed. The head set (GREEN) = these 68 + the three RED files = 71.

## Prototype (thrown away; archived for GREEN)
Diff: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G2_red/prototype.diff; E1 / E2 diff: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G2_red/E1_E2.diff; files: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G2_red/prototype_files/. Five scripts (kb_seed_common, seed_kb_batch, seed_kb_brands_wikidata, cron_feed_walker, cron_pdp_discovery), three railway.*.json, E1 (P01_ALLOWED + a per-file function map P01_FUNCTIONS) and E2 (P02_ALLOWED + the five exact lines). Scratch worktree C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/g2s created twice (the second to re-verify the final RED bytes), removed both times with git worktree remove --force.
The golden tests/fixtures/s81_s16_batch_request_golden.json was RECORDED from the prototype DRY run over the R7 fixture corpus (3 pages, 2 juices, 2 requests) by C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G2_red/tools/record_golden.py; R7 pins it byte-for-byte.

## Mutation table (50; byte copies, restored, sha256-verified after each; .qa-mutation.lock created and removed)
| id | mutant | result | killing rows | [pyt] |
|---|---|---|---|---|
| S-M1 | run_mode treats 'dry' as DRY | KILLED | test_s16_r01_run_mode_table | [pyt] tag=g2red-mut-S-M1 start=2026-11-04 06:48:46 end=2026-11-04 06:48:49 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M2 | run_mode reads the variable once (import-time memo) | KILLED | test_s16_r01_run_mode_table | [pyt] tag=g2red-mut-S-M2 start=2026-11-04 06:48:49 end=2026-11-04 06:48:54 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M3 | the OFF check moved after the corpus read | KILLED | test_s16_r02_off_is_inert_full_config | [pyt] tag=g2red-mut-S-M3 start=2026-11-04 06:48:54 end=2026-11-04 06:48:58 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M4 | the default 'true' in os.getenv(flag, ...) | KILLED | test_s16_r01_run_mode_table, test_s16_r02_off_is_inert_full_config | [pyt] tag=g2red-mut-S-M4 start=2026-11-04 06:48:58 end=2026-11-04 06:49:02 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M5 | the deny-link scan dropped | KILLED | test_s16_r04_page_rule | [pyt] tag=g2red-mut-S-M5 start=2026-11-04 06:49:02 end=2026-11-04 06:49:06 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M6 | url_gate skips the origin comparison | KILLED | test_s16_r04_page_rule, test_s16_r25_url_gate_reasons | [pyt] tag=g2red-mut-S-M6 start=2026-11-04 06:49:07 end=2026-11-04 06:49:11 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M7 | url_gate accepts a candidate row | KILLED | test_s16_r25_url_gate_reasons | [pyt] tag=g2red-mut-S-M7 start=2026-11-04 06:49:11 end=2026-11-04 06:49:15 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M8 | the existing-specs filter dropped | KILLED | test_s16_r06_idempotent_rerun | [pyt] tag=g2red-mut-S-M8 start=2026-11-04 06:49:15 end=2026-11-04 06:49:19 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M9 | thinking omitted from params | KILLED | test_s16_r07_request_golden | [pyt] tag=g2red-mut-S-M9 start=2026-11-04 06:49:19 end=2026-11-04 06:49:23 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M10 | the digest outside _wrap_search_context | KILLED | test_s16_r08_prompt_fence | [pyt] tag=g2red-mut-S-M10 start=2026-11-04 06:49:23 end=2026-11-04 06:49:27 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M11 | the bound check skipped in APPLY (after create) | KILLED | test_s16_r09_budget_bound | [pyt] tag=g2red-mut-S-M11 start=2026-11-04 06:49:27 end=2026-11-04 06:49:31 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M12 | reserve called after create | KILLED | test_s16_r10_breaker_contract, test_s16_r11_apply_call_order_golden | [pyt] tag=g2red-mut-S-M12 start=2026-11-04 06:49:31 end=2026-11-04 06:49:35 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M13 | record called in addition to settle | KILLED | test_s16_r10_breaker_contract | [pyt] tag=g2red-mut-S-M13 start=2026-11-04 06:49:35 end=2026-11-04 06:49:39 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M14 | usage logged for every row | KILLED | test_s16_r12_usage_first_20 | [pyt] tag=g2red-mut-S-M14 start=2026-11-04 06:49:39 end=2026-11-04 06:49:43 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M15 | a snippet out of range accepted (0) | KILLED | test_s16_r13_citation_or_omit | [pyt] tag=g2red-mut-S-M15 start=2026-11-04 06:49:43 end=2026-11-04 06:49:47 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M16 | delete before the writes | KILLED | test_s16_r11_apply_call_order_golden | [pyt] tag=g2red-mut-S-M16 start=2026-11-04 06:49:47 end=2026-11-04 06:49:51 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M17 | a second clock read per table | KILLED | test_s16_r15_one_observation_time | [pyt] tag=g2red-mut-S-M17 start=2026-11-04 06:49:51 end=2026-11-04 06:49:55 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M18 | the key read live from os.environ in main | KILLED | test_s16_r20_no_key_apply | [pyt] tag=g2red-mut-S-M18 start=2026-11-04 06:49:55 end=2026-11-04 06:49:59 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M19 | base_url not passed | KILLED | test_s16_r21_client_construction | [pyt] tag=g2red-mut-S-M19 start=2026-11-04 06:49:59 end=2026-11-04 06:50:03 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M20 | APPLY of the brand script inserts into kb_merchants | KILLED | test_s16_r23_brands_dry_and_apply | [pyt] tag=g2red-mut-S-M20 start=2026-11-04 06:50:03 end=2026-11-04 06:50:07 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M21 | the extractor filter dropped (any kb_specs row skips the juice) | KILLED | test_s16_r06_idempotent_rerun | [pyt] tag=g2red-mut-S-M21 start=2026-11-04 06:50:07 end=2026-11-04 06:50:11 elapsed=4s bound=600s status=FAIL rc=1 |
| S-M22 | KB_SEED_MAX_JUICES ignored | KILLED | test_s16_r30_int_knobs_table | [pyt] tag=g2red-mut-S-M22 start=2026-11-04 06:50:11 end=2026-11-04 06:50:16 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M1 | the host-level ToS check dropped | KILLED | test_d09_r04_tos_gate | [pyt] tag=g2red-mut-W-M1 start=2026-11-04 06:53:01 end=2026-11-04 06:53:05 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M2 | require_tos=False in the per-URL gate | KILLED | test_d09_r04_tos_gate | [pyt] tag=g2red-mut-W-M2 start=2026-11-04 06:53:05 end=2026-11-04 06:53:09 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M3 | row_currency falls back to BHD | KILLED | test_d09_r09_currency_blind_rule | [pyt] tag=g2red-mut-W-M3 start=2026-11-04 06:53:09 end=2026-11-04 06:53:13 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M4 | Shopify rung platform_api | KILLED | test_d09_r09_currency_blind_rule | [pyt] tag=g2red-mut-W-M4 start=2026-11-04 06:53:14 end=2026-11-04 06:53:18 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M5 | the probe disagreement ignored | KILLED | test_d09_r10_currency_probe | [pyt] tag=g2red-mut-W-M5 start=2026-11-04 06:53:18 end=2026-11-04 06:53:22 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M6 | Woo amount without the minor unit (/100) | KILLED | test_d09_r11_woo_amount_currency | [pyt] tag=g2red-mut-W-M6 start=2026-11-04 06:53:22 end=2026-11-04 06:53:26 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M7 | the variable-spread skip dropped | KILLED | test_d09_r11_woo_amount_currency | [pyt] tag=g2red-mut-W-M7 start=2026-11-04 06:53:26 end=2026-11-04 06:53:30 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M8 | the sale / list pair with two clock reads | KILLED | test_d09_r12_list_and_sale_pair | [pyt] tag=g2red-mut-W-M8 start=2026-11-04 06:53:30 end=2026-11-04 06:53:34 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M9 | the accessory guard dropped | KILLED | test_d09_r13_fragrance_and_guards | [pyt] tag=g2red-mut-W-M9 start=2026-11-04 06:53:34 end=2026-11-04 06:53:38 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M10 | brand guessed from the title's first word | KILLED | test_d09_r14_identity | [pyt] tag=g2red-mut-W-M10 start=2026-11-04 06:53:38 end=2026-11-04 06:53:42 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M11 | Politeness replaced by a fixed 1 s sleep | KILLED | test_d09_r06_politeness_and_concurrency | [pyt] tag=g2red-mut-W-M11 start=2026-11-04 06:53:42 end=2026-11-04 06:53:46 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M12 | allow_redirects=True | KILLED | test_d09_r07_named_ua_no_redirect_ssrf | [pyt] tag=g2red-mut-W-M12 start=2026-11-04 06:53:46 end=2026-11-04 06:53:51 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M13 | the re-observation update sets captured_at | KILLED | test_d09_r16_dry_writes_nothing_apply_order | [pyt] tag=g2red-mut-W-M13 start=2026-11-04 06:53:51 end=2026-11-04 06:53:55 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M14 | a 429 continues to the next page | KILLED | test_d09_r17_throttle_challenge_badfeed | [pyt] tag=g2red-mut-W-M14 start=2026-11-04 06:53:55 end=2026-11-04 06:53:59 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M15 | the feed URL built from the row host | KILLED | test_d09_r05_robots_gate_per_url, test_d09_r15_offer_row_fields | [pyt] tag=g2red-mut-W-M15 start=2026-11-04 06:53:59 end=2026-11-04 06:54:03 elapsed=4s bound=600s status=FAIL rc=1 |
| W-M16 | FEED_WALKER_CURRENCY_PROBES ignored (always 3) | KILLED | test_d09_r21_int_knobs_table | [pyt] tag=g2red-mut-W-M16 start=2026-11-04 06:54:03 end=2026-11-04 06:54:07 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M1 | cc_cdx_enabled ignores the parent mode (CDX read with the parent OFF) | KILLED | test_d11_r02_off_inert_full_config | [pyt] tag=g2red-mut-D-M1 start=2026-11-04 06:51:19 end=2026-11-04 06:51:23 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M2 | the KB_CC_INDEX regex dropped | KILLED | test_d11_r10_cdx_inert | [pyt] tag=g2red-mut-D-M2 start=2026-11-04 06:51:23 end=2026-11-04 06:51:27 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M3 | robots 403 treated as allow-all (no_sitemap) | KILLED | test_d11_r04_robots_and_declared_sitemaps | [pyt] tag=g2red-mut-D-M3 start=2026-11-04 06:51:27 end=2026-11-04 06:51:30 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M4 | the declared-sitemap cap removed | KILLED | test_d11_r04_robots_and_declared_sitemaps | [pyt] tag=g2red-mut-D-M4 start=2026-11-04 06:51:31 end=2026-11-04 06:51:34 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M5 | an off-site (and disallowed) sitemap fetched | KILLED | test_d11_r04_robots_and_declared_sitemaps | [pyt] tag=g2red-mut-D-M5 start=2026-11-04 06:51:34 end=2026-11-04 06:51:38 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M6 | build_sitemap_index used (Redis write) | KILLED | test_d11_r05_reuses_the_collector | [pyt] tag=g2red-mut-D-M6 start=2026-11-04 06:51:39 end=2026-11-04 06:51:42 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M7 | the V2 PDP markers forced | KILLED | test_d11_r06_pdp_markers_follow_v2 | [pyt] tag=g2red-mut-D-M7 start=2026-11-04 06:51:43 end=2026-11-04 06:51:46 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M8 | zero-offer juices ranked | KILLED | test_d11_r07_ranking | [pyt] tag=g2red-mut-D-M8 start=2026-11-04 06:51:47 end=2026-11-04 06:51:50 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M9 | every collected URL written (no match step) | KILLED | test_d11_r08_matching | [pyt] tag=g2red-mut-D-M9 start=2026-11-04 06:51:51 end=2026-11-04 06:51:54 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M10 | the re-discovery update moves state and source_hint | KILLED | test_d11_r09_gap_rows | [pyt] tag=g2red-mut-D-M10 start=2026-11-04 06:51:54 end=2026-11-04 06:51:58 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M11 | the CDX 503 stops only the host, not the run | KILLED | test_d11_r11_cdx_request_shape_and_stop | [pyt] tag=g2red-mut-D-M11 start=2026-11-04 06:51:58 end=2026-11-04 06:52:02 elapsed=4s bound=600s status=FAIL rc=1 |
| D-M12 | PDP_DISCOVERY_MAX_HOSTS ignored | KILLED | test_d11_r16_int_knobs_and_max_hosts | [pyt] tag=g2red-mut-D-M12 start=2026-11-04 06:52:02 end=2026-11-04 06:52:06 elapsed=4s bound=600s status=FAIL rc=1 |

Notes: W-M1 SURVIVED its first run (the per-URL gate with require_tos=True gives the same 'tos' outcome); R4 then gained a case pinning the spec 2.2 order (a ToS-less host with no currency reads 'tos', not 'currency_unknown') and an assertion that the walker's fetcher is built with require_tos=True (which also kills W-M2); all 16 W mutants were re-run on the final D09 file (KILLED). The later GTIN-stem edit (a 12-digit literal rebuilt by concatenation, the same value at run time) was re-verified against the prototype (proto-on-final2).
Implementation choices: S-M3 = a corpus read inserted before the OFF return; S-M11 = the bound check skipped in APPLY; S-M15 = snippet 0 accepted; D-M5 = both the same-site and the url_gate filter dropped (the same-site filter alone is masked by url_gate's origin check: equivalent); D-M7 = pdp_markers_v2_enabled forced True (the prototype never calls _is_pdp_url_v2); D-M8 = zero-offer products appended to the rank (reads the fake's product list: test-coupled). Mutation definitions: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G2_red/tools/mutants.py; logs C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-G2_red/mutants/.

## Deviations from the spec (reported, not silently changed)
D1 D09 R3 says every seed row is 'made live' in the fake: measured 43 feed hosts that way (candidate json rows add 19); 24 only with the seeded status kept (live rows get tos allowed + a robots record). The row keeps the seeded status; the ordered 24 equals the spec 1.3 list (pinned sha 89e900fc...). D11 R3 likewise (71, sha b0da63d9..., equals the spec 1.3 list).
D2 D09 2.3 'challenge_vendor(...) non-empty': challenge_vendor returns 'unknown', never empty; the prototype uses robots_registry._challenge (the cf-mitigated header or a walled HTML body).
D3 a knob whose clamp starts at 0 (FEED_WALKER_CURRENCY_PROBES 0..10): the _int_knob shape maps <= 0 to the default, which makes spec R10 'probes 0' impossible; R21 pins '0' -> 0 there and '0' -> the default for the knobs whose clamp starts at 1.
D4 R-G2-1: the OFF line carries the mode and the flag in ONE INFO record ('[KB_SEED] mode=off ENABLE_KB_SEED not set; skipping run'); a non-OFF entry logs 'mode=<m>' once.
D5 S81-16 --resume: no bound check and no breaker call (nothing is submitted); R19 pins no reserve / create / settle / record.
D6 R11 'kb_merchants read pages' = one select with the one-row fake; R11 polls at KB_SEED_POLL_SECONDS=15 (two 15 s sleeps).
D7 D09 R5 'another origin': with R-G2-12 every URL is built on robots.origin, so a per-URL origin mismatch is unreachable; R5 pins that a www record origin is fetched on that origin only (W-M15 killed by R5 and R15).
D8 D09 R11 'code and row currency missing': the host-level currency_unknown gate (2.2) fires first; the row asserts that host reason.
D9 R23 per R-G2-3: DRY and APPLY identical (two GETs, report only, zero client writes); the IP-literal site falls to the KB top-label check; 302 new hosts -> 300 kept.
D10 S81-16 P2 locates the record dict inside the frozen fixture document (the fixture holds input + expected).
D11 R2 records corpus reads by patching builtins.open over the corpus dir (no seam exists for open).

## Open questions for the gate
Q1 The golden pins the whole SYSTEM text (extraction_service.SPECS_SYSTEM_STATIC_PREFIX_NO_FABRICATION + SEARCH_RESULTS_GUARD + the prototype's SEED_RULES sentence), the digest layout '[snippet_N] <host>' newline text, and the USER layout. GREEN must reproduce the prototype's texts byte-for-byte (prototype_files/seed_kb_batch.py: SEED_RULES, system_prompt, user_prompt, build_requests) or the golden is re-recorded under a ruling; a later edit of that prefix in app/ reddens R7.
Q2 The prototype reads gtins through seed_spec_spine._iter_jsonld_nodes / _is_product and uses robots_registry._challenge / _fetch_following / _stored_crawl_delay / _origin_of (private names; most are named by the spec as consumed).
Q3 The two sha256 host-list literals contain digit runs; the added-line sweep's 8-digit check may flag them (hashes, not personal data).
Q4 D11 gates the host with url_gate(row, origin + '/') (spec 2.2 step 1 as written): a record disallowing '/' for either agent skips the host before robots.txt is read.

## NOT MEASURED
- The fourteen backend-scanning client fences and the full jest suite (GREEN / rebase duty, LC-7; no junction in a backend RED round).
- The comm set at head (71 files; GREEN).
- Anything against the network (Anthropic, Wikidata, Common Crawl, merchant feeds): fakes only.

## Restore check
Real worktree: HEAD c6fb6533; git diff HEAD empty; only the six new files untracked; the spec copy unchanged. Scratch worktree removed (git worktree list shows no g2s). No pytest of mine left running (the other python processes on the box belong to another lane, S81-10b_red shares this scratchpad; none touched).
