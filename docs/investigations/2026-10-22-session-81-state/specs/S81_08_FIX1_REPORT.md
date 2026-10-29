# S81-08 CLIENT-FIRST-OTA - fix round 1 report (Opus 5.5 fix agent, 2026-10-29)

Unit S81-08 CLIENT-FIRST-OTA, client lane, NO runtime flag (merges now; ships only in the first post-approval OTA after LEGAL-V3 is live and after the dated item-32 line, UB-R4). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s08; branch feature/s81-s08-client-first-ota; base e7c81956; HEAD at start 3f990a6908be12312fdc8a440a875ddfa8d0d6b5 (verified, git status --short EMPTY); HEAD after the ONE fix-round commit bcf75f844d50ad11935a2512f77054d5a36ed4b3 (through the pre-commit hook, never --no-verify; not pushed, not rebased, no PR). Notes folder C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad\S81-08_fix1 (notes.md is the running log). This report and PR_BODY.md are written THROUGH THE SHELL (python mkreport.py / mkbody.py), as the harness requires; pure ASCII except the PR body's mandated attribution emoji.

Inputs read in full: s81-common.txt; RULINGS_FIX1_S81_08 (F1-1..F1-12 + the procedure, read at the start and again before reporting); S81_08_ADV1_correctness.md; S81_08_ADV1_appreview.md; GATE_S81_08 (GC-1..GC-11); RULINGS_S81_08 (R-S08-1..15 + amendments); PLAN_S81 context / standing constraints / client lane / flip order; S81_09_BRIEF (Q8 already carries the F1-8 contract); the GREEN report and PR_BODY.md; the GREEN notes; every source file edited here; the frozen RED harnesses (consentRecord, requestHeaders, resetRender, resetTime, deviceId) for their idioms.

## 1. Start (procedure step 1)

- HEAD 3f990a6908be12312fdc8a440a875ddfa8d0d6b5 on feature/s81-s08-client-first-ota; `git status --short` EMPTY; no .qa-mutation.lock; the junction SmartCompareApp/node_modules -> the clone install present (@babel/core, .bin/jest).
- The nine frozen RED files re-hashed at the start: all equal the frozen sha256 (ab242206..., c8b489fb..., 66f3ffb5..., c57792aa..., e76fa815..., 5ab229ee..., b5527c05..., d44e06de..., f01bd05b...).
- Tools by path: node v24.11.1, jest 29.7.0, tsc 5.9.3, eslint v9.39.4, coreutils timeout 8.32. `node -e 0` = 4.6-5.6 s (slow box; no foreign jest / pytest process was running at any launch).

## 2. RED step (procedure step 2)

New file SmartCompareApp/__tests__/s81_08/gateRows.s81_08.test.ts (13 rows; ASCII, LF; sha256 c306ae0a0a7a6bc76e67fe706d08422cf30c51c4759f696e158f4ed5b9376de8, unchanged after the RED step). Section 1 (the resetRender.s81_08 harness: plain top-level jest.mock, real i18next over the real catalogs): F1-3a, F1-4, F1-9, F1-9b, F1-8a, F1-8b, X6. Section 2 (module worlds: jest.resetModules() then jest.isolateModulesAsync + jest.doMock per row, the requestHeaders idiom; the REAL aiConsent / requestContext / authService over in-memory AsyncStorage and SecureStore): F1-1a, F1-1b, F1-1c, X4, F1-3b, X9.

- [jest] tag=fix1-red-gaterows-head start=1793261685 end=1793261745 rc=1 elapsed=60s -> 6 failed, 7 passed, 13 total at the GREEN HEAD bytes. rows.py red: bad=0.
  - RED (each failed on an expect assertion at 3f990a69): F1-3a (`typeof hasCurrentAiConsentForRequest` "undefined" on the global mock), F1-4 ("...refresh at 13:01." instead of the anchored "13:00."), F1-9 (runs [free, dot, +1, dot, resets] instead of [free, dot, resets, dot, +1]), F1-8a ({free: 3} lifetime math instead of {free: 1} on the device axis), F1-1c (the header "2" after logout: the memo survived), F1-3b (the jest-only fallback sent "2").
  - PIN-type (passed at 3f990a69, proven by the named mutant on those same HEAD bytes, mutate.py tag red_pin, in place, lock held, every restore sha-verified):
    - id | verdict | failing_rows(assertion) | expected | expected_hit | restore | rc | elapsed | wait | other | desc
    - M24 | KILLED | F1-1a F1-1b F1-1c F1-3a F1-3b F1-4 F1-8a F1-9 | F1-1a,F1-1b | F1-1a,F1-1b | restored-sha-OK | rc=1 | 31s | wait=0s |  | consent memo ignores the account (spec M24)
    - X4 | KILLED | F1-1c F1-3a F1-3b F1-4 F1-8a F1-9 X4 | X4 | X4 | restored-sha-OK | rc=1 | 29s | wait=0s |  | consent memo generation guard removed
    - X6 | KILLED | F1-1c F1-3a F1-3b F1-4 F1-8a F1-9 X6 | X6 | X6 | restored-sha-OK | rc=1 | 35s | wait=0s |  | only-if-absent check becomes case-sensitive
    - X9 | KILLED | F1-1c F1-3a F1-3b F1-4 F1-8a F1-9 X9 | X9 | X9 | restored-sha-OK | rc=1 | 23s | wait=0s |  | a failed legacy read is replayed for the process
  - F1-8b and F1-9b are plain PINs of the build-3 shapes (lifetime math; the pill without a reset).
- The nine frozen RED files were not touched (re-hashed again before the commit and after it: equal).

## 3. GREEN step (procedure step 3; smallest hunks)

- F1-1 (MAJ-1 / MAJ-A1): rows F1-1a / F1-1b (PIN-type: spec M24 KILLED on the GREEN bytes and on the final bytes) and F1-1c (RED: the logout drop). CODE: src/services/aiConsent.ts exports `forgetRequestConsent` (doc comment; the module header and the memo comment now read "keyed by the account and dropped by recordAiConsent / clearAiConsent, by a signed-out request and by logout()"); src/services/authService.ts `logout()` finally: right after `await clearSession()` (the saved user is gone), a lazy synchronous `require('./aiConsent')` + a `typeof` guard + the call, inside try/catch (never fails logout; a no-op under the jest global consent mock); an `eslint-disable-next-line @typescript-eslint/no-require-imports` above it (the codebase idiom, rtlBootstrap.ts / pushPrePrompt.ts) keeps the eslint delta at zero.
- F1-2: rows X4 / X6 / X9 (PIN-type, each KILLED by its mutant on both byte sets); X5 / X10 / X11 / X12 / X24 / X30 / X31 are stated limits in the PR body and the CLAUDE.md row; M26 re-run on the final bytes (SURVIVED, the accepted equivalent); M31 not re-run (untouched code, accepted equivalent).
- F1-3: __tests__/setup.ts: the global aiConsent mock gains `hasCurrentAiConsentForRequest` (it calls the mocked `hasCurrentAiConsent` at call time, so a suite overriding that mock moves both; a null user reads false); the factory now builds a typed `mockConsent: Record<string, any>` (the self-reference needs a type; TS7022 otherwise), every other entry unchanged in value (re-indented one level). src/services/requestContext.ts `consentHeaderValue`: the fallback branch is DELETED: one read, `consent.hasCurrentAiConsentForRequest(userId)`; a module without it throws inside the try and omits the header (row F1-3b). Full suite: no node moved (L1 included, 3794 passed).
- F1-4: src/utils/resetTime.ts: `sheetResetClock` resolves the 429 detail (`initial`) at `anchoredNow(initial, nowMs)`, a module-level WeakMap keyed by the detail object that stores the first nowMs it saw; the fetched /usage/status (S81-09's absolute resets_at) is never anchored and still decides first (GC-2, G11 green); the module doc names the anchor as its only state. src/screens/PaywallScreen.tsx untouched (the T2-a2 250-line cap holds). Row F1-4 (RED at 3f990a69: 13:01 instead of 13:00 after the fetch re-render 40 s later; self-checked that the shift crosses a minute).
- F1-5: src/services/sentry.ts header doc comment names x-device-fingerprint and x-device-fingerprint-legacy beside authorization / x-admin-key / cookie.
- F1-6 / F1-7 (docs): CLAUDE.md S81-08 row restated in place (lines 522-529; CRLF kept; the added text ASCII; non-ASCII bytes 3937 -> 3937): the header (the OTA precondition: LEGAL-V3 live, backend deployed AND landing redeployed, and the dated item-32 line; the fix-round rulings named), the device-id bullet (the changed VALUES: register / social X-Device-Fingerprint and the share BODY device_fingerprint_hash carry the new id; invite rows mix the compositions, a revived SAME_DEVICE (S81-08d) must match both; X9), the consent bullet (the key pinned by F1-1a / F1-1b, the logout drop, X4, no jest-only fallback), the reset bullet (F1-4, F1-8, F1-9), the pins bullet (the gate rows, setup.ts), the owner steps ((1) re-verify the App Privacy answers, published 2026-10-11, no change or re-attestation expected, against inventory row 7; (3) LEGAL-V3 live + the dated item-32 line, UB-R4 / 5.1.2(i); (6) OWNER_ACTIONS item 34, F1-11) and the stated limits. docs/privacy-data-inventory.md row 7 (DeviceID) WHERE cell refreshed (CRLF kept; ASCII; the cell's two old arrows replaced by "->", so the file's non-ASCII bytes go 60 -> 54); type / Linked / Tracking / Purposes unchanged; c3 / c5 / u15 / u16 (nativeBundle.w37), privacyManifest.s74 and nativeStrings.b3a green.
- F1-8: src/hooks/useComparisonCounter.ts: when counted_scope is 'daily' / 'device_daily' and remaining[that axis] is a number, the hook returns used = max(0, total - max(0, axisRemaining - sessionConsumed)) and total = limits.daily (FREE_LIMIT when absent), so HomeScreen's unchanged `total - used` renders THAT axis's remaining; otherwise the lifetime math is byte-for-byte today's; the comment no longer claims the case cannot happen. src/services/usageService.ts: `remaining.device_daily?: number` (typed, optional). Rows F1-8a (RED: device axis 1, daily axis 2, minus a local compare) and F1-8b (PIN: no counted_scope, 'monthly', 'lifetime', and a named axis without its remaining keep the lifetime math). The S81-09 brief already carries Q8 (the orchestrator's half).
- F1-9: src/screens/HomeScreen.tsx: the resets block (the decorative a11y-hidden dot + the home-header-counter-resets Text) moved before the bonus block (reorder_pill.py: byte-level, CRLF kept, lines only moved plus one comment line extended; non-ASCII bytes 241 -> 241; the resets dot keeps its ASCII escape, the bonus dot its base bytes); the a11y label is unchanged (GC-4). Rows F1-9 (RED) and F1-9b (PIN: no reset = the build-3 runs). The AR copy is unchanged; the order question joins the [NATIVE READ] list.
- F1-10 / F1-11: nothing in this unit (the orchestrator's S81-12 rebase and OWNER_ACTIONS item 34).
- F1-12: the gates (sections 5-7).

## Deviations (each with its reason)

1. The gate-rows file holds two harnesses and the module-world section starts with jest.resetModules(): jest-runtime's requireMock returns a mock the MAIN registry has cached even inside isolateModules (node_modules/jest-runtime/build/index.js:932-936), and the render harness caches the api / authService / aiConsent / deviceFingerprint mocks at file load. The row order is load-bearing and stated in the file header (F1-3a reads the global setup.ts mock before any world maps the module).
2. F1-1 (b) "B agrees -> the header returns for B and stays absent after a switch back to A only if A's record is gone" is pinned as: A with a record -> present; A's record gone (clearAiConsent(A) before B's request refills the memo) -> absent; the same row covers the reverse direction (a consented A right after a non-consented B), which M24 fails too.
3. F1-1c removes A's record from the in-memory store directly (outside the consent API, so nothing but logout can drop the memo), then logs out and signs A in again with no request in between: the row isolates the logout drop from the account key.
4. The F1-4 anchor lives in resetTime.ts as a WeakMap keyed by the 429 detail object (the ruling allows resetTime; PaywallScreen keeps its 250-line cap and needs no hook). It also anchors the window check of an absolute resets_at carried by the 429 detail itself (none today; S81-09 puts resets_at on /usage/status, which is never anchored).
5. The hook carries the counted axis in its existing {used, total} fields (HomeScreen and every HomeScreen suite mock unchanged) instead of a new field; `used` thus means "used on the counted axis" (the lifetime counter when no daily axis is named).
6. On a daily axis the pill's denominator is limits.daily (FREE_LIMIT when absent): S81-09's contract names remaining.device_daily but no device-axis cap.
7. __tests__/setup.ts: the mock factory became a block with a typed object (the self-reference); the diff re-indents the existing entries by two spaces, values unchanged.
8. The commit trailer names this agent's model (Claude Opus 5.5), per the session attribution rule and the common brief's own-model rule.

## Questions for the gate / the orchestrator

1. F1-8 x S81-09: the compare GATE (canCompare) still reads lifetime-free / daily / monthly. Under ENABLE_DEVICE_DAILY_QUOTA with the monthly and lifetime caps retired, if S81-09's /usage/status stops sending a numeric remaining.monthly, the client gate collapses to `used < 3` with used = used.lifetime (0 or the retired count), so a retired count >= 3 would client-paywall the user. Rule for S81-09: keep remaining.daily AND remaining.monthly numeric (or name a client unit that moves the gate to the counted axis).
2. Should the device-axis denominator come from a server field (e.g. limits.device_daily) once S81-09's device-cap knob can differ from limits.daily?
3. Premium with a counted daily axis renders remaining.daily / limits.daily (e.g. "10/10 free"); today premium shows N/3. Acceptable, or should S81-09 send no counted_scope for premium (Q1 default: premium not device-capped)?

## NOT MEASURED

- Real devices, the OTA itself, the App Privacy page and the TestFlight check (owner steps).
- The spec mutants on code this round did not change (M1-M12, M14-M21, M27-M30b, M31, M32, M36, M38, M40-M45, M48-M53a, X1-X3, X5, X7, X8, X10-X31 except those listed in section 6): the correctness adversary's table on the GREEN bytes stands for them (those files are byte-identical here except the comment-only sentry.ts hunk and the usageService.ts type line).

## 4. Files (base 3f990a69 .. HEAD bcf75f84; sha256 of the bytes on disk after the commit, blob sha256 of the committed object)

| path | +/- | sha256 before (byte copy) | sha256 after (disk) | blob sha256 |
|---|---|---|---|---|
| CLAUDE.md | +7 / -7 | 5fae2d4e46f2dd18b4322691a2a8ae132ec7a666175d31b28a1c59a3541cfe2d | f4c5bd6f77f3c68ca575e8979fa63173ee5fc1489ca4c3448e98006643ccda4b | f7522223e3c0fac2fd9aeaab66297d23bd602b325fdb5e48d1b3111ddcf77f3d |
| SmartCompareApp/__tests__/s81_08/gateRows.s81_08.test.ts | +697 / -0 | new file | c306ae0a0a7a6bc76e67fe706d08422cf30c51c4759f696e158f4ed5b9376de8 | c306ae0a0a7a6bc76e67fe706d08422cf30c51c4759f696e158f4ed5b9376de8 |
| SmartCompareApp/__tests__/setup.ts | +31 / -22 | 9579b4b5d6d8e20418d0678be3c5134dd38b3944a1769979f0ba4845f3d1ef2e | 168befc8ead3b0df6fe88fc38a19f36b2515b6839ebb4196333612229bc1dc8f | 876fcfd7312471b1d5bff6ee1ce9e1699643a2f3840934216ddad96607b313db |
| SmartCompareApp/src/hooks/useComparisonCounter.ts | +21 / -3 | 28be1bc5b71cc3c2fc1e4aaca536a10ed1507fa89590038df45a0eceb52d4ff5 | 8511e43acf642298725c317e73b2d0ea7b47b02e87ecbadfce5a8b730eab51b8 | 9386736be23efec82837a83a7ad12fb0d77504e1f75d392470bd13acf864f6b6 |
| SmartCompareApp/src/screens/HomeScreen.tsx | +11 / -10 | 4c906170d479d64818a9e601f8fbe7665f4fbdf9e25d2de257b5463efa0903e9 | bee8b92730e6d74f1382a8f102fc3d18e2c6f2547ed89da498de039344abde29 | 429dbdc3f5edb87e36e457a8451b8d4ff316252ef5f96bba40d098fee02e082b |
| SmartCompareApp/src/services/aiConsent.ts | +11 / -6 | 35a3534045630425dd93cf0702d466328bd586655b468f35b0170f04966fec70 | 4a26ac8f9d87328433ff39a017e5dd05dbefcc1b92b394154d7a08825ca2862d | 6c281a673aee592fa8342a7831f7691d1cd91ea636e7fca3c0507b8cec7ac799 |
| SmartCompareApp/src/services/authService.ts | +11 / -0 | e9b7a72159b676161ccdc0d35758ef015402857f0a5a4deae7b4f80b93ca18c1 | f3a95d0297f4f6c42c995a649d23c576f1f93ef17f4aee1a2d8c564ebafe84e7 | feb227809a9d9adcd0b56580261db354d66bcdfa98afc8cbb9a8933c98a968ca |
| SmartCompareApp/src/services/requestContext.ts | +4 / -8 | 121634bd9dbb656119d6df89bd7d0a48fec401014999444b38fb3b8ca2edb20b | a6aae37c5d895d7af5b562b24cd09461f6336eb20273348862ea493accf24202 | a6aae37c5d895d7af5b562b24cd09461f6336eb20273348862ea493accf24202 |
| SmartCompareApp/src/services/sentry.ts | +2 / -1 | 9d482698471761c1db82ae8d9084295bd3a596cc94a3c218147d2177982780ed | 6dd60fd6d9606db12264c673c1caee15835d4b27acbfc623c72d508e45ee6848 | 370c687478fe495b62ba922a6cfc8dba7c801551cffe895efe0d3273d690201e |
| SmartCompareApp/src/services/usageService.ts | +3 / -0 | 7d656bf7621e30b2a6d174b085065948f8306911550ef58d6cf7d0cf3ee27cd6 | dace2c371f4ac8def6e9d6fdbf3014383acb36ecf9b31119d93d1b69cb8cb4d4 | 4a28ef613900af9946871b087e025b02eb945bba0df5eb21f591d9ed187abe41 |
| SmartCompareApp/src/utils/resetTime.ts | +18 / -2 | eb1f94da98d2665b304db91a2a351ef49fda84b8aec4bd618d6344bad9d5f56e | 5e6d654b8a8834d0492c042ee883e8a44930b5420fe05d51fc637e2ced1d0c37 | 5e6d654b8a8834d0492c042ee883e8a44930b5420fe05d51fc637e2ced1d0c37 |
| docs/privacy-data-inventory.md | +1 / -1 | 36ad9cacacd013a534a1e92aee7214e034da67ac1ebe963948a2851acc24ee2b | 14adc19e007b330415aa4d4d803e2dca185aa76efb4414b835581ac79e820d27 | edecec6e9cf40f3e1c7ca4b3b691580de9ceecaf95f59c96e3ef428b193ba2b6 |

## 5. Every run (in order; one jest / one pytest at a time)

- [jest] tag=fix1-red-gaterows-head start=1793261685 end=1793261745 rc=1 elapsed=60s | Test Suites: 1 failed, 1 total | Tests: 6 failed, 7 passed, 13 total (RED step at GREEN HEAD 3f990a69; rows.py red: bad=0)
- [tsc] tag=fix1-tsc-dev1 start=1793262274 end=1793262311 rc=0 elapsed=37s errors=0
- [jest] tag=fix1-green-dev1 start=1793262326 end=1793262379 rc=0 elapsed=53s | Test Suites: 10 passed, 10 total | Tests: 100 passed, 100 total
- [jest] tag=fix1-inventory-fences start=1793262521 end=1793262554 rc=1 elapsed=33s | Test Suites: 1 failed, 2 passed, 3 total | Tests: 4 failed, 62 passed, 66 total (the 4 nativeBundle.w37 drift nodes d5/k2/k4/k5 only)
- [eslint] tag=fix1-eslint-delta start=1793262605 end=1793262648 rc=0 elapsed=43s (0 errors; 1 new warning authService no-require-imports 3->4, then fixed by an eslint-disable-next-line)
- [eslint] tag=fix1-eslint-delta2 start=1793262671 end=1793262725 rc=0 elapsed=54s (0 errors; 0 new problems vs the byte copies over the 10 changed client files)
- [jest] tag=fix1-red+gate start=1793262778 end=1793262811 rc=0 elapsed=33s | Test Suites: 10 passed, 10 total | Tests: 100 passed, 100 total
- [jest] tag=fix1-4.1 start=1793262819 end=1793262839 rc=0 elapsed=20s | Test Suites: 3 passed, 3 total | Tests: 38 passed, 38 total
- [jest] tag=fix1-set55 start=1793262849 end=1793262892 rc=1 elapsed=43s | Test Suites: 1 failed, 54 passed, 55 total | Tests: 4 failed, 593 passed, 597 total (the drift nodes only)
- [jest] tag=fix1-inband-A start=1793262928 end=1793262971 rc=0 elapsed=43s | Test Suites: 31 passed, 31 total | Tests: 418 passed, 418 total
- [jest] tag=fix1-inband-B start=1793262981 end=1793263033 rc=0 elapsed=52s | Test Suites: 31 passed, 31 total | Tests: 418 passed, 418 total
- [jest] tag=fix1-inband-red+gate+4.1 start=1793263040 end=1793263066 rc=0 elapsed=26s | Test Suites: 13 passed, 13 total | Tests: 138 passed, 138 total
- [jest] tag=fix1-full-head start=1793263081 end=1793263155 rc=1 elapsed=74s | Test Suites: 1 failed, 3 skipped, 385 passed, 386 of 389 total | Tests: 4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total (Snapshots 42/42; the 4 failures = nativeBundle.w37 d5/k2/k4/k5; node diff vs GREEN: +13 gate rows, 0 gone, 0 moved)
- [jest] tag=fix1-red+gate-committed start=1793265743 end=1793265800 rc=0 elapsed=57s | Test Suites: 10 passed, 10 total | Tests: 100 passed, 100 total (after the commit bcf75f84, on the committed bytes)
- [commit] bcf75f844d50ad11935a2512f77054d5a36ed4b3 through the pre-commit hook: rc=0 elapsed=166s (gitleaks / secret shapes / ESLint on the staged client files: 0 errors, 14 warnings)
- Mutation tables: mutate.py tag red_pin (section 2) and tag final (section 6).
- [pyt] tag=s08f1-be-head-01 start=2026-10-29 12:10:47 end=2026-10-29 12:15:35 elapsed=288s bound=1200s status=OK rc=0 (chunk01, 25 files: 1899 passed, 4 deselected; [hermeticity] sentinel checked 1899 test(s); [netguard] blocked 41 attempt(s) from 31 node(s))
- [pyt] tag=s08f1-be-head-02 start=2026-10-29 12:15:45 end=2026-10-29 12:16:44 elapsed=59s bound=1200s status=OK rc=0 (chunk02, 5 files: 589 passed; [hermeticity] sentinel checked 589 test(s); [netguard] blocked 24 attempt(s) from 2 node(s))
- comm: FAILED node ids HEAD 0, base 0 (GREEN's fresh e7c81956 record, be_base_01 1899 passed / be_base_02 589 passed); branch-only-new EMPTY

## 6. Mutation table on the final bytes (F1-12; mutate.py tag final; in place, .qa-mutation.lock held for the run and removed at its end, a byte copy of every target before its first mutant, the file rewritten from memory and sha-compared after EVERY mutant)

| id | verdict | failing_rows(assertion) | expected | expected_hit | restore | rc | elapsed | wait | other | desc |
|---|---|---|---|---|---|---|---|---|---|---|
| M13 | KILLED | B14b B5 E9 F1-1a F1-1b F1-1c X4 | B5,E9 | B5,E9 | restored-sha-OK | rc=1 | 55s | wait=0s |  | consent header sent without a current record |
| M15b | KILLED | B14b | B14b | B14b | restored-sha-OK | rc=1 | 35s | wait=0s |  | consent builder failure throws through |
| M22 | KILLED | E9 X4 | E9 | E9 | restored-sha-OK | rc=1 | 37s | wait=0s |  | consent memo not invalidated by recordAiConsent |
| M23 | KILLED | E9 | E9 | E9 | restored-sha-OK | rc=1 | 34s | wait=0s |  | consent memo not invalidated by clearAiConsent |
| M24 | KILLED | F1-1a F1-1b | F1-1a,F1-1b | F1-1a,F1-1b | restored-sha-OK | rc=1 | 60s | wait=0s |  | consent memo ignores the account (spec M24) |
| M26 | SURVIVED | - | - | - | restored-sha-OK | rc=0 | 65s | wait=0s |  | signed-out guard dropped (accepted equivalent, F1-2) |
| X4 | KILLED | X4 | X4 | X4 | restored-sha-OK | rc=1 | 57s | wait=0s |  | consent memo generation guard removed |
| X6 | KILLED | X6 | X6 | X6 | restored-sha-OK | rc=1 | 42s | wait=0s |  | only-if-absent check becomes case-sensitive |
| X9 | KILLED | X9 | X9 | X9 | restored-sha-OK | rc=1 | 64s | wait=0s |  | a failed legacy read is replayed for the process |
| MF1 | KILLED | F1-1c | F1-1c | F1-1c | restored-sha-OK | rc=1 | 64s | wait=0s |  | logout() keeps the consent memo (F1-1 drop removed) |
| MF3 | KILLED | F1-3b | F1-3b | F1-3b | restored-sha-OK | rc=1 | 64s | wait=0s |  | the jest-only fallback restored (F1-3) |
| MF3a | KILLED | F1-3a L1 | F1-3a,L1 | F1-3a,L1 | restored-sha-OK | rc=1 | 64s | wait=0s |  | the global consent mock loses hasCurrentAiConsentForRequest (F1-3) |
| MF4 | KILLED | F1-4 | F1-4 | F1-4 | restored-sha-OK | rc=1 | 70s | wait=0s |  | the 429 relative reset re-anchored at every render (F1-4) |
| MF4b | KILLED | F1-4 | F1-4 | F1-4 | restored-sha-OK | rc=1 | 59s | wait=0s |  | the anchor is never stored (F1-4) |
| M37f | KILLED | G11 | G11 | G11 | restored-sha-OK | rc=1 | 63s | wait=0s |  | spec M37 on the final line: the sheet prefers initialUsage over the fetched status |
| M47 | KILLED | G5b G6 | G5b,G6 | G5b,G6 | restored-sha-OK | rc=1 | 60s | wait=0s |  | open / unknown sheet states ignore the scope |
| MF8a | KILLED | F1-8a | F1-8a | F1-8a | restored-sha-OK | rc=1 | 71s | wait=0s |  | the pill ignores the counted axis (lifetime math always, F1-8) |
| MF8b | KILLED | F1-8a F1-8b | F1-8a | F1-8a | restored-sha-OK | rc=1 | 92s | wait=0s |  | the device axis counted from remaining.daily (F1-8) |
| MF8c | KILLED | F1-8a | F1-8a | F1-8a | restored-sha-OK | rc=1 | 73s | wait=0s |  | the axis count ignores local compares (F1-8) |
| MF8d | KILLED | F1-8b | F1-8b | F1-8b | restored-sha-OK | rc=1 | 61s | wait=0s |  | a non-daily counted_scope drives the count (F1-8) |
| MF8e | KILLED | F1-8b | F1-8b | F1-8b | restored-sha-OK | rc=1 | 54s | wait=0s |  | a named axis without its remaining falls back to remaining.daily (F1-8) |
| M46 | KILLED | G7 | G7 | G7 | restored-sha-OK | rc=1 | 47s | wait=0s |  | hook ignores counted_scope for resetsAt |
| MF9 | KILLED | F1-9 | F1-9 | F1-9 | restored-sha-OK | rc=1 | 60s | wait=0s |  | the pill order reverted: the bonus before the resets node (F1-9) |
| M33 | KILLED | F1-9b G9 G9b | G9 | G9 | restored-sha-OK | rc=1 | 53s | wait=0s |  | pill resets node rendered when absent |

Spec section-6 mutants re-run here are the ones on code this round changed (requestContext consent read: M13, M15b, M26; aiConsent memo: M22, M23, M24; resetTime sheetResetClock: M37 on its new line (M37f), M47; the hook: M46; the pill: M33) plus M24 / X4 / X6 / X9 and the new rows' mutants MF1 (logout drop), MF3 / MF3a (F1-3), MF4 / MF4b (F1-4), MF8a-MF8e (F1-8), MF9 (F1-9). M26 is the accepted equivalent (F1-2); M31 (accepted equivalent) is untouched code and was not re-run. The rest of the spec table touches code this round did not change (GREEN bytes, measured by the correctness adversary: 48 / 51 KILLED, the 3 survivors ruled by F1-2).

## 7. Comm set (zero-regression gate) and the backend set

No backend file changed. Re-derived at HEAD: (A) the backend tests that read SmartCompareApp by path: the same 23; (B) the CLAUDE.md readers: the same 5 (test_ci_gates in A); (C) the header-contract trio; (D) readers of docs/privacy-data-inventory.md among the backend tests: none (rg over tests/), so the set is GREEN's 30 files exactly (chunk01 = 25, chunk02 = 5). The backend-scanning CLIENT fences (the fourteen suites joining a repo-root path) and the three client readers of the inventory (nativeBundle.w37 c3 / c5 / u15 / u16, clientTruth/privacyManifest.s74, b3a/nativeStrings.b3a) ran inside the full jest suite: green except the four accepted drift nodes. Base record = GREEN's fresh record at e7c81956 (be_base_01: 1899 passed, 4 deselected, 0 failed; be_base_02: 589 passed, 0 failed); this round's HEAD runs are in section 5; branch-only-new = the sorted FAILED node ids at HEAD minus base.

## 8. State at hand-off

- HEAD bcf75f844d50ad11935a2512f77054d5a36ed4b3 on feature/s81-s08-client-first-ota; parent 3f990a6908be12312fdc8a440a875ddfa8d0d6b5; not pushed, not rebased, no PR.
- git status --short: EMPTY
- .qa-mutation.lock: absent
- junction SmartCompareApp/node_modules: @babel/core present, .bin/jest present (never touched)
- re-hash at hand-off (the nine frozen RED files and the gate-rows file, working copy AND committed blob vs the recorded sha256):
  - cameraHeaders.s81_08.test.ts disk OK blob OK
  - consentRecord.s81_08.test.ts disk OK blob OK
  - deviceId.s81_08.test.ts disk OK blob OK
  - i18nKeys.s81_08.test.ts disk OK blob OK
  - requestHeaders.s81_08.test.ts disk OK blob OK
  - resetRender.s81_08.test.tsx disk OK blob OK
  - resetTime.s81_08.test.ts disk OK blob OK
  - socialLegacy.s81_08.test.ts disk OK blob OK
  - sseHeaders.s81_08.test.ts disk OK blob OK
  - gateRows.s81_08.test.ts disk OK blob OK
- No scratch worktree was created by this agent (the backend set ran in the real worktree on the final bytes, with no mutant applied; the base record is GREEN's fresh e7c81956 record).
- No package manager, no npx, no push, no rebase, no stash, no --no-verify; no .env read; no process of this agent left running.
