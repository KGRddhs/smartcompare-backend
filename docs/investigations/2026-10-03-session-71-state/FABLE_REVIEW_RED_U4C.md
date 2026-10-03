
---

## Orchestrator gate on the RED tests (BINDING - supersedes everything above where they differ)

Fable orchestrator, session 71, 2026-10-03 09:44 +03. Verdict: **PASS, no change**. GREEN may start.

Reviewed (sha256 prefixes): `__tests__/components/QarenLogo.test.tsx` `d9241b8cea42`, `__tests__/SplashScreen.test.tsx` `c23f00d8e19b`, `__tests__/components/hero/LoadingRings.test.tsx` `061dfb0868e9`, `__tests__/brand/inAppMark.u4c.test.ts` `ca1d728067fd`, `__tests__/SplashScreen.mark.u4c.test.tsx` `4993e2cf25c5`, `__tests__/utils/splashMarkLayout.u4c.test.ts` `85bfc54fbe15`. Measured by the RED agent at base `eb86075e`: exactly 27 tests fail (A1-A8, B1-B5, B9-B11, B13, C1-C4, C6, D1-D3, E1, F1), each for its stated reason; the five PINs pass; the neighbour set and the FULL suite show no other failure (3446 passed, 27 failed, 3499 total, 44 snapshots passed); tsc and eslint clean; no `.snap`, no file under `src/`, `assets/`, `scripts/` changed. A scratch prototype passed all 39 tests and 22 simulated mutants were killed. The orchestrator read the splash test file in full.

- **UG1 - the RED deviations are accepted:** C3 finds the mark through the accessibility-hidden host so it fails at base for its stated reason; the local structural node type; `jest.requireActual` inside the test body; the `near(x, 0.01)` matcher; the deep style flatten; the stricter B6, B7 and B12; F1 passing the size explicitly.
- **UG2 - the splash wrapper's style keys are exactly `position`, `left`, `top`, `width`, `height`** (C1 and C6 pin the key set). `pointerEvents` and `testID` are props, not style keys. A GREEN that needs another style key on that wrapper is wrong.
- **UG3 - the six RED files are FROZEN.** A test edit needs a test defect proven by measurement and is reported as a deviation.
- **UG4 - the GREEN target** after the one authorised snapshot update: Test Suites 3 skipped, 354 passed, 354 of 357 total; Tests 13 skipped, 13 todo, 3473 passed, 3499 total; Snapshots 44 passed.
- **UG5 - `B6` pins `manifest.pillow` to `12.3.0`:** the renderer is run only with the pinned venv.
