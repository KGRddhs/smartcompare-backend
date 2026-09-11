/**
 * W3-6 — `ResetPasswordScreen`: the set-a-new-password screen that does not
 * exist anywhere in the app today (finding MB-FLOWS-STATE-02).
 *
 * It reads the recovery access token from the module slot exactly ONCE on
 * mount, never renders it, never logs it, and hands it to
 * `authService.completePasswordRecovery` together with the new password.
 *
 * Contract the implementation must satisfy (asserted below):
 *   - inputs found by placeholder `auth.newPassword` / `auth.confirmPassword`
 *     (the ForgotPassword/Register convention: placeholder = the t() key)
 *   - testIDs `reset-password-submit`, `reset-password-signin`,
 *     `reset-password-request-new-link` on the three Buttons
 *   - both CTAs use `navigation.reset`, NOT `navigate`: on the cold-start
 *     deep-link path the Auth stack holds ONLY [ResetPassword], so a push
 *     would leave the back gesture landing on a screen whose slot is spent.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.mock('../src/services/authService', () => ({
  completePasswordRecovery: jest.fn(),
}));

jest.mock('../src/services/api', () => ({
  parseApiError: (err: any) => ({
    message: err?.response?.data?.error || err?.message || 'Unknown error',
    code: err?.response?.data?.code,
  }),
}));

import ResetPasswordScreen from '../src/screens/ResetPasswordScreen';
import { completePasswordRecovery } from '../src/services/authService';
import {
  setPendingRecovery,
  __resetPendingRecoveryForTests,
} from '../src/services/passwordRecoveryLink';

const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
  reset: jest.fn(),
} as any;

const VALID = 'NewPassw0rd!x';

function renderScreen() {
  return render(<ResetPasswordScreen navigation={mockNavigation} />);
}

function lastRouteName(resetArg: any): string {
  return resetArg.routes[resetArg.routes.length - 1].name;
}

beforeEach(() => {
  jest.clearAllMocks();
  __resetPendingRecoveryForTests();
});

describe('with a recovery token in the slot', () => {
  beforeEach(() => {
    setPendingRecovery({ accessToken: 'tok' });
  });

  it('submits the slot token with the new password, then offers a sign-in CTA that RESETS to Login', async () => {
    (completePasswordRecovery as jest.Mock).mockResolvedValue(undefined);

    const screen = renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText('auth.newPassword'), VALID);
    fireEvent.changeText(screen.getByPlaceholderText('auth.confirmPassword'), VALID);
    fireEvent.press(screen.getByTestId('reset-password-submit'));

    await waitFor(() => {
      expect(completePasswordRecovery).toHaveBeenCalledTimes(1);
    });
    expect(completePasswordRecovery).toHaveBeenCalledWith('tok', VALID);

    await waitFor(() => {
      expect(screen.getByText('auth.passwordUpdated')).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId('reset-password-signin'));
    expect(mockNavigation.reset).toHaveBeenCalledTimes(1);
    expect(lastRouteName(mockNavigation.reset.mock.calls[0][0])).toBe('Login');
  });

  it('never puts the token on screen', async () => {
    (completePasswordRecovery as jest.Mock).mockResolvedValue(undefined);

    const screen = renderScreen();
    expect(JSON.stringify(screen.toJSON())).not.toContain('tok');

    fireEvent.changeText(screen.getByPlaceholderText('auth.newPassword'), VALID);
    fireEvent.changeText(screen.getByPlaceholderText('auth.confirmPassword'), VALID);
    fireEvent.press(screen.getByTestId('reset-password-submit'));

    await waitFor(() => {
      expect(completePasswordRecovery).toHaveBeenCalledTimes(1);
    });
    expect(JSON.stringify(screen.toJSON())).not.toContain('tok');
  });

  it('refuses a mismatched confirmation without calling the API', () => {
    const screen = renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText('auth.newPassword'), VALID);
    fireEvent.changeText(screen.getByPlaceholderText('auth.confirmPassword'), 'NewPassw0rd!y');
    fireEvent.press(screen.getByTestId('reset-password-submit'));

    expect(completePasswordRecovery).not.toHaveBeenCalled();
    expect(screen.getByText('auth.passwordsDoNotMatch')).toBeTruthy();
  });

  it('refuses a weak password without calling the API (same rule as RegisterScreen:192)', () => {
    const screen = renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText('auth.newPassword'), 'short1');
    fireEvent.changeText(screen.getByPlaceholderText('auth.confirmPassword'), 'short1');
    fireEvent.press(screen.getByTestId('reset-password-submit'));

    expect(completePasswordRecovery).not.toHaveBeenCalled();
    expect(screen.getByText('auth.passwordRequirements')).toBeTruthy();
  });

  it('renders the server message when the backend rejects the recovery token', async () => {
    (completePasswordRecovery as jest.Mock).mockRejectedValue({
      response: {
        data: {
          error: 'This reset link is no longer valid.',
          code: 'RECOVERY_TOKEN_INVALID',
        },
      },
    });

    const screen = renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText('auth.newPassword'), VALID);
    fireEvent.changeText(screen.getByPlaceholderText('auth.confirmPassword'), VALID);
    fireEvent.press(screen.getByTestId('reset-password-submit'));

    await waitFor(() => {
      expect(screen.getByText('This reset link is no longer valid.')).toBeTruthy();
    });
    expect(screen.queryByText('auth.passwordUpdated')).toBeNull();
  });
});

describe('with an EMPTY slot (a stale link, a cold remount, or a spent token)', () => {
  it('renders the expired state instead of a form, and its CTA RESETS to ForgotPassword', () => {
    const screen = renderScreen();

    expect(screen.getByText('auth.resetLinkExpired')).toBeTruthy();
    expect(screen.queryByPlaceholderText('auth.newPassword')).toBeNull();
    expect(screen.queryByTestId('reset-password-submit')).toBeNull();

    fireEvent.press(screen.getByTestId('reset-password-request-new-link'));
    expect(mockNavigation.reset).toHaveBeenCalledTimes(1);
    expect(lastRouteName(mockNavigation.reset.mock.calls[0][0])).toBe('ForgotPassword');
  });
});
