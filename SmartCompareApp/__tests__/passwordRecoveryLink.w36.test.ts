/**
 * W3-6 — `src/services/passwordRecoveryLink.ts`: the pure parser for a
 * Supabase recovery deep link, plus the module-scoped slot that carries the
 * access token from the linking layer to the ResetPassword screen.
 *
 * Finding MB-FLOWS-STATE-02: a password reset cannot be completed by any
 * email/password user — there is no recovery route and no set-new-password
 * screen anywhere in the app.
 *
 * Why a slot and not a route param (measured, §10 M4 / probe P4): the
 * recovery token arrives in the URL FRAGMENT, and the installed
 * @react-navigation/core 7.17.4 splits a path on `?` only
 * (`getStateFromPath.tsx:749-750`, zero occurrences of `#`/`fragment`/`hash`
 * in the file). Forwarding the fragment as a QUERY instead would match the
 * route but writes `access_token` into `routes[].params` AND `routes[].path`
 * of the navigation state — i.e. into anything that serialises navigation
 * state. So the tokens are parked in process memory and the path is
 * rewritten to the bare `reset-password`.
 *
 * The token is a live credential for its ~1 h TTL: this module must never
 * log it, must never retain the refresh token (the backend half needs only
 * the access token), and `consume` must clear on read.
 */

import * as fs from 'fs';
import * as path from 'path';

import {
  parseRecoveryLink,
  setPendingRecovery,
  consumePendingRecovery,
  __resetPendingRecoveryForTests,
} from '../src/services/passwordRecoveryLink';

beforeEach(() => {
  __resetPendingRecoveryForTests();
});

describe('parseRecoveryLink — accepts a real recovery link', () => {
  it('parses the FRAGMENT form GoTrue emits for an implicit-flow recovery', () => {
    // reset_password_for_email sends no code_challenge (measured on the
    // installed supabase-auth: `"code_challenge" in source` -> False), so the
    // link is implicit-flow and the session lands in the fragment.
    expect(
      parseRecoveryLink(
        'reset-password#access_token=tok-SECRET-1&expires_in=3600&refresh_token=rt-1&token_type=bearer&type=recovery',
      ),
    ).toEqual({ accessToken: 'tok-SECRET-1' });
  });

  it('parses the QUERY form too (the shape is GoTrue server behaviour, unmeasured offline)', () => {
    expect(
      parseRecoveryLink('reset-password?access_token=tok-SECRET-2&type=recovery'),
    ).toEqual({ accessToken: 'tok-SECRET-2' });
  });

  it('tolerates the leading slash extractPathFromURL can leave on the path', () => {
    expect(
      parseRecoveryLink('/reset-password#access_token=tok-SECRET-3&type=recovery'),
    ).toEqual({ accessToken: 'tok-SECRET-3' });
  });

  it('returns EXACTLY one key — the refresh token is discarded, never retained', () => {
    const parsed = parseRecoveryLink(
      'reset-password#access_token=tok-SECRET-4&refresh_token=rt-MUST-NOT-BE-KEPT&type=recovery',
    );
    expect(parsed).not.toBeNull();
    expect(Object.keys(parsed as object)).toEqual(['accessToken']);
    expect(JSON.stringify(parsed)).not.toContain('rt-MUST-NOT-BE-KEPT');
  });
});

describe('parseRecoveryLink — refuses everything else', () => {
  it('returns null when `type` is absent', () => {
    expect(parseRecoveryLink('reset-password#access_token=tok')).toBeNull();
  });

  it('returns null when `type` is not `recovery` (a signup link is not a reset)', () => {
    expect(parseRecoveryLink('reset-password#access_token=tok&type=signup')).toBeNull();
  });

  it('returns null when `access_token` is empty', () => {
    expect(parseRecoveryLink('reset-password#access_token=&type=recovery')).toBeNull();
  });

  it('returns null when `access_token` is absent', () => {
    expect(parseRecoveryLink('reset-password#type=recovery')).toBeNull();
  });

  it("returns null for GoTrue's expired-link error redirect", () => {
    expect(
      parseRecoveryLink(
        'reset-password#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid+or+has+expired',
      ),
    ).toBeNull();
  });

  it('returns null when the first segment is not EXACTLY `reset-password`', () => {
    expect(
      parseRecoveryLink('reset-passwordx#access_token=tok&type=recovery'),
    ).toBeNull();
    expect(
      parseRecoveryLink('r/reset-password#access_token=tok&type=recovery'),
    ).toBeNull();
    expect(
      parseRecoveryLink('reset-password/extra#access_token=tok&type=recovery'),
    ).toBeNull();
  });

  it('returns null for the bare path with no parameters at all', () => {
    expect(parseRecoveryLink('reset-password')).toBeNull();
  });
});

describe('the pending-recovery slot', () => {
  it('consume returns what was set, then null — the token dies on first read', () => {
    setPendingRecovery({ accessToken: 'tok-SECRET-5' });
    expect(consumePendingRecovery()).toEqual({ accessToken: 'tok-SECRET-5' });
    expect(consumePendingRecovery()).toBeNull();
  });

  it('consume on an untouched slot is null', () => {
    expect(consumePendingRecovery()).toBeNull();
  });

  it('__resetPendingRecoveryForTests clears a set slot', () => {
    setPendingRecovery({ accessToken: 'tok-SECRET-6' });
    __resetPendingRecoveryForTests();
    expect(consumePendingRecovery()).toBeNull();
  });
});

describe('the module never emits the token anywhere', () => {
  const SOURCE = fs.readFileSync(
    path.join(__dirname, '..', 'src', 'services', 'passwordRecoveryLink.ts'),
    'utf8',
  );

  // Strip block + line comments so prose about logging cannot satisfy or
  // trip the scan.
  const CODE = SOURCE.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');

  it('contains no console call', () => {
    expect(CODE).not.toMatch(/console\s*\./);
  });

  it('contains no Sentry breadcrumb and no analytics call', () => {
    expect(CODE).not.toMatch(/Sentry/);
    expect(CODE).not.toMatch(/trackEvent/);
  });
});
