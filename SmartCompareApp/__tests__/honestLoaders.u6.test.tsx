/**
 * S69 U6 R6 fix-round (App Review guideline 2.3.1) — the COMPARISON loaders
 * show no invented statistics. The .s69 honestCounts fence covers the
 * onboarding surfaces only; this file extends it to the Home and Results
 * compare loaders, the surface App Review sees most:
 *
 *   - LoadingRings' counter chip (default counterTarget ticks to a nominal
 *     2,074) is hidden on Home's fullscreen loader and on Results' camera /
 *     history loader;
 *   - the rotating default tips no longer include
 *     'loading.tip.peer_prioritize' ("73% of Capital shoppers your age
 *     prioritize Quality."), a figure computed from nothing.
 *
 * Home's loader is pinned at the call site (HomeScreen renders too much to
 * mount here); the tip rotation and the Results loader are behavioural.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, act } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) =>
      opts && typeof opts === 'object' && 'defaultValue' in opts ? opts.defaultValue : key,
  }),
}));

const mockIdentifyFromImages = jest.fn();

jest.mock('../src/services/api', () => ({
  getComparison: jest.fn(),
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
  useLanguage: () => ({ isRTL: false, language: 'en', setLanguage: jest.fn() }),
}));

jest.mock('../src/lib/performance/wallTimeInstrumentation', () => ({
  getWallTimeTracker: () => ({ mark: jest.fn(), report: jest.fn(), reset: jest.fn() }),
}));

import ResultsScreen from '../src/screens/ResultsScreen';
import { LoadingScreenVariants } from '../src/screens/LoadingScreenVariants';

const SRC = path.resolve(__dirname, '../src');

describe('S69 U6 R6 — Home compare loader shows no counter chip', () => {
  it('HomeScreen renders its LoadingScreenVariants with showCounter={false}', () => {
    const home = fs.readFileSync(path.join(SRC, 'screens/HomeScreen.tsx'), 'utf8');
    const loader = home.match(/<LoadingScreenVariants\b[\s\S]*?\/>/);
    expect(loader).not.toBeNull();
    expect(loader![0]).toMatch(/testID="home-loading-screen"/);
    expect(loader![0]).toMatch(/showCounter=\{false\}/);
  });

  it('LoadingScreenVariants with showCounter={false} renders no counter chip', () => {
    jest.useFakeTimers();
    try {
      const screen = render(
        <LoadingScreenVariants variant="concentric" mode="comparison" showCounter={false} />,
      );
      expect(screen.queryByTestId('loading-rings')).toBeTruthy();
      expect(screen.queryByTestId('loading-rings-counter-chip')).toBeNull();
    } finally {
      jest.useRealTimers();
    }
  });
});

describe('S69 U6 R6 — the default compare tips carry no invented percentage', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it('a full rotation never shows loading.tip.peer_prioritize (the 73%)', () => {
    const screen = render(<LoadingScreenVariants variant="concentric" mode="comparison" />);
    const seen = new Set<string>();
    for (let i = 0; i < 12; i++) {
      const node = screen.queryByTestId('loading-tips-text');
      if (node) seen.add(String(node.props.children));
      act(() => {
        jest.advanceTimersByTime(2500);
      });
    }
    // Guard: the carousel really rotated, so absence is not a frozen tip.
    expect(seen.size).toBeGreaterThanOrEqual(2);
    expect(seen.has('loading.tip.peer_prioritize')).toBe(false);
    for (const text of seen) expect(text).not.toMatch(/%/);
  });
});

describe('S69 U6 R6 — Results loader shows no counter chip', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it('the camera-path loading state renders the rings without the 2,074 chip', async () => {
    mockIdentifyFromImages.mockImplementation(() => new Promise(() => undefined));
    const screen = render(
      <ResultsScreen
        route={{ params: { vision_products: ['file://a.jpg', 'file://b.jpg'] } } as any}
        navigation={{ goBack: jest.fn(), navigate: jest.fn(), setOptions: jest.fn() } as any}
      />,
    );
    await act(async () => {
      jest.advanceTimersByTime(3000);
    });
    expect(screen.getByTestId('results-loading-state')).toBeTruthy();
    expect(screen.queryByTestId('loading-rings-logo')).toBeTruthy();
    expect(screen.queryByTestId('loading-rings-counter-chip')).toBeNull();
    screen.unmount();
  });
});
