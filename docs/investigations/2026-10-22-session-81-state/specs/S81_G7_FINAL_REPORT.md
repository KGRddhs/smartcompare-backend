# S81-G7 FINAL ROUND (REBASE + GATES) REPORT (agent: Opus 5.5, claude-opus-5-5), 2026-11-05

Unit S81-G7 FOLLOWUPS = D16b + D17b + D22c + D22d. Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g7, branch feature/s81-g7-followups.
Verified first: HEAD 4b0f3b9c9192c3c6c69c883c0c4a60461aca9ec5, branch feature/s81-g7-followups, git status --short empty.
Written through the shell (python), per the harness rule.

## SHAs
- head_before 4b0f3b9c9192c3c6c69c883c0c4a60461aca9ec5
- base origin/main (git fetch origin main, 15:08) 05303c6f01348610fa7c813e6588c7cea4b89734 (#390 merge)
- replayed GREEN commit 4d73ebf8 (patch of 4b0f3b9c)
- round commit (head_after) ce3ec2a7dcab4c96f436b551f7ab3dbc7bf6152e "test(learning): S81-G7 final round: G7-GR1..GR3 gate rows, CLAUDE.md L-D22c-6 / L-D22d-4" through the pre-commit hook (ruff "All checks passed!", gitleaks clean; no --no-verify), trailer Co-Authored-By: Claude Opus 5.5. HEAD = origin/main + 2. No push, no PR.

## Conflicts and resolutions
- ONE replayed commit; ONE conflict: CLAUDE.md (as measured by the orchestrator's merge-tree), content conflict only at the :341 **Feature Flags:** clause. The S81-G7 block itself auto-merged, but git placed it right after the S81-G5 owner-steps bullet (BEFORE main's S81-11 block, no blank line).
- Resolution (UNION, merge order, RB-G7-4): the :341 line = main's line (base + the S81-11 sentence + the S81-20 sentence) with the S81-G7 sentence inserted after the S81-20 sentence, before `REAL_ACTION_MIN_SECONDS`; asserted in python that main's line = base + main's insert, the branch's line = base + the G7 sentence exactly, and the result carries every sentence once. The 7-line S81-G7 block was moved (byte-identical lines) to after the S81-20 block's owner-steps bullet, preceded by ONE blank line, followed by the existing blank + `## Tests`. CRLF kept (1058 CRLF of 1058 LF). After the resolution `git diff --cached origin/main -- CLAUDE.md` = 9 insertions / 1 deletion (the :341 line + blank + 7 block lines); every other hunk of main kept.
- git diff --check clean after the continue; grep for <<<<<<< / >>>>>>> over CLAUDE.md, app/, tests/ EMPTY.
- `git diff 4b0f3b9c HEAD -- app scripts data tests` is NOT literally empty: it equals exactly main's own delta 6869a3e6..05303c6f over those paths (the six #390 app files + its tests; `git patch-id --stable` 1cdc5bcb... both sides), i.e. the branch's own change is unchanged: patch-id of `git diff 6869a3e6 4b0f3b9c` == patch-id of `git diff origin/main HEAD` over app scripts data tests (16835ac6... both). Every unit file's blob at HEAD == at 4b0f3b9c (14 files listed by rev-parse), data/variant_hint_learned.json absent. (Deviation DV-1: the literal "EMPTY" check cannot hold once main moved app/; measured the equivalent.)

## Frozen files (GC-1): HEAD blobs
6fd81d37... d16b, 927dc060... d17b, ff9b45da... d22c profile, 79a33372... d22c varhint, 15c5dc0f... d22d, 8c793a16... golden: all six equal at HEAD (git show HEAD:<f> | sha256sum).
Line endings (DV-2): the rebase checkout re-materialised these six as CRLF in the working copy (core.autocrlf=true; GREEN had them LF because RED wrote them). With CRLF the golden's own digest check fails (5 nodes of test_p1_flag_off_golden, [pyt] g7fin-units-off-crlf FAIL rc=1, 5 failed / 55 passed, AssertionError "the golden file changed"). Every gate below ran with the six written back as the exact LF blob bytes (= GC-1 shas, = CI's checkout); at the end they were rewritten as CRLF so `git status --short` is empty (the blobs never changed; the working copy then mirrors the checkout state).

## Pin rows (NEW tests/test_s81_g7_gate_rows.py, sha256 dea4c5492bb5e858e120e080b70f651365cf2f87d5a9e1120aca4d121f2a1bd8; pure ASCII, LF, 0 CR; the only @ is the pytest fixture decorator)
- G7-GR1 test_g7_gr1_read_by_every_chunk (RB-G7-1): _read_by over 250 values: IN_CHUNK 100, 3 requests of 100 / 100 / 50 values, 750 rows all distinct, every product present, every request ordered by id; cap 700 -> 700 rows, "capped", 3 requests, last range (0, 99), no page above 500.
- G7-GR2 test_g7_gr2_render_escapes_del (RB-G7-2): _render("Nova"+DEL+"Oud") == "Nova\x7fOud" (literal backslash), 0x1F the same, a clean name unchanged.
- G7-GR3 test_g7_gr3_dropped_counts_wrong_unclean_only (RB-G7-2): _gather(...)["dropped_fields"]: 1 for one wrong unclean row; still 1 with a clean-named wrong row added; still 1 with an unclean-named "correct" row added; 0 for unclean-correct + clean-wrong.
- Mutants on sha-verified byte copies of scripts/cron_learning.py (6997e623...; CRLF-aware exact single-match edits) under .qa-mutation.lock (created, removed after the last restore; restore sha-compared after each):
  ADV-O1 (break -> return rows, "ok" after the first chunk): [pyt] tag=g7fin-mut-adv-o1 start=2026-11-05 15:15:18 end=2026-11-05 15:15:21 elapsed=4s bound=600s status=FAIL rc=1 -> KILLED (AssertionError, test_g7_gr1)
  ADV-O2 (range(0x7F, 0xA0) -> range(0x80, 0xA0)): [pyt] tag=g7fin-mut-adv-o2 start=2026-11-05 15:15:22 end=2026-11-05 15:15:26 elapsed=4s bound=600s status=FAIL rc=1 -> KILLED (AssertionError, test_g7_gr2)
  ADV-O4 (count unclean names before the non-wrong continue): [pyt] tag=g7fin-mut-adv-o4 start=2026-11-05 15:15:26 end=2026-11-05 15:15:30 elapsed=4s bound=600s status=FAIL rc=1 -> KILLED (AssertionError, test_g7_gr3)
  restored_sha_ok true x3, final_ok true (mut_results.json).
- Green at HEAD: [pyt] tag=g7fin-gr-off start=2026-11-05 15:14:47 end=2026-11-05 15:14:50 elapsed=3s bound=600s status=OK rc=0 (3 passed; [hermeticity] 3; [netguard] blocked 0)

## CLAUDE.md (round commit, S81-G7 block only)
- D22c (1) row: + "Stated limit L-D22c-6 (flip-window data): ..." (RB-G7-3).
- D22d row: + "Stated limit L-D22d-4: three edges are pinned only by the GREEN-owned gate rows ... G7-GR1 / GR2 / GR3" (RB-G7-1 / RB-G7-2).
- The spec's "maps to its default bucket" sentence: ABSENT from the block (and from the GREEN PR body) - grep -i "default bucket" / "maps to its" over CLAUDE.md = no hit; nothing to withdraw in the bytes; recorded as withdrawn.
- 2 lines changed, CRLF kept (Edit tool), added text 0 non-ASCII, git diff --check clean.

## Gates at the rebased HEAD (every pytest through pyt.py, one at a time)
(1) units (5 RED files + the gate rows):
[pyt] tag=g7fin-units-off start=2026-11-05 15:16:57 end=2026-11-05 15:17:04 elapsed=7s bound=600s status=OK rc=0 (63 passed; [hermeticity] 63; [netguard] blocked 0)
[pyt] tag=g7fin-units-on start=2026-11-05 15:17:05 end=2026-11-05 15:17:13 elapsed=7s bound=600s status=OK rc=0 (63 passed, ENABLE_BEHAVIOR_PROFILE_REBUILD=true in the runner env only; [netguard] blocked 0)
E1 / E2: [pyt] tag=g7fin-e1e2 start=2026-11-05 15:17:14 end=2026-11-05 15:17:18 elapsed=4s bound=600s status=OK rc=0 (27 passed)
(2) conflicted test files: NONE (the only conflict was CLAUDE.md); its readers are gate (7).
(3) R8 pair alone:
[pyt] tag=g7fin-r8-unit start=2026-11-05 15:17:28 end=2026-11-05 15:17:44 elapsed=16s bound=600s status=OK rc=0 (141 passed; [netguard] blocked 0)
[pyt] tag=g7fin-r8 start=2026-11-05 15:17:45 end=2026-11-05 15:17:55 elapsed=10s bound=600s status=OK rc=0 (132 passed; [netguard] blocked 0)
(4) tests/test_paid_route_metering.py:
[pyt] tag=g7fin-paid-off start=2026-11-05 15:17:57 end=2026-11-05 15:18:02 elapsed=5s bound=600s status=OK rc=0 (21 passed; [netguard] blocked 2 from 2 nodes = the neutralized.supabase.invalid sentinels)
[pyt] tag=g7fin-paid-on start=2026-11-05 15:18:04 end=2026-11-05 15:18:09 elapsed=5s bound=600s status=OK rc=0 (21 passed, ENABLE_BEHAVIOR_PROFILE_REBUILD=true exported; [netguard] blocked 2 from 2 nodes, same sentinels)
(5) pins + CI-order set (flag unset):
[pyt] tag=g7fin-pins start=2026-11-05 15:18:59 end=2026-11-05 15:19:27 elapsed=29s bound=1200s status=FAIL rc=1 (14 files: 3 failed = d16 r10 / d17 r9 / s19 r15 env CRLF, 946 passed; [hermeticity] 949; [netguard] blocked 0)
[pyt] tag=g7fin-ciorder start=2026-11-05 15:19:29 end=2026-11-05 15:20:58 elapsed=89s bound=1200s status=FAIL rc=1 (22 files = GREEN's 21 + the gate rows: 3 failed = the same 3 env nodes, 1164 passed; [netguard] blocked 22 from 21 nodes = test_hermeticity_pins by design)
(6) comm set: see the section below. Corpus gate, fences, full jest below.
(7) CLAUDE.md readers by the import graph (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire):
[pyt] tag=g7fin-readers start=2026-11-05 15:18:10 end=2026-11-05 15:18:29 elapsed=19s bound=600s status=OK rc=0 (510 passed; [netguard] blocked 24 from 2 nodes = the s04 neutralized-supabase sentinels)
(8) ruff 0.16.5 --select E9,F63,F7,F82 --no-cache on the 14 touched python files: All checks passed!; py_compile OK.
(9) hook files: NOT MEASURED. The unit touches no .githooks file; the rulings do not rule these files out, so they were run ALONE (after every other pytest) at the 1800 s ceiling: [pyt] tag=g7fin-hook-notdash start=2026-11-05 16:25:24 end=2026-11-05 16:55:29 elapsed=1804s bound=1800s status=TIMEOUT rc=124 (-k "not dash": 327 collected / 167 selected; the log reached test_precommit_hook_phase_b.py; tests/test_precommit_hook.py showed '.....FFF' before the cut, failure text not reached, unread). The once-alone re-run and the -k dash half did not fit the 2-hour budget: the driver started tag g7fin-hook-dash and I stopped that tree at once (taskkill of my own driver PID, command line matched my tag and cwd); no [pyt] line for it. The pre-commit hook itself ran green on both commits.

## Comm set (zero-regression gate)
- HEAD: 700 files (GREEN's 699 comm_members + tests/test_s81_g7_gate_rows.py) in 28 chunks of <= 25, bound 1200, + tests/test_secret_scan_static.py alone. Totals 26892 passed, 53 skipped, 105 deselected, 39 xfailed, 15 failed + 2 errors = 17 FAILED/ERROR node ids (head_failed.txt).
  [pyt] tag=g7fin-comm-chunk_00 start=2026-11-05 15:22:08 end=2026-11-05 15:22:51 elapsed=43s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_01 start=2026-11-05 15:22:54 end=2026-11-05 15:23:57 elapsed=62s bound=1200s status=FAIL rc=1
  [pyt] tag=g7fin-comm-chunk_02 start=2026-11-05 15:24:00 end=2026-11-05 15:24:45 elapsed=45s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_03 start=2026-11-05 15:24:49 end=2026-11-05 15:26:08 elapsed=78s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_04 start=2026-11-05 15:26:12 end=2026-11-05 15:27:56 elapsed=104s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_05 start=2026-11-05 15:28:02 end=2026-11-05 15:28:37 elapsed=35s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_06 start=2026-11-05 15:28:43 end=2026-11-05 15:29:29 elapsed=47s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_07 start=2026-11-05 15:29:34 end=2026-11-05 15:30:32 elapsed=58s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_08 start=2026-11-05 15:30:35 end=2026-11-05 15:33:33 elapsed=178s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_09 start=2026-11-05 15:33:36 end=2026-11-05 15:33:54 elapsed=18s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_10 start=2026-11-05 15:33:56 end=2026-11-05 15:34:40 elapsed=44s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_11 start=2026-11-05 15:34:44 end=2026-11-05 15:35:02 elapsed=18s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_12 start=2026-11-05 15:35:08 end=2026-11-05 15:35:30 elapsed=22s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_13 start=2026-11-05 15:35:35 end=2026-11-05 15:36:38 elapsed=64s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_14 start=2026-11-05 15:36:45 end=2026-11-05 15:37:47 elapsed=62s bound=1200s status=FAIL rc=1
  [pyt] tag=g7fin-comm-chunk_15 start=2026-11-05 15:37:53 end=2026-11-05 15:38:25 elapsed=32s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_16 start=2026-11-05 15:38:30 end=2026-11-05 15:38:55 elapsed=25s bound=1200s status=FAIL rc=1
  [pyt] tag=g7fin-comm-chunk_17 start=2026-11-05 15:38:59 end=2026-11-05 15:41:01 elapsed=122s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_18 start=2026-11-05 15:41:06 end=2026-11-05 15:42:49 elapsed=103s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_19 start=2026-11-05 15:42:53 end=2026-11-05 15:44:56 elapsed=123s bound=1200s status=FAIL rc=1
  [pyt] tag=g7fin-comm-chunk_20 start=2026-11-05 15:45:01 end=2026-11-05 15:46:58 elapsed=117s bound=1200s status=FAIL rc=1
  [pyt] tag=g7fin-comm-chunk_21 start=2026-11-05 15:47:03 end=2026-11-05 15:47:45 elapsed=42s bound=1200s status=FAIL rc=1
  [pyt] tag=g7fin-comm-chunk_22 start=2026-11-05 15:47:50 end=2026-11-05 15:49:44 elapsed=113s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_23 start=2026-11-05 15:49:50 end=2026-11-05 15:50:17 elapsed=27s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_24 start=2026-11-05 15:50:19 end=2026-11-05 15:51:17 elapsed=57s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_25 start=2026-11-05 15:51:21 end=2026-11-05 15:52:18 elapsed=56s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_26 start=2026-11-05 15:52:22 end=2026-11-05 15:53:06 elapsed=44s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-comm-chunk_27 start=2026-11-05 15:53:10 end=2026-11-05 15:53:35 elapsed=25s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-secretscan start=2026-11-05 15:53:37 end=2026-11-05 15:54:13 elapsed=36s bound=600s status=OK rc=0
- BASE RECORD at 05303c6f (stored: harness/base_records/05303c6f01348610fa7c813e6588c7cea4b89734/a0bfab9529396f4db8aeaf0bd12b41117c594c8d5e2f9f8618c829ea1ec25ad2.{files,txt,header.txt}; 695 files = 700 + secret_scan minus the 6 unit files absent at base): GC-9 per-file reuse: 501 REUSED from the 6869a3e6 record ab9758ed... (unchanged since 6869a3e6; neither the file nor its imported tests.* modules names result_gate / response_builder / error_handler / text_routes / image_routes / url_routes / SmartCompareApp / CLAUDE.md / CLAUDE_MD; not a glob / walk / listdir / iterdir / scandir reader); 0 needed from dd959a10 (every reused member is in ab9758ed); 194 RUN at 05303c6f (163 by reference, 15 walkers, 12 changed by #390, 4 not in any record = GREEN's re-derivation members) in the DETACHED junction-free scratch worktree S81-G7_final/bw (git worktree add --detach; removed with git worktree remove --force; `ls` = gone; git worktree list has no S81-G7_final entry).
  The first base attempt (g7fin-base-bchunk_00..07) was a pytest USAGE error (CR characters in the chunk lists written by python on Windows; rc=4-class, each 1-2 s, "file or directory not found"); logs kept in basec/usage_err/; NOT a result. Re-run (after the corpus gate, never beside it):
  [pyt] tag=g7fin-base2-bchunk_00 start=2026-11-05 16:12:56 end=2026-11-05 16:13:38 elapsed=42s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-base2-bchunk_01 start=2026-11-05 16:13:41 end=2026-11-05 16:14:19 elapsed=38s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-base2-bchunk_02 start=2026-11-05 16:14:24 end=2026-11-05 16:16:07 elapsed=103s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-base2-bchunk_03 start=2026-11-05 16:16:11 end=2026-11-05 16:16:48 elapsed=38s bound=1200s status=FAIL rc=1
  [pyt] tag=g7fin-base2-bchunk_04 start=2026-11-05 16:16:52 end=2026-11-05 16:19:39 elapsed=167s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-base2-bchunk_05 start=2026-11-05 16:19:43 end=2026-11-05 16:21:31 elapsed=108s bound=1200s status=FAIL rc=1
  [pyt] tag=g7fin-base2-bchunk_06 start=2026-11-05 16:21:33 end=2026-11-05 16:22:55 elapsed=82s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-base2-bchunk_07 start=2026-11-05 16:22:59 end=2026-11-05 16:24:01 elapsed=62s bound=1200s status=OK rc=0
  [pyt] tag=g7fin-base2-secretscan start=2026-11-05 16:24:03 end=2026-11-05 16:24:37 elapsed=34s bound=600s status=OK rc=0
  Base FAILED: 8 run (personalization_bundle_c x2, s10 r06, s16 r27 x5) + 9 reused (auth_interceptor x2, page_scraping x2, prompt_truth x2, d16 r10, d17 r9, s19 r15) = 17.
- comm -13 (HEAD-only) EMPTY; comm -23 (base-only) EMPTY: the HEAD set is exactly the 17 environmental nodes of the base record; the cold-tiktoken pair tests/test_prompt_truth.py (ERROR) identical both sides.
- A stricter variant (also treating app.main / TestClient users as #390-dependent) would have run 250 files; the ruling's textual rule (194) was applied. Recorded for the gate.

## Corpus gate (alone, no pytest alive)
HEAD (sc-s81-g7): RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656; OVERALL SHA256 d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf; exit=0 start=2026-11-05 15:56:04 end=2026-11-05 16:04:37
BASE 05303c6f (scratch worktree bw): RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656; OVERALL SHA256 d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf; exit=0 start=2026-11-05 16:04:38 end=2026-11-05 16:12:49
Both equal to each other and to GC-4 (no STOP).

## Client
- Junction present (node_modules/@babel/core and .bin/jest exist); node v24.11.1; jest 29.7.0.
- Fourteen fences by path: [jest] tag=g7fin-fences start=2026-11-05 15:36:08 end=2026-11-05 15:36:31 rc=1 -> Test Suites 1 failed, 13 passed, 14 total; Tests 4 failed, 236 passed = d5 / k2 / k4 / k5 of config/nativeBundle.w37 (the known drift nodes).
- FULL jest once from sc-s81-g7/SmartCompareApp with --json --outputFile=S81-G7_final/full.json: [jest] tag=g7fin-full start=2026-11-05 15:36:50 end=2026-11-05 15:37:26 rc=1 -> from full.json: numTotalTestSuites 410, passed suites 406, failed 1; numTotalTests 4006, numPassedTests 3976, numFailedTests 4 (the four w37 nodes d5 / k2 / k4 / k5), pending 13, todo 13. = the expected 3,976 + the four.

## Footprint
git diff --stat origin/main...HEAD: 17 files changed, 2095 insertions(+), 77 deletions(-), hunks only (no whole-file diff): CLAUDE.md, app/services/{kb_operator,kb_serve,price_service,structured_comparison_service}.py, data/variant_hint_learned.json (deleted), scripts/{cron_kb_coverage,cron_learning}.py, tests/fixtures/s81_d22c_flag_off_golden.json, tests/test_s81_d16b_operator_dates.py, test_s81_d17b_coverage_paging.py, test_s81_d22c_profile_select.py, test_s81_d22c_varhint_retire.py, test_s81_d22d_learning_hardening.py, test_s81_g5_gate_rows.py, test_s81_g7_gate_rows.py, test_variant_llm_hint_b3b.py = exactly the 17-path list of the task. (DV-3: RB-G7-7 counts "the 10 GREEN files + the gate-rows file = 11 paths"; the measured footprint vs main is 17 because the 6 frozen RED / golden files were committed in the GREEN commit (GREEN report) and are new vs main too; no other file.)
App / scripts bytes in the round commit: none (git show --stat ce3ec2a7 = CLAUDE.md + tests/test_s81_g7_gate_rows.py).

## PR body
S81-G7_final/PR_BODY.md: 12565 bytes (<= 25,600), pure ASCII, no trailer (the orchestrator appends it); one section per unit, the four minors by id with dispositions, the gate rows and their mutants, the comm paragraph from the measured lists, the hook sentence, every stated limit kept + L-D22c-6 / L-D22d-4, [NATIVE READ] EMPTY.

## Deviations
- DV-1: the literal `git diff 4b0f3b9c HEAD -- app scripts data tests` EMPTY check replaced by its measurable meaning (the delta equals main's own #389/#390 delta, patch-id equal; the unit's diff patch-id equal; every unit blob identical).
- DV-2: the six frozen files' working copies came back CRLF from the rebase checkout; gates ran on LF bytes = GC-1 = CI; restored to CRLF at the end so git status is empty (blobs untouched). An LF working copy shows " M" in git status on this box with an empty `git diff` (stat-only), which is why the final state is CRLF.
- DV-3: footprint 17, not 11 (see Footprint).
- DV-4: the first base comm attempt was a usage error (CR in chunk lists), re-run under new tags (g7fin-base2-*).
- DV-5: the base comm set includes the 4 GREEN re-derivation members (no record had them; run at base: green).

## NOT MEASURED
- The hook test files tests/test_precommit_hook*.py (both halves): TIMEOUT once (g7fin-hook-notdash), re-run and the dash half not run (budget). The 3 F seen in tests/test_precommit_hook.py before the cut are unexplained (not read).
- Nothing else: every other gate of RB-G7-7 measured.

## git status --short (final)
(empty) - verified 16:57 after the six frozen working copies were written back as CRLF; HEAD ce3ec2a7, origin/main..HEAD = 2 commits; .qa-mutation.lock absent; scratch worktree removed.
