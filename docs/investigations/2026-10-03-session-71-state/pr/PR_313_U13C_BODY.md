## U13c: camera `/image/identify` 401 -> one refresh -> one retry, plus a sign-in state (#298)

Client only (SmartCompareApp), JS only, OTA-capable. It must also be in the store binary. Base `main` 72b13bc5.

### Why
U13 (#297) is ACTIVE in production. Since then, `POST /api/v1/image/identify` answers **401 AUTH_REQUIRED** to any caller without a valid bearer, and it does so only after FastAPI has parsed the whole multipart upload. The camera path is a raw React Native `fetch` (whatwg-fetch), not axios, so the 401 refresh interceptor never runs on it. Today, the first camera compare after the access token expires shows **"No comparison loaded"**. `ENABLE_STRICT_OPTIONAL_AUTH` precondition (2) in CLAUDE.md is the same gap.

### What changes
**`src/services/api.ts`, inside `identifyFromImages` plus one private helper placed after it.** G7b keeps the rest of the file byte-identical: the refresh singleton, `performRefresh` and the interceptor.
- The URL is built once (`identifyUrl`) and reused, so `src` still has exactly one `/image/identify` literal (the `aiDispatchFence` inventory is unchanged).
- On a FIRST response with `status === 401` (any body, as the interceptor does; never 403):
  - read its body once;
  - wait for a token through the shared zero-argument `getOrStartRefresh()` single flight;
  - on `success` with a token, send exactly ONE retry. The retry uses the same URL, `POST`, the SAME FormData instance (no rebuild, no second `manipulateAsync`), headers `{ Authorization: 'Bearer <new>' }` and the SAME `controller.signal`.
- The retry's response goes through the existing handling unchanged:
  - 2xx returns the JSON;
  - 429 USAGE_LIMIT gives the H3 tag;
  - any other non-ok, a second 401 included, gives the existing axios-shaped `Server error <status>`.
- When the refresh fails (`success` false, no token, or a rejection), nothing is re-sent. The call throws the axios-shaped error built from the FIRST 401's already-read body (`response.status 401`, `data.code AUTH_REQUIRED`). A refresh rejection is never propagated, because its status belongs to `/auth/refresh`. The camera never calls `clearSession()` or `emitSessionInvalid()` itself; `performRefresh` already clears and announces a dead session once per refresh.
- One shared `IDENTIFY_TIMEOUT_MS` (120 s) deadline covers the whole call. `waitForIdentifyRefresh(signal)` races only the WAIT against `controller.signal` (the P-A3 shape). The signal is never passed into the refresh, which runs to completion and stores or clears the session itself. If the deadline fires during the wait, the call ends with the existing TIMEOUT error and sends no retry. The abort listener is removed when the race settles, and a refresh that settles after a lost race is handled, so no rejection goes unhandled.
- Any first status other than 401 takes exactly today's path. The first request keeps today's shape: option keys `[method, body, headers, signal]`, and headers `{}` when no token is stored.

**`src/screens/ResultsScreen.tsx`, the camera catch and the existing empty-state return only**
- `loadError` gains `'auth'`. In the CAMERA catch only, `classifyLoadFailure(err) === 'auth'` sets `'auth'` instead of `'generic'`. The USAGE_LIMIT and engine-outage checks before it are unchanged, and so is the history-detail catch.
- `'auth'` renders through the EXISTING `if (!result || loadError)` return. It adds no new header, no new `ArrowLeft` (`rtl/directionalIconWiring` still counts 3) and no new top-level return. Its parts:
  - container `testID="results-auth-state"`;
  - title `t('common.signInRequired')`, with no body line;
  - one CTA, `testID="results-auth-signin"`, label `t('auth.signIn')`.
- The CTA awaits `clearSession()` and then calls `emitSessionInvalid()`, so App's listener swaps to the Auth stack. This is the HistoryScreen pattern without an `onLogout` prop. There is no server revocation (UR5).
- No new i18n keys: both keys exist in `en.json` and `ar.json`.

**`src/services/sessionEvents.ts`: header comment only.** It names the user-initiated ResultsScreen CTA as a second emission site, next to the one automatic site (`performRefresh`).

**New tests (frozen at the RED gate, not edited since):**
- `__tests__/api.cameraAuthRetry.u13c.test.ts`: 20 nodes. RED: T1-T11, T17b, T19. PIN: T12-T16, T17a, T18. The response fakes are single-read, like whatwg-fetch.
- `__tests__/screens/camera.authRequired.u13c.test.tsx`: 4 nodes. RED: S1, S2. PIN: S3, S4.

### Rulings applied (spec `docs/investigations/2026-10-03-session-71-state/U13C_CAMERA_401_SPEC.md`)
- **UR1/UR2:** a second 401 after a good refresh, and any failed refresh (transient or dead), show the same user-confirmed sign-in state.
- **UR3:** one shared deadline, with the refresh wait raced against the signal.
- **UR4:** any 401 triggers the refresh; a 403 never does.
- **UR5:** no server revocation.
- **UR6/UG1:** only the three source files above change.

### Gates (fix round, 2026-10-03; jest 29.7.0, tsc 5.9.3, eslint v9.39.4, node v24.11.1; project tools by path under coreutils `timeout`)
- **G1**, the two new files: `Test Suites: 2 passed, 2 total` / `Tests: 24 passed, 24 total` / `Snapshots: 0 total`.
- **G2 + G2b + new**, 40 suites in one call: `Test Suites: 40 passed, 40 total` / `Tests: 13 todo, 526 passed, 539 total` / `Snapshots: 0 total`. These include the 11 auth-owning suites, run in a stable window.
- **G3, FULL suite:** `Test Suites: 3 skipped, 359 passed, 359 of 362 total` / `Tests: 13 skipped, 13 todo, 3509 passed, 3535 total` / `Snapshots: 42 passed, 42 total`. That is UG2 exactly: base plus the 24 new nodes, no FAIL line, and the tree sha-checked before and after.
- **tsc --noEmit:** rc 0, no output.
- **eslint** on the 3 changed files and the 2 new tests: 0 errors. Warnings per file are unchanged from base (api.ts 8, ResultsScreen.tsx 59, sessionEvents.ts 0).
- **gate_untouched.py:** G7a PASS (18 must-not-change files), G7b PASS (api.ts outside `identifyFromImages`), G7c PASS (no `.snap`). G7d flags only the untracked spec doc, which UG2 allows.
- **Mutants (UG3):**
  - M1-M23 and the UNHANDLED extra were each killed on the GREEN tree by the named tests. M12 and M16 were killed on their owning suites. Every restore sha256 matched.
  - The engineering adversary independently re-killed all of them plus A1, A1b, A3, A4, A4b, A5, A5c, A7, A8, A9, A10, A11 and A14.
  - This fix round re-killed the ResultsScreen mutants on the final ResultsScreen bytes: M6, M15, M23, A3, A4, A4b, A5c, A8, A10 and A11. All 16 restores sha256 OK.

### Review
Two Opus adversaries reviewed the change.
- **Auth-flow lens:** races with the interceptor, the single-use refresh token, the deadline, and the dead-session double emit. It measured on the real whatwg-fetch 3.6.20 and the RN abort-controller polyfill.
- **Engineering lens:** gates, mutants and hygiene.

Neither found a defect. The fix round applied the comment-accuracy findings, which are comment-only:
- a failed refresh re-sends nothing and also shows the sign-in state;
- a transient refresh failure can leave a valid session behind (spec L4).

The comment-only claim was checked: a TypeScript-parser print of all three source files with comments removed is identical to GREEN.

### Known limits / follow-ups
- **Test gaps (the code is correct; no frozen test pins these, and in the fix round each listed mutant survived):**
  - UR3 "listener removed when the race settles" (A2, A2b);
  - an abort before the race starts, during the first 401 body read (A6);
  - correction 8's "no new top-level return", which is fenced only through the `ArrowLeft` count (A3b);
  - a bare non-envelope 401, pinned at the service level (T19) but not at the screen (A5b);
  - the retry's option keys (A13).
  These are candidates for a test-only follow-up.
- **L1, device check:** re-sending the same FormData on a device. The multipart re-read was checked against the real RN `FormData.js` and whatwg-fetch, with `convertRequestBody` probed. Native OkHttp / `RCTNetworking` was read but not run. On a device: sign in, let the access token expire, take two photos, and expect a result with no sign-in prompt.
- **L2:** each 401 costs one full multipart upload before the retry. The refused request is not metered.
- **L4 / Q2:** a TRANSIENT refresh failure shows the sign-in state, so a tap on "Sign In" signs out a session that may still be valid (HistoryScreen parity). The follow-up route is a `getToken()` check after a failed refresh; it needs no `performRefresh` edit.
- **L8, plus the adversary notes:**
  - `identifyFromImages` is not aborted when Results unmounts, which is pre-existing. A camera 401 that lands after an earlier dead-session refresh repeats the clear and emit; that is interceptor parity, and App's listener is idempotent.
  - A late 401 after a re-login can refresh and retry under the new session; the result is discarded.
  - Abort-on-unmount would close both, but it is a separate unit.
- **Abort at entry:** an abort that lands before the race starts still starts or joins one refresh, which then runs to completion (P-A3 parity).
- **Sign In double tap:** the CTA has no in-flight guard. A double tap gives 2 clears and 2 emits; both are idempotent, matching HistoryScreen.

### Shipping
OTA-capable (`app.json`, `eas.json`, `package.json` and the lock are unchanged), and it must be in the store binary. After merge, the tester lever is `npm ls`, then `eas update --branch preview --clear-cache` from main. Ship this OTA before `ENABLE_STRICT_OPTIONAL_AUTH` is considered.

## Orchestrator review (session 71)
- Process: Opus spec (measured: the single flight is getOrStartRefresh, the backend parses the multipart before the guard, the same FormData can be re-sent), Opus adversarial spec review (11 corrections: the refresh wait had to be raced against the deadline or a slow refresh held the call for 230 s; single-read response fakes; a 403 pin; a non-JSON 401 pin; the CTA order), orchestrator rulings UR1-UR8, Opus RED gated PASS (15 reds for the stated reasons, 9 pins, satisfiability sketch with 21 mutants killed), Opus GREEN (24 mutants killed), two Opus adversaries (auth-flow: interceptor races, two uploads in flight, the deadline in both directions, dead sessions, HTML 401 bodies, a near-device whatwg-fetch transport; engineering: all gates re-run, 39 mutants), both SOUND; the fix round changed three comments.
- The orchestrator read the api.ts and ResultsScreen diffs, fast-forwarded the branch to main `1974e217` (no client file moved) and re-ran the FULL jest suite there (359 passed of 362 suites, 3,509 tests, 42 snapshots) and tsc (clean).
- Follow-up issue filed at merge: five test-strength gaps the adversaries measured (the race listener removal, an abort during the first 401 body read, the auth state through a new top-level return, a bare 401 at the screen level, an extra option on the retry) and the pre-existing no-abort-on-unmount of the camera upload (a late 401 can refresh under a re-logged-in session; the same property as the axios replay).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
