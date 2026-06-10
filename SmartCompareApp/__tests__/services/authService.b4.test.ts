/**
 * B4 regression test — Google sign-in body shape (FINAL post-resolution).
 *
 * PRE-CLEANUP-STATE: tests RED against `main` until B4 cleanup commit
 * lands (revert of 8d1444e). On the `feature/bundle-e-visual-fidelity`
 * worktree branch this test ships on, the simple body shape is already in
 * place (no decode block) — tests are GREEN here today and will STAY
 * GREEN once main rebases / merges to include the revert.
 *
 * RESOLUTION
 * B4 was the "Nonces mismatch" Supabase error that fired every Google
 * sign-in. Three iterations chased this bug:
 *
 *   1. PRE-Path-A   — FE generated random nonce + sent to Supabase, but
 *                     Google iOS SDK did NOT bind it into id_token.nonce.
 *                     Parity failed.
 *   2. Path A R1    — Drop the FE nonce entirely. Failed because
 *                     @react-native-google-signin auto-embeds its own
 *                     internal nonce claim into the id_token. Parity
 *                     failed the other direction.
 *   3. ECHO (8d1444e)— Decode id_token payload, read .nonce claim, echo
 *                     to backend. Failed because Supabase computes
 *                     SHA-256(echoed_value) and compares to the claim
 *                     (which IS already the hash) — hash-of-hash mismatch.
 *
 * RESOLUTION (2026-05-26): Ahmed toggled "Skip nonce checks" in
 * Supabase dashboard → Auth → Providers → Google. Verified by device
 * walkthrough: sign-in works + Step 17 Finish lands in Home tab.
 *
 * With nonce checks skipped server-side, the FE has no nonce work to do.
 * The decode block in commit 8d1444e becomes dead code — team-lead will
 * revert that commit. The final FE state is:
 *
 *     const body = { provider: 'google', id_token: idToken };
 *
 * INVARIANT THIS TEST PINS
 * `body.nonce` MUST NEVER be present in the POST to /auth/social-login for
 * `provider='google'`, regardless of what's in the id_token payload. The
 * FE can't bind a known raw value (Google iOS SDK has no nonce param), and
 * Supabase is configured to skip the check — sending any nonce risks
 * future regression if the toggle is ever flipped back.
 *
 * Why this matters: if a future engineer re-introduces FE-side nonce
 * generation OR re-adds the decode-and-echo block under the mistaken
 * belief that "more parity is safer", and Supabase's Skip-Nonce toggle
 * is later removed, every Google sign-in fails again. This test fails
 * loudly on any commit that adds a nonce key to the body.
 *
 * LESSON RECORDED (post-bundle memory):
 * Tests pin OBSERVABLE BEHAVIOR, not intended design. The journey from
 * ECHO-pinning at 7e3bb5a to no-nonce-pinning here demonstrates that
 * when the team intentionally pivots, the test follows. The pre-pivot
 * test was correct for its moment — it would have RED'd if someone
 * accidentally reverted the decode block before the team intended.
 */
import * as SecureStore from 'expo-secure-store';

const mockSignIn = jest.fn();
const mockHasPlayServices = jest.fn().mockResolvedValue(true);
jest.mock(
  '@react-native-google-signin/google-signin',
  () => ({
    GoogleSignin: {
      configure: jest.fn(),
      hasPlayServices: mockHasPlayServices,
      signIn: mockSignIn,
    },
  }),
  { virtual: true },
);

// Sentry mock left in place even though authService no longer calls it on
// the no-nonce path — defensive against future re-adds firing breadcrumbs
// we'd want to assert on. authService's Google error paths call
// Sentry.captureMessage (B4 diagnostics), so the mock MUST export it or the
// suite throws "captureMessage is not a function". B.1 F3.6.
const mockAddBreadcrumb = jest.fn();
const mockCaptureMessage = jest.fn();
jest.mock(
  '@sentry/react-native',
  () => ({
    addBreadcrumb: (...args: unknown[]) => mockAddBreadcrumb(...args),
    captureMessage: (...args: unknown[]) => mockCaptureMessage(...args),
    captureException: jest.fn(),
    init: jest.fn(),
  }),
  { virtual: true },
);

const saveTokenSpy = jest.spyOn(SecureStore, 'setItemAsync');

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

import { signInWithGoogle } from '../../src/services/authService';

/**
 * Minimal JWT helper for cases that DO want a parseable token shape, even
 * though the no-nonce invariant means the FE never reads it. Keeps the
 * test cases ergonomic.
 */
function makeJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: 'RS256' })).toString('base64')
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  const body = Buffer.from(JSON.stringify(payload)).toString('base64')
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  return `${header}.${body}.dummy-signature`;
}

function sentBodyFor(call: number = 0): Record<string, unknown> {
  return JSON.parse(mockFetch.mock.calls[call][1].body);
}

describe('signInWithGoogle — B4 final no-nonce invariant (Supabase Skip-Nonce toggle)', () => {
  beforeEach(() => {
    mockSignIn.mockReset();
    mockHasPlayServices.mockClear();
    mockFetch.mockReset();
    mockAddBreadcrumb.mockClear();
    saveTokenSpy.mockClear();
  });

  it('NEVER posts a nonce key — even when id_token payload HAS a nonce claim', async () => {
    // This is the regression-net's load-bearing case. A future engineer
    // who re-adds the decode-and-echo block (commit 8d1444e shape) will
    // RED this test loudly.
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u1', nonce: 'google-embedded-hash' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u1' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();

    const body = sentBodyFor();
    expect(body.provider).toBe('google');
    expect(body.id_token).toBe(idToken);
    expect('nonce' in body).toBe(false);
  });

  it('NEVER posts a nonce key — when id_token payload has no nonce claim', async () => {
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u2' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u2' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();
    expect('nonce' in sentBodyFor()).toBe(false);
  });

  it('NEVER posts a nonce key — when id_token is malformed (not a JWT)', async () => {
    mockSignIn.mockResolvedValue({ data: { idToken: 'opaque-not-a-jwt' } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u3' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();
    const body = sentBodyFor();
    expect(body.id_token).toBe('opaque-not-a-jwt');
    expect('nonce' in body).toBe(false);
  });

  it('body keys are EXACTLY { provider, id_token } — no leaked extras', async () => {
    // Pins the body keyset tightly so any new field (nonce, code, scope,
    // PKCE verifier, etc.) trips a RED first time it's added.
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u4' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u4' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();
    expect(Object.keys(sentBodyFor()).sort()).toEqual(['id_token', 'provider']);
  });
});

describe('signInWithGoogle — session persistence + error paths', () => {
  beforeEach(() => {
    mockSignIn.mockReset();
    mockHasPlayServices.mockClear();
    mockFetch.mockReset();
    mockAddBreadcrumb.mockClear();
    saveTokenSpy.mockClear();
  });

  it('returns success + saves access_token + refresh_token + user on 200', async () => {
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u5' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        user: { id: 'u5', email: 'u5@gmail.com' },
        session: {
          access_token: 'supabase-access',
          refresh_token: 'supabase-refresh',
          expires_at: 1234567890,
        },
      }),
    });

    const result = await signInWithGoogle();

    expect(result.success).toBe(true);
    expect(result.user?.id).toBe('u5');
    expect(result.token).toBe('supabase-access');

    const setKeys = saveTokenSpy.mock.calls.map((c) => c[0]);
    expect(setKeys).toEqual(expect.arrayContaining(['qaren_token', 'qaren_refresh_token']));
  });

  it('returns success=false + does NOT save token on backend error response', async () => {
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u6' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ success: false, error: 'Authentication failed' }),
    });

    const result = await signInWithGoogle();

    expect(result.success).toBe(false);
    // B4 diagnostic instrumentation is intentionally still in authService.ts
    // (Google Sign-In remains under investigation — CLAUDE.md Known Bugs).
    // The backend-reject path wraps the server reason in a [B4-DIAG] string
    // rather than returning the bare reason; assert on the stable parts.
    expect(result.error).toContain('[B4-DIAG] backend rejected token');
    expect(result.error).toContain('Authentication failed');
    // No SecureStore write attempted when success=false.
    expect(saveTokenSpy).not.toHaveBeenCalled();
  });

  it('returns success=false when no idToken is returned by Google SDK', async () => {
    mockSignIn.mockResolvedValue({ data: { idToken: null } });

    const result = await signInWithGoogle();

    expect(result.success).toBe(false);
    // No-idToken path returns the [B4-DIAG] diagnostic (intentionally still in
    // authService.ts pending Google Sign-In resolution). Assert the stable
    // prefix rather than the full dynamic message.
    expect(result.error).toContain('[B4-DIAG] no idToken from native SDK');
    // No POST attempted when token absent.
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('returns "Sign-in cancelled" when SDK throws SIGN_IN_CANCELLED', async () => {
    mockSignIn.mockRejectedValue({ code: 'SIGN_IN_CANCELLED', message: 'cancelled' });

    const result = await signInWithGoogle();

    expect(result.success).toBe(false);
    expect(result.error).toBe('Sign-in cancelled');
  });
});
