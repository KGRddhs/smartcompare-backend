/**
 * #118 — HomeScreen must abort an in-flight compare on unmount.
 *
 * Since M13-35 drain-not-abandon, an abandoned stream still completes the
 * Phase-2 tail server-side (default-unbounded), so an unaborted request is
 * not free. `streamComparison` returns an `abort()` and HomeScreen stashes
 * it in `abortRef`, but before #118 there was NO call site — unmounting
 * Home mid-compare leaked the request.
 *
 * Harness copied from HomeScreen.bundleE.s3.integration.test.tsx
 * (boundary mocks: services + native modules; drive TwoInputShell.onSubmit
 * directly to mirror a user tap inside the shell).
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react-native';

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
    navigation: {
      navigate: jest.fn(),
      goBack: jest.fn(),
    },
    ...overrides,
  };
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
});

describe('#118 — abort in-flight compare on Home unmount', () => {
  it('calls the streamComparison abort when Home unmounts mid-compare', async () => {
    const abort = jest.fn();
    // Never-settling subscribe — the compare stays in flight forever.
    mockStreamComparison.mockReturnValue({ subscribe: jest.fn(), abort });

    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    expect(mockStreamComparison).toHaveBeenCalledTimes(1);
    expect(abort).not.toHaveBeenCalled();

    rendered.unmount();
    expect(abort).toHaveBeenCalledTimes(1);
  });

  it('does NOT abort on unmount when the compare already completed', async () => {
    const abort = jest.fn();
    let handlers: any = null;
    mockStreamComparison.mockReturnValue({
      subscribe: (h: any) => {
        handlers = h;
      },
      abort,
    });

    const props = makeProps();
    const rendered = render(<HomeScreen {...props} />);
    fireEvent.press(rendered.getByTestId('home-mode-type'));
    const shell = await waitFor(() =>
      rendered.getByTestId('mock-two-input-shell'),
    );
    shell.props.onSubmit('iPhone 15', 'Galaxy S24');
    // Complete the compare — HomeScreen nulls abortRef in onComplete.
    await handlers.onComplete({ success: true, comparison: {} });

    rendered.unmount();
    expect(abort).not.toHaveBeenCalled();
  });
});
