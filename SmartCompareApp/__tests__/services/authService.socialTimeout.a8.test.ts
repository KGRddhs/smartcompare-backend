/**
 * A8 — the social-login raw fetches are bounded, and a deadline expiry is
 * kept OUT of the [B4-DIAG] diagnostic channel.
 *
 * THE DEFECT
 * `signInWithGoogle` / `signInWithApple` POST to /api/v1/auth/social-login
 * with a raw `fetch` and no deadline. RN sets none of its own, so a stalled
 * socket NEVER SETTLES (it does not throw), the surrounding try/catch cannot
 * fire, and LoginScreen's `socialLoading` stays set — with
 * `disabled = loading || Boolean(socialLoading)` that leaves both social
 * buttons AND the email/password form inert, with no cancel affordance.
 *
 * Every timeout case below drives a fetch that never settles, which is the
 * only faithful reproduction: a `mockRejectedValue` would exercise the
 * catch that already existed and prove nothing.
 *
 * TWO NO-REGRESSION HALVES ARE PINNED ALONGSIDE
 *  - a real transport throw (offline / cert-pin) must STILL produce the
 *    [B4-DIAG] Sentry capture + diagnostic string, because that channel is
 *    live for the open Google Sign-In investigation (CLAUDE.md Known Bugs);
 *  - a deadline must NOT produce it, or the channel fills with timeouts.
 */

import * as SecureStore from 'expo-secure-store';
import { SOCIAL_LOGIN_TIMEOUT_MS } from '../../src/services/fetchWithDeadline';

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

const mockAddBreadcrumb = jest.fn();
const mockCaptureMessage = jest.fn();
jest.mock(
  '@sentry/react-native',
  () => ({
    addBreadcrumb: (...args: unknown[]) => mockAddBreadcrumb(...args),
    captureMessage: (...args: unknown[]) => mockCaptureMessage(...args),
    captureException: jest.fn(),
    init: jest.fn(),
  }),
  { virtual: true }
);

const saveTokenSpy = jest.spyOn(SecureStore, 'setItemAsync');

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { signInWithGoogle, signInWithApple, SIGN_IN_TIMEOUT_KEY } = require('../../src/services/authService');

const ID_TOKEN = 'header.payload.signature';

/**
 * A fetch that never settles, plus a promise that resolves the moment it is
 * called — so the test advances the deadline only AFTER the request is in
 * flight, never before.
 */
function armStalledFetch(): Promise<void> {
  let started: () => void = () => {};
  const inFlight = new Promise<void>((resolve) => {
    started = resolve;
  });
  mockFetch.mockImplementation(() => {
    started();
    return new Promise(() => {});
  });
  return inFlight;
}

beforeEach(() => {
  mockSignIn.mockReset();
  mockAppleSignInAsync.mockReset();
  mockHasPlayServices.mockClear();
  mockFetch.mockReset();
  mockAddBreadcrumb.mockClear();
  mockCaptureMessage.mockClear();
  saveTokenSpy.mockClear();
  mockSignIn.mockResolvedValue({ data: { idToken: ID_TOKEN } });
  mockAppleSignInAsync.mockResolvedValue({ identityToken: ID_TOKEN });
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('signInWithGoogle — deadline (A8)', () => {
  it('resolves with the localizable timeout key when the POST never settles', async () => {
    const inFlight = armStalledFetch();

    const pending = signInWithGoogle();
    await inFlight;
    jest.advanceTimersByTime(SOCIAL_LOGIN_TIMEOUT_MS);
    const result = await pending;

    expect(result.success).toBe(false);
    expect(result.errorKey).toBe(SIGN_IN_TIMEOUT_KEY);
    expect(SIGN_IN_TIMEOUT_KEY).toBe('auth.signInTimeout');
    // No English diagnostic string — the screen renders t(errorKey).
    expect(result.error).toBeUndefined();
    expect(saveTokenSpy).not.toHaveBeenCalled();
  });

  it('aborts the in-flight request rather than leaving the socket open', async () => {
    const inFlight = armStalledFetch();

    const pending = signInWithGoogle();
    await inFlight;
    const signal = mockFetch.mock.calls[0][1].signal;
    expect(signal).toBeDefined();
    expect(signal.aborted).toBe(false);

    jest.advanceTimersByTime(SOCIAL_LOGIN_TIMEOUT_MS);
    await pending;

    expect(signal.aborted).toBe(true);
  });

  it('does NOT pollute the [B4-DIAG] Sentry channel with a timeout', async () => {
    const inFlight = armStalledFetch();

    const pending = signInWithGoogle();
    await inFlight;
    jest.advanceTimersByTime(SOCIAL_LOGIN_TIMEOUT_MS);
    await pending;

    expect(mockCaptureMessage).not.toHaveBeenCalled();
    const categories = mockAddBreadcrumb.mock.calls.map((c: any[]) => c[0]?.category);
    expect(categories).toContain('a8_deadline');
  });

  it('keeps the POST body unchanged when a deadline is armed', async () => {
    const inFlight = armStalledFetch();

    const pending = signInWithGoogle();
    await inFlight;
    jest.advanceTimersByTime(SOCIAL_LOGIN_TIMEOUT_MS);
    await pending;

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(Object.keys(body).sort()).toEqual(['id_token', 'provider']);
  });
});

describe('signInWithGoogle — no regression on the paths that already worked', () => {
  it('a real transport throw STILL raises the [B4-DIAG] network capture', async () => {
    mockFetch.mockRejectedValue(new TypeError('Network request failed'));

    const result = await signInWithGoogle();

    expect(result.success).toBe(false);
    expect(result.errorKey).toBeUndefined();
    expect(result.error).toContain('[B4-DIAG] network/cert-pin failure');
    expect(mockCaptureMessage).toHaveBeenCalled();
  });

  it('a 200 still saves the session and returns success', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        user: { id: 'u1', email: 'u1@example.com' },
        session: { access_token: 'at-1', refresh_token: 'rt-1' },
      }),
    });

    const result = await signInWithGoogle();

    expect(result.success).toBe(true);
    expect(result.token).toBe('at-1');
    expect(result.errorKey).toBeUndefined();
    expect(saveTokenSpy.mock.calls.map((c) => c[0])).toEqual(
      expect.arrayContaining(['qaren_token', 'qaren_refresh_token'])
    );
  });
});

describe('signInWithApple — deadline (A8)', () => {
  it('resolves with the localizable timeout key when the POST never settles', async () => {
    const inFlight = armStalledFetch();

    const pending = signInWithApple();
    await inFlight;
    jest.advanceTimersByTime(SOCIAL_LOGIN_TIMEOUT_MS);
    const result = await pending;

    expect(result.success).toBe(false);
    expect(result.errorKey).toBe(SIGN_IN_TIMEOUT_KEY);
    expect(result.error).toBeUndefined();
    expect(saveTokenSpy).not.toHaveBeenCalled();
    const categories = mockAddBreadcrumb.mock.calls.map((c: any[]) => c[0]?.category);
    expect(categories).toContain('a8_deadline');
  });

  it('aborts the in-flight request', async () => {
    const inFlight = armStalledFetch();

    const pending = signInWithApple();
    await inFlight;
    const signal = mockFetch.mock.calls[0][1].signal;

    jest.advanceTimersByTime(SOCIAL_LOGIN_TIMEOUT_MS);
    await pending;

    expect(signal.aborted).toBe(true);
  });

  it('a real transport throw still falls to the pre-existing outer catch', async () => {
    mockFetch.mockRejectedValue(new TypeError('Network request failed'));

    const result = await signInWithApple();

    expect(result.success).toBe(false);
    expect(result.errorKey).toBeUndefined();
    expect(result.error).toBe('Network request failed');
  });

  it('a 200 still returns success with the session token', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        user: { id: 'u2', email: 'u2@example.com' },
        session: { access_token: 'at-2' },
      }),
    });

    const result = await signInWithApple();

    expect(result.success).toBe(true);
    expect(result.token).toBe('at-2');
    expect(result.errorKey).toBeUndefined();
  });
});
