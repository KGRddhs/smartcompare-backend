/**
 * NewOnboardingHost — Phase 2 Task 24.
 *
 * Wraps the OnboardingFlow orchestrator and persists the collected data
 * (demographics + preferences + attribution) on completion. The persistence
 * never blocks the user: the host advances synchronously and the saves run
 * in the background.
 *
 * M18 MB-flows-04 — the saves are no longer fire-and-forget-and-lost.
 * `persistWithDraft` writes a local AsyncStorage draft BEFORE the network
 * attempts, retries each bucket once, and clears the draft only when every
 * bucket succeeded. The server-side gate (`users.preferences_completed`)
 * is written solely by the preferences PUT, so on failure the draft is the
 * recovery path: the next cold start re-mounts this host (gate still
 * false), the mount effect replays the draft, and on success the host
 * auto-completes — the user is NOT forced back through the 17 steps. An
 * AppState listener (armed by the service only while a draft is pending)
 * also replays when the app returns to the foreground mid-session.
 *
 * App.tsx mounts this only when `features.ENABLE_NEW_ONBOARDING` is true
 * and the user needs onboarding. Otherwise the legacy 6-step
 * OnboardingScreen is used. See `src/config/features.ts` for the flag.
 *
 * Three persistence buckets (built in `onboardingDraft.ts`):
 * - `putDemographics` (Task 14 fields: country, governorate, age_group, gender)
 * - `savePreferences` (Task 15 fields: priorities, budget, brand_attitude)
 * - `saveAttribution` (Task 15 field: attribution_source)
 *
 * Each is independent — a failed save in one bucket does not block the others.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { OnboardingFlow } from './OnboardingFlow';
import {
  OnboardingFlowData,
  OnboardingStep,
} from './types';
import {
  persistWithDraft,
  persistOnboardingBuckets,
  flushPendingOnboardingDraft,
} from '../../services/onboardingDraft';
import {
  loadOnboardingResume,
  peekOnboardingResume,
  clearOnboardingResume,
  type OnboardingResumeRecord,
} from '../../services/onboardingResume';

// S79 B3-A C3: queue the resume read at bundle evaluation. App.tsx imports
// this module statically, so the read starts before init()'s own reads and
// has usually settled by the time the host mounts. Never rejects; the record
// is single use (removed on read).
void loadOnboardingResume();

type ResumeView = { settled: boolean; value: OnboardingResumeRecord | null };

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

export function NewOnboardingHost({
  onComplete,
  initialStep,
  initialData,
  mode = 'full',
  onEditDone,
}: Props) {
  // S79 B3-A C3: resume after the language step's RTL reload. Only the full
  // flow with no explicit initialStep (App.tsx's mount) applies a record;
  // edit mode never does. Settled record -> mount at its step; settled
  // null -> today's step 1; not settled yet -> step 1 now, then remount
  // (key change) at the record's step when the read resolves.
  const resumeEligible = mode === 'full' && initialStep === undefined;
  const [resume, setResume] = useState<ResumeView>(() =>
    resumeEligible ? peekOnboardingResume() : { settled: true, value: null },
  );
  const resumeSettled = resume.settled;
  useEffect(() => {
    if (resumeSettled) return undefined;
    let cancelled = false;
    void loadOnboardingResume().then((value) => {
      if (!cancelled) setResume({ settled: true, value });
    });
    return () => {
      cancelled = true;
    };
  }, [resumeSettled]);
  const applied = resumeEligible && resume.settled ? resume.value : null;

  // Keep the latest onComplete reachable from the mount-replay effect
  // without re-running the effect when App.tsx passes a fresh closure.
  const onCompleteRef = useRef(onComplete);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  });

  // M18 MB-flows-04 — mount replay. The host only mounts in full mode
  // while the server-side gate is still false, so a pending draft here
  // means a previous completion never reached the backend. Replay it;
  // on success auto-complete so the user skips the redundant re-run.
  // On failure (still offline) the draft stays for a later attempt and
  // the user proceeds through the flow exactly as before this fix.
  useEffect(() => {
    if (mode !== 'full') return undefined;
    let cancelled = false;
    void flushPendingOnboardingDraft().then((result) => {
      if (!cancelled && result.hadDraft && result.success && result.data) {
        onCompleteRef.current(result.data as OnboardingFlowData);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [mode]);

  const handleComplete = useCallback((data: OnboardingFlowData) => {
    // Persistence buckets (demographics / preferences / attribution) are
    // built and fired inside the draft service — each independent, each
    // retried once, all rejections contained (both entry points below
    // never reject, so `void` is safe).
    //
    // Edit-mode pops the modal back to Profile instead of running through
    // the auth/preferences gate of the full flow. No draft in edit mode:
    // this host only re-mounts pre-gate, so an edit-mode draft could
    // never be replayed (and the gate is already set for these users) —
    // edit saves get the retry but stay best-effort.
    if (mode === 'edit' && onEditDone) {
      void persistOnboardingBuckets(data);
      onEditDone();
      return;
    }

    // Full flow: draft + retry, then advance — ALWAYS advance, even if
    // the network is offline. The draft (not the user's patience) is
    // what makes the save survive.
    void persistWithDraft(data);
    // S79 B3-A C3: a completed flow leaves no resume record behind.
    void clearOnboardingResume();
    onComplete(data);
  }, [onComplete, mode, onEditDone]);

  const effectiveInitialStep: OnboardingStep | undefined =
    mode === 'edit' ? (initialStep ?? EDIT_MODE_FIRST_STEP) : initialStep;
  const effectiveLastStep: OnboardingStep | undefined =
    mode === 'edit' ? EDIT_MODE_LAST_STEP : undefined;

  return (
    <OnboardingFlow
      key={applied ? `resume-${applied.step}` : 'fresh'}
      onComplete={handleComplete}
      initialStep={applied ? applied.step : effectiveInitialStep}
      initialData={applied ? { ...applied.data, ...(initialData ?? {}) } : initialData}
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
