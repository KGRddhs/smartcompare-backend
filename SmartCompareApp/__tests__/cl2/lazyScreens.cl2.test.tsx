/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R30-R32, P9, P10 (spec section 5 as amended
 * by RULINGS_S81_G6 R-G6-1): the lazy FIVE (Onboarding, NewOnboardingHost,
 * ScanCamera, InviteeQuiz, ReferralLanding) through
 * src/navigation/lazyScreen.tsx; Legal and Paywall STAY EAGER (15 eager
 * static screen imports). The Suspense fallback is one full-screen View in
 * the theme background colour: no Text, no string.
 *
 * lazyScreen.tsx does not exist at base: it is read through loadOptional and
 * asserted.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, act } from '@testing-library/react-native';

function loadOptional(rel: string): any {
  try {
    return require(rel);
  } catch {
    return null;
  }
}

const ROOT = path.resolve(__dirname, '../..');
const APP = fs.readFileSync(path.join(ROOT, 'App.tsx'), 'utf8').replace(/\r\n/g, '\n');
const MOD = '../../src/navigation/lazyScreen';

const LAZY: [string, string][] = [
  ['OnboardingScreen', './src/screens/OnboardingScreen'],
  ['NewOnboardingHost', './src/screens/onboarding/NewOnboardingHost'],
  ['ScanCameraScreen', './src/screens/ScanCameraScreen'],
  ['InviteeQuizScreen', './src/screens/InviteeQuizScreen'],
  ['ReferralLandingScreen', './src/screens/ReferralLandingScreen'],
];

const EAGER: [string, string][] = [
  ['SplashScreen', './src/screens/SplashScreen'],
  ['LoginScreen', './src/screens/LoginScreen'],
  ['RegisterScreen', './src/screens/RegisterScreen'],
  ['ForgotPasswordScreen', './src/screens/ForgotPasswordScreen'],
  ['ResetPasswordScreen', './src/screens/ResetPasswordScreen'],
  ['HomeScreen', './src/screens/HomeScreen'],
  ['ResultsScreen', './src/screens/ResultsScreen'],
  ['LegalScreen', './src/screens/LegalScreen'],
  ['ContactUsScreen', './src/screens/ContactUsScreen'],
  ['EditProfileScreen', './src/screens/EditProfileScreen'],
  ['EditPreferencesFlow', './src/screens/EditPreferencesFlow'],
  ['HistoryScreen', './src/screens/HistoryScreen'],
  ['ProfileScreen', './src/screens/ProfileScreen'],
  ['PaywallScreen', './src/screens/PaywallScreen'],
  ['UpdateRequiredScreen', './src/screens/UpdateRequiredScreen'],
];

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');

function staticImportOf(spec: string): RegExp {
  return new RegExp("^import\\s[^;]*from\\s+'" + esc(spec) + "';", 'm');
}

function hostTexts(tree: any): string[] {
  const out: string[] = [];
  const walk = (node: any) => {
    if (node == null) return;
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    if (typeof node === 'string') {
      out.push(node);
      return;
    }
    if (node.type === 'Text') out.push('<Text>');
    walk(node.children);
  };
  walk(tree);
  return out;
}

function flatStyle(style: any): any {
  if (Array.isArray(style)) return Object.assign({}, ...style.map(flatStyle));
  return style || {};
}

class Boundary extends React.Component<{ onError: (e: unknown) => void; children?: any }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: unknown) {
    this.props.onError(error);
  }

  render() {
    return this.state.failed ? null : this.props.children;
  }
}

describe('CL2 lazy screens (C6)', () => {
  it('R30 the five lazy screens: no static import, each bound through lazyScreen(() => import(...))', () => {
    expect(APP).toMatch(/import \{\s*lazyScreen\s*\} from '\.\/src\/navigation\/lazyScreen';/);
    const stillStatic = LAZY.filter(([, spec]) => staticImportOf(spec).test(APP)).map(([n]) => n);
    expect(stillStatic).toEqual([]);
    const unbound = LAZY.filter(
      ([name, spec]) =>
        !new RegExp(
          // An explicit type argument (lazyScreen<Props>(...)) is allowed.
          'const\\s+' + name + '\\s*=\\s*lazyScreen(?:<[^>()]*>)?\\(\\s*\\(\\)\\s*=>\\s*import\\(\\s*\'' + esc(spec) + "'\\s*\\)"
        ).test(APP)
    ).map(([n]) => n);
    expect(unbound).toEqual([]);
  });

  it('R31 the helper renders a host-text-free background View, then the screen with the same props', async () => {
    const mod = loadOptional(MOD);
    expect(mod).not.toBeNull();
    expect(typeof mod.lazyScreen).toBe('function');
    const { colors } = require('../../src/theme');
    const { Text } = require('react-native');
    let resolveLoad: (m: any) => void = () => undefined;
    const loader = () =>
      new Promise<any>((resolve) => {
        resolveLoad = resolve;
      });
    const Screen = mod.lazyScreen(loader);
    const Loaded = (props: any) => React.createElement(Text, { testID: 'cl2-loaded' }, 'p=' + props.marker);
    const rendered = render(React.createElement(Screen, { marker: 'm-1' }));
    const before = rendered.toJSON();
    expect(hostTexts(before)).toEqual([]);
    const views = rendered.UNSAFE_root.findAll((n: any) => n.type === 'View');
    expect(views.length).toBeGreaterThan(0);
    expect(flatStyle(views[0].props.style).backgroundColor).toBe(colors.bg.primary);
    await act(async () => {
      resolveLoad({ default: Loaded });
    });
    expect(rendered.getByTestId('cl2-loaded').props.children).toBe('p=m-1');
  });

  it('R32 a rejecting loader reaches an error boundary; the helper adds no Text', async () => {
    const mod = loadOptional(MOD);
    expect(mod).not.toBeNull();
    const seen: unknown[] = [];
    const spy = jest.spyOn(console, 'error').mockImplementation(() => undefined);
    try {
      const Screen = mod.lazyScreen(() => Promise.reject(new Error('synthetic load failure')));
      const rendered = render(
        React.createElement(Boundary, { onError: (e: unknown) => seen.push(e) }, React.createElement(Screen, {}))
      );
      await act(async () => {
        await Promise.resolve();
        await new Promise<void>((resolve) => setImmediate(resolve));
      });
      expect(seen.length).toBe(1);
      expect(String((seen[0] as Error).message)).toBe('synthetic load failure');
      expect(hostTexts(rendered.toJSON())).toEqual([]);
    } finally {
      spy.mockRestore();
    }
  });

  it('P9 index.ts first import is the Sentry bootstrap', () => {
    const idx = fs.readFileSync(path.join(ROOT, 'index.ts'), 'utf8').replace(/\r\n/g, '\n');
    const firstImport = idx.split('\n').find((line) => /^import\s/.test(line));
    expect(firstImport).toBe("import './src/services/sentryBootstrap';");
  });

  it('P10 the 15 eager screens stay static imports (Legal and Paywall included)', () => {
    const missing = EAGER.filter(([, spec]) => !staticImportOf(spec).test(APP)).map(([n]) => n);
    expect(missing).toEqual([]);
    expect(EAGER.length).toBe(15);
  });
});
