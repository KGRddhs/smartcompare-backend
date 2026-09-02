/**
 * M18 MB-flows-04 — onboarding completion draft + retry service.
 *
 * The completion save used to be pure fire-and-forget: `safeFire`
 * swallowed every rejection and the host advanced unconditionally, so a
 * failed preferences PUT left `preferences_completed` false server-side
 * and the next cold start re-ran all 17 steps with the answers gone.
 *
 * This service gives the save a local AsyncStorage draft plus a bounded
 * retry, WITHOUT ever blocking the user (the host still advances
 * synchronously; everything here is background work):
 *   - `persistWithDraft` writes the draft first, then fires the three
 *     buckets (each with one immediate retry), and clears the draft only
 *     when every non-empty bucket succeeded.
 *   - `flushPendingOnboardingDraft` replays a pending draft (host mount
 *     on the next cold start / app foreground) and reports whether the
 *     replay succeeded so the host can skip the redundant 17-step re-run.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const putDemographicsMock = jest.fn();
const savePreferencesMock = jest.fn();
const saveAttributionMock = jest.fn();

jest.mock('../../src/services/api', () => ({
  putDemographics: (...args: unknown[]) => putDemographicsMock(...args),
  savePreferences: (...args: unknown[]) => savePreferencesMock(...args),
  saveAttribution: (...args: unknown[]) => saveAttributionMock(...args),
}));

import {
  ONBOARDING_DRAFT_KEY,
  saveOnboardingDraft,
  loadOnboardingDraft,
  clearOnboardingDraft,
  persistOnboardingBuckets,
  persistWithDraft,
  flushPendingOnboardingDraft,
  _resetOnboardingDraftInternalsForTests,
} from '../../src/services/onboardingDraft';

const FULL_DATA = {
  country: 'BH' as const,
  governorate: 'Capital' as const,
  age_group: '25-34' as const,
  gender: 'Male' as const,
  language: 'en' as const,
  priorities: ['quality_reliability'],
  budget: 'mid' as const,
  brand_attitude: 'best_of_both' as const,
  attribution_source: 'instagram' as const,
};

beforeEach(async () => {
  await AsyncStorage.clear();
  jest.clearAllMocks();
  _resetOnboardingDraftInternalsForTests();
  putDemographicsMock.mockResolvedValue({ success: true, cohort_match: null });
  savePreferencesMock.mockResolvedValue({ success: true });
  saveAttributionMock.mockResolvedValue({ success: true });
});

describe('draft storage primitives', () => {
  it('round-trips a draft through AsyncStorage', async () => {
    await saveOnboardingDraft(FULL_DATA);
    const draft = await loadOnboardingDraft();
    expect(draft).not.toBeNull();
    expect(draft!.data.country).toBe('BH');
    expect(draft!.data.priorities).toEqual(['quality_reliability']);
    expect(typeof draft!.savedAt).toBe('number');
  });

  it('returns null when no draft is stored', async () => {
    expect(await loadOnboardingDraft()).toBeNull();
  });

  it('returns null (not a throw) on corrupt stored JSON', async () => {
    await AsyncStorage.setItem(ONBOARDING_DRAFT_KEY, 'not-json{{{');
    expect(await loadOnboardingDraft()).toBeNull();
  });

  it('clearOnboardingDraft removes the stored draft', async () => {
    await saveOnboardingDraft(FULL_DATA);
    await clearOnboardingDraft();
    expect(await loadOnboardingDraft()).toBeNull();
  });
});

describe('persistOnboardingBuckets', () => {
  it('fires only the buckets that have data and resolves true on success', async () => {
    const ok = await persistOnboardingBuckets({ country: 'BH' });
    expect(ok).toBe(true);
    expect(putDemographicsMock).toHaveBeenCalledTimes(1);
    expect(putDemographicsMock).toHaveBeenCalledWith({ country: 'BH' });
    expect(savePreferencesMock).not.toHaveBeenCalled();
    expect(saveAttributionMock).not.toHaveBeenCalled();
  });

  it('resolves true without any call when nothing is persistable', async () => {
    const ok = await persistOnboardingBuckets({ notifications_enabled: true });
    expect(ok).toBe(true);
    expect(putDemographicsMock).not.toHaveBeenCalled();
    expect(savePreferencesMock).not.toHaveBeenCalled();
    expect(saveAttributionMock).not.toHaveBeenCalled();
  });

  it('retries a failed bucket once and resolves true when the retry succeeds', async () => {
    savePreferencesMock
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ success: true });
    const ok = await persistOnboardingBuckets(FULL_DATA);
    expect(ok).toBe(true);
    expect(savePreferencesMock).toHaveBeenCalledTimes(2);
  });

  it('resolves false when a bucket keeps failing after the retry', async () => {
    savePreferencesMock.mockRejectedValue(new Error('network'));
    const ok = await persistOnboardingBuckets(FULL_DATA);
    expect(ok).toBe(false);
    expect(savePreferencesMock).toHaveBeenCalledTimes(2);
    // The other buckets are independent — they still fired.
    expect(putDemographicsMock).toHaveBeenCalled();
    expect(saveAttributionMock).toHaveBeenCalled();
  });

  it('treats a resolved { success: false } as a failure', async () => {
    savePreferencesMock.mockResolvedValue({ success: false, error: 'nope' });
    const ok = await persistOnboardingBuckets(FULL_DATA);
    expect(ok).toBe(false);
  });

  it('never rejects even when every bucket throws', async () => {
    putDemographicsMock.mockRejectedValue(new Error('a'));
    savePreferencesMock.mockRejectedValue(new Error('b'));
    saveAttributionMock.mockRejectedValue(new Error('c'));
    await expect(persistOnboardingBuckets(FULL_DATA)).resolves.toBe(false);
  });
});

describe('persistWithDraft', () => {
  it('clears the draft after all buckets succeed', async () => {
    const ok = await persistWithDraft(FULL_DATA);
    expect(ok).toBe(true);
    expect(await loadOnboardingDraft()).toBeNull();
  });

  it('keeps the draft when a bucket keeps failing', async () => {
    savePreferencesMock.mockRejectedValue(new Error('network'));
    const ok = await persistWithDraft(FULL_DATA);
    expect(ok).toBe(false);
    const draft = await loadOnboardingDraft();
    expect(draft).not.toBeNull();
    expect(draft!.data.budget).toBe('mid');
  });

  it('arms a foreground replay on failure; the replay completes the save when the app returns to foreground', async () => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { AppState } = require('react-native');
    savePreferencesMock.mockRejectedValue(new Error('offline'));
    await persistWithDraft(FULL_DATA);
    expect(await loadOnboardingDraft()).not.toBeNull();
    expect(AppState.addEventListener).toHaveBeenCalledWith('change', expect.any(Function));

    // Connection restored; user foregrounds the app.
    savePreferencesMock.mockResolvedValue({ success: true });
    AppState.__emit('active');
    // Join the in-flight (deduped) replay the emit kicked off.
    await flushPendingOnboardingDraft();
    expect(await loadOnboardingDraft()).toBeNull();
  });

  it('writes the draft BEFORE attempting the network saves', async () => {
    // If the process dies mid-save the draft must already be on disk.
    let draftAtCallTime: string | null = 'unset';
    savePreferencesMock.mockImplementation(async () => {
      draftAtCallTime = await AsyncStorage.getItem(ONBOARDING_DRAFT_KEY);
      return { success: true };
    });
    await persistWithDraft(FULL_DATA);
    expect(draftAtCallTime).not.toBeNull();
    expect(draftAtCallTime).not.toBe('unset');
  });
});

describe('flushPendingOnboardingDraft', () => {
  it('reports hadDraft=false when nothing is pending (and calls no API)', async () => {
    const res = await flushPendingOnboardingDraft();
    expect(res.hadDraft).toBe(false);
    expect(putDemographicsMock).not.toHaveBeenCalled();
  });

  it('replays a pending draft, clears it and returns its data on success', async () => {
    await saveOnboardingDraft(FULL_DATA);
    const res = await flushPendingOnboardingDraft();
    expect(res.hadDraft).toBe(true);
    expect(res.success).toBe(true);
    expect(res.data?.country).toBe('BH');
    expect(putDemographicsMock).toHaveBeenCalled();
    expect(savePreferencesMock).toHaveBeenCalled();
    expect(saveAttributionMock).toHaveBeenCalled();
    expect(await loadOnboardingDraft()).toBeNull();
  });

  it('keeps the draft when the replay fails', async () => {
    savePreferencesMock.mockRejectedValue(new Error('still offline'));
    await saveOnboardingDraft(FULL_DATA);
    const res = await flushPendingOnboardingDraft();
    expect(res.hadDraft).toBe(true);
    expect(res.success).toBe(false);
    expect(await loadOnboardingDraft()).not.toBeNull();
  });

  it('dedupes concurrent flushes (single replay for overlapping calls)', async () => {
    await saveOnboardingDraft(FULL_DATA);
    const [a, b] = await Promise.all([
      flushPendingOnboardingDraft(),
      flushPendingOnboardingDraft(),
    ]);
    expect(a.success).toBe(true);
    expect(b.success).toBe(true);
    // One replay, not two: each bucket fired exactly once.
    expect(savePreferencesMock).toHaveBeenCalledTimes(1);
  });
});
