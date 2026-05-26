/**
 * B4 regression test — Google sign-in nonce handling.
 *
 * REAL fix (commit 8d1444e, ROOT CAUSE Sentry PYTHON-FASTAPI-F captured
 * 2026-05-26 14:03Z): the FE used to generate a random nonce client-side
 * and POST it alongside the Google id_token, but Google's native iOS SDK
 * does NOT bind the nonce into the token's `nonce` claim (unlike Apple's
 * expo-apple-authentication which DOES bind it). Supabase then failed the
 * nonce-parity check with "Passed nonce and nonce in id_token should
 * either both exist or both be empty".
 *
 * The fix: DROP nonce entirely from the Google flow. Replay protection
 * comes from the short token TTL + Supabase's audience/issuer checks
 * against `iosClientId`. Apple still uses hashed-nonce because its SDK
 * binds the hash into the token claim.
 *
 * Invariant this test pins (regression-guard):
 *   `body` posted to /auth/social-login for provider='google' MUST NOT
 *   contain a `nonce` key, regardless of what's in the id_token payload.
 *
 * Why this matters: if a future refactor reintroduces FE-side nonce
 * generation OR adds "echo nonce from id_token payload" logic, Supabase
 * will reject every Google sign-in with the same nonce-parity error.
 * This test fails loudly on the first PR that breaks the invariant.
 *
 * NOTE: dispatcher's prompt described an "echo nonce from token payload"
 * design which was the WRONG diagnosis path. The actual ship is
 * "nonce-drop". Test follows the real code at authService.ts:420-483,
 * not the prompt.
 */
import * as SecureStore from 'expo-secure-store';

// Lazy mock the Google sign-in module — authService.ts uses require()
// inside getGoogleSignin() so the mock must be registered before the
// service is imported.
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

// SecureStore mock is provided globally via jest.config.js moduleNameMapper.
// Capture saveToken side-effects via the shared mock.
const saveTokenSpy = jest.spyOn(SecureStore, 'setItemAsync');

// Mock global fetch — the service uses raw fetch() for the social-login POST.
const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

import { signInWithGoogle } from '../../src/services/authService';

/**
 * Minimal JWT helper — header + base64url payload + dummy signature.
 * Base64url-encodes the payload so id_token.split('.')[1] decodes to it.
 * Padding stripped (= chars removed) to match real JWTs.
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

describe('signInWithGoogle — B4 nonce-drop regression (commit 8d1444e)', () => {
  beforeEach(() => {
    mockSignIn.mockReset();
    mockHasPlayServices.mockClear();
    mockFetch.mockReset();
    saveTokenSpy.mockClear();
  });

  it('NEVER posts a nonce field — even when id_token payload has a nonce claim', async () => {
    // The pre-fix code would have echoed this nonce; post-fix MUST NOT.
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u1', nonce: 'should-NOT-be-echoed' });
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
    // The single-line regression invariant — body must NOT carry a nonce key.
    expect('nonce' in body).toBe(false);
  });

  it('NEVER posts a nonce field when id_token payload has no nonce claim', async () => {
    const idToken = makeJwt({ aud: 'iosClientId', sub: 'u2' });
    mockSignIn.mockResolvedValue({ data: { idToken } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u2' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();

    const body = sentBodyFor();
    expect('nonce' in body).toBe(false);
  });

  it('NEVER posts a nonce field when id_token is malformed (not a JWT)', async () => {
    mockSignIn.mockResolvedValue({ data: { idToken: 'not-a-jwt-just-an-opaque-string' } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u3' }, session: { access_token: 't' } }),
    });

    await signInWithGoogle();

    const body = sentBodyFor();
    expect(body.id_token).toBe('not-a-jwt-just-an-opaque-string');
    expect('nonce' in body).toBe(false);
  });

  it('body keys are EXACTLY { provider, id_token } — no extras', async () => {
    // Extra keys (nonce, code, scope, etc.) leaking into the POST could
    // re-introduce parity issues with Supabase. Pin the body keyset.
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

describe('signInWithGoogle — happy path + session persistence', () => {
  beforeEach(() => {
    mockSignIn.mockReset();
    mockHasPlayServices.mockClear();
    mockFetch.mockReset();
    saveTokenSpy.mockClear();
  });

  it('returns success + saves token + refresh_token + user on 200', async () => {
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

    // saveToken writes to SecureStore under the 'qaren_token' key + refresh
    // under 'qaren_refresh_token'.
    const setKeys = saveTokenSpy.mock.calls.map((c) => c[0]);
    expect(setKeys).toEqual(expect.arrayContaining(['qaren_token', 'qaren_refresh_token']));
  });

  it('returns success=false when no idToken is returned by Google SDK', async () => {
    mockSignIn.mockResolvedValue({ data: { idToken: null } });

    const result = await signInWithGoogle();

    expect(result.success).toBe(false);
    expect(result.error).toBe('Failed to get Google ID token');
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
