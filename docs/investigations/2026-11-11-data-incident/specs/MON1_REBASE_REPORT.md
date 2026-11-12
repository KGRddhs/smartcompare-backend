# MON1 FINAL ROUND REBASE REPORT (agent Opus 5.5, 2026-11-12 11:00-11:50 AST)

Unit: MON1 LLM-CREDENTIAL-HEALTH (FOCUS), worktree sc-inc-mon1, branch fix/inc-mon1-llm-credential-health.
HEAD before: 95f50119ac9aeb05d8025bad4400aa6d93c0ad69 (verified; git status --short empty before anything).
Base (fetched origin/main): 1dd0241471906d924a486b41913c6efdaccf7cdd.
HEAD after: cccfb855323b2dacbe89b08c6438fe8cd594d4d3 (da693ec7 + 6a6c5334 replayed; cccfb855 = the pin-row commit, through the hook, Co-Authored-By Claude Opus 5.5).
Tree ids: origin/main^{tree} = b5e8624c^{tree} = 8bd9d6e525f31f1985874d24614ddf97a8f93d8d (the stored record reused; no base pass, no scratch worktree created).

## Conflicts and resolutions
- CLAUDE.md, commit 1 (c6592b53), ONE region: the Feature Flags pointer line (:342). UNION: main's line verbatim (S81-04c, S81-12 LEGAL-V3, G-INC-1 sentences) with the MON1 sentence inserted after the G-INC-1 sentence, before `REAL_ACTION_MIN_SECONDS`. Verified: the branch line minus the MON1 sentence equals the a74caba7 line byte for byte. The MON1 block auto-merged after the G-INC-1 block (:650-656), one blank line before `## Tests` (:658). Resolved with Python, CRLF preserved. A slip in my first resolution write (the slice kept the opening marker line and dropped the empty line after the pointer line) was caught before staging and repaired from origin/main's bytes; the staged result's `git diff origin/main -- CLAUDE.md` = the pointer line changed + the 8-line block added, nothing else.
- Commit 2 (95f50119) replayed with no conflict. git diff --check clean; no conflict markers in CLAUDE.md, app/ or tests/ at HEAD.
- Every non-CLAUDE.md file of the footprint has the same blob at HEAD as at 95f50119 (no application byte changed by the replay or the round).

## Footprint
git diff --stat origin/main...HEAD: exactly the 16 files of RB-MON1F-4, 3383 insertions(+), 6 deletions(-); no whole-file diff; the .githooks diff is empty.

## Pin rows (tests/test_inc_mon1_gate_rows.py; the frozen RED files never edited)
- G15 test_g15_a_late_event_stamps_the_cooldown: rejected t0, ok t5, rejected t10 (suppressed, pending), a confirming failure at t950 sends the late rejected; ok at t955 is emitted; rejected at t960 (10 s after the late event, 960 s after the first rejected event) sends NO event and logs the suppressed WARNING once.
- G16 test_g16_the_test_reset_clears_the_pending_marks: a pending mark is set; _reset_credential_health_state() empties _PENDING and the snapshot.
- My first G15 version failed on its own assertion (caplog still held the t10 suppression line): [pyt] tag=inc-mon1-final-g1516 start=2026-11-12 11:05:36 end=2026-11-12 11:05:42 elapsed=6s bound=600s status=FAIL rc=1. Fixed with caplog.clear() before the last step: [pyt] tag=inc-mon1-final-g1516b start=2026-11-12 11:05:58 end=2026-11-12 11:06:02 elapsed=5s bound=600s status=OK rc=0 (2 passed, netguard 0).
- Mutants (byte copy of app/services/llm_credential_health.py, working-copy sha256 e9a828cafc32c0372d2e99a0dee51f6de1327fb97c1d7c188b37c7caf24e98c8; an exact-string edit matching once; restore sha-compared equal after each; .qa-mutation.lock created and removed; driver mut/drive.py, logs mut/mut_*.log):
  - RV9 (the late branch's `_LAST_ALERT[key] = now` removed): KILLED by G15 (AssertionError: one more 'rejected' event). [pyt] tag=inc-mon1-final-mut-rv9 start=2026-11-12 11:06:22 end=2026-11-12 11:06:29 elapsed=7s bound=600s status=FAIL rc=1 (1 failed, 17 passed)
  - RV12 (`_PENDING.clear()` removed from the reset seam): KILLED by G16 (AssertionError: the openai/rejected mark survived the reset). [pyt] tag=inc-mon1-final-mut-rv12 start=2026-11-12 11:06:31 end=2026-11-12 11:06:40 elapsed=8s bound=600s status=FAIL rc=1 (1 failed, 17 passed)
- sha256 of the committed blobs (LF): tests/test_inc_mon1_credential_health.py 10061c0a64da034588602258d5020c015f97e95f7020e9eb0251a2c94bf56c71 (unchanged); tests/test_inc_mon1_probe.py 2950c33e70d30a3dd69361a9726ce1421b778c4a9a00354067b213a530845880 (unchanged); tests/test_inc_mon1_gate_rows.py e542d3e3c2fcb8059ec0196d051edfb87f278ad3c9168a9d82dbd7b9f5d5645a (was d8a07d4f...).
- sha256 of the working copies (CRLF) after the round: credential_health 8f1c89e4d403a9d572c757e533c8ba340926a3632674686f2e4ac05ceb83ce5d; probe 120f8834feca10a0f25674c60bbe6a8a06332c56182ca15a6ac0c27024a7bdca; gate rows 21a1e83a43162cf99b96d84056c99068a2c9da31b557d5d356a1c42f5e0c22a9. Before the rebase these working copies were LF on disk and hashed to 10061c0a / 2950c33e / d8a07d4f; the rebase checkout rewrote them CRLF under core.autocrlf=true. Content unchanged (the committed blobs are identical).

## Gates (RB-MON1F-5, in the order of RB-MON1F-7)
(1) [pyt] tag=inc-mon1-final-unit-off start=2026-11-12 11:08:33 end=2026-11-12 11:09:07 elapsed=34s bound=600s status=OK rc=0 (flag unset; 148 passed; netguard 0; hermeticity 148)
    [pyt] tag=inc-mon1-final-unit-on start=2026-11-12 11:09:10 end=2026-11-12 11:09:45 elapsed=35s bound=600s status=OK rc=0 (ENABLE_LLM_CREDENTIAL_PROBE=true; 148 passed; netguard 0)
(4) ruff --select E9,F63,F7,F82 --no-cache on the 14 touched .py files: All checks passed; py_compile rc 0; black --check on the 5 files this unit adds to .github/black-clean-paths.txt: 5 files would be left unchanged.
(2) CI-order set, 35 files (the s20 lifespan user first, the 2 RED files, the gate rows, then 29 test files reading /health, sentry_service, llm_credential or a lifespan, tests/test_s81_s03_llm_ledger_v2.py, tests/test_paid_route_metering.py; the list is ciorder_files.txt):
    [pyt] tag=inc-mon1-final-ciorder start=2026-11-12 11:11:45 end=2026-11-12 11:14:40 elapsed=175s bound=1200s status=FAIL rc=1 (3081 passed, 1 skipped; 2 failed = tests/test_s81_s24_auth_throttle.py::test_r92_hygiene + ::test_p83_red_file_setenv_hygiene, the CRLF working-copy rows, both in the base record; netguard 62 from 19 nodes; hermeticity 3084)
(3) The whole free tier at HEAD: 773 files (the stored 770-file list, identical to every tests/test_*.py at origin/main minus the four test_precommit_hook*.py, plus the 3 unit files), 31 chunks of at most 25, bound 1200: 29,832 passed, 53 skipped, 25 failed + 2 errors = 27 FAILED/ERROR ids. Base record b5e8624c.../9a02556d... (27 ids): comm -13 EMPTY, comm -23 EMPTY (the cold-tiktoken pair of tests/test_prompt_truth.py on both sides). HEAD record stored: harness/base_records/cccfb855323b2dacbe89b08c6438fe8cd594d4d3/a3b268422b56352a5ae3f7047f976486eae33504cffef477d0f6cbe92472bc2f.{files,txt,pyt.log,header.txt}. netguard 764 attempts from 222 nodes in all. Hook files NOT run (ruling RB-MON1F-5 (3)); `git diff --stat origin/main...HEAD -- .githooks` empty. The chunk lines:
    [pyt] tag=inc-mon1-final-head-01 waited=45s for the box pytest slot
    [pyt] tag=inc-mon1-final-head-01 start=2026-11-12 11:16:03 end=2026-11-12 11:16:39 elapsed=36s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-02 waited=3s for the box pytest slot
    [pyt] tag=inc-mon1-final-head-02 start=2026-11-12 11:16:44 end=2026-11-12 11:17:16 elapsed=32s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-mon1-final-head-03 start=2026-11-12 11:17:19 end=2026-11-12 11:17:46 elapsed=27s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-04 start=2026-11-12 11:17:48 end=2026-11-12 11:18:39 elapsed=51s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-05 start=2026-11-12 11:18:41 end=2026-11-12 11:19:19 elapsed=38s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-06 start=2026-11-12 11:19:27 end=2026-11-12 11:19:47 elapsed=20s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-07 start=2026-11-12 11:19:49 end=2026-11-12 11:20:09 elapsed=20s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-08 start=2026-11-12 11:20:12 end=2026-11-12 11:20:33 elapsed=21s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-09 start=2026-11-12 11:20:35 end=2026-11-12 11:22:09 elapsed=94s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-10 start=2026-11-12 11:22:11 end=2026-11-12 11:23:26 elapsed=75s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-11 start=2026-11-12 11:23:28 end=2026-11-12 11:24:12 elapsed=44s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-12 start=2026-11-12 11:24:19 end=2026-11-12 11:24:59 elapsed=40s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-13 start=2026-11-12 11:25:02 end=2026-11-12 11:25:19 elapsed=17s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-14 start=2026-11-12 11:25:21 end=2026-11-12 11:25:38 elapsed=17s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-15 start=2026-11-12 11:25:40 end=2026-11-12 11:26:17 elapsed=36s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-16 start=2026-11-12 11:26:19 end=2026-11-12 11:26:55 elapsed=36s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-mon1-final-head-17 start=2026-11-12 11:26:57 end=2026-11-12 11:27:21 elapsed=23s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-18 start=2026-11-12 11:27:28 end=2026-11-12 11:27:52 elapsed=24s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-mon1-final-head-19 start=2026-11-12 11:27:54 end=2026-11-12 11:28:09 elapsed=15s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-20 start=2026-11-12 11:28:11 end=2026-11-12 11:31:21 elapsed=190s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-21 start=2026-11-12 11:31:23 end=2026-11-12 11:32:48 elapsed=84s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-22 start=2026-11-12 11:32:50 end=2026-11-12 11:33:37 elapsed=47s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-mon1-final-head-23 waited=2s for the box pytest slot
    [pyt] tag=inc-mon1-final-head-23 start=2026-11-12 11:33:40 end=2026-11-12 11:35:21 elapsed=102s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-mon1-final-head-24 waited=2s for the box pytest slot
    [pyt] tag=inc-mon1-final-head-24 start=2026-11-12 11:35:30 end=2026-11-12 11:36:26 elapsed=56s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-mon1-final-head-25 waited=2s for the box pytest slot
    [pyt] tag=inc-mon1-final-head-25 start=2026-11-12 11:36:29 end=2026-11-12 11:37:45 elapsed=77s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-26 start=2026-11-12 11:37:48 end=2026-11-12 11:38:38 elapsed=51s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-27 start=2026-11-12 11:38:41 end=2026-11-12 11:39:21 elapsed=40s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-28 waited=2s for the box pytest slot
    [pyt] tag=inc-mon1-final-head-28 start=2026-11-12 11:39:25 end=2026-11-12 11:40:18 elapsed=52s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-29 start=2026-11-12 11:40:26 end=2026-11-12 11:41:23 elapsed=57s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-30 start=2026-11-12 11:41:25 end=2026-11-12 11:42:04 elapsed=39s bound=1200s status=OK rc=0
    [pyt] tag=inc-mon1-final-head-31 waited=3s for the box pytest slot
    [pyt] tag=inc-mon1-final-head-31 start=2026-11-12 11:42:08 end=2026-11-12 11:42:32 elapsed=24s bound=1200s status=OK rc=0
(5) The full jest suite once: [jest] tag=inc-mon1-final-jest-full version=29.7.0 waited=8s start=2026-11-12 11:43:59 end=2026-11-12 11:44:37 rc=1 (the H5 probe empty before the start). Suites 1 failed / 3 skipped / 408 passed (412); Tests 4 failed / 13 skipped / 13 todo / 4,039 passed (4,069); Snapshots 41 passed. The only failed suite is config/nativeBundle.w37 with exactly its 4 accepted drift nodes (d5, k2, k4, k5). The other 13 fences PASS in that run (brand/inAppMark.u4c, clientTruth/medicalNote, privacyManifest, shareTruth .s74, clipboardFallbackService (+edges), DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService (+edges), ResultsScreen.timeout). Log: jest_full.log.

## PR body
PR_BODY.md in this folder: 25,481 bytes (python), pure ASCII, LF, WITHOUT the attribution line (about 25,550 once the orchestrator appends it). Carries: base and HEAD shas; O2 and O3 ANSWERED 2026-11-12 at the recommendation; G15 / G16 with RV9 / RV12; "68 test files plus the gate-rows file"; owner step 1's meta phrase removed; L-18 (a late redundant recovery event; a held recovery is sent only by a later served call or, with the probe on, by the next tick); M-4's owner steps by name; the final-round gates as measured (the whole-tree comm paragraph, the jest line); PROOF ON THE PHONE unchanged; "merged, NOT yet proven". To stay under 25,600 bytes (LC-3) the GREEN and fix-round gate sections were condensed into one "earlier rounds" section that points at specs/MON1_FIX1_REPORT.md and specs/MON1_FIX1_REVERIFY.md.

## NOT MEASURED
Nothing. (The hook test files were not run by ruling RB-MON1F-5 (3); no base pass by ruling.)

## Deviations
- The CI-order file list was re-derived (the fix round's exact 21-file list is not in this scratchpad): 35 files, the same GC-11 order (lifespan user, RED files, gate rows) followed by the health / sentry / lifespan readers.
- The frozen files' WORKING-COPY sha256 values changed (an LF -> CRLF checkout by the rebase); their committed blobs are byte-unchanged.
- My first G15 version failed on its own assertion (caplog scope); corrected before any mutant ran.
- A resolution slip in CLAUDE.md (described above) was repaired before staging; the final diff against main is exactly the union.

## git status --short (worktree, at the end)
(empty)
