/**
 * P-A8 — the social sign-in error banner renders an i18n KEY, never the
 * service's English diagnostic.
 *
 * Finding (mobile polish round, key `A8`): A8 built the right channel
 * (`AuthResponse.errorKey`) and used it for exactly ONE outcome — the
 * sign-in deadline. Every OTHER non-timeout failure return from
 * `signInWithGoogle` / `signInWithApple` carries `error`, and the screens
 * read `result.errorKey ? t(result.errorKey) : result.error || <fallback>`,
 * so the fallback was unreachable and the live user-facing sentence was the
 * service string itself:
 *
 *   "[B4-DIAG] backend rejected token. status=401 code=... server_error=..."
 *   "[B4-DIAG] network/cert-pin failure before backend. ..."
 *   "Failed to get Apple identity token"        <- forbidden "Failed to"
 *   "Google Sign-In not available (requires development build)"
 *
 * Those strings are addressed to the dispatcher (authService.ts:94-99 says
 * so itself) and are English-only, so an Arabic user read English transport
 * detail in the auth banner. The fix is where the SCREEN routes them, not
 * what the service returns: `setError(t(result.errorKey ?? 'auth.<x>Failed'))`
 * with the diagnostic going to the __DEV__ console (authService already
 * mirrors every [B4-DIAG] to Sentry.captureMessage at the source).
 *
 * Three fences, because the render test alone would pass if a later refactor
 * moved the leak into a different `setError` call:
 *   1. RENDER   — the four real failure shapes never reach the banner, in EN
 *                 and in AR, on both screens.
 *   2. SOURCE   — no `setError(...)` in either social handler takes anything
 *                 but `t(...)` (positive control on the call count first).
 *   3. COPY     — the two catalog sentences are clean in BOTH locales.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import enCatalog from '../src/i18n/en.json';
import arCatalog from '../src/i18n/ar.json';

const EN = enCatalog as Record<string, string>;
const AR = arCatalog as Record<string, string>;

// Mutable so a describe block can swap the app into Arabic. The `mock`
// prefix is what lets the hoisted jest.mock factory close over it.
const mockCatalogRef: { current: Record<string, string> } = { current: EN };

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string }) =>
      mockCatalogRef.current[key] ?? opts?.defaultValue ?? key,
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: jest.fn(),
}));

const mockSignInWithGoogle = jest.fn();
const mockSignInWithApple = jest.fn();
jest.mock('../src/services/authService', () => ({
  login: jest.fn(),
  register: jest.fn(),
  requestPasswordReset: jest.fn(),
  signInWithGoogle: (...args: any[]) => mockSignInWithGoogle(...args),
  signInWithApple: (...args: any[]) => mockSignInWithApple(...args),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(true),
}));

jest.mock('../src/services/api', () => ({
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const LoginScreen = require('../src/screens/LoginScreen').default;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const RegisterScreen = require('../src/screens/RegisterScreen').default;

const navigation: any = { navigate: jest.fn(), goBack: jest.fn() };

/**
 * The failure returns authService actually produces on a non-timeout social
 * outcome. Shapes copied from src/services/authService.ts (the [B4-DIAG]
 * builders at :672/:732/:757/:769 plus the two plain-English guards at
 * :649/:820). If any of these ever renders, an Arabic user reads English.
 */
const SERVICE_FAILURES: { label: string; error: string }[] = [
  {
    label: 'no idToken from the native SDK',
    error:
      '[B4-DIAG] no idToken from native SDK. signInResult.data keys: [(empty)]. Likely: Supabase iOS Client ID mismatch in app.json plugin config OR Google Cloud OAuth iOS bundle ID (com.qaren.app) not registered. Send this whole message to dispatcher.',
  },
  {
    label: 'network / cert-pin failure before the backend',
    error:
      '[B4-DIAG] network/cert-pin failure before backend. parts=3 err=Network request failed. Likely: certificatePinning.ts SPKI pin stale OR API_BASE_URL unreachable from device. Send this whole message.',
  },
  {
    label: 'backend rejected the token',
    error:
      '[B4-DIAG] backend rejected token. status=401 code=AUTH_REQUIRED server_error=invalid token. Send this whole message.',
  },
  {
    label: 'threw before fetch',
    error:
      '[B4-DIAG] threw before fetch. code=(no-code) msg=boom domain=(no-domain). Likely: hasPlayServices/signIn() native SDK reject. Send this whole message.',
  },
  {
    label: 'native module missing',
    error: 'Google Sign-In not available (requires development build)',
  },
  {
    label: 'no Apple identity token',
    error: 'Failed to get Apple identity token',
  },
];

const authServiceSrc = fs.readFileSync(
  path.resolve(__dirname, '../src/services/authService.ts'),
  'utf8',
);

beforeEach(() => {
  jest.clearAllMocks();
  mockCatalogRef.current = EN;
});

// ---------------------------------------------------------------------------
// Positive control — the leak channel this fence guards is REAL and still
// produces the strings above. Without this, deleting the [B4-DIAG] builders
// would make every assertion below vacuously true.
// ---------------------------------------------------------------------------
describe('positive control — authService still returns English diagnostics', () => {
  it('builds [B4-DIAG] strings and hands them back on `error`', () => {
    const diagHits = authServiceSrc.match(/\[B4-DIAG\]/g) || [];
    expect(diagHits.length).toBeGreaterThan(3);
    const diagReturns = authServiceSrc.match(/error: `\$\{(?:msg|rejMsg|thrownMsg)\}/g) || [];
    expect(diagReturns.length).toBeGreaterThan(2);
    // The plain-English guards are on the same channel.
    expect(authServiceSrc).toContain("error: 'Failed to get Apple identity token'");
  });
});

// ---------------------------------------------------------------------------
// Fence 1 — RENDER
// ---------------------------------------------------------------------------
describe('LoginScreen — a service diagnostic never reaches the banner (P-A8)', () => {
  it.each(SERVICE_FAILURES)('google: $label', async ({ error }) => {
    mockSignInWithGoogle.mockResolvedValueOnce({ success: false, error });

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    fireEvent.press(screen.getByTestId('login-social-google'));

    await waitFor(() => expect(screen.getByText(EN['auth.googleFailed'])).toBeTruthy());
    expect(screen.queryByText(error)).toBeNull();
    expect(screen.queryByText(/\[B4-DIAG\]/)).toBeNull();
  });

  it.each(SERVICE_FAILURES)('apple: $label', async ({ error }) => {
    mockSignInWithApple.mockResolvedValueOnce({ success: false, error });

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    await waitFor(() => expect(screen.getByTestId('login-social-apple')).toBeTruthy());
    fireEvent.press(screen.getByTestId('login-social-apple'));

    await waitFor(() => expect(screen.getByText(EN['auth.appleFailed'])).toBeTruthy());
    expect(screen.queryByText(error)).toBeNull();
  });

  it('an Arabic user reads Arabic, not the English diagnostic', async () => {
    mockCatalogRef.current = AR;
    mockSignInWithGoogle.mockResolvedValueOnce({
      success: false,
      error: SERVICE_FAILURES[2].error,
    });

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    fireEvent.press(screen.getByTestId('login-social-google'));

    await waitFor(() => expect(screen.getByText(AR['auth.googleFailed'])).toBeTruthy());
    expect(screen.queryByText(EN['auth.googleFailed'])).toBeNull();
    expect(screen.queryByText(SERVICE_FAILURES[2].error)).toBeNull();
  });

  it('a thrown social sign-in also renders the catalog sentence', async () => {
    mockSignInWithGoogle.mockRejectedValueOnce(new Error('Request failed with status code 502'));

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    fireEvent.press(screen.getByTestId('login-social-google'));

    await waitFor(() => expect(screen.getByText(EN['auth.googleFailed'])).toBeTruthy());
    expect(screen.queryByText('Request failed with status code 502')).toBeNull();
  });

  it('still routes a named outcome through its errorKey', async () => {
    // No-regression on A8 itself: the deadline key must keep winning.
    mockSignInWithGoogle.mockResolvedValueOnce({
      success: false,
      errorKey: 'auth.signInTimeout',
      error: SERVICE_FAILURES[0].error,
    });

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    fireEvent.press(screen.getByTestId('login-social-google'));

    await waitFor(() => expect(screen.getByText(EN['auth.signInTimeout'])).toBeTruthy());
  });

  it('a user cancellation still shows no banner at all', async () => {
    mockSignInWithGoogle.mockResolvedValueOnce({ success: false, error: 'Sign-in cancelled' });

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    fireEvent.press(screen.getByTestId('login-social-google'));

    await waitFor(() => expect(mockSignInWithGoogle).toHaveBeenCalledTimes(1));
    expect(screen.queryByTestId('login-error')).toBeNull();
  });
});

describe('RegisterScreen — a service diagnostic never reaches the banner (P-A8)', () => {
  function renderRegister() {
    return render(
      <RegisterScreen
        navigation={navigation}
        route={{ params: undefined }}
        onRegisterSuccess={jest.fn()}
      />
    );
  }

  it.each(SERVICE_FAILURES)('google: $label', async ({ error }) => {
    mockSignInWithGoogle.mockResolvedValueOnce({ success: false, error });

    const screen = renderRegister();
    fireEvent.press(screen.getByText(EN['auth.googleSignIn']));

    await waitFor(() => expect(screen.getByText(EN['auth.googleFailed'])).toBeTruthy());
    expect(screen.queryByText(error)).toBeNull();
  });

  it('a thrown social sign-in also renders the catalog sentence', async () => {
    mockSignInWithGoogle.mockRejectedValueOnce(new Error('Request failed with status code 502'));

    const screen = renderRegister();
    fireEvent.press(screen.getByText(EN['auth.googleSignIn']));

    await waitFor(() => expect(screen.getByText(EN['auth.googleFailed'])).toBeTruthy());
    expect(screen.queryByText('Request failed with status code 502')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Fence 2 — SOURCE. Comment-aware, so a fence can't be satisfied by prose.
// ---------------------------------------------------------------------------

/**
 * Drops `//` and block comments while preserving string literals (the copy
 * keys the fence anchors on live inside quotes). Same stripper as
 * __tests__/authService.bootOptimistic.a3.test.ts.
 */
function stripComments(src: string): string {
  let out = '';
  let quote: string | null = null;
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    const next = src[i + 1];
    if (quote) {
      out += c;
      if (c === '\\') {
        out += next ?? '';
        i += 2;
        continue;
      }
      if (c === quote) quote = null;
      i += 1;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') {
      quote = c;
      out += c;
      i += 1;
      continue;
    }
    if (c === '/' && next === '/') {
      while (i < src.length && src[i] !== '\n') i += 1;
      continue;
    }
    if (c === '/' && next === '*') {
      i += 2;
      while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) i += 1;
      i += 2;
      continue;
    }
    out += c;
    i += 1;
  }
  return out;
}

/** The body of one `const <name> = async () => { ... }` handler. */
function sliceHandler(src: string, name: string): string {
  const start = src.indexOf(`const ${name} = async`);
  expect(start).toBeGreaterThan(-1);
  const end = src.indexOf('\n  const ', start + 1);
  return src.slice(start, end === -1 ? src.length : end);
}

/** Every argument passed to `setError(...)`, paren- and quote-balanced. */
function setErrorArgs(slice: string): string[] {
  const args: string[] = [];
  const needle = 'setError(';
  let idx = slice.indexOf(needle);
  while (idx !== -1) {
    let i = idx + needle.length;
    const start = i;
    let depth = 1;
    let quote: string | null = null;
    while (i < slice.length && depth > 0) {
      const c = slice[i];
      if (quote) {
        if (c === '\\') {
          i += 2;
          continue;
        }
        if (c === quote) quote = null;
        i += 1;
        continue;
      }
      if (c === '"' || c === "'" || c === '`') {
        quote = c;
        i += 1;
        continue;
      }
      if (c === '(') depth += 1;
      else if (c === ')') depth -= 1;
      i += 1;
    }
    args.push(slice.slice(start, i - 1).trim());
    idx = slice.indexOf(needle, i);
  }
  return args;
}

const SCREENS: { file: string; handlers: string[] }[] = [
  { file: 'LoginScreen', handlers: ['handleGoogleSignIn', 'handleAppleSignIn'] },
  { file: 'RegisterScreen', handlers: ['handleGoogleSignIn', 'handleAppleSignIn'] },
];

describe('source fence — the social banner is fed only by t() (P-A8)', () => {
  for (const { file, handlers } of SCREENS) {
    const src = stripComments(
      fs.readFileSync(path.resolve(__dirname, `../src/screens/${file}.tsx`), 'utf8'),
    );

    for (const handler of handlers) {
      const slice = sliceHandler(src, handler);

      it(`${file}.${handler} passes setError only t(...) or the '' reset`, () => {
        const args = setErrorArgs(slice);
        // Positive control: the calls the fence inspects exist. The handler
        // clears the banner on entry, sets it on the failure branch, and sets
        // it in the catch — three calls. A refactor that changes the shape
        // must revisit this fence rather than silently escape it.
        expect(args.length).toBe(3);
        expect(args[0]).toBe("''");
        for (const arg of args.slice(1)) {
          expect(arg.startsWith('t(')).toBe(true);
          // `result.errorKey` is the SANCTIONED channel; `result.error` is not.
          expect(arg).not.toMatch(/result\.error(?!Key)/);
          expect(arg).not.toMatch(/parseApiError/);
          // No raw sentence: the only quoted things allowed are i18n keys.
          const literals = arg.match(/'[^']*'/g) || [];
          for (const literal of literals) {
            expect(literal).toMatch(/^'auth\.[A-Za-z.]+'$/);
          }
        }
      });

      it(`${file}.${handler} still consults result.error for control flow + diagnostics`, () => {
        // Positive control the other way: `result.error` is still READ (the
        // cancellation sentinel and the __DEV__ log), so the assertion above
        // is about routing, not about the field having vanished.
        expect(slice).toMatch(/result\.error/);
      });
    }

    it(`${file}: no banner write anywhere in the file sits on a social result.error`, () => {
      // File-wide sweep so the leak cannot simply be MOVED out of the two
      // slices above. RegisterScreen still has one `setError(result.error ||
      // ...)` in the EMAIL register path — a different service (`register`,
      // whose `error` is the backend's own envelope message, not a
      // [B4-DIAG] capture) and outside this finding — so the assertion is
      // positional: whatever still reads `result.error` must live OUTSIDE
      // handleGoogleSignIn / handleAppleSignIn.
      const allArgs = setErrorArgs(src);
      expect(allArgs.length).toBeGreaterThan(3); // positive control
      const socialSource = handlers.map((h) => sliceHandler(src, h)).join('\n');
      for (const arg of allArgs.filter((a) => /result\.error(?!Key)/.test(a))) {
        expect(socialSource).not.toContain(arg);
      }
    });
  }
});

// ---------------------------------------------------------------------------
// Fence 3 — COPY. The sentence the banner now always shows must be clean in
// both locales; before P-A8 it was effectively dead code.
// ---------------------------------------------------------------------------
describe('copy policy — the social fallback sentences (P-A8)', () => {
  const policy = JSON.parse(
    fs.readFileSync(path.resolve(__dirname, '../src/i18n/.copy-policy.json'), 'utf8'),
  ) as { scary_vocab_en: string[]; scary_vocab_ar: string[] };

  const KEYS = ['auth.googleFailed', 'auth.appleFailed'];

  it.each(KEYS)('%s exists in both catalogs', (key) => {
    expect(typeof EN[key]).toBe('string');
    expect(typeof AR[key]).toBe('string');
    expect(EN[key].length).toBeGreaterThan(0);
    expect(AR[key].length).toBeGreaterThan(0);
  });

  it.each(KEYS)('%s carries no scary vocabulary in EN', (key) => {
    for (const banned of policy.scary_vocab_en) {
      expect(EN[key].toLowerCase()).not.toContain(banned.toLowerCase());
    }
    // Stricter than the shared list, which only bans "Failed to": the bare
    // token is forbidden in user-facing copy too (see errorCopy.ts).
    expect(EN[key].toLowerCase()).not.toContain('failed');
  });

  it.each(KEYS)('%s carries no scary vocabulary in AR', (key) => {
    for (const banned of policy.scary_vocab_ar) {
      expect(AR[key]).not.toContain(banned);
    }
  });

  it.each(KEYS)('%s is not an untranslated echo of the English', (key) => {
    expect(AR[key]).not.toBe(EN[key]);
  });
});
