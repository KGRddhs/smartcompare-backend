/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-08 CLIENT-FIRST-OTA RED - rows I1..I5: the legacy fingerprint header on
 * the two social sign-ins (spec 3.5 as amended by RULINGS_S81_08 R-S08-4 /
 * R-S08B-1: the legacy value rides ONLY register and the two social
 * sign-ins, while the window is open; R-S08-9: every call to a NEW
 * deviceFingerprint export sits in its own try, so a module mocked with
 * getDeviceFingerprint only degrades to "no legacy header" (I5)).
 *
 * The authService.socialFingerprint.w3-3 harness shapes (native sheets and
 * fetch mocked; api mocked). Plain jest.mock / jest.doMock only. Every RED
 * row fails at base on an assertion. Synthetic values; Date.now pinned.
 */

const nodeCrypto = require('crypto');

const sha = (s: string): string => nodeCrypto.createHash('sha256').update(s, 'utf8').digest('hex');
const NEW = sha('s81-08-new');
const LEG = sha('s81-08-legacy');
const PRE_CUTOFF_MS = Date.UTC(2026, 9, 23, 12, 0, 0);
const CUTOFF_MS = Date.UTC(2027, 2, 31, 21, 0, 0);

const mockSignIn = jest.fn();
jest.mock('@react-native-google-signin/google-signin', () => ({
  GoogleSignin: {
    configure: jest.fn(),
    hasPlayServices: jest.fn().mockResolvedValue(true),
    signIn: (...a: unknown[]) => mockSignIn(...a),
  },
}));

const mockAppleSignInAsync = jest.fn();
jest.mock('expo-apple-authentication', () => ({
  signInAsync: (...a: unknown[]) => mockAppleSignInAsync(...a),
  isAvailableAsync: jest.fn().mockResolvedValue(true),
  AppleAuthenticationScope: { FULL_NAME: 0, EMAIL: 1 },
}));

jest.mock('expo-crypto', () => ({
  getRandomBytesAsync: jest.fn().mockResolvedValue(new Uint8Array(32)),
  digestStringAsync: jest.fn().mockResolvedValue('a'.repeat(64)),
  randomUUID: () => require('crypto').randomUUID(),
  CryptoDigestAlgorithm: { SHA256: 'SHA-256' },
}));

jest.mock('@sentry/react-native', () => ({
  addBreadcrumb: jest.fn(),
  captureMessage: jest.fn(),
  captureException: jest.fn(),
  init: jest.fn(),
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
// R-S08-9 / I5: with mockDFMode.partial the module exposes getDeviceFingerprint
// ONLY (every other export reads undefined at call time), the shape of the
// partial mocks in authService.socialFingerprint.w3-3 / logoutRefreshFirst.w1-4d.
const mockDFMode = { partial: false };
jest.mock('../../src/services/deviceFingerprint', () => {
  const m: any = {};
  for (const k of Object.keys(mockDF)) {
    Object.defineProperty(m, k, {
      enumerable: true,
      get: () => (mockDFMode.partial && k !== 'getDeviceFingerprint' ? undefined : (mockDF as any)[k]),
    });
  }
  return m;
});

const mockApiPost = jest.fn();
jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...a: unknown[]) => mockApiPost(...a),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
  API_BASE_URL: 'https://test.invalid',
  getOrStartRefresh: jest.fn(),
  getInFlightRefresh: jest.fn(() => null),
}));

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

const auth = require('../../src/services/authService');

const ID_TOKEN = 'header.payload.signature';

function okResponse() {
  return {
    ok: true,
    status: 200,
    json: async () => ({
      success: true,
      user: { id: 'u1', email: 'u1@example.invalid' },
      session: { access_token: 'at-1', refresh_token: 'rt-1' },
    }),
  };
}

function cancelled(code: string): any {
  return Object.assign(new Error('cancelled'), { code });
}

let dateSpy: jest.SpyInstance | null = null;

beforeEach(() => {
  mockSignIn.mockReset();
  mockAppleSignInAsync.mockReset();
  mockFetch.mockReset();
  mockApiPost.mockReset();
  mockSignIn.mockResolvedValue({ data: { idToken: ID_TOKEN } });
  mockAppleSignInAsync.mockResolvedValue({ identityToken: ID_TOKEN });
  mockFetch.mockResolvedValue(okResponse());
  mockDF.getDeviceFingerprint.mockReset();
  mockDF.legacyDeviceFingerprintHash.mockReset();
  mockDF.getDeviceIdentity.mockReset();
  mockDF.legacyFingerprintHeaderActive.mockClear();
  mockDFMode.partial = false;
  mockDF.getDeviceFingerprint.mockResolvedValue(NEW);
  mockDF.legacyDeviceFingerprintHash.mockResolvedValue(LEG);
  mockDF.getDeviceIdentity.mockResolvedValue({ hash: NEW, source: 'securestore' });
  dateSpy = jest.spyOn(Date, 'now').mockReturnValue(PRE_CUTOFF_MS);
});

afterEach(() => {
  if (dateSpy) dateSpy.mockRestore();
  dateSpy = null;
});

async function bothProviders(a: any): Promise<any[]> {
  const g = await a.signInWithGoogle();
  const ap = await a.signInWithApple();
  return [g, ap];
}

describe('S81-08 I - the legacy fingerprint on the social sign-ins', () => {
  it('I1 Google and Apple send X-Device-Fingerprint-Legacy LEG beside X-Device-Fingerprint NEW', async () => {
    const results = await bothProviders(auth);
    expect(results.map((r) => r.success)).toEqual([true, true]);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    for (const call of mockFetch.mock.calls) {
      expect(String(call[0])).toContain('/api/v1/auth/social-login');
      expect(call[1].headers['X-Device-Fingerprint']).toBe(NEW);
      expect(call[1].headers['X-Device-Fingerprint-Legacy']).toBe(LEG);
    }
  });

  it('I2 (PIN, full config) a cancelled sign-in reads neither id', async () => {
    mockSignIn.mockRejectedValue(cancelled('SIGN_IN_CANCELLED'));
    mockAppleSignInAsync.mockRejectedValue(cancelled('ERR_REQUEST_CANCELED'));
    const results = await bothProviders(auth);
    expect(results.map((r) => r.success)).toEqual([false, false]);
    expect(mockDF.getDeviceFingerprint).not.toHaveBeenCalled();
    expect(mockDF.legacyDeviceFingerprintHash).not.toHaveBeenCalled();
    expect(mockDF.getDeviceIdentity).not.toHaveBeenCalled();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('I3 (PIN, full config) a legacy-hash failure never blocks sign-in: sent, no legacy header, device header kept', async () => {
    mockDF.legacyDeviceFingerprintHash.mockRejectedValue(new Error('legacy'));
    const results = await bothProviders(auth);
    expect(results.map((r) => r.success)).toEqual([true, true]);
    expect(mockFetch).toHaveBeenCalledTimes(2);
    for (const call of mockFetch.mock.calls) {
      expect(call[1].headers['X-Device-Fingerprint']).toBe(NEW);
      expect('X-Device-Fingerprint-Legacy' in call[1].headers).toBe(false);
      expect(call[1].headers['Content-Type']).toBe('application/json');
    }
  });

  it('I4 (PIN, full config) at the cutoff no legacy header and no legacy read on either provider', async () => {
    dateSpy?.mockReturnValue(CUTOFF_MS);
    const results = await bothProviders(auth);
    expect(results.map((r) => r.success)).toEqual([true, true]);
    expect(mockDF.legacyDeviceFingerprintHash).not.toHaveBeenCalled();
    for (const call of mockFetch.mock.calls) {
      expect(call[1].headers['X-Device-Fingerprint']).toBe(NEW);
      expect('X-Device-Fingerprint-Legacy' in call[1].headers).toBe(false);
    }
  });

  it('I5 (PIN, R-S08-9) deviceFingerprint mocked with getDeviceFingerprint ONLY: both POSTs sent, no legacy header', async () => {
    mockDFMode.partial = true;
    try {
      const df = require('../../src/services/deviceFingerprint');
      expect(typeof df.legacyDeviceFingerprintHash).toBe('undefined');
      expect(typeof df.legacyFingerprintHeaderActive).toBe('undefined');
      const results = await bothProviders(auth);
      expect(results.map((r) => r.success)).toEqual([true, true]);
      expect(mockFetch).toHaveBeenCalledTimes(2);
      for (const call of mockFetch.mock.calls) {
        expect(call[1].headers['X-Device-Fingerprint']).toBe(NEW);
        expect('X-Device-Fingerprint-Legacy' in call[1].headers).toBe(false);
      }
    } finally {
      mockDFMode.partial = false;
    }
  });
});
