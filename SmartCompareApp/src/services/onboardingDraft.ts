/**
 * Onboarding completion draft + retry — M18 MB-flows-04.
 *
 * The completion save used to be pure fire-and-forget: NewOnboardingHost
 * swallowed every rejection and advanced unconditionally, while the gate
 * that decides whether onboarding runs again (`users.preferences_completed`)
 * is only ever written by the savePreferences PUT. A single failed PUT
 * (offline, 400, stale-session 401) therefore advanced the user with
 * nothing stored server-side, and the next cold start re-ran all 17 steps
 * with every answer gone.
 *
 * This module makes the save survivable WITHOUT ever blocking the user —
 * the host still advances synchronously; everything here is background:
 *
 *   - `persistWithDraft(data)` writes a local AsyncStorage draft FIRST,
 *     then fires the three persistence buckets (demographics /
 *     preferences / attribution — each independent, each with one
 *     immediate retry), and clears the draft only when every non-empty
 *     bucket succeeded. On failure the draft stays and a foreground
 *     replay is armed.
 *   - `flushPendingOnboardingDraft()` replays a pending draft. The host
 *     calls it on mount (next cold start, since the server-side gate is
 *     still false), and an AppState listener calls it when the app
 *     returns to the foreground — so a flaky connection that recovers
 *     later still completes the save. On a successful mount replay the
 *     host auto-completes, sparing the user the 17-step re-run.
 *
 * Retry policy is deliberately timer-free (one immediate retry per
 * bucket, then rely on the foreground / next-launch replays): an offline
 * device does not recover in the 1-3s a backoff would cover, and real
 * timers dangling past component unmount are their own hazard.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { AppState } from 'react-native';
import {
  putDemographics,
  savePreferences,
  saveAttribution,
} from './api';
import type {
  OnboardingFlowData,
  OnboardingAttributionSource,
} from '../screens/onboarding/types';

/**
 * AsyncStorage key for the pending completion draft. Versioned so a
 * future shape change can migrate rather than mis-parse.
 * NOTE: `authService.logout()` clears this key on user-initiated logout
 * so a draft can never be replayed into a DIFFERENT account that later
 * signs in on the same device.
 */
export const ONBOARDING_DRAFT_KEY = '@qaren_onboarding_draft_v1';

/** Stored draft shape. */
export interface OnboardingDraft {
  data: Partial<OnboardingFlowData>;
  savedAt: number;
}

/** Result of a draft replay attempt. */
export interface DraftFlushResult {
  hadDraft: boolean;
  success: boolean;
  data?: Partial<OnboardingFlowData>;
}

/** Initial attempt + 1 immediate retry per bucket. */
const MAX_ATTEMPTS_PER_BUCKET = 2;

function devWarn(message: string, err?: unknown): void {
  if (__DEV__) {
    console.warn(`[onboardingDraft] ${message}`, err ?? '');
  }
}

// ---------------------------------------------------------------------------
// Bucket payload builders (mirrors the host's original inline construction —
// only fields the user actually picked are sent; backend accepts partials).
// ---------------------------------------------------------------------------

export function buildDemographicsPayload(
  data: Partial<OnboardingFlowData>
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  if (data.country) payload.country = data.country;
  if (data.governorate) payload.governorate = data.governorate;
  if (data.age_group) payload.age_group = data.age_group;
  if (data.gender) payload.gender = data.gender;
  if (data.language) payload.language = data.language;
  return payload;
}

export function buildPreferencesPayload(
  data: Partial<OnboardingFlowData>
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  if (data.priorities) payload.priorities = data.priorities;
  if (data.budget) payload.budget = data.budget;
  if (data.brand_attitude) payload.brand_attitude = data.brand_attitude;
  return payload;
}

// ---------------------------------------------------------------------------
// Draft storage primitives (every one swallows storage errors — a broken
// AsyncStorage must never break onboarding itself).
// ---------------------------------------------------------------------------

export async function saveOnboardingDraft(
  data: Partial<OnboardingFlowData>
): Promise<void> {
  try {
    const draft: OnboardingDraft = { data, savedAt: Date.now() };
    await AsyncStorage.setItem(ONBOARDING_DRAFT_KEY, JSON.stringify(draft));
  } catch (err) {
    devWarn('failed to write draft', err);
  }
}

export async function loadOnboardingDraft(): Promise<OnboardingDraft | null> {
  try {
    const raw = await AsyncStorage.getItem(ONBOARDING_DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as OnboardingDraft;
    if (!parsed || typeof parsed !== 'object' || typeof parsed.data !== 'object' || parsed.data === null) {
      return null;
    }
    return parsed;
  } catch (err) {
    devWarn('failed to read draft (treating as absent)', err);
    return null;
  }
}

export async function clearOnboardingDraft(): Promise<void> {
  try {
    await AsyncStorage.removeItem(ONBOARDING_DRAFT_KEY);
  } catch (err) {
    devWarn('failed to clear draft', err);
  }
}

// ---------------------------------------------------------------------------
// Persistence with retry
// ---------------------------------------------------------------------------

/**
 * Runs one bucket with up to MAX_ATTEMPTS_PER_BUCKET attempts. Resolves
 * true on success, false on exhaustion. Never rejects. A resolved
 * `{ success: false }` body counts as a failure (the server did not
 * store it), while an absent `success` field counts as success — the
 * legacy edit-mode contract resolves `{}`.
 */
async function attemptBucket(
  fire: () => Promise<{ success?: boolean } | void>,
  label: string
): Promise<boolean> {
  for (let attempt = 1; attempt <= MAX_ATTEMPTS_PER_BUCKET; attempt += 1) {
    try {
      const result = await fire();
      if (result && result.success === false) {
        throw new Error(`${label} responded success=false`);
      }
      return true;
    } catch (err) {
      devWarn(`${label} persistence attempt ${attempt} failed`, err);
    }
  }
  return false;
}

/**
 * Fires every bucket that has data (independently — a failed bucket does
 * not block the others). Resolves true only when EVERY fired bucket
 * succeeded; true immediately when nothing is persistable. Never rejects.
 */
export async function persistOnboardingBuckets(
  data: Partial<OnboardingFlowData>
): Promise<boolean> {
  const jobs: Array<Promise<boolean>> = [];

  const demographics = buildDemographicsPayload(data);
  if (Object.keys(demographics).length > 0) {
    jobs.push(
      attemptBucket(() => putDemographics(demographics as never), 'demographics')
    );
  }

  const preferences = buildPreferencesPayload(data);
  if (Object.keys(preferences).length > 0) {
    jobs.push(
      attemptBucket(() => savePreferences(preferences as never), 'preferences')
    );
  }

  if (data.attribution_source) {
    jobs.push(
      attemptBucket(
        () => saveAttribution(data.attribution_source as OnboardingAttributionSource),
        'attribution'
      )
    );
  }

  if (jobs.length === 0) return true;
  const results = await Promise.all(jobs);
  return results.every(Boolean);
}

/**
 * Completion-time entry point: draft first (so the answers are on disk
 * before any network attempt), then the buckets, then clear the draft on
 * full success. On failure the draft stays and the foreground replay is
 * armed. Never rejects — safe to `void` from the host.
 */
export async function persistWithDraft(
  data: Partial<OnboardingFlowData>
): Promise<boolean> {
  await saveOnboardingDraft(data);
  const ok = await persistOnboardingBuckets(data);
  if (ok) {
    await clearOnboardingDraft();
    disarmForegroundFlush();
  } else {
    armForegroundFlush();
  }
  return ok;
}

// ---------------------------------------------------------------------------
// Pending-draft replay (mount + foreground)
// ---------------------------------------------------------------------------

let inFlightFlush: Promise<DraftFlushResult> | null = null;

/**
 * Replays a pending draft if one exists. Deduped: overlapping callers
 * share one replay. Clears the draft (and the foreground listener) on
 * success; keeps both on failure. Never rejects.
 */
export function flushPendingOnboardingDraft(): Promise<DraftFlushResult> {
  if (inFlightFlush) return inFlightFlush;
  inFlightFlush = (async (): Promise<DraftFlushResult> => {
    try {
      const draft = await loadOnboardingDraft();
      if (!draft) return { hadDraft: false, success: false };
      const ok = await persistOnboardingBuckets(draft.data);
      if (ok) {
        await clearOnboardingDraft();
        disarmForegroundFlush();
      } else {
        armForegroundFlush();
      }
      return { hadDraft: true, success: ok, data: draft.data };
    } catch (err) {
      devWarn('draft flush failed unexpectedly', err);
      return { hadDraft: false, success: false };
    } finally {
      inFlightFlush = null;
    }
  })();
  return inFlightFlush;
}

// ---------------------------------------------------------------------------
// Foreground replay listener — armed only while a draft is pending, so a
// connection that recovers mid-session completes the save without waiting
// for the next cold start.
// ---------------------------------------------------------------------------

let appStateSubscription: { remove: () => void } | null = null;

function armForegroundFlush(): void {
  if (appStateSubscription) return;
  try {
    appStateSubscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        void flushPendingOnboardingDraft();
      }
    });
  } catch (err) {
    // AppState unavailable (bare test envs) — the mount replay still covers us.
    devWarn('could not arm foreground flush', err);
    appStateSubscription = null;
  }
}

function disarmForegroundFlush(): void {
  if (!appStateSubscription) return;
  try {
    appStateSubscription.remove();
  } catch {
    // ignore
  }
  appStateSubscription = null;
}

/** Test hook: reset module state between tests. */
export function _resetOnboardingDraftInternalsForTests(): void {
  disarmForegroundFlush();
  inFlightFlush = null;
}
