/**
 * S69 U6 T2 — login() / register() return i18n KEYS, never raw strings (RT-9).
 *
 * Spec R2 + review corrections 7-11 and open questions A/B:
 *   - the backend envelope is `{success:false, error:'<English>', code, request_id}`
 *     (app/middleware/error_handler.py), so today's
 *     `error.response?.data?.detail || error.message` surfaces axios's
 *     "Request failed with status code 401" (authService.ts:188-194 / :259-265),
 *     and the non-throwing branches (:183-186 / :252-255) return raw English.
 *   - Login 401 -> `auth.errors.invalidCredentials` (every 401, by code/status;
 *     never by matching English text — open question A).
 *   - 429 -> settingsErrorKey: RATE_LIMITED -> common.errors.rateLimited,
 *     ACCOUNT_LOCKED -> common.errors.locked.
 *   - Register: TERMS_ACCEPTANCE_REQUIRED -> auth.consent.required,
 *     INVITE_CODE_NOT_FOUND -> auth.errors.inviteCodeNotFound (new key),
 *     duplicate-email BAD_REQUEST -> auth.registerFailed (open question B).
 *   - anything else -> auth.loginFailed / auth.registerFailed.
 *   - The key may travel in `errorKey` or `error`; `error` is never raw text.
 *   - LoginScreen / RegisterScreen render t(key) — including their catch arms
 *     (LoginScreen.tsx:333-334, RegisterScreen.tsx:268-271, correction 10).
 *   - Every new key is in BOTH catalogs; EN has no "couldn't"/"failed"/
 *     "try again"; AR is MSA without diacritics and without the nine banned
 *     terms of src/i18n/.copy-policy.json.
 *
 * .ts (not .tsx) per the spec path, so screens render via React.createElement.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

jest.mock('expo-apple-authentication', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactReq = require('react');
  return {
    __esModule: true,
    AppleAuthenticationButton: (props: any) =>
      ReactReq.createElement('AppleAuthenticationButton', props),
    AppleAuthenticationButtonType: { SIGN_IN: 0, CONTINUE: 1, SIGN_UP: 2 },
    AppleAuthenticationButtonStyle: { WHITE: 0, WHITE_OUTLINE: 1, BLACK: 2 },
    AppleAuthenticationScope: { FULL_NAME: 0, EMAIL: 1 },
    isAvailableAsync: jest.fn().mockResolvedValue(false),
    signInAsync: jest.fn(),
  };
});

jest.mock('react-native-reanimated', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const RealReact = require('react');
  const passthrough = ({ children, ...props }: any) =>
    RealReact.createElement('mock-Animated-View', props, children);
  return {
    __esModule: true,
    default: { View: passthrough, Text: passthrough },
    FadeIn: { duration: () => ({ delay: () => ({}) }), delay: () => ({}) },
    FadeInDown: { duration: () => ({ delay: () => ({}) }), delay: () => ({}) },
    useSharedValue: (init: any) => ({ value: init }),
    useAnimatedStyle: (fn: any) => fn(),
    withTiming: (v: any) => v,
    withRepeat: (a: any) => a,
    withDelay: (_: any, a: any) => a,
    withSequence: (...a: any[]) => a[a.length - 1],
    runOnJS: (fn: any) => fn,
    Easing: {
      inOut: () => (t: number) => t,
      out: () => (t: number) => t,
      ease: (t: number) => t,
      cubic: (t: number) => t,
    },
  };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: jest.fn(),
}));

jest.mock('../../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: jest.fn().mockResolvedValue('f'.repeat(64)),
}));

const mockPost = jest.fn();
jest.mock('../../src/services/api', () => {
  const actual = jest.requireActual('../../src/services/api');
  const client = {
    post: (...args: any[]) => mockPost(...args),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  };
  return { __esModule: true, ...actual, default: client, api: client };
});

// eslint-disable-next-line @typescript-eslint/no-require-imports
const authService = require('../../src/services/authService');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const LoginScreen = require('../../src/screens/LoginScreen').default;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const RegisterScreen = require('../../src/screens/RegisterScreen').default;
 
const en: Record<string, string> = require('../../src/i18n/en.json');
 
const ar: Record<string, string> = require('../../src/i18n/ar.json');
 
const policy = require('../../src/i18n/.copy-policy.json');

const RAW_401 = 'Request failed with status code 401';

/** An axios-shaped rejection carrying the backend's unified envelope. */
function axiosError(
  status: number,
  envelope: Record<string, unknown> | null,
  message = `Request failed with status code ${status}`,
) {
  const err: any = new Error(message);
  err.isAxiosError = true;
  err.response = { status, data: envelope, headers: {} };
  return err;
}

function envelope(error: string, code: string, extra: Record<string, unknown> = {}) {
  return { success: false, error, code, request_id: 'req-s69', ...extra };
}

/** The key the service returned, whichever field carries it. */
function keyOf(result: any): unknown {
  return result?.errorKey ?? result?.error;
}

/** The failure carries exactly `key`; `error` is never raw text. */
function expectKeyOnly(result: any, key: string, raws: string[]) {
  expect(result.success).toBe(false);
  expect(keyOf(result)).toBe(key);
  expect([undefined, key]).toContain(result.error);
  for (const raw of raws) {
    expect(String(result.error ?? '')).not.toContain(raw);
    expect(String(result.errorKey ?? '')).not.toContain(raw);
  }
  // A key the screen renders must exist in both catalogs.
  expect(typeof en[key]).toBe('string');
  expect(typeof ar[key]).toBe('string');
}

const AR_DIACRITICS = /[\u064b-\u0652\u0670]/;
const BRAND_AR = '\u0645\u064a\u0651\u0632'; // ميّز — the one diacritic allowed

function expectEnCopyClean(value: string) {
  expect(value.trim().length).toBeGreaterThan(0);
  expect(value).not.toMatch(/couldn['\u2019]?t|failed|try again/i);
  for (const { pattern } of policy.banned_en) {
    expect(value).not.toMatch(new RegExp(pattern));
  }
}

function expectArCopyClean(value: string) {
  expect(value.trim().length).toBeGreaterThan(0);
  expect(value).toMatch(/[\u0600-\u06ff]/);
  expect(value.split(BRAND_AR).join('')).not.toMatch(AR_DIACRITICS);
  for (const term of policy.scary_vocab_ar) {
    expect(value).not.toContain(term);
  }
  for (const { pattern } of policy.banned_ar) {
    expect(value).not.toContain(pattern);
  }
}

beforeEach(() => {
  mockPost.mockReset();
});

describe('S69 U6 T2 \u2014 login() maps failures to i18n keys', () => {
  it('T2.1 401 (AUTH_REQUIRED envelope) -> auth.errors.invalidCredentials, never the axios message or the English envelope text', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(401, envelope('Invalid email or password', 'AUTH_REQUIRED')),
    );
    const result = await authService.login('user@example.com', 'WrongPass1!');
    expectKeyOnly(result, 'auth.errors.invalidCredentials', [RAW_401, 'Invalid email or password']);
  });

  it('T2.2 401 carrying the unconfirmed-email message still maps by status, not by English text', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(401, envelope('Please verify your email before logging in', 'AUTH_REQUIRED')),
    );
    const result = await authService.login('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'auth.errors.invalidCredentials', [
      RAW_401,
      'Please verify your email before logging in',
    ]);
  });

  it('T2.3 429 RATE_LIMITED (slowapi 5/minute) -> common.errors.rateLimited', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(429, envelope('Rate limit exceeded: 5 per 1 minute', 'RATE_LIMITED')),
    );
    const result = await authService.login('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'common.errors.rateLimited', [
      'Request failed with status code 429',
      'Rate limit exceeded',
    ]);
  });

  it('T2.4 429 ACCOUNT_LOCKED (lockout, retry_after_seconds) -> common.errors.locked', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(
        429,
        envelope('Account temporarily locked', 'ACCOUNT_LOCKED', { retry_after_seconds: 900 }),
      ),
    );
    const result = await authService.login('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'common.errors.locked', [
      'Request failed with status code 429',
      'Account temporarily locked',
    ]);
  });

  it('T2.5 500 INTERNAL_ERROR -> auth.loginFailed', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(500, envelope('Something went wrong', 'INTERNAL_ERROR')),
    );
    const result = await authService.login('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'auth.loginFailed', [
      'Request failed with status code 500',
      'Something went wrong',
    ]);
  });

  it('T2.6 a transport failure with no response (ERR_NETWORK) -> auth.loginFailed, never "Network Error"', async () => {
    const err: any = new Error('Network Error');
    err.code = 'ERR_NETWORK';
    err.isAxiosError = true;
    mockPost.mockRejectedValueOnce(err);
    const result = await authService.login('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'auth.loginFailed', ['Network Error']);
  });

  it('T2.7 the non-throwing branch (200 without a user) -> auth.loginFailed, never the body text', async () => {
    mockPost.mockResolvedValueOnce({ data: { success: false, error: 'Login failed upstream' } });
    const result = await authService.login('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'auth.loginFailed', ['Login failed upstream', 'Login failed']);
  });
});

describe('S69 U6 T2 \u2014 register() maps failures to i18n keys', () => {
  it('T2.8 400 TERMS_ACCEPTANCE_REQUIRED -> auth.consent.required', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(400, envelope('Terms acceptance required', 'TERMS_ACCEPTANCE_REQUIRED')),
    );
    const result = await authService.register('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'auth.consent.required', [
      'Request failed with status code 400',
      'Terms acceptance required',
    ]);
  });

  it('T2.9 404 INVITE_CODE_NOT_FOUND -> auth.errors.inviteCodeNotFound (new key, both catalogs)', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(404, envelope('Invite code not found', 'INVITE_CODE_NOT_FOUND')),
    );
    const result = await authService.register('user@example.com', 'StrongPass1!', {
      inviteCode: 'QR-ABCDEF',
    });
    expectKeyOnly(result, 'auth.errors.inviteCodeNotFound', [
      'Request failed with status code 404',
      'Invite code not found',
    ]);
  });

  it('T2.10 duplicate email (plain-string 400, BAD_REQUEST) -> auth.registerFailed, never the English text', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(400, envelope('An account with this email already exists', 'BAD_REQUEST')),
    );
    const result = await authService.register('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'auth.registerFailed', [
      'Request failed with status code 400',
      'An account with this email already exists',
    ]);
  });

  it('T2.11 429 RATE_LIMITED -> common.errors.rateLimited', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(429, envelope('Rate limit exceeded: 3 per 1 minute', 'RATE_LIMITED')),
    );
    const result = await authService.register('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'common.errors.rateLimited', ['Request failed with status code 429']);
  });

  it('T2.12 500 -> auth.registerFailed', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(500, envelope('Something went wrong', 'INTERNAL_ERROR')),
    );
    const result = await authService.register('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'auth.registerFailed', ['Request failed with status code 500']);
  });

  it('T2.13 the non-throwing branch (200 without a user) -> auth.registerFailed, never the body text', async () => {
    mockPost.mockResolvedValueOnce({ data: { success: false, error: 'Registration failed upstream' } });
    const result = await authService.register('user@example.com', 'StrongPass1!');
    expectKeyOnly(result, 'auth.registerFailed', ['Registration failed upstream']);
  });
});

describe('S69 U6 T2 \u2014 the new keys are in both catalogs and follow the copy rules', () => {
  it.each(['auth.errors.invalidCredentials', 'auth.errors.inviteCodeNotFound'])(
    'T2.14 %s: EN clean (no couldn\'t / failed / try again), AR MSA without diacritics or banned terms',
    (key) => {
      expect(typeof en[key]).toBe('string');
      expect(typeof ar[key]).toBe('string');
      expectEnCopyClean(en[key]);
      expectArCopyClean(ar[key]);
    },
  );
});

// ---------------------------------------------------------------------------
// Screens render t(key), never result.error / parseApiError(err).message.
// ---------------------------------------------------------------------------

function makeNavigation(): any {
  return {
    navigate: jest.fn(),
    goBack: jest.fn(),
    canGoBack: () => false,
    getParent: () => ({ navigate: jest.fn() }),
  };
}

function renderLogin() {
  return render(
    React.createElement(LoginScreen, { navigation: makeNavigation(), onLoginSuccess: jest.fn() }),
  );
}

function renderRegister() {
  return render(
    React.createElement(RegisterScreen, {
      navigation: makeNavigation(),
      route: { params: undefined },
      onRegisterSuccess: jest.fn(),
    }),
  );
}

function submitLogin(screen: any) {
  fireEvent.changeText(screen.getByTestId('login-email-input'), 'user@example.com');
  fireEvent.changeText(screen.getByTestId('login-password-input'), 'StrongPass1!');
  fireEvent.press(screen.getByTestId('login-submit'));
}

function submitRegister(screen: any) {
  fireEvent.changeText(screen.getByPlaceholderText('auth.email'), 'user@example.com');
  fireEvent.changeText(screen.getByPlaceholderText('auth.password'), 'StrongPass1!');
  fireEvent.changeText(screen.getByPlaceholderText('auth.confirmPassword'), 'StrongPass1!');
  fireEvent.press(screen.getByTestId('consent-checkbox'));
  fireEvent.press(screen.getByText('auth.register'));
}

describe('S69 U6 T2 \u2014 LoginScreen / RegisterScreen render the translated key', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('T2.15 LoginScreen renders t("auth.errors.invalidCredentials") for a 401, never the raw axios / envelope text', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(401, envelope('Invalid email or password', 'AUTH_REQUIRED')),
    );
    const screen = renderLogin();
    submitLogin(screen);

    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText('auth.errors.invalidCredentials')).toBeTruthy());
    expect(screen.queryByText(RAW_401)).toBeNull();
    expect(screen.queryByText('Invalid email or password')).toBeNull();
  });

  it('T2.16 LoginScreen catch arm: a throwing login() renders t("auth.loginFailed"), never parseApiError(err).message', async () => {
    jest
      .spyOn(authService, 'login')
      .mockRejectedValueOnce(new Error('Request failed with status code 502'));
    const screen = renderLogin();
    submitLogin(screen);

    await waitFor(() => expect(screen.getByText('auth.loginFailed')).toBeTruthy());
    expect(screen.queryByText('Request failed with status code 502')).toBeNull();
  });

  it('T2.17 RegisterScreen renders t("auth.registerFailed") for a 500, never the raw axios text', async () => {
    mockPost.mockRejectedValueOnce(
      axiosError(500, envelope('Something went wrong', 'INTERNAL_ERROR')),
    );
    const screen = renderRegister();
    submitRegister(screen);

    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText('auth.registerFailed')).toBeTruthy());
    expect(screen.queryByText('Request failed with status code 500')).toBeNull();
    expect(screen.queryByText('Something went wrong')).toBeNull();
  });

  it('T2.18 RegisterScreen catch arm: a throwing register() renders t("auth.registerFailed"), never parseApiError(err).message', async () => {
    jest
      .spyOn(authService, 'register')
      .mockRejectedValueOnce(new Error('Request failed with status code 502'));
    const screen = renderRegister();
    submitRegister(screen);

    await waitFor(() => expect(screen.getByText('auth.registerFailed')).toBeTruthy());
    expect(screen.queryByText('Request failed with status code 502')).toBeNull();
  });
});
