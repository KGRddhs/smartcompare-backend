/**
 * S74 CLIENT-TRUTH - no clipboard read on Register (decision CLIP=A).
 *
 * Spec CLIENT_TRUTH_SPEC.md section 4 + section 8 rows CT-R1..CT-R3. At main
 * dfbda511 RegisterScreen imports tryReadClipboardForInviteCode
 * (RegisterScreen.tsx:25) and calls it on every mount with an empty invite
 * field (:101-112), then shows a consent banner (:383-419). The redirect
 * Worker that would put a code on the clipboard is not deployed (AR-8), so
 * the read serves no live path. After the change a referral code reaches
 * register() only from the route `code` param (deep link), the Android
 * Play Install Referrer hand-off, or manual typing.
 *
 * Harness: __tests__/RegisterScreen.deferredCode.test.tsx:15-104 (the
 * clipboardFallbackService mock stays so a read, if any, is observable).
 */
import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, waitFor, act } from '@testing-library/react-native';

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

jest.mock('../../src/services/authService', () => ({
  register: jest.fn(),
  signInWithGoogle: jest.fn().mockResolvedValue({ success: false }),
  signInWithApple: jest.fn().mockResolvedValue({ success: false }),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(false),
}));

jest.mock('../../src/services/api', () => ({
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

const consumeDeferredMock = jest.fn();
jest.mock('../../src/services/deferredInviteCode', () => ({
  consumeDeferredInviteCode: () => consumeDeferredMock(),
  setDeferredInviteCode: jest.fn(),
  __resetDeferredInviteCodeForTests: jest.fn(),
}));

const tryClipboardMock = jest.fn();
jest.mock('../../src/services/clipboardFallbackService', () => ({
  tryReadClipboardForInviteCode: () => tryClipboardMock(),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const RegisterScreen = require('../../src/screens/RegisterScreen').default;

const REGISTER_SOURCE = fs.readFileSync(
  path.resolve(__dirname, '../../src/screens/RegisterScreen.tsx'),
  'utf8',
);

const mockNavigation: any = {
  navigate: jest.fn(),
  goBack: jest.fn(),
};

function renderScreen(params: Record<string, unknown> = {}) {
  return render(
    <RegisterScreen
      navigation={mockNavigation}
      route={{ params } as any}
      onRegisterSuccess={jest.fn()}
    />,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  consumeDeferredMock.mockReturnValue(null);
  tryClipboardMock.mockResolvedValue(null);
});

describe('S74 CLIENT-TRUTH Register never reads the clipboard', () => {
  it('CT-R1: with a QR code on the clipboard and an empty field, the clipboard is never read and no consent banner renders', async () => {
    tryClipboardMock.mockResolvedValue('QR-BBBBBB');
    const { queryByTestId, queryByDisplayValue } = renderScreen();
    // The mount effect has run (the PIR hand-off is consulted first).
    await waitFor(() => expect(consumeDeferredMock).toHaveBeenCalledTimes(1));
    // Flush the microtasks a clipboard read would resolve on.
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(tryClipboardMock).not.toHaveBeenCalled();
    expect(queryByTestId('clipboard-consent-banner')).toBeNull();
    expect(queryByDisplayValue('QR-BBBBBB')).toBeNull();
  });

  it('CT-R2 + Y7: RegisterScreen.tsx has no clipboardFallbackService import and no direct expo-clipboard read', () => {
    const lineHits = (re: RegExp) =>
      REGISTER_SOURCE.split(/\r?\n/)
        .map((l, i) => `${i + 1}: ${l.trim()}`)
        .filter((l) => re.test(l));
    // Code lines only: a comment may still name the reader for the re-enable note.
    const codeOnly = (lines: string[]) => lines.filter((l) => !/^\d+: (?:\/\/|\/?\*|\{\/\*)/.test(l));
    expect({
      importLines: lineHits(/(?:from\s+|require\(\s*)['"][^'"]*clipboardFallbackService['"]/),
      readerLines: codeOnly(lineHits(/tryReadClipboardForInviteCode/)),
      expoClipboardLines: codeOnly(lineHits(/['"]expo-clipboard['"]/)),
      clipboardApiLines: codeOnly(lineHits(/\b(?:getStringAsync|hasStringAsync)\b/)),
    }).toEqual({ importLines: [], readerLines: [], expoClipboardLines: [], clipboardApiLines: [] });
  });

  it('CT-R3 GUARD: a deep-link route code pre-fills and locks the invite field', async () => {
    const { findByDisplayValue, getByLabelText } = renderScreen({ code: 'QR-AAAAAA' });
    const field = await findByDisplayValue('QR-AAAAAA');
    expect(field.props.editable).toBe(false);
    // The locked state offers the clear control.
    expect(getByLabelText('register.inviteCode.clear')).toBeTruthy();
    expect(tryClipboardMock).not.toHaveBeenCalled();
  });
});
