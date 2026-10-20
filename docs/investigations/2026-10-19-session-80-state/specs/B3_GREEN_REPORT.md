# B3 GREEN REPORT: VISION-IDENTITY-V2 (ENABLE_VISION_IDENTITY_V2)

- Unit B3, flag ENABLE_VISION_IDENTITY_V2 + knob VISION_TIMEOUT_SECONDS. Worktree C:/Users/SynAckITPC/Documents/AI/sc-s80-b3, branch feature/s80-b3-vision-identity-v2 (created with the one allowed `git checkout -b`), base 81df2b641454e0301cca51a3ba01bf8ef3d7e649.
- HEAD 764d44162dd83563dc5c9aa930dcb9c192f35f89 (one commit through the pre-commit hook; hook "All checks passed!"). Not pushed, not rebased, no PR.
- Window 2026-10-20 06:37 -> 07:35 AST. Notes and every artifact: <scratchpad>/B3_green/ (notes.md, logs, comm_logs/, mut/, comm_head.py, mutate_green.py, PR_BODY.md). Byte copies before any edit: <scratchpad>/B3_green_before/ (SHA256SUMS.json + tests__test_regression_gate_diff.py).
- Inputs read in full: s80-common.txt, PLAN_S80.md sections 0-1, RULINGS_R0.md, RULINGS_BATCH1.md (Common + B3), GATE_B3.md, .qa-s80/B3_UNIT_SPEC.md, .qa-s80/B3_SPEC_REVIEW.md, B3_RED_REPORT.md, the RED prototype diff (reference only; every hunk re-derived and written as GREEN's own code).
- RED file re-hash: start 36b78a40...f15e, end 36b78a40...f15e (on disk and `git show HEAD:` blob identical; LF; untouched). Only ONE RED file exists (the brief says "the two RED files" but names one; GATE_B3 names one).
- No .env read, no secret printed, no network, no personal values; production flag state not probed (the flag is a new name, unset by construction).

## Files (final sha256 of bytes on disk; numstat vs base)

| file | +/- | sha256 before | sha256 after |
|---|---|---|---|
| app/services/openai_service.py | 451/0 | 71bed08a...99acb | ff15a9fe9d447dcfadc7df99578e3d601820e7f7964286e45a61c50c45431a3d |
| app/api/image_routes.py | 55/8 | 3813cb9a...95ef | 4502ff0e9a816be33e392e9e21d20e7fea1f14f48d60bb03e2017dde846b19ae |
| app/services/structured_comparison_service.py | 26/2 | 7db53e39...6d2 | deaed222fc36d5aa5785afe832fb4951f9de8ab4b42c3e341d0c0652a8aa3409 |
| tests/test_camera_vision.py | 4/12 | ecd8e497...1d2e | 89d87f56556b0b20072d953121bc42b438f0e83892c802127827b1d9e01a45c0 |
| tests/.pre_impl_failures.txt | 13/7 | ad2a9a78...6a8 | 1b5b9104bebf8dec7cf7de9f35106dc6511083f98e18d3dfe7ebaa8b743ca0e1 |
| tests/PRE_IMPL_FAILURE_BASELINE.md | 8/11 | e8a548a6...a9f | c24661fee564142afdcf6eed4797af956e0c95a68ad3f486a43c7dfa87c171e6 |
| tests/test_model_config_enforced.py | 1/1 | b3813ad6...f19b | 86f13cb641fe352f84dba44fbf33dde26a4f8fc0e48214dd9e063b402c99580b |
| tests/w4_11_prompt_digest_recorder.py | 1/1 | 8c90ef5b...a826 | 65735b08e23e9f1e2d4dcc8f29b63abaec67330b8115c6a7729d5fb7ad49a387 |
| tests/test_prompt_fence.py | 1/1 | d5474744...5930 | 7ab3f9e0e024a40eb2fad31ad2b1f358d3982f86e78a484c31c2f125496b6e84 |
| tests/test_s71_u13_compare_auth_required.py | 1/0 | 289f24f5...4121 | 9d5ef1e4f41eb1b0b26b20e45be95d790b5402f424c787a1199aed76e474731a |
| tests/test_regression_gate_diff.py | 6/1 | 0021fcee...c3fd | 7f7d2b33343ee5cbfa6f70a52ffe545af7f8d7e38eb086386b2cba20284347a3 |
| CLAUDE.md | 7/4 | ab7ec7dd...7415 | c74f9158ecc56ede0b52dabd109d732c87c8ac90158738820529fd7d18b53a5b |
| tests/test_s80_b3_vision_identity_v2.py (RED, frozen) | 1538/0 | 36b78a40...f15e | 36b78a404deefbc4fbea66b2d75574f203346a8e53550a3ddf04d3550e4af15e |

Byte hygiene: high-byte counts unchanged in every existing file (all additions ASCII; .pre_impl_failures.txt 45 -> 42 because the deleted bullet carried an em dash); every existing file CRLF with 0 bare LF; the RED file LF. The VISION_PROMPT_V2 string equals the spec 2.2 block character for character (3,170 chars, ASCII, sha256 7d7f2c83b11dfb8b05cb9541379b798bcaa6fe0cfeb16526bf38e8966723dd24). Added-line sweep: @gmail 0, +973 0, sk- 0, eyJ 0, PRIVATE KEY 0, credentialed URL 0, AKIA 0; the two 8-digit hits are a pre-existing UUID on an edited CLAUDE.md line and the VISION_PROMPT_SHA_OFF literal.

## Implementation (contract as amended)

- openai_service.py: `import asyncio, math, os`; constants `_VISION_TIMEOUT_DEFAULT` 20.0, `_VISION_V2_MAX_TOKENS` 1000, `VISION_CATEGORY_KEYS` (A2b order), `VISION_V2_PUBLIC_KEYS`, `VISION_V2_INTERNAL_KEYS`, `VISION_PROMPT_V2` (category line built from VISION_CATEGORY_KEYS), `VISION_RESPONSE_FORMAT_V2` (category anyOf, GB-3); readers `vision_identity_v2_enabled` (house idiom) and `vision_timeout_seconds` (WARNING naming the variable on garbage / non-finite / <= 0); helpers `public_vision_products`, `_normalize_vision_products_v2` (lazy canonicalize_category import), `_select_vision_products_v2` (one per index, two for one image, unpaired after paired in reply order, no cap), `_vision_finish_label` (literal / "None" / type name), `_vision_image_parts`, `_identify_products_v2` (knob read once, `asyncio.wait_for` around `guarded_llm_create` with `response_format=` and the two kwargs helpers, WARNING on expiry then re-raise, `_log_cache_telemetry`, triage: refusal or non-str content -> WARNING + `LLMUnavailableError("vision returned no content")`, length -> parse failure, JSON / shape failures -> parse failure, counts INFO line, usage-None-tolerant cost). `identify_products` gains the flag-first branch; the V1 body is untouched.
- structured_comparison_service.py: `_vision_identity_fields` (presence-gated on `_is_product`, five keys incl. `_vision_image_index`, a NEW features list); one splat on each twin's `"_vision": True` line (not reflowed, C12/R15).
- image_routes.py: widened import + `get_user_preferences` import; `_camera_user_preferences` (fail-soft, WARNING type name only); the flag read once inside the comparison try right before `compare_from_text`, conditional `user_id` / `user_preferences` kwargs; `public_vision_products` at the six wire sites (need_second_product, both metadata branches, both envelope call sites, comparison_failed); the list passed into `compare_from_text` stays un-stripped.

## Runs (every pytest through pyt.py, one process at a time)

```
unit file, flag unset (first):  105 passed, 10 warnings in 11.56s; [hermeticity] 105; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3green-unit-off-1 start=2026-10-20 06:44:55 end=2026-10-20 06:45:10 elapsed=15s bound=600s status=OK rc=0
unit file, ENABLE_VISION_IDENTITY_V2=true (runner env only):  105 passed; [hermeticity] 105; [netguard] blocked 0
[pyt] tag=b3green-unit-on-1 start=2026-10-20 06:45:18 end=2026-10-20 06:45:39 elapsed=21s bound=600s status=OK rc=0
camera_vision (E1-E3 proof, pre-commit):  25 passed, 1 deselected; [hermeticity] 25; [netguard] blocked 0
[pyt] tag=b3green-camera-vision start=2026-10-20 06:46:28 end=2026-10-20 06:46:46 elapsed=18s bound=600s status=OK rc=0
CI-order set (29 files, pre-commit):  1327 passed, 1 deselected; [hermeticity] 1327; [netguard] blocked 29 attempt(s) from 23 node(s)
[pyt] tag=b3green-ciorder-1 start=2026-10-20 06:48:22 end=2026-10-20 06:50:47 elapsed=145s bound=1200s status=OK rc=0
E8 + CLAUDE.md readers (rgd, ci_gates, behavior_dimension_translation):  111 passed, 1 skipped (pre-existing QA-output skip); [hermeticity] 112; [netguard] blocked 0
[pyt] tag=b3green-rgd-and-claude-readers start=2026-10-20 07:16:17 end=2026-10-20 07:16:37 elapsed=20s bound=600s status=OK rc=0
unit file, flag unset (final bytes, after the mutation restore):  105 passed; [hermeticity] 105; [netguard] blocked 0
[pyt] tag=b3green-unit-off-final start=2026-10-20 07:27:42 end=2026-10-20 07:27:47 elapsed=5s bound=600s status=OK rc=0
unit file, flag ON (final bytes):  105 passed; [hermeticity] 105; [netguard] blocked 0
[pyt] tag=b3green-unit-on-final start=2026-10-20 07:27:48 end=2026-10-20 07:27:53 elapsed=5s bound=600s status=OK rc=0
CI-order set at HEAD 764d4416 (30 files = the 29 + test_regression_gate_diff.py):  1359 passed, 1 skipped, 1 deselected; [hermeticity] 1360; [netguard] blocked 29 attempt(s) from 23 node(s)
[pyt] tag=b3green-ciorder-head start=2026-10-20 07:29:06 end=2026-10-20 07:29:49 elapsed=43s bound=1200s status=OK rc=0
camera_vision at HEAD 764d4416:  25 passed, 1 deselected, 11 warnings in 4.74s; [hermeticity] 25; [netguard] blocked 0
[pyt] tag=b3green-camera-vision-head start=2026-10-20 07:29:59 end=2026-10-20 07:30:05 elapsed=6s bound=600s status=OK rc=0
gen_baseline_mirror --check at HEAD: "OK: mirror is current (8 nodes)."
```

Identity pins of spec 4.2 inside the CI-order set (all green): test_image_identify_llm_unavailable_s69, test_retro_w2_1 (W2-1 camera body pins), test_paid_route_metering, test_m13_26_image_error_envelope, test_cost_meter_s74, test_w4_13_measurement_truth, test_w4_13_flag_off_ledger, test_s71_u13_compare_auth_required (T23 unchanged), test_m13_03_paid_work_gating, test_b2_strict_optional_auth, test_comparison_id_echo, test_security_regression, test_text_error_envelope_no_raw_exception, test_logger_no_query_leak, test_sentry_channels_u8d_unit, test_openai_key_log_hygiene_s69, test_model_config, test_u3c_store_false_pin, test_prompt_fence, test_s75_fanout_identity (FY25), test_explicit_pair_category, test_ci_gates, test_backend_cleanup, test_m18_openai_tpm_sizing, test_legal_docs_u8.

Lint: `python -m ruff check --select E9,F63,F7,F82 --no-cache` on the ten changed Python files: "All checks passed!"; `py_compile` rc 0. Full default ruff on the three source files: identical per-rule counts base vs HEAD (openai_service W293 x4; image_routes B008 x2, B904 x2, F401 x2; scs B905 x2, E702 x1, F401 x13, F841 x2), so no new finding.

## Comm set (zero-regression gate)

- HEAD list: <scratchpad>/B3_green/comm_head_list.txt, 248 files, 10 chunks (9 x 25 + 23), sha256 708a4e63fd6e91cb2046d4316ce5a5cbedd4e5c05ac2d831f58b3d08e995d997; reasons comm_head_reasons.tsv (modref 205, symbol 123, green_symbol 15, srcscan 47, client_scan 23, claude_md_reader 2, red_base_list 246). Rule: the RED module + symbol greps UNION a GREEN symbol grep (public_vision_products, vision_identity_v2_enabled, _vision_identity_fields, _camera_user_preferences, VISION_TIMEOUT_SECONDS, ENABLE_VISION_IDENTITY_V2, VISION_PROMPT_V2, VISION_RESPONSE_FORMAT_V2, VISION_CATEGORY_KEYS, get_user_preferences) UNION source-scanning pins UNION CLAUDE.md readers UNION SmartCompareApp scanners, MINUS test_precommit_hook*.py, the unit file INCLUDED, UNION the RED base list (246). Head-only: tests/test_auth_preference_toggles_w314.py, tests/test_s80_b3_vision_identity_v2.py; RED-only: none. NETWORK_FLAKY_EXCLUDE nodes deselected per chunk (as RED).
- Chunk lines: see PR_BODY.md (c01..c10 with [pyt] lines; c07 is the final re-run, its first pass kept as comm_logs/b3green-comm-head-c07.prefix.log).
- HEAD FAILED/ERROR set (4): test_page_scraping x2 (baseline rows), test_prompt_truth x2 (cold-tiktoken ERRORs). Base set (RED, 7): those 4 + the three camera_vision rows. `comm -13 base head` = EMPTY. Fixed: the three camera_vision rows.
- First pass: chunk 7 showed tests/test_regression_gate_diff.py::test_load_baseline_reads_committed_file branch-only-new (it asserted a camera_vision id is a baseline member); fixed by E8 and re-run (final c07: 885 passed, 2 errors = the tiktoken pair).

## Mutation spot-check on the GREEN bytes (beyond the procedure, for evidence)

14 mutants, lock <worktree>/.qa-mutation.lock held and removed, byte copy -> exact edit (matched once) -> unit file via pyt.py bound 600 -> restore -> sha256 compare: 14 KILLED (AssertionError; no KeyError/AttributeError/TypeError E-lines), 14 restores verified, final sha256 of the three source files equal to the pre-mutation snapshot (sha256sum -c OK).
G1 flag-first removed -> P1 x7, P2 x7, P3, P3b, P10; G2 forwarding ungated -> P6 x2; G3 metadata strip removed -> R17 x2, R18, R19, R20; G4 unpaired first -> R8, R8c, R8d; G5 one image keeps one -> R6b; G6 no feature cap -> R9; G7 no _vision_image_index -> R13 x2, R14; G8 wait_for unbounded -> R10, R10b; G9 raising prefs propagates -> R16b, P8 x3; G10 unknown confidence medium -> R9; G11 None content -> dict -> R4 x3, R4b; G12 knob read before flag -> P1 x7, P2 x7, R10; G13 prefs forwarded when not completed -> R16b; G14 missing is_product -> False -> R9. [pyt] lines: mut/results.json (e.g. `[pyt] tag=b3green-mut-G1 start=2026-10-20 07:23:53 end=2026-10-20 07:24:01 elapsed=9s bound=600s status=FAIL rc=1` ... `[pyt] tag=b3green-mut-G14 start=2026-10-20 07:26:58 end=2026-10-20 07:27:05 elapsed=7s bound=600s status=FAIL rc=1`).

## Counts

RED rows green at HEAD: 69/69 (RED report numbering: R1..R23 incl. variants); PIN rows green: 36/36; unit file 105/105 in both flag states; GREEN mutants 14/14 KILLED.

## Deviations (each deliberate, for the gate)

- D1 E8 (unlisted pin change): tests/test_regression_gate_diff.py:183 asserted `any("test_camera_vision.py" in i for i in ids)` over the committed baseline; the R-A14 prune makes it false. Rewritten minimally to assert `test_auth_interceptor.py` is a member and `test_camera_vision.py` is absent, with a dated comment. Neither the spec 4.1 table nor the RED prototype's 27-file CI-order set covered it; the comm set caught it.
- D2 Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, not the brief's `Claude Fable 5.1`. This agent's system prompt states the model is claude-opus-5-5; I did not write a model claim I cannot stand behind. The orchestrator verifies the model from the first transcript and may amend the trailer (and should check its subagent-model pin) if its record differs.
- D3 The PRUNED paragraph is a dated sibling of the 2026-09-02 PRUNED paragraph (header of .pre_impl_failures.txt), and the camera_vision bullet was deleted from "Rows NOT removed", instead of writing the paragraph inside that list; wording as spec 3.5 with no `::` on any comment line (GB-6); proof cites the pyt tag (the HEAD sha did not exist yet).
- D4 CLAUDE.md: one more in-place rewrite beyond spec 3.9: the FULL REVIEW block's "count is the one stated in **Tests** (11, recounted 2026-10-03)" -> "(8 since B3, session 80, 2026-10-20; 11 before)" (principle 5). Line 502 also notes the two GB-7 rows observed passing on this box.
- D5 CLAUDE.md:502 is written at base as the final intended text carrying `openai_service.py:81` (B3-R4); main 4a38ce93 (#363) edited the same line, so the orchestrator's rebase will conflict there: take B3's line. The row anchor follows G-2 (after the B3-B block); B1's row lands first.
- D6 CI-order set = spec 7.4 list UNION the RED 27 UNION tests/test_s75_fanout_identity.py and tests/test_explicit_pair_category.py (spec 4.2 identity pins) = 29 files pre-commit; at HEAD + test_regression_gate_diff.py = 30. Run twice (pre-commit and at the HEAD sha) so the HEAD line exists.
- D7 Comm set 248 = RED 246 + 2 head-only files (rule re-derived with the GREEN symbols).
- D8 The task named <scratchpad>/B3_red/; the RED artifacts are in <scratchpad>/B3red/ (read from there).
- D9 `git add -N` was run once on the RED file before the added-line sweep (intent-to-add; no content change); the commit used `git add <paths>` + `git commit -m ... -- <paths>`.

## Questions for the gate

- Q1 Accept E8 (D1) as a deliberate pin change of this unit?
- Q2 tests/test_camera_vision.py's three mocked nodes do not clear ENABLE_VISION_IDENTITY_V2 (spec 3.4: nothing else in that file); with the flag in a developer env they take the V2 path (a MagicMock message has a truthy `refusal` -> LLMUnavailableError) and go red. Recorded as stated limit 14 in the row; add the flag to that file's env hygiene in a follow-up, or here?
- Q3 The header of tests/.pre_impl_failures.txt (lines 2-3) says '#' lines are ignored by parse_failure_ids, which is false (GB-6); left as is (hardening regression_gate_diff is the separate follow-up GB-6 names).
- Q4 D2: confirm the trailer / model record.

## NOT MEASURED

- The comm set at base was not re-run by GREEN (the RED base run over the same 246 files is the base side; the two head-only files passed at HEAD, so they cannot contribute a branch-only-new id). No scratch worktree was created.
- Live behaviour (structured outputs with image input, Arabic transliteration, 1-based index rate) is a canary item.

## git status --short (worktree, at the end)

(empty: everything committed at 764d4416; no untracked file, no .qa-mutation.lock; no python process with a b3green / sc-s80-b3 command line)
