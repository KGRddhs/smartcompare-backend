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
 * P-A3 (round-1 polish) — the first cut of A3 replaced the 120s budget
 * with an 8s per-call deadline on the boot POST. That was the wrong
 * lever, and a regression against main: the refresh token is SINGLE-USE,
 * so giving up client-side does NOT stop the server finishing the
 * rotation — it only stops the phone learning the new token. The device
 * then keeps a spent token, and the next refresh (a 401 on History, or
 * the next launch) presents it; past Supabase's 10s reuse interval the
 * whole session family is revoked and a perfectly valid session is logged
 * out. Nothing on the render path ever waited for this refresh, so the
 * deadline bought nothing user-visible either.
 *
 * PRINCIPLE PINNED HERE: an in-flight POST /auth/refresh is NEVER aborted
 * client-side. A deadline may bound what a CALLER waits for; it may never
 * bound the request.
 *
 * Pinned here:
 *   1. cached user + token present, refresh still pending -> initializeAuth
 *      RESOLVES (the render path never waits on the network).
 *   2. the boot refresh reaches the transport with NO per-call config —
 *      no timeout, no AbortSignal — and a refresh that lands long after
 *      the boot stopped waiting still persists the rotated tokens + user
 *      and still calls onSessionRefreshed.
 *   3. refresh failure (transient) -> the cached user still stands, tokens
 *      are kept, and nothing tells the app the session died.
 *   4. refresh dead (401 / no refresh token) -> the EXISTING session-death
 *      path runs: tokens cleared + session-invalid emitted, which is what
 *      App.tsx already subscribes to.
 *   5. a logout that lands mid-flight is not undone by the refresh's own
 *      completion (P-A3 session-generation guard).
 *   6. the auth-state contract stays `verifyAuth(): User | null`.
 */

import * as fs from 'fs';
import * as path from 'path';
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

const FRESH_USER = {
  id: 'u-cached',
  email: 'cached@qaren.app',
  display_name: 'Renamed Elsewhere',
  preferences_completed: true,
};

/** Let every already-queued microtask/`setImmediate` continuation run. */
async function settleBackground(): Promise<void> {
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
}

/**
 * Like settleBackground, but also drains 0ms timers — the queue a
 * client-side deadline would fire on. After this, "the client gave up"
 * has either happened or can no longer happen.
 */
async function settleIncludingTimers(): Promise<void> {
  for (let i = 0; i < 3; i += 1) {
    await new Promise((resolve) => setImmediate(resolve));
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

async function seedCachedSession(): Promise<void> {
  await AsyncStorage.setItem(USER_KEY, JSON.stringify(CACHED_USER));
  await SecureStore.setItemAsync(TOKEN_KEY, 'at-cached');
  await SecureStore.setItemAsync(REFRESH_KEY, 'rt-cached');
}

/** A refresh POST that stays in flight until the test settles it. */
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

/**
 * A transport that HONOURS whatever per-call deadline the client sends —
 * the whole point of the P-A3 pins below.
 *
 * The scenario is "the server needs longer than the client's patience":
 * if the client attaches a `timeout`, this request is cut off client-side
 * FIRST (axios's ECONNABORTED shape, no `response`), and the server's own
 * completion — `completeOnServer(...)`, i.e. the rotation that really did
 * happen — lands on an already-settled promise and is lost. With no
 * deadline attached, the request simply stays open until the server
 * answers. A mock that ignored `config.timeout` would make these tests
 * pass with the abort restored, which is exactly the regression they
 * exist to catch.
 */
function slowServerPost(): { completeOnServer: (value: any) => void } {
  const handles: any = {};
  mockPost.mockImplementationOnce(
    (_url: string, _body: any, config?: any) =>
      new Promise((resolve, reject) => {
        handles.completeOnServer = resolve;
        if (config && typeof config.timeout === 'number') {
          setTimeout(
            () =>
              reject(
                Object.assign(
                  new Error(`timeout of ${config.timeout}ms exceeded`),
                  { code: 'ECONNABORTED' },
                ),
              ),
            0,
          );
        }
      }),
  );
  return handles as { completeOnServer: (value: any) => void };
}

/**
 * Comment-aware source stripper for the static fences below: a fence that
 * matched commentary would keep passing after the code moved into a
 * comment. String literals are preserved (the URL the fence anchors on
 * lives in one); `//` and `/* *\/` runs are dropped.
 */
function stripComments(src: string): string {
  let out = '';
  let quote: string | null = null;
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    const next = src[i + 1];
    if (quote) {
      out += c;
      if (c === '\\') {
        out += next ?? '';
        i += 2;
        continue;
      }
      if (c === quote) quote = null;
      i += 1;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') {
      quote = c;
      out += c;
      i += 1;
      continue;
    }
    if (c === '/' && next === '/') {
      while (i < src.length && src[i] !== '\n') i += 1;
      continue;
    }
    if (c === '/' && next === '*') {
      i += 2;
      while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) i += 1;
      i += 2;
      continue;
    }
    out += c;
    i += 1;
  }
  return out;
}

const authServiceSrc = stripComments(
  fs.readFileSync(path.resolve(__dirname, '../src/services/authService.ts'), 'utf8'),
);
const apiSrc = stripComments(
  fs.readFileSync(path.resolve(__dirname, '../src/services/api.ts'), 'utf8'),
);

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

/**
 * P-A3 — these five replace the round-0 pins that asserted the boot POST
 * carried `{ timeout: BOOT_REFRESH_TIMEOUT_MS }`.
 *
 * They are not deleted but INVERTED, because the old contract was the
 * bug: the deadline aborted the REQUEST, and an aborted refresh still
 * spends the single-use token server-side. The replacement contract is
 * (a) a late-landing refresh still persists its rotation, and (b) nothing
 * client-side can cut the request off in the first place.
 */
describe('the boot refresh is never aborted client-side (P-A3)', () => {
  it('reaches the transport with NO per-call config — no timeout, no AbortSignal', async () => {
    await seedCachedSession();
    mockPost.mockImplementationOnce(() => new Promise(() => {}));

    await authService.initializeAuth();
    await settleBackground();

    expect(mockPost).toHaveBeenCalledTimes(1); // positive control
    const call = mockPost.mock.calls[0];
    expect(call[0]).toBe('/api/v1/auth/refresh');
    expect(call[1]).toEqual({ refresh_token: 'rt-cached' });
    // `undefined` covers both "no third argument" and "an explicitly
    // undefined config"; anything else is a client-side abort lever.
    expect(call[2]).toBeUndefined();
    expect(JSON.stringify(call)).not.toMatch(/timeout|signal/i);
  });

  it('a refresh that lands AFTER the boot stopped waiting still persists the rotated session', async () => {
    // The token-burn hazard in one test: the client's patience runs out,
    // the cold backend finishes the rotation anyway. The phone must end
    // up holding the NEW tokens, never the spent ones.
    await seedCachedSession();
    const server = slowServerPost();
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);
    const onSessionRefreshed = jest.fn();

    const user = await authService.initializeAuth(onSessionRefreshed);
    expect(user).toEqual(CACHED_USER); // boot never waited

    // Any client-side deadline the request carried would fire in here.
    await settleIncludingTimers();

    // ...and only now does the server answer.
    server.completeOnServer({
      data: {
        success: true,
        session: { access_token: 'at-new', refresh_token: 'rt-new' },
        user: FRESH_USER,
      },
    });
    await settleIncludingTimers();

    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBe('at-new');
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBe('rt-new');
    expect(JSON.parse((await AsyncStorage.getItem(USER_KEY)) as string)).toEqual(
      FRESH_USER,
    );
    expect(onSessionRefreshed).toHaveBeenCalledTimes(1);
    expect(onSessionRefreshed).toHaveBeenCalledWith(FRESH_USER);
    expect(sessionDied).not.toHaveBeenCalled();
  });

  it('the mid-session interceptor path carries no per-call config either', async () => {
    await SecureStore.setItemAsync(REFRESH_KEY, 'rt-cached');
    mockPost.mockResolvedValueOnce({
      data: { success: true, session: { access_token: 'at-new' } },
    });

    // api.performRefresh calls refreshSession() with no arguments.
    await authService.refreshSession();

    expect(mockPost).toHaveBeenCalledTimes(1); // positive control
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/refresh', {
      refresh_token: 'rt-cached',
    });
  });

  it('source fence: the refresh POST call site has no deadline/abort plumbing', () => {
    // Positive controls first — a fence that silently stopped matching
    // would "pass" forever.
    expect(authServiceSrc).toContain('async function refreshSession(');
    const occurrences =
      authServiceSrc.split("'/api/v1/auth/refresh'").length - 1;
    expect(occurrences).toBe(1);

    const urlIdx = authServiceSrc.indexOf("'/api/v1/auth/refresh'");
    const openIdx = authServiceSrc.lastIndexOf('api.post(', urlIdx);
    expect(openIdx).toBeGreaterThan(-1);
    let depth = 0;
    let end = -1;
    for (let i = openIdx + 'api.post'.length; i < authServiceSrc.length; i += 1) {
      const ch = authServiceSrc[i];
      if (ch === '(') depth += 1;
      else if (ch === ')') {
        depth -= 1;
        if (depth === 0) {
          end = i;
          break;
        }
      }
    }
    expect(end).toBeGreaterThan(openIdx);
    const callSite = authServiceSrc.slice(openIdx, end + 1);
    expect(callSite).toContain('refresh_token'); // positive control
    expect(callSite).not.toMatch(/timeout/i);
    expect(callSite).not.toMatch(/signal|abort/i);
    // The removed constant must not come back as a footgun either.
    expect(authServiceSrc).not.toContain('BOOT_REFRESH_TIMEOUT_MS');
    expect(authService.BOOT_REFRESH_TIMEOUT_MS).toBeUndefined();
  });

  it('source fence: api.ts exposes no per-call refresh options to pass one through', () => {
    expect(apiSrc).toContain('getOrStartRefresh'); // positive control
    expect(apiSrc).toMatch(/export function getOrStartRefresh\(\s*\)/);
    expect(apiSrc).toMatch(/function performRefresh\(\s*\)/);
    expect(apiSrc).not.toContain('RefreshOptions');
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

  it('a transport-level timeout is still transient: the session survives an unreachable backend', async () => {
    // The client no longer ARMS a deadline (see P-A3 above), but the OS
    // or the server can still drop a socket. That shape must stay
    // transient — it must never be read as a dead session.
    await seedCachedSession();
    const sessionDied = jest.fn();
    onSessionInvalid(sessionDied);
    mockPost.mockRejectedValueOnce(
      Object.assign(new Error('socket hang up'), { code: 'ECONNABORTED' }),
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
    mockPost.mockResolvedValueOnce({
      data: {
        success: true,
        session: { access_token: 'at-new', refresh_token: 'rt-new' },
        user: FRESH_USER,
      },
    });

    const onSessionRefreshed = jest.fn();
    const user = await authService.initializeAuth(onSessionRefreshed);
    await settleBackground();

    expect(user).toEqual(CACHED_USER); // rendered from cache first
    expect(onSessionRefreshed).toHaveBeenCalledTimes(1);
    expect(onSessionRefreshed).toHaveBeenCalledWith(FRESH_USER);
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

  it('a logout mid-flight is not undone when the refresh lands (P-A3 session generation)', async () => {
    // Round-0 P3 carry-over, now reachable BY DESIGN: the boot refresh
    // runs in the background and (P-A3) is never cut short, so a logout
    // tap can land while it is open. Its completion must not write the
    // rotated tokens back over the cleared storage — that resurrects a
    // session the user ended, and the next launch boots into Main as the
    // logged-out user.
    await seedCachedSession();
    const post = pendingPost();
    const onSessionRefreshed = jest.fn();

    await authService.initializeAuth(onSessionRefreshed);
    await settleBackground();
    expect(mockPost).toHaveBeenCalledTimes(1); // positive control: in flight

    await authService.logout();
    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();

    post.resolve({
      data: {
        success: true,
        session: { access_token: 'at-new', refresh_token: 'rt-new' },
        user: FRESH_USER,
      },
    });
    await settleBackground();

    expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
    expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
    expect(await AsyncStorage.getItem(USER_KEY)).toBeNull();
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
 *
 * P-A3 — coalesced callers inherit the shared request, and that request
 * is un-abortable for all of them: the assertions below pin the two-arg
 * (config-free) POST from BOTH start orders.
 */
describe('boot refresh shares api.ts refresh mutex (A3 / R9)', () => {
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
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/refresh', {
      refresh_token: 'rt-cached',
    });

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

    // The interceptor wins the start this time; the request on the wire
    // is the same config-free one either way.
    const interceptorRefresh = apiModule.__testRefreshDedup();
    await settleBackground();
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/refresh', {
      refresh_token: 'rt-cached',
    });

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
