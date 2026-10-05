# READINESS_CLIENT — MYEZ iOS store binary (SmartCompareApp at main 845ece15)

Finder: CLIENT (Opus, read-only), session 72, 2026-10-05 13:47-14:40 AST. Checkout `C:/Users/SynAckITPC/Documents/AI/sc-s71-u13` at `845ece15` (git status clean). Every `file:line` below is at 845ece15 unless it names another file. Nothing was run against the network, EAS, Sentry, Railway or a device. No jest, tsc or eslint run (every claim was settled by reading). Orchestrator facts for 2026-10-05 are taken as given: zero mobile-UA requests in 38 h, Sentry `react-native` 0 issues in 14 days, phones on OTA `e2bde9c9` (from `94c097cd`), no production build, no ASC record, no screenshots, `qaren.app` 522.

## 0. Verdict in five lines

1. **The repo is closer to launch than the runbook table suggests.** Every Claude unit that needs no owner input is merged: #253, #254, #255, #257, #258, #269, #274 (session 69), and #279, #288, #307, #313 (session 71).
2. **Two App Review blockers are code-visible.** First, the in-app legal screens render the backend's 2026-03-26 DRAFT template, which still says "Qaren" and promises an opt-out that does nothing. Second, the Profile "Help improve AI quality" toggle is still on screen and has no effect. Both wait on owner input: U8 needs the legal inputs and U3b needs D3.
3. **Three new client findings that no document lists:**
   - placeholder copy on the reviewer's path: "Photo upload coming soon" on the account-deletion screen, and "Pricing lands in an upcoming update." on every pending price;
   - Google Sign-In has not been verified on any build since CLAUDE.md recorded it failing (session 54), and it would be the reviewer's first tap;
   - the canary value: at the documented soft-launch value of 10, 90 % of new users get the legacy 6-step onboarding, which no device has run in months.
4. **Mobile Sentry reporting should work, judging by the code alone.** The DSN is hard-coded, init runs first, there is no enabled gate, error sampling is 100 %, and `beforeSend` returns the event. The 0 events match the 0 mobile requests: nobody opened the app. One zero-code device test proves delivery (section 4).
5. **Nothing merged in session 71 is on a phone.** The new icon and launch screen need a NEW binary. No iOS binary has been built since 2026-07-04, so a preview build from the release commit has to come before the production build.

## 1. app.json (store config)

| Field | Value at 845ece15 | Evidence | Status |
|---|---|---|---|
| name | `MYEZ` | app.json:3 | DONE (#254/#257) |
| slug / scheme | `qaren` / `qaren` (identifier, allowed) | app.json:4, :15 | DONE |
| version | `1.0.0`; `runtimeVersion.policy appVersion` | app.json:5, :264-265 | OK for the first store build |
| bundle id | `com.qaren.app` (matches AASA appID `8K562M549D.com.qaren.app`, landing/.well-known/apple-app-site-association) | app.json:21 | DONE |
| supportsTablet | `false` | app.json:22 | DONE (#254); native, in the binary only |
| orientation / style | portrait / light | app.json:6, :8 | OK |
| usesAppleSignIn | true | app.json:23 | DONE |
| associatedDomains | `applinks:qaren.app` only | app.json:24 | OPEN (domain 522; section 6) |
| Export compliance | `ITSAppUsesNonExemptEncryption: false` | app.json:145 | DONE |
| Usage strings | camera "MYEZ needs camera access to photograph products for comparison." (app.json:212); microphone, honest, on BOTH expo-camera and expo-image-picker (app.json:213, :221); photos (app.json:220); `faceIDPermission:false` (app.json:197); `locales/en.json` + `locales/ar.json` carry CFBundleDisplayName + the three purpose strings | as listed | DONE (#254); AR strings still need a native review |
| Locales | `expo.locales` en/ar (app.json:16-19), expo-localization `supportedLocales.ios [en, ar]` (app.json:203) | as listed | DONE |
| privacyManifests | `NSPrivacyTracking false`; 13 collected types, identical to `docs/privacy-data-inventory.md` (13 types; purposes AppFunctionality 12 / Analytics 4 / ProductPersonalization 3 in both); 4 required-reason APIs CA92.1 / C617.1 / 35F9.1 / E174.1 | app.json:25-141; equality pinned by `__tests__/config/nativeBundle.w37.test.ts` | DONE; PM-7 (post-build privacy report) still owed on a real build |
| Plugins | expo-font, expo-secure-store, expo-localization, expo-camera, expo-image-picker, google-signin (iosUrlScheme), expo-apple-authentication, expo-notifications, expo-build-properties, @sentry/react-native {url de.sentry.io, org qaren-rr, project react-native} | app.json:183-256 | OK. The Sentry source-map upload has been on since `43cca757` (2026-05-24), so the build needs `SENTRY_AUTH_TOKEN` in the EAS production environment, or `SENTRY_ALLOW_FAILURE` (EXPO-12) |
| Android intent filters | qaren.app /r/ /c/ /q/ + `qaren` scheme | app.json:157-171 | not in the iOS lane |

## 2. eas.json

- `cli.version >= 18.8.1`, `appVersionSource: remote` (eas.json:2-4).
- Profiles (eas.json:6-22):
  - `development`: developmentClient, internal, channel development;
  - `preview`: internal, channel preview;
  - `production`: `autoIncrement: true`, channel production.
- **No `env` block in any profile.** No `EXPO_PUBLIC_*` name is defined in eas.json. The client reads exactly one `EXPO_PUBLIC_*` name, `EXPO_PUBLIC_SENTRY_DSN` (sentry.ts:231), with a hard-coded fallback. The API base URL is hard-coded: `API_BASE_URL = 'https://web-production-58776.up.railway.app'` (api.ts:20).
- What is set in the EAS dashboard environments is NOT VERIFIED today. The runbook §7 says only `SENTRY_AUTH_TOKEN` is set.
- **The submit block is present but empty:** `"submit": {"production": {}}` (eas.json:23-25). U10 fills `ios.ascAppId` + `appleTeamId` once the ASC app id exists. Until then `eas submit` can only run interactively, with an Apple login that can create or look up the app. The runbook's "missing block" is more precisely an empty block.

## 3. CANARY_NEW_ONBOARDING_PERCENT

- **Value now:** `export const CANARY_NEW_ONBOARDING_PERCENT = 100;` (src/config/features.ts:30). Its comment says "MUST drop back to 10 immediately before App Store soft-launch submission" (features.ts:25-27).
- **The CLAUDE.md rule, verbatim:**
  - CLAUDE.md:255: "set the soft-launch value 10 on main BEFORE `eas build --profile production`, then ramp 10→50→100 only with `eas update --branch production`, never `preview`."
  - CLAUDE.md:506: "Drop to 10 only at App Store soft-launch, then ramp 10→50→100 per `docs/runbooks/qaren-canary-onboarding.md`."
- **What the value controls:** App.tsx renders `NewOnboardingHost` (the 17-step flow) when `features.ENABLE_NEW_ONBOARDING` is true and the legacy 6-step `OnboardingScreen` otherwise. The flag is `hashBucket(stable id, percent)` (features.ts:108-110), keyed on user.id after sign-in.
- **What 10 would mean:** about 90 % of new accounts get the legacy flow (language, region, priorities, budget, lifestyle, brand; OnboardingScreen.tsx, 413 lines). That flow:
  - has no "What reaches OpenAI" step (#274 Step 5) and no Step 17 push ask (#269). The AI-consent sheet at Home still gates every compare, and the push ask then comes only from the post-result pre-prompt;
  - has not run on a tester phone for months, because testers bucket at 100.
- **The App Review reviewer is not affected either way.** The demo account completes onboarding before submission (runbook §3 E1).
- **Decision owed (Ahmed):**
  - (A) follow the rule: set 10 on main before the build and add the legacy flow to the device checklist; or
  - (B) keep 100 and record the change of rule in CLAUDE.md and the canary runbook.
- **Finder's recommendation: B.** The legacy flow is the less-reviewed path, and a canary at launch volume buys little signal. Assumption: launch volume is small, which the 0 organic mobile requests support.
- Either way the value is embedded in the binary. Changing it after launch needs a production-channel OTA.

## 4. Sentry on the client: verdict

**Verdict: reporting should work, judging by the code alone. Zero events are fully explained by zero app usage. Delivery has never been observed after 2026-07-06, so treat it as UNPROVEN, not broken.**

Evidence (all at 845ece15):

**Init order.** `index.ts:6` imports `./src/services/sentryBootstrap` FIRST. Its body calls `initSentry()` (sentryBootstrap.ts:23-25) before App's import graph runs. The order is pinned by `__tests__/bootSentryOrder.w312.test.ts` (W3-12, #145). App's default export is `Sentry.wrap(App)` (App.tsx:501).

**DSN.** `dsn || process.env.EXPO_PUBLIC_SENTRY_DSN || FALLBACK_DSN` (sentry.ts:229-232):
- The fallback is a hard-coded DSN on `ingest.de.sentry.io` (sentry.ts:59-60). It is the ONLY DSN ever committed (`git log -p`: introduced in `4558f9e5` on 2026-05-16, never changed).
- eas.json sets no `EXPO_PUBLIC_SENTRY_DSN`, and Metro inlines `EXPO_PUBLIC_*` at bundle time. Every OTA bundle and every build therefore gets the fallback, unless an EAS dashboard environment sets that name. That is NOT VERIFIED; the runbook §7 says only `SENTRY_AUTH_TOKEN` is set.
- The `react-native` project's last issue, REACT-NATIVE-D, was seen 2026-07-06 (ledger 07:55). That date fits device builds from that time delivering through this same DSN.

**Enabled conditions.** No `enabled:` option and no `__DEV__` gate (sentry.ts:235-245). It reports in Expo Go, dev and release alike. In Expo Go the native layer is absent and the SDK falls back to JS transport. The `try/catch` only swallows an init throw.

**Sampling.** No `sampleRate`, so errors and messages go out at 100 % (the SDK default). `tracesSampleRate: 0.1` affects only transactions. That explains "0 spans" with little or no usage, and it does not suppress errors.

**beforeSend.**
- `scrubBeforeSend` (sentry.ts:96-148) always returns the event.
- `scrubBeforeBreadcrumb` (:156-169) and `scrubBeforeSendTransaction` (:178-201) also always return their input.
- Nothing drops events.

**SDK/native match.** `@sentry/react-native ~7.2.0` has been pinned since `c8b37fb3` (2026-05-16). That predates the 2026-07-04 iOS build the testers run, so JS and native SDK versions match under any OTA. The lock holds one copy, 7.2.0.

**Event producers that need no error.** `comparison_wall_time` (level info) is captured on EVERY ResultsScreen unmount:
- the reveal-timer effect (ResultsScreen.tsx:460-495, deps `[]`) calls `tracker.mark('ready_celebration')` after 800 ms;
- `mark()` sets `started` even without `start()` (wallTimeInstrumentation.ts:70-76);
- `report()` then captures on unmount (ResultsScreen.tsx:493; wallTimeInstrumentation.ts:97-112).

The cert-pin listener (certificatePinning.ts:111-125), the release-build pinning-init warning (:140-147) and the Google `b4_diag` messages (authService.ts:878/960/985/997) are the other producers.

**Why 0 events.** Any Results visit on any build since Sprint A would have produced a `comparison_wall_time` event. Zero events in 14-30 days therefore means either nobody reached Results or delivery is broken. With 0 mobile-UA requests in 38 h (and 77 h in session 71), the first explanation is sufficient. That is an assumption: it beats "broken" because the code path contains no drop point and the DSN delivered in July.

**What cannot be decided by reading:** the DSN to project mapping on the Sentry side, a dashboard `EXPO_PUBLIC_SENTRY_DSN`, native transport behaviour, device egress.

**Cheapest on-device test (zero code, works while OpenAI is still unfunded).**
1. A tester signs in on the current preview build. Any OTA works; `e2bde9c9` already has the instrumentation.
2. In Safari, open `qaren://comparison/sentry-check` and accept "Open in MYEZ". This route comes from linking.ts:83; any Results visit works.
3. The Results screen opens on "comparison not found". Wait 2 seconds, then close it.
4. Within a minute, Sentry org `qaren-rr`, project `react-native`, must show an issue or event with message `comparison_wall_time`, level info, carrying the tag `wall_time.ready_celebration_ms`.

If nothing appears after the app is foregrounded again, mobile reporting is broken. The conditional unit U-SNT below then applies. A session row under Releases is a second, weaker signal (auto session tracking is on by default; NOT VERIFIED).

**Launch weight.** High, not an App Review blocker. The cert-pin-rotation alarm (section 7) and every crash signal depend on it.

## 5. What a reviewer sees first

**Native launch screen.** `splash-icon.png` on white (app.json:10-14). The MYEZ art is on main (#279) but in a NEW binary only.

**JS splash.** The mark is drawn at the native frame and does not move. Only the tagline fades. It lasts at most 1.5 s (SplashScreen.tsx:29, :120; #288).

**Login gate.**
- Unauthenticated users land on `Auth > Login` (App.tsx:365-371). There is no guest path (LL-3; D6 is open).
- Login offers the native `AppleSignInButton` (LoginScreen.tsx:60; #269), Google (a coloured text "G" placeholder glyph, LoginScreen.tsx:115-122) and email/password.
- Register carries the 13+ consent row with Terms/Privacy links (RegisterScreen.tsx:138 to Legal).
- `usePreventScreenCapture` runs on the four auth screens only (LoginScreen.tsx:194 and peers), so no screenshot target is blocked.

**Google Sign-In: NOT VERIFIED and a risk.** CLAUDE.md:876 still says "currently failing on EAS preview (Session 54)". No open issue tracks it, and no iOS build has existed since 2026-07-04 to re-test it. A failing first-row button is a guideline 2.1 rejection.

**Demo account.** Email login exists (`auth.email` / `auth.password`). The account itself is Ahmed's (confirmed, onboarded, `subscription_tier=premium`).

**Onboarding, for a new account only.** At percent 100: the 17-step flow minus Step 16 when signed in (`AUTHED_STEP_SEQUENCE`, OnboardingFlow.tsx:130, :212):
- no whole-flow skip;
- Steps 6 and 7 (age, gender) have Skip (OnboardingFlow.tsx:560, :567);
- Step 14 holds a 3.2 s floor (Step14 `DEFAULT_MIN_DURATION_MS = 3200`).

At percent 10: the legacy 6-step flow for about 90 %.

**AI consent sheet.**
- Shown before the first compare, scan, photo-library pick or camera permission (`withAiConsent`, #274). It names OpenAI (en.json `aiConsent.body`).
- "Read more in the Privacy Policy" opens Legal (HomeScreen.tsx:141).

**LegalScreen renders the DRAFT text verbatim.** It fetches `/api/v1/legal/privacy_policy|terms_of_service` (LegalScreen.tsx:33-34, :52-55) and renders the markdown unchanged. The backend files start:
- privacy_policy.md:3 `**Qaren — Product Comparison App**`
- privacy_policy.md:5 `*Last Updated: March 26, 2026*`
- privacy_policy.md:7 `*DRAFT — This document is a template...*`
- terms_of_service.md:3-7, the same lines

privacy_policy.md:82-88 promises the "Help improve AI quality" opt-out. The screen is English-only (LL-14) and caches the last copy in AsyncStorage `legal_cache_<doc>` (LegalScreen.tsx:46, :56-61). This is App Review blocker LL-1/RT-3 and waits for U8. The fix is backend content + landing, plus the client `TERMS_VERSION` (consent.ts:12 `'2026-03-26'`).

**The Profile "Help improve AI quality" toggle is still rendered** (ProfileScreen.tsx:503-510). `select_client_for_user` has 0 callers (only its def, openai_service.py:82; #266), so the toggle routes nothing, and its subtitle makes a privacy promise (en.json:417). This is U3b and waits for D3. High (5.1.2 disclosure honesty).

**Limit sheet.** The honest limit sheet is DONE: PaywallScreen.tsx has no price, trial, Restore, "Coming soon" or rating (grep, 0 hits; #255). The only remaining "Premium" strings are budget-tier labels (`onboarding.budget.premium`, `results.value.premium`), not purchases. There is no 3.1.1 wording.

**Placeholder copy on the reviewer's path (NEW).**
- `editProfile.avatar.placeholder` "Photo upload coming soon" is rendered under the avatar (EditProfileScreen.tsx:188; en.json:919). This is the account-deletion screen the review notes send the reviewer to.
- `results.price.pending` "Pricing lands in an upcoming update." (en.json:155; ResultsContent.tsx:139) shows on every pending price, which is common.

Both read as unfinished-feature placeholders under guideline 2.1. Medium.

**Account deletion is reachable in-app.** Path: Profile tab, then the header gear ("Settings", ProfileScreen.tsx:366, which opens EditProfile directly), then "Delete account" (EditProfileScreen.tsx:275), a confirm Alert (:126-133), then `DELETE /api/v1/auth/account` (:137). DONE. The review-notes text "gear icon → Edit profile → Delete account" should read "gear icon → Delete account", because the gear opens Edit profile itself. Migration 043 (full erasure) is backend and unapplied (backend lane).

**Push permission.** It is asked in exactly two places: onboarding Step 17 (Step17Notifications.tsx:60) and the one-time post-result pre-prompt (pushPrePrompt.ts:109). It is never asked at launch or login (#269, RT-12 DONE).

**Brand fences.**
- `__tests__/i18n/brand.myez.s69.test.ts` covers the brand-key set, the 10 Arabic verb uses of قارن, and "no blind replace" of the embedded forms.
- `brand.hardcoded.s69` covers hard-coded literals in src.
- `landing.brand.s69` covers the 9 landing pages.
- `tests/test_health_brand_s69.py` covers the /health text.
- `inAppMark.u4c` / `revealGlyph.u4d` cover no Q glyph in src.

My own greps:
- "Qaren|QAREN|Qaran" over src, App.tsx and locales finds ONLY identifiers and comments: `QarenLogo` imports, file headers, and the key name `referrals.landing.openQaren`, whose value is "Open MYEZ" (en.json:464).
- A scan of every en/ar catalog value finds 0 Latin "qaren/qaran" values. The 1,000 keys are equal in en and ar.
- The Arabic قارن substring hits are verb forms (`app.tagline`/`splash.tagline` "قارن بذكاء", `home.compare.cta` "قارن", `history.recompare`, `onboarding.s15.cta`, ...) and embedded مقارنة forms. These are allowed by the s69 ruling.
- No old logo: QaranIcon is deleted (#307), and `QarenLogo` renders the MYEZ PNG (#288).

**Fabricated-number copy (low).**
- `onboarding.s12.title` "388 GCC shoppers helped train this." is rendered by Step12CohortProof.tsx:116 in the new flow. Its source was NOT VERIFIED; it may be the survey count.
- `results.tips.cohort_match` "47 cohort peers..." and `results.tips.cohort_priority` "73%..." are in the catalog. No render site was found for them (the U6 R6 removal), so they are dead keys.

## 6. Deep links and universal links

- Prefixes: `['qaren://', 'https://qaren.app']` (linking.ts:47). Routes:
  - `c/:share_token` goes to ReferralLanding and `q/:share_token` to InviteeQuiz;
  - `r/:code` and `reset-password` go to Register and ResetPassword;
  - `profile/referrals`, `cohort/divergence` and `comparison/:comparison_id` are the push targets (linking.ts:48-85).
- Universal links depend on `applinks:qaren.app` (app.json:24). The landing serves the AASA (appID `8K562M549D.com.qaren.app`, paths `/r/* /c/* /q/*`), and nginx routes `/c/ /r/ /q/` to `open.html` (landing/nginx.conf.template:15, :63-70). That works on the Railway landing host only.
- **What the 522 breaks:**
  - The associated-domain check fails. Universal links never open the app; harmless to the binary and to review.
  - **Every backend-built share/referral link is dead for recipients**: `APP_BASE_URL = "https://qaren.app"` (app/services/referral_service.py:50), and the share preview uses `https://qaren.app/r/QR-XXXXXX` (ShareBottomSheet.tsx:143). A reviewer who taps Share on a result hands out a Cloudflare 522 link. High.
  - Support mail `mailto:support@qaren.app` (ContactUsScreen.tsx:218) forwarding is unverified (LL-13/RT-11).
- The landing hand-off page is live on `qaren-landing-production.up.railway.app` since session 70.
- **Fix options, Ahmed's call:**
  - attach `qaren.app` to the landing service (no code); or
  - a backend unit that reads the share host from env and points it at the Railway landing until then (no binary change); optionally a native change adding `applinks:qaren-landing-production.up.railway.app`, which needs a new binary.
- `qaren://reset-password` needs the Supabase redirect allow-list entry plus `ENABLE_PASSWORD_RESET_DEEP_LINK` (RT-10, Ahmed).

## 7. Certificate pinning: failure mode and signal

- 13 SPKIs, all ISRG / Let's Encrypt (X1, X2, YE, YR roots; YE1-3, YR1-3; legacy E5/E7/E8), pinned on `web-production-58776.up.railway.app` with `includeSubdomains` (certificatePinning.ts:52-85 hashes, :69 host, :98-104 init; #253).
- **If Railway's chain rotates to anything outside that set** (a different CA, or a new Let's Encrypt generation), the native pinning library rejects every backend call:
  - Every axios call fails with "Network Error". Sign-in, compare, history and legal all fail, so the app reads as offline and is unusable.
  - The server stays healthy, so `/health` monitoring does not see it.
- **Signal:** one Sentry event per session per device, `[SECURITY] Certificate pin mismatch - backend call rejected`, fingerprint `cert-pin-mismatch` (certificatePinning.ts:111-125).
  - The Sentry ingest host is not pinned, so the event can leave the device.
  - It is only as good as mobile Sentry (section 4).
  - A release build where pinning init fails reports `...running unpinned` as a warning (:140-147).
- **Recovery:** the pins are JS, so a production-channel OTA carries new pins. Two cold launches are needed. expo-updates fetches from `u.expo.dev`, which is not pinned.
- `ENABLE_EXPO_FETCH_SSE_DEFAULT = false` must stay false: expo/fetch may bypass the pinning hook (features.ts:40-52).

## 8. Device checks owed: ONE ordered list

The tester binary predates #254 (native config) and #279 (icons, bumps). "OTA" below means the preview channel updated from main 845ece15, after U4b's OTA rule:
- (a) `npm ls` shows the U4b version set;
- (b) smoke that OTA on ONE phone before announcing it (PR_279 body).

"NEW" means a preview build from the release commit, installed after deleting the old app, and then the same checks on the production/TestFlight binary.

| # | Check | OTA (preview) | NEW binary |
|---|---|---|---|
| 1 | Mobile Sentry delivery: the `qaren://comparison/sentry-check` test, a `comparison_wall_time` event in `react-native` | yes (do first; also works on `e2bde9c9`) | repeat on TestFlight (release transport) |
| 2 | U4b OTA smoke: the app boots and every tab renders after the OTA from a U4b main | yes, on ONE phone | n/a |
| 3 | Email/password sign-in; the native Apple button (CONTINUE/SIGN_UP, black, full width) on Login and Register; a wrong password shows the invalid-credentials copy, not a raw 401 | yes | Sign in with Apple again on the App Store-signed build |
| 4 | Google Sign-In end to end (CLAUDE.md:876 says failing since session 54) | yes | yes; if it fails, hide or fix before the build |
| 5 | AI consent sheet EN + AR copy; Agree / Not now; the Privacy link closes the sheet and opens Legal | yes | yes |
| 6 | Legal screens (privacy, terms): today they show DRAFT/Qaren, the expected fail until U8 + backend deploy | yes | yes (after U8) |
| 7 | Compare: outage copy while OpenAI is unfunded; after funding, a real verdict, degraded-result copy, confidence pills | yes | yes |
| 8 | U13c camera 401: sign in, let the access token expire, take two photos, expect a result with no sign-in prompt (L1 re-sends the same FormData through native networking) | yes | yes |
| 9 | Honest limit sheet with an exhausted free account (3/day); monthly wins over daily | yes | optional |
| 10 | Push: the pre-prompt appears once after a fresh result and never at launch or login; Step 17 persists the answer | yes (permission UI) | APNs token + one test push via Expo's push tool on TestFlight |
| 11 | Trending tap prefills both inputs and runs the compare; no invented view counts | yes | - |
| 12 | Account deletion with a throwaway account: Profile, gear, Delete account, confirm; signed out after | yes | - |
| 13 | U4c mark sharpness at 24 pt (History), 28 pt (Home, Profile) and in the loaders, on a 2x and a 3x iPhone; Home header 2 pt shorter | yes | - |
| 14 | U4d reveal badge: mark at the 1.1 spring overshoot (no halo, slight softness); whether the 112 pt badge hides a DimensionBars label (L3); Register header gap mark-to-tagline; ForgotPassword mark | yes | - |
| 15 | JS splash motion: the mark never moves or fades; the tagline fades in after 200 ms (L6) | yes (motion only) | the hand-off itself, row 18 |
| 16 | Arabic, part 1 (JS): RTL on first launch (one reload, flag written first); the 51 `results.dimension.*` labels (45 reachable, longest 21 chars) on one line, plus a native review of all 51 (8 reworded in #251); plurals at 0/1/2/3/11 incl. `referrals.bonus.expiresIn*`; InviteeQuiz char counter and the six reverted `textAlign` cells; LoadingRings through a full slow compare; onboarding Step 14 SVG; icons on every screen; AR consent sheet + Step 5 copy; AR U6 strings (auth errors, push pre-prompt) | yes | spot re-check |
| 17 | Launcher icon is the MYEZ art; the old app was deleted first, so no cached icon or launch screen | no | yes |
| 18 | Launch screen to JS splash hand-off: no jump in EN, no horizontal jump in AR (RTL pre-mirror); white or blank flash on a FRESH install and again after an OTA. If visible, a native expo-splash-screen unit is needed before the store build | no (the old binary's launch screen is the Expo placeholder) | yes |
| 19 | Native strings: camera and photo prompts EN + AR; no microphone prompt ever; no Face ID prompt; home-screen name "MYEZ" / "ميّز" under an Arabic device language | no | yes |
| 20 | Certificate pinning active in the release build: no `running unpinned` Sentry warning; normal calls succeed | no | yes |
| 21 | iPad (if one is available): the iPhone-only app runs in compatibility mode, which App Review may use | no | yes |
| 22 | Universal links: only after qaren.app is attached (otherwise they open the Railway hand-off page in Safari) | no | yes |
| 23 | Full smoke on the EXACT TestFlight binary (Apple, Google and email sign-in, camera, compare, push, Arabic walkthrough), and the ASC processing email has no ITMS-90683 / 91053 / 91061 | no | yes |
| 24 | Legacy 6-step onboarding end to end, ONLY if Ahmed picks canary 10 | yes (force by bucket) | yes |

## 9. Levers: every client change since 94c097cd (the phones' OTA base)

`git diff --name-only 94c097cd 845ece15 -- SmartCompareApp` lists 45 files, 26 of them non-test.

| PR | Client change | OTA carries it? | Only a new binary? |
|---|---|---|---|
| #279 U4b | `assets/icon.png`, `splash-icon.png`, `adaptive-icon.png` (launcher icon, native launch screen) | no | YES |
| #279 U4b | `assets/favicon.png` | web only, not a launch item | - |
| #279 U4b | `package.json` / lock: expo 54.0.37 + the SDK-54 patch set, gesture-handler removed | the JS halves ride any OTA bundled from this main, under the U4b OTA rule | the native halves: YES |
| #288 U4c | `QarenLogo.tsx` (PNG Image), `assets/brand/myez-mark{,@2x,@3x}.png`, SplashScreen hand-off + `utils/splashMarkLayout.ts`, Home header | YES (assets ship in the update) | must be embedded. The hand-off geometry matches the NEW launch screen only |
| #307 U4d | RevealBurst badge, Register and ForgotPassword marks, `QaranIcon` deleted, `icons/index.ts` | YES | must be embedded |
| #313 U13c | `services/api.ts` (camera 401 refresh-retry), ResultsScreen auth state, `sessionEvents.ts` comment | YES | must be embedded |
| #288/#307 | comment-only edits: LoadingRings, Profile, History, PhoneMockup, UtilityIcons | YES (no behaviour) | - |
| #285 #290 #297 #310 #312 | backend / tooling | n/a (Railway) | - |

Session-69 client units (#253 pins, #255, #257, #258, #269, #274) are already on phones via `e2bde9c9`. #254 (native config) is NOT on phones; it needs a new binary.

**Cut the production build from a main that contains:**
- already on main: #253, #254, #255, #257, #258, #269, #274, #279, #288, #307, #313;
- still to land: U8 (legal + `TERMS_VERSION`), U3b (the toggle), the canary decision commit, the placeholder-copy unit, and the Google decision.

The full list is in extra[].

## 10. Dependency state and CI

- **package.json vs lock: in sync.** The lock's root `dependencies` (42) and `devDependencies` (12) equal package.json, and every direct dependency resolves inside its range (scan_lock_out.txt). There is one copy each of expo 54.0.37, expo-constants 18.0.14, expo-updates 29.0.20, @sentry/react-native 7.2.0, react-native 0.81.5 and react-native-ssl-public-key-pinning 1.2.6. `react-native-gesture-handler` is absent. `expo-dev-client` stays a dependency (runbook §7: harmless in Release).
- **CI client gates** (`.github/workflows/ci.yml`):
  - frontend-tests job, BLOCKING: `npm ci`, `npx jest --ci` (:291-292), `npx eslint "src/**/*.{ts,tsx}"` (:297-298), `npx tsc --noEmit` (:301-302), and the Expo drift check offline (`EXPO_OFFLINE=1 npx expo install --check`, :331-332);
  - report-only: the online drift check (:334-336);
  - `npm audit --audit-level=high` is `continue-on-error: true` (:226-228), so it never blocks;
  - `channel-freshness` is not required; it skips without `EXPO_TOKEN`, and its 2026-10-07 date is a reminder only (no date-based test).
- **npm audit: NOT VERIFIED today.** There was no network, and no npm command was run. The lock holds no advisory data. The last recorded figure is CLAUDE.md:30 (session 69, 2026-09-29): 35 vulnerabilities (1 low, 20 moderate, 13 high, 1 critical), "none in direct deps". Whether any high or critical advisory sits in a DIRECT dependency at 845ece15 cannot be settled from the lock; the CI log of the latest main run is the source.

## 11. Screenshots

- **Required sizes, from the ASC spec as I know it; the live help page was not re-checked today (no web access).** An iPhone-only app (`supportsTablet:false`) needs ONE iPhone set:
  - 6.9" (1320x2868, 1290x2796 or 1260x2736 portrait); or
  - 6.5" (1284x2778 or 1242x2688).
- 1 to 10 per localization, PNG or JPEG, no alpha (the runbook says Claude strips alpha). No iPad set is needed (#271 updated the checklist to 6.9"/6.5", no iPad).
- A 6.1" phone's native 1179x2556 is not an accepted size and must be resized; the aspect ratio is almost identical.
- **What must work to shoot the six runbook screens:**

  | Screen | Needs |
  |---|---|
  | Home with two products entered | the MYEZ mark in the header: OTA from main 845ece15 or the store build, otherwise the old Q-ring is in the shot |
  | Results winner card | OpenAI funded, a warm-up pair that passes the A1 assertions, the U4d badge |
  | Dimension bars / "where the runner-up wins" | a non-degraded verdict. The badge may cover a bar label (L3) |
  | Confidence pills | a real result with prices. A pending price shows "Pricing lands in an upcoming update.", so fix the copy or pick pairs with prices |
  | Camera framing two products | a physical device, the camera permission granted, AI consent accepted |
  | History with 3 or more entries | 3 successful compares on the demo account (premium: 10/day) |

- Arabic set (optional): the Arabic walkthrough first.
- Do not shoot splash, sign-in, loading or the limit sheet (runbook §3 E3).

## Rows (schema of the synthesis)

See the StructuredOutput rows. They are identical in content to this report.

## Not verified (and why)

- Sentry server side: the DSN-to-project mapping, whether any EAS dashboard environment sets `EXPO_PUBLIC_SENTRY_DSN`, whether sessions show in Release Health. Network and Sentry are forbidden.
- Google Sign-In on any current build: no build exists since 2026-07-04.
- npm audit advisories at 845ece15: no network.
- Screenshot pixel sizes against the live ASC help page: no web access.
- The source of the "388 GCC shoppers" figure.
- The white-flash, sharpness and hand-off device checks: not testable in jest by design.
- That the `comparison_wall_time` event fires on a not-found Results visit: established by reading only (ResultsScreen.tsx:460-495 + wallTimeInstrumentation.ts:70-112), not executed.

## Files written (sha256 in the structured output)

- READINESS_CLIENT.md (this file)
- notes.md
- scan_i18n.py + scan_i18n_out.txt
- scan_lock.py + scan_lock_out.txt
- issues_client.txt
- findings_list.txt
