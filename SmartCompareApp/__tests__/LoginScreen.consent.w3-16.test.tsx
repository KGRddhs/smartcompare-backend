/**
 * W3-16 — consent capture on LoginScreen (spec §5-A.6, §5-A.7).
 *
 * LoginScreen's Google / Apple buttons CREATE an account on a first social
 * sign-in (auth_service.sign_in_with_social inserts the users row iff none
 * exists), so they are gated by the same consent checkbox as Register.
 * Email/password Sign in is NOT gated — it never creates an account.
 *
 * Harness = AuthScreens.socialDiagnostic.pa8.test.tsx Login block
 * (`login-social-google` / `login-social-apple` testIDs; Platform.OS is
 * 'ios' in the RN mock and isAppleSignInAvailable resolves true).
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { TERMS_VERSION } from '../src/services/consent';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: jest.fn(),
}));

const mockLogin = jest.fn();
const mockSignInWithGoogle = jest.fn();
const mockSignInWithApple = jest.fn();
jest.mock('../src/services/authService', () => ({
  login: (...args: any[]) => mockLogin(...args),
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

const parentNavigate = jest.fn();
const navigation: any = {
  navigate: jest.fn(),
  goBack: jest.fn(),
  canGoBack: () => false,
  getParent: () => ({ navigate: parentNavigate }),
};

const EXPECTED_CONSENT = {
  terms_accepted: true,
  terms_version: TERMS_VERSION,
  age_attested: true,
};

// The error must SAY something: an empty consent-error Text would block the
// user with no explanation (fixer addition — the testID alone survived the
// copy being deleted).
function expectConsentErrorCopy(screen: any) {
  expect(screen.getByTestId('consent-error').props.children).toBe('auth.consent.required');
}

function renderLogin(onLoginSuccess: jest.Mock = jest.fn()) {
  return render(<LoginScreen navigation={navigation} onLoginSuccess={onLoginSuccess} />);
}

describe('W3-16 LoginScreen — social sign-in is consent-gated', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignInWithGoogle.mockResolvedValue({ success: false, error: 'Sign-in cancelled' });
    mockSignInWithApple.mockResolvedValue({ success: false, error: 'Sign-in cancelled' });
    mockLogin.mockResolvedValue({ success: true });
  });

  // §5-A.6 — Google, unticked
  it('6a. an UNTICKED Google tap is blocked: signInWithGoogle() is not called and consent-error renders', async () => {
    const screen = renderLogin();

    fireEvent.press(screen.getByTestId('login-social-google'));

    expect(mockSignInWithGoogle).not.toHaveBeenCalled();
    await waitFor(() => expectConsentErrorCopy(screen));
  });

  // §5-A.6 — Google, ticked
  it('6b. a TICKED Google tap passes the consent payload to signInWithGoogle()', async () => {
    const screen = renderLogin();

    fireEvent.press(screen.getByTestId('consent-checkbox'));
    fireEvent.press(screen.getByTestId('login-social-google'));

    await waitFor(() => expect(mockSignInWithGoogle).toHaveBeenCalledTimes(1));
    expect(mockSignInWithGoogle.mock.calls[0]).toEqual([EXPECTED_CONSENT]);
  });

  // §5-A.6 — Apple, unticked
  it('6c. an UNTICKED Apple tap is blocked: signInWithApple() is not called and consent-error renders', async () => {
    const screen = renderLogin();
    await waitFor(() => expect(screen.getByTestId('login-social-apple')).toBeTruthy());

    fireEvent.press(screen.getByTestId('login-social-apple'));

    expect(mockSignInWithApple).not.toHaveBeenCalled();
    await waitFor(() => expectConsentErrorCopy(screen));
  });

  // §5-A.6 — Apple, ticked
  it('6d. a TICKED Apple tap passes the consent payload to signInWithApple()', async () => {
    const screen = renderLogin();
    await waitFor(() => expect(screen.getByTestId('login-social-apple')).toBeTruthy());

    fireEvent.press(screen.getByTestId('consent-checkbox'));
    fireEvent.press(screen.getByTestId('login-social-apple'));

    await waitFor(() => expect(mockSignInWithApple).toHaveBeenCalledTimes(1));
    expect(mockSignInWithApple.mock.calls[0]).toEqual([EXPECTED_CONSENT]);
  });

  // ADDED in green (Fable red-gate ruling 2) — mirror of Register's R1: the
  // Login consent row's Terms / Privacy spans reach the ROOT Legal route
  // through getParent(); the AuthStack itself has no `Legal`.
  it('6e. renders an UNCHECKED consent checkbox whose Terms / Privacy spans open the root Legal route', () => {
    const screen = renderLogin();

    expect(screen.getByRole('checkbox', { checked: false })).toBeTruthy();

    fireEvent.press(screen.getByText('common.terms'));
    expect(parentNavigate).toHaveBeenCalledWith('Legal', { doc: 'terms' });

    fireEvent.press(screen.getByText('common.privacy'));
    expect(parentNavigate).toHaveBeenCalledWith('Legal', { doc: 'privacy' });
    expect(parentNavigate).toHaveBeenCalledTimes(2);

    expect(navigation.navigate).not.toHaveBeenCalledWith('Legal', expect.anything());
  });

  // Fixer additions (adversary review): ticking the box after a blocked tap
  // must CLEAR the red error, and the box must be locked while an
  // account-creating request is in flight.
  it('6f. ticking the box after a blocked tap clears consent-error', async () => {
    const screen = renderLogin();

    fireEvent.press(screen.getByTestId('login-social-google'));
    await waitFor(() => expectConsentErrorCopy(screen));

    fireEvent.press(screen.getByTestId('consent-checkbox'));

    expect(screen.getByRole('checkbox', { checked: true })).toBeTruthy();
    expect(screen.queryByTestId('consent-error')).toBeNull();
  });

  it('6g. the checkbox is disabled while a Google sign-in is in flight', async () => {
    mockSignInWithGoogle.mockReturnValue(new Promise(() => {}));
    const screen = renderLogin();

    expect(screen.getByTestId('consent-checkbox').props.disabled).toBe(false);

    fireEvent.press(screen.getByTestId('consent-checkbox'));
    fireEvent.press(screen.getByTestId('login-social-google'));

    await waitFor(() => expect(mockSignInWithGoogle).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(screen.getByTestId('consent-checkbox').props.disabled).toBe(true),
    );
  });

  // §5-A.7 — PRESERVE PIN (green today and after): email/password Sign in
  // never creates an account, so it must never wait on the checkbox.
  // Mutation that must redden it: gate handleLogin on the box.
  it('7. email/password Sign in is NOT gated — login() runs with the box left unticked', async () => {
    const onLoginSuccess = jest.fn();
    const screen = renderLogin(onLoginSuccess);

    // Whatever consent control exists is left untouched (unticked).
    expect(screen.queryAllByRole('checkbox', { checked: true })).toHaveLength(0);

    fireEvent.changeText(screen.getByTestId('login-email-input'), 'user@example.com');
    fireEvent.changeText(screen.getByTestId('login-password-input'), 'StrongPass1!');
    fireEvent.press(screen.getByTestId('login-submit'));

    await waitFor(() => expect(mockLogin).toHaveBeenCalledTimes(1));
    expect(mockLogin).toHaveBeenCalledWith('user@example.com', 'StrongPass1!');
    await waitFor(() => expect(onLoginSuccess).toHaveBeenCalledTimes(1));
    expect(screen.queryByTestId('consent-error')).toBeNull();
  });
});
