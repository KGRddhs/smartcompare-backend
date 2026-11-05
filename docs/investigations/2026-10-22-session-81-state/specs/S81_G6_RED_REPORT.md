# S81-G6 RED REPORT (CL2 CLIENT-SPEED) -- RED agent, Opus 5.5, 2026-11-05 03:33-04:10 AST

Base ec747b496953869c0370e4f28bf025c6f694a97d (worktree sc-s81-g6, verified by rev-parse). Spec sha256 048029fd...b5d1 verified. Rulings RULINGS_S81_G6 R-G6-1..15 applied.
Toolchain (by path through the junction; node_modules/@babel/core 7.29.0 and node_modules/.bin/jest present): jest 29.7.0, typescript 5.9.3, eslint 9.39.4, react-native 0.81.5.
Client exceptions honoured: prototype + mutation table IN PLACE under sc-s81-g6/.qa-mutation.lock on shutil byte copies (bytes/ and mut_bytes/), restored + sha256-compared after each run; NO scratch worktree created; no npm/npx; no git write; no .env read.

## 1. RED files (12, pure ASCII, LF, 0 bytes > 127, 0 CRLF)
| file | bytes | sha256 |
|---|---|---|
| SmartCompareApp/__tests__/cl2/bootParallel.cl2.test.ts | 8051 | 2762a2dc47cafdd9c036398c39e44b79ca9ce7998528df4a9c1991dd21aa89a8 |
| SmartCompareApp/__tests__/cl2/clientSpeed.cl2.test.ts | 1611 | b211d9a484c9aec67aa4318d02ca9e397efe41edbd48c88fba87cf4d035ed2ea |
| SmartCompareApp/__tests__/cl2/freezeOnBlur.cl2.test.ts | 1769 | c03900e7a3173ad6d1a0275a118bcb180d9d0a05b3beb0857036daeeee8de0ed |
| SmartCompareApp/__tests__/cl2/historySwr.cl2.test.tsx | 9655 | c613f37c932278df82f6debb9e1887fb3ff5983ae621e4e96eee488be413916c |
| SmartCompareApp/__tests__/cl2/homeFloor.cl2.test.tsx | 11702 | d963fa5d59b06e44417cad6c770b47509d673e87994241c2b450574bbd8b5de0 |
| SmartCompareApp/__tests__/cl2/imagePrefetch.cl2.test.ts | 6928 | 4ead2f471e481a025d7333a7f2c28bc0d0215918615b8a9d55ca67d92fc4605b |
| SmartCompareApp/__tests__/cl2/lazyScreens.cl2.test.tsx | 6748 | 1bd2ee55f3a28d69927e75fa38425ea4b983e501466b47a381af477e45ae8542 |
| SmartCompareApp/__tests__/cl2/metroSentry.cl2.test.ts | 4213 | 6477aea2e54a244af5baf0f36f501694c09e5759608ed69560312955aef2bef4 |
| SmartCompareApp/__tests__/cl2/revealCut.cl2.test.tsx | 5427 | 3784131a7f14469c8b0337995fac4d7b5237029c664f730db4c73412d23c99f7 |
| SmartCompareApp/__tests__/cl2/scope.cl2.test.ts | 3806 | af416eb9d5a7556f59f0f98eb455f6bc86a5ab6f7acefd3516af6f7685ddba18 |
| SmartCompareApp/__tests__/cl2/sessionClear.cl2.test.ts | 2537 | c75694ff6734a57ffaf6be410ab6db23515e40d1c4aa382d97cfff23872d6c7f |
| SmartCompareApp/__tests__/cl2/swrCache.cl2.test.ts | 3784 | ef05d1021ef3e0df03ea35de7f9f9e9de3f742ecf93871612b94d64c42780e03 |

## 2. Rows and base result (final bytes)
Base run: [jest] tag=g6red-comm-chunk_base_00 files=25 start=04:05:42 end=04:06:31 rc=0 ; [jest] tag=g6red-comm-chunk_base_01 files=25 start=04:06:34 end=04:06:48 rc=0 ; [jest] tag=g6red-comm-chunk_base_02 files=25 start=04:06:49 end=04:07:04 rc=0 ; [jest] tag=g6red-comm-chunk_base_03 files=25 start=04:07:06 end=04:07:25 rc=1 ; [jest] tag=g6red-comm-chunk_base_04 files=23 start=04:07:26 end=04:07:40 rc=1 ; DONE
cl2 at base: 57 nodes = 37 FAILED (every RED row, each an AssertionError: base_red_assertions.tsv, 37/37 ASSERT, 0 non-assert) + 20 passed (every PIN row + R4b-mid + R8b).
Per file (failed / passed at base): bootParallel 1/2, clientSpeed 3/0, freezeOnBlur 1/1, historySwr 3/3, homeFloor 5/3, imagePrefetch 9/0, lazyScreens 3/2, metroSentry 3/1, revealCut 1/2, scope 0/5, sessionClear 2/1, swrCache 6/0.
RED rows -> nodes: R1-R3 (clientSpeed), R4, R4b-fast, R5, R6, R7 (homeFloor), R8 (revealCut), R9 x2, R10, R11, R12 x2, R13, R14, R15 (imagePrefetch), R16-R21 (swrCache), R22-R24 (historySwr), R25-R26 (sessionClear), R27-R29 (metroSentry), R30-R32 (lazyScreens), R33 (bootParallel), R34 (freezeOnBlur) = 37 nodes.
Green at base (PIN-type): P1, P2, R4b-mid (homeFloor); R8b, P3 (revealCut); P4-P6 (historySwr); P7 (sessionClear); P8 (metroSentry); P9, P10 (lazyScreens); P11, P12 (bootParallel); P13 (freezeOnBlur); P14-P18 (scope).

### Assertion proof per RED node (first failure line at base)
```
sessionClear.cl2.test.ts	R25 App.tsx has exactly one setSwrUser call, in the user?.id	ASSERT	Error: expect(received).toBe(expected) // Object.is equality
sessionClear.cl2.test.ts	R26 ResultsScreen invalidates history:* inside a mount ([]) 	ASSERT	Error: expect(received).toMatch(expected)
bootParallel.cl2.test.ts	R33 getStableId is called while getSavedLanguage is still pe	ASSERT	Error: expect(jest.fn()).toHaveBeenCalledTimes(expected)
freezeOnBlur.cl2.test.ts	R34 the MainTabs Tab.Navigator screenOptions carry freezeOnB	ASSERT	Error: expect(received).toMatch(expected)
clientSpeed.cl2.test.ts	R1 exports the three constants and the two functions	ASSERT	Error: expect(received).not.toBeNull()
clientSpeed.cl2.test.ts	R2 homeFloorDelayMs follows the A17 300 / 400 rule	ASSERT	Error: expect(received).not.toBeNull()
clientSpeed.cl2.test.ts	R3 revealDelayMs is 0 on a measured fast hit and 800 otherwi	ASSERT	Error: expect(received).not.toBeNull()
swrCache.cl2.test.ts	R16 exports SWR_FOCUS_THROTTLE_MS = 30000 and the six functi	ASSERT	Error: expect(received).not.toBeNull()
swrCache.cl2.test.ts	R17 no user: write is a no-op, read is undefined, focus alwa	ASSERT	Error: expect(received).not.toBeNull()
swrCache.cl2.test.ts	R18 throttle: false at T+29999, true at T+30000	ASSERT	Error: expect(received).not.toBeNull()
swrCache.cl2.test.ts	R19 user change: u-a -> u-b clears; u-b -> u-b keeps; -> nul	ASSERT	Error: expect(received).not.toBeNull()
swrCache.cl2.test.ts	R20 invalidateSwrPrefix drops history:* only	ASSERT	Error: expect(received).not.toBeNull()
swrCache.cl2.test.ts	R21 the leaf has no import, no require and no AsyncStorage	ASSERT	Error: expect(received).toBe(expected) // Object.is equality
imagePrefetch.cl2.test.ts	R9 two https URLs -> one prefetch each; returns undefined sy	ASSERT	Error: expect(received).not.toBeNull()
imagePrefetch.cl2.test.ts	R9 also reads the legacy top-level products array	ASSERT	Error: expect(received).not.toBeNull()
imagePrefetch.cl2.test.ts	R10 non-https, empty, non-string and over-long URLs are neve	ASSERT	Error: expect(received).not.toBeNull()
imagePrefetch.cl2.test.ts	R11 three products -> only the first two are prefetched	ASSERT	Error: expect(received).not.toBeNull()
imagePrefetch.cl2.test.ts	R12 a rejecting prefetch gets a catch handler attached	ASSERT	Error: expect(received).not.toBeNull()
imagePrefetch.cl2.test.ts	R12 a rejecting prefetch raises no unhandledRejection; a thr	ASSERT	Error: expect(received).not.toBeNull()
imagePrefetch.cl2.test.ts	R13 an absent Image.prefetch (the jest mock shape) is a sile	ASSERT	Error: expect(received).not.toBeNull()
imagePrefetch.cl2.test.ts	R14 the same URL across two calls is prefetched once; FIFO 3	ASSERT	Error: expect(received).not.toBeNull()
imagePrefetch.cl2.test.ts	R15 wiring: Home floor starts with the prefetch; Results pre	ASSERT	Error: expect(received).toMatch(expected)
lazyScreens.cl2.test.tsx	R30 the five lazy screens: no static import, each bound thro	ASSERT	Error: expect(received).toMatch(expected)
lazyScreens.cl2.test.tsx	R31 the helper renders a host-text-free background View, the	ASSERT	Error: expect(received).not.toBeNull()
lazyScreens.cl2.test.tsx	R32 a rejecting loader reaches an error boundary; the helper	ASSERT	Error: expect(received).not.toBeNull()
homeFloor.cl2.test.tsx	R4 SSE fast hit (t=100) navigates with no further advance an	ASSERT	Error: expect(jest.fn()).toHaveBeenCalledWith(...expected)
homeFloor.cl2.test.tsx	R4b the fast path (t=100) passes fastHit: true	ASSERT	Error: expect(jest.fn()).toHaveBeenCalledTimes(expected)
homeFloor.cl2.test.tsx	R5 SSE mid hit (t=350) is held to the 400 ms floor: not at 3	ASSERT	Error: expect(jest.fn()).toHaveBeenCalledWith(...expected)
homeFloor.cl2.test.tsx	R6 URL fast hit (~0 ms) navigates after the promise drain wi	ASSERT	Error: expect(jest.fn()).toHaveBeenCalledWith(...expected)
homeFloor.cl2.test.tsx	R7 the two https product images are prefetched BEFORE naviga	ASSERT	Error: expect(received).toEqual(expected) // deep equality
revealCut.cl2.test.tsx	R8 a measured fast hit (result + fastHit: true) reveals afte	ASSERT	Error: expect(jest.fn()).toHaveBeenCalledTimes(expected)
historySwr.cl2.test.tsx	R22 user set: a focus at +10 s does not refetch; a focus at 	ASSERT	Error: expect(received).not.toBeNull()
historySwr.cl2.test.tsx	R23 warm cache: a remount paints the cached rows before the 	ASSERT	Error: expect(received).not.toBeNull()
historySwr.cl2.test.tsx	R24 a delete invalidates: the next focus inside 30 s fetches	ASSERT	Error: expect(received).not.toBeNull()
metroSentry.cl2.test.ts	R27 static: the Sentry wrapper with includeWebReplay false, 	ASSERT	Error: expect(received).toContain(expected) // indexOf
metroSentry.cl2.test.ts	R28 resolver: the replay packages resolve empty on ios and a	ASSERT	Error: expect(received).toBe(expected) // Object.is equality
metroSentry.cl2.test.ts	R29 the Sentry frame collapse is installed	ASSERT	Error: expect(received).toContain(expected) // indexOf
```

## 3. Prototype (in place; thrown away, restored byte-for-byte)
Files: NEW src/utils/clientSpeed.ts, src/services/swrCache.ts, src/services/imagePrefetch.ts, src/navigation/lazyScreen.tsx; EDIT App.tsx, metro.config.js, src/screens/HomeScreen.tsx, ResultsScreen.tsx, HistoryScreen.tsx, src/types/types.ts (fastHit?: boolean, R-G6-4); E1-E5 as spec 4.1; PLUS two E-rows the spec missed (E6, E7, section 6).
Diff: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/bd48b535-2d58-47fc-9bbe-cf719f400b7b/scratchpad/S81-G6_red/prototype.diff ; copies: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/bd48b535-2d58-47fc-9bbe-cf719f400b7b/scratchpad/S81-G6_red/prototype_files/
[jest] tag=g6red-proto-cl2-t14-b start=03:49:57 end=03:50:16 rc=0 -> 26 suites (12 cl2 + 14 base-touched incl. E1-E5) 194 passed, 5 todo, 0 failed.
[jest] tag=g6red-proto-boot-2 start=03:58:46 end=03:58:55 rc=0 -> bootParallel 3 passed (final bytes).
In-band pairs, order-preserving sequencer (orderSequencer.js), 12 cl2 + loaderVisibility + searchState.a12 + historyFloor.a17 + gateB + mobileJank.m21:
  [jest] tag=g6red-proto-inband-A start=03:59:30 end=03:59:38 rc=0 -> 17 suites 81 passed
  [jest] tag=g6red-proto-inband-B start=03:59:40 end=03:59:49 rc=0 -> 17 suites 81 passed
tsc (prototype in place): [tsc] tag=g6red-proto-tsc start=03:47:40 rc=2 (2 errors: my test makeProps type + the prototype NewOnboardingHost lazy binding) ; [tsc] tag=g6red-proto-tsc-2 start=03:48:07 rc=2 (binding still) ; [tsc] tag=g6red-proto-tsc-3 start=03:48:35 end=03:48:42 rc=0 after `lazyScreen<NewOnboardingHostProps>(...)` with an explicit props type.
eslint by path (git diff --name-only --relative + 4 new + 12 cl2): [eslint] tag=g6red-proto-eslint rc=1 (1 error in my metroSentry test: expo/no-dynamic-env-var) ; [eslint] tag=g6red-proto-eslint-2 start=03:49:32 end=03:49:45 rc=0 -> 0 errors, 100 warnings (pre-existing classes; metro.config.js is eslint-ignored).
Backend pins on the prototype: [pyt] tag=g6red-be-pins-proto start=2026-11-05 04:04:39 end=2026-11-05 04:04:55 elapsed=16s bound=600s status=OK rc=0 (stdout; log be_pins_proto.log)
  -> 210 passed, 13 warnings ([hermeticity] sentinel checked 210; 7 [netguard] sentinel/egress-neutralised lines, no real egress). Base (reused, spec 1.12): [pyt] tag=g6spec-be-pins start=2026-11-05 03:10:52 end=2026-11-05 03:11:06 elapsed=14s bound=1200s status=OK rc=0 -> 210 passed.

## 4. Mutation table (on the prototype bytes, in place, restore + sha256 after each; all restores matched)
| M | mutation | [jest] | killed by |
|---|---|---|---|
| M1 | SKIP 300 -> 0 | tag=g6red-M1 start=03:51:54 end=03:52:06 rc=1 | clientSpeed:R1, clientSpeed:R2, homeFloor:R4, homeFloor:R4b |
| M2 | FLOOR 400 -> 1200 | tag=g6red-M2 start=03:52:06 end=03:52:18 rc=1 | clientSpeed:R1, clientSpeed:R2, homeFloor:R5 |
| M3 | > -> >= at the skip boundary | tag=g6red-M3 start=03:52:18 end=03:52:24 rc=1 | clientSpeed:R2 |
| M4 | revealDelayMs always 800 | tag=g6red-M4 start=03:52:24 end=03:52:38 rc=1 | clientSpeed:R3, revealCut:R8 |
| M5 | Home remaining = Math.max(0, 1200 - elapsed) | tag=g6red-M5 start=03:52:38 end=03:52:45 rc=1 | homeFloor:R4, homeFloor:R4b, homeFloor:R5, homeFloor:R6 |
| M6 | Results delay literal 800 restored | tag=g6red-M6 start=03:52:45 end=03:52:52 rc=1 | revealCut:R8 |
| M7 | imagePrefetch drop the https check | tag=g6red-M7 start=03:52:52 end=03:53:00 rc=1 | imagePrefetch:R10 |
| M8 | imagePrefetch slice(0, 3) | tag=g6red-M8 start=03:53:00 end=03:53:06 rc=1 | imagePrefetch:R11 |
| M9 | imagePrefetch remove the .catch | tag=g6red-M9 start=03:53:06 end=03:53:15 rc=1 | imagePrefetch:R12 (R12-thenable by assertion; the R12 rejection node fails by jest-circus unhandled-rejection error, not assertion) |
| M10 | imagePrefetch seen-set never consulted | tag=g6red-M10 start=03:53:15 end=03:53:22 rc=1 | imagePrefetch:R14 |
| M11 | Home remove prefetchProductImages(result) | tag=g6red-M11 start=03:53:22 end=03:53:29 rc=1 | homeFloor:R7, imagePrefetch:R15 |
| M12 | setSwrUser never clears | tag=g6red-M12 start=03:53:29 end=03:53:38 rc=1 | swrCache:R19 |
| M13 | throttle >= -> > | tag=g6red-M13 start=03:53:38 end=03:53:44 rc=1 | swrCache:R18 |
| M14 | swrWrite ignores the no-user guard | tag=g6red-M14 start=03:53:53 end=03:54:06 rc=0 | SURVIVED (EQUIVALENT by construction: swrRead returns undefined with no user and setSwrUser clears on every change, so a no-user write is unobservable; ruling requested) |
| M15 | History focus ignores shouldRefetchOnFocus | tag=g6red-M15 start=03:54:06 end=03:54:13 rc=1 | historySwr:R22 |
| M16 | History delete without invalidateSwrPrefix | tag=g6red-M16 start=03:54:13 end=03:54:20 rc=1 | historySwr:R24 |
| M17 | App remove the setSwrUser effect | tag=g6red-M17 start=03:54:20 end=03:54:26 rc=1 | sessionClear:R25 |
| M18 | Results remove the history invalidation | tag=g6red-M18 start=03:54:26 end=03:54:33 rc=1 | sessionClear:R26 |
| M19 | metro includeWebReplay: true | tag=g6red-M19 start=03:54:33 end=03:54:41 rc=1 | metroSentry:R27, metroSentry:R28 |
| M20 | ScanCamera back to a static import | tag=g6red-M20 start=03:54:41 end=03:54:48 rc=1 | lazyScreens:R30 (R-G6-1: ScanCamera back to static) |
| M21 | lazyScreen fallback <Text>...</Text> | tag=g6red-M21 start=03:54:48 end=03:55:00 rc=1 | lazyScreens:R31, scope:P17 |
| M22 | getStableId awaited after bootstrapRtl (base form) | tag=g6red-M22 start=03:58:56 end=03:59:03 rc=1 | bootParallel:R33 |
| M23 | drop stableIdP.catch(...) | tag=g6red-M23 start=03:59:03 end=03:59:09 rc=1 | bootParallel:P12 |
| M24 | freezeOnBlur removed | tag=g6red-M24 start=03:55:14 end=03:55:21 rc=1 | freezeOnBlur:R34 |
| M25 | fastHit always true | tag=g6red-M25 start=03:55:21 end=03:55:28 rc=1 | homeFloor:P1, homeFloor:R4b (R-G6-4 new mutant) |
Totals: 25 mutants, 24 KILLED (all by an assertion), 1 SURVIVED (M14, equivalent: ruling requested). M22/M23 were re-run on the final bootParallel bytes (P12 hardened with a tracking Promise binding so M23 fails on an assertion, not on a runner-level unhandled rejection).

## 5. Comm set (section 12.1)
List: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/bd48b535-2d58-47fc-9bbe-cf719f400b7b/scratchpad/S81-G6_red/COMM_SET.txt (142 = 125 jest + 12 cl2 + 5 backend pins); reasons: C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/bd48b535-2d58-47fc-9bbe-cf719f400b7b/scratchpad/S81-G6_red/comm_reasons.tsv
Base side: the 14 base-touched suites reuse the spec line [jest] tag=g6spec-base-touched start=03:11:18 end=03:11:34 rc=0 (14 suites, 137 passed, 5 todo, 0 failed); the other 111 + the 12 cl2 files once at base by path:
[jest] tag=g6red-comm-chunk_base_00 files=25 start=04:05:42 end=04:06:31 rc=0
[jest] tag=g6red-comm-chunk_base_01 files=25 start=04:06:34 end=04:06:48 rc=0
[jest] tag=g6red-comm-chunk_base_02 files=25 start=04:06:49 end=04:07:04 rc=0
[jest] tag=g6red-comm-chunk_base_03 files=25 start=04:07:06 end=04:07:25 rc=1
[jest] tag=g6red-comm-chunk_base_04 files=23 start=04:07:26 end=04:07:40 rc=1
DONE
  -> 123 suites: 1264 passed, 41 failed = 37 cl2 RED nodes + the 4 config/nativeBundle.w37 drift nodes.
Head side (prototype in place, 137 suites):
[jest] tag=g6red-comm-chunk_head_00 files=25 start=04:00:12 end=04:00:27 rc=0
[jest] tag=g6red-comm-chunk_head_01 files=25 start=04:00:28 end=04:00:44 rc=1
[jest] tag=g6red-comm-chunk_head_02 files=25 start=04:00:45 end=04:00:58 rc=0
[jest] tag=g6red-comm-chunk_head_03 files=25 start=04:00:59 end=04:01:17 rc=1
[jest] tag=g6red-comm-chunk_head_04 files=25 start=04:01:18 end=04:01:33 rc=0
[jest] tag=g6red-comm-chunk_head_05 files=12 start=04:01:34 end=04:01:41 rc=0
DONE
  -> 1436 passed, 6 failed = the 4 w37 drift nodes + HomeScreen.minDisplayFloor (1 node) + ResultsEntryParams.a18 (1 node), both caused by R-G6-4 (deviation D1/D2); with E6/E7 applied: [jest] tag=g6red-proto-E6E7 start=04:04:14 end=04:04:28 rc=0 -> 2 suites 18 passed.
Sorted failed sets (non-cl2): base = head-final = the 4 w37 nodes:
```
__tests__/config/nativeBundle.w37.test.ts::W3-7 (d) runtime dependencies are imported, justified, or pending removal > d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules
__tests__/config/nativeBundle.w37.test.ts::session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k2 package-lock.json and node_modules resolve the five packages at or above those patches
__tests__/config/nativeBundle.w37.test.ts::session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k4 eslint-config-expo is on the SDK-54 line (~10.0.x) in package.json, the lock and node_modules
__tests__/config/nativeBundle.w37.test.ts::session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k5 offline expo-install consistency: every declared package the installed expo bundles satisfies its bundled range, apart from expo.install.exclude
```
comm -13 (head-only) = EMPTY; comm -23 (base-only, pre-existing suites) = EMPTY; the 37 cl2 nodes are base-only by design (RED -> green on the prototype).
Backend pins: base 210 passed (spec line) / prototype 210 passed (g6red-be-pins-proto): no difference.

## 6. Deviations from the spec (rulings win; reported, not silently changed)
- D1 (E6, NEW E-row needed): __tests__/ResultsEntryParams.a18.test.ts:153 pins the Results param declaration as the literal list [comparison_id, result, vision_products]; R-G6-4 adds `fastHit?: boolean` to src/types/types.ts Results, so the list must gain fastHit. Measured red on the prototype; green with the one-line amendment.
- D2 (E7, NEW E-row needed): __tests__/HomeScreen.minDisplayFloor.test.ts:157-164 requires exactly one `navigation.navigate('Results' as any, { result })`; any form that adds fastHit: true on the fast path breaks it (spec 4.1 says this suite stays green: false under R-G6-4). Prototype amendment: the regex also accepts `fastHit ? { result, fastHit: true } : { result }`.
- D3 (R29): the spec row says the stock config does not collapse the Sentry debug frame; measured on the installed expo/metro-config the STOCK customizeFrame already returns collapse:true for node_modules/@sentry/core/cjs/debug.js (and instrument.js), so the behaviour alone is not RED. R29 additionally pins that symbolicator.customizeFrame is Sentry's withSentryFramesCollapsed wrapper (7.2.0 source names collapseSentryInternalFrames) and that an app frame keeps collapse:false.
- D4 (M14 equivalent): with swrRead's no-user guard and setSwrUser clearing on every change, a write that ignores the no-user guard is unobservable through the API; reported for a ruling instead of weakening R17.
- D5 (types file): R-G6-4 needs SmartCompareApp/src/types/types.ts (a 6th edited source file, beyond spec 3's list); the route-name pins stay green.
- D6 (fast-hit boundary): the prototype defines fastHit = 0 <= elapsed <= HOME_FLOOR_SKIP_BELOW_MS (the "renders now" band); rows pin t=100 (fastHit) and t=350 / t=1500 (no fastHit) only, so GREEN may choose the exact boundary.
- D7 (R30 form): R30 accepts an explicit type argument (`lazyScreen<Props>(() => import(...))`) because tsc rejects the untyped `.then` form for NewOnboardingHost (named export); spec 2.3 C6 form as written fails tsc.
- D8 (unhandled rejection rows): under jest-circus a real unhandled rejection is reported as a test ERROR and never reaches a test's process listener, so the `unhandledRejection` listener checks in R12 / P12 are vacuous as listeners; the catch is instead pinned by a recorded thenable (R12) and a tracking Promise binding injected into the boot block (P12).
- D9 (prototype fallback): lazyScreen fallback = <View style={{ flex: 1, backgroundColor: colors.bg.primary }} /> (R-G6-1); R31 pins backgroundColor === colors.bg.primary.
- No full jest run (LC-7); offline export not repeated (7.4).

## 7. Restore check
`git status --short` in sc-s81-g6: only `?? SmartCompareApp/__tests__/cl2/`; `git diff --quiet` = clean; snap.py verify: 10 edited files sha256 == base (App.tsx ef0669d1..., metro.config.js 20fa442d..., HomeScreen bee8b927..., ResultsScreen a1448cbd..., HistoryScreen 210c5c09..., types.ts b37759fc..., pb1 a2c950ec..., bundleB 679afdb5..., dedupe 446051e3..., loaderVisibility 601a3d7a...) + minDisplayFloor 8d8a4e0e... / a18 1fb90513... OK; the 4 new source files removed; .qa-mutation.lock removed; no scratch worktree was created; no pytest left running (only the stall monitors).

## 8. Files
Notes C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/bd48b535-2d58-47fc-9bbe-cf719f400b7b/scratchpad/S81-G6_red/notes.md; snapshot/mutation harness snap.py, mutate.py, mutation_results.json, mut_M*.json; comm chunk logs chunk_{base,head}_NN.{log,json}; failed_base.txt / failed_head.txt / failed_head_final.txt; base_red_assertions.tsv; be_pins_proto.log.
