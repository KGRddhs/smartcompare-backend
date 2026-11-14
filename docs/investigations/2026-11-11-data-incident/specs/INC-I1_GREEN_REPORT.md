# INC-I1 PICTURE-MUST-MATCH: GREEN report (GREEN round; Opus 5.5 GREEN agent of the S95-FIX lane; 2026-11-14)

- Unit: INC-I1 PICTURE-MUST-MATCH; flag `ENABLE_IMAGE_RELEVANCE_GUARD` (new, default OFF, read per call), knob `IMAGE_RELEVANCE_CANDIDATES` (5, clamped 1..10). Class SAFE (GC-12 / I1-R9): one adversary next.
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-inc-i1`; branch `fix/inc-i1-picture-must-match` created with `git checkout -b` at the base `731bcddf531a7e123963246168ca19f262859337` (the one branch command; no stash, reset, rebase, merge or clean). HEAD after the one commit: `5cf13f622394f4f9133b46b026dc77376b0038b1`. Not pushed; no PR opened.
- Inputs read in full: the common brief (H0-H12 + the session-81 rules), PLAN_S81 (context, standing constraints, the VERIFY corrections incl. Images), RULINGS_INC_R0, RULINGS_INC_I1 (I1-R1..I1-R21), GATE_INC_I1 (GC-1..GC-14, binding), the spec (sha256 5539e844..., read from the byte-equal parts `<SP>/INC-I1/spec/part1..4.txt`), the review (sha256 5b1df569..., from `<SP>/filed/i1/`), the RED report and its prototype diff + leaf (a reference only; this leaf and these edits are written anew).
- Every pytest ran through `<SP>/harness/gate.py` (the runner was never called; nothing waited inside a runner); one pytest at a time; the comm chunks and the gate sets by ONE sequential driver (`seqrun.py`, a byte copy of the RED round's, which calls gate.py per job). Notes: `<SP>/INC-I1_green/notes.md`.
- Production flag state used (names only): H12 (c): `ENABLE_DATA_GUARDS_V2`, `ENABLE_IMAGE_PIPELINE_V2`, `ENABLE_KB_FIRST_SERVE` OFF on web; `ENABLE_IMAGE_RELEVANCE_GUARD` is a new, unset name.

## 0. Files (one commit; bytes on disk, the edited files keep CRLF, the new leaf is LF)

| path | sha256 before | sha256 after | numstat +/- |
|---|---|---|---|
| app/services/image_relevance.py | (new) | 5c6508fd36ac3f97a6c360dda7c96b7ef55ec571570a82411ad2abc4c227b626 | +569 / -0 |
| app/services/image_service.py | c4d7492f358417889663d0983aa4782042c39cfbfa7ff63e213dfb1e0bcb69f8 | defc99d109d1aee513e09574eb6174afa10ba19c3741c3b9d0d3f4b5e9c6fd4d | +128 / -6 |
| app/services/structured_comparison_service.py | 08bf1120d7e0ca08c034a68877098cf2d9f9494d9ffec7f2ea64ac7b04a0c1ef | de8c77ce164620d6e9de376edb47ce27f30a884fb7e2e05e65efee61ccb23bc1 | +15 / -0 |
| app/services/noon_service.py | 2ae3e23a8f1754d19dfa6e7d75425f302fb5ed91ae18bb62b12eb3cd680d31e9 | c41eb9654400e5ff1b78debf45b33f07f72bf1e36afe4c2a665df32374f01a5e | +10 / -0 |
| CLAUDE.md | a0788e541ca1673aa43380e4423ad15ee925281e8c221a4d18d428eb6ffd047d | 45724a6f91c170323202d7b89cee8ec683b8236b1c2fb5d42735d8dde161943e | +7 / -2 |
| .github/black-clean-paths.txt | cd12403ba4eeeb0351525c7afdac3d8d05f118fc661d453424920df90d0fc71a | a56c73324451137b3671dd58397cd28984fd008139dc643c5b2791b9f9a53908 | +3 / -0 |
| tests/test_inc_i1_picture_must_match.py | (new) | e34614401f70599fdbd83da477b2cb19268863dee49b3a416eed4a77f9f5a08f | +1529 / -0 |
| tests/test_inc_i1_noon_and_wiring.py | (new) | 96153bd679ca30ee37d0232b90df9ec0f86b48be02089a2270663836a148dfb0 | +489 / -0 |

Byte copies of the five edited files (before any edit): `<SP>/INC-I1_green_before/` with `before_shas.json`. High-byte counts of the edited files are unchanged (img 72, scs 2876, noon 186, CLAUDE.md 3904, black list 15): every added line is ASCII; no bare LF entered a CRLF file (`apply_green.py` asserts both).

## 1. The frozen RED files

- At the start (22:07): `e34614401f70599fdbd83da477b2cb19268863dee49b3a416eed4a77f9f5a08f` (A, 50,539 B) and `96153bd679ca30ee37d0232b90df9ec0f86b48be02089a2270663836a148dfb0` (B, 17,086 B): equal to GC-1. Never edited.
- At the end: re-hashed after the commit and before the jest fences: tests/test_inc_i1_picture_must_match.py e34614401f70599fdbd83da477b2cb19268863dee49b3a416eed4a77f9f5a08f (equal to GC-1); tests/test_inc_i1_noon_and_wiring.py 96153bd679ca30ee37d0232b90df9ec0f86b48be02089a2270663836a148dfb0 (equal to GC-1); both equal, never edited.

## 2. What was built (the spec change list as amended by the review, the rulings and the gate)

- NEW `app/services/image_relevance.py` (a leaf; black 26.5.1 clean; pure ASCII; module level: the stdlib, `category_gate` (the tokenizer `normalize`), `jsonld_widen` (`allowed_image_url`, `RASTER_EXTENSIONS`), `deny_hosts` (the flag-free `is_denied_url` / `is_denied_source` and the one registrable-label rule `_registrable_label`); `price_service._BRAND_ALIAS_GROUPS` / `_jsonld_image_urls` only inside `alias_groups()` / `first_https_raster()`; no logger, no I/O, no host literal; every function total). Public seams (GC-6): `guard_enabled`, `candidates_knob` (I1-R7 clamp), `alias_groups` + `EXTRA_ALIAS_GROUPS` (I1-R18), `identity` (I1-R3 every token for an empty brand, I1-R4 (b) subset alias rule, (c) number + unit, the placeholder brands, I1-R2 + GC-5 Q-3 the fragrance-word categories), `check(ident, texts, hosts, fragrance_texts=())` (I1-R4 (a) registrable host labels for the brand only; I1-R5 the KG type for the fragrance word only; GC-5 Q-2 an empty line token set = name), `image_query`, `first_https_raster`, `relevance_kwargs` (flag first, then the camera exclusion), `RelevanceCall` (`accept`, `accept_scheme`, `organic_passes`, `accept_pick`, `summary`; the deny FIRST per GC-5 Q-5, then https, then the text test; Tier 3: deny, https + raster path, never an organic link (GC-5 Q-1: reason scheme), a passing related item of `organic[:10]` (I1-R20), else the empty-text reason or the first related item's reason).
- `app/services/image_service.py`: the leaf import by module attribute; four helpers after `_log_img_tier` (`_first_image` https preference, `_extract_relevant_image_from_search` KG / organic[:20] / images[:20] in the base precedence, `_relevant_serper_image` the walk of images[:knob], `_log_img_relevance` the one INFO line); `get_product_image_url(..., relevance=None)` (keyword-only, last) + its docstring line; the guard setup after the empty-name return (`relevance is not None and _relevance.guard_enabled()`, spec 2.3); the piggyback condition (https + deny), Tier 1.5b (the guarded extractor), Tier 1 (`<name> perfume` / knob results under the guard; the base `images[0]` block becomes the `elif` of the guarded walk), Tier 3 (the precondition and the pick check); a `finally` that logs the one `[IMG_RELEVANCE]` line (no await). Untouched: `_is_valid_image_url`, `extract_image_from_search`, `extract_image_via_gpt`, `_TIER3_PROMPT`, the X2a bookkeeping and the CancelledError arm.
- `app/services/structured_comparison_service.py`: the leaf import (module attribute); `**_image_relevance.relevance_kwargs(brand, name, category, partial_slot, is_vision)` as the last argument of the cascade call in the image task (inside the KB conditional's else branch, so it is evaluated only when the cascade runs); the I1-R14 condition right after `page_img = ...` in the price-page override: `if _image_relevance.guard_enabled() and not is_vision and not (isinstance(page_img, str) and page_img.strip().startswith("https://")): page_img = None` (flag read first; text products only, GC-5 Q-4). No other scs line.
- `app/services/noon_service.py`: the leaf import; before `return price` in `_confirm_pdp`: under the flag `price["image_url"] = first_https_raster(product.get("image"))` when one passes. No log line; flag OFF never reads `product["image"]`.
- `CLAUDE.md` (CRLF kept): the INC-I1 block after the S81-07c block, before `## Tests`, one blank line before its heading (heading + the flag row + the stated limits + the owner steps, names only); the Feature Flags pointer clause after the S81-07c sentence (:341); one sentence at the end of the image paragraph (:313). `.github/black-clean-paths.txt` (CRLF kept): the leaf and the two RED files appended (I1-R17).

## 3. Deviations (from the spec, the prototype or the generic procedure; each with its reason)

- D-G1 Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (GC-11 and H12 (a), binding) instead of the procedure template's `Claude Fable 5.1`; the agent is Opus 5.5 (the global pin), not Fable.
- D-G2 Order: CLAUDE.md and the black list were edited BEFORE the head comm-set run (the procedure lists them after it), so the CLAUDE.md readers and the black-allowlist reader ran on the final bytes; the fourteen client fences ran last (GC-10).
- D-G3 Byte copies in `<SP>/INC-I1_green_before/` (the task's path), not the spec's `<SP>/INC-I1/green_before/`.
- D-G4 Deny order (GC-5 Q-5 "the deny check runs FIRST"): in `accept`, `accept_scheme` and `accept_pick` the deny runs before the https test and the text test, so an http candidate on a banned host logs `denied` (the prototype logged `scheme`). No frozen row has such a candidate.
- D-G5 Deny channels beyond I1-R1's list (stricter, inside the flag, never part of the relevance test): the TITLE text of every item through `is_denied_source` (the review's "(or its title)"), and for a knowledge-graph card its `website` / `descriptionLink` (`is_denied_url`) and `descriptionSource` (`is_denied_source`). No frozen row changes (no row title names a banned site).
- D-G6 The spaced unit word `gm` is excluded from the line tokens with ml / oz / fl / g (I1-R4 (c); the prototype kept `gm` as a line token, RED P-3), so a typed `100 gm` never demands `gm` in a picture title.
- D-G7 GC-5 Q-3 implemented: an empty or non-string category reads as `other` (the fragrance word is required with an empty brand); the prototype treated it as a non-fragrance category. Unpinned by the frozen rows (production canonicalizes to a non-empty key).
- D-G8 GC-5 Q-4 implemented: the I1-R14 https condition on the price-page override applies to TEXT products only (`and not is_vision`); the prototype applied it to every product. No frozen row drives a camera product through the override, so a mutant dropping `not is_vision` is not killed by the RED files (stated limit L-G3).
- D-G9 Tier 1 structure: under the guard the walk of images[:knob] runs and the base `images[0]` block becomes its `elif` (one base line `if` -> `elif`, no re-indent), instead of the prototype's `images = []` reset; flag OFF runs the base block unchanged.
- D-G10 The guard setup in img keeps spec 2.3's order `relevance is not None and _relevance.guard_enabled()` (a pure argument precondition first, so the production flag-OFF path, which passes no keyword, reads nothing new); every other gated predicate (relevance_kwargs, the noon block, the override condition) reads the flag as its first statement.
- D-G11 The CLAUDE.md block follows spec 8's heading and three bullets, its content amended by the rulings (the 1..10 clamp of I1-R7 replaces the spec's below-1-falls-back-to-5; the deny of I1-R1; I1-R2 / R3 / R4 / R5 / R10 / R12 / R14; I1-R6 and I1-R13; the I1-R19 price-warmer step; the I1-R15 canary items).
- D-G12 Head comm set = 30 chunks: the RED round's 29 base chunks unchanged (one-for-one with the base record) + chunk 30 with the two RED files, not a re-chunking of the 712 files.
- D-G13 `<SP>/INC-I1_green/PR_BODY.md` ends with the mandated footer line, whose robot emoji is the only non-ASCII content of that file (4 bytes); the report and every repository file are pure ASCII in the added text.

## 4. Runs (every [pyt] line; the full logs are under `<SP>/INC-I1_green/`)

```
[pyt] tag=inc-i1-green-on start=2026-11-14 22:25:59 end=2026-11-14 22:26:02 elapsed=3s bound=600s status=OK rc=0
summary: 118 passed, 1 warning
[hermeticity] sentinel checked 118 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
```
```
[pyt] tag=inc-i1-green-off start=2026-11-14 22:31:26 end=2026-11-14 22:31:29 elapsed=3s bound=600s status=OK rc=0
summary: 118 passed, 1 warning
[hermeticity] sentinel checked 118 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
```
```
[pyt] tag=inc-i1-head-img start=2026-11-14 22:32:22 end=2026-11-14 22:32:30 elapsed=8s bound=600s status=OK rc=0
summary: 112 passed, 14 warnings
[hermeticity] sentinel checked 112 test(s)
[netguard] blocked 3 attempt(s) from 1 node(s)
[netguard]   tests/test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service [egress] socket.getaddrinfo api.openai.com:443
```
```
[pyt] tag=inc-i1-head-pins start=2026-11-14 22:32:36 end=2026-11-14 22:33:02 elapsed=25s bound=1200s status=OK rc=0
summary: 972 passed, 15 warnings
[hermeticity] sentinel checked 972 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
```
```
[pyt] tag=inc-i1-head-scan start=2026-11-14 22:33:09 end=2026-11-14 22:33:34 elapsed=25s bound=1200s status=OK rc=0
summary: 371 passed, 15 warnings
[hermeticity] sentinel checked 371 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
```
```
[pyt] tag=inc-i1-head-pins2 start=2026-11-14 22:33:41 end=2026-11-14 22:35:04 elapsed=83s bound=1200s status=FAIL rc=1
summary: 1 failed, 373 passed, 6 warnings
[hermeticity] sentinel checked 374 test(s)
[netguard] blocked 22 attempt(s) from 21 node(s)
[netguard]   tests/test_hermeticity_pins.py::test_guard_blocks_getaddrinfo_for_a_public_host [egress] socket.getaddrinfo example.com:443
[netguard]   tests/test_hermeticity_pins.py::test_guard_decodes_a_bytes_host_in_the_record [egress] socket.getaddrinfo example.com:443
[netguard]   ... 19 more node line(s) in the log
```
```
[pyt] tag=inc-i1-ciorder start=2026-11-14 22:35:42 end=2026-11-14 22:35:59 elapsed=17s bound=1200s status=OK rc=0
summary: 783 passed, 15 warnings
[hermeticity] sentinel checked 783 test(s)
[netguard] blocked 3 attempt(s) from 1 node(s)
[netguard]   tests/test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service [egress] socket.getaddrinfo api.openai.com:443
```
```
[pyt] tag=inc-i1-ciorder-rev start=2026-11-14 22:37:52 end=2026-11-14 22:38:09 elapsed=17s bound=1200s status=OK rc=0
summary: 783 passed, 15 warnings
[hermeticity] sentinel checked 783 test(s)
[netguard] blocked 3 attempt(s) from 1 node(s)
[netguard]   tests/test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service [egress] socket.getaddrinfo api.openai.com:443
```

- green-on: `ENABLE_IMAGE_RELEVANCE_GUARD=true` exported for the one runner call; green-off: `=false`. Both 118 passed: every RED and PIN row green (the rows set their own flags).
- The spec 1.10 sets at head (img 7 files, pins 8, scan 7): the same pass state as the RED round's base runs (112 / 972 / 371 passed, no failure). pins2 = the remaining spec 4.2 identity pins (test_s81_s07_meas_harness, test_s75_fanout_identity, test_serper_record_usage, test_s78_serper_key_memo, test_hermeticity_pins): one failure, `tests/test_s81_s07_meas_harness.py::test_r35_fixtures` (assert b'\r' not in a fixture: the CRLF checkout), a base-record id (GC-5 Q-6).
- The CI-order set (GC-8: spec 7.3's twelve files + the two RED files, sorted = CI's alphabetical order) ran once in each order in ONE process each: green both ways; the one netguard block is the known base node listed in `tests/.network_attempt_baseline.txt`.

## 5. The comm set at HEAD (GC-7)

- Re-derived at head with the spec's comm.py rules (`<SP>/INC-I1_green/comm_head.py`: the texts of the changed and new files read from the working tree, the new leaf as a fourth seed, plus every `.github` / black-list reader; git reads otherwise): closure 85 modules (app/main.py included), derived 712 files = the RED round's 710 (`<SP>/INC-I1/red/comm/comm_set.txt`, sha256 5e2f0266...) + tests/test_inc_i1_noon_and_wiring.py, tests/test_inc_i1_picture_must_match.py; nothing else (base minus derived: none). The `.github` readers are all members except the excluded pre-commit hook files (the unit edits no .githooks). Union list `<SP>/INC-I1_green/comm/comm_set_head.txt` (sha256 f7acf4c68e0de335107e0ebfe04c712147f21348b80e6c6a3d798c746cf35fd2).
- Chunks: the RED round's 29 base chunks unchanged (`<SP>/INC-I1/red/comm/chunks.txt`) + chunk 30 = the two RED files (`<SP>/INC-I1_green/comm/chunks_head.txt`), bound 1200, tags inc-i1-comm-head-01..30, one at a time through gate.py, the flag and the knob unset (the production default).
- HEAD failure ids: 28; base record ids (`<SP>/harness/base_records/731bcddf531a7e123963246168ca19f262859337/5e2f0266d1a562fcdc79629d26cbfbc7b5a52e6fabd501bdecbf7a24296410ba.txt`): 28.
- **branch-only NEW (HEAD minus base): EMPTY**. Base ids not failing at head: none.
- Newly referenced modules (the leaf reaches category_gate, jsonld_widen, deny_hosts, price_service): every test naming category_gate (8), jsonld_widen (5), deny_hosts (10) or robots_eval (11) is a member; of the 209 tests naming price_service only tests/test_be_harness.py is outside, and it names price_service in a docstring only (no import of it or of any closure member), so the unit cannot change its result; not added.

| chunk | status | summary | FAILED / ERROR ids |
|---|---|---|---|
| 01 | OK | 783 passed, 15 warnings | - |
| 02 | FAIL | 2 failed, 548 passed, 39 warnings | tests/test_auth_interceptor.py::test_sign_in_with_social_exception<br>tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully |
| 03 | OK | 461 passed, 1 deselected, 15 warnings | - |
| 04 | OK | 1788 passed, 1 skipped, 7 deselected, 17 warnings | - |
| 05 | OK | 656 passed, 1 xfailed, 15 warnings | - |
| 06 | OK | 422 passed, 9 deselected, 17 warnings | - |
| 07 | OK | 394 passed, 2 skipped, 1 warning | - |
| 08 | OK | 2013 passed, 15 warnings | - |
| 09 | OK | 1400 passed, 1 skipped, 5 deselected, 22 warnings | - |
| 10 | OK | 627 passed, 1 xfailed, 17 warnings | - |
| 11 | OK | 463 passed, 16 warnings | - |
| 12 | OK | 176 passed, 17 warnings | - |
| 13 | OK | 574 passed, 1 skipped, 10 deselected, 1 warning | - |
| 14 | FAIL | 2 failed, 3721 passed, 22 skipped, 18 warnings | tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest<br>tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction |
| 15 | FAIL | 2 failed, 744 passed, 3 skipped, 5 deselected, 23 warnings | tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities<br>tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys |
| 16 | FAIL | 404 passed, 3 skipped, 9 deselected, 1 xfailed, 17 warnings, 2 errors | tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence<br>tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable |
| 17 | OK | 320 passed, 1 skipped, 1 deselected, 17 warnings | - |
| 18 | OK | 862 passed, 373 warnings | - |
| 19 | OK | 1439 passed, 17 warnings | - |
| 20 | FAIL | 7 failed, 2214 passed, 16 warnings | tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only<br>tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset] |
| 21 | FAIL | 7 failed, 2541 passed, 137 warnings | tests/test_s81_s07_meas_harness.py::test_r35_fixtures<br>tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata] |
| 22 | FAIL | 6 failed, 1687 passed, 49 warnings | tests/test_s81_s18b_store_label.py::test_r2_table_shape<br>tests/test_s81_s19_gap_queue.py::test_r15_hygiene<br>tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf<br>tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first<br>tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene<br>tests/test_s81_s24_auth_throttle.py::test_r92_hygiene |
| 23 | OK | 1118 passed, 1 xfailed, 17 warnings | - |
| 24 | OK | 657 passed, 1 skipped, 2 deselected, 16 warnings | - |
| 25 | OK | 456 passed, 7 skipped, 8 deselected, 24 warnings | - |
| 26 | OK | 561 passed, 4 deselected, 17 warnings | - |
| 27 | OK | 382 passed, 4 deselected, 35 xfailed, 14 warnings | - |
| 28 | OK | 1249 passed, 10 skipped, 17 warnings | - |
| 29 | OK | 169 passed, 1 warning | - |
| 30 | OK | 118 passed | - |

```
[pyt] tag=inc-i1-comm-head-01 start=2026-11-14 22:38:16 end=2026-11-14 22:38:47 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-02 start=2026-11-14 22:40:13 end=2026-11-14 22:40:38 elapsed=25s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-03 start=2026-11-14 22:45:13 end=2026-11-14 22:45:38 elapsed=25s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-04 start=2026-11-14 22:45:45 end=2026-11-14 22:46:49 elapsed=64s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-05 start=2026-11-14 22:49:02 end=2026-11-14 22:49:17 elapsed=15s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-06 start=2026-11-14 22:49:24 end=2026-11-14 22:49:37 elapsed=13s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-07 start=2026-11-14 22:50:00 end=2026-11-14 22:50:20 elapsed=19s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-08 start=2026-11-14 22:50:27 end=2026-11-14 22:51:05 elapsed=39s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-09 start=2026-11-14 22:51:12 end=2026-11-14 22:52:09 elapsed=57s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-10 start=2026-11-14 22:52:16 end=2026-11-14 22:53:06 elapsed=50s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-11 start=2026-11-14 22:54:59 end=2026-11-14 22:55:26 elapsed=26s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-12 start=2026-11-14 22:55:33 end=2026-11-14 22:55:45 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-13 start=2026-11-14 22:55:52 end=2026-11-14 22:56:11 elapsed=19s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-14 start=2026-11-14 22:56:18 end=2026-11-14 22:56:45 elapsed=27s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-15 start=2026-11-14 22:56:51 end=2026-11-14 22:57:28 elapsed=37s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-16 start=2026-11-14 22:57:35 end=2026-11-14 22:58:01 elapsed=26s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-17 start=2026-11-14 22:58:08 end=2026-11-14 22:58:21 elapsed=13s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-18 start=2026-11-14 23:06:48 end=2026-11-14 23:09:34 elapsed=166s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-19 start=2026-11-14 23:09:41 end=2026-11-14 23:11:04 elapsed=83s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-20 start=2026-11-14 23:11:11 end=2026-11-14 23:12:04 elapsed=54s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-21 start=2026-11-14 23:12:27 end=2026-11-14 23:14:36 elapsed=128s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-22 start=2026-11-14 23:14:42 end=2026-11-14 23:15:34 elapsed=51s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-23 start=2026-11-14 23:15:41 end=2026-11-14 23:16:18 elapsed=37s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-24 start=2026-11-14 23:16:25 end=2026-11-14 23:17:11 elapsed=46s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-25 start=2026-11-14 23:17:17 end=2026-11-14 23:17:59 elapsed=41s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-26 start=2026-11-14 23:18:05 end=2026-11-14 23:18:41 elapsed=35s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-27 start=2026-11-14 23:18:48 end=2026-11-14 23:19:15 elapsed=27s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-28 start=2026-11-14 23:19:21 end=2026-11-14 23:19:56 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-29 start=2026-11-14 23:21:07 end=2026-11-14 23:21:13 elapsed=6s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-30 start=2026-11-14 23:21:20 end=2026-11-14 23:21:23 elapsed=3s bound=1200s status=OK rc=0
```

## 6. Lint and hygiene

- `python -m py_compile` on the four app files: OK. `python -m ruff check --select E9,F63,F7,F82 --no-cache` (ruff 0.16.5) on the four app files and the two RED files: All checks passed. `python -m black --check` (26.5.1) on the leaf and the two RED files: unchanged (the leaf was formatted with black before the copy).
- Added-line sweep over the diff and the three new files (`<SP>/INC-I1_green/added_lines.txt`): no 8-digit run, no `@gmail`, no `+973`, no `sk-` / AKIA / xox / JWT / credentialed-URL / PEM shape, no 64-hex literal; the only e-mail-like hits are `@pytest` decorators; the only bytes > 127 are the existing characters of the two rewritten CLAUDE.md lines (:313, :341). The leaf and the two RED files: 0 bytes > 127, no CR.

## 7. The commit (GC-11)

```
branch: fix/inc-i1-picture-must-match  HEAD before: 731bcddf531a7e123963246168ca19f262859337
M  .github/black-clean-paths.txt
M  CLAUDE.md
A  app/services/image_relevance.py
M  app/services/image_service.py
M  app/services/noon_service.py
M  app/services/structured_comparison_service.py
A  tests/test_inc_i1_noon_and_wiring.py
A  tests/test_inc_i1_picture_must_match.py
All checks passed!
3 files would be left unchanged.
[fix/inc-i1-picture-must-match 5cf13f62] fix(images): INC-I1 PICTURE-MUST-MATCH guard, dark behind ENABLE_IMAGE_RELEVANCE_GUARD
 8 files changed, 2750 insertions(+), 8 deletions(-)
 create mode 100644 app/services/image_relevance.py
 create mode 100644 tests/test_inc_i1_noon_and_wiring.py
 create mode 100644 tests/test_inc_i1_picture_must_match.py
commit rc=0  HEAD after: 5cf13f622394f4f9133b46b026dc77376b0038b1
HEAD MOVED
5cf13f62 fix(images): INC-I1 PICTURE-MUST-MATCH guard, dark behind ENABLE_IMAGE_RELEVANCE_GUARD
hook: ruff (E9,F63,F7,F82) 'All checks passed!'; black --check on the allowlisted staged files: '3 files would be left unchanged'; gitleaks / added-line sweep / binary check: no refusal (the commit was created).
autocrlf note: git warned that the three new LF files (the leaf and the two RED files) are LF in the working copy; the index holds LF; the frozen RED blobs hash e3461440... / 96153bd6... in HEAD.
black also printed its notice that Python 3.12 cannot parse code formatted for a newer target (a version notice; the files were left unchanged).
```

## 8. The fourteen client fences (GC-10, once, the last gate)

```
gate.py --wait-only, then the H5 jest probe (no jest alive), then from sc-inc-i1/SmartCompareApp through the orchestrator's junction: timeout -k 15 600 node node_modules/jest/bin/jest.js --ci <the fourteen suites by path>
[jest] node v24.11.1 jest 29.7.0
PASS __tests__/clientTruth/privacyManifest.s74.test.ts
PASS __tests__/clipboardFallbackService.test.ts
PASS __tests__/playInstallReferrerService.test.ts
PASS __tests__/playInstallReferrerService.edges.test.ts
PASS __tests__/landing.domain.s76.test.ts
PASS __tests__/ResultsScreen.timeout.test.tsx
PASS __tests__/onboarding/step05Trust.s69.test.tsx
PASS __tests__/clientTruth/shareTruth.s74.test.tsx
PASS __tests__/clientTruth/medicalNote.s74.test.tsx
PASS __tests__/honestCounts.s69.test.tsx
PASS __tests__/DimensionBars.perCategory.test.tsx
PASS __tests__/brand/inAppMark.u4c.test.ts
FAIL __tests__/config/nativeBundle.w37.test.ts
PASS __tests__/navigation/linking.w315.test.ts (5.511 s)
Test Suites: 1 failed, 13 passed, 14 total
Tests:       4 failed, 236 passed, 240 total
[jest] tag=inc-i1-fences start=2026-11-14 23:23:02 end=2026-11-14 23:23:10 rc=1
The 4 failed nodes = the four accepted config/nativeBundle.w37 drift nodes (d5 react-native-gesture-handler removal; k2, k4, k5 the Expo SDK 54 patch-level rows), the same nodes as the G-INC-1 / S81-12d records: no fence reads a literal this unit adds or moves.
```

## 9. Stated limits GREEN adds (LC-4) and open questions

- L-G1 `_related` (Tier-3 host relation) relates a dotless pick host (for example a bare top-level label) to every link under it; such a pick cannot load, so the client shows the placeholder (never a wrong picture). Not hardened mid-run to keep the gated bytes stable.
- L-G2 `_first_image` prefers the first https key of an item; an item whose https value is on a banned host is rejected whole (`denied`), even when another key of the same item holds a clean https image.
- L-G3 The GC-5 Q-4 camera exemption of the override https rule (D-G8) and the Q-3 empty-category reading (D-G7) carry no frozen row: the adversary may ask for gate rows (LC-4: a minor is a stated limit by default).
- L-G4 The deny on titles (D-G5) uses `is_denied_source`'s whole-token match of the four banned labels; a product title that merely names one of those sites as a word is rejected (precision first).
- Q-G1 (for the orchestrator) Keep the stricter deny channels of D-G5 (title text; the KG website / description link / description source)? Recommended: keep (H12 (g): never Fragrantica data in any form).
- Q-G2 (for the orchestrator) Gate rows for D-G7 / D-G8 in a fix round, or stated limits? Recommended: stated limits unless the adversary rates them above minor.

## 10. End state

```
5cf13f62 fix(images): INC-I1 PICTURE-MUST-MATCH guard, dark behind ENABLE_IMAGE_RELEVANCE_GUARD
fix/inc-i1-picture-must-match
(git status --short above is EMPTY: the worktree is clean at HEAD; the node_modules junction is the orchestrator's and untracked-ignored)
```

- NOT MEASURED in this round: the mutation table on the GREEN bytes (the RED round's 66 on the prototype stand; GC-3 gives the re-run sample to the adversary); the full jest suite (LC-7: the last round before the PR); every production behaviour (H6: nothing here is a production claim; the unit is "merged, NOT yet proven" until the owner's phone proof).
- PR body draft: `<SP>/INC-I1_green/PR_BODY.md` (written by `build_docs.py` through the shell).
