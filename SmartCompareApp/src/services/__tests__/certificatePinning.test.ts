/**
 * Tests for certificate pinning setup.
 *
 * M18 MB-security-04: the pin set must include an RSA-chain backup
 * (ISRG Root X1) alongside the ECDSA family (ISRG Root X2 + YE1/E7/E8/E5).
 * All five previously-pinned hashes stay — the fix is ADDITIVE. Without
 * the X1 pin, a Let's Encrypt RSA issuance (R10-R14 chain) would brick
 * every pinned build — a repeat of the documented 2026-07-06 outage.
 *
 * M18 MB-security-07: a release-build (`!__DEV__`) pinning-init failure
 * must be observable via Sentry.captureMessage — console.* is stripped by
 * babel in production, so before this fix a misbuilt binary ran the whole
 * session unpinned with zero telemetry. Fail-open behavior is unchanged.
 */

const mockInitializeSslPinning = jest.fn();
jest.mock('react-native-ssl-public-key-pinning', () => ({
  initializeSslPinning: (...args: unknown[]) => mockInitializeSslPinning(...args),
  isSslPinningAvailable: () => false,
}));

const mockCaptureMessage = jest.fn();
jest.mock('@sentry/react-native', () => ({
  captureMessage: (...args: unknown[]) => mockCaptureMessage(...args),
  init: jest.fn(),
  wrap: <T,>(c: T): T => c,
}));

// SPKI SHA-256 pins. ISRG_ROOT_X1 derived offline from the certifi CA
// bundle (method validated by reproducing the committed ISRG_ROOT_X2 pin
// byte-for-byte from the same bundle).
const ISRG_ROOT_X1 = 'C5+lpZ7tcVwmwQIMcRtPbsQtWLABXhQzejna0wHFr8M=';
const ISRG_ROOT_X2 = 'diGVwiVYbubAI3RW4hB9xU8e/CH2GnkuvVFZE8zmgzI=';
const LE_YE1 = 'brzvtCELCIZUo4sD/qPX0ccRtPsd3DY6RfmxpOU9oB4=';
const LE_E7 = 'y7xVm0TVJNahMr2sZydE2jQH8SquXV9yLF9seROHHHU=';
const LE_E8 = 'iFvwVyJSxnQdyaUvUERIf+8qk7gRze3612JMwoO3zdU=';
const LE_E5 = 'NYbU7PBwV4y9J67c4guWTki8FJ+uudrXL0a4V4aRcrg=';

const RAILWAY_HOST = 'web-production-58776.up.railway.app';

function loadModule(): typeof import('../certificatePinning') {
  let mod: typeof import('../certificatePinning');
  jest.isolateModules(() => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    mod = require('../certificatePinning');
  });
  return mod!;
}

describe('setupCertificatePinning', () => {
  const devFlag = () => (globalThis as any).__DEV__;
  let savedDev: unknown;

  beforeEach(() => {
    savedDev = devFlag();
    mockInitializeSslPinning.mockReset().mockResolvedValue(undefined);
    mockCaptureMessage.mockReset();
  });

  afterEach(() => {
    (globalThis as any).__DEV__ = savedDev;
  });

  // --- MB-security-04: RSA-chain backup pin -------------------------------

  it('pins the ISRG Root X1 (RSA chain) backup', async () => {
    const { setupCertificatePinning } = loadModule();
    await setupCertificatePinning();
    expect(mockInitializeSslPinning).toHaveBeenCalledTimes(1);
    const config = mockInitializeSslPinning.mock.calls[0][0] as Record<string, any>;
    expect(config[RAILWAY_HOST].publicKeyHashes).toContain(ISRG_ROOT_X1);
  });

  it('keeps ALL five existing pins (fix is additive, removes nothing)', async () => {
    const { setupCertificatePinning } = loadModule();
    await setupCertificatePinning();
    const hashes = (mockInitializeSslPinning.mock.calls[0][0] as Record<string, any>)[
      RAILWAY_HOST
    ].publicKeyHashes as string[];
    for (const pin of [ISRG_ROOT_X2, LE_YE1, LE_E7, LE_E8, LE_E5]) {
      expect(hashes).toContain(pin);
    }
    const config = mockInitializeSslPinning.mock.calls[0][0] as Record<string, any>;
    expect(config[RAILWAY_HOST].includeSubdomains).toBe(true);
  });

  // --- MB-security-07: observable release-build init failure --------------

  it('captures a Sentry warning when init fails in a RELEASE build', async () => {
    (globalThis as any).__DEV__ = false;
    mockInitializeSslPinning.mockRejectedValue(new Error('native module missing'));
    const { setupCertificatePinning } = loadModule();
    await setupCertificatePinning();
    expect(mockCaptureMessage).toHaveBeenCalledTimes(1);
    const [message, context] = mockCaptureMessage.mock.calls[0];
    expect(message).toContain('[SECURITY]');
    expect(message.toLowerCase()).toContain('pinning');
    expect((context as any).level).toBe('warning');
    expect(String((context as any).extra.message)).toContain('native module missing');
  });

  it('stays quiet in DEV (Expo Go is the expected benign case)', async () => {
    (globalThis as any).__DEV__ = true;
    mockInitializeSslPinning.mockRejectedValue(new Error('Expo Go: no native module'));
    const { setupCertificatePinning } = loadModule();
    await setupCertificatePinning();
    expect(mockCaptureMessage).not.toHaveBeenCalled();
  });

  it('remains fail-open: an init failure never throws to the caller', async () => {
    (globalThis as any).__DEV__ = false;
    mockInitializeSslPinning.mockRejectedValue(new Error('boom'));
    const { setupCertificatePinning } = loadModule();
    await expect(setupCertificatePinning()).resolves.toBeUndefined();
  });

  it('a failed init does not latch — a later call retries initialization', async () => {
    (globalThis as any).__DEV__ = false;
    mockInitializeSslPinning.mockRejectedValueOnce(new Error('transient'));
    const { setupCertificatePinning } = loadModule();
    await setupCertificatePinning();
    await setupCertificatePinning();
    expect(mockInitializeSslPinning).toHaveBeenCalledTimes(2);
  });
});
