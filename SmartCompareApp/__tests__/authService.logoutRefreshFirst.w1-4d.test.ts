/**
 * W1-4d (retro fix of the W1-4 client half, PR #140) — logout must not
 * present a stale or expired session to POST /api/v1/auth/logout.
 *
 * The retro adversary measured the gap: /auth/logout sits on the 401
 * interceptor's skip-refresh list (api.ts), and logout() neither waits for
 * a refresh that is already in flight nor refreshes an access token whose
 * `exp` has passed. The server's get_current_user rejects that Bearer with
 * 401 BEFORE logout_user runs, so the upstream revocation never happens —
 * and when a refresh WAS in flight, the server finishes rotating RT1 -> RT2,
 * the P-A3 epoch guard discards RT2 on the phone, and RT2 stays live
 * upstream with nothing left to revoke it.
 *
 * Contract pinned here (orchestrator ruling for group R-CLIENT):
 *   - api.ts gains ONE read-only export, getInFlightRefresh(), returning the
 *     in-flight refresh Promise or null. Calling it never starts a refresh.
 *   - logout() first awaits an in-flight refresh (errors swallowed), THEN
 *     reads the stored pair.
 *   - If the access token's JWT `exp` has passed (payload decoded WITHOUT
 *     verification), logout() calls getOrStartRefresh() ONCE and uses the
 *     new pair. A malformed token (or one with no `exp`) is "expired-unknown"
 *     -> no refresh attempt, proceed as today.
 *   - Exactly ONE POST /api/v1/auth/logout, no retry loop; clearSession stays
 *     in `finally`, so local state is cleared on every path.
 *
 * Harness: the REAL api.ts and the REAL authService.ts. Only the transport
 * is swapped (a stub axios adapter on the real instance), so the request
 * interceptor that attaches the Bearer from storage, the 401 response
 * interceptor and its skip list, the refresh singleton and the P-A3 epoch
 * guard all run exactly as they do on a phone. The Authorization header
 * asserted below is the one the adapter RECEIVES — i.e. what goes on the
 * wire — not the one logout() passes in.
 *
 * Zero network: every test runs behind a guard that fails the test on any
 * socket connect, DNS lookup, node http(s) request or global fetch. The
 * stub adapter is the only transport.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(),
  SaveFormat: { JPEG: 'jpeg' },
}));

jest.mock('../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: jest.fn().mockResolvedValue('f'.repeat(64)),
}));

// ---------------------------------------------------------------------------
// Zero-network guard (autouse for every test in this file).
// ---------------------------------------------------------------------------

/* eslint-disable @typescript-eslint/no-require-imports */
const nodeNet = require('net');
const nodeDns = require('dns');
const nodeHttp = require('http');
const nodeHttps = require('https');
/* eslint-enable @typescript-eslint/no-require-imports */

const netAttempts: string[] = [];
const restorers: (() => void)[] = [];

function guard(obj: any, key: string, label: string): void {
  const original = obj[key];
  obj[key] = function blocked(...args: any[]) {
    const target = (() => {
      try {
        return typeof args[0] === 'string' ? args[0] : JSON.stringify(args[0]);
      } catch {
        return String(args[0]);
      }
    })();
    netAttempts.push(`${label}(${target})`);
    throw new Error(`W1-4d zero-network guard: ${label} attempted (${target})`);
  };
  restorers.push(() => {
    obj[key] = original;
  });
}

beforeAll(() => {
  guard(nodeNet.Socket.prototype, 'connect', 'net.Socket.connect');
  guard(nodeNet, 'connect', 'net.connect');
  guard(nodeNet, 'createConnection', 'net.createConnection');
  guard(nodeDns, 'lookup', 'dns.lookup');
  guard(nodeDns.promises, 'lookup', 'dns.promises.lookup');
  guard(nodeHttp, 'request', 'http.request');
  guard(nodeHttp, 'get', 'http.get');
  guard(nodeHttps, 'request', 'https.request');
  guard(nodeHttps, 'get', 'https.get');
  if (typeof (globalThis as any).fetch === 'function') {
    guard(globalThis as any, 'fetch', 'fetch');
  }
});

afterAll(() => {
  while (restorers.length) restorers.pop()!();
});

// ---------------------------------------------------------------------------
// Real modules (loaded once; state reset per test below).
// ---------------------------------------------------------------------------

/* eslint-disable @typescript-eslint/no-require-imports */
const authService = require('../src/services/authService');
const apiModule = require('../src/services/api');
/* eslint-enable @typescript-eslint/no-require-imports */

const TOKEN_KEY = 'qaren_token';
const REFRESH_KEY = 'qaren_refresh_token';
const USER_KEY = '@qaren_user';

const LOGOUT_URL = '/api/v1/auth/logout';
const REFRESH_URL = '/api/v1/auth/refresh';

const RT1 = 'rt1-old-9f3a';
const RT2 = 'rt2-rotated-4c1d';

function b64url(obj: unknown): string {
  return Buffer.from(JSON.stringify(obj)).toString('base64url');
}

/** An unsigned-but-well-formed JWT. logout() must decode WITHOUT verifying. */
function jwt(payload: Record<string, unknown>): string {
  return `${b64url({ alg: 'HS256', typ: 'JWT' })}.${b64url(payload)}.c2lnbmF0dXJl`;
}

const nowSec = () => Math.floor(Date.now() / 1000);
const EXPIRED_AT1 = jwt({ sub: 'u1', exp: nowSec() - 120, marker: 'AT1-expired' });
const VALID_AT1 = jwt({ sub: 'u1', exp: nowSec() + 3600, marker: 'AT1-valid' });
const VALID_AT2 = jwt({ sub: 'u1', exp: nowSec() + 3600, marker: 'AT2-fresh' });

// ---------------------------------------------------------------------------
// Stub transport on the REAL axios instance.
// ---------------------------------------------------------------------------

type Seen = {
  url: string;
  baseURL: string | undefined;
  method: string | undefined;
  auth: string | undefined;
  body: any;
  refreshSettledAtSend: boolean;
};

let seen: Seen[] = [];
let routes: Record<string, (config: any) => Promise<any>> = {};
let refreshSettled = false;

function readAuthHeader(config: any): string | undefined {
  const h = config?.headers;
  if (!h) return undefined;
  if (typeof h.get === 'function') return h.get('Authorization') ?? h.Authorization;
  return h.Authorization;
}

function parseBody(data: any): any {
  if (typeof data !== 'string') return data;
  try {
    return JSON.parse(data);
  } catch {
    return data;
  }
}

function ok(config: any, data: any) {
  return { data, status: 200, statusText: 'OK', headers: {}, config };
}

function httpError(config: any, status: number, data: any = {}): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.config = config;
  err.response = { status, statusText: String(status), data, headers: {}, config };
  return err;
}

function networkError(config: any): any {
  const err: any = new Error('Network Error');
  err.isAxiosError = true;
  err.code = 'ERR_NETWORK';
  err.config = config;
  return err;
}

function refreshOk(config: any) {
  return ok(config, {
    success: true,
    session: { access_token: VALID_AT2, refresh_token: RT2 },
    user: { id: 'u1', email: 'u1@qaren.test' },
  });
}

/** A refresh POST that stays in flight until the test settles it. */
function deferredRefresh(): {
  resolve: () => void;
  rejectNetwork: () => void;
  reject401: () => void;
} {
  const handles: any = {};
  routes[REFRESH_URL] = (config: any) =>
    new Promise((res, rej) => {
      handles.resolve = () => {
        refreshSettled = true;
        res(refreshOk(config));
      };
      handles.rejectNetwork = () => {
        refreshSettled = true;
        rej(networkError(config));
      };
      handles.reject401 = () => {
        refreshSettled = true;
        rej(httpError(config, 401, { detail: 'Invalid refresh token' }));
      };
    });
  return handles;
}

async function settle(rounds = 20): Promise<void> {
  for (let i = 0; i < rounds; i += 1) {
    await new Promise((r) => setImmediate(r));
  }
}

const calls = (url: string) => seen.filter((s) => s.url === url);

async function seed(access: string | null, refresh: string | null): Promise<void> {
  if (access !== null) await SecureStore.setItemAsync(TOKEN_KEY, access);
  if (refresh !== null) await SecureStore.setItemAsync(REFRESH_KEY, refresh);
  await AsyncStorage.setItem(USER_KEY, JSON.stringify({ id: 'u1' }));
}

async function expectLocalCleared(): Promise<void> {
  expect(await SecureStore.getItemAsync(TOKEN_KEY)).toBeNull();
  expect(await SecureStore.getItemAsync(REFRESH_KEY)).toBeNull();
  expect(await AsyncStorage.getItem(USER_KEY)).toBeNull();
}

beforeEach(async () => {
  netAttempts.length = 0;
  seen = [];
  refreshSettled = false;
  routes = {
    [LOGOUT_URL]: async (config: any) => ok(config, { success: true }),
    [REFRESH_URL]: async (config: any) => {
      refreshSettled = true;
      return refreshOk(config);
    },
  };
  (SecureStore as any).__reset();
  await AsyncStorage.clear();
  apiModule.__resetRefreshMutex();

  (apiModule.api as any).defaults.adapter = async (config: any) => {
    seen.push({
      url: config.url,
      baseURL: config.baseURL,
      method: config.method,
      auth: readAuthHeader(config),
      body: parseBody(config.data),
      refreshSettledAtSend: refreshSettled,
    });
    const handler = routes[config.url];
    if (!handler) throw httpError(config, 404, { detail: `unrouted ${config.url}` });
    return handler(config);
  };
});

afterEach(() => {
  // Autouse zero-network assertion: the stub adapter is the only transport.
  expect(netAttempts).toEqual([]);
  // Every request that DID go out went through the axios instance to the
  // one configured backend, on an auth path.
  for (const s of seen) {
    expect(s.baseURL).toBe(apiModule.API_BASE_URL);
    expect(s.url.startsWith('/api/v1/auth/')).toBe(true);
    expect(s.method).toBe('post');
  }
});

// ---------------------------------------------------------------------------
// The new read-only export.
// ---------------------------------------------------------------------------

describe('api.getInFlightRefresh — read-only view of the refresh singleton', () => {
  it('is exported as a function', () => {
    expect(typeof apiModule.getInFlightRefresh).toBe('function');
  });

  it('returns null when idle, the SAME Promise while a refresh is in flight, null after it settles, and never starts one', async () => {
    await seed(VALID_AT1, RT1);
    const refresh = deferredRefresh();

    expect(apiModule.getInFlightRefresh()).toBeNull();
    await settle();
    expect(calls(REFRESH_URL)).toHaveLength(0); // reading never starts a refresh

    const inflight = apiModule.getOrStartRefresh();
    await settle();
    expect(calls(REFRESH_URL)).toHaveLength(1); // positive control: in flight
    expect(apiModule.getInFlightRefresh()).toBe(inflight);

    refresh.resolve();
    await inflight;
    await settle();
    expect(apiModule.getInFlightRefresh()).toBeNull();
    expect(calls(REFRESH_URL)).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// Red (1): logout during an in-flight refresh.
// ---------------------------------------------------------------------------

describe('logout waits for a refresh that is already in flight', () => {
  it('sends the NEW pair (AT2/RT2) once the in-flight refresh lands — never the stale AT1/RT1', async () => {
    await seed(EXPIRED_AT1, RT1);
    const refresh = deferredRefresh();

    // The boot refresh / a coalesced 401 is mid-flight when the user taps
    // "Log out".
    const inflight = apiModule.getOrStartRefresh();
    await settle();
    expect(calls(REFRESH_URL)).toHaveLength(1); // positive control
    expect(calls(REFRESH_URL)[0].body).toEqual({ refresh_token: RT1 });

    const loggingOut = authService.logout();
    await settle();
    refresh.resolve();
    await expect(loggingOut).resolves.toBeUndefined();
    await inflight.catch(() => undefined);
    await settle();

    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(1);
    expect(logouts[0].auth).toBe(`Bearer ${VALID_AT2}`);
    expect(logouts[0].body).toEqual({ refresh_token: RT2 });
    // AT2 is unexpired, so the in-flight refresh is the ONLY refresh.
    expect(calls(REFRESH_URL)).toHaveLength(1);
    await expectLocalCleared();
  });

  it('does not send the logout POST until the in-flight refresh settles, and swallows its failure', async () => {
    await seed(VALID_AT1, RT1);
    const refresh = deferredRefresh();

    const inflight = apiModule.getOrStartRefresh();
    await settle();
    expect(calls(REFRESH_URL)).toHaveLength(1); // positive control

    const loggingOut = authService.logout();
    await settle();
    refresh.rejectNetwork(); // transient: the stored pair is still the live one
    await expect(loggingOut).resolves.toBeUndefined();
    await inflight.catch(() => undefined);

    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(1);
    expect(logouts[0].refreshSettledAtSend).toBe(true);
    expect(logouts[0].auth).toBe(`Bearer ${VALID_AT1}`);
    expect(logouts[0].body).toEqual({ refresh_token: RT1 });
    expect(calls(REFRESH_URL)).toHaveLength(1); // AT1 unexpired: no second refresh
    await expectLocalCleared();
  });

  it('pin: an in-flight refresh that dies with 401 never produces a retry loop and local state is cleared', async () => {
    await seed(VALID_AT1, RT1);
    const refresh = deferredRefresh();

    const inflight = apiModule.getOrStartRefresh();
    await settle();

    const loggingOut = authService.logout();
    await settle();
    refresh.reject401();
    await expect(loggingOut).resolves.toBeUndefined();
    await inflight.catch(() => undefined);
    await settle();

    expect(calls(REFRESH_URL)).toHaveLength(1);
    expect(calls(LOGOUT_URL).length).toBeLessThanOrEqual(1);
    await expectLocalCleared();
  });
});

// ---------------------------------------------------------------------------
// Red (2): an expired access token is refreshed ONCE before the logout POST.
// ---------------------------------------------------------------------------

describe('logout refreshes an expired access token exactly once first', () => {
  it('refreshes with RT1, then posts ONE logout carrying AT2/RT2', async () => {
    await seed(EXPIRED_AT1, RT1);

    await expect(authService.logout()).resolves.toBeUndefined();

    expect(seen.map((s) => s.url)).toEqual([REFRESH_URL, LOGOUT_URL]);
    expect(calls(REFRESH_URL)[0].body).toEqual({ refresh_token: RT1 });
    const [logoutCall] = calls(LOGOUT_URL);
    expect(logoutCall.auth).toBe(`Bearer ${VALID_AT2}`);
    expect(logoutCall.body).toEqual({ refresh_token: RT2 });
    await expectLocalCleared();
  });

  it('a transient refresh failure costs neither the logout POST nor the local clear (one refresh, one logout)', async () => {
    await seed(EXPIRED_AT1, RT1);
    routes[REFRESH_URL] = async (config: any) => {
      refreshSettled = true;
      throw networkError(config);
    };

    await expect(authService.logout()).resolves.toBeUndefined();

    expect(calls(REFRESH_URL)).toHaveLength(1);
    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(1);
    expect(logouts[0].refreshSettledAtSend).toBe(true);
    expect(logouts[0].body).toEqual({ refresh_token: RT1 });
    await expectLocalCleared();
  });

  it('a refresh refused with 401 is attempted once, never retried, and local state is cleared', async () => {
    await seed(EXPIRED_AT1, RT1);
    routes[REFRESH_URL] = async (config: any) => {
      refreshSettled = true;
      throw httpError(config, 401, { detail: 'Invalid refresh token' });
    };

    await expect(authService.logout()).resolves.toBeUndefined();

    expect(calls(REFRESH_URL)).toHaveLength(1);
    expect(calls(LOGOUT_URL).length).toBeLessThanOrEqual(1);
    await expectLocalCleared();
  });

  it('pin: an UNEXPIRED JWT is sent as-is with no refresh (exp is seconds, not ms)', async () => {
    await seed(VALID_AT1, RT1);

    await authService.logout();

    expect(calls(REFRESH_URL)).toHaveLength(0);
    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(1);
    expect(logouts[0].auth).toBe(`Bearer ${VALID_AT1}`);
    expect(logouts[0].body).toEqual({ refresh_token: RT1 });
    await expectLocalCleared();
  });

  it.each([
    ['an opaque non-JWT string', 'at-live'],
    ['two segments', 'aaa.bbb'],
    ['a payload that is not base64url JSON', 'aaa.%%%not-base64%%%.ccc'],
    ['a payload that decodes to non-JSON', `${b64url({ alg: 'HS256' })}.${Buffer.from('not json').toString('base64url')}.sig`],
    ['a JWT with no exp claim', jwt({ sub: 'u1' })],
    ['a JWT whose exp is not a number', jwt({ sub: 'u1', exp: 'soon' })],
  ])('pin: %s is expired-UNKNOWN -> no refresh attempt, one logout POST as today', async (_label, token) => {
    await seed(token, RT1);

    await expect(authService.logout()).resolves.toBeUndefined();

    expect(calls(REFRESH_URL)).toHaveLength(0);
    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(1);
    expect(logouts[0].auth).toBe(`Bearer ${token}`);
    expect(logouts[0].body).toEqual({ refresh_token: RT1 });
    await expectLocalCleared();
  });

  it('pin: no access token stored -> no refresh, no logout POST, local state cleared', async () => {
    await seed(null, RT1);

    await expect(authService.logout()).resolves.toBeUndefined();

    expect(seen).toHaveLength(0);
    await expectLocalCleared();
  });
});

// ---------------------------------------------------------------------------
// Red (3) / pins: a 401 from /auth/logout itself.
// ---------------------------------------------------------------------------

describe('a 401 from /auth/logout clears local state and never loops', () => {
  it('pin: valid token, logout answers 401 -> no refresh (skip list), exactly one logout POST, cleared', async () => {
    await seed(VALID_AT1, RT1);
    routes[LOGOUT_URL] = async (config: any) => {
      throw httpError(config, 401, { detail: 'Invalid or expired token' });
    };

    await expect(authService.logout()).resolves.toBeUndefined();
    await settle();

    expect(calls(REFRESH_URL)).toHaveLength(0);
    expect(calls(LOGOUT_URL)).toHaveLength(1);
    await expectLocalCleared();
  });

  it('expired token: one refresh, then ONE logout that 401s — no second refresh, no second logout, cleared', async () => {
    await seed(EXPIRED_AT1, RT1);
    routes[LOGOUT_URL] = async (config: any) => {
      throw httpError(config, 401, { detail: 'Invalid or expired token' });
    };

    await expect(authService.logout()).resolves.toBeUndefined();
    await settle();

    expect(calls(REFRESH_URL)).toHaveLength(1);
    expect(calls(LOGOUT_URL)).toHaveLength(1);
    expect(calls(LOGOUT_URL)[0].auth).toBe(`Bearer ${VALID_AT2}`);
    await expectLocalCleared();
  });

  it('pin: the rotated pair from the pre-logout refresh is NOT resurrected after the clear', async () => {
    await seed(EXPIRED_AT1, RT1);

    await authService.logout();
    await settle();

    await expectLocalCleared();
    expect(await authService.getToken()).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Pins that must stay true through the fix.
// ---------------------------------------------------------------------------

describe('logout never leaks either token pair to the console', () => {
  it.each([
    ['expired token (refresh-first path)', EXPIRED_AT1, false],
    ['in-flight refresh path', EXPIRED_AT1, true],
    ['valid token, server 401', VALID_AT1, false],
  ])('writes no token value on the %s, even with __DEV__ on', async (_label, access, inflightFirst) => {
    await seed(access as string, RT1);
    let inflight: Promise<unknown> | null = null;
    let refresh: ReturnType<typeof deferredRefresh> | null = null;
    if (inflightFirst) {
      refresh = deferredRefresh();
      inflight = apiModule.getOrStartRefresh();
      await settle();
    }
    routes[LOGOUT_URL] = async (config: any) => {
      throw httpError(config, 401, { detail: 'Invalid or expired token' });
    };

    const prevDev = (globalThis as any).__DEV__;
    (globalThis as any).__DEV__ = true;
    const spies = (['log', 'info', 'warn', 'error', 'debug'] as const).map((m) =>
      jest.spyOn(console, m).mockImplementation(() => {}),
    );
    try {
      const loggingOut = authService.logout();
      await settle();
      refresh?.resolve();
      await loggingOut;
      await inflight?.catch(() => undefined);
      await settle();

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

      for (const secret of [EXPIRED_AT1, VALID_AT1, VALID_AT2, RT1, RT2]) {
        expect(written).not.toContain(secret);
      }
    } finally {
      spies.forEach((s) => s.mockRestore());
      (globalThis as any).__DEV__ = prevDev;
    }
  });
});

describe('the logout request goes only to API_BASE_URL through the axios instance', () => {
  it('pin: the configured base URL is the production backend and the axios instance carries it', () => {
    expect(apiModule.API_BASE_URL).toMatch(/^https:\/\//);
    expect((apiModule.api as any).defaults.baseURL).toBe(apiModule.API_BASE_URL);
  });

  it('pin: /auth/logout stays on the interceptor skip-refresh list (source)', () => {
    /* eslint-disable @typescript-eslint/no-require-imports */
    const src: string = require('fs').readFileSync(
      require('path').join(__dirname, '../src/services/api.ts'),
      'utf8',
    );
    /* eslint-enable @typescript-eslint/no-require-imports */
    const m = src.match(/const authFlowEndpoints = \[([^\]]*)\]/);
    expect(m).not.toBeNull();
    expect(m![1]).toContain("'/auth/logout'");
    expect(m![1]).toContain("'/auth/refresh'");
  });
});

// ---------------------------------------------------------------------------
// Green-phase pins for the Fable red-gate rulings (1) and (2).
// ---------------------------------------------------------------------------

describe('logout never blocks on a black-holed refresh (ruling 1: 5 s bound on the WAIT)', () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  it('pin: a refresh that never settles lets logout send ONE POST after the bound and clear state', async () => {
    await seed(EXPIRED_AT1, RT1);
    const refresh = deferredRefresh();
    jest.useFakeTimers({ doNotFake: ['setImmediate', 'nextTick', 'queueMicrotask'] });

    const inflight = apiModule.getOrStartRefresh();
    await settle();
    expect(calls(REFRESH_URL)).toHaveLength(1); // positive control: hung on the wire

    let done = false;
    const loggingOut = authService.logout().then(() => {
      done = true;
    });
    await settle();
    jest.advanceTimersByTime(4_999);
    await settle();
    expect(done).toBe(false); // still inside the bound: it does wait
    expect(calls(LOGOUT_URL)).toHaveLength(0);

    jest.advanceTimersByTime(1);
    await settle();
    expect(done).toBe(true);
    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(1);
    expect(logouts[0].refreshSettledAtSend).toBe(false);
    // Freshest pair available = the stored one; no second refresh is queued
    // behind the hung one (getOrStartRefresh would coalesce onto it).
    expect(logouts[0].auth).toBe(`Bearer ${EXPIRED_AT1}`);
    expect(logouts[0].body).toEqual({ refresh_token: RT1 });
    expect(calls(REFRESH_URL)).toHaveLength(1);
    await expectLocalCleared();
    await loggingOut;

    // The request itself was never cut short (P-A3); when it finally lands
    // after the logout, the epoch guard keeps its pair out of storage.
    refresh.resolve();
    await inflight.catch(() => undefined);
    await settle();
    await expectLocalCleared();
  });
});

describe('a refresh landing after the logout epoch bump (ruling 2: P-A3 by construction)', () => {
  it('pin: the rotated pair is never written to storage, yet it is what the logout POST carries', async () => {
    await seed(EXPIRED_AT1, RT1);
    const refresh = deferredRefresh();
    const inflight = apiModule.getOrStartRefresh();
    await settle();

    const setSpy = jest.spyOn(SecureStore, 'setItemAsync');
    try {
      const loggingOut = authService.logout();
      await settle();
      refresh.resolve();
      await loggingOut;
      await inflight.catch(() => undefined);
      await settle();

      const written = setSpy.mock.calls.map((c) => c[1]);
      expect(written).not.toContain(VALID_AT2);
      expect(written).not.toContain(RT2);
      const logouts = calls(LOGOUT_URL);
      expect(logouts).toHaveLength(1);
      expect(logouts[0].auth).toBe(`Bearer ${VALID_AT2}`);
      expect(logouts[0].body).toEqual({ refresh_token: RT2 });
      await expectLocalCleared();
    } finally {
      setSpy.mockRestore();
    }
  });
});

// ---------------------------------------------------------------------------
// Retro-fix pins (R-CLIENT adversary on the W1-4d green).
// ---------------------------------------------------------------------------

const VALID_B = jwt({ sub: 'uB', exp: nowSec() + 3600, marker: 'B-valid' });
const RT_B = 'rtB-user-b-7777';

describe('the handoff only carries a refresh that belongs to the session this logout ends', () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  it('ADV-A1 pin: a refresh of user A hung across logout -> login(B) -> logout never makes the logout of B present the rotated pair of A', async () => {
    await seed(VALID_AT1, RT1);
    const refresh = deferredRefresh();
    jest.useFakeTimers({ doNotFake: ['setImmediate', 'nextTick', 'queueMicrotask'] });

    const inflight = apiModule.getOrStartRefresh();
    await settle();
    expect(calls(REFRESH_URL)).toHaveLength(1); // positive control: the refresh of A is on the wire

    // Logout #1 (user A) gives up waiting at the bound.
    const l1 = authService.logout();
    await settle();
    jest.advanceTimersByTime(5_000);
    await settle();
    await l1;
    expect(calls(LOGOUT_URL)).toHaveLength(1);

    // User B signs in through the real login().
    routes['/api/v1/auth/login'] = async (config: any) =>
      ok(config, { user: { id: 'uB' }, session: { access_token: VALID_B, refresh_token: RT_B } });
    const res = await authService.login('b@qaren.test', 'pw');
    expect(res.success).toBe(true);
    expect(await authService.getToken()).toBe(VALID_B);
    expect(apiModule.getInFlightRefresh()).toBe(inflight); // the refresh of A is still the singleton

    // Logout #2 (user B) while the refresh of A lands with the rotated pair of A.
    const l2 = authService.logout();
    await settle();
    refresh.resolve();
    await l2;
    await inflight.catch(() => undefined);
    await settle();

    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(2);
    expect(logouts[1].auth).toBe(`Bearer ${VALID_B}`);
    expect(logouts[1].body).toEqual({ refresh_token: RT_B });
    await expectLocalCleared();
  });

  it('pin: the handoff is released when logout finishes, so a refresh landing afterwards leaves no pair in memory', async () => {
    await seed(EXPIRED_AT1, RT1);
    const refresh = deferredRefresh();
    jest.useFakeTimers({ doNotFake: ['setImmediate', 'nextTick', 'queueMicrotask'] });

    const inflight = apiModule.getOrStartRefresh();
    await settle();
    expect(authService.__pendingLogoutHandoffCount()).toBe(0);

    const loggingOut = authService.logout();
    await settle();
    expect(authService.__pendingLogoutHandoffCount()).toBe(1); // positive control: registered while preparing
    jest.advanceTimersByTime(5_000);
    await settle();
    await loggingOut;
    expect(authService.__pendingLogoutHandoffCount()).toBe(0);

    refresh.resolve(); // the hung refresh lands after the logout finished
    await inflight.catch(() => undefined);
    await settle();
    expect(authService.__pendingLogoutHandoffCount()).toBe(0);
    await expectLocalCleared();
  });

  it('pin: a 200 refresh with success:false is never handed off (the stored pair is sent)', async () => {
    await seed(VALID_AT1, RT1);
    let land: () => void = () => {};
    routes[REFRESH_URL] = (config: any) =>
      new Promise((res) => {
        land = () => {
          refreshSettled = true;
          res(ok(config, { success: false, session: { access_token: 'AT-refused', refresh_token: 'RT-refused' } }));
        };
      });
    const inflight = apiModule.getOrStartRefresh();
    await settle();

    const loggingOut = authService.logout();
    await settle();
    land();
    await loggingOut;
    await inflight.catch(() => undefined);

    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(1);
    expect(logouts[0].auth).toBe(`Bearer ${VALID_AT1}`);
    expect(logouts[0].body).toEqual({ refresh_token: RT1 });
    await expectLocalCleared();
  });

  it('pin: a handed-off session without a refresh_token sends AT2 with the stored refresh token (what storage would hold)', async () => {
    await seed(EXPIRED_AT1, RT1);
    let land: () => void = () => {};
    routes[REFRESH_URL] = (config: any) =>
      new Promise((res) => {
        land = () => {
          refreshSettled = true;
          res(ok(config, { success: true, session: { access_token: VALID_AT2 }, user: { id: 'u1' } }));
        };
      });
    const inflight = apiModule.getOrStartRefresh();
    await settle();

    const loggingOut = authService.logout();
    await settle();
    land();
    await loggingOut;
    await inflight.catch(() => undefined);

    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(1);
    expect(logouts[0].auth).toBe(`Bearer ${VALID_AT2}`);
    expect(logouts[0].body).toEqual({ refresh_token: RT1 });
    expect(calls(REFRESH_URL)).toHaveLength(1); // AT2 is unexpired: no second refresh
    await expectLocalCleared();
  });
});

describe('an in-flight refresh that fails transiently, then an expired token', () => {
  it('pin: costs exactly one more bounded refresh, and the logout carries the pair it produced', async () => {
    await seed(EXPIRED_AT1, RT1);
    let failFirst: () => void = () => {};
    let n = 0;
    routes[REFRESH_URL] = (config: any) => {
      n += 1;
      if (n === 1) {
        return new Promise((_res, rej) => {
          failFirst = () => {
            refreshSettled = true;
            rej(networkError(config));
          };
        });
      }
      refreshSettled = true;
      return Promise.resolve(refreshOk(config));
    };
    const inflight = apiModule.getOrStartRefresh();
    await settle();
    expect(calls(REFRESH_URL)).toHaveLength(1); // positive control

    const loggingOut = authService.logout();
    await settle();
    failFirst();
    await loggingOut;
    await inflight.catch(() => undefined);

    expect(seen.map((s) => s.url)).toEqual([REFRESH_URL, REFRESH_URL, LOGOUT_URL]);
    const [logoutCall] = calls(LOGOUT_URL);
    expect(logoutCall.auth).toBe(`Bearer ${VALID_AT2}`);
    expect(logoutCall.body).toEqual({ refresh_token: RT2 });
    await expectLocalCleared();
  });
});

describe('the logout bound leaves no timer behind', () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  it.each([
    ['an in-flight refresh that lands inside the bound', true],
    ['the expired-token refresh', false],
  ])('pin: after %s, no timer is pending', async (_label, inflightFirst) => {
    await seed(EXPIRED_AT1, RT1);
    jest.useFakeTimers({ doNotFake: ['setImmediate', 'nextTick', 'queueMicrotask'] });
    let inflight: Promise<unknown> | null = null;
    let refresh: ReturnType<typeof deferredRefresh> | null = null;
    if (inflightFirst) {
      refresh = deferredRefresh();
      inflight = apiModule.getOrStartRefresh();
      await settle();
    }
    expect(jest.getTimerCount()).toBe(0);

    const loggingOut = authService.logout();
    await settle();
    refresh?.resolve();
    await loggingOut;
    await inflight?.catch(() => undefined);
    await settle();

    expect(calls(REFRESH_URL)).toHaveLength(1); // positive control: a bounded wait happened
    expect(calls(LOGOUT_URL)[0].auth).toBe(`Bearer ${VALID_AT2}`);
    expect(jest.getTimerCount()).toBe(0);
  });
});

describe('isJwtExpired edges (decoded WITHOUT verification)', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('pin: exp equal to now counts as expired (the token is no longer valid AT exp)', async () => {
    const now = 1_800_000_000_000;
    jest.spyOn(Date, 'now').mockReturnValue(now);
    await seed(jwt({ sub: 'u1', exp: now / 1000 }), RT1);

    await authService.logout();

    expect(calls(REFRESH_URL)).toHaveLength(1);
    expect(calls(LOGOUT_URL)[0].auth).toBe(`Bearer ${VALID_AT2}`);
  });

  it('pin: exp one second after now is NOT expired (positive control for the boundary)', async () => {
    const now = 1_800_000_000_000;
    jest.spyOn(Date, 'now').mockReturnValue(now);
    const token = jwt({ sub: 'u1', exp: now / 1000 + 1 });
    await seed(token, RT1);

    await authService.logout();

    expect(calls(REFRESH_URL)).toHaveLength(0);
    expect(calls(LOGOUT_URL)[0].auth).toBe(`Bearer ${token}`);
  });

  /** A base64url payload whose length is a multiple of 4 (no partial group). */
  function alignedPayload(): string {
    for (let pad = 0; pad < 3; pad += 1) {
      const p = b64url({ sub: 'u1', exp: nowSec() - 120, p: 'x'.repeat(pad) });
      if (p.length % 4 === 0) return p;
    }
    throw new Error('unreachable');
  }

  it('control: the aligned expired payload itself IS expired (one refresh)', async () => {
    const token = `${b64url({ alg: 'HS256' })}.${alignedPayload()}.sig`;
    await seed(token, RT1);

    await authService.logout();

    expect(calls(REFRESH_URL)).toHaveLength(1);
  });

  it('pin: a payload whose base64url length is 1 mod 4 is malformed -> expired-UNKNOWN, no refresh', async () => {
    const token = `${b64url({ alg: 'HS256' })}.${alignedPayload()}A.sig`;
    await seed(token, RT1);

    await authService.logout();

    expect(calls(REFRESH_URL)).toHaveLength(0);
    const logouts = calls(LOGOUT_URL);
    expect(logouts).toHaveLength(1);
    expect(logouts[0].auth).toBe(`Bearer ${token}`);
  });

  it('pin: a non-finite exp (JSON -1e999 parses to -Infinity) is expired-UNKNOWN, no refresh', async () => {
    const raw = '{"sub":"u1","exp":-1e999}';
    expect(JSON.parse(raw).exp).toBe(-Infinity); // the premise: JSON CAN yield a non-finite number
    const token = `${b64url({ alg: 'HS256' })}.${Buffer.from(raw).toString('base64url')}.sig`;
    await seed(token, RT1);

    await authService.logout();

    expect(calls(REFRESH_URL)).toHaveLength(0);
    expect(calls(LOGOUT_URL)[0].auth).toBe(`Bearer ${token}`);
  });
});
