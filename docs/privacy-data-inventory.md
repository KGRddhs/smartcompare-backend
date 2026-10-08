# Privacy data inventory (iOS `NSPrivacyCollectedDataTypes`)

Engineering-owned list of the data the Qaren mobile client (`SmartCompareApp/`) sends off the
device. It is the source for three things:

1. `SmartCompareApp/app.json` → `expo.ios.privacyManifests.NSPrivacyCollectedDataTypes`, which
   `expo prebuild` writes into `PrivacyInfo.xcprivacy` (through `withPrivacyInfo` /
   `mergePrivacyInfo` in `@expo/config-plugins`).
2. The App Store Connect privacy nutrition labels. Fill them in from this file, not from the
   privacy-policy text.
3. The legal redraft of `app/legal/privacy_policy.md` §2 (CLAUDE.md App-Store blocker #2).

**Keeping it in sync.** The JSON block at the end of this file is the literal
`NSPrivacyCollectedDataTypes` array. `SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts`
(c3) parses the first `json` fence in this file and deep-equals it to app.json's array after
sorting both by type. c5 parses every numbered row of the table below and requires its type,
Linked, Tracking and Purposes to equal the JSON block's entry for that type (and the row set to
equal the block's). Adding, removing or re-purposing a row means editing exactly two places:
this file (table and JSON block) and app.json. No test hard-codes the number of rows.

**Native-build only.** `app.json` changes reach phones through `eas build`, never through
`eas update`.

## Collected data types

All anchors are `SmartCompareApp/` paths at `b63a8368`. Every row has `Tracking = false`, which
matches `NSPrivacyTracking: false`. There is no ad SDK and no cross-app or cross-company linking.

| # | `NSPrivacyCollectedDataType…` | Where the client sends it (file:line) | Linked | Tracking | Purposes |
|---|---|---|---|---|---|
| 1 | `EmailAddress` | `src/services/authService.ts:121-150` register body `{ email, password, … }` → `POST /api/v1/auth/register`; `:193-196` login; `:624-626` password reset; social `id_token` (`:718` Google, `:868-872` Apple) carries the email claim | true | false | AppFunctionality |
| 2 | `Name` | `src/services/api.ts:432` `PUT /api/v1/auth/profile { display_name }`; `RegisterOptions.name` exists (`authService.ts:107-111`) but `RegisterScreen.tsx:222` does not pass it; Google `id_token` claims carry a name (derived on the backend) | true | false | AppFunctionality |
| 3 | `PhotosorVideos` | `src/services/api.ts:245-262` JPEG `FormData('images')` → `:285` `POST /api/v1/image/identify` (the policy §2.2 says processed, not stored) | true | false | AppFunctionality |
| 4 | `OtherUserContent` | typed product text `api.ts:856-862` `product_a` / `product_b` → `/api/v1/text/compare`; free text `change_suggestion` `api.ts:875-882` → `/api/v1/feedback` (product feedback; the Contact Us form also writes this field and is declared once, under row 13) | true | false | AppFunctionality, Analytics |
| 5 | `SearchHistory` | comparison queries are stored on the server and read back: `api.ts:366` `GET /api/v1/comparisons/history`, `:402` `GET /api/v1/comparisons/{id}` (the policy §2.2 names "search history"). Personalization (anchors at `89f2dc6a`): the home "smart pick" `app/api/home_routes.py:682` `GET /smart-pick` reads the user's last 5 stored comparisons (`:783-792`) and picks one by the user's priorities (`:796` `_select_smart_pick`). Analytics (anchors at `dfbda511`): the server logs each compare query to `search_logs` (`app/services/database_service.py:753` `log_search`), read by the admin dashboards `app/services/analytics_service.py:24` `get_daily_stats` and `:73` `get_popular_queries` (`app/api/admin_routes.py:70, :81`) | true | false | AppFunctionality, Analytics, ProductPersonalization |
| 6 | `UserID` | the account id is saved from `response.data.user` (`authService.ts:151-152` `saveUser`); feedback and events are keyed by `comparison_id` (`api.ts:877`, `:891`) | true | false | AppFunctionality, Analytics |
| 7 | `DeviceID` | `src/services/deviceFingerprint.ts:27-35` SHA-256 of `applicationId \| osBuildId \| random nonce` → `X-Device-Fingerprint` header (`authService.ts:148`) and `device_fingerprint_hash` (`src/components/ShareBottomSheet.tsx:159`); Expo push token `src/services/pushTokenService.ts:77` → `:90` `PUT /api/v1/auth/push-token { expo_push_token }` | true | false | AppFunctionality (Apple's App Functionality definition includes fraud prevention) |
| 8 | `ProductInteraction` | `api.ts:888-898` `trackEvents([{ event_type, event_data, comparison_id }])` → `POST /api/v1/events`; the `trackEvent` wrapper (`api.ts:914`) is called from e.g. `src/screens/HomeScreen.tsx:250, 324, 331, 338, 380, 498`. Personalization (anchors at `89f2dc6a`): `tab_switch` dwell events are read back (`app/services/structured_comparison_service.py:5221` `user_events`) into `behavior_profile.dimension_sensitivity` (`app/services/behavior_service.py:107-124`), which shifts the user's comparison scoring weights (`app/services/scoring_service.py:1402-1404` → `apply_behavioral_adjustments` `:2896-2932`) and is the fallback priority for the home smart pick (`app/api/home_routes.py:760-763`) | true | false | Analytics, ProductPersonalization |
| 9 | `CrashData` | `src/services/sentry.ts:235-245` `Sentry.init({ dsn, sendDefaultPii: false, tracesSampleRate: 0.1, beforeSend, beforeBreadcrumb, beforeSendTransaction })`. A fallback DSN is always set, so every build reports | true (conservative: no `Sentry.setUser` anywhere in `src`, but the SDK attaches a per-install device id) | false | AppFunctionality |
| 10 | `PerformanceData` | `sentry.ts:238` `tracesSampleRate: 0.1`; `src/lib/performance/wallTimeInstrumentation.ts` (imports `@sentry/react-native`) | true (same reason as row 9) | false | AppFunctionality, Analytics |
| 11 | `OtherDiagnosticData` | Sentry breadcrumbs and device context, scrubbed at `sentry.ts:243-245`; `authService.ts:692/752/777/789` `captureMessage` extras (token shape and error codes, no identity) | true (same reason as row 9) | false | AppFunctionality |
| 12 | `OtherDataTypes` | demographics `api.ts:996-1002` `{ age_group, gender, governorate, language, country }` → `:1044` `PUT /api/v1/auth/demographics`; preferences `src/types/types.ts:546-556` `{ priorities, budget, lifestyle, brand_attitude, ai_sharing_enabled, notifications_* }` → `api.ts:478` `PUT /api/v1/auth/preferences` | true | false | ProductPersonalization, AppFunctionality |
| 13 | `CustomerSupport` | the in-app Contact Us form (anchors at `89f2dc6a`): `src/screens/ContactUsScreen.tsx:84-96` composes `[category] subject` + message into `change_suggestion` → `POST /api/v1/feedback`; the request carries the signed-in user's bearer token (`src/services/api.ts:58`) | true | false | AppFunctionality |

## Not collected

Listed so the label is complete:

- **IP address.** Not collected today, on two conditions that must hold at submission time (PM-8): (1) the API is not fronted by Cloudflare — behind it, `_derive_country` would start storing an IP-derived country in `demographics_profile`, which makes **Coarse Location** declarable; (2) `ENABLE_PROXY_AWARE_RATELIMIT` stays OFF — ON, `admin_audit_log.ip_address` would hold the user's real client IP next to `user_id` instead of the Railway edge IP, which Apple counts as collecting IP address. Flip either and re-file the labels first.
- **Location, precise or coarse.** The region is a hard-coded `'bahrain'` string (`api.ts:240`,
  `:862`). No location API is imported.
- **Audio.** No audio or microphone API is used anywhere in `src/`, `App.tsx` or `index.ts`.
  `RECORD_AUDIO` is blocked on Android (`android.blockedPermissions` in app.json is the only
  guard). On iOS the build carries an `NSMicrophoneUsageDescription` that says audio is never
  recorded, because the installed `expo-camera` binary still links the capture-device audio API
  (session 69 U4a, finding EXPO-07). The app never asks for the microphone.
- **Contacts, payment info, phone number.**
- **Advertising data.** There is no ad SDK, and `NSPrivacyTracking` is `false`.
- **The Play install referrer.** `src/services/playInstallReferrerService.ts:24-36` reads it on
  the device, and it only feeds `setDeferredInviteCode` (`App.tsx:178-182`). What reaches the
  backend is the invite code (`authService.ts:146`), not the referrer string.

## Open before App Store submission

- **Identifier spelling.** Nothing installed here can check the type and purpose identifier
  strings. Every `PrivacyInfo.xcprivacy` shipped in `node_modules` has an empty collected-types
  array, and `mergePrivacyInfo` passes the strings through without checking them. A reviewer
  must compare them with Apple's "Describing data use in privacy manifests" page before merge.
  A typo would only show up when the build is uploaded to App Store Connect.
- **The `Linked` value on the Sentry rows (9-11)** is set conservatively to `true`. Legal may
  downgrade it.
- **Whether legal merges `SearchHistory` and `OtherUserContent`.** If they do, edit this file
  and app.json together.
- **`CustomerSupport` vs `OtherUserContent`.** The Contact Us form and product feedback share
  one backend field (`change_suggestion`). Session 69 U4a declares the form once, as
  `CustomerSupport` (row 13), and row 4 keeps typed products and product feedback. Legal may
  prefer a different split.

## Manifest array (machine-read — keep identical to app.json)

```json
[
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeEmailAddress",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeName",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypePhotosorVideos",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeOtherUserContent",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality",
      "NSPrivacyCollectedDataTypePurposeAnalytics"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeSearchHistory",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality",
      "NSPrivacyCollectedDataTypePurposeAnalytics",
      "NSPrivacyCollectedDataTypePurposeProductPersonalization"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeUserID",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality",
      "NSPrivacyCollectedDataTypePurposeAnalytics"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeDeviceID",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeProductInteraction",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAnalytics",
      "NSPrivacyCollectedDataTypePurposeProductPersonalization"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeCrashData",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypePerformanceData",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality",
      "NSPrivacyCollectedDataTypePurposeAnalytics"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeOtherDiagnosticData",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeOtherDataTypes",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeProductPersonalization",
      "NSPrivacyCollectedDataTypePurposeAppFunctionality"
    ]
  },
  {
    "NSPrivacyCollectedDataType": "NSPrivacyCollectedDataTypeCustomerSupport",
    "NSPrivacyCollectedDataTypeLinked": true,
    "NSPrivacyCollectedDataTypeTracking": false,
    "NSPrivacyCollectedDataTypePurposes": [
      "NSPrivacyCollectedDataTypePurposeAppFunctionality"
    ]
  }
]
```
