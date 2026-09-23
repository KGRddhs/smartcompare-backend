# W3-7 — the native-only App Store bundle (ONE `eas build`)

## 1. Header

| field | value |
|---|---|
| unit | W3-7 |
| findings | MB-TWO-LEVER-RELEASE-02 (RECORD_AUDIO + boilerplate NSMicrophoneUsageDescription, P1), MB-TWO-LEVER-RELEASE-08 (no NSPrivacyCollectedDataTypes, P3), MB-TWO-LEVER-RELEASE-09 (runtimeVersion pinned to appVersion 1.0.0, P3), MB-SAFE-HYGIENE-01 (template launcher PNGs, P1), MB-SAFE-HYGIENE-06 (`react-native-gesture-handler` orphan dep, P3) |
| OTA class | **needs-build** for every config half (app.json permissions + plugin options, `ios.privacyManifests`, the eventual icons, the eventual dependency removal — none of these can ride `eas update`); **ci-only** for the test file + the committed inventory doc. Nothing in this unit is OTA-safe and nothing touches the backend. |
| base SHA | `ed75dc708b82c0b911c9de8a3e59d4418c6e278c` (worktree `sc-w3-native`, `git status` empty at start and at the end of this spec) |
| flag | none — config, docs and tests only; no runtime behaviour changes |
| installed toolchain (measured, see §10) | typescript **5.9.3** (pin `~5.9.2`), jest 29.7.0, ts-jest 29.4.9, expo **54.0.34** (pin `~54.0.33`), expo-camera **17.0.10** (pin `~17.0.10`), expo-image-picker **17.0.11** (pin `~17.0.11`), @expo/config-plugins 54.0.4, @expo/prebuild-config 54.0.8, @expo/config-types 54.0.10, @expo/plist 0.4.8, react-native-gesture-handler **2.28.0** (pin `~2.28.0`), react-native-screens 4.16.0, @react-navigation/native-stack 7.15.0, bottom-tabs 7.16.0, react-native-reanimated 4.1.7, react-native-worklets 0.5.1 |

Client tools by path only (`node node_modules/typescript/bin/tsc`, `node node_modules/jest/bin/jest.js`, `node node_modules/eslint/bin/eslint.js`); `tsc -v` printed `Version 5.9.3`.

## 2. Scope correction — what is ALREADY on main at ed75dc70

Every anchor the plan and the review carry was re-located at ed75dc70 and quoted (§3). None of the app.json / package.json anchors moved: `app.json:73` is still `"android.permission.RECORD_AUDIO"`, `app.json:21` is still the `privacyManifests` block (lines 21-41), `app.json:144` is still `"runtimeVersion"`, `package.json:50` is still `react-native-gesture-handler`. Two anchors in the verifier's -07 detail DID move: `trackEvents` is at `api.ts:888-898` now (verified.json says `:814-846`); `pushTokenService.ts:77` is still exact.

| plan item | status at ed75dc70 | evidence | decision |
|---|---|---|---|
| (a) config test: no RECORD_AUDIO, both plugin entries `microphonePermission:false` | **RED ×4** | probe `w37.nativeBundle.probe.test.ts`: `android.permissions does not list RECORD_AUDIO` ×, `blockedPermissions` ×, `expo-camera opts out` ×, `expo-image-picker opts out` × | keep, plus the executed-plugin assertions (§5 a6-a8) that prove the config actually produces a mic-free Info.plist / AndroidManifest |
| (b) the three PNG SHA-256s differ from the template hashes and `splash != adaptive` | **RED (art missing)** | `sha256sum`: icon `74c64047…`, splash `5f4c0a73…`, adaptive `5f4c0a73…` (17547 B each, byte-equal); last touched by `5d22f2b7` "Day 5" and never since | keep as **skipped-with-reason**, never a red CI (brief). Ahmed supplies art. |
| (c) `ios.privacyManifests.NSPrivacyCollectedDataTypes` non-empty and equal to the committed inventory | **RED ×2** | key absent (`app.json:21-41` has only `NSPrivacyTracking` + 4 accessed-API types); `docs/privacy-data-inventory.md` does not exist (`ls` → No such file) | keep |
| (d) every runtime dep imported or allowlisted, RED on exactly `react-native-gesture-handler` | **RED on exactly one name** — but only once six other zero-import deps are justified | scan probe: 7 deps have zero `src`/`App.tsx`/`index.ts` imports; 6 of them have a config reference or a peer edge from an imported package; `react-native-gesture-handler` has **none** (0 imports, 0 installed dep/peer edges, lockfile edge = ROOT only, `package-lock.json:45`) | keep; the allowlist must carry the six justified names with their measured reason or the test is red on seven names, not one |
| -09 runtimeVersion (policy `appVersion`, version `1.0.0`) | **ALREADY GREEN as a pin; the finding's fix is NOT taken here** | probe `policy is appVersion and expo.version is the runtime phones are on` √ | **drop the policy change**: switching to `fingerprint` or bumping `expo.version` in this PR would retarget the PENDING `eas update --branch preview` at a runtime no phone has (the M18 MB-two-lever-04 trap the campaign already recorded). Keep a conscious pin (§5 e1) and the sequencing sentence in the PR body (§9). The finding's preflight script is a follow-up, not this unit. |
| "run `expo prebuild --clean` then assert the plist/manifest" | replaced | prebuild writes `ios/` + `android/` (forbidden here and unwanted in CI). The INSTALLED plugins and prebuild-config base mods execute in-process over an in-memory copy of app.json with empty `modResults` (probe `w37_plugin_exec.js`, `w37_plugin_variants.js`) — that is the same code path prebuild runs before it serialises files. The privacy manifest is asserted through the installed `IOSConfig.PrivacyInfo.mergePrivacyInfo`, the exact function `withPrivacyInfo` uses to build `PrivacyInfo.xcprivacy` (`PrivacyInfo.js:45-53` → `:93-128`). No disk writes. |

Nothing in this unit was shipped by the parallel session: `grep -rln "RECORD_AUDIO|privacyManifests|\"plugins\"" __tests__` matches only HomeScreen/Camera suites that mock `expo-camera` — no config assertion exists anywhere in `__tests__/` today (measured).

## 3. The defect — measured at ed75dc70

### 3.1 RECORD_AUDIO and the microphone purpose string (MB-TWO-LEVER-RELEASE-02)

`SmartCompareApp/app.json:71-74`:
```json
      "permissions": [
        "android.permission.CAMERA",
        "android.permission.RECORD_AUDIO"
      ]
```
`SmartCompareApp/app.json:92-103` (plugin entries carry only the purpose strings; no opt-out):
```json
      [
        "expo-camera",
        {
          "cameraPermission": "Qaren needs camera access to photograph products for comparison."
        }
      ],
      [
        "expo-image-picker",
        {
          "photosPermission": "Qaren needs photo library access to identify products from your photos."
        }
      ],
```
No audio API is used anywhere: `grep -rn -i -E "audio|microphone|gesture-handler|GestureHandler" src App.tsx index.ts` → **zero hits** (measured). `package.json` has no `expo-av`/`expo-audio`.

**Why deleting line 73 alone does nothing (the triple re-add), measured on the installed plugins:**

* `expo-camera/plugin/build/withCamera.js:7` — `const withCamera = (config, { cameraPermission, microphonePermission, recordAudioAndroid = true } = {})`; `:8-14` applies `NSMicrophoneUsageDescription: MICROPHONE_USAGE` (`:6` = `'Allow $(PRODUCT_NAME) to access your microphone'`) unless the option is `false`; `:15-19` adds `recordAudioAndroid && 'android.permission.RECORD_AUDIO'` to `android.permissions` — default `true`.
* `expo-image-picker/plugin/build/withImagePicker.js:24-36` — same default microphone string; `:34-36` `if (microphonePermission !== false) withPermissions(config, ['android.permission.RECORD_AUDIO'])`; `:39-42` `withBlockedPermissions(config, [microphonePermission === false && 'android.permission.RECORD_AUDIO', …].filter(Boolean))` — the block is emitted ONLY when the option is exactly `false`.
* `expo-camera/android/src/main/AndroidManifest.xml:3` — `<uses-permission android:name="android.permission.RECORD_AUDIO" />` is declared unconditionally in the LIBRARY manifest, so Gradle's manifest merge re-adds it to the app unless the app manifest carries `tools:node="remove"` for it.
* `@expo/config-plugins/build/ios/Permissions.js:29-36` — `applyPermissions`: `if (permissions[permission] === false) delete infoPlist[permission]; else infoPlist[permission] = permissions[permission] || infoPlist[permission] || description;` — an ABSENT option (today) writes the boilerplate default.
* `@expo/config-plugins/build/android/Permissions.js:50-61` — `withBlockedPermissions` strips the name from `config.android.permissions` and `:91-103` `ensureBlockedPermission` pushes `{ 'android:name': permission, 'tools:node': 'remove' }`; `:63-70` `withInternalBlockedPermissions` reads `config.android.blockedPermissions` (schema key confirmed at `@expo/config-types/build/ExpoConfig.d.ts:657`).

**Probe output** (`node ../.qa-w3b/probes/w37_plugin_variants.js`, installed plugins + the two prebuild-config Android base mods from `withDefaultPlugins.js:196`, empty in-memory `modResults`, both plugin orders):
```
A  CURRENT app.json (line 73 present, no opt-outs)
    iOS NSMicrophoneUsageDescription = "Allow $(PRODUCT_NAME) to access your microphone"
    Android RECORD_AUDIO             = REQUESTED | CAMERA requested | plugin-order independent: true
B  line 73 deleted only
    iOS NSMicrophoneUsageDescription = "Allow $(PRODUCT_NAME) to access your microphone"
    Android RECORD_AUDIO             = REQUESTED | CAMERA requested | plugin-order independent: true
C  + expo-camera {microphonePermission:false, recordAudioAndroid:false} ONLY
    iOS NSMicrophoneUsageDescription = undefined
    Android RECORD_AUDIO             = REQUESTED | CAMERA requested | plugin-order independent: false
D  + expo-image-picker {microphonePermission:false} ONLY
    iOS NSMicrophoneUsageDescription = "Allow $(PRODUCT_NAME) to access your microphone"
    Android RECORD_AUDIO             = BLOCKED(tools:node=remove) | CAMERA requested | plugin-order independent: false
E  + BOTH plugin opt-outs
    iOS NSMicrophoneUsageDescription = undefined
    Android RECORD_AUDIO             = BLOCKED(tools:node=remove) | CAMERA requested | plugin-order independent: true
F  + BOTH opt-outs + android.blockedPermissions:[RECORD_AUDIO]
    iOS NSMicrophoneUsageDescription = undefined
    Android RECORD_AUDIO             = BLOCKED(tools:node=remove) | CAMERA requested | plugin-order independent: true
G  android.blockedPermissions ONLY (no plugin opt-outs)
    iOS NSMicrophoneUsageDescription = "Allow $(PRODUCT_NAME) to access your microphone"
    Android RECORD_AUDIO             = BLOCKED(tools:node=remove) | CAMERA requested | plugin-order independent: true
H  camera {microphonePermission:false} but recordAudioAndroid left default
    iOS NSMicrophoneUsageDescription = undefined
    Android RECORD_AUDIO             = BLOCKED(tools:node=remove) | CAMERA requested | plugin-order independent: true
```
Reading: today (A) both platforms request the microphone. The naive edit (B) changes nothing. Each plugin alone (C, D) fixes one platform and is plugin-ORDER-DEPENDENT. Only BOTH opt-outs (E) are clean on both platforms and order-independent; `android.blockedPermissions` (F) adds a second, plugin-independent guard on Android; `recordAudioAndroid:false` is redundant once image-picker blocks (H) but is kept so the camera entry is self-describing if image-picker is ever removed.

### 3.2 Privacy manifest declares nothing about collection (MB-TWO-LEVER-RELEASE-08)

`app.json:21-41` — `privacyManifests` = `NSPrivacyTracking: false` + four `NSPrivacyAccessedAPITypes` (`CA92.1`, `C617.1`, `35F9.1`, `E174.1`). No `NSPrivacyCollectedDataTypes`, no `NSPrivacyTrackingDomains`. `mergePrivacyInfo({}, expo.ios.privacyManifests)` on the installed `@expo/config-plugins` therefore returns `NSPrivacyCollectedDataTypes: []` (`PrivacyInfo.js:96` defaults it to `[]`, `:112-119` merges only what app.json supplies). Meanwhile the client transmits, measured with file:line in §4.2: email, a display name, photos, typed product text, a hashed device identifier, an Expo push token, product-interaction events, self-declared demographics, preferences, and Sentry crash/performance data.

### 3.3 Template launcher art (MB-SAFE-HYGIENE-01)

```
74c64047eb557b1341bba7a2831eedde9ddb705e6451a9ad9f5552bf558f13de  icon.png          22380 bytes
5f4c0a732b6325bf4071d9124d2ae67e037cb24fcc9c482ef82bea742109a3b8  splash-icon.png   17547 bytes
5f4c0a732b6325bf4071d9124d2ae67e037cb24fcc9c482ef82bea742109a3b8  adaptive-icon.png 17547 bytes
```
`git log --oneline -- assets/icon.png assets/splash-icon.png assets/adaptive-icon.png` → one commit, `5d22f2b7 Day 5: Mobile app working…`. The template-identity claim is the repo's own record (`docs/plans/bundle-d-followups.md:100-114`, CLAUDE.md:13, re-confirmed by the verifier at 76ace90); **no Expo template PNG exists in node_modules to re-derive it here** (`find node_modules/expo node_modules/@expo -name icon.png` → nothing). What IS self-contained evidence: `splash-icon.png` and `adaptive-icon.png` are byte-identical, which no custom render would produce.

### 3.4 `react-native-gesture-handler` (MB-SAFE-HYGIENE-06)

`package.json:50` — `"react-native-gesture-handler": "~2.28.0"`. Scan probe (`w37_dep_usage_scan.js`, 43 deps, 454 source files): zero imports in `src/`, `App.tsx`, `index.ts`, `__tests__/`, `__mocks__/`, config files, `app.json`, `eas.json`; and after reading every `node_modules/*/package.json` (and `@scope/*`), **no installed package declares it** in `dependencies`/`peerDependencies`/`optionalDependencies`. `package-lock.json` mentions it at `:45` (ROOT dependencies) and `:12562` (its own entry) only. `App.tsx` uses `@react-navigation/native-stack` + `bottom-tabs` (scan: 14 + 1 src importers) whose peers are `react-native-screens` and `react-native-safe-area-context` — NOT gesture-handler.

### 3.5 runtimeVersion (MB-TWO-LEVER-RELEASE-09)

`app.json:5` `"version": "1.0.0"`, `:144-146` `"runtimeVersion": { "policy": "appVersion" }`, `eas.json:4` `"appVersionSource": "remote"`, `:19` `"autoIncrement": true` (production profile). Phones on `preview` run runtime `1.0.0`. This is the pin the unit keeps (see §2).

## 4. The fix — MINIMAL design

### 4.1 Files to touch

1. **`SmartCompareApp/app.json`** — five edits, nothing else:
   * `android.permissions` (`:71-74`) → `["android.permission.CAMERA"]` (delete `:73`).
   * add `android.blockedPermissions: ["android.permission.RECORD_AUDIO"]` (schema key `@expo/config-types` `ExpoConfig.d.ts:657`; consumed by `withInternalBlockedPermissions`, registered as an Android base mod at `@expo/prebuild-config/build/plugins/withDefaultPlugins.js:196`).
   * `expo-camera` entry (`:92-97`) → `{ "cameraPermission": "<unchanged>", "microphonePermission": false, "recordAudioAndroid": false }` — option names from the INSTALLED `withCamera.d.ts` (`cameraPermission?: string | false; microphonePermission?: string | false; recordAudioAndroid?: boolean`).
   * `expo-image-picker` entry (`:98-103`) → `{ "photosPermission": "<unchanged>", "microphonePermission": false }` — from the installed `withImagePicker.d.ts` (`photosPermission?: string | false; cameraPermission?: string | false; microphonePermission?: string | false`). Do NOT set `cameraPermission: false` here: image-picker's `:41` would then BLOCK `android.permission.CAMERA`, which the app needs.
   * `ios.privacyManifests` → add `NSPrivacyCollectedDataTypes` (the array in §4.2, each entry with exactly the four keys the installed type declares at `ExpoConfig.d.ts:482-487`: `NSPrivacyCollectedDataType`, `NSPrivacyCollectedDataTypeLinked`, `NSPrivacyCollectedDataTypeTracking`, `NSPrivacyCollectedDataTypePurposes`). Keep `NSPrivacyTracking: false` and the four accessed-API entries byte-identical.
   * **Unchanged:** `version`, `runtimeVersion`, `updates.url`, `extra.eas.projectId`, plugin ORDER, every other key.
2. **`docs/privacy-data-inventory.md`** (new, repo root `docs/`) — the engineering-owned enumeration (§4.2) as (i) a human table with `file:line` per row and (ii) ONE fenced ```` ```json ```` block that is the literal `NSPrivacyCollectedDataTypes` array. The test parses the first ```` ```json ```` fence and deep-equals it to app.json's array (both sorted by `NSPrivacyCollectedDataType`), so the doc and the manifest cannot drift.
3. **`SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts`** (new; `__tests__/config/` already exists with `featureBucket.test.ts` / `features.test.ts`; jest `testMatch` `**/__tests__/**/*.test.ts` picks it up with no flag; `tsc --noEmit` covers `__tests__` — 290 test files in `--listFilesOnly`). Reads `app.json`, `package.json`, the docs file and the three PNGs with `fs` only; executes the installed plugins in-process. No client module is imported, so no `moduleNameMapper` shim is involved. Optional helper `__tests__/helpers/w37NativeConfig.ts` for the plugin-execution function if it keeps the test readable (pattern: `helpers/w312BootSandbox.ts`).

### 4.2 The inventory — enumerated from code at ed75dc70

Purpose identifiers are Apple's (`NSPrivacyCollectedDataTypePurposeAppFunctionality`, `…Analytics`, `…ProductPersonalization`, `…DeveloperAdvertising`, `…ThirdPartyAdvertising`, `…Other`). **Honesty note:** the data-type and purpose identifier STRINGS cannot be verified on an installed package here — every `PrivacyInfo.xcprivacy` shipped in node_modules (expo-application, expo-constants, expo-device, expo-file-system, expo-localization, expo-notifications, react-native ×5) carries an EMPTY `NSPrivacyCollectedDataTypes` array (grep for `NSPrivacyCollectedDataType[A-Za-z]+` matched only the plural key, 14×), and `mergePrivacyInfo` passes strings through unvalidated (`PrivacyInfo.js:112-119`). The reviewer checks spelling against Apple's "Describing data use in privacy manifests" page before merge; a misspelling would surface only at App Store Connect upload. Recorded as an open question (§8).

| # | `NSPrivacyCollectedDataType…` | evidence (file:line at ed75dc70) | Linked | Tracking | Purposes |
|---|---|---|---|---|---|
| 1 | `EmailAddress` | `authService.ts:121-150` register body `{ email, password, … }` → `POST /api/v1/auth/register`; `:193-196` login; `:624-626` password reset; social `id_token` (`:718` google, `:868-872` apple) carries the email claim | true | false | AppFunctionality |
| 2 | `Name` | `api.ts:432` `PUT /api/v1/auth/profile { display_name }`; `RegisterOptions.name` exists (`authService.ts:107-111`) but `RegisterScreen.tsx:222` does not pass it; Google `id_token` claims carry a name (backend-derived) | true | false | AppFunctionality |
| 3 | `PhotosorVideos` | `api.ts:245-262` JPEG `FormData('images')` → `:285` `POST /api/v1/image/identify` (policy §2.2: processed, not stored) | true | false | AppFunctionality |
| 4 | `OtherUserContent` | typed product text `api.ts:856-862` `product_a/product_b` → `/api/v1/text/compare`; free text `change_suggestion` `api.ts:875-882` → `/api/v1/feedback`; `ContactUsScreen.tsx:88-95` composes subject+message into the same field | true | false | AppFunctionality, Analytics |
| 5 | `SearchHistory` | comparison queries are persisted server-side and read back `api.ts:366` `GET /api/v1/comparisons/history`, `:402` `GET /api/v1/comparisons/{id}` (policy §2.2 names "search history") | true | false | AppFunctionality |
| 6 | `UserID` | account id saved from `response.data.user` (`authService.ts:151-152` `saveUser`); `comparison_id`-keyed feedback/events `api.ts:877`, `:891` | true | false | AppFunctionality, Analytics |
| 7 | `DeviceID` | `deviceFingerprint.ts:27-35` SHA-256(`applicationId|osBuildId|random nonce`) → `X-Device-Fingerprint` header `authService.ts:148`, `ShareBottomSheet.tsx:159` `device_fingerprint_hash`; Expo push token `pushTokenService.ts:77` → `:90` `PUT /api/v1/auth/push-token { expo_push_token }` | true | false | AppFunctionality (Apple's App Functionality definition includes fraud prevention) |
| 8 | `ProductInteraction` | `api.ts:888-898` `trackEvents([{ event_type, event_data, comparison_id }])` → `POST /api/v1/events`; callers e.g. `HomeScreen.tsx:250, 324, 331, 338, 380, 498` | true | false | Analytics |
| 9 | `CrashData` | `sentry.ts:235-243` `Sentry.init({ dsn, sendDefaultPii: false, tracesSampleRate: 0.1, beforeSend, beforeBreadcrumb, beforeSendTransaction })`; `FALLBACK_DSN` is always set (W3-12 ruling), so every build reports | true (conservative — no `Sentry.setUser` anywhere in `src` (grep), but the SDK attaches a per-install device id) | false | AppFunctionality |
| 10 | `PerformanceData` | `sentry.ts:238` `tracesSampleRate: 0.1`; `src/lib/performance/wallTimeInstrumentation.ts` (scan: `@sentry/react-native` importer) | true (same) | false | AppFunctionality, Analytics |
| 11 | `OtherDiagnosticData` | Sentry breadcrumbs/device context, scrubbed at `sentry.ts:243-245`; `authService.ts:692/752/777/789` `captureMessage` extras (token shape, error codes — no identity) | true (same) | false | AppFunctionality |
| 12 | `OtherDataTypes` | demographics `api.ts:996-1002` `{ age_group, gender, governorate, language, country }` → `:1044` `PUT /api/v1/auth/demographics`; preferences `types.ts:546-556` `{ priorities, budget, lifestyle, brand_attitude, ai_sharing_enabled, notifications_* }` → `api.ts:478` `PUT /api/v1/auth/preferences` | true | false | ProductPersonalization, AppFunctionality |

Not collected (state it in the doc so the label is complete): precise/coarse location (region is a hard-coded `'bahrain'` string at `api.ts:240`, `:862`; no location API imported), audio (this unit removes the permission), contacts, payment info, advertising data (no ad SDK; `NSPrivacyTracking: false`), phone number. The Play install referrer (`playInstallReferrerService.ts:24-36`) is read on device and only feeds `setDeferredInviteCode` (`App.tsx:178-182`) — the invite code, not the referrer string, reaches the backend (`authService.ts:146`).

Every `NSPrivacyCollectedDataTypeTracking` is `false`, consistent with `NSPrivacyTracking: false` at `app.json:22` — the test pins that consistency.

### 4.3 What the unit does NOT do

* Does not touch `package.json` or `package-lock.json`. Removing `react-native-gesture-handler` is `npm uninstall` + a lockfile commit = a human toolchain step (Ahmed). The code half lands a pending-removal allowlist that goes RED the moment the package is gone until the entry is deleted (§5 d2), so the allowlist cannot go stale.
* Does not touch `assets/*.png`. Icon tests are skipped-with-reason until art lands (§5 b).
* Does not change `version`, `runtimeVersion`, or the plugin order (§2, -09 row).
* Does not run `expo prebuild`. Does not add a CI job (branch protection unchanged; the new test file runs inside the existing required `frontend-tests` job, `.github/workflows/ci.yml:262-263` `npx jest --ci`).
* Backward compatibility: no runtime code changes; phones on 97b5f15 and on the pending OTA are unaffected. The next NATIVE build carries the changes.

## 5. Red tests — `SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts`

All `fs`-only unless stated. `APP = path.resolve(__dirname, '../..')`, `REPO = path.resolve(APP, '..')`. Plugin execution helper `compile(expo, order)` = the body of `w37_plugin_variants.js::compile` (installed `expo-camera/app.plugin.js`, `expo-image-picker/app.plugin.js` — resolved through `require.resolve(…, { paths: [APP] })` — then `AndroidConfig.Permissions.withInternalBlockedPermissions` + `withPermissions` from `'expo/config-plugins'` (resolvable: `require.resolve('expo/config-plugins')` → `node_modules/expo/config-plugins.js`), then `config.mods.ios.infoPlist` / `config.mods.android.manifest` with `introspect: true` and empty `modResults`). Measured runtime under jest: 200-320 ms per compile.

| id | assertion | why RED today (measured) | mutation that must redden it after the fix |
|---|---|---|---|
| a1 | `expo.android.permissions` does not contain `android.permission.RECORD_AUDIO` | probe × — `app.json:73` | re-add the string |
| a2 | `expo.android.blockedPermissions` contains `android.permission.RECORD_AUDIO` | probe × — key absent | delete the key |
| a3 | expo-camera entry options: `microphonePermission === false` AND `recordAudioAndroid === false` | probe × — entry has only `cameraPermission` | drop either option |
| a4 | expo-image-picker entry: `microphonePermission === false` | probe × — entry has only `photosPermission` | drop it |
| a6 | executed plugins: `Info.plist` has NO `NSMicrophoneUsageDescription`; `NSCameraUsageDescription === 'Qaren needs camera access to photograph products for comparison.'`; `NSPhotoLibraryUsageDescription` unchanged | probe × — `"Allow $(PRODUCT_NAME) to access your microphone"` | set only ONE plugin's `microphonePermission:false` (variant D leaves the string) |
| a7 | executed plugins: `uses-permission` carries `RECORD_AUDIO` ONLY as `{ 'android:name': …, 'tools:node': 'remove' }` and `CAMERA` as a plain request | probe × — plain `{"android:name":"android.permission.RECORD_AUDIO"}` | variant C (camera-only opt-out) leaves it REQUESTED |
| a8 | order pin: `compile(expo, [camera, picker])` deep-equals `compile(expo, [picker, camera])` on `{mic, usesPermission}` | GREEN today (A is order-independent) — kept because it is the assertion that fails on the half-fixes: variants C and D are order-DEPENDENT | remove either plugin's opt-out |
| c1 | `expo.ios.privacyManifests.NSPrivacyCollectedDataTypes` is an array with `length > 0` | probe × — `undefined` | delete the key |
| c2 | every entry has exactly the four keys, `NSPrivacyCollectedDataType` matches `/^NSPrivacyCollectedDataType[A-Z][A-Za-z]+$/`, `Linked`/`Tracking` booleans, `Purposes` a non-empty array of `/^NSPrivacyCollectedDataTypePurpose[A-Z][A-Za-z]+$/`; `Tracking === false` for all while `NSPrivacyTracking === false`; type ids unique | RED — no entries | set any `Tracking: true`, or duplicate a type |
| c3 | `docs/privacy-data-inventory.md` exists; its first ```` ```json ```` fence parses to an array that deep-equals app.json's (both sorted by type) | probe × — file missing | change a purpose in one place only |
| c4 | `IOSConfig.PrivacyInfo.mergePrivacyInfo({}, expo.ios.privacyManifests)` (installed `expo/config-plugins`) returns `NSPrivacyCollectedDataTypes` whose type set equals c3's set, `NSPrivacyTracking === false`, and the four `NSPrivacyAccessedAPITypes` unchanged (deep-equal to the committed list) | RED — merge returns `[]` (`PrivacyInfo.js:96`) | delete the key; or alter an accessed-API reason |
| d1 | for every key of `package.json.dependencies`: imported (regex over `src/**/*.{ts,tsx}`, `App.tsx`, `index.ts`: `from '<dep>'`/`from '<dep>/…'`/`require('<dep>…')`/`import('<dep>…')`/`import '<dep>…'`), OR in `JUSTIFIED` with a config reference (`babel-preset-expo` → `babel.config.js:206`; `expo-build-properties` → `app.json:118`; `expo-dev-client` → `eas.json:8` `developmentClient: true`), OR declared in `dependencies`/`peerDependencies` of an IMPORTED dependency's installed `package.json` (measured edges: `react-native-safe-area-context` ← `@react-navigation/native-stack`, `bottom-tabs`; `react-native-screens` ← same two; `react-native-worklets` ← `react-native-reanimated`), OR a key of `PENDING_REMOVAL`. Assert the set of otherwise-unjustified names **equals** `Object.keys(PENDING_REMOVAL)` (`['react-native-gesture-handler']`) | RED with an empty `PENDING_REMOVAL`: the scan probe shows exactly one unjustified name. (After the unit the entry makes it green; that IS the code half.) | delete the `PENDING_REMOVAL` entry; or break the peer-edge lookup (`react-native-screens` then surfaces) |
| d2 | every `PENDING_REMOVAL` key is still in `package.json.dependencies` | GREEN today; goes RED the moment Ahmed uninstalls, until the entry is deleted — the stale-allowlist guard | (that event) |
| d3 | `it.todo('AHMED: npm uninstall react-native-gesture-handler, commit package-lock.json, delete the PENDING_REMOVAL entry, then eas build')` | todo (jest reports it, never fails) | — |
| d4 | pending-removal names must stay unused: zero imports in `src`/`App.tsx`/`index.ts` and no installed dependency of the app declares them | GREEN today (measured) — a future `import 'react-native-gesture-handler'` would make the removal reason false | add an import |
| b1 | `it.skip` (guarded by `const ICON_ART_SUPPLIED = false`): `sha256(icon.png) !== '74c64047…'` | skipped-with-reason: "AHMED: supply art — CLAUDE.md blocker #1 / bundle-d-followups ICN-0001"; RED if un-skipped today (hash equal) | (art) |
| b2 | `it.skip` (same guard): `sha256(splash) !== '5f4c0a73…'`, `sha256(adaptive) !== '5f4c0a73…'`, `sha256(splash) !== sha256(adaptive)` | skipped; RED ×3 if un-skipped today | (art) |
| b3 | `it.todo('flip ICON_ART_SUPPLIED once assets/ are re-rendered')` + always-on pin: the three files exist, start with the PNG signature `89 50 4E 47`, and `app.json:7/:11/:49` point at them | GREEN — guards a broken path, never the art | rename a file |
| e1 | `expo.runtimeVersion` deep-equals `{ policy: 'appVersion' }` and `expo.version === '1.0.0'` — docstring: "conscious pin: flipping either retargets `eas update`; Ahmed changes both the pin and app.json in the release commit AFTER the last OTA to the 1.0.0 fleet" | GREEN today (probe √) | bump either |

Measured probe tally at ed75dc70 (`node node_modules/jest/bin/jest.js --ci --verbose --roots ../.qa-w3b/probes/__tests__`): `Tests: 8 failed, 2 skipped, 1 todo, 6 passed, 17 total` — the 8 failures are a1-a4, a6, a7, c1, c3 exactly.

## 6. Preserve — with the pin that proves each

| behaviour | pin |
|---|---|
| camera purpose string, photos purpose string, `android.permission.CAMERA` requested | a5 (static, GREEN today) + a6/a7 assert them in the executed output |
| `NSPrivacyTracking: false` and the four `NSPrivacyAccessedAPITypes` (`CA92.1`, `C617.1`, `35F9.1`, `E174.1`) | c4 deep-equals the accessed-API list to the committed four |
| plugin ORDER and the other plugin entries (`expo-font`, `expo-secure-store`, `expo-localization`, google-signin, `expo-apple-authentication`, `expo-notifications`, `expo-build-properties`, `@sentry/react-native`) | new pin: `expo.plugins.map(p => Array.isArray(p) ? p[0] : p)` deep-equals the 10-name list in app.json order |
| `version 1.0.0`, `runtimeVersion appVersion`, `updates.url`, `extra.eas.projectId 387a4fcb-…` | e1 + one pin on `updates.url` and `extra.eas.projectId` |
| the three PNGs are byte-identical to today (no accidental re-encode by an editor) — until Ahmed's art commit | `git diff --stat -- SmartCompareApp/assets` empty in the PR; b3 keeps the paths valid |
| `package.json` and `package-lock.json` untouched | `git diff --stat` empty for both; d2 |
| existing suites that read `package.json` | `__tests__/i18n/plurals.test.ts` (`:125-128` `require('../../package.json')`) — measured GREEN at base (3 suites, 29 tests with `__tests__/config/*`) |

## 7. Gates

1. **Red-first**: a1-a4, a6, a7, c1-c4 must fail for the stated reasons before app.json/docs are edited (d1 with `PENDING_REMOVAL = {}` fails on exactly one name).
2. **Unit files**: `node node_modules/jest/bin/jest.js --ci __tests__/config/nativeBundle.w37.test.ts` (plus the helper if created). Run it twice: once alone, once with `--detectOpenHandles` (§8 flag on the worker warning).
3. **Neighbour suites** (modules touched: `app.json`, `package.json` readers, `expo-camera`/`expo-image-picker` consumers — none of the SRC is touched, but these are the suites that would notice a config or mock drift): `__tests__/config/featureBucket.test.ts`, `__tests__/config/features.test.ts`, `__tests__/i18n/plurals.test.ts`, `__tests__/versionCompare.a9.test.ts`, `__tests__/HomeScreen.scanCamera.test.tsx`, `__tests__/CameraHelpOverlay.test.tsx`. Baseline measured GREEN for the first three (29 tests).
4. **tsc**: `node node_modules/typescript/bin/tsc --noEmit` (covers `__tests__`; the test's `any`-typed config object must not leak `implicit any` under `strict: true` — type the plugin functions as `ConfigPlugin<…>` from `'expo/config-plugins'` or annotate locally).
5. **eslint on the new files by path**: `node node_modules/eslint/bin/eslint.js __tests__/config/nativeBundle.w37.test.ts` (CI lints only `src/**`, so this is the only time the file is linted; `console.log` is not needed in the final test — the probe's MEASURE cases are dropped).
6. **Full jest suite once in the green phase** (baseline 2,729 passed / 0 failed / 278 suites at ece0fbbe).
7. **Backend halves: none** — no pytest, ruff, or comm gate applies; say so in the PR.
8. **Byte-identity**: `git diff --stat` must list exactly `SmartCompareApp/app.json`, `docs/privacy-data-inventory.md`, the new test file (and the optional helper). Nothing else.
9. Fable review before commit. Agents never commit.

## 8. What this unit CANNOT do / Ahmed dependencies / device-or-store-only verification

**Ahmed dependencies (the code half lands without every one of them):**
1. **Launcher art** — regenerate `assets/{icon,splash-icon,adaptive-icon}.png` as bytes-different renders of the approved concentric-circles visual (bundle-d-followups approach 1 or 2); then flip `ICON_ART_SUPPLIED` to `true` (b1/b2 become live and must pass: three distinct hashes, none equal to the recorded template hashes).
2. **`npm uninstall react-native-gesture-handler`** + commit `package-lock.json`, then delete the `PENDING_REMOVAL` entry (d2 forces this). Changes autolinking → part of the same native build.
3. **`eas build --profile production`** (Apple Developer gate upstream). The build's `expo.version` bump (→ new runtime) must be a separate one-line commit made AFTER the last `eas update --branch preview` to the 1.0.0 fleet; e1 is the tripwire.
4. **App Store Connect nutrition labels** filled from `docs/privacy-data-inventory.md` (not from the policy text), and the legal redraft (-07, CLAUDE.md blocker #2) folding the same rows into `app/legal/privacy_policy.md` §2 (today it names email, display name, preferences, feedback, usage, device type, camera — and omits the fingerprint hash, push token and demographics).
5. **Identifier spelling review** against Apple's privacy-manifest documentation (§4.2 honesty note) — the only check that catches a typo before upload.

**Device / store only:**
* iOS Settings → Qaren shows Camera and Photos but no Microphone row; Android app info → Permissions lists no Microphone; the Play Console "App permissions" declaration no longer lists `RECORD_AUDIO`.
* A one-off rehearsal in a scratch clone (NOT this worktree, not CI): `npx expo prebuild --clean --no-install`, then confirm `ios/Qaren/Info.plist` has no `NSMicrophoneUsageDescription`, `android/app/src/main/AndroidManifest.xml` carries `RECORD_AUDIO` only with `tools:node="remove"`, and `ios/Qaren/PrivacyInfo.xcprivacy` carries the 12 collected-data entries. The in-process test is the same code path, but the Gradle manifest MERGE (which is what finally drops expo-camera's library declaration at `AndroidManifest.xml:3`) only runs in a real build — the `tools:node="remove"` semantics are asserted from `@expo/config-plugins`' emitted attribute, not from Gradle.
* Apple's privacy report / ICN-0001 verdicts happen only at submission.

**Flags:**
* Intermittent jest warning `A worker process has failed to exit gracefully and has been force exited` seen in 1 of 2 runs when BOTH probe files ran under workers; never when the plugin-exec probe ran alone (2/2 clean), never under `--detectOpenHandles` (no handle reported), never `--runInBand`. Root cause not identified (loading `expo/config-plugins` in a worker is the only unusual thing these tests do). It is a warning, not a failure; the green phase must run the unit file with `--detectOpenHandles` and the full suite once and record whether it recurs.
* `-09`: the finding's fix (fingerprint policy or a preflight script) is deliberately NOT taken; only the pin. Say so in the PR so nobody re-files it as "missed".
* `expo-dev-client` is justified only by `eas.json:8` — if the development profile is ever dropped, the allowlist reason becomes false; the JUSTIFIED map carries the line reference so a reviewer can re-check.

## 9. PR-body facts

* Base ed75dc70. Files: `SmartCompareApp/app.json` (5 edits), `docs/privacy-data-inventory.md` (new), `SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts` (new). No `src/`, no `package.json`/lockfile, no `assets/`, no backend. No flag. **needs-build**: nothing here reaches phones by OTA; it ships with the next `eas build`.
* RECORD_AUDIO: at ed75dc70 the installed expo-camera 17.0.10 and expo-image-picker 17.0.11 plugins re-add `RECORD_AUDIO` and write `"Allow $(PRODUCT_NAME) to access your microphone"` even with `app.json:73` deleted (variant B). Both plugin opt-outs together are necessary and sufficient (variant E); each alone fixes one platform and is plugin-order-dependent (C, D); `android.blockedPermissions` is the belt-and-braces second guard on Android (F). Zero audio/microphone references in `src`, `App.tsx`, `index.ts`.
* Privacy manifest: `NSPrivacyCollectedDataTypes` goes from absent to 12 entries, all `Tracking:false` (consistent with `NSPrivacyTracking:false`), each enumerated from code with file:line in `docs/privacy-data-inventory.md`; the test deep-equals doc and manifest and asserts the merged output of the installed `mergePrivacyInfo` (the function prebuild uses to write `PrivacyInfo.xcprivacy`). Identifier strings not machine-verifiable here — reviewed against Apple's docs by <name>.
* Icons: unchanged; hashes `74c64047…` / `5f4c0a73…` / `5f4c0a73…` (splash == adaptive, 17547 B, single commit `5d22f2b7`). Tests skipped with the reason string; flip `ICON_ART_SUPPLIED` when art lands. Still CLAUDE.md App-Store blocker #1.
* `react-native-gesture-handler` 2.28.0: 0 imports, 0 installed dep/peer edges, lockfile edge ROOT-only. On the pending-removal allowlist; removal = `npm uninstall` + lockfile commit (Ahmed) and the allowlist test goes red until the entry is deleted. 6 other zero-import deps are justified by config reference or peer edge (listed in the test).
* runtimeVersion: policy `appVersion`, version `1.0.0` — pinned, NOT changed; changing either before the pending `eas update --branch preview` would retarget it at a runtime no phone has. The production build's version bump is Ahmed's release commit after the last 1.0.0 OTA.
* Gates run: unit file (N tests, M skipped, K todo), neighbour suites (6 files), `tsc --noEmit` 5.9.3 clean, eslint on the new file, full jest suite (numbers), `git diff --stat` = 3 files. Worker-exit warning: recurred / did not recur.
* Not verifiable in CI: Gradle manifest merge, iOS Settings permission rows, ASC privacy report, ICN-0001 — device/store checklist in §8.

## 10. Measurements run (command → observed output)

All from `C:/Users/SynAckITPC/Documents/AI/sc-w3-native/SmartCompareApp` unless noted; 2026-09-11.

1. `git rev-parse HEAD` → `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`; `git status --short` → empty (start and end).
2. `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3`. Installed versions via `node -p "require('<pkg>/package.json').version"`: expo 54.0.34, expo-camera 17.0.10, expo-image-picker 17.0.11, @expo/config-plugins 54.0.4, @expo/prebuild-config 54.0.8, @expo/config 12.0.13, @expo/config-types 54.0.10, @expo/plist 0.4.8, react-native-gesture-handler 2.28.0, react-native-screens 4.16.0, @react-navigation/native 7.2.4, native-stack 7.15.0, bottom-tabs 7.16.0, react-native-reanimated 4.1.7, jest 29.7.0, ts-jest 29.4.9, typescript 5.9.3, eslint 9.39.4, expo-updates 29.0.17.
3. `sha256sum assets/{icon,splash-icon,adaptive-icon,favicon}.png` + sizes → `74c64047…` 22380 B / `5f4c0a73…` 17547 B / `5f4c0a73…` 17547 B / favicon `24272cda…` 1466 B. `git log --oneline -- assets/icon.png assets/splash-icon.png assets/adaptive-icon.png` → `5d22f2b7` only.
4. `find node_modules/expo node_modules/@expo node_modules/create-expo-app -name icon.png …` → nothing (no template to re-derive the hash from).
5. `grep -rn -i -E "audio|microphone|gesture-handler|GestureHandler" src App.tsx index.ts` → no output.
6. `cat node_modules/expo-camera/plugin/build/withCamera.js` (22 lines, quoted §3.1), `withCamera.d.ts`, `expo-image-picker/plugin/build/withImagePicker.js` (47 lines), `withImagePicker.d.ts`, `expo-camera/android/src/main/AndroidManifest.xml` (RECORD_AUDIO at :3), `expo-image-picker/android/src/main/AndroidManifest.xml` (no RECORD_AUDIO), `@expo/config-plugins/build/android/Permissions.js` (:33-70, :91-103), `ios/Permissions.js` (:24-39), `ios/PrivacyInfo.js` (:45-53, :93-128), `plugins/withMod.js`, `@expo/prebuild-config/build/plugins/withDefaultPlugins.js:196` (Android base-mod list incl. `withInternalBlockedPermissions`, `withPermissions`) and `:169` (`withPrivacyInfo` in the iOS list), `@expo/config-types/build/ExpoConfig.d.ts:457-487` (privacyManifests type), `:654-657` (blockedPermissions).
7. `node ../.qa-w3b/probes/w37_plugin_exec.js` → CURRENT: mic string present, `RECORD_AUDIO` requested; PROPOSED: mic `undefined`, `RECORD_AUDIO` `tools:node:"remove"`; VARIANT opt-outs-only: same as proposed; VARIANT naive: same as current.
8. `node ../.qa-w3b/probes/w37_plugin_variants.js` → the A-H table quoted verbatim in §3.1.
9. `node ../.qa-w3b/probes/w37_dep_usage_scan.js` → `dependencies: 43 | scanned source files: 454`; zero-src-import candidates: `babel-preset-expo` (config, expo:dependencies), `expo-build-properties` (app.json), `expo-dev-client` (NONE — justified by eas.json:8), `react-native-gesture-handler` (NONE), `react-native-safe-area-context` (peer of bottom-tabs/elements/native-stack), `react-native-screens` (peer of bottom-tabs/native-stack), `react-native-worklets` (peer of reanimated); every other dep has ≥1 src importer.
10. `grep -n "react-native-gesture-handler" package-lock.json` → `:45` (root deps) and `:12562/:12564` (own entry) only. `node -p "JSON.stringify(require('expo-dev-client/package.json').peerDependencies)"` → `{"expo":"*"}`; `grep -n dev-client node_modules/expo/package.json` → nothing.
11. `node node_modules/jest/bin/jest.js --ci --verbose --roots ../.qa-w3b/probes/__tests__` → `Tests: 8 failed, 2 skipped, 1 todo, 6 passed, 17 total` (per-test glyphs in §5). The probe lives outside jest's `rootDir` so it is passed as an extra root; the default `testMatch` then picks it up; the real unit file needs no flag.
12. Same with `--detectOpenHandles --testPathPattern pluginExec` → `Tests: 2 failed, 2 passed, 4 total`, no handle reported; `--runInBand` → same, no warning; default workers, pluginExec alone ×2 → no warning; both probes under workers ×2 → the force-exit warning once.
13. `node node_modules/jest/bin/jest.js --ci __tests__/i18n/plurals.test.ts __tests__/config` → `Test Suites: 3 passed`, `Tests: 29 passed`.
14. `node node_modules/typescript/bin/tsc --noEmit --listFilesOnly | grep -c __tests__` → 290. `node -p "require.resolve('expo/config-plugins')"` → `…/node_modules/expo/config-plugins.js` (the junction resolves into the shared install).
15. `grep -rln -E "expo-camera|\"plugins\"|RECORD_AUDIO|privacyManifests" __tests__` → only HomeScreen/CameraHelpOverlay suites (mocks of expo-camera); `grep -rln -E "assets/(icon|splash|adaptive)" __tests__` → nothing; `grep -rl -E "app\.json|package\.json" __tests__` → `AuthScreens.socialDiagnostic.pa8` (string), `i18n/plurals` (`require('../../package.json')`), `versionCompare.a9` (comment).
16. Collection sites quoted in §4.2 came from `sed -n`/`grep -n` over `src/services/{authService,api,deviceFingerprint,pushTokenService,sentry,referralService,playInstallReferrerService}.ts`, `src/components/ShareBottomSheet.tsx:159`, `src/screens/{RegisterScreen,ContactUsScreen,HomeScreen}.tsx`, `src/types/types.ts:546-556`, `App.tsx:176-182`; `grep -rn setUser src` → only React `useState` setters (no `Sentry.setUser`).
17. `grep -rho "NSPrivacyCollectedDataType[A-Za-z]+" node_modules/@sentry node_modules/expo-* node_modules/expo node_modules/react-native …` → `14 NSPrivacyCollectedDataTypes` only; `find … -name PrivacyInfo.xcprivacy` → 11 files, sample `expo-notifications/ios/PrivacyInfo.xcprivacy` has an empty `NSPrivacyCollectedDataTypes` array.
18. Docs re-read at ed75dc70: `docs/investigations/2026-09-06-full-review-tables.md:67,72,426,441,442`; `…-full-review.md` W3 table (W3-7 rows); `…-full-review-verified.json` entries for -02/-07/-08/-09/HYGIENE-01/-06; `docs/plans/bundle-d-followups.md:100-170`; `CLAUDE.md:8-18`; `app/legal/privacy_policy.md:14-31`; `.github/workflows/ci.yml:248-275`; `.gitignore:72` (`.qa-*/` — this spec and the probes are untracked).

Probe files (gitignored, `.qa-w3b/probes/`): `w37_plugin_exec.js`, `w37_plugin_variants.js`, `w37_dep_usage_scan.js`, `__tests__/w37.nativeBundle.probe.test.ts`, `__tests__/w37.pluginExec.probe.test.ts`.

## FABLE REVIEW RULINGS (binding, 2026-09-11)

Verdict: **APPROVED_WITH_RULINGS**. Every file:line anchor, every plugin option name, every probe output and every hash in §1-§10 was independently re-measured and reproduced exactly. The spec's substance stands. The rulings below correct six things the spec gets wrong or leaves unexecutable, and add one mandatory assertion. Rulings are binding and override the body of the spec where they conflict.

New review probes (gitignored, `.qa-w3b/probes/`, written fresh this session — they do not reuse the writer's): `w37_fable_mutations.js`, `__tests__/w37.fable.leak.probe.test.ts`, `__tests__/w37.fable.heavy{A,B}.probe.test.ts`, `__tests__/w37.fable.trivial{A,B}.probe.test.ts`.

### R1 — Base commit is b63a8368, not ed75dc70. Every anchor still holds verbatim.

`git rev-parse HEAD` → `b63a8368b7910a946020438a5447bbcd6b792805` (= `origin/main`, branch `feature/s65-w3-7-native-bundle`). `ed75dc70` is an ancestor. `git diff --stat ed75dc70 b63a8368` → 13 files, **backend only** (`Procfile`, `app/api/text_routes.py`, `app/main.py`, `app/middleware/rate_limiter.py`, `app/services/{feedback_service,price_service}.py`, `app/utils/async_utils.py`, `railway.json`, 5 `tests/*`). `git diff --stat ed75dc70 b63a8368 -- SmartCompareApp/` → **empty**; same for `-- docs/`.

Binding: the red phase works at `b63a8368` and may trust every anchor, hash and quote in §1-§10 unchanged. Replace the SHA label only. Re-verified at b63a8368: `app.json:5` `"version": "1.0.0"`, `:73` `"android.permission.RECORD_AUDIO"`, `:92-97` expo-camera with only `cameraPermission`, `:98-103` expo-image-picker with only `photosPermission`, `:118` expo-build-properties, `:144-146` `runtimeVersion {policy:"appVersion"}`, no `blockedPermissions`, no `NSPrivacyCollectedDataTypes`; `package.json:50` `"react-native-gesture-handler": "~2.28.0"`; `babel.config.js:206` `presets: ['babel-preset-expo']`; `eas.json:8` `"developmentClient": true`. Installed versions all reproduced: tsc `Version 5.9.3` (pin `~5.9.2`), expo 54.0.34 (pin `~54.0.33`), expo-camera 17.0.10, expo-image-picker 17.0.11, @expo/config-plugins 54.0.4, @expo/prebuild-config 54.0.8, @expo/config-types 54.0.10, @expo/plist 0.4.8, react-native-gesture-handler 2.28.0, expo-updates 29.0.17, jest 29.7.0.

### R2 — a7's stated mutation is FALSE. a7 survives every single mutation of the fix. Add a7b (mandatory).

§5 claims a7 is reddened by "variant C (camera-only opt-out)". That is true of variant C *in isolation*, but NOT of the fix this unit actually ships, because the fix also adds `android.blockedPermissions`. Measured from the full PROPOSED fix (`node ../.qa-w3b/probes/w37_fable_mutations.js`), one fix element removed at a time:

| mutation | a6 (iOS mic) | a7 (RECORD_AUDIO) | a8 (order-indep) |
|---|---|---|---|
| M0 none (full fix) | PASS undefined | PASS `tools:node=remove` | true |
| M1 restore `app.json:73` | PASS | **PASS** | true |
| M2 drop `android.blockedPermissions` | PASS | **PASS** | true |
| M3 drop camera `microphonePermission:false` | FAIL `"Allow $(PRODUCT_NAME)…"` | **PASS** | false |
| M4 drop camera `recordAudioAndroid:false` | PASS | **PASS** | true |
| M5 drop picker `microphonePermission:false` | PASS | **PASS** | false |
| M6 drop `blockedPermissions` AND picker opt-out | PASS | **FAIL — PLAIN REQUEST** | false |
| M8 revert whole fix (= main) | FAIL | FAIL — PLAIN REQUEST | true |

a7 is green under M1, M2, M3, M4, M5 and M7. It reddens only when **both** Android levers are dropped together (M6). As written it is a decoration with respect to every single-element mutation. Cause: `android.blockedPermissions` and the image-picker opt-out are mutually redundant — each alone produces `tools:node="remove"`.

Binding: add assertion **a7b**. Compile a deep copy of `expo` with `android.blockedPermissions` **deleted**, and assert `uses-permission` still carries `RECORD_AUDIO` only as `{'android:name': …, 'tools:node': 'remove'}`. This isolates the plugin lever from the app.json lever. Measured: green after the fix (M2 → `tools:node=remove`), red if the picker opt-out is dropped (M6 → plain request). Record a7b's mutation as "drop `expo-image-picker.microphonePermission:false`". With a7b added, every fix element has a test and both behavioural elements (M3, M5) are caught by an executed-output assertion.

### R3 — Deleting `app.json:73` is behaviourally INERT. Label a1 a source-shape pin.

Measured M1: re-adding `android.permission.RECORD_AUDIO` to `android.permissions` on top of the full fix changes nothing — intermediate `config.android.permissions` stays `["android.permission.CAMERA"]`, the plist is unchanged, and the manifest still carries `tools:node="remove"`. Mechanism READ on the installed source, not inferred: `@expo/config-plugins/build/android/Permissions.js:52-55` — `withBlockedPermissions` filters the blocked names out of `config.android.permissions` at registration time:

```js
if (config?.android?.permissions && Array.isArray(config.android.permissions)) {
  config.android.permissions = prefixAndroidPermissionsIfNecessary(config.android.permissions).filter(permission => !resolvedPermissions.includes(permission));
}
```

`expo-image-picker` calls it whenever `microphonePermission === false` (`withImagePicker.js:39-42`). So once the picker opt-out lands, line 73 is stripped automatically.

Binding: a1 stays (it is the literal ask of MB-TWO-LEVER-RELEASE-02 and keeps the committed source honest) but the spec and the PR body must describe it as a **source-shape pin with no compiled-output consequence**. The green phase must not count a1 as behavioural coverage. Same for the §7 red-first gate: a1 failing today proves the string is present, nothing more.

### R4 — `recordAudioAndroid: false` is fully inert. Split a3; its mutation row is wrong.

§5 a3's mutation reads "drop either option". Only one of the two bites. Measured M4: dropping `recordAudioAndroid:false` changes the plist, the manifest, `config.android.permissions` and order-independence not at all (identical to M0 on every axis). Measured M3: dropping `microphonePermission:false` reddens a6 **and** a8. The writer's own variant H showed this and §8 admits it; §5's mutation column contradicts §8.

Binding: split a3 into a3a (`microphonePermission === false`, behavioural — mutation M3 reddens a6 + a8) and a3b (`recordAudioAndroid === false`, **self-documenting pin, no behavioural mutation exists**). Keep a3b — it stops `expo-camera` from *requesting* the permission (`withCamera.js:15-19`, `recordAudioAndroid = true` default) in any future config where the picker no longer blocks — but state in the docstring that no assertion in this suite reddens when it is removed.

### R5 — `android.blockedPermissions` is writer-added scope. Permitted; declare it.

MB-TWO-LEVER-RELEASE-02's `fix` field names only: delete `android.permission.RECORD_AUDIO` from `android.permissions`, set the expo-camera entry to `{cameraPermission, microphonePermission:false, recordAudioAndroid:false}`, and the expo-image-picker entry to `{photosPermission, microphonePermission:false}`. It does **not** ask for `android.blockedPermissions`. The spec adds it.

Binding: keep it — it is consistent with the finding's own stated intent ("so no plugin can re-add it") and is schema-valid (`@expo/config-types` `ExpoConfig.d.ts:657`, consumed by `withInternalBlockedPermissions`, registered as an Android base mod at `@expo/prebuild-config/build/plugins/withDefaultPlugins.js:196`, re-read and confirmed verbatim). But the PR body must declare it as scope beyond the finding, and R2's a7b is **mandatory** so the belt does not hide whether the braces work.

### R6 — The jest worker force-exit warning is NOT this unit's. Delete the gate and the open question.

§8 flags "A worker process has failed to exit gracefully" as an unexplained risk attributed to loading `expo/config-plugins` in a worker, and §7 gate 2 makes the green phase re-run with `--detectOpenHandles` and record recurrence. Measured control experiment refutes the attribution:

* Two **trivial** passing suites (`expect(1+1).toBe(2)`, no `expo/config-plugins`, no app import) under default workers → warning reproduced on run 1 of 2.
* Two **heavy** passing suites that do execute the installed plugins → warning reproduced 3 of 3.
* Single suite alone (`w37.fable.leak.probe.test.ts`, which loads `expo/config-plugins` and asserts `IOSConfig.PrivacyInfo.mergePrivacyInfo` is a function) → no warning, 3 of 3. `process._getActiveHandles()` after the load reports only jest's own `Socket`/`Pipe`/`ChildProcess` entries — **no `Timeout`**, i.e. no leaked timer from config-plugins.
* Exit code with the warning present, captured correctly (`out=$(…); code=$?`, not through a pipe): `JEST_EXIT_CODE=0`, 2 of 2, `Test Suites: 2 passed`.

So the warning is a pre-existing property of this repo's jest 29.7.0 worker teardown on this machine, appears with ≥2 suites regardless of what they import, and **cannot fail CI** (exit 0). `expo/config-plugins` is exonerated.

Binding: delete the `--detectOpenHandles` gate and the §8/§11 open question. The green phase runs the unit file once, normally. If the warning appears in the full 278-suite run it is pre-existing noise and must not be chased or "fixed"; do not add `--forceExit`, `--runInBand`, or a lazy-require workaround for it.

### R7 — d1's edge scan MUST exclude `devDependencies`, or d1 is green and the unit's headline test dies.

An exhaustive walk of all **898** installed `package.json` files finds three packages declaring `react-native-gesture-handler` — every one of them a `devDependencies` edge:

```
@testing-library/react-native@13.3.3 :: devDependencies -> ^2.28.0
react-native-reanimated@4.1.7        :: devDependencies -> 2.28.0
react-native-screens@4.16.0          :: devDependencies -> ^2.28.0
```

Zero `dependencies`, `peerDependencies` or `optionalDependencies` edges. The writer's probe used `['dependencies','peerDependencies','optionalDependencies']` and is correct. But the hazard is live: MB-SAFE-HYGIENE-06's own verifier row says it "re-walked package-lock.json packages[*] for every dependencies/peerDependencies/optionalDependencies/**devDependencies** edge", so a red-phase agent reading the finding will plausibly widen the scan — and the moment `devDependencies` is included, `react-native-gesture-handler` becomes justified, `PENDING_REMOVAL` must be empty, and **d1 passes today**, silently deleting the unit's headline red test.

Binding: the test hard-codes exactly `const EDGE_FIELDS = ['dependencies', 'peerDependencies', 'optionalDependencies']` with a comment naming the three devDependency decoys above and this ruling. A `devDependencies` edge of an installed library is that library's own test tooling and is never a reason to ship a native module. (The finding's verifier reached the same conclusion — "the only residual references are inside react-native-screens' opt-in `gesture-handler/` subpath (the app never imports that subpath)".)

### R8 — d1 goes green by editing its own allowlist. Bookkeeping, not coverage.

d1's transition red→green comes from adding `'react-native-gesture-handler'` to `PENDING_REMOVAL` **inside the test file** — no product code changes. §5 half-admits this; §7 gate 1 still lists it as a red test.

Binding: label d1 bookkeeping-red in the spec and the PR body. The durable guards are **d2** (every `PENDING_REMOVAL` key is still declared — reddens the moment Ahmed uninstalls, forcing the entry's deletion) and **d4** (pending-removal names stay unimported — reddens on a future `import 'react-native-gesture-handler'`). Those two are the reason the allowlist is worth committing; d1 alone is not behavioural coverage.

### R9 — c4 is a key-name guard, not validation. Say what it can and cannot catch.

Read on the installed `@expo/config-plugins/build/ios/PrivacyInfo.js`: `mergePrivacyInfo(existing, privacyManifests)` destructures `NSPrivacyCollectedDataTypes = []` (`:96`) from `existing`, then for each incoming entry pushes it when no entry with that `NSPrivacyCollectedDataType` is already present (`:112-119`). With `existing = {}` this is the **identity map** over the array, provided type ids are unique (which c2 pins). Therefore c4 can never disagree with c1/c3 about content — it is not semantic validation.

Measured on the current config: `IOSConfig.PrivacyInfo.mergePrivacyInfo({}, expo.ios.privacyManifests)` → `NSPrivacyCollectedDataTypes = []`, `NSPrivacyTracking = false`, `NSPrivacyAccessedAPITypes.length = 4`. `mergePrivacyInfo` is exported and reachable as `IOSConfig.PrivacyInfo.mergePrivacyInfo` (`Object.keys` → `['mergePrivacyInfo','setPrivacyInfo','withPrivacyInfo']`), and is the exact function `withPrivacyInfo` → `setPrivacyInfo:63` uses to build `PrivacyInfo.xcprivacy`.

Binding: keep c4 — it is genuinely worth having, because it proves the array sits under the exact key the installed writer reads and that `NSPrivacyTracking:false` plus the four accessed-API entries survive the merge. State its mutation honestly: **reddens** on misspelling or misnesting the `NSPrivacyCollectedDataTypes` key, or altering an accessed-API reason; **does not redden** on any change to the data-type or purpose identifier strings. Those strings remain machine-unverifiable here (all 11 shipped `PrivacyInfo.xcprivacy` files carry an empty collected-types array) and stay an Ahmed/legal gate before merge.

### R10 — 43 vs 55 dependencies: not a contradiction. Record the reconciliation.

MB-SAFE-HYGIENE-06's title says "the only true orphan among **55** declared deps"; §10 measurement 9 says **43**. Measured: `dependencies = 43`, `devDependencies = 12`, sum `= 55`. The finding counts both blocks; d1 scans the 43 runtime `dependencies` only, which is correct (a devDependency is not shipped or autolinked).

Binding: record this in the spec so the green phase does not "correct" 43 to 55 or widen d1's input set to `devDependencies` (see R7).

### R11 — d1's import scan excludes `__tests__`; the finding's wording includes it. Keep the narrower scan.

MB-SAFE-HYGIENE-06's `test_first` says "imported somewhere under src/App.tsx/**__tests__**". §5 d1 scans `src/**/*.{ts,tsx}`, `App.tsx`, `index.ts` only. Measured: the outcome is identical either way — `react-native-gesture-handler` has `tests=0`, and the only zero-src-import dep with a test import is `babel-preset-expo` (`tests=1`), which is already justified twice over (`babel.config.js:206` and an `expo:dependencies` edge).

Binding: keep the narrower scan — an import inside a test suite is not a reason to ship a native module into every EAS build — and state the deviation plus this measurement in the test's docstring so it does not read as an oversight.

### R12 — e1 / -09: deferral CONFIRMED. Add the positive statement the red phase needs.

The spec's decision not to take -09's fix is correct and I confirm it from the finding's own text. MB-TWO-LEVER-RELEASE-09 `impact`: "the symmetric trap is already documented (M18 MB-two-lever-04: bumping expo.version BEFORE an OTA retargets it at a runtime no device has, reaching zero phones)", and its `fix` notes switching to `policy: "fingerprint"` "is itself a native-build change and must land with the next `eas build`". The verifier CONFIRMED that `appVersionSource: "remote"` (`eas.json:4`) with `autoIncrement: true` (`eas.json:19`, production profile) "bumps buildNumber/versionCode only, leaving expo.version — hence runtimeVersion — pinned at '1.0.0'".

Binding: add to §4.3 the positive statement, which the spec currently only implies — **W3-7's app.json edits are runtimeVersion-neutral.** The `appVersion` policy derives the runtime solely from `expo.version`, which this unit does not touch; permissions, plugin options, `blockedPermissions` and `privacyManifests` do not enter the runtime version. Therefore merging W3-7 neither retargets nor blocks the pending `eas update --branch preview`, and phones on 97b5f15 are unaffected — the changes simply do not take effect until the next `eas build`. e1 is the tripwire that keeps this true; its docstring must name `eas.json:4` `appVersionSource: "remote"` so Ahmed's later release commit is not written on the assumption that `app.json` `version` alone drives the store build number.

### R13 — b1/b2 must not assert "Expo template". That claim is not reproducible here.

Re-ran the search independently: `find node_modules/ -maxdepth 6 \( -name icon.png -o -name 'splash*.png' -o -name adaptive-icon.png \)` → **nothing**; and the only files anywhere in the repo of size 17547 B or 22380 B are the three assets themselves. So the template-identity claim is the repo's record (MB-SAFE-HYGIENE-01 title: "the exact SHA-256s recorded as Expo-template-identical **on 2026-05-24**"), not something derivable at this commit.

Re-measured: `icon.png` `74c64047eb557b1341bba7a2831eedde9ddb705e6451a9ad9f5552bf558f13de` (22380 B); `splash-icon.png` and `adaptive-icon.png` both `5f4c0a732b6325bf4071d9124d2ae67e037cb24fcc9c482ef82bea742109a3b8` (17547 B each).

Binding: word b1/b2 as "differs from the SHA-256 recorded on 2026-05-24", never "differs from the Expo template hash". The self-contained, reproducible evidence that the art is placeholder is that `splash-icon.png` and `adaptive-icon.png` are **byte-identical** — keep that as its own assertion (it is also exactly what HYGIENE-01's `test_first` asks for). Skip-with-reason under `ICON_ART_SUPPLIED = false` plus the `it.todo` is correct per the brief and stays.

### R14 — b1/b2/b3 must read the PNGs with `fs`. An `import` silently hashes the stub.

`jest.config.js:55` maps `'\\.(ttf|otf|woff2?|png|jpg)$'` → `<rootDir>/__mocks__/fileStub.ts`. Any `import`/`require` of a PNG from the test resolves to the stub, so `sha256` would hash the stub and b1/b2 would be meaningless — the "test cannot reach the value it claims to test" hazard. §4.1 says "fs only" in prose; this makes it binding: `fs.readFileSync(path.join(APP, 'assets/icon.png'))` + `crypto.createHash('sha256')`, never a module import. Same for `app.json`, `package.json` and `docs/privacy-data-inventory.md` — read and `JSON.parse`, do not `require` (`require` would also cache and hide edits within a run).

### R15 — a5 is referenced in §6 but never defined in §5. Define it.

§6 row 1 cites "a5 (static, GREEN today)"; §5's table has a1-a4, a6, a7, a8 and no a5. As written the red phase cannot know what to implement. Binding definition: **a5** = static pin, GREEN today, asserting `expo.android.permissions` contains `'android.permission.CAMERA'`, the expo-camera entry's `cameraPermission === 'Qaren needs camera access to photograph products for comparison.'`, and the expo-image-picker entry's `photosPermission === 'Qaren needs photo library access to identify products from your photos.'` — i.e. the fix removes the microphone without disturbing the two purpose strings or the camera request. Verified present and exact at b63a8368 (`app.json:72`, `:95`, `:101`).

### R16 — Do not hard-code the entry count. The inventory doc is the single source.

§4.1 says "12 entries". §11 records the open question of whether legal collapses `SearchHistory` and `OtherUserContent`, and MB-TWO-LEVER-RELEASE-08's `fix` enumerates ten types "e.g.". Binding: no assertion may hard-code a count. c1 asserts non-empty; c2 asserts per-entry shape, id pattern, uniqueness and `Tracking === false` while `NSPrivacyTracking === false`; c3 asserts set-equality with the doc's first ```` ```json ```` fence. Adding or removing a row must require editing exactly two places (app.json and the doc) and nothing else. The identifier spellings stay an Ahmed/legal gate before merge (R9).

### R17 — Confirmed-correct items (re-measured; no change required)

Recorded so the green phase does not re-litigate them:

* **Plugin option names come from the installed source, as the brief demanded.** `expo-camera/plugin/build/withCamera.js` (22 lines) and `.d.ts`: `cameraPermission?: string|false`, `microphonePermission?: string|false`, `recordAudioAndroid?: boolean` (default `true`, `:7`). `expo-image-picker/plugin/build/withImagePicker.js` (47 lines) and `.d.ts`: `photosPermission`, `cameraPermission`, `microphonePermission`. Both quoted in §3.1 verbatim-correct.
* **The `cameraPermission: false` landmine is real.** `withImagePicker.js:41` — `cameraPermission === false && 'android.permission.CAMERA'` is passed to `withBlockedPermissions`, which would block the camera the app needs. §4.1's warning stands.
* **iOS deletion mechanism.** `@expo/config-plugins/build/ios/Permissions.js:30-36` — `applyPermissions` deletes the key when the option is `=== false`, else writes `permissions[p] || infoPlist[p] || default` (`:34`), which is why the current config compiles the boilerplate microphone string. `withCamera`/`withImagePicker` discard `createPermissionsPlugin(...)`'s return value, which is harmless: `withBaseMod` mutates `config.mods` in place (`plugins/withMod.js:54-58`, `:123`) and returns the same object.
* **All four probe outputs reproduce exactly**: `w37_plugin_exec.js` (CURRENT mic string + plain RECORD_AUDIO; PROPOSED mic `undefined` + `tools:node=remove`), `w37_plugin_variants.js` (the A-H table in §3.1, byte-for-byte), `w37_dep_usage_scan.js` (`dependencies: 43 | scanned source files: 454`, seven zero-import candidates, only `expo-build-properties`/`expo-dev-client`/`react-native-gesture-handler` with NONE edges), and the probe suite tally `Tests: 8 failed, 2 skipped, 1 todo, 6 passed, 17 total` with failures a1-a4, a6, a7, c1, c3 exactly.
* **Privacy-inventory collection anchors re-located at b63a8368**: `api.ts:888` `export async function trackEvents` (the verifier's `api.ts:814-846` is stale — the spec's re-location to `:888-898` is correct), `deviceFingerprint.ts:32` `Crypto.digestStringAsync`, `pushTokenService.ts:77` `getExpoPushTokenAsync`, `sentry.ts:235` `Sentry.init` with `:237` `sendDefaultPii: false`, and `grep -rn setUser src/` → only React `useState` setters, no `Sentry.setUser`. The conservative `Linked: true` on the Sentry rows is a defensible call for legal to downgrade, not a defect.
* **Test placement and collection.** `__tests__/config/` exists (`featureBucket.test.ts`, `features.test.ts`); `jest.config.js:4` `testMatch: ['**/__tests__/**/*.test.ts', …]` collects the new file with no flag; `testEnvironment: 'node'`; CI runs the whole suite via `npx jest --ci` (`ci.yml:264`) inside the required `frontend-tests` job, so no branch-protection change is needed. `.qa-w3b/` is outside jest's `rootDir` (`SmartCompareApp`) and is gitignored at `.gitignore:72` (`.qa-*/`), so probes are never collected by CI and never appear in `git status`. `__tests__/setup.ts` is benign (16 lines: `extend-expect`, `__DEV__ = false`, and silencing `console.warn`/`console.error` — note the silencing, so do not rely on console output for evidence inside the suite).
* **-02's option shapes match the finding's own `fix` text**, including its explanation that image-picker "additionally calls withBlockedPermissions in that case, which is what actually strips it from the merged manifest" — consistent with R3's mechanism.
* **Gradle caveat is correctly stated.** The test asserts the `tools:node="remove"` attribute emitted by `@expo/config-plugins`; the actual drop of `expo-camera`'s library-level `RECORD_AUDIO` (`expo-camera/android/src/main/AndroidManifest.xml:3`) happens in Gradle's manifest merge during a real build, which no test here reaches.

### R18 — Red-phase execution order (supersedes §7 gate 1 and gate 2)

1. Write the full test file with `PENDING_REMOVAL = {}` and `ICON_ART_SUPPLIED = false`. Run `node node_modules/jest/bin/jest.js --ci __tests__/config/nativeBundle.w37.test.ts`. Required red set: **a1, a2, a3a, a3b, a4, a6, a7, a7b, c1, c2, c3, c4, d1**. Required green set: **a5, a8, b3, d2, d4, e1**; b1/b2 skipped, b3-todo and d3 reported as todo. Any other outcome is a spec defect — stop and report, do not adjust the test to fit.
2. Apply the app.json edits and write `docs/privacy-data-inventory.md`; add the `PENDING_REMOVAL` entry. Re-run: all green, b1/b2 still skipped.
3. Mutation check — revert each of M1-M5 in turn and confirm the ruling's table (R2/R3/R4): M3 must redden a3a + a6 + a8; M5 must redden a4 + a7b + a8; M1 reddens a1 only; M2 reddens a2 only; M4 reddens a3b only.
4. `node node_modules/typescript/bin/tsc --noEmit` and `node node_modules/eslint/bin/eslint.js "__tests__/config/nativeBundle.w37.test.ts"`. Do not run the full 278-suite jest here; the green phase owns that. No `--detectOpenHandles` gate (R6).
5. `git status --short` must show only the three intended files. `git diff --stat -- SmartCompareApp/package.json SmartCompareApp/package-lock.json SmartCompareApp/assets` must be empty.
