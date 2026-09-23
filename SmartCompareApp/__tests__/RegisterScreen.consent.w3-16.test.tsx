/**
 * W3-16 — consent capture on RegisterScreen (spec §5-A.1..5).
 *
 * Contract:
 *  - One explicit control (`testID="consent-checkbox"`, role checkbox,
 *    unchecked by default) — ticking it is the ToS acceptance AND the 13+
 *    attestation.
 *  - Its Terms / Privacy spans open the ROOT-level `Legal` route through
 *    `navigation.getParent()?.navigate('Legal', { doc })` (Register lives in
 *    the nested AuthStack, whose param list has no `Legal`).
 *  - Create Account, Google and Apple are ALL gated: unticked -> the service
 *    is not called and `testID="consent-error"` renders; ticked -> the
 *    service receives the consent payload.
 *
 * Harness = RegisterScreen.inviteCode.test.tsx mock set. The RN mock's
 * Platform.OS is 'ios' (__mocks__/react-native.ts:70) and
 * isAppleSignInAvailable resolves true, so the Apple leg renders — no skip.
 *
 * Queries are by testID for the new control (ruling 11: the clipboard
 * consent banner's strings live on the same screen), and by the i18n KEY
 * for the Terms / Privacy spans (the mocked t() is the identity).
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { TERMS_VERSION } from '../src/services/consent';

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
  }),
}));

jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: jest.fn(),
}));

const mockRegister = jest.fn();
const mockSignInWithGoogle = jest.fn();
const mockSignInWithApple = jest.fn();
jest.mock('../src/services/authService', () => ({
  register: (...args: any[]) => mockRegister(...args),
  signInWithGoogle: (...args: any[]) => mockSignInWithGoogle(...args),
  signInWithApple: (...args: any[]) => mockSignInWithApple(...args),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(true),
}));

jest.mock('../src/services/api', () => ({
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const RegisterScreen = require('../src/screens/RegisterScreen').default;

const parentNavigate = jest.fn();
const mockNavigation: any = {
  navigate: jest.fn(),
  goBack: jest.fn(),
  canGoBack: () => false,
  getParent: () => ({ navigate: parentNavigate }),
};
const onRegisterSuccess = jest.fn();

const EXPECTED_CONSENT = {
  terms_accepted: true,
  terms_version: TERMS_VERSION,
  age_attested: true,
};

function renderScreen() {
  return render(
    <RegisterScreen
      navigation={mockNavigation}
      route={{ params: undefined }}
      onRegisterSuccess={onRegisterSuccess}
    />,
  );
}

// The error must SAY something: an empty consent-error Text would block the
// user with no explanation (fixer addition — the testID alone survived the
// copy being deleted).
function expectConsentErrorCopy(screen: any) {
  expect(screen.getByTestId('consent-error').props.children).toBe('auth.consent.required');
}

function fillRequired(getByPlaceholderText: any) {
  fireEvent.changeText(getByPlaceholderText('auth.email'), 'user@example.com');
  fireEvent.changeText(getByPlaceholderText('auth.password'), 'StrongPass1!');
  fireEvent.changeText(getByPlaceholderText('auth.confirmPassword'), 'StrongPass1!');
}

describe('W3-16 RegisterScreen — consent capture', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRegister.mockResolvedValue({ success: true, user: { id: 'u1' } });
    mockSignInWithGoogle.mockResolvedValue({ success: false, error: 'Sign-in cancelled' });
    mockSignInWithApple.mockResolvedValue({ success: false, error: 'Sign-in cancelled' });
  });

  // §5-A.1
  it('1. renders an UNCHECKED consent checkbox whose Terms / Privacy spans open the root Legal route', () => {
    const screen = renderScreen();

    expect(screen.getByRole('checkbox', { checked: false })).toBeTruthy();
    expect(screen.getByTestId('consent-checkbox')).toBeTruthy();

    fireEvent.press(screen.getByText('common.terms'));
    expect(parentNavigate).toHaveBeenCalledWith('Legal', { doc: 'terms' });

    fireEvent.press(screen.getByText('common.privacy'));
    expect(parentNavigate).toHaveBeenCalledWith('Legal', { doc: 'privacy' });

    // The route lives on the ROOT navigator; the AuthStack cannot resolve it.
    expect(mockNavigation.navigate).not.toHaveBeenCalledWith('Legal', expect.anything());
  });

  // §5-A.2
  it('2. an UNTICKED Create Account is blocked: register() is not called and consent-error renders', async () => {
    const screen = renderScreen();
    fillRequired(screen.getByPlaceholderText);

    fireEvent.press(screen.getByText('auth.register'));

    await waitFor(() => expectConsentErrorCopy(screen));
    expect(mockRegister).not.toHaveBeenCalled();
  });

  // §5-A.3
  it('3. a TICKED Create Account forwards the consent payload to register()', async () => {
    const screen = renderScreen();
    fillRequired(screen.getByPlaceholderText);

    fireEvent.press(screen.getByTestId('consent-checkbox'));
    fireEvent.press(screen.getByText('auth.register'));

    await waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1));
    expect(mockRegister).toHaveBeenCalledWith(
      'user@example.com',
      'StrongPass1!',
      expect.objectContaining({ consent: EXPECTED_CONSENT }),
    );
    expect(screen.queryByTestId('consent-error')).toBeNull();
  });

  // §5-A.4 (unticked half)
  it('4a. an UNTICKED Google tap is blocked: signInWithGoogle() is not called and consent-error renders', async () => {
    const screen = renderScreen();

    fireEvent.press(screen.getByText('auth.googleSignIn'));

    expect(mockSignInWithGoogle).not.toHaveBeenCalled();
    await waitFor(() => expectConsentErrorCopy(screen));
  });

  // §5-A.4 (ticked half)
  it('4b. a TICKED Google tap passes the consent payload to signInWithGoogle()', async () => {
    const screen = renderScreen();

    fireEvent.press(screen.getByTestId('consent-checkbox'));
    fireEvent.press(screen.getByText('auth.googleSignIn'));

    await waitFor(() => expect(mockSignInWithGoogle).toHaveBeenCalledTimes(1));
    expect(mockSignInWithGoogle.mock.calls[0]).toEqual([EXPECTED_CONSENT]);
  });

  // §5-A.5 (unticked half)
  it('5a. an UNTICKED Apple tap is blocked: signInWithApple() is not called and consent-error renders', async () => {
    const screen = renderScreen();
    await waitFor(() => expect(screen.getByText('auth.appleSignIn')).toBeTruthy());

    fireEvent.press(screen.getByText('auth.appleSignIn'));

    expect(mockSignInWithApple).not.toHaveBeenCalled();
    await waitFor(() => expectConsentErrorCopy(screen));
  });

  // §5-A.5 (ticked half)
  it('5b. a TICKED Apple tap passes the consent payload to signInWithApple()', async () => {
    const screen = renderScreen();
    await waitFor(() => expect(screen.getByText('auth.appleSignIn')).toBeTruthy());

    fireEvent.press(screen.getByTestId('consent-checkbox'));
    fireEvent.press(screen.getByText('auth.appleSignIn'));

    await waitFor(() => expect(mockSignInWithApple).toHaveBeenCalledTimes(1));
    expect(mockSignInWithApple.mock.calls[0]).toEqual([EXPECTED_CONSENT]);
  });

  // Fixer additions (adversary review): ticking the box after a blocked tap
  // must CLEAR the red error, and the box must be locked while an
  // account-creating request is in flight.
  it('8. ticking the box after a blocked tap clears consent-error', async () => {
    const screen = renderScreen();

    fireEvent.press(screen.getByText('auth.googleSignIn'));
    await waitFor(() => expectConsentErrorCopy(screen));

    fireEvent.press(screen.getByTestId('consent-checkbox'));

    expect(screen.getByRole('checkbox', { checked: true })).toBeTruthy();
    expect(screen.queryByTestId('consent-error')).toBeNull();
  });

  it('9. the checkbox is disabled while a Google sign-in is in flight', async () => {
    mockSignInWithGoogle.mockReturnValue(new Promise(() => {}));
    const screen = renderScreen();

    expect(screen.getByTestId('consent-checkbox').props.disabled).toBe(false);

    fireEvent.press(screen.getByTestId('consent-checkbox'));
    fireEvent.press(screen.getByText('auth.googleSignIn'));

    await waitFor(() => expect(mockSignInWithGoogle).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(screen.getByTestId('consent-checkbox').props.disabled).toBe(true),
    );
  });

  it('10. the checkbox is disabled while an EMAIL Create Account request is in flight', async () => {
    mockRegister.mockReturnValue(new Promise(() => {}));
    const screen = renderScreen();
    fillRequired(screen.getByPlaceholderText);

    expect(screen.getByTestId('consent-checkbox').props.disabled).toBe(false);

    fireEvent.press(screen.getByTestId('consent-checkbox'));
    fireEvent.press(screen.getByText('auth.register'));

    await waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(screen.getByTestId('consent-checkbox').props.disabled).toBe(true),
    );
  });
});
