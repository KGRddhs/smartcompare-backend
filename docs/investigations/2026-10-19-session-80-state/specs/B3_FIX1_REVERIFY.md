# B3 VISION-IDENTITY-V2 fix round 1 -- RE-VERIFIER REPORT (correctness lens)

- Unit B3 (ENABLE_VISION_IDENTITY_V2 + knob VISION_TIMEOUT_SECONDS). Worktree
  C:/Users/SynAckITPC/Documents/AI/sc-s80-b3, branch feature/s80-b3-vision-identity-v2.
- Window 2026-10-20 10:16 -> 12:00 AST (past the 90-min budget by the mandated hook re-run).
- HEAD verified at start (10:16 AST) and at end: 7b1e3ecf81ef2bb24ce08e84d89c0069f98b386a.
  `git status --short` of the real worktree empty at start and end; no .qa-mutation.lock there.
  The real worktree was never written (pytest runs only, read-only; __pycache__ is gitignored).
- `git diff 764d4416 HEAD --numstat`: CLAUDE.md 2/2, tests/test_s80_b3_vision_identity_v2.py 352/0.
  No app/ file changed in the fix round.
- Probes and mutants ran in MY detached scratch worktree <scratchpad>/B3_fix1_adv at 7b1e3ecf
  (removed at the end with `git worktree remove --force`; absent from `git worktree list`) (the RED file's real LF bytes copied in; app/services/openai_service.py ff15a9fe...1a3d,
  app/api/image_routes.py 4502ff0e...19ae, structured_comparison_service.py deaed222...3409,
  the RED file e8b2c9c1...8642, test_camera_vision.py, w4_11_prompt_digest_recorder.py and
  CLAUDE.md all sha256-equal to the real worktree before the first mutant; the two mutated
  files sha-equal after every restore and at the end, before removal).
- No .env read, no secret printed, no network (netguard on every run), no production probe;
  production flag state not read (a new name). No personal values. Pure ASCII + LF in every
  file I wrote. Agent model: claude-opus-5-5.

## VERDICT: SOUND (0 blocking, 0 major, 2 minor, 2 nits)

The fix round does what RULINGS_FIX1_B3 asks. The RED file is append-only (the 65,236 B at
764d4416 are a byte prefix of the 80,670 B at HEAD; sha256 e8b2c9c1...8642 on disk == the HEAD
blob; 0 bytes > 127; 0 CR). Unit file 131/131 flag unset AND flag ON. All nine named mutants
(XB1-XB3, Y1-Y3, Z1-Z3) plus BM1 and three extras of mine (XB1c, Z4, Z5) are KILLED by
AssertionError only, each by the row the ruling names. The CI-order set (plus the F3-2 file),
test_price_fallback_may_decline.py and the two CLAUDE.md readers are green. VISION_PROMPT_SHA_ON
equals sha256 of the AST-evaluated constant AND of the spec 2.2 block (independently measured).
Every adversary MAJOR (2) and MINOR (10 + 8) of the previous round is closed or recorded. The two
minors below are documentation wording; neither is a behaviour or pin defect.

## Hook test files (F3-5: the not-dash set ALONE, the TIMEOUT rule): NOT MEASURED

Run 1 (alone; no other pytest on the box, checked by process list): TIMEOUT at the 1800 s bound
after 51 of 167 not-dash nodes, all 51 passed (test_precommit_hook.py 31/31 of its not-dash
nodes, test_precommit_hook_phase_b.py 20), 0 failed. Re-run once, alone: TIMEOUT again after 26
nodes (19 passed, 7 F in test_precommit_hook.py at collection positions 8, 14, 15, 16, 19, 20,
21: `sh-red_staged_black_dirty_allowlisted_with_clean_working_copy_refused`,
`sh-red_env_fallback_to_common_dir_from_linked_worktree`, `sh-red_black_absent_warns_and_passes`,
`sh-red_skill_md_bare_colon_value_refused`, `sh-red_staged_ok_with_broken_working_copy_passes`,
`sh-red_path_with_space_passes`, `sh-red_non_ascii_path_passes`). All seven PASSED in run 1 on
the identical bytes (HEAD 7b1e3ecf, same worktree) about 40 minutes earlier, so they read as the
slow-spawn load class (the box spawned a `sh -c true` in about 1.75 s and ran ~35-70 s per hook
node); the failure details were lost with the killed process tree. Per the rule, recorded NOT
MEASURED, not a failure. B3 edits no `.githooks` file and the hook test files read none of B3's
changed files; the fix commit itself passed the hook.

## Minors / nits (for the orchestrator)

- RV-min-1 (doc truth; CLAUDE.md row limit (14) and PR-body limit 15). "the netguard ratchet
  would report about 50 new egress nodes" is not what the ratchet would do. The ~50 nodes'
  attempts are `socket.create_connection neutralized.supabase.invalid:443` (both adversaries:
  "sentinel-neutralised" / "every extra attempt sentinel-class"); scripts/netguard_ratchet.py
  classifies a `*.invalid` / `neutralized.*` host as `sentinel` (`_classify_target`, :41-:57) and a
  NEW node whose classes do not include `egress` prints a WARNING line and exits 0 (:13-:17,
  :116-:136; CI fails only on a NEW node whose classes include `egress`). Suggested wording: "the
  netguard ratchet would print about 50 new sentinel-only WARNING lines (not a CI failure)". The
  wrong word came from correctness min-5 and was copied into ruling F3-4; the substance of the
  limit (never export the flag in a test environment) stands.
- RV-min-2 (doc, PR-body defect table, F3-5 row R12). The R12 row reads "R12 x15 (`TRUE` /
  " true " / ON / 1 / yes true; unset / "" / false / 0 / no / off / garbage / "tru e" false)";
  that enumerates 13 of the 15 parameters (`"true"` and `"on"` are missing from the list). The
  count x15 is right (test file :1082-:1087). Wording only.
- RV-nit-1 (CLAUDE.md :505, the CI-GREEN bullet, unchanged by this round). "`TypeError` at
  `openai_service.py:81`, the `cached_tokens > 0` line" is the base-81df2b64 line; at B3 HEAD the
  `if cached_tokens > 0:` line is :84 (B3 added `import asyncio`, `import math`, `import os`).
  The sentence is past tense and ruling B3-R4 mandated keeping `:81`; it names the symbol too.
  Optional: "(`:81` at 81df2b64)".
- RV-nit-2 (record). The fix commit's trailer is `Co-Authored-By: Claude Opus 5.5` (fix report D1;
  GREEN's D2 likewise): the agents ran on claude-opus-5-5, not the Fable pin named in the common
  brief. A record question for the orchestrator's model ledger, not a defect in the bytes.

## Mutation table (re-applied on sha-verified byte copies in my scratch worktree)

Harness <scratchpad>/B3_fix1/reverify/rv_mutate.py (written independently of the fix agent's
mutate_fix1.py): sha-check the target against the HEAD sha, shutil.copyfile byte copy, exact
edit with every anchor matching exactly once (CRLF preserved; block moves re-indented by 4 when
they leave the compare `try`), the unit file through pyt.py with ENABLE_VISION_IDENTITY_V2
removed from the runner env, restore from the copy, sha256 compare (stop on mismatch).
Mutation lock <scratch>/.qa-mutation.lock held for each batch and removed. Every failure is an
AssertionError (no other `E   <Type>` line, no pytest ERROR), every expected row failed.

| id | mutant | failed rows (exactly) | verdict |
|---|---|---|---|
| XB1 | route personalisation block (`_compare_extra` + flag-gated `_camera_user_preferences`) moved to just BEFORE `vision_ledger = start_openai_ledger()` | XB1 x8 (all eight exits), XB1b, Y2b x2 (11) | KILLED |
| BM1 | the same block moved to just AFTER that line (engineering BM1) | the same 11 | KILLED |
| XB1c (mine) | the same block moved to just after `vision_cost = vision_result.get("cost", 0)` (after the vision try, the parse-error exit and moderation; before the 0- / 1-product exits) | XB1[zero_products_action_error], XB1[need_second_product] (2) | KILLED |
| XB2 | `_parse_failure` + the `finish_reason == "length"` check moved above the refusal / no-content check | XB2, XB2b (2) | KILLED |
| XB3 | the flag-first `if vision_identity_v2_enabled(): return await _identify_products_v2(...)` moved below the V1 content build (before `# Call OpenAI Vision API`) | XB3[true-1], [true-2], [true-3] (3; [None-2] stays green, as designed) | KILLED |
| Y1 | `_log_cache_telemetry(response, "identify_products")` dropped from the V2 path | Y1 (1) | KILLED |
| Y2 | `except asyncio.TimeoutError:` -> `except Exception:` | Y2 x2, Y2b x2 (4) | KILLED |
| Y3 | `if refusal or not isinstance(raw_content, str):` -> `if not isinstance(raw_content, str):` | Y3 (1) | KILLED |
| Z1 | the no-invention rule (3 source lines) deleted from VISION_PROMPT_V2 | Z1_Z3 sha, substrings [no_invention], [confidence_low] (3) | KILLED |
| Z2 | "from 0 ... (image_index 0 is the first image)" -> "from 1 ... (image_index 1 ...)" | Z1_Z3 sha, [numbered_from_0] (2) | KILLED |
| Z3 | "the 0-based number" -> "the 1-based number" | Z1_Z3 sha, [zero_based] (2) | KILLED |
| Z4 (mine) | `confidence to "low"` -> `confidence to "medium"` | Z1_Z3 sha, [confidence_low] (2) | KILLED |
| Z5 (mine) | "do NOT invent one from its shape" -> "you may infer one from its shape" | Z1_Z3 sha, [no_invention] (2) | KILLED |

13 applied, 13 KILLED, 0 survivors. Raw records: <scratchpad>/B3_fix1/reverify/mut_results.jsonl;
logs <scratchpad>/B3_fix1/reverify/mut_logs/; byte copies <scratchpad>/B3_fix1/reverify/mut_backup/.

```
[pyt] tag=b3rv-scratch-baseline start=2026-10-20 10:31:25 end=2026-10-20 10:32:00 elapsed=35s bound=600s status=OK rc=0   (131 passed; [hermeticity] 131; [netguard] blocked 0)
[pyt] tag=b3rv-mut-XB1 start=2026-10-20 10:32:21 end=2026-10-20 10:33:08 elapsed=47s bound=600s status=FAIL rc=1   (11 failed, 120 passed)
[pyt] tag=b3rv-mut-BM1 start=2026-10-20 10:33:11 end=2026-10-20 10:34:02 elapsed=51s bound=600s status=FAIL rc=1   (11 failed, 120 passed)
[pyt] tag=b3rv-mut-XB1c start=2026-10-20 10:34:06 end=2026-10-20 10:35:09 elapsed=63s bound=600s status=FAIL rc=1  (2 failed, 129 passed)
[pyt] tag=b3rv-mut-XB2 start=2026-10-20 10:35:14 end=2026-10-20 10:35:25 elapsed=11s bound=600s status=FAIL rc=1   (2 failed, 129 passed)
[pyt] tag=b3rv-mut-XB3 start=2026-10-20 10:35:39 end=2026-10-20 10:35:55 elapsed=16s bound=600s status=FAIL rc=1   (3 failed, 128 passed)
[pyt] tag=b3rv-mut-Y1 start=2026-10-20 10:35:57 end=2026-10-20 10:36:15 elapsed=19s bound=600s status=FAIL rc=1    (1 failed, 130 passed)
[pyt] tag=b3rv-mut-Y2 start=2026-10-20 10:36:17 end=2026-10-20 10:36:23 elapsed=6s bound=600s status=FAIL rc=1     (4 failed, 127 passed)
[pyt] tag=b3rv-mut-Y3 start=2026-10-20 10:36:23 end=2026-10-20 10:36:30 elapsed=7s bound=600s status=FAIL rc=1     (1 failed, 130 passed)
[pyt] tag=b3rv-mut-Z1 start=2026-10-20 10:38:20 end=2026-10-20 10:38:25 elapsed=6s bound=600s status=FAIL rc=1     (3 failed, 128 passed)
[pyt] tag=b3rv-mut-Z2 start=2026-10-20 10:38:27 end=2026-10-20 10:38:45 elapsed=18s bound=600s status=FAIL rc=1    (2 failed, 129 passed)
[pyt] tag=b3rv-mut-Z3 start=2026-10-20 10:38:47 end=2026-10-20 10:39:02 elapsed=15s bound=600s status=FAIL rc=1    (2 failed, 129 passed)
[pyt] tag=b3rv-mut-Z4 start=2026-10-20 10:39:02 end=2026-10-20 10:39:15 elapsed=12s bound=600s status=FAIL rc=1    (2 failed, 129 passed)
[pyt] tag=b3rv-mut-Z5 start=2026-10-20 10:39:16 end=2026-10-20 10:39:33 elapsed=17s bound=600s status=FAIL rc=1    (2 failed, 129 passed)
```

## Runs (every pytest through pyt.py, one at a time; flag state in the runner env only)

```
unit file, real worktree, flag unset: 131 passed, 10 warnings; [hermeticity] sentinel checked 131 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3rv-unit-off start=2026-10-20 10:21:58 end=2026-10-20 10:22:31 elapsed=34s bound=600s status=OK rc=0
unit file, real worktree, ENABLE_VISION_IDENTITY_V2=true: 131 passed, 10 warnings; [hermeticity] 131; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3rv-unit-on start=2026-10-20 10:22:41 end=2026-10-20 10:23:19 elapsed=37s bound=600s status=OK rc=0
tests/test_price_fallback_may_decline.py (F3-2), real worktree: 17 passed; [hermeticity] 17; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3rv-pricefallback start=2026-10-20 10:40:27 end=2026-10-20 10:40:42 elapsed=15s bound=600s status=OK rc=0
CI-order set = GREEN's 30 files + tests/test_price_fallback_may_decline.py, sorted (31 files), real worktree: 1402 passed, 1 skipped, 1 deselected, 23 warnings; [hermeticity] sentinel checked 1403 test(s); [netguard] blocked 29 attempt(s) from 23 node(s) (all 23 node ids in tests/.network_attempt_baseline.txt; = the fix round's 1385 + 17)
[pyt] tag=b3rv-ciorder start=2026-10-20 10:41:14 end=2026-10-20 10:42:33 elapsed=79s bound=1200s status=OK rc=0
CLAUDE.md readers (tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py) on the HEAD CLAUDE.md: 79 passed; [hermeticity] 79; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3rv-claude-readers start=2026-10-20 10:43:35 end=2026-10-20 10:44:02 elapsed=27s bound=600s status=OK rc=0
hook files -k "not dash", ALONE, run 1: TIMEOUT after 51 of 167 nodes (51 passed, 0 failed)
[pyt] tag=b3rv-hook-notdash start=2026-10-20 10:49:46 end=2026-10-20 11:19:52 elapsed=1806s bound=1800s status=TIMEOUT rc=124
hook files -k "not dash", ALONE, the one re-run: TIMEOUT after 26 nodes (19 passed, 7 F that passed in run 1)
[pyt] tag=b3rv-hook-notdash-rerun start=2026-10-20 11:26:38 end=2026-10-20 11:56:45 elapsed=1807s bound=1800s status=TIMEOUT rc=124
hook test_precommit_hook.py -k "not dash" --collect-only (to name the 7 F positions)
[pyt] tag=b3rv-hook-collect start=2026-10-20 11:58:14 end=2026-10-20 11:58:34 elapsed=20s bound=600s status=OK rc=0
```

Lint / syntax on the one touched Python file (the RED file): ruff `--select E9,F63,F7,F82
--no-cache` "All checks passed!", `--select F` "All checks passed!", py_compile OK.

## Independent measurements (beyond the runs)

- VISION_PROMPT_V2 evaluated from the module AST (with VISION_CATEGORY_KEYS): 3,170 chars,
  ASCII, sha256 7d7f2c83b11dfb8b05cb9541379b798bcaa6fe0cfeb16526bf38e8966723dd24 = the RED
  file's VISION_PROMPT_SHA_ON = the spec 2.2 fenced block (B3_UNIT_SPEC.md lines 150-176, joined)
  character for character. Each of the four quoted rule substrings occurs exactly once.
- CLAUDE.md: only lines 474 (header) and 475 (row) differ between 764d4416 and HEAD; both pure
  ASCII; whole-file high-byte count 3979 at 764d4416, HEAD blob and working copy; working copy
  CRLF with 0 bare LF (938 CRLF); the HEAD blob LF-only (index).
- F3-2 comm list <scratchpad>/B3_fix1/comm_head_list_fix1.txt: sha256 238a3d03...1ccc, 249 lines;
  every importer of tests/w4_11_prompt_digest_recorder.py (test_model_config_enforced,
  test_prompt_fence, test_prompt_truth, test_price_fallback_may_decline) is in it, and every
  reader of the other edited test-support / test files (.pre_impl_failures.txt,
  PRE_IMPL_FAILURE_BASELINE.md, the edited test files: test_camera_vision, test_ci_gates,
  test_regression_gate_diff, test_s71_u13_compare_auth_required, test_s71_u13_pins,
  test_security_regression, test_value_math) is in it. The s80-common.txt addendum (line 73)
  carries the rule.
- The fix report's D5 is right and correctness min-4's sub-claim was wrong: the V1 normaliser is
  `"brand": p.get("brand") or "Unknown"` / `"name": p.get("name") or "Unknown Product"`
  (openai_service.py V1 block, after `# Normalize: ensure each product has all expected fields`),
  so a null brand reads `Unknown` in both; the real change is a whitespace-only brand / name and
  `""` size / price -> None. `"confidence": p.get("confidence", "medium")` keeps an explicit
  unrecognised (or null) value verbatim, as the row now says.
- D6 is right: identify_products returns the un-stripped list, so the owner's off-route smoke
  sees `_image_index` / `_category` (VISION_V2_INTERNAL_KEYS), never `image_index` / `category`.
- "V1 had no route-level bound (only the SDK client's 120 s per-attempt timeout and its
  retries)": `client = AsyncOpenAI(..., timeout=httpx.Timeout(120.0, connect=30.0),
  max_retries=openai_max_retries())` (openai_service.py module singleton); the V1 call has no
  wait_for. TRUE.
- Activation "after ENABLE_RESULT_STATUS_METADATA and before ENABLE_IMAGE_PIPELINE_V2" and
  "RESULT_GATE several R-A2 windows later": PLAN_S80.md R-A2 order STATUS_METADATA ->
  VISION_IDENTITY_V2 -> IMAGE_PIPELINE_V2 -> CATEGORY_TRUTH -> CLAIMS_PROVENANCE -> URL_MODE_V2 ->
  RESULT_GATE. TRUE.
- Rebase note: base :501-:502 = HEAD :504-:505 (3 lines inserted above); main 4a38ce93 changed
  only :502 (`openai_service.py:109` -> `:81`, "the `cached_tokens > 0` line, re-measured
  2026-10-19 at 81df2b64"); B3's :505 carries `openai_service.py:81`, the `cached_tokens > 0` line
  (only main's "re-measured 2026-10-19 at 81df2b64" annotation is not carried); B3 changed :501
  too (the 11 -> 8 prune clause), so taking B3's two lines is right. TRUE (RV-nit-1 on :81).
- `_openai_failure_is_transient` treats builtin `TimeoutError` as transient
  (api_budget_service.py:913), so the V2 expiry rides the coded 503. `_camera_user_preferences`
  returns the preferences only on `success` AND `preferences_completed`, logs
  `[IMAGE] preferences read failed: <Type>` at WARNING and returns None on a raise. The knob is
  read only inside `_identify_products_v2` (one call site). `public_vision_products` wraps the
  six wire sites (image_routes.py :460, :531, :536, :577, :625, :678). All TRUE.

## CLAUDE.md row (:474-:475) and PR body, sentence by sentence

Checked every sentence of the header, the row and the PR body against the bytes (the source at
HEAD, the RED file, the run logs, the plan / rulings). Everything matches except RV-min-1
(both documents), RV-min-2 (PR body) and RV-nit-1 (CLAUDE.md :505, not part of the row). Items
with a non-obvious check:
- Row "a missing or unrecognised value -> `low` (V1: a missing key -> `medium`, an unrecognised
  value kept verbatim)": `_normalize_vision_products_v2` lower-strips, maps anything outside
  {high, medium, low} to low. TRUE.
- Row "category canonicalised (empty / null -> None)", "features stripped, cut at 80 characters,
  at most 8", "the best TWO when the request carries exactly one image", "UNPAIRED ... after the
  paired picks in reply order", "ties keep the earlier" (stable sorted): TRUE in the bytes.
- Row and PR "a refused / None-content reply is the coded 503 LLM_UNAVAILABLE where V1 returned a
  500": V2 raises LLMUnavailableError (route :351 maps it to 503); V1 passes None to
  clean_json_response and raises a non-transient error -> the 500 literal. TRUE.
- Row "Fix-round pins ... the unit file holds 131 nodes": 131 collected and passed. TRUE.
- Row / PR limit numbering: row limits (1)-(15), PR limits 1-18; every cross-reference inside a
  document uses its own numbers (PR owner step 3 -> limits 17, 5, 18; row activation -> limits
  15, 5). TRUE.
- PR "Fix round 1 ... 10 / 10 KILLED" and its table: reproduced by my independent harness with
  the same failing-row sets (XB1 / BM1 11, XB2 2, XB3 3, Y1 1, Y2 4, Y3 1, Z1 3, Z2 2, Z3 2).
- PR "F3-2 ... 249 files ... sha256 `238a3d03...1ccc`": TRUE (above).
- PR "the old file bytes are a prefix of the new": TRUE.
- PR limit 15 "measured by both adversaries: CI-order set 3 failed / 1356 passed, netguard 79
  attempts from 73 nodes vs 29 / 23": the quoted figures are the engineering adversary's
  (b3adveng-ciorder-flagenv); the correctness adversary measured the same effect on its 21-file
  set (53 nodes / 56 attempts). Not re-measured here (flag-ON runs of those sets are the
  adversaries'); wording "egress" is RV-min-1.

## Previous-round findings: closed or recorded

| finding | status | evidence |
|---|---|---|
| eng MAJ-E1 comm set misses test_price_fallback_may_decline | CLOSED | in comm list fix1 (249); green alone (b3rv-pricefallback) and inside the CI-order run; rule in s80-common.txt :73 and the PR body |
| eng MAJ-E2 BM1 placement unpinned | CLOSED | BM1 KILLED by XB1 x8 + XB1b + Y2b x2; XB1 and my XB1c (a later placement) KILLED too |
| corr min-1 hard precondition not executable | CLOSED | row + PR owner step 1 = the F3-3 off-route smoke text (with D6's `_image_index` / `_category`, measured right) |
| corr min-2 prompt rules unpinned | CLOSED | Z1_Z3 sha + 4 substrings; Z1-Z5 KILLED; sha == spec 2.2 block |
| corr min-3 two products at image_index 0 | RECORDED | row limit (15), PR limit 17, canary item (need_second_product count vs V1) |
| corr min-4 / eng minor 1 client-visible sentence | CLOSED | measured list in row + PR limit 10 (D5 correction verified) |
| corr min-5 / eng minor 5 limit 14 understated | CLOSED (wording RV-min-1) | widened in row (14) and PR 15 |
| corr min-6 XB1 | CLOSED | killed (above) |
| corr min-7 XB2 | CLOSED | killed |
| corr min-8 XB3 | CLOSED | killed |
| corr min-9 Y1 / Y2 / Y3 + empty-tail canary note | CLOSED | killed; canary sentence in the row activation and PR limit 18 |
| corr min-10 placeholder pairs billed | CLOSED | row limit (5) + PR limit 5 clause + canary item |
| corr note X19 / eng minor 7 | RECORDED | no X19 exists for B3 (fix report, PR body) |
| eng minor 2 rebase note | CLOSED | verified (above) |
| eng minor 3 R12 row | CLOSED (wording RV-min-2) | PR defect table row added |
| eng minor 4 ruff list | CLOSED | SIM102 / SIM103 / SIM118 in the PR lint paragraph |
| eng minor 6 hook files | RECORDED NOT MEASURED | two TIMEOUTs alone this round (hook section); B3 edits no .githooks file |
| eng minor 8 confirmations | no action | - |

## Prove-nothing check on the new rows

None of the 26 new nodes is vacuous: each is killed by at least one mutant above except
XB3[None-2] (flag OFF: one encode per image on the V1 path; a design pin that the flag-OFF branch
is unchanged; by construction no V2-placement mutant can redden it) and XB1b's delivery half is
killed by XB1 / BM1 (prefs before identify). Y2b additionally fails under XB1 / BM1 (its
`prefs.calls == []`), so it doubles as a non-delivery prefs pin for the 500 / 429 exits.

## NOT MEASURED / not re-run

- The pre-commit hook test files (tests/test_precommit_hook*.py), `-k "not dash"`: two TIMEOUTs alone (b3rv-hook-notdash, b3rv-hook-notdash-rerun), NOT MEASURED (see the hook section); the `-k dash` half (160 nodes) not run (no budget left at ~60 s per node on this box).
- The full comm set (249 files, 10 chunks) was not re-run: the fix round changes no app/ file;
  the one added comm file and the CLAUDE.md readers were run (green).
- The flag-ON wider-suite numbers of limit 14 / PR 15 (taken from the two adversaries' logs).
- Live OpenAI behaviour (the owner's off-route smoke).

## Files written (notes folder; pure ASCII, LF)

<scratchpad>/B3_fix1/REVERIFY_REPORT.md (this file); <scratchpad>/B3_fix1/reverify/: notes.md,
rv_mutate.py, mut_results.jsonl, mut_logs/*.log, mut_backup/* (byte copies), RED_764.py and
RED_head_blob.py (git blobs, for the prefix check), claude_row.txt, unit_off.log, unit_on.log,
scratch_baseline.log, pricefallback.log, ciorder.log, ciorder_nodes.txt, baseline_nodes.txt,
claude_readers.log, hook_notdash.log, hook_notdash_rerun.log, hook_collect.log. The runner logs carry the runner's own line endings.

## git status --short (real worktree sc-s80-b3, at the end)

(empty) -- HEAD 7b1e3ecf81ef2bb24ce08e84d89c0069f98b386a; RED sha e8b2c9c1...8642 unchanged.
