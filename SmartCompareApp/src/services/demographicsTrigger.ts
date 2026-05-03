/**
 * Demographics-prompt trigger logic and dismissal cooldown state.
 *
 * Schedule (per design doc Section 5.5):
 *   Sessions 1, 2, 3: show on each session until dismissed
 *   After 3 dismissals: 7-day cooldown
 *   4th attempt after 7 days
 *   Dismissed on 4th: never auto-prompt again
 *
 * State is persisted in expo-secure-store (consistent with auth tokens).
 */

import * as SecureStore from 'expo-secure-store';

export const COOLDOWN_DAYS = 7;
export const MAX_AUTO_ATTEMPTS = 4;
const STORAGE_KEY = 'qaren.demographicsPromptState.v1';

const DAY_MS = 1000 * 60 * 60 * 24;

export interface DemographicsState {
  hasSubmitted: boolean;
  dismissedCount: number;
  lastDismissedAt: Date | null;
}

export interface TriggerInput extends DemographicsState {
  /** 1-based count of sessions where the user has reached the results screen. */
  currentSessionIndex: number;
}

/**
 * Pure decision function. Determines whether to show the demographics
 * bottom sheet based on the user's history.
 */
export function shouldShowDemographicsPrompt(state: TriggerInput): boolean {
  if (state.hasSubmitted) return false;
  if (state.dismissedCount >= MAX_AUTO_ATTEMPTS) return false;

  if (state.dismissedCount === 0) {
    return state.currentSessionIndex >= 1;
  }

  if (state.dismissedCount < 3) {
    return state.currentSessionIndex > state.dismissedCount;
  }

  // dismissedCount === 3 → require 7-day cooldown before attempt #4
  if (!state.lastDismissedAt) return false;
  const daysSince =
    (Date.now() - state.lastDismissedAt.getTime()) / DAY_MS;
  return daysSince >= COOLDOWN_DAYS;
}

interface StoredShape {
  hasSubmitted?: boolean;
  dismissedCount?: number;
  lastDismissedAt?: string | null;
}

async function readState(): Promise<StoredShape> {
  try {
    const raw = await SecureStore.getItemAsync(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

async function writeState(next: StoredShape): Promise<void> {
  try {
    await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // best-effort persistence; transient SecureStore failures shouldn't crash
  }
}

export async function loadDemographicsState(): Promise<DemographicsState> {
  const raw = await readState();
  return {
    hasSubmitted: raw.hasSubmitted === true,
    dismissedCount: typeof raw.dismissedCount === 'number' ? raw.dismissedCount : 0,
    lastDismissedAt: raw.lastDismissedAt ? new Date(raw.lastDismissedAt) : null,
  };
}

export async function recordDismissal(): Promise<void> {
  const current = await readState();
  const nextCount = (current.dismissedCount ?? 0) + 1;
  await writeState({
    ...current,
    dismissedCount: nextCount,
    lastDismissedAt: new Date().toISOString(),
  });
}

export async function recordSubmission(): Promise<void> {
  const current = await readState();
  await writeState({
    ...current,
    hasSubmitted: true,
  });
}

/**
 * Test-only helper: clears stored state. Should not be called from app code.
 */
export async function _resetDemographicsState(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(STORAGE_KEY);
  } catch {
    // ignore
  }
}
