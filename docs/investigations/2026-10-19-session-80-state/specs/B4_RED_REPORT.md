# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- RED report (Fable RED agent, 2026-10-20)

- Unit: B4 URL-MODE-V2, flag `ENABLE_URL_MODE_V2` (default OFF, read per call).
- Real worktree: `C:\Users\SynAckITPC\Documents\AI\sc-s80-b4`, detached at base `81df2b641454e0301cca51a3ba01bf8ef3d7e649` (main has moved to cb80ea2f with B1; RED measured at the spec base per orchestrator note (b)).
- Inputs read in full: s80-common.txt (incl. the 2026-10-20 addendum), PLAN_S80.md sections 0-1 and the B4 unit text, RULINGS_R0.md, RULINGS_BATCH1.md "Common" G-1..G-4 and "B4 URL-MODE-V2" B4-R1..R11; spec `.qa-s80/B4_UNIT_SPEC.md` sha256 `fbb3cb8f0dd293f7ea421384f923779867a1d2da864c077e2e739923a0a0adfb`; review `.qa-s80/B4_SPEC_REVIEW.md` sha256 `c454ad16d713ec86964b570e84aade03501e117886943331dddc737c3d45f3cc`.
- Written in the real worktree: ONLY `tests/test_s80_url_mode_v2.py` (new, untracked; 0 bytes > 127, 0 CR). Notes folder `<scratchpad>/B4_red/`: notes.md, every runner log, the prototype patch `proto_patch.py`, the mutation driver `mutate.py` + `mutants.jsonl` + `mutation_table.md` + `mutants/*.log|.xml`, the comm list `comm_files.txt` + `comm_reasons.tsv` + `comm_chunk1..5.txt` + `comm_base_c1..5.log`, the base probe `probe_base.py` / `probe_base_out.json`.
- Personal data: none; synthetic ids built at run time (uuid4); fixture URLs are public store URLs or `*.test` hosts; no credential-shaped literal.

## 1. Step 2: the review's NOT-MEASURED files, each ALONE at base (G-3)

```
tests/test_retro_w2_1.py: 111 passed, 11 warnings in 3.83s; [hermeticity] sentinel checked 111 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4red-base-test_retro_w2_1 start=2026-10-20 12:19:34 end=2026-10-20 12:19:39 elapsed=6s bound=600s status=OK rc=0
tests/test_url_compare_category.py: 9 passed, 1 warning in 10.76s; sentinel 9; netguard 0
[pyt] tag=b4red-base-test_url_compare_category start=2026-10-20 12:19:41 end=2026-10-20 12:19:57 elapsed=15s bound=600s status=OK rc=0
tests/test_prompt_fence.py: 61 passed, 1 warning in 7.12s; sentinel 61; netguard 0
[pyt] tag=b4red-base-test_prompt_fence start=2026-10-20 12:20:00 end=2026-10-20 12:20:13 elapsed=13s bound=600s status=OK rc=0
tests/test_retro_w0_4.py: 157 passed in 142.12s; sentinel 157; netguard 0
[pyt] tag=b4red-base-test_retro_w0_4 start=2026-10-20 12:20:18 end=2026-10-20 12:22:43 elapsed=146s bound=600s status=OK rc=0
tests/test_ssrf_redirect_hardening.py: 5 passed in 3.40s; sentinel 5; netguard 0
[pyt] tag=b4red-base-test_ssrf_redirect_hardening start=2026-10-20 12:22:45 end=2026-10-20 12:22:51 elapsed=6s bound=600s status=OK rc=0
tests/test_s71_u13_compare_auth_required.py: 137 passed, 11 warnings in 26.24s; sentinel 137; netguard 0
[pyt] tag=b4red-base-test_s71_u13_compare_auth_required start=2026-10-20 12:22:55 end=2026-10-20 12:23:25 elapsed=30s bound=600s status=OK rc=0
tests/test_paid_route_metering.py: 21 passed, 13 warnings in 6.82s; sentinel 21
[netguard] blocked 2 attempt(s) from 2 node(s) (pre-existing: ::test_camera_success_consumes_once_and_never_refunds and ::test_url_compare_saves_history_with_input_type_url, socket.create_connection neutralized.supabase.invalid:443)
[pyt] tag=b4red-base-test_paid_route_metering start=2026-10-20 12:23:26 end=2026-10-20 12:23:35 elapsed=8s bound=600s status=OK rc=0
tests/test_w4_13_measurement_truth.py: 219 passed, 11 warnings in 19.63s; sentinel 219; netguard 0
[pyt] tag=b4red-base-test_w4_13_measurement_truth start=2026-10-20 12:23:39 end=2026-10-20 12:24:03 elapsed=24s bound=600s status=OK rc=0
tests/test_model_config_enforced.py: 27 passed, 1 warning in 6.12s; sentinel 27; netguard 0
[pyt] tag=b4red-base-test_model_config_enforced start=2026-10-20 12:24:05 end=2026-10-20 12:24:13 elapsed=8s bound=600s status=OK rc=0
```

All nine green at base; `git status --short` empty after.

## 2. The RED file at base (real worktree)

`tests/test_s80_url_mode_v2.py`: 252 nodes = 206 RED + 46 PIN.

Final run (the frozen file, sha256 `c4549be2f5cd8edfd60cbc07db427ed5275cc4b44ab719614ef97b9eca227cae`, 71,891 bytes):
```
206 failed, 46 passed, 11 warnings in 16.97s
[hermeticity] sentinel checked 252 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4red-unit-base-final start=2026-10-20 13:35:17 end=2026-10-20 13:35:39 elapsed=22s bound=600s status=FAIL rc=1
```
Earlier iterations (same counts): `[pyt] tag=b4red-unit-base1 ... elapsed=15s status=FAIL rc=1` (208/44 before the P25 fix), `[pyt] tag=b4red-unit-base2 start=2026-10-20 12:39:07 end=2026-10-20 12:39:22 elapsed=15s bound=600s status=FAIL rc=1` (206/46), `[pyt] tag=b4red-unit-base3 start=2026-10-20 12:47:44 end=2026-10-20 12:48:04 elapsed=20s bound=600s status=FAIL rc=1` (206/46). Failed node ids: `<scratchpad>/B4_red/unit_base_final.xml` (and `unit_base3.xml.failed.txt`).

Every failure is an AssertionError: the failure-site lines of the log read `tests\test_s80_url_mode_v2.py:<n>: AssertionError` 206 times and nothing else; the junit xml carries 0 `<error>` elements (no setup/import error). Missing symbols are read with `getattr` / `inspect.signature` (`_fn`, `_const`, `_assert_kwarg`) and asserted; no route row can reach the network (the httpx transport is a MockTransport injected into every `httpx.AsyncClient` the module builds AND set on `url_extraction_service._TRANSPORT`; the SSRF validator `app.utils.url_validator.validate_external_url` is a recording fake), so at base the RED route rows exercise the REAL base behaviour (base `fetch_page` over the mock transport) and fail on the observed body / status / ledger.

RED nodes (function(count)): test_both_urls_403_field_both(2) test_challenge_page_is_store_unreadable(2) test_classify_url_path_table(34) test_copy_constants_verbatim_and_policy_clean(1) test_deadline_yields_timeout_503(2) test_error_handler_passthrough_on(3) test_error_handler_reader_table(14) test_fetch_page_v2_blocks_private_initial_url(1) test_fetch_page_v2_blocks_redirect_to_metadata(1) test_fetch_page_v2_caps_redirect_chain(1) test_fetch_page_v2_keeps_status_and_final_url(1) test_flag_reader_table_on(14) test_info_line_survives_a_malformed_url(1) test_info_lines_print_host_only(1) test_is_usable_title_table(1) test_llm_answers_on_a_usable_title_page(4) test_mixed_codes_precedence(2) test_mixed_codes_precedence_not_product_page_over_unresolved(2) test_never_unknown_product_flag_on(3) test_node_bearing_page_with_llm_false_delivers(1) test_non_2xx_reason_table(4) test_non_delivery_per_r_a3_every_code(16) test_normalize_url_table(1) test_null_name_only_when_the_title_is_unusable(1) test_pdp_image_is_first_https_string(20) test_pregate_field_and_reason(14) test_pregate_homepage_pair_refused_before_reserve(12) test_pregate_same_url_after_normalisation(10) test_pregate_writes_no_search_log_row(2) test_prompt_v2_asks_is_product_page_and_keeps_shape(1) test_prompt_v2_is_derived_from_v1(1) test_recommendation_and_key_differences_filled(2) test_recommendation_fallback_when_reason_leaks_scores(2) test_redirect_to_homepage_is_not_product_page_post_fetch(2) test_route_fetch_blocked_or_capped_is_store_unreadable(4) test_service_flag_reader_table(14) test_test_seams_have_production_values(1) test_transport_error_is_store_unreadable(2) test_v02_fragrancex_403_is_store_unreadable(2) test_v09_storefront_pages_unresolved(2) test_v2_kwarg_is_conditional[*-on](2).

PIN nodes (46, green at base, every flag-OFF one under the FULL configuration of ruling B1: metering ON, search-log truth ON, an authed user, the transport, the LLM fake, the verdict fake, the ledger, plus a raising pre-gate stand-in / a call recorder where it matters): test_pregate_lets_distinct_pdps_through[POST|GET] (P4); test_ssrf_refusal_byte_identical_in_both_states[4] (P5, homepage pair per C10); test_flag_off_homepage_pair_is_base_behaviour[14] (P6, seven OFF spellings x two verbs); test_body_text_access_denied_is_not_a_challenge[2] (R11b, the M15 body-substring pin); test_codeless_failure_keeps_base_body_flag_on[2] (P15); test_flag_off_no_deadline[2] (P17); test_deadline_exception_arm_untouched[2] (P18); test_flag_off_image_passes_through_raw[env-unset|env-true] (P20); test_flag_off_recommendation_empty[2] (P23); test_prompt_off_render_equals_w411_digest[2] (P25, amended, D1); test_error_handler_four_key_body[5] (R32 OFF half + B4-R5 scope); test_w4_13_rows_unchanged_flag_off[None|false|garbage] + test_w4_13_rows_full_config_flag_off (P36); test_v2_kwarg_is_conditional[*-off] (R38 OFF half); test_fetch_page_untouched_pin (R39, base source sha `34dd74c6...8655` confirmed by probe).

Spec-row mapping and the rulings applied: R1-R3, P4-P6, R7 (+ the service reader table), R8-R14 (+ R14b NOT_PRODUCT_PAGE > UNRESOLVED), P15, R16-P18, R19 (10 image cases x both ENABLE_PRICE_PARSE_OFFLOAD states, B4-R10 Q7; inline pages carry no og:image except the og rows and the LLM returns no image_url, C20; plus an og-image-joined-on-the-FINAL-url case), P20, R21-P23, R24-R26, R27 rewritten per B4-R1 (usable title: `is_product_page:false` -> UNRESOLVED/not_product_page; `name:null`, `{}`, offline -> DELIVERY with name == title), R43 (node-bearing page + LLM false -> delivery, B4-R1), R44 (null_name only when the title is unusable), R28 per C8 (no_product_node, `llm_calls == []`), the C19 status table (403/404/500/302-without-Location -> http_403/http_4xx/http_5xx/http_3xx), R29 with the B4-R7 misses pinned as current behaviour (`/ar/search`, `/s`, `/uae-en/search/`, `/uae-en/`, `/uae-en`, `/eng/`, `/en/cart.html` -> None), R30 with B4-R4 (`http://[`, `https://a.test:99999/x` -> ''), R31, R32 scoped to the three B4 codes (B4-R5: an INSUFFICIENT_DATA detail carrying field/reason stays four-key under ON), R33, R34 (+ the malformed-url row, B4-R4), R35 (code asserted, both metering states), P36, R37, R38, R39, R40-R42 (+ R42b: status/final_url kept, 403 kept with no raise) and the route rows for blocked hop / redirect cap (B4-R3, mandatory). Every fake installed on `url_routes.compare_from_urls` / `url_extraction_service.extract_from_url` accepts `**kwargs` (C15). UNIT_ENV is deleted by an autouse fixture (spec list + ENABLE_LLM_PREFLIGHT_BREAKER, ENABLE_SYNC_DB_OFFLOAD, ENABLE_ANON_USAGE_GATE, SEARCH_LOG_SYNTHETIC_TOKEN, every OPENAI_MODEL_*); the limiter is disabled per test and `app.dependency_overrides` restored.

## 3. Prototype (scratch worktree `<scratchpad>/B4_red/b4_scratch`, detached at 81df2b64; thrown away)

Change list implemented quickly by `proto_patch.py` (exact-string edits) on `app/services/url_extraction_service.py`, `app/api/url_routes.py`, `app/middleware/error_handler.py` (the clear-list edits E1-E4 and CLAUDE.md were not prototyped). Prototype shas (after the mutation restores, re-verified OK): ues `5d22c6c1...`, url_routes `0b123f58...`, error_handler `9068515a...`, RED file `c4549be2...`.

```
ENABLE_URL_MODE_V2=true exported:
252 passed, 11 warnings in 13.45s; [hermeticity] sentinel checked 252 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4red-proto-on2 start=2026-10-20 12:46:57 end=2026-10-20 12:47:12 elapsed=15s bound=600s status=OK rc=0
flag unset:
252 passed, 11 warnings in 13.36s; sentinel 252; netguard 0
[pyt] tag=b4red-proto-off start=2026-10-20 12:47:15 end=2026-10-20 12:47:30 elapsed=15s bound=600s status=OK rc=0
final file (c4549be2...), after the 63 mutant restores:
252 passed, 11 warnings in 11.24s; sentinel 252; netguard 0
[pyt] tag=b4red-proto-on-final start=2026-10-20 13:35:41 end=2026-10-20 13:35:54 elapsed=13s bound=600s status=OK rc=0
252 passed, 11 warnings in 13.92s; sentinel 252; netguard 0
[pyt] tag=b4red-proto-off-final start=2026-10-20 13:35:57 end=2026-10-20 13:36:17 elapsed=19s bound=600s status=OK rc=0
```
(The rows set or delete the flag themselves, so both runner states run the same assertions: all RED rows green, all PIN rows green, flag-OFF identity rows green.)

Existing pins against the prototype (one call): `tests/test_retro_w2_1.py tests/test_prompt_fence.py tests/test_url_compare_category.py tests/test_model_config_enforced.py tests/test_u3c_store_false_pin.py tests/test_sentry_channels_u8d_unit.py tests/test_ssrf_redirect_hardening.py tests/test_w4_13_flag_off_ledger.py tests/test_retro_w0_4_efg.py tests/test_retro_w0_4.py::test_w04c_no_async_def_reaches_a_soup_helper_inline`:
```
1 failed, 508 passed, 11 warnings in 51.34s; [hermeticity] sentinel checked 509 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
FAILED tests/test_sentry_channels_u8d_unit.py::TestR8SourceLines::test_u8d_red_r8_in_except_lines_no_user_content[url_extraction_fetch_failed]
[pyt] tag=b4red-proto-pins start=2026-10-20 12:48:23 end=2026-10-20 12:49:16 elapsed=54s bound=600s status=FAIL rc=1
```
What the spec got wrong (found by the prototype), see section 6: S1 (the R8 single-call pin), S2 (P25 fixture key), S3 (R24 region count). The W0-4c transitive soup guard stayed green with the B4-R2 shape (regex title read, `nodes_present` / `site_names` computed inside the offloaded `extract_generic_data_v2`, the only inline shape `if _price_parse_offload_enabled(): await run_parse_offloaded(...) else: fn(...)`).

## 4. Mutation table (63 mutants: spec M1-M49 incl. review M48/M49, plus 14 sub-mutants; each on a byte copy of the prototype, exact-string edit matching once, the whole RED file through pyt.py `--bound 600`, restored and sha256-compared; lock `<scratch>/.qa-mutation.lock` created and removed)

Result: **63 / 63 KILLED, every kill an AssertionError, 0 survivors, 0 equivalent.** Full table with every [pyt] line: `<scratchpad>/B4_red/mutation_table.md` (per-mutant logs and junit xml in `mutants/`).

| # | mutant | result | failed nodes | first killing rows | [pyt] |
|---|---|---|---|---|---|
| M1 | pre-gate runs with the flag read removed (always ON) | KILLED (AssertionError) | 20 | test_flag_off_homepage_pair_is_base_behaviour[POST-None]; test_flag_off_homepage_pair_is_base_behaviour[POST-]; test_flag_off_homepage_pair_is_base_behaviour[POST-false] | tag=b4red-mut-M1 elapsed=10s status=FAIL rc=1 |
| M2 | service reader == 'true' (no strip/lower/set) | KILLED (AssertionError) | 18 | test_service_flag_reader_table[TRUE]; test_service_flag_reader_table[ true ]; test_service_flag_reader_table[1] | tag=b4red-mut-M2 elapsed=11s status=FAIL rc=1 |
| M2b | error-handler reader == 'true' (no strip/lower/set) | KILLED (AssertionError) | 6 | test_error_handler_reader_table[TRUE]; test_error_handler_reader_table[ true ]; test_error_handler_reader_table[1] | tag=b4red-mut-M2b elapsed=10s status=FAIL rc=1 |
| M3 | pre-gate placed BEFORE the SSRF check (POST) | KILLED (AssertionError) | 7 | test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/?gclid=abc123] | tag=b4red-mut-M3 elapsed=11s status=FAIL rc=1 |
| M4 | pre-gate inside _compare_urls_metered after the reserve | KILLED (AssertionError) | 36 | test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/?gclid=abc123] | tag=b4red-mut-M4 elapsed=13s status=FAIL rc=1 |
| M5a | classify ignores the homepage regex | KILLED (AssertionError) | 31 | test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/?gclid=abc123] | tag=b4red-mut-M5a elapsed=17s status=FAIL rc=1 |
| M5b | classify ignores the search regex | KILLED (AssertionError) | 7 | test_pregate_field_and_reason[POST-url1-search]; test_pregate_field_and_reason[POST-both-home-search]; test_pregate_field_and_reason[GET-url1-search] | tag=b4red-mut-M5b elapsed=13s status=FAIL rc=1 |
| M5c | classify ignores the cart regex | KILLED (AssertionError) | 7 | test_pregate_field_and_reason[POST-url1-cart]; test_pregate_field_and_reason[POST-url1-checkout]; test_pregate_field_and_reason[GET-url1-cart] | tag=b4red-mut-M5c elapsed=17s status=FAIL rc=1 |
| M5d | classify ignores the account regex | KILLED (AssertionError) | 5 | test_pregate_field_and_reason[POST-url1-account]; test_pregate_field_and_reason[GET-url1-account]; test_classify_url_path_table[/account-account] | tag=b4red-mut-M5d elapsed=10s status=FAIL rc=1 |
| M5e | classify ignores the category regex | KILLED (AssertionError) | 6 | test_pregate_field_and_reason[POST-url1-category]; test_pregate_field_and_reason[GET-url1-category]; test_classify_url_path_table[/collections/men-category] | tag=b4red-mut-M5e elapsed=11s status=FAIL rc=1 |
| M6 | category rule fires on a product segment | KILLED (AssertionError) | 1 | test_classify_url_path_table[/collections/men/products/sauvage-None] | tag=b4red-mut-M6 elapsed=15s status=FAIL rc=1 |
| M7 | same_url compares raw strings | KILLED (AssertionError) | 8 | test_pregate_same_url_after_normalisation[POST-slash]; test_pregate_same_url_after_normalisation[POST-case-host]; test_pregate_same_url_after_normalisation[POST-no-www] | tag=b4red-mut-M7 elapsed=14s status=FAIL rc=1 |
| M8 | same_url treats two '' as equal | KILLED (AssertionError) | 1 | test_normalize_url_table | tag=b4red-mut-M8 elapsed=14s status=FAIL rc=1 |
| M9a | pre-gate field always both | KILLED (AssertionError) | 12 | test_pregate_field_and_reason[POST-url2-home]; test_pregate_field_and_reason[POST-url1-search]; test_pregate_field_and_reason[POST-url1-cart] | tag=b4red-mut-M9a elapsed=13s status=FAIL rc=1 |
| M9b | post-fetch field always both | KILLED (AssertionError) | 12 | test_v02_fragrancex_403_is_store_unreadable[POST]; test_v02_fragrancex_403_is_store_unreadable[GET]; test_challenge_page_is_store_unreadable[POST] | tag=b4red-mut-M9b elapsed=13s status=FAIL rc=1 |
| M10a | refusal detail drops field/reason | KILLED (AssertionError) | 56 | test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/?gclid=abc123] | tag=b4red-mut-M10a elapsed=12s status=FAIL rc=1 |
| M10b | error-handler passthrough removed | KILLED (AssertionError) | 59 | test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/?gclid=abc123] | tag=b4red-mut-M10b elapsed=13s status=FAIL rc=1 |
| M11 | passthrough with the flag OFF | KILLED (AssertionError) | 1 | test_error_handler_four_key_body[off-b4-code-keys] | tag=b4red-mut-M11 elapsed=12s status=FAIL rc=1 |
| M11b | passthrough not scoped to the three codes | KILLED (AssertionError) | 1 | test_error_handler_four_key_body[on-other-code-keys] | tag=b4red-mut-M11b elapsed=10s status=FAIL rc=1 |
| M12 | passthrough copies a non-str value | KILLED (AssertionError) | 3 | test_error_handler_passthrough_on[NOT_PRODUCT_PAGE]; test_error_handler_passthrough_on[STORE_UNREADABLE]; test_error_handler_passthrough_on[UNRESOLVED_PRODUCT] | tag=b4red-mut-M12 elapsed=10s status=FAIL rc=1 |
| M13 | _fetch_page_v2 calls raise_for_status | KILLED (AssertionError) | 11 | test_v02_fragrancex_403_is_store_unreadable[POST]; test_v02_fragrancex_403_is_store_unreadable[GET]; test_both_urls_403_field_both[POST] | tag=b4red-mut-M13 elapsed=14s status=FAIL rc=1 |
| M14 | 2xx check accepts 3xx/4xx (status < 500) | KILLED (AssertionError) | 13 | test_v02_fragrancex_403_is_store_unreadable[POST]; test_v02_fragrancex_403_is_store_unreadable[GET]; test_both_urls_403_field_both[POST] | tag=b4red-mut-M14 elapsed=10s status=FAIL rc=1 |
| M15a | challenge = body substring | KILLED (AssertionError) | 2 | test_body_text_access_denied_is_not_a_challenge[POST]; test_body_text_access_denied_is_not_a_challenge[GET] | tag=b4red-mut-M15a elapsed=31s status=FAIL rc=1 |
| M15b | challenge check removed | KILLED (AssertionError) | 2 | test_challenge_page_is_store_unreadable[POST]; test_challenge_page_is_store_unreadable[GET] | tag=b4red-mut-M15b elapsed=26s status=FAIL rc=1 |
| M16 | post-fetch final-url check removed | KILLED (AssertionError) | 8 | test_redirect_to_homepage_is_not_product_page_post_fetch[POST]; test_redirect_to_homepage_is_not_product_page_post_fetch[GET]; test_mixed_codes_precedence_not_product_page_over_unresolved[POST] | tag=b4red-mut-M16 elapsed=34s status=FAIL rc=1 |
| M17 | exact @type == Product (no shape ladder) | KILLED (AssertionError) | 6 | test_pdp_image_is_first_https_string[graph-parse-off]; test_pdp_image_is_first_https_string[graph-parse-on]; test_pdp_image_is_first_https_string[has_variant-parse-off] | tag=b4red-mut-M17 elapsed=23s status=FAIL rc=1 |
| M18 | is_usable_title ignores site_names | KILLED (AssertionError) | 11 | test_v09_storefront_pages_unresolved[POST]; test_v09_storefront_pages_unresolved[GET]; test_mixed_codes_precedence[POST] | tag=b4red-mut-M18 elapsed=37s status=FAIL rc=1 |
| M19 | is_usable_title accepts 'Unknown Product' | KILLED (AssertionError) | 1 | test_is_usable_title_table | tag=b4red-mut-M19 elapsed=25s status=FAIL rc=1 |
| M20 | no-LLM short-circuit removed | KILLED (AssertionError) | 5 | test_v09_storefront_pages_unresolved[POST]; test_v09_storefront_pages_unresolved[GET]; test_never_unknown_product_flag_on[name_null] | tag=b4red-mut-M20 elapsed=66s status=FAIL rc=1 |
| M21 | is_product_page false ignored | KILLED (AssertionError) | 1 | test_llm_answers_on_a_usable_title_page[not_product_page] | tag=b4red-mut-M21 elapsed=32s status=FAIL rc=1 |
| M21b | is_product_page false refuses a node-bearing page | KILLED (AssertionError) | 1 | test_node_bearing_page_with_llm_false_delivers | tag=b4red-mut-M21b elapsed=23s status=FAIL rc=1 |
| M22 | null_name check removed (falls to the empty title) | KILLED (AssertionError) | 1 | test_null_name_only_when_the_title_is_unusable | tag=b4red-mut-M22 elapsed=17s status=FAIL rc=1 |
| M22b | null_name refuses a usable-title page whose LLM name is null | KILLED (AssertionError) | 4 | test_llm_answers_on_a_usable_title_page[name_null]; test_llm_answers_on_a_usable_title_page[empty]; test_llm_answers_on_a_usable_title_page[offline] | tag=b4red-mut-M22b elapsed=20s status=FAIL rc=1 |
| M23a | normalize_image_url without the https check | KILLED (AssertionError) | 2 | test_pdp_image_is_first_https_string[http_only-parse-off]; test_pdp_image_is_first_https_string[http_only-parse-on] | tag=b4red-mut-M23a elapsed=12s status=FAIL rc=1 |
| M23b | normalize_image_url without urljoin | KILLED (AssertionError) | 6 | test_pdp_image_is_first_https_string[og_fallback_relative-parse-off]; test_pdp_image_is_first_https_string[og_fallback_relative-parse-on]; test_pdp_image_is_first_https_string[og_joined_on_final_url-parse-off] | tag=b4red-mut-M23b elapsed=17s status=FAIL rc=1 |
| M24 | og fallback keeps the key-presence test | KILLED (AssertionError) | 4 | test_pdp_image_is_first_https_string[og_fallback_relative-parse-off]; test_pdp_image_is_first_https_string[og_fallback_relative-parse-on]; test_pdp_image_is_first_https_string[og_joined_on_final_url-parse-off] | tag=b4red-mut-M24 elapsed=23s status=FAIL rc=1 |
| M24b | og image joined against the requested url, not the final url | KILLED (AssertionError) | 2 | test_pdp_image_is_first_https_string[og_joined_on_final_url-parse-off]; test_pdp_image_is_first_https_string[og_joined_on_final_url-parse-on] | tag=b4red-mut-M24b elapsed=15s status=FAIL rc=1 |
| M25 | image_url stays raw ON | KILLED (AssertionError) | 8 | test_pdp_image_is_first_https_string[http_only-parse-off]; test_pdp_image_is_first_https_string[http_only-parse-on]; test_pdp_image_is_first_https_string[image_object-parse-off] | tag=b4red-mut-M25 elapsed=28s status=FAIL rc=1 |
| M26 | image_url normalised OFF too | KILLED (AssertionError) | 2 | test_flag_off_image_passes_through_raw[env-unset]; test_flag_off_image_passes_through_raw[env-true] | tag=b4red-mut-M26 elapsed=18s status=FAIL rc=1 |
| M27 | recommendation without strip_score_internals | KILLED (AssertionError) | 2 | test_recommendation_fallback_when_reason_leaks_scores[POST]; test_recommendation_fallback_when_reason_leaks_scores[GET] | tag=b4red-mut-M27 elapsed=16s status=FAIL rc=1 |
| M28 | qualitative fallback dropped | KILLED (AssertionError) | 2 | test_recommendation_fallback_when_reason_leaks_scores[POST]; test_recommendation_fallback_when_reason_leaks_scores[GET] | tag=b4red-mut-M28 elapsed=21s status=FAIL rc=1 |
| M29 | key_differences includes the similar list | KILLED (AssertionError) | 2 | test_recommendation_and_key_differences_filled[POST]; test_recommendation_and_key_differences_filled[GET] | tag=b4red-mut-M29 elapsed=20s status=FAIL rc=1 |
| M30 | a new top-level key on the delivery dict | KILLED (AssertionError) | 2 | test_recommendation_and_key_differences_filled[POST]; test_recommendation_and_key_differences_filled[GET] | tag=b4red-mut-M30 elapsed=10s status=FAIL rc=1 |
| M31 | value fill applied OFF | KILLED (AssertionError) | 16 | test_flag_off_homepage_pair_is_base_behaviour[POST-None]; test_flag_off_homepage_pair_is_base_behaviour[POST-]; test_flag_off_homepage_pair_is_base_behaviour[POST-false] | tag=b4red-mut-M31 elapsed=19s status=FAIL rc=1 |
| M32 | V1 prompt edited in place (V1 == V2) | KILLED (AssertionError) | 3 | test_prompt_off_render_equals_w411_digest[env-unset]; test_prompt_off_render_equals_w411_digest[env-true]; test_prompt_v2_is_derived_from_v1 | tag=b4red-mut-M32 elapsed=14s status=FAIL rc=1 |
| M33 | V2 drops the URL line | KILLED (AssertionError) | 2 | test_prompt_v2_asks_is_product_page_and_keeps_shape; test_prompt_v2_is_derived_from_v1 | tag=b4red-mut-M33 elapsed=17s status=FAIL rc=1 |
| M34 | V2 selected OFF | KILLED (AssertionError) | 2 | test_prompt_off_render_equals_w411_digest[env-unset]; test_prompt_off_render_equals_w411_digest[env-true] | tag=b4red-mut-M34 elapsed=15s status=FAIL rc=1 |
| M35 | wait_for removed | KILLED (AssertionError) | 6 | test_deadline_yields_timeout_503[POST]; test_deadline_yields_timeout_503[GET]; test_non_delivery_per_r_a3_every_code[POST-TIMEOUT-meter-on] | tag=b4red-mut-M35 elapsed=32s status=FAIL rc=1 |
| M36 | timeout arm re-raises | KILLED (AssertionError) | 6 | test_deadline_yields_timeout_503[POST]; test_deadline_yields_timeout_503[GET]; test_non_delivery_per_r_a3_every_code[POST-TIMEOUT-meter-on] | tag=b4red-mut-M36 elapsed=12s status=FAIL rc=1 |
| M37 | timeout result lacks the code | KILLED (AssertionError) | 6 | test_deadline_yields_timeout_503[POST]; test_deadline_yields_timeout_503[GET]; test_non_delivery_per_r_a3_every_code[POST-TIMEOUT-meter-on] | tag=b4red-mut-M37 elapsed=14s status=FAIL rc=1 |
| M38 | TIMEOUT routed through _raise_url_refusal (400) | KILLED (AssertionError) | 6 | test_deadline_yields_timeout_503[POST]; test_deadline_yields_timeout_503[GET]; test_non_delivery_per_r_a3_every_code[POST-TIMEOUT-meter-on] | tag=b4red-mut-M38 elapsed=18s status=FAIL rc=1 |
| M39 | coded url failures through _surface_comparison_failure (field lost) | KILLED (AssertionError) | 20 | test_v09_storefront_pages_unresolved[POST]; test_v09_storefront_pages_unresolved[GET]; test_v02_fragrancex_403_is_store_unreadable[POST] | tag=b4red-mut-M39 elapsed=22s status=FAIL rc=1 |
| M40 | codeless arm replaced by a coded body | KILLED (AssertionError) | 2 | test_codeless_failure_keeps_base_body_flag_on[POST]; test_codeless_failure_keeps_base_body_flag_on[GET] | tag=b4red-mut-M40 elapsed=38s status=FAIL rc=1 |
| M41 | precedence inverted | KILLED (AssertionError) | 4 | test_mixed_codes_precedence[POST]; test_mixed_codes_precedence[GET]; test_mixed_codes_precedence_not_product_page_over_unresolved[POST] | tag=b4red-mut-M41 elapsed=31s status=FAIL rc=1 |
| M42 | v2 kwarg passed OFF | KILLED (AssertionError) | 16 | test_flag_off_homepage_pair_is_base_behaviour[POST-None]; test_flag_off_homepage_pair_is_base_behaviour[POST-]; test_flag_off_homepage_pair_is_base_behaviour[POST-false] | tag=b4red-mut-M42 elapsed=20s status=FAIL rc=1 |
| M43 | INFO request line keeps the full url | KILLED (AssertionError) | 2 | test_info_lines_print_host_only; test_info_line_survives_a_malformed_url | tag=b4red-mut-M43 elapsed=37s status=FAIL rc=1 |
| M43b | Detected-retailer line keeps the full url | KILLED (AssertionError) | 1 | test_info_lines_print_host_only | tag=b4red-mut-M43b elapsed=44s status=FAIL rc=1 |
| M44 | refund skipped for a new code | KILLED (AssertionError) | 20 | test_v09_storefront_pages_unresolved[POST]; test_v09_storefront_pages_unresolved[GET]; test_v02_fragrancex_403_is_store_unreadable[POST] | tag=b4red-mut-M44 elapsed=38s status=FAIL rc=1 |
| M45 | success-branch lifetime bump reached for a new code | KILLED (AssertionError) | 22 | test_v09_storefront_pages_unresolved[POST]; test_v09_storefront_pages_unresolved[GET]; test_v02_fragrancex_403_is_store_unreadable[POST] | tag=b4red-mut-M45 elapsed=40s status=FAIL rc=1 |
| M46 | search_logs row written for a pre-gate refusal (POST) | KILLED (AssertionError) | 7 | test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com]; test_pregate_homepage_pair_refused_before_reserve[POST-https://www.fragrancex.com/?gclid=abc123] | tag=b4red-mut-M46 elapsed=20s status=FAIL rc=1 |
| M47 | fetch_page body edited | KILLED (AssertionError) | 1 | test_fetch_page_untouched_pin | tag=b4red-mut-M47 elapsed=29s status=FAIL rc=1 |
| M48 | _fetch_page_v2 per-hop validation removed | KILLED (AssertionError) | 3 | test_route_fetch_blocked_or_capped_is_store_unreadable[POST-blocked_hop-blocked]; test_route_fetch_blocked_or_capped_is_store_unreadable[GET-blocked_hop-blocked]; test_fetch_page_v2_blocks_redirect_to_metadata | tag=b4red-mut-M48 elapsed=36s status=FAIL rc=1 |
| M49 | _fetch_page_v2 hop bound removed | KILLED (AssertionError) | 3 | test_route_fetch_blocked_or_capped_is_store_unreadable[POST-redirect_cap-redirect_cap]; test_route_fetch_blocked_or_capped_is_store_unreadable[GET-redirect_cap-redirect_cap]; test_fetch_page_v2_caps_redirect_chain | tag=b4red-mut-M49 elapsed=18s status=FAIL rc=1 |

## 5. Comm set at base (real worktree, union rule)

List `<scratchpad>/B4_red/comm_files.txt` (119 files, sha256 `84b1f89b5f4c5be0bbb6638077ba7d91a72bbc6776512ea60f41797d8bb31151`), per-file reasons `comm_reasons.tsv`. Union = the spec section-7 95-file list (sha `698ad35e...`) UNION the module/symbol grep `url_routes|url_extraction_service|error_handler` (35) UNION the SmartCompareApp-scanning tests (25) UNION every test importing the EDITED test-support module `tests/w4_11_prompt_digest_recorder.py` (E2; the 2026-10-20 addendum: adds `tests/test_price_fallback_may_decline.py`, `tests/test_prompt_truth.py`) UNION the W4-13 url-envelope pins (`tests/test_w4_13_flag_off_ledger.py`, `tests/test_m18_preverdict_disconnect_refund.py`) UNION the source-scanning grep (74) UNION the named s80-common pins UNION the CLAUDE.md readers. EXCLUDED: the precommit hook files (`test_precommit_hook.py`, `_phase_b.py`, `_phase_b_round2.py`), `tests/test_rate_limiting_complete.py` (NETWORK_FLAKY_EXCLUDE, never matched), the RED file itself (fails by design at base; GREEN adds it at HEAD), the non-test module `tests/w4_11_prompt_digest_recorder.py`.

Base runs (real worktree, one process at a time, `--bound 1200`):
```
c1: 890 passed, 1 skipped, 12 deselected, 13 warnings in 55.13s; [hermeticity] sentinel checked 891 test(s); [netguard] blocked 2 attempt(s) from 2 node(s)
[pyt] tag=b4red-comm-base-c1 start=2026-10-20 13:16:52 end=2026-10-20 13:17:49 elapsed=57s bound=1200s status=OK rc=0
c2: 2146 passed, 1 skipped, 18 warnings in 377.01s; [hermeticity] sentinel checked 2147 test(s); [netguard] blocked 58 attempt(s) from 39 node(s)
[pyt] tag=b4red-comm-base-c2 start=2026-10-20 13:17:53 end=2026-10-20 13:24:12 elapsed=380s bound=1200s status=OK rc=0
c3: 682 passed, 2 skipped, 8 deselected, 1 xfailed, 13 warnings, 2 errors in 133.64s; [hermeticity] sentinel checked 685 test(s); [netguard] blocked 123 attempt(s) from 8 node(s)
[pyt] tag=b4red-comm-base-c3 start=2026-10-20 13:24:22 end=2026-10-20 13:26:41 elapsed=139s bound=1200s status=FAIL rc=1
c4: 1622 passed, 1 skipped, 1 deselected, 15 warnings in 381.93s; [hermeticity] sentinel checked 1623 test(s); [netguard] blocked 12 attempt(s) from 6 node(s)
[pyt] tag=b4red-comm-base-c4 start=2026-10-20 13:26:49 end=2026-10-20 13:33:15 elapsed=386s bound=1200s status=OK rc=0
c5: 615 passed, 1 skipped, 13 warnings in 97.13s; [hermeticity] sentinel checked 616 test(s); [netguard] blocked 27 attempt(s) from 23 node(s)
[pyt] tag=b4red-comm-base-c5 start=2026-10-20 13:33:21 end=2026-10-20 13:35:06 elapsed=104s bound=1200s status=OK rc=0
```
Base FAILED/ERROR set (`comm_base_failed.txt`): exactly the two expected environmental nodes (cold tiktoken cache, s80-common): `tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence`, `tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable` (ERROR). Every netguard block is a pre-existing `[sentinel] ... neutralized.supabase.invalid:443` / egress-baseline node (none from a URL-mode file). GREEN re-derives the list at HEAD (adding the RED file and `test_s80_url_mode_v2.py` importers) and diffs head vs this base set.

## 6. Deviations from the spec (rows changed, never silently)

- D1 (P25): the spec asserts `sha256(message) == FIXTURE["url_extract_user"]`. Wrong at base: that fixture key is the PRE-fence render (recorded at 61585c58; `tests/w4_11_prompt_digest_recorder.py` says these digests MUST move when the W4-11 fences land), so the base OFF render (`65edcacae42a8287a66e784f3d963eb41fba80b0219caae25fe10bef2c853a66`, measured at 81df2b64 with the recorder's exact url/html/retailer/answer) does not equal it. P25 pins the base-measured digest + the fixture's `url_extract_kwargs` ({gpt-4o-mini, 800, 0.1, store False}, unchanged), and is parametrised over env unset/"true" (the service reads no env).
- D2 (R24): "exactly ONE `<SEARCH_RESULTS>` open" is unsatisfiable literally: `SEARCH_RESULTS_GUARD` itself names the tag (measured: opens at offsets 26 and 376). R24 counts the region AFTER the guard (the F13 reading, `opens[-1]`): exactly one open and one close in the body, the `URL:` line before the open.
- D3 (R12): the spec pins the base ERROR template `Failed to fetch URL host %s: %s` reused by `_fetch_page_v2`. A second call site with that prefix reddens `tests/test_sentry_channels_u8d_unit.py::TestR8SourceLines::...[url_extraction_fetch_failed]` (asserts exactly ONE ERROR call with prefix `Failed to fetch` in url_extraction_service.py; measured on the prototype). R12 now asserts exactly one ERROR record containing the host and the exception type and no path, not the exact template, so either ruling (S1) satisfies it.
- D4 (R9): kept as specified: the INFO line `[URL-V2] outcome=http_error reason=http_403 status=403` (the spec's `outcome` value for a non-2xx; the prototype logs `outcome=<fetch outcome>|http_error|challenge|not_product_page|unresolved|ok`).
- D5 (P36): the spec's "truth ON ... calls as recorded" is self-contradictory (the fixture records truth OFF, `calls: []`). Split into (a) the five url scenarios re-driven exactly as recorded (truth OFF, anonymous, metering OFF) under flag None/"false"/"garbage" == the fixture records, and (b) a full-config row (truth + metering ON, authed, flag "off") asserting the fixture bodies and the base row constants.
- D6 additions beyond the spec rows (all within the rulings): R7b service reader table; R11b body-text PIN (spec M15 note); R14b; R42b; R43/R44 (B4-R1); the C19 status table; the malformed-url INFO row (B4-R4); the copy-constant row; the seam row (`_TRANSPORT is None`, deadline 25.0).
- D7 R1 events: asserted `["ssrf", "ssrf", "pregate"]` with the SSRF fake on `validate_external_url` (the route's two checks), as specified.

## 7. Questions for the gate

- S1 (blocking for GREEN) the u8d R8 collision: either (a) `_fetch_page_v2` logs a DIFFERENT ERROR template (host + type only, e.g. `[URL-V2] fetch failed host %s: %s`), keeping R8 untouched (my recommendation: no pin edit, R12 already accepts it), or (b) an E5 row amending R8 to accept N calls with that prefix. Option (c), routing both through one helper, changes `fetch_page` and breaks R39 / the spec's byte-unchanged rule.
- S2 the spec 2.2 (b) post-fetch rule names only `{homepage, search}` but its parenthesis says cart/account/category after a redirect count too; the prototype refuses ANY class; RED pins only the homepage redirect. Rule which.
- S3 the `[URL-V2] outcome=` vocabulary is pinned only for the 403 case (D4); GREEN may choose the rest.
- S4 `classify_url_path(None)` returns `homepage` (urlsplit('') has path ''); unreachable from the route (pydantic str) and not pinned.

## 8. NOT MEASURED

- The comm set at HEAD (no GREEN bytes exist); the CI-order set (spec gate 7, OFF only per B4-R8).
- The prototype was not run against the full comm set (only the 10 pin files of section 3); the clear-list edits E1-E4 and the CLAUDE.md row were not prototyped.
- The four `test_precommit_hook*.py` files (excluded by rule; `.githooks` untouched).
- No TIMEOUT occurred in any run (no re-run needed).

## 9. Restore check

- sha256 of all 3,406 tracked files in the real worktree: identical before (12:40, `real_tracked_sha_before.txt`) and after (13:37, `real_tracked_sha_after.txt`), `cmp` equal.
- `git -C sc-s80-b4 status --short` = `?? tests/test_s80_url_mode_v2.py` only; HEAD still `81df2b641454e0301cca51a3ba01bf8ef3d7e649`.
- Scratch worktree `<scratchpad>/B4_red/b4_scratch` removed with `git worktree remove --force`; `git worktree list` no longer shows it; it carried no node_modules junction.
- Mutation lock created in the scratch worktree only and removed; every mutant restore sha256-verified by the driver; the prototype files re-verified OK against `proto_sha.txt` after the last batch.
- No orphan pytest: no python process carries a `b4red` tag after the last run.
