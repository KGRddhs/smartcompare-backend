# S81-08 unit spec: CLIENT-FIRST-OTA (request-context headers, stable device id, device-keyed consent, exact reset time)

Unit S81-08 CLIENT-FIRST-OTA, client lane (SmartCompareApp only, OTA-capable). Flag: NONE (a client
unit: RN has no per-call env flag; the dated legacy-header cutoff and the capability list are code
constants). Ships ONLY in the first post-approval OTA together with S81-11 and the consent v3 copy
(UB-R4); merges to main before that. No native file is touched (app.json, eas.json, package.json,
package-lock.json unchanged; every module used is already linked in build 1.0.0 (3)).

- Worktree: `C:\Users\SynAckITPC\Documents\AI\sc-s81-s08`, detached at base
  `dfc6502f791cdccbf0a620041f66888a734015d3` (HEAD == base, measured 2026-10-23 15:54 AST);
  `git status --short` EMPTY before and after every probe of this spec (the only file written in the
  worktree is this spec under the gitignored `.qa-s80/`, `.gitignore:72 .qa-*/`).
- Branch for RED/GREEN: `feature/s81-client-first-ota`.
- `SmartCompareApp/node_modules` is a JUNCTION to the clone (`<JUNCTION> node_modules
  [...\smartcompare\SmartCompareApp\node_modules]`); `node_modules/@babel/core/package.json` and
  `node_modules/.bin/jest{,.cmd,.ps1}` present (measured). Never delete anything recursively there.
- Tools (by path from SmartCompareApp, measured): jest 29.7.0, TypeScript 5.9.3, ESLint v9.39.4;
  `node -e 0` 2.25 s at 16:31 and 1.02 s at 16:36 (load varies; one jest at a time).
- Client source at base == build 3: `git diff --stat 683f56c0 dfc6502f -- SmartCompareApp/src
  SmartCompareApp/package.json SmartCompareApp/app.json SmartCompareApp/package-lock.json
  SmartCompareApp/eas.json` is EMPTY, so every client fact below is also a build-3 fact.
- Evidence pointers: unit brief `sc-docs-70/docs/investigations/2026-10-22-session-81-state/specs/S81_08_BRIEF.md`;
  PLAN_S81 client lane S81-08 text (PLAN_S81.md:173) and VERIFY "Quota, auth, refusal" (PLAN_S81.md:101-106);
  owner decisions 2 and 5 (PLAN_S81.md:194, :201); RULINGS_S81_05 R-S05-1 / R-S05-2 / R-S05-10;
  GATE_S81_05 GC-2; RULINGS_FIX1_S81_05; research digests `runs/research/A5.json`, `A7.json`, `R5.json`,
  `R6.json` (session-81 state folder); PLAN_S80 section 0 + `runs/research/contract_freeze.json`
  (session-80 state folder). Measurement notes: `<scratchpad>/S81-08/notes.md`, logs `base_set.log`,
  `base_set.json`, `be_base.log` in the same folder.
- Sister units and contracts: S81-05 REQUEST-CONTEXT (server half, GREEN `e9fd7148` on
  `feature/s81-s05-request-context`, read via `git show`, never changed): header names, shapes and the
  None rule this unit must satisfy. S81-09 DEVICE-QUOTA-RIYADH (NOT BUILT): consumes
  X-Device-Fingerprint, X-Device-Fingerprint-Legacy and sends `resets_at` / `retry_after` / `scope`;
  this unit renders those only when PRESENT. S81-12 LEGAL-V3: owns the consent copy and the
  `AI_CONSENT_VERSION` value (this unit sends whatever the constant holds). S81-11 HONEST-FRAGRANCE-UI:
  same OTA; owns the as-of date rendering (see D7 / Q3). SF1 / CL3: later consumers of the
  compare request id (this unit only generates and exposes it).
- Personal-data rule: the repo is public. No real name, email, phone, Apple ID, device id, IDFV,
  ANDROID_ID, address or account id in any file, fixture or log line. Every id, hash and UUID in the
  tests is synthetic and built at run time (`'a'.repeat(64)`, `require('crypto').createHash('sha256')`
  over a synthetic string, `randomUUID` from node for v4 shapes). No credential-shaped literal.
- Measurement location: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/S81-08/`.

-----------------------------------------------------------------------------------------------------

## 0. What the unit does

1. Every request to our backend through the axios instance (which includes every metered request
   and `/api/v1/usage/status`), BOTH camera raw-fetch attempts (`/api/v1/image/identify` and its U13c
   401 retry) and the SSE request carry the request-context headers S81-05 parses:
   `X-Device-Fingerprint` (the new stable device id hash), `X-Device-Fingerprint-Legacy` (today's
   composition, for a dated transition window, ruling R-S05-1), `X-AI-Consent-Version`
   (`String(AI_CONSENT_VERSION)` only when a current consent record exists, else omitted) and, on
   compare attempts, `X-Compare-Request-Id` (a fresh lower-case uuid4 per attempt, shared by that
   attempt's SSE and REST requests and by both camera attempts, exposed to the caller for SF1 / CL3).
2. The device id stops hashing `Device.osBuildId` (which changes on OS updates, A7 / R5): it becomes
   the SHA-256 hex of a SecureStore UUID generated once per install (the existing `device_fp_nonce`
   item), with IDFV (iOS) / ANDROID_ID (Android) as the fallback when SecureStore is unavailable. The
   legacy composition survives only behind `legacyDeviceFingerprintHash()` for the transition header.
3. The AI-consent record is kept per account (as today) AND mirrored under one device-scoped key,
   so a second account on the same device is not re-asked for the same version (owner decision 2,
   the one device rule) while a version bump still re-asks everyone.
4. The usage pill on Home and the limit sheet (PaywallScreen) render the exact local reset time when
   the server sends `resets_at` on `/usage/status` or `resets_at` / `retry_after_seconds` /
   `retry_after` on the USAGE_LIMIT 429; when absent, both render today's tree and copy byte for byte.
   Three EN + AR keys are added (parity, copy policy, Arabic-first, every AR string [NATIVE READ]).

Nothing on the server changes; no response the build-3 client reads changes; the unit adds request
headers the base server ignores (S81-05 is dark and not merged at base).

-----------------------------------------------------------------------------------------------------

## 1. Base state (measured at dfc6502f)

All client paths relative to `SmartCompareApp/`. Every working-copy file is CRLF (`core.autocrlf=true`;
measured: CR count == line count for every file below); line numbers are LF line numbers of the
working copy (identical to `git show dfc6502f:`).

### 1.1 Where requests leave the device today (the header sites)

| Site | file:line | Measured fact |
|---|---|---|
| axios instance | src/services/api.ts:29-32 | `axios.create({ baseURL: API_BASE_URL, timeout: 120000 })`. |
| request interceptor | src/services/api.ts:54-69 | lazily `require('./authService').getToken()`; sets ONLY `config.headers.Authorization = 'Bearer <token>'` when a token exists; returns config; no other header anywhere. |
| response interceptor (401 retry) | src/services/api.ts:208-250 | on 401 (not auth-flow URLs, not `_retry`) refreshes through `getOrStartRefresh()`, sets `originalRequest.headers.Authorization`, re-enters `api(originalRequest)` (the request interceptor runs again on the SAME config object). |
| camera first attempt | src/services/api.ts:282-309 | raw `fetch(identifyUrl, { method: 'POST', body: formData, headers, signal })`; `headers` = `{}` or `{ Authorization }` (:286-289). |
| camera 401 retry (U13c) | src/services/api.ts:317-331 | on 401 reads the body, waits `waitForIdentifyRefresh`, retries with `headers: { Authorization: 'Bearer <refreshed>' }` ONLY (:325): every other header of attempt 1 is dropped today. |
| REST compare (default transport) | src/services/api.ts:677-709 | `api.get('/api/v1/text/compare', { params, signal, timeout: COMPARE_TIMEOUT_MS })`; params = q or product_a/product_b + region + optional selected_category / nocache / lang. |
| SSE (flag `ENABLE_EXPO_FETCH_SSE`, default off) | src/services/api.ts:820-846 | `headers = { Accept: 'text/event-stream' }` + Authorization; `require('expo/fetch').fetch(url, { method: 'GET', headers, signal })`; on failure falls back to exactly one `runRestCompare()` (:943). |
| streamComparison return | src/services/api.ts:646-652, :948 | returns `{ subscribe, abort }` only. |
| compareTextPair (0 callers, W4-14 ruling R1) | src/services/api.ts:961-979 | `api.post('/api/v1/text/compare', body, { timeout })`. |
| Link mode | src/screens/HomeScreen.tsx:560-572 | `api.post('/api/v1/url/compare', {...}, { timeout: COMPARE_TIMEOUT_MS, signal })`. |
| /usage/status | src/services/usageService.ts:43-50 | `api.get('/api/v1/usage/status')` (axios, so the interceptor applies). |
| register | src/services/authService.ts:136-155 | `getDeviceFingerprint()` in its own try; `api.post('/api/v1/auth/register', body, fingerprint ? { headers: { 'X-Device-Fingerprint': fingerprint } } : undefined)`. |
| Google social sign-in | src/services/authService.ts:977-999 | fingerprint read AFTER the native sheet (W3-3 C6), raw `fetchWithDeadline(.../auth/social-login, { headers: { 'Content-Type', ...X-Device-Fingerprint } })`. |
| Apple social sign-in | src/services/authService.ts:1140-1161 | same shape as Google. |
| share (body, not header) | src/components/ShareBottomSheet.tsx:158-170 | `fp = deviceFingerprintHash prop ?? await getDeviceFingerprint()`; `createShare({ ..., device_fingerprint_hash: fp })`. |
| other axios callers | ContactUsScreen.tsx:91, EditProfileScreen.tsx:140, LegalScreen.tsx:79, pushTokenService.ts:94, referralService.ts:108/117/133/154, authService.ts:206/324/497/808/831 | all through `api` (the interceptor applies). |

Measured conclusion (matches A7 / R5 / R-S05-7): X-Device-Fingerprint rides only register and the two
social sign-ins (header) and share (body); no compare, camera, SSE or usage request carries any
context header; no X-Compare-Request-Id or X-AI-Consent-Version exists anywhere in `src/`.

### 1.2 The device fingerprint today (src/services/deviceFingerprint.ts, 57 lines)

| What | Line | Fact |
|---|---|---|
| imports | 7-10 | expo-application, expo-device, expo-secure-store, expo-crypto. |
| nonce key | 12 | `NONCE_KEY = 'device_fp_nonce'`. |
| cache | 14-15, 18-19 | module `cached` + `inflight` (concurrent calls coalesce). |
| nonce | 22-26 | `SecureStore.getItemAsync(NONCE_KEY)`; if absent `Crypto.randomUUID()` then `SecureStore.setItemAsync`. |
| composition | 27-31 | `[Application.applicationId ?? '', Device.osBuildId ?? Device.osInternalBuildId ?? '', nonce].join('|')`. |
| hash | 32-35 | `Crypto.digestStringAsync(SHA256, raw)` (lower-case hex). |
| failure | 39-50 | W3-3 C5: `.catch` clears `inflight` and rethrows (no poisoned promise). |
| test hook | 54-57 | `_resetCacheForTests()`. |

The nonce IS already a SecureStore UUID generated once per install (Keychain on iOS: usually survives
a reinstall; Android: reset on uninstall; A7 finding 12). Only `osBuildId` makes today's value change
on an OS update. `expo-application` exposes `getIosIdForVendorAsync(): Promise<string | null>` and
`getAndroidId(): string` (node_modules/expo-application/build/Application.d.ts:50, :84; package
`expo-application ~7.0.8` is a direct dependency, package.json:27, lock 7.0.8, already in build 3).

### 1.3 The consent record today (src/services/aiConsent.ts, 271 lines)

| What | Line | Fact |
|---|---|---|
| version | 46 | `export const AI_CONSENT_VERSION = 2`. |
| key | 48, 55-57 | `@qaren_ai_consent_<userId>`. |
| record | 50-53 | `{ version: unknown; at: string }`. |
| read | 60-71 | null user -> null; JSON parse; requires `typeof at === 'string'`; returns `{ version, at }` only. |
| current | 74-77 | `record !== null && record.version === AI_CONSENT_VERSION`. |
| record | 80-88 | null user persists nothing (ruling R3); storage failure swallowed. |
| clear | 91-98 | removes the account key (caller: EditProfileScreen.tsx:143 on account deletion). |
| user | 100-107 | `getSavedUser()` (authService) -> id or null. |
| gate | 114-120 | `ensureAiConsent(ask)`. |
| imports | 40-43 | react, react-native Platform, AsyncStorage, `getSavedUser` from './authService' (static). |

Cycle fact: aiConsent -> authService (static) and authService -> api (static, authService.ts:55);
api.ts reaches authService only through lazy `require()` (api.ts:58, :284, :821). Any new module that
api.ts imports statically must therefore reach aiConsent / authService lazily.

`__tests__/setup.ts:18-39` globally mocks `../src/services/aiConsent` (AI_CONSENT_VERSION 2,
`hasCurrentAiConsent` -> true, `readAiConsent` -> null, ...); only the consent suites map it back.

### 1.4 The usage pill, the limit sheet and the 429 shape

| What | file:line | Fact |
|---|---|---|
| UsageStatus type | src/services/usageService.ts:8-30 | tier, used{daily,monthly,lifetime}, limits{daily,monthly,lifetime_free,monthly_base?,monthly_bonus?}, remaining{daily,monthly,lifetime_free?}. No reset field. |
| UsageLimitError | src/services/usageService.ts:32-41 | code, tier, reason, remaining. |
| 429 payload reader | src/services/usageService.ts:59-73 | `detail.code === 'USAGE_LIMIT'` -> detail, top-level `code` -> data. |
| hook | src/hooks/useComparisonCounter.ts:8-91 | hydrates `getUsageStatus()` once on mount (:17-39), returns `{ used, total, canCompare, shouldShowPaywall, increment }` (:91). `status` is internal. |
| pill | src/screens/HomeScreen.tsx:138, :938-1000 | `baseFreeRemaining = max(0, total - used)`; `<TouchableOpacity testID="home-header-counter">`, a11y `t('home.headerCounter.a11y', {free,total,bonus})` (:962-966), text `{baseFreeRemaining}/{total} {t('home.headerCounter.free')}` (:978), optional `+bonus`. |
| sheet state | src/screens/PaywallScreen.tsx:37-71 | `stateFromStatus` (monthly wins, then daily, else open) / `stateFromInitial` (reason, error suffix, remaining). |
| sheet copy | src/screens/PaywallScreen.tsx:100-126, :161-165 | daily -> `paywall.limit.resets_daily`, monthly -> `resets_monthly`, open -> no resets line, unknown -> `resets_unknown`; rendered in `testID="paywall-resets"`. |
| Paywall params | src/types/types.ts:617-625 | `initialUsage?: { tier?, reason?, error?, code?, remaining? }`. |
| EN copy | src/i18n/en.json:380, :382, :711 | resets_daily "Your free comparisons refresh every day.", resets_unknown "Free comparisons refresh every day and every month.", a11y "{{free}} of {{total}} free comparisons, plus {{bonus}} bonus". |
| AR copy | src/i18n/ar.json:377, :379, :708 | the AR twins (non-ASCII; see 2.7 for code points). |
| catalogs | src/i18n/{en,ar}.json | FLAT keys (dotted strings), 1,010 keys each, sets equal (measured). |

429 on the wire at base (app/middleware/error_handler.py:127-170): a structured detail is flattened to
`{ success: false, error, code, request_id }`; `tier` / `remaining` are dropped; a detail `retry_after`
that is a positive int becomes the top-level `retry_after_seconds` plus a `Retry-After` header
(`_detail_retry_after`, :110-125). The USAGE_LIMIT raise (app/api/text_routes.py:619-628) carries no
`retry_after` today. So: when S81-09 adds `retry_after` to the USAGE_LIMIT detail, the client sees
`retry_after_seconds`; `resets_at` reaches the wire only through S81-09's allow-list. The camera path
(api.ts:341-358) throws `err.detail = <parsed body>`; ResultsScreen.tsx:362 passes it as `initialUsage`.

### 1.5 Backend facts this unit must satisfy (read, never changed)

| Fact | Source | Value |
|---|---|---|
| header names | S81-05 leaf `git show e9fd7148:app/utils/request_context.py`:72-74 | `x-ai-consent-version`, `x-device-fingerprint`, `x-compare-request-id` (the first occurrence decides). |
| fingerprint shape | same :89 and app/api/auth_routes.py:35 (base) | `^[a-f0-9]{64}$` (lower-case hex only). |
| consent shape | same :92, :121-125 | 1-3 ASCII digits -> int; else None. |
| request id shape | same :135-152 | canonical hyphenated uuid4, any case, normalised to lower case (R-S05-2); S81-08 sends lower case. |
| state | same :81-83, GATE_S81_05 GC-2 | absent / malformed / ok; an EMPTY header value is malformed, so a header is never sent with an empty value. |
| legacy header | RULINGS_S81_05 R-S05-1 | `X-Device-Fingerprint-Legacy`, same 64-hex shape, S81-08's contract; S81-05 does not parse it. |
| register read | app/api/auth_routes.py:478-496 (`_read_valid_device_fingerprint`, header read at :489), :515-537 (match on `users.device_fingerprint_hash`), :540-579 (social, behind `ENABLE_SOCIAL_DEVICE_FINGERPRINT`) | the server stores the VALUE verbatim and matches it against stored rows. |
| /usage/status | app/api/usage_routes.py:9-15, app/services/usage_service.py:712-758 | keys tier / used / limits / remaining only; no `resets_at` at base. |

### 1.6 Libraries and native modules (all already linked in build 3)

expo-secure-store 15.0.8, expo-crypto 15.0.9 (`randomUUID(): string`, `digestStringAsync`), expo-application
7.0.8, expo-device 8.0.10, @react-native-async-storage/async-storage (lock), axios (lock), i18next.
`Crypto.randomUUID()` on iOS returns UPPER-case hex (NSUUID), hence the lower-casing. No new dependency.

### 1.7 Test-harness facts the RED/GREEN must respect

- jest.config.js `testMatch` `**/__tests__/**/*.test.ts(x)`, preset ts-jest, `setupFilesAfterEnv` setup.ts.
- moduleNameMapper maps expo-application, expo-device, expo-crypto, expo-secure-store and AsyncStorage
  to root shims in `__mocks__/`: `expo-application.ts` exports applicationId only (no IDFV / ANDROID_ID
  functions), `expo-device.ts` exports osBuildId 'TEST-BUILD-ID', `expo-crypto.ts` exports a COUNTER
  `randomUUID` ('00000000-0000-0000-0000-<n>', not a valid v4) and NO `digestStringAsync`,
  `expo-secure-store.ts` is an in-memory store, `async-storage.ts` exposes `_store`. So, in every
  existing suite that does not mock them, `getDeviceFingerprint()` rejects (no digest) and every new
  header builder must treat a rejection as "omit the header". New suites mock these with plain
  `jest.mock(name, factory)` (installed or mapped modules: never `{ virtual: true }`).
- axios is mocked in the api.* suites with `interceptors.request.use: jest.fn()` (e.g.
  `__tests__/api.outputLang.w414.test.ts:31-43`), so the interceptor never runs there and the
  interceptor function is reachable as `instance.interceptors.request.use.mock.calls[0][0]`.
- `__tests__/api.cameraAuthRetry.u13c.test.ts` drives the real `identifyFromImages` with a mocked
  global fetch and asserts EXACT header objects (see 4.1).

### 1.8 Guards the new code must not trip

i18n parity (en/ar key sets equal: `__tests__/consent/aiConsentV2.s75.test.ts:194` and the i18n
suites), `__tests__/copy-policy.test.ts` (banned_en / banned_ar / scary_vocab_* in
`src/i18n/.copy-policy.json`: "couldn't", "try again", "Failed to" and the four AR terms), the digit
policy `__tests__/i18n/digitPolicy.w311.test.ts` (ASCII digits in AR, `APP_DIGIT_SYSTEM = 'latn'`),
`__tests__/i18n/no-missing-referenced-keys.test.ts`, the brand fence `__tests__/i18n/brand.myez.s69.test.ts`,
the paywall honesty fence `__tests__/screens/paywall.noSubscriptionUi.s69.test.ts` (EXACT `paywall.*`
key set, no "tomorrow", no Arabic-Indic digits, none of its `AR_DISHONEST` patterns incl. the AR
"tomorrow" word U+063A U+062F U+0627), the consent sha fence
`__tests__/consent/aiConsentVersion.s69.test.ts` (copy + version; untouched), the AI dispatch fence
`__tests__/consent/aiDispatchFence.s69.test.ts`, `__tests__/config/nativeBundle.w37.test.ts` (native
config; 4 drift nodes red at base), and the backend client-scanning tests (7.3). Every new code line is
ASCII; AR values are the only non-ASCII additions.

### 1.9 Line endings

Every touched client file is CRLF in the working copy and LF in the index; the Edit tool preserves
CRLF. New files are written LF (git normalises). `git diff --stat` must show hunks, never a whole-file
rewrite of an existing file.

### 1.10 Base pass state of the files the unit touches or pins (measured)

One jest process, 48 suites (`base_set.txt` in the notes folder: the 17 `api.*` suites, the 5
consent suites, the 10 i18n suites, deviceFingerprint, socialFingerprint.w3-3, ShareBottomSheet.w3-3,
useComparisonCounter, LimitReachedSheet.s69, paywall.noSubscriptionUi.s69, honestCounts.s69,
ResultsScreen.usageFetch.a15, copy-policy, nativeBundle.w37, authService.consent.w3-16,
shareTruth.s74, HomeScreen.rateLimitedSeconds.w314, authService.m18, appleAuthCode.b3a,
googleButton.b3a):

`[jest] tag=s08-base-set start=1792762296 end=1792762452 rc=1 elapsed=156s` -> 48 suites (47 passed,
1 failed), 458 tests: 454 passed, 4 failed = exactly the four nativeBundle.w37 drift nodes (d5
gesture-handler, k2, k4, k5). Per suite (passed/failed): deviceFingerprint 6/0,
api.cameraAuthRetry.u13c 20/0, api.outputLang.w414 6/0, api.refreshInterceptor 15/0,
api.streamComparison.expoFetch 3/0, consent/aiProcessingConsent.s69 26/0, consent/aiConsentV2.s75 10/0,
consent/aiConsentVersion.s69 1/0, authService.socialFingerprint.w3-3 9/0,
ShareBottomSheet.deviceFingerprint.w3-3 3/0, hooks/useComparisonCounter 12/0,
screens/LimitReachedSheet.s69 28/0, screens/paywall.noSubscriptionUi.s69 12/0, honestCounts.s69 14/0,
copy-policy 5/0, config/nativeBundle.w37 54/4 (full list in `base_set_counts.txt`).

Backend client-scanning + CLAUDE.md-reader set (25 files, 7.3), bounded runner at base:
`[pyt] tag=s08-be-base start=2026-10-23 16:36:47 end=2026-10-23 16:40:16 elapsed=209s bound=1200s
status=OK rc=0` -> 1899 passed, 4 deselected, 0 failed; `[netguard] blocked 41 attempt(s) from 31
node(s)` (sentinel / egress lines only, the existing baseline class); no `[hermeticity]` line.

FULL jest suite: NOT MEASURED here (a plain probe took over 120 s while the 48-suite run was live: the
box was in the slow-spawn state). Cited from the ledger / brief, unmeasured in this run: 3,694 passed
with only the four nativeBundle.w37 drift nodes red. GREEN measures it once at base and at head.

-----------------------------------------------------------------------------------------------------

## 2. Contract

### 2.1 Headers and shapes (every value lower-case ASCII; a header is OMITTED, never sent empty)

| Header | Value | When sent | Server contract |
|---|---|---|---|
| X-Device-Fingerprint | `getDeviceFingerprint()` = SHA-256 hex of the stable id (2.3) | every axios request, both camera attempts, the SSE request; register keeps its explicit value (the same function) | 64 lower-case hex (S81-05 / auth_routes:35) |
| X-Device-Fingerprint-Legacy | `legacyDeviceFingerprintHash()` = today's composition byte for byte | wherever X-Device-Fingerprint is sent AND `Date.now() < LEGACY_FINGERPRINT_HEADER_UNTIL_MS`; also both social sign-ins | 64 lower-case hex (R-S05-1) |
| X-AI-Consent-Version | `String(AI_CONSENT_VERSION)` ("2" at base) | only when `hasCurrentAiConsent(savedUserId)` is true (account record OR verified device mirror of the CURRENT version) | 1-3 ASCII digits |
| X-Compare-Request-Id | `newCompareRequestId()` = `Crypto.randomUUID().toLowerCase()` if it matches `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`, else no header | compare attempts only: streamComparison (SSE + its REST fallback, ONE id), identifyFromImages (both attempts, ONE id), and any axios request to `/api/v1/text/compare`, `/api/v1/url/compare`, `/api/v1/text/quick` that does not already carry one | canonical uuid4 (R-S05-2) |
| X-Client-Capabilities | comma-joined `CLIENT_CAPABILITIES` | never while the list is empty (shipped empty, D7) | S81-18 |

Rule of precedence (D6): a context header already present on the request config (any letter case of
the name) is never overwritten; the interceptor only fills absent names. Authorization handling stays
exactly as today.

### 2.2 New and changed symbols (types)

- `src/services/deviceFingerprint.ts`:
  `getDeviceFingerprint(): Promise<string>` (NEW semantics, same name and signature);
  `legacyDeviceFingerprintHash(): Promise<string>` (today's body); `LEGACY_FINGERPRINT_HEADER_UNTIL_MS:
  number` (= `Date.UTC(2027, 2, 31, 21, 0, 0)` = 2027-04-01 00:00 Asia/Riyadh, Q2);
  `legacyFingerprintHeaderActive(nowMs?: number): boolean`; `_resetCacheForTests()` resets both caches.
- `src/services/requestContext.ts` (NEW, imports deviceFingerprint and expo-crypto statically, reaches
  authService / aiConsent by lazy `require`): `CLIENT_CAPABILITIES: readonly string[]` (= `[]`);
  `COMPARE_REQUEST_PATHS: readonly string[]`; `newCompareRequestId(): string | null`;
  `buildContextHeaders(opts?: { compareRequestId?: string | null }): Promise<Record<string, string>>`
  (never rejects); `applyContextHeaders(config): Promise<config>` (the interceptor half; never rejects).
- `src/services/aiConsent.ts`: `AI_CONSENT_DEVICE_KEY = '@qaren_device_ai_consent'` (outside the
  `@qaren_ai_consent_` prefix, so no user id can collide and `T1.4`'s prefix filter is unaffected);
  `AiConsentRecord` stays `{ version, at }`; the stored JSON gains an optional `deviceId: string`.
- `src/services/api.ts`: `streamComparison(...)` returns `{ subscribe, abort, compareRequestId: string |
  null }` (additive).
- `src/utils/resetTime.ts` (NEW, pure): `resolveResetAt(src: { resets_at?: unknown;
  retry_after_seconds?: unknown; retry_after?: unknown } | null | undefined, nowMs: number): Date | null`;
  `formatResetClock(at: Date, offsetMinutes?: number): string` (`'HH:MM'`, 24 h, ASCII digits; default
  offset `-at.getTimezoneOffset()`, the device-local clock).
- `src/services/usageService.ts`: `UsageStatus.resets_at?: string`; `UsageLimitError` gains optional
  `resets_at?: string; retry_after_seconds?: number; retry_after?: number` (types only).
- `src/types/types.ts` Paywall `initialUsage` gains the same three optional fields.
- `src/hooks/useComparisonCounter.ts`: returns additive `resetsAt: string | null` (`status.resets_at`
  when a string, else null).
- i18n (both catalogs): `home.headerCounter.resets`, `home.headerCounter.a11yResets`,
  `paywall.limit.resets_at` (2.7).

### 2.3 Device id (D2)

`getDeviceFingerprint()`: read `device_fp_nonce` from SecureStore (generate with `Crypto.randomUUID()`
and `setItemAsync` when absent, exactly as today); hash `stableId.trim().toLowerCase()` with SHA-256;
cache per process; coalesce concurrent calls; never read `Device.osBuildId` / `osInternalBuildId` /
`Application.applicationId`. When the SecureStore read or write THROWS: fallback = iOS
`Application.getIosIdForVendorAsync()` (non-empty string), Android `Application.getAndroidId()`
(non-empty string), each guarded with `typeof fn === 'function'`; the fallback value is hashed the same
way, NOT cached (the next call retries SecureStore) and NEVER persisted anywhere (no AsyncStorage, no
SecureStore write of a fallback). No fallback value -> reject (callers omit the header), with the
W3-3 C5 inflight reset kept. One SecureStore read of the nonce serves both the new and the legacy hash
(a shared in-process nonce memo; the two hashes have separate caches).

`legacyDeviceFingerprintHash()`: today's lines 21-50 byte for byte (same nonce key, same `|` join of
applicationId, `osBuildId ?? osInternalBuildId ?? ''`, the nonce as stored, no lower-casing), its own
cache and inflight; called only while `legacyFingerprintHeaderActive()`.

### 2.4 Legacy window (D3)

`legacyFingerprintHeaderActive(nowMs = Date.now())` = `nowMs < LEGACY_FINGERPRINT_HEADER_UNTIL_MS`.
After the cutoff no code path calls `legacyDeviceFingerprintHash()` (no osBuildId read at all). A later
OTA deletes the legacy function, the constant and the header (out of scope).

### 2.5 Consent record (D8)

- `recordAiConsent(userId)`: null user -> persist nothing (R3 kept). Else write the account key
  `{ version, at, deviceId? }` and, when `getDeviceFingerprint()` resolved, ALSO the device key
  `{ version, at, deviceId }`. A rejected device id writes the account record without `deviceId` and
  no device key. Storage failures stay swallowed.
- `hasCurrentAiConsent(userId)` = account record current (today) OR (device record
  `version === AI_CONSENT_VERSION` AND `deviceId === await getDeviceFingerprint()`); any failure reading
  the device id or the device key -> that branch is false. A version bump re-asks everyone (both
  records must carry the new version).
- `readAiConsent` keeps returning exactly `{ version, at }`.
- `clearAiConsent(userId)` (account deletion) removes the account key only; the device key holds no
  account identifier and stays (Q5).
- The consent copy, `AI_CONSENT_VERSION` and the sha fence are untouched (S81-12 owns them).

### 2.6 Compare request id (D5)

One id per compare ATTEMPT: `streamComparison(input, options)` calls `newCompareRequestId()` once at
call time; `subscribe()` sends it on the SSE request and on the single REST compare (default transport
or fallback) via `config.headers['X-Compare-Request-Id']`; the returned object exposes it as
`compareRequestId`. `identifyFromImages` mints one id per call and sends it on both attempts. Link mode
and compareTextPair get theirs from the interceptor (compare path, absent header). The axios 401 retry
re-enters the interceptor with the original config, so the id survives (only-if-absent).

### 2.7 Reset time rendering (D9)

`resolveResetAt(src, nowMs)`: (1) `resets_at` string with a finite `Date.parse` strictly after `nowMs`
and at most 48 h after it -> that Date; else (2) `retry_after_seconds`, else (3) `retry_after`: a
number that is an integer, `> 0` and `<= 172800` (not a bool, not a string) -> `new Date(nowMs + s *
1000)`; else null. `formatResetClock(at, offset)`: `HH:MM` of `at` shifted by `offset` minutes, both
zero-padded, ASCII digits, 24-hour clock.

PaywallScreen: `resetAt = resolveResetAt(fetchedStatus) ?? resolveResetAt(initialUsage)` (the fetched
`/usage/status` decides first, like the state). If `resetAt` is non-null and the state is `daily`,
`open` or `unknown`, the `paywall-resets` line is `t('paywall.limit.resets_at', { time })`; `monthly`
keeps `paywall.limit.resets_monthly` (a daily reset time must never be shown for a monthly limit);
when `resetAt` is null every state renders today's line (or none for `open`) byte for byte.

Home pill: `resetsAt` from the hook -> `resolveResetAt({ resets_at: resetsAt }, Date.now())`; when
non-null, ONE extra `<Text testID="home-header-counter-resets">{t('home.headerCounter.resets', { time })}</Text>`
after the bonus block, and the a11y label switches to `home.headerCounter.a11yResets` (free, total,
bonus, time); when null the tree and the a11y label are today's.

Copy (EN; AR given as code points because this spec is pure ASCII; every AR string [NATIVE READ]):
- `paywall.limit.resets_at`: EN "Your free comparisons refresh at {{time}}." AR = the base AR
  `paywall.limit.resets_daily` with its last two words (U+0643 U+0644, U+064A U+0648 U+0645 ".")
  replaced by U+0627 U+0644 U+0633 U+0627 U+0639 U+0629 " {{time}}.", i.e.
  U+062A U+062A U+062C U+062F U+062F _ U+0645 U+0642 U+0627 U+0631 U+0646 U+0627 U+062A U+0643 _
  U+0627 U+0644 U+0645 U+062C U+0627 U+0646 U+064A U+0629 _ U+0627 U+0644 U+0633 U+0627 U+0639 U+0629 _ {{time}} .
- `home.headerCounter.resets`: EN "resets {{time}}" AR U+062A U+062A U+062C U+062F U+062F _ {{time}}.
- `home.headerCounter.a11yResets`: EN "{{free}} of {{total}} free comparisons, plus {{bonus}} bonus. They refresh at {{time}}"
  AR = the base AR `home.headerCounter.a11y` + U+060C _ U+0648 U+062A U+062A U+062C U+062F U+062F _
  U+0627 U+0644 U+0633 U+0627 U+0639 U+0629 _ {{time}}.
(`_` = one ASCII space.) No value contains a digit, "tomorrow", "today", a banned or scary term.

### 2.8 Capabilities (D7)

`CLIENT_CAPABILITIES = []` ships empty; `buildContextHeaders` adds `X-Client-Capabilities` only for a
non-empty list. Reason: PLAN_S81:173 lists `price_asof`, but S81-18 serves past-TTL prices only to
clients that send it, and the as-of date rendering is S81-11 (D20); announcing the capability before
the rendering exists would let a past-TTL price render without its date. S81-11 appends 'price_asof' in
the PR that renders the date (Q3).

### 2.9 Failure table

| Failure | Behaviour |
|---|---|
| SecureStore read/write throws | fallback IDFV / ANDROID_ID hash, not cached, not persisted; none -> device headers omitted |
| `digestStringAsync` / expo-crypto missing or throws | that header omitted |
| legacy hash throws | legacy header omitted; the new one still sent |
| `getSavedUser` / AsyncStorage throws | consent header omitted |
| `randomUUID` throws or returns a non-v4 | no X-Compare-Request-Id (never a made-up id) |
| any builder throws | the interceptor still returns the config with Authorization as today; the camera / SSE request still goes out |
| `resets_at` unparseable, past, > 48 h ahead, non-string | ignored (today's copy) |
| `retry_after*` 0, negative, non-integer, bool, string, NaN, Infinity, > 172800 | ignored |
| status / 429 carries a reset but the state is monthly | today's monthly copy |

No header value, id or hash is ever logged (`console.*`, Sentry breadcrumb) by this unit.

### 2.10 Identity invariant (the main invariant; build-3 compatibility)

The unit has no flag, so its invariant is: (a) the server contract is unchanged (request bodies,
query params, URL, method and signal of every request are byte-identical; only request headers are
added; no response is read differently except the optional reset fields); (b) with no reset field on
the wire (today's server, S81-09 unbuilt) the pill and the sheet render today's tree and copy byte for
byte; (c) the legacy hash equals today's `getDeviceFingerprint()` output byte for byte on the same
SecureStore state, so S81-09 / the register path can match every stored row; (d) a header builder can
never block, delay past its own awaits, or fail a request. PIN rows run with the FULL configuration
present (every expo module mocked, consent record planted, device id resolvable, legacy window open)
plus call recorders, so a "not gated" mutant is killable (B1 rule).

### 2.11 Test seams (production values in brackets)

`Date.now` via `jest.spyOn` [system clock]; `LEGACY_FINGERPRINT_HEADER_UNTIL_MS` read at call time
[2027-03-31T21:00:00Z]; `formatResetClock(at, offsetMinutes)` [`-at.getTimezoneOffset()`];
`Platform.OS` on the root react-native mock [device OS]; `_resetCacheForTests()` [none]; expo module
factories per suite [native modules]; `instance.interceptors.request.use.mock.calls[0][0]` [the
registered interceptor]; `features._setExpoFetchSseForTests` [ENABLE_EXPO_FETCH_SSE false].

-----------------------------------------------------------------------------------------------------

## 3. Change list (the order GREEN applies it)

0. Byte copies (Python `shutil.copyfile` + sha256) of every file below before the first edit, into the
   notes folder; mutation lock `<worktree>/.qa-mutation.lock` for the mutation phase only.
1. `src/services/deviceFingerprint.ts`: new `getDeviceFingerprint` (2.3), `legacyDeviceFingerprintHash`
   (today's body), the shared nonce memo, the fallback, `LEGACY_FINGERPRINT_HEADER_UNTIL_MS`,
   `legacyFingerprintHeaderActive`, `_resetCacheForTests` resetting all caches; correct the stale
   header comment ("resets on uninstall" is wrong for iOS, A7 finding 12).
2. `src/services/requestContext.ts` (new, LF): 2.2 / 2.1 / 2.6 / 2.8.
3. `src/services/aiConsent.ts`: 2.5 (static import of deviceFingerprint is safe: it imports only expo
   modules).
4. `src/services/api.ts`: the request interceptor awaits `applyContextHeaders(config)` after the
   Authorization line (inside its own try; never rejects); `identifyFromImages` builds
   `ctx = await buildContextHeaders({ compareRequestId: newCompareRequestId() })` once and sends
   `{ ...ctx, Authorization? }` on attempt 1 and `{ ...ctx, Authorization: 'Bearer <new>' }` on the
   retry; `streamComparison` mints the id, sends it on SSE (`{ Accept, Authorization?, ...ctx }`) and in
   the REST config `headers`, returns `compareRequestId`. Nothing else in api.ts.
5. `src/services/authService.ts`: both social sign-ins read `legacyDeviceFingerprintHash()` in its own
   try, right after the existing `getDeviceFingerprint()` read (after the native sheet, C6), only while
   `legacyFingerprintHeaderActive()`, and spread `X-Device-Fingerprint-Legacy` beside
   `X-Device-Fingerprint`. register is NOT edited (its explicit X-Device-Fingerprint already calls
   `getDeviceFingerprint()`; the interceptor adds the legacy and consent headers).
6. `src/utils/resetTime.ts` (new, LF): 2.7 helpers.
7. `src/services/usageService.ts`, `src/types/types.ts`: the optional type fields (2.2).
8. `src/hooks/useComparisonCounter.ts`: additive `resetsAt` in the return object.
9. `src/screens/PaywallScreen.tsx`: 2.7 sheet rule (state logic untouched).
10. `src/screens/HomeScreen.tsx`: 2.7 pill rule (the 938-1000 block only).
11. `src/i18n/en.json`, `src/i18n/ar.json`: the three keys each (append beside their families; parity).
12. Deliberate pin changes 4.1 (test files only).
13. RED files under `__tests__/s81_08/` (section 5), unchanged by GREEN except hygiene a gate names.
14. `CLAUDE.md`: section 8 text.
No other file. Explicitly NOT touched: app.json, eas.json, package.json, package-lock.json,
`__tests__/setup.ts`, every `__mocks__/` shim, `src/components/ShareBottomSheet.tsx` (the body now
carries the new value through the unchanged `getDeviceFingerprint()` call, D1), every backend file.

-----------------------------------------------------------------------------------------------------

## 4. Existing pins

### 4.1 Pins that change deliberately (each predicted from the measured asserts; RED measures the exact red set on the prototype and lists any extra node for a ruling)

| # | Node | Why it moves | New assertion |
|---|---|---|---|
| E1 | `__tests__/deviceFingerprint.test.ts` > "hashes applicationId|osBuildId|nonce in that order via SHA-256" (:80-90) | the new id hashes the lower-cased nonce only | the new composition (`digest('SHA256', 'persisted-nonce')`), plus the same assertion moved onto `legacyDeviceFingerprintHash()` verbatim |
| E2 | `__tests__/deviceFingerprint.test.ts` > "retries after a transient SecureStore failure instead of replaying the rejection" (:120-133) | the first call now takes the IDFV fallback (root mock has none -> still rejects) and the second resolves to the NEW hash | expected value `hash(nonce-ok)`; the rejection-not-replayed property kept (getItemAsync called twice) |
| E3 (predicted, possibly no change) | `__tests__/api.cameraAuthRetry.u13c.test.ts` T1 (:333), T9 (:486), T17b (:583, :586), T19 (:599), T17a (:725-726) | exact `toEqual({ Authorization })` / `toEqual({})` header objects; both attempts now carry every context header that RESOLVES in that suite | if any node reddens: assert `Authorization` exactly as today AND that attempt 2's non-Authorization headers equal attempt 1's (`omit(h, 'Authorization')` equality); T17a: attempt-1 headers carry no Authorization without a token |
| E4 | `__tests__/screens/paywall.noSubscriptionUi.s69.test.ts` T2-c1 / T2-c2 (:125-131) | `PAYWALL_ALLOW` pins the EXACT `paywall.*` key set | add `'paywall.limit.resets_at'` to `PAYWALL_ALLOW` (one line); the fence's no-promise / no-"tomorrow" / digit checks then cover the new key |

Note on E3 (measured mock shapes, predicted outcome): that suite does not mock expo-crypto, so the
root shim applies: its `randomUUID` returns a non-v4 counter ('00000000-0000-0000-0000-<n>'), so
`newCompareRequestId()` yields null and no id header is added, and it has no `digestStringAsync`, so
no device header is added; it mocks authService with `getToken` / `refreshSession` / `clearSession`
only (:43-47), so `getSavedUser` is undefined, the consent read throws inside its try and the consent
header is omitted. The prototype may therefore show all six E3 nodes STAYING GREEN; RED reports which
nodes actually redden and GREEN re-pins only those (a no-change E3 row is recorded as such).

### 4.2 Pins that must stay green and unedited

- `__tests__/authService.socialFingerprint.w3-3.test.ts` (9 nodes; incl. the register pin :239-255
  `toEqual({ headers: { 'X-Device-Fingerprint': FP } })`, kept because register is not edited, and the
  C6 "cancelled sign-in never reads the fingerprint" pins, which now also cover the legacy read
  placement).
- `__tests__/ShareBottomSheet.deviceFingerprint.w3-3.test.tsx` (3), `__tests__/clientTruth/shareTruth.s74.test.tsx` (10).
- `__tests__/consent/aiProcessingConsent.s69.test.tsx` (26; T1.4's prefix filter and T1.7 "per account"
  stay green because the device key is outside the prefix and T1.7 plants no device key; T1.8 no-user
  persists nothing), `aiConsentV2.s75` (10), `aiConsentVersion.s69` (1, the sha fence),
  `aiDispatchFence.s69` (5), `aiConsentSheetScroll.s75` (6).
- `__tests__/hooks/useComparisonCounter.test.ts` (12; no whole-object equality on the return, measured).
- `__tests__/screens/LimitReachedSheet.s69.test.tsx` (28), `__tests__/honestCounts.s69.test.tsx` (14),
  `__tests__/ResultsScreen.usageFetch.a15.test.tsx` (4), `__tests__/HomeScreen.rateLimitedSeconds.w314.test.tsx` (6).
- every `api.*` suite other than E3 (outputLang reads only `call[1].params` and the SSE URL, so the new
  `headers` key in the REST config does not move it), `api.refreshInterceptor` (15), `api.sessionGate.m18` (6).
- the i18n suites, copy-policy, brand fence, digit policy; `__tests__/config/nativeBundle.w37.test.ts`
  (50 green + the same 4 drift nodes red).
- the backend client-scanning set (7.3), unedited.

-----------------------------------------------------------------------------------------------------

## 5. RED tests

Location `SmartCompareApp/__tests__/s81_08/` (matched by testMatch), files `*.s81_08.test.ts(x)`, LF,
ASCII except AR expectations read from the catalog at run time. Hermetic: every expo module, axios,
`expo/fetch`, the sentry service and global fetch mocked with plain `jest.mock(name, factory)`; never
`{ virtual: true }`. Every RED fails at base on an assertion only: new modules and exports are loaded
with `const load = (p) => { try { return require(p); } catch { return null; } }` and asserted with
`expect(mod).not.toBeNull()` / `expect(typeof mod.x).toBe('function')`; promise outcomes are captured
into values (`try { v = await f(); } catch { v = 'REJECTED'; }`) before `expect`. Every PIN runs with
the full configuration and recorders (2.10). Synthetic values: `NEW = sha256('s81-08-new')`,
`LEG = sha256('s81-08-legacy')` (node crypto at run time), ids from node `crypto.randomUUID()`
upper-cased where the lower-casing is the point.

| # | test (file :: name) | assertion | at base | satisfied by |
|---|---|---|---|---|
| A1 | deviceId :: exports the legacy hash | `typeof legacyDeviceFingerprintHash === 'function'` | RED | 3.1 |
| A2 | deviceId :: new id = sha256(lower-cased nonce) | nonce 'Persisted-Nonce-Ab' -> digest called with ('SHA256', 'persisted-nonce-ab'), value `h(persisted-nonce-ab)` | RED | 3.1 |
| A3 | deviceId :: new id never reads osBuildId | getter-instrumented expo-device mock: 0 reads of osBuildId / osInternalBuildId during `getDeviceFingerprint()` | RED | 3.1 |
| A4 | deviceId :: legacy == today's composition | `legacyDeviceFingerprintHash()` digest input `'app.qaren.test|iPhone15,2/21D|Persisted-Nonce-Ab'` exactly, value equal | RED | 3.1 |
| A5 | deviceId :: stable across restarts | first run generates + persists under `device_fp_nonce` once; after `_resetCacheForTests()` the same value, no second setItemAsync | PIN | base + 3.1 |
| A6 | deviceId :: iOS fallback, not cached | SecureStore throws -> `getIosIdForVendorAsync` called, value `h(<idfv lower>)`, no setItemAsync, no AsyncStorage write; next call with a healthy SecureStore reads SecureStore again | RED | 3.1 |
| A7 | deviceId :: Android fallback | Platform.OS 'android', SecureStore throws -> `getAndroidId` value hashed; IDFV never called | RED | 3.1 |
| A8 | deviceId :: no fallback -> reject | SecureStore throws, IDFV null -> value 'REJECTED' AND `getIosIdForVendorAsync` called once | RED | 3.1 |
| A9 | deviceId :: the id is written only to SecureStore | full first-run path: AsyncStorage.setItem recorder never called; SecureStore.setItemAsync called with `device_fp_nonce` only | PIN | base + 3.1 |
| A10 | deviceId :: one nonce read serves both hashes | new + legacy in one process -> getItemAsync 1 call, digest 2 calls (one per composition), repeat calls cached | RED | 3.1 |
| A11 | deviceId :: dated cutoff constant | `LEGACY_FINGERPRINT_HEADER_UNTIL_MS === Date.UTC(2027, 2, 31, 21, 0, 0)` | RED | 3.1 (Q2) |
| A12 | deviceId :: window predicate | active at cutoff-1 ms, inactive at cutoff and cutoff+1 | RED | 3.1 |
| B1 | requestHeaders :: usage/status gets device + legacy + consent | captured interceptor on `{url:'/api/v1/usage/status', headers:{}}` -> headers equal `{Authorization, X-Device-Fingerprint: NEW, X-Device-Fingerprint-Legacy: LEG, X-AI-Consent-Version: '2'}` | RED | 3.2, 3.4 |
| B2 | requestHeaders :: compare path gets a lower-case v4 id | `/api/v1/text/compare`, randomUUID upper-case -> header equals its lower case and matches the v4 regex | RED | 3.2, 3.4 |
| B3 | requestHeaders :: id only on compare paths | `/api/v1/url/compare` and `/api/v1/text/quick` get one; `/api/v1/usage/status`, `/api/v1/comparisons/history`, `/api/v1/feedback`, `/api/v1/auth/register` get none | RED | 3.2 |
| B4 | requestHeaders :: only-if-absent | a config carrying `X-Device-Fingerprint: 'c'*64` and `x-compare-request-id: <id>` keeps both values; legacy + consent still added | RED | 3.2 |
| B5 | requestHeaders :: no consent record -> no consent header | `hasCurrentAiConsent` false -> no X-AI-Consent-Version; device headers present | RED | 3.2 |
| B6 | requestHeaders :: Authorization unchanged (full config) | token null -> no Authorization; token 't' -> 'Bearer t'; config returned (same object) | PIN | base + 3.4 |
| B7 | requestHeaders :: builders never block a request (full config) | device, legacy, consent and randomUUID all failing -> interceptor resolves, headers == `{Authorization}` exactly | PIN | base + 3.2 |
| B8 | requestHeaders :: after the cutoff no legacy read | `Date.now` = cutoff -> no legacy header AND legacy recorder 0 calls; device header present | RED (device part) | 3.2 |
| B9 | requestHeaders :: capabilities | `CLIENT_CAPABILITIES` deep-equals `[]`; no X-Client-Capabilities header | RED | 3.2 |
| B10 | requestHeaders :: values never logged (full config) | console.* and sentry mock recorders contain none of NEW / LEG / the id | PIN | base + 3.2 |
| B11 | requestHeaders :: shapes the server accepts | REAL deviceFingerprint with a digest mock returning real sha256 hex: X-Device-Fingerprint and -Legacy match `^[a-f0-9]{64}$`, consent `^[0-9]{1,3}$`, id canonical v4 lower case | RED | 3.1, 3.2 |
| B12 | requestHeaders :: register end-to-end | the interceptor applied to register's config (explicit NEW) yields X-Device-Fingerprint NEW + legacy LEG | RED | 3.2 |
| C1 | cameraHeaders :: attempt 1 carries the context | fetch init headers include Authorization, NEW, LEG, '2', a v4 id | RED | 3.4 |
| C2 | cameraHeaders :: the 401 retry keeps the same context and id | attempt 2 headers == attempt 1 headers with Authorization replaced by the new bearer | RED | 3.4 |
| C3 | cameraHeaders :: one id per call | two calls -> two distinct ids | RED | 3.4 |
| C4 | cameraHeaders :: request otherwise unchanged (full config) | URL, method, the same FormData object and the same signal on both attempts | PIN | base + 3.4 |
| D1 | sseHeaders :: SSE request headers | expo fetch init headers == `{Accept: 'text/event-stream', Authorization, NEW, LEG, '2', id}` | RED | 3.4 |
| D2 | sseHeaders :: fallback reuses the attempt id | SSE throws -> the REST config `headers['X-Compare-Request-Id']` equals the SSE id; one REST call | RED | 3.4 |
| D3 | sseHeaders :: the id is exposed | `streamComparison(...).compareRequestId` equals the id sent | RED | 3.4 |
| D4 | sseHeaders :: default transport | SSE off: REST config params equal today's literal `{product_a, product_b, region: 'bahrain'}` and headers carry the id | RED (id part) | 3.4 |
| D5 | sseHeaders :: one id per attempt | two `streamComparison` calls -> distinct ids | RED | 3.4 |
| E1 | consentRecord :: Agree writes account + device | account key JSON `{version:2, at, deviceId: NEW}`; `@qaren_device_ai_consent` `{version:2, at, deviceId: NEW}` | RED | 3.3 |
| E2 | consentRecord :: one device rule | after `recordAiConsent('user-a')`, `hasCurrentAiConsent('user-b')` true | RED | 3.3 |
| E3 | consentRecord :: a bump re-asks everyone (full config) | device + account records version 1 -> false for both users | PIN | base + 3.3 |
| E4 | consentRecord :: device mirror must match this device (full config) | device record version 2 with deviceId 'd'*64 != NEW -> false for user-b | PIN | base + 3.3 |
| E5 | consentRecord :: no user persists nothing (full config) | `recordAiConsent(null)` -> neither key written | PIN | base + 3.3 |
| E6 | consentRecord :: deletion keeps the device mirror (full config) | `clearAiConsent('user-a')` removes the account key; the planted device key stays | PIN | base + 3.3 (Q5) |
| E7 | consentRecord :: read shape unchanged | stored `{version, at, deviceId}` -> `readAiConsent` returns exactly `{version, at}` | PIN | base + 3.3 |
| E8 | consentRecord :: device id failure degrades to account-only (full config) | rejecting device id -> account record without deviceId, no device key, `hasCurrentAiConsent('user-a')` true | PIN | base + 3.3 |
| E9 | consentRecord :: the header follows the record | real aiConsent + real requestContext: no record -> no consent header; after `recordAiConsent` -> '2' | RED | 3.2, 3.3 |
| F1 | resetTime :: module + exports | `resolveResetAt`, `formatResetClock` are functions | RED | 3.6 |
| F2 | resetTime :: resets_at in window | now + 5 h (built at run time) -> that instant; `formatResetClock(at, 180)` equals the test's own HH:MM | RED | 3.6 |
| F3 | resetTime :: precedence | resets_at over retry_after_seconds over retry_after | RED | 3.6 |
| F4 | resetTime :: garbage -> null | non-string, 'x', past, now, now + 48 h + 1 s; retry 0, -1, 1.5, '60', true, NaN, Infinity, 172801 | RED | 3.6 |
| F5 | resetTime :: clock format | 03:05 zero-padded, 24-hour (15:00 not 3:00), ASCII digits only | RED | 3.6 |
| F6 | resetTime :: Riyadh midnight | '2026-10-24T00:00:00+03:00' -> '00:00' at offset 180, '01:00' at offset 240 | RED | 3.6 |
| G1 | resetRender :: sheet daily + resets_at | `paywall-resets` == EN `paywall.limit.resets_at` with the formatted time | RED | 3.9 |
| G2 | resetRender :: sheet daily, no reset field (full config: every other status field present) | `paywall-resets` == EN `paywall.limit.resets_daily` byte for byte | PIN | base + 3.9 |
| G3 | resetRender :: 429 retry_after_seconds fallback | fetched status null, `initialUsage.retry_after_seconds` 3600 -> time of now + 1 h | RED | 3.9 |
| G4 | resetRender :: monthly keeps today's copy (full config) | monthly state + resets_at -> `resets_monthly` | PIN | base + 3.9 |
| G5 | resetRender :: open state shows the time | open + resets_at -> resets line present | RED | 3.9 |
| G6 | resetRender :: unknown, nothing present | `resets_unknown` | PIN | base + 3.9 |
| G7 | resetRender :: hook exposes resetsAt | `resetsAt` == status.resets_at; null when absent or non-string | RED | 3.8 |
| G8 | resetRender :: pill with a reset | `home-header-counter-resets` == EN `home.headerCounter.resets`; a11y label == `a11yResets` | RED | 3.10 |
| G9 | resetRender :: pill without a reset (full config) | no `home-header-counter-resets` node; text `${free}/${total} free`; a11y == today's key | PIN | base + 3.10 |
| G10 | resetRender :: Arabic render | AR sheet line contains the ASCII HH:MM and no Arabic-Indic digit | RED | 3.9, 3.11 |
| H1 | i18nKeys :: keys exist with placeholders | three keys in EN and AR; `{{time}}` in all; a11yResets also `{{free}} {{total}} {{bonus}}` | RED | 3.11 |
| H2 | i18nKeys :: honest copy | none of the six values matches copy-policy banned / scary lists, /tomorrow/i, /today/i, a digit, or any `AR_DISHONEST` / `EN_DISHONEST` pattern of the paywall fence (copied into the RED file as code-point escapes) | RED | 3.11 |
| H3 | i18nKeys :: parity (full catalogs) | EN key set == AR key set | PIN | base + 3.11 |
| I1 | socialLegacy :: Google + Apple send the legacy header | `X-Device-Fingerprint-Legacy` == LEG beside `X-Device-Fingerprint` == NEW | RED | 3.5 |
| I2 | socialLegacy :: cancelled sign-in reads neither id (full config) | both recorders 0 calls | PIN | base + 3.5 |
| I3 | socialLegacy :: legacy failure never blocks sign-in (full config) | rejecting legacy -> the POST is sent, no legacy header, X-Device-Fingerprint present | PIN | base + 3.5 |
| I4 | socialLegacy :: after the cutoff no legacy on social | `Date.now` = cutoff -> no legacy header, legacy recorder 0 | PIN | base + 3.5 |

Counts: 45 RED, 20 PIN (65 rows; A 12, B 12, C 4, D 5, E 9, F 6, G 10, H 3, I 4). G-rows render PaywallScreen with `@react-navigation/native`
mocked (useNavigation / useRoute) and `getUsageStatus` mocked; G8 / G9 render HomeScreen through the
harness of `__tests__/HomeScreen.rateLimitedSeconds.w314.test.tsx` (measured green at base, 6 nodes)
with `useComparisonCounter` mocked; RED may move G8 / G9 to another measured-green Home harness and
says which. Satisfiability: the RED agent proves 65/65 green on an IN-PLACE prototype with byte
copies of every edited file (restored and sha-checked; no junctioned scratch worktree), then 45 red /
20 green at base.

No tester scenario of the session-80 `eval_regression.json` applies (it covers compare quality; the
words reset / limit / fingerprint / consent occur 13 times there, none about this client contract).

-----------------------------------------------------------------------------------------------------

## 6. Mutation table (each on a byte copy of the GREEN file, an exact-string edit matching once, the killing rows by `-t`, restore + sha256 compare; KILLED = an assertion failure)

| # | Mutant | File | Killed by |
|---|---|---|---|
| M1 | `getDeviceFingerprint` returns the legacy composition | deviceFingerprint.ts | A2, A3 |
| M2 | the new raw string includes `Device.osBuildId` | deviceFingerprint.ts | A3 |
| M3 | drop `.toLowerCase()` on the stable id | deviceFingerprint.ts | A2 |
| M4 | legacy composition lower-cases the nonce | deviceFingerprint.ts | A4 |
| M5 | fallback value stored in `cached` | deviceFingerprint.ts | A6 |
| M6 | fallback persisted with AsyncStorage.setItem | deviceFingerprint.ts | A6, A9 |
| M7 | Android branch calls IDFV | deviceFingerprint.ts | A7 |
| M8 | separate SecureStore read per hash (memo removed) | deviceFingerprint.ts | A10 |
| M9 | cutoff comparison inverted (`nowMs >= UNTIL` for `nowMs < UNTIL`) | deviceFingerprint.ts | A12, B1 |
| M10 | interceptor overwrites an explicit header | requestContext.ts | B4, B12 |
| M11 | id added on every path | requestContext.ts | B3 |
| M12 | id not lower-cased | requestContext.ts | B2, B11 |
| M13 | consent header sent without a current record | requestContext.ts | B5, E9 |
| M14 | legacy window check removed | requestContext.ts | B8 |
| M15 | one builder's try removed (throws through) | requestContext.ts | B7 |
| M16 | headers logged via console.log | requestContext.ts | B10 |
| M17 | capabilities header sent while empty | requestContext.ts | B9 |
| M18 | camera retry sends Authorization only (today's line) | api.ts | C2 |
| M19 | camera retry mints a new id | api.ts | C2 |
| M20 | SSE fallback mints a new id | api.ts | D2 |
| M21 | returned `compareRequestId` differs from the sent id | api.ts | D3 |
| M22 | device mirror not written | aiConsent.ts | E1, E2 |
| M23 | device mirror ignores deviceId | aiConsent.ts | E4 |
| M24 | device mirror ignores version | aiConsent.ts | E3 |
| M25 | `clearAiConsent` also removes the device key | aiConsent.ts | E6 |
| M26 | `recordAiConsent(null)` writes the device key | aiConsent.ts | E5 |
| M27 | resolveResetAt accepts past times | resetTime.ts | F4 |
| M28 | 48 h bound removed | resetTime.ts | F4 |
| M29 | precedence swapped (retry before resets_at) | resetTime.ts | F3 |
| M30 | 12-hour clock / no zero pad | resetTime.ts | F5 |
| M31 | monthly state renders the daily time | PaywallScreen.tsx | G4 |
| M32 | resets line always uses resets_at copy | PaywallScreen.tsx | G2 |
| M33 | pill resets node rendered when absent | HomeScreen.tsx | G9 |
| M34 | social legacy read before the native sheet | authService.ts | I2 |
| M35 | social legacy sent after the cutoff | authService.ts | I4 |

Expected equivalent survivors: none predicted; any survivor is reported for a ruling.

-----------------------------------------------------------------------------------------------------

## 7. Gates for GREEN (cheapest first; every jest by path from SmartCompareApp under coreutils timeout,
one at a time, the tool version printed, a `[jest] tag=... start=... end=... rc=...` line each)

7.1 Static: `timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit` (exit 0);
`timeout -k 15 600 node node_modules/eslint/bin/eslint.js $(git diff --name-only --relative)` from
SmartCompareApp plus the new files; byte checks: new files LF and ASCII, edited files keep CRLF, bytes
> 127 only in the AR catalog values; `git diff --name-only` lists no app.json / eas.json / package*.json
/ `.snap` / `.expo/atlas.jsonl`; no `jest -u`.

7.2 Jest, in order: (a) the 9 RED files, 65/65; (b) the 4.1 suites (deviceFingerprint,
api.cameraAuthRetry.u13c, paywall.noSubscriptionUi.s69) with their re-pins; (c) the 48-suite base set
of 1.10 (expect 454 + re-pinned nodes passed, the same 4 drift nodes red); (d) `--runInBand` ORDER
PAIRS with an order-preserving `--testSequencer` (a 10-line sequencer file in the notes folder that
returns the paths in argv order), both orders: deviceId.s81_08 + deviceFingerprint.test;
requestHeaders.s81_08 + api.refreshInterceptor.test; cameraHeaders.s81_08 + api.cameraAuthRetry.u13c;
consentRecord.s81_08 + consent/aiProcessingConsent.s69; resetRender.s81_08 + screens/LimitReachedSheet.s69;
(e) one `--runInBand` run of the 9 RED files + the 4.1 suites; (f) the FULL suite once:
`timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci` at base (NOT MEASURED in this spec) and
at head: passed count = base + 65 (the new rows) and the only failures the four nativeBundle.w37 drift
nodes. The full suite is the comm set for the client (api.ts is referenced by 104 suites, aiConsent /
deviceFingerprint / usage / paywall by 43, measured by grep), so no reference-grep subset replaces it.

7.3 Backend comm set (the client-visible change rule: the SmartCompareApp-scanning backend tests UNION
the CLAUDE.md readers UNION the fingerprint pins; no backend file changes, so the module-reference grep
is empty and the source-scanning pins do not read client files): one bounded-runner chunk of 25 files
at head vs the base record (1899 passed, 1.10):
tests/test_arabic_verdict_output_w414.py tests/test_b2_strict_optional_auth.py tests/test_ci_gates.py
tests/test_comparison_id_echo.py tests/test_consent_capture_w3_16.py
tests/test_dimension_label_catalog_parity_w414.py tests/test_events_allowlist_superset.py
tests/test_feature_bucket_parity.py tests/test_feedback_allowlist_superset.py
tests/test_landing_fallback_pages_s69.py tests/test_legal_disclosure_s77.py tests/test_legal_docs_u8.py
tests/test_legal_docs_u8_d3c.py tests/test_legal_docs_u8_polish.py tests/test_legal_s78.py
tests/test_migration_037_security_definer_grants.py tests/test_paid_route_metering.py
tests/test_register_benefits_parity_s69.py tests/test_review_paraphrase.py tests/test_secret_scan_static.py
tests/test_security_regression.py tests/test_text_error_envelope_no_raw_exception.py
tests/test_timeout_partial_integration.py tests/test_auth_routes_invite_fingerprint.py
tests/test_behavior_dimension_translation.py
(`grep -rl SmartCompareApp tests/` = 27 files: these 23 + the two precommit-hook files, which stay
out unless .githooks changes, + 2 fixtures). `comm -13` of the sorted FAILED node ids EMPTY.

7.4 Commit gate: the pre-commit hook (gitleaks + the secret shapes + ESLint on staged client files)
on the commit, never `--no-verify`; the added-line sweep (no @gmail, +973, 8-digit runs, key shapes).

-----------------------------------------------------------------------------------------------------

## 8. CLAUDE.md row and owner steps

Edit in place (principle 5): (1) the Frontend Services bullet for `api.ts` gains one sentence: "Since
S81-08 (OTA after approval) every axios request, both camera attempts and the SSE request carry
`X-Device-Fingerprint`, `X-Device-Fingerprint-Legacy` (until 2027-04-01 00:00 Riyadh), `X-AI-Consent-Version`
(only with a current consent record) and, on compare attempts, `X-Compare-Request-Id` (lower-case
uuid4, one per attempt, `streamComparison(...).compareRequestId`); a builder failure only omits its
header." (2) the "Session 69 client surfaces" `aiConsent.ts` clause "AsyncStorage
`@qaren_ai_consent_<userId>`, no server record" becomes "AsyncStorage `@qaren_ai_consent_<userId>` plus
the device mirror `@qaren_device_ai_consent` ({version, at, deviceId}; one consent per device and
version, S81-08), no server record". (3) the usage_service bullet's "Device-bound (Migration 021)"
sentence gains "(the client value changes with the S81-08 OTA: the legacy value rides
`X-Device-Fingerprint-Legacy` for the transition window)". (4) a new row after the last SESSION 81
flag row (measured: at dfc6502f the last is the S81-03 LLM-LEDGER-V2 row; S81-05's row is not on main
yet, so the anchor is a known union at rebase in the session order B1, B3, B4, D03, S81-03, ST1,
S81-05, S81-08); a client unit has no flag, so the row is headed "SESSION 81 client unit":

"SESSION 81 client unit (S81-08 CLIENT-FIRST-OTA, no flag; merged to main, reaches phones ONLY with the
first post-approval OTA together with S81-11 and the consent v3 copy, UB-R4): request headers for S81-05:
`X-Device-Fingerprint` = SHA-256 hex of the SecureStore UUID `device_fp_nonce` lower-cased (IDFV / ANDROID_ID
fallback only when SecureStore throws, never cached or persisted; no osBuildId), `X-Device-Fingerprint-Legacy`
= the build-3 composition applicationId|osBuildId|nonce (constant `LEGACY_FINGERPRINT_HEADER_UNTIL_MS`
= 2027-03-31T21:00:00Z; removed by a later OTA), `X-AI-Consent-Version` = String(AI_CONSENT_VERSION)
only with a current account or device consent record, `X-Compare-Request-Id` = lower-case uuid4 per
compare attempt; headers are never overwritten when set and never sent empty; register, both social
sign-ins and the share body now carry the NEW value (precondition Q1). `X-Client-Capabilities` ships
with an empty list (S81-11 adds price_asof with the as-of rendering). The usage pill and the limit
sheet show the device-local reset time (HH:MM) only when `/usage/status` sends `resets_at` or the
USAGE_LIMIT 429 carries `resets_at` / `retry_after_seconds`; absent = the build-3 copy (S81-09 is the
producer). Owner steps (names only): update the App Store Connect App Privacy answers BEFORE the OTA
(Device ID, linked to the user, App Functionality / fraud prevention, not tracking); publish the OTA
only after approval, after LEGAL-V3 is live and after a backend that reads `X-Device-Fingerprint-Legacy`
at register / social sign-in / the referral SAME_DEVICE check is deployed (Q1); then the TestFlight
check of a compare, the camera and the limit sheet in EN and AR. Stated limits: the consent header is
the client's claim; the legacy header doubles the fingerprint bytes per request until the cutoff; the
reset time renders only once S81-09 is live; no E2E on a device in CI."

-----------------------------------------------------------------------------------------------------

## 9. Stated limits

1. The consent version header is the client's own claim; the server cannot verify it (S81-06 routes on it).
2. The legacy header (and its osBuildId read) lives until the cutoff; it doubles the fingerprint
   bytes on every request and keeps the near-fingerprinting composition on the wire for the window
   (the build-3 status quo, R5 finding 29).
3. Register, both social sign-ins and the share body switch to the NEW value with the OTA: until a
   backend reads `X-Device-Fingerprint-Legacy` there, a re-signup on a device whose earlier accounts
   stored the legacy value does not inherit `lifetime_comparisons_used`, and a pre-OTA invite plus a
   post-OTA same-device registration is not flagged SAME_DEVICE (Q1 names the precondition).
4. The fallback id (IDFV / ANDROID_ID) differs from the primary value, so a device whose SecureStore
   fails intermittently can present two ids; iOS IDFV can be null before the first unlock.
5. iOS Keychain items usually survive a reinstall (the id with them); Android resets on uninstall;
   neither is a strong device signal against a script that sends random hashes (A7 finding 13).
6. The device consent mirror lives in AsyncStorage (per install, restorable from a backup; the
   deviceId check rejects a mirror restored to another device).
7. The reset time is the device-local clock (UAE / Oman see 01:00 for a Riyadh midnight reset); it
   renders only when S81-09 sends the field.
8. No E2E on a device: the owner's TestFlight check after the OTA is the proof; S81-05 never logs
   headers, so header arrival is visible only through S81-09's header_state metric.
9. Expo web is not a target (no CORS change; S81-05 R-S05-6).
10. The consent header costs one `getSavedUser` + up to two AsyncStorage reads per request (no memo,
    correctness first, Q6).
11. FULL jest baseline not measured in this spec (box load); GREEN measures it.

-----------------------------------------------------------------------------------------------------

## 10. Out of scope

Any backend change (S81-05 / S81-09 own the server halves); sending the compare request id with
feedback and events (SF1 / CL3); the as-of date rendering and `price_asof` (S81-11 / S81-18); the
consent copy, version and sha fence (S81-12); removing the legacy header (a later OTA); App Attest /
DeviceCheck (native, 1.0.1); the device-quota remaining counts on the pill (S81-09's fields; this unit
renders only the reset time); the OTA itself (owner, after approval).

-----------------------------------------------------------------------------------------------------

## 11. Open questions for the orchestrator

- Q1 (MAJOR, transition order): the spec follows R-S05-1 and the brief literally: register, social and
  share carry the NEW value, the legacy value rides X-Device-Fingerprint-Legacy. The base server
  matches stored rows on X-Device-Fingerprint / the share body only, so the "keep working" promise
  holds only once a backend that reads the legacy header at register, social sign-in and the referral
  SAME_DEVICE check is live BEFORE the OTA (build 3 never sends the header, so that read is
  unflagged-safe). Rule: (a) keep the spec (precondition on S81-09 or a small additive backend unit),
  or (b) keep the legacy VALUE in X-Device-Fingerprint at register / social and in the share body
  until S81-09 flips (safe with today's server, but a second OTA is needed to move those sites).
- Q2: the cutoff date 2027-03-31T21:00:00Z and the RUNTIME cutoff (the header stops by itself even if
  no later OTA ships) vs a code-removal-only window.
- Q3: PLAN_S81:173 lists `X-Client-Capabilities: price_asof`; the spec ships the plumbing with an
  empty list (2.8) so S81-11 adds the token with the rendering. Confirm the deviation.
- Q4: the stable id reuses `device_fp_nonce` (existing installs keep one id across the OTA) instead of
  a new SecureStore key.
- Q5: account deletion keeps the device consent mirror (it holds no account id) - or clear it too.
- Q6: per-request consent read without a memo (stated limit 9.10) vs an in-memory memo invalidated
  on record / user change.
- Q7: the pill shows the reset time whenever present (D9) vs only when the free count is 0; device-local
  clock vs Riyadh time.
- Q8: S81-09 should put `retry_after` (int) in the USAGE_LIMIT detail so the existing handler emits
  `retry_after_seconds` + `Retry-After` (error_handler.py:146-167); the client reads
  `retry_after_seconds`, then `retry_after`, and `resets_at` through S81-09's allow-list.
- Q9: the device/consent headers ride EVERY axios request (auth, legal, events included), the simplest
  reading of "every metered request"; or an allowlist of metered paths.

## Not done in this spec

No prototype of the change (RED's job); no mutation run; the FULL jest suite not measured at base; the
exact red set of E3 not measured (predicted, possibly zero, 4.1 note); no device or TestFlight check;
the App Privacy wording is the owner's.
