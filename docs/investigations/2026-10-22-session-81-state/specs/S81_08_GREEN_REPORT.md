# S81-08 CLIENT-FIRST-OTA - GREEN report (Opus 5.5 GREEN agent, 2026-10-29)

Unit S81-08 CLIENT-FIRST-OTA, client lane, NO runtime flag (merges dark for the client; ships only in the first post-approval OTA after the owner's DATED ledger line of ENABLE_LEGACY_FINGERPRINT_READER=true on web, OWNER_ACTIONS item 32, UB-R4). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s08; branch feature/s81-s08-client-first-ota created from the detached base before the first edit; base e7c81956f11749b1378aa449c4ac616c82bfe6a9 (#376); HEAD 3f990a6908be12312fdc8a440a875ddfa8d0d6b5 (ONE commit through the pre-commit hook, rc=0, never --no-verify; not pushed, not rebased, no PR). Notes folder C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-08_green (notes.md is the running log); byte copies in C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-08_green_before (before_sha.json). This report and PR_BODY.md are written through the shell (python mkreport.py / mkbody.py), as the harness requires.

Inputs read in full: s81-common.txt; PLAN_S81 (standing constraints, VERIFY corrections, client lane, flip order, owner decisions); RULINGS_S81_08 (R-S08-1..R-S08-15, Measurement rulings, Amendments); RULINGS_S81_08B; GATE_S81_08 (GC-1..GC-11); the spec (sha 49c05a18..., equal in the worktree .qa-s80 and the docs copy); the review (db02a714...); the RED report; the nine RED files; DEFECT_LEDGER S81-08 row; OWNER_ACTIONS item 32; the ledger tail (no dated ENABLE_LEGACY_FINGERPRINT_READER=true line yet: the OTA precondition is open).

## 1. First gate (GC-8) at base e7c81956, before any edit

- RED files re-hashed at start: all nine equal the frozen sha256 (bytes>127 = 0, CR = 0 each).
- [jest] tag=s08g-red-base start=1793247144 end=1793247180 rc=1 elapsed=36s -> 54 failed / 33 passed / 87; analyze.py base: bad=0 (every failure an expect assertion, every PIN green).
- [jest] tag=s08g-full-base start=1793247192 end=1793247266 rc=1 elapsed=74s -> 388 suites, 3811 tests: 3727 passed, 58 failed, 13 skipped, 13 todo; the nine RED files are in the run (54 F / 33 P); EXCLUDING s81_08: 3694 passed, 4 failed = nativeBundle.w37 d5 / k2 / k4 / k5. BASE FIGURE 3694 (as expected). 48-suite set 454 / 4; R-S08-11 seven 139 / 0.
- Tools by path: node v24.11.1, jest 29.7.0, tsc 5.9.3, eslint v9.39.4, coreutils timeout 8.32; junction node_modules/@babel/core + .bin/jest present at start and at end; node -e 0 = 1056 ms at start, 1755 ms mid-run.

## 2. Files (base e7c81956 .. HEAD 3f990a69; sha256 of the bytes on disk after the commit)

| path | +/- | sha256 before (byte copy) | sha256 after | blob sha256 |
|---|---|---|---|---|
| CLAUDE.md | +11 / -2 | bcfea87b5e622fd7d172c663ef95da0251b9fa51f5bd06b96b09ef78781b930a | 5fae2d4e46f2dd18b4322691a2a8ae132ec7a666175d31b28a1c59a3541cfe2d | d5f5ec6749412f3bfd7b20f320cf4e40d99b6113e2456ab7c0b432188d20c273 |
| SmartCompareApp/__tests__/deviceFingerprint.test.ts | +19 / -5 | 461daf8882500b7f01dd9607609df59bf715264e96bf96f8d1c91a4dc1468bf2 | b8012a972ebe7dec49ae77c956d35b062362be25841208cf38a4db0daba6c343 | 835e155dc454943ba0ab7007d706e7a1f0abe32f07312e7f4c3d8326bd603c0a |
| SmartCompareApp/__tests__/s81_08/cameraHeaders.s81_08.test.ts | +271 / -0 | new file | ab242206548cd7fad4be9afbb73c2d5c0399a8ce3628512be330e59856662502 | ab242206548cd7fad4be9afbb73c2d5c0399a8ce3628512be330e59856662502 |
| SmartCompareApp/__tests__/s81_08/consentRecord.s81_08.test.ts | +230 / -0 | new file | c8b489fb8decf3ed89dd315ee49e5862b04c73f4f0415c7274d8dee1e1e200c0 | c8b489fb8decf3ed89dd315ee49e5862b04c73f4f0415c7274d8dee1e1e200c0 |
| SmartCompareApp/__tests__/s81_08/deviceId.s81_08.test.ts | +311 / -0 | new file | 66f3ffb5dced2a578729a3e78177dd71ffed5d505bafeff219d52748c3d6718d | 66f3ffb5dced2a578729a3e78177dd71ffed5d505bafeff219d52748c3d6718d |
| SmartCompareApp/__tests__/s81_08/i18nKeys.s81_08.test.ts | +124 / -0 | new file | c57792aa8b27a0cb79aae8f90d11a3889631f75340160e0b0d0d2b4c4734eac3 | c57792aa8b27a0cb79aae8f90d11a3889631f75340160e0b0d0d2b4c4734eac3 |
| SmartCompareApp/__tests__/s81_08/requestHeaders.s81_08.test.ts | +659 / -0 | new file | e76fa815b3654fe2b7dd5c0ec097b444b27f220a332de49257c7a8297889a7cb | e76fa815b3654fe2b7dd5c0ec097b444b27f220a332de49257c7a8297889a7cb |
| SmartCompareApp/__tests__/s81_08/resetRender.s81_08.test.tsx | +435 / -0 | new file | 5ab229eefbddd2bba985150decff4019d9a9b13f2b9ce3c5cec8e0f52daddcbf | 5ab229eefbddd2bba985150decff4019d9a9b13f2b9ce3c5cec8e0f52daddcbf |
| SmartCompareApp/__tests__/s81_08/resetTime.s81_08.test.ts | +108 / -0 | new file | b5527c0503b10ca3ff1b2a98374a333b52ecafc2196c285af5fa33e299fd75c2 | b5527c0503b10ca3ff1b2a98374a333b52ecafc2196c285af5fa33e299fd75c2 |
| SmartCompareApp/__tests__/s81_08/socialLegacy.s81_08.test.ts | +210 / -0 | new file | d44e06de33452d9cecaf1d1f7570fbf6127635cfe50884b8245b5a4a97ca6581 | d44e06de33452d9cecaf1d1f7570fbf6127635cfe50884b8245b5a4a97ca6581 |
| SmartCompareApp/__tests__/s81_08/sseHeaders.s81_08.test.ts | +263 / -0 | new file | f01bd05b9e5792513dc4add42a57e4577de7d74c37ca30b3268266411bd9a0d9 | f01bd05b9e5792513dc4add42a57e4577de7d74c37ca30b3268266411bd9a0d9 |
| SmartCompareApp/__tests__/screens/paywall.noSubscriptionUi.s69.test.ts | +3 / -0 | 69ecca15b432f4b4915f10a239eb169ddb38f61a01ed121c68b28cc97f944818 | a1cb8d345aba673cbc5e05bbb53b7e9f946d956ab8dc9ac89769246fe15a4dcf | f6873911bf76cb6e12867b2129eab337ec34f36d712ddb66d83016feb2807ce1 |
| SmartCompareApp/src/hooks/useComparisonCounter.ts | +24 / -4 | 12cd11f830689800ee85ae6ef851e9c36ebdd23dd311788426d85faf4b16e1ab | 28be1bc5b71cc3c2fc1e4aaca536a10ed1507fa89590038df45a0eceb52d4ff5 | 797ceb4180b02df8fe833c8dccf74682efb11b0991ce21aebfa33ad0ee0e622c |
| SmartCompareApp/src/i18n/ar.json | +3 / -0 | 7aea08684554f15371ebb2d46eccfbfa44c1a83d66b98c1ab60d9567893fcbbe | 96dfc4010c8619b02a2d7a41483fb78a5579fd1c1c6fa9c797e598f675c2bf52 | 96debfdd154354c92c3be5c796e3471d34543d2d2f8d00e12c6d2f024795baf5 |
| SmartCompareApp/src/i18n/en.json | +3 / -0 | 5b42c7a3542659810087a32b38e5534ed58cb2d3cf9124b4f31ce2189528ffb1 | 331e3ab86043b96e77da4e7af1cfd3b72c8e2635d1a99b788e07d2325ce07f23 | b06890bc587802a1560275caac2e9bd387f61dbac60b2b1bd53c0469daa54f7d |
| SmartCompareApp/src/screens/HomeScreen.tsx | +60 / -7 | e5f49be783d9c865dd202aeb682ecf2b75a9fc6737040fcb4f2d71ba9199db55 | 4c906170d479d64818a9e601f8fbe7665f4fbdf9e25d2de257b5463efa0903e9 | 13a8785230c58c1349969c07a0204bf2187965d484d844c71da9133ca9fb3d0a |
| SmartCompareApp/src/screens/PaywallScreen.tsx | +8 / -7 | 85bdfe4a9b58cdf2b3768eb4538fbb438baeda3ddedee0427434284a86024582 | f5a1a977a02fd8d459297967a7fc5f0075f87d3e08c406ca64ed6121d522f48e | aeafec87e79b21fc12264e887853298cb1d468c30ef6796216204ef3ba18e9c1 |
| SmartCompareApp/src/services/aiConsent.ts | +61 / -5 | a7dc249cb1606d271e7cd01e48a272df2b6c7b7bb91cd366b599d8ee8817b5d1 | 35a3534045630425dd93cf0702d466328bd586655b468f35b0170f04966fec70 | f9e05295a853b82acda2d9518f828d330a9f650950975f5ab732365bfb6c282c |
| SmartCompareApp/src/services/api.ts | +54 / -5 | a100d731c8dfff60fb3cf28372e987504922a78829a3c16ba287bed0dba89d3e | 86e20414eeeda2e155b2c0add04f90c41ffb61434092c0be88fec59eb9915cba | d4db724c5b677f86542a83e30bca8eb2818650ee56d02c9065f99775a7fe0990 |
| SmartCompareApp/src/services/authService.ts | +37 / -2 | 252e8dcd64ae4ed09cc928bb2fa287c22488c4da488d8e3df9787cc8762afe44 | e9b7a72159b676161ccdc0d35758ef015402857f0a5a4deae7b4f80b93ca18c1 | db5e3be74e375ca0d052c866b48cf8725d176ffe542ac1fd074729336381bc62 |
| SmartCompareApp/src/services/deviceFingerprint.ts | +171 / -37 | e40a4d590e3cda3b61e9a2ba4c2002e53338ca1853560584a48f435bfb47dc28 | a775580351caa3cffc379d4b033a65b366366632a3cc664ef6c98dc5e6c95c88 | 16b663f98a6bf38a303e882a251d935353338939ae7e5be38f65a55823cb5be9 |
| SmartCompareApp/src/services/requestContext.ts | +192 / -0 | new file | 121634bd9dbb656119d6df89bd7d0a48fec401014999444b38fb3b8ca2edb20b | 121634bd9dbb656119d6df89bd7d0a48fec401014999444b38fb3b8ca2edb20b |
| SmartCompareApp/src/services/sentry.ts | +9 / -1 | 52fc4b371bd76ad12311e5103cce4ba9d884e97ebf70ab872a545b7f96770329 | 9d482698471761c1db82ae8d9084295bd3a596cc94a3c218147d2177982780ed | ed020526ff704d9e99ec652a77b783c2108a385abd8749aeb57fc034aa1c4ef3 |
| SmartCompareApp/src/services/usageService.ts | +20 / -2 | 1e34578285268a9393d600aba2ca44d529390c03ed3ae71f0756f7199c625480 | 7d656bf7621e30b2a6d174b085065948f8306911550ef58d6cf7d0cf3ee27cd6 | bb9fbe9b320c3c0de98468c4b346504806c8564d4cfd281e861b3109d5fd3ba2 |
| SmartCompareApp/src/types/types.ts | +6 / -0 | 8500ccb1ef6a5ae1bb14e77f1d4ceab61a12a03da2eafd02d3a674cb32f89139 | b37759fc43f87302603db0e2d21d924946da62998a32a7a04db9eabecfeeb29f | 596fed47c366f457af504662a6904d170de214f8ea76b09935f25325844d95e9 |
| SmartCompareApp/src/utils/resetTime.ts | +94 / -0 | new file | eb1f94da98d2665b304db91a2a351ef49fda84b8aec4bd618d6344bad9d5f56e | eb1f94da98d2665b304db91a2a351ef49fda84b8aec4bd618d6344bad9d5f56e |

26 files, +3386 / -77. The nine RED files: working copy == blob == the frozen sha256 (re-hashed at start, before the commit and after it). Existing files keep CRLF (crlf == lf counts); the two new source files and the RED files are LF. Added lines are ASCII everywhere except the three AR catalog values; CLAUDE.md lines 171 and 195 carry their pre-existing non-ASCII characters (the appended text is ASCII; bytes>127 3937 -> 3937). The added-line sweep (addcheck.py: @gmail, +973, 8-digit runs, sk- / AKIA / JWT / PEM / credentialed URL) found nothing.

## 3. What the code does (own code; the RED prototype.diff read as a reference only)

- deviceFingerprint.ts: shared in-process nonce memo (one SecureStore read for both hashes; a failure memoises nothing); getDeviceIdentity() -> {hash, source} (only a securestore identity cached; concurrent calls coalesce; a rejection is not replayed); getDeviceFingerprint() = identity.hash (string contract, GC-1); IDFV (iOS) / ANDROID_ID (Android) fallback only when the nonce read or write throws, never cached or persisted, the ORIGINAL error rethrown when none; legacyDeviceFingerprintHash() = the build-3 composition with its own cache; LEGACY_FINGERPRINT_HEADER_UNTIL_MS = Date.UTC(2027, 2, 31, 21, 0, 0); legacyFingerprintHeaderActive(nowMs = Date.now()); _resetCacheForTests() resets all six caches; the stale header comment corrected (A7 finding 12).
- requestContext.ts (NEW): CLIENT_CAPABILITIES = [] (no header while empty); the call-site marker withRequestContext(id?) = {qarenRequestContext: true, headers?: {X-Compare-Request-Id}} (no headers key without an id); isContextRequest; newCompareRequestId() = randomUUID lower-cased when a canonical v4, else null; buildContextHeaders({compareRequestId}) never rejects: the device read raced against a 1,000 ms setTimeout and shape-checked (64 lower-case hex), the consent read = lazy authService.getSavedUser + aiConsent.hasCurrentAiConsentForRequest (falling back to hasCurrentAiConsent ONLY when the memo export is absent, i.e. the jest global mock, and never for a null user), the version shape-checked (1-3 digits); mergeContextHeaders: only-if-absent in any letter case (an empty value counts as absent), works on a plain object and on AxiosHeaders, never throws. No logging.
- aiConsent.ts: parseAiConsentRecord extracted (readAiConsent behaviour identical); hasCurrentAiConsentForRequest = a single-entry per-account memo with a generation counter; recordAiConsent / clearAiConsent drop it in a finally AFTER the storage write (a read racing them is discarded); a null user drops it and reads false; a storage throw reads false and is not memoised. No device id, no device key (R-S08-3).
- api.ts: the request interceptor starts buildContextHeaders() only for a marked config, before awaiting getToken (concurrent), and merges after; an unmarked request takes today's path exactly. identifyFromImages mints one id, builds the context concurrently with getToken, sends {Authorization?, ...ctx} on attempt 1 and {Authorization: new, ...ctx} on the U13c retry (same id), and adds compareRequestId to the resolved result only when an id exists (GC-3; type IdentifyResultWithRequestId). streamComparison mints one id at call time; the SSE headers = {Accept, Authorization?, ...ctx}; the REST compare config spreads withRequestContext(id); returns {subscribe, abort, compareRequestId}. compareTextPair (0 callers) is marked with its own id.
- authService.ts: legacyFingerprintHeader(fingerprint): no value without a resolved X-Device-Fingerprint, every call to a new deviceFingerprint export inside one try (R-S08-9), shape-checked; spread at register and both social sign-ins (read after the native sheet).
- usageService.ts: UsageScope; used.lifetime optional (R-S08-13); resets_at / counted_scope on UsageStatus; resets_at / retry_after_seconds / retry_after / scope on UsageLimitError; getUsageStatus marked.
- sentry.ts: SENSITIVE_HEADERS += x-device-fingerprint, x-device-fingerprint-legacy (R-S08-12).
- resetTime.ts (NEW, pure): resolveResetAt (retry_after_seconds > retry_after > resets_at, GC-2; window now..now+48 h; non-finite now -> null), formatResetClock (rounded to the minute; default offset = the device offset at that minute), isDailyScope, sheetResetClock (daily always; open / unknown only for a daily scope; monthly never; the fetched status first).
- useComparisonCounter.ts: a status without used.lifetime is accepted when it carries both axes (used then keeps the local cache); resetsAt only for counted_scope daily / device_daily (GC-5).
- PaywallScreen.tsx: fetched holds the raw status (state = stateFromStatus(fetched) ?? initial); resetClock from sheetResetClock; the daily / open / default resets lines take paywall.limit.resets_at when set; 250 elements (cap 250): +1 import line, the blank line after onDismiss replaced by the resetClock line.
- HomeScreen.tsx: Link mode mints the id, keeps it in urlCompareRequestIdRef (R-S08-15) and spreads withRequestContext(id); the pill: a11yResets label + a decorative separator (the bonus pattern, a11y-hidden, written as an ASCII escape) + the home-header-counter-resets Text only when resolveResetAt resolves.
- types.ts: the Paywall initialUsage gains resets_at / retry_after_seconds / retry_after / scope (T2-d holds).
- en.json / ar.json: three keys each (1010 -> 1013); AR derived from base catalog words by i18n_add.py (resets_at and resets asserted equal to the spec 2.7 code points).
- Re-pins: E1 + E2 (deviceFingerprint.test.ts, node titles unchanged), E4 (PAYWALL_ALLOW). E3 none (measured). No E6 (the cap holds).
- CLAUDE.md: the unit row after the S81-15 row and before ## Tests (lines 522-529), plus one sentence on the api.ts bullet (line 195) and on the usage_service Device-bound sentence (line 171); CRLF kept.

## 4. Every run (in order)

- [jest] tag=s08g-red-base start=1793247144 end=1793247180 rc=1 elapsed=36s
- [jest] tag=s08g-full-base start=1793247192 end=1793247266 rc=1 elapsed=74s
- [tsc] tag=s08g-7.1-tsc start=1793249856 end=1793249880 rc=0 elapsed=24s errors=0
- [jest] tag=s08g-7.2a-red start=1793249884 end=1793249923 rc=0 elapsed=39s Tests:       87 passed, 87 total
- [jest] tag=s08g-7.2b-4.1 start=1793249938 end=1793249956 rc=0 elapsed=18s Tests:       38 passed, 38 total
- [jest] tag=s08g-7.2c-set55 start=1793249977 end=1793250024 rc=1 elapsed=47s Tests:       4 failed, 593 passed, 597 total
- [jest] tag=s08g-7.2d-inband-A start=1793250064 end=1793250112 rc=0 elapsed=48s Tests:       393 passed, 393 total
- [jest] tag=s08g-7.2d-inband-B start=1793250137 end=1793250173 rc=0 elapsed=36s Tests:       393 passed, 393 total
- [jest] tag=s08g-7.2e-inband-red+4.1 start=1793250191 end=1793250207 rc=0 elapsed=16s Tests:       125 passed, 125 total
- [jest] tag=s08g-7.2f-full-head start=1793250219 end=1793250277 rc=1 elapsed=58s
- [eslint] tag=s08g-eslint-dev1 start=1793249352 end=1793249415 rc=0 elapsed=63s -> 0 errors, 33 warnings over 23 files (12 edited + 2 new + 9 RED)
- [eslint] tag=s08g-eslint-delta start=1793249454 end=1793249661 rc=0 elapsed=207s -> per edited file the base copy (via --stdin) and HEAD have equal problem counts by rule (0 new); new files: requestContext.ts 2 x @typescript-eslint/no-require-imports (the lazy-require idiom of api.ts), resetTime.ts 0; RED resetRender 3 x import/first (GC-7)
- [tsc] tag=s08g-tsc-dev1 rc=0 errors=0; [jest] tag=s08g-red-dev1 rc=0 87 / 87 (development runs on the same bytes)
- axios probe (axios_probe.js; real axios 1.20.0, stub adapter, the GREEN requestContext.ts transpiled): the marker survives mergeConfig on the first pass and on a 401 re-drive; config.headers is AxiosHeaders; device / consent / id reach the adapter on both attempts; an unmarked request carries none.
- Backend (bounded runner, the shared .venv-qaren, one pytest at a time):
  - [pyt] tag=s08g-be-base-01 start=2026-10-29 08:07:28 end=2026-10-29 08:09:41 elapsed=132s bound=1200s status=OK rc=0 (1899 passed, 4 deselected; [hermeticity] sentinel checked 1899 test(s); [netguard] blocked 41 attempt(s) from 31 node(s))
  - [pyt] tag=s08g-be-base-02 start=2026-10-29 08:10:00 end=2026-10-29 08:10:46 elapsed=46s bound=1200s status=OK rc=0 (589 passed; [hermeticity] sentinel checked 589 test(s); [netguard] blocked 24 attempt(s) from 2 node(s))
  - [pyt] tag=s08g-be-head-01 start=2026-10-29 08:11:25 end=2026-10-29 08:15:00 elapsed=215s bound=1200s status=OK rc=0 (1899 passed, 4 deselected; [hermeticity] sentinel checked 1899 test(s); [netguard] blocked 41 attempt(s) from 31 node(s))
  - [pyt] tag=s08g-be-head-02 start=2026-10-29 08:15:09 end=2026-10-29 08:15:30 elapsed=21s bound=1200s status=OK rc=0 (589 passed; [hermeticity] sentinel checked 589 test(s); [netguard] blocked 24 attempt(s) from 2 node(s))
  - [pyt] tag=s08g-ci-order start=2026-10-29 08:15:59 end=2026-10-29 08:19:21 elapsed=202s bound=1200s status=OK rc=0 (2488 passed, 4 deselected; [hermeticity] sentinel checked 2488 test(s); [netguard] blocked 65 attempt(s) from 33 node(s))
- Commit: pre-commit hook rc=0 (138 s; gitleaks / secret shapes / ESLint on the staged client files: 0 errors, 27 warnings); log commit_hook.log.

## 5. Counts

- RED: 87 / 87 at HEAD (the 54 RED rows green, the 33 PINs still green); in-band A / B 393 / 393 each; in-band RED + 4.1 125 / 125.
- FULL suite HEAD: 3781 passed = 3694 + 87; 4 failed = the drift nodes; node-level diff (nodediff.py) base vs HEAD: 0 non-RED nodes moved, appeared or disappeared (3811 nodes both sides, no duplicate titles).
- 48-suite set 454 / 4 (unchanged: the re-pinned nodes keep their ids and pass); R-S08-11 seven 139 / 0; 4.1 suites 38 / 38 (u13c 20 / 20: E3 no move).
- Mutants: NOT re-run by GREEN (GC-9; the adversaries re-run the section-6 table on these bytes).
- Backend comm set: 30 files in 2 chunks; base 2488 / 0, HEAD 2488 / 0; FAILED sets empty both sides; comm -13 branch-only-new EMPTY; CI-order 2488 / 0.

## 6. Comm set derivation (derive_comm.py at HEAD)

No app/, scripts/, migrations/, tests/ or .github/ file changed, so the module-reference grep is empty. Union of: (A) the backend tests that read SmartCompareApp by path: 23 (the 2 test_precommit_hook* files excluded); (B) the CLAUDE.md readers: test_ci_gates (in A), test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_gate_rows, test_s81_s08b_legacy_fingerprint; (C) the header-contract trio test_auth_routes_invite_fingerprint, test_s81_s05_request_context, test_social_login_device_fingerprint. = the RED's 30 files exactly. Eight further backend files mention the header names (test_m13_03_paid_work_gating, test_retro_w2_1, test_s71_u13_compare_auth_required, test_s81_s03_llm_ledger_v2, test_s81_s06_anthropic_router, test_sentry_channels_u8d(_unit), test_w4_13_measurement_truth): server-only pins a client diff cannot move; not added. The source-scanning pins read app/ only (GC-7 / D10). Fresh base record in a detached scratch worktree S81-08_green/base_wt at e7c81956 without a junction (no node_modules); removed with git worktree remove --force (0 entries in git worktree list, gone from disk).

## 7. Deviations (each with its reason)

1. AR home.headerCounter.a11yResets names the subject in its time clause ("and the free comparisons refresh at {{time}}") instead of the spec 2.7 code points ("and they refresh at {{time}}"): the same fix GC-4 made in EN, so the clause cannot read as covering the bonus (R-S08-2); [NATIVE READ]. The other two AR values equal the spec code points (asserted by i18n_add.py).
2. The pill's reset node is preceded by a decorative separator Text (the existing bonus-dot pattern, a11y-hidden) for legibility; the spec named one extra Text: the testID node is the one text-bearing addition.
3. compareTextPair (0 callers) carries withRequestContext + its own id because R-S08-5 lists POST /text/compare; unpinned (GC-7 stated limit).
4. PaywallScreen stays at the 250-element cap without E6: +1 import line, and the blank line after onDismiss became the resetClock line.
5. useComparisonCounter accepts a status without used.lifetime only when it carries both axes; used then reads the local cache; the axes are not decremented between compares in that case (stated limit; the 429 is the backstop).
6. The request-path consent read falls back to hasCurrentAiConsent when the consent module lacks the memo export (reachable only under the jest global mock of __tests__/setup.ts, which the spec forbids editing; resetRender L1 needs it); never for a null or failing user (B15).
7. Header values are shape-checked before sending (device and legacy 64 lower-case hex, consent 1-3 digits), so a malformed value is omitted rather than sent (the S81-05 parser would mark it malformed).
8. getDeviceIdentity returns a copy of the cached identity (callers cannot mutate the cache).
9. The commit trailer reads "Co-Authored-By: Claude Opus 5.5" (this agent's model, per the session attribution rule and the common brief's own-model rule) instead of the task text's "Claude Fable 5.1".
10. PR_BODY.md ends with the mandated attribution line, whose robot emoji is the file's only non-ASCII content.
11. CLAUDE.md lines 171 and 195 were extended in place, so the two modified lines carry their pre-existing non-ASCII characters; the added text is ASCII.
12. The "CI-order set" for this client unit = the 30-file backend set sorted, one runner call (no backend unit file exists).
13. No python file changed: ruff / py_compile not applicable; flag ON / OFF unit runs not applicable (no flag): the base run (54 / 33) is the OFF analogue, the HEAD run (87 / 87) the ON one.

## 8. Questions for the gate / adversaries

1. Owner: the three AR strings ([NATIVE READ]); in particular whether the a11yResets clause excludes the bonus.
2. SF1 / CL3 contract: the Link-mode id lives in a HomeScreen ref with no reader, and a thrown camera error carries no id; should SF1 receive the ids via the Results navigation params (a later unit)?
3. Is the defensive fallback to hasCurrentAiConsent (absent memo export) acceptable, or should the global setup mock gain the memo export in a later unit (setup.ts was out of scope here)?
4. The register / social legacy read is unbounded like the base device read there (a SecureStore hang would delay sign-in as it does at base); bound it like the request path in a later unit?

## 9. NOT MEASURED

- The section-6 mutation table (by design: GC-9 / GC-11, the adversaries).
- Real native modules on a device (expo-secure-store, expo-crypto digest casing, IDFV / ANDROID_ID), the OTA itself, the App Privacy wording, the TestFlight check: owner steps.
- Nothing the task named for GREEN is left unmeasured.

## 10. Stated limits (carried into the PR body)

The consent header is the client's claim; the legacy header lives until 2027-03-31T21:00Z at three sites; a device with intermittent SecureStore failure can present two ids; the reset time is device-local and renders only once S81-09 sends it (the pill count is S81-09's client half); a status without used.lifetime is not decremented between compares; the register / social legacy read is unbounded like the base; the Link-mode id has no reader yet and compareTextPair is unpinned; no on-device E2E in CI; Expo web is not a target.

## 11. State at hand-off

- git status --short of sc-s81-s08: EMPTY (clean vs HEAD 3f990a69); branch feature/s81-s08-client-first-ota; not pushed.
- No .qa-mutation.lock; the junction intact (node_modules/@babel/core/package.json and .bin/jest present); the scratch worktree base_wt removed and verified gone; no orphan pytest started by this agent remains (every runner call returned).
- Production flag state (R-A15): the newest dated ledger line read (2026-10-29 07:29) records no ENABLE_LEGACY_FINGERPRINT_READER=true line, so the OTA precondition (item 32) is open; nothing here changes production (client code reaches phones only by the OTA).
