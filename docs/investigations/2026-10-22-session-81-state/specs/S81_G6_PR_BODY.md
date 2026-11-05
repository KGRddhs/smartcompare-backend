# S81-G6 CLIENT-PERF = CL2 CLIENT-SPEED (client unit, no runtime flag)

Base `ec747b496953869c0370e4f28bf025c6f694a97d` (origin/main, fetched 2026-11-05 ~05:32 AST, after the round commit; `git rebase origin/main` = up to date, nothing replayed) -> HEAD `a93b0153b3fc13651f420f94aa15256ffeb66785` on `feature/s81-g6-client-perf` (two commits: GREEN `ab4b3b31` + the final-round commit: the GREEN-owned gate-rows file and the CLAUDE.md stated-limit ids, RULINGS_REBASE_S81_G6 RB-G6-8).

A SAFE client unit under LC-9 (a group of one). React Native reads no per-call env flag and no `features.ts` constant is added, so **there is no flag: the OTA is the gate.** It merges to main now and **ships only in the OTA with the first KB-first canary, after the first review-safe OTA** (S81-08 + S81-11 + consent v3; UB-R4; the #377 precedent). Nothing reaches build 1.0.0 (3): no native, app.json, package or permission change. Same screens, same strings, same order of effects: only timing, caching and module evaluation move.

Spec `.qa-s80/S81-G6_UNIT_SPEC.md` (sha256 048029fd...b5d1), rulings `specs/RULINGS_S81_G6.md` (R-G6-1..R-G6-15), RED gate `specs/GATE_S81_G6.md` (GC-1..GC-11), RED report `specs/S81_G6_RED_REPORT.md`, GREEN report `specs/S81_G6_GREEN_REPORT.md`, adversary report `specs/S81_G6_ADV1_correctness.md`, final-round rulings `specs/RULINGS_REBASE_S81_G6.md` (RB-G6-1..RB-G6-11) and the final-round report `REBASE_REPORT.md`.

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
| gate row | the Home-level INCLUSIVE fast-hit boundary (GC-4): a response at exactly t = 300 ms navigates at once with `fastHit: true`, one at t = 301 ms waits for the 400 ms floor with no fastHit (RB-G6-2) | G6-GR1 (`gateRows.cl2.test.tsx`, GREEN-owned) |

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

## Counts (measured in the final round at HEAD `a93b0153`)

- RED: 12 frozen files (sha256 re-hashed against GC-1 from `git show HEAD:<path>` and on disk, before and after the round commit: unchanged) + the GREEN-owned `gateRows.cl2.test.tsx` (sha256 `ff3f0716cf025bf262572014eb4e8124d994447a0cc966e5aba2a88ddc088165`): **58 / 58 green** (57 RED-file nodes: 37 RED at base, 20 PIN; + G6-GR1).
- Mutation: the RED table **25 spec mutants, 24 KILLED, M14 EQUIVALENT by ruling (GC-3)** (section 4 of `specs/S81_G6_RED_REPORT.md`); the adversary re-applied 24 of them on the GREEN bytes (all KILLED) and **38 in all**: the own mutant **O1** (`<=` to `<` at the Home fast-hit gate) survived there and is now **KILLED by G6-GR1** (an `expect(...).toBe(true)` failure on a sha-verified byte copy of `HomeScreen.tsx` under `.qa-mutation.lock`, restored and sha256-equal); **O5 / O7 / O11 EQUIVALENT by ruling (RB-G6-3)** with M14.
- Touched set: the 13 cl2 files + 16 touched suites (the 14 base-touched incl. E1-E5, plus E6 / E7): 29 suites, 213 passed, 5 todo. In-band pairs in both orders (the RED's order-preserving sequencer) over the 21 App.tsx readers: 115 / 115 each way; one in-band run of the touched set: 29 suites, 213 passed.
- tsc 5.9.3 rc 0; eslint 9.39.4 over the 29 files of `git diff --name-only --relative origin/main`: 0 errors (108 warnings = GREEN's 99 + 9 pre-existing-class warnings in the new test file: `no-require-imports` x8 in the jest.mock factories, `import/first` x1, the loaderVisibility pattern).
- Comm set at HEAD (RB-G6-1): **159 jest suites** (GREEN's 158: the RED's 137 + App.routing + types.contract + 19 src-walking suites; + `src/components/__tests__/TwoInputShell.test.tsx`, which reads HomeScreen.tsx by path) in 7 batches of at most 25: 1698 passed, 13 todo; failed = exactly the four `config/nativeBundle.w37` drift nodes = the base failed set (reused from the RED / GREEN measurements; no base scratch worktree for a client unit); `comm -13` EMPTY, `comm -23` EMPTY. Backend pins (5 files: test_legal_docs_u8_d3c, test_events_allowlist_superset, test_security_regression and the two CLAUDE.md readers test_ci_gates, test_behavior_dimension_translation): `[pyt] tag=g6final-be-pins elapsed=39s bound=600s status=OK rc=0` -> 210 passed (base 210 passed).
- Full jest suite once (LC-7, the arbiter): `timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci` from `SmartCompareApp/` (start 05:40:31, end 05:40:55): Test Suites 1 failed, 3 skipped, 398 passed, 399 of 402; Tests **3852 passed** (= the base 3,794 + the 57 RED-file nodes + G6-GR1), 4 failed = exactly the four `config/nativeBundle.w37` drift nodes (d5, k2, k4, k5), 13 skipped, 13 todo, 3882 total; Snapshots 42 passed, 42 total (0 added / updated / unmatched; no `.snap` in the diff); Time 21.6 s.

## Export byte pair (a MEASUREMENT, never a gate; R-G6-6)

Offline `node node_modules/expo/bin/cli export --platform ios` (EXPO_OFFLINE=1): base 6,594,787 B / 2211 modules (replay strings: rrweb 3, ReplayContainer 1) -> HEAD **6,355,018 B / 2214 modules** (rrweb 0, ReplayContainer 0), -239,769 B. No bundle-size claim beyond this pair (the MS1 atlas is the real instrument).

## Stated limits (GC-11, spec section 9; the adversary minors as limits, LC-4)

- CL2-L1: no on-device measurement: the lazy fallback duration, cold start, freezeOnBlur and the reveal feel are NOT MEASURED (jest renders no App; owner step 3).
- CL2-L2: no bundle-size claim beyond the export pair above (the atlas is NOT MEASURED; expo-atlas absent; the hbc sha is not cited, RB-G6-6).
- CL2-L3: the 30 s throttle is a constant and the cache is memory only (lost on restart); History can show a list up to 30 s old on a pure tab switch with no Results view and no delete in between (a compare that failed after a server save is not invalidated).
- CL2-L4 (m4, RB-G6-4): a History fetch still in flight when Results mounts can stamp a list older than a just-saved comparison after the Results invalidation ran, so a History focus within 30 s may omit the new row until pull-to-refresh or the next throttle window (self-healing; a generation counter is CL2c material if the canary shows it).
- CL2-L5 (m5, RB-G6-5): three HomeScreen.tsx comments (:195, :224, :1210) still describe the removed 1.2 s floor; comments only, fixed by the next client unit that touches HomeScreen (G6b / CL5).
- CL2-L6 (RB-G6-7): the warm History snapshot is read once per mount (a useState initializer), so an already-mounted History tab repaints only from its own fetch; the Results reveal decision is read once at mount.
- Also stated: fast hit = the Home response within 300 ms; only then do the haptic, RevealBurst and the wall-time tags `ready_celebration` / `user_tappable` move earlier. The Home focus refetch (the quota pill) and `initializeAuth`'s serial reads are unchanged. `HomeScreen.minDisplayFloor.test.ts` pins a local replica of the floor (pre-existing; E7 only widens its regex). The Sentry Metro wrapper adds the debug-id plugin, so every bundle's bytes and the OTA hash change (and it sets `___SENTRY_METRO_DEV_SERVER___` in the Metro process). The installed expo 54.0.34 vs the pinned ~54.0.37 drift (owner step 1). No analytics event, no i18n key, no rendered string added.

## Adversary (correctness, ONE, LC-1; `specs/S81_G6_ADV1_correctness.md`)

SOUND on the exact GREEN bytes: 0 blocking, 0 major, six minors: m1 the comm-set gap (TwoInputShell, measured green; now in the 159, RB-G6-1); m2 the Home 300 ms edge test gap (O1; closed by G6-GR1, RB-G6-2); m3 O5 / O7 / O11 equivalent (RB-G6-3); m4 the SWR write race (CL2-L4); m5 the stale comments (CL2-L5); m6 the export hbc sha not reproducible (the byte pair stands, RB-G6-6).

## [NATIVE READ]

EMPTY (no Arabic or English string added or changed).

## Owner steps (names only; a dated ledger line each)

1. The OTA: with the first KB-first canary, after the first review-safe OTA; `npm ls` / `npm ci` in `SmartCompareApp/` before `eas update`.
2. The MS1 atlas measurement before any speed claim.
3. The device check (TestFlight / dev client) of the first open of the five lazy screens (Onboarding, NewOnboardingHost, ScanCamera, InviteeQuiz, ReferralLanding): no visible blank.
4. The TestFlight device check before CL2b (the Geist runtime-load drop).
5. The #118 cert-pinning device check before G6b (SS1 + CL5).
6. Canary reads: cold start and comparison wall time from Sentry, the History refetch count per session.

Separate files (filed by the orchestrator): the gate logs `GATE_LOGS_S81_G6_GREEN.txt`, the sha table `S81_G6_GREEN_SHA_TABLE.tsv`, the GREEN report, the adversary report, the final-round `REBASE_REPORT.md`, the mutation table in `specs/S81_G6_RED_REPORT.md`.
