# S79 B3-A client unit spec (measured)

- Unit: B3-A (client, one PR, ships in the build-3 binary 1.0.0 (3)). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s79-b3client`, branch `feature/s79-b3-client`, base main `b965c63b` (`git status --short` empty at the start and after every measurement; `.qa-s79/` is gitignored by `.gitignore:72` `.qa-*/`).
- Inputs: `<scratchpad>/b3/audit_findings_for_b3.json` (findings L1-05, L1-06, L1-07, L1-08, L3-01, L3-07, L3-08, L5-01, L5-02, L5-08, L5-09, L5-10, L5-13, L5-15, P1, P6, P7, P9; pointers were taken at build-2 commit `eed0f628` and are RE-MEASURED below at `b965c63b`), `<scratchpad>/audit/ASC_FACTS_2026-10-17.md`, house format `sc-docs-70/docs/investigations/2026-10-14-session-78-state/specs/S78_LEGAL_UNIT_SPEC.md` + `RULINGS_S78_TG_SM_SPEC_REVIEW.md`.
- Relayed user request (the only user voice): "Yes I agree do the 5 steps too. And improve the design too of the screen look at cal AI and use a more attractive font for Arabic". The computed B3-A task does not cover the design / Arabic-font part; it is recorded as open questions Q1-Q2 (section 12), not built here.
- Personal-data rule: this file carries no home address, house / block / road number, phone number or personal email.
- Companion file: `.qa-s79/B3A_JEST_SUBSET_BASE.txt` (the 163 existing jest suites the unit touches, with their base status).
- Every line number below is at `b965c63b`. Every file the unit edits is CRLF in the working copy and LF in the index (`git ls-files --eol`: `i/lf w/crlf` for app.json, locales/en.json, locales/ar.json, src/i18n/en.json, src/i18n/ar.json, HomeScreen.tsx, authService.ts, docs/privacy-data-inventory.md); the Edit tool keeps CRLF; a whole-file diff in `git diff --stat` is a defect.

## 0. What the unit does (one paragraph)

Removes the screen-capture block from the four auth screens (keeps `secureTextEntry` and the dependency); gives the Home (and ScanCamera) camera pad an honest denied state with an Open Settings button and a re-check on return; makes the onboarding language step survive its own RTL reload by persisting the step and answers right before `Updates.reloadAsync()` and resuming at the step after the language step; replaces six dishonest copy claims (offline save, BHD-for-everyone, 25+ retailers, credits, invented testimonials, raw server strings on the tailored-pick card) in EN + AR; rewrites the camera / photo-library purpose strings to say the photos go to MYEZ's servers and OpenAI and adds `PurposeOther` to five privacy-manifest entries to match the published App Privacy labels; replaces the typed "G" with the official Google logo, gives Google its own full-width row under Apple on Login and puts Apple first on Register, drops `offlineAccess`, signs out of Google on logout and revokes on deletion (best effort); sends Apple's `authorizationCode` as an OPTIONAL `authorization_code` on `/social-login` so unit B3-B can revoke Apple tokens on deletion.

## 1. Toolchain and environment (measured)

- `node --version` v24.11.1; `node node_modules/jest/bin/jest.js --version` 29.7.0; `node node_modules/typescript/bin/tsc --version` 5.9.3; `node node_modules/eslint/bin/eslint.js --version` v9.39.4 (all run by path from `SmartCompareApp/`).
- `SmartCompareApp/node_modules` is the junction to the shared clone install; `node_modules/@babel/core` and `node_modules/.bin/jest` exist.
- Junction drift vs `package-lock.json` (measured by reading each `package.json` `version` vs the lock): `expo-screen-capture` installed 8.0.9 / lock 8.0.10; `expo-updates` 29.0.17 / 29.0.20; `expo` 54.0.34 / 54.0.37; `expo-font` 14.0.11 / 14.0.12; `expo-localization` 17.0.8 / 17.0.9; `eslint-config-expo` 55.0.1 / ~10.0.x. Matching the lock: `expo-apple-authentication` 8.0.8, `@react-native-google-signin/google-signin` 16.1.2, `expo-camera` 17.0.10, `expo-image-picker` 17.0.11. Where a pinned behaviour matters and the junction drifts, the pinned copy was read in the sibling checkout `sc-s70-u4b/SmartCompareApp/node_modules` (read-only): expo-screen-capture 8.0.10 (`ios/ScreenCaptureModule.swift` sha256 `725a3479...`), expo-updates 29.0.20.
- The drift is the cause of the 4 base jest failures (section 2.9); EAS builds install from the lock, so the binary gets the lock versions.

## 2. Base state (measured at b965c63b)

### 2.1 Item 1: screen-capture block on the auth screens

- `src/screens/LoginScreen.tsx:46` import + `:194` `usePreventScreenCapture();`; `RegisterScreen.tsx:20` + `:40`; `ForgotPasswordScreen.tsx:20` + `:34`; `ResetPasswordScreen.tsx:30` + `:54`. No other `src/` or `App.tsx` file imports `expo-screen-capture` (grep).
- Pinned native behaviour (8.0.10, `ScreenCaptureModule.swift`): `preventScreenCapture` (l.43-53) calls `preventScreenRecording()` and `preventScreenshots()` and observes `UIScreen.capturedDidChangeNotification`; `preventScreenRecording()` (l.97-108) adds a full-screen black `blockView` (l.24-27) over `keyWindow.subviews.first` while `UIScreen.main.isCaptured`; `preventScreenshots()` (l.117-139) moves the window layer under a secure `UITextField` layer; `allowScreenCapture` (l.55-64) removes the block view (the 8.0.10 fix; the junction's 8.0.9 lacks it). JS wrapper `build/ScreenCapture.js:4,31-72`: `activeTags` set, native allow only when the set empties. So any screen recording of sign-in / sign-up shows black, which is what Apple's 2.1 request (a recording from launch covering registration, login, deletion) cannot accept.
- `secureTextEntry` occurrences (kept): Login 1, Register 2, Forgot 0, Reset 2.
- Dependency: `package.json:40` `"expo-screen-capture": "~8.0.10"`; lock `:7450-7452` 8.0.10; `__tests__/config/nativeBundle.w37.test.ts:1521-1527` `SDK54_TARGETS` pins `'expo-screen-capture': '8.0.10'` (test k2). Jest maps the module to `__mocks__/expo-screen-capture.ts` (`jest.config.js` moduleNameMapper).
- Decision: KEEP the dependency (no package.json / lock change). Reasons, measured: (a) dropping it would edit package.json and package-lock.json, which this unit may not touch, and would redden the w37 SDK-54 pin k2 (`SDK54_TARGETS`, :1525); (b) with no JS caller the native module is autolinked but inert: nothing calls `preventScreenCapture`, so no block view, no secure layer; (c) a later unit can drop it together with the w37 pin. Stated in limit L1.

### 2.2 Item 2: camera access denied

- `HomeScreen.tsx:42` `import { CameraView, useCameraPermissions } from 'expo-camera'`; `:112` `const [permission, requestPermission] = useCameraPermissions();`; `:709` `const cameraPermissionGranted = permission?.granted;`; `:729-735` `handleRequestCameraPermission` = `withAiConsent(() => { void requestPermission(); })`; `:736-740` gallery fallback through `withAiConsent`; `:758-778` the not-granted card: Camera icon, `home.permission.title`, `home.permission.body`, a `TouchableOpacity` (no testID) with `home.permission.cta`, and the gallery link `home.permission.gallery_link`. Styles `:1422-1460`. No `Linking`, no `canAskAgain` anywhere in `src/` (grep).
- `ScanCameraScreen.tsx:315-345`: the same pad (`testID="scan-camera-permission"`), CTA `scan-camera-permission-cta` `onPress={requestPermission}` (:326-337), gallery `scan-camera-permission-gallery`.
- Library (expo-camera 17.0.10 / expo-modules-core 3.0.30): `useCameraPermissions` returns `[PermissionResponse | null, request, get]` (`expo-camera/build/index.d.ts:24`); `PermissionResponse` has `status` ('granted' | 'undetermined' | 'denied', `PermissionsInterface.d.ts:9-13,26`), `granted`, `canAskAgain` (:40), `expires`. `src/PermissionsHook.ts:34-81`: `get` runs once on mount; there is NO AppState refresh, so the status is stale after a trip to Settings until the screen remounts or `get` is called.
- Catalog (`src/i18n/en.json`): `:713` `home.permission.title` "Snap to compare", `:714` body, `:715` `home.permission.cta` "Turn on camera", `:716` gallery link. AR twins at the same keys.
- `__mocks__/react-native.ts:136-141` `Linking` = `openURL`, `canOpenURL`, `getInitialURL`, `addEventListener`; NO `openSettings`.

### 2.3 Item 3: Arabic at onboarding step 2 reloads and restarts

- `Step02Language.tsx:26-31` `select(lang)`: `void switchLanguage(lang); onChange(lang);` (fire and forget).
- `hooks/useLanguage.ts:10-28`: returns early when `lang === i18n.language` (:11); `saveLanguage(lang)` (:13, AsyncStorage `@qaren_language`, `i18n/index.ts:15,27-29`); `i18n.changeLanguage` (:14); when `I18nManager.isRTL !== (lang === 'ar')` (:17): `allowRTL(true)`, `forceRTL(...)`, then `require('expo-updates').reloadAsync()` (:21-26, errors swallowed; no `__DEV__` guard, no loop flag).
- expo-updates 29.0.20 `build/Updates.js:168-178`: `reloadAsync(options)` throws `ERR_UPDATES_DISABLED` in `__DEV__`; accepts `options.reloadScreenOptions`.
- `i18n/rtlBootstrap.ts:29` `RTL_BOOTSTRAPPED_KEY = '@qaren_rtl_bootstrapped'`; `:42-65` boot path; after a `useLanguage` reload `I18nManager.isRTL` already equals the target, so `bootstrapRtl` returns at :45 (no second reload).
- `App.tsx:194-200` `init()`: `getSavedLanguage()` -> `i18n.changeLanguage` -> `bootstrapRtl`; `:371-378` mounts `<NewOnboardingHost onComplete=.../>` with no `initialStep` when `isAuthenticated && needsPreferences`.
- `NewOnboardingHost.tsx:73-156`: full mode replays a pending completion draft on mount (:93-104, `services/onboardingDraft.ts:53` key `@qaren_onboarding_draft_v1`, written only on completion); passes `isAuthenticated={true}` (:153) so the traversal is `AUTHED_STEP_SEQUENCE` = `[1..15, 17]` (`OnboardingFlow.tsx:130-132`; full sequence :127-129).
- `OnboardingFlow.tsx:196-206` step and answers live only in `useState` (`initialStep` default 1, `initialData`); `:261-275` `onboarding_started` is stamped with `initialStep`; `:293-311` advance by sequence index; step 2 is not in `STEPS_WITH_OWN_CTA` (:157-159), so the user still has to tap Continue after choosing a language, but the reload fires on the tap itself; `:541-544` the step-2 adapter `onChange={(lang) => setField('language', lang)}`.
- Answers given before the reload: step 1 has no input, so the only answer is `language`.
- AsyncStorage keys in use (grep of `src/`): `@qaren_language`, `@qaren_rtl_bootstrapped`, `@qaren_onboarding_draft_v1`, `@qaren_user`, `@qaren_recent_searches`, `@qaren_free_comparisons_used`, `@qaren_push_preprompt_answered`, `@qaren_push_token_registered`, `@qaren_ai_consent_<id>`, `qaren.demographicsPromptState.v1`, `qaren_device_id_v1`, `device_fp_nonce` (+ SecureStore `qaren_token`, `qaren_refresh_token`). `@qaren_onboarding_resume_v1` is free.
- Callers of `switchLanguage`: `Step02Language.tsx:29`, `OnboardingScreen.tsx:173` (legacy), `ProfileScreen.tsx:447,453`.
- Measured test constraints: `__tests__/App.bootGuard.b5.test.ts:36-131` evaluates the `init()` block text of App.tsx with a FIXED list of injected names, so any new identifier inside `init()` throws `ReferenceError` there and reddens the auth-path rows (:202-231): App.tsx `init()` must not change. `__tests__/screens/onboarding/NewOnboardingHost.test.tsx:52-53` and `NewOnboardingHost.draftRetry.test.tsx:148-154` query `onboarding-step-1` synchronously right after `render`: the host must still render step 1 synchronously when there is no settled resume record. `__tests__/screens/onboarding/Step02Language.test.tsx:41-55` asserts `switchLanguage` `toHaveBeenCalledWith('en')` / `('ar')` (ONE argument).

### 2.4 Item 4: dishonest copy (EN line / AR line)

| key | en.json | ar.json | rendered at | claim |
|---|---|---|---|---|
| `loading.tip.save_offline` | :287 "Save any comparison to revisit later — even offline." | :284 | default tip, `LoadingScreenVariants.tsx:176-180` (`DEFAULT_COMPARISON_TIP_KEYS`), every Home compare loader | no offline storage exists (only server History) |
| `results.tips.save_offline` | :752 (same text) | :749 | not rendered (no `results.tips` reference in `src/`) | same |
| `onboarding.s4.subtitle` | :551 "Currency, retailers, and peer cohort all calibrate to your region." | :548 | `Step04Country.tsx:89-94` (defaultValue repeats the EN text at :91-92) | prices are BHD for every country |
| `loading.stage.cross_checking` | :279 "Cross-checking 25+ retailers" | :276 | stage 2 of `DEFAULT_COMPARISON_STAGE_KEYS` (`LoadingScreenVariants.tsx:165-171`), ticks on a timer | fixed number; Results can say "Checked across 1 retail source." (en :183) |
| `loading.tip.cross_checks` | :285 "MYEZ cross-checks 25+ retailers — never just one." | :282 | default tip (:177) | same |
| `results.tips.retailers` | :749 (same as :285) | :746 | not rendered | same |
| `onboarding.s3.subtitle` | :544 "Side-by-side comparisons across 25+ retailers — picked for you." | :541 | `Step03ValueProp.tsx:36` | same "25+" |
| `auth.welcomeBackSub` | :1017 "Your advisor and credits are waiting." | :1014 | `LoginScreen.tsx:411-415` (defaultValue repeats the EN text at :413) | nothing is sold; ASC: no IAP |
| `onboarding.s1.subtitle` | :534 "Built for the GCC. By people like you." | :531 | `Step01Welcome.tsx:81` | frames the quotes as user testimonials |
| `onboarding.s1.quote_1..3` | :535-537 "Picked Galaxy — ...", "Picked La Roche — ...", "Picked Centrum — ..." | :532-534 | `Step01Welcome.tsx:84-104` as `QuoteRow` (documented as a "testimonial card", `components/primitives/QuoteRow.tsx:4`); defaultValues repeat EN at :88-102 | invented quotes |
| tailored-pick card | n/a | n/a | `components/HomeEditorialSections.tsx:93-112`: `(pick.category ?? '').toUpperCase()` (:100) and `pick.updated_at` verbatim (:105) | backend `app/api/home_routes.py:480-517` `_format_updated_at` returns fixed English "Just now", "Nm ago", "Nh ago", "Nd ago", "Older", "Recently"; `:603-604,669` raw `category`; no `created_at` in the payload (:655-680) |

- Existing catalog keys reused: `home.categories.*` (en :101-109, incl. `other`), `time.justNow` (:313), `time.minutesAgo_*` (:314-319), `time.hoursAgo_*` (:320-325), `time.daysAgo_*` (:326-331), `history.title` (:289, AR "السجل").
- Catalog shape: flat dotted keys; en 1005 keys, ar 1005 keys, key sets equal (measured).
- Not in the computed task but in the audit (L1-08 / L5-09): peer-learning claims en :631-633 ("Real people. Real buys. Real picks.", "Your peers refine it every time you compare."), :637 / :665 ("Trained by your peers."), :660, :751 ("47 cohort peers ..."), and "credits" in :339 `profile.month.bonus`, :680 `onboarding.s16.subtitle`. Recorded as Q4; not changed by this unit.

### 2.5 Item 5: purpose strings and privacy manifest

- `app.json:210-216` `expo-camera` plugin: `cameraPermission` (:213) "MYEZ needs camera access to photograph products for comparison.", `microphonePermission` (:214), `recordAudioAndroid: false`; `:218-223` `expo-image-picker`: `photosPermission` (:221) "MYEZ needs photo library access to identify products from your photos.", `microphonePermission` (:222). `app.json:16-19` `locales` -> `./locales/en.json`, `./locales/ar.json`; each holds exactly `ios.{CFBundleDisplayName, NSCameraUsageDescription, NSPhotoLibraryUsageDescription, NSMicrophoneUsageDescription}`.
- Info.plist keys the plugins emit (read: `expo-camera/plugin/build/withCamera.js:7-13`, `expo-image-picker/plugin/build/withImagePicker.js:24-32`, both `IOSConfig.Permissions.createPermissionsPlugin`, an undefined option keeps the existing value): `NSCameraUsageDescription` (camera plugin; image-picker passes none), `NSPhotoLibraryUsageDescription` (image-picker), `NSMicrophoneUsageDescription` (both). The `.lproj/InfoPlist.strings` come from `locales/*.json`.
- Pins on these strings: `nativeBundle.w37.test.ts:64-65` constants `CAMERA_PURPOSE` / `PHOTOS_PURPOSE`; `a5` (:199-204) plugin options; `a6` (:206-211) executed plugins' Info.plist; `u9` (:1370-1389) locale shape and no `"` / `\`; `u10` (:1391-1405) `locales/en.json` == plugin strings; `u11` (:1407-1441) `locales/ar.json`: Arabic present, NO Latin letters, no harakat / shadda except inside the brand «ميّز», no banned / scary AR terms, differs from EN. So "OpenAI" must be written in Arabic script in `locales/ar.json`.
- Privacy manifest `app.json:25-142` `ios.privacyManifests`: 13 collected types, all linked, none tracking. Purposes at base vs the published App Privacy (ASC facts line 24):

| type | app.json lines | manifest purposes at base | published label purposes | gap |
|---|---|---|---|---|
| PhotosorVideos | :41-44 | AppFunctionality | App Functionality, Other Purposes | + Other |
| OtherUserContent | :47-53 | AppFunctionality, Analytics | Other Purposes, Analytics, App Functionality | + Other |
| SearchHistory | :56-63 | AppFunctionality, Analytics, ProductPersonalization | Other Purposes, App Functionality, Product Personalization, Analytics | + Other |
| ProductInteraction | :81-87 | Analytics, ProductPersonalization | Product Personalization, Analytics, Other Purposes | + Other |
| OtherDataTypes | :111-117 | ProductPersonalization, AppFunctionality | Product Personalization, App Functionality, Other Purposes | + Other |
| the other 8 | | | consistent or not itemised in the ASC facts | none |

- So the binary's PrivacyInfo does NOT cover the published "Other Purposes"; the fix is a manifest edit (`NSPrivacyCollectedDataTypePurposeOther` on those five) mirrored in `docs/privacy-data-inventory.md` (table rows 3, 4, 5, 8, 12 at :33-42 and the first ```json fence at :83), because w37 `c3` (:676-686) deep-equals the fence with app.json and `c5` (:715-769) equals every numbered row with the fence (purpose cells must match `^[A-Z][A-Za-z]+$`, so `Other` is valid). Other pins are compatible: `:1474-1479` and `clientTruth/privacyManifest.s74.test.ts:33-51` use `toContain`; `:1462-1466` pins CustomerSupport exactly (unchanged).

### 2.6 Item 6: Google button, offlineAccess, sign-out / revoke

- `LoginScreen.tsx:113-123` `SocialGlyph`: Email = lucide `Mail`; Google = `<Text style={socialStyles.glyphGoogle}>G</Text>` (comment "placeholder"); `socialStyles` `:689-718`: `btn` `flex: 1, minHeight: 48` (:690-702), `label` `fontSize: 13, lineHeight: 13` (:706-711), `glyphGoogle` (:712-717). Layout `:407-460`: title, subtitle, `ConsentRow` (:418-424), Apple full-width row (:429-439, `AppleSignInButton` variant `continue`, testID `login-social-apple`), then ONE `socialRow` holding Google (`login-social-google`, label `auth.googleSignIn` = "Continue with Google", en :367) and Email (`login-social-email`) side by side (:442-458), OR divider, email fields.
- `RegisterScreen.tsx:402-446`: inputs ..., `ConsentRow` (:402-408), Create Account `Button` (:410-415), OR divider (:418-422), Google `Button variant="secondary"` with no logo and no testID (:424-430), then Apple `register-social-apple` variant `signUp` (:435-445), all below the four inputs.
- `onboarding/Step16Account.tsx:106-112` typed "G" too (Apple first at :159-167). Step 16 is never mounted in production (host passes `isAuthenticated={true}`), and its Apple / Google buttons only call `onSelectMethod`, which advances the flow (`OnboardingFlow.tsx:412-419`); no request is built there.
- `components/AppleSignInButton.tsx:26,53-76`: SDK native button, `width: '100%'`, `height: 48`.
- Official button `@react-native-google-signin/google-signin` 16.1.2: `GoogleSigninButton` (`lib/typescript/src/buttons/GoogleSigninButton.d.ts`) props `size` / `color` / `disabled` / `onPress`, NO label prop; native `RNGoogleSigninButton` via `codegenNativeComponent` deep import of `react-native/Libraries/Utilities/codegenNativeComponent` (`src/spec/SignInButtonNativeComponent.ts`); fixed sizes Standard 230x48, Wide 312x48 (`src/buttons/GoogleSigninButton.tsx:74-80`). Decision: do NOT use it. Measured reasons: (a) its label is the SDK's own (not "Continue with Google", not the app language, not right-to-left with the app), (b) six existing suites press Google by testID `login-social-google` and by the text `auth.googleSignIn` (`auth/appleButton.s69.test.tsx:237,311`, `AuthScreens.socialDiagnostic.pa8.test.tsx:154-254`, `AuthScreens.socialTimeout.a8.test.tsx:77-155`, `LoginScreen.consent.w3-16.test.tsx:85-165`, `RegisterScreen.consent.w3-16.test.tsx:176-241`, `AuthScreens.test.tsx:121`), (c) the deep react-native import is not transformed under this jest config (only `@react-navigation` .js is) and would need a new moduleNameMapper entry. Use the official Google "G" logo asset drawn with `react-native-svg` (`package.json:56` ^15.12.1, already in the binary; jest mock `__mocks__/react-native-svg.ts` renders `Svg` / `Path` hosts) inside the existing custom button; Google's sign-in branding guidelines allow a custom button that uses the standard logo and the label "Continue with Google" (stated from the published guidelines, not re-read in this session: the orchestrator or GREEN confirms it when downloading the asset).
- `services/authService.ts:22-31` `getGoogleSignin()` lazy `require` in try/catch; `:830-848` `configureGoogleSignIn` -> `gs.configure({ webClientId, iosClientId, offlineAccess: true })` (:844). `ConfigureParams.offlineAccess` (types.d.ts:24-29): "an authorization code is returned so the server can ... exchange for a refresh token". No `serverAuthCode` read anywhere in `src/` (grep); backend `app/api/auth_routes.py:297-305` `SocialLoginRequest` has no server-code field and nothing in `app/` reads one (grep `server_auth_code|serverAuthCode|authorization_code`: no hit). So `offlineAccess` is unused: drop it.
- No `signOut` / `revokeAccess` in `src/` (grep). Library (16.1.2, `GoogleSignin.d.ts:27-31`): `signInSilently()`, `signOut(): Promise<null>`, `revokeAccess(): Promise<null>`, `hasPreviousSignIn(): boolean`, `getCurrentUser()`. iOS (`ios/RNGoogleSignin.mm:175-192`): `signOut` calls `[GIDSignIn.sharedInstance signOut]` and resolves; `revokeAccess` calls `disconnectWithCompletion:` and rejects on an SDK error.
- `logout()` `authService.ts:272-345`: epoch bump, refresh-first preparation, `clearSession()`, `POST /api/v1/auth/logout`, `finally` clears the session and the onboarding draft (lazy import). Account deletion: `EditProfileScreen.tsx:127-161` -> `api.delete('/api/v1/auth/account')`, `clearAiConsent`, `clearRecentSearches`, `clearSession`, `onAccountDeleted`. Six suites mock `services/authService` with factories that lack any new export (`clientTruth/deviceData.s74.test.tsx:51`, `EditProfileScreen.bundleE.s3.integration.test.tsx:45`, `EditProfileScreen.deleteCopy.w314.test.tsx:55`, `HomeScreen.bundleE.s3.integration.test.tsx:69`, `ProfileScreen.bundleE.s3.integration.test.tsx:47`, `ProfileScreen.logoutCopy.b6.test.tsx:80`): a new authService export called from EditProfileScreen must be guarded (`typeof fn === 'function'`) and in its own try/catch, or those suites redden.

### 2.7 Item 7: Apple authorization code

- The ONLY builder of the Apple `/social-login` request is `authService.signInWithApple` (`:1022-1137`), called from `LoginScreen.tsx:272` and `RegisterScreen.tsx:155` (Step 16 builds none, section 2.6). Body today (:1094-1099): `{ provider: 'apple', id_token: idToken, nonce: rawNonce, ...(consent ?? {}) }`; `credential.authorizationCode` is never read.
- expo-apple-authentication 8.0.8 `build/AppleAuthentication.types.d.ts:110-151`: `identityToken: string | null` (:145), `authorizationCode: string | null` (:150).
- Backend at base: `SocialLoginRequest` (`auth_routes.py:297-305`) has no `model_config`; measured with the pinned venv (pydantic 2.13.4): a body with an extra `authorization_code` validates and the field is dropped (`model_config.get('extra')` is None, default ignore). So B3-A can ship before B3-B without a 422.
- Existing pins: `services/authService.consent.w3-16.test.ts:171-185` deep-equals the Apple body `{provider, id_token, nonce, terms_accepted, terms_version, age_attested}` with a credential mock `{ identityToken }` only (:116); `authService.socialFingerprint.w3-3.test.ts:121,233` and `services/authService.socialTimeout.a8.test.ts:107` mock the same shape.

### 2.8 Fences the new code and copy must respect (measured)

- `__tests__/consent/aiDispatchFence.s69.test.ts:216-232,279-281,300-325`: the inventory pins exactly ONE `camera-permission` reference in HomeScreen (gated, :309) and ONE in ScanCameraScreen (ungated, :318), i.e. references of the 2nd element of `useCameraPermissions()`. New code must add no reference to `requestPermission`; `Linking.openSettings` and the 3rd tuple element are not tracked.
- `__tests__/i18n/brand.myez.s69.test.ts`: `:144-157` the EN values carrying `MYEZ` are exactly the 27 brand keys; `:182` the count of the standalone AR brand word «ميّز» equals `BRAND_KEYS.length`; `:166-170` the count of the standalone AR verb «قارن» equals `VERB_KEYS.length`; `:209` every BRAND_KEY keeps the brand in EN and AR. So: new or changed values add no `MYEZ` / «ميّز» / standalone «قارن» (embedded forms like «مقارنة» are fine), and `loading.tip.cross_checks` + `results.tips.retailers` (BRAND_KEYS :67, :76) keep exactly one `MYEZ` and one «ميّز».
- `src/i18n/.copy-policy.json`: banned EN (Best Pick, Best Choice, Smart Pick, Winner, Excellent, Choose this, Get this, This is right, Beats, Why we picked this, We recommend, Best for), banned AR (5 patterns), scary EN `couldn't`, `try again`, `Failed to`; scary AR تعذر، فشل، تقدير، مُقدَّر; enforced by `__tests__/copy-policy.test.ts` over both catalogs.
- `__tests__/LoadingScreenVariants.wave2.test.tsx:58-73` pins the default stage keys and tip keys (incl. `loading.tip.save_offline`): keep the keys, change values only.
- `__tests__/screens/onboarding/Step01Welcome.test.tsx:39-49` pins testIDs `welcome-quote-1..3` and keys `onboarding.s1.quote_1..3`: keep both, change values only.

### 2.9 Base pass state (measured)

```
FULL jest (arbiter):  Test Suites: 1 failed, 3 skipped, 368 passed, 369 of 372 total
                      Tests: 4 failed, 13 skipped, 13 todo, 3603 passed, 3633 total; Snapshots: 42 passed, 42 total; Time: 88.875 s
                      [jest] tag=base-full start=2026-10-17 06:18:28 end=2026-10-17 06:20:12 rc=1
                      (timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci --json; log <scratchpad>/b3a/base_full_jest.{log,json})
  the 4 base failures, all in __tests__/config/nativeBundle.w37.test.ts, all junction drift (section 1), none touched by this unit:
    W3-7 (d) ... d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules   (installed: true)
    session 70 U4b ... k2 package-lock.json and node_modules resolve the five packages at or above those patches     (installed < lock)
    session 70 U4b ... k4 eslint-config-expo is on the SDK-54 line (~10.0.x) ...                                     (installed 55.0.1)
    session 70 U4b ... k5 offline expo-install consistency ...                                                        (eslint-config-expo 55.0.1)
  skipped suites at base: HomeScreen.redesign, HomeScreen.modeChipAnim, HomeScreen.scanCamera (describe.skip)
TOUCHED SUBSET (163 suites, .qa-s79/B3A_JEST_SUBSET_BASE.txt, from the same run): passed=1643 failed=4 (the same 4) skipped/todo=18
tsc:    node node_modules/typescript/bin/tsc --noEmit   [tsc] tag=base start=06:55:56 end=06:56:15 rc=0 (no output)
eslint: node node_modules/eslint/bin/eslint.js <the 16 src files of section 3 that exist at base + ResetPasswordScreen.w36.test.tsx + nativeBundle.w37.test.ts>
        [eslint] tag=base start=06:56:31 end=06:57:55 rc=0 -> 25 problems (0 errors, 25 warnings)
BACKEND comm set (25 files, section 8 gate 7), one chunk through the bounded runner:
  [pyt] tag=b3a-base-comm1 start=2026-10-17 06:34:49 end=2026-10-17 06:54:51 elapsed=1202s bound=1200s status=TIMEOUT rc=124
        (reached 80 % inside tests/test_precommit_hook_phase_b.py; every node before it passed: no F/E in the progress lines)
  re-run once, alone:
  [pyt] tag=b3a-base-comm1-rerun start=2026-10-17 06:58:07 end=2026-10-17 07:18:10 elapsed=1202s bound=1200s status=TIMEOUT rc=124 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\2dae842f-c924-40f1-bd05-6b610eed0f5f\scratchpad\b3a\base_comm1_rerun.log
  -> NOT MEASURED at base (two TIMEOUTs at the 1200 s chunk bound; both reached test_precommit_hook_phase_b.py with no F/E before it;
     progress marks counted in the two logs: 1680 and 1679 '.', 0 F, 0 E, 0 s / x / X; partial counts only, the files after the hook pair never ran).
     Orchestrator's call: split the two precommit-hook files into their own chunk (CLAUDE.md: 1200-1800 s per hook file column under load),
     the other 23 files as one chunk. The unit changes no backend file and no hook, so these two files cannot move; the 23 are the real comm set.
```

### 2.10 Line endings and diff hygiene

All edited files are CRLF in the working copy (section header). New files (tests, `GoogleGlyph.tsx`, `onboardingResume.ts`, the fixture) are written LF or CRLF consistently per file; `git diff --stat` must show content lines only for edited files.

## 3. Contract and change list (in the order GREEN applies it)

Before the first edit: byte-copy (Python `shutil.copyfile`) every file listed below to `<scratchpad>/b3a_green_before/` with its sha256; restore only from those copies, never `git checkout`.

### C1. Screen capture (item 1)
- Delete the `expo-screen-capture` import and the `usePreventScreenCapture()` call from LoginScreen (:46, :194), RegisterScreen (:20, :40), ForgotPasswordScreen (:20, :34), ResetPasswordScreen (:30, :54). Keep every `secureTextEntry`. No package.json, lock or `__mocks__/expo-screen-capture.ts` change (the mock stays for the w37 pin and any later caller).
- Pin change PC1 (section 5).

### C2. Camera denied state (item 2)
- Predicate `cameraDenied = permission?.status === 'denied' && permission?.canAskAgain === false` (strict: an object without `status`, as the existing suites mock, is NOT denied).
- HomeScreen: destructure the third element (`const [permission, requestPermission, getPermission] = useCameraPermissions();` keeps ONE reference to `requestPermission`). When `!cameraPermissionGranted && cameraDenied`, the card shows `home.permission.denied_title`, `home.permission.denied_body`, a button `testID="home-permission-open-settings"` labelled `home.permission.open_settings` whose `onPress` calls `Linking.openSettings()` (from `react-native`; NOT wrapped in `withAiConsent`; a rejection is swallowed), and the unchanged gallery link (still through `withAiConsent`). Otherwise the card is byte-for-byte today's (title / body / "Turn on camera" -> consent -> `requestPermission`). Give the existing CTA `testID="home-permission-cta"` (additive).
- While the denied card is shown, an `AppState` `change` listener calls `getPermission()` once per transition to `'active'` (guarded by `typeof getPermission === 'function'`: every existing HomeScreen suite mocks a TWO-element tuple) (so returning from Settings refreshes); the listener is removed when the card unmounts or the permission changes.
- ScanCameraScreen: the same predicate and keys on its pad; button `testID="scan-camera-permission-open-settings"` replaces `scan-camera-permission-cta` only in the denied state; the existing `onPress={requestPermission}` stays the single reference.
- `__mocks__/react-native.ts` `Linking` gains `openSettings: jest.fn(() => Promise.resolve())` (additive; GREEN).
- New keys (both catalogs): `home.permission.denied_title`, `home.permission.denied_body`, `home.permission.open_settings` (section 4).

### C3. Onboarding resume across the RTL reload (item 3)
- New `src/services/onboardingResume.ts`:
  - `export const ONBOARDING_RESUME_KEY = '@qaren_onboarding_resume_v1'`; `export const RESUME_TTL_MS = 10 * 60 * 1000`.
  - `saveOnboardingResume({ step, data }): Promise<void>` writes `JSON.stringify({ v: 1, step, data, saved_at: Date.now() })`; never rejects.
  - `loadOnboardingResume(): Promise<{ step: OnboardingStep; data: Partial<OnboardingFlowData> } | null>`: memoised per JS context (one promise); reads the key, ALWAYS removes it (single use, also when invalid), returns null unless: `v === 1`; `step` is an integer in `[3..15, 17]` (never 1, 2 or 16); `data.language` is `'en'` or `'ar'`; `0 <= Date.now() - saved_at <= RESUME_TTL_MS`; `data` keeps only keys of `OnboardingFlowData` with valid values (unknown keys dropped). Never rejects.
  - `peekOnboardingResume(): { settled: boolean; value: record | null }` (synchronous view of the memoised promise).
  - `clearOnboardingResume(): Promise<void>`; never rejects.
- Preload: `NewOnboardingHost.tsx` calls `void loadOnboardingResume()` at module top level (App.tsx imports it statically at :41, so the read is queued at bundle evaluation, before `init()`'s reads). App.tsx is NOT edited (section 2.3, App.bootGuard.b5). Measured: no suite that imports `NewOnboardingHost` or `App` asserts `AsyncStorage.getItem` / `removeItem` / `multiRemove` call counts (grep over `__tests__/` for `toHaveBeenCalledTimes`, `.not` and `.mock.calls` on those three: 0 files), so the import-time read moves no existing assertion.
- `useLanguage.switchLanguage(lang, opts?: { beforeReload?: () => Promise<void> | void })`: unchanged early return when `lang === i18n.language`; unchanged `saveLanguage` / `changeLanguage`; only on the reload path (`I18nManager.isRTL !== shouldBeRTL`), after `forceRTL` and BEFORE `Updates.reloadAsync()`, it awaits `opts.beforeReload()` inside try/catch, bounded at 1500 ms (a hung or rejecting hook never prevents the reload). Calls without `opts` behave exactly as today (Profile, legacy onboarding).
- `Step02Language` gains an optional prop `onBeforeReload?: (lang) => Promise<void>`. With the prop: `switchLanguage(lang, { beforeReload: () => onBeforeReload(lang) })`; without it: `switchLanguage(lang)` with ONE argument (the existing pin).
- `OnboardingFlow` step-2 adapter passes `onBeforeReload={(lang) => saveOnboardingResume({ step: <the entry after 2 in stepSequence>, data: { ...data, language: lang } })}` (= 3 in both sequences).
- `NewOnboardingHost` (mode `'full'` and no `initialStep` prop): `useState` initialiser takes `peekOnboardingResume()`; if settled with a record, mounts `OnboardingFlow` with `initialStep = record.step` and `initialData = { ...record.data, ...props.initialData }`; if settled with null, today's render; if not yet settled, renders today's step 1 and, when the promise resolves with a record, remounts the flow (`key` change) at the record's step. Edit mode never applies a record. `handleComplete` (full mode) calls `void clearOnboardingResume()`.
- Result: EN -> AR at step 2 = record `{step: 3, data: {language: 'ar'}}`, reload, the flow resumes at step 3 in RTL with Arabic selected on Back; AR -> EN symmetric; choosing the current language or a language whose direction already matches writes nothing and does not reload. The draft replay (`flushPendingOnboardingDraft`) is unchanged.

### C4. Honest copy (item 4)
- Catalog values per section 4 (EN + AR, key sets stay equal; 5 new keys in both).
- Drop or update the stale `defaultValue` literals: `Step04Country.tsx:91-92`, `LoginScreen.tsx:413`, `Step01Welcome.tsx:88-102` (each equals the new EN value or is removed).
- `Step01Welcome`: render `onboarding.s1.examples_label` (`testID="welcome-examples-label"`) directly above the three `QuoteRow`s; keep the three testIDs and keys.
- `HomeEditorialSections`: category pill text = `t('home.categories.' + category.trim().toLowerCase()).toUpperCase()` when that key exists and is not `other`; otherwise the pill is hidden (null-hide rule). Updated chip: map the server string: `/^Just now$/` -> `t('time.justNow')`; `/^(\d+)m ago$/` -> `t('time.minutesAgo', { count })`; `/^(\d+)h ago$/` -> `t('time.hoursAgo', { count })`; `/^(\d+)d ago$/` -> `t('time.daysAgo', { count })`; `Older` -> `t('home.smart_pick.updated_older')`; anything else (incl. `Recently`, ISO strings) -> chip hidden. No backend change (B3-B / later).

### C5. Purpose strings and manifest (item 5)
- `app.json` `cameraPermission` and `photosPermission` = the EN strings of section 4.2; `locales/en.json` the same two values; `locales/ar.json` the AR twins (Arabic script only, no diacritics except the brand, OpenAI written «أوبن إيه آي»). Microphone strings and display names unchanged.
- `app.json` privacy manifest: append `NSPrivacyCollectedDataTypePurposeOther` to PhotosorVideos, OtherUserContent, SearchHistory, ProductInteraction, OtherDataTypes; nothing else changes (tracking false, linked true, the four accessed-API entries).
- `docs/privacy-data-inventory.md`: add `Other` to the Purposes cell of rows 3, 4, 5, 8, 12 and the same purpose to the five entries of the ```json fence (keeps w37 c3 / c5 equal).
- Pin change PC2 (constants in w37).

### C6. Google button and Google session (item 6)
- New `src/components/GoogleGlyph.tsx`: `GoogleGlyph({ size = 18 })` = `Svg` `viewBox="0 0 48 48"` (`testID="google-glyph"`) with the four official "G" paths in the brand colours `#EA4335`, `#4285F4`, `#FBBC05`, `#34A853`, copied from Google's sign-in branding asset download (not redrawn; GREEN states the source URL in the file header). Reference path data (verify against the download): red `M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z`; blue `M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z`; yellow `M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z`; green `M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z`.
- LoginScreen: `SocialGlyph` google -> `<GoogleGlyph />`; order: ConsentRow, Apple row (unchanged), Google on its OWN full-width row (`width: '100%'`, `minHeight: 48`, same as Apple's 48), Email on its own full-width row below, OR, fields. Label style: no `lineHeight` below 1.2 x `fontSize` (drop `lineHeight: 13`), `fontSize` >= 15.
- RegisterScreen: mirror Login: ConsentRow, Apple (`register-social-apple`), Google (`testID="register-social-google"`, `GoogleGlyph`, label `auth.googleSignIn`), OR divider, then the inputs, invite code, Create Account, benefits. Consent still gates all three paths (W3-16 unchanged).
- Step16Account: `GoogleGlyph` instead of the typed "G" (:112).
- `configureGoogleSignIn`: remove `offlineAccess` (webClientId and iosClientId unchanged; the id token still needs `webClientId`).
- New exports in authService: `googleSignOutBestEffort(): Promise<void>` (if `getGoogleSignin()` exists and `hasPreviousSignIn?.()` is true, `await signOut()`; never rejects) and `revokeGoogleAccessBestEffort(boundMs = 3000): Promise<void>` (if `hasPreviousSignIn?.()` is true, `revokeAccess()` raced against `boundMs`; never rejects; missing functions on the module = no-op).
- `logout()`: `void googleSignOutBestEffort();` as the LAST statement of its `finally` (fire and forget; adds no await to the logout chain).
- `EditProfileScreen.handleDeleteAccount`: after `await clearSession();` and before `onAccountDeleted?.()`: `try { if (typeof revokeGoogleAccessBestEffort === 'function') void revokeGoogleAccessBestEffort(); } catch {}` (not awaited; a failed DELETE never reaches it).

### C7. Apple authorization code (item 7)
- `signInWithApple`: `const authorizationCode = typeof credential.authorizationCode === 'string' && credential.authorizationCode.length > 0 ? credential.authorizationCode : null;` body = `{ provider: 'apple', id_token: idToken, nonce: rawNonce, ...(authorizationCode ? { authorization_code: authorizationCode } : {}), ...(consent ?? {}) }`. Absent / null / empty / non-string -> the JSON is byte-identical to today's. Never logged (no console / Sentry argument contains it). Google path unchanged.
- Contract for B3-B: `POST /api/v1/auth/social-login` body gains OPTIONAL string `authorization_code`, sent only with `provider: 'apple'`; the backend at base ignores it (section 2.7).

## 4. Copy (EN + AR). Every AR string is marked [NATIVE READ] for the owner.

### 4.1 Catalog `src/i18n/en.json` / `ar.json`

| key | new EN | new AR [NATIVE READ] |
|---|---|---|
| `home.permission.denied_title` (new) | Camera access is off | الكاميرا غير مفعّلة لهذا التطبيق |
| `home.permission.denied_body` (new) | To snap products, allow camera access for this app in Settings. You can still pick two photos from your gallery. | لتصوير المنتجات، اسمح بالوصول إلى الكاميرا لهذا التطبيق من الإعدادات. ويمكنك اختيار صورتين من المعرض. |
| `home.permission.open_settings` (new) | Open Settings | افتح الإعدادات |
| `onboarding.s1.examples_label` (new) | Examples of what you can compare | أمثلة على ما يمكنك مقارنته |
| `home.smart_pick.updated_older` (new) | Over a week ago | منذ أكثر من أسبوع |
| `loading.tip.save_offline` | Every comparison you run is saved in History. | كل مقارنة تجريها تُحفظ في السجل. |
| `results.tips.save_offline` | Every comparison you run is saved in History. | كل مقارنة تجريها تُحفظ في السجل. |
| `onboarding.s4.subtitle` | Prices are shown in Bahraini Dinar (BHD) for now. Your country helps tailor the advice. | نعرض الأسعار حالياً بالدينار البحريني. ويساعدنا بلدك في تخصيص النصائح. |
| `loading.stage.cross_checking` | Checking retailers | نتحقق من المتاجر |
| `loading.tip.cross_checks` (BRAND_KEY) | MYEZ checks retailers across the GCC for each product. | ميّز يتحقق من متاجر في دول الخليج لكل منتج. |
| `results.tips.retailers` (BRAND_KEY) | MYEZ checks retailers across the GCC for each product. | ميّز يتحقق من متاجر في دول الخليج لكل منتج. |
| `onboarding.s3.subtitle` | Side-by-side comparisons with prices from GCC retailers. | مقارنات جنباً إلى جنب مع أسعار من متاجر الخليج. |
| `auth.welcomeBackSub` | Sign in to compare any two products. | سجّل الدخول لمقارنة أي منتجين. |
| `onboarding.s1.subtitle` | Built for shoppers in the GCC. | صُمم للمتسوقين في الخليج. |
| `onboarding.s1.quote_1` | Galaxy or iPhone? See where each one is stronger on camera and battery. | جالكسي أو آيفون؟ اعرف أين يتميز كل منهما في الكاميرا والبطارية. |
| `onboarding.s1.quote_2` | Two sunscreens? See which one suits sensitive skin. | واقيان من الشمس؟ اعرف أيهما يناسب البشرة الحساسة. |
| `onboarding.s1.quote_3` | Two multivitamins? See how their nutrients differ. | فيتامينان متعددان؟ اعرف الفرق بين مكوناتهما الغذائية. |

Checked against section 2.8 (mechanically: `<scratchpad>/b3a/check_copy.py` parses the 17 rows of 4.1 and the 2 rows of 4.2 out of this file and applies the copy-policy lists, the brand / verb word counts and the u9 / u11 rules: 0 issues): no banned or scary term (EN / AR); `MYEZ` and «ميّز» appear only in the two BRAND_KEYS, once each, as at base; no standalone «قارن» (only embedded «مقارنة», «مقارنته», «مقارنات», «لمقارنة»); «يتميز» is not the brand word (different letters). Note: the AR denied title is longer than the EN one on purpose (a bare «الكاميرا غير مفعّلة» reads as a device fault).

### 4.2 Native purpose strings (`app.json` plugin options = `locales/en.json`; `locales/ar.json`)

| key | EN (app.json + locales/en.json) | AR (locales/ar.json) [NATIVE READ] |
|---|---|---|
| NSCameraUsageDescription | MYEZ uses the camera to photograph the two products you want to compare. The photos are uploaded to MYEZ's servers and sent to OpenAI to identify the products. | يستخدم ميّز الكاميرا لتصوير المنتجين اللذين تريد المقارنة بينهما. ترفع الصور إلى خوادم ميّز وترسل إلى أوبن إيه آي للتعرف على المنتجات. |
| NSPhotoLibraryUsageDescription | MYEZ opens your photo library only for the photos you pick. Those photos are uploaded to MYEZ's servers and sent to OpenAI to identify the products. | يفتح ميّز مكتبة الصور فقط للصور التي تختارها. ترفع هذه الصور إلى خوادم ميّز وترسل إلى أوبن إيه آي للتعرف على المنتجات. |

AR checked against u11: Arabic letters present, no Latin letter, no harakat / shadda / sukun outside «ميّز», none of the banned or scary AR terms, differs from EN. EN checked against u9: no `"`, no `\` (the apostrophe is allowed). Neither string claims MYEZ does not store the photos (not measured here; the policy's wording is the owner's).

## 5. Existing pins

### 5.1 Pins that change (deliberately), one row each

| # | test (file:line) | asserts at base | new assertion | reason |
|---|---|---|---|---|
| PC1 | `__tests__/ResetPasswordScreen.w36.test.tsx:159-162` `arms the screen-capture guard on mount` (+ comment :34-36, import :83) | `usePreventScreenCapture` called on mount | rename to `does not block screen capture (B3-A)` and assert `expect(usePreventScreenCapture).not.toHaveBeenCalled()`; the `jest.mock('expo-screen-capture')` stays | item 1 |
| PC2 | `__tests__/config/nativeBundle.w37.test.ts:64-65` `CAMERA_PURPOSE` / `PHOTOS_PURPOSE` | the base EN strings (feeds a5 :199-204, a6 :206-211, u10 :1391-1405) | the section 4.2 EN strings; titles of a5 / a6 / u10 say "B3-A purpose strings" | item 5 |

No other existing assertion changes. `docs/privacy-data-inventory.md` is edited (C5) so that w37 c3 / c5 stay green; that is data, not a test change.

### 5.2 Pins that must stay green unchanged (each is in the touched subset)

`App.bootGuard.b5.test.ts` (App.tsx `init()` untouched), `screens/onboarding/Step02Language.test.tsx` (one-argument call), `screens/onboarding/NewOnboardingHost.test.tsx`, `NewOnboardingHost.draftRetry.test.tsx`, `NewOnboardingHost.editMode.test.tsx`, `screens/onboarding/OnboardingFlow*.test.tsx`, `rtlBootstrap.s69.test.tsx`, `consent/aiDispatchFence.s69.test.ts`, `consent/aiProcessingConsent.s69.test.tsx` (T1.13 / T1.14 with `{granted:false}`), `i18n/brand.myez.s69.test.ts`, `copy-policy.test.ts`, `LoadingScreenVariants.wave2.test.tsx`, `honestLoaders.u6.test.tsx`, `screens/onboarding/Step01Welcome.test.tsx`, `services/authService.consent.w3-16.test.ts` (10b Apple body), `authService.socialFingerprint.w3-3.test.ts`, `services/authService.socialTimeout.a8.test.ts`, `services/authService.b4.test.ts`, `authService.logoutRefreshFirst.w1-4d.test.ts`, the six auth-screen suites of section 2.6, `LoginScreen.noopControls.b9.test.tsx` (`login-social-email`), `EditProfileScreen.*`, `clientTruth/deviceData.s74.test.tsx`, `clientTruth/privacyManifest.s74.test.ts`, `config/nativeBundle.w37.test.ts` (all rows except the 4 drift nodes, which stay failing exactly as at base), `HomeEditorialSections.smartPickPrice.w311.test.tsx`, `SmartPickCard.imageUrl.test.tsx`.

## 6. RED tests

Seven new files under `SmartCompareApp/__tests__/b3a/` plus one fixture `SmartCompareApp/__tests__/fixtures/b3a_copy.json` (every EN / AR string of section 4, `encoding utf-8`; test sources stay ASCII, Arabic only in the fixture, failure messages escape non-ASCII). Every import of a module that does not exist at base (`onboardingResume`, `GoogleGlyph`) is a `require` inside the test body (or `jest.isolateModules`), so the PIN rows of the same file run green at base. Mocks follow the existing suites named in each row (copy their harness; no new shared mock is written by RED; `Linking.openSettings` is assigned inside the test: `(RN.Linking as any).openSettings = jest.fn(() => Promise.resolve())`). Hermetic: no network, no timers left running (`jest.useFakeTimers` only where a row says so).

| # | file / test | assertion | RED / PIN, reason at base |
|---|---|---|---|
| R1 | `authNoScreenCapture.b3a.test.tsx` `r1 the four auth screens neither import nor call expo-screen-capture` | for Login / Register / ForgotPassword / ResetPassword source (CRLF-normalised): no `from 'expo-screen-capture'`, no `usePreventScreenCapture(`, `preventScreenCaptureAsync(`, `enableAppSwitcherProtectionAsync(` | RED: imports at :46 / :20 / :20 / :30, calls at :194 / :40 / :34 / :54 |
| R2 | same `r2 no file under src/ or App.tsx imports expo-screen-capture` | glob `src/**/*.{ts,tsx}` + `App.tsx` | RED: the four files |
| R3 | same `r3 password fields keep secureTextEntry` | counts of `secureTextEntry` >= Login 1, Register 2, Reset 2 | PIN (green at base) |
| R4 | same `r4 the dependency stays` | `package.json` dependencies `expo-screen-capture` === `~8.0.10` | PIN |
| R5 | same file `r5 ResetPasswordScreen mounts without arming capture protection` | render with the w36 harness; `usePreventScreenCapture` mock not called | RED: called at :54 |
| R6 | `cameraDenied.b3a.test.tsx` `r6 denied + cannot ask again shows the Settings state` (harness of `consent/aiProcessingConsent.s69.test.tsx` `renderHome`, mock permission `{granted:false,status:'denied',canAskAgain:false}`, scan mode) | texts `EN['home.permission.denied_title']`, `EN['home.permission.denied_body']`, button `home-permission-open-settings` with `EN['home.permission.open_settings']`; `EN['home.permission.cta']` absent; gallery link present | RED: keys missing (`EN[...]` undefined) and the base card shows "Turn on camera" |
| R7 | same `r7 Open Settings opens Settings without consent or a permission request` | press -> `Linking.openSettings` called once; `requestPermission` mock 0 calls; consent sheet (`ai-consent-agree`) absent | RED: no button |
| R8 | same `r8 the gallery link in the denied state still goes through consent` | press `EN['home.permission.gallery_link']` -> consent sheet shown; `launchImageLibraryAsync` only after Agree | PIN |
| R9 | same `r9 not denied keeps today's card` | for `{granted:false}`, `{granted:false,status:'undetermined',canAskAgain:true}`, `{granted:false,status:'undetermined',canAskAgain:false}`, `{granted:false,status:'denied',canAskAgain:true}`: "Turn on camera" shown, no `home-permission-open-settings`; press -> sheet -> Agree -> `requestPermission` once | PIN |
| R10 | same `r10 returning to the app re-checks the permission` | mock tuple third element `getPermission`; in the denied state emit AppState `change` `'background'` then `'active'` (registry in `__mocks__/react-native.ts`) -> `getPermission` called once after `'active'`; not called while granted | RED: HomeScreen never calls it |
| R11 | same `r11 ScanCamera pad has the same denied state` (harness of `ScanCameraScreen.permission.test.tsx`, whose mock is `[{ granted: false }, mockRequestPermission]` at :25 and therefore stays on today's CTA) | denied mock -> `scan-camera-permission-open-settings` shown, press -> `openSettings`; `scan-camera-permission-cta` absent; not denied -> today's CTA | RED: no such testID |
| R12 | `onboardingResume.b3a.test.tsx` `r12 save then load returns the record once` | `saveOnboardingResume({step:3,data:{language:'ar'}})` -> stored JSON has `v:1`, `step:3`, `data.language:'ar'`, numeric `saved_at`; a fresh module (`jest.isolateModules`) `loadOnboardingResume()` -> `{step:3,data:{language:'ar'}}`; key removed; second load in a fresh module -> null | RED: module missing |
| R13 | same `r13 invalid records load as null and are removed` | each of: `saved_at` older than `RESUME_TTL_MS` (+1 ms), `saved_at` 61 s in the future, `v:2`, `step` 1 / 2 / 16 / 18 / 3.5, `language:'fr'`, malformed JSON -> null, key removed; unknown `data` keys dropped from a valid record | RED: module missing |
| R14 | same `r14 EN to AR: the hook runs beforeReload after forceRTL and before reloadAsync` (`renderHook(useLanguage)`; `jest.mock('expo-updates', () => ({ reloadAsync: jest.fn() }))`; i18n mock language `'en'`; `I18nManager.isRTL=false`) | `switchLanguage('ar', { beforeReload })` -> call order `setItem('@qaren_language')` < `forceRTL(true)` < `beforeReload` < `reloadAsync`; each once | RED: the hook ignores the 2nd argument (beforeReload 0 calls) |
| R15 | same `r15 AR to EN: the same order with forceRTL(false)` | i18n `'ar'`, `isRTL=true`, `switchLanguage('en', { beforeReload })` | RED: same |
| R16 | same `r16 no-reload paths call neither beforeReload nor reloadAsync` | (a) same language; (b) language differs but `I18nManager.isRTL` already equals the target; (c) `opts` omitted on a reload path -> `reloadAsync` once, nothing else new | PIN (base never calls beforeReload; (c) is today's behaviour) |
| R17 | same `r17 a failing beforeReload never blocks the reload` | `beforeReload` rejects -> `reloadAsync` once; `beforeReload` never settles (fake timers, advance 1500 ms) -> `reloadAsync` once | RED: beforeReload 0 calls |
| R18 | same `r18 Step02Language forwards beforeReload only when given onBeforeReload` | with prop: `switchLanguage` called with `('ar', { beforeReload: fn })` and `fn()` calls the prop with `'ar'`; without prop: called with exactly `('ar')` | RED: the prop is ignored |
| R19 | same `r19 OnboardingFlow writes the step after the language step` | render `OnboardingFlow` at `initialStep={2}` with `isAuthenticated` true and false (useLanguage mocked, capture opts); press `lang-ar`; invoke the captured `beforeReload` -> stored record `step:3`, `data.language:'ar'`; same for `lang-en` with `'en'` | RED: no opts |
| R20 | same `r20 the host resumes at step 3 with the language kept` | store a valid record, then `jest.isolateModules` require `NewOnboardingHost`, flush microtasks, render full mode -> `onboarding-progress` `data-current-step` 3; press `onboarding-back` -> step 2 with `lang-ar` `accessibilityState.selected` true; key removed | RED: base renders step 1 |
| R21 | same `r21 a late-settling preload remounts at the resumed step` | `AsyncStorage.getItem` for the key returns a deferred promise; first render shows `onboarding-step-1`; resolve with a valid record -> step 3 | RED |
| R22 | same `r22 stale record: step 1 and the key is removed` | record with `saved_at` = now - TTL - 1 -> `onboarding-step-1` synchronously; key absent afterwards | RED: base leaves the key |
| R23 | same `r23 no record: step 1 renders synchronously` | `render` then immediate `getByTestId('onboarding-step-1')` | PIN |
| R24 | same `r24 edit mode ignores a record` | record present, `mode='edit'` -> step 8 | PIN |
| R25 | same `r25 completing the flow clears the record` | full mode at step 17 (draftRetry harness), record stored after mount, press `s17-not-now` -> key absent | RED: nothing clears it |
| R26 | `honestCopy.b3a.test.tsx` `r26 changed values equal the fixture` | for the 12 changed keys of 4.1: `EN[k] === fx.en[k]` and `AR[k] === fx.ar[k]` | RED: base values |
| R27 | same `r27 new keys exist in both catalogs` | the 5 new keys present in EN and AR with the fixture values; key sets equal | RED: missing |
| R28 | same `r28 no dishonest claim remains in any EN / AR value` | no EN value matches `/25\+/`, `/even offline/i`, `/calibrate to your region/i`, `/credits are waiting/i`, `/people like you\.?$/i` on `onboarding.s1.subtitle`, `/^Picked /` on the quote keys; no AR value contains `25` next to «متجر» or «حتى بدون إنترنت» / «حتى دون إنترنت» | RED: en :279/:285/:544/:749, :287/:752, :551, :1017, :534-537 and AR twins |
| R29 | same `r29 stale defaultValues are gone` | static scan of `Step04Country.tsx`, `LoginScreen.tsx`, `Step01Welcome.tsx`: every `t('<changed key>', { defaultValue: '...' })` literal equals the new EN value (or there is none) | RED: :91-92, :413, :88-102 |
| R30 | same `r30 the welcome screen labels the quotes as examples` | `Step01Welcome` renders `welcome-examples-label` with `onboarding.s1.examples_label` before `welcome-quote-1` in tree order | RED: absent |
| R31 | same `r31 new and changed values respect the copy and brand fences` | for the 17 keys of 4.1: no copy-policy banned / scary hit (EN / AR); `MYEZ` only in the two BRAND_KEYS (once each), «ميّز» likewise; no standalone «قارن» (the brand test's `wordRe`) | PIN (the base values pass; guards GREEN's copy) |
| R32 | same `r32 the tailored-pick card shows localised labels` (harness of `HomeEditorialSections.smartPickPrice.w311.test.tsx`, but with an i18next instance initialised from the real `en.json` / `ar.json` as `clientTruth/copyTruth.s74.test.ts:40-60` does) | EN: category `electronics` -> pill `ELECTRONICS`; `other` and `gadgets` -> `home-smart-pick-category` absent; updated `Older` -> `Over a week ago`; `3d ago` -> `3d ago`; `Just now` -> `just now`; `Recently` -> `home-smart-pick-updated` absent. AR: `electronics` -> AR `home.categories.electronics`; `Older` -> fixture AR; `3d ago` -> AR `time.daysAgo` for count 3 | RED: base shows `OTHER`, `Older`, `Recently` raw |
| R33 | `nativeStrings.b3a.test.ts` `r33 plugin options carry the new purpose strings` | `expo-camera.cameraPermission` and `expo-image-picker.photosPermission` === fixture EN; each contains `servers` and `OpenAI` | RED: base strings |
| R34 | same `r34 locale files carry the new strings` | `locales/en.json` == plugin strings; `locales/ar.json` == fixture AR; AR contains «أوبن إيه آي» and «خوادم» | RED |
| R35 | same `r35 executed plugins write them into Info.plist` (compile helper of w37 a6, both plugin orders) | `NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription` === new EN | RED |
| R36 | same `r36 the five label types declare PurposeOther and nothing else moves` | PhotosorVideos, OtherUserContent, SearchHistory, ProductInteraction, OtherDataTypes purposes include `NSPrivacyCollectedDataTypePurposeOther`; the purposes of the other 8 types equal a frozen copy of the base values written in the test; `PurposeOther` appears on exactly 5 entries | RED: 0 entries |
| R37 | same `r37 the inventory doc lists Other for the same five rows` | rows 3, 4, 5, 8, 12 Purposes cells contain `Other`; the json fence equals app.json | RED |
| R38 | same `r38 microphone strings and display names unchanged` | MIC string EN / AR and `CFBundleDisplayName` EN / AR equal their base values (frozen in the test) | PIN |
| R39 | `googleButton.b3a.test.tsx` `r39 Login: Apple, then Google on its own full-width row, then Email` (harness of `auth/appleButton.s69.test.tsx`, `Platform.OS='ios'`, Apple available) | tree order `login-social-apple` < `login-social-google` < `login-social-email` < `login-email-input`; the parent View of `login-social-google` contains no other social button; flattened Google style has no `flex: 1` sharing a row and `minHeight >= 48` | RED: Google and Email share `socialRow` (:442-458) |
| R40 | same `r40 Google shows the official logo, not a typed G` | the `login-social-google` subtree has a `Svg` host (`google-glyph`) with 4 `Path` hosts whose `fill` set is {#EA4335,#4285F4,#FBBC05,#34A853}; no `Text` child equal to `G` | RED: `Text` "G" (:122) |
| R41 | same `r41 the Google label cannot be clipped by a fixed line height` | flattened label style: `lineHeight` absent or >= 1.2 x `fontSize`; `fontSize` >= 15 | RED: 13 / 13 (:706-711) |
| R42 | same `r42 Register: Apple first, then Google, then the form` | tree order `register-social-apple` < `register-social-google` < the first `TextInput` host; `register-social-google` contains `google-glyph` | RED: no testID; Google and Apple after the inputs |
| R43 | same `r43 Step16Account uses the logo` | `account-google` subtree has `google-glyph`, no `Text` "G" | RED: :112 |
| R44 | same `r44 configure no longer asks for offline access` (mock `@react-native-google-signin/google-signin` as `services/authService.b4.test.ts` does) | `configure` arg has no `offlineAccess: true`; `webClientId` and `iosClientId` equal the base literals (:834, :843) | RED: `offlineAccess: true` |
| R45 | same `r45 logout signs out of Google only when a Google session exists, without delaying logout` | `hasPreviousSignIn` true -> `signOut` once; false -> 0; `signOut` rejecting -> `logout()` resolves, server POST still sent once; `signOut` never settling -> `logout()` resolves and the POST is sent once | RED: never called |
| R46 | same `r46 revokeGoogleAccessBestEffort is bounded and fail-soft` | true -> `revokeAccess` once; rejecting -> resolves; never settling + fake timers 3000 ms -> resolves; false or module missing -> no call | RED: export missing |
| R47 | same `r47 account deletion revokes Google after the local clears` (EditProfileScreen harness of `EditProfileScreen.deleteCopy.w314.test.tsx`, authService mock WITH the new export) | successful DELETE -> `revokeGoogleAccessBestEffort` called once, after `clearSession`, before `onAccountDeleted`; DELETE rejecting -> not called; with the mock WITHOUT the export the flow still reaches `onAccountDeleted` | RED: not called |
| R48 | same `r48 Google request body unchanged` | `signInWithGoogle(consent)` body keys exactly `provider`, `id_token` + consent; no `authorization_code`, no `server_auth_code` | PIN |
| R49 | `appleAuthCode.b3a.test.ts` `r49 Apple sends the authorization code when present` (harness of `services/authService.consent.w3-16.test.ts`) | credential `{identityToken: T, authorizationCode: 'c_test_code'}` -> body `toEqual({provider:'apple', id_token:T, nonce:<string>, authorization_code:'c_test_code', ...CONSENT})` | RED: no field |
| R50 | same `r50 absent, null, empty or non-string code keeps today's bytes` | for `authorizationCode` undefined / null / '' / 42: the raw body string equals `JSON.stringify({provider:'apple', id_token:T, nonce, ...CONSENT})` (same key order) | PIN |
| R51 | same `r51 the code is never logged` | spy `console.log/warn/error` and the Sentry mock (`addBreadcrumb`, `captureMessage`, `captureException`) during r49: no argument (deep, stringified) contains `c_test_code` | PIN |

R3, R4, R8, R9, R16, R23, R24, R31, R38, R48, R50, R51 are PINs (green at base; marked so in their titles). Every other row is RED at base for the stated reason. The RED agent proves each reason by running the seven files at base (one jest process, by path, `--ci`) and pasting the per-node outcome, then proves satisfiability on a throwaway detached worktree (`git worktree add --detach <scratchpad>/b3a_proto b965c63b`; the node_modules junction must be recreated there with `cmd /c mklink /J` to the shared install and unlinked with `cmd /c rmdir` before `git worktree remove --force`), or reports the rows it could not prototype.

## 7. Mutation table (each mutant applied to GREEN's code on a byte copy; restore from the copy and sha-compare)

| # | mutant | killed by |
|---|---|---|
| M1 | re-add `usePreventScreenCapture()` to RegisterScreen only | R1, R2 |
| M2 | denied predicate `||` instead of `&&` | R9 |
| M3 | denied predicate drops the `status` check (`canAskAgain === false` alone) | R9 (the `undetermined` + `canAskAgain:false` case) |
| M4 | Open Settings via `Linking.openURL('app-settings:')` | R7 |
| M5 | Open Settings wrapped in `withAiConsent` | R7 |
| M6 | a second `requestPermission` reference in the denied branch | `aiDispatchFence.s69` inventory |
| M7 | AppState listener removed | R10 |
| M8 | `beforeReload` called after `reloadAsync` | R14, R15 |
| M9 | `beforeReload` called on the no-reload path | R16 |
| M10 | `beforeReload` awaited without bound / its rejection propagates | R17 |
| M11 | Step02 always passes the opts object | `Step02Language.test.tsx` (one-argument pin), R18 |
| M12 | resume step = 2 | R19, R20 |
| M13 | load does not remove the key | R12 (second load), R22 |
| M14 | TTL check removed | R13, R22 |
| M15 | step 16 accepted | R13 |
| M16 | host ignores a late-settling preload | R21 |
| M17 | `handleComplete` does not clear the record | R25 |
| M18 | edit mode applies a record | R24 |
| M19 | one AR changed value reverted | R26, R28 |
| M20 | `loading.tip.save_offline` removed from `DEFAULT_COMPARISON_TIP_KEYS` instead of reworded | `LoadingScreenVariants.wave2.test.tsx` |
| M21 | new AR value containing «ميّز» | `brand.myez.s69` :182, R31 |
| M22 | stale `defaultValue` left in Step04Country | R29 |
| M23 | pill shows `OTHER` for `other` | R32 |
| M24 | `Older` passed through | R32 |
| M25 | `PurposeOther` missing on ProductInteraction | R36 |
| M26 | inventory doc not updated | w37 c3 / c5, R37 |
| M27 | AR purpose string with Latin "OpenAI" | w37 u11 |
| M28 | Google back in a shared row with Email | R39 |
| M29 | typed "G" restored | R40 |
| M30 | `lineHeight: 13` restored | R41 |
| M31 | Register order Google before Apple | R42 |
| M32 | `offlineAccess: true` restored | R44 |
| M33 | `signOut` called without the `hasPreviousSignIn` check | R45 (false case) |
| M34 | `signOut` awaited inside `logout` before the server POST | R45 (the never-settling case) |
| M35 | revoke not bounded | R46 |
| M36 | revoke before DELETE | R47 |
| M37 | revoke call unguarded (no typeof / try) | R47 (mock without the export) and `EditProfileScreen.deleteCopy.w314` |
| M38 | `authorization_code: null` sent when the code is null | R50 |
| M39 | `authorization_code` added to the Google body | R48 |
| M40 | the code logged in the `__DEV__` diagnostic line | R51 |

## 8. Gates for GREEN (cheapest first; one process at a time; tools by path from `SmartCompareApp/` under `timeout`)

1. Toolchain: `node_modules/@babel/core` and `node_modules/.bin/jest` exist; print node / jest / tsc / eslint versions.
2. `timeout -k 15 600 node node_modules/typescript/bin/tsc --noEmit` -> rc 0 (base rc 0).
3. `timeout -k 15 600 node node_modules/eslint/bin/eslint.js` on every changed or new `.ts` / `.tsx` (the 16 src files: LoginScreen, RegisterScreen, ForgotPasswordScreen, ResetPasswordScreen, HomeScreen, ScanCameraScreen, onboarding/OnboardingFlow, onboarding/NewOnboardingHost, onboarding/Step02Language, onboarding/Step01Welcome, onboarding/Step04Country, onboarding/Step16Account, hooks/useLanguage, services/authService, EditProfileScreen, components/HomeEditorialSections; plus the new `services/onboardingResume.ts`, `components/GoogleGlyph.tsx`, the 7 new tests, `ResetPasswordScreen.w36.test.tsx`, `config/nativeBundle.w37.test.ts`, `__mocks__/react-native.ts`) -> 0 errors; no new warning in a changed file (base: 0 errors, 25 warnings over the 18 base files).
4. JSON: `JSON.parse` of `app.json`, `locales/en.json`, `locales/ar.json`, `src/i18n/en.json`, `src/i18n/ar.json`, the fixture; en / ar catalog key sets equal (1010 keys each).
5. Unit: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/b3a` -> all pass.
6. Touched subset: the 163 suites of `.qa-s79/B3A_JEST_SUBSET_BASE.txt` + `__tests__/b3a` in one run (bound 600) -> the failing node ids are exactly the 4 base w37 drift nodes (section 2.9).
7. Backend comm set (CLAUDE.md rule: every backend test that scans `SmartCompareApp/`; `grep -rl SmartCompareApp tests/` minus the two JSON fixtures = 25 files), one chunk through the bounded runner, bound 1200, base and head, `comm -13` of the sorted FAILED ids must be empty: `test_arabic_verdict_output_w414`, `test_b2_strict_optional_auth`, `test_ci_gates`, `test_comparison_id_echo`, `test_consent_capture_w3_16`, `test_dimension_label_catalog_parity_w414`, `test_events_allowlist_superset`, `test_feature_bucket_parity`, `test_feedback_allowlist_superset`, `test_landing_fallback_pages_s69`, `test_legal_disclosure_s77`, `test_legal_docs_u8`, `test_legal_docs_u8_d3c`, `test_legal_docs_u8_polish`, `test_legal_s78`, `test_migration_037_security_definer_grants`, `test_paid_route_metering`, `test_precommit_hook_phase_b`, `test_precommit_hook_phase_b_round2`, `test_register_benefits_parity_s69`, `test_review_paraphrase`, `test_secret_scan_static`, `test_security_regression`, `test_text_error_envelope_no_raw_exception`, `test_timeout_partial_integration`. No backend test reads `docs/privacy-data-inventory.md` (grep: only the client suites `config/nativeBundle.w37` and `clientTruth/privacyManifest.s74`), and the unit edits no `app/` file, so the backend source-scanning pins of `app/` cannot move. Of these, `test_dimension_label_catalog_parity_w414`, `test_register_benefits_parity_s69`, `test_arabic_verdict_output_w414` read the client catalogs and `test_consent_capture_w3_16` reads `consent.ts`; the rest scan paths. The chunk TIMED OUT at base once (section 2.9): if it times out at head too, split by the orchestrator's ruling (the precommit-hook pair alone), never by raising the bound.
8. FULL jest, the arbiter: `timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci` (no `-u`; `git status --short -- '*.snap'` empty) -> failing node ids exactly the 4 base drift nodes; suites 372 + 7 new.
9. Diff hygiene: `git diff --stat b965c63b` touches exactly: the 16 src files above, `__mocks__/react-native.ts`, `app.json`, `locales/en.json`, `locales/ar.json`, `src/i18n/en.json`, `src/i18n/ar.json`, `docs/privacy-data-inventory.md`, `__tests__/ResetPasswordScreen.w36.test.tsx`, `__tests__/config/nativeBundle.w37.test.ts`, plus the new files (`src/services/onboardingResume.ts`, `src/components/GoogleGlyph.tsx`, `__tests__/b3a/*` (7), `__tests__/fixtures/b3a_copy.json`); NO `package.json`, `package-lock.json`, `App.tsx`, `jest.config.js`, `.snap`, backend `app/` file; CRLF kept; personal-data sweep of the added lines (no address / phone / personal email pattern) and the `sk-` rule (`\bsk-[A-Za-z0-9_-]{20,}`) clean.

## 9. OTA vs binary

`runtimeVersion` policy `appVersion` (`app.json:265-267`) and version 1.0.0 (`:5`): build 2 and build 3 share runtime `1.0.0`, so any JS-only change could also reach build 2 by `eas update` (production branch) — but the standing rule is no OTA before approval; everything below ships in the build-3 binary.

| change | needs the binary | also OTA-capable after approval |
|---|---|---|
| C1 screen capture removed | no (JS) | yes |
| C2 camera denied state | no (JS; `Linking.openSettings` is core RN) | yes |
| C3 onboarding resume | no (JS; AsyncStorage + expo-updates already native) | yes |
| C4 copy + tailored-pick mapping | no (JS catalogs) | yes |
| C5 purpose strings (`app.json` plugins, `locales/*`) | YES (Info.plist + InfoPlist.strings are compiled into the binary) | no |
| C5 privacy manifest `PurposeOther` | YES (PrivacyInfo.xcprivacy is in the binary) | no |
| C5 inventory doc | no (repo doc) | n/a |
| C6 Google logo / layout / Register order | no (react-native-svg already native) | yes |
| C6 `offlineAccess` dropped, signOut / revoke | no (JS calls into the existing native module) | yes |
| C7 Apple `authorization_code` | no (JS) | yes (useful only once B3-B is live) |

## 10. Stated limits (true after the unit)

- L1 The `expo-screen-capture` native module stays linked (inert: no caller). Dropping it is a later unit with the w37 SDK pin.
- L2 Nothing here is device-verified: the black block view, the denied state after a real iOS denial, the RTL reload resume, the Google sign-out / revoke and Apple's code are measured from source and jest only. iOS terminates an app when a privacy permission is changed in Settings, so the AppState re-check (C2) mainly covers the "came back without changing" path (stated from platform knowledge, not measured here).
- L3 Google `revokeAccess` on iOS needs a restored current user; after a cold start without `signInSilently()` it may reject (`disconnectWithCompletion` error) and is then swallowed: revocation stays best effort. The backend has no Google revoke.
- L4 Apple token revocation needs B3-B (code exchange + `/auth/revoke` with a Sign in with Apple key the owner creates). B3-A only delivers the code at sign-in; an account created before build 3 has no stored code, so B3-B's deletion path must handle "no refresh token" (re-auth or skip).
- L5 The resume record holds only the language at step 2 (no other answers exist yet); it is not bound to a user id (TTL 10 min + single use + consumed at the next bundle load); a different account signing in within 10 minutes on the same device after a failed reload could inherit the language choice only.
- L6 The tailored-pick time chip is mapped from the server's English strings; a server wording change silently hides the chip (null-hide). The proper fix (codes or `created_at` from the backend) is server-side.
- L7 Copy: the AR strings are drafts for the owner's native read; the EN wording is the house voice, not legal advice.
- L8 The backend comm chunk timed out at base twice (section 2.9) and is NOT MEASURED at base; its base / head comparison needs the orchestrator's split ruling (the two precommit-hook files alone, the other 23 together).

## 11. Out of scope (recorded, not built)

- 13-17 age bucket: `onboarding/Step06Age.tsx:21` `AGE_GROUPS = ['18-24','25-34','35-44','45-54','55+']`, `types.ts:28-37` (cohort keys are exact and backend-validated).
- Dynamic Type clipping: `LoginScreen.tsx:656` CTA `height: 52`, `:732` fields `height: 48`, `:709` `lineHeight: 13` (fixed by C6 only for the Google label), no `maxFontSizeMultiplier` on Login (the consent sheet does it: `components/AiConsentSheet.tsx:81,96,111`).
- Hard-coded `paddingTop: 50`: `LoginScreen.tsx:557`, `PaywallScreen.tsx:189`, `components/results/ResultsContent.tsx:622`, `ResultsScreen.tsx:1062`, `onboarding/Step16Account.tsx:265` (follow-up: `useSafeAreaInsets().top` + spacing; `react-native-safe-area-context` ~5.6.0 is a dependency).
- Anything server-side (`home_routes` codes, Apple exchange / revoke = B3-B, policy text).
- The relayed user request's design pass ("look at Cal AI") and a new Arabic font (Q1, Q2).
- Peer-learning and other "credits" copy (Q4); `reloadScreenOptions` for a branded reload screen (Q5).

## 12. Open questions for the orchestrator

- Q1 (user request, relayed): "improve the design too of the screen look at cal AI". Which screen is meant is not stated in the request; the B3-A task has no design item. Proposed: a separate design unit (or a B3-A addendum) after the user names the screen; a design pass on auth / onboarding screens would collide with C2, C4 and C6 in the same files, so it should either land in B3-A before RED or after B3-A merges.
- Q2 (user request, relayed): "use a more attractive font for Arabic". Measured: the only Arabic face is Cairo (`@expo-google-fonts/cairo` ^0.4.2, `package.json:16`; `src/theme/fonts.ts:26-49` loads 400 / 600 / 700); no other `@expo-google-fonts/*` package is installed. A new face (candidates to show the owner: IBM Plex Sans Arabic, Tajawal, Almarai, Noto Kufi Arabic, Readex Pro) needs a package.json + lock change (outside this agent's rules) and touches the font tests (`jest.config.js` maps `@expo-google-fonts/cairo`); fonts loaded with `expo-font` from JS assets are OTA-capable, but a new npm package still has to be installed by the orchestrator. Decide: in B3-A (binary) or a follow-up OTA after approval.
- Q3 (user request, relayed): "do the 5 steps too" names no list in the task text; the orchestrator should map it (likely the owner steps of the session-79 plan) — nothing in this spec depends on it.
- Q4 Extend item 4 to the peer-learning claims (en :631-633, :637, :660, :665, :751) and the other "credits" strings (:339, :680)? Same honesty class (audit L1-08 / L5-09); proposed: yes, in this unit, same fences (they touch no BRAND_KEY except none; `onboarding.s12.title` is already pinned by `clientTruth/copyTruth.s74` CT-C3).
- Q5 Use `Updates.reloadAsync({ reloadScreenOptions: { backgroundColor, spinner } })` (29.0.20 `build/Updates.js:173-175`) in `useLanguage` so the reload shows a branded screen instead of a flash? JS-only, native support is in the build; not specified here.
- Q6 Login title "Welcome back." stays for first-time users (task names only the subtitle). Change to a brand-free "Welcome." / «أهلاً بك.»? (A title with "MYEZ" would break `brand.myez.s69` :144.)
- Q7 Bind the resume record to the user id (L5)? Needs the user id inside OnboardingFlow (not available today); proposed: no.
- Q8 ScanCamera denied state (C2, R11) is included because its CTA is equally dead (audit L3-07, `ScanCameraScreen.tsx:326-337`); drop it if the orchestrator wants Home only.
