# S81-08 CLIENT-FIRST-OTA - RED report (Opus 5.5 RED agent, 2026-10-29)

Unit S81-08 CLIENT-FIRST-OTA, client lane, NO runtime flag (merges dark for the client; ships only in the first post-approval OTA after the dated ENABLE_LEGACY_FINGERPRINT_READER flip line). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s08 detached at base 2922972010b350d3afdca9ee7e30bc08624db4bd (git status --short EMPTY at start). Inputs read in full: s81-common.txt, the spec (.qa-s80/S81-08_UNIT_SPEC.md, 792 lines), the review (.qa-s80/S81-08_SPEC_REVIEW.md), RULINGS_S81_08 (R-S08-1..15, Measurement rulings, the Amendment by R-S08B-1 / R-S08B-5), RULINGS_S81_08B, PLAN_S81 sections 0-1 + client lane + flip order, the ledger tail. Notes folder: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-08_red (notes.md is the running log). This report is written through the shell (python), as the harness requires.

## 1. Files written

Only the nine RED files under SmartCompareApp/__tests__/s81_08/ (LF, pure ASCII; AR expectations read from the catalogs at run time; AR fence patterns as code-point escapes). No other file in the worktree was left changed.

| file | sha256 | bytes | bytes>127 | CR |
|---|---|---|---|---|
| __tests__/s81_08/cameraHeaders.s81_08.test.ts | ab242206548cd7fad4be9afbb73c2d5c0399a8ce3628512be330e59856662502 | 11124 | 0 | 0 |
| __tests__/s81_08/consentRecord.s81_08.test.ts | c8b489fb8decf3ed89dd315ee49e5862b04c73f4f0415c7274d8dee1e1e200c0 | 9593 | 0 | 0 |
| __tests__/s81_08/deviceId.s81_08.test.ts | 66f3ffb5dced2a578729a3e78177dd71ffed5d505bafeff219d52748c3d6718d | 12543 | 0 | 0 |
| __tests__/s81_08/i18nKeys.s81_08.test.ts | c57792aa8b27a0cb79aae8f90d11a3889631f75340160e0b0d0d2b4c4734eac3 | 4771 | 0 | 0 |
| __tests__/s81_08/requestHeaders.s81_08.test.ts | e76fa815b3654fe2b7dd5c0ec097b444b27f220a332de49257c7a8297889a7cb | 27483 | 0 | 0 |
| __tests__/s81_08/resetRender.s81_08.test.tsx | 5ab229eefbddd2bba985150decff4019d9a9b13f2b9ce3c5cec8e0f52daddcbf | 18351 | 0 | 0 |
| __tests__/s81_08/resetTime.s81_08.test.ts | b5527c0503b10ca3ff1b2a98374a333b52ecafc2196c285af5fa33e299fd75c2 | 4165 | 0 | 0 |
| __tests__/s81_08/socialLegacy.s81_08.test.ts | d44e06de33452d9cecaf1d1f7570fbf6127635cfe50884b8245b5a4a97ca6581 | 8124 | 0 | 0 |
| __tests__/s81_08/sseHeaders.s81_08.test.ts | f01bd05b9e5792513dc4add42a57e4577de7d74c37ca30b3268266411bd9a0d9 | 10485 | 0 | 0 |

## 2. Row set (spec section 5 as amended) and the base verdict

Final RED: 9 files, 87 rows = 54 RED + 33 PIN (the spec had 65 = 45 + 20; the task text repeated 65). At base: 54 failed, 33 passed; EVERY failure is an assertion (first line `Error: expect(...)`, analyze.py: bad=0); every PIN passes. Per row in Appendix A.

| file | rows | RED | PIN | what changed against the spec table |
|---|---|---|---|---|
| deviceId.s81_08.test.ts | 13 | 11 | 2 | A1-A12 as specified (A8 also pins the ORIGINAL SecureStore error, R-S08-10); A13 NEW: R-S08-7 `{hash, source}` through `getDeviceIdentity()` (sources securestore / idfv / android_id). |
| requestHeaders.s81_08.test.ts | 22 | 15 | 7 | B3 DROPPED (R-S08-1); B1 / B4 / B5 / B11 / B12 restated for R-S08-4 amended (legacy ONLY at register + social) and R-S08-5 (device + consent only on call-site-marked metered requests); B2 = newCompareRequestId lower-cases a v4; B2b NEW (M36: non-v4 -> null, no REST headers key, C13); B8 = register at the cutoff + usage still carries the device id; B13, B14a-d, B16 NEW (R-S08-9); B15 NEW (C7 / R-S08-3); B17 NEW (R-S08B-5 no legacy on share); B18 NEW (R-S08-5 negative: history / feedback / legal / events / refresh get nothing); B19 NEW (R-S08-12 Sentry names). |
| cameraHeaders.s81_08.test.ts | 6 | 4 | 2 | C1 / C2 without the legacy header (amendment); C5 NEW (R-S08-9); C6 NEW (R-S08-15 camera id exposed: accepts a `compareRequestId` field on the resolved result OR an `onCompareRequestId` callback in an optional third argument). |
| sseHeaders.s81_08.test.ts | 6 | 5 | 1 | D1 without the legacy header; D6 NEW (R-S08-9: stream still sent, no REST fallback). |
| consentRecord.s81_08.test.ts | 11 | 1 | 10 | R-S08-3 (NO device mirror): E1 / E2 / E4 / E6 / E8 INVERTED into PINs of today per-account behaviour (they kill a mirror); E3 / E5 / E7 PIN as specified; A9b NEW PIN (no AsyncStorage value carries the device id); E9 RED = the header follows the ACCOUNT record through the memo (none -> version after Agree -> none after clear -> none signed out -> none for another account); E10 NEW PIN (signed-out: asked every time, nothing persisted). |
| resetTime.s81_08.test.ts | 6 | 6 | 0 | F3 pins the R-S08-14 precedence (retry_after_seconds, then retry_after, then resets_at; the spec 2.7 had resets_at first); F5 gains rounding (23:59:55 -> 00:00, 03:05:40 -> 03:06, R-S08-10). |
| resetRender.s81_08.test.tsx | 15 | 9 | 6 | R-S08-2 daily axis: G5 = open (counted_scope device_daily) and unknown (429 scope daily) show the time; G5b NEW PIN (open without a daily axis keeps the base tree); G6 adds unknown + resets_at without scope; G7 pins the axis rule IN THE HOOK (resetsAt only for counted_scope daily / device_daily); G7b NEW (R-S08-13 status without used.lifetime); G9b NEW (M38 past resetsAt); G11 NEW (M37 fetched beats 429); L1 NEW (R-S08-1 / R-S08-5 Link mode: call-site lower-case v4 id, and the REAL interceptor adds device + consent to that config). |
| i18nKeys.s81_08.test.ts | 3 | 2 | 1 | H2 adds the R-S08-2 copy rule: the clause carrying {{time}} never carries {{bonus}}, and the EN time sentence does not start with They / It / These / Both (the spec EN "They refresh at" fails it by design). |
| socialLegacy.s81_08.test.ts | 5 | 1 | 4 | I5 NEW (R-S08-9 partial mock: getDeviceFingerprint only -> both POSTs sent, no legacy header). |

Harness facts the GREEN must know (measured while writing the RED):
- `jest.isolateModules` falls back to the SHARED mock registry for an explicitly mocked module already instantiated there, and a lazy `require()` made by the code at call time (api.ts requires ./authService inside the interceptor) lands in the shared registry when it runs outside the isolate callback. Both produced vacuous / cross-test-leaking rows in the first draft (measured: the second world reused the first world axios instance; I5 ran on the full mock). Fixed: every B row runs inside `jest.isolateModulesAsync`; I5 uses a switchable getter mock (`mockDFMode.partial`). GREEN must not "simplify" these back.
- The rows drive the REAL call sites (getUsageStatus, register, streamComparison REST / SSE, identifyFromImages, createShare, getComparisonHistory, submitFeedback, HomeScreen Link mode) and run the captured config through the REAL registered interceptor, so a header is accepted whether the call site or the interceptor sets it; the metered marker NAME is not pinned (any enumerable config key works; B18 pins the negative).
- The interceptor must handle a PLAIN-object `config.headers` (the rows pass plain objects; axios passes AxiosHeaders, which also supports property assignment).
- Every legacy-dependent row pins `Date.now` pre-cutoff (2026-10-23 12:00Z) and B8 / I4 run AT the cutoff (C5).

## 3. Runs (every jest / tsc / eslint / pyt line)

Tools by path from sc-s81-s08/SmartCompareApp through the junction (node_modules/@babel/core/package.json and node_modules/.bin/jest{,.cmd,.ps1} present at start and at end): node v24.11.1, jest 29.7.0, tsc 5.9.3, eslint v9.39.4, coreutils timeout 8.32. node -e 0 = 1.96 s at start. One jest process at a time (the two in-band runs and the mutation loop ran in the background; nothing else ran meanwhile except eslint).

- BASE FULL jest (the arbiter): `timeout -k 15 1800 node node_modules/jest/bin/jest.js --ci --json --outputFile=full_base.json` -> [jest] tag=s08-red-full-base start=1793240669 end=1793240754 rc=1 elapsed=85s ; Test Suites: 1 failed, 3 skipped, 375 passed, 376 of 379 total ; Tests: 4 failed, 13 skipped, 13 todo, 3694 passed, 3724 total (the 4 nativeBundle.w37 drift nodes).
- BACKEND comm chunk 01 (spec 7.3, 25 files) at pure base: [pyt] tag=s08red-be-base-01 start=2026-10-29 05:31:56 end=2026-10-29 05:33:02 elapsed=67s bound=1200s status=OK rc=0 -> 1899 passed, 4 deselected, 13 warnings ; [netguard] blocked 41 attempt(s) from 31 node(s) ; [hermeticity] sentinel checked 1899 test(s).
- BACKEND comm chunk 02 (5 contract / CLAUDE.md readers) at pure base: [pyt] tag=s08red-be-base-02 start=2026-10-29 05:33:14 end=2026-10-29 05:34:01 elapsed=47s bound=1200s status=OK rc=0 -> 589 passed, 63 warnings ; [netguard] blocked 24 attempt(s) from 2 node(s) ; [hermeticity] sentinel checked 589 test(s).
- RED development runs at base (try1 / try2 / try3.json, 06:00-06:01): try3 = 87 rows, 54 failed (assertion only) / 33 passed; superseded by the final base run below (helpers hardened, B14b extended, imports reordered, two TS fixes).
- PROTOTYPE RED runs: proto1.json 86/87 (I5 vacuous partial mock -> test fixed); proto2.json (after the helper hardening) 87/87 passed, 0 failed.
- PROTOTYPE FULL jest: [jest] tag=s08-red-full-proto start=1793243289 end=1793243328 rc=1 elapsed=39s ; 388 suites (382 passed, 3 failed, 3 skipped) ; Tests: 8 failed, 13 skipped, 13 todo, 3777 passed, 3811 total = the 4 drift nodes + deviceFingerprint.test E1 + E2 + paywall.noSubscriptionUi.s69 T2-c1 + T2-c2 (E4).
- PROTOTYPE in-band order A (RED file before its pair suite; 29 files; --runInBand --testSequencer=argvSequencer.js): [jest] tag=s08-red-inband-proto-A start=1793243409 end=1793243477 rc=1 elapsed=68s ; 393 tests, 389 passed, 4 failed = E1, E2, T2-c1, T2-c2 only.
- PROTOTYPE in-band order B (pair suite before the RED file, extras first, reversed): [jest] tag=s08-red-inband-proto-B start=1793243485 end=1793243527 rc=1 elapsed=42s ; 393 tests, 389 passed, 4 failed = the same four.
- ESLint (first draft): [eslint] tag=s08-red-eslint start=1793243800 end=1793243841 rc=0 elapsed=41s ; 0 errors, 3 import/first warnings (fixed in the final bytes).
- MUTATION loop (mutate.py, one jest --json per mutant over the listed RED files, 8-39 s each, 06:14-06:36): 59 mutants, 59 KILLED (assertion-only), restore sha OK after every run (Appendix B; per-mutant lines in mutate_run.log).
- FINAL RED bytes on the prototype (re-applied by proto.py from the base byte copies, then restored and sha-verified):
  - verify-base OK
  - apply ok
  - verify-proto OK
  - [jest] tag=s08-red-proto-final start=1793245541 end=1793245613 rc=0 elapsed=72s Tests:       87 passed, 87 total
  - restore ok
  - verify-base OK
  - PROTO-DONE
- FINAL gates at base with the final RED bytes (final_gates.sh; RED run, tsc --noEmit, eslint, the in-band order runs):
  - node_modules/.bin/jest
  - node_modules/@babel/core/package.json
  - [jest] tag=s08-red-base-final start=1793245625 end=1793245683 rc=1 elapsed=58s Tests:       54 failed, 33 passed, 87 total
  - [tsc] tag=s08-red-tsc-base start=1793245685 end=1793245714 rc=2 elapsed=29s errors=1 s81_08_errors=1
  - [eslint] tag=s08-red-eslint-final start=1793245720 end=1793245770 rc=0 elapsed=50s ? 3 problems (0 errors, 3 warnings)
  - [jest] tag=s08-red-inband-base-A start=1793245772 end=1793245893 rc=1 elapsed=121s Tests:       54 failed, 339 passed, 393 total
  - [jest] tag=s08-red-inband-base-B start=1793245900 end=1793245988 rc=1 elapsed=88s Tests:       54 failed, 339 passed, 393 total
  - DONE
  - [tsc] tag=s08-red-tsc-base-2 start=1793246033 end=1793246068 rc=0 elapsed=35s errors=0
  - [jest] tag=s08-red-base-final-consentRecord start=1793246072 end=1793246093 rc=1 elapsed=21s Tests:       1 failed, 10 passed, 11 total

## 4. Base record for GREEN

- FULL jest at base (the arbiter, MEASURED): 379 suites (375 passed, 1 failed, 3 skipped), 3724 tests: 3694 passed, 4 failed, 13 skipped, 13 todo; snapshots 42 passed. Failed nodes = exactly the four nativeBundle.w37 drift nodes (d5 gesture-handler, k2, k4, k5). Equals the ledger figure 3,694. full_base.json / full_base.log.
- Spec 1.10 48-suite base set and the R-S08-11 additions, extracted from the FULL runs (the 48-suite list = the spec agent base_set.txt; baseset.py):
  - BASE-FULL spec-1.10 set: suites=48 passed=454 failed=4 missing=[]
  - FAIL __tests__/config/nativeBundle.w37.test.ts :: d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules
  - FAIL __tests__/config/nativeBundle.w37.test.ts :: k2 package-lock.json and node_modules resolve the five packages at or above those patches
  - FAIL __tests__/config/nativeBundle.w37.test.ts :: k4 eslint-config-expo is on the SDK-54 line (~10.0.x) in package.json, the lock and node_modules
  - FAIL __tests__/config/nativeBundle.w37.test.ts :: k5 offline expo-install consistency: every declared package the installed expo bundles satisfies its bundled range, apart from expo.install.exclude
  - BASE-FULL R-S08-11 additions not in the spec set (authService.logoutRefreshFirst.w1-4d.test.ts, authService.logoutRevoke.w1-4.test.ts, rtl/textAlignLogical.contract.test.ts, HomeScreen.bundleE.contract.test.tsx, HomeScreen.bundleE.s3.integration.test.tsx, HomeScreen.bundleE.s3.test.tsx, HomeScreen.currentDesign.contract.test.ts): suites=7 passed=139 failed=0 missing=[]
  - PROTO-FULL spec-1.10 set: suites=48 passed=450 failed=8 missing=[]
  - FAIL __tests__/deviceFingerprint.test.ts :: hashes applicationId|osBuildId|nonce in that order via SHA-256
  - FAIL __tests__/deviceFingerprint.test.ts :: retries after a transient SecureStore failure instead of replaying the rejection
  - FAIL __tests__/screens/paywall.noSubscriptionUi.s69.test.ts :: T2-c1 en.json paywall.* keys are EXACTLY the allowlist
  - FAIL __tests__/screens/paywall.noSubscriptionUi.s69.test.ts :: T2-c2 ar.json paywall.* keys are EXACTLY the allowlist
  - FAIL __tests__/config/nativeBundle.w37.test.ts :: d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules
  - FAIL __tests__/config/nativeBundle.w37.test.ts :: k2 package-lock.json and node_modules resolve the five packages at or above those patches
  - FAIL __tests__/config/nativeBundle.w37.test.ts :: k4 eslint-config-expo is on the SDK-54 line (~10.0.x) in package.json, the lock and node_modules
  - FAIL __tests__/config/nativeBundle.w37.test.ts :: k5 offline expo-install consistency: every declared package the installed expo bundles satisfies its bundled range, apart from expo.install.exclude
  - PROTO-FULL R-S08-11 additions not in the spec set (authService.logoutRefreshFirst.w1-4d.test.ts, authService.logoutRevoke.w1-4.test.ts, rtl/textAlignLogical.contract.test.ts, HomeScreen.bundleE.contract.test.tsx, HomeScreen.bundleE.s3.integration.test.tsx, HomeScreen.bundleE.s3.test.tsx, HomeScreen.currentDesign.contract.test.ts): suites=7 passed=139 failed=0 missing=[]
- Backend client-scanning comm set at pure base (before any new file existed in the worktree): comm/comm_files.txt (30 files) + comm/comm_reasons.tsv; chunk 01 = the spec 7.3 25 files (1899 passed, 4 deselected, 0 failed = the spec record), chunk 02 = 5 contract / CLAUDE.md readers (589 passed, 0 failed). FAILED node set at base: EMPTY.
- Expected at GREEN (from the prototype): FULL jest = base + 87 new rows, the only failures the 4 drift nodes once GREEN re-pins E1 / E2 (deviceFingerprint.test) and E4 (PAYWALL_ALLOW gains paywall.limit.resets_at). Measured on the prototype before those re-pins: 388 suites, 3811 tests, 3777 passed, 8 failed = drift x4 + E1 + E2 + T2-c1 + T2-c2.

## 5. Prototype (IN PLACE in the real worktree, client exception)

Byte copies + sha256 of the 11 edited files and the 2 new-file absences in proto_backup/base_sha.json before the first edit; .qa-mutation.lock created (agent label + time) and deleted after the last restore; the prototype snapshot in proto_snapshot/proto_sha.json; the diff in prototype.diff (reference only for GREEN, never committed). Change list implemented: deviceFingerprint.ts (new id = sha256(lower(trim(nonce))), shared nonce memo, IDFV / ANDROID_ID fallback only on a SecureStore throw, never cached / persisted, original error rethrown, legacy hash byte-identical with its own cache, cutoff constant + predicate, getDeviceIdentity {hash, source}); requestContext.ts NEW (CLIENT_CAPABILITIES [], newCompareRequestId, withRequestContext marker, buildContextHeaders with the 1,000 ms device race and the account-only consent read, contextHeadersFor / mergeContextHeaders only-if-absent, never rejects); aiConsent.ts (hasCurrentAiConsentForRequest memo per account, invalidated by record / clear); api.ts (interceptor Promise.all(getToken, context), camera ctx on both attempts + compareRequestId on the result, streamComparison one id for SSE + REST, exposed); authService.ts (readLegacyFingerprint in its own try, register + both social sign-ins after the native sheet); usageService.ts (marker); sentry.ts (two header names); useComparisonCounter.ts (tolerant of a missing used.lifetime; resetsAt only for a daily counted_scope); PaywallScreen.tsx (+1 line: 250 = the T2-a2 cap, the rule in resetTime.sheetResetTime); HomeScreen.tsx (Link mode id + marker; pill line + a11yResets); resetTime.ts NEW; en.json / ar.json (3 keys each; EN a11yResets "... Free comparisons refresh at {{time}}"; AR from the spec code points, [NATIVE READ]). types.ts and CLAUDE.md were NOT prototyped (no row reads them).

Prototype ON (= the change applied): the 9 RED files 87/87 passed (proto2.json; the final bytes again 87/87 in proto_final.json). Prototype OFF (= base): 54 failed (assertion only) / 33 passed. FULL jest on the prototype: 3777 passed / 8 failed (above). In-band order runs on the prototype, both orders, 29 files: 389 passed / 4 failed = only E1 / E2 / T2-c1 / T2-c2. Spec facts the prototype measured: E3 (u13c) = NO node moves (the root crypto shim gives a non-v4 id and no digest, the authService mock has no getSavedUser); RF1 aiDispatchFence stays green under R-S08-1; RF2 T2-a2 stays green at exactly 250 lines; socialFingerprint.w3-3 and logoutRefreshFirst.w1-4d stay green under the R-S08-9 try rule; the timing suites (settleTerminalLatch.a7, networkMatrix.m18) stay green with the added awaits.

## 6. Mutation table

59 mutants on byte copies of the prototype (one exact-string edit matching once, the listed RED files run with jest --json, the file restored from the prototype snapshot and sha-compared after EVERY run): 59 KILLED (every failing row an assertion), 0 not killed: none. Restore sha OK for every mutant (Appendix B). Spec mutants M22-M26 (device mirror) do not exist under R-S08-3; they are replaced by the consent-memo / no-mirror mutants M22-M26b; M11 (path list) is dropped with B3 (R-S08-1); M35 (social legacy after the cutoff) is the same site as M14 in this prototype (one shared helper for register and social) and is killed by I4 / B8; M39-M53 cover the rows the rulings added.

The 59-mutant loop ran on the RED bytes of 06:14 (before the final type-only / harness-shape edits: `: any` annotations on the recorder objects, the HomeScreen props spread, typed console spies, the component mock factories written inline, a String(v) in A9b; no assertion changed). The final bytes were re-proven: 87/87 on the re-applied prototype (proto_final.json), 54 RED / 33 PIN at base (base_final.json, consentRecord re-run alone after the String(v) edit), and a confirmation sample of mutants re-run on the final bytes (mut/mutation_confirm_final_bytes.tsv):
  - M16 headers logged via console.log: KILLED by [B10] (restored-sha-OK)
  - M18 camera retry sends Authorization only (base line): KILLED by [C2] (restored-sha-OK)
  - M21 returned compareRequestId differs from the sent id: KILLED by [D3 D4] (restored-sha-OK)
  - M24 consent memo ignores the account (one memo for every user): KILLED by [E9] (restored-sha-OK)
  - M26 consent header for a signed-out device (null user asked): KILLED by [B15] (restored-sha-OK)
  - M33 pill resets node rendered when absent: KILLED by [G9 G9b] (restored-sha-OK)
  - M50 Link mode request not on the metered allowlist: KILLED by [L1] (restored-sha-OK)
  - M53g legacy header not sent on the Google sign-in: KILLED by [I1] (restored-sha-OK)

## 7. Deviations from the spec (rulings applied) and items for the gate

- D1 Row count 87 (54 RED / 33 PIN), not 65: the rulings add B2b, B13, B14a-d, B15-B19, C5, C6, D6, A9b, A13, E10, G5b, G7b, G9b, G11, L1, I5 and drop B3; R-S08-3 inverts the E family into PINs.
- D2 R-S08-7 says `getDeviceFingerprint` returns `{hash, source}`; taken literally it breaks the string contract that R-S08-9 B13 / I5, the w3-3 register pin (`toEqual({ headers: { X-Device-Fingerprint: FP } })`) and the unchanged share body rely on. The RED keeps `getDeviceFingerprint(): Promise<string>` and pins the source on a NEW export `getDeviceIdentity()` (A13, the review C6 name). GATE: confirm the name.
- D3 R-S08-14 precedence pinned literally (retry_after_seconds, then retry_after, then resets_at), reversing spec 2.7 (resets_at first). Relative values are clock-skew free, which supports the ruling reading. GATE: confirm the direction (F3 / M29 flip together).
- D4 R-S08-2 placement: the axis rule for the pill lives in the HOOK (`resetsAt` non-null only for counted_scope daily / device_daily, G7) so HomeScreen renders whatever resolves (G8 / G9 / G9b with the hook mocked); the sheet reads `counted_scope` from the fetched status and `scope` from the 429 initialUsage (G5 / G5b / G6).
- D5 B8 restated: "register at the cutoff sends no legacy and reads none; usage still carries the device id" (RED); the spec B8 was a usage-only cutoff row, meaningless once legacy never rides usage.
- D6 C6 accepts either exposure form for the camera id (a `compareRequestId` result field, as prototyped, or an `onCompareRequestId` callback in an optional third argument). A result field collides with u13c T1 `toEqual(OK_DATA)` only when an id exists; in that suite the root crypto shim yields no v4 id, so no collision was measured.
- D7 L1 reaches the REAL interceptor through `axios.interceptors.request.handlers` (axios internals) inside the HomeScreen harness; an axios upgrade that renames `handlers` would break L1 (not a product defect).
- D8 The Link-mode id exposure through a HomeScreen ref (R-S08-15) has no row (an internal ref); compareTextPair (0 callers) is neither marked nor pinned.
- D9 R-S08-12 adds src/services/sentry.ts to the change list (B19); spec 3 says "No other file".
- D10 The comm set is the spec 7.3 25 files + 5 contract / CLAUDE.md readers; the common-brief named source-scanning pins (test_model_config*, test_prompt_fence, ...) are not added: they read app/ only and the unit changes no app/ file (the spec 7.3 reason).
- D11 Copy: the spec EN a11yResets "They refresh at {{time}}" fails H2 by design (R-S08-2); the prototype used "Free comparisons refresh at {{time}}". The AR a11yResets (spec code points) passes the structural check (its time clause has no {{bonus}}) but its verb "wa-tatajaddad" may still read as covering the bonus: [NATIVE READ] for the owner.
- D12 ESLint on the RED files: 0 errors, 3 import/first warnings in resetRender (the screen imports sit AFTER the mocks on purpose: the mock factories return module-scope recorders, and moving the imports to the top was measured to hit the TDZ (ReferenceError at load); the HomeScreen.rateLimitedSeconds.w314 harness has the same shape). tsc: the first final gate found 11 TS7022 / TS7024 / TS18046 errors (self-referencing recorder objects, an excess `route` prop); fixed with `: any` annotations and a props spread, then re-gated.

Open questions for the gate: (1) D2 accessor name; (2) D3 precedence; (3) D6 exposure form; (4) D11 AR wording; (5) whether the hook (D4) or HomeScreen owns the axis rule; (6) whether CLAUDE.md section 8 text must also drop the device-mirror sentence (R-S08-3 superseded spec 8 item (2)).

## 8. Restore check and state at hand-off

- git status --short: ?? SmartCompareApp/__tests__/s81_08/
- git diff --stat: EMPTY
- git rev-parse HEAD: 2922972010b350d3afdca9ee7e30bc08624db4bd
- the 11 prototype-edited files sha256 == their base byte copies and the 2 new files absent: OK
- .qa-mutation.lock present: False
- junction: node_modules/@babel/core/package.json True, node_modules/.bin/jest True
- RED files in the worktree vs the staged copies: cameraHeaders.s81_08.test.ts=same, consentRecord.s81_08.test.ts=same, deviceId.s81_08.test.ts=same, i18nKeys.s81_08.test.ts=same, requestHeaders.s81_08.test.ts=same, resetRender.s81_08.test.tsx=same, resetTime.s81_08.test.ts=same, socialLegacy.s81_08.test.ts=same, sseHeaders.s81_08.test.ts=same
- No scratch worktree was created (client exception: prototype + mutants in place on sha-verified byte copies); no git write command was run; nothing committed or pushed.
- no worktree was added or removed by this agent (git worktree list read only; the real worktree sc-s81-s08 is listed at 2922972010b3 detached)

NOT MEASURED: nothing the task named; the FULL jest suite at base was measured (85 s). Not done: GREEN work (types.ts, CLAUDE.md, the 4.1 re-pins), no commit, no push.


## Appendix A. Per-row outcome at base (final RED bytes, base_final.json)

| file | row | at base | first failure line |
|---|---|---|---|
| cameraHeaders.s81_08.test.ts | C1 RED | failed | Error: expect(received).toMatch(expected) |
| cameraHeaders.s81_08.test.ts | C2 RED | failed | Error: expect(received).toMatch(expected) |
| cameraHeaders.s81_08.test.ts | C3 RED | failed | Error: expect(received).toMatch(expected) |
| cameraHeaders.s81_08.test.ts | C4 PIN | passed |  |
| cameraHeaders.s81_08.test.ts | C5 PIN | passed |  |
| cameraHeaders.s81_08.test.ts | C6 RED | failed | Error: expect(received).toMatch(expected) |
| sseHeaders.s81_08.test.ts | D1 RED | failed | Error: expect(received).toMatch(expected) |
| sseHeaders.s81_08.test.ts | D2 RED | failed | Error: expect(received).toMatch(expected) |
| sseHeaders.s81_08.test.ts | D3 RED | failed | Error: expect(received).toMatch(expected) |
| sseHeaders.s81_08.test.ts | D4 RED | failed | Error: expect(received).toMatch(expected) |
| sseHeaders.s81_08.test.ts | D5 RED | failed | Error: expect(received).toMatch(expected) |
| sseHeaders.s81_08.test.ts | D6 PIN | passed |  |
| i18nKeys.s81_08.test.ts | H1 RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| i18nKeys.s81_08.test.ts | H2 RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| i18nKeys.s81_08.test.ts | H3 PIN | passed |  |
| socialLegacy.s81_08.test.ts | I1 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| socialLegacy.s81_08.test.ts | I2 PIN | passed |  |
| socialLegacy.s81_08.test.ts | I3 PIN | passed |  |
| socialLegacy.s81_08.test.ts | I4 PIN | passed |  |
| socialLegacy.s81_08.test.ts | I5 PIN | passed |  |
| resetTime.s81_08.test.ts | F1 RED | failed | Error: expect(received).not.toBeNull() |
| resetTime.s81_08.test.ts | F2 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| resetTime.s81_08.test.ts | F3 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| resetTime.s81_08.test.ts | F4 RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| resetTime.s81_08.test.ts | F5 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| resetTime.s81_08.test.ts | F6 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| consentRecord.s81_08.test.ts | E1 PIN | passed |  |
| consentRecord.s81_08.test.ts | E2 PIN | passed |  |
| consentRecord.s81_08.test.ts | E3 PIN | passed |  |
| consentRecord.s81_08.test.ts | E4 PIN | passed |  |
| consentRecord.s81_08.test.ts | E5 PIN | passed |  |
| consentRecord.s81_08.test.ts | E6 PIN | passed |  |
| consentRecord.s81_08.test.ts | E7 PIN | passed |  |
| consentRecord.s81_08.test.ts | E8 PIN | passed |  |
| consentRecord.s81_08.test.ts | A9b PIN | passed |  |
| consentRecord.s81_08.test.ts | E9 RED | failed | Error: expect(received).not.toBeNull() |
| consentRecord.s81_08.test.ts | E10 PIN | passed |  |
| deviceId.s81_08.test.ts | A1 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| deviceId.s81_08.test.ts | A2 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| deviceId.s81_08.test.ts | A3 RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| deviceId.s81_08.test.ts | A4 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| deviceId.s81_08.test.ts | A5 PIN | passed |  |
| deviceId.s81_08.test.ts | A6 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| deviceId.s81_08.test.ts | A7 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| deviceId.s81_08.test.ts | A8 RED | failed | Error: expect(jest.fn()).toHaveBeenCalledTimes(expected) |
| deviceId.s81_08.test.ts | A9 PIN | passed |  |
| deviceId.s81_08.test.ts | A10 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| deviceId.s81_08.test.ts | A11 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| deviceId.s81_08.test.ts | A12 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| deviceId.s81_08.test.ts | A13 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| requestHeaders.s81_08.test.ts | B1 RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| requestHeaders.s81_08.test.ts | B2 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| requestHeaders.s81_08.test.ts | B2b RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| requestHeaders.s81_08.test.ts | B4 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| requestHeaders.s81_08.test.ts | B5 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| requestHeaders.s81_08.test.ts | B6 PIN | passed |  |
| requestHeaders.s81_08.test.ts | B7 PIN | passed |  |
| requestHeaders.s81_08.test.ts | B8 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| requestHeaders.s81_08.test.ts | B9 RED | failed | Error: expect(received).not.toBeNull() |
| requestHeaders.s81_08.test.ts | B10 PIN | passed |  |
| requestHeaders.s81_08.test.ts | B11 RED | failed | Error: expect(received).toMatch(expected) |
| requestHeaders.s81_08.test.ts | B12 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| requestHeaders.s81_08.test.ts | B13 RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| requestHeaders.s81_08.test.ts | B14a RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| requestHeaders.s81_08.test.ts | B14b RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| requestHeaders.s81_08.test.ts | B14c PIN | passed |  |
| requestHeaders.s81_08.test.ts | B14d RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| requestHeaders.s81_08.test.ts | B15 PIN | passed |  |
| requestHeaders.s81_08.test.ts | B16 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| requestHeaders.s81_08.test.ts | B17 PIN | passed |  |
| requestHeaders.s81_08.test.ts | B18 PIN | passed |  |
| requestHeaders.s81_08.test.ts | B19 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| resetRender.s81_08.test.tsx | G1 RED | failed | Error: expect(received).toBeDefined() |
| resetRender.s81_08.test.tsx | G2 PIN | passed |  |
| resetRender.s81_08.test.tsx | G3 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| resetRender.s81_08.test.tsx | G4 PIN | passed |  |
| resetRender.s81_08.test.tsx | G5 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| resetRender.s81_08.test.tsx | G5b PIN | passed |  |
| resetRender.s81_08.test.tsx | G6 PIN | passed |  |
| resetRender.s81_08.test.tsx | G10 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| resetRender.s81_08.test.tsx | G11 RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| resetRender.s81_08.test.tsx | G7 RED | failed | Error: expect(received).toEqual(expected) // deep equality |
| resetRender.s81_08.test.tsx | G7b RED | failed | Error: expect(received).toBe(expected) // Object.is equality |
| resetRender.s81_08.test.tsx | G8 RED | failed | Error: expect(received).toBeDefined() |
| resetRender.s81_08.test.tsx | G9 PIN | passed |  |
| resetRender.s81_08.test.tsx | G9b PIN | passed |  |
| resetRender.s81_08.test.tsx | L1 RED | failed | Error: expect(received).toMatch(expected) |

## Appendix B. Mutation table (raw, mut/mutation_table.tsv)

| id | mutant | file | verdict | failing rows | expected killers (spec / this RED) | restore |
|---|---|---|---|---|---|---|
| M1 | getDeviceFingerprint returns the legacy composition | src/services/deviceFingerprint.ts | KILLED | A2 A3 A6 A7 A8 A10 | A2 A3 | restored-sha-OK |
| M2 | the new raw string includes Device.osBuildId | src/services/deviceFingerprint.ts | KILLED | A2 A3 A6 A13 | A3 | restored-sha-OK |
| M3 | drop .toLowerCase() on the stable id | src/services/deviceFingerprint.ts | KILLED | A2 A6 A13 | A2 | restored-sha-OK |
| M4 | legacy composition lower-cases the nonce | src/services/deviceFingerprint.ts | KILLED | A4 | A4 | restored-sha-OK |
| M5 | fallback value stored in the cache | src/services/deviceFingerprint.ts | KILLED | A6 | A6 | restored-sha-OK |
| M6 | fallback persisted with AsyncStorage.setItem | src/services/deviceFingerprint.ts | KILLED | A6 | A6 | restored-sha-OK |
| M7 | Android branch calls IDFV | src/services/deviceFingerprint.ts | KILLED | A7 A13 | A7 | restored-sha-OK |
| M8 | separate SecureStore read per hash (memo removed) | src/services/deviceFingerprint.ts | KILLED | A10 | A10 | restored-sha-OK |
| M9 | cutoff comparison inverted | src/services/deviceFingerprint.ts | KILLED | A12 B11 | A12 B11 | restored-sha-OK |
| M9b | no fallback: rejects with a new error instead of the original | src/services/deviceFingerprint.ts | KILLED | A8 | A8 | restored-sha-OK |
| M9c | getDeviceIdentity reports the wrong source on the fallback | src/services/deviceFingerprint.ts | KILLED | A13 | A13 | restored-sha-OK |
| M10 | interceptor overwrites an explicit header | src/services/requestContext.ts | KILLED | B4 | B4 | restored-sha-OK |
| M12 | compare id not lower-cased | src/services/requestContext.ts | KILLED | B2 B11 | B2 | restored-sha-OK |
| M13 | consent header sent without a current record | src/services/requestContext.ts | KILLED | E9 B5 B14b | B5 E9 | restored-sha-OK |
| M14 | legacy window check removed (register + social helper) | src/services/authService.ts | KILLED | I4 B8 | B8 I4 | restored-sha-OK |
| M15a | device builder try removed (throws through) | src/services/requestContext.ts | KILLED | B14a | B14a | restored-sha-OK |
| M15b | consent builder try removed (throws through) | src/services/requestContext.ts | KILLED | B14b | B14b | restored-sha-OK |
| M15c | legacy builder try removed (throws through) | src/services/authService.ts | KILLED | I3 I5 B13 B14c | B14c I3 | restored-sha-OK |
| M15d | compare-id builder try removed (throws through) | src/services/requestContext.ts | KILLED | C5 D6 B14d | B14d C5 D6 | restored-sha-OK |
| M16 | headers logged via console.log | src/services/requestContext.ts | KILLED | B10 | B10 | restored-sha-OK |
| M17 | capabilities header sent while empty | src/services/requestContext.ts | KILLED | B1 B7 B9 B13 B14a B14b B14d | B9 | restored-sha-OK |
| M18 | camera retry sends Authorization only (base line) | src/services/api.ts | KILLED | C2 | C2 | restored-sha-OK |
| M19 | camera retry mints a new id | src/services/api.ts | KILLED | C2 C5 | C2 | restored-sha-OK |
| M20 | REST compare (SSE fallback) mints a new id | src/services/api.ts | KILLED | D2 D4 | D2 D4 | restored-sha-OK |
| M21 | returned compareRequestId differs from the sent id | src/services/api.ts | KILLED | D3 D4 | D3 D4 | restored-sha-OK |
| M22 | consent memo not invalidated by recordAiConsent | src/services/aiConsent.ts | KILLED | E9 | E9 | restored-sha-OK |
| M23 | consent memo not invalidated by clearAiConsent | src/services/aiConsent.ts | KILLED | E9 | E9 | restored-sha-OK |
| M24 | consent memo ignores the account (one memo for every user) | src/services/aiConsent.ts | KILLED | E9 | E9 | restored-sha-OK |
| M25 | a device-level mirror satisfies consent | src/services/aiConsent.ts | KILLED | E4 | E4 | restored-sha-OK |
| M26 | consent header for a signed-out device (null user asked) | src/services/requestContext.ts | KILLED | B15 | B15 | restored-sha-OK |
| M26b | Agree also writes a device-level copy | src/services/aiConsent.ts | KILLED | E1 | E1 | restored-sha-OK |
| M27 | resolveResetAt accepts past times | src/utils/resetTime.ts | KILLED | F4 | F4 | restored-sha-OK |
| M28 | 48 h bound removed | src/utils/resetTime.ts | KILLED | F4 | F4 | restored-sha-OK |
| M29 | precedence swapped (resets_at before the retry fields) | src/utils/resetTime.ts | KILLED | F3 | F3 | restored-sha-OK |
| M30 | 12-hour clock / no zero pad | src/utils/resetTime.ts | KILLED | F2 F5 F6 | F5 | restored-sha-OK |
| M30b | truncation instead of rounding | src/utils/resetTime.ts | KILLED | F5 | F5 | restored-sha-OK |
| M31 | monthly state renders the daily time | src/utils/resetTime.ts | KILLED | G4 | G4 | restored-sha-OK |
| M32 | the resets line always uses the resets_at copy | src/screens/PaywallScreen.tsx | KILLED | G2 G4 G5b G6 | G2 | restored-sha-OK |
| M33 | pill resets node rendered when absent | src/screens/HomeScreen.tsx | KILLED | G9 G9b | G9 | restored-sha-OK |
| M34 | social legacy read before the native sheet | src/services/authService.ts | KILLED | I2 | I2 | restored-sha-OK |
| M36 | v4 check removed in newCompareRequestId | src/services/requestContext.ts | KILLED | B2b | B2b | restored-sha-OK |
| M37 | the sheet prefers initialUsage over the fetched status | src/utils/resetTime.ts | KILLED | G11 | G11 | restored-sha-OK |
| M38 | pill renders the raw resetsAt without resolveResetAt | src/screens/HomeScreen.tsx | KILLED | G9b | G9b | restored-sha-OK |
| M39 | a NEW deviceFingerprint export called outside its try (R-S08-9) | src/services/authService.ts | KILLED | I5 B13 | I5 B13 | restored-sha-OK |
| M40 | device-id read not bounded at 1,000 ms | src/services/requestContext.ts | KILLED | B16 | B16 | restored-sha-OK |
| M41 | context headers on every request (marker ignored) | src/services/requestContext.ts | KILLED | B12 B18 | B18 | restored-sha-OK |
| M42 | legacy header on metered requests | src/services/requestContext.ts | KILLED | B1 B8 B13 B14a B14b B14d | B1 | restored-sha-OK |
| M43 | legacy header on the share call | src/services/requestContext.ts | KILLED | B17 | B17 | restored-sha-OK |
| M44 | Sentry header names not added | src/services/sentry.ts | KILLED | B19 | B19 | restored-sha-OK |
| M45 | hook drops a status without used.lifetime | src/hooks/useComparisonCounter.ts | KILLED | G7b | G7b | restored-sha-OK |
| M46 | hook ignores counted_scope | src/hooks/useComparisonCounter.ts | KILLED | G7 | G7 | restored-sha-OK |
| M47 | open / unknown sheet states ignore the scope | src/utils/resetTime.ts | KILLED | G5b G6 | G5b G6 | restored-sha-OK |
| M48 | camera compare id not exposed | src/services/api.ts | KILLED | C6 | C6 | restored-sha-OK |
| M49 | Link mode sends no compare id | src/screens/HomeScreen.tsx | KILLED | L1 | L1 | restored-sha-OK |
| M50 | Link mode request not on the metered allowlist | src/screens/HomeScreen.tsx | KILLED | L1 | L1 | restored-sha-OK |
| M51 | /usage/status not marked | src/services/usageService.ts | KILLED | B1 B4 B5 B8 B11 B13 B14a B14b B16 | B1 | restored-sha-OK |
| M52 | legacy header not sent at register | src/services/authService.ts | KILLED | B11 B12 | B12 | restored-sha-OK |
| M53g | legacy header not sent on the Google sign-in | src/services/authService.ts | KILLED | I1 | I1 | restored-sha-OK |
| M53a | legacy header not sent on the Apple sign-in | src/services/authService.ts | KILLED | I1 | I1 | restored-sha-OK |

