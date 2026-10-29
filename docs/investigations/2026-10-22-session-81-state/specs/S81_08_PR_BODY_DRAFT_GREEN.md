# S81-08 CLIENT-FIRST-OTA: request-context headers, stable device id, exact reset time

Client lane (SmartCompareApp only). **No runtime flag**: React Native reads no per-call env flag, so this unit merges to main dark for the client and **ships only in the first post-approval OTA**, published only after the owner's DATED ledger line of `ENABLE_LEGACY_FINGERPRINT_READER=true` on `web` (OWNER_ACTIONS item 32, the S81-08b reader; never "after S81-08b merges") and after the App Privacy answers are updated (UB-R4). As of the newest ledger line read for this PR (2026-10-29 07:29) that dated flip line is NOT yet recorded, so the OTA precondition is open. Build 3 (1.0.0 (3), in review) never runs this code and sends none of the new headers.

Rulings: `specs/RULINGS_S81_08.md` R-S08-1..R-S08-15 (amended by RULINGS_S81_08B R-S08B-1 / R-S08B-5), the RED gate `specs/GATE_S81_08.md` GC-1..GC-11, the review corrections, the spec `.qa-s80/S81-08_UNIT_SPEC.md` (precedence GATE > RULINGS > review > spec). Base `e7c81956` (#376); branch `feature/s81-s08-client-first-ota`; GREEN commit `3f990a69`.

## What it does

- **Request headers** (`src/services/requestContext.ts`, the S81-05 contract): `X-Device-Fingerprint` (64 lower-case hex) and `X-AI-Consent-Version` (`String(AI_CONSENT_VERSION)`, only when the SAVED ACCOUNT holds a current consent record) ride ONLY the metered requests a call site marks with `withRequestContext()` (R-S08-5; the request interceptor reads the marker; no route literal, so `consent/aiDispatchFence.s69` is unchanged): the REST GET and the POST `/api/v1/text/compare`, `/api/v1/url/compare` (Link mode), `/api/v1/usage/status`. Both camera attempts (`/api/v1/image/identify` + its U13c 401 retry) and the SSE request build the same headers with `buildContextHeaders()`. Nothing new rides history, feedback, events, legal, the auth refresh or share.
- **Compare id** (R-S08-1 / R-S08-14 / R-S08-15): `X-Compare-Request-Id` = `newCompareRequestId()` (a lower-case uuid4, else no header) minted at the call site, ONE per compare attempt, shared by the SSE request and its single REST fallback and by both camera attempts; exposed additively: `streamComparison(...).compareRequestId`, the camera result field `compareRequestId` (GC-3), a HomeScreen ref for Link mode (no reader until SF1 / CL3).
- **Capabilities** (R-S08-6): `CLIENT_CAPABILITIES = []`, so no `X-Client-Capabilities` header (S81-11 adds `price_asof` together with the as-of rendering).
- **Device id** (`src/services/deviceFingerprint.ts`, R-S08-7 / GC-1): `getDeviceFingerprint(): Promise<string>` (contract unchanged) = SHA-256 hex of the lower-cased SecureStore UUID `device_fp_nonce` (the existing item, so an installed app keeps one id across the OTA), never osBuildId; `getDeviceIdentity()` -> `{hash, source}` (`securestore` | `idfv` | `android_id`); the iOS IDFV / Android ANDROID_ID fallback ONLY when SecureStore throws, never cached or persisted; no fallback = a rejection with the ORIGINAL SecureStore error. One nonce read serves the new and the legacy hash.
- **Legacy value** (R-S08-4 as amended by R-S08B-1 / R-S08B-5): `legacyDeviceFingerprintHash()` = the build-3 composition `applicationId|osBuildId|nonce` byte for byte; `X-Device-Fingerprint-Legacy` ONLY at POST `/api/v1/auth/register` and the two social sign-ins (after the native sheet), beside a resolved `X-Device-Fingerprint`, while `Date.now() < LEGACY_FINGERPRINT_HEADER_UNTIL_MS` (2027-03-31T21:00:00Z, a runtime cutoff); every call to a new deviceFingerprint export sits in its own try (R-S08-9). Never at share, compares, camera, SSE or usage status.
- **Consent** (R-S08-3): stays PER ACCOUNT; no device-level copy, no device id in AsyncStorage; the request path reads the record through `hasCurrentAiConsentForRequest` (an in-memory per-account memo dropped by `recordAiConsent` / `clearAiConsent` and by a signed-out request; a storage failure is never remembered); a signed-out device or a `getSavedUser` failure sends no consent header.
- **Reset time** (`src/utils/resetTime.ts`; R-S08-2 / R-S08-8 / R-S08-10 / R-S08-14, GC-2 / GC-5): precedence `retry_after_seconds`, then `retry_after` (whole seconds 1..172800), then `resets_at` (strictly after now, at most 48 h ahead); `HH:MM` device-local, 24-hour, ASCII digits, rounded to the minute. The limit sheet: daily state always, open / unknown states only for a daily axis (`counted_scope` on `/usage/status`, `scope` on the 429: `daily` / `device_daily`), monthly never, the fetched status first. The Home pill: `useComparisonCounter` exposes `resetsAt` only for a daily `counted_scope` (and now accepts a status without `used.lifetime`, R-S08-13). With no reset field (today's server) both render the build-3 tree and copy byte for byte.
- **Sentry** (R-S08-12): `SENSITIVE_HEADERS` += `x-device-fingerprint`, `x-device-fingerprint-legacy`. No header value, hash or id is logged anywhere.
- **Failure rule**: a header is never sent empty, never overwrites a value the request carries (any letter case), and a failing builder only omits its own header; the device-id read on the request path is bounded at 1,000 ms.

## Defect / finding ids -> RED nodes (`SmartCompareApp/__tests__/s81_08/`, 87 rows: 54 RED + 33 PIN at base)

| id (source) | what | RED nodes |
|---|---|---|
| PLAN_S81 VERIFY "Quota, auth, refusal" / A7 / R5 / R-S05-7 (no context header on any metered request) | device + consent on the metered allowlist; compare id per attempt; capabilities empty; builders never block | requestHeaders B1, B2, B2b, B4, B5, B6, B7, B9, B10, B11, B13, B14a-d, B15, B16, B18; cameraHeaders C1-C6; sseHeaders D1-D6; resetRender L1 |
| A7 finding 12 / R5 finding 16 (osBuildId makes the id change on an OS update; near-fingerprinting composition) | SecureStore id, IDFV / ANDROID_ID fallback, `{hash, source}` | deviceId A1-A13 |
| R-S05-1 / R-S08-4 (+ R-S08B-1 / R-S08B-5) dual-VALUE transition, K1 | the legacy value at register + the two social sign-ins only, dated cutoff | requestHeaders B8, B11, B12, B14c, B17; socialLegacy I1-I5 |
| R-S08-3 / K2 (5.1.2(i): consent per person) | per-account consent, request memo, no device copy | consentRecord E1-E10, A9b; requestHeaders B15 |
| Owner decision 5 + R-S08-2 / R-S08-14 (BL2 / RF9 honesty) | exact local reset time on the daily axis only | resetTime F1-F6; resetRender G1-G11, G5b, G7b, G9b; i18nKeys H1-H3 |
| R-S08-12 (C18) | Sentry redacts the two fingerprint headers by name | requestHeaders B19 |
| R-S08-15 (RF12) | compare ids exposed for SF1 / CL3 | cameraHeaders C6; sseHeaders D3 (Link-mode ref: no row, stated limit) |

## Deliberate pin changes (spec 4.1)

| # | node | change | reason |
|---|---|---|---|
| E1 | `__tests__/deviceFingerprint.test.ts` > "hashes applicationId|osBuildId|nonce in that order via SHA-256" (title kept, node id unchanged) | `getDeviceFingerprint()` now digests `persisted-nonce` -> `hash(persisted-nonce)`; the build-3 assertion moved verbatim onto `legacyDeviceFingerprintHash()` | R-S08-7: no osBuildId in the new id |
| E2 | same file > "retries after a transient SecureStore failure instead of replaying the rejection" | the retry now resolves `hash(nonce-ok)`; `.rejects.toBe(err)` kept (no IDFV in this suite's mock, the ORIGINAL error) | R-S08-10 / review RF5 |
| E3 | `__tests__/api.cameraAuthRetry.u13c.test.ts` T1 / T9 / T17a / T17b / T19 | NONE: measured 20 / 20 green, no node moved (the root shims give no v4 id and no digest; the authService mock has no getSavedUser) | prediction held |
| E4 | `__tests__/screens/paywall.noSubscriptionUi.s69.test.ts` T2-c1 / T2-c2 | `PAYWALL_ALLOW` += `paywall.limit.resets_at` (the T2-e1 / T2-e2 honesty checks now cover it) | the exact key-set fence |
| (E6) | the T2-a2 PaywallScreen line cap 250 | NOT needed: `split(/\r?\n/).length` = 250 (the reset rule lives in `resetTime.sheetResetClock`, R-S08-8) | |

No `.snap` file, no `package*.json`, `app.json`, `eas.json` or native file changed; `__tests__/setup.ts` and every `__mocks__/` shim untouched; `consent/aiDispatchFence.s69` unchanged and green.

## Gates (tools by path from `SmartCompareApp` through the junction; one jest at a time)

- First gate at base `e7c81956` (GC-8): RED 54 failed (assertion only) / 33 passed; FULL suite 3,694 passed outside `s81_08` with only the four nativeBundle.w37 drift nodes red (d5 / k2 / k4 / k5).
- `[tsc] tag=s08g-7.1-tsc rc=0 errors=0`; ESLint 0 errors, problem counts per edited file equal at base and HEAD (new files: `requestContext.ts` 2 `no-require-imports` warnings = the lazy-require idiom of api.ts; RED `resetRender` 3 `import/first` warnings, GC-7).
- `[jest] tag=s08g-7.2a-red rc=0` 87 / 87; `[jest] tag=s08g-7.2b-4.1 rc=0` 38 / 38; `[jest] tag=s08g-7.2c-set55` 593 passed / 4 failed = the 48-suite set 454 / 4 (the drift nodes) + the R-S08-11 seven 139 / 0; in-band ORDER pairs (argv sequencer) A 393 / 393 and B 393 / 393; in-band RED + 4.1 125 / 125.
- `[jest] tag=s08g-7.2f-full-head`: 388 suites, 3,811 tests, **3,781 passed = 3,694 + 87**, 4 failed = the drift nodes, 13 skipped, 13 todo, snapshots 42 / 42; node-level diff base vs HEAD: 0 non-RED nodes moved.
- Backend comm set (30 files = the spec 7.3 twenty-five + the CLAUDE.md / header-contract readers; re-derived at HEAD: no backend file changed, so the module-reference grep is empty) vs a FRESH base record at `e7c81956` in a detached scratch worktree without a junction (removed afterwards, verified gone):
  - `[pyt] tag=s08g-be-base-01 elapsed=132s bound=1200s status=OK rc=0` 1899 passed, 4 deselected; `[hermeticity] sentinel checked 1899 test(s)`; `[netguard] blocked 41 attempt(s) from 31 node(s)`
  - `[pyt] tag=s08g-be-base-02 elapsed=46s bound=1200s status=OK rc=0` 589 passed; `[hermeticity] sentinel checked 589 test(s)`; `[netguard] blocked 24 attempt(s) from 2 node(s)`
  - `[pyt] tag=s08g-be-head-01 elapsed=215s bound=1200s status=OK rc=0` 1899 passed, 4 deselected; same hermeticity / netguard lines
  - `[pyt] tag=s08g-be-head-02 elapsed=21s bound=1200s status=OK rc=0` 589 passed; same lines
  - FAILED sets base 0 / HEAD 0: **branch-only-new EMPTY**. CI-order (the 30 files sorted, one call): `[pyt] tag=s08g-ci-order elapsed=202s bound=1200s status=OK rc=0` 2488 passed, 4 deselected; `[hermeticity] sentinel checked 2488 test(s)`; `[netguard] blocked 65 attempt(s) from 33 node(s)`.
- The section-6 mutation table is NOT re-run by GREEN (GC-9 / GC-11: the adversaries re-run it on these bytes).

## [NATIVE READ] (owner; AR as code points, `_` = space)

- `paywall.limit.resets_at`: EN "Your free comparisons refresh at {{time}}."; AR U+062A U+062A U+062C U+062F U+062F _ U+0645 U+0642 U+0627 U+0631 U+0646 U+0627 U+062A U+0643 _ U+0627 U+0644 U+0645 U+062C U+0627 U+0646 U+064A U+0629 _ U+0627 U+0644 U+0633 U+0627 U+0639 U+0629 _ "{{time}}."
- `home.headerCounter.resets`: EN "resets {{time}}"; AR U+062A U+062A U+062C U+062F U+062F _ "{{time}}"
- `home.headerCounter.a11yResets`: EN "{{free}} of {{total}} free comparisons, plus {{bonus}} bonus. Free comparisons refresh at {{time}}"; AR "{{free}}" _ U+0645 U+0646 _ "{{total}}" _ U+0645 U+0642 U+0627 U+0631 U+0646 U+0627 U+062A _ U+0645 U+062C U+0627 U+0646 U+064A U+0629 U+060C _ U+0628 U+0627 U+0644 U+0625 U+0636 U+0627 U+0641 U+0629 _ U+0625 U+0644 U+0649 _ "{{bonus}}" _ U+0625 U+0636 U+0627 U+0641 U+064A U+0629 U+060C _ U+0648 U+062A U+062A U+062C U+062F U+062F _ U+0627 U+0644 U+0645 U+0642 U+0627 U+0631 U+0646 U+0627 U+062A _ U+0627 U+0644 U+0645 U+062C U+0627 U+0646 U+064A U+0629 _ U+0627 U+0644 U+0633 U+0627 U+0639 U+0629 _ "{{time}}"

`paywall.limit.resets_at` and `home.headerCounter.resets` equal the spec 2.7 code points. `home.headerCounter.a11yResets` names the subject explicitly in the time clause ("and the free comparisons refresh at {{time}}") instead of the spec's "and they refresh at {{time}}", mirroring the GC-4 EN wording so the clause does not read as covering the bonus (R-S08-2); the owner confirms whether it reads naturally and whether the bonus is clearly excluded.

## Stated limits

1. The consent header is the client's claim (the server cannot verify it).
2. The legacy header and its osBuildId read live until 2027-03-31T21:00Z at three sites (register, both social sign-ins); a later OTA deletes the code.
3. A device whose SecureStore fails intermittently can present two ids (IDFV can be null before the first unlock); neither id is a strong device signal against a script that sends random hashes.
4. The reset time is the device-local clock (UAE / Oman read 01:00 for a Riyadh midnight) and renders only once S81-09 sends the fields; the pill's COUNT is S81-09's client half to change.
5. A status without `used.lifetime` drives the gate from its axes but does not decrement them between compares (the backend 429 stays the backstop).
6. The register / social legacy read is unbounded, like the base device read at those sites; the request-path device read is bounded at 1,000 ms.
7. The Link-mode compare id sits in a HomeScreen ref with no reader until SF1 / CL3; `compareTextPair` (0 callers) is marked but unpinned; a thrown camera error carries no id.
8. No on-device E2E in CI: the owner's TestFlight check after the OTA is the proof; S81-05 never logs header values, so arrival is visible only through S81-09's header-state metric. Expo web is not a target.
9. Test harness (RED D7, GC-7): row L1 reaches the real interceptor through axios internals (`interceptors.request.handlers`), so an axios upgrade that renames them breaks that row, not the product; the camera id exposure is the result field (GC-3; C6 accepts it).

## Owner steps (names only)

1. Update the App Store Connect App Privacy answers BEFORE the OTA (Device ID, linked to the user, App Functionality / fraud prevention, not tracking).
2. Set `ENABLE_LEGACY_FINGERPRINT_READER=true` on `web` and record the DATED ledger line (OWNER_ACTIONS item 32): the OTA precondition.
3. Publish the first post-approval OTA (UB-R4) only after 1 and 2, together with S81-11 and the consent v3 copy.
4. TestFlight check of a compare, the camera and the limit sheet in EN and AR; the native read of the three AR strings above.

## CLAUDE.md

The unit row "SESSION 81 unit (S81-08 CLIENT-FIRST-OTA, 2026-10-29; NO runtime flag ...)" after the S81-15 row and before `## Tests` (GC-6: no device-mirror sentence, legacy only at register + the two social sign-ins, ships only after the dated item-32 line), plus one sentence each on the Frontend Services `api.ts` bullet and the `usage_service.py` Device-bound sentence. No backend test reads these lines (no R11-style pin).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
