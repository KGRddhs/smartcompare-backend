/**
 * M18 mobile-auth unit — authService contracts.
 *
 * MB-flows-01: refreshSession must DISCRIMINATE dead-session outcomes
 *   from transient ones so performRefresh (api.ts) can stop replaying a
 *   dead token. New additive field `sessionInvalid: true` on the three
 *   dead paths (no refresh token / 200-without-session / 401), absent on
 *   network errors (a flaky network must never log the user out).
 *
 * MB-flows-03: register() must surface the email-confirmation case
 *   (Supabase returns a user WITHOUT a session) via additive
 *   `needsEmailConfirmation: true` instead of a bare success that
 *   dead-ends the Register screen.
 *
 * MB-security-03: pre-SecureStore plaintext token residue in
 *   AsyncStorage ('@qaren_token' / '@qaren_refresh_token' and the older
 *   '@smartcompare_*' pair) must be purged at boot — the 2026-04
 *   SecureStore migration switched reads/writes but never deleted the
 *   legacy keys, leaving refresh tokens in the Android-auto-backup-able
 *   RKStorage database.
 *
 * Plus login / logout / refresh-success smoke pins per the unit spec.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

const mockPost = jest.fn();

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockPost(...args),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
  API_BASE_URL: 'https://test.invalid',
}));

jest.mock('../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: jest.fn().mockResolvedValue('f'.repeat(64)),
}));

// eslint-disable-next-line @typescript-eslint/no-var-requires
const authService = require('../src/services/authService');

const TOKEN_KEY = 'qaren_token';
const REFRESH_KEY = 'qaren_refresh_token';
const USER_KEY = '@qaren_user';

const LEGACY_KEYS = [
  '@qaren_token',
  '@qaren_refresh_token',
  '@smartcompare_token',
  '@smartcompare_refresh_token',
];

beforeEach(async () => {
  mockPost.mockReset();
  (SecureStore as any).__reset();
  await AsyncStorage.clear();
  (AsyncStorage.multiRemove as jest.Mock).mockClear();
});

describe('refreshSession — dead-session discrimination (MB-flows-01)', () => {
  it('flags sessionInvalid when no refresh token is stored', async () => {
    const result = await authService.refreshSession();
    expect(result.success).toBe(false);
    expect(result.sessionInvalid).toBe(true);
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('flags sessionInvalid on a 200 that carries no session', async () => {
    await SecureStore.setItemAsync(REFRESH_KEY, 'rt-1');
    mockPost.mockResolvedValueOnce({ data: { success: true } }); // no session

    const result = await authService.refreshSession();

    expect(result.success).toBe(false);
    expect(result.sessionInvalid).toBe(true);
  });

  it('flags sessionInvalid on a 401 and clears the stored tokens', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'stale-access');
    await SecureStore.setItemAsync(REFRESH_KEY, 'revoked-rt');
    mockPost.mockRejectedValueOnce({ response: { status: 401 }, message: '401' });

    const result = await authService.refreshSession();

    expect(result.success).toBe(false);
    expect(result.sessionInvalid).toBe(true);
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
  });

  it('does NOT flag sessionInvalid (and keeps tokens) on a network error', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'still-good-maybe');
    await SecureStore.setItemAsync(REFRESH_KEY, 'rt-keep');
    mockPost.mockRejectedValueOnce(new Error('Network Error'));

    const result = await authService.refreshSession();

    expect(result.success).toBe(false);
    expect(result.sessionInvalid).toBeFalsy();
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBe('still-good-maybe');
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBe('rt-keep');
  });

  it('smoke: success path saves the rotated tokens', async () => {
    await SecureStore.setItemAsync(REFRESH_KEY, 'rt-old');
    mockPost.mockResolvedValueOnce({
      data: {
        success: true,
        session: { access_token: 'at-new', refresh_token: 'rt-new' },
        user: { id: 'u1', email: 'a@b.c' },
      },
    });

    const result = await authService.refreshSession();

    expect(result.success).toBe(true);
    expect(result.token).toBe('at-new');
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBe('at-new');
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBe('rt-new');
  });
});

describe('register — email-confirmation surface (MB-flows-03)', () => {
  it('reports needsEmailConfirmation when the backend returns a user without a session', async () => {
    mockPost.mockResolvedValueOnce({
      data: { user: { id: 'u1', email: 'new@user.bh' } }, // no session
    });

    const result = await authService.register('new@user.bh', 'StrongPass1x');

    expect(result.success).toBe(true);
    expect(result.needsEmailConfirmation).toBe(true);
    expect(result.token).toBeUndefined();
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
  });

  it('does not set needsEmailConfirmation when a session is issued, and saves the token', async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        user: { id: 'u1', email: 'new@user.bh' },
        session: { access_token: 'at-1', refresh_token: 'rt-1' },
      },
    });

    const result = await authService.register('new@user.bh', 'StrongPass1x');

    expect(result.success).toBe(true);
    expect(result.needsEmailConfirmation).toBeFalsy();
    expect(result.token).toBe('at-1');
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBe('at-1');
  });
});

describe('login / logout smoke (unit spec)', () => {
  it('login saves user + tokens on success', async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        user: { id: 'u1', email: 'a@b.c' },
        session: { access_token: 'at-login', refresh_token: 'rt-login' },
      },
    });

    const result = await authService.login('a@b.c', 'StrongPass1x');

    expect(result.success).toBe(true);
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBe('at-login');
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBe('rt-login');
    expect(await AsyncStorage.getItem(USER_KEY)).toContain('a@b.c');
  });

  it('logout clears the local session even when the server call fails', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'at');
    await SecureStore.setItemAsync(REFRESH_KEY, 'rt');
    await AsyncStorage.setItem(USER_KEY, JSON.stringify({ id: 'u1' }));
    mockPost.mockRejectedValueOnce(new Error('server down'));

    await authService.logout();

    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
    expect(await AsyncStorage.getItem(USER_KEY)).toBeNull();
  });
});

describe('legacy AsyncStorage token residue purge (MB-security-03)', () => {
  it('purgeLegacyAuthStorage removes all four pre-SecureStore keys', async () => {
    await AsyncStorage.setItem('@qaren_token', 'plain-at');
    await AsyncStorage.setItem('@qaren_refresh_token', 'plain-rt');
    await AsyncStorage.setItem('@smartcompare_token', 'old-at');
    await AsyncStorage.setItem('@smartcompare_refresh_token', 'old-rt');
    // The current (non-secret) user cache must survive the sweep.
    await AsyncStorage.setItem(USER_KEY, '{"id":"u1"}');

    await authService.purgeLegacyAuthStorage();

    for (const key of LEGACY_KEYS) {
      expect(await AsyncStorage.getItem(key)).toBeNull();
    }
    expect(await AsyncStorage.getItem(USER_KEY)).toBe('{"id":"u1"}');
  });

  it('initializeAuth triggers the legacy purge (fire-and-forget at boot)', async () => {
    await AsyncStorage.setItem('@qaren_refresh_token', 'plain-rt');

    await authService.initializeAuth(); // no user/token -> returns null fast
    // Let the fire-and-forget purge settle.
    await new Promise((resolve) => setImmediate(resolve));

    expect(AsyncStorage.multiRemove).toHaveBeenCalledWith(
      expect.arrayContaining(LEGACY_KEYS),
    );
    expect(await AsyncStorage.getItem('@qaren_refresh_token')).toBeNull();
  });
});
