/**
 * Canary percentage-bucketing primitive (Tasks 47-48 rollout).
 *
 * Why: ENABLE_NEW_ONBOARDING is a frontend build-time const (features.ts)
 * not a Railway env var, so the plan's "set flag to 10% in Railway env"
 * doesn't apply. We need stable, deterministic per-user bucketing so a
 * canary at percent=10 picks the SAME 10% of users on every launch (no
 * flicker between flows mid-onboarding).
 *
 * Stability invariant: hashBucket(id, percent) is a pure function. Same
 * (id, percent) → same boolean, every call, every device. The percent
 * is a constant in features.ts that we change to ramp the canary
 * (10 → 50 → 100) via EAS Update; no app-store re-release needed.
 *
 * Anonymous-to-authed transition: pre-signup the helper uses a
 * device-id stored in expo-secure-store (created lazily once per
 * device); post-signup it switches to user.id. Onboarding happens
 * BEFORE signup, so device-id determines which onboarding flow shows.
 * The orchestrator (OnboardingFlow) persists step state, so a user
 * who somehow flips buckets mid-onboarding (rare race) still finishes
 * the flow they started.
 */

import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';

const DEVICE_ID_KEY = 'qaren_device_id_v1';

/**
 * djb2 hash — fast, deterministic, even-distribution for the canary
 * bucket use case. Cryptographic strength is not a security goal here
 * (no signing, no auth); we just need a stable mapping from id → 0..99.
 *
 * Returns a non-negative integer.
 */
export function djb2(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) {
    // hash * 33 + char
    h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  }
  // Coerce to non-negative 32-bit int — JS bitwise ops yield signed.
  return h >>> 0;
}

/**
 * Bucket `id` into the lowest `percent` percent of the 0-99 distribution.
 * - percent <= 0 → false (canary off — opposite of "everyone")
 * - percent >= 100 → true (everyone in)
 * - empty/null id → false (canary defaults off; safer to ship the
 *   legacy flow to a user we can't identify yet than the new one)
 */
export function hashBucket(id: string | null | undefined, percent: number): boolean {
  if (!id) return false;
  if (percent <= 0) return false;
  if (percent >= 100) return true;
  const bucket = djb2(id) % 100;
  return bucket < percent;
}

/**
 * Cached stable id for the current app session. Recomputed on cold start
 * but stable within a session. Resolves to:
 *   1. Authed user.id when available (set by setStableUserId after login).
 *   2. Persistent device-id from expo-secure-store, lazy-created on
 *      first call via Crypto.randomUUID().
 */
let _cachedId: string | null = null;

export async function getStableId(): Promise<string> {
  if (_cachedId) return _cachedId;

  try {
    let deviceId = await SecureStore.getItemAsync(DEVICE_ID_KEY);
    if (!deviceId) {
      deviceId = Crypto.randomUUID();
      await SecureStore.setItemAsync(DEVICE_ID_KEY, deviceId);
    }
    _cachedId = deviceId;
    return deviceId;
  } catch {
    // SecureStore unavailable (Expo Go on a sim with no keychain) →
    // fall back to an in-memory uuid that lasts for the session.
    const fallback = Crypto.randomUUID();
    _cachedId = fallback;
    return fallback;
  }
}

/**
 * Override the cached id with the authed user.id. Call this once after
 * login so the canary bucket follows the user across devices (same
 * user.id → same bucket on phone + tablet). Idempotent.
 */
export function setStableUserId(userId: string | null | undefined): void {
  if (userId && typeof userId === 'string' && userId.length > 0) {
    _cachedId = userId;
  }
}

/**
 * Test-only: clear the cached id so subsequent getStableId() re-resolves.
 * Production callers should never need this — the cache is invalidated
 * implicitly on cold start.
 */
export function _resetStableIdForTests(): void {
  _cachedId = null;
}
