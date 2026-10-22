# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- fix round 3 report (2026-10-22)

- Unit B4, flag `ENABLE_URL_MODE_V2` (default OFF, read per call). Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, spec base `81df2b64` (not rebased, GC-7).
- Start: HEAD `83daa8cbc923e81abde398bdf93f84bdc4acab66` verified, `git status --short` empty, no `.qa-mutation.lock`, RED file sha `1e8e28aeff8c7fbc9fc9bcf67e0a765ed151ad1f87b8cd9508da38ac54894e0a` re-hashed and equal.
- End: HEAD **`0aac07f1f7304e61fa5cac86935c9306f08605d0`** (ONE commit through the pre-commit hook, `All checks passed!`; `git add -- <paths>` + `git commit -m <subject> -m <trailer> -- <paths>`; no push, no rebase, no stash, no checkout). `git status --short` empty after the commit; working copy byte-identical before and after it (`precommit_hashes.txt` == `postcommit_hashes.txt`); the committed RED blob hashes to the working-copy sha.
- Agent model: claude-opus-5-5 (this agent's system prompt). Trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. The relayed user request ("dont forget to run /synack-build-orchestrator"): the skill was loaded at the start and its Step 5 loop (tests first and failing for the right reason, minimal code to green, gates, then commit) is the procedure below; orchestration, review gates and PRs stay the orchestrator's.
- Read: s81-common.txt (twice), RULINGS_FIX3_B4.md (twice), B4_FIX2_REVERIFY.md, RULINGS_FIX2_B4.md, RULINGS_FIX1_B4.md, GATE_B4.md, RULINGS_BATCH1.md (B4 section), B4_FIX2_REPORT.md, B4_PR_BODY_DRAFT_FIX2.md (sha `97272c19...`), the CLAUDE.md B4 header and row. Not opened: B4_UNIT_SPEC.md, B4_SPEC_REVIEW.md, B4_GREEN_REPORT.md, B4_FIX1_REPORT.md, B4_ADV2_correctness.md, B4_ADV2_engineering.md (the round-2 re-verifier report and the fix-2 rulings cite what this round needed; the code and the RED file were read directly).
- No .env read, copied or printed; no flag set outside one runner call; no network; no scratch worktree created (mutation in place under the lock, see deviations).

## Files (final sha256 = bytes on disk = the committed working copy)

| file | +/- (83daa8cb..0aac07f1) | sha256 before (83daa8cb) | sha256 after (0aac07f1) | bytes > 127 before/after | line endings |
|---|---|---|---|---|---|
| tests/test_s80_url_mode_v2.py (RED, append only) | +340/-0 | 1e8e28aeff8c7fbc9fc9bcf67e0a765ed151ad1f87b8cd9508da38ac54894e0a | **bac8730196c75769e672646e6f1dee7901bfb3fb275af1d84af6a9d97517f1d9** | 0/0 | LF (as frozen); 119,355 B, 2,416 lines; the first 101,070 B are the 1e8e28ae file |
| app/services/url_extraction_service.py | +50/-18 | 35f3756603e6fe8d2642b3375f2a2fa6590ab9cadeca42a4064a55116df7d4f9 | b0d7b8d96aec34352dccdf008d29ddb60fdd03779cb28cc19cfddcf29cc49f68 | 18/18 | CRLF 1395/1395 (blob LF) |
| CLAUDE.md (the SESSION 80 B4 header + row, 2 lines in place) | +2/-2 | 6e51ad94ef65217f46ced4aed186cf725814b054dc0a54735aab59df86f408f2 | c4af580314acbf212b0368d87d6ed5648bc1a66712edde79db6f508b739bd1e6 | 3979/3979 | CRLF 938/938 |

Added-line sweep (`sweep.py` over `git diff -U0`, 392 added lines): 0 non-ASCII, 0 @gmail, 0 +973, 0 8+-digit runs, 0 sk-/AKIA/xox/eyJ/credentialed-URL/PEM. Byte copies before the first edit: `B4_fix3/before/` + `SHA256SUMS.txt` (and `CLAUDE.md.pre_row_edit`).

Notes-folder files (not committed, all under `<scratchpad>/B4_fix3/`): `PR_BODY.md` sha256 `ddb7487437c502efe6530a3069cb314f0d6d5adb6e1be604a5d4d3e43ff7f98a` (40,669 B, LF; 4 bytes > 127 = the required robot attribution line), `pr_body_build.py`, `pr_fix3_section.md`, `pr_gates.md`, `red_append3.py` (the appended block as first written), `mutate3.py`, `mut_results.jsonl` (23 rows), `mut_*.log`, `base_run.py`, `claude_row_edit.py`, `claude_row_before.txt`, `sweep.py`, `netguard_check.py`, `comm_ref.txt`, `comm_walk.txt`, `comm_extra.txt`, `comm_union.txt`, `comm_chunk_00..03`, `notes.md`, every `*.log` below.

## What changed (smallest hunks; every code change is in a function only the flagged path reaches)

- **F3-1 (MAJOR-R1)**: `normalize_url_for_same_check` builds the base key as before and appends `"?" + urlencode(pairs)` when the query carries product-route markers, `pairs = _product_route_pairs(parts.query, _SAME_URL_PRODUCT_QUERY_KEYS)`. New `_SAME_URL_PRODUCT_QUERY_KEYS = _PRODUCT_ROUTE_QUERY_KEYS | {"products_id"}` (no `pid`). New helper `_product_route_pairs(query, keys)`: `parse_qs(query, keep_blank_values=True)` (percent-decoding), keys `.lower()`, values `.strip()`, `("route", "product/product")` only when the value lower-cases to exactly `product/product`, an allow-listed key only with a non-empty value, `sorted(set(pairs))`. `urlencode` joins the existing `urllib.parse` import. The only caller of the key is `url_routes._url_pre_gate` (flagged).
- **F3-2 / F3-4**: `_query_names_a_product_route(query)` is now `bool(_product_route_pairs(query, _PRODUCT_ROUTE_QUERY_KEYS))`, so the one helper serves both F2-1 sites (`classify_url_path` = the pre-gate and the post-fetch final-url check) and the F3-1 key: exact `product/product` route value (case-insensitive), non-empty values.
- **F3-3**: `_extract_from_url_v2`: `title = next((t for t in (raw_data.get("title"), raw_data.get("full_title")) if is_usable_title(t, site_names)), None)`; `None` -> `UNRESOLVED_PRODUCT` `null_name` (as before); an unusable `raw_data["title"]` is set to None so `normalize_product_data` (`title or full_title`) ships the usable full title. For a nameless node the raw title is already None (no change; `extraction_method` unchanged); for a usable title nothing changes.
- **Docstrings/comments**: `normalize_url_for_same_check`, `_query_names_a_product_route`, `_extract_from_url_v2` item (f), the two new constants.
- **F3-6**: the CLAUDE.md header cites F3-1..F3-7; the row's effect clause (exact `route=product/product` + the listing consequence; non-empty values; the same-url key's product-route keys), the title-scan window and the 401 reason (F3-5), the F3-3 sentence, the WARNING list (blocked initial url or hop, m7), the X1 pin, the Sentry cause (m8), limit (1) (listing routes, empty values, `products_id` key-only, the root `?pid=` link), limit (11) (F3-1 with the measured class; ASP.NET `?pid=` stays), limit (16) (fix-round-3 bytes, 408 nodes), the canary (two DIFFERENT stores AND one same-store OpenCart pair -> 200). PR body draft `B4_fix3/PR_BODY.md` from the state-folder fix-2 copy: the same corrections plus a "Fix round 3" section and the fix-round-3 gates.

## RED step (RED file new sha `bac87301...f1d9`)

73 nodes appended (no existing row changed). Run on the `83daa8cb` code bytes:
```
50 failed, 358 passed, 11 warnings in 11.69s; every failure location line AssertionError (50/50), no other class; [hermeticity] sentinel checked 408 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4f3-red start=2026-10-22 16:05:17 end=2026-10-22 16:05:30 elapsed=13s bound=600s status=FAIL rc=1
```
After the GREEN step two PIN refinements were made (the `listing-route-not-a-key` row's values `("?route=product/category&path=20", "?route=product/category&path=25")` -> `("?route=product/category&product_id=5", "?product_id=5")`, which made it a real guard against R1; two docstrings made accurate). Re-proof on the `83daa8cb` service bytes (swapped in under the lock, restored, sha-verified `b0d7b8d9... OK`) with the RED file at `c10c15c3...` (= the final file minus one docstring):
```
50 failed, 358 passed, 11 warnings in 14.36s; 50 AssertionError; the same failing set as b4f3-red; sentinel 408; netguard 0
[pyt] tag=b4f3-red2 start=2026-10-22 16:53:40 end=2026-10-22 16:53:56 elapsed=16s bound=600s status=FAIL rc=1
```
RED file sha history this round: `1e8e28ae` (frozen in) -> `b6753884cd18a93f7d3e00fd8f348bce17e4bfae5aa5358faf30d7aa3770238a` (after the append, the b4f3-red run) -> `c10c15c3a8acf49f94a82bd5ec4b7dedae9720fcb09aca66b5d22a014c91e563` (key-row values + one docstring) -> **`bac8730196c75769e672646e6f1dee7901bfb3fb275af1d84af6a9d97517f1d9`** (one docstring; committed).

New rows (class; at 83daa8cb; killed mutants on the fix bytes):

| row | class | at 83daa8cb | killed by |
|---|---|---|---|
| `test_same_store_query_routed_pair_is_not_same_url_flag_on[POST|GET x opencart-index|opencart-root|prestashop|woocommerce|oscommerce]` (10) | RED (F3-1, real route) | FAIL 400 same_url, 0 fetches | K1 (10), K5 (oscommerce x2) |
| `test_same_url_still_refused_for_tracking_pid_and_identical_pairs[POST|GET x aspnet-pid|identical|same-id-tracking]` (6) | PIN (F3-1 guard) | pass | K2 (aspnet-pid, same-id-tracking), K6 / K6b (aspnet-pid) |
| `test_same_url_key_keeps_product_route_values[opencart|woocommerce|oscommerce|prestashop]` (4) | RED (F3-1, the key) | FAIL equal keys | K1 (4), K5 (oscommerce) |
| `test_same_url_key_equal_when_only_dropped_keys_differ[tracking-dropped|key-case|route-value-case|percent-decoded|value-stripped|order|empty-value-dropped|pid-not-a-key|listing-route-not-a-key]` (9) | PIN (F3-1/F3-2/F3-4 in the key) | pass | K2 (all 9), K3 (key-case), R2 / R4 (route-value-case), K4b (percent-decoded, value-stripped), K4 (value-stripped), K7 (order), K8 / K8b (empty-value-dropped), K6 / K6b (pid-not-a-key), R1 / R4 (listing-route-not-a-key) |
| `test_classify_url_path_listing_route_is_homepage[/index.php|/ x 5 listing routes]` (10) | RED (F3-2) | FAIL None | R1 (10) |
| `test_classify_url_path_product_product_route_is_case_insensitive[/index.php?route=PRODUCT/PRODUCT|/?route=Product/Product]` (2) | RED (F3-2) | FAIL homepage | R2 (2), R3, R4 |
| `test_classify_url_path_product_product_route_stays_exempt[route=product/product&product_id=7|route=PRODUCT/PRODUCT&product_id=7]` (2) | PIN (the ruling's two exempt rows) | pass | R5 (both), R4 (upper-case row) |
| `test_listing_route_link_refused_before_reserve[POST|GET x 5]` (10) | RED (F3-2, pre-gate site, real route) | FAIL (fetched) | R1 (10) |
| `test_redirect_to_listing_route_is_homepage_post_fetch[5]` (5) | RED (F3-2, post-fetch site) | FAIL (extracted) | R1 (5) |
| `test_classify_url_path_empty_product_key_is_homepage[/index.php?product_id=|/?product=|/index.php?id_product=|/?product=%20|/?gclid=x&product_id=]` (5) | RED (F3-4) | FAIL None | K8 (5), K4 (`%20`) |
| `test_classify_url_path_non_empty_value_and_pid_limit[product-id-5-exempt|pid-root-homepage]` (2) | PIN (F3-4 / F3-1 guards) | pass | K8b (product-id-5-exempt), K6b (pid-root-homepage) |
| `test_placeholder_node_name_gives_way_to_a_usable_llm_full_title[Unknown|Product|Unknown Product|Rasasi]` (4) | RED (F3-3) | FAIL null_name after 1 LLM call | T1 (4), T2 (4) |
| `test_challenge_title_past_the_scan_window_is_not_read` | PIN (F3-5, E1b) | pass | E1b |
| `test_node_named_like_the_site_takes_the_usable_meta_title` | PIN (F3-5, F5e) | pass | F5e |
| `test_transport_error_line_carries_no_exception_info` | PIN (F3-5, X1) | pass | X1 |
| `test_non_2xx_401_is_the_4xx_class` | PIN (F3-5, X5) | pass | X5 |

Counts: 73 new = 50 RED + 23 PIN; the file has 408 nodes.

## GREEN + gates on the final bytes (every pytest through pyt.py, one at a time)

```
unit flag unset (fix code, the b6753884 RED file): 408 passed, 11 warnings in 7.88s; sentinel 408; netguard 0
[pyt] tag=b4f3-unit-off start=2026-10-22 16:09:11 end=2026-10-22 16:09:20 elapsed=9s bound=600s status=OK rc=0
unit ENABLE_URL_MODE_V2=true: 408 passed, 11 warnings in 8.25s; sentinel 408; netguard 0
[pyt] tag=b4f3-unit-on start=2026-10-22 16:09:20 end=2026-10-22 16:09:29 elapsed=9s bound=600s status=OK rc=0
unit flag unset (final bytes): 408 passed, 11 warnings in 10.00s; sentinel 408; netguard 0
[pyt] tag=b4f3-unit-off2 start=2026-10-22 16:55:39 end=2026-10-22 16:55:50 elapsed=11s bound=600s status=OK rc=0
unit ENABLE_URL_MODE_V2=true (final bytes): 408 passed, 11 warnings in 8.36s; sentinel 408; netguard 0
[pyt] tag=b4f3-unit-on2 start=2026-10-22 16:55:51 end=2026-10-22 16:56:01 elapsed=10s bound=600s status=OK rc=0
tests/test_sentry_channels_u8d_unit.py ALONE: 141 passed; sentinel 141; netguard 0
[pyt] tag=b4f3-u8d-unit start=2026-10-22 16:16:00 end=2026-10-22 16:16:09 elapsed=9s bound=600s status=OK rc=0
tests/test_sentry_channels_u8d.py ALONE: 131 passed; sentinel 131; netguard 0
[pyt] tag=b4f3-u8d start=2026-10-22 16:16:10 end=2026-10-22 16:16:17 elapsed=7s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag unset: 21 passed, 13 warnings; netguard blocked 2 attempt(s) from 2 node(s) (neutralized.supabase.invalid sentinel, both in the baseline)
[pyt] tag=b4f3-meter-off start=2026-10-22 16:16:17 end=2026-10-22 16:16:22 elapsed=4s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag exported: 21 passed, 13 warnings; netguard the same 2 baseline nodes
[pyt] tag=b4f3-meter-on start=2026-10-22 16:16:22 end=2026-10-22 16:16:26 elapsed=4s bound=600s status=OK rc=0
CI-order set (13 files, alphabetical, flag OFF): 1059 passed (= 986 + 73), 13 warnings in 17.94s; sentinel 1059; netguard blocked 10 attempt(s) from 10 node(s)
[pyt] tag=b4f3-ci-order start=2026-10-22 16:16:40 end=2026-10-22 16:16:59 elapsed=19s bound=1200s status=OK rc=0
CI-order set on the final bytes: 1059 passed, 13 warnings in 21.43s; sentinel 1059; netguard 10 / 10
[pyt] tag=b4f3-ci-order2 start=2026-10-22 16:56:20 end=2026-10-22 16:56:43 elapsed=23s bound=1200s status=OK rc=0
20-file pin set, flag exported: 1037 passed, 13 warnings in 30.15s; sentinel 1037; netguard 10 / 10
[pyt] tag=b4f3-pins20-flagON start=2026-10-22 16:17:00 end=2026-10-22 16:17:31 elapsed=31s bound=1200s status=OK rc=0
comm 00: 671 passed, 1 skipped, 2 deselected; sentinel 672; netguard blocked 29 attempt(s) from 28 node(s)
[pyt] tag=b4f3-comm-00 start=2026-10-22 16:18:05 end=2026-10-22 16:19:10 elapsed=65s bound=1200s status=OK rc=0
comm 01: 1249 passed, 5 skipped, 5 deselected, 1 xfailed, 2 errors (the cold-tiktoken pair); sentinel 1252; netguard blocked 204 attempt(s) from 13 node(s)
[pyt] tag=b4f3-comm-01 start=2026-10-22 16:19:11 end=2026-10-22 16:20:41 elapsed=90s bound=1200s status=FAIL rc=1
comm 02: 1694 passed; sentinel 1694; netguard blocked 13 attempt(s) from 7 node(s)
[pyt] tag=b4f3-comm-02 start=2026-10-22 16:21:00 end=2026-10-22 16:22:10 elapsed=71s bound=1200s status=OK rc=0
comm 02 re-run on the final test bytes (it holds the unit file): 1694 passed; netguard 13 / 7
[pyt] tag=b4f3-comm-02b start=2026-10-22 16:56:45 end=2026-10-22 16:58:38 elapsed=113s bound=1200s status=OK rc=0
comm 03: 221 passed; sentinel 221; netguard 0
[pyt] tag=b4f3-comm-03 start=2026-10-22 16:22:11 end=2026-10-22 16:22:18 elapsed=7s bound=1200s status=OK rc=0
CLAUDE.md readers (test_ci_gates.py + test_behavior_dimension_translation.py) after the row edit: 79 passed; sentinel 79; netguard 0
[pyt] tag=b4f3-claude-readers start=2026-10-22 16:24:21 end=2026-10-22 16:24:25 elapsed=4s bound=600s status=OK rc=0
hook files collection: 327 nodes (62 + 30 + 114 + 121)
[pyt] tag=b4f3-hook-collect start=2026-10-22 16:27:25 end=2026-10-22 16:27:27 elapsed=2s bound=600s status=OK rc=0
the four tests/test_precommit_hook*.py files ALONE (F3-7; no other pytest on the box, process list read first; spawn probe node -e 0 = 0.15 s): 324 passed, 3 skipped, 7 warnings in 1524.49s; sentinel 327; netguard 0
[pyt] tag=b4f3-hooks start=2026-10-22 16:27:37 end=2026-10-22 16:53:03 elapsed=1526s bound=1800s status=OK rc=0
```
0 TIMEOUTs. Comm set (re-derived for this round, which edits one code file): the reference grep of tests for `url_extraction_service|url_routes|normalize_url_for_same_check|classify_url_path|_extract_from_url_v2|extract_from_url|compare_from_urls|/api/v1/url` (28) UNION every test that walks / globs / names an `app/` path (48) UNION the standing source-scanning pins (incl. `test_auth_error_log_hygiene.py`, `test_start_command.py`) UNION the two CLAUDE.md readers UNION the CI-order set and the 20-file pin set, MINUS the four hook files: 78 files (`comm_union.txt`). No edited test-support module. HEAD failures over the 78 = the two cold-tiktoken ERRORs `tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable` / `::test_render_digests_match_base_except_the_fence` (the zero-network guard's teardown on the tiktoken download), the brief's known environmental pair and the fix-round-2 base set, so `comm -13` is empty; the base was not re-run (NOT MEASURED, below). Netguard: 48 distinct nodes over every log of the round, 0 not in `tests/.network_attempt_baseline.txt` (`netguard_check.py`).

Lint: `ruff 0.16.5 check --select E9,F63,F7,F82 --no-cache` on the service and the unit file: `All checks passed!` (also on the final bytes); `compile()` of both: OK (no bytecode written); full-rule ruff on the service 57 -> 57 (W293 56, F401 1; no new finding). The hook ran ruff / py_compile / the secret scans / gitleaks on the commit: `All checks passed!`. `.githooks` and `.gitleaks.toml`: untouched (`git diff --name-only 81df2b64..HEAD -- .githooks .gitleaks.toml` empty; working-copy diff empty).

## Mutation table (fix round 3; in place in the unit worktree under `.qa-mutation.lock` (label `b4f3-fix-agent (claude-opus-5-5)`), byte copy `mut_bak/` -> exact edit matching once (CRLF-adapted) -> pyt.py over the full unit file (bound 600, every ENABLE_* unset, PYTHONDONTWRITEBYTECODE=1) -> restore from the byte copy -> sha256 compare (abort on mismatch; none: every restore `b0d7b8d9...`) -> lock removed; `mutate3.py`, `mut_results.jsonl`)

| mutant | result | failing nodes | [pyt] |
|---|---|---|---|
| K1 key drops the query again | KILLED | 14 | tag=b4f3-K1_key_drops_query start=2026-10-22 16:10:45 end=16:10:54 elapsed=10s status=FAIL rc=1 |
| K2 key keeps the whole query | KILLED | 16 | tag=b4f3-K2_key_whole_query 16:10:55-16:11:04 elapsed=10s status=FAIL rc=1 |
| K3 keys case-sensitive | KILLED | 4 | tag=b4f3-K3_keys_case_sensitive 16:11:05-16:11:14 elapsed=10s status=FAIL rc=1 |
| K4 values not stripped | KILLED | 2 | tag=b4f3-K4_values_not_stripped 16:11:14-16:11:24 elapsed=10s status=FAIL rc=1 |
| K4b values not percent-decoded (raw split) | KILLED | 3 | tag=b4f3-K4b_values_not_decoded 16:11:25-16:11:34 elapsed=9s status=FAIL rc=1 |
| K5 `products_id` missing from the key | KILLED | 3 | tag=b4f3-K5_no_products_id 16:11:34-16:11:43 elapsed=9s status=FAIL rc=1 |
| K6 `pid` in the key | KILLED | 3 | tag=b4f3-K6_pid_in_key 16:11:44-16:11:53 elapsed=10s status=FAIL rc=1 |
| K6b `pid` in the allow-list | KILLED | 4 | tag=b4f3-K6b_pid_in_allow_list 16:12:35-16:12:44 elapsed=9s status=FAIL rc=1 |
| K7 order-sensitive key | KILLED | 1 | tag=b4f3-K7_key_order_sensitive 16:12:44-16:12:53 elapsed=9s status=FAIL rc=1 |
| K8 empty value counts (F3-4) | KILLED | 6 | tag=b4f3-K8_empty_value_counts 16:12:54-16:13:03 elapsed=10s status=FAIL rc=1 |
| K8b non-empty value refused | KILLED | 35 | tag=b4f3-K8b_non_empty_value_refused 16:54:36-16:54:50 elapsed=14s status=FAIL rc=1 |
| R1 any `product/` route value (F3-2 reverted), first run | KILLED | 25 | tag=b4f3-R1_route_startswith_product 16:13:03-16:13:14 elapsed=11s status=FAIL rc=1 |
| R1 re-run after the key-row refinement | KILLED | 26 | tag=b4f3-R1_route_startswith_product 16:54:11-16:54:24 elapsed=13s status=FAIL rc=1 |
| R2 route value case-sensitive | KILLED | 3 | tag=b4f3-R2_route_value_case_sensitive 16:13:14-16:13:25 elapsed=11s status=FAIL rc=1 |
| R3 route marker dropped | KILLED | 4 | tag=b4f3-R3_route_marker_dropped 16:13:26-16:13:36 elapsed=10s status=FAIL rc=1 |
| R4 case-sensitive route veto | KILLED | 5 | tag=b4f3-R4_route_veto_case_sensitive 16:54:25-16:54:35 elapsed=11s status=FAIL rc=1 |
| R5 the exact route vetoing | KILLED | 24 | tag=b4f3-R5_exact_route_vetoes 16:55:09-16:55:21 elapsed=11s status=FAIL rc=1 |
| T1 first truthy title (F3-3 reverted) | KILLED | 4 | tag=b4f3-T1_first_truthy_title 16:13:54-16:14:03 elapsed=9s status=FAIL rc=1 |
| T2 unusable title not cleared | KILLED | 4 | tag=b4f3-T2_unusable_title_not_cleared 16:14:03-16:14:13 elapsed=9s status=FAIL rc=1 |
| E1b title window unbounded | KILLED | 1 | tag=b4f3-E1b_title_window_unbounded 16:14:13-16:14:22 elapsed=9s status=FAIL rc=1 |
| F5e node-name check ignores the site names | KILLED | 1 | tag=b4f3-F5e_node_name_ignores_site_names 16:14:22-16:14:31 elapsed=9s status=FAIL rc=1 |
| X1 `exc_info=True` on the transport ERROR line | KILLED | 1 | tag=b4f3-X1_transport_error_exc_info 16:14:32-16:14:41 elapsed=9s status=FAIL rc=1 |
| X5 a 401 as `http_403` | KILLED | 1 | tag=b4f3-X5_401_as_http_403 16:14:41-16:14:50 elapsed=9s status=FAIL rc=1 |

22 distinct mutants (23 runs), 22 KILLED, 0 SURVIVED, every kill AssertionError only (the location-line classes of each log). The F3-5 mutants were applied on the fix bytes; the four mutated lines are byte-equal at `83daa8cb`, and the four PINs pass on the `83daa8cb` code bytes (b4f3-red / b4f3-red2: they are among the 358 passed). The control is the unmutated unit run (b4f3-unit-off, 408 passed).

## Rulings answered

- F3-1: done (key + `_SAME_URL_PRODUCT_QUERY_KEYS` with `products_id`, no `pid`; real-route RED rows POST and GET for the five same-store shapes; PINs for the tracking-only pair, the ASP.NET `?pid=` pair, identical urls; pure-key RED/PIN tables). No blanket query rule. Flag OFF byte-identical: the key's only caller is the flagged pre-gate (`grep` of app/: `url_routes.py:119-120` only); the existing OFF rows (P6 `test_flag_off_homepage_pair_is_base_behaviour` with the raising pre-gate stand-in, etc.) are green.
- F3-2: done (exact `product/product`, case-insensitive key and value, at both F2-1 sites through the one helper, and in the key).
- F3-3: done (first usable of title / full_title; the unusable title cleared). See deviation D1.
- F3-4: done (non-empty value after the strip, at both sites and in the key).
- F3-5: done (E1b, F5e, X1, X5 PINs; X4 = F3-4). See deviation D2.
- F3-6: done (CLAUDE.md row and PR body).
- F3-7: done (the four hook files alone, one bounded call, OK).

## Deviations

- D1 (F3-3 row): the ruling says `test_placeholder_llm_name_with_a_usable_llm_full_title` encoded the defect and its expectation moves from `UNRESOLVED_PRODUCT` `null_name` to the delivered full title. Measured: that row (a NAMELESS node, `_product(name=None, price=None)`, an empty `<title>`, LLM `name` "N/A" + a usable `full_title`) already asserts and gets the delivered full title at `83daa8cb` (green in b4f3-red). Old and new expectation: both "delivered, name == the full title" (unchanged, byte-identical). The re-verifier's m3 case (a placeholder-NAMED node) is the new RED row `test_placeholder_node_name_gives_way_to_a_usable_llm_full_title[*]` (old: `null_name` at 83daa8cb; new: delivered full title).
- D2 (F3-5 X5 word): the ruling says "an upstream 401 is reported with reason http_401"; no `http_401` word exists (GC-3 vocabulary; `_v2_status_reason` maps every 4xx but 403 to `http_4xx`), so such a PIN could not pass at HEAD as F3-5 requires. The PIN pins the measured `http_4xx` and kills the X5 mutant; a per-status word is a vocabulary change for a ruling.
- D3 (`products_id` scope): in the same-url key only, per the F3-1 text; the homepage-class allow-list stays the F2-1 set (narrowed). A root `/?products_id=N` link is still a homepage (unpinned). An osCommerce PDP is `product_info.php`, which no class refuses.
- D4 (whitespace-only value): treated as empty (`/?product=%20` is a homepage, pinned), from the ruling's "values compared after percent-decoding and whitespace strip" applied to the F3-4 "non-empty value".
- D5 (rows refined after the RED step): the `listing-route-not-a-key` key row's values (the first pair was equal under R1 too, so it guarded nothing) and two PIN docstrings (`test_classify_url_path_product_product_route_stays_exempt` named a mutant that does not kill it; now the route-veto mutants R4 / R5 that do). The RED-step proof was re-run on the 83daa8cb service bytes (b4f3-red2, same 50 failures, AssertionError only); the last edit after it is a docstring only.
- D6 (mutation in place): the mutants ran in the unit worktree under `.qa-mutation.lock` (the brief's in-worktree protocol: byte copy, restore, sha256 compare, lock removed) rather than in a detached scratch worktree, so no second checkout and no extra node_modules risk; the 83daa8cb re-proof used the same protocol (the HEAD byte copy swapped in and restored). `git status --short` empty at the end.
- D7 (comm set): re-derived by the brief's rule for this round's single edited code file (78 files) instead of re-running fix-2's 184-file union; the standing source-scanning pins, both CLAUDE.md readers and `test_auth_error_log_hygiene.py` are in it.
- D8 (hook run as a background shell task): the 1800 s bound exceeds the tool's 600 s foreground limit, so the ONE bounded pyt.py call ran as a background shell task; nothing else ran pytest meanwhile (the agent polled the log with a Python sleep loop) and it ended OK at 1526 s.
- D9: two throwaway files were briefly written under `/tmp` (a `git show` of the HEAD service file and a grep file list) and deleted at once; every kept file is in the notes folder.
- D10: the commit trailer names Claude Opus 5.5 (this agent's model).

## Open questions for the gate / the re-verifier

1. Should the homepage-class allow-list also carry `products_id` (a root `/?products_id=N` link is a homepage today), or is the key-only scope of F3-1 the intended reading?
2. Is a per-status `http_401` reason word wanted (a GC-3 vocabulary change), or is `http_4xx` for a 401 the contract (now pinned)?
3. Same-url key corner cases, unpinned: `route=product/product&product_id=1` vs `?product_id=1` (no route) differ (two urls of one product are fetched and compared); `?route=product/category&product_id=5` is exempt through `product_id` and its key drops the listing route. Both follow the ruling's literal key; flag if a narrower reading is wanted.
4. The lower-case exempt PIN row (`route=product/product&product_id=7`) restates F2-1 behaviour; it is killed only by the contrived exact-route veto R5. Kept because the ruling names the row.

## NOT MEASURED

- A base (83daa8cb) re-run of the 4 comm chunks: their only failures are the brief's known cold-tiktoken pair (also the fix-round-2 base set), so they cannot be branch-only-NEW; the unit file itself was run on the 83daa8cb code bytes twice (RED step).
- Any live store, Sentry or Railway behaviour (rules); the OpenCart / PrestaShop / WooCommerce / osCommerce / ASP.NET shapes are synthetic pages of the registry URL shapes through the real route.
- The post-rebase run (GC-7, the orchestrator) and both adversaries on this HEAD (the orchestrator, per RULINGS_FIX3_B4).

## End state

Worktree `sc-s80-b4`: HEAD `0aac07f1f7304e61fa5cac86935c9306f08605d0`, `git status --short` empty, no `.qa-mutation.lock`, no scratch worktree created. No pytest left running (every run ended OK or FAIL; the hook run ended OK). Final sha256 (bytes on disk): RED `bac8730196c75769e672646e6f1dee7901bfb3fb275af1d84af6a9d97517f1d9`, url_extraction_service `b0d7b8d96aec34352dccdf008d29ddb60fdd03779cb28cc19cfddcf29cc49f68`, CLAUDE.md `c4af580314acbf212b0368d87d6ed5648bc1a66712edde79db6f508b739bd1e6`; unchanged this round: url_routes `9229e0b4...`, error_handler `7e539cc7...`, test_paid_route_metering `4724c308...`. PR body draft: `<scratchpad>/B4_fix3/PR_BODY.md` sha256 `ddb7487437c502efe6530a3069cb314f0d6d5adb6e1be604a5d4d3e43ff7f98a`.
