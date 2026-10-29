/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-08 CLIENT-FIRST-OTA RED - rows A1..A13 (spec section 5 as amended by
 * RULINGS_S81_08 R-S08-7 / R-S08-10 and the review C5 / C16).
 *
 * The stable device id: SHA-256 hex of the lower-cased SecureStore nonce
 * `device_fp_nonce` (no osBuildId), the IDFV / ANDROID_ID fallback only when
 * SecureStore throws (never cached, never persisted), the legacy build-3
 * composition kept byte for byte behind `legacyDeviceFingerprintHash()`, the
 * dated cutoff constant, and (R-S08-7) the id source exposed as
 * `{ hash, source }` by `getDeviceIdentity()` while `getDeviceFingerprint()`
 * keeps resolving the hash string (its existing callers and pins need it).
 *
 * Hermetic: every expo module mocked with a plain jest.mock(name, factory)
 * (never virtual). New exports are read through load() / typeof checks and
 * promise outcomes are captured, so every RED row fails at base on an
 * assertion only. Every legacy-dependent row pins Date.now pre-cutoff (C5).
 * Synthetic values only.
 */

const mockSecureState: { store: Record<string, string>; failGet: unknown[] } = {
  store: {},
  failGet: [],
};
const mockSecure = {
  getItemAsync: jest.fn(async (key: string) => {
    if (mockSecureState.failGet.length > 0) {
      throw mockSecureState.failGet.shift();
    }
    return Object.prototype.hasOwnProperty.call(mockSecureState.store, key)
      ? mockSecureState.store[key]
      : null;
  }),
  setItemAsync: jest.fn(async (key: string, value: string) => {
    mockSecureState.store[key] = value;
  }),
  deleteItemAsync: jest.fn(async (key: string) => {
    delete mockSecureState.store[key];
  }),
};
jest.mock('expo-secure-store', () => mockSecure);

const mockApplication = {
  applicationId: 'app.qaren.test',
  getIosIdForVendorAsync: jest.fn(),
  getAndroidId: jest.fn(),
};
jest.mock('expo-application', () => mockApplication);

const mockDeviceReads = { osBuildId: 0, osInternalBuildId: 0 };
jest.mock('expo-device', () => {
  const m: any = {};
  Object.defineProperty(m, 'osBuildId', {
    enumerable: true,
    get: () => {
      mockDeviceReads.osBuildId += 1;
      return 'iPhone15,2/21D';
    },
  });
  Object.defineProperty(m, 'osInternalBuildId', {
    enumerable: true,
    get: () => {
      mockDeviceReads.osInternalBuildId += 1;
      return null;
    },
  });
  return m;
});

const mockCrypto = {
  digestStringAsync: jest.fn(async (_alg: string, raw: string) => `hash(${raw})`),
  randomUUID: jest.fn(() => 'Fixed-Uuid-0001'),
  CryptoDigestAlgorithm: { SHA256: 'SHA256' },
};
jest.mock('expo-crypto', () => mockCrypto);

// One AsyncStorage recorder shared by every module registry (isolateModules).
const mockAsync = {
  getItem: jest.fn(async () => null),
  setItem: jest.fn(async () => undefined),
  removeItem: jest.fn(async () => undefined),
  multiRemove: jest.fn(async () => undefined),
  clear: jest.fn(async () => undefined),
};
jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: mockAsync,
}));

const DF_PATH = '../../src/services/deviceFingerprint';
const PRE_CUTOFF_MS = Date.UTC(2026, 9, 23, 12, 0, 0);
const CUTOFF_MS = Date.UTC(2027, 2, 31, 21, 0, 0);

type Outcome = { ok: true; value: any } | { ok: false; error: any };

async function capture(fn: () => any): Promise<Outcome> {
  try {
    return { ok: true, value: await fn() };
  } catch (error) {
    return { ok: false, error };
  }
}

const valueOf = (o: Outcome): any => (o.ok ? o.value : 'REJECTED');

let dateSpy: jest.SpyInstance | null = null;

/** A fresh deviceFingerprint module with Platform.OS set first (no shared caches). */
function freshModule(os: 'ios' | 'android' = 'ios'): any {
  let mod: any = null;
  jest.isolateModules(() => {
    const RN = require('react-native');
    RN.Platform.OS = os;
    try {
      mod = require(DF_PATH);
    } catch {
      mod = null;
    }
  });
  return mod;
}

function asyncStorageSetItem(): jest.Mock {
  return mockAsync.setItem;
}

beforeEach(() => {
  mockSecureState.store = {};
  mockSecureState.failGet = [];
  mockSecure.getItemAsync.mockClear();
  mockSecure.setItemAsync.mockClear();
  mockSecure.deleteItemAsync.mockClear();
  mockApplication.getIosIdForVendorAsync.mockReset();
  mockApplication.getAndroidId.mockReset();
  mockApplication.getIosIdForVendorAsync.mockResolvedValue('Idfv-Present-0001');
  mockApplication.getAndroidId.mockReturnValue('Android-Present-0001');
  mockCrypto.digestStringAsync.mockClear();
  mockCrypto.randomUUID.mockClear();
  mockDeviceReads.osBuildId = 0;
  mockDeviceReads.osInternalBuildId = 0;
  mockAsync.setItem.mockClear();
  dateSpy = jest.spyOn(Date, 'now').mockReturnValue(PRE_CUTOFF_MS);
});

afterEach(() => {
  if (dateSpy) dateSpy.mockRestore();
  dateSpy = null;
  const RN = require('react-native');
  RN.Platform.OS = 'ios';
});

describe('S81-08 A - the stable device id', () => {
  it('A1 exports the legacy hash', () => {
    const mod = freshModule();
    expect(mod).not.toBeNull();
    expect(typeof mod?.legacyDeviceFingerprintHash).toBe('function');
  });

  it('A2 the new id = sha256 of the lower-cased nonce', async () => {
    mockSecureState.store.device_fp_nonce = 'Persisted-Nonce-Ab';
    const mod = freshModule();
    const out = await capture(() => mod.getDeviceFingerprint());
    expect(valueOf(out)).toBe('hash(persisted-nonce-ab)');
    expect(mockCrypto.digestStringAsync).toHaveBeenCalledWith('SHA256', 'persisted-nonce-ab');
  });

  it('A3 the new id never reads osBuildId / osInternalBuildId', async () => {
    mockSecureState.store.device_fp_nonce = 'Persisted-Nonce-Ab';
    const mod = freshModule();
    mockDeviceReads.osBuildId = 0;
    mockDeviceReads.osInternalBuildId = 0;
    const out = await capture(() => mod.getDeviceFingerprint());
    expect(out.ok).toBe(true);
    expect(mockDeviceReads).toEqual({ osBuildId: 0, osInternalBuildId: 0 });
  });

  it('A4 the legacy hash == the build-3 composition byte for byte', async () => {
    mockSecureState.store.device_fp_nonce = 'Persisted-Nonce-Ab';
    const mod = freshModule();
    const fn = mod?.legacyDeviceFingerprintHash;
    const out: Outcome =
      typeof fn === 'function' ? await capture(() => fn()) : { ok: true, value: 'MISSING' };
    expect(valueOf(out)).toBe('hash(app.qaren.test|iPhone15,2/21D|Persisted-Nonce-Ab)');
    expect(mockCrypto.digestStringAsync).toHaveBeenCalledWith(
      'SHA256',
      'app.qaren.test|iPhone15,2/21D|Persisted-Nonce-Ab',
    );
  });

  it('A5 (PIN, full config) stable across restarts: one generated nonce, persisted once', async () => {
    const mod = freshModule();
    const first = await capture(() => mod.getDeviceFingerprint());
    expect(first.ok).toBe(true);
    expect(mockSecure.setItemAsync).toHaveBeenCalledTimes(1);
    expect(mockSecure.setItemAsync).toHaveBeenCalledWith('device_fp_nonce', 'Fixed-Uuid-0001');
    mod._resetCacheForTests();
    const second = await capture(() => mod.getDeviceFingerprint());
    expect(second.ok).toBe(true);
    expect(valueOf(second)).toBe(valueOf(first));
    expect(mockSecure.setItemAsync).toHaveBeenCalledTimes(1);
    expect(mockCrypto.randomUUID).toHaveBeenCalledTimes(1);
  });

  it('A6 iOS fallback when SecureStore throws: IDFV hashed lower-case, not cached, not persisted', async () => {
    mockSecureState.failGet = [new Error('keychain busy')];
    mockApplication.getIosIdForVendorAsync.mockResolvedValue('AbCd-IDFV-0001');
    const mod = freshModule('ios');
    const first = await capture(() => mod.getDeviceFingerprint());
    expect(valueOf(first)).toBe('hash(abcd-idfv-0001)');
    expect(mockApplication.getIosIdForVendorAsync).toHaveBeenCalledTimes(1);
    expect(mockSecure.setItemAsync).not.toHaveBeenCalled();
    expect(asyncStorageSetItem()).not.toHaveBeenCalled();
    // Not cached: the next call with a healthy SecureStore reads SecureStore again.
    mockSecureState.store.device_fp_nonce = 'Persisted-Nonce-Ab';
    const second = await capture(() => mod.getDeviceFingerprint());
    expect(valueOf(second)).toBe('hash(persisted-nonce-ab)');
    expect(mockSecure.getItemAsync).toHaveBeenCalledTimes(2);
  });

  it('A7 Android fallback: ANDROID_ID hashed, IDFV never called', async () => {
    mockSecureState.failGet = [new Error('keystore busy')];
    mockApplication.getAndroidId.mockReturnValue('Android-Id-77');
    const mod = freshModule('android');
    const out = await capture(() => mod.getDeviceFingerprint());
    expect(valueOf(out)).toBe('hash(android-id-77)');
    expect(mockApplication.getAndroidId).toHaveBeenCalled();
    expect(mockApplication.getIosIdForVendorAsync).not.toHaveBeenCalled();
    expect(mockSecure.setItemAsync).not.toHaveBeenCalled();
  });

  it('A8 no fallback value -> rejects with the ORIGINAL SecureStore error after asking IDFV once', async () => {
    const err = new Error('keychain locked');
    mockSecureState.failGet = [err];
    mockApplication.getIosIdForVendorAsync.mockResolvedValue(null);
    const mod = freshModule('ios');
    const out = await capture(() => mod.getDeviceFingerprint());
    expect(valueOf(out)).toBe('REJECTED');
    expect(out.ok ? null : out.error).toBe(err);
    expect(mockApplication.getIosIdForVendorAsync).toHaveBeenCalledTimes(1);
  });

  it('A9 (PIN, full config) the id is written only to SecureStore, never to AsyncStorage', async () => {
    const mod = freshModule();
    const out = await capture(() => mod.getDeviceFingerprint());
    expect(out.ok).toBe(true);
    expect(asyncStorageSetItem()).not.toHaveBeenCalled();
    expect(mockSecure.setItemAsync).toHaveBeenCalledTimes(1);
    for (const call of mockSecure.setItemAsync.mock.calls) {
      expect(call[0]).toBe('device_fp_nonce');
    }
  });

  it('A10 one nonce read serves both hashes; repeat calls are cached', async () => {
    mockSecureState.store.device_fp_nonce = 'Persisted-Nonce-Ab';
    const mod = freshModule();
    const legacy = mod?.legacyDeviceFingerprintHash;
    expect(typeof legacy).toBe('function');
    const a = await capture(() => mod.getDeviceFingerprint());
    const b = await capture(() => legacy());
    const a2 = await capture(() => mod.getDeviceFingerprint());
    const b2 = await capture(() => legacy());
    expect([a.ok, b.ok, a2.ok, b2.ok]).toEqual([true, true, true, true]);
    expect(valueOf(a2)).toBe(valueOf(a));
    expect(valueOf(b2)).toBe(valueOf(b));
    expect(valueOf(a)).not.toBe(valueOf(b));
    expect(mockSecure.getItemAsync).toHaveBeenCalledTimes(1);
    expect(mockCrypto.digestStringAsync).toHaveBeenCalledTimes(2);
  });

  it('A11 the dated cutoff constant = 2027-04-01 00:00 Asia/Riyadh', () => {
    const mod = freshModule();
    expect(mod?.LEGACY_FINGERPRINT_HEADER_UNTIL_MS).toBe(CUTOFF_MS);
  });

  it('A12 the window predicate: active before the cutoff, inactive at and after it', () => {
    const mod = freshModule();
    const fn = mod?.legacyFingerprintHeaderActive;
    expect(typeof fn).toBe('function');
    const at = (ms: number) => (typeof fn === 'function' ? fn(ms) : 'MISSING');
    expect(at(CUTOFF_MS - 1)).toBe(true);
    expect(at(CUTOFF_MS)).toBe(false);
    expect(at(CUTOFF_MS + 1)).toBe(false);
  });

  it('A13 (R-S08-7) getDeviceIdentity exposes { hash, source } for the three paths', async () => {
    mockSecureState.store.device_fp_nonce = 'Persisted-Nonce-Ab';
    const iosMod = freshModule('ios');
    const ident = iosMod?.getDeviceIdentity;
    expect(typeof ident).toBe('function');
    const stored = typeof ident === 'function' ? valueOf(await capture(() => ident())) : 'MISSING';
    expect(stored).toEqual({ hash: 'hash(persisted-nonce-ab)', source: 'securestore' });

    mockSecureState.failGet = [new Error('keychain busy')];
    mockApplication.getIosIdForVendorAsync.mockResolvedValue('AbCd-IDFV-0001');
    const iosFresh = freshModule('ios');
    const idfv =
      typeof iosFresh?.getDeviceIdentity === 'function'
        ? valueOf(await capture(() => iosFresh.getDeviceIdentity()))
        : 'MISSING';
    expect(idfv).toEqual({ hash: 'hash(abcd-idfv-0001)', source: 'idfv' });

    mockSecureState.failGet = [new Error('keystore busy')];
    mockApplication.getAndroidId.mockReturnValue('Android-Id-77');
    const androidMod = freshModule('android');
    const aid =
      typeof androidMod?.getDeviceIdentity === 'function'
        ? valueOf(await capture(() => androidMod.getDeviceIdentity()))
        : 'MISSING';
    expect(aid).toEqual({ hash: 'hash(android-id-77)', source: 'android_id' });
  });
});
