# INC-C1a SIZE-LABEL: GREEN report (S96, GREEN agent, 2026-11-16 21:18-21:32 AST)

Worktree sc-s96-c1a, branch fix/inc-c1a-size-label at b0ad2603 (HEAD unchanged). Written through the shell.

## VERDICT: BLOCKED at G-3 (no commit made)
A backend fence outside the gate's 18 moved pins fails at the change and passes at base:
- tests/test_s81_12_legal_v3.py::test_p3_i18n_key_sets_equal_and_unchanged (PIN R-S12-8) pins BASE_I18N_KEY_COUNT = 1011 and BASE_I18N_NAMESET_SHA256 = 2d351a2c...f543 (:240-241); the change has 1014 keys, sha cd5995fb...e8e6. Line 239 of that file: "Re-record ONLY with a ruling". The gate rules no backend moved pin, so blocked=true per the task.
- Measured: the 1014-key set minus the three INC-C1a keys hashes to exactly the recorded base sha 2d351a2c... (so the only change is results.price.withSize / perMl / differentSizes).
- Proposed E-row (NOT applied; notes/proposed_E19_legal_v3.diff): :240 `BASE_I18N_KEY_COUNT = 1011` -> `1014`; :241 the sha split in two literals -> "cd5995fb42987f33165330732c5fdf1b1c" "88dfc639676d0742fa431077bfe8e6" (CRLF file). If ruled, the staging list gains tests/test_s81_12_legal_v3.py (a tests/*.py file: the bundle rule's "src plus tests" and the hook behaviour on a .py file are for the orchestrator to confirm).

## G-1 (done)
git apply of red/proto.diff rc=0; `git diff` of the six src files hashes to 42f78d54...2907 = proto.diff's sha256 (byte-identical); CRLF kept (every line CRLF in all six files); stat 6 files +98 -9.

## G-2 (done; uncommitted in the worktree)
18 moved-pin tests, 22 assertion sites + 6 titles that stated the old truth (B1 "nothing else", B7 "== {Authorization}", B9 "ship empty", C5 "{Authorization} only", copy.s11 and arCopy "1,011"). No assertion weakened: every exact object stays an exact toEqual and gains the one key in the file's own case (lower-case in s81_08, 'X-Client-Capabilities' in u13c); B9 now asserts ['price_size'] and toBe('price_size'); the leaf counts rise by exactly 3. Beyond the RED report's line list (same 18 tests, later assertions surfaced once the first was fixed): B14b :542 (second object), C5 :257 (the retry object), T17b :583 and T17a :725 (the no-token first request `{}` -> `{ 'X-Client-Capabilities': 'price_size' }`, CC-5: the camera upload now always carries the header). Full list (base file:line old -> new): notes/pin_edit_list.txt (28 hunks).

## G-3 backend fences (pyt.py, waitfree first)
Set (9 files): the six the gate names + the grep-found readers tests/test_register_benefits_parity_s69.py (I18N en/ar.json), tests/test_events_allowlist_superset.py and tests/test_security_regression.py (rglob over SmartCompareApp/src). test_comparison_id_echo.py names types.ts only in docstrings.
- [pyt] tag=s96c-green-fences start=2026-11-16 21:23:37 end=21:23:52 elapsed=16s bound=600s status=FAIL rc=1: 1 failed, 302 passed; [hermeticity] sentinel checked 303 test(s); [netguard] blocked 12 attempt(s) from 6 node(s) (test_security_regression sentinels). FAILED test_s81_12_legal_v3.py::test_p3_i18n_key_sets_equal_and_unchanged.
- Base re-run in a detached scratch worktree (notes/basewt at b0ad2603, removed with worktree remove --force, absent from worktree list): [pyt] tag=s96c-green-legalbase start=21:24:26 end=21:24:29 elapsed=3s status=OK rc=0, 38 passed; [hermeticity] 38; [netguard] blocked 0. The failure COUNTS.

## G-4 gates (measured; the commit is withheld)
- RED file 9 of 9 (C1-C7, P1, P2): [jest] tag=s96c-green-pins3 start=21:22:30 end=21:22:33 rc=0, 7 suites 129/129 (the RED file + the 6 moved-pin files). Earlier: pins1 21:19:46 rc=1 18 failed (the 18 expected); pins2 21:21:32 rc=1 3 failed (the later assertion sites above).
- FULL jest once (jest 29.7.0): [jest] tag=s96c-green-full start=21:25:48 end=21:26:00 rc=1: 414 suites (410 passed, 1 failed, 3 skipped), 4081 tests: 4051 passed, 4 failed, 13 skipped, 13 todo; snapshots 41/41. The only FAIL suite is config/nativeBundle.w37 (d5, k2, k4, k5) = the 4 accepted nodes.
- tsc 5.9.3 --noEmit: rc=0, 0 lines (21:26:06-21:26:12; run without a waitfree immediately before it, right after the full jest, box was free 21:25:48).
- eslint 9.39.4 "src/**/*.{ts,tsx}" (ci.yml:298): rc=0, 0 errors / 147 warnings (= the RED report's base count). eslint on the 12 diffed files + RED file: 0 errors, 15 warnings; none on an added line (json format checked against the -U0 hunks).
- --runInBand pairs (notes/orderSequencer.js, order from S96C_ORDER, the [seq] line printed): [jest] tag=s96c-green-pair-ab 21:28:14-21:28:16 rc=0 sizeLabel > requestHeaders 31/31; [jest] tag=s96c-green-pair-ba 21:28:16-21:28:18 rc=0 requestHeaders > sizeLabel 31/31.
- Pre-commit hook: NOT RUN (it runs at commit; no commit).

## G-5: NOT DONE (blocked). git status --short: 12 M (6 src + 6 moved-pin test files) + ?? SmartCompareApp/__tests__/c1a/. RED file sha256 7a9f3fff...a05d unchanged.

## Final sha256 (bytes on disk): notes/shas.txt
ResultsContent.tsx 1e603e66... ar.json f122dc8e... en.json d8c8d205... requestContext.ts bd0757b5... types.ts 0970e0a3... formatNumber.ts 9ab5aa22... api.cameraAuthRetry.u13c 01d4f6dc... s11/copy.s11 abeca05d... s11e/arCopy.s11e 3ed9db30... cameraHeaders 3dd69d4e... requestHeaders c20f83fe... sseHeaders 7be5e108...

## Deviations
- D1 the backend moved pin above (unruled) -> blocked, no commit.
- D2 the moved-pin assertion sites exceed the RED report's line list (same 18 tests): B14b :542, C5 :257, T17b :583, T17a :725.
- D3 six test titles edited where the title stated the old truth.
- D4 G-3 set widened by grep with three more readers (all green).
- D5 no --runInBand FULL run (LC-7: the full suite once); tsc ran without its own waitfree call.

## Open questions
- Q1 Rule the E-row for tests/test_s81_12_legal_v3.py:240-241 (1011 -> 1014, sha -> cd5995fb...e8e6) and its staging; then a resumed GREEN re-runs that file, the hook and commits.
