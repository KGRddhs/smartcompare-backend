# U4b — Expo SDK 54 patch bumps, gesture-handler removal, MYEZ launcher art — unit spec

**Session 70, 2026-09-30.** Apple launch lane, runbook §4 row U4 (the deferred half of U4a; `U4A_NATIVE_CONFIG_SPEC.md` R-C) and `2026-09-29-session-69-state/NEXT_SESSION_PROMPT.md` §4 "U4b". Owner: Claude. Decision D4 (Ahmed): the icon art is the ORIGINAL master `C:/Users/SynAckITPC/Downloads/MYEZ-icon-white-2048.png`; candidate E in `icon-candidates/` is superseded and is not an input.

**OTA class: NATIVE.** Every dependency bump, the gesture-handler removal and every launcher PNG reach users only through `eas build` (the production profile listens on the `production` channel, which has never received an update). Identifiers stay `qaren` (bundle id `com.qaren.app`, slug `qaren`, scheme `qaren://`).

Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b`, branch `feature/s70-u4b-icons-deps`. It has its OWN real `SmartCompareApp/node_modules` (`npm ci`, not a junction), so the package-manager commands in §3 touch nothing outside it.

---

## 0. Base SHA

`94c097cda4e3d63562c5e40e444f4965c4a0222d` — main, 2026-09-29 16:55:37 +0300, "Merge pull request #276 from KGRddhs/docs/session-69-close". `git rev-parse HEAD` in the worktree printed exactly this at the start of measurement (2026-09-30 03:03 AST); the worktree was clean (`git status --short` empty).

Every anchor below is at this SHA. Re-anchor by symbol, not by line number, if main moves.

---

## 1. Measured facts

Toolchain (printed, not assumed): `node --version` → `v24.11.1`; `npm --version` → `11.6.2`; `node node_modules/expo/bin/cli --version` → `54.0.24` (the `@expo/cli` that ships with the installed `expo 54.0.34`); `node node_modules/jest/bin/jest.js --version` → `29.7.0`; venv `python -c "import PIL; print(PIL.__version__)"` → `12.3.0` (= the pin `requirements-dev.txt:78 pillow==12.3.0`).

Scratch evidence (session-temporary, NOT in the repo): `…/scratchpad/u4b/` — `notes.md`, `npm_view.txt`, `pkgdiff_report.txt`, `changelog_new_sections.txt`, `png_facts.json`, `introspect_base.json`, `proto/` (the render prototype and its outputs), `jest_base_run3.log`.

### 1.1 The drift list (`npx expo install --check`)

```
$ cd SmartCompareApp && npx --no-install expo install --check
The following packages should be updated for best compatibility with the installed expo version:
  expo@54.0.34 - expected version: ~54.0.37
  expo-font@14.0.11 - expected version: ~14.0.12
  expo-localization@17.0.8 - expected version: ~17.0.9
  expo-screen-capture@8.0.9 - expected version: ~8.0.10
  expo-updates@29.0.17 - expected version: ~29.0.20
  react-native-svg@15.15.5 - expected version: 15.12.1
  eslint-config-expo@55.0.1 - expected version: ~10.0.0
Your project may not work correctly until you install the expected versions of the packages.
Found outdated dependencies
```

Seven rows: five patch-level behind, `react-native-svg` minor-level AHEAD (installed 15.15.5 from `package.json` `"^15.12.1"`; SDK 54 expects exact `15.12.1`), and `eslint-config-expo` on the SDK-55 line (`"^55.0.0"` → 55.0.1; SDK 54 expects `~10.0.0`). The last row is NOT in the runbook — §8 Q1.

`package.json` has **no `"expo"` key** at base, so there is no `expo.install.exclude`.

**The expected `expo` version comes from the Expo API, not from the lockfile.** Offline, the same command reads only the installed `expo`'s `bundledNativeModules.json`:

```
$ EXPO_OFFLINE=1 npx --no-install expo install --check
Dependency validation is unreliable in offline-mode
The following packages should be updated for best compatibility with the installed expo version:
  react-native-svg@15.15.5 - expected version: 15.12.1
  eslint-config-expo@55.0.1 - expected version: ~10.0.0
```

(`@expo/cli/build/src/start/doctor/dependencies/bundledNativeModules.js:84` — remote versions unless `EXPO_OFFLINE`.) SDK-54 `expo` publish dates (`npm view expo time`): 54.0.34 2026-04-27, 54.0.35 2026-05-28, 54.0.36 2026-07-15, 54.0.37 2026-08-17 (`dist-tags.sdk-54` = `54.0.37`). A blocking ONLINE check goes red on an unchanged main each time Expo ships an SDK-54 patch — §8 Q3.

### 1.2 `bundledNativeModules.json`, installed expo 54.0.34 vs target 54.0.37

Every name the app declares that either file lists (`node -e` over both files and `package.json`):

| package | package.json | installed | bundled @54.0.34 | bundled @54.0.37 |
|---|---|---|---|---|
| expo-font | ~14.0.11 | 14.0.11 | ~14.0.11 | **~14.0.12** |
| expo-localization | ~17.0.8 | 17.0.8 | ~17.0.8 | **~17.0.9** |
| expo-screen-capture | ~8.0.9 | 8.0.9 | ~8.0.9 | **~8.0.10** |
| expo-updates | ~29.0.17 | 29.0.17 | ~29.0.17 | **~29.0.20** |
| react-native-svg | ^15.12.1 | 15.15.5 | 15.12.1 | 15.12.1 |
| eslint-config-expo (dev) | ^55.0.0 | 55.0.1 | ~10.0.0 | ~10.0.0 |
| react-native-gesture-handler | ~2.28.0 | 2.28.0 | ~2.28.0 | ~2.28.0 |
| 22 others (async-storage, sentry, camera, crypto, notifications, reanimated, screens, react, react-native, worklets, …) | — | satisfy both | unchanged | unchanged |

Keys that change between the two files: `expo-constants ~18.0.13→~18.0.14`, `expo-file-system ~19.0.22→~19.0.24`, `expo-font`, `expo-local-authentication`, `expo-localization`, `expo-router`, `expo-screen-capture`, `expo-server`, `expo-updates ~29.0.17→~29.0.20`, `jest-expo`. `expo-constants` and `expo-file-system` are not declared by the app; they arrive transitively through `expo 54.0.37`'s own `dependencies` (below).

`expo 54.0.37`'s `dependencies` vs the installed 54.0.34's (`npm view expo@54.0.37 dependencies` vs `node_modules/expo/package.json`): `@expo/cli 54.0.24→54.0.27`, `@expo/config ~12.0.13→~12.0.14`, `@expo/config-plugins ~54.0.4→~54.0.5`, `@expo/metro-config 54.0.15→54.0.17`, `babel-preset-expo ~54.0.10→~54.0.12`, `expo-constants ~18.0.13→~18.0.14`, `expo-file-system ~19.0.22→~19.0.24`, `expo-font ~14.0.11→~14.0.12`, `expo-modules-autolinking 3.0.25→3.0.27`; `expo-modules-core 3.0.30`, `expo-asset ~12.0.13`, `expo-keep-awake ~15.0.8`, `@expo/fingerprint 0.15.5` UNCHANGED. `react-native` stays `0.81.5`.

### 1.3 What the target versions change (tarball diff, installed vs target)

Method: `npm pack --prefer-offline <pkg>@<target>` into the scratchpad (a read of public tarballs; nothing installed), extracted with Python `tarfile`, every file sha256-compared against `SmartCompareApp/node_modules/<pkg>` (`pkgdiff.py`, report `pkgdiff_report.txt`). "Native" = `ios/`, `android/`, `*.swift|m|mm|h|kt|java|podspec|gradle`, `expo-module.config.json`. The `local-maven-repo/<ver>/` add/remove pairs (prebuilt Android AARs renamed by version) are omitted below.

| package | native files changed | runtime-JS (bundled) files changed | CHANGELOG entries in the target tarball |
|---|---|---|---|
| expo 54.0.34→54.0.37 | `android/src/main/java/expo/modules/fetch/NativeResponse.kt` (response closed off the modules queue, NonCancellable), `android/build.gradle`. **iOS native: none.** | `src/winter/TextDecoder.ts` rewritten (pure JS UTF-8 polyfill; zero `require`/`import`/`global` references in the new file; installed lazily by `src/winter/runtime.native.ts:8`) | none shipped in the tarball |
| expo-font 14.0.11→14.0.12 | `android/build.gradle`, `expo-module.config.json` (version string only) | `src/ExpoFontLoader.web.ts` (web only); config plugin `plugin/src/withFontsAndroid.ts` (build time) | "Sanitize values in web font loader and Android config plugin (#45887)" |
| expo-localization 17.0.8→17.0.9 | `android/build.gradle`, `expo-module.config.json` (version only) | none; config plugin `plugin/src/withExpoLocalization.ts` (build time) | "Prevalidate locale strings in config-plugin (#45888)" |
| expo-screen-capture 8.0.9→8.0.10 | **`ios/ScreenCaptureModule.swift`**: `allowScreenCapture` now also calls `self.blockView.removeFromSuperview()`; `android/build.gradle`; `expo-module.config.json` | none | "[iOS] Fixed the screen-recording overlay staying attached (permanent black screen) after `allowScreenCaptureAsync` is called while a recording is active (#48000)" — the app calls `usePreventScreenCapture()` on 4 screens (`ForgotPasswordScreen.tsx:33`, `LoginScreen.tsx:194`, `RegisterScreen.tsx:40`, `ResetPasswordScreen.tsx:54`), whose unmount calls `allowScreenCaptureAsync` |
| expo-updates 29.0.17→29.0.20 | **16 native files** (iOS `AppLauncherWithDatabase`, `EmbeddedAppLoader`, `RemoteAppLoader`, `UpdatesDatabase`, `UpdatesReaper`, `Update`, `UpdatesError`, `UpdatesStateMachine`, `UpdatesUtils`, `EXUpdates.podspec`; Android `UpdatesUtils`, `Reaper`, `FileDownloader`, `ExpoUpdatesUpdate`, `UpdatesStateMachine`, `build.gradle`) + a new iOS test file | none (only `cli/` code-signing and `utils/` find-up, both build-time tooling) | 29.0.20: "Reject updates whose asset key or file extension contains a path separator, which previously let a manifest write and delete files outside the updates directory (#48762, #48763)"; iOS script_phase `always_out_of_date`. 29.0.19: internal find-up. 29.0.18: CLI private key owner-only permissions; no logging on download progress |
| expo-file-system 19.0.22→19.0.24 (transitive) | Android `FileSystemDirectory/Module/Path.kt`, `legacy/FileSystemLegacyModule.kt`, iOS `Legacy/FileSystemHelpers.swift`, gradle, module config | none | Android path-traversal fixes in `createFile/createDirectory/rename`, missing permission check in `delete()`, Expo Go path change; iOS `copyAsync` of edited `ph://` assets |
| expo-constants 18.0.13→18.0.14 (transitive) | `android/build.gradle` only | none | "does not introduce any user-facing changes" |
| expo-modules-autolinking 3.0.25→3.0.27 | none | none (build-time JS: Android gradle `sourceDir` symlinks; devtools plugin bounds) | #48495, #45841 |
| babel-preset-expo 54.0.10→54.0.12 | none | none (`build/common.js`: expo-router root path must stay inside the project; the app has no expo-router) | none shipped |
| @expo/metro-config 54.0.15→54.0.17 | none | none (`ExpoMetroConfig.js` `getPkgVersion` moved to a util; web `<link>` CSS attribute escaping; `sideEffects.js` import path) | — |

Config-plugin deltas that read `app.json` (diffed `plugin/src/*.ts`): `expo-localization` now throws unless every `supportedLocales` entry is a BCP-47 tag (`new Intl.Locale(tag)`) — the app's `en` / `ar` pass, and U4a's u6/u7/u12 execute the INSTALLED plugin in memory, so G6 re-proves it after the bump; `expo-font`'s Android plugin now `JSON.stringify`s the family name in the generated `addCustomFont` call.

`expo-modules-core` is 3.0.30 on both sides; no bumped package's JS calls a native method that the installed native side lacks (the only runtime-bundled JS delta is the self-contained `TextDecoder` polyfill). `@expo/cli 54.0.27` (the CLI that `eas update` / `expo export` would run) was NOT diffed — stated limit §7.

### 1.4 `eslint-config-expo` 10.0.0 vs 55.0.1 — content-identical

The tarball diff finds exactly ONE changed file, `package.json`:

```
$ diff node_modules/eslint-config-expo/package.json <10.0.0 tarball>/package.json
3c3   "version": "55.0.1"            →  "version": "10.0.0"
42c42 "eslint-plugin-expo": "^1.0.3" →  "eslint-plugin-expo": "^1.0.0"
57c57 gitHead 0675db12…              →  gitHead cb7062e2…
```

`flat.js`, `default.js`, `flat/*`, `utils/*` are byte-identical. Installed `eslint-plugin-expo` is `1.0.3`, which satisfies both ranges, so npm keeps it. `eslint.config.js:6` consumes `require('eslint-config-expo/flat')`. The dependency was added as `"^55.0.0"` in `84a4fd24` (2026-05-11, "feat(lint): ESLint 9 flat config …"). Both versions peer on `eslint >=8.10` (installed 9.39.4).

### 1.5 `react-native-svg`

`package.json:53` `"^15.12.1"` → installed 15.15.5; SDK 54 bundles exact `15.12.1`. Installed-manifest walk (1,067 manifests): the only non-dev edge is `lucide-react-native :: peerDependencies ^12 || ^13 || ^14 || ^15`. The preview binary's lock (`git show 6042506d:SmartCompareApp/package-lock.json`) already resolves 15.15.5, so keeping it via `expo.install.exclude` keeps native code identical to what testers run; a downgrade to 15.12.1 would be a native change nobody asked for (the app renders its hero illustrations and every Lucide icon through it).

### 1.6 How `npx expo install` behaves here (read from the installed `@expo/cli` 54.0.24)

- `install/installAsync.js:169-182`: when `expo` is in the package list it runs `npm install expo@<spec>` FIRST, then `await`s a spawned `npx expo install <the rest>` under the NEW CLI (`install/installExpoPackage.js:73`, spawn at `:114`). The follow-up resolves the remaining packages from the NEW `expo`'s `bundledNativeModules.json` (so `expo-font` → `~14.0.12`, etc.).
- After installing, `applyPluginsAsync` → `autoAddConfigPluginsAsync` only adds packages that have an `app.plugin.js`, are not already in `expo.plugins`, and are not auto-plugins. `expo-font` and `expo-localization` are already in `app.json` plugins; `expo-updates` is in `getAutoPlugins()` (measured list); `expo-screen-capture` has no `app.plugin.js`. `attemptAddingPluginsAsync` returns immediately on an empty list (`utils/modifyConfigPlugins.js`). **So the installs do not rewrite `app.json`** — gate G9 re-verifies by sha.
- `install --fix` (`fixPackages.js:69`, dev half at `:104`) installs devDependencies with `addDevAsync`; `checkPackages.js:94` and `validateDependenciesVersions.js:163-197` honour `expo.install.exclude` (name, optionally with a range).

### 1.7 `react-native-gesture-handler` — every place that names it

`git grep -n "react-native-gesture-handler" -- . ':!SmartCompareApp/package-lock.json'` at base:

- `SmartCompareApp/package.json:50` — `"react-native-gesture-handler": "~2.28.0",`
- `SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts` — `:8` (header, names the finding), `:454` and `:469` (EDGE_FIELDS / R11 docstrings), `:514` (the `PENDING_REMOVAL` entry, `:503-516` incl. its comment), `:546` (a docstring example), `:751` (the `d3` `it.todo`).
- `SmartCompareApp/package-lock.json:45` (root `dependencies`), `:12562-12564` (its own `packages` entry, 2.28.0). Its lock `dependencies`: `@egjs/hammerjs` (0 other dependents; itself depends on `@types/hammerjs`, 0 other dependents), `hoist-non-react-statics` (also used by `@sentry/react`), `invariant` (11 other dependents). So `npm uninstall` removes exactly three lock packages: `react-native-gesture-handler`, `@egjs/hammerjs`, `@types/hammerjs`.
- `docs/runbooks/bundle-bcd-perf-audit.md:104` — a Bundle B/C/D table row saying "✗ false positive — required by `@react-navigation` at native-link time … **Keep**". FALSE by measurement (below); R11 corrects it.
- `CLAUDE.md:578` (a session-66 paragraph listing Ahmed's owed actions), `docs/investigations/2026-09-06-full-review*`, `…/2026-09-24-session-66-close-state.md:113`, `…/2026-09-24-session-67-state/APPLY_PACK_AHMED.md:119`, `…/2026-09-29-session-69-state/{APP_STORE_LAUNCH_RUNBOOK.md:68, NEXT_SESSION_PROMPT.md:100, appstore_findings_verified.json (EXPO-09 + the orphan finding)}`, `docs/investigations/specs/2026-09-23/W3_7_UNIT_SPEC.md`, `docs/plans/2026-05-06-tos-evidence/agent-b-report.md:267`, `docs/superpowers/plans/2026-03-28-qaren-frontend-redesign.md:89` — historical records; not edited by this unit (docs checkpoint territory).
- **Not referenced** by `jest.config.js`, `babel.config.js`, `metro.config.js`, `App.tsx`, `index.ts`, `src/**`, `__mocks__/**`, `app.json`, `eas.json`, `tsconfig.json` (no hits in the grep above).

Installed-manifest walk (`rngh_walk.js`, every `package.json` under `node_modules` incl. nested): 1,067 manifests; the ONLY edges are `@testing-library/react-native :: devDependencies ^2.28.0`, `react-native-reanimated :: devDependencies 2.28.0`, `react-native-screens :: devDependencies ^2.28.0`. Zero `dependencies` / `peerDependencies` / `optionalDependencies` edges — `@react-navigation/*` does not need it (the runbook row is wrong). `tsconfig.json` sets `"types": ["jest", "node"]`, so removing `@types/hammerjs` changes nothing for `tsc`.

### 1.8 `PENDING_REMOVAL` — every occurrence

`git grep -n PENDING_REMOVAL`: code only in `SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts` — `:503` (declaration), `:643` (comment), `:732-733` (`d1`), `:734` (comment), `:742-744` (`d2`), `:751` (`d3` todo text), `:754-755` (`d4`). Every other hit is a doc listed in 1.7. The `d3` todo is `:750-752`:

```ts
  it.todo(
    'd3 AHMED: npm uninstall react-native-gesture-handler, commit package-lock.json, delete the PENDING_REMOVAL entry, then eas build',
  );
```

### 1.9 Every icon / splash / favicon / notification field in `app.json`

- `expo.icon: "./assets/icon.png"` (`app.json:6`)
- `expo.splash: { "image": "./assets/splash-icon.png", "resizeMode": "contain", "backgroundColor": "#ffffff" }` (`:9-13`) — the LEGACY root key; there is no `expo-splash-screen` plugin entry
- `expo.android.adaptiveIcon: { "foregroundImage": "./assets/adaptive-icon.png", "backgroundColor": "#ffffff" }` — the background is ALREADY the tile white
- `expo.web.favicon: "./assets/favicon.png"`
- `expo-notifications` plugin options: `{ "color": "#10B981" }` — no `icon` (Android small notification icon), which Android then derives from the launcher icon
- ABSENT: `expo.ios.icon` (so no iOS 18 `dark` / `tinted` variants), `expo.android.icon`, `android.adaptiveIcon.monochromeImage` / `backgroundImage`, `expo.notification`, `ios.splash`, `android.splash`

`npx --no-install expo config --type introspect --json` (3 s, exit 0) resolves exactly these: `icon ./assets/icon.png`; `splash {"image":"./assets/splash-icon.png","resizeMode":"contain","backgroundColor":"#ffffff"}`; `ios.icon undefined`; `android.adaptiveIcon {"foregroundImage":"./assets/adaptive-icon.png","backgroundColor":"#ffffff"}`; `web.favicon ./assets/favicon.png`; `notification undefined`; `expoPlist.EXUpdatesRuntimeVersion "1.0.0"`; `infoPlist.CFBundleShortVersionString "1.0.0"`, `UILaunchStoryboardName "SplashScreen"`. The introspected `splashScreenStoryboard` holds ONE image view: `id EXPO-SplashScreen`, `image "SplashScreenLegacy"`, `contentMode "scaleAspectFit"`, frame 414×736, constrained top/leading/trailing/bottom to the container; background `SplashScreenBackground` = sRGB 1/1/1. Android `styles`: `Theme.App.SplashScreen` parent `AppTheme`, `android:windowBackground @drawable/ic_launcher_background`.

### 1.10 How the splash image is actually drawn (legacy `splash` key, no `expo-splash-screen`)

`expo-splash-screen` is NOT installed (`find node_modules -maxdepth 3 -name expo-splash-screen` → nothing; 0 lock hits). `@expo/prebuild-config` applies its `unversioned/expo-splash-screen` FALLBACK (`createLegacyPlugin({packageName: 'expo-splash-screen', fallback: [withAndroidSplashScreen, withIosSplashScreen]})`). `getIosSplashConfig.js` for a root `splash` returns `enableFullScreenImage_legacy: true, imageWidth: 200`; `InterfaceBuilder.js:89-90` then sizes the view 414×736 pinned to all four edges, and `withIosSplashAssets.js` copies the image at @1x/@2x/@3x WITHOUT resizing. With `scaleAspectFit`, a square 1024×1024 image is drawn at the FULL SCREEN WIDTH (375–440 pt on current iPhones), vertically centred, over `#ffffff`. So the wordmark's on-screen width = (ink width ÷ canvas width) × screen width. Android: `getAndroidSplashConfig.js` root-`splash` branch, `imageWidth: 200` dp drawables.

### 1.11 How EAS builds the iOS icon from `expo.icon`

`@expo/prebuild-config/build/plugins/icons/withIosIcons.js:181-201`: one 1024 universal icon, `resizeMode: 'cover'`, `removeTransparency: appearance !== 'dark'`, `backgroundColor: '#ffffff'` for the any/tinted appearance. So transparency would be flattened onto white at build time anyway; this unit still commits an OPAQUE file so the repo asset is exactly what the App Store gets.

### 1.12 The `nativeBundle.w37` launcher-art block (base)

`SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts:236-278` (abridged: two comment lines and the test bodies elided, the `sha256` helper joined onto one line):

```ts
describe('W3-7 (b) launcher art', () => {
  // SHA-256s recorded on 2026-05-24 (bundle-d-followups ICN-0001; re-measured
  // at b63a8368). Ruling R13: this is the repo's RECORD, not a hash derivable
  // here — no Expo template PNG exists in node_modules. …
  const RECORDED_2026_05_24 = {
    icon: '74c64047eb557b1341bba7a2831eedde9ddb705e6451a9ad9f5552bf558f13de',
    splashAndAdaptive: '5f4c0a732b6325bf4071d9124d2ae67e037cb24fcc9c482ef82bea742109a3b8',
  };
  const sha256 = (file: string): string => crypto.createHash('sha256').update(fs.readFileSync(path.join(APP, 'assets', file))).digest('hex');
  // AHMED: flip to true once assets/{icon,splash-icon,adaptive-icon}.png are
  // re-rendered (CLAUDE.md App-Store blocker #1 / bundle-d-followups ICN-0001).
  const ICON_ART_SUPPLIED = false;                                   // :251
  const itArt = ICON_ART_SUPPLIED ? it : it.skip;
  itArt('b1 icon.png differs from the SHA-256 recorded on 2026-05-24 …', …);
  itArt('b2 splash-icon.png and adaptive-icon.png differ from the SHA-256 recorded on 2026-05-24 and from each other …', …);
  it.todo('b3-todo flip ICON_ART_SUPPLIED once assets/ are re-rendered');   // :265
  it('b3 [PRESERVE] the three launcher PNGs exist, are PNGs, and app.json points at them', …);
});
```

The file header (`:14-17`) binds ruling R14: every input is read with `fs` + `JSON.parse`, never `import`/`require` of a PNG or JSON (`jest.config.js` maps `\.(ttf|otf|woff2?|png|jpg)$` to `__mocks__/fileStub.ts`).

Base run of the file alone: `Tests: 2 skipped, 2 todo, 38 passed, 42 total` (b1/b2 skipped; `b3-todo` and `d3` todo).

### 1.13 The CI step

`.github/workflows/ci.yml:304-310`, the LAST step of job `frontend-tests` (Node 20, `npm ci`, then jest / eslint / tsc, all blocking since M18):

```yaml
      # S69 U9 (BLD-BP-08) — reports Expo SDK / native-package version drift
      # (the 7 patch bumps U4b owes) WITHOUT blocking; `expo install --check`
      # exits 1 on drift and never writes. Ratchet to blocking once U4b lands
      # and the step reads clean.
      - name: Expo dependency drift (non-blocking)
        continue-on-error: true
        run: cd SmartCompareApp && npx expo install --check
```

No test pins this step: `tests/test_ci_gates.py` has no `expo`/`frontend-tests` match, and `grep -rln "frontend-tests\|ci.yml"` over `tests/*.py` and `SmartCompareApp/__tests__` finds nothing for it.

### 1.14 The master PNG

`C:/Users/SynAckITPC/Downloads/MYEZ-icon-white-2048.png` — 146,295 bytes, sha256 `70b2f8264d7eb07dbfe7627d332d991dc68429f3440615751bf99eacc05a4b41` (`png_facts.py`, Pillow 12.3.0, plus a raw IHDR read):

- IHDR: 2048 × 2048, bit depth 8, **colour type 6 (RGBA)**, interlace 0; chunks exactly `IHDR, IDAT, IEND` (no gAMA/iCCP/sRGB/tEXt).
- Alpha: 180,868 pixels at 0 (the four corners), 4,010,750 at 255, 2,686 partial (the anti-aliased tile edge). Corner pixels `(0,0,0,0)`; centre `(255,255,255,255)`.
- Tile: a FULL-BLEED rounded square (touches all four edges) filled exactly `(255,255,255)`. Corner = a true circular arc of **radius 461.0 px = 0.2251 × side** (least-squares over the alpha-127.5 edge, RMS 0.076 px; radii 450 / 470 fit at 3.6 / 3.0 px RMS). All four corners symmetric: first alpha ≥ 128 on row 0 at x = 439, last at 1608; bottom row first at 439; main and anti-diagonal first at 135.
- Ink (a pixel counts when some channel is > 40 below white): bounding box x 483…1627, y 399…1640 inclusive = **1145 × 1242 px** (any non-white: 483…1628 × 399…1640 = 1146 × 1242). Black ink exact `(10,10,11)` (152,962 px in a 1-in-4 pixel sample); emerald dot exact **`(16,185,129)` = `#10B981`** = `colors.accent` (`src/theme/index.ts:19`) = the `expo-notifications` colour; dot bbox x 1419…1552, y 1507…1639 (≈ 134 px). Ink-bbox centre (1055.5, 1019.5) vs tile centre (1023.5, 1023.5): the composition sits 32 px right of centre by design — this unit preserves it, never re-centres.
- Maximum distance of any non-white pixel centre from the tile centre: **869.149 px** (drives the Android safe-zone fit).

### 1.15 The base assets (the recorded Expo template art)

| file | IHDR | mode | sha256 | notes |
|---|---|---|---|---|
| `assets/icon.png` | 1024², ct **3** (palette), no tRNS | P | `74c64047…58f13de` = RECORDED icon | corners `(245,245,247)`, centre `(221,221,225)`; 0 emerald px, 0 near-black px |
| `assets/adaptive-icon.png` | 1024², ct **3** + tRNS | P | `5f4c0a73…3b8` | byte-identical to splash-icon |
| `assets/splash-icon.png` | 1024², ct **3** + tRNS | P | `5f4c0a73…3b8` | = RECORDED splashAndAdaptive |
| `assets/favicon.png` | 48², ct **4** (grey+alpha), **interlaced** | LA | `24272cdaeff82cc5facdaccd982a6f05b60c4504704bbf94c19a6388659880bb` | not in RECORDED_2026_05_24 |

"Has alpha" is NOT a discriminator at base: the palette files carry alpha through `tRNS`. The colour type is.

### 1.16 The preview binary's native versions

The testers run preview build 773a9375, stated to be built from `6042506d` (2026-07-04, "fix(ios): add modular_headers …" — the build id itself is not verifiable from the repo). `git show 6042506d:SmartCompareApp/package-lock.json` resolves expo 54.0.34, expo-updates 29.0.17, expo-font 14.0.11, expo-localization 17.0.8, expo-screen-capture 8.0.9, expo-file-system 19.0.22, expo-constants 18.0.13, expo-modules-core 3.0.30, expo-modules-autolinking 3.0.25, react-native 0.81.5, react-native-gesture-handler 2.28.0, react-native-svg 15.15.5 — **identical to base**. Since `6042506d`, `app.json` (+133/−9) and `package.json` (+8/−2, the axios bump and `intl-pluralrules`, both pure JS) changed; U4a's native `app.json` changes already sit on main at `expo.version` 1.0.0.

`eas.json`: `cli.appVersionSource "remote"`; `preview` → channel `preview`; `production` → channel `production`, `autoIncrement: true`. `app.json`: `version "1.0.0"`, `runtimeVersion { policy: "appVersion" }`. Pinned by `nativeBundle.w37.test.ts` `e1 [CONSCIOUS PIN]` (`:768-781`).

### 1.17 Full jest baseline (base, this worktree)

`timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci`, three runs:
- run 3 (log `jest_base_run3.log`): `Test Suites: 3 skipped, 351 passed, 351 of 354 total` / `Tests: 15 skipped, 15 todo, 3428 passed, 3458 total` / `Snapshots: 44 passed, 44 total` / 10.1 s.
- run 1: `1 failed` in `__tests__/HistoryScreen.mobileJank.m21.test.tsx` (describe `MB-flows-08 — hero marquee tap`, `:127`); the file passed alone (4/4) and in runs 2–3. **Pre-existing flake**, not this unit's; a red there in the GREEN gate is re-run once before it counts.

### 1.18 Other facts the design depends on

- **PNG decoding under jest:** `jest.config.js` `testEnvironment: 'node'`; Node's built-in `zlib.inflateSync` is available (`typeof require('zlib').inflateSync === 'function'`). `pngjs 3.4.0`, `parse-png 2.1.0`, `jimp-compact 0.16.1` exist ONLY transitively (`@expo/image-utils → parse-png → pngjs`) and are undeclared — a test must not import them. `sharp` absent.
- **The in-app glyph is still the old Qaren mark:** `src/screens/SplashScreen.tsx:112` renders `<QarenLogo size={128} />` (a Q-ring + tail + emerald dot SVG, `src/components/QarenLogo.tsx`) under the brand text; `QarenLogo` is also used by Home (`:900`), Profile (`:355`), History (`:939`), onboarding Step 1 (`:76`) and `LoadingRings`. After this unit the native splash shows MYEZ and the JS splash that follows shows the Q-ring — §8 Q4.
- **Line endings:** `package.json`, `package-lock.json`, `app.json`, the W3-7 test, `ci.yml`, the runbook are `i/lf w/crlf`; no `.gitattributes`; PNGs are detected as binary (no EOL conversion).
- **Pillow determinism (measured on this box):** the prototype renderer (`proto/render_proto.py`) run twice produced byte-identical files (sha256 equal for all four outputs).

---

## 2. Requirements

R1. **Commit the master.** `docs/brand/myez-icon-master-2048.png` = a byte copy (Python `shutil.copyfile`) of `C:/Users/SynAckITPC/Downloads/MYEZ-icon-white-2048.png`; sha256 on disk `70b2f8264d7eb07dbfe7627d332d991dc68429f3440615751bf99eacc05a4b41`. The folder `docs/brand/` is new.

R2. **The renderer** `scripts/render_myez_icons.py` exists as designed in §4 (the location follows CLAUDE.md App-Store blocker #1: "a `scripts/` PIL/Cairo script"). It passes `python -m py_compile` and `ruff check --select E9,F63,F7,F82 --no-cache` (CI's `backend-lint` covers `scripts/`).

R3. **Four rendered files**, written ONLY by R2 (never hand-edited, never taken from `icon-candidates/`):
- `SmartCompareApp/assets/icon.png` — 1024 × 1024, IHDR colour type **2** (RGB, 8-bit, non-interlaced), no `tRNS`; the master flattened onto the tile white `(255,255,255)` (transparent corners become white — a full-bleed square; iOS applies its own mask) then resized 2048→1024 LANCZOS. Corners `(255,255,255)`.
- `SmartCompareApp/assets/adaptive-icon.png` — 1024 × 1024, colour type **6** (RGBA); transparent background; the mark alone (white tile removed exactly, §4.3) scaled about the tile centre so every pixel with alpha > 0 lies inside the Android **66 dp safe-zone circle** (108 dp canvas → radius 1024 × 33/108 = 312.89 px) with an 8 px margin. Prototype: max radius 305.57 px, alpha bbox (320,290)–(726,731).
- `SmartCompareApp/assets/splash-icon.png` — 1024 × 1024, colour type **6**; transparent background; wordmark + dot only, scaled so the ink width is **30 % of the canvas** (≈ 112–132 pt on 375–440 pt-wide iPhones, the size of the 128 pt brand element the JS SplashScreen shows next — §1.10, §1.18). Prototype alpha bbox (364,342)–(676,679), width 312 px = 30.5 %.
- `SmartCompareApp/assets/favicon.png` — 48 × 48, colour type **6**; the full rounded tile with transparent corners (`web.favicon` references it, §1.9).
- The three launcher files differ pairwise and from the recorded template SHA-256s; favicon differs from `24272cda…`.

R4. **The manifest** `docs/brand/myez-icons.manifest.json`, written by R2 (§4.5): master path + sha256, Pillow version, the parameters, and per output the file sha256, the decoded-pixel sha256 (`Image.tobytes()` in the file's own mode), width, height, mode. JSON with `sort_keys=True`, 2-space indent, trailing newline, LF, no timestamps.

R5. **`app.json`: no change** under Q2 = keep (§8). Every field this unit needs is already right (§1.9): `icon`, `splash.image`, `splash.backgroundColor "#ffffff"`, `android.adaptiveIcon.{foregroundImage, backgroundColor "#ffffff"}`, `web.favicon`. The transparent renders are composited over exactly that white. Do NOT add `ios.icon` dark/tinted, a notification icon, a monochrome image or the `expo-splash-screen` plugin (§8 Q5). Under Q2 = bump, the ONLY change is `"version": "1.0.1"`.

R6. **`package.json`** after §3:
- a new top-level `"expo": { "install": { "exclude": ["react-native-svg"] } }` (under Q1 = exclude: `["eslint-config-expo", "react-native-svg"]`);
- `dependencies`: `expo` `"~54.0.37"`, `expo-font` `"~14.0.12"`, `expo-localization` `"~17.0.9"`, `expo-screen-capture` `"~8.0.10"`, `expo-updates` `"~29.0.20"` (or a later SDK-54 patch the Expo API names on the day — same major.minor, patch ≥); `react-native-gesture-handler` GONE; every other entry byte-unchanged (`react-native-svg` stays `"^15.12.1"`);
- `devDependencies` (Q1 = align, default): `eslint-config-expo` `"~10.0.0"`; nothing else changes.

R7. **`package-lock.json`** changes ONLY through §3's commands. Expected: removed `node_modules/react-native-gesture-handler`, `node_modules/@egjs/hammerjs`, `node_modules/@types/hammerjs` and the root `dependencies` entry; changed versions under `node_modules/expo`, `expo-font`, `expo-localization`, `expo-screen-capture`, `expo-updates`, `expo-file-system`, `expo-constants`, `expo-modules-autolinking`, `babel-preset-expo`, `eslint-config-expo`, `node_modules/@expo/*` (cli, config, config-plugins, metro-config, env, json-file, plist, …). Any other added/removed/changed `packages` key is listed in the GREEN report with its reason (typically a transitive of `@expo/cli 54.0.27`). `node_modules/react-native-svg` stays 15.15.5.

R8. **`SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts`:**
- (b) `ICON_ART_SUPPLIED = true` at `:251`; delete the `b3-todo` line `:265`; replace the "AHMED: flip to true …" comment with one line naming R1/R2 (`docs/brand/myez-icon-master-2048.png` via `scripts/render_myez_icons.py`, session 70 U4b); add `RECORDED_BASE_94C097CD = { favicon: '24272cdaeff82cc5facdaccd982a6f05b60c4504704bbf94c19a6388659880bb' }` beside `RECORDED_2026_05_24`; add b4–b14 (§5); `b1`, `b2`, `b3` stay.
- (d) `PENDING_REMOVAL` becomes `{}` (the constant, its type and the R8 docstring stay — d1 is still the guard that a NEW orphan reddens); its per-entry comment is replaced by one line "react-native-gesture-handler was removed in session 70 U4b (npm uninstall + lock)"; delete the `d3` todo `:750-752`; the EDGE_FIELDS / R11 docstrings keep their measurements but say "was" for gesture-handler; add d5 (§5). `d1`/`d2`/`d4` bodies and fixtures unchanged.
- a new `describe('session 70 U4b — Expo SDK 54 patch level with one deliberate exclusion', …)` holding k1–k6 (§5), placed after the `session 69 U4a` block.
- (e) `e1` value unchanged under Q2 = keep; its comment gains ONE sentence: "U4b (session 70) moved native patch versions without moving expo.version — measured JS-compatible with the 1.0.0 preview binary (spec §1.3); those native fixes reach testers only through a new build." Under Q2 = bump: `e1` asserts `'1.0.1'` and the comment says why.
- R14 still holds: PNG / JSON / YAML inputs are read with `fs` (+ `JSON.parse`); the only new import is the helper of R9 and Node's `zlib`.

R9. **Helper** `SmartCompareApp/__tests__/helpers/pngDecode.ts` (not collected by `testMatch`): `pngChunks(buf)` (walks length/type/data/CRC from offset 8; throws on a bad signature; the CRC is skipped, not verified), `readIhdr(buf)` (`{ width, height, bitDepth, colorType, interlace }`, throws unless the first chunk is IHDR), `decodePng(buf)` → `{ width, height, channels: 3 | 4, pixels: Uint8Array }` for bit depth 8, colour type 2 or 6, interlace 0 ONLY (concatenate every IDAT, `zlib.inflateSync`, undo filters 0 None / 1 Sub / 2 Up / 3 Average / 4 Paeth with bpp = channels); anything else throws `Error('pngDecode: unsupported <field> <value>')`. No dependency is added.

R10. **CI ratchet** (Q3 default = the task as written): the step becomes
```yaml
      # S69 U9 (BLD-BP-08) → RATCHETED TO BLOCKING in session 70 U4b once
      # `npx expo install --check` read clean (react-native-svg excluded via
      # expo.install.exclude). NOTE: the expected versions come from the Expo
      # API, so a new SDK-54 patch release reddens this step on an unchanged
      # main (spec §1.1) — that is the signal to run the next bump unit.
      - name: Expo dependency drift
        run: cd SmartCompareApp && npx expo install --check
```
(no `continue-on-error`). Under Q3 = B, instead: a blocking step `Expo dependency drift (lockfile)` running `cd SmartCompareApp && EXPO_OFFLINE=1 npx expo install --check`, followed by a report-only step `Expo SDK patch drift (report-only)` with `continue-on-error: true` running the online check. No other line of `ci.yml` changes.

R11. **Stale runbook row:** below the table in `docs/runbooks/bundle-bcd-perf-audit.md` (after the `react-native-vector-icons` row, before "**Action this commit:**"), add one line: `**SESSION 70 CORRECTION (2026-09-30):** the react-native-gesture-handler row is wrong — a walk of all 1,067 installed manifests found only devDependencies edges (no @react-navigation dependency or peer), and U4b removed the package (npm uninstall + lock).` Nothing else in that file changes.

R12. **Nothing else changes.** `git status --short` after GREEN lists exactly: `SmartCompareApp/package.json`, `SmartCompareApp/package-lock.json`, `SmartCompareApp/assets/{icon,adaptive-icon,splash-icon,favicon}.png`, `SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts`, `SmartCompareApp/__tests__/helpers/pngDecode.ts` (new), `docs/brand/myez-icon-master-2048.png` (new), `docs/brand/myez-icons.manifest.json` (new), `scripts/render_myez_icons.py` (new), `.github/workflows/ci.yml`, `docs/runbooks/bundle-bcd-perf-audit.md`, this spec folder — plus `SmartCompareApp/app.json` ONLY under Q2 = bump. No `.snap`, no `src/**`, no backend `app/**`, no `tests/**`, no `eas.json`, no `requirements*.txt`. `git diff --stat` must not show a whole-file rewrite of any CRLF text file (compare `git diff --stat` line counts against the intended edits).

---

## 3. Package-manager commands (run ONLY in this worktree, from `C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b/SmartCompareApp`, in this order)

The session rules reserve package-manager commands to the orchestrator; the GREEN agent does P0, P1 and P5–P8 and reports; the orchestrator (or the GREEN agent, if the orchestrator hands it the steps) runs P2–P4. Network is required for P2–P5 (npm registry + the Expo versions API).

- **P0 snapshot.** Python `shutil.copyfile` of `package.json`, `package-lock.json`, `app.json` into the agent's scratchpad; print their sha256. (Restore = copy back + sha-compare; never `git checkout --`.)
- **P1 exclude first (Edit tool, not npm).** Add the `"expo"` key of R6 to `package.json` (before `"private": true`), so every later `expo install` honours it. Under Q1 = exclude, the list is `["eslint-config-expo", "react-native-svg"]` and P4 is skipped.
- **P2** `npm uninstall react-native-gesture-handler`
- **P3** `npx expo install expo@~54.0.37 expo-font expo-localization expo-screen-capture expo-updates` — installs `expo` first, then runs `npx expo install expo-font expo-localization expo-screen-capture expo-updates` under the new CLI (§1.6). If the spawned follow-up fails, run that second command by hand.
- **P4** (Q1 = align) `npm install --save-dev eslint-config-expo@~10.0.0`
- **P5** `npx expo install --check` → exit 0; the output names `react-native-svg` as skipped via `expo.install.exclude` and ends "Dependencies are up to date". Also record `EXPO_OFFLINE=1 npx expo install --check` → exit 0.
- **P6** `npm ls react-native-gesture-handler @egjs/hammerjs @types/hammerjs` → `(empty)`; `npm ls expo expo-font expo-localization expo-screen-capture expo-updates expo-file-system expo-constants eslint-config-expo react-native-svg` → paste; `npm ls --all > NUL` / `>/dev/null` → exit 0 (no invalid / missing / extraneous).
- **P7** sha256 of `app.json` equals the P0 copy (the installs must not touch it, §1.6).
- **P8** a node one-off (scratchpad) that diffs `packages` of the P0 lock copy against the new lock: print removed / added / version-changed keys; compare with R7's expected set and justify every extra.

Never run `npm audit fix`, `expo install --fix` without P1 in place, `npx expo prebuild`, `eas *`, or anything that writes `ios/` / `android/`.

---

## 4. The render script — `scripts/render_myez_icons.py`

### 4.1 Contract

- Inputs: `docs/brand/myez-icon-master-2048.png` (path relative to the repo root = `Path(__file__).resolve().parents[1]`). Constant `MASTER_SHA256 = "70b2f8264d7eb07dbfe7627d332d991dc68429f3440615751bf99eacc05a4b41"`; a mismatch prints both hashes and exits 2 before rendering. It also asserts IHDR 2048 × 2048 RGBA.
- Pillow guard: `PINNED_PILLOW = "12.3.0"` (= `requirements-dev.txt`); a different `PIL.__version__` exits 2 unless `--any-pillow` is passed (re-baselining is then a deliberate act, and the manifest records the version used).
- Outputs: the four files of R3 under `SmartCompareApp/assets/` (or `--out-dir DIR` for a dry render) and the manifest of R4 (skipped with `--out-dir`).
- `--check`: renders in memory, writes NOTHING; for each output compares the on-disk file's mode, size and `tobytes()` with the fresh render (pixel equality — robust to zlib byte differences across platforms), and compares the on-disk manifest with a freshly computed one (file sha256 included, since the manifest must describe the committed bytes). Exit 0 = reproducible; exit 1 lists every mismatch.
- Re-run (from the repo root, pinned venv): `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe scripts/render_myez_icons.py` then `… --check`. Runtime on this box ≈ 5 s (the per-pixel loops over 4.2 M pixels).
- Pure stdlib + Pillow; no network; no randomness; no timestamps; prints one line per output (`name mode size sha256`).

### 4.2 Constants (derived in §1 and the prototype)

```
CANVAS = 1024
TILE_WHITE = (255, 255, 255)
SAFE_RADIUS = CANVAS * 33 / 108            # 312.888… px (Android 66 dp circle on a 108 dp canvas)
ADAPTIVE_MARGIN = 8                        # px inside the safe circle
SPLASH_INK_WIDTH_FRACTION = 0.30           # ink width / canvas width on the splash
FAVICON = 48
RESAMPLE = Image.Resampling.LANCZOS
```

### 4.3 Algorithm (exact; the prototype `proto/render_proto.py` implements it and was run twice with identical bytes)

1. `master = Image.open(MASTER)`; `master.load()`; assert mode RGBA, size 2048².
2. **icon.png:** `base = Image.new("RGBA", (2048, 2048), TILE_WHITE + (255,))`; `base.alpha_composite(master)`; `icon = base.convert("RGB").resize((1024, 1024), RESAMPLE)`.
3. **mark (2048², RGBA)** = the exact inverse of "composite over white", integer arithmetic, per pixel `(r, g, b, a)` of the master:
   - `a == 0` → `(0, 0, 0, 0)`;
   - `a < 255` → first flatten onto white: `c = (c*a + 255*(255 - a) + 127) // 255` for each channel;
   - `d = max(255 - r, 255 - g, 255 - b)`; `d == 0` → `(0, 0, 0, 0)` (the tile white disappears);
   - else `F_c = 255 - ((255 - c)*255 + d//2) // d` and the output is `(F_r, F_g, F_b, d)`.
   Compositing `mark` back over white reproduces the flattened master within 1 per channel (the black ink `(10,10,11)` becomes `(0,0,1, 245)`, the emerald `(16,185,129)` becomes `≈(0,180,121, 239)`; over white they return to the originals). **This is correct ONLY over white** — both consumers composite over `#ffffff` (§1.9, R5); see §7.
4. `R_INK` = the maximum distance of any `mark` pixel with alpha > 0 (pixel centre) from (1023.5, 1023.5) → 869.149 on the committed master.
5. **adaptive-icon.png:** `s_a = (SAFE_RADIUS - ADAPTIVE_MARGIN) / R_INK` (= 0.350790); `n = round(2048 * s_a)` (= 718); `scaled = mark.resize((n, n), RESAMPLE)` (Pillow resizes RGBA premultiplied, so no dark fringes); `out = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))`; `out.alpha_composite(scaled, ((1024 - n)//2, (1024 - n)//2))` (offset 153).
6. **splash-icon.png:** `W_INK = mark.getchannel("A").getbbox()` width (= 1146); `s_s = SPLASH_INK_WIDTH_FRACTION * 1024 / W_INK` (= 0.268063); `n = round(2048 * s_s)` (= 549); same placement (offset 237).
7. **favicon.png:** `master.resize((48, 48), RESAMPLE)` (RGBA, the rounded tile with transparent corners).
8. Save each with `img.save(path, format="PNG", optimize=False, compress_level=9)` and no `pnginfo` → chunks exactly `IHDR, IDAT, IEND` (measured on the prototype outputs; RGB → colour type 2, RGBA → 6, never palette, never interlaced).

### 4.4 Prototype results (scratchpad `proto/out1`, `proto/out2` — two runs, identical bytes)

| output | mode / size | sha256 (prototype, this box) | measured |
|---|---|---|---|
| icon.png | RGB 1024² | `2530d5b33098dac3b2aa417982c506d8b93e2bbe5b07d387d78eabc52edc5834` (34,053 B) | corners `(255,255,255)`; 3,524 emerald px (G > R+60 and G > B+20); 151,892 near-black px (max channel < 40) |
| adaptive-icon.png | RGBA 1024² | `b336b66be61f3c72a23404f201fdcb444f78aa2d9e8d5974069b306f26cb89ce` (20,945 B) | corners alpha 0; max alpha>0 radius 305.57 ≤ 312.89; alpha bbox (320,290,726,731); 77,320 px alpha ≥ 128; 1,884 emerald + 82,813 near-black among alpha > 0 |
| splash-icon.png | RGBA 1024² | `bf8df272011f8c374bbdd1b681c892a238fa487ad62dfa9df5e84cbb953976b7` (17,247 B) | corners alpha 0; 998,172 px (95.2 %) alpha 0; alpha bbox (364,342,676,679) → width 312 = 30.5 %; composited over white the dot reads `(16,185,128)` |
| favicon.png | RGBA 48² | `3d225c46961f8d45a0faa2828a41b7b4e355607971f4e060091ae52e8b21d4d5` (2,208 B) | corners alpha 0 |

The GREEN's own run must reproduce these pixel facts; the file sha256s are expected to match on this box with Pillow 12.3.0 but the binding record is the manifest the GREEN commits. A contact sheet (`proto/contact_out1.png`: the icon under a rounded mask, the adaptive foreground over white inside the 72 dp viewport circle with the 66 dp safe circle in red, the splash on a 390 × 844 pt phone, the favicon) was inspected: the mark is intact, inside the safe circle, and the splash wordmark sits centred at ~30 % of the width.

### 4.5 Manifest shape (`docs/brand/myez-icons.manifest.json`)

```json
{
  "master": {"path": "docs/brand/myez-icon-master-2048.png", "sha256": "70b2f826…"},
  "outputs": {
    "SmartCompareApp/assets/adaptive-icon.png": {"height": 1024, "mode": "RGBA", "pixels_sha256": "…", "sha256": "…", "width": 1024},
    "SmartCompareApp/assets/favicon.png": {…},
    "SmartCompareApp/assets/icon.png": {"height": 1024, "mode": "RGB", …},
    "SmartCompareApp/assets/splash-icon.png": {…}
  },
  "params": {"adaptive_margin_px": 8, "canvas": 1024, "favicon_px": 48, "safe_radius_px": 312.889, "splash_ink_width_fraction": 0.3, "tile_white": "#ffffff"},
  "pillow": "12.3.0",
  "renderer": "scripts/render_myez_icons.py"
}
```

`pixels_sha256` = sha256 of `Image.open(file).tobytes()` in the file's own mode (RGB = 3 bytes/pixel, RGBA = 4) — exactly the byte layout R9's decoder returns, so jest cross-checks the hand-written decoder against Pillow on four real adaptive-filtered files (b7).

---

## 5. RED tests (all in `SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts` unless named; helper per R9)

"RED at base" means: with the test edits applied and NOTHING else (base assets, base `package.json` / lock / `node_modules`, no `docs/brand/`, base `ci.yml`), the test fails for the stated reason. Expected RED count: **19** (b1, b2, b4, b5, b6, b7, b8, b9, b10, b13, b14 = 11; d1, d5 = 2; k1–k6 = 6; plus e1 only under Q2 = bump); **2** new pins stay green at base (b11 PRESERVE, b12 HARNESS); `b3`, `d2`, `d4`, `e1`, `p1`, `p2` and every other existing test stay green. The two todos (`b3-todo`, `d3`) are gone, so the file reports 0 todo.

| id | name (prefix exactly) | assertion | why RED at base |
|---|---|---|---|
| b1 | `b1 icon.png differs from the SHA-256 recorded on 2026-05-24` (existing, un-skipped) | sha256(icon.png) ≠ `74c64047…` | base icon IS that file |
| b2 | `b2 splash-icon.png and adaptive-icon.png differ …` (existing, un-skipped) | both ≠ `5f4c0a73…` and ≠ each other | both ARE that file |
| b4 | `b4 icon.png is a 1024x1024 8-bit truecolour PNG with no alpha channel and no tRNS` | `readIhdr` = {1024, 1024, 8, **2**, 0}; `pngChunks` has no `tRNS` | colour type 3 (palette) |
| b5 | `b5 adaptive-icon.png and splash-icon.png are 1024x1024 8-bit RGBA PNGs` | both IHDR {1024, 1024, 8, **6**, 0} | colour type 3 + tRNS |
| b6 | `b6 favicon.png (web.favicon) is a 48x48 8-bit RGBA PNG and differs from the favicon recorded at base 94c097cd` | IHDR {48, 48, 8, 6, 0}; sha ≠ `24272cda…` | colour type 4, interlace 1, sha equal |
| b7 | `b7 the four PNGs are the committed renderer's output (docs/brand/myez-icons.manifest.json)` | manifest `master.sha256` = sha256 of `docs/brand/myez-icon-master-2048.png`; for each of the 4 outputs: file sha256 = manifest `sha256`; `decodePng` pixels sha256 = manifest `pixels_sha256`; width/height/mode agree with IHDR (RGB ↔ 2, RGBA ↔ 6) | manifest file missing |
| b8 | `b8 icon.png pixels: tile-white corners and the MYEZ mark (not the grey template)` | IHDR ct 2 asserted first; decoded corners `(255,255,255)`; ≥ 2,000 emerald px (G > R+60 && G > B+20); ≥ 100,000 near-black px (max < 40) | IHDR ct 3 (the template has 0 emerald and 0 near-black px, §1.15) |
| b9 | `b9 adaptive-icon.png pixels: transparent corners, every inked pixel inside the Android 66 dp safe circle` | IHDR ct 6 first; the 4 corner alphas = 0; for every pixel with alpha > 0, distance((x,y),(511.5,511.5)) ≤ 1024·33/108; ≥ 40,000 px alpha ≥ 128 (prototype 77,320); ≥ 1,000 emerald px among alpha ≥ 128 (prototype 1,716) | IHDR ct 3 |
| b10 | `b10 splash-icon.png pixels: transparent background, wordmark at ~30% of the canvas width, narrower than the adaptive mark` | IHDR ct 6 first; 4 corner alphas = 0; ≥ 90 % of pixels alpha 0; the alpha > 0 bbox width W satisfies 0.28·1024 ≤ W ≤ 0.33·1024 AND W < the adaptive-icon alpha > 0 bbox width | IHDR ct 3 |
| b11 | `b11 [PRESERVE] the white the transparent art is composited over` | `android.adaptiveIcon.backgroundColor === '#ffffff'`, `splash.backgroundColor === '#ffffff'`, `splash.resizeMode === 'contain'`, `web.favicon === './assets/favicon.png'` | GREEN at base (a pin, not a red) |
| b12 | `b12 [HARNESS] the inline PNG decoder round-trips all five filter types and refuses what it cannot read` | builds in-test a 3-px-wide, 5-row RGBA image whose rows use filters 0,1,2,3,4 (forward filters computed in the test, `zlib.deflateSync`, hand-assembled chunks with any CRC), `decodePng` returns the source pixels exactly; a 1×1 RGB image round-trips; IHDR colour type 3, bit depth 16 and interlace 1 each throw `/pngDecode: unsupported/` | GREEN at base (it proves the harness before any art exists) |
| b13 | `b13 the MYEZ master is committed with its recorded SHA-256` | `docs/brand/myez-icon-master-2048.png` exists; sha256 = `70b2f826…`; IHDR {2048, 2048, 8, 6, 0} | file missing |
| b14 | `b14 [SOURCE-SHAPE] scripts/render_myez_icons.py exists, pins the master SHA-256 and writes the four launcher files` | the file exists and its text contains the master sha256, `docs/brand/myez-icon-master-2048.png` and each of the four asset file names | file missing |
| d1 | existing `d1 [BOOKKEEPING-RED — ruling R8] …` with `PENDING_REMOVAL = {}` | unjustified runtime deps == [] | unjustified = `['react-native-gesture-handler']` |
| d5 | `d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules` | absent from `dependencies` and `devDependencies`; absent from lock `packages[""].dependencies` and no `packages["node_modules/react-native-gesture-handler"]`; `!fs.existsSync(node_modules/react-native-gesture-handler)` | present everywhere |
| k1 | `k1 package.json declares the five SDK-54 packages at or above the patch expo install --check expects` | for expo ~54.0.37, expo-font ~14.0.12, expo-localization ~17.0.9, expo-screen-capture ~8.0.10, expo-updates ~29.0.20: the declared range starts with `~`, same major.minor, patch ≥ target | `~54.0.33`, `~14.0.11`, `~17.0.8`, `~8.0.9`, `~29.0.17` |
| k2 | `k2 package-lock.json and node_modules resolve the five packages at or above those patches` | lock `packages["node_modules/<p>"].version` and `node_modules/<p>/package.json` version: same major.minor, patch ≥ target | 54.0.34, 14.0.11, 17.0.8, 8.0.9, 29.0.17 |
| k3 | `k3 expo.install.exclude is exactly ["react-native-svg"]` (Q1 = exclude: `["eslint-config-expo", "react-native-svg"]`) | deep-equal | no `expo` key |
| k4 | `k4 eslint-config-expo is on the SDK-54 line (~10.0.x) in package.json, the lock and node_modules` (Q1 = align only; under Q1 = exclude this test instead pins `^55` + the exclusion reason in a comment) | devDependency range `~10.0.x`; lock + installed version 10.0.x | `^55.0.0` / 55.0.1 |
| k5 | `k5 offline expo-install consistency: every declared package the installed expo bundles satisfies its bundled range, apart from expo.install.exclude` | read `node_modules/expo/bundledNativeModules.json`; for every name in `dependencies` ∪ `devDependencies` that it lists and that is not excluded, the INSTALLED version satisfies the bundled range (supported forms: exact `x.y.z`, `~x.y.z`, `^x.y.z`; any other form fails the test by name); every excluded name must be one the bundle lists | `react-native-svg` 15.15.5 ∉ `15.12.1` and `eslint-config-expo` 55.0.1 ∉ `~10.0.0` (no exclude at base) |
| k6 | `k6 CI: the frontend-tests expo install --check step is blocking and no longer named non-blocking` | text-parse `.github/workflows/ci.yml` (split on `/\r?\n/`): inside `frontend-tests:` the step whose `run:` is `cd SmartCompareApp && npx expo install --check` is named exactly `Expo dependency drift` and its block (up to the next `- name:` at the same indent) has no `continue-on-error`; the job header (from `  frontend-tests:` to `    steps:`) has no `continue-on-error`. (Q3 = B: the `EXPO_OFFLINE=1 …` step named `Expo dependency drift (lockfile)` is blocking and the online step named `Expo SDK patch drift (report-only)` keeps `continue-on-error: true`.) | the step is named `… (non-blocking)` and carries `continue-on-error: true` |
| e1 | existing `e1 [CONSCIOUS PIN] …` | Q2 = keep: unchanged (green at base and after). Q2 = bump: asserts `'1.0.1'` → RED at base | — |

Semver helper for k1/k2/k5: a ~15-line in-file function (`parse x.y.z`, compare major/minor/patch); no dependency.

**Proving the reds (RED agent):** run the file alone at base; every id above except b11/b12/e1(keep) fails with a message naming the base value; paste the summary line. Then mutation spot-checks during GREEN: (i) revert `icon.png` to the base bytes → b1, b4, b7, b8 red; (ii) re-save `adaptive-icon.png` with the mark scaled 5 % larger → b7 and b9 red; (iii) delete `"expo"` from `package.json` → k3 (and k5) red; (iv) put `continue-on-error: true` back → k6 red; (v) corrupt one Paeth byte in the helper → b7 and b12 red. Restore from byte copies, sha-compare (session rules).

---

## 6. Gates (GREEN; cheapest first; print each tool's version first)

- **G1** `PYTHONIOENCODING=utf-8 <venv python> -m py_compile scripts/render_myez_icons.py` and `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache scripts/render_myez_icons.py` → clean.
- **G2** `<venv python> scripts/render_myez_icons.py` → four `name mode size sha256` lines; then `… --check` → exit 0. Run the render a second time and confirm every file sha256 is unchanged (determinism on this box).
- **G3** `npx expo install --check` → exit 0, "Dependencies are up to date", `react-native-svg` skipped by `expo.install.exclude`; `EXPO_OFFLINE=1 npx expo install --check` → exit 0.
- **G4** `npx expo-doctor` (orchestrator; it downloads `expo-doctor` into the npx cache) → the "packages match versions required by the installed Expo SDK" check passes; paste the full output; any OTHER failed check is compared with a base run (`git worktree add --detach` is NOT usable for this — no node_modules; the orchestrator runs doctor at base first or accepts the S69 record "1 check failed = the 7-package drift" at eed4ee10, `appstore_findings_verified.json` EXPO-09).
- **G5** `npx --no-install expo config --type introspect --json` → `icon ./assets/icon.png`, `splash.image ./assets/splash-icon.png` + `backgroundColor #ffffff`, `android.adaptiveIcon {foregroundImage ./assets/adaptive-icon.png, backgroundColor #ffffff}`, `web.favicon ./assets/favicon.png`, `expoPlist.EXUpdatesRuntimeVersion "1.0.0"` (Q2 = keep), `CFBundleShortVersionString "1.0.0"`, `CFBundleLocalizations ["en","ar"]`, `NSMicrophoneUsageDescription` = the U4a string, no `NSFaceIDUsageDescription`, the storyboard image view `SplashScreenLegacy` / `scaleAspectFit`; plugin list unchanged (p1). Paste the fragments into the PR body.
- **G6** jest, the W3-7 file alone: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/config/nativeBundle.w37.test.ts` → 0 failed, 0 skipped, 0 todo; expected `Tests: 58 passed, 58 total` (base 38 passed + b1/b2 now running + 18 new: b4–b14, d5, k1–k6; the two todos deleted).
- **G7** FULL jest: `timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci` → 0 failed. Expected if nothing else moves: suites `3 skipped, 351 passed, 351 of 354 total` (no new test FILE — the helper is not collected); tests `13 skipped, 13 todo, 3448 passed, 3474 total` (base 3,428 passed / 15 skipped / 15 todo / 3,458: +2 passed from b1/b2, −2 skipped, −2 todo, +18 new); snapshots `44 passed`; NO `.snap` in the diff. Explain any other delta. The known flake (§1.17) is re-run once if it appears.
- **G8** `timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit` → 0 errors (tsc includes `__tests__/**`); `timeout -k 15 600 node node_modules/eslint/bin/eslint.js <git diff --name-only --relative, *.ts only>` → 0 errors; ALSO `node node_modules/eslint/bin/eslint.js "src/**/*.{ts,tsx}"` (the CI step) → 0 errors, warning count reported against base (the eslint-config-expo change must not move it; base count measured before P4 or taken from a base run in the orchestrator's clone).
- **G9** P7 (app.json sha unchanged, Q2 = keep) and P8 (lock key diff within R7's set) re-printed; `npm ls --all` exit 0.
- **G10** `git status --short` = R12's list exactly; `git diff --stat` shows no whole-file rewrite; list every written file with its final sha256.

Backend pytest is NOT a gate for this unit (no backend file changes); the only Python file is the renderer (G1/G2).

---

## 7. Stated limits

- **No device verification.** Icon, adaptive icon and splash appearance are verified by pixel pins and a contact sheet, not on a phone. They reach users only through `eas build`; the preview build + 2-iPhone smoke test of runbook row 12 is where they are first seen for real.
- **Colour-to-alpha foregrounds are correct only over white.** `adaptive-icon.png` and `splash-icon.png` carry the ink at alpha 239–245 (not 255) because the white tile was removed exactly; over `#ffffff` they reproduce the master within 1 per channel. If Ahmed ever changes `android.adaptiveIcon.backgroundColor` or `splash.backgroundColor`, or wants Android 13 themed (monochrome) icons, re-render from a master with a real transparent background (R2 then needs a second input).
- **The composition is not re-centred.** The master's ink sits 32 px right of the tile centre (§1.14); every output preserves that offset.
- **Android paths not built.** The legacy splash path without `expo-splash-screen` (Android `Theme.App.SplashScreen` → `@drawable/ic_launcher_background`) and the adaptive icon are Expo-generated at build time and were not built in this lane (the launch lane is iOS). The Android notification small icon still derives from the launcher icon (no `expo-notifications` `icon`); on Android that renders as a white silhouette of an opaque square.
- **No iOS 18 dark / tinted icon variants** (`ios.icon` stays unset); iOS derives its own treatment.
- **`@expo/cli 54.0.27` was not diffed** (it builds the OTA bundle, not the binary); the runtime-JS conclusion in §1.3 covers the packages that end up IN the bundle (`expo`, `expo-font`, `expo-localization`, `expo-screen-capture`, `expo-updates`, `expo-file-system`, `expo-constants`) plus `babel-preset-expo` and `@expo/metro-config`.
- **Evidence gathering used the network** as the task allowed: `npx expo install --check` (Expo API), `npm view` and `npm pack` of the target tarballs into the scratchpad (read-only; nothing installed, no project file touched).
- **Pixel pins, not byte pins, cross platforms.** The renderer's `--check` compares pixels; the committed manifest pins the committed bytes. Pillow's LANCZOS is expected to be identical across x86-64/arm64 at 12.3.0 but a cross-platform re-render was not measured.
- **`expo-doctor` was not run at base by this spec** (it is not in the spec-writer's allowed tool set); G4 relies on the orchestrator.
- **773a9375 ← 6042506d is the task's statement**; the repo can prove only that `6042506d`'s lock carries the base native versions.
- **Lock regenerated by npm 11.6.2 locally, consumed by `npm ci` on CI's Node 20 (npm 10.x).** Lockfile v3 is read by both; the CI run of the PR is the proof that `npm ci` accepts it.

---

## 8. Open questions for the orchestrator

**Q1 — `eslint-config-expo`: ALIGN to `~10.0.0` (recommended, default) or EXCLUDE.**
Evidence: the 10.0.0 and 55.0.1 tarballs differ in `package.json` only (version, gitHead, `eslint-plugin-expo` `^1.0.0` vs `^1.0.3`); every config file is byte-identical and the installed `eslint-plugin-expo 1.0.3` satisfies both ranges (§1.4), so aligning changes ZERO lint rules while making `expo install --check` clean without widening `expo.install.exclude` beyond the one native module whose drift is deliberate. `^55.0.0` arrived with the flat-config commit `84a4fd24` (2026-05-11), not as a considered SDK choice. Excluding would only make sense to track the SDK-55 config line on purpose — no evidence of that. Risk of aligning: none measured; G8 (eslint on `src` + changed files, warning count vs base) is the proof.

**Q2 — `expo.version`: KEEP `1.0.0` (recommended) or bump to `1.0.1` in this unit.**
Evidence (§1.3, §1.16):
- The testers' preview binary (stated: 773a9375 from `6042506d`) carries exactly the base native versions. After U4b, an `eas update --branch preview` from main would carry JS built against expo 54.0.37 et al. to that binary.
- The only runtime-bundled JS that changes is `expo/src/winter/TextDecoder.ts`, a self-contained pure-JS polyfill (no native calls). `expo-updates`' runtime JS is unchanged (its diff is native + build-time CLI). `expo-font` / `expo-localization` change only config plugins (build time) and the web loader. `expo-modules-core` (3.0.30) and `react-native` (0.81.5) do not move. So a post-U4b OTA is measured JS-compatible with the 1.0.0 binary; the gesture-handler native module left in that binary is simply never referenced (0 imports).
- The native changes are fixes that matter but ride only a new binary: `expo-updates` rejects manifests whose asset keys contain path separators (security, #48762/#48763); `expo-file-system` Android path-traversal fixes; `expo-screen-capture`'s iOS black-screen-after-allow fix (the app's 4 auth screens call it on unmount); an Android fetch stream close fix in `expo`.
- `main` ALREADY carries U4a's native-only `app.json` changes (#254) at 1.0.0 — a bump here would not mark "the" native boundary; it would only re-target every later OTA to runtime 1.0.1, which no installed binary has, so the session-69 client units that are main-only (#251 #253 #255 #257 #258 #269 #274) could no longer reach the testers by the planned `eas update --branch preview` until a new preview build exists.
- CLAUDE.md's rule ("bump `expo.version` for every native change … never for a JS-only hotfix") is written for AFTER launch (`APP_STORE_LAUNCH_RUNBOOK.md:301`, §5: "Changes after launch need a new `expo.version` (BLD-BP-05)"); the store has never received a build, and the first App Store version would become 1.0.1 for no user-visible reason.
Recommendation: keep 1.0.0 and record the rule (R8's `e1` comment + the PR body): *"The U4b native fixes reach testers only through a new preview BUILD; before the first `eas update --branch preview` from a main that contains U4b, run `npm ls` and confirm the runtime-JS delta is the one measured in this spec. From the first production build on, every native change bumps `expo.version`."* If the orchestrator prefers a hard boundary (bump), the price is: e1 flips to 1.0.1, `app.json` changes, and the next tester-visible anything needs a new preview build.

**Q3 — the CI ratchet: the task as written (blocking ONLINE check, default in R10/k6) or split (recommended).**
Evidence (§1.1): the online check's expected versions come from the Expo API and move with every SDK-54 patch (four releases in 2026: 04-27, 05-28, 07-15, 08-17). As a blocking step in the required-looking `frontend-tests` job it reddens every PR on an unchanged main within ~1–2 months, and the only fix is another native bump + build. `EXPO_OFFLINE=1` makes the same command compare the lockfile-installed packages with the INSTALLED expo's `bundledNativeModules.json` — deterministic, and it still catches every drift a repo change can introduce (k5 pins the same rule in jest). Recommended: blocking offline step + report-only online step (R10 alternative text). The RED agent needs this ruling before writing k6.

**Q4 — the in-app glyph.** The JS `SplashScreen` (`src/screens/SplashScreen.tsx:112`) shows `QarenLogo` (the old Q-ring) at 128 pt immediately after the native MYEZ splash, and the same component heads Home, Profile, History, onboarding Step 1 and the loading rings. Out of U4b's scope (JS/UI, OTA-capable). Recommend a follow-up unit (U4c) that renders the MYEZ mark in-app; it can ride an OTA.

**Q5 — optional native icon fields.** Android notification small icon (`expo-notifications` `icon`, a white-on-transparent silhouette), `android.adaptiveIcon.monochromeImage` (Android 13 themed icons) and iOS 18 `ios.icon.{dark,tinted}` are all unset and stay unset here (Apple-first lane; each needs its own art decision). Confirm they are follow-ups, not launch blockers.

**Q6 — renderer location.** `scripts/render_myez_icons.py` (default: CLAUDE.md names `scripts/` for this; covered by CI ruff) or `docs/brand/render_myez_icons.py` (keeps the brand source and its generator together, outside backend lint). The b14 path follows the ruling.

---

## Review corrections (BINDING - supersede the body)

Adversarial review, 2026-09-30 03:38–03:59 AST, worktree at `94c097cd` (clean except this folder), spec sha256 before review `e0c3ad45d4a2fb21d84caf5c41c8819c8e918bd0e3776325cf6a877b138ce362`. Read-and-measure only; no network, no install. Evidence files are in the reviewer's scratchpad `…/scratchpad/u4b-adv/` (`notes.md`, `png_facts_adv.json`, `rediff_report.txt`, `rngh_code_refs.txt`, `jest_w37_base.log`, `jest_full_base.log`, `npm_ls_all_base.txt`, `lock_6042506d.json`).

### Re-measured and CONFIRMED (no change)

- Master PNG: 146,295 B, sha256 `70b2f826…4b41`, IHDR 2048×2048 / 8 / ct 6 / interlace 0; alpha 0 / 255 / partial = 180,868 / 4,010,750 / 2,686; ink bbox 483…1627 × 399…1640 (1145 × 1242); max non-white radius 869.149; row-0 first/last α≥128 at 439/1608; diagonal 135; emerald `(16,185,129)` (Pillow 12.3.0 + raw IHDR, `png_measure.py`).
- Base assets: shas, IHDR and modes exactly as §1.15.
- Prototype (`proto/out1` vs `out2`): byte-identical; icon RGB ct 2 with white corners; adaptive ct 6, max α>0 radius 305.57 ≤ 312.89, α bbox (320,290,726,731); splash α bbox width 312; favicon 48² ct 6. The contact sheet shows the intact mark inside the safe circle.
- Drift list, offline vs online semantics, install order (`installAsync.js` installs `expo` then spawns the follow-up), the exclude log line, exit codes (`checkPackages.js`: 0 "Dependencies are up to date", 1 "Found outdated dependencies").
- `bundledNativeModules.json` and `expo` `dependencies` deltas 54.0.34 → 54.0.37: exactly the keys in §1.2.
- Independent re-diff of the writer's target tarballs against `node_modules` (`rediff.py`): the only runtime-bundled JS change is `expo/src/winter/TextDecoder.ts` (427 lines, zero `require`/`import`/`global`, loaded lazily by `src/winter/runtime.native.ts:8`); `expo-updates` `build/` unchanged (its JS delta is `cli/` + `utils/` only); `expo-file-system` / `expo-constants` / `expo-screen-capture` JS unchanged; `eslint-config-expo` differs in `package.json` only (3 lines).
- `6042506d` lock vs base lock: 4 version differences, all JS (axios, form-data, hasown, intl-pluralrules); zero native-package differences.
- Gesture-handler: only `package.json:50` and the W3-7 test lines outside docs; navigators are `native-stack` + `bottom-tabs`; lock removal = exactly `react-native-gesture-handler`, `@egjs/hammerjs`, `@types/hammerjs` (`hoist-non-react-statics` also used by `@sentry/react`, `invariant` by 10+ packages).
- `@expo/prebuild-config` 54.0.8 code for the icon (`withIosIcons.js:181-201`) and the legacy splash (`getIosSplashConfig.js` root branch; `InterfaceBuilder.js:89-90` 414×736 full-screen).
- Jest baselines: W3-7 file `Tests: 2 skipped, 2 todo, 38 passed, 42 total`; full suite `3 skipped, 351 passed, 351 of 354` / `15 skipped, 15 todo, 3428 passed, 3458 total` / `44 passed` snapshots, rc 0. G6 (58) and G7 (3448 / 13 / 13 / 3474) arithmetic holds.
- `npm ls --all` at base exits 0 (only `UNMET OPTIONAL` lines), so G9 is satisfiable. `testMatch` is `**/__tests__/**/*.test.ts(x)`, so `__tests__/helpers/pngDecode.ts` is not collected. No `.snap` embeds icon bytes; no `src/**`, test or script references an asset PNG.

### Corrections

1. **§1.14 chunk list.** The master is `IHDR`, **37** `IDAT`, `IEND`, not a single `IDAT`. R9's "concatenate every IDAT" is load-bearing. All 2,686 partial-alpha edge pixels are RGB `(255,255,255)` (0 non-white), so flattening onto white yields a pure white square with no ghost ring — this confirms R3's icon design.

2. **Network belongs to the orchestrator (session rule 8).** The ONLINE `expo install --check` fetches the Expo versions API (`getVersionedPackages.js:84`, `bundledNativeModules.js:84`), and G4 downloads `expo-doctor`. The GREEN agent therefore runs only `EXPO_OFFLINE=1 npx --no-install expo install --check` and `EXPO_OFFLINE=1 npx --no-install expo config --type introspect --json`. The online halves of P5 and G3, and G4, are the orchestrator's. §3 is amended from "the GREEN agent does P0, P1 and P5–P8" to "P0, P1, P5-offline, P6–P8".

3. **Resolved versions on the day must equal the measured set, or Q2's evidence lapses.** P3's `expo@~54.0.37` takes the highest 54.0.x, and the spawned follow-up takes the Expo API's versions (online mode prefers the remote map: `getCombinedKnownVersionsAsync`, "Prefer the remote versions"). A patch published before GREEN would be installed silently. Expo is still publishing: the registry `time.modified` of `expo`, `expo-font`, `expo-localization` and `expo-screen-capture` is 2026-09-29 (`npm_view.txt`). §1.3 covers only expo 54.0.37, expo-font 14.0.12, expo-localization 17.0.9, expo-screen-capture 8.0.10, expo-updates 29.0.20, expo-file-system 19.0.24, expo-constants 18.0.14, babel-preset-expo 54.0.12 and @expo/metro-config 54.0.17. **Binding:** P6 prints the installed version of each of these nine. If ANY differs, STOP. The orchestrator re-runs the §1.3 tarball diff for the new versions, and GREEN continues only if the bundled runtime-JS delta is still self-contained pure JS; record the outcome in the PR body. R6's "or a later SDK-54 patch" clause is conditional on this re-diff.

4. **The Q2 rule must be executable.** "Run `npm ls` and confirm the runtime-JS delta is the measured one" cannot be done: `npm ls` prints versions, not a JS delta. **Replace the rule** (e1 comment + PR body) with: *"Before the first `eas update --branch preview` from a main that contains U4b: (a) `npm ls` shows exactly the version set recorded in the U4b PR body; (b) diff `@expo/cli` `build/src/export/**` (the code `eas update` runs; not diffed in §1.3, see §7) between 54.0.24 and the installed version, or smoke-test that OTA on one tester device before announcing it; (c) any later expo-package bump repeats (a)–(b) or bumps `expo.version`. From the first production build on, every native change bumps `expo.version`."*

5. **Re-read the build-time icon/splash code after the bump.** §1.10 and §1.11 were read from the installed `@expo/prebuild-config` 54.0.8 (`@expo/cli` 54.0.24 declares `^54.0.8`). `@expo/cli` moves to 54.0.27, and its prebuild-config range was not measured. **G5 is extended:** print the installed `@expo/prebuild-config` version after P3. If it changed, grep `plugins/icons/withIosIcons.js` (`removeTransparency`, `'#ffffff'`, `'cover'`), `unversioned/expo-splash-screen/getIosSplashConfig.js` (root `config.splash` branch: `enableFullScreenImage_legacy: true`, `imageWidth: 200`) and `InterfaceBuilder.js` (414 / 736), and paste the lines. The splash art's 30 % sizing is valid only while the legacy full-screen `scaleAspectFit` path holds.

6. **Android legacy splash size (a limit the spec does not state).** In `getAndroidSplashConfig.js:43-55`, the root-`splash` branch sets `imageWidth: 200`. `withAndroidSplashImages.js:167-190` then resizes the image with `contain` to 200 dp inside a 288 dp canvas, and `withAndroidSplashDrawables.js:34-48` centres it. With the ink at 30 % of the canvas, the Android legacy wordmark is about 60 dp wide, against about 112–132 pt on iOS. **Add to §7:** this is accepted for the Apple-first lane. A balanced Android splash needs the `expo-splash-screen` plugin, which is a new native dependency and belongs in a follow-up.

7. **iOS launch-screen caching (add to §7 and to the runbook row-12 device check).** iOS caches the launch-storyboard snapshot per install. This is known platform behaviour and was not measured here. A tester who updates over the old preview build can keep seeing the old template launch screen until the app is deleted and reinstalled, or the device is restarted. The first device verification of the MYEZ splash therefore uses a fresh install.

8. **Backend tests read `ci.yml`, so "Backend pytest is NOT a gate" (§6) is wrong.** `tests/test_ci_gates.py` YAML-parses `.github/workflows/ci.yml` (`:33`, job and step assertions incl. `:186`). `tests/test_channel_freshness.py` and `tests/test_hermeticity_pins.py` also read it. **Add G11:** `PYTHONIOENCODING=utf-8 <venv python> <scratchpad>/harness/pyt.py --bound 600 --tag u4b-ci --log <scratchpad>/u4b-ci.log --cwd <worktree> -- tests/test_ci_gates.py tests/test_channel_freshness.py tests/test_hermeticity_pins.py` must show 0 failed; paste the `[pyt]` line. `tests/` is not edited.

9. **Black allowlist ratchet.** The header of `.github/black-clean-paths.txt` says "Added a new .py file? It should be black-clean, so add it here". The last new script, `scripts/check_channel_freshness.py` (W3-13, `4ef632f5`), was added there. `tests/test_ci_gates.py::test_black_allowlist_entries_are_actually_clean` verifies every entry. **Binding:** the renderer is black-clean under the pinned `black==26.5.1` (`requirements-dev.txt:3`; present in the venv) and gets one line in `.github/black-clean-paths.txt`. G1 adds `<venv python> -m black --check scripts/render_myez_icons.py`. R12's file list gains `.github/black-clean-paths.txt`. G11 above covers the allowlist test.

10. **Manifest line endings.** `core.autocrlf=true` and there is no `.gitattributes`. Every text file checks out CRLF on this box: `git ls-files --eol` shows `i/lf w/crlf` for ci.yml, package.json, app.json and scripts/*.py, and `i/-text` for the PNGs. **Binding:** (a) the renderer writes the manifest with `open(path, "w", encoding="utf-8", newline="\n")`, because Python text mode on Windows writes CRLF otherwise; (b) `--check` compares the manifest as `json.loads(on_disk) == fresh_dict`, never as bytes, because a fresh Windows checkout holds a CRLF manifest and a byte compare would fail on an unchanged tree. The PNG sha256 pins are unaffected (binary files).

11. **`babel-preset-expo` is a direct dependency.** `package.json` declares `~54.0.10`, while expo 54.0.37 requires `~54.0.12`. The base lock has exactly one copy (`node_modules/babel-preset-expo` 54.0.10), and `babel.config.js` resolves it from the root. **P8 must show** exactly one `…/babel-preset-expo` key, at ≥ 54.0.12. If npm nests `node_modules/expo/node_modules/babel-preset-expo` instead, the app keeps transforming with 54.0.10. In that case bump the declared range to `~54.0.12` (the only allowed exception to R6's "byte-unchanged") and re-run P8.

12. **Code-level gesture-handler evidence (the spec walked manifests only).** `grep -rl react-native-gesture-handler` over every installed `.js/.mjs/.cjs/.ts/.tsx`, outside the package itself, finds 11 files:
    - `react-native-screens/{src,lib/commonjs,lib/module,lib/typescript}/gesture-handler/*`, the opt-in `react-native-screens/gesture-handler` subpath (listed in its `files`). Nothing in `src/`, `App.tsx`, `index.ts` or `@react-navigation/*` imports it, and `react-native-screens/src/index.tsx` does not reference it.
    - One comment in `react-native/Libraries/NativeComponent/ViewConfigIgnore.js`.
    - `@expo/cli`'s `createExpoAutolinkingResolver.js:43` list, labelled "Peer dependencies from expo-router"; the app has no `expo-router`.

    No bundled module requires the package, so Metro cannot fail to resolve it after P2. R11's correction line may cite this. It confirms the removal and adds no requirement.

13. **RED-phase scope.** b12 is "GREEN at base" only if the RED agent writes `__tests__/helpers/pngDecode.ts` (R9) together with the test edits. Without the helper the file fails to import and every test in it reds. **Binding:** the helper is RED-phase test infrastructure. §5's "NOTHING else" excludes only the product files: assets, `package.json`/lock, `node_modules`, `docs/brand/`, `scripts/`, `ci.yml`, the runbook and the black allowlist. With `PENDING_REMOVAL = {}`, the real-app halves of d2 and d4 become vacuous by design; d5 replaces them, and their fixture halves still run. Accepted.

14. **§1.1 publish dates are unverified.** "54.0.34 2026-04-27 … 54.0.37 2026-08-17" and `dist-tags.sdk-54` are not in the saved evidence: `npm_view.txt` has no `time` or `dist-tags` rows. They cannot be re-measured offline, so treat them as supporting colour only. The Q3 ruling below does not depend on them.

### Answers to the writer's open questions (RECOMMENDATIONS; the orchestrator rules)

- **Q1 → ALIGN `eslint-config-expo` to `~10.0.0`.**
  - The re-measured diff of `package.json` is 3 lines: version, gitHead, and `eslint-plugin-expo` `^1.0.0` vs `^1.0.3`. Every config file is byte-identical, and the installed `eslint-plugin-expo` 1.0.3 satisfies both ranges.
  - `bundledNativeModules.json` lists `eslint-config-expo: ~10.0.0` at both 54.0.34 and 54.0.37.
  - Aligning keeps `expo.install.exclude` to `react-native-svg` alone. G8's warning-count comparison is the proof.

- **Q2 → KEEP `expo.version` 1.0.0, conditional on corrections 3 and 4.** Evidence, independently re-derived:
  - The only bundled runtime-JS delta is the self-contained TextDecoder polyfill.
  - The runtime JS of `expo-updates`, `expo-file-system` and `expo-constants` is unchanged, and `expo-modules-core` (3.0.30) and `react-native` (0.81.5) do not move.
  - `6042506d` → base has zero native version differences.
  - Main already carries U4a's native `app.json` changes at 1.0.0.

  A bump would strand every tester's preview binary from the pending session-69 client OTAs. The task's keep-option wording ("the next preview BUILD must precede any further OTA") is deliberately replaced by the executable check in correction 4, because the evidence shows the post-U4b JS runs on the 1.0.0 binary. If the orchestrator prefers the stricter rule, the cost is that no preview OTA ships until a new preview build exists.

- **Q3 → B (split): a blocking `EXPO_OFFLINE=1` step plus a report-only online step.**
  - The online expected map is the Expo API's and is preferred over the lockfile-installed bundle (`getCombinedKnownVersionsAsync`). It changes on Expo's schedule, not the repo's.
  - `getRemoteVersionsForSdkAsync` rethrows every non-`OFFLINE` API error. A blocking online step therefore also goes red on an Expo API outage.
  - `frontend-tests` is one of the jobs CLAUDE.md records as REQUIRED since M18. A blocking online step would block every merge on an unchanged main.
  - The offline step is deterministic against the lock and still catches every drift a repo change can introduce. Keep k5 as the in-jest twin. The ratchet the runbook asks for is still satisfied, because the offline step blocks.

- **Q4 → a follow-up unit U4c (the in-app MYEZ glyph, OTA-capable).** Confirmed at `SplashScreen.tsx:112` (128 pt), `HomeScreen.tsx:900`, `ProfileScreen.tsx:355`, `HistoryScreen.tsx:939`, `Step01Welcome.tsx:76` and `LoadingRings.tsx:212`. Recommend landing U4c BEFORE the production build if the schedule allows. The store binary runs exactly the JS it was built with, and App Review would see the Q-ring right after the MYEZ native splash. Otherwise ship it later with `eas update --branch production`, never `preview`.

- **Q5 → confirmed as follow-ups, not launch blockers.** `withIosIcons.js` emits one opaque 1024 universal icon from `expo.icon`, which is all App Store submission needs. iOS 18 dark and tinted variants are optional, and without them iOS uses or derives from the light icon. The Android notification small icon and `monochromeImage` are outside the Apple lane. The legacy-splash Android sizing (correction 6) joins this follow-up list.

- **Q6 → `scripts/render_myez_icons.py`.** CI's blocking `ruff check --select E9,F63,F7,F82 --no-cache app/ scripts/ tests/` (`ci.yml:170`) covers it, it follows the CLAUDE.md blocker #1 wording, and correction 9 adds the black allowlist line. No backend test imports every script. The only test that walks `scripts/` does a text search for `cleanup_expired_ratings` (`tests/test_retro_w1_2b.py:344-356`), which is unaffected.

**Verdict: APPROVED_WITH_CORRECTIONS.** The design and every load-bearing measurement hold. The corrections are gates and guards, not a redesign.
