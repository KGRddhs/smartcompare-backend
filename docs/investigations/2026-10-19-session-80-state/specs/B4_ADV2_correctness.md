# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- adversary 2, lens CORRECTNESS (2026-10-20)

Verdict: **NOT_READY** (blocking 0, MAJOR 1, minor 7).

- Unit B4, worktree `C:/Users/SynAckITPC/Documents/AI/sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, HEAD verified `96676f1fe9ddc4b4bc57e3e8aec166e4c7e26d4b` at 17:39 and again at the end (18:08). `git status --short` empty at start and end; no `.qa-mutation.lock`; worktree never edited (gates there ran with PYTHONDONTWRITEBYTECODE=1).
- Agent model: claude-opus-5-5 (this agent's system prompt).
- Read: s80-common.txt (+ addendum), PLAN_S80.md sections 0-1 + B4, RULINGS_R0.md, RULINGS_BATCH1.md (Common + B4-R1..R11), GATE_B4.md, RULINGS_FIX1_B4.md, B4_GREEN_REPORT.md, B4_FIX1_REPORT.md, B4_FIX1_REVERIFY.md, PR_BODY.md (sha ea1a3ae4), the CLAUDE.md row, the full diff 81df2b64..96676f1f of the 3 app files, the RED file.
- Scratch worktrees (both removed, `git worktree list` shows no B4_adv2 entry; neither held node_modules): `<scratchpad>/B4_adv2_correctness` (detached 96676f1f, RED file copied byte-exact from the worktree: 546fc27d...8b46; app/test/CLAUDE.md hashes equal to the worktree before the first mutant and after the last) and `<scratchpad>/B4_adv2_base` (detached 81df2b64, RED file copied in for its helpers).
- Hashes at end (worktree): RED 546fc27d07579808..., url_extraction_service 0abf3b950898fd10..., url_routes 9229e0b4d027e392..., error_handler 7e539cc7b17fcc6c..., test_paid_route_metering 4724c308c6a5805a..., CLAUDE.md 8502da3b038953d7... (= the fix and re-verify reports).
- No .env read/copied/printed; no flag set outside one runner call; no network (every netguard line below: 0 blocked, or sentinel-class nodes already in the baseline).

## 1. Runs (every pytest through pyt.py, one at a time)

```
unit ON  (worktree): 253 passed, 11 warnings in 8.48s; [hermeticity] sentinel checked 253; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4a2c-unit-on start=2026-10-20 17:45:56 end=2026-10-20 17:46:06 elapsed=10s bound=600s status=OK rc=0
unit OFF (worktree): 253 passed, 11 warnings in 57.63s; sentinel 253; netguard 0
[pyt] tag=b4a2c-unit-off start=2026-10-20 17:46:20 end=2026-10-20 17:47:29 elapsed=69s bound=600s status=OK rc=0
CI-order set, 13 files, flag OFF (worktree): 904 passed, 13 warnings in 16.93s; sentinel 904; netguard blocked 10 attempt(s) from 10 node(s) (sentinel neutralized.supabase.invalid, baseline class)
[pyt] tag=b4a2c-ci-order start=2026-10-20 18:02:30 end=2026-10-20 18:02:48 elapsed=19s bound=1200s status=OK rc=0
tests/test_sentry_channels_u8d_unit.py ALONE: 141 passed, 1 warning in 8.53s; netguard 0
[pyt] tag=b4a2c-test_sentry_channels_u8d_unit start=2026-10-20 18:05:46 end=2026-10-20 18:05:56 elapsed=10s bound=600s status=OK rc=0
tests/test_sentry_channels_u8d.py ALONE: 131 passed, 1 warning in 6.21s; netguard 0
[pyt] tag=b4a2c-test_sentry_channels_u8d start=2026-10-20 18:05:57 end=2026-10-20 18:06:05 elapsed=8s bound=600s status=OK rc=0
flag-OFF identity probe @HEAD (240 nodes): 240 passed, 11 warnings in 4.80s; sentinel 240; netguard 0
[pyt] tag=b4a2c-identity-head start=2026-10-20 17:58:39 end=2026-10-20 17:58:45 elapsed=6s bound=600s status=OK rc=0
flag-OFF identity probe @BASE 81df2b64 (240 nodes): 240 passed, 11 warnings in 4.88s; sentinel 240; netguard 0
[pyt] tag=b4a2c-identity-base start=2026-10-20 17:58:55 end=2026-10-20 17:59:01 elapsed=6s bound=600s status=OK rc=0
flag-ON probes @HEAD (145 nodes: R-A3 matrix 136, registry scan, PDP shapes, same_url, LLM name, mid-flip): 145 passed, 11 warnings in 4.16s; sentinel 145; netguard 0
[pyt] tag=b4a2c-probe-on start=2026-10-20 17:59:46 end=2026-10-20 17:59:51 elapsed=6s bound=600s status=OK rc=0
OpenCart / query-routed PDP route probe @HEAD (12 nodes, ON+OFF): 12 passed, 11 warnings in 2.84s
[pyt] tag=b4a2c-opencart-head start=2026-10-20 18:01:43 end=2026-10-20 18:01:47 elapsed=4s bound=600s status=OK rc=0
OpenCart / query-routed PDP route probe @BASE (12 nodes): 12 passed, 11 warnings in 2.74s
[pyt] tag=b4a2c-opencart-base start=2026-10-20 18:01:49 end=2026-10-20 18:01:53 elapsed=4s bound=600s status=OK rc=0
nameless-Product-node probe @HEAD (4 nodes): 4 passed, 10 warnings in 2.73s
[pyt] tag=b4a2c-nameless start=2026-10-20 18:04:38 end=2026-10-20 18:04:42 elapsed=4s bound=600s status=OK rc=0
```
0 TIMEOUTs. Probe files (notes folder): test_zz_b4adv2_identity.py, test_zz_b4adv2_probe_on.py, test_zz_b4adv2_opencart.py, test_zz_b4adv2_nameless.py; outputs identity_{base,head}.jsonl + identity_diff.txt, probe_on.jsonl + probe_on_summary.txt, opencart_{base,head}.jsonl, nameless.jsonl.

## 2. Mutation table (scratch worktree; harness `B4_adv2/mutate.py` + `mutants_def.py`: lock -> byte copy -> exact edit matching once (CRLF-adapted) -> pyt.py on the full unit file (+ the u8d unit file where named) -> restore -> sha256 compare; every restore sha-equal; lock removed; results `mut_results.jsonl`, logs `mut_<name>.log`)

| # | mutant | result | first killing node(s) (E-lines all AssertionError) | [pyt] |
|---|---|---|---|---|
| G10 | normaliser-stage image coercion removed (`"image_url": raw.get("image_url")`) | KILLED (1) | test_normaliser_coerces_a_raw_image_list_flag_on | tag=b4a2c-G10_normaliser_coercion_removed start=17:52:50 end=17:53:00 elapsed=10s status=FAIL rc=1 |
| R8a | SECOND ERROR with the base `Failed to fetch URL host` prefix in the v2 except arm | KILLED (3) | test_sentry_channels_u8d_unit.py::TestR8SourceLines::test_u8d_red_r8_in_except_lines_no_user_content[url_extraction_fetch_failed] (+ R12 POST/GET) | tag=b4a2c-R8a_second_error_base_prefix elapsed=22s status=FAIL rc=1 |
| R8b | `[URL-V2] fetch failed host=%s reason=%s type=%s` demoted to WARNING | KILLED (2) | test_transport_error_is_store_unreadable[POST|GET] (R12) | tag=b4a2c-R8b_distinct_template_warning elapsed=30s status=FAIL rc=1 |
| P1 | WebPage counted as a site name | SURVIVED (253 passed) | - (D2 pin gap) | tag=b4a2c-P1_webpage_is_site_name elapsed=9s status=OK rc=0 |
| P2 | v2 `[SSRF] Blocked redirect to host=` prints the full target url | SURVIVED (253) | - (D3 pin gap) | tag=b4a2c-P2_ssrf_redirect_full_url elapsed=12s status=OK rc=0 |
| P3 | `Detected retailer` label = raw netloc for an unknown host | SURVIVED (253) | - (D4 pin gap) | tag=b4a2c-P3_retailer_label_raw_netloc elapsed=9s status=OK rc=0 |
| S01 | `_fetch_page_v2` bound range(5) -> range(6) | SURVIVED (253) | - (R42 asserts `<= 6` requests) | tag=b4a2c-S01_redirect_bound_6 elapsed=9s status=OK rc=0 |
| S02 | post-fetch class check refuses only `homepage` (GC-2: every class) | SURVIVED (253) | - (R13 pins homepage only) | tag=b4a2c-S02_postfetch_homepage_only elapsed=11s status=OK rc=0 |
| S03 | pair `reason` taken from the LAST failing link carrying the chosen code | SURVIVED (253) | - (no same-code / different-reason pair row) | tag=b4a2c-S03_reason_from_last_link elapsed=9s status=OK rc=0 |
| S04 | error handler passes a non-str field/reason | KILLED (3) | test_error_handler_passthrough_on[*] | tag=b4a2c-S04_handler_non_str_passthrough elapsed=10s status=FAIL rc=1 |
| S05 | route refusal `reason` forced to "unknown" | KILLED (20) | test_both_urls_403_field_both[*] ... | tag=b4a2c-S05_route_reason_constant elapsed=10s status=FAIL rc=1 |
| S06 | two '' same-url keys make a same_url refusal | KILLED (1) | test_normalize_url_table | tag=b4a2c-S06_two_empty_keys_same elapsed=9s status=FAIL rc=1 |
| S07 | same-url key keeps the query | KILLED (3) | test_pregate_same_url_after_normalisation[*-query-fragment], test_normalize_url_table | tag=b4a2c-S07_same_check_keeps_query elapsed=9s status=FAIL rc=1 |
| S08 | pair `field` url1/url2 swapped | KILLED (12) | test_challenge_page_is_store_unreadable[*] ... | tag=b4a2c-S08_pair_field_swapped elapsed=10s status=FAIL rc=1 |
| S09 | category product-segment veto removed | KILLED (1) | test_classify_url_path_table[/collections/men/products/sauvage-None] | tag=b4a2c-S09_category_veto_removed elapsed=9s status=FAIL rc=1 |
| S10 | `extract_generic_data_v2` takes the LAST Product node | SURVIVED (253) | - ("first node in document order" unpinned) | tag=b4a2c-S10_last_product_node elapsed=9s status=OK rc=0 |
| S11 | site-name walk stops at depth 0 (no @graph) | KILLED (11) | test_is_usable_title_table, test_mixed_codes_precedence[*] | tag=b4a2c-S11_site_names_no_graph_walk elapsed=12s status=FAIL rc=1 |
| S12 | site-name comparison removed from is_usable_title | KILLED (11) | test_is_usable_title_table ... | tag=b4a2c-S12_site_name_check_removed elapsed=12s status=FAIL rc=1 |
| S13 | deadline x4 | KILLED (6) | test_deadline_yields_timeout_503[*], test_non_delivery_per_r_a3_every_code[*-TIMEOUT-*] | tag=b4a2c-S13_deadline_x4 elapsed=12s status=FAIL rc=1 |
| S14 | key_differences include `similar` | KILLED (2) | test_recommendation_and_key_differences_filled[*] | tag=b4a2c-S14_key_differences_include_similar elapsed=9s status=FAIL rc=1 |
| S15 | GET pre-gate checks url1 twice | KILLED (21) | GET rows | tag=b4a2c-S15_get_pregate_url1_twice elapsed=14s status=FAIL rc=1 |
| S16 | blocked outcome reported as fetch_error | KILLED (2) | test_route_fetch_blocked_or_capped_is_store_unreadable[*-blocked_hop-blocked] | tag=b4a2c-S16_blocked_reported_as_fetch_error elapsed=10s status=FAIL rc=1 |
| S17 | route drops UNRESOLVED_PRODUCT from its refusal codes | KILLED (2) | test_v09_storefront_pages_unresolved[*] | tag=b4a2c-S17_route_drops_unresolved_code elapsed=9s status=FAIL rc=1 |
| S18 | handler passthrough drops STORE_UNREADABLE | KILLED (15) | test_both_urls_403_field_both[*] ... | tag=b4a2c-S18_handler_drops_store_unreadable elapsed=11s status=FAIL rc=1 |
| S19 | 3xx reason dropped | KILLED (1) | test_non_2xx_reason_table[302-http_3xx] | tag=b4a2c-S19_3xx_reason_dropped elapsed=14s status=FAIL rc=1 |
| S20 | no_product_node rule ignores placeholders/site names | KILLED (2) | test_v09_storefront_pages_unresolved[*] | tag=b4a2c-S20_unresolved_placeholder_check_dropped elapsed=11s status=FAIL rc=1 |

Counts: 26 applied; KILLED 19 (G10, R8a, R8b + 16 spec mutants), SURVIVED 7 = P1/P2/P3 (expected, D2/D3/D4 accepted unpinned by F4-4) + S01/S02/S03/S10 (pin gaps; the BEHAVIOUR behind S02 and S03 was measured correct in section 3). Every kill an AssertionError.

## 3. Runtime truth of the claims

- **Flag-OFF identity (PLAN section 0 items 4-5): CONFIRMED.** The same probe file run at base 81df2b64 and head 96676f1f: 20 scenarios (two PDPs delivered, homepage pair, search/cart/category vs PDP, same_url, url1 403/404/500, both 403, 2xx challenge, transport ConnectTimeout, redirect to the root, redirect to 169.254.169.254, storefront pages, raw image LIST, LLM offline, verdict error -> LLM_UNAVAILABLE 503, anonymous delivery, metering OFF) x POST/GET x OFF spellings {unset, "false", "off"} x ENABLE_PRICE_PARSE_OFFLOAD {unset, true}, FULL configuration (metering + truth ON, authed, transport, LLM fake, verdict fake, ledger) = 240 records: status diffs 0, body diffs 0 (incl. the pinned `{"success": false, "error": "Could not extract both products", "code": "BAD_REQUEST"}` 400 and the LLM_UNAVAILABLE 503), ledger diffs 0 (consumes/refunds/lifetime/history/search_logs rows/labels/fetched urls/LLM calls), app.* log records: same count and the same (logger, level) sequence in all 240; the ONLY message deltas are the three unflagged host-only INFO lines (`URL comparison request`, `Detected retailer`; base `Detected retailer: fragrancex.com for URL: https://.../products/...` -> head `Detected retailer: unknown for host www.fragrancex.com`). The SSRF 400 body and the W4-13 url rows are pinned by P5/P36 (green in the unit runs above).
- **R-A3 on every new exit (flag ON): CONFIRMED.** 136 route runs = 17 exits x POST/GET x metering ON/OFF x authed/anonymous (pre-gate homepage, pre-gate same_url, delivery, url1 403, url2 404, 2xx challenge, ConnectTimeout, ReadTimeout, redirect to root/search/cart/category/account, SSRF-blocked hop, unresolved pair, LLM is_product_page false, verdict error): pre-gate = 0 consume / 0 refund / 0 rows; every coded non-delivery with metering ON + authed = consume 1, refund exactly 1, lifetime 0, history 0, one failure row with the code's constant; anonymous / metering OFF = nothing consumed or refunded; delivery = refund 0, lifetime 1, history ['url']. Codes/fields/reasons: STORE_UNREADABLE url1 http_403 / url2 http_4xx / challenge / fetch_error (both ConnectTimeout and ReadTimeout) / blocked; NOT_PRODUCT_PAGE url1 homepage|search|cart|category|account (GC-2 every class works, though only homepage is pinned: S02); UNRESOLVED_PRODUCT both no_product_node / url1 not_product_page; TIMEOUT via R16/R35 (unit). ERROR records: exactly one `[URL-V2] fetch failed host=www.fragrancex.com reason=fetch_error type=...` per transport-failing link, none elsewhere.
- **Error-handler mapping and scope: CONFIRMED.** Passthrough only for the three B4 codes and str values (S04/S18 killed; R32 scope rows). Mid-request flip (route ON, handler OFF, monkeypatched reader): 400 `{"success","error","code":"STORE_UNREADABLE"}` with field/reason dropped, refund 1 = stated limit 12. TIMEOUT is the structured 503 (code TIMEOUT), never the bare-503 FEATURE_DISABLED (PLAN 0 item 3).
- **Contract freeze (PLAN section 0):** OFF byte-identical (above). ON: delivered key set unchanged (R21), additive `field`/`reason` on error envelopes only, `products[i].image_url` str-or-null (the stated B4-R11 retype), no `metadata` (R0-1). Build 3 client (`HomeScreen.tsx` runUrlCompare): a new 400 code renders the default copy, TIMEOUT the timeout copy. Flag stays OFF through review (activation precondition in the row): PLAN 0 item 2 respected.
- `_QUALITATIVE_WINNER_REASON` is callable (response_builder.py:342 call site); the R22 fallback path is real.
- Client-visible `product.name`: the Results tile (`SmartCompareApp/src/components/results/ResultsContent.tsx:292`) and the share text (`ResultsScreen.tsx:539`) render `products[i].name`, not `full_name` (relevant to minor 4).

## 4. Findings

### MAJOR

**M1. The pre-gate refuses real product pages whose PDP route lives in the query string of a root or `/index.php` path (OpenCart, PrestaShop, WooCommerce plain permalinks) as `NOT_PRODUCT_PAGE` / `homepage`, at $0, before any fetch.**
- Code: `url_extraction_service.classify_url_path` (HEAD :177-202) returns "homepage" from `price_service._NOT_A_PDP_HOME_PATH_RE` (`^/?$|...|^/index\.(?:html?|php)$`, price_service.py:13019) on the PATH alone; `url_routes._url_pre_gate` (:105-122) refuses on it before the reserve, and `_extract_from_url_v2` (:920-923) applies the same class to the FINAL url after a redirect. In price_service that regex is one signal inside `classify_not_a_pdp`, which returns None for "every page that declares a Product node" (price_service.py:13196-13202); B4 reuses it as a sole, query-blind, pre-fetch rule with no node veto.
- Measured (registry scan over every url string in `data/*.json`, 519 urls, 83 classified): the `sample_url` / `sample_pdp_url` of four LIVE Bahrain sources in `data/bh_gcc_sources.json` (OpenCart, `genuine_method: page_scrape_jsonld`, `status: live`) classify as `homepage`: `matgarbahrain.com/index.php?route=product/product&product_id=1262`, `jawaherbh.com/...product_id=4154`, `lilyorganicsbh.com/...product_id=2058`, `shop.stc.com.bh/...product_id=5313` (+ `leenaz.net`, dead). Round-2/round-4 candidate files record them as curl-readable JSON-LD Product pages with BHD prices.
- Measured through the route (synthetic pages, same URL shapes, Product nodes with prices): POST and GET, pairs OpenCart/OpenCart, PrestaShop `index.php?id_product=12&controller=product` / OpenCart, WooCommerce `/?product=dior-sauvage-edp` / OpenCart: flag OFF (head) and base -> 200 delivered with both product names, 2 fetches, 1 consume; flag ON -> 400 `{"code": "NOT_PRODUCT_PAGE", "field": "both", "reason": "homepage", "error": "That link opens a store page, not a product page. ..."}`, 0 fetches. A working compare becomes a false refusal with false copy when the flag flips.
- Not stated: limit (1) covers a single-page store / a locale root that 302s; limit (3) lists regex MISSES, not this over-refusal. The RED table pins it as intended (`test_classify_url_path_table[/index.php-homepage]`), so no gate saw it.
- Fix shape (for a ruling; R-A7/B4-R7 keep the refusal side path-only): a root or `/index.(html?|php)` path is `homepage` only when the query carries no product-route key (`route=product/`, `product_id`, `id_product`, `product=`, `p=`); a blanket "any non-empty query exempts" would break the frozen R1 rows (`/?gclid=abc123`, `/?gbraid=xyz&gad_source=1` -> homepage). Same exemption at the post-fetch final-url check. Add PIN rows for the three shapes (pre-gate and post-redirect).

### minor

1. **D2 / D3 / D4 pin gaps (F4-4 accepted contract, no pin): P1, P2, P3 survive the full unit file (253 passed each).** Behaviour measured correct at HEAD (`_V2_SITE_NAME_TYPES = {"Organization","WebSite"}` :241; host-only v2 `[SSRF]` lines :409/:422/:431; `_retailer_log_name` :128-134). Rows to add: a WebPage-name == title PDP that must not be refused at $0; a host-only assertion on the v2 `[SSRF] Blocked redirect to host=` text (R41 matches the prefix only); a `user:pass@` unknown-host link for the `Detected retailer` label (R34 uses a userinfo-free fragrancex url).
2. **Further pin gaps (spec mutants that survive):** S01 the 5-hop bound (R42 accepts <= 6 requests; the row says "the 5-hop redirect cap"); S02 GC-2 post-fetch refusal for search/cart/account/category (behaviour measured correct, section 3; only homepage pinned, R13 / R14b); S03 the pair `reason` is the FIRST failing link's when both carry the chosen code (e.g. url1 403 + url2 404 -> http_403; unpinned); S10 "first Product node in document order" (R19 has_variant has one member).
3. **B4-R1 deviation on a Product node without `name`.** `extract_generic_data_v2` sets `data["title"] = item.get("name")` even when None and then skips the meta fallback on key PRESENCE (`if "title" not in data`, :691) -- the same key-presence class the unit fixed for og:image -- and step (f) reads only `title` / `full_title`, never the LLM `name`. Measured (page `<title>Rasasi Hawas Ice</title>` + og:title, Product node with price and no name): LLM `{"name": null}` -> UNRESOLVED_PRODUCT `null_name`; LLM `{"name": "Hawas Ice", "full_title": null}` -> `null_name` (flag OFF delivers name "Hawas Ice"); LLM offline -> `null_name`. B4-R1: "null_name only when the page title is unusable (a usable title keeps the page with name == title)". R44 pins only the EMPTY-`<title>` case. Rare input (a nameless Product node is invalid schema.org), so minor.
4. **"never a `success: true` with `Unknown Product`" (CLAUDE.md row, PR body) is an overclaim.** Under ON a page with a usable title and no price whose LLM answer carries a placeholder `name` is delivered with that name: measured `name` == "Unknown Product" / "Unknown" / "N/A" / "Product" / "Rasasi" (site name), `full_name` == "Rasasi Hawas Ice", `success: true`. The client renders `product.name` (ResultsContent.tsx:292, share text ResultsScreen.tsx:539). Not a regression vs OFF (same merge), but the residual of the V09 class the row says is closed. Fix: apply `is_usable_title` to the merged `name` under ON (fall back to the title), plus a row.
5. **same_url drops the query, so variant links of ONE product are refused with the store-page copy.** Measured `_url_pre_gate`: Shopify `/products/sauvage?variant=111` vs `?variant=222` -> `{"field":"both","reason":"same_url"}`; WooCommerce `?attribute_pa_size=50ml` vs `100ml` -> same_url. R-A5 calls the same perfume at two sizes a valid pair; the user sees "That link opens a store page, not a product page." Limit 11 does not mention query-borne variants. (http vs https and `:443` vs none are not same: as stated.)
6. **The v2 fetch timeout (httpx `timeout=30.0`, `_fetch_page_v2` :415) exceeds the 25 s deadline**, so a stalled/tarpitting store always surfaces as the 503 TIMEOUT ("give it another tap": a retry repeats the 25 s and the reserve/refund) and never as STORE_UNREADABLE `fetch_error`. Read from code (not measured live; httpx timeouts are not exercised by the MockTransport); not stated in the row.
7. **Sentry consequence of the non-2xx WARNING is not in the CLAUDE.md row** (re-verifier minor 2, still open): flag ON, a 403/404/5xx link (V02 fragrancex class) logs WARNING and no longer creates the Sentry event that base's `raise_for_status` -> ERROR line created (the evidence channel that found V02, R0-7). The `[URL-V2] outcome=http_error` INFO line and the search_logs failure row remain the counters.

## 5. Prove-nothing / prove-less rows
- `test_classify_url_path_table[/index.php-homepage]` pins the M1 defect as intended behaviour (and nothing pins a query-routed PDP).
- `test_fetch_page_v2_caps_redirect_chain` (R42): `1 <= fetched <= 6` does not prove the 5-hop bound (S01).
- `test_redirect_to_homepage_is_not_product_page_post_fetch` (R13): homepage only; GC-2's other four classes unpinned (S02).
- `test_mixed_codes_precedence*` (R14/R14b): different codes only; same-code reason choice unpinned (S03).
- `test_pdp_image_is_first_https_string[has_variant]`: one member; first-node order unpinned (S10).
- `test_fetch_page_v2_blocks_redirect_to_metadata` (R41): prefix match only, host-only text unpinned (P2).
- `test_info_lines_print_host_only` (R34): no userinfo host, so the D4 label rule is unpinned (P3).
- `test_is_usable_title_table` (R31): no WebPage node (P1).
- `test_never_unknown_product_flag_on` (R28) / `test_null_name_only_when_the_title_is_unusable` (R44): cover the default-title path only; the LLM-merged placeholder `name` (minor 4) and the usable-`<title>` nameless node (minor 3) are not exercised.

## 6. Information (not findings): main-side collisions for the GC-7 rebase
`git merge-tree --write-tree --name-only 95cf6f86 96676f1f` (objects only, no ref or worktree change): CONFLICT (content) in CLAUDE.md, tests/test_model_config_enforced.py, tests/test_prompt_fence.py, tests/test_s71_u13_compare_auth_required.py, tests/w4_11_prompt_digest_recorder.py (B3 #365 added its flag to the same clear lists); app/api/url_routes.py auto-merges (B1 #364 adds `capture_result_status(result, "url", ...)` at the delivery exit only; B4's coded refusals raise before it, consistent with B1's "one status message per delivery exit").

## 7. NOT MEASURED
- Live behaviour of any real store (rules); the M1 hosts were measured as registry data + synthetic pages of the same URL shape through the real route.
- Minor 6 (timeout arithmetic) is read from code.
- The comm set, ruff/py_compile, the CLAUDE.md readers and the hook files (engineering lens; the CI-order set and the u8d R8 files were re-run here).
- The post-rebase run (GC-7, orchestrator).
