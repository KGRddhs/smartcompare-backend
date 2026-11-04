# S81-G4 KB-SERVE GREEN REPORT (GREEN agent, Opus 5.5, 2026-11-04)

Written through the shell (python). Base 0b19de5bcc1416111d48bc725359b95151a658ca; branch feature/s81-g4-kb-serve created; NOT COMMITTED.

## BLOCKER (STOP, needs an orchestrator ruling)
The ONE commit through the hook is refused by the pre-commit gitleaks step: `generic-api-key tests/test_s81_d16_operator_ingest.py:53`.
Line 53 of the FROZEN D16 RED file is `OPENAPI_PATHS_SHA256 = "<the 64-hex OpenAPI path-set digest>"` (the P2 literal, GC-1). gitleaks 8.30.1 with
HEAD:.gitleaks.toml reads it as an API key (the name contains 'API', the value is 64 hex). The hook uses HEAD's .gitleaks.toml (a config change judges
only LATER commits), refuses a .gitleaksignore, and an inline gitleaks:allow would edit the frozen file. Nothing else was refused (the run was
retried once after the docstring fix: the same single finding).
Options: (a) an E-row on the frozen D16 file appending `  # gitleaks:allow` to line 53 (its sha moves); (b) rename the literal (e.g.
OPENAPI_PATHSET_DIGEST) under a RULINGS_FIX E-row; (c) a separate prior PR widening .gitleaks.toml for a '*_SHA256 = <64 hex>' digest name, then this commit.
The index holds the 19 files staged (git add only; no commit, no reset / restore).

## Frozen RED files (re-hashed first and last: unchanged)
- tests/test_s81_s18_kb_first_serve.py OK
- tests/fixtures/s81_s18_flag_off_golden.json OK
- tests/test_s81_s19_gap_queue.py OK
- tests/test_s81_d16_operator_ingest.py OK
- tests/test_s81_d17_coverage.py OK

## Files (19 = 12 new + 7 edited; the spec's '13 new' list names 12 files)
| path | sha256 before | sha256 after |
|---|---|---|
| CLAUDE.md | c02ac5a5a3cb1ab413dd37e115454e99c7be8e196ee07df4abf32b21bfd1b4ab | 3e3f91f96d155011fdf5743ea7bc352b067cf1b9ff59e499c505d924ddf1ca5e |
| app/api/admin_routes.py | fdb4a93a7986bfde20beae9e0323f2c3e855abdc7bf1fc33d1198c1908635f25 | 151cddc3024ed12214cc1bcb95fdbd458abf9197fe309733031a0e6455df7a96 |
| app/api/image_routes.py | 7170301629df2a86f29662b0c7e5927682acadd68dc40eeee3ff2343d1558340 | 987e89f9362bdfc596ff6c58101321240433eb79f5419e7f44e2c35f8c5b91d5 |
| app/api/text_routes.py | 8e1d42df86194f97cd4db69fabc37df50c850ae98ffd4be0b9cd3becc8e82bb8 | 437bc724e96685c1d3b31c55573150d80d72194edc90af9da3d172316cc470e2 |
| app/services/kb_ingest.py | e12a88ad2003822efa8ec5c7873fa90a2f329a45d52925961da0a0e4fb318b54 | 00849ecacf43f74f85b031fe86db78e05c8d4429c18a1b299b524774a9b417c3 |
| app/services/structured_comparison_service.py | 79b1f729c46f4c48e403702660e31ce01547563a7a9a811308c7d340dfd45998 | 32d61a98f6b56cb026a9175f34b0c2b3f1d550d02d102bcf743f47003b231f1c |
| tests/test_s81_kb_schema.py | 9f420bc0a82b5610732f91279c8f3cfbfdcc97aae02f15341a498757011ed59e | 5a2b4d60c606a1219b246d04278d61a58bbd10ae2026d6a1834eefe44f76dc8f |
| app/services/kb_operator.py | (new) | fc17b39c9ef1994c4a850b4b4b6a76236469a5de8cda90d7eae602f346bca94a |
| app/services/kb_serve.py | (new) | 7009e45331a5b65af47a14ae0f7221aed58d4d3fb58d571aeaa36a0652884505 |
| docs/runbooks/2026-11-kb-operator-ingest.md | (new) | c1f289b6524aadca4e09ca4444c01ff760ce45a26887970e431d5c2b5e51535f |
| railway.kbcoverage.json | (new) | 5ec64a9badb80126e89c9880f6d4e50f2d7dd0b0c6149b10cc96b0d97338c9bb |
| railway.kbenrich.json | (new) | 6ad03fb14557606232bf1c91902a5f25103e384e648285b11c7b150cbd043326 |
| scripts/cron_kb_coverage.py | (new) | ff2b9c45273e10fe483b73eb445325b83520cd8e628847586b40038f176637b9 |
| scripts/cron_kb_enrich.py | (new) | 33414373aa304bfaf00f9a5fcfaea7050da28e7dcd2cede4f9c16d592caddf2e |
| tests/fixtures/s81_s18_flag_off_golden.json | (new) | 8ab15ee0c25633f8df73b8acec93dcf6568b395ed7bcfcfdd5c28ff6e0eb8d6b |
| tests/test_s81_d16_operator_ingest.py | (new) | 65d0186063d818301061cd5b3a1f491715a9f2b59ccd245a5fa3beb3b61a7758 |
| tests/test_s81_d17_coverage.py | (new) | 03b7ccf6140148c884e8e2b4f57123baee3c38207712ebedfecc320659f2f317 |
| tests/test_s81_s18_kb_first_serve.py | (new) | 7be2ed3a9c05c6680b654cf3bf548ade374873056e03ec01836e8d66cb769cd2 |
| tests/test_s81_s19_gap_queue.py | (new) | a400b6795ed166df98a59326c49f04565c60157777b6a2dce7a1bdc7481ffe84 |

git diff --cached --stat:
```
 CLAUDE.md                                     |    9 +-
 app/api/admin_routes.py                       |   62 +
 app/api/image_routes.py                       |    4 +
 app/api/text_routes.py                        |    9 +-
 app/services/kb_ingest.py                     |    5 +-
 app/services/kb_operator.py                   |  393 +++
 app/services/kb_serve.py                      |  416 ++++
 app/services/structured_comparison_service.py |  111 +-
 docs/runbooks/2026-11-kb-operator-ingest.md   |   71 +
 railway.kbcoverage.json                       |   14 +
 railway.kbenrich.json                         |   14 +
 scripts/cron_kb_coverage.py                   |  374 +++
 scripts/cron_kb_enrich.py                     |  684 ++++++
 tests/fixtures/s81_s18_flag_off_golden.json   | 3277 +++++++++++++++++++++++++
 tests/test_s81_d16_operator_ingest.py         |  615 +++++
 tests/test_s81_d17_coverage.py                |  557 +++++
 tests/test_s81_kb_schema.py                   |   10 +-
 tests/test_s81_s18_kb_first_serve.py          | 1325 ++++++++++
 tests/test_s81_s19_gap_queue.py               |  815 ++++++
 19 files changed, 8748 insertions(+), 17 deletions(-)
```
Byte copies of the 7 edited files + SHA256SUMS: <scratchpad>/S81-G4_green_before/. Edited files keep CRLF (0 non-CRLF lines each; text_routes.py
was once LF-converted by a sed -i and restored to CRLF from the same text; the before copy had 0 non-CRLF lines). New files: bytes > 127 = 0, CR = 0.

## Gates ([pyt] / [jest] lines)
- [pyt] tag=g4g-d17a elapsed=3s status=OK rc=0 (23 passed)
- [pyt] tag=g4g-s19a elapsed=5s status=OK rc=0 (34 passed)
- [pyt] tag=g4g-s18a elapsed=5s status=OK rc=0 (56 passed: S18 + D16)
- [pyt] tag=g4g-red-off start=2026-11-04 21:27:51 end=2026-11-04 21:28:02 elapsed=11s bound=600s status=OK rc=0 (642 passed; [hermeticity] 642; [netguard] blocked 0)
- [pyt] tag=g4g-red-on start=2026-11-04 21:28:10 end=2026-11-04 21:28:22 elapsed=11s bound=600s status=OK rc=0 (the seven flags in one call; 642 passed; [netguard] 0)
- [pyt] tag=g4g-ciorder-off start=2026-11-04 21:28:34 end=2026-11-04 21:29:27 elapsed=53s bound=1200s status=FAIL rc=1 (5 failed = the r27 baseline, 1535 passed; [hermeticity] 1540; [netguard] blocked 28 attempts from 10 nodes = the base figure)
- [pyt] tag=g4g-s77-d9 start=2026-11-04 21:55:28 end=2026-11-04 21:55:33 elapsed=4s bound=600s status=OK rc=0 (65 passed)
- [pyt] tag=g4g-comm-09b start=2026-11-04 21:55:44 end=2026-11-04 21:56:28 elapsed=44s bound=1200s status=FAIL rc=1 (5 failed = r27, 1176 passed; [netguard] blocked 13 from 2 nodes)
- [pyt] tag=g4g-red-on2 start=2026-11-04 21:56:47 end=2026-11-04 21:56:59 elapsed=12s bound=600s status=OK rc=0 (673 passed incl. test_legal_disclosure_s77; [netguard] 0)
- [pyt] tag=g4g-red-off2 start=2026-11-04 21:57:01 end=2026-11-04 21:57:14 elapsed=13s bound=600s status=OK rc=0 (673 passed; [netguard] 0)
- [jest] tag=g4g-fences start=2026-11-04 21:31:40 end=2026-11-04 21:31:57 rc=1 (jest 29.7.0, node v24.11.1; 13/14 suites, 236/240; failed = exactly the 4 config/nativeBundle.w37 drift nodes d5, k2, k4, k5)
- ruff 0.16.5 --select E9,F63,F7,F82 on the 4 new modules + the 5 edited app files + the test file: All checks passed; default ruff on the 4 new modules: clean; py_compile OK; json.loads OK on railway.kbenrich.json, railway.kbcoverage.json and the golden.
- Corpus gate NOT run (price_service.py not in the diff). Hook test files NOT run (no .githooks change). FULL jest NOT run (LC-7).

## Comm set (LC-6: the stored base record REUSED)
Re-derived with g4spec/comm.py at HEAD: 665 = the RED's 661 + the four RED files (0 other additions, 0 dropped); <scratchpad>/S81-G4_green/comm_head_derived.txt
(sha256 26135f397487e79304257f14daf0a675af02964be5f8c065061ca834cfff7b95). Run in 27 chunks of <= 25 + tests/test_secret_scan_static.py alone (bound 1200,
one at a time, the RED driver's FLAKY deselects and unit-env strip) vs base_records/0b19de5b.../90b85603...txt (14 nodes). First pass: HEAD 15, comm -13 =
tests/test_legal_disclosure_s77.py::test_s77_d9_bot_page_claim_matches_the_runtime (the QarenBot-emitter pin counted a docstring word in
scripts/cron_kb_enrich.py). Fixed by rewording that docstring (no code); chunk 09 re-run: HEAD 14, comm -13 EMPTY, comm -23 EMPTY (the 14 baseline nodes identical).
Chunk [pyt] lines:
```
2026-11-04 21:31:17 START comm HEAD driver: 664 files in 27 chunks (+ the secret scan, run alone)
2026-11-04 21:32:04 [pyt] tag=g4g-comm-00 start=2026-11-04 21:31:17 end=2026-11-04 21:32:03 elapsed=46s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-00.log
2026-11-04 21:32:41 [pyt] tag=g4g-comm-01 start=2026-11-04 21:32:04 end=2026-11-04 21:32:41 elapsed=37s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-01.log
2026-11-04 21:33:25 [pyt] tag=g4g-comm-02 start=2026-11-04 21:32:41 end=2026-11-04 21:33:25 elapsed=44s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-02.log
2026-11-04 21:35:17 [pyt] tag=g4g-comm-03 start=2026-11-04 21:33:27 end=2026-11-04 21:35:17 elapsed=109s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-03.log
2026-11-04 21:35:33 [pyt] tag=g4g-comm-04 start=2026-11-04 21:35:17 end=2026-11-04 21:35:32 elapsed=15s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-04.log
2026-11-04 21:35:47 [pyt] tag=g4g-comm-05 start=2026-11-04 21:35:33 end=2026-11-04 21:35:46 elapsed=13s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-05.log
2026-11-04 21:36:05 [pyt] tag=g4g-comm-06 start=2026-11-04 21:35:47 end=2026-11-04 21:36:05 elapsed=18s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-06.log
2026-11-04 21:38:16 [pyt] tag=g4g-comm-07 start=2026-11-04 21:36:05 end=2026-11-04 21:38:16 elapsed=130s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-07.log
2026-11-04 21:39:51 [pyt] tag=g4g-comm-08 start=2026-11-04 21:38:16 end=2026-11-04 21:39:51 elapsed=95s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-08.log
2026-11-04 21:40:26 [pyt] tag=g4g-comm-09 start=2026-11-04 21:39:52 end=2026-11-04 21:40:26 elapsed=34s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-09.log
2026-11-04 21:40:51 [pyt] tag=g4g-comm-10 start=2026-11-04 21:40:26 end=2026-11-04 21:40:51 elapsed=25s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-10.log
2026-11-04 21:41:05 [pyt] tag=g4g-comm-11 start=2026-11-04 21:40:52 end=2026-11-04 21:41:04 elapsed=12s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-11.log
2026-11-04 21:41:30 [pyt] tag=g4g-comm-12 start=2026-11-04 21:41:05 end=2026-11-04 21:41:30 elapsed=25s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-12.log
2026-11-04 21:41:52 [pyt] tag=g4g-comm-13 start=2026-11-04 21:41:30 end=2026-11-04 21:41:52 elapsed=22s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-13.log
2026-11-04 21:42:36 [pyt] tag=g4g-comm-14 start=2026-11-04 21:41:53 end=2026-11-04 21:42:35 elapsed=43s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-14.log
2026-11-04 21:43:00 [pyt] tag=g4g-comm-15 start=2026-11-04 21:42:36 end=2026-11-04 21:42:59 elapsed=23s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-15.log
2026-11-04 21:43:14 [pyt] tag=g4g-comm-16 start=2026-11-04 21:43:00 end=2026-11-04 21:43:14 elapsed=14s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-16.log
2026-11-04 21:46:02 [pyt] tag=g4g-comm-17 start=2026-11-04 21:43:14 end=2026-11-04 21:46:02 elapsed=168s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-17.log
2026-11-04 21:47:42 [pyt] tag=g4g-comm-18 start=2026-11-04 21:46:02 end=2026-11-04 21:47:42 elapsed=99s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-18.log
2026-11-04 21:49:28 [pyt] tag=g4g-comm-19 start=2026-11-04 21:47:42 end=2026-11-04 21:49:28 elapsed=106s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-19.log
2026-11-04 21:50:00 [pyt] tag=g4g-comm-20 start=2026-11-04 21:49:28 end=2026-11-04 21:49:59 elapsed=31s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-20.log
2026-11-04 21:51:04 [pyt] tag=g4g-comm-21 start=2026-11-04 21:50:00 end=2026-11-04 21:51:03 elapsed=64s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-21.log
2026-11-04 21:51:37 [pyt] tag=g4g-comm-22 start=2026-11-04 21:51:04 end=2026-11-04 21:51:37 elapsed=33s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-22.log
2026-11-04 21:52:29 [pyt] tag=g4g-comm-23 start=2026-11-04 21:51:39 end=2026-11-04 21:52:28 elapsed=50s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-23.log
2026-11-04 21:53:19 [pyt] tag=g4g-comm-24 start=2026-11-04 21:52:29 end=2026-11-04 21:53:18 elapsed=49s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-24.log
2026-11-04 21:53:53 [pyt] tag=g4g-comm-25 start=2026-11-04 21:53:19 end=2026-11-04 21:53:52 elapsed=33s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-25.log
2026-11-04 21:54:09 [pyt] tag=g4g-comm-26 start=2026-11-04 21:53:53 end=2026-11-04 21:54:09 elapsed=16s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-26.log
2026-11-04 21:54:31 [pyt] tag=g4g-comm-secret start=2026-11-04 21:54:09 end=2026-11-04 21:54:31 elapsed=22s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\0e351457-2b4f-4512-a571-3ecd2f577f5c\scratchpad\S81-G4_green\comm\g4g-comm-secret.log
2026-11-04 21:54:31 DONE failed=15
```

## Deviations
- Commit trailer would name the agent's own model (Co-Authored-By: Claude Opus 5.5): the task text said 'Claude Fable 5.1' AND 'the trailer names your own model'; this agent runs on Opus 5.5.
- H8: the scs call sites pass comparison_quality=None and log_verdict_key computes verdict_comparison_quality(product_data) itself (GC-4 (c)), so flag OFF H8 is exactly one env read (the prototype evaluated the quality at the call site even OFF). An explicit value (R17) is honoured.
- S81-19 rating / review_count gaps fill when the extraction carries the D08 _jsonld_facts.rating (2.5 / L6), through build_review_row insert-ignore; the prototype never filled them.
- S81-19 search candidates are restricted to the search host (same netloc) for the JSON shape too (the prototype accepted any absolute URL there and relied on the gate).
- The D16 view route answers 400 KB_STORE_UNAVAILABLE when the client is None or a read raises (never a 5xx), mirroring the ingest rule.
- CLAUDE.md / PR owner steps name SUPABASE_SERVICE_KEY (the codebase name, as the G2 block) where the spec's S81-19 owner step wrote SUPABASE_SERVICE_ROLE_KEY.
- Footprint count: 19 files (12 new + 7 edited); the spec's 12.3 says '13 new' but lists 12 files; the list matches exactly.
- An unquoted bash heredoc once executed backtick fragments while patching the PR-body generator (only 'command not found' errors; nothing outside the scratchpad was touched).

## Hygiene
No robots_registry text in the four new modules; no kb_merchants literal in the two new app modules (nor the scripts); no 'partner' constant / merchant_registry import in structured_comparison_service.py; include_in_schema=False on both D16 routes; no QarenBot / NAMED_AGENT text in the new modules; no kb_service token in the two scripts; the kbenrich: namespace exists only in scripts/cron_kb_enrich.py; D17 never writes Redis; no new dependency, host or credential name; the capability header value is never logged.

git status --short (final):
```
M  CLAUDE.md
M  app/api/admin_routes.py
M  app/api/image_routes.py
M  app/api/text_routes.py
M  app/services/kb_ingest.py
A  app/services/kb_operator.py
A  app/services/kb_serve.py
M  app/services/structured_comparison_service.py
A  docs/runbooks/2026-11-kb-operator-ingest.md
A  railway.kbcoverage.json
A  railway.kbenrich.json
A  scripts/cron_kb_coverage.py
A  scripts/cron_kb_enrich.py
A  tests/fixtures/s81_s18_flag_off_golden.json
A  tests/test_s81_d16_operator_ingest.py
A  tests/test_s81_d17_coverage.py
M  tests/test_s81_kb_schema.py
A  tests/test_s81_s18_kb_first_serve.py
A  tests/test_s81_s19_gap_queue.py
```
PR body draft: <scratchpad>/S81-G4_green/PR_BODY.md (HEAD marked NOT COMMITTED).
