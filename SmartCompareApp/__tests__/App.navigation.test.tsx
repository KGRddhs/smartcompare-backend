/**
 * Bundle D Task 1.F.3 — "Edit style profile" navigation registration.
 *
 * Verifies the contract that lets EditProfileScreen + ProfileScreen call
 * `navigation.navigate('Onboarding', { mode: 'edit', source: 'styleProfile' })`
 * from inside the post-auth stack without a silent no-op:
 *
 *   1. `RootStackParamList` declares the route + params shape.
 *   2. `NewOnboardingHost` accepts an optional `mode` prop ('full' | 'edit')
 *      and an optional `onEditDone` callback for the edit-mode close path.
 *   3. App.tsx wires the Onboarding screen permanently in the authed branch
 *      (not just behind the `needsPreferences` gate), so re-entry works
 *      after preferences are already saved.
 *
 * Pure-static checks — no React renderer needed; this guards the
 * compile-time + module-export surface so the runtime no-op can't recur.
 */

import type { RootStackParamList } from '../src/types/types';

describe('Bundle D 1.F.3 — Edit style profile navigation contract', () => {
  it('declares the Onboarding route in RootStackParamList', () => {
    const route: keyof RootStackParamList = 'Onboarding';
    expect(route).toBe('Onboarding');
  });

  it('accepts { mode: "edit", source: "styleProfile" } params', () => {
    const params: RootStackParamList['Onboarding'] = {
      mode: 'edit',
      source: 'styleProfile',
    };
    expect(params?.mode).toBe('edit');
    expect(params?.source).toBe('styleProfile');
  });

  it('NewOnboardingHost exposes a `mode` prop and `onEditDone` close hook', () => {
    // Static source-grep — runtime require pulls i18n init which is not
    // module-safe in the jest node env. The contract is a Props surface,
    // so the static check is the right granularity for this gate.
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const fs = require('fs');
    const src: string = fs.readFileSync(
      require('path').resolve(
        __dirname,
        '../src/screens/onboarding/NewOnboardingHost.tsx'
      ),
      'utf8'
    );
    expect(src).toMatch(/mode\?:\s*'full'\s*\|\s*'edit'/);
    expect(src).toMatch(/onEditDone\?:\s*\(\)\s*=>\s*void/);
  });

  it('App.tsx source registers an Onboarding screen permanently in the authed branch', () => {
    // We grep the source rather than rendering — the App.tsx render tree
    // is gated behind auth + Stack.Navigator wiring that's heavy to mock.
    // The contract surfaced here is: the string "Onboarding" must appear
    // in the authed branch alongside EditProfile/EditPreferences.
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const fs = require('fs');
    const src: string = fs.readFileSync(
      require('path').resolve(__dirname, '../App.tsx'),
      'utf8'
    );
    // Two occurrences of the screen name expected — once in the
    // needs-preferences branch (fresh signup) and once in the authed
    // branch (re-entry for edit). If only one match, the re-entry path
    // is still broken.
    const matches = (src.match(/name="Onboarding"/g) || []).length;
    expect(matches).toBeGreaterThanOrEqual(2);
  });
});
