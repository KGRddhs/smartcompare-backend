# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- fix round 4 RE-VERIFIER, both lenses (correctness + engineering), 2026-10-22

Verdict: **SOUND** (blocking 0, MAJOR 0, minor 2, information 7). Both round-3 MAJORs are CLOSED with measurements on the round-4 bytes: MAJOR-E2 (two 5 MB links through the real POST route, flag ON: 400 `NOT_PRODUCT_PAGE` both / `url_too_long`, zero `parse_qsl` calls process-wide, 0 consumes, 0 fetches, 0 rows, the pre-gate under 10 microseconds) and MAJOR-E1 (the 121-file branch-level comm set re-derived independently with 0 missing files, every chunk re-run at HEAD: the only failures are the known cold-tiktoken pair). Every round-3 minor (m1, m2, m3, m4 extended, c-m1, c-m2, e-m5 / A3-1, e-m6, e-m7) is closed in code or text. 18 mutants on sha-verified byte copies: 16 KILLED (AssertionError only), 2 SURVIVED = the two minors below (pin gaps on adjacent shapes; neither is present in the code). Flag-OFF differential base `81df2b64` vs HEAD: 44 / 44 records byte-identical; R-A3 holds on all 22 flag-ON records. The hook test files are NOT MEASURED again (slow-spawn box, TIMEOUT rule could not be completed; bytes unchanged since base).

- Unit B4, worktree `C:/Users/SynAckITPC/Documents/AI/sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, HEAD verified `d2ee1c9c4e5e432c40620179252bb583f5c1e58b` at 22:57 AST (start) and at the end; `git status --short` empty at start and end; no `.qa-mutation.lock`; the unit worktree was never edited.
- Agent model: claude-opus-5-5.
- Read: s81-common.txt (start and before reporting), RULINGS_FIX4_B4.md (in full, twice), B4_FIX4_REPORT.md, PR_BODY.md (round 4, in full), B4_ADV3_correctness.md (in full), B4_ADV3_engineering.md (findings, row/PR section), B4_FIX3_REVERIFY.md (verdict, minors, closure table), GATE_B4.md, the CLAUDE.md B4 header + row (word diff 0aac07f1..d2ee1c9c and the full row as injected), the round-4 code diff (`git diff 0aac07f1 d2ee1c9c -- app/`) and the 362 appended RED lines. PLAN_S80 sections 0-1, RULINGS_R0 and RULINGS_BATCH1 are cited through the common brief and the fix-round rulings; not re-read in full.
- Scratch worktree `<scratchpad>/B4_fix4_adv` (detached `d2ee1c9c`, no node_modules); all 3,407 tracked files sha256-equal to the unit worktree after copying the LF RED file byte-exact over the autocrlf checkout (`treecmp.py`); service / routes sha-verified before the first mutant and after the last; removed at the end (`git worktree list` checked).
- No .env read, copied or printed; no flag set outside one runner call; no network (every netguard node of my runs is in `tests/.network_attempt_baseline.txt`: 82 distinct, 0 new).

## 1. Re-hash

| file | sha256 (unit worktree bytes) | check |
|---|---|---|
| tests/test_s80_url_mode_v2.py | `18529278af07cb65ca686636380ef033fb5f67a24a0c853b1a87d5571c744ef2` | == `git show HEAD:` (the LF blob); 138,403 B, 0 bytes > 127, 0 CR; its first 119,355 bytes == the `bac87301...` file of `0aac07f1` (pure append, 362 lines) |
| app/services/url_extraction_service.py | `edc9a2449566b821954183715d0bdd2faabef0bf3954ef6bad5875b0f1a990ee` | CRLF 1426/1426, 18 bytes > 127 (unchanged count) |
| app/api/url_routes.py | `d96aa60b513c6a9e270da367c66a15b70b53544a9f5386f6df1f80b52c4410e8` | CRLF 547/547, 0 bytes > 127 |
| app/middleware/error_handler.py | `7e539cc7b17fcc6c9b982a2ebe4b212096af57deb8c1bded330eb57e5fc6d482` | unchanged |
| CLAUDE.md | `fdc0397ae0a3460fbe32dc975d4ef1fa63f55f3d37a0b18e9998ee0c4e2257be` | CRLF 938/938 in the working copy, blob LF, 3,979 bytes > 127 before and after (2 lines changed, both ASCII) |

Added-line sweep of `git diff -U0 0aac07f1 d2ee1c9c` (423 lines): 0 non-ASCII, 0 @gmail, 0 +973, 0 8+-digit runs, 0 sk- / AKIA / xox / eyJ / credentialed-URL / PEM. `git diff --name-only 96676f1f d2ee1c9c -- tests/` = the unit's RED file only. `git diff --name-only 81df2b64 HEAD -- .githooks .gitleaks.toml` = empty. ruff 0.16.5 `--select E9,F63,F7,F82` clean on the service, routes, error handler and the RED file; `compile()` clean; full-rule ruff with the repo config 57 -> 57 (service) and 12 -> 12 (routes), 0aac07f1 vs HEAD.

## 2. Runs (every pytest through pyt.py; mine one at a time; scratch worktree unless named)

```
unit flag unset: 452 passed, 11 warnings in 16.80s; [hermeticity] sentinel checked 452 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4f4rv-unit-off start=2026-10-22 22:59:25 end=2026-10-22 22:59:43 elapsed=18s bound=600s status=OK rc=0
unit ENABLE_URL_MODE_V2=true: 452 passed, 11 warnings in 12.97s; sentinel 452; netguard 0
[pyt] tag=b4f4rv-unit-on start=2026-10-22 22:59:53 end=2026-10-22 23:00:07 elapsed=14s bound=600s status=OK rc=0
probes (section 4): 15 passed, 1 failed = a probe artifact (the GET probe's 60 KB link, percent-encoded, exceeded the TEST CLIENT's 65,536-char url limit: httpx InvalidURL in the client, not the app); re-run at 20 KB:
[pyt] tag=b4f4rv-probe1 start=2026-10-22 23:08:36 end=2026-10-22 23:08:59 elapsed=22s bound=600s status=FAIL rc=1
[pyt] tag=b4f4rv-probe1b start=2026-10-22 23:09:41 end=2026-10-22 23:10:10 elapsed=29s bound=600s status=OK rc=0
RED file on the 0aac07f1 code bytes (service + routes swapped in under my lock, restored sha-verified): 32 failed, 420 passed, 11 warnings in 17.70s; every failure location line AssertionError
[pyt] tag=b4f4rv-RED_at_0aac07f1 start=2026-10-22 23:11:40 end=2026-10-22 23:12:02 elapsed=21s bound=600s status=FAIL rc=1
18 mutants (section 3): one [pyt] line each, 23:12:02-23:21:50
flag-OFF differential (the round-3 correctness adversary's probe test_zz_b4adv3c_offdiff.py, copied in unchanged, 11 scenarios x POST/GET x {unset, "false", "true"}, full configuration): 66 passed; sentinel 66; netguard 0
[pyt] tag=b4f4rv-offdiff-head start=2026-10-22 23:22:36 end=2026-10-22 23:23:09 elapsed=33s bound=600s status=OK rc=0
  -> compared with B4_adv2/offdiff_base.jsonl (recorded at 81df2b64): OFF records compared 44, identical 44, differing 0; ON leg 22 / 22 R-A3 OK (og_site_llm now 200 with 1 LLM call: the F4-4 effect)
CI-order set (13 files, alphabetical, flag OFF): 1103 passed, 13 warnings in 24.17s; sentinel 1103; netguard blocked 10 attempt(s) from 10 node(s)
[pyt] tag=b4f4rv-ci-order start=2026-10-22 23:27:03 end=2026-10-22 23:27:30 elapsed=28s bound=1200s status=OK rc=0
comm 00 (25 files): 951 passed, 1 skipped, 3 deselected, 23 warnings in 66.41s; sentinel 952; netguard blocked 15 attempt(s) from 5 node(s)
[pyt] tag=b4f4rv-comm-00 start=2026-10-22 23:28:07 end=2026-10-22 23:29:16 elapsed=68s bound=1200s status=OK rc=0
comm 01 (25): 2124 passed, 18 warnings in 108.96s; sentinel 2124; netguard blocked 29 attempt(s) from 28 node(s)
[pyt] tag=b4f4rv-comm-01 start=2026-10-22 23:29:24 end=2026-10-22 23:31:15 elapsed=111s bound=1200s status=OK rc=0
comm 02 (25): 1064 passed, 5 skipped, 5 deselected, 1 xfailed, 13 warnings, 2 errors in 35.06s (ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable, ::test_render_digests_match_base_except_the_fence = the known cold-tiktoken pair); sentinel 1067; netguard blocked 204 attempt(s) from 13 node(s)
[pyt] tag=b4f4rv-comm-02 start=2026-10-22 23:31:59 end=2026-10-22 23:32:39 elapsed=39s bound=1200s status=FAIL rc=1
comm 03 (25): 2047 passed, 13 warnings in 185.39s; sentinel 2047; netguard blocked 12 attempt(s) from 6 node(s)
[pyt] tag=b4f4rv-comm-03 start=2026-10-22 23:34:40 end=2026-10-22 23:37:47 elapsed=188s bound=1200s status=OK rc=0
comm 04 (21): 768 passed, 9 skipped, 10 deselected, 35 xfailed, 12 warnings in 75.94s; sentinel 812; netguard blocked 90 attempt(s) from 42 node(s)
[pyt] tag=b4f4rv-comm-04 start=2026-10-22 23:32:49 end=2026-10-22 23:34:13 elapsed=84s bound=1200s status=OK rc=0
URL-route readers, ENABLE_URL_MODE_V2=true exported, chunk 00 (25): 1086 passed, 3 skipped, 3 deselected, 1 xfailed, 13 warnings, 2 errors (the same cold-tiktoken pair); sentinel 1090; netguard blocked 213 attempt(s) from 22 node(s)
[pyt] tag=b4f4rv-urlreaders-on-00 start=2026-10-22 23:38:34 end=2026-10-22 23:41:44 elapsed=190s bound=1200s status=FAIL rc=1
chunk 01 (15): 1234 passed, 13 warnings; sentinel 1234; netguard blocked 12 attempt(s) from 8 node(s)
[pyt] tag=b4f4rv-urlreaders-on-01 start=2026-10-22 23:41:54 end=2026-10-22 23:43:26 elapsed=92s bound=1200s status=OK rc=0
tests/test_sentry_channels_u8d_unit.py alone: 141 passed; sentinel 141; netguard 0
[pyt] tag=b4f4rv-u8d-unit start=2026-10-22 23:44:11 end=2026-10-22 23:44:21 elapsed=10s bound=600s status=OK rc=0
tests/test_sentry_channels_u8d.py alone: 131 passed; sentinel 131; netguard 0
[pyt] tag=b4f4rv-u8d start=2026-10-22 23:44:25 end=2026-10-22 23:44:34 elapsed=9s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag unset: 21 passed; netguard blocked 2 attempt(s) from 2 node(s) (baseline sentinel nodes)
[pyt] tag=b4f4rv-meter-off start=2026-10-22 23:44:37 end=2026-10-22 23:44:42 elapsed=5s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag exported: 21 passed; the same 2 baseline nodes
[pyt] tag=b4f4rv-meter-on start=2026-10-22 23:44:45 end=2026-10-22 23:44:50 elapsed=5s bound=600s status=OK rc=0
CLAUDE.md readers (tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py): 79 passed; sentinel 79; netguard 0
[pyt] tag=b4f4rv-claude-readers start=2026-10-22 23:44:53 end=2026-10-22 23:44:58 elapsed=5s bound=600s status=OK rc=0
hook test files (all four, -k "not dash", alone on the box at launch, bound 1800): stopped by me at 00:02:54 after 36 nodes passed, 0 failed, 0 errors (about 27 s per node; node -e 0 2.14 s at 23:50 = the slow-spawn state); no [pyt] summary line (the runner was killed with its tree: my own tag b4f4rv-hooks-notdash, cwd my scratch worktree, PIDs 500396 > 500968 > 2056 > 501952, command lines read first) -> NOT MEASURED (section 6)
```
Netguard over all my logs (hook logs excluded): 82 distinct nodes, 0 not in `tests/.network_attempt_baseline.txt` (12 of them egress-class, all baselined). Every number above equals the fix agent's figure for the same set (chunk 04's netguard count 90 / 42 vs the fix agent's 87 / 41 differs by one baselined node; the pass / skip / xfail counts are identical). The fix agent's [pyt] lines in the PR body were cross-checked against `harness/pyt_ledger.jsonl`: every tag, start, end, status and summary matches. Not re-run by me: the 20-file pin set with the flag exported (its [pyt] line `b4f4-pins20-flagON` is in the ledger, OK, 1037 passed; 14 of its 20 files are inside my URL-reader chunks above, which ran green with the flag exported).

## 3. Mutation table (scratch worktree; `B4_fix4_rv/mutate_rv.py`: `.qa-mutation.lock` (label `b4f4rv-reverifier (claude-opus-5-5)`) -> byte copy -> one exact edit matching ONCE (CRLF-adapted) -> pyt.py bound 600 over the FULL unit file, every ENABLE_* unset, PYTHONDONTWRITEBYTECODE=1 -> restore from the byte copy -> sha256 compare (abort on mismatch; none: every restore `edc9a244...` / `d96aa60b...`) -> lock removed; logs `mut_<id>.log`, results `mut_results.jsonl`; the kill class is read from pytest's traceback location lines)

| mutant (fix) | edit | result | failing nodes (functions) | [pyt] |
|---|---|---|---|---|
| B1 (F4-1 bound) | `len(u) > _URL_V2_MAX_LINK_CHARS + 1` (2,049 accepted) | KILLED | 8 (`test_link_over_2048_chars_refused_before_any_parse`) | tag=b4f4rv-B1_bound_plus_one 23:12:02-23:12:19 elapsed=16s status=FAIL rc=1 |
| B2 (F4-1 bound) | `for u in (url1, url1)` (url2 never checked) | KILLED | 6 (same function) | tag=b4f4rv-B2_url2_never_checked 23:12:21-23:12:40 elapsed=19s status=FAIL rc=1 |
| B3 (F4-1 reason) | the bound returns reason `homepage` | KILLED | 9 (+ `test_two_5mb_links_refused_fast_with_no_parse`) | tag=b4f4rv-B3_long_reason_homepage 23:12:42-23:13:17 elapsed=34s status=FAIL rc=1 |
| B4 (F4-1 placement) | a length 400 in the GET route BEFORE the flag branch | KILLED | 4 (GET rows of the long-link function; flag-ON rows only) | tag=b4f4rv-B4_get_bound_outside_flag 23:13:17-23:13:42 elapsed=25s status=FAIL rc=1 |
| B5 (F4-1 OFF identity, GET) | `if not v2 and (len(url1) > 2048 or len(url2) > 2048): raise 400` in the GET route | **SURVIVED** | 0 | tag=b4f4rv-B5_get_bound_flag_off_only 23:16:06-23:16:52 elapsed=46s status=OK rc=0 |
| B6 (F4-1 OFF identity, POST) | the same in the POST route | KILLED | 2 (`test_flag_off_5mb_links_are_base_behaviour`) | tag=b4f4rv-B6_post_bound_flag_off_only 23:16:52-23:17:26 elapsed=34s status=FAIL rc=1 |
| V1 (F4-1 view) | `url_pre_gate_view`'s route filter keeps only `route` pairs | KILLED | 18 (5 functions) | tag=b4f4rv-V1_route_filter_route_only 23:17:27-23:17:56 elapsed=29s status=FAIL rc=1 |
| V2 (F4-1 parse once) | the view parses the query a second time for the route pairs | KILLED | 3 (`test_pregate_parses_each_query_once_per_request`, `test_pregate_pass_path_parses_each_query_once`) | tag=b4f4rv-V2_view_parses_twice 23:17:57-23:18:12 elapsed=15s status=FAIL rc=1 |
| V3 (F4-1 parse once, empty pairs) | `classify_url_path`: `if not pairs` (re-parse when the passed pairs are EMPTY) | **SURVIVED** | 0 | tag=b4f4rv-V3_empty_pairs_reparse 23:18:14-23:18:56 elapsed=41s status=OK rc=0 |
| EA31r (F4-3) | `products_id` dropped from `_PRODUCT_ROUTE_QUERY_KEYS` | KILLED | 12 (3 functions) | tag=b4f4rv-EA31r_products_id_dropped 23:18:59-23:19:55 elapsed=56s status=FAIL rc=1 |
| EA31p (F4-3, post-fetch site only) | the post-fetch check classifies `final_url` with `products_id` renamed | KILLED | 8 (`test_products_id_pair_delivers_flag_on`, `test_redirect_to_zen_cart_pdp_is_not_refused_post_fetch`) | tag=b4f4rv-EA31p_postfetch_site_only 23:20:31-23:20:50 elapsed=19s status=FAIL rc=1 |
| T6 (F4-4) | the meta-title usability check ignores the site names | KILLED | 4 | tag=b4f4rv-T6_meta_title_ignores_site_names 23:20:51-23:21:08 elapsed=17s status=FAIL rc=1 |
| T7 (F4-4) | first truthy of og:title / `<title>`, THEN the usability check (no fall-through) | KILLED | 6 | tag=b4f4rv-T7_first_truthy_then_usable 23:21:10-23:21:21 elapsed=11s status=FAIL rc=1 |
| X7 (F4-5) | `exc_info=True` on the type-only line | KILLED | 2 (`test_extract_with_ai_error_line_carries_the_type_only`) | tag=b4f4rv-X7_error_line_exc_info 23:21:22-23:21:33 elapsed=11s status=FAIL rc=1 |
| X8 (F4-5) | `repr(e)` on the line | KILLED | 2 (same) | tag=b4f4rv-X8_error_line_repr 23:21:33-23:21:50 elapsed=17s status=FAIL rc=1 |
| RED_at_0aac07f1 (control) | the 0aac07f1 service + routes under the round-4 RED file | 32 failed, 420 passed (= the RED step) | AssertionError only | tag=b4f4rv-RED_at_0aac07f1 23:11:40-23:12:02 elapsed=21s status=FAIL rc=1 |

16 of the 18 mutants were KILLED, each by an AssertionError only (0 collection / setup errors). At least one per F4 fix was killed: F4-1 by B1-B4, B6, V1 and V2; F4-3 by EA31r and EA31p; F4-4 by T6 and T7; F4-5 by X7 and X8. EA31r is the inverse of the round-3 survivor EA31. Its round-3 form (the allow-list made equal to the same-url key set) is now the shipped code, so EA31r is the mutant that tests it. The unmutated control is the two unit runs (452 / 452). The two survivors are recorded as minors m-1 and m-2.

## 4. Runtime truth (probes `B4_fix4_rv/test_zz_b4f4rv_probe.py`, real route, full configuration of the RED harness; output `probe.jsonl`, `probe_get.jsonl`)

- **MAJOR-E2 closure (measured).** A process-wide recorder wrapped `urllib.parse.parse_qsl`, which every `parse_qs` calls, plus the service's own `parse_qs` name. Through the real POST route, with the full configuration:
  - Flag ON, two 5 MB `index.php?product_id=N&a=b&...` links: 400 `{code NOT_PRODUCT_PAGE, field both, reason url_too_long}` with the store-page copy. **0 parse calls** of any length, 0 consumes, 0 refunds, 0 fetches, 0 search_logs rows, 0 LLM calls. The pre-gate's own wall time rounds to 0.0 ms (under 10 microseconds). The whole test-client request took 0.31 s on the first call of the session (warm-up) and 0.069 s for the marker-less twin. Before this round the engineering adversary measured 3.55 s.
  - Flag ON, one long link: field `url1`, 0.034 s.
  - Flag OFF, the same requests: the base codeless 400, 1 consume, 1 refund, 1 failure row, 0.077-0.079 s. This is the base behaviour; the OFF differential below shows it is unchanged.
  - GET, a 20 KB link: 400 `url1` / `url_too_long`, 0 service parses, 0 consumes, 0 fetches.
- **Parse-once on the pass path (measured).** A delivered same-store OpenCart pair (`product_id` 1262 vs 1263) through the real route made exactly 4 service `parse_qs` calls, each on a 37-character query. Two are the pre-gate (one per link) and two are the post-fetch final-url checks (stated in limit (20)).
- **Refactor equivalence.** `url_pre_gate_view(u) == (classify_url_path(u), normalize_url_for_same_check(u))` on 35 urls. They include every F4-3 shape, `products_id[]`, an upper-case key, cart and listing routes carrying `products_id`, a malformed port, `http://[::1` (urlsplit ValueError), `""`, a non-url, a duplicated key and a 1,600-character tracking prefix: 35 / 35 equal.
- **F4-3 classes.** All of these are exempt (None):
  - `/?products_id=12`;
  - `/?Products_Id=12`;
  - Zen Cart `main_page=product_info&products_id=12`;
  - `main_page=shopping_cart&products_id=12`;
  - `/?route=checkout/cart&products_id=5`;
  - `/?route=product/category&products_id=5`.

  The last three are the stated cart / listing consequence, now covering `products_id`. Still homepage: `/?products_id=`, `/?products_id[]=12`. The pre-gate gives:
  - `?products_id=12` vs `13`: passes;
  - the same id with different tracking keys: `same_url` (correct);
  - a 2,049-character pair: `both / url_too_long`;
  - an exactly 2,048-character link: passes.
- **F4-4 rule (`extract_generic_data_v2`, node-less pages).**
  - A usable og:title wins over an unusable `<title>`.
  - og:title equal to the site name with a site-name `<title>`: None, so `no_product_node` at $0.
  - `RASASI STORE!` (case and punctuation variant of the site name): unusable, so the `<title>` is taken.
  - A missing og:title with a placeholder `<title>`: None.
  - An empty og:title: the `<title>` is taken.
  - A placeholder og:title (`Unknown`) with `<title>` `Rasasi Store | Home`: the `<title>` is taken. That is the cost class the PR body names: one paid LLM call where round 3 refused at $0. See i-6.
- **Flag-OFF identity.** The OFF differential is 44 / 44 byte-identical between `81df2b64` and `d2ee1c9c`. Each record compares status, body minus request_id, consume / refund / lifetime / history / search_logs rows, the fire-and-forget labels, the LLM and verdict call counts and the fetched url list. By code reading, every round-4 hunk is behind `if v2:` or is reached only from flagged code:
  - the bound and `url_pre_gate_view` sit in `_url_pre_gate`;
  - `pairs=` is passed only by the view;
  - `_PRODUCT_ROUTE_QUERY_KEYS` is read by `classify_url_path`, the view and the import-time `_SAME_URL_PRODUCT_QUERY_KEYS`, whose set is unchanged;
  - the meta title is computed inside `extract_generic_data_v2`.

  The exception is the unflagged F4-5 log line.
- **R-A3.** All 22 flag-ON records of the differential hold R-A3 (pre-gate refusals: 0 consume, 0 row; post-fetch refusals: 1 consume, 1 refund, 1 failure row with the code's constant; deliveries: 1 consume, lifetime 1, history 1). The `url_too_long` exit is a pre-gate refusal with 0 consume and 0 row (probe above and the RED rows).
- **Client bound.** `SmartCompareApp/src/components/TwoInputShell.tsx:225` `URL_MAX = 2048`. `validateUrl` checks the trimmed length in [1, 2048], and the TextInput's `maxLength={URL_MAX}` caps the raw text, so no app-built link exceeds the server bound. The bound refuses only non-app callers.

## 5. Findings

### BLOCKING
None.

### MAJOR
None.

### minor
- **m-1 (pin gap, flag-OFF identity of the GET route for an over-long link).** Mutant B5 survives the 452-node unit file. It adds a length 400 to the GET route that fires only when the flag is OFF. The F4-1 flag-OFF PIN `test_flag_off_5mb_links_are_base_behaviour[*]` is POST-only, because a GET cannot carry 5 MB. No flag-OFF GET row uses a link longer than 2,048 characters, so a "bound outside the flag" regression on GET would ship green. Its POST twin B6 and the flag-ON GET twin B4 are killed. The shipped code is correct: the bound lives only in `_url_pre_gate`, called only under `if v2:`, and the OFF differential is identical. Proposed fix (one appended row at the gate's discretion): a flag-OFF GET row with a 2,049-20,000-character link under the full configuration and the raising pre-gate stand-in, asserting the base 400 and one refund. The probe in section 4 shows the test client carries a 20 KB GET link.
- **m-2 (pin gap, "parse once" for a link whose pairs are empty).** Mutant V3 survives. In it, `classify_url_path` re-parses its own query when the view passes an EMPTY pairs list: a marker-less root link, a tracking-only link or a homepage. The parse-count rows use links that carry a product marker (non-empty pairs). The result is identical, and the harm class is closed by the 2,048 bound: each extra parse is of at most 2,048 characters, microseconds. The ruling's "no second parse" is therefore not pinned for this path. Proposed fix (optional): a parse-count row for a tracking-only / homepage pair, expecting one parse per link. Grade information if the gate considers the bound sufficient.

### information
- i-1 The fix agent's deviations D1-D4 are measured and consistent:
  - D1: the F4-5 row is RED at `0aac07f1`;
  - D2: the 2,048 boundary row is a PIN, killed by B1 here and by L1 in the fix agent's run;
  - D3: the 50 ms bound is asserted on the pre-gate wall; the whole request is under 1 s;
  - D4: the parse-count scope is the pre-gate; the post-fetch check parses once more, measured in section 4.
- i-2 ID collision: RULINGS_FIX1_B4 and RULINGS_FIX4_B4 both number their rulings F4-1..F4-6. PR body line 17 cites "F4-1, amending GC-1" without the file name; that is the fix-round-1 ruling, while F4-1 elsewhere in the body is the round-4 bound. The CLAUDE.md row qualifies the same citation as "RULINGS_FIX1_B4 F4-1". Wording only.
- i-3 PR body line 22: "`products_id` in `_PRODUCT_ROUTE_QUERY_KEYS`, read only through `classify_url_path`". It is also read by `url_pre_gate_view`'s route filter and by the import-time `_SAME_URL_PRODUCT_QUERY_KEYS` union, whose value is unchanged. All readers are flagged, so the OFF claim stands. Wording only.
- i-4 Limit (20) and the PR F4-1 bullet say the host-only `URL comparison request` INFO line still reads an over-long link. That is true for POST; the GET route has no such line, and only the SSRF validation reads it there. Wording only.
- i-5 The X1 row's docstring still overclaims (round-3 m3). The rulings allow no edit to an existing row; it is recorded in the row and the PR body, and the assertions stand.
- i-6 F4-4 cost: the PR body carries the cost note (the adversary's 5 held non-PDP pages now take one paid LLM call each where round 3 refused at $0). The CLAUDE.md row states the rule but not the cost. Limit (6) ("the LLM is still called once per link with a usable title and no price (cost unchanged)") remains true against base, where those pages were also LLM-called. Optional one-clause addition at the rebase.
- i-7 The hook test files are NOT MEASURED for the second round running (section 6). Their bytes are unchanged since base, and the last complete measurement is fix round 3: 324 passed + 3 skipped (fix agent) and 327 / 0 failed (round-3 re-verifier).

## 6. Hook test files (F3-7 / the brief's TIMEOUT rule)

**Launch.** `tests/test_precommit_hook.py`, `tests/test_precommit_hook_phase_b.py`, `tests/test_precommit_hook_phase_b_round2.py` and `tests/test_precommit_hook_round2.py` started together at 23:45:37 with `-k "not dash"` (167 of the 327 nodes) and bound 1800. No other pytest was running on the box at launch (process list read at 23:45:19; only the stall monitor was up).

**Rate.** At about 27 s per node the half could not finish inside its bound: `node -e 0` measured 2.14 s at 23:50, against 0.59-0.87 s earlier in the session. By the brief's rule the box was pathological, and my 90-minute budget could not hold the second half plus the TIMEOUT re-run.

**Stop.** I stopped the run at 00:02:54 after **36 nodes passed, 0 failed, 0 errors**. It was my own process tree: command lines were read first and matched tag `b4f4rv-hooks-notdash` and my scratch cwd, and the stop was `taskkill /T /F` on the runner, PID 500396.

**Verdict for the hook files: NOT MEASURED** (the same as in fix round 4).

**Why this blocks nothing:**
- the unit changes no hook byte (`git diff --name-only 81df2b64 HEAD -- .githooks .gitleaks.toml` is empty);
- the pre-commit hook itself ran on the round-4 commit (`All checks passed!`, the fix report);
- the last complete measurement is fix round 3 on the same hook bytes.

**Owed.** Re-run the four files when the box is quiet (about 4.7 s per node then), or accept the round-3 measurement at the gate.

## 7. Closure of the previous round's findings

| finding (source) | status | evidence |
|---|---|---|
| MAJOR-E2 unbounded pre-gate parsing (ADV3 engineering) | CLOSED | section 4: 0 parses, 0 cost, pre-gate < 10 us on two 5 MB links; mutants B1-B4, B6, V1, V2 killed; RED rows fail at 0aac07f1 (32 / 420 reproduced) |
| MAJOR-E1 comm set missed the recorder's importers (ADV3 engineering) | CLOSED | independent re-derivation at HEAD: module grep `url_routes|url_extraction_service|error_handler|w4_11_prompt_digest_recorder` = 40 files, of which 37 are collectable and all are in the 121-file list (`conftest.py`, `_env_safety.py` and the recorder are the 3 non-collectable modules). All named files are in the list: `test_price_fallback_may_decline`, `test_limiter_endpoint_key`, `test_observability`, the 7 comment matches, the 10 SmartCompareApp scanners and every source-scanning pin. Every SmartCompareApp scanner (23), app/ walker (58), CLAUDE.md namer (34) and symbol-grep file (16) is in it; 0 missing. All 5 chunks re-run at HEAD (section 2): only the known cold-tiktoken pair fails |
| m1 PR line 42 intermediate sha (FIX3 re-verifier, confirmed by both ADV3) | CLOSED | PR line 44 cites `bac87301...`, 119,355 B + the CRLF-checkout note (verified: the fresh scratch checkout hashed `2d2b1cf7...`, the blob `18529278...`) |
| m2 hooks "ALONE" overclaim | CLOSED | PR lines 82 and 186: "run alone except d03rev-probe1, which overlapped 16:45-16:46; result stands" |
| m3 X1 sentence | CLOSED (docstring recorded, i-5) | row: "on that record, and no record of the run carries exception info"; PR line 17 / 80 scoped; matches the asserts at `tests/test_s80_url_mode_v2.py:2399-2401` |
| m4 extended (listing / cart route exemption) | CLOSED | row effect clause + limit (1); PR lines 10, 77, 201; probe: cart and listing routes with `product_id` / `products_id` are exempt |
| c-m1 first truthy meta title (ADV3 correctness) | CLOSED | F4-4 code; 7 rows; T6 / T7 (and the fix agent's T4 / T5) killed; the differential's `og_site_llm` ON record now delivers |
| c-m2 limit (11) class | CLOSED | row limit (11) and PR line 201 name every same-store pair outside the five keys (`?pid=`, `product.php?id=`, `ProductDetails.aspx?ProductID=`, `item?sku=`) and the deny-list follow-up |
| e-m5 / A3-1 `products_id` homepage marker (both ADV3) | CLOSED | F4-3; 15 rows; EA31r and EA31p killed; Zen Cart post-fetch row |
| e-m6 exception text on the ON-path ERROR line | CLOSED | F4-5 (`type(e).__name__`), unflagged log-only; X7 / X8 (and X6 / X6b) killed |
| e-m7 comm hygiene (non-collectable modules; `test_rate_limiting_complete` silent) | CLOSED | the list holds 121 `tests/test_*.py` files, all present on disk; the PR comm paragraph states `test_rate_limiting_complete` is IN (green) |
| A3-1 Zen Cart extension, I1 survivor (ADV3 correctness) | CLOSED | the Zen Cart rows in F4-3; the I1 / EA31 reading is now the code |
| i-1 amazon / noon title, i-3 same-scheme (ADV3 correctness, information) | unchanged, recorded | limits (3) / (7); same-scheme is cost only |
| fix-agent open questions 1-4 | 1: hooks still NOT MEASURED (section 6). 2: keep `test_rate_limiting_complete` in (green, baselined nodes). 3: not required, since the post-fetch parse is of one final url bounded by httpx at 65,536 characters and comes after a paid fetch (limit 20). 4: the edge request-body cap is NOT MEASURED, an owner follow-up | |

## 8. CLAUDE.md row and PR body against the bytes

- **Row (word diff `0aac07f1..d2ee1c9c`, the 2 changed lines read in full).** Each sentence below was checked against the code and the measurements and is TRUE:
  - the header citation of RULINGS_FIX4_B4 F4-1..F4-6;
  - the 2,048 bound (`url_routes._URL_V2_MAX_LINK_CHARS`, checked first, reason `url_too_long`);
  - the listing / cart clause with the four keys;
  - `products_id` with the Zen Cart url;
  - "parsed ONCE per request for both the class and the key, `url_pre_gate_view`" (true for the code; the empty-pairs path is not pinned, m-2);
  - the reason vocabulary incl. `url_too_long`;
  - the first-usable meta title;
  - "that first meta title";
  - the X1 sentence;
  - the F4-5 unflagged sentence;
  - limit (1);
  - limit (11);
  - limit (16): 452 / 21 / 40 readers 2,320 = 1,086 + 1,234 / 1,037 pins (ledger), re-measured here except the pins;
  - limit (20) (i-4 wording on GET).

  The row stays ASCII on its changed lines and CRLF in the working copy.
- **PR body (`d1a3a009...`, 209 lines, read in full).** Each sentence below was checked and is TRUE:
  - line 3 (the commits);
  - lines 10, 11, 17, 20, 22 (i-2 and i-3 wording);
  - the defect table's round-4 node counts (4 / 6 / 2 / PIN 3; 4 / 2 / PIN 1; 8 / 1 / 2 / 1 / PIN 6 / PIN 2; 2), counted from the parametrisations and from the RED-at-base failing set (32);
  - line 44 (append-only prefix, sha, node count, the CRLF note);
  - line 57 (no other test file touched since `96676f1f`);
  - the Fix round 4 bullets;
  - the round-4 deviations;
  - every round-4 gate figure (the RED step, unit, u8d, metering, CI-order, the five comm chunks, the URL readers, CLAUDE.md readers, lint 57 -> 57 / 12 -> 12), re-measured here or cross-checked against the runner ledger;
  - the mutation paragraph (ledger tags present);
  - the stated-limits paragraph and the owner steps (unchanged by this round except the `url_too_long` sentence).

  The hooks paragraph (line 143) is accurate: its two TIMEOUT [pyt] lines are in the ledger. NOT TRUE: nothing found. Imprecise: i-2, i-3 and i-4 (wording only).

## 9. Deviations

- D1 The hook call (section 6) ran as a background shell task with no other pytest of mine running, because one tool call cannot exceed 600 s and the brief's bound for the hook files is 1,200-1,800 s. It is my own tree, tag `b4f4rv-hooks-notdash`; its command line was read before it was stopped. The fix agent's D6 is the same.
- D2 The mutants and probes ran in my scratch worktree, not in place. The RED-at-base control swapped both code files to their `0aac07f1` blobs (CRLF-adapted) and restored them sha-verified.
- D3 My probe's first GET case (60 KB) hit the TEST CLIENT's own 65,536-character url limit, not the app. It was re-run at 20 KB; the `b4f4rv-probe1` FAIL line above is that artifact.

## 10. NOT MEASURED

- The four `tests/test_precommit_hook*.py` files to completion (section 6).
- The 20-file pin set with the flag exported (not re-run; the fix agent's ledger line stands, and 14 of its 20 files ran in my flag-ON URL-reader chunks).
- A base re-run of the comm chunks: the HEAD failure set is the brief's known environmental pair.
- Live stores, Sentry, Railway and the edge request-body cap (rules).
- The post-rebase run (GC-7, the orchestrator's).

## 11. End state

HEAD `d2ee1c9c4e5e432c40620179252bb583f5c1e58b` in `sc-s80-b4`, `git status --short` empty, no `.qa-mutation.lock`, never edited. Scratch worktree `B4_fix4_adv` removed with `git worktree remove --force` (it had no node_modules); `git worktree list` no longer shows it. No pytest of mine is left running. Notes folder `<scratchpad>/B4_fix4_rv/` holds:
- `notes.md`, `treecmp.py`, `mutate_rv.py`, `mut_results.jsonl`, `mut_*.log`, `mut_bak/`;
- `test_zz_b4f4rv_probe.py` (a copy; the copy in the scratch worktree was deleted before the comm runs), `probe.jsonl`, `probe_get.jsonl`, `offdiff_head4.jsonl`;
- `comm4_list.sorted`, `modgrep.txt`, `red_prev.py`, `ruffprev/`;
- every `*.log`.
