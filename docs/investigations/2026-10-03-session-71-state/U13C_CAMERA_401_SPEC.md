# U13c: camera `/image/identify` 401 -> one single-flight refresh -> one retry (SPEC)

Unit U13c, MYEZ Apple launch lane, session 71 (2026-10-03). Issue #298. Client only (SmartCompareApp), OTA-capable.
Spec writer: Opus (read-and-measure only). Status: DRAFT, awaiting Fable rulings on section 8 before any RED test.
Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b`, branch `feature/s71-u13c-camera-401`.
Line numbers are anchors at base; the named symbol is authoritative.

---

## 1. Base

```
$ git -C sc-s70-u4b rev-parse HEAD            -> 72b13bc53fb74445ea6e5782d7b8af67c938c399
$ git -C sc-s70-u4b status --porcelain=v1 | wc -l   -> 0   (clean)
$ git -C sc-s70-u4b branch --show-current     -> feature/s71-u13c-camera-401
$ git log --oneline -1                        -> 72b13bc5 Merge pull request #307 ... s71-u4d-reveal-glyph
```
Toolchain (from `SmartCompareApp/`): `node_modules/@babel/core` and `node_modules/.bin/jest` present; `node node_modules/jest/bin/jest.js --version` -> `29.7.0`; react-native 0.81.5, expo 54.0.37, whatwg-fetch 3.6.20 (`node -e "require('./node_modules/<p>/package.json').version"`). Jest runs `preset: 'ts-jest'`, `testEnvironment: 'node'`, `setup.ts` sets `__DEV__ = false` (`jest.config.js`, `__tests__/setup.ts:11`).

---

## 2. Measured facts

### (a) The camera upload path today

Command: `cat -n src/services/api.ts | sed -n '1,420p'`; `grep -rn "image/identify\|identifyProduct\|uploadImage" src` (one caller).

- Only caller: `ResultsScreen` camera effect, `src/screens/ResultsScreen.tsx:288-390`, lazily `await import('../services/api')` then `identifyFromImages(visionProducts, 'bahrain')` (`:295-296`). No other `src` caller: `grep -n "identifyFromImages\|image/identify"` finds only comments elsewhere (`failureClassification.ts:68`, `fetchWithDeadline.ts:31`, `types/types.ts:594`, `ResultsScreen.tsx:283,325,370`).
- `identifyFromImages` (`api.ts:252-374`):
  - builds ONE `FormData`, one `images` part per URI after `ImageManipulator.manipulateAsync(uri, [{resize:{width:1024}}], {format: JPEG, compress: 0.8})` -> `{uri: manipulated.uri, type:'image/jpeg', name:'product_<i>.jpg'}` (`:259-276`);
  - bearer: `const { getToken } = require('./authService'); const token = await getToken();` -> `headers = {}` plus `Authorization: Bearer <token>` only when a token exists (`:278-285`). The `require` avoids the import cycle (`authService.ts:54` imports `api`);
  - deadline: `const controller = new AbortController(); const abortTimer = setTimeout(() => controller.abort(), IDENTIFY_TIMEOUT_MS)` (`:295-296`), `IDENTIFY_TIMEOUT_MS = 120000` (`:46`), cleared in `finally` (`:371-373`);
  - request: `fetch(\`${API_BASE_URL}/api/v1/image/identify?region=${encodeURIComponent(region)}\`, { method:'POST', body: formData, headers, signal: controller.signal })` (`:298-306`). It is the RN global fetch (whatwg-fetch), NOT axios, so NO interceptor runs;
  - `!response.ok`: reads `response.text()`; 429 with `USAGE_LIMIT` (top-level or `detail`) -> `Error('Usage limit reached')` with `code:'USAGE_LIMIT'`, `detail` (H3, `:316-334`); every other non-ok -> `Object.assign(new Error(\`Server error ${status}\`), { response: { status, data: parsedBody ?? { error: errorText } } })` (`:350-355`);
  - ok -> `response.json()` returned as-is (`:358-360`);
  - catch: `AbortError` -> `Object.assign(new Error('identify_timeout'), { code:'TIMEOUT', response:{ status:503, data:{ code:'TIMEOUT' } } })` (`:362-369`); anything else rethrown.
- What a 401 does today. Scratch jest probe `scratchpad/u13c/__tests__/probe_base_camera401.test.ts`, run with `--roots <scratch>/u13c --modulePaths <app>/node_modules` under the app jest config. Real `api.ts`, `authService` mocked, `fetch` mocked 401 then 200:
  ```
  PROBE-1 {"fetchCalls":1,"refreshCalls":0,"firstAuth":"Bearer OLD-TOKEN","firstOptsKeys":["method","body","headers","signal"],
           "url":"https://web-production-58776.up.railway.app/api/v1/image/identify?region=bahrain","bodyIsFormData":true,
           "caughtMessage":"Server error 401","caughtStatus":401,"caughtCode":"AUTH_REQUIRED","emits":0,"clearSessionCalls":0}
  PROBE-1 classify auth engineOutage false
  ```
- Classification (`failureClassification.ts:45-61`, `classifyLoadFailure`): `status === 401 -> 'auth'` (row 3); `isCameraEngineOutage` (`:82-95`) is false for 401.
- Screen (`ResultsScreen.tsx:351-382`, camera catch): `USAGE_LIMIT` -> Paywall (`:357-361`); `isCameraEngineOutage` -> `engine_unavailable` (`:374-378`); else `const kind = classifyLoadFailure(err); setLoadError(kind === 'timeout' ? 'timeout' : 'generic')` (`:379-380`). So 401 -> `'generic'`.
- What the user sees for a 401 today (`ResultsScreen.tsx:758-816`): title `t('results.emptyState.title')` = "No comparison loaded", CTA `t('results.emptyState.cta')` = "Back to history" (`goBack`). Copy measured with a Python `json.load` of `src/i18n/en.json` (flat keys); both keys present in `ar.json`.
- The history-detail catch maps `'auth'` to a no-op (`:262-263`, "Axios 401 interceptor handles refresh/redirect"), then `setLoadingResult(false)` -> the same generic empty state. Out of scope here (see 7, L6).

### (b) The axios refresh contract

Command: `cat -n src/services/api.ts | sed -n '50,246p'`; `cat -n src/services/authService.ts | sed -n '440,760p'`; `cat -n src/services/sessionEvents.ts`; `sed -n '265,420p' App.tsx`.

- Single flight: `getOrStartRefresh()` (`api.ts:173-179`, exported, ZERO arguments) caches one module-scope `refreshPromise` and clears it in `.finally`. It is the ONLY entry to `POST /api/v1/auth/refresh` (`api.ts:73-85`: the refresh token is single-use; a second spender's 401 maps to `clearSession()` + session-invalid and logs the user out). `authService.runBootRefresh` also goes through it (`authService.ts:714-731`).
- P-A3 (`api.ts:90-111`, `authService.ts:451-464`): the refresh request takes NO per-call timeout and NO AbortSignal; a caller that wants to stop waiting races the Promise, it never aborts the request. Source fences pin this: `authService.bootOptimistic.a3.test.ts:403-407` (`/export function getOrStartRefresh\(\s*\)/`, `/function performRefresh\(\s*\)/`, no `RefreshOptions`) and `:369-399` (the refresh POST call site has no timeout/signal).
- `performRefresh` (`api.ts:112-155`): `refreshSession()` (via `require('./authService')`, `:114`) ->
  - `success` -> `getToken()` -> `{ success:true, token }` (`:139-142`);
  - failure with `sessionInvalid` (no refresh token / server refused / refresh 401) -> `await clearSession(); emitSessionInvalid();` then `{ success:false, token:null, error }` (`:123-137`);
  - transient failure (network, non-401) -> `{ success:false, token:null, error }` with NO clear and NO emit (`:128-129`: "a flaky connection must never log the user out");
  - a throw -> `clearSession()` + `emitSessionInvalid()` in `finally`, then rethrow (`:144-154`).
  `RefreshResult = { success, token, error? }` (`:86`) does not expose `sessionInvalid`.
- Interceptor (`api.ts:204-246`): 429 USAGE_LIMIT rejected untouched; any `401` not already `_retry` and not an auth-flow URL -> `_retry = true`, `await getOrStartRefresh()`, on `success && token` sets `Authorization` and replays `api(originalRequest)` (a NEW request with the same config, so the per-call timeout restarts); otherwise rejects the original 401; a refresh throw rejects the refresh error. A second 401 on the replay is rejected as-is: the interceptor never clears or emits on it.
- Auth loss in the rest of the app (the "sign-in state"):
  - automatic: `emitSessionInvalid()` (single emitter today: `performRefresh`, `sessionEvents.ts:13-20`) -> `App.tsx` listener `setIsAuthenticated(false); setNeedsPreferences(false); setUser(null)` (`App.tsx:279-286`) -> the navigator renders only the `Auth` stack (`App.tsx:365-371`). `Results` is a modal in the authenticated group (`App.tsx:389-393`, `component={ResultsScreen}`, no `onLogout` prop), so it unmounts;
  - user-confirmed: a 401 that survives the interceptor on History -> `setAuthError(true)` (`HistoryScreen.tsx:698-702`) -> `renderAuthError`: `t('common.signInRequired')` ("Sign In Required") + button `t('auth.signIn')` ("Sign In") -> `await clearSession(); onLogout();` (`HistoryScreen.tsx:910-923`); `onLogout` = `handleLogout` = `clearSession()` + the same state trio (`App.tsx:330-335`).
- Can the camera use the same helpers? Yes: `getOrStartRefresh` is in the same module as `identifyFromImages` (call it directly, no `require`). `authService` functions must keep the `require('./authService')` pattern inside `api.ts` (cycle).

### (c) Backend behaviour on the camera route (U13, active since 14:23)

Command: `sed -n '150,300p' app/api/image_routes.py`; `grep -n ... app/api/text_routes.py`; `grep -n "async def get_optional_user" -A 60 app/api/auth_routes.py`; `grep -n ... tests/test_s71_u13_compare_auth_required.py`.

- `@router.post("/identify", dependencies=[Depends(require_paid_route_user)])` (`image_routes.py:153`), then `@limiter.limit("10/minute")`.
- `require_paid_route_user` (`text_routes.py:310-332`): flag ON, no resolved user, no admin key -> `_refuse_paid_route` -> `HTTPException(401, detail={"code":"AUTH_REQUIRED","error":"Sign in to continue."})` (`:233`, `:274-280`), for a missing bearer (`NO_CREDENTIAL`) and a rejected one (`BEARER_REJECTED`). `get_optional_user` (`auth_routes.py:425-459`) turns ANY `verify_token` failure, including an exception (a Supabase blip), into "rejected" -> 401 (strict ON raises its own 401 first; same envelope per U13 T16).
- Wire body (U13 `_assert_envelope`, `tests/test_s71_u13_compare_auth_required.py:379-391`): `set(body) == {"success","error","code","request_id"}`, `success False`, `code "AUTH_REQUIRED"`. T15/T16 (`:698-717`): an expired bearer on every user route incl. `/image/identify` (route `U6`, `:149`, sent as multipart `files=`) -> 401 AUTH_REQUIRED, zero provider/usage calls. T06 (`:597-608`): anonymous -> 401, `stubs.calls == {}` (no Vision, no credit).
- Which stage parses the body: FastAPI 0.141.1 (venv `fastapi.__version__`, pinned `requirements.txt:47`), `fastapi/routing.py:429-430` `body = await request.form()` runs BEFORE `solve_dependencies` (`:481`). So the whole multipart upload is received and parsed before the guard refuses; the 401 arrives only after the full upload. U13 T18c (`:798-807`) pins the same framework order for JSON (decode 422 precedes the guard).
- Consequences for the client: a 401 costs one full upload and no credit (the guard precedes the metering at `image_routes.py:281-295`); the retry is metered normally. T19 (`:810`) measured that refusals do not burn the limiter bucket (on `/text/compare`).
- Envelopes the client already handles on this route: 429 `detail={"error","code":"USAGE_LIMIT","tier","remaining"}` (`image_routes.py:190-197`, `:286-294`); 200 `action` in `comparison | need_second_product | comparison_failed | error` (W2-1b envelope; consumed at `ResultsScreen.tsx:298-349`).

### (d) Re-sending the same FormData on React Native

Command: read `node_modules/react-native/Libraries/Network/{FormData.js,fetch.js,convertRequestBody.js,XMLHttpRequest.js}`, `node_modules/whatwg-fetch/dist/fetch.umd.js`, `node_modules/expo/src/winter/{runtime.native.ts,FormData.ts}`; probe `scratchpad/u13c/probe_formdata_resend.js` (loads the REAL RN `FormData.js` through the app's `babel-preset-expo` and the REAL whatwg-fetch with a recording XHR applying RN's `convertRequestBody` rule). Output (`probe_formdata_resend.out`):
```
P1 getParts twice equal: true
P1 _parts unchanged after getParts x2: true
P2 first fetch status: 401
P2 second fetch status: 200
P2 sends: 2 both same FormData instance: true
P2 identical multipart parts on both sends: true
P2 bearer per send: Bearer OLD , Bearer NEW
P3 aborted-signal fetch rejects: AbortError | sends added: 0
```
- Global `fetch` is whatwg-fetch (`Libraries/Network/fetch.js:15`); Expo's winter runtime does NOT replace fetch, it only patches `FormData.prototype.append/set/...` over the same `_parts` (`runtime.native.ts:24`, `FormData.ts:installFormDataPatch`).
- whatwg-fetch builds a NEW `Request` per `fetch(url, init)` (`fetch.umd.js:355-386`); `bodyUsed` lives on that Request, never on the FormData. `xhr.send(request._bodyInit)` (`:637`) -> RN `convertRequestBody`: `{formData: body.getParts()}` (`convertRequestBody.js:35-36`), a pure map.
- Native side reads each file part per request: Android `NetworkingModule.kt:constructMultipartBody` -> `RequestBodyUtil.getFileInputStream` -> `contentResolver.openInputStream` (`:749`, `RequestBodyUtil.kt:74`); iOS `RCTNetworking.mm` `RCTHTTPFormDataHelper process:` loads each part's `uri` (`:72-95`).
- Verdict: the SAME FormData instance can be re-sent; no rebuild, no second `manipulateAsync`. Precondition: the `ImageManipulator` cache files still exist at retry time (nothing in `identifyFromImages` deletes them). Device-only to observe end to end (7, L1).
- An already-aborted signal: whatwg-fetch rejects `AbortError` before `xhr.send` (`fetch.umd.js:536-537`; probe P3: 0 sends), which the existing catch maps to TIMEOUT.
- Jest limit: the jest env is Node with Node's undici `FormData` (PROBE-2: the RN file object is stringified, `[["images","[object Object]"]]`) and `fetch` is a `jest.fn`, so unit tests can only pin body IDENTITY across the two calls; RN semantics rest on the source reading + probe above.

### (e) Existing tests on the camera path (all GREEN at base)

Command: `grep -rln "identifyFromImages\|image/identify" . | grep -v node_modules`; `grep -rln "classifyLoadFailure\|failureClassification" __tests__`; runs:
```
jest --ci api.networkMatrix.m18 ResultsScreen.networkMatrix.m18 screens/camera.engineUnavailable.s69 api.sessionGate.m18
     api.refreshInterceptor api.refreshMutex api.refreshMutex.branches api.expiredTokenRetry.b2 App.sessionInvalid.m18
     ResultsScreen.timeout ResultsScreen.historyDetailFetch Screens.bundleD.contract screens/ResultsScreen.degraded.s69
  -> Test Suites: 13 passed, 13 total / Tests: 8 todo, 164 passed, 172 total / Snapshots: 0 total
jest --ci consent/aiDispatchFence.s69 authService.bootOptimistic.a3 ResultsScreen.bundleE.s3 consent/aiProcessingConsent.s69
     honestLoaders.u6 HomeScreen.scanCamera authService.logoutRefreshFirst.w1-4d
  -> Test Suites: 1 skipped, 6 passed, 6 of 7 total / Tests: 3 skipped, 133 passed, 136 total
```
- `api.networkMatrix.m18.test.ts:252-349` exercises the real `identifyFromImages`: 500 shape, 502 non-JSON, 429 USAGE_LIMIT, the 120 s abort -> TIMEOUT, offline TypeError. No 401 case. Its `authService` mock has `refreshSession: jest.fn()` (resolves `undefined`); untouched by U13c because no test there returns 401.
- `ResultsScreen.networkMatrix.m18.test.ts:67-75`: source slice from `export async function identifyFromImages` to `export async function getComparisonHistory` must contain `AbortController`, `IDENTIFY_TIMEOUT_MS`, `signal`; `:38-51`: `classifyLoadFailure(` at least twice, `setLoadError('vision_failed')` exactly once, `setLoadError('timeout')` and `('not_found')` present.
- `consent/aiDispatchFence.s69.test.ts:58-325`: AST inventory over `App.tsx` + `src/**` must EQUAL a pinned list containing exactly ONE `src/services/api.ts | endpoint:/image/identify | impl:identifyFromImages` row and ONE `src/screens/ResultsScreen.tsx | call:identifyFromImages | ungated` row. Any second string/template literal containing `/image/identify` in `src`, or the URL moved into a differently named top-level function, FAILS it.
- `screens/camera.engineUnavailable.s69.test.tsx`: renders `ResultsScreen` with `identifyFromImages` mocked; 503/500 outage, comparison_failed, success:false, watchdog TIMEOUT. No 401 or plain-4xx camera case. The harness this unit's screen test copies.
- `ResultsScreen.bundleE.s3.test.tsx:223`, `Screens.bundleD.contract.test.ts:52-60`: source regexes on ResultsScreen (identify call, not_found wiring); unaffected.
- Which would break: none of the above if section 3 is followed. No test pins camera-401 -> generic today (`grep -n "401"` over every suite that mocks `identifyFromImages` returns only the classifier row `api.networkMatrix.m18.test.ts:212`). No ResultsScreen snapshot exists (17 `.snap` files, 42 `exports[` entries, none for ResultsScreen).

### (f) Sentry / analytics on this path

Command: `grep -n ... src/services/sentry.ts`, `__mocks__/sentry-react-native.ts`, the `identifyFromImages` body.
- `identifyFromImages` adds no breadcrumb, no analytics event, no Sentry call; its only logs are `__DEV__`-gated (`:256-257`, `:336` logs `status` + server body text, `:359` logs `action`). None carries the token today.
- Device Sentry scrubs `Bearer ...`, JWT shapes and `authorization` headers in `beforeSend` / `beforeBreadcrumb` (`sentry.ts:28-45`, `:96-166`). That is defence in depth only; U13c must not rely on it (R9).

---

## 3. Requirements

- **R1 Trigger.** In `identifyFromImages`, when the FIRST response has `status === 401` (any body, mirroring the interceptor), obtain a token through `getOrStartRefresh()` (called with no arguments). Never call `refreshSession()` directly, never add a refresh helper, never pass a signal or timeout into the refresh (P-A3).
- **R2 One retry.** If the RefreshResult has `success === true` and a non-empty `token`, send exactly ONE retry: the same URL value, `method: 'POST'`, the SAME `FormData` instance (no rebuild, no second `manipulateAsync`), headers exactly `{ Authorization: 'Bearer <result.token>' }`, the SAME `controller.signal`. Per call: at most 2 `fetch` calls and at most 1 `getOrStartRefresh()` call, whatever the retry returns.
- **R3 Retry outcome.** The retry's response goes through the EXISTING handling unchanged: 2xx returns `response.json()` (any `action`, incl. `comparison_failed`); 429 USAGE_LIMIT gives the H3 tagged error; any other non-ok, a second 401 included, gives the existing `Server error <status>` axios-shaped error with `response.data` = the parsed body.
- **R4 Auth loss in the service.** A failed refresh (`success` false, no token, or `getOrStartRefresh()` rejecting) sends NO retry and throws the existing axios-shaped error built from the FIRST 401 response (`response.status === 401`, `response.data.code === 'AUTH_REQUIRED'` when the backend sent the envelope). A rejection from `getOrStartRefresh()` is caught and never propagated: its status belongs to `/auth/refresh` and would misclassify, e.g. a refresh 500 read as an engine outage. `identifyFromImages` never calls `clearSession()` or `emitSessionInvalid()` itself. A dead session is cleared and announced exactly once, by `performRefresh`. A transient failure clears nothing.
- **R5 Screen mapping.** In the ResultsScreen CAMERA catch only, `classifyLoadFailure(err) === 'auth'` sets a new `loadError` value `'auth'`, never `'generic'`. The USAGE_LIMIT and engine-outage checks before it stay as they are. The history-detail catch (`:254-272`) is unchanged.
- **R6 Sign-in state.** `loadError === 'auth'` renders inside the existing empty-state shell (header back arrow unchanged), with these parts:
  - container `testID="results-auth-state"`;
  - title `t('common.signInRequired')`, no body line;
  - one CTA, `testID="results-auth-signin"`, label `t('auth.signIn')`. Its `onPress` does `await clearSession()` (from `../services/authService`) and then `emitSessionInvalid()` (from `../services/sessionEvents`), so App's listener lands the user on the Auth stack. This is the HistoryScreen pattern without an `onLogout` prop.

  No new i18n keys (both keys exist in `en.json` and `ar.json`).
- **R7 Everything else unchanged (S2).** Any first status other than 401 follows today's path: one fetch, no refresh, the same thrown errors and returned data. The first `fetch` call keeps today's exact shape:
  - the same URL value;
  - option keys `[method, body, headers, signal]`;
  - `headers` = `{Authorization}` when a token is stored, `{}` when none is.
- **R8 Deadline.** One `AbortController` and one `IDENTIFY_TIMEOUT_MS` timer bound the whole call (first upload, refresh wait and retry), cleared in the existing `finally`. A deadline that expires during the refresh wait does not touch the refresh. The retry then runs on the already-aborted signal: RN fetch rejects `AbortError` without sending (probe P3), and the existing catch turns that into the TIMEOUT error. Subject to Q3.
- **R9 No token leak.** Nothing U13c adds writes the old or new access token anywhere: no console call (also under `__DEV__ === true`), no Sentry call, no analytics call, no field or message of a thrown error.
- **R10 Source invariants.** The following must all hold after the change:
  - The `/image/identify` URL appears as ONE literal in `src` and stays lexically inside `identifyFromImages`, so it is built once and reused (the `aiDispatchFence` inventory);
  - No new `src` string literal contains `/image/identify`, including error messages and logs;
  - `getOrStartRefresh()` keeps its zero-argument signature;
  - `api.ts` before the `identifyFromImages` JSDoc and from the `Get comparison history` JSDoc onward is byte-identical (gate G7b, which pins the singleton, `performRefresh` and the interceptor);
  - The `identifyFromImages`..`getComparisonHistory` slice still contains `AbortController`, `IDENTIFY_TIMEOUT_MS` and `signal`.
- **R11 OTA / scope (S4, S5).** JS only. No change to `app.json`, `eas.json`, `package.json` or `package-lock.json`. No native module. No `.snap` file added, changed or deleted.

Non-goals: the history-detail 401 (still the generic state, see L6), the SSE 401 (falls back to the axios REST compare, which refreshes), HomeScreen 401 copy, skipping the refresh when another caller already rotated the token.

---

## 4. Files

Touch (the only allowed set, enforced by G7d):
- `SmartCompareApp/src/services/api.ts`, inside `identifyFromImages` only (R1-R4, R7-R10). A non-exported helper with no URL literal may sit between the two G7b markers.
- `SmartCompareApp/src/screens/ResultsScreen.tsx`, with four changes and nothing else:
  - the `loadError` union gains `'auth'`;
  - the camera catch line `:380`;
  - the `isAuth` render branch, title, CTA and `testID`;
  - imports: `clearSession` joins the existing `authService` import, plus `emitSessionInvalid`.
- `SmartCompareApp/src/services/sessionEvents.ts`, header comment only, if Q1 is ruled as recommended. Its "exactly ONE emission site" sentence becomes false.
- NEW `SmartCompareApp/__tests__/api.cameraAuthRetry.u13c.test.ts`
- NEW `SmartCompareApp/__tests__/screens/camera.authRequired.u13c.test.tsx`

Must NOT change (G7a byte-compare against base, CRLF-normalised): `app.json`, `eas.json`, `package.json`, `package-lock.json`, `App.tsx`, `src/services/authService.ts`, `src/services/failureClassification.ts` (401 -> `'auth'` already exists), `src/services/errorCopy.ts`, `src/services/sentry.ts`, `src/screens/HistoryScreen.tsx`, `src/i18n/en.json`, `src/i18n/ar.json`, `jest.config.js`, every existing test file (named in G7a: `api.networkMatrix.m18`, `camera.engineUnavailable.s69`, `aiDispatchFence.s69`), every `.snap`, backend `app/api/image_routes.py` and `app/api/text_routes.py`.

---

## 5. Tests

### 5.1 RED - `__tests__/api.cameraAuthRetry.u13c.test.ts` (service, real `api.ts` refresh singleton)

Harness: copy `api.sessionGate.m18.test.ts:24-90`. It mocks:
- `certificatePinning`;
- `authService` as `{ getToken, refreshSession, clearSession }` over `mockGetToken / mockRefreshSession / mockClearSession`;
- `axios` (instance with `interceptors.*.use: jest.fn()`);
- `expo-image-manipulator` (`manipulateAsync` resolves `{uri:'file:///manipulated.jpg'}`);
- `../src/services/sentry`, and `@sentry/react-native` with `jest.fn` members, for T16.

`beforeEach` does the following:
- `jest.resetModules()`, then `require` `api` and `sessionEvents`;
- `__resetSessionListeners()`, then subscribe an `emits` counter;
- `api.__resetRefreshMutex()`;
- `global.fetch = jest.fn()`, restored in `afterEach` together with real timers.

Tokens: `mockGetToken.mockResolvedValueOnce('OLD-TOKEN').mockResolvedValue('NEW-TOKEN')`, so `performRefresh` reads NEW. Responses are `{ok, status, text, json}` objects, and the 401 body is the U13 envelope `{"success":false,"code":"AUTH_REQUIRED","error":"Sign in to continue.","request_id":"r"}`.

| id | name | asserts | RED at base because |
|---|---|---|---|
| T1 | `401 then 200: one refresh, one retry with the new bearer, resolves the 200 data` | resolves the 200 JSON. `fetch` x2, `mockRefreshSession` x1. Call 1 `Authorization` is `Bearer OLD-TOKEN`, call 2 headers `toEqual({Authorization:'Bearer NEW-TOKEN'})`. Same URL, `method` POST. `calls[1][1].body === calls[0][1].body` and `calls[1][1].signal === calls[0][1].signal`. `clearSession` x0, `emits` 0 | base rejects `Server error 401` after 1 fetch and 0 refreshes (PROBE-1) |
| T2 | `401 twice: exactly one refresh, no third request, rejects the auth error` | rejects with `response.status 401`, `response.data.code 'AUTH_REQUIRED'`, `classifyLoadFailure(err) === 'auth'`, `isCameraEngineOutage(err) === false`. `fetch` x2 exactly, refresh x1, `clearSession` x0, `emits` 0 | base: `fetch` x1, refresh x0 |
| T3 | `dead session (refresh sessionInvalid): no retry, cleared and announced exactly once by performRefresh` | `mockRefreshSession` resolves `{success:false, error:'No refresh token found', sessionInvalid:true}`. Rejects the 401 auth error from the FIRST response; `fetch` x1; refresh x1; `clearSession` x1; `emits` 1 | base: refresh x0, clearSession x0, emits 0 |
| T4 | `transient refresh failure: no retry, nothing cleared, nothing announced` | refresh resolves `{success:false, error:'Network Error'}`. Rejects the 401 auth error; `fetch` x1; refresh x1; `clearSession` x0; `emits` 0 | base: refresh x0 |
| T5 | `a rejecting refresh is swallowed into the 401 auth error, never the refresh error` | `mockRefreshSession` rejects `Object.assign(new Error('boom'), {response:{status:500}})`, so `performRefresh` clears, emits and rethrows. The camera rejects with `response.status 401` and `data.code 'AUTH_REQUIRED'`; NOT status 500; `fetch` x1 | base: refresh x0 (asserted first) |
| T6 | `401 then 429 USAGE_LIMIT: the retry goes through the H3 tag` | rejects `{code:'USAGE_LIMIT', detail:{code:'USAGE_LIMIT'}}`; refresh x1 | base rejects the 401 |
| T7 | `401 then 500 INTERNAL_ERROR: the retry's error is the existing engine-outage shape` | rejects `Server error 500`, `response {status:500, data:{code:'INTERNAL_ERROR'}}`, `isCameraEngineOutage` true | base rejects the 401 |
| T8 | `401 then 200 comparison_failed: the envelope is returned untouched` | resolves `toEqual` the envelope | base rejects the 401 |
| T9 | `single flight: a refresh already in flight is joined, never a second refresh` | `mockRefreshSession` returns a deferred. Start `api.__testRefreshDedup()`, then call `identifyFromImages` with a first 401. Flush, resolve the deferred `{success:true}`. Assert `mockRefreshSession` x1 TOTAL and retry bearer `Bearer NEW-TOKEN` | base: identify rejects 401, 1 fetch |
| T10 | `deadline during the refresh wait: TIMEOUT, nothing sent on the aborted signal` (fake timers) | fetch #1 gives 401. The refresh is a deferred. Advance `IDENTIFY_TIMEOUT_MS + 1`, then resolve `{success:true}`. Fetch #2's mock rejects `AbortError` when `opts.signal.aborted`, mirroring whatwg-fetch `:536`. Rejects `{code:'TIMEOUT'}`; refresh x1; any second call's `signal.aborted === true` | base rejects 401 at once, not TIMEOUT |
| T11 | `one shared deadline: a hung retry times out at IDENTIFY_TIMEOUT_MS from the start` (fake timers, Q3) | fetch #1 resolves 401 only after 60 000 ms of FAKE time, so a per-attempt timer would be re-armed late. Refresh OK; fetch #2 hangs (honours abort). Advance `IDENTIFY_TIMEOUT_MS + 1` in total from the call start: rejects `{code:'TIMEOUT'}`. A per-attempt timer would still be pending | base rejects 401 |

### 5.2 PIN - same file (green at base and after)

| id | name | asserts |
|---|---|---|
| T12 | `200 first: no refresh` | resolves; `fetch` x1; refresh x0 |
| T13 | `500 first: existing axios-shaped error, no refresh` | `Server error 500` + `response{status, data}`; refresh x0; `fetch` x1 |
| T14 | `offline TypeError: passes through, no refresh` | no `.response`; `classifyLoadFailure` gives `'timeout'`; refresh x0 |
| T15 | `429 USAGE_LIMIT first: H3 tag, no refresh` | tagged error; refresh x0 |
| T16 | `no access token is ever logged or thrown` | `globalThis.__DEV__ = true` for this test, restored after. Spy every `console.{log,info,warn,error,debug}`, every `jest.fn` export of both Sentry mocks, and capture the thrown error. Run 401->200 and 401->401. `JSON.stringify` of every recorded call argument plus `String(err)`, `err.message` and `JSON.stringify(err.response)` contains neither `OLD-TOKEN` nor `NEW-TOKEN` |
| T17 | `first request shape is today's` | keys `['method','body','headers','signal']`; with `getToken` returning `null` the headers are `{}`. Also: a 401 with no stored token still takes R1 (refresh x1) |

### 5.3 RED - `__tests__/screens/camera.authRequired.u13c.test.tsx` (screen)

Harness: copy `camera.engineUnavailable.s69.test.tsx:29-130` (`api` mocked with `mockIdentifyFromImages`, `authService` mocked incl. `clearSession: mockClearSession`, fake timers, `renderCamera` + `tick(1500)`; the global `react-i18next` mock returns keys). Use the REAL `sessionEvents`, with a listener subscribed in the test and removed in `afterEach`. Thrown error: `thrownIdentify(401, {success:false, code:'AUTH_REQUIRED', error:'Sign in to continue.'})`.

| id | name | asserts | RED at base because |
|---|---|---|---|
| S1 | `a camera 401 shows the sign-in state, never the generic error` | `getByTestId('results-auth-state')` and `getByText('common.signInRequired')` and `getByText('auth.signIn')` are present. `results.emptyState.title`, `results.emptyState.cta`, `results.timeout.*`, `home.errors.engineUnavailable.*` and `results.emptyState.visionFailed` are absent. `navigation.navigate` not called | base renders `results.emptyState.title` (`:380` gives `'generic'`) |
| S2 | `the sign-in CTA clears the session, then announces it` | `fireEvent.press(getByTestId('results-auth-signin'))` + flush. `mockClearSession` x1, listener x1; the order (recorded) is clear before emit; `navigation.goBack` not called | no such testID at base |

PIN (same file): S3 `a camera 400 still shows the generic state` (`results.emptyState.title` + `results.emptyState.cta`, no `common.signInRequired`). S4 `the history-detail 401 is unchanged` (`route.params.comparison_id`, `mockGetComparison` rejects 401: no `common.signInRequired`, `results.emptyState.title` rendered).

Expected RED run: T1-T11 + S1-S2 fail on assertions (13), not on harness errors. T12-T17 + S3-S4 pass (8). Before the GREEN gate, the RED agent pastes each failing assertion's message.

### 5.4 Existing PIN suites (must stay green, unmodified)

`api.networkMatrix.m18`, `ResultsScreen.networkMatrix.m18`, `screens/camera.engineUnavailable.s69`, `api.sessionGate.m18`, `api.refreshInterceptor`, `api.refreshMutex`, `api.refreshMutex.branches`, `api.expiredTokenRetry.b2`, `App.sessionInvalid.m18`, `ResultsScreen.timeout`, `ResultsScreen.historyDetailFetch`, `Screens.bundleD.contract`, `screens/ResultsScreen.degraded.s69`, `consent/aiDispatchFence.s69`, `authService.bootOptimistic.a3`, `ResultsScreen.bundleE.s3`, `consent/aiProcessingConsent.s69`, `honestLoaders.u6`, `authService.logoutRefreshFirst.w1-4d` (HomeScreen.scanCamera is skipped at base).

### 5.5 Mutants

Each mutant is applied to the GREEN bytes after a `shutil.copyfile` snapshot. Run the two new files, restore from the copy, then sha256-compare. Every mutant must turn at least one named test red.

| # | mutant | killed by |
|---|---|---|
| M1 | no retry: refresh, then throw the first 401 | T1, T6, T7, T8 |
| M2 | two retries: loop refresh+retry up to 2 times | T2 (fetch x2 exactly, refresh x1) |
| M3 | retry without the new token (reuses the original `headers`) | T1 (call 2 bearer) |
| M4 | refresh on 500 (trigger on `!response.ok`) | T13 (refresh x0), T7 |
| M5 | parallel refresh outside the single flight: `require('./authService').refreshSession()` directly | T9 (refreshSession x2), T3 (no clear/emit without `performRefresh`) |
| M6 | generic error on the second 401: screen maps `'auth'` to `'generic'`, or the service throws a status-less `Error` | S1; T2 (`classifyLoadFailure === 'auth'`) |
| M7 | token logged: `console.log('[identify] retry', headers)` or `Sentry.addBreadcrumb({data:{headers}})` | T16 |
| M8 | retry rebuilds the body (`new FormData()`) | T1 (body identity) |
| M9 | a fresh `AbortController` + timer per attempt | T1 (signal identity), T11 |
| M10 | the camera calls `clearSession()` on any failed refresh | T4 (`clearSession` x0) |
| M11 | the camera calls `emitSessionInvalid()` after a failed refresh (double emit) | T3 (`emits` exactly 1), T4 |
| M12 | retry with the old token after a failed refresh | T3, T4 (`fetch` x1) |
| M13 | the retry bypasses the existing handling (`return response.json()` on any status) | T6, T7 |
| M14 | rethrow the refresh error instead of the 401 | T5 |
| M15 | the CTA only calls `navigation.goBack()` | S2 |
| M16 | a second inline `/image/identify` template for the retry | `consent/aiDispatchFence.s69` (inventory mismatch) |

---

## 6. GREEN gates (run from `SmartCompareApp/`; print tool versions first; check `node_modules/@babel/core` + `node_modules/.bin/jest` exist)

- **G1 new files.** `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/api.cameraAuthRetry.u13c.test.ts __tests__/screens/camera.authRequired.u13c.test.tsx`. Expect 2 suites passed, 21 tests passed (17 + 4), 0 snapshots.
- **G2 PIN subset.** The 19 suites in 5.4 by path, one `timeout -k 15 600` call. Measured at base (16:59): `Test Suites: 19 passed, 19 total` / `Tests: 8 todo, 297 passed, 305 total` / `Snapshots: 0 total`. Expect the identical line after GREEN.
- **G3 full suite.** `timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci`. Base, as given by the orchestrator (not re-run here; this agent is limited to subset runs): 357 passed of 360 suites, 3,485 tests, 42 snapshots. Cross-checks measured here: 360 test files match `testMatch`, and 42 `exports[` entries sit in 17 `.snap` files. Expect 359 passed of 362 suites (the same 3 non-passing suites as base and no others), base tests + 21, and `Snapshots: 42 passed, 42 total`, 0 written, 0 obsolete, 0 failed.
- **G4 tsc.** `timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit`. Exit 0, no output.
- **G5 eslint by path.** `timeout -k 15 600 node node_modules/eslint/bin/eslint.js $(git diff --name-only --relative) __tests__/api.cameraAuthRetry.u13c.test.ts __tests__/screens/camera.authRequired.u13c.test.tsx`. 0 errors.
- **G6/G7 untouched + no snapshot.** `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <scratch>/u13c/gate_untouched.py C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b` must print 4 PASS lines and rc=0. Its checks:
  - G7a: 18 must-not-change files byte-identical to base;
  - G7b: `api.ts` outside `identifyFromImages`;
  - G7c: no `.snap` path;
  - G7d: changed and untracked set within the 5 allowed paths.

  Measured at base: 4 PASS, rc=0. Also run `git diff --stat`: no whole-file diff (CRLF).
- **G8 mutants.** M1-M15 each red on its named test and restored with a sha256 match. M16 runs `aiDispatchFence` only.

---

## 7. Risks and stated limits

- **L1 Re-sending on device.** Re-sending the same FormData was measured on the real RN `FormData.js` and the real whatwg-fetch, with RN's `convertRequestBody` rule. The native multipart (OkHttp `openInputStream`, iOS form-data helper) was read but not run. Only a device shows a 401 -> retry uploading both JPEGs again. Device check: sign in, let the access token expire (or revoke it server side), take the two photos, and expect a result with no sign-in prompt.
- **L2 Double upload.** The guard runs after FastAPI parses the full multipart (2(c)). Each 401 therefore costs one complete upload (2 x ~1024 px JPEG at q 0.8) before the retry. The limiter and metering are not charged for the refused request (U13 T06/T19).
- **L3 Second 401 after a good refresh.** This means the backend rejected a freshly minted token: a deleted or banned user, or a `verify_token` exception, since `auth_routes.py:458-459` turns a Supabase blip into "rejected". Under R6 the user decides; an automatic logout here could sign users out during a Supabase blip (Q1).
- **L4 Transient refresh failure.** This shows the sign-in state (S1 as bound). Tapping "Sign In" then logs out a session that may still be valid. HistoryScreen does exactly this today (Q2).
- **L5 One-frame state.** On a dead session, `performRefresh` emits before the camera throws. The `'auth'` state may commit in the same frame that App swaps to the Auth stack. Not observable in jest.
- **L6 Out of scope, recorded for a follow-up.** The history-detail 401 is still a no-op that renders the generic "No comparison loaded" (`ResultsScreen.tsx:262-271`). The axios interceptor has already retried once by then.
- **L7 Production timing.** U13 is ACTIVE in production, so until this OTA ships, every camera compare after an idle longer than the access-token TTL shows "No comparison loaded" unless another axios call refreshed first.

---

## 8. Open questions (with recommendations)

- **Q1. What does a second 401 after a SUCCESSFUL refresh do?**
  - Options: (A) the R5/R6 sign-in state with a user-confirmed CTA; (B) the service itself calls `clearSession()` + `emitSessionInvalid()` and auto-routes to Auth.
  - RECOMMEND A. The axios path never logs out on a replayed 401 (2(b)). HistoryScreen asks the user. B would log users out on a Supabase verify blip (L3).
  - A adds a second `emitSessionInvalid()` call site (the ResultsScreen CTA, user-initiated). RECOMMEND updating the `sessionEvents.ts` header comment, comment-only, as allowed in section 4. The alternative, passing `onLogout` into Results, means editing `App.tsx`, which is pinned by source-scanning suites.
- **Q2. Transient refresh failure: sign-in state (as S1 binds) or the retryable timeout state?**
  - RECOMMEND keeping the sign-in state for this unit, as bound and consistent with HistoryScreen.
  - If Fable prefers timeout: it needs `sessionInvalid` exposed on `RefreshResult`. That edits `performRefresh`, the contract G7b pins, so it belongs in a separate unit.
- **Q3. Deadline: one 120 s budget for the whole call (R8, T11), or a fresh 120 s per attempt like axios's replay?**
  - RECOMMEND one shared budget. `IDENTIFY_TIMEOUT_MS` is documented as the whole identify deadline. It is the smallest diff (the existing controller, timer and `finally` already wrap the function). Per-attempt timers could hold the loader for up to ~6 min.
- **Q4. Retry on ANY 401, or only `code === 'AUTH_REQUIRED'`?**
  - RECOMMEND any 401, mirroring the interceptor. Strict mode and edge 401s also mean "bad bearer". T17 covers a 401 with no stored token.
- **Q5. Should the CTA also revoke the session server side (`authService.logout()`)?**
  - RECOMMEND no. Mirror HistoryScreen (`clearSession` + state downgrade). Revocation is the Profile logout's job.


---

## Review corrections (BINDING - supersede the body)

Adversarial review, Opus, 2026-10-03 17:02-17:40, read-and-measure only. Base re-verified: `git -C sc-s70-u4b rev-parse HEAD` -> `72b13bc53fb74445ea6e5782d7b8af67c938c399`, `status --porcelain | wc -l` -> `0`, branch `feature/s71-u13c-camera-401`; jest `29.7.0`, `node_modules/@babel/core` + `node_modules/.bin/jest` present. Scratch probe: `scratchpad/u13c/review/__tests__/adv_probe.test.ts` (real `api.ts` refresh singleton + captured interceptor, `authService` mocked at the boundary, an inline scratch CANDIDATE of this spec's GREEN with one injected mutant per variant), run `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci --roots <review> --modulePaths <app>/node_modules <file>` -> `Tests: 7 passed, 7 total` (output `review/adv_probe.out`). Notes: `review/notes.md`.

Re-measured and CONFIRMED (no correction): the camera call site and its base 401 behaviour (writer PROBE-1 re-run: `fetchCalls 1, refreshCalls 0, "Server error 401", status 401, AUTH_REQUIRED, classify auth`; `awk 'NR>=252&&NR<=374' api.ts | grep -c "getOrStartRefresh\|refreshSession"` -> `0`); the single-flight contract (2(b)); backend body-before-guard (venv fastapi `0.141.1`, `fastapi/routing.py`: `body = await request.form()` precedes `solved_result = await solve_dependencies(...)`; `/identify` declares `images: List[UploadFile] = File(...)`, so the form path is taken); every live `/image/identify` 401 carries `code AUTH_REQUIRED` (`_refuse_paid_route`, and strict ON `_reject_or_anonymous` raises `detail={"code":"AUTH_REQUIRED",...}`, `auth_routes.py:409-422`); the FormData re-send (writer probe re-run, identical P1/P2/P3 lines; `convertRequestBody.js`: `if (body instanceof FormData) return {formData: body.getParts()}`, called per send by `RCTNetworking.ios.js:42` / `RCTNetworking.android.js:72`; RN `Libraries/Network/fetch.js` = `require('whatwg-fetch')`; `expo/src/winter/runtime.native.ts` installs only the FormData patch, no fetch); the writer's G2 base line (re-run: `Test Suites: 19 passed, 19 total` / `Tests: 8 todo, 297 passed, 305 total` / `Snapshots: 0 total`); `gate_untouched.py` at base (re-run: 4 PASS, rc=0); i18n keys `common.signInRequired`, `auth.signIn` flat in `en.json` and `ar.json` (python `json.load`).

### Corrections

1. **R8 / Q3 / T10: the written design does NOT bound the call at `IDENTIFY_TIMEOUT_MS`. Race the refresh WAIT against the signal.** Awaiting `getOrStartRefresh()` is not interrupted by `controller.abort()`, and the refresh POST is bounded only by the axios INSTANCE timeout (`api.ts:27` `timeout: 120000`; `authService.ts:739` "the 120s global axios timeout"; `refreshSession` calls `api.post('/api/v1/auth/refresh', {...})` with no per-call config). Measured (ADV-1, fake timers, 401 at t=100 s, refresh settles at t=230 s):
   ```
   ADV-1 [writer] {"settledAtMs":230000,"outcome":{"err":"TIMEOUT"},"fetchAtSettle":2,...,"refreshCalls":1}
   ADV-1 [race]   {"settledAtMs":120000,"outcome":{"err":"TIMEOUT"},"fetchAtSettle":1,"fetchCallsFinal":1,"refreshCalls":1}
   ```
   BINDING R8 (replaces the body's R8): one `AbortController` + one `IDENTIFY_TIMEOUT_MS` timer for the whole call (unchanged). The camera awaits `getOrStartRefresh()` RACED against `controller.signal` (P-A3's own sanctioned shape, `api.ts:169-170`: "A caller that wants to stop WAITING races this Promise"; the spec's own 2(b) says the same, yet its R8 does not race). The signal is never passed into the refresh. If the signal aborts first, the wait rejects with an `AbortError`-named error that the EXISTING catch maps to TIMEOUT, NO retry is sent, and the refresh keeps running to completion (it still persists or clears the session itself). The abort listener is removed when the race settles (`signal.addEventListener` / `removeEventListener`: RN's `AbortController` is `abort-controller` 3.0.0 + `event-target-shim` 5.0.1, the same API whatwg-fetch uses at `fetch.umd.js:627/632`). A refresh that rejects after the race was lost must not become an unhandled rejection. Place any helper AFTER `identifyFromImages`' closing brace and BEFORE the `/**\n * Get comparison history` JSDoc (keeps G7b's markers and the identify JSDoc attached; still inside the networkMatrix slice). R4's "a rejection from `getOrStartRefresh()` is caught" does NOT apply to this AbortError: it ends the call as TIMEOUT. REWRITE T10: fetch #1 gives 401, the refresh is a deferred that the test does NOT resolve; advance `IDENTIFY_TIMEOUT_MS + 1`; assert the call has ALREADY rejected `{code:'TIMEOUT'}`, `fetch` x1, `mockRefreshSession` x1. Then resolve the deferred `{success:true}` and flush: `fetch` still x1; a `process.on('unhandledRejection')` recorder installed for the test records nothing. Repeat with the deferred REJECTING after the abort (same assertions). New mutant **M21** "await the refresh, then fetch on the aborted signal" (the body's R8) is killed by T10.

2. **T16 misses a token carried on the thrown error outside `.response`.** A mutant that makes the error more axios-like, `err.config = { headers }` (the interceptor itself reads `error.config`), passes T16 as written. Measured (ADV-2, 401 -> refresh ok -> 401): `{"status":401,"specifiedCheckSeesToken":false,"deepCheckSeesToken":true}`. BINDING T16: (a) serialise the thrown error DEEPLY: every own property name, enumerable or not (`Object.getOwnPropertyNames`), recursively, cycle-safe, plus `JSON.stringify(err)`. None of it may contain `OLD-TOKEN` or `NEW-TOKEN`; (b) positive controls, or the test can pass vacuously: the console spy recorded the `'=== IDENTIFY FROM IMAGES ==='` dev log (proves the `__DEV__ = true` toggle took effect), and `fetch.mock.calls[0][1].headers.Authorization === 'Bearer OLD-TOKEN'` (proves a token existed to leak); (c) T16 asserts NO outcome (it uses `.catch(() => {})`), so it stays a PIN at base. Note `__tests__/setup.ts:43-44` replaces `console.warn` / `console.error` with no-ops, and `__mocks__/sentry-react-native.ts` exports plain functions, not `jest.fn`, so the per-file `jest.fn` Sentry mock the body names is required. New mutant **M18** `err.config = { headers }` is killed by T16(a).

3. **Response fakes must be single-read, as whatwg-fetch is.** whatwg-fetch `consumed()` (`fetch.umd.js:173-178`): a second `text()` / `json()` on the same Response rejects `TypeError('Already read')`, and `classifyLoadFailure` maps an error with no `.response` to `'timeout'` (`failureClassification.ts:59`). A GREEN that reads the first 401's body twice (for example, once at the existing `:309` and again to build the failed-refresh error) passes the body's re-readable fakes but shows the retryable timeout state on a device instead of the sign-in state. Measured (ADV-3, transient refresh failure):
   ```
   {"rereadable":{"name":"Error","msg":"Server error 401","status":401,"classify":"auth"},
    "singleRead":{"name":"TypeError","msg":"Already read","classify":"timeout"}}
   ```
   BINDING: every response fake in `api.cameraAuthRetry.u13c.test.ts` is single-read: a second `text()` or `json()` call on the same object rejects `TypeError('Already read')`. Requirement added to R3/R4: each response body is read at most once. New mutant **M19** (double read) is killed by T4 and T3 with these fakes.

4. **No 403 test: "refresh on 401 OR 403" survives.** The non-401 PINs are 500 (T13), 429 (T15) and a TypeError (T14). A mutant gated on `status === 401 || status === 403` passes all of them (`grep -n "403" U13C_CAMERA_401_SPEC.md` before this section -> one hit, line 54, the line-number cite `bootOptimistic.a3.test.ts:403-407`; no 403 status anywhere). BINDING: add PIN **T18** `403 first: existing axios-shaped error, no refresh`. Body `{"success":false,"code":"FORBIDDEN","error":"x"}`. Asserts: rejects `Server error 403` with `response.status 403`; `fetch` x1; `mockRefreshSession` x0. New mutant **M17** (refresh on 403) is killed by T18.

5. **Q4 is not pinned: an AUTH_REQUIRED-only trigger survives.** Every 401 fixture in 5.1 carries the AUTH_REQUIRED envelope. BINDING (Q4 = any 401): add RED **T19** `a 401 without the AUTH_REQUIRED envelope still refreshes and retries`. First response: 401 with the non-JSON body `Unauthorized`, then 200. Asserts: resolves the 200 data, refresh x1, and retry headers `toEqual({Authorization:'Bearer NEW-TOKEN'})`. RED at base: refresh x0, as in PROBE-1. New mutant **M22** (`code === 'AUTH_REQUIRED'` gate) is killed by T19.

6. **T17 is not a PIN as written.** Its clause "a 401 with no stored token still takes R1 (refresh x1)" is RED at base: identify contains 0 refresh calls (the `grep -c` above), and PROBE-1 gives `refreshCalls 0`. BINDING: split it.
   - **T17a** (PIN): the first request's shape. Keys are `['method','body','headers','signal']`; headers are `{}` when `getToken` gives `null`, and `{Authorization:'Bearer OLD-TOKEN'}` otherwise.
   - **T17b** (RED): with `getToken` giving `null` first and `NEW-TOKEN` after the refresh, a 401 then 200 gives: first headers `{}`, refresh x1, retry headers `{Authorization:'Bearer NEW-TOKEN'}`, and the call resolves.

7. **"Unit tests can only pin body IDENTITY" (2(d)) is wrong. Pin the part count too.** Node's FormData in this jest env supports `getAll`. Measured (ADV-6, 401 -> 200): `{"sameBody":true,"partsAtRetry":2,"manipulateCalls":2}`. A retry that re-appends to the SAME instance keeps identity but sends 4 parts. A retry that re-runs `manipulateAsync` keeps identity too. BINDING T1 additions:
   - `manipulateAsync` is called exactly 2 times for 2 URIs across the whole call;
   - `calls[1][1].body.getAll('images').length === 2`.

   New mutant **M20** (re-append to the same FormData) is killed by T1. A recursive retry (`return identifyFromImages(...)`) is killed by T1 (manipulate x4) and by `aiDispatchFence` (a new `src/services/api.ts | call:identifyFromImages | ungated` row).

8. **G2 is missing 19 suites that read or render ResultsScreen, and one pins a count this unit can break.** `rtl/directionalIconWiring.contract.test.ts:20,48-49` pins EXACTLY 3 `<ArrowLeft` sites in `ResultsScreen.tsx`, all wrapped in `DirectionalIcon`. A sign-in state given its own header would make 4 and turn the suite red. BINDING R6: the auth state renders through the EXISTING `if (!result || loadError)` return (the title ternary, the CTA ternary, the `emptyStateContainer` testID ternary). No new header, no new `ArrowLeft`, no new top-level return. ADD as **G2b**, one `timeout -k 15 600` call, measured at base 17:27:
   - the suites: `rtl/directionalIconWiring.contract`, `Results.memo.m21`, `ResultsEntryParams.a18`, `ResultsScreen.comparisonId.m18`, `ResultsScreen.demographicsCopy.w314`, `ResultsScreen.guards`, `ResultsScreen.redesign`, `ResultsScreen.usageFetch.a15`, `ResultsScreen.historyFloor.a17`, `ResultsScreen.pushPrePrompt.u6`, `screens/ResultsScreen.bundle_c_integration`, `screens/ResultsScreen.integration`, `screens/ResultsScreen.no_estimated_copy`, `screens/ResultsScreen`, `screens/ResultsScreen.weird_mode`, `services/pushNavigation.w315`, `services/pushPrompt.s69`, `HomeScreen.bundleB.contract`, `ShareBottomSheet.deviceFingerprint.w3-3`;
   - the base line: `Test Suites: 19 passed, 19 total` / `Tests: 5 todo, 205 passed, 210 total` / `Snapshots: 0 total`. Expect the identical line after GREEN.

   The suites that read `api.ts` source (`errorCopy.a11`, `bootSentryOrder.w312`, `getPreferences.emptyObject`, `ProfileScreen.optimistic`, `HomeScreen.bundleE.contract`, `api.getComparison.comparisonId.m18`) only read code outside `identifyFromImages`, which G7b keeps byte-identical. G3 covers them.

9. **The race question and "exactly once": parity holds; one claim is qualified.**
   - **Concurrent callers.** A camera 401 and an interceptor 401 join one refresh. Measured (ADV-5): `{"refreshCallsWhilePending":1,"refreshCallsTotal":1,"axiosReplayAuth":"Bearer NEW-TOKEN","cameraRetryAuth":"Bearer NEW-TOKEN","emits":0}`.
   - **Sequential callers.** A camera 401 that arrives after another caller's refresh has SETTLED starts a new refresh. That is not a double spend: `refreshSession` awaits `saveToken` and `SecureStore.setItemAsync(REFRESH_TOKEN_KEY, ...)` before it resolves (`authService.ts:500-505`), and `getOrStartRefresh` only clears the singleton in `.finally` after that, so the second refresh presents the rotated token.
   - **Late 401 after a dead session.** After a dead-session refresh, a late 401 clears and emits AGAIN. The base interceptor does exactly this. Measured (ADV-4, captured interceptor, `sessionInvalid` refresh): `{"afterFirst":{"refresh":1,"clear":1,"emits":1},"afterSecond":{"refresh":2,"clear":2,"emits":2}}`. App's listener sets the same three values each time (`App.tsx:279-286`), so it is idempotent.

   BINDING wording: "cleared and announced exactly once" (R4, T3) means once per `performRefresh` call, not once per session. Add **L8**: a camera 401 that lands after an earlier dead-session refresh repeats the clear and emit (harmless, interceptor parity). No code change; skipping the refresh when the session is already gone remains a non-goal.

10. **S2 must pin completion order, not call order.** "clear before emit (recorded)" does not kill a CTA that calls `clearSession()` without awaiting it. BINDING S2: `mockClearSession` returns a promise that resolves on a later macrotask and pushes `'clear-done'` when it resolves. The session listener pushes `'emit'`. Assert the order equals `['clear-done','emit']`. New mutant **M23** (un-awaited `clearSession` in the CTA) is killed by S2.

11. **Q2's rationale is wrong; the ruling stands.** "The timeout option would need `sessionInvalid` exposed on `RefreshResult`, which edits `performRefresh`" is false. `performRefresh` clears the stored session on every dead path: `sessionInvalid` (`api.ts:123-132`) and a throw (`:144-152`). It also clears on "Session ended during refresh" via the logout that bumped the epoch (`authService.ts:479-497`, `clearSession` `:626-637`). So `getToken()` after a failed refresh tells "transient" (token still stored) from "dead" (cleared) without touching G7b. S1 binds the sign-in state for any failed refresh, so this unit keeps the sign-in state (Q2 below). The `getToken()` distinction is recorded as the follow-up route, not built here.

### Updated counts and gates (supersede 5.3, 5.5, G1, G3)

- **Service file**, 20 tests:
  - RED: T1-T11 with T10 rewritten (#1), T17b, T19;
  - PIN: T12-T16 with T16 rewritten (#2), T17a, T18.
- **Screen file**, 4 tests: RED S1 and S2 (S2 rewritten, #10); PIN S3 and S4.
- **Expected RED run:** 15 failing on assertions (T1-T11, T17b, T19, S1, S2) and 9 passing (T12-T16, T17a, T18, S3, S4). The RED agent pastes each failure message. For T10 the message must show a pending or late result, not a harness error.
- **G1:** `Test Suites: 2 passed` / `Tests: 24 passed`, 0 snapshots.
- **G3:** base tests + 24.
- **G2b:** as in #8.
- **Mutants:** the table gains M17-M23 (#1-#7, #10).
  - M7 is killed by T16(a) as well as the console spy.
  - M9 is still killed by T1 (signal identity) and T11.
- **G8:** runs M1-M15 and M17-M23 on the two new files; M16 runs on `aiDispatchFence` only.

### Open questions: RECOMMENDATIONS

- **Q1: A.** The second 401 after a successful refresh shows the sign-in state with a user-confirmed CTA: `await clearSession()`, then `emitSessionInvalid()`. B emits from the service on a 401 the backend can produce for a Supabase verify blip (`auth_routes.py:458-459`: any exception becomes `_reject_or_anonymous`, which becomes a 401 under U13). The axios path never logs out on a replayed 401 (`api.ts:237-241`). The `sessionEvents.ts` header comment ("exactly ONE emission site") gets a comment-only update naming the user-initiated ResultsScreen CTA as the second site. `App.sessionInvalid.m18.test.ts:108` only requires `api.ts` to contain `emitSessionInvalid`, so nothing pins exclusivity. The CTA handler is an inline async arrow, the HistoryScreen pattern; no new hook after the `if (loadingResult)` early return at `:728`. eslint-config-expo enables `react-hooks` recommended (`flat/utils/react.js`), so G5 would catch a misplaced hook.
- **Q2: sign-in state** (S1 binds it). Correct the rationale as in #11. The `getToken()` transient/dead split is a separate follow-up and needs no `performRefresh` edit.
- **Q3: one shared 120 s budget, ENFORCED by racing the refresh wait** (#1). The body's version measured 230 s. Per-attempt timers are rejected; T11 stays.
- **Q4: any 401**, mirroring the interceptor (`api.ts:222`). Pinned by T19 (#5). Today every live `/image/identify` 401 carries AUTH_REQUIRED anyway.
- **Q5: no server revocation.** `authService.logout()` awaits an in-flight refresh within a bound, then POSTs `/auth/logout` (`authService.ts:272-297`). That adds network work and a wait to a "Sign In" tap. HistoryScreen's CTA is local only (`HistoryScreen.tsx:916-917`). Revocation stays with the Profile logout.

## Orchestrator rulings (BINDING - supersede the review corrections and the body; 2026-10-03 17:40)

Review verdict APPROVED_WITH_CORRECTIONS; corrections 1-11 are accepted as written and bind the RED and GREEN agents. Rulings on the open questions:

- **UR1 (Q1 = A).** A second 401 after a successful refresh is thrown by the service as the existing 401 error; ResultsScreen shows a camera-only sign-in state built from the existing i18n keys (title common.signInRequired, CTA auth.signIn) reusing the existing empty-state return (correction 8: no new header, no new ArrowLeft); the CTA awaits clearSession() and then calls emitSessionInvalid() (correction 10 pins the order). sessionEvents.ts gets the comment-only update about the second emission site.
- **UR2 (Q2).** A failed refresh, transient or dead, shows the same sign-in state (correction 11: no performRefresh edit).
- **UR3 (Q3, correction 1).** One shared IDENTIFY_TIMEOUT_MS budget: the refresh WAIT is raced against controller.signal (the P-A3 shape at api.ts:169-170); the signal is never passed into the refresh; an abort during the wait maps to TIMEOUT with no retry; the listener is removed when the race settles; no unhandled rejection.
- **UR4 (Q4, correction 5).** Any 401 triggers the single refresh, regardless of body shape; a 403 never does (correction 4).
- **UR5 (Q5).** No server-side revocation from the CTA.
- **UR6 (files).** RED writes only the two new test files of section 5 (the service file and the screen file) and nothing else; GREEN touches only src/services/api.ts (identifyFromImages and its helpers), src/screens/ResultsScreen.tsx (the auth state), src/services/sessionEvents.ts (comment only); the aiDispatchFence (exactly one /image/identify literal inside identifyFromImages) and bootOptimistic (the zero-argument getOrStartRefresh) pins stay green; no snapshot, no i18n key, no app.json / eas.json / package.json / lock change.
- **UR7 (gates).** The RED counts of the review (service file 20 nodes: 13 RED + 7 PIN; screen file 4: 2 RED + 2 PIN); G1, G2 and G2b (the 19 ResultsScreen suites), G3 the FULL suite with totals derived from base (357 passed of 360 suites, 3,485 tests, 42 snapshots, plus the 24 new nodes), tsc, eslint by path, gate_untouched.py; mutants M1-M23 as corrected.
- **UR8 (shipping).** OTA-capable; must be in the store binary; after merge the preview OTA from main is the tester lever (npm ls first).

## Orchestrator gate on the RED tests (BINDING - supersedes everything above where they differ; 2026-10-03 18:43)

Gate: **PASS.** Two files under SmartCompareApp/__tests__, FROZEN from here on: api.cameraAuthRetry.u13c.test.ts (sha256 b76227a0de3842fd...; RED T1-T11, T17b, T19; PIN T12-T16, T17a, T18) and screens/camera.authRequired.u13c.test.tsx (ed0d1bffbcab260b...; RED S1, S2; PIN S3, S4). At base 72b13bc5: 15 RED each for the stated reason, 9 PIN green; the 40-suite neighbour run and the FULL suite fail only on the 15 REDs; tsc clean; eslint 0 errors; no .snap; the satisfiability sketch turns all 24 nodes green and kills M1-M11, M13-M15, M17-M23 plus the UNHANDLED extra (M12 and M16 belong to existing suites). Deviations D1-D7 accepted: the unhandled-rejection guard is the real-macrotask yield inside T10 (a process recorder never fires in this jest sandbox), T10 runs both late-refresh passes in one node, the stricter assertions of D4 and the extra-fetch guard of D5.

- **UG1.** GREEN edits only src/services/api.ts (identifyFromImages and its private helpers), src/screens/ResultsScreen.tsx (the camera-only auth state through the existing empty-state return, testID results-auth-signin on the CTA, order clearSession then emitSessionInvalid) and src/services/sessionEvents.ts (comment only). No test file, mock, config, i18n catalog, .snap, app.json, eas.json, package.json or lock changes.
- **UG2 (targets).** After GREEN: Test Suites 359 passed, 3 skipped, 362 total; Tests 3,509 passed, 13 skipped, 13 todo, 3,535 total; Snapshots 42 passed; tsc 0; eslint 0 errors on the changed files; gate_untouched.py PASS on G7a-G7c (G7d allows the spec doc); aiDispatchFence, bootOptimistic and rtl/directionalIconWiring green.
- **UG3 (mutants).** M1-M23 of the spec as corrected (M12, M16 on their owning suites) plus the UNHANDLED extra, each on the GREEN tree, byte copy, mutate, run the named files, must FAIL, restore, sha256 equal; never git checkout --.
- **UG4 (process).** GREEN, then two Opus adversaries (auth-flow lens: races with the interceptor, the single-use refresh token, the deadline, the dead-session double emit; engineering lens: gates, mutants, hygiene), fix, orchestrator diff review, commit, PR, merge on green. OTA-capable and must be in the store binary; the preview OTA from main (after npm ls) is the tester lever.
