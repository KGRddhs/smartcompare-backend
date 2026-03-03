# Design: Account Panel, Social Auth, Image/History Bug Fixes

**Date:** 2026-03-03 (Session 15)
**Status:** Approved

## Overview

Seven items in one session: two bug fixes (image upload, history 401), one new screen (account settings), two social auth providers (Google, Apple), input validation across all forms, and EAS build fix.

## 1. Image Upload Bug Fix

**Problem:** OpenAI returns `invalid_image_format` (400) for ALL camera/gallery photos. The frontend renames HEIC extensions to `.jpg` but never transcodes the actual bytes. Backend magic-byte check falls through for HEIC, labels it as `image/jpeg`, and OpenAI rejects the mislabeled HEIC bytes.

**Fix — Frontend:**
- Add `expo-image-manipulator` dependency
- In `identifyFromImages()` (api.ts), run every image through `ImageManipulator.manipulateAsync()` with `[{ resize: { width: 1024 } }]` and `format: SaveFormat.JPEG, compress: 0.8`
- This guarantees actual JPEG bytes regardless of source format (HEIC, HEIF, PNG, etc.)
- Also reduces upload size (max 1024px width)

**Fix — Backend safety net:**
- Add HEIC/HEIF magic byte detection in `image_routes.py`
- If HEIC detected, return 400 with clear message: "HEIC format not supported, please use JPEG/PNG"
- Add GIF magic byte detection (`GIF87a` / `GIF89a`) for completeness

**Files changed:**
- `SmartCompareApp/src/services/api.ts` — add image transcoding before FormData
- `app/api/image_routes.py` — add HEIC detection + GIF detection

## 2. History 401 Bug Fix

**Problem:** `HistoryScreen.tsx` calls `getComparisonHistory()` which hits `GET /api/v1/comparisons/history` — an endpoint requiring `get_current_user()`. If the access token expired and refresh failed, it throws 401. The screen crashes with an unhandled error.

**Fix:**
- HistoryScreen: catch 401 specifically, show "Sign in to view history" message with a login button
- Verify the axios 401 interceptor is functioning (the Session 13 fix for `refresh_session()` should be working — confirm the backend still returns `user` in refresh response)
- `identifyFromImages()` uses `fetch()` not `axios` — add auth token header manually to keep session alive

**Files changed:**
- `SmartCompareApp/src/screens/HistoryScreen.tsx` — graceful 401 handling
- `SmartCompareApp/src/services/api.ts` — attach auth token to `fetch()` in `identifyFromImages()`

## 3. Account Settings Screen

**Design:** Single screen (`AccountScreen`) with inline editing. Accessible from home screen via gear/profile icon.

**Layout:**
```
[Profile Header]
  Avatar placeholder (initials circle)
  user@email.com
  Member since date

[Account Details]
  Display Name    [editable field]     [Save]
  Email           [editable field]     [Save]

[Security]
  Change Password  [>]  (opens modal)

[Connected Accounts]
  Google    [Connect / Connected]
  Apple     [Connect / Connected]

[Danger Zone]
  [Log Out]
```

**Password change modal:**
- Current password (required)
- New password (min 6 chars)
- Confirm new password (must match)
- Save / Cancel buttons

**Input validation (all forms across the app):**
- Name: 2-100 characters, trimmed, not empty
- Email: regex validation `^[^\s@]+@[^\s@]+\.[^\s@]+$`, backend validates via Supabase
- Password: min 6 characters (matches registration requirement)
- Confirm password: must match new password exactly
- All fields: trim whitespace, show inline error messages below field

**Backend endpoints (new):**
- `PUT /api/v1/auth/profile` — update display name in `users` table. Requires auth.
- `PUT /api/v1/auth/email` — update email via Supabase Auth (triggers verification email). Requires auth.
- `PUT /api/v1/auth/password` — change password. Requires current password + new password. Requires auth.

**Files changed:**
- `SmartCompareApp/src/screens/AccountScreen.tsx` — new file
- `SmartCompareApp/src/types.ts` — add AccountScreen to navigation types
- `SmartCompareApp/src/screens/HomeScreen.tsx` — add gear/profile icon to navigate to account
- `SmartCompareApp/src/services/api.ts` — add `updateProfile()`, `updateEmail()`, `changePassword()` functions
- `SmartCompareApp/src/services/authService.ts` — add helper for getting stored user data
- `app/api/auth_routes.py` — add 3 new endpoints
- `app/services/auth_service.py` — add update_profile(), update_email(), change_password() methods

## 4. Google Sign-In (Native SDK)

**Library:** `@react-native-google-signin/google-signin`

**Flow:**
1. User taps "Continue with Google" on Login/Register screen
2. Native Google sign-in sheet appears
3. User selects Google account
4. Library returns `idToken`
5. Frontend sends `idToken` to Supabase via `supabase.auth.signInWithIdToken({ provider: 'google', token: idToken })`
6. Supabase creates/links account, returns access_token + refresh_token
7. Frontend stores tokens (same as email/password flow)

**Configuration required:**
- Google Cloud Console: create OAuth 2.0 client IDs for iOS (bundle ID) and Android (SHA-1 fingerprint)
- Supabase dashboard: enable Google provider, paste Web client ID + secret
- `app.json`: add `@react-native-google-signin/google-signin` plugin with `iosUrlScheme`

**Backend changes:** None. Supabase handles OAuth server-side. Existing `get_current_user()` works with Google-issued JWTs.

**Files changed:**
- `SmartCompareApp/package.json` — add `@react-native-google-signin/google-signin`
- `SmartCompareApp/app.json` — add plugin config
- `SmartCompareApp/src/services/authService.ts` — add `signInWithGoogle()`
- `SmartCompareApp/src/screens/LoginScreen.tsx` — add Google button
- `SmartCompareApp/src/screens/RegisterScreen.tsx` — add Google button
- `SmartCompareApp/src/screens/AccountScreen.tsx` — add "Link Google" in connected accounts

## 5. Apple Sign-In (Native SDK)

**Library:** `expo-apple-authentication` (built into Expo SDK)

**Flow:**
1. User taps "Continue with Apple" on Login/Register screen
2. Native Apple sign-in sheet appears (iOS only)
3. User authenticates with Face ID / Touch ID
4. Library returns `identityToken`
5. Frontend sends token to Supabase via `supabase.auth.signInWithIdToken({ provider: 'apple', token: identityToken })`
6. Supabase creates/links account, returns access_token + refresh_token
7. Frontend stores tokens

**Configuration required:**
- Apple Developer account (deferred — will be purchased later)
- Enable "Sign in with Apple" capability
- Supabase dashboard: enable Apple provider, configure Service ID + key
- Note: Apple Sign-In button only shows on iOS (Apple requirement)

**Platform behavior:**
- iOS: native Apple sign-in sheet
- Android: hide Apple sign-in button (Apple doesn't support native Android sign-in well)

**Files changed:**
- `SmartCompareApp/package.json` — add `expo-apple-authentication` (if not already in SDK)
- `SmartCompareApp/app.json` — add Apple auth entitlement
- `SmartCompareApp/src/services/authService.ts` — add `signInWithApple()`
- `SmartCompareApp/src/screens/LoginScreen.tsx` — add Apple button (iOS only)
- `SmartCompareApp/src/screens/RegisterScreen.tsx` — add Apple button (iOS only)
- `SmartCompareApp/src/screens/AccountScreen.tsx` — add "Link Apple" in connected accounts

**Note:** Code will be built and ready but Apple Sign-In won't be fully testable until Apple Developer subscription is active. The button will be hidden/disabled until credentials are configured.

## 6. EAS Build Fix

**Problem:** `app.json` is missing `expo-camera` and `expo-image-picker` plugin entries, which breaks EAS builds.

**Fix:** Add the missing plugin configurations:
```json
{
  "plugins": [
    ["expo-camera", { "cameraPermission": "SmartCompare needs camera access to photograph products." }],
    ["expo-image-picker", { "photosPermission": "SmartCompare needs photo access to identify products." }],
    "@react-native-google-signin/google-signin"
  ]
}
```

**Files changed:**
- `SmartCompareApp/app.json` — add all missing plugins + new social auth plugins

## 7. Navigation Updates

- Add `AccountScreen` to `RootStackParamList` in types
- Add stack screen in App.tsx / navigation config
- HomeScreen: add settings/profile icon in header that navigates to AccountScreen
- AccountScreen: back button to return to HomeScreen

## Dependencies Added

| Package | Purpose |
|---------|---------|
| `expo-image-manipulator` | Image transcoding (HEIC → JPEG) |
| `@react-native-google-signin/google-signin` | Native Google sign-in |
| `expo-apple-authentication` | Native Apple sign-in (iOS) |
| `@supabase/supabase-js` | Direct Supabase client for OAuth (if not already present) |

## 8. Team Execution Strategy

**Agent team:** 3 Opus agents with `bypassPermissions`, circular cross-QA (same pattern as Sessions 9, 12, 14).

**Proposed team split:**

| Agent | Primary Work | QA Target |
|-------|-------------|-----------|
| Agent 1 (Backend) | Auth endpoints (profile/email/password), HEIC detection, backend safety nets | QAs Agent 3's work |
| Agent 2 (Frontend-Core) | AccountScreen, input validation, navigation, image transcoding fix, history 401 fix | QAs Agent 1's work |
| Agent 3 (Frontend-Auth) | Google sign-in, Apple sign-in, auth service updates, Login/Register screen buttons, EAS build fix | QAs Agent 2's work |

**Rules:**
- Features must be 100% complete before team is disbanded
- Each agent QAs another agent's work (circular: 1→3, 2→1, 3→2)
- If QA finds subpar or missed work, send it back for fixes
- Idle agents write red-green tests for new features (target: 80% coverage on new code)
- All agents are Opus (not Sonnet or Haiku)

**Test coverage targets:**
- New backend endpoints: unit tests for all 3 (profile, email, password)
- AccountScreen: component behavior tests
- Image transcoding: test HEIC/PNG/JPEG paths
- Social auth: mock tests for Google/Apple sign-in flows
- History 401: test graceful error handling

## Not In Scope

- Legacy `/api/v1/compare` route TypeErrors
- ResultsScreen type divergence from types.ts
- Apple Developer subscription purchase (deferred)
- Account deletion (can add later)
- Profile picture upload
