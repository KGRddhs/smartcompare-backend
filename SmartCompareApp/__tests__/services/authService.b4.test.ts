/**
 * B4 regression test — Google sign-in nonce ECHO from id_token claim.
 *
 * REAL fix (main commit 8d1444e, "fix(auth/google): echo nonce from id_token
 * claim for Supabase parity"). ROOT CAUSE captured at Sentry PYTHON-FASTAPI-F
 * on 2026-05-26 14:03Z:
 *
 *   "Auth error in social_login: Passed nonce and nonce in id_token should
 *    either both exist or not."
 *
 * Path A R1 (Bundle D Phase 3, commit bb78b6b) assumed Google's iOS native SDK
 * does NOT embed a nonce in the issued idToken — and dropped the FE-side
 * nonce. That assumption was wrong: @react-native-google-signin auto-generates
 * a nonce claim. With FE NOT passing nonce but the idToken carrying one,
 * Supabase's parity check fails (it requires both or neither).
 *
 * Bundle E `8d1444e` REVERSES Path A R1's drop and instead:
 *   1. base64url-decode the idToken's middle segment (payload)
 *   2. JSON.parse, read `nonce` claim
 *   3. If present, set body.nonce = tokenNonce alongside id_token
 *   4. Backend conditionally forwards nonce to Supabase; parity holds
 *
 * Replay protection unchanged — comes from Supabase audience check on the
 * `aud` claim (vs iosClientId), Google's RS256 signature, and short token TTL.
 * The echoed nonce satisfies Supabase parity; the FE doesn't independently
 * "know" the nonce (it's Google-generated), so it doesn't add new replay
 * protection beyond what the signature + audience already give.
 *
 * INVARIANT THIS TEST PINS (B4 regression-guard):
 *   When the Google id_token's payload contains a non-empty `nonce` claim,
 *   signInWithGoogle MUST set `body.nonce` to that claim value before POSTing
 *   to /auth/social-login. When no claim is present, `body.nonce` MUST be
 *   absent. A malformed token MUST NOT crash — it falls through to no-nonce
 *   + a Sentry breadcrumb so we can audit decode failures.
 *
 * Why this matters: a future engineer reading Path A R1's old comment block
 * could re-drop the decode + reintroduce the parity break that fired B4. This
 * test fails loudly on any commit that removes the decode block.
 *
 * NOTE on worktree state: `8d1444e` lives on `main`. The
 * `feature/bundle-e-visual-fidelity` worktree branch this test ships on does
 * not yet contain the decode block — so the test will be RED here until main
 * lands on the branch (rebase, merge, or cherry-pick). That's the expected
 * RED-pending-merge state.
 */
import * as SecureStore from 'expo-secure-store';

// Mock Sentry — the decode-block fires addBreadcrumb on both success and
// decode-failure paths. Mock surfaces capture for assertion.
const mockAddBreadcrumb = jest.fn();
jest.mock(
  '@sentry/react-native',
  () => ({
    addBreadcrumb: (...args: unknown[]) => mockAddBreadcrumb(...args),
    captureException: jest.fn(),
    init: jest.fn(),
  }),
  { virtual: true },
);

// Mock Google sign-in module — authService uses lazy require() inside
// getGoogleSignin() so the mock must be registered before service import.
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

const saveTokenSpy = jest.spyOn(SecureStore, 'setItemAsync');

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

// atob is available in modern Node (16+) globally. RN Hermes also has it.
// The code uses `typeof atob === 'function'` so the test env mirrors prod.
if (typeof (global as any).atob !== 'function') {
  (global as any).atob = (s: string) => Buffer.from(s, 'base64').toString('binary');
}

import { signInWithGoogle } from '../../src/services/authService';

/**
 * Minimal JWT helper — header + base64url(payload) + dummy sig. Padding (=)
 * stripped to match real JWTs.
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

describe('signInWithGoogle — B4 nonce ECHO regression (commit 8d1444e)', () => {
  beforeEach(() => {
    mockSignIn.mockReset();
    mockHasPlayServices.mockClear();
    mockFetch.mockReset();
    mockAddBreadcrumb.mockClear();
    saveTokenSpy.mockClear();
  });

  it('echoes nonce from idToken payload claim to body.nonce', async () => {
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u1', nonce: 'abc-123-xyz' });
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
    // The single-line B4 regression invariant.
    expect(body.nonce).toBe('abc-123-xyz');
  });

  it('omits nonce key when idToken payload has no nonce claim', async () => {
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u2' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u2' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();

    const body = sentBodyFor();
    expect(body.id_token).toBe(idToken);
    // No nonce in payload → no body.nonce — backend `if nonce:` guard skips
    // the Supabase nonce param and parity holds (both empty).
    expect(body.nonce).toBeUndefined();
  });

  it('omits nonce + fires Sentry breadcrumb when token decode fails (malformed)', async () => {
    // 'opaque' has no dots → parts[1] is undefined → decode throws → catch fires
    mockSignIn.mockResolvedValue({ data: { idToken: 'not-a-jwt-just-opaque' } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u3' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();

    const body = sentBodyFor();
    expect(body.id_token).toBe('not-a-jwt-just-opaque');
    expect(body.nonce).toBeUndefined();
    // A b4_diag warning breadcrumb fires per authService.ts:467
    const warningBreadcrumbs = mockAddBreadcrumb.mock.calls.filter((c) =>
      c[0]?.level === 'warning' && c[0]?.category === 'b4_diag',
    );
    expect(warningBreadcrumbs.length).toBeGreaterThanOrEqual(1);
  });

  it('omits nonce when payload claim is an empty string (treated as absent)', async () => {
    // Defensive: the source guard requires `typeof claims.nonce === 'string'
    // && claims.nonce.length > 0`. Empty string must NOT echo.
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u4', nonce: '' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u4' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();

    expect(sentBodyFor().nonce).toBeUndefined();
  });

  it('omits nonce when payload claim is not a string (e.g. number)', async () => {
    // Defensive: typeof guard rejects non-string nonce values.
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u5', nonce: 12345 });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u5' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();

    expect(sentBodyFor().nonce).toBeUndefined();
  });

  it('fires success breadcrumb when nonce is echoed', async () => {
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u6', nonce: 'real-nonce' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u6' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();

    // A b4_diag info breadcrumb at level='info' fires per authService.ts
    // when nonce is echoed. Message references the nonce length.
    const successBreadcrumbs = mockAddBreadcrumb.mock.calls.filter((c) =>
      c[0]?.level === 'info' && c[0]?.category === 'b4_diag' &&
      typeof c[0]?.message === 'string' && c[0].message.includes('nonce echoed'),
    );
    expect(successBreadcrumbs.length).toBeGreaterThanOrEqual(1);
  });
});

describe('signInWithGoogle — happy path + session persistence (unchanged)', () => {
  beforeEach(() => {
    mockSignIn.mockReset();
    mockHasPlayServices.mockClear();
    mockFetch.mockReset();
    mockAddBreadcrumb.mockClear();
    saveTokenSpy.mockClear();
  });

  it('returns success + saves token + refresh_token + user on 200', async () => {
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u7', nonce: 'n' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        user: { id: 'u7', email: 'u7@gmail.com' },
        session: {
          access_token: 'supabase-access',
          refresh_token: 'supabase-refresh',
          expires_at: 1234567890,
        },
      }),
    });

    const result = await signInWithGoogle();

    expect(result.success).toBe(true);
    expect(result.user?.id).toBe('u7');
    expect(result.token).toBe('supabase-access');

    const setKeys = saveTokenSpy.mock.calls.map((c) => c[0]);
    expect(setKeys).toEqual(expect.arrayContaining(['qaren_token', 'qaren_refresh_token']));
  });

  it('returns success=false when no idToken is returned by Google SDK', async () => {
    mockSignIn.mockResolvedValue({ data: { idToken: null } });

    const result = await signInWithGoogle();

    expect(result.success).toBe(false);
    expect(result.error).toBe('Failed to get Google ID token');
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('returns "Sign-in cancelled" when SDK throws SIGN_IN_CANCELLED', async () => {
    mockSignIn.mockRejectedValue({ code: 'SIGN_IN_CANCELLED', message: 'cancelled' });

    const result = await signInWithGoogle();

    expect(result.success).toBe(false);
    expect(result.error).toBe('Sign-in cancelled');
  });
});
