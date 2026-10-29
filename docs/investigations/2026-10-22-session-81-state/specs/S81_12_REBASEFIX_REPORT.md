# S81-12 PINFIX_REPORT: the rebase-fix round (RULINGS_REBASE_S81_12 RB12-11..RB12-14; agent Opus 5.5; 2026-10-29 18:39-20:44 AST)

- unit: S81-12 LEGAL-V3; worktree sc-s81-s12; branch feature/s81-legal-v3; nothing pushed, no PR opened; report written through the shell (the harness refuses a subagent Write of a report .md).
- head_before 5ae65723f37bc8089cb88050b9a047871db05a29; base origin/main 6c14ac954f601902d322547de04982033aca5925 (local ref, not re-fetched; merge-base(origin/main, HEAD) = 6c14ac95); head_after e8c8c1dc488a5547a874ccffb7dbd8a96ec7965c (ONE fix commit on 5ae65723; see deviation D1: first committed as 807c2c9c, amended once through the hook).

## E0 (measured at the start, 18:39-18:55)
- git diff --name-only origin/main...5ae65723 sorted = 43 files, identical to the rebase round's footprint_rebased.txt (fp_prev.txt in the notes folder).
- blob sha256 at 5ae65723: tests/test_s81_12_legal_v3.py 1372db2462a6713455f5b4ecb09d989c76278daafcca1ba60b03f3bbacf84f29 (= expected); SmartCompareApp/__tests__/s81_08/requestHeaders.s81_08.test.ts e76fa815b3654fe2b7dd5c0ec097b444b27f220a332de49257c7a8297889a7cb (= main 6c14ac95); SmartCompareApp/__tests__/s81_08/resetRender.s81_08.test.tsx 5ab229eefbddd2bba985150decff4019d9a9b13f2b9ce3c5cec8e0f52daddcbf (= main 6c14ac95).
- P3 recipe re-derived (derive_p3.py, sha256 of '\n'.join(sorted(keys))): HEAD 5ae65723 = 1013 keys, 3d786372b3ca325bc294b675e4e7c0cf3ec39140e4b919860483a3987ee4ab9f, EN == AR; main 6c14ac95 identical; the working copies identical; added vs 98d85433 = home.headerCounter.a11yResets, home.headerCounter.resets, paywall.limit.resets_at; removed none.

## Edits (byte copies in <notes>/bytecopy/ before each write; exact-string, matched once; CRLF working copies kept; pure ASCII, bytes > 127 = 0 after every write)
| file | edit | working copy sha256 before -> after | blob sha256 5ae65723 -> e8c8c1dc |
|---|---|---|---|
| tests/test_s81_12_legal_v3.py (E1 = EK3) | :212 BASE_I18N_KEY_COUNT 1010 -> 1013; :213 BASE_I18N_NAMESET_SHA256 9ff8684f8b72ed2dc7a6d3c7e80c684696bb0d5f4952aed43fabc4a13cb14273 -> 3d786372b3ca325bc294b675e4e7c0cf3ec39140e4b919860483a3987ee4ab9f (kept as two literals, 34 + 30 chars, the file's own split); nothing else | f03454039c9838a896d98fc0be433195912bb7c58c63933ee0282eb67fe7764b -> 0b59fd87fecbc2d1483450691bf5833a57bd06e7427a60c389e72bb7b39c25f8 (73910 B both, 1315 CRLF) | 1372db2462a6713455f5b4ecb09d989c76278daafcca1ba60b03f3bbacf84f29 -> 9163cfcb01e4d15fab1e799743a6998ebf6760982fa846611a81f223dcd3c2a6 |
| SmartCompareApp/__tests__/s81_08/requestHeaders.s81_08.test.ts (E2 = E-S08a) | :338 `plantConsent(2);` -> `plantConsent(Number(/AI_CONSENT_VERSION\s*=\s*([0-9]+)/.exec(require('fs').readFileSync(__dirname + '/../../src/services/aiConsent.ts', 'utf8'))?.[1]));` (the real module's constant, read without loading any module; see D1) | d0c3c7b4ce945406764d85398796cad57728de6010a5a587cfeaa2e095095aef -> 1ebf3618d3be8b0ff4c1e8c090dc4751993a311d719141f333fdee4608c84d6d (28142 -> 28278 B, 659 CRLF) | e76fa815b3654fe2b7dd5c0ec097b444b27f220a332de49257c7a8297889a7cb -> b0e8afa8f2ab169154cdcdb6c08954f32e1f460be87c3a0ac5fdf7672032d135 |
| SmartCompareApp/__tests__/s81_08/resetRender.s81_08.test.tsx (E3 = E-S08b) | :430 `toBe('2')` -> `toBe(String(require('../../src/services/aiConsent').AI_CONSENT_VERSION))` (the module instance the real interceptor reads: the setup.ts mock, 3) | 63a36908e6612954764fdae7b6677b3c029d2f724d3d48f9bd0e30cdf1be2812 -> cdf4acb8ff96c1b255e6abe6ed42a71171f068826116d495ebebf8cd51b76560 (18786 -> 18849 B, 435 CRLF) | 5ab229eefbddd2bba985150decff4019d9a9b13f2b9ce3c5cec8e0f52daddcbf -> e041c0f359faf95bf5f57044365a7299d399c072a952ed7e2547e722e2483fe6 |
- Row ids unchanged; each S81-08 hunk is one line (git diff: 2 +- per file). Commit message: `test(legal): S81-12 rebase fix, EK3 i18n re-record at 6c14ac95 + the S81-08 consent-version E-rows (RULINGS_REBASE_S81_12 RB12-11..12)` + `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; the hook passed both times ('All checks passed!'), never --no-verify.


## VERDICT: READY_FOR_PR (HELD: the orchestrator opens the DRAFT PR titled [HELD for the flip window]).
- Every gate measured on e8c8c1dc: G1 tsc 0 / eslint 0 errors; G2 37 + H1 by design / 22; G3 100 / 100; G4 comm 110 files at 6c14ac95, branch-only-new = H1 only (by design), EMPTY otherwise, base record stored; G5 141 passed; G6 3803 passed + the 4 drift nodes; G7 45 files, diff --check clean, status empty.
- For the orchestrator's review: D1 (the commit was amended once) and D2 (the E-S08a form reads the module constant from source).

## Gates on e8c8c1dc (after the commit; every pytest through pyt.py, ONE at a time; every client tool by path through the sc-s81-s12 junction, ONE jest at a time; node v24.11.1, jest 29.7.0, typescript 5.9.3, eslint 9.39.4, @babel/core 7.29.0)
- G1: [tsc] start=2026-10-29 19:24:58 end=2026-10-29 19:25:19 rc=0 error_lines=0; [eslint] start=2026-10-29 19:25:23 end=2026-10-29 19:25:47 rc=0 lines=9 -> tsc 0 errors; eslint 0 errors on the two edited S81-08 files, 3 warnings (import/first at resetRender.s81_08.test.tsx 177-179: main's untouched lines; this round's hunk is :430).
- G2: [pyt] tag=s12rf-units start=2026-10-29 19:08:46 end=2026-10-29 19:10:09 elapsed=83s bound=600s status=FAIL rc=1  (tests/test_s81_12_legal_v3.py + tests/test_s81_12_gate_rows.py: 1 failed = H1 by design (test_h1_merge_window_recorded) / 59 passed; [hermeticity] sentinel checked 60 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)) -> the RED file 38 = 37 passed + H1 by design (P3 green); gate rows 22 / 22.
- G3:
  [jest] tag=s12rf2-s81_08 start=2026-10-29 19:24:07 end=2026-10-29 19:24:45 rc=0
    Test Suites: 10 passed, 10 total
    Tests: 100 passed, 100 total
    Snapshots: 0 total
  -> 100 / 100: the 8 formerly red nodes (B1, B4, B11, B13, B14a, B14d, B16, L1) green; B5 / B14b green.
- G4 comm set at 6c14ac95 (the rebase's 110-file list, sorted-list sha256 0ea7381449f5f3eb3525491e0111251beea8810931f4aa6c0447dffb08a29fdb; 5 chunks of 22; bound 1200):
  [pyt] tag=s12rf-base-0 start=2026-10-29 19:14:38 end=2026-10-29 19:21:33 elapsed=415s bound=1200s status=FAIL rc=1  (2948 passed, 2 skipped, 4 deselected, 1 xfailed, 27 warnings, 2 errors in 404.08s (0:06:44); [hermeticity] sentinel checked 2951 test(s); [netguard] blocked 14 attempt(s) from 8 node(s))
  [pyt] tag=s12rf-base-1 start=2026-10-29 19:21:37 end=2026-10-29 19:28:07 elapsed=390s bound=1200s status=OK rc=0  (1438 passed, 1 skipped, 262 warnings in 379.80s (0:06:19); [hermeticity] sentinel checked 1439 test(s); [netguard] blocked 6 attempt(s) from 4 node(s))
  [pyt] tag=s12rf-base-2 start=2026-10-29 19:28:13 end=2026-10-29 19:37:45 elapsed=572s bound=1200s status=OK rc=0  (1537 passed, 16 warnings in 550.73s (0:09:10); [hermeticity] sentinel checked 1537 test(s); [netguard] blocked 51 attempt(s) from 32 node(s))
  [pyt] tag=s12rf-base-3 start=2026-10-29 19:37:47 end=2026-10-29 19:37:55 elapsed=9s bound=1200s status=FAIL rc=4  (pytest usage error rc=4: tests/test_s81_12_gate_rows.py does not exist at 6c14ac95 (branch-only); re-run without it as the -fr chunk)
  [pyt] tag=s12rf-base-4 start=2026-10-29 19:37:58 end=2026-10-29 19:38:10 elapsed=12s bound=1200s status=FAIL rc=4  (pytest usage error rc=4: tests/test_s81_12_legal_v3.py does not exist at 6c14ac95 (branch-only); re-run without it as the -fr chunk)
  [pyt] tag=s12rf-base-3f NO-LINE rc=1  (pyt.py exited rc 1 before pytest started: no log; its stdout was not kept, so the cause was not observed; a runner probe at 20:07 ran normally)
  [pyt] tag=s12rf-base-4f NO-LINE rc=1  (pyt.py exited rc 1 before pytest started: no log; its stdout was not kept, so the cause was not observed; a runner probe at 20:07 ran normally)
  [pyt] tag=s12rf-base-3fr start=2026-10-29 20:23:01 end=2026-10-29 20:26:36 elapsed=215s bound=1200s status=OK rc=0  (2243 passed, 2 deselected, 23 warnings in 208.94s (0:03:28); [hermeticity] sentinel checked 2243 test(s); [netguard] blocked 50 attempt(s) from 22 node(s))
  [pyt] tag=s12rf-base-4fr start=2026-10-29 20:32:32 end=2026-10-29 20:36:10 elapsed=218s bound=1200s status=OK rc=0  (1288 passed, 21 skipped, 35 xfailed, 61 warnings in 208.41s (0:03:28); [hermeticity] sentinel checked 1323 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
  [pyt] tag=s12rf-head-0 start=2026-10-29 19:38:15 end=2026-10-29 19:45:33 elapsed=438s bound=1200s status=FAIL rc=1  (2948 passed, 2 skipped, 4 deselected, 1 xfailed, 27 warnings, 2 errors in 432.69s (0:07:12); [hermeticity] sentinel checked 2951 test(s); [netguard] blocked 14 attempt(s) from 8 node(s))
  [pyt] tag=s12rf-head-1 start=2026-10-29 19:45:37 end=2026-10-29 19:51:24 elapsed=347s bound=1200s status=OK rc=0  (1438 passed, 1 skipped, 262 warnings in 334.01s (0:05:34); [hermeticity] sentinel checked 1439 test(s); [netguard] blocked 6 attempt(s) from 4 node(s))
  [pyt] tag=s12rf-head-2 start=2026-10-29 19:51:33 end=2026-10-29 20:04:38 elapsed=786s bound=1200s status=FAIL rc=1  (killed by the per-test 120 s pytest-timeout inside pathlib.read_text -> io.open; no pytest summary: a measurement failure)
  [pyt] tag=s12rf-head-3 NO-LINE rc=1  (pyt.py exited rc 1 before pytest started: no log; its stdout was not kept, so the cause was not observed; a runner probe at 20:07 ran normally)
  [pyt] tag=s12rf-head-4 NO-LINE rc=1  (pyt.py exited rc 1 before pytest started: no log; its stdout was not kept, so the cause was not observed; a runner probe at 20:07 ran normally)
  [pyt] tag=s12rf-head-2r start=2026-10-29 20:10:11 end=2026-10-29 20:22:29 elapsed=738s bound=1200s status=OK rc=0  (1538 passed, 16 warnings in 703.96s (0:11:43); [hermeticity] sentinel checked 1538 test(s); [netguard] blocked 48 attempt(s) from 31 node(s))
  [pyt] tag=s12rf-head-3r start=2026-10-29 20:26:40 end=2026-10-29 20:30:37 elapsed=238s bound=1200s status=OK rc=0  (2265 passed, 2 deselected, 23 warnings in 231.36s (0:03:51); [hermeticity] sentinel checked 2265 test(s); [netguard] blocked 50 attempt(s) from 22 node(s))
  [pyt] tag=s12rf-head-4r start=2026-10-29 20:36:11 end=2026-10-29 20:39:47 elapsed=216s bound=1200s status=FAIL rc=1  (1 failed, 1325 passed, 21 skipped, 35 xfailed, 61 warnings in 209.65s (0:03:29); [hermeticity] sentinel checked 1361 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
  base FAILED/ERROR ids (2): tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence; tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
  head FAILED/ERROR ids (3): tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence; tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable; tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
  comm -13 (branch-only-new): tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded only (H1 by design; the frozen RED file does not exist at base) -> EMPTY otherwise; comm -23 (base-only): EMPTY
  [pyt] tag=s12rf-probe start=2026-10-29 20:07:08 end=2026-10-29 20:07:24 elapsed=15s bound=60s status=OK rc=0  (a runner liveness probe after the rc 1 exits, not a gate: --collect-only -q tests/test_s81_12_gate_rows.py, 22 tests collected)
  cold-tiktoken pair: ERROR at base (chunk 0) and ERROR on HEAD (chunk 0): identical both sides.
  chunk pairs measured on both sides: [0, 1, 2, 3, 4]; NOT MEASURED chunks: none
  base record STORED (LC-6): C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/harness/base_records/6c14ac954f601902d322547de04982033aca5925/0ea7381449f5f3eb3525491e0111251beea8810931f4aa6c0447dffb08a29fdb.txt (sha256 f1d57c9013e972595630157c7d510d92e7261086307fba68f1b8611d31a54f10) + .pyt.log + .files
- G5: [pyt] tag=s12rf-sentry-unit NO-LINE rc=1  (pyt.py exited rc 1 before pytest started: no log; its stdout was not kept, so the cause was not observed; a runner probe at 20:07 ran normally) | [pyt] tag=s12rf-sentry-unitr start=2026-10-29 20:39:51 end=2026-10-29 20:41:29 elapsed=98s bound=600s status=OK rc=0  (141 passed, 1 warning in 84.31s (0:01:24); [hermeticity] sentinel checked 141 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
- G6: 
  [jest] tag=s12rf2-full start=2026-10-29 19:25:56 end=2026-10-29 19:28:30 rc=1
    Test Suites: 1 failed, 3 skipped, 386 passed, 387 of 390 total
    Tests: 4 failed, 13 skipped, 13 todo, 3803 passed, 3833 total
    Snapshots: 42 passed, 42 total
  -> 3803 passed (3795 + the 8 repaired nodes); only the four nativeBundle.w37 drift nodes red (d5, k2, k4, k5); 42 snapshots passed, none written; no -u; no .snap in the diff.
- superseded runs on 807c2c9c (before the amend, kept for the record):
  [jest] tag=s12rf-s81_08 start=2026-10-29 19:09:07 end=2026-10-29 19:11:05 rc=1
    Test Suites: 1 failed, 9 passed, 10 total
    Tests: 2 failed, 98 passed, 100 total
    Snapshots: 0 total
  [jest] tag=s12rf-full start=2026-10-29 19:14:55 end=2026-10-29 19:17:00 rc=1
    Test Suites: 2 failed, 3 skipped, 385 passed, 387 of 390 total
    Tests: 6 failed, 13 skipped, 13 todo, 3801 passed, 3833 total
    Snapshots: 42 passed, 42 total
  -> B5 + B14b red (deviation D1).

- G7 / FOOTPRINT: `git diff --name-only origin/main...HEAD` sorted = 45 files = the 43 of 5ae65723 + SmartCompareApp/__tests__/s81_08/requestHeaders.s81_08.test.ts + SmartCompareApp/__tests__/s81_08/resetRender.s81_08.test.tsx (comm vs the 43: only those two added, none removed):
  CLAUDE.md, SmartCompareApp/__tests__/consent/aiConsentV2.s75.test.ts, SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts, SmartCompareApp/__tests__/consent/aiProcessingConsent.s69.test.tsx, SmartCompareApp/__tests__/landing.brand.s69.test.ts, SmartCompareApp/__tests__/onboarding/step05Trust.s69.test.tsx, SmartCompareApp/__tests__/s81_08/requestHeaders.s81_08.test.ts, SmartCompareApp/__tests__/s81_08/resetRender.s81_08.test.tsx, SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts, SmartCompareApp/__tests__/setup.ts, SmartCompareApp/src/components/AiConsentSheet.tsx, SmartCompareApp/src/i18n/ar.json, SmartCompareApp/src/i18n/en.json, SmartCompareApp/src/screens/onboarding/Step05Trust.tsx, SmartCompareApp/src/services/aiConsent.ts, SmartCompareApp/src/services/consent.ts, app/legal/privacy_policy.md, app/legal/privacy_policy_ar.md, app/legal/processors.json, app/legal/terms_of_service.md, app/legal/terms_of_service_ar.md, app/services/consent_service.py, landing/ar/privacy.html, landing/ar/terms.html, landing/privacy.html, landing/terms.html, scripts/fill_in_legal.py, scripts/legal_variants_u8.json, tests/fixtures/legal_d3c_u8.json, tests/fixtures/legal_disclosure_s77.json, tests/fixtures/legal_fill_in_u8.json, tests/fixtures/legal_prefill_u8/privacy_policy.md, tests/fixtures/legal_prefill_u8/privacy_policy_ar.md, tests/fixtures/legal_prefill_u8/terms_of_service.md, tests/fixtures/legal_prefill_u8/terms_of_service_ar.md, tests/fixtures/legal_s78.json, tests/test_consent_capture_w3_16.py, tests/test_legal_disclosure_s77.py, tests/test_legal_docs_u8.py, tests/test_legal_docs_u8_d3c.py, tests/test_legal_docs_u8_polish.py, tests/test_legal_s78.py, tests/test_s81_12_gate_rows.py, tests/test_s81_12_legal_v3.py, tests/test_s81_s06_anthropic_router.py
  `git diff --check origin/main...HEAD` clean (rc 0); `git diff --stat origin/main...HEAD`: 45 files, 2788 insertions, 378 deletions; the only whole-file entries are files new on the branch (tests/test_s81_12_legal_v3.py 1315, tests/test_s81_12_gate_rows.py 583, SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts 166); the two S81-08 files 2 lines each; no .snap; `git status --short` EMPTY after the commit; the hook files tests/test_precommit_hook*.py NOT run (the unit changes no .githooks file).

## PR body (patched in place through python, exact-string replacements, C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-12_rebase/PR_BODY.md)
- before 25480 B sha256 cfdeee0858a6219a3d055ef41d598025fb63786026016ccfee00b7419413d08e; after 25511 B sha256 4f53587424420ec473b82f23f9dc0c96c2d061010f684d6696db3d777e7459b5; bytes > 127 = 0; <= 25,600.
- replaced: the HEAD sentence (HEAD = e8c8c1dc, previous head 5ae65723 named, base 6c14ac95 kept, footprint 45); the whole 'OPEN before this PR opens' section -> '## Rebase-fix round on HEAD e8c8c1dc' (EK3 with the two constants, 1013 keys, the new frozen-file blob sha; E-S08a / E-S08b with the reason and probe 37 / 37; the counts on e8c8c1dc; the comm figures: 110 files, the base record sha, branch-only-new EMPTY, the sentry unit file's result); and, so the body does not contradict the new HEAD (deviation D3), the two 'PROPOSED ... not applied' E-rows, the 'three sanctioned amendments' sentence, the comm set's NOT MEASURED sentence and the '(rebase) ... NOT MEASURED' stated limit. Every other byte kept; the 'Counts on HEAD 5ae65723' section is left as the record of that head.

## Deviations
- D1 (the one commit): the first E2 form `plantConsent(require('../../src/services/aiConsent').AI_CONSENT_VERSION)` was committed as 807c2c9c (hook passed) and measured red at G3 (98 / 100: B5, B14b): a plain require in that file's beforeEach instantiates the setup.ts mock in jest's MAIN mock registry, and requireMock inside the rows' isolateModules worlds falls back to the main registry, so each world's own aiConsent doMock (requireActual for 'real' worlds) was skipped (consent always yes). Replaced by a source read of the real module's constant (no module loading), pre-checked 100 / 100, and the commit AMENDED once through the hook (git commit --amend -F, never --no-verify) -> e8c8c1dc: still ONE fix commit on 5ae65723 (807c2c9c stays only in the reflog). Not in the NEVER list, but not the literal 'ONE git commit': for the orchestrator's review.
- D2 (the handles): requestHeaders.s81_08 has no consent handle in scope at :338 (only w.consent inside each row's world, built after the beforeEach) and its local mock (mockGlobalConsent, AI_CONSENT_VERSION 2) serves only the 'global' worlds; resetRender.s81_08 has no consent handle at all. E2 reads the real module's constant from src/services/aiConsent.ts (the value the 'real' worlds compare against); E3 requires the module inline at :430 (the instance the real interceptor reads). Both one-line hunks; neither is the literal digit.
- D3 (PR body): beyond the HEAD sentence and the OPEN section, four stale statements were rewritten (listed above) so the body matches e8c8c1dc; the instruction said 'keep every other byte'.
- D4 (budget): the round ran about 2 h 05 min (18:39 -> 20:44) against the 60-minute budget: the box was loaded (node -e 0 = 7.1 s at start; 84 pct CPU with the S81-09 GREEN's comm chunks) and the 22-file comm chunks took 3.5 to 12 min each; head-2 was killed by a per-test 120 s timeout inside io.open and five runs at 20:04-20:05 exited before pytest started; each was re-run once alone and measured.
- D6: at 20:31 I stopped my own driver tree (taskkill /T /F on the PID of comm_driver3.py, matched by its command line; its only pytest child was my base-4fr run in <notes>/b, about 1 min in) to re-plan the remaining runs; base-4fr was re-run from scratch at 20:32 (its partial log deleted first). No other process was touched.
- D7 (order): E4 (the PR body) ran after the gates, because it carries the measured figures (comm, R8 unit file, full jest).
- D5: origin/main was not re-fetched (no write outside the worktree); local origin/main = 6c14ac95 = merge-base, so the three-dot footprint is unaffected by any later main.

## NOT MEASURED
- nothing in G1-G7; the hook files tests/test_precommit_hook*.py were not run by design (the unit changes no .githooks file). The FULL jest suite ran twice (LC-7 says once): the first run (on 807c2c9c, 19:14-19:17) is superseded by D1; the arbiter run is the one on e8c8c1dc.

## Scratch worktree
- detached scratch worktree <notes>/b at 6c14ac95 (git -c core.longpaths=true worktree add --detach, no junction) created at 19:14 and again at 20:22 (driver2 removed it after its two runs failed to spawn); removed with `git worktree remove` (no --force) at 20:06 and 20:41 (rc 0 both); `git worktree list` no longer lists it (count 0) and the directory is gone.

## git status --short (worktree, at the end)
```
(empty)
```
