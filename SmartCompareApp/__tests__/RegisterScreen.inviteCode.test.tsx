/**
 * RegisterScreen invite code field — Bundle A Task 4.8
 *
 * Contract (Bundle A design §1.5 + plan Task 2.3):
 * - typed code validates QR-[A-HJ-NP-Z2-9]{6} on submit
 * - invalid format blocks submit and shows inline error
 * - route.params.code (from deep link) pre-fills + LOCKS the field
 * - clear icon (×) unlocks the field and clears the value
 * - valid code is forwarded to authService.register as { inviteCode }
 *
 * NOTE: A pre-existing test file `RegisterScreen.inviteId.test.tsx`
 * covers the F3.5 invite_id forwarding contract. This file is the new
 * coverage for the Bundle A invite_code path — kept separate so the
 * two contracts (auto-link UUID vs typed code) remain independent.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

jest.mock('react-native-reanimated', () => {
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
jest.mock('../src/services/authService', () => ({
  register: (...args: any[]) => mockRegister(...args),
  signInWithGoogle: jest.fn().mockResolvedValue({ success: false }),
  signInWithApple: jest.fn().mockResolvedValue({ success: false }),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(false),
}));

jest.mock('../src/services/api', () => ({
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

const RegisterScreen = require('../src/screens/RegisterScreen').default;

const mockNavigation: any = {
  navigate: jest.fn(),
  goBack: jest.fn(),
};
const onRegisterSuccess = jest.fn();

function renderScreen(routeParams: any = undefined) {
  return render(
    <RegisterScreen
      navigation={mockNavigation}
      route={{ params: routeParams }}
      onRegisterSuccess={onRegisterSuccess}
    />,
  );
}

function fillRequired(getByPlaceholderText: any) {
  fireEvent.changeText(getByPlaceholderText('auth.email'), 'user@example.com');
  fireEvent.changeText(getByPlaceholderText('auth.password'), 'StrongPass1!');
  fireEvent.changeText(getByPlaceholderText('auth.confirmPassword'), 'StrongPass1!');
}

describe('RegisterScreen — invite code field (Bundle A 4.8)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRegister.mockResolvedValue({ success: true, user: { id: 'u1' } });
  });

  it('forwards a valid typed invite code in the register call', async () => {
    const { getByPlaceholderText, getByText } = renderScreen(undefined);
    fillRequired(getByPlaceholderText);
    fireEvent.changeText(
      getByPlaceholderText('register.inviteCode.placeholder'),
      'QR-ABCD23',
    );
    fireEvent.press(getByText('auth.register'));

    await waitFor(() => expect(mockRegister).toHaveBeenCalled());
    expect(mockRegister).toHaveBeenCalledWith(
      'user@example.com',
      'StrongPass1!',
      expect.objectContaining({ inviteCode: 'QR-ABCD23' }),
    );
  });

  it('blocks submit and shows inline error when typed code has wrong shape', async () => {
    const { getByPlaceholderText, getByText, queryByText } = renderScreen(undefined);
    fillRequired(getByPlaceholderText);
    fireEvent.changeText(
      getByPlaceholderText('register.inviteCode.placeholder'),
      // Bundle B/C/D Task #36 — onChangeText now strips chars outside
      // the canonical alphabet `[A-HJ-NP-Z2-9]`, so wrong-shape inputs
      // need a body that *survives* the strip yet still fails the regex.
      // "BAD" survives (all canonical), but is only 3 chars — regex needs
      // exactly 6 after the dash.
      'QR-BAD',
    );
    fireEvent.press(getByText('auth.register'));

    await waitFor(() => {
      expect(queryByText('register.inviteCode.invalid')).toBeTruthy();
    });
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it('omits inviteCode entirely when field is empty', async () => {
    const { getByPlaceholderText, getByText } = renderScreen(undefined);
    fillRequired(getByPlaceholderText);
    fireEvent.press(getByText('auth.register'));

    await waitFor(() => expect(mockRegister).toHaveBeenCalled());
    const callArgs = mockRegister.mock.calls[0];
    // Third arg is the options object; inviteCode key may be absent or
    // present-but-undefined depending on conditional-spread choice.
    expect(callArgs[2].inviteCode).toBeUndefined();
  });

  it('pre-fills + locks the field when route.params.code is set (deep link)', async () => {
    const { getByPlaceholderText } = renderScreen({ code: 'QR-DEEP23' });
    const field = getByPlaceholderText('register.inviteCode.placeholder');
    expect(field.props.value).toBe('QR-DEEP23');
    expect(field.props.editable).toBe(false);
  });

  it('clear icon (×) unlocks the field and clears the value', async () => {
    const { getByPlaceholderText, getByLabelText } = renderScreen({
      code: 'QR-DEEP23',
    });
    const clearBtn = getByLabelText('register.inviteCode.clear');
    fireEvent.press(clearBtn);

    const field = getByPlaceholderText('register.inviteCode.placeholder');
    expect(field.props.value).toBe('');
    expect(field.props.editable).toBe(true);
  });

  it('uppercases and strips invalid chars as the user types', async () => {
    const { getByPlaceholderText } = renderScreen(undefined);
    const field = getByPlaceholderText('register.inviteCode.placeholder');
    // Lowercase + a stray symbol get normalized to "QR-AB23" (upper + filtered)
    fireEvent.changeText(field, 'qr-ab*23');
    expect(field.props.value).toBe('QR-AB23');
  });
});
