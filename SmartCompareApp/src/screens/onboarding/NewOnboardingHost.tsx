/**
 * NewOnboardingHost — Phase 2 Task 24.
 *
 * Wraps the OnboardingFlow orchestrator and persists the collected data
 * (demographics + preferences + attribution) on completion. The persistence
 * is best-effort: any rejection is swallowed so the user is never stranded
 * mid-onboarding because the network had a hiccup.
 *
 * App.tsx mounts this only when `features.ENABLE_NEW_ONBOARDING` is true
 * and the user needs onboarding. Otherwise the legacy 6-step
 * OnboardingScreen is used. See `src/config/features.ts` for the flag.
 *
 * Three persistence buckets:
 * - `putDemographics` (Task 14 fields: country, governorate, age_group, gender)
 * - `savePreferences` (Task 15 fields: priorities, budget, brand_attitude)
 * - `saveAttribution` (Task 15 field: attribution_source)
 *
 * Each is independent — a failed save in one bucket does not block the others.
 */

import React, { useCallback } from 'react';
import { OnboardingFlow } from './OnboardingFlow';
import {
  OnboardingFlowData,
  OnboardingStep,
  OnboardingAttributionSource,
} from './types';
import {
  putDemographics,
  savePreferences,
  saveAttribution,
} from '../../services/api';

interface Props {
  /** Fired once persistence is best-effort done (never blocks on errors). */
  onComplete: (data: OnboardingFlowData) => void;
  /** Test/resume hook. */
  initialStep?: OnboardingStep;
  /** Test/resume hook. */
  initialData?: Partial<OnboardingFlowData>;
}

/**
 * Best-effort wrapper around an async API call. Logs in dev only and
 * never throws; ALL persistence on this screen is fire-and-forget.
 */
function safeFire<T>(promise: Promise<T>, label: string): Promise<void> {
  return promise.then(
    () => undefined,
    (err) => {
      if (__DEV__) {
        console.warn(`[NewOnboardingHost] ${label} persistence failed:`, err);
      }
    }
  );
}

export function NewOnboardingHost({ onComplete, initialStep, initialData }: Props) {
  const handleComplete = useCallback((data: OnboardingFlowData) => {
    // Demographics — only POST if the user supplied any values (skip-only
    // users, "Prefer not to say" everywhere, get an empty payload which
    // backend rejects). Backend accepts partials per CLAUDE.md.
    const demographicsPayload: Record<string, unknown> = {};
    if (data.country) demographicsPayload.country = data.country;
    if (data.governorate) demographicsPayload.governorate = data.governorate;
    if (data.age_group) demographicsPayload.age_group = data.age_group;
    if (data.gender) demographicsPayload.gender = data.gender;
    if (data.language) demographicsPayload.language = data.language;

    if (Object.keys(demographicsPayload).length > 0) {
      void safeFire(putDemographics(demographicsPayload as never), 'demographics');
    }

    // Preferences — `priorities` is required by the type, but backend
    // accepts partial. We only persist fields the user actually picked.
    if (
      data.priorities ||
      data.budget ||
      data.brand_attitude
    ) {
      const prefsPayload: Record<string, unknown> = {};
      if (data.priorities) prefsPayload.priorities = data.priorities;
      if (data.budget) prefsPayload.budget = data.budget;
      if (data.brand_attitude) prefsPayload.brand_attitude = data.brand_attitude;
      void safeFire(savePreferences(prefsPayload as never), 'preferences');
    }

    // Attribution — separate endpoint (Task 8).
    if (data.attribution_source) {
      void safeFire(
        saveAttribution(data.attribution_source as OnboardingAttributionSource),
        'attribution'
      );
    }

    // Always advance the user, even if the network is offline — the host
    // is presentation-glue; persistence is the network layer's problem.
    onComplete(data);
  }, [onComplete]);

  return (
    <OnboardingFlow
      onComplete={handleComplete}
      initialStep={initialStep}
      initialData={initialData}
    />
  );
}
