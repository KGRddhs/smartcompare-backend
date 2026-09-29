/**
 * S69 U6 T1 — Sign in with Apple renders the SDK's native button (LL-10).
 *
 * Spec: docs/investigations/2026-09-29-session-69-state/U6_SIGNIN_FIRST_RUN_SPEC.md
 * R1 + ruling R-A (the SDK's native view, never a custom-drawn logo), with the
 * spec-review corrections 2-6 and open question G:
 *   - Login: AppleAuthenticationButton, buttonType CONTINUE, buttonStyle
 *     BLACK, cornerRadius = radii.button (12), height >= 44, and it KEEPS the
 *     `login-social-apple` testID (three existing suites press it by id).
 *   - Register: AppleAuthenticationButton, buttonType SIGN_UP (or CONTINUE),
 *     BLACK, cornerRadius 12, height >= 44.
 *   - The W3-16 consent gate stays in front of onPress on both screens.
 *   - The native button has no disabled prop, so a press while any sign-in
 *     is in flight must be a no-op (review correction 4).
 *   - Android keeps today's behaviour: no Apple control at all.
 *   - The empty Apple glyph (`<Text style={socialStyles.glyphApple}></Text>`)
 *     and its "native build" comment go away (Login + onboarding Step 16).
 *
 * expo-apple-authentication is mocked here with the REAL enum values
 * (AppleAuthentication.types.d.ts:232-262: SIGN_IN=0, CONTINUE=1, SIGN_UP=2;
 * WHITE=0, WHITE_OUTLINE=1, BLACK=2). The native element is found by its
 * component TYPE, so a hand-drawn look-alike carrying the same testID cannot
 * satisfy these tests.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { TERMS_VERSION } from '../../src/services/consent';

jest.mock('expo-apple-authentication', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactReq = require('react');
  const AppleAuthenticationButton = (props: any) =>
    ReactReq.createElement('AppleAuthenticationButton', props);
  return {
    __esModule: true,
    AppleAuthenticationButton,
    AppleAuthenticationButtonType: { SIGN_IN: 0, CONTINUE: 1, SIGN_UP: 2 },
    AppleAuthenticationButtonStyle: { WHITE: 0, WHITE_OUTLINE: 1, BLACK: 2 },
    AppleAuthenticationScope: { FULL_NAME: 0, EMAIL: 1 },
    isAvailableAsync: jest.fn().mockResolvedValue(true),
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

const mockLogin = jest.fn();
const mockRegister = jest.fn();
const mockSignInWithGoogle = jest.fn();
const mockSignInWithApple = jest.fn();
jest.mock('../../src/services/authService', () => ({
  login: (...args: any[]) => mockLogin(...args),
  register: (...args: any[]) => mockRegister(...args),
  requestPasswordReset: jest.fn(),
  signInWithGoogle: (...args: any[]) => mockSignInWithGoogle(...args),
  signInWithApple: (...args: any[]) => mockSignInWithApple(...args),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(true),
}));

jest.mock('../../src/services/api', () => ({
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const AppleAuth = require('expo-apple-authentication');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const RN = require('react-native');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const LoginScreen = require('../../src/screens/LoginScreen').default;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const RegisterScreen = require('../../src/screens/RegisterScreen').default;

const NativeAppleButton = AppleAuth.AppleAuthenticationButton;
const BUTTON_TYPE = AppleAuth.AppleAuthenticationButtonType;
const BUTTON_STYLE = AppleAuth.AppleAuthenticationButtonStyle;

const EXPECTED_CONSENT = {
  terms_accepted: true,
  terms_version: TERMS_VERSION,
  age_attested: true,
};

const SRC = path.resolve(__dirname, '../../src');

function makeNavigation(): any {
  return {
    navigate: jest.fn(),
    goBack: jest.fn(),
    canGoBack: () => false,
    getParent: () => ({ navigate: jest.fn() }),
  };
}

function renderLogin() {
  return render(<LoginScreen navigation={makeNavigation()} onLoginSuccess={jest.fn()} />);
}

function renderRegister() {
  return render(
    <RegisterScreen
      navigation={makeNavigation()}
      route={{ params: undefined }}
      onRegisterSuccess={jest.fn()}
    />,
  );
}

/** Every rendered instance of the SDK's native button, by component TYPE. */
function nativeButtons(screen: any): any[] {
  return screen.UNSAFE_queryAllByType(NativeAppleButton);
}

async function findNativeButton(screen: any): Promise<any> {
  await waitFor(() => expect(nativeButtons(screen)).toHaveLength(1));
  return nativeButtons(screen)[0];
}

/** Height of a (possibly nested / array) RN style, minHeight as fallback. */
function styleHeight(style: any): number {
  const flat = Object.assign(
    {},
    ...([] as any[]).concat(style ?? []).flat(Infinity).filter(Boolean),
  );
  return Number(flat.height ?? flat.minHeight ?? 0);
}

async function flushEffects() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

async function pressAllNative(screen: any) {
  for (const b of nativeButtons(screen)) {
    await act(async () => {
      b.props.onPress();
    });
  }
}

describe('S69 U6 T1 \u2014 Sign in with Apple uses the native AppleAuthenticationButton', () => {
  const originalOS = RN.Platform.OS;

  beforeEach(() => {
    jest.clearAllMocks();
    RN.Platform.OS = 'ios';
    mockLogin.mockResolvedValue({ success: true });
    mockRegister.mockResolvedValue({ success: true, user: { id: 'u1' } });
    mockSignInWithGoogle.mockResolvedValue({ success: false, error: 'Sign-in cancelled' });
    mockSignInWithApple.mockResolvedValue({ success: false, error: 'Sign-in cancelled' });
  });

  afterAll(() => {
    RN.Platform.OS = originalOS;
  });

  describe('LoginScreen', () => {
    it('T1.1 renders AppleAuthenticationButton (CONTINUE, BLACK, cornerRadius 12, height >= 44) carrying the login-social-apple testID', async () => {
      const screen = renderLogin();
      const btn = await findNativeButton(screen);

      expect(btn.props.buttonType).toBe(BUTTON_TYPE.CONTINUE);
      expect(btn.props.buttonStyle).toBe(BUTTON_STYLE.BLACK);
      expect(btn.props.cornerRadius).toBe(12);
      expect(styleHeight(btn.props.style)).toBeGreaterThanOrEqual(44);
      // The three existing suites press the Apple control by this id.
      expect(btn.props.testID).toBe('login-social-apple');
      // No second, hand-drawn Apple row next to the native one.
      expect(screen.queryByText('auth.appleSignIn')).toBeNull();
    });

    it('T1.2 the native button is consent-gated: unticked -> blocked + consent-error; ticked -> signInWithApple(consent)', async () => {
      const screen = renderLogin();
      const btn = await findNativeButton(screen);

      await act(async () => {
        btn.props.onPress();
      });
      expect(mockSignInWithApple).not.toHaveBeenCalled();
      await waitFor(() =>
        expect(screen.getByTestId('consent-error').props.children).toBe('auth.consent.required'),
      );

      fireEvent.press(screen.getByTestId('consent-checkbox'));
      await act(async () => {
        nativeButtons(screen)[0].props.onPress();
      });
      await waitFor(() => expect(mockSignInWithApple).toHaveBeenCalledTimes(1));
      expect(mockSignInWithApple.mock.calls[0]).toEqual([EXPECTED_CONSENT]);
    });

    it('T1.3 a native-button press while a Google sign-in is in flight is a no-op (the SDK view has no disabled prop)', async () => {
      mockSignInWithGoogle.mockReturnValue(new Promise(() => {}));
      const screen = renderLogin();
      await findNativeButton(screen);
      fireEvent.press(screen.getByTestId('consent-checkbox'));

      fireEvent.press(screen.getByTestId('login-social-google'));
      await waitFor(() => expect(mockSignInWithGoogle).toHaveBeenCalledTimes(1));
      await pressAllNative(screen);
      expect(mockSignInWithApple).not.toHaveBeenCalled();
    });

    it('T1.4 a second Apple press while the first is in flight does not start a second sign-in', async () => {
      mockSignInWithApple.mockReturnValue(new Promise(() => {}));
      const screen = renderLogin();
      await findNativeButton(screen);
      fireEvent.press(screen.getByTestId('consent-checkbox'));

      await act(async () => {
        nativeButtons(screen)[0].props.onPress();
      });
      await waitFor(() => expect(mockSignInWithApple).toHaveBeenCalledTimes(1));
      // Press again through whatever Apple control is on screen now (the
      // re-rendered handler sees the in-flight state).
      await pressAllNative(screen);
      expect(mockSignInWithApple).toHaveBeenCalledTimes(1);
    });

    it('T1.5 platform gating: iOS renders exactly one native Apple button; Android renders no Apple control at all', async () => {
      const ios = renderLogin();
      await findNativeButton(ios);
      ios.unmount();

      RN.Platform.OS = 'android';
      const android = renderLogin();
      await flushEffects();
      expect(nativeButtons(android)).toHaveLength(0);
      expect(android.queryByTestId('login-social-apple')).toBeNull();
      expect(android.queryByText('auth.appleSignIn')).toBeNull();
    });
  });

  describe('RegisterScreen', () => {
    it('T1.6 renders AppleAuthenticationButton (SIGN_UP or CONTINUE, BLACK, cornerRadius 12, height >= 44) and no text-only Apple row', async () => {
      const screen = renderRegister();
      const btn = await findNativeButton(screen);

      expect([BUTTON_TYPE.SIGN_UP, BUTTON_TYPE.CONTINUE]).toContain(btn.props.buttonType);
      expect(btn.props.buttonStyle).toBe(BUTTON_STYLE.BLACK);
      expect(btn.props.cornerRadius).toBe(12);
      expect(styleHeight(btn.props.style)).toBeGreaterThanOrEqual(44);
      expect(screen.queryByText('auth.appleSignIn')).toBeNull();
    });

    it('T1.7 the native button is consent-gated: unticked -> blocked + consent-error; ticked -> signInWithApple(consent)', async () => {
      const screen = renderRegister();
      const btn = await findNativeButton(screen);

      await act(async () => {
        btn.props.onPress();
      });
      expect(mockSignInWithApple).not.toHaveBeenCalled();
      await waitFor(() =>
        expect(screen.getByTestId('consent-error').props.children).toBe('auth.consent.required'),
      );

      fireEvent.press(screen.getByTestId('consent-checkbox'));
      await act(async () => {
        nativeButtons(screen)[0].props.onPress();
      });
      await waitFor(() => expect(mockSignInWithApple).toHaveBeenCalledTimes(1));
      expect(mockSignInWithApple.mock.calls[0]).toEqual([EXPECTED_CONSENT]);
    });

    it('T1.8 a native-button press while a Google sign-in is in flight is a no-op', async () => {
      mockSignInWithGoogle.mockReturnValue(new Promise(() => {}));
      const screen = renderRegister();
      await findNativeButton(screen);
      fireEvent.press(screen.getByTestId('consent-checkbox'));

      fireEvent.press(screen.getByText('auth.googleSignIn'));
      await waitFor(() => expect(mockSignInWithGoogle).toHaveBeenCalledTimes(1));
      await pressAllNative(screen);
      expect(mockSignInWithApple).not.toHaveBeenCalled();
    });

    it('T1.9 platform gating: iOS renders exactly one native Apple button; Android renders none', async () => {
      const ios = renderRegister();
      await findNativeButton(ios);
      ios.unmount();

      RN.Platform.OS = 'android';
      const android = renderRegister();
      await flushEffects();
      expect(nativeButtons(android)).toHaveLength(0);
      expect(android.queryByText('auth.appleSignIn')).toBeNull();
    });
  });

  describe('the empty Apple glyph is gone', () => {
    it.each([
      ['LoginScreen.tsx', 'screens/LoginScreen.tsx'],
      ['Step16Account.tsx', 'screens/onboarding/Step16Account.tsx'],
    ])('T1.10 %s has no empty glyphApple <Text> and no "native build" glyph-swap comment', (_n, rel) => {
      const src = fs.readFileSync(path.join(SRC, rel), 'utf8');
      // The empty Text renders nothing (no U+F8FF): the HIG-required logo is
      // only ever drawn by the SDK's native button.
      expect(src).not.toMatch(/<Text[^>]*glyphApple[^>]*>\s*<\/Text>/);
      expect(src).not.toMatch(/happens during native build/);
    });
  });
});
