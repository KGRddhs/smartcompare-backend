# B3 VISION-IDENTITY-V2 adversary report, lens ENGINEERING

- Unit: B3 VISION-IDENTITY-V2 (ENABLE_VISION_IDENTITY_V2 + knob VISION_TIMEOUT_SECONDS).
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-s80-b3, branch feature/s80-b3-vision-identity-v2.
- HEAD verified at start and end: 764d44162dd83563dc5c9aa930dcb9c192f35f89; `git status --short` of the worktree empty at start and end; no .qa-mutation.lock there. The worktree was never written.
- RED file re-hash: start and end 36b78a404deefbc4fbea66b2d75574f203346a8e53550a3ddf04d3550e4af15e (bytes on disk, LF) and the HEAD blob identical.
- Window 2026-10-20 08:11 -> 09:20 AST. All probes and the mutant ran in a detached scratch worktree <scratchpad>/B3_adv_engineering at 764d4416 (changed-file sha256 equal to the real worktree; the RED file differs only by the autocrlf checkout, blob equal), removed with `git worktree remove --force` and verified absent from `git worktree list`.
- No .env read, no secret value printed, no network, no production probe; flag state not read (a new name).

## Verdict: NOT_READY (0 blocking, 2 major, 8 minor)

## MAJOR

### MAJ-E1 Comm set misses a direct consumer of an edited module (procedural; measured green)
`tests/test_price_fallback_may_decline.py` imports the edited test-support module (`:25 from tests import w4_11_prompt_digest_recorder as recorder`) and iterates the exact list B3 extends (`:102 for name in recorder.FLAGS:`; B3 adds ENABLE_VISION_IDENTITY_V2 to `tests/w4_11_prompt_digest_recorder.py` FLAGS). It is in none of: GREEN's 248-file HEAD list, RED's 246-file base list, spec 7.5's 213-file rule. Cause: every modref regex (spec 7.5, RED, GREEN `comm_head.py`) lists app modules and baseline files but not the edited test-support module `w4_11_prompt_digest_recorder` (its other importers, test_prompt_fence / test_prompt_truth / test_model_config_enforced, are in the set for other reasons). Measured at HEAD, alone: 17 passed
`[pyt] tag=b3adveng-pricefallback start=2026-10-20 09:14:24 end=2026-10-20 09:16:08 elapsed=104s bound=600s status=OK rc=0` ([hermeticity] 17; [netguard] blocked 0).
Green at HEAD, so it cannot add a branch-only-new id; the defect is the gate's file set. Remedy (no code change): add the file to the comm list and the PR body comm paragraph with the line above; add the edited test-support module names to the derivation regex. Re-derivation details below (23 extra candidates triaged; this is the only real one).

### MAJ-E2 Hand block-move mutant BM1 SURVIVED: the placement of the preferences read is unpinned
The brief's "X19 block-move mutant" does not exist in B3's spec (section 6), RED table (`B3red/mutation_table.md`; B3's M19a/M19b are key-rename mutants) or GATE_B3; I applied the B3 analogue by hand. Spec 2.6 fixes the contract: "Forwarding (the ONE route-level flag read, immediately before `:450`)". BM1 moves the whole personalisation block (`_compare_extra = {}` + the flag-gated `_camera_user_preferences` read, `image_routes.py:483-490` at HEAD) to just after `vision_ledger = start_openai_ledger()` (`:335`), i.e. before the vision call and outside the compare try. Byte copy, one exact match each, lock in the scratch worktree, restore sha256 equal (4502ff0e...19ae):
`[pyt] tag=b3adveng-mut-BM1 start=2026-10-20 09:04:54 end=2026-10-20 09:05:02 elapsed=8s bound=600s status=OK rc=0` -- 237 passed (unit file + tests/test_retro_w2_1.py + tests/test_paid_route_metering.py).
Not equivalent: under ON a signed-in scan then pays one `get_user_preferences` Supabase round trip (inline on the loop while ENABLE_SYNC_DB_OFFLOAD is OFF, stated limit 8) on EVERY non-delivery exit that never compares (vision 503, parse error, moderation block, zero products, and `need_second_product`, the most common one-photo exit), and before the vision call on every scan. No row kills it. Remedy: one PIN/RED row in a follow-up test file (the RED file is frozen): flag ON, signed-in, vision stub returning one product -> `need_second_product`, and a vision stub raising -> 503; assert the `image_routes.get_user_preferences` recorder was never called. The orchestrator may rule this a minor (the GREEN bytes are correct; only the pin is missing).

## MINOR

1. Doc truth (CLAUDE.md row, PR body "Stated limits" 10, spec 9.10): "confidence ... an unknown value -> `low` (V1: `medium`)" and "The one client-visible value change: under ON a missing / unknown confidence reads `low` instead of `medium`". V1 (`openai_service.py` V1 normaliser, `"confidence": p.get("confidence", "medium")`) keeps an unrecognised value verbatim ("certain" stays "certain", "HIGH " stays "HIGH ") and defaults only a MISSING key. Under ON the same lists (`metadata.identified_products`, `need_second_product.products`) also change values elsewhere: whitespace-only brand/name -> `Unknown` / `Unknown Product`, "" -> None for size/price, confidence case-folded, and membership/order (one per image_index, unpaired last, is_product false dropped). Suggest: "a missing confidence reads low (V1: medium) and an unrecognised one low (V1: verbatim); the lists are re-selected per image (see above)".
2. PR body rebase note says CLAUDE.md "line 502" conflicts. Read-only `git merge-tree 81df2b64 4a38ce93 764d4416`: the only conflicting file is CLAUDE.md and the hunk spans :501-:502 (the Eval-anchor bullet and the CI-GREEN bullet). Main 4a38ce93 changed only :502 (`:109` -> `:81`, "the `cached_tokens > 0` line, re-measured ... at 81df2b64"), a sentence B3 rewrites and already carries (`openai_service.py:81`, the `cached_tokens > 0` line); :501 is in the hunk by adjacency only. "Take B3's lines" for both is correct and loses nothing; wording only. All other files merge cleanly.
3. PR body defect table maps no row to R12 (`test_R12_flag_reader`, the house-idiom reader); add it to the flag-OFF identity row.
4. GREEN report's per-rule ruff list for structured_comparison_service.py omits SIM102 / SIM103 / SIM118 (1 each). Measured: full ruff 0.16.5 per-rule counts identical base vs HEAD on all three source files (openai_service 4 W293; image_routes B008 2, B904 2, F401 2; scs E702 1, SIM102 1, SIM103 1, SIM118 1, B905 2, F841 2, F401 13), so the PR body sentence is true; report-only.
5. Stated limit 14 measured: with ENABLE_VISION_IDENTITY_V2=true exported on the runner, the 30-file CI-order set gives 3 failed / 1356 passed / 1 skipped / 1 deselected, the 3 = exactly the three named test_camera_vision.py nodes `[pyt] tag=b3adveng-ciorder-flagenv start=2026-10-20 09:05:43 end=2026-10-20 09:13:48 elapsed=485s bound=1200s status=FAIL rc=1`. Additionally 37 authed camera nodes (test_retro_w2_1.py 34, test_paid_route_metering.py 3) reach the REAL `get_user_preferences` under the flag ([netguard] 79 attempts / 73 nodes vs 29 / 23 OFF; every extra attempt sentinel-class `neutralized.supabase.invalid`, all still pass). Worth one clause in limit 14; the wider suite with the flag set is not measured.
6. Pre-commit hook files (B3 edits no .githooks; GREEN did not run them): `-k "not dash"` TIMEOUT at the bound after 41 of 167 nodes (36 passed, 5 F) with the box at about 30 s per node (sibling gates): `[pyt] tag=b3adveng-hook-notdash start=2026-10-20 08:32:11 end=2026-10-20 09:02:13 elapsed=1802s bound=1800s status=TIMEOUT rc=124`. The 5 F re-run alone: 5 passed `[pyt] tag=b3adveng-hook-failed5 start=2026-10-20 09:02:55 end=2026-10-20 09:04:48 elapsed=112s bound=600s status=OK rc=0` (load flakes: test_precommit_hook.py sh-red_git_mv_to_env_refused; test_precommit_hook_phase_b.py sh-gl_shim_rc2_broken_config_refuses, sh-gl_shim_argv_flags_env_and_color, sh-gl_shim_config_is_a_copy_of_head, sh-gl_shim_no_config_when_head_has_none). See NOT MEASURED.
7. The brief names "the X19 block-move mutant"; no X19 exists for B3 (template id from another unit). Recorded so the next brief names a B3 id.
8. The CLAUDE.md row and PR body otherwise match the bytes (checked: flag-first read; the second read once per request at the compare site; knob grammar and WARNING form, same `%r` form as the cited text_routes knob; max_tokens 1000 vs V1 500; object-or-array; selection rules; unpaired order; feature cut 80 / 8; the five public + five internal keys; the six `public_vision_products` wire sites; identity keys presence-gated with no flag read and never on the wire (`_fetch_product_data` reads only brand/name/variant/category/search_query/_vision, `_resolve_pair_category` only search_query/name); refusal / None / choice-less -> LLMUnavailableError and expiry -> TimeoutError both on the existing coded 503 exit 1 (`_openai_failure_is_transient` treats builtin TimeoutError as transient) with reserved + anon refunds; length -> exit 2 refunded; user_id forwarding adds behaviour-profile + demographics reads and the profile write, no save / metering inside the orchestrator (no `save_comparison` / `log_search` / `record_*` in scs); base prompt sha `bb737687...` = the RED pin literal; OFF kwargs set {model, messages, max_tokens, temperature, store}; base six identity keys; base three-kwarg call).

## Engineering checks (all measured on the exact bytes)

- Diff hygiene: 13 files, +2112 / -48; numstat equals the GREEN/PR tables row for row; every changed blob LF with high-byte counts unchanged except tests/.pre_impl_failures.txt 45 -> 42 (the deleted bullet's em dash); real worktree working copies CRLF with 0 bare LF on all 12 existing files, the RED file LF; `git diff --check 81df2b64 HEAD` clean; no whole-file diff. Every deleted line justified (CLAUDE.md 4 in-place rewrites; image_routes 8 = 1 import + 6 wire sites + 1 call; scs 2 twin lines; test_camera_vision 12 mock-usage lines; .pre_impl 3 rows + 3 bullet lines + count line; the generated mirror; 1 line per clear-list; rgd 1 assertion).
- Imports: exactly spec 2.6 / 3 (openai_service `asyncio`, `math`, `os`; image_routes widened openai_service import + `auth_service.get_user_preferences`, already loaded via auth_routes; test_camera_vision `types`); the `canonicalize_category` import is lazy as specified. Helper names differ from spec 3.1 (`_select_vision_products_v2` for `_select_best_per_image`, plus private helpers) -- internal only.
- VISION_PROMPT_V2: 3,170 chars, ASCII, sha256 7d7f2c83b11dfb8b05cb9541379b798bcaa6fe0cfeb16526bf38e8966723dd24, equal to the spec 2.2 block character for character (evaluated from the AST, not imported).
- M1 AST pin: 16 chat sites at HEAD, 15 at base (the pin's own matcher, re-implemented over both trees); the new site is openai_service.py:473 (inside `_identify_products_v2`, def at :457; the V1 site is :638); no literal temperature / max_tokens.
- Baseline file: CI's `grep -vE '^\s*(#|$)'` -> 8 rows; `scripts.regression_gate_diff.parse_failure_ids` -> 8 (the new PRUNED paragraph has no `::`, GB-6); `python -m scripts.gen_baseline_mirror --check` -> "OK: mirror is current (8 nodes)."
- Lint: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on the 10 changed .py files "All checks passed!"; `py_compile` rc 0; full-rule counts equal base vs HEAD (minor 4).
- Netguard ratchet (CI fails on a NEW egress node): every blocked node in my 7 logs (61 nodes) is in tests/.network_attempt_baseline.txt; over GREEN's 10 chunk logs 171 nodes, 4 not in the baseline (test_s78_all_timeout_cap_as_timeout F15[on]/[off] sentinel; test_specs_no_fabrication_guard flag_on_static_prefix egress = the cold tiktoken download, warmed in CI; test_supplement_branch_genuine cde2 egress = a .pre_impl row CI deselects), all four identical in the RED base logs -> pre-existing.
- PR body `[pyt]` lines: all 15 match the harness ledger (start, status, rc; elapsed rounded).
- Comm set re-derivation (union rule; my regex broader: every edited module incl. test-support files and edited test files, every added / edited / newly referenced symbol, path-walk + app-path, CLAUDE.md mentions, SmartCompareApp): 271 candidates vs GREEN 248; GREEN-only 0; mine-only 23 = 16 CLAUDE.md mentions in comments/docstrings (not readers), 6 "srcscan" hits reading fixtures or `inspect.getsource` of unrelated functions, and 1 real miss (MAJ-E1). Processors.json readers all in GREEN's list; no migration changed.

## Runs (every pytest through pyt.py, one at a time, flag state exported on the runner call only)

```
unit file, flag unset: 105 passed; [hermeticity] 105; [netguard] blocked 0
[pyt] tag=b3adveng-unit-off start=2026-10-20 08:16:33 end=2026-10-20 08:16:48 elapsed=14s bound=600s status=OK rc=0
unit file, ENABLE_VISION_IDENTITY_V2=true: 105 passed; [hermeticity] 105; [netguard] blocked 0
[pyt] tag=b3adveng-unit-on start=2026-10-20 08:17:24 end=2026-10-20 08:17:34 elapsed=10s bound=600s status=OK rc=0
CI-order set (GREEN's 30 files, sorted): 1359 passed, 1 skipped, 1 deselected; [hermeticity] 1360; [netguard] blocked 29 attempt(s) from 23 node(s)  (= GREEN's line)
[pyt] tag=b3adveng-ciorder start=2026-10-20 08:19:44 end=2026-10-20 08:22:17 elapsed=152s bound=1200s status=OK rc=0
extras (test_auth_preference_toggles_w314, test_behavior_dimension_translation, test_migration_index_predicate_immutability, test_price_fallback_may_decline, test_prompt_truth, test_start_command): 144 passed, 2 skipped, 1 xfailed, 2 errors = the two cold-tiktoken test_prompt_truth ERRORs (base noise); [hermeticity] 147; [netguard] blocked 0
[pyt] tag=b3adveng-extras start=2026-10-20 08:23:14 end=2026-10-20 08:23:57 elapsed=42s bound=600s status=FAIL rc=1
comm chunk 1 (GREEN chunking): 779 passed, 5 deselected; [hermeticity] 779; [netguard] blocked 60 attempt(s) from 18 node(s)  (= GREEN c01)
[pyt] tag=b3adveng-comm-c01 start=2026-10-20 08:24:52 end=2026-10-20 08:26:07 elapsed=75s bound=1200s status=OK rc=0
comm chunk 6: 2 failed (test_page_scraping x2, baseline rows), 487 passed, 7 deselected; [hermeticity] 489; [netguard] blocked 156 attempt(s) from 21 node(s)  (= GREEN c06)
[pyt] tag=b3adveng-comm-c06 start=2026-10-20 08:26:08 end=2026-10-20 08:27:04 elapsed=56s bound=1200s status=FAIL rc=1
comm chunk 7: 885 passed, 4 skipped, 2 deselected, 1 xfailed, 2 errors (the tiktoken pair); [hermeticity] 889; [netguard] blocked 111 attempt(s) from 9 node(s)  (= GREEN c07 final)
[pyt] tag=b3adveng-comm-c07 start=2026-10-20 08:27:04 end=2026-10-20 08:29:11 elapsed=127s bound=1200s status=FAIL rc=1
hook files collect-only: 327 collected (160 dash / 167 not dash)
[pyt] tag=b3adveng-hook-collect start=2026-10-20 08:31:54 end=2026-10-20 08:31:57 elapsed=3s bound=600s status=OK rc=0
hook files -k "not dash": TIMEOUT after 41 nodes (36 passed, 5 F)
[pyt] tag=b3adveng-hook-notdash start=2026-10-20 08:32:11 end=2026-10-20 09:02:13 elapsed=1802s bound=1800s status=TIMEOUT rc=124
the 5 F nodes alone: 5 passed; [hermeticity] 5; [netguard] blocked 0
[pyt] tag=b3adveng-hook-failed5 start=2026-10-20 09:02:55 end=2026-10-20 09:04:48 elapsed=112s bound=600s status=OK rc=0
mutant BM1 (block move, SURVIVED): 237 passed
[pyt] tag=b3adveng-mut-BM1 start=2026-10-20 09:04:54 end=2026-10-20 09:05:02 elapsed=8s bound=600s status=OK rc=0
CI-order set with ENABLE_VISION_IDENTITY_V2=true exported (stated limit 14): 3 failed (the three camera_vision nodes), 1356 passed, 1 skipped, 1 deselected; [hermeticity] 1360; [netguard] blocked 79 attempt(s) from 73 node(s)
[pyt] tag=b3adveng-ciorder-flagenv start=2026-10-20 09:05:43 end=2026-10-20 09:13:48 elapsed=485s bound=1200s status=FAIL rc=1
missed comm file alone (MAJ-E1): 17 passed; [hermeticity] 17; [netguard] blocked 0
[pyt] tag=b3adveng-pricefallback start=2026-10-20 09:14:24 end=2026-10-20 09:16:08 elapsed=104s bound=600s status=OK rc=0
```

Branch-only-new over the chunks I re-ran (c01, c06, c07) plus the extras and the CI-order set: EMPTY (every failure is in the RED base set of 7 or the tiktoken pair).

## Counts

- Unit file 105/105 OFF and ON; CI-order 1359 passed; comm chunks 3/10 re-run, identical to GREEN; 1 comm file added and green.
- Mutants applied by this lens: 1 (BM1, SURVIVED). The spec / GREEN mutants are the correctness lens's re-application.

## Prove-nothing rows

- The preferences-read placement (spec 2.6 "immediately before :450") has no killing row (BM1).
- R15 pins the stream twin by source text only (stated limit 9, accepted).
- P8 is vacuous at base by its own docstring; non-vacuous at HEAD (GREEN's G9 killed by P8 x3) -- not a prove-nothing at HEAD.

## NOT MEASURED

- Pre-commit hook files: 126 of the 167 `not dash` nodes and all 160 `dash` nodes. The bounded run timed out once (line above); the rule's single re-run alone was not made because at the measured ~30 s/node (box load from sibling gates) both halves need about 80 min each, beyond this agent's 90-minute budget. B3 edits no .githooks file, the GREEN commit passed the hook, and the B1 adversary measured 149 + 18 + 46 hook nodes green on the same hook bytes this morning.
- Comm chunks 2, 3, 4, 5, 8, 9, 10 not re-run by this lens (GREEN's logs read instead: failure sets match its report; ratchet check above).
- The comm set at base for the missed file (green at HEAD, so not needed for branch-only-new).

## Questions for the orchestrator

1. MAJ-E1: accept the remedy as a PR-body / comm-list amendment only (no code), with the [pyt] line above?
2. MAJ-E2: a follow-up pin row (new file, the RED file stays frozen) in a fix round, or rule BM1 a minor with a stated limit?
3. Minor 1: reword the "one client-visible value change" sentence in the row and the PR body before the commit is amended?

## Files written (notes folder only; final sha256 of bytes on disk in the structured output)

<scratchpad>/B3_adv/: notes.md, derive_comm.py, comm_mine.txt, run_chunks.py, blockmove.py, diff_openai.txt, diff_routes_scs.txt, diff_tests_docs.txt, mergetree.txt, claude_lines_cmp.txt, pr_pyt.txt, the run logs (*.log), this report; all pure ASCII + LF (the three diff dumps and mergetree.txt carry the repo's non-ASCII as backslash escapes). The BM1 byte copy (sha 4502ff0e...19ae = HEAD image_routes.py) was deleted after the sha-verified restore. The folder also holds the correctness adversary's files (correctness_REPORT.md, mutate.py, probe_prompt.py, bytes_check.py, sha_before_mut.txt, test_zz_b3adv_probe.py.txt); not mine, not read.

`git status --short` of the worktree at the end: empty (HEAD 764d4416).
