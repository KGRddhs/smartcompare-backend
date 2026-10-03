# U4c — the in-app MYEZ mark (JS + bundled PNG; OTA-capable; in the store binary)

Spec writer: Opus (read-and-measure only), session 71, 2026-10-03 08:22–08:55 AST. Evidence folder (all scratch, nothing in the worktree): `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad/u4c2/` (below: `SC/`). Inputs read: plan §U4c + "Ahmed's answers", research digest §U4c, U4B spec §1.9–1.14, §4, review corrections + rulings RQ1–RQ21, `scripts/render_myez_icons.py`, `docs/brand/myez-icons.manifest.json`, the earlier agent's `scratchpad/u4c/` (re-run, not cited).

Binding decisions implemented (not re-opened): **D1** drop the app-name text beside the mark; **D2** the splash mark starts at the native launch position at full opacity, only text animates; **D3** exactly ONE `jest -u`, on `__tests__/hero/LoadingRings.test.tsx`, diff reviewed by the orchestrator.

---

## 1. Base

```
$ git -C C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b rev-parse HEAD
de66a25f23684cdc880cfa358e65553e181f259a
$ git -C …/sc-s70-u4b status --porcelain        (empty = clean; re-checked after every measurement)
$ git -C …/sc-s70-u4b branch --show-current
feature/s70-u4b-icons-deps
```

U4c is cut from **main after PR #279 (U4b) merges**, on a new branch in this same worktree. Every anchor below was measured at `de66a25f`. **The RED agent's first step:** `git diff de66a25f <new-base> -- SmartCompareApp/src SmartCompareApp/__tests__ SmartCompareApp/__mocks__ SmartCompareApp/assets SmartCompareApp/app.json SmartCompareApp/package.json scripts/render_myez_icons.py docs/brand` must be empty. If it is not (U4b changed in review), STOP and report; anchors and the recorded hashes must be re-measured.

Tool versions (from `SmartCompareApp`): jest 29.7.0, tsc 5.9.3, eslint 9.39.4; Pillow 12.3.0, Python 3.12.9 (pinned venv), black 26.5.1. `node_modules/@babel/core` and `node_modules/.bin/jest` exist.

Baselines at `de66a25f` (logs in `SC/`):
- FULL jest (`timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci`, `SC/jest_full_base.log`): `Test Suites: 3 skipped, 351 passed, 351 of 354 total` / `Tests: 13 skipped, 13 todo, 3448 passed, 3474 total` / `Snapshots: 44 passed, 44 total`, rc 0.
- Subset of every suite this unit touches (13 files, `SC/jest_base_subset.log`): `13 passed / 136 passed / Snapshots: 2 passed`.
- `tsc --noEmit`: 0 lines, rc 0 (`SC/tsc_base.log`).
- eslint on `src/theme/fonts.ts src/components/QarenLogo.tsx src/screens/SplashScreen.tsx src/screens/HomeScreen.tsx`: `0 errors, 3 warnings` (all 3 in HomeScreen.tsx:65-66, `import/no-duplicates` ×2 + `import/no-named-as-default`).
- `python scripts/render_myez_icons.py --check`: 4× `pixels match` + `myez-icons.manifest.json matches`, rc 0. `black --check` and `ruff --select E9,F63,F7,F82` on the renderer: clean.

---

## 2. Measured facts

### (a) `src/components/QarenLogo.tsx` (64 lines, `cat -n`)
- `import Svg, { Circle, Path, G } from 'react-native-svg'` (:16); `import { colors } from '../theme'` (:17).
- `Props = { size?: number; color?: string }` (:19-22); `export default function QarenLogo({ size = 32, color = colors.text.primary })` (:24-27).
- Draws `<Svg width={size} height={size} viewBox="0 0 32 32" fill="none">` → `<G>`: Q-ring `Circle cx16 cy16 r13 stroke={color} strokeWidth 2.5` (:44-51), Q-tail `Path d="M22 22 L27 27"` (:53-58), emerald dot `Circle cx22 cy11 r2 fill={colors.accent}` (:60).
- Accessibility: **only** `accessibilityElementsHidden` + `importantForAccessibility="no-hide-descendants"` (:39-40). No `accessible`, no label. **The component has NO testID.** The testIDs the plan protects live elsewhere: `loading-rings-logo` (wrapper in LoadingRings.tsx:206), `welcome-qicon` (wrapper in Step01Welcome.tsx:75), `mock-qaren-logo` (the 11 jest mocks).

### (b) Every import and use (`git -C … grep -n "QarenLogo" -- SmartCompareApp`; `git grep -n "M22 22 L27 27\|r={13}\|cx={22}"`; `git grep -ln react-native-svg -- src App.tsx`)

| site (import line) | JSX | size (pt) | surrounding layout | background under the mark |
|---|---|---|---|---|
| SplashScreen.tsx (:12) | `<QarenLogo size={128} />` :112 in `Animated.View brandStack` :111-114 | 128 | centred column, `gap 20`, wordmark below, tagline below | `colors.bg.primary` **#FFFFFF** (container :123-129) |
| HomeScreen.tsx (:74) | `<QarenLogo size={28} />` :900 in `View headerLeft` :899-902 | 28 | row, `alignItems center`, + `Text t('app.name')` :901 | header has no bg → `container` **#FFFFFF** (:1191-1194) |
| ProfileScreen.tsx (:69) | `<QarenLogo size={28} />` :355 in `ProfileHeaderRow` `View headerRow` :354 | 28 | row `gap 12`, + user name/region text | **#FFFFFF** (container :647-650) |
| HistoryScreen.tsx (:34) | `<QarenLogo size={24} />` :939 in `View header` :937-943 | 24 | row, + `Text t('history.title')` | **#FFFFFF** (container :1025-1028) |
| Step01Welcome.tsx (:52) | `<QarenLogo size={40} />` :76 in `View brandRow testID="welcome-qicon"` :75-77 | 40 | top-left; container padding 24, brandRow paddingTop 8 → mark at (24,32)–(64,72) | **NOT white**: the absolutely positioned `warmCornerLeft` (:145-153; top −130, left −108, 360×260, radius clamps to 130 → straight section x 22…122, y −130…130) covers the whole mark: `rgba(190,200,255,0.22)` over #FFFFFF = **(240.7, 242.9, 255) ≈ #F1F3FF**. `warmCornerRight` starts at x ≥ W−252 ≥ 123: no overlap. |
| LoadingRings.tsx (:63) | `<QarenLogo size={Math.round(size * 0.22)} />` :212 in `View center testID="loading-rings-logo"` :206 | callers: **LoadingScreenVariants.tsx:369 `size={240}` → 53** (Home compare loader + onboarding Step14), **ResultsScreen.tsx:742 `size={120}` → 26**; default 320 → 70 (tests only) | static centre of 3 expanding emerald rings (rings start at r = 0.1875·size, mark half-width 0.11·size → never overlap) | **#FFFFFF** (LoadingScreenVariants root :578-583; ResultsScreen container :987-990) |

- The research digest missed the **240 → 53 pt** loader size (the most-seen LoadingRings instance).
- `App.tsx`, `__mocks__/`: no QarenLogo reference. Q-ring path data appears only in QarenLogo.tsx and in `__tests__/hero/__snapshots__/LoadingRings.test.tsx.snap` (`git grep -c` → 4 hits; no other of the 17 `.snap` files).
- **A second old Q glyph exists:** `src/icons/QaranIcon.tsx` ("Qaran brand mark — Q rendered as a magnifying glass") rendered by `RevealBurst.tsx:242` at `round(56*1.2)=67` pt on a `colors.accentLight` (#ECFDF5) circle, in the Results winner reveal (`ResultsContent.tsx:461`). It is not QarenLogo and has its own snapshots (`RevealBurst.test.tsx.snap` 2 hits, `visual-foundation.test.tsx.snap` 9 hits) → outside D3 → **OQ2**.
- **No dark theme:** `app.json` `"userInterfaceStyle": "light"`; no `useColorScheme`/`Appearance` in src (`git grep` empty). The only non-white surface under a mark is Step01Welcome's tint.

**Cut-out error over each background** (`SC/measure_geo.py` → `SC/geo_facts.json`, prototype @3x). With the colour-to-alpha cut-out, a pixel of ink colour I and coverage w composited over B differs from the ideal `w·I + (1−w)·B` by exactly `w·(1−α_ink)·(B−W)` (α_ink = 245/255 black, 239/255 emerald). Max visible error (levels of 255): **#FFFFFF 0.00; #F1F3FF (Welcome tint) 0.88; #F8F8FA 0.44 (reference); #ECFDF5 1.19 (RevealBurst reference); #0A0A0B 15.4 (dark reference, no site).** Every real site is ≤ 0.88 level: invisible. Note: LANCZOS overshoot clips some core pixels to alpha 255 (`core_samples`: black `(0,0,1,255)`, emerald `(0,181,121,255)`), so a few core pixels read (0,0,1)/(0,181,121) instead of the master's (10,10,11)/(16,185,129) on every background including white — a resampling property shared with U4b's splash-icon.png, not a background error.

### (c) D1 — brand text adjacent to the mark (and what pins it)

| site | adjacent text | verdict | what pins it |
|---|---|---|---|
| Splash | `<Animated.Text style={styles.logo}>{t('app.name')}</Animated.Text>` :113 (40/700, `styles.logo` :136-141) | **REMOVE** | `__tests__/SplashScreen.test.tsx:36-42` `getByText('MYEZ')` (breaks → inverted, see §5). |
| Splash | `t('splash.tagline')` :115-117 = "Compare smarter" (en) | KEEP (tagline, not the name; ar value does not contain ميّز) | `SplashScreen.test.tsx:44-48` |
| Home | `<Text style={[styles.logo, styles.logoSpaced]}>{t('app.name')}</Text>` :901 | **REMOVE** (+ the then-unused `styles.logo` :1207-1211 and `styles.logoSpaced` :1212-1214; only user is :901) | nothing renders Home and asserts 'MYEZ' (`git grep -n MYEZ -- __tests__`: only SplashScreen.test:41 asserts it; HomeScreen.test.ts:52 is a mock table) |
| Profile | user display name + region subtitle | KEEP (not brand) | — |
| History | `t('history.title')` = "History" | KEEP (screen title) | — |
| Step01Welcome | none in `brandRow` | — | — |
| LoadingRings | none (counter chip / caption are not brand) | — | — |

Removing the two `t('app.name')` uses breaks no fence: `app.name` stays referenced by App.tsx:140, ForgotPasswordScreen:87, ReferralLandingScreen:174, RegisterScreen:293/324, Step17Notifications:90 (`git grep -n "app\.name"`), so `no-missing-referenced-keys` and `no-deleted-keys` are unaffected (no catalog change); `brand.myez.s69` reads the catalog only; `brand.hardcoded.s69` inspects string literals/JSX text and skips comments and `require()` specifiers (`isModuleSpecifier`, :48-61) — a `require('../../assets/brand/myez-mark.png')` and "Qaren" in comments are safe; **a string literal containing "Qaren" is not**. There is no unused-key fence (`__tests__/i18n/` lists none). Consequence (Ahmed's D1, recorded): Arabic users lose the Arabic «ميّز» beside the Home mark and the Splash; the mark is Latin.

### (d) D2 — the hand-off

**SplashScreen.tsx today:** `logoOpacity` 0 → 1 and `logoScale` 0.8 → 1 over 400 ms `Easing.out(Easing.ease)` (:43-44, :64-65), applied to the `brandStack` (mark + wordmark, :111); `taglineOpacity` 0 → 1, `withDelay(200, withTiming(1, {duration: 400}))` (:45, :68); container `flex 1, #FFFFFF, justifyContent/alignItems center, gap 20` → the stack is centred as a whole, so the mark sits ABOVE centre and grows from 80 % at opacity 0: a jump + fade at hand-off. Floors MIN 700 / MAX 1500 ms (:28-29) — unchanged by U4c.

**App.tsx:** `if (!fontsLoaded || isLoading || showSplash) return <SplashScreen onFinish={handleSplashFinish} ready={fontsLoaded && !isLoading} />` (:345-348) — bare at the root (no SafeAreaView), so the container fills the window. Pinned by `SplashScreen.readyFloor.a5.test.tsx:173-185` (App.tsx is not touched).

**Native launch screen (iOS):** `expo-splash-screen` is NOT installed (`ls node_modules | grep -i splash` → nothing). `@expo/prebuild-config` **54.0.9** (nested at `node_modules/expo/node_modules/@expo/cli/node_modules/@expo/prebuild-config`) `getIosSplashConfig.js` root-`splash` branch: `enableFullScreenImage_legacy: true, imageWidth: 200`; `InterfaceBuilder.js:87-90` frame 414×736, `getAbsoluteConstraints(..., legacy=true)` (:73-77) pins the image view **top/leading/trailing/bottom to `EXPO-ContainerView`** (full screen); `withIosSplashScreenStoryboardImage.js:46-49` `contain` → **`scaleAspectFit`**. So the square 1024 splash-icon.png is drawn at the full screen WIDTH W, vertically centred.

**expo-updates 29.0.20** (`ios/EXUpdates/ReactDelegateHandler/ExpoUpdatesReactDelegateHandler.swift:47-62`) re-shows the launch storyboard view inside a deferred root view while the update controller starts; then `recreateRootView` (:103-116, `window.makeKeyAndVisible()` :116) installs the RN root view with the white background and **no loading view** (no `expo-splash-screen` subscriber to `customizeRootView`). Between that swap and the first JS frame the screen is plain white for an unmeasured interval → limit L2 / OQ4. U4c can fix the geometry, not that gap.

**Geometry.** splash-icon.png (renderer `render()`: `splash_scale = 0.30·1024/1146`, `n = round(2048·s) = 549`, offset `(1024−549)//2 = 237`). The mark PNG of this unit is the master's ink box `(483,399,1629,1641)` padded to a square of side 1242 at master origin **(435, 399)** (§2h). Equating master pixels on both sides gives, for a window W×H (portrait, D = min(W,H) = W):

```
size = W · 1242·549/(2048·1024)                 = 0.3251352 · W
left = (W−D)/2 + D·(237 + 435·549/2048)/1024     = 0.3453212 · W     (portrait)
top  = (H−D)/2 + D·(237 + 399·549/2048)/1024     = (H−W)/2 + 0.3358970 · W
```

| window (pt) | scale | size | left | top | mark centre − screen centre | @Nx px / asset px |
|---|---|---|---|---|---|---|
| 375×667 | 2 | 121.926 | 129.495 | 271.961 | (+2.958, −0.576) | 243.9 / 256 |
| 390×844 | 3 | 126.803 | 134.675 | 358.000 | (+3.077, −0.599) | 380.4 / 384 |
| 393×852 | 3 | 127.778 | 135.711 | 361.508 | (+3.100, −0.603) | 383.3 / 384 |
| 430×932 | 3 | 139.808 | 148.488 | 395.436 | (+3.392, −0.660) | **419.4 / 384 (×1.09 upscale)** |
| 440×956 (16 Pro Max) | 3 | 143.060 | 151.941 | 405.795 | — | **429.2 / 384 (×1.12)** |

The +3 pt horizontal offset is the master's own 32 px design offset (U4b §1.14), preserved.

**Measured, not just derived** (`SC/geo_facts.json`): native ink = alpha ≥ 128 bbox of the COMMITTED splash-icon.png `(366,344,673,677)` mapped by aspect-fit; JS ink = alpha ≥ 128 bbox of the prototype @3x `(15,0,369,384)` mapped through the layout above. Edge differences (pt), l/t/r/b: 375×667 `+0.225/−0.015/+0.198/−0.038`; 390×844 `+0.234/−0.016/+0.206/−0.039`; 393×852 `+0.236/−0.016/+0.208/−0.040`; 430×932 `+0.258/−0.017/+0.228/−0.043`. **Max 0.258 pt.** Plus RN's pixel-grid rounding (≤ 1/(2·scale) pt). **Tolerance: 0.5 pt.**

**The pure function** (new module `src/utils/splashMarkLayout.ts`; it imports nothing from `react-native`; the screen passes `Dimensions.get('window')` — the RN jest mock has `Dimensions` (390×844, `__mocks__/react-native.ts:72-75`) but NO `useWindowDimensions`):

```ts
export const MASTER_PX = 2048;
export const SPLASH_CANVAS_PX = 1024;
export const SPLASH_MARK_PX = 549;      // = manifest mark_geometry.splash_mark_px
export const SPLASH_OFFSET_PX = 237;    // = manifest mark_geometry.splash_offset_px
export const MARK_SQUARE_MASTER_PX = [435, 399, 1242] as const; // x0, y0, side
export function splashMarkLayout(win: { width: number; height: number }): { left: number; top: number; size: number }
// D = min(w,h); k = D / SPLASH_CANVAS_PX; f = SPLASH_MARK_PX / MASTER_PX;
// left = (w-D)/2 + k*(SPLASH_OFFSET_PX + x0*f); top = (h-D)/2 + k*(SPLASH_OFFSET_PX + y0*f); size = k*side*f
```

**Android** (not the target; Apple-first lane): the legacy root splash draws splash-icon.png `contain` into a 200 dp image in a 288 dp canvas, centred (U4B correction 6) — the wordmark is ~61 dp wide there vs ~126 dp from this layout, so on Android the hand-off still jumps (scale). Accepted (limit L3, OQ3). Android `Image` also fades non-resource sources for 300 ms (`ReactImageView.kt:423-427`: `fadeDurationMs >= 0 → it; isResource → 0; else 300`) — an OTA-delivered asset is a file, not a resource, hence R4's `fadeDuration={0}`.

### (e) LoadingRings
- The mark is static (not animated): `<View style={styles.center} pointerEvents="none" testID="loading-rings-logo"><QarenLogo size={Math.round(size * 0.22)} /></View>` (:206-213); only the three `Ring` circles animate (`useAnimatedProps`, :108-125).
- Snapshot file `__tests__/hero/__snapshots__/LoadingRings.test.tsx.snap` (323 lines, `i/lf w/crlf`), written ONLY by `__tests__/hero/LoadingRings.test.tsx` (2 `toMatchSnapshot`, keys `LoadingRings hero renders default snapshot 1` :3, `… renders with explicit counter target 1` :164). Other LoadingRings suites (`components/hero/LoadingRings.test.tsx`, `hero/LoadingRings.animation.test.tsx`) write no snapshot.
- **The exact expected change was generated, not guessed:** a scratch probe (`SC/probe2/__tests__/LoadingRings.test.tsx`: same describe/it names, the real worktree LoadingRings, QarenLogo mocked to the R-contract component) run with `--ci=false --roots SC/probe2` wrote the snapshot into scratch only. `diff -u --strip-trailing-cr` vs the committed file = `SC/expected_snap_fade0.diff` (sha256 `563805f2d0bb75627caa05197f5b28e388eac83b38329f9d40723d29e980e047`): two identical hunks `@@ -92,37 +92,23 @@` and `@@ -253,37 +239,23 @@`, each replacing the 30-line `<Svg …>…</Svg>` (viewBox 0 0 32 32, G, two Circles, Path) with:

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
            "height": 70,
            "width": 70,
          }
        }
      />
```
Expected new snapshot file: `SC/probe2/__tests__/__snapshots__/LoadingRings.test.tsx.snap`, LF, sha256 **`7d22d5444df76638082781bc047c6397d091bf46793e444007b7afae79669e07`**. (Variant without `fadeDuration`, if OQ6 strikes R4's fade: `SC/probe/...snap` sha256 `669ca9d0b05c4d3671b6b78ac8a821c3859d4067f07de4a9cc11714908592c8a`, diff `SC/expected_snap.diff` sha256 `2c1bb3f16e1d3dbf90b27c96604a6905da94a1c7d28e829ff7b75ec21826db58`.)

### (f) jest
- `jest.config.js` moduleNameMapper `'\\.(ttf|otf|woff2?|png|jpg)$' → __mocks__/fileStub.ts` (`export default 0;`). **Probe** (`SC/probe/__tests__/pngstub.probe.test.ts`, run with `--roots SC/probe`): `PROBE {"a":{"default":0},"keys":["default"],"esModule":true,"same_ab":true,"same_ac":true}` — `require` of icon.png, of splash-icon.png and of a **nonexistent** `../../assets/brand/does-not-exist.png` all return the SAME object. **So `toBe(require(samePath))` cannot detect a wrong source file** (the digest's recommended assertion is a sanity check only); the source file is pinned by an AST test (A8) plus the asset/manifest tests.
- RN mock: `Image = ({source, ...props}) => createElement('Image', {...props, source})` (`__mocks__/react-native.ts:16-17`) → host type `'Image'`; style passes through unflattened.
- Reanimated mock: `useAnimatedStyle(updater)` returns `updater()` on each render; `withTiming/withDelay` return the target; shared values are plain objects (`__mocks__/react-native-reanimated.ts:16-46`). So the FIRST render shows the initial values (splash base: `{opacity: 0, transform: [{scale: 0.8}]}` on the brandStack) — a first-frame test is meaningful.
- The 11 suites that mock the path (all non-virtual, all return `createElement('View', { testID: 'mock-qaren-logo' })`): `HomeScreen.{abortOnUnmount, arabicAlerts.w311, bootDefer.b5, bundleE.s3.integration, cancelCompare.a4, eS3hf.loaderVisibility, engineUnavailable.s69, errorCopy.a11, rateLimitedSeconds.w314, trending.s69}.test.tsx` + `consent/aiProcessingConsent.s69.test.tsx`. Only `HomeScreen.cancelCompare.a4.test.tsx:211` reads the testID. None changes.
- `QarenLogo.test.tsx` (5 cases): 1 "single Svg root" → GOES; 2 "size → width+height+viewBox" → CHANGES (Image style); 3 "default 32" → CHANGES (Image style); 4 "emerald accent dot" → GOES (the dot is now pixels: B4); 5 "color prop" → GOES (prop dropped; tsc would reject `color=` once Props loses it — tsconfig has no `include`, so tests are type-checked).
- `Step01Welcome.test.tsx` (7 cases) renders the REAL QarenLogo; only `getByTestId('welcome-qicon')` touches the mark → all 7 stay green unchanged. `honestLoaders.u6.test.tsx:137` (`loading-rings-logo` present) stays green.
- `jest --ci` never writes snapshots; `-u` is forbidden except D3 (`s70-common.txt` rule; `--ci -u` → `updateSnapshot: 'all'`).

### (g) Metro and EAS Update (from node_modules)
- Scale pick: `react-native/Libraries/Image/AssetUtils.js:15-28` `pickScale` = smallest available scale ≥ `PixelRatio.get()`, else the largest. Metro 0.83.3 `src/Assets.js` records `scales`, `files` (one per scale) and intrinsic `width = firstFileWidth / scale` (→ 128). Style sets width/height explicitly, so the intrinsic size never matters.
- tsc: no `*.png` declaration needed for `require` (it returns `any`; precedent `src/theme/fonts.ts:44-46` requires `.ttf` and tsc is clean at base). `import x from '*.png'` would fail TS2307 — use `require`.
- eslint: `eslint-config-expo/flat/utils/typescript.js:84-96` `@typescript-eslint/no-require-imports` allows `\.(…|png|…)$` → no disable comment needed.
- `metro.config.js`: stock `getDefaultConfig` + `cacheVersion` only; `app.json` has no `assetBundlePatterns` / `updates.assetPatternsToBeBundled`.
- EAS Update / `expo export`: `@expo/cli` 54.0.27 `build/src/export/exportAssets.js`: `assetPatternsToBeBundled(exp)` (:97-107) is undefined here → `bundledAssetsSet` undefined → `assetShouldBeIncludedInExport` returns true for every asset (:115-118) and **every scale file** is copied (`asset.files.forEach`, :223). `@expo/metro-config` 54.0.17 `getAssets.js` hashes every scale file (`fileHashes`). So all three PNGs ship in an update; the embedded bundle (`export:embed`, Xcode build phase) copies every scale too. Proof on the real bundle = gate G10.
- Device note: on Windows, Metro may need a restart to see newly added images (RN docs `images.md`, digest).

### (h) Renderer extension (`scripts/render_myez_icons.py`, 382 lines, read in full)
Structure: `OUTPUT_NAMES = (ADAPTIVE, FAVICON_NAME, ICON, SPLASH)` (:79) drives `build_manifest` (:255), `write_outputs` (:286) and `check` (:299); `render()` (:225-247) returns a dict; manifest = `{master, outputs, params, pillow, renderer}`, `json.dumps(sort_keys=True, indent=2) + "\n"`, written `newline="\n"`, compared as parsed JSON.

**Blocker found:** `nativeBundle.w37.test.ts:376-377` (b7) pins `Object.keys(manifest.outputs).sort()` to EXACTLY the four launcher paths. Adding the mark rows to `outputs` would red b7. **Design: keep `OUTPUT_NAMES` and `outputs` exactly as they are; add two new top-level keys.**

Algorithm (from the committed master; prototype `SC/proto_mark2.py` imports the worktree renderer with bytecode writing off and calls its own `load_master`, `remove_tile_white`, `encode_png`, `RESAMPLE`):
1. `mark = remove_tile_white(master)` (unchanged U4b §4.3 step 3).
2. `left, top, right, bottom = mark.getchannel("A").getbbox()` → `(483, 399, 1629, 1641)`; `ink 1146 × 1242`.
3. `side = max(w, h) = 1242`; `ox, oy = (side−w)//2, (side−h)//2 = (48, 0)`; `square = Image.new("RGBA", (side, side), (0,0,0,0)); square.paste(mark.crop(bbox), (ox, oy))` (measured: `paste` ≡ `alpha_composite` here, `paste_equals_alpha_composite: true`; use `paste`, it is an exact copy).
4. For `(name, n)` in `MARK_SIZES = (("brand/myez-mark.png", 128), ("brand/myez-mark@2x.png", 256), ("brand/myez-mark@3x.png", 384))`: `square.resize((n, n), RESAMPLE)` (LANCZOS, premultiplied RGBA); `encode_png`.
5. Output path `output_rel(name)` = `SmartCompareApp/assets/brand/myez-mark*.png` (subdirectory `brand/` must be created: `write_outputs` does `(out_dir / name).parent.mkdir(parents=True, exist_ok=True)`, also under `--out-dir`).
6. Manifest gains (sort order puts both before `"master"`; nothing else moves):
   - `"mark_outputs"`: `{ "<rel path>": {height, mode, pixels_sha256, sha256, width} }` for the three files (same row shape as `outputs`);
   - `"mark_geometry"`: `{"ink_bbox_master_px": [483,399,1629,1641], "mark_square_master_px": [435,399,1242], "master_px": 2048, "splash_canvas_px": 1024, "splash_mark_px": 549, "splash_offset_px": 237}` — computed by the renderer from the master and the SAME `splash_scale` / `place_scaled` arithmetic it already uses (expose `n` and the offset without changing a pixel), so `--check` re-derives them.
7. `--check` iterates `OUTPUT_NAMES + MARK_NAMES` and compares the whole manifest dict (already does). Docstring: list the three new outputs and the two keys.

Prototype runs (pinned venv, twice, `SC/run1`, `SC/run2`): byte-identical (`sha256sum`, `cmp facts.json` → `FACTS_IDENTICAL`), `in_process_repeat_equal_384: true`, 1.4 s:

| file | IHDR | bytes | sha256 (file, this box) | pixels_sha256 (binding pin) | alpha bbox (≥1) | corners |
|---|---|---|---|---|---|---|
| myez-mark.png | 128² RGBA | 4,734 | `dc77ee4caed1144c9c49bd40ce48a2d4eeb264af30e4d2b64737a186bd66d5ce` | `0129d00820d78baa910ec8f50515d6cfd4ca6189283b320e51fee7f2a0f8a624` | (2,0,125,128) | (0,0,0,0)×4 |
| myez-mark@2x.png | 256² RGBA | 8,986 | `5b00db3aa4e357404dd02f4ee0ac8fa8207b7af2bdefc62b5f570753ebd21801` | `32f7c08105b36b0f1a292dba54d0925327d0ba6a31ff7686bf7f31f553a1702d` | (7,0,248,256) | (0,0,0,0)×4 |
| myez-mark@3x.png | 384² RGBA | 13,731 | `61091aa460291c4bfeec85969fcd2ad7fb32ebdd2f7429d0a6c0e2107ac06eaa` | `a06dbd98fb11d3559ef6b2b2482ca3fbce185bdf5a9c683a96735fe26777d867` | (12,0,371,384); ≥128: (15,0,369,384) | (0,0,0,0)×4 |

(They equal the earlier agent's numbers.) **Expected manifest** = `SC/expected_manifest.json` (built from the committed manifest + these rows by `SC/expected_manifest.py`): `removed lines: 0 added lines: 40`, `outputs unchanged: True params unchanged: True`. The four existing files and rows do not move by one byte: the GREEN proves it with G2/G4 (renderer `--check` still matches the committed four; `git diff` shows no change to the four PNGs; b7 green).

### (i) Legibility (contact sheets, LOOKED AT)
`SC/contact_sheet.py` → `SC/sheet_device_px.png` (every site size at true device pixels), `SC/sheet_small_zoom4.png` (24/26/28/40 magnified ×4), `SC/sheet_zoom2.png`. Device emulation: the @2x asset on 2x, @3x on 3x, scaled to `round(size·scale)` px by (a) LANCZOS (best case) and (b) point-sampled bilinear via `Image.transform` (worst case: GPU linear filter, no mipmaps), over each site's background (Welcome 40 over #F1F3FF and over white). **Verdict: the two-line MY/EZ wordmark and the emerald dot are legible at 24 pt and 28 pt at both 2x and 3x, in both filter cases** (24 pt @2x = 48 px: letters ~20 px tall, dot ~4 px, clean; the worst-case filter adds slight jaggies only). No fringe on the tint. Splash at 140 pt @3x (430-pt phones) shows a mild softening from the 1.09× upscale → OQ1. No legibility open question is needed.

### (j) Other things that would trip
- `nativeBundle.w37.test.ts` b7 (manifest `outputs` keys) — avoided by design (§2h). b14 needles stay present. w37's `sourceFiles`/`moduleSpecifiers` walk `src/` + App.tsx + index.ts for dependency specifiers; a relative `require('../../assets/…png')` matches no package (`importedDeps`, `s === dep || startsWith(dep + '/')`).
- `__tests__/helpers/w312BootSandbox.ts` stubs every module outside the boot chain (QarenLogo/Splash not on it).
- No test walks or size-budgets `assets/` (`git grep -ln "statSync|bundleSize|size-limit|\.png'" -- __tests__` → only w37, a sandbox resolver and a source walker over `src/`).
- eslint: no inline-style / unused-style rule is active (base run reports neither); `i18next/no-literal-string` + the restricted-syntax rules ban literal user-visible strings (`accessibilityLabel="MYEZ"` would fail lint — do not add one).
- Black allowlist: `.github/black-clean-paths.txt:44` already lists the renderer; `tests/test_ci_gates.py::test_black_allowlist_entries_are_actually_clean` re-checks it (G5). CI does not run the renderer.
- `brand.hardcoded.s69`: comments may keep saying Qaren; no new string literal may contain it.

---

## 3. Requirements

- **R1 Assets.** Exactly three new files `SmartCompareApp/assets/brand/myez-mark.png`, `myez-mark@2x.png`, `myez-mark@3x.png`: 128/256/384 px square, 8-bit RGBA (colour type 6), non-interlaced, chunks IHDR/IDAT…/IEND, transparent corners, decoded pixels_sha256 = §2h table (binding; file sha256 is whatever the committed bytes are and must equal the manifest). Written ONLY by the renderer.
- **R2 Renderer.** `scripts/render_myez_icons.py` extended per §2h: `OUTPUT_NAMES` literal unchanged; new `MARK_SIZES`/`MARK_NAMES`; render/write/check/manifest cover the three; manifest gains `mark_outputs` + `mark_geometry` (values §2h step 6); `outputs`, `params`, `master`, `pillow`, `renderer` unchanged. `--check` exit 0 lists 7 `pixels match` + `matches`. Stays black-clean (26.5.1) and ruff-clean; stdlib + Pillow; deterministic.
- **R3 Component contract.** `src/components/QarenLogo.tsx` keeps its path and `export default function QarenLogo`; `Props = { size?: number }` (`color` removed); default `size = 32`; module-scope `const MARK = require('../../assets/brand/myez-mark.png');` (the only `require`; no `react-native-svg`, no `expo-image`, no `tintColor` anywhere); returns exactly ONE RN `Image`:
  `<Image source={MARK} style={{ width: size, height: size }} resizeMode="contain" fadeDuration={0} accessibilityElementsHidden importantForAccessibility="no-hide-descendants" />` — no testID, no `accessible`, no label (hidden exactly as today), no RTL flip, no wrapper View.
- **R4 No fade.** `fadeDuration={0}` (Android-only prop; OTA assets are non-resource files and would fade 300 ms; iOS ignores it) — see OQ6.
- **R5 Sites.** All six sites keep `<QarenLogo size={…} />` with the sizes of §2b (Home 28, Profile 28, History 24, Step01Welcome 40, LoadingRings `Math.round(size * 0.22)`); Splash uses the layout size (R7). No other src file imports QarenLogo. No `<QarenLogo` passes `color`.
- **R6 D1.** Remove `<Animated.Text style={styles.logo}>{t('app.name')}</Animated.Text>` (Splash :113) and `<Text style={[styles.logo, styles.logoSpaced]}>{t('app.name')}</Text>` (Home :901), and the then-unused `styles.logo` (both files), `styles.logoSpaced` (Home) and `brandStack` (Splash). Keep the Home `headerLeft` View (the mark's row) and every other text (tagline, Profile name/region, History title). No i18n catalog change.
- **R7 D2.** `SplashScreen.tsx`: `const { width, height } = Dimensions.get('window'); const mark = splashMarkLayout({ width, height });` render `<View testID="splash-mark" pointerEvents="none" style={{ position: 'absolute', left: mark.left, top: mark.top, width: mark.size, height: mark.size }}><QarenLogo size={mark.size} /></View>` — a plain `View` (not Animated), physical `left` (never `start`/`end`/`right`: the native launch screen is not mirrored in RTL), no opacity, no transform, no `logoOpacity`/`logoScale`/`logoStyle`. The tagline is the ONLY animated element (same `withDelay(200, withTiming(1, { duration: 400 }))`), absolutely positioned at `top: mark.top + mark.size + spacing.lg`, `left: 0, right: 0`, `textAlign: 'center'`, `...typography.body`, `color: colors.text.secondary`. Container: `flex: 1, backgroundColor: colors.bg.primary`. Floors (MIN 700 / MAX 1500, `ready`, `finishOnce`) byte-unchanged.
- **R8 Pure layout.** New `src/utils/splashMarkLayout.ts` exactly as §2d (constants equal to `manifest.mark_geometry`; no `react-native` import; output depends only on the argument). For 390×844 → `{left: 134.675, top: 358.000, size: 126.803}` (±0.01); hand-off error vs the committed splash-icon.png ≤ 0.5 pt on the four windows.
- **R9 Snapshot.** The ONLY `.snap` change is `__tests__/hero/__snapshots__/LoadingRings.test.tsx.snap`, produced by ONE `jest --ci -u __tests__/hero/LoadingRings.test.tsx` (G7), equal byte-for-byte to the expected file of §2e (sha256 `7d22d544…9e07`).
- **R10 Untouched.** `app.json`, `eas.json`, `package.json`, `package-lock.json`, `App.tsx`, the four launcher PNGs, the master, `src/i18n/*.json`, `__mocks__/*`, `jest.config.js`, `metro.config.js`, `babel.config.js`, the 11 mocking suites, `nativeBundle.w37.test.ts`, `helpers/pngDecode.ts`, every other `.snap`, `QaranIcon.tsx`/`RevealBurst.tsx` (OQ2) — byte-unchanged. The unit stays OTA-capable (no native dependency) and is in the store binary (bundled asset).
- **R11 Hygiene.** Comments in touched files describe the MYEZ mark (the QarenLogo a11y comment :29-33 says the glyph sits beside a wordmark — update it: after D1 it does not, and the mark is decorative/hidden as before). Edits via the Edit tool; working copies are CRLF (`i/lf w/crlf`); a whole-file rewrite in `git diff --stat` is a defect (except the authorised .snap, which jest writes LF — content-only under autocrlf).

## 4. Files

**Touch (exact):**
- `scripts/render_myez_icons.py` (R2)
- `docs/brand/myez-icons.manifest.json` (renderer-written; +40 lines, 0 removed)
- `SmartCompareApp/assets/brand/myez-mark.png`, `myez-mark@2x.png`, `myez-mark@3x.png` (new, renderer-written)
- `SmartCompareApp/src/components/QarenLogo.tsx` (R3/R4)
- `SmartCompareApp/src/utils/splashMarkLayout.ts` (new, R8)
- `SmartCompareApp/src/screens/SplashScreen.tsx` (R6/R7)
- `SmartCompareApp/src/screens/HomeScreen.tsx` (R6: one Text + two styles; the header doc comment :6 may be updated)
- Tests: `__tests__/components/QarenLogo.test.tsx` (rewritten), `__tests__/SplashScreen.test.tsx` (case 1 inverted), `__tests__/components/hero/LoadingRings.test.tsx` (case 2 rewritten), `__tests__/hero/__snapshots__/LoadingRings.test.tsx.snap` (G7 only), new `__tests__/brand/inAppMark.u4c.test.ts`, new `__tests__/SplashScreen.mark.u4c.test.tsx`, new `__tests__/utils/splashMarkLayout.u4c.test.ts`.

**Must NOT change:** everything in R10, plus ProfileScreen.tsx, HistoryScreen.tsx, Step01Welcome.tsx, LoadingRings.tsx, LoadingScreenVariants.tsx, ResultsScreen.tsx (their `<QarenLogo size>` calls already satisfy R5), `.github/*`.

## 5. Tests

Helpers: decode PNGs with `__tests__/helpers/pngDecode.ts` (`readIhdr`, `decodePng`); read JSON/PNG with `fs` (never `require` a PNG/JSON for data — w37 ruling R14); AST via the installed `typescript` (as `brand.hardcoded.s69` does). Find the mark host as `root.findAll(n => typeof n.type === 'string' && n.props.accessibilityElementsHidden === true)` so the same helper finds `Svg` at base and `Image` after.

**RED (fail at base for the stated reason):**

| id | file | asserts | why red at base |
|---|---|---|---|
| A1 | components/QarenLogo.test.tsx | exactly one host `Image`; zero `Svg`/`Circle`/`Path`/`G` | renders Svg, 0 Image |
| A2 | 〃 | `size={48}` → Image `style` toEqual `{width:48,height:48}` | no Image |
| A3 | 〃 | default → `{width:32,height:32}` | no Image |
| A4 | 〃 | `resizeMode === 'contain'`, `fadeDuration === 0` | no Image |
| A5 | 〃 | `accessibilityElementsHidden === true`, `importantForAccessibility === 'no-hide-descendants'`, no `accessibilityLabel`, `accessible` not true | no Image |
| A6 | 〃 | no `tintColor` in props nor in `StyleSheet.flatten(style)` | no Image |
| A7 | 〃 | `source` toBe `require('../../assets/brand/myez-mark.png')` (path from `__tests__/components/`) — sanity only: every PNG maps to the same stub (§2f) | no Image |
| A8 | 〃 [SOURCE/AST] | QarenLogo.tsx: exactly one `require()`; arg literal `'../../assets/brand/myez-mark.png'`; `path.resolve(dirname, arg)` exists on disk; the call has no enclosing function (module scope); no import of `react-native-svg`/`expo-image`; no `color` member in `Props`; default export function named `QarenLogo` | 0 requires; svg import; `color` present |
| B1 | brand/inAppMark.u4c.test.ts | the 3 files exist; IHDR `(n,n,8,6,0)` for 128/256/384 | files missing |
| B2 | 〃 | `manifest.mark_outputs` keys = the 3 rel paths; each row's sha256 = file sha, pixels_sha256 = decoder sha, width/height/mode match | key missing |
| B3 | 〃 | decoded pixels_sha256 = the §2h binding values | files missing |
| B4 | 〃 | @3x: 4 corners alpha 0; alpha≥128 bbox top=0, bottom=384, `|left−(384−right)| ≤ 1`; ≥ 500 emerald px (G>R+60, alpha≥200) all with x≥192 and y≥192; ≥ 10,000 near-black px (max channel < 40, alpha≥200). Prototype measured: bbox (15,0,369,384), asymmetry 0; emerald 1,289 px in x 305…344, y 343…382; near-black 57,520 | missing |
| B5 | 〃 | `manifest.mark_geometry` deep-equals §2h values AND the constants exported by `src/utils/splashMarkLayout.ts` | key/module missing |
| B9 | 〃 [SITES/AST] | every `<QarenLogo>` size expression: Home `28`, Profile `28`, History `24`, Step01Welcome `40`, LoadingRings text `Math.round(size * 0.22)`, Splash NOT a numeric literal | Splash `128` |
| B10 | 〃 [D1/AST] | for every `<QarenLogo>` in src: no sibling child of its parent JSX element contains a call `t('app.name')` | Home :901, Splash :113 |
| B11 | 〃 | no src file contains `M22 22 L27 27`; QarenLogo.tsx does not import `react-native-svg` | QarenLogo.tsx |
| B13 | 〃 [SOURCE] | renderer text contains `brand/myez-mark.png`, `@2x`, `@3x`, `mark_outputs`, `mark_geometry`, and the literal `OUTPUT_NAMES = (ADAPTIVE, FAVICON_NAME, ICON, SPLASH)` | strings absent |
| C1 | SplashScreen.mark.u4c.test.tsx | testID `splash-mark` exists; flattened style = `{position:'absolute', left≈134.675, top≈358.000, width≈126.803, height≈126.803}` (±0.01, mock window 390×844); keys include `left`, exclude `start`/`end`/`right` | no testID |
| C2 | 〃 | the host Image inside `splash-mark` has width = height = the same size | no Image |
| C3 | 〃 [D2 first frame] | from the mark host up to the root: no ancestor style (flattened) has `opacity` defined and ≠ 1, nor a `transform` | brandStack `{opacity:0, transform:[{scale:0.8}]}` |
| C4 | 〃 [D1] | `queryByText('MYEZ')` null and the mocked `t` never called with `'app.name'` | wordmark rendered |
| D1 | utils/splashMarkLayout.u4c.test.ts | the §2d table for 375×667, 390×844, 393×852, 430×932 (±0.01) | module missing |
| D2 | 〃 [pixels] | decode committed `assets/splash-icon.png` and `assets/brand/myez-mark@3x.png`; alpha≥128 bboxes; native rect (aspect-fit) vs JS rect (layout + bbox·size/384): every edge ≤ 0.5 pt on the 4 windows | module + asset missing |
| D3 | 〃 [pure] | AST: no `react-native` import; two calls with the same input are deep-equal; 390×844 and 430×932 give the two table rows (argument-only) | module missing |
| E1 | SplashScreen.test.tsx (case 1 replaced) | "does not render the app name beside the mark (D1)": `queryByText('MYEZ')` null | 'MYEZ' rendered |
| F1 | components/hero/LoadingRings.test.tsx (case 2 replaced) | inside `loading-rings-logo` there is one host Image whose style width = height = 70 / 53 / 26 for size 320 / 240 / 120 | Svg, no Image |

**PIN (green at base and after):** B6 `manifest.outputs` = exactly the four rows with today's sha256/pixels_sha256 (hard-coded from the committed manifest) and `params` unchanged; B7 `app.json` icon/splash/adaptive paths, `splash.resizeMode 'contain'`, `backgroundColor '#ffffff'`, no `assetBundlePatterns`, no `expo-splash-screen` plugin, `package.json` has no `expo-image`; B8 exactly six src files import QarenLogo (AST); B12 no `<QarenLogo` passes `color`; C5 tagline `'Compare smarter'` renders and its flattened `opacity` is 0 on the first render (only the text animates); plus unchanged: SplashScreen.test cases 2-4, readyFloor.a5 (9), Step01Welcome (7), the 11 mocking suites, brand fences, i18n fences, w37 (b7 included), honestLoaders.

Counts: **RED 26** (A1–A8, B1–B5, B9–B11, B13, C1–C4, D1–D3, E1, F1); **PIN 5 new** (B6, B7, B8, B12, C5). The two LoadingRings snapshots are PIN at base and red after GREEN until G7.

**Mutants the tests must kill** (each applied to the GREEN tree, run the named file(s), restore from a byte copy and sha-compare — never `git checkout --`):

| # | mutant | killed by |
|---|---|---|
| M1 | `require('../../assets/splash-icon.png')` (wrong source; jest stub identical) | A8 |
| M2 | `resizeMode="cover"` / omitted | A4, snapshot |
| M3 | drop `accessibilityElementsHidden` or `importantForAccessibility` | A5, snapshot |
| M4 | QarenLogo back to the Svg Q-ring (or a site inlines its own Svg Q) | A1, B11, F1, snapshot |
| M5 | renderer drift: `RESAMPLE` → BICUBIC for the mark, or 1 px padding, outputs regenerated | B3 (+ B2 if not regenerated; G2 `--check`) |
| M6 | mark rows put into `outputs` (OUTPUT_NAMES extended) | w37 b7, B6, B13 |
| M7 | splash layout off by > tolerance: centred on screen (`left = (W−size)/2`, 3.1 pt off) or `top` without `(H−W)/2` | C1, D1, D2 |
| M8 | splash mark still animated (opacity 0 → 1 or scale 0.8) | C3 |
| M9 | brand text left beside the mark (Home or Splash) | B10, C4, E1 |
| M10 | `tintColor` added | A6 |
| M11 | `import { Image } from 'expo-image'` | A8 (+ B7 if the dependency is added) |
| M12 | `start:` instead of `left:` in the splash wrapper | C1 |
| M13 | `fadeDuration` removed | A4, snapshot |

## 6. GREEN gates (cheapest first; print versions first; worktree `C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b`, app `…/SmartCompareApp`)

- **G0** `git rev-parse HEAD`, `git status --porcelain`; tools exist (`node_modules/@babel/core`, `.bin/jest`); versions.
- **G1 renderer.** From the repo root: `PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 <venv python> scripts/render_myez_icons.py` (writes the 7 files + manifest), then `… --check` → exit 0, 7× `pixels match`, `myez-icons.manifest.json matches`; `… --out-dir <scratch>/g1` and `sha256sum` equal to the committed seven.
- **G2 four outputs did not move.** `git diff --exit-code -- SmartCompareApp/assets/icon.png SmartCompareApp/assets/adaptive-icon.png SmartCompareApp/assets/splash-icon.png SmartCompareApp/assets/favicon.png docs/brand/myez-icon-master-2048.png` (exit 0); `git diff -U0 docs/brand/myez-icons.manifest.json` shows only `+` lines (40), equal to `SC/expected_manifest.json` modulo the file sha256 values.
- **G3 PNGs vs manifest, independent of the renderer.** A venv one-liner: for each of the 7 manifest rows, sha256(file bytes) == `sha256`, sha256(`Image.open(f).tobytes()`) == `pixels_sha256`, size/mode match; mark pixels_sha256 == §2h.
- **G4 lint (python).** `<venv python> -m black --check scripts/render_myez_icons.py`; `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache scripts/render_myez_icons.py`.
- **G5 backend tests that read CI/black state.** `PYTHONIOENCODING=utf-8 <venv python> <scratchpad>/harness/pyt.py --bound 600 --tag u4c-ci --log <scratch>/u4c-ci.log --cwd <worktree> -- tests/test_ci_gates.py` → 0 failed; paste the `[pyt]` line.
- **G6 unit files.** `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/components/QarenLogo.test.tsx __tests__/brand/inAppMark.u4c.test.ts __tests__/SplashScreen.mark.u4c.test.tsx __tests__/utils/splashMarkLayout.u4c.test.ts __tests__/SplashScreen.test.tsx __tests__/SplashScreen.readyFloor.a5.test.tsx __tests__/components/hero/LoadingRings.test.tsx __tests__/hero/LoadingRings.animation.test.tsx __tests__/screens/onboarding/Step01Welcome.test.tsx __tests__/config/nativeBundle.w37.test.ts __tests__/brand.hardcoded.s69.test.ts __tests__/i18n/no-missing-referenced-keys.test.ts __tests__/honestLoaders.u6.test.tsx __tests__/HomeScreen.cancelCompare.a4.test.tsx` → all pass.
- **G7 the ONE authorised snapshot update (D3), run once, after the implementation is final:**
  1. byte copy the current `.snap` to scratch (Python `shutil.copyfile`, record sha256);
  2. `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci -u __tests__/hero/LoadingRings.test.tsx` → `2 snapshots updated`;
  3. sha256 of the new `.snap` MUST equal `7d22d5444df76638082781bc047c6397d091bf46793e444007b7afae79669e07` (or `669ca9d0…` if OQ6 removes `fadeDuration`); if not, STOP — no second `-u`; report the diff;
  4. `git status --porcelain -- '*.snap'` → exactly `M SmartCompareApp/__tests__/hero/__snapshots__/LoadingRings.test.tsx.snap`; `git diff --stat -- '*.snap'` → one file;
  5. paste `git diff -- SmartCompareApp/__tests__/hero/__snapshots__/LoadingRings.test.tsx.snap` into the report (must equal `SC/expected_snap_fade0.diff` hunk for hunk);
  6. re-run `jest --ci __tests__/hero/LoadingRings.test.tsx` → `3 passed`, `Snapshots: 2 passed`.
- **G8 FULL jest.** `timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci` → 0 failed; expected `Test Suites: 3 skipped, 354 passed, 354 of 357 total` (base 351 + 3 new files) and, with one `it` per id of §5, `Tests: 13 skipped, 13 todo, 3472 passed, 3498 total` (base 3448 + 24: QarenLogo.test 5 → 8 = +3; SplashScreen.test 4 → 4; components/hero/LoadingRings.test 5 → 5; new B 13 + C 5 + D 3 = +21); `Snapshots: 44 passed`. If the RED agent splits an id into several `it`s, the RED report states the new total and G8 uses it. The known flake `HistoryScreen.mobileJank.m21` is re-run once alone (RQ11).
- **G9 tsc.** `timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit` → no output, rc 0.
- **G10 eslint** on `git diff --name-only --relative` (inside SmartCompareApp) `.ts/.tsx` files → 0 errors; HomeScreen.tsx warnings ≤ 3 (base), every other file 0.
- **G11 the assets are in the bundle (offline).** From SmartCompareApp: `EXPO_OFFLINE=1 npx --no-install expo export --platform ios --dump-assetmap --output-dir <scratch>/g11-export` → `assetmap.json` has one entry `name "myez-mark"`, `type "png"`, `scales [1,2,3]`, 3 `files`; and `EXPO_OFFLINE=1 npx --no-install expo export:embed --platform ios --dev false --entry-file index.ts --bundle-output <scratch>/g11-embed/main.jsbundle --assets-dest <scratch>/g11-embed/assets` → three files under `<scratch>/g11-embed/assets` whose sha256 equal the three committed PNGs (find by sha, not by path). Afterwards `git status --porcelain` unchanged (`.expo/` and `dist/` are gitignored; outputs go to scratch only).
- **G12 untouched files.** `git diff --exit-code -- SmartCompareApp/app.json SmartCompareApp/eas.json SmartCompareApp/package.json SmartCompareApp/package-lock.json SmartCompareApp/App.tsx SmartCompareApp/src/i18n` (exit 0); `git diff --stat` lists exactly the §4 touch list; no whole-file rewrite of a CRLF file.

## 7. Risks and stated limits

- **L1** jest cannot see pixels on device: the mark's on-device sharpness and the downscale filter (RN may draw a full-size `UIImage` with Core Animation's linear filter) were emulated (§2i), not measured. Device check: Home/History/Profile headers and the loader on a 2x and a 3x iPhone.
- **L2** The white gap between the expo-updates launch-storyboard view and the first JS frame (§2d) is native behaviour this JS unit cannot remove; its length is unmeasured. First device verification on a FRESH install (U4B correction 7: iOS caches the launch snapshot). → OQ4.
- **L3** Android hand-off still jumps (200 dp legacy splash vs the iOS-derived layout); accepted for the Apple-first lane.
- **L4** The JS splash is pinned to the CURRENT renderer geometry through `mark_geometry`; any change to `SPLASH_INK_WIDTH_FRACTION` or the master changes both the native art and (through `--check`/B5/D2) the tests — by design.
- **L5** First-frame image decode: RN loads even bundled images asynchronously; the mark may appear one frame after the first layout pass. Not measurable in jest; the device check covers it.
- **L6** The reviewer and screenshots see the EMBEDDED JS: U4c must merge before the production build (digest pitfall; Guideline 2.3). After launch it ships to production by `eas update --branch production` only.
- **L7** The cut-out is exact only over white; every current site is white or #F1F3FF (≤ 0.88 level). A future dark or tinted surface (e.g. the RevealBurst #ECFDF5 badge, 1.19 levels; dark #0A0A0B, 15 levels) needs its own check.
- **L8** File sha256 values of PNGs depend on Pillow/zlib; the binding pins are `pixels_sha256` (B3) and the manifest written by the GREEN's own run.
- **Stop conditions:** the base diff of §1 is non-empty; G7's sha differs; G2 shows any change to the four launcher files; any `.snap` other than LoadingRings changes; app.json/package.json/lock change.

## 8. Open questions (each with a recommendation)

- **OQ1 — asset sizes.** On 430/440-pt 3x iPhones the splash mark is 419–429 device px drawn from the 384-px @3x asset (×1.09–1.12 upscale, mild softening seen in `SC/sheet_device_px.png`). **Recommend 144/288/432** (prototype `SC/run144`: pixels_sha256 `a357a444532fbf938c1b934778f3cde19afce73286cec4289b27a06268a7ff85` / `3ce07993badac82a3231859f5d5843d4b016934189ee4ee8b3fd177e725e1b6c` / `0df5a2a8a715f6444ee6edae3d79148b9c1c299a5e2ae5a968ae33e5002519c1`; 24 pt @2x = 6× downscale, still clean). If ruled, only R1/B1/B3/B4 numbers and `MARK_SIZES` change; the snapshot, the layout and every other test are size-independent. Otherwise keep 128/256/384 (the plan's constraint) and accept the softening.
- **OQ2 — RevealBurst's QaranIcon (old Q-magnifier, 67 pt on #ECFDF5, Results winner reveal).** **Recommend OUT of U4c**: replacing it changes `RevealBurst.test.tsx.snap` and `visual-foundation.test.tsx.snap` (D3 authorises one file), and the badge reads as a "compare/magnifier" glyph. File a follow-up issue (MYEZ dot or a neutral check in the badge) and decide before the production build if the reviewer path matters.
- **OQ3 — Android splash hand-off.** **Recommend accept** (Apple-first); the Android sizing joins the RQ5 follow-up (`expo-splash-screen` = native, next binary).
- **OQ4 — the white gap before the first JS frame.** **Recommend:** device check on a fresh install before the production build; if the gap is visible (> ~100 ms), a follow-up native unit adds `expo-splash-screen` (`preventAutoHideAsync` at module scope, `hideAsync` after SplashScreen's first layout) in the production build, which cannot ship by OTA.
- **OQ5 — accessibility after D1.** Home and Splash no longer expose any brand name to VoiceOver (the hidden mark stays hidden, per the plan). **Recommend no change** (the brand is decorative; no App Review requirement); the alternative is `accessibilityLabel={t('app.name')}` + `accessibilityRole="header"` on Home's `headerLeft` (not on the component).
- **OQ6 — `fadeDuration={0}` (R4).** Added by this spec from the measured Android fade rule; it adds one line to each snapshot hunk. **Recommend keep.** If struck, G7 expects sha `669ca9d0…` and A4/M13 drop the fade clause.
- **OQ7 — manifest layout.** New top-level keys `mark_outputs` + `mark_geometry` instead of rows in `outputs` (which w37 b7 pins to four). **Recommend as specified** (no edit to the U4b test file; the four rows and `params` stay byte-identical).
- **OQ8 — Splash tagline placement.** The spec places it 20 pt below the mark, screen-centred (the mark itself is 3 pt right of centre by design). **Recommend accept**; the alternative (centre the tagline under the mark's centre) is a one-line change.

## Review corrections (BINDING - supersede the body)

Adversarial review (Opus), 2026-10-03 08:50–09:30 AST:
- **Worktree:** `sc-s70-u4b` at `de66a25f`. `git status --porcelain` was empty before and after every measurement.
- **Spec sha256 before this section:** `a2cff0902b7fefc10156688a1d2fc3f400cf7c5af1eab9cbb2b9c371494828b7`.
- **Evidence (scratch only, `SC/review/`):**
  - `notes.md`
  - `render_ext.py` with `ext1/`, `ext2/`, `ext144/`
  - `geo_check.py` with `geo_check.log`
  - `sheet.py` and `rev_*.png`
  - `upscale.py`
  - `probe/` with `probe_run.log`
  - `tsprobe/` with `tsprobe.log`
  - `jest_base_subset.log`, `eslint_base.log`
- **Nothing was written in the worktree.** The one stray file there predates this review and the writer: `scripts/__pycache__/render_myez_icons.cpython-312.pyc` (08:15:23, gitignored). G1 keeps `PYTHONDONTWRITEBYTECODE=1`.

### Re-measured and CONFIRMED (no change)

**Sites**
- `git grep -n QarenLogo -- src App.tsx` gives exactly the six sites, at the §2b sizes.
- `__tests__/brand.hardcoded.s69.test.ts` names QarenLogo only in a comment (:8).
- The only other Q glyph is `QaranIcon` (RevealBurst:242).
- PhoneMockup's "Q-mark" exists only in its docstring (:16); the code draws none.
- No mark is rendered by App.tsx, the navigation headers, the paywall or the consent sheet.
- The backgrounds under the marks are as in §2b: the Step01 tint is `(240.7, 242.9, 255)`, and `userInterfaceStyle` is `"light"`.

**Renderer design (re-implemented independently)**
- `review/render_ext.py` runs over a byte copy of the renderer (sha `8b388402…`, same as the worktree).
- Two runs give identical bytes (`cmp e1.sha e2.sha` → `RUNS_IDENTICAL`).
- The four launcher files are byte-equal to the committed ones (`four_bytes_equal_committed: all true`, `outputs_rows_equal_committed: true`).
- The mark `pixels_sha256` values equal the §2h table. The 144/288/432 values equal OQ1's.
- The manifest equals the writer's `expected_manifest.json` (parsed). `diff` against the committed manifest gives **40 `>` lines and 0 `<` lines**.
- B4's pixel facts re-measure exactly:
  - emerald: 1,289 px in x 305…344, y 343…382
  - near-black: 57,520 px
  - α≥128 bbox `(15,0,369,384)`, asymmetry 0
  - corners `(0,0,0,0)`

**Hand-off geometry (LTR)**
- `review/geo_check.py` maps the committed `splash-icon.png` (aspect-fit, full-screen storyboard) against `myez-mark@{2x,3x}` through the §2d layout, on eight windows: 375×667@2, 390×844, 393×852, 402×874, 414×896@2, 430×932, 440×956, 320×568@2.
- α≥128 edge differences: at most **0.264 pt**.
- α≥1 differences: up to 0.90 pt. These are faint LANCZOS fringe pixels removed by the tight crop, and are invisible.
- `@expo/prebuild-config` is **54.0.9**, the copy `@expo/cli` 54.0.27 resolves (`require.resolve` → `node_modules/expo/node_modules/@expo/cli/node_modules/@expo/prebuild-config`).
- Prebuild behaviour, read from that copy:
  - `getIosSplashConfig.js:50-59`: `enableFullScreenImage_legacy: true`.
  - `InterfaceBuilder.js:73-76/87-90`: the image is 414×736, pinned top/leading/trailing/bottom to `EXPO-ContainerView`, which is the view controller's root view (`withIosSplashScreenStoryboard.js:126`).
  - `withIosSplashScreenStoryboardImage.js:46-49`: `contain` maps to `scaleAspectFit`.

**expo-updates 29.0.20**
- The deferred root view shows the same storyboard (`ExpoUpdatesReactDelegateHandler.swift:47-59`).
- `recreateRootView` sets a white background and calls `makeKeyAndVisible` (:113-116), with no loading view (`ExpoAppDelegate.swift:23-67`).
- OQ4's mechanism stands.

**Snapshot, with the REAL component**
- `review/probe/` renders a scratch component written exactly to R3 (not a mock) inside the real LoadingRings, with the same describe/it names (`--roots <scratch> --modulePaths <app>/node_modules --ci=false`).
- The written `.snap` has sha256 **`7d22d5444df76638082781bc047c6397d091bf46793e444007b7afae79669e07`**, identical to §2e.
- All 17 tracked `.snap` files have their test file. There are no inline snapshots.
- Only `LoadingRings.test.tsx.snap` holds the mark subtree (`git grep -c` over `*.snap`). It has exactly 2 keys for 2 `toMatchSnapshot` calls, so `-u` leaves no obsolete key.

**Base subset**
- Command: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci` over SplashScreen, readyFloor.a5, QarenLogo, both LoadingRings files, LoadingRings.animation, Step01Welcome, brand.hardcoded.s69, brand.myez.s69, no-missing-referenced-keys, no-deleted-keys, honestLoaders.u6, HomeScreen.cancelCompare.a4 and nativeBundle.w37.
- Result: `Test Suites: 14 passed` / `Tests: 125 passed` / `Snapshots: 2 passed`, rc 0.
- No fence requires `t('app.name')` in Home or Splash. No unused-key fence exists.
- w37 b7 pins only `Object.keys(manifest.outputs)` (`nativeBundle.w37.test.ts:377`), not the top-level keys.

**jest / tsc / eslint**
- jest: the stub mapping is confirmed (`jest.config.js` moduleNameMapper → `fileStub.ts`, `export default 0`).
- jest: the suites that mock `react-native` wholesale cannot break on the new `Image`. `HomeScreen.test.ts` does not import a mark site. `aiProcessingConsent.s69` keeps `requireActual` and mocks QarenLogo anyway.
- jest: no test counts `Svg` or `Image` hosts on the six sites.
- tsc: `tsc -p review/tsprobe` over the R3, R7 and layout shapes (static `require` of a PNG, `fadeDuration`) exits rc 0.
- eslint: the base run on QarenLogo, Splash and Home gives `0 errors, 3 warnings` (HomeScreen 65-66).
- eslint: `@typescript-eslint/no-require-imports` allows `\.png$` (`eslint-config-expo/flat/utils/typescript.js:84-96`).

**OTA and caching**
- `exportAssets.js:97-118,210-235` (cli 54.0.27) copies every scale file when `assetPatternsToBeBundled` is unset.
- With an OTA running, `expo-asset` resolves assets to content-hash file URIs (`Asset.fx.js:5-27`, `LocalAssets.js:7-20`). The embedded bundle uses RN's bundle URL (`PlatformUtils.js:18-25`).
- A changed PNG therefore always gets a new URI, so a stale image cache after an OTA is not possible.
- Android's 300 ms fade rule is confirmed (`ReactImageView.kt:425-426`).
- On iOS, an Image is accessible only when `alt` is set (`Image.ios.js:178`). "Hidden exactly as today" holds without `accessible`.

**Legibility (LOOKED AT)**
- Sheets: `review/rev_24_28_at3x_zoom6.png` and `review/rev_sheet_device_px.png`, at 24, 26, 28, 40 and 53 pt, 2x and 3x.
- Each is drawn twice: LANCZOS, and point-sampled bilinear with no prefilter.
- MY/EZ and the dot read clearly in every cell. The worst-case filter adds only slight stair-stepping on the diagonals.
- **A user can read the mark at 24 pt and at 28 pt.**

### Corrections

1. **(MAJOR) R7's "physical `left`" lands MIRRORED for Arabic users, 6 pt away from the launch mark.**

   React Native swaps `left`/`right` under RTL by default. Measured:
   - `RCTI18nUtil.m:20`: `[sharedInstance swapLeftAndRightInRTL:true]`.
   - `RCTFabricSurface.mm:181`: `layoutContext.swapLeftAndRightInRTL = isRTL && doLeftAndRightSwapInRTL`.
   - `YogaLayoutableShadowNode.cpp:596,912-917`: `position(Left)` becomes `Start`, applied recursively.
   - Android: `I18nUtil.kt:47-48`, default `true`.
   - The app forces RTL for `ar` (`src/i18n/rtlBootstrap.ts:47-48`, `src/hooks/useLanguage.ts:18-19`) and never calls `swapLeftAndRightInRTL(false)`. The header of the repo's own `__tests__/rtl/textAlignLogical.contract.test.ts` records the same fact.

   The native launch screen is a full-width aspect-fit image and is not mirrored. The R7 wrapper `left: mark.left`, though, lays out as `start` and lands at `W − left − size`. The error per window:
   - 375×667: **−5.917 pt**
   - 390×844: **−6.153 pt**
   - 393×852: −6.201 pt
   - 430×932: −6.784 pt
   - 440×956: −6.942 pt

   That is a visible horizontal jump at the hand-off, which D2 forbids.

   **Replace R7's left clause:**
   - In `SplashScreen.tsx`, compute `const mirrored = I18nManager.isRTL && I18nManager.doLeftAndRightSwapInRTL !== false;` and set `left: mirrored ? width - mark.left - mark.size : mark.left`. Add a comment that cites the swap.
   - `splashMarkLayout` stays physical and pure, so R8 and the D1/D2/D3 tests are unchanged.
   - `!== false` matches RN's default (`I18nManager.js:26`) and the jest mock, which has no `doLeftAndRightSwapInRTL`.
   - Still never use `start`, `end` or `right`.
   - The tagline (`left: 0, right: 0, textAlign: 'center'`) is symmetric and needs no change.

   **New RED C6** (in `SplashScreen.mark.u4c.test.tsx`):
   - Set `(I18nManager as any).isRTL = true`, as `TwoInputShell.rtl.test.tsx` does, and restore it in `afterEach`.
   - Expect the flattened `left` ≈ **128.522** (±0.01), with `top` and `width` as in C1.
   - It is red at base because the testID does not exist.

   **New mutants:**
   - **M14**, no mirroring: killed by C6.
   - **M15**, mirroring applied in LTR as well: killed by C1.

2. **Wrong REDs: A5 and A6 pass at base.**

   §5's helper (`findAll(n => typeof n.type === 'string' && n.props.accessibilityElementsHidden === true)`) finds the base `Svg`. The probe (`review/probe_run.log`) reports, for the base QarenLogo, `"base":[{"type":"Svg","a11y":true,"ifa":"no-hide-descendants"}]`, with no label, no `accessible` and no `tintColor`. So A5's a11y assertions and A6's no-tint assertion PASS at base.

   **Binding:**
   - A2–A7 and C2 each first assert exactly one host with `type === 'Image'` (`root.findAll(n => n.type === 'Image')`), and read every prop from that host.
   - The a11y helper is used only for A1's "zero Svg" half.
   - The RED report must show A5 and A6 failing because there is no Image.

3. **Wrong PINs: B5 must not import the missing module at file top.**

   `brand/inAppMark.u4c.test.ts` carries the PINs B6, B7, B8 and B12 next to B5. A top-level `import … from '../../src/utils/splashMarkLayout'` fails the whole file at base with `Cannot find module`, the same failure the probe hit for an unresolvable import. That would make the PINs red.

   **Binding:**
   - B5 loads the constants inside its own `it` (`jest.requireActual` or `require` in the test body), or reads them from the TS AST.
   - B2, B3 and B4 read files with `fs` inside their `it`.
   - Every PIN in that file must be green at base in the RED report.

4. **B10 can be escaped; strengthen it.**

   Mutant: Home keeps `<Text>{t('app.name')}</Text>` but moves it from `headerLeft` into the `header` row. It is then not a sibling of `<QarenLogo>`, so B10 passes. No Home render test asserts that the text is gone, because the 11 Home suites mock both `t` and the logo.

   **Binding:**
   - B10 also asserts, through the TS AST, ZERO call expressions `t('app.name')` in `SplashScreen.tsx` and in `HomeScreen.tsx`.
   - At base there is one in each (`git grep -n "app\.name" -- src`: `HomeScreen.tsx:901`, `SplashScreen.tsx:113`), so the assertion is red at base for the stated reason.
   - The other `app.name` sites are untouched: App.tsx:140, ForgotPassword:87, Register:293/324, ReferralLanding:174, Step17:90.

5. **C3 misses layout animations.**

   The reanimated mock exports `FadeIn` (`__mocks__/react-native-reanimated.ts:82`). Its `Animated.View` is the RN host `View` (:9), so an `entering` prop reaches the host props. Mutant: `<Animated.View entering={FadeIn}>` around the mark passes C3 as written.

   **Binding:**
   - C3 also asserts that no host from the mark up to the root carries `entering`, `exiting` or `layout`.
   - Add mutant **M16**, `entering={FadeIn}` on the wrapper, killed by C3.

6. **OQ1's premise is inverted: keep 128/256/384.**

   The native launch screen draws the mark from `splash-icon.png`. The mark square there is `1242·549/2048 = 332.9 px`, which 3x phones UPSCALE: ×1.14 at 390 pt (380 px) up to ×1.29 at 440 pt (429 px). The JS @3x asset is 384 px, drawn at ×0.99–1.12, so the JS frame is always the sharper one.

   `review/rev_splash430_native_vs384_vs432.png` (430 pt, bilinear, device px, LOOKED AT): native, 384 and 432 are indistinguishable at 1:1, and the native frame is the softest.

   The spec also missed 414×896@2x, which draws 269.2 px from the 256 asset (×1.05). That is equally negligible.

   **Binding:** `MARK_SIZES` stays 128/256/384 (the plan). R1, B1, B3 and B4 are unchanged.

7. **L5 is a measured mechanism, and it shapes OQ4's follow-up.**

   Fabric requests every image on a background queue (`RCTImageManager.mm:67`, `dispatch_async(_backgroundSerialQueue, …)`). The loader differs by source:
   - embedded bundle: `RCTLocalAssetImageLoader` (`requiresScheduling NO`, `imageNamed`);
   - OTA: an async file URL.

   Either way, the mark's pixels arrive at least one frame after the JS splash's first commit. The base `Svg` draws on mount. U4c therefore adds at least one blank frame at the hand-off, on top of the expo-updates white gap (L2). jest cannot test this.

   **Binding additions to §7 and OQ4:**
   - (a) The device check records whether a blank or white flash is visible between the launch screen and the JS mark: once on a fresh install (embedded bundle), once after an OTA.
   - (b) A future `expo-splash-screen` unit must call `hideAsync()` from the mark `Image`'s `onLoad`, not from the first layout.
   - (c) That unit must also pass `enableFullScreenImage_legacy: true` to the plugin (props branch, `getIosSplashConfig.js:13-29`). Otherwise the native splash geometry changes, and R8 and D2 with it.

8. **G7 pre-step: orphan snapshot files.**

   `jest -u` with any path filter still runs `jest-snapshot` `cleanup()` over the whole haste FS (`@jest/core/build/TestScheduler.js:190`). When `updateSnapshot === 'all'`, it unlinks every `.snap` whose test file is missing (`jest-snapshot/build/index.js:186-188`). Today there are 17 tracked `.snap` files and 0 orphans.

   **Binding:**
   - G7 step 0 lists every `.snap` under `SmartCompareApp` (excluding `node_modules`) and confirms each has its test file.
   - If any orphan exists, STOP before `-u`, because it would be deleted.
   - Step 4's `git status -- '*.snap'` check stays.

9. **Cross-reference fix.**
   - §2g says "Proof on the real bundle = gate G10". The bundle gate is **G11**; G10 is eslint.
   - G11 is network-free as written: `EXPO_OFFLINE=1` also disables CLI telemetry (`@expo/cli/build/src/utils/telemetry/index.js:39`).

10. **G8 totals.**
    - Corrections 1 and 5 give the new splash file C1–C6, and add assertions to B10 and C3.
    - The RED report therefore restates the expected `Tests:` total from its own `it` count.
    - The base arithmetic (3448 / 3474 tests, 351 → 354 suites) is confirmed and stays the anchor.

11. **(Low; device check only) The Home header loses 2 pt.**
    - After D1, `headerLeft` holds only the 28 pt mark.
    - The row loses the `typography.title` text (lineHeight `20*1.5 = 30`), so the header shrinks from 30 to 28 pt and everything below moves up 2 pt.
    - Add this to the L1 device check. No test.

12. **(Low; record only) Text-only logos outside D1.**
    - `ForgotPasswordScreen.tsx:87` and `RegisterScreen.tsx:293/324` render `t('app.name')` as a TEXT logo, with no mark beside it.
    - D1 covers only text adjacent to the mark, so these are out of scope, and U4c leaves them unchanged.
    - The orchestrator may file a follow-up if those screens should show the mark.

### Answers to the writer's open questions (RECOMMENDATIONS; the orchestrator rules)

- **OQ1 → REJECT; keep 128/256/384** (correction 6). The native launch frame is the softer image (×1.14–1.29 upscale), and the 384 @3x asset is already sharper at the hand-off. The 432 prototype shows no visible gain.
- **OQ2 → AGREE: keep it OUT of U4c, and file the follow-up now.**
  - RevealBurst's `QaranIcon` is in the Results winner reveal, which App Review sees on every compare.
  - Replacing it needs its own snapshot authorisation (the RevealBurst and visual-foundation snapshots), which D3 does not give.
  - Decide before the production build.
- **OQ3 → AGREE: accept** for the Apple-first lane, and add it to the RQ5 follow-up. Not re-measured here beyond U4B correction 6.
- **OQ4 → AGREE, sharpened** (correction 7).
  - The gap exists TODAY, independent of U4c, so it can be measured now on the current preview binary with a fresh install.
  - The production binary is not built yet. If the gap is visible, a native `expo-splash-screen` unit (legacy full-screen option, `hideAsync` on the mark's `onLoad`) has to land before that build, or else wait for the next binary.
  - U4c itself stays JS-only.
- **OQ5 → AGREE: no change.** The mark stays hidden. No test or eslint rule requires a label, and a literal label would fail `no-restricted-syntax` (`eslint.config.js:38-39` `LETTERS` / `USER_VISIBLE_ATTRS` and the `restrictedLiteralSyntax` selector below them).
- **OQ6 → AGREE: keep `fadeDuration={0}`.** The fade is measured (`ReactImageView.kt:425-426`), and OTA assets are file URIs (`Asset.fx.js:18`). The G7 sha stays `7d22d544…`, re-confirmed with the real component.
- **OQ7 → AGREE.** b7 pins only the `outputs` keys (`:377`). The two new top-level keys add 40 lines and remove 0 (re-measured).
- **OQ8 → AGREE: accept.** The screen-centred tagline is symmetric under RTL (`left: 0, right: 0`), so correction 1 needs nothing extra for it.

**Verdict: APPROVED_WITH_CORRECTIONS.**
- These re-measure as stated: the asset pipeline, the renderer extension, the snapshot, the LTR geometry, the OTA and store-binary claims, and legibility.
- The design defect is correction 1: the splash mark is mirrored under RTL.
- Corrections 2–5 fix wrong REDs, wrong PINs and unkilled mutants in the test list.
- The remaining corrections are gates and stated limits.

---

## Orchestrator rulings (BINDING - supersede the review corrections and the body)

Fable orchestrator, session 71, 2026-10-03 09:17 +03. The spec body and the review section (file sha256 `f3b00c24...` after the reviewer's append) were read. Verdict: ACCEPTED with the rulings below. RED may start. Precedence: these rulings, then the review corrections, then the body. Agents never edit this spec.

- **UR1 - base and worktree.** U4c is built in `C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b` on branch `feature/s71-u4c-inapp-mark`, cut from main `eb86075e` (PR #279 merged). Measured: `git diff --stat de66a25f eb86075e` is empty, so every anchor recorded at `de66a25f` holds. The worktree keeps its real `node_modules`, which matches the lock on main.
- **UR2 (OQ1, correction 6) - asset sizes stay 128 / 256 / 384.** The reviewer measured that the JS frame is already the sharper of the two; 144/288/432 is rejected.
- **UR3 (OQ2, correction 12) - OUT of U4c:** the `QaranIcon` Q-magnifier in `RevealBurst` and the text-only `t('app.name')` logos on ForgotPassword and Register. One follow-up issue, filed by the orchestrator now. Replacing `QaranIcon` changes two more snapshot files, which needs Ahmed's own authorisation; D3 covers the `LoadingRings` file only.
- **UR4 (OQ3) - the Android hand-off jump is accepted** for the Apple-first lane and joins issue #281.
- **UR5 (OQ4, corrections 7 and 11) - device checks are release items, not code:** the white gap before the first JS frame, the one-frame image decode on a fresh install and after an OTA, and the 2 pt Home header shift. They go into the PR body and the launch runbook. Any later `expo-splash-screen` unit calls `hideAsync` from the mark's `onLoad` and sets `enableFullScreenImage_legacy: true`.
- **UR6 (OQ5) - no VoiceOver change.** The mark stays hidden from accessibility exactly as today.
- **UR7 (OQ6) - `fadeDuration={0}` stays.** The expected snapshot sha is `7d22d5444df76638082781bc047c6397d091bf46793e444007b7afae79669e07`.
- **UR8 (OQ7) - manifest layout as specified:** new top-level keys `mark_outputs` and `mark_geometry`; `outputs`, `params`, `OUTPUT_NAMES` and the four launcher files do not move by one byte.
- **UR9 (OQ8) - the tagline placement is as specified** (20 pt below the mark, centred on the screen).
- **UR10 (correction 1) - the RTL compensation is accepted exactly as the reviewer wrote it.** `splashMarkLayout` stays physical and pure. `SplashScreen` computes `left` at RENDER time: `(I18nManager.isRTL && I18nManager.doLeftAndRightSwapInRTL !== false) ? width - mark.left - mark.size : mark.left`. The read happens inside the component body, never in a module-scope `StyleSheet.create` or constant: a module-scope value is frozen at import, before a test can flip the mocked `I18nManager`, and that is how the earlier `textAlign` double-flip stayed green. RED C6 and mutants M14 and M15 are added as the correction states.
- **UR11 - corrections 2, 3, 4, 5, 8, 9 and 10 are ACCEPTED as written** and are binding: the host-`Image` precondition for A2-A7 and C2; B5 loads the layout module inside its own `it`; the AST assertion of zero `t('app.name')` calls in `SplashScreen.tsx` and `HomeScreen.tsx`; C3 also rejects `entering` / `exiting` / `layout` on any host from the mark to the root (mutant M16); G7 step 0 checks for orphan `.snap` files and stops if any exist; the G10/G11 reference fix; the RED report restates the expected full-suite totals.
- **UR12 - the single authorised snapshot update (D3)** is run by the GREEN agent, exactly once, by the G7 procedure. The RED agent never runs `jest -u` and changes no `.snap`. A sha different from UR7's is a STOP, not a second `-u`.
- **UR13 - roles.** Every agent is Opus. The RED agent writes ONLY test files: the three new files (`__tests__/brand/inAppMark.u4c.test.ts`, `__tests__/SplashScreen.mark.u4c.test.tsx`, `__tests__/utils/splashMarkLayout.u4c.test.ts`) and the three edits section 4 names (`__tests__/components/QarenLogo.test.tsx`, case 1 of `__tests__/SplashScreen.test.tsx`, case 2 of `__tests__/components/hero/LoadingRings.test.tsx`). It edits nothing under `src/`, `assets/`, `scripts/` or `docs/brand/`. The RED files are frozen after the orchestrator's gate; GREEN is a separate launch.
- **UR14 - no new test may import a module this unit creates at file top** (`src/utils/splashMarkLayout`): a RED is a failing test, never a suite that cannot load, so the PINs in the same file stay green at base.
- **UR15 - PR wording.** The unit is OTA-capable (no native dependency, `app.json` / `eas.json` / `package.json` / the lock unchanged) AND must be in the store binary, so it merges before the production build.

---

## Orchestrator gate on the RED tests (BINDING - supersedes everything above where they differ)

Fable orchestrator, session 71, 2026-10-03 09:44 +03. Verdict: **PASS, no change**. GREEN may start.

Reviewed (sha256 prefixes): `__tests__/components/QarenLogo.test.tsx` `d9241b8cea42`, `__tests__/SplashScreen.test.tsx` `c23f00d8e19b`, `__tests__/components/hero/LoadingRings.test.tsx` `061dfb0868e9`, `__tests__/brand/inAppMark.u4c.test.ts` `ca1d728067fd`, `__tests__/SplashScreen.mark.u4c.test.tsx` `4993e2cf25c5`, `__tests__/utils/splashMarkLayout.u4c.test.ts` `85bfc54fbe15`. Measured by the RED agent at base `eb86075e`: exactly 27 tests fail (A1-A8, B1-B5, B9-B11, B13, C1-C4, C6, D1-D3, E1, F1), each for its stated reason; the five PINs pass; the neighbour set and the FULL suite show no other failure (3446 passed, 27 failed, 3499 total, 44 snapshots passed); tsc and eslint clean; no `.snap`, no file under `src/`, `assets/`, `scripts/` changed. A scratch prototype passed all 39 tests and 22 simulated mutants were killed. The orchestrator read the splash test file in full.

- **UG1 - the RED deviations are accepted:** C3 finds the mark through the accessibility-hidden host so it fails at base for its stated reason; the local structural node type; `jest.requireActual` inside the test body; the `near(x, 0.01)` matcher; the deep style flatten; the stricter B6, B7 and B12; F1 passing the size explicitly.
- **UG2 - the splash wrapper's style keys are exactly `position`, `left`, `top`, `width`, `height`** (C1 and C6 pin the key set). `pointerEvents` and `testID` are props, not style keys. A GREEN that needs another style key on that wrapper is wrong.
- **UG3 - the six RED files are FROZEN.** A test edit needs a test defect proven by measurement and is reported as a deviation.
- **UG4 - the GREEN target** after the one authorised snapshot update: Test Suites 3 skipped, 354 passed, 354 of 357 total; Tests 13 skipped, 13 todo, 3473 passed, 3499 total; Snapshots 44 passed.
- **UG5 - `B6` pins `manifest.pillow` to `12.3.0`:** the renderer is run only with the pinned venv.
