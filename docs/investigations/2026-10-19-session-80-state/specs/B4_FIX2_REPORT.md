# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- fix round 2 report (2026-10-20)

- Unit B4, flag `ENABLE_URL_MODE_V2` (default OFF, read per call). Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, base `81df2b64` (not rebased, GC-7).
- Start: HEAD `96676f1fe9ddc4b4bc57e3e8aec166e4c7e26d4b` verified 19:31, `git status --short` empty, no `.qa-mutation.lock`, RED file sha `546fc27d...8b46` re-hashed and equal.
- End: HEAD **`83daa8cbc923e81abde398bdf93f84bdc4acab66`** (ONE commit through the pre-commit hook, `All checks passed!`; `git add <paths>` + `git commit -m <subject> -m <trailer> -- <paths>`; no push, no rebase, no stash, no checkout in the worktree). `git status --short` empty after the commit and after the last run (20:28). Working copy byte-identical before and after the commit (`precommit_hashes.txt` == `postcommit_hashes.txt`).
- Agent model: claude-opus-5-5 (this agent's system prompt). Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the task: "YOUR OWN MODEL NAME"; the common brief's Fable 5.1 trailer would be a false attribution).
- Read: s80-common.txt (incl. the 2026-10-20 addendum), RULINGS_FIX2_B4.md (twice), GATE_B4.md, RULINGS_FIX1_B4.md, B4_FIX1_REPORT.md, B4_ADV2_correctness.md, B4_ADV2_engineering.md, the fix-1 PR body, the GREEN report's CI-order / comm paragraphs, the adversary probe drafts (`B4_adv2/eng/test_zz_b4a2e_loghyg.py`, `B4_adv2/mutants_def.py`, `B4_adv2/mutate.py`). Not opened this round: the spec, the spec review, B4_FIX1_REVERIFY.md, RULINGS_BATCH1.md, PLAN_S80.md (the fix rulings and the adversary reports cite what this round needed).

## Files (final sha256 = bytes on disk = the committed working copy)

| file | +/- | sha256 before (96676f1f) | sha256 after (83daa8cb) | bytes > 127 before/after | line endings |
|---|---|---|---|---|---|
| tests/test_s80_url_mode_v2.py (RED, append only) | +486/-0 | 546fc27d07579808ea7b8b7fb60cd87a3be8462ebdaea677aa3c8e21587f8b46 | **1e8e28aeff8c7fbc9fc9bcf67e0a765ed151ad1f87b8cd9508da38ac54894e0a** | 0/0 | LF (as frozen); 101,070 B; the first 75,913 B are the 546fc27d file |
| app/services/url_extraction_service.py | +85/-17 | 0abf3b950898fd10678f3092c424729696072a6d33b1925d3dc2a09279e647c2 | 35f3756603e6fe8d2642b3375f2a2fa6590ab9cadeca42a4064a55116df7d4f9 | 18/18 | CRLF 1363/1363 (blob LF) |
| CLAUDE.md (the SESSION 80 B4 header + row, 2 lines in place) | +2/-2 | 8502da3b038953d7ecaad3637567683f8149415af1304c90fc1dc52749a2c0ad | 6e51ad94ef65217f46ced4aed186cf725814b054dc0a54735aab59df86f408f2 | 3979/3979 | CRLF 938/938 |

The committed RED blob (`git show HEAD:tests/test_s80_url_mode_v2.py`) hashes to `1e8e28ae...4e0a`. Added-line sweep over `git diff -U0` of the three files (573 added lines): 0 non-ASCII, 0 @gmail, 0 +973, 0 8+-digit runs, 0 sk-/AKIA/xox/eyJ, 0 credentialed URL, 0 PEM (`sweep.py`). Byte copies of every edited file before the first edit: `B4_fix2/before/` + `SHA256SUMS.txt`.

Notes-folder files (not committed): `PR_BODY.md` sha256 `97272c1951555ac1a65a7b2dde932f0ba118c9b2e0096c0869d4f42300c797af` (the new PR body draft; 4 bytes > 127 = the required robot glyph line), `red_append.py` `d0914248...` (the appended block), `mutants_def.py` `24c971d0...`, `mutate.py` `91085847...`, `mut_results.jsonl` (25 rows), `sweep.py`, `netguard_check.py`, `notes.md`, every log named below.

## What changed (smallest additive hunks; every code change is in a function only the flagged path reaches)

- **F2-1 (M1)**: new `_PRODUCT_ROUTE_QUERY_KEYS = frozenset({"product_id", "id_product", "product"})` and `_query_names_a_product_route(query)` (`parse_qs(query, keep_blank_values=True)`, keys `.lower()`; a `route` key counts when a value starts with `product/`); `classify_url_path` keeps the parsed `urlsplit` and returns `homepage` only when `_NOT_A_PDP_HOME_PATH_RE.match(path) and not _query_names_a_product_route(parts.query)` (falls through to the other classes otherwise). Both sites use it: the pre-gate (`url_routes._url_pre_gate`) and the post-fetch final-url check in `_extract_from_url_v2` (no route edit needed). Comment + docstring updated. `parse_qs` was already imported (unused until now).
- **F2-2 (E1)**: `_V2_TITLE_RE` deleted. New `_v2_first_title(html)`: `html[:65536]`, a length-preserving ASCII lower-casing (`str.translate`), `str.find("<title")` until an opener followed by `>` or whitespace, `find(">")`, then `find("</title")` followed by optional whitespace and `>` (looping past a non-matching candidate); no close tag -> the first `_V2_TITLE_MAX_CHARS` (1024) characters after the opener's `>`; no opener or no `>` -> None. `_is_challenge_page` feeds the same prefix check. Linear.
- **F2-5**: `extract_generic_data_v2` computes the site names right after `extract_meta_tags`, and sets `data["title"] = og_title or page_title` when `"title" not in data` (unchanged no-node case) OR the node's title is unusable AND the meta title is usable (value, not key presence); `_extract_from_url_v2` sets `raw_data["name"] = None` after the existing title check when the merged name is not usable (so `normalize_product_data` ships `name = title`). Docstring (f) updated.
- **F2-3**: process only (comm set); no product code.
- **F2-6**: CLAUDE.md row edited in place (header cites F2-1..F2-6; effect clause gains the F2-1 exemption, the F2-2 scan, the redirect-cap definition, the GC-2 / first-node / WebPage / pair-reason pins, the F2-5 name rule replacing "never a `success: true` with `Unknown Product`"; logs gain the F2-4a pin and the Sentry consequence (a); limit (1) gains the exemption and (d); (3) wording "query-based refusal"; (11) gains (c); (16) replaced by the measured flag-exported list (a); new (18) = (b); new (19) = (f)). PR body draft rewritten to `B4_fix2/PR_BODY.md`.

## RED step (rows appended, RED file new sha `1e8e28ae...4e0a`)

82 nodes appended (no existing row changed; no row pinned a product-route query as homepage: R29's `/index.php` row has an empty query and keeps `homepage`). Run on the `96676f1f` code bytes:
```
33 failed, 302 passed, 11 warnings in 14.02s; E-classes: 33 AssertionError, no other; [hermeticity] sentinel checked 335 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4f2-red start=2026-10-20 19:46:34 end=2026-10-20 19:46:51 elapsed=16s bound=600s status=FAIL rc=1
```
Existing 253 rows: all green. New rows (class; at 96676f1f; killed mutant(s) on the fix bytes):

| row | class | at 96676f1f | killed by |
|---|---|---|---|
| `test_classify_url_path_product_route_query_is_not_homepage[*]` (13) | RED (F2-1) | FAIL `homepage` | M1a (all 13), M1d (3 upper-case-key rows) |
| `test_classify_url_path_tracking_query_stays_homepage[*]` (12: gclid, gbraid, utm_source, fbclid, /index.php, /index.php?, /?p=123, route=common/home, routes=, product_ids=, utm_content=product_id, ref=product) | PIN (F2-1 guard) | pass | M1b (10 of 12), M1c (4), M1e (/?p=123) |
| `test_query_routed_pdp_pair_delivers_flag_on[POST|GET x opencart-opencart|prestashop-opencart|woocommerce-opencart]` (6) | RED (F2-1, pre-gate site, real route) | FAIL 400 NOT_PRODUCT_PAGE | M1a |
| `test_redirect_to_query_routed_pdp_is_not_refused_post_fetch[POST|GET]` (2) | RED (F2-1, post-fetch site) | FAIL 400 | M1a |
| `test_redirect_to_tracking_root_is_still_homepage_post_fetch[POST|GET]` (2) | PIN (F2-1 guard, post-fetch) | pass | M1b |
| `test_challenge_title_scan_is_linear[no-gt-in-window|gt-no-close]` (2) | RED (F2-2) | FAIL: 2430 ms / 2249 ms > 500 ms | M2a |
| `test_challenge_title_verdicts_preserved[*]` (10) | PIN (F2-2 behaviour) | pass | M2b (2 case rows), M2c (attribute row) |
| `test_challenge_title_without_a_close_tag_is_read_to_a_bound` | RED (F2-2 ruled shape) | FAIL (regex: no title) | M2a, M2d |
| `test_v2_fetch_log_records_carry_the_host_only[blocked_initial|blocked_hop|redirect_cap|non_2xx|challenge|transport]` (6) | PIN (F2-4a) | pass | P2, P3, S3, S5, S8, S9 |
| `test_webpage_name_is_not_a_site_name` | PIN (F2-4b) | pass | P1 |
| `test_detected_retailer_label_is_a_supported_name_or_unknown[base-path|v2-path]` (2) | PIN (F2-4c) | pass | P3, S5 |
| `test_fetch_page_v2_redirect_bound_is_five_requests` | PIN (F2-4d) | pass | S01 range(6), S01b range(4) |
| `test_post_fetch_final_url_in_any_pregate_class_is_not_product_page[search|cart|checkout|account|category]` (5) | PIN (F2-4e) | pass | S02 |
| `test_pair_reason_is_the_first_failing_links[POST|GET x 403-then-404|404-then-403]` (4) | PIN (F2-4f, S03) | pass | S03 |
| `test_first_product_node_in_document_order_wins[two-blocks|graph]` (2) | PIN (F2-4f, S10) | pass | S10 |
| `test_nameless_node_without_price_falls_back_to_the_title` | RED (F2-5) | FAIL null_name | M5a |
| `test_placeholder_llm_name_never_ships_flag_on[Unknown Product|Unknown|N/A|Product|Rasasi]` (5) | RED (F2-5) | FAIL: delivered the placeholder | M5b (5), M5d (Rasasi) |
| `test_placeholder_llm_name_with_a_usable_llm_full_title` | RED (F2-5) | FAIL: delivered 'N/A' | M5b |
| `test_nameless_node_with_price_uses_the_meta_title_without_the_llm[title_tag|og_title]` (2) | RED (F2-5) | FAIL null_name (LLM called) | M5a |
| `test_no_usable_title_and_placeholder_name_is_unresolved[*]` (4) | PIN (F2-5 guard) | pass | M5c |

Counts: 82 new = 33 RED + 49 PIN; file 335 nodes.

## GREEN + gates on the final bytes (every pytest through pyt.py, one at a time)

```
unit flag unset: 335 passed, 11 warnings in 8.89s; sentinel 335; netguard 0
[pyt] tag=b4f2-unit-off start=2026-10-20 19:48:43 end=2026-10-20 19:48:54 elapsed=10s bound=600s status=OK rc=0
unit ENABLE_URL_MODE_V2=true: 335 passed, 11 warnings in 9.20s; sentinel 335; netguard 0
[pyt] tag=b4f2-unit-on start=2026-10-20 19:49:02 end=2026-10-20 19:49:13 elapsed=11s bound=600s status=OK rc=0
mutation control (scratch, unmutated): 335 passed
[pyt] tag=b4f2-mut-control start=2026-10-20 19:50:59 end=2026-10-20 19:51:08 elapsed=9s bound=600s status=OK rc=0
tests/test_sentry_channels_u8d_unit.py ALONE: 141 passed; sentinel 141; netguard 0
[pyt] tag=b4f2-u8d-unit start=2026-10-20 19:59:57 end=2026-10-20 20:00:08 elapsed=10s bound=600s status=OK rc=0
tests/test_sentry_channels_u8d.py ALONE: 131 passed; sentinel 131; netguard 0
[pyt] tag=b4f2-u8d start=2026-10-20 20:00:10 end=2026-10-20 20:00:20 elapsed=10s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag unset: 21 passed; sentinel 21; netguard blocked 2 attempt(s) from 2 node(s) (sentinel, both in the baseline)
[pyt] tag=b4f2-meter-off start=2026-10-20 20:00:24 end=2026-10-20 20:00:29 elapsed=5s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag exported: 21 passed; sentinel 21; netguard blocked 2 attempt(s) from 2 node(s) (same two)
[pyt] tag=b4f2-meter-on start=2026-10-20 20:00:31 end=2026-10-20 20:00:38 elapsed=7s bound=600s status=OK rc=0
CI-order set (13 files, alphabetical, flag OFF): 986 passed (= 904 + 82), 13 warnings in 18.56s; sentinel 986; netguard blocked 10 attempt(s) from 10 node(s) (baseline)
[pyt] tag=b4f2-ci-order start=2026-10-20 20:00:41 end=2026-10-20 20:01:02 elapsed=21s bound=1200s status=OK rc=0
comm 00 (incl. test_auth_error_log_hygiene.py): 1040 passed; sentinel 1040; netguard blocked 3 attempt(s) from 3 node(s)
[pyt] tag=b4f2-comm-00 start=2026-10-20 20:04:11 end=2026-10-20 20:04:35 elapsed=24s bound=1200s status=OK rc=0
comm 01: 2477 passed, 2 skipped, 12 deselected; sentinel 2479; netguard blocked 26 attempt(s) from 10 node(s)
[pyt] tag=b4f2-comm-01 start=2026-10-20 20:04:51 end=2026-10-20 20:05:44 elapsed=53s bound=1200s status=OK rc=0
comm 02: 774 passed, 1 skipped; sentinel 775; netguard blocked 29 attempt(s) from 28 node(s)
[pyt] tag=b4f2-comm-02 start=2026-10-20 20:05:54 end=2026-10-20 20:08:40 elapsed=166s bound=1200s status=OK rc=0
comm 03: 596 passed, 1 skipped, 10 deselected; sentinel 597; netguard 0
[pyt] tag=b4f2-comm-03 start=2026-10-20 20:08:52 end=2026-10-20 20:09:09 elapsed=17s bound=1200s status=OK rc=0
comm 04: 1044 passed, 6 skipped, 1 xfailed, 2 errors (the cold-tiktoken pair); sentinel 1048; netguard blocked 123 attempt(s) from 8 node(s)
[pyt] tag=b4f2-comm-04 start=2026-10-20 20:09:15 end=2026-10-20 20:10:41 elapsed=87s bound=1200s status=FAIL rc=1
comm 05: 1891 passed; sentinel 1891; netguard blocked 16 attempt(s) from 8 node(s)
[pyt] tag=b4f2-comm-05 start=2026-10-20 20:10:53 end=2026-10-20 20:12:54 elapsed=120s bound=1200s status=OK rc=0
comm 06: 649 passed, 7 skipped, 1 deselected; sentinel 656; netguard blocked 27 attempt(s) from 23 node(s)
[pyt] tag=b4f2-comm-06 start=2026-10-20 20:12:59 end=2026-10-20 20:13:40 elapsed=41s bound=1200s status=OK rc=0
comm 07: 461 passed, 1 skipped; sentinel 462; netguard 0
[pyt] tag=b4f2-comm-07 start=2026-10-20 20:13:46 end=2026-10-20 20:13:56 elapsed=11s bound=1200s status=OK rc=0
base re-run (scratch at 96676f1f bytes) of chunks 01 / 06 / 05 for the netguard comparison:
[pyt] tag=b4f2-base-comm-01 start=2026-10-20 20:14:57 end=2026-10-20 20:15:56 elapsed=59s bound=1200s status=OK rc=0   (2477 passed; netguard 29 attempts / 11 nodes)
[pyt] tag=b4f2-base-comm-06 start=2026-10-20 20:16:00 end=2026-10-20 20:16:47 elapsed=48s bound=1200s status=OK rc=0   (649 passed; netguard 27 / 23)
[pyt] tag=b4f2-base-comm-05 start=2026-10-20 20:17:00 end=2026-10-20 20:19:30 elapsed=150s bound=1200s status=OK rc=0  (1809 passed = 1891 - 82; netguard 16 / 8)
20-file pin set, flag exported: 1037 passed, 13 warnings in 41.98s; sentinel 1037; netguard blocked 10 attempt(s) from 10 node(s)
[pyt] tag=b4f2-pins20-flagON start=2026-10-20 20:21:19 end=2026-10-20 20:22:03 elapsed=44s bound=600s status=OK rc=0
CLAUDE.md readers (test_ci_gates.py + test_behavior_dimension_translation.py) after the row edit: 79 passed; sentinel 79; netguard 0
[pyt] tag=b4f2-claude-readers start=2026-10-20 20:23:42 end=2026-10-20 20:23:47 elapsed=5s bound=600s status=OK rc=0
tests/test_auth_error_log_hygiene.py ALONE on the committed bytes: 69 passed, 11 warnings in 5.71s; sentinel 69; netguard 0
[pyt] tag=b4f2-auth-log-hygiene start=2026-10-20 20:28:14 end=2026-10-20 20:28:22 elapsed=8s bound=600s status=OK rc=0
```
0 TIMEOUTs. Comm set (F2-3): union of GREEN's 120 (`B4_green/comm_head_files.txt`), the fix-1 delta chunk (9) and 64 files a broad grep matched (`os.walk|rglob|glob.glob|.glob(|iglob|Path("app"|"app/"|"app"|'app'|APP_DIR|app_dir|read_text(` over tests), minus the four `test_precommit_hook*.py`: 184 files (`comm_union.txt`, chunks `comm_chunk_00..07`). Of the 64, a strict check (walk/glob AND an `app` path token in the same file) leaves only `tests/test_auth_error_log_hygiene.py` (= the engineering adversary's E2 finding); the other 63 are over-inclusion. Every standing source-scanning pin (test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit) and both CLAUDE.md readers were already in the prior sets and are in the union. HEAD FAILED/ERROR ids over the 184 files = `tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable`, `::test_render_digests_match_base_except_the_fence` (ERROR, cold tiktoken) = the RED base set (`B4_green/base_failed_ids.txt`): `comm -13 base head` EMPTY. Netguard: 80 distinct nodes over the comm logs, 5 not in `tests/.network_attempt_baseline.txt` (two openaipublic tiktoken downloads, a footlocker curl_cffi fetch in test_flush_live_price_key, two `neutralized.supabase.invalid` sentinels in test_s78_all_timeout_cap_as_timeout); the same chunks at the `96676f1f` bytes show head-only = none (one base-only node, `test_flush_live_price_key.py::test_flag_off_body_is_the_legacy_shape_exactly`, the egress flake GREEN also saw), so they are pre-existing, order-dependent subset artifacts. Every netguard node in the unit / u8d / metering / CI-order / pins20 / readers logs is in the baseline (`netguard_check.py`: 10 nodes, 0 new).

Lint: `ruff 0.16.5 check --select E9,F63,F7,F82 --no-cache` on the service and the unit file: `All checks passed!`; `compile()` of both: OK (no bytecode written; equivalent to py_compile); full-rule ruff on the service 58 -> 57 findings (F401 2 -> 1: `parse_qs` now used; W293 56 unchanged; no new rule class). The pre-commit hook ran ruff / py_compile / the secret scans on the commit: `All checks passed!`.

## Mutation table (fix round 2; detached scratch worktree `B4_fix2/scratch` at 96676f1f + the two edited files copied byte-exact; lock `.qa-mutation.lock` held during the run and removed; byte copy -> exact edit matching once (CRLF-adapted) -> pyt.py over the full unit file (bound 600) -> restore from the byte copy -> sha256 compare (the harness aborts on a mismatch; none); results `mut_results.jsonl`, logs `mut_<name>.log`)

| mutant | result | failing nodes | [pyt] |
|---|---|---|---|
| M1a product-route exemption removed | KILLED | 21 | tag=b4f2-M1a_product_route_exemption_removed start=19:51:20 end=19:51:46 elapsed=26s status=FAIL rc=1 |
| M1b blanket "any non-empty query" exemption | KILLED | 16 | tag=b4f2-M1b_blanket_query_exemption 19:51:46-19:51:58 elapsed=11s status=FAIL rc=1 |
| M1c substring "product" anywhere in the query | KILLED | 4 | tag=b4f2-M1c_substring_product_anywhere 19:51:59-19:52:18 elapsed=19s status=FAIL rc=1 |
| M1d case-sensitive keys | KILLED | 3 | tag=b4f2-M1d_case_sensitive_keys 19:52:18-19:52:29 elapsed=11s status=FAIL rc=1 |
| M1e bare `p` added to the allow-list | KILLED | 1 | tag=b4f2-M1e_bare_p_key_added 19:52:30-19:52:42 elapsed=12s status=FAIL rc=1 |
| M2a the quadratic regex reintroduced | KILLED | 3 | tag=b4f2-M2a_quadratic_regex_reintroduced 19:52:43-19:53:08 elapsed=25s status=FAIL rc=1 |
| M2b case-sensitive opener | KILLED | 2 | tag=b4f2-M2b_case_sensitive_opener 19:53:08-19:53:19 elapsed=10s status=FAIL rc=1 |
| M2c opener refuses attributes | KILLED | 1 | tag=b4f2-M2c_opener_refuses_attributes 19:53:20-19:53:36 elapsed=16s status=FAIL rc=1 |
| M2d unclosed title read as none | KILLED | 1 | tag=b4f2-M2d_no_close_is_no_title 19:53:37-19:53:47 elapsed=10s status=FAIL rc=1 |
| P1 WebPage counted as a site name | KILLED | 1 | tag=b4f2-P1_webpage_is_site_name 19:53:48-19:53:58 elapsed=10s status=FAIL rc=1 |
| P2 blocked-redirect line prints the target | KILLED | 1 | tag=b4f2-P2_ssrf_redirect_full_url 19:53:59-19:54:09 elapsed=10s status=FAIL rc=1 |
| P3 retailer label = raw netloc | KILLED | 8 | tag=b4f2-P3_retailer_label_raw_netloc 19:54:12-19:54:29 elapsed=17s status=FAIL rc=1 |
| S3 `_log_fetch_failed` prints the url | KILLED | 5 | tag=b4f2-S3_log_fetch_failed_prints_url 19:54:31-19:54:41 elapsed=10s status=FAIL rc=1 |
| S5 `_host_only` returns the netloc | KILLED | 9 | tag=b4f2-S5_host_only_returns_netloc 19:54:44-19:54:55 elapsed=11s status=FAIL rc=1 |
| S8 blocked-initial line prints the url | KILLED | 1 | tag=b4f2-S8_ssrf_initial_prints_url 19:54:57-19:55:15 elapsed=18s status=FAIL rc=1 |
| S9 too-many-redirects line prints the url | KILLED | 1 | tag=b4f2-S9_ssrf_too_many_prints_url 19:55:16-19:55:27 elapsed=11s status=FAIL rc=1 |
| S01 redirect loop range(6) | KILLED | 1 | tag=b4f2-S01_redirect_bound_6 19:55:29-19:55:39 elapsed=10s status=FAIL rc=1 |
| S01b redirect loop range(4) | KILLED | 1 | tag=b4f2-S01b_redirect_bound_4 19:55:40-19:56:00 elapsed=20s status=FAIL rc=1 |
| S02 post-fetch refuses homepage only | KILLED | 5 | tag=b4f2-S02_postfetch_homepage_only 19:56:02-19:56:12 elapsed=10s status=FAIL rc=1 |
| S03 pair reason from the LAST link | KILLED | 4 | tag=b4f2-S03_reason_from_last_link 19:56:14-19:56:24 elapsed=10s status=FAIL rc=1 |
| S10 last Product node | KILLED | 2 | tag=b4f2-S10_last_product_node 19:56:26-19:56:49 elapsed=23s status=FAIL rc=1 |
| M5a meta fallback on key presence | KILLED | 3 | tag=b4f2-M5a_meta_fallback_on_key_presence 19:56:50-19:57:03 elapsed=14s status=FAIL rc=1 |
| M5b merged name unchecked | KILLED | 6 | tag=b4f2-M5b_merged_name_unchecked 19:57:04-19:57:47 elapsed=42s status=FAIL rc=1 |
| M5c null_name refusal dropped | KILLED | 5 | tag=b4f2-M5c_null_name_refusal_dropped 19:57:49-19:58:17 elapsed=28s status=FAIL rc=1 |
| M5d merged-name check without site names | KILLED | 1 | tag=b4f2-M5d_merged_name_ignores_site_names 19:58:18-19:58:38 elapsed=20s status=FAIL rc=1 |

25 applied, 25 KILLED, 0 SURVIVED; every E-line class across the 25 logs is AssertionError (104 named lines; the rest are pytest assertion-diff lines of the same failures; no other exception class). Every adversary-2 survivor (P1, P2, P3, S01, S02, S03, S10, S3, S5, S8, S9) is now killed; M1 and E1 are killed both ways (M1a / M1b; M2a).

## Rulings answered

- F2-1: done; one hunk in `classify_url_path` serves both sites; allow-list literal to the ruling (key presence for `product_id` / `id_product` / `product`, keys case-insensitive; `route` value `startswith("product/")`, value case not folded); no blanket query rule; bare `p` absent (pinned as current behaviour); no existing row corrected (none encoded the defect).
- F2-2: done; `_V2_TITLE_RE` deleted; str.find extraction; bounded no-close capture; RED (1) + PIN (2) rows plus the no-close RED row.
- F2-3: done (184-file union; test_auth_error_log_hygiene.py green in chunk 00 and alone; PR body paragraph rewritten).
- F2-4 a-f: done; every named mutant killed on byte copies (table above).
- F2-5: done; R28 / R44 green; flag OFF unchanged (both functions are v2-only).
- F2-6 a-f: CLAUDE.md row and PR body (see "What changed").

## Deviations

- X1 (F2-5 row classes): the ruling lists "no usable title and a placeholder LLM name gives UNRESOLVED_PRODUCT" among the new RED rows; at 96676f1f that input already resolves to `null_name` (measured: the four `test_no_usable_title_and_placeholder_name_is_unresolved` nodes pass at HEAD), so it is recorded as a PIN guarding the fix (killed by M5c), not a RED row. The RED F2-5 rows are the three other named cases (LLM name null + usable title; placeholder LLM name + usable title, 5 spellings incl. the site name; nameless node + usable title + offline LLM, 2 variants) plus one extra measured case (placeholder name + usable LLM `full_title`, delivered 'N/A' at HEAD).
- X2 (F2-4d wording): the ruling says "exactly 5 redirect hops are followed and the 6th is refused"; the measured bound of both `fetch_page` and `_fetch_page_v2` (`for _ in range(5)`) is FIVE REQUESTS = four followed hops, the fifth redirect refused as `redirect_cap` without requesting its target. The row pins that exact bound both ways (a 4-hop chain delivers on the fifth request; a longer chain is `redirect_cap` after exactly five requests with `final_url` = the sixth url, never requested), which is what kills `range(6)` (and `range(4)`). The CLAUDE.md row's "5-hop redirect cap" wording was corrected to "at most five requests, four followed hops".
- X3 (F2-2 ruled shape): with no close tag the first title's text is now read up to 1,024 characters (the regex read an unclosed title as no title), so an unclosed "Just a moment..." title is now a challenge; pinned as a RED row (`test_challenge_title_without_a_close_tag_is_read_to_a_bound`) and stated in the row and PR body. Opener matching is ASCII-case-insensitive (the regex's `re.I` also folded a few non-ASCII look-alikes such as U+0130 / U+212A; not reachable on a real `<title>` tag).
- X4 (F2-6 f placement): the diff notes are in the PR body AND as stated limit (19) of the CLAUDE.md row (the ruling says both gain (a)-(f)); the row names "the noon path id of a classify row" without its digits so the docs add no 8-digit run.
- X5 (comm set breadth): the F2-3 union includes 63 over-included files from a broad grep (cheap, all green) besides the one strict app/ walker.
- X6: `compile()` instead of `python -m py_compile` (same syntax check, no `__pycache__` write in the worktree).
- X7: `git worktree prune` was run once after removing my scratch worktree (it only drops admin entries whose directories are gone; no worktree directory was touched).
- X8: commit trailer names Claude Opus 5.5 (this agent's model), per the task text, not the brief's Fable 5.1.

## Open questions for the gate / the re-verifier

1. **Same-store query-routed pairs are refused `same_url` (read from code, not run):** `normalize_url_for_same_check` drops the query, so two OpenCart products of ONE store (`index.php?route=product/product&product_id=A` vs `...=B`) normalise equal and the pre-gate refuses them as `same_url` before any fetch. F2-1 fixed the homepage half of M1; this same-key half is the same over-refusal class for query-routed stores (the four live Bahrain OpenCart registry sources). Recorded as part of stated limit (11) with the variant-URL case; a product-route-aware same-url key (keep the allow-listed query keys in the key) would be a small F2-1-shaped hunk if the orchestrator wants it before the flip.
2. The `route` value check is case-sensitive (`startswith("product/")`, the ruling's literal text); keys are case-insensitive. An upper-case route value (`route=Product/product`, never emitted by OpenCart) stays homepage. Unpinned either way.
3. A `product_id=` / `product=` key with an EMPTY value counts as a product-route marker (key presence, the ruling's literal text); such a link is then fetched and judged post-fetch instead of refused at $0. Unpinned.
4. The relayed user request "also update context files": the context file this unit owns is the CLAUDE.md B4 row (updated in place); the session docs (`docs/CONTEXT_SESSION_LOG.md`, the session-80 state folder on `sc-docs-70`, MEMORY.md) are the orchestrator's (read-only for agents) and were not touched.

## NOT MEASURED

- The new `_is_challenge_page` timing on the flood pages is not printed (the RED rows assert < 500 ms and pass; the 2430 / 2249 ms figures are the 96676f1f measurements of the same rows).
- Any live store / Sentry / Railway behaviour (rules); the four `test_precommit_hook*.py` files (excluded by rule; `.githooks` untouched; the hook itself ran on the commit); a base re-run of comm chunks 00 / 02 / 03 / 04 / 07 (their HEAD failures are only the cold-tiktoken base pair, so they cannot be branch-only-NEW); the post-rebase run (GC-7, orchestrator).

## End state

Worktree `sc-s80-b4`: HEAD `83daa8cbc923e81abde398bdf93f84bdc4acab66`, `git status --short` empty, no `.qa-mutation.lock`. Scratch worktree `B4_fix2/scratch` removed (`git worktree remove --force`; `git worktree list` shows no B4_fix2 entry). No pytest left running (every run was a foreground bounded call that ended OK / FAIL, never TIMEOUT). No .env read, copied or printed; no flag set outside one runner call.
