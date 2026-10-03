## U4c: the in-app MYEZ mark (replaces the old Qaren Q-ring)

Session 71, MYEZ Apple launch lane. Spec: `docs/investigations/2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md` (body, review corrections 1-12, orchestrator rulings UR1-UR15, RED gate UG1-UG5).

**OTA-capable AND required in the store binary (UR15).** The unit adds no native dependency; `app.json`, `eas.json`, `package.json` and the lock are byte-unchanged, so it can ship by `eas update`. The App Review build embeds its JS bundle, though, so this PR must merge BEFORE the production build (L6).

### What changes
- **`src/components/QarenLogo.tsx`.** It now draws the MYEZ mark (the black MY/EZ wordmark and the emerald dot) as ONE React Native `Image` of a bundled PNG.
  - The source is a module-scope `require('../../assets/brand/myez-mark.png')`, drawn with `resizeMode="contain"` and `fadeDuration={0}`. Android fades non-resource images in over 300 ms, and an OTA-delivered asset is a file, not a resource.
  - It stays hidden from VoiceOver/TalkBack exactly as before (`accessibilityElementsHidden`, `importantForAccessibility="no-hide-descendants"`).
  - It has no `color` prop, no tint, no `react-native-svg` and no `expo-image`. Path, name and default export are unchanged, so all six sites keep their `<QarenLogo size>` calls.
- **`assets/brand/myez-mark.png`, `@2x`, `@3x` (128/256/384 px, RGBA).** These are rendered from the committed master by `scripts/render_myez_icons.py`.
  - The renderer gains `MARK_SIZES`/`MARK_NAMES` and two new top-level manifest keys, `mark_outputs` and `mark_geometry` (+40 lines, 0 removed).
  - `OUTPUT_NAMES`, `outputs`, `params` and the four launcher files do not move by one byte. `--check` reports 7x `pixels match` plus `manifest matches`.
- **D1: no app-name text beside the mark.** The `t('app.name')` wordmark is removed from Splash and from the Home header, together with its now-unused styles. The i18n catalogs are unchanged.
- **D2: the splash hand-off does not move.**
  - The new pure `src/utils/splashMarkLayout.ts` computes where the iOS launch storyboard draws the mark: `splash-icon.png` aspect-fit across the window, with constants equal to `manifest.mark_geometry`.
  - `SplashScreen` draws the mark at exactly that rect, at full opacity and not animated. The wrapper is a plain `View testID="splash-mark"` with exactly `position/left/top/width/height`.
  - Under RTL, React Native swaps a physical `left`, while the launch screen is never mirrored. `left` is therefore pre-mirrored at render time (`I18nManager.isRTL && doLeftAndRightSwapInRTL !== false`).
  - Only the tagline animates (same 200 ms delay and 400 ms fade). It sits 20 pt below the mark and is centred on the screen. The ready/min/max floors are byte-unchanged.
  - Measured hand-off error versus the native frame is at most about 0.34 pt on 8 iPhone windows (tolerance 0.5 pt).
- **D3: one authorised snapshot update.** `__tests__/hero/__snapshots__/LoadingRings.test.tsx.snap` was produced by a single `jest --ci -u` on that file. Its sha256 is `7d22d5444df76638082781bc047c6397d091bf46793e444007b7afae79669e07`, as pre-computed by the spec. The diff swaps the 32x32 Svg Q-ring for the Image, in two identical hunks. No other `.snap` changed.

### Tests
- Three new suites: `__tests__/brand/inAppMark.u4c.test.ts` (assets, manifest, sites, D1 AST fences), `__tests__/SplashScreen.mark.u4c.test.tsx` (C1-C6 incl. RTL) and `__tests__/utils/splashMarkLayout.u4c.test.ts` (layout table, a pixel hand-off check against the committed `splash-icon.png`, purity).
- Rewritten: `QarenLogo.test.tsx`, SplashScreen case 1 (inverted to "no app name") and LoadingRings case 2 (host Image at 70/53/26).
- 27 REDs failed at base for their stated reasons. 25 GREEN mutants plus an adversary set were killed.

### Gates (fix-round re-run on the final bytes, each inside a 16-file sha bracket)
- Full jest: `Test Suites: 3 skipped, 354 passed, 354 of 357 total` / `Tests: 13 skipped, 13 todo, 3473 passed, 3499 total` / `Snapshots: 44 passed, 44 total`.
- Unit files: 6 suites, 39 passed.
- Neighbours (Splash floors, LoadingRings, Step01Welcome, nativeBundle w37, brand and i18n fences, rtl, the 10 QarenLogo-mocking suites): 30 suites, 284 passed, 2 snapshots.
- `tsc --noEmit`: clean.
- eslint on the 10 changed files: 0 errors (3 base warnings in HomeScreen).
- Renderer `--check` OK. black and ruff clean.
- Backend client-scanning tests (17 files): `1608 passed, 4 deselected` (`[pyt] status=OK rc=0`).
- `expo export:embed --platform ios` (offline): all three PNG scales are copied, and the compiled QarenLogo carries `contain` / `fadeDuration:0` / a11y-hidden.
- Untouched-file diff is empty (app.json, eas.json, package.json, lock, App.tsx, i18n, mocks, configs, launcher PNGs, other sites).

### Device checks before the production build (UR5; not testable in jest)
1. **White or blank flash at the hand-off.** Check on a FRESH install (embedded bundle) and again after an OTA. Causes: the expo-updates white gap before the first JS frame, plus at least one frame of asynchronous image decode, while the tagline starts at opacity 0. If it is visible, a native `expo-splash-screen` unit is needed in the production binary: `hideAsync` from the mark Image's `onLoad`, `enableFullScreenImage_legacy: true`.
2. **Mark sharpness** at 24 pt (History), 28 pt (Home, Profile) and in the loaders, on a 2x and a 3x iPhone.
3. **Home header** is 2 pt shorter now that the wordmark is gone.
4. **Arabic:** the splash mark must not jump horizontally (the RTL pre-mirror).

### Accepted limits and out of scope
- **Not in this unit (UR3, issue #283; decide before the production build):**
  - the old `QaranIcon` Q-magnifier in the Results winner reveal (`RevealBurst`). Replacing it needs two more snapshot authorisations.
  - the text-only `t('app.name')` logos on ForgotPassword and Register.
- **Android hand-off still jumps** (legacy 200 dp splash). Accepted for the Apple-first lane (#281).
- **Dark or tinted surfaces.** The mark's transparency is exact over white or near-white only; every current site is #FFFFFF or #F1F3FF. A future dark surface needs its own asset.
- **Accessibility.** No brand name is announced on Home or Splash; the mark stays hidden from accessibility as before (UR6).
- **Follow-ups:**
  - stale "Q-ring" / "Q logo" comments in `LoadingRings.tsx`, `ProfileScreen.tsx` and `HistoryScreen.tsx` (files this unit must not touch).
  - optional extra tests pinning the mark's post-mount opacity and the tagline's position and delay. The implementation matches the spec; today only the first frame and the text are pinned.

## Orchestrator review (session 71)
- Process: Opus spec, Opus adversarial spec review (12 corrections, one MAJOR: the splash mark would have landed about 6 pt off the launch screen in Arabic because React Native mirrors left and right), orchestrator rulings, Opus RED gated PASS, Opus GREEN, two Opus adversaries (visual / App Review and engineering), both SOUND; the fix agent changed nothing.
- The orchestrator re-hashed the ten changed files against the reports, read `QarenLogo.tsx`, `splashMarkLayout.ts` and the two screen diffs, and confirmed exactly one `.snap` changed (sha `7d22d544...`, the single update the owner authorised).
- The branch is fast-forwarded to main `ca604e0a` (PR #285 touched no client file). On that tree: FULL jest 354 suites passed, 3,473 tests passed, 44 snapshots passed; tsc clean.
- Known test gaps, implementation correct (follow-up issue): a fade of the splash mark AFTER the first frame and the tagline position and delay are not pinned; the six RED files were frozen after the gate.
- Out of scope by ruling, issue #283: the Q-magnifier in the winner reveal and the text-only logos on the forgot-password and register screens.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
