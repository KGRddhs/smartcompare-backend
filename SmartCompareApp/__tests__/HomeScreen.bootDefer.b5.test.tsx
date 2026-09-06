/**
 * B5 — Home's first paint must not race the calls nothing renders from.
 *
 * A cold Home used to fire FOUR network calls at once:
 *   1. GET  /api/v1/usage/status     (useComparisonCounter — feeds the gate)
 *   2. GET  /api/v1/referrals/status (feeds the bonus pill)
 *   3. GET  /health                  (result DISCARDED — telemetry only)
 *   4. POST /api/v1/events           (compare_entry_view analytics)
 *
 * (3) and (4) have no consumer on screen, so they are now scheduled behind
 * the interaction queue. (1) and (2) stay inline — they feed what the user
 * actually sees, and the usage GET is the tier gate that shipped in #119's
 * OTA, so it is deliberately untouched here.
 *
 * These are behavioural assertions: `render()` flushes effects synchronously,
 * so a call made inline is already visible when render() returns, while a
 * deferred one is not. Move `checkServer()` back onto the critical path and
 * the first assertion below fails.
 *
 * Sync-render pattern per CLAUDE.md: `useFocusEffect` is mocked as a plain
 * `useEffect`, then plain `render()` + `waitFor()` (no act() wrapping).
 */

import React from 'react';
import { render, waitFor } from '@testing-library/react-native';

jest.mock('@react-navigation/native', () => {
  const ReactRequired = require('react');
  return {
    useFocusEffect: (cb: any) => {
      ReactRequired.useEffect(() => {
        const cleanup = cb();
        return cleanup;
      }, []);
    },
  };
});

jest.mock('expo-camera', () => {
  const ReactRequired = require('react');
  return {
    CameraView: () => ReactRequired.createElement('CameraView'),
    useCameraPermissions: () => [{ granted: true }, jest.fn()],
  };
});

jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: jest.fn().mockResolvedValue({ canceled: true }),
  MediaTypeOptions: { Images: 'Images' },
}));

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn().mockResolvedValue(undefined),
  notificationAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Light: 'Light' },
  NotificationFeedbackType: { Success: 'Success' },
}));

const mockHealthCheck = jest.fn();
const mockStreamComparison = jest.fn();
const mockApiPost = jest.fn();
const mockTrackEvent = jest.fn();
const mockGetSavedUser = jest.fn();
const mockGetReferralStatus = jest.fn();

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockApiPost(...args),
  },
  healthCheck: (...args: any[]) => mockHealthCheck(...args),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
  COMPARE_TIMEOUT_MS: 35000,
}));

jest.mock('../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

jest.mock('../src/services/usageService', () => ({
  isUsageLimitError: () => false,
  getUsageLimitDetail: () => null,
}));

jest.mock('../src/services/referralService', () => ({
  getReferralStatus: (...args: any[]) => mockGetReferralStatus(...args),
}));

jest.mock('../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => ({
    used: 1,
    total: 3,
    canCompare: true,
    increment: jest.fn(),
  }),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../src/components/CategorySelector', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', { testID: 'mock-category-selector' }),
  };
});

jest.mock('../src/components/QarenLogo', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', { testID: 'mock-qaren-logo' }),
  };
});

jest.mock('../src/components/TwoInputShell', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) =>
      ReactRequired.createElement('View', {
        testID: 'mock-two-input-shell',
        ...props,
      }),
  };
});

jest.mock('../src/components/PaywallBanner', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', { testID: 'mock-paywall-banner' }),
  };
});

jest.mock('../src/components/HomeEditorialSections', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', {
        testID: 'mock-home-editorial-sections',
      }),
  };
});

jest.mock('../src/icons', () => ({
  ScanIcon: () => null,
  LinkIcon: () => null,
  TypeIcon: () => null,
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
        return opts.defaultValue;
      }
      return key;
    },
  }),
}));

import HomeScreen from '../src/screens/HomeScreen';

function makeProps(overrides: any = {}) {
  return {
    navigation: { navigate: jest.fn(), goBack: jest.fn() },
    ...overrides,
  };
}

function entryViewCalls() {
  return mockTrackEvent.mock.calls.filter((c) => c[0] === 'compare_entry_view');
}

beforeEach(() => {
  jest.clearAllMocks();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'k@example.com' });
  mockGetReferralStatus.mockResolvedValue({ monthly_bonus_comparisons: 0 });
});

describe('B5 — HomeScreen keeps consumer-less boot calls off the first paint', () => {
  it('does not hit /health while the screen is painting', () => {
    render(<HomeScreen {...makeProps()} />);

    // Effects have already run at this point (render flushes them), so an
    // inline `checkServer()` would be visible here.
    expect(mockHealthCheck).not.toHaveBeenCalled();
  });

  it('does not POST the compare_entry_view analytics while painting', () => {
    render(<HomeScreen {...makeProps()} />);

    expect(entryViewCalls()).toHaveLength(0);
  });

  it('still sends the /health ping once the interactions settle', async () => {
    render(<HomeScreen {...makeProps()} />);

    await waitFor(() => expect(mockHealthCheck).toHaveBeenCalledTimes(1));
  });

  it('still sends compare_entry_view once the interactions settle', async () => {
    render(<HomeScreen {...makeProps()} />);

    await waitFor(() => expect(entryViewCalls()).toHaveLength(1));
    // Payload unchanged — only the timing moved.
    expect(entryViewCalls()[0][1]).toEqual({ mode: 'scan' });
  });

  it('keeps the referral status fetch on the critical path (it feeds the bonus pill)', () => {
    render(<HomeScreen {...makeProps()} />);

    expect(mockGetReferralStatus).toHaveBeenCalledTimes(1);
  });

  it('keeps the saved-user read on the critical path (it feeds the greeting)', () => {
    render(<HomeScreen {...makeProps()} />);

    expect(mockGetSavedUser).toHaveBeenCalledTimes(1);
  });

  it('a rejecting /health ping stays swallowed after the defer', async () => {
    // The deferred task runs outside the effect's call stack, so an
    // unguarded rejection there would surface as an unhandled rejection
    // rather than being caught by the caller.
    mockHealthCheck.mockRejectedValue(new Error('offline'));
    render(<HomeScreen {...makeProps()} />);

    await waitFor(() => expect(mockHealthCheck).toHaveBeenCalledTimes(1));
    // Give the rejection a turn to propagate if it were ever going to.
    await new Promise<void>((resolve) => setImmediate(resolve));
  });
});
