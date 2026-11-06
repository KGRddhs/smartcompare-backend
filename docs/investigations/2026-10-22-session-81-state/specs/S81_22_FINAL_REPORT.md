# S81-22 FINAL ROUND REPORT (rebase + pin rows + gates; agent Opus 5.5, 2026-11-06 20:10-21:05 AST)

- Worktree sc-s81-s22, branch feature/s81-s22-compare-runs. HEAD before c22ff9c03ccb39273c32bdb190f72607b6ad9fb5 (clean). Base fetched origin/main 05ccaed2635386faed427d63157b5387a636d235. HEAD after 5a82f30e4a87b33f1b23c8d880c655c86d55aba3 (3 ahead: f96b2348 GREEN replay, c0a5b198 FIX1 replay, 5a82f30e final round). No push, no PR, no further rebase.
- git status --short at the end: EMPTY. .qa-mutation.lock removed. Scratch worktrees bw (05ccaed2) and hw (HEAD, core.autocrlf=false) removed; git worktree list shows neither; neither held a node_modules junction.

## Replay (RB-S22-1)
- merge-tree conflict set re-measured after the fetch = CLAUDE.md, tests/test_s81_kb_schema.py, tests/test_s81_s05_request_context.py (as ruled).
- Commit 1 (0d588d0b -> f96b2348): CLAUDE.md 2 hunks: (a) the Feature Flags pointer line (:341): both sides inserted at the same offset of the base line; each side verified = base + one pure insertion; union = base[:i] + the S81-SF1 sentence + the S81-22 sentence + base[i:]; (b) the block: the S81-SF1 block kept after S81-G7, one blank line, then the S81-22 block. tests/test_s81_kb_schema.py: SF1's E2 comment line + this branch's E1 comment line + for n in ("051",): ; the two P02_ALLOWED entries intact. tests/test_s81_s05_request_context.py: 3 hunks, union: both allowlist entries (database_service.py then compare_runs.py), both attr sets (_LOG_SEARCH_CTX_ATTRS then _RUNS_CTX_ATTRS), both _CTX_CONSUMER_ATTRS entries. CRLF kept (byte-level Python resolver, resolve1.py).
- Commit 2 (c22ff9c0 -> c0a5b198): CLAUDE.md 1 hunk (the moved block as context): resolved = SF1 block + blank + the fix commit's S81-22 block; verified ours' S81-22 lines == 0d588d0b's block and theirs == c22ff9c0's block byte for byte (resolve2.py).
- git diff --check clean after each continue; no <<<<<<< / >>>>>>> in CLAUDE.md, app/, tests/.
- Patch-id --stable of 18cb9e04..c22ff9c0 vs origin/main..HEAD per file: 12 / 15 identical (every app / scripts / migrations / railway / new test file); the 3 differing are exactly the unioned files (pre_patchids.txt / post_patchids.txt). Unioned files vs main (numstat): CLAUDE.md 7/1, kb_schema 6/1, s05 13/0: only this unit's lines.
- Footprint git diff --stat origin/main...HEAD: the 15 files the brief lists, +5008 / -4; no whole-file diff.
- Frozen RED blobs (git show HEAD:<path> | sha256): compare_runs db13c005e04f3e9986190a538f6baa77ddaa587178ab1677f8399360922000eb, judge b7c2c377e4c6b8c5b0db77dc16a746963b16f6f765910275c60df436577d8430: before the rebase, after the replay, at the end: identical.

## Round commit (RB-S22-2) 5a82f30e
- tests/test_s81_s22_gate_rows.py (+54 lines): G22-GR6 test_g22_gr6_field_status_boundary (a field_status of exactly 16,384 serialized bytes kept, 16,385 -> {"truncated": true}); G22-GR7 test_g22_gr7_escalation_answer_capped_counted_once (one escalation whose answer note is 450 chars: escalation.sent 1, escalation.answer_capped 1, batch.answer_capped 0). New blob sha256 fc22cc7e1313694520409605f3e31ba8f6760e69100c53540ce32011ae6e61b2 (fix-round blob 6ad6b7ea...). Pure ASCII; LF blob.
- Green first: [pyt] argv=["C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe", "-m", "pytest", "-p", "no:cacheprovider", "-p", "no:randomly", "--timeout=120", "-m", "not (live_unit or live_db or integration)", "tests/test_s81_s22_gate_rows.py"] (13 passed).
- Mutants (byte copies under .qa-mutation.lock, restored, sha-compared): rv17 compare_runs.py size > FIELD_STATUS_MAX_BYTES -> >= : KILLED (AssertionError at gate_rows:279) [pyt] argv=["C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe", "-m", "pytest", "-p", "no:cacheprovider", "-p", "no:randomly", "--timeout=120", "-m", "not (live_unit or live_db or integration)", "tests/test_s81_s22_gate_rows.py", "-k", "test_g22_gr6"]; restored sha ff5aac75... equal. rv18 cron_compare_judge.py esc["answer_capped"] += 1 -> pass : KILLED (assert 0 == 1 at gate_rows:305) [pyt] argv=["C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe", "-m", "pytest", "-p", "no:cacheprovider", "-p", "no:randomly", "--timeout=120", "-m", "not (live_unit or live_db or integration)", "tests/test_s81_s22_gate_rows.py", "-k", "test_g22_gr7"]; restored sha f54f1a28... equal.
- CLAUDE.md in place (CRLF kept, 2 lines changed): the gate-row range G22-GR1..GR7 with GR6 / GR7 named; L-MARKER widened by m3 / m4. No hook-test sentence exists in CLAUDE.md's S81-22 block (the stale sentence was the PR body's, m5): corrected in the PR body only (D2).
- ONE commit through the hook (All checks passed!), trailer Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>.

## Gates: every [pyt] line (one pytest at a time; no foreign live pytest was seen before any run)
```
[pyt] tag=s22x-red-off start=2026-11-06 20:20:47 end=2026-11-06 20:21:01 elapsed=14s bound=600s status=FAIL rc=1
[pyt] tag=s22x-red-on start=2026-11-06 20:21:02 end=2026-11-06 20:21:18 elapsed=16s bound=600s status=FAIL rc=1
[pyt] tag=s22x-erow-off start=2026-11-06 20:21:19 end=2026-11-06 20:21:36 elapsed=17s bound=600s status=OK rc=0
[pyt] tag=s22x-erow-on start=2026-11-06 20:21:38 end=2026-11-06 20:22:03 elapsed=25s bound=600s status=OK rc=0
[pyt] tag=s22x-conf-s81_kb_schema start=2026-11-06 20:22:03 end=2026-11-06 20:22:12 elapsed=9s bound=600s status=OK rc=0
[pyt] tag=s22x-conf-migration_043_delete start=2026-11-06 20:22:13 end=2026-11-06 20:22:22 elapsed=9s bound=600s status=OK rc=0
[pyt] tag=s22x-conf-s81_s05_request_cont start=2026-11-06 20:22:22 end=2026-11-06 20:22:27 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=s22x-r8 start=2026-11-06 20:22:28 end=2026-11-06 20:22:47 elapsed=19s bound=600s status=OK rc=0
[pyt] tag=s22x-paid-off start=2026-11-06 20:22:48 end=2026-11-06 20:22:52 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=s22x-paid-on start=2026-11-06 20:22:53 end=2026-11-06 20:22:57 elapsed=4s bound=600s status=OK rc=0
[pyt] tag=s22x-claude-readers start=2026-11-06 20:22:58 end=2026-11-06 20:23:04 elapsed=6s bound=600s status=OK rc=0
[pyt] tag=s22x-pins-off start=2026-11-06 20:23:04 end=2026-11-06 20:25:01 elapsed=116s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-pins-on start=2026-11-06 20:25:02 end=2026-11-06 20:26:52 elapsed=111s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-ciorder start=2026-11-06 20:26:53 end=2026-11-06 20:27:49 elapsed=56s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-head-c00 start=2026-11-06 20:27:50 end=2026-11-06 20:28:20 elapsed=30s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c01 start=2026-11-06 20:28:20 end=2026-11-06 20:28:53 elapsed=33s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-head-c02 start=2026-11-06 20:28:54 end=2026-11-06 20:29:10 elapsed=17s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c03 start=2026-11-06 20:29:11 end=2026-11-06 20:30:13 elapsed=61s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c04 start=2026-11-06 20:30:13 end=2026-11-06 20:30:49 elapsed=35s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c05 start=2026-11-06 20:30:49 end=2026-11-06 20:31:05 elapsed=16s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c06 start=2026-11-06 20:31:06 end=2026-11-06 20:31:20 elapsed=15s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c07 start=2026-11-06 20:31:21 end=2026-11-06 20:31:46 elapsed=24s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c08 start=2026-11-06 20:31:47 end=2026-11-06 20:32:25 elapsed=39s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c09 start=2026-11-06 20:32:26 end=2026-11-06 20:33:35 elapsed=68s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c10 start=2026-11-06 20:33:35 end=2026-11-06 20:34:12 elapsed=37s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c11 start=2026-11-06 20:34:13 end=2026-11-06 20:34:34 elapsed=22s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c12 start=2026-11-06 20:34:35 end=2026-11-06 20:34:47 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c13 start=2026-11-06 20:34:48 end=2026-11-06 20:35:07 elapsed=19s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c14 start=2026-11-06 20:35:08 end=2026-11-06 20:35:40 elapsed=33s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-head-c15 start=2026-11-06 20:35:41 end=2026-11-06 20:36:22 elapsed=40s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-head-c16 start=2026-11-06 20:36:22 end=2026-11-06 20:36:44 elapsed=22s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c17 start=2026-11-06 20:36:45 end=2026-11-06 20:37:05 elapsed=20s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-head-c18 start=2026-11-06 20:37:06 end=2026-11-06 20:39:17 elapsed=131s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c19 start=2026-11-06 20:39:18 end=2026-11-06 20:40:54 elapsed=97s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c20 start=2026-11-06 20:40:55 end=2026-11-06 20:42:24 elapsed=89s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-head-c21 start=2026-11-06 20:42:25 end=2026-11-06 20:44:01 elapsed=96s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-head-c22 start=2026-11-06 20:44:02 end=2026-11-06 20:44:45 elapsed=43s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-head-c23 start=2026-11-06 20:44:46 end=2026-11-06 20:45:55 elapsed=69s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c24 start=2026-11-06 20:45:56 end=2026-11-06 20:46:16 elapsed=20s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c25 start=2026-11-06 20:46:17 end=2026-11-06 20:47:08 elapsed=52s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c26 start=2026-11-06 20:47:09 end=2026-11-06 20:48:00 elapsed=50s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c27 start=2026-11-06 20:48:00 end=2026-11-06 20:48:21 elapsed=21s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c28 start=2026-11-06 20:48:22 end=2026-11-06 20:48:59 elapsed=37s bound=1200s status=OK rc=0
[pyt] tag=s22x-head-c29 start=2026-11-06 20:49:00 end=2026-11-06 20:49:05 elapsed=6s bound=1200s status=OK rc=0
[pyt] tag=s22x-base-c00 start=2026-11-06 20:49:21 end=2026-11-06 20:50:13 elapsed=52s bound=1200s status=OK rc=0
[pyt] tag=s22x-base-c01 start=2026-11-06 20:50:14 end=2026-11-06 20:51:26 elapsed=72s bound=1200s status=OK rc=0
[pyt] tag=s22x-base-c02 start=2026-11-06 20:51:27 end=2026-11-06 20:51:59 elapsed=32s bound=1200s status=OK rc=0
[pyt] tag=s22x-base-c03 start=2026-11-06 20:51:59 end=2026-11-06 20:54:26 elapsed=147s bound=1200s status=OK rc=0
[pyt] tag=s22x-base-c04 start=2026-11-06 20:54:27 end=2026-11-06 20:55:47 elapsed=80s bound=1200s status=FAIL rc=1
[pyt] tag=s22x-base-c05 start=2026-11-06 20:55:48 end=2026-11-06 20:57:22 elapsed=94s bound=1200s status=OK rc=0
[pyt] tag=s22x-base-c06 start=2026-11-06 20:57:23 end=2026-11-06 20:57:32 elapsed=9s bound=1200s status=OK rc=0
[pyt] tag=s22x-lfproof start=2026-11-06 20:57:32 end=2026-11-06 20:57:45 elapsed=13s bound=600s status=OK rc=0
[pyt] tag=s22x-secretscan start=2026-11-06 20:57:45 end=2026-11-06 20:57:54 elapsed=8s bound=600s status=OK rc=0
```
- Unit gates: RED + gate rows unset 209 / 211 and exported 209 / 211 (red: test_b02_one_transaction_ascii_lf + test_j01_script_exists_and_off_first, the LF-bytes readers in this box's CRLF working copy; s22x-lfproof in an LF checkout of HEAD: 211 / 211). E-rows 756 / 756 both states; each conflicted file alone green (529 / 51 / 176); R8 pair 273; paid metering 21 both states; CLAUDE.md readers 79; pins (46 files) unset 3544 passed + b02 / j01 / r06 + 2 tiktoken ERRORs; exported 3540 + the same + the four L-I2I6 nodes (test_s81_s03 i2 / i6, the stated S81-22d precondition); U13 / M13-21 green both (no re-record); CI-order (19 files) 1770 passed + r06 + 2 tiktoken (identical noise).
- Jest: fences [jest] tag=s22x-fences start=2026-11-06 20:21:01 end=2026-11-06 20:21:10 rc=1 : 13 / 14 suites, 236 passed, 4 failed = config/nativeBundle.w37 d5 / k2 / k4 / k5. Full once: [jest] tag=s22x-full start=2026-11-06 20:21:31 end=2026-11-06 20:21:50 rc=1 : 3,976 passed, 4 failed (the w37 nodes), 13 pending, 13 todo, 41 / 41 snapshots (full.json).
- Comm: HEAD set 732 files (head_set.txt) = the GREEN's 729 + tests/test_referral_share_status_lifetime.py, tests/test_s81_sf1_surfaces_be.py (app/ rglob walker), tests/test_s81_sf1_gate_rows.py; 30 / 30 chunks, no TIMEOUT, 28,671 passed. HEAD FAILED 24 ids (head_failed.txt). Base record base_records/05ccaed2.../48158306040c03a47f796111202cc390acf667a5dcf521715e95f6d0889e9305 (729 files; 575 reused per file from 18cb9e04/e701a8ba... with 10 ids, 154 run at 05ccaed2 in 7 chunks with 12 ids; reasons base_run_why.tsv): 22 ids, all environmental. comm -23 EMPTY; comm -13 = the two head-only CRLF working-copy nodes above (green in the LF checkout). tests/test_secret_scan_static.py alone 31 passed.
- Lint: ruff E9,F63,F7,F82 --no-cache on the 11 touched python files: All checks passed; py_compile rc 0; sqlfluff 4.3.0 on 048 + rollback: clean; railway.judge.json json.loads ok.
- Corpus gate NOT repeated (the extraction spine is untouched by this branch and by SF1).

## NOT MEASURED
- tests/test_precommit_hook*.py: not run, per RB-S22-3 / RB-S22-5 (the re-verifier measured them alone on the fix-round bytes, green: 167 + 157 passed, 3 skipped); the unit touches no .githooks file.

## Deviations
- D1: RB-S22-4 names a 16-file footprint; measured (and the brief's list) = 15 files.
- D2: no hook-test sentence in CLAUDE.md to correct; the correction is in the PR body.
- D3: 2 head-only nodes red in the CRLF working copy (rebase checkout); green in an LF checkout of the same HEAD; environmental.
- D4: the base-record reuse test reads each member's own text (the ruling's criterion); app.main-transitive importers whose text names none of the SF1 modules were reused.
- PR body: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/4478042e-6f11-47b0-addf-eb1422827e28/scratchpad/S81-22_final/PR_BODY.md (pure ASCII, LF, no attribution line: the orchestrator appends it).
