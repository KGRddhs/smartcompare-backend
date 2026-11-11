# G-INC-1 FIX ROUND 1 RE-VERIFY REPORT (lens: correctness; agent Opus 5.5; 2026-11-11/12)

HEAD verified dcdbf53027cb8f114b190429282cf46652d9571b at start and end (branch fix/inc-g1-result-truth); worktree git status empty at start and end; the worktree was never edited. Scratch worktree <SP>/g1f (the short path of rulings C), detached at dcdbf530, no node_modules junction, clean after every restore, removed with git worktree remove --force (0 entries left).

VERDICT: SOUND (no blocking, no major; 3 minors = stated limits / notes).

## RED file hashes (committed blob = sc-inc-g1 working copy, start and end)
x9 b2ef4d34... (= frozen); x10 8419549c... (F1-1 pin-fix; supersedes GC-1 f1c7f330...); x8 8a2cc6d6... (= frozen); x2a febb83de... (= frozen); gate rows 96858246.... Blobs LF, ASCII.

## Diff of the fix commit (a92b0ba3..dcdbf530)
4 files: CLAUDE.md (1 line, in place), tests/test_cohort_summary_orchestrator.py (3 renames, bodies unchanged), tests/test_inc_g1_gate_rows.py (new), tests/test_inc_x10_listing_match_guard.py (+7 -2). Nothing under app/. The X10 diff = the docstring environment sentence (2 lines, names WARMER_CONTEXT) + in the autouse _env fixture monkeypatch.delenv("WARMER_CONTEXT", raising=False) and a 4-line comment: no assertion changed, no row removed, no parametrisation changed. Blob line endings unchanged (LF); bytes > 127 unchanged (cohort file 33 = base, CLAUDE.md 3904 = base). Old E-row names have no other reference.

## F1-1 proven both ways
- Pre-fix X10 bytes (sha f1c7f330), order wave_b then X10: 5 failed = the five P10-2 nodes on `AssertionError: assert False is True` (should_cache_price base-value line), 56 passed:
  [pyt] tag=inc-g1-rv-order-oldx10 start=2026-11-11 23:41:09 end=2026-11-11 23:41:14 elapsed=5s bound=600s status=FAIL rc=1
- HEAD, order wave_b, X10, X9, X8, X2a, gate rows: 106 passed:
  [pyt] tag=inc-g1-rv-order-head start=2026-11-11 23:40:53 end=2026-11-11 23:40:59 elapsed=7s bound=600s status=OK rc=0
- R10-10 at BASE (the three app files replaced by their a74caba7 blobs, sha-verified backups restored and checked OK), pin-fixed X10, wave_b first, -k "r10_10 or p10_2": R10-10 FAILED on `AssertionError: assert True is False`, the five P10-2 passed (1 failed, 5 passed, 55 deselected); R10-10 now proves the guard, not the leaked veto:
  [pyt] tag=inc-g1-rv-r1010-base start=2026-11-11 23:41:31 end=2026-11-11 23:41:36 elapsed=5s bound=600s status=FAIL rc=1

## Unit ON / OFF (four RED files + gate rows)
  [pyt] tag=inc-g1-rv-on start=2026-11-11 23:41:45 end=2026-11-11 23:41:51 elapsed=6s bound=600s status=OK rc=0 (both flags true: 88 passed; netguard 0)
  [pyt] tag=inc-g1-rv-off start=2026-11-11 23:41:53 end=2026-11-11 23:41:59 elapsed=6s bound=600s status=OK rc=0 (both flags unset: 88 passed; netguard 0)

## Mutants: 12 applied, 12 KILLED, 0 survived (harness rv/rvmut.py; byte copies in rv/bak; every restore sha256 = HEAD bytes; lock created and removed; flags unset; every failure an AssertionError)
- RV-beautywide (H1 scope widened to _FRAGRANCE_BEAUTY_CATEGORIES; adversary survivor): KILLED by GR1 x3. [pyt] tag=inc-g1-rv-mut-rv-beautywide start=2026-11-11 23:42:46 end=2026-11-11 23:42:52 elapsed=7s bound=600s status=FAIL rc=1
- RV-llmerr (llm_pick error logged as miss; adversary survivor): KILLED by GR2. [pyt] tag=inc-g1-rv-mut-rv-llmerr start=2026-11-11 23:42:54 end=2026-11-11 23:43:00 elapsed=7s bound=600s status=FAIL rc=1
- RV-eros (Eros men -> women): KILLED, 11 nodes. [pyt] tag=inc-g1-rv-mut-rv-eros start=2026-11-11 23:43:02 end=2026-11-11 23:43:08 elapsed=7s bound=600s status=FAIL rc=1
- RV-dylan (Dylan Blue men -> women): KILLED by R10-5. [pyt] tag=inc-g1-rv-mut-rv-dylan start=2026-11-11 23:43:10 end=2026-11-11 23:43:16 elapsed=7s bound=600s status=FAIL rc=1
- RV-aventus (Aventus men -> women): KILLED by R10-3, P10-1[T7]. [pyt] tag=inc-g1-rv-mut-rv-aventus start=2026-11-11 23:43:17 end=2026-11-11 23:43:24 elapsed=7s bound=600s status=FAIL rc=1
- RV-lightblue (Light Blue women -> men): KILLED by R10-4, P10-1[T14]. [pyt] tag=inc-g1-rv-mut-rv-lightblue start=2026-11-11 23:43:26 end=2026-11-11 23:43:32 elapsed=7s bound=600s status=FAIL rc=1
- RV-noH2 (backstop hook H2 off): KILLED by R10-8, R10-9. [pyt] tag=inc-g1-rv-mut-rv-noh2 start=2026-11-11 23:43:33 end=2026-11-11 23:43:40 elapsed=7s bound=600s status=FAIL rc=1
- RV-cohortlive (cohort helper restored to a live body; + test_cohort_summary_orchestrator.py): KILLED, 18 nodes. [pyt] tag=inc-g1-rv-mut-rv-cohortlive start=2026-11-11 23:43:41 end=2026-11-11 23:43:49 elapsed=7s bound=600s status=FAIL rc=1
- RV-noH1 (selection hook H1 off): KILLED, 11 nodes. [pyt] tag=inc-g1-rv-mut-rv-noh1 start=2026-11-11 23:43:50 end=2026-11-11 23:43:57 elapsed=7s bound=600s status=FAIL rc=1
- RV-x8noflag (X8 flag conjunct dropped): KILLED by P8-1 x5. [pyt] tag=inc-g1-rv-mut-rv-x8noflag start=2026-11-11 23:43:58 end=2026-11-11 23:44:05 elapsed=7s bound=600s status=FAIL rc=1
- RV-qgender (gendered-query early return removed): KILLED by P10-1[T8,T15], P10-5. [pyt] tag=inc-g1-rv-mut-rv-qgender start=2026-11-11 23:44:06 end=2026-11-11 23:44:13 elapsed=7s bound=600s status=FAIL rc=1
- RV-x10envfix (the F1-1 delenv removed; wave_b then X10): KILLED, the five P10-2 nodes. [pyt] tag=inc-g1-rv-mut-rv-x10envfix start=2026-11-11 23:44:14 end=2026-11-11 23:44:19 elapsed=5s bound=600s status=FAIL rc=1
One per fix: F1-1 RV-x10envfix; F1-3 RV-beautywide + RV-llmerr; F1-4 (renames, no logic) RV-cohortlive kills the renamed rows; F1-2 = the CI-order run; F1-5/F1-6 = documents, checked below.

## CI-order set (wave_b first, the 22 spec 12.2 files, the gate rows; 24 files)
  [pyt] tag=inc-g1-rv-ciorder start=2026-11-11 23:44:55 end=2026-11-11 23:46:11 elapsed=76s bound=1200s status=OK rc=0 (728 passed; netguard 25 blocked from 22 nodes = the hermeticity pins' own guard rows)

## Comm chunks (737-file list = 771 tests/test_*.py minus 34 excluded; chunk_09 = wave_b + four RED + gate rows; chunk_03 = test_cohort_summary_orchestrator.py)
  [pyt] tag=inc-g1-rv-comm03 start=2026-11-11 23:46:37 end=2026-11-11 23:47:29 elapsed=52s bound=1200s status=OK rc=0 (1245 passed, 3 skipped, 5 deselected)
  [pyt] tag=inc-g1-rv-comm03rs start=2026-11-11 23:48:38 end=2026-11-11 23:49:29 elapsed=52s bound=1200s status=OK rc=0 (-rs: the 3 skips = test_category_payload_completeness.py "prod fixture <cat>.json not present", gitignored fixtures absent in a fresh scratch worktree; the fix agent's 1248 ran where they exist)
  [pyt] tag=inc-g1-rv-comm09 start=2026-11-11 23:47:31 end=2026-11-11 23:47:46 elapsed=16s bound=1200s status=OK rc=0 (353 passed, 1 skipped, 5 deselected)
  0 failed ids; comm -13 vs the base record (28 ids) EMPTY. Renames (old -> new, green at head): test_returns_peer_count_and_governorate_when_resolved -> test_resolved_cohort_returns_none_since_inc_x9; test_peer_count_sourced_from_cohort_match_n -> test_cohort_match_n_never_surfaces_since_inc_x9; test_broadened_governorate_quality_still_emits -> test_broadened_governorate_quality_returns_none_since_inc_x9.

## Hook test files ALONE (no .githooks change; own runner calls, split by -k; no TIMEOUT)
  [pyt] tag=inc-g1-rv-hooks-notdash start=2026-11-11 23:49:37 end=2026-11-12 00:05:19 elapsed=942s bound=1800s status=OK rc=0 (167 passed, 160 deselected; line rebuilt from the runner ledger: the shell moved the call to the background past its 600 s foreground limit)
  [pyt] tag=inc-g1-rv-hooks-dash start=2026-11-12 00:05:54 end=2026-11-12 00:24:05 elapsed=1091s bound=1800s status=OK rc=0 (157 passed, 3 skipped, 167 deselected)

## Walkers of spec 12.1 + CLAUDE.md readers
  [pyt] tag=inc-g1-rv-walkers start=2026-11-12 00:24:20 end=2026-11-12 00:25:26 elapsed=65s bound=1200s status=OK rc=0 (696 passed, 1 xfailed)

## Lint / hygiene
ruff E9,F63,F7,F82 and the default set on the three changed test files: All checks passed; py_compile ok; no sk-/JWT/PEM/credentialed-URL shape (the dummy key is concatenated); no digest constant added.

## PR body (<SP>/G-INC-1_fix1/PR_BODY.md) against the bytes
- 20,189 bytes (cap 25,600), LF, only bytes > 127 = the 4-byte attribution emoji.
- 0 `NO [pyt] LINE` (also 0 in G-INC-1_GREEN_REPORT_F15.md); reads "25 mutants applied, none survived; 1 not applicable after R-G1-6" (= GC-3).
- All 28 [pyt] lines in the body and the F15 report (20 tags) match the runner ledger field for field (start, end, elapsed +-1 s, bound, status, rc); every bracketed count matches the summary line of that run's log.
- "40 failed at base, 44 PIN green" = GC-2. E-row base assertions = the a74caba7 bytes; new names = HEAD; the other quoted row names exist.
- The two new limits are in the X10 stated limits (body line 34) and the CLAUDE.md INC-X10 row (line 639, in place: the trailing "repeat." became "repeat; L-X10-6 ...; L-X10-7 ...", nothing else on the line changed).
- The footprint sentence = git diff --stat a74caba7..dcdbf530 (10 files); "merged, NOT yet proven" and a PROOF ON THE PHONE per unit with no AI-text check are present.

## Previous round's findings
- B1 (CI red, WARMER_CONTEXT leak): CLOSED (F1-1 proven both ways; CI-order green with wave_b first).
- m1 / m2 surviving mutants: CLOSED (GR1 / GR2; both re-killed here).
- m3 placeholders, m4 mutant count: CLOSED.
- m5 E-row names: CLOSED (renamed); the remaining None rows are a stated limit in the body.
- m6 two X10 limits: CLOSED (see N1).
- m7 CLAUDE.md replay conflict: RECORDED for the final round (F1-7 / GC-9).
- Prove-nothing rows: R10-10 now proves the guard; the cohort None rows = stated limit; P9-5 unchanged.

## MINOR (stated limits by default, LC-4)
- N1 (precision of L-X10-7): probed on HEAD bytes (query "Versace Eros EDP", flag OFF vs ON): at the SELECTION gate the base already rejects a title with a lone "her" ("Versace Eros EDP 100ml perfect for her": _selection_match False with the flag OFF) and the Arabic / mixed titles probed; the guard's new rejection for L-X10-7 is at the BACKSTOP (backstop_identity_verdict True OFF -> False not_exact:gender ON: cache read and display). The limit is true of the guard; the "gift for her" example is also caught by a base rule at selection. L-X10-6 is accurate (ON == OFF for the Arabic titles). No change required.
- N2 (fix report D4): test_cohort_match_n_never_surfaces_since_inc_x9 keeps the docstring "peer_count must be the cohort prior's real sample size `n`, verbatim", which contradicts its name and assertion (F1-4 kept bodies on purpose).
- N3 (fix report D3): one X10 docstring line is 123 characters (ruff clean).

## Deviations of this re-verifier
- Scratch worktree <SP>/g1f (rulings C) instead of <SP>/G-INC-1_fix1_adv (task text), for the MAX_PATH hazard.
- One collect-only `python -m pytest --co -q` ran outside the runner in the scratch worktree (no test executed; output discarded; removed with the worktree).
- Client fences / jest not run: no application, script or client file changed (rulings B.3); the full jest suite is the final round's (LC-7).

Evidence: <SP>/G-INC-1_fix1/rv/ (logs, rvmut.py, mut_results_all.json, probe.py, chkbody.py, bak/).
