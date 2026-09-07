/**
 * S65 W1-4 (client half) — logout must hand the server the refresh token
 * it needs in order to revoke the session.
 *
 * The Bearer header only identifies WHICH user is leaving. Supabase
 * revokes a session by its REFRESH token, so the pre-W1-4 request — an
 * empty `{}` body — left the stored refresh token valid upstream until it
 * expired on its own. The backend (PR #139) accepts an OPTIONAL
 * `refresh_token` body field and revokes that token when
 * ENABLE_LOGOUT_UPSTREAM_REVOCATION is on; until the client actually
 * SENDS the field the flag is inert on every phone. These tests pin the
 * client half.
 *
 * Deliberately pinned as unchanged: the Bearer header, the empty-body
 * shape when nothing is stored, server errors staying ignored, and the
 * local clear always running. Also pinned: the token value must never
 * reach console output — it is a live credential until revoked.
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

// The SecureStore keys authService actually reads/writes (no '@' prefix —
// SecureStore rejects it). REFRESH_KEY is the SAME key refreshSession()
// reads to mint a new session.
const TOKEN_KEY = 'qaren_token';
const REFRESH_KEY = 'qaren_refresh_token';
const USER_KEY = '@qaren_user';

const STORED_REFRESH = 'rt-must-be-revoked-9f3a';

beforeEach(async () => {
  mockPost.mockReset();
  (SecureStore as any).__reset();
  await AsyncStorage.clear();
});

describe('logout sends the stored refresh_token so the server can revoke it', () => {
  it('posts { refresh_token } with the Bearer still attached when a token is stored', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'at-live');
    await SecureStore.setItemAsync(REFRESH_KEY, STORED_REFRESH);
    await AsyncStorage.setItem(USER_KEY, JSON.stringify({ id: 'u1' }));
    mockPost.mockResolvedValueOnce({ data: { success: true } });

    await authService.logout();

    expect(mockPost).toHaveBeenCalledTimes(1);
    const [url, body, config] = mockPost.mock.calls[0];
    expect(url).toBe('/api/v1/auth/logout');
    expect(body).toEqual({ refresh_token: STORED_REFRESH });
    expect(config.headers.Authorization).toBe('Bearer at-live');
  });

  it('sends the SAME stored value refreshSession() would spend', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'at-live');
    await SecureStore.setItemAsync(REFRESH_KEY, STORED_REFRESH);
    mockPost.mockResolvedValueOnce({ data: { success: true } });

    // Read through the same key surface the app uses, then log out.
    const stored = await SecureStore.getItemAsync(REFRESH_KEY);
    await authService.logout();

    expect(mockPost.mock.calls[0][1]).toEqual({ refresh_token: stored });
  });

  it('keeps today exact empty body when no refresh token is stored', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'at-live');
    // No REFRESH_KEY written.
    mockPost.mockResolvedValueOnce({ data: { success: true } });

    await authService.logout();

    expect(mockPost).toHaveBeenCalledTimes(1);
    const [url, body, config] = mockPost.mock.calls[0];
    expect(url).toBe('/api/v1/auth/logout');
    expect(body).toEqual({});
    expect(Object.keys(body)).toHaveLength(0);
    expect(config.headers.Authorization).toBe('Bearer at-live');
  });

  it('still makes no server call at all when there is no access token', async () => {
    await SecureStore.setItemAsync(REFRESH_KEY, STORED_REFRESH);

    await authService.logout();

    expect(mockPost).not.toHaveBeenCalled();
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
  });

  it('degrades to the empty body when the SecureStore read throws', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'at-live');
    await SecureStore.setItemAsync(REFRESH_KEY, STORED_REFRESH);
    mockPost.mockResolvedValueOnce({ data: { success: true } });

    const realGet = (SecureStore as any).getItemAsync;
    const spy = jest
      .spyOn(SecureStore, 'getItemAsync')
      .mockImplementation(async (key: string) => {
        if (key === REFRESH_KEY) throw new Error('keystore unavailable');
        return realGet(key);
      });

    await authService.logout();

    // The POST still happens (a keystore hiccup must not cost the server
    // call), with today's body shape.
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost.mock.calls[0][1]).toEqual({});
    spy.mockRestore();
  });
});

describe('logout — unchanged local-clear behaviour', () => {
  it('clears the local session and resolves when the server errors', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'at-live');
    await SecureStore.setItemAsync(REFRESH_KEY, STORED_REFRESH);
    await AsyncStorage.setItem(USER_KEY, JSON.stringify({ id: 'u1' }));
    mockPost.mockRejectedValueOnce(new Error('server down'));

    await expect(authService.logout()).resolves.toBeUndefined();

    expect(mockPost.mock.calls[0][1]).toEqual({ refresh_token: STORED_REFRESH });
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
    expect(await AsyncStorage.getItem(USER_KEY)).toBeNull();
  });

  it('clears the local session and resolves when the request times out', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'at-live');
    await SecureStore.setItemAsync(REFRESH_KEY, STORED_REFRESH);
    await AsyncStorage.setItem(USER_KEY, JSON.stringify({ id: 'u1' }));
    mockPost.mockRejectedValueOnce({ code: 'ECONNABORTED', message: 'timeout of 0ms exceeded' });

    await expect(authService.logout()).resolves.toBeUndefined();

    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
    expect(await AsyncStorage.getItem(USER_KEY)).toBeNull();
  });

  it('clears the local session even when the server call succeeds', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'at-live');
    await SecureStore.setItemAsync(REFRESH_KEY, STORED_REFRESH);
    await AsyncStorage.setItem(USER_KEY, JSON.stringify({ id: 'u1' }));
    mockPost.mockResolvedValueOnce({ data: { success: true } });

    await authService.logout();

    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
    expect(await AsyncStorage.getItem(USER_KEY)).toBeNull();
  });
});

describe('logout never leaks the refresh token to logs', () => {
  it('writes nothing containing the token value, even on the __DEV__ failure path', async () => {
    await SecureStore.setItemAsync(TOKEN_KEY, 'at-live');
    await SecureStore.setItemAsync(REFRESH_KEY, STORED_REFRESH);
    mockPost.mockRejectedValueOnce(new Error('server down'));

    // The only console writes in logout() are __DEV__-gated; force the
    // dev branch on so the assertion has something to catch.
    const prevDev = (globalThis as any).__DEV__;
    (globalThis as any).__DEV__ = true;

    const spies = (['log', 'info', 'warn', 'error', 'debug'] as const).map((m) =>
      jest.spyOn(console, m).mockImplementation(() => {})
    );

    try {
      await authService.logout();

      const written = spies
        .flatMap((s) => s.mock.calls)
        .flat()
        .map((arg) => {
          try {
            return typeof arg === 'string' ? arg : JSON.stringify(arg);
          } catch {
            return String(arg);
          }
        })
        .join(' | ');

      expect(written).not.toContain(STORED_REFRESH);
      // The pre-existing dev breadcrumb itself is unchanged.
      expect(written).toContain('Server logout failed, clearing local session');
    } finally {
      spies.forEach((s) => s.mockRestore());
      (globalThis as any).__DEV__ = prevDev;
    }
  });
});
