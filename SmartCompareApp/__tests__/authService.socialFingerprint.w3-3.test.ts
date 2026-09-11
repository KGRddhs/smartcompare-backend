/**
 * W3-3 — MB-NETWORK-CONTRACT-03 (client half).
 *
 * THE DEFECT (measured at ed75dc70 / b63a8368)
 * `signInWithGoogle` and `signInWithApple` POST to /api/v1/auth/social-login
 * with `headers: { 'Content-Type': 'application/json' }` and nothing else
 * (authService.ts:728-736 google, :863-875 apple), and neither path ever calls
 * `getDeviceFingerprint` (0 calls). `/register` (:131-148) has sent
 * `X-Device-Fingerprint` since Bundle A, so a user who arrives through Google
 * or Apple has NO row-level device binding: the backend can never write
 * `users.device_fingerprint_hash` for them, and every downstream anti-farming
 * control that reads it fails OPEN
 * (`referral_service._referrer_device_lifetime_count`,
 * `abuse_detection_service.evaluate_invite` SAME_DEVICE).
 *
 * RED here: C1, C2.
 * PINS (green today AND after the fix, each with a named mutation): C3, C4,
 * C6, and the register-header pin (§6 — no existing client test asserts it;
 * `grep X-Device-Fingerprint __tests__` = 0 at base).
 *
 * Harness: mocks copied from `__tests__/services/authService.socialTimeout.a8.test.ts:27-75`
 * (google-signin virtual mock, expo-apple-authentication virtual mock,
 * expo-crypto factory, Sentry shim, global.fetch recorder), with every
 * `'../../src/...'` path rewritten to `'../src/...'` because this file sits at
 * `__tests__/` root, not `__tests__/services/` (RULING R6). `deviceFingerprint`
 * is MOCKED (the `authService.m18.test.ts:41` idiom): under the a8 expo-crypto
 * factory the REAL module rejects, which is the separate defect C5 measures.
 */

const mockSignIn = jest.fn();
const mockHasPlayServices = jest.fn().mockResolvedValue(true);
jest.mock(
  '@react-native-google-signin/google-signin',
  () => ({
    GoogleSignin: {
      configure: jest.fn(),
      hasPlayServices: mockHasPlayServices,
      signIn: mockSignIn,
    },
  }),
  { virtual: true }
);

const mockAppleSignInAsync = jest.fn();
jest.mock(
  'expo-apple-authentication',
  () => ({
    signInAsync: (...args: unknown[]) => mockAppleSignInAsync(...args),
    isAvailableAsync: jest.fn().mockResolvedValue(true),
    AppleAuthenticationScope: { FULL_NAME: 0, EMAIL: 1 },
  }),
  { virtual: true }
);

jest.mock('expo-crypto', () => ({
  getRandomBytesAsync: jest.fn().mockResolvedValue(new Uint8Array(32)),
  digestStringAsync: jest.fn().mockResolvedValue('a'.repeat(64)),
  CryptoDigestAlgorithm: { SHA256: 'SHA-256' },
}));

jest.mock(
  '@sentry/react-native',
  () => ({
    addBreadcrumb: jest.fn(),
    captureMessage: jest.fn(),
    captureException: jest.fn(),
    init: jest.fn(),
  }),
  { virtual: true }
);

const FP = 'b'.repeat(64);
const mockGetDeviceFingerprint = jest.fn();
jest.mock('../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: (...args: unknown[]) => mockGetDeviceFingerprint(...args),
}));

// The register pin drives `api.post`; the social paths use the raw
// `fetchWithDeadline` -> global.fetch and are unaffected by this mock.
const mockApiPost = jest.fn();
jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: unknown[]) => mockApiPost(...args),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
  API_BASE_URL: 'https://test.invalid',
  getOrStartRefresh: jest.fn(),
}));

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { signInWithGoogle, signInWithApple, register } = require('../src/services/authService');

const ID_TOKEN = 'header.payload.signature';

function okResponse() {
  return {
    ok: true,
    status: 200,
    json: async () => ({
      success: true,
      user: { id: 'u1', email: 'u1@example.com' },
      session: { access_token: 'at-1', refresh_token: 'rt-1' },
    }),
  };
}

beforeEach(() => {
  mockSignIn.mockReset();
  mockAppleSignInAsync.mockReset();
  mockHasPlayServices.mockClear();
  mockFetch.mockReset();
  mockApiPost.mockReset();
  mockGetDeviceFingerprint.mockReset();
  mockSignIn.mockResolvedValue({ data: { idToken: ID_TOKEN } });
  mockAppleSignInAsync.mockResolvedValue({ identityToken: ID_TOKEN });
  mockFetch.mockResolvedValue(okResponse());
  mockGetDeviceFingerprint.mockResolvedValue(FP);
});

describe('W3-3 C1/C2 — social sign-in sends X-Device-Fingerprint (RED at base)', () => {
  it('C1: signInWithGoogle POSTs social-login with the 64-hex fingerprint header', async () => {
    const result = await signInWithGoogle();

    expect(result.success).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(String(url)).toContain('/api/v1/auth/social-login');
    // Content-Type must survive alongside the new key (R13: plain object
    // literal, never a Headers instance — a8 and these tests index it).
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(init.headers['X-Device-Fingerprint']).toBe(FP);
    expect(mockGetDeviceFingerprint).toHaveBeenCalledTimes(1);
  });

  it('C2: signInWithApple POSTs social-login with the 64-hex fingerprint header', async () => {
    const result = await signInWithApple();

    expect(result.success).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0];
    expect(String(url)).toContain('/api/v1/auth/social-login');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(init.headers['X-Device-Fingerprint']).toBe(FP);
    expect(mockGetDeviceFingerprint).toHaveBeenCalledTimes(1);
  });
});

describe('W3-3 pins — the fingerprint must not change anything else', () => {
  it('C3 (pin): the google body stays exactly {provider, id_token} — the hash never rides in the body', async () => {
    // B4 invariant: Google must send NO nonce, and the fix must not smuggle
    // the fingerprint into the JSON body instead of the header.
    // Mutation that reddens this: put the hash in the body.
    await signInWithGoogle();

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(Object.keys(body).sort()).toEqual(['id_token', 'provider']);
    expect(body.provider).toBe('google');
    expect(body.id_token).toBe(ID_TOKEN);
    expect(Object.values(body)).not.toContain(FP);
  });

  it('C4 (pin): a fingerprint failure never blocks google sign-in', async () => {
    // Tolerance pin, mirrors register (:131-136). Mutation that reddens this:
    // remove the try/catch around getDeviceFingerprint() — the rejection then
    // reaches the outer catch and returns [B4-DIAG] threw before fetch.
    mockGetDeviceFingerprint.mockRejectedValue(new Error('keychain'));

    const result = await signInWithGoogle();

    expect(result.success).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const init = mockFetch.mock.calls[0][1];
    expect(init.headers['Content-Type']).toBe('application/json');
    expect('X-Device-Fingerprint' in init.headers).toBe(false);
  });

  it('C4 (pin): a fingerprint failure never blocks apple sign-in', async () => {
    mockGetDeviceFingerprint.mockRejectedValue(new Error('keychain'));

    const result = await signInWithApple();

    expect(result.success).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const init = mockFetch.mock.calls[0][1];
    expect(init.headers['Content-Type']).toBe('application/json');
    expect('X-Device-Fingerprint' in init.headers).toBe(false);
  });

  it('C6 (pin): a cancelled google sign-in never reads the fingerprint', async () => {
    // The read belongs AFTER gs.signIn() returns an id token, so a user who
    // backs out of the native sheet touches neither SecureStore nor crypto.
    // Mutation that reddens this: move the fingerprint read above gs.signIn().
    const cancelled: any = new Error('cancelled');
    cancelled.code = 'SIGN_IN_CANCELLED';
    mockSignIn.mockRejectedValue(cancelled);

    const result = await signInWithGoogle();

    expect(result).toEqual({ success: false, error: 'Sign-in cancelled' });
    expect(mockGetDeviceFingerprint).not.toHaveBeenCalled();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('register pin: /auth/register still sends X-Device-Fingerprint (§6 — no other test asserts it)', async () => {
    // Green today and after. Mutation that reddens this: drop the third
    // api.post argument in register().
    mockApiPost.mockResolvedValue({
      data: {
        success: true,
        user: { id: 'u-reg', email: 'r@example.com' },
        session: { access_token: 'at', refresh_token: 'rt' },
      },
    });

    await register('r@example.com', 'ValidP@ss123');

    expect(mockApiPost).toHaveBeenCalledTimes(1);
    const [path, , config] = mockApiPost.mock.calls[0];
    expect(path).toBe('/api/v1/auth/register');
    expect(config).toEqual({ headers: { 'X-Device-Fingerprint': FP } });
  });
});
