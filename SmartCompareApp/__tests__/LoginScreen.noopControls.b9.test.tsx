/**
 * B9 — LoginScreen's two no-op controls.
 *
 * Before this fix the sign-in header shipped two controls that a user could
 * press and that did nothing at all:
 *
 *   1. The back chevron called `navigation.goBack()` unconditionally. On
 *      every organic launch Login is index 0 of both the root stack (App.tsx
 *      renders only "Auth" while signed out) and the auth stack
 *      (AuthNavigator lists Login first), and Register / ForgotPassword reach
 *      it via `navigate('Login')`, which pops instead of pushing — so there
 *      was never anything below it. The referral deep link (`r/:code` mounts
 *      Register alone, whose "Sign in" pushes Login) is the one path where a
 *      target exists, so the control is GATED, not deleted.
 *
 *   2. The "Email" social pill called `setSocialLoading('')`. The pill is
 *      only pressable while `socialLoading === ''`, so that was a same-value
 *      setState React bails out of — zero render, zero effect. Its own
 *      comment claimed a "focus hint"; there was no ref anywhere in the file.
 *
 * These assertions are on the OBSERVABLE outcome (is the control on screen /
 * did the field receive focus), never on the handler's internals.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: jest.fn(),
}));

jest.mock('../src/services/authService', () => ({
  login: jest.fn(),
  register: jest.fn(),
  requestPasswordReset: jest.fn(),
  signInWithGoogle: jest.fn(),
  signInWithApple: jest.fn(),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(false),
}));

jest.mock('../src/services/api', () => ({
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const LoginScreen = require('../src/screens/LoginScreen').default;

type Nav = {
  navigate: jest.Mock;
  goBack: jest.Mock;
  canGoBack?: jest.Mock;
};

const makeNav = (canGoBack?: boolean): Nav => ({
  navigate: jest.fn(),
  goBack: jest.fn(),
  ...(canGoBack === undefined ? {} : { canGoBack: jest.fn(() => canGoBack) }),
});

/**
 * react-test-renderer resolves a ref on a host element through
 * `createNodeMock`; without one `ref.current` is null in tests even though
 * the real TextInput exposes `focus()`. Injecting the mock is what makes the
 * imperative focus observable here.
 */
const nodeMockFor = (focus: jest.Mock) => (element: React.ReactElement) => {
  const props = element.props as { testID?: string } | undefined;
  if (props?.testID === 'login-email-input') return { focus };
  return null;
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('B9 — login back arrow is gated on having a target', () => {
  it('does not render the arrow when the stack has nothing to pop to', () => {
    const navigation = makeNav(false);
    const screen = render(
      <LoginScreen navigation={navigation as any} onLoginSuccess={jest.fn()} />
    );

    expect(screen.queryByTestId('login-back')).toBeNull();
    // The header keeps the arrow's box so the headline does not jump.
    expect(screen.getByTestId('login-back-spacer')).toBeTruthy();
    expect(navigation.canGoBack).toHaveBeenCalled();
  });

  it('renders the arrow and pops the stack when there IS a target', () => {
    const navigation = makeNav(true);
    const screen = render(
      <LoginScreen navigation={navigation as any} onLoginSuccess={jest.fn()} />
    );

    const back = screen.getByTestId('login-back');
    expect(screen.queryByTestId('login-back-spacer')).toBeNull();

    fireEvent.press(back);
    expect(navigation.goBack).toHaveBeenCalledTimes(1);
  });

  it('hides the arrow rather than throwing when canGoBack is absent', () => {
    const navigation = makeNav();
    const screen = render(
      <LoginScreen navigation={navigation as any} onLoginSuccess={jest.fn()} />
    );

    expect(screen.queryByTestId('login-back')).toBeNull();
    expect(screen.getByTestId('login-back-spacer')).toBeTruthy();
    expect(navigation.goBack).not.toHaveBeenCalled();
  });
});

describe('B9 — the "Email" social pill focuses the email field', () => {
  it('puts the cursor in the email input when pressed', () => {
    const focus = jest.fn();
    const screen = render(
      <LoginScreen navigation={makeNav(false) as any} onLoginSuccess={jest.fn()} />,
      { createNodeMock: nodeMockFor(focus) }
    );

    fireEvent.press(screen.getByTestId('login-social-email'));

    expect(focus).toHaveBeenCalledTimes(1);
  });

  it('leaves the other sign-in controls usable (no phantom loading latch)', () => {
    const focus = jest.fn();
    const navigation = makeNav(false);
    const screen = render(
      <LoginScreen navigation={navigation as any} onLoginSuccess={jest.fn()} />,
      { createNodeMock: nodeMockFor(focus) }
    );

    fireEvent.press(screen.getByTestId('login-social-email'));

    // Pressing the pill must not disable the rest of the screen, and the
    // password field must not be the one that took focus.
    expect(screen.getByTestId('login-submit').props.accessibilityState.disabled).toBe(
      false
    );
    fireEvent.press(screen.getByTestId('login-register-link'));
    expect(navigation.navigate).toHaveBeenCalledWith('Register');
  });
});
