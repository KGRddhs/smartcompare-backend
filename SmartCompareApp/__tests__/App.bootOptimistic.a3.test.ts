/**
 * A3 — App.tsx's half of the optimistic boot (static source contract).
 *
 * The render tree is gated on `isLoading`, which `init()` flips false
 * only after the auth check returns. authService now returns the CACHED
 * user immediately and refreshes in the background (pinned behaviourally
 * in authService.bootOptimistic.a3.test.ts); App.tsx's remaining job is
 * to re-sync when that background refresh lands, without ever throwing a
 * user back into onboarding on a late server read.
 *
 * Source-grep granularity matches this repo's other App.* suites
 * (App.sessionInvalid.m18.test.ts, App.navigation.test.tsx) — the root
 * component pulls in the whole navigator + font stack to render.
 */

import * as fs from 'fs';
import * as path from 'path';

const appSrc: string = fs.readFileSync(
  path.resolve(__dirname, '../App.tsx'),
  'utf8',
);

describe('App.tsx — boot re-sync wiring (A3)', () => {
  it('hands initializeAuth a callback for the background refresh result', () => {
    // A bare `initializeAuth()` means the boot has no way to pick up the
    // refreshed user — the state it rendered from would stay stale for
    // the whole session.
    expect(appSrc).toMatch(/await\s+initializeAuth\(\s*\(/);
  });

  it('the callback re-applies the refreshed user', () => {
    const callback = appSrc.match(
      /initializeAuth\(\s*\(\s*\w+\s*\)\s*=>\s*\{[\s\S]*?\n\s*\}\)/,
    );
    expect(callback).not.toBeNull();
    expect(callback![0]).toMatch(/setUser\(\s*\w+\s*\)/);
  });

  it('the callback only ever LOWERS the onboarding gate', () => {
    // `setNeedsPreferences(!user.preferences_completed)` here would let a
    // late/stale server read shove a user who is mid-onboarding (or who
    // just finished it) back into the onboarding stack.
    const callback = appSrc.match(
      /initializeAuth\(\s*\(\s*\w+\s*\)\s*=>\s*\{[\s\S]*?\n\s*\}\)/,
    );
    expect(callback).not.toBeNull();
    expect(callback![0]).toContain('setNeedsPreferences(false)');
    expect(callback![0]).not.toMatch(/setNeedsPreferences\(\s*!/);
  });

  it('still releases the splash gate after the auth check', () => {
    // The whole point of the finding: `isLoading` must reach false on a
    // boot that never got a refresh answer.
    expect(appSrc).toContain('setIsLoading(false)');
    expect(appSrc).toMatch(/if\s*\(!fontsLoaded\s*\|\|\s*isLoading\s*\|\|\s*showSplash\)/);
  });

  it('keeps the session-death route back to Auth subscribed', () => {
    // The optimistic boot leans on this listener: a definitively dead
    // session now surfaces AFTER Main has rendered.
    expect(appSrc).toMatch(/onSessionInvalid\(\(\)\s*=>\s*\{/);
  });
});
