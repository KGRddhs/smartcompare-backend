/**
 * M18 MB-flows-03 — registration that needs email confirmation must not
 * silently dead-end.
 *
 * Old chain: register() returned bare success with token undefined ->
 * RegisterScreen called onRegisterSuccess() -> App.handleLoginSuccess ->
 * verifyAuth() -> initializeAuth() returned null (no token saved) ->
 * handleLoginSuccess body is inside `if (authUser)` so NOTHING happened:
 * spinner cleared, same filled-in form, no message. The user's only
 * signal was a contradictory "already registered" error on a second tap.
 *
 * New contract: authService.register() sets `needsEmailConfirmation`
 * when the backend returns a user WITHOUT a session; RegisterScreen then
 * renders the check-your-inbox card instead of firing onRegisterSuccess.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

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

function renderScreen() {
  return render(
    <RegisterScreen
      navigation={mockNavigation}
      route={{ params: undefined }}
      onRegisterSuccess={onRegisterSuccess}
    />,
  );
}

function fillRequired(getByPlaceholderText: any) {
  fireEvent.changeText(getByPlaceholderText('auth.email'), 'user@example.com');
  fireEvent.changeText(getByPlaceholderText('auth.password'), 'StrongPass1x');
  fireEvent.changeText(getByPlaceholderText('auth.confirmPassword'), 'StrongPass1x');
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('RegisterScreen — email-confirmation flow (M18 MB-flows-03)', () => {
  it('shows the check-your-inbox card and does NOT fire onRegisterSuccess when confirmation is required', async () => {
    mockRegister.mockResolvedValueOnce({
      success: true,
      needsEmailConfirmation: true,
      user: { id: 'u1', email: 'user@example.com' },
    });

    const screen = renderScreen();
    fillRequired(screen.getByPlaceholderText);
    fireEvent.press(screen.getByText('auth.register'));

    await waitFor(() =>
      expect(screen.getByText('register.emailConfirmation.title')).toBeTruthy(),
    );
    expect(onRegisterSuccess).not.toHaveBeenCalled();
  });

  it('back-to-sign-in on the confirmation card navigates to Login', async () => {
    mockRegister.mockResolvedValueOnce({
      success: true,
      needsEmailConfirmation: true,
      user: { id: 'u1', email: 'user@example.com' },
    });

    const screen = renderScreen();
    fillRequired(screen.getByPlaceholderText);
    fireEvent.press(screen.getByText('auth.register'));

    await waitFor(() =>
      expect(screen.getByText('register.emailConfirmation.backToSignIn')).toBeTruthy(),
    );
    fireEvent.press(screen.getByText('register.emailConfirmation.backToSignIn'));
    expect(mockNavigation.navigate).toHaveBeenCalledWith('Login');
    expect(onRegisterSuccess).not.toHaveBeenCalled();
  });

  it('still fires onRegisterSuccess when a session token is issued (no confirmation gate)', async () => {
    mockRegister.mockResolvedValueOnce({
      success: true,
      token: 'at-1',
      user: { id: 'u1', email: 'user@example.com' },
    });

    const screen = renderScreen();
    fillRequired(screen.getByPlaceholderText);
    fireEvent.press(screen.getByText('auth.register'));

    await waitFor(() => expect(onRegisterSuccess).toHaveBeenCalledTimes(1));
    expect(screen.queryByText('register.emailConfirmation.title')).toBeNull();
  });
});
