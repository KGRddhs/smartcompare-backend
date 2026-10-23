# S81-08 CLIENT-FIRST-OTA: adversarial spec review

- Reviewer: adversarial spec reviewer (Opus 5.5), 2026-10-23.
- Spec: `.qa-s80/S81-08_UNIT_SPEC.md`, sha256 `49c05a18482525c0c2a013051036dadeb0411181673ed214b6b7670b06434971`
  (re-hashed at the start and before reporting: unchanged, 792 lines).
- Worktree `sc-s81-s08`, HEAD == base `dfc6502f791cdccbf0a620041f66888a734015d3`; `git status --short` EMPTY
  before and after (this file is the only write, under the gitignored `.qa-s80/`).
- Junction health: `SmartCompareApp/node_modules` is a JUNCTION to the clone; `node_modules/@babel/core/package.json`
  and `node_modules/.bin/jest` present (measured).
- Box state: `node -e 0` 16.5 s, then 4.9 s (slow-spawn pathology, threshold 1.5 s). NO jest, tsc, eslint or pytest
  was run by this review (one jest at a time on a box that slow would starve the sibling lanes). Every finding
  below is a static measurement at the base sha (Read / Grep / `git show dfc6502f:`) plus two stdlib probes in
  `<scratchpad>/S81-08-review/probe1.py`. The FULL jest baseline (3,694 passed, only the 4 nativeBundle.w37 drift
  nodes red) is NOT MEASURED here; the spec's 48-suite figure (454/458) and the 25-file backend figure (1899
  passed) are cited, not re-measured.
- Inputs read: s81-common.txt, PLAN_S81.md (Standing constraints, VERIFY corrections, F1-F4, Milestones S81-05 /
  S81-08 / S81-09 / S81-11, owner decisions 1-12), RULINGS_R0.md, DEFECT_LEDGER.md (no S81-08 row yet),
  ledger.md (newest lines to 16:03), specs/S81_08_BRIEF.md, RULINGS_S81_05.md, GATE_S81_05.md,
  RULINGS_FIX1_S81_05.md, runs/research/A7.json + R5.json (findings), the S81-05 leaf at `e9fd7148`.

## Verdict: APPROVE_WITH_CHANGES

The base-state tables are, with two cite slips, accurate at `dfc6502f` (every api.ts / authService / aiConsent /
deviceFingerprint / usageService / PaywallScreen / HomeScreen / i18n line I re-measured matches; the S81-05
header names, the 64-hex rule, the 1-3 ASCII digit rule and the lower-case uuid4 round trip match
`git show e9fd7148:app/utils/request_context.py:72-147`; probe P1 confirms the client regex and the server parser
agree on upper-case NSUUID, lower-case v4, the root-mock counter id and a v1 id). But the spec's pin prediction
misses two deterministic red nodes (the AI dispatch fence and the paywall line cap), one mutant it claims killed
survives, several rows are time bombs against the dated cutoff, two existing suites that partially mock
`deviceFingerprint` stay green only under an implementation rule the spec never states, and three design points
(the pill reset beside a never-resetting lifetime count, the device id written into AsyncStorage by the consent
mirror, the legacy osBuildId composition broadcast on every request) need an orchestrator ruling before RED.

## 1. Refuted claims (measured truth, file:line at dfc6502f)

- RF1 (MAJOR, spec 1.8 / 4.2 "aiDispatchFence.s69 (5) stays green and unedited"). REFUTED.
  `__tests__/consent/aiDispatchFence.s69.test.ts` walks EVERY `src/**/*.ts(x)` file (`sourceFiles`, :83-97),
  records every string literal whose text includes `/text/compare`, `/text/quick`, `/url/compare` (`OPENAI_ROUTES`
  :66-74, the literal visitor :252-263; a literal outside an api.ts dispatch function is classified `ungated`,
  :239-246) and pins the inventory EXACTLY (:296-325). Spec 2.2 adds `src/services/requestContext.ts` with
  `COMPARE_REQUEST_PATHS` = the literals `/api/v1/text/compare`, `/api/v1/url/compare`, `/api/v1/text/quick`
  (2.1 row 4): three new `ungated` endpoint sites, so the node "the dispatch-site inventory over App.tsx + src/
  is exactly the pinned one" goes red at GREEN. Not in 4.1.
- RF2 (MAJOR, spec 4.1 E4 is the only paywall-fence change). REFUTED.
  `__tests__/screens/paywall.noSubscriptionUi.s69.test.ts:104-110` (T2-a2) caps `src/screens/PaywallScreen.tsx`
  at `src.split(/\r?\n/).length <= 250`. Measured: 248 CRLF lines plus the trailing newline = 249 elements, so
  ONE line of headroom. Spec 3.9 needs at least: the import of the two helpers, a second piece of state for the
  raw fetched status (today `fetched` stores only `stateFromStatus(status)`, :80-95, so the raw `resets_at` is
  not retained), the `resetAt` line and the per-state branch. T2-a2 reddens at GREEN.
- RF3 (MAJOR, spec 4.2 "authService.socialFingerprint.w3-3 ... stay green and unedited"). TRUE ONLY UNDER AN
  UNSTATED RULE. That suite mocks `../src/services/deviceFingerprint` with `getDeviceFingerprint` ONLY
  (`authService.socialFingerprint.w3-3.test.ts:71-72`). Spec 3.5 reads `legacyDeviceFingerprintHash()` "in its
  own try ... only while `legacyFingerprintHeaderActive()`": if the window gate is evaluated outside the try,
  `legacyFingerprintHeaderActive` is `undefined` in that suite, both social sign-ins throw a TypeError and
  C1 / C2 / C4 / C6 redden. The same partial mock exists in `authService.logoutRefreshFirst.w1-4d.test.ts:51-53`,
  which runs the REAL axios instance and the REAL request interceptor with a stub adapter (:260-272) and is not
  in the spec's 48-suite base set, 4.2 or 7.2.
- RF4 (MAJOR, mutation table M15 "one builder's try removed: killed by B7"). REFUTED. B7 fails ALL four builders
  and expects headers == `{Authorization}`. With one builder's try removed, that builder's rejection rejects
  `applyContextHeaders`, which spec 3.4 wraps in the interceptor's own try, so the interceptor still returns
  `{Authorization}` and B7 stays green. No row has one builder failing while the others succeed, so M15 survives
  for every builder. The same gap leaves "buildContextHeaders loses its catch" unkillable on the camera and SSE
  paths (no row runs `identifyFromImages` or the SSE request with failing builders).
- RF5 (spec 4.1 E2 note "root mock has none -> still rejects"). INACCURATE. `__tests__/deviceFingerprint.test.ts`
  uses its LOCAL factory `jest.mock('expo-application', () => ({ applicationId: 'app.qaren.test' }))` (:18),
  not the root shim; and its line :126 asserts `.rejects.toBe(err)`, i.e. the SAME error object SecureStore
  threw. Spec 2.3 says only "No fallback value -> reject"; if GREEN rejects with a new error, :126 also moves and
  E2 is under-stated.
- RF6 (spec 1.2 cite). `node_modules/expo-application/build/Application.d.ts`: `getAndroidId(): string` is at :50
  and `getIosIdForVendorAsync(): Promise<string | null>` at :84 (the spec pairs the names with the lines in
  reverse). The root shim `__mocks__/expo-application.ts` also exports `nativeApplicationVersion` /
  `nativeBuildVersion` (1.7 says "applicationId only"); immaterial to the design.
- RF7 (spec 0 / 2.10(a) "headers the base server ignores"). WORDING. The base server READS `x-device-fingerprint`
  at `app/api/text_routes.py:1405` (`/text/quick`) and `app/api/image_routes.py:227` (`/image/identify`) under
  `ENABLE_ANON_USAGE_GATE`, for anonymous callers only; unreachable from a signed-in client
  (`require_paid_route_user`, image_routes.py:192; `/text/quick` is admin-only; ENABLE_COMPARE_AUTH_REQUIRED ON).
  Behaviour claim holds; the sentence should say "never reached for a signed-in client".
- RF8 (MAJOR, brief vs spec 2.5 / E1 / A9). CONTRADICTION. The brief item 2 says "every write of the id goes
  through expo-secure-store (never AsyncStorage)". Spec 2.5 / E1 write `deviceId` = the X-Device-Fingerprint
  header value into AsyncStorage TWICE (the account record `@qaren_ai_consent_<userId>` and the mirror
  `@qaren_device_ai_consent`); A9 pins only the `getDeviceFingerprint()` path, so the contradiction is unpinned.
  Worse, when the id came from the IDFV / ANDROID_ID fallback, `recordAiConsent` persists the fallback hash in
  AsyncStorage, contradicting spec 2.3 "NEVER persisted anywhere (no AsyncStorage ...)". (The brief's item 3
  itself names `{version, at, deviceId}`, so the brief is internally inconsistent; it needs a ruling.)
- RF9 (MAJOR, spec 2.7 pill rule, G8; also G5 / the sheet `open` state). HONESTY DEFECT. The pill count is the
  LIFETIME counter: `useComparisonCounter.ts:22-25` hydrates only `used.lifetime`, `:89` `total = lifetime_free`,
  `HomeScreen.tsx:938` `baseFreeRemaining = max(0, total - used)`; the lifetime counter never resets. Rendering
  "resets HH:MM" beside "2/3 free" claims the lifetime free comparisons refresh at that time. PLAN_S81.md:148:
  S81-09 adds `resets_at` to `/usage/status` (under `ENABLE_RIYADH_RESET`) and retires the lifetime cap under a
  SEPARATE flag (`ENABLE_DEVICE_DAILY_QUOTA`), so a window where `resets_at` is present and the pill still counts
  lifetime is reachable. The sheet's `open` state counts lifetime-free compares too (`openRemaining`,
  PaywallScreen.tsx:51-56). The spec never consumes the `scope` field the brief says S81-09 sends. The EN a11y
  copy "plus {{bonus}} bonus. They refresh at {{time}}" also claims the monthly referral bonus refreshes daily.
- RF10 (spec 2.10(d) "a header builder can never block, delay past its own awaits, or fail a request"). UNPINNED.
  The awaits are unbounded (SecureStore read, two to three AsyncStorage reads, `getSavedUser`) and spec 3.4 runs
  them serially AFTER `getToken()` on every axios request; no row uses a never-settling builder. Low likelihood
  (the mocks and the native modules settle), but the claim as written is not proven.
- RF11 (spec 9.2 stated limit "the legacy header ... doubles the fingerprint bytes on every request and keeps the
  near-fingerprinting composition on the wire"). A STATED LIMIT THAT IS A DEFECT. No consumer needs the legacy
  value outside the paths that match STORED rows: register (`_inherit_device_counter`, auth_routes.py:499-537),
  social sign-in (:540-579) and the referral SAME_DEVICE checks (referral_service.py:680-802,
  abuse_detection_service.py:132-249, fed by the share body). S81-09 drops the stored-hash step (PLAN_S81.md:102)
  and keys its daily counters fresh per Riyadh day, so it never needs the legacy value on a compare. Build 3 sends
  the osBuildId composition on 3 call sites; the spec moves it onto EVERY request for about five months
  (R5 finding 16: an OS build string mixed into an id "sits close to the fingerprinting line").
- RF12 (spec 0.1 / 2.6 "exposed to the caller for SF1 / CL3"). PARTIAL. Only `streamComparison` exposes the id.
  `identifyFromImages` mints one per call and returns `ImageIdentifyResult` without it; Link mode
  (HomeScreen.tsx:560-572) gets its id inside the interceptor where no caller can read it. CL3 (feedback on the
  Results screen) needs the id for camera and link compares too, so another api.ts / HomeScreen change would be
  owed later.

## 2. Corrections (binding unless the orchestrator rules otherwise)

- C1 (fixes RF1 and RF12). Drop `COMPARE_REQUEST_PATHS`. Mint the id at the call sites: `streamComparison` (as
  specified), `identifyFromImages` (as specified, and expose it: e.g. an optional `onCompareRequestId` callback
  argument, additive), Link mode in `HomeScreen.handleUrlCompare` (pass
  `headers: { 'X-Compare-Request-Id': id }` in the existing config; the interceptor's only-if-absent rule keeps
  it), `compareTextPair` inside api.ts (0 callers; optional). The interceptor then adds only the device /
  legacy / consent headers. M11 and B3 fall away; the fence inventory is unchanged (no new route literal).
  If the orchestrator keeps the interceptor path list instead: list the fence as deliberate change E5 (three new
  `ungated` rows for `src/services/requestContext.ts` with the reason line the fence header demands, :43-45),
  drop the dead `/api/v1/text/quick` entry (no client caller), and never write the paths as a regex literal to
  dodge the fence.
- C2 (fixes RF2). Either list T2-a2 as deliberate change E6 (raise the cap to a stated number with a reason line),
  or move the sheet rule into a pure helper in `src/utils/resetTime.ts` (e.g. `resetLineKey(state, resetAt)`)
  and keep the net PaywallScreen.tsx growth at one line. Measure `split(/\r?\n/).length` on the GREEN bytes.
- C3 (fixes RF3). Rule: every call from `authService.ts` or `requestContext.ts` to a NEW `deviceFingerprint`
  export (`legacyFingerprintHeaderActive`, `legacyDeviceFingerprintHash`) sits INSIDE its own try, so a module
  mocked with `getDeviceFingerprint` only degrades to "no legacy header". Add two PIN rows: I5 (deviceFingerprint
  mocked with `getDeviceFingerprint` only: both social POSTs go out with X-Device-Fingerprint and no legacy
  header) and B13 (same partial mock: the interceptor resolves with Authorization + X-Device-Fingerprint +
  consent). Add `authService.logoutRefreshFirst.w1-4d`, `authService.logoutRevoke.w1-4` and
  `api.expiredTokenRetry.b2` (the real-interceptor suites) to 4.2 and to the 7.2(c) set.
- C4 (fixes RF4). Add B14: each builder failing ALONE (device, legacy, consent, id) leaves the other three headers
  present (four sub-rows; kills M15 per builder). Add C5: all builders failing -> the camera attempt 1 still goes
  out with `{Authorization}` only, and the U13c 401 retry still runs; add D6: all builders failing -> the SSE
  request still goes out over `expo/fetch` (no REST fallback triggered by a builder) and `runRestCompare` is not
  called. These also pin the camera failure-envelope interaction: a builder error must never surface as
  `identifyFromImages` rejecting (ResultsScreen would show the photo-blaming copy).
- C5 (time bomb). Every row that expects the legacy header or depends on the window (A10, B1, B4, B11, B12, C1,
  C2, D1, I1, I2, I3) pins `Date.now` to a fixed pre-cutoff instant (e.g. `Date.UTC(2026, 9, 23)`). Built on the
  real clock they turn red on main on 2027-04-01 00:00 Riyadh, and the I2 / I3 PINs silently become vacuous (no
  legacy read is possible after the cutoff, so a mis-placed read can no longer be caught).
- C6 (fixes RF8). The consent mirror stores a DERIVED tag, never the header value:
  `deviceTag = sha256('qaren-ai-consent|' + fingerprint)` (or keep the mirror in SecureStore). Drop `deviceId`
  from the ACCOUNT record (the account branch never reads it). Write no mirror when the id came from the
  fallback (expose the source, e.g. `getDeviceIdentity(): Promise<{ hash, source: 'stored' | 'fallback' }>`
  beside the unchanged `getDeviceFingerprint()`). Add A9b: after Agree, no AsyncStorage value equals the
  X-Device-Fingerprint value; and E11: SecureStore throws + IDFV present -> account record written, no mirror.
- C7 (null user; unstated). Spec 2.5 makes `hasCurrentAiConsent(null)` true when a current mirror exists, which
  changes `ensureAiConsent` for a signed-out user (today R3: "the sheet still shows" for no saved user; T1.8 stays
  green only because it plants no mirror). Rule it and pin it (E10). Also rule the HEADER for a signed-out device
  and pin that a `getSavedUser` THROW omits the consent header even though the global setup mock's
  `hasCurrentAiConsent` returns true (B15): that distinction is exactly what keeps the six u13c E3 nodes green;
  an implementation that copies aiConsent's own swallowing `currentUserId()` (aiConsent.ts:100-107) would map
  the throw to `null`, call the mock, send `X-AI-Consent-Version: 2` and redden E3.
- C8 (fixes RF11; needs a ruling). Send `X-Device-Fingerprint-Legacy` only where a stored row is matched:
  `/api/v1/auth/register`, both social sign-ins, `/api/v1/referrals/share` (and the invite / quiz routes if the
  backend reader matches there). B1 / C1 / D1 then expect no legacy header on usage, compare, camera and SSE;
  B12 / I1 keep it; restate 9.2. If the orchestrator keeps "every request", state the App Review / privacy
  exposure as a contract risk in the CLAUDE.md row.
- C9 (fixes RF9; needs a ruling). Render the reset time only when the counted axis is the daily one: the sheet
  `daily` state always; the sheet `open` / `unknown` states and the Home pill only when the server says the reset
  applies to what is counted (consume S81-09's `scope`, e.g. render iff `scope` names a daily axis), or defer the
  pill to S81-09's client half, which changes the count at the same time. G5 / G8 / G9 and the copy change with
  the ruling; the a11y copy must not say the bonus refreshes.
- C10 (probe P2). `formatResetClock` rounds to the nearest minute for retry-derived instants. With truncation, a
  device clock 5 s behind the server shows `23:59` for a `00:00` reset (P2: retry_after 3600 at 23:00:00.4
  Riyadh); rounding shows `00:00`. F5 gains `23:59:55 -> 00:00`. (`resets_at` absolute values are unaffected.)
- C11. RED rows never hard-code `'2'` for X-AI-Consent-Version; read `String(AI_CONSENT_VERSION)` from the module
  in scope. S81-12 bumps the constant in the same OTA and must update the `__tests__/setup.ts` mock
  (`aiConsentV2.s75` :180 compares the two), so literal `'2'` rows collide with a sibling unit.
- C12 (fixes RF10). Run the context build concurrently with `getToken()` (`Promise.all`) and bound the device-id
  read on the request path (e.g. a 1,000 ms race that omits the header on expiry), or state the unbounded await
  as a limit; add B16 with a never-settling `getDeviceFingerprint` under fake timers. Fewer serial awaits also
  shrink the microtask risk in C15.
- C13. D4: when `newCompareRequestId()` returns null, the REST config carries no `headers` key (today's object
  byte for byte, `api.ts:688-695`); pin it.
- C14 (missing mutants). M36 "the v4 regex check removed in `newCompareRequestId`": add B2b (randomUUID returns
  `00000000-0000-0000-0000-000000000001`, the root shim's shape -> no header on a compare request). M37 "the sheet
  prefers `initialUsage` over the fetched status": add a G row with both present and different instants. M38
  "the pill renders the raw `resetsAt` string without `resolveResetAt`": add G9b (a PAST `resets_at` -> no
  `home-header-counter-resets` node).
- C15 (unmeasured timing pins). The interceptor and the SSE path gain awaits. Add to 7.2(c) and to the
  `--runInBand` pairs: `api.settleTerminalLatch.a7` (fake timers + `microFlush(80)`, :117-122, :266-295),
  `api.networkMatrix.m18` (fake-timer camera / watchdog deadlines, :306-322, :443-483),
  `authService.logoutRefreshFirst.w1-4d` (real interceptor under fake timers, the 5 s bound, :610-654),
  `consent/aiDispatchFence.s69`, `screens/paywall.noSubscriptionUi.s69`, `rtl/textAlignLogical.contract`
  (any new pill style), `i18n/priceDigits.crossScreen.w414` (PIN 15: every `toLocaleString(` passes a locale),
  the `HomeScreen.bundleE.*` / `currentDesign.contract` source pins. Keep `api.cameraAuthRetry.u13c.test.ts:719`
  (fetch init keys exactly `['method', 'body', 'headers', 'signal']`) on the 4.2 list.
- C16. Fix RF5 / RF6 / RF7 wording; E2 states which error the no-fallback path rejects with (recommended: rethrow
  the ORIGINAL SecureStore error so :126 stays verbatim).
- C17 (RED design). B8 needs a recorder module for the legacy function while B11 / B12 / E9 need the REAL
  `deviceFingerprint`; in one file that needs `jest.isolateModules` + `jest.doMock` per row. State it so RED does
  not hoist one `jest.mock` that makes half the rows vacuous.
- C18 (optional, belt and braces). `src/services/sentry.ts:49` redacts request headers by NAME only
  (`authorization`, `x-admin-key`, `cookie`); add `x-device-fingerprint` and `x-device-fingerprint-legacy` if the
  change list may grow by one file. The 64-hex generic pattern (:44) already redacts them inside strings.

## 3. Blocking issues (rule before RED; BL4 before the OTA)

- BL1. C1: the compare-id path list collides with the AI dispatch fence; rule call-site minting (recommended) or a
  deliberate fence re-pin.
- BL2. C9: the reset time beside a lifetime count (pill) and in the lifetime-inclusive `open` sheet state is a false
  claim reachable once S81-09 sends `resets_at`; rule the axis signal (`scope`) or defer the pill.
- BL3. C6 + C7: the consent mirror writes the server-visible device id (and the fallback id) into AsyncStorage
  against the brief; and the signed-out semantics of the mirror and the header are unstated. Rule both.
- BL4 (OTA, not merge). Q1 / contract risk K1: no unit owns the UNFLAGGED backend reader of
  `X-Device-Fingerprint-Legacy` at register, social sign-in and the SAME_DEVICE checks; S81-09 flips AFTER the
  first OTA (PLAN_S81.md:185) and drops stored-hash matching, so it is not the vehicle. Create the unit
  (proposed S81-08b, additive, byte-identical for build 3 because build 3 never sends the header) and record the
  OTA precondition in DEFECT_LEDGER.

## 4. Contract risks

- K1. Transition order (spec Q1): until the backend reader lands, every post-OTA register / social sign-in stores
  the NEW value and inherits nothing from accounts that stored the legacy value; a pre-OTA referrer plus a post-OTA
  same-device invitee is not flagged SAME_DEVICE while `ENABLE_REFERRAL_SYSTEM` is ON. The runtime cutoff
  (2027-04-01 00:00 Riyadh) ends the legacy header regardless of backend progress.
- K2. One device consent (owner decision 2 extended to consent): account B, possibly a different person, is never
  shown the AI disclosure, and its X-AI-Consent-Version header routes it to Anthropic under S81-06 (consent >= 3).
  App Review 5.1.2(i) asks for explicit permission before sharing with third-party AI; this is an owner / legal
  ruling, and S81-12's policy text must say consent is per device.
- K3. S81-09 coupling: `useComparisonCounter` accepts `/usage/status` only when `used.lifetime` is a number
  (`useComparisonCounter.ts:22`); if S81-09 retires the lifetime fields under its flag, the hook drops the whole
  status (no `resetsAt`, and `canCompare` collapses to the local `used < 3` fallback, :81-82). S81-09's spec must
  keep `used.lifetime` numeric or ship the client half.
- K4. One id spans two server requests when the SSE stream fails and the REST fallback runs (and the stream may
  still complete server-side, #118); S81-22 / SF1 must not put a UNIQUE constraint on `compare_request_id`.
- K5. Privacy: the device id rides every axios request (auth, legal, events, history); S81-12 (privacy s8) and the
  App Privacy answers must describe it (spec Q9).
- K6. The 429 wire carries only `success / error / code / request_id` (+ `retry_after_seconds` / `Retry-After` for
  a positive int `retry_after`, and the B4 keys) at base (`error_handler.py` `http_exception_handler` /
  `_detail_retry_after`); `resets_at` and `scope` reach the client only through S81-09's allow-list.
- K7. Build-3 compatibility holds by construction: the unit ships only by OTA; no response the build-3 client reads
  changes; no native file is touched (expo-application 7.0.8 / expo-crypto / expo-secure-store already linked).

## 5. Pin collisions not listed in spec 4.1

1. `__tests__/consent/aiDispatchFence.s69.test.ts` "the dispatch-site inventory ... is exactly the pinned one"
   (RF1; deterministic red under spec 2.2).
2. `__tests__/screens/paywall.noSubscriptionUi.s69.test.ts` T2-a2 line cap 250 (RF2; 249 at base).
3. `__tests__/deviceFingerprint.test.ts:126` `.rejects.toBe(err)` (RF5; depends on the unstated rejection reason).
4. `__tests__/authService.socialFingerprint.w3-3.test.ts` C1 / C2 / C4 / C6 and
   `__tests__/authService.logoutRefreshFirst.w1-4d.test.ts` (partial `deviceFingerprint` mocks; RF3).
5. Six `api.cameraAuthRetry.u13c` E3 nodes stay green only if a `getSavedUser` throw omits the consent header
   (C7 / B15); the spec's prediction rests on that unstated rule.
6. Timing-sensitive suites under fake timers / fixed microtask budgets (C15): `api.settleTerminalLatch.a7`,
   `api.networkMatrix.m18`, `authService.logoutRefreshFirst.w1-4d`; unmeasured.
7. Sibling collision: literal `'2'` consent rows vs S81-12's version bump in the same OTA (C11).

## 6. Questions for the orchestrator

1. BL1 / C1: mint the compare id at the call sites (recommended; no fence change, exposes the Link-mode and
   camera ids for CL3) or keep the interceptor path list with a deliberate fence re-pin?
2. C8: legacy header only on register / social sign-in / referral share (recommended) or on every request as specified?
3. BL2 / C9: render the reset time only on a daily axis named by S81-09's `scope`, or defer the pill to S81-09's
   client half? And the sheet `open` / `unknown` states?
4. BL3 / C6: may the consent mirror hold the X-Device-Fingerprint value in AsyncStorage, or a derived tag
   (recommended)? Write a mirror for a fallback-derived id or not (recommended: not)?
5. BL3 / C7: does a current device mirror suppress the consent sheet for a signed-out user (a change to R3)? Is the
   consent header sent with no saved user?
6. BL4: which unit owns the unflagged backend legacy reader that must be live before the OTA (proposed S81-08b)?
7. K2: owner / legal ruling on per-device consent for a second account (and S81-12's wording).
8. C2: raise the PaywallScreen line cap (E6) or keep the sheet change in a helper?
9. Spec Q2-Q9: this review agrees with Q3 (empty capability list until S81-11 renders the as-of date), Q4 (reuse
   `device_fp_nonce`), Q5 (keep the mirror on deletion only if C6's derived tag is adopted; otherwise clear it),
   Q6 (no memo is acceptable once C12 bounds the awaits), Q8 (S81-09 puts an int `retry_after` in the USAGE_LIMIT
   detail); Q2 (runtime cutoff) is acceptable only with C5's fixed-clock rows and BL4 landed.
10. DEFECT_LEDGER: add the S81-08 row (client lane gaps from A5 / A7 / R5 / R6) and the S81-08b row.

## Not done in this review

No jest, tsc, eslint or pytest run (box `node -e 0` 16.5 s / 4.9 s); the FULL jest baseline, the 48-suite set and
the 25-file backend set are cited from the spec, NOT MEASURED; no in-place prototype (a review agent may not write
in the worktree beyond this file); the timing-pin risks in C15 are predicted, not measured; the Arabic copy is
unreviewed beyond the code points (every AR string stays [NATIVE READ]).
