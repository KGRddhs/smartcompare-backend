# S81-G6 CLIENT-PERF -- group spec (CL2 CLIENT-SPEED alone; SS1 + CL5 wait as G6b)

Header
- Group: S81-G6 CLIENT-PERF, LC-9 SAFE group with ONE unit (CL2). SS1 + CL5 PROGRESSIVE PAINT are G6b, gated on owner item 19 (the #118 cert-pinning device check, OWNER_ACTIONS_S81.md:34).
- Branch: feature/s81-g6-client-perf. Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-g6 (detached at base). Base sha: ec747b496953869c0370e4f28bf025c6f694a97d.
- Lane: client (SmartCompareApp). Flags: NONE (client units are not flag-gated; the OTA is the gate; #377 added no features.ts constant). Backend: no app/ file, no ENABLE_* name.
- git status --short of the worktree: empty before every probe and after (only this untracked, gitignored .qa-s80/ file is new; `git check-ignore -v .qa-s80/x.md` -> `.gitignore:72:.qa-*/`).
- Measurement location: <scratchpad>/g6/ (probe_metro.js, probe_metro2.js, probe_tx.js, export_base.log, jest_base_touched.log, be_pins_base.log, jest_comm.txt, sca_scanners.txt). Scratchpad = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/bd48b535-2d58-47fc-9bbe-cf719f400b7b/scratchpad.
- Personal data: none in any file; synthetic ids only (`u-a`, `u-b`, `https://img.example.test/a.jpg`), built at run time where a shape matters.
- Evidence pointers: PLAN_S81.md :47 (speed findings), :99 (client rules), :177 (CL2 unit text), :222 (Atlas gate rule); specs/S81_G6_BRIEF.md (rules (a)-(f), Q1-Q10); PLAN_S80.md section 0 (contract freeze: image_url is an absolute https raster URL or null, item 4).

## 0. The group

0.1 Units: CL2 CLIENT-SPEED (lane client, ships in the OTA "with the first KB-first canary", after the first review-safe OTA = S81-08 + S81-11 + consent v3; UB-R4: nothing merges into the build-3 binary, app.json, native folders or a permission string).

0.2 Flags: none. No features.ts constant (features.ts:52 `ENABLE_EXPO_FETCH_SSE_DEFAULT = false` and its override :59 / getter :115-119 untouched); the SSE flags ENABLE_EXPO_FETCH_SSE_DEFAULT / ENABLE_PREVERDICT_DISCONNECT_ABORT / ENABLE_FULL_STREAM_DEADLINE untouched (G6b). Knob CONSTANTS (code constants, not flags): HOME_FLOOR_MS = 400, HOME_FLOOR_SKIP_BELOW_MS = 300, REVEAL_DELAY_MS = 800 (unchanged value), SWR_FOCUS_THROTTLE_MS = 30000, PREFETCH_MAX_URLS = 2, PREFETCH_URL_MAX_LEN = 2048, PREFETCH_SEEN_MAX = 32.

0.3 DEFECT id (draft, names only; no DEFECT_LEDGER row exists): `MYEZ-S81-CL2 CLIENT-SPEED` -> no flag -> RED nodes `SmartCompareApp/__tests__/cl2/*.cl2.test.ts(x)` -> PR (one) -> status MERGED-DARK-UNTIL-OTA. Closes the PLAN_S81 :47 speed findings "1.2 s floor + 800 ms reveal", "serial storage reads", "198,567 B dead Sentry replay code", "History refetches 50 rows per focus" (the last only on tab switches, see 2.4).

0.4 Change list (CL2, the eight plan changes as re-cut by the brief and by this spec):
- C1 Home floor: skip under 300 ms, else 400 ms (A17 rule reused at HomeScreen.tsx:200).
- C2 Reveal cut: the 800 ms winner-reveal timer (ResultsScreen.tsx:460-476) collapses to 0 when the result is in the route params at mount ("fast hit").
- C3 Image.prefetch of the two product images at result arrival (bounded, https only, fire-and-forget).
- C4 History SWR in memory per user + throttled focus refetch (30 s), invalidated on every Results mount and on a delete; pull-to-refresh / search / retry always live. HOME IS EXCLUDED (2.4: the :167 refetch feeds the quota pill's +bonus count, a quota surface).
- C5 metro.config.js: `getSentryExpoConfig(__dirname, { includeWebReplay: false })` composed with `qarenCacheVersion`.
- C6 Lazy-loaded Legal / Paywall / Onboarding (legacy + NewOnboardingHost) / ScanCamera / InviteeQuiz / ReferralLanding through ONE helper (React.lazy + Suspense, fallback null), the binding names kept.
- C7 Parallel boot read: getStableId() started before `await getSavedLanguage()` (the only independent pair in App.tsx's init); every effect in the same order.
- C8 freezeOnBlur: true on the Tab navigator's screenOptions.
- EXCLUDED: the Geist runtime-load drop (fonts.ts untouched; CL2b after the TestFlight device check), SS1 / CL5 (G6b), expo-image (NT1), any authService.ts change.

0.5 Files two units share: none (one unit). Within CL2 the shared hot files and the order GREEN applies them: (1) the new leaves src/utils/clientSpeed.ts, src/services/swrCache.ts, src/services/imagePrefetch.ts, src/navigation/lazyScreen.tsx; (2) metro.config.js; (3) HomeScreen.tsx; (4) ResultsScreen.tsx; (5) HistoryScreen.tsx; (6) App.tsx (C6, C7, C8 and the one setSwrUser effect in one edit pass); (7) the E-row test edits; (8) CLAUDE.md block. Known rebase neighbours: S81-11 HONEST-FRAGRANCE-UI (ResultsContent, ReferralLanding, InviteeQuiz, HomeScreen QUICK_CATS) and CL3 (ResultsScreen) may touch the same screens: a rebase hunk, never a contract dependency.

## Unit CL2

### 1. Base state (measured at ec747b49 in this run)

1.1 Toolchain through the junction (checked: node_modules/@babel/core and node_modules/.bin/jest exist). Installed versions (read from node_modules/*/package.json): react-native 0.81.5, react 19.1.0, react-native-screens 4.16.0, @react-navigation/native 7.2.4, native-stack 7.15.0, bottom-tabs 7.16.0, @react-navigation/core 7.17.4, @sentry/react-native 7.2.0, expo 54.0.34 (package.json pins ~54.0.37: installed drift, the known nativeBundle.w37 class), expo-font 14.0.11, metro 0.83.3, jest 29.7.0, typescript 5.9.3, eslint 9.39.4; jest-expo NOT installed. jest.config.js: preset ts-jest, testEnvironment node, `^react-native$` mapped to __mocks__/react-native.ts (its `Image` at :16 is a function component WITHOUT `prefetch`), setupFilesAfterEnv __tests__/setup.ts. tsconfig extends expo/tsconfig.base, strict.

1.2 Line endings: every touched file is CRLF in the working copy, LF in the index (`git ls-files --eol`: i/lf w/crlf; core.autocrlf=true). Bytes / CRLF / non-ASCII / sha256[:16] at base:
| file | bytes | CRLF | >127 | sha256[:16] |
|---|---|---|---|---|
| SmartCompareApp/App.tsx | 23686 | 501 | 132 | ef0669d1d0c13c18 |
| SmartCompareApp/metro.config.js | 853 | 17 | 0 | 20fa442d837d3eba |
| SmartCompareApp/src/screens/HomeScreen.tsx | 62925 | 1588 | 241 | bee8b92730e6d74f |
| SmartCompareApp/src/screens/HistoryScreen.tsx | 48215 | 1378 | 196 | 210c5c091bff51bd |
| SmartCompareApp/src/screens/ResultsScreen.tsx | 47107 | 1101 | 252 | a1448cbd95436f70 |
| __tests__/metro.cacheVersion.pb1.test.ts | 11249 | 269 | 24 | a2c950ec969545a7 |
| __tests__/HomeScreen.bundleB.contract.test.tsx | 20350 | 434 | 150 | 679afdb566cf3375 |
| __tests__/HomeScreen.eS3hf.dedupe.test.tsx | 5791 | 130 | 39 | 446051e35ff10270 |
| __tests__/HomeScreen.eS3hf.loaderVisibility.test.tsx | 11884 | 361 | 36 | 601a3d7a3698c570 |
The existing non-ASCII bytes are comment punctuation; new lines are pure ASCII; a whole-file diff in `git diff --stat` is a defect (Edit tool preserves CRLF; new files are written LF like the repo's other new client files, then normalised by git).

1.3 Entry and boot (Q2). index.ts:6 `import './src/services/sentryBootstrap';` is the FIRST import (W3-12; pinned by bootSentryOrder.w312); sentryBootstrap.ts imports only `./sentry` (:22) and calls initSentry() (:24). App.tsx init() (:194-244), all SERIAL: :198 `const lang = await getSavedLanguage();` (AsyncStorage read, src/i18n/index.ts:17-25, swallows its own error) -> :199 `await i18n.changeLanguage(lang)` -> :200 `await bootstrapRtl(lang)` (may `Updates.reloadAsync()` the bundle once, rtlBootstrap.ts:11-12) -> :207 `const initialId = await getStableId();` (SecureStore read, lazily CREATES the device id on first call, featureBucket.ts:70-88, swallows SecureStore errors) -> :208 setFlagStableId -> :216-243 `await initializeAuth(cb)` in its own try/catch (authService.ts:809-835: getSavedUser then getToken, serial, then a fire-and-forget network refresh). :263-269 `init().catch(...).finally(() => setIsLoading(false))`. Independence: getStableId depends on nothing above it; initializeAuth must stay after bootstrapRtl (it starts a background token refresh; starting it before a possible RTL reload could rotate a refresh token mid-reload = an auth hazard) and its internal reads live in authService.ts (auth, FOCUS: untouched). The other boot reads the brief lists (aiConsent.ts :81/:126, onboardingResume.ts :156, onboardingDraft.ts :134, pushPrePrompt.ts :57, demographicsTrigger.ts :63, deviceFingerprint.ts :77) are NOT in App's mount chain: `grep` of App.tsx for those module names = 0 matches; they run in their own consumers. So the one parallel pair is (getSavedLanguage, getStableId).

1.4 Navigators (App.tsx). Static screen imports :37-65 (Splash :37, Onboarding :38, NewOnboardingHost :41 named export, Login :49, Register :50, ForgotPassword :51, ResetPassword :52, Home :53, Results :54, Legal :56, ContactUs :57, EditProfile :58, EditPreferencesFlow :59, History :60, Profile :61, ReferralLanding :62, InviteeQuiz :63, ScanCamera :64, Paywall :65, UpdateRequired :72). AuthStack.Screen :106-113; Tab.Navigator screenOptions :122-134 (headerShown, tint colours, tabBarStyle, tabBarLabelStyle; NO freezeOnBlur); Tab.Screen :136-167 (HomeTab component, HistoryTab render-prop with onLogout, ProfileTab render-prop); root Stack.Screen: Auth :367, Onboarding :372-383 (legacy OnboardingScreen or NewOnboardingHost by features.ENABLE_NEW_ONBOARDING), Main :386, Results :389-393, ContactUs :394-398, EditProfile :399-406, EditPreferences :407-411, OnboardingEdit :426-444, ScanCamera :446-450, Paywall :454-462 (transparentModal), ReferralLanding :477-480, InviteeQuiz :481, Legal :488-492. UpdateRequired is rendered outside the navigator (:357-359). User state: setUser at :218, :233, :283 (null, onSessionInvalid), :309, :334 (null, handleLogout). `grep -rn "React.lazy|lazy(|Suspense|enableFreeze|freezeOnBlur|Image.prefetch"` over src + App.tsx = 0 matches. No ErrorBoundary anywhere in src (grep 0); Sentry.wrap (sdk.js:126-138 on 7.2.0) adds TouchEventBoundary + Profiler + FeedbackWidgetProvider, NO error boundary.

1.5 Sign-out paths (Q6). Every path ends in clearSession() (authService.ts:688-699: epoch bump then three deletes) and then a user-state downgrade in App: user logout ProfileScreen.tsx:302-303 (logout() + onLogout -> handleLogout App.tsx:330-335), HistoryScreen.tsx:916-917 (clearSession + onLogout), account delete EditProfileScreen.tsx:147 (clearSession + onAccountDeleted = handleLogout), dead session api.ts:149-150 / :166-170 (clearSession + emitSessionInvalid -> App listener :279-286), camera sign-in ResultsScreen.tsx:780-781 (clearSession + emitSessionInvalid). Every one reaches App's `setUser(null)` (:283 or :334). The user-id change points are the five setUser calls above.

1.6 Timings (Q1). HomeScreen.tsx:195-221: `loadingStartedAtRef` (:198) is set at compare start (:390 SSE path, :559 URL path); :200 `const MIN_LOADING_MS = 1200;`; navigateToResultsWithFloor (:201-221) computes `remaining = Math.max(0, MIN_LOADING_MS - elapsed)` and either advances now or `advanceTimerRef.current = setTimeout(advance, remaining)`; advance navigates `Results` with `{ result }` then setLoading(false). Callers: :446 `navigateToResultsWithFloor(data)` (stream / REST text compare), :598 `navigateToResultsWithFloor(response.data)` (URL compare). Home renders the loader with variant="concentric" (:1206-1207), so LoadingScreenVariants' StreamingCardsVariant reveal (REVEAL_STAGE_MS = 400 at :427, used :448) is NOT on the Home path: it is not the plan's "800 ms reveal". The 800 ms reveal is ResultsScreen.tsx:460-476: a mount effect `setTimeout(..., 800)` that sets winnerRevealed (gates RevealBurst, ResultsContent.tsx:469), springs winnerScale, marks `ready_celebration`, fires a Medium haptic, and marks `user_tappable` 420 ms later (also cited in session-72 READINESS_CLIENT.md:88 and session-80 COMPACT.md:249). ResultsScreen.tsx:139-141 CAMERA_FLOOR_MS = 1200, HISTORY_FLOOR_MS = 400, HISTORY_FLOOR_SKIP_BELOW_MS = 300; A17 rule :232-246 (`if (elapsed > SKIP) wait FLOOR - elapsed`); camera floor :320-325 unchanged by CL2. `result` state is seeded from route.params.result (:154-156); loadingResult is true only for comparison_id / vision_products (:157-160).

1.7 History (C4). HistoryScreen.tsx: state :649 history, :656 initialLoading(true), :659 total, :665 appliedQuery; loadHistory :690-714 (getComparisonHistory(50, 0, query) -> setHistory/setTotal; 401 -> authError + []; other error -> loadError; finally clears initialLoading/refreshing/searching); the A12 focus effect :719-723 refetches on EVERY focus with appliedQueryRef.current; applyQuery :725-733, onRetryLoad :744-747, onRefresh (pull-to-refresh) :749-752; delete :808-818 (deleteComparison then filter + total-1). HistoryScreen receives no user; getComparisonHistory (api.ts:477-482) sends no lang. Bottom-tab screens stay mounted after first focus, so the every-focus refetch is the tab-switch cost.

1.8 Home focus effects (C4 re-cut). :167-192 getReferralStatus on every focus -> bonusInfo, rendered as the quota pill's `+N` and in its a11y label (:989, :995, :1034-1052) = a quota-display surface; :276-292 checkServer (an unconsumed /health ping kept for telemetry) + loadUser + loadRecentSearches (local AsyncStorage reads). Neither is throttled by CL2 (2.4).

1.9 Sentry Metro wrapper (Q3), measured on the installed 7.2.0 (node_modules/@sentry/react-native/metro.js -> dist/js/tools/metroconfig.js). getSentryExpoConfig(projectRoot, options) (:54-74): sets process.env.___SENTRY_METRO_DEV_SERVER___='true'; calls expo's getDefaultConfig(projectRoot, {...options, unstable_beforeAssetSerializationPlugins: [releaseConstants (web only, injectReleaseForWeb default true), debugId plugin]}); withSentryFramesCollapsed (symbolicator.customizeFrame); withSentryResolver ONLY when `includeWebReplay === false` (:67-69; the resolver returns `{type:'empty'}` for /@sentry(?:-internal)?\/replay/ on every platform, :124-129); withSentryMiddleware (server.enhanceMiddleware, dev server only). Options on 7.2.0: annotateReactComponents, includeWebReplay, enableSourceContextInDevelopment, getDefaultConfig, injectReleaseForWeb (metroconfig.d.ts); NO includeWebFeedback (8.10 = NT1). Probe (probe_metro2.js, node, offline): stock-vs-stock control diff = []; stock-vs-Sentry diff = exactly `resolver.resolveRequest null -> fn`, `server.enhanceMiddleware`, `symbolicator.customizeFrame` (the serializer plugins live inside expo's customSerializer closure, not visible as a key diff); stock cacheVersion "1.0" in both; qarenCacheVersion(stock) === qarenCacheVersion(sentry) = true; the Sentry resolver maps `@sentry-internal/replay` on ios to {"type":"empty"} and passes `react` through. Stock transform options (probe_tx.js): experimentalImportSupport true, inlineRequires false; asyncRequireModulePath expo/internal/async-require-module.

1.10 Byte proxy and lazy form (Q4, Q8). ONE offline export at base (EXPO_OFFLINE=1 CI=1, 600 s bound): `node node_modules/expo/bin/cli export --platform ios --output-dir <scratch>/g6/export_base` rc=0 in 63 s: "iOS Bundled 42988ms index.ts (2211 modules)", ONE bundle `_expo/static/js/ios/index-fc5613a1f22d1cae70c4fe5607e62a6f.hbc` = 6,594,787 bytes (sha256[:16] 1b56f83887b2611a); the bundle carries Sentry replay code (`grep -c -a`: rrweb 3, replayIntegration 1, ReplayContainer 1). The base already has dynamic imports (ResultsScreen.tsx:239 `await import('../services/api')`, authService.ts `await import('./onboardingDraft')`) and the export still emits ONE native bundle: on native, Expo 54 / Metro keep `import()` targets in the main bundle and defer only their EVALUATION (no chunk split). So C6 saves module-evaluation time at boot, not bytes; C5 is the byte change. git status after the export: clean (.expo/ and dist/ are gitignored; no .expo dir was left in SmartCompareApp).

1.11 Tests reading the touched files. No jest suite renders the real App component (grep for an App import = 0); App.tsx is read as SOURCE by 10 App.* suites + bootRegressionPins / bootSentry* (w312BootSandbox executes App's module body with stubbed imports; unknown local modules become callable Proxy stubs, w312BootSandbox.ts:95-112) + paywall.noSubscriptionUi.s69 (:244 `name="Paywall"[\s\S]{0,80}component=\{PaywallScreen\}`) + App.legalRouteHoist.w3-16 + App.distinctRouteNames. The B5 boot pin App.bootGuard.b5 extracts the init block (BLOCK_START `    async function init() {`) and asserts `await getSavedLanguage()` (:138), `await initializeAuth(` (:139), stubs getStableId with mockResolvedValue (:73) and a SYNC throw (:181-183). Snapshot files (17) cover components only (none of App, the six lazy screens, Home, History or Results). The jest comm set by the union rule = 125 suites (list in <scratchpad>/g6/jest_comm.txt; rule in section 7).

1.12 Base pass state (bounded runners, this run):
- jest, 14 touched suites: `[jest] tag=g6spec-base-touched start=03:11:18 end=03:11:34 rc=0` -> Test Suites 14 passed; Tests 137 passed, 5 todo (metro.cacheVersion.pb1, App.bootGuard.b5, bootRegressionPins.w312, bootSentryOrder.w312, bootSentryAlarm.w312, HomeScreen.bundleB.contract, HomeScreen.eS3hf.dedupe, HomeScreen.eS3hf.loaderVisibility, HistoryScreen.searchState.a12, screens/paywall.noSubscriptionUi.s69, App.legalRouteHoist.w3-16, App.distinctRouteNames, App.bootOptimistic.a3, rtlBootstrap.s69).
- backend pins (section 7.3): `[pyt] tag=g6spec-be-pins start=2026-11-05 03:10:52 end=2026-11-05 03:11:06 elapsed=14s bound=1200s status=OK rc=0` -> 210 passed (netguard lines: sentinel / egress neutralised in test_security_regression.py, no real egress).
- Full jest baseline (orchestrator, S83 final rounds 2026-11-05): 3,794 passed + the four config/nativeBundle.w37 drift nodes red; 413 files under __tests__ (395 *.test.ts(x) by find). Not re-run by this spec (LC-7: once, in the last round).

### 2. Contract

2.1 No flag, no backend change, no request/response change (contract_freeze: nothing the client sends or reads changes; the prefetch reads `overview.products[i].image_url`, documented absolute https raster URL or null). Main invariant (replaces flag-OFF identity): SAME screens, SAME strings, SAME order of effects; only timing, caching and module evaluation move. No i18n key added or changed (en/ar parity and .copy-policy.json fences untouched; [NATIVE READ] list EMPTY); no analytics event added (test_events_allowlist_superset scans src/).

2.2 New modules (leaves; signatures binding):
- src/utils/clientSpeed.ts (no imports): `export const HOME_FLOOR_MS = 400; export const HOME_FLOOR_SKIP_BELOW_MS = 300; export const REVEAL_DELAY_MS = 800;` `export function homeFloorDelayMs(elapsedMs: number): number` = `Number.isFinite(elapsedMs) && elapsedMs > HOME_FLOOR_SKIP_BELOW_MS ? Math.max(0, HOME_FLOOR_MS - elapsedMs) : 0` (A17 boundary: exactly 300 renders now; negative / NaN render now); `export function revealDelayMs(resultPresentAtMount: boolean): number` = present ? 0 : REVEAL_DELAY_MS.
- src/services/swrCache.ts (NO imports, in-memory only, never AsyncStorage): `SWR_FOCUS_THROTTLE_MS = 30000`; `setSwrUser(userId: string | null): void` (a different id, including null, CLEARS every entry; the same id is a no-op); `swrRead<T>(key: string): { data: T; fetchedAt: number } | undefined` (undefined when no user); `swrWrite<T>(key: string, data: T, now = Date.now()): void` (no-op when no user); `shouldRefetchOnFocus(key: string, now = Date.now()): boolean` (true when no user, no entry, or `now - fetchedAt >= SWR_FOCUS_THROTTLE_MS`); `invalidateSwrPrefix(prefix: string): void`; `clearSwrCache(): void` (also resets the user; test seam).
- src/services/imagePrefetch.ts (imports `Image` from react-native only): `prefetchProductImages(result: unknown): void` -- reads `result.overview.products ?? result.products`, takes the first PREFETCH_MAX_URLS = 2 entries, keeps `image_url` strings that start with `https://` and are at most 2048 chars, skips any URL in a module FIFO seen-set (max 32), then for each: `try { const p = Image.prefetch(url); if (p && typeof p.catch === 'function') p.catch(() => undefined); } catch {}`; guard `Image && typeof Image.prefetch === 'function'` (the jest mock has none); returns undefined synchronously; never awaited; never logs a URL.
- src/navigation/lazyScreen.tsx: `export function lazyScreen<P>(load: () => Promise<{ default: React.ComponentType<P> }>): React.ComponentType<P>` = `const Lazy = React.lazy(load); return function LazyScreen(props) { return <Suspense fallback={null}><Lazy {...props} /></Suspense>; }`; no Text, no useTranslation, no error UI, no import of any screen.

2.3 Edits (binding behaviour):
- C1 HomeScreen.tsx: :200 `const MIN_LOADING_MS = 1200;` removed; :205 becomes `const remaining = homeFloorDelayMs(elapsed);` (import from '../utils/clientSpeed'); `advance`, `advanceTimerRef`, `setTimeout(advance, remaining)`, the unmount and cancel clears unchanged (gateB pins). First statement of navigateToResultsWithFloor: `prefetchProductImages(result);` (C3).
- C2 ResultsScreen.tsx: the mount effect :460-476 reads `const delay = revealDelayMs(!!route?.params?.result);` at mount and passes it to the existing setTimeout (`setTimeout(async () => {...}, delay)`); the body (setWinnerRevealed, spring, ready_celebration, haptic, user_tappable +420) unchanged; history (comparison_id) and camera (vision_products) paths keep 800.
- C3 ResultsScreen.tsx: a new effect `useEffect(() => { prefetchProductImages(result); }, [result]);` (the Home path is de-duplicated by the seen-set).
- C4 ResultsScreen.tsx: a new mount effect `useEffect(() => { invalidateSwrPrefix('history:'); }, []);` (any Results view may have saved a comparison). HistoryScreen.tsx: key = `'history:' + query`; initial state from `swrRead('history:')` (history, total; initialLoading = !cached); loadHistory writes `swrWrite(key, { comparisons, total })` on success only (401 / error never stamp); the :719-723 focus effect becomes `if (shouldRefetchOnFocus('history:' + appliedQueryRef.current)) loadHistory(appliedQueryRef.current);`; applyQuery / onRetryLoad / onRefresh unchanged (always fetch); the delete success branch adds `invalidateSwrPrefix('history:');`. App.tsx: ONE call line, a new effect after the onSessionInvalid effect (:279-286): `useEffect(() => { setSwrUser(user?.id ?? null); }, [user?.id]);` -- it fires on every sign-out (setUser(null) at :283 and :334 = every path in 1.5) and on every user-id change (:218, :233, :309). authService.ts is NOT edited (rule (c): no token / session / refresh line moves; the alternative line in clearSession() :688 is Q-OQ2).
- C5 metro.config.js: `const { getSentryExpoConfig } = require('@sentry/react-native/metro');` replaces the expo/metro-config require; `const config = getSentryExpoConfig(__dirname, { includeWebReplay: false });`; `config.cacheVersion = qarenCacheVersion(__dirname, config.cacheVersion);` unchanged (once); the comment block keeps `P-B1-CACHE` and replaces "This is the ONLY deviation from the stock Expo default config" with a sentence naming the two deviations (the Sentry wrapper and the cache key).
- C6 App.tsx: the static imports of LegalScreen (:56), ReferralLandingScreen (:62), InviteeQuizScreen (:63), ScanCameraScreen (:64), PaywallScreen (:65), OnboardingScreen (:38) and NewOnboardingHost (:41) become `const LegalScreen = lazyScreen(() => import('./src/screens/LegalScreen'));` (and so on; `const NewOnboardingHost = lazyScreen(() => import('./src/screens/onboarding/NewOnboardingHost').then((m) => ({ default: m.NewOnboardingHost })));`), placed after the last static import; every `component={X}` / `<X .../>` use and every route name unchanged. index.ts untouched (sentryBootstrap stays first). Eager (unchanged): Splash, Login, Register, ForgotPassword, ResetPassword, Home, Results, History, Profile, ContactUs, EditProfile, EditPreferencesFlow, UpdateRequired.
- C7 App.tsx init(): first statements `const stableIdP = Promise.resolve().then(getStableId); stableIdP.catch(() => undefined);` then `const lang = await getSavedLanguage();` (literal kept: B5 :138), changeLanguage, bootstrapRtl unchanged, then `const initialId = await stableIdP;` replaces :207; everything after unchanged. Semantics kept: a rejecting / throwing getStableId still rejects init (outer catch -> finally setIsLoading(false); initializeAuth not called), no unhandled rejection (the attached catch), the effect order changeLanguage -> bootstrapRtl -> setFlagStableId -> initializeAuth unchanged. Only the SecureStore read (and a first-run id write) overlaps the AsyncStorage read.
- C8 App.tsx: `freezeOnBlur: true,` added inside the Tab.Navigator screenOptions (:123-134). AuthStack and root Stack screenOptions stay `{ headerShown: false }`. No enableFreeze() call. bottom-tabs 7.16.0 types.tsx:300-307 documents the option ("Requires react-native-screens >=3.16.0"; installed 4.16.0); BottomTabView passes it to MaybeScreen (ScreenFallback.tsx: only when Screens.screensEnabled()); in jest App is never rendered, so inert.

2.4 Home SWR re-cut (deviation from PLAN_S81 :177, stated): the Home :167 focus refetch drives the quota pill's `+bonus` count (a quota surface under LC-1); throttling it would show a stale count for up to 30 s after a compare or a referral credit, so CL2 does NOT throttle it; the :276 effect is local reads + a telemetry ping, nothing to cache. Throttling Home is a FOCUS unit of its own if ever wanted.

2.5 Failure table
| event | behaviour |
|---|---|
| Image.prefetch rejects / throws / is undefined | swallowed; render unchanged (ProductImage still loads its own URI) |
| image_url null / http / data: / > 2048 chars / third product | not prefetched |
| SWR cache miss / no user set | today's path (fetch on focus; spinner first paint) |
| fetch fails (401 or other) | no stamp; next focus refetches; mounted state as today |
| new compare viewed | Results mount invalidates history:* -> next History focus refetches |
| delete row | invalidates history:*; mounted list already filtered |
| pull-to-refresh / search submit / retry | always fetch (never throttled) |
| first History focus after sign-in | cache cleared by setSwrUser on the user change -> fetch |
| lazy screen module body throws / import rejects | the error propagates (no ErrorBoundary exists in src, measured; Sentry global handler reports); today the same throwing body crashes at boot. On native the module is in the same bundle (1.10), so no chunk-load failure class |
| lazy screen first open | Suspense fallback null until the import() promise settles (module evaluation + one commit); NOT MEASURED on device (9) |
| getStableId rejects or throws | init rejects as today; splash released by finally; no unhandled rejection |
| bootstrapRtl reloads the bundle | the first-run device-id write may already have happened (base: it happened on the next boot) -- harmless, same id store |
| Sentry metro resolver | only @sentry(-internal)/replay resolves empty; every other module via the original resolver |

2.6 Seams: clientSpeed pure functions; swrCache `clearSwrCache` + `now` params; imagePrefetch reads `require('react-native').Image.prefetch` at call time (tests assign a jest.fn on the mapped mock module); lazyScreen takes the loader; App boot block via the B5 extraction harness; metro config by `require('../metro.config.js')`.

### 3. Change list (opens with byte copies; GREEN takes shutil.copyfile byte copies of every edited file under <scratchpad>/g6/bytes/ first)
1. NEW SmartCompareApp/src/utils/clientSpeed.ts
2. NEW SmartCompareApp/src/services/swrCache.ts
3. NEW SmartCompareApp/src/services/imagePrefetch.ts
4. NEW SmartCompareApp/src/navigation/lazyScreen.tsx
5. EDIT SmartCompareApp/metro.config.js (C5)
6. EDIT SmartCompareApp/src/screens/HomeScreen.tsx (C1, C3)
7. EDIT SmartCompareApp/src/screens/ResultsScreen.tsx (C2, C3, C4 invalidation)
8. EDIT SmartCompareApp/src/screens/HistoryScreen.tsx (C4)
9. EDIT SmartCompareApp/App.tsx (C4 effect, C6, C7, C8)
10. EDIT tests (E-rows 4.1): __tests__/metro.cacheVersion.pb1.test.ts, __tests__/HomeScreen.bundleB.contract.test.tsx, __tests__/HomeScreen.eS3hf.dedupe.test.tsx, __tests__/HomeScreen.eS3hf.loaderVisibility.test.tsx
11. NEW RED files __tests__/cl2/*.cl2.test.ts(x) (section 5; written by the RED agent, frozen)
12. EDIT CLAUDE.md (one block, section 8)
No other file: not package.json / package-lock.json / app.json / metro.cacheVersion.js / babel.config.js / index.ts / src/services/sentryBootstrap.ts / src/services/authService.ts / src/config/features.ts / src/theme/fonts.ts / src/i18n/* / any .snap / any native folder / any backend file.

### 4. Existing pins

4.1 Deliberate changes (E-rows; amended by GREEN with the reason in a comment, never weakened beyond the stated intent)
| E | file:line | base assertion | amended to | reason |
|---|---|---|---|---|
| E1 | __tests__/metro.cacheVersion.pb1.test.ts:254 | `expect(src).toContain("require('expo/metro-config')")` | `toContain("require('@sentry/react-native/metro')")` + `toMatch(/getSentryExpoConfig\(\s*__dirname\s*,\s*\{\s*includeWebReplay:\s*false\s*\}\s*\)/)`; :252-253 (P-B1-CACHE comment positive control) and :256-259 (one cacheVersion assignment, the cacheVersion require, module.exports) kept; :137-153 kept (the stock-config sanity at :152 still requires expo/metro-config directly) | C5 changes the config's provenance; every cacheVersion assertion stays |
| E2 | __tests__/HomeScreen.bundleB.contract.test.tsx:219-221 | `MIN_LOADING_MS\s*=\s*1200` in HomeScreen | HomeScreen imports homeFloorDelayMs from '../utils/clientSpeed' and clientSpeed.ts declares `HOME_FLOOR_MS = 400` and `HOME_FLOOR_SKIP_BELOW_MS = 300`; the section heading comment says the A17 rule; :223-226 (loadingStartedAtRef rows) unchanged | C1 |
| E3 | __tests__/HomeScreen.eS3hf.dedupe.test.tsx:91-94 | same regex | navigateToResultsWithFloor present + `homeFloorDelayMs(` used in HomeScreen | C1 |
| E4 | __tests__/HomeScreen.eS3hf.loaderVisibility.test.tsx:217-265 | SSE response at 100 ms keeps the loader, navigate after +1200 | response at 350 ms keeps the loader mounted; +49 still mounted, +1 (t=400) navigates and the loader unmounts after navigate | C1: under 300 ms renders now (RED R5 covers that band); the anti-regression intent (no bare Home before navigate) kept in the floored band |
| E5 | same file :267-306 | URL response at ~0 ms keeps the loader, navigate after +1200 | the api.post mock resolves through a deferred released after advanceTimersByTime(350); then loader mounted, +50 navigates | C1 |
No other existing assertion changes. In particular App.bootGuard.b5 :138 (`await getSavedLanguage()`) stays green by construction of C7; paywall.noSubscriptionUi.s69 :244, App.legalRouteHoist, App.distinctRouteNames stay green because the binding names and route registrations are unchanged; HomeScreen.minDisplayFloor.test.ts tests a local replica (its own `MIN_LOADING_MS = 1200` at :13) and stays green (a stated limit: that suite never read the source constant); HistoryScreen.searchState.a12 :155-180 stays green because no user is set in that suite (no user = every focus refetches).

4.2 Must stay green: the 125-suite jest comm set (section 7.1, incl. bootSentryOrder / bootSentryAlarm / bootRegressionPins (the boot sandbox must parse App.tsx's `import()` and call the stubbed lazyScreen), App.*, HomeScreen.*, HistoryScreen.*, ResultsScreen.* incl. the client fence ResultsScreen.timeout, Screens.bundleD.contract (:75 CAMERA_FLOOR_MS = 1200), consent/aiDispatchFence.s69, navigation.branchRootExit.w34, theme/fonts + cairoSubpathImports, i18n parity, copy-policy, every snapshot suite with NO .snap change), tsc, eslint by path, and the backend pins of 7.3.

### 5. RED tests (the RED agent writes them; each fails at base on an AssertionError only: a module that does not exist is read through a `loadOptional(relPath)` helper (try { return require(p) } catch { return null }) and asserted, never imported at top level; static rows read files with fs.readFileSync, CRLF normalised; PIN rows are green at base with a recorder)

Files: __tests__/cl2/clientSpeed.cl2.test.ts, homeFloor.cl2.test.tsx, revealCut.cl2.test.tsx, imagePrefetch.cl2.test.ts, swrCache.cl2.test.ts, historySwr.cl2.test.tsx, sessionClear.cl2.test.ts, metroSentry.cl2.test.ts, lazyScreens.cl2.test.tsx, bootParallel.cl2.test.ts, freezeOnBlur.cl2.test.ts, scope.cl2.test.ts.

| # | file | test | assertion | at base | satisfied by |
|---|---|---|---|---|---|
| R1 | clientSpeed | exports | module loads; HOME_FLOOR_MS 400, HOME_FLOOR_SKIP_BELOW_MS 300, REVEAL_DELAY_MS 800, two functions | RED (null) | 2.2 |
| R2 | clientSpeed | floor table | homeFloorDelayMs: -50->0, 0->0, 100->0, 300->0, 301->99, 350->50, 400->0, 1500->0, NaN->0 | RED | 2.2 |
| R3 | clientSpeed | reveal | revealDelayMs(true)=0, (false)=800 | RED | 2.2 |
| R4 | homeFloor | SSE fast | (loaderVisibility harness) response at t=100 -> navigate('Results', {result}) with no further advance; loader gone after | RED (base waits to 1200) | C1 |
| R5 | homeFloor | SSE mid | response at t=350 -> not navigated at t=399, navigated at t=400 | RED (base 1200) | C1 |
| R6 | homeFloor | URL fast | URL api.post resolves at ~0 -> navigated after the promise drain, no advance | RED | C1 |
| R7 | homeFloor | prefetch at arrival | response carrying two https image_url -> the assigned Image.prefetch recorder called with both BEFORE navigate (order recorder) | RED (no call) | C3 |
| P1 | homeFloor | slow | response at t=1500 -> navigates at once | green | - |
| P2 | homeFloor | error | onError unmounts the loader at once, no navigate | green | - |
| R8 | revealCut | fast hit | ResultsScreen with route.params.result, fake timers: after advanceTimersByTime(1) the Haptics.impactAsync mock is called once and the wall-time tracker mock has ready_celebration | RED (800) | C2 |
| P3 | revealCut | history keeps 800 | route.params.comparison_id (getComparison pending): haptic not called at 799, called at 800 | green | C2 |
| R9 | imagePrefetch | basic | two https URLs -> prefetch called once each; return value undefined synchronously | RED | 2.2 |
| R10 | imagePrefetch | filter | http:, data:, '', null, undefined, 42, 2049-char https -> zero calls | RED | 2.2 |
| R11 | imagePrefetch | bound | three products -> only the first two prefetched | RED | 2.2 |
| R12 | imagePrefetch | swallow | prefetch rejects -> no 'unhandledRejection' (process listener recorder) after flush; prefetch throws sync -> no throw | RED | 2.2 |
| R13 | imagePrefetch | absent | Image.prefetch deleted -> no throw, zero calls | RED (module null) | 2.2 |
| R14 | imagePrefetch | dedupe | same URL across two calls -> one call; 33 distinct then the first again -> called again (FIFO 32) | RED | 2.2 |
| R15 | imagePrefetch | wiring | HomeScreen navigateToResultsWithFloor body starts with `prefetchProductImages(result)`; ResultsScreen has `useEffect(() => { prefetchProductImages(result); }, [result])` | RED | C3 |
| R16 | swrCache | exports | SWR_FOCUS_THROTTLE_MS 30000 + the six functions | RED | 2.2 |
| R17 | swrCache | no user | write no-op; read undefined; shouldRefetchOnFocus true | RED | 2.2 |
| R18 | swrCache | throttle | user u-a, write at T: shouldRefetch false at T+29999, true at T+30000 | RED | 2.2 |
| R19 | swrCache | user change | u-a -> u-b clears; u-b -> u-b keeps; -> null clears | RED | 2.2 |
| R20 | swrCache | invalidate | invalidateSwrPrefix('history:') drops history:* only | RED | 2.2 |
| R21 | swrCache | leaf | source has zero `import ` / `require(` statements and no AsyncStorage | RED (file absent) | 2.2 |
| R22 | historySwr | throttled focus | user set, first load ok; focus at +10 s -> no getComparisonHistory call; focus at +31 s -> one call | RED | C4 |
| R23 | historySwr | warm remount | cache warm for history:'' -> a remount renders history-row ids before the (pending) fetch resolves | RED (spinner) | C4 |
| R24 | historySwr | delete invalidates | delete a row -> next focus within 30 s fetches | RED | C4 |
| P4 | historySwr | no user | no setSwrUser -> every focus fetches (A12 behaviour) | green | - |
| P5 | historySwr | refresh live | user set, within window: onRefresh, search submit, retry each fetch | green | - |
| P6 | historySwr | failure no stamp | user set, load rejects -> next focus fetches | green | - |
| R25 | sessionClear | one call | App.tsx has exactly one `setSwrUser(` and it is `useEffect(() => { setSwrUser(user?.id ?? null); }, [user?.id])` | RED | C4 |
| R26 | sessionClear | results invalidation | ResultsScreen has `invalidateSwrPrefix('history:')` inside a `[]` effect | RED | C4 |
| P7 | sessionClear | auth untouched | authService.ts contains no `swrCache` / `setSwrUser`; clearSession body still the epoch bump + three deletes | green | rule (c) |
| R27 | metroSentry | static | comment-stripped metro.config.js requires '@sentry/react-native/metro', calls getSentryExpoConfig(__dirname, { includeWebReplay: false }), no includeWebFeedback, exactly one `config.cacheVersion = qarenCacheVersion(` | RED | C5 |
| R28 | metroSentry | resolver | require('../metro.config.js').resolver.resolveRequest maps '@sentry-internal/replay' and '@sentry/replay' on ios and android to {type:'empty'}; 'react' goes to the recorder context.resolveRequest | RED (null at base) | C5 |
| R29 | metroSentry | frames | symbolicator.customizeFrame({file: 'node_modules/@sentry/core/cjs/debug.js'}) has collapse true | RED (stock: no collapse) | C5 |
| P8 | metroSentry | cache key | config.cacheVersion === qarenCacheVersion(APP_ROOT, '1.0') | green | - |
| R30 | lazyScreens | no static import | App.tsx has no static import of the seven modules (Legal, Paywall, Onboarding, NewOnboardingHost, ScanCamera, InviteeQuiz, ReferralLanding) and each binding is `lazyScreen(() => import('./src/screens/...'))` | RED | C6 |
| R31 | lazyScreens | helper | lazyScreen with a deferred loader renders a tree with no host text, then (after resolve, act) the loaded component with the same props | RED (null) | C6 |
| R32 | lazyScreens | failure | a rejecting loader reaches a test ErrorBoundary (recorder); the helper renders no Text | RED (null) | C6 |
| P9 | lazyScreens | entry | index.ts first import is './src/services/sentryBootstrap' | green | - |
| P10 | lazyScreens | eager set | the 13 eager screens remain static imports | green | - |
| R33 | bootParallel | overlap | (B5 extraction harness) getSavedLanguage returns a pending deferred: after a microtask flush getStableId HAS been called | RED (base calls it after bootstrapRtl) | C7 |
| P11 | bootParallel | order | recorder: changeLanguage('ar') < bootstrapRtl('ar') < setFlagStableId < initializeAuth; setIsLoading(false) once | green | C7 |
| P12 | bootParallel | rejection | getStableId rejects -> setIsLoading(false), initializeAuth not called, no 'unhandledRejection'; sync throw same | green | C7 |
| R34 | freezeOnBlur | tabs | the MainTabs Tab.Navigator screenOptions object contains `freezeOnBlur: true` | RED | C8 |
| P13 | freezeOnBlur | scope | no `enableFreeze(` in App.tsx / index.ts; the AuthStack and root Stack screenOptions are exactly `{ headerShown: false }` | green | C8 |
| P14 | scope | no flag | features.ts keeps `ENABLE_EXPO_FETCH_SSE_DEFAULT = false` and exports no new name (export list equals the base list, recorded as a literal) | green | rule (d) |
| P15 | scope | no package | package.json: @sentry/react-native "~7.2.0", no expo-image, no expo-atlas | green | rule (e) |
| P16 | scope | fonts | fonts.ts still requires Geist-Regular/SemiBold/Bold .ttf and calls useFonts | green | rule (b) |
| P17 | scope | no copy | each new module (when present) has no `t(`, no useTranslation, no `<Text`, no string literal rendered | green (vacuous at base) | 2.1 |
| P18 | scope | Home not throttled | HomeScreen has no `shouldRefetchOnFocus` / `swrRead`; the :167 getReferralStatus focus effect still runs on every focus | green | 2.4 |
Counts: RED 34 (R1-R34), PIN 18 (P1-P18). Behaviour rows use jest fake timers (modern, Date mocked); mocks of installed packages are non-virtual (`jest.mock(name, factory)`); the RED agent proves the cl2 files with --runInBand pairs in both orders (order-preserving sequencer) next to the HomeScreen / HistoryScreen / ResultsScreen suites.

Satisfiability prototype (RED agent, IN PLACE): byte copies of the five edited source files + the four E-row tests + the new leaves, apply 2.3, run the cl2 files and the 14 touched suites green, restore, sha256-compare against 1.2 (stop on mismatch), mutation lock file .qa-mutation.lock.

### 6. Mutation table (byte copies, one exact-string edit each, run the killing file, restore, sha256 compare)
| M | file | mutation | killed by |
|---|---|---|---|
| M1 | clientSpeed.ts | SKIP 300 -> 0 | R2, R4 |
| M2 | clientSpeed.ts | FLOOR 400 -> 1200 | R2, R5 |
| M3 | clientSpeed.ts | `>` -> `>=` at the skip boundary | R2 (300 -> 0) |
| M4 | clientSpeed.ts | revealDelayMs always 800 | R3, R8 |
| M5 | HomeScreen.tsx | remaining = Math.max(0, 1200 - elapsed) | R4, R5 |
| M6 | ResultsScreen.tsx | delay literal 800 restored | R8 |
| M7 | imagePrefetch.ts | drop the https check | R10 |
| M8 | imagePrefetch.ts | slice(0, 3) | R11 |
| M9 | imagePrefetch.ts | remove the .catch | R12 |
| M10 | imagePrefetch.ts | seen-set never consulted | R14 |
| M11 | HomeScreen.tsx | remove prefetchProductImages(result) | R7, R15 |
| M12 | swrCache.ts | setSwrUser never clears | R19 |
| M13 | swrCache.ts | `>=` -> `>` in the throttle | R18 |
| M14 | swrCache.ts | write ignores the no-user guard | R17 |
| M15 | HistoryScreen.tsx | focus effect ignores shouldRefetchOnFocus | R22 |
| M16 | HistoryScreen.tsx | delete branch without invalidateSwrPrefix | R24 |
| M17 | App.tsx | remove the setSwrUser effect | R25 |
| M18 | ResultsScreen.tsx | remove the history invalidation | R26 |
| M19 | metro.config.js | includeWebReplay: true | R27, R28 |
| M20 | App.tsx | LegalScreen back to a static import | R30 |
| M21 | lazyScreen.tsx | fallback `<Text>...</Text>` | R31, P17 |
| M22 | App.tsx | `const initialId = await getStableId();` restored after bootstrapRtl | R33 |
| M23 | App.tsx | drop `stableIdP.catch(...)` | P12 |
| M24 | App.tsx | freezeOnBlur removed | R34 |
Equivalent survivors are reported for a ruling.

### 7. Gates (cheapest first)
7.1 jest comm set (union rule): every suite under __tests__ naming App.tsx / '../App', HomeScreen, HistoryScreen, ResultsScreen, metro.config / metro.cacheVersion, w312BootSandbox, sessionEvents, or the new modules (swrCache, imagePrefetch, lazyScreen, clientSpeed): 125 suites at base (<scratchpad>/g6/jest_comm.txt) + the 12 cl2 files; by path, `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci <paths>` in chunks; plus every snapshot suite (no .snap in the diff). The fourteen backend-scanning client fences: no backend / docs / scripts literal moves, so they are not CL2's trigger; ResultsScreen.timeout and config/nativeBundle.w37 are members of the comm set anyway (w37 = the four accepted drift nodes).
7.2 `timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit`; eslint by path over `git diff --name-only --relative` inside SmartCompareApp (+ the new files).
7.3 Backend pins that read the touched files (union rule f), through pyt.py, bound 600 each (or one 1200 set): tests/test_legal_docs_u8_d3c.py (reads SmartCompareApp/App.tsx :957/:1028, `tabBarLabel: t('profile.title')` must stay), tests/test_events_allowlist_superset.py (rglob SmartCompareApp/src/*.ts*: no new event literal), tests/test_security_regression.py (rglob src for service-role strings :501-512; reads authService.ts), and the CLAUDE.md readers tests/test_ci_gates.py + tests/test_behavior_dimension_translation.py. Base: 210 passed (1.12). The other 20 SmartCompareApp-scanning backend tests (sca_scanners.txt, 25 files) read files CL2 does not touch.
7.4 Byte proxy (rule (e)): GREEN repeats the 1.10 export ONCE at head (same command, offline, 600 s) and reports the ios .hbc bytes before (6,594,787) / after and the replay-string counts; no bundle-size claim beyond that measured pair; the atlas stays NOT MEASURED (expo-atlas not installed).
7.5 The FULL jest suite ONCE in the last round (LC-7): 3,794 passed baseline + the 12 cl2 files' rows, only the four nativeBundle.w37 drift nodes red; one --runInBand full run; never jest -u.

### 8. CLAUDE.md row and owner steps
One block after the S81-G4 block's owner-steps bullet (CLAUDE.md:563), before the blank line at :564:
"**SESSION 81 client unit (S81-G6 CLIENT-PERF = CL2 CLIENT-SPEED, 2026-11-05; NO flag (client units are not flag-gated; the OTA is the gate); spec `.qa-s80/S81-G6_UNIT_SPEC.md`, the RED files `SmartCompareApp/__tests__/cl2/*.cl2.test.ts(x)`):** Home floor skips under 300 ms else 400 ms (`src/utils/clientSpeed.ts`; the camera 1.2 s and history 400 / 300 floors unchanged); the 800 ms winner reveal is 0 when Results opens with the result in its params; `prefetchProductImages` (`src/services/imagePrefetch.ts`, two https URLs, fire-and-forget); History SWR in memory per user (`src/services/swrCache.ts`, 30 s focus throttle, cleared by the one `setSwrUser` effect in App.tsx on sign-out / user change, invalidated by every Results mount and every delete; Home is NOT throttled: its focus refetch feeds the quota pill); `metro.config.js` = `getSentryExpoConfig(__dirname, { includeWebReplay: false })` + the P-B1 cache key; Legal / Paywall / Onboarding / ScanCamera / InviteeQuiz / ReferralLanding through `src/navigation/lazyScreen.tsx`; getStableId overlaps getSavedLanguage at boot; `freezeOnBlur` on the tabs. Ships ONLY in the OTA with the first KB-first canary, after the first review-safe OTA. Stated limits: no bundle-size claim beyond the measured export pair; the Geist drop is CL2b; SS1 / CL5 are G6b; the cache is lost on app restart."
- Owner steps (names only, a dated ledger line each): (1) the OTA slot "with the first KB-first canary", after the first review-safe OTA (UB-R4); (2) the MS1 atlas measurement before any speed claim; (3) the TestFlight / dev-client check of the first open of Legal and Paywall (no visible blank) before the OTA; (4) the TestFlight device check before CL2b's Geist drop; (5) the #118 check before G6b; (6) canary reads: cold start and comparison_wall_time from Sentry, the History refetch count per session.

### 9. Stated limits
- No on-device measurement in this unit: the lazy fallback duration, cold start, freezeOnBlur behaviour and the reveal feel are NOT MEASURED (jest renders no App; the owner's device check is step 3).
- No bundle-size claim beyond the 7.4 export pair; the atlas gate is NOT MEASURED (expo-atlas absent).
- The 30 s throttle is a constant; the cache is memory only (lost on restart); History can show a list up to 30 s old on a pure tab switch when nothing was viewed in Results and nothing deleted (a compare that failed after a server save is not invalidated).
- "Fast hit" = the result in the route params at Results mount = every Home text / URL compare (the brief's definition); haptic and RevealBurst now fire during the modal slide-in; wall-time tags ready_celebration / user_tappable shift earlier (the canary reads them).
- Home focus refetch unchanged (2.4); initializeAuth's two serial reads unchanged (auth, FOCUS).
- HomeScreen.minDisplayFloor.test.ts pins a replica, not the source (pre-existing).
- The Sentry Metro wrapper adds the debug-id plugin to every bundle (bundle bytes and the OTA hash change) and sets ___SENTRY_METRO_DEV_SERVER___ in the Metro process.
- No analytics event added; no i18n key added.

### 10. Out of scope
The Geist runtime-load drop (CL2b), expo-image (NT1), @sentry/react-native 8.x includeWebFeedback (NT1), SS1 / CL5 progressive paint and every SSE flag (G6b), Home SWR / the referral and usage refetches, any authService.ts / token / session change, LoadingScreenVariants' StreamingCards reveal (not on the Home path), the splash floor (A5), any package or native change.

### 11. Open questions (for the orchestrator's rulings)
- OQ1 LC-1 class: the lazy Legal / Paywall / Onboarding / ScanCamera screens are App-Review-visible screens whose CONTENT is unchanged but whose first open may show the null fallback for one commit (not measurable in jest). This spec classifies CL2 SAFE (no copy / flow / consent / paywall / legal / permission change) with owner step 3; the conservative alternative is to keep Legal and Paywall eager (drop two of the seven bindings).
- OQ2 sign-out line: rule (c) asks for ONE call in the existing sign-out path; this spec places it as one App.tsx effect keyed on user?.id (covers all five sign-out paths and every user change, touches no auth file). The alternative is one line in authService.clearSession() (:688-699), which covers the same paths but edits the auth file.
- OQ3 Home SWR: excluded (2.4). Confirm the cut, or rule a separate FOCUS unit.
- OQ4 Fast-hit definition: the brief's (result in params) vs a narrower one (Home elapsed under the skip band); this spec follows the brief.
- OQ5 E4 / E5 amend two behavioural rows of loaderVisibility; confirm they are E-rows rather than new RED rows replacing them.

Not done in this spec: no RED file, no source edit, no satisfiability prototype, no mutation run, no full jest run, no export at head.

## 12. The group

12.1 Combined comm set: the 125 jest suites + 12 cl2 files (7.1) + the 5 backend pins (7.3). CI-order set: the cl2 files, the four E-row suites, the 14 base-touched suites (1.12), then the rest of the 125, then the backend 5.
12.2 Footprint: 4 new source files, 5 edited source files (App.tsx, metro.config.js, HomeScreen.tsx, HistoryScreen.tsx, ResultsScreen.tsx), 4 edited test files (E1-E5), 12 new test files, CLAUDE.md. No package, native, backend, migration, i18n, .snap or docs-legal file.
12.3 Shared-file plan: one unit; GREEN applies 0.5's order in one pass; App.tsx receives four hunks (imports -> lazy bindings, the init block, the setSwrUser effect, the Tab screenOptions).
12.4 PR plan: ONE PR from feature/s81-g6-client-perf, body at most 25,600 bytes (measured with python): summary, counts (RED 34 / PIN 18 / mutants 24), the E-rows table, the stated limits, the [NATIVE READ] list (EMPTY), the export byte pair, the owner steps names-only, "ships only in the OTA with the first KB-first canary".
12.5 SAFE check, surface by surface: auth / tokens / sessions -- NOT touched (authService.ts untouched; App.tsx's auth wiring keeps its order; the new effect only reads user?.id into an in-memory cache); quota / billing / refunds -- NOT touched (Home's quota-pill refetch deliberately excluded, 2.4; useComparisonCounter untouched); legal or privacy text -- NOT touched (LegalScreen content unchanged, only lazily evaluated); consent path -- NOT touched (useAiConsentGate, aiConsent.ts untouched); security middleware -- none (client); migrations -- none; Redis / Lua -- none; App-Review-visible client surface -- no copy, flow, permission or paywall content change; presentation timing only (OQ1); secrets or key handling -- none (the Sentry Metro wrapper reads no credential; source-map upload is unchanged EAS behaviour). focus_surfaces_found: none, subject to OQ1.
