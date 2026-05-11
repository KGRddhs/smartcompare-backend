# Agent B — Frontend Forensics Report

**Model:** Sonnet | **Returned:** 2026-05-06
**Scope:** `SmartCompareApp/` (Expo managed workflow, React Native 0.81.5, Expo SDK 54)

---

# SECTION 1: Screens Inventory

## 1.1 SplashScreen
- **Export:** `SmartCompareApp/src/screens/SplashScreen.tsx:17` — `export default function SplashScreen`
- **Purpose:** Displays animated logo and tagline for ~1.5 seconds, then fires `onFinish` to proceed to auth or main flow.
- **Auth required:** No.
- **User inputs:** None.
- **Backend calls:** None.

## 1.2 LoginScreen
- **Export:** `SmartCompareApp/src/screens/LoginScreen.tsx:32` — `export default function LoginScreen`
- **Purpose:** Authenticates existing users via email/password, Google Sign-In, or Apple Sign-In.
- **Auth required:** No (pre-auth screen).
- **User inputs:** Email address (TextInput, `keyboardType="email-address"`), password (TextInput, `secureTextEntry`).
- **Backend calls:** `POST /api/v1/auth/login` (email/password); `POST /api/v1/auth/social-login` (Google/Apple, called via raw `fetch` not axios — `authService.ts:414`).
- **Additional:** Calls `usePreventScreenCapture()` (`expo-screen-capture`) — prevents screenshots on this screen (`LoginScreen.tsx:34`).

## 1.3 RegisterScreen
- **Export:** `SmartCompareApp/src/screens/RegisterScreen.tsx:32` — `export default function RegisterScreen`
- **Purpose:** Creates new user accounts via email/password, Google Sign-In, or Apple Sign-In. Optionally links a referral invite.
- **Auth required:** No (pre-auth screen).
- **User inputs:** Email address, password (`secureTextEntry`), confirm password (`secureTextEntry`). Optional `invite_id` route parameter forwarded from referral flow (`RegisterScreen.tsx:38`).
- **Backend calls:** `POST /api/v1/auth/register` (email, password, optional `invite_id`); `POST /api/v1/auth/social-login` (Google/Apple).
- **Additional:** Calls `usePreventScreenCapture()` (`RegisterScreen.tsx:34`).

## 1.4 ForgotPasswordScreen
- **Export:** `SmartCompareApp/src/screens/ForgotPasswordScreen.tsx:31` — `export default function ForgotPasswordScreen`
- **Purpose:** Triggers a server-side password-reset email via Supabase.
- **Auth required:** No.
- **User inputs:** Email address (TextInput, `keyboardType="email-address"`).
- **Backend calls:** `POST /api/v1/auth/password-reset` (`authService.ts:356`).
- **Additional:** Calls `usePreventScreenCapture()` (`ForgotPasswordScreen.tsx:33`).

## 1.5 OnboardingScreen
- **Export:** `SmartCompareApp/src/screens/OnboardingScreen.tsx:51` — `export default function OnboardingScreen`
- **Purpose:** 6-step wizard collecting user preferences after first login (or when editing preferences from Profile). Steps: language, region, priorities, budget, lifestyle, brand attitude.
- **Auth required:** Yes (shown immediately after first authenticated login when `preferences_completed` is false — `App.tsx:135`).
- **Backend calls:** `PUT /api/v1/auth/preferences` via `savePreferences()` from `api.ts:240` (called at `OnboardingScreen.tsx:107`).

## 1.6 HomeScreen
- **Export:** `SmartCompareApp/src/screens/HomeScreen.tsx:53` — `export default function HomeScreen`
- **Purpose:** Camera-first main screen with three input modes: camera capture, text search (via SearchOverlay), and URL paste.
- **Auth required:** No (used anonymously and authenticated). Auth token attached if available.
- **User inputs:**
  - Camera: live viewfinder + shutter button, gallery picker (`expo-image-picker`). Images are JPEG-transcoded before upload (`api.ts:128`).
  - Text: free-text search query (SearchOverlay TextInput).
  - URL mode: two URL TextInputs for product pages.
  - Category selection: chip selector (no free text).
  - Recent searches: stored locally in AsyncStorage at key `@qaren_recent_searches` (`HomeScreen.tsx:41`).
- **Backend calls:**
  - Camera → `POST /api/v1/image/identify` (multipart/form-data, up to 4 JPEG images, region=bahrain) (`api.ts:152`).
  - Text → `GET /api/v1/text/compare/stream` (SSE) with fallback to `GET /api/v1/text/compare` (`api.ts:283`, `HomeScreen.tsx:234`).
  - URL → `POST /api/v1/url/compare` (url1, url2, region, selected_category) (`HomeScreen.tsx:295`).
  - Health check → `GET /health` on focus (`HomeScreen.tsx:93`).

## 1.7 ResultsScreen
- **Export:** `SmartCompareApp/src/screens/ResultsScreen.tsx:83` — `export default function ResultsScreen`
- **Purpose:** Full comparison results: product cards, verdict, price table, specs, reviews, scores, feedback, and referral share CTA.
- **Auth required:** No (results shown to anonymous users too; demographics prompt only shown to authenticated users — `ResultsScreen.tsx:227`).
- **User inputs:**
  - FeedbackCard: thumbs up/down and optional text suggestion (dispatches `POST /api/v1/feedback`).
  - DemographicsBottomSheet: age group, gender, governorate chip selections (optional; all default to "Prefer not to say").
  - ShareBottomSheet: privacy toggles (show_name, show_result, show_reasons) + share target.
  - Specs "show differences only" toggle (Switch — local UI only, no backend call).
- **Backend calls:**
  - `POST /api/v1/events` (batch event tracking on unmount — `ResultsScreen.tsx:149`).
  - `PUT /api/v1/auth/demographics` via `putDemographics()` (`api.ts:452`, triggered from `ResultsScreen.tsx:249`).
  - `POST /api/v1/referrals/share` via ShareBottomSheet (when sharing).
  - `GET /api/v1/usage/status` on mount (`ResultsScreen.tsx:104`).

## 1.8 HistoryScreen
- **Export:** `SmartCompareApp/src/screens/HistoryScreen.tsx:47` — `export default function HistoryScreen`
- **Purpose:** Date-grouped list of past comparisons with search filter and delete option.
- **Auth required:** Yes (401 redirects to login — `HistoryScreen.tsx:69`).
- **User inputs:** Search query TextInput (sent to backend as query param — `HistoryScreen.tsx:65`).
- **Backend calls:** `GET /api/v1/comparisons/history?limit=50&offset=0&search=...` (`api.ts:175`); `DELETE /api/v1/comparisons/{id}` (`api.ts:184`).

## 1.9 ProfileScreen
- **Export:** `SmartCompareApp/src/screens/ProfileScreen.tsx:59` — `export default function ProfileScreen`
- **Purpose:** Account management, settings (language, preferences), privacy controls (AI sharing toggle, notifications), legal links, and danger zone (logout/delete).
- **Auth required:** Yes (loads saved user from local storage on mount).
- **User inputs:**
  - Display name (TextInput, max 100 chars — `ProfileScreen.tsx:331`).
  - Current/new/confirm password (3x TextInput, `secureTextEntry`, via modal — `ProfileScreen.tsx:528`).
  - AI sharing enabled (Switch — `ProfileScreen.tsx:398`).
  - Notifications master toggle and 3 sub-toggles: `decision_insight`, `cohort_curiosity`, `decision_retrospective` (Switch — `ProfileScreen.tsx:419–473`).
  - Language selector (EN/AR inline toggle).
- **Backend calls:** `PUT /api/v1/auth/profile` (display name), `PUT /api/v1/auth/password` (password change), `PUT /api/v1/auth/preferences` (AI sharing, notifications), `GET /api/v1/auth/preferences`, `GET /api/v1/auth/cohort-profile`, `POST /api/v1/auth/logout`, `PUT /api/v1/auth/push-token` (push token registration via `tryRegisterPushToken()` called in `App.tsx:139`).

## 1.10 PaywallScreen
- **Export:** `SmartCompareApp/src/screens/PaywallScreen.tsx:32` — `export default function PaywallScreen`
- **Purpose:** Bottom sheet modal showing usage limits, free vs premium tier comparison, and upgrade CTA (payment not yet wired — comment at `PaywallScreen.tsx:131`).
- **Auth required:** No.
- **User inputs:** None (subscribe button is a placeholder with no action).
- **Backend calls:** `GET /api/v1/usage/status` (`usageService.ts:37`, called from `PaywallScreen.tsx:41`).

## 1.11 ReferralLandingScreen
- **Export:** `SmartCompareApp/src/screens/ReferralLandingScreen.tsx:44` — `export default function ReferralLandingScreen`
- **Purpose:** Invitee landing page reached via deep link (`qaren://c/{token}?ref={code}` or `https://qaren.app/c/{token}`). Shows referrer name (privacy-gated), product preview, and "Start comparison" CTA.
- **Auth required:** No (explicitly pre-auth reachable — `App.tsx:207`).
- **Backend calls:** `GET /api/v1/referrals/invite/{token}?ref={code}` (`referralService.ts:123`).

## 1.12 InviteeQuizScreen
- **Export:** `SmartCompareApp/src/screens/InviteeQuizScreen.tsx:62` — `export default function InviteeQuizScreen`
- **Purpose:** 4-question personalization wizard for unauthenticated invitees. No PII stored pre-signup per design doc (`InviteeQuizScreen.tsx:9`).
- **Auth required:** No.
- **User inputs:**
  - Q1: Priority (one of 8 chip options).
  - Q2: Budget tier (budget/mid/premium radio).
  - Q3: Brand attitude (one of 3 radio options).
  - Q4: Non-negotiable free text (optional TextInput, maxLength=256 — `InviteeQuizScreen.tsx:317`).
- **Backend calls:** `POST /api/v1/referrals/invite/{token}/quiz` (priority, budget, brand_attitude, optional non_negotiable) (`referralService.ts:141`).

---

# SECTION 2: Permissions Declared in app.json

All permissions are declared in `SmartCompareApp/app.json` under the `plugins` array.

## 2.1 Camera Permission
- **Plugin:** `expo-camera` (`app.json:36–40`)
- **iOS Info.plist usage string (verbatim):** `"Qaren needs camera access to photograph products for comparison."`
- **Android equivalent:** Expo default for this plugin (uses `android.permission.CAMERA`).
- **Runtime trigger:** `HomeScreen.tsx:62` — `const [permission, requestPermission] = useCameraPermissions()`. Permission request shown when camera area is tapped with no prior grant. Text on request UI: "Camera Permission Needed / Qaren needs camera access to photograph products for comparison." (`HomeScreen.tsx:349`).

## 2.2 Photo Library Permission
- **Plugin:** `expo-image-picker` (`app.json:41–44`)
- **iOS Info.plist usage string (verbatim):** `"Qaren needs photo library access to identify products from your photos."`
- **Android equivalent:** Expo default for this plugin (uses `READ_EXTERNAL_STORAGE` / `READ_MEDIA_IMAGES` on Android 13+).
- **Runtime trigger:** `HomeScreen.tsx:141` — `ImagePicker.launchImageLibraryAsync(...)` called when user taps gallery button. Expo handles permission prompt before opening picker.

## 2.3 Secure Store
- **Plugin:** `expo-secure-store` (`app.json:33`) — no permission string (uses iOS Keychain / Android Keystore directly, no user-facing permission dialog).

## 2.4 Localization
- **Plugin:** `expo-localization` (`app.json:34`) — reads device locale, no user-facing permission dialog.

## 2.5 Google Sign-In
- **Plugin:** `@react-native-google-signin/google-signin` (`app.json:48–51`)
- **iOS URL scheme (verbatim):** `"com.googleusercontent.apps.21336192767-38hi4t1ac23089iau7jdog1f43oc7rdm"`
- **Android equivalent:** Expo default. No additional Android permission declared in app.json.

## 2.6 Apple Sign-In
- **Plugin:** `expo-apple-authentication` (`app.json:53`)
- **iOS setting:** `"usesAppleSignIn": true` (`app.json:18`)
- **iOS scopes requested at runtime:** `FULL_NAME` and `EMAIL` (`authService.ts:476–479`).
- **Android:** Not available (iOS only, gated at `Platform.OS === 'ios'` in `LoginScreen.tsx:45`).

## 2.7 Push Notifications
- **NOT listed as a plugin in app.json.** The SDK `expo-notifications` is in `package.json:33` but has no plugin entry. At runtime, `pushTokenService.ts:62–66` calls `Notifications.requestPermissionsAsync()` lazily (only if status is not already "granted"). Triggers on every authenticated app launch and login (`App.tsx:139`, `App.tsx:163`).
- **Android:** POST_NOTIFICATIONS permission is handled by the OS (Android 13+); Expo manages it.
- **⚠️ FLAG:** Plugin missing from app.json — at build time the `NSUserNotificationUsageDescription` (iOS) may not be auto-injected; risk for build/review.

## 2.8 Build Properties
- **Plugin:** `expo-build-properties` with `"networkInspector": false` (`app.json:55–61`) — disables the Expo network inspector in builds; no user-facing permission.

## 2.9 Confirmed ABSENT Permissions
The following were searched in `app.json` and `SmartCompareApp/src/` — none found:
- Location: not present in `app.json` plugins or any `src/` file.
- Microphone: not present.
- Contacts: not present.
- Calendar: not present.
- Bluetooth: not present.
- Advertising ID / IDFA: not present anywhere in `package.json` or `src/`.

---

# SECTION 3: Local Storage

## 3.1 expo-secure-store Writes (Sensitive/Cryptographic)

| Key | Content | File:Line |
|-----|---------|-----------|
| `@qaren_token` (constant `TOKEN_STORAGE_KEY`) | JWT access token (Supabase) | `authService.ts:290` — `SecureStore.setItemAsync(TOKEN_STORAGE_KEY, token)` |
| `@qaren_refresh_token` (constant `REFRESH_TOKEN_KEY`) | Supabase refresh token | `authService.ts:97` — `SecureStore.setItemAsync(REFRESH_TOKEN_KEY, ...)` |
| `qaren.demographicsPromptState.v1` | Demographics prompt state (hasSubmitted, dismissedCount, lastDismissedAt) — no demographic answers themselves | `demographicsTrigger.ts:72` — `SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(next))` |

**CLAUDE.md security pattern confirmed:** Access token and refresh token go to `expo-secure-store`, NOT AsyncStorage. Evidence: `authService.ts:279` — `getToken()` calls `SecureStore.getItemAsync(TOKEN_STORAGE_KEY)`; `authService.ts:289` — `saveToken()` calls `SecureStore.setItemAsync(TOKEN_STORAGE_KEY, token)`.

## 3.2 AsyncStorage Writes (Non-Sensitive Cache)

| Key | Content | File:Line |
|-----|---------|-----------|
| `@qaren_user` (constant `USER_STORAGE_KEY`) | User profile object (id, email, display_name, auth_provider, preferences_completed) — NOT the auth token | `authService.ts:268` — `AsyncStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))` |
| `@qaren_recent_searches` (constant `RECENT_SEARCHES_KEY`) | Array of up to 5 recent text search queries (strings) | `HomeScreen.tsx:113` — `AsyncStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated))` |
| `@qaren_language` (constant `LANGUAGE_KEY`) | Selected language string (`'en'` or `'ar'`) | `i18n/index.ts:13` — `AsyncStorage.setItem(LANGUAGE_KEY, lang)` |

**Note:** The user object stored in AsyncStorage includes email address and display name but explicitly excludes auth tokens (`authService.ts:304` comment: "User profile is non-secret"). On logout, `clearSession()` calls `AsyncStorage.removeItem(USER_STORAGE_KEY)` (`authService.ts:304`).

---

# SECTION 4: Network Calls

## 4.1 Base URL and Transport Security
- **Base URL:** `'https://web-production-58776.up.railway.app'` — `api.ts:13`.
- **Protocol:** HTTPS enforced (hardcoded `https://` scheme). All comparison, auth, feedback, and event API calls use this base.
- **Timeout:** 120,000 ms (2 minutes) for image processing (`api.ts:21`).

## 4.2 Certificate Pinning
- **Implementation:** `react-native-ssl-public-key-pinning` via `initializeSslPinning()` (`certificatePinning.ts:14`).
- **Pinned host:** `web-production-58776.up.railway.app` with `includeSubdomains: true` (`certificatePinning.ts:27`).
- **Pinned hashes (verbatim):**
  - `"iFvwVyJSxnQdyaUvUERIf+8qk7gRze3612JMwoO3zdU="` — Let's Encrypt E8 intermediate (`certificatePinning.ts:17`)
  - `"NYbU7PBwV4y9J67c4guWTki8FJ+uudrXL0a4V4aRcrg="` — Let's Encrypt E5 intermediate (`certificatePinning.ts:18`)
- **Caveat:** Pinning is a no-op in Expo Go (graceful degradation logged at `certificatePinning.ts:37`). Active only in native builds (EAS).

## 4.3 Direct Third-Party Calls (Not Routed Through Backend)

### Google Sign-In SDK
- **Library:** `@react-native-google-signin/google-signin` v16.1.2
- **Call location:** `authService.ts:404` — `gs.signIn()` calls Google's native OAuth flow directly on the device. The resulting `idToken` is then forwarded to the Qaren backend at `POST /api/v1/auth/social-login` (`authService.ts:414`).
- **Data sent to Google:** Device calls Google's OAuth service with the configured web client ID (`21336192767-i9prqks93nrdmb9rg7ho2v1md9bgqgsv.apps.googleusercontent.com` — `authService.ts:377`).
- **Data returned to app:** Google ID token (`idToken`) — forwarded to Qaren backend, not stored client-side.

### Apple Sign-In SDK
- **Library:** `expo-apple-authentication` v8.0.8
- **Call location:** `authService.ts:476` — `apple.signInAsync()` calls Apple's native `AuthenticationServices` framework.
- **Scopes requested:** `FULL_NAME` and `EMAIL` (`authService.ts:477–479`).
- **Data sent to Apple:** Cryptographic nonce (SHA256 of 32 random bytes — `authService.ts:471`). Apple returns `identityToken` which is forwarded to Qaren backend.
- **iOS only:** Gated by `Platform.OS === 'ios'` at `LoginScreen.tsx:45`.

### Expo Push Notification Token Registration
- **Library:** `expo-notifications` v0.32.17
- **Call location:** `pushTokenService.ts:78` — `Notifications.getExpoPushTokenAsync()` contacts Expo's push notification servers to obtain a device token in format `ExponentPushToken[...]`.
- **Data sent:** Device identifier to Expo's servers (standard Expo push service).
- **Data returned:** Expo push token string, which is then PUT to Qaren backend at `PUT /api/v1/auth/push-token` (`pushTokenService.ts:90`).
- **Trigger:** Called on every authenticated app launch and immediately after login/register (`App.tsx:139`, `App.tsx:163`).

---

# SECTION 5: Frontend SDKs

## 5.1 Packages That Transmit Data Off-Device

| Package | Version | Purpose | Transmits to |
|---------|---------|---------|-------------|
| `axios` | 1.13.4 | HTTP client for all Qaren backend API calls | `web-production-58776.up.railway.app` only |
| `@react-native-google-signin/google-signin` | 16.1.2 | Google OAuth native flow | Google OAuth servers (to obtain ID token forwarded to Qaren backend) |
| `expo-apple-authentication` | 8.0.8 | Apple Sign-In native flow | Apple AuthenticationServices (iOS only) |
| `expo-notifications` | 0.32.17 | Push notification permission + Expo push token fetch | Expo push servers (for token), then Qaren backend |
| `expo-localization` | 17.0.8 | Reads device locale (language/region) | Local read only — no transmission |
| `expo-camera` | 17.0.10 | Camera viewfinder and photo capture | Images sent to Qaren backend via `POST /api/v1/image/identify` |
| `expo-image-picker` | 17.0.10 | Photo library selection | Photos sent to Qaren backend via `POST /api/v1/image/identify` |
| `expo-image-manipulator` | 14.0.8 | JPEG transcode and resize before upload | Local processing only before upload to Qaren backend |
| `react-native-ssl-public-key-pinning` | 1.2.6 | SPKI certificate pinning for Qaren backend host | No data sent; intercepts connections |

## 5.2 Local-Only Packages (No Off-Device Transmission)

- `expo-secure-store` 15.0.8 — iOS Keychain / Android Keystore
- `expo-crypto` 15.0.8 — cryptographic nonce generation for OAuth flows
- `expo-haptics` 15.0.8 — device haptic feedback
- `expo-blur` 15.0.8 — UI blur effects
- `expo-image` 3.0.11 — image display
- `expo-media-library` 18.2.1 — imported in package.json but Cannot determine from code whether it is called at runtime in any screen (no `MediaLibrary` import found in src/)
- `expo-screen-capture` 8.0.9 — prevents screenshots on login/register/forgot-password screens
- `expo-status-bar` 3.0.9 — status bar styling
- `expo-build-properties` 1.0.10 — build-time configuration
- `@react-native-async-storage/async-storage` 2.2.0 — local non-sensitive cache
- `@react-navigation/native`, `@react-navigation/native-stack`, `@react-navigation/bottom-tabs` — navigation
- `react-native-reanimated` 4.1.1, `react-native-gesture-handler` 2.28.0 — animations/gestures
- `react-native-screens` 4.16.0, `react-native-safe-area-context` 5.6.0 — native screen management
- `react-native-svg` 15.12.1 — SVG rendering
- `react-native-paper` 5.15.0 — UI components
- `react-native-worklets` 0.5.1 — Reanimated worklets runtime
- `i18next` 26.0.1, `react-i18next` 17.0.1 — i18n
- `lucide-react-native` 1.7.0 — icons
- `@expo-google-fonts/cairo` 0.4.2, `@expo-google-fonts/inter` 0.4.2 — embedded fonts (no network call at runtime; fonts bundled)
- `react-native-vector-icons` 10.3.0 — icon library

## 5.3 Confirmed Absent SDKs

Searched `package.json` for all of the following — **none found (no matches)**:
- Firebase / `@react-native-firebase` / `firebase`
- Crashlytics
- Sentry (frontend SDK — `@sentry/react-native`)
- Mixpanel
- Amplitude
- AppsFlyer
- Adjust
- Meta SDK / Facebook SDK
- Google Ads SDK
- OneSignal
- RevenueCat
- Stripe
- Tap Payments / BenefitPay (paywall subscribe button is a placeholder — `PaywallScreen.tsx:131` comment)
- AppCheck
- Any advertising/attribution library (`IDFA`, `advertising-id`, `ATTrackingManager`)

---

# SECTION 6: Onboarding & Data Captured at Signup

## 6.1 OnboardingScreen Flow (6 Steps)

The wizard appears after the user's first successful login when `authUser.preferences_completed === false` (`App.tsx:135`). It can also be re-opened from ProfileScreen to edit preferences.

| Step | Question | Options | Required | Data Field |
|------|----------|---------|----------|-----------|
| 0 | Language selection | English / العربية | No (defaults to device language) | `selectedLanguage: 'en' \| 'ar'` — applied immediately via `switchLanguage()`, not sent to backend |
| 1 | Region / country | bahrain, saudi_arabia, uae, kuwait, qatar, oman (flags) | Yes (must select to proceed) | `region` — not sent to backend directly (only used to determine locale) |
| 2 | Shopping priorities (pick 1–3) | price, quality, brand_reputation, durability, latest_features, ease_of_use, eco_friendly, health_safety | Yes (1–3 required) | `priorities: string[]` |
| 3 | Budget tier | budget, mid, premium | Yes | `budget: 'budget' \| 'mid' \| 'premium'` |
| 4 | Lifestyle tags (any number) | gamer, photographer, fitness_enthusiast, vegan, sensitive_skin, parent, student, professional, outdoor_adventurer, minimalist, tech_enthusiast | No (step 4 always valid — `OnboardingScreen.tsx:74`) | `lifestyle: string[]` |
| 5 | Brand attitude | brand_loyal, function_first, best_of_both | Yes | `brandAttitude: string` |

## 6.2 Data Sent to Backend

**Step completion (step 5 "Complete" button):** `savePreferences()` is called at `OnboardingScreen.tsx:107`, which calls `PUT /api/v1/auth/preferences` via `api.ts:240`. Payload:
```
{
  priorities: string[],
  budget: "budget" | "mid" | "premium",
  lifestyle: string[],
  brand_attitude: string
}
```

**Note:** Region (step 1) and language (step 0) are NOT sent to the backend via this call. Region is used as a UI-only hint for display; language is stored locally in AsyncStorage at `@qaren_language` (`i18n/index.ts:13`). If the backend fails, the app silently proceeds with `onComplete()` (`OnboardingScreen.tsx:116`).

## 6.3 Post-Registration Demographics Collection (Optional, Separate from Onboarding)

After the first comparison result, authenticated users are shown `DemographicsBottomSheet` (`ResultsScreen.tsx:222–247`). This is a separate, optional prompt (not part of onboarding):
- **Fields:** age_group (18-24, 25-34, 35-44, 45-54, 55+), gender (Female, Male), governorate (Capital, Muharraq, Northern, Southern, Other). All default to "Prefer not to say" if not selected (`DemographicsBottomSheet.tsx:120`).
- **Auto-detected:** language (from device locale, never free-text — `DemographicsBottomSheet.tsx:72`).
- **Backend call:** `PUT /api/v1/auth/demographics` (`api.ts:452`).
- **Dismissal scheduling:** Stored in `expo-secure-store` at key `qaren.demographicsPromptState.v1` (`demographicsTrigger.ts:17`). Shows max 4 times, with 7-day cooldown after 3 dismissals. Never shown again after user submits.

## 6.4 AI Sharing and Notification Preferences (ProfileScreen)

Users can later toggle from ProfileScreen:
- **AI sharing enabled** (`ai_sharing_enabled: bool`) — default ON when undefined (`ProfileScreen.tsx:102`). Controls whether preferences influence the AI comparison prompt. Written via `PUT /api/v1/auth/preferences` (`ProfileScreen.tsx:129`).
- **Notifications master toggle** (`notifications_enabled: bool`) and 3 sub-types (`decision_insight`, `cohort_curiosity`, `decision_retrospective`) — written via `PUT /api/v1/auth/preferences` (`ProfileScreen.tsx:165`).

---

**Summary of native folder state:** No `ios/` or `android/` directories exist in `SmartCompareApp/` — confirmed by directory listing. This is an Expo managed workflow project. There are no `AndroidManifest.xml` or `Info.plist` files to read. All permissions are declared via Expo plugin configuration in `app.json`.
