/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-08 CLIENT-FIRST-OTA RED - rows C1..C6: the camera raw-fetch attempts
 * (spec section 5 as amended by RULINGS_S81_08: R-S08-1 one compare id minted
 * per identifyFromImages call and sent on both attempts; R-S08-4 as amended by
 * R-S08B-1 / R-S08B-5: NO legacy header on the camera; R-S08-9 C5: a builder
 * failure never blocks the upload or the U13c retry; R-S08-15: the id is
 * exposed additively to the caller).
 *
 * Drives the REAL identifyFromImages with a mocked global fetch (the U13c
 * harness shapes). The consent record is the REAL aiConsent over an in-memory
 * AsyncStorage. Plain jest.mock(name, factory) only. Every RED row fails at
 * base on an assertion. Synthetic values only; Date.now pinned pre-cutoff.
 */

const nodeCrypto = require('crypto');

const sha = (s: string): string => nodeCrypto.createHash('sha256').update(s, 'utf8').digest('hex');
const NEW = sha('s81-08-new');
const LEG = sha('s81-08-legacy');
const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const PRE_CUTOFF_MS = Date.UTC(2026, 9, 23, 12, 0, 0);
const USER_A = 'user-a-synthetic';
const CONSENT_KEY = '@qaren_ai_consent_' + USER_A;
const URIS = ['file:///synthetic-a.jpg', 'file:///synthetic-b.jpg'];

jest.mock('../../src/services/certificatePinning', () => ({ setupCertificatePinning: jest.fn() }));

const mockAuthState = { token: 'bearer-old-synthetic' as string | null };
const mockAuth = {
  getToken: jest.fn(async () => mockAuthState.token),
  getSavedUser: jest.fn(async () => ({ id: 'user-a-synthetic' })),
  refreshSession: jest.fn(async () => {
    mockAuthState.token = 'bearer-new-synthetic';
    return { success: true };
  }),
  clearSession: jest.fn(async () => undefined),
};
jest.mock('../../src/services/authService', () => ({
  getToken: (...a: any[]) => (mockAuth.getToken as any)(...a),
  getSavedUser: (...a: any[]) => (mockAuth.getSavedUser as any)(...a),
  refreshSession: (...a: any[]) => (mockAuth.refreshSession as any)(...a),
  clearSession: (...a: any[]) => (mockAuth.clearSession as any)(...a),
}));

jest.mock('axios', () => {
  const instance: any = jest.fn();
  Object.assign(instance, {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    request: jest.fn(),
    interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } },
  });
  return { create: jest.fn(() => instance), __instance: instance };
});

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(async (uri: string) => ({ uri: uri + '.jpg' })),
  SaveFormat: { JPEG: 'jpeg' },
}));

jest.mock('../../src/services/sentry', () => ({
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: (s: string) => s,
  scrubBeforeSend: (e: any) => e,
}));

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
jest.mock('../../src/services/deviceFingerprint', () => mockDF);

const mockUuid: { next: () => string } = { next: () => nodeCrypto.randomUUID() };
jest.mock('expo-crypto', () => ({
  randomUUID: () => mockUuid.next(),
  digestStringAsync: jest.fn(async () => 'f'.repeat(64)),
  CryptoDigestAlgorithm: { SHA256: 'SHA256' },
}));

const mockAsync: any = {
  store: {} as Record<string, string>,
  getItem: jest.fn(async (k: string) => (k in mockAsync.store ? mockAsync.store[k] : null)),
  setItem: jest.fn(async (k: string, v: string) => {
    mockAsync.store[k] = v;
  }),
  removeItem: jest.fn(async (k: string) => {
    delete mockAsync.store[k];
  }),
  multiRemove: jest.fn(async () => undefined),
  clear: jest.fn(async () => undefined),
};
jest.mock('@react-native-async-storage/async-storage', () => ({ __esModule: true, default: mockAsync }));

// The REAL consent module (the global setup mock is mapped back).
jest.mock('../../src/services/aiConsent', () => jest.requireActual('../../src/services/aiConsent'));

const api = require('../../src/services/api');
const consent = require('../../src/services/aiConsent');

function mkResponse(status: number, body: string) {
  let used = false;
  const read = (): Promise<string> => {
    if (used) return Promise.reject(new TypeError('Already read'));
    used = true;
    return Promise.resolve(body);
  };
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => read(),
    json: () => read().then((t) => JSON.parse(t)),
  };
}

const OK_BODY = JSON.stringify({ action: 'comparison', success: true, result: { overview: { winner: 'A' } } });
const AUTH_BODY = JSON.stringify({ success: false, code: 'AUTH_REQUIRED', error: 'x', request_id: 'r' });

let fetchMock: jest.Mock;
let originalFetch: any;
let dateSpy: jest.SpyInstance | null = null;

function queue(...rs: [number, string][]): void {
  rs.forEach(([s, b]) => fetchMock.mockResolvedValueOnce(mkResponse(s, b)));
}

function lowerHeaders(h: any): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of Object.keys(h || {})) {
    if (h[k] !== undefined && h[k] !== null) out[k.toLowerCase()] = String(h[k]);
  }
  return out;
}

function omitAuth(h: Record<string, string>): Record<string, string> {
  const out = { ...h };
  delete out.authorization;
  return out;
}

async function settle(p: Promise<any>): Promise<{ ok: boolean; value?: any; error?: any }> {
  try {
    return { ok: true, value: await p };
  } catch (error) {
    return { ok: false, error };
  }
}

beforeEach(() => {
  originalFetch = (global as any).fetch;
  fetchMock = jest.fn();
  (global as any).fetch = fetchMock;
  api.__resetRefreshMutex?.();
  mockAuthState.token = 'bearer-old-synthetic';
  mockAuth.getToken.mockClear();
  mockAuth.refreshSession.mockClear();
  mockAuth.getSavedUser.mockReset();
  mockAuth.getSavedUser.mockResolvedValue({ id: USER_A });
  mockDF.getDeviceFingerprint.mockReset();
  mockDF.legacyDeviceFingerprintHash.mockReset();
  mockDF.getDeviceIdentity.mockReset();
  mockDF.getDeviceFingerprint.mockResolvedValue(NEW);
  mockDF.legacyDeviceFingerprintHash.mockResolvedValue(LEG);
  mockDF.getDeviceIdentity.mockResolvedValue({ hash: NEW, source: 'securestore' });
  mockUuid.next = () => nodeCrypto.randomUUID();
  mockAsync.store = { [CONSENT_KEY]: JSON.stringify({ version: consent.AI_CONSENT_VERSION, at: '2026-10-23T12:00:00.000Z' }) };
  dateSpy = jest.spyOn(Date, 'now').mockReturnValue(PRE_CUTOFF_MS);
});

afterEach(() => {
  (global as any).fetch = originalFetch;
  if (dateSpy) dateSpy.mockRestore();
  dateSpy = null;
});

describe('S81-08 C - camera identify headers', () => {
  it('C1 attempt 1 carries Authorization + device + consent + a lower-case v4 id, and no legacy header', async () => {
    queue([200, OK_BODY]);
    const out = await settle(api.identifyFromImages(URIS, 'bahrain'));
    expect(out.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const h = lowerHeaders(fetchMock.mock.calls[0][1].headers);
    expect(h['x-compare-request-id'] ?? '').toMatch(V4);
    expect(h).toEqual({
      authorization: 'Bearer bearer-old-synthetic',
      'x-device-fingerprint': NEW,
      'x-ai-consent-version': String(consent.AI_CONSENT_VERSION),
      'x-compare-request-id': h['x-compare-request-id'],
    });
    expect(h['x-device-fingerprint-legacy']).toBeUndefined();
  });

  it('C2 the U13c 401 retry keeps the same context and the same id; only Authorization changes', async () => {
    queue([401, AUTH_BODY], [200, OK_BODY]);
    const out = await settle(api.identifyFromImages(URIS, 'bahrain'));
    expect(out.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const h1 = lowerHeaders(fetchMock.mock.calls[0][1].headers);
    const h2 = lowerHeaders(fetchMock.mock.calls[1][1].headers);
    expect(h2.authorization).toBe('Bearer bearer-new-synthetic');
    expect(omitAuth(h2)).toEqual(omitAuth(h1));
    expect(h1['x-compare-request-id'] ?? '').toMatch(V4);
    expect(h1['x-device-fingerprint']).toBe(NEW);
  });

  it('C3 one id per call: two identify calls send two distinct ids', async () => {
    queue([200, OK_BODY], [200, OK_BODY]);
    await settle(api.identifyFromImages(URIS, 'bahrain'));
    await settle(api.identifyFromImages(URIS, 'bahrain'));
    const a = lowerHeaders(fetchMock.mock.calls[0][1].headers)['x-compare-request-id'];
    const b = lowerHeaders(fetchMock.mock.calls[1][1].headers)['x-compare-request-id'];
    expect(a ?? '').toMatch(V4);
    expect(b ?? '').toMatch(V4);
    expect(a).not.toBe(b);
  });

  it('C4 (PIN, full config) the request is otherwise unchanged: URL, method, one FormData, one signal on both attempts', async () => {
    queue([401, AUTH_BODY], [200, OK_BODY]);
    const out = await settle(api.identifyFromImages(URIS, 'bahrain'));
    expect(out.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const [first, second] = fetchMock.mock.calls;
    expect(first[0]).toBe(`${api.API_BASE_URL}/api/v1/image/identify?region=bahrain`);
    expect(second[0]).toBe(first[0]);
    expect(first[1].method).toBe('POST');
    expect(second[1].method).toBe('POST');
    expect(second[1].body).toBe(first[1].body);
    expect(second[1].signal).toBe(first[1].signal);
    expect(Object.keys(first[1]).sort()).toEqual(['body', 'headers', 'method', 'signal']);
  });

  it('C5 (PIN, full config) every builder failing: attempt 1 goes out with {Authorization} only and the retry still runs', async () => {
    mockDF.getDeviceFingerprint.mockRejectedValue(new Error('device'));
    mockDF.getDeviceIdentity.mockRejectedValue(new Error('device'));
    mockDF.legacyDeviceFingerprintHash.mockRejectedValue(new Error('legacy'));
    mockAuth.getSavedUser.mockRejectedValue(new Error('user'));
    mockUuid.next = () => {
      throw new Error('uuid');
    };
    queue([401, AUTH_BODY], [200, OK_BODY]);
    const out = await settle(api.identifyFromImages(URIS, 'bahrain'));
    expect(out.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(lowerHeaders(fetchMock.mock.calls[0][1].headers)).toEqual({
      authorization: 'Bearer bearer-old-synthetic',
    });
    expect(lowerHeaders(fetchMock.mock.calls[1][1].headers)).toEqual({
      authorization: 'Bearer bearer-new-synthetic',
    });
  });

  it('C6 (R-S08-15) the camera compare id is exposed to the caller and equals the id sent', async () => {
    queue([200, OK_BODY]);
    const onCompareRequestId = jest.fn();
    const out = await settle((api as any).identifyFromImages(URIS, 'bahrain', { onCompareRequestId }));
    expect(out.ok).toBe(true);
    const sent = lowerHeaders(fetchMock.mock.calls[0][1].headers)['x-compare-request-id'];
    const exposed = (out.value && out.value.compareRequestId) ?? onCompareRequestId.mock.calls[0]?.[0];
    expect(sent ?? '').toMatch(V4);
    expect(exposed).toBe(sent);
  });
});
