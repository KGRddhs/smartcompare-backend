/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1 OTA-BATCH RED -- hold on (INC_C1_UNIT_SPEC_V2.md section 7.1, rows
 * H1, H2, H3 and the pin H5; gate rulings F1 and F2).
 *
 * The contract this file fixes for GREEN (spec 1.4):
 *  - services/api COMPARE_TIMEOUT_MS is 50000 (35000 at base): the REST text
 *    compare GET, compareTextPair, the History GET (getComparison) and the
 *    Home link POST each carry timeout 50000 (H1).
 *  - A capped partial (HTTP 200, success true, metadata.partial true) that the
 *    server sends 36 s after the request reaches onComplete once (H2), and
 *    Home navigates to Results with it and raises no alert (H3).
 *  - "Hold on" (common.error + home.errors.timeout, two arguments) stays for
 *    a 503 TIMEOUT and for no answer inside the deadline (H5: passes at base
 *    and after GREEN).
 *
 * Harness (F2): the REAL services/api (streamComparison, getComparison,
 * compareTextPair, parseApiError) with only the axios instance mocked, as in
 * api.networkMatrix.m18, plus the HomeScreen mocks of HomeScreen.errorCopy.a11
 * except services/api. deadline(config, serverMs, response) answers at
 * serverMs or rejects as axios does (code ECONNABORTED) at config.timeout,
 * first wins; jest fake timers drive both clocks. F1: existing exports only,
 * no new path mocked, every base failure is an expect assertion. Synthetic
 * values only.
 */

import React from 'react';
import { render, fireEvent, act } from '@testing-library/react-native';
import enCatalog from '../../src/i18n/en.json';

import HomeScreen from '../../src/screens/HomeScreen';
import {
  COMPARE_TIMEOUT_MS,
  compareTextPair,
  getComparison,
  streamComparison,
} from '../../src/services/api';

const EN = enCatalog as unknown as Record<string, string>;

// ------------------------------------------------- api.networkMatrix.m18 --

jest.mock('../../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

const mockGetSavedUser = jest.fn();
const mockGetReferralStatus = jest.fn();

jest.mock('../../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

jest.mock('axios', () => {
  const instance = {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return { create: jest.fn(() => instance), __instance: instance };
});

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn().mockResolvedValue({ uri: 'file:///manipulated.jpg' }),
  SaveFormat: { JPEG: 'jpeg' },
}));

jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));

jest.mock('../../src/services/sentry', () => ({
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: (s: string) => s,
  scrubBeforeSend: (e: any) => e,
}));

// --------------------------- HomeScreen.errorCopy.a11 (all but services/api) --

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
      ReactRequired.createElement('View', { ...props, testID: 'mock-loading-screen-variants' }),
  };
});

jest.mock('../../src/icons', () => ({
  ScanIcon: () => null,
  LinkIcon: () => null,
  TypeIcon: () => null,
}));

jest.mock('react-i18next', () => {
  const catalog = require('../../src/i18n/en.json') as Record<string, string>;
  return {
    useTranslation: () => ({
      t: (key: string, opts?: any) => {
        if (catalog[key] !== undefined) return catalog[key];
        if (opts && typeof opts === 'object' && 'defaultValue' in opts) return opts.defaultValue;
        return key;
      },
    }),
  };
});

const axiosInstance = (require('axios') as any).__instance;

// ------------------------------------------------------------------ bodies --

const PRODUCTS = [
  {
    name: 'Chanel No 5',
    brand: 'Chanel',
    category: 'fragrances',
    price: { amount: 77.94, currency: 'BHD', retailer: 'noon.com', source_method: 'page_scrape' },
  },
  {
    name: 'Dior Sauvage',
    brand: 'Dior',
    category: 'fragrances',
    price: { amount: 47, currency: 'BHD', retailer: 'store-b.example.com', source_method: 'page_scrape' },
  },
];

/** The capped best-available body (success true, metadata.partial true). */
const PARTIAL = {
  success: true,
  products: PRODUCTS,
  overview: {
    winner: { product_index: 0, name: 'Chanel No 5', reason: 'Fits the brief.' },
    products: PRODUCTS,
  },
  comparison: {},
  recommendation: 'Fits the brief.',
  metadata: { query: 'Chanel No 5 vs Dior Sauvage', partial: true, partial_stage: 'post_gather' },
};

/**
 * The server answers at serverMs (never when it is not finite); axios
 * rejects with code ECONNABORTED at config.timeout. First wins.
 */
function deadline(config: any, serverMs: number, response: any): Promise<any> {
  return new Promise((resolve, reject) => {
    if (Number.isFinite(serverMs)) {
      setTimeout(() => resolve(response), serverMs);
    }
    const limit = typeof config?.timeout === 'number' ? config.timeout : 0;
    if (limit > 0) {
      setTimeout(() => reject(Object.assign(new Error('timeout'), { code: 'ECONNABORTED' })), limit);
    }
  });
}

/** An axios rejection exactly as the interceptor hands it to the caller. */
function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data };
  return err;
}

let textCompare: (config: any) => Promise<any> = () => Promise.resolve({ data: {} });

/** The mocked axios instance answers by url. */
function answer(url: string, config: any): Promise<any> {
  if (url === '/api/v1/text/compare') return textCompare(config);
  if (url === '/api/v1/url/compare') return Promise.resolve({ data: PARTIAL });
  return Promise.resolve({ data: {} });
}

const makeNavigation = () => ({ navigate: jest.fn(), goBack: jest.fn() });

/** Mount Home on real timers, pick a mode, then hand the clock to jest. */
function mountHome(modeTestId: 'home-mode-type' | 'home-mode-link') {
  const navigation = makeNavigation();
  const rendered = render(<HomeScreen navigation={navigation as any} />);
  fireEvent.press(rendered.getByTestId(modeTestId));
  const shell = rendered.getByTestId('mock-two-input-shell');
  jest.useFakeTimers();
  return { navigation, rendered, shell };
}

async function advance(ms: number) {
  await act(async () => {
    await jest.advanceTimersByTimeAsync(ms);
  });
}

/** Rows loop over many renders; bound each one well above jest's 5 s default. */
const ROW_MS = 60000;

let alertSpy: jest.SpyInstance;

beforeEach(() => {
  jest.useRealTimers();
  jest.clearAllMocks();
  textCompare = (config: any) => deadline(config, 36000, { data: PARTIAL });
  axiosInstance.get.mockImplementation((url: string, config?: any) => answer(url, config));
  axiosInstance.post.mockImplementation((url: string, _body?: any, config?: any) =>
    answer(url, config),
  );
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'k@example.com' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 0,
    bonus_referrer_name: null,
    bonus_expires_at: null,
  });
  const RN = require('react-native');
  alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => undefined);
});

afterEach(() => {
  alertSpy.mockRestore();
  jest.useRealTimers();
});

// ------------------------------------------------------------------ H rows --

describe('INC-C1 hold-on rows (fail at base)', () => {
  it('H1 deadline: COMPARE_TIMEOUT_MS is 50000 on the text GET, compareTextPair, the History GET and the link POST', async () => {
    expect(COMPARE_TIMEOUT_MS).toBe(50000);

    jest.useFakeTimers();
    streamComparison({ product_a: 'Chanel No 5', product_b: 'Dior Sauvage' }).subscribe({
      onComplete: jest.fn(),
      onError: jest.fn(),
    });
    await Promise.resolve();
    expect(axiosInstance.get).toHaveBeenCalledWith(
      '/api/v1/text/compare',
      expect.objectContaining({ timeout: 50000 }),
    );

    compareTextPair('Chanel No 5', 'Dior Sauvage').catch(() => undefined);
    expect(axiosInstance.post).toHaveBeenCalledWith(
      '/api/v1/text/compare',
      expect.anything(),
      expect.objectContaining({ timeout: 50000 }),
    );

    await getComparison('cmp-c1').catch(() => undefined);
    expect(axiosInstance.get).toHaveBeenCalledWith('/api/v1/comparisons/cmp-c1', { timeout: 50000 });
    jest.useRealTimers();

    const home = mountHome('home-mode-link');
    await act(async () => {
      home.shell.props.onSubmit('https://noon.com/a', 'https://store-b.example.com/b');
    });
    expect(axiosInstance.post).toHaveBeenCalledWith(
      '/api/v1/url/compare',
      expect.anything(),
      expect.objectContaining({ timeout: 50000 }),
    );
    home.rendered.unmount();
  }, ROW_MS);

  it('H2 a capped partial answered at 36 s reaches onComplete once with the body and never onError', async () => {
    jest.useFakeTimers();
    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'Chanel No 5', product_b: 'Dior Sauvage' }).subscribe({
      onComplete,
      onError,
    });
    await jest.advanceTimersByTimeAsync(36500);
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledWith(PARTIAL);
    expect(onError).not.toHaveBeenCalled();
  }, ROW_MS);

  it('H3 Home: the partial answered at 36 s navigates to Results with the result and raises no alert', async () => {
    const home = mountHome('home-mode-type');
    await act(async () => {
      home.shell.props.onSubmit('Chanel No 5', 'Dior Sauvage');
    });
    await advance(37000);
    expect(home.navigation.navigate).toHaveBeenCalledWith('Results', { result: PARTIAL });
    expect(alertSpy).not.toHaveBeenCalled();
    home.rendered.unmount();
  }, ROW_MS);
});

// ------------------------------------------------------------------ H5 pin --

describe('INC-C1 hold-on pin (passes at base)', () => {
  it('H5 a 503 TIMEOUT and a compare with no answer inside the deadline both keep the Hold on alert, two arguments', async () => {
    const holdOn = [EN['common.error'], EN['home.errors.timeout']];
    expect(holdOn.every((s) => typeof s === 'string' && s.length > 0)).toBe(true);

    textCompare = () =>
      Promise.reject(
        axiosError(503, { success: false, error: 'upstream slow', code: 'TIMEOUT', request_id: 'r' }),
      );
    const first = mountHome('home-mode-type');
    await act(async () => {
      first.shell.props.onSubmit('Chanel No 5', 'Dior Sauvage');
    });
    await advance(100);
    expect(alertSpy).toHaveBeenCalledTimes(1);
    expect(alertSpy.mock.calls[0]).toEqual(holdOn);
    expect(first.navigation.navigate).not.toHaveBeenCalledWith('Results', expect.anything());
    first.rendered.unmount();

    jest.useRealTimers();
    alertSpy.mockClear();
    textCompare = (config: any) => deadline(config, Infinity, { data: PARTIAL });
    const second = mountHome('home-mode-type');
    await act(async () => {
      second.shell.props.onSubmit('Chanel No 5', 'Dior Sauvage');
    });
    await advance(60000);
    expect(alertSpy).toHaveBeenCalledTimes(1);
    expect(alertSpy.mock.calls[0]).toEqual(holdOn);
    expect(second.navigation.navigate).not.toHaveBeenCalledWith('Results', expect.anything());
    second.rendered.unmount();
  }, ROW_MS);
});
