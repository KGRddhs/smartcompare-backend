/**
 * A3 — app boot must not await a network token refresh.
 *
 * Before this fix, `initializeAuth()` awaited `refreshSession()` before
 * resolving, and App.tsx gates its whole tree on the `isLoading` flag it
 * flips AFTER that await. The refresh POST carried no per-call timeout,
 * so it rode api.ts's 120s global budget: a cold backend added seconds to
 * every launch and a black-holing connection (captive portal, stalled
 * proxy) froze the splash for two minutes with no cancel and no escape.
 * The cached-user fallback existed but only ran once the call SETTLED, so
 * blocking bought nothing on the failure path.
 *
 * Pinned here:
 *   1. cached user + token present, refresh still pending -> initializeAuth
 *      RESOLVES (the render path never waits on the network).
 *   2. the boot refresh carries a per-call deadline far under the 120s
 *      global; the mid-session interceptor path passes none.
 *   3. refresh failure (transient) -> the cached user still stands, tokens
 *      are kept, and nothing tells the app the session died.
 *   4. refresh dead (401 / no refresh token) -> the EXISTING session-death
 *      path runs: tokens cleared + session-invalid emitted, which is what
 *      App.tsx already subscribes to.
 *   5. the auth-state contract stays `verifyAuth(): User | null`.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import {
  onSessionInvalid,
  __resetSessionListeners,
} from '../src/services/sessionEvents';

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

const CACHED_USER = {
  id: 'u-cached',
  email: 'cached@qaren.app',
  preferences_completed: true,
};

/** api.ts's global axios budget — the ceiling this finding is about. */
const GLOBAL_AXIOS_TIMEOUT_MS = 120000;

/** Let every already-queued microtask/`setImmediate` continuation run. */
async function settleBackground(): Promise<void> {
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
}

async function seedCachedSession(): Promise<void> {
  await AsyncStorage.setItem(USER_KEY, JSON.stringify(CACHED_USER));
  await SecureStore.setItemAsync(TOKEN_KEY, 'at-cached');
  await SecureStore.setItemAsync(REFRESH_KEY, 'rt-cached');
}

beforeEach(async () => {
  mockPost.mockReset();
  (SecureStore as any).__reset();
  await AsyncStorage.clear();
  __resetSessionListeners();
});

describe('initializeAuth — boots from cache without awaiting the network (A3)', () => {
  it('resolves with the cached user while the refresh POST is still in flight', async () => {
    await seedCachedSession();
    // The refresh never settles — exactly the black-holed-connection case.
    // If initializeAuth awaits it, this test times out instead of passing.
    mockPost.mockImplementationOnce(() => new Promise(() => {}));

    const user = await authService.initializeAuth();

    expect(user).toEqual(CACHED_USER);
    expect(mockPost).toHaveBeenCalledTimes(1); // fired, just not awaited
  });

  it('renders-path resolution does not depend on the refresh at all (no POST resolution needed)', async () => {
    await seedCachedSession();
    mockPost.mockImplementationOnce(() => new Promise(() => {}));

    // A generous-but-finite race: the boot result must win against a
    // deadline far shorter than any network budget.
    const raced = await Promise.race([
      authService.initializeAuth(),
      new Promise((resolve) => setTimeout(() => resolve('TIMED_OUT'), 250)),
    ]);

    expect(raced).toEqual(CACHED_USER);
  });

  it('returns null and never touches the network without a cached user + token', async () => {
    const user = await authService.initializeAuth();

    expect(user).toBeNull();
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('keeps the verifyAuth(): User | null contract', async () => {
    await seedCachedSession();
    mockPost.mockImplementationOnce(() => new Promise(() => {}));

    const user = await authService.verifyAuth();

    expect(user).toEqual(CACHED_USER);

    await AsyncStorage.clear();
    (SecureStore as any).__reset();
    expect(await authService.verifyAuth()).toBeNull();
  });
});

describe('boot refresh deadline (A3)', () => {
  it('sends the boot refresh with a per-call timeout well under the 120s global', async () => {
    await seedCachedSession();
    mockPost.mockImplementationOnce(() => new Promise(() => {}));

    await authService.initializeAuth();

    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/auth/refresh',
      { refresh_token: 'rt-cached' },
      { timeout: authService.BOOT_REFRESH_TIMEOUT_MS },
    );
    expect(authService.BOOT_REFRESH_TIMEOUT_MS).toBeGreaterThan(0);
    expect(authService.BOOT_REFRESH_TIMEOUT_MS).toBeLessThan(
      GLOBAL_AXIOS_TIMEOUT_MS,
    );
  });

  it('leaves the mid-session interceptor path on the global budget (no per-call config)', async () => {
    await SecureStore.setItemAsync(REFRESH_KEY, 'rt-cached');
    mockPost.mockResolvedValueOnce({
      data: { success: true, session: { access_token: 'at-new' } },
    });

    // api.performRefresh calls refreshSession() with no arguments.
    await authService.refreshSession();

    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/auth/refresh',
      { refresh_token: 'rt-cached' },
      undefined,
    );
  });
});

describe('background refresh outcomes (A3)', () => {
  it('transient failure: cached user stands, tokens kept, no session-death signal', async () => {
    await seedCachedSession();
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);
    mockPost.mockRejectedValueOnce(new Error('Network Error'));

    const user = await authService.initializeAuth();
    await settleBackground();

    expect(user).toEqual(CACHED_USER);
    expect(sessionDied).not.toHaveBeenCalled();
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBe('at-cached');
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBe('rt-cached');
  });

  it('timeout failure is transient too: the session survives an unreachable backend', async () => {
    await seedCachedSession();
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);
    // Shape axios produces on a per-call timeout: no `response`.
    mockPost.mockRejectedValueOnce(
      Object.assign(new Error('timeout of 8000ms exceeded'), {
        code: 'ECONNABORTED',
      }),
    );

    const user = await authService.initializeAuth();
    await settleBackground();

    expect(user).toEqual(CACHED_USER);
    expect(sessionDied).not.toHaveBeenCalled();
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBe('at-cached');
  });

  it('401: boot still resolves optimistically, then the existing session-death path runs', async () => {
    await seedCachedSession();
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);
    mockPost.mockRejectedValueOnce({ response: { status: 401 }, message: '401' });

    const user = await authService.initializeAuth();
    expect(user).toEqual(CACHED_USER); // never blocked on the answer

    await settleBackground();

    expect(sessionDied).toHaveBeenCalledTimes(1);
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
    expect(await AsyncStorage.getItem(USER_KEY)).toBeNull();
  });

  it('no refresh token: the dead session is caught by the sessionInvalid FLAG, not the error string', async () => {
    // M21 gated this on `error === 'Session expired'`, which only matched
    // the 401 branch — this path returns 'No refresh token found' and used
    // to boot into MainTabs on a definitively dead session.
    await AsyncStorage.setItem(USER_KEY, JSON.stringify(CACHED_USER));
    await SecureStore.setItemAsync(TOKEN_KEY, 'at-orphaned');
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);

    await authService.initializeAuth();
    await settleBackground();

    expect(mockPost).not.toHaveBeenCalled();
    expect(sessionDied).toHaveBeenCalledTimes(1);
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
  });

  it('server refuses a session (200 without one): same dead-session path', async () => {
    await seedCachedSession();
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);
    mockPost.mockResolvedValueOnce({ data: { success: true } }); // no session

    await authService.initializeAuth();
    await settleBackground();

    expect(sessionDied).toHaveBeenCalledTimes(1);
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
  });

  it('success: the fresher user is handed back to the caller, session untouched', async () => {
    await seedCachedSession();
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);
    const fresh = {
      id: 'u-cached',
      email: 'cached@qaren.app',
      display_name: 'Renamed Elsewhere',
      preferences_completed: true,
    };
    mockPost.mockResolvedValueOnce({
      data: {
        success: true,
        session: { access_token: 'at-new', refresh_token: 'rt-new' },
        user: fresh,
      },
    });

    const onSessionRefreshed = jest.fn();
    const user = await authService.initializeAuth(onSessionRefreshed);
    await settleBackground();

    expect(user).toEqual(CACHED_USER); // rendered from cache first
    expect(onSessionRefreshed).toHaveBeenCalledTimes(1);
    expect(onSessionRefreshed).toHaveBeenCalledWith(fresh);
    expect(sessionDied).not.toHaveBeenCalled();
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBe('at-new');
  });

  it('does not call the refreshed-user callback on a failed refresh', async () => {
    await seedCachedSession();
    const onSessionRefreshed = jest.fn();
    mockPost.mockRejectedValueOnce(new Error('Network Error'));

    await authService.initializeAuth(onSessionRefreshed);
    await settleBackground();

    expect(onSessionRefreshed).not.toHaveBeenCalled();
  });
});
