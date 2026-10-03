
## Summary

The winner-reveal badge in `RevealBurst` drew the old Qaran "Q as a magnifier" glyph (`src/icons/QaranIcon.tsx`, 67 pt, `#0A0A0B`). It now shows the MYEZ mark that `QarenLogo` renders (the bundled `assets/brand/myez-mark.png`, 56 pt = `size={BADGE_R}`).

Register (the form and the email-confirmation state) and ForgotPassword replace their 36 pt bold `t('app.name')` text logo with the same mark (`<QarenLogo size={56} />`). Login is unchanged because it has no brand block.

`QaranIcon` and its barrel export are deleted, so no Q glyph is drawn anywhere in `src/`. Stale "Q-ring / Q logo / Q-mark" comments are corrected. New tests pin the splash so it can never animate after the first frame.

The change is client only, unflagged and OTA-capable. It must be on main before `eas build --profile production`, because the App Store reviewer and the screenshots see the embedded JS.

Spec: `docs/investigations/2026-10-03-session-71-state/U4D_REVEAL_GLYPH_SPEC.md` (sha256 `f40fbc8f…`), including its review corrections C1-C8, rulings UR1-UR14 and the RED gate UG1-UG6.

## What changed (src)

- `src/components/hero/RevealBurst.tsx`:
  - `import QarenLogo from '../QarenLogo'` replaces the QaranIcon import.
  - The badge's only child is now `<QarenLogo size={BADGE_R} />`, with no wrapper, no extra prop and no tint.
  - Unchanged: the badge itself (112 x 112, radius 56, `#ECFDF5`, the emerald shadow, the 0 → 1.1 → 1.0 spring), the particles and every constant.
  - The docstring gains one line.
- `src/screens/RegisterScreen.tsx`: both headers render `<QarenLogo size={56} />` and keep the `t('splash.tagline')` subtitle. The unused `logo` style is removed, and the file no longer calls `t('app.name')`.
- `src/screens/ForgotPasswordScreen.tsx`: the header renders `<QarenLogo size={56} />`, and the `logo` style is removed.
- `src/icons/QaranIcon.tsx` is DELETED. `src/icons/index.ts` drops `export { QaranIcon }`; every other export stays (Back, Close, Search, Bell, Settings, Plus, Scan, Link, Type, `flipForRTL`).
- Comment-only edits:
  - `LoadingRings.tsx`: two comments.
  - `UtilityIcons.tsx`: the SearchIcon comment.
  - `ProfileScreen.tsx`: two comments.
  - `HistoryScreen.tsx`: three comments. One claimed `alignItems: 'baseline'`, but the code is `'center'`.
  - `PhoneMockup.tsx`: the docstring claimed a "Q-mark" the code never drew.
- Accessibility and appearance come from `QarenLogo`, which this PR does not change. The Image is hidden (`accessibilityElementsHidden`, `importantForAccessibility="no-hide-descendants"`), uses `resizeMode="contain"` and `fadeDuration={0}`, and has no `tintColor`. No host up to the root carries a label.
- Untouched: `app.json`, `eas.json`, `package.json`, the lock, `App.tsx`, `assets/**`, the i18n catalogs, `__mocks__`, the jest, metro and babel configs, `QarenLogo.tsx`, `SplashScreen.tsx` and `LoginScreen.tsx`. `react-native-svg` stays a dependency, because nine other `src` files import it.

## Tests

New files:
- `__tests__/brand/revealGlyph.u4d.test.tsx` (R1-R9):
  - exactly one hidden, untinted 56 x 56 Image inside `reveal-burst-badge`, and no Svg-family host there;
  - an AST check of the import and of the badge's only child;
  - QaranIcon deleted and no longer exported;
  - no Q-glyph geometry or stale Q comment anywhere in `src/`;
  - the badge style and the remaining barrel exports pinned.
- `__tests__/screens/authBrandMark.u4d.test.tsx` (A1-A5): Register's form state and ForgotPassword each render one hidden 56 x 56 Image and no `app.name` text. An AST check covers Register's two marks and ForgotPassword's one. Login is pinned unchanged.
- `__tests__/SplashScreen.motion.u4d.test.tsx` (P1b, P2-P4):
  - every host from the splash Image to the root stays frozen at each 50 ms step up to 1,600 ms, and after `ready`;
  - the tagline is the only animation (`withDelay(200, withTiming(1, {duration: 400}))`);
  - its geometry is pinned in LTR and RTL.
- `__tests__/icons/flipForRTL.test.tsx`: the two `flipForRTL` cases, moved verbatim from the deleted `QaranIcon.test.tsx`.

Edited:
- `__tests__/brand/inAppMark.u4c.test.ts` (ruling UR8 only): `SITE_FILES` gains RevealBurst, ForgotPassword and Register, for nine importers in total. The B9 size map gains `expression:BADGE_R` (RevealBurst), `numeric:56` x2 (Register) and `numeric:56` (ForgotPassword).
- `__tests__/snapshots/visual-foundation.test.tsx`: the QaranIcon import and its two `it`s are removed.

Deleted: `__tests__/icons/QaranIcon.test.tsx`.

## Snapshots (exactly two authorised `jest --ci -u` runs, one per owning file)

- `__tests__/hero/__snapshots__/RevealBurst.test.tsx.snap`:
  - Both keys replace the 30-line QaranIcon `<Svg>` with the 17-line hidden `<Image … height 56 width 56>` (hunks `@@ -140,36 +140,23 @@` and `@@ -339,36 +326,23 @@`, +34/-60).
  - sha256 `57149ef59c89245c77f5cbd0cd947269fc48f4c8c7f6bba6d5e9a9d67ab9f887`, equal to the value the spec reproduced independently.
- `__tests__/snapshots/__snapshots__/visual-foundation.test.tsx.snap`:
  - The two QaranIcon keys are removed (0/-66), and the other 15 keys are byte-identical.
  - sha256 `67dde70b6c176bde01467ece1d2cae61db522e36d6d15983ae85a1c62a871b38`.
- No other `.snap` changed, and there are no orphan snapshot files.

## Gates (fix round, on the final bytes, 2026-10-03)

- Toolchain: jest 29.7.0, tsc 5.9.3 and eslint v9.39.4, run by path from `SmartCompareApp` under coreutils `timeout`.
- Full jest: `Test Suites: 3 skipped, 357 passed, 357 of 360 total` / `Tests: 13 skipped, 13 todo, 3485 passed, 3511 total` / `Snapshots: 42 passed, 42 total`, rc 0.
- The five gated test files: 5 suites passed, 33 tests passed.
- The 41-suite neighbour set: 41 suites passed, 410 tests, 23 snapshots. It covers auth, Register, Login, Splash, RevealBurst, LoadingRings, PhoneMockup, icons, the i18n fences, bundleD, brand.hardcoded, Profile/History, and the four ResultsScreen renderers.
- `tsc --noEmit`: rc 0, no output.
- eslint on the 15 changed and new files: 0 errors and 8 warnings. Every warning is pre-existing, and the count per file equals base.
- Backend tests that scan the client (17 files): `[pyt] tag=u4d-fix-client-scan elapsed=28s bound=1200s status=OK rc=0`, 1608 passed, 4 deselected; 0 new network-attempt nodes.
- Grep: `src/` and `App.tsx` contain none of `QaranIcon`, `M22 22 L27 27`, `x1="14.2"`, `Q-ring`, `Q logo` or `Q-mark`. There are nine `react-native-svg` importers.
- `git diff --stat` shows no whole-file rewrite. The two `.snap` files and `inAppMark.u4c.test.ts` are LF working copies, and their numstat is the same with and without `--ignore-cr-at-eol`.
- Mutants:
  - Every spec mutant is killed on the final tree: M1a, M1b, M2a, M2b, M3a, M3b, M4a, M4a2, M4b, M4c, M5, M8, M9a, M9b, M10, MS1-MS4, MX1-MX3 and MT1-MT4.
  - Seven more adversary mutants are killed: two that pass `size` as a string, a tint spread, a dropped form-state tagline, a restored HistoryScreen 'baseline' claim, the mark wrapped in a plain View, and `BellIcon` dropped from the barrel.
  - Each mutant was applied to a byte copy, run, and restored to a sha-equal file. The full suite and tsc were re-run green after the batch.

## Stated limits and device checks (after the production build: fresh install and after an OTA)

- L1/UR12, the badge at the 1.1 spring overshoot:
  - On the OTA path, iOS decodes the PNG at the 168 px view size, so the overshoot is a brief ~10 % upscale.
  - In simulation it shows only slightly softer edges at x4 zoom, with no halo.
  - The emerald dot's opaque pixels are (0,181,121): 2.53:1 on `#ECFDF5` and 2.51:1 on `#F8F8FA`. The dot is decorative; the letters are 19.9:1.
- Register header: the tagline keeps its 8 pt `marginTop` under the mark. The mark's ink fills its 56 pt box, so the visible gap is tighter than it was under the old text line box. Check it on a device.
- L3 (existing): the 112 pt badge stays centred over the DimensionBars card for as long as the Results screen is open, and it now shows "MYEZ" there. Whether it hides a bar label is a device and product call.
- L4: VoiceOver no longer reads the app name at the top of Register and ForgotPassword, and Arabic users see the Latin mark instead of «ميّز». This is the accepted D1/D3 consequence, the same as on Home and Splash.
- L6: the splash pins use an instrumented reanimated mock, so they prove binding and arguments, not real frame timing. On a device, the mark must never move or fade, and the tagline must fade in after 200 ms.

## Known test gaps (recorded, not fixed here; the gated test files are frozen)

- No test renders Register's email-confirmation state to check accessibility; only the AST check covers it. So jest still passes if an `accessible accessibilityLabel` is added to that header or the tagline is dropped from it. The code in this PR is correct for both.
- A named `tintColor` attribute on an auth-screen `<QarenLogo>` passes jest but fails `tsc` (TS2322), which CI enforces.

## Orchestrator review (session 71)
- Process: Opus spec (measured: the mark reads at 56 pt in the badge with no halo; Login has no brand block, so Register and ForgotPassword get the mark), Opus adversarial spec review (8 corrections: a weak splash pin three post-mount mutants passed was replaced by P1b; the snapshot hazard check moved from git status to git diff), orchestrator rulings UR1-UR14, Opus RED gated PASS (13 reds for the stated reasons, P1b proven against seven mutants in scratch), Opus GREEN (the two authorised snapshot updates landed on the pre-computed shas 57149ef5 / 67dde70b), two Opus adversaries (visual / App Review: own renders of every changed screen incl. RTL and a Pillow composite at the overshoot; engineering: all gates re-run, 35 mutants), both SOUND; the fix round changed nothing and re-measured the 25 mutants the engineering adversary ran out of time for (all killed).
- The orchestrator re-hashed the changed files, read the source diffs and both snapshot diffs (RevealBurst: only the Svg subtree became the Image in two keys; visual-foundation: only the two QaranIcon keys removed), fast-forwarded the branch to main `c1a467c6` (no client file moved) and re-ran the FULL jest suite there (357 passed of 360 suites, 3,485 tests, 42 snapshots) and tsc (clean).
- Known test gaps recorded above (the Register email-confirmation state is not rendered for accessibility; a tintColor attribute on an auth mark is caught by tsc, not jest) and the device checks after the production build are the owner's; the landing favicon 404 is a pre-existing follow-up.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
