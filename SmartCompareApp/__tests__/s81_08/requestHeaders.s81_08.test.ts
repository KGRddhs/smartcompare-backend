/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-08 CLIENT-FIRST-OTA RED - rows B1..B19 (spec section 5 as amended by
 * RULINGS_S81_08: R-S08-1 call-site compare ids (B3 dropped), R-S08-3
 * account-only consent, R-S08-4 + its amendment by R-S08B-1 / R-S08B-5 (the
 * legacy header ONLY at register and the two social sign-ins, never on
 * compares, usage, share or any other request), R-S08-5 (the device and
 * consent headers only on the metered allowlist marked at the call site),
 * R-S08-6 empty capabilities, R-S08-9 (B13, B14, B16), R-S08-12 (B19)).
 *
 * Every row drives the REAL call site (usageService.getUsageStatus,
 * authService.register, api.streamComparison's REST compare,
 * referralService.createShare, api.getComparisonHistory / submitFeedback)
 * against a fake axios instance, then runs the captured request config through
 * the REAL registered request interceptor, so the assertions hold whether a
 * header is set at the call site or by the interceptor. Each row builds its
 * own module world (jest.isolateModules + jest.doMock, review C17); every
 * world re-declares every mock it needs, so nothing leaks between rows.
 * Plain jest.doMock(name, factory) only, never virtual. New exports are read
 * through load() / typeof, outcomes are captured: every RED row fails at
 * base on an assertion. PIN rows run with the full configuration (device id,
 * legacy hash, consent record, token all resolvable) plus recorders (B1 rule).
 * Synthetic values only; Date.now pinned pre-cutoff unless a row says not.
 */

const nodeCrypto = require('crypto');

const sha = (s: string): string => nodeCrypto.createHash('sha256').update(s, 'utf8').digest('hex');
const NEW = sha('s81-08-new');
const LEG = sha('s81-08-legacy');
const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const HEX64 = /^[a-f0-9]{64}$/;
const PRE_CUTOFF_MS = Date.UTC(2026, 9, 23, 12, 0, 0);
const CUTOFF_MS = Date.UTC(2027, 2, 31, 21, 0, 0);
const USER_A = 'user-a-synthetic';
const BEARER_VALUE = 'bearer-synthetic-1';
const CONSENT_KEY = '@qaren_ai_consent_' + USER_A;

// ---------------------------------------------------------------- shared recorders --

const mockSecure: any = {
  store: {} as Record<string, string>,
  getItemAsync: jest.fn(async (key: string) =>
    Object.prototype.hasOwnProperty.call(mockSecure.store, key) ? mockSecure.store[key] : null,
  ),
  setItemAsync: jest.fn(async (key: string, value: string) => {
    mockSecure.store[key] = value;
  }),
  deleteItemAsync: jest.fn(async (key: string) => {
    delete mockSecure.store[key];
  }),
};

const mockAsync: any = {
  store: {} as Record<string, string>,
  failKeys: [] as string[],
  getItem: jest.fn(async (key: string) => {
    if (mockAsync.failKeys.includes(key)) throw new Error('storage busy');
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
  clear: jest.fn(async () => {
    mockAsync.store = {};
  }),
};

const mockDF = {
  getDeviceFingerprint: jest.fn(),
  legacyDeviceFingerprintHash: jest.fn(),
  legacyFingerprintHeaderActive: jest.fn(
    (nowMs?: number) => (typeof nowMs === 'number' ? nowMs : Date.now()) < Date.UTC(2027, 2, 31, 21, 0, 0),
  ),
  getDeviceIdentity: jest.fn(),
  LEGACY_FINGERPRINT_HEADER_UNTIL_MS: Date.UTC(2027, 2, 31, 21, 0, 0),
  _resetCacheForTests: jest.fn(),
};

const mockAuth = {
  getToken: jest.fn(),
  getSavedUser: jest.fn(),
};

const mockCryptoState: { uuid: () => string } = { uuid: () => nodeCrypto.randomUUID().toUpperCase() };

const mockSentrySvc: Record<string, jest.Mock> = {
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: jest.fn((s: string) => s),
  scrubBeforeSend: jest.fn((e: any) => e),
  scrubBeforeBreadcrumb: jest.fn((b: any) => b),
  scrubBeforeSendTransaction: jest.fn((e: any) => e),
};

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

const mockGlobalConsent = {
  __esModule: true,
  AI_CONSENT_VERSION: 2,
  AI_CONSENT_KEY_PREFIX: '@qaren_ai_consent_',
  aiConsentStorageKey: (u: string) => `@qaren_ai_consent_${u}`,
  readAiConsent: jest.fn(async () => null),
  hasCurrentAiConsent: jest.fn(async () => true),
  recordAiConsent: jest.fn(async () => undefined),
  clearAiConsent: jest.fn(async () => undefined),
  ensureAiConsent: jest.fn(async () => true),
  useAiConsentGate: () => ({ withAiConsent: (a: () => void) => a(), sheetProps: {} }),
};

// ---------------------------------------------------------------- helpers --

type WorldOpts = {
  df?: 'mock' | 'partial' | 'real';
  consent?: 'real' | 'global';
};

function load(path: string): any {
  try {
    return require(path);
  } catch {
    return null;
  }
}

async function flush(rounds = 30): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await new Promise<void>((r) => setImmediate(r));
  }
}

/**
 * Every row runs inside jest.isolateModulesAsync, so the lazy require() calls the
 * code makes while a request is built (api.ts requires ./authService at call
 * time) land in the row's own registry and never in the shared one.
 */
function iso(fn: () => Promise<void>): Promise<void> {
  return jest.isolateModulesAsync(fn);
}

/** The module world of one row: the real api / usage / auth / referral / consent code over fakes. */
function world(o: WorldOpts = {}): any {
  const w: any = {};
  const instanceFn: any = jest.fn();
  Object.assign(instanceFn, {
    get: jest.fn(async () => ({ data: { success: true } })),
    post: jest.fn(async () => ({ data: { success: false, error: 'synthetic' } })),
    put: jest.fn(async () => ({ data: {} })),
    delete: jest.fn(async () => ({ data: {} })),
    request: jest.fn(),
    interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } },
  });
  w.instance = instanceFn;
  {
    jest.doMock('axios', () => ({ create: jest.fn(() => instanceFn), __instance: instanceFn }));
    jest.doMock('../../src/services/certificatePinning', () => ({ setupCertificatePinning: jest.fn() }));
    jest.doMock('expo-image-manipulator', () => ({ manipulateAsync: jest.fn(), SaveFormat: { JPEG: 'jpeg' } }));
    jest.doMock('../../src/services/sentry', () => mockSentrySvc);
    jest.doMock('@sentry/react-native', () => ({ __esModule: true, ...mockSentryRN, default: mockSentryRN }));
    jest.doMock('expo-secure-store', () => mockSecure);
    jest.doMock('@react-native-async-storage/async-storage', () => ({ __esModule: true, default: mockAsync }));
    jest.doMock('expo-crypto', () => ({
      randomUUID: () => mockCryptoState.uuid(),
      digestStringAsync: async (_alg: string, raw: string) => sha(raw),
      getRandomBytesAsync: async (n: number) => new Uint8Array(n),
      CryptoDigestAlgorithm: { SHA256: 'SHA256' },
    }));
    jest.doMock('expo-application', () => ({
      applicationId: 'app.qaren.test',
      getIosIdForVendorAsync: async () => null,
      getAndroidId: () => '',
    }));
    jest.doMock('expo-device', () => ({ osBuildId: 'iPhone15,2/21D', osInternalBuildId: null }));
    if (o.df === 'real') {
      jest.dontMock('../../src/services/deviceFingerprint');
    } else if (o.df === 'partial') {
      jest.doMock('../../src/services/deviceFingerprint', () => ({
        getDeviceFingerprint: (...a: any[]) => mockDF.getDeviceFingerprint(...a),
      }));
    } else {
      jest.doMock('../../src/services/deviceFingerprint', () => mockDF);
    }
    if (o.consent === 'global') {
      jest.doMock('../../src/services/aiConsent', () => mockGlobalConsent);
    } else {
      jest.doMock('../../src/services/aiConsent', () => jest.requireActual('../../src/services/aiConsent'));
    }
    jest.doMock('../../src/services/authService', () => {
      const real = jest.requireActual('../../src/services/authService');
      return {
        __esModule: true,
        ...real,
        getToken: (...a: any[]) => mockAuth.getToken(...a),
        getSavedUser: (...a: any[]) => mockAuth.getSavedUser(...a),
      };
    });
    w.api = require('../../src/services/api');
    w.auth = require('../../src/services/authService');
    w.usage = require('../../src/services/usageService');
    w.referral = require('../../src/services/referralService');
    w.consent = require('../../src/services/aiConsent');
    w.df = require('../../src/services/deviceFingerprint');
    w.features = require('../../src/config/features');
    w.rc = load('../../src/services/requestContext');
  }
  w.interceptor = instanceFn.interceptors.request.use.mock.calls[0]?.[0];
  return w;
}

function lowerHeaders(h: any): Record<string, string> {
  const out: Record<string, string> = {};
  if (!h || typeof h !== 'object') return out;
  const src = typeof h.toJSON === 'function' ? h.toJSON() : h;
  for (const k of Object.keys(src)) {
    const v = src[k];
    if (v === undefined || v === null) continue;
    out[k.toLowerCase()] = String(v);
  }
  return out;
}

function cfgFrom(url: string, method: string, arg: any): any {
  const base = arg && typeof arg === 'object' ? { ...arg } : {};
  return { ...base, url, method, headers: { ...((arg && arg.headers) || {}) } };
}

async function through(w: any, cfg: any): Promise<any> {
  expect(typeof w.interceptor).toBe('function');
  return w.interceptor(cfg);
}

function lastCall(mockFn: jest.Mock, url: string): any[] | undefined {
  const calls = mockFn.mock.calls.filter((c: any[]) => c[0] === url);
  return calls[calls.length - 1];
}

async function usageConfig(w: any): Promise<any> {
  await w.usage.getUsageStatus();
  const call = lastCall(w.instance.get, '/api/v1/usage/status');
  expect(call).toBeDefined();
  return cfgFrom('/api/v1/usage/status', 'get', call ? call[1] : undefined);
}

async function usageHeaders(w: any): Promise<Record<string, string>> {
  const out = await through(w, await usageConfig(w));
  return lowerHeaders(out?.headers);
}

async function registerSent(w: any): Promise<{ arg: any; headers: Record<string, string> }> {
  let regError: any = null;
  try {
    await w.auth.register('synthetic.user@example.invalid', 'pw-synthetic', {});
  } catch (e) {
    regError = e;
  }
  expect(regError).toBeNull();
  const call = lastCall(w.instance.post, '/api/v1/auth/register');
  expect(call).toBeDefined();
  const arg = call ? call[2] : undefined;
  const out = await through(w, cfgFrom('/api/v1/auth/register', 'post', arg));
  return { arg, headers: lowerHeaders(out?.headers) };
}

async function restCompareSent(w: any): Promise<{ arg: any; headers: Record<string, string>; handle: any }> {
  w.features._setExpoFetchSseForTests?.(false);
  let handle: any = null;
  let startError: any = null;
  try {
    handle = w.api.streamComparison({ product_a: 'Alpha One', product_b: 'Beta Two' });
    handle.subscribe({ onComplete: jest.fn(), onError: jest.fn() });
  } catch (e) {
    startError = e;
  }
  expect(startError).toBeNull();
  await flush();
  const call = lastCall(w.instance.get, '/api/v1/text/compare');
  expect(call).toBeDefined();
  const arg = call ? call[1] : undefined;
  const out = await through(w, cfgFrom('/api/v1/text/compare', 'get', arg));
  return { arg, headers: lowerHeaders(out?.headers), handle };
}

function plantConsent(version: unknown): void {
  mockAsync.store[CONSENT_KEY] = JSON.stringify({ version, at: '2026-10-23T12:00:00.000Z' });
}

let dateSpy: jest.SpyInstance | null = null;

function consentVersion(w: any): string {
  return String(w.consent.AI_CONSENT_VERSION);
}

beforeEach(() => {
  mockSecure.store = {};
  mockAsync.store = {};
  mockAsync.failKeys = [];
  [mockSecure.getItemAsync, mockSecure.setItemAsync, mockAsync.getItem, mockAsync.setItem].forEach((m) =>
    m.mockClear(),
  );
  mockDF.getDeviceFingerprint.mockReset();
  mockDF.legacyDeviceFingerprintHash.mockReset();
  mockDF.getDeviceIdentity.mockReset();
  mockDF.legacyFingerprintHeaderActive.mockClear();
  mockDF.getDeviceFingerprint.mockResolvedValue(NEW);
  mockDF.legacyDeviceFingerprintHash.mockResolvedValue(LEG);
  mockDF.getDeviceIdentity.mockResolvedValue({ hash: NEW, source: 'securestore' });
  mockAuth.getToken.mockReset();
  mockAuth.getSavedUser.mockReset();
  mockAuth.getToken.mockResolvedValue(BEARER_VALUE);
  mockAuth.getSavedUser.mockResolvedValue({ id: USER_A });
  mockCryptoState.uuid = () => nodeCrypto.randomUUID().toUpperCase();
  Object.values(mockSentrySvc).forEach((m) => m.mockClear());
  Object.values(mockSentryRN).forEach((m) => m.mockClear());
  mockGlobalConsent.hasCurrentAiConsent.mockClear();
  plantConsent(2);
  dateSpy = jest.spyOn(Date, 'now').mockReturnValue(PRE_CUTOFF_MS);
});

afterEach(() => {
  jest.useRealTimers();
  if (dateSpy) dateSpy.mockRestore();
  dateSpy = null;
});

// ---------------------------------------------------------------- rows --

describe('S81-08 B - request context headers (axios interceptor + call-site markers)', () => {
  it('B1 /usage/status carries Authorization + X-Device-Fingerprint + X-AI-Consent-Version, nothing else', () =>
    iso(async () => {
    const w = world();
    const h = await usageHeaders(w);
    expect(h).toEqual({
      authorization: 'Bearer ' + BEARER_VALUE,
      'x-device-fingerprint': NEW,
      'x-ai-consent-version': consentVersion(w),
    });
    }));

  it('B2 newCompareRequestId lower-cases an upper-case v4 (NSUUID)', () =>
    iso(async () => {
    const upper = nodeCrypto.randomUUID().toUpperCase();
    mockCryptoState.uuid = () => upper;
    const w = world();
    expect(typeof w.rc?.newCompareRequestId).toBe('function');
    const id = typeof w.rc?.newCompareRequestId === 'function' ? w.rc.newCompareRequestId() : null;
    expect(id).toBe(upper.toLowerCase());
    expect(String(id)).toMatch(V4);
    }));

  it('B2b a non-v4 uuid (the root shim counter) -> no id, and the REST compare config has no headers key', () =>
    iso(async () => {
    mockCryptoState.uuid = () => '00000000-0000-0000-0000-000000000001';
    const w = world();
    expect(typeof w.rc?.newCompareRequestId).toBe('function');
    const id = typeof w.rc?.newCompareRequestId === 'function' ? w.rc.newCompareRequestId() : 'MISSING';
    expect(id).toBeNull();
    const sent = await restCompareSent(w);
    expect(sent.headers['x-compare-request-id']).toBeUndefined();
    expect(sent.arg && Object.prototype.hasOwnProperty.call(sent.arg, 'headers')).toBe(false);
    }));

  it('B4 only-if-absent: explicit device / id values survive, consent is still added', () =>
    iso(async () => {
    const w = world();
    const cfg = await usageConfig(w);
    const explicitId = nodeCrypto.randomUUID();
    cfg.headers['X-Device-Fingerprint'] = 'c'.repeat(64);
    cfg.headers['x-compare-request-id'] = explicitId;
    const h = lowerHeaders((await through(w, cfg))?.headers);
    expect(h['x-device-fingerprint']).toBe('c'.repeat(64));
    expect(h['x-compare-request-id']).toBe(explicitId);
    expect(h['x-ai-consent-version']).toBe(consentVersion(w));
    const names = Object.keys((await through(w, cfg))?.headers || {}).map((k) => k.toLowerCase());
    expect(names.filter((n) => n === 'x-device-fingerprint')).toHaveLength(1);
    expect(names.filter((n) => n === 'x-compare-request-id')).toHaveLength(1);
    }));

  it('B5 no current consent record -> no X-AI-Consent-Version; the device header is still sent', () =>
    iso(async () => {
    delete mockAsync.store[CONSENT_KEY];
    const w = world();
    const h = await usageHeaders(w);
    expect(h['x-ai-consent-version']).toBeUndefined();
    expect(h['x-device-fingerprint']).toBe(NEW);
    }));

  it('B6 (PIN, full config) Authorization unchanged: none without a token, Bearer with one, same config object', () =>
    iso(async () => {
    const w = world();
    mockAuth.getToken.mockResolvedValue(null);
    const cfgA = await usageConfig(w);
    const outA = await through(w, cfgA);
    expect(outA).toBe(cfgA);
    expect(lowerHeaders(outA.headers).authorization).toBeUndefined();
    mockAuth.getToken.mockResolvedValue('t');
    const cfgB = await usageConfig(w);
    const outB = await through(w, cfgB);
    expect(outB).toBe(cfgB);
    expect(lowerHeaders(outB.headers).authorization).toBe('Bearer t');
    }));

  it('B7 (PIN, full config) every builder failing never blocks the request: headers == {Authorization}', () =>
    iso(async () => {
    mockDF.getDeviceFingerprint.mockRejectedValue(new Error('device'));
    mockDF.legacyDeviceFingerprintHash.mockRejectedValue(new Error('legacy'));
    mockDF.getDeviceIdentity.mockRejectedValue(new Error('device'));
    mockAuth.getSavedUser.mockRejectedValue(new Error('user'));
    mockCryptoState.uuid = () => {
      throw new Error('uuid');
    };
    const w = world();
    const h = await usageHeaders(w);
    expect(h).toEqual({ authorization: 'Bearer ' + BEARER_VALUE });
    }));

  it('B8 at the cutoff: register drops the legacy header (no legacy read) and usage still carries the device id', () =>
    iso(async () => {
    dateSpy?.mockReturnValue(CUTOFF_MS);
    const w = world();
    const reg = await registerSent(w);
    expect(reg.headers['x-device-fingerprint']).toBe(NEW);
    expect(reg.headers['x-device-fingerprint-legacy']).toBeUndefined();
    expect(mockDF.legacyDeviceFingerprintHash).not.toHaveBeenCalled();
    const h = await usageHeaders(w);
    expect(h['x-device-fingerprint']).toBe(NEW);
    expect(h['x-device-fingerprint-legacy']).toBeUndefined();
    }));

  it('B9 capabilities ship empty: CLIENT_CAPABILITIES == [] and no X-Client-Capabilities header', () =>
    iso(async () => {
    const w = world();
    expect(w.rc).not.toBeNull();
    expect(w.rc?.CLIENT_CAPABILITIES).toEqual([]);
    const h = await usageHeaders(w);
    expect(h['x-client-capabilities']).toBeUndefined();
    }));

  it('B10 (PIN, full config) no header value, hash or id is ever logged or sent to Sentry', () =>
    iso(async () => {
    const spies = (['log', 'info', 'warn', 'error', 'debug'] as const).map((m) => jest.spyOn(console, m));
    try {
    const w = world();
    await usageHeaders(w);
    await registerSent(w);
    const sent = await restCompareSent(w);
    const id = sent.headers['x-compare-request-id'] || 'no-id-sent';
    const recorded = JSON.stringify([
      ...spies.map((s) => s.mock.calls),
      ...Object.values(mockSentrySvc).map((m) => m.mock.calls),
      ...Object.values(mockSentryRN).map((m) => m.mock.calls),
    ]);
    expect(recorded.includes(NEW)).toBe(false);
    expect(recorded.includes(LEG)).toBe(false);
    expect(recorded.includes(id)).toBe(false);
    } finally {
      spies.forEach((s) => s.mockRestore());
    }
    }));

  it('B11 shapes the server accepts (REAL deviceFingerprint, real sha256 digest)', () =>
    iso(async () => {
    mockSecure.store.device_fp_nonce = 'Synthetic-Nonce-B11';
    const w = world({ df: 'real' });
    const h = await usageHeaders(w);
    expect(h['x-device-fingerprint'] ?? '').toMatch(HEX64);
    expect(h['x-ai-consent-version'] ?? '').toMatch(/^[0-9]{1,3}$/);
    const reg = await registerSent(w);
    expect(reg.headers['x-device-fingerprint'] ?? '').toMatch(HEX64);
    expect(reg.headers['x-device-fingerprint-legacy'] ?? '').toMatch(HEX64);
    const sent = await restCompareSent(w);
    expect(sent.headers['x-compare-request-id'] ?? '').toMatch(V4);
    }));

  it('B12 register end-to-end: X-Device-Fingerprint NEW + X-Device-Fingerprint-Legacy LEG, no consent / id', () =>
    iso(async () => {
    const w = world();
    const reg = await registerSent(w);
    expect(reg.headers['x-device-fingerprint']).toBe(NEW);
    expect(reg.headers['x-device-fingerprint-legacy']).toBe(LEG);
    expect(reg.headers['x-ai-consent-version']).toBeUndefined();
    expect(reg.headers['x-compare-request-id']).toBeUndefined();
    }));

  it('B13 (R-S08-9) deviceFingerprint mocked with getDeviceFingerprint ONLY: usage gets device + consent, register no legacy', () =>
    iso(async () => {
    const w = world({ df: 'partial' });
    const h = await usageHeaders(w);
    expect(h).toEqual({
      authorization: 'Bearer ' + BEARER_VALUE,
      'x-device-fingerprint': NEW,
      'x-ai-consent-version': consentVersion(w),
    });
    const reg = await registerSent(w);
    expect(reg.headers['x-device-fingerprint']).toBe(NEW);
    expect(reg.headers['x-device-fingerprint-legacy']).toBeUndefined();
    }));

  it('B14a the device id failing ALONE leaves consent and Authorization', () =>
    iso(async () => {
    mockDF.getDeviceFingerprint.mockRejectedValue(new Error('device'));
    mockDF.getDeviceIdentity.mockRejectedValue(new Error('device'));
    const w = world();
    const h = await usageHeaders(w);
    expect(h).toEqual({
      authorization: 'Bearer ' + BEARER_VALUE,
      'x-ai-consent-version': consentVersion(w),
    });
    }));

  it('B14b the consent read failing ALONE (getSavedUser throws; storage throws) leaves the device header and Authorization', () =>
    iso(async () => {
    const w = world();
    mockAuth.getSavedUser.mockRejectedValue(new Error('user'));
    const thrown = await usageHeaders(w);
    expect(thrown).toEqual({ authorization: 'Bearer ' + BEARER_VALUE, 'x-device-fingerprint': NEW });
    mockAuth.getSavedUser.mockResolvedValue({ id: USER_A });
    mockAsync.failKeys = [CONSENT_KEY];
    const h = await usageHeaders(w);
    expect(h).toEqual({ authorization: 'Bearer ' + BEARER_VALUE, 'x-device-fingerprint': NEW });
    }));

  it('B14c (PIN, full config) the legacy hash failing ALONE: register is still sent with the device header', () =>
    iso(async () => {
    mockDF.legacyDeviceFingerprintHash.mockRejectedValue(new Error('legacy'));
    const w = world();
    const reg = await registerSent(w);
    expect(lastCall(w.instance.post, '/api/v1/auth/register')).toBeDefined();
    expect(reg.headers['x-device-fingerprint']).toBe(NEW);
    expect(reg.headers['x-device-fingerprint-legacy']).toBeUndefined();
    }));

  it('B14d the compare id failing ALONE: the REST compare keeps device + consent, no id, no headers key at the call site', () =>
    iso(async () => {
    mockCryptoState.uuid = () => {
      throw new Error('uuid');
    };
    const w = world();
    const sent = await restCompareSent(w);
    expect(sent.headers).toEqual({
      authorization: 'Bearer ' + BEARER_VALUE,
      'x-device-fingerprint': NEW,
      'x-ai-consent-version': consentVersion(w),
    });
    expect(sent.arg && Object.prototype.hasOwnProperty.call(sent.arg, 'headers')).toBe(false);
    }));

  it('B15 (PIN) a getSavedUser THROW or a signed-out device sends no consent header, even when the consent module says yes', () =>
    iso(async () => {
    const w = world({ consent: 'global' });
    mockAuth.getSavedUser.mockRejectedValue(new Error('user'));
    const thrown = await usageHeaders(w);
    expect(thrown['x-ai-consent-version']).toBeUndefined();
    expect(thrown.authorization).toBe('Bearer ' + BEARER_VALUE);
    mockAuth.getSavedUser.mockResolvedValue(null);
    const signedOut = await usageHeaders(w);
    expect(signedOut['x-ai-consent-version']).toBeUndefined();
    expect(signedOut.authorization).toBe('Bearer ' + BEARER_VALUE);
    }));

  it('B16 a never-settling device id read is bounded at 1,000 ms: the request leaves without it', () =>
    iso(async () => {
    mockDF.getDeviceFingerprint.mockImplementation(() => new Promise(() => undefined));
    mockDF.getDeviceIdentity.mockImplementation(() => new Promise(() => undefined));
    const w = world();
    const cfg = await usageConfig(w);
    jest.useFakeTimers({ doNotFake: ['Date', 'setImmediate', 'nextTick', 'queueMicrotask'] });
    let done = false;
    let out: any = null;
    expect(typeof w.interceptor).toBe('function');
    Promise.resolve(w.interceptor(cfg)).then((c: any) => {
      done = true;
      out = c;
    });
    await jest.advanceTimersByTimeAsync(1000);
    for (let i = 0; i < 20; i++) await Promise.resolve();
    jest.useRealTimers();
    expect(done).toBe(true);
    const h = lowerHeaders(out?.headers);
    expect(h['x-device-fingerprint']).toBeUndefined();
    expect(h['x-ai-consent-version']).toBe(consentVersion(w));
    expect(h.authorization).toBe('Bearer ' + BEARER_VALUE);
    }));

  it('B17 (PIN, R-S08B-5) the share call carries no legacy header; the body keeps the device value', () =>
    iso(async () => {
    const w = world();
    const input = { comparison_id: 'cmp-synthetic', device_fingerprint_hash: NEW };
    await w.referral.createShare(input);
    const call = lastCall(w.instance.post, '/api/v1/referrals/share');
    expect(call).toBeDefined();
    expect(call ? call[1] : null).toEqual(input);
    const out = await through(w, cfgFrom('/api/v1/referrals/share', 'post', call ? call[2] : undefined));
    const h = lowerHeaders(out?.headers);
    expect(h['x-device-fingerprint-legacy']).toBeUndefined();
    expect(mockDF.legacyDeviceFingerprintHash).not.toHaveBeenCalled();
    }));

  it('B18 (PIN, R-S08-5) requests off the metered allowlist get no device / legacy / consent / id header', () =>
    iso(async () => {
    const w = world();
    await w.api.getComparisonHistory(5, 0);
    await w.api.submitFeedback({ useful: true });
    const configs = [
      cfgFrom('/api/v1/comparisons/history', 'get', lastCall(w.instance.get, '/api/v1/comparisons/history')?.[1]),
      cfgFrom('/api/v1/feedback', 'post', lastCall(w.instance.post, '/api/v1/feedback')?.[2]),
      cfgFrom('/api/v1/legal/privacy', 'get', undefined),
      cfgFrom('/api/v1/events', 'post', undefined),
      cfgFrom('/api/v1/auth/refresh', 'post', undefined),
    ];
    for (const cfg of configs) {
      const h = lowerHeaders((await through(w, cfg))?.headers);
      expect({ url: cfg.url, h }).toEqual({ url: cfg.url, h: { authorization: 'Bearer ' + BEARER_VALUE } });
    }
    }));

  it('B19 (R-S08-12) Sentry redacts the two fingerprint request headers by name', () =>
    iso(async () => {
    jest.doMock('@sentry/react-native', () => ({ __esModule: true, ...mockSentryRN, default: mockSentryRN }));
    jest.doMock('../../src/services/sentry', () => jest.requireActual('../../src/services/sentry'));
    const sentry = require('../../src/services/sentry');
    const event = {
      request: {
        url: 'https://example.invalid/api/v1/usage/status',
        headers: {
          'X-Device-Fingerprint': 'fp-value-synthetic',
          'x-device-fingerprint-legacy': 'legacy-value-synthetic',
          'X-AI-Consent-Version': '2',
        },
      },
    };
    const out = sentry.scrubBeforeSend(event, {});
    expect(out.request.headers['X-Device-Fingerprint']).toBe('[REDACTED]');
    expect(out.request.headers['x-device-fingerprint-legacy']).toBe('[REDACTED]');
    expect(out.request.headers['X-AI-Consent-Version']).toBe('2');
    }));
});
