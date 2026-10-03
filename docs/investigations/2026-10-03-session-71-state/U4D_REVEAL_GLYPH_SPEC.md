# U4d: the MYEZ mark in the winner reveal, the auth text logos, QaranIcon removed, splash pins (issue #283)

Spec writer: Opus (read and measure only), session 71, 2026-10-03, 11:15 to 11:55 AST.

Evidence folder (scratch only, nothing in the worktree): `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad/u4d/`, called `SC/` below. Running notes: `SC/notes.md`.

Inputs read:
- `s70-common.txt`
- `SC/issue_283.md`
- the U4c spec in full, including its review corrections, UR1 to UR15 and UG1 to UG5
- the merged U4c code and its six test files

Binding inputs, implemented here and not re-opened:
- **D1.** The reveal glyph becomes the MYEZ mark.
- **D2.** Exactly two `.snap` files change, each by one `jest -u`.
- **D3.** The U4c rules apply:
  - no app-name text beside the mark;
  - the mark is hidden from accessibility;
  - no `tintColor`;
  - no `expo-image`;
  - no change to `app.json`, `eas.json`, `package.json` or the lock.
- **O1 to O4.** The orchestrator defaults. O1 needs a ruling, because Login shows no brand at all (section 2e).

Precedence: if a later "review corrections" or "rulings" section is appended, it supersedes this body.

---

## 1. Base

```
$ git -C C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b rev-parse HEAD
0a7446b4400ac12d9ddfab3a031577d95c816f2d
$ git -C …/sc-s70-u4b status --porcelain          (empty, re-checked after every probe: still empty)
$ git -C …/sc-s70-u4b branch --show-current
feature/s71-u4d-reveal-glyph
$ git -C …/sc-s70-u4b log --oneline -2
0a7446b4 Merge pull request #288 from KGRddhs/feature/s71-u4c-inapp-mark
60278405 feat(mobile): the in-app MYEZ mark replaces the old Q-ring (S71 U4c)
```

**Tools** (run from `SmartCompareApp`): jest 29.7.0, tsc 5.9.3, eslint v9.39.4; Pillow 12.3.0 under Python 3.12.9 (pinned venv). `node_modules/@babel/core` and `node_modules/.bin/jest` exist.

`git config core.autocrlf` is `true`. Every file this unit edits is CRLF in the working copy. Measured with `grep -c $'\r$' f` == `wc -l < f` on `RevealBurst.tsx`, `RegisterScreen.tsx`, `ForgotPasswordScreen.tsx`, `index.ts`, `ProfileScreen.tsx`, `HistoryScreen.tsx`, `LoadingRings.tsx` and `inAppMark.u4c.test.ts`. Both `.snap` files are `i/lf w/crlf` (`git ls-files --eol`).

**Baselines at `0a7446b4`:**

- **Base subset** (`SC/jest_base_subset.log`). This is every suite U4d touches or neighbours: the three RevealBurst suites, visual-foundation, the three icons suites, the three Splash suites, the five Register suites, the three AuthScreens suites, appleButton, authErrorCopy, the bundleD contract, brand.hardcoded, the no-missing-referenced-keys, no-deleted-keys and brand.myez fences, inAppMark.u4c, QarenLogo, the two LoadingRings suites, ResultsContent.render, DirectionalIcon and LoginScreen.noopControls.
  - Command: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci <32 paths>`
  - Result: `Test Suites: 32 passed` / `Tests: 8 todo, 352 passed, 360 total` / `Snapshots: 23 passed`, rc 0.
- **FULL suite.** Not run by this writer: the task forbids it. The anchor is UG4, measured by the U4c GREEN on the same tree that merged as `0a7446b4`: `Test Suites: 3 skipped, 354 passed, 354 of 357 total` / `Tests: 13 skipped, 13 todo, 3473 passed, 3499 total` / `Snapshots: 44 passed`.
- **tsc.** `timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit` gives rc 0 and 0 lines (`SC/tsc_base.log`).
- **eslint.** On the 12 files this unit touches (`SC/eslint_base.log`): `0 errors, 8 warnings`.
  - `src/icons/index.ts`: 1 (30:17 array-type)
  - `ForgotPasswordScreen.tsx`: 1 (16:3 unused `ActivityIndicator`)
  - `HistoryScreen.tsx`: 5
  - `ProfileScreen.tsx`: 1
  - Every other file: 0.

---

## 2. Measured facts

### (a) `src/icons/QaranIcon.tsx`, and every reference to it

The file is 49 lines, read in full:
- Its docstring calls it the "Qaran brand mark — Q rendered as a magnifying glass".
- It exports `QaranIcon({ size = 24, color = '#0A0A0B', testID })`, named at :23, and `export default QaranIcon` at :49.
- It draws `<Svg width={size} height={size} viewBox="0 0 24 24" fill="none" testID={testID}>`, containing:
  - a ring: `Circle cx=10 cy=10 r=6 stroke={color}`;
  - a handle: `Line x1="14.2" y1="14.2" x2="20" y2="20"`, stroke `max(1.5, size*2.5/24)`, round cap;
  - a tail dot: `Circle cx=20 cy=20 r={stroke*0.6} fill={color}`. The docstring says this dot "echoes the Q tail".
- It has no accessibility props.
- Its only testID is the `testID` prop, which no caller passes.

`git grep -n QaranIcon -- src App.tsx __tests__ __mocks__` (run from `SmartCompareApp`). The other 14 hits are in `docs/`, which is untouched.

| site | kind | needs |
|---|---|---|
| `src/icons/QaranIcon.tsx` :23, :49 | definition | **delete the file** |
| `src/icons/index.ts:8` `export { QaranIcon } from './QaranIcon';` | barrel re-export | delete the line; also fix the :4 comment "infrastructure + brand mark" |
| `src/components/hero/RevealBurst.tsx:50` import, `:242` `<QaranIcon size={Math.round(BADGE_R * 1.2)} />` | **the only RENDERED use** | replace (R1) |
| `src/components/hero/LoadingRings.tsx:57`, `:209` | comments only | reword (R8) |
| `src/icons/UtilityIcons.tsx:62-63` "similar grammar to QaranIcon … QaranIcon stays an outlined ring as a brand mark" | comment only | reword (R8) |
| `__tests__/icons/QaranIcon.test.tsx` | test: 4 QaranIcon cases (:9-38) + 2 `flipForRTL` cases (:40-48) | delete the file; move the 2 `flipForRTL` cases verbatim to a new `__tests__/icons/flipForRTL.test.tsx` |
| `__tests__/snapshots/visual-foundation.test.tsx:24` (import from the barrel), `:90-92` `it('QaranIcon default')`, `:120-124` `it('QaranIcon emerald 32')` | snapshot test | remove the import line and the two `it`s; the two snapshot keys become obsolete, which section 6 G3 handles |
| `__tests__/snapshots/__snapshots__/visual-foundation.test.tsx.snap:249`, `:327` | 2 keys | removed by G3 |
| `__tests__/hero/__snapshots__/RevealBurst.test.tsx.snap` :143-172, :342-371 | the QaranIcon Svg subtree inside `reveal-burst-badge`, in both keys | rewritten by G3 |
| `__mocks__/*` | none | — |
| the 11 `jest.mock('../src/icons', …)` barrel mocks (`HomeScreen.*` ×10, `aiProcessingConsent.s69`) | they mock only `ScanIcon`, `LinkIcon` and `TypeIcon` (e.g. `HomeScreen.abortOnUnmount.test.tsx:145-149`) | none |
| barrel re-export tests: `ModeIcons.test.tsx:53-60`, `UtilityIcons.test.tsx:61-71` | neither names QaranIcon | none |

Other places that could draw a Q or a magnifier with a tail. `git grep -l "from 'react-native-svg'" -- src App.tsx` gives 10 files. None of the nine others draws a Q:
- `ScannerReticle`: 4 corner `Path`s.
- `LoadingRings`: the rings.
- `PhoneMockup`: frame, cards, a check `Path` (:294), a home-indicator `Rect` and a notch `Circle`. Its docstring :16 claims a "White circular Q-mark", but the code draws none.
- `RevealBurst`: the particles.
- `CohortBullet`: a `Polyline` check.
- `ProductImage`: a `Rect` + `Line` placeholder.
- `ModeIcons`.
- `UtilityIcons`.
- `Step16Account`: a bookmark `Path`.

`UtilityIcons.SearchIcon` is a plain filled magnifier with no tail dot (`d="M10 3.5a6.5 6.5 0 1 0 4.05 11.6l4.42 4.42…"`). It is not a Q, and no screen uses it (`git grep -n "\bSearchIcon\b" -- src App.tsx` hits only `src/icons/`). It keeps its visual-foundation snapshot.

`git grep -nE "14\.2|M22 22 L27 27|x2=\"20\"|cx=\"20\"" -- src` hits only `QaranIcon.tsx` :9, :36-38, :44. After U4d **no Q glyph is drawn in `src/`**, and no other site needs a magnifier, so O2's "plain magnifier" branch is empty.

### (b) RevealBurst (274 lines, read in full)

**The badge** (`Animated.View testID="reveal-burst-badge"`, :230-243):
- Style: `[styles.badge, {width: BADGE_R*2, height: BADGE_R*2, borderRadius: BADGE_R}, badgeStyle]`, so a **112 × 112 pt circle**. `BADGE_R = 56` is at :70.
- `styles.badge` (:265-273): `backgroundColor: colors.accentLight` = **`#ECFDF5`** (`src/theme/index.ts:21`), centred children, an emerald shadow (`shadowColor #10B981`, opacity 0.18, radius 12, offset y 4).
- The badge size does NOT follow the `size` prop; only the particle Svg does (:218).
- It sits in `badgeWrap` (absolute fill, centred, `pointerEvents="none"`, :229, :256-264).

**The glyph** is `<QaranIcon size={Math.round(BADGE_R * 1.2)} />`, which is **67 pt**, colour default **`#0A0A0B`** (snapshot :143-171: `width={67}`, `stroke="#0A0A0B"`, `strokeWidth={6.979166666666667}`). It has no accessibility props, and neither does its wrapper.

**Animations:**
- The glyph has none of its own.
- Its wrapper badge carries `badgeStyle = useAnimatedStyle(() => ({ transform: [{ scale: badgeScale.value }] }))` (:212-214). `badgeScale` starts at `animated ? 0 : 1` (:193) and springs to 1 through `motion.revealBurst.badgeSpring` (:199): 0 → 1.1 → 1.0.
- The particles are separate: `useAnimatedProps` on `AnimatedCircle` (:132-165).

**Mount site:** only `src/components/results/ResultsContent.tsx:461`:
- `<RevealBurst key={comparisonId || 'no-comparison-id'} fireOnce particleCount={6} size={220} />`
- inside `View testID="results-v2-reveal-burst-slot"` (absolute fill over the section, :455-467, style `revealBurstSlot` :787-795);
- gated `!isWeird && winnerRevealed` and `scoring_v2.dimensions.length >= 3`;
- inside the `Animated.View testID="results-scoring-v2"` (`entering={FadeInDown.delay(300).duration(400)}`);
- over `DimensionBars`, i.e. block "4. Dimension bars" of the file header.

The surrounding copy is the verdict section above ("Why this fits you", the verdict and the runner-up card) and the dimension-bar labels under the badge. `ResultsScreen.tsx:103` imports `RevealBurst` but never renders it (`grep -n "RevealBurst\|<Reveal" src/screens/ResultsScreen.tsx` gives only :103).

The badge is never unmounted. A10 notes the burst "is never unmounted", and only the particles fade. So the 112 pt badge and its glyph stay centred over the bars for the life of the screen. That is today's behaviour and U4d does not change it (L3).

### (c) The mark over the badge tint (`SC/badge_measure.py` → `SC/badge_facts.json`, `SC/badge_zoom.py`)

**Cut-out error.** This uses U4c's formula: error = (w − a)·(255 − B), where w is the coverage reconstructed from the over-white composite. Max over all pixels and channels, in levels of 255:

| asset | over `#ECFDF5` (badge) | over `#F8F8FA` (auth screens) | over `#FFFFFF` |
|---|---|---|---|
| `myez-mark.png` (128) | **1.192** | 0.439 | 0.000 |
| `@2x` (256) | **1.192** | 0.439 | 0.000 |
| `@3x` (384) | **1.192** | 0.439 | 0.000 |

The worst pixel is an emerald-dot core pixel `(0,180,120,239)`, the LANCZOS overshoot already noted by U4c. 1.19 levels is below any visible step. U4c recorded the same value (§2b, L7).

**Fit inside the circle.** The ink fills the full height: α≥128 bbox `(15,0,369,384)` at @3x. Its farthest point from the image centre is **0.68005 × size** (α≥128) or 0.68537 × size (α≥1). The largest size whose ink stays 8 pt inside the 56 pt radius is **70.6 pt**; touching the edge is 82.4 pt.

| size (pt) | ink radius (pt) | clearance to the badge edge (pt) | letter height per line (0.4505 × size) |
|---|---|---|---|
| 48 | 32.6 | 23.4 | 21.6 |
| **56 (= BADGE_R)** | 38.1 | **17.9** | 25.2 |
| 60 | 40.8 | 15.2 | 27.0 |
| 64 | 43.5 | 12.5 | 28.8 |
| 67 (today's glyph box) | 45.6 | 10.4 | 30.2 |
| 72 | 49.0 | 7.0 | 32.4 |

The letter height comes from the two black-ink row runs at @3x, `(0,173)` and `(211,384)` (`SC/notes_rows.txt`).

**LOOKED AT.** `SC/badge_sheet_3x_device_px.png` and `SC/badge_sheet_2x_device_px.png` show 48/52/56/60/64/67/72/76 pt inside the 112 pt `#ECFDF5` circle on a white card. They use the @2x and @3x assets at true device pixels, with LANCZOS on the top row and point-sampled bilinear (no prefilter) on the bottom row. `SC/badge_zoom6_56_64.png` magnifies the Z and the dot ×6.

- **The mark is clearly readable at every candidate size, at 2x and at 3x, with both filters.**
- There is no halo or fringe over the tint. Only normal anti-aliasing shows at ×6.
- 72 and 76 crowd the circle's top-left.
- 56 to 64 sit balanced.

**Recommendation: 56 pt (`size={BADGE_R}`).** It has the widest clearance of the balanced sizes. Its letter height of 25.2 pt equals the cap height of the current 36 pt bold text logo on the auth screens (section 2e), so one mark size reads the same in both places. The fallback (a plain check) is NOT triggered: the mark is readable, and the cut-out error is 1.19 levels.

### (d) The two snapshot files

`git ls-files '*.snap'` lists 17 files under `SmartCompareApp`. `find . -name "*.snap" -not -path "./node_modules/*"` also gives 17. Each one has its test file: the orphan loop printed nothing. There are no inline snapshots (U4c review).

**`__tests__/hero/__snapshots__/RevealBurst.test.tsx.snap`** (375 lines):
- It is owned only by `__tests__/hero/RevealBurst.test.tsx`, which has 2 `toMatchSnapshot` and 2 `exports[` keys. Its third case, `fireOnce`, takes no snapshot.
- **Both keys embed the QaranIcon subtree.** The exact change was generated, not guessed. `SC/probe/__tests__/hero/RevealBurst.test.tsx` uses the same describe/it names and the REAL worktree `RevealBurst`, with its `QaranIcon` import mocked to render the REAL `QarenLogo size={56}`. It was run with `--ci=false --roots SC/probe --modulePaths <app>/node_modules`, so it wrote only into scratch.
- `diff -u --strip-trailing-cr` against the committed file is `SC/expected_revealburst_snap.diff`. It has two identical hunks, `@@ -140,36 +140,23 @@` and `@@ -339,36 +326,23 @@`. Each replaces the 30-line `<Svg fill="none" height={67} viewBox="0 0 24 24" width={67}>…</Svg>` with:

```
      <Image
        accessibilityElementsHidden={true}
        fadeDuration={0}
        importantForAccessibility="no-hide-descendants"
        resizeMode="contain"
        source={
          {
            "default": 0,
          }
        }
        style={
          {
            "height": 56,
            "width": 56,
          }
        }
      />
```

- The expected new file is `SC/probe/__tests__/hero/__snapshots__/RevealBurst.test.tsx.snap`: LF, 6,363 bytes, sha256 **`57149ef59c89245c77f5cbd0cd947269fc48f4c8c7f6bba6d5e9a9d67ab9f887`**.
- If another size is ruled (OQ1), re-run the probe with `U4D_MARK_SIZE=<n>`. Only the two `56`s per hunk change.

**`__tests__/snapshots/__snapshots__/visual-foundation.test.tsx.snap`** (17 keys):
- It is owned only by `__tests__/snapshots/visual-foundation.test.tsx`, which has 17 `toMatchSnapshot`.
- Two keys render QaranIcon directly (not through RevealBurst): `Icon snapshots — default 24px black QaranIcon default 1` (:249) and `Icon snapshots — emerald accent at 32px QaranIcon emerald 32 1` (:327).
- The probe `SC/probe/__tests__/snapshots/visual-foundation.test.tsx` is the committed test minus the import and the two `it`s (15 cases). It produced `SC/expected_visualfoundation_snap.diff`: two hunks, `@@ -246,39 +246,6 @@` and `@@ -323,39 +290,6 @@`, with **66 lines removed and 0 added**. The removed lines are exactly the two `exports[...QaranIcon...]` blocks.
- The expected new file is LF, 8,514 bytes, sha256 **`67dde70b6c176bde01467ece1d2cae61db522e36d6d15983ae85a1c62a871b38`**.
- The `colors` key contains `"accentLight": "#ECFDF5"`. That is the theme token, which is unchanged.

**What one `jest -u` per file touches** (jest 29.7.0, read and measured):
- `-u` sets `updateSnapshot: 'all'`.
- On `RevealBurst.test.tsx`, it rewrites the 2 mismatching keys.
- On `visual-foundation.test.tsx`, it removes the 2 unchecked keys (`State.js:175-178` `removeUncheckedKeys`) and leaves the other 15 byte-identical (probe).
- With any path filter, `TestScheduler.js:182-208` also runs `cleanup()` over the WHOLE haste FS and unlinks orphan `.snap` files when `updateSnapshot === 'all'` (U4c correction 8). There are 0 orphans today. U4d deletes `QaranIcon.test.tsx`, which owns no `.snap`, so there are still 0.
- The path patterns `__tests__/hero/RevealBurst.test.tsx` and `__tests__/snapshots/visual-foundation.test.tsx` do not match `components/hero/RevealBurst.test.tsx` or `hero/RevealBurst.animation.test.tsx`. G3 also checks `Test Suites: 1 passed, 1 total` per run.

**Measured hazard 1: obsolete keys fail the run.** Once the two `it`s are removed, and until the authorised `-u`, a `--ci` run of visual-foundation exits **rc 1** even though every test passes. Probe `SC/probe_obsolete` gave:
```
 › 2 snapshots obsolete.
Test Suites: 1 passed, 1 total
Tests:       15 passed, 15 total
Snapshots:   2 obsolete, 15 passed, 15 total
rc=1
```
The cause is `snapshot.failure = !updateAll && (unchecked || unmatched || filesRemoved)` at `TestScheduler.js:203-208`, and `success = !(… || snapshot.failure …)` at :314.

**Measured hazard 2: `--ci` rewrites the file.** The same `--ci` run REWROTE the `.snap` file: CRLF became LF, the content was identical, and the mtime moved. `State.save()` writes whenever `this._uncheckedKeys.size > 0` (`State.js:149-152`), even under `--ci`. In the worktree that is a content-identical rewrite, which `git diff` does not show under autocrlf. The RED and GREEN reports must still show `git diff --exit-code -- '*.snap'` = 0 before G3.

**Other suites:**
- No other `.snap` and no other test embeds or asserts QaranIcon, an Svg inside the badge, the glyph colour or 67 (`git grep -lE "QaranIcon|reveal-burst|#ECFDF5" -- '*.snap'` gives the two files only).
- `__tests__/components/hero/RevealBurst.test.tsx` is unaffected by the swap:
  - `findAllByType('Svg').length > 0` and `svgs[0].props.width === 280` read the particle Svg, which stays.
  - The `reveal-burst-badge` test only checks that the badge exists.
  - Its case name at :33 says "renders the Q-badge at center" (OQ6).
- `hero/RevealBurst.animation.test.tsx` reads only the particles and the badge's flattened `transform`. It is unaffected.

### (e) O1: the three auth screens

| screen | brand block today | background under it | tests that pin it |
|---|---|---|---|
| **Login** (`LoginScreen.tsx`, anatomy docstring :7-18; JSX :375-415) | **none**: a header row (back button or spacer, B9), then `Text styles.title` `t('auth.welcomeBack', {defaultValue:'Welcome back.'})` 32/700, then the subtitle. No `QarenLogo`, no `t('app.name')` (`git grep -n "app\.name\|QarenLogo" -- src/screens/LoginScreen.tsx` is empty) | `colors.bg.primary` #FFFFFF | none (`LoginScreen.noopControls.b9`, `AuthScreens.test` assert other things) |
| **Register** form (`RegisterScreen.tsx:322-326`) | `<View style={styles.header}><Text style={styles.logo}>{t('app.name')}</Text><Text style={styles.subtitle}>{t('splash.tagline')}</Text></View>` | `container` `colors.bg.secondary` **#F8F8FA** (:536-539); the header sits on the container, not in the white `form` card | none asserts the text: `git grep -n "app\.name" -- __tests__` hits no Register suite; the five `RegisterScreen.*` suites mock `t` to return the key |
| **Register** email-confirmation state (`:288-306`, `:291-295`) | the same header (`:293` logo, `:294` tagline) | #F8F8FA | none |
| **ForgotPassword** (`ForgotPasswordScreen.tsx:85-88`) | `<View style={styles.header}><Text style={styles.logo}>{t('app.name')}</Text></View>` | `colors.bg.secondary` #F8F8FA (:142-145) | no suite renders this screen; `Screens.bundleD.contract.test.ts:259-283` reads its source only, for `requestPasswordReset` and the Login navigation |

The two `styles.logo` styles are the same: `{ fontSize: 36, fontWeight: '700', color: colors.text.primary }` (Register :556-560, ForgotPassword :156-160). `styles.header` is `{ alignItems: 'center', marginBottom: spacing['2xl'] }` (32 pt) in both. `content` is `justifyContent: 'center'`.

The design reference `docs/claude-design-handoff/ui_kits/mobile/AuthScreens.jsx` has `QarenSignInScreen` and `QarenSaveAdvisorScreen` and no logo. It has no Register or ForgotPassword design.

**O1's premise does not hold:** Login shows neither the mark nor a text logo. The recommendation is **R-a** (OQ2): one rule for all three screens, "**no auth screen draws the app name as a text logo; where a screen has a brand block, it is `<QarenLogo size={56} />`**".
- Register (both states) and ForgotPassword swap the `Text` for the mark.
- Register keeps the tagline under the mark, 8 pt below (`subtitle.marginTop: spacing.sm`).
- Login stays unchanged, because it has no brand block.
- At 56 pt the mark's letters are 25.2 pt tall, about the cap height of today's 36 pt bold text. The block grows from one 36 pt text line (its line box is unmeasured; about 43 pt at RN's default) to 56 pt. Because `content` is `justifyContent: 'center'`, the card moves down by about half the growth, roughly 6 pt (device check).
- Over #F8F8FA the cut-out error is 0.439 levels.

What replacing the text breaks (measured):
- **The i18n fences:** nothing.
  - `app.name` stays referenced by `App.tsx:140` (`tabBarLabel`), `ReferralLandingScreen.tsx:174` and `Step17Notifications.tsx:90`.
  - `splash.tagline` stays referenced by Register and Splash.
  - There is no catalog change, so `no-missing-referenced-keys` and `no-deleted-keys` are unaffected. There is no unused-key fence: `ls __tests__/i18n` lists none.
- **`brand.hardcoded.s69`:** nothing. It adds no string literal, and the `require` and import specifiers are skipped.
- **`Screens.bundleD.contract`:** nothing. Its regexes for Register (:232-253) and ForgotPassword (:259-283) do not mention the logo.
- **`inAppMark.u4c.test.ts` B8 and B9 GO RED (section 2h).**
- **Accessibility:** VoiceOver no longer announces "MYEZ" at the top of these screens, because the mark is hidden. Arabic users lose the «ميّز» text there. This matches D1/D3 for Home and Splash.

### (f) O3: what the U4c splash tests pin, and the new pins

`SplashScreen.tsx` (146 lines, read in full):
- The mark is a plain `View testID="splash-mark"` with the style `{position, left: markLeft, top, width, height}`, wrapping `<QarenLogo size={mark.size} />` (:109-121).
- The tagline is `<Animated.Text style={[styles.tagline, { top: mark.top + mark.size + spacing.lg }, taglineStyle]}>` (:122-126).
  - `styles.tagline` is `{position:'absolute', left:0, right:0, textAlign:'center', ...typography.body, color: colors.text.secondary}` (:138-145).
  - `taglineStyle = useAnimatedStyle(() => ({ opacity: taglineOpacity.value }))` (:86-88).
  - The effect sets `taglineOpacity.value = withDelay(200, withTiming(1, { duration: 400 }))` (:60-64).

What `SplashScreen.mark.u4c.test.tsx` pins:

| pinned | not pinned |
|---|---|
| C1/C6: the first render's wrapper style = exactly the 5 keys (390×844, LTR and RTL) | anything after the first render |
| C3: on the first render, no host from the mark to the root has opacity ≠ 1, a `transform`, or `entering`/`exiting`/`layout` | an animated style whose value is 1 at mount (allowed by `!== 1`); `animatedProps`; values that change after mount |
| C5: the tagline renders with opacity 0 on the first render | the tagline `top`, position, edges, type and colour; the delay 200 and duration 400; that the tagline is the ONLY animation |

**Mock fact.** The repo mock's `useSharedValue(init)` returns a FRESH `{value: init}` on every render (`__mocks__/react-native-reanimated.ts:16-18`). Values set after mount are therefore invisible after a re-render. The first prototype measured this: tagline opacity stayed 0 after `advanceTimersByTime(700)`.

**The pins** are a new file, `__tests__/SplashScreen.motion.u4d.test.tsx`. It uses a file-local `jest.mock('react-native-reanimated', factory)` that wraps the repo mock (`jest.requireActual('../__mocks__/react-native-reanimated')`) and adds:
- `__esModule: true` and `default: base.default`. The spread drops TS's non-enumerable `__esModule`, so it has to be set explicitly.
- `useSharedValue` made stable through `React.useRef({value}).current`.
- `useAnimatedStyle` recording every returned object in a `Set` exported as `__animatedStyles`.
- `withTiming`, `withDelay`, `withSpring`, `withRepeat` and `withSequence` wrapped in `jest.fn`.

The working prototype with absolute paths is `SC/probe_o3/__tests__/SplashScreen.motion.u4d.test.tsx`.

| id | renders | asserts |
|---|---|---|
| P1 | `<SplashScreen onFinish={fn} />`; then `act(advanceTimersByTime(700))`; `rerender(… ready)`; `act(advanceTimersByTime(1000))` | at each of the 4 moments, every host from the one `Image` to the root has: no style object in `__animatedStyles`, no `opacity` key, no `transform`, no `entering`/`exiting`/`layout`/`animatedProps`. The `splash-mark` flattened style equals the C1 rect (±0.01) |
| P2 | first render | `withDelay.mock.calls` = `[[200, 1]]`, `withTiming.mock.calls` = `[[1, {duration: 400}]]`; `withSpring`, `withRepeat` and `withSequence` are never called |
| P3 | first render, then `advanceTimersByTime(700)` | the tagline's flattened key set is exactly `color, fontSize, fontWeight, left, lineHeight, opacity, position, right, textAlign, top`, with values `absolute, 0, 0, 'center', 16, '400', 24, '#6B7280'`, top ≈ **504.803** (= 358.000 + 126.803 + 20, ±0.01) and opacity 0. After the re-render the opacity is 1, which shows the timing is bound to the tagline |
| P4 | `I18nManager.isRTL = true` (restored in `afterEach`) | the tagline has left 0, right 0, top ≈ 504.803, and no `start`/`end` |

**Measured** (`SC/run_splash_mutants.sh` → `SC/splash_mutants.log`, against a scratch copy of the worktree SplashScreen and 8 scratch mutants):
- The scratch copy is `SC/splash_mutants/BASE.tsx`. The mutants come from `SC/make_splash_mutants.py`.
- **P1 to P4 pass at base (4 passed, rc 0) and kill all 8 mutants.**
- A redirected copy of the U4c suite (`SC/probe_u4c/`) passes at base (6 passed) and kills only MS3.

| mutant | P1–P4 (new) | U4c C1–C6 |
|---|---|---|
| MS1 a new `Animated.View` around `splash-mark`, opacity 1 → 0.4 after mount | P1 + P2 fail | passes (gap) |
| MS2 an animated style attached with a constant opacity of 1 | P1 fails | passes (gap) |
| MS3 the container scales 1 → 1.05 after mount | P1 + P2 fail | C3 fails |
| MS4 `top` bound to a shared value that starts at `mark.top` and slides to 300 | P1 + P2 fail | passes (gap) |
| MT1 tagline `withDelay(300…)` | P2 fails | passes |
| MT2 tagline `duration: 300` | P2 fails | passes |
| MT3 tagline top uses `spacing.base` (16) | P3 + P4 fail | passes |
| MT4 tagline `start: 0, end: 0` | P3 + P4 fail | passes |

### (g) O4 and O2: stale comments (all comment-only; corrected wording is binding in R8)

| file:line (symbol) | today | corrected |
|---|---|---|
| `LoadingRings.tsx:57-62` (the comment above `import QarenLogo`) | "swap center from QaranIcon (magnifier mark, …) to QarenLogo (brand Q-ring with emerald accent dot) …" | `// The centre is the brand mark, QarenLogo (the MYEZ mark: the MY/EZ`<br>`// wordmark with the emerald dot, a bundled PNG since U4c), per design doc`<br>`// § 3.2 LoadingRings. An earlier magnifier glyph read as a heavy black`<br>`// blob at this size and was retired (F-S2.W3.hotfix, task #37).` |
| `LoadingRings.tsx:207-211` (the JSX comment in `loading-rings-logo`) | "… Was QaranIcon at 0.4 (96px stroke ~10px) which read as a heavy magnifier blob. The QarenLogo Q-ring stays light + ships the brand mark." | `{/* The MYEZ mark (QarenLogo) at 0.22 of the rings size: visually`<br>`    centred against the 3-ring stack without bleeding into the`<br>`    inner ring's r=60 footprint. */}` |
| `ProfileScreen.tsx:6` (file docstring) | `1. ProfileHeaderRow  — Q logo + name + dynamic "Capital · GCC" subtitle` | `… — MYEZ mark + name + dynamic "Capital · GCC" subtitle` |
| `ProfileScreen.tsx:428` (JSX comment above `<ProfileHeaderRow />`) | `{/* 1. Header — Q logo + name + region + settings icon */}` | `{/* 1. Header — MYEZ mark + name + region + settings icon */}` |
| `HistoryScreen.tsx:938` (the `header` JSX) | `brand glyph leading the screen title.` | `the MYEZ mark (QarenLogo) leading the screen title.` |
| `HistoryScreen.tsx:1029-1032` (the comment on `styles.header`) | it claims `` `alignItems: 'baseline'` so the QarenLogo glyph base-aligns …``; **the code at :1035 is `alignItems: 'center'`** | `// Bundle D Claude-Design (option small, Task 2.F.2 screen 4): the MYEZ`<br>`// mark (QarenLogo, an image) and the display-type title are centre-`<br>`// aligned in the header row (alignItems: 'center').` |
| `HistoryScreen.tsx:1044` (the comment on `headerTitleSpaced`) | `RTL-safe spacer between the QarenLogo glyph` | `RTL-safe spacer between the MYEZ mark (QarenLogo)` |
| `UtilityIcons.tsx:62-63` (the comment above `SearchIcon`) | "similar grammar to QaranIcon but heavier; QaranIcon stays an outlined ring as a brand mark" | `// ── SearchIcon ── chunky filled magnifier (a plain search glyph, not a`<br>`// brand mark).` |
| `icons/index.ts:4` | `Phase 1 (this commit): infrastructure + brand mark.` | ` * Phase 1: infrastructure. The brand mark is QarenLogo`<br>` * (src/components/QarenLogo.tsx), not an icon.` |
| `PhoneMockup.tsx:16` (OQ5) | `- White circular Q-mark on the home indicator area` (the code draws no mark) | ` *   - Home-indicator bar and camera-notch dot on the bezel (no brand mark)` |
| `RevealBurst.tsx:10-11` (file docstring) | "Center holds a scale-bounce badge …" | add: `The badge carries the MYEZ mark (QarenLogo, U4d).` |

`Step01Welcome.tsx:6` ("the prior Phase 2 anatomy (96px black Q-badge …)") describes history accurately, so it is kept.

### (h) jest environment for an Image in RevealBurst, and every other suite the unit breaks

- **The PNG stub.** `jest.config.js:77` maps `\.(ttf|otf|woff2?|png|jpg)$` to `__mocks__/fileStub.ts` (`export default 0`), so `source` serialises as `{"default": 0}` (probe, section 2d).
- **The RN mock.** `Image = ({source, ...props}) => createElement('Image', {...props, source})` (`__mocks__/react-native.ts:16-17`) gives the host type `'Image'`.
- **The reanimated mock.** `Animated.View` is the RN `View` host (`__mocks__/react-native-reanimated.ts:9`), so the badge stays a host `View` with its style array. `useAnimatedStyle` evaluates once per render.
- **No RevealBurst suite mocks `react-native` or reanimated locally.** The three RevealBurst suites use the global mocks (`grep jest.mock` on them gives nothing).
- **Results suites.** 12 suites `jest.mock` `RevealBurst` itself (to `() => null` or a View), so they are unaffected. 4 suites render ResultsScreen without mocking it (`ResultsScreen.historyFloor.a17`, `.usageFetch.a15`, `honestLoaders.u6`, `camera.engineUnavailable.s69`). None asserts an Image count (`grep -n "Image\b\|findAllByType"` gives only an error string). `QarenLogo` and its PNG `require` are already loaded on that path through `LoadingRings` (U4c).
- **`inAppMark.u4c.test.ts` B8 and B9 break, and that is EXPECTED.**
  - B8 (`:395-401`) pins `SITE_FILES` (`:101-108`) to exactly six importers of QarenLogo.
  - B9 (`:403-428`) pins the size map of every `<QarenLogo>`.
  - U4d adds `components/hero/RevealBurst.tsx` (`expression:BADGE_R`), `screens/RegisterScreen.tsx` (`numeric:56` ×2) and `screens/ForgotPasswordScreen.tsx` (`numeric:56`).
  - These are edited in RED (section 5).
  - B10 stays green. Register's mark has only the `t('splash.tagline')` sibling, and the B10 scan checks `t('app.name')` siblings.
  - B11 and B12 stay green.
- **`QarenLogo.test.tsx`, `SplashScreen.mark.u4c`, `Step01Welcome` and `LoadingRings`** are unchanged.
- **tsc type-checks tests**: `tsconfig` has no `include` (U4c §2f). Any test still importing `QaranIcon` after the deletion is a TS2307. G5 catches it.

### (i) Bundling

- **No new asset.** RevealBurst and the auth screens render `QarenLogo`, which already `require`s `assets/brand/myez-mark.png` (`QarenLogo.tsx:22`).
- The assets on disk are unchanged: sha256 `dc77ee4c…`, `5b00db3a…` and `61091aa4…`, equal to U4c §2h.
- U4c's G11 proved all three scales ship in both the embedded bundle and `expo export`.
- **No native dependency.** `package.json` is untouched.
- **`react-native-svg` stays.** Nine `src` files still import it after QaranIcon.tsx goes: ScannerReticle, LoadingRings, PhoneMockup, RevealBurst (particles), CohortBullet, ProductImage, ModeIcons, UtilityIcons and Step16Account. `package.json:56` and `:76` keep it.
- **OTA-capable**, and it must be in the store binary (the reviewer sees the embedded JS).

---

## 3. Requirements

- **R1. The reveal glyph is the mark.** `RevealBurst.tsx`:
  - remove `import { QaranIcon } from '../../icons/QaranIcon';` (:50);
  - add `import QarenLogo from '../QarenLogo';`;
  - replace :242 with `<QarenLogo size={BADGE_R} />` (56 pt; OQ1).
  - No wrapper, no extra prop, no `tintColor`, no own `Image`, no `react-native-svg` element inside the badge.
  - The badge (`reveal-burst-badge`: 112 × 112, radius 56, `#ECFDF5`, shadow, `badgeStyle`), the particles, `badgeWrap`, the props and every constant other than the import stay byte-unchanged.
- **R2. Accessibility and appearance come from QarenLogo.**
  - The Image is hidden: `accessibilityElementsHidden` and `importantForAccessibility="no-hide-descendants"`.
  - No `accessibilityLabel` and no `accessible` on it or on any host up to the RevealBurst root.
  - `resizeMode="contain"`, `fadeDuration={0}`, no `tintColor`.
  - `QarenLogo.tsx` itself is NOT changed.
- **R3. O2: QaranIcon is gone.**
  - Delete `src/icons/QaranIcon.tsx` and the line `export { QaranIcon } from './QaranIcon';` (`index.ts:8`).
  - No file in `src/` or `App.tsx` contains `QaranIcon`, `x1="14.2"` or `M22 22 L27 27` (comments included).
  - The barrel keeps every other export: Back, Close, Search, Bell, Settings, Plus, Scan, Link, Type and `flipForRTL`.
- **R4. O1 (as R-a; OQ2).**
  - In `RegisterScreen.tsx`, replace `<Text style={styles.logo}>{t('app.name')}</Text>` at BOTH :293 and :324 with `<QarenLogo size={56} />`. Keep the `<Text style={styles.subtitle}>{t('splash.tagline')}</Text>` sibling.
  - In `ForgotPasswordScreen.tsx:87`, make the same replacement.
  - Each file imports `QarenLogo from '../components/QarenLogo'` and drops its then-unused `logo` style.
  - `t('app.name')` is called 0 times in both files.
  - `LoginScreen.tsx` is unchanged.
  - No i18n catalog change.
- **R5. D3 at the new sites.**
  - No app-name text is a sibling of any `<QarenLogo>`; U4c B10 enforces this.
  - No `color` or `tintColor` attribute and no spread on any `<QarenLogo>`; U4c B12 enforces this.
  - No `expo-image`.
- **R6. O3: the splash is pinned, not changed.**
  - `SplashScreen.tsx` stays byte-unchanged.
  - The new file of section 5 (P1 to P4) passes at base and after.
- **R7. Snapshots.** Exactly two `.snap` files change, each by ONE `jest --ci -u` on its own test file (G3). Their new content equals the section 2d expected files:
  - `57149ef5…` for RevealBurst at 56 pt;
  - `67dde70b…` for visual-foundation.
- **R8. O4 comments** are reworded exactly as in section 2g. They are comment-only edits, through the Edit tool, with CRLF preserved. A whole-file diff in `git diff --stat` is a defect.
- **R9. Untouched:**
  - `app.json`, `eas.json`, `package.json`, `package-lock.json`, `App.tsx`;
  - `assets/**`, `scripts/**`, `docs/brand/**`;
  - `src/i18n/*`, `__mocks__/*`, `jest.config.js`, `metro.config.js`, `babel.config.js`;
  - `src/components/QarenLogo.tsx`, `src/utils/splashMarkLayout.ts`, `src/screens/SplashScreen.tsx`, `LoginScreen.tsx`, `HomeScreen.tsx`, `Step01Welcome.tsx`, `ResultsContent.tsx`, `ResultsScreen.tsx`;
  - every `.snap` except the two in R7.
  - `react-native-svg` stays a dependency.

## 4. Files

**GREEN touches (src):**
- `src/components/hero/RevealBurst.tsx` (R1, docstring)
- `src/icons/QaranIcon.tsx` (DELETED)
- `src/icons/index.ts` (one line removed; :4 comment)
- `src/icons/UtilityIcons.tsx` (comment)
- `src/screens/RegisterScreen.tsx` (R4)
- `src/screens/ForgotPasswordScreen.tsx` (R4)
- `src/components/hero/LoadingRings.tsx`, `src/screens/ProfileScreen.tsx` and `src/screens/HistoryScreen.tsx` (comments)
- `src/components/hero/PhoneMockup.tsx` (comment, if OQ5 is ruled yes)
- through G3 only: `__tests__/hero/__snapshots__/RevealBurst.test.tsx.snap` and `__tests__/snapshots/__snapshots__/visual-foundation.test.tsx.snap`

**RED touches (tests only):**
- new `__tests__/brand/revealGlyph.u4d.test.tsx`
- new `__tests__/screens/authBrandMark.u4d.test.tsx`
- new `__tests__/SplashScreen.motion.u4d.test.tsx`
- new `__tests__/icons/flipForRTL.test.tsx` (the 2 cases moved verbatim)
- DELETE `__tests__/icons/QaranIcon.test.tsx`
- edit `__tests__/snapshots/visual-foundation.test.tsx` (remove the `QaranIcon,` import line and the two `it`s, nothing else)
- edit `__tests__/brand/inAppMark.u4c.test.ts`:
  - `SITE_FILES` gains `components/hero/RevealBurst.tsx`, `screens/ForgotPasswordScreen.tsx` and `screens/RegisterScreen.tsx`, keeping the list sorted; "six" becomes "nine" in the B8 name and comments;
  - the B9 expected map gains `'components/hero/RevealBurst.tsx': ['expression:BADGE_R']`, `'screens/ForgotPasswordScreen.tsx': ['numeric:56']` and `'screens/RegisterScreen.tsx': ['numeric:56', 'numeric:56']`, and its name lists them;
- optional (OQ6): rename the case name only at `__tests__/components/hero/RevealBurst.test.tsx:33`.

**MUST NOT change:** everything in R9, plus `__tests__/SplashScreen.mark.u4c.test.tsx`, `__tests__/components/QarenLogo.test.tsx`, `__tests__/hero/RevealBurst.test.tsx`, `__tests__/hero/RevealBurst.animation.test.tsx`, the 11 barrel-mocking suites and `.github/*`.

## 5. Tests

**Helpers:**
- Find the mark as the host with `n.type === 'Image'` (U4c correction 2: the a11y helper finds Svgs too).
- Flatten styles deeply (the repo mock flattens one level).
- Use AST through the installed `typescript`, as `inAppMark.u4c` does.
- Never import a module this unit deletes, and never `require` a missing file at file top (UR14).
- `require('../../src/icons')` goes inside the `it`.
- `t` is mocked to return the key in the auth file, following the `RegisterScreen.emailConfirmation.m18.test.tsx:20-43` pattern of `jest.mock` for authService, api and expo-screen-capture.

**RED** (each fails at base for the stated reason):

| id | file | asserts | why red at base |
|---|---|---|---|
| R1 | revealGlyph.u4d | `<RevealBurst />`: inside `reveal-burst-badge` exactly 1 host `Image` and 0 hosts of type `Svg`/`Circle`/`Line`/`Path`/`G` | Svg + 2 Circle + Line, 0 Image |
| R2 | 〃 | that Image's flattened style toEqual `{width: 56, height: 56}` for `<RevealBurst />` AND `<RevealBurst size={220} />` (the Results mount) | no Image |
| R3 | 〃 | that Image has `accessibilityElementsHidden === true`, `importantForAccessibility === 'no-hide-descendants'`, `resizeMode === 'contain'` and `fadeDuration === 0`; no `tintColor` in props or in the flattened style; no host from the Image to the root has `accessibilityLabel` or `accessible === true`; `source` toBe `require('../../assets/brand/myez-mark.png')` (sanity only: every PNG maps to the same stub) | no Image |
| R5 | 〃 [AST] | `RevealBurst.tsx` has a default import `QarenLogo` from `'../QarenLogo'`; no module specifier containing `icons`; exactly 1 `<QarenLogo>` JSX whose attributes are exactly `size` (no spread); the only JSX child of the element with `testID="reveal-burst-badge"` is that `<QarenLogo>` | imports `../../icons/QaranIcon`, 0 QarenLogo |
| R6 | 〃 [O2] | `fs.existsSync(src/icons/QaranIcon.tsx) === false`, and `'QaranIcon' in require('../../src/icons') === false` | the file exists and is exported |
| R8 | 〃 [source] | no file under `src/` (recursive `.ts`/`.tsx`) or `App.tsx` contains `QaranIcon`, `x1="14.2"` or `M22 22 L27 27` (raw text) | 5 files contain `QaranIcon` |
| R9 | 〃 [O4] | no `src` file contains `Q-ring`, `Q logo` or `Q-mark` (drop `Q-mark` if OQ5 is no); `HistoryScreen.tsx` does not contain ``` `alignItems: 'baseline'` ``` | LoadingRings (2), ProfileScreen (2), PhoneMockup (1), HistoryScreen |
| A1 | authBrandMark.u4d | render Register (form): exactly 1 host Image, hidden (the R3 a11y props), 56 × 56, no tint; `queryByText('app.name')` null; `getByText('splash.tagline')` present | Text logo, 0 Image |
| A2 | 〃 [AST] | `RegisterScreen.tsx`: 0 `t('app.name')` calls; exactly 2 `<QarenLogo>` with `size={56}` (numeric literal), each a child of a JSX element whose `style` is `styles.header`; no `logo` property in the `StyleSheet.create` object | 2 calls, 0 QarenLogo, `logo` present |
| A3 | 〃 | render ForgotPassword: 1 hidden 56 × 56 Image; `queryByText('app.name')` null; `getAllByText('auth.resetPassword').length >= 1` | Text logo |
| A4 | 〃 [AST] | `ForgotPasswordScreen.tsx`: 0 `t('app.name')`; exactly 1 `<QarenLogo size={56} />` inside `styles.header`; no `logo` style; default import from `'../components/QarenLogo'` | 1 call, 0 QarenLogo |
| B8′ | inAppMark.u4c (edited) | the nine importers | six importers |
| B9′ | 〃 (edited) | the size map with the three new entries | entries missing |

**PIN** (green at base and after):

| id | file | asserts |
|---|---|---|
| R4 | revealGlyph.u4d | the badge's flattened style has `backgroundColor '#ECFDF5'`, `width 112`, `height 112` and `borderRadius 56` |
| R7 | 〃 | the barrel still exports `BackIcon`, `CloseIcon`, `SearchIcon`, `BellIcon`, `SettingsIcon`, `PlusIcon`, `ScanIcon`, `LinkIcon`, `TypeIcon` and `flipForRTL` (each defined) |
| A5 | authBrandMark.u4d [AST] | `LoginScreen.tsx` has 0 `<QarenLogo>` and 0 `t('app.name')` (Login unchanged under R-a) |
| P1–P4 | SplashScreen.motion.u4d | section 2f (prototype green at base, kills 8 mutants) |
| F1, F2 | icons/flipForRTL | the two moved cases, verbatim |

The neighbours stay green unchanged: the U4c suites, the RevealBurst animation and structure suites, visual-foundation's 15 cases, the Register, Auth and bundleD suites, brand.hardcoded and the i18n fences.

**Counts.**
- **New `it`s:** 18 (R1–R9, i.e. 9; A1–A5, i.e. 5; P1–P4, i.e. 4), plus 2 moved (F1, F2).
- **Removed:** 6 (`QaranIcon.test.tsx`) and 2 (visual-foundation).
- **RED at base:** 13 (R1, R2, R3, R5, R6, R8, R9, A1, A2, A3, A4, B8′, B9′).
- If the RED agent splits an id into several `it`s, the RED report restates the totals.

**RED-state full suite** (before GREEN):
- `Tests: 13 failed, 13 skipped, 13 todo, 3472 passed, 3511 total`
- `Snapshots: 2 obsolete, 42 passed`
- rc 1. The obsolete keys alone force rc 1 (section 2d).
- Suites: 357 + 3 skipped = 360 total, failing suites = revealGlyph, authBrandMark and inAppMark.u4c.
- Check after every RED run: `git diff --exit-code -- '*.snap'` = 0. A content-identical LF rewrite of the visual-foundation `.snap` is expected (section 2d hazard 2).

**Mutants** the tests must kill. Each is applied to the GREEN tree; run the named files; restore from a byte copy (Python `shutil.copyfile`) and compare sha256. Never `git checkout --`.

| # | mutant | killed by |
|---|---|---|
| M1 | the reveal still draws an Svg Q: RevealBurst keeps `<QaranIcon>` (file restored), or inlines `<Svg><Circle/><Line/></Svg>` in the badge | R1, R5, R8, snapshot |
| M2 | the mark gets a `tintColor` (`<Image … tintColor="#0A0A0B">` in RevealBurst, or on QarenLogo) | R3 (+ U4c A6 if on QarenLogo), snapshot |
| M3a | the mark is not hidden: RevealBurst renders its own `<Image source={require('../../../assets/brand/myez-mark.png')} style={…}/>` without the hidden props | R3, R5, snapshot |
| M3b | the mark is wrongly labelled: `<View accessible accessibilityLabel={t('app.name')}>` around it | R3 |
| M4a | a text logo is left on Register (either site) | A1 or A2, B9′ |
| M4b | a text logo is left on ForgotPassword | A3, A4, B9′ |
| M4c | the mark is added but `t('app.name')` is kept beside it | A2/A4, U4c B10 |
| M5 | QaranIcon is still exported: the file and the barrel line are kept, RevealBurst is fixed | R6, R8 |
| M6 | the splash mark gets a post-mount opacity animation (MS1) | P1, P2 |
| M7 | the tagline delay (MT1), duration (MT2), offset (MT3) or edges (MT4) change | P2 / P3 / P4 |
| M8 | the old glyph box size: `<QarenLogo size={Math.round(BADGE_R * 1.2)} />` (67) | R2, B9′, snapshot |
| M9 | the auth mark at the wrong size (`size={64}`) | A1, A3, A2/A4, B9′ |
| M10 | a stale comment is left (LoadingRings "Q-ring") | R9 |
| M11 | an animated style attached to the splash mark with a constant value (MS2), or a post-mount `top` slide (MS4) | P1 |

## 6. GREEN gates

Run them cheapest first and print the versions first. Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b`; the app is `…/SmartCompareApp`.

- **G0.**
  - `git rev-parse HEAD`;
  - `git status --porcelain`;
  - `ls node_modules/@babel/core/package.json node_modules/.bin/jest`;
  - the jest, tsc and eslint versions.
- **G1. Unit files.**
  - Command: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/brand/revealGlyph.u4d.test.tsx __tests__/screens/authBrandMark.u4d.test.tsx __tests__/SplashScreen.motion.u4d.test.tsx __tests__/icons/flipForRTL.test.tsx __tests__/brand/inAppMark.u4c.test.ts __tests__/components/hero/RevealBurst.test.tsx __tests__/hero/RevealBurst.animation.test.tsx __tests__/SplashScreen.mark.u4c.test.tsx __tests__/SplashScreen.test.tsx __tests__/components/QarenLogo.test.tsx __tests__/RegisterScreen.emailConfirmation.m18.test.tsx __tests__/RegisterScreen.consent.w3-16.test.tsx __tests__/Screens.bundleD.contract.test.ts __tests__/brand.hardcoded.s69.test.ts __tests__/i18n/no-missing-referenced-keys.test.ts __tests__/icons/ModeIcons.test.tsx __tests__/icons/UtilityIcons.test.tsx`
  - Expect: all pass.
  - The two snapshot owners are NOT in G1. Before G3 they fail only on the expected snapshots (RevealBurst: 2 `toMatchSnapshot` mismatches; visual-foundation: 2 obsolete, rc 1).
- **G2. tsc.** `timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit` gives no output and rc 0.
- **G3. The two authorised snapshot updates (D2).** Run once, after the implementation is final.
  0. List every `.snap` under `SmartCompareApp` (excluding `node_modules`) and check that each has its test file (`<dir>/../<name without .snap>`). If any orphan exists, STOP.
  1. Byte-copy both `.snap` files to scratch with `shutil.copyfile`, and record their sha256.
  2. Run `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci -u __tests__/hero/RevealBurst.test.tsx`. Expect `Test Suites: 1 passed, 1 total`, `Tests: 3 passed`, `Snapshots: 2 updated, 2 total`. The sha256 of the new `.snap` MUST be `57149ef59c89245c77f5cbd0cd947269fc48f4c8c7f6bba6d5e9a9d67ab9f887`, or the sha of the OQ1 re-probe for the ruled size.
  3. Run `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci -u __tests__/snapshots/visual-foundation.test.tsx`. Expect `Test Suites: 1 passed, 1 total`, `Tests: 15 passed`, `Snapshots: 2 removed, 15 passed`. The sha256 MUST be `67dde70b6c176bde01467ece1d2cae61db522e36d6d15983ae85a1c62a871b38`.
  4. Any sha mismatch is a STOP. Do not run a second `-u`; report the diff.
  5. `git status --porcelain -- '*.snap'` must show exactly two ` M` lines, for those two files. `git diff --stat -- '*.snap'` must show 2 files.
  6. Paste both `git diff -- <snap>` into the report. Hunk for hunk they must equal `SC/expected_revealburst_snap.diff` and `SC/expected_visualfoundation_snap.diff` (2 hunks each; RevealBurst 30 lines out and 17 in per hunk; visual-foundation 66 out and 0 in).
  7. Re-run both files with `--ci`: `Snapshots: 2 passed` and `15 passed`, 0 obsolete, rc 0.
- **G4. FULL jest.** `timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci` must give 0 failed, rc 0, and:
  - `Test Suites: 3 skipped, 357 passed, 357 of 360 total`. This is base 354 − 1 (`QaranIcon.test`) + 4 new.
  - `Tests: 13 skipped, 13 todo, 3485 passed, 3511 total`. This is base 3473 − 6 + 2 − 2 + 18 = 3485, and base 3499 − 6 + 2 − 2 + 18 = 3511.
  - `Snapshots: 42 passed, 42 total` (44 − 2).
  - If RED restated the count, use its totals.
  - Re-run the known flake `HistoryScreen.mobileJank.m21` once, alone (RQ11).
- **G5. eslint** on `git diff --name-only --relative` (run inside SmartCompareApp; `.ts`/`.tsx`, without the deleted file) and the new test files:
  - 0 errors;
  - warnings ≤ base per file: `index.ts` 1, ForgotPassword 1 (the pre-existing unused `ActivityIndicator`; do not fix it here), HistoryScreen 5, ProfileScreen 1;
  - every other file 0.
- **G6. No Q glyph (grep).** From the repo root:
  - `git grep -nE "QaranIcon|M22 22 L27 27|x1=\"14\.2\"" -- SmartCompareApp/src SmartCompareApp/App.tsx` gives no output (rc 1).
  - `git grep -nE "Q-ring|Q logo" -- SmartCompareApp/src` gives no output.
  - `test ! -e SmartCompareApp/src/icons/QaranIcon.tsx`.
  - `git grep -l "from 'react-native-svg'" -- SmartCompareApp/src | wc -l` gives 9.
- **G7. Untouched.**
  - `git diff --exit-code -- SmartCompareApp/app.json SmartCompareApp/eas.json SmartCompareApp/package.json SmartCompareApp/package-lock.json SmartCompareApp/App.tsx SmartCompareApp/assets SmartCompareApp/src/i18n SmartCompareApp/__mocks__ SmartCompareApp/jest.config.js SmartCompareApp/src/components/QarenLogo.tsx SmartCompareApp/src/screens/SplashScreen.tsx SmartCompareApp/src/screens/LoginScreen.tsx scripts docs/brand` exits 0.
  - `git diff --stat` lists exactly the section 4 touch list (D = `QaranIcon.tsx`, `QaranIcon.test.tsx`).
  - No whole-file rewrite of a CRLF file.
  - The two `.snap` diffs are content-only.

## 7. Risks and stated limits

- **L1 (device only).** On a 2x and a 3x iPhone, check:
  - the badge mark's sharpness during the spring overshoot (scale 1.1 → 61.6 pt → 185 device px from the 384 px asset: a downscale, fine in emulation);
  - that the dot reads against the light tint. The emerald `#10B981` on `#ECFDF5` has a WCAG contrast ratio of 2.41:1; it is decorative, and the letters are black on the tint at 18.79:1 (computed with the venv one-liner in `SC/notes.md`).
- **L2.** Like every RN Image, the PNG decodes asynchronously (U4c correction 7). Here the badge starts at scale 0 and springs, so a one-frame decode delay is hidden behind the spring start. That is expected, and unmeasurable in jest.
- **L3 (existing, unchanged).** The 112 pt badge stays centred over the DimensionBars card for the life of the Results screen, and only the particles fade (A10). With the new mark, a "MYEZ" badge sits permanently over the bars. Device-check whether it hides a bar label; a change would be a separate product call.
- **L4.** On Register and ForgotPassword, VoiceOver no longer reads the app name, and Arabic users see the Latin mark instead of «ميّز» (D1/D3 consequence, same as Home and Splash).
- **L5.** The RED state carries 2 obsolete snapshots, so any visual-foundation run before G3 exits rc 1 and rewrites the file to LF with identical content (section 2d). This is measured, expected and harmless. Reports must show `git diff --exit-code -- '*.snap'` = 0 at RED.
- **L6.** The splash pins use a file-local instrumented reanimated mock, with a stable `useSharedValue`. They prove binding and arguments, not frame timing. Real motion is a device check: the mark must not move or fade at any time, and the tagline fades in after 200 ms.
- **L7.** It is OTA-capable, and it must merge before the production build, because the reviewer and the screenshots see the embedded JS.

**Stop conditions:**
- the base is not `0a7446b4`, or the worktree is dirty;
- a G3 sha differs;
- any other `.snap` changes;
- `app.json`, `package.json` or the lock changes;
- a test other than those in section 4 needs an edit.

## 8. Open questions (each with a RECOMMENDATION)

- **OQ1. The reveal mark size.**
  - **Recommend 56 pt (`size={BADGE_R}`).** It is readable at 2x and 3x with both filters, has 17.9 pt clearance to the circle and 25.2 pt letters (section 2c, contact sheets LOOKED AT).
  - The alternatives 60 or 64 pt are also clean. 67 pt and above crowds the circle.
  - A different size changes only the number in R1/R2, B9′ and the G3 sha (re-probe with `U4D_MARK_SIZE`).
- **OQ2. O1's premise is false: Login shows no brand at all.**
  - **Recommend R-a**: Register (both states) and ForgotPassword show `<QarenLogo size={56} />` in place of the text logo; Login stays without a brand block.
  - The rule is "no text logo on any auth screen; a brand block, where one exists, is the mark".
  - The alternatives:
    - **R-b:** delete the brand block on Register and ForgotPassword to match Login. The block is about 43 pt of text plus a 32 pt margin; in the centred `content` column the card shifts up by about half of that, roughly 38 pt. The account-creation screen App Review sees then carries no brand.
    - **R-c:** add the mark to Login too. That changes a design-recomposed screen with its own anatomy contract and B9 header geometry.
- **OQ3. Who edits `visual-foundation.test.tsx` and deletes `QaranIcon.test.tsx`.**
  - **Recommend RED**, as test-file changes forced by O2; GREEN touches tests only through G3.
  - The cost is the RED-state `2 obsolete` and rc 1 (L5).
  - The alternative is GREEN doing both just before G3, which keeps the RED full suite free of obsolete snapshots but makes GREEN edit test files.
- **OQ4. Where the `flipForRTL` cases go.**
  - **Recommend** the new `__tests__/icons/flipForRTL.test.tsx`, with verbatim cases, imported from `'../../src/icons'`. The helper keeps its 2 tests.
  - Keeping them in a file named `QaranIcon.test.tsx` would leave a test file named after a deleted component.
- **OQ5. `PhoneMockup.tsx:16` claims a "Q-mark" the code does not draw.** It is outside O4's three files.
  - **Recommend fixing it** (comment-only; R9 checks `Q-mark`). If ruled no, drop `Q-mark` from R9 and from the touch list.
- **OQ6. `__tests__/components/hero/RevealBurst.test.tsx:33` is named "renders the Q-badge at center".** It stays green.
  - **Recommend a name-only edit** to "renders the mark badge at center" in RED. The alternative is to leave it, since it is cosmetic.
- **OQ7. `ReferralLandingScreen.tsx:174` renders `t('app.name')` as a centred header TITLE** between a back button and a spacer. This is the referral landing page.
  - **Recommend out of scope.** It is a title, not a logo block, and it is not an auth screen.
  - If the owner wants a mark there too, file a follow-up. App Review reaches it only through a referral link.

---

## Review corrections (BINDING - supersede the body)

Adversarial review (Opus), session 71, 2026-10-03 11:53 to 12:35 AST.
- **Worktree:** `sc-s70-u4b`, HEAD `0a7446b4400ac12d9ddfab3a031577d95c816f2d`, branch `feature/s71-u4d-reveal-glyph`. `git status --porcelain | wc -l` was `0` before and after every run below.
- **Spec sha256 before this section:** `4608a9d826d5d455181fd61a2c8384dfcd673fda8af9cd2bcc17160cac38a4c8` (equal to the writer's report).
- **Evidence (scratch only, `SC/review/`):** `notes.md`; `mark_stats.py` → `mark_stats.json`; `sheet.py` → `rev_badge_sheet.png`, `rev_badge56_zoom4.png`; `make_probes.py` → `probe/` (green-shaped RevealBurst + auth probe), `splash_mut/`; `run_mx.sh` → `splash_mx.log`; `probe_o3b/` + `run_p1b.sh` → `splash_p1b.log`; `make_obs.py` → `probe_obs/` + `probe_obs.log`; `crlf_repo/` (a throw-away git repo); `jest_snap_owners_base.log`, `jest_neighbours_base.log`, `probe_run.log`.
- **Nothing was written in the worktree.** Every jest run was a path subset or used `--roots <scratch>`; no `-u` anywhere.
- **Tools:** jest 29.7.0, tsc 5.9.3, Pillow 12.3.0 (pinned venv; numpy is not installed there, so the pixel work is pure Pillow), git 2.52.0.windows.1.

### Re-measured and CONFIRMED (no change)

**QaranIcon and every Q glyph (2a, O2)**
- `git grep -n QaranIcon -- .` outside `docs/` gives exactly the spec's sites: `src/icons/QaranIcon.tsx`, `src/icons/index.ts:8`, `RevealBurst.tsx:50/:242`, the comments `LoadingRings.tsx:57/:209` and `UtilityIcons.tsx:62-63`, `__tests__/icons/QaranIcon.test.tsx`, `visual-foundation.test.tsx:24/:90-91/:120-122` and its `.snap` `:249/:327`. No dynamic import, no `require`, no `__mocks__` entry, no story or listing, nothing in `CLAUDE.md`, `design-sync.config.json` or `.design-sync/`.
- The 10 `react-native-svg` importers in `src/` draw no other Q. `lucide-react-native` `Search` (Step05Trust) is a plain magnifier. No text `'Q'` logo (`git grep -nE ">\s*Q\s*<|['\"]Q['\"]"` is empty). No catalog string mentions a Q.
- The deletion plan is complete: after it, `git grep -l "from 'react-native-svg'" -- src` gives 9.

**The badge and the mark (2b, 2c, D1)**
- Badge 112 × 112, radius 56, `#ECFDF5`, scale spring on the wrapper only; the only mount is `ResultsContent.tsx:461` (`size={220}`). `ResultsScreen.tsx:103` imports it and never renders it. The share path is text-only (`Share.share({ message })`, `ShareBottomSheet.tsx:193-205`, `ResultsScreen.tsx:533`); there is no view-shot or image generator. Step15Reveal uses MatchBadge.
- No clipping is possible: the 56 pt image box's corner is 28·√2 = 39.6 pt from the centre, inside the 56 pt radius, so even the transparent corners stay on the tint.
- **Halo, measured two ways.** `mark_stats.py` over all three scales: every partially transparent pixel is black (max channel ≤ 5) or emerald, and the largest amount by which any composite pixel is LIGHTER than its background is **0.039 levels over `#ECFDF5`**, 0.082 over `#F8F8FA`, 0 over white. A light fringe (a halo) is therefore impossible; the edges can only darken, which is ordinary anti-aliasing.
- **LOOKED AT** `SC/review/rev_badge_sheet.png` (3x LANCZOS / 3x point-sampled bilinear / 2x LANCZOS; the old Q at 67 pt redrawn from its 24-grid, then the mark at 48, 56, 60, 64, 67 pt, then 56 pt at the spring's 1.1 overshoot) and `rev_badge56_zoom4.png` (×4). **A user can read MY / EZ and the dot in every cell, with both filters, at 2x and 3x. There is no halo.** At 56 pt the ink (56 pt tall, 51.6 pt wide) has about the visual footprint of the old glyph (its ink ≈ 0.78 × 67 ≈ 52 pt). D1 stands; the check-glyph fallback is not triggered.
- Reduce motion: reanimated is 4.1.7, whose `withSpring` defaults to the system reduce-motion setting, so the badge simply lands at scale 1. RTL: nothing in the badge path mirrors (no `scaleX`, `badgeWrap` is `left:0/right:0`), and the Image is the same component U4c already ships under RTL.

**Snapshots (2d, D2)**
- 17 tracked `.snap`, 17 on disk, **0 orphans** (loop over `git ls-files '*.snap'`). Only the two named files embed the glyph (`git grep -c "reveal-burst|6.979|QaranIcon|x1=\"14.2\"|ECFDF5" -- '*.snap'` → RevealBurst 24, visual-foundation 5).
- Owners at base: `jest --ci __tests__/hero/RevealBurst.test.tsx __tests__/snapshots/visual-foundation.test.tsx` → `Test Suites: 2 passed` / `Tests: 20 passed` / `Snapshots: 19 passed`, rc 0, both `.snap` mtimes unchanged.
- **The RevealBurst expected sha is reproduced independently**, with no mock: `SC/review/probe/RevealBurstGreen.tsx` is the worktree file with exactly the R1 edit; under the committed test's describe/it names (`--ci=false --roots SC/review/probe`) it wrote a 6,363-byte `.snap` with sha256 **`57149ef59c89245c77f5cbd0cd947269fc48f4c8c7f6bba6d5e9a9d67ab9f887`**.
- **The visual-foundation expected sha is reproduced independently:** removing the two `QaranIcon` blocks from the LF-normalised committed file in Python gives 8,514 bytes, sha256 **`67dde70b6c176bde01467ece1d2cae61db522e36d6d15983ae85a1c62a871b38`**.
- Hazard 1 re-measured (`probe_obs`, the RED-shaped test over the committed CRLF bytes `ac572b71…`, 9,966 B): `› 2 snapshots obsolete`, `Tests: 15 passed`, `Snapshots: 2 obsolete, 15 passed`, rc=1.

**Who else renders the new sites (2h)**
- 12 suites mock RevealBurst; 4 render ResultsScreen with the real one (historyFloor.a17, usageFetch.a15, honestLoaders.u6, camera.engineUnavailable.s69); pushPrePrompt.u6 mocks ResultsContent; none counts Images.
- Only four suites mock `react-native` wholesale (HomeScreen.test, aiProcessingConsent.s69, the two playInstallReferrer suites); none reaches Register, ForgotPassword or RevealBurst, and no suite renders `App.tsx`. The local reanimated mocks in four Register suites and appleButton.s69 are irrelevant to an `Image`.
- Comment edits are safe: the Profile order tests use `indexOf('<ProfileHeaderRow')` (`ProfileScreen.bundleE.s3.test.tsx:41`); no PhoneMockup or LoadingRings suite reads its source; JSX comments do not reach the LoadingRings snapshot; the bundleD regexes for Register (`:235-252`) and ForgotPassword (`:262-276`) name no logo, style or import order that the swap moves.
- Neighbour subset at base (30 suites: inAppMark.u4c, QarenLogo, Splash ×2, RevealBurst ×2, icons ×3, bundleD, brand.hardcoded, AuthScreens, Register ×5, Login ×2, three i18n fences, PhoneMockup ×3, Profile/History s3, LoadingRings ×3): `Test Suites: 30 passed` / `Tests: 8 todo, 270 passed, 278 total` / `Snapshots: 4 passed`, rc 0.

**O1 (2e)**
- Login has no brand block (`git grep -n "app\.name\|QarenLogo\|logo" -- src/screens/LoginScreen.tsx` hits only the Apple-logo comment lines 12 and 69).
- Probe `SC/review/probe/__tests__/auth/authImages.test.tsx` at base: `REGISTER_FORM {"Image":0,"appName":1,"tagline":1,"svg":0}` (Apple available), `FORGOT {"Image":0,"appName":1,"resetPw":2}`. So A1/A3's "exactly 1 Image" is red at base and cannot be polluted by another Image (the Apple mock renders `AppleAuthenticationButton`, no Image).

**O3 (2f)**
- Re-ran the writer's prototype: base 4 passed; the writer's log shows it kills MS1–MS4 and MT1–MT4.

### Corrections

1. **(MAJOR, test design) P1 does not pin "never animates after the first frame". Three mutants survive it. Replace P1 with P1b.**

   P1 samples only 4 moments (0, 700 ms, after `ready`, 1,700 ms) and checks only opacity, transform, animated-style identity, layout-animation props and the `splash-mark` rect. Measured with `SC/review/run_mx.sh` (the writer's own `probe_o3` against scratch mutants from `make_probes.py`):
   ```
   BASE                              rc=0 Tests: 4 passed, 4 total
   MX1_state_inner_margin_slide      rc=0 Tests: 4 passed, 4 total   (inner View marginTop 0 -> -20 at 300 ms, plain useState)
   MX2_state_pulse_between_samples   rc=0 Tests: 4 passed, 4 total   (wrapper opacity 0.5 from 100 to 600 ms)
   MX3_remount_after_min             rc=0 Tests: 4 passed, 4 total   (splash-mark re-keyed when minElapsed flips)
   ```
   MX1 is a post-mount position slide, MX2 a fade, MX3 a remount (a fresh image request, so a possible blank frame on device). O3 forbids all three.

   **Binding:** P1 becomes **P1b** (same id slot, so every count in §5 and §6 is unchanged). Prototype: `SC/review/probe_o3b/__tests__/SplashScreen.motion.p1b.test.tsx`. At the first frame it records, for every host from the one `Image` up to the root, `{type, testID, deep-flattened style}`, and the `Image` test instance. It asserts no violation at the first frame (no style object from `__animatedStyles`, no `opacity`, no `transform`, no `entering`/`exiting`/`layout`/`animatedProps`). It then advances fake timers in **50 ms steps to 1,600 ms**, then re-renders with `ready`, and at every step requires: the same violations-free state, the same serialised host-path styles, and `image === firstImage`. Keep P1's first-frame `RECT` assertion.

   Measured with `SC/review/run_p1b.sh` → `splash_p1b.log`: P1b passes on the scratch base copy AND on the worktree file (`WORKTREE rc=0 Tests: 1 passed`), and kills MX1 (`300 ms: path styles changed`), MX2 (`100 ms: View opacity`), MX3 (`700 ms: Image remounted`), MS1, MS2, MS3 (first-frame violations) and MS4 (`700 ms: path styles changed`).

   **Mutant table:** add M12 = MX1, M13 = MX2, M14 = MX3, each killed by P1b. M6 and M11 are killed by P1b as well.

2. **(MAJOR, gate) Hazard 2 is incomplete: `git status` DOES show the LF rewrite.**

   §2d says the content-identical CRLF → LF rewrite is something "`git diff` does not show under autocrlf". True for `git diff`, but `git status` shows it. Measured in `SC/review/crlf_repo` (autocrlf=true, git 2.52.0.windows.1): commit a CRLF file (index LF), rewrite the working file as LF →
   ```
   git status --porcelain   ->  " M f.snap"
   git diff --exit-code     ->  rc 0, --stat and --numstat empty
   ```
   `probe_obs` shows what the RED-state run does to the real file: 9,966 B with 485 CR → **9,481 B with 0 CR, sha256 `34dc58879eae23196429936fb5d5fd552f32a212b99de26cb2af6e38d9885a08`** (obsolete keys kept).

   **Binding:**
   - In the RED state, `git status --porcelain` WILL list ` M SmartCompareApp/__tests__/snapshots/__snapshots__/visual-foundation.test.tsx.snap` after any `--ci` run that includes that suite (the RED full suite does). That is expected and is NOT a `.snap` change.
   - Every "no `.snap` changed" check before G3 (the RED report, the orchestrator's RED gate, GREEN's G1) uses `git diff --exit-code -- '*.snap'` (rc 0) AND `git diff --numstat -- '*.snap'` (empty), never `git status`.
   - The RED report names that status line and its cause, and gives the file's sha256. It must be either the committed `ac572b71396f7da3755422255629ad087b0a700144eefa09785e4f30a0fb736e` (CRLF, never run) or `34dc58879eae23196429936fb5d5fd552f32a212b99de26cb2af6e38d9885a08` (LF rewrite). Anything else is a STOP.
   - G3 step 5 (`git status` shows exactly two ` M` `.snap` lines after the update) stays valid.

3. **(MEDIUM, wrong reds) Two RED assertions need a precondition or a filter.**
   - **(a)** R2, R3, A1 and A3 must FIRST assert exactly one host with `n.type === 'Image'` in the scope they test, and read every prop from that host (U4c correction 2). R3's "no host from the Image to the root has `accessibilityLabel` / `accessible === true`" is otherwise vacuous at base, where there is no Image. The RED report must show R2/R3/A1/A3 failing on the Image count.
   - **(b)** R5 ("the only JSX child of the `reveal-burst-badge` element is that `<QarenLogo>`") must ignore whitespace-only `JsxText`. Measured with the installed typescript on the worktree file: the badge's children are `JsxText(ws=true), JsxSelfClosingElement, JsxText(ws=true)`. Without `!(ts.isJsxText(c) && c.containsOnlyTriviaWhiteSpaces)`, R5 stays red after a correct GREEN.

4. **(MEDIUM, process) `inAppMark.u4c.test.ts` is frozen by U4c UG3; the B8/B9 edit needs its own ruling.**

   **Binding:** the orchestrator lifts UG3 for exactly these bytes:
   - `SITE_FILES` (+3 entries, kept sorted);
   - the word "six" → "nine" in B8's name and its comment;
   - B9's expected map (+3 entries) and its name.

   No other line of that file moves. The RED report pastes that file's `git diff`.

5. **(LOW) The new splash file's shape.**
   - `__tests__/SplashScreen.motion.u4d.test.tsx` imports `../src/screens/SplashScreen` statically. The prototype's `U4D_SPLASH` environment hook and its absolute paths stay in scratch.
   - It keeps `jest.clearAllMocks()` in `beforeEach`; P2 reads cumulative `mock.calls`.
   - Its `jest.mock('react-native-reanimated', factory)` is not `virtual`.

6. **(LOW, L1) The spring-overshoot arithmetic.**
   - RN iOS decodes a file-URL image down to the view's pixel size (`RCTDecodeImageWithData`, `node_modules/react-native/Libraries/Image/RCTImageUtils.mm:259-302`, `kCGImageSourceThumbnailMaxPixelSize`). After an OTA the mark arrives as a file, so at 3x the bitmap is 168 px. The 1.1 overshoot is then a transient ~10 % UPSCALE of that bitmap, not "a downscale from the 384 px asset". The embedded bundle's `imageNamed` path keeps the full asset.
   - The simulated cell (column 7 of `rev_badge_sheet.png`) shows no visible softening.
   - Keep it as an L1 device check (fresh install and after an OTA). No code change.

7. **(LOW, inventory) O1 completeness.**
   - `ResetPasswordScreen.tsx` (auth stack, W3-6) has no brand block: `grep -nE "logo|app\.name|QarenLogo|styles\.header"` is empty. It is unchanged under R-a.
   - `Step17Notifications.tsx:90` `t('app.name')` is the sender line of a push-notification preview card, not a logo. It stays out of scope with OQ7.
   - §2a's "the other 14 hits are in `docs/`" is 31 lines in 12 files; docs stay untouched.

8. **(LOW, gate) G6 also greps `Q-mark` when OQ5 is ruled yes:** `git grep -nE "Q-ring|Q logo|Q-mark" -- SmartCompareApp/src` must give no output. **Stated limit:** R5 inspects only the badge, and R8 only the old glyph's exact geometry strings. An inline Q drawn elsewhere in the particle `Svg` would be caught only by the G3 snapshot sha.

### Answers to the writer's open questions (RECOMMENDATIONS; the orchestrator rules)

- **OQ1 → AGREE: 56 pt (`size={BADGE_R}`).** My own 3x/2x sheet with two filters, the ×4 zoom and the pixel statistics show it readable with no halo. Its ink footprint matches the old glyph's, and it keeps 17.9 pt of clearance. 60 and 64 are also clean. The sha for 56 is independently reproduced (`57149ef5…`).
- **OQ2 → AGREE: R-a.**
  - Register (both states) and ForgotPassword show `<QarenLogo size={56} />` in place of the text logo. Login and ResetPassword stay without a brand block. That matches the design reference `AuthScreens.jsx`, which has none on sign-in.
  - Rule: "no auth screen draws the app name as a text logo; a brand block, where one exists, is the mark".
  - R-b loses the only brand cue on the account-creation screen App Review sees. R-c reopens a recomposed screen.
- **OQ3 → AGREE: RED** makes both test edits (they are test files; GREEN keeps to `src/` plus the G3 run). Correction 2 is binding with it: the RED state carries `2 obsolete`, rc 1, and an expected ` M` status line on the visual-foundation `.snap`.
- **OQ4 → AGREE.** Move the two `flipForRTL` cases verbatim to `__tests__/icons/flipForRTL.test.tsx`, importing from `'../../src/icons'`.
- **OQ5 → AGREE: fix the comment.** `PhoneMockup.tsx` draws a `#2A2A2F` indicator `Rect` and a `#2A2A2F` notch `Circle` (`:303-318`), and no mark. No suite reads that file's source. Comment-only. Add `Q-mark` to G6 (correction 8).
- **OQ6 → AGREE: optional name-only edit.** `components/hero/RevealBurst.test.tsx` owns no snapshot; its five cases stay green.
- **OQ7 → AGREE: out of scope** (a header title on a non-auth screen). The same applies to the Step17 push-preview sender line (correction 7).

**Verdict: APPROVED_WITH_CORRECTIONS.** These hold as measured: D1 (the mark reads, no halo), the QaranIcon deletion plan, both expected snapshot shas, the O1 inventory and its premise, the neighbour suites and the counts. Corrections 1–2 are the substantive ones: an under-powered splash pin, and a git-status signal that would have read as an unauthorised `.snap` change. Corrections 3–5 are test-construction musts. Corrections 6–8 are limits and inventory.

## Orchestrator rulings (BINDING - supersede the review corrections and the body; 2026-10-03 12:30)

Review verdict APPROVED_WITH_CORRECTIONS; corrections C1-C8 are accepted as written and bind the RED and GREEN agents, with these rulings on top (later wins):

- **UR1 (OQ1).** The mark in the reveal badge is 56 pt (size={BADGE_R}); the check-glyph fallback is not used.
- **UR2 (OQ2 = R-a).** Register (both states) and ForgotPassword render <QarenLogo size={56} /> in place of the t('app.name') text logo; Login is unchanged (it has no brand block). Rule: no auth screen shows a text logo; where a screen has a brand block, it is the mark.
- **UR3 (OQ3, RED scope).** RED does NOT delete __tests__/icons/QaranIcon.test.tsx and does NOT edit __tests__/snapshots/visual-foundation.test.tsx. GREEN makes both edits (delete the file; remove the QaranIcon import line and the two its) immediately before its authorised jest -u on visual-foundation.test.tsx, so the RED state never carries obsolete snapshots and never rewrites a .snap. The RED-state full-suite expectation changes accordingly: 13 failed RED its, no obsolete snapshot, git diff --exit-code -- *.snap = 0 and no .snap in git status (C2 then applies to GREEN).
- **UR4 (OQ4).** RED creates __tests__/icons/flipForRTL.test.tsx with the two flipForRTL cases copied verbatim (they pass at base; the original file stays until GREEN deletes it, so the two cases run twice in the RED state, which is accepted).
- **UR5 (OQ5).** Yes: the PhoneMockup.tsx:16 comment is corrected (comment-only); R9 and G6 keep Q-mark in their grep.
- **UR6 (OQ6).** No rename of the RevealBurst.test.tsx case name; that file is not edited (its snapshot file changes through the authorised jest -u only, and the expected sha 57149ef5... assumes no rename).
- **UR7 (OQ7, C7).** ReferralLandingScreen and Step17Notifications stay out of scope; no follow-up is filed.
- **UR8 (C4, the frozen U4c test).** The U4c freeze (UG3) is lifted for exactly this edit of __tests__/brand/inAppMark.u4c.test.ts: SITE_FILES gains components/hero/RevealBurst.tsx, screens/ForgotPasswordScreen.tsx and screens/RegisterScreen.tsx (sorted), six becomes nine in the B8 name and comment, and the B9 expected map gains the three entries named in section 4 with its name updated. The RED report pastes that diff; nothing else in that file changes.
- **UR9 (C1).** P1 is replaced by P1b (every host on the path from the Image to the root frozen, sampled every 50 ms to 1600 ms and after ready); mutants M12-M14 (MX1-MX3) are added to the kill list. The new splash file is __tests__/SplashScreen.motion.u4d.test.tsx (one file; C5 conventions).
- **UR10 (C2, GREEN gate).** Every no-snapshot-changed check uses git diff --exit-code plus git diff --numstat on *.snap, never git status; the visual-foundation .snap sha must be ac572b71... (untouched) or 34dc5887... (the content-identical LF rewrite) before G3, anything else is a STOP. The two authorised jest -u runs (RevealBurst.test.tsx, then visual-foundation.test.tsx, one each) must land on 57149ef5... and 67dde70b...; a different sha is a STOP that the orchestrator rules on, not a retry with -u.
- **UR11 (C3).** R2, R3, A1 and A3 first assert exactly one Image host and read every prop from it; R5 ignores whitespace-only JsxText.
- **UR12 (C6, C8).** Stated limits as written; the device checks after the production build (fresh install and after an OTA) include the reveal badge at the 1.1 spring overshoot.
- **UR13 (files).** RED writes only: the three new test files of section 4 (revealGlyph.u4d, authBrandMark.u4d, SplashScreen.motion.u4d), icons/flipForRTL.test.tsx, and the UR8 edit; nothing under src/, no .snap, no mock, no config. GREEN touches only the src files of section 4 plus the test deletions and edits of UR3 and the two .snap files through jest -u; package.json, app.json, eas.json and the lock do not change.
- **UR14.** No file-top import of a module this unit deletes; require inside the it (section 5 helpers).

## Orchestrator gate on the RED tests (BINDING - supersedes everything above where they differ; 2026-10-03 13:01)

Gate: **PASS.** Five files under SmartCompareApp/__tests__, FROZEN from here on (sha256 prefixes): brand/revealGlyph.u4d.test.tsx fb358765702be2ac (R1-R9), screens/authBrandMark.u4d.test.tsx 8b899fd531aba340 (A1-A5), SplashScreen.motion.u4d.test.tsx 1aa07e756e1a13d8 (P1b, P2-P4), icons/flipForRTL.test.tsx 58c77d4b462c5620 (F1, F2), and the UR8 edit of brand/inAppMark.u4c.test.ts 6cec039bf0b5034b (+9/-3, the diff read by the orchestrator: exactly the SITE_FILES, B8 and B9 changes). At base 0a7446b4: 13 RED (R1 R2 R3 R5 R6 R8 R9 A1 A2 A3 A4 B8 B9) each for the stated reason, R2/R3/A1/A3 failing first on the Image-host count; every PIN green; P1b proven against MX1-MX3 and MS1-MS4 in scratch; the GREEN-shape probe turned R1-R5, R7 and A1-A5 green on copies; the full suite at RED = 13 failed, no suite fails to load, 44 snapshots pass, both .snap shas unchanged (git diff --exit-code 0).

- **UG1 (no test edit in GREEN except the ruled ones).** GREEN edits no test file except: DELETE __tests__/icons/QaranIcon.test.tsx and the two-it-plus-import removal in __tests__/snapshots/visual-foundation.test.tsx (UR3), both immediately before the authorised jest -u on visual-foundation. The five gated files above are byte-frozen.
- **UG2 (the two snapshot updates).** Exactly two jest -u runs by GREEN, one per owning file, in this order: __tests__/hero/RevealBurst.test.tsx (expected .snap sha 57149ef5...), then __tests__/snapshots/visual-foundation.test.tsx (expected 67dde70b...). Before each: git diff --exit-code -- "*.snap" is 0 (UR10). After both: git diff --numstat shows exactly those two .snap paths; a different sha is a STOP and a report, never a second -u. No adversary and no fix agent ever runs jest -u.
- **UG3 (targets).** After GREEN: Test Suites 3 skipped, 357 passed, 357 of 360; Tests 13 skipped, 13 todo, 3485 passed, 3511 total; Snapshots 42 passed, 42 total; tsc 0; eslint 0 errors on the changed files; the backend tests that scan the client (grep -rl SmartCompareApp tests/ --include=test_*.py) green through the bounded runner.
- **UG4 (files).** GREEN touches only the src files of spec section 4 (RevealBurst.tsx, QaranIcon.tsx deleted, icons/index.ts, UtilityIcons.tsx comment, RegisterScreen.tsx, ForgotPasswordScreen.tsx, the LoadingRings / ProfileScreen / HistoryScreen / PhoneMockup comments) plus the UG1 test edits and the two .snap files; app.json, eas.json, package.json, the lock, App.tsx, the i18n catalogs, mocks and configs do not change; react-native-svg stays a dependency (nine other src files use it).
- **UG5 (mutants).** M1-M11 of spec section 5 plus M12-M14 (MX1-MX3) and the P2-P4 mutants MT1-MT4: each on the GREEN tree, byte copy, mutate, run the named files, must FAIL, restore, sha256 equal, never -u, never git checkout --.
- **UG6 (process).** GREEN, then two Opus adversaries (visual / App Review, engineering), then fix, then the orchestrator diff review (both .snap diffs read), commit, PR, merge on green. OTA-capable and must be in the store binary (before the production build).
