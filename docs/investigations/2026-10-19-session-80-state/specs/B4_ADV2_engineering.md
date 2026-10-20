# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- adversary 2, lens ENGINEERING (+ security), 2026-10-20

Verdict: **NOT_READY** (blocking 0, MAJOR 2, minor 6).

- Unit B4, worktree `C:/Users/SynAckITPC/Documents/AI/sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, HEAD verified `96676f1fe9ddc4b4bc57e3e8aec166e4c7e26d4b` at 18:10 (first call) and again at the end; `git status --short` empty at start and end; no `.qa-mutation.lock` in the worktree; the worktree was never edited (every run there with `PYTHONDONTWRITEBYTECODE=1`; compile check via `compile()`, no `py_compile` bytecode write).
- Agent model: claude-opus-5-5 (this agent's system prompt).
- Read: s80-common.txt (+ the 2026-10-20 addendum), PLAN_S80.md sections 0-1, RULINGS_BATCH1.md (G-2, B4-R1..R11), GATE_B4.md (GC-1..GC-8), RULINGS_FIX1_B4.md (F4-1..F4-6), B4_GREEN_REPORT.md, B4_FIX1_REPORT.md, B4_FIX1_REVERIFY.md, PR_BODY.md (sha `ea1a3ae4...`), the CLAUDE.md row (worktree lines 474-475), the full app diff `81df2b64..96676f1f`, the spec sections 2.2 / 2.3 / 3 (searched), the RED harness (`tests/test_s80_url_mode_v2.py:300-380`). RULINGS_R0.md was not opened (the plan and the batch rulings cite what this lens needs).
- Scratch worktree `<scratchpad>/B4_adv2_engineering` (detached `96676f1f`, no node_modules, the LF RED file copied byte-exact over the autocrlf checkout); sha-verified equal to the worktree on 14 files before the first mutant and after the last (`eng/sha_before.txt`, `eng/sha_after.txt`); removed at the end (`git worktree list` shows no B4_adv2 entry). Notes and logs: `<scratchpad>/B4_adv2/eng/`.
- No .env read/copied/printed; no flag outside one runner call; no network (every netguard node below is in `tests/.network_attempt_baseline.txt`, checked node by node by `eng/netguard_check.py`).

## 1. Runs (every pytest through pyt.py, one at a time)

```
unit ON (worktree): 253 passed, 11 warnings in 7.17s; [hermeticity] sentinel checked 253 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4a2e-unit-on start=2026-10-20 18:22:48 end=2026-10-20 18:22:56 elapsed=9s bound=600s status=OK rc=0
unit OFF (worktree): 253 passed, 11 warnings in 7.05s; sentinel 253; netguard 0
[pyt] tag=b4a2e-unit-off start=2026-10-20 18:22:58 end=2026-10-20 18:23:08 elapsed=10s bound=600s status=OK rc=0
CI-order set (13 files, alphabetical, flag OFF, worktree): 904 passed, 13 warnings in 16.97s; sentinel 904; netguard blocked 10 attempt(s) from 10 node(s) (all in the baseline)
[pyt] tag=b4a2e-ci-order start=2026-10-20 18:23:51 end=2026-10-20 18:24:10 elapsed=19s bound=1200s status=OK rc=0
comm chunk 1 (25 files: source-scanning pins + CLAUDE.md readers + support-module importers, incl. tests/test_auth_error_log_hygiene.py; list eng/chunk1.txt), flag OFF, worktree:
1278 passed, 2 skipped, 1 xfailed, 18 warnings, 2 errors in 176.75s; sentinel 1281; netguard blocked 34 attempt(s) from 27 node(s) (all in the baseline)
ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable / ::test_render_digests_match_base_except_the_fence (getaddrinfo openaipublic.blob.core.windows.net = the cold-tiktoken base noise, identical to the RED base set B4_green/base_failed_ids.txt)
[pyt] tag=b4a2e-comm-c1-head start=2026-10-20 18:24:29 end=2026-10-20 18:27:27 elapsed=179s bound=1200s status=FAIL rc=1
comm chunk 2 (19 files: module / symbol / route-path references; eng/chunk2.txt): 680 passed, 1 skipped, 2 deselected, 13 warnings in 50.09s; sentinel 681; netguard blocked 134 attempt(s) from 15 node(s) (all in the baseline)
[pyt] tag=b4a2e-comm-c2-head start=2026-10-20 18:27:58 end=2026-10-20 18:28:50 elapsed=52s bound=1200s status=OK rc=0
comm chunk 3 (25 files: SmartCompareApp scanners + app-path readers; eng/chunk3.txt): 1898 passed, 4 deselected, 13 warnings in 29.11s; sentinel 1898; netguard blocked 14 attempt(s) from 14 node(s) (all in the baseline)
[pyt] tag=b4a2e-comm-c3-head start=2026-10-20 18:29:09 end=2026-10-20 18:29:40 elapsed=31s bound=1200s status=OK rc=0
```
HEAD FAILED/ERROR ids over the three chunks + the CI-order set = the two cold-tiktoken ERRORs only = the base set, so `comm -13 base head` is EMPTY (no base re-run needed: nothing else fails at HEAD).

Scratch-worktree runs (control, mutants, probes, hook files) are in sections 3-5.

Lint (worktree, read-only): `ruff 0.16.5 check --select E9,F63,F7,F82 --no-cache` over the 3 app files, the 6 edited test files (E1-E6) and the unit file: `All checks passed!`; `compile()` over the same 10 files: OK. Full-rule ruff per rule class, base -> head (`eng/ruff_cmp.txt`): url_extraction_service 59 {F401 3, W293 56} -> 58 {F401 2, W293 56}; url_routes 12 -> 12 (same classes); error_handler 0 -> 0; no rule class grows.

## 2. Diff hygiene (`eng/hygiene.txt`)

- 11 files, +2370 / -24. Every edited backend file is all-CRLF in the working copy (CRLF count == line count) and LF in the index (0 CR in the HEAD blob); no whole-file diff. The RED file is LF in both (as frozen; sha `546fc27d...8b46` = the committed blob).
- Non-ASCII bytes unchanged per file (CLAUDE.md 3979/3979, service 18/18, error_handler 3/3, test_retro_w2_1 3/3, every other file 0); the 2370 added lines carry 0 non-ASCII bytes.
- The 24 deleted lines are each replaced in place: 4 signatures extended with a defaulted kwarg, 4 INFO lines rewritten host-only (R-A1 b), the base `gather(...)` and the two `recommendation` / `key_differences` reads restructured behind `url_mode_v2`, the `image_url` line, the `"Unknown Product"` default (kept on the OFF branch), and four clean-list lines extended (E1-E5). No deletion without a replacement.
- Imports vs spec 3: as listed, plus one extra stdlib `import string` in the service (used by `_title_key`), and the spec helper `_v2_product_nodes(html)` is inlined into `extract_generic_data_v2` (neither reported as a deviation; harmless; minor m6).
- Added-line sweep: 0 hits for @gmail / +973 / sk- / AKIA / xox / eyJ / credentialed URL / PEM. Two 8+ digit runs exist, neither personal: the hex constant `BASE_FETCH_PAGE_SHA = "34dd74c6180584097193..."` and the noon product path `/en/-/p666775809` in a classify row. The GREEN and fix reports' "no 8-digit run" claim was measured with word boundaries (minor m5, accuracy only).

## 3. Comm-set re-derivation (union rule, `eng/derive_comm.py`, `eng/comm_reasons.tsv`)

Rules: module grep (`url_routes|url_extraction_service|error_handler`) UNION symbol grep (24 changed / new names incl. `compare_from_urls`, `extract_from_url`, `normalize_product_data`, `extract_with_ai`, `URL_EXTRACTION_PROMPT`, `fetch_page`, `http_exception_handler`, `_compare_urls_metered`, `ENABLE_URL_MODE_V2`, `_fetch_page_v2`, ...) UNION the route path `/api/v1/url/` UNION every test that walks or reads `app/` by path UNION the named s80-common pins (+ `test_start_command*`) UNION the CLAUDE.md readers (only `test_ci_gates.py` and `test_behavior_dimension_translation.py` actually READ it; 24 files merely mention it in prose, checked by `eng/claude_readers.py`) UNION the SmartCompareApp scanners (the unit changes the client-visible contract under ON) UNION the importers of the edited test-support module `tests/w4_11_prompt_digest_recorder.py` (test_model_config_enforced, test_price_fallback_may_decline, test_prompt_fence, test_prompt_truth, test_s80: all in GREEN's list) UNION the importers of the six edited test files (only `test_w4_13_flag_off_ledger.py` via its generator, in GREEN's list; `test_s71_u13_pins.py` "copies conventions, not imported") MINUS the four `test_precommit_hook*.py`.

Against GREEN's 120-file list (`B4_green/comm_head_files.txt`, sha `84828db5...`):
- **Missing from GREEN's list (and from the PR body's comm-set paragraph): `tests/test_auth_error_log_hygiene.py`.** It walks `app/` (`os.walk(app_dir)`, :566-583, `app_dir` = the `app` package dir) counting `LoggingIntegration(` constructions -- a source-scanning pin under the rule. RED's 119 missed it, so GREEN's 120 did too. It is in the re-verifier's 37-file fix-round delta union (`B4_fix1_rv/delta_union.txt`, run green at `96676f1f`) and green in my chunk 1 here. MAJOR-E2 below.
- Also mine-not-GREEN, all correctly excluded: `tests/test_rate_limiting_complete.py` (NETWORK_FLAKY_EXCLUDE, B4-R9), `tests/test_s71_u13_pins.py` (not an importer), 24 prose-only CLAUDE.md mentions.
- GREEN-not-mine (31 files: migrations / gitleaks / skill-frontmatter readers and other RED-grep source scanners): over-inclusion, harmless.
- Every other walker of `app/` (`eng/walkers.txt`, 31 walkers classified) is in GREEN's list or walks only migrations / fixtures / docs / `_proof`.

## 4. Mutation (scratch worktree; `eng/mut.py`: lock, byte copy, exact edit matching once on the CRLF bytes, pyt.py bound 600, restore, sha256 compare; every restore sha-equal; lock removed)

Control on the unmutated scratch copy over the 19-file wide set (the CI-order 13 + both u8d files + test_auth_error_log_hygiene + test_s70_exc_summary_logs + test_url_validator_offloop_hops + test_retro_w0_4_efg):
`1419 passed, 13 warnings in 48.10s` -- `[pyt] tag=b4a2e-control-wide start=2026-10-20 18:33:02 end=2026-10-20 18:33:52 elapsed=50s bound=1200s status=OK rc=0`

| id | mutant | result | first killing node (E class) | [pyt] |
|---|---|---|---|---|
| G10 | normaliser-stage image coercion removed (`"image_url": (raw.get("image_url")`) | KILLED (1) | test_normaliser_coerces_a_raw_image_list_flag_on (AssertionError) | tag=b4a2e-G10_normaliser_coercion_removed start=18:34:01 end=18:34:11 elapsed=9s status=FAIL rc=1 |
| R8a | a SECOND ERROR `Failed to fetch URL host ...` beside the F4-1 line | KILLED (3) | test_sentry_channels_u8d_unit.py::TestR8SourceLines::test_u8d_red_r8_in_except_lines_no_user_content[url_extraction_fetch_failed] ("expected one ERROR call with template prefix 'Failed to fetch', found 2") + R12 POST/GET | tag=b4a2e-R8a_second_error_base_prefix start=18:34:11 end=18:34:33 elapsed=22s status=FAIL rc=1 |
| R8b | the distinct `[URL-V2] fetch failed` template demoted to WARNING | KILLED (2) | test_transport_error_is_store_unreadable[GET/POST] (R12, AssertionError) | tag=b4a2e-R8b_distinct_template_demoted_warning start=18:34:34 end=18:34:56 elapsed=22s status=FAIL rc=1 |
| P1 | WebPage counted as a site name | SURVIVED (1419 passed, wide set) | pin gap (D2, F4-4) | tag=b4a2e-P1_webpage_counts_as_site_name start=18:34:57 end=18:35:47 elapsed=50s status=OK rc=0 |
| P2 | v2 `[SSRF] Blocked redirect to host=` prints the full target url | SURVIVED (1419 passed) | pin gap (D3, F4-4) | tag=b4a2e-P2_v2_ssrf_redirect_line_full_url start=18:35:47 end=18:36:38 elapsed=50s status=OK rc=0 |
| P3 | `Detected retailer` label = raw netloc (`_retailer_log_name` without the SUPPORTED key check) | SURVIVED (1419 passed) | pin gap (D4, F4-4) | tag=b4a2e-P3_retailer_label_raw_netloc start=18:36:40 end=18:37:31 elapsed=51s status=OK rc=0 |
| S1 | v2 per-hop SSRF check removed | KILLED (3) | test_fetch_page_v2_blocks_redirect_to_metadata | tag=b4a2e-S1_v2_per_hop_ssrf_removed start=18:37:32 end=18:37:41 elapsed=9s status=FAIL rc=1 |
| S2 | v2 initial-url SSRF check removed | KILLED (1) | test_fetch_page_v2_blocks_private_initial_url | tag=b4a2e-S2_v2_initial_ssrf_removed start=18:37:42 end=18:37:51 elapsed=9s status=FAIL rc=1 |
| S3 | `_log_fetch_failed` WARNING prints the pasted url, not the host | SURVIVED (1419 passed) | pin gap (minor m2) | tag=b4a2e-S3_fetch_failed_warning_full_url start=18:37:52 end=18:38:43 elapsed=52s status=OK rc=0 |
| S4 | `URL comparison request` INFO prints both full urls | KILLED (2) | test_info_lines_print_host_only / test_info_line_survives_a_malformed_url | tag=b4a2e-S4_compare_info_line_full_urls start=18:38:44 end=18:38:53 elapsed=9s status=FAIL rc=1 |
| S5 | `_host_only` returns `netloc` (userinfo + port) | KILLED (1), only incidentally | test_info_line_survives_a_malformed_url (no userinfo row anywhere; minor m2) | tag=b4a2e-S5_host_only_returns_netloc_userinfo start=18:38:54 end=18:39:45 elapsed=51s status=FAIL rc=1 |
| S6 | error-handler passthrough accepts non-str values | KILLED (3) | test_error_handler_passthrough_on[*] | tag=b4a2e-S6_handler_passthrough_non_str start=18:39:46 end=18:39:55 elapsed=9s status=FAIL rc=1 |
| S8 | v2 `[SSRF] Blocked initial URL: host=` prints the url | SURVIVED (1419 passed) | pin gap (D3 family) | tag=b4a2e-S8_v2_ssrf_initial_line_full_url start=18:39:56 end=18:40:46 elapsed=50s status=OK rc=0 |
| S9 | v2 `[SSRF] Too many redirects for host=` prints the url | SURVIVED (1419 passed) | pin gap (D3 family) | tag=b4a2e-S9_v2_ssrf_too_many_line_full_url start=18:40:48 end=18:41:38 elapsed=50s status=OK rc=0 |
| S10 | GET verb skips the pre-gate | KILLED (19) | test_pregate_field_and_reason[GET-*] | tag=b4a2e-S10_get_verb_skips_pregate start=18:41:39 end=18:41:49 elapsed=10s status=FAIL rc=1 |
| S13 | `URL extraction request` INFO prints the url | KILLED (1) | test_info_lines_print_host_only | tag=b4a2e-S13_extract_info_line_full_url start=18:41:50 end=18:41:59 elapsed=9s status=FAIL rc=1 |
| S14 | base `Detected retailer` INFO prints the url | KILLED (1) | test_info_lines_print_host_only | tag=b4a2e-S14_base_detected_retailer_full_url start=18:42:00 end=18:42:09 elapsed=9s status=FAIL rc=1 |
| S15 | `[URL-V2] refused` INFO also prints the error copy | KILLED (12) | test_pregate_homepage_pair_refused_before_reserve[*] | tag=b4a2e-S15_refused_line_logs_url start=18:42:10 end=18:42:21 elapsed=10s status=FAIL rc=1 |
| S16 | POST pre-gate placed after a credit reserve | KILLED (30) | test_codeless_failure_keeps_base_body_flag_on[POST] + the pre-gate rows | tag=b4a2e-S16_pregate_after_reserve_POST start=18:42:21 end=18:42:31 elapsed=10s status=FAIL rc=1 |
| S17 | deadline 25.0 -> 250.0 | KILLED (1) | test_test_seams_have_production_values | tag=b4a2e-S17_deadline_off_by_10x start=18:42:32 end=18:42:41 elapsed=9s status=FAIL rc=1 |

19 mutants: 13 KILLED (every kill an AssertionError, no other E class), 6 SURVIVED = P1 / P2 / P3 (the brief's expected pin gaps: D2 / D3 / D4 accepted as contract by F4-4) and S3 / S8 / S9 (the same log-hygiene contract on the other three v2 WARNING templates). The behaviour each survivor would break is measured CORRECT at HEAD (section 5 probe 2).

## 5. Probes (scratch worktree; probe files copied in, run, deleted; archived as `eng/test_zz_b4a2e_probe.py`, `eng/test_zz_b4a2e_loghyg.py`)

Probe 1 -- event-loop cost of the v2 challenge-title regex (MAJOR-E1). Page: `"<html><head><title " + "<title " * 9400 + "></head>..."` (66 KB, served 200 by a MockTransport; SSRF validator allowed; LLM stubbed to raise; a 5 ms asyncio heartbeat records the max gap):
```
[probe] _is_challenge_page(crafted 64KB) = False in 2497 ms
[probe] one link v2=True  offload=True : UNRESOLVED_PRODUCT no_product_node elapsed=2.48s max_loop_gap=2463 ms
[probe] one link v2=True  offload=False: UNRESOLVED_PRODUCT no_product_node elapsed=2.47s max_loop_gap=2468 ms
[probe] one link v2=False offload=True : success (base path)              elapsed=0.08s max_loop_gap=53 ms
[probe] one link v2=False offload=False: success (base path)              elapsed=0.04s max_loop_gap=40 ms
[probe] pair v2 offload=True : UNRESOLVED_PRODUCT field=both elapsed=5.66s max_loop_gap=5615 ms
[probe] pair v2 offload=False: UNRESOLVED_PRODUCT field=both elapsed=5.05s max_loop_gap=5052 ms
7 passed, 1 warning in 20.34s; netguard blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4a2e-probe-title-regex2 start=2026-10-20 18:45:56 end=2026-10-20 18:46:18 elapsed=22s bound=600s status=OK rc=0
```
(First attempt with `"<title>" * 9400`: the regex alone 2823 ms, then BeautifulSoup raised RecursionError in BOTH flag states on that nesting (pre-existing, codeless 400): `[pyt] tag=b4a2e-probe-title-regex start=2026-10-20 18:45:00 end=2026-10-20 18:45:26 elapsed=27s bound=600s status=FAIL rc=1`, 4 failed (the probe's own RecursionError), 3 passed. Standalone timing of the bare pattern on 64 KB: `<title>`x9362 2788 ms, `<title `x9362 2367 ms, a normal challenge page 0.0 ms.)

Probe 2 -- log hygiene at runtime under ON (a `https://userinfo@www.b4shop.example/products/<pathtok>?ref=<qtok>` link, secret / path / query tokens built at run time; every record of every logger at DEBUG captured):
```
[probe] kind=transport     -> STORE_UNREADABLE fetch_error   leaks=0  (ERROR [URL-V2] fetch failed host=www.b4shop.example reason=fetch_error type=ConnectError)
[probe] kind=redirect_meta -> STORE_UNREADABLE blocked       leaks=0  (WARNING [SSRF] Blocked redirect to host=169.254.169.254; WARNING [URL-V2] fetch failed ... reason=blocked type=None)
[probe] kind=loop          -> STORE_UNREADABLE redirect_cap  leaks=0  (WARNING [SSRF] Too many redirects for host=www.b4shop.example; WARNING ... reason=redirect_cap)
[probe] kind=http403       -> STORE_UNREADABLE http_403      leaks=0
[probe] kind=challenge     -> STORE_UNREADABLE challenge     leaks=0
[probe] kind=redirect_home -> NOT_PRODUCT_PAGE homepage      leaks=0
[probe] kind=ok            -> success                        leaks=0
7 passed, 10 warnings in 2.42s; netguard blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4a2e-probe-loghyg start=2026-10-20 19:14:35 end=2026-10-20 19:14:39 elapsed=4s bound=600s status=OK rc=0
```
No record of any level from any logger carried the userinfo secret, the path token or the query token on any outcome: the behaviour behind P2 / P3 / S3 / S5 / S8 / S9 is CORRECT at HEAD; only its pins are missing (minor m1 / m2).

## 6. Hook test files ALONE (TIMEOUT rule; `.githooks` untouched by the unit)

```
tests/test_precommit_hook_phase_b.py (114 nodes, scratch worktree, flag unset): 44 passed (no failure) when the bound fired, ~17 s per node
[pyt] tag=b4a2e-hook-phase-b start=2026-10-20 18:48:32 end=2026-10-20 19:08:40 elapsed=1208s bound=1200s status=TIMEOUT rc=124
```
The rule's single re-run alone was NOT done: at the measured ~17 s per node the file needs ~32 min, past the 1200 s bound and past this agent's 90-minute budget (a second TIMEOUT is the predicted outcome). Reported NOT MEASURED, with `tests/test_precommit_hook_phase_b_round2.py` (121 nodes, not started). `tests/test_precommit_hook.py` and `tests/test_precommit_hook_round2.py` were run ALONE and green by the re-verifier on these bytes (B4_FIX1_REVERIFY section 2: 31+31 and 15+15 passed). The unit does not touch `.githooks`; the hook itself passed on both unit commits. No orphan pytest after the TIMEOUT (only the three pre-existing unrelated python.exe processes).

## 7. The CLAUDE.md row and the PR body against the bytes

- Every log template the row and PR body list matches the code (`grep` of every `logger.` call in the three app files: service :321 / :409 / :422 / :431 / :439 / :880 / :904 / :947 / :966 / :990 / :1020 / :1217, routes :129 / :148 / :376 / :438); the only remaining url-bearing lines are the OFF-path `fetch_page` `[SSRF]` lines (:355 / :365 / :371, stated limit 10) and the pre-existing `AI extraction error: {e}` ERROR (:852, base, both states; u8d's Sentry policy reduces the event text to the type).
- "Logs (constants, ints, exception type names and hosts only)": TRUE at HEAD (probe 2), but only the ERROR line, the three INFO lines and the refused/outcome INFO lines are pinned; the four v2 WARNING templates are not (P2, S3, S8, S9).
- Flag-OFF identity, the error-handler scope (B4-R5), the per-call reader idiom, billing R-A3 on every new exit (pre-gate before the reserve; coded refusals, TIMEOUT and the deadline's other-exception arm through the one refund), the PLAN section 0 freeze (no new top-level key; `image_url` retype stated; no bare 503: the TIMEOUT 503 is structured): TRUE by code read and by the unit / CI-order / comm runs above (the correctness lens owns the matrices).
- The PR body maps MYEZ-005 / 006 / 014 / 017, OWNER-INFO, OWNER-SCRAPERS, V02 and V09 to RED node ids (GC-8): TRUE; every cited test name exists in the RED file (`eng/prbody_nodes.txt`: 56 test functions; the only two cited names not in it are other files, `test_precommit_hook`, `test_retro_w2_1`).
- The PR body comm-set paragraph names GREEN's 120 files + the fix agent's 9-file delta chunk; neither contains `tests/test_auth_error_log_hygiene.py` (MAJOR-E2).
- Row gaps already raised by the re-verifier and still open: the Sentry consequence of F4-1 / the non-2xx WARNING is in the PR body owner step only; limit 16's "no other file was measured with it set" is superseded (minor m3). The row does not state the challenge check's cost (MAJOR-E1).

## 8. Findings

### MAJOR

**MAJOR-E1. `_is_challenge_page` is not bounded in TIME: the "bounded regex over text[:65536]" of ruling B4-R2 is quadratic, runs inline on the event loop in `_extract_from_url_v2`, and a crafted 66 KB page freezes the single uvicorn worker about 2.5 s per link, 5.0-5.6 s per pair, flag ON, in both `ENABLE_PRICE_PARSE_OFFLOAD` states.**
- Code: `_V2_TITLE_RE = re.compile(r"<title(?:\s[^>]*)?>(.*?)</title\s*>", re.I | re.S)` and `_V2_TITLE_RE.search(html[:65536])` (url_extraction_service.py, the `_is_challenge_page` block after `classify_url_path`), called synchronously from the `async def _extract_from_url_v2` before any offload. `search` retries at every `<title` position and each attempt scans to the end of the window (the unbounded `[^>]*` and the lazy `(.*?)` with no closing tag), so k openers in an n-byte window cost about k*n.
- Measured (probe 1): one link 2463-2468 ms max loop gap, a pair 5052-5615 ms; the SAME page on the flag-OFF path 40-53 ms. The outcome is a refunded non-delivery (UNRESOLVED_PRODUCT `no_product_node`), so the free tier does not bound it: any signed-in account (U13 is ON in production) can paste two links to a host it controls and stall every other request for ~5 s per call, limited only by the route's rate limit (`@limiter.limit("10/minute")` on each verb, url_routes.py:414 / :465: 10 POSTs a minute alone is up to ~56 s of stall per minute from one limiter key). This is the event-loop-freeze class the W0 P0 (`ENABLE_OFFLOOP_DNS_RESOLVE`) and W0-4 exist to remove, re-opened by new code; dark today (flag OFF), live on the flip.
- Not seen by any gate: B4-R2 asked for "a bounded regex over text[:65536] with no soup" (the review's C1 offered "OR evaluate it inside the offloaded parse job"); `tests/test_retro_w0_4.py`'s guard checks soup helpers only; R11 / `test_body_text_access_denied_is_not_a_challenge` pin the verdict, not the cost.
- Fix shape (for a ruling): scan only the FIRST opener with a bounded attribute class and find the close in a bounded slice, e.g. `m = re.search(r"<title\b[^>]{0,256}>", head, re.I)`; `end = head.lower().find("</title", m.end(), m.end() + 1024)` (linear), or move `_is_challenge_page` into the offloaded parse job; add a PIN row (the probe-1 page: `_is_challenge_page` returns within a small bound, e.g. < 50 ms, and the v2 one-link loop gap stays under a bound) and a mutant that restores the current pattern.

**MAJOR-E2. The unit's comm set misses one source-scanning pin: `tests/test_auth_error_log_hygiene.py` (walks `app/` with `os.walk`, :566-583).** It is absent from RED's 119, GREEN's 120 and the PR body's comm-set paragraph (rule: "every test that walks or reads app/ by path"; the brief: a missing file is a MAJOR). Mitigation measured: green at HEAD in my chunk 1 (and in the re-verifier's fix-round delta union at `96676f1f`), so `comm -13` is empty; no product risk. Fix: add it to the unit's comm list and the PR body's comm-set paragraph (with a `[pyt]` line on the final bytes); no code change.

### minor

- m1 (brief: report as pin gaps). P1 / P2 / P3 SURVIVE the 19-file wide set (1419 passed each): D2 (WebPage not a site name), D3 (host-only v2 `[SSRF]` lines), D4 (the `Detected retailer` label never the raw netloc) are accepted contract (F4-4) with no pin; behaviour measured correct at HEAD (code :241 / :409 / :422 / :431 / :128-134; probe 2).
- m2. The same log-hygiene contract is unpinned on three more templates: S3 (the `[URL-V2] fetch failed ... reason=blocked|redirect_cap|http_*|challenge` WARNING of `_log_fetch_failed`), S8 (`[SSRF] Blocked initial URL: host=`), S9 (`[SSRF] Too many redirects for host=`) each survive with the url in place of the host; and no row anywhere carries a `userinfo@` link: S5 (`_host_only` returning `netloc`, i.e. userinfo + port in every host-only line) is killed only incidentally by the malformed-url row. One row (a userinfo + path + query link driven through blocked / redirect-cap / non-2xx / challenge / transport outcomes, asserting no secret, path or query token in ANY record) closes P2, P3, S3, S5, S8 and S9 together (probe 2 is that row in draft).
- m3. Carried from the re-verifier, still open in the committed row: the F4-1 / non-2xx Sentry consequence is not in the CLAUDE.md row; limit 16's "no other file was measured with it set" is superseded.
- m4. Prove-nothing / prove-less rows (section 9).
- m5. Report accuracy: the GREEN and fix reports' added-line sweep says "no 8-digit run"; two exist (a sha256 hex constant and the noon path id `p666775809`), neither personal.
- m6. Two unreported spec-shape deviations: an extra `import string`; the spec helper `_v2_product_nodes(html)` inlined into `extract_generic_data_v2`. Harmless.

## 9. Prove-nothing / prove-less rows

- `test_challenge_page_is_store_unreadable[*]` (R11) and `test_body_text_access_denied_is_not_a_challenge[*]`: pin the verdict, never the cost of the check (MAJOR-E1).
- `tests/test_retro_w0_4.py::test_w04c_no_async_def_reaches_a_soup_helper_inline`: green, but it proves only "no soup inline", not "no unbounded parse inline" (MAJOR-E1 passes it).
- `test_fetch_page_v2_blocks_redirect_to_metadata` (R41) / `test_fetch_page_v2_blocks_private_initial_url` (R40) / `test_fetch_page_v2_caps_redirect_chain` (R42): match the `[SSRF]` prefix only; the host-only text is unpinned (P2, S8, S9).
- `test_info_lines_print_host_only` (R34): no userinfo link, so D4 and `_host_only`'s userinfo stripping are unpinned (P3, S5).
- `test_transport_error_is_store_unreadable[*]` (R12): pins host-only on the ERROR line only; its WARNING siblings are unpinned (S3).

## 10. Information (not findings)

- Main-side collisions at the GC-7 rebase onto `origin/main` `95cf6f86` (B1 #364, B3 #365): B4 shares 6 of main's 25 changed files. Same-line textual conflicts are certain in four clean lists, where B3 appended `ENABLE_VISION_IDENTITY_V2` to the very line B4 extends: `tests/test_model_config_enforced.py` (:105), `tests/test_prompt_fence.py` (:51), `tests/w4_11_prompt_digest_recorder.py` (:45), `tests/test_s71_u13_compare_auth_required.py` (:83, adjacent insert). `app/api/url_routes.py`: B1's import (after `from app.api.auth_routes import get_optional_user`) sits one line from B4's import block, and B1's `capture_result_status(result, "url", ...)` is on the success exit only (no overlap with B4's hunks); `CLAUDE.md`: the row moves after the B1 and B3 rows (G-2).
- Pre-existing, both states: BeautifulSoup raises RecursionError on ~9,400 nested `<title>` openers (codeless 400 OFF and ON); `extract_with_ai`'s `AI extraction error: {e}` ERROR (:852).

## 11. NOT MEASURED

- `tests/test_precommit_hook_phase_b.py`: one TIMEOUT (44/114 passed, 0 failed when cut), the re-run not done (budget); `tests/test_precommit_hook_phase_b_round2.py`: not started. Both excluded from comm sets by rule (`.githooks` untouched).
- A base re-run of my three comm chunks (not needed: the only HEAD failures are the two cold-tiktoken ERRORs, equal to the RED base set; `tests/test_auth_error_log_hygiene.py` passes at HEAD so it cannot be branch-only-NEW).
- The comm files of my derivation outside the three chunks + the CI-order set (8 app-path readers of chunk A: test_genuine_predicate_parity, test_genuine_price_clobber_guard, test_migration_043_delete_user_cascade, test_negcache_genuine_invalidation, test_no_luxury_gate_in_tier3, test_s79_b3b_apple_revoke, test_scoring_calibration_bundle_c, test_value_badge_category_dims): in GREEN's 120 and green in its 5 chunks at `9db99de9`; not re-run here.
- MAJOR-E1 under real httpx / Railway (measured with a MockTransport on this box; production CPU speed unmeasured) and the flag-ON flag-exported runs (the correctness lens and the re-verifier did those).
- Any Sentry, live or network behaviour (rules).

## 12. End state

- Worktree `sc-s80-b4`: HEAD `96676f1fe9ddc4b4bc57e3e8aec166e4c7e26d4b`; `git status --short` empty; no `.qa-mutation.lock`; never edited. Final sha256 of the unit files (bytes on disk, = the scratch copy before and after, `eng/sha_before.txt` / `eng/sha_after.txt`): RED `546fc27d07579808...8b46`, url_extraction_service `0abf3b950898fd10...`, url_routes `9229e0b4d027e392...`, error_handler `7e539cc7b17fcc6c...`, test_paid_route_metering `4724c308c6a5805a...`, CLAUDE.md `8502da3b038953d7...` (= the fix and re-verify reports).
- Scratch worktree `<scratchpad>/B4_adv2_engineering` removed (`git worktree remove --force`; `git worktree list` shows 0 B4_adv2 entries); the two probe files were deleted from it before the removal (archived in `eng/`).
- Files written (all under `<scratchpad>/B4_adv2/`, nothing in any worktree): this report; `eng/` = notes.md, hygiene.py/.txt, derive_comm.py, comm_mine.txt, comm_reasons.tsv, walkers.txt, scanners.txt, claude_readers.py/.txt, make_chunks.py, chunk1/2/3.txt, chunk_{A,B,C}_all.txt, netguard_check.py, ruff_cmp.py/.txt, sha_verify.py, sha_before.txt, sha_after.txt, mut.py, mut_results.jsonl, mut_*.log, bak/ (the byte copies), test_zz_b4a2e_probe.py, test_zz_b4a2e_loghyg.py, prbody_nodes.py/.txt, claude_row.txt, app.diff, every [pyt] log named above.
- Counts: unit 253/253 ON and OFF; CI-order 904; comm chunks 1278 (+2 known ERRORs) / 680 / 1898; mutants 19 applied, 13 KILLED, 6 SURVIVED (all pin gaps, behaviour correct); probes 2; TIMEOUTs 1 (hook phase_b, NOT MEASURED).
