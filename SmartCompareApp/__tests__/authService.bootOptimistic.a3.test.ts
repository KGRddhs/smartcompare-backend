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

// A3 follow-up: the boot refresh now goes through api.ts's module-scope
// refresh singleton, so this suite has to exercise the REAL api.ts —
// mocking the api MODULE would mock away the very dedup the boot path
// depends on. The transport is mocked one level lower instead (axios),
// which keeps every `mockPost` assertion below identical.
jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('axios', () => {
  const instance = {
    post: (...args: any[]) => mockPost(...args),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return { __esModule: true, default: { create: jest.fn(() => instance) } };
});

jest.mock('../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: jest.fn().mockResolvedValue('f'.repeat(64)),
}));

// eslint-disable-next-line @typescript-eslint/no-var-requires
const authService = require('../src/services/authService');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const apiModule = require('../src/services/api');

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
  // Several cases below deliberately leave a refresh POST in flight
  // forever; without this the next case would coalesce onto that dead
  // Promise instead of starting its own.
  apiModule.__resetRefreshMutex();
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

/**
 * A3 follow-up — the background boot refresh must not spend the
 * single-use refresh token a second time.
 *
 * Supabase rotates the refresh token on every successful POST
 * /auth/refresh, so it is SINGLE-USE, and the backend says so in its own
 * docstring (app/api/auth_routes.py::refresh): "If two concurrent clients
 * race to refresh with the same token, only one wins; the loser gets a
 * 401 ... Deduping is therefore a CLIENT-SIDE responsibility — the mobile
 * app must hold a module-scope singleton Promise around the refresh
 * call."
 *
 * That singleton is api.ts's getOrStartRefresh(). Moving the boot refresh
 * OFF the render path put it in genuine flight alongside the launch's
 * first authed calls (App.tsx's push-token PUT, Home's referral-status
 * GET on focus), each of which rides the SAME cached-and-expired Bearer
 * and enters the 401 interceptor's refresh. A boot refresh that called
 * refreshSession() directly would therefore issue a SECOND concurrent
 * refresh with the same token: the loser's 401 lands on clearSession() +
 * sessionInvalid, routing the user back to the Auth stack at launch and
 * deleting the winner's freshly stored tokens.
 */
describe('boot refresh shares api.ts refresh mutex (A3 / R9)', () => {
  const FRESH_USER = {
    id: 'u-cached',
    email: 'cached@qaren.app',
    display_name: 'Renamed Elsewhere',
    preferences_completed: true,
  };

  /** A refresh POST that stays in flight until the test resolves it. */
  function pendingPost(): { resolve: (v: any) => void; reject: (e: any) => void } {
    const handles: any = {};
    mockPost.mockImplementationOnce(
      () =>
        new Promise((res, rej) => {
          handles.resolve = res;
          handles.reject = rej;
        }),
    );
    return handles;
  }

  it('a 401 landing DURING boot joins the boot refresh: ONE POST, one token spend', async () => {
    await seedCachedSession();
    const post = pendingPost();

    await authService.initializeAuth();
    await settleBackground(); // let the background refresh reach the transport
    expect(mockPost).toHaveBeenCalledTimes(1);

    // The 401 interceptor's refresh entry point, fired while the boot
    // refresh is still in flight.
    const interceptorRefresh = apiModule.__testRefreshDedup();
    await settleBackground();

    // Bypassing the mutex shows up here as a SECOND POST carrying the
    // SAME (already-spent) refresh token.
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/auth/refresh',
      { refresh_token: 'rt-cached' },
      { timeout: authService.BOOT_REFRESH_TIMEOUT_MS },
    );

    post.resolve({
      data: {
        success: true,
        session: { access_token: 'at-new', refresh_token: 'rt-new' },
      },
    });

    // The coalesced 401 caller gets the winner's rotated token, not a 401.
    await expect(interceptorRefresh).resolves.toEqual(
      expect.objectContaining({ success: true, token: 'at-new' }),
    );
    await settleBackground();

    expect(mockPost).toHaveBeenCalledTimes(1);
    // The winner's freshly stored session survives.
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBe('at-new');
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBe('rt-new');
  });

  it('a boot starting while a 401 refresh is in flight joins it, and still re-syncs the user', async () => {
    await seedCachedSession();
    const post = pendingPost();

    // The interceptor wins the start this time, so its (global-budget)
    // deadline is the one on the wire.
    const interceptorRefresh = apiModule.__testRefreshDedup();
    await settleBackground();
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/auth/refresh',
      { refresh_token: 'rt-cached' },
      undefined,
    );

    const onSessionRefreshed = jest.fn();
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);
    const user = await authService.initializeAuth(onSessionRefreshed);
    await settleBackground();

    expect(user).toEqual(CACHED_USER);
    expect(mockPost).toHaveBeenCalledTimes(1); // joined, did not race

    post.resolve({
      data: {
        success: true,
        session: { access_token: 'at-new', refresh_token: 'rt-new' },
        user: FRESH_USER,
      },
    });
    await interceptorRefresh;
    await settleBackground();

    expect(mockPost).toHaveBeenCalledTimes(1);
    // A coalesced boot has no result object of its own, so it re-reads
    // what the winner persisted — the UI still learns the fresher user.
    expect(onSessionRefreshed).toHaveBeenCalledTimes(1);
    expect(onSessionRefreshed).toHaveBeenCalledWith(FRESH_USER);
    expect(sessionDied).not.toHaveBeenCalled();
  });

  it('a dead session seen by BOTH the boot refresh and a concurrent 401 logs out exactly once', async () => {
    // The failure this pins is symmetric to the double-spend: two
    // independent refreshes would each map their 401 to clearSession() +
    // emitSessionInvalid(), so App.tsx would be told twice. Sharing the
    // round-trip makes it exactly one — and never zero, which is the
    // other way to get this wrong.
    await seedCachedSession();
    const post = pendingPost();
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);

    await authService.initializeAuth();
    await settleBackground();
    const interceptorRefresh = apiModule.__testRefreshDedup();
    await settleBackground();
    expect(mockPost).toHaveBeenCalledTimes(1);

    post.reject({ response: { status: 401 }, message: '401' });
    await expect(interceptorRefresh).resolves.toEqual(
      expect.objectContaining({ success: false, token: null }),
    );
    await settleBackground();

    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(sessionDied).toHaveBeenCalledTimes(1);
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
    expect(await AsyncStorage.getItem(USER_KEY)).toBeNull();
  });
});
