/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-08 CLIENT-FIRST-OTA fix round 1: the gate rows of RULINGS_FIX1_S81_08
 * (F1-1, F1-2 = X4 / X6 / X9, F1-3, F1-4, F1-8, F1-9). The nine frozen RED
 * files stay byte-identical; every new row lives in this file.
 *
 * Two harnesses, in this order (load-bearing):
 *   1. The rendered rows (PaywallScreen, HomeScreen, the real
 *      useComparisonCounter) and the pure / global-mock rows run on the
 *      resetRender.s81_08 harness: plain top-level jest.mock, a real i18next
 *      instance over the real catalogs, Date.now pinned. F1-3a reads the
 *      global __tests__/setup.ts consent mock, which this harness leaves in
 *      place, so it runs before any row maps the module over it.
 *   2. The module-world rows (the request-path consent memo across accounts,
 *      logout, the X4 race, the deleted jest-only fallback, the legacy retry
 *      at register) start from jest.resetModules() (jest-runtime hands an
 *      isolated registry a mock the main registry has already cached) and
 *      build their own registry with jest.isolateModulesAsync + jest.doMock
 *      (the requestHeaders.s81_08 idiom), re-declaring every mock they need.
 *
 * Kinds: a RED row fails at the GREEN HEAD 3f990a69 on an expect assertion
 * only; a PIN row (title "(PIN ...)") passes there and is proven by the
 * mutant it names (spec M24; the correctness adversary's X4 / X6 / X9),
 * which turns it red. Synthetic values only.
 */
import React from 'react';
import { render, waitFor, act, renderHook } from '@testing-library/react-native';

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

// ---------------------------------------------------------------- module-world doubles --
// Used only by the module-world rows (section 2), after jest.resetModules().

const mockAsync: any = {
  store: {} as Record<string, string>,
  holds: {} as Record<string, Promise<string | null>>,
  getItem: jest.fn(async (key: string): Promise<string | null> => {
    const held = mockAsync.holds[key];
    if (held) {
      delete mockAsync.holds[key];
      return held;
    }
    return Object.prototype.hasOwnProperty.call(mockAsync.store, key) ? mockAsync.store[key] : null;
  }),
  setItem: jest.fn(async (key: string, value: string) => {
    mockAsync.store[key] = value;
  }),
  removeItem: jest.fn(async (key: string) => {
    delete mockAsync.store[key];
  }),
  multiRemove: jest.fn(async (keys: string[]) => {
    keys.forEach((k) => delete mockAsync.store[k]);
  }),
  multiGet: jest.fn(async (keys: string[]) => keys.map((k) => [k, mockAsync.store[k] ?? null])),
  multiSet: jest.fn(async (pairs: [string, string][]) => {
    pairs.forEach(([k, v]) => {
      mockAsync.store[k] = v;
    });
  }),
  getAllKeys: jest.fn(async () => Object.keys(mockAsync.store)),
  clear: jest.fn(async () => {
    mockAsync.store = {};
  }),
};

const mockSecure: any = {
  store: {} as Record<string, string>,
  failGets: 0,
  getItemAsync: jest.fn(async (key: string) => {
    if (mockSecure.failGets > 0) {
      mockSecure.failGets -= 1;
      throw new Error('keychain busy (synthetic)');
    }
    return Object.prototype.hasOwnProperty.call(mockSecure.store, key) ? mockSecure.store[key] : null;
  }),
  setItemAsync: jest.fn(async (key: string, value: string) => {
    mockSecure.store[key] = value;
  }),
  deleteItemAsync: jest.fn(async (key: string) => {
    delete mockSecure.store[key];
  }),
};

const mockWorldPost = jest.fn(async (..._a: any[]) => ({ data: { success: false, error: 'synthetic' } }));

const mockSentryRN: Record<string, jest.Mock> = {
  addBreadcrumb: jest.fn(),
  captureMessage: jest.fn(),
  captureException: jest.fn(),
  captureEvent: jest.fn(),
  setContext: jest.fn(),
  setExtra: jest.fn(),
  setTag: jest.fn(),
  setTags: jest.fn(),
  setUser: jest.fn(),
  init: jest.fn(),
};

// The screens load AFTER every mock and recorder above is initialised.
const PaywallScreen = require('../../src/screens/PaywallScreen').default;
const HomeScreen = require('../../src/screens/HomeScreen').default;
const EN = require('../../src/i18n/en.json') as Record<string, string>;
const { __inst: inst } = require('react-i18next');

const nodeCrypto = require('crypto');
const sha = (s: string): string => nodeCrypto.createHash('sha256').update(s, 'utf8').digest('hex');
const NEW = sha('s81-08-new');
const NOW = Date.UTC(2026, 9, 23, 9, 0, 0);
const H = 3600 * 1000;
const MINUTE = 60 * 1000;
const USER_A = 'user-a-synthetic';
const USER_B = 'user-b-synthetic';
const KEY_A = '@qaren_ai_consent_' + USER_A;
const USER_KEY = '@qaren_user';
const AT = new Date('2026-10-23T12:00:00.000Z');
const DOT = ' ' + String.fromCharCode(0xb7) + ' ';

function localHHMM(epochMs: number): string {
  const d = new Date(epochMs);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** The HH:MM the app shows for an instant: rounded to the nearest minute, device-local. */
function shownHHMM(epochMs: number): string {
  return localHHMM(Math.round(epochMs / MINUTE) * MINUTE);
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

function resetsText(screen: any): string | null {
  const node = screen.queryByTestId('paywall-resets');
  if (!node) return null;
  const c = node.props.children;
  return Array.isArray(c) ? c.join('') : String(c);
}

function findJson(node: any, testID: string): any {
  if (!node || typeof node !== 'object') return null;
  if (Array.isArray(node)) {
    for (const n of node) {
      const hit = findJson(n, testID);
      if (hit) return hit;
    }
    return null;
  }
  if (node.props && node.props.testID === testID) return node;
  return findJson(node.children, testID);
}

/** The pill's text runs in render order (one entry per host child). */
function pillRuns(screen: any): string[] {
  const pill = findJson(screen.toJSON(), 'home-header-counter');
  const kids: any[] = (pill && pill.children) || [];
  return kids.map((k: any) => (typeof k === 'string' ? k : (k.children || []).map(String).join('')));
}

async function flush(rounds = 30): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await new Promise<void>((r) => setImmediate(r));
  }
}

function iso_(fn: () => Promise<void>): Promise<void> {
  return jest.isolateModulesAsync(fn);
}

let dateSpy: jest.SpyInstance | null = null;

beforeEach(() => {
  jest.clearAllMocks();
  mockRouteParams = undefined;
  mockGetUsageStatus.mockReset();
  mockAuth.getSavedUser.mockResolvedValue({ id: USER_A });
  mockDF.getDeviceFingerprint.mockResolvedValue(NEW);
  mockDF.getDeviceIdentity.mockResolvedValue({ hash: NEW, source: 'securestore' });
  mockCounter.value = { used: 1, total: 3, canCompare: true, increment: jest.fn(async () => 2), resetsAt: null };
  mockAsync.store = {};
  mockAsync.holds = {};
  mockSecure.store = {};
  mockSecure.failGets = 0;
  dateSpy = jest.spyOn(Date, 'now').mockReturnValue(NOW);
});

afterEach(async () => {
  if (dateSpy) dateSpy.mockRestore();
  dateSpy = null;
  await inst.changeLanguage('en');
});

// ============================================================ section 1 =====

describe('S81-08 fix round 1 - the global consent mock, the sheet, the pill, the hook (RULINGS_FIX1 F1-3 / F1-4 / F1-8 / F1-9 / X6)', () => {
  it('F1-3a the global setup.ts consent mock answers the request-path read like hasCurrentAiConsent (no user: false)', async () => {
    const consent = require('../../src/services/aiConsent');
    expect(jest.isMockFunction(consent.hasCurrentAiConsent)).toBe(true);
    expect(typeof consent.hasCurrentAiConsentForRequest).toBe('function');
    expect(await consent.hasCurrentAiConsentForRequest(USER_A)).toBe(true);
    expect(await consent.hasCurrentAiConsentForRequest(null)).toBe(false);
    consent.hasCurrentAiConsent.mockResolvedValueOnce(false);
    expect(await consent.hasCurrentAiConsentForRequest(USER_A)).toBe(false);
  });

  it('F1-4 a relative 429 reset is anchored once per initialUsage: the /usage/status re-render keeps the minute', async () => {
    const seconds = 3610;
    const anchored = inst.t('paywall.limit.resets_at', { time: shownHHMM(NOW + seconds * 1000) });
    // Self-check: 40 s later the same relative value lands on the next minute.
    expect(inst.t('paywall.limit.resets_at', { time: shownHHMM(NOW + 40 * 1000 + seconds * 1000) })).not.toBe(anchored);
    let resolveFetch: (v: any) => void = () => undefined;
    mockGetUsageStatus.mockImplementation(
      () =>
        new Promise((r) => {
          resolveFetch = r;
        }),
    );
    mockRouteParams = { initialUsage: { reason: 'daily_limit', code: 'USAGE_LIMIT', retry_after_seconds: seconds } };
    const screen = render(React.createElement(PaywallScreen));
    await waitFor(() => expect(mockGetUsageStatus).toHaveBeenCalled());
    expect(resetsText(screen)).toBe(anchored);
    dateSpy?.mockReturnValue(NOW + 40 * 1000);
    await act(async () => {
      resolveFetch(status());
      await new Promise((r) => setImmediate(r));
    });
    expect(screen.getByTestId('paywall-title').props.children).toBe(EN['paywall.dailyLimit']);
    expect(resetsText(screen)).toBe(anchored);
  });

  async function home(): Promise<any> {
    const props: any = { navigation: { navigate: jest.fn(), goBack: jest.fn(), addListener: jest.fn(() => jest.fn()) } };
    const screen = render(React.createElement(HomeScreen, props));
    await waitFor(() => expect(screen.getByTestId('home-header-counter')).toBeTruthy());
    return screen;
  }

  it('F1-9 the pill order: N/T free, then the resets node, then the bonus (the a11y label unchanged)', async () => {
    const at = NOW + 5 * H;
    mockCounter.value = { ...mockCounter.value, resetsAt: iso(at) };
    const screen = await home();
    const time = shownHHMM(at);
    await waitFor(() =>
      expect(screen.getByTestId('home-header-counter').props.accessibilityLabel).toBe(
        inst.t('home.headerCounter.a11yResets', { free: 2, total: 3, bonus: 1, time }),
      ),
    );
    expect(pillRuns(screen)).toEqual([
      '2/3 ' + inst.t('home.headerCounter.free'),
      DOT,
      inst.t('home.headerCounter.resets', { time }),
      DOT,
      '+1',
    ]);
  });

  it('F1-9b (PIN) without a reset the pill keeps the build-3 runs: N/T free, then the bonus', async () => {
    const screen = await home();
    await waitFor(() =>
      expect(screen.getByTestId('home-header-counter').props.accessibilityLabel).toBe(
        inst.t('home.headerCounter.a11y', { free: 2, total: 3, bonus: 1 }),
      ),
    );
    expect(pillRuns(screen)).toEqual(['2/3 ' + inst.t('home.headerCounter.free'), DOT, '+1']);
  });

  const realHook = () =>
    jest.requireActual('../../src/hooks/useComparisonCounter').useComparisonCounter as () => any;

  async function hookFor(s: any): Promise<any> {
    mockGetUsageStatus.mockResolvedValue(s);
    const { result } = renderHook(() => realHook()());
    await waitFor(() => expect(mockGetUsageStatus).toHaveBeenCalled());
    await act(async () => {
      await new Promise((r) => setImmediate(r));
    });
    return result;
  }

  const pill = (r: any) => ({ free: r.current.total - r.current.used, total: r.current.total });

  // remaining: lifetime math 3 - 0 = 3, the account daily axis 2, the device daily axis 1.
  const axisStatus = (scope: string) =>
    status({
      used: { daily: 1, monthly: 1, lifetime: 0 },
      remaining: { daily: 2, monthly: 9, lifetime_free: 3, device_daily: 1 },
      counted_scope: scope,
      resets_at: iso(NOW + 5 * H),
    });

  it('F1-8a a status naming a daily counted axis drives the pill count from THAT axis, minus local compares', async () => {
    const device = await hookFor(axisStatus('device_daily'));
    expect(pill(device)).toEqual({ free: 1, total: 3 });
    await act(async () => {
      await device.current.increment();
    });
    expect(pill(device)).toEqual({ free: 0, total: 3 });
    const daily = await hookFor(axisStatus('daily'));
    expect(pill(daily)).toEqual({ free: 2, total: 3 });
  });

  // lifetime math 3 - 2 = 1; the account daily axis would read 2, the device axis 0.
  const lifetimeStatus = (over: Record<string, unknown> = {}) =>
    status({
      used: { daily: 1, monthly: 1, lifetime: 2 },
      remaining: { daily: 2, monthly: 9, lifetime_free: 1, device_daily: 0 },
      ...over,
    });

  it('F1-8b (PIN) no counted axis, a non-daily one, or an axis without its remaining keep the lifetime math', async () => {
    const got = [
      pill(await hookFor(lifetimeStatus())),
      pill(await hookFor(lifetimeStatus({ counted_scope: 'monthly' }))),
      pill(await hookFor(lifetimeStatus({ counted_scope: 'lifetime' }))),
      pill(
        await hookFor(
          lifetimeStatus({ counted_scope: 'device_daily', remaining: { daily: 2, monthly: 9, lifetime_free: 1 } }),
        ),
      ),
    ];
    expect(got).toEqual([
      { free: 1, total: 3 },
      { free: 1, total: 3 },
      { free: 1, total: 3 },
      { free: 1, total: 3 },
    ]);
  });

  it('X6 (PIN, killed by X6) only-if-absent is case-insensitive: an explicit header in any case is never doubled', () => {
    const rc = require('../../src/services/requestContext');
    const explicit = sha('s81-08-explicit');
    const id = nodeCrypto.randomUUID();
    const headers: Record<string, string> = { 'x-device-fingerprint': explicit, 'X-AI-CONSENT-VERSION': '7' };
    const cfg: any = { headers };
    rc.mergeContextHeaders(cfg, {
      'X-Device-Fingerprint': NEW,
      'X-AI-Consent-Version': '2',
      'X-Compare-Request-Id': id,
    });
    expect(cfg.headers).toEqual({
      'x-device-fingerprint': explicit,
      'X-AI-CONSENT-VERSION': '7',
      'X-Compare-Request-Id': id,
    });
  });
});

// ============================================================ section 2 =====

function worldApiAndPlatform(): void {
  jest.doMock('@react-native-async-storage/async-storage', () => ({ __esModule: true, default: mockAsync }));
  jest.doMock('expo-secure-store', () => mockSecure);
  jest.doMock('expo-crypto', () => ({
    randomUUID: () => require('crypto').randomUUID(),
    digestStringAsync: async (_alg: string, raw: string) => sha(raw),
    getRandomBytesAsync: async (n: number) => new Uint8Array(n),
    CryptoDigestAlgorithm: { SHA256: 'SHA256' },
  }));
  jest.doMock('@sentry/react-native', () => ({ __esModule: true, ...mockSentryRN, default: mockSentryRN }));
  jest.doMock('../../src/services/api', () => ({
    __esModule: true,
    default: {
      post: (...a: any[]) => mockWorldPost(...a),
      get: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
    },
    API_BASE_URL: 'https://example.invalid',
    getOrStartRefresh: () => Promise.resolve({ success: false, token: null }),
    getInFlightRefresh: () => null,
  }));
}

/** The REAL aiConsent, requestContext and authService over in-memory storage; the device id is a recorder. */
function consentWorld(): any {
  worldApiAndPlatform();
  jest.doMock('../../src/services/deviceFingerprint', () => mockDF);
  jest.doMock('../../src/services/authService', () => jest.requireActual('../../src/services/authService'));
  jest.doMock('../../src/services/aiConsent', () => jest.requireActual('../../src/services/aiConsent'));
  return {
    auth: require('../../src/services/authService'),
    consent: require('../../src/services/aiConsent'),
    rc: require('../../src/services/requestContext'),
  };
}

function signIn(userId: string): void {
  mockAsync.store[USER_KEY] = JSON.stringify({ id: userId });
}

async function consentHeader(w: any): Promise<string | undefined> {
  const h = (await w.rc.buildContextHeaders()) || {};
  expect(h['X-Device-Fingerprint']).toBe(NEW);
  const hit = Object.keys(h).find((k) => k.toLowerCase() === 'x-ai-consent-version');
  return hit ? String(h[hit]) : undefined;
}

describe('S81-08 fix round 1 - module worlds: the per-account consent memo, logout, X4, the deleted fallback, X9', () => {
  beforeEach(() => {
    jest.resetModules();
  });

  it('F1-1a (PIN, killed by M24) A agrees, then the saved user becomes B with NO signed-out read: B gets no consent header', () =>
    iso_(async () => {
      const w = consentWorld();
      const version = String(w.consent.AI_CONSENT_VERSION);
      await w.consent.recordAiConsent(USER_A, AT);
      signIn(USER_A);
      expect(await consentHeader(w)).toBe(version);
      signIn(USER_B);
      expect(await consentHeader(w)).toBeUndefined();
      signIn(USER_A);
      expect(await consentHeader(w)).toBe(version);
    }));

  it('F1-1b (PIN, killed by M24) B after a non-consented B, B agrees, and A only while A holds a record', () =>
    iso_(async () => {
      const w = consentWorld();
      const version = String(w.consent.AI_CONSENT_VERSION);
      await w.consent.recordAiConsent(USER_A, AT);
      signIn(USER_B);
      expect(await consentHeader(w)).toBeUndefined();
      signIn(USER_A);
      expect(await consentHeader(w)).toBe(version);
      signIn(USER_B);
      await w.consent.recordAiConsent(USER_B, AT);
      expect(await consentHeader(w)).toBe(version);
      signIn(USER_A);
      expect(await consentHeader(w)).toBe(version);
      await w.consent.clearAiConsent(USER_A);
      signIn(USER_B);
      expect(await consentHeader(w)).toBe(version);
      signIn(USER_A);
      expect(await consentHeader(w)).toBeUndefined();
    }));

  it('F1-1c logout() drops the request-path consent memo (the next request of the next session reads the record again)', () =>
    iso_(async () => {
      const w = consentWorld();
      const version = String(w.consent.AI_CONSENT_VERSION);
      await w.consent.recordAiConsent(USER_A, AT);
      signIn(USER_A);
      expect(await consentHeader(w)).toBe(version);
      // The record goes away outside the consent API (no memo drop): the memo
      // still answers for A until something drops it.
      delete mockAsync.store[KEY_A];
      expect(await consentHeader(w)).toBe(version);
      let logoutError: unknown = null;
      try {
        await w.auth.logout();
      } catch (e) {
        logoutError = e;
      }
      expect(logoutError).toBeNull();
      expect(Object.prototype.hasOwnProperty.call(mockAsync.store, USER_KEY)).toBe(false);
      signIn(USER_A);
      expect(await consentHeader(w)).toBeUndefined();
    }));

  it('X4 (PIN, killed by X4) a read racing an Agree never memoises the stale false (the generation guard)', () =>
    iso_(async () => {
      const w = consentWorld();
      const version = String(w.consent.AI_CONSENT_VERSION);
      signIn(USER_A);
      let release: (v: string | null) => void = () => undefined;
      mockAsync.holds[KEY_A] = new Promise<string | null>((r) => {
        release = r;
      });
      const racing = w.rc.buildContextHeaders();
      await flush();
      expect(mockAsync.getItem).toHaveBeenCalledWith(KEY_A);
      expect(Object.prototype.hasOwnProperty.call(mockAsync.holds, KEY_A)).toBe(false);
      await w.consent.recordAiConsent(USER_A, AT);
      release(null);
      const first = (await racing) || {};
      expect(first['X-AI-Consent-Version']).toBeUndefined();
      expect(await consentHeader(w)).toBe(version);
    }));

  it('F1-3b no jest-only fallback: a consent module without the request-path read sends no consent header', () =>
    iso_(async () => {
      worldApiAndPlatform();
      jest.doMock('../../src/services/deviceFingerprint', () => mockDF);
      jest.doMock('../../src/services/authService', () => ({
        getSavedUser: async () => ({ id: USER_A }),
        getToken: async () => null,
      }));
      const hasCurrent = jest.fn(async () => true);
      jest.doMock('../../src/services/aiConsent', () => ({
        __esModule: true,
        AI_CONSENT_VERSION: 2,
        hasCurrentAiConsent: hasCurrent,
      }));
      const rc = require('../../src/services/requestContext');
      const h = (await rc.buildContextHeaders()) || {};
      expect(h['X-Device-Fingerprint']).toBe(NEW);
      expect(h['X-AI-Consent-Version']).toBeUndefined();
      expect(hasCurrent).not.toHaveBeenCalled();
    }));

  it('X9 (PIN, killed by X9) a failed legacy SecureStore read is retried at the next register, never latched', () =>
    iso_(async () => {
      worldApiAndPlatform();
      const idfv = 'IDFV-SYNTHETIC-0001';
      jest.doMock('expo-application', () => ({
        applicationId: 'app.qaren.test',
        getIosIdForVendorAsync: async () => idfv,
        getAndroidId: () => '',
      }));
      jest.doMock('expo-device', () => ({ osBuildId: 'iPhone15,2/21D', osInternalBuildId: null }));
      jest.doMock('../../src/services/deviceFingerprint', () =>
        jest.requireActual('../../src/services/deviceFingerprint'),
      );
      jest.doMock('../../src/services/authService', () => jest.requireActual('../../src/services/authService'));
      const RN = require('react-native');
      RN.Platform.OS = 'ios';
      const auth = require('../../src/services/authService');
      const nonce = 'Synthetic-Nonce-X9';
      mockSecure.store.device_fp_nonce = nonce;
      const registerHeaders = async (): Promise<Record<string, string>> => {
        mockWorldPost.mockClear();
        const out = await auth.register('x9.user@example.invalid', 'pw-synthetic', {});
        expect(out && typeof out === 'object').toBe(true);
        const call = mockWorldPost.mock.calls.find((c: any[]) => c[0] === '/api/v1/auth/register');
        expect(call).toBeDefined();
        return ((call && call[2] && call[2].headers) || {}) as Record<string, string>;
      };
      // Register 1: SecureStore throws for the device read AND the legacy read.
      mockSecure.failGets = 2;
      const first = await registerHeaders();
      expect(mockSecure.failGets).toBe(0);
      expect(first['X-Device-Fingerprint']).toBe(sha(idfv.toLowerCase()));
      expect(first['X-Device-Fingerprint-Legacy']).toBeUndefined();
      // Register 2: SecureStore is back; the legacy value is read again.
      const second = await registerHeaders();
      expect(second['X-Device-Fingerprint']).toBe(sha(nonce.toLowerCase()));
      expect(second['X-Device-Fingerprint-Legacy']).toBe(sha(['app.qaren.test', 'iPhone15,2/21D', nonce].join('|')));
    }));
});
