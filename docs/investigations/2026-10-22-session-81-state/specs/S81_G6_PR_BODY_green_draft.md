# S81-G6 CLIENT-PERF = CL2 CLIENT-SPEED (client unit, no runtime flag)

Base `ec747b496953869c0370e4f28bf025c6f694a97d` (origin/main) -> HEAD `ab4b3b3184f176568e97ad852b9cfdebea8ffd9c` on `feature/s81-g6-client-perf` (one commit).

A SAFE client unit under LC-9 (a group of one). React Native reads no per-call env flag and no `features.ts` constant is added, so **there is no flag: the OTA is the gate.** It merges to main now and **ships only in the OTA with the first KB-first canary, after the first review-safe OTA** (S81-08 + S81-11 + consent v3; UB-R4; the #377 precedent). Nothing reaches build 1.0.0 (3): no native, app.json, package or permission change. Same screens, same strings, same order of effects: only timing, caching and module evaluation move.

Spec `.qa-s80/S81-G6_UNIT_SPEC.md` (sha256 048029fd...b5d1), rulings `specs/RULINGS_S81_G6.md` (R-G6-1..R-G6-15), RED gate `specs/GATE_S81_G6.md` (GC-1..GC-11), RED report `specs/S81_G6_RED_REPORT.md`.

## The unit: changes -> RED rows -> flag -> OTA slot

| change | what | RED rows (`SmartCompareApp/__tests__/cl2/`) |
|---|---|---|
| C1 Home floor | `src/utils/clientSpeed.ts` (leaf): `homeFloorDelayMs` = the A17 rule, a response within 300 ms (inclusive) renders now, a slower one waits for 400 ms from the start; HomeScreen's `MIN_LOADING_MS = 1200` removed (camera 1.2 s and history 400 / 300 floors unchanged) | R1, R2 (clientSpeed); R4, R5, R6, P1, P2 (homeFloor) |
| C2 reveal cut | the 800 ms winner reveal is 0 ONLY on a measured fast hit: Home passes the additive route param `fastHit: true` when its own measured response was within 300 ms (GC-4); ResultsScreen reads `route.params.fastHit === true` via `revealDelayMs`; `RootStackParamList.Results.fastHit?: boolean` (GC-5); slow compares, history and camera keep 800 | R3; R4b x2 (homeFloor); R8, R8b, P3 (revealCut) |
| C3 image prefetch | `src/services/imagePrefetch.ts`: first two products' https `image_url` (at most 2048 chars), FIFO memory of 32, fire-and-forget with a catch, guarded when `Image.prefetch` is absent; called first in `navigateToResultsWithFloor` and in a Results `[result]` effect | R7 (homeFloor); R9-R15 (imagePrefetch) |
| C4 History SWR | `src/services/swrCache.ts` (leaf, memory only, per user, `SWR_FOCUS_THROTTLE_MS` 30000): History paints a warm list, refetches on focus only when stale / missing / no user, stamps only a success, invalidates on delete; every Results mount invalidates `history:*`; ONE App.tsx effect `setSwrUser(user?.id ?? null)` on `[user?.id]` (R-G6-2); `authService.ts` untouched; Home NOT cached (R-G6-3) | R16-R21 (swrCache); R22-R24, P4-P6 (historySwr); R25, R26, P7 (sessionClear); P18 (scope) |
| C5 metro | `getSentryExpoConfig(__dirname, { includeWebReplay: false })` from `@sentry/react-native/metro` + the P-B1 `qarenCacheVersion` composed on top (R-G6-6) | R27-R29, P8 (metroSentry) |
| C6 lazy screens | `src/navigation/lazyScreen.tsx` (React.lazy + Suspense; fallback = one View in `colors.bg.primary`, no text): Onboarding, NewOnboardingHost (explicit props type, GC-5), ScanCamera, InviteeQuiz, ReferralLanding; Legal and Paywall stay eager (R-G6-1 / GC-8: 15 eager); `index.ts` first import still `sentryBootstrap` | R30-R32, P9, P10 (lazyScreens); P17 (scope) |
| C7 boot | `getStableId` started before `await getSavedLanguage()` with a catch attached, awaited at its old place (R-G6-7); `initializeAuth` untouched | R33, P11, P12 (bootParallel) |
| C8 freeze | `freezeOnBlur: true` in the MainTabs `Tab.Navigator` screenOptions only (R-G6-8) | R34, P13 (freezeOnBlur) |
| scope | no flag, package, font or copy change | P14-P16 (scope) |

Flag: none. OTA slot: with the first KB-first canary, after the first review-safe OTA.

## Deliberate pin changes (E-rows, amended in place with the reason in a comment)

| E | file | base assertion | amended to | reason |
|---|---|---|---|---|
| E1 | `__tests__/metro.cacheVersion.pb1.test.ts:262` (the spec measured :254) | `require('expo/metro-config')` in the stripped config | `require('@sentry/react-native/metro')` + `getSentryExpoConfig(__dirname, { includeWebReplay: false })`; every cacheVersion assertion kept; the config's "ONLY deviation" comment now names the two deviations | C5 changes the provenance |
| E2 | `__tests__/HomeScreen.bundleB.contract.test.tsx:219-221` | `MIN_LOADING_MS = 1200` | HomeScreen imports `homeFloorDelayMs` from `../utils/clientSpeed` and sets `const remaining = homeFloorDelayMs(elapsed);`; clientSpeed declares 400 / 300 | C1 |
| E3 | `__tests__/HomeScreen.eS3hf.dedupe.test.tsx:91-94` | the same regex | `homeFloorDelayMs(elapsed)` in HomeScreen | C1 |
| E4 | `__tests__/HomeScreen.eS3hf.loaderVisibility.test.tsx` SSE row (:217-265) | response at 100 ms, navigate after +1200 | response at 350 ms; loader mounted and no navigate at +49; navigate and loader gone at t=400 | C1 (A17 300 / 400; the under-300 band is R4) |
| E5 | same file, URL row (:267-306) | URL post resolves at ~0, navigate after +1200 | post released at t=350 by a deferred; loader mounted, no navigate; +50 navigates | C1 |
| E6 | `__tests__/ResultsEntryParams.a18.test.ts:153` | declared Results params `[comparison_id, result, vision_products]` | + `fastHit` | R-G6-4 / GC-2 |
| E7 | `__tests__/HomeScreen.minDisplayFloor.test.ts:157-164` | exactly one `navigate('Results' as any, { result })` | the regex also accepts `fastHit ? { result, fastHit: true } : { result }` (still exactly one) | R-G6-4 / GC-2 |

No other existing assertion moved.

## Counts

- RED: 12 frozen files, **57 nodes** (37 RED at base, every first failure an `expect()` AssertionError; 20 PIN green at base) -> **57 / 57 green at HEAD**; the 12 files' sha256 re-hashed before and after: unchanged.
- Mutation table (RED, on the prototype bytes): **25 mutants, 24 KILLED by assertions, M14 EQUIVALENT by ruling (GC-3)**; the table is section 4 of `specs/S81_G6_RED_REPORT.md`; the adversary re-applies at least ten on these bytes.
- Touched set: the 12 cl2 files + 16 touched suites (the 14 base-touched incl. E1-E5, plus E6 / E7): 28 suites, 212 passed, 5 todo. In-band pairs in both orders (order-preserving sequencer) over the App.tsx readers (App.* x11, bootRegressionPins / bootSentryAlarm / bootSentryOrder, paywall.noSubscriptionUi.s69, six cl2 files): 21 suites, 115 / 115 each way; one in-band run of the touched set: 28 suites, 212 passed.
- tsc 5.9.3 rc 0; eslint 9.39.4 over the 28 changed / new / cl2 files: 0 errors (per-file warning counts equal to base).
- Comm set at HEAD: 158 jest files (the RED's 137 + App.routing + types.contract + 19 src-walking suites, unioned) in 7 chunks: 1642 passed; failed = exactly the four `config/nativeBundle.w37` drift nodes = the base failed set; `comm -13` EMPTY, `comm -23` EMPTY. Backend pins (5 files): `[pyt] tag=g6green-be-pins-2 elapsed=15s bound=600s status=OK rc=0` -> 210 passed (base 210 passed).

## Export byte pair (a MEASUREMENT, never a gate; R-G6-6)

Offline `node node_modules/expo/bin/cli export --platform ios` (EXPO_OFFLINE=1): base 6,594,787 B / 2211 modules (replay strings: rrweb 3, ReplayContainer 1) -> HEAD **6,355,018 B / 2214 modules** (rrweb 0, ReplayContainer 0), -239,769 B. No bundle-size claim beyond this pair (the MS1 atlas is the real instrument).

## Stated limits (GC-11, spec section 9)

- GC-11 / 9.1: no on-device measurement: the lazy fallback duration, cold start, freezeOnBlur and the reveal feel are NOT MEASURED (jest renders no App; owner step 3).
- GC-11 / 9.2: no bundle-size claim beyond the export pair above; the atlas is NOT MEASURED (expo-atlas absent).
- GC-11 / 9.3: the 30 s throttle is a constant and the cache is memory only (lost on restart); History can show a list up to 30 s old on a pure tab switch with no Results view and no delete in between (a compare that failed after a server save is not invalidated).
- 9.4 (as amended by R-G6-4): fast hit = the Home response within 300 ms; only then do the haptic, RevealBurst and the wall-time tags `ready_celebration` / `user_tappable` move earlier (the canary reads them).
- GC-11 / 9.5: the Home focus refetch is unchanged (the quota pill); `initializeAuth`'s serial reads are unchanged.
- 9.6: `HomeScreen.minDisplayFloor.test.ts` pins a local replica of the floor, not the source (pre-existing; E7 only widens its source-wiring regex).
- GC-11 / 9.7: the Sentry Metro wrapper adds the debug-id plugin, so every bundle's bytes and the OTA hash change; it also sets `___SENTRY_METRO_DEV_SERVER___` in the Metro process.
- GC-11: the installed expo 54.0.34 vs the pinned ~54.0.37 drift (owner step 1 runs `npm ls` / `npm ci` first).
- 9.8: no analytics event, no i18n key, no rendered string added.

## [NATIVE READ]

EMPTY (no Arabic or English string added or changed).

## Owner steps (names only; a dated ledger line each)

1. The OTA: with the first KB-first canary, after the first review-safe OTA; `npm ls` / `npm ci` in `SmartCompareApp/` before `eas update`.
2. The MS1 atlas measurement before any speed claim.
3. The device check (TestFlight / dev client) of the first open of the five lazy screens (Onboarding, NewOnboardingHost, ScanCamera, InviteeQuiz, ReferralLanding): no visible blank.
4. The TestFlight device check before CL2b (the Geist runtime-load drop).
5. The #118 cert-pinning device check before G6b (SS1 + CL5).
6. Canary reads: cold start and comparison wall time from Sentry, the History refetch count per session.

Separate files (filed by the orchestrator): the gate logs `GATE_LOGS_S81_G6_GREEN.txt`, the sha table `GREEN_SHA_TABLE.tsv`, the GREEN report `S81-G6_GREEN_REPORT.md`, the mutation table in `specs/S81_G6_RED_REPORT.md`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
