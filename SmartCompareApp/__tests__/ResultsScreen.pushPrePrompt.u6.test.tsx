/**
 * S69 U6 R3 fix-round — ResultsScreen's notifications pre-prompt, pinned
 * BEHAVIOURALLY (the .s69 suite only regex-scans this wiring: T3.17/T3.18).
 *
 * The 2s mount tick in ResultsScreen is the only automatic push ask for a
 * user who never saw onboarding Step 17, so a one-token regression there
 * silences every push-token registration for existing users. Each case
 * renders the real screen with fake timers and asserts what the user sees
 * at the 2s tick:
 *
 *   fresh compare, signed in, OS 'undetermined', nothing persisted -> shown
 *   opened from History / Smart pick (comparison_id)             -> hidden
 *   no result on screen when the tick fires (camera still loading,
 *     result lands later)                                        -> hidden
 *   demographics sheet shows on this mount                       -> hidden
 *   @qaren_push_preprompt_answered already persisted             -> hidden
 *   OS already asked (granted)                                   -> hidden
 *   signed out                                                   -> hidden
 *
 * Adversary mutants this kills: M8 (`false && showPushPrePrompt`), M12
 * (`fromHistory: false`), M13 (the `!resultRef.current` guard dropped).
 *
 * ResultsContent / DemographicsBottomSheet / ShareBottomSheet are stubbed
 * (the Reanimated results tree is not under test); PushPrePrompt is REAL,
 * so `push-preprompt` is the modal the user would see. Boundary mocks
 * otherwise mirror ResultsScreen.historyFloor.a17.test.tsx.
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const mockGetComparison = jest.fn();
const mockIdentifyFromImages = jest.fn();
const mockGetSavedUser = jest.fn();
const mockShouldShowDemographics = jest.fn();
const mockGetPermissionsAsync = jest.fn();
const mockRequestPermissionsAsync = jest.fn();

jest.mock('../src/services/api', () => ({
  getComparison: (...args: any[]) => mockGetComparison(...args),
  identifyFromImages: (...args: any[]) => mockIdentifyFromImages(...args),
  trackEvents: jest.fn().mockResolvedValue(undefined),
  submitFeedback: jest.fn().mockResolvedValue(undefined),
  shareComparison: jest.fn(),
  putDemographics: jest.fn().mockResolvedValue(undefined),
  parseApiError: jest.fn(() => ({ code: 'INTERNAL_ERROR', message: '' })),
}));

jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
  onSessionInvalid: jest.fn(() => () => undefined),
}));

jest.mock('../src/services/pushTokenService', () => ({
  tryRegisterPushToken: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../src/services/demographicsTrigger', () => ({
  loadDemographicsState: jest.fn().mockResolvedValue({ dismissedCount: 0 }),
  shouldShowDemographicsPrompt: (...args: any[]) => mockShouldShowDemographics(...args),
  recordDismissal: jest.fn().mockResolvedValue(undefined),
  recordSubmission: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('expo-notifications', () => ({
  getPermissionsAsync: (...args: any[]) => mockGetPermissionsAsync(...args),
  requestPermissionsAsync: (...args: any[]) => mockRequestPermissionsAsync(...args),
}));

jest.mock('../src/components/results/ResultsContent', () => {
  const { View } = require('react-native');
  return { ResultsContent: () => <View testID="results-content-stub" /> };
});

jest.mock('../src/components/DemographicsBottomSheet', () => {
  const { View } = require('react-native');
  return {
    __esModule: true,
    default: ({ visible }: { visible: boolean }) =>
      visible ? <View testID="demographics-sheet-stub" /> : null,
  };
});

jest.mock('../src/components/ShareBottomSheet', () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock('expo-localization', () => ({
  locale: 'en-US',
  getLocales: () => [{ languageCode: 'en', regionCode: 'BH' }],
}));

jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({ isRTL: false, language: 'en', setLanguage: jest.fn() }),
}));

jest.mock('../src/lib/performance/wallTimeInstrumentation', () => ({
  getWallTimeTracker: () => ({ mark: jest.fn(), report: jest.fn(), reset: jest.fn() }),
}));

import ResultsScreen from '../src/screens/ResultsScreen';
import { PUSH_PREPROMPT_ANSWERED_KEY } from '../src/services/pushPrePrompt';

const RESULT = {
  products: [{ name: 'Product A' }, { name: 'Product B' }],
  winner_index: 0,
  recommendation: 'Product A fits you better.',
} as any;

const makeNavigation = () =>
  ({ goBack: jest.fn(), navigate: jest.fn(), setOptions: jest.fn() }) as any;

const flush = async () => {
  await act(async () => {
    for (let i = 0; i < 8; i++) await Promise.resolve();
  });
};

/** Advance the fake clock by `ms`, draining microtasks on both sides. */
const tick = async (ms: number) => {
  await flush();
  await act(async () => {
    jest.advanceTimersByTime(ms);
  });
  await flush();
};

const renderResults = (params: Record<string, unknown>) =>
  render(<ResultsScreen route={{ params } as any} navigation={makeNavigation()} />);

describe('S69 U6 R3 — ResultsScreen shows the push pre-prompt once, after a fresh result', () => {
  beforeEach(async () => {
    jest.useFakeTimers();
    await AsyncStorage.clear();
    mockGetComparison.mockReset();
    mockIdentifyFromImages.mockReset();
    mockGetSavedUser.mockReset().mockResolvedValue({ id: 'user-1', email: 'u@example.com' });
    mockShouldShowDemographics.mockReset().mockReturnValue(false);
    mockGetPermissionsAsync
      .mockReset()
      .mockResolvedValue({ status: 'undetermined', granted: false });
    mockRequestPermissionsAsync.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('shows the pre-prompt at the 2s tick after a fresh compare result (never asks the OS itself)', async () => {
    const screen = renderResults({ result: RESULT });
    expect(screen.getByTestId('results-content-stub')).toBeTruthy();

    await tick(1900);
    expect(screen.queryByTestId('push-preprompt')).toBeNull();

    await tick(200);
    expect(screen.getByTestId('push-preprompt')).toBeTruthy();
    expect(mockRequestPermissionsAsync).not.toHaveBeenCalled();
  });

  it('stays hidden when Results was opened from History / Smart pick (comparison_id)', async () => {
    mockGetComparison.mockResolvedValue(RESULT);
    const screen = renderResults({ comparison_id: 'cmp-1' });

    await tick(100);
    // Guard: the history payload really is on screen, so "hidden" below is
    // the history rule and not an empty state.
    expect(screen.getByTestId('results-content-stub')).toBeTruthy();

    await tick(2500);
    expect(screen.queryByTestId('push-preprompt')).toBeNull();
  });

  it('stays hidden when no result is on screen at the tick, even once it lands later', async () => {
    // Camera path: identify+compare answers at 3s, after the 2s decision.
    mockIdentifyFromImages.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ action: 'comparison', result: RESULT }), 3000),
        ),
    );
    const screen = renderResults({ vision_products: ['file://a.jpg', 'file://b.jpg'] });

    await tick(2100);
    expect(screen.queryByTestId('results-loading-state')).toBeTruthy();
    expect(mockGetPermissionsAsync).not.toHaveBeenCalled();

    await tick(1500);
    expect(screen.getByTestId('results-content-stub')).toBeTruthy();
    expect(screen.queryByTestId('push-preprompt')).toBeNull();
  });

  it('stays hidden on the mount that shows the demographics sheet', async () => {
    mockShouldShowDemographics.mockReturnValue(true);
    const screen = renderResults({ result: RESULT });

    await tick(2100);
    expect(screen.getByTestId('demographics-sheet-stub')).toBeTruthy();
    expect(screen.queryByTestId('push-preprompt')).toBeNull();
  });

  it('stays hidden once an answer is persisted', async () => {
    await AsyncStorage.setItem(PUSH_PREPROMPT_ANSWERED_KEY, 'not_now');
    const screen = renderResults({ result: RESULT });

    await tick(2100);
    expect(screen.getByTestId('results-content-stub')).toBeTruthy();
    expect(screen.queryByTestId('push-preprompt')).toBeNull();
  });

  it('stays hidden when the OS was already asked', async () => {
    mockGetPermissionsAsync.mockResolvedValue({ status: 'granted', granted: true });
    const screen = renderResults({ result: RESULT });

    await tick(2100);
    expect(screen.queryByTestId('push-preprompt')).toBeNull();
  });

  it('stays hidden for a signed-out user', async () => {
    mockGetSavedUser.mockResolvedValue(null);
    const screen = renderResults({ result: RESULT });

    await tick(2100);
    expect(screen.queryByTestId('push-preprompt')).toBeNull();
    expect(mockGetPermissionsAsync).not.toHaveBeenCalled();
  });
});
