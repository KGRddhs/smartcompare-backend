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
 * - cleared when the flow completes and on logout (ruling A6).
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

function parseRecord(raw: string | null): OnboardingResumeRecord | null {
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
  const age = Date.now() - savedAt;
  if (age < 0 || age > RESUME_TTL_MS) return null;
  if (!isObject(rec.data)) return null;
  const data = cleanData(rec.data);
  if (!data) return null;
  return { step: step as OnboardingStep, data };
}

let memo: Promise<OnboardingResumeRecord | null> | null = null;
let peekState: OnboardingResumePeek = { settled: false, value: null };

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
  memo = (async (): Promise<OnboardingResumeRecord | null> => {
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
    (value) => {
      peekState = { settled: true, value };
      return value;
    },
    () => {
      peekState = { settled: true, value: null };
      return null;
    },
  );
  return memo;
}

/** Synchronous view of the memoised read (`settled: false` before it resolves). */
export function peekOnboardingResume(): OnboardingResumePeek {
  return peekState;
}

/** Remove the record; never rejects. */
export async function clearOnboardingResume(): Promise<void> {
  try {
    await AsyncStorage.removeItem(ONBOARDING_RESUME_KEY);
  } catch {
    // best effort
  }
}
