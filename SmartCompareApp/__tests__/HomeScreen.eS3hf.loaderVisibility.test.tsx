/**
 * Bundle E S3 hotfix L1 R3 — theatrical loader visibility during 1.2s floor.
 *
 * Final-code-reviewer flagged: on cached / fast responses (<1.2s elapsed),
 * SSE onComplete success path and URL try-block success path both call
 * `setLoading(false)` BEFORE `navigateToResultsWithFloor` schedules its
 * setTimeout. Result:
 *   1. setLoading(false) → React unmounts the fullscreen LoadingScreenVariants
 *   2. setTimeout(advance, ~1.0s) still pending
 *   3. user sees bare HomeScreen for up to 1.2s before navigation fires
 *
 * Fix shape: move `setLoading(false)` INSIDE the `advance` closure on the
 * success paths so the loader stays mounted until navigate fires. Error
 * paths keep their immediate `setLoading(false)` — failures should drop
 * the loader instantly.
 *
 * This is a RUNTIME test (not source-grep) — Gate B feedback specifically
 * asked for unmount-mid-timer coverage that proves the actual render
 * sequence, not just the symbol presence in source.
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

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockApiPost(...args),
  },
  healthCheck: (...args: any[]) => mockHealthCheck(...args),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
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
    increment: jest.fn().mockResolvedValue(undefined),
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

// Stub the actual loader so we can assert on its mount/unmount via the
// known testID without rendering the full reanimated tree.
jest.mock('../src/screens/LoadingScreenVariants', () => {
  const ReactRequired = require('react');
  return {
    LoadingScreenVariants: (props: any) =>
      ReactRequired.createElement('View', {
        ...props,
        // testID set AFTER spread so HomeScreen's own testID prop
        // ("home-loading-screen") does not shadow the mock's testID.
        // The visibility assertions below pin on the mock's testID.
        testID: 'mock-loading-screen-variants',
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
    navigation: {
      navigate: jest.fn(),
      goBack: jest.fn(),
    },
    ...overrides,
  };
}

// Fake timers enabled per-test AFTER initial mount + waitFor for the
// shell. `waitFor` polls via setInterval, which doesn't progress under
// fake timers — so we keep real timers for the mount phase, then swap.

beforeEach(() => {
  jest.clearAllMocks();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'k@example.com' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 1,
    bonus_referrer_name: 'Sara',
    bonus_expires_at: null,
  });
});

afterEach(() => {
  if (jest.isMockFunction(setTimeout)) jest.useRealTimers();
});

describe('HomeScreen — theatrical loader visibility during 1.2s floor', () => {
  it('SSE onComplete success keeps loader mounted until navigate fires (cached path)', async () => {
    let subscribeHandlers: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (handlers: any) => {
        subscribeHandlers = handlers;
      },
      abort: jest.fn(),
    });

    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );

    // Real timers above for waitFor; now swap so navigateToResultsWithFloor
    // can be advanced deterministically below.
    jest.useFakeTimers();

    // Trigger compare — setLoading(true) runs, loader mounts.
    await act(async () => {
      shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    });
    expect(rendered.queryByTestId('mock-loading-screen-variants')).toBeTruthy();

    // Cached response: backend resolves at t≈100ms (well below 1.2s floor).
    expect(subscribeHandlers).not.toBeNull();
    await act(async () => {
      jest.advanceTimersByTime(100);
      await subscribeHandlers.onComplete({ success: true, comparison: {} });
    });

    // CRITICAL: loader MUST still be mounted because the 1.2s floor has
    // not elapsed yet. The bug shape was: setLoading(false) fires here,
    // loader unmounts, user sees bare HomeScreen for ~1.1s.
    expect(
      rendered.queryByTestId('mock-loading-screen-variants'),
    ).toBeTruthy();

    // Advance past the floor — navigate fires AND loader unmounts AFTER navigate.
    await act(async () => {
      jest.advanceTimersByTime(1200);
    });
    expect(props.navigation.navigate).toHaveBeenCalledWith(
      'Results',
      expect.objectContaining({ result: expect.any(Object) }),
    );
  });

  it('URL compare success keeps loader mounted until navigate fires (cached path)', async () => {
    mockApiPost.mockResolvedValue({
      data: { success: true, comparison: {} },
    });

    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-link'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );

    jest.useFakeTimers();

    // Trigger URL compare. handleUrlCompare awaits api.post then
    // navigateToResultsWithFloor schedules setTimeout.
    await act(async () => {
      shell.props.onSubmit('https://noon.com/a', 'https://amazon.com/b');
    });
    // Drain the promise chain so api.post resolves and the floor is
    // scheduled.
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(mockApiPost).toHaveBeenCalled();
    // CRITICAL: loader must still be mounted, floor not yet elapsed.
    expect(
      rendered.queryByTestId('mock-loading-screen-variants'),
    ).toBeTruthy();

    // Advance past 1.2s floor → navigate fires.
    await act(async () => {
      jest.advanceTimersByTime(1200);
    });
    expect(props.navigation.navigate).toHaveBeenCalledWith(
      'Results',
      expect.objectContaining({ result: expect.any(Object) }),
    );
  });

  it('SSE onError immediately unmounts the loader (no floor wait on errors)', async () => {
    let subscribeHandlers: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (handlers: any) => {
        subscribeHandlers = handlers;
      },
      abort: jest.fn(),
    });

    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );

    jest.useFakeTimers();

    await act(async () => {
      shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    });
    expect(rendered.queryByTestId('mock-loading-screen-variants')).toBeTruthy();

    // Error path — drop loader immediately, never wait the floor.
    await act(async () => {
      subscribeHandlers.onError({ message: 'GPT timeout' });
    });
    expect(rendered.queryByTestId('mock-loading-screen-variants')).toBeNull();
  });

  it('URL onError immediately unmounts the loader', async () => {
    mockApiPost.mockRejectedValue(new Error('Network 500'));

    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-link'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );

    // No fake timers needed — error path doesn't schedule anything we
    // need to advance past.
    await act(async () => {
      shell.props.onSubmit('https://noon.com/a', 'https://amazon.com/b');
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    // After error, loader must be gone.
    expect(rendered.queryByTestId('mock-loading-screen-variants')).toBeNull();
  });
});
