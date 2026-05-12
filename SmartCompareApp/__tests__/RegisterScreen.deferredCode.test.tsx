/**
 * RegisterScreen deferred-code + clipboard fallback — Bundle B/C/D Task 2.12.
 *
 * Verifies the mount-effect priority chain:
 *   1. deferredInviteCode.consumeDeferredInviteCode() (Android PIR)
 *   2. clipboardFallbackService.tryReadClipboardForInviteCode() (iOS)
 *      — shows EXPLICIT consent banner; never auto-fills.
 *
 * Apple-review surface: clipboard read is once-per-mount; consent
 * dialog is mandatory; declining leaves the field empty.
 */
import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';

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
    t: (key: string, opts?: Record<string, unknown>) => {
      let str = key;
      if (opts) {
        for (const [k, v] of Object.entries(opts)) {
          if (k === 'defaultValue') continue;
          str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
        }
      }
      return str;
    },
  }),
}));

jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: jest.fn(),
}));

jest.mock('../src/services/authService', () => ({
  register: jest.fn(),
  signInWithGoogle: jest.fn().mockResolvedValue({ success: false }),
  signInWithApple: jest.fn().mockResolvedValue({ success: false }),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(false),
}));

jest.mock('../src/services/api', () => ({
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

const consumeDeferredMock = jest.fn();
jest.mock('../src/services/deferredInviteCode', () => ({
  consumeDeferredInviteCode: () => consumeDeferredMock(),
  setDeferredInviteCode: jest.fn(),
  __resetDeferredInviteCodeForTests: jest.fn(),
}));

const tryClipboardMock = jest.fn();
jest.mock('../src/services/clipboardFallbackService', () => ({
  tryReadClipboardForInviteCode: () => tryClipboardMock(),
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
      route={{ params: {} } as any}
      onRegisterSuccess={onRegisterSuccess}
    />
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  consumeDeferredMock.mockReturnValue(null);
  tryClipboardMock.mockResolvedValue(null);
});

describe('RegisterScreen — deferred code + clipboard fallback', () => {
  it('pre-fills + locks invite code when deferred PIR code exists (Android path)', async () => {
    consumeDeferredMock.mockReturnValue('QR-ATAUX9');
    const { findByDisplayValue } = renderScreen();
    expect(await findByDisplayValue('QR-ATAUX9')).toBeTruthy();
  });

  it('does NOT auto-fill from clipboard; shows consent banner instead', async () => {
    tryClipboardMock.mockResolvedValue('QR-BBBBBB');
    const { findByTestId, queryByDisplayValue } = renderScreen();
    expect(await findByTestId('clipboard-consent-banner')).toBeTruthy();
    // CRITICAL Apple-review invariant: never pre-fill before consent.
    expect(queryByDisplayValue('QR-BBBBBB')).toBeNull();
  });

  it('consent accept sets the invite code', async () => {
    tryClipboardMock.mockResolvedValue('QR-CCCCCC');
    const { findByTestId, findByDisplayValue } = renderScreen();
    const acceptBtn = await findByTestId('clipboard-consent-accept');
    await act(async () => {
      fireEvent.press(acceptBtn);
    });
    expect(await findByDisplayValue('QR-CCCCCC')).toBeTruthy();
  });

  it('consent reject dismisses the banner without setting the code', async () => {
    tryClipboardMock.mockResolvedValue('QR-DDDDDD');
    const { findByTestId, queryByTestId, queryByDisplayValue } = renderScreen();
    const rejectBtn = await findByTestId('clipboard-consent-reject');
    await act(async () => {
      fireEvent.press(rejectBtn);
    });
    await waitFor(() =>
      expect(queryByTestId('clipboard-consent-banner')).toBeNull()
    );
    expect(queryByDisplayValue('QR-DDDDDD')).toBeNull();
  });

  it('does not consult clipboard when a deferred PIR code is already available', async () => {
    consumeDeferredMock.mockReturnValue('QR-EEEEEE');
    renderScreen();
    await waitFor(() => {
      // Mount effect resolved.
      expect(consumeDeferredMock).toHaveBeenCalledTimes(1);
    });
    expect(tryClipboardMock).not.toHaveBeenCalled();
  });

  it('does not show consent when clipboard contains no QR code', async () => {
    tryClipboardMock.mockResolvedValue(null);
    const { queryByTestId } = renderScreen();
    await waitFor(() => expect(tryClipboardMock).toHaveBeenCalled());
    expect(queryByTestId('clipboard-consent-banner')).toBeNull();
  });
});
