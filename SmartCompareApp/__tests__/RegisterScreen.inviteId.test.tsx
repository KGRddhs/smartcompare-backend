/**
 * RegisterScreen invite_id capture (F3.5)
 *
 * Focused on the F3.5 contract: when the user reaches Register from the
 * InviteeQuiz soft-signup CTA, route.params.invite_id is forwarded to
 * authService.register so the backend can link redeemed_by_user_id.
 *
 * Doesn't try to test the entire registration flow (existing
 * AuthScreens.test.tsx is a separate concern, currently in the
 * pre-existing-failures bucket due to LoginScreen import side effects).
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

// LoginScreen / RegisterScreen import certificatePinning indirectly via
// authService — but since we mock authService completely the chain is cut.
// We import RegisterScreen *after* the mocks above so they bind first.
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
    />
  );
}

describe('RegisterScreen — invite_id forwarding (F3.5)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRegister.mockResolvedValue({ success: true, user: { id: 'u1' } });
  });

  it('forwards invite_id from route.params to authService.register', async () => {
    const { getByPlaceholderText, getByText } = renderScreen({
      invite_id: 'invite-uuid-1',
    });
    fireEvent.changeText(getByPlaceholderText('auth.email'), 'invitee@example.com');
    fireEvent.changeText(getByPlaceholderText('auth.password'), 'StrongPass1!');
    fireEvent.changeText(getByPlaceholderText('auth.confirmPassword'), 'StrongPass1!');
    // Button title — RNTL's fireEvent.press walks up to the TouchableOpacity ancestor.
    fireEvent.press(getByText('auth.register'));
    await waitFor(() => expect(mockRegister).toHaveBeenCalled());
    // Bundle A §1.5 — register() takes a RegisterOptions object so the new
    // inviteCode + (future) name fields can travel alongside inviteId. The
    // F3.5 contract (deep-link → invite_id forwarded) is preserved.
    expect(mockRegister).toHaveBeenCalledWith(
      'invitee@example.com',
      'StrongPass1!',
      expect.objectContaining({ inviteId: 'invite-uuid-1' }),
    );
  });

  it('omits invite_id (passes undefined inside options) when route.params is empty', async () => {
    const { getByPlaceholderText, getByText } = renderScreen(undefined);
    fireEvent.changeText(getByPlaceholderText('auth.email'), 'fresh@example.com');
    fireEvent.changeText(getByPlaceholderText('auth.password'), 'StrongPass1!');
    fireEvent.changeText(getByPlaceholderText('auth.confirmPassword'), 'StrongPass1!');
    fireEvent.press(getByText('auth.register'));
    await waitFor(() => expect(mockRegister).toHaveBeenCalled());
    expect(mockRegister).toHaveBeenCalledWith(
      'fresh@example.com',
      'StrongPass1!',
      expect.objectContaining({ inviteId: undefined }),
    );
  });
});
