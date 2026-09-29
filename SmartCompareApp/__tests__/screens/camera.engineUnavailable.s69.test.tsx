/**
 * S69 U7 T3 (spec R3) — a camera-path engine outage is not the price-gathering loop.
 *
 * Base (d792f00e), ResultsScreen camera effect (src/screens/ResultsScreen.tsx
 * :257-336):
 *   - a THROWN identify failure goes through classifyLoadFailure, whose rows
 *     5/6 send any 503 / 5xx to 'timeout' -> "Still gathering prices" + "Tap to
 *     retry" (results.timeout.*), a loop the user can never exit during an
 *     OpenAI outage (a 429 `insufficient_quota` surfaces as a 500 today, a 503
 *     LLM_UNAVAILABLE after the R4 backend seam);
 *   - a 200 `action: 'comparison_failed'` is hard-wired to setLoadError('timeout')
 *     (:293-300) whatever its `code` (INTERNAL_ERROR on exit 6, the result's own
 *     code incl. LLM_UNAVAILABLE under ENABLE_CAMERA_FAILURE_ENVELOPE);
 *   - flag OFF (prod), an unsuccessful comparison arrives as `action:
 *     'comparison'` with `success: false`, and the client setResult()s the
 *     failure payload (:276-287) without looking at `success`.
 *
 * Contract pinned (spec R3 + binding review correction 13 / open question 8):
 * each of those shapes shows the R1 copy — title key
 * `home.errors.engineUnavailable.title`, body key
 * `home.errors.engineUnavailable.body` — with a way back and NO retry loop
 * (no `results-timeout-state`, no `results-timeout-retry`, no
 * results.timeout.* copy). The identify watchdog's own TIMEOUT-coded 503
 * (api.ts:365-368) still lands on the retryable timeout state.
 *
 * Boundary mocks mirror ResultsScreen.historyFloor.a17.test.tsx (global
 * react-i18next mock returns the key for any uncatalogued string).
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
  parseApiError: jest.fn(() => ({ code: 'INTERNAL_ERROR', message: '' })),
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

const ENGINE_TITLE = 'home.errors.engineUnavailable.title';
const ENGINE_BODY = 'home.errors.engineUnavailable.body';

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

/** The axios-SHAPED error identifyFromImages throws on !response.ok (api.ts:350-356). */
const thrownIdentify = (status: number, data: any) =>
  Object.assign(new Error(`Server error ${status}`), { response: { status, data } });

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

function expectEngineUnavailable(rendered: any, navigation: any) {
  // The R1 copy.
  expect(rendered.getByText(ENGINE_TITLE)).toBeTruthy();
  expect(rendered.getByText(ENGINE_BODY)).toBeTruthy();
  // Not the price-gathering retry loop.
  expect(rendered.queryByTestId('results-timeout-state')).toBeNull();
  expect(rendered.queryByTestId('results-timeout-retry')).toBeNull();
  expect(rendered.queryByText('results.timeout.title')).toBeNull();
  expect(rendered.queryByText('results.timeout.body')).toBeNull();
  expect(rendered.queryByText('results.timeout.retry')).toBeNull();
  // Not photo-blame either.
  expect(rendered.queryByText('results.emptyState.visionFailed')).toBeNull();
  // A way back: the state's CTA returns to the previous screen. The camera
  // user did not come from History, so the label is a neutral "Back"
  // (common.back), never "Back to history" (results.emptyState.cta).
  expect(rendered.queryByText('results.emptyState.cta')).toBeNull();
  fireEvent.press(rendered.getByText('common.back'));
  expect(navigation.goBack).toHaveBeenCalled();
  expect(navigation.navigate).not.toHaveBeenCalledWith('Paywall', expect.anything());
}

describe('S69 U7 T3 — camera engine outage shows the R1 copy, not "still gathering prices"', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockGetComparison.mockReset();
    mockIdentifyFromImages.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('thrown 503 LLM_UNAVAILABLE from /image/identify (the R4 envelope)', async () => {
    mockIdentifyFromImages.mockRejectedValue(
      thrownIdentify(503, {
        success: false,
        error: 'Still warming up the comparison engine — give it another tap in a moment.',
        code: 'LLM_UNAVAILABLE',
        request_id: 'req-503',
      }),
    );
    const { rendered, navigation } = await renderCamera();
    expect(mockIdentifyFromImages).toHaveBeenCalled();
    expectEngineUnavailable(rendered, navigation);
  });

  it('thrown bare 500 (non-JSON body) from /image/identify', async () => {
    mockIdentifyFromImages.mockRejectedValue(
      thrownIdentify(500, { error: 'Internal Server Error' }),
    );
    const { rendered, navigation } = await renderCamera();
    expectEngineUnavailable(rendered, navigation);
  });

  it('thrown 500 SERVER_ERROR envelope (today\'s vision-exception exit)', async () => {
    mockIdentifyFromImages.mockRejectedValue(
      thrownIdentify(500, {
        success: false,
        error: 'Image analysis failed. Please try again.',
        code: 'SERVER_ERROR',
        request_id: 'req-500',
      }),
    );
    const { rendered, navigation } = await renderCamera();
    expectEngineUnavailable(rendered, navigation);
  });

  it('200 action "comparison_failed" carrying LLM_UNAVAILABLE / INTERNAL_ERROR', async () => {
    for (const code of ['LLM_UNAVAILABLE', 'INTERNAL_ERROR']) {
      mockIdentifyFromImages.mockReset();
      mockIdentifyFromImages.mockResolvedValue({
        success: false,
        action: 'comparison_failed',
        error: 'comparison unavailable',
        code,
        products: [{ brand: 'A', name: 'one' }, { brand: 'B', name: 'two' }],
      });
      const { rendered, navigation } = await renderCamera();
      expectEngineUnavailable(rendered, navigation);
      rendered.unmount();
    }
  });

  it('200 action "comparison" with success:false + LLM_UNAVAILABLE (envelope flag OFF, prod)', async () => {
    mockIdentifyFromImages.mockResolvedValue({
      success: false,
      action: 'comparison',
      error: 'Still warming up the comparison engine — give it another tap in a moment.',
      code: 'LLM_UNAVAILABLE',
      identified_products: [{ brand: 'A', name: 'one' }, { brand: 'B', name: 'two' }],
    });
    const { rendered, navigation } = await renderCamera();
    expectEngineUnavailable(rendered, navigation);
  });

  it('200 action "comparison" with success:false and a NON-outage code is a load error, never a result (envelope flag OFF)', async () => {
    // Review fix — before, anything without an outage code fell through to
    // setResult() and painted the failure payload as the "not loading"
    // empty screen. Each row: [code, expected state].
    const rows: [string | undefined, 'timeout' | 'generic'][] = [
      ['TIMEOUT', 'timeout'],
      ['INSUFFICIENT_DATA', 'generic'],
      [undefined, 'generic'],
    ];
    for (const [code, expected] of rows) {
      mockIdentifyFromImages.mockReset();
      mockIdentifyFromImages.mockResolvedValue({
        success: false,
        action: 'comparison',
        error: 'comparison unsuccessful',
        ...(code ? { code } : {}),
        identified_products: [{ brand: 'A', name: 'one' }, { brand: 'B', name: 'two' }],
      });
      const navigation = makeNavigation();
      const { rendered } = await renderCamera(navigation);
      // Never the failure payload rendered as a result (the products < 2
      // "not loading" shell keys on results.empty.*).
      expect(rendered.getByTestId('results-empty-state')).toBeTruthy();
      expect(rendered.queryByText('results.empty.title')).toBeNull();
      expect(rendered.queryByText(ENGINE_TITLE)).toBeNull();
      if (expected === 'timeout') {
        expect(rendered.getByTestId('results-timeout-state')).toBeTruthy();
        expect(rendered.getByTestId('results-timeout-retry')).toBeTruthy();
      } else {
        expect(rendered.getByText('results.emptyState.title')).toBeTruthy();
        expect(rendered.queryByTestId('results-timeout-state')).toBeNull();
        expect(rendered.queryByText('results.emptyState.visionFailed')).toBeNull();
      }
      rendered.unmount();
    }
  });

  it('the identify watchdog TIMEOUT (503 + code TIMEOUT) still lands on the retryable timeout state', async () => {
    // RED anchor first: the outage path must exist before this control runs.
    mockIdentifyFromImages.mockRejectedValue(
      thrownIdentify(503, { success: false, code: 'LLM_UNAVAILABLE', error: 'x' }),
    );
    const first = await renderCamera();
    expect(first.rendered.getByText(ENGINE_TITLE)).toBeTruthy();
    first.rendered.unmount();

    // Control: api.ts:365-368 synthesizes this on the 2-minute abort.
    mockIdentifyFromImages.mockReset();
    mockIdentifyFromImages.mockRejectedValue(
      Object.assign(new Error('identify_timeout'), {
        code: 'TIMEOUT',
        response: { status: 503, data: { code: 'TIMEOUT' } },
      }),
    );
    const { rendered } = await renderCamera();
    expect(rendered.getByTestId('results-timeout-state')).toBeTruthy();
    expect(rendered.getByTestId('results-timeout-retry')).toBeTruthy();
    expect(rendered.queryByText(ENGINE_TITLE)).toBeNull();
  });
});
