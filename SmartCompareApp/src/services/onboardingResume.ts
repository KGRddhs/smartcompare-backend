/**
 * Onboarding resume across the language step's RTL reload (S79 B3-A C3).
 *
 * Choosing a language whose direction differs from the current layout makes
 * `useLanguage.switchLanguage` call `Updates.reloadAsync()`, which restarts
 * the JS bundle and used to drop the user back on onboarding step 1. Right
 * before that reload, OnboardingFlow saves the step AFTER the language step
 * and the answers given so far; `NewOnboardingHost` reads the record once at
 * bundle evaluation and mounts the flow at that step.
 *
 * The record is per device, short-lived and single use:
 * - stored under `@qaren_onboarding_resume_v1` as
 *   `{ v: 1, step, data, saved_at }` (epoch ms);
 * - removed on every read, valid or not;
 * - valid only for `v === 1`, an integer step in 3..15 or 17 (never 1, 2 or
 *   16), `data.language` 'en' or 'ar', and an age in [0, RESUME_TTL_MS];
 * - `data` keeps only known OnboardingFlowData keys with valid values;
 * - cleared when the flow completes and on logout (ruling A6);
 * - single use in memory too (fix round FA1): a clear also resets the
 *   in-memory view (the memo goes, the peek becomes settled-null), the host
 *   consumes the record once it applies it, and RESUME_TTL_MS applies again
 *   at peek time from the privately kept `saved_at`.
 * Every exported function is fail-soft: none of them rejects or throws.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { OnboardingFlowData, OnboardingStep } from '../screens/onboarding/types';

export const ONBOARDING_RESUME_KEY = '@qaren_onboarding_resume_v1';
export const RESUME_TTL_MS = 10 * 60 * 1000;

export interface OnboardingResumeRecord {
  step: OnboardingStep;
  data: Partial<OnboardingFlowData>;
}

export interface OnboardingResumePeek {
  settled: boolean;
  value: OnboardingResumeRecord | null;
}

const RESUMABLE_STEPS: ReadonlySet<number> = new Set([3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17]);

/** The allowed values of each single-choice answer (types.ts unions). */
const CHOICES: Readonly<Record<string, readonly string[]>> = {
  country: ['BH', 'SA', 'AE', 'KW', 'QA', 'OM'],
  governorate: ['Capital', 'Muharraq', 'Northern', 'Southern'],
  age_group: ['18-24', '25-34', '35-44', '45-54', '55+'],
  gender: ['Male', 'Female'],
  budget: ['budget', 'mid', 'premium', 'luxury', 'top_tier'],
  brand_attitude: ['brand_loyal', 'function_first', 'best_of_both', 'trust_known_brands'],
  attribution_source: ['friend', 'instagram', 'tiktok', 'app_store', 'google', 'other'],
};

const MAX_PRIORITIES = 14;

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

/** Copy only the known answer keys whose values are valid. */
function cleanData(raw: Record<string, unknown>): Partial<OnboardingFlowData> | null {
  const language = raw.language;
  if (language !== 'en' && language !== 'ar') return null;
  const out: Record<string, unknown> = { language };
  for (const [key, allowed] of Object.entries(CHOICES)) {
    const v = raw[key];
    if (typeof v === 'string' && allowed.includes(v)) out[key] = v;
  }
  const priorities = raw.priorities;
  if (
    Array.isArray(priorities) &&
    priorities.length <= MAX_PRIORITIES &&
    priorities.every((p) => typeof p === 'string' && p.length > 0)
  ) {
    out.priorities = [...priorities];
  }
  if (typeof raw.notifications_enabled === 'boolean') {
    out.notifications_enabled = raw.notifications_enabled;
  }
  return out as Partial<OnboardingFlowData>;
}

/** A parsed record and its private `saved_at` (epoch ms), kept for the peek-time TTL. */
interface ParsedRecord {
  record: OnboardingResumeRecord;
  savedAt: number;
}

/** True while `savedAt` is within [0, RESUME_TTL_MS] of now. */
function withinTtl(savedAt: number): boolean {
  const age = Date.now() - savedAt;
  return age >= 0 && age <= RESUME_TTL_MS;
}

function parseRecord(raw: string | null): ParsedRecord | null {
  if (typeof raw !== 'string' || raw.length === 0) return null;
  let rec: unknown;
  try {
    rec = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isObject(rec) || rec.v !== 1) return null;
  const step = rec.step;
  if (typeof step !== 'number' || !Number.isInteger(step) || !RESUMABLE_STEPS.has(step)) return null;
  const savedAt = rec.saved_at;
  if (typeof savedAt !== 'number' || !Number.isFinite(savedAt)) return null;
  if (!withinTtl(savedAt)) return null;
  if (!isObject(rec.data)) return null;
  const data = cleanData(rec.data);
  if (!data) return null;
  return { record: { step: step as OnboardingStep, data }, savedAt };
}

let memo: Promise<OnboardingResumeRecord | null> | null = null;
let peekState: OnboardingResumePeek = { settled: false, value: null };
/** The `saved_at` of the settled record (null when there is none). */
let peekSavedAt: number | null = null;
/** Bumped by every reset, so a read that settles after a clear cannot republish its record. */
let generation = 0;

/**
 * Forget the in-memory record: the memo goes (the next load reads storage
 * again) and the peek becomes settled-null. Synchronous; never throws.
 */
function resetMemory(): void {
  generation += 1;
  memo = null;
  peekState = { settled: true, value: null };
  peekSavedAt = null;
}

/** Write the record; never rejects. */
export async function saveOnboardingResume(record: OnboardingResumeRecord): Promise<void> {
  try {
    await AsyncStorage.setItem(
      ONBOARDING_RESUME_KEY,
      JSON.stringify({ v: 1, step: record.step, data: record.data, saved_at: Date.now() }),
    );
  } catch {
    // best effort: without the record the flow restarts at step 1 (today)
  }
}

/**
 * Read, remove and validate the record. Memoised per JS context: every
 * caller gets the same promise, so the record is consumed exactly once per
 * bundle load. Never rejects.
 */
export function loadOnboardingResume(): Promise<OnboardingResumeRecord | null> {
  if (memo) return memo;
  const gen = generation;
  memo = (async (): Promise<ParsedRecord | null> => {
    let raw: string | null = null;
    try {
      raw = await AsyncStorage.getItem(ONBOARDING_RESUME_KEY);
    } catch {
      raw = null;
    }
    try {
      await AsyncStorage.removeItem(ONBOARDING_RESUME_KEY);
    } catch {
      // single use either way: this context never reads it again
    }
    return parseRecord(raw);
  })().then(
    (parsed) => {
      // A clear or consume that ran while the read was in flight wins.
      if (gen !== generation) return null;
      peekState = { settled: true, value: parsed ? parsed.record : null };
      peekSavedAt = parsed ? parsed.savedAt : null;
      return parsed ? parsed.record : null;
    },
    () => {
      if (gen !== generation) return null;
      peekState = { settled: true, value: null };
      peekSavedAt = null;
      return null;
    },
  );
  return memo;
}

/**
 * Synchronous view of the memoised read (`settled: false` before it
 * resolves). RESUME_TTL_MS applies again at peek time: a record read at
 * bundle evaluation but peeked after its TTL is `{ settled: true, value: null }`.
 */
export function peekOnboardingResume(): OnboardingResumePeek {
  if (peekState.settled && peekState.value && (peekSavedAt === null || !withinTtl(peekSavedAt))) {
    return { settled: true, value: null };
  }
  return peekState;
}

/**
 * Mark the record as applied: the in-memory view becomes settled-null, so a
 * later full-mode mount in the same JS context starts at step 1. Synchronous;
 * never throws. Storage is untouched (the read already removed the key).
 */
export function consumeOnboardingResume(): void {
  resetMemory();
}

/** Remove the record from memory and storage; never rejects. */
export async function clearOnboardingResume(): Promise<void> {
  resetMemory();
  try {
    await AsyncStorage.removeItem(ONBOARDING_RESUME_KEY);
  } catch {
    // best effort
  }
}
