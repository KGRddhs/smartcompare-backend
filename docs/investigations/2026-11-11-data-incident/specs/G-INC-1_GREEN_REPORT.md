# G-INC-1 GREEN REPORT (agent Opus 5.5, 2026-11-11)

Unit: G-INC-1 = INC-X9 + INC-X10 + INC-X8 + INC-X2a. Worktree sc-inc-g1, branch fix/inc-g1-result-truth (created from a74caba7), ONE commit a92b0ba325914c59fbb26a2e7803bf8317aa2bbc (hook passed; not pushed, not rebased).

## Files (sha256 before -> after, working copy bytes; CRLF kept)
- app/services/structured_comparison_service.py 735f5a1c... -> 368a87f2c269a27e43a4009cc7a233b797876a8bea0f5aaff4345d77b28f6d0a (+54 -49): X9 helper = docstring + return None, _COHORT_GOV_SKIP deleted (no other reader at base, git grep); was_cohort_block_active import still used (two metadata sites). X8 helpers after _phase2_min_residual_seconds + the block before result["rating"].
- app/services/price_service.py 47c92eae... -> a5d26d1bbf0342f9171275e86dc6d3f528b6bf73cfbab79fd42696efbd950d53 (+55): table, words, listing_match_guard_enabled, _vd_gender_line_flip after _vd_feminine_query_unconfirmed; H1 in _descriptor_axis_mismatch; H2 in _descriptor_backstop_axes_verdict (outside the gender if-block).
- app/services/image_service.py 708354eb... -> c4d7492f358417889663d0983aa4782042c39cfbfa7ff63e213dfb1e0bcb69f8 (+96 -47; git diff -w +51): imports, _log_img_tier, bookkeeping, CancelledError arm (no await, bare raise). The 8 added lines with bytes > 127 are the pre-existing em-dash comment / log lines re-indented unchanged (the "[image] All tiers exhausted" text must stay byte-equal); no new non-ASCII.
- tests/test_cohort_summary_orchestrator.py b2c5fd44... -> 694093ce6da4817e533873a9040c15befe0d72bb3c8f1250c0d162d9c408ea0b (+6 -4): E9-1..E9-3 (is None, same subjects, names unchanged).
- CLAUDE.md 14de024f... -> 2eb41195bd877e2c77c9201cd48ea175abb94646a57c82bbf0db0b09cb9e4119 (+9 -2): :260 in place, the :341 sentence after the S81-G10 sentence, the group block after the S81-G10 owner-steps bullet before ## Tests (one blank line). Added text pure ASCII; CRLF kept (0 lone LF).
- The four RED files committed unchanged: re-hashed at start and end, working copy AND committed blob: x9 b2ef4d34..., x10 f1c7f330..., x8 8a2cc6d6..., x2a febb83de... (all match GC-1).
Byte copies of the five edited files: <SP>/G-INC-1_green_before/.

## Runs
- RED files, both flags ON: `NO [pyt] LINE` (84 passed, 11 warnings in 4.52s).
- RED files, both flags unset: `NO [pyt] LINE` (84 passed, 11 warnings in 4.35s); the flag-OFF identity rows alone: `NO [pyt] LINE` (15 passed, 44 deselected, 11 warnings in 2.77s).
- Identity pins of spec 4.2 (the four units' base-pass sets, 23 files): `NO [pyt] LINE` (649 passed, 1 deselected, 11 warnings in 33.80s; the one netguard node is pre-existing and green).
- CI-order set (spec 12.2, 22 files): `NO [pyt] LINE` (706 passed, 16 warnings in 70.78s (0:01:10)).
- Comm set at HEAD: 736 files (the RED round's union list, re-derived, nothing new), 30 chunks of <= 25 (bound 1200), all `status=OK` or `FAIL` on the base-known nodes only. HEAD failures 32 ids; base record = the whole-tree record at a74caba7 (`harness/base_records/a74caba7.../23f5330f...`, 28 ids), reused per file (GC-7).
- branch-only-NEW = 5 ids, all `tests/test_inc_x10_listing_match_guard.py::test_p10_2_flag_off_identity_full_config[*]`: an ORDER DEPENDENCE of the frozen RED row, present at BASE too, NOT a regression: `tests/test_identity_stamps_wave_b.py` imports `scripts/measure_warmed_kpi.py`, which sets `WARMER_CONTEXT=1` at import and is not restored, so the warmer write veto makes `should_cache_price` refuse the women's listing and P10-2's base-value assertion fails. Measured at base a74caba7 in a scratch worktree with the same RED file: `NO [pyt] LINE`; at HEAD: `NO [pyt] LINE`; at base with WARMER_CONTEXT=1 alone: `NO [pyt] LINE`. CI collects every module in one process, so CI would show this red: OPEN, a pin-fix round on the RED file (delete WARMER_CONTEXT in the row's environment) is needed before the PR.
- Client fences (15 suites by path through the live junction, jest 29.7.0): `[jest] tag=inc-g1-fences rc=1`: 246 passed, 4 failed = the four accepted `config/nativeBundle.w37` drift nodes (d5, k2, k4, k5).
- Lint: ruff E9,F63,F7,F82 clean on the four edited python files; the default ruff set reports the same counts at base and head (21 / 38 / 0 / 0); py_compile clean; the pre-commit hook passed.

- X10 order proof logs: <SP>/G-INC-1_green/p102_base_order.log, p102_head_order.log, p102_base_warm.log (scratch worktree <SP>/G-INC-1_green/wb at a74caba7, no node_modules, removed with git worktree remove --force; git worktree list verified).
- Comm artefacts: <SP>/G-INC-1_green/comm/ (comm_list_head.txt sha256 fe0bddde..., 30 chunk logs / .files / .failed, pyt_lines.txt, head_failed.txt, base_failed_sorted.txt, branch_only_new.txt). Base-only id: tests/test_s80_url_mode_v2.py::test_deadline_yields_timeout_503[POST] (the known wall-clock flake, green at head).

## Deviations
- D1: the img re-indent keeps the original tier comments (the RED prototype dropped them); outcome words as the RED report item 8 (piggyback miss when a truthy but invalid page image).
- D2: E9-3 drops its governorate assertion (the block is None; same subject).
- D3: commit trailer names Opus 5.5 (the prompt's first paragraph and the session attribution), not the Fable 5.1 template line of step 7.

## Open questions for the gate
- Q1 (BLOCKING for the PR): P10-2 (frozen) fails in CI's one-process order at base and head because tests/test_identity_stamps_wave_b.py leaks WARMER_CONTEXT=1 from its scripts.measure_warmed_kpi import (its restore list omits WARMER_CONTEXT). Proposed pin-fix (test-only, LC-2): the RED file's autouse env fixture adds monkeypatch.delenv("WARMER_CONTEXT", raising=False) (it also makes R10-10 non-vacuous in that order); alternative: add WARMER_CONTEXT to test_identity_stamps_wave_b.py's _MEASURE_ENV_KEYS (an extra E-row). GREEN did not edit either.
- Q2: the CI-order set of spec 12.2 lacks test_identity_stamps_wave_b.py; the next round's CI-order set should include it before the RED files.

## NOT MEASURED
- The full jest suite (LC-7: the last round before the PR). Mutation table not re-run at GREEN (RED: 25/25 KILLED on the prototype; the GREEN code is the same logic).

## git status --short (after commit)
(empty: only gitignored .qa-s80/ present)
