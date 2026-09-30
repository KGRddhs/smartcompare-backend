# U4b spec notes, started Wed Sep 30 03:03:48 AST 2026
base 94c097cda4e3d63562c5e40e444f4965c4a0222d
## deps (03:03-03:15)
- expo install --check at base: 7 rows (expo 54.0.34->~54.0.37, font 14.0.11->~14.0.12, loc 17.0.8->~17.0.9, screen-capture 8.0.9->~8.0.10, updates 29.0.17->~29.0.20, rn-svg 15.15.5 expected 15.12.1, eslint-config-expo 55.0.1 expected ~10.0.0). expo CLI 54.0.24 (network fetch of versions API).
- package.json has NO "expo" key (no install.exclude).
- expo-splash-screen NOT installed; app.json uses legacy root "splash" key -> prebuild-config getIosSplashConfig: enableFullScreenImage_legacy true, imageWidth 200 (iOS: image view full-screen, contentMode from resizeMode contain); Android imageWidth 200.
- tarball diffs (pkgdiff_report.txt): expo 54.0.37 native: android NativeResponse.kt + build.gradle; JS: src/winter/TextDecoder.ts rewrite (pure JS, no requires). expo-font: config plugin (Android) + web loader only. expo-localization: config plugin prevalidation only. screen-capture: ios ScreenCaptureModule.swift (+removeFromSuperview). expo-updates: 16 native files (path-separator security fix, reaper, loaders), JS only cli/utils. expo-file-system 19.0.24 (transitive): native only (Android path traversal fix, iOS ph:// copy). expo-constants 18.0.14: build.gradle only. autolinking 3.0.27: JS build-time. babel-preset-expo 54.0.12: router-root path guard.
- eslint-config-expo 10.0.0 vs 55.0.1: ONLY package.json differs (version, gitHead, eslint-plugin-expo ^1.0.0 vs ^1.0.3); installed eslint-plugin-expo 1.0.3.
- preview binary commit 6042506d lock: same native versions as base (expo 54.0.34, updates 29.0.17, ...).
- expo install with expo in list: installs expo first then awaits spawn of `npx expo install <rest>` under new CLI; autoAddConfigPlugins adds nothing (font+localization already in plugins, updates is AUTO_PLUGIN, screen-capture has no plugin).
- rngh walk: 1067 manifests, only devDependencies edges (@testing-library/react-native, reanimated, screens).
## png + splash + icons (03:15-03:40)
- master 2048x2048 RGBA ct6, chunks IHDR/IDAT/IEND only, sha 70b2f826...; alpha0 180,868 px, alpha255 4,010,750, partial 2,686. tile white exact (255,255,255,255). corners transparent. circular corner radius fit r=461.0 px (0.2251 side), rms 0.076 px, symmetric (row0 first/last >=128: 439/1608; diag 135).
- ink (d>40 from white) incl bbox x483..1627 y399..1640 (1145x1242); any non-white 483..1628 x 399..1640 (1146x1242); black exact (10,10,11); emerald exact (16,185,129) dot bbox 1419..1552 x 1507..1639 (~134 px). ink bbox centre (1055.5,1019.5) vs tile centre 1023.5.
- base assets: icon.png P ct3 1024 sha 74c6...; adaptive==splash P ct3+tRNS 1024 sha 5f4c...; favicon LA ct4 48x48 interlaced sha 2427...
- introspect base: icon ./assets/icon.png; splash {image,contain,#ffffff}; adaptiveIcon fg ./assets/adaptive-icon.png bg #ffffff; web.favicon; no ios.icon, no notification icon (expo-notifications plugin only color #10B981); storyboard imageView SplashScreenLegacy scaleAspectFit pinned to 4 edges; EXUpdatesRuntimeVersion 1.0.0; CFBundleShortVersionString 1.0.0.
- prebuild withIosIcons: 1024 cover, removeTransparency + bg #ffffff for light/tinted; dark variant keeps alpha.
- prototype render (proto/render_proto.py): deterministic 2 runs same sha. icon RGB 2530d5b3...; adaptive RGBA b336b66b... max alpha radius 305.57 <= 312.89 safe; splash RGBA bf8df272... (30% width, bbox 364..676 x 342..679); favicon RGBA 48 3d225c46...
- JS splash (src/screens/SplashScreen.tsx:112) renders QarenLogo (old Q-ring SVG) size 128 + t('app.name') -> brand jump after native splash; QarenLogo used in 6 surfaces. out of scope -> open question.
- CI: expo install --check remote expectations drift with each SDK-54 patch (54.0.34 04-27, .35 05-28, .36 07-15, .37 08-17); EXPO_OFFLINE=1 at base reports only svg + eslint-config-expo.
- uninstall rngh removes lock pkgs: rngh, @egjs/hammerjs, @types/hammerjs (hoist-non-react-statics + invariant stay).
- metro-config 54.0.15->54.0.17: getPkgVersion refactor + web css escaping; no native-bundle change.
## jest base (03:23-03:28)
- nativeBundle.w37 alone at base: 38 passed, 2 skipped (b1,b2), 2 todo (b3-todo,d3), 42 total. jest 29.7.0.
- FULL jest at base, 3 runs: run1 1 failed (HistoryScreen.mobileJank.m21 describe MB-flows-08 :127, flake; passed alone 4/4) ; run2 no FAIL lines; run3 351 passed/3 skipped suites (354), 3428 passed/15 skipped/15 todo (3458), 44 snapshots, 10.1 s.
- eas.json: preview channel preview, production channel production autoIncrement, appVersionSource remote.
- line endings: package.json, lock, app.json, w37 test, ci.yml, runbook are i/lf w/crlf. no .gitattributes.
- tsconfig types [jest,node] -> @types/hammerjs removal inert.
- pngjs 3.4.0 installed only via parse-png <- @expo/image-utils (undeclared) -> use node zlib.
- spec written 03:37: docs/investigations/2026-09-30-session-70-state/U4B_ICONS_DEPS_SPEC.md
