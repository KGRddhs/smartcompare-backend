/**
 * S69 U6 T3 — no system push prompt at launch or login; an in-app pre-prompt
 * asks once (RT-12, App Review guideline 4.5.4).
 *
 * Spec R3 + review corrections 12-15 and open questions C/D:
 *   - `tryRegisterPushToken()` (called on every authed launch, App.tsx:238,
 *     and right after login, App.tsx:313) NEVER calls
 *     `requestPermissionsAsync`; it registers only an ALREADY-granted
 *     permission. Both App call sites go through it, so pinning the service
 *     pins "launch and login do not prompt".
 *   - The pre-prompt state is persisted in AsyncStorage under
 *     `@qaren_push_preprompt_answered` (consent.ts is a pure module with no
 *     storage — correction 14).
 *   - `src/services/pushPrePrompt.ts`:
 *       shouldShowPushPrePrompt(ctx?) -> true only when the OS permission is
 *         'undetermined' AND the flag is unset AND the Results screen was not
 *         opened from History / Smart pick (ctx.fromHistory) AND the
 *         demographics sheet is not showing on this mount
 *         (ctx.demographicsShown) — corrections 15 / open question C;
 *       answerPushPrePrompt('allow' | 'not_now') -> persists the flag;
 *         'allow' asks the OS once and, when granted, registers the token.
 *   - `src/components/PushPrePrompt.tsx` (named export PushPrePrompt,
 *     props { visible, onClose }): testIDs push-preprompt /
 *     push-preprompt-allow / push-preprompt-not-now; copy keys
 *     notifications.prePrompt.{title,body,allow,notNow}.
 *   - Onboarding Step 17 is the pre-prompt for new users: Allow that is
 *     granted registers the token (correction 12 — today it never does), and
 *     BOTH answers set the flag so Results never asks again.
 *   - Copy (open question D): says what the live pushes are and that they can
 *     be switched off in Profile; never promises price drops (the backend
 *     sends none — correction 13); brand MYEZ / ميّز.
 *   - ResultsScreen wires the pre-prompt, gated on history-origin and the
 *     demographics sheet.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const mockNotifications = {
  __esModule: true,
  getPermissionsAsync: jest.fn(),
  requestPermissionsAsync: jest.fn(),
  getExpoPushTokenAsync: jest.fn(),
  setNotificationChannelAsync: jest.fn(),
  setNotificationHandler: jest.fn(),
  AndroidImportance: { DEFAULT: 3, HIGH: 4, MAX: 5, LOW: 2, MIN: 1 },
};
jest.mock('expo-notifications', () => mockNotifications);

const mockPut = jest.fn();
jest.mock('../../src/services/api', () => {
  const client = {
    put: (...args: any[]) => mockPut(...args),
    post: jest.fn(),
    get: jest.fn(),
    delete: jest.fn(),
  };
  return {
    __esModule: true,
    default: client,
    api: client,
    parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
    trackEvent: jest.fn(),
    trackEvents: jest.fn(),
  };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

const PREPROMPT_KEY = '@qaren_push_preprompt_answered';
const TOKEN = 'ExponentPushToken[s69]';
const SRC = path.resolve(__dirname, '../../src');

 
const en: Record<string, string> = require('../../src/i18n/en.json');
 
const ar: Record<string, string> = require('../../src/i18n/ar.json');
 
const policy = require('../../src/i18n/.copy-policy.json');

function setOsStatus(status: 'undetermined' | 'granted' | 'denied') {
  mockNotifications.getPermissionsAsync.mockResolvedValue({
    status,
    granted: status === 'granted',
    canAskAgain: status !== 'denied',
  });
}

function setRequestResult(status: 'granted' | 'denied') {
  mockNotifications.requestPermissionsAsync.mockResolvedValue({
    status,
    granted: status === 'granted',
    canAskAgain: false,
  });
}

function prePrompt() {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  return require('../../src/services/pushPrePrompt');
}

function tokenPuts() {
  return mockPut.mock.calls.filter((c) => String(c[0]).includes('/push-token'));
}

beforeEach(async () => {
  jest.clearAllMocks();
  await AsyncStorage.clear();
  setOsStatus('undetermined');
  setRequestResult('granted');
  mockNotifications.getExpoPushTokenAsync.mockResolvedValue({ data: TOKEN });
  mockPut.mockResolvedValue({ data: { success: true } });
});

describe('S69 U6 T3 \u2014 tryRegisterPushToken never prompts (launch + login path)', () => {
  it('T3.1 undetermined -> no system prompt, no token, no PUT; already granted -> the token is still registered', async () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { tryRegisterPushToken } = require('../../src/services/pushTokenService');

    setOsStatus('undetermined');
    const undetermined = await tryRegisterPushToken();
    expect(mockNotifications.requestPermissionsAsync).not.toHaveBeenCalled();
    expect(mockNotifications.getExpoPushTokenAsync).not.toHaveBeenCalled();
    expect(tokenPuts()).toHaveLength(0);
    expect(undetermined.registered).toBe(false);

    setOsStatus('granted');
    const granted = await tryRegisterPushToken();
    expect(granted.registered).toBe(true);
    expect(tokenPuts()).toEqual([['/api/v1/auth/push-token', { expo_push_token: TOKEN }]]);
    expect(mockNotifications.requestPermissionsAsync).not.toHaveBeenCalled();
  });

  it('T3.2 denied -> no system prompt and nothing registered', async () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { tryRegisterPushToken } = require('../../src/services/pushTokenService');
    setOsStatus('denied');
    const result = await tryRegisterPushToken();
    expect(result.registered).toBe(false);
    expect(mockNotifications.requestPermissionsAsync).not.toHaveBeenCalled();
    expect(tokenPuts()).toHaveLength(0);
  });

  it('T3.3 pushTokenService.ts has no requestPermissionsAsync call left', () => {
    const src = fs.readFileSync(path.join(SRC, 'services/pushTokenService.ts'), 'utf8');
    const code = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(code).not.toMatch(/requestPermissionsAsync\s*\(/);
  });
});

describe('S69 U6 T3 \u2014 pushPrePrompt service', () => {
  it('T3.4 persists under @qaren_push_preprompt_answered', () => {
    expect(prePrompt().PUSH_PREPROMPT_ANSWERED_KEY).toBe(PREPROMPT_KEY);
  });

  it('T3.5 shows only when the OS status is undetermined and the flag is unset', async () => {
    const { shouldShowPushPrePrompt } = prePrompt();

    setOsStatus('undetermined');
    expect(await shouldShowPushPrePrompt()).toBe(true);

    setOsStatus('granted');
    expect(await shouldShowPushPrePrompt()).toBe(false);

    setOsStatus('denied');
    expect(await shouldShowPushPrePrompt()).toBe(false);

    setOsStatus('undetermined');
    await AsyncStorage.setItem(PREPROMPT_KEY, 'not_now');
    expect(await shouldShowPushPrePrompt()).toBe(false);
  });

  it('T3.6 never shows on a Results opened from History / Smart pick, nor on the mount that shows the demographics sheet', async () => {
    const { shouldShowPushPrePrompt } = prePrompt();
    setOsStatus('undetermined');
    expect(await shouldShowPushPrePrompt({ fromHistory: false, demographicsShown: false })).toBe(true);
    expect(await shouldShowPushPrePrompt({ fromHistory: true, demographicsShown: false })).toBe(false);
    expect(await shouldShowPushPrePrompt({ fromHistory: false, demographicsShown: true })).toBe(false);
  });

  it('T3.7 "Not now" persists, never asks the OS, and the pre-prompt is never re-asked automatically', async () => {
    const { answerPushPrePrompt, shouldShowPushPrePrompt } = prePrompt();
    const granted = await answerPushPrePrompt('not_now');

    expect(granted).toBe(false);
    expect(mockNotifications.requestPermissionsAsync).not.toHaveBeenCalled();
    expect(await AsyncStorage.getItem(PREPROMPT_KEY)).not.toBeNull();
    expect(await shouldShowPushPrePrompt()).toBe(false);
    expect(tokenPuts()).toHaveLength(0);
  });

  it('T3.8 "Allow" asks the OS exactly once and, when granted, registers the token; the flag is persisted', async () => {
    const { answerPushPrePrompt, shouldShowPushPrePrompt } = prePrompt();
    setRequestResult('granted');
    // After the grant, the OS reports granted — as it does on device.
    mockNotifications.requestPermissionsAsync.mockImplementation(async () => {
      setOsStatus('granted');
      return { status: 'granted', granted: true, canAskAgain: false };
    });

    const granted = await answerPushPrePrompt('allow');

    expect(granted).toBe(true);
    expect(mockNotifications.requestPermissionsAsync).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(tokenPuts()).toEqual([['/api/v1/auth/push-token', { expo_push_token: TOKEN }]]),
    );
    expect(await AsyncStorage.getItem(PREPROMPT_KEY)).not.toBeNull();
    expect(await shouldShowPushPrePrompt()).toBe(false);
  });

  it('T3.9 "Allow" that the OS denies registers nothing and still persists the answer', async () => {
    const { answerPushPrePrompt } = prePrompt();
    setRequestResult('denied');

    const granted = await answerPushPrePrompt('allow');

    expect(granted).toBe(false);
    expect(mockNotifications.requestPermissionsAsync).toHaveBeenCalledTimes(1);
    expect(tokenPuts()).toHaveLength(0);
    expect(await AsyncStorage.getItem(PREPROMPT_KEY)).not.toBeNull();
  });
});

describe('S69 U6 T3 \u2014 PushPrePrompt component', () => {
  function renderPrompt(onClose = jest.fn()) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { PushPrePrompt } = require('../../src/components/PushPrePrompt');
    return { onClose, screen: render(<PushPrePrompt visible onClose={onClose} />) };
  }

  it('T3.10 renders the title, body and both actions from notifications.prePrompt.*', () => {
    const { screen } = renderPrompt();
    expect(screen.getByTestId('push-preprompt')).toBeTruthy();
    expect(screen.getByText('notifications.prePrompt.title')).toBeTruthy();
    expect(screen.getByText('notifications.prePrompt.body')).toBeTruthy();
    expect(screen.getByTestId('push-preprompt-allow')).toBeTruthy();
    expect(screen.getByTestId('push-preprompt-not-now')).toBeTruthy();
  });

  it('T3.11 "Not now" persists the answer, never asks the OS, and closes', async () => {
    const { screen, onClose } = renderPrompt();
    await act(async () => {
      fireEvent.press(screen.getByTestId('push-preprompt-not-now'));
    });
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(mockNotifications.requestPermissionsAsync).not.toHaveBeenCalled();
    expect(await AsyncStorage.getItem(PREPROMPT_KEY)).not.toBeNull();
  });

  it('T3.12 "Allow" shows the system prompt once, registers on grant, and closes', async () => {
    mockNotifications.requestPermissionsAsync.mockImplementation(async () => {
      setOsStatus('granted');
      return { status: 'granted', granted: true, canAskAgain: false };
    });
    const { screen, onClose } = renderPrompt();
    await act(async () => {
      fireEvent.press(screen.getByTestId('push-preprompt-allow'));
    });
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(mockNotifications.requestPermissionsAsync).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(tokenPuts()).toHaveLength(1));
    expect(await AsyncStorage.getItem(PREPROMPT_KEY)).not.toBeNull();
  });
});

describe('S69 U6 T3 \u2014 onboarding Step 17 is the pre-prompt for new users', () => {
  function renderStep17(onDone = jest.fn()) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { Step17Notifications } = require('../../src/screens/onboarding/Step17Notifications');
    return { onDone, screen: render(<Step17Notifications onDone={onDone} />) };
  }

  it('T3.13 Allow that is granted registers the push token and persists the answer', async () => {
    mockNotifications.requestPermissionsAsync.mockImplementation(async () => {
      setOsStatus('granted');
      return { status: 'granted', granted: true, canAskAgain: false };
    });
    const { screen, onDone } = renderStep17();
    await act(async () => {
      fireEvent.press(screen.getByTestId('s17-allow'));
    });
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(true));
    expect(mockNotifications.requestPermissionsAsync).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(tokenPuts()).toEqual([['/api/v1/auth/push-token', { expo_push_token: TOKEN }]]),
    );
    expect(await AsyncStorage.getItem(PREPROMPT_KEY)).not.toBeNull();
  });

  it('T3.14 "Maybe later" persists the answer (Results never asks again) without asking the OS', async () => {
    const { screen, onDone } = renderStep17();
    await act(async () => {
      fireEvent.press(screen.getByTestId('s17-not-now'));
    });
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(false));
    expect(mockNotifications.requestPermissionsAsync).not.toHaveBeenCalled();
    await waitFor(async () => expect(await AsyncStorage.getItem(PREPROMPT_KEY)).not.toBeNull());
  });
});

describe('S69 U6 T3 \u2014 pre-prompt copy (EN + AR)', () => {
  const KEYS = [
    'notifications.prePrompt.title',
    'notifications.prePrompt.body',
    'notifications.prePrompt.allow',
    'notifications.prePrompt.notNow',
  ];
  const AR_DIACRITICS = /[\u064b-\u0652\u0670]/;
  const BRAND_AR = '\u0645\u064a\u0651\u0632'; // ميّز

  it('T3.15 every key exists in both catalogs and passes the copy rules', () => {
    for (const key of KEYS) {
      expect(typeof en[key]).toBe('string');
      expect(typeof ar[key]).toBe('string');
      expect(en[key].trim()).not.toBe('');
      expect(ar[key].trim()).not.toBe('');
      expect(en[key]).not.toMatch(/couldn['\u2019]?t|failed|try again/i);
      for (const { pattern } of policy.banned_en) expect(en[key]).not.toMatch(new RegExp(pattern));
      expect(ar[key].split(BRAND_AR).join('')).not.toMatch(AR_DIACRITICS);
      for (const term of policy.scary_vocab_ar) expect(ar[key]).not.toContain(term);
      for (const { pattern } of policy.banned_ar) expect(ar[key]).not.toContain(pattern);
    }
  });

  it('T3.16 the copy names MYEZ / \u0645\u064a\u0651\u0632, says it can be switched off in Profile, and promises no price drops', () => {
    const enText = `${en['notifications.prePrompt.title']} ${en['notifications.prePrompt.body']}`;
    const arText = `${ar['notifications.prePrompt.title']} ${ar['notifications.prePrompt.body']}`;
    expect(enText).toContain('MYEZ');
    expect(enText).not.toMatch(/Qaren/);
    expect(en['notifications.prePrompt.body']).toMatch(/Profile/);
    expect(enText).not.toMatch(/price/i);
    expect(arText).toContain(BRAND_AR);
    // The old brand قارن as a whole word (مقارنة 'comparison' contains it as a substring).
    expect(arText).not.toMatch(/(^|[^\u0600-\u06ff])\u0642\u0627\u0631\u0646([^\u0600-\u06ff]|$)/);
    expect(arText).not.toContain('\u0633\u0639\u0631'); // سعر (price)
    expect(arText).not.toContain('\u0623\u0633\u0639\u0627\u0631'); // أسعار (prices)
  });
});

describe('S69 U6 T3 \u2014 ResultsScreen wires the pre-prompt', () => {
  const src = fs.readFileSync(path.join(SRC, 'screens/ResultsScreen.tsx'), 'utf8');

  it('T3.17 imports shouldShowPushPrePrompt + PushPrePrompt and renders <PushPrePrompt', () => {
    expect(src).toMatch(
      /import\s*\{[^}]*\bshouldShowPushPrePrompt\b[^}]*\}\s*from\s*['"]\.\.\/services\/pushPrePrompt['"]/,
    );
    expect(src).toMatch(
      /import\s*\{[^}]*\bPushPrePrompt\b[^}]*\}\s*from\s*['"]\.\.\/components\/PushPrePrompt['"]/,
    );
    expect(src).toMatch(/<PushPrePrompt\b/);
  });

  it('T3.18 the gate passes the history origin and the demographics-sheet state', () => {
    const call = src.match(/shouldShowPushPrePrompt\(\s*\{([\s\S]*?)\}\s*\)/);
    expect(call).not.toBeNull();
    const ctx = call![1];
    expect(ctx).toMatch(/fromHistory\s*:/);
    expect(ctx).toMatch(/demographicsShown\s*:/);
  });
});
