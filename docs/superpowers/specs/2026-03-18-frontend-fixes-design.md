# Frontend Audit Fixes: Bugs, Share Integration, Error Handling, Cleanup

**Date:** 2026-03-18 (Session 24)
**Status:** Approved

## Problem

Frontend audit revealed 2 critical bugs (broken logout, broken navigation), missing backend connections (share endpoints, category banner), inconsistent error handling, and dead code. These must be fixed before UI redesign.

## Scope

8 fixes across frontend files only (no backend changes):

1. **AccountScreen logout bug** — doesn't call `onLogout()`, user stuck in MainNavigator
2. **HistoryScreen "Sign In" navigation bug** — routes to non-existent screen
3. **Share integration** — connect Share button to `POST /api/v1/share` + OS share sheet
4. **Category switched banner** — show info banner when category auto-corrected
5. **Unified error parsing** — `parseApiError()` utility, update all screens
6. **Dead code cleanup** — remove 5 unused api.ts functions
7. **User type consolidation** — fix duplicate User definitions
8. **PreferencesScreen lifestyle fix** — allow 0 lifestyle tags (was forcing 1+)

## Design

### 1. AccountScreen Logout Fix

**File:** `SmartCompareApp/src/screens/AccountScreen.tsx`

**Problem:** `handleLogout()` calls `clearSession()` then `navigation.reset()` to Home. But `isAuthenticated` in App.tsx is never set to `false`, so user stays in MainNavigator.

**Fix:** Add `onLogout` prop (same as HomeScreen). Replace `navigation.reset()` with `onLogout()`. App.tsx already passes `onLogout` to HomeScreen — add same prop to AccountScreen route.

**App.tsx change:** Pass `onLogout` callback to AccountScreen via `screenOptions` or route params.

### 2. HistoryScreen "Sign In" Navigation Fix

**File:** `SmartCompareApp/src/screens/HistoryScreen.tsx`

**Problem:** On 401, shows "Sign In Required" button that calls `navigation.navigate('Login')`. Login is in AuthNavigator, not MainNavigator — fails silently.

**Fix:** Replace with `onLogout()` pattern — clear session, let App.tsx swap to AuthNavigator. Same approach as fix #1.

### 3. Share Integration

**Files:** `SmartCompareApp/src/services/api.ts`, `SmartCompareApp/src/screens/ResultsScreen.tsx`

**New api.ts function:**
```typescript
export const shareComparison = async (comparisonId: string): Promise<{ share_token: string; share_url: string }> => {
  const response = await api.post(`/api/v1/share/${comparisonId}`);
  return response.data;
};
```

**ResultsScreen Share button flow:**
1. If authenticated AND comparison has an ID → call `shareComparison(id)` → get `share_url`
2. Open OS share sheet with: text summary + `\n\nView full comparison: ${share_url}`
3. If anonymous or no comparison ID → fall back to current text-only sharing
4. Track `share` event via `trackEvents()`

**Error handling:** If share API fails, fall back to text-only sharing (graceful degradation).

### 4. Category Switched Banner

**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

Add at top of results (before tabs):
```
If result.category_switched === true:
  Show info banner: "Category adjusted from {selected} to {category_used}"
  Blue/info background, dismissible with X button
```

Simple `View` with `Text` — no new component needed.

### 5. Unified Error Parsing

**File:** `SmartCompareApp/src/services/api.ts`

**New utility:**
```typescript
export function parseApiError(error: any): { message: string; code: string | null } {
  const data = error?.response?.data;
  if (data?.error) {
    return { message: data.error, code: data.code || null };
  }
  if (data?.detail) {
    return { message: typeof data.detail === 'string' ? data.detail : 'Invalid request', code: null };
  }
  if (error?.message) {
    return { message: error.message, code: null };
  }
  return { message: 'Something went wrong', code: null };
}
```

**Update all screens** to use `parseApiError()` instead of ad-hoc `error.response?.data?.detail`:
- HomeScreen (URL compare error, line ~146)
- LoginScreen (line ~101/112)
- RegisterScreen (login error handling)
- CameraScreen (lines ~163-177)
- AccountScreen (profile/email/password errors)
- HistoryScreen (already checks status code, add message parsing)
- ForgotPasswordScreen (error display)

**Internal code logic:** Use `code` field for:
- `AUTH_REQUIRED` → trigger logout/redirect
- `RATE_LIMITED` → show "Please try again in a minute"
- All others → show the `message` field

### 6. Dead Code Cleanup

**File:** `SmartCompareApp/src/services/api.ts`

Delete these functions (all call non-existent endpoints, none imported anywhere):
- `compareProducts()` (~80 lines)
- `quickCompare()` (~10 lines)
- `getRateLimitStatus()` (~4 lines)
- `getSubscriptionStatus()` (~4 lines)
- `debugUpload()` (~22 lines)

### 7. User Type Consolidation

**Files:** `authService.ts`, `types/types.ts`

Keep `User` in `authService.ts` as the auth-focused type (id, email, created_at, preferences_completed). Add `display_name` and `auth_provider` fields to match backend responses.

Remove or align `User` in `types.ts` — if it's used elsewhere with different fields (subscription_tier), keep it but rename to `UserProfile` to avoid confusion.

### 8. PreferencesScreen Lifestyle Fix

**File:** `SmartCompareApp/src/screens/PreferencesScreen.tsx`

Change `isStepValid()` for step 2 (lifestyle):
- From: `lifestyle.length >= 1`
- To: `true` (lifestyle is always valid, 0+ tags)

## Files Changed

| File | Changes |
|------|---------|
| `SmartCompareApp/src/screens/AccountScreen.tsx` | Add onLogout prop, fix logout handler |
| `SmartCompareApp/src/screens/HistoryScreen.tsx` | Fix "Sign In" button to use onLogout pattern |
| `SmartCompareApp/src/screens/ResultsScreen.tsx` | Share integration + category switched banner |
| `SmartCompareApp/src/screens/PreferencesScreen.tsx` | Lifestyle validation fix |
| `SmartCompareApp/src/screens/HomeScreen.tsx` | Use parseApiError() |
| `SmartCompareApp/src/screens/LoginScreen.tsx` | Use parseApiError() |
| `SmartCompareApp/src/screens/RegisterScreen.tsx` | Use parseApiError() |
| `SmartCompareApp/src/screens/CameraScreen.tsx` | Use parseApiError() |
| `SmartCompareApp/src/screens/ForgotPasswordScreen.tsx` | Use parseApiError() |
| `SmartCompareApp/src/services/api.ts` | Add shareComparison(), parseApiError(), delete 5 dead functions |
| `SmartCompareApp/src/services/authService.ts` | Add display_name, auth_provider to User type |
| `SmartCompareApp/App.tsx` | Pass onLogout to AccountScreen + HistoryScreen |

## Agent Team Strategy

**2 rounds of 2 Opus agents via TeamCreate.**

### Round 1: Critical Fixes + Error Handling
- **Agent A (frontend-core):** Fixes 1-2 (logout + nav bugs), fix 5 (parseApiError + update all screens), fix 6 (dead code), fix 8 (lifestyle)
- **Agent B (frontend-test):** TypeScript check after each fix. QA Agent A's work. Write edge-case verification.
- Cross-QA before dissolving.

### Round 2: Share + Banner + Type Cleanup
- **Agent A (frontend-share):** Fix 3 (share integration), fix 4 (category banner), fix 7 (User type)
- **Agent B (frontend-test2):** TypeScript check. QA. Verify all screens compile.
- Cross-QA before dissolving.

## Success Criteria

- [ ] AccountScreen logout clears auth state (no stuck-in-MainNavigator bug)
- [ ] HistoryScreen 401 redirects to login properly
- [ ] Share button generates backend link + opens OS share sheet
- [ ] Category switched banner shows when applicable
- [ ] All error messages use parseApiError() utility
- [ ] 5 dead api.ts functions removed
- [ ] User type consistent across files
- [ ] Lifestyle allows 0 selections
- [ ] `npx tsc --noEmit` passes with 0 errors
