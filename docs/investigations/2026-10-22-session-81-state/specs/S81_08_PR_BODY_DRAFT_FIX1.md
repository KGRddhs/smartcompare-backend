# S81-08 CLIENT-FIRST-OTA: request-context headers, stable device id, exact reset time

Client lane (SmartCompareApp + docs). **No runtime flag**: React Native reads no per-call env flag, so this unit merges to main dark for the client and **ships only in the first post-approval OTA**, published only after LEGAL-V3 is live (backend deployed AND landing redeployed) and after the owner's DATED ledger line of `ENABLE_LEGACY_FINGERPRINT_READER=true` on `web` (OWNER_ACTIONS item 32, the S81-08b reader; never "after S81-08b merges"), UB-R4 / 5.1.2(i). As of the newest ledger line read for this PR no dated flip line is recorded, so the OTA precondition is open. Build 3 (1.0.0 (3), in review) never runs this code and sends none of the new headers.

Rulings: `specs/RULINGS_FIX1_S81_08.md` F1-1..F1-12 (fix round 1, binding over the rest), `specs/RULINGS_S81_08.md` R-S08-1..R-S08-15 (amended by RULINGS_S81_08B R-S08B-1 / R-S08B-5), the RED gate `specs/GATE_S81_08.md` GC-1..GC-11, the review corrections, the spec `.qa-s80/S81-08_UNIT_SPEC.md`. Base `e7c81956` (#376); branch `feature/s81-s08-client-first-ota`; commits `3f990a69` (GREEN) and `bcf75f84` (fix round 1).

## What it does

- **Request headers** (`src/services/requestContext.ts`, the S81-05 contract): `X-Device-Fingerprint` (64 lower-case hex) and `X-AI-Consent-Version` (`String(AI_CONSENT_VERSION)`, only when the SAVED ACCOUNT holds a current consent record) ride ONLY the metered requests a call site marks with `withRequestContext()` (R-S08-5; no route literal, so `consent/aiDispatchFence.s69` is unchanged): the REST GET and the POST `/api/v1/text/compare`, `/api/v1/url/compare` (Link mode), `/api/v1/usage/status`. Both camera attempts (`/api/v1/image/identify` + its U13c 401 retry) and the SSE request build the same headers with `buildContextHeaders()`. No new HEADER rides history, feedback, events, legal, the auth refresh or share; a header is never sent empty and never overwrites a value the request carries, in any letter case (gate row X6).
- **Compare id** (R-S08-1 / R-S08-14 / R-S08-15): `X-Compare-Request-Id` = `newCompareRequestId()` (a lower-case uuid4, else no header) minted at the call site, ONE per compare attempt, shared by the SSE request and its single REST fallback and by both camera attempts; exposed additively: `streamComparison(...).compareRequestId`, the camera result field `compareRequestId` (GC-3), a HomeScreen ref for Link mode (no reader until SF1 / CL3).
- **Capabilities** (R-S08-6): `CLIENT_CAPABILITIES = []`, so no `X-Client-Capabilities` header (S81-11 adds `price_asof` with the as-of rendering).
- **Device id** (`src/services/deviceFingerprint.ts`, R-S08-7 / GC-1): `getDeviceFingerprint(): Promise<string>` = SHA-256 of the lower-cased SecureStore UUID `device_fp_nonce` (the existing item: an installed app keeps one id across the OTA), never osBuildId; `getDeviceIdentity()` -> `{hash, source}`; the iOS IDFV / Android ANDROID_ID fallback ONLY when SecureStore throws, never cached or persisted; no fallback = the ORIGINAL SecureStore error. One nonce read serves the new and the legacy hash.
- **Legacy value** (R-S08-4 as amended by R-S08B-1 / R-S08B-5): the build-3 composition `applicationId|osBuildId|nonce` rides `X-Device-Fingerprint-Legacy` ONLY at POST `/api/v1/auth/register` and the two social sign-ins, beside a resolved `X-Device-Fingerprint`, while `Date.now() < LEGACY_FINGERPRINT_HEADER_UNTIL_MS` (2027-03-31T21:00:00Z); a failed legacy read is retried at the next register / social sign-in, never latched (gate row X9).
- **Changed VALUES (F1-6; the shapes do not change):** after the OTA the `X-Device-Fingerprint` header at register and the two social sign-ins and the share BODY's `device_fingerprint_hash` carry the NEW id (the share call is unchanged; its value is the new id). Invite rows written by OTA clients therefore mix the build-3 and the new compositions, so a revived SAME_DEVICE check (S81-08d) must match both.
- **Consent** (R-S08-3): stays PER ACCOUNT; no device-level copy, no device id in AsyncStorage; the request path reads the record through `hasCurrentAiConsentForRequest`, an in-memory memo KEYED BY THE ACCOUNT (pinned now: gate rows F1-1a / F1-1b, spec M24 killed) and dropped by `recordAiConsent` / `clearAiConsent`, by a signed-out request and, since fix round 1, by `authService.logout()` (F1-1, gate row F1-1c); a read racing an Agree never memoises (gate row X4). `__tests__/setup.ts`'s global consent mock exports `hasCurrentAiConsentForRequest` (it answers what the mocked `hasCurrentAiConsent` answers; no user: false) and the jest-only fallback in `consentHeaderValue` is deleted (F1-3, gate rows F1-3a / F1-3b).
- **Reset time** (`src/utils/resetTime.ts`; R-S08-2 / R-S08-8 / R-S08-10 / R-S08-14, GC-2 / GC-5): precedence `retry_after_seconds`, then `retry_after` (whole seconds 1..172800), then `resets_at` (strictly after now, at most 48 h ahead); `HH:MM` device-local, 24-hour, ASCII digits, rounded to the minute. The limit sheet: daily state always, open / unknown states only for a daily axis, monthly never, the fetched status first. A RELATIVE reset of the 429 detail is anchored ONCE per detail object (F1-4, gate row F1-4), so the re-render after the `/usage/status` fetch keeps the minute; the fetched status (S81-09's absolute `resets_at`) still decides first (GC-2).
- **Home pill** (F1-8 / F1-9; the S81-09 contract, its brief Q8): when `counted_scope` names a daily axis (`daily` / `device_daily`) and the status carries that axis's remaining (`remaining.daily` / `remaining.device_daily`), the pill COUNTS that axis (`useComparisonCounter`: total = `limits.daily`, used = total minus the axis's remaining less the compares consumed since hydration), never `lifetime_free - used.lifetime`, which stays for a status without one (build-3 backends) (gate rows F1-8a / F1-8b). The pill reads `N/T free . resets HH:MM . +B`: the subjectless resets node follows the free count, never the bonus (gate rows F1-9 / F1-9b); the a11y label is unchanged (GC-4). With no reset field (today's server) both the sheet and the pill render the build-3 tree and copy byte for byte.
- **Sentry** (R-S08-12, F1-5): `SENSITIVE_HEADERS` += `x-device-fingerprint`, `x-device-fingerprint-legacy`; the header doc comment now names them. No header value, hash or id is logged anywhere.
- **Privacy inventory** (F1-7): `docs/privacy-data-inventory.md` row 7 (DeviceID) WHERE cell refreshed (the SecureStore install id with the IDFV / ANDROID_ID fallback on the metered requests, register, the social sign-ins and the share body; the legacy composition at register + the two social sign-ins until 2027-03-31T21:00Z; what build 3 sends); type, Linked, Tracking and Purposes unchanged; the c3 / c5 fences green (measured).

## Defect / finding ids -> test nodes (`SmartCompareApp/__tests__/s81_08/`)

| id (source) | what | nodes |
|---|---|---|
| PLAN_S81 VERIFY "Quota, auth, refusal" / A7 / R5 / R-S05-7 | device + consent on the metered allowlist; compare id per attempt; capabilities empty; builders never block | requestHeaders B1, B2, B2b, B4, B5, B6, B7, B9, B10, B11, B13, B14a-d, B15, B16, B18; cameraHeaders C1-C6; sseHeaders D1-D6; resetRender L1; gateRows X6 |
| A7 finding 12 / R5 finding 16 | SecureStore id, IDFV / ANDROID_ID fallback, `{hash, source}` | deviceId A1-A13 |
| R-S05-1 / R-S08-4 (+ R-S08B-1 / R-S08B-5), K1 | the legacy value at register + the two social sign-ins only, dated cutoff, never latched | requestHeaders B8, B11, B12, B14c, B17; socialLegacy I1-I5; gateRows X9 |
| R-S08-3 / K2; ADV1 correctness MAJ-1 = appreview MAJ-A1; correctness m4 / m5 / m9 | per-account consent: the memo key, the logout drop, the generation guard, no jest-only fallback | consentRecord E1-E10, A9b; requestHeaders B15; gateRows F1-1a, F1-1b, F1-1c, X4, F1-3a, F1-3b |
| Owner decision 5 + R-S08-2 / R-S08-14 (BL2 / RF9); correctness m6; appreview m4 / m5 | exact local reset time on the daily axis; the anchored relative reset; the counted-axis pill count; the pill order | resetTime F1-F6; resetRender G1-G11, G5b, G7b, G9b; i18nKeys H1-H3; gateRows F1-4, F1-8a, F1-8b, F1-9, F1-9b |
| R-S08-12 (C18) | Sentry redacts the two fingerprint headers by name | requestHeaders B19 |
| R-S08-15 (RF12) | compare ids exposed for SF1 / CL3 | cameraHeaders C6; sseHeaders D3 (Link-mode ref: no row, stated limit) |

PIN-type gate rows (they pass on the GREEN bytes and are proven by the mutant they name, measured on both the GREEN bytes and the final bytes): F1-1a / F1-1b (spec M24), X4, X6, X9; F1-8b and F1-9b pin the build-3 shapes. RED gate rows (each failed on an expect assertion at `3f990a69`): F1-1c, F1-3a, F1-3b, F1-4, F1-8a, F1-9.

## Deliberate pin and harness changes

| # | node / file | change | reason |
|---|---|---|---|
| E1 | `__tests__/deviceFingerprint.test.ts` > "hashes applicationId|osBuildId|nonce in that order via SHA-256" (title kept) | `getDeviceFingerprint()` digests `persisted-nonce`; the build-3 assertion moved onto `legacyDeviceFingerprintHash()` | R-S08-7 |
| E2 | same file > "retries after a transient SecureStore failure instead of replaying the rejection" | the retry resolves `hash(nonce-ok)`; `.rejects.toBe(err)` kept | R-S08-10 / RF5 |
| E3 | `__tests__/api.cameraAuthRetry.u13c.test.ts` | NONE (20 / 20, no node moved) | prediction held |
| E4 | `__tests__/screens/paywall.noSubscriptionUi.s69.test.ts` T2-c1 / T2-c2 | `PAYWALL_ALLOW` += `paywall.limit.resets_at` | the exact key-set fence |
| F1-3 | `__tests__/setup.ts` (the global consent mock) | gains `hasCurrentAiConsentForRequest` (delegates to the mocked `hasCurrentAiConsent`; no user: false) | the production fallback branch is deleted; the full suite moves no node (L1 included) |

No `.snap`, `package*.json`, `app.json`, `eas.json` or native file changed; every `__mocks__/` shim untouched; `consent/aiDispatchFence.s69` unchanged and green; `PaywallScreen.tsx` untouched by the fix round (the T2-a2 250-line cap holds).

## Gates (fix round 1, on the final bytes; tools by path from `SmartCompareApp` through the junction; node v24.11.1, jest 29.7.0, tsc 5.9.3, eslint v9.39.4; one jest at a time)

- `[jest] tag=fix1-red-gaterows-head start=1793261685 end=1793261745 rc=1 elapsed=60s | Test Suites: 1 failed, 1 total | Tests: 6 failed, 7 passed, 13 total (RED step at GREEN HEAD 3f990a69; rows.py red: bad=0)`
- `[tsc] tag=fix1-tsc-dev1 start=1793262274 end=1793262311 rc=0 elapsed=37s errors=0`
- `[jest] tag=fix1-green-dev1 start=1793262326 end=1793262379 rc=0 elapsed=53s | Test Suites: 10 passed, 10 total | Tests: 100 passed, 100 total`
- `[jest] tag=fix1-inventory-fences start=1793262521 end=1793262554 rc=1 elapsed=33s | Test Suites: 1 failed, 2 passed, 3 total | Tests: 4 failed, 62 passed, 66 total (the 4 nativeBundle.w37 drift nodes d5/k2/k4/k5 only)`
- `[eslint] tag=fix1-eslint-delta start=1793262605 end=1793262648 rc=0 elapsed=43s (0 errors; 1 new warning authService no-require-imports 3->4, then fixed by an eslint-disable-next-line)`
- `[eslint] tag=fix1-eslint-delta2 start=1793262671 end=1793262725 rc=0 elapsed=54s (0 errors; 0 new problems vs the byte copies over the 10 changed client files)`
- `[jest] tag=fix1-red+gate start=1793262778 end=1793262811 rc=0 elapsed=33s | Test Suites: 10 passed, 10 total | Tests: 100 passed, 100 total`
- `[jest] tag=fix1-4.1 start=1793262819 end=1793262839 rc=0 elapsed=20s | Test Suites: 3 passed, 3 total | Tests: 38 passed, 38 total`
- `[jest] tag=fix1-set55 start=1793262849 end=1793262892 rc=1 elapsed=43s | Test Suites: 1 failed, 54 passed, 55 total | Tests: 4 failed, 593 passed, 597 total (the drift nodes only)`
- `[jest] tag=fix1-inband-A start=1793262928 end=1793262971 rc=0 elapsed=43s | Test Suites: 31 passed, 31 total | Tests: 418 passed, 418 total`
- `[jest] tag=fix1-inband-B start=1793262981 end=1793263033 rc=0 elapsed=52s | Test Suites: 31 passed, 31 total | Tests: 418 passed, 418 total`
- `[jest] tag=fix1-inband-red+gate+4.1 start=1793263040 end=1793263066 rc=0 elapsed=26s | Test Suites: 13 passed, 13 total | Tests: 138 passed, 138 total`
- `[jest] tag=fix1-full-head start=1793263081 end=1793263155 rc=1 elapsed=74s | Test Suites: 1 failed, 3 skipped, 385 passed, 386 of 389 total | Tests: 4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total (Snapshots 42/42; the 4 failures = nativeBundle.w37 d5/k2/k4/k5; node diff vs GREEN: +13 gate rows, 0 gone, 0 moved)`
- `[jest] tag=fix1-red+gate-committed start=1793265743 end=1793265800 rc=0 elapsed=57s | Test Suites: 10 passed, 10 total | Tests: 100 passed, 100 total (after the commit bcf75f84, on the committed bytes)`
- `[commit] bcf75f844d50ad11935a2512f77054d5a36ed4b3 through the pre-commit hook: rc=0 elapsed=166s (gitleaks / secret shapes / ESLint on the staged client files: 0 errors, 14 warnings)`
- Backend 30-file comm set at HEAD (no backend file changed; re-derived: no backend test reads `docs/privacy-data-inventory.md`) vs GREEN's fresh base record at `e7c81956` (1899 + 589 passed, 0 failed):
  - `[pyt] tag=s08f1-be-head-01 start=2026-10-29 12:10:47 end=2026-10-29 12:15:35 elapsed=288s bound=1200s status=OK rc=0 (chunk01, 25 files: 1899 passed, 4 deselected; [hermeticity] sentinel checked 1899 test(s); [netguard] blocked 41 attempt(s) from 31 node(s))`
  - `[pyt] tag=s08f1-be-head-02 start=2026-10-29 12:15:45 end=2026-10-29 12:16:44 elapsed=59s bound=1200s status=OK rc=0 (chunk02, 5 files: 589 passed; [hermeticity] sentinel checked 589 test(s); [netguard] blocked 24 attempt(s) from 2 node(s))`
  - `comm: FAILED node ids HEAD 0, base 0 (GREEN's fresh e7c81956 record, be_base_01 1899 passed / be_base_02 589 passed); branch-only-new EMPTY`

## Mutation table (F1-12; in place on sha-verified byte copies under `.qa-mutation.lock`, restored and sha-compared after every mutant)

24 mutants: 23 KILLED, 1 SURVIVED (accepted equivalent), 0 other.

| id | verdict | failing rows (assertion) | expected | restore | what |
|---|---|---|---|---|---|
| M13 | KILLED | B14b B5 E9 F1-1a F1-1b F1-1c X4 | B5,E9 | restored-sha-OK | consent header sent without a current record |
| M15b | KILLED | B14b | B14b | restored-sha-OK | consent builder failure throws through |
| M22 | KILLED | E9 X4 | E9 | restored-sha-OK | consent memo not invalidated by recordAiConsent |
| M23 | KILLED | E9 | E9 | restored-sha-OK | consent memo not invalidated by clearAiConsent |
| M24 | KILLED | F1-1a F1-1b | F1-1a,F1-1b | restored-sha-OK | consent memo ignores the account (spec M24) |
| M26 | SURVIVED | - | - | restored-sha-OK | signed-out guard dropped (accepted equivalent, F1-2) |
| X4 | KILLED | X4 | X4 | restored-sha-OK | consent memo generation guard removed |
| X6 | KILLED | X6 | X6 | restored-sha-OK | only-if-absent check becomes case-sensitive |
| X9 | KILLED | X9 | X9 | restored-sha-OK | a failed legacy read is replayed for the process |
| MF1 | KILLED | F1-1c | F1-1c | restored-sha-OK | logout() keeps the consent memo (F1-1 drop removed) |
| MF3 | KILLED | F1-3b | F1-3b | restored-sha-OK | the jest-only fallback restored (F1-3) |
| MF3a | KILLED | F1-3a L1 | F1-3a,L1 | restored-sha-OK | the global consent mock loses hasCurrentAiConsentForRequest (F1-3) |
| MF4 | KILLED | F1-4 | F1-4 | restored-sha-OK | the 429 relative reset re-anchored at every render (F1-4) |
| MF4b | KILLED | F1-4 | F1-4 | restored-sha-OK | the anchor is never stored (F1-4) |
| M37f | KILLED | G11 | G11 | restored-sha-OK | spec M37 on the final line: the sheet prefers initialUsage over the fetched status |
| M47 | KILLED | G5b G6 | G5b,G6 | restored-sha-OK | open / unknown sheet states ignore the scope |
| MF8a | KILLED | F1-8a | F1-8a | restored-sha-OK | the pill ignores the counted axis (lifetime math always, F1-8) |
| MF8b | KILLED | F1-8a F1-8b | F1-8a | restored-sha-OK | the device axis counted from remaining.daily (F1-8) |
| MF8c | KILLED | F1-8a | F1-8a | restored-sha-OK | the axis count ignores local compares (F1-8) |
| MF8d | KILLED | F1-8b | F1-8b | restored-sha-OK | a non-daily counted_scope drives the count (F1-8) |
| MF8e | KILLED | F1-8b | F1-8b | restored-sha-OK | a named axis without its remaining falls back to remaining.daily (F1-8) |
| M46 | KILLED | G7 | G7 | restored-sha-OK | hook ignores counted_scope for resetsAt |
| MF9 | KILLED | F1-9 | F1-9 | restored-sha-OK | the pill order reverted: the bonus before the resets node (F1-9) |
| M33 | KILLED | F1-9b G9 G9b | G9 | restored-sha-OK | pill resets node rendered when absent |

## [NATIVE READ] (owner; AR as code points, `_` = space; unchanged by fix round 1)

- `paywall.limit.resets_at`: EN "Your free comparisons refresh at {{time}}."; AR U+062A U+062A U+062C U+062F U+062F _ U+0645 U+0642 U+0627 U+0631 U+0646 U+0627 U+062A U+0643 _ U+0627 U+0644 U+0645 U+062C U+0627 U+0646 U+064A U+0629 _ U+0627 U+0644 U+0633 U+0627 U+0639 U+0629 _ "{{time}}."
- `home.headerCounter.resets`: EN "resets {{time}}"; AR U+062A U+062A U+062C U+062F U+062F _ "{{time}}"
- `home.headerCounter.a11yResets`: EN "{{free}} of {{total}} free comparisons, plus {{bonus}} bonus. Free comparisons refresh at {{time}}"; AR "{{free}}" _ U+0645 U+0646 _ "{{total}}" _ U+0645 U+0642 U+0627 U+0631 U+0646 U+0627 U+062A _ U+0645 U+062C U+0627 U+0646 U+064A U+0629 U+060C _ U+0628 U+0627 U+0644 U+0625 U+0636 U+0627 U+0641 U+0629 _ U+0625 U+0644 U+0649 _ "{{bonus}}" _ U+0625 U+0636 U+0627 U+0641 U+064A U+0629 U+060C _ U+0648 U+062A U+062A U+062C U+062F U+062F _ U+0627 U+0644 U+0645 U+0642 U+0627 U+0631 U+0646 U+0627 U+062A _ U+0627 U+0644 U+0645 U+062C U+0627 U+0646 U+064A U+0629 _ U+0627 U+0644 U+0633 U+0627 U+0639 U+0629 _ "{{time}}"

`paywall.limit.resets_at` and `home.headerCounter.resets` equal the spec 2.7 code points. `home.headerCounter.a11yResets` names the subject explicitly in the time clause ("and the free comparisons refresh at {{time}}") instead of the spec's "and they refresh at {{time}}", mirroring the GC-4 EN wording so the clause does not read as covering the bonus (R-S08-2); the owner confirms whether it reads naturally and whether the bonus is clearly excluded.

Owner question added by fix round 1 (F1-9): in the pill, the AR `home.headerCounter.resets` now sits right after the free count (`N/T free . <resets HH:MM> . +B`); confirm it reads as covering the free comparisons only.

## Stated limits

1. The consent header is the client's claim (the server cannot verify it).
2. The legacy header and its osBuildId read live until 2027-03-31T21:00Z at three sites (register, both social sign-ins); a later OTA deletes the code.
3. A device whose SecureStore fails intermittently can present two ids (IDFV can be null before the first unlock); neither id is a strong device signal against a script that sends random hashes.
4. The reset time is the device-local clock (UAE / Oman read 01:00 for a Riyadh midnight), renders only once S81-09 sends the fields, and neither the sheet nor the pill re-renders when the instant passes (the line stays until the next render); a relative 429 reset counts from the first render of that 429 detail object (F1-4), not from the moment the response arrived.
5. On a daily axis the pill's denominator is `limits.daily` (S81-09 sends no device-axis cap; free = 3 / 3) and the compare gate still reads the lifetime-free, daily and monthly axes, not `remaining.device_daily` (the backend 429 stays the backstop); a status without `used.lifetime` is not decremented between compares.
6. The register / social legacy read is unbounded, like the base device read at those sites; the request-path device read is bounded at 1,000 ms.
7. The Link-mode compare id sits in a HomeScreen ref with no reader until SF1 / CL3; `compareTextPair` (0 callers) is marked but unpinned; a thrown camera error carries no id.
8. Equivalent or unpinned under valid values (F1-2 / correctness m1 / m2 / m9): X5 (an empty explicit header counts as absent), X10 / X11 / X12 (the legacy / consent / device value shape checks), X24 (legacy only beside a resolved device id), X30 (the request path through the memo: same answers, more storage reads), X31 (a signed-out request drops the memo: the key and the logout drop guard the switch), spec M26 / M31 (redundant guards), the pill's `FREE_LIMIT` fallback for a status without `limits.daily`.
9. No on-device E2E in CI: the owner's TestFlight check after the OTA is the proof; S81-05 never logs header values, so arrival is visible only through S81-09's header-state metric. Expo web is not a target.
10. Test harness (RED D7, GC-7): row L1 reaches the real interceptor through axios internals (`interceptors.request.handlers`); the gate-rows module worlds call `jest.resetModules()` first (jest-runtime hands an isolated registry a mock the main registry already cached), so the file's row order is load-bearing (stated in its header).

## Owner steps (names only)

1. BEFORE the OTA, re-verify the App Privacy answers (Device ID, linked, App Functionality, not tracking: published 2026-10-11; no change or re-attestation expected), against `docs/privacy-data-inventory.md` row 7.
2. Set `ENABLE_LEGACY_FINGERPRINT_READER=true` on `web` and record the DATED ledger line (OWNER_ACTIONS item 32).
3. Publish the first post-approval OTA only after LEGAL-V3 is live (backend deployed AND landing redeployed) and after the dated item-32 line (UB-R4 / 5.1.2(i)), together with S81-11 and the consent v3 copy.
4. TestFlight check of a compare, the camera and the limit sheet in EN and AR; the native read of the three AR strings above.
5. The 1.0.1 Notes for Review carry the device-identifier note (OWNER_ACTIONS item 34, F1-11; the orchestrator).

Cross-unit (recorded by the orchestrator, nothing in this PR): F1-10 (the privacy s14 IDFV / ANDROID_ID clause is S81-12's text, RULINGS_FIX1_S81_12 F2-7); F1-8 = S81-09 brief Q8 (`remaining.device_daily` with `counted_scope`).

## CLAUDE.md

The unit row "SESSION 81 unit (S81-08 CLIENT-FIRST-OTA, 2026-10-29; NO runtime flag ...)" after the S81-15 row and before `## Tests`, restated in place by fix round 1: the OTA precondition (LEGAL-V3 live + the dated item-32 line), the changed VALUES (F1-6), the consent memo key / logout drop / no jest-only fallback, the anchored relative reset, the counted-axis pill count and the pill order (F1-4 / F1-8 / F1-9), the owner steps (F1-7, re-verify, no change expected), the stated limits; plus the api.ts bullet and the usage_service Device-bound sentence (GREEN). No backend test reads these lines.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
