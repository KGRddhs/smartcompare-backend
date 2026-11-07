# S81-24 FINAL ROUND (REBASE-AND-GATES) REPORT, Opus 5.5, 2026-11-07 12:59-13:50 AST

VERDICT: BLOCKED. The replay, the round commit and every gate ran. The comm set of record shows 12 branch-only-new FAILED nodes: the frozen P73 row `test_p73_hop_probe_off_silent`. It depends on test order, it would likely show in CI, and fixing it needs an edit to the frozen RED file, which is outside this round's authority.

## Identity
- Worktree sc-s81-s24, branch feature/s81-s24-auth-throttle-v2.
- head_before: ba4079cce1bb0adfcab2fb6f35efa9f31278bc92 (verified; git status --short was empty before the first command).
- base_main: origin/main = 39ac80ba437760d1a77eaac9670faeea505f08f4 (git fetch origin main).
- head_after: a920190bb991488306712fdf1aeed4a080a092ff (3 ahead of origin/main):
  - 0775995d = replayed f8f64d9d
  - 0e9b0fc9 = replayed ba4079cc
  - a920190b = the round commit (CLAUDE.md only, through the hook; trailer Co-Authored-By: Claude Opus 5.5)
- No push, no PR, no further rebase, no stash, reset or checkout.

## Step 1: the replay (`git rebase --onto origin/main daf86d32 feature/s81-s24-auth-throttle-v2`)
The only conflict was CLAUDE.md, on commit 1 of 2 (two hunks). Commit 2 replayed clean.
- :341 Feature Flags line: both sides inserted at the same offset (5079), after the S81-22 sentence. Resolved as UNION = base + main's S81-G8 sentence + the branch's S81-24 sentence (merge order). Computed with Python on bytes.
- :614 block: resolved as the S81-G8 block (main, 5 lines), one blank line, the S81-24 block (branch, 5 lines), one blank line, `## Tests`.
- :92 apply record and the S81-08b row: no conflict. Main's text was kept at the replay.
- Line endings: CRLF kept (1084 CRLF, 0 bare LF). `git diff --check` was clean after the continue. The grep for <<<<<<< / >>>>>>> over CLAUDE.md, app/ and tests/ is empty.
- Patch-id equality (git patch-id --stable, per file) held for every non-CLAUDE.md hunk:
  - auth_routes 970d0d1f
  - request_id 15afda6a
  - auth_throttle d371667a (commit 1) and 6f79a414 (commit 2)
  - _env_safety a7ad273f
  - RED file 069dadca
  - fix1_rows 229824e1
  - gate_rows 5879075c
- CLAUDE.md content checks:
  - commit 2's +/- lines are sha-identical (239a366b both sides);
  - commit 1's block lines are sha-identical (abd20967 both sides); only the :341 line differs (main's G8 sentence).
  - Records: S81-24_final/patchids_before.txt and patchids_after.txt.
- Frozen and fix-round blobs, hashed after the replay and again LAST (`git show HEAD:<path>` | sha256):
  - tests/test_s81_s24_auth_throttle.py 7fdf71db5b2cc43e34b24674b62d3eb57e117b1c8fa683719471b10c4c562228
  - tests/test_s81_s24_fix1_rows.py f96a9dd8e47c65641c3b01da15200f56c21f640ac32f13e91d969e8419bc23ba
  - tests/test_s81_s24_gate_rows.py 5b5916139bd6a1b43708a681f7b8c05ddd3a086940cd99d9c8c444961590c233
  - app/services/auth_throttle.py 4ed97e78fef5f74ca26735ba844fcd545671fb45870ab79bed1993c97b2590c7
  - The working copy equals each blob.

## Step 2: the round commit (RB-S24-3), CLAUDE.md only
Exact-string replacements in Python (each old string matched once), CRLF kept, added text pure ASCII:
- (a) :92: both clauses take the EXACT ruled after-wording.
- (b) :513 Activation sentence and :515 Owner steps: the EXACT ruled after-wording.
- (b) the OTA-precondition sentence: DEVIATION D1 (below). The committed text is "The OTA precondition is the DATED ledger line of this flip ON, and it is MET (the 2026-11-07 09:00 line: deployment cffeb4eb), never the merge:".
- (c) L-F1 and L-F2 appended after L-S24-19 in the S81-24 stated-limits row, in the row's "L-id text" style.
- The CLAUDE.md blob is ca9a3ab1e5e11ea30dc50668d1dd9a188a3f612516873522c9cf1745eeafac14; the working copy (CRLF) is f0e6ae61bfaaa6ff689b3467ab7a089b530b14b823e12a748a412219046664a5.
- `git diff --numstat origin/main...HEAD` CLAUDE.md: 10 / 4.

## Pin rows and mutants
- No new test row and no new test file in this round. The ruling makes the round commit CLAUDE.md only, and the frozen file stays byte-identical, so its sha is unchanged at 7fdf71db....
- No mutant was run in this round. The CLAUDE.md rewrites are covered by the existing readers: test_s81_s08b_gate_rows RB8-4 / RB8-5a, test_s81_s08b_legacy_fingerprint R11, test_ci_gates and the others, all green at HEAD.
- .qa-mutation.lock was never created.

## [pyt] lines (every gate; logs under S81-24_final/logs/)
```
[pyt] tag=s24fin-cmdreaders-exact start=2026-11-07 13:07:41 end=2026-11-07 13:08:03 elapsed=21s bound=600s status=FAIL rc=1   (the EXACT RB-S24-3 (b) wording: 1 failed test_s81_s08b_gate_rows::test_rb8_4_ota_precondition_wording, 509 passed; [hermeticity] 510; [netguard] blocked 24 from 2 nodes (sentinel))
[pyt] tag=s24fin-cmdreaders start=2026-11-07 13:11:39 end=2026-11-07 13:11:57 elapsed=18s bound=600s status=OK rc=0   (six CLAUDE.md readers by the import graph: 510 passed; [hermeticity] 510; [netguard] blocked 24 from 2 nodes (sentinel))
[pyt] tag=s24fin-unit-off start=2026-11-07 13:12:52 end=2026-11-07 13:13:02 elapsed=9s bound=600s status=FAIL rc=1   (2 failed r92 / p83: the rebase left the four LF files CRLF in the working copy; see D2)
[pyt] tag=s24fin-unit-on start=2026-11-07 13:13:04 end=2026-11-07 13:13:14 elapsed=10s bound=600s status=FAIL rc=1   (same two, D2)
[pyt] tag=s24fin-unit-off2 start=2026-11-07 13:13:51 end=2026-11-07 13:14:00 elapsed=9s bound=600s status=OK rc=0   (212 passed; [hermeticity] 212; [netguard] blocked 0)
[pyt] tag=s24fin-unit-on2 start=2026-11-07 13:14:03 end=2026-11-07 13:14:12 elapsed=9s bound=600s status=OK rc=0   (212 passed, flags + synthetic pepper + eight knobs exported in the call only; [hermeticity] 212; [netguard] blocked 0)
[pyt] tag=s24fin-pins-off start=2026-11-07 13:14:22 end=2026-11-07 13:15:00 elapsed=39s bound=600s status=OK rc=0   (316 passed, 1 skipped, 2 deselected; [hermeticity] 317)
[pyt] tag=s24fin-pins-on start=2026-11-07 13:15:03 end=2026-11-07 13:15:37 elapsed=34s bound=600s status=OK rc=0   (316 passed, 1 skipped, 2 deselected; [hermeticity] 317; [netguard] blocked 0)
[pyt] tag=s24fin-r8pair start=2026-11-07 13:15:40 end=2026-11-07 13:16:07 elapsed=27s bound=600s status=OK rc=0   (273 passed; [netguard] blocked 0)
[pyt] tag=s24fin-paid-off start=2026-11-07 13:16:10 end=2026-11-07 13:16:16 elapsed=6s bound=600s status=OK rc=0   (21 passed; [netguard] blocked 2 from 2 nodes (sentinel))
[pyt] tag=s24fin-paid-on start=2026-11-07 13:16:18 end=2026-11-07 13:16:23 elapsed=5s bound=600s status=OK rc=0   (21 passed)
[pyt] tag=s24fin-ciorder start=2026-11-07 13:16:52 end=2026-11-07 13:18:08 elapsed=76s bound=1200s status=FAIL rc=1   (19 files: 2 failed = the two baselined test_auth_interceptor social nodes, 789 passed, 1 skipped, 2 deselected)
[pyt] tag=s24fin-migreaders start=2026-11-07 13:18:12 end=2026-11-07 13:18:35 elapsed=23s bound=600s status=OK rc=0   (13 test_migration_* + test_s81_kb_schema: 791 passed, 10 deselected)
[pyt] tag=s24fin-secretscan start=2026-11-07 13:18:38 end=2026-11-07 13:18:47 elapsed=9s bound=600s status=OK rc=0   (31 passed)
[pyt] tag=s24fin-base39-c00 start=2026-11-07 13:19:14 end=2026-11-07 13:19:19 elapsed=6s bound=1200s status=OK rc=0   (BASE 39ac80ba scratch worktree, the 7 RUN members: 76 passed, 7 deselected, 0 failed)
[pyt] tag=s24fin-comm-c00 start=2026-11-07 13:19:22 end=2026-11-07 13:19:55 elapsed=33s bound=1200s status=FAIL rc=1
[pyt] tag=s24fin-comm-c01 start=2026-11-07 13:19:58 end=2026-11-07 13:20:32 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c02 start=2026-11-07 13:20:35 end=2026-11-07 13:21:08 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c03 start=2026-11-07 13:21:14 end=2026-11-07 13:22:17 elapsed=63s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c04 start=2026-11-07 13:22:19 end=2026-11-07 13:23:19 elapsed=60s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c05 start=2026-11-07 13:23:21 end=2026-11-07 13:23:46 elapsed=25s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c06 start=2026-11-07 13:23:51 end=2026-11-07 13:24:19 elapsed=28s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c07 start=2026-11-07 13:24:45 end=2026-11-07 13:25:17 elapsed=31s bound=1200s status=FAIL rc=1
[pyt] tag=s24fin-comm-c08 start=2026-11-07 13:25:19 end=2026-11-07 13:27:58 elapsed=158s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c09 start=2026-11-07 13:28:00 end=2026-11-07 13:29:36 elapsed=96s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c10 start=2026-11-07 13:29:39 end=2026-11-07 13:30:49 elapsed=69s bound=1200s status=FAIL rc=1
[pyt] tag=s24fin-comm-c11 start=2026-11-07 13:30:52 end=2026-11-07 13:31:55 elapsed=63s bound=1200s status=FAIL rc=1   (22 failed = 10 environmental + the 12 P73 nodes)
[pyt] tag=s24fin-comm-c12 start=2026-11-07 13:31:58 end=2026-11-07 13:33:01 elapsed=64s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c13 start=2026-11-07 13:33:04 end=2026-11-07 13:34:03 elapsed=59s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c14 start=2026-11-07 13:34:07 end=2026-11-07 13:35:01 elapsed=54s bound=1200s status=OK rc=0
[pyt] tag=s24fin-comm-c15 start=2026-11-07 13:35:04 end=2026-11-07 13:35:11 elapsed=7s bound=1200s status=OK rc=0
[pyt] tag=s24fin-p73-b1 start=2026-11-07 13:39:31 end=2026-11-07 13:39:50 elapsed=19s bound=600s status=FAIL rc=1   (s08b..s10b + P73: P73 12 failed)
[pyt] tag=s24fin-p73-b2 start=2026-11-07 13:39:53 end=2026-11-07 13:40:29 elapsed=36s bound=600s status=FAIL rc=1   (s11b..s18b + P73: P73 green; 6 environmental)
[pyt] tag=s24fin-p73-b3 start=2026-11-07 13:40:32 end=2026-11-07 13:40:50 elapsed=18s bound=600s status=FAIL rc=1   (s19..s23 + P73: P73 12 failed)
[pyt] tag=s24fin-p73-test_s81_s08b_legacy_fingerprint start=2026-11-07 13:42:27 end=2026-11-07 13:42:33 elapsed=6s bound=600s status=OK rc=0   (97 passed)
[pyt] tag=s24fin-p73-test_s81_s20_result_gate start=2026-11-07 13:42:36 end=2026-11-07 13:42:47 elapsed=10s bound=600s status=FAIL rc=1   (THE MINIMAL REPRO: 12 failed = P73, 166 passed)
```
Every chunk's [hermeticity] / [netguard] lines are in logs/s24fin-comm-cNN.out and .log (sentinel blocks only).

## [jest] lines (jest 29.7.0, node v24.11.1; through the junction sc-s81-s24/SmartCompareApp/node_modules; @babel/core and .bin/jest verified; the junction was never touched)
```
[jest] tag=s24fin-fences start=2026-11-07 13:19:47 end=2026-11-07 13:19:54 rc=1   (15 suites: 14 passed, 1 failed = config/nativeBundle.w37 d5 / k2 / k4 / k5 only; b3a/nativeStrings PASS; Tests 4 failed, 242 passed)
[jest] tag=s24fin-full start=2026-11-07 13:35:36 end=2026-11-07 13:36:04 rc=1   (full.json: numPassedTests 3976, numFailedTests 4 (the four w37 nodes), numPendingTests 13, numTodoTests 13, 410 suites, 1 failed suite)
```

## The comm set of record (RB-S24-4; MAJ-RV1 + m-RV3)
- Derivation: an AST closure over tests/**/*.py (S81-24_final/comm/closure.py, output closure.json), seeded with the 370 of e3b889e4... plus the three S81-24 files. It covers Import, ImportFrom (including relative imports), and import_module / __import__ with a string literal OR a NAME bound to a string literal in the same module. It iterates to a fixpoint in both directions: importers of a member, and the test modules a member imports as support, recursively.
- Additions, each with its reason:
  - tests/test_s81_d17b_coverage_paging.py: imports the member test_s81_d17_coverage through the NAME D17 (MAJ-RV1)
  - tests/test_m13_04_full_stream_deadline.py: imported as support by the member test_prescoring_showable_guard (m-RV3)
  - tests/test_m18_region_guard_prescoring.py: imported as support by the member test_prescoring_showable_guard (m-RV3)
  - tests/test_retro_w1_3.py: imports the member test_openai_breaker
  - tests/test_s81_b1b_url_telemetry.py: imports the member test_s80_b1 (new on main)
  - tests/test_s81_g8_gate_rows.py: imports the member test_s81_s18_kb_first_serve (new on main)
  - tests/test_s81_s11b_result_aggregates.py: imports the member test_s81_s18_kb_first_serve (new on main)
  - tests/test_s81_s18b_store_label.py: imports the member test_s81_s18_kb_first_serve (new on main)
  - tests/test_migration_041_user_events_public_select_policy.py: a migration reader (RB-S24-3 names the 13 test_migration_* files; it was the only one missing)
- Hits NOT added (not collected, or excluded by rule): tests/_bundle_c_helpers, _env_safety, _netguard, _retro_r_mig_sql, _route_introspection, _tokenizer, w4_11_prompt_digest_recorder (helpers); tests/fixtures/_gen_rubric_truth_flag_on_golden.py and _gen_w4_13_flag_off_ledger.py (generators); tests/test_precommit_hook_phase_b_round2.py (the hook files).
- Set of record: 379 files (sha256 99bacbe81c9a56698265ded8f3abce425983408a5ddd3c9985b8d30923236f0a) + 3 HEAD-only = 382 at HEAD, in 16 chunks of at most 25 files (comm/chunk_00..15).
- Base 39ac80ba, built per file (comm/plan2.tsv):
  - 347 REUSED from the G9 RED record 39ac80ba/fe55771e... (same main sha);
  - 25 REUSED from the daf86d32 records (bytes unchanged; none of the eight G8 names, CLAUDE.md or data; no app.main or TestClient; no walker);
  - 7 RUN at 39ac80ba in a detached scratch worktree S81-24_final/base39 (junction-free; removed with git worktree remove --force; verified gone from git worktree list and from disk): test_demographics_rls, test_migration_037, test_migration_041, test_migration_042, test_rsc_flight_price, test_sentry_service, test_skill_frontmatter. Result: 0 FAILED.
  - STORED as harness/base_records/39ac80ba437760d1a77eaac9670faeea505f08f4/99bacbe8....{files,header.txt,txt,pyt.log}.
- Result:
  - base FAILED = 21 ids (the 20 environmental ids + tests/test_s81_s18b_store_label.py::test_r2_table_shape, a CRLF data-file id that is identical on both sides);
  - HEAD FAILED = the same 21 + the 12 P73 nodes;
  - `comm -23` EMPTY;
  - `comm -13` = the 12 tests/test_s81_s24_auth_throttle.py::test_p73_hop_probe_off_silent nodes, so it is NOT empty.

## The blocker (B1)
- `test_p73_hop_probe_off_silent` (frozen, PIN class, 12 params) asserts `sorted(h.json()) == [the five keys]` "because the TestClient runs no lifespan here". tests/test_s81_s20_result_gate.py (:1039 / :1058 `with TestClient(app_main.app, ...)`) runs the lifespan. In the same process, a later /health then carries `adapter_executor` and `redis_offloop_pool`, and the P73 AssertionError fires (minimal repro: s24fin-p73-test_s81_s20_result_gate).
- Earlier rounds never saw it because their chunks ran the RED file after the test_w* to test_z* files.
- CI (.github/workflows/ci.yml:116, `python -m pytest tests/ -v ...`, one process, test_s81_s20 sorted before test_s81_s24) very likely goes red on these 12 nodes.
- A fix is an E-row on the frozen RED file (P73 tolerating or clearing the two lifespan keys) or an isolation fixture. Neither is allowed in this round: RB-S24-3 makes it CLAUDE.md only, and GC-1 keeps the file byte-identical. It needs an orchestrator ruling and a test-only pin-fix round (LC-2: no re-verifier).

## Deviations
- D1: The EXACT RB-S24-3 (b) OTA-precondition sentence turns the frozen tests/test_s81_s08b_gate_rows.py::test_rb8_4_ota_precondition_wording red (RB8_4_REQUIRED "The OTA precondition is the DATED ledger line of this flip ON"; measured in s24fin-cmdreaders-exact). The committed wording keeps the required fragment and states MET with the same facts.
- D2: The replay re-wrote the four LF files with CRLF in the working copy (core.autocrlf=true). That turned the frozen R92 / P83 rows red, which read the working-copy bytes. The working copies were then re-written from their own HEAD blobs (`git show HEAD:<path>` > file; sha-equal to the blob, no content change). Since then `git diff` is EMPTY, but `git status --short` lists the four files as ` M` (the cached stat of an LF working copy under autocrlf). The index was not touched: `git update-index` is outside the exception list.
- D3: The comm set grew from the expected 373 to 382 (the eight closure additions + test_migration_041), each listed above.
- D4: Base membership came from the G9 RED record (stored 13:05) for 347 members, so no full scratch run was needed.

## NOT MEASURED
- The four tests/test_precommit_hook*.py: NOT RUN by ruling (RB-S24-4: no .githooks change; this unit touches no .githooks file).
- The corpus gate: NOT REQUIRED (no price-pipeline module in the diff).
- CI itself was not run (no push).

## Final state
- `git diff --stat origin/main...HEAD`: 8 files changed, 3122 insertions(+), 4 deletions(-): exactly the eight files, no whole-file diff.
- `git status --short`:
  ```
   M app/services/auth_throttle.py
   M tests/test_s81_s24_auth_throttle.py
   M tests/test_s81_s24_fix1_rows.py
   M tests/test_s81_s24_gate_rows.py
  ```
  This is stat only; `git diff` is empty (D2).
- No .env read. No flag, knob or pepper in any .env or the OS environment (exported in single runner calls only). No package manager. No git write in any other worktree. No foreign process killed. No pytest or jest left running.
- PR body: S81-24_final/PR_BODY.md (19,603 bytes, pure ASCII, no attribution line; the orchestrator appends it). It is marked DRAFT / NOT READY because of B1.
