/**
 * W3-16 — authService carries the consent payload on the account-creating
 * requests (spec §5-A.8, §5-A.9, §5-A.10).
 *
 * The fields are added ONLY when the caller passes a consent object, so
 *  - `register(e, p, {})` still posts no consent key (§5-A.9, compat pin), and
 *  - `signInWithGoogle()` with no argument still posts EXACTLY
 *    { provider, id_token } — pinned by authService.b4.test.ts:170, not
 *    duplicated here.
 *
 * Harness: the axios `api.post` mock of __tests__/authService.m18.test.ts for
 * register, and the Google / Apple / expo-crypto / Sentry mocks + global
 * fetch of __tests__/services/authService.socialTimeout.a8.test.ts for the
 * two raw social-login fetches.
 */

import { TERMS_VERSION } from '../../src/services/consent';

const mockPost = jest.fn();
jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockPost(...args),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
  API_BASE_URL: 'https://test.invalid',
  getOrStartRefresh: jest.fn(),
}));

jest.mock('../../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: jest.fn().mockResolvedValue('f'.repeat(64)),
}));

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
  { virtual: true },
);

const mockAppleSignInAsync = jest.fn();
jest.mock(
  'expo-apple-authentication',
  () => ({
    signInAsync: (...args: unknown[]) => mockAppleSignInAsync(...args),
    isAvailableAsync: jest.fn().mockResolvedValue(true),
    AppleAuthenticationScope: { FULL_NAME: 0, EMAIL: 1 },
  }),
  { virtual: true },
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
  { virtual: true },
);

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { register, signInWithGoogle, signInWithApple } = require('../../src/services/authService');

const CONSENT = {
  terms_accepted: true as const,
  terms_version: TERMS_VERSION,
  age_attested: true as const,
};
const CONSENT_KEYS = ['terms_accepted', 'terms_version', 'age_attested'];
const ID_TOKEN = 'header.payload.signature';

function postedRegisterBody(): Record<string, unknown> {
  expect(mockPost).toHaveBeenCalledTimes(1);
  expect(mockPost.mock.calls[0][0]).toBe('/api/v1/auth/register');
  return mockPost.mock.calls[0][1];
}

function sentFetchBody(): Record<string, unknown> {
  expect(mockFetch).toHaveBeenCalledTimes(1);
  expect(String(mockFetch.mock.calls[0][0])).toMatch(/\/api\/v1\/auth\/social-login$/);
  return JSON.parse(mockFetch.mock.calls[0][1].body);
}

beforeEach(() => {
  mockPost.mockReset();
  mockFetch.mockReset();
  mockSignIn.mockReset();
  mockAppleSignInAsync.mockReset();
  mockPost.mockResolvedValue({
    data: {
      user: { id: 'u1', email: 'new@user.bh' },
      session: { access_token: 'at-1', refresh_token: 'rt-1' },
    },
  });
  mockSignIn.mockResolvedValue({ data: { idToken: ID_TOKEN } });
  mockAppleSignInAsync.mockResolvedValue({ identityToken: ID_TOKEN });
  mockFetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      success: true,
      user: { id: 'u1' },
      session: { access_token: 't', refresh_token: 'r' },
    }),
  });
});

describe('W3-16 authService — register() body', () => {
  // §5-A.8
  it('8. register(e, p, { consent }) posts terms_accepted / terms_version / age_attested', async () => {
    await register('new@user.bh', 'StrongPass1x', { consent: CONSENT });

    const body = postedRegisterBody();
    expect(body).toMatchObject({
      email: 'new@user.bh',
      password: 'StrongPass1x',
      terms_accepted: true,
      terms_version: TERMS_VERSION,
      age_attested: true,
    });
  });

  // §5-A.9 — PRESERVE PIN (green today and after): no consent object -> no
  // consent key. Mutation that must redden it: spread the fields unconditionally.
  it('9. register(e, p, {}) posts NONE of the consent keys', async () => {
    await register('new@user.bh', 'StrongPass1x', {});

    const body = postedRegisterBody();
    for (const key of CONSENT_KEYS) {
      expect(key in body).toBe(false);
    }
    expect(body).toEqual({ email: 'new@user.bh', password: 'StrongPass1x' });
  });
});

describe('W3-16 authService — social-login bodies', () => {
  // §5-A.10 (Google)
  it('10a. signInWithGoogle(consent) posts the consent keys alongside provider + id_token', async () => {
    await signInWithGoogle(CONSENT);

    expect(sentFetchBody()).toEqual({
      provider: 'google',
      id_token: ID_TOKEN,
      terms_accepted: true,
      terms_version: TERMS_VERSION,
      age_attested: true,
    });
  });

  // §5-A.10 (Apple)
  it('10b. signInWithApple(consent) posts the consent keys alongside provider + id_token + nonce', async () => {
    await signInWithApple(CONSENT);

    const body = sentFetchBody();
    expect(typeof body.nonce).toBe('string');
    expect((body.nonce as string).length).toBeGreaterThan(0);
    expect(body).toEqual({
      provider: 'apple',
      id_token: ID_TOKEN,
      nonce: body.nonce,
      terms_accepted: true,
      terms_version: TERMS_VERSION,
      age_attested: true,
    });
  });
});
