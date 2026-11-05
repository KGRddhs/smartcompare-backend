# S81-G6 ADVERSARY REPORT -- lens: correctness (LC-1 with the App-Review / auth / quota / engineering checks, R-G6-14 / GC-10)

Agent: Opus 5.5 (claude-opus-5-5), 2026-11-05 04:50-05:15 AST. Worktree sc-s81-g6, branch feature/s81-g6-client-perf, HEAD ab4b3b3184f176568e97ad852b9cfdebea8ffd9c (verified first and last), base ec747b49.

VERDICT: SOUND (no blocking, no major). The minors below become stated limits (LC-4).

## Method note (a conflict in the brief)
The computed brief's tail says "never edit the worktree; use a scratch worktree". GC-10 (binding) and the unit text say THE CLIENT EXCEPTION applies: probes run IN PLACE under .qa-mutation.lock, because a scratch worktree would need a node_modules junction. I followed GC-10. Every mutant and the OFF run used shutil.copyfile byte copies under <worktree>/.qa-mutation.lock, and each file was restored and sha256-compared after its run (harness: mut.py and off.py in this folder; zero RESTORE MISMATCH). End state: `git status --short` EMPTY, HEAD unchanged, no lock left, junction intact.

## Identity checks
- The 12 frozen RED files were re-hashed first and last: all equal to the GC-1 table.
- GREEN_SHA_TABLE.tsv: all 29 rows match the sha256 on disk (29 checked, 0 bad).
- Diff hygiene: 0 added lines with bytes > 127. New files are LF + ASCII. Existing files' blobs are LF (core.autocrlf=true, CRLF on disk), the same as base. No package / app.json / native / i18n / .env / .snap path. authService.ts is byte-identical (git diff --quiet). Every removed line is justified: the five static imports, the getStableId await, MIN_LOADING_MS, the E-row assertions, the metro default-config lines and the History initial states.
- Toolchain by path: jest 29.7.0, typescript 5.9.3, eslint 9.39.4, @sentry/react-native 7.2.0, react-native-screens 4.16.0, expo 54.0.34.

## Runs (every line)
- [jest] tag=adv-cl2-erows start=04:51:50 end=04:52:02 rc=0 -> 18 suites (12 cl2 + the 6 E-row files), 148 passed, 5 todo.
- OFF (base sources put back in place, the 4 new leaves removed): [jest] tag=adv-off-cl2 start=05:08:38 end=05:08:53 rc=1 -> 37 failed, 20 passed of 57. This is exactly the RED split.
- [tsc] tag=adv-tsc start=05:09:00 end=05:09:08 rc=0.
- [eslint] tag=adv-eslint start=05:09:11 end=05:09:20 rc=0 files=28 -> 0 errors, 99 warnings (the same count as GREEN).
- [jest] tag=adv-inband-app start=05:12:37 end=05:12:44 rc=0 -> --runInBand over GREEN's orderA (21 App.tsx-reader suites), 115 / 115.
- Comm chunks (GREEN's lists): [jest] tag=adv-chunk-01 start=05:11:35 end=05:11:48 rc=0 (22 passed + 3 skipped suites; 229 passed, 13 skipped; matches GREEN's line). [jest] tag=adv-chunk-03 start=05:11:52 end=05:12:07 rc=0 (25 suites, 174 passed). [jest] tag=adv-chunk-05 start=05:12:12 end=05:12:25 rc=0 (25 suites, 268 passed).
- Comm-set re-derivation (see m1): [jest] tag=adv-twoinput start=05:11:23 end=05:11:32 rc=0 -> src/components/__tests__/TwoInputShell.test.tsx 56 / 56.
- [pyt] tag=g6adv-be-pins start=2026-11-05 05:12:58 end=2026-11-05 05:13:15 elapsed=17s bound=600s status=OK rc=0 -> 210 passed (the 5 SmartCompareApp-scanning backend pins; base also 210). [netguard] printed sentinel lines only.
- Export (a MEASUREMENT): [export] tag=adv-export start=05:13:23 end=05:13:39 rc=0, "iOS Bundled ... (2214 modules)". index-f5bb695e0e11bd260f79a7b05128b75a.hbc = 6,355,018 B (rrweb 0, ReplayContainer 0, replayIntegration 1). This reproduces GREEN's pair against base 6,594,787 B / 2211 modules (-239,769 B). The output was deleted; no .expo or dist folder was left.

## Mutants (in place, over the 18-suite set; logs adv-mut-*.log, mut_results.jsonl)
Spec mutants on the GREEN bytes: 24 applied (M14 left out as equivalent by GC-3). ALL 24 KILLED by assertions:
M1 (5 rows), M2 (6), M3 (R2), M4 (R3, R8), M5 (8), M6 (R8), M7 (R10), M8 (R11), M9 (R12 x2), M10 (R14), M11 (R7, R15), M12 (R19), M13 (R18), M15 (R22), M16 (R24), M17 (R25), M18 (R26), M19 (R27, R28, the P-B1 fence), M20 = ScanCamera back to a static import (R30), M21 (R31, P17), M22 (R33), M23 (P12), M24 (R34), M25 (P1, R4b mid, minDisplayFloor).
Own mutants, KILLED:
- O2: the warm initial state dropped (R23).
- O3: Results reads fastHit as always true (R8b, P3, a18).
- O4: the FIFO bound 32 -> 100000 (R14).
- O6: the Results prefetch effect dropped (R15, a regex row).
- O8: the fallback colour set to '#ffffff' (R31).
- O9: the setSwrUser effect deps set to [] (R25, a regex row).
- O10: a mismatched stamp key (R22, R23).
- O12: initialLoading true on a warm cache (R23).
- O13: a negative floor (P1, R2).
- O14: setSwrUser clears on the same id (R19).
SURVIVED: four own mutants, each equivalent or a test gap on correct code (minors m2 and m3):
- O1: Home's fastHit `<=` -> `<` at 300.
- O5: swrRead's no-user guard removed. Equivalent by the GC-3 reasoning: setSwrUser clears on every change, so no entry exists while the user is null.
- O7: `measuredStart !== null` dropped. Equivalent on both callers, since both set the ref (GREEN D-G5).
- O11: the missing-Image.prefetch guard removed. Same behaviour: calling undefined throws inside the try and is swallowed, so R13 cannot tell.

## Probes (claims checked against runtime truth)
- No copy or flow change: the five lazy screen modules and Legal / Paywall are not in the diff, so every string they render is the base string. The fallback is `<View style={fallbackStyle} />` with colors.bg.primary and no Text (R31 / P17 / M21 / O8). The lazy bindings are used as Stack.Screen components and inside render functions (App.tsx :413-:516). HEAD has 15 eager static screen imports (Legal :55, Paywall :64). index.ts's first import is ./src/services/sentryBootstrap.
- Auth: authService.ts is byte-identical. There is exactly one `useEffect(() => { setSwrUser(user?.id ?? null); }, [user?.id]);`. Every sign-out path in App.tsx ends in setUser(null) (:310, :369).
- Quota: HomeScreen's referral / usage useFocusEffect (:167) is unchanged in the diff, and Home has no swrCache import (P18).
- fastHit: fastHit = a measured start AND 0 <= elapsed <= 300 (inclusive, the same as homeFloorDelayMs's 0 band). Home navigates with `fastHit ? { result, fastHit: true } : { result }`, and Results calls `revealDelayMs(route?.params?.fastHit === true)`. The history entries (comparison_id: History :814 / :823, Home :1196, Profile :412) and the camera entries (Home :721, ScanCamera :282 / :306) never pass fastHit, so they keep 800 ms (P3, R8b, O3). ResultsScreen's CAMERA_FLOOR_MS 1200 and HISTORY 400 / 300 are untouched.
- Prefetch: the first two products only, https only, at most 2048 chars, a FIFO dedupe of 32, a try plus an attached catch, and no log (M7-M10, O4, R12).
- Throttle and invalidations: the throttle uses >= 30000 (M13). Only a successful load stamps the cache. A delete and every Results mount invalidate history:*. Refresh, submit and retry always fetch (P5).
- Boot: `Promise.resolve().then(getStableId)` plus `.catch(() => undefined)` come before `await getSavedLanguage()`, and the promise is awaited at the old place. init().catch().finally(setIsLoading(false)) is unchanged. P12 pins the rejection path (M23 killed). Note: getSavedLanguage is called first in the same tick and getStableId one microtask later. The two reads overlap, which is what R-G6-7 asks.
- Metro (read in the installed 7.2.0 source): getSentryExpoConfig calls expo/metro-config getDefaultConfig with the debug-id and release-constants plugins. It then applies withSentryFramesCollapsed, withSentryResolver (only when includeWebReplay === false) and withSentryMiddleware (dev server only). cacheVersion is composed once on top (P8, E1). No app code imports a replay integration, so the empty-module mapping cannot be observed at runtime on native.
- The export byte pair reproduces (above). tsc and eslint are clean.

## Findings
Blocking: none. Major: none.

Minor (stated limits / documentation rulings):
- m1 COMM-SET GAP (closed by this adversary's run): src/components/__tests__/TwoInputShell.test.tsx reads src/screens/HomeScreen.tsx by path (HOMESCREEN_PATH, :82). It is NOT in GREEN's 158-file comm list (COMM_SET_jest_green.txt) and not in the RED's list. I ran it: green at HEAD (adv-twoinput, 56 / 56), so `comm -13` stays EMPTY. The brief's rule makes an UNMEASURED missing file a MAJOR. This one has been measured, so I record it as a minor. Two follow-ups: the PR body's comm set should read 159 jest files (+ TwoInputShell), and the final round's comm set must include this file.
- m2 TEST GAP: O1 survives. No test pins GC-4's INCLUSIVE 300 boundary at the Home level (R4b uses t=100 and t=350). R2 / M3 pin the boundary in the leaf. GREEN's code is correct (`<=`). Stated limit: the Home 300 ms edge is pinned only through homeFloorDelayMs.
- m3 EQUIVALENT MUTANTS O5 / O7 / O11 (see above): nothing observes them through the API or the callers, so no new row is needed.
- m4 SWR WRITE RACE: loadHistory captures no generation and no user. If a History fetch is still in flight when Results mounts, Results' invalidation runs first and the late fetch then stamps a list older than a just-saved comparison. A History tab focus within the next 30 s shows that list without the new row; pull-to-refresh fixes it. This is narrow: it needs an in-flight History fetch to overlap a sub-second KB-first compare. It is the same class as GREEN's GC-11 / 9.3 limit, which should name it.
- m5 STALE COMMENTS: three HomeScreen.tsx comments still describe the removed 1200 ms floor: :195 "Min-display floor (1.2s)", :1210 "The min-display floor (1.2s)" and :224 "for up to 1.2s". They are comments only; behaviour is unaffected.
- m6 EXPORT HASH: this run did not reproduce the GREEN report's hbc sha256[:16] e34ff39a37059de5 (this run: 6f548e2d2d9ec20c). The file name, the size 6,355,018 B and the 2214 modules do reproduce. The PR body cites only the byte pair, so it needs no change. This is a measurement note.

## Prove-nothing rows (source-regex rows that cannot fail on runtime behaviour)
R15 (the Home / Results prefetch wiring), R25 / R26 (where setSwrUser and the invalidation sit), R27 static, R30 / P10 (import shapes), R34 / P13 (the freezeOnBlur text), P14-P16 (features / package / fonts), P18 (Home not cached), and E2 / E3 / E6 / E7 (source regexes). Jest does NOT measure the runtime behaviour these rows stand for: the freezeOnBlur effect, the first open of a lazy screen on a device, and cold start. That stays with owner step 3 (GC-11).

## Files
mut.py, off.py, mut_results.jsonl, mut_run2.out, adv-*.log, tsc.log, eslint.log, be_pins.log, export.log, and missing.txt (my union candidates; of these, only TwoInputShell reads a changed file).
