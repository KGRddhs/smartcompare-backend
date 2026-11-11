/**
 * S81-G6 CL2 CLIENT-SPEED -- GREEN-owned gate rows (RULINGS_REBASE_S81_G6).
 *
 * G6-GR1 (RB-G6-2, the adversary's minor m2 / survivor O1): the Home-level
 * INCLUSIVE fast-hit boundary of GC-4. A Home response that lands at exactly
 * t = 300 ms (HOME_FLOOR_SKIP_BELOW_MS) navigates to Results at once with
 * params carrying fastHit: true; one that lands at t = 301 ms is held to the
 * 400 ms floor and navigates with no fastHit. The leaf rows (R2 / M3) pin
 * homeFloorDelayMs; this row pins the HomeScreen gate itself, so the O1 edit
 * (the `<=` of the Home fast-hit gate changed to `<`) is killed here.
 *
 * Harness: the HomeScreen.eS3hf.loaderVisibility pattern (real timers for
 * the mount and waitFor, then modern fake timers so Date.now and the floor
 * timer move together with advanceTimersByTime). Synthetic values only.
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';

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

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockApiPost(...args),
  },
  healthCheck: (...args: any[]) => mockHealthCheck(...args),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
}));

jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

jest.mock('../../src/services/usageService', () => ({
  isUsageLimitError: () => false,
  getUsageLimitDetail: () => null,
}));

jest.mock('../../src/services/referralService', () => ({
  getReferralStatus: (...args: any[]) => mockGetReferralStatus(...args),
}));

jest.mock('../../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => ({
    used: 1,
    total: 3,
    canCompare: true,
    increment: jest.fn().mockResolvedValue(undefined),
  }),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../../src/components/CategorySelector', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-category-selector' }),
  };
});

jest.mock('../../src/components/QarenLogo', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-qaren-logo' }),
  };
});

jest.mock('../../src/components/TwoInputShell', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) =>
      ReactRequired.createElement('View', { testID: 'mock-two-input-shell', ...props }),
  };
});

jest.mock('../../src/components/PaywallBanner', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-paywall-banner' }),
  };
});

jest.mock('../../src/components/HomeEditorialSections', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', { testID: 'mock-home-editorial-sections' }),
  };
});

jest.mock('../../src/screens/LoadingScreenVariants', () => {
  const ReactRequired = require('react');
  return {
    LoadingScreenVariants: (props: any) =>
      ReactRequired.createElement('View', {
        ...props,
        testID: 'mock-loading-screen-variants',
      }),
  };
});

jest.mock('../../src/icons', () => ({
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

import HomeScreen from '../../src/screens/HomeScreen';

const LOADER = 'mock-loading-screen-variants';

function makeProps() {
  return {
    navigation: {
      navigate: jest.fn(),
      goBack: jest.fn(),
    },
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 0,
    bonus_referrer_name: null,
    bonus_expires_at: null,
  });
});

afterEach(() => {
  if (jest.isMockFunction(setTimeout)) jest.useRealTimers();
});

/** Mount Home in text mode, start an SSE compare under fake timers. */
async function startSse(props: any) {
  let handlers: any = null;
  mockStreamComparison.mockReturnValue({
    subscribe: (h: any) => {
      handlers = h;
    },
    abort: jest.fn(),
  });
  const rendered = render(<HomeScreen {...props} />);
  fireEvent.press(rendered.getByTestId('home-mode-type'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  jest.useFakeTimers();
  await act(async () => {
    shell.props.onSubmit('Alpha One', 'Beta Two');
  });
  expect(rendered.queryByTestId(LOADER)).toBeTruthy();
  expect(handlers).not.toBeNull();
  return { rendered, handlers };
}

describe('CL2 gate rows (GREEN-owned)', () => {
  it('G6-GR1 the Home fast-hit gate is inclusive: t=300 navigates at once with fastHit: true, t=301 waits for the 400 ms floor with no fastHit', async () => {
    // t = 300: the edge of the "renders now" band (GC-4, inclusive).
    const atEdge = makeProps();
    const first = await startSse(atEdge);
    await act(async () => {
      jest.advanceTimersByTime(300);
      await first.handlers.onComplete({ success: true, comparison: {} });
    });
    expect(atEdge.navigation.navigate).toHaveBeenCalledTimes(1);
    const [edgeRoute, edgeParams] = atEdge.navigation.navigate.mock.calls[0];
    expect(edgeRoute).toBe('Results');
    expect(edgeParams.fastHit).toBe(true);
    expect(edgeParams.result).toEqual(expect.any(Object));
    first.rendered.unmount();
    jest.useRealTimers();

    // t = 301: one millisecond past the band, held to the 400 ms floor.
    const pastEdge = makeProps();
    const second = await startSse(pastEdge);
    await act(async () => {
      jest.advanceTimersByTime(301);
      await second.handlers.onComplete({ success: true, comparison: {} });
    });
    expect(pastEdge.navigation.navigate).not.toHaveBeenCalled();
    await act(async () => {
      jest.advanceTimersByTime(99);
    });
    expect(pastEdge.navigation.navigate).toHaveBeenCalledTimes(1);
    const [pastRoute, pastParams] = pastEdge.navigation.navigate.mock.calls[0];
    expect(pastRoute).toBe('Results');
    expect('fastHit' in pastParams).toBe(false);
    expect(pastParams.result).toEqual(expect.any(Object));
  });
});
