/**
 * Push token registration (F5.4).
 *
 * Fetches the Expo push token and PUTs it to /api/v1/auth/push-token so
 * Loop 2 + re-engagement-cron can deliver — ONLY when notification
 * permission is ALREADY granted. Idempotent — safe to call on every app
 * launch post-auth. Backend write is RLS-protected.
 *
 * S69 U6 R3 (audit RT-12, App Review guideline 4.5.4): this function never
 * shows the system permission prompt. It runs on every authenticated launch
 * and right after login (App.tsx), where the prompt used to appear with no
 * explanation. The ask now lives behind an in-app explanation: onboarding
 * Step 17, or the one-time pre-prompt after a first result
 * (services/pushPrePrompt.ts), both of which call this after a grant.
 *
 * Graceful degradation:
 *   - Permission not granted       → no-op, no token registered
 *   - expo-notifications unavailable (Expo Go on Android, dev build
 *     missing the module) → swallowed, no crash
 *   - Network failure              → swallowed, no UI noise
 *
 * Loop 2 push will simply not deliver to users without a token; backend's
 * push_service.get_user_push_token returns None and the dispatcher
 * no-ops. So this function failing silently is the correct UX.
 */

import { api } from './api';

const REGISTERED_FLAG_KEY = '@qaren_push_token_registered';

export interface RegisterPushTokenResult {
  registered: boolean;
  reason?: 'no_module' | 'permission_denied' | 'network_error' | 'no_token' | 'already_registered';
}

let inFlight: Promise<RegisterPushTokenResult> | null = null;

/**
 * Idempotently register the device's Expo push token with the backend.
 * Returns a result object describing what happened — never throws.
 *
 * Coalesces concurrent calls (e.g. login + onLoginSuccess both trigger).
 */
export async function tryRegisterPushToken(): Promise<RegisterPushTokenResult> {
  if (inFlight) return inFlight;
  inFlight = doRegister().finally(() => {
    inFlight = null;
  });
  return inFlight;
}

async function doRegister(): Promise<RegisterPushTokenResult> {
  // 1. Lazy-import expo-notifications so a missing native module doesn't
  //    break app startup. Some EAS dev builds may strip the module if the
  //    plugin isn't configured; this also makes the module easier to mock
  //    in Jest without a global jest.mock().
  let Notifications: typeof import('expo-notifications');
  try {
    Notifications = require('expo-notifications');
  } catch (err) {
    if (__DEV__) console.warn('[pushToken] expo-notifications module unavailable', err);
    return { registered: false, reason: 'no_module' };
  }

  // 2. Permission check — read only. Undetermined or denied means no token;
  //    the in-app pre-prompt (Step 17 / pushPrePrompt) is the only place
  //    that asks the OS.
  try {
    const existing = await Notifications.getPermissionsAsync();
    if (existing?.status !== 'granted') {
      return { registered: false, reason: 'permission_denied' };
    }
  } catch (err) {
    if (__DEV__) console.warn('[pushToken] permission check failed', err);
    return { registered: false, reason: 'permission_denied' };
  }

  // 3. Fetch the Expo push token. Format: "ExponentPushToken[XXXX...]".
  let token: string;
  try {
    const tokenResp = await Notifications.getExpoPushTokenAsync();
    token = tokenResp?.data ?? '';
    if (!token) {
      return { registered: false, reason: 'no_token' };
    }
  } catch (err) {
    if (__DEV__) console.warn('[pushToken] getExpoPushTokenAsync failed', err);
    return { registered: false, reason: 'no_token' };
  }

  // 4. PUT to backend. The endpoint is idempotent so re-registration of
  //    the same token is a 200 no-op server-side.
  try {
    await api.put('/api/v1/auth/push-token', { expo_push_token: token });
    return { registered: true };
  } catch (err) {
    if (__DEV__) console.warn('[pushToken] PUT /push-token failed', err);
    return { registered: false, reason: 'network_error' };
  }
}

// Internal flag key exported for tests that want to reset state via mock storage.
export const PUSH_TOKEN_REGISTERED_KEY = REGISTERED_FLAG_KEY;
