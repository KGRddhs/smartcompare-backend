/**
 * A4 — the compare loader must offer a cancel affordance, and cancelling
 * must actually stick.
 *
 * Before this fix `styles.loadingFullscreen` was an absoluteFill overlay at
 * zIndex 100 with `pointerEvents="auto"` and NOTHING tappable inside it.
 * `abortRef` had exactly one call site — the unmount cleanup — and Home is a
 * bottom-tab ROOT, so it never unmounts on a tab switch. A user watching a
 * stuck compare had no exit but backgrounding the app.
 *
 * Two halves are pinned here:
 *   1. the control exists only while loading, aborts the in-flight request,
 *      drops the overlay and reports the cancel to analytics;
 *   2. a response that lands AFTER the cancel is dropped on the floor — it
 *      must not burn a comparison credit (`increment`) and must not drag the
 *      user into Results. This is the half that actually needs the run-
 *      generation guard: the URL path is a plain awaited `api.post`, so its
 *      `then` still runs when the abort loses the race.
 *
 * Harness copied from HomeScreen.abortOnUnmount.test.tsx (boundary mocks:
 * services + native modules; drive TwoInputShell.onSubmit directly to mirror
 * a user tap inside the shell).
 */

import React from 'react';
import { StyleSheet } from 'react-native';
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
const mockIncrement = jest.fn();

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
    increment: (...args: any[]) => mockIncrement(...args),
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
    navigation: {
      navigate: jest.fn(),
      goBack: jest.fn(),
    },
    ...overrides,
  };
}

/** Mount Home, switch to the given input mode, hand back the shell. */
async function mountInMode(props: any, modeTestId: string) {
  const rendered = render(<HomeScreen {...props} />);
  fireEvent.press(rendered.getByTestId(modeTestId));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  return { rendered, shell };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'k@example.com' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 0,
    bonus_referrer_name: null,
    bonus_expires_at: null,
  });
  mockIncrement.mockResolvedValue(undefined);
});

describe('A4 — compare loader cancel affordance', () => {
  it('renders no cancel control while Home is idle', async () => {
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    await waitFor(() => rendered.getByTestId('mock-qaren-logo'));
    expect(rendered.queryByTestId('home-loading-screen')).toBeNull();
    expect(rendered.queryByTestId('home-loading-cancel')).toBeNull();
  });

  it('surfaces a cancel control with the loader, and pressing it aborts the in-flight compare and dismisses the overlay', async () => {
    const abort = jest.fn();
    // Never-settling subscribe — the compare stays in flight forever, which
    // is exactly the hung-connection state the user needs an exit from.
    mockStreamComparison.mockReturnValue({ subscribe: jest.fn(), abort });

    const props = makeProps();
    const { rendered, shell } = await mountInMode(props, 'home-mode-type');

    await act(async () => {
      shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    });

    expect(rendered.getByTestId('home-loading-screen')).toBeTruthy();
    const cancel = rendered.getByTestId('home-loading-cancel');
    expect(abort).not.toHaveBeenCalled();

    await act(async () => {
      fireEvent.press(cancel);
    });

    expect(abort).toHaveBeenCalledTimes(1);
    expect(rendered.queryByTestId('home-loading-screen')).toBeNull();
    expect(rendered.queryByTestId('home-loading-cancel')).toBeNull();
    expect(mockTrackEvent).toHaveBeenCalledWith('compare_cancelled', {
      mode: 'type',
    });
  });

  it('drops a text completion that lands after the cancel — no credit burned, no navigation', async () => {
    const abort = jest.fn();
    let handlers: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (h: any) => {
        handlers = h;
      },
      abort,
    });

    const props = makeProps();
    const { rendered, shell } = await mountInMode(props, 'home-mode-type');

    await act(async () => {
      shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    });
    await act(async () => {
      fireEvent.press(rendered.getByTestId('home-loading-cancel'));
    });

    // The transport dispatches a late success anyway (an abort the server
    // never honored, or a frame already in the read buffer).
    await act(async () => {
      await handlers.onComplete({ success: true, comparison: {} });
    });

    expect(mockIncrement).not.toHaveBeenCalled();
    expect(props.navigation.navigate).not.toHaveBeenCalledWith(
      'Results',
      expect.anything()
    );
    expect(rendered.queryByTestId('home-loading-screen')).toBeNull();
  });

  it('drops a URL-compare response that resolves after the cancel — no credit burned, no navigation', async () => {
    let resolvePost: (v: any) => void = () => {};
    mockApiPost.mockReturnValue(
      new Promise((resolve) => {
        resolvePost = resolve;
      })
    );

    const props = makeProps();
    const { rendered, shell } = await mountInMode(props, 'home-mode-link');

    await act(async () => {
      shell.props.onSubmit('https://a.example/p', 'https://b.example/p');
    });
    expect(mockApiPost).toHaveBeenCalledTimes(1);
    // The URL path must publish an abort handle too — before A4 it set none,
    // so neither the unmount cleanup nor cancel could reach it.
    expect(mockApiPost.mock.calls[0][2]).toEqual(
      expect.objectContaining({ signal: expect.anything() })
    );

    await act(async () => {
      fireEvent.press(rendered.getByTestId('home-loading-cancel'));
    });

    await act(async () => {
      resolvePost({ data: { success: true, comparison: {} } });
    });

    expect(mockIncrement).not.toHaveBeenCalled();
    expect(props.navigation.navigate).not.toHaveBeenCalledWith(
      'Results',
      expect.anything()
    );
  });

  it('does not wedge the next compare — a fresh run after a cancel still counts', async () => {
    const abort = jest.fn();
    let handlers: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (h: any) => {
        handlers = h;
      },
      abort,
    });

    const props = makeProps();
    const { rendered, shell } = await mountInMode(props, 'home-mode-type');

    await act(async () => {
      shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    });
    await act(async () => {
      fireEvent.press(rendered.getByTestId('home-loading-cancel'));
    });

    // Second attempt, same screen.
    await act(async () => {
      shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    });
    await act(async () => {
      await handlers.onComplete({ success: true, comparison: {} });
    });

    expect(mockIncrement).toHaveBeenCalledTimes(1);
  });

  it('anchors the cancel control with no direction-dependent offsets so RTL renders identically', async () => {
    mockStreamComparison.mockReturnValue({ subscribe: jest.fn(), abort: jest.fn() });

    const props = makeProps();
    const { rendered, shell } = await mountInMode(props, 'home-mode-type');
    await act(async () => {
      shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    });

    const flat: Record<string, any> =
      StyleSheet.flatten(rendered.getByTestId('home-loading-cancel').props.style) ?? {};
    expect(flat.alignSelf).toBe('center');
    for (const key of [
      'left',
      'right',
      'start',
      'end',
      'marginLeft',
      'marginRight',
      'marginStart',
      'marginEnd',
    ]) {
      expect(flat[key]).toBeUndefined();
    }
  });
});
