/**
 * M18 MB-flows-02 — a session cleared from non-UI code must route the
 * app back to the Auth stack.
 *
 * `setIsAuthenticated(false)` previously lived ONLY in handleLogout
 * (user-initiated: History/Profile sign-out + account deletion), so a
 * clearSession() fired by the 401 interceptor left MainTabs mounted
 * with no token: every compare alert-failed, every history row opened
 * empty, and ResultsScreen's "interceptor handles refresh/redirect"
 * comment pointed at a redirect that did not exist.
 *
 * Two layers pinned here:
 *   1. The sessionEvents channel itself (unit).
 *   2. App.tsx subscribes to it and downgrades auth state (static
 *      source contract — the App render tree is heavy to mock; this
 *      repo's App.* tests use the same source-grep granularity, see
 *      App.navigation.test.tsx).
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  onSessionInvalid,
  emitSessionInvalid,
  __resetSessionListeners,
} from '../src/services/sessionEvents';

describe('sessionEvents — pub/sub unit (M18 MB-flows-02)', () => {
  beforeEach(() => {
    __resetSessionListeners();
  });

  it('notifies a subscribed listener on emit', () => {
    const listener = jest.fn();
    onSessionInvalid(listener);

    emitSessionInvalid();

    expect(listener).toHaveBeenCalledTimes(1);
  });

  it('stops notifying after unsubscribe', () => {
    const listener = jest.fn();
    const unsubscribe = onSessionInvalid(listener);
    unsubscribe();

    emitSessionInvalid();

    expect(listener).not.toHaveBeenCalled();
  });

  it('a throwing listener never blocks the others', () => {
    const bad = jest.fn(() => {
      throw new Error('listener-boom');
    });
    const good = jest.fn();
    onSessionInvalid(bad);
    onSessionInvalid(good);

    expect(() => emitSessionInvalid()).not.toThrow();
    expect(good).toHaveBeenCalledTimes(1);
  });

  it('emit with no listeners is a no-op', () => {
    expect(() => emitSessionInvalid()).not.toThrow();
  });
});

describe('App.tsx — session-invalid wiring (static source contract)', () => {
  const appSrc: string = fs.readFileSync(
    path.resolve(__dirname, '../App.tsx'),
    'utf8',
  );

  it('imports onSessionInvalid from the sessionEvents service', () => {
    expect(appSrc).toMatch(
      /import\s*\{[^}]*onSessionInvalid[^}]*\}\s*from\s*'\.\/src\/services\/sessionEvents'/,
    );
  });

  it('subscribes and downgrades auth state inside the subscription', () => {
    // The subscription callback must flip the SAME trio handleLogout
    // flips, so a dead session lands on the Auth stack.
    const subscription = appSrc.match(
      /onSessionInvalid\(\(\)\s*=>\s*\{[\s\S]*?\}\)/,
    );
    expect(subscription).not.toBeNull();
    expect(subscription![0]).toContain('setIsAuthenticated(false)');
    expect(subscription![0]).toContain('setNeedsPreferences(false)');
    expect(subscription![0]).toContain('setUser(null)');
  });

  it('cleans the subscription up (unsubscribe returned from the effect)', () => {
    // The effect must return the unsubscribe function so a remounted
    // root never stacks dead listeners.
    expect(appSrc).toMatch(/const\s+unsubscribe\s*=\s*onSessionInvalid\(/);
    expect(appSrc).toMatch(/return\s+unsubscribe;/);
  });
});

describe('api.ts — emit sites (static source contract)', () => {
  const apiSrc: string = fs.readFileSync(
    path.resolve(__dirname, '../src/services/api.ts'),
    'utf8',
  );

  it('performRefresh emits session-invalid where it clears the session', () => {
    expect(apiSrc).toMatch(/emitSessionInvalid/);
  });
});
