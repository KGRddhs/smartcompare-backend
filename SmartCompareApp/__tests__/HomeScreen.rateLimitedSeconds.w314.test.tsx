/**
 * W3-14 R3 — Home's rate-limit alert tells the user HOW LONG to wait.
 *
 * W1-9 (#152) made both 429 envelopes carry `retry_after_seconds`; A11 made
 * Home render `t(friendlyErrorKey(parsed.code))` on both compare paths
 * (HomeScreen.tsx:482 text/SSE `onError`, :573 URL `catch`). Neither passed
 * the seconds on, so a rate-limited user got "give it a moment" with no
 * number and re-hammered. Fix contract (spec §4): both call sites become
 * `t(friendlyErrorKey(parsed.code), { count: parsed.retryAfterSeconds })`.
 *
 * Harness = HomeScreen.errorCopy.a11.test.tsx with TWO deliberate changes:
 *  1. `parseApiError` is the REAL function (jest.requireActual) — the a11
 *     harness re-implements it WITHOUT the new field (:79-97), so the seconds
 *     could never reach the screen through it;
 *  2. `t` honours `count` by resolving `key + '_one' | '_other'` when present
 *     (the a11 `t` ignores opts).
 *
 * ANTI-TAUTOLOGY (FABLE ruling R-16): the count-aware `t` below reads the
 * fix's own catalog entry back through this file's own suffix logic, so it
 * cannot by itself prove plural resolution. The anchors are:
 *  - errorCopy.w314.test.ts (R2) — REAL i18next on the REAL catalogs;
 *  - the m18 source regex (ResultsScreen.networkMatrix.m18.test.ts, updated
 *    in the green phase per ruling R-15) — the call-site shape.
 * What only THIS file can show is that the body is NOT the base sentence
 * once the field is on the wire — asserted first on every with-field row.
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';
import enCatalog from '../src/i18n/en.json';

const EN = enCatalog as Record<string, string>;

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
  selectionAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Light: 'Light' },
  NotificationFeedbackType: { Success: 'Success' },
}));

const mockHealthCheck = jest.fn();
const mockStreamComparison = jest.fn();
const mockApiPost = jest.fn();
const mockTrackEvent = jest.fn();
const mockGetSavedUser = jest.fn();
const mockGetReferralStatus = jest.fn();

// Network surface mocked; `parseApiError` is the REAL one.
jest.mock('../src/services/api', () => {
  const real = jest.requireActual('../src/services/api');
  return {
    __esModule: true,
    default: {
      post: (...args: any[]) => mockApiPost(...args),
    },
    healthCheck: (...args: any[]) => mockHealthCheck(...args),
    streamComparison: (...args: any[]) => mockStreamComparison(...args),
    parseApiError: real.parseApiError,
    trackEvent: (...args: any[]) => mockTrackEvent(...args),
    COMPARE_TIMEOUT_MS: 35000,
  };
});

jest.mock('../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
  getToken: jest.fn().mockResolvedValue(null),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
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
    default: () => ReactRequired.createElement('View', { testID: 'mock-category-selector' }),
  };
});

jest.mock('../src/components/QarenLogo', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-qaren-logo' }),
  };
});

jest.mock('../src/components/TwoInputShell', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) =>
      ReactRequired.createElement('View', { testID: 'mock-two-input-shell', ...props }),
  };
});

jest.mock('../src/components/PaywallBanner', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-paywall-banner' }),
  };
});

jest.mock('../src/components/HomeEditorialSections', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', { testID: 'mock-home-editorial-sections' }),
  };
});

jest.mock('../src/screens/LoadingScreenVariants', () => {
  const ReactRequired = require('react');
  return {
    LoadingScreenVariants: (props: any) =>
      ReactRequired.createElement('View', { ...props, testID: 'mock-loading-screen-variants' }),
  };
});

jest.mock('../src/icons', () => ({
  ScanIcon: () => null,
  LinkIcon: () => null,
  TypeIcon: () => null,
}));

// REAL en.json; count-aware (see the anti-tautology note in the header).
jest.mock('react-i18next', () => {
  const catalog = require('../src/i18n/en.json') as Record<string, string>;
  return {
    useTranslation: () => ({
      t: (key: string, opts?: any) => {
        if (opts && typeof opts === 'object' && typeof opts.count === 'number') {
          const plural = catalog[`${key}${opts.count === 1 ? '_one' : '_other'}`];
          if (plural !== undefined) return plural.replace('{{count}}', String(opts.count));
        }
        if (catalog[key] !== undefined) return catalog[key];
        if (opts && typeof opts === 'object' && 'defaultValue' in opts) return opts.defaultValue;
        return key;
      },
    }),
  };
});

import HomeScreen from '../src/screens/HomeScreen';

function makeProps(): any {
  return { navigation: { navigate: jest.fn(), goBack: jest.fn() } };
}

function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data, headers: {} };
  return err;
}

/** The W1-9 slowapi 429 envelope; `seconds === undefined` = older backend (field absent). */
const RATE_LIMITED_429 = (seconds?: number) =>
  axiosError(429, {
    success: false,
    error: 'Rate limit exceeded. Please try again later.',
    code: 'RATE_LIMITED',
    request_id: 'req-429',
    ...(seconds === undefined ? {} : { retry_after_seconds: seconds }),
  });

const RAW = /Rate limit|try again|per 1 minute/i;

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

async function submitTextCompare(rendered: any) {
  let handlers: any = null;
  mockStreamComparison.mockReturnValue({
    subscribe: (h: any) => {
      handlers = h;
    },
    abort: jest.fn(),
  });
  fireEvent.press(rendered.getByTestId('home-mode-type'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('iPhone 15', 'Galaxy S24');
  });
  return handlers;
}

async function submitUrlCompare(rendered: any) {
  fireEvent.press(rendered.getByTestId('home-mode-link'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('https://noon.com/a', 'https://amazon.com/b');
  });
}

async function textPathBody(err: any): Promise<any> {
  const RN = require('react-native');
  const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
  const rendered = render(<HomeScreen {...makeProps()} />);
  const handlers = await submitTextCompare(rendered);
  await act(async () => {
    handlers.onError(err);
  });
  expect(alertSpy).toHaveBeenCalledTimes(1);
  expect(alertSpy.mock.calls[0][0]).toBe(EN['common.error']);
  const body = alertSpy.mock.calls[0][1];
  alertSpy.mockRestore();
  return body;
}

async function urlPathBody(err: any): Promise<any> {
  mockApiPost.mockRejectedValueOnce(err);
  const RN = require('react-native');
  const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
  const rendered = render(<HomeScreen {...makeProps()} />);
  await submitUrlCompare(rendered);
  await waitFor(() => expect(alertSpy).toHaveBeenCalled());
  expect(alertSpy.mock.calls[0][0]).toBe(EN['common.error']);
  const body = alertSpy.mock.calls[0][1];
  alertSpy.mockRestore();
  return body;
}

describe('W3-14 R3 — text compare (onError, HomeScreen.tsx:482)', () => {
  it('429 WITH retry_after_seconds: 42 -> the seconds sentence, never the base one', async () => {
    const body = await textPathBody(RATE_LIMITED_429(42));
    expect(body).not.toMatch(RAW);
    // The one thing the count-aware mock cannot fake (R-16a).
    expect(body).not.toBe(EN['home.errors.rateLimited']);
    expect(body).toBe(
      (EN['home.errors.rateLimited_other'] ?? '<missing _other>').replace('{{count}}', '42'),
    );
    expect(body).toContain('42');
  });

  it('429 WITHOUT the field (older backend) -> the base sentence, unchanged', async () => {
    const body = await textPathBody(RATE_LIMITED_429(undefined));
    expect(body).not.toMatch(RAW);
    expect(body).toBe(EN['home.errors.rateLimited']);
  });
});

describe('W3-14 R3 — URL compare (catch, HomeScreen.tsx:573)', () => {
  it('429 WITH retry_after_seconds: 42 -> the seconds sentence, never the base one', async () => {
    const body = await urlPathBody(RATE_LIMITED_429(42));
    expect(body).not.toMatch(RAW);
    expect(body).not.toBe(EN['home.errors.rateLimited']);
    expect(body).toBe(
      (EN['home.errors.rateLimited_other'] ?? '<missing _other>').replace('{{count}}', '42'),
    );
    expect(body).toContain('42');
  });

  it('429 WITHOUT the field -> the base sentence, unchanged', async () => {
    const body = await urlPathBody(RATE_LIMITED_429(undefined));
    expect(body).not.toMatch(RAW);
    expect(body).toBe(EN['home.errors.rateLimited']);
  });
});

describe('W3-14 R3 — preserve: a non-429 code is unaffected by the count option', () => {
  it('text path: codeless edge 502 -> home.errors.comparison (no "failed")', async () => {
    const body = await textPathBody(axiosError(502, '<html>Bad gateway</html>'));
    expect(body).not.toMatch(/failed/i);
    expect(body).toBe(EN['home.errors.comparison']);
  });

  it('URL path: INSUFFICIENT_DATA 400 -> home.errors.insufficientData', async () => {
    const body = await urlPathBody(
      axiosError(400, {
        success: false,
        error: 'Not enough product data to compare',
        code: 'INSUFFICIENT_DATA',
      }),
    );
    expect(body).toBe(EN['home.errors.insufficientData']);
  });
});
