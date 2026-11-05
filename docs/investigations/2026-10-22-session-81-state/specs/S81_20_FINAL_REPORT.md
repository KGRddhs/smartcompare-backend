# S81-20 FINAL REBASE REPORT (B2-RESULT-GATE-V2, ENABLE_RESULT_GATE) - rebase-and-gates agent, Opus 5.5, 2026-11-05
Written through the shell (python), per the harness rule.

Unit S81-20. Worktree sc-s81-s20, branch feature/s81-s20-result-gate-v2.
- HEAD before: 404b4ba525d42074a52f514ab0ac7299b857dbf4 (on 6869a3e6); git status empty before.
- base (origin/main fetched): 229b61e9349a3dbf54332b53cdd6f923b86093ec.
- replayed GREEN commit: ba0ba38f; round commit = HEAD after: 3bfb02d5d2970d739f1e02cfabc4dc87502d752b (2 ahead of origin/main). Through the hook (passed), Co-Authored-By Claude Opus 5.5. No push, no PR.
- git status --short at the end: 0 lines (empty).

## STEP 1 the replay
Conflict: CLAUDE.md only (2 hunks), as the orchestrator measured.
- Hunk 1 (:341 Feature Flags pointer line): both sides inserted one sentence at the same offset after the S81-G5 sentence. UNION: main's S81-11 sentence first, then the branch's ENABLE_RESULT_GATE sentence (verified equal to the branch line with main's sentence inserted).
- Hunk 2 (after the S81-G5 block): main's S81-11 client block (7 lines) kept verbatim, one blank line, then the branch's S81-20 block (3 lines). Every other main hunk (incl. the rewritten Frontend CohortBadge sentence) kept.
- Resolved with Python on bytes (CRLF kept: 1050 CRLF = 1050 LF); git diff --check clean; no conflict markers in CLAUDE.md / app / tests. numstat vs main after the resolution: CLAUDE.md 5 / 1 (= the GREEN's 5 / 1 vs 6869a3e6).
- git diff 404b4ba5 HEAD -- app tests: EMPTY after the replay. Frozen RED blob 6eebb584 unchanged (LF sha256 13aa83ade66d14759278e6da14668f60d48dabdcb1002b4d7bb29c0a88c0180c); gate-rows blob f88422c0 unchanged at the replay (LF sha256 c88caa06...874c). After the replay the working copies of the two new test files are CRLF (autocrlf checkout; the GREEN wrote them LF), so the sha over the CRLF bytes differs (46c6c360... / f17c64b2...); the LF-normalised sha and the blob are the frozen ones.

## STEP 2 the round commit (test + docs only)
- E9 tests/test_s81_s09_device_quota.py CLEAN_ENV +1 name (reason comment).
- E10 tests/test_s81_s10_fragrance_gate.py _CLEAR_ENV +1 name.
- E12 tests/test_s81_s18_kb_first_serve.py CLEARED_ENV +1 name.
- E14 tests/test_s81_s17_kb_ingest.py CLEARED_ENV +1 name.
- E11 tests/test_s81_s10_gate_rows.py and E13 tests/test_s81_s09_gate_rows.py: NO byte change (deviation D-F1). Neither file has an env list of its own; both import their autouse env fixture from the E10 / E9 file. Lines :252 / :288 of s10_gate_rows are single delenv calls (LEXP / ENABLE_COMPARE_AUTH_REQUIRED) inside two unrelated rows. Measured: both files green with the flag exported after E9 / E10 (s20f-e9e14-on).
- G20-GR4 in tests/test_s81_s20_gate_rows.py (+19 lines: a docstring line + one test). It drives the stream refusal end to end through the RED harness (red._budget_route(..., "stream", None)) and asserts: the ONE result_gate row has input_type text_stream, error_message result_gate:no_evidence, success False; the only usage_refund label is usage_refund.text_stream.result_gate; one refund, one record. New LF sha256 c7f532c54b2b582fd44ec760bf8e16b61d7be767c99d6b0e8e21b902145512ef (CRLF working copy 6a3409de...).
- CLAUDE.md S81-20 row edited IN PLACE (1 line changed):
  - the Accounting sentence (RB-S20-6);
  - the canary row (RB-S20-6);
  - the gate-rows list gains GR4;
  - L12 rewritten (E1-E14; the six files green exported = 46 of the 135 sweep nodes; the other 13 files / 89 nodes stay red exported);
  - L23 extended (RB-S20-8);
  - L24-L28 added after L23.
  The S81-20 row carries no comm count (no 390 there), so RB-S20-4's count edit had no anchor; the 392 is in the PR body (D-F2).
- Added lines: pure ASCII (0 non-ASCII); 0 personal / credential shapes; no new constant names. ruff E9/F63/F7/F82 clean; py_compile clean on the 6 app files + every touched test file.
- Every app file byte-identical to 404b4ba5 (working-copy sha256 equal to the GREEN table; git diff ba0ba38f HEAD -- app EMPTY).

## Pin-row mutant
A8 (input_type="text_stream" -> "text" in _s20_stream_settle; exact string, matched once) on a sha-verified byte copy of app/api/text_routes.py under .qa-mutation.lock. G20-GR4 FAILED with an AssertionError (the row shows input_type 'text') = KILLED. Restored from the copy; sha256 8e40919d0f1889ba9434856536630291e5ab8cfee34543380755cf56617190fc before and after; lock removed.

## Gates (every [pyt] line, from the pyt ledger)
[pyt] tag=s20f-gr-off start=2026-11-05 12:49:16 end=2026-11-05 12:49:22 elapsed=6s bound=600s status=OK rc=0
[pyt] tag=s20f-mut-a8 start=2026-11-05 12:49:37 end=2026-11-05 12:49:44 elapsed=6s bound=600s status=FAIL rc=1
[pyt] tag=s20f-e9e14-on start=2026-11-05 12:49:59 end=2026-11-05 12:50:19 elapsed=20s bound=600s status=FAIL rc=1
[pyt] tag=s20f-e9e14-off start=2026-11-05 12:50:27 end=2026-11-05 12:50:45 elapsed=18s bound=600s status=FAIL rc=1
[pyt] tag=s20f-unit-off start=2026-11-05 12:53:22 end=2026-11-05 12:53:30 elapsed=8s bound=600s status=OK rc=0
[pyt] tag=s20f-unit-on start=2026-11-05 12:53:31 end=2026-11-05 12:53:39 elapsed=8s bound=600s status=OK rc=0
[pyt] tag=s20f-ci-order start=2026-11-05 12:54:23 end=2026-11-05 12:57:42 elapsed=200s bound=1200s status=FAIL rc=1
[pyt] tag=s20f-r8 start=2026-11-05 12:57:54 end=2026-11-05 12:58:21 elapsed=26s bound=600s status=OK rc=0
[pyt] tag=s20f-meter-off start=2026-11-05 12:58:24 end=2026-11-05 12:58:29 elapsed=5s bound=600s status=OK rc=0
[pyt] tag=s20f-meter-on start=2026-11-05 12:58:30 end=2026-11-05 12:58:40 elapsed=10s bound=600s status=OK rc=0
[pyt] tag=s20f-erows-on start=2026-11-05 12:58:41 end=2026-11-05 12:59:18 elapsed=37s bound=600s status=OK rc=0
[pyt] tag=s20f-comm-00 start=2026-11-05 13:00:00 end=2026-11-05 13:00:57 elapsed=57s bound=1200s status=FAIL rc=1
[pyt] tag=s20f-comm-01 start=2026-11-05 13:00:58 end=2026-11-05 13:01:44 elapsed=46s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-02 start=2026-11-05 13:01:45 end=2026-11-05 13:03:15 elapsed=90s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-03 start=2026-11-05 13:03:16 end=2026-11-05 13:03:58 elapsed=41s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-04 start=2026-11-05 13:03:58 end=2026-11-05 13:06:32 elapsed=153s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-05 start=2026-11-05 13:06:34 end=2026-11-05 13:07:30 elapsed=55s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-06 start=2026-11-05 13:07:31 end=2026-11-05 13:08:01 elapsed=30s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-07 start=2026-11-05 13:08:03 end=2026-11-05 13:08:55 elapsed=52s bound=1200s status=FAIL rc=1
[pyt] tag=s20f-comm-08 start=2026-11-05 13:08:55 end=2026-11-05 13:09:39 elapsed=44s bound=1200s status=FAIL rc=1
[pyt] tag=s20f-comm-09 start=2026-11-05 13:09:40 end=2026-11-05 13:12:59 elapsed=199s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-10 start=2026-11-05 13:12:59 end=2026-11-05 13:15:25 elapsed=146s bound=1200s status=FAIL rc=1
[pyt] tag=s20f-comm-11 start=2026-11-05 13:15:27 end=2026-11-05 13:19:01 elapsed=215s bound=1200s status=FAIL rc=1
[pyt] tag=s20f-comm-12 start=2026-11-05 13:19:02 end=2026-11-05 13:21:03 elapsed=121s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-13 start=2026-11-05 13:21:04 end=2026-11-05 13:22:05 elapsed=62s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-14 start=2026-11-05 13:22:07 end=2026-11-05 13:23:25 elapsed=78s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-15 start=2026-11-05 13:23:28 end=2026-11-05 13:24:15 elapsed=47s bound=1200s status=OK rc=0
[pyt] tag=s20f-comm-secretscan start=2026-11-05 13:24:15 end=2026-11-05 13:25:48 elapsed=92s bound=600s status=OK rc=0
[pyt] tag=s20f-base-00 start=2026-11-05 13:26:18 end=2026-11-05 13:26:59 elapsed=41s bound=1200s status=OK rc=0
[pyt] tag=s20f-base-01 start=2026-11-05 13:27:00 end=2026-11-05 13:30:55 elapsed=235s bound=1200s status=OK rc=0
[pyt] tag=s20f-base-02 start=2026-11-05 13:30:56 end=2026-11-05 13:33:09 elapsed=133s bound=1200s status=FAIL rc=1
[pyt] tag=s20f-base-03 start=2026-11-05 13:33:10 end=2026-11-05 13:34:04 elapsed=54s bound=1200s status=OK rc=0
[pyt] tag=s20f-base-secretscan start=2026-11-05 13:34:04 end=2026-11-05 13:34:53 elapsed=49s bound=600s status=OK rc=0

Counts:
- s20f-gr-off: 13 passed.
- s20f-mut-a8: 1 failed (KILLED).
- s20f-e9e14-on / -off: 504 passed, 1 failed each (test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content, environmental CRLF, in the base record).
- s20f-unit-off / -on: 179 passed each (166 RED + 13 gate rows).
- s20f-ci-order (57 files = the GREEN 56 + test_s81_s09_gate_rows.py): 4635 passed, 1 failed (r06, identical to GREEN).
- s20f-r8: 273 passed.
- s20f-meter-off / -on: 21 passed each.
- s20f-erows-on (E1-E3, E5-E8 files + test_w4_13_flag_off_ledger.py, flag exported; the FY25 digests, B1 P10 / P11, the T23 snapshot): 1331 passed. The CI-order run covers the same files with the flag unset.
- Comm set: 392 files (the GREEN 390 + tests/test_migration_index_predicate_immutability.py + tests/test_openai_key_log_hygiene_s69.py) at HEAD, flag unset, 16 chunks of at most 25 (s20f-comm-00..15, bound 1200, all finished, no TIMEOUT; 17,764 passed) + tests/test_secret_scan_static.py alone (s20f-comm-secretscan OK, 31 passed). HEAD FAILED = 17 = the base record exactly (environmental: test_auth_interceptor x2, test_page_scraping x2, test_personalization_bundle_c x2, test_prompt_truth x2 (cold tiktoken, identical both sides), test_s81_d16 r10, test_s81_d17 r9, the r06 CRLF node, test_s81_s16_kb_seed r27 x5, test_s81_s19 r15). Base record at 229b61e9 = base_records/229b61e9.../dd959a10...txt (390 files = the 392 minus the two unit files absent at base): 302 REUSED per file (GC-9) from the stored 6869a3e6 record 97218ca8... (#389 changed only SmartCompareApp/ files + CLAUDE.md), 88 RUN at 229b61e9 in a removed detached junction-free scratch worktree (every CLAUDE.md / SmartCompareApp referencing file incl. the six CLAUDE.md readers by the import graph, every glob walker, the two added pins; s20f-base-00..03 + secretscan: 7,816 passed, 5 failed = the s16 r27 nodes). comm -13 (branch-only NEW) EMPTY; comm -23 EMPTY.
- Base record STORED: harness/base_records/229b61e9349a3dbf54332b53cdd6f923b86093ec/dd959a10a6dc0ce604ef1fe016d82a52ef8c903b6af9d231a53adbd18ac09ec9.(txt|files|header.txt|pyt.log), with the reused-vs-run split in the header. The scratch worktree S81-20_final/bw was removed (git worktree remove --force); git worktree list no longer shows it and the directory is gone. It never had node_modules.
- Fourteen backend-scanning client fences by path through the junction (jest 29.7.0, node v24.11.1): [jest] tag=s20f-fences rc=1: 13 / 14 suites, 236 / 240 tests; the 4 = config/nativeBundle.w37 d5 / k2 / k4 / k5 (the accepted drift nodes).
- FULL jest ONCE (LC-7), --json, figures from full.json: [jest] tag=s20f-full rc=1: numPassedTests 3976, numFailedTests 4 (the four nativeBundle.w37 drift nodes), numPendingTests 13, numTodoTests 13, of 4006; suites 406 passed / 1 failed of 410; snapshots 41 matched, 0 added / updated / unmatched / removed. Equal to the post-#389 baseline (3,976 + the four w37 nodes).
- Corpus gate NOT repeated (D6; no app change).
- Hook test files (tests/test_precommit_hook*.py) NOT run: the unit touches no .githooks file and the round args rule them out ("the hook test files NOT run (no .githooks change)"); the round commit passed the pre-commit hook.
- The two CLAUDE.md readers tests/test_ci_gates.py and tests/test_behavior_dimension_translation.py: green at HEAD (in s20f-ci-order and the comm set) and run at base (in s20f-base).

## Footprint vs origin/main (git diff --numstat origin/main HEAD): 21 paths, hunks only
5	1	CLAUDE.md
48	2	app/api/image_routes.py
126	2	app/api/text_routes.py
32	2	app/api/url_routes.py
18	0	app/middleware/error_handler.py
9	1	app/services/response_builder.py
212	3	app/services/result_gate.py
1	1	tests/test_paid_route_metering.py
1	0	tests/test_retro_w2_1.py
1	0	tests/test_s71_u13_compare_auth_required.py
1	0	tests/test_s75_fanout_identity.py
1	0	tests/test_s80_b1.py
1	0	tests/test_s80_b3_vision_identity_v2.py
3	2	tests/test_s81_kb_schema.py
1	0	tests/test_s81_s09_device_quota.py
1	0	tests/test_s81_s10_fragrance_gate.py
1	0	tests/test_s81_s17_kb_ingest.py
1	0	tests/test_s81_s18_kb_first_serve.py
216	0	tests/test_s81_s20_gate_rows.py
1765	0	tests/test_s81_s20_result_gate.py
2	1	tests/test_w4_13_measurement_truth.py

(23 expected; the two absent paths are E11 / E13, D-F1.)

## sha256 (working copy, LF-normalised, path)
d9260c3f1c231a4c3373be10824b7a70959e4021d65cf3e40e1616bb9be7f8bd 1cf7c18d9d2f7a319c2a96de7ace76e14b6fd90c51643b11ef955ee5f50b5a2b CLAUDE.md
8e260b7badb9be34cb7446f047c8067b251c54fcddcc72f77868a9990fbd5831 925536eb8ef63c9cf7a9ce9887afad93764b20180e7e9b20d666b5867bbf7884 app/api/image_routes.py
8e40919d0f1889ba9434856536630291e5ab8cfee34543380755cf56617190fc 552c33e81b15f40ea456b530b6c680c5bb7bdc13ebb021010d1c449679c24c7b app/api/text_routes.py
06fe720d8583cf39fab1c5c8090070458e320f412a24eddcc201a4b45a626484 7fe4f9be06a2314966f6bcfe60dd60cb2a8975246a41341c3f672112d68016b3 app/api/url_routes.py
a6af83ebcd1b2594f8e9812f1de4f4e506dda51358b1dd790f08a12b0ce3a1bd 95e4b14c0521ad6e58fdb0272f24af980121d2a5dc1d30d71474076639ea18ab app/middleware/error_handler.py
e90326dd15cf96c4c29076d95b2ee7904e4fe155336d257a980d7372e31f3fe9 a0d5ece85f30bd87742a9ab6ceed62dbada8f9b0956c4f53aafbc1f96d6fb764 app/services/response_builder.py
bb6d46a53293380907fa936b29145e9b8192978978d4ff5034fcfd1308689d9e a9b744d70bc2fb7c068cca09bdc1e06a328bcebc24bb359aedaa28266bbc699e app/services/result_gate.py
d32c881ba89861a413a006bfdf858c95aeb9f4cbf3cf01593ff9610db1a89465 9f43c8aef0fb880e7607894b8fc534bb2b3a13d5e1cdbb404d421743beddd482 tests/test_paid_route_metering.py
fd73703ce31da7b4f2b011b31b0240aa6638e4db8abcfce915d7ae334e521b04 e62c23b1ef729c966fef9d035942374ad6c4f9764e2f506328a1646b68d09d36 tests/test_retro_w2_1.py
0ce2ca7705b430806ca3d1f0477e7b15b6e707c3487c0d894c5804a57ede00c0 9b62157952f515d57aa13c16ea38cf6ff819a2e5c5f523a19d57a882d6136ff0 tests/test_s71_u13_compare_auth_required.py
a4198be47a3fa75a79f9b635528d2212c073c2efc97f802fddd913be04f0e769 93c59246ef6c1ee6a41f54aef6edd21ceaf448f6f6b92dcbfe47a27f9e87e4a1 tests/test_s75_fanout_identity.py
b1144ec0ca13d4dc8b06ed783cc7bbe76c99518a1c01e2504c888d8511e56379 79beede655b00aa6ca223d9c8c4e75883efd3df9b926fd373fc19a37f065700c tests/test_s80_b1.py
1eaa139b99599a0bd0972cf6536b16705c2d49692e002425a7ce2ce7a419f723 26280a2cd432a9353a4e07997a5356bffeefb2e4b6000039098603fc35bd7046 tests/test_s80_b3_vision_identity_v2.py
347eb28c0691a8fa33165c633d00e0c1ac192a19f29e8f8eb1be5f9e45a0a146 ffcbfca8a38527b49dfbdc3d9b84864c6f2e1035e130033a00870a9404794a31 tests/test_s81_kb_schema.py
3146f54d8c8e16ea72f3fdb1917289d513a9d42bfa780ad1cb5a05b22a5a3d2d 61916c65b5e7a91330122f46e9fdab9c295a5d981a0ec159f4a1a910ef545783 tests/test_s81_s09_device_quota.py
d7849252ef3553041c790cd9393a0757fc8cfa32a518e656c90636f36b59bbbb e65e08e3ccfa6c5b1143cd1201e528335001234e3c25b954f92e68ee1c7c8960 tests/test_s81_s10_fragrance_gate.py
58058c6eeb683ccdff00db4462bd3fde6ab161acf97860465d790339f09c618a 55820bd08592d24237f80fddf326b189061f221530d7ac2a6e7f029c4953ea37 tests/test_s81_s17_kb_ingest.py
f8f3218e28b7e131c21b35c36236460bdcfa27bc10ec786cd1ea6628cd81c8b2 488f3857f3cbd51bed8942a4726745b044b77c70f1a39e1ed8368c4321a19e19 tests/test_s81_s18_kb_first_serve.py
6a3409deaa4100c1e122b3e02523f347d8ebf241edcba3be7ccdd8db527b2dc2 c7f532c54b2b582fd44ec760bf8e16b61d7be767c99d6b0e8e21b902145512ef tests/test_s81_s20_gate_rows.py
46c6c360607b0960f73319740782618acbca2e05623d3446c6bbf38e3540eb65 13aa83ade66d14759278e6da14668f60d48dabdcb1002b4d7bb29c0a88c0180c tests/test_s81_s20_result_gate.py
b3036b443c79636c5839223b86ac5a8db4f4b1e0aa26f25ab14acf5f3ad053d3 3b9cb2bb11e0984ec4d10b5c9261f7614700dac68f616a38295f815cbb09d348 tests/test_w4_13_measurement_truth.py

## NOT MEASURED
- tests/test_precommit_hook*.py: not run (ruled out by the round args; no .githooks change).

## Deviations
- D-F1: E11 / E13 not edited. The two gate-rows files carry no env list and inherit E10 / E9 through the imported autouse fixture; both were measured green with the flag exported. Footprint 21 paths, not 23.
- D-F2: RB-S20-4's CLAUDE.md comm count: the S81-20 row carries no comm count, so nothing was rewritten; the 392 is in the PR body.
- D-F3: the CI-order set gained tests/test_s81_s09_gate_rows.py (57 files) so E13 is in it.
- D-F4: the fences and the full jest ran while the head comm-set pytest driver was running (one jest and one pytest at a time); no TIMEOUT anywhere.
- D-F5: an Edit-tool anchor briefly dropped a space in tests/test_s81_s17_kb_ingest.py (NOW =datetime). It was fixed before the commit (the committed diff is the one added line); s17 then re-ran green in s20f-ci-order and the comm set.

## PR body
S81-20_final/PR_BODY.md: 16,172 bytes, 0 non-ASCII, no attribution line (the orchestrator appends it).
