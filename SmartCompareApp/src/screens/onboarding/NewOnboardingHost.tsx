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
  /**
   * 'full' (default) — fresh-signup 17-step flow, calls `onComplete` to
   * advance the root navigator past the needs-preferences gate.
   * 'edit' — re-entry from Profile / EditProfile "Edit style profile";
   * jumps the user directly to the style steps (priorities → budget →
   * brand_attitude) and closes the modal via `onEditDone` instead of
   * touching the auth/preferences gate. Existing data on the screens is
   * still persisted via the same three buckets.
   */
  mode?: 'full' | 'edit';
  /**
   * Edit-mode close hook. Required when `mode === 'edit'`. App.tsx wires
   * this to `navigation.goBack()` so the user returns to Profile.
   */
  onEditDone?: () => void;
}

/** Style-profile edit flow — minimal subset that mirrors the design.
 *  Maps to priorities → budget → brand_attitude (steps 8/9/10). */
const EDIT_MODE_FIRST_STEP: OnboardingStep = 8;
const EDIT_MODE_LAST_STEP: OnboardingStep = 10;

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

export function NewOnboardingHost({
  onComplete,
  initialStep,
  initialData,
  mode = 'full',
  onEditDone,
}: Props) {
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
    // Edit-mode pops the modal back to Profile instead of running through
    // the auth/preferences gate of the full flow.
    if (mode === 'edit' && onEditDone) {
      onEditDone();
    } else {
      onComplete(data);
    }
  }, [onComplete, mode, onEditDone]);

  const effectiveInitialStep: OnboardingStep | undefined =
    mode === 'edit' ? (initialStep ?? EDIT_MODE_FIRST_STEP) : initialStep;
  const effectiveLastStep: OnboardingStep | undefined =
    mode === 'edit' ? EDIT_MODE_LAST_STEP : undefined;

  return (
    <OnboardingFlow
      onComplete={handleComplete}
      initialStep={effectiveInitialStep}
      initialData={initialData}
      lastStep={effectiveLastStep}
      // F-S2.step16-skip (task #42): NewOnboardingHost is only mounted
      // by App.tsx's `isAuthenticated && needsPreferences` branch — by
      // construction, any user reaching this host is already
      // authenticated. Hard-code `isAuthenticated={true}` here so the
      // orchestrator skips Step 16 ("Save your advisor — Sign in so
      // X") which is redundant in current production.
      //
      // If a future flow ever needs to mount NewOnboardingHost for an
      // anonymous user (e.g. anonymous-trial marketing surface),
      // promote this to a prop on NewOnboardingHostProps + thread it
      // through App.tsx. The OnboardingFlow prop already accepts
      // `false` as the original-17-step default.
      isAuthenticated={true}
    />
  );
}
