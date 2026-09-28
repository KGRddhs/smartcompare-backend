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
const mockAddSslPinningErrorListener = jest.fn();
jest.mock('react-native-ssl-public-key-pinning', () => ({
  initializeSslPinning: (...args: unknown[]) => mockInitializeSslPinning(...args),
  isSslPinningAvailable: () => false,
  addSslPinningErrorListener: (...args: unknown[]) => mockAddSslPinningErrorListener(...args),
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
    mockAddSslPinningErrorListener.mockReset().mockReturnValue({ remove: jest.fn() });
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

// ---------------------------------------------------------------------------
// Session 69 U5 (audit BLD-BP-01): the LIVE chain of web-production-58776
// measured 2026-09-29 is leaf <- Let's Encrypt YE2 <- ISRG Root YE <- ISRG
// Root X2. Only the ISRG Root X2 pin matched (X1 on devices that end the chain
// there), and that match disappears the day a phone trusts Root YE directly
// (path building then stops at Root YE). Every SPKI below was derived from the
// PEMs on https://letsencrypt.org/certificates/ (certs/gen-y/*.pem); YE2 and
// Root YE were also cross-checked against the live chain.
// ---------------------------------------------------------------------------
const LE_YE2 = 's/tdAOmUzd8syaTuqfgGvFcn6DzA5Cmb+Vby1ST+U3Y=';
const LE_YE3 = 'ppiiCCS+BOR6GjPE+kiHMb6SAR8jox6QDiyibJwqz84=';
const LE_YR1 = 'LoMHBotttiDko50Gi13uXW71eIy7LAttI+rYT8wXF4w=';
const LE_YR2 = 'nWN7PSep5XDQdge5zK24CnCRXHr3KvzhKEGxsdqCX9E=';
const LE_YR3 = 'UaqofZhLVZrGnpKfiIoCLYMuCJ/026CkErUQG8pLx5k=';
const ISRG_ROOT_YE = 'sCkq5UWXjg+7mKu9lMhhYF5bGLsy7VI/UNW3tccdR7w=';
const ISRG_ROOT_YR = 'fk6IOKit1ild5647BH06ujSIq5XbCgqlbYl6ANhhi88=';

describe('setupCertificatePinning — Gen-Y chain coverage (session 69 U5)', () => {
  const devFlag = () => (globalThis as any).__DEV__;
  let savedDev: unknown;
  beforeEach(() => {
    savedDev = devFlag();
    mockInitializeSslPinning.mockReset().mockResolvedValue(undefined);
    mockAddSslPinningErrorListener.mockReset().mockReturnValue({ remove: jest.fn() });
    mockCaptureMessage.mockReset();
  });
  afterEach(() => {
    (globalThis as any).__DEV__ = savedDev;
  });

  const hashesOf = async () => {
    const { setupCertificatePinning } = loadModule();
    await setupCertificatePinning();
    return (mockInitializeSslPinning.mock.calls[0][0] as Record<string, any>)[RAILWAY_HOST]
      .publicKeyHashes as string[];
  };

  it('pins every certificate of the LIVE chain measured 2026-09-29 (YE2, Root YE, Root X2)', async () => {
    const hashes = await hashesOf();
    for (const pin of [LE_YE2, ISRG_ROOT_YE, ISRG_ROOT_X2]) expect(hashes).toContain(pin);
  });

  it('pins the whole Gen-Y family so any LE rotation inside it keeps the store binary alive', async () => {
    const hashes = await hashesOf();
    for (const pin of [LE_YE1, LE_YE2, LE_YE3, LE_YR1, LE_YR2, LE_YR3, ISRG_ROOT_YE, ISRG_ROOT_YR]) {
      expect(hashes).toContain(pin);
    }
  });

  it('is additive: the previous six pins all remain', async () => {
    const hashes = await hashesOf();
    for (const pin of [ISRG_ROOT_X2, ISRG_ROOT_X1, LE_YE1, LE_E7, LE_E8, LE_E5]) expect(hashes).toContain(pin);
    expect(new Set(hashes).size).toBe(hashes.length);
  });

  it('registers a pin-error listener after a successful init and forwards a mismatch to Sentry', async () => {
    (globalThis as any).__DEV__ = false;
    const { setupCertificatePinning } = loadModule();
    await setupCertificatePinning();
    expect(mockAddSslPinningErrorListener).toHaveBeenCalledTimes(1);
    const listener = mockAddSslPinningErrorListener.mock.calls[0][0] as (e: any) => void;
    listener({ serverHostname: RAILWAY_HOST, message: 'Pin verification failed' });
    expect(mockCaptureMessage).toHaveBeenCalledTimes(1);
    const [message, context] = mockCaptureMessage.mock.calls[0];
    expect(message).toContain('[SECURITY]');
    expect(message.toLowerCase()).toContain('pin');
    expect((context as any).level).toBe('error');
    expect(String((context as any).extra.serverHostname)).toBe(RAILWAY_HOST);
  });

  it('does not register the listener when init failed (nothing is pinned to report on)', async () => {
    (globalThis as any).__DEV__ = false;
    mockInitializeSslPinning.mockRejectedValue(new Error('boom'));
    const { setupCertificatePinning } = loadModule();
    await setupCertificatePinning();
    expect(mockAddSslPinningErrorListener).not.toHaveBeenCalled();
  });

  it('a listener that throws never breaks the init path, never reports "unpinned", and keeps the init latched', async () => {
    (globalThis as any).__DEV__ = false;
    mockAddSslPinningErrorListener.mockImplementation(() => {
      throw new Error('listener unavailable');
    });
    const { setupCertificatePinning } = loadModule();
    await expect(setupCertificatePinning()).resolves.toBeUndefined();
    // The inner try/catch must swallow it: a throw reaching the outer catch
    // would emit a FALSE "session is running unpinned" warning for a session
    // that IS pinned, and would leave the init un-latched.
    expect(mockCaptureMessage).not.toHaveBeenCalled();
    await setupCertificatePinning();
    expect(mockInitializeSslPinning).toHaveBeenCalledTimes(1);
  });

  it('the exact pin set is the exported BACKEND_PUBLIC_KEY_HASHES (13 pins, no leaf, no strays)', async () => {
    const mod = loadModule();
    await mod.setupCertificatePinning();
    const hashes = (mockInitializeSslPinning.mock.calls[0][0] as Record<string, any>)[RAILWAY_HOST]
      .publicKeyHashes as string[];
    const expected = [
      ISRG_ROOT_X2, ISRG_ROOT_X1, ISRG_ROOT_YE, ISRG_ROOT_YR,
      LE_YE2, LE_YE1, LE_YE3, LE_YR1, LE_YR2, LE_YR3,
      LE_E7, LE_E8, LE_E5,
    ];
    expect(new Set(hashes)).toEqual(new Set(expected));
    expect(hashes).toHaveLength(13);
    expect([...mod.BACKEND_PUBLIC_KEY_HASHES]).toEqual(hashes);
    // The leaf measured 2026-09-29 is never pinned.
    expect(hashes).not.toContain('HLb3HRWGSbybWXPPGKsaL3NwYvwWHrTYTCYU15lfeQ4=');
  });

  it('an iOS-shaped event (no message) is reported with an empty message, and a second mismatch is not re-reported', async () => {
    (globalThis as any).__DEV__ = false;
    const { setupCertificatePinning } = loadModule();
    await setupCertificatePinning();
    const listener = mockAddSslPinningErrorListener.mock.calls[0][0] as (e: any) => void;
    listener({ serverHostname: RAILWAY_HOST });
    listener({ serverHostname: RAILWAY_HOST, message: 'Certificate pinning failure!' });
    expect(mockCaptureMessage).toHaveBeenCalledTimes(1);
    const [, context] = mockCaptureMessage.mock.calls[0];
    expect((context as any).extra.message).toBe('');
    expect((context as any).fingerprint).toEqual(['cert-pin-mismatch']);
  });
});
