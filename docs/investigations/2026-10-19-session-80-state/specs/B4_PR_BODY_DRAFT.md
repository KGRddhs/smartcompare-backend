# B4 URL-MODE-V2: link pre-gate, typed outcomes, URL images, why-we-chose (ENABLE_URL_MODE_V2, dark)

Unit B4 of the session-80 QA/UX remediation lane (PLAN_S80.md section 3 B4, ruling R-A7 as amended by RULINGS_R0.md R0-1 / R0-6 / R0-7, RULINGS_BATCH1.md B4-R1..R11, RED gate GATE_B4.md GC-1..GC-8). Branch `feature/s80-b4-url-mode-v2`, GREEN commit `9db99de9` on the spec base `81df2b64`; the orchestrator rebases onto `origin/main` (`cb80ea2f` or newer, B1 merged) after the adversaries (GC-7). The CLAUDE.md row is re-placed after the SESSION 80 B1 and B3 rows at the rebase (G-2 order B1, B3, B4).

## What the flag does

`ENABLE_URL_MODE_V2` (default OFF, read per call; a new name, so unset in production by construction). The route reads it ONCE per request and threads a bool down as the conditional kwarg `url_mode_v2=True`.

ON:
- **Pre-gate ($0, before the credit reserve, after the unchanged SSRF 400).** POST/GET `/api/v1/url/compare` refuse a link whose PATH is a storefront root, a search route, a cart/checkout route, an account route or a category/collection listing without a product segment, and a pair equal after normalisation: HTTP 400 `code: NOT_PRODUCT_PAGE` + additive `field` (url1|url2|both) + `reason` (homepage|search|cart|account|category|same_url). Nothing reserved, nothing fetched, no search_logs row (the SSRF-400 class).
- **Typed post-fetch outcomes.** A second fetch function `_fetch_page_v2` keeps the last status and the final url (`fetch_page` is byte-unchanged): transport error / SSRF-blocked hop / redirect cap / non-2xx / title-anchored challenge page -> 400 `STORE_UNREADABLE`; a final url in any pre-gate class -> 400 `NOT_PRODUCT_PAGE` (GC-2); no Product node (JSON-LD shape ladder) and no usable title -> 400 `UNRESOLVED_PRODUCT` with no LLM call; the LLM's `is_product_page: false` refuses only a node-less page, `null_name` only an unusable title (B4-R1); never `success: true` with `Unknown Product`. A 25 s `asyncio.wait_for` -> the structured 503 `TIMEOUT`. Precedence STORE_UNREADABLE > NOT_PRODUCT_PAGE > UNRESOLVED_PRODUCT with `field: both`; an exception inside `extract_from_url` keeps the base codeless 400.
- **Non-delivery (R-A3)** through the existing coded-failure exit: refund once (`usage_refund.url.compare.failure`), no lifetime bump, no history row, the W4-13 failure row with the code's constant message.
- **Envelope.** The error handler passes `field` / `reason` (str only) through for the three B4 codes only (B4-R5).
- **Images.** `image_url` = the first absolute https url string (JSON-LD `image` via `price_service._jsonld_image_urls`, `@graph` / `@type` lists / `ProductGroup.hasVariant` via the shape ladder, `urljoin` on the FINAL url, the og:image key-presence bug fixed) or null. A deliberate retype from the raw JSON-LD list on fragrancex-class pages (PLAN section 0 item 4).
- **Why we chose.** The frozen keys `recommendation` (from `strip_score_internals(winner_reason)` with the `_QUALITATIVE_WINNER_REASON` fallback) and `key_differences` (the `specs_comparison` advantages) are filled; the top-level key set is unchanged and there is still no `metadata` (Link compares stay unpersisted, R0-1).
- **Prompt.** `URL_EXTRACTION_PROMPT_V2` asks for `is_product_page`; derived from the untouched V1 by two count-checked swaps; same render shape and kwargs `{gpt-4o-mini, 800, 0.1, store False}`.

UNFLAGGED (R-A1 b, log-only): the INFO lines `URL comparison request`, `URL extraction request` and `Detected retailer` print the host only (the retailer label is a SUPPORTED_RETAILERS name or `unknown`, never the raw netloc).

OFF: byte-identical (base positional call, no pre-gate, no deadline, `fetch_page`, the base prompt, the raw `image_url`, `recommendation ""` / `key_differences []`, the four-key envelope). The only OFF deltas: one env read per request in the route and one per error response, the import-time derived prompt constant, four defaulted kwargs (non-wire).

Build 3: every new 400 code renders the generic copy (`errorCopy.ts` default arm) exactly as the codeless 400 today; the 503 TIMEOUT renders the timeout copy. C3 maps `field` / `reason` after approval.

## Defects -> RED nodes -> flag -> precondition

| defect | RED nodes (`tests/test_s80_url_mode_v2.py::`) | flag | activation precondition |
|---|---|---|---|
| MYEZ-005 homepage links accepted (V02/V09) | `test_pregate_homepage_pair_refused_before_reserve[*]` (12), `test_pregate_field_and_reason[*]` (14), `test_pregate_same_url_after_normalisation[*]` (10), `test_flag_reader_table_on[*]` (14), `test_pregate_writes_no_search_log_row[*]`, `test_classify_url_path_table[*]` (34), `test_normalize_url_table`, `test_redirect_to_homepage_is_not_product_page_post_fetch[*]`, `test_mixed_codes_precedence_not_product_page_over_unresolved[*]` | ENABLE_URL_MODE_V2 | App Store approval; R-A2 order (after CLAIMS_PROVENANCE, before RESULT_GATE); owner's yes; one canary window |
| MYEZ-006 link failure gives no cause | `test_v02_fragrancex_403_is_store_unreadable[*]`, `test_both_urls_403_field_both[*]`, `test_challenge_page_is_store_unreadable[*]`, `test_transport_error_is_store_unreadable[*]` (see Open item), `test_non_2xx_reason_table[*]`, `test_route_fetch_blocked_or_capped_is_store_unreadable[*]`, `test_deadline_yields_timeout_503[*]`, `test_mixed_codes_precedence[*]`, `test_error_handler_passthrough_on[*]`, `test_error_handler_reader_table[*]`, `test_service_flag_reader_table[*]`, `test_non_delivery_per_r_a3_every_code[*]` (16), `test_copy_constants_verbatim_and_policy_clean` | same | same |
| MYEZ-014 URL images | `test_pdp_image_is_first_https_string[*]` (10 cases x 2 parse-offload states) | same | same |
| MYEZ-017 empty why-we-chose (URL mode) | `test_recommendation_and_key_differences_filled[*]`, `test_recommendation_fallback_when_reason_leaks_scores[*]` | same | same |
| OWNER-INFO (URL mode) | `test_llm_answers_on_a_usable_title_page[*]`, `test_node_bearing_page_with_llm_false_delivers`, `test_null_name_only_when_the_title_is_unusable`, `test_never_unknown_product_flag_on[*]`, `test_is_usable_title_table`, `test_prompt_v2_asks_is_product_page_and_keeps_shape`, `test_prompt_v2_is_derived_from_v1` | same | same |
| OWNER-SCRAPERS (URL-mode scraper) | `test_fetch_page_v2_blocks_private_initial_url`, `test_fetch_page_v2_blocks_redirect_to_metadata`, `test_fetch_page_v2_caps_redirect_chain`, `test_fetch_page_v2_keeps_status_and_final_url`, `test_route_fetch_blocked_or_capped_is_store_unreadable[*]`, `test_test_seams_have_production_values`, `test_v2_kwarg_is_conditional[*-on]` | same | same |
| V02 (fragrancex 403 -> codeless 400) | `test_v02_fragrancex_403_is_store_unreadable[POST|GET]`, `test_both_urls_403_field_both[POST|GET]` | same | same |
| V09 (storefront delivered as success, billed) | `test_v09_storefront_pages_unresolved[POST|GET]`, `test_pregate_homepage_pair_refused_before_reserve[*]` | same | same |
| unflagged host-only logging (R-A1 b) | `test_info_lines_print_host_only`, `test_info_line_survives_a_malformed_url` | none (log-only) | ships on merge |

Flag-OFF identity PINs (full configuration, ruling B1): `test_ssrf_refusal_byte_identical_in_both_states[*]`, `test_flag_off_homepage_pair_is_base_behaviour[*]` (14), `test_codeless_failure_keeps_base_body_flag_on[*]`, `test_flag_off_no_deadline[*]`, `test_deadline_exception_arm_untouched[*]`, `test_flag_off_image_passes_through_raw[*]`, `test_flag_off_recommendation_empty[*]`, `test_prompt_off_render_equals_w411_digest[*]`, `test_error_handler_four_key_body[*]`, `test_w4_13_rows_unchanged_flag_off[*]`, `test_w4_13_rows_full_config_flag_off`, `test_v2_kwarg_is_conditional[*-off]`, `test_fetch_page_untouched_pin`, `test_body_text_access_denied_is_not_a_challenge[*]`, `test_pregate_lets_distinct_pdps_through[*]`.

## Deliberate pin changes (spec 4.1; test-only, additive; no existing assertion changes value)

| E | test (file) | before | after | reason |
|---|---|---|---|---|
| E1 | `tests/test_model_config_enforced.py` `_clean_env` | five flags cleared | six (+ `ENABLE_URL_MODE_V2`) | R0-6: a developer `.env` with the flag must not move the M3 kwargs |
| E2 | `tests/w4_11_prompt_digest_recorder.py` `FLAGS` | ten names | eleven | R0-6; the digest fixture is NOT regenerated |
| E3 | `tests/test_prompt_fence.py` `_W411_FLAGS` | ten names | eleven | R0-6; F11/F13 measure the OFF render |
| E4 | `tests/test_s71_u13_compare_auth_required.py` `CLEAN_ENV` | seventeen names | eighteen | R0-6: every env name a paid route reads per call |
| E5 | `tests/test_retro_w2_1.py` `_clean_flags` | five names | six | ruling B4-R8 (wanted) |

No fixture regenerated (`w4_11_prompt_render_digests.json`, `s71_u13_flag_off_baseline.json`, `w4_13_flag_off_ledger.json` untouched); no requirements, client, `.githooks`, `tests/.pre_impl_failures.txt`, `processors.json` or migration change.

## Gates (every pytest through the bounded runner, one process at a time; the free tier)

Unit file (`tests/test_s80_url_mode_v2.py`, 252 nodes):
```
ENABLE_URL_MODE_V2=true: 2 failed, 250 passed, 11 warnings in 9.26s; [hermeticity] sentinel checked 252 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4g-unit-on2 start=2026-10-20 14:03:15 end=2026-10-20 14:03:28 elapsed=13s bound=600s status=FAIL rc=1
flag unset: 2 failed, 250 passed, 11 warnings in 20.47s; sentinel 252; netguard 0
[pyt] tag=b4g-unit-off1 start=2026-10-20 14:03:44 end=2026-10-20 14:04:07 elapsed=23s bound=600s status=FAIL rc=1
```
The two red nodes are `test_transport_error_is_store_unreadable[POST|GET]` (Open item below); at base the file is 206 RED / 46 PIN.

Existing pins (flag OFF, one call, 20 files): `1037 passed, 13 warnings in 172.17s; sentinel 1037; netguard blocked 10 attempt(s) from 10 node(s)` (all `[sentinel] neutralized.supabase.invalid`, pre-existing at base) - `[pyt] tag=b4g-pins1 start=2026-10-20 14:05:47 end=2026-10-20 14:08:47 elapsed=179s bound=600s status=OK rc=0`. W0-4c guard file: `157 passed in 89.26s` - `[pyt] tag=b4g-retro-w0-4 start=2026-10-20 14:09:01 end=2026-10-20 14:10:39 elapsed=98s bound=600s status=OK rc=0`.

Comm set at HEAD (GC-5: the RED base list of 119 UNION the module/symbol grep at HEAD UNION the SmartCompareApp scanners UNION the importers of the edited test-support module `tests/w4_11_prompt_digest_recorder.py` and of every edited test file UNION the source-scanning pins UNION the CLAUDE.md readers UNION the unit file = 120 files; minus the three `test_precommit_hook*.py` files; `tests/test_rate_limiting_complete.py` never matched, NETWORK_FLAKY_EXCLUDE), 5 chunks, bound 1200, flag OFF:
```
c1: 890 passed, 1 skipped, 12 deselected, 13 warnings in 118.37s; sentinel 891; netguard blocked 2 attempt(s) from 2 node(s)
[pyt] tag=b4g-comm-head-c1 start=2026-10-20 14:17:32 end=2026-10-20 14:19:35 elapsed=123s bound=1200s status=OK rc=0
c2: 2146 passed, 1 skipped, 18 warnings in 442.46s; sentinel 2147; netguard blocked 55 attempt(s) from 38 node(s)
[pyt] tag=b4g-comm-head-c2 start=2026-10-20 14:19:45 end=2026-10-20 14:27:10 elapsed=445s bound=1200s status=OK rc=0
c3: 682 passed, 2 skipped, 8 deselected, 1 xfailed, 13 warnings, 2 errors in 46.01s; sentinel 685; netguard blocked 123 attempt(s) from 8 node(s)
[pyt] tag=b4g-comm-head-c3 start=2026-10-20 14:27:29 end=2026-10-20 14:28:21 elapsed=51s bound=1200s status=FAIL rc=1
c4: 2 failed, 1843 passed, 1 skipped, 1 deselected, 13 warnings in 502.31s; sentinel 1846; netguard blocked 12 attempt(s) from 6 node(s)
[pyt] tag=b4g-comm-head-c4 start=2026-10-20 14:28:44 end=2026-10-20 14:37:20 elapsed=516s bound=1200s status=FAIL rc=1
c5: 644 passed, 1 skipped, 16 warnings in 255.81s; sentinel 645; netguard blocked 24 attempt(s) from 22 node(s)
[pyt] tag=b4g-comm-head-c5 start=2026-10-20 14:37:41 end=2026-10-20 14:42:07 elapsed=266s bound=1200s status=OK rc=0
```
HEAD FAILED/ERROR set: the two cold-tiktoken `tests/test_prompt_truth.py` ERRORs (identical at base, environmental) + the two unit-file R12 nodes. Branch-only-NEW vs the RED base set = `tests/test_s80_url_mode_v2.py::test_transport_error_is_store_unreadable[POST|GET]` only (the unit's own RED file; zero new failures in the existing estate). Totals: base 5955 passed over 119 files; HEAD 6205 passed = 5955 + 250 unit nodes. Netguard: no node blocked at HEAD that was not blocked at base (2 base-only egress nodes, none head-only).

CI-order set (alphabetical, flag OFF only per B4-R8): `2 failed, 901 passed, 13 warnings in 129.91s; sentinel 903; netguard blocked 10 attempt(s) from 10 node(s)` - `[pyt] tag=b4g-ci-order start=2026-10-20 14:44:09 end=2026-10-20 14:46:30 elapsed=140s bound=1200s status=FAIL rc=1` (the same two R12 nodes).

Lint: `ruff check --select E9,F63,F7,F82` clean on the three app files, the five edited test files and the unit file; `py_compile` clean; full-rule ruff on the app files shows no new finding vs base (one fewer: `typing.Tuple` is now used).

Mutation on the GREEN bytes (12 targeted mutants, byte copy + exact edit + restore + sha256): 11 KILLED, 1 SURVIVED (`G10`: the normaliser-stage `image_url` coercion removed; the generic v2 extractor already normalises, so only an LLM-merged or amazon/noon image reaches that stage and no RED row covers it; reported for a ruling). RED ran 63/63 mutants on its prototype.

## Open item for the gate (blocking the "all rows green" claim)

GC-1 (binding) rules that `_fetch_page_v2` logs ONE WARNING `[URL-V2] fetch failed host=%s reason=%s type=%s` and never the base ERROR template. The frozen RED row R12 (`test_transport_error_is_store_unreadable[POST|GET]`) asserts exactly ONE **ERROR**-level record carrying the exception type (`_messages(..., logging.ERROR)`), so GC-1's "R12 already accepts this" does not hold: implemented per GC-1, R12 is red on that one assertion (status, body, field and reason all pass). Measured alternative (byte copy, restored, sha-verified): the transport-error line at ERROR inside the except arm with the distinct template turns R12 green and keeps every u8d R8 pin green (`12 passed` for `-k "transport_error or R8 or r8"`, `[pyt] tag=b4g-variant-error-level ... status=OK rc=0`). Ruling needed: amend R12 to WARNING (re-freeze the RED file) or amend GC-1 for the transport-error case.

## Stated limits (full list in the CLAUDE.md row)

Root-served PDPs refused as homepages; fragrancex stays unreadable (R-A7, no impersonation); the measured pre-gate misses `/ar/search`, amazon `/s`, noon `/uae-en/search/`, 3-letter locale roots, `/en/cart.html` (B4-R7; Amazon then refused post-fetch at $0, noon after the paid LLM rung); KPI moves (constant messages, V09 successes become failures, pre-gate refusals write no row); 503 TIMEOUT raises the 5xx rate; ItemList members are not reached by the shape ladder; https only, first image only; amazon/noon never report a Product node; prose-derived recommendation (B12 brings scoring); refunds use the legacy previous-window fallback (B4-R6); a WebPage node name never counts as a site name; never set the flag in a local `.env` (measured: five `url_compare_*` nodes of `tests/test_paid_route_metering.py` go red; their stub has the base signature); an inner builtin TimeoutError escaping `compare_from_urls` before the deadline would also be reported as TIMEOUT (none known: the inner `wait_for` sites catch theirs).

## Owner steps (names only)

None before approval. After approval: (1) flip `ENABLE_URL_MODE_V2` in the R-A2 order (after `ENABLE_CLAIMS_PROVENANCE`, before `ENABLE_RESULT_GATE`), one change per canary window; (2) three Link compares from a TestFlight install (the fragrancex homepage pair -> 400 NOT_PRODUCT_PAGE in under 1 s with 0 credits; a real PDP pair -> 200 with a non-empty `recommendation` and a str `image_url`; a Rasasi PDP pair); (3) read the Railway log for the `[URL-V2]` lines and the `/url/compare` 400 / 503 counts, and the url failure mix in `search_logs`; (4) the C3 OTA maps the codes and `field` / `reason` to the audit copy. Rollback: unset the variable (per call, immediate).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
