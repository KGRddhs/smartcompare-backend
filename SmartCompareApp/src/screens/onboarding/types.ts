/**
 * Onboarding flow types — Phase 2.
 *
 * The new 17-step onboarding (Cal-AI-Lite) lives alongside the legacy
 * 6-step OnboardingScreen until Task 24 swaps the runtime route. This
 * type intentionally does NOT shadow `src/types/types.ts#OnboardingData`
 * (that one is the legacy 6-step shape used by the existing flow).
 *
 * See docs/plans/2026-05-06-qaren-ux-redesign-design.md Section 2 for
 * the screen map and the cohort-key value contract.
 */

/** All 17 step indices, 1-based to match design-spec screen numbers. */
export type OnboardingStep =
  | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9
  | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17;

/** GCC country code (matches backend `demographics.country` value set). */
export type OnboardingCountry = 'BH' | 'SA' | 'AE' | 'KW' | 'QA' | 'OM';

/** Bahrain governorate. Conditional sub-question on step 4. */
export type OnboardingGovernorate =
  | 'Capital'
  | 'Muharraq'
  | 'Northern'
  | 'Southern';

/**
 * Age group buckets — must match `cohort_priors.json` keys exactly per
 * CLAUDE.md ("cohort match is exact-case"). Do NOT lowercase.
 */
export type OnboardingAgeGroup =
  | '18-24'
  | '25-34'
  | '35-44'
  | '45-54'
  | '55+';

/** Gender — exact strings for cohort match. */
export type OnboardingGender = 'Male' | 'Female';

/** Budget tier — aligns with backend `_get_price_tier()`. */
export type OnboardingBudget = 'budget' | 'mid' | 'premium';

/**
 * Brand attitude — original 3 + the cohort-derived `trust_known_brands`
 * (CLAUDE.md "VALID_BRAND_ATTITUDE" enum).
 */
export type OnboardingBrandAttitude =
  | 'brand_loyal'
  | 'function_first'
  | 'best_of_both'
  | 'trust_known_brands';

/**
 * Attribution source — matches backend Pydantic enum on
 * POST /api/v1/auth/attribution (Task 8).
 */
export type OnboardingAttributionSource =
  | 'friend'
  | 'instagram'
  | 'tiktok'
  | 'app_store'
  | 'google'
  | 'other';

/** Accumulated user input from all 17 steps (every field optional during the flow). */
export interface OnboardingFlowData {
  // step 2 — language (also drives RTL)
  language?: 'en' | 'ar';
  // step 4 — country + conditional governorate when country === 'BH'
  country?: OnboardingCountry;
  governorate?: OnboardingGovernorate;
  // step 6 — age group
  age_group?: OnboardingAgeGroup;
  // step 7 — gender
  gender?: OnboardingGender;
  // step 8 — priorities (1-3 of 8 + 6 cohort enums; see CLAUDE.md VALID_PRIORITIES)
  priorities?: string[];
  // step 9 — budget tier
  budget?: OnboardingBudget;
  // step 10 — brand attitude
  brand_attitude?: OnboardingBrandAttitude;
  // step 11 — attribution
  attribution_source?: OnboardingAttributionSource;
  // step 17 — notification permission
  notifications_enabled?: boolean;
}

/** Last step in the flow. */
export const ONBOARDING_TOTAL_STEPS = 17 as const;
