/**
 * A15 — ResultsScreen must not fire a usage-status round-trip on mount.
 *
 * ResultsScreen used to hold `const [usageStatus, setUsageStatus] = useState(...)`
 * plus `useEffect(() => { getUsageStatus().then(setUsageStatus); }, [])`.
 * `usageStatus` had exactly one whole-word occurrence repo-wide — its own
 * declaration — so the state was write-only and the authenticated
 * `GET /api/v1/usage/status` it bought was discarded on every Results open.
 * (The paywall hop at the identify-failure branch reads `err.detail`, not
 * this state; the freemium pill lives on Home via `useComparisonCounter`.)
 *
 * Contract pinned here BEHAVIOURALLY, at the transport boundary rather than
 * at the service module boundary: mounting ResultsScreen issues zero
 * `/usage/status` GETs. Asserting on the mocked axios instance means the
 * test still fails if the fetch comes back through any other caller
 * (usageService, a direct api.get, a new hook) — it pins the round-trip,
 * not the import.
 *
 * Render target is the `!result` empty-state branch (route.params undefined),
 * which is the lightest tree that still runs every mount effect — the usage
 * effect was declared above the early return, so it fired on this path too.
 *
 * Strip check: re-adding the import + state + effect to ResultsScreen.tsx
 * turns "does not GET /usage/status" red (measured, see commit message).
 *
 * Boundary mocks mirror ResultsScreen.timeout.test.tsx (axios instance +
 * certificatePinning) and HomeScreen.abortOnUnmount.test.tsx (service stubs).
 */

import React from 'react';
import { render, waitFor } from '@testing-library/react-native';

jest.mock('axios', () => {
  const instance = {
    get: jest.fn().mockResolvedValue({ data: {} }),
    put: jest.fn().mockResolvedValue({ data: {} }),
    post: jest.fn().mockResolvedValue({ data: {} }),
    delete: jest.fn().mockResolvedValue({ data: {} }),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return { create: jest.fn(() => instance), __instance: instance };
});

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

// expo-localization ships untransformed ESM and is reached twice from this
// screen's import graph (src/i18n/index.ts and DemographicsBottomSheet.tsx).
// Same stub the DemographicsBottomSheet suites use.
jest.mock('expo-localization', () => ({
  locale: 'en-US',
  getLocales: () => [{ languageCode: 'en', regionCode: 'BH' }],
}));

// src/i18n/index.ts pulls expo-localization's untransformed ESM through the
// hook; the established stub across the screen suites (see
// OnboardingScreen.test.tsx, ProfileScreen.bundleE.s3.integration.test.tsx).
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

const axiosMock = require('axios') as { __instance: { get: jest.Mock } };

const makeNavigation = () =>
  ({
    goBack: jest.fn(),
    navigate: jest.fn(),
    setOptions: jest.fn(),
  }) as any;

const usageGets = () =>
  axiosMock.__instance.get.mock.calls.filter((call: any[]) =>
    String(call[0] ?? '').includes('/usage/status')
  );

describe('A15 — ResultsScreen mount does not fetch usage status', () => {
  beforeEach(() => {
    axiosMock.__instance.get.mockClear();
  });

  it('renders the empty state without issuing GET /usage/status', async () => {
    const { getByTestId } = render(
      <ResultsScreen route={{ params: undefined } as any} navigation={makeNavigation()} />
    );

    // Guard the negative assertion: the screen genuinely mounted, so
    // "never called" cannot pass by way of a render that never happened.
    expect(getByTestId('results-empty-state')).toBeTruthy();

    // Flush the mount effects' microtasks — the dead fetch was fired from a
    // mount `useEffect`, so it would already be recorded by here.
    await waitFor(() => {
      expect(usageGets()).toHaveLength(0);
    });
  });

  it('still issues no /usage/status GET after the mount effects settle', async () => {
    render(
      <ResultsScreen route={{ params: undefined } as any} navigation={makeNavigation()} />
    );

    await new Promise((resolve) => setImmediate(resolve));

    expect(usageGets()).toHaveLength(0);
  });
});

describe('A15 — the write-only usage state is gone from the source', () => {
  const fs = require('fs') as typeof import('fs');
  const path = require('path') as typeof import('path');
  const RAW = fs.readFileSync(
    path.resolve(__dirname, '../src/screens/ResultsScreen.tsx'),
    'utf8'
  );
  // Assert against CODE, not prose: the deletion left a tombstone comment
  // that names the removed state, and a naive /usageStatus/ match would
  // read that comment as the defect.
  const SOURCE = RAW.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');

  it('declares no usageStatus state and no setter for it', () => {
    expect(SOURCE).not.toMatch(/usageStatus/);
    expect(SOURCE).not.toMatch(/setUsageStatus/);
  });

  it('does not import usageService', () => {
    expect(SOURCE).not.toMatch(/services\/usageService/);
  });
});
