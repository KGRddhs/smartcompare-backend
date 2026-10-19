# B3-A spec review (adversarial, 2026-10-17)

- **Spec:** `sc-s79-b3client/.qa-s79/B3A_CLIENT_UNIT_SPEC.md`, sha256 `ef9f86ce60c86fc9db1662292c1ccc5fe7955c30985fe898c65cd3bf85d188e1` (re-hashed at the start: match). Worktree HEAD `b965c63bd2a59be8ad9c3d5d2e1cccd5702c19d5`, `git status --short` empty before and after every measurement below.
- **Verdict: APPROVE_WITH_RULINGS.** One BLOCKING item (B1: the module-fresh test recipe of R12, R13, R20, R21, R22 and R24 cannot pass after a correct GREEN, measured by four jest probes). Everything else is a correction, a missing row or a ruling for the orchestrator.
- **Personal-data rule:** this file carries no home address, house / block / road number, phone number or personal email.
- **Relayed user request (the only user voice):** "Yes I agree do the 5 steps too. And improve the design too of the screen look at cal AI and use a more attractive font for Arabic". The spec records the design and font parts as Q1 / Q2. Q2's measured premise is wrong (section 1, C1); rulings RV4 / RV5 below.
- Every line number is at `b965c63b`. Every tool ran by path from `SmartCompareApp/` (jest 29.7.0, RNTL 13.3.3, node v24.11.1); pytest only through the bounded runner `pyt.py`.

## 0. Measurements taken for this review (pasted)

```
FULL jest at base (arbiter re-measure):
  Test Suites: 1 failed, 3 skipped, 368 passed, 369 of 372 total
  Tests:       4 failed, 13 skipped, 13 todo, 3603 passed, 3633 total
  Snapshots:   42 passed, 42 total
  [jest] tag=review-base-full start=2026-10-17 07:41:22 end=2026-10-17 07:41:41 rc=1
  failing nodes = nativeBundle.w37 d5, k2, k4, k5 (the spec's 4 drift nodes, identical)

BACKEND comm set at base, the 23 files (spec's 25 minus the two precommit-hook files):
  ========= 1846 passed, 4 deselected, 13 warnings in 76.50s (0:01:16) ==========
  [pyt] tag=b3a-rev-base-comm23 start=2026-10-17 07:47:36 end=2026-10-17 07:48:54 elapsed=78s bound=1200s status=OK rc=0
  (netguard lines only in tests/test_timeout_partial_integration.py: pre-existing baseline egress, blocked, no F/E)

CLAUDE.md source-scanning pins at base (test_model_config, test_model_config_enforced, test_prompt_fence,
test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability,
test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit):
  ======================= 350 passed, 1 warning in 36.80s =======================
  [pyt] tag=b3a-rev-base-srcpins start=2026-10-17 07:49:08 end=2026-10-17 07:49:47 elapsed=39s bound=600s status=OK rc=0

jest probes (gitignored dir SmartCompareApp/.qa-b3a-probe/, removed afterwards; copies in the reviewer's scratchpad b3a_review/probe_copy/):
  p1 component required inside jest.isolateModules, rendered with the OUTER RNTL
     -> threw "Cannot read properties of null (reading 'useState')"   (two React copies)
  p2 react + '@testing-library/react-native' (index) + component inside one isolateModules
     -> renders, but the test FAILS: "Hooks cannot be defined inside tests. Hook of type "afterAll" ..."
        (the RNTL index registers afterEach/beforeAll/afterAll at require time, build/index.js:21-43)
  p3 __DEV__ seen by app code under jest -> false   (__tests__/setup.ts:11)
  p4 react + '@testing-library/react-native/pure' + component inside one isolateModules
     -> rendered:hook-ok, PASS
  p5 AsyncStorage: outer setItem, then require the mock inside jest.isolateModules
     -> inner sees=null sameInstance=false   (a fresh, empty mock store per isolate)
  jest.isolateModulesAsync exists in this jest (jest-runtime 29.7.0 build/index.js:1091)
```

## 1. Refuted or corrected claims

| # | spec claim (section) | measured |
|---|---|---|
| C1 | Q2: "the only Arabic face is Cairo ... loads 400 / 600 / 700"; "a new face ... needs a package.json + lock change" | Cairo is LOADED (`src/theme/fonts.ts`, `useAppFonts` at `App.tsx:173`) but APPLIED NOWHERE: 0 references to `fontFamily.ar` or `Cairo_` outside `fonts.ts`; the typography tokens (`src/theme/index.ts:54-96`) carry no `fontFamily`; the only two `fontFamily` uses in `src/` are `Geist-Bold` on budget numerals (`BudgetPicker.tsx:110`, `Step09Budget.tsx:147`). Arabic (and almost all English) text renders in the iOS system font today. A new face needs NO npm package: the Geist precedent is local OFL TTFs in `assets/fonts/` loaded by `require` in `appFontMap` (`fonts.ts`) and embedded by the `expo-font` config plugin (`app.json:186-191`); jest maps `.ttf` to `__mocks__/fileStub.ts` (`jest.config.js:77`). Fonts loaded by `useFonts` from JS assets are OTA-capable; fonts listed in the `expo-font` plugin are binary. |
| C2 | C6 / 2.6: drop `offlineAccess` because it is unused (the P9 data-minimisation framing) | On iOS (the only shipped platform) the change is a NO-OP: 16.1.2 iOS `configure` builds `GIDConfiguration initWithClientID:clientId serverClientID:options[@"webClientId"]` unconditionally (`ios/RNGoogleSignin.mm:100`), and `offlineAccess` is read only by the JS guard (`src/signIn/GoogleSignin.ts:24`) and Android (`RNGoogleSigninModule.java:130`, `Utils.java:67`). The iOS sign-in keeps returning a `serverAuthCode` (`RNGoogleSignin.mm:249`). Dropping it is still correct hygiene; the spec must not present it as minimisation on iOS (ruling RV6). |
| C3 | Mutation table: "M40 the code logged in the `__DEV__` diagnostic line - killed by R51" | `__DEV__` is false in every suite (`__tests__/setup.ts:11`, probe p3), so `if (__DEV__) console.log('[APPLE-DIAG] ...')` (`authService.ts:1062`) never executes under jest; R51 as written cannot kill M40 (ruling RV2). |
| C4 | Section 6 recipes: R12 "a fresh module (`jest.isolateModules`) `loadOnboardingResume()` -> {step:3}"; R20 "store a valid record, then `jest.isolateModules` require `NewOnboardingHost`, flush microtasks, render"; R13 / R21 / R22 / R24 the same harness | Not satisfiable after a correct GREEN: a record stored through the outer registry is invisible to the isolate's fresh AsyncStorage mock (p5), a component required in an isolate cannot be rendered by the outer RNTL (p1), and requiring the RNTL index inside the isolate fails the test (p2). R24 is additionally VACUOUS as written: in the outer registry the host's import-time preload has already settled to null, so "edit mode ignores a record" holds whether or not edit mode would apply one (M18 survives). BLOCKING B1, ruling RV1. |
| C5 | 2.9 / L8: the backend comm chunk is "NOT MEASURED at base" | Measured: the 23 non-hook files pass in 78 s (1846 passed), and the 8 source-scanning pins pass in 39 s (350 passed); the two timeouts were the precommit-hook pair alone. The pair writes fixture paths `SmartCompareApp/...` into a temporary repo (`test_precommit_hook_phase_b.py:294,322,690`; `_round2.py:241,299,447`) and reads nothing of the real client tree, so this unit cannot move them (ruling RV3). |
| C6 | Section 8 gate 7: "one chunk through the bounded runner, bound 1200, base and head" over 25 files | Contradicts 2.9's own split and is the configuration that timed out twice. Superseded by RV3. |
| C7 | Section 8 gate 9 lists `docs/privacy-data-inventory.md` beside SmartCompareApp-relative paths | The file is at the REPO ROOT (`docs/privacy-data-inventory.md`; w37 reads it as `path.join(REPO, 'docs', 'privacy-data-inventory.md')` at `nativeBundle.w37.test.ts:610` and `:1174`); `SmartCompareApp/docs/` does not exist. R37 and gate 9 must use the repo-root path (RV13). |
| C8 | L3: "Google `revokeAccess` on iOS needs a restored current user; after a cold start without `signInSilently()` it may reject" | UNMEASURED either way: the native body is `[GIDSignIn.sharedInstance disconnectWithCompletion:]` (`RNGoogleSignin.mm:182-192`); whether the GoogleSignIn SDK falls back to the keychain auth state lives in the CocoaPod, which is not in `node_modules`. Keep it as an uncertainty, not a measured limit. |

Confirmed (re-measured, no change needed): every item-1 pointer (Login :46 / :194, Register :20 / :40, Forgot :20 / :34, Reset :30 / :54; `package.json:40`; junction 8.0.9 vs `sc-s70-u4b` 8.0.10; `ScreenCaptureModule.swift` sha256 `725a3479...`; `OnCreate` only sizes the block view, so the module is inert without a caller); Home `:112` / `:709` / `:731` / `:759-776`; iOS `canAskAgain = status != Denied` (`expo-modules-core/ios/Legacy/Services/Permissions/EXPermissionsService.m:142`) and camera `.restricted -> denied` (`expo-camera/ios/Common/CameraPermissionsRequester.swift:38`), so the predicate matches iOS exactly; `aiDispatchFence` tracks only `elements[1]` of `useCameraPermissions()` (`aiDispatchFence.s69.test.ts:216-232`); `Linking` mock without `openSettings`; the `AppState.__emit` registry (`__mocks__/react-native.ts:104-121`); `useLanguage`, `Step02Language`, `rtlBootstrap` lines; `App.tsx:41` static import, `:194-200` `init()`; `CANARY_NEW_ONBOARDING_PERCENT = 100` (`features.ts:30`), so the legacy `OnboardingScreen` path is dead; the copy table (en/ar 1005 keys each, sets equal); the tailored-pick sources (backend category vocabulary `cache_service.py:284` equals the `home.categories.*` keys); `app.json` plugin options `:211-223`, `updates.url` set (expo-updates enabled, so `reloadAsync` works in the release build); the 13 manifest entries and the 5 purpose gaps vs the ASC facts; `SocialLoginRequest` (`auth_routes.py:295-302`) has no `model_config` (the `:293` `extra: ignore` belongs to the class above); the 25-file comm list (`grep -rl SmartCompareApp tests/` = 27 minus the two JSON fixtures).

## 2. BLOCKING

- **B1 (R12, R13, R20, R21, R22, R24): the module-fresh harness.** As written these rows go red at base for the wrong reason (a hook crash or an empty store) and stay red after a correct GREEN. Fix by RV1 before RED.

## 3. Missing test rows (what a mutant or the reviewer's device flow survives today)

| id | row | why (mutant / flow it catches) |
|---|---|---|
| MR1 | R20b: host-level AR -> EN resume (record `{step:3, data:{language:'en'}}`, i18n mock 'en' after the reload) -> step 3, Back shows `lang-en` selected | the task requires both directions; R20 covers the host only for 'ar', R15 covers only the hook |
| MR2 | R1 / R2 widened: any `expo-screen-capture` substring in an `import ... from`, `require(`, dynamic `import(` or deep subpath (`expo-screen-capture/build/...`) over `src/**`, `App.tsx` AND the entry `index.ts`; plus render-level rows for Login, Register and ForgotPassword asserting the `usePreventScreenCapture` mock is not called (R5 covers Reset only) | a wrapper hook in `src/hooks/` importing a deep path, or a `require`, survives the exact-quote scan |
| MR3 | R3 at render level: the password `TextInput`s carry `secureTextEntry: true` (Login password field; Register x2; Reset x2) | R3 counts the word; `secureTextEntry={false}` (or `type === 'email'` at `LoginScreen.tsx:181`) survives |
| MR4 | R51 runs with `(globalThis as any).__DEV__ = true` (restored in `finally`) | C3: otherwise M40 survives |
| MR5 | R7b: `Linking.openSettings` rejecting -> no throw, no unhandled rejection, the card stays; R10b: after the permission turns granted (or unmount), `AppState.__emit('active')` calls `getPermission` 0 more times | C2 promises a swallowed rejection and a removed listener; no row pins either (a never-removed listener survives M7's row) |
| MR6 | R13b: TTL boundary: `now - saved_at === RESUME_TTL_MS` is valid, `+1 ms` invalid | a `<` vs `<=` mutant survives the +1 ms case alone |
| MR7 | R42b (Register, if RV9 is adopted): an unticked Create Account press brings the consent error into view (the ScrollView `scrollTo` called toward the consent row, or `consent-error` rendered adjacent to the Create Account button) | C6 moves `ConsentRow` above the Apple / Google rows while Create Account stays below the four inputs and the invite code; a blocked press then shows its error off-screen on a scrolled form: a "dead button" in the reviewer's sign-up flow (the L3-07 class) |
| MR8 | R45b: `googleSignOutBestEffort` also fires when `logout()` has no token or the server POST rejects (the `finally` path) | the spec's "LAST statement of its `finally`" has no row for the no-token branch |
| MR9 | R14 / R15 per-key order assertions (if RV7 is adopted): `setItem('@qaren_rtl_bootstrapped', 'rtl'|'ltr')` before `reloadAsync`, and every "once" assertion filtered by key | a blanket "setItem once" would go red on the extra key |
| MR10 | R28b: no AR value contains `25+` / `٢٥` next to «متجر» in Western OR Arabic-Indic digits | the AR regex as specified checks Western digits only |
| MR11 | R31b (if RV10 is adopted): the 17 new / changed AR values carry no harakat, shadda or tanween outside «ميّز» (the `[ً-ْٰ]` rule of `authErrorCopy.s69.test.ts:149`) | house rule for new AR copy since S69; today 7 of the 17 AR strings carry diacritics (C9 below) |

C9 (measured with `check_spec_copy.py` over the spec's own tables): 0 banned / scary hits, brand counts as the spec states; but 7 AR values carry diacritics: shadda in `home.permission.denied_title` («مفعّلة») and `auth.welcomeBackSub` («سجّل»), damma in `loading.tip.save_offline` / `results.tips.save_offline` («تُحفظ») and `onboarding.s1.subtitle` («صُمم»), tanween in `onboarding.s4.subtitle` («حالياً») and `onboarding.s3.subtitle` («جنباً»). No existing test breaks (182 of 1005 base AR values carry diacritics; the no-diacritics rules are key-scoped), so this is a ruling, not a blocker.

## 4. Flag-OFF / byte-identity check

- The unit is unflagged client code (RN has no per-call flag, the M23 precedent). The byte-identity obligations the house rules impose are the ones the spec states: (a) Apple body without a usable code is byte-identical (R50, PIN, key order included); (b) the Google body unchanged (R48); (c) `switchLanguage` without `opts` behaves exactly as today (R16c) and `Step02Language` without the prop calls `switchLanguage` with ONE argument (the existing pin `Step02Language.test.tsx:41-55`; jest's `toHaveBeenCalledWith` compares argument arrays by length, so `('ar', undefined)` would redden it); (d) the not-denied Home card is today's card (R9); (e) App.tsx `init()` untouched (bootGuard.b5). All five are pinned. Missing: none beyond MR1-MR11.
- Backend: no flag, no `app/` file, and the base comm set is now measured (section 0); the backend at base ignores `authorization_code` (pydantic default `extra = ignore`), so B3-A can ship before B3-B.

## 5. Comm set (CLAUDE.md rules)

- **SmartCompareApp-scanning rule:** the 25 files are right by the grep. Split as RV3: the 23 non-hook files (base 1846 passed, 78 s) + the 8 source-scanning pins (base 350 passed, 39 s), each one chunk; the precommit pair excluded with the measured reason (fixture path literals in a temp repo).
- **Source-scanning-pin rule:** B3-A edits no `app/` file (gate 9 proves it), so the pins are vacuous by construction; they cost 39 s, so run them anyway and close the rule literally.
- **Constraints the comm set imposes on GREEN that the spec does not state (all measured; RV12):**
  - `tests/test_security_regression.py:514-523`: every line of `authService.ts` that starts with `console.` must carry `__DEV__` on the SAME line; `:557-560`: the string `Web Client ID:` is banned in `authService.ts`; the file is read with the platform default encoding (`read_text()`), so new non-ASCII in `authService.ts` can fail it locally on Windows.
  - `tests/test_legal_docs_u8.py:779-785` (`CLIENT_PROBES`): the literal `@react-native-google-signin/google-signin` must stay in `src/services/authService.ts` (moving the Google helpers to a new module reddens T7).
  - `tests/test_legal_docs_u8_d3c.py:1035`: `t('editProfile.deleteAccount')` must stay in `EditProfileScreen.tsx`.
  - `tests/test_events_allowlist_superset.py`: no new `trackEvent('...')` / `fireEvent('...')` literal unless it is already in `feedback_routes.VALID_EVENT_TYPES` (B3-A cannot edit the backend).

## 6. App Review angle (would the change itself create a rejection risk?)

- **Screen capture removal:** removes the 2.1 recording blocker; no new risk. `secureTextEntry` stays (MR3 pins it at render level).
- **Camera denied state:** an Open Settings button after a denial is the accepted 5.1.1(iv) pattern. Existing risk the unit touches: the NOT-denied card is a custom pre-permission screen whose button says "Turn on camera" before the system prompt; App Review's 5.1.1 template rejects pre-prompts that "encourage or direct users to allow" access and asks for neutral words such as "Continue" / "Next" (RV11, owner's call; not introduced by B3-A).
- **Purpose strings:** accurate (the image route uploads to a temp dir cleaned per request and calls OpenAI vision, `image_routes.py:19,155-156`); they name OpenAI, consistent with the consent sheet and the description; AR is Arabic-script only (w37 u11 holds). No risk. Do not add "MYEZ does not store them" (not measured; the policy wording is the owner's).
- **Privacy manifest PurposeOther:** aligns the binary with the published labels; no risk.
- **Google button:** official "G" in a custom button, Apple first and the same 48 pt height on both screens meets the HIG parity finding (L5-08); Google's branding rules are Google's, not Apple's. The Register re-layout needs RV9 so a blocked Create Account is not a silent dead tap.
- **Copy:** the new strings pass the copy policy; "Your country helps tailor the advice." is true only while `ENABLE_COHORT_PERSONALIZATION` is on in production (code default false, `extraction_service.py:2061-2062`; the 2026-09-06 Railway snapshot recorded true; not re-read, Railway is off limits) -> RV19.
- **Onboarding resume:** removes the "reload looks like a crash" finding; the residual risk is a second boot-time reload (RV7).
- **Remaining reviewer-visible claims the unit leaves:** steps 13-15 say "Trained by your peers", "{{count}} cohort peers helped train this", "Matching to peers in {{governorate}}", and the loader caption "cohort peers refining your match" (`loading.cohort.caption`); every new account passes steps 13-15 -> RV17.

## 7. Proposed rulings

- **RV1 (BLOCKING B1).** Every row that needs a fresh `onboardingResume` memo (R12, R13, R20, R20b, R21, R22, R24) uses ONE recipe: `await jest.isolateModulesAsync(async () => { const AS = require('@react-native-async-storage/async-storage').default; /* plant the record with await AS.setItem(...), or for R21 replace AS.getItem with the deferred stub */; const React = require('react'); const TL = require('@testing-library/react-native/pure'); const { NewOnboardingHost } = require('<path>/NewOnboardingHost'); /* flush */; const r = TL.render(React.createElement(NewOnboardingHost, {...})); /* assert, fireEvent from TL */; TL.cleanup(); })`; service-only rows (R12, R13) require `onboardingResume` inside the same isolate after planting. Never render an isolated component with the outer RNTL (p1); never require the RNTL index inside an isolate (p2); assert storage through the isolate's `AS`, never the outer import (p5). Alternative if the orchestrator prefers no isolation: a test-only `__resetOnboardingResumeMemoForTests()` export and a host that calls the memoised `loadOnboardingResume()` on mount when `peek` is unsettled (then R20 / R21 / R22 / R24 run in the normal registry). Why: section 0 probes p1, p2, p4, p5.
- **RV2.** R51 sets `__DEV__ = true` for its call and restores it (MR4). Why: C3.
- **RV3.** Comm gate = chunk A (the 23 non-hook files, bound 1200) + chunk B (the 8 source-scanning pins, bound 600), base (measured, section 0) and head, `comm -13` of the sorted FAILED ids empty. The precommit-hook pair is out with the reason "fixture path literals in a temp repo; reads no real client file; the unit edits no hook". Strike L8 and gate 7's 25-file chunk. Why: C5, C6.
- **RV4 (user request, font).** Correct Q2 per C1. Do NOT fold a font change into B3-A: applying any family is a typography change across every `Text` (42 snapshots, `arabicLineHeightMultiplier`) and needs the owner's face choice. Open a separate unit B3-T after the owner picks: either apply the already-bundled Cairo, or add a local OFL TTF set (candidates to show: IBM Plex Sans Arabic, Tajawal, Readex Pro, Noto Kufi Arabic) under `assets/fonts/` with NO npm change; ship it in the build-3 binary through the `expo-font` plugin if it must be in the reviewed build, otherwise by OTA after approval through `useFonts`. Why: the user asked for it; the spec's premise was wrong; scope and snapshot risk.
- **RV5 (user request, design).** Ask the user which screen "look at Cal AI" refers to BEFORE B3-A RED. If it is Login / Register (the screens C6 re-lays), fold the restyle into C6 now (R39-R42 pin order, row width, height and label size, which a restyle keeps) so the files churn once; otherwise a separate design unit after B3-A merges. Why: avoid two passes over the same files in one binary.
- **RV6.** Keep dropping `offlineAccess`, but restate C6 and add a limit: "no effect on iOS; the iOS SDK still returns a serverAuthCode because `webClientId` sets `serverClientID` (`RNGoogleSignin.mm:100`); the app never reads, sends or stores it". Why: C2.
- **RV7.** In `useLanguage`'s reload path, write `@qaren_rtl_bootstrapped` = `'rtl'|'ltr'` (the target) before `Updates.reloadAsync()`, inside the same try and bound as `beforeReload`; add MR9. Why: `rtlBootstrap.ts:55-61` reloads again whenever `I18nManager.isRTL` disagrees and the flag is not the target; `useLanguage` never writes the flag, so if `isRTL` were stale after the first reload, `init()` would reload a second time AFTER the import-time preload consumed the remove-on-read record, and the user would land on step 1 again. Whether `isRTL` can be stale after `reloadAsync` on RN 0.81 / new architecture is unmeasured (device), so this is defence in depth at the cost of one AsyncStorage write.
- **RV8.** `logout()`'s `finally` also clears the resume record (beside `clearOnboardingDraft`). Why: closes L5 for one line; no existing logout pin asserts AsyncStorage removals by key.
- **RV9.** Register keeps the Login order (ConsentRow, Apple, Google, OR, form) and adds MR7: a blocked Create Account brings the consent error into view. Why: section 6.
- **RV10.** New / changed AR values carry no diacritics except «ميّز» (MR11); the fixture's 7 AR strings are re-spelled before RED, e.g. «الكاميرا غير مفعلة لهذا التطبيق», «سجل الدخول لمقارنة أي منتجين.», «كل مقارنة تجريها تحفظ في السجل.», «صمم للمتسوقين في الخليج.», «نعرض الأسعار حاليا بالدينار البحريني. ...», «مقارنات جنبا إلى جنب ...»; all still [NATIVE READ]. Why: C9; the S69 rule for new AR copy.
- **RV11 (owner's call).** Consider "Continue" / «متابعة» for the not-denied pre-permission CTA (`home.permission.cta`); if adopted, R9's text changes before RED. Why: section 6.
- **RV12.** Add the four comm constraints of section 5 to the spec's section 2.8 as GREEN rules.
- **RV13.** R37 and gate 9 use the repo-root `docs/privacy-data-inventory.md`. Why: C7.
- **RV14 / RV15 / RV16.** Adopt MR2, MR3, MR5 (and MR6, MR8, MR10) as rows; mutants to add: M41 "wrapper hook `require('expo-screen-capture')` in `src/hooks/`" (MR2), M42 "`secureTextEntry={false}` on Register" (MR3), M43 "AppState listener never removed" (MR5), M44 "`openSettings` rejection rethrown" (MR5), M45 "TTL check `<` instead of `<=`" (MR6).
- **RV17 (Q4).** Extend item 4 to the learning claims a reviewer sees on every new account: `onboarding.s13.subtitle` ("Trained by your peers."), `onboarding.s14.cohort_footer`, `loading.cohort.caption`, and the en :631-633 / :637 / :665 / :751 set; survey-backed cohort counts may stay. Same fences (none of these keys is a BRAND_KEY or VERB_KEY). Owner confirms.
- **RV18 (Q8).** ScanCamera's denied pad is practically unreachable on iOS (ScanCamera is entered only from Home's granted branch, `HomeScreen.tsx:719,779`, and iOS terminates an app whose privacy permission changes in Settings); keep it as cheap defence or drop R11; no App Review impact either way.
- **RV19.** The owner confirms `ENABLE_COHORT_PERSONALIZATION` is on in production, or `onboarding.s4.subtitle` keeps only its first sentence.
- **RV20.** Allow LoginScreen's local `SocialButton` to move to a shared `src/components/SocialSignInButton.tsx` (add it to gate 9) so Register reuses one implementation; the `login-social-*` testIDs and `auth.googleSignIn` label are unchanged.

## 8. OTA vs binary (checked)

The spec's table is right: C5 purpose strings and the privacy manifest are binary-only; every other change is JS and OTA-capable (Linking.openSettings is core RN; react-native-svg, expo-updates and AsyncStorage are already native). Addition for RV4: a font listed in the `expo-font` config plugin is binary; a font loaded only by `useFonts` from a JS asset is OTA-capable.

## 9. Stated limits of this review

- No device was used; every device claim (black block view, denial flow, RTL reload, Google sign-out / revoke) stays as the spec states it.
- Railway, Supabase and the network were not touched; the production state of `ENABLE_COHORT_PERSONALIZATION` is from the 2026-09-06 snapshot only.
- The Cal AI reference was not looked up (no network); RV5 asks the user instead.
- The precommit-hook pair was not run (excluded by RV3 with a measured reason).
