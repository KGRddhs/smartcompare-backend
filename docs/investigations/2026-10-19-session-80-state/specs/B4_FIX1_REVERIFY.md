# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- fix round 1 RE-VERIFY report (correctness lens, 2026-10-20)

- Unit B4 fix round 1. Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, HEAD verified `96676f1fe9ddc4b4bc57e3e8aec166e4c7e26d4b` at 16:06 (parents: `9db99de9` GREEN, `81df2b64` base). `git status --short` empty at the start and at the end. The worktree was never edited (every gate there ran with PYTHONDONTWRITEBYTECODE=1; probes, mutants and the base run ran in my own detached scratch worktrees).
- Agent model: claude-opus-5-5 (this agent's system prompt).
- Inputs read: s80-common.txt (+ 2026-10-20 addendum), PLAN_S80.md sections 0-1, RULINGS_R0.md (via the plan), RULINGS_BATCH1.md Common + B4-R1..R11, GATE_B4.md GC-1..GC-8, RULINGS_FIX1_B4.md (twice), B4_GREEN_REPORT.md (the round this answers), B4_FIX1_REPORT.md, PR_BODY.md, the CLAUDE.md B4 row, the fix diff `9db99de9..96676f1f`, the B4 hunks of url_extraction_service / url_routes / error_handler, the R8 AST pins of tests/test_sentry_channels_u8d_unit.py.
- Notes folder: `<scratchpad>/B4_fix1_rv/` (notes.md, mut_rv.py, mut_results.jsonl, mut_table.txt, every log named below, claude_row.txt, delta_union.txt, adv_verify_before/after.txt).

## 1. Hashes (bytes on disk; re-hashed at the start and the end)

| file | sha256 | notes |
|---|---|---|
| tests/test_s80_url_mode_v2.py (RED) | 546fc27d07579808ea7b8b7fb60cd87a3be8462ebdaea677aa3c8e21587f8b46 | = committed blob; LF, 0 bytes > 127, 75,913 B, 253 nodes; first 71,891 B hash to c4549be2f5cd8edfd60cbc07db427ed5275cc4b44ab719614ef97b9eca227cae (pure append of the F4-2 row) |
| app/services/url_extraction_service.py | 0abf3b950898fd10678f3092c424729696072a6d33b1925d3dc2a09279e647c2 | CRLF 1295/1295, 18 bytes > 127 (pre-existing, = GREEN) |
| tests/test_paid_route_metering.py | 4724c308c6a5805a873a015f2a07e02850e8db5c020f46423e71208505ead73f | CRLF 831/831, 0 bytes > 127 |
| CLAUDE.md | 8502da3b038953d7ecaad3637567683f8149415af1304c90fc1dc52749a2c0ad | CRLF 938/938; the B4 row (line 475) is pure ASCII |
| app/api/url_routes.py | 9229e0b4d027e392f21e5da9edb29549f40fcde2bb22ca90c4351701ab3a59ba | unchanged since GREEN |
| app/middleware/error_handler.py | 7e539cc7b17fcc6c9b982a2ebe4b212096af57deb8c1bded330eb57e5fc6d482 | unchanged since GREEN |
| PR_BODY.md (notes, not committed) | ea1a3ae4d909aae87b41243954eb2ba5a8bd9f5e1e6db9f67277c7433b80e82f | LF, 4 bytes > 127 = the required robot-glyph line (D9) |

All equal the fix report's values. Fix diff `9db99de9..96676f1f`: 4 files, +99/-6 (CLAUDE.md 4, service 14, metering 12, RED 75), no whole-file diff; added-line sweep (99 lines): 0 hits for @gmail / +973 / 8-digit runs / sk- / AKIA / xox / eyJ / credentialed URL / PEM, 0 non-ASCII.

## 2. Runs (every pytest through pyt.py, one at a time; flag state = the env of that one call)

Unit file, the bytes under verification (worktree):
```
ENABLE_URL_MODE_V2=true: 253 passed, 11 warnings in 15.02s; [hermeticity] sentinel checked 253 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4rv-unit-on start=2026-10-20 16:09:53 end=2026-10-20 16:10:10 elapsed=17s bound=600s status=OK rc=0
flag unset: 253 passed, 11 warnings in 13.70s; sentinel 253; netguard blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4rv-unit-off start=2026-10-20 16:10:24 end=2026-10-20 16:10:40 elapsed=15s bound=600s status=OK rc=0
```
The R8 pins, each file ALONE (flag unset):
```
tests/test_sentry_channels_u8d_unit.py: 141 passed, 1 warning in 21.65s; sentinel 141; netguard 0
[pyt] tag=b4rv-u8d-unit start=2026-10-20 16:10:53 end=2026-10-20 16:11:16 elapsed=24s bound=600s status=OK rc=0
tests/test_sentry_channels_u8d.py: 131 passed, 1 warning in 15.16s; sentinel 131; netguard 0
[pyt] tag=b4rv-u8d start=2026-10-20 16:11:29 end=2026-10-20 16:11:46 elapsed=17s bound=600s status=OK rc=0
```
Metering file, both flag states (E6 proof):
```
flag unset: 21 passed, 13 warnings in 8.44s; sentinel 21; netguard blocked 2 attempt(s) from 2 node(s)
[pyt] tag=b4rv-meter-off start=2026-10-20 16:11:59 end=2026-10-20 16:12:10 elapsed=11s bound=600s status=OK rc=0
ENABLE_URL_MODE_V2=true exported: 21 passed, 13 warnings in 8.70s; sentinel 21; netguard blocked 2 attempt(s) from 2 node(s)
[pyt] tag=b4rv-meter-on start=2026-10-20 16:12:11 end=2026-10-20 16:12:22 elapsed=11s bound=600s status=OK rc=0
```
(both blocked nodes, `test_camera_success_consumes_once_and_never_refunds` and `test_url_compare_saves_history_with_input_type_url`, are `[sentinel]` rows already in tests/.network_attempt_baseline.txt:92-93.)

CI-order set (13 files alphabetical, flag OFF only per B4-R8):
```
904 passed, 13 warnings in 26.04s; [hermeticity] sentinel checked 904 test(s); [netguard] blocked 10 attempt(s) from 10 node(s)
[pyt] tag=b4rv-ci-order start=2026-10-20 16:12:40 end=2026-10-20 16:13:08 elapsed=28s bound=1200s status=OK rc=0
```
(all 10 netguard nodes are in the baseline; = the GREEN and fix-round counts.)

Fix-round delta comm set, re-derived at HEAD (`delta_union.txt`, 37 test files): the module/symbol grep `url_extraction_service|_fetch_page_v2|extract_from_url|compare_from_urls` (19 test files) UNION every test that walks app/ (rglob / os.walk over the app dir, 17 files) UNION the named source-scanning pins of s80-common (test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit) UNION the CLAUDE.md readers (test_ci_gates, test_behavior_dimension_translation) UNION every test naming an edited test file (test_image_identify_llm_unavailable_s69.py, docstrings only); no hook file matched; 11 already run above; the other 26 in two chunks, flag OFF:
```
c1 (test_auth_error_log_hygiene, test_behavior_dimension_translation, test_ci_gates, test_conftest_env_safety, test_domain_s76, test_hermeticity_pins, test_image_identify_llm_unavailable_s69, test_legal_disclosure_s77, test_legal_docs_u8, test_legal_s78, test_llm_provider_base_url, test_migration_043_delete_user_cascade, test_migration_index_predicate_immutability):
560 passed, 1 skipped, 2 deselected, 16 warnings in 145.26s; [hermeticity] sentinel checked 561 test(s); [netguard] blocked 22 attempt(s) from 21 node(s)
[pyt] tag=b4rv-delta-c1 start=2026-10-20 16:18:44 end=2026-10-20 16:21:12 elapsed=148s bound=1200s status=OK rc=0
c2 (test_model_config, test_model_config_enforced, test_openai_breaker, test_openai_key_log_hygiene_s69, test_retro_w0_4, test_retro_w0_4_efg, test_retro_w1_2b, test_s70_url_client_retries, test_shopify_pdp_json, test_start_command, test_u3b_sharing_branch_removed, test_u3c_store_false_pin, test_url_validator_offloop_hops):
526 passed, 13 warnings in 95.87s; [hermeticity] sentinel checked 526 test(s); [netguard] blocked 121 attempt(s) from 6 node(s)
[pyt] tag=b4rv-delta-c2 start=2026-10-20 16:21:59 end=2026-10-20 16:23:37 elapsed=98s bound=1200s status=OK rc=0
```
Netguard: c1's 21 nodes are all test_hermeticity_pins guard self-tests, c2's 6 are test_openai_breaker nodes; every one is in tests/.network_attempt_baseline.txt (checked node by node). Zero FAILED / ERROR ids at HEAD over the whole delta set, the CI-order set, the unit, R8 and metering files, so `comm -13` against any base set is empty by construction (no base re-run needed; the two cold-tiktoken test_prompt_truth ERRORs are not in this delta set).

Flag-EXPORTED measurements (the local-.env class, CLAUDE.md limit 16):
```
the GREEN 20-file pin set (B4_fix1/pins20_files.txt), ENABLE_URL_MODE_V2=true: 1037 passed, 13 warnings in 32.81s; sentinel 1037; netguard blocked 10 attempt(s) from 10 node(s) (all in the baseline)
[pyt] tag=b4rv-pins20-flagON start=2026-10-20 16:33:51 end=2026-10-20 16:34:26 elapsed=35s bound=1200s status=OK rc=0
the other five URL-route readers not in that set (test_b2_strict_optional_auth, test_sentry_channels_u8d, test_shutdown_drain, test_url_validator_offloop, test_url_validator_offloop_hops), ENABLE_URL_MODE_V2=true: 195 passed, 11 warnings in 23.32s; sentinel 195; netguard 0
[pyt] tag=b4rv-urlreaders-flagON start=2026-10-20 16:38:29 end=2026-10-20 16:38:54 elapsed=25s bound=1200s status=OK rc=0
```
Base run (closes fix-report X4; detached scratch worktree `B4_fix1_base` at `81df2b64`, the RED file copied in byte-exact, sha 546fc27d...8b46; removed afterwards):
```
207 failed, 46 passed, 11 warnings in 14.19s; sentinel 253; netguard 0 (= the gate's 206 RED + the new row; 46 PIN)
[pyt] tag=b4rv-base-red start=2026-10-20 16:35:14 end=2026-10-20 16:35:30 elapsed=16s bound=600s status=FAIL rc=1
```
690 E-lines; 203 exception-class E-lines, ALL AssertionError (0 other class). The new row at base: `E AssertionError: B4: extract_from_url has no 'url_mode_v2' parameter: ['url']` (the `_assert_kwarg` first line, as the PR body states).

Log-level census of the unreadable-fetch rows (scratch worktree, `-o log_cli=true --log-cli-level=WARNING`, rows transport_error / challenge_page_is / v02_fragrancex / route_fetch_blocked, POST+GET):
```
10 passed, 243 deselected, 11 warnings in 2.70s
[pyt] tag=b4rv-r12-errlog start=2026-10-20 16:39:17 end=2026-10-20 16:39:21 elapsed=4s bound=600s status=OK rc=0
ERROR   x2  [URL-V2] fetch failed host=www.fragrancex.com reason=fetch_error type=ConnectTimeout   (url_extraction_service.py:439, inside the except arm)
WARNING x2 each  [URL-V2] fetch failed ... reason=blocked|challenge|http_403|redirect_cap type=None (url_extraction_service.py:321, _log_fetch_failed)
WARNING x2  [SSRF] Blocked redirect to host=169.254.169.254 ; WARNING x2  [SSRF] Too many redirects for host=www.fragrancex.com
```
No other ERROR record from any logger (url_routes, error_handler) on these refusals: exactly ONE ERROR per transport-error request, as the row and the PR body state.

Lint (scratch worktree, same bytes): `ruff check --select E9,F63,F7,F82 --no-cache` over the 3 app files + E1-E6 test files + the unit file: `All checks passed!`; `py_compile` on the same 10: rc 0; full-rule ruff on url_extraction_service.py: `Found 58 errors.` for the GREEN bytes (B4_fix1/before copy, sha 649c93a8...) and `Found 58 errors.` for HEAD (the PR body's 58 / 58 confirmed).

Pre-commit hook files ALONE (scratch worktree; `.githooks` untouched by the unit; box under load: `node -e 0` 0.77 s at 16:07, 2.60 s at 16:52):
```
collect (4 files): 62 + 114 + 121 + 30 = 327 nodes
[pyt] tag=b4rv-hook-collect start=2026-10-20 16:39:59 end=2026-10-20 16:40:02 elapsed=3s bound=600s status=OK rc=0
tests/test_precommit_hook.py -k "not dash": 31 passed, 31 deselected, 2 warnings in 748.87s; sentinel 31; netguard 0
[pyt] tag=b4rv-h1-nd start=2026-10-20 16:40:25 end=2026-10-20 16:52:55 elapsed=750s bound=1200s status=OK rc=0
tests/test_precommit_hook.py -k dash: 31 passed, 31 deselected, 2 warnings in 902.07s; sentinel 31; netguard 0
[pyt] tag=b4rv-h1-d start=2026-10-20 16:52:57 end=2026-10-20 17:08:00 elapsed=904s bound=1200s status=OK rc=0
tests/test_precommit_hook_round2.py -k "not dash": 15 passed, 15 deselected, 2 warnings in 360.23s; sentinel 15; netguard 0
[pyt] tag=b4rv-h4-nd start=2026-10-20 17:08:25 end=2026-10-20 17:14:26 elapsed=362s bound=1200s status=OK rc=0
tests/test_precommit_hook_round2.py -k dash: 15 passed, 15 deselected, 2 warnings in 397.16s; sentinel 15; netguard 0
[pyt] tag=b4rv-h4-d start=2026-10-20 17:14:36 end=2026-10-20 17:21:14 elapsed=399s bound=1200s status=OK rc=0
```
0 TIMEOUTs. tests/test_precommit_hook_phase_b.py (114 nodes) and tests/test_precommit_hook_phase_b_round2.py (121 nodes): NOT MEASURED (section 7). The unit's commits passed the hook itself (fix report), and `.githooks` is untouched by the unit.

## 3. Mutation table (scratch worktree `B4_fix1_adv`, detached at 96676f1f; mutation lock created and removed per batch; byte copy -> exact edit matching once (EOL-adapted, CRLF app files) -> killing rows via pyt.py -k (bound 600) -> restore from the byte copy -> sha256 compare; PYTHONDONTWRITEBYTECODE=1 so no stale pyc)

Scratch sha-verify: before the first mutant every checked file equals the worktree byte for byte (the RED file was copied byte-exact over the autocrlf checkout: 546fc27d...8b46) and after the last probe again (adv_verify_before/after.txt: RED 546fc27d, service 0abf3b95, metering 4724c308, url_routes 9229e0b4, error_handler 7e539cc7, both u8d files, conftest, CLAUDE.md 8502da3b; lock absent). Controls on the unmutated scratch copy: unit + u8d_unit `394 passed` (`[pyt] tag=b4rv-adv-control start=2026-10-20 16:27:19 end=2026-10-20 16:27:36 elapsed=17s bound=600s status=OK rc=0`); metering `-k url_compare` with the flag exported `7 passed, 14 deselected` (`[pyt] tag=b4rv-adv-control-meter-on start=2026-10-20 16:27:44 end=2026-10-20 16:27:48 elapsed=4s bound=600s status=OK rc=0`).

| # | mutant (fix) | result | first killing node (all E-lines AssertionError, 0 other class) | [pyt] |
|---|---|---|---|---|
| M1 | F4-1, R8 shape 1a: the F4-1 ERROR line reuses the base `Failed to fetch URL host` prefix | KILLED (1) | test_sentry_channels_u8d_unit.py::TestR8SourceLines::test_u8d_red_r8_in_except_lines_no_user_content[url_extraction_fetch_failed] ("found 2") | tag=b4rv-M1_r8_new_line_reuses_base_prefix start=2026-10-20 16:27:55 end=2026-10-20 16:28:01 elapsed=6s bound=600s status=FAIL rc=1 |
| M2 | F4-1, R8 shape 1b: a SECOND ERROR with the base prefix beside the F4-1 line | KILLED (3) | the same u8d R8 node + test_transport_error_is_store_unreadable[POST|GET] | tag=b4rv-M2_r8_second_error_base_prefix start=2026-10-20 16:28:02 end=2026-10-20 16:28:07 elapsed=6s bound=600s status=FAIL rc=1 |
| M3 | F4-1, R8 shape 2: the distinct template demoted to WARNING (GREEN's GC-1 shape) | KILLED (2) | test_transport_error_is_store_unreadable[POST|GET] (`AssertionError: []`) | tag=b4rv-M3_r8_distinct_template_demoted_warning start=2026-10-20 16:28:08 end=2026-10-20 16:28:18 elapsed=10s bound=600s status=FAIL rc=1 |
| M4 | F4-1: the ERROR leaves the except arm (`_log_fetch_failed` at ERROR, the arm calls it) | KILLED (1) | test_sentry_channels_u8d_unit.py::TestR8SourceLines::test_u8d_pin_r8_no_other_outside_except_error_line | tag=b4rv-M4_error_outside_except_via_helper start=2026-10-20 16:28:27 end=2026-10-20 16:28:36 elapsed=9s bound=600s status=FAIL rc=1 |
| M5 | F4-1: the ERROR line logs the pasted url, not the host | KILLED (2) | test_transport_error_is_store_unreadable[POST|GET] (`/products/` in the line) | tag=b4rv-M5_error_line_logs_pasted_url start=2026-10-20 16:28:37 end=2026-10-20 16:28:47 elapsed=10s bound=600s status=FAIL rc=1 |
| M5b | F4-1: the ERROR line logs the exception value, not its TYPE | KILLED (2) | test_transport_error_is_store_unreadable[POST|GET] | tag=b4rv-M5b_error_line_logs_str_e start=2026-10-20 16:28:48 end=2026-10-20 16:28:53 elapsed=5s bound=600s status=FAIL rc=1 |
| M6 | F4-2 = G10: the normaliser-stage image coercion removed | KILLED (1) | test_normaliser_coerces_a_raw_image_list_flag_on (`('amazon_raw_src', None, '//m.media.example.test/images/b4.jpg')`) | tag=b4rv-M6_G10_normaliser_coercion_removed start=2026-10-20 16:28:53 end=2026-10-20 16:28:58 elapsed=5s bound=600s status=FAIL rc=1 |
| M7 | F4-3 = E6 removed (`_CLEAN_ENV = ()`), flag EXPORTED | KILLED (5) | the five url_compare_* nodes of test_paid_route_metering.py (`assert 500 == 200`) | tag=b4rv-M7_E6_clean_list_emptied start=2026-10-20 16:28:59 end=2026-10-20 16:29:04 elapsed=5s bound=600s status=FAIL rc=1 |
| M8 | spec B4-R5: error-handler passthrough unscoped (any code) | KILLED (1) | test_error_handler_four_key_body[on-other-code-keys] | tag=b4rv-M8_handler_passthrough_unscoped start=2026-10-20 16:29:13 end=2026-10-20 16:29:18 elapsed=5s bound=600s status=FAIL rc=1 |
| M9 | house idiom: service flag reader without `.strip().lower()` | KILLED (9) | test_service_flag_reader_table[TRUE] + test_flag_reader_table_on rows | tag=b4rv-M9_service_reader_no_strip_lower start=2026-10-20 16:29:19 end=2026-10-20 16:29:24 elapsed=5s bound=600s status=FAIL rc=1 |
| M10 | PLAN 0 item 4: an http image accepted | KILLED (3) | test_pdp_image_is_first_https_string[http_only-*] + test_normaliser_coerces_a_raw_image_list_flag_on | tag=b4rv-M10_image_http_accepted start=2026-10-20 16:29:25 end=2026-10-20 16:29:30 elapsed=5s bound=600s status=FAIL rc=1 |
| M11 | flag-OFF identity: the OFF route passes `url_mode_v2=False` explicitly | KILLED (16) | test_flag_off_homepage_pair_is_base_behaviour[*] (`{'url_mode_v2': False} == {}`) | tag=b4rv-M11_off_path_explicit_kwarg start=2026-10-20 16:29:30 end=2026-10-20 16:29:38 elapsed=8s bound=600s status=FAIL rc=1 |
| M12 | R-A3: no refund for a B4 coded refusal | KILLED (8) | test_non_delivery_per_r_a3_every_code[*-meter-on] | tag=b4rv-M12_no_refund_for_v2_refusals start=2026-10-20 16:29:47 end=2026-10-20 16:29:53 elapsed=6s bound=600s status=FAIL rc=1 |
| M13 | B4-R2: challenge judged on the whole body | KILLED (2) | test_body_text_access_denied_is_not_a_challenge[POST|GET] | tag=b4rv-M13_challenge_on_whole_body start=2026-10-20 16:29:54 end=2026-10-20 16:29:59 elapsed=5s bound=600s status=FAIL rc=1 |
| M14 | R-A7: same_url compared without normalising url2 | KILLED (8) | test_pregate_same_url_after_normalisation[*] | tag=b4rv-M14_same_url_unnormalised start=2026-10-20 16:29:59 end=2026-10-20 16:30:05 elapsed=5s bound=600s status=FAIL rc=1 |
| M15 | V02: a 403 reported as http_4xx | KILLED (7) | test_v02_fragrancex_403_is_store_unreadable[*], test_both_urls_403_field_both[*], test_mixed_codes_precedence[*], test_non_2xx_reason_table[403-http_403] | tag=b4rv-M15_403_reason_generic start=2026-10-20 16:30:05 end=2026-10-20 16:30:10 elapsed=5s bound=600s status=FAIL rc=1 |

16/16 KILLED, every kill on an AssertionError, every restore sha-equal (service 0abf3b95 / metering 4724c308 / error_handler 7e539cc7 / url_routes 9229e0b4 before == after). One per fix: F4-1 (M1-M5b, incl. both R8 shapes the ruling names), F4-2 (M6 = G10), F4-3 (M7); eight spec mutants (M8-M15) beyond GREEN's G1-G12.

Information probes of the contracts F4-4 accepted WITHOUT a pin (full unit file, scratch):

| # | probe | result | [pyt] |
|---|---|---|---|
| P1 | D2: a WebPage node's name counts as a site name (`_V2_SITE_NAME_TYPES` + "WebPage") | SURVIVED (253 passed) | tag=b4rv-P1_D2_webpage_counts_as_site_name start=2026-10-20 16:37:12 end=2026-10-20 16:37:21 elapsed=9s bound=600s status=OK rc=0 |
| P2 | D3: the v2 `[SSRF] Blocked redirect to host=` WARNING prints the full redirect target | SURVIVED (253 passed) | tag=b4rv-P2_D3_ssrf_redirect_line_full_url start=2026-10-20 16:37:21 end=2026-10-20 16:37:30 elapsed=9s bound=600s status=OK rc=0 |
| P3 | D4: the `Detected retailer` label is `retailer['name']` (the raw netloc of an unknown host) | SURVIVED (253 passed) | tag=b4rv-P3_D4_retailer_label_raw_netloc start=2026-10-20 16:37:31 end=2026-10-20 16:37:40 elapsed=9s bound=600s status=OK rc=0 |

No other test file references `_V2_SITE_NAME_TYPES`, `og_site_name`, `Detected retailer`, `_retailer_log_name` or `Blocked redirect to host` (grep over tests/), so these three stated contracts are unpinned anywhere (GREEN already said "unpinned" for D2 and D4; F4-4 accepted them as contract and did not ask for pins).

## 4. The CLAUDE.md row and the PR body against the bytes

CLAUDE.md row (line 475 of the worktree file; word diff vs GREEN = the six F4-6 hunks). Each fix-round sentence checked against code and measurement:
- Header cites F4-1..F4-6 of `specs/RULINGS_FIX1_B4.md`: TRUE (the file exists with those ids).
- "a WebPage node's name is not a site name" (effect clause and limit 14): TRUE for the bytes (`_V2_SITE_NAME_TYPES = frozenset({"Organization", "WebSite"})`, url_extraction_service.py:241) but UNPINNED (P1).
- "`[URL-V2] fetch failed host=<h> reason=<r> type=<ExceptionType or None>` once per unreadable fetch: at ERROR for a transport error (`reason=fetch_error`, logged inside `_fetch_page_v2`'s except arm with the exception TYPE ...), at WARNING for a blocked hop, the redirect cap, a non-2xx or a challenge page (`type=None`)": TRUE (code :436-441 and :316-322, the log census above; M3/M4/M5/M5b killed). The blocked INITIAL url also takes the WARNING (the row's earlier sentence names it).
- "never the base `Failed to fetch URL host` ERROR template, which stays the one ERROR call with that prefix (the u8d R8 pin)": TRUE (u8d R8 141+131 green; M1/M2 killed by that pin).
- Limit 7 "(their image, and an LLM-merged one, is coerced in the normaliser: pinned by `test_normaliser_coerces_a_raw_image_list_flag_on`)": TRUE (M6 killed; the row drives the noon raw list, the amazon raw src and the LLM-merged list through `normalize_product_data(..., url_mode_v2=True)`).
- Limit 16: TRUE as written ("the five `url_compare_*` nodes ... closed by ... E5 ... and E6 ...: with the flag exported that file and the 20-file pin set of the GREEN report pass"; re-measured 21 passed and 1037 passed; M7 shows the five nodes go red without E6). Its last clause "no other file was measured with it set" is now superseded by this round: the five remaining URL-route readers pass with the flag exported (195 passed).
- Limit 17 (F4-5): TRUE (`asyncio.TimeoutError is TimeoutError` on the pinned 3.12.9; `_compare_with_deadline` catches it around the `wait_for` at url_routes.py:142-149 and logs the deadline WARNING; the inner `wait_for` in `extraction_service` :1384 sits inside an `except Exception` that degrades to "other"; `extract_from_url` exceptions are absorbed by `gather(..., return_exceptions=True)` in `compare_from_urls`).
- Unchanged GREEN sentences spot-checked against the bytes: the `[URL-V2] outcome=` vocabulary (ok|fetch_error|blocked|redirect_cap|http_error|challenge|not_product_page|unresolved, once per link), the three host-only v2 `[SSRF]` lines (TRUE, P2 shows unpinned), the `Detected retailer` label rule (TRUE, P3 shows unpinned), limit 10 (`fetch_page`'s `[SSRF]` lines still print the full url: TRUE), limit 11 (same_url keeps the port and path case: TRUE, url_extraction_service.py:136-155), limit 12 (the error handler reads the flag at response time: TRUE), limit 13 (`refund_comparison_credit(user_id)` without consumed_keys: TRUE), limit 15 (`classify_url_path` None for falsy / non-str: TRUE), "one env read per request in the route and one per error response": TRUE.

PR body (`B4_fix1/PR_BODY.md`, sha ea1a3ae4...):
- "What the flag does" Logs bullet: the ERROR / WARNING split, the u8d R8 statement and the host-only `[SSRF]` lines: TRUE (as above); no remaining WARNING wording for the transport-error line (grep of every "WARNING" occurrence).
- Defects table: node counts re-collected (253 nodes): pregate_homepage 12, pregate_field_and_reason 14, same_url 10, flag_reader_table_on 14, classify_url_path_table 34, non_delivery 16, flag_off_homepage 14, pdp_image 20 (10 x 2), the new row 1: all TRUE.
- RED-file sentence (c4549be2 -> 546fc27d, pure append, 253 nodes, LF, 0 bytes > 127): TRUE.
- E6 row ("no clean list", one-name autouse fixture in the `_clean_flags` shape of test_retro_w2_1.py:172-176): TRUE; "closes the measured local-.env class (its five url_compare_* nodes)": TRUE (M7).
- Fix round 1 F4-1 bullet ("exactly ONE record at ERROR, lexically inside its except arm ... R12 green ... u8d R8 pins stay green ... outside-except ERROR scan sees no new call ... other outcomes keep their WARNING"): TRUE (log census; u8d green; M4 shows the outside-except pin would catch a moved call).
- F4-2 bullet (four cases, both parse-offload states, LLM call counts 0 / 1, the G10 AssertionError text, "at base ... fails on its first line, the `_assert_kwarg` AssertionError"): TRUE, the last clause now MEASURED (base run above).
- F4-4 / F4-5 / F4-6 bullets: TRUE (D2 / D3 / D4 are stated; D3 is stated as the host-only `[SSRF]` lines); the commit trailer names Claude Opus 5.5 (D8 accepted by F4-6).
- Gates paragraph: every quoted [pyt] line is the fix agent's own; my re-runs above reproduce the same pass counts (253 / 253, 272 = 141 + 131, 21 / 21, 904, 1037, ruff 58 / 58).
- Owner step 3 Sentry sentence: TRUE from the code (sentry_service.py:651 `LoggingIntegration(level=logging.ERROR)`, no event_level, the T8 pin in test_auth_error_log_hygiene.py asserts the SDK default event level ERROR; OFF: `fetch_page`'s `raise_for_status` sends a non-2xx into the base ERROR line; ON: `_log_fetch_failed` WARNING). Not measured against a Sentry instance (as the body says).

## 5. Closure of the round's inputs (GREEN deviations D1-D9, questions Q1-Q5; no adversary has run on B4 yet, so there is no adversary MAJOR / MINOR to close)

| item | status | evidence |
|---|---|---|
| D1 / Q1 (R12 vs GC-1) | CLOSED by F4-1 | R12 green ON and OFF; u8d R8 green; M1-M5b killed |
| D2 (WebPage excluded) / Q4 | CLOSED as contract (F4-4), stated in the row; UNPINNED | P1 survives |
| D3 (host-only v2 `[SSRF]` lines) / Q4 | CLOSED as contract (F4-4), stated in the row; UNPINNED | P2 survives |
| D4 (retailer label) / Q4 | CLOSED as contract (F4-4), stated in the row; UNPINNED | P3 survives |
| D5 (normalize_product_data kwargs) | recorded (row: the four defaulted-kwarg signatures) | code |
| D6 (`_compare_with_deadline` helper) | recorded; semantics verified | M12 / deadline rows green |
| D7 (title regex, isinstance + tuple) | recorded | M8, M13 killed |
| D8 (trailer) | CLOSED (F4-6 accepted) | `git log -1`: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` |
| D9 (robot glyph) | recorded | PR body 4 bytes > 127 = that line only |
| Q2 (G10 survivor) | CLOSED by F4-2 | M6 killed |
| Q3 (E6) | CLOSED by F4-3 | meter ON/OFF 21/21; M7 killed |
| Q5 (inner TimeoutError) | CLOSED as stated limit 17 (F4-5) | code read (section 4) |
| fix X1 (E6 shape) | accepted | test_retro_w2_1 `_clean_flags` shape |
| fix X2 (u8d one call) | superseded | each file run ALONE here |
| fix X3 (no second full comm pass) | closed for this round's delta | 37-file delta set, 0 failures |
| fix X4 (base fail read, not run) | CLOSED, measured | base run: the `_assert_kwarg` AssertionError |
| fix X5 (trailer) | accepted (F4-6) | - |
| fix open Q1 (Sentry sentence only in the PR body) | open, MINOR below | - |

## 6. Findings

Blocking: none. Major: none.

Minor:
1. D2 / D3 / D4 are stated as contract in the CLAUDE.md row and the PR body (and D3 / D4 are security-relevant log hygiene that ships unflagged for D4), but no row pins them: P1, P2 and P3 each survive the full unit file. F4-4 accepted them without asking for pins, so this is not a defect of this round; for the two adversaries (GC-8 security lens owns D3 / D4): a `user:pass@` link row for the `Detected retailer` label, a host-only assertion on the v2 `[SSRF]` WARNING text (R41 matches the prefix only, test_s80_url_mode_v2.py:1485), and a WebPage-name-equals-title page that must not be refused at $0.
2. The Sentry consequence of F4-1 (ON: a link transport error is a Sentry event under the new `[URL-V2] fetch failed` template; a non-2xx moves from the base ERROR event to a WARNING) is in the PR body owner step 3 but not in the committed CLAUDE.md row (fix-report open Q1). Suggest one sentence in the row at the rebase.
3. CLAUDE.md limit 16's closing clause "no other file was measured with it set" is superseded by this round's measurement (the five remaining URL-route readers pass with the flag exported, 195 passed); optional wording update at the rebase.

## 7. NOT MEASURED

- tests/test_precommit_hook_phase_b.py and tests/test_precommit_hook_phase_b_round2.py (235 nodes): at the measured 24-29 s per node on the loaded box (`node -e 0` 2.60 s) they need about 100 minutes, past this agent's 90-minute budget; not started (no TIMEOUT, no partial run). Excluded from comm sets by rule (`.githooks` untouched).
- GREEN's G1-G5, G7-G9, G11, G12 were not re-run on these bytes; the eight new spec mutants M8-M15 and the F4 mutants M1-M7 were run instead (the F4-1 edit sits inside the except arm, outside every G-mutant snippet, as the fix report states).
- Any Sentry or live behaviour (the owner step-3 Sentry sentence is read from code); the post-rebase run (GC-7, orchestrator).
- The unit-file collect-only run's [pyt] line was discarded (stdout to /dev/null); it executed no test (253 nodes counted from its log).

## 8. End state

- Worktree: HEAD `96676f1fe9ddc4b4bc57e3e8aec166e4c7e26d4b`, `git status --short` empty, no `.qa-mutation.lock`; end hashes equal the start hashes (RED 546fc27d...8b46, service 0abf3b95...47c2, metering 4724c308...d73f, CLAUDE.md 8502da3b...c0ad, url_routes 9229e0b4...59ba, error_handler 7e539cc7...82).
- Scratch worktrees `B4_fix1_adv` (96676f1f) and `B4_fix1_base` (81df2b64) removed with `git worktree remove --force` (neither held a node_modules junction); `git worktree list` shows no B4_fix1 entry.
- No pytest process left (count 0 at 17:22).
- No `.env` read, copied or printed; no flag set outside a single runner call; no network.

## Verdict

SOUND. Blocking: none. Major: none. Minor: 3 (section 6). Every fix of the round (F4-1, F4-2, F4-3, the F4-4/F4-5/F4-6 docs) is present in the bytes, gated green (unit 253/253 ON and OFF, R8 272, metering 21/21 in both states, CI-order 904, delta comm 1086, flag-exported 1037 + 195, two hook files 92), and each code/test fix has a killed mutant (16/16 KILLED on AssertionError, sha-verified restores); the CLAUDE.md row and the PR body match the bytes sentence by sentence on every fix-round claim; GREEN D1-D9 and Q1-Q5 are closed or recorded.
