/**
 * NewOnboardingHost tests — Phase 2 Task 24.
 *
 * The host component renders OnboardingFlow and on completion fires the
 * supplied onComplete (which the App router uses to transition to Main
 * or Auth). Persistence of demographics/preferences/attribution to the
 * backend is best-effort fire-and-forget; the host MUST still complete
 * even if the network calls fail (otherwise we strand the user).
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { NewOnboardingHost } from '../../../src/screens/onboarding/NewOnboardingHost';

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

const putDemographicsMock = jest.fn().mockResolvedValue({
  success: true,
  cohort_match: null,
});
const savePreferencesMock = jest.fn().mockResolvedValue({ success: true });
const saveAttributionMock = jest.fn().mockResolvedValue({ success: true });

jest.mock('../../../src/services/api', () => ({
  putDemographics: (...args: unknown[]) => putDemographicsMock(...args),
  savePreferences: (...args: unknown[]) => savePreferencesMock(...args),
  saveAttribution: (...args: unknown[]) => saveAttributionMock(...args),
}));

beforeEach(() => {
  putDemographicsMock.mockClear().mockResolvedValue({ success: true, cohort_match: null });
  savePreferencesMock.mockClear().mockResolvedValue({ success: true });
  saveAttributionMock.mockClear().mockResolvedValue({ success: true });
});

describe('NewOnboardingHost', () => {
  it('renders the OnboardingFlow at step 1 by default', () => {
    const { getByTestId } = render(<NewOnboardingHost onComplete={jest.fn()} />);
    expect(getByTestId('onboarding-step-1')).toBeTruthy();
  });

  it('still calls onComplete when the host advances past step 17', () => {
    const onComplete = jest.fn();
    const { getByTestId } = render(
      <NewOnboardingHost
        onComplete={onComplete}
        initialStep={17}
        initialData={{
          country: 'BH',
          age_group: '25-34',
          priorities: ['quality_reliability'],
          budget: 'mid',
          brand_attitude: 'best_of_both',
          attribution_source: 'instagram',
        }}
      />
    );
    fireEvent.press(getByTestId('onboarding-next'));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('calls onComplete even when persistence calls reject', async () => {
    putDemographicsMock.mockRejectedValue(new Error('network'));
    savePreferencesMock.mockRejectedValue(new Error('network'));
    saveAttributionMock.mockRejectedValue(new Error('network'));
    const onComplete = jest.fn();
    const { getByTestId } = render(
      <NewOnboardingHost
        onComplete={onComplete}
        initialStep={17}
        initialData={{
          country: 'BH',
          age_group: '25-34',
          priorities: ['quality_reliability'],
          budget: 'mid',
          brand_attitude: 'best_of_both',
          attribution_source: 'instagram',
        }}
      />
    );
    fireEvent.press(getByTestId('onboarding-next'));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});
