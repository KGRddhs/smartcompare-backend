/**
 * deviceFingerprint service — Bundle A Task 4.1
 *
 * Contract under test (see Bundle A design §1.5 + frontend Task 2.1):
 *  - First call without a persisted nonce → generates one via Crypto.randomUUID
 *    and persists it under SecureStore key `device_fp_nonce`.
 *  - Subsequent calls with a persisted nonce → does NOT call setItemAsync
 *    again (no churn on re-launch).
 *  - In-memory cache short-circuits repeat work: two calls in the same
 *    process return the same hash and only hit SecureStore.getItemAsync once.
 *
 * Why these assertions: backend relies on a stable fingerprint to lock the
 * 3 lifetime free comparisons across signups on the same physical device.
 * Re-generating the nonce on each launch would break that invariant — the
 * test ensures we never do.
 */

jest.mock('expo-application', () => ({ applicationId: 'app.qaren.test' }));
jest.mock('expo-device', () => ({
  osBuildId: 'iPhone15,2/21D',
  osInternalBuildId: null,
}));

// expo-crypto default mock lacks digestStringAsync/CryptoDigestAlgorithm;
// extend it locally so the SHA-256 path is deterministic for the test.
jest.mock('expo-crypto', () => ({
  digestStringAsync: jest.fn(async (_alg: string, raw: string) => `hash(${raw})`),
  randomUUID: jest.fn(() => 'fixed-uuid-0001'),
  CryptoDigestAlgorithm: { SHA256: 'SHA256' },
}));

// expo-secure-store gets mocked per-test for getItemAsync return values.
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';
import { getDeviceFingerprint, _resetCacheForTests } from '../src/services/deviceFingerprint';

describe('deviceFingerprint', () => {
  beforeEach(() => {
    _resetCacheForTests();
    jest.clearAllMocks();
  });

  it('creates and persists a nonce on first call when none exists', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(null);

    await getDeviceFingerprint();

    expect(SecureStore.getItemAsync).toHaveBeenCalledWith('device_fp_nonce');
    expect(Crypto.randomUUID).toHaveBeenCalledTimes(1);
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('device_fp_nonce', 'fixed-uuid-0001');
  });

  it('reuses existing nonce on subsequent launches (does NOT re-persist)', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('persisted-nonce');

    await getDeviceFingerprint();

    expect(SecureStore.setItemAsync).not.toHaveBeenCalled();
    expect(Crypto.randomUUID).not.toHaveBeenCalled();
  });

  it('returns the same hash across calls in one process (in-memory cache)', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('persisted-nonce');

    const a = await getDeviceFingerprint();
    const b = await getDeviceFingerprint();

    expect(a).toBe(b);
    // Cache hits should not re-read SecureStore.
    expect(SecureStore.getItemAsync).toHaveBeenCalledTimes(1);
    expect(Crypto.digestStringAsync).toHaveBeenCalledTimes(1);
  });

  it('hashes applicationId|osBuildId|nonce in that order via SHA-256', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('persisted-nonce');

    const hash = await getDeviceFingerprint();

    expect(Crypto.digestStringAsync).toHaveBeenCalledWith(
      'SHA256',
      'app.qaren.test|iPhone15,2/21D|persisted-nonce',
    );
    expect(hash).toBe('hash(app.qaren.test|iPhone15,2/21D|persisted-nonce)');
  });

  it('coalesces concurrent calls into a single SecureStore read', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('persisted-nonce');

    const [a, b, c] = await Promise.all([
      getDeviceFingerprint(),
      getDeviceFingerprint(),
      getDeviceFingerprint(),
    ]);

    expect(a).toBe(b);
    expect(b).toBe(c);
    expect(SecureStore.getItemAsync).toHaveBeenCalledTimes(1);
  });
});
