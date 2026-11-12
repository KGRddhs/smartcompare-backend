/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-08 CLIENT-FIRST-OTA RED - rows G1..G11 + L1 (spec 2.7 / 3.8-3.10 as
 * amended by RULINGS_S81_08 R-S08-2: the reset time renders only on the DAILY
 * axis - the sheet's daily state always; the sheet's open / unknown states and
 * the Home pill ONLY when the status names the counted axis (`counted_scope`
 * on /usage/status, `scope` on the USAGE_LIMIT 429 detail, rendered for
 * 'daily' / 'device_daily' only); R-S08-8 the sheet rule in the pure helper;
 * R-S08-13 the hook tolerates a missing used.lifetime; R-S08-14 precedence;
 * R-S08-1 / R-S08-5 / R-S08-15 Link mode mints its compare id at the call
 * site and its request is on the metered allowlist).
 *
 * The pill rule lives in the hook: `resetsAt` is non-null only for a daily
 * counted_scope (G7), so HomeScreen renders whatever resolves (G8 / G9 / G9b).
 * PaywallScreen renders through the LimitReachedSheet.s69 harness (a real
 * i18next instance over the real catalogs); HomeScreen through the
 * HomeScreen.rateLimitedSeconds.w314 harness. Plain jest.mock only. Every RED
 * row fails at base on an assertion. Synthetic values; Date.now pinned.
 */
import React from 'react';
import { render, waitFor, fireEvent, act, renderHook } from '@testing-library/react-native';

jest.mock('react-i18next', () => {
  const i18next = require('i18next');
  const enJson = require('../../src/i18n/en.json');
  const arJson = require('../../src/i18n/ar.json');
  const inst = i18next.createInstance();
  inst.init({
    lng: 'en',
    fallbackLng: 'en',
    resources: { en: { translation: enJson }, ar: { translation: arJson } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  });
  const t = (key: string, opts?: Record<string, unknown>) => inst.t(key, opts);
  return {
    useTranslation: () => ({ t, i18n: inst }),
    __inst: inst,
    initReactI18next: { type: '3rdParty', init: () => {} },
  };
});

let mockRouteParams: Record<string, unknown> | undefined;
jest.mock('@react-navigation/native', () => {
  const ReactRequired = require('react');
  return {
    useNavigation: () => ({ goBack: jest.fn(), navigate: jest.fn(), canGoBack: () => true, dispatch: jest.fn() }),
    useRoute: () => ({ key: 'Paywall-1', name: 'Paywall', params: mockRouteParams }),
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

jest.mock('expo-crypto', () => ({
  randomUUID: () => require('crypto').randomUUID().toUpperCase(),
  digestStringAsync: jest.fn(async () => 'f'.repeat(64)),
  CryptoDigestAlgorithm: { SHA256: 'SHA256' },
}));

const mockApiPost = jest.fn();
jest.mock('../../src/services/api', () => {
  const real = jest.requireActual('../../src/services/api');
  return {
    __esModule: true,
    default: { post: (...args: any[]) => mockApiPost(...args) },
    healthCheck: jest.fn().mockResolvedValue(true),
    streamComparison: jest.fn(() => ({ subscribe: jest.fn(), abort: jest.fn(), compareRequestId: null })),
    parseApiError: real.parseApiError,
    trackEvent: jest.fn(),
    COMPARE_TIMEOUT_MS: 35000,
    __real: real,
  };
});

const mockAuth = {
  getSavedUser: jest.fn(async () => ({ id: 'user-a-synthetic' })),
  getToken: jest.fn(async () => null),
};
jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...a: any[]) => (mockAuth.getSavedUser as any)(...a),
  getToken: (...a: any[]) => (mockAuth.getToken as any)(...a),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
}));

const mockGetUsageStatus = jest.fn();
jest.mock('../../src/services/usageService', () => ({
  getUsageStatus: (...a: unknown[]) => mockGetUsageStatus(...a),
  isUsageLimitError: () => false,
  getUsageLimitDetail: () => null,
}));

jest.mock('../../src/services/referralService', () => ({
  getReferralStatus: jest.fn().mockResolvedValue({
    monthly_bonus_comparisons: 1,
    bonus_referrer_name: 'Synthetic',
    bonus_expires_at: null,
  }),
}));

const mockCounter: { value: any } = { value: null };
jest.mock('../../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => mockCounter.value,
}));

const mockDF = {
  getDeviceFingerprint: jest.fn(),
  legacyDeviceFingerprintHash: jest.fn(),
  legacyFingerprintHeaderActive: jest.fn(() => true),
  getDeviceIdentity: jest.fn(),
  LEGACY_FINGERPRINT_HEADER_UNTIL_MS: Date.UTC(2027, 2, 31, 21, 0, 0),
  _resetCacheForTests: jest.fn(),
};
jest.mock('../../src/services/deviceFingerprint', () => mockDF);

jest.mock('../../src/components/CategorySelector', () => {
  const ReactRequired = require('react');
  return { __esModule: true, default: () => ReactRequired.createElement('View', { testID: 'mock-category-selector' }) };
});
jest.mock('../../src/components/QarenLogo', () => {
  const ReactRequired = require('react');
  return { __esModule: true, default: () => ReactRequired.createElement('View', { testID: 'mock-qaren-logo' }) };
});
jest.mock('../../src/components/TwoInputShell', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) => ReactRequired.createElement('View', { testID: 'mock-two-input-shell', ...props }),
  };
});
jest.mock('../../src/components/PaywallBanner', () => {
  const ReactRequired = require('react');
  return { __esModule: true, default: () => ReactRequired.createElement('View', { testID: 'mock-paywall-banner' }) };
});
jest.mock('../../src/components/HomeEditorialSections', () => {
  const ReactRequired = require('react');
  return { __esModule: true, default: () => ReactRequired.createElement('View', { testID: 'mock-home-editorial-sections' }) };
});
jest.mock('../../src/screens/LoadingScreenVariants', () => {
  const ReactRequired = require('react');
  return {
    LoadingScreenVariants: (props: any) =>
      ReactRequired.createElement('View', { ...props, testID: 'mock-loading-screen-variants' }),
  };
});
jest.mock('../../src/icons', () => ({ ScanIcon: () => null, LinkIcon: () => null, TypeIcon: () => null }));


// The screens load AFTER every mock and recorder above is initialised (the factories
// return module-scope recorders, so an import above them would hit the TDZ).
import PaywallScreen from '../../src/screens/PaywallScreen';
import HomeScreen from '../../src/screens/HomeScreen';
import en from '../../src/i18n/en.json';
const { __inst: inst } = require('react-i18next');
const EN = en as Record<string, string>;
const NOW = Date.UTC(2026, 9, 23, 9, 0, 0);
const H = 3600 * 1000;
const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const NEW = require('crypto').createHash('sha256').update('s81-08-new', 'utf8').digest('hex');

function localHHMM(epochMs: number): string {
  const d = new Date(epochMs);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}`;
}

function iso(epochMs: number): string {
  return new Date(epochMs).toISOString();
}

function status(over: Record<string, unknown> = {}): any {
  return {
    tier: 'free',
    used: { daily: 3, monthly: 3, lifetime: 3 },
    limits: { daily: 3, monthly: 10, lifetime_free: 3, monthly_base: 10, monthly_bonus: 0 },
    remaining: { daily: 0, monthly: 7, lifetime_free: 0 },
    ...over,
  };
}

const OPEN = { remaining: { daily: 2, monthly: 9, lifetime_free: 0 }, used: { daily: 1, monthly: 1, lifetime: 3 } };
const MONTHLY = { remaining: { daily: 2, monthly: 0, lifetime_free: 0 } };

async function sheet(fetched: any, initialUsage?: any): Promise<ReturnType<typeof render>> {
  mockGetUsageStatus.mockResolvedValue(fetched);
  mockRouteParams = initialUsage ? { initialUsage } : undefined;
  const screen = render(<PaywallScreen />);
  await waitFor(() => expect(mockGetUsageStatus).toHaveBeenCalled());
  await act(async () => {
    await new Promise((r) => setImmediate(r));
  });
  return screen;
}

function resetsText(screen: any): string | null {
  const node = screen.queryByTestId('paywall-resets');
  if (!node) return null;
  const c = node.props.children;
  return Array.isArray(c) ? c.join('') : String(c);
}

const timeLine = (lng: string, at: number) =>
  inst.t('paywall.limit.resets_at', { lng, time: localHHMM(at) });

let dateSpy: jest.SpyInstance | null = null;

beforeEach(() => {
  jest.clearAllMocks();
  mockRouteParams = undefined;
  mockGetUsageStatus.mockReset();
  mockAuth.getSavedUser.mockResolvedValue({ id: 'user-a-synthetic' });
  mockDF.getDeviceFingerprint.mockResolvedValue(NEW);
  mockCounter.value = { used: 1, total: 3, canCompare: true, increment: jest.fn(async () => 2), resetsAt: null };
  dateSpy = jest.spyOn(Date, 'now').mockReturnValue(NOW);
});

afterEach(async () => {
  if (dateSpy) dateSpy.mockRestore();
  dateSpy = null;
  await inst.changeLanguage('en');
});

describe('S81-08 G - the limit sheet reset line (PaywallScreen)', () => {
  it('G1 daily state + resets_at -> the exact local time line', async () => {
    const at = NOW + 5 * H;
    const screen = await sheet(status({ resets_at: iso(at), counted_scope: 'daily' }));
    expect(EN['paywall.limit.resets_at']).toBeDefined();
    expect(resetsText(screen)).toBe(timeLine('en', at));
  });

  it('G2 (PIN, full config) daily state, no reset field -> resets_daily byte for byte', async () => {
    const screen = await sheet(status({ counted_scope: 'daily' }));
    expect(resetsText(screen)).toBe(EN['paywall.limit.resets_daily']);
  });

  it('G3 the 429 fallback: no fetched status, retry_after_seconds 3600 -> the time of now + 1 h', async () => {
    const screen = await sheet(null, { reason: 'daily_limit', code: 'USAGE_LIMIT', retry_after_seconds: 3600 });
    expect(resetsText(screen)).toBe(timeLine('en', NOW + H));
  });

  it('G4 (PIN, full config) the monthly state keeps resets_monthly even with a daily reset time', async () => {
    const screen = await sheet(status({ ...MONTHLY, resets_at: iso(NOW + 5 * H), counted_scope: 'daily' }));
    expect(resetsText(screen)).toBe(EN['paywall.limit.resets_monthly']);
  });

  it('G5 open / unknown states show the time ONLY on a daily axis (counted_scope / scope)', async () => {
    const at = NOW + 5 * H;
    const open = await sheet(status({ ...OPEN, resets_at: iso(at), counted_scope: 'device_daily' }));
    expect(resetsText(open)).toBe(timeLine('en', at));
    open.unmount();
    const unknown = await sheet(null, { code: 'USAGE_LIMIT', resets_at: iso(at), scope: 'daily' });
    expect(resetsText(unknown)).toBe(timeLine('en', at));
  });

  it('G5b (PIN, full config) open state without a daily axis keeps the base tree: no resets line', async () => {
    const at = NOW + 5 * H;
    const noScope = await sheet(status({ ...OPEN, resets_at: iso(at) }));
    expect(resetsText(noScope)).toBeNull();
    noScope.unmount();
    const lifetime = await sheet(status({ ...OPEN, resets_at: iso(at), counted_scope: 'lifetime' }));
    expect(resetsText(lifetime)).toBeNull();
  });

  it('G6 (PIN) unknown state keeps resets_unknown (nothing present, or a time without a daily scope)', async () => {
    const bare = await sheet(null);
    expect(resetsText(bare)).toBe(EN['paywall.limit.resets_unknown']);
    bare.unmount();
    const noScope = await sheet(null, { code: 'USAGE_LIMIT', resets_at: iso(NOW + 5 * H) });
    expect(resetsText(noScope)).toBe(EN['paywall.limit.resets_unknown']);
  });

  it('G10 Arabic: the AR time line carries the ASCII HH:MM and no Arabic-Indic digit', async () => {
    await inst.changeLanguage('ar');
    const at = NOW + 5 * H;
    const screen = await sheet(status({ resets_at: iso(at), counted_scope: 'daily' }));
    const line = resetsText(screen) ?? '';
    expect(line).toBe(timeLine('ar', at));
    expect(line).toContain(localHHMM(at));
    expect(/[\u0660-\u0669]/.test(line)).toBe(false);
  });

  it('G11 the fetched /usage/status decides first: its resets_at beats the 429 retry value', async () => {
    const fetchedAt = NOW + 2 * H;
    const screen = await sheet(status({ resets_at: iso(fetchedAt), counted_scope: 'daily' }), {
      reason: 'daily_limit',
      retry_after_seconds: 5 * 3600,
    });
    expect(resetsText(screen)).toBe(timeLine('en', fetchedAt));
  });
});

describe('S81-08 G - the hook and the Home pill', () => {
  const realHook = () =>
    jest.requireActual('../../src/hooks/useComparisonCounter').useComparisonCounter as () => any;

  async function hookResetsAt(s: any): Promise<any> {
    mockGetUsageStatus.mockResolvedValue(s);
    const { result } = renderHook(() => realHook()());
    await waitFor(() => expect(mockGetUsageStatus).toHaveBeenCalled());
    await act(async () => {
      await new Promise((r) => setImmediate(r));
    });
    return result.current;
  }

  it('G7 the hook exposes resetsAt only for a daily counted_scope with a string resets_at', async () => {
    const at = iso(NOW + 5 * H);
    const got = [
      (await hookResetsAt(status({ resets_at: at, counted_scope: 'daily' }))).resetsAt,
      (await hookResetsAt(status({ resets_at: at, counted_scope: 'device_daily' }))).resetsAt,
      (await hookResetsAt(status({ resets_at: at, counted_scope: 'lifetime' }))).resetsAt,
      (await hookResetsAt(status({ resets_at: at }))).resetsAt,
      (await hookResetsAt(status({ resets_at: 123, counted_scope: 'daily' }))).resetsAt,
      (await hookResetsAt(status({ counted_scope: 'daily' }))).resetsAt,
    ];
    expect(got).toEqual([at, at, null, null, null, null]);
  });

  it('G7b (R-S08-13) a status without used.lifetime is still accepted', async () => {
    const at = iso(NOW + 5 * H);
    const s = status({
      used: { daily: 1, monthly: 1 },
      remaining: { daily: 2, monthly: 9 },
      resets_at: at,
      counted_scope: 'device_daily',
    });
    const r = await hookResetsAt(s);
    expect(r.resetsAt).toBe(at);
    expect(r.canCompare).toBe(true);
  });

  async function home(): Promise<any> {
    const props: any = { navigation: { navigate: jest.fn(), goBack: jest.fn(), addListener: jest.fn(() => jest.fn()) } };
    const screen = render(<HomeScreen {...props} />);
    await waitFor(() => expect(screen.getByTestId('home-header-counter')).toBeTruthy());
    return screen;
  }

  it('G8 the pill with a reset: one extra resets node and the a11yResets label', async () => {
    const at = NOW + 5 * H;
    mockCounter.value = { ...mockCounter.value, resetsAt: iso(at) };
    const screen = await home();
    const time = localHHMM(at);
    expect(EN['home.headerCounter.resets']).toBeDefined();
    await waitFor(() =>
      expect(screen.getByTestId('home-header-counter').props.accessibilityLabel).toBe(
        inst.t('home.headerCounter.a11yResets', { free: 2, total: 3, bonus: 1, time }),
      ),
    );
    const node = screen.queryByTestId('home-header-counter-resets');
    expect(node).not.toBeNull();
    const c = node?.props.children;
    expect(Array.isArray(c) ? c.join('') : String(c)).toBe(inst.t('home.headerCounter.resets', { time }));
  });

  it('G9 (PIN, full config) the pill without a reset keeps the base tree and label', async () => {
    const screen = await home();
    await waitFor(() =>
      expect(screen.getByTestId('home-header-counter').props.accessibilityLabel).toBe(
        inst.t('home.headerCounter.a11y', { free: 2, total: 3, bonus: 1 }),
      ),
    );
    expect(screen.queryByTestId('home-header-counter-resets')).toBeNull();
  });

  it('G9b (PIN) a PAST resetsAt renders nothing new', async () => {
    mockCounter.value = { ...mockCounter.value, resetsAt: iso(NOW - H) };
    const screen = await home();
    await waitFor(() =>
      expect(screen.getByTestId('home-header-counter').props.accessibilityLabel).toBe(
        inst.t('home.headerCounter.a11y', { free: 2, total: 3, bonus: 1 }),
      ),
    );
    expect(screen.queryByTestId('home-header-counter-resets')).toBeNull();
  });

  it('L1 Link mode mints a lower-case v4 compare id at the call site and its request is metered', async () => {
    mockApiPost.mockResolvedValue({ data: { success: false, code: 'TIMEOUT' } });
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    try {
      const screen = await home();
      fireEvent.press(screen.getByTestId('home-mode-link'));
      const shell = await waitFor(() => screen.getByTestId('mock-two-input-shell'));
      await act(async () => {
        shell.props.onSubmit('https://example.invalid/a', 'https://example.invalid/b');
      });
      await waitFor(() => expect(mockApiPost).toHaveBeenCalled());
      const call = mockApiPost.mock.calls.find((c: any[]) => c[0] === '/api/v1/url/compare');
      expect(call).toBeDefined();
      const cfg = call ? call[2] : {};
      const idKey = Object.keys(cfg?.headers || {}).find((k) => k.toLowerCase() === 'x-compare-request-id');
      const id = idKey ? cfg.headers[idKey] : '';
      expect(id).toMatch(V4);
      const real = require('../../src/services/api').__real;
      const handler = real.default.interceptors.request.handlers.find((x: any) => x && x.fulfilled);
      const out = await handler.fulfilled({ ...cfg, url: '/api/v1/url/compare', method: 'post', headers: { ...(cfg?.headers || {}) } });
      const lower: Record<string, string> = {};
      Object.keys(out?.headers || {}).forEach((k) => {
        lower[k.toLowerCase()] = String(out.headers[k]);
      });
      expect(lower['x-compare-request-id']).toBe(id);
      expect(lower['x-device-fingerprint']).toBe(NEW);
      expect(lower['x-ai-consent-version']).toBe(String(require('../../src/services/aiConsent').AI_CONSENT_VERSION));
    } finally {
      alertSpy.mockRestore();
    }
  });
});
