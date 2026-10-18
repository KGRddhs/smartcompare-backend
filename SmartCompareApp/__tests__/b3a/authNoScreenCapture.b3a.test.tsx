/**
 * S79 B3-A item 1 -- no screen-capture block on the auth screens (spec C1,
 * rows R1-R5; ruling A12: MR2 widened scan + render rows for all four
 * screens, MR3 render-level secureTextEntry).
 */
/* eslint-disable @typescript-eslint/no-require-imports */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, act } from '@testing-library/react-native';

const APP = path.resolve(__dirname, '../..');

jest.mock('react-native-reanimated', () => {
  const RealReact = require('react');
  const passthrough = ({ children, ...props }: any) => RealReact.createElement('mock-Animated-View', props, children);
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
    Easing: { inOut: () => (t: number) => t, out: () => (t: number) => t, ease: (t: number) => t, cubic: (t: number) => t },
  };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: 'en', changeLanguage: jest.fn() } }),
}));

jest.mock('expo-screen-capture', () => ({ usePreventScreenCapture: jest.fn() }));

jest.mock('../../src/services/authService', () => ({
  login: jest.fn(),
  register: jest.fn(),
  requestPasswordReset: jest.fn(),
  completePasswordRecovery: jest.fn(),
  signInWithGoogle: jest.fn(),
  signInWithApple: jest.fn(),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(false),
  getToken: jest.fn().mockResolvedValue(null),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
}));

jest.mock('../../src/services/api', () => ({
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

const { usePreventScreenCapture } = require('expo-screen-capture');

const SCREENS = {
  Login: 'src/screens/LoginScreen.tsx',
  Register: 'src/screens/RegisterScreen.tsx',
  ForgotPassword: 'src/screens/ForgotPasswordScreen.tsx',
  ResetPassword: 'src/screens/ResetPasswordScreen.tsx',
};
const read = (rel: string) => fs.readFileSync(path.join(APP, rel), 'utf8').replace(/\r\n/g, '\n');

function sourceFiles(dir: string, out: string[] = []): string[] {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) sourceFiles(p, out);
    else if (/\.(ts|tsx)$/.test(e.name)) out.push(p);
  }
  return out;
}

/** Any module specifier naming expo-screen-capture (or a deep subpath). */
const SPECIFIER =
  /(?:\bfrom\s*|\brequire\s*\(\s*|\bimport\s*\(\s*|\bimport\s+)['"`]expo-screen-capture(?:\/[^'"`]*)?['"`]/;

function nav(): any {
  return { navigate: jest.fn(), goBack: jest.fn(), reset: jest.fn(), canGoBack: () => false, getParent: () => ({ navigate: jest.fn() }) };
}

async function mount(name: keyof typeof SCREENS) {
  const mod = require(path.join(APP, SCREENS[name]));
  const C = mod.default;
  let s: any;
  if (name === 'Login') s = render(<C navigation={nav()} onLoginSuccess={jest.fn()} />);
  else if (name === 'Register')
    s = render(<C navigation={nav()} route={{ params: undefined }} onRegisterSuccess={jest.fn()} />);
  else s = render(<C navigation={nav()} />);
  await act(async () => {
    await Promise.resolve();
  });
  return s;
}

function secureInputs(json: any): number {
  let n = 0;
  const walk = (x: any) => {
    if (x == null || typeof x !== 'object') return;
    if (Array.isArray(x)) return x.forEach(walk);
    if (x.type === 'TextInput' && x.props?.secureTextEntry === true) n += 1;
    walk(x.children);
  };
  walk(json);
  return n;
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('B3-A no screen-capture block (C1)', () => {
  it('r1 the four auth screens neither import nor call expo-screen-capture', () => {
    const bad: string[] = [];
    for (const [name, rel] of Object.entries(SCREENS)) {
      const src = read(rel);
      if (SPECIFIER.test(src)) bad.push(`${name}:import`);
      for (const call of ['usePreventScreenCapture(', 'preventScreenCaptureAsync(', 'enableAppSwitcherProtectionAsync(']) {
        if (src.includes(call)) bad.push(`${name}:${call}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it('r2 no file under src/, App.tsx or index.ts names expo-screen-capture in an import, require or dynamic import', () => {
    const files = [...sourceFiles(path.join(APP, 'src')), path.join(APP, 'App.tsx'), path.join(APP, 'index.ts')];
    const hits = files
      .filter((f) => fs.existsSync(f))
      .filter((f) => SPECIFIER.test(fs.readFileSync(f, 'utf8')))
      .map((f) => path.relative(APP, f).replace(/\\/g, '/'));
    expect(hits).toEqual([]);
  });

  it('r3 [PIN] password fields keep secureTextEntry (source counts)', () => {
    const count = (rel: string) => (read(rel).match(/secureTextEntry/g) ?? []).length;
    expect(count(SCREENS.Login)).toBeGreaterThanOrEqual(1);
    expect(count(SCREENS.Register)).toBeGreaterThanOrEqual(2);
    expect(count(SCREENS.ResetPassword)).toBeGreaterThanOrEqual(2);
  });

  it('r3b [PIN] (MR3) the rendered password inputs carry secureTextEntry: true', async () => {
    expect(secureInputs((await mount('Login')).toJSON())).toBeGreaterThanOrEqual(1);
    expect(secureInputs((await mount('Register')).toJSON())).toBeGreaterThanOrEqual(2);
    require('../../src/services/passwordRecoveryLink').setPendingRecovery({ accessToken: 'tok' });
    expect(secureInputs((await mount('ResetPassword')).toJSON())).toBeGreaterThanOrEqual(2);
  });

  it('r4 [PIN] the dependency stays', () => {
    const pkg = JSON.parse(fs.readFileSync(path.join(APP, 'package.json'), 'utf8'));
    expect(pkg.dependencies['expo-screen-capture']).toBe('~8.0.10');
  });

  it('r5 ResetPasswordScreen mounts without arming capture protection', async () => {
    await mount('ResetPassword');
    expect(usePreventScreenCapture).not.toHaveBeenCalled();
  });

  it.each(['Login', 'Register', 'ForgotPassword'] as const)(
    'r5b (MR2) %s mounts without arming capture protection',
    async (name) => {
      await mount(name);
      expect(usePreventScreenCapture).not.toHaveBeenCalled();
    },
  );
});
