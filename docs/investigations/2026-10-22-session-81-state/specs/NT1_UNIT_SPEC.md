# NT1_UNIT_SPEC: NT1a NATIVE 1.0.1, the P0 only (provider-neutral camera / photo purpose strings + expo.version 1.0.1)

- Unit: NT1a (the P0 of PLAN_S81 unit NT1; the rest is NT1b, out of scope, section 10). Client, NATIVE config. FOCUS (App-Review-visible surface + the OTA runtime; LC-1): spec review, RED gate, GREEN, two adversaries (correctness; app-review-and-privacy), final round with the full jest suite once (LC-7).
- Flag: NONE. A native config unit: React Native reads no per-call env flag. The invariant that replaces flag-OFF identity (section 2.4): every byte outside the two purpose strings (app.json + locales en / ar), expo.version and the pins that name them is identical to base; no file under app/, src/, SmartCompareApp/src/ or migrations/ moves.
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-nt1 (detached at base). Branch for GREEN: feature/s81-nt1a-native-101.
- Base sha: 6b909e0a92067d6b3562eee325e4956c116441f7 (origin/main 2026-11-11 20:30, #399 S81-04c). `git status --short` EMPTY before and after every probe of this spec (measured; the spec itself lives under .qa-s80/, ignored by .gitignore:72 `.qa-*/`).
- Store-build identity (measured): `git diff --stat 683f56c0 6b909e0a -- SmartCompareApp/app.json SmartCompareApp/eas.json SmartCompareApp/package.json SmartCompareApp/locales` is EMPTY: the four config files at base are the bytes of the store build MYEZ 1.0.0 (3).
- Evidence pointers (all read in this run): NT1_BRIEF.md (R-NT1-1..8, Q1-Q7); s81-common.txt; PLAN_S81.md (copy: the NT1 unit text is at PLAN_S81.md:179 in the scratchpad copy, :165 in the docs-checkout numbering the brief cites; Standing constraints :13-19; owner decision 10 :208; VERIFY corrections :98 / :109); RULINGS_CLAUDE_PATH.md C5; OTA_READINESS_2026-11-07.md; RULINGS_S81_08.md; RULINGS_FIX1_S81_12.md F1-6; the eas-cli 18.8.1 install at %APPDATA%/npm/node_modules/eas-cli (oclif.manifest.json + build/*.js, read offline; nothing executed). Measurement notes and scripts: <scratchpad>/nt1/notes/ (ar_check.py / ar_check.out, canon.py / canon.out, base1.log, base2.log).
- Sister units and contracts: S81-12 LEGAL-V3 (PR #378, branch origin/feature/s81-legal-v3 e8c8c1dc, merge-base 6c14ac95): its three-dot diff touches NONE of this unit's files (measured: `git diff --stat 6b909e0a...origin/feature/s81-legal-v3 -- SmartCompareApp/app.json SmartCompareApp/locales SmartCompareApp/__tests__/config SmartCompareApp/__tests__/b3a SmartCompareApp/__tests__/fixtures/b3a_copy.json` empty); the only shared file is CLAUDE.md (a known rebase: NT1a's block lands after #378's). The contract consumed from S81-12: the phrase "our AI providers" (Terms s8 heading and licence grant, F1-6; privacy "section 4 explains what is sent to our AI providers"), and the AR phrase of its texts (section 2.2). CL3 / CL4 / S81-11d / S81-24e: not on main; they only matter for what the 1.0.1 BUILD commit embeds (R-NT1-4 c, section 2.6). The merge freeze on main for the #378 round applies (R-NT1-7).
- Personal-data rule: no personal value in any file, test, fixture or log (the repo is public). The Apple team id and ASC app id already in eas.json:26-27 are not repeated anywhere new. No .env read, no secret printed, no Railway / EAS / ASC / network call by any agent of this unit.

## 0 WHAT the unit does

1. The two iOS purpose strings that today name OpenAI stop naming any provider: the expo-camera `cameraPermission` (app.json:220) and the expo-image-picker `photosPermission` (app.json:228), mirrored as `NSCameraUsageDescription` / `NSPhotoLibraryUsageDescription` in locales/en.json:4-5 (byte-equal to app.json) and their Arabic twins in locales/ar.json:4-5. "OpenAI" becomes "our AI providers" (the v3 policy / Terms phrase, F1-6); the AR provider token OPENAI_AR (section 1.1) becomes the shadda-free form of the v3 AR phrase. Nothing else in the sentences moves.
2. `expo.version` 1.0.0 -> 1.0.1 (app.json:5). Nothing else moves: the iOS build number is remote (eas.json:4 `appVersionSource: "remote"` + :19 `autoIncrement: true`), package.json `version` is npm metadata Expo does not read (Q1).
3. The pins that name the old strings or the old version are re-aimed (E1-E5), never weakened; one new RED file pins the new truth and the byte-identity invariant.
4. No JS / TS source change, no backend change, no dependency change, no package-manager run, no build, no publish (R-NT1-6). The unit is DONE only when the 1.0.1 binary on the owner's phone shows the new prompts (R-NT1-8).

## 1 BASE STATE (measured at 6b909e0a)

### 1.1 The strings (SmartCompareApp/)
| file:line | key | value at base |
|---|---|---|
| app.json:5 | expo.version | "1.0.0" |
| app.json:16-19 | expo.locales | { en: ./locales/en.json, ar: ./locales/ar.json } |
| app.json:217-224 | plugins["expo-camera"] | cameraPermission (:220) = "MYEZ uses the camera to photograph the two products you want to compare. The photos are uploaded to MYEZ's servers and sent to OpenAI to identify the products."; microphonePermission (:221) = "MYEZ only uses the camera to photograph products. Audio is never recorded."; recordAudioAndroid (:222) false |
| app.json:225-231 | plugins["expo-image-picker"] | photosPermission (:228) = "MYEZ opens your photo library only for the photos you pick. Those photos are uploaded to MYEZ's servers and sent to OpenAI to identify the products."; microphonePermission (:229) = the same MIC sentence |
| app.json:272-274 | expo.runtimeVersion | { policy: "appVersion" } |
| app.json:275-277 | expo.updates.url | https://u.expo.dev/<projectId> |
| locales/en.json:3-6 | ios.* | CFBundleDisplayName "MYEZ"; NSCameraUsageDescription / NSPhotoLibraryUsageDescription = byte-equal to app.json:220 / :228; NSMicrophoneUsageDescription = MIC |
| locales/ar.json:3-6 | ios.* | CFBundleDisplayName (sha256 5d3c4d53...); NSCameraUsageDescription sha256 8e418902289a71fa371109a362ab4641bbda06bc8609cbb8491e17b987283c2a; NSPhotoLibraryUsageDescription sha256 4a5e381e2f0dd2b6910248588549e928eb45ca02d89de330cd714d044ff475d3; NSMicrophoneUsageDescription sha256 999e6f18... |

The AR base strings as JSON escapes (pure ASCII here; the file holds UTF-8):
- camera: "\u064a\u0633\u062a\u062e\u062f\u0645 \u0645\u064a\u0651\u0632 \u0627\u0644\u0643\u0627\u0645\u064a\u0631\u0627 \u0644\u062a\u0635\u0648\u064a\u0631 \u0627\u0644\u0645\u0646\u062a\u062c\u064a\u0646 \u0627\u0644\u0644\u0630\u064a\u0646 \u062a\u0631\u064a\u062f \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629 \u0628\u064a\u0646\u0647\u0645\u0627. \u062a\u0631\u0641\u0639 \u0627\u0644\u0635\u0648\u0631 \u0625\u0644\u0649 \u062e\u0648\u0627\u062f\u0645 \u0645\u064a\u0651\u0632 \u0648\u062a\u0631\u0633\u0644 \u0625\u0644\u0649 \u0623\u0648\u0628\u0646 \u0625\u064a\u0647 \u0622\u064a \u0644\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a."
- photos: "\u064a\u0641\u062a\u062d \u0645\u064a\u0651\u0632 \u0645\u0643\u062a\u0628\u0629 \u0627\u0644\u0635\u0648\u0631 \u0641\u0642\u0637 \u0644\u0644\u0635\u0648\u0631 \u0627\u0644\u062a\u064a \u062a\u062e\u062a\u0627\u0631\u0647\u0627. \u062a\u0631\u0641\u0639 \u0647\u0630\u0647 \u0627\u0644\u0635\u0648\u0631 \u0625\u0644\u0649 \u062e\u0648\u0627\u062f\u0645 \u0645\u064a\u0651\u0632 \u0648\u062a\u0631\u0633\u0644 \u0625\u0644\u0649 \u0623\u0648\u0628\u0646 \u0625\u064a\u0647 \u0622\u064a \u0644\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a."
- The provider token is exactly OPENAI_AR = "\u0623\u0648\u0628\u0646 \u0625\u064a\u0647 \u0622\u064a" (once in each string; measured by ar_check.py).

### 1.2 Version and build numbers (Q1)
| where | what | moves in NT1a? |
|---|---|---|
| app.json:5 `expo.version` | the marketing version (CFBundleShortVersionString) AND, through `runtimeVersion.policy: appVersion`, the OTA runtime | YES -> "1.0.1" |
| eas.json:3-4 `cli.version ">= 18.8.1"`, `appVersionSource: "remote"` | the build number (CFBundleVersion / versionCode) lives on EAS servers | NO |
| eas.json:18-21 production `autoIncrement: true`, `channel: "production"` | EAS increments the remote build number at each production build (3 -> 4 expected; `eas build:version:get` is the owner's read) | NO |
| app.json `ios.buildNumber` / `android.versionCode` | ABSENT (measured: top-level expo keys = android, extra, icon, ios, locales, name, newArchEnabled, orientation, owner, plugins, runtimeVersion, scheme, slug, splash, updates, userInterfaceStyle, version, web) | NO (adding one would fight the remote source) |
| package.json:3 `"version": "1.0.0"` | npm package metadata of `smartcompareapp`; Expo reads expo.version, never this; mirrored in package-lock.json's root | NO (moving it edits package-lock.json, a dependency-file change R-NT1-6 forbids; Q-O2) |
| SmartCompareApp/src, App.tsx, index.ts | no version literal (measured: `git grep "1\.0\.0\|1\.0\.1" -- src App.tsx index.ts` empty) | NO |
| app/api/version_routes.py:34-36 | `APP_MIN_VERSION` / `APP_LATEST_VERSION` defaults "1.0.0", `APP_FORCE_UPDATE` default false (env, owner) | NO (Q5, document only) |
| SmartCompareApp/src/services/appVersionService.ts:129 | the client compares `Application.nativeApplicationVersion` (the BINARY's version: OTAs never move it) | NO |

How eas-cli 18.8.1 uses expo.version (read in the installed build, offline): managed workflow (no SmartCompareApp/ios or /android dir, measured) -> build/build/ios/version.js:95-107 `readShortVersionAsync` returns `exp.version`; build/build/ios/build.js:42-48 takes the build number from `resolveRemoteBuildNumberAsync` when appVersionSource is REMOTE (local autoIncrement forced false, :71-73). `eas update` derives the runtime per platform from the project config at publish time (build/commands/update/index.js:318 -> build/project/publish.js:487 `getRuntimeVersionInfoObjectsAsync` -> resolveRuntimeVersionAsync.js:36 `Updates.getRuntimeVersionNullableAsync(projectDir, exp, platform)`); `eas update` has NO runtime-version flag (its flags: branch, channel, message, input-dir, skip-bundler, clear-cache, no-bytecode, source-maps, emit-metadata, rollout-percentage, platform, auto, private-key-path, environment, json, non-interactive).

The w37 drift nodes: the four accepted base failures of config/nativeBundle.w37 are d5, k2, k4, k5 (session-79 GATE_B3.md:9 / :23): they compare package.json / package-lock.json / the clone's node_modules versions (react-native-gesture-handler removal, the five SDK-54 packages, eslint-config-expo, expo-install consistency). None reads expo.version or a purpose string; NT1a moves none of them (they stay red exactly as at base).

### 1.3 Readers of the two sentences (Q2; `git grep` over the worktree at base)
| reader | file:line | reads | class |
|---|---|---|---|
| nativeBundle.w37 | __tests__/config/nativeBundle.w37.test.ts:64-67 (comment + CAMERA_PURPOSE / PHOTOS_PURPOSE literals) | the EN strings | E1 |
| w37 a5 | :201-206 | plugin options == literals | moves with E1 (assertion unchanged) |
| w37 a6 | :208-213 | executed Info.plist == literals | moves with E1 |
| w37 u10 | :1394-1408 | en.json == literals == plugin options | moves with E1 |
| w37 u9 / u11 / u12 | :1373-1392 / :1410-1445 / :1447-1460 | locale shape, AR fence (no Latin, no diacritics outside the brand, copy-policy banned + scary terms, AR != EN), Android resolves no strings | STAY (must pass on the new AR strings: measured by ar_check.py, section 2.2) |
| b3a fixture | __tests__/fixtures/b3a_copy.json:91-92 (native.en), :95-96 (native.ar) | both languages, both keys | E3 |
| b3a r33 | __tests__/b3a/nativeStrings.b3a.test.ts:90-98 (`toContain('OpenAI')` at :96) | plugin options == fixture; contains 'servers' and 'OpenAI' | E4 |
| b3a r34 | :29 OPENAI_AR, :100-111 (`includes(OPENAI_AR)` at :108) | locales == fixture; AR contains OPENAI_AR and SERVERS_AR | E4 |
| b3a r35 | :113-122 | executed Info.plist == fixture EN (both orders) | moves with E3 |
| b3a r38 | :171-185 | MIC strings, display names, en key set | STAY (PIN) |
| honestCopy.b3a | __tests__/b3a/honestCopy.b3a.test.tsx:20 | requires b3a_copy.json (reads the en / ar catalogs, NOT `native`: measured) | STAY, joins the comm set |
| HomeScreen.tsx:820, Step05Trust.tsx:13 / :23 | comments only ("sent to OpenAI") | no assertion; JS / TS source is out of scope (R-NT1-6); Step05Trust copy is S81-12's | not touched |
| landing/privacy.html:206, tests/fixtures/legal_prefill_u8/privacy_policy.md:28, app/legal/privacy_policy.md:28 | the v2 policy sentence, not the purpose string | S81-12 rewrites them ("our AI providers") | not touched |
| tests/test_extraction_cohort_prompt.py:8 / :298 | docstrings about prompts | not a reader | none |
| docs/** | historic specs, PR bodies, audits (W3_7_UNIT_SPEC, B3A spec, appstore findings, NOTES_DRAFT*, REVIEW_NOTES_*_S77) | frozen records | not edited |
| CLAUDE.md:508 | "build 3's Info.plist purpose strings say photos go to OpenAI, `app.json:220,228`" (the S81-06 flip-order sentence) | prose | stays TRUE for build 3 until 1.0.1 is live; rewritten in place on the dated line that 1.0.1 is live (R-A15), not in this unit |
| CLAUDE.md:759 | the W3-7 / U4a summary of `expo.locales` | prose, no string quoted | unchanged |

No store-metadata doc in the repo quotes the purpose strings (the ASC listing and Notes for Review live in App Store Connect; the drafts in docs/investigations/2026-10-1x are historic).

### 1.4 Readers of expo.version / the runtime (Q1 / Q2)
| reader | file:line | class |
|---|---|---|
| w37 e1 | __tests__/config/nativeBundle.w37.test.ts:1107 (title "... expo.version is \"1.0.0\""), :1108-1128 (comment: "Ahmed changes both this pin and app.json in the release commit AFTER the last OTA to the 1.0.0 fleet"), :1130 `expect(expo.version).toBe('1.0.0')` | E2 (the release commit this comment anticipates) |
| w37 p1 / p2 | :1133 / :1149 | plugin names + ORDER, updates.url + projectId | STAY |
| versionCompare.a9 | __tests__/versionCompare.a9.test.ts:168-172 | a literal 1.0.0 vs 1.0.0 (reads no file) | STAY |
| appVersionService.a9, s11/launchSurfaces.s11, s11/categoryRow.s11 | mockNativeVersion / server-body literals | STAY (mocked versions; no file read) |
| backend | app/api/version_routes.py:34-36 | env defaults | not touched |

### 1.5 Config readers by path (Q6)
Client suites that read app.json / locales / eas.json by path: b3a/nativeStrings.b3a (app.json, locales), config/nativeBundle.w37 (app.json, locales, eas.json:8 developmentClient, package.json, lock, node_modules), config/domain.s76 (app.json, eas.json, App.tsx, index.ts, the locales/ walk: D4 no "qaren.app"), clientTruth/privacyManifest.s74 (app.json manifest), brand/inAppMark.u4c B7 (app.json launcher art + splash; package.json no expo-image). Comment-only mentions: navigation/linking.w315.test.ts:107 / :164, AuthScreens.socialDiagnostic.pa8.test.tsx:92, versionCompare.a9:168.
BACKEND tests that scan SmartCompareApp config by path (the fourteen-fence rule run the other way): tests/test_legal_docs_u8.py:785 (CLIENT_PROBES "EAS Update": needle u.expo.dev in SmartCompareApp/app.json, positive control); tests/test_legal_s78.py via tests/fixtures/legal_s78.json:306-308 (the eas_update row's module path SmartCompareApp/app.json, read by p.read_text at :109); app/legal/processors.json:95 (module ["SmartCompareApp/app.json"]) read by the processors readers tests/test_legal_disclosure_s77.py, test_legal_docs_u8.py, test_legal_docs_u8_polish.py, test_legal_s78.py, test_s79_b3b_apple_revoke.py, test_s81_s06_anthropic_router.py, test_s81_s22b_self_critique_retire.py, test_s81_sf1_surfaces_be.py; tests/test_ci_gates.py:933 EAS_JSON (eas.json cli.version range :1049-1060, production channel :1244, requireCommit :1291); tests/test_migration_037_security_definer_grants.py:892 (a docstring naming app.json / eas.json, no read). No backend test reads locales/ or the purpose strings. None of these needles (u.expo.dev, the module path, eas.json keys) moves in NT1a.

### 1.6 Readers of the version on the backend and the force-update path (Q5)
appVersionService.ts:109-115 forces an update only when `force_update === true` AND current < min_version; :129 current = `Application.nativeApplicationVersion` (the binary). Once 1.0.1 is live: `APP_MIN_VERSION=1.0.1` + `APP_FORCE_UPDATE=true` on web would block every 1.0.0 install (the store-only ones that never update the binary) with the force-update screen; `APP_LATEST_VERSION=1.0.1` alone only informs. RULINGS_CLAUDE_PATH C3(c): APP_MIN_VERSION has no role for the text flips; its role returns when 1.0.1 is live. Documented only: the owner's call 4 (specs/RULINGS_TESTING_PHASE.md, not opened here).

### 1.7 Android (Q3)
The expo-camera / expo-image-picker purpose options are iOS Info.plist keys; locales are resolved for iOS only (w37 u12 :1447-1460 pins `getResolvedLocalesAsync(APP, locales, 'android')` == { en: {}, ar: {} }; u9's comment :1374-1377: top-level keys would reach Android, so "ios" is the only top-level key). Android asks for CAMERA with the OS's own dialog (app.json:181-183) and shows none of these strings. MYEZ ships on the App Store only (the six GCC storefronts); no Play listing is recorded.

### 1.8 Guards GREEN must not trip
- w37 u9: exactly the four keys under "ios"; no `"` and no `\` in any value (ios/Locales.js writes values unescaped). The new EN strings contain one apostrophe (MYEZ's), as today: allowed.
- w37 u11: AR values: Arabic present, NO Latin letter, no diacritic [\u064B-\u0652] outside the brand word (\u0645\u064a\u0651\u0632 keeps its shadda), none of .copy-policy.json banned_ar / scary_vocab_ar, AR != EN. Measured on the drafts: diacritics False, latin False, unsafe False, banned [], scary [], neq_en True.
- w37 p1: plugin names and ORDER unchanged. w37 c1-c5 / b3a r36 / r37 / privacyManifest.s74: the manifest and docs/privacy-data-inventory.md untouched.
- domain.s76 D4: no "qaren.app" introduced.
- Pre-commit hook + gitleaks: no key-shaped literal (the new pins hold sha256 hex under names free of key / token / secret / auth / api / credential / password / access, per the gitleaks keyword rule).
- The i18n copy fences read src/i18n only (copy-policy.test.ts); locales/ is fenced by w37 u11 alone.

### 1.9 Line endings and bytes (working copy, core.autocrlf=true; the index is LF)
| file | bytes | CRLF lines | non-ASCII bytes | sha256 (working copy) |
|---|---|---|---|---|
| SmartCompareApp/app.json | 10438 | 279 | 0 | e31ceefaf0ac2d3c4752550d44e150b7d239de0c2a0b49280a7854f8edb7d844 |
| SmartCompareApp/eas.json | 645 | 31 | 0 | 46dc2663b6c2e887b4ae38d383f71f10d4894085de89ce16dafa2a0ea7c4a418 |
| SmartCompareApp/package.json | 2577 | 81 | 0 | 397f71bb64387015cbaa9b448b6e742957720bdb47b38c41ff85680a73490716 |
| SmartCompareApp/locales/en.json | 560 | 8 | 0 | 4673ffc8e135944caef4051b5e680fc42bb1ca8c1941357b102d37404675667a |
| SmartCompareApp/locales/ar.json | 747 | 8 | 516 | 1a1ade194cf67751601aced1ef1b3a10e820c4ce42a48d684a583640d60d4326 |
| SmartCompareApp/__tests__/fixtures/b3a_copy.json | 7448 | 99 | 2120 | 76ed94a382c3d648902e547df6cc00702244f891a8336d2424d7230265deace2 |
| SmartCompareApp/__tests__/b3a/nativeStrings.b3a.test.ts | 9359 | 186 | 28 | d1ccc4a21eb2ede7624e1c3ed9e6f15172a760b3e6b9e2a358831b0d06acaf4e |
| SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts | 89808 | 1678 | 259 | 8c6d175c4487e841be50be22ad4fddbc9a459b0b3347fa19cb7c8f8ad7f88552 |
Every file ends with a newline. GREEN edits with the Edit tool (line endings kept); a whole-file line in `git diff --stat` is a defect. locales/ar.json and the fixture are UTF-8 by design (the only files of the unit allowed bytes > 127; the RED file escapes every Arabic code point as \uXXXX so it stays ASCII).

### 1.10 Base pass state
- Client (jest): NOT RUN in this round by the brief (no node_modules junction at the spec stage). Recorded baseline (common brief, MOVING MAIN 6b909e0a): 411 suites, 4,030 passed + the four w37 drift nodes (d5, k2, k4, k5) + 13 skipped + 13 todo. The RED round measures the touched suites at base through the junction.
- Backend config readers + CLAUDE.md readers + the legal / processors readers at base (pyt.py, venv .venv-qaren, one process, the foreign-process probe empty before each):
  - `[pyt] tag=nt1-spec-base1 start=2026-11-11 21:42:40 end=2026-11-11 21:42:56 elapsed=15s bound=1200s status=OK rc=0` -- tests/test_legal_docs_u8.py tests/test_legal_s78.py tests/test_ci_gates.py tests/test_migration_037_security_definer_grants.py: 149 passed, 4 deselected; `[hermeticity] sentinel checked 149 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
  - `[pyt] tag=nt1-spec-base2 start=2026-11-11 21:43:02 end=2026-11-11 21:43:37 elapsed=35s bound=1200s status=OK rc=0` -- tests/test_behavior_dimension_translation.py tests/test_s81_s04_spend_breaker.py tests/test_s81_s08b_legacy_fingerprint.py tests/test_s81_s08b_gate_rows.py tests/test_s81_s23_bypass_retire.py tests/test_legal_disclosure_s77.py tests/test_legal_docs_u8_polish.py tests/test_security_regression.py: 662 passed; `[hermeticity] sentinel checked 662 test(s)`; `[netguard] blocked 36 attempt(s) from 8 node(s)` (the sentinel / neutralized supabase.invalid and api.openai.com attempts of test_security_regression, base noise, no failure).
  - FAILED node-id set at base for these 12 files: EMPTY. Not a full comm-set base record (section 7 names the full set; LC-6 stores it at RED / GREEN).

## 2 CONTRACT

### 2.1 Flag and knobs
None. The "switch" is the binary: build 1.0.0 (3) keeps its strings forever; a 1.0.1 build carries the new ones. Rollback = do not submit / do not release 1.0.1 (an OTA cannot change Info.plist).

### 2.2 The new values (every one a literal the RED file pins)
EN (both places byte-equal: app.json plugin options AND locales/en.json):
- NEW_CAM_EN = "MYEZ uses the camera to photograph the two products you want to compare. The photos are uploaded to MYEZ's servers and sent to our AI providers to identify the products." (169 bytes; sha256 aa17e72bb46be89557c2e56ff824efc79f5990e83f1e2f9a39ea0778763d3407)
- NEW_PHOTOS_EN = "MYEZ opens your photo library only for the photos you pick. Those photos are uploaded to MYEZ's servers and sent to our AI providers to identify the products." (158 bytes; sha256 23ffac74fbbecdac80902515d4aa5e93e72c9e2068ff4a4f0e6941c7bd5ee868)
Each is the base string with the one token "OpenAI" replaced by "our AI providers" (asserted by ar_check.py).

AR (locales/ar.json only; [NATIVE READ] each): the base string with OPENAI_AR replaced by AI_PROVIDERS_AR = "\u0645\u0632\u0648\u062f\u064a \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a \u0644\u062f\u064a\u0646\u0627" (gloss: "our AI providers"; the v3 AR policy and Terms write the same words with a shadda on the first one, "\u0645\u0632\u0648\u0651\u062f\u064a \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a \u0644\u062f\u064a\u0646\u0627", measured in origin/feature/s81-legal-v3:app/legal/privacy_policy_ar.md and terms_of_service_ar.md; R-NT1-2 and w37 u11 forbid the shadda outside the brand word, so the purpose string drops it). The sentence keeps "\u0625\u0644\u0649" before it: "... \u0648\u062a\u0631\u0633\u0644 \u0625\u0644\u0649 \u0645\u0632\u0648\u062f\u064a \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a \u0644\u062f\u064a\u0646\u0627 \u0644\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a."
- NEW_CAM_AR = "\u064a\u0633\u062a\u062e\u062f\u0645 \u0645\u064a\u0651\u0632 \u0627\u0644\u0643\u0627\u0645\u064a\u0631\u0627 \u0644\u062a\u0635\u0648\u064a\u0631 \u0627\u0644\u0645\u0646\u062a\u062c\u064a\u0646 \u0627\u0644\u0644\u0630\u064a\u0646 \u062a\u0631\u064a\u062f \u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629 \u0628\u064a\u0646\u0647\u0645\u0627. \u062a\u0631\u0641\u0639 \u0627\u0644\u0635\u0648\u0631 \u0625\u0644\u0649 \u062e\u0648\u0627\u062f\u0645 \u0645\u064a\u0651\u0632 \u0648\u062a\u0631\u0633\u0644 \u0625\u0644\u0649 \u0645\u0632\u0648\u062f\u064a \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a \u0644\u062f\u064a\u0646\u0627 \u0644\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a." (278 UTF-8 bytes; sha256 cf0a067db3b08a308f2afdfc793e8dda50d655e28349d10a2058a40e286d53de) [NATIVE READ]
- NEW_PHOTOS_AR = "\u064a\u0641\u062a\u062d \u0645\u064a\u0651\u0632 \u0645\u0643\u062a\u0628\u0629 \u0627\u0644\u0635\u0648\u0631 \u0641\u0642\u0637 \u0644\u0644\u0635\u0648\u0631 \u0627\u0644\u062a\u064a \u062a\u062e\u062a\u0627\u0631\u0647\u0627. \u062a\u0631\u0641\u0639 \u0647\u0630\u0647 \u0627\u0644\u0635\u0648\u0631 \u0625\u0644\u0649 \u062e\u0648\u0627\u062f\u0645 \u0645\u064a\u0651\u0632 \u0648\u062a\u0631\u0633\u0644 \u0625\u0644\u0649 \u0645\u0632\u0648\u062f\u064a \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a \u0644\u062f\u064a\u0646\u0627 \u0644\u0644\u062a\u0639\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a." (246 UTF-8 bytes; sha256 b0506c299ff48967709cce1dd00d22c63cc051e9b30ba19907cfade6da431d3e) [NATIVE READ]
The fence check of the drafts (w37 u9 / u11 rules + .copy-policy.json, run by ar_check.py): no diacritic outside the brand, no Latin letter, no `"` or `\`, no banned or scary term, AR != EN. GREEN writes the AR values by decoding these escapes in Python (never typed through a heredoc) and re-hashes them.

VERSION: expo.version = "1.0.1". runtimeVersion stays { policy: "appVersion" } (so the 1.0.1 binary's runtime is "1.0.1").

### 2.3 Failure table (what goes wrong, what catches it)
| failure | effect | caught by |
|---|---|---|
| EN app.json and en.json differ by a byte | the Info.plist (plugin) string and the en.lproj string disagree; iOS shows the .lproj one for English, so a drifted plugin string ships in no-lproj fallbacks | R5, w37 u10 |
| a provider name survives in any of the six strings | App Review sees a provider the consent sheet may not name the same way | R1-R3 |
| AR loses the shadda-free rule or gains Latin | the InfoPlist.strings fence | u11, R6 |
| version 1.0.1 merged before the second production OTA is published | every later `eas update` from main targets runtime 1.0.1 and NO LONGER reaches 1.0.0 installs (R-NT1-4) | process gate G-ORDER (section 7), never a test |
| runtimeVersion policy changed with the bump | OTAs computed differently from the store binary | R8, w37 e1 |
| a plugin key, the privacy manifest, eas.json or package.json moves | native diff beyond the unit | P1-P6 |
| a "1.0.1" build cut from a commit without the consent v3 client | the binary's embedded sheet says the v2 copy while the strings say "our AI providers"; the first launch runs the embedded JS until an OTA for runtime 1.0.1 exists | owner step O3 (build commit checklist, 2.6) |

No server envelope moves: no backend file is touched (the contract freeze of PLAN_S80 section 0 is untouched by construction; no refusal path, no new key, no 503).

### 2.4 The identity invariant (replaces flag-OFF identity)
After GREEN, with canonical JSON = a recursive key-sorted JSON.stringify with no whitespace, hashed as UTF-8 (the Python twin json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False); measured at base by canon.py, the RED round re-measures the JS twin at base and must get the same hex):
- expo minus `version` minus plugins[expo-camera].cameraPermission minus plugins[expo-image-picker].photosPermission: caf4a65e155d5b0b4c94c60889dad6adcf75adcb37d8307c2a00201074311abe
- plugins minus the two keys: 5d26fd82e847...
- expo.ios.privacyManifests: b404a4ad821187207961453699630b7f1b515098f83c16eb7f638f6038220e47
- eas.json: d5be08d3481cea3d5dd48b31ec506121b469bed96028e375cb8967571bc6f7cc
- package.json: 3dc071e586adf4d560c48868fc42b7254b873762bf9c6d10a524b53e5cd0aaae
- locales/en.json minus the two keys: 976decc199a8...
- locales/ar.json minus the two keys: a71cf2018a06...
(Reference: the full expo object at base hashes 0e5d050fe692d8404392fa02627dddb650c89a763adcd03a3925ec40e5860ffb.)
Plus the gate check G-SCOPE: `git diff --name-only <base>..HEAD` lists exactly the files of section 3 (no app/, src/, SmartCompareApp/src/, migrations/, package*.json, eas.json, ios/, android/).

### 2.5 Test seams
None in product code. The RED file reads the JSON files from disk (fs + path from __dirname, as b3a / w37 do) and, for R9 / P8 only, executes the INSTALLED config plugins in memory with introspect: true (the w37 a6 / b3a r35 recipe: `require.resolve('expo-camera/app.plugin.js', { paths: [APP] })`, nothing written). Production values: the files themselves.

### 2.6 The runtime trap and the two-runtime procedure (R-NT1-4; Q4; PROPOSED, not run)
(a) THE MERGE GATE (G-ORDER): NT1a merges only after (1) the dated ledger line that the SECOND production OTA (consent v3, after the #378 merge and deploys) is published from main, and (2) the relay's dated word that no further 1.0.0 OTA is pending from main. Reason (measured in eas-cli 18.8.1, section 1.2): `eas update` reads expo.version from the checkout at publish time and has no runtime flag; from the NT1a merge on, every `eas update` from main publishes runtime-1.0.1 updates that no 1.0.0 install accepts.
(b) THE TWO-RUNTIME PROCEDURE while 1.0.0 installs remain (proposed for OTA_READINESS; the relay / owner run every step, names only):
1. At the NT1a merge, record in the ledger L100 = the first-parent parent of the NT1a merge commit (the last main whose app.json says 1.0.0).
2. A 1.0.0 hotfix OTA (JS-only, needed by 1.0.0 installs): cut a maintenance branch release/1.0.x from L100 (never from main), cherry-pick ONLY JS-only commits that are safe on the 1.0.0 binary (no native module, no app.json, no dependency change: the same OTA-eligibility table as OTA_READINESS), run `npm ls` (drift = `npm ci` first), then `eas update --branch production --message "<release/1.0.x sha>"` from that checkout. The runtime is derived from its app.json = 1.0.0, so only 1.0.0 installs take it. Check the message sha has no trailing asterisk.
3. A 1.0.1 OTA: from main (app.json 1.0.1), `eas update --branch production ...` -> runtime 1.0.1. One EAS branch carries both runtimes; each install takes the newest update of ITS runtime (the expo-updates model; the read-only check is `eas update:list --branch production --runtime-version 1.0.0` / `1.0.1`, a list command, the owner's).
4. `eas update:republish --group <id>` republishes an existing group with its ORIGINAL runtime (build/commands/update/republish.js: it copies the group's updates); it is the rollback lever for either runtime, never a way to retarget a group to another runtime.
5. Between the NT1a merge and the 1.0.1 release: no runtime-1.0.1 OTA while 1.0.1 is In Review (the reviewer's build would load it on its second launch: the reviewed bytes must be the embedded ones). After release, OTAs to runtime 1.0.1 follow the normal canary rules.
6. A 1.0.0 OTA stops being useful when the share of 1.0.0 sessions is negligible (Sentry release / the app-open events); retiring it is the owner's call together with APP_MIN_VERSION (Q5).
OTA_READINESS_2026-11-07.md must gain (the orchestrator files it in the state folder; not edited by this unit): a section "After NT1a (expo.version 1.0.1 on main)" with steps 1-6, the line "never `eas update` from main for a 1.0.0 fix", and the G-ORDER precondition.
(c) WHAT THE 1.0.1 BUILD COMMIT MUST CONTAIN (O3; the binary embeds the JS of its build commit): NT1a; S81-12 (#378) merged, so the embedded consent sheet is v3 (AI_CONSENT_VERSION 3, the copy naming Anthropic and OpenAI) and the strings point at a policy that names the providers; S81-08 / S81-11 / S81-11e / CL2 / SF1's client line (already on main); CL3 ONLY if its three owner steps are done (ENABLE_FEEDBACK_V2 ON first, per the session-91 notes); ENABLE_SURFACES_FIELD OFF on web for the whole review window (the 2.1(a) chips rule, PLAN_S81:109). It must NOT contain: any client unit whose backend precondition is unmet at build time (each unit's PR body names it); a NT1b native item (section 10); an uncommitted change (build from a clean main checkout, the asterisk rule).

## 3 CHANGE LIST (in the order GREEN applies it)
0. Byte copies (Python shutil.copyfile) of every file below into <notes>/green_copies/ with their sha256 (the 1.9 values are the base); the mutation lock rule applies to any later mutation run.
1. SmartCompareApp/app.json:5 `"version": "1.0.0"` -> `"version": "1.0.1"` (Edit; one line).
2. SmartCompareApp/app.json:220 cameraPermission -> NEW_CAM_EN; :228 photosPermission -> NEW_PHOTOS_EN (Edit; the token "OpenAI" -> "our AI providers" in each line; nothing else on the lines).
3. SmartCompareApp/locales/en.json:4-5 -> NEW_CAM_EN / NEW_PHOTOS_EN (Edit).
4. SmartCompareApp/locales/ar.json:4-5 -> NEW_CAM_AR / NEW_PHOTOS_AR (a Python write that replaces OPENAI_AR by AI_PROVIDERS_AR in exactly those two values on the decoded bytes and re-encodes with the file's CRLF; then sha-check each value against 2.2 and the whole file's other lines byte-identical).
5. E1: SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts:64-67 (comment -> "S79 B3-A (PC2, GA1); NT1a (2026-11): the camera / photo-library purpose strings say where the photos go (MYEZ's servers and our AI providers, the v3 policy phrase); no provider is named."; the two literals -> NEW_CAM_EN / NEW_PHOTOS_EN).
6. E2: w37 e1 :1107 title -> 'e1 [CONSCIOUS PIN] runtimeVersion is { policy: "appVersion" } and expo.version is "1.0.1"'; :1130 -> toBe('1.0.1'); the comment :1108-1128 gains, in place of "Ahmed changes both this pin and app.json in the release commit AFTER the last OTA to the 1.0.0 fleet": "NT1a (2026-11) is that release commit: it merged only after the second production OTA to the 1.0.0 fleet (G-ORDER); a later 1.0.0 OTA is published from the release/1.0.x maintenance branch, never from main." (the rest of the comment unchanged).
7. E3: SmartCompareApp/__tests__/fixtures/b3a_copy.json:91-92 native.en -> the NEW EN pair; :95-96 native.ar -> the NEW AR pair (Python write on decoded bytes as in step 4; every other byte identical; the `_doc` string unchanged).
8. E4: SmartCompareApp/__tests__/b3a/nativeStrings.b3a.test.ts: :29 `const OPENAI_AR = ...` -> `const AI_PROVIDERS_AR = '<AI_PROVIDERS_AR as \u escapes>';` plus `const OPENAI_AR = '<the base escapes>';` kept for the negative assertion; r33 :95-97 the loop asserts `toContain('servers')`, `toContain('our AI providers')` and `not.toMatch(/openai|anthropic|claude|gpt/i)`; r34 :107-110 asserts `includes(AI_PROVIDERS_AR)` true, `includes(OPENAI_AR)` false, `includes(SERVERS_AR)` true. Titles unchanged (node ids stable). Pure ASCII kept in the added lines (\u escapes).
9. NEW RED file SmartCompareApp/__tests__/nt1/nativeStrings.nt1.test.ts (section 5; pure ASCII, \u escapes; LF in the index).
10. CLAUDE.md: the NT1a block (section 8) after the S81-04c block (before `## Tests`, one blank line before its heading) + the :341 pointer clause sentence in merge order (after S81-04c's, and after #378's if #378 merged first); CRLF kept.
No other file. In particular NOT: package.json, package-lock.json, eas.json, docs/privacy-data-inventory.md, src/**, App.tsx, landing/**, app/**, any snapshot.

## 4 EXISTING PINS

### 4.1 Pins that change deliberately (E-rows)
| E | file:line | before | after | reason |
|---|---|---|---|---|
| E1 | __tests__/config/nativeBundle.w37.test.ts:64-67 | CAMERA_PURPOSE / PHOTOS_PURPOSE = the OpenAI sentences | the NEW EN pair; comment re-dated | R-NT1-2; a5 / a6 / u10 keep their assertions, re-aimed at the new truth (a5's title says "unchanged": it means "unchanged by W3-7", left as is to keep the node id) |
| E2 | nativeBundle.w37.test.ts:1107 / :1108-1128 / :1130 | expo.version "1.0.0" | "1.0.1"; the comment records G-ORDER and the maintenance branch | R-NT1-3; this is the release commit the pin's own comment anticipates; the runtimeVersion half of e1 is unchanged |
| E3 | __tests__/fixtures/b3a_copy.json:91-92, :95-96 | the OpenAI EN / AR pairs | the NEW EN / AR pairs | R-NT1-2; r33 / r34 / r35 read their expected values from here |
| E4 | __tests__/b3a/nativeStrings.b3a.test.ts:29, :94-97, :107-110 | asserts the strings CONTAIN OpenAI / OPENAI_AR | asserts they contain "our AI providers" / AI_PROVIDERS_AR and NOT the provider; 'servers' / SERVERS_AR kept | re-aimed, strictly stronger (a provider-named string now fails) |
| E5 | CLAUDE.md (new block + :341 clause) | absent | section 8 | house rule; the CLAUDE.md readers join the comm set |

### 4.2 Pins that must stay green and unedited
w37 a1-a4, a3b, a7, a7b, a8 (microphone, RECORD_AUDIO), b1-b14, c1-c5 (manifest + inventory), d1, d2, d4, e1's runtimeVersion half, p1 (plugin order), p2 (updates.url, projectId), u1-u16 (u9 / u11 / u12 must pass ON the new AR strings), k1, k3, k6; the four drift nodes d5 / k2 / k4 / k5 stay red exactly as at base; b3a r35-r38; b3a/honestCopy.b3a; config/domain.s76 (D1-D4); clientTruth/privacyManifest.s74; brand/inAppMark.u4c B7; versionCompare.a9; appVersionService.a9; s11/launchSurfaces.s11; s11/categoryRow.s11; copy-policy.test.ts; the fourteen backend-scanning client fences; on the backend every test of section 1.5 / 1.10.

## 5 RED TESTS
File: SmartCompareApp/__tests__/nt1/nativeStrings.nt1.test.ts (the client RED rule of the common brief: __tests__/<unit>/*.<unit>.test.ts; the task text's tests/test_s81_<unit>.py template is for backend units and would duplicate jest pins in a second language: Q-O1). Hermetic: reads files only; R9 / P8 execute installed plugins in memory (introspect, nothing written). Every RED fails at base on an expect() assertion only (all values are read from existing files; no missing symbol, no import of a new module). Every PIN is green at base and after GREEN and runs with the FULL configuration (the real app.json / locales / eas.json / package.json on disk), so a mutant anywhere in those files is visible to it. Constants: NEW_CAM_EN, NEW_PHOTOS_EN (literals), NEW_CAM_AR / NEW_PHOTOS_AR as \u escapes plus their sha256, OPENAI_AR, AI_PROVIDERS_AR, SERVERS_AR = "\u062e\u0648\u0627\u062f\u0645", PROVIDER_EN = /openai|anthropic|claude|chatgpt|\bgpt\b/i, PROVIDER_AR = [OPENAI_AR, "\u0623\u0646\u062b\u0631\u0648\u0628\u064a\u0643" (Anthropic), "\u0643\u0644\u0648\u062f" (Claude), "\u0634\u0627\u062a \u062c\u064a \u0628\u064a \u062a\u064a" (ChatGPT)], the canonical hashes of 2.4, a `canon()` helper (recursive key sort, JSON.stringify, no spaces) and `sha()` (node crypto, UTF-8).

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | n01 no provider name in the app.json purpose strings | for cameraPermission and photosPermission: `{key, hit: PROVIDER_EN.test(v)}` equals `{key, hit: false}` | FAIL (OpenAI) | step 2 |
| R2 | n02 no provider name in locales/en.json camera / photos | same over en.ios.NSCameraUsageDescription / NSPhotoLibraryUsageDescription | FAIL | step 3 |
| R3 | n03 no provider name in locales/ar.json camera / photos | for each value: PROVIDER_EN.test false AND every PROVIDER_AR token absent | FAIL (OPENAI_AR) | step 4 |
| R4 | n04 app.json carries the exact new EN strings | cameraPermission === NEW_CAM_EN; photosPermission === NEW_PHOTOS_EN | FAIL | step 2 |
| R5 | n05 EN strings byte-equal across app.json and locales/en.json | en camera === app.json cameraPermission === NEW_CAM_EN; en photos === photosPermission === NEW_PHOTOS_EN | FAIL (at base they are equal to each other but not to NEW_*) | steps 2-3 |
| R6 | n06 locales/ar.json carries the exact AR drafts | sha(ar camera) === cf0a067d...; sha(ar photos) === b0506c29...; and each === the decoded \u literal | FAIL | step 4 |
| R7 | n07 the AR strings name "our AI providers" and the servers, once each | split(AI_PROVIDERS_AR).length - 1 === 1 and split(SERVERS_AR).length - 1 === 1 for both values | FAIL (AI_PROVIDERS_AR absent) | step 4 |
| R8 | n08 expo.version is 1.0.1 and the runtime still follows it | expo.version === '1.0.1'; runtimeVersion deep-equals { policy: 'appVersion' } | FAIL (1.0.0) | step 1 |
| R9 | n09 executed plugins write the new EN strings into Info.plist, both plugin orders | the b3a r35 recipe: plist.NSCameraUsageDescription === NEW_CAM_EN, NSPhotoLibraryUsageDescription === NEW_PHOTOS_EN for [camera, picker] and [picker, camera] | FAIL | step 2 (needs node_modules) |
| P1 | p01 the privacy manifest is byte-identical to base | sha(canon(expo.ios.privacyManifests)) === b404a4ad... | PASS | (no edit) |
| P2 | p02 every plugin option except the two purpose strings is identical to base | deep-copy plugins, delete the two keys, sha(canon) === 5d26fd82...; plus plugin names in order === the base list | PASS | (no edit) |
| P3 | p03 the expo object differs from base only in version and the two strings | deep-copy expo, delete version and the two keys, sha(canon) === caf4a65e... | PASS | (no edit) |
| P4 | p04 the locale files differ only in the two keys | sha(canon(en minus two keys)) === 976decc1...; ar === a71cf201...; key sets === the four keys under "ios" | PASS | (no edit) |
| P5 | p05 eas.json is identical to base | sha(canon(eas.json)) === d5be08d3...; appVersionSource 'remote'; production autoIncrement true and channel 'production' (named for the failure message) | PASS | (no edit) |
| P6 | p06 package.json is identical to base (no version or dependency move) | sha(canon(package.json)) === 3dc071e5...; version '1.0.0' | PASS | (no edit) |
| P7 | p07 microphone and display-name strings unchanged | MIC literal on both plugins and en.json; sha(ar mic) === 999e6f18...; en display 'MYEZ'; sha(ar display) === 5d3c4d53... | PASS | (no edit) |
| P8 | p08 Android still resolves no locale strings and requests CAMERA only through the OS | getResolvedLocalesAsync(APP, locales, 'android') deep-equals { en: {}, ar: {} }; android.permissions === ['android.permission.CAMERA'] | PASS (needs node_modules) | (no edit) |
Counts: 9 RED, 8 PIN. The R-NT1-5 rows map: provider-free (R1-R3), EN byte-equal (R5), both AR keys present (R6 / R7 / P4), version everywhere it is mirrored (R8; package.json is NOT a mirror, P6), manifest and other plugin blocks byte-identical (P1-P3). No tester scenario of eval_regression.json applies (a native-string unit; no compare path moves).

## 6 MUTATION TABLE (after GREEN, on byte copies of the GREEN files; each mutant one exact-string edit that matches once; run the killing rows by path with `jest -t`; restore from the copy; sha256-compare; the .qa-mutation.lock rule)
| M | file | mutation | killed by |
|---|---|---|---|
| M1 | app.json | cameraPermission "our AI providers" -> "OpenAI" | R1, R4, R5, R9, w37 a5 / a6 / u10, b3a r33 |
| M2 | app.json | photosPermission "our AI providers" -> "OpenAI" | R1, R4, R5, R9 |
| M3 | locales/en.json | camera "our AI providers" -> "OpenAI" | R2, R5, w37 u10 |
| M4 | locales/en.json | photos "our AI providers" -> "Anthropic" | R2, R5 |
| M5 | locales/ar.json | camera AI_PROVIDERS_AR -> OPENAI_AR | R3, R6, R7, b3a r34 |
| M6 | locales/ar.json | photos: first word of AI_PROVIDERS_AR re-gains the shadda (\u0645\u0632\u0648\u0651\u062f\u064a) | R6, R7, w37 u11 |
| M7 | locales/ar.json | camera: " Anthropic" inserted after AI_PROVIDERS_AR | R3, R6, w37 u11 (latin) |
| M8 | app.json | version "1.0.1" -> "1.0.0" | R8, w37 e1 |
| M9 | app.json | runtimeVersion policy "appVersion" -> "sdkVersion" | R8, P3, w37 e1 |
| M10 | app.json | expo-image-picker microphonePermission: "never recorded." -> "not recorded." | P2, P3, P7, b3a r38 |
| M11 | app.json | PhotosorVideos drops NSPrivacyCollectedDataTypePurposeOther | P1, P3, b3a r36, w37 c3 / c5 |
| M12 | app.json | expo-camera gains "barcodeScannerEnabled": false | P2, P3 |
| M13 | app.json | a trailing space inside cameraPermission only | R4, R5 |
| M14 | eas.json | production autoIncrement true -> false | P5 |
| M15 | package.json | "version": "1.0.0" -> "1.0.1" | P6 |
| M16 | locales/en.json | NSMicrophoneUsageDescription gains a word | P4, P7, w37 u10 |
Equivalent survivors: none expected; any survivor is reported for a ruling.

## 7 COMM SET AND GATES FOR GREEN (cheapest first)
G0 hygiene: `git diff --name-only` == section 3 exactly (G-SCOPE); bytes > 127 only in locales/ar.json and b3a_copy.json (both already UTF-8); no CRLF whole-file diff; JSON.parse of the three JSON files; the added-line sweep (no @gmail, +973, 8-digit run, key shape; the hash constants named without gitleaks keywords: CANON_SHA_*, never *_KEY / *_TOKEN); `git status --short -- '*.snap'` empty.
G1 the RED file at GREEN: 17 / 17 green (jest by path; the RED round records 9 failing / 8 passing at base).
G2 the touched / reader client suites by path, one jest (the node_modules junction the orchestrator creates; check node_modules/@babel/core and .bin/jest first): __tests__/nt1/nativeStrings.nt1.test.ts, __tests__/b3a/nativeStrings.b3a.test.ts, __tests__/b3a/honestCopy.b3a.test.tsx, __tests__/config/nativeBundle.w37.test.ts (failing node ids exactly d5, k2, k4, k5), __tests__/config/domain.s76.test.ts, __tests__/clientTruth/privacyManifest.s74.test.ts, __tests__/brand/inAppMark.u4c.test.ts, __tests__/versionCompare.a9.test.ts, __tests__/appVersionService.a9.test.ts, __tests__/s11/launchSurfaces.s11.test.ts, __tests__/s11/categoryRow.s11.test.tsx, __tests__/copy-policy.test.ts.
G3 the fourteen backend-scanning client fences by path (CLAUDE.md changes): brand/inAppMark.u4c, clientTruth/medicalNote.s74.test.tsx, clientTruth/privacyManifest.s74, clientTruth/shareTruth.s74.test.tsx, clipboardFallbackService(.test.ts + .edges.test.ts), config/nativeBundle.w37, DimensionBars.perCategory.test.tsx, honestCounts.s69.test.tsx, landing.domain.s76.test.ts, navigation/linking.w315.test.ts, onboarding/step05Trust.s69.test.tsx, playInstallReferrerService(.test.ts + .edges.test.ts), ResultsScreen.timeout.test.tsx.
G4 tsc (`node node_modules/typescript/bin/tsc --noEmit`) and eslint on the two edited .ts test files + the RED file.
G5 backend comm set through pyt.py (base and head, chunks <= 25 files, bound 1200, `comm -13` of the sorted FAILED sets EMPTY): (a) the SmartCompareApp-scanning backend tests: tests/test_arabic_verdict_output_w414.py, test_b2_strict_optional_auth.py, test_ci_gates.py, test_comparison_id_echo.py, test_consent_capture_w3_16.py, test_dimension_label_catalog_parity_w414.py, test_events_allowlist_superset.py, test_feature_bucket_parity.py, test_feedback_allowlist_superset.py, test_landing_fallback_pages_s69.py, test_legal_disclosure_s77.py, test_legal_docs_u8.py, test_legal_docs_u8_d3c.py, test_legal_docs_u8_polish.py, test_legal_s78.py, test_migration_037_security_definer_grants.py, test_paid_route_metering.py, test_register_benefits_parity_s69.py, test_review_paraphrase.py, test_s81_sf1_gate_rows.py, test_s81_sf1_surfaces_be.py, test_secret_scan_static.py, test_security_regression.py, test_text_error_envelope_no_raw_exception.py, test_timeout_partial_integration.py; (b) the processors.json readers not already listed: test_s79_b3b_apple_revoke.py, test_s81_s06_anthropic_router.py, test_s81_s22b_self_critique_retire.py; (c) the CLAUDE.md readers by the import graph: test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py; (d) the named source-scanning pins: test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command*.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py; MINUS the four test_precommit_hook*.py files (the unit edits no .githooks). No app/ module is edited, so the module / symbol reference grep adds nothing beyond (a)-(d). 12 of these files are green at base in this run (1.10); the rest are measured at RED / GREEN and the base record stored per LC-6 at 6b909e0a.
G6 FINAL ROUND ONLY (LC-7): the FULL jest suite once (`timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci`): 411 + 1 suites; failing node ids exactly the four drift nodes.
G-ORDER (process, before the merge, not a test): the dated ledger line of the second production OTA + the relay's no-pending-1.0.0-OTA word (2.6 a); the #378 merge freeze respected.

## 8 CLAUDE.md BLOCK (after the S81-04c block, before `## Tests`) and OWNER STEPS (names only)
Block text (ASCII; GREEN types it with the Edit tool, CRLF kept):
"**SESSION 81 native unit (NT1a NATIVE-1.0.1-P0, 2026-11; NO flag: a native config change that reaches users only in a NEW binary, never by OTA; spec `.qa-s80/NT1_UNIT_SPEC.md`):** `SmartCompareApp/app.json` `expo.version` is 1.0.1 and the expo-camera `cameraPermission` / expo-image-picker `photosPermission` purpose strings (mirrored in `locales/en.json`, Arabic twins in `locales/ar.json`, [NATIVE READ]) say photos are sent to MYEZ's servers and 'our AI providers' (the v3 policy phrase) and name no provider; the consent sheet v3 and the privacy policy name the providers. Build 1.0.0 (3) keeps its OpenAI strings until 1.0.1 is released. **Runtime rule:** with `runtimeVersion.policy: appVersion`, every `eas update` from main targets runtime 1.0.1 from this merge on and no longer reaches 1.0.0 installs; a 1.0.0 OTA is published only from the `release/1.0.x` maintenance branch cut at the last 1.0.0 main sha (recorded in the ledger at the merge). The merge waited for the second production OTA (G-ORDER). Pins: `__tests__/nt1/nativeStrings.nt1.test.ts` (R1-R9, P1-P8) + the re-aimed w37 a5 / a6 / u10 / e1 and b3a r33 / r34. NT1b (expo-image, Cairo via expo-font, Sentry 8.x, share plugins + card, Instagram Stories, Snapchat Creative Kit, Android minify, screenshots) is a later binary."
The :341 pointer clause gains "NT1a: expo.version 1.0.1 + provider-neutral purpose strings (native, binary only)." in merge order.
Owner steps (in order; nothing here is run by an agent):
- O1 [NATIVE READ] of NEW_CAM_AR / NEW_PHOTOS_AR (the shadda-free "our AI providers") before GREEN merges.
- O2 G-ORDER: the second production OTA published (dated ledger line) and no further 1.0.0 OTA pending from main; then the merge.
- O3 the 1.0.1 build from a clean main that contains NT1a + #378 (2.6 c): `npm ls` clean, `eas build --profile production --platform ios` (build number from the remote source, expected 4: `eas build:version:get` to read it), then `eas submit`.
- O4 the 1.0.1 App Store listing ("What's New") and the Notes for Review (draft below); the App Privacy label re-checked against the v3 policy (the PurposeOther meaning: Q-O4); the 2026-10-29 PLA acceptance (the memory record says it gates 1.0.1).
- O5 ENABLE_SURFACES_FIELD OFF on web through the review window; no runtime-1.0.1 OTA while In Review.
- O6 after release: the owner's device check (both prompts in EN and AR: delete and reinstall the app, and switch the iPhone language to Arabic for the AR pair), then ENABLE_ANTHROPIC_VISION (window 21) on its own yes; the CLAUDE.md:508 sentence rewritten in place on that dated line; APP_MIN_VERSION / APP_FORCE_UPDATE stay the owner's call 4.
Notes for Review draft (EN; the owner edits): "MYEZ 1.0.1 changes two permission texts. The camera and photo-library permission prompts now say that photos are uploaded to MYEZ's servers and sent to our AI providers to identify the products; they no longer name a single provider, because MYEZ now uses more than one. The providers are named, before any photo is sent, in the in-app AI permission sheet shown before the first comparison or scan (it names Anthropic and OpenAI and links the Privacy Policy), and in the Privacy Policy (section 4) at https://getmyez.com/privacy. No other permission, data type or feature changed in this build." (Append the demo-account lines of the 1.0.0 (3) notes unchanged.)

## 9 STATED LIMITS
- L1 The strings reach users only through the 1.0.1 binary; 1.0.0 (3) installs keep "sent to OpenAI" until they update the app (an OTA cannot change Info.plist). The camera stays broken for them while the OpenAI credential is dead (the incident); APP_MIN_VERSION is the only lever and it is the owner's.
- L2 The AR "our AI providers" omits the shadda the v3 legal AR text carries (the purpose-string fence forbids diacritics); the two spellings read the same, [NATIVE READ].
- L3 No on-device proof in the agent chain: Info.plist and InfoPlist.strings are proven by the executed-plugin rows (introspect) and the locale resolver, not by a built .ipa; the DONE criterion is the owner's phone (R-NT1-8).
- L4 The two-runtime procedure (2.6 b) is read from eas-cli 18.8.1's code and the expo-updates model; it was not executed (no publish by agents). Its first use should be checked with `eas update:list --runtime-version` on the owner's side.
- L5 The canonical-JSON PIN hashes were measured with Python; the RED round must reproduce them with the JS twin at base (a mismatch is a harness defect, fixed in the RED round, never by re-pinning to the GREEN bytes).
- L6 package.json "version" stays 1.0.0 (npm metadata), so `npm`-side tooling reports 1.0.0 for a 1.0.1 binary (cosmetic; Q-O2).
- L7 The privacy manifest's PurposeOther (documented as the OpenAI data-sharing programme in docs/privacy-data-inventory.md:46) stays byte-identical in 1.0.1 although S81-12 ends the programme; changing the manifest is out of this unit (Q-O4).

## 10 OUT OF SCOPE
- NT1b (follow-up id NT1b, a later binary; R-NT1-1): expo-image in ProductImage; Cairo embedded through the expo-font plugin with the runtime gate dropped; @sentry/react-native 8.10 (includeWebFeedback); react-native-share config plugin + react-native-view-shot share card; Instagram Stories (Meta app id); Snapchat Creative Kit (after Snap review); TikTok copy-link; Android minify / shrink; new screenshots; Notes for Review for the category narrowing and share targets; CL2b (the Geist drop). Each changes native dependencies and needs installs and device tests.
- Any JS / TS source (HomeScreen.tsx:820 and Step05Trust.tsx:13 / :23 comments), the consent sheet copy (S81-12), the legal texts and landing (S81-12), docs/privacy-data-inventory.md, the App Privacy label, APP_MIN_VERSION / APP_LATEST_VERSION / APP_FORCE_UPDATE, ENABLE_ANTHROPIC_VISION, OTA_READINESS edits (the orchestrator files 2.6 b), CLAUDE.md:508 (rewritten when 1.0.1 is live).
- Every package-manager command, `eas build`, `eas submit`, `eas update`, the store listing.

## 11 OPEN QUESTIONS FOR THE ORCHESTRATOR
- Q-O1 RED file location: the client rule (__tests__/nt1/*.nt1.test.ts, chosen: the pins it sits beside are jest and R9 / P8 need the installed plugins) vs the task template's tests/test_s81_nt1.py (a python twin of R1-R8 / P1-P7 could run at the spec stage without a junction and in backend CI; it would duplicate the jest rows). Recommendation: jest only.
- Q-O2 package.json "version": keep 1.0.0 (recommended: R-NT1-6, no lock edit, Expo never reads it) or move it with the lock root in the same commit (a dependency-file edit).
- Q-O3 R-NT1-1 THE SPLIT is the owner's call through the relay; this spec assumes the split is granted. If the owner refuses it, NT1 re-specs as one unit and none of the NT1b items fit this spec's invariant (P2 / P3 / P6 would all move).
- Q-O4 The privacy manifest PurposeOther (L7) and the App Privacy label after the OpenAI programme ends: keep for 1.0.1 (byte-identical, this spec) or a separate native-config unit before the 1.0.1 build (it would change the store label and needs the owner's ASC edit in the same window).
- Q-O5 The AR draft: the shadda-free v3 phrase (chosen) or a shorter "\u0645\u0632\u0648\u062f\u064a \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a" without "\u0644\u062f\u064a\u0646\u0627"; [NATIVE READ] decides.
- Q-O6 The maintenance-branch name and who records L100 in the ledger (the relay, at the merge).
- Q-O7 Whether the CLAUDE.md block should wait until 1.0.1 is released (then only the merge facts are true at merge time; chosen: write it at merge, it states the runtime rule which is true from the merge on).

Not done in this spec: no jest run (by the brief); no RED file written; no edit to any tracked file; no mutation run; no eas / npm / network call; the Expo docs for SDK 54 were not fetched (the runtime behaviour is read from the installed eas-cli code); the full backend comm-set base record (G5) beyond the 12 files of 1.10.
