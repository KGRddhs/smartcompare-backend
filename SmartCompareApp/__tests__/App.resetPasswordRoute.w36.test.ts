/**
 * W3-6 — the ResetPassword screen must actually be REGISTERED in the
 * unauthenticated Auth stack, and its route name must exist in
 * `AuthStackParamList`.
 *
 * Source-scanned rather than rendered: importing `App.tsx` drags in fonts,
 * Sentry and ~20 screens, which every existing `App.*.test` deliberately
 * avoids (see `App.referral.test.tsx`). `App.distinctRouteNames.test.ts`
 * scans `<Stack\.Screen` only — `<AuthStack.Screen` is outside its regex, so
 * the new registration needs its own pin.
 *
 * Measured at base: `grep -n -i "reset-password\|ResetPassword\|recovery"
 * SmartCompareApp/App.tsx` returns nothing at all.
 */

import * as fs from 'fs';
import * as path from 'path';

import type { AuthStackParamList } from '../src/types/types';

const APP = fs.readFileSync(path.join(__dirname, '..', 'App.tsx'), 'utf8');

describe('AuthNavigator registers the ResetPassword screen', () => {
  it('declares <AuthStack.Screen name="ResetPassword" …>', () => {
    expect(APP).toMatch(/<AuthStack\.Screen\s+name=["']ResetPassword["']/);
  });

  it('imports the screen component', () => {
    expect(APP).toMatch(
      /import\s+ResetPasswordScreen\s+from\s+['"]\.\/src\/screens\/ResetPasswordScreen['"]/,
    );
  });
});

describe('the linking config knows the reset-password path', () => {
  // This node lives here rather than in linking.resetPassword.w36.test.ts so
  // it RUNS on today's tree: that suite cannot even load until
  // src/navigation/linking.ts exists, so its reds would all be import
  // failures. Measured at base: `grep -n reset-password App.tsx` -> nothing.
  it('App.tsx declares the reset-password path or imports the extracted linking module', () => {
    const declaresPath = /reset-password/.test(APP);
    const importsModule = /from\s+['"]\.\/src\/navigation\/linking['"]/.test(APP);
    expect(declaresPath || importsModule).toBe(true);
  });
});

describe('AuthStackParamList declares the route', () => {
  it('accepts ResetPassword as a key (compile-time — this line fails tsc until the key exists)', () => {
    const k: keyof AuthStackParamList = 'ResetPassword';
    expect(k).toBe('ResetPassword');
  });
});
