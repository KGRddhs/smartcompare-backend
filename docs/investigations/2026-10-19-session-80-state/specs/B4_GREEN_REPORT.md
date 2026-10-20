# B4 URL-MODE-V2 (ENABLE_URL_MODE_V2) -- GREEN report (2026-10-20)

- Unit B4, flag `ENABLE_URL_MODE_V2` (default OFF, read per call). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s80-b4`, branch `feature/s80-b4-url-mode-v2` (created with the one allowed `git checkout -b`), base `81df2b641454e0301cca51a3ba01bf8ef3d7e649` (not rebased, GC-7).
- HEAD `9db99de97245aa4543e054dd5f94c0800b270e69` (one commit through the pre-commit hook: `All checks passed!`; not pushed, no PR).
- Agent model: this GREEN agent ran on claude-opus-5-5 (system prompt; the session-80 ledger 13:50 line records the same); the commit trailer says `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the brief's Fable 5.1 text would be a false attribution).
- RED file `tests/test_s80_url_mode_v2.py`: sha256 `c4549be2f5cd8edfd60cbc07db427ed5275cc4b44ab719614ef97b9eca227cae` at the start, after the commit (working copy) and as the committed blob (`git show HEAD:...`); 0 bytes > 127, LF.
- `git status --short` at the end: empty. No mutation lock left; no orphan pytest (the two python.exe processes are unrelated `http.server` instances).
- Inputs read in full: s80-common.txt (+ the 2026-10-20 addendum), PLAN_S80.md sections 0-1 + B4, RULINGS_R0.md, RULINGS_BATCH1.md Common G-1..G-4 + B4-R1..R11, GATE_B4.md GC-1..GC-8, the spec and review, the RED report and prototype (reference only; every hunk re-derived).

## Files (final sha256 = bytes on disk = the committed working copy)

| file | +/- | sha256 before | sha256 after | bytes > 127 (before/after) |
|---|---|---|---|---|
| app/services/url_extraction_service.py | +617/-17 | 0330b762eb7defa1e218e210ff7a51ae3c341c94a8d52365f85d724ee7c59fa9 | 649c93a88cbded0fc399594c9492fcd83cbc568ace3a40cba9f0029a4eaabef1 | 18/18 |
| app/api/url_routes.py | +112/-3 | bc3d0822e7e89906d6248fb66af710e755f7755dbd7e9d770107bb430d1557db | 9229e0b4d027e392f21e5da9edb29549f40fcde2bb22ca90c4351701ab3a59ba | 0/0 |
| app/middleware/error_handler.py | +25/-0 | 8116436749c8ebeb826d39a14428f69cff25f912b0cbeda23e5a853943bac4c5 | 7e539cc7b17fcc6c9b982a2ebe4b212096af57deb8c1bded330eb57e5fc6d482 | 3/3 |
| tests/test_model_config_enforced.py (E1) | +1/-1 | b3813ad62ce944a44a7ad505fab119be2055d15139436d507620e210a1b3f19b | 5e90f9a63ff8f0013dceedc65813aff546e6867481cf060168e2f30de934336b | 0/0 |
| tests/w4_11_prompt_digest_recorder.py (E2) | +1/-1 | 8c90ef5bff06208f4f9f3025ff5a0dd94fc2d7396115004d0d92ab722537a826 | 2c92065df907f975e2cffaf00eff960b83b22916aae6a23237b76c1dd6d4b8e6 | 0/0 |
| tests/test_prompt_fence.py (E3) | +1/-1 | d5474744d232934194321158516135f5087a4feb355d769372e3867815305930 | b5b39f98a5db0c94e65437dba3f9122d664f5dcb408f805c5d6b323a03cea2d5 | 0/0 |
| tests/test_s71_u13_compare_auth_required.py (E4) | +1/-0 | 289f24f590627b351862a00ee701fb9978d8f0ae4254a7df98a3cae132dd4121 | 24cd27ff6993b0e83a050f6a32a605edaff8ae10d97bd09ff9757814d6f7ac94 | 0/0 |
| tests/test_retro_w2_1.py (E5, B4-R8) | +1/-1 | 1d14c619fb67fdefd44d574a414122bacef13372353656bb4e70ba18b4df46e8 | ba125e514242fa81a1268946435a1a380e0f03ac21753a14c33b50ea254a33de | 3/3 |
| CLAUDE.md (the SESSION 80 B4 row) | +3/-0 | ab7ec7dde1724998f7d12a4d5a2c70ee55efdad95c89c6c025413a21929d7415 | 89ce189a83da5f6fc8e95ad5d01937a969194fee3401f84482061466738e06b4 | 3979/3979 |
| tests/test_s80_url_mode_v2.py (RED, frozen) | +1515 | c4549be2...cae | c4549be2f5cd8edfd60cbc07db427ed5275cc4b44ab719614ef97b9eca227cae | 0/0 |

Every edited backend file stays all-CRLF (CRLF count == line count); `git diff --stat` shows content lines only (8 whitespace-only lines the Edit tool emptied were restored to their base bytes by a line-level SequenceMatcher before the commit). Byte copies: `<scratchpad>/B4_green_before/` + `SHA256SUMS.txt`. CLAUDE.md row: after the SESSION 79 B3-B row, before `## Tests` (no SESSION 80 row exists at the spec base; at the rebase it goes after the B1 and B3 rows, G-2).

## Implementation map (spec 2.2 as amended)

- `url_extraction_service`: copy constants; `url_mode_v2_enabled` (house idiom); `_TRANSPORT = None`; `_host_only` / `normalize_url_for_same_check` (ValueError-safe, B4-R4); `classify_url_path` (price_service root/search regexes lazily + cart/account/category, product-segment veto, falsy/non-str -> None, GC-4); `_is_challenge_page` (bounded regex on `<title>` of `text[:65536]`, no soup, B4-R2); `_title_key` / `is_usable_title` / `_v2_site_names` (Organization + WebSite + og:site_name, `@graph` walked); `normalize_image_url` (`_jsonld_image_urls` + `urljoin` on the final url, https only); `_v2_code_message`; `_log_fetch_failed` (GC-1 WARNING); `_fetch_page_v2` (fetch_page's loop, status/final url kept, per-hop SSRF, 5-hop bound, host-only `[SSRF]` lines, never raises); `extract_generic_data_v2` (shape ladder, image normalised, og fallback by VALUE, private `_v2_product_node` / `_v2_site_names`); `URL_EXTRACTION_PROMPT_V2` via `_derive_url_extraction_prompt_v2` (two count-checked swaps, RuntimeError at import on drift); `extract_with_ai(..., url_mode_v2=False)`; `_v2_status_reason`, `_v2_refusal`, `_extract_from_url_v2` (steps a-f; extractor via the W0-4f offload shape); `extract_from_url(url, url_mode_v2=False)`; `normalize_product_data(..., url_mode_v2=False, final_url=None)`; `compare_from_urls(..., url_mode_v2=False)` + `_v2_pair_failure` + `_v2_verdict_fill`; the base `Detected retailer` INFO line host-only.
- `url_routes`: `_URL_COMPARE_DEADLINE_SECONDS = 25.0`; `_URL_V2_REFUSAL_CODES`; `_url_pre_gate`; `_raise_url_refusal`; `_compare_with_deadline` (`asyncio.wait_for`, TIMEOUT result + WARNING, other exceptions to the base arm); `_compare_urls_metered(..., url_mode_v2=False)`; both verbs read the flag once, SSRF first, then the pre-gate, then the metered call with the conditional kwarg; the three INFO lines host-only.
- `error_handler`: `_url_mode_v2_keys_enabled` (local one-liner) + the scoped passthrough (flag first; `isinstance(code, str)` and code in the three B4 codes; str values only; a tuple, so an unhashable code cannot raise).

## Runs (every pytest through pyt.py, one at a time)

Unit file, both flag states (the rows set what they need):
```
ENABLE_URL_MODE_V2=true  (-x, first look): 1 failed, 112 passed -> stopped at R12
[pyt] tag=b4g-unit-on1 start=2026-10-20 14:02:50 end=2026-10-20 14:03:02 elapsed=12s bound=600s status=FAIL rc=1
ENABLE_URL_MODE_V2=true: 2 failed, 250 passed, 11 warnings in 9.26s; [hermeticity] sentinel checked 252 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b4g-unit-on2 start=2026-10-20 14:03:15 end=2026-10-20 14:03:28 elapsed=13s bound=600s status=FAIL rc=1
flag unset: 2 failed, 250 passed, 11 warnings in 20.47s; sentinel 252; netguard 0
[pyt] tag=b4g-unit-off1 start=2026-10-20 14:03:44 end=2026-10-20 14:04:07 elapsed=23s bound=600s status=FAIL rc=1
ENABLE_URL_MODE_V2=true (after the retailer-label change): 2 failed, 250 passed, 11 warnings in 53.97s; sentinel 252; netguard 0
[pyt] tag=b4g-unit-on3 start=2026-10-20 14:49:58 end=2026-10-20 14:50:59 elapsed=61s bound=600s status=FAIL rc=1
```
Failed nodes in every run: `test_transport_error_is_store_unreadable[POST]`, `[GET]` (R12), on `assert len(errors) == 1` with `errors == []` (no ERROR-level record): see Deviation D1.

R12 alternative measured (byte copy of the GREEN service, transport-error line at ERROR inside the except arm, same distinct template; restored, sha `dd613f0d...0fac` before == after, lock removed):
```
-k "transport_error or R8 or r8" over the unit file + tests/test_sentry_channels_u8d_unit.py: 12 passed, 381 deselected, 11 warnings in 33.89s; sentinel 12; netguard 0
[pyt] tag=b4g-variant-error-level start=2026-10-20 14:04:43 end=2026-10-20 14:05:23 elapsed=40s bound=600s status=OK rc=0
```

Existing pins / identity (flag OFF, one call, 20 files: test_retro_w2_1, test_url_compare_category, test_prompt_fence, test_model_config_enforced, test_s71_u13_compare_auth_required, test_w4_13_flag_off_ledger, test_w4_13_measurement_truth, test_error_middleware, test_ssrf_redirect_hardening, test_retro_w0_4_efg, test_paid_route_metering, test_u13e_url_detect_guard, test_comparison_id_echo, test_u3c_store_false_pin, test_sentry_channels_u8d_unit, test_429_contract, test_retro_w1_9_429, test_text_routes_error_mapping, test_http_400_cap_cut_mapping, test_s70_url_client_retries):
```
1037 passed, 13 warnings in 172.17s; [hermeticity] sentinel checked 1037 test(s); [netguard] blocked 10 attempt(s) from 10 node(s)
[pyt] tag=b4g-pins1 start=2026-10-20 14:05:47 end=2026-10-20 14:08:47 elapsed=179s bound=600s status=OK rc=0
```
(the 10 blocks are `[sentinel] neutralized.supabase.invalid:443` on test_paid_route_metering x2, test_text_routes_error_mapping x1, test_http_400_cap_cut_mapping x7, all present in the RED base comm logs; sentinel class, not egress.)
```
tests/test_retro_w0_4.py (the W0-4c guards incl. the transitive soup guard): 157 passed in 89.26s; sentinel 157; netguard 0
[pyt] tag=b4g-retro-w0-4 start=2026-10-20 14:09:01 end=2026-10-20 14:10:39 elapsed=98s bound=600s status=OK rc=0
```
Information only (flag EXPORTED ON over the same 20 files, the local-.env class, B4-R8):
```
5 failed, 1032 passed, 13 warnings in 107.88s  -> tests/test_paid_route_metering.py::test_url_compare_post_returns_success_on_extracted_pair, ::test_url_compare_get_returns_success_on_extracted_pair, ::test_url_compare_failure_exit_refunds_once, ::test_url_compare_threads_selected_category, ::test_url_compare_saves_history_with_input_type_url (TypeError: _stub_url_leaves.<locals>._extract() got an unexpected keyword argument 'url_mode_v2')
[pyt] tag=b4g-pins1-flagON-info start=2026-10-20 14:13:01 end=2026-10-20 14:15:01 elapsed=120s bound=600s status=FAIL rc=1
```
Post-edit delta runs (after the retailer-label change and the CLAUDE.md sentence amendment):
```
unit + u8d_unit + retro_w0_4_efg + ssrf_redirect + url_compare_category + prompt_fence + retro_w2_1 + the three W0-4c guard nodes: 2 failed (R12), 701 passed; sentinel 703; netguard 0
[pyt] tag=b4g-delta-after-logname start=2026-10-20 14:51:15 end=2026-10-20 14:53:02 elapsed=106s bound=600s status=FAIL rc=1
test_ci_gates + test_behavior_dimension_translation + test_w4_13_measurement_truth + test_w4_13_flag_off_ledger + test_paid_route_metering + test_s71_u13 + test_model_config_enforced + test_u3c_store_false_pin (committed HEAD bytes): 516 passed, 13 warnings in 24.47s; sentinel 516; netguard blocked 2 attempt(s) from 2 node(s)
[pyt] tag=b4g-delta2-head start=2026-10-20 15:01:39 end=2026-10-20 15:02:09 elapsed=31s bound=600s status=OK rc=0
```

Comm set at HEAD (GC-5 + the 2026-10-20 addendum; builder `B4_green/build_comm_head.py`, list `comm_head_files.txt` sha256 `84828db51c091f3791ecb62deae6c20cb4c6c12e274e4762d6cb42a75135decb`, reasons `comm_head_reasons.tsv`): 120 files = the RED base list of 119 (sha `84b1f89b...1151`) UNION the module/symbol grep at HEAD (`url_routes|url_extraction_service|error_handler`) UNION the SmartCompareApp scanners UNION every test referencing the edited test-support module `w4_11_prompt_digest_recorder` UNION the importers of the five edited test files and the unit file (none beyond the list) UNION the W4-13 url envelope pins UNION the source-scanning pins (HEAD grep + the RED grep + the named s80-common pins + test_retro_w0_4) UNION the CLAUDE.md readers UNION the unit file; EXCLUDED: tests/test_precommit_hook.py, test_precommit_hook_phase_b.py, test_precommit_hook_phase_b_round2.py (`.githooks` untouched); tests/test_rate_limiting_complete.py never matched (NETWORK_FLAKY_EXCLUDE). Added beyond the RED list: only the unit file; dropped: none. Flag OFF, bound 1200:
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
HEAD FAILED/ERROR ids (`head_failed_ids.txt`): `tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence` (ERROR), `::test_truth_on_prefix_static_and_cacheable` (ERROR) -- identical to the RED base set (`comm_base_failed.txt`, cold tiktoken cache); `tests/test_s80_url_mode_v2.py::test_transport_error_is_store_unreadable[GET]`, `[POST]`.
`comm -13 base head` (branch-only-NEW) = the two R12 nodes of the unit's own RED file (D1); ZERO new failures in the 119 existing files. Totals: base 5955 passed over 119 files, HEAD 6205 passed = 5955 + the 250 passing unit nodes. Netguard node sets (base from the RED comm logs vs HEAD): head-only = none; base-only = `tests/test_flush_live_price_key.py::test_flag_off_body_is_the_legacy_shape_exactly [egress]`, `tests/test_timeout_partial_integration.py::TestStreamingTimeoutD2Contract::test_stream_hardcap_yields_stream_timeout_partial [egress]` (attempted at base, not at HEAD; files untouched by the unit).
The comm chunks ran BEFORE two log-text-only edits (the retailer label helper, a CLAUDE.md sentence); both delta runs above cover every file that reads those bytes.

CI-order set (alphabetical, flag OFF only, B4-R8):
```
tests/test_error_middleware.py tests/test_http_400_cap_cut_mapping.py tests/test_paid_route_metering.py tests/test_prompt_fence.py tests/test_retro_w2_1.py tests/test_s71_u13_compare_auth_required.py tests/test_s80_url_mode_v2.py tests/test_ssrf_redirect_hardening.py tests/test_text_routes_error_mapping.py tests/test_u13e_url_detect_guard.py tests/test_url_compare_category.py tests/test_w4_13_flag_off_ledger.py tests/test_w4_13_measurement_truth.py
2 failed (R12), 901 passed, 13 warnings in 129.91s; sentinel 903; netguard blocked 10 attempt(s) from 10 node(s)
[pyt] tag=b4g-ci-order start=2026-10-20 14:44:09 end=2026-10-20 14:46:30 elapsed=140s bound=1200s status=FAIL rc=1
```

Lint: `python -m ruff check --select E9,F63,F7,F82 --no-cache` on the 3 app files + 5 edited tests + the unit file: `All checks passed!`; `python -m py_compile` on the same: OK; full-rule ruff (worktree config) on the 3 app files: 70 findings at HEAD vs 71 at base, no new rule/line class (the one removed: `typing.Tuple` unused). None of the edited files is on `.github/black-clean-paths.txt`. Added-line sweep (`git diff -U0 | grep ^+` for @gmail, +973, 8-digit runs, sk-/AKIA/xox/eyJ, credentialed URL, PEM): no hit.

## Mutation on the GREEN bytes (reduced, 12 mutants; `B4_green/mutants_green.py` via `variant.py`: lock, byte copy, exact edit matching once, `-k` the killing rows, restore, sha256 compare; every restore OK, lock removed)

| mutant | result | [pyt] |
|---|---|---|
| G1 route reads v2 = True (POST) | KILLED (7 failed) | tag=b4g-mut-G1_route_gate_always_on elapsed=5s status=FAIL rc=1 |
| G2 error-handler flag check removed | KILLED (1 failed) | tag=b4g-mut-G2_handler_flag_check_removed elapsed=5s status=FAIL rc=1 |
| G3 `_fetch_page_v2` per-hop SSRF removed | KILLED (3 failed) | tag=b4g-mut-G3_fetch_v2_hop_validation_removed elapsed=5s status=FAIL rc=1 |
| G4 hop bound 5 -> 50 | KILLED (3 failed) | tag=b4g-mut-G4_fetch_v2_hop_bound_removed elapsed=5s status=FAIL rc=1 |
| G5 LLM false refuses a node-bearing page | KILLED (1 failed) | tag=b4g-mut-G5_llm_false_refuses_node_page elapsed=5s status=FAIL rc=1 |
| G6 og fallback by key presence | KILLED (4 failed) | tag=b4g-mut-G6_og_fallback_key_presence elapsed=5s status=FAIL rc=1 |
| G7 deadline timeout=None | KILLED (2 failed) | tag=b4g-mut-G7_deadline_removed elapsed=6s status=FAIL rc=1 |
| G8 coded refusals through the shared mapping | KILLED (4 failed) | tag=b4g-mut-G8_refusal_through_shared_mapping elapsed=5s status=FAIL rc=1 |
| G9 site names ignored | KILLED (3 failed) | tag=b4g-mut-G9_site_names_ignored elapsed=9s status=FAIL rc=1 |
| G10 normaliser image coercion removed (ON) | SURVIVED (20 passed) | tag=b4g-mut-G10_v2_image_raw_on_wire elapsed=51s status=OK rc=0 |
| G11 precedence inverted | KILLED (4 failed) | tag=b4g-mut-G11_precedence_inverted elapsed=73s status=FAIL rc=1 |
| G12 post-fetch class check removed | KILLED (4 failed) | tag=b4g-mut-G12_post_fetch_class_check_removed elapsed=46s status=FAIL rc=1 |

G10 is not equivalent: the generic v2 extractor already returns a normalised image, so the normaliser-stage coercion only acts on an LLM-merged `image_url` (the extractor found none) or on the amazon / noon extractors' raw image; no RED row exercises either. Reported for a ruling (a row an adversary may add). The RED agent's 63-mutant table ran on its prototype, not on these bytes; the full M1-M49 table on the GREEN bytes is NOT MEASURED here.

## Counts

RED file: 252 nodes (206 RED + 46 PIN at base); HEAD: 250 green, 2 red (R12, D1) in both flag states. Mutants on GREEN bytes: 11/12 KILLED, 1 survivor (G10). Comm: 120 files, branch-only-NEW = 2 (unit file R12 only), 0 in the existing estate.

## Deviations

- D1 (GC-1 vs RED R12, the one blocking item): GC-1 (binding) puts `_fetch_page_v2`'s transport error (and every unreadable-fetch outcome) on ONE WARNING `[URL-V2] fetch failed host=%s reason=%s type=%s`; the frozen R12 asserts exactly one ERROR-level record with the exception type, so the gate's "R12 already accepts this" is factually wrong (measured: `AssertionError: []` at line 728). Implemented per GC-1; R12 POST/GET red (all their other assertions pass); the RED file is not edited. Measured alternative: the transport-error line at ERROR inside the except arm, same distinct template -> R12 green and every u8d R8 pin green (b4g-variant-error-level). A ruling picks one.
- D2 site names: Organization / WebSite / og:site_name (the spec's own CLAUDE.md row wording), NOT WebPage (spec 2.2 lists it): a WebPage node names the page itself and on a PDP without Product schema it is often equal to the `<title>`, which would refuse that PDP at $0 without the LLM rung. Unpinned either way (the fixture's WebPage name differs from its title).
- D3 the v2 fetch's three `[SSRF]` WARNING lines print the host only (`host=<h>`); the spec says "the base WARNING lines" (full url). R40/R41 match by prefix; the security lens (no user content in a WARNING line) wins for new code; `fetch_page`'s own lines are unchanged (L10).
- D4 the `Detected retailer` INFO label (both paths) is a SUPPORTED_RETAILERS name or `unknown`, not `retailer["name"]`: for an unknown retailer that name is the raw netloc, which carries a pasted `user:pass@` (the SSRF guard does not refuse userinfo). Unpinned beyond R34.
- D5 `normalize_product_data` gains `url_mode_v2` and `final_url` only (the spec's unused `site_names` kwarg omitted).
- D6 `_compare_with_deadline` helper holds the `wait_for` arm (the spec placed it inline in `_compare_urls_metered`); same semantics: the TIMEOUT result goes through the unchanged failure exit, any other exception to the base arm.
- D7 the challenge-title regex is `<title(?:\s[^>]*)?>` (not `<title[^>]*>`, which also matches `<titlefoo>`); the error-handler code check is `isinstance(str)` + a tuple membership (an unhashable code cannot raise).
- D8 commit trailer `Claude Opus 5.5` (the actual model; the brief's text says Fable 5.1).
- D9 the PR body's last line carries the required robot glyph (4 bytes > 127), the only non-ASCII byte in any file written.

## Questions for the gate

1. D1: re-freeze R12 with WARNING (my recommendation: GC-1's reason holds; one RED-row edit) or keep ERROR for the transport-error case (measured green)?
2. G10 survivor: add a row for an LLM-merged or amazon/noon raw image under ON (the adversary can write it), or accept?
3. E6 wanted? `ENABLE_URL_MODE_V2` into `tests/test_paid_route_metering.py`'s clean list would close the measured local-.env class (5 nodes); not done (only E5 was authorised).
4. D2 (WebPage excluded from site names) and D3/D4 (host-only labels): confirm.

## NOT MEASURED

- The full M1-M49 mutation table on the GREEN bytes (12 targeted mutants run instead).
- A base re-run of the comm set (the RED report's base runs are the base side; GREEN did not rebuild a base scratch worktree since no HEAD-only failure outside the unit file appeared).
- The four `test_precommit_hook*.py` files (excluded by rule; `.githooks` untouched); the hook itself ran on the commit.
- Any live fetch (rules); the post-rebase run on `cb80ea2f` (the orchestrator's step, GC-7).

## Notes folder

`<scratchpad>/B4_green/`: notes.md, snap.py (byte copies + hashes), ws_restore.py, variant.py, mutants_green.py (+ .json), build_comm_head.py, comm_head_* (list, reasons, chunks, logs), every `[pyt]` log named in this report, precommit/postcommit hashes, PR_BODY.md, commit_msg.txt.
