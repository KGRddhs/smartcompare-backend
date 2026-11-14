# S95-LOGO RESULT-LOGO-OVERLAY: unit spec (session 95 main lane, 2026-11-14)

- Unit: S95-LOGO. No runtime flag (a client change; it reaches phones only through the THIRD over-the-air update for runtime 1.0.0, published by the relay after the merge).
- Class: SAFE by LC-1 (orchestrator ruling, recorded here and in the GATE file): the diff removes one decorative element from the result page and one unused import; it adds no copy, no permission, no consent, auth, quota, legal, network or data-flow change, and no native change (no app.json, package.json or package-lock.json byte moves), so it is OTA-safe on the 1.0.0 binary. One adversary (correctness, with the checks of section 6 folded in). No spec-review adversary (LC-8).
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s95-logo, branch fix/s95-result-logo-overlay, base = origin/main 731bcddf531a7e123963246168ca19f262859337 (HEAD = base, git status empty at the start). SmartCompareApp/node_modules is a JUNCTION to the clone's node_modules: never delete, move or recreate it; never run a recursive delete. The clone's node_modules carries expo 54.0.34 against the lock's 54.0.37 (every jest-relevant package matches: jest 29.7.0, @testing-library/react-native 13.3.3, react-native 0.81.5, reanimated 4.1.7, typescript 5.9.3, eslint 9.39.4); CI is the arbiter.
- Measurement location: the scratchpad notes folder of your round (<scratch>/s95logo/<round>/).
- The repository is PUBLIC: no personal value in any byte (synthetic product names only).
- Evidence: the owner's words 2026-11-13 (verbatim): "MYEZ logo is an error it shouldnt be shown" (a large MYEZ logo drawn over the result page while scrolling, two screenshots). Diagnosis: S95_FIRST_REPORT.md section 4 (in/ beside this file).

## 0. WHAT

The result page draws the winner-reveal celebration `RevealBurst` in an absolute-fill slot over the score bars once the winner is revealed in normal mode. Its six particles fade out, but its badge (a 112 px circle holding the MYEZ mark, `QarenLogo` at `BADGE_R` = 56) only scales 0 to 1 and never fades, and the slot is never unmounted, so the MYEZ badge stays over the bars for the life of the screen and scrolls with the page. The fix: stop mounting `RevealBurst` on the result page. The component file and its own tests stay (a dozen result suites `jest.mock` its path; deleting it would break them; a later cleanup can retire it).

## 1. BASE STATE (731bcddf, read with git show)

| file:line | fact |
|---|---|
| SmartCompareApp/src/components/results/ResultsContent.tsx:73 | `import { RevealBurst } from '../hero/RevealBurst';` |
| ResultsContent.tsx:89 / :105 | interface fields `comparisonId: string \| undefined;` / `winnerRevealed: boolean;` |
| ResultsContent.tsx:127 / :136 | both destructured in the component's parameter list |
| ResultsContent.tsx:529 | `const isWeird = scoring_v2.comparison_quality === 'weird';` (its only reader is :536) |
| ResultsContent.tsx:536-548 | `{!isWeird && winnerRevealed ? ( <View style={styles.revealBurstSlot} pointerEvents="none" testID="results-v2-reveal-burst-slot"> <RevealBurst key={comparisonId \|\| 'no-comparison-id'} fireOnce particleCount={6} size={220} /> </View> ) : null}` |
| ResultsContent.tsx:543 | the ONLY reader of `comparisonId` in the file (:677 passes `feedbackComparisonId`, a different prop) |
| ResultsContent.tsx:866-880 | the comment above and the `revealBurstSlot` style (absolute fill, centered) |
| ResultsContent.tsx:20, :32, :112-121, :512-525 | comments naming RevealBurst (the header map, the memo note, the JSX block comment saying the celebration "is preserved") |
| SmartCompareApp/src/components/hero/RevealBurst.tsx:71 / :156 / :200 / :243 | `BADGE_R = 56`; particle opacity fades; the badge only springs its scale to 1; `<QarenLogo size={BADGE_R} />` inside `reveal-burst-badge` |
| SmartCompareApp/src/screens/ResultsScreen.tsx:102 | `import { RevealBurst } from '../components/hero/RevealBurst';` never rendered in that file (an unused import) |
| ResultsScreen.tsx:207 / :503 / :968 | `winnerRevealed` state, set true by the reveal timer, passed to ResultsContent (it also drives nothing else that this unit touches; the winner card scale `winnerScaleAnimStyle` is separate and stays) |
| SmartCompareApp/__tests__/components/ResultsContent.render.test.tsx:282-285 | PIN `renders RevealBurst slot when winnerRevealed=true and not weird` (expects the slot) |
| SmartCompareApp/__tests__/ResultsScreen.bundleE.s3.test.tsx:208-211 | PIN `orchestrator still renders RevealBurst keyed on comparisonId, fireOnce` (`<RevealBurst` and `fireOnce` in the ResultsContent source) |
| no backend test | no tests/*.py names ResultsContent, components/results or components/hero |

Base sha256 (git bytes): ResultsContent.tsx 53b7d70c3447a396e89458275c93c2d021dae05d98b0756932f78b40ec7ee055; ResultsScreen.tsx fbefbd983764ff4cb2ae6a368595328178390f52c9b4c825e3764a360faed0c5; ResultsContent.render.test.tsx 0a1f0be0a24658b4a2bb27d14852906bad3a34e469e510fd75c530e442c3370f; ResultsScreen.bundleE.s3.test.tsx 996a8d3b60efa732d9065fea6d4a837a4d1091c98c11a859bd98432ed9448956.

## 2. CONTRACT

- After the change no module of the result page mounts `RevealBurst` or imports it, and nothing on the result page renders `QarenLogo`. "The result page" = `src/screens/ResultsScreen.tsx` and every `.tsx` under `src/components/results/`.
- Unchanged: the dimension bars section (`results-scoring-v2`, `results-v2-bars`) renders exactly as before in every mode; the weird-mode and `winnerRevealed=false` paths already render no slot; the winner card's own scale animation (`winnerScaleAnimStyle`); the ResultsContent props interface (both `comparisonId` and `winnerRevealed` stay as fields so no call site or test changes type; they are no longer destructured); `RevealBurst.tsx` and its tests; the loading view of ResultsScreen (`results-loading-state`, LoadingRings with its small mark) is NOT the result page and is not touched.
- No copy, no i18n key, no snapshot, no native file.

## 3. CHANGE LIST (take byte copies of every file first)

1. `SmartCompareApp/src/components/results/ResultsContent.tsx`:
   (a) delete the import at :73;
   (b) delete the conditional slot block :536-548 (the whole `{!isWeird && winnerRevealed ? (...) : null}` expression and the blank line after it);
   (c) delete `const isWeird ...` at :529 (no other reader); keep the IIFE shape otherwise unchanged (smallest diff);
   (d) delete `comparisonId,` (:127) and `winnerRevealed,` (:136) from the destructuring; keep both interface fields, each with one ASCII comment line: kept for the call sites, not read since S95-LOGO;
   (e) delete the `revealBurstSlot` style (:872-880) and its comment above it (from the comment line that introduces the slot, :866 or the nearest start of that comment, through :880);
   (f) rewrite the comments that would become false, ASCII only: the JSX block comment (:519-523) says the RevealBurst celebration is no longer mounted on the result page (S95-LOGO: its MYEZ badge never faded and stayed over the bars; the owner ruled the logo must not show); the header map line :20 drops "+ RevealBurst"; :32 drops RevealBurst from the contract list if it names it as mounted; the memo note :117 drops "+ RevealBurst mount". Comments elsewhere stay.
2. `SmartCompareApp/src/screens/ResultsScreen.tsx`: delete the unused import at :102. Nothing else in that file.
3. E-rows (section 4.1).
4. The RED file `SmartCompareApp/__tests__/s95logo/resultLogo.s95logo.test.tsx` (the RED round writes it; GREEN never edits it).
No other file. No CLAUDE.md change (no flag, no owner step beyond the update the relay publishes; the RED file is the regression guard; CLAUDE.md:259 still truthfully lists RevealBurst among the hero illustrations).

## 4. EXISTING PINS

### 4.1 Deliberate changes (GREEN edits them; each fails at head without the edit)
- E1 `__tests__/components/ResultsContent.render.test.tsx:282-285`: rename to `does NOT render the RevealBurst slot even when winnerRevealed=true (S95-LOGO)` and assert `queryByTestId('results-v2-reveal-burst-slot')` is null.
- E2 `__tests__/ResultsScreen.bundleE.s3.test.tsx:208-211`: rename to `result page mounts no RevealBurst (S95-LOGO)` and assert `RESULTS_CONTENT_SRC` does NOT match `/<RevealBurst/` and does not match `/from '\.\.\/hero\/RevealBurst'/`; the `fireOnce` assertion goes (that token lived only in the removed mount).
### 4.2 Stay green (measure, do not edit)
Every suite naming ResultsContent, ResultsScreen or RevealBurst (git grep at base, about 40 files: the `ResultsContent.*`, `ResultsScreen.*`, `Results.memo.m21`, `components/ResultsContent.*`, `screens/ResultsScreen.*`, `s11/*`, `clientTruth/medicalNote.s74`, `brand/inAppMark.u4c` (the QarenLogo site census still lists RevealBurst.tsx, unchanged), `brand/revealGlyph.u4d` (renders RevealBurst directly), `hero/RevealBurst*`, `components/hero/RevealBurst`, `primitives/MatchBadge`, `theme/motion`, `rtl/directionalIconWiring.contract`, `HomeScreen.bundleB.contract`, `InviteeQuizScreen.degraded.s69`, `ProductImage.resizeMode`, `screens/onboarding/Step15Reveal`). The suites that `jest.mock('.../hero/RevealBurst', ...)` keep working because the module still exists.

## 5. RED TESTS (`SmartCompareApp/__tests__/s95logo/resultLogo.s95logo.test.tsx`)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| L1 | render ResultsContent with a revealed winner in normal mode and >= 3 dimensions, the REAL RevealBurst (no mock of its path; copy the other mocks and the props of `__tests__/components/ResultsContent.render.test.tsx`) | `queryByTestId('results-v2-reveal-burst-slot')` null AND `queryByTestId('reveal-burst-badge')` null AND `UNSAFE_queryAllByType(QarenLogo)` length 0 | FAIL (AssertionError: the slot and the badge render) | 3.1 (b) |
| L2 | the same render | `getByTestId('results-v2-bars')` present and `getByTestId('results-scoring-v2')` present | PASS (PIN) | stays |
| L3 | the same render with `winnerRevealed=false`, and again with `comparison_quality='weird'` and `winnerRevealed=true` | no `reveal-burst-badge`, no QarenLogo; bars present | PASS (PIN) | stays |
| L4 | source scan (TypeScript AST via the project's `typescript` package, as `brand/inAppMark.u4c` does) of `src/screens/ResultsScreen.tsx` and every `.tsx` under `src/components/results/` | no import declaration whose module specifier ends with `hero/RevealBurst` or `/QarenLogo`, and no JSX element named `RevealBurst` or `QarenLogo` | FAIL (AssertionError naming ResultsContent.tsx and ResultsScreen.tsx) | 3.1 (a), 3.2 |
| L5 | source scan of `ResultsContent.tsx` | no `revealBurstSlot` key in the StyleSheet (AST: no property assignment named `revealBurstSlot`) | FAIL | 3.1 (e) |

RED rows fail at base on an AssertionError only (never an import or setup error). A failing-row message names the offending file or test id. Pure ASCII; no personal value; no snapshot; no `{ virtual: true }` mock of an installed package; plain `jest.mock(name, factory)` only. Prove the file with --runInBand at base (L1, L4, L5 fail; L2, L3 pass) and with the satisfiability prototype IN PLACE (byte copies of ResultsContent.tsx and ResultsScreen.tsx, apply the change list 3.1 and 3.2, run the RED file green, restore, sha256-compare against section 1).

## 6. MUTATION TABLE (GREEN or the adversary, on byte copies, restore and sha-compare)
- M1 re-add only the ResultsContent import (no mount): L4 kills.
- M2 re-add the mount without the slot View (RevealBurst directly in the section): L1 kills (badge / QarenLogo).
- M3 re-add the slot View with the RevealBurst but gated `winnerRevealed && false`: equivalent (dead code); expected survivor of L1, killed by L4 (the import) and L5 only if the style comes back: report it.
- M4 render `<QarenLogo size={56} />` directly inside DimensionBars' section in ResultsContent: L1 and L4 kill.
- Folded adversary checks: the diff touches exactly the files of section 3; no `.snap`; no i18n; no native file; the winner card scale animation still applies (ResultsScreen passes `winnerScaleAnimStyle`, ResultsContent still reads it); `comparisonId` and `winnerRevealed` have no remaining reader that the change silently broke; the a11y and memo suites stay green; the third-update bundle = exactly this unit's two src files on top of the second update's client (`git diff --name-only ea47cbfb <head> -- SmartCompareApp` minus `__tests__`).

## 7. GATES (cheapest first)
1. The RED file at head: 5 of 5 pass.
2. The E-row files and every 4.2 suite by path (jest --ci, one jest at a time on this box, wait for the slot first).
3. `node node_modules/typescript/bin/tsc --noEmit` (the whole project) and `node node_modules/eslint/bin/eslint.js` over the changed src and test files.
4. The backend SmartCompareApp-scanning tests (the 29 tests/*.py files that name SmartCompareApp, listed by `git grep -l SmartCompareApp -- 'tests/*.py'`; the precommit-hook files in their own call) through pyt.py, bound 1200 each call: expected all pass (the change only deletes client code); a failure is compared with the same node at base on the byte-copy prototype.
5. The FULL jest suite ONCE (LC-7), at the last round before the PR; any failure is re-run at base bytes (byte-copy restore of the two src files and the two E-row files) to prove it pre-exists.

## 8. CLAUDE.md ROW + owner steps
No CLAUDE.md change (section 3). Owner and relay steps: the third update, from the merge sha, by the relay's recipe (S95 writes it after the merge); the owner judges it on his phone after the SECOND cold start.

## 9. STATED LIMITS
- L-1: the emerald particle celebration goes with the badge (the owner's ruling covers the logo; a particle-only celebration is a later design choice).
- L-2: `RevealBurst.tsx` stays in the tree, unused by production code, with its tests, the census rows and a dozen `jest.mock` lines of its path; retiring it is a cleanup unit.
- L-3: the loading view of ResultsScreen and the Home compare loader keep LoadingRings with its small centered mark (not the result page).
- L-4: local jest runs on the clone's node_modules (expo 54.0.34 against the lock's 54.0.37); CI on the exact lock is the arbiter.
- L-5: the change reaches a phone only from the second cold start after the third update is published.

## 10. OUT OF SCOPE
The consent re-ask (no defect found; S95_FIRST_REPORT.md), every data-pipeline issue (the S95-FIX lane), the honest bars (INC-X6), the price-with-size rule (INC-X1), the page design.

## 11. OPEN QUESTIONS
None blocking. Not done in this spec: no code, no test, no run.
