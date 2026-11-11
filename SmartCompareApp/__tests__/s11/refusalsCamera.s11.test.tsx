/**
 * S81-11 RED -- the camera refusal states (spec 2.3, C14; R-A6 kept for the
 * unreadable-photo cases).
 *
 * /image/identify answers HTTP 200 with action 'error' for the S81-10 gate
 * (category_gate.camera_refusal_body / camera_budget_body). After this OTA
 * the code is readable: CATEGORY_NOT_LIVE -> results-category-not-live-state
 * (title home.categories.fragrancesOnly, body home.errors.categoryNotLive,
 * the neutral Back CTA; never the retry, never the Paywall, no re-send);
 * reason same_identity / category_conflict -> results-reason-state; every
 * other action 'error' (incl. placeholder_identity / low_confidence) keeps
 * today's vision_failed state.
 *
 * Harness = screens/camera.engineUnavailable.s69.test.tsx (the global
 * react-i18next mock echoes keys).
 */

import React from 'react';
import { render, act, fireEvent } from '@testing-library/react-native';

const mockGetComparison = jest.fn();
const mockIdentifyFromImages = jest.fn();

jest.mock('../../src/services/api', () => ({
  getComparison: (...args: any[]) => mockGetComparison(...args),
  identifyFromImages: (...args: any[]) => mockIdentifyFromImages(...args),
  trackEvents: jest.fn().mockResolvedValue(undefined),
  submitFeedback: jest.fn().mockResolvedValue(undefined),
  parseApiError: jest.fn(() => ({ code: null, message: '' })),
}));

jest.mock('../../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
  getSavedUser: jest.fn().mockResolvedValue(null),
  onSessionInvalid: jest.fn(() => () => undefined),
}));

jest.mock('../../src/services/demographicsTrigger', () => ({
  loadDemographicsState: jest.fn().mockResolvedValue({}),
  shouldShowDemographicsPrompt: jest.fn().mockReturnValue(false),
  recordDismissal: jest.fn().mockResolvedValue(undefined),
  recordSubmission: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('expo-localization', () => ({
  locale: 'en-US',
  getLocales: () => [{ languageCode: 'en', regionCode: 'BH' }],
}));

jest.mock('../../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    isRTL: false,
    language: 'en',
    setLanguage: jest.fn(),
  }),
}));

jest.mock('../../src/lib/performance/wallTimeInstrumentation', () => ({
  getWallTimeTracker: () => ({
    mark: jest.fn(),
    report: jest.fn(),
    reset: jest.fn(),
  }),
}));

import ResultsScreen from '../../src/screens/ResultsScreen';

const makeNavigation = () =>
  ({
    goBack: jest.fn(),
    navigate: jest.fn(),
    setOptions: jest.fn(),
  }) as any;

const flush = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
};

const tick = async (ms: number) => {
  await flush();
  await act(async () => {
    jest.advanceTimersByTime(ms);
  });
  await flush();
};

async function renderCamera(navigation = makeNavigation()) {
  const rendered = render(
    <ResultsScreen
      route={{ params: { vision_products: ['file://a.jpg', 'file://b.jpg'] } } as any}
      navigation={navigation}
    />,
  );
  await tick(1500);
  return { rendered, navigation };
}

/** category_gate.camera_refusal_body (HTTP 200), synthetic values. */
const REFUSAL_BODY = {
  success: false,
  action: 'error',
  error: 'We compare fragrances for now.',
  code: 'CATEGORY_NOT_LIVE',
  category: 'electronics',
  categories_live: ['fragrances'],
  vision_cost: 0.001,
};

/** category_gate.camera_budget_body (HTTP 200), synthetic values. */
const BUDGET_BODY = {
  success: false,
  action: 'error',
  error: 'Daily refusal budget reached.',
  code: 'CATEGORY_NOT_LIVE',
  scope: 'refusal_daily',
  retry_after_seconds: 3600,
  resets_at: '2026-11-06T21:00:00Z',
  categories_live: ['fragrances'],
};

function expectNoRetryNoPaywall(rendered: any, navigation: any) {
  expect(rendered.queryByTestId('results-timeout-state')).toBeNull();
  expect(rendered.queryByTestId('results-timeout-retry')).toBeNull();
  expect(rendered.queryByText('results.emptyState.visionFailed')).toBeNull();
  expect(navigation.navigate).not.toHaveBeenCalledWith('Paywall', expect.anything());
  expect(navigation.navigate).not.toHaveBeenCalledWith('Paywall');
  expect(mockIdentifyFromImages).toHaveBeenCalledTimes(1);
}

describe('S81-11 C4 -- camera CATEGORY_NOT_LIVE (refusal + budget bodies)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockGetComparison.mockReset();
    mockIdentifyFromImages.mockReset();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  for (const [name, body] of [
    ['camera_refusal_body', REFUSAL_BODY],
    ['camera_budget_body', BUDGET_BODY],
  ] as const) {
    it(`${name} -> results-category-not-live-state with the two strings and Back`, async () => {
      mockIdentifyFromImages.mockResolvedValue(body);
      const { rendered, navigation } = await renderCamera();
      expect(rendered.queryByTestId('results-category-not-live-state')).not.toBeNull();
      expect(rendered.queryByText('home.categories.fragrancesOnly')).not.toBeNull();
      expect(rendered.queryByText('home.errors.categoryNotLive')).not.toBeNull();
      expectNoRetryNoPaywall(rendered, navigation);
      expect(rendered.queryByText('common.back')).not.toBeNull();
      fireEvent.press(rendered.getByText('common.back'));
      expect(navigation.goBack).toHaveBeenCalled();
      await tick(5000);
      expect(mockIdentifyFromImages).toHaveBeenCalledTimes(1);
    });
  }
});

describe('S81-11 C6 -- camera reason same_identity / category_conflict', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockIdentifyFromImages.mockReset();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  for (const reason of ['same_identity', 'category_conflict']) {
    it(`action error + reason ${reason} -> results-reason-state with the reason copy`, async () => {
      mockIdentifyFromImages.mockResolvedValue({
        success: false,
        action: 'error',
        error: 'x',
        reason,
      });
      const { rendered, navigation } = await renderCamera();
      expect(rendered.queryByTestId('results-reason-state')).not.toBeNull();
      expect(
        rendered.queryByText(`home.errors.insufficientDataReason.${reason}`),
      ).not.toBeNull();
      expectNoRetryNoPaywall(rendered, navigation);
    });
  }
});

describe('S81-11 PIN rows -- camera absent = today (R-A6)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockIdentifyFromImages.mockReset();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('P7: action error with no code / no reason, placeholder_identity, low_confidence -> vision_failed', async () => {
    for (const extra of [{}, { reason: 'placeholder_identity' }, { reason: 'low_confidence' }]) {
      mockIdentifyFromImages.mockReset();
      mockIdentifyFromImages.mockResolvedValue({ success: false, action: 'error', ...extra });
      const { rendered } = await renderCamera();
      expect(rendered.queryByText('results.emptyState.visionFailed')).not.toBeNull();
      expect(rendered.queryByTestId('results-category-not-live-state')).toBeNull();
      expect(rendered.queryByTestId('results-reason-state')).toBeNull();
      rendered.unmount();
    }
  });

  it('P8: action comparison_failed (no code) -> the timeout state', async () => {
    mockIdentifyFromImages.mockResolvedValue({ success: false, action: 'comparison_failed' });
    const { rendered } = await renderCamera();
    expect(rendered.queryByTestId('results-timeout-state')).not.toBeNull();
    expect(rendered.queryByTestId('results-category-not-live-state')).toBeNull();
  });
});
