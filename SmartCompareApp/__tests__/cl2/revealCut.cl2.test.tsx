/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R8, R8b, P3 (spec section 5 as amended by
 * RULINGS_S81_G6 R-G6-4): the 800 ms winner reveal is cut to 0 ONLY on a
 * measured fast hit (Home passes route.params.fastHit === true); every other
 * Results mount (a slow Home compare, a history re-open, the camera) keeps
 * the 800 ms brand moment.
 *
 * Boundary mocks mirror ResultsScreen.historyFloor.a17.test.tsx; the haptic
 * and the wall-time tracker are recorders. Synthetic values only.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, act } from '@testing-library/react-native';

const mockGetComparison = jest.fn();
const mockIdentifyFromImages = jest.fn();
const mockMarks: string[] = [];
const mockImpact = jest.fn(() => Promise.resolve());

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
  getToken: jest.fn().mockResolvedValue('synthetic'),
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

jest.mock('expo-haptics', () => ({
  impactAsync: (...args: any[]) => (mockImpact as any)(...args),
  notificationAsync: jest.fn().mockResolvedValue(undefined),
  selectionAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Light: 'Light', Medium: 'Medium', Heavy: 'Heavy' },
  NotificationFeedbackType: { Success: 'Success' },
}));

jest.mock('../../src/hooks/useLanguage', () => ({
  useLanguage: () => ({ isRTL: false, language: 'en', setLanguage: jest.fn() }),
}));

jest.mock('../../src/lib/performance/wallTimeInstrumentation', () => ({
  getWallTimeTracker: () => ({
    mark: (name: string) => mockMarks.push(name),
    report: jest.fn(),
    reset: jest.fn(),
    start: jest.fn(),
  }),
}));

import ResultsScreen from '../../src/screens/ResultsScreen';

const RESULTS_SRC = fs
  .readFileSync(path.resolve(__dirname, '../../src/screens/ResultsScreen.tsx'), 'utf8')
  .replace(/\r\n/g, '\n');

const makeNavigation = () =>
  ({ goBack: jest.fn(), navigate: jest.fn(), setOptions: jest.fn() }) as any;

/** A synthetic, render-light result (no products: the empty-content branch). */
const RESULT: any = { success: true };

const flush = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
};

const advance = async (ms: number) => {
  await act(async () => {
    jest.advanceTimersByTime(ms);
  });
  await flush();
};

describe('CL2 reveal cut (C2)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockMarks.length = 0;
    mockImpact.mockClear();
    mockGetComparison.mockReset();
    mockIdentifyFromImages.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('R8 a measured fast hit (result + fastHit: true) reveals after 1 ms', async () => {
    const rendered = render(
      <ResultsScreen
        route={{ params: { result: RESULT, fastHit: true } } as any}
        navigation={makeNavigation()}
      />
    );
    await advance(1);
    expect(mockImpact).toHaveBeenCalledTimes(1);
    expect(mockMarks).toContain('ready_celebration');
    rendered.unmount();
  });

  it('R8b a result WITHOUT fastHit keeps the 800 ms reveal: not at 799, at 800', async () => {
    const rendered = render(
      <ResultsScreen route={{ params: { result: RESULT } } as any} navigation={makeNavigation()} />
    );
    await advance(799);
    expect(mockImpact).not.toHaveBeenCalled();
    expect(mockMarks).not.toContain('ready_celebration');
    await advance(1);
    expect(mockImpact).toHaveBeenCalledTimes(1);
    expect(mockMarks).toContain('ready_celebration');
    rendered.unmount();
  });

  it('P3 the history path (comparison_id, fetch pending) keeps 800: not at 799, at 800', async () => {
    mockGetComparison.mockImplementation(() => new Promise(() => undefined));
    const rendered = render(
      <ResultsScreen
        route={{ params: { comparison_id: 'cmp-cl2' } } as any}
        navigation={makeNavigation()}
      />
    );
    await advance(799);
    expect(mockImpact).not.toHaveBeenCalled();
    await advance(1);
    expect(mockImpact).toHaveBeenCalledTimes(1);
    // The camera and history floors are unchanged by CL2.
    expect(RESULTS_SRC).toMatch(/const CAMERA_FLOOR_MS = 1200;/);
    expect(RESULTS_SRC).toMatch(/const HISTORY_FLOOR_MS = 400;/);
    expect(RESULTS_SRC).toMatch(/const HISTORY_FLOOR_SKIP_BELOW_MS = 300;/);
    rendered.unmount();
  });
});
