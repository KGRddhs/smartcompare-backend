/**
 * W3-6 — the recovery deep link must resolve to `Auth > ResetPassword`
 * WITHOUT ever putting the access token into navigation state.
 *
 * Finding MB-FLOWS-STATE-02 ("Password reset is unrecoverable: the app has
 * no recovery deep link or set-new-password screen anywhere").
 *
 * This suite runs the REAL parser. `getStateFromPath` is
 * `jest.requireActual`'d from the installed @react-navigation/core TSX
 * SOURCE (7.17.4): the published package is ESM-only `lib/module` with an
 * `exports` map that blocks deep imports, which is why jest.config.js
 * carries `@react-navigation` in `transformIgnorePatterns`. A hand-written
 * fake parser would prove nothing here — the whole defect is about what the
 * REAL parser does with a `#fragment` (measured: `getStateFromPath.tsx:749`
 * splits on `?` only; the file contains no `#`/`fragment`/`hash` handling at
 * all), so the fix has to be verified against it.
 *
 * Measured at base (probe P2): today's config returns `undefined` for
 * `reset-password#access_token=…&type=recovery` — the link the backend would
 * emit lands nowhere and the app simply opens.
 */

/* eslint-disable import/first --
   the jest.mock factory is written ABOVE the imports deliberately: the real
   @react-navigation/native is ESM-only and must never be loaded, so the
   ordering is made explicit here rather than left to transformer hoisting. */

jest.mock('@react-navigation/native', () => ({
  __esModule: true,
  getStateFromPath: jest.requireActual(
    '../node_modules/@react-navigation/core/src/getStateFromPath',
  ).getStateFromPath,
}));

import { linking } from '../src/navigation/linking';
import {
  consumePendingRecovery,
  __resetPendingRecoveryForTests,
} from '../src/services/passwordRecoveryLink';

/** Walk the focused route chain, as the probe does. */
function focused(state: any): string[] {
  const names: string[] = [];
  let s = state;
  while (s && s.routes && s.routes.length) {
    const r = s.routes[s.index ?? s.routes.length - 1];
    names.push(r.name);
    s = r.state;
  }
  return names;
}

/** Call the app's OWN override, exactly as useLinking.native.tsx:133 does. */
function resolve(p: string): any {
  return (linking as any).getStateFromPath(p, linking.config);
}

beforeEach(() => {
  __resetPendingRecoveryForTests();
});

describe('a recovery link resolves to the ResetPassword screen', () => {
  const RECOVERY =
    'reset-password#access_token=tok-SECRET-1&refresh_token=rt-SECRET-1&expires_in=3600&token_type=bearer&type=recovery';

  it('names Auth > ResetPassword', () => {
    expect(focused(resolve(RECOVERY))).toEqual(['Auth', 'ResetPassword']);
  });

  it('keeps the token OUT of navigation state and parks it in the slot instead', () => {
    const state = resolve(RECOVERY);

    // Nothing that serialises navigation state may carry the credential.
    expect(JSON.stringify(state)).not.toContain('tok-SECRET-1');
    expect(JSON.stringify(state)).not.toContain('rt-SECRET-1');
    const leaf = state.routes[state.routes.length - 1].state.routes[0];
    expect(leaf.params).toBeUndefined();

    // The slot carries the access token, and ONLY the access token.
    const pending = consumePendingRecovery();
    expect(pending).toEqual({ accessToken: 'tok-SECRET-1' });
    expect(Object.keys(pending as object)).toEqual(['accessToken']);
  });

  it('the slot is consumed once — a second read is null', () => {
    resolve(RECOVERY);
    expect(consumePendingRecovery()).not.toBeNull();
    expect(consumePendingRecovery()).toBeNull();
  });
});

describe('a reset-password link that carries no usable token still reaches the screen', () => {
  // The screen's empty-slot branch renders "this link is no longer valid" +
  // request-a-new-one. Falling through to the default parser instead would
  // return `undefined` (probe P3) and the app would open on Login with no
  // message at all — which is the single most common reset failure
  // (GoTrue redirects an expired/used link to
  // `#error=access_denied&error_code=otp_expired`).
  const CASES: [string, string][] = [
    ['a signup link', 'reset-password#access_token=x-SIGNUP&type=signup'],
    ['a recovery link with no token', 'reset-password#type=recovery'],
    [
      'the expired-link error redirect',
      'reset-password#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid+or+has+expired',
    ],
  ];

  it.each(CASES)('%s still names Auth > ResetPassword with an EMPTY slot', (_label, url) => {
    const state = resolve(url);
    expect(focused(state)).toEqual(['Auth', 'ResetPassword']);
    expect(consumePendingRecovery()).toBeNull();
  });

  it('a signup token is never parked in the slot and never enters the state', () => {
    const state = resolve('reset-password#access_token=x-SIGNUP&type=signup');
    expect(consumePendingRecovery()).toBeNull();
    expect(JSON.stringify(state)).not.toContain('x-SIGNUP');
  });
});

describe('preserve — the existing deep links resolve exactly as before the move', () => {
  it('redeem?code= is still rewritten to Register with an upper-cased code', () => {
    const state = resolve('redeem?code=qr-abc123');
    expect(focused(state)).toEqual(['Auth', 'Register']);
    const leaf = state.routes[state.routes.length - 1].state.routes[0];
    expect(leaf.params.code).toBe('QR-ABC123');
  });

  it('r/:code still resolves to Register with an upper-cased code', () => {
    const state = resolve('r/qr-abc123');
    expect(focused(state)).toEqual(['Auth', 'Register']);
    const leaf = state.routes[state.routes.length - 1].state.routes[0];
    expect(leaf.params.code).toBe('QR-ABC123');
  });

  it('c/:share_token still resolves to ReferralLanding', () => {
    const state = resolve('c/tok');
    expect(focused(state)).toEqual(['ReferralLanding']);
    expect(state.routes[0].params.share_token).toBe('tok');
  });

  it('q/:share_token still resolves to InviteeQuiz', () => {
    expect(focused(resolve('q/tok'))).toEqual(['InviteeQuiz']);
  });

  it('both prefixes survive the move — the universal-link prefix is not dropped', () => {
    expect(linking.prefixes).toEqual(['qaren://', 'https://qaren.app']);
  });
});
