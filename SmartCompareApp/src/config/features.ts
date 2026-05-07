/**
 * Frontend feature flags.
 *
 * Convention matches backend per CLAUDE.md ("all default OFF in code;
 * flip in Railway during canary"). For Phase 2 this is a build-time
 * const; remote config can replace this object later (e.g. via Supabase
 * remote_config table or expo-constants overrides).
 *
 * Canary plan (Tasks 47, 48):
 *   - Default: false everywhere
 *   - 10% canary: flip via build override or remote config
 *   - 50% → 100% over 7 days based on metrics
 */

export const features = {
  /**
   * Renders the new 17-step Cal-AI-Lite onboarding (Phase 2). When false,
   * the legacy 6-step OnboardingScreen is used. Default OFF for canary.
   * See docs/plans/2026-05-06-qaren-ux-redesign.md Tasks 47-48.
   */
  ENABLE_NEW_ONBOARDING: false as boolean,
} as const;

export type FeatureFlag = keyof typeof features;
