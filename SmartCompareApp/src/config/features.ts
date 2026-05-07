/**
 * Frontend feature flags.
 *
 * Plan revision (correcting stale plan task 47 step 1): we cannot
 * "set the flag to 10% in Railway env" because this is a frontend
 * build-time TypeScript const. The actual rollout knob is the
 * CANARY_NEW_ONBOARDING_PERCENT constant below; ramp it 10 → 50 → 100
 * via EAS Update (no app-store re-release).
 *
 * Pattern is reusable for future canaries: add a new flag + percent
 * pair. Each flag has its own getStableId() bucket call so different
 * canaries assign users independently (a user in the onboarding 10%
 * is not necessarily in another canary's 10%).
 */

import { hashBucket } from './featureBucket';

/**
 * Canary ramp constant. Change via EAS Update during rollout:
 *   - 0 → flag OFF for everyone (default)
 *   - 10 → 10% canary (Task 47)
 *   - 50 → 50% (Task 48 step 1)
 *   - 100 → everyone (Task 48 step 2; hold 7 days then remove legacy path)
 *
 * CURRENT: 10 (Task 47 — first canary cohort).
 */
export const CANARY_NEW_ONBOARDING_PERCENT = 10;

/**
 * Stable id resolved at app startup (App.tsx calls getStableId() once
 * and caches the result via setFlagStableId here). The features object
 * reads this synchronously per call — cheap because hashBucket is
 * O(len(id)) on a short uuid/jwt sub.
 */
let _stableIdForFlags: string | null = null;

/**
 * Init hook — call from App.tsx after `await getStableId()` resolves.
 * Idempotent. Safe to call multiple times; later calls override (e.g.
 * device-id → user.id transition on login).
 */
export function setFlagStableId(id: string | null | undefined): void {
  _stableIdForFlags = id || null;
}

/**
 * Test-only: clear the cached id so subsequent reads return false.
 */
export function _resetFlagStableIdForTests(): void {
  _stableIdForFlags = null;
}

/**
 * Frontend feature flags.
 *
 * Convention: every flag is a getter so it re-evaluates per call against
 * the current stable id + canary percent. Mutating setFlagStableId
 * during a session (e.g. on login) flips a user's bucket from
 * device-id-based to user-id-based; that's the intended behavior for
 * cross-device consistency post-signup.
 *
 * Canary plan (Tasks 47, 48):
 *   - Default: 0 percent → false everywhere
 *   - 10% canary: bump CANARY_NEW_ONBOARDING_PERCENT to 10, EAS Update
 *   - 50% → 100% over 7 days based on metrics
 */
export const features = {
  /**
   * Renders the new 17-step Cal-AI-Lite onboarding (Phase 2). When
   * false, the legacy 6-step OnboardingScreen is used. Bucketed by
   * stable id (device-id pre-signup, user.id post-signup) so a given
   * user always sees the same flow on the same percent setting.
   */
  get ENABLE_NEW_ONBOARDING(): boolean {
    return hashBucket(_stableIdForFlags, CANARY_NEW_ONBOARDING_PERCENT);
  },
} as const;

export type FeatureFlag = keyof typeof features;
