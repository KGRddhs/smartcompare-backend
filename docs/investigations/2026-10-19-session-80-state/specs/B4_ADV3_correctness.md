# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- round-3 ADVERSARY, correctness lens (2026-10-22)

Verdict: **SOUND** (blocking 0, MAJOR 0, minor 6: two NEW (c-m1 the meta title is the first TRUTHY of og:title / `<title>`, so an og:title equal to the site name or a placeholder shadows a usable `<title>` and a node-less PDP is refused `no_product_node` at $0 where flag OFF delivers; c-m2 limit (11) understates the same_url over-refusal class) plus the re-verifier's m1-m4, all four CONFIRMED and m3 / m4 EXTENDED; the A3-1 known gap recorded with a measured extension (Zen Cart's default PDP url is refused `homepage` at $0); 61 mutants, 60 KILLED, 1 SURVIVED = the A3-1 shape; flag-OFF differential 44 / 44 byte-identical base vs head; R-A3 holds on all 22 flag-ON exits measured).

- Unit B4, worktree `C:/Users/SynAckITPC/Documents/AI/sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, HEAD verified `0aac07f1f7304e61fa5cac86935c9306f08605d0` at 19:05 AST (start) and again at the end; `git status --short` empty at start and end; no `.qa-mutation.lock`; the worktree was never edited (runs there with PYTHONDONTWRITEBYTECODE=1).
- Agent model: claude-opus-5-5 (this agent's system prompt).
- Read: s81-common.txt (start and again before reporting), PLAN_S80.md sections 0-1, RULINGS_BATCH1.md (B4 section), GATE_B4.md, RULINGS_FIX2_B4.md, RULINGS_FIX3_B4.md (incl. the addendum A3-1..A3-4), B4_FIX3_REPORT.md, B4_FIX3_REVERIFY.md, the spec's mutation table (B4_UNIT_SPEC.md section 6), PR_BODY.md (sha256 `ddb74874...f98a`), the CLAUDE.md B4 header + row (lines 474-475), the full `81df2b64..0aac07f1` diff of `url_routes.py`, `error_handler.py`, `url_extraction_service.py` and the RED file harness. Not opened: RULINGS_R0.md in full (only the B4 lines), B4_SPEC_REVIEW.md, the GREEN / FIX1 / FIX2 reports.
- Scratch worktrees (both under my notes folder, no node_modules): `<scratchpad>/B4_adv2_correctness` (detached `0aac07f1`; the LF RED file copied byte-exact over the autocrlf checkout) and `<scratchpad>/B4_adv2_base` (detached `81df2b64`, for the flag-OFF differential). sha256 of the mutated / support files equal to the unit worktree before the first mutant and after the last (section 2). Both removed at the end (`git worktree list` checked).
- No .env read, copied or printed; no flag set outside one runner call; no network (every netguard line below reads `blocked 0` or names baseline nodes only). Read-only reads of the held corpora `sc-scraper-proof/_proof/{html,global/html,global/corpus.json,sweep2_curl_cffi.jsonl}` (zero-network files; nothing written there).

## 1. RED file and code re-hash

`tests/test_s80_url_mode_v2.py` = `bac8730196c75769e672646e6f1dee7901bfb3fb275af1d84af6a9d97517f1d9` (unit worktree bytes = the scratch copy), 408 nodes. Unit worktree code: `app/services/url_extraction_service.py` `b0d7b8d96aec34352dccdf008d29ddb60fdd03779cb28cc19cfddcf29cc49f68`, `app/api/url_routes.py` `9229e0b4d027e392f21e5da9edb29549f40fcde2bb22ca90c4351701ab3a59ba`, `app/middleware/error_handler.py` `7e539cc7b17fcc6c9b982a2ebe4b212096af57deb8c1bded330eb57e5fc6d482`; the scratch copies hashed equal before the first mutant and after the last (every restore sha-verified by the harness; final re-hash before removal: `b0d7b8d9...`, `9229e0b4...`, `7e539cc7...`, `bac87301...`).

## 2. Runs (every pytest through pyt.py, one at a time, my runs never overlapped each other)

```
unit flag unset (unit worktree): 408 passed, 11 warnings in 8.01s; [hermeticity] sentinel checked 408 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4adv3c-unit-off start=2026-10-22 19:13:44 end=2026-10-22 19:13:53 elapsed=9s bound=600s status=OK rc=0
unit ENABLE_URL_MODE_V2=true (unit worktree): 408 passed, 11 warnings in 7.90s; sentinel 408; netguard 0
[pyt] tag=b4adv3c-unit-on start=2026-10-22 19:13:54 end=2026-10-22 19:14:03 elapsed=9s bound=600s status=OK rc=0
probe 1 (scratch; meta-title class, amazon/noon, generic query pairs, Zen Cart): 4 passed; sentinel 4; netguard 0
[pyt] tag=b4adv3c-probe1 start=2026-10-22 19:14:14 end=2026-10-22 19:14:18 elapsed=4s bound=600s status=OK rc=0
fixture scan (162 held fixture pages): 1 passed; sentinel 1; netguard 0
[pyt] tag=b4adv3c-scan start=2026-10-22 19:15:40 end=2026-10-22 19:15:46 elapsed=7s bound=600s status=OK rc=0
Gulf corpus scan (92 pages): OK
[pyt] tag=b4adv3c-scan-html start=2026-10-22 19:16:26 end=2026-10-22 19:16:52 elapsed=25s bound=600s status=OK rc=0
global corpus scan, one call (429 pages): FAIL = pytest-timeout's 120 s PER-TEST limit inside one scan node (not a [pyt] TIMEOUT, not a product failure); re-run split in three slices:
[pyt] tag=b4adv3c-scan-global_html start=2026-10-22 19:16:53 end=2026-10-22 19:18:58 elapsed=125s bound=600s status=FAIL rc=1
[pyt] tag=b4adv3c-scan-g_0 start=2026-10-22 19:19:46 end=2026-10-22 19:20:38 elapsed=52s bound=600s status=OK rc=0
[pyt] tag=b4adv3c-scan-g_170 start=2026-10-22 19:20:40 end=2026-10-22 19:21:43 elapsed=63s bound=600s status=OK rc=0
[pyt] tag=b4adv3c-scan-g_340 start=2026-10-22 19:21:44 end=2026-10-22 19:22:18 elapsed=35s bound=600s status=OK rc=0
61 mutants (section 3): one [pyt] line each, 19:27:15-19:43:38, every one bound=600s; table below
probe 2 (scratch; pre-gate over 707 held urls, challenge timing, classify edges): 3 passed; sentinel 3; netguard 0
[pyt] tag=b4adv3c-probe2 start=2026-10-22 19:44:54 end=2026-10-22 19:45:03 elapsed=9s bound=600s status=OK rc=0
flag-OFF differential, head scratch (11 scenarios x POST/GET x {unset, "false", "true"}, full config): 66 passed; sentinel 66; netguard 0
[pyt] tag=b4adv3c-offdiff-head start=2026-10-22 19:45:25 end=2026-10-22 19:45:33 elapsed=9s bound=600s status=OK rc=0
the same file in the base scratch worktree (81df2b64): 66 passed; sentinel 66; netguard 0
[pyt] tag=b4adv3c-offdiff-base start=2026-10-22 19:45:34 end=2026-10-22 19:45:39 elapsed=5s bound=600s status=OK rc=0
CI-order set (13 files, alphabetical, flag OFF, unit worktree): 1059 passed, 13 warnings in 19.35s; sentinel 1059; netguard blocked 10 attempt(s) from 10 node(s), all 10 in tests/.network_attempt_baseline.txt (class sentinel)
[pyt] tag=b4adv3c-ci-order start=2026-10-22 19:46:05 end=2026-10-22 19:46:27 elapsed=22s bound=1200s status=OK rc=0
CI-order set with ENABLE_URL_MODE_V2=true exported: 1059 passed, 13 warnings in 22.51s; sentinel 1059; netguard the same 10 baseline nodes
[pyt] tag=b4adv3c-ci-order-flagON start=2026-10-22 19:46:28 end=2026-10-22 19:46:53 elapsed=26s bound=1200s status=OK rc=0
```
0 [pyt] TIMEOUTs. The CI-order set is the fix report's 13 files (test_error_middleware, test_http_400_cap_cut_mapping, test_paid_route_metering, test_prompt_fence, test_retro_w2_1, test_s71_u13_compare_auth_required, test_s80_url_mode_v2, test_ssrf_redirect_hardening, test_text_routes_error_mapping, test_u13e_url_detect_guard, test_url_compare_category, test_w4_13_flag_off_ledger, test_w4_13_measurement_truth): it holds the pinned flag-OFF 400 bodies (`test_retro_w2_1`), the W4-13 ledger fixture, the T23 OpenAPI fixture and the error-envelope pins. Comm chunks, the hook files, the u8d pins and ruff are the engineering lens (and were re-measured by the round-3 re-verifier on these bytes); not re-run here.

## 3. Mutation table (scratch worktree `0aac07f1`; my own harness `B4_adv2/mutate_c.py`: lock `.qa-mutation.lock` labelled `b4adv3c-correctness-adversary` -> byte copy -> exact edit matching ONCE (CRLF-adapted) -> pyt.py bound 600 over the FULL unit file, every ENABLE_* unset, PYTHONDONTWRITEBYTECODE=1 -> restore from the byte copy -> sha256 compare (abort on mismatch; none) -> lock removed; KILLED = rc 1 with every traceback location line `AssertionError`; logs `B4_adv2/mut_<id>.log`, results `B4_adv2/mut_results.jsonl`)

61 mutants: 60 KILLED (AssertionError only), 1 SURVIVED (I1 = the A3-1 known gap, by design of the brief). Groups: the brief's hand mutants (M1 at both sites jointly AND each site alone; E1 = the quadratic `<title(?:\s[^>]*)?>(.*?)</title\s*>` regex reintroduced over `html[:65536]`, killed by `test_challenge_title_scan_is_linear`, "_is_challenge_page took 2425 ms on 65849 bytes" vs the 500 ms ceiling; F2-4a as six leaks, b, c, d, e, f as two); the 22 F3 mutants K1..K8b / R1..R5 / T1..T2 / E1b / F5e / X1 / X5 (re-written from the ruling names, same edits as the fix agent's); 23 spec mutants of B4_UNIT_SPEC section 6 expressed on the HEAD bytes (S-ids = the spec's M-numbers).

| mutant | result | failing nodes | [pyt] |
|---|---|---|---|
| M1_home_ignores_route_query | KILLED | 38 | tag=b4adv3c-M1_home_ignores_route_query 19:27:15-19:27:29 elapsed=15s status=FAIL rc=1 |
| M1b_pregate_site_only | KILLED | 18 | tag=b4adv3c-M1b_pregate_site_only 19:27:30-19:27:44 elapsed=14s status=FAIL rc=1 |
| M1c_postfetch_site_only | KILLED | 16 | tag=b4adv3c-M1c_postfetch_site_only 19:27:44-19:27:55 elapsed=11s status=FAIL rc=1 |
| E1_quadratic_title_regex | KILLED | 3 | tag=b4adv3c-E1_quadratic_title_regex 19:27:57-19:28:15 elapsed=19s status=FAIL rc=1 |
| F24a1_log_fetch_failed_url | KILLED | 5 | tag=b4adv3c-F24a1_log_fetch_failed_url 19:28:16-19:28:31 elapsed=15s status=FAIL rc=1 |
| F24a2_blocked_initial_url | KILLED | 1 | tag=b4adv3c-F24a2_blocked_initial_url 19:28:31-19:28:47 elapsed=15s status=FAIL rc=1 |
| F24a3_too_many_redirects_url | KILLED | 1 | tag=b4adv3c-F24a3_too_many_redirects_url 19:28:47-19:29:16 elapsed=29s status=FAIL rc=1 |
| F24a4_blocked_redirect_target | KILLED | 1 | tag=b4adv3c-F24a4_blocked_redirect_target 19:29:17-19:29:27 elapsed=10s status=FAIL rc=1 |
| F24a5_host_only_netloc | KILLED | 9 | tag=b4adv3c-F24a5_host_only_netloc 19:29:27-19:29:38 elapsed=11s status=FAIL rc=1 |
| F24a6_transport_error_url | KILLED | 4 | tag=b4adv3c-F24a6_transport_error_url 19:29:39-19:29:49 elapsed=10s status=FAIL rc=1 |
| F24b_webpage_is_site_name | KILLED | 1 | tag=b4adv3c-F24b_webpage_is_site_name 19:29:49-19:30:03 elapsed=13s status=FAIL rc=1 |
| F24c_raw_netloc_label | KILLED | 8 | tag=b4adv3c-F24c_raw_netloc_label 19:30:04-19:30:16 elapsed=12s status=FAIL rc=1 |
| F24d_redirect_range6 | KILLED | 1 | tag=b4adv3c-F24d_redirect_range6 19:30:16-19:30:29 elapsed=12s status=FAIL rc=1 |
| F24e_gc2_homepage_only | KILLED | 5 | tag=b4adv3c-F24e_gc2_homepage_only 19:30:31-19:30:47 elapsed=16s status=FAIL rc=1 |
| F24f1_last_link_reason | KILLED | 4 | tag=b4adv3c-F24f1_last_link_reason 19:30:47-19:31:01 elapsed=14s status=FAIL rc=1 |
| F24f2_last_product_node | KILLED | 2 | tag=b4adv3c-F24f2_last_product_node 19:31:02-19:31:12 elapsed=10s status=FAIL rc=1 |
| K1_key_drops_query | KILLED | 14 | tag=b4adv3c-K1_key_drops_query 19:31:12-19:31:23 elapsed=11s status=FAIL rc=1 |
| K2_key_whole_query | KILLED | 16 | tag=b4adv3c-K2_key_whole_query 19:31:23-19:31:34 elapsed=11s status=FAIL rc=1 |
| K3_keys_case_sensitive | KILLED | 4 | tag=b4adv3c-K3_keys_case_sensitive 19:31:34-19:31:47 elapsed=13s status=FAIL rc=1 |
| K4_values_not_stripped | KILLED | 2 | tag=b4adv3c-K4_values_not_stripped 19:31:48-19:31:58 elapsed=10s status=FAIL rc=1 |
| K4b_values_not_decoded | KILLED | 3 | tag=b4adv3c-K4b_values_not_decoded 19:31:58-19:32:11 elapsed=13s status=FAIL rc=1 |
| K5_no_products_id | KILLED | 3 | tag=b4adv3c-K5_no_products_id 19:32:12-19:32:28 elapsed=16s status=FAIL rc=1 |
| K6_pid_in_key | KILLED | 3 | tag=b4adv3c-K6_pid_in_key 19:32:29-19:32:40 elapsed=11s status=FAIL rc=1 |
| K6b_pid_in_allow_list | KILLED | 4 | tag=b4adv3c-K6b_pid_in_allow_list 19:32:40-19:32:53 elapsed=13s status=FAIL rc=1 |
| K7_key_order_sensitive | KILLED | 1 | tag=b4adv3c-K7_key_order_sensitive 19:32:53-19:33:04 elapsed=11s status=FAIL rc=1 |
| K8_empty_value_counts | KILLED | 6 | tag=b4adv3c-K8_empty_value_counts 19:33:05-19:33:19 elapsed=14s status=FAIL rc=1 |
| K8b_non_empty_value_refused | KILLED | 35 | tag=b4adv3c-K8b_non_empty_value_refused 19:33:19-19:33:33 elapsed=13s status=FAIL rc=1 |
| R1_route_startswith_product | KILLED | 26 | tag=b4adv3c-R1_route_startswith_product 19:33:33-19:33:56 elapsed=23s status=FAIL rc=1 |
| R2_route_value_case_sensitive | KILLED | 3 | tag=b4adv3c-R2_route_value_case_sensitive 19:33:56-19:34:12 elapsed=16s status=FAIL rc=1 |
| R3_route_marker_dropped | KILLED | 4 | tag=b4adv3c-R3_route_marker_dropped 19:34:12-19:34:25 elapsed=13s status=FAIL rc=1 |
| R4_route_veto_case_sensitive | KILLED | 5 | tag=b4adv3c-R4_route_veto_case_sensitive 19:34:25-19:34:42 elapsed=16s status=FAIL rc=1 |
| R5_exact_route_vetoes | KILLED | 24 | tag=b4adv3c-R5_exact_route_vetoes 19:34:42-19:34:56 elapsed=14s status=FAIL rc=1 |
| T1_first_truthy_title | KILLED | 4 | tag=b4adv3c-T1_first_truthy_title 19:34:57-19:35:09 elapsed=12s status=FAIL rc=1 |
| T2_unusable_title_not_cleared | KILLED | 4 | tag=b4adv3c-T2_unusable_title_not_cleared 19:35:10-19:35:25 elapsed=15s status=FAIL rc=1 |
| E1b_title_window_unbounded | KILLED | 1 | tag=b4adv3c-E1b_title_window_unbounded 19:35:25-19:35:37 elapsed=12s status=FAIL rc=1 |
| F5e_node_name_ignores_site_names | KILLED | 1 | tag=b4adv3c-F5e_node_name_ignores_site_names 19:35:40-19:36:22 elapsed=41s status=FAIL rc=1 |
| X1_transport_error_exc_info | KILLED | 1 | tag=b4adv3c-X1_transport_error_exc_info 19:36:24-19:36:47 elapsed=23s status=FAIL rc=1 |
| X5_401_as_http_403 | KILLED | 1 | tag=b4adv3c-X5_401_as_http_403 19:36:49-19:37:08 elapsed=19s status=FAIL rc=1 |
| I1_A31_products_id_in_home_allowlist | SURVIVED | 0 | tag=b4adv3c-I1_A31_products_id_in_home_allowlist 19:37:10-19:37:34 elapsed=24s status=OK rc=0 |
| S01_route_always_on | KILLED | 10 | tag=b4adv3c-S01_route_always_on 19:37:35-19:37:54 elapsed=19s status=FAIL rc=1 |
| S02_reader_exact_true | KILLED | 18 | tag=b4adv3c-S02_reader_exact_true 19:37:55-19:38:12 elapsed=17s status=FAIL rc=1 |
| S07_same_url_raw | KILLED | 12 | tag=b4adv3c-S07_same_url_raw 19:38:12-19:38:29 elapsed=17s status=FAIL rc=1 |
| S08_two_empty_equal | KILLED | 1 | tag=b4adv3c-S08_two_empty_equal 19:38:30-19:38:50 elapsed=21s status=FAIL rc=1 |
| S09_field_always_both | KILLED | 22 | tag=b4adv3c-S09_field_always_both 19:38:52-19:39:05 elapsed=13s status=FAIL rc=1 |
| S11_passthrough_flag_off | KILLED | 1 | tag=b4adv3c-S11_passthrough_flag_off 19:39:07-19:39:22 elapsed=15s status=FAIL rc=1 |
| S12_passthrough_non_str | KILLED | 3 | tag=b4adv3c-S12_passthrough_non_str 19:39:23-19:39:39 elapsed=15s status=FAIL rc=1 |
| S14_2xx_accepts_4xx | KILLED | 19 | tag=b4adv3c-S14_2xx_accepts_4xx 19:39:40-19:39:55 elapsed=15s status=FAIL rc=1 |
| S15_challenge_body_substring | KILLED | 4 | tag=b4adv3c-S15_challenge_body_substring 19:39:55-19:40:12 elapsed=16s status=FAIL rc=1 |
| S16_postfetch_check_removed | KILLED | 20 | tag=b4adv3c-S16_postfetch_check_removed 19:40:12-19:40:35 elapsed=22s status=FAIL rc=1 |
| S18_usable_ignores_site_names | KILLED | 15 | tag=b4adv3c-S18_usable_ignores_site_names 19:40:35-19:40:48 elapsed=12s status=FAIL rc=1 |
| S20_no_llm_shortcircuit_removed | KILLED | 5 | tag=b4adv3c-S20_no_llm_shortcircuit_removed 19:40:50-19:41:21 elapsed=31s status=FAIL rc=1 |
| S21_is_product_page_ignored | KILLED | 1 | tag=b4adv3c-S21_is_product_page_ignored 19:41:21-19:41:36 elapsed=15s status=FAIL rc=1 |
| S23_image_no_https_check | KILLED | 3 | tag=b4adv3c-S23_image_no_https_check 19:41:37-19:41:53 elapsed=15s status=FAIL rc=1 |
| S24_og_image_key_presence | KILLED | 4 | tag=b4adv3c-S24_og_image_key_presence 19:41:53-19:42:05 elapsed=12s status=FAIL rc=1 |
| S27_recommendation_unstripped | KILLED | 2 | tag=b4adv3c-S27_recommendation_unstripped 19:42:06-19:42:19 elapsed=13s status=FAIL rc=1 |
| S35_deadline_removed | KILLED | 6 | tag=b4adv3c-S35_deadline_removed 19:42:20-19:42:34 elapsed=14s status=FAIL rc=1 |
| S36_timeout_reraises | KILLED | 6 | tag=b4adv3c-S36_timeout_reraises 19:42:34-19:42:48 elapsed=14s status=FAIL rc=1 |
| S41_precedence_inverted | KILLED | 4 | tag=b4adv3c-S41_precedence_inverted 19:42:48-19:43:00 elapsed=12s status=FAIL rc=1 |
| S42_v2_kwarg_off | KILLED | 14 | tag=b4adv3c-S42_v2_kwarg_off 19:43:00-19:43:12 elapsed=12s status=FAIL rc=1 |
| S43_info_full_url | KILLED | 2 | tag=b4adv3c-S43_info_full_url 19:43:12-19:43:24 elapsed=12s status=FAIL rc=1 |
| S44_refund_skipped_new_code | KILLED | 18 | tag=b4adv3c-S44_refund_skipped_new_code 19:43:25-19:43:38 elapsed=13s status=FAIL rc=1 |

Equivalent survivors: none. Prove-nothing rows: none found at node level (every spec mutant and every named hand mutant reddens at least one row on an AssertionError); one DOCSTRING overclaims its assertion (m3 extension, section 5).

## 4. Runtime truth of the claims (measured, not read)

- **Flag-OFF identity (PLAN section 0 item 5, the row's "Flag OFF: byte-identical").** Independent differential (`b4adv3c-offdiff-*`): a self-contained probe importing no B4 symbol, run in a base `81df2b64` scratch worktree and in the head scratch worktree, 11 scenarios (PDP pair, storefront pair, same url, 403, challenge page, transport error, redirect to the homepage, a title-only page through the LLM, an og:title-equals-site-name page through the LLM, a verdict exception, an SSRF-blocked link) x POST/GET x {flag unset, "false"}, every one under the FULL configuration (metering ON, search-log truth ON, an authed user, the transport, the LLM fake, the verdict fake, the ledger): **44 of 44 records byte-identical** (status, body minus `request_id`, consume / refund / lifetime / history / search_logs rows / fire-and-forget labels, LLM and verdict call counts, the fetched url list). The pinned bodies hold: SSRF `400 {"success": false, "error": "URL blocked by security policy", "code": "BAD_REQUEST"}` and the codeless `400 ... "Could not extract both products"` (403 and transport scenarios) are identical at base and head; the CI-order set (it carries `test_retro_w2_1`'s 400 pins and the W4-13 ledger fixture) is green flag OFF and with the flag exported. Unflagged deltas are log text only (R-A1 b), as the row says.
- **Billing R-A3 on every new exit (flag ON leg of the same differential, real route, full config).** 22 of 22 ON records satisfy: pre-gate refusals (`home_pair` -> `NOT_PRODUCT_PAGE url1 homepage`, `same_url` -> `both same_url`) consume 0, refund 0, no row, nothing fetched; post-fetch refusals (`http_403`, `challenge`, `transport` -> `STORE_UNREADABLE` http_403 / challenge / fetch_error; `redirect_home` -> `NOT_PRODUCT_PAGE homepage` after 3 fetches; `og_site_llm` -> `UNRESOLVED_PRODUCT no_product_node`) consume 1, refund 1, lifetime 0, history 0, exactly one failure row carrying the code's copy constant; deliveries consume 1, refund 0, lifetime 1, history 1, one success row; the verdict exception keeps the base exception arm (500, refund 1, row `url_compare_exception`). The deadline exit is pinned by `test_deadline_yields_timeout_503` (refund label, one failure row with `TIMEOUT_FRIENDLY_MESSAGE`, 503, four-key body) and killed by S35 / S36 here.
- **Error-handler mapping and scope (ruling B4-R5).** Code read: the passthrough reads the flag FIRST, requires a structured detail with a str `code` in the three B4 codes, copies str `field` / `reason` only; S11 (passthrough with the flag OFF) and S12 (non-str copied) are killed. TIMEOUT is the structured 503 through `_surface_comparison_failure` (never a bare 503, PLAN section 0 item 3).
- **Contract freeze (PLAN section 0).** ON delivery keys = the frozen 8-key set (no `metadata`, R0-1); `image_url` a str or None (S23 / S24 killed); the 400 refusal adds only `field` / `reason`; flag OFF untouched (above). The new codes render build 3's generic copy (ruled R-A7 / B4-R11).
- **Pre-gate over-refusal on real PDP urls.** `classify_url_path` over 707 held urls (probe 2): the 39 registry `sample_url` refusals are all collection / brand / homepage liveness urls, the 5 global-corpus "usable_pdp" refusals are storefront roots (`/?lang=en` x4, `miswag.com/en`) and the 1 Gulf-sweep refusal is `faces.ae/en/brands/tom-ford` (a brand listing): **0 real PDPs refused**. The same-url key over the same set collides 3 times, each two links of ONE product (a trailing slash; a `?country=` parameter): correct refusals.
- **E1 linearity at HEAD.** `_is_challenge_page` on a 65,812-byte `<title ` flood 0.10 ms; a 64 KB `</title ` close-like flood 2.26 ms; a `<titlex` flood ending in a real challenge title 1.88 ms (verdict True); an unclosed opener with 30,000 attributes 0.04 ms; a `<` flood 0.07 ms (probe 2).
- **Row / PR sentences re-checked against the bytes and found imprecise:** m1-m4 (confirmed, section 5), plus c-m1 (the "usable `<title>` / og:title" and "no usable title" sentences), c-m2 (limit 11's class), the A3-1 sentence (PR line 74 / fix report D3), the noon clause of limit (3) (information). Everything else this lens checked (the deadline, the R-A3 exits, the passthrough scope, the four-key OFF envelope, the outcome vocabulary, the WARNING / ERROR split, the host-only SSRF lines) matches the bytes.

## 5. Findings

### BLOCKING

None.

### MAJOR

None. (Every candidate below was measured for prevalence before it was graded; none reaches a measured real PDP class.)

### minor

- **c-m1 (NEW, code + row/PR text): the meta title is the first TRUTHY of og:title / `<title>`, not the first USABLE (the F3-3 defect class at a second site).** `extract_generic_data_v2` (url_extraction_service.py, `meta_title = meta.get("og_title") or meta.get("page_title")`) feeds both the F2-5 fallback and, on a node-less page, the `no_product_node` decision in `_extract_from_url_v2`. When og:title is truthy but unusable (equal to og:site_name / an Organization or WebSite name, or a placeholder) a usable `<title>` is never consulted. Measured (probe 1, `b4adv3c-probe1`, flag ON vs the base body OFF, same pages, same LLM fake):
  - node-less page, og:title = og:site_name "Rasasi Store", `<title>` "Rasasi Hawas Ice 100ml | Rasasi Store": ON `UNRESOLVED_PRODUCT no_product_node`, 0 LLM calls; OFF delivered (`name` "Hawas Ice" from the LLM), 1 call;
  - the same with og:title "Product": ON `no_product_node`, 0 calls; OFF delivered;
  - a Product node named like the site, WITH a price, og:title = site, usable `<title>`: ON `null_name`, 0 calls (the price skips the LLM, the F2-5 fallback reads the unusable og:title); OFF delivers the site name (garbage);
  - control (no og:title, usable `<title>`): ON == OFF delivered.
  - through the real route POST and GET, full configuration (the differential's `og_site_llm` scenario): flag ON `400 UNRESOLVED_PRODUCT url1 no_product_node`, 0 LLM calls, consume 1 / refund 1; flag OFF `200` with `products[0].name` "Hawas Ice", 1 LLM call, byte-identical at base and head.
  This contradicts B4-R1's text ("null_name only when the page title is unusable; a usable title keeps the page") and the row / PR body sentences "no usable title (empty, a placeholder, or equal to an Organization / WebSite name or og:site_name ...)" and "a Product node whose name is missing or unusable takes a usable `<title>` / og:title" (PR body lines 11 and 69): the `<title>` is taken only when og:title is absent. **Prevalence (why minor, not MAJOR):** a read-only scan of 683 held pages (`b4adv3c-scan*`: 162 test fixtures, the 92-page Gulf PDP corpus, the 429-page global corpus) finds 5 pages in the class, ALL non-PDPs (two Shopify `/password` pages, a "Category not found!" page, two storefront homepages), where today's $0 refusal is the correct verdict and the "first usable" fix would add one paid LLM call each; 0 real PDPs. Fix options for the gate: (a) `meta_title` = the first `is_usable_title` of og:title, `<title>` (one line; RED rows from the three probe pages; costs one LLM call on the measured non-PDP hits), or (b) keep the behaviour and correct the row / PR sentences into a stated limit ("og:title, when present, is the only meta title consulted").
- **c-m2 (NEW, docs): limit (11) / PR line 140 name only the ASP.NET `?pid=` class, but EVERY query-keyed store outside the allow-list is refused `same_url`.** Measured through the real route POST, full config (probe 1): `product.php?id=11` vs `?id=12`, `ProductDetails.aspx?ProductID=11` vs `=12`, `item?sku=AB11` vs `AB12` (one store each): flag ON `400 NOT_PRODUCT_PAGE both / same_url`, 0 fetches, 0 consumes; flag OFF `200`, 2 fetches, 1 consume. The rule is the ruled F3-1 allow-list (a blanket query rule is forbidden), so this is behaviour-as-ruled, but the stated limit understates the class (`id`, `ProductID` (no underscore), `sku`, `itemid`, ...). The held registry has no such PDP shape (its only query-keyed PDP rows are the 5 OpenCart `route + product_id` rows), so no measured live store is affected. Fix: limit (11) and the PR stated-limits paragraph say "two products of one store addressed by any query key outside the allow-list (e.g. `product.php?id=`, `ProductDetails.aspx?ProductID=`, `?sku=`, the ASP.NET `?pid=`)". A design note for the follow-up: a TRACKING-key deny-list (utm_*, gclid, gbraid, wbraid, fbclid, srsltid, ref, ...) instead of a product-key allow-list would turn this over-refusal class into the cheaper failure mode (one product fetched twice).
- **m1 CONFIRMED** (PR body line 42): the "new frozen sha256 `b6753884...238a` (408 nodes, 119,199 bytes)" is the intermediate RED-step file; the committed file is `bac87301...f1d9`, 119,355 bytes (re-hashed here, section 1); line 90 carries the right value.
- **m2 CONFIRMED** (PR body lines 80 and 125, fix report): `harness/pyt_ledger.jsonl` line 38 `d03rev-probe1` 16:45:56-16:46:11 sits inside line 39 `b4f3-hooks` 16:27:37-16:53:03; "ALONE (no other pytest on the box)" overclaims (the run ended OK, the measurement stands).
- **m3 CONFIRMED and EXTENDED**: PR line 78 says `exc_info`, `exc_text` and `stack_info` are None "on every other record of the run"; `test_transport_error_line_carries_no_exception_info` asserts all three on the ERROR record only and `rec.exc_info` falsy on the others (no `exc_text` / `stack_info` check there). The row's own DOCSTRING makes the same overclaim ("like every other record of the run ... no stack info"), so the docstring needs the same correction (a docstring edit changes the frozen RED sha; the gate decides whether to touch it).
- **m4 CONFIRMED and EXTENDED**: limit (1) / the effect clause / PR line 140 say an OpenCart listing route on a root or `/index.*` path is refused at $0; probe 2 measures `classify_url_path` = None (exempt, fetched) for `/index.php?route=product/category&product_id=5` AND for `/?route=checkout/cart&product_id=5` (a CART route): any route carrying a non-empty `product_id` / `id_product` / `product` is exempt. Cost only (the link is fetched; a cart page then needs the paid LLM rung to be refused `not_product_page`). Fix: "unless the link also carries a non-empty product_id / id_product / product".

### known gap (recorded per the brief, NOT a MAJOR): A3-1, with a measured extension

`products_id` is in the same-url key but absent from the homepage-class allow-list at both F2-1 sites. Mutant `I1_A31_products_id_in_home_allowlist` SURVIVES (no row pins either reading). Measured beyond the osCommerce root link of the addendum: **Zen Cart's default (non-SEO) PDP url `index.php?main_page=product_info&products_id=N` is classified `homepage`**, and a Zen Cart same-store pair through the real route POST, full config, is flag ON `400 NOT_PRODUCT_PAGE both / homepage`, 0 fetches, 0 consumes, while flag OFF delivers `200` (probe 1, `zencart-main_page`). So the fix report's D3 sentence and PR line 74 ("an osCommerce PDP is `product_info.php`, which no class refuses") understate the class: every non-SEO Zen Cart PDP is refused at $0. The A3-1 fix (products_id joins the allow-list at both sites) closes it; the next round's RED rows should include the Zen Cart shape (`/index.php?main_page=product_info&products_id=12` exempt, POST and GET).

### information

- i-1 amazon / noon: their base extractors never read `<title>`, so an Amazon page without `#productTitle` and a noon page with neither a JSON-LD Product nor an `<h1>` are `no_product_node` at $0 although their `<title>` names the product; OFF the LLM delivers (probe 1). Limit (7) states the Amazon interstitial case; limit (3)'s "noon only after the paid LLM rung" holds only for a noon page WITH an `<h1>` or a Product node (`extract_noon_data`'s title sources, read from code; the probe's noon page with neither is refused at $0). Wording only.
- i-2 The pathological title shapes stay linear at HEAD (probe 2 timings, section 4).
- i-3 Same-scheme only: `http://` vs `https://` links of one product are different keys (fetched twice; cost only).

## 6. Questions for the gate

1. c-m1: fix (meta title = the first USABLE of og:title / `<title>`, with RED rows from the three probe pages; one more LLM call on the measured non-PDP hits) or record as a stated limit and correct the row / PR sentences? Grading it minor rests on 0 PDPs in 683 held pages; the gate may grade it MAJOR on B4-R1's text alone.
2. c-m2: is the allow-list's over-refusal class (any same-store pair keyed outside the five keys) acceptable as a stated limit (the row then needs the wider wording), or should the follow-up move the same-url key to a tracking-key deny-list?
3. A3-1: include the Zen Cart `index.php?main_page=product_info&products_id=N` shape in the next round's RED rows (POST and GET), since it is the realistic class behind the gap.
4. m1-m4 + the m3 docstring: fix now (docs; the docstring edit re-freezes the RED sha) or at the GC-7 rebase.

## 7. NOT MEASURED

- Comm chunks, the hook files, the u8d R8 pins, the metering file both ways, ruff / py_compile and the two CLAUDE.md readers on these bytes (engineering lens; the round-3 re-verifier measured them on `0aac07f1`, B4_FIX3_REVERIFY section 2). This lens ran the unit file both ways, the CI-order set both ways, 61 mutants, the OFF differential and the probes.
- Any live store, Railway, Sentry or OpenAI behaviour (rules). The og-shadow and generic-query-key classes were measured on synthetic pages and held corpora only; their live prevalence is unknown.
- The post-rebase run (GC-7) and the engineering adversary on this HEAD (the orchestrator).

## 8. End state

Unit worktree `sc-s80-b4`: HEAD `0aac07f1f7304e61fa5cac86935c9306f08605d0`, `git status --short` empty, no `.qa-mutation.lock`, never edited. Scratch worktrees `B4_adv2_correctness` and `B4_adv2_base` removed with `git worktree remove --force` (no node_modules in either; `git worktree list` shows neither). No pytest of mine left running. Notes folder `<scratchpad>/B4_adv2/`: this report, `notes.md`, `mutate_c.py`, `mut_results.jsonl`, `mut_table.txt`, `mut_*.log`, `mut_bak/` (the byte copies), the probe files `test_zz_b4adv3c_probe.py`, `test_zz_b4adv3c_probe2.py`, `test_zz_b4adv3c_scan.py`, `test_zz_b4adv3c_offdiff.py` (copies; the copies placed in the scratch worktrees went with them), `cmp_offdiff.py`, `probe_c.jsonl`, `probe_c2.jsonl`, `scan_*.jsonl`, `shadow_pages.txt`, `offdiff_head.jsonl`, `offdiff_base.jsonl`, `claude_row.txt`, `svc.diff`, every `*.log`.

