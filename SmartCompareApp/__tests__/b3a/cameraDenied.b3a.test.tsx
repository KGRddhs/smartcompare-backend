/**
 * S79 B3-A item 2 -- an honest camera-denied state (spec C2, rows R6-R11;
 * rulings A9 (the pre-permission CTA stays "Turn on camera"), A12 (MR5:
 * R7b / R10b), A14 (keep R11)).
 *
 * Harness of consent/aiProcessingConsent.s69.test.tsx (renderHome with the
 * REAL consent gate, scan mode). `Linking.openSettings` is assigned here
 * (the shared react-native mock does not define it).
 */
/* eslint-disable @typescript-eslint/no-require-imports */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

jest.mock('../../src/services/aiConsent', () => jest.requireActual('../../src/services/aiConsent'));

jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  const ReactRequired = require('react');
  const Modal = (props: any) => {
    const wasVisible = ReactRequired.useRef(props.visible !== false);
    ReactRequired.useEffect(() => {
      const nowVisible = props.visible !== false;
      if (wasVisible.current && !nowVisible && typeof props.onDismiss === 'function') props.onDismiss();
      wasVisible.current = nowVisible;
    }, [props.visible]);
    if (props.visible === false) return null;
    return ReactRequired.createElement('Modal', props, props.children);
  };
  return { ...RN, Modal };
});

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

let mockPermission: Record<string, unknown> = { granted: true };
const mockRequestPermission = jest.fn();
const mockGetPermission = jest.fn();
jest.mock('expo-camera', () => {
  const ReactRequired = require('react');
  return {
    CameraView: () => ReactRequired.createElement('CameraView'),
    useCameraPermissions: () => [mockPermission, mockRequestPermission, mockGetPermission],
  };
});

const mockLaunchImageLibrary = jest.fn();
jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: (...args: any[]) => mockLaunchImageLibrary(...args),
  MediaTypeOptions: { Images: 'Images' },
}));

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn().mockResolvedValue(undefined),
  notificationAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Light: 'Light' },
  NotificationFeedbackType: { Success: 'Success' },
}));

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn().mockResolvedValue({ data: { success: false } }), get: jest.fn() },
  healthCheck: jest.fn().mockResolvedValue(true),
  streamComparison: jest.fn(() => ({ subscribe: jest.fn(), abort: jest.fn() })),
  identifyFromImages: jest.fn(),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  trackEvent: jest.fn(),
  COMPARE_TIMEOUT_MS: 35000,
  getHomeTrending: jest.fn().mockResolvedValue({ region: 'bahrain', trending: [] }),
  getHomeSmartPick: jest.fn().mockResolvedValue({ smart_pick: null, empty_state: true }),
  getHomeQuickCategories: jest.fn().mockResolvedValue({ categories: [] }),
  getHomeSavings: jest.fn().mockResolvedValue({ savings: null }),
}));

const mockGetSavedUser = jest.fn();
jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));
jest.mock('../../src/services/usageService', () => ({
  isUsageLimitError: () => false,
  getUsageLimitDetail: () => null,
}));
jest.mock('../../src/services/referralService', () => ({
  getReferralStatus: jest.fn().mockResolvedValue({ monthly_bonus_comparisons: 0 }),
}));
jest.mock('../../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => ({ used: 1, total: 3, canCompare: true, increment: jest.fn().mockResolvedValue(2) }),
}));
const mockStub = (id: string) => () => {
  const ReactRequired = require('react');
  return { __esModule: true, default: (props: any) => ReactRequired.createElement('View', { testID: id, ...props }) };
};
jest.mock('../../src/components/CategorySelector', () => mockStub('mock-category-selector')());
jest.mock('../../src/components/QarenLogo', () => mockStub('mock-qaren-logo')());
jest.mock('../../src/components/TwoInputShell', () => mockStub('mock-two-input-shell')());
jest.mock('../../src/components/PaywallBanner', () => mockStub('mock-paywall-banner')());
jest.mock('../../src/components/HomeEditorialSections', () => mockStub('mock-home-editorial-sections')());
jest.mock('../../src/icons', () => ({ ScanIcon: () => null, LinkIcon: () => null, TypeIcon: () => null }));

jest.mock('react-i18next', () => {
  const cat: Record<string, string> = require('../../src/i18n/en.json');
  const t = (key: string, opts?: any) => {
    const fallback = typeof opts === 'string' ? opts : opts?.defaultValue;
    let str: string = cat[key] ?? fallback ?? key;
    if (opts && typeof opts === 'object') {
      for (const [k, v] of Object.entries(opts)) {
        if (k === 'defaultValue') continue;
        str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
      }
    }
    return str;
  };
  return { useTranslation: () => ({ t, i18n: { language: 'en' } }) };
});

const RN = require('react-native');
const HomeScreen = require('../../src/screens/HomeScreen').default;
const ScanCameraScreen = require('../../src/screens/ScanCameraScreen').default;
const EN: Record<string, string> = require('../../src/i18n/en.json');

const DENIED = { granted: false, status: 'denied', canAskAgain: false };

async function flush(times = 4) {
  for (let i = 0; i < times; i += 1) {
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
  }
}

function makeNavigation() {
  const navigation: any = { navigate: jest.fn(), goBack: jest.fn() };
  navigation.getParent = () => navigation;
  return navigation;
}

async function renderHome() {
  const navigation = makeNavigation();
  const screen = render(<HomeScreen navigation={navigation} />);
  await flush();
  return { navigation, screen };
}

async function press(screen: any, testID: string) {
  await act(async () => {
    fireEvent.press(screen.getByTestId(testID));
  });
  await flush();
}

const sheet = (screen: any) => screen.queryByTestId('ai-consent-sheet');

let openSettings: jest.Mock;
beforeEach(async () => {
  jest.clearAllMocks();
  await (AsyncStorage as any).clear();
  mockPermission = { granted: true };
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'k@example.com' });
  mockLaunchImageLibrary.mockResolvedValue({ canceled: true });
  mockRequestPermission.mockResolvedValue({ granted: true });
  mockGetPermission.mockResolvedValue(DENIED);
  openSettings = jest.fn(() => Promise.resolve());
  (RN.Linking as any).openSettings = openSettings;
});

describe('B3-A camera denied state on Home (C2)', () => {
  it('r6 denied + cannot ask again shows the Settings state', async () => {
    for (const k of ['home.permission.denied_title', 'home.permission.denied_body', 'home.permission.open_settings']) {
      expect({ k, type: typeof EN[k] }).toEqual({ k, type: 'string' });
    }
    mockPermission = { ...DENIED };
    const { screen } = await renderHome();
    expect(screen.getByText(EN['home.permission.denied_title'])).toBeTruthy();
    expect(screen.getByText(EN['home.permission.denied_body'])).toBeTruthy();
    const btn = screen.getByTestId('home-permission-open-settings');
    expect(screen.getByText(EN['home.permission.open_settings'])).toBeTruthy();
    expect(btn).toBeTruthy();
    expect(screen.queryByText(EN['home.permission.cta'])).toBeNull();
    expect(screen.getByText(EN['home.permission.gallery_link'])).toBeTruthy();
  });

  it('r7 Open Settings opens Settings without consent or a permission request', async () => {
    mockPermission = { ...DENIED };
    const { screen } = await renderHome();
    expect(screen.queryByTestId('home-permission-open-settings')).not.toBeNull();
    await press(screen, 'home-permission-open-settings');
    expect(openSettings).toHaveBeenCalledTimes(1);
    expect(mockRequestPermission).not.toHaveBeenCalled();
    expect(sheet(screen)).toBeNull();
  });

  it('r7b (MR5) a rejecting openSettings is swallowed and the card stays', async () => {
    mockPermission = { ...DENIED };
    openSettings.mockImplementation(() => Promise.reject(new Error('no settings')));
    const unhandled: unknown[] = [];
    const onUnhandled = (e: unknown) => unhandled.push(e);
    process.on('unhandledRejection', onUnhandled);
    try {
      const { screen } = await renderHome();
      expect(screen.queryByTestId('home-permission-open-settings')).not.toBeNull();
      await press(screen, 'home-permission-open-settings');
      await flush(4);
      expect(openSettings).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId('home-permission-open-settings')).toBeTruthy();
      expect(unhandled).toEqual([]);
    } finally {
      process.off('unhandledRejection', onUnhandled);
    }
  });

  it('r8 [PIN] the gallery link in the denied state still goes through consent', async () => {
    mockPermission = { ...DENIED };
    const { screen } = await renderHome();
    await act(async () => {
      fireEvent.press(screen.getByText(EN['home.permission.gallery_link']));
    });
    await flush();
    expect(mockLaunchImageLibrary).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();
    await press(screen, 'ai-consent-agree');
    await waitFor(() => expect(mockLaunchImageLibrary).toHaveBeenCalledTimes(1));
  });

  it.each([
    [{ granted: false }],
    [{ granted: false, status: 'undetermined', canAskAgain: true }],
    [{ granted: false, status: 'undetermined', canAskAgain: false }],
    [{ granted: false, status: 'denied', canAskAgain: true }],
  ])('r9 [PIN] not denied keeps today\'s card: %j', async (perm) => {
    mockPermission = { ...perm };
    const { screen } = await renderHome();
    expect(screen.queryByTestId('home-permission-open-settings')).toBeNull();
    await act(async () => {
      fireEvent.press(screen.getByText(EN['home.permission.cta']));
    });
    await flush();
    expect(mockRequestPermission).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();
    await press(screen, 'ai-consent-agree');
    await waitFor(() => expect(mockRequestPermission).toHaveBeenCalledTimes(1));
  });

  it('r10 returning to the app re-checks the permission; never while granted', async () => {
    mockPermission = { ...DENIED };
    const { screen } = await renderHome();
    await act(async () => {
      RN.AppState.__emit('background');
      RN.AppState.__emit('active');
    });
    await flush();
    expect(mockGetPermission).toHaveBeenCalledTimes(1);
    screen.unmount();

    jest.clearAllMocks();
    mockPermission = { granted: true, status: 'granted', canAskAgain: true };
    const granted = await renderHome();
    await act(async () => {
      RN.AppState.__emit('background');
      RN.AppState.__emit('active');
    });
    await flush();
    expect(mockGetPermission).not.toHaveBeenCalled();
    granted.screen.unmount();
  });

  it('r10b (MR5) after the permission turns granted, or after unmount, the listener is gone', async () => {
    mockPermission = { ...DENIED };
    const { screen, navigation } = await renderHome();
    await act(async () => {
      RN.AppState.__emit('background');
      RN.AppState.__emit('active');
    });
    await flush();
    const before = mockGetPermission.mock.calls.length;
    expect(before).toBeGreaterThanOrEqual(1);
    mockPermission = { granted: true, status: 'granted', canAskAgain: true };
    screen.rerender(<HomeScreen navigation={navigation} />);
    await flush();
    await act(async () => {
      RN.AppState.__emit('background');
      RN.AppState.__emit('active');
    });
    await flush();
    expect(mockGetPermission).toHaveBeenCalledTimes(before);

    mockPermission = { ...DENIED };
    const second = await renderHome();
    second.screen.unmount();
    const after = mockGetPermission.mock.calls.length;
    await act(async () => {
      RN.AppState.__emit('background');
      RN.AppState.__emit('active');
    });
    await flush();
    expect(mockGetPermission).toHaveBeenCalledTimes(after);
  });
});

describe('B3-A camera denied state on ScanCamera (C2, A14)', () => {
  const nav = () => ({ goBack: jest.fn(), navigate: jest.fn() }) as any;

  it('r11 ScanCamera pad has the same denied state', async () => {
    mockPermission = { ...DENIED };
    const s = render(<ScanCameraScreen navigation={nav()} route={{} as any} />);
    expect(s.queryByTestId('scan-camera-permission-open-settings')).not.toBeNull();
    expect(s.queryByTestId('scan-camera-permission-cta') === null).toBe(true);
    await act(async () => {
      fireEvent.press(s.getByTestId('scan-camera-permission-open-settings'));
    });
    expect(openSettings).toHaveBeenCalledTimes(1);
    expect(mockRequestPermission).not.toHaveBeenCalled();
    s.unmount();

    // Fix round FA4: R9's four not-denied objects (the first is the original
    // {granted:false} case) keep the CTA and never show Open Settings.
    const NOT_DENIED = [
      { granted: false },
      { granted: false, status: 'undetermined', canAskAgain: true },
      { granted: false, status: 'undetermined', canAskAgain: false },
      { granted: false, status: 'denied', canAskAgain: true },
    ];
    for (const perm of NOT_DENIED) {
      mockRequestPermission.mockClear();
      mockPermission = { ...perm };
      const s2 = render(<ScanCameraScreen navigation={nav()} route={{} as any} />);
      expect({
        perm,
        openSettings: s2.queryByTestId('scan-camera-permission-open-settings') !== null,
        cta: s2.queryByTestId('scan-camera-permission-cta') !== null,
      }).toEqual({ perm, openSettings: false, cta: true });
      fireEvent.press(s2.getByTestId('scan-camera-permission-cta'));
      expect(mockRequestPermission).toHaveBeenCalledTimes(1);
      s2.unmount();
    }
  });
});
