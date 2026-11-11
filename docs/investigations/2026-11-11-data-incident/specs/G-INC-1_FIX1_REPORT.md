# G-INC-1 FIX ROUND 1 REPORT (agent Opus 5.5, 2026-11-11)

Unit G-INC-1 (INC-X9 + INC-X10 + INC-X8 + INC-X2a). Worktree sc-inc-g1, branch fix/inc-g1-result-truth. Start HEAD a92b0ba325914c59fbb26a2e7803bf8317aa2bbc (verified, status empty, the four frozen RED files re-hashed = GC-1). ONE commit dcdbf53027cb8f114b190429282cf46652d9571b through the hook (passed; no push, no rebase, no stash). Trailer: Co-Authored-By: Claude Opus 5.5. git status --short after the commit: empty.

## Rulings applied
- F1-1 (ruled pin-fix): tests/test_inc_x10_listing_match_guard.py autouse _env adds monkeypatch.delenv("WARMER_CONTEXT", raising=False) + a 4-line comment; the docstring's environment sentence names WARMER_CONTEXT. No assertion changed, no row removed (diff +7 -2, only the fixture and the docstring). NEW sha256 8419549c2861055f93a33f8fcf66a1060bdf2ab1ace7b76a64a1281078f01a18 (working copy = committed blob, LF, ASCII); SUPERSEDES GC-1's f1c7f330... for this file.
- F1-2: the CI-order set runs tests/test_identity_stamps_wave_b.py FIRST, then the 22 spec 12.2 files + the gate-rows file (24 files; list in ciorder_files.txt).
- F1-3: NEW tests/test_inc_g1_gate_rows.py: GR1 test_gr1_guard_is_fragrance_scoped_not_beauty_wide[makeup|skincare|haircare] (flag OFF and ON: selection True, backstop verdict equal; the fragrances control is rejected) and GR2 test_gr2_llm_pick_error_outcome_names_the_class (budget denied, the LLM pick raises RuntimeError: the llm_pick line is error:RuntimeError, the call returns None, call order budget then gpt). sha256 96858246713929bb04dbfaf91c08d367f806995b181979d15b86e721e6f16f5a (LF, ASCII). Each row's environment is stated by an autouse fixture (EXACT_PRICE_GATE and AXES set; GENUINE_PRICE_PRIORITY, WARMER_CONTEXT, DATA_GUARDS_V2 and the flag deleted).
- F1-4: renamed in tests/test_cohort_summary_orchestrator.py (bodies, docstrings included, unchanged): test_returns_peer_count_and_governorate_when_resolved -> test_resolved_cohort_returns_none_since_inc_x9; test_peer_count_sourced_from_cohort_match_n -> test_cohort_match_n_never_surfaces_since_inc_x9; test_broadened_governorate_quality_still_emits -> test_broadened_governorate_quality_returns_none_since_inc_x9. git grep: no other reference to the old names. CRLF kept (166 CRLF of 166 LF). sha256 working copy b63cb13a..., committed blob 1395cdf7....
- F1-5: <SP>/G-INC-1_fix1/PR_BODY.md and <SP>/G-INC-1_fix1/G-INC-1_GREEN_REPORT_F15.md (a corrected copy; the original GREEN report is left untouched as evidence): all 8 `NO [pyt] LINE` placeholders replaced. The GREEN runner printed its [pyt] status line to stdout only (pyt.py writes only the argv lines to the log), so each line is REBUILT field for field from that run's record in <SP>/harness/pyt_ledger.jsonl (tags inc-g1-green-on, -off, -offrows, -pins, inc-g1-ciorder, inc-g1-p102-base-order, -head-order, -base-warm), and the body says so. Mutant count now reads: 25 applied, none survived; 1 not applicable after R-G1-6.
- F1-6: the two limits joined INC-X10 in the PR body and in its CLAUDE.md row (line 639, in place: L-X10-6 an Arabic-only title fails open; L-X10-7 a pronoun of the other side in marketing text rejects the right product). CLAUDE.md CRLF kept (1106 CRLF of 1106 LF), added text ASCII; sha256 working copy 1dfcd90d..., committed blob ce373e30....
- F1-7: no application file changed (git diff a92b0ba3..HEAD -- app is empty); the other three frozen RED files are byte-identical (x9 b2ef4d34..., x8 8a2cc6d6..., x2a febb83de...).

## Runs (every [pyt] line; the pytest summary in brackets)
- [pyt] tag=inc-g1-fix1-repro start=2026-11-11 23:25:38 end=2026-11-11 23:25:47 elapsed=9s bound=600s status=FAIL rc=1 (5 failed, 56 passed, 10 warnings in 5.94s)
- [pyt] tag=inc-g1-fix1-order-head start=2026-11-11 23:26:01 end=2026-11-11 23:26:05 elapsed=4s bound=600s status=OK rc=0 (61 passed, 10 warnings in 2.97s)
- [pyt] tag=inc-g1-fix1-r1010-base start=2026-11-11 23:26:16 end=2026-11-11 23:26:22 elapsed=5s bound=600s status=FAIL rc=1 (1 failed, 5 passed, 55 deselected, 11 warnings in 4.27s)
- [pyt] tag=inc-g1-fix1-gr-head start=2026-11-11 23:27:22 end=2026-11-11 23:27:26 elapsed=3s bound=600s status=OK rc=0 (4 passed, 11 warnings in 2.23s)
- [pyt] tag=inc-g1-fix1-mut-a10-beautywide start=2026-11-11 23:27:43 end=2026-11-11 23:27:48 elapsed=5s bound=600s status=FAIL rc=1 (3 failed, 1 deselected, 11 warnings in 3.71s)
- [pyt] tag=inc-g1-fix1-mut-a2-llmerr start=2026-11-11 23:27:49 end=2026-11-11 23:27:53 elapsed=4s bound=600s status=FAIL rc=1 (1 failed, 3 deselected, 10 warnings in 3.25s)
- [pyt] tag=inc-g1-fix1-on start=2026-11-11 23:28:09 end=2026-11-11 23:28:15 elapsed=5s bound=600s status=OK rc=0 (88 passed, 11 warnings in 4.57s)
- [pyt] tag=inc-g1-fix1-off start=2026-11-11 23:28:16 end=2026-11-11 23:28:22 elapsed=6s bound=600s status=OK rc=0 (88 passed, 11 warnings in 4.65s)
- [pyt] tag=inc-g1-fix1-ciorder start=2026-11-11 23:28:32 end=2026-11-11 23:29:45 elapsed=74s bound=1200s status=OK rc=0 (728 passed, 15 warnings in 72.45s (0:01:12))
- [pyt] tag=inc-g1-fix1-comm-03 start=2026-11-11 23:30:17 end=2026-11-11 23:31:08 elapsed=51s bound=1200s status=OK rc=0 (1248 passed, 5 deselected, 13 warnings in 49.31s)
- [pyt] tag=inc-g1-fix1-comm-09 start=2026-11-11 23:31:10 end=2026-11-11 23:31:24 elapsed=14s bound=1200s status=OK rc=0 (353 passed, 1 skipped, 5 deselected, 13 warnings in 13.39s)
- [pyt] tag=inc-g1-fix1-walkers start=2026-11-11 23:32:01 end=2026-11-11 23:33:02 elapsed=61s bound=1200s status=OK rc=0 (696 passed, 1 xfailed, 18 warnings in 59.67s)

- Repro (before F1-1): failed ids = the five test_p10_2_flag_off_identity_full_config[unset, false, padFALSE, zero, garbage]; AssertionError on the should_cache_price base-value line, as the adversary measured.
- R10-10 at base: scratch worktree <SP>/G-INC-1_fix1/wb at a74caba7 (no node_modules), the pin-fixed X10 file copied in; order wave_b then X10, -k "r10_10 or p10_2": R10-10 FAILED with `AssertionError: assert True is False` (should_cache_price accepted the women's listing); the five P10-2 passed. Worktree removed with git worktree remove --force; git worktree list holds none of mine.
- Mutants: scratch worktree <SP>/G-INC-1_fix1/wh at a92b0ba3 + the gate-rows file; lock .qa-mutation.lock created and removed; byte copy before, restore after, sha256 equal to the GREEN shas (price_service a5d26d1b..., image_service c4d7492f...). A10-beautywide (H1 `cat == "fragrances"` -> `cat in _FRAGRANCE_BEAUTY_CATEGORIES`): KILLED, GR1 3 of 3 on AssertionError (('makeup', False) and so on). A2-llmerr (the llm_pick except arm sets `_outcome = "miss"`): KILLED, GR2 on AssertionError ([('llm_pick', 'miss')] != [('llm_pick', 'error:RuntimeError')]). Results in mut_results.json; harness mut.py. Worktree removed.
- Comm set: head list = GREEN's 736 + tests/test_inc_g1_gate_rows.py = 737 (comm/comm_list_fix1.txt, sha256 a352227a...), rechunked by 25; chunk 03 (= GREEN chunk 04, identical file list; holds test_cohort_summary_orchestrator.py) and chunk 09 (wave_b, the four RED files, the gate rows) run at head with both unit flags removed from the env: 0 failed ids; `comm -13` against the base record (G-INC-1_green/comm/base_failed_sorted.txt, 28 ids, the whole-tree record harness/base_records/a74caba7.../23f5330f...) is EMPTY. Renamed nodes (old -> new) are listed under F1-4; the old names were green at base, the new names are green at head. Other chunks not re-run: no file they hold changed and no application file changed.
- Walkers of spec 12.1 (tests/test_hermeticity_pins.py, tests/test_ci_gates.py, tests/test_scoring_rubric_truth.py) + the CLAUDE.md readers (test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py): green (the walkers line above).
- ruff --select E9,F63,F7,F82 and the default ruff set on the three changed test files: All checks passed; py_compile ok; the pre-commit hook passed.
- Client fences and jest: NOT re-run (no application, script or client file changed; ruling B.3); the full jest suite is the final round's (LC-7).

## PR body
<SP>/G-INC-1_fix1/PR_BODY.md: 20,189 bytes (python len of the utf-8 bytes; cap 25,600); LF; the only bytes > 127 are the 4 bytes of the attribution emoji line, as in GREEN's body. PROOF ON THE PHONE per unit kept (none needs AI text); 'merged, NOT yet proven' kept; a fix-round gates block added; the E-rows table shows the new and the old names; the stated limit that the remaining rows of test_cohort_summary_orchestrator.py no longer test a gate.

## Deviations
- D1: F1-5 for the GREEN report is a corrected COPY (G-INC-1_GREEN_REPORT_F15.md), not an in-place edit of the GREEN file, so the original evidence stays byte-identical.
- D2: the rebuilt GREEN [pyt] lines and the fix-round lines in the PR body omit the log= field (the ledger and this report keep the paths).
- D3: the re-flowed X10 docstring sentence leaves one docstring line at 123 characters (the ruff default set is clean); kept to hold the diff minimal.
- D4: the renamed E-row test_cohort_match_n_never_surfaces_since_inc_x9 keeps its old docstring ("peer_count must be the cohort prior's real sample size"), because F1-4 keeps the bodies as GREEN left them; the name now states the assertion.

## Open questions
- Q1: the GREEN [pyt] lines are rebuilt from the runner ledger, not read from a log; accept them as the real lines (F1-5 says 'from the logs')?
- Q2: for the re-verifier's F1-1 diff check: the X10 diff also touches the module docstring (2 lines) beside the fixture; both are environment statements, no assertion.

## NOT MEASURED
- The full comm set (only the two chunks holding changed files were re-run), the client fences and the full jest suite (see above).

Report written through the shell (python).
