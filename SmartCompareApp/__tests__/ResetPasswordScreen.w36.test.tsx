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
 *   - failures render by CODE, never by `parseApiError(...).message`
 *     (api.ts / errorCopy.ts contract): RECOVERY_TOKEN_INVALID swaps to the
 *     request-a-new-link state, UPSTREAM_UNAVAILABLE (a Supabase blip — the
 *     link still works) keeps the form with `auth.resetConnectionRetry`,
 *     everything else renders `common.error`; after any failure the form is
 *     usable again.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// The screen is a password-entry surface: it must call the screen-capture
// guard. The shared __mocks__ stub is a plain no-op function, so it is swapped
// for a spy here to make the call observable.
jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: jest.fn(),
}));

jest.mock('../src/services/authService', () => ({
  completePasswordRecovery: jest.fn(),
  getToken: jest.fn().mockResolvedValue(null),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
}));

// The REAL parseApiError, not a stand-in: its codeless transport arm returns
// an EMPTY message (offline / axios deadline / bare 503), and a stand-in that
// fell back to `err.message` hid exactly the silent-failure path the screen
// must render. Only api.ts's network surface is mocked (the
// api.networkMatrix.m18 harness).
jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));
jest.mock('axios', () => {
  const instance = {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return { create: jest.fn(() => instance), __instance: instance };
});
jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(),
  SaveFormat: { JPEG: 'jpeg' },
}));
jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));
jest.mock('../src/services/sentry', () => ({
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: (s: string) => s,
  scrubBeforeSend: (e: any) => e,
}));

import ResetPasswordScreen from '../src/screens/ResetPasswordScreen';
import { completePasswordRecovery } from '../src/services/authService';
import { usePreventScreenCapture } from 'expo-screen-capture';
import {
  setPendingRecovery,
  consumePendingRecovery,
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

// After a failure the form must be usable again: the submit button (and the
// inputs) re-enable, and a second tap really submits a second time.
async function expectFormUsableAgain(screen: ReturnType<typeof renderScreen>) {
  const submit = screen.getByTestId('reset-password-submit');
  expect(submit.props.disabled).toBe(false);
  expect(screen.getByPlaceholderText('auth.newPassword').props.editable).toBe(true);
  fireEvent.press(submit);
  await waitFor(() => {
    expect(completePasswordRecovery).toHaveBeenCalledTimes(2);
  });
}

async function submitValid(screen: ReturnType<typeof renderScreen>) {
  fireEvent.changeText(screen.getByPlaceholderText('auth.newPassword'), VALID);
  fireEvent.changeText(screen.getByPlaceholderText('auth.confirmPassword'), VALID);
  fireEvent.press(screen.getByTestId('reset-password-submit'));
  await waitFor(() => {
    expect(completePasswordRecovery).toHaveBeenCalledTimes(1);
  });
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
    expect(mockNavigation.reset).toHaveBeenCalledWith({
      index: 0,
      routes: [{ name: 'Login' }],
    });
    expect(mockNavigation.navigate).not.toHaveBeenCalled();
  });

  it('arms the screen-capture guard on mount (a new password is typed here)', () => {
    renderScreen();
    expect(usePreventScreenCapture).toHaveBeenCalled();
  });

  it('consumes the slot on mount — the token is not left parked for a second reader', () => {
    renderScreen();
    expect(consumePendingRecovery()).toBeNull();
  });

  it('never puts the token on screen', async () => {
    (completePasswordRecovery as jest.Mock).mockResolvedValue(undefined);

    const screen = renderScreen();
    expect(JSON.stringify(screen.toJSON())).not.toContain('tok');

    await submitValid(screen);
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

  // One case per rule (same rule as RegisterScreen:192 and the backend's
  // _validate_password_strength): each password breaks exactly ONE rule, so
  // dropping any single check lets its case through to the API.
  it.each([
    ['too short', 'Short1abc'],
    ['no uppercase', 'nouppercase1234'],
    ['no lowercase', 'NOLOWERCASE1234'],
    ['no digit', 'NoDigitsAtAllHere'],
  ])('refuses a weak password (%s) without calling the API', (_rule, weak) => {
    const screen = renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText('auth.newPassword'), weak);
    fireEvent.changeText(screen.getByPlaceholderText('auth.confirmPassword'), weak);
    fireEvent.press(screen.getByTestId('reset-password-submit'));

    expect(completePasswordRecovery).not.toHaveBeenCalled();
    expect(screen.getByText('auth.passwordRequirements')).toBeTruthy();
  });

  it('a RECOVERY_TOKEN_INVALID rejection swaps the form for the request-a-new-link state', async () => {
    (completePasswordRecovery as jest.Mock).mockRejectedValue({
      response: {
        status: 400,
        data: {
          success: false,
          error: 'This reset link is no longer valid.',
          code: 'RECOVERY_TOKEN_INVALID',
        },
      },
    });

    const screen = renderScreen();
    await submitValid(screen);

    await waitFor(() => {
      expect(screen.getByText('auth.resetLinkExpired')).toBeTruthy();
    });
    expect(screen.queryByTestId('reset-password-submit')).toBeNull();
    expect(screen.queryByText('auth.passwordUpdated')).toBeNull();
    // The backend's English sentence is never render input (Arabic users).
    expect(screen.queryByText('This reset link is no longer valid.')).toBeNull();

    fireEvent.press(screen.getByTestId('reset-password-request-new-link'));
    expect(mockNavigation.reset).toHaveBeenCalledWith({
      index: 1,
      routes: [{ name: 'Login' }, { name: 'ForgotPassword' }],
    });
  });

  // Every failure that is NOT a dead token keeps the form (the user can tap
  // again) and renders the translated common.error — never an empty box,
  // never a raw backend or axios string. The first two are the codeless
  // transport class for which the REAL parseApiError returns message ''.
  const OTHER_FAILURES: [string, any, string | null][] = [
    [
      'an offline device (ERR_NETWORK, no response)',
      Object.assign(new Error('Network Error'), { code: 'ERR_NETWORK' }),
      'Network Error',
    ],
    ['a bare 503 from the edge', { response: { status: 503, data: {} } }, null],
    [
      'a generic backend failure (RECOVERY_FAILED)',
      {
        response: {
          status: 400,
          data: {
            success: false,
            error: 'Something went wrong. Please try again later.',
            code: 'RECOVERY_FAILED',
          },
        },
      },
      'Something went wrong. Please try again later.',
    ],
  ];

  it.each(OTHER_FAILURES)(
    '%s renders common.error and keeps the form',
    async (_label, rejection, rawText) => {
      (completePasswordRecovery as jest.Mock).mockRejectedValue(rejection);

      const screen = renderScreen();
      await submitValid(screen);

      await waitFor(() => {
        expect(screen.getByText('common.error')).toBeTruthy();
      });
      expect(screen.getByTestId('reset-password-submit')).toBeTruthy();
      expect(screen.queryByText('auth.passwordUpdated')).toBeNull();
      expect(screen.queryByText('auth.resetLinkExpired')).toBeNull();
      if (rawText) {
        expect(screen.queryByText(rawText)).toBeNull();
      }
      await expectFormUsableAgain(screen);
    },
  );

  it('an upstream blip (UPSTREAM_UNAVAILABLE) keeps the form and says the link still works', async () => {
    // The backend returns this when Supabase could not be reached while
    // checking the link. It is not a verdict on the link, so the screen must
    // NOT send the user back for a new email.
    (completePasswordRecovery as jest.Mock).mockRejectedValue({
      response: {
        status: 400,
        data: {
          success: false,
          error: 'Connection failed. Please try again.',
          code: 'UPSTREAM_UNAVAILABLE',
        },
      },
    });

    const screen = renderScreen();
    await submitValid(screen);

    await waitFor(() => {
      expect(screen.getByText('auth.resetConnectionRetry')).toBeTruthy();
    });
    expect(screen.queryByText('common.error')).toBeNull();
    expect(screen.queryByText('auth.resetLinkExpired')).toBeNull();
    expect(screen.queryByText('Connection failed. Please try again.')).toBeNull();
    await expectFormUsableAgain(screen);
  });
});

describe('with an EMPTY slot (a stale link, a cold remount, or a spent token)', () => {
  it('renders the expired state instead of a form, and its CTA RESETS to [Login, ForgotPassword]', () => {
    const screen = renderScreen();

    expect(screen.getByText('auth.resetLinkExpired')).toBeTruthy();
    expect(screen.queryByPlaceholderText('auth.newPassword')).toBeNull();
    expect(screen.queryByTestId('reset-password-submit')).toBeNull();

    fireEvent.press(screen.getByTestId('reset-password-request-new-link'));
    expect(mockNavigation.reset).toHaveBeenCalledTimes(1);
    // Login MUST sit under ForgotPassword: its own back link is goBack(), and
    // on a cold start the Auth stack held only [ResetPassword] — without Login
    // underneath, Back would dead-end.
    expect(mockNavigation.reset).toHaveBeenCalledWith({
      index: 1,
      routes: [{ name: 'Login' }, { name: 'ForgotPassword' }],
    });
    expect(mockNavigation.navigate).not.toHaveBeenCalled();
  });
});
