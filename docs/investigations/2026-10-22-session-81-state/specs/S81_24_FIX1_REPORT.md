# S81-24 FIX ROUND 1 REPORT (RED-then-GREEN), fix agent Opus 5.5, 2026-11-07

Unit S81-24; branch feature/s81-s24-auth-throttle-v2 in sc-s81-s24; start HEAD f8f64d9dfd9e7e471b6611032312a33187910a1a (verified; `git status --short` empty; the node_modules junction present, @babel/core + .bin/jest verified, never touched). NEW HEAD ba4079cce1bb0adfcab2fb6f35efa9f31278bc92 (ONE commit through the hook: ruff "All checks passed!", gitleaks silent; never --no-verify; trailer Co-Authored-By: Claude Opus 5.5). No push, no PR, no rebase, no stash. `git status --short` after the commit: EMPTY.

## New files (sha256; working copy = committed blob, pure ASCII, LF, 0 bytes > 127)
- tests/test_s81_s24_fix1_rows.py f96a9dd8e47c65641c3b01da15200f56c21f640ac32f13e91d969e8419bc23ba (+251)
- tests/test_s81_s24_gate_rows.py 5b5916139bd6a1b43708a681f7b8c05ddd3a086940cd99d9c8c444961590c233 (+144)

## Edited files (before -> after; byte copies before edit in <scratchpad>/S81-24_fix1_before/ with SHA256SUMS.txt)
- app/services/auth_throttle.py (LF, ASCII) 98ce9f5bf457fc9dd6a1de798e67b6fcaf3ef6f309bdd6d25ec82d983c0b3cae -> 4ed97e78fef5f74ca26735ba844fcd545671fb45870ab79bed1993c97b2590c7 (+38 / -7: the F1-1 hunk only)
- CLAUDE.md (CRLF kept in the working copy, 1078 CRLF before and after, 0 bare LF; added text ASCII) 33d48e6b6db6c50dc26d28cad34a6c306a995b175420b7cfd45f7c3adb6173a3 -> 4b24d30f16fc6cfb2cc410def077d8b692c3f4c7c152200303b9a5149abbe1af (working copy; the LF blob 3d8f3937218c32bf8d26bf843cdc4f148c8abcee6c380061808900aabe04c4d4), +2 / -2 (two lines of the S81-24 block in place)
- request_id.py NOT edited (used only as a mutant target, restored sha-equal 40386516...).

## F1-1 (the GREEN hunk)
`_durable_done(endpoint, abandoned)` builds the done-callback for a durable write's INNER future (`asyncio.wrap_future(...)`, attached at creation, before the shield): it returns on a cancelled future, always calls `fut.exception()` (so the loop's 'Future exception was never retrieved' ERROR cannot fire), and, only when the caller had stopped waiting (`abandoned[0]` set by `except (asyncio.TimeoutError, asyncio.CancelledError)` around the shielded `wait_for`), logs ONE WARNING `[AUTH_THROTTLE] record failed endpoint=%s type=%s` (endpoint = login_fail / login_clear, the type name only). `_run` gains `endpoint: str = "record"`; the non-durable gate read is `return await asyncio.wait_for(job, ...)` unshielded, unchanged in behaviour. A failure seen by the caller (no abandon) still logs only the memoised skipped line (the frozen r61 / r64 / r65 forbid any other [AUTH_THROTTLE] line there). The module text never names llm_spend_breaker (r91 forbids it); the model is its _run_bounded_async form.

## RED step (the new rows at f8f64d9d, auth_throttle.py unedited)
- [pyt] tag=s24f1-red-head start=2026-11-07 11:40:28 end=2026-11-07 11:40:35 elapsed=6s bound=600s status=FAIL rc=1 -- 2 failed, 11 passed; [hermeticity] 13; [netguard] blocked 0
- [pyt] tag=s24f1-red-head-all start=2026-11-07 11:41:21 end=2026-11-07 11:41:34 elapsed=13s bound=600s status=FAIL rc=1 -- 2 failed, 210 passed (frozen 199 + 13 new); [hermeticity] 212; [netguard] blocked 0
- FAILED = the two F1-R1 nodes only ([fail_timeout-login_fail], [clear_cancel-login_clear]), each on an AssertionError (`assert ['Future exception was never retrieved'] == []`); F1-R2 (1), F1-R3 (1), G24-GR1 (3), G24-GR2 (5), G24-GR3 (1) green at HEAD (the PIN class); every frozen row green.
- Gate-row mutants (sha-verified byte copies under S81-24_fix1/mut/, applied in place, restored and sha-verified):
  - GR1 `pepper.strip().encode` -> `pepper.encode` (key only) sha 236c0c23...: [pyt] tag=s24f1-mut-GR1 start=2026-11-07 11:41:02 end=11:41:06 elapsed=4s bound=600s status=FAIL rc=1 (3 failed = the three G24-GR1 nodes, AssertionError only); restored 98ce9f5b sha-equal
  - GR2 the `endpoint not in ENDPOINTS` guard removed sha 013e71fd...: [pyt] tag=s24f1-mut-GR2 start=2026-11-07 11:41:06 end=11:41:10 elapsed=4s status=FAIL rc=1 (5 failed = the five G24-GR2 nodes, AssertionError only); restored sha-equal
  - GR3 the three presence booleans by truthiness (request_id.py, CRLF) sha fbeb396d...: [pyt] tag=s24f1-mut-GR3 start=2026-11-07 11:41:10 end=11:41:14 elapsed=4s status=FAIL rc=1 (1 failed = G24-GR3, AssertionError); restored 40386516 sha-equal

## GREEN step gates (one pytest at a time; only the two stall_monitor.py processes were live; no foreign pytest seen)
- ruff --select E9,F63,F7,F82 --no-cache + full ruff + py_compile on auth_throttle.py: clean; ruff E9/F63/F7/F82 on both new files: clean. git diff --stat hunks only.
- [pyt] tag=s24f1-green-off start=2026-11-07 11:41:57 end=2026-11-07 11:42:08 elapsed=11s bound=600s status=OK rc=0 -- 212 passed; [hermeticity] 212; [netguard] blocked 0 (frozen + both new files, flags unset)
- [pyt] tag=s24f1-green-on start=2026-11-07 11:42:08 end=2026-11-07 11:42:19 elapsed=10s bound=600s status=OK rc=0 -- 212 passed; [hermeticity] 212; [netguard] blocked 0 (ENABLE_AUTH_THROTTLE_V2=true + a synthetic low-entropy AUTH_THROTTLE_PEPPER + the eight knobs + ENABLE_HOP_PROBE_LOG=true exported in the runner call only)
- F1-1 mutants (killed by F1-R1, AssertionError only, restored 4ed97e78 sha-equal each):
  - F1a the callback removed (sha dc749e4e...): [pyt] tag=s24f1-mut-F1a start=2026-11-07 11:42:27 end=11:42:35 elapsed=8s bound=600s status=FAIL rc=1 (2 failed = F1-R1 x2)
  - F1b the callback re-raising (sha cad2c502...): [pyt] tag=s24f1-mut-F1b start=2026-11-07 11:42:35 end=11:42:44 elapsed=8s status=FAIL rc=1 (2 failed = F1-R1 x2)
  - F1c the WARNING carrying the message text (sha 6fa367d4...): [pyt] tag=s24f1-mut-F1c start=2026-11-07 11:42:44 end=11:42:52 elapsed=8s status=FAIL rc=1 (2 failed = F1-R1 x2)
  - F1d (extra) the abandon guard removed (sha 6cb037aa...): [pyt] tag=s24f1-mut-F1d start=2026-11-07 11:42:52 end=11:43:01 elapsed=9s status=FAIL rc=1 (killed by the FROZEN r61 / r64 / r65: the extra line breaks the fail-open line contract)
- Pins set of GATE GC-2 (test_429_contract, test_s81_s05_request_context, test_retro_w1_9, test_retro_w1_1, test_brute_force, test_retro_w1_9_429, test_conftest_env_safety):
  - [pyt] tag=s24f1-pins-on start=2026-11-07 11:43:09 end=2026-11-07 11:43:39 elapsed=30s bound=600s status=OK rc=0 -- 316 passed, 1 skipped, 2 deselected; [hermeticity] 317; [netguard] blocked 0
  - [pyt] tag=s24f1-pins-off start=2026-11-07 11:43:39 end=2026-11-07 11:44:09 elapsed=30s bound=600s status=OK rc=0 -- 316 passed, 1 skipped, 2 deselected; [hermeticity] 317; [netguard] blocked 0
- CI-order set (19 files, spec 1.10 + s08b + retro_w1_1): [pyt] tag=s24f1-ci start=2026-11-07 11:46:38 end=2026-11-07 11:47:32 elapsed=53s bound=1200s status=FAIL rc=1 -- 2 failed, 789 passed, 1 skipped, 2 deselected; [hermeticity] 792; [netguard] blocked 18 attempt(s) from 11 node(s) (the neutralized.supabase.invalid sentinel); FAILED = the two baselined test_auth_interceptor social nodes (= base).
- tests/test_secret_scan_static.py alone at HEAD: [pyt] tag=s24f1-secretscan start=2026-11-07 12:04:23 end=2026-11-07 12:04:29 elapsed=7s bound=600s status=OK rc=0 -- 31 passed; [hermeticity] 31; [netguard] blocked 0
- Client fences (jest 29.7.0, node v24.11.1, by path from sc-s81-s24/SmartCompareApp through the junction): [jest] tag=s24f1-fences start=2026-11-07 12:04:38 end=2026-11-07 12:04:44 rc=1 -- Test Suites 1 failed, 14 passed, 15 total; Tests 4 failed, 242 passed = exactly the four config/nativeBundle.w37 drift nodes (d5, k2, k4, k5); b3a/nativeStrings PASS. 13 / 14 fences + b3a as required.
- NOT RUN as ruled: the FULL jest (LC-7), the four tests/test_precommit_hook*.py (no .githooks change), the corpus gate (no price-pipeline module touched: auth_throttle.py only).

## F1-2 the comm closure (MAJ-C1)
- Derivation: an AST walk over every tests/**/*.py (Import, ImportFrom incl. relative, importlib.import_module / __import__ string args), the closure of the 365 (the 364 of a9a3f4b3... + the RED file) under "imports a member test module", iterated to a fixpoint (script output and list: <scratchpad>/S81-24_fix1/comm/closure_additions.txt).
- Importer additions: tests/test_s81_s10_gate_rows.py (imports the member tests/test_s81_s10_fragrance_gate.py) -> ADDED. Hits NOT added: tests/test_precommit_hook_phase_b_round2.py (imports the member test_gitleaks_config; excluded by rule, the hook files), tests/fixtures/_gen_rubric_truth_flag_on_golden.py (imports test_scoring_spec_field_normalization) and tests/fixtures/_gen_w4_13_flag_off_ledger.py (imports test_w4_13_measurement_truth): generator scripts, not collected by pytest.
- The reverse direction (test modules members import as support, not themselves members), ADDED for completeness: tests/test_compare_timeout_graceful.py (by test_cost_meter_s74, test_s81_s03_llm_ledger_v2), tests/test_hotfix_shopping_query_clean.py (by test_hermeticity_pins), tests/test_openai_breaker.py (by test_cost_meter_s74, test_s81_s03_llm_ledger_v2), tests/test_prescoring_showable_guard.py (by test_hermeticity_pins), tests/test_tradeoffs_dedup_parity.py (by test_scoring_rubric_truth). Non-test helpers imported by members (_env_safety, _netguard, _retro_r_mig_sql, _route_introspection, _tokenizer, _bundle_c_helpers, w4_11_prompt_digest_recorder, fixtures/lane1/_helpers) are not collected and none was edited.
- The widened set = 370 files (sha256 e3b889e40fc8fddc5544b51854d02c7a8e4bf45f948fb8565e335311d4b15c34), STORED as its own record: <scratchpad>/harness/base_records/daf86d32d222a885c42dc537e83c25483527a83b/e3b889e4....{files,header.txt,txt,pyt.log} (the a9a3f4b3 header form). Base side: no new base run: the 364 REUSED from a9a3f4b3... (LC-6) and the 6 additions REUSED from the same-base daf86d32 record ea0d2f1b... (all six are members of that 712; 0 of its 24 FAILED ids fall in them), so no scratch worktree was needed. Base FAILED = the 20 environmental ids.
- HEAD side (the 370 + the RED file + the two new files = 373, CLAUDE.md already edited, 15 chunks of <= 25, one pytest at a time):
  - [pyt] tag=s24f1-comm-chunk_00 start=2026-11-07 11:49:32 end=2026-11-07 11:50:02 elapsed=29s bound=1200s status=FAIL rc=1 -- 2 failed, 780 passed, 21 warnings
  - [pyt] tag=s24f1-comm-chunk_01 start=2026-11-07 11:50:02 end=2026-11-07 11:50:36 elapsed=34s bound=1200s status=OK rc=0 -- 1202 passed, 36 deselected, 23 warnings
  - [pyt] tag=s24f1-comm-chunk_02 start=2026-11-07 11:50:36 end=2026-11-07 11:51:08 elapsed=32s bound=1200s status=OK rc=0 -- 911 passed, 1 skipped, 11 deselected, 13 warnings
  - [pyt] tag=s24f1-comm-chunk_03 start=2026-11-07 11:51:09 end=2026-11-07 11:52:07 elapsed=58s bound=1200s status=OK rc=0 -- 2010 passed, 1 skipped, 11 warnings
  - [pyt] tag=s24f1-comm-chunk_04 start=2026-11-07 11:52:07 end=2026-11-07 11:53:04 elapsed=57s bound=1200s status=OK rc=0 -- 556 passed, 1 skipped, 14 deselected, 18 warnings
  - [pyt] tag=s24f1-comm-chunk_05 start=2026-11-07 11:53:04 end=2026-11-07 11:53:27 elapsed=22s bound=1200s status=OK rc=0 -- 490 passed, 13 warnings
  - [pyt] tag=s24f1-comm-chunk_06 start=2026-11-07 11:53:27 end=2026-11-07 11:53:57 elapsed=31s bound=1200s status=OK rc=0 -- 3618 passed, 2 skipped, 10 deselected, 2 warnings
  - [pyt] tag=s24f1-comm-chunk_07 start=2026-11-07 11:53:58 end=2026-11-07 11:54:29 elapsed=31s bound=1200s status=FAIL rc=1 -- 751 passed, 27 skipped, 6 deselected, 1 xfailed, 18 warnings, 2 errors
  - [pyt] tag=s24f1-comm-chunk_08 start=2026-11-07 11:54:29 end=2026-11-07 11:57:05 elapsed=156s bound=1200s status=OK rc=0 -- 840 passed, 1 skipped, 271 warnings
  - [pyt] tag=s24f1-comm-chunk_09 start=2026-11-07 11:57:05 end=2026-11-07 11:58:49 elapsed=104s bound=1200s status=FAIL rc=1 -- 1 failed, 2483 passed, 13 warnings
  - [pyt] tag=s24f1-comm-chunk_10 start=2026-11-07 11:58:50 end=2026-11-07 12:00:02 elapsed=72s bound=1200s status=FAIL rc=1 -- 7 failed, 2399 passed, 64 warnings
  - [pyt] tag=s24f1-comm-chunk_11 start=2026-11-07 12:00:02 end=2026-11-07 12:01:12 elapsed=70s bound=1200s status=FAIL rc=1 -- 8 failed, 2131 passed, 1 xfailed, 45 warnings
  - [pyt] tag=s24f1-comm-chunk_12 start=2026-11-07 12:01:13 end=2026-11-07 12:01:58 elapsed=45s bound=1200s status=OK rc=0 -- 822 passed, 1 skipped, 8 deselected, 15 warnings
  - [pyt] tag=s24f1-comm-chunk_13 start=2026-11-07 12:01:58 end=2026-11-07 12:02:59 elapsed=61s bound=1200s status=OK rc=0 -- 677 passed, 6 skipped, 6 deselected, 35 xfailed, 19 warnings
  - [pyt] tag=s24f1-comm-chunk_14 start=2026-11-07 12:02:59 end=2026-11-07 12:03:38 elapsed=39s bound=1200s status=OK rc=0 -- 1232 passed, 10 skipped, 13 warnings
  - chunk lists and logs: <scratchpad>/S81-24_fix1/comm/chunk_NN{,.log,.out}; [hermeticity] / [netguard] lines in each .out.
- HEAD FAILED/ERROR = 20 ids (18 failed + the 2 cold-tiktoken test_prompt_truth ERRORs), identical to the base set: `comm -13` (branch-only-new) EMPTY; `comm -23` EMPTY. test_s81_s10_gate_rows.py ran in chunk_10 at HEAD with 0 failures (its base outcome: 0 failures in ea0d2f1b).

## Documentation (F1-4 / F1-6)
- CLAUDE.md S81-24 block, in place (names only, CRLF kept, ASCII): the row's 'a stdlib leaf' -> 'a leaf over `cache_service.redis_client` (stdlib + `fastapi.HTTPException`)'; the shield sentence names the done-callback, the record-failed WARNING and F1-R1..F1-R3 in tests/test_s81_s24_fix1_rows.py; the malformed-reply clause states the ints-only parser; G24-GR1..G24-GR3 (tests/test_s81_s24_gate_rows.py) named after the P70-P74 sentence; L1 narrowed (localhost Redis 5.0.14 / Lua 5.1 probe; the limit is Upstash's engine and REST path); L8, L-S24-17, L-S24-18, L-S24-19 added. NOT touched: the :92 apply record, the S81-08b row (the final round's).
- PR body re-cut: <scratchpad>/S81-24_fix1/PR_BODY.md, 15,621 bytes (python len), pure ASCII except the attribution line; states the ints-only reply parser, DAY_KEY_TTL_SECONDS as the one ruled name exception (F1-5), the fix-round rows / mutants / gates, L1 narrowed, L8, L-S24-17..19, L-F1.

## Deviations
- D-F1 two extra F1-R1 nodes (parametrized: the timeout path on login_fail and the task-cancel path on login_clear) and extra parametrizations of G24-GR1 (3 paddings) and G24-GR2 (5 unknown names); 13 new nodes in all.
- D-F2 the WARNING fires only when the wait was abandoned (a TimeoutError or CancelledError out of the shielded wait_for); a failure the caller sees keeps the one memoised skipped line, because the frozen r61 / r64 / r65 pin exactly that line set (mutant F1d proves it). Stated limit L-F1: a timeout and the job failure in the SAME loop iteration retrieve the exception without the WARNING.
- D-F3 the comm widening also takes the five test modules members import as support (not required by the importer rule); their base outcome is reused from ea0d2f1b, so no base run and no scratch worktree.
- D-F4 the CLAUDE.md edit was made BEFORE the comm run, so the CLAUDE.md readers in the set ran once after it (no re-run needed).
- D-F5 the commit trailer names this agent's own model (Claude Opus 5.5).

## Open questions
- Q-F1 the same latent never-retrieved form exists in the merged llm_spend_breaker._run_bounded_async(durable=True) (flag OFF; the security adversary's note): a follow-up unit for the orchestrator.

## Restore / state
No .env read; no flag, knob or pepper in any .env or the OS environment (exported in single runner calls only); no network; no package manager; the junction untouched; no git write in any other worktree; no pytest or jest left running; every mutant target restored sha-equal.
- git status --short after the commit: [] (EMPTY)
- frozen RED re-hashed LAST: git show HEAD:tests/test_s81_s24_auth_throttle.py | sha256sum = 7fdf71db5b2cc43e34b24674b62d3eb57e117b1c8fa683719471b10c4c562228 (= 7fdf71db... byte-identical); working copy 7fdf71db5b2cc43e34b24674b62d3eb57e117b1c8fa683719471b10c4c562228
