/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R4, R4b, R5, R6, R7, P1, P2 (spec section 5
 * as amended by RULINGS_S81_G6 R-G6-4): the Home -> Results floor.
 *
 * Harness: the HomeScreen.eS3hf.loaderVisibility boundary mocks (the loader
 * stub carries the testID the visibility rows read). Modern fake timers are
 * switched on AFTER the mount + waitFor, so Date.now() and the floor timer
 * move together with advanceTimersByTime.
 *
 * New rule (C1): a response under HOME_FLOOR_SKIP_BELOW_MS (300 ms) renders
 * now and carries the additive route param fastHit: true; 300-400 ms waits
 * for the 400 ms floor; anything slower navigates at once. Synthetic values
 * only.
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

function makeProps(order?: string[]): any {
  return {
    navigation: {
      navigate: jest.fn((...args: any[]) => {
        if (order) order.push('navigate:' + String(args[0]));
      }),
      goBack: jest.fn(),
    },
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u-a', email: 'u-a@example.test' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 0,
    bonus_referrer_name: null,
    bonus_expires_at: null,
  });
});

afterEach(() => {
  if (jest.isMockFunction(setTimeout)) jest.useRealTimers();
  const RN = require('react-native');
  if (RN.Image && Object.prototype.hasOwnProperty.call(RN.Image, 'prefetch')) {
    delete RN.Image.prefetch;
  }
});

/** Mount Home in text mode, start an SSE compare, return the handlers. */
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

async function completeAt(handlers: any, ms: number, data: any) {
  await act(async () => {
    jest.advanceTimersByTime(ms);
    await handlers.onComplete(data);
  });
}

function lastParams(props: any): any {
  const calls = props.navigation.navigate.mock.calls;
  return calls.length ? calls[calls.length - 1][1] : undefined;
}

describe('CL2 Home floor (C1)', () => {
  it('R4 SSE fast hit (t=100) navigates with no further advance and drops the loader', async () => {
    const props = makeProps();
    const { rendered, handlers } = await startSse(props);
    await completeAt(handlers, 100, { success: true, comparison: {} });
    expect(props.navigation.navigate).toHaveBeenCalledWith(
      'Results',
      expect.objectContaining({ result: expect.any(Object) })
    );
    expect(rendered.queryByTestId(LOADER)).toBeNull();
  });

  it('R4b the fast path (t=100) passes fastHit: true', async () => {
    const props = makeProps();
    const { handlers } = await startSse(props);
    await completeAt(handlers, 100, { success: true, comparison: {} });
    expect(props.navigation.navigate).toHaveBeenCalledTimes(1);
    const params = lastParams(props);
    expect(params && params.fastHit).toBe(true);
  });

  it('R4b the mid path (t=350) navigates with no fastHit', async () => {
    const props = makeProps();
    const { handlers } = await startSse(props);
    await completeAt(handlers, 350, { success: true, comparison: {} });
    await act(async () => {
      jest.advanceTimersByTime(2000);
    });
    expect(props.navigation.navigate).toHaveBeenCalledTimes(1);
    const params = lastParams(props);
    expect(params).toEqual(expect.objectContaining({ result: expect.any(Object) }));
    expect(params.fastHit).not.toBe(true);
  });

  it('R5 SSE mid hit (t=350) is held to the 400 ms floor: not at 399, navigated at 400', async () => {
    const props = makeProps();
    const { rendered, handlers } = await startSse(props);
    await completeAt(handlers, 350, { success: true, comparison: {} });
    await act(async () => {
      jest.advanceTimersByTime(49);
    });
    expect(props.navigation.navigate).not.toHaveBeenCalled();
    expect(rendered.queryByTestId(LOADER)).toBeTruthy();
    await act(async () => {
      jest.advanceTimersByTime(1);
    });
    expect(props.navigation.navigate).toHaveBeenCalledWith(
      'Results',
      expect.objectContaining({ result: expect.any(Object) })
    );
    expect(rendered.queryByTestId(LOADER)).toBeNull();
  });

  it('R6 URL fast hit (~0 ms) navigates after the promise drain with no advance', async () => {
    mockApiPost.mockResolvedValue({ data: { success: true, comparison: {} } });
    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-link'));
    const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
    jest.useFakeTimers();
    await act(async () => {
      shell.props.onSubmit('https://shop.example.test/a', 'https://shop.example.test/b');
    });
    await act(async () => {
      for (let i = 0; i < 6; i += 1) {
        await Promise.resolve();
      }
    });
    expect(mockApiPost).toHaveBeenCalled();
    expect(props.navigation.navigate).toHaveBeenCalledWith(
      'Results',
      expect.objectContaining({ result: expect.any(Object) })
    );
  });

  it('R7 the two https product images are prefetched BEFORE navigate', async () => {
    const order: string[] = [];
    const RN = require('react-native');
    RN.Image.prefetch = jest.fn((url: string) => {
      order.push('prefetch:' + url);
      return Promise.resolve(true);
    });
    const props = makeProps(order);
    const { handlers } = await startSse(props);
    const urlA = 'https://img.example.test/r7-a.jpg';
    const urlB = 'https://img.example.test/r7-b.jpg';
    await completeAt(handlers, 1500, {
      success: true,
      overview: { products: [{ image_url: urlA }, { image_url: urlB }] },
    });
    await act(async () => {
      jest.advanceTimersByTime(2000);
    });
    expect(order).toEqual(['prefetch:' + urlA, 'prefetch:' + urlB, 'navigate:Results']);
  });

  it('P1 a slow hit (t=1500) navigates at once, with no fastHit', async () => {
    const props = makeProps();
    const { rendered, handlers } = await startSse(props);
    await completeAt(handlers, 1500, { success: true, comparison: {} });
    expect(props.navigation.navigate).toHaveBeenCalledWith(
      'Results',
      expect.objectContaining({ result: expect.any(Object) })
    );
    expect(lastParams(props).fastHit).not.toBe(true);
    expect(rendered.queryByTestId(LOADER)).toBeNull();
  });

  it('P2 onError unmounts the loader at once and never navigates', async () => {
    const props = makeProps();
    const { rendered, handlers } = await startSse(props);
    await act(async () => {
      handlers.onError({ message: 'synthetic error' });
    });
    expect(rendered.queryByTestId(LOADER)).toBeNull();
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });
    expect(props.navigation.navigate).not.toHaveBeenCalled();
  });
});
