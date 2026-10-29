/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-08 CLIENT-FIRST-OTA RED - rows E1..E10 + A9b: the AI-consent record
 * (spec section 5 E-rows as amended by RULINGS_S81_08 R-S08-3: NO device-level
 * consent mirror; consent stays PER ACCOUNT; the X-AI-Consent-Version header
 * is read from the ACCOUNT record only through an in-memory memo invalidated
 * by recordAiConsent / clearAiConsent / sign-out; a signed-out user keeps
 * today's behaviour; no device id, derived tag or fallback value is ever
 * written to AsyncStorage (A9b)).
 *
 * Under R-S08-3 the spec's device-mirror rows invert: E1, E2, E4, E6 and E8 are
 * now PINs of today's per-account behaviour (they kill any mirror), E9 is the
 * one RED row (the header follows the account record, memo invalidation
 * included). The REAL aiConsent over an in-memory AsyncStorage; the device id
 * module is a recorder. Synthetic values only.
 */

const nodeCrypto = require('crypto');

const sha = (s: string): string => nodeCrypto.createHash('sha256').update(s, 'utf8').digest('hex');
const NEW = sha('s81-08-new');
const LEG = sha('s81-08-legacy');
const PRE_CUTOFF_MS = Date.UTC(2026, 9, 23, 12, 0, 0);
const USER_A = 'user-a-synthetic';
const USER_B = 'user-b-synthetic';
const KEY_A = '@qaren_ai_consent_' + USER_A;
const KEY_B = '@qaren_ai_consent_' + USER_B;
const DEVICE_KEY = '@qaren_device_ai_consent';
const AT = new Date('2026-10-23T12:00:00.000Z');

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

const mockAuth = {
  getSavedUser: jest.fn(),
  getToken: jest.fn(async () => null),
};
jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...a: any[]) => (mockAuth.getSavedUser as any)(...a),
  getToken: (...a: any[]) => (mockAuth.getToken as any)(...a),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
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

const mockSecure = {
  getItemAsync: jest.fn(async () => 'synthetic-nonce'),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
};
jest.mock('expo-secure-store', () => mockSecure);

jest.mock('expo-crypto', () => ({
  randomUUID: () => require('crypto').randomUUID(),
  digestStringAsync: jest.fn(async () => 'f'.repeat(64)),
  CryptoDigestAlgorithm: { SHA256: 'SHA256' },
}));

jest.mock('../../src/services/aiConsent', () => jest.requireActual('../../src/services/aiConsent'));

const consent = require('../../src/services/aiConsent');

function load(path: string): any {
  try {
    return require(path);
  } catch {
    return null;
  }
}

function plant(key: string, version: unknown, extra: Record<string, unknown> = {}): void {
  mockAsync.store[key] = JSON.stringify({ version, at: AT.toISOString(), ...extra });
}

async function consentHeader(rc: any): Promise<string | undefined> {
  if (!rc || typeof rc.buildContextHeaders !== 'function') return 'NO_BUILDER';
  let h: any = null;
  try {
    h = await rc.buildContextHeaders();
  } catch {
    return 'REJECTED';
  }
  const hit = Object.keys(h || {}).find((k) => k.toLowerCase() === 'x-ai-consent-version');
  return hit ? String(h[hit]) : undefined;
}

let dateSpy: jest.SpyInstance | null = null;

beforeEach(() => {
  mockAsync.store = {};
  [mockAsync.getItem, mockAsync.setItem, mockAsync.removeItem].forEach((m) => m.mockClear());
  mockAuth.getSavedUser.mockReset();
  mockAuth.getSavedUser.mockResolvedValue({ id: USER_A });
  mockDF.getDeviceFingerprint.mockReset();
  mockDF.legacyDeviceFingerprintHash.mockReset();
  mockDF.getDeviceIdentity.mockReset();
  mockDF.getDeviceFingerprint.mockResolvedValue(NEW);
  mockDF.legacyDeviceFingerprintHash.mockResolvedValue(LEG);
  mockDF.getDeviceIdentity.mockResolvedValue({ hash: NEW, source: 'securestore' });
  [mockSecure.getItemAsync, mockSecure.setItemAsync, mockSecure.deleteItemAsync].forEach((m) => m.mockClear());
  dateSpy = jest.spyOn(Date, 'now').mockReturnValue(PRE_CUTOFF_MS);
});

afterEach(() => {
  if (dateSpy) dateSpy.mockRestore();
  dateSpy = null;
});

describe('S81-08 E - the consent record stays per account (R-S08-3)', () => {
  it('E1 (PIN, full config) Agree writes the account key {version, at} only: no deviceId, no device key', async () => {
    await consent.recordAiConsent(USER_A, AT);
    expect(mockAsync.setItem).toHaveBeenCalledTimes(1);
    expect(mockAsync.setItem.mock.calls[0][0]).toBe(KEY_A);
    expect(JSON.parse(mockAsync.store[KEY_A])).toEqual({
      version: consent.AI_CONSENT_VERSION,
      at: AT.toISOString(),
    });
    expect(DEVICE_KEY in mockAsync.store).toBe(false);
  });

  it('E2 (PIN, full config) per account: user-a agreeing never covers user-b on the same device', async () => {
    await consent.recordAiConsent(USER_A, AT);
    expect(await consent.hasCurrentAiConsent(USER_A)).toBe(true);
    expect(await consent.hasCurrentAiConsent(USER_B)).toBe(false);
  });

  it('E3 (PIN, full config) a version bump re-asks: an older account record is not current', async () => {
    plant(KEY_A, consent.AI_CONSENT_VERSION - 1);
    plant(DEVICE_KEY, consent.AI_CONSENT_VERSION - 1, { deviceId: NEW });
    expect(await consent.hasCurrentAiConsent(USER_A)).toBe(false);
  });

  it('E4 (PIN, full config) a planted device-level record never satisfies consent for any account', async () => {
    plant(DEVICE_KEY, consent.AI_CONSENT_VERSION, { deviceId: NEW });
    expect(await consent.hasCurrentAiConsent(USER_B)).toBe(false);
    expect(await consent.hasCurrentAiConsent(USER_A)).toBe(false);
  });

  it('E5 (PIN, full config) no user persists nothing', async () => {
    await consent.recordAiConsent(null, AT);
    expect(mockAsync.setItem).not.toHaveBeenCalled();
    expect(Object.keys(mockAsync.store)).toEqual([]);
  });

  it('E6 (PIN, full config) account deletion removes exactly that account record', async () => {
    plant(KEY_A, consent.AI_CONSENT_VERSION);
    plant(KEY_B, consent.AI_CONSENT_VERSION);
    await consent.clearAiConsent(USER_A);
    expect(mockAsync.removeItem).toHaveBeenCalledTimes(1);
    expect(mockAsync.removeItem).toHaveBeenCalledWith(KEY_A);
    expect(KEY_A in mockAsync.store).toBe(false);
    expect(KEY_B in mockAsync.store).toBe(true);
  });

  it('E7 (PIN) the read shape is unchanged: {version, at} only', async () => {
    plant(KEY_A, consent.AI_CONSENT_VERSION, { deviceId: NEW });
    expect(await consent.readAiConsent(USER_A)).toEqual({
      version: consent.AI_CONSENT_VERSION,
      at: AT.toISOString(),
    });
  });

  it('E8 (PIN, full config) record / has / read / clear never touch the device id', async () => {
    await consent.recordAiConsent(USER_A, AT);
    await consent.hasCurrentAiConsent(USER_A);
    await consent.readAiConsent(USER_A);
    await consent.clearAiConsent(USER_A);
    expect(mockDF.getDeviceFingerprint).not.toHaveBeenCalled();
    expect(mockDF.getDeviceIdentity).not.toHaveBeenCalled();
    expect(mockDF.legacyDeviceFingerprintHash).not.toHaveBeenCalled();
    expect(mockSecure.getItemAsync).not.toHaveBeenCalled();
  });

  it('A9b (PIN, full config) after Agree no AsyncStorage value carries the device id', async () => {
    await consent.recordAiConsent(USER_A, AT);
    for (const call of mockAsync.setItem.mock.calls) {
      expect(String(call[1]).includes(NEW)).toBe(false);
      expect(String(call[1]).includes(LEG)).toBe(false);
    }
    expect(Object.values(mockAsync.store).some((v: any) => String(v).includes(NEW))).toBe(false);
  });

  it('E9 the consent header follows the ACCOUNT record: none, then the version after Agree, none after clear and after sign-out', async () => {
    const rc = load('../../src/services/requestContext');
    expect(rc).not.toBeNull();
    const version = String(consent.AI_CONSENT_VERSION);
    expect(await consentHeader(rc)).toBeUndefined();
    await consent.recordAiConsent(USER_A, AT);
    expect(await consentHeader(rc)).toBe(version);
    await consent.clearAiConsent(USER_A);
    expect(await consentHeader(rc)).toBeUndefined();
    await consent.recordAiConsent(USER_A, AT);
    expect(await consentHeader(rc)).toBe(version);
    mockAuth.getSavedUser.mockResolvedValue(null);
    expect(await consentHeader(rc)).toBeUndefined();
    mockAuth.getSavedUser.mockResolvedValue({ id: USER_B });
    expect(await consentHeader(rc)).toBeUndefined();
  });

  it('E10 (PIN, full config) a signed-out user is asked every time and nothing is persisted', async () => {
    plant(KEY_A, consent.AI_CONSENT_VERSION);
    mockAuth.getSavedUser.mockResolvedValue(null);
    mockAsync.setItem.mockClear();
    const ask = jest.fn(async () => true);
    expect(await consent.ensureAiConsent(ask)).toBe(true);
    expect(await consent.ensureAiConsent(ask)).toBe(true);
    expect(ask).toHaveBeenCalledTimes(2);
    expect(mockAsync.setItem).not.toHaveBeenCalled();
  });
});
