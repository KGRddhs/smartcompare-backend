# S81-10b LINKS-GATE GREEN report (GREEN agent Opus 5.5, 2026-11-04 07:13-07:40 AST)

Written through the shell by a generator script (the harness refuses a subagent Write of a report .md).
Unit S81-10b (FOCUS, LC-1: two adversaries), flag ENABLE_FRAGRANCE_ONLY_GATE (shared with S81-10, no new name).
Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s10b, branch feature/s81-s10b-links-gate (created from the detached c6fb6533 before the first edit).
HEAD 0e936223921ec0dd4bf70061807521de75799c95 (ONE commit through the pre-commit hook; trailer Co-Authored-By: Claude Opus 5.5). Not pushed, not rebased, no PR.
git status --short after the commit: empty.

## Files (sha256 of the bytes on disk; before copies in scratchpad/S81-10b_green_before/ with SHA256SUMS.txt)
| File | before | after | numstat vs c6fb6533 |
|---|---|---|---|
| app/api/url_routes.py | c0ff7eb2f4e2c046fae7a59667238d69b63040bc0e2d9f88e23ec05a9f87b9b7 | 04aa91fd315bcd124d67619c71b8c339ca8a27f43e215545a5138e60d08a09c1 | +45 -8 |
| app/services/url_extraction_service.py | 0a5243074a762847a75f8468c0d3928c825d5b8188f30422665b87d820a69aa6 | f0cfb93415af8b695d6d5e357811e616f93a39914a4404fb664a392e8d13e542 | +83 -1 |
| app/services/category_gate.py | 97332ff705887648b609b3f0ba520808a9e83243290e3457ec19774bfc68a813 | 3ec5c49f29dd326ccbdebca93e5e403d2b673abee42265d3e484ee14ce8c8fda | +16 -8 |
| app/api/text_routes.py | 0c3f564702a3bb0d4eb4c4c10d1bb5401b5e9fb9c470516dd926ac0cd5a6568c | 8e1d42df86194f97cd4db69fabc37df50c850ae98ffd4be0b9cd3becc8e82bb8 | +2 -1 (comment only) |
| tests/test_s81_s10_fragrance_gate.py (EK2) | 2541b5d7506f60f73726b0a734bf8d87f6af327117e80a8d0bbf72550633eecc | 0824b692a6fcc8f8de0f838c5cadee598ff0ab58607a00f342ce33739f6eb8fe | +3 -6 |
| tests/test_s81_s10_gate_rows.py (docstring) | 47056816e2ff01a7a8c406d99bf706fc9996466fe05fb966eefadde3eff5aa05 | 7ef9716f15ec47ef409ab0219e1baacf26eb35cb3421111dfdfeaed2701803b5 | +4 -2 |
| CLAUDE.md (S81-10 block in place) | ce91be9dd3ce5fc1bf5f7181f65c897729ad8a7e33d4fc6ea0409c96e7c5a343 | 29b83aa746ef4863fd7ee38b722b5aa7875b6161f54c2390164933267a95532e | +3 -3 (CRLF kept: 1009 CRLF, 0 bare LF) |
| tests/test_s81_s10b_links_gate.py (RED, frozen) | 2df272ff30b54271ac72af0d05235fab3fc98be1372923b66bc6811dc16488d0 | same (disk and committed blob) | +1226 |
| tests/fixtures/s81_s10b_flag_off_golden.json (RED, frozen) | aebccaa6afedec3a4e9b541c4f7742b2b29c1ced2b7d4205296066358f745eae | same (disk and committed blob) | +996 |

EK2 LF blob sha256 of tests/test_s81_s10_fragrance_gate.py: before fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e (= git show c6fb6533:path | sha256sum), after ac6b061618319f5947ff4a89b22bc6fd83804eeb30655ebd3287f231d4db7656 (= git show HEAD:path | sha256sum; GC-3: my own comment text, not the prototype's 8750e81c...).
RED files re-hashed at start and end: identical to the gate shas.

## What was implemented (own code; the RED prototype diff read as a reference only)
- category_gate: _ROUTE_LABELS + url.post / url.get; post_resolve_refusal(..., classify=None, resolver_classified: bool = True) keyword-only; the branch: `no_real_chip and resolver_classified` -> the C11 reuse (unchanged for every S81-10 caller); `real chip and evidence` -> proceed (unchanged); else ONE classify (the real-chip no-evidence arm, unchanged, plus the no-chip arm when resolver_classified is False: no evidence shortcut, R-S10B-2). Docstrings: the module route list (six routes incl. the link verbs) + one sentence on the link path; the function docstring one sentence. No new import, no request_context substring.
- url_routes: `from app.services import category_gate as _category_gate` (module alias only); `_url_fragrance_gate_kwargs(request, route)` (flag reader first, then the admin mark); `async _url_refusal_budget(user, route)` (budget_subject, budget_state_async, log_budget_spent + 429 budget_detail, else GateDecision proceed carrying the subject); `_compare_with_deadline(..., fragrance_gate=None)` forwarding only when not None; `_compare_urls_metered(..., gate_route=None)` whose FIRST statement is the budget line (before the S81-06 consent gate and the reserve) and whose two compare calls take `**_gate_kw`; the POST / GET handlers compute `gate_kw` right after `v2 = url_mode_v2_enabled()` and pass `**gate_kw` at the four call sites. No route docstring, decorator or signature change.
- url_extraction_service: `compare_from_urls(..., *, fragrance_gate=None)` + one Args docstring entry; the gated block between the resolve and the write-back; `_url_gate_copy` (shallow copy with search_query "<brand> <name>"; an `other` page whose own text fires rule 1 takes that group) and `_url_fragrance_decision` (pair rule 1 over vision_texts(products); per-page copies; post_resolve_refusal over the copies with resolver_classified=False and a classify wrapper reading extraction_service.classify_category_llm at call time and recording the answer; the GC-1 form-override rewrite; the R-S10B-3 rewrite on a recorded canonical `fragrances` answer; record_refusal_async once, log_refused("post_extract", category), refusal_result). All gate imports function-local (flag-OFF module import set unchanged); no router / guarded_llm_create call (G4); no D03 / S15 / S81-05 needle.
- text_routes.py:558-560 comment rewritten in place ("The url_routes failure arm reaches it too (S81-10b: compare_from_urls returns it for a refused link pair)"); no code byte.
- EK2: the 4-line URL needle loop of P02 deleted; the EK1 comment (:1026 at base) rewritten to name EK1 and EK2; the gate-rows docstring :3-4 rewritten (names the EK2 sha, EK1's and the pre-EK1 sha as history).
- CLAUDE.md: the S81-10 block (:543-545) edited in place per spec 8 (a)-(h): (a) header parenthetical names S81-10b with its spec / review / rulings / gate; (b) six routes; (c) the link sentence after the camera sentence with R-S10B-1 (per-page rule 1 on copies carrying search_query), R-S10B-2 (no chip -> ONE A2b whatever the evidence; real chip -> evidence or ONE A2b), R-S10B-3 (the fragrances rewrite) and GC-1 (pair rule 1 whatever the LLM label); (d) the link golden (nineteen scenarios); (e) the S81-10b precondition removed; (f) the link canary items of RULINGS_S81_10B; (g) "the URL path is ungated until S81-10b" replaced by the link limits incl. L12 as GC-1 words it; (h) owner step (3) removed and renumbered (1)-(6). No new block, no new heading, names only.

## Runs (every [pyt] line; logs under scratchpad/S81-10b_green/)
[pyt] tag=s10b-green-red-off start=2026-11-04 07:20:41 end=2026-11-04 07:20:46 elapsed=5s bound=600s status=OK rc=0  -- 75 passed; [hermeticity] sentinel checked 75 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10b-green-red-on start=2026-11-04 07:20:54 end=2026-11-04 07:20:59 elapsed=5s bound=600s status=OK rc=0  -- ENABLE_FRAGRANCE_ONLY_GATE=true for that one call; 75 passed; hermeticity 75; netguard 0
[pyt] tag=s10b-green-s10 start=2026-11-04 07:20:59 end=2026-11-04 07:21:05 elapsed=7s bound=600s status=FAIL rc=1  -- S81-10 RED (with EK2) + gate rows: 175 passed, 1 failed = test_r06_production_lexicon_content (environmental, CRLF lexicon copy; red at base); hermeticity 176; netguard 0
[pyt] tag=s10b-green-pin-a start=2026-11-04 07:21:15 end=2026-11-04 07:21:25 elapsed=10s bound=1200s status=FAIL rc=1  -- 245 passed + R06; hermeticity 246; netguard 1 from 1 node (test_text_routes_error_mapping timeout row, neutralized host) = base
[pyt] tag=s10b-green-pin-b start=2026-11-04 07:21:25 end=2026-11-04 07:21:42 elapsed=18s bound=1200s status=OK rc=0  -- 959 passed; hermeticity 959; netguard 2 from 2 nodes (test_paid_route_metering, neutralized host) = base
[pyt] tag=s10b-green-pin-c start=2026-11-04 07:21:53 end=2026-11-04 07:22:31 elapsed=38s bound=1200s status=OK rc=0  -- 1419 passed; hermeticity 1419; netguard 0
[pyt] tag=s10b-green-pin-d start=2026-11-04 07:22:31 end=2026-11-04 07:23:08 elapsed=37s bound=1200s status=OK rc=0  -- 699 passed; hermeticity 699; netguard 24 from 2 nodes (s04 r42 / p08) = base
Pin sets a-d = 3,322 passed + R06 = the spec 1.10 base figures exactly (zero new failures).
[pyt] tag=s10b-green-comm-c00 start=2026-11-04 07:24:17 end=2026-11-04 07:25:41 elapsed=84s bound=1200s status=OK rc=0  -- 2146 passed, 1 skipped, 6 deselected; hermeticity 2147; netguard 69 from 47 nodes
[pyt] tag=s10b-green-comm-c01 start=2026-11-04 07:25:54 end=2026-11-04 07:26:23 elapsed=30s bound=1200s status=OK rc=0  -- 608 passed, 4 deselected; hermeticity 608; netguard 124 from 9 nodes
[pyt] tag=s10b-green-comm-c02 start=2026-11-04 07:26:36 end=2026-11-04 07:29:17 elapsed=161s bound=1200s status=OK rc=0  -- 3621 passed, 1 deselected; hermeticity 3621; netguard 109 from 9 nodes
[pyt] tag=s10b-green-comm-c03 start=2026-11-04 07:29:23 end=2026-11-04 07:30:38 elapsed=76s bound=1200s status=FAIL rc=1  -- 1532 passed + R06; hermeticity 1533; netguard 143 from 65 nodes
[pyt] tag=s10b-green-comm-c04 start=2026-11-04 07:30:45 end=2026-11-04 07:31:12 elapsed=27s bound=1200s status=OK rc=0  -- 387 passed; hermeticity 387; netguard 0
[pyt] tag=s10b-green-secret start=2026-11-04 07:31:12 end=2026-11-04 07:31:17 elapsed=5s bound=1200s status=OK rc=0  -- tests/test_secret_scan_static.py ALONE: 31 passed; hermeticity 31; netguard 0
[pyt] tag=s10b-green-ciorder start=2026-11-04 07:31:48 end=2026-11-04 07:32:25 elapsed=37s bound=1200s status=FAIL rc=1  -- CI-order set (13 files, collection order: test_error_middleware, test_paid_route_metering, test_retro_w1_9_429, test_s80_url_mode_v2, test_s81_s06_anthropic_router, test_s81_s09_device_quota, test_s81_s10_fragrance_gate, test_s81_s10_gate_rows, test_s81_s10b_links_gate, test_text_routes_error_mapping, test_url_compare_category, test_w4_13_flag_off_ledger, test_w4_13_measurement_truth; list in ci_order_set.txt): 1528 passed + R06; hermeticity 1529; netguard 3 from 3 nodes
[jest] tag=s10b-green-fences start=2026-11-04 07:32:42 end=2026-11-04 07:32:52 rc=1  -- node v24.11.1, jest 29.7.0 (node node_modules/jest/bin/jest.js --ci, by path from SmartCompareApp through the orchestrator's junction; @babel/core and .bin/jest present; timeout 1800): 14 suites, 13 passed; 240 tests, 236 passed, 4 failed = config/nativeBundle.w37 d5, k2, k4, k5 (the accepted base drift). Full jest NOT run (LC-7; no fence red beyond the drift).

## Comm set
- List: the RED's 108 files (comm_files.txt sha256 3e2570e2f4b52365abd81eee4cfe6dbdd34c24c8a801fb13113fc2bfb1e8d84b = specs/S81_10B_COMM_SET.txt), re-derived at HEAD with the RED's commset_10b.py (the union rule incl. the claude and client-scan classes) plus a grep for my new symbols (_url_fragrance_gate_kwargs, _url_refusal_budget, _url_fragrance_decision, _url_gate_copy, resolver_classified) and the edited test module test_s81_s10_gate_rows: 131 raw hits = the RED's 130 raw hits + tests/test_s81_s10b_links_gate.py (the unit RED file, run separately as the unit gate); the only new-symbol referencer is the RED file; no importer of test_s81_s10_gate_rows exists. ADDITIONS: none. So the set and the base sha match the cache.
- Base: the CACHED record harness/base_records/c6fb65336deab4f48275b13d3847e0f42b298984/3e2570e2f4b52365abd81eee4cfe6dbdd34c24c8a801fb13113fc2bfb1e8d84b.txt REUSED (LC-6); no base run, no scratch worktree, nothing appended.
- HEAD: 107 files in 5 chunks (25/25/25/25/7, alphabetical) + tests/test_secret_scan_static.py alone: 8,325 passed, 1 skipped, 1 failed.
- HEAD FAILED (sorted) = tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content = base FAILED. comm -13 (branch-only-new): EMPTY. R06 is identical both sides (GC-6; the worktree lexicon copy is CRLF, so R06 stays red).

## Cheap gates (GC-8 a)
- ruff check --select E9,F63,F7,F82 --no-cache over the 7 python files: All checks passed. Full-rule ruff (informational) on the three app files: no new finding vs the base bytes (url_routes 24/24, url_extraction_service 112 -> 110 lines of output, category_gate 0/0).
- py_compile: the 7 python files compiled. json.loads on the golden: ok.
- Added-line bytes > 127 over the whole diff: 0; the PR body and report are generated files outside the repo (the PR body ends with the required robot-emoji line).
- git diff --stat: no whole-file diff (CLAUDE.md 3 / 3 lines; every CRLF file keeps CRLF).
- Greps on url_routes.py and url_extraction_service.py: 0 hits for ENABLE_FRAGRANCE_ONLY_GATE, request_context, deny_hosts, denied_source, ENABLE_DATA_GUARDS_V2, robots_registry, kb_merchants, device_key_pepper, x-ai-consent-version, x-compare-request-id, header_state, "from app.services.category_gate import".
- Hook test files not run (no .githooks change). Mutation table not re-run (the adversaries re-run it).

## Pin changes
Exactly ONE sanctioned pin change: E1 = EK2 (P02's URL clause). No other pin moved (the 1.10 pin sets, the comm set and the CI-order set measured). T23 green (pin set c).

## Deviations
- DV1: the CLAUDE.md header parenthetical (spec 8 a) is dated 2026-11-04 (the build day of the rulings, RED and GREEN) instead of the spec's 2026-11-02, and names the rulings / gate ids; (d) says nineteen scenarios (UG01-UG19 after R-S10B-12), not the spec's eighteen; (g) carries L12 as GC-1 words it plus the R-S10B-2 / -3 / C8 limits.
- DV2: the per-page rule 1 calls category_gate.evaluate([text]) on the copy's "<brand> <name>" text directly instead of evaluate(vision_texts([copy])) (the same string; the prototype's form), so the copy helper reads no gate helper beyond evaluate.
- DV3: the category_gate branch was restructured (no_real_chip and resolver_classified -> reuse; real chip and evidence -> proceed; else ONE classify) rather than nesting the prototype's inner if; resolver_classified=True is the base branch byte-for-byte in behaviour (the S81-10 RED + gate rows, R18 (c) and pin sets a-d green).
- DV4: the CI-order set is not named by any file; I ran the 13 suites around the unit (the RED and the S81-10 files, the URL, metering, device-quota, router, error-mapping and W4-13 suites) in one process in CI collection order; listed above and in ci_order_set.txt.
- DV5: the fence run used the 14 files the common brief names (clipboardFallbackService.test.ts only; the sibling clipboardFallbackService.edges.test.ts is not in the named list and was not run).

## Open questions
- Q1: R-S10B-3 rewrites category_used on the LAST recorded A2b answer; post_resolve_refusal makes at most one classify call per decision, so last == only. The rewrite fires on any arm (R-S10B-3's words): with the chip `fragrances` it is a no-op (the resolver already set the chip), and with a non-fragrance chip (e.g. `electronics`, the R08 shape) whose blind pair the A2b calls `fragrances` the pair is compared as fragrances instead of under the chip. Confirm that reading.
- Q2: the fragrances rewrite leaves category_switched / original_category of the resolver untouched (the URL path discards them, as the form override does): confirm no reader needs them on the link path.

## NOT MEASURED
- The full jest suite (LC-7: the last round runs it). The hook test files. The mutation table on these bytes (the adversaries').

## Paths
- Report: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_green/S81-10b_GREEN_REPORT.md
- PR body draft: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/0e351457-2b4f-4512-a571-3ecd2f577f5c/scratchpad/S81-10b_green/PR_BODY.md
- Logs, chunk lists, comm_head.txt / .tsv, ci_order_set.txt, jest_fences.log, the CLAUDE.md edit script: the same folder. Before copies: scratchpad/S81-10b_green_before/.
