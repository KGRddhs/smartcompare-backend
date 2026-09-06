/**
 * A17 — the History → Results display floor must not tax a fast re-open.
 *
 * ResultsScreen held ONE mount-anchored deadline (`minDisplayUntilRef =
 * Date.now() + 1200`) and both async entry paths waited on it. On the camera
 * path that is free — identify+compare is always multi-second, so the floor
 * has elapsed before the payload lands. On the History path it was not:
 * `getComparison(id)` is a single GET of an already-persisted comparison, so
 * time-to-content on a re-open was `max(fetch, 1200ms)` and nearly the whole
 * 1.2s was dead wait.
 *
 * Contract pinned here BEHAVIOURALLY, on the clock rather than on the
 * constants: with fake timers driving both the mocked fetch and the floor's
 * setTimeout, each test asserts the exact tick at which the loading state
 * gives way. That is the thing a user feels, and it stays true if the
 * numbers are later retuned in one place.
 *
 *   fast hit   (fetch 120ms) → renders at 120ms, no floor at all
 *   mid hit    (fetch 350ms) → still held to the 400ms floor
 *   slow hit   (fetch 800ms) → renders at 800ms, floor already elapsed
 *   camera     (fetch 120ms) → STILL held to the full 1.2s (untouched)
 *
 * Strip check (measured, see commit message): restoring the single
 * `minDisplayUntilRef = Date.now() + 1200` deadline on both paths turns the
 * fast-hit and slow-hit cases red (they sit in the loading state until
 * 1200ms); deleting the history floor outright instead turns the mid-hit
 * case red (it renders at 350ms and the rings flash).
 *
 * `getComparison` is resolved with `null` on purpose. What is under test is
 * WHEN the loading state ends, not what replaces it, and a null payload
 * lands on the same light `results-empty-state` branch A15's suite renders —
 * so the assertion never depends on the full Reanimated results tree.
 *
 * Boundary mocks mirror ResultsScreen.usageFetch.a15.test.tsx.
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

const mockGetComparison = jest.fn();
const mockIdentifyFromImages = jest.fn();

jest.mock('../src/services/api', () => ({
  getComparison: (...args: any[]) => mockGetComparison(...args),
  identifyFromImages: (...args: any[]) => mockIdentifyFromImages(...args),
  trackEvents: jest.fn().mockResolvedValue(undefined),
  submitFeedback: jest.fn().mockResolvedValue(undefined),
  parseApiError: jest.fn(() => ({ code: 'INTERNAL_ERROR', message: '' })),
}));

jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
  getSavedUser: jest.fn().mockResolvedValue(null),
  onSessionInvalid: jest.fn(() => () => undefined),
}));

jest.mock('../src/services/demographicsTrigger', () => ({
  loadDemographicsState: jest.fn().mockResolvedValue({}),
  shouldShowDemographicsPrompt: jest.fn().mockReturnValue(false),
  recordDismissal: jest.fn().mockResolvedValue(undefined),
  recordSubmission: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('expo-localization', () => ({
  locale: 'en-US',
  getLocales: () => [{ languageCode: 'en', regionCode: 'BH' }],
}));

jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({
    isRTL: false,
    language: 'en',
    setLanguage: jest.fn(),
  }),
}));

jest.mock('../src/lib/performance/wallTimeInstrumentation', () => ({
  getWallTimeTracker: () => ({
    mark: jest.fn(),
    report: jest.fn(),
    reset: jest.fn(),
  }),
}));

import ResultsScreen from '../src/screens/ResultsScreen';

const makeNavigation = () =>
  ({
    goBack: jest.fn(),
    navigate: jest.fn(),
    setOptions: jest.fn(),
  }) as any;

/**
 * A fetch that "takes" `ms` of fake-timer time before resolving to `value`.
 * Modern fake timers move Date.now() with advanceTimersByTime, so the
 * screen's own elapsed arithmetic sees the same clock this drives.
 */
const slowResolve = <T,>(ms: number, value: T) =>
  new Promise<T>((resolve) => setTimeout(() => resolve(value), ms));

/** Drain queued microtasks (the dynamic `import()`, each `await`) . */
const flush = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
};

/**
 * Advance the fake clock by `ms`.
 *
 * Flushing FIRST is load-bearing: the effect reaches its fetch through
 * `await import('../services/api')`, so on the first tick the mocked fetch's
 * own timer has not been scheduled yet and a bare advanceTimersByTime would
 * step straight over it. Flushing again afterwards lets the resolved fetch
 * run the floor arithmetic and commit its state.
 */
const tick = async (ms: number) => {
  await flush();
  await act(async () => {
    jest.advanceTimersByTime(ms);
  });
  await flush();
};

describe('A17 — History → Results floor is skipped on a fast hit', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockGetComparison.mockReset();
    mockIdentifyFromImages.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders a 120ms hit immediately instead of holding it to 1.2s', async () => {
    mockGetComparison.mockImplementation(() => slowResolve(120, null));

    const rendered = render(
      <ResultsScreen
        route={{ params: { comparison_id: 'cmp-1' } } as any}
        navigation={makeNavigation()}
      />
    );

    // Guard: the screen really did mount into the loading state, so the
    // "gone by 130ms" assertion cannot pass on a render that never happened.
    expect(rendered.queryByTestId('results-loading-state')).toBeTruthy();

    await tick(130);

    expect(mockGetComparison).toHaveBeenCalledWith('cmp-1');
    expect(rendered.queryByTestId('results-loading-state')).toBeNull();
    expect(rendered.queryByTestId('results-empty-state')).toBeTruthy();
  });

  it('renders an 800ms hit as soon as it lands (floor already elapsed)', async () => {
    mockGetComparison.mockImplementation(() => slowResolve(800, null));

    const rendered = render(
      <ResultsScreen
        route={{ params: { comparison_id: 'cmp-2' } } as any}
        navigation={makeNavigation()}
      />
    );

    await tick(790);
    expect(rendered.queryByTestId('results-loading-state')).toBeTruthy();

    await tick(20);
    expect(rendered.queryByTestId('results-loading-state')).toBeNull();
  });
});

describe('A17 — the shortened floor still catches a mid-speed hit', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockGetComparison.mockReset();
    mockIdentifyFromImages.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('holds a 350ms hit until 400ms rather than flashing the rings', async () => {
    mockGetComparison.mockImplementation(() => slowResolve(350, null));

    const rendered = render(
      <ResultsScreen
        route={{ params: { comparison_id: 'cmp-3' } } as any}
        navigation={makeNavigation()}
      />
    );

    // The payload is in hand at 350ms, but the loader must stay: a load the
    // user actually watched does not get yanked away mid-animation.
    await tick(360);
    expect(rendered.queryByTestId('results-loading-state')).toBeTruthy();

    await tick(50);
    expect(rendered.queryByTestId('results-loading-state')).toBeNull();
  });
});

describe('A17 — the camera path keeps the full 1.2s brand floor', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockGetComparison.mockReset();
    mockIdentifyFromImages.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('holds a 120ms identify all the way to 1200ms', async () => {
    // Not a realistic latency for identify+compare — that is the point. It
    // forces the camera floor to be the only thing that can be holding the
    // loader, so this fails the moment the camera path picks up the
    // history path's shortened deadline.
    mockIdentifyFromImages.mockImplementation(() =>
      slowResolve(120, { action: 'comparison', result: null })
    );

    const rendered = render(
      <ResultsScreen
        route={{ params: { vision_products: ['file://a.jpg', 'file://b.jpg'] } } as any}
        navigation={makeNavigation()}
      />
    );

    await tick(500);
    expect(mockIdentifyFromImages).toHaveBeenCalled();
    expect(rendered.queryByTestId('results-loading-state')).toBeTruthy();

    await tick(710);
    expect(rendered.queryByTestId('results-loading-state')).toBeNull();
  });
});
