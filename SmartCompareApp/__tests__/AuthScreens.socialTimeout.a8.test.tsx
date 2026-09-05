/**
 * A8 — a social sign-in deadline renders LOCALIZED, retryable copy on both
 * auth screens, never a raw service string.
 *
 * `authService` cannot call `t` (it is not a component and imports no i18n),
 * so a timeout crosses the boundary as an i18n KEY on `AuthResponse.errorKey`
 * — the A11 rule applied to auth: copy comes from a named outcome, never from
 * whatever string the service happened to build. The screens must PREFER that
 * key. If they fall through to `result.error || <fallback>` instead, an
 * Arabic user gets the English fallback ("Google sign-in failed" /
 * "Apple sign-in failed") — which also carries the forbidden token "failed".
 *
 * `t` here resolves through the REAL en.json, so these assertions are on the
 * sentence a user actually sees, not on a key echo.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import enCatalog from '../src/i18n/en.json';

const EN = enCatalog as Record<string, string>;
const TIMEOUT_COPY = EN['auth.signInTimeout'];

jest.mock('react-i18next', () => {
  const catalog = require('../src/i18n/en.json') as Record<string, string>;
  return {
    useTranslation: () => ({
      t: (key: string, opts?: { defaultValue?: string }) =>
        catalog[key] ?? opts?.defaultValue ?? key,
      i18n: { language: 'en', changeLanguage: jest.fn() },
    }),
  };
});

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

const TIMEOUT_RESULT = { success: false, errorKey: 'auth.signInTimeout' };

beforeEach(() => {
  jest.clearAllMocks();
});

describe('LoginScreen — social deadline copy (A8)', () => {
  it('renders the localized timeout sentence when Google sign-in times out', async () => {
    mockSignInWithGoogle.mockResolvedValueOnce(TIMEOUT_RESULT);

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    fireEvent.press(screen.getByTestId('login-social-google'));

    await waitFor(() => expect(screen.getByTestId('login-error')).toBeTruthy());
    expect(screen.getByText(TIMEOUT_COPY)).toBeTruthy();
    // The English fallback must NOT be what shipped.
    expect(screen.queryByText(EN['auth.googleFailed'])).toBeNull();
  });

  it('renders the localized timeout sentence when Apple sign-in times out', async () => {
    mockSignInWithApple.mockResolvedValueOnce(TIMEOUT_RESULT);

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    await waitFor(() => expect(screen.getByTestId('login-social-apple')).toBeTruthy());
    fireEvent.press(screen.getByTestId('login-social-apple'));

    await waitFor(() => expect(screen.getByText(TIMEOUT_COPY)).toBeTruthy());
    expect(screen.queryByText(EN['auth.appleFailed'])).toBeNull();
  });

  it('still shows the catalog fallback when the service sends no errorKey', async () => {
    // No-regression: the pre-A8 branch is untouched for every other outcome.
    mockSignInWithGoogle.mockResolvedValueOnce({ success: false });

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    fireEvent.press(screen.getByTestId('login-social-google'));

    await waitFor(() => expect(screen.getByText(EN['auth.googleFailed'])).toBeTruthy());
  });

  it('releases the screen after a timeout (buttons are pressable again)', async () => {
    // The filed defect was an INERT screen: `disabled = loading ||
    // Boolean(socialLoading)` gated every control while the fetch hung. A
    // settled outcome must clear socialLoading via the handler's `finally`.
    mockSignInWithGoogle.mockResolvedValueOnce(TIMEOUT_RESULT);

    const screen = render(<LoginScreen navigation={navigation} onLoginSuccess={jest.fn()} />);
    fireEvent.press(screen.getByTestId('login-social-google'));
    await waitFor(() => expect(screen.getByText(TIMEOUT_COPY)).toBeTruthy());

    mockSignInWithGoogle.mockResolvedValueOnce({ success: true });
    fireEvent.press(screen.getByTestId('login-social-google'));
    await waitFor(() => expect(mockSignInWithGoogle).toHaveBeenCalledTimes(2));
  });
});

describe('RegisterScreen — social deadline copy (A8)', () => {
  function renderRegister() {
    return render(
      <RegisterScreen
        navigation={navigation}
        route={{ params: undefined }}
        onRegisterSuccess={jest.fn()}
      />
    );
  }

  it('renders the localized timeout sentence when Google sign-in times out', async () => {
    mockSignInWithGoogle.mockResolvedValueOnce(TIMEOUT_RESULT);

    const screen = renderRegister();
    fireEvent.press(screen.getByText(EN['auth.googleSignIn']));

    await waitFor(() => expect(screen.getByText(TIMEOUT_COPY)).toBeTruthy());
    expect(screen.queryByText('Google sign-in failed')).toBeNull();
  });

  it('still shows the hardcoded fallback when the service sends no errorKey', async () => {
    mockSignInWithGoogle.mockResolvedValueOnce({ success: false });

    const screen = renderRegister();
    fireEvent.press(screen.getByText(EN['auth.googleSignIn']));

    await waitFor(() => expect(screen.getByText('Google sign-in failed')).toBeTruthy());
  });
});
