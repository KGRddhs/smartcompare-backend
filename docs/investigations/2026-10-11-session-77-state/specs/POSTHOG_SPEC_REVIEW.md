# S77 POSTHOG - adversarial spec review

Reviewed: `.qa-s77/POSTHOG_UNIT_SPEC.md` (sha256 17c53315eb1e1ff608bc914d52b2b6557e70c16665e2acb21f509b79abb71b60).
Code base: main 10135306 (worktree sc-s77-posthog). Legal text: PR #351 at be658fac (worktree sc-s77-legal).
Library sources read 2026-10-12: posthog-js `main` (packages/react-native package.json = 4.81.0, so main == the
spec's version) files `src/autocapture.tsx`, `src/posthog-rn.ts`, `src/native-deps.tsx`,
`src/optional/OptionalExpoFileSystem.ts`, `packages/core/src/posthog-core.ts`, `posthog-core-stateless.ts`;
registry.npmjs.org/posthog-react-native/4.81.0; posthog-python `master` `posthog/client.py`; context7
/posthog/posthog.com (events-retention, privacy/data-storage) and /websites/posthog_libraries_react-native.
Reviewer: S77 adversary agent, 2026-10-12 02:09-02:40 AST. No test, install, network call to our API, or
git write was made.

## Verdict: APPROVE_WITH_RULINGS

The design holds: the client half is OTA-feasible, the masking plan keeps rendered text and TextInput values
out, and the server option (a) is the right choke point. No finding is BLOCKING: the spec's own section 8
order sends nothing before the policy is live or before App Review approval. Nine MAJOR findings need a
ruling before RED: one privacy leak path the spec missed (F1), a deletion race (F2), two server
classification/coverage errors (F3, F4), one event-loop regression (F5), one identity bug (F6), a CI
ordering break in the legal plan (F7), legal-truth gaps (F8), and the OTA verification order (F9).

## Claims re-derived and CONFIRMED

- posthog-react-native 4.81.0: deps `@posthog/core ^1.58.0`, `@posthog/types ^1.415.2`; all 14 peers
  `optional: true`; no `react-native` field, no codegen/expo field, no install scripts; exports `.`, `./expo`,
  `./metro` (tooling only) [registry 4.81.0].
- Optional peers are loaded by a static `require()` inside try/catch (`src/optional/OptionalExpoFileSystem.ts`).
  Metro's own default is `allowOptionalDependencies: false` (sc-s70-u4b
  `node_modules/metro-config/src/defaults/index.js:136`) but `@expo/metro-config` sets it `true`
  (`node_modules/expo/node_modules/@expo/metro-config/build/ExpoMetroConfig.js:308`), so the unresolved
  `expo-file-system` require bundles and throws only at run time (caught). metro.config.js uses the stock
  `getDefaultConfig` (one cacheVersion deviation).
- expo-file-system 19.0.24 exists only nested (`node_modules/expo/node_modules/expo-file-system`); no top-level
  copy (measured in sc-s70-u4b). `customStorage: AsyncStorage` is honoured (`posthog-rn.ts`: `persistence
  === 'file'` -> `options.customStorage ?? buildOptimisticAsyncStorage()`).
- `$device_name` = expo-device `modelName`, not the user-set device name; getAppProperties sends no device
  identifier [native-deps.tsx].
- Autocapture: `children` -> `$el_text` only when listed in `propsToCapture`; `ph-no-capture` checked on every
  ancestor even past `maxElementsCaptured`; only listed props are read [autocapture.tsx]. Dynamic testIDs
  (grep of `testID={\`...${}...\`}` over src/) encode gender/age/gov/country/budget/brand/lifestyle/priority/
  attribution only in the 12 files of spec 2.3; the rest carry enums, indexes or UUIDs.
- Opt-out: `defaultOptIn ?? true`; `optedOut = persisted OptedOut ?? !defaultOptIn`; `enqueue` and
  `sendImmediate` drop when opted out [core-stateless]. `before_send` is supported, receives
  `{uuid, event, properties, $set, $set_once, timestamp}`, a null return or a throw drops [core].
- `/flags` is NOT called when `preloadFeatureFlags: false` and `disableRemoteFeatureFlags: true` (the remote
  config handler calls `flagsAsync({fetchConfig:true})` only when `preloadFeatureFlags !== false &&
  !disableRemoteFeatureFlags`; `reset()` emits cleared flags instead of reloading) [core].
- posthog-python: `disabled = disabled or not self.api_key`; `disable_geoip=True` default; `capture(event,
  **kwargs)` with `distinct_id` as keyword; enqueue `queue.put(msg, block=False)`; `send_feature_flags`
  default False; atexit best-effort flush (1.0 s) [client.py master].
- PostHog retention 1 year free / 7 years paid and "you cannot make that period shorter"; person deletion
  queues event deletion asynchronously (`events_queued_for_deletion`) [posthog.com docs via context7].
- App Privacy / manifest: app.json `ios.privacyManifests` declares UserID, SearchHistory, ProductInteraction,
  OtherUserContent, PerformanceData with `Analytics`, all Linked true, Tracking false; DeviceID purpose
  AppFunctionality only; OtherDiagnosticData AppFunctionality only (measured). The inventory
  (docs/privacy-data-inventory.md rows 5/7/8) matches.
- Anchors spot-checked at 10135306: App.tsx:217/:230/:306/:362, authService.ts:626, api.ts:997-1030,
  feedback_service.py:82, database_service.py:753, main.py:396/:399, tests/test_shutdown_drain.py:961,
  auth_routes.py:1164-1167, certificatePinning.ts:69, sentry.ts:267-280 - all as cited.

## Findings

### F1 MAJOR - `Application Opened` ships the cold-start deep link, path tokens included
Evidence: posthog-rn.ts `captureAppLifecycleEvents`: `const initialUrl = (await Linking.getInitialURL()) ??
undefined` then `this.capture('Application Opened', { ..., ...maybeAdd('url', initialUrl) })`. The app's
links carry tokens in the PATH: `c/:share_token`, `q/:share_token`, `r/:code` and `reset-password` with the
recovery tokens after `#`/`?` (SmartCompareApp/src/navigation/linking.ts:32, :47-59). A signed-in user
(persisted opt-in) cold-started by a share/quiz/referral link sends the share token or invite code to
PostHog. Spec 2.5 claims "Route NAME only, never params (... share tokens)" and does not list this channel;
`scrubEvent` strips only query/fragment, so path tokens pass. (The fragment strip does cover the recovery
tokens - by accident; nothing pins it.)

### F2 MAJOR - account deletion races the analytics queues; a deleted user can be re-created in PostHog
Evidence: core `reset()` always keeps `PostHogPersistedProperty.Queue`; `optOut()` does not clear the queue;
`flushInternal`/`_flush` have no opt-out check [core, core-stateless]. EditProfileScreen.tsx:139 and :146 call
`DELETE /api/v1/auth/account` first and `clearSession()` (-> reset + optOut) after, so up to 20 events / 10 s
of the deleted user's queue are sent after the server erased the account and after B2 queued the PostHog
deletion. Server side the same: the posthog-python queue flushes every 5 s while B2 fires immediately from the
deletion route (spec 4.5). PostHog deletes events asynchronously and a later event for the same distinct_id
creates a new person, so the s9 promise does not hold.

### F3 MAJOR - a failed stream is reported as `server_compare_completed`
Evidence: text_routes.py:1220-1293. When a stream ends on a `success: False` terminal payload
(STREAM_TIMEOUT / INSUFFICIENT_DATA / moderation refusal) with no `error` event, the `if user_id:` block runs
`save_comparison_and_track_cohort` / `track_after_persist` regardless of `ENABLE_SEARCH_LOG_TRUTH`. Spec 4.3
captures BEFORE the falsy-id return, so the failure becomes `server_compare_completed {saved: false}`; with
the TRUTH flag ON the same compare ALSO emits `server_compare_failed` from log_search (text_routes.py:1222-1240)
- one compare, two contradictory events.

### F4 MAJOR - failure coverage exists only with `ENABLE_SEARCH_LOG_TRUTH` ON
Evidence: with the flag OFF, stream `success:False` terminals write a SUCCESS row (text_routes.py:1242-1258),
abandoned/incomplete streams write no row (:1347 `if _truth:`), and `/url/compare` + `/text/quick` write
none (CLAUDE.md W4-13 row). The stream is the app's main compare path. Spec 4.2's "every failure path calls
log_search(..., success=False)" is true only with the flag ON; its prod state is not recorded in the spec.

### F5 MAJOR - the opt-out preference read blocks the event loop
Evidence: spec 4.3 reads `users.preferences.analytics_enabled` "via `run_db`"; `run_db` is inline when
`ENABLE_SYNC_DB_OFFLOAD` is OFF (app/utils/db_offload.py:35-39), the documented prod state. One cold compare
already freezes the loop 6.5-16.2 s (rules addendum S77); a blocking Supabase RTT per user per 300 s on top
is a regression the unit does not need: the routes already fetch the preferences (text_routes.py:602, :819
`get_user_preferences`).

### F6 MAJOR - `identifyUser` memo survives `resetAnalytics`
Evidence: spec 2.1 makes `identifyUser` "Idempotent per userId" and `resetAnalytics` = `reset()` + `optOut()`
only. Logout then login as the SAME user in one JS session skips `optIn()` + `identify()`, so that user stays
opted out (persisted) until the next cold start. Tests a4/a5 do not cover the sequence.

### F7 MAJOR - the legal PR cannot merge before the client PR (T7 goes red)
Evidence (#351 tests/test_legal_docs_u8.py): T7 schema fails when a row's module path is not a file
(":module path ... is not a file in the repo", :959-960); `test_t7_client_probes_find_their_needles`
(:923-930) fails when the probe file lacks the needle. The proposed row lists
`SmartCompareApp/src/services/analytics.ts` and a new CLIENT_PROBES entry for it, yet spec 8 merges L
(step 2) before A (step 7). T7b itself is fine: `eu.i.posthog.com` and `eu.posthog.com` are covered by the
row host `posthog.com` (`_covers` suffix rule, :876-878), and adding `"Posthog"` to CLIENT_CONSTRUCTORS
catches `Posthog(...)` / `posthog.Posthog(...)`.

### F8 MAJOR - legal-truth gaps in the planned text
(a) Server events carry `query` (typed text or pasted links, spec 4.3 tables) but the planned s3.2 lists only
"product names, result, prices, timing, cost" and s3.4 says "never what you type": the policy would
understate the transfer. (b) s14 "signing out clears the identifier" is false: `reset()` keeps `DeviceId`,
`InstalledAppBuild`, `InstalledAppVersion` and the event queue [posthog-rn.ts, core]. (c) #351 s8 bullet 1
keeps activity records "until you delete them or your account"; PostHog keeps 1/7 years and cannot shorten
it, so s8 needs its own PostHog line in every case and s9 must not say "immediately" for PostHog (F2).
(d) #351 privacy_policy.md:151 (s15) PROMISES a new effective date on any change; with the 2026-10-11 text
live, O-6 is not optional. (e) `reloadRemoteConfigAsync()` runs at every launch, signed out included, gated
only by `disabled`, not by opt-out [posthog-rn.ts initAfterStorage; core `remoteConfigAsync`]: a GET to
`<host>/array/<key>/config` that gives PostHog the device IP before sign-in. No identifier rides it, but
s3.4/s5 must not say PostHog receives nothing before sign-in.

### F9 MAJOR - the OTA is verified only after it reaches every production phone; the fingerprint base is wrong
Evidence: spec 1 compares fingerprints before/after the install on a branch cut from main 10135306, but
build 2 was built from an earlier session-76 commit (memory: build 1.0.0 (2) attached 2026-10-11; main has
moved since); a native drift between that commit and main would not be caught. Spec 8 step 7 verifies "on a
device" AFTER `eas update --branch production`; Hermes run-time behaviour of @posthog/core (fetch,
AbortController, uuid, AsyncStorage blob size) is not proven by `expo export`. This is the first update the
production channel ever receives.

### F10 MINOR - `$anon_distinct_id` is the install identifier the scrub misses
core `identify()` adds `$anon_distinct_id: this.getAnonymousId()`; RN seeds `DeviceId` from that anonymous
id. Event properties never carry `$device_id` (core and RN common properties do not add it); it rides only the
`/flags` body, which `before_send` cannot touch. What keeps DeviceId out is
`preloadFeatureFlags:false` + `disableRemoteFeatureFlags:true`, not the scrub; spec 2.1's reasoning is wrong.

### F11 MINOR - the first screen is never tracked
`onStateChange` does not fire for the initial state, and at boot `identifyUser` runs while App renders
`<SplashScreen>` (no NavigationContainer, App.tsx:345), so `getCurrentRoute()` is undefined.

### F12 MINOR - `initAnalytics()` before `bootstrapRtl` doubles lifecycle events
App.tsx:198-200: `bootstrapRtl` may `Updates.reloadAsync()` once; a client built before it captures
`Application Opened` twice (opted-in users).

### F13 MINOR - `input_type` default mislabels streams
The three direct `track_after_persist` callers (text_routes.py:744, :931, :1279) would default to "text";
:1279 is the stream ("text_stream" in its log_search rows).

### F14 MINOR - shutdown flush bound is on the await, not on the thread
`wait_for(to_thread(client.flush), 1.5)` cancels the await only; `client.flush()` defaults to
`timeout_seconds=10` (client.py master) and ThreadPoolExecutor workers are joined at interpreter exit, so exit
can run past the 30 s window. The new arithmetic 30 > 20 + 8 + 1.5 leaves 0.5 s of margin.

### F15 MINOR - first `import posthog` and client construction on the loop
The lazy `_get_client()` runs inside a fire_and_forget task on the loop thread (import of posthog and its
transitive packages, consumer-thread start). Unmeasured.

### F16 MINOR - the posthog library logger can raise Sentry ERROR events
U8d's `LoggingIntegration(level=logging.ERROR)` turns library ERROR logs (upload failures) into Sentry events;
the spec scrubs only its own warning line.

### F17 MINOR - do not depend on React Native's `URL` polyfill in `scrubEvent`
RN's built-in `URL` implements only part of the WHATWG getters (behaviour on 0.81.5 NOT verified here); a
throw drops the event (fail-closed, but silently loses `source_click` and lifecycle events).

### F18 MINOR - install hygiene
`@posthog/core`/`@posthog/types` are caret ranges, so the 14-day cooling of the top package does not cool the
transitive ones. sc-s77-posthog has no node_modules; RED's `tsc` needs the package types.

### F19 MINOR - `PreferenceTogglesBody._at_least_one` rejects an analytics-only body
auth_routes.py:1427-1432 requires `ai_sharing_enabled` or `notifications_enabled`; spec 2.6 adds
`analytics_enabled` without amending the validator.

### F20 MINOR - App Privacy and sequencing details
No new data type is required (confirmed above). Device model/OS/locale/time zone/screen size ride with events;
adding OtherDiagnosticData -> Analytics is optional. Spec 8 publishes/verifies ASC (step 6) AFTER enabling
server capture (step 5); verification must come first. "Discard client IP data" is listed as an owner step
but is the condition for the inventory's "IP address: not collected" and "no Coarse Location", so it must be
verified on a real event before the client OTA. ASC published answers were not visible to me (O-7 stands).

### F21 MINOR - other EXPO_PUBLIC values ride the same `--environment production`
sentry.ts:267 inlines `process.env.EXPO_PUBLIC_SENTRY_DSN`; the update inlines whatever the EAS production
environment holds, which may differ from what build 2's embedded bundle used.

### F22 MINOR - test hygiene and key rotation
b1 asserts `"posthog" not in sys.modules` while b3 injects a fake module: every test must use
`monkeypatch.setitem/delitem` on `sys.modules` and reset the singleton. The lazy singleton keeps the first key:
a key rotation needs a restart (state it in the flag row). Sentry RN's default trace-propagation targets
(not verified here) may attach `sentry-trace`/`baggage` headers to PostHog requests; optional to restrict.

## Proposed rulings (adoptable verbatim)

- **PR1 (F1, F17).** `scrubEvent` reduces EVERY `url`-valued property (including `url` on `Application
  Opened`) to scheme + host + first path segment, with the query, fragment and any further path segments
  removed (`qaren://c/<token>?ref=X` -> `qaren://c`; `https://getmyez.com/c/<token>` -> `https://getmyez.com/c`;
  `qaren://reset-password#access_token=...` -> `qaren://reset-password`), except `source_click.url`, which
  keeps scheme + host + path and loses only query and fragment. Implement with string operations, not `URL`.
  Test a8 adds: an `Application Opened` event built with each of the four link shapes; no token substring
  survives in the serialized event.
- **PR2 (F2).** Add `prepareAccountDeletion(): Promise<void>` to analytics.ts: `optOut()` then
  `flush()` raced against 2000 ms; never throws. EditProfileScreen calls it BEFORE `DELETE /account`;
  `clearSession()` keeps reset + optOut after. Server: `capture_*` skips a user id whose deletion was requested
  in this process (in-memory set filled by the deletion route BEFORE the erase); B2 runs
  `await asyncio.to_thread(client.flush, timeout_seconds=2)` (when a client exists) BEFORE `bulk_delete`, and
  logs `events_queued_for_deletion` and `deletion_errors` by count only. Policy s9 says PostHog deletion is
  "requested when you delete your account and completed by PostHog on its own schedule", never
  "immediately". New tests: a6b (the call order on the delete path), b11b (flush before bulk_delete; no
  capture after the deletion request).
- **PR3 (F3).** `server_compare_completed` is captured only when `full_response.get("success") is True`
  (partials included). A `success: False` payload reaching `track_after_persist` captures nothing there.
  Test b3b: a `success: False` stream terminal produces zero `server_compare_completed` in both TRUTH-flag
  states.
- **PR4 (F4).** Activation precondition: `ENABLE_SEARCH_LOG_TRUTH=true` on `web` (the owner confirms with an
  exact-line count) BEFORE `ENABLE_POSTHOG_SERVER_CAPTURE`. The flag row and the stated limits say: with
  TRUTH OFF, stream failure terminals, abandoned streams and Link-mode failures emit no
  `server_compare_failed`.
- **PR5 (F5).** No preference read on the event loop: the server opt-out check takes the preferences the
  route already fetched where it has them; otherwise it reads `users.preferences` through
  `asyncio.to_thread` (never `run_db`), with the 300 s / 2048-entry cache. A missing row means opted out.
  Test b8b: with `ENABLE_SYNC_DB_OFFLOAD` unset, the read runs on a non-loop thread.
- **PR6 (F6).** `resetAnalytics()` clears the identify memo (and the last-tracked route). Test a4b:
  identify(A) -> reset -> identify(A) calls `optIn` + `identify` twice.
- **PR7 (F7).** Merge order: B, then A (both inert: no key, flag OFF), then L, then activation. If L must
  merge first, its processors.json row lists only `app/services/product_analytics_service.py` and hosts
  `["posthog.com"]`; A then adds the client module path, the `posthog-react-native` host and the
  CLIENT_PROBES entry in the same PR.
- **PR8 (F8).** L text: (a) s3.2 states that the text you type or the link you paste (shortened) is sent to
  PostHog with the comparison record, and s3.4 scopes "never what you type" to taps and screens; (b) s14 says
  signing out resets the analytics identity and that a random install identifier and unsent events stay in
  app storage until sent or the App is deleted; (c) s8 gets its own PostHog line (1 year on the free plan,
  7 years on paid plans) and s9 follows PR2; (d) O-6 is decided: bump the effective date through the T6
  machinery (s15 promises it); (e) s3.4/s5 say the App contacts PostHog when it starts, before sign-in,
  without an identifier. If the owner prefers not to disclose (a), drop `query` from both server events
  instead.
- **PR9 (F9).** (1) The "before" fingerprint is build 2's: EAS's recorded fingerprint for the build, or
  `npx @expo/fingerprint` run at build 2's git commit (from its EAS build page); "after" is the branch
  after the install; they must be equal. (2) Before the production publish, the same commit is published
  with `eas update --branch preview --environment preview` (a preview environment holding a SEPARATE test
  PostHog project key) to an internal build whose fingerprint equals build 2's, and a device QA records: taps
  and screens arrive; Auth screens and `ph-no-capture` screens send nothing; no `$ip` and no `$geoip_*`
  property; no token in any `url`; the account-deletion path of PR2. (3) Only then
  `eas update --branch production --environment production`, after `npm ls`.
- **PR10 (F10).** `before_send` also deletes `$anon_distinct_id`. Test a3 pins `preloadFeatureFlags: false`
  and `disableRemoteFeatureFlags: true` with the comment "these keep DeviceId out of the /flags body".
- **PR11 (F11, F12).** Track the initial route from a `navigationRef.addListener('ready', ...)`
  registration in App.tsx (the pinned `onReady={onNavigationReady}` literal stays untouched); call
  `initAnalytics()` after `bootstrapRtl(lang)` and before `initializeAuth`.
- **PR12 (F13).** The three direct `track_after_persist` callers pass `input_type` explicitly
  ("text", "text", "text_stream"); the composite passes its own.
- **PR13 (F14, F15).** The shutdown handler runs `client.flush(timeout_seconds=POSTHOG_SHUTDOWN_FLUSH_TIMEOUT)`
  inside `asyncio.to_thread`, with the outer `wait_for` at the same bound plus 0.25 s;
  `POSTHOG_SHUTDOWN_FLUSH_TIMEOUT = 1.0` (margin 1 s: 30 > 20 + 8 + 1.0 + 0.25 pinned). GREEN verifies
  that the pinned 7.67.0 `flush` accepts `timeout_seconds`; if it does not, use `shutdown()` in the thread and
  record the measured worst case. First client construction (including `import posthog`) runs in
  `asyncio.to_thread`; GREEN reports its measured cost.
- **PR14 (F16).** `logging.getLogger("posthog")` is set to CRITICAL at client construction;
  `on_error` logs `"[POSTHOG] send failed: %s", type(exc).__name__` at WARNING.
- **PR15 (F18).** The orchestrator installs with `npm install --save-exact posthog-react-native@<V>
  --before=<install date minus 14 days>` (so the transitive ranges resolve to versions at least 14 days old)
  in a worktree with its own real node_modules, before RED runs `tsc`.
- **PR16 (F19).** `PreferenceTogglesBody` accepts `analytics_enabled` alone (validator and error text
  updated); test.
- **PR17 (F20).** Section 8 order becomes: merge B, A, L (PR7) -> L live on the API and the landing redeployed
  -> App Review approval and manual release -> owner creates the EU project, turns ON "Discard client IP
  data", keeps "Enable exception autocapture" OFF, signs the PostHog DPA -> owner verifies/publishes ASC App
  Privacy -> `ENABLE_SEARCH_LOG_TRUTH` confirmed (PR4) -> server key + flag; one own-account compare must show
  `server_compare_completed` with no `$ip`/`$geoip_*` -> PR9 preview QA -> EAS production variable created
  (not earlier: any production update after its creation would carry the client) -> production OTA.
- **PR18 (F21).** Before the production publish the owner lists the NAMES of the EAS production environment
  variables; only `EXPO_PUBLIC_POSTHOG_KEY` (and optional `EXPO_PUBLIC_POSTHOG_HOST`) may be new.
- **PR19 (F22).** Backend tests manipulate `sys.modules` only through `monkeypatch` and reset the module
  singleton per test; the flag row states that a key change needs a restart.

## Not verified (stated, not guessed)

- App Store Connect published answers, the PostHog account, Railway variable states (`ENABLE_SEARCH_LOG_TRUTH`,
  `ENABLE_SYNC_DB_OFFLOAD`), build 2's exact git commit and fingerprint.
- The spec's gitleaks measurements (no run here), and the Apple help-page quotes in spec 7.2.
- posthog-python 7.67.0 specifically (I read `master`); the RN `URL` polyfill on 0.81.5; Sentry RN's default
  trace-propagation targets; whether remote config can enable error tracking (docs say native capture is
  "gated by your project's Enable exception autocapture setting", i.e. AND, not OR).
