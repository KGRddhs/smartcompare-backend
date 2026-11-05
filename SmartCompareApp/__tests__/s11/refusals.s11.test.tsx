/**
 * S81-11 RED -- refusal rendering on the text and link paths + the copy map
 * (spec 2.3 / 2.5, C11 / C12 / C13; rulings R-S11-22, R-S11-26; R-S10B-15).
 *
 * CATEGORY_NOT_LIVE (400 and 429, text and link) renders ONE coming-soon
 * Alert: title t('home.categories.fragrancesOnly'), body
 * t('home.errors.categoryNotLive'), never the Paywall, never seconds. The
 * additive INSUFFICIENT_DATA `reason` (S81-20, read TOP-LEVEL from the
 * envelope, R-S11-26) gets per-reason copy; no_evidence / unknown / absent =
 * today's sentence.
 *
 * Harness = HomeScreen.errorCopy.a11.test.tsx: the REAL errorCopy map and the
 * REAL usageService (so a widened USAGE_LIMIT test is killable); the api
 * mock's parseApiError mirrors api.ts plus the additive reason read; `t`
 * resolves through the REAL en.json with plural selection on `count`.
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';
import enCatalog from '../../src/i18n/en.json';

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
  ImpactFeedbackStyle: { Light: 'Light' },
  NotificationFeedbackType: { Success: 'Success' },
}));

const mockHealthCheck = jest.fn();
const mockStreamComparison = jest.fn();
const mockApiPost = jest.fn();
const mockApiGet = jest.fn();
const mockTrackEvent = jest.fn();
const mockGetSavedUser = jest.fn();
const mockGetReferralStatus = jest.fn();

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockApiPost(...args),
    get: (...args: any[]) => mockApiGet(...args),
  },
  healthCheck: (...args: any[]) => mockHealthCheck(...args),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  parseApiError: (error: any) => {
    const data = error?.response?.data;
    const status = error?.response?.status;
    const rawCode =
      (typeof data?.code === 'string' && data.code) ||
      (typeof data?.detail?.code === 'string' && data.detail.code) ||
      null;
    if (rawCode === 'TIMEOUT' || rawCode === 'STREAM_TIMEOUT' || (status === 503 && !rawCode)) {
      return { message: '', code: 'TIMEOUT' };
    }
    const out: any = { message: '', code: rawCode };
    const ra = data?.retry_after_seconds;
    if (typeof ra === 'number' && Number.isFinite(ra) && ra > 0) out.retryAfterSeconds = Math.ceil(ra);
    // S81-11 R-S11-26: the additive reason, top-level first, string only.
    const reason =
      (typeof data?.reason === 'string' && data.reason) ||
      (typeof data?.detail?.reason === 'string' && data.detail.reason) ||
      undefined;
    if (reason) out.reason = reason;
    return out;
  },
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
  COMPARE_TIMEOUT_MS: 35000,
  API_BASE_URL: 'https://api.example.test',
}));

jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
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
  const interp = (s: string, opts?: any) => {
    if (!opts || typeof opts !== 'object') return s;
    let out = s;
    for (const [k, v] of Object.entries(opts)) {
      if (k === 'defaultValue' || v === undefined) continue;
      out = out.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
    }
    return out;
  };
  const t = (key: string, opts?: any) => {
    if (opts && typeof opts === 'object' && typeof opts.count === 'number') {
      const form = opts.count === 1 ? `${key}_one` : `${key}_other`;
      if (catalog[form] !== undefined) return interp(catalog[form], opts);
    }
    if (catalog[key] !== undefined) return interp(catalog[key], opts);
    if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
      return interp(opts.defaultValue, opts);
    }
    return key;
  };
  return { useTranslation: () => ({ t, i18n: { language: 'en' } }) };
});

import HomeScreen from '../../src/screens/HomeScreen';

const TITLE_KEY = 'home.categories.fragrancesOnly';
const BODY_KEY = 'home.errors.categoryNotLive';
const MISSING = '<missing catalog key>';
const TITLE = EN[TITLE_KEY] ?? MISSING;
const BODY = EN[BODY_KEY] ?? MISSING;

function makeProps() {
  return { navigation: { navigate: jest.fn(), goBack: jest.fn() } };
}

function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data };
  return err;
}

const NOT_LIVE_400 = () =>
  axiosError(400, {
    success: false,
    error: 'We compare fragrances for now.',
    code: 'CATEGORY_NOT_LIVE',
    category: 'electronics',
    categories_live: ['fragrances'],
    request_id: 'req-s11-1',
  });

const NOT_LIVE_429 = () =>
  axiosError(429, {
    success: false,
    error: 'Daily refusal budget reached.',
    code: 'CATEGORY_NOT_LIVE',
    scope: 'refusal_daily',
    retry_after_seconds: 3600,
    resets_at: '2026-11-06T21:00:00Z',
    categories_live: ['fragrances'],
    request_id: 'req-s11-2',
  });

const INSUFFICIENT = (reason?: string) =>
  axiosError(400, {
    success: false,
    error: 'Not enough product data to compare',
    code: 'INSUFFICIENT_DATA',
    ...(reason ? { reason } : {}),
    request_id: 'req-s11-3',
  });

let alertSpy: jest.SpyInstance;

beforeEach(() => {
  jest.clearAllMocks();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'user-a@example.com' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 0,
    bonus_referrer_name: null,
    bonus_expires_at: null,
  });
  const RN = require('react-native');
  alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
});

afterEach(() => {
  alertSpy.mockRestore();
});

async function textError(err: any) {
  let handlers: any = null;
  mockStreamComparison.mockReturnValue({
    subscribe: (h: any) => {
      handlers = h;
    },
    abort: jest.fn(),
  });
  const props = makeProps();
  const rendered = render(<HomeScreen {...(props as any)} />);
  fireEvent.press(rendered.getByTestId('home-mode-type'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('Dior Sauvage EDP', 'Bleu de Chanel EDP');
  });
  await act(async () => {
    handlers.onError(err);
  });
  return props;
}

async function textTerminalFalse(data: any) {
  let handlers: any = null;
  mockStreamComparison.mockReturnValue({
    subscribe: (h: any) => {
      handlers = h;
    },
    abort: jest.fn(),
  });
  const props = makeProps();
  const rendered = render(<HomeScreen {...(props as any)} />);
  fireEvent.press(rendered.getByTestId('home-mode-type'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('Dior Sauvage EDP', 'Bleu de Chanel EDP');
  });
  await act(async () => {
    await handlers.onComplete(data);
  });
  return props;
}

async function urlReject(err: any) {
  mockApiPost.mockRejectedValueOnce(err);
  const props = makeProps();
  const rendered = render(<HomeScreen {...(props as any)} />);
  fireEvent.press(rendered.getByTestId('home-mode-link'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('https://store-a.example.com/p/1', 'https://store-a.example.com/p/2');
  });
  await waitFor(() =>
    expect(alertSpy.mock.calls.length + props.navigation.navigate.mock.calls.length).toBeGreaterThan(0),
  );
  return props;
}

async function urlResolveFalse(data: any) {
  mockApiPost.mockResolvedValueOnce({ data });
  const props = makeProps();
  const rendered = render(<HomeScreen {...(props as any)} />);
  fireEvent.press(rendered.getByTestId('home-mode-link'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('https://store-a.example.com/p/1', 'https://store-a.example.com/p/2');
  });
  await waitFor(() => expect(alertSpy).toHaveBeenCalled());
  return props;
}

function expectComingSoon(props: any) {
  expect(alertSpy).toHaveBeenCalledTimes(1);
  expect(alertSpy.mock.calls[0][0]).toBe(TITLE);
  expect(alertSpy.mock.calls[0][1]).toBe(BODY);
  expect(String(alertSpy.mock.calls[0][1])).not.toMatch(/\d/);
  expect(props.navigation.navigate).not.toHaveBeenCalledWith('Paywall', expect.anything());
  expect(props.navigation.navigate).not.toHaveBeenCalledWith('Paywall');
}

describe('S81-11 C1 / C2 -- text path CATEGORY_NOT_LIVE', () => {
  it('C1: a 400 renders the coming-soon Alert, never the Paywall', async () => {
    const props = await textError(NOT_LIVE_400());
    expectComingSoon(props);
  });

  it('C2: a 429 (retry_after_seconds 3600, refusal_daily) renders the same Alert, no seconds', async () => {
    const props = await textError(NOT_LIVE_429());
    expectComingSoon(props);
  });

  it('C1b: a success:false terminal carrying CATEGORY_NOT_LIVE renders the same Alert', async () => {
    const props = await textTerminalFalse({
      success: false,
      code: 'CATEGORY_NOT_LIVE',
      category: 'electronics',
      categories_live: ['fragrances'],
    });
    expectComingSoon(props);
  });
});

describe('S81-11 C3 -- link path CATEGORY_NOT_LIVE (R-S10B-15)', () => {
  it('a 400 renders the coming-soon Alert', async () => {
    const props = await urlReject(NOT_LIVE_400());
    expectComingSoon(props);
  });

  it('a 429 renders the same Alert, no seconds, no Paywall', async () => {
    const props = await urlReject(NOT_LIVE_429());
    expectComingSoon(props);
  });

  it('a success:false body with CATEGORY_NOT_LIVE renders the same Alert', async () => {
    const props = await urlResolveFalse({ success: false, code: 'CATEGORY_NOT_LIVE' });
    expectComingSoon(props);
  });
});

describe('S81-11 C5 -- INSUFFICIENT_DATA reason copy (S81-20 additive, R-S11-26)', () => {
  const REASONS = ['same_identity', 'placeholder_identity', 'category_conflict'];
  for (const reason of REASONS) {
    it(`text: reason ${reason} -> its own sentence`, async () => {
      await textError(INSUFFICIENT(reason));
      const key = `home.errors.insufficientDataReason.${reason}`;
      expect(EN[key]).toBeDefined();
      expect(alertSpy.mock.calls[0][1]).toBe(EN[key]);
    });
    it(`link: reason ${reason} -> its own sentence`, async () => {
      await urlReject(INSUFFICIENT(reason));
      const key = `home.errors.insufficientDataReason.${reason}`;
      expect(EN[key]).toBeDefined();
      expect(alertSpy.mock.calls[0][1]).toBe(EN[key]);
    });
  }

  it('text: a reason under detail (legacy shape) is read too', async () => {
    await textError(
      axiosError(400, { detail: { code: 'INSUFFICIENT_DATA', reason: 'same_identity' } }),
    );
    expect(EN['home.errors.insufficientDataReason.same_identity']).toBeDefined();
    expect(alertSpy.mock.calls[0][1]).toBe(EN['home.errors.insufficientDataReason.same_identity']);
  });

  it('text: a success:false terminal forwards its reason', async () => {
    await textTerminalFalse({ success: false, code: 'INSUFFICIENT_DATA', reason: 'category_conflict' });
    expect(EN['home.errors.insufficientDataReason.category_conflict']).toBeDefined();
    expect(alertSpy.mock.calls[0][1]).toBe(
      EN['home.errors.insufficientDataReason.category_conflict'],
    );
  });
});

describe('S81-11 PIN rows -- absent = today (green at base)', () => {
  it('P2: INSUFFICIENT_DATA with no reason / no_evidence / an unknown reason -> today', async () => {
    for (const r of [undefined, 'no_evidence', 'brand_new_reason']) {
      alertSpy.mockClear();
      await textError(INSUFFICIENT(r));
      expect(alertSpy.mock.calls[0][1]).toBe(EN['home.errors.insufficientData']);
    }
    alertSpy.mockClear();
    await urlReject(INSUFFICIENT('no_evidence'));
    expect(alertSpy.mock.calls[0][1]).toBe(EN['home.errors.insufficientData']);
  });

  it('P3: 429 USAGE_LIMIT on text and link -> navigate(Paywall, {initialUsage})', async () => {
    const usage = {
      success: false,
      error: 'limit',
      code: 'USAGE_LIMIT',
      tier: 'free',
      reason: 'daily',
      used: 3,
      limit: 3,
    };
    const p1 = await textError(axiosError(429, usage));
    expect(p1.navigation.navigate).toHaveBeenCalledWith(
      'Paywall',
      expect.objectContaining({ initialUsage: expect.objectContaining({ code: 'USAGE_LIMIT' }) }),
    );
    expect(alertSpy).not.toHaveBeenCalled();
    const p2 = await urlReject(axiosError(429, usage));
    expect(p2.navigation.navigate).toHaveBeenCalledWith(
      'Paywall',
      expect.objectContaining({ initialUsage: expect.objectContaining({ code: 'USAGE_LIMIT' }) }),
    );
  });

  it('P4: RATE_LIMITED 429 with retry_after_seconds 5 keeps the seconds sentence', async () => {
    await textError(
      axiosError(429, { success: false, code: 'RATE_LIMITED', retry_after_seconds: 5 }),
    );
    expect(alertSpy).toHaveBeenCalledTimes(1);
    expect(alertSpy.mock.calls[0]?.[1]).toBe(
      EN['home.errors.rateLimited_other'].replace('{{count}}', '5'),
    );
    expect(alertSpy.mock.calls[0]?.[0]).toBe(EN['common.error']);
  });

  it('P4b: an engine outage keeps its own title + body', async () => {
    await textError(axiosError(503, { success: false, code: 'LLM_UNAVAILABLE' }));
    expect(alertSpy.mock.calls[0][0]).toBe(EN['home.errors.engineUnavailable.title']);
    expect(alertSpy.mock.calls[0][1]).toBe(EN['home.errors.engineUnavailable.body']);
  });
});

describe('S81-11 C7 -- errorCopy map (C12)', () => {
  const ec = () => require('../../src/services/errorCopy');

  it('CATEGORY_NOT_LIVE -> categoryNotLive / fragrancesOnly', () => {
    expect(ec().friendlyErrorKey('CATEGORY_NOT_LIVE')).toBe(BODY_KEY);
    expect(ec().friendlyErrorTitleKey('CATEGORY_NOT_LIVE')).toBe(TITLE_KEY);
  });

  it('INSUFFICIENT_DATA + reason -> the reason key; no_evidence / unknown / none -> today', () => {
    const f = ec().friendlyErrorKey as (c: any, r?: any) => string;
    expect(f('INSUFFICIENT_DATA', 'same_identity')).toBe(
      'home.errors.insufficientDataReason.same_identity',
    );
    expect(f('INSUFFICIENT_DATA', 'placeholder_identity')).toBe(
      'home.errors.insufficientDataReason.placeholder_identity',
    );
    expect(f('INSUFFICIENT_DATA', 'category_conflict')).toBe(
      'home.errors.insufficientDataReason.category_conflict',
    );
  });

  it('PIN: the single-argument results are unchanged (absent reason = today)', () => {
    const f = ec().friendlyErrorKey as (c: any, r?: any) => string;
    expect(f('INSUFFICIENT_DATA')).toBe('home.errors.insufficientData');
    expect(f('INSUFFICIENT_DATA', 'no_evidence')).toBe('home.errors.insufficientData');
    expect(f('INSUFFICIENT_DATA', 'whatever')).toBe('home.errors.insufficientData');
    expect(f('INSUFFICIENT_DATA', 42)).toBe('home.errors.insufficientData');
    expect(f('RATE_LIMITED', 'same_identity')).toBe('home.errors.rateLimited');
    expect(f('LLM_UNAVAILABLE')).toBe('home.errors.engineUnavailable.body');
    expect(f(null)).toBe('home.errors.comparison');
    expect(f(undefined)).toBe('home.errors.comparison');
    expect(ec().friendlyErrorTitleKey('RATE_LIMITED')).toBe('common.error');
    expect(ec().friendlyErrorTitleKey(null)).toBe('common.error');
  });

  it('every key the map can return exists in both catalogs', () => {
    const AR = require('../../src/i18n/ar.json') as Record<string, string>;
    const f = ec().friendlyErrorKey as (c: any, r?: any) => string;
    const keys = new Set<string>([
      f('CATEGORY_NOT_LIVE'),
      ec().friendlyErrorTitleKey('CATEGORY_NOT_LIVE'),
      f('INSUFFICIENT_DATA', 'same_identity'),
      f('INSUFFICIENT_DATA', 'placeholder_identity'),
      f('INSUFFICIENT_DATA', 'category_conflict'),
    ]);
    for (const k of keys) {
      expect(typeof EN[k]).toBe('string');
      expect(typeof AR[k]).toBe('string');
    }
  });
});
