# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- fix round 2 RE-VERIFIER, correctness lens (2026-10-20)

Verdict: **NOT_READY** (blocking 0, MAJOR 1, minor 9). M1 (homepage half), E1 and E2 are CLOSED with evidence; every round-2 adversary survivor is now killed. The one MAJOR is the unruled same_url residual of the M1 class (MAJOR-R1 below), measured through the real route.

- Unit B4, worktree `C:/Users/SynAckITPC/Documents/AI/sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, HEAD verified `83daa8cbc923e81abde398bdf93f84bdc4acab66` at 20:32 and again at the end; `git status --short` empty at start and end; no `.qa-mutation.lock`; the worktree was never edited (every run there with PYTHONDONTWRITEBYTECODE=1; the only `__pycache__` files there date from 15:58, not mine).
- Agent model: claude-opus-5-5 (this agent's system prompt).
- Read: s80-common.txt (+ the 2026-10-20 addendum), PLAN_S80.md sections 0-1, RULINGS_BATCH1.md (Common + B4-R1..R11), GATE_B4.md, RULINGS_FIX1_B4.md, RULINGS_FIX2_B4.md (binding), B4_ADV2_correctness.md, B4_ADV2_engineering.md, B4_FIX2_REPORT.md, PR_BODY.md (fix 2, sha `97272c19...`), the CLAUDE.md row (lines 474-475), the full fix-round-2 diff 96676f1f..83daa8cb and the route/service code it touches. Not opened: RULINGS_R0.md, B4_FIX1_REVERIFY.md, B4_FIX1_REPORT.md (the fix-2 rulings and both adversary reports cite what this lens needed).
- Scratch worktree `<scratchpad>/B4_fix2_adv` (detached 83daa8cb, no node_modules); the LF RED file copied byte-exact over the autocrlf checkout; 13 other files sha-equal to the worktree before the first mutant and after the last (url_extraction_service `35f37566...`, url_routes `9229e0b4...`, error_handler `7e539cc7...`, CLAUDE.md `6e51ad94...`, metering `4724c308...`, the RED file `1e8e28ae...`). Removed at the end. Notes, probes, logs: `<scratchpad>/B4_fix2_rv/`.
- No .env read/copied/printed; no flag set outside one runner call; no network (every netguard node below is in `tests/.network_attempt_baseline.txt`, checked id by id).

## 1. RED file re-hash

`tests/test_s80_url_mode_v2.py` = `1e8e28aeff8c7fbc9fc9bcf67e0a765ed151ad1f87b8cd9508da38ac54894e0a` (worktree bytes = the committed blob), 101,070 B, LF (0 CR), 0 bytes > 127, 2,076 lines. Its first 75,913 bytes hash to `546fc27d07579808...8b46` (= `git show 96676f1f:` the previous frozen file): a pure append; the 96676f1f..83daa8cb diff of the file has 0 removed lines. Collected: 335 nodes over 76 functions.

## 2. Runs (every pytest through pyt.py, one process at a time)

```
unit flag unset (worktree): 335 passed, 11 warnings in 19.23s; [hermeticity] sentinel checked 335 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4rv2-unit-off start=2026-10-20 20:39:59 end=2026-10-20 20:40:25 elapsed=26s bound=600s status=OK rc=0
unit ENABLE_URL_MODE_V2=true (worktree): 335 passed, 11 warnings in 7.46s; sentinel 335; netguard 0
[pyt] tag=b4rv2-unit-on start=2026-10-20 20:40:33 end=2026-10-20 20:40:42 elapsed=9s bound=600s status=OK rc=0
probes (scratch, section 4): 38 passed, 11 warnings in 3.14s; sentinel 38; netguard 0
[pyt] tag=b4rv2-probe start=2026-10-20 20:43:22 end=2026-10-20 20:43:27 elapsed=5s bound=600s status=OK rc=0
mutation control (scratch, unmutated): 335 passed, 11 warnings in 7.48s; sentinel 335; netguard 0
[pyt] tag=b4rv2-mut-control start=2026-10-20 20:46:37 end=2026-10-20 20:46:46 elapsed=9s bound=600s status=OK rc=0
R8 pins ALONE (worktree): tests/test_sentry_channels_u8d_unit.py 141 passed; netguard 0
[pyt] tag=b4rv2-u8d-unit start=2026-10-20 20:56:13 end=2026-10-20 20:56:36 elapsed=24s bound=600s status=OK rc=0
R8 pins ALONE (worktree): tests/test_sentry_channels_u8d.py 131 passed; netguard 0
[pyt] tag=b4rv2-u8d start=2026-10-20 20:56:39 end=2026-10-20 20:56:50 elapsed=10s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag unset: 21 passed, 13 warnings; netguard blocked 2 attempt(s) from 2 node(s) (sentinel neutralized.supabase.invalid, both in the baseline)
[pyt] tag=b4rv2-meter-off start=2026-10-20 20:57:03 end=2026-10-20 20:57:08 elapsed=5s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag exported: 21 passed, 13 warnings; netguard the same 2 baseline nodes
[pyt] tag=b4rv2-meter-on start=2026-10-20 20:57:10 end=2026-10-20 20:57:15 elapsed=6s bound=600s status=OK rc=0
tests/test_auth_error_log_hygiene.py ALONE (E2): 69 passed, 11 warnings in 3.46s; sentinel 69; netguard 0
[pyt] tag=b4rv2-auth-log-hygiene start=2026-10-20 20:57:17 end=2026-10-20 20:57:23 elapsed=5s bound=600s status=OK rc=0
CI-order set (13 files, alphabetical, flag OFF, worktree): 986 passed, 13 warnings in 66.74s; sentinel 986; netguard blocked 10 attempt(s) from 10 node(s), 0 not in the baseline
[pyt] tag=b4rv2-ci-order start=2026-10-20 20:57:47 end=2026-10-20 20:58:56 elapsed=69s bound=1200s status=OK rc=0
F2-3 source-scanning chunk (13 files: test_auth_error_log_hygiene, test_behavior_dimension_translation, test_ci_gates, test_migration_index_predicate_immutability, test_model_config, test_model_config_enforced, test_openai_key_log_hygiene_s69, test_prompt_fence, test_retro_w0_4, test_retro_w0_4_efg, test_sentry_channels_u8d_unit, test_start_command, test_u3c_store_false_pin), flag OFF, worktree: 777 passed, 11 warnings in 80.41s; sentinel 777; netguard 0
[pyt] tag=b4rv2-srcscan start=2026-10-20 21:01:21 end=2026-10-20 21:02:43 elapsed=82s bound=1200s status=OK rc=0
limit-16 20-file pin set, flag EXPORTED (worktree): 1037 passed, 13 warnings in 30.00s; netguard 10 nodes, 0 new
[pyt] tag=b4rv2-pins20-flagON start=2026-10-20 21:03:03 end=2026-10-20 21:03:36 elapsed=32s bound=1200s status=OK rc=0
collection of the RED file: 335 nodes
[pyt] tag=b4rv2-collect start=2026-10-20 21:03:51 end=2026-10-20 21:03:55 elapsed=4s bound=600s status=OK rc=0
X1 mutant vs the two u8d files (scratch): 272 passed (survived)
[pyt] tag=b4rv2-X1-vs-u8d start=2026-10-20 21:04:30 end=2026-10-20 21:04:45 elapsed=15s bound=600s status=OK rc=0
hook file ALONE (scratch, .githooks / hook tests sha-equal to the worktree; the unit's diff 81df2b64..HEAD touches no .githooks / .gitleaks.toml): tests/test_precommit_hook.py 62 collected, 20 passed (0 failed) when the bound fired, ~29 s per node
[pyt] tag=b4rv2-hook-a start=2026-10-20 21:05:32 end=2026-10-20 21:15:18 elapsed=586s bound=580s status=TIMEOUT rc=124
```
1 TIMEOUT (the hook file). Its single re-run was NOT done: at the measured ~29 s per node the file needs ~30 min (a second TIMEOUT is certain inside any foreground bound), and the session ledger's 21:00 / 21:15 lines announce the owner's 21:30 shutdown. `tests/test_precommit_hook.py`, `_round2`, `_phase_b`, `_phase_b_round2`: NOT MEASURED by this agent (excluded from comm sets by rule; the hook itself passed on the fix commit per the fix report). No orphan pytest after the TIMEOUT (process list read: none of mine).

Comm-set check (F2-3 / E2): my own re-derivation over the tests tree (31 files that walk/glob/listdir; 19 of them name an `app` path; 44 files that build an `app/` path string) finds NO file outside the fix agent's 184-file union (`B4_fix2/comm_union.txt`); every standing source-scanning pin and both CLAUDE.md readers are in it. I did not re-run the 8 union chunks (the fix agent's chunk logs and the ledger entries b4f2-comm-00..07 exist with the cited times and statuses, `harness/pyt_ledger.jsonl`); the CI-order set, the source-scanning chunk, the R8 pins, the metering file, the 20-file set and the auth-hygiene file were re-run here on the HEAD bytes.

Lint (worktree, read-only): `ruff 0.16.5 check --select E9,F63,F7,F82 --no-cache` on the service, url_routes, error_handler and the RED file: `All checks passed!`; `compile()` of the four: OK. Full-rule ruff on the service, 96676f1f vs HEAD: 58 {F401 2, W293 56} -> 57 {F401 1, W293 56} (the fix report's claim, confirmed).
Hygiene (96676f1f..HEAD, 3 files): service CRLF 1363/1363, 18 bytes > 127 before and after; CLAUDE.md CRLF 938/938, 3979/3979; RED file LF, 0. 573 added lines: 0 non-ASCII, 0 @gmail, 0 +973, 0 8+-digit runs, 0 sk-/AKIA/xox/eyJ/credentialed-URL/PEM.

## 3. Mutation table (scratch worktree; `B4_fix2_rv/mutate.py`: lock `.qa-mutation.lock` -> byte copy -> exact edit(s) matching once (CRLF-adapted) -> pyt.py bound 600 on the full unit file with every ENABLE_* unset and PYTHONDONTWRITEBYTECODE=1 (no stale bytecode after a same-size restore) -> restore -> sha256 compare (abort on mismatch; none) -> lock removed; results `mut_results.jsonl`, logs `mut_<id>.log`)

Every KILLED row: all E-lines AssertionError, no other class. Times are the [pyt] lines (tag `b4rv2-<id>`, status FAIL rc=1 for a kill, OK rc=0 for a survivor).

| id | mutant | result | killing nodes (first) | [pyt] elapsed |
|---|---|---|---|---|
| M1a | pre-gate site: query stripped before `classify_url_path` (a product-route query refused again) | KILLED 6 | test_query_routed_pdp_pair_delivers_flag_on[POST-opencart-opencart] | 10s |
| M1b | post-fetch site: final url's query stripped (refused again post-fetch) | KILLED 8 | test_query_routed_pdp_pair_delivers_flag_on[*], test_redirect_to_query_routed_pdp_is_not_refused_post_fetch[*] | 19s |
| M1c | pre-gate site: any query exempts (a gclid root delivered) | KILLED 6 | test_pregate_homepage_pair_refused_before_reserve[POST-...?gclid=abc123] (+gbraid) | 14s |
| M1d | post-fetch site: any query exempts | KILLED 3 | test_redirect_to_tracking_root_is_still_homepage_post_fetch[POST] | 14s |
| M1e | any `route` value is a product route | KILLED 1 | test_classify_url_path_tracking_query_stays_homepage[/index.php?route=common/home] | 10s |
| E1a | the quadratic lazy-group title regex reintroduced in `_is_challenge_page` | KILLED 3 | test_challenge_title_scan_is_linear[no-gt-in-window], [gt-no-close], test_challenge_title_without_a_close_tag_is_read_to_a_bound | 22s |
| E1b | title window unbounded (`window = html`) | **SURVIVED** (335) | - (the "first 64 KiB" is unpinned, minor m5) | 15s |
| E1c | no-close bound 1024 -> 4 | KILLED 1 | test_challenge_title_without_a_close_tag_is_read_to_a_bound | 17s |
| E1d | opener accepts whitespace only (plain `<title>` missed) | KILLED 8 | test_challenge_page_is_store_unreadable[*] | 12s |
| P1 | WebPage counted as a site name | KILLED 1 | test_webpage_name_is_not_a_site_name | 22s |
| P2 | `[SSRF] Blocked redirect to host=` prints the target | KILLED 1 | test_v2_fetch_log_records_carry_the_host_only[blocked_hop] | 12s |
| P3 | retailer label = raw netloc for an unknown host | KILLED 8 | test_v2_fetch_log_records_carry_the_host_only[*], test_detected_retailer_label_is_a_supported_name_or_unknown[*] | 10s |
| S3 | `_log_fetch_failed` prints the url | KILLED 5 | test_v2_fetch_log_records_carry_the_host_only[*] | 10s |
| S5 | `_host_only` returns netloc | KILLED 9 | test_info_line_survives_a_malformed_url, F2-4a / F2-4c rows | 10s |
| S8 | `[SSRF] Blocked initial URL` prints the url | KILLED 1 | test_v2_fetch_log_records_carry_the_host_only[blocked_initial] | 12s |
| S9 | `[SSRF] Too many redirects` prints the url | KILLED 1 | test_v2_fetch_log_records_carry_the_host_only[redirect_cap] | 10s |
| S01 | v2 loop `range(6)` | KILLED 1 | test_fetch_page_v2_redirect_bound_is_five_requests | 10s |
| S02 | post-fetch refuses the homepage class only | KILLED 5 | test_post_fetch_final_url_in_any_pregate_class_is_not_product_page[*] | 10s |
| S03 | pair reason from the LAST link carrying the code | KILLED 4 | test_pair_reason_is_the_first_failing_links[*] | 10s |
| S10 | the LAST Product node | KILLED 2 | test_first_product_node_in_document_order_wins[*] | 10s |
| F5a | unusable merged name ships (`raw_data["name"] = None` removed) | KILLED 6 | test_placeholder_llm_name_never_ships_flag_on[*], ..._with_a_usable_llm_full_title | 13s |
| F5b | meta fallback on key presence again | KILLED 3 | test_nameless_node_without_price_falls_back_to_the_title, ..._with_price_uses_the_meta_title_without_the_llm[*] | 10s |
| F5c | null_name refusal dropped | KILLED 5 | test_null_name_only_when_the_title_is_unusable, test_no_usable_title_and_placeholder_name_is_unresolved[*] | 12s |
| F5d | merged-name check ignores site names | KILLED 1 | test_placeholder_llm_name_never_ships_flag_on[Rasasi] | 13s |
| F5e | node-name usability ignores site names (extract_generic_data_v2) | **SURVIVED** (335) | - (minor m5; behaviour correct at HEAD, probe f25 node-name-is-site-name) | 9s |
| X1 | transport ERROR line gains `exc_info=True` (traceback text) | **SURVIVED** (335; and 272 over the two u8d files) | - (F2-4a checks `getMessage()` only, minor m5) | 9s / 15s |
| X2 | url2's class wins when both links are refused | KILLED 2 | test_pregate_field_and_reason[*-both-home-search] | 10s |
| X3 | "access denied" dropped from the challenge prefixes | KILLED 1 | test_challenge_title_verdicts_preserved[...Access denied...] | 10s |
| X4 | `parse_qs` without keep_blank_values (an empty product key not a route) | **SURVIVED** (335) | - (fix report open question 3, ruling text ambiguous; information) | 9s |
| X5 | a 401 reported as http_403 | **SURVIVED** (335) | - (no 401 row; pre-existing GREEN shape, minor m5) | 56s |
| X6 | post-fetch class check reads the pasted url, not the final url | KILLED 17 | test_redirect_to_homepage_is_not_product_page_post_fetch[*] + F2-4e rows | 51s |

Counts: 31 applied (one per fix and more: F2-1 x5 at both sites both directions, F2-2 x4, F2-4 x11 = every adversary-2 survivor, F2-5 x5, spec x6), 26 KILLED, 5 SURVIVED (E1b, F5e, X1, X4, X5: pin gaps or a ruling ambiguity; no behaviour defect behind them at HEAD). Every adversary-2 survivor (P1, P2, P3, S01, S02, S03, S10, S3, S5, S8, S9) is killed by an independent re-write of the mutant.

## 4. Probes (scratch; `B4_fix2_rv/test_zz_b4rv2_probe.py`, output `probe.jsonl`)

1. **Same-store pairs through the real route (full config, metering + truth ON, authed), POST and GET, flag OFF vs ON** (pages with a Product node and a price each):

| pair (one host, two products) | flag OFF | flag ON |
|---|---|---|
| OpenCart `index.php?route=product/product&product_id=1262` vs `...=1263` | 200, both names, 2 fetches, 1 consume | 400 NOT_PRODUCT_PAGE field both reason same_url, 0 fetches, 0 consumes |
| OpenCart root `/?route=product/product&product_id=11` vs `12` | 200 | 400 same_url |
| PrestaShop `index.php?id_product=12&controller=product` vs `13` | 200 | 400 same_url |
| WooCommerce `/?product=b4-oud-a` vs `b4-oud-b` | 200 | 400 same_url |
| osCommerce `product_info.php?products_id=1` vs `2` | 200 | 400 same_url |
| ASP.NET `ProductDetails.aspx?pid=100` vs `200` | 200 | 400 same_url |
| Shopify `/products/sauvage?variant=111` vs `222` (F2-6 c, ruled) | 200 | 400 same_url |

2. `classify_url_path` (pre-gate and post-fetch class): `index.php?route=product/category&path=20`, `route=product/search&search=oud`, `route=product/compare`, `route=product/special`, `route=product/manufacturer` -> None (pass the pre-gate, fetched; all were `homepage` at 96676f1f); `route=checkout/cart` and `route=account/login` -> homepage; `/?product=` and `/index.php?product_id=` (empty value) -> None; `/?a=1;product_id=2` -> homepage; `&amp;product_id=` -> None (the `route` key carries it).
3. `_is_challenge_page` timing (max of 3 runs): `<title ` flood with no `>` in the window 0.083 ms, with `>` and no close 0.061 ms, `<title>` x9300 0.071 ms, `<titlex` x9300 2.2 ms, `</title ` close-candidate flood 2.5 ms, 65,000 spaces after `</title` 4.0 ms, upper-case flood 0.048 ms, `<` x66000 0.075 ms, a 2 MB normal challenge page 0.04 ms (True). End to end (`extract_from_url(url_mode_v2=True)` on the 66 KB `<title ` flood, 5 ms asyncio heartbeat): 27.3 ms elapsed / 27.3 ms max loop gap with the parse inline, 27.0 / 27.0 ms offloaded (the engineering adversary measured 2463-2468 ms at 96676f1f). E1 is closed end to end.
4. F2-5 edges (flag ON): node named like og:site_name + usable `<title>` + price, LLM offline -> delivered `Rasasi Hawas Ice`, 0 LLM calls; LLM `name` a list + usable title -> delivered name == title (was the list); usable LLM name -> kept; node name usable -> kept; node `Unknown` + empty title + price + LLM offline -> null_name, 0 calls; node `Unknown` + empty title + NO price + LLM `full_title` usable -> **null_name after 1 paid LLM call** (minor m3).

## 5. Findings

### MAJOR

**MAJOR-R1. The M1 class survives in the pre-gate's same_url rule: under ON, two DIFFERENT products of one query-routed store are refused at $0 as `NOT_PRODUCT_PAGE` / `same_url` with the store-page copy, where flag OFF delivers the pair.**
- Code: `url_routes._url_pre_gate` (:105-122) refuses `same_url` when `normalize_url_for_same_check(url1) == ...(url2)`; `url_extraction_service.normalize_url_for_same_check` (:137-155) drops the whole query. F2-1 taught `classify_url_path` that a query can name the product (`_PRODUCT_ROUTE_QUERY_KEYS`, `_query_names_a_product_route`), but the same-url key still ignores it, so every pair of two product pages that differ ONLY in the query is "the same url".
- Measured (probe 1, real route, POST and GET, full configuration): OpenCart (`index.php?route=product/product&product_id=1262` vs `1263`, and the root form), PrestaShop (`id_product`), WooCommerce (`?product=`), osCommerce (`products_id`) and ASP.NET (`?pid=`) same-store pairs -> flag OFF 200 with both product names (2 fetches, 1 consume); flag ON 400 `{"code": "NOT_PRODUCT_PAGE", "field": "both", "reason": "same_url", "error": "That link opens a store page, not a product page. ..."}`, 0 fetches. A working compare becomes a false refusal with false copy when the flag flips: the exact consequence RULINGS_FIX2_B4 F2-1 ruled MAJOR for M1, on the same four LIVE Bahrain OpenCart registry sources (matgarbahrain, jawaherbh, lilyorganicsbh, shop.stc.com.bh: any compare of two products of one of those stores), and comparing two products of one store is an ordinary Link-mode use.
- Not ruled: F2-6 c accepts only "two size / variant URLs of ONE product" (`?variant=`, `?attribute_pa_size=`) as a stated limit. The CLAUDE.md row's limit (11) and the PR body extend that limit to "two query-routed products of one store at the same path (OpenCart ... A vs B, read from code)" and cite F2-6 c for it; F2-6 c does not cover different products, the case is now measured (not only read from code) and it is wider than OpenCart. The fix agent raised it as open question 1; no ruling accepts it. The new RED row `test_query_routed_pdp_pair_delivers_flag_on[opencart-opencart]` uses two DIFFERENT hosts (`b4opencart` / `b4opencart2`), so no row exercises the same-store pair.
- Fix shape (for a ruling; the frozen R3 row `FX_PDP + "?utm=1#top"` -> same_url and the frozen `test_normalize_url_table` stay green under it): make the same-url key product-route-aware, i.e. keep the F2-1 allow-listed product-route query keys (`product_id`, `id_product`, `product`, and `route` when it starts `product/`) with their values, sorted, in the key, so tracking-only differences still compare equal; add PIN/RED rows: same-store OpenCart / PrestaShop / WooCommerce pairs deliver (POST and GET), the same `product_id` twice (or with a utm difference) is still `same_url`. Shapes outside the allow-list (osCommerce `products_id`, ASP.NET `pid`, any id-in-query store) then need either the allow-list widened or a stated limit with its own ruling. Alternative ruling: accept the whole class as a stated limit with an accurate citation (a new ruling, not F2-6 c) and change the owner canary step accordingly.

### minor

- m1. Citation accuracy: CLAUDE.md row limit (11) and the PR body's stated-limits paragraph cite F2-6 c for the different-products case (see MAJOR-R1); "read from code" is now measured, and the class is wider than OpenCart (PrestaShop, WooCommerce `?product=`, osCommerce, ASP.NET `?pid=`).
- m2. The `route` allow-list is broader than the PDP route: OpenCart `route=product/category`, `product/search`, `product/compare`, `product/special`, `product/manufacturer` (listing / search pages) now pass the pre-gate and the post-fetch class check (probe 2; all were refused at $0 at 96676f1f, as `homepage`). Each such link now costs a fetch, the reserve and refund, and when the page has a usable title and no price the paid extraction LLM, which can also deliver a product read off a listing page. Ruling-literal ("a `route` key whose value starts with `product/`"), unstated in the row (which says "an OpenCart `route=product/...`"). Recommend narrowing to `route=product/product` or stating it.
- m3. F2-5 residual: `_extract_from_url_v2` computes `title = raw_data.get("title") or raw_data.get("full_title")` (first TRUTHY, not first usable), so a Product node named with a placeholder (`Unknown`, `Product`) and no usable `<title>` shadows a usable LLM `full_title`: measured `UNRESOLVED_PRODUCT null_name` after one paid LLM call, while a NAMELESS node with the same LLM answer delivers (the new row `test_placeholder_llm_name_with_a_usable_llm_full_title`). The F2-5 invariant (never a delivered placeholder) holds; the behaviour is inconsistent on a rare input. Fix shape: pick the first USABLE of title / full_title.
- m4. PR body: "OpenCart / PrestaShop / WooCommerce query-routed pairs now DELIVER through the real route" holds for pairs from two different stores only (the rows use two hosts); the owner canary step "add one OpenCart query-routed Bahrain PDP pair from the registry ... -> 200" must say two DIFFERENT stores (a same-store pair is refused `same_url`, MAJOR-R1).
- m5. Pin gaps (mutant survivors, behaviour correct at HEAD): E1b (the "first 64 KiB" window of the title scan); F5e (a Product node named like the site falls back to a usable meta title: measured correct by probe 4, unpinned); X1 (the F2-4a row checks `rec.getMessage()` only, so `exc_info=True` on the transport ERROR line survives the unit file and both u8d files; the row's sentence "no record of any logger carries a pasted userinfo, path or query token" is pinned for message text only; real httpx transport messages rarely carry the url, so low risk); X5 (no 401 row in the non-2xx reason table; pre-existing GREEN shape).
- m6. X4 / fix-report open questions 2-3 (information, ruling ambiguity): an empty-valued `product_id=` / `product=` key counts as a product route (key presence, the ruling's literal text) and the `route` value check is case-sensitive; both unpinned either way.
- m7. Row wording: the `[URL-V2] fetch failed` WARNING list says "a blocked hop" but the blocked INITIAL url logs it too (`_fetch_page_v2`: `_log_fetch_failed(url, "blocked", None)` on the initial-url branch); the PR body has it right.
- m8. Row / PR Sentry sentence: the outcome is correct (ERROR -> event, WARNING -> no event), but the cause is the default `event_level=logging.ERROR` of `LoggingIntegration`; `level=logging.ERROR` (sentry_service.py:651) sets the breadcrumb level.
- m9. Hook test files NOT MEASURED here (one TIMEOUT, re-run not done; section 2).

## 6. Adversary round-2 items: closure

| item | status | evidence |
|---|---|---|
| M1 correctness MAJOR (homepage over-refusal of query-routed PDPs) | CLOSED for the homepage class at BOTH sites; residual in same_url = MAJOR-R1 | 13 + 6 + 2 RED rows green; M1a/M1b (refused again) and M1c/M1d (gclid root delivered) killed at each site; M1e killed |
| E1 engineering MAJOR (quadratic title regex on the loop) | CLOSED | `_V2_TITLE_RE` deleted; E1a killed by the 500 ms rows; probe 3: <= 4 ms on 9 adversarial pages, 27 ms end-to-end loop gap (was 2463 ms) |
| E2 engineering MAJOR (test_auth_error_log_hygiene missing from the comm set) | CLOSED | in the 184-file union; my re-derivation finds no other missing app walker/reader; green alone and in the source-scanning chunk |
| correctness minor 1 (P1/P2/P3 pin gaps) | CLOSED | P1, P2, P3 killed |
| correctness minor 2 (S01/S02/S03/S10) | CLOSED | all four killed (S01 bound pinned as five requests, the documented X2 deviation; row wording corrected) |
| correctness minor 3 (nameless Product node) | CLOSED (residual m3) | F5b killed; rows green |
| correctness minor 4 ("never Unknown Product" overclaim) | CLOSED | F5a/F5c/F5d killed; row and PR body rewritten to the F2-5 rule |
| correctness minor 5 (same_url variant links) | RECORDED (limit 11, F2-6 c) | the different-product extension is MAJOR-R1 |
| correctness minor 6 (30 s httpx timeout > 25 s deadline) | RECORDED (limit 18, F2-6 b) | `httpx.AsyncClient(timeout=30.0, ...)` at `_fetch_page_v2` |
| correctness minor 7 / eng m3 (Sentry consequence; limit 16) | RECORDED | row "Sentry consequence" sentence (m8 wording); limit 16 list re-measured: 1037 passed flag exported |
| eng m1 (P1-P3), m2 (S3/S8/S9/S5) | CLOSED | killed |
| eng m4 (prove-nothing rows) | CLOSED | replaced by the F2-4 pins |
| eng m5 (8-digit runs), m6 (`import string`, inlined helper) | RECORDED | limit 19 + PR diff notes |
| round-1 re-verifier D2/D3/D4 (folded into F2-4) | CLOSED | F2-4b / F2-4a / F2-4c pins, mutants killed |

## 7. CLAUDE.md row and PR body against the bytes

Checked sentence by sentence (row `claude_row.txt`, 14,955 B; PR body `97272c19...`). TRUE against the code and the runs: the header citations; the F2-1 exemption and its allow-list (code :182-194, :213); the tracking-only examples; the redirect cap "at most five requests, four followed hops" (`range(5)`, F2-4d); the linear `str.find` scan of the first 64 KiB with a 1,024-character unclosed bound (:229-280); every-class GC-2 post-fetch refusal (F2-4e); first-node-in-document-order (F2-4f); WebPage not a site name (F2-4b); the F2-5 name rule (`extract_generic_data_v2` :749-755, `_extract_from_url_v2` :1024-1030); the pair precedence and first-link reason (F2-4f); the log templates incl. F4-1's ERROR line; flag-OFF identity (every fix-round-2 hunk is in `classify_url_path` / `_is_challenge_page` / `extract_generic_data_v2` / `_extract_from_url_v2`, whose only callers are the flagged pre-gate and the v2 path: grep of app/); the unflagged host-only INFO lines; limits (1), (16) (1037 nodes re-measured), (18), (19); the PR body's node counts (every cited count equals the collection: e.g. test_classify_url_path_table 34, product-route 13, tracking 12, query-routed pairs 6, linear 2, verdicts 10, F2-4a 6, placeholder 5); the PR body's 25 fix-agent [pyt] lines (all present in `harness/pyt_ledger.jsonl` with the same start/end/status); ruff 58 -> 57. NOT TRUE / imprecise: limit (11) and the PR stated-limits paragraph (F2-6 c citation, MAJOR-R1 / m1); the PR F2-1 sentence and the owner canary step (m4); the WARNING list (m7); the Sentry cause (m8); limit (1)'s and the effect clause's "an OpenCart `route=product/...`" without the listing-route consequence (m2).

Context files (the relayed user request "also update context files"): this agent never edits the worktree or `sc-docs-70` (the common brief: read-only for agents). The context files this unit owns are the CLAUDE.md B4 row and the PR body; the corrections they need are exactly m1, m2, m4, m7, m8 above and the MAJOR-R1 outcome, for the next fix round or the orchestrator; the session state files (ledger, NEXT_SESSION prompt, MEMORY.md) are the orchestrator's.

## 8. Questions for the gate

1. MAJOR-R1: product-route-aware same-url key now (smallest hunk, F2-1-shaped), or a new ruling accepting the same-store class as a stated limit (with the osCommerce / `?pid=` shapes named)?
2. m2: narrow the `route` exemption to `route=product/product` (OpenCart's PDP route), or state the listing-route consequence?
3. m3: pick the first USABLE of title / full_title in `_extract_from_url_v2`?

## 9. NOT MEASURED

- The four `tests/test_precommit_hook*.py` files (one TIMEOUT on `test_precommit_hook.py`, 20/62 passed, 0 failed when cut; re-run not done; the other three not started; the owner's 21:30 shutdown).
- A re-run of the fix agent's 8 comm chunks (cited from its logs and the ledger; the CI-order set, the source-scanning chunk, the R8 pins, the metering file, the 20-file set and the auth-hygiene file re-run here).
- Live store / Sentry / Railway behaviour (rules); the registry hosts were exercised as synthetic pages of the same URL shape through the real route.
- The post-rebase run (GC-7, orchestrator).

## 10. End state

- Worktree `sc-s80-b4`: HEAD `83daa8cbc923e81abde398bdf93f84bdc4acab66`, `git status --short` empty, no `.qa-mutation.lock`, never edited. Final sha256 (bytes on disk): RED `1e8e28aeff8c7fbc9fc9bcf67e0a765ed151ad1f87b8cd9508da38ac54894e0a`, url_extraction_service `35f3756603e6fe8d2642b3375f2a2fa6590ab9cadeca42a4064a55116df7d4f9`, url_routes `9229e0b4d027e392f21e5da9edb29549f40fcde2bb22ca90c4351701ab3a59ba`, error_handler `7e539cc7b17fcc6c9b982a2ebe4b212096af57deb8c1bded330eb57e5fc6d482`, CLAUDE.md `6e51ad94ef65217f46ced4aed186cf725814b054dc0a54735aab59df86f408f2`, test_paid_route_metering `4724c308c6a5805a873a015f2a07e02850e8db5c020f46423e71208505ead73f`.
- Scratch worktree `<scratchpad>/B4_fix2_adv`: sha-equal to the worktree after the last restore; the probe file deleted from it; removed with `git worktree remove --force` (section in the final message).
- Deviation: the mutation harness (31 sequential pyt.py calls, one pytest at a time, nothing else launched meanwhile) ran as ONE background shell task so the 600 s tool limit did not cut it; every run inside it is a bounded foreground pyt.py call; it completed (exit 0) and its restore check printed OK.
- Files written (all under `<scratchpad>/B4_fix2_rv/` except this report): notes.md, mutate.py, mut_results.jsonl, mut_*.log, mutate_run.out, bak/ (byte copies), test_zz_b4rv2_probe.py, probe.jsonl, probe.log, unit_on.log, unit_off.log, u8d_unit.log, u8d.log, meter_on.log, meter_off.log, auth_log_hygiene.log, ci_order.log, srcscan.log, pins20_on.log, collect.log, collect_counts.txt, hook_a.log, mut_X1_vs_u8d.log, ruffcmp/, claude_row.txt, claude_diff.txt, svc_head.py, routes_head.py, red_prev.py, walk_any.txt, walk_app.txt, read_app.txt, fix2_union.txt, ng_baseline_ids.txt; this report `<scratchpad>/B4_fix2/REVERIFY_REPORT.md`.
