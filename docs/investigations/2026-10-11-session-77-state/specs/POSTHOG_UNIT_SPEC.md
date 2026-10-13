# S77 POSTHOG - implementation spec (analytics: taps, screens, comparisons, results)

Base: main 10135306 (worktree sc-s77-posthog, branch feature/s77-posthog). Legal text read at PR #351
(sc-s77-legal, HEAD be658fac). Written 2026-10-12 by the S77 spec agent. Every `file:line` is at
10135306 unless marked `#351`. Library facts carry their source in brackets.

## 0. Verdict and shape

- **OTA feasible: YES for the client half.** posthog-react-native 4.81.0 is pure JS (the published
  package holds only `dist/`, `tooling/`, LICENSE, README, package.json; no ios/, android/, podspec,
  expo-module.config.json or app.plugin.js [app.unpkg.com/posthog-react-native@4.81.0]); its two
  dependencies are `@posthog/core` and `@posthog/types` [registry.npmjs.org/posthog-react-native/latest];
  every native peer it can use is already linked in build 2 (section 1). The deciding fact is that
  nothing it needs is a native module missing from the binary, so `eas update` can carry it.
- **Recommended server option: (a)** posthog-python capture at the two existing choke points
  (`feedback_service.track_after_persist`, `database_service.log_search` failure rows) behind
  `ENABLE_POSTHOG_SERVER_CAPTURE` (default OFF, read per call), lazy client, off-loop queue, bounded
  flush after the W1-6 drain.
- Three parts, one PR each, all dark until the owner supplies the key: **A** client (OTA after App
  Review approval), **B** backend server capture (+ optional B2 person deletion), **L** legal text through
  the U8 machinery on top of #351. L goes live before any event is sent (section 8).
- Decisions the orchestrator/owner must take are listed as **O-n** in section 10.

## 1. OTA feasibility (Q1)

| Fact | Value | Source |
|---|---|---|
| Latest posthog-react-native | 4.81.0 (published about 2026-10-10, "2 days ago" on unpkg) | npm registry `latest` dist-tag; app.unpkg.com |
| Runtime deps | `@posthog/core ^1.58.0`, `@posthog/types ^1.415.2` | npm registry |
| Peers (all 14 `optional: true`) | expo-device >=4, expo-application >=4, expo-localization >=11, expo-file-system >=13, @react-native-async-storage/async-storage >=1, expo-updates >=0.25, @react-navigation/native >=5, react-native-svg >=15, react-native-safe-area-context >=4, react-native-device-info, react-native-localize, react-native-navigation, @posthog/react-native-plugin >=2.9.3, posthog-react-native-session-replay >=1.6.0 | npm registry `peerDependenciesMeta` |
| Expo install line (docs) | `npx expo install posthog-react-native expo-file-system expo-application expo-device expo-localization`; "no mobile native dependencies outside of supported Expo packages" | posthog.com/docs/libraries/react-native |

Peers already in build 2 (SmartCompareApp/package.json + package-lock.json):

| Peer | package.json | lock (installed) |
|---|---|---|
| expo-application | `~7.0.8` (package.json:27) | 7.0.8 (lock:7083) |
| expo-device | `~8.0.10` (:33) | 8.0.10 (lock:7284) |
| expo-localization | `~17.0.9` (:38) | 17.0.9 (lock:7375) |
| @react-native-async-storage/async-storage | `2.2.0` (:17) | 2.2.0 (lock:2884) |
| expo-updates | `~29.0.20` (:43) | present |
| @react-navigation/native | `^7.1.28` (:20) | 7.2.4 (lock:3206) |
| react-native-svg | `^15.12.1` (:56) | 15.15.5 (lock:12643) |
| react-native-safe-area-context | `~5.6.0` (:53) | present |
| expo-file-system | NOT declared | 19.0.24, NESTED at `node_modules/expo/node_modules/expo-file-system` (lock:7769; a dependency of `expo`, lock:7040). Not hoisted: `sc-s70-u4b/SmartCompareApp/node_modules/expo-file-system` does not exist (measured). |

Consequences:
- The SDK's storage order is expo-file-system (new File/Paths API) -> legacy expo-file-system ->
  AsyncStorage -> error [raw `packages/react-native/src/native-deps.tsx`]. From
  `node_modules/posthog-react-native` the nested expo-file-system does not resolve, so it would fall to
  AsyncStorage. **Spec: pass `customStorage: AsyncStorage` explicitly** (constructor uses
  `options.customStorage ?? buildOptimisticAsyncStorage()` when `persistence: 'file'` [raw `posthog-rn.ts`])
  and **do not add expo-file-system to package.json** (adding it would hoist a JS copy whose native
  module version must equal the binary's; avoidable risk).
- Device/app properties come from expo-application, expo-device, expo-localization (all linked):
  `$app_build/$app_name/$app_namespace/$app_version/$device_manufacturer/$device_name(=modelName)/
  $os_name/$os_version/$is_emulator/$locale/$timezone`; no IDFV, no advertising id [native-deps.tsx].
- **What would REQUIRE a new binary (out of scope, must not be added):** `@posthog/react-native-plugin`
  (2.12.5, native iOS/Android; renamed `posthog-react-native-session-replay`; needed for session replay,
  native crash capture, push integrations; replay "Expo Go is not supported - use a development
  build") [registry; posthog.com/docs/session-replay/installation/react-native]; any change to
  `app.json` plugins or `ios.privacyManifests` (docs/privacy-data-inventory.md:21-22 "app.json changes
  reach phones through eas build, never through eas update"); adding expo-file-system at top level.
- The `./expo` export (`dist/tooling/expoconfig.js`) is a tooling helper, not a config plugin; do not
  add it to app.json plugins.
- SDK-54 compatibility: RN 0.81.5 / React 19.1.0 / expo 54.0.37. Metro uses the stock
  `getDefaultConfig` (metro.config.js), so package `exports` resolution is the SDK default. Proven only
  by the bundle gate in section 9 (`npx expo export --platform ios`), not by reading.
- **Native-change detector (mandatory install gate):** run `npx expo-updates fingerprint:generate
  --platform ios` (or `npx @expo/fingerprint .`; @expo/fingerprint 0.15.5 is in the lock) before and
  after the install. Identical = no native change. Different = STOP and diff the sources; the runtime
  is `{"policy":"appVersion"}` (app.json; pinned by nativeBundle.w37 e1), so a native change would NOT
  change the runtime version and an OTA would silently reach a binary without it.
- Install command (orchestrator only): `npm install --save-exact posthog-react-native@<V>` in
  SmartCompareApp, where V is the newest 4.x published at least 14 days before the install (4.81.0 is
  2 days old today; supply-chain cooling). Then `npm ls posthog-react-native @posthog/core` (memory
  rule: npm ls before any eas update), `node node_modules/jest/bin/jest.js --ci` (full),
  `tsc --noEmit`, and the fingerprint comparison.

## 2. Client design (Q2)

### 2.1 Module `SmartCompareApp/src/services/analytics.ts` (new, a LEAF)
Imports only `posthog-react-native` and `@react-native-async-storage/async-storage`. Never imports
`./api`, `./authService` or navigation (keeps the W3-12 boot-order invariant and avoids cycles:
authService and api will import it). Exports:

- `initAnalytics(): void` - idempotent. Reads `process.env.EXPO_PUBLIC_POSTHOG_KEY` and
  `process.env.EXPO_PUBLIC_POSTHOG_HOST` by static dot access (required for inlining [docs.expo.dev
  guides/environment-variables]). Key absent/blank -> client stays `null` and EVERY export is a no-op
  (tests, dev, CI, any bundle built without the EAS variable). Host default `https://eu.i.posthog.com`.
  Key present -> `new PostHog(key, options)` with:
  `host`, `persistence: 'file'`, `customStorage: AsyncStorage`, `defaultOptIn: false`,
  `captureAppLifecycleEvents: true`, `disableGeoip: true`, `preloadFeatureFlags: false`,
  `disableRemoteFeatureFlags: true` (4.49+), `enableSessionReplay: false`, every
  `errorTracking.autocapture` switch off (Sentry stays the crash reporter; exact key names from the
  installed `types.ts`, tsc-checked), `flushAt: 20`, `flushInterval: 10000` (doc defaults),
  `before_send: scrubEvent`. Wrapped in try/catch: a constructor failure leaves `null`.
- `getAnalyticsClient(): PostHog | null` - for the provider.
- `identifyUser(userId: string): Promise<void>` - no-op without client or when the per-user switch
  (2.5) is off; else `optIn()` then `identify(userId)` with NO properties (never email, name,
  display_name). Idempotent per userId.
- `resetAnalytics(): void` - `reset()` then `optOut()` (opt-out is persisted [docs: "persisted and
  will be respected until optIn/Out is called again"]).
- `trackScreen(routeName: string | undefined): void` - `screen(routeName)` with NO properties; skips
  undefined and repeats of the last name.
- `mirrorEvents(events)` - section 3.
- `setAnalyticsEnabled(userId, enabled)` / `isAnalyticsEnabled(userId)` - section 2.5.
- `scrubEvent(event)` (exported for tests) - drops `$device_id` if present (keeps the label set inside
  the existing manifest, section 7.3), drops `$ip` if present, strips the query and fragment from any
  `url` property, returns the event; never throws (a throw returns `null` = drop).

`reset()` keeps the SDK's `DeviceId`, `InstalledAppBuild`, `InstalledAppVersion` by default
[posthog-rn.ts]; acceptable because the DeviceId is never sent (scrubbed) and is a random install id.

### 2.2 Bootstrap order (index.ts / App.tsx)
- index.ts:6 keeps `import './src/services/sentryBootstrap'` FIRST; nothing analytics-related is added
  to index.ts or sentryBootstrap.ts (bootSentryOrder.w312 pins `order == [initSentry(), api.ts module
  body]` and the bootstrap's import graph).
- No client is constructed in a module body. `initAnalytics()` is called at the top of `init()` inside
  App's boot effect (App.tsx:183-270, `init()` at :194), before `initializeAuth` (App.tsx:217), so a restored session can
  identify immediately.

### 2.3 Provider placement and touch autocapture
- `PostHogProvider` is optional; it is needed only for `captureTouches` [docs]. Render it INSIDE the
  NavigationContainer (docs v7 example) around `<StatusBar/>` + `<Stack.Navigator>` (App.tsx:362-494)
  through a tiny `AnalyticsProvider` wrapper in `src/components/AnalyticsProvider.tsx` that returns
  `children` unchanged when `getAnalyticsClient()` is null.
- Props: `client={client}`, `autocapture={{ captureScreens: false, captureTouches: true,
  propsToCapture: ['testID', 'ph-label'], customLabelProp: 'ph-label', noCaptureProp:
  'ph-no-capture', maxElementsCaptured: 20 }}`. Lifecycle events come from the client option
  `captureAppLifecycleEvents` (default true since 4.39.0 [docs]), not from the provider.
- Why `propsToCapture: ['testID','ph-label']`: the default list is `['style','testID',
  'accessibilityLabel', customLabelProp, 'children']`, string `children` become `$el_text`, and removing
  `'children'` turns `$el_text` off [raw `packages/react-native/src/autocapture.tsx`]. This single
  setting keeps rendered product names, comparison results, history titles and every Text node out of
  PostHog. `value` is never in the list, so TextInput values are never captured (the code has no
  TextInput branch and reads only listed props [autocapture.tsx]).
- `ph-no-capture` drops the WHOLE touch event when found on any ancestor (the check runs even above
  `maxElementsCaptured`) [autocapture.tsx]. Add `ph-no-capture` to the ROOT element of every surface
  whose testIDs encode personal answers or that holds credentials (measured: dynamic testIDs
  `gender-${..}`, `age-${..}`, `gov-${..}`, `country-${..}`, `budget-${..}`, `brand-${..}`,
  `lifestyle-${..}`, `priority-${..}`, `attr-${..}`, `profile-priorities-empty-${..}`):
  src/screens/onboarding/OnboardingFlow.tsx (covers Step01-17), src/screens/OnboardingScreen.tsx,
  src/screens/EditPreferencesFlow.tsx, src/screens/EditProfileScreen.tsx,
  src/components/DemographicsBottomSheet.tsx, src/components/ProfileEditorialSections.tsx,
  src/screens/InviteeQuizScreen.tsx, src/screens/ContactUsScreen.tsx, and the four auth screens
  (LoginScreen, RegisterScreen, ForgotPasswordScreen, ResetPasswordScreen; defence in depth - they are
  unreachable while opted out, 2.4). Pickers (BudgetPicker, BrandAttitudePicker, LifestylePicker) are
  covered by their hosting screens. `<View ph-no-capture>` is valid TSX (hyphenated attributes are not
  type-checked).
- testIDs that remain (e.g. `tab-home`, `profile-row-logout`, `history-row-${item.id}` with a
  comparison UUID, `results-product-card-${idx}`) are developer constants or internal ids, not
  personal content. Optional `ph-label` on the 10 most important CTAs (compare submit, share, scan,
  paywall CTA) for readable names; not required.

### 2.4 Identity: user id only; no capture before the user is known (DECIDED)
- `defaultOptIn: false`: nothing is sent until `identifyUser` opts in. Justification: (1) the auth
  stack (email/password entry) is the only signed-out surface, so nothing useful is lost while
  credentials stay out; (2) anonymous capture would need a device-scoped identifier, which build 2's
  manifest declares for App Functionality only (section 7.3); (3) one identity model, distinct_id =
  Supabase user id. Cost: no signed-out funnel (signup counts stay available in Supabase).
- `identifyUser(user.id)` call sites: App.tsx:230 block (restored session, next to
  `setStableUserId(authUser.id)`) and App.tsx:306 block (fresh login/register/social). Never pass
  `email`, `display_name` or `name` (authService.ts:64-67 `User`); no `$set`.
- `resetAnalytics()` inside `clearSession()` (authService.ts:626, before the SecureStore deletes;
  never throws). This one site covers logout (authService.ts:320/:336 via `logout()`:272), account
  deletion (EditProfileScreen.tsx:146 `clearSession()` before `onAccountDeleted`), dead refresh
  (api.ts:134, :151 -> sessionInvalid), HistoryScreen.tsx:916 and ResultsScreen.tsx:780.

### 2.5 Screens
React Navigation is v7 (`@react-navigation/native` 7.2.4). Docs: for v7 set `captureScreens: false`
and call `posthog.screen` manually [posthog.com/docs/libraries/react-native]. App.tsx:362 has
`onReady={onNavigationReady}` (literal pinned by App.pushTap.w315.test.ts:101) and no
`onStateChange`. Add `onStateChange={() => trackScreen(navigationRef.getCurrentRoute()?.name)}` (do
not touch `onReady`). `identifyUser` also emits the current route once (App passes
`navigationRef.getCurrentRoute()?.name` after identify). Route NAME only, never params (Results params
carry comparison payloads; ReferralLanding/InviteeQuiz carry share tokens).

### 2.6 Opt-out switch (RECOMMENDED, O-3)
Apple 5.1.2 and Bahrain PDPL: the processing is first-party product analytics through a processor, no
tracking, no ads, so the recommended basis is legitimate interest with an easy objection path (policy
s10 already promises objection by email). Recommend an in-app switch anyway: ProfileScreen
"Privacy & notifications" section (ProfileScreen.tsx:~463, next to the notifications ToggleRow wired
at :156-175), label "Share usage analytics", default ON.
- Client: stored in AsyncStorage key `@qaren_analytics_enabled:<userId>`; OFF -> `optOut()` +
  `reset()`; ON -> `identifyUser`. Also sent to the server (below).
- Server: `PUT /api/v1/auth/preference-toggles` gains optional `analytics_enabled: Optional[bool]`
  (auth_routes.py:1414-1433 body, :1466 key loop); stored in the existing `users.preferences` JSONB, no
  migration. Server capture (section 4) skips a user whose `preferences.analytics_enabled is False`.
- i18n keys in src/i18n/en.json and ar.json (`profile.analytics.title`, `profile.analytics.subtitle`).
If O-3 is declined: drop 2.6 and the server preference read; the policy must then name email as the
only objection route.

## 3. Mirroring first-party events (Q3) - RECOMMENDED

One call site: `trackEvents` (api.ts:997-1007) - every emitter funnels through it, including
`trackEvent` (api.ts:1023-1030), ResultsScreen's local `trackEvent` that queues into
`pendingEventsRef` and flushes via `trackEvents` on unmount (ResultsScreen.tsx:438-444, :487), and the
onboarding wrappers. Add `mirrorEvents(events)` BEFORE the POST, inside its own try/catch, so a mirror
failure can never affect the first-party write. Each event -> `capture(event_type, {...event_data,
comparison_id})`. Names unchanged so PostHog funnels match `user_events`.

Fired today (production src, measured):

| event_type | emitter | properties | personal data? |
|---|---|---|---|
| compare_entry_view | HomeScreen.tsx:337 | mode | no |
| compare_entry_paywall_banner_view | :344, :643 | mode | no |
| compare_entry_paywall_banner_tap | :751, :892 | mode | no |
| compare_entry_content_block | :351 | mode, layer | no |
| compare_entry_submit | :399, :540 | mode, used_paste_split, used_autoswitch | no |
| compare_entry_paste_split | :865 | source_box, mode | no |
| compare_entry_mode_autoswitch | :873 | from, to, trigger | no |
| compare_entry_ready | :880 | mode, time_to_ready_ms | no |
| compare_cancelled | :263 | mode | no |
| share | ResultsScreen.tsx:544 | method, cta_variant | no |
| share_sheet_opened | :547 | cta_variant | no |
| share_completed | :558 | cta_variant, lifetime_invites_remaining | no |
| source_click | :588 | source_name, url | url = retailer page URL: strip query + fragment (scrubEvent) |
| demographics_submitted | :650 | all_skipped (boolean only) | no (answers are NOT in the event) |
| demographics_dismissed | :669 | none | no |
| result_view_duration | :482 | duration_ms (+ comparison_id) | comparison UUID (pseudonymous) |
| onboarding_started | OnboardingFlow.tsx:262, OnboardingScreen.tsx:144 | step_number, step_name, locale, flow_variant | no |
| onboarding_step_completed / _completed | OnboardingFlow.tsx:298/:306, OnboardingScreen.tsx:169/:182 | same | no |

Allowlisted but not fired by the client today: save, tab_switch, feedback_submit, spec_expand,
result_abandon, screenshot (app/api/feedback_routes.py:58-88). The privacy invariant "event_data must
never contain user-typed text or pasted URLs" is documented at api.ts:1015-1019.
- No new event types are added to `user_events`. New PostHog-only captures (screens, touches,
  lifecycle) do not use `trackEvent(`/`fireEvent(`/`fireAnalytics(`/`event_type:` literals, so the
  superset fence (tests/test_events_allowlist_superset.py:37-42 patterns) is unaffected; a new
  PostHog-only helper must not be NAMED `trackEvent`.
- Opt-out is automatic: an opted-out client drops captures.

## 4. Comparisons and results (Q4) - option (a), fully specified

### 4.1 Options weighed
- (a) server capture - covers every phone including build 2 BEFORE the OTA, every input path, and
  server-only fields (cost, cache, partial stage, model downgrade); one choke point per outcome.
  RECOMMENDED.
- (b) PostHog data-warehouse link to Supabase - no code, but hands a third party read credentials to
  the production database (users table with emails), billed per synced row, and needs a policy
  disclosure of a much wider transfer. REJECTED for v1.
- (c) client-only - misses phones that never take the OTA, the server fields, and compares whose app
  was killed mid-stream. Keep as a supplement only (section 3).

### 4.2 Where completion is known (measured)
- All compares require auth (U13: tests/test_s71_u13_compare_auth_required.py), so `user_id` exists.
- SUCCESS, saved: `feedback_service.track_after_persist(comparison_id, *, full_response, user_id)`
  (app/services/feedback_service.py:82-133) is reached by text sync (text_routes.py:744), text pair
  (:931), SSE stream (:1279) and, through `save_comparison_and_track_cohort` (:136-163), image/camera
  (image_routes.py:555) and URL (url_routes.py:201) and the flag-OFF text paths (text_routes.py:755,
  :939, :1287). It runs inside `fire_and_forget` (app/utils/async_utils.py:44), off the response path,
  and already writes the server-side `comparison_completed` user_events row (:107-112).
- FAILURE: every failure path calls `database_service.log_search(..., success=False, ...)`
  (database_service.py:753-803; ~20 call sites in text_routes/url_routes/image_routes), also inside
  `fire_and_forget`. `error_message` there is a human message (`_failure_log_message`,
  text_routes.py:457-468), not the code; the code is not passed to log_search.
- Partial deliveries are successes (`success: True`, `metadata.partial`/`partial_stage`, text_routes.py
  471-477) and are saved, so they reach track_after_persist.

### 4.3 New module `app/services/product_analytics_service.py`
- `posthog_server_capture_enabled() -> bool`: `ENABLE_POSTHOG_SERVER_CAPTURE` truthy (`_TRUTHY`
  idiom, read PER CALL like `search_log_truth_enabled`, database_service.py:711) AND
  `POSTHOG_PROJECT_API_KEY` non-blank.
- `_get_client()`: lazy singleton created on the first enabled capture, under a `threading.Lock`;
  `import posthog` happens INSIDE it (flag OFF never imports the library). Constructor:
  `Posthog(project_api_key=key, host=os.getenv("POSTHOG_HOST") or "https://eu.i.posthog.com",
  sync_mode=False, disable_geoip=True, max_queue_size=1000, flush_at=50, flush_interval=5.0,
  timeout=5, max_retries=2, on_error=_on_error, send=True)`. Library facts: `disabled = disabled or not
  api_key` (empty key = no-op); default `disable_geoip=True`; `capture()` is `@no_throw`, builds the
  message and `queue.put(msg, block=False)` (dropped when full, never blocks); consumer threads send
  batches; `send_feature_flags` default False so capture makes no network call on the caller's thread;
  `flush()` BLOCKS until drained or timeout; `sync_mode=True` would send on the calling thread and is
  forbidden [context7 /posthog/posthog-python client.py; raw client.py]. Version: posthog 7.67.0,
  requires-python >=3.10 (runtime 3.12.9 runtime.txt:1) [pypi.org/pypi/posthog/json].
- `capture_compare_completed(*, user_id, comparison_id, full_response, input_type=None)` and
  `capture_compare_failed(*, user_id, input_type, query, error_message, duration_ms, cost)`: return
  immediately when disabled; otherwise skip opted-out users (2.6, `users.preferences.analytics_enabled
  is False`, read via `run_db` with a per-process TTL cache of 300 s, 2048 entries); build properties;
  `client.capture(event, distinct_id=str(user_id), properties=props)`. Any exception: log
  `logger.warning("[POSTHOG] capture skipped: %s", type(exc).__name__)` - type only, never the message,
  the query or the key (u8d AST pins in tests/test_sentry_channels_u8d_unit.py:830-845).
- Event-loop cost: the capture call is a dict build + `clean()` + non-blocking queue put, run inside
  an already-detached fire_and_forget task. GREEN MEASURES it on the pinned version (memory rule:
  measure, never read): 1000 captures with a stubbed consumer, p99 < 2 ms, and a test asserting the
  HTTP send function is invoked only from a non-loop thread. If the measurement fails, wrap the capture
  in `asyncio.to_thread` (default executor, NOT the adapter executor).

Event `server_compare_completed` (from track_after_persist, BEFORE its falsy-id early return, so
delivered-but-unsaved compares are visible with `saved: false`):

| property | source | note |
|---|---|---|
| comparison_id | arg | UUID or null |
| saved | `bool(comparison_id)` | |
| input_type | new keyword-only arg, default None -> "text" | the three text_routes callers are all text; the composite passes its own (`camera`/`url`) |
| category | `full_response["category"]` (response_builder.py:1895) | |
| product_a, product_b | `overview.products[i]` `brand + " " + name` (response_builder.py:1909-1914) | resolved names, not typed text |
| winner_name, winner_index | `overview.winner.name/product_index` (:1900-1902) | |
| price_a, price_b, currency_a, currency_b, price_found_a, price_found_b | `overview.products[i].price` (public_price_view, price_service.py:9320) amount/currency keys | GREEN maps the exact keys |
| partial, partial_stage | `metadata.partial`, `metadata.partial_stage` | |
| latency_ms | `metadata.elapsed_ms` (:2063) | |
| cost_usd | `metadata.total_cost` (:2066) | |
| cached, comparison_quality, cache_hit | metadata (:2069, :2079, `_compute_cache_observability`) | |
| source_method_a/b | per-product `source_method` when present in the response | absent -> omitted |
| model_downgraded | `metadata.openai_usage` / downgrade marker when present | absent -> omitted |
| query | `full_response["query"]`, truncated to 200 chars; URL compares reduced to host + path | typed text = Search History (declared, section 7.3) |

Never: email, display name, access token, verdict prose, pros/cons, preferences, demographics,
`metadata.fact_check`, `_verdict_critique`.

Event `server_compare_failed` (from log_search only when `success is False and user_id`):
`input_type`, `latency_ms` (duration_ms), `cost_usd`, `query` (200 chars, URL reduced),
`error_class` derived by keyword from `error_message` (`timeout` | `content_unavailable` |
`insufficient_data` | `other`; never the message itself). Success rows of log_search capture nothing
(no double counting). Limit: the exact error code stays in `search_logs` only.

### 4.4 Shutdown flush (W1-6)
- New `@app.on_event("shutdown") async def _flush_product_analytics()` in app/main.py registered AFTER
  `_drain_background_tasks` (main.py:399-433), so captures queued by draining tasks are flushed:
  `await asyncio.wait_for(asyncio.to_thread(client.flush), POSTHOG_SHUTDOWN_FLUSH_TIMEOUT)` with
  `POSTHOG_SHUTDOWN_FLUSH_TIMEOUT: float = 1.5`, no-op when the client was never built; exceptions and
  timeout logged by type.
- The load-bearing arithmetic becomes 30 > 20 + 8 + 1.5 (railway.json `drainingSeconds: 30`,
  `--timeout-graceful-shutdown 20`, `DRAIN_TIMEOUT = 8.0` main.py:396). Extend
  tests/test_shutdown_drain.py:961 `test_the_shutdown_window_arithmetic_holds` (pin moved, not
  deleted). posthog's own `atexit` handler does "a short best-effort flush" [raw client.py]; a SIGKILL
  loses the queue (honest limit, same as W1-6).

### 4.5 Optional B2: person deletion on account deletion (O-5)
Policy s9 (#351 privacy_policy.md:115) promises immediate deletion of "in-app activity records".
PostHog copies need deletion: `POST /api/projects/:project_id/persons/bulk_delete` with
`distinct_ids` and `delete_events` returns 202 and queues deletion; check `deletion_errors`; needs a
PERSONAL API key [posthog.com docs privacy/data-storage]. Spec: flag `ENABLE_POSTHOG_PERSON_DELETE`,
vars `POSTHOG_PERSONAL_API_KEY` (scope person:write only), `POSTHOG_PROJECT_ID`,
`POSTHOG_API_HOST` (default `https://eu.posthog.com`, the private API host, not `eu.i.`), called as a
`fire_and_forget` from the account-deletion route (auth_routes.py:1165-1167) after the user row is
erased, via the existing async httpx client, timeout 5 s, logged by type. If B2 is not active at
activation, the s9 text must say how PostHog data is deleted (section 7.1, O-5).

## 5. Keys and config (Q5)

- The project key (`phc_...`) is a public, write-only ingestion key, but it MUST NOT be committed:
  measured with the local gitleaks 8.30.1 (the CI pin, ci.yml:527-531) over stdin with the repo
  `.gitleaks.toml` (useDefault=true) and a runtime-built random `phc_` + 43-char value:
  `const POSTHOG_KEY = '...'`, `export const POSTHOG_API_KEY = '...'`, `apiKey: '...'`,
  `EXPO_PUBLIC_POSTHOG_KEY=...` and `"posthogProjectKey": "..."` all -> **leaks found: 1, RuleID
  generic-api-key (entropy 4.9)**; only a keyword-free name (`const PH = '...'`) passed. Gitleaks has no
  posthog-specific rule (0 matches in the binary). The hook's own regex (.githooks/pre-commit:178/:214)
  does not match `phc_`, but its step 4g runs gitleaks (pre-commit:443-480), and CI's secret-scan job
  blocks. Renaming a variable to dodge the scanner is forbidden.
- Client: EAS environment variable `EXPO_PUBLIC_POSTHOG_KEY` (visibility plaintext or sensitive, NOT
  secret - client-side values cannot be secret [docs.expo.dev eas-update/environment-variables]) in the
  `production` environment, optional `EXPO_PUBLIC_POSTHOG_HOST`. `eas update` takes the REQUIRED
  `--environment` flag and uses only that environment's variables [same page]; `EXPO_PUBLIC_*`
  references are replaced in the bundle at build time and must be static `process.env.X`
  [docs.expo.dev guides/environment-variables]. Not app.json `extra` (app.json is pinned by
  nativeBundle.w37 p1/p2 and the variable would still be committed). No `.env` in SmartCompareApp
  (`.env*.local` gitignored); never commit one.
- Backend (Railway web): `ENABLE_POSTHOG_SERVER_CAPTURE` (default off), `POSTHOG_PROJECT_API_KEY`,
  `POSTHOG_HOST` (default EU ingestion). B2: `ENABLE_POSTHOG_PERSON_DELETE`,
  `POSTHOG_PERSONAL_API_KEY`, `POSTHOG_PROJECT_ID`, `POSTHOG_API_HOST`. The pre-commit .env check
  (pre-commit:381-433) refuses any staged diff containing a local `.env` value of a *KEY* variable, so
  local values stay local.
- Host: EU Cloud `https://eu.i.posthog.com` (Sentry is already EU/Germany; EU keeps the s7 transfer list
  short). Must equal the region the owner creates the project in (O-1).
- No-op guarantees: client - no key, no client; backend - flag off or blank key returns before any
  import; the library itself disables on a blank key [client.py `self.disabled = disabled or not
  self.api_key`; RN: "The client will be disabled" on empty key, posthog-rn.ts].
- Tests never write a `phc_` literal: build sentinels at runtime (`'ph' + 'c_' + 'x'.repeat(43)`).

## 6. CSP / network / Sentry (Q6)

- Certificate pinning pins ONLY `web-production-58776.up.railway.app` (+ subdomains)
  (src/services/certificatePinning.ts:69 `BACKEND_HOST`, :98-103 `initializeSslPinning`). PostHog
  hosts are not in the map, so they are unpinned and unaffected; do NOT add them (PostHog rotates
  certs; a pin failure would only drop analytics). No CSP exists in the app.
- Sentry (src/services/sentry.ts:263-283, `sendDefaultPii: false`, scrub hooks): PostHog batch
  requests would appear as http breadcrumbs and spans. Add to `scrubBeforeBreadcrumb` a drop of
  breadcrumbs whose URL host ends with `posthog.com` (minimisation, and the remote-config URL can carry
  the project key). Do not add a `phc_` regex to SENSITIVE_PATTERNS (would need a literal-shaped test).
- Minimisation summary: no `$el_text`, no TextInput values, no route params, no person properties,
  GeoIP off on both SDKs, `$ip` dropped client-side, and the owner turns ON the PostHog project setting
  "Discard client IP data" (otherwise PostHog stores `$ip` with each event, which the inventory treats
  as IP collection, docs/privacy-data-inventory.md:51).

## 7. Legal and store (Q7)

### 7.1 Legal text through U8 (PR "L", on top of #351; #351 must merge first or L rebases on it)
Workflow as #351 (be658fac): edit `app/legal/privacy_policy.md` + `privacy_policy_ar.md` (AR marked for
native review), keep `tests/fixtures/legal_prefill_u8/privacy_policy*.md` in step, run
`scripts/fill_in_legal.py` (variants in `scripts/legal_variants_u8.json` only if a fork/clause is
used), regenerate `landing/privacy.html` + `landing/ar/privacy.html` with
`scripts/render_legal_landing.py`, move the d3c pins (`tests/fixtures/legal_d3c_u8.json`,
tests/test_legal_docs_u8_d3c.py) and add a new D-test file (pattern tests/test_legal_disclosure_s77.py).
Edits (EN; AR mirrors):
- s2 Summary (#351 :15): keep "we do not track you across other companies' apps"; add one sentence:
  we use PostHog to measure how the App is used.
- s3.2 Search records (#351 :30): add that comparison records (product names, result, prices, timing,
  cost) are also sent to PostHog for analytics.
- s3.4 In-app activity (#351 :45): name the taps and screens recorded by PostHog, linked to your
  account number, never what you type; app/device details (model, OS, app version, language, time
  zone).
- s3.6 Why (#351 :53-59): add "In our legitimate interest in understanding and improving the App:
  usage analytics (PostHog). You can switch it off in Profile [if O-3] or object by email."
- s5 Who receives (#351 :73-87): new bullet "PostHog: product analytics; receives your account number
  and the in-app activity and comparison records in sections 3.2 and 3.4, stored in the EU [region per
  O-1]; never your name or email."
- s7 Transfers (#351 :97-99): add PostHog's region; if EU, "Germany (Sentry and PostHog)"; PostHog Inc.
  is a US company - state as the reviewer decides (O-1).
- s8 Retention (#351 :101-111): new line "Analytics records held by PostHog: [1 year on PostHog's free
  plan / 7 years on paid plans; PostHog cannot shorten it]" [posthog.com docs data/events-retention].
- s9 Deletion (#351 :115-117): add PostHog: with B2 "we ask PostHog to delete them when you delete your
  account"; without B2 a manual-deletion sentence with a period (O-5).
- s10 Rights / withdrawing (#351 :119-127): the switch (O-3) and objection by email.
- s14 Device (#351 :145-147): the App also keeps an analytics identifier and a short event queue in app
  storage; signing out clears the identifier.
- s15 / effective date: s15 promises a new effective date on change; T6 moves twelve anchors together
  including `SmartCompareApp/src/services/consent.ts:12` TERMS_VERSION and
  `app/services/consent_service.py:31` (tests/test_legal_docs_u8.py:116-127, :704-719). Bumping is safe
  for build-2 phones (consent records the version sent, `consent_from_fields` consent_service.py:49-74). Decision O-6.
- processors.json new row (app/legal/processors.json): `{"id":"posthog","name_en":"PostHog",
  "name_ar":"PostHog","kind":"processor","personal_data":true,"module":
  ["app/services/product_analytics_service.py","SmartCompareApp/src/services/analytics.ts"],"hosts":
  ["posthog.com","posthog-react-native"],"gate_flag":null}`. T7b scans string literals in app/services
  for `https?://host` (tests/test_legal_docs_u8.py:810-832): the module's default host
  `eu.i.posthog.com` (and B2's `eu.posthog.com`) is covered by `posthog.com` (`_covers` suffix rule).
  T7c needs a CLIENT_PROBES entry (test_legal_docs_u8.py:772-778) `"PostHog (app)":
  ("SmartCompareApp/src/services/analytics.ts", "posthog-react-native")`; add `"PostHog"` to
  SPEC_RECIPIENTS_EN (:782) and `"Posthog"` to CLIENT_CONSTRUCTORS (:756) so the backend constructor
  is caught even without a URL literal. T7a then requires "PostHog" in both policies.
- Landing: landing.brand.s69 jest counts addresses per privacy page (#351 moved it 10 -> 11); adding no
  address keeps it.

### 7.2 Is changing App Privacy while In Review OK? (Apple documents)
App Store Connect Help, Manage app privacy: data-type responses are edited in App Store Connect and
"Updates to data types will be published after you click Publish"; "If your product page isn't live
yet, your responses will be published once your product page goes live"; only privacy-policy URL
changes "release with your next app version"; "You're responsible for keeping your responses accurate
and up to date ... If your app is currently available on the App Store, make sure your responses
reflect the data collected only from that app version." Apple does not say edits are blocked during
review. Reading: the answers are app-level, publishable at any time, and must describe what the LIVE
version collects. Do not change them while build 2 is In Review; publish any change right after
approval and before the OTA reaches phones (section 8).

### 7.3 Inventory, manifest, App Privacy answers
The build-2 manifest (app.json:25-~150, mirrored in docs/privacy-data-inventory.md) ALREADY declares,
all Linked true, Tracking false: ProductInteraction (Analytics, ProductPersonalization), SearchHistory
(AppFunctionality, Analytics, ProductPersonalization), UserID (AppFunctionality, Analytics),
OtherUserContent (AppFunctionality, Analytics), PerformanceData (AppFunctionality, Analytics);
DeviceID (AppFunctionality only); NSPrivacyTracking false. PostHog as designed fits inside these
labels: taps/screens/lifecycle = ProductInteraction; queries and product names = SearchHistory;
distinct_id = UserID; no DeviceID for analytics (`$device_id` scrubbed), no location (GeoIP off, IP
discarded), no crash data (error tracking off). Therefore:
- **app.json manifest: NO change** (and none could reach build 2 by OTA).
- **docs/privacy-data-inventory.md: evidence-only edits** - rows 5 (SearchHistory: + server
  `server_compare_*` capture), 6 (UserID: + PostHog distinct_id), 8 (ProductInteraction: + PostHog
  autocapture, screens, mirroring at api.ts trackEvents); the JSON block and every row's
  type/Linked/Tracking/Purposes stay byte-equal (nativeBundle.w37 c3/c5 deep-equal them to app.json).
  Add a "Not collected" note: PostHog GeoIP off, IP discarded, no `$device_id`.
- **App Store Connect (owner, after approval, before the OTA):** open each of Product Interaction,
  Search History, User ID and confirm "Analytics" is ticked, Linked = yes, Tracking = no; if any is
  missing, add it and Publish. No new data type is needed IF the published answers equal the inventory
  (I could not see ASC; owner verifies - O-7). If the owner declines the `$device_id` scrub or the IP
  discard, Device ID (Analytics) / Coarse Location must be added and the manifest fixed in the next
  binary.

## 8. Sequencing and activation (Q8)

Everything is dark until the owner provides the key; merging any part changes nothing in production.
1. Merge B (server capture, flag OFF; posthog pinned in requirements.in/.txt) - inert.
2. Merge L (legal text) - publishes the policy through the API (`/api/v1/legal/privacy`, served from
   app/legal) and the landing pages after the landing deploy. Text-before-data: L live before step 5.
3. App Review approves build 2; owner releases it manually (UB-R4 style: no OTA to production before
   approval).
4. Owner: create the PostHog project in the chosen region, turn ON "Discard client IP data", note
   retention (plan), create the personal key for B2 if chosen.
5. Owner: Railway web vars `POSTHOG_PROJECT_API_KEY`, `POSTHOG_HOST`; then
   `ENABLE_POSTHOG_SERVER_CAPTURE=true` (read per call, no restart). Verify one own-account compare
   shows `server_compare_completed` in PostHog. (B2 vars + flag at the same time if chosen.)
6. Owner: App Store Connect App Privacy check/publish (7.3).
7. Merge A (client, inert without the variable). Create EAS env var `EXPO_PUBLIC_POSTHOG_KEY`
   (production). `eas update --branch production --environment production` - this is the
   post-approval OTA; verify on a device that taps/screens arrive and that the Auth screens send
   nothing.
Rollback: unset `ENABLE_POSTHOG_SERVER_CAPTURE` (instant); client - republish the previous update or
an update built without the EAS variable (no-op client).

## 9. Tests (RED first)

Client (jest, ts; mocks via moduleNameMapper `^posthog-react-native$` ->
`__mocks__/posthog-react-native.ts` recording calls; jest.config.js:34-40 style; no `virtual: true`):
- `__tests__/analytics/analytics.s77.test.ts`
  a1 no key -> `initAnalytics` builds nothing; identify/reset/screen/mirror are no-ops; no mock calls.
  a2 blank or whitespace key -> same as a1.
  a3 key set -> constructor options: host default EU, `defaultOptIn:false`, `persistence:'file'`,
     `customStorage` is the AsyncStorage mock, `disableGeoip:true`, `enableSessionReplay:false`,
     error-tracking autocapture all off, `before_send` set.
  a4 `identifyUser(id)` -> `optIn` then `identify(id)` with no second argument; never an email/name
     (a User fixture with email + display_name; assert neither string appears in any recorded call).
  a5 `resetAnalytics` -> `reset` then `optOut`.
  a6 `clearSession()` calls `resetAnalytics` (logout, delete-account and dead-refresh paths all go
     through it; one test per path through authService/EditProfileScreen/api.performRefresh mocks).
  a7 `trackScreen` sends the route name only (no params), dedupes repeats, ignores undefined.
  a8 `scrubEvent` drops `$device_id` and `$ip`, strips URL query/fragment, never throws (null on throw).
  a9 a capture before identify is not sent (mock enforces opt-out semantics).
  a10 analytics switch OFF -> identify does not opt in; ON -> it does (O-3).
  a11 no console capture: `console.log` after init produces no capture call.
- `__tests__/analytics/provider.s77.test.tsx`
  p1 `AnalyticsProvider` without a client renders children only (no PostHogProvider).
  p2 with a client: `autocapture.propsToCapture` equals `['testID','ph-label']` (no 'children', no
     'accessibilityLabel', no 'value'), `captureScreens:false`, `captureTouches:true`.
  p3 [SOURCE PIN] each file in the 2.3 list contains `ph-no-capture` on its root JSX element.
- `__tests__/analytics/mirror.s77.test.ts`
  m1 `trackEvents([...])` calls `mirrorEvents` once with the same events and still POSTs.
  m2 a throwing mirror does not stop the POST; a failing POST does not stop the mirror.
  m3 `source_click` url loses query + fragment in the mirrored properties.
- `__tests__/App.analytics.s77.test.ts` [SOURCE PIN, same style as App.pushTap.w315]: `identifyUser`
  next to both `setStableUserId(authUser.id)` sites; `<NavigationContainer` keeps
  `onReady={onNavigationReady}` and gains `onStateChange`; AnalyticsProvider inside it.
- Boot order: bootSentryOrder.w312 stays green unchanged (analytics.ts is not imported by index.ts or
  sentryBootstrap.ts; no module-body construction).
Backend (pytest via the bounded runner; posthog stubbed by injecting a fake module into
`sys.modules["posthog"]` - the real library is installed for GREEN measurements only):
- `tests/test_posthog_server_capture_s77.py`
  b1 flag OFF -> `posthog` never imported (`"posthog" not in sys.modules` after a full
     track_after_persist + log_search run), no client, no `users` read; existing outputs byte-identical
     (same track_event calls, same insert records).
  b2 flag ON + blank key -> same as b1.
  b3 flag ON + key -> exactly one `server_compare_completed` per track_after_persist, distinct_id =
     user_id, properties exactly the 4.3 table keys; `saved` false when comparison_id is None (and
     the existing early return still skips the four follow-ups).
  b4 no email/display_name/access_token anywhere in captured properties (fixture user dict carries
     all three; sentinel strings searched in the serialized call).
  b5 log_search success=False -> one `server_compare_failed` with `error_class` and without the raw
     message; success=True -> nothing.
  b6 capture raising (fake client) -> swallowed, one WARNING with the exception TYPE only; the
     exception message sentinel is absent from caplog.
  b7 off-loop: the fake client's network send is invoked from a non-event-loop thread; constructor
     kwargs include `sync_mode=False`.
  b8 opted-out user (`preferences.analytics_enabled` False) -> no capture; TTL cache hit -> one read.
  b9 query truncated to 200 chars; URL query reduced to host + path.
  b10 shutdown: `_flush_product_analytics` registered after `_drain_background_tasks`; bounded by
     `POSTHOG_SHUTDOWN_FLUSH_TIMEOUT`; no-op when no client.
  b11 (B2) delete-account fires the bulk_delete request with distinct_ids=[user_id] only when its flag
     and both vars are set; failures logged by type.
- tests/test_shutdown_drain.py:961 - arithmetic extended to 20 + 8 + 1.5 < 30 (moved pin).
- tests/test_events_allowlist_superset.py - must stay green unchanged (no new user_events types).
- Legal: new tests/test_legal_posthog_s77.py (D-style, RED at base: PostHog absent from both policies
  and from processors.json) + T7/T7a/T7b/T7c, T6 (if O-6), d3c fixture moves, polish pins.
Source-scanning pins to include in every comm set (memory rule):
- backend: tests/test_legal_docs_u8.py (T7 globs app/services; T7c reads client files),
  tests/test_sentry_channels_u8d_unit.py (AST over app/), tests/test_model_config.py,
  tests/test_model_config_enforced.py, tests/test_hermeticity_pins.py (no network in tests),
  tests/test_auth_error_log_hygiene.py, tests/test_u3b_sharing_branch_removed.py,
  tests/test_u3c_store_false_pin.py, tests/test_w4_13_measurement_truth.py,
  tests/test_w4_13_flag_off_ledger.py (log_search), tests/test_retro_w0_4.py,
  tests/test_retro_w0_4_efg.py, tests/test_retro_w1_2b.py, tests/test_domain_s76.py,
  tests/test_migration_043_delete_user_cascade.py (deletion fence, B2), tests/test_shutdown_drain.py,
  tests/test_health_loop_lag.py, tests/test_events_allowlist_superset.py, the prompt-fence digests;
  plus the direct users of track_after_persist/log_search: tests/test_comparison_id_echo.py,
  test_feedback_service.py, test_cost_meter_s74.py, test_paid_route_metering.py, test_retro_w2_1.py,
  test_s71_u13_compare_auth_required.py, test_s71_u13_pins.py, test_b2_strict_optional_auth.py,
  test_m18_offload_sweep_residual.py, test_m18_preverdict_disconnect_refund.py,
  test_m13_35_sse_disconnect_finally.py, test_text_error_envelope_no_raw_exception.py,
  test_s70_model_router_downgrade.py, test_ci_gates.py (requirements lock / pip-audit).
- client: __tests__/config/nativeBundle.w37.test.ts (d1 unjustified runtime deps - posthog-react-native
  is justified by its import; c3/c5 inventory vs app.json; k5 offline expo-install consistency),
  __tests__/clientTruth/privacyManifest.s74.test.ts, __tests__/bootSentryOrder.w312.test.ts,
  __tests__/App.pushTap.w315.test.ts, App.updateGate.a9, App.distinctRouteNames,
  App.legalRouteHoist.w3-16, landing.brand.s69 (if L touches landing), the full jest suite after the
  install (memory rule for rebased client units).
Gates beyond tests: `tsc --noEmit`; eslint on changed files; `npx expo export --platform ios` bundles
(no network); fingerprint unchanged (section 1); `npm ls`; backend ruff E9/F63/F7/F82 + py_compile;
pip-audit on the new lock.

## 10. Files, risks, limits, owner inputs (Q10)

Files - A (client): SmartCompareApp/package.json + package-lock.json (orchestrator install only),
src/services/analytics.ts (new), src/components/AnalyticsProvider.tsx (new), App.tsx (init, identify x2,
provider, onStateChange), src/services/authService.ts (clearSession -> resetAnalytics),
src/services/api.ts (trackEvents mirror), src/services/sentry.ts (breadcrumb drop), ProfileScreen.tsx +
src/i18n/en.json + ar.json (switch, O-3), the twelve `ph-no-capture` files of 2.3,
__mocks__/posthog-react-native.ts + jest.config.js moduleNameMapper, tests above.
B (backend): requirements.in (+`posthog==<pin>`), requirements.txt (uv compile; new transitive
`backoff`, `distro`; `requests` 2.34.2 and `typing-extensions` 4.16.0 already pinned),
app/services/product_analytics_service.py (new), app/services/feedback_service.py
(track_after_persist + composite passes input_type), app/services/database_service.py (log_search
failure hook), app/main.py (flush handler), app/api/auth_routes.py (toggle key; B2 hook),
tests above. L (legal): app/legal/privacy_policy.md, privacy_policy_ar.md, processors.json,
tests/fixtures/legal_prefill_u8/privacy_policy*.md, landing/privacy.html, landing/ar/privacy.html,
tests/fixtures/legal_d3c_u8.json, tests/test_legal_docs_u8.py (probe/recipient/constructor lists),
new D-test file; if O-6 the twelve date anchors incl. consent.ts and consent_service.py;
docs/privacy-data-inventory.md (evidence text only).

Risks:
- R1 an unseen native dependency in the installed SDK version -> fingerprint gate + bundle gate.
- R2 personal content in touch events through a testID or label not in the 2.3 list -> propsToCapture
  limit + ph-no-capture list + a device QA pass reading 50 raw `$autocapture` events in PostHog.
- R3 identity leak: identify called with an email by a future edit -> a4/b4.
- R4 server capture cost on the loop -> b7 + GREEN measurement; fallback to_thread.
- R5 legal drift: data sent before the text is live -> section 8 order; L must merge and deploy first.
- R6 PostHog event volume/billing (touch autocapture is chatty) -> owner watches the free tier;
  `captureTouches` can be turned off by a later OTA.
- R7 App Privacy mismatch if the published ASC answers differ from the inventory (O-7).
- R8 retention cannot be shortened in PostHog; deletion depends on B2 or a manual process.
Stated limits:
- Phones that never take the OTA send no client events (server events still cover their compares).
- Signed-out funnel (login/register views) is not measured, by design.
- Server failures carry a coarse `error_class`, not the code; exact codes stay in `search_logs`.
- Compares by canary/synthetic accounts are not filtered server-side (filter by user id in PostHog).
- `$autocapture` element names are component display names; readable names need `ph-label`.
- A SIGKILL/OOM loses the server queue (as W1-6).
- I could not see App Store Connect, the PostHog account, or Railway; all statements about them are
  from documentation.

Owner inputs / decisions:
- O-1 PostHog region (recommend EU Cloud) and the project; host values follow; legal s5/s7 wording.
- O-2 the project API key -> Railway `POSTHOG_PROJECT_API_KEY` + EAS `EXPO_PUBLIC_POSTHOG_KEY`;
  turn ON "Discard client IP data".
- O-3 in-app analytics switch (recommended yes) - adds 2.6 and b8/a10.
- O-4 plan / retention (free = 1 year, paid = 7 years) for s8 text.
- O-5 automated person deletion (B2, needs a personal API key with person:write) vs a manual
  deletion process stated in s9.
- O-6 bump the effective date (twelve T6 anchors) for the PostHog text, or keep 2026-10-11 as #351 did.
- O-7 confirm the published App Privacy answers equal docs/privacy-data-inventory.md (Analytics on
  Product Interaction, Search History, User ID).
- O-8 session replay later: needs @posthog/react-native-plugin = a new binary, a new manifest/App
  Privacy review and its own legal text; not in this unit.

## Sources
npm registry posthog-react-native/latest and @posthog/react-native-plugin/latest; app.unpkg.com
posthog-react-native@4.81.0; posthog.com/docs/libraries/react-native (context7
/websites/posthog_libraries_react-native and WebFetch); raw github PostHog/posthog-js
packages/react-native/src/{autocapture.tsx,native-deps.tsx,posthog-rn.ts,logs-defaults.ts};
posthog.com/docs/session-replay/installation/react-native; context7 /posthog/posthog-python and raw
github PostHog/posthog-python posthog/client.py; pypi.org/pypi/posthog/json (7.67.0); context7
/posthog/posthog.com (events-retention, privacy/data-storage); docs.expo.dev/eas-update/
environment-variables and guides/environment-variables; developer.apple.com/help/app-store-connect/
manage-app-information/manage-app-privacy; local gitleaks 8.30.1 run (stdin, no file written).
