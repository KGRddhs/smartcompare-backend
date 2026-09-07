/**
 * B9 — the Step-17 notifications answer must survive the tap that ends
 * onboarding, and must reach the backend.
 *
 * It was broken twice over:
 *
 *   1. Stale closure. The wiring was
 *      `setField('notifications_enabled', granted); handleNext();`, and
 *      `handleNext` was a useCallback closing over THIS render's `data`. At
 *      the terminal step it called `onComplete(data)` — the object from
 *      before the setState — so the answer never left the flow.
 *
 *   2. No transport. Even with (1) fixed, `buildPreferencesPayload` copied
 *      only priorities / budget / brand_attitude, so the field had no bucket
 *      to ride in. (That half is pinned in
 *      __tests__/services/onboardingDraft.test.ts.)
 *
 * Unset is not a harmless default: ProfileScreen renders the master toggle
 * from `notifications_enabled !== false` (unset shows ON) and
 * reengagement_service.py skips a user only on `is False` (unset stays
 * targetable), while App.tsx registers a push token on every authed launch.
 * So a user who tapped "Not now" kept a live token, a Profile toggle reading
 * ON, and full re-engagement eligibility.
 */
import React from 'react';
import { render, fireEvent, act, waitFor } from '@testing-library/react-native';

const requestPermissionsAsync = jest.fn();
jest.mock('expo-notifications', () => ({
  requestPermissionsAsync: (...args: any[]) => requestPermissionsAsync(...args),
  getPermissionsAsync: jest.fn(),
  getExpoPushTokenAsync: jest.fn(),
  setNotificationChannelAsync: jest.fn(),
  setNotificationHandler: jest.fn(),
  AndroidImportance: { DEFAULT: 3, HIGH: 4, MAX: 5, LOW: 2, MIN: 1 },
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string, opts?: any) => opts?.defaultValue ?? k }),
}));

jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({ isRTL: false, language: 'en', switchLanguage: jest.fn() }),
}));

const trackEvents = jest.fn().mockResolvedValue(undefined);
const putDemographics = jest.fn().mockResolvedValue({ success: true });
const savePreferences = jest.fn().mockResolvedValue({ success: true });
const saveAttribution = jest.fn().mockResolvedValue({ success: true });
jest.mock('../src/services/api', () => ({
  trackEvents: (...args: any[]) => trackEvents(...args),
  putDemographics: (...args: any[]) => putDemographics(...args),
  savePreferences: (...args: any[]) => savePreferences(...args),
  saveAttribution: (...args: any[]) => saveAttribution(...args),
}));

import { OnboardingFlow } from '../src/screens/onboarding/OnboardingFlow';
import { NewOnboardingHost } from '../src/screens/onboarding/NewOnboardingHost';
import type { OnboardingFlowData } from '../src/screens/onboarding/types';
import { _resetOnboardingDraftInternalsForTests } from '../src/services/onboardingDraft';

const seededData: Partial<OnboardingFlowData> = {
  language: 'en',
  country: 'BH',
  age_group: '25-34',
  gender: 'Male',
  priorities: ['quality'],
  budget: 'mid',
  brand_attitude: 'trust_known_brands',
  attribution_source: 'friend',
};

beforeEach(() => {
  jest.clearAllMocks();
  _resetOnboardingDraftInternalsForTests();
  requestPermissionsAsync.mockResolvedValue({ status: 'granted', granted: true });
});

describe('B9 — Step 17 hands its answer to onComplete', () => {
  it('"Not now" completes the flow with notifications_enabled === false', async () => {
    const onComplete = jest.fn();
    const screen = render(
      <OnboardingFlow
        onComplete={onComplete}
        initialStep={17}
        initialData={seededData}
        isAuthenticated
      />
    );
    expect(screen.getByTestId('onboarding-step-17')).toBeTruthy();

    await act(async () => {
      fireEvent.press(screen.getByTestId('s17-not-now'));
    });

    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onComplete.mock.calls[0][0]).toMatchObject({
      notifications_enabled: false,
    });
    // The rest of the answer set still rides along.
    expect(onComplete.mock.calls[0][0]).toMatchObject({ country: 'BH', budget: 'mid' });
  });

  it('"Allow" with an OS grant completes with notifications_enabled === true', async () => {
    const onComplete = jest.fn();
    const screen = render(
      <OnboardingFlow
        onComplete={onComplete}
        initialStep={17}
        initialData={seededData}
        isAuthenticated
      />
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId('s17-allow'));
    });

    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
    expect(onComplete.mock.calls[0][0]).toMatchObject({
      notifications_enabled: true,
    });
  });

  it('"Allow" that the OS denies completes with notifications_enabled === false', async () => {
    requestPermissionsAsync.mockResolvedValue({ status: 'denied', granted: false });
    const onComplete = jest.fn();
    const screen = render(
      <OnboardingFlow
        onComplete={onComplete}
        initialStep={17}
        initialData={seededData}
        isAuthenticated
      />
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId('s17-allow'));
    });

    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
    expect(onComplete.mock.calls[0][0]).toMatchObject({
      notifications_enabled: false,
    });
  });
});

describe('B9 — the answer reaches the backend, not just onComplete', () => {
  it('a "Not now" tap PUTs an explicit false in the preferences bucket', async () => {
    const screen = render(
      <NewOnboardingHost
        onComplete={jest.fn()}
        initialStep={17}
        initialData={seededData}
      />
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId('s17-not-now'));
    });

    await waitFor(() => expect(savePreferences).toHaveBeenCalledTimes(1));
    expect(savePreferences.mock.calls[0][0]).toMatchObject({
      notifications_enabled: false,
    });
  });
});
