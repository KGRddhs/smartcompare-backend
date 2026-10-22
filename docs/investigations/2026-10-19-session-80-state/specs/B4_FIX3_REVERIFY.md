# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- fix round 3 RE-VERIFIER, correctness lens (2026-10-22)

Verdict: **SOUND** (blocking 0, MAJOR 0, minor 5: four doc-accuracy sentences in the PR body / CLAUDE.md row and one information-grade pin-gap pair). MAJOR-R1 and m1-m9 of the round-2 re-verifier are CLOSED with evidence; every fix-round-3 hunk is correct against RULINGS_FIX3_B4, unreachable flag OFF (measured), and every F3 mutant plus the five F3-5 mutants is killed on sha-verified byte copies. The bytes moved, so both adversaries still run on this HEAD (RULINGS_FIX3_B4).

- Unit B4, worktree `C:/Users/SynAckITPC/Documents/AI/sc-s80-b4`, branch `feature/s80-b4-url-mode-v2`, HEAD verified `0aac07f1f7304e61fa5cac86935c9306f08605d0` at 17:05 AST and again at the end; `git status --short` empty at start and end; no `.qa-mutation.lock`; the worktree was never edited (every run there with PYTHONDONTWRITEBYTECODE=1, ruff with --no-cache).
- Agent model: claude-opus-5-5 (this agent's system prompt). The relayed user request ("dont forget to run /synack-build-orchestrator"): the skill was loaded at the start; this report is its Step-5 gate review on the exact bytes, with the Step-6 categories in section 7; orchestration, issues and PRs stay the orchestrator's.
- Read: s81-common.txt (start and again before reporting), PLAN_S80.md sections 0-1, RULINGS_BATCH1.md (B4 section), GATE_B4.md, RULINGS_FIX2_B4.md (F2-1, F2-3, F2-6, its re-verifier section), RULINGS_FIX3_B4.md (binding; twice), B4_FIX2_REVERIFY.md (in full), B4_ADV2_correctness.md and B4_ADV2_engineering.md (findings sections), B4_FIX3_REPORT.md, PR_BODY.md (sha256 `ddb7487437c502efe6530a3069cb314f0d6d5adb6e1be604a5d4d3e43ff7f98a`, 40,669 B, LF, 4 bytes > 127 = the robot attribution line), the CLAUDE.md B4 header + row (lines 474-475), the full 83daa8cb..0aac07f1 diff and the route / service code it touches. Not opened: RULINGS_R0.md (the rulings above cite what this lens needed).
- Scratch worktree `<scratchpad>/B4_fix3_adv` (detached 0aac07f1, no node_modules); the LF RED file copied byte-exact over the autocrlf checkout; 15 unit / support files sha-equal to the worktree before the first mutant and after the last (`B4_fix3_rv/shacheck.py`; service `b0d7b8d9...`, routes `9229e0b4...`, error_handler `7e539cc7...`, CLAUDE.md `c4af5803...`, metering `4724c308...`, RED `bac87301...`). Notes, harness, logs: `<scratchpad>/B4_fix3_rv/`.
- No .env read, copied or printed; no flag set outside one runner call (ENABLE_* names in this agent's environment: none, read by name only); no network (every netguard node below is in `tests/.network_attempt_baseline.txt`, checked id by id).

## 1. RED file re-hash

`tests/test_s80_url_mode_v2.py` = `bac8730196c75769e672646e6f1dee7901bfb3fb275af1d84af6a9d97517f1d9` (worktree bytes = the committed blob `git show HEAD:`), 119,355 B, LF (0 CR), 0 bytes > 127, 2,416 lines. Its first 101,070 bytes hash to `1e8e28aeff8c7fbc9fc9bcf67e0a765ed151ad1f87b8cd9508da38ac54894e0a` (= `git show 83daa8cb:` the frozen file): a pure append (numstat 340 / 0). 408 nodes (the unit runs). No existing row changed: the F3-3-named row `test_placeholder_llm_name_with_a_usable_llm_full_title` is byte-unchanged and passes on the 83daa8cb service bytes (BASE83 below), so the fix agent's deviation D1 is confirmed.

## 2. Runs (every pytest through pyt.py; my runs one at a time)

```
unit flag unset (worktree): 408 passed, 11 warnings in 14.02s; [hermeticity] sentinel checked 408 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4rv3-unit-off start=2026-10-22 17:12:03 end=2026-10-22 17:12:20 elapsed=16s bound=600s status=OK rc=0
unit ENABLE_URL_MODE_V2=true (worktree): 408 passed, 11 warnings in 9.85s; sentinel 408; netguard 0
[pyt] tag=b4rv3-unit-on start=2026-10-22 17:12:41 end=2026-10-22 17:12:52 elapsed=11s bound=600s status=OK rc=0
mutation control (scratch, unmutated): 408 passed, 11 warnings in 8.41s; sentinel 408; netguard 0
[pyt] tag=b4rv3-mut-control start=2026-10-22 17:14:53 end=2026-10-22 17:15:03 elapsed=10s bound=600s status=OK rc=0
CI-order set (13 files, alphabetical, flag OFF, worktree): 1059 passed, 13 warnings in 25.30s; netguard blocked 10 attempt(s) from 10 node(s), 0 not in the baseline
[pyt] tag=b4rv3-ci-order start=2026-10-22 17:22:14 end=2026-10-22 17:22:40 elapsed=27s bound=1200s status=OK rc=0
comm 00 (worktree, flag OFF): 671 passed, 1 skipped, 2 deselected, 28 warnings in 110.24s; sentinel 672; netguard blocked 29 attempt(s) from 28 node(s), 0 new
[pyt] tag=b4rv3-comm-00 start=2026-10-22 17:28:55 end=2026-10-22 17:30:48 elapsed=113s bound=1200s status=OK rc=0
comm 01: 1249 passed, 5 skipped, 5 deselected, 1 xfailed, 13 warnings, 2 errors in 98.09s; sentinel 1252; netguard blocked 204 attempt(s) from 13 node(s), 0 new
  ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable / ::test_render_digests_match_base_except_the_fence (teardown: getaddrinfo openaipublic.blob.core.windows.net = the brief's cold-tiktoken pair)
[pyt] tag=b4rv3-comm-01 start=2026-10-22 17:30:49 end=2026-10-22 17:32:29 elapsed=100s bound=1200s status=FAIL rc=1
comm 02: 1694 passed, 13 warnings in 83.36s; sentinel 1694; netguard blocked 13 attempt(s) from 7 node(s), 0 new
[pyt] tag=b4rv3-comm-02 start=2026-10-22 17:32:43 end=2026-10-22 17:34:08 elapsed=85s bound=1200s status=OK rc=0
comm 03: 221 passed, 11 warnings in 6.88s; sentinel 221; netguard 0
[pyt] tag=b4rv3-comm-03 start=2026-10-22 17:34:10 end=2026-10-22 17:34:18 elapsed=8s bound=1200s status=OK rc=0
R8 pins ALONE: tests/test_sentry_channels_u8d_unit.py 141 passed; sentinel 141; netguard 0
[pyt] tag=b4rv3-u8d-unit start=2026-10-22 17:35:08 end=2026-10-22 17:35:19 elapsed=11s bound=600s status=OK rc=0
R8 pins ALONE: tests/test_sentry_channels_u8d.py 131 passed; sentinel 131; netguard 0
[pyt] tag=b4rv3-u8d start=2026-10-22 17:35:20 end=2026-10-22 17:35:27 elapsed=7s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag unset: 21 passed, 13 warnings; netguard blocked 2 attempt(s) from 2 node(s) (baseline)
[pyt] tag=b4rv3-meter-off start=2026-10-22 17:35:27 end=2026-10-22 17:35:32 elapsed=4s bound=600s status=OK rc=0
tests/test_paid_route_metering.py flag exported: 21 passed, 13 warnings; netguard the same 2 baseline nodes
[pyt] tag=b4rv3-meter-on start=2026-10-22 17:35:33 end=2026-10-22 17:35:37 elapsed=4s bound=600s status=OK rc=0
tests/test_auth_error_log_hygiene.py ALONE (F2-3): 69 passed, 11 warnings in 3.74s; sentinel 69; netguard 0
[pyt] tag=b4rv3-auth-hygiene start=2026-10-22 17:35:38 end=2026-10-22 17:35:43 elapsed=5s bound=600s status=OK rc=0
limit-16 20-file pin set, flag EXPORTED (worktree): 1037 passed, 13 warnings in 36.04s; netguard 10 nodes, 0 new
[pyt] tag=b4rv3-pins20-flagON start=2026-10-22 17:42:09 end=2026-10-22 17:42:48 elapsed=38s bound=1200s status=OK rc=0
probes (scratch, section 5): 5 passed, 11 warnings in 3.52s; sentinel 5; netguard 0
[pyt] tag=b4rv3-probe start=2026-10-22 18:36:21 end=2026-10-22 18:36:25 elapsed=5s bound=600s status=OK rc=0
hook files (F3-7; scratch worktree, .githooks/pre-commit + .gitleaks.toml + the four hook test files sha-equal to the worktree), all four in ONE call, beside the sibling D03 workflow (no quiet window in 20 min): 213 of 327 nodes done when the bound fired, 210 passed, 3 skipped, 0 failed = the first three files COMPLETE (test_precommit_hook.py 62, _round2 30, _phase_b 114: 203 passed + 3 skipped, collection order = argv order) and 7 of _phase_b_round2's 121
[pyt] tag=b4rv3-hooks start=2026-10-22 18:03:13 end=2026-10-22 18:33:14 elapsed=1801s bound=1800s status=TIMEOUT rc=124
TIMEOUT-rule re-run, launched 18:36:39 with no other pytest on the box (hooks2_pre.txt); D03 started d03g-comm-head-01 at 18:36:45; after 18 nodes (test_precommit_hook.py again, already measured) I stopped MY tree (taskkill /T on PID 5856 = pyt.py --tag b4rv3-hooks-rerun, command line read first; no [pyt] line) and re-ran only the one unmeasured file in its own call (the brief lets the hook files be split across runner calls):
tests/test_precommit_hook_phase_b_round2.py ALONE in its call (D03's d03g-comm-head-05 was running at launch, hooks3_pre.txt): 121 passed, 4 warnings in 930.00s; [hermeticity] sentinel checked 121 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4rv3-hooks-pbr2 start=2026-10-22 18:45:45 end=2026-10-22 19:01:16 elapsed=931s bound=1800s status=OK rc=0
```
Hook files on the final bytes, combined: 324 passed + 3 skipped = 327 nodes, 0 failed (= the fix agent's 324 / 3 at 16:53). The unit touches no `.githooks` / `.gitleaks.toml`.

The comm set is the fix agent's 78-file union (`B4_fix3/comm_chunk_00..03`), re-run here on the HEAD bytes; the CLAUDE.md readers (`test_ci_gates.py`, `test_behavior_dimension_translation.py`) and every F2-3 source-scanning pin (incl. `test_auth_error_log_hygiene.py`) are in chunks 00-02. `comm -13 base head` is empty: the head failure set is exactly the two cold-tiktoken teardown ERRORs (the brief's known environmental pair, also the fix-round-2 base set); the base was not re-run (it cannot add a branch-only failure to an empty set).

Comm-set re-derivation (mine, scratch tree): the module / symbol reference grep (`url_extraction_service|normalize_url_for_same_check|classify_url_path|_product_route_pairs|_query_names_a_product_route|_extract_from_url_v2|extract_from_url|is_usable_title|_PRODUCT_ROUTE_QUERY_KEYS|_SAME_URL_PRODUCT_QUERY_KEYS|_OPENCART_PRODUCT_ROUTE|url_routes|compare_from_urls|/api/v1/url`: 28 files) is inside the union; every test that walks or globs (`os.walk|rglob|glob.glob|.glob(`: 32 files) is inside the union; the only tests that read `CLAUDE.md` by name are the two readers. A broader `"app/"`-string grep adds 34 files, each reading a SPECIFIC other app file (auth_routes, structured_comparison_service, usage_service, config.py, ...) or naming CLAUDE.md in a comment; none reads `url_extraction_service.py` or walks `app/`, so none can see this round's edit. No edited test-support module this round. No missed member (the MAJOR-E2 class is not reopened).

Concurrency (the brief: one pytest at a time; another workflow may share the box): my own runs never overlapped each other, but the runner ledger shows the sibling D03 workflow (`d03red-*`, `d03rev-*`) running pytest during several of mine (e.g. `d03red-p1probe` 17:23:17-17:23:21 and `d03red-scratch-base1` 17:24:00-17:24:10 inside `b4rv3-OFFID`, `d03red-proto-*` 17:31-17:33 inside `b4rv3-comm-01/02`, and its M1..M50 mutants 17:36-17:41 plus later gates during my hook wait). Every overlapped run of mine passed (no TIMEOUT), so the overlap changes timing only. For the hook files I waited for a 120 s quiet window (`quiet.ps1`, 20 min max): the box was never quiet (`BUSY-TIMEOUT at 18:03:12`), so the first hook call ran beside D03 and hit the bound; the TIMEOUT-rule re-run was launched at 18:36:39 with no other pytest on the box (process list `hooks2_pre.txt`).

Lint (worktree, read-only): `ruff 0.16.5 check --select E9,F63,F7,F82 --no-cache` on the service, url_routes and the RED file: `All checks passed!`; `compile()` of the service and the RED file: OK (no bytecode written). Full-rule ruff on the service: 57 (W293 56, F401 1), unchanged from 83daa8cb (the fix report's claim). Hygiene (83daa8cb..HEAD, 3 files, `hygiene.py`): service CRLF 1395/1395, 18 bytes > 127 at head and in the 83daa8cb blob; CLAUDE.md CRLF 938/938, 3979/3979; RED file LF, 0; 392 added lines: 0 non-ASCII, 0 @gmail, 0 +973, 0 8+-digit runs, 0 sk-/AKIA/xox/eyJ/credentialed-URL/PEM. `git diff --name-only 81df2b64..HEAD -- .githooks .gitleaks.toml`: empty (the unit touches no hook file).

## 3. Mutation table (scratch worktree; `B4_fix3_rv/mutate.py`: lock `.qa-mutation.lock` -> byte copy -> exact edit matching ONCE (CRLF-adapted) -> pyt.py bound 600 over the full unit file, every ENABLE_* unset, PYTHONDONTWRITEBYTECODE=1 -> restore from the byte copy -> sha256 compare, abort on mismatch (none; every restore `b0d7b8d9...`) -> lock removed; results `mut_results.jsonl`, logs `mut_<id>.log`; the kill class is read from pytest's traceback location lines)

Every mutant below is my own re-write (independent of the fix agent's `mutate3.py`). KILLED = rc 1 with every location line `AssertionError`.

| id | fix | mutant | result | failing nodes | [pyt] |
|---|---|---|---|---|---|
| BASE83 | RED proof | the whole service file at `83daa8cb` | 50 failed = exactly the 50 RED rows (10+4 F3-1, 10+2+10+5 F3-2, 5 F3-4, 4 F3-3), 50 AssertionError; 358 passed (the 23 new PINs + all 335 old rows) | 50 | tag=b4rv3-BASE83_service_at_83daa8cb start=17:15:23 end=17:15:36 elapsed=13s status=FAIL rc=1 |
| K1 | F3-1 | the key drops the query again (`return key`) | KILLED | 14 | tag=b4rv3-K1_key_drops_query 17:15:36-17:15:47 elapsed=12s FAIL rc=1 |
| K2 | F3-1 | a blanket key: the whole raw query kept | KILLED (frozen R3 query-fragment rows, `test_normalize_url_table`, the tracking / pid PINs) | 16 | tag=b4rv3-K2_key_whole_query 17:15:48-17:16:01 elapsed=14s FAIL rc=1 |
| K3 | F3-1 | `products_id` out of the same-url keys | KILLED (oscommerce route rows x2 + key row) | 3 | tag=b4rv3-K3_no_products_id_in_key 17:16:02-17:16:15 elapsed=14s FAIL rc=1 |
| K4 | F3-1 | `pid` added to the same-url keys | KILLED (aspnet-pid PIN x2, pid-not-a-key) | 3 | tag=b4rv3-K4_pid_in_key 17:16:16-17:16:30 elapsed=15s FAIL rc=1 |
| K5 | F3-1/F3-4 | values not stripped | KILLED (value-stripped, `/?product=%20`) | 2 | tag=b4rv3-K5_values_not_stripped 17:16:31-17:16:43 elapsed=12s FAIL rc=1 |
| K6 | F3-1/F3-4 | keys case-sensitive | KILLED | 4 | tag=b4rv3-K6_keys_case_sensitive 17:16:43-17:16:55 elapsed=12s FAIL rc=1 |
| K7 | F3-1 | order-sensitive key (`list(dict.fromkeys(pairs))`) | KILLED (order row) | 1 | tag=b4rv3-K7_key_order_sensitive 17:17:57-17:18:08 elapsed=11s FAIL rc=1 |
| K8 | F3-1/F3-2 | the raw route value kept in the key | KILLED (route-value-case row) | 1 | tag=b4rv3-K8_route_raw_value_in_key 17:18:08-17:18:18 elapsed=10s FAIL rc=1 |
| R1 | F3-2 | F3-2 reverted (`v.startswith("product/")`, case-sensitive) | KILLED | 29 | tag=b4rv3-R1_route_startswith_product 17:18:18-17:18:31 elapsed=13s FAIL rc=1 |
| R2 | F3-2 | route value case-sensitive | KILLED | 3 | tag=b4rv3-R2_route_value_case_sensitive 17:18:32-17:18:42 elapsed=10s FAIL rc=1 |
| R3 | F3-2 | any non-empty route value is a marker | KILLED (incl. the frozen `route=common/home` row) | 27 | tag=b4rv3-R3_any_route_value 17:18:42-17:18:54 elapsed=12s FAIL rc=1 |
| X4 | F3-4 / F3-5 | an empty value counts (`elif k in keys:`) | KILLED | 6 | tag=b4rv3-X4_empty_value_counts 17:18:55-17:19:05 elapsed=11s FAIL rc=1 |
| T1 | F3-3 | F3-3 reverted (first TRUTHY title) | KILLED (4 F3-3 rows) | 4 | tag=b4rv3-T1_first_truthy_title 17:19:06-17:19:16 elapsed=11s FAIL rc=1 |
| T2 | F3-3 | the unusable title not cleared | KILLED | 4 | tag=b4rv3-T2_unusable_title_not_cleared 17:19:42-17:19:55 elapsed=13s FAIL rc=1 |
| E1b | F3-5 | title window unbounded (`window = html`) | KILLED | 1 | tag=b4rv3-E1b_title_window_unbounded 17:20:05-17:20:18 elapsed=13s FAIL rc=1 |
| F5e | F3-5 | node-name usability without the site names | KILLED | 1 | tag=b4rv3-F5e_node_name_ignores_site_names 17:20:18-17:20:29 elapsed=10s FAIL rc=1 |
| X1 | F3-5 | `exc_info=True` on the transport ERROR line | KILLED | 1 | tag=b4rv3-X1_transport_error_exc_info 17:20:29-17:20:40 elapsed=11s FAIL rc=1 |
| X5 | F3-5 | a 401 as `http_403` | KILLED | 1 | tag=b4rv3-X5_401_as_http_403 17:20:40-17:20:52 elapsed=12s FAIL rc=1 |
| T3 | F3-3 | candidate order swapped (full_title first) | SURVIVED: EQUIVALENT (the local `title` is only None-checked; the shipped title is decided by the clearing line + `normalize_product_data`) | 0 | tag=b4rv3-T3_candidate_order_swapped 17:19:55-17:20:05 elapsed=9s OK rc=0 |
| I1 | info | `classify_url_path` takes `products_id` too | SURVIVED (a root `/?products_id=N` link: homepage at HEAD per the F3-1 "key only" text, unpinned) | 0 | tag=b4rv3-I1_classify_takes_products_id 17:20:52-17:21:02 elapsed=10s OK rc=0 |
| I2 | info | key not de-duplicated | SURVIVED (only `?product_id=1&product_id=1` vs `?product_id=1` differ; contrived) | 0 | tag=b4rv3-I2_key_not_deduplicated 17:21:03-17:21:13 elapsed=10s OK rc=0 |
| I3 | info | the route marker dropped from the key | SURVIVED (`?route=product/product&product_id=1` vs `?product_id=1`: different keys at HEAD, fetched; equal under I3; unpinned) | 0 | tag=b4rv3-I3_key_drops_route_marker 17:21:13-17:21:24 elapsed=11s OK rc=0 |
| OFFID | flag OFF | every round-3 hunk raises when reached (`_product_route_pairs` entry + the F3-3 site), run over the whole 13-file CI-order set | 255 failed, ALL in the unit file and all flag-ON rows (134 AssertionError + 121 RuntimeError B4RV3_OFF_PROBE); 804 passed incl. EVERY other CI-order file (651 nodes) and every unit flag-OFF row (`test_flag_off_*`, `test_w4_13_rows_*_flag_off`, `test_prompt_off_render_equals_w411_digest`) | 255 | tag=b4rv3-OFFID_round3_hunks_raise 17:23:18-17:24:12 elapsed=54s bound=1200s FAIL rc=1 |

Counts: 23 mutants applied (one or more per fix: F3-1 x7, F3-2 x3 (+K8), F3-3 x3, F3-4 x1 (+K5, K6), the five F3-5 mutants E1b / F5e / X1 / X4 / X5), 19 KILLED (AssertionError only), 1 equivalent (T3), 3 information survivors (I1, I2, I3: unpinned shapes, behaviour per the rulings at HEAD), plus the BASE83 RED proof and the OFFID reachability probe. Flag-OFF identity of this round is proven by OFFID (no flag-OFF path in 14 files reaches a round-3 hunk) on top of the unchanged OFF rows; `grep` of app/: `normalize_url_for_same_check` is called only at `url_routes.py:119-120` inside `_url_pre_gate`, which both handlers call only under `if v2:` (:448-449, :483-484); `classify_url_path` only there and in `_extract_from_url_v2` (:1011), reached only through `extract_from_url(url_mode_v2=True)`.

## 4. Fix-round-3 hunks against the rulings (code read at HEAD)

- F3-1 (`normalize_url_for_same_check` :137-160, `_SAME_URL_PRODUCT_QUERY_KEYS` :190, `_product_route_pairs` :196-212): the base key unchanged; `?` + `urlencode(sorted(set(pairs)))` appended only when a marker is present; markers = `route` with value exactly `product/product` (lower-cased compare, canonical value stored) and `product_id` / `id_product` / `product` / `products_id` with a non-empty stripped value; keys lower-cased; values percent-decoded by `parse_qs` (Python 3.12.9, `&` separator only); `pid` absent; no blanket query rule. Matches F3-1 / F3-2 / F3-4 literally.
- F3-2 / F3-4 at both F2-1 sites: `_query_names_a_product_route` (:215-218) is `bool(_product_route_pairs(query, _PRODUCT_ROUTE_QUERY_KEYS))`; `classify_url_path` (:238) serves the pre-gate and the post-fetch final-url check (:1011). Matches.
- F3-3 (`_extract_from_url_v2` :1050-1058): `title = next(first is_usable_title of (title, full_title))`; None -> `null_name`; an unusable `raw_data["title"]` is cleared so `normalize_product_data` (:1150, `title or full_title`) ships the usable one; F2-5's name rule follows unchanged. A case delivered before is delivered identically (the clearing only fires when the old code refused or the raw title was already falsy); `extraction_method` is `ai` for the newly delivered case (the title came from the LLM). Matches F3-3.
- No log line, envelope key, copy constant, prompt or metering change this round (diff read in full).

## 5. Probes (scratch; `B4_fix3_rv/test_zz_b4rv3_probe.py`, copied in, run, deleted; output `probe.jsonl`)

1. Same-url key edges: `?product_id=1&gclid` class (pinned) equal; `?product=oud+a` vs `%20a` equal (both decode to a space); `id_product=1&id_product_attribute=5` vs `=6` equal -> through the real route flag ON `400 NOT_PRODUCT_PAGE same_url`, 0 fetches, flag OFF 200 (two PrestaShop combinations of ONE product: the F2-6 c "two size / variant links of ONE product" class; the row names only `?variant=` / `?attribute_pa_size=` as examples); OC4 `language=en-gb` vs `ar` of one product equal; `route=product/product&product_id=1` vs `?product_id=1` (one product) differ -> both fetched, 200 ON and OFF (I3 shape; cost only); an HTML-entity `&amp;product_id=` same-store pair equal (`amp;product_id` is not a key: refused `same_url`; at OFF the store would not see a `product_id` either); `%FE` vs `%FF` values collapse to U+FFFD and are equal (contrived); Arabic slugs differ. A 258 KB query with 20,001 keys: key 17 ms, classify 16 ms (linear).
2. `classify_url_path`: `/?products_id=5` homepage (I1 / D3), `/index.php?route=product/category&product_id=5` None (exempt through `product_id`: see minor m4), `/index.php?route=product/product` None, `/?route=product/product%20` None, `/?route=product%2Fproduct` None, `/index.php?route=product/product.review&product_id=4` None, `/?Product=a` None, `/?p=12` homepage, `/?pid=1` homepage, `/index.php?route=product/product&product_id=%20` None (the exact route alone is a marker).
3. Real route, flag ON, full configuration: a WooCommerce same-store pair with a mixed-case key (`?Product=b4-a` vs `?product=b4-b`) -> 200, both names, 2 fetches. (The flag-OFF twin hit the route's 10/minute limiter inside my probe, 429 RATE_LIMITED: a probe artifact, not a finding.)
4. F3-3 scope edge: a Product node named `Unknown`, an empty `<title>`, no price, the LLM answering a usable `name` and `full_title: null`: flag ON `UNRESOLVED_PRODUCT null_name` after 1 LLM call; flag OFF delivers `name` "Hawas Ice" with `full_name` "Unknown". Per B4-R1 (null_name exactly when the page title is unusable) and F3-3's literal candidate set (title, full_title), this is ruled behaviour; recorded as information i4 below.

## 6. Findings

### MAJOR

None.

### minor

- m1 (PR body, evidence accuracy). Line 42 states the fix-round-3 RED file's "new frozen sha256 `b6753884cd18a93f7d3e00fd8f348bce17e4bfae5aa5358faf30d7aa3770238a` (408 nodes, 119,199 bytes ...)". That is the INTERMEDIATE file of the RED step (fix report: `1e8e28ae` -> `b6753884` -> `c10c15c3` -> `bac87301`); the committed and frozen file is `bac8730196c75769e672646e6f1dee7901bfb3fb275af1d84af6a9d97517f1d9`, 119,355 bytes (section 1). The body's own gates section (line 90) carries the right value, so the body contradicts itself on the one sha the next round re-hashes. Fix: replace the sha and size on line 42.
- m2 (PR body + fix report, F3-7 claim). "The four `tests/test_precommit_hook*.py` files ran ALONE (no other pytest on the box)" (lines 80, 125): the runner ledger shows `d03rev-probe1` (2026-10-22 16:45:56-16:46:11) inside the fix agent's `b4f3-hooks` window (16:27:37-16:53:03). The process list was read only before the launch. The run ended OK (324 passed, 3 skipped), so the measurement stands; the sentence overclaims. Fix: "no other pytest at launch; one 15 s sibling run overlapped".
- m3 (PR body, X1 sentence). Line 78: "`exc_info`, `exc_text` and `stack_info` are None on the one ERROR record and on every other record of the run": the row (`test_transport_error_line_carries_no_exception_info`) asserts all three on the ERROR record but only `exc_info` (falsy) on the other records. Fix: "... on the ERROR record; no record of the run carries exc_info". (The CLAUDE.md row's wording, "the transport ERROR record carries no exception or stack info", is accurate.)
- m4 (CLAUDE.md row limit (1) + effect clause, PR body stated limits). "an OpenCart `route=product/product` only, so an OpenCart listing route on a root or /index.* path ... is refused at $0 as a homepage" is true only when the listing link carries no other marker: `/index.php?route=product/category&product_id=5` is exempt through its `product_id` (probe 2; the fix report's open question 3). Fix: add "unless it also carries a non-empty product_id / id_product / product".
- m5 (pin gaps on ruled shapes, behaviour correct at HEAD; information-grade): I1 (the homepage-class allow-list excludes `products_id`, F3-1 "key only") and I3 (the `route=product/product` pair is part of the same-url key, F3-1 text) both survive the 408 rows. Neither changes a delivered result for a realistic pair (I1: a root `/?products_id=N` osCommerce link is rare, the PDP is `product_info.php`; I3: one product with and without the route marker). A PIN each would freeze the ruled reading.

### information (no action required unless the gate wants it)

- i1 X5 deviation (fix report D2): F3-5 asks for "reason http_401"; no such word exists (GC-3 vocabulary; `_v2_status_reason` :948-958 maps every 4xx but 403 to `http_4xx`), so a PIN asserting it could not pass at 83daa8cb. The PIN asserts `http_4xx` and kills X5. Accept, or rule a per-status word (a vocabulary change).
- i2 F3-3 named row (fix report D1): confirmed: the named row uses a NAMELESS node and passes on the 83daa8cb bytes; the placeholder-NAMED defect is the new RED row (fails at 83daa8cb, killed T1 / T2).
- i3 PrestaShop combination links of one product (`id_product_attribute`) are refused `same_url` flag ON (probe 1); the same class as the stated F2-6 c limit; the row could name it as an example.
- i4 F3-3 scope: the LLM's `name` is not a title candidate (probe 4); ruled by B4-R1 + F3-3's literal set; a follow-up could add it as a third candidate.
- i5 CLAUDE.md header nit (pre-existing, not this round): "`specs/GATE_B4.md` fix-round rulings" lacks a separator.

## 7. Step-6 categories (synack-build-orchestrator rubric, this round's diff only)

- Security: none found. The round adds no log line, no network call, no new input surface; `parse_qs` over a 258 KB query is 17 ms (linear); keys are rebuilt with `urlencode` (no raw user text in the key); no credential-shaped literal (sweep).
- Performance: none (two `parse_qs` passes per link in the flagged pre-gate; measured above).
- Complexity: none blocking; `_product_route_pairs` serves both sites and the key (one helper, the smallest shape). The local `title` in `_extract_from_url_v2` is only None-checked (T3 equivalent): a reader could misread it as the shipped title (low).
- Dead code: none added; the old `_query_names_a_product_route` body is replaced, not left behind.

## 8. Round-2 items: closure

| item | status | evidence |
|---|---|---|
| MAJOR-R1 (same-store query-routed pairs refused same_url) | CLOSED | 10 route RED rows (OpenCart index + root, PrestaShop, WooCommerce, osCommerce x POST/GET) + 4 key RED rows fail on the 83daa8cb bytes (BASE83) and pass at HEAD; K1 / K3 killed; the guard PINs (tracking-only, `?pid=`, identical) kill K2 / K4; ASP.NET `?pid=` recorded as the ruled stated limit (limits 1 and 11) |
| m1 citation (limit 11 / PR stated limits) | CLOSED | limit (11) cites F3-1 with the measured class; F2-6 c now covers variants only |
| m2 listing routes | CLOSED | exact `product/product` at both sites and in the key; R1 / R3 killed; 10 + 10 + 5 rows; residual wording m4 |
| m3 first usable title | CLOSED | T1 / T2 killed; 4 RED rows; scope note i4 |
| m4 PR F2-1 sentence + canary | CLOSED | PR lines 65 and 146, row canary: two DIFFERENT stores AND one same-store OpenCart pair -> 200 |
| m5 pin gaps E1b / F5e / X1 / X5 | CLOSED | all four killed by the new PINs (X5 as `http_4xx`, i1) |
| m6 X4 / case | CLOSED | X4 killed (empty value), K6 / R2 killed (key and route-value case) |
| m7 WARNING list | CLOSED | row and PR: "a blocked initial url or a blocked hop" (code: `_fetch_page_v2` logs `_log_fetch_failed(url, "blocked", None)` on both branches) |
| m8 Sentry cause | CLOSED | `sentry_service.py:651` = `LoggingIntegration(level=logging.ERROR)`; sentry-sdk 2.68.1 (venv METADATA) `integrations/logging.py`: `DEFAULT_EVENT_LEVEL = logging.ERROR`, `event_level` default; the row and PR text match |
| m9 hook files NOT MEASURED | CLOSED | the fix agent's one call OK (324 passed, 3 skipped, 1526 s; see m2 on "ALONE"); here on the final bytes: three files complete inside the TIMEOUT'd call + `_phase_b_round2` 121 passed in its own call = 327 nodes, 0 failed (section 2) |
| round-2 adversary items (M1, E1, E2 and their minors) | stay CLOSED / RECORDED (B4_FIX2_REVERIFY section 6); their rows are among the 408 green in both flag states; E2's member `test_auth_error_log_hygiene.py` green alone and in comm 00 |

## 9. CLAUDE.md row and PR body against the bytes

Row (lines 474-475, 17,054 B after CR strip; word diff vs 83daa8cb read in full) checked sentence by sentence: TRUE: the header citations (F3-1..F3-7 added); the effect clause's exact-route marker, non-empty values, case-insensitive keys, and the same-url key's kept keys (code :137-218); "first 64 KiB only (pinned F3-5)" (E1b row); "a 401 is http_4xx, pinned F3-5" (X5 row; `_v2_status_reason`); the F3-3 sentence; the WARNING list incl. the blocked INITIAL url (m7); "the transport ERROR record carries no exception or stack info, pinned F3-5" (X1 row); the Sentry cause and `sentry_service.py:651` (m8); the flag-OFF clause (no new OFF delta: OFFID); limit (1) (except m4); limit (11) (the measured class; `?pid=` and variant links still same_url; pinned); limit (16) (408 / 21 / 1037 re-measured here with the flag exported on the HEAD bytes); the canary (two DIFFERENT stores AND one same-store OpenCart pair). IMPRECISE: m4.

PR body (`ddb74874...`) checked sentence by sentence: TRUE: the header and commit list; the ON / OFF / UNFLAGGED / Build 3 paragraphs (incl. "every fix-round-3 change ... reached only through the flagged path", proven by OFFID); the defect table's fix-round-3 node counts (counted from the parametrisations in the file, and for the RED rows from the BASE83 failure list per function: 10, 4, 10, 2, 10, 5, 5, 4; PINs 6, 9, 2, 2 and the four singles; the file total 408 = the unit runs); E1..E6 table (unchanged files this round: `git diff 83daa8cb..HEAD` touches only the service, the RED file and CLAUDE.md); fix round 3 F3-1..F3-6 bullets (F3-1 route outcome "200 with both names, 2 fetches and 1 consume" = the row's assertions; F3-2 "route=PRODUCT/PRODUCT alone ... a homepage at 83daa8cb" = BASE83); the deviations (X5 word, F3-3 row, products_id key-only, whitespace-only value); the RED-step [pyt] lines and every other fix-agent [pyt] line (all present in `harness/pyt_ledger.jsonl` with the same tag, start, end, status and summary); the RED arithmetic (50 = 10+4+10+2+10+5+5+4); the CI-order, comm, metering, u8d, readers and lint figures (re-measured here where named in section 2); the mutation paragraph's per-mutant counts (= the ledger summaries). NOT TRUE / imprecise: m1 (line 42 sha and size), m2 (lines 80 / 125 "ALONE"), m3 (line 78 X1 sentence), m4 (line 140 listing-route clause).

## 10. Questions for the gate

1. m1-m4: fix the four sentences now (docs only; the CLAUDE.md row edit needs the two CLAUDE.md readers re-run) or at the GC-7 rebase?
2. i1: accept `http_4xx` for a 401 (the PIN as written) or rule a per-status word?
3. m5 / I1, I3: add the two PINs (root `/?products_id=N` stays homepage; the route marker is part of the key) or accept as unpinned ruled shapes?

## 11. NOT MEASURED

- A single uninterrupted all-four-files hook call on a quiet box (the box was never quiet: section 2; the split measurement covers all 327 nodes).
- Base (83daa8cb) re-run of the 4 comm chunks (head failure set = the known cold-tiktoken pair only, so `comm -13` cannot be non-empty); the unit file itself was run on the 83daa8cb service bytes (BASE83).
- Live store / Sentry / Railway behaviour (rules); every store shape is a synthetic page through the real route.
- The post-rebase run (GC-7) and both adversaries on this HEAD (the orchestrator, per RULINGS_FIX3_B4).

## 12. End state

- Worktree `sc-s80-b4`: HEAD `0aac07f1f7304e61fa5cac86935c9306f08605d0`, `git status --short` empty, no `.qa-mutation.lock`, never edited. Final sha256 (bytes on disk): RED `bac8730196c75769e672646e6f1dee7901bfb3fb275af1d84af6a9d97517f1d9`, url_extraction_service `b0d7b8d96aec34352dccdf008d29ddb60fdd03779cb28cc19cfddcf29cc49f68`, url_routes `9229e0b4d027e392f21e5da9edb29549f40fcde2bb22ca90c4351701ab3a59ba`, error_handler `7e539cc7b17fcc6c9b982a2ebe4b212096af57deb8c1bded330eb57e5fc6d482`, CLAUDE.md `c4af580314acbf212b0368d87d6ed5648bc1a66712edde79db6f508b739bd1e6`, test_paid_route_metering `4724c308c6a5805a873a015f2a07e02850e8db5c020f46423e71208505ead73f`.
- Scratch worktree `<scratchpad>/B4_fix3_adv`: sha-equal to the worktree after the last restore (15/15), no lock left, probe file deleted; removed with `git worktree remove --force` (no node_modules in it); `git worktree list` no longer shows it. No pytest of mine left running (process list).
- Deviations: (1) the hook re-run was split (section 2) after the sibling workflow kept the box busy; (2) my runs overlapped D03 runs (ledger, section 2), none of mine timed out except the first hook call; (3) the 90-minute budget was exceeded (start 17:05, end ~19:05) to finish the TIMEOUT-rule hook re-run; (4) a throwaway empty file `/tmp/x1` was created by a redirect and deleted at once; every kept file is in the notes folder; (5) the first batch's `killed` flags in `mut_results.jsonl` were computed with a summary-line parser that missed the class; the table above is re-derived from the logs' location lines (`mutate.py --reclass`, `mut_table.md`).
- Files written (all under `<scratchpad>/B4_fix3_rv/` except this report): notes.md, shacheck.py, mutate.py, mut_results.jsonl, mut_table.md, mut_*.log, bak/ (byte copies), hygiene.py, pyproc.ps1, quiet.ps1, quiet.out, test_zz_b4rv3_probe.py, probe.jsonl, probe.log, unit_off.log, unit_on.log, ci_order.log, ci_ng_nodes.txt, comm_00..03.log, comm_02.out, comm_03.out, ng_*.txt, b4rv3-*.log/.out (u8d, meter, auth hygiene), pins20_on.log/.out, hooks.log/.out, hooks2.log/.out, hooks2_pre.txt, hooks3.log/.out, hooks3_pre.txt, hooks_wt.txt, hooks_adv.txt, claude_row.txt, claude_row_split.txt, my_ref.txt, my_walk.txt, my_union.txt, walkers.txt, extra34.txt, offid_failed_funcs.txt; this report `<scratchpad>/B4_fix3/REVERIFY_REPORT.md`.
