# U4a — native config for the first App Store build (app.json only; no dependency changes) — unit spec

> **RENAME NOTICE (Ahmed, 2026-09-30, binding — supersedes every "Qaren" / "قارن" display string below):** the app is renamed **MYEZ** (Arabic **ميّز**). For THIS unit that means: `expo.name` becomes `"MYEZ"`, `locales/en.json` `CFBundleDisplayName` = `"MYEZ"`, `locales/ar.json` `CFBundleDisplayName` = `"ميّز"`, and every purpose string reads "MYEZ only uses the camera…" / the Arabic equivalent with ميّز. The bundle identifier `com.qaren.app`, the slug `qaren`, the scheme `qaren://` and the EAS project id are UNCHANGED (invisible to users; changing them would orphan the credentials and deep links). A red assertion that pins `Qaren` / `قارن` as the display name is WRONG by this notice: the green agent corrects it, quoting this paragraph as the evidence. Other in-app brand strings (i18n catalogs, legal, landing) are a separate rename unit, not U4a.

**Session 69, audit findings EXPO-04 / SA-03 / BLD-BP-09 (iPad), EXPO-07 (microphone string), EXPO-08 (Face ID string), EXPO-10 / SA-10 (Arabic bundle localization), PM-5 / PM-6 (privacy manifest gaps).** Owner: Claude. Everything here is NATIVE (needs the production `eas build`, cannot ride an OTA), so it must merge before Ahmed's build. The icon files (D4) and the dependency bumps / gesture-handler removal (they touch the SHARED `node_modules` junction and must run alone in the clone) are **U4b**, not this unit.

## 1. Measured base (main `89f2dc6a`, `SmartCompareApp/app.json`)

- `ios.supportsTablet: true` (line 18) → Info.plist allows all four iPad orientations, `UIRequiresFullScreen=false`; the app has zero iPad layout code; App Store Connect then requires 13-inch iPad screenshots and the reviewer may test on an iPad. Launch runbook decision **D1, recommended A = false for 1.0.0** (the orchestrator applies A; the PR body flags it for Ahmed).
- `expo-camera` plugin: `microphonePermission: false`, `expo-image-picker` plugin: `microphonePermission: false` (W3-7) → no `NSMicrophoneUsageDescription`, while the installed expo-camera binary still links `AVCaptureDevice … .audio` (`node_modules/expo-camera/ios/Common/CameraPermissionsRequester.swift:106-113`, `Current/CameraSessionManager.swift:147`). Apple's upload scan can flag ITMS-90683 for a linked protected API without a purpose string; no production upload has ever tested it.
- `NSFaceIDUsageDescription` is generated (EXPO-08: a plugin default for a feature the app never uses — find WHICH plugin emits it with `npx expo config --type introspect` and read that plugin's options; `expo-secure-store` has `faceIDPermission`).
- No `CFBundleLocalizations` / no `locales` entry: the home-screen name and the camera/photo purpose strings are English-only on an Arabic device, and App Store Connect may not list Arabic under Languages.
- `ios.privacyManifests` (12 collected types) lacks `NSPrivacyCollectedDataTypeCustomerSupport` (the in-app Contact Us form sends support text) and lacks `NSPrivacyCollectedDataTypePurposeProductPersonalization` on `SearchHistory` and `ProductInteraction` (both feed cohort/priority personalization). `docs/privacy-data-inventory.md` is kept equal to app.json by a jest test — both must change together.

## 2. Target (R = requirement)

R1. `ios.supportsTablet: false`. Introspected Info.plist: no `UISupportedInterfaceOrientations~ipad` entry (or only portrait), `UIDeviceFamily` = iPhone only (`[1]`) — verify by `npx expo config --type introspect` (read-only; never `expo prebuild`).
R2. `expo-camera` plugin `microphonePermission` and `expo-image-picker` plugin `microphonePermission` both set to the honest string **"Qaren only uses the camera to photograph products. Audio is never recorded."** (`recordAudioAndroid: false` stays). Introspected plist has `NSMicrophoneUsageDescription` with that exact string; the Android manifest still has no `RECORD_AUDIO` (it stays in `blockedPermissions`).
R3. Face ID: pass the option that REMOVES `NSFaceIDUsageDescription` from the emitting plugin (`faceIDPermission: false` on `expo-secure-store` if that is the source — confirm by introspection before and after). If removal is impossible without dropping the plugin, keep the key with an honest string and record why.
R4. Arabic bundle localization: `expo-localization` plugin options `supportedLocales: { ios: ["en", "ar"], android: ["en", "ar"] }` (SDK 54 plugin — read `node_modules/expo-localization/plugin/build/*.js` for the exact option names) AND top-level `expo.locales: { "en": "./locales/en.json", "ar": "./locales/ar.json" }` with `SmartCompareApp/locales/en.json` = `{ "CFBundleDisplayName": "Qaren", "NSCameraUsageDescription": "<the EN camera string>", "NSPhotoLibraryUsageDescription": "<the EN photos string>", "NSMicrophoneUsageDescription": "<R2 string>" }` and `locales/ar.json` with `"CFBundleDisplayName": "قارن"` and native-quality MSA translations of the three strings (no diacritics; copy policy applies). Introspection must show `CFBundleLocalizations` containing `ar` (or the equivalent the plugin emits) and the locale files wired.
R5. Privacy manifest: add the `CustomerSupport` collected type (linked true, tracking false, purpose AppFunctionality) and add `NSPrivacyCollectedDataTypePurposeProductPersonalization` to `SearchHistory` and `ProductInteraction`. Update `docs/privacy-data-inventory.md` in the same commit so the parity jest test passes, and add the CustomerSupport row to the inventory with the Contact Us form as its source.
R6. Nothing else in app.json changes (the diff is reviewable line by line). `package.json`, `package-lock.json`, `node_modules` untouched.

## 3. Tests (RED at base)

T1. Extend `__tests__/config/nativeBundle.w37.test.ts` (keep every existing assertion that stays true; flip the ones this unit deliberately changes, e.g. "no NSMicrophoneUsageDescription" becomes "the honest string is present"): supportsTablet false; the mic string on both plugins; Face ID key absent after introspection (use the same in-process plugin execution the file already uses — `w37_plugin_exec`-style — never prebuild); `supportedLocales` and `locales` present; the two locale files exist, parse, and carry the four keys with the AR display name `قارن`; manifest: CustomerSupport present, ProductPersonalization on the two types.
T2. The inventory-parity test (find it: grep `privacy-data-inventory` in `__tests__`) stays green only when the inventory changed too — no edit needed unless it hard-codes the type list.
T3. Existing tests are the regression net: the whole `__tests__/config/` folder and any test reading app.json.

## 4. Gates

- jest by path: `'nativeBundle|config/|privacy|inventory|i18nFence'` under `timeout -k 15 900`; then the FULL suite (orchestrator).
- `npx tsc --noEmit`; eslint by path.
- `npx expo config --type introspect` (read-only) — paste the relevant plist/manifest fragments into the PR body as evidence; `npx expo-doctor` result unchanged (still the 7 out-of-date packages, handled by U4b).
- `git diff --stat` shows only app.json, the two new locale files, `docs/privacy-data-inventory.md`, the W3-7 test (and the inventory test if it hard-codes types).

## 5. Rulings

- R-A: D1 is applied as option A (`supportsTablet: false`) and stated in the PR body; if Ahmed answers B the change is a one-line revert before the build.
- R-B: the mic string is deliberately honest rather than the Expo boilerplate; Apple reads purpose strings for accuracy.
- R-C: icons and dependency bumps are U4b — do not touch them here.
- R-D: never `expo prebuild`, never write `ios/` or `android/`; introspection only.
- R-E: never `git checkout --`; `node_modules` is a junction — never delete or reinstall.
