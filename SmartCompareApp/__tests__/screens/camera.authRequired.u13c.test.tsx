/**
 * S71 U13c (issue #298) -- a camera 401 that survives identifyFromImages' one
 * refresh + one retry shows a camera-only sign-in state, never the generic
 * "No comparison loaded".
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U13C_CAMERA_401_SPEC.md
 * (R5/R6, section 5.3, review corrections 8 and 10, rulings UR1/UR2/UR5).
 *
 * Base (72b13bc5), ResultsScreen camera catch: classifyLoadFailure(err) ===
 * 'auth' falls through to setLoadError('generic') -> results.emptyState.title +
 * results.emptyState.cta (goBack). Contract pinned here:
 *   - camera 401 -> container testID `results-auth-state`, title
 *     t('common.signInRequired'), one CTA testID `results-auth-signin` labelled
 *     t('auth.signIn');
 *   - the CTA awaits clearSession() and only then emitSessionInvalid() (the
 *     order of COMPLETION is pinned: 'clear-done' before 'emit'); no goBack;
 *   - a camera 400 keeps the generic state; the history-detail 401 is unchanged.
 *
 * Harness: screens/camera.engineUnavailable.s69.test.tsx (api mocked with
 * mockIdentifyFromImages, authService mocked incl. clearSession, fake timers,
 * renderCamera + tick(1500); the global react-i18next mock returns keys). The
 * REAL sessionEvents is used, observed through a listener removed after each test.
 */

import React from 'react';
import { render, act, fireEvent } from '@testing-library/react-native';
import { onSessionInvalid } from '../../src/services/sessionEvents';

const mockGetComparison = jest.fn();
const mockIdentifyFromImages = jest.fn();
const mockClearSession = jest.fn();

jest.mock('../../src/services/api', () => ({
  getComparison: (...args: any[]) => mockGetComparison(...args),
  identifyFromImages: (...args: any[]) => mockIdentifyFromImages(...args),
  trackEvents: jest.fn().mockResolvedValue(undefined),
  submitFeedback: jest.fn().mockResolvedValue(undefined),
  parseApiError: jest.fn(() => ({ code: 'INTERNAL_ERROR', message: '' })),
}));

jest.mock('../../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: (...args: any[]) => mockClearSession(...args),
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

const AUTH_STATE = 'results-auth-state';
const AUTH_CTA = 'results-auth-signin';

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

/** The axios-SHAPED error identifyFromImages throws on !response.ok (api.ts:350-355). */
const thrownIdentify = (status: number, data: any) =>
  Object.assign(new Error(`Server error ${status}`), { response: { status, data } });

const AUTH_REQUIRED_BODY = {
  success: false,
  code: 'AUTH_REQUIRED',
  error: 'Sign in to continue.',
};

async function renderCamera(navigation = makeNavigation()) {
  const rendered = render(
    <ResultsScreen
      route={{ params: { vision_products: ['file://a.jpg', 'file://b.jpg'] } } as any}
      navigation={navigation}
    />,
  );
  // Past the 1.2s camera floor, so any settled state is on screen.
  await tick(1500);
  return { rendered, navigation };
}

describe('S71 U13c -- a camera 401 shows the sign-in state', () => {
  let unsubscribe: (() => void) | null = null;

  beforeEach(() => {
    jest.useFakeTimers();
    mockGetComparison.mockReset();
    mockIdentifyFromImages.mockReset();
    mockClearSession.mockReset();
    mockClearSession.mockResolvedValue(undefined);
  });

  afterEach(() => {
    if (unsubscribe) unsubscribe();
    unsubscribe = null;
    jest.useRealTimers();
  });

  it('S1 a camera 401 shows the sign-in state, never the generic error', async () => {
    mockIdentifyFromImages.mockRejectedValue(thrownIdentify(401, AUTH_REQUIRED_BODY));

    const { rendered, navigation } = await renderCamera();

    expect(mockIdentifyFromImages).toHaveBeenCalled();
    // Not the generic "No comparison loaded" / "Back to history".
    expect({
      genericTitleShown: rendered.queryByText('results.emptyState.title') !== null,
      genericCtaShown: rendered.queryByText('results.emptyState.cta') !== null,
    }).toEqual({ genericTitleShown: false, genericCtaShown: false });
    // The sign-in state, from the existing i18n keys.
    expect(rendered.getByTestId(AUTH_STATE)).toBeTruthy();
    expect(rendered.getByText('common.signInRequired')).toBeTruthy();
    expect(rendered.getByText('auth.signIn')).toBeTruthy();
    // Not the retry loop, not the engine outage, not photo-blame.
    expect(rendered.queryByText('results.timeout.title')).toBeNull();
    expect(rendered.queryByText('results.timeout.body')).toBeNull();
    expect(rendered.queryByText('results.timeout.retry')).toBeNull();
    expect(rendered.queryByText('home.errors.engineUnavailable.title')).toBeNull();
    expect(rendered.queryByText('home.errors.engineUnavailable.body')).toBeNull();
    expect(rendered.queryByText('results.emptyState.visionFailed')).toBeNull();
    expect(navigation.navigate).not.toHaveBeenCalled();
  });

  it('S2 the sign-in CTA clears the session, then announces it', async () => {
    const order: string[] = [];
    // clearSession settles on a LATER macrotask, so an un-awaited call would
    // let the emit overtake it.
    mockClearSession.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          setTimeout(() => {
            order.push('clear-done');
            resolve();
          }, 0);
        }),
    );
    unsubscribe = onSessionInvalid(() => {
      order.push('emit');
    });
    mockIdentifyFromImages.mockRejectedValue(thrownIdentify(401, AUTH_REQUIRED_BODY));

    const { rendered, navigation } = await renderCamera();

    fireEvent.press(rendered.getByTestId(AUTH_CTA));
    await tick(10);
    await tick(10);

    expect(mockClearSession).toHaveBeenCalledTimes(1);
    expect(order.filter((e) => e === 'emit')).toHaveLength(1);
    expect(order).toEqual(['clear-done', 'emit']);
    expect(navigation.goBack).not.toHaveBeenCalled();
  });

  it('S3 a camera 400 still shows the generic state', async () => {
    mockIdentifyFromImages.mockRejectedValue(
      thrownIdentify(400, { success: false, code: 'BAD_REQUEST', error: 'Bad request' }),
    );

    const { rendered } = await renderCamera();

    expect(rendered.getByText('results.emptyState.title')).toBeTruthy();
    expect(rendered.getByText('results.emptyState.cta')).toBeTruthy();
    expect(rendered.queryByText('common.signInRequired')).toBeNull();
    expect(rendered.queryByTestId(AUTH_STATE)).toBeNull();
  });

  it('S4 the history-detail 401 is unchanged', async () => {
    mockGetComparison.mockRejectedValue(
      Object.assign(new Error('Request failed with status code 401'), {
        response: { status: 401, data: AUTH_REQUIRED_BODY },
      }),
    );
    const navigation = makeNavigation();

    const rendered = render(
      <ResultsScreen
        route={{ params: { comparison_id: 'cmp-u13c-401' } } as any}
        navigation={navigation}
      />,
    );
    await tick(1500);

    expect(mockGetComparison).toHaveBeenCalledWith('cmp-u13c-401');
    expect(mockIdentifyFromImages).not.toHaveBeenCalled();
    expect(rendered.getByText('results.emptyState.title')).toBeTruthy();
    expect(rendered.queryByText('common.signInRequired')).toBeNull();
    expect(rendered.queryByTestId(AUTH_STATE)).toBeNull();
  });
});
