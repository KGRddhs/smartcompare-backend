/**
 * M18 MB-flows-04 — NewOnboardingHost completion persistence: local draft
 * + retry, without blocking the advance.
 *
 * Before this fix the host fired the three saves via `safeFire`
 * (swallowing every rejection) and advanced unconditionally, so a failed
 * preferences PUT left `preferences_completed` false server-side and the
 * next cold start re-ran all 17 onboarding steps with the answers lost.
 *
 * Contract pinned here:
 *   1. Completion writes a local draft and clears it once every save
 *      succeeds.
 *   2. When persistence keeps failing the user STILL advances (the
 *      deliberate advance-anyway behaviour is preserved), the save is
 *      retried, and the draft survives for a later replay.
 *   3. Mounting the full-mode host with a pending draft replays the
 *      saves; on success it auto-completes so the user is NOT forced
 *      through the 17 steps again.
 *   4. A failed mount replay keeps the draft and stays in the flow.
 *   5. Edit mode never touches the draft machinery.
 *
 * NOTE: the draft key is deliberately hardcoded (not imported) so this
 * file exercises the host behaviourally rather than through the service's
 * own constants.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { NewOnboardingHost } from '../../../src/screens/onboarding/NewOnboardingHost';

const DRAFT_KEY = '@qaren_onboarding_draft_v1';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

jest.mock('../../../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    language: 'en',
    isRTL: false,
    switchLanguage: jest.fn(),
  }),
}));

const putDemographicsMock = jest.fn();
const savePreferencesMock = jest.fn();
const saveAttributionMock = jest.fn();

jest.mock('../../../src/services/api', () => ({
  putDemographics: (...args: unknown[]) => putDemographicsMock(...args),
  savePreferences: (...args: unknown[]) => savePreferencesMock(...args),
  saveAttribution: (...args: unknown[]) => saveAttributionMock(...args),
  trackEvents: jest.fn().mockResolvedValue(undefined),
}));

const FULL_DATA = {
  country: 'BH' as const,
  age_group: '25-34' as const,
  priorities: ['quality_reliability'],
  budget: 'mid' as const,
  brand_attitude: 'best_of_both' as const,
  attribution_source: 'instagram' as const,
};

beforeEach(async () => {
  await AsyncStorage.clear();
  jest.clearAllMocks();
  putDemographicsMock.mockResolvedValue({ success: true, cohort_match: null });
  savePreferencesMock.mockResolvedValue({ success: true });
  saveAttributionMock.mockResolvedValue({ success: true });
});

function renderAtStep17(onComplete: jest.Mock) {
  return render(
    <NewOnboardingHost
      onComplete={onComplete}
      initialStep={17}
      initialData={FULL_DATA}
    />
  );
}

describe('NewOnboardingHost — completion draft + retry (MB-flows-04)', () => {
  it('writes a local draft on completion and clears it once every save succeeds', async () => {
    const onComplete = jest.fn();
    const { getByTestId } = renderAtStep17(onComplete);
    fireEvent.press(getByTestId('s17-not-now'));
    // Advance is still synchronous and unconditional.
    expect(onComplete).toHaveBeenCalledTimes(1);
    await waitFor(async () => {
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        DRAFT_KEY,
        expect.stringContaining('"country":"BH"')
      );
    });
    // All three buckets succeeded -> draft cleared.
    await waitFor(async () => {
      expect(await AsyncStorage.getItem(DRAFT_KEY)).toBeNull();
    });
  });

  it('still advances when persistence keeps failing, retries the save, and keeps the draft', async () => {
    putDemographicsMock.mockRejectedValue(new Error('network'));
    savePreferencesMock.mockRejectedValue(new Error('network'));
    saveAttributionMock.mockRejectedValue(new Error('network'));
    const onComplete = jest.fn();
    const { getByTestId } = renderAtStep17(onComplete);
    fireEvent.press(getByTestId('s17-not-now'));
    // The deliberate advance-anyway behaviour is preserved.
    expect(onComplete).toHaveBeenCalledTimes(1);
    // The preferences save was RETRIED (initial attempt + 1 retry).
    await waitFor(() => {
      expect(savePreferencesMock).toHaveBeenCalledTimes(2);
    });
    // The draft survives for the next-launch / next-foreground replay.
    const stored = await AsyncStorage.getItem(DRAFT_KEY);
    expect(stored).not.toBeNull();
    expect(stored).toContain('"budget":"mid"');
  });

  it('replays a pending draft on mount and auto-completes when the replay succeeds', async () => {
    await AsyncStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({ data: FULL_DATA, savedAt: 123 })
    );
    const onComplete = jest.fn();
    render(<NewOnboardingHost onComplete={onComplete} />);
    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledTimes(1);
    });
    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({ country: 'BH', budget: 'mid' })
    );
    expect(savePreferencesMock).toHaveBeenCalled();
    expect(await AsyncStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it('keeps the draft and stays in the flow when the mount replay fails', async () => {
    putDemographicsMock.mockRejectedValue(new Error('still offline'));
    savePreferencesMock.mockRejectedValue(new Error('still offline'));
    saveAttributionMock.mockRejectedValue(new Error('still offline'));
    await AsyncStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({ data: FULL_DATA, savedAt: 123 })
    );
    const onComplete = jest.fn();
    const { getByTestId } = render(<NewOnboardingHost onComplete={onComplete} />);
    await waitFor(() => {
      expect(savePreferencesMock).toHaveBeenCalled();
    });
    expect(onComplete).not.toHaveBeenCalled();
    // Still at step 1 of the flow; draft retained for the next attempt.
    expect(getByTestId('onboarding-step-1')).toBeTruthy();
    expect(await AsyncStorage.getItem(DRAFT_KEY)).not.toBeNull();
  });

  it('edit mode does not run the mount replay', async () => {
    await AsyncStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({ data: FULL_DATA, savedAt: 123 })
    );
    const onComplete = jest.fn();
    render(
      <NewOnboardingHost
        mode="edit"
        onComplete={onComplete}
        onEditDone={jest.fn()}
      />
    );
    // Give any (wrong) mount replay a chance to fire.
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(onComplete).not.toHaveBeenCalled();
    expect(putDemographicsMock).not.toHaveBeenCalled();
    expect(await AsyncStorage.getItem(DRAFT_KEY)).not.toBeNull();
  });
});
