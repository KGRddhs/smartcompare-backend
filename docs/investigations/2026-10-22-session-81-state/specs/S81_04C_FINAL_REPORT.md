# S81-04c REFUSAL-LOG-HYGIENE: final round (REBASE-AND-GATES) report

Agent: Opus 5.5 (claude-opus-5-5). Worktree sc-s81-s04c, branch feature/s81-s04c-refusal-log-hygiene. Round 2026-11-11 19:56-20:12 AST.

## State
- HEAD before: 4c7cd43095db040f3a42334c65def408626ffb86 (git status --short empty, branch verified).
- git fetch origin main: origin/main = FETCH_HEAD = a74caba7e3ff66b12e94178c912197c845ccbd14; re-fetched at the end: unmoved.
- git rebase origin/main: "Current branch feature/s81-s04c-refusal-log-hygiene is up to date." (no-op, RB-04C-2). Commits replayed: 0. Conflicts: none. Resolutions: none.
- Round commit (through the hook, no --no-verify, trailer Co-Authored-By: Claude Opus 5.5): 10359aa8480159704a5ff345cbd8ac745b3d41c8 "docs(s81-04c): final-round in-place CLAUDE.md rewrites (RB-04C-3 a-d)", CLAUDE.md only, 1 file +4 / -4.
- HEAD after: 10359aa8480159704a5ff345cbd8ac745b3d41c8. No push, no PR.
- CLAUDE.md sha256 29c638d8... -> d102c888...; CRLF kept (1103 CRLF = 1103 LF); non-ASCII byte count unchanged (3904 -> 3904); git diff --check clean.
- git diff --stat origin/main...HEAD: CLAUDE.md 28, app/api/image_routes.py 8, app/services/extraction_service.py 34, app/services/url_extraction_service.py 6, tests/test_s81_s04c_refusal_log_hygiene.py 843, tests/test_s81_s06_router_gate_rows.py 23; 6 files, +910 / -32. Exactly the six allowed files; no whole-file diff.
- Conflict-marker grep (^<<<<<<< / ^>>>>>>>) over CLAUDE.md, app/ and tests/: empty.
- RED file tests/test_s81_s04c_refusal_log_hygiene.py sha256 774e3e61a7b416299d735281e2a14d7c801d662fa7122568be665b1a56ee4fac first and last (working copy and HEAD blob).
- .qa-mutation.lock: never created (no mutant owed).
- git status --short at the end: empty.

## The CLAUDE.md edits (RB-04C-3), exact-string, each matched once on its line
- (a) :480 B4 row: "`extract_with_ai`'s ERROR line is `AI extraction error: <ExceptionType>` ..." -> "`extract_with_ai`'s except arm logs `AI extraction error: <ExceptionType>` ... : at ERROR for every exception outside the `api_budget_service.LLMUnavailableError` class and, since S81-04c (2026-11-11), at WARNING by type for a class member (role flags OFF; with a role flag ON the arm WARNs by type and re-raises, as since S81-06), so the arm's log record of a refusal raises no Sentry event."
- (b) :495 limit (9): "(`<prefix>: LLMUnavailableError`, no exc_info, no exception text)" -> "(`<prefix>: <TypeName>`: `LLMUnavailableError` for the base class the breaker raises, a subclass prints its own name; no exc_info, no exception text)".
- (c) :638 S81-04c block: "so a refusal raises no Sentry event;" -> "so the ARM'S LOG RECORD of a refusal raises no Sentry event (with a role flag ON, an Anthropic SDK error that the router turns into a class member, `AnthropicDispatchError`, is still captured once by the explicit `AnthropicIntegration`: measured 1 event, mechanism `anthropic`; pre-existing, unchanged by this unit, not reachable in production while the role flags are unset);".
- (b)+(d) :857 W1-3 row: "a denial that reaches a dispatch site's except arm logs that arm at WARNING by type (`<prefix>: LLMUnavailableError`), never an ERROR, so a denial raises no Sentry event;" -> "a denial that reaches one of the eight arms of S81-04c (`extraction_service` parse, specs, price, price fallback, reviews and verdict, `image_routes` camera vision, `url_extraction_service` AI extraction) logs that arm at WARNING by type (`<prefix>: <TypeName>`: `LLMUnavailableError`, the base class a W1-3 denial raises), never an ERROR, so the arm's log record raises no Sentry event; the five other WARNING arms a denial can reach (classify, image tier 3, specs_targeted, specs_synthesized, disambiguate) print the exception text (at WARNING, never an ERROR) and are the follow-up S81-04e REFUSAL-TEXT-HYGIENE (planned);".
- Script: S81-04c_final/claude_md_round.py (byte copy CLAUDE.md.before sha-verified first).

## Pin rows and mutants
None (RB-04C-1 no fix round; RB-04C-3 the one round commit is CLAUDE.md only). No test file edited; RED file sha unchanged 774e3e61...

## Gates at HEAD 10359aa8 (every pytest through harness/pyt.py via S81-04c_final/run.py, which waits while any foreign pytest is live; the incident lane's inc-* gates were live and were waited for, nothing killed)
- [pyt] tag=s04c-final-unit-off start=2026-11-11 20:00:26 end=2026-11-11 20:00:39 elapsed=13s bound=600s status=OK rc=0 : 183 passed (RED 102 + E1 file 81); [hermeticity] sentinel checked 183; [netguard] blocked 0
- [pyt] tag=s04c-final-unit-on start=2026-11-11 20:00:41 end=2026-11-11 20:00:54 elapsed=13s bound=600s status=OK rc=0 : 183 passed, ENABLE_ANTHROPIC_TEXT / ENABLE_LLM_PREFLIGHT_BREAKER / ENABLE_LLM_SPEND_BREAKER=true exported (the unit has no flag; these are the arms' reachers); [hermeticity] 183; [netguard] blocked 0
- (2) conflicted test files alone: none (no conflict).
- [pyt] tag=s04c-final-secretscan start=2026-11-11 20:00:56 end=2026-11-11 20:01:08 elapsed=12s bound=600s status=OK rc=0 : 31 passed; [netguard] blocked 0
- [pyt] tag=s04c-final-r8pair start=2026-11-11 20:01:40 end=2026-11-11 20:02:00 elapsed=20s bound=600s status=OK rc=0 : 273 passed (tests/test_sentry_channels_u8d_unit.py + tests/test_sentry_channels_u8d.py); [netguard] blocked 0
- [pyt] tag=s04c-final-paid-off start=2026-11-11 20:02:01 end=2026-11-11 20:02:05 elapsed=4s bound=600s status=OK rc=0 : 21 passed; [netguard] blocked 2 attempt(s) from 2 node(s)
- [pyt] tag=s04c-final-paid-on start=2026-11-11 20:02:06 end=2026-11-11 20:02:12 elapsed=6s bound=600s status=FAIL rc=1 : 16 failed / 5 passed with the three flags above exported: ENABLE_ANTHROPIC_TEXT ON with no provider configured -> LLM_UNAVAILABLE 503 at the camera / url routes. Measured at base: [pyt] tag=s04c-final-base-paid-on start=2026-11-11 20:06:26 end=2026-11-11 20:06:32 elapsed=7s bound=600s status=FAIL rc=1 : 16 failed / 5 passed; the sorted FAILED id lists are IDENTICAL (paid_on_base_failed.txt = paid_on_head_failed.txt). Environmental, not this unit.
- [pyt] tag=s04c-final-paid-brk start=2026-11-11 20:05:44 end=2026-11-11 20:05:51 elapsed=7s bound=600s status=OK rc=0 : 21 passed with only ENABLE_LLM_PREFLIGHT_BREAKER / ENABLE_LLM_SPEND_BREAKER exported; base: [pyt] tag=s04c-final-base-paid-brk start=2026-11-11 20:06:35 end=2026-11-11 20:06:45 elapsed=10s bound=600s status=OK rc=0 : 21 passed.
  Base worktree: git worktree add --detach S81-04c_final/base_wt a74caba7 (HEAD verified), removed with git worktree remove --force, git worktree list shows it gone, path absent on disk (base_paid.py).
- [pyt] tag=s04c-final-claudemd start=2026-11-11 20:02:13 end=2026-11-11 20:03:12 elapsed=59s bound=1200s status=OK rc=0 : 908 passed (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire, test_secret_scan_static, test_retro_w1_2d, test_skill_frontmatter, test_sqlfluff_config, test_s81_s06_anthropic_router); [netguard] blocked 24 attempt(s) from 2 node(s) (supabase.invalid sentinels)
- [pyt] tag=s04c-final-ciorder start=2026-11-11 20:03:44 end=2026-11-11 20:04:38 elapsed=54s bound=1200s status=OK rc=0 : 1367 passed, 0 failed (GATE D6 order, s20 first); [netguard] blocked 48 attempt(s) from 11 node(s)
- [pyt] tag=s04c-final-urlv2 start=2026-11-11 20:04:39 end=2026-11-11 20:04:48 elapsed=9s bound=600s status=OK rc=0 : 456 passed (tests/test_s80_url_mode_v2.py alone, GC-5)
- (6) comm set: 375 files of record (s04c_red/comm_set.txt) vs the stored base record base_records/a74caba7.../0a224f48... (47 FAILED ids). CLAUDE.md-only round (RB-04C-6): the CLAUDE.md readers re-derived at HEAD by code grep (open/read_text of CLAUDE.md: test_behavior_dimension_translation, test_ci_gates, test_s81_s04_spend_breaker, test_s81_s08b_gate_rows (imports CLAUDE_MD), test_s81_s08b_legacy_fingerprint, test_s81_s23_bypass_retire) = GREEN's six; with GREEN's .md walkers the 11 files above, all members, 0 FAILED ids at base; re-run at HEAD 908 passed, 0 FAILED. Every other member reuses GREEN's 15 chunk logs S81-04c_green/s04c-green-comm-00..14 (bound 1200, 0 TIMEOUT, at 4c7cd430 whose app/ and tests/ bytes equal HEAD's). comm -13 (base ids vs GREEN head_failed 23 ids) recomputed this round: 0 lines = EMPTY. The cold-tiktoken pair tests/test_prompt_truth.py: in GREEN's chunk logs and the stored record as before (not re-run this round). No member added: the round touched no app/ or test file.
- (7) the two CLAUDE.md readers tests/test_ci_gates.py and tests/test_behavior_dimension_translation.py: inside s04c-final-claudemd, green.
- (8) ruff 0.16.5 --select E9,F63,F7,F82 --no-cache on the five python files: All checks passed; py_compile rc=0.
- Client, jest 29.7.0 through the worktree's junction (node_modules/@babel/core and .bin/jest present), no foreign jest live at either start:
  [jest] tag=s04c-final-fences start=2026-11-11 20:07:58 end=2026-11-11 20:08:08 rc=1 : 21 / 22 suites, 337 / 341 tests; failures = the four config/nativeBundle.w37 drift nodes (d5, k2, k4, k5) = baseline.
  [jest] tag=s04c-final-fulljest start=2026-11-11 20:08:09 end=2026-11-11 20:08:30 rc=1 : THE FULL JEST ONCE: Test Suites 1 failed, 3 skipped, 407 passed, 408 of 411; Tests 4 failed, 13 skipped, 13 todo, 4030 passed, 4060 total; Snapshots 41 passed. = baseline exactly (4,030 + the four w37 drift nodes + 13 skipped + 13 todo, 411 suites).
- (9) hook files tests/test_precommit_hook*.py: NOT run, per the task ("the hook test files NOT run") and GATE_S81_04C GC-9 ("the hook test files are NOT run (no .githooks change)"); the unit touches no .githooks file.

## NOT MEASURED
- The hook test files (ruled not run).
- The full 375-file comm set was not re-run at HEAD 10359aa8: per RB-04C-6 only the CLAUDE.md readers re-ran; the rest are GREEN's chunk logs at 4c7cd430 (identical app/ and tests/ bytes).
- The cold-tiktoken pair tests/test_prompt_truth.py was not re-run this round (it is not a CLAUDE.md reader).
- The corpus gate (no prompt / payload change).

## PR body
S81-04c_final/PR_BODY.md: 14,153 bytes (<= 25,600 without the attribution line), pure ASCII (0 bytes > 127: the draft's 4 non-ASCII bytes were the robot emoji of the attribution line, which is removed for the orchestrator to append), 0 hits for @gmail / +973 / 8-digit runs / key shapes / names. sha256 b40d3c1d5a1e3c88bb9c6c1d03be1508f4440b3a713da63dfc42adaaba3052c4. Carries: base a74caba7, HEAD 10359aa8, both commits, the RED sha 774e3e61..., the rulings and both adversary verdicts, no pin rows / no mutants owed, the comm paragraph from the measured list, the hook-files sentence, the "no Sentry event" sentences made exact (the arm's log record; the role-ON Anthropic integration capture as L7), L1-L6 kept (L2 per GC-6) + L7 / L8 from the adversary minors, the follow-up S81-04e, E1's old node id, the proof-standard sentence.

## Deviations
- D1 tests/test_paid_route_metering.py "with the flag exported": the unit has no flag; measured with the three reacher flags (16 failures, identical at base in a detached scratch worktree, so environmental) and with the two breaker flags only (21 passed both sides). The extra base worktree is the brief's allowed detached scratch worktree.
- D2 The PR body gains two stated limits L7 / L8 (the observability m1 and the RB-04C-5 gate-text figure) beside L1-L6.
- D3 tests/test_s80_url_mode_v2.py re-run alone (not in RB-04C-6's list) because the stored record masks its flake (GC-5): 456 passed.
