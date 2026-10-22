# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2): adversary round 3, engineering + security lens (2026-10-22)

Verdict: **NOT_READY** (blocking 0, MAJOR 2, minor 7). MAJOR-E1 is a comm-set membership gap of the addendum class (green when measured here, so it closes with a list edit plus [pyt] lines). MAJOR-E2 is a new event-loop freeze. The flagged pre-gate parses each pasted url's whole query string with `parse_qs` up to four times per request, on the loop, and the url fields have no length bound: 3.55 s per 10 MB request flag ON against 0.089 s OFF, and 1.81 s on the $0 refusal path. That is the round-2 E1 harm class. The re-verifier's m1-m4 are all CONFIRMED and m4 is EXTENDED. The A3-1 gap is confirmed (mutant EA31 survives 408/408) and recorded as the known gap, not a MAJOR. Flag-OFF identity, the error-handler scope, SSRF per hop and host-only logging all hold on the bytes.

- Unit B4, lens engineering (plus security). Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`. HEAD verified `0aac07f1f7304e61fa5cac86935c9306f08605d0` before any run. `git status --short` was empty at start and at end, and no `.qa-mutation.lock` was present. Model: claude-opus-5-5.
- Frozen RED file `tests/test_s80_url_mode_v2.py`: the unit worktree bytes and `git show HEAD:` both hash to `bac8730196c75769e672646e6f1dee7901bfb3fb275af1d84af6a9d97517f1d9`, and the blob has 0 CR and 0 bytes > 127. Note: a fresh checkout under `core.autocrlf=true` writes this file CRLF (my scratch copy hashes `6bd45274...`). The frozen sha is the LF blob, so a re-hash must use `git show HEAD:` or the unit worktree bytes.
- Scratch worktree `<scratchpad>/B4_adv2_engineering`, detached at 0aac07f1. I ran every pytest, probe and mutant there and never edited the unit worktree. Notes, scripts and logs are under `<scratchpad>/B4_adv2/eng/`.
- Read: s81-common.txt (twice), PLAN_S80.md sections 0-1, RULINGS_R0.md (B4 parts), RULINGS_BATCH1.md (B4 section), GATE_B4.md, RULINGS_FIX2_B4.md (F2-3, F2-4, F2-6), RULINGS_FIX3_B4.md with the A3 addendum (twice), B4_FIX3_REPORT.md, B4_fix3/REVERIFY_REPORT.md (verdict, comm and minors), PR_BODY.md (sha `ddb74874...`, read line by line), the CLAUDE.md B4 header and row (word diff), and the full 81df2b64..0aac07f1 diff of the three app files and the six test files.
- No .env was read, copied or printed. No flag was set outside one runner call. No network was used (netguard: 0 new nodes in any of my logs).

## Findings

### MAJOR-E1 (process, comm set; the s80 addendum class): an importer of the branch-edited test-support module is missing from the HEAD comm set
- The branch edits `tests/w4_11_prompt_digest_recorder.py` (E2: `FLAGS` gains `ENABLE_URL_MODE_V2`). That module imports `app.services.url_extraction_service` at :89, which is the module fix round 3 edited.
- `tests/test_price_fallback_may_decline.py` imports the recorder (:25) and iterates `recorder.FLAGS` (:102). So it is an importer of an edited test-support module, and E2 changes its behaviour.
- It sat in the RED 119, the GREEN 120 and the fix-2 184-file sets. The fix-round-3 set (`B4_fix3/comm_union.txt`, 78 files; the PR body's comm paragraph, line 115) drops it, because D7 re-derived the set for this round's one edited code file only. The re-verifier re-ran the same 78 and wrote "No edited test-support module this round". So nobody ran it on the 0aac07f1 bytes.
- Beyond the addendum rule, the HEAD list also lacks other members of the branch's own module grep (`url_routes|url_extraction_service|error_handler`, as RED and GREEN used it):
  - the `error_handler` importers `tests/test_limiter_endpoint_key.py` (:63) and `tests/test_observability.py` (:134);
  - seven files that match that grep only in comments or docstrings (`test_auth_refresh_and_revocation`, `test_auth_routes_invite_fingerprint`, `test_be_harness`, `test_image_identify_llm_unavailable_s69`, `test_social_login_smoke`, `test_account_deletion_u8b`, `test_timeout_partial_integration`);
  - ten SmartCompareApp scanners that were in GREEN's set (the client-visible contract under ON): `test_arabic_verdict_output_w414`, `test_consent_capture_w3_16`, `test_dimension_label_catalog_parity_w414`, `test_feature_bucket_parity`, `test_feedback_allowlist_superset`, `test_landing_fallback_pages_s69`, `test_register_benefits_parity_s69`, `test_review_paraphrase`, `test_text_error_envelope_no_raw_exception`, and `test_timeout_partial_integration` again.
- Derivation: `eng/../comm_derive.py`, `comm_why.py` and `comm_derived.txt`. Of the 108-file union, 24 extra files only mention CLAUDE.md in prose; they are not readers and are correctly out.
- Measured here at HEAD: the 19 files in one chunk, flag OFF, `1688 passed, 12 warnings in 22.34s; sentinel 1688; netguard blocked 27 attempt(s) from 23 node(s)`. All 23 nodes are in `tests/.network_attempt_baseline.txt` (0 new). `[pyt] tag=b4adv2e-comm-extra start=2026-10-22 20:28:17 end=2026-10-22 20:28:41 elapsed=24s bound=1200s status=OK rc=0`.
- Green, so `comm -13` is empty. The rule still makes a missed importer a MAJOR.
- Fix (list and docs only):
  - The unit's comm set at the final HEAD is the branch-level union, not a per-round delta: GREEN's 120 UNION the source-scanning pins UNION the importers of every edited test-support module UNION the fix deltas.
  - Add these 19 files to the list and to the PR body's comm paragraph with the [pyt] line above, or re-run them at the GC-7 rebased HEAD.

### MAJOR-E2 (security / robustness, flag ON): the pre-gate parses unbounded user input on the event loop
- `URLCompareRequest.url1/url2` are a bare `str` with no `max_length` (`url_routes.py:312-315`).
- Under the flag the pre-gate runs before the reserve, in the async route, on the loop:
  - `classify_url_path` calls `_query_names_a_product_route` -> `_product_route_pairs` -> `parse_qs(query, keep_blank_values=True)` (`url_extraction_service.py:198-211`) for a root or `/index.*` path;
  - `normalize_url_for_same_check` calls the same parse again on each url.
  - That is up to four full-query parses per request.
- Measured (`eng/probe.log`, test `test_p4_large_url_body_event_loop_cost`, through the real POST route with the full configuration):
  - two 5 MB `index.php?product_id=1&a=b&...` urls: flag ON **3.550 s** (then STORE_UNREADABLE fetch_error, because httpx refuses any url over 65,536 chars, so nothing is fetched; refunded) against flag OFF **0.089 s**;
  - the same urls without the marker: flag ON **1.809 s**, a $0 `NOT_PRODUCT_PAGE homepage`, no credit consumed, against OFF 0.081 s;
  - one `classify_url_path` or `normalize_url_for_same_check` call on a 5 MB url costs 0.87-0.90 s;
  - stdlib alone: `parse_qs` costs 0.17 s per MB of `a=b&` pairs.
  - `[pyt] tag=b4adv2e-probe start=2026-10-22 20:27:09 end=2026-10-22 20:27:28 elapsed=18s bound=600s status=FAIL rc=1`. The 6 failed nodes are the P1 GET probe artifact explained under Probes.
- This is a 40x amplification against base on attacker-sized input. A signed-in caller (self-registration is free under U13) can block the single worker about 1.8-3.5 s per 10 MB request on the $0 path. The per-IP limiter is not per-attacker (CLAUDE.md, session 71 finding). Same harm class as the round-2 E1 MAJOR (a crafted input freezing the loop).
- The work is pure waste: an over-65,536-char url can never be fetched (httpx `InvalidURL: URL too long`).
- Fix, flag ON only: before any parse, refuse a url longer than httpx's `MAX_URL_LENGTH` (65,536), or a tighter 8 KiB, as `NOT_PRODUCT_PAGE` (or `STORE_UNREADABLE`). Alternatively bound the parse (`query[:8192]`, or `max_num_fields` with the ValueError caught). Add a RED row with a 5 MB url asserting a refusal and a bounded `parse_qs` call count. Keeping the pydantic model untouched keeps the OFF OpenAPI identical.
- NOT MEASURED: Railway's edge request-body cap (it bounds the practical size).

### minor
- **m1 CONFIRMED.** PR_BODY.md line 42 carries the intermediate `b6753884...` (119,199 B). The committed file is `bac87301...` (119,355 B); line 90 is right. Add the CRLF-checkout note above.
- **m2 CONFIRMED.** Lines 80 and 125 say "ALONE ... no other pytest on the box". In the runner ledger `d03rev-probe1` (16:45:56-16:46:11) ran inside `b4f3-hooks` (16:27:37-16:53:03). Reword to "no other pytest at launch; one 15 s sibling run overlapped".
- **m3 CONFIRMED.** Line 78 says `exc_text` and `stack_info` are None "on every other record of the run". The row (`test_transport_error_line_carries_no_exception_info`, :2399-2401) asserts them on the ERROR record only, and only `exc_info` (falsy) on every record.
- **m4 CONFIRMED and EXTENDED.**
  - In code, `/index.php?route=product/category&product_id=5` -> `classify_url_path` None: it is exempt through `product_id`, and the key drops the listing route.
  - The imprecise clause is not only limit (1) and PR line 140. It also sits in PR line 10 ("the listing routes ... stay a homepage, refused at $0"), PR line 75 ("are refused at $0 as a homepage again") and the row's effect clause ("a listing route such as `product/category` ... stays a homepage").
  - Each needs "unless it also carries a non-empty `product_id` / `id_product` / `product`".
- **e-m5 (A3-1 known gap, confirmed).** Mutant EA31 (homepage allow-list = the same-url key set) survives 408/408, so neither reading is pinned. Probe P3: `/?products_id=12`, `/index.php?products_id=12` and the Zen Cart default `/index.php?main_page=product_info&products_id=12` -> `homepage` at $0; `product_info.php?products_id=12` -> None. This is for the next fix round per A3-1, not a MAJOR.
- **e-m6 (log hygiene, pre-existing, unstated).** `extract_with_ai`'s `logger.error(f"AI extraction error: {e}")` (`url_extraction_service.py:940`) is reachable on the flag-ON path. Probe P1 `llm_boom` recorded `ERROR ... AI extraction error: b4 offline`. It is the only ON-path line carrying exception TEXT. The row and PR "Logs (constants, ints, exception type names and hosts only)" paragraph names the B4 lines only; limit (10) names the OFF `[SSRF]` full-url lines but not this one. Sentry gets `<TypeName>` (U8d) and Railway gets the text. Add it as a stated pre-existing limit, or `type(e).__name__` it in a later unit.
- **e-m7 (comm hygiene).**
  - The fix-3 chunks pass non-test modules as pytest files (`tests/conftest.py`, `tests/_env_safety.py`, `tests/_retro_r_mig_sql.py`, the two `tests/fixtures/_gen_*.py`, `tests/w4_11_prompt_digest_recorder.py`). They collect nothing, so "78 files" overstates the members.
  - Chunk 01 carries `tests/test_rate_limiting_complete.py`, which B4-R9 / spec section 7 names as deliberately excluded (NETWORK_FLAKY_EXCLUDE). 5 of its nodes attempt the network (blocked, in the baseline). Harmless, but a red there is a flake class, and the PR paragraph does not say it is in.

## Gates (all on 0aac07f1, scratch worktree, flag unset unless named; one pytest of mine at a time)

```
unit flag unset: 408 passed, 11 warnings in 8.09s; sentinel 408; netguard 0
[pyt] tag=b4adv2e-unit-off start=2026-10-22 19:55:00 end=2026-10-22 19:55:10 elapsed=9s bound=600s status=OK rc=0
unit ENABLE_URL_MODE_V2=true: 408 passed, 11 warnings in 8.16s; sentinel 408; netguard 0
[pyt] tag=b4adv2e-unit-on start=2026-10-22 19:55:21 end=2026-10-22 19:55:30 elapsed=9s bound=600s status=OK rc=0
CI-order set (the 13 files, alphabetical): 1059 passed, 13 warnings in 20.58s; sentinel 1059; netguard blocked 10 attempt(s) from 10 node(s) (all baseline, sentinel class)
[pyt] tag=b4adv2e-ci-order start=2026-10-22 19:55:31 end=2026-10-22 19:55:53 elapsed=22s bound=1200s status=OK rc=0
comm 00 (fix-3 chunk; holds both CLAUDE.md readers + test_auth_error_log_hygiene): 671 passed, 1 skipped, 2 deselected; sentinel 672; netguard blocked 29 attempt(s) from 28 node(s)
[pyt] tag=b4adv2e-comm-00 start=2026-10-22 20:29:29 end=2026-10-22 20:31:13 elapsed=104s bound=1200s status=OK rc=0
comm 01 (holds test_model_config, _enforced, prompt_fence, migration_index, openai_key_log_hygiene): 1249 passed, 5 skipped, 5 deselected, 1 xfailed, 2 errors = tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable / ::test_render_digests_match_base_except_the_fence (the known cold-tiktoken pair, the base set); sentinel 1252; netguard blocked 204 attempt(s) from 13 node(s)
[pyt] tag=b4adv2e-comm-01 start=2026-10-22 20:31:16 end=2026-10-22 20:33:00 elapsed=103s bound=1200s status=FAIL rc=1
comm 02 (holds the unit file, u3c, start_command, u8d_unit, u8d, ssrf, secret_scan_static): 1694 passed; sentinel 1694; netguard blocked 13 attempt(s) from 7 node(s)
[pyt] tag=b4adv2e-comm-02 start=2026-10-22 20:33:33 end=2026-10-22 20:35:26 elapsed=113s bound=1200s status=OK rc=0
comm extra (the 19 MAJOR-E1 files): 1688 passed, 12 warnings; sentinel 1688; netguard blocked 27 attempt(s) from 23 node(s), 0 new
[pyt] tag=b4adv2e-comm-extra start=2026-10-22 20:28:17 end=2026-10-22 20:28:41 elapsed=24s bound=1200s status=OK rc=0
hook files, -k "not dash" (167 of 327; beside the sibling D03 adversary's mutant runs): 131 passed, 0 failed when the bound fired
[pyt] tag=b4adv2e-hooks-notdash start=2026-10-22 19:56:12 end=2026-10-22 20:26:14 elapsed=1802s bound=1800s status=TIMEOUT rc=124
hook files, -k "not dash", TIMEOUT-rule re-run alone (the sibling D03 workflow still active): 131 passed, 0 failed when the bound fired again -> NOT MEASURED
[pyt] tag=b4adv2e-hooks-notdash-rerun start=2026-10-22 20:40:01 end=2026-10-22 21:10:04 elapsed=1803s bound=1800s status=TIMEOUT rc=124
```
- Every netguard node in my logs is in `tests/.network_attempt_baseline.txt` (0 new). The comm 01 errors equal the brief's known pair, so `comm -13` over the four chunks is empty.
- Hooks: the `-k "not dash"` half timed out twice (NOT MEASURED, TIMEOUT rule); the `-k dash` half (160 nodes) was stopped by me before its first node. I killed my own pyt tree after reading its command line (tag `b4adv2e-hooks-dash`) to keep one pytest at a time and fit the budget; that half is NOT MEASURED here.
  - The prior measurements of the same hook bytes stand: the fix agent's 324 passed + 3 skipped, and the re-verifier's 327 nodes with 0 failed.
  - `.githooks` / `.gitleaks.toml`: `git diff --name-only 81df2b64 HEAD -- .githooks .gitleaks.toml` is empty.
- Lint: `ruff 0.16.5 check --select E9,F63,F7,F82 --no-cache` over all ten touched .py files (3 app, 6 tests, the recorder): `All checks passed!`. `compile()` of all ten: OK (no bytecode written). Full-rule ruff: `error_handler.py` clean at head and base; `url_routes.py` 5 fixable at both.
- Source-scanning pins: all inside comm 00-02 above and green (`test_model_config`, `test_model_config_enforced`, `test_prompt_fence`, `test_u3c_store_false_pin`, `test_start_command`, `test_migration_index_predicate_immutability`, `test_openai_key_log_hygiene_s69`, `test_sentry_channels_u8d_unit`, `test_auth_error_log_hygiene`; walkers incl. `test_secret_scan_static`).
- CLAUDE.md readers: `tests/test_ci_gates.py` and `tests/test_behavior_dimension_translation.py` in comm 00, green.

## Diff hygiene (81df2b64..0aac07f1, `hygiene.py` -> `B4_adv2/hygiene.txt`)
- 11 files; every blob is LF (0 CR). Working copies in the unit worktree are CRLF for the ten edited files; the RED file is LF (= its blob). Every working copy normalises to its blob, so no whole-file diff.
- 3296 added / 24 deleted lines. 0 added lines with non-ASCII. Bytes > 127 per file are unchanged base -> head (service 18/18, error_handler 3/3, test_retro_w2_1 3/3, CLAUDE.md 3979/3979).
- Sweep: 0 @gmail / +973 / sk- / AKIA / xox / JWT / credentialed-URL / PEM. The two 8+-digit hits are the `BASE_FETCH_PAGE_SHA` hex and the noon path id (row (19) is true).
- Every deleted line is replaced by a gated or host-only form:
  - the positional `compare_from_urls` call (now OFF only);
  - the three full-url INFO lines (now host-only, R-A1 b);
  - the four signatures (now defaulted kwargs);
  - the "Unknown Product" default and the raw `image_url` (now OFF-branch only);
  - `recommendation` / `key_differences` (now OFF-branch only);
  - the import line widened;
  - four clean-list lines (E1, E3, E5, E2 each gain the flag name; E4 and E6 are additions).
- Imports match the spec and the R0 shape:
  - top-level additions are stdlib only (`asyncio` in the route; `string`, `urlencode` / `urljoin` / `urlsplit` in the service; `os` in the handler);
  - `price_service`, `url_validator`, `response_builder` and `text_sanitize` are imported lazily inside flag-ON functions only;
  - the route imports the five service names it uses.
- Commit trailers: all four commits carry `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- CLAUDE.md row placement: lines 474-475, after the B3-B block and before `## Tests` (G-2).

## SSRF and log hygiene (security)
- `_fetch_page_v2` keeps every guard; each mutant below is KILLED in the unit file:
  - it validates the initial url (ES1, by `test_fetch_page_v2_blocks_private_initial_url`);
  - it validates every hop before following it (ES2, by `test_route_fetch_blocked_or_capped_is_store_unreadable[POST-blocked_hop-blocked]`);
  - it never lets httpx auto-follow (ES3 `follow_redirects=True`, by `test_redirect_to_homepage_is_not_product_page_post_fetch[POST]`);
  - it keeps the 5-request bound (ES4 `range(4)`, by `test_fetch_page_v2_redirect_bound_is_five_requests`; the correctness adversary killed `range(6)`).
- The error-handler passthrough stays scoped to the three codes (EH1 global scope KILLED by `test_error_handler_four_key_body[on-other-code-keys]`). EH2 (extra keys passed through) SURVIVED as an equivalent mutant: no B4 raise carries any other key.
- Log lines, probe P1 at route level, flag ON, POST and GET:
  - Inputs: a pasted link with userinfo, path tokens and a query token, driven through the six outcomes F2-4a does not drive (delivered; post-fetch homepage redirect; `no_product_node`; LLM `is_product_page:false`; `null_name`; LLM exception).
  - Every `app.*` record carried the host only.
  - The B4 lines carry constants, ints, type names and hosts only: `[URL-V2] refused code=/field=/reason=`; `[URL-V2] outcome=/reason=/status=`; `Detected retailer: <SUPPORTED name|unknown> for host <h>`; `URL comparison request: <h> vs <h>`.
  - The 6 GET probe "failures" are the TestClient's own `httpx` request-line record, not app code.
- Mutants on log hygiene:
  - EL2 (the ON-path `Detected retailer` with the url) KILLED by `test_v2_fetch_log_records_carry_the_host_only[blocked_hop]`;
  - EL3 (the refused line at ERROR) KILLED by `test_pregate_homepage_pair_refused_before_reserve`;
  - EL1 (the non-transport `[URL-V2] fetch failed` WARNING raised to ERROR) survives the unit file but is KILLED by the u8d source pin `tests/test_sentry_channels_u8d_unit.py::TestR8SourceLines::test_u8d_pin_r8_no_other_outside_except_error_line` (EL1 against the u8d pair + the CI-order set + auth hygiene: `1 failed, 991 passed`, `[pyt] tag=b4adv2e-EL1-pins start=2026-10-22 20:38:58 end=2026-10-22 20:39:27 elapsed=29s bound=1200s status=FAIL rc=1`).
- Pre-existing, unchanged: the OFF `fetch_page` `[SSRF]` full-url WARNINGs (row limit (10)) and e-m6.
- The E1 regression guard holds: probe P2 times a 67,512-char `<title ` flood at 0.0000 s per `_is_challenge_page` call, and an unclosed 70 KB title at 0.0001 s.

## Row and PR body against the bytes
TRUE:
- the Sentry sentence: `sentry_service.py:651` `LoggingIntegration(level=logging.ERROR)`; installed sentry-sdk 2.68.1 = the lock; `DEFAULT_EVENT_LEVEL` 40; no `enable_logs`;
- the OFF-delta list (route env read, one read per error response, the derived prompt constant, four defaulted kwargs) plus the separately stated unflagged INFO host-only lines;
- "Fix rounds 2 and 3 touched no test file other than the unit's own RED file" (`git diff --name-only 96676f1f HEAD` = CLAUDE.md, the service, the RED file);
- the deadline WARNING text; the outcome vocabulary; the passthrough scope; the redirect bound; limits (9), (12), (16), (18) and (19);
- the canary and owner steps (names only); the lint figures; the CI-order count 1059.

NOT TRUE or imprecise: m1, m2, m3 and m4 (extended) above; the comm paragraph's membership (MAJOR-E1); the "Logs" paragraph's silence on e-m6.

## Mutation table (mine, engineering; `eng/mutate_e.py`)
Method: the scratch worktree under my `.qa-mutation.lock`; a byte copy; one exact edit matching once (CRLF-adapted); `pyt.py` bound 600 over the unit file with `-x`, every `ENABLE_*` unset and `PYTHONDONTWRITEBYTECODE=1`; restore from the byte copy; a sha256 compare. Every restore was OK (service `b0d7b8d9...`, routes and handler sha-equal to their pre-mutation copies); the lock was removed.

| id | mutant | result | killing node / note | [pyt] |
|---|---|---|---|---|
| ES1 | v2 initial url not validated | KILLED | test_fetch_page_v2_blocks_private_initial_url | b4adv2e-ES1... 20:35:49-20:36:01 FAIL rc=1 |
| ES2 | v2 hop not validated | KILLED | test_route_fetch_blocked_or_capped_is_store_unreadable[POST-blocked_hop-blocked] | 20:36:02-20:36:10 FAIL |
| ES3 | v2 client follow_redirects=True | KILLED | test_redirect_to_homepage_is_not_product_page_post_fetch[POST] | 20:36:11-20:36:16 FAIL |
| ES4 | redirect loop range(4) | KILLED | test_fetch_page_v2_redirect_bound_is_five_requests | 20:36:16-20:36:27 FAIL |
| EH1 | passthrough for any code | KILLED | test_error_handler_four_key_body[on-other-code-keys] | 20:36:28-20:36:36 FAIL |
| EH2 | passthrough of extra keys | SURVIVED | equivalent (no B4 raise carries them) | 20:36:38-20:36:51 OK 408 passed |
| EL1 | non-transport fetch-failed line at ERROR | SURVIVED the unit file; KILLED by u8d R8 | test_sentry_channels_u8d_unit.py::TestR8SourceLines::test_u8d_pin_r8_no_other_outside_except_error_line | unit 20:36:51-20:37:08 OK; b4adv2e-EL1-pins 20:38:58-20:39:27 FAIL |
| EL2 | ON-path Detected retailer prints the url | KILLED | test_v2_fetch_log_records_carry_the_host_only[blocked_hop] | 20:37:09-20:37:25 FAIL |
| EL3 | refused line at ERROR | KILLED | test_pregate_homepage_pair_refused_before_reserve[POST-...] | 20:37:26-20:37:31 FAIL |
| ED1 | deadline 35 s | KILLED | test_test_seams_have_production_values | 20:37:31-20:37:36 FAIL |
| ER1 | same_url rule dropped | KILLED | test_pregate_same_url_after_normalisation[POST-identical] | 20:37:37-20:37:45 FAIL |
| EA31 | products_id in the homepage allow-list (A3-1) | SURVIVED | known gap (no row either way) | 20:37:45-20:37:54 OK 408 passed |

The brief's correctness-lens hand mutants (M1, E1, F2-4a..f, K1-K8b, R1-R5, T1-T2, E1b, F5e, X1, X5) were applied by the round-3 correctness adversary (`B4_adv2/correctness_REPORT.md`: 61 mutants, 60 KILLED, 1 SURVIVED = the A3-1 shape). I did not duplicate them; my ES4 / EL2 / EA31 overlap the F2-4d / F2-4a / A3-1 families.

## Prove-nothing rows (engineering scope)
- PR body lines 80 / 125 "ALONE": the overlap was not observed (m2).
- The comm "78 files" count includes 6 non-test modules that collect nothing (e-m7).
- The fix-3 `comm -13 base head is empty (the base was not re-run)` argues from the known pair rather than measuring the base. It is acceptable only because the head failure set equals the brief's known environmental pair; my runs reproduce the same set.
- `test_transport_error_line_carries_no_exception_info` proves `exc_text` / `stack_info` on one record only (m3).

## Deviations
- D1: `<scratchpad>/B4_adv2/` is shared with the round-3 correctness adversary (finished 19:50). My first logs `B4_adv2/unit_off.log`, `unit_on.log`, `ci_order.log`, `svc.diff` and `svc_base.py` overwrote same-named files of theirs. Their `[pyt]` ledger lines in `harness/pyt_ledger.jsonl` stand, and my overwrites are runs of the same bytes that also passed. Everything after 20:05 is under `B4_adv2/eng/`.
- D2: the hook files ran as background shell tasks (the 1800 s bound exceeds the tool's 600 s foreground limit). No other pytest of mine ran meanwhile. The `-k dash` half was stopped before its first node (above).
- D3: the probe file `tests/test_zz_b4adv2e_probe.py` ran in the scratch worktree (copied from `eng/`, removed after the run); `git status --short` of the scratch worktree was empty afterwards.

## NOT MEASURED
- The hook `-k dash` half here (stopped).
- Railway's edge request-body cap (MAJOR-E2 practical bound).
- Any live store, Sentry or Railway behaviour (rules).
- A base run of the comm chunks: the head failure set = the known environmental pair.

## Files (written by me; sha256 at report time in `eng/report_hashes.txt`)
`eng/notes.md`, `eng/mutate_e.py`, `eng/mut_el1_u8d.py`, `eng/test_zz_b4adv2e_probe.py`, `eng/comm_extra_chunk.txt`, `eng/run_hooks2.sh`, `eng/*.log`, `eng/mut_results.jsonl`, `B4_adv2/run_hooks.sh`, `B4_adv2/hygiene.py`, `B4_adv2/hygiene.txt`, `B4_adv2/comm_derive.py`, `B4_adv2/comm_why.py`, `B4_adv2/comm_derived.txt`, `B4_adv2/comm_union_derived.txt`, `B4_adv2/claude_row.txt`, `B4_adv2/base_url_routes.py`, `B4_adv2/base_error_handler.py`, `B4_adv2/hooks*.log`, this report.

## End state
Unit worktree `sc-s80-b4`: HEAD `0aac07f1f7304e61fa5cac86935c9306f08605d0`, `git status --short` empty, no `.qa-mutation.lock`; the working-copy sha256 of all 11 branch files equal at start and end (`eng/unit_wc_start.txt` == `eng/unit_wc_end.txt` as sets). Scratch worktree `B4_adv2_engineering` removed with `git worktree remove --force` and absent from `git worktree list`; no pytest of mine left running (process list: 0 `b4adv2e` processes). Hook files: two TIMEOUTs on the -k "not dash" half (131/167 passed, 0 failed each time) -> NOT MEASURED here; -k dash stopped, NOT MEASURED. Finished 21:12 AST (budget 90 min from 19:51).
