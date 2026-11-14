## S95-LOGO RESULT-LOGO-OVERLAY: no MYEZ badge over the result page

A client unit with no runtime flag. It reaches phones only through the third over-the-air update for runtime 1.0.0, published after the merge.

### The defect

The owner saw a large MYEZ logo drawn over the result page while scrolling and ruled it an error ("MYEZ logo is an error it shouldnt be shown").

The cause is in `ResultsContent.tsx`. Once the winner is revealed in normal mode, it mounts the winner-reveal celebration `RevealBurst` in an absolute-fill slot over the score bars, and it never unmounts it. The celebration's six particles fade out. Its badge does not: a 112 px circle holding the MYEZ mark (`QarenLogo` at `BADGE_R` = 56) only springs its scale from 0 to 1. So the badge stayed over the bars for the life of the screen and scrolled with the page.

### The change

- `SmartCompareApp/src/components/results/ResultsContent.tsx`: removed the `RevealBurst` import, the slot (`results-v2-reveal-burst-slot`), its `revealBurstSlot` style and the `isWeird` constant that only gated it. `comparisonId` and `winnerRevealed` are no longer destructured; both stay in the props interface, so no call site or test changes type. The comments that described the celebration as preserved now say why it is gone.
- `SmartCompareApp/src/screens/ResultsScreen.tsx`: removed one unused `RevealBurst` import.
- `RevealBurst.tsx` and its own tests stay. A dozen result suites `jest.mock` its path, and retiring it is a separate cleanup.
- The winner card's own scale animation (`winnerScaleAnimStyle`) is unchanged.

### Tests

- NEW `SmartCompareApp/__tests__/s95logo/resultLogo.s95logo.test.tsx`, five rows:
  - L1: a revealed winner, rendered with the REAL `RevealBurst`, shows no slot, no `reveal-burst-badge` and no `QarenLogo`.
  - L2 / L3: the bars still render. Weird mode and the not-yet-revealed state also show no badge.
  - L4: a TypeScript-AST scan finds no result-page module (`ResultsScreen.tsx` and every `.tsx` under `components/results/`) that imports or renders `RevealBurst` or `QarenLogo`.
  - L5: no `revealBurstSlot` style.
  - At base 731bcddf, L1, L4 and L5 fail on assertions and L2 and L3 pass. Mutants M1 (the import back), M2 (the element back) and M4 (a bare `QarenLogo` in the section) are killed.
- Deliberate re-pins of pins that encoded the removed celebration:
  - E1, `__tests__/components/ResultsContent.render.test.tsx`: the slot is absent even when the winner is revealed.
  - E2, `__tests__/ResultsScreen.bundleE.s3.test.tsx`: the result page mounts no `RevealBurst`.
  - E3, `__tests__/screens/ResultsScreen.weird_mode.test.tsx`: the three source scans for the `isWeird` celebration guard become one row asserting the celebration is gone. Its prune and no-banner rows are unchanged.

### Gates (local; CI on the exact lock is the arbiter)

- RED file: 5 of 5 at HEAD.
- The 75 suites that name ResultsContent, ResultsScreen or RevealBurst, plus the RED file: 807 passed, 13 todo.
- Full jest suite: 4,042 passed. The only failures are the 4 known `nativeBundle.w37` install-drift nodes (d5, k2, k4, k5); each was proved to fail at base bytes as well.
- `tsc --noEmit`: 0 errors.
- eslint over the two src files: 0 errors and no new warning (ResultsScreen has one fewer).
- The 27 backend tests that read client files: 2,140 passed.
- One adversary (the unit is SAFE by the leaner chain): SOUND. It checked the six-path diff, the frozen RED file and an import-closure scan showing that nothing on the result path reaches `QarenLogo` or `RevealBurst`. It also confirmed that the winner-card scale animation is intact and that every mutant is killed.

### Stated limits

- The emerald particle celebration goes with the badge. A particles-only celebration would be a later design choice.
- `RevealBurst.tsx` remains in the tree unused by production code, together with its tests, its census rows and the `jest.mock` lines that name its path.
- The loading views, the Home compare loader and the ResultsScreen loading state, keep `LoadingRings` with its small centered mark. They are not the result page.
- Local jest ran on an install with expo 54.0.34 against the lock's 54.0.37. Every jest-relevant package matched.
- A phone runs the change only from its second cold start after the update is published.
- The guard is file-scoped to the result page (adversary MIN-1). A `RevealBurst` mounted from a result child outside `components/results/`, for example `FeedbackCard`, would pass the RED file. The in-app mark census still fails on any new direct `QarenLogo` import anywhere in `src`.
- Some test prose still describes the removed client weird-mode branch (MIN-2): the header and describe title of `ResultsScreen.weird_mode.test.tsx`. So does one comment in `src/theme/motion.ts:91` (MIN-3). Prose only.

### After the merge (the relay's steps; nothing here flips or publishes)

- Publish the third over-the-air update from the merge sha. Its bundle is the second update's client (ea47cbfb) plus exactly the two src files above, and `git diff --name-only ea47cbfb <merge> -- SmartCompareApp` minus `__tests__` must list only them. No package, lock or app.json change, and app.json says 1.0.0.
- The proof is on the owner's phone after the second cold start: a compare with a clear winner, then scroll past the score bars. There must be no MYEZ badge.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
