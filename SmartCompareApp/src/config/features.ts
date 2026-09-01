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
 *   - 0 → flag OFF for everyone
 *   - 10 → 10% canary (target for App Store soft launch)
 *   - 50 → 50% (Task 48 step 1)
 *   - 100 → everyone (build/test mode + post-launch full rollout)
 *
 * CURRENT: 100 — pre-App Store build mode. Two human testers; bucketing
 * at <100% would statistically hide the new flow from them. MUST drop
 * back to 10 immediately before App Store soft-launch submission.
 * See runbook: docs/runbooks/qaren-canary-onboarding.md.
 */
export const CANARY_NEW_ONBOARDING_PERCENT = 100;

/**
 * #118 — SSE transport decision for streamComparison().
 *
 * React Native's global fetch (whatwg-fetch) has NO `response.body`
 * ReadableStream, so the old always-try-stream path threw on every device
 * call AFTER the backend had already run a full comparison, then fell back
 * to a SECOND full REST compare (double OpenAI + double Serper per tap).
 *
 *   false (shipped default) → Option B: never issue the stream request;
 *     go straight to the single REST compare. One backend request per tap.
 *   true → Option A: stream over `expo/fetch` (real ReadableStream +
 *     AbortSignal). Flip ONLY after a device check on an EAS preview build
 *     confirms certificate pinning still rejects a mismatched cert on both
 *     platforms — expo/fetch rides its own native HTTP client and may
 *     bypass the react-native-ssl-public-key-pinning hook on the one host
 *     we pin (see issue #118).
 *
 * Rollout knob: this constant, flipped via EAS Update (same shape as
 * CANARY_NEW_ONBOARDING_PERCENT above — RN has no per-call env flag).
 */
export const ENABLE_EXPO_FETCH_SSE_DEFAULT = false;

/**
 * Test-only override for ENABLE_EXPO_FETCH_SSE. `null` restores the
 * shipped constant. Mirrors _resetFlagStableIdForTests below.
 */
let _expoFetchSseOverride: boolean | null = null;
export function _setExpoFetchSseForTests(value: boolean | null): void {
  _expoFetchSseOverride = value;
}

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

  /**
   * #118 — when true, streamComparison() streams SSE over `expo/fetch`;
   * when false (default) it issues exactly one REST compare and never
   * attempts the stream. See ENABLE_EXPO_FETCH_SSE_DEFAULT above for the
   * flip preconditions (certificate-pinning device check).
   */
  get ENABLE_EXPO_FETCH_SSE(): boolean {
    return _expoFetchSseOverride ?? ENABLE_EXPO_FETCH_SSE_DEFAULT;
  },
} as const;

export type FeatureFlag = keyof typeof features;
