# S81-G8 FINAL ROUND (REBASE-AND-GATES) REPORT

Agent: Opus 5.5 (claude-opus-5-5), 2026-11-07 08:48-09:03 AST. Written through the shell (python). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g8, branch feature/s81-g8-followups.

## State
- HEAD before: fe2ba6703d22e48842bf4af2d714d0716aa5f8bf (status clean, verified first).
- origin/main (fetched 08:48): daf86d32d222a885c42dc537e83c25483527a83b = the base. `git rebase origin/main`: 'Current branch feature/s81-g8-followups is up to date.' 0 commits replayed, no conflict, no resolution.
- HEAD after: fd947d38c9612c43f4ec241027e2548084ed693e (2 ahead of origin/main: fe2ba670 GREEN + fd947d38 the round commit; through the hook, 'All checks passed!', trailer Co-Authored-By: Claude Opus 5.5).
- git status --short at the end: empty. .qa-mutation.lock removed. No push, no PR.

## Frozen files (GC-1), first and last, disk and HEAD blob: all EQUAL
- tests/test_s81_b1b_url_telemetry.py 7dc7f8aa9f79ba0d241bfebf9ce5486c1f0a307f75b53741ac82d666355cee71
- tests/test_s81_s11b_result_aggregates.py 957020e30f9a88358c43e00db3fd4293b98271d3c3cb6c483bbae8c3ef4a0cf0
- tests/test_s81_s18b_store_label.py 4fc4b3996834e09626a712aa68d88319f5139414aac845ee2d9511123b048adf
- tests/fixtures/s81_g8_flag_off_golden.json 497754da580815222767a5138226cf2d16bc2e981bcac3dff462ea86fc15eb8f

## The round commit (RB-G8-3)
- NEW tests/test_s81_g8_gate_rows.py sha256 26305eca0d5acd3df04fe55a480c64ba8565f2264b6aa85b550d160da4ef6bd2 (disk = blob; 0 bytes > 127; LF; 149 lines). Rows: test_g8_gr1_partial_ctx_output_lang_both_paths (captures every dict assigned to _partial_build_ctx through a __setattr__ subclass installed as scs.StructuredComparisonService, then runs the real compare_from_text / compare_from_text_streaming through the S18 faked-compare driver; the first ctx: REST keys == the 7-key base literal, stream starts with the 8-key base head, no output_lang without a lang or with output_lang=None; with 'ar' / 'en' = the same items + ('output_lang', lang) last), test_g8_gr2_aggregates_fold_host_case_and_space, test_g8_gr3_label_value_url_guard (positive control + '/', ':', 'http', 'HTTP' cases; fallback on both surfaces in en and ar; exactly one WARNING per file state).
- CLAUDE.md (CRLF kept, 1078 CRLF lines before and after; sha256 31fffe43... -> 07ec1c0c...): line 92 the older 045 / 047 clause replaced by the RB-G8-3 wording; the appended GREEN sentence replaced by the RB-G8-3 050 / 052 + 046 / 049 / 048 sentence; '(035, 036 and anything newer than 044)' -> '... not named here)'; the 11b row gains the G8-GR2 sentence; the 18b row gains G8-GR1 / G8-GR3 (GR1-GR3 = MIN-2..MIN-4) and L-S18b-6. Edited text pure ASCII (line 92 keeps its 30 pre-existing non-ASCII bytes, the same count before and after); no added line holds scoring_method + enum. git diff --stat for the round: CLAUDE.md 3 / 3 lines.

## Gate-row mutants (byte copies in the notes folder, exact-string edit matching once, restore + sha256 compare EQUAL each time, under .qa-mutation.lock)
- OWN-3 (app/services/structured_comparison_service.py, row test_g8_gr1): KILLED rc=1, AssertionError | [pyt] tag=g8fin-mut-OWN-3 start=2026-11-07 08:50:51 end=2026-11-07 08:50:55 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 2 deselected, 10 warnings in 3.42s
- OWN-4 (app/services/structured_comparison_service.py, row test_g8_gr1): KILLED rc=1, AssertionError | [pyt] tag=g8fin-mut-OWN-4 start=2026-11-07 08:50:55 end=2026-11-07 08:50:59 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 2 deselected, 10 warnings in 3.33s
- OWN-5 (app/services/structured_comparison_service.py, row test_g8_gr1): KILLED rc=1, AssertionError | [pyt] tag=g8fin-mut-OWN-5 start=2026-11-07 08:50:59 end=2026-11-07 08:51:04 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 2 deselected, 10 warnings in 3.62s
- OWN-6 (app/services/kb_serve.py, row test_g8_gr2): KILLED rc=1, AssertionError | [pyt] tag=g8fin-mut-OWN-6 start=2026-11-07 08:51:04 end=2026-11-07 08:51:08 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 2 deselected, 11 warnings in 3.49s
- OWN-6b (app/services/kb_serve.py, row test_g8_gr2): KILLED rc=1, AssertionError | [pyt] tag=g8fin-mut-OWN-6b start=2026-11-07 08:51:09 end=2026-11-07 08:51:13 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 2 deselected, 11 warnings in 3.37s
- OWN-8 (app/services/store_labels.py, row test_g8_gr3): KILLED rc=1, AssertionError | [pyt] tag=g8fin-mut-OWN-8 start=2026-11-07 08:51:13 end=2026-11-07 08:51:17 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 2 deselected, 11 warnings in 3.65s
- OWN-8b (app/services/store_labels.py, row test_g8_gr3): KILLED rc=1, AssertionError | [pyt] tag=g8fin-mut-OWN-8b start=2026-11-07 08:51:18 end=2026-11-07 08:51:22 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 2 deselected, 11 warnings in 3.79s
- OWN-3 REST literal entry dropped; OWN-4 stream literal entry dropped; OWN-5 REST entry unconditional; OWN-6 hosts.add(retailer); OWN-6b hosts.add(retailer.lower()); OWN-8 _valid_value URL guard -> return True; OWN-8b 'http' in value (no lower). 7 / 7 KILLED. OWN-5 (ruled equivalent in production) is killed by GR1's no-key assertion. OWN-9 = L-S18b-6 (not pinned).
- Pre-commit run of the rows: [pyt] tag=g8fin-gr-off start=2026-11-07 08:50:21 end=2026-11-07 08:50:25 elapsed=4s bound=600s status=OK rc=0 | 3 passed, 10 warnings in 2.67s

## Gates at HEAD fd947d38 (one pytest at a time; only the stall monitor python processes were live on the box, no foreign pytest)
- ruff --select E9,F63,F7,F82 --no-cache tests/test_s81_g8_gate_rows.py: All checks passed; py_compile clean; bytes > 127 = 0.
- git diff --stat origin/main...HEAD: exactly the 14 allowed files, hunks only, 10094 insertions / 17 deletions (CLAUDE.md 14, the gate-rows file 149).
- (1) units OFF: [pyt] tag=g8fin-units-off start=2026-11-07 08:55:24 end=2026-11-07 08:55:31 elapsed=7s bound=600s status=OK rc=0 | 37 passed, 11 warnings in 6.01s
- (1) units ON (the three flags exported in the runner call only): [pyt] tag=g8fin-units-on start=2026-11-07 08:55:31 end=2026-11-07 08:55:38 elapsed=7s bound=600s status=OK rc=0 | 37 passed, 11 warnings in 5.59s
- (2) conflicted test files: none (no conflict).
- (3) R8 pair: [pyt] tag=g8fin-r8 start=2026-11-07 08:57:44 end=2026-11-07 08:58:06 elapsed=22s bound=600s status=OK rc=0 | 273 passed, 1 warning in 20.04s
- (4) paid-route metering unset: [pyt] tag=g8fin-paid-off start=2026-11-07 08:58:06 end=2026-11-07 08:58:11 elapsed=4s bound=600s status=OK rc=0 | 21 passed, 13 warnings in 3.24s
- (4) paid-route metering exported: [pyt] tag=g8fin-paid-on start=2026-11-07 08:58:11 end=2026-11-07 08:58:15 elapsed=4s bound=600s status=OK rc=0 | 21 passed, 13 warnings in 3.39s
- (5) CI-order set (24 files = spec 12.1 + gate rows): [pyt] tag=g8fin-ciorder start=2026-11-07 08:55:50 end=2026-11-07 08:57:28 elapsed=98s bound=1200s status=FAIL rc=1 | 1 failed, 1719 passed, 18 warnings in 96.21s (0:01:36) ; the one failure tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (known CRLF environmental).
- (6)/(7) CLAUDE.md readers by the import graph (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire) + test_s81_kb_schema + the 13 tests/test_migration_*.py + the gate rows (run before the commit on the identical bytes): [pyt] tag=g8fin-readers start=2026-11-07 08:54:23 end=2026-11-07 08:55:00 elapsed=37s bound=1200s status=OK rc=0 | 1304 passed, 10 deselected, 14 warnings in 35.92s
- (6) comm: REUSE. The round changes no app / scripts file, so GREEN's 715-file HEAD run (29 chunks, HEAD FAILED = the 24 environmental ids = the stored record base_records/daf86d32d222a885c42dc537e83c25483527a83b/ea0d2f1beeeec1668aae965d6514dd51ce0d3771919fd9d5b888f08c049b46f5.txt; comm -13 EMPTY) stands; the files the round touches (gate rows + CLAUDE.md readers + migration readers) re-ran at HEAD above with 0 failures, so comm -13 vs the record is EMPTY. No base worktree created (record reused, LC-6).
- tests/test_secret_scan_static.py alone: [pyt] tag=g8fin-secretscan start=2026-11-07 08:57:37 end=2026-11-07 08:57:44 elapsed=7s bound=600s status=OK rc=0 | 31 passed, 1 warning in 6.29s
- Corpus gate NOT repeated (no app / scripts change in the round); GREEN's HEAD OVERALL SHA256 200474dfcecf2bcc625eb66b3c3fbe65a4a66f2d35b51037aaf5a6b13351dc3f = base stands.
- Fences (14 + b3a by path, node v24.11.1, jest 29.7.0, junction verified, untouched): [jest] tag=g8fin-fences start=08:58:34 end=08:58:41 rc=1 | Test Suites: 1 failed, 14 passed, 15 total | Tests: 4 failed, 242 passed, 246 total | the red suite config/nativeBundle.w37 with exactly d5 / k2 / k4 / k5; b3a green.
- FULL jest ONCE: [jest] tag=g8fin-full start=09:01:09 end=09:01:29 rc=1 | full.json: 4006 tests, 3976 passed, 4 failed (the four config/nativeBundle.w37 nodes d5 / k2 / k4 / k5), 13 pending, 13 todo; 410 suites (406 passed, 1 failed, 3 pending) = the expected baseline.
- (9) hook test files tests/test_precommit_hook*.py: NOT RUN (the unit touches no .githooks file; RB-G8-4 rules them not run).

## PR body
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/8723f7aa-4b51-496c-9ed1-d602ed517c8b/scratchpad/S81-G8_final/PR_BODY.md: 14,651 bytes (python len of the bytes), 0 bytes > 127, 33 [NATIVE READ] rows kept; base daf86d32 / HEAD fd947d38; adversary SOUND + GR1-GR3 + L-S18b-6 (OWN-5 equivalent, killed by GR1); counts 34 + 3 gate rows, 24 + 7 mutants; the apply-record rewrite named; comm 715 vs ea0d2f1b... REUSED; corpus pair; fences; full-jest figure; L-B1b-1..4 / L-S11b-1..4 / L-S18b-1..6 + the R-G8-3 note; owner steps incl. the apply record.

## NOT MEASURED
- The hook test files (ruled not run). The corpus gate (ruled not repeated). The full 715-file comm at the final HEAD (ruled REUSE; the round touched no app / scripts file).

## Deviations
- DV1: the gate-row mutants are 7 (OWN-3, OWN-4, OWN-5, OWN-6, OWN-6b, OWN-8, OWN-8b), not 3; the extra variants strengthen GR1-GR3 and are all KILLED; the PR body states 24 + 7.
- DV2: the GREEN draft's trailing attribution line was dropped from the final body (the orchestrator appends it, RB-G8-6), so the body is pure ASCII.
- DV3: the task's gate (6) wording names a base full-suite run in a scratch worktree; RB-G8-4 rules REUSE of the stored record (no app / scripts change), so no scratch worktree was created.
- DV4: the CLAUDE.md readers + migration readers ran once, before the round commit, on bytes identical to the committed HEAD (the commit changed no byte; disk sha = blob sha for both files).

## Files in the notes folder
- PR_BODY.md, REBASE_REPORT.md, commit_msg.txt, edit_claude.py, CLAUDE.md.before, mutants.py, mutants.json, mut_*.log, bytecopy_*, gr_off.log, units_off.log, units_on.log, ciorder.log, readers.log, secretscan.log, r8.log, paid_off.log, paid_on.log, fence_paths.txt, fences.log, full.json, full_jest.log, write_pr_body.py, write_report.py.
