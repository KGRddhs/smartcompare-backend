/**
 * S71 U13c (issue #298) -- the camera upload's 401 gets ONE refresh through the
 * single flight and ONE retry with the same FormData, inside one deadline.
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U13C_CAMERA_401_SPEC.md
 * (sections 3 and 5.1/5.2 as superseded by "Review corrections" 1-7 and 9 and by
 * "Orchestrator rulings" UR1-UR8).
 *
 * Base (72b13bc5): identifyFromImages (src/services/api.ts) is a raw RN fetch
 * with no 401 handling: one fetch, no refresh, a thrown `Server error 401`.
 * Contract pinned here:
 *   - any first 401 -> exactly one getOrStartRefresh() (the exported zero-argument
 *     single flight, so refreshSession() runs once even when another caller's
 *     refresh is already in flight) -> on success exactly one retry: same URL,
 *     POST, the SAME FormData (2 parts, no second manipulateAsync), headers exactly
 *     { Authorization: 'Bearer <new token>' }, the SAME AbortSignal;
 *   - the retry's response goes through the existing handling (200 data, 429 H3
 *     tag, `Server error <status>` axios-shaped error);
 *   - a failed or rejecting refresh: no retry, the FIRST 401's axios-shaped error
 *     (never the refresh error); the camera never clears or emits itself;
 *   - one IDENTIFY_TIMEOUT_MS budget for the whole call; the refresh WAIT is raced
 *     against the deadline (never the refresh itself);
 *   - a 403 or any other non-401 never refreshes; no token is ever logged or
 *     carried on a thrown error.
 *
 * Harness: api.sessionGate.m18.test.ts (the REAL api.ts refresh singleton,
 * authService mocked at the boundary, the REAL sessionEvents observed through a
 * listener). Response fakes are SINGLE-READ like whatwg-fetch's consumed(): a
 * second text()/json() on the same object rejects TypeError('Already read').
 * Fake timers only in T10/T11 (the deadline); nothing depends on wall-clock time.
 */

import { classifyLoadFailure, isCameraEngineOutage } from '../src/services/failureClassification';

jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

const mockRefreshSession = jest.fn();
const mockGetToken = jest.fn();
const mockClearSession = jest.fn();

jest.mock('../src/services/authService', () => ({
  getToken: (...args: any[]) => mockGetToken(...args),
  refreshSession: (...args: any[]) => mockRefreshSession(...args),
  clearSession: (...args: any[]) => mockClearSession(...args),
}));

jest.mock('axios', () => {
  const instance = {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    request: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  const instanceFn: any = jest.fn();
  Object.assign(instanceFn, instance);
  return { create: jest.fn(() => instanceFn), __instance: instanceFn };
});

const mockManipulateAsync = jest.fn();
jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: (...args: any[]) => mockManipulateAsync(...args),
  SaveFormat: { JPEG: 'jpeg' },
}));

// T16 -- every Sentry surface reachable from api.ts is a jest.fn whose calls are
// read back (the global __mocks__/sentry-react-native.ts exports plain functions).
const mockSentryService: Record<string, jest.Mock> = {
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: jest.fn((s: string) => s),
  scrubBeforeSend: jest.fn((e: any) => e),
  scrubBeforeBreadcrumb: jest.fn((b: any) => b),
  scrubBeforeSendTransaction: jest.fn((e: any) => e),
};
jest.mock('../src/services/sentry', () => mockSentryService);

const mockSentryRN: Record<string, jest.Mock> = {
  setTag: jest.fn(),
  setTags: jest.fn(),
  setContext: jest.fn(),
  setExtra: jest.fn(),
  setUser: jest.fn(),
  captureMessage: jest.fn(),
  captureException: jest.fn(),
  captureEvent: jest.fn(),
  addBreadcrumb: jest.fn(),
  addIntegration: jest.fn(),
  init: jest.fn(),
  getCurrentScope: jest.fn(() => ({
    setTag: mockSentryRN.setTag,
    setTags: mockSentryRN.setTags,
    setContext: mockSentryRN.setContext,
    setExtra: mockSentryRN.setExtra,
    setUser: mockSentryRN.setUser,
    clear: jest.fn(),
  })),
  withScope: jest.fn((cb: (scope: any) => void) => cb(mockSentryRN.getCurrentScope())),
  startSpan: jest.fn((_opts: any, cb: (span: any) => any) => cb({ end: jest.fn() })),
  startInactiveSpan: jest.fn(() => ({ end: jest.fn() })),
  startSpanManual: jest.fn((_opts: any, cb: (span: any) => any) => cb({ end: jest.fn() })),
  getClient: jest.fn(() => null),
  lastEventId: jest.fn(() => null),
};
jest.mock('@sentry/react-native', () => ({
  __esModule: true,
  ...mockSentryRN,
  default: mockSentryRN,
}));

// Captured before any test installs fake timers: a REAL macrotask yield drains
// every pending microtask without moving fake time.
const realSetImmediate: (cb: () => void) => unknown = setImmediate;
async function flushReal(rounds = 10): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await new Promise<void>((resolve) => {
      realSetImmediate(resolve);
    });
  }
}

const URIS = ['file:///a.jpg', 'file:///b.jpg'];

const AUTH_ENVELOPE = {
  success: false,
  code: 'AUTH_REQUIRED',
  error: 'Sign in to continue.',
  request_id: 'r',
};
const AUTH_BODY = JSON.stringify(AUTH_ENVELOPE);
const AUTH_ENVELOPE_2 = { ...AUTH_ENVELOPE, request_id: 'r2' };
const AUTH_BODY_2 = JSON.stringify(AUTH_ENVELOPE_2);
const OK_DATA = {
  action: 'comparison',
  success: true,
  result: { overview: { winner: 'A' } },
};
const OK_BODY = JSON.stringify(OK_DATA);
const USAGE_BODY = JSON.stringify({
  detail: { error: 'Daily limit reached', code: 'USAGE_LIMIT', tier: 'free', remaining: 0 },
});
const INTERNAL_ENVELOPE = {
  success: false,
  code: 'INTERNAL_ERROR',
  error: 'Something went wrong.',
  request_id: 'r5',
};
const INTERNAL_BODY = JSON.stringify(INTERNAL_ENVELOPE);
const COMPARISON_FAILED = {
  success: false,
  action: 'comparison_failed',
  code: 'INTERNAL_ERROR',
  error: 'The comparison did not finish.',
};
const FORBIDDEN_ENVELOPE = { success: false, code: 'FORBIDDEN', error: 'x' };

/** A whatwg-fetch-like Response: the body can be read ONCE (fetch.umd.js consumed()). */
function mkResponse(status: number, body: string) {
  let used = false;
  const read = (): Promise<string> => {
    if (used) return Promise.reject(new TypeError('Already read'));
    used = true;
    return Promise.resolve(body);
  };
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => read(),
    json: () => read().then((text) => JSON.parse(text)),
  };
}

function abortError(): Error {
  return Object.assign(new Error('Aborted'), { name: 'AbortError' });
}

/** A request that never answers; it rejects AbortError when its signal aborts (whatwg-fetch). */
function hangUntilAbort(signal: AbortSignal): Promise<never> {
  return new Promise<never>((_resolve, reject) => {
    if (signal.aborted) {
      reject(abortError());
      return;
    }
    signal.addEventListener('abort', () => reject(abortError()), { once: true });
  });
}

type Outcome =
  | { status: 'pending' }
  | { status: 'resolved'; value: any }
  | { status: 'rejected'; error: any };

function track(p: Promise<any>): { outcome: Outcome } {
  const box: { outcome: Outcome } = { outcome: { status: 'pending' } };
  p.then(
    (value) => {
      box.outcome = { status: 'resolved', value };
    },
    (error) => {
      box.outcome = { status: 'rejected', error };
    },
  );
  return box;
}

function summarize(o: Outcome) {
  if (o.status === 'rejected') {
    return {
      status: 'rejected',
      code: o.error?.code,
      message: o.error?.message,
      httpStatus: o.error?.response?.status,
    };
  }
  return { status: o.status };
}

const TIMEOUT_SUMMARY = {
  status: 'rejected',
  code: 'TIMEOUT',
  message: 'identify_timeout',
  httpStatus: 503,
};

async function settle(p: Promise<any>): Promise<{ value: any; error: any }> {
  try {
    return { value: await p, error: undefined };
  } catch (error) {
    return { value: undefined, error };
  }
}

/** Every string reachable from `v` through own property names (enumerable or not), cycle-safe. */
function deepText(v: any, seen: Set<any> = new Set()): string[] {
  if (v === null || v === undefined) return [];
  if (typeof v === 'string') return [v];
  if (typeof v !== 'object' && typeof v !== 'function') return [String(v)];
  if (seen.has(v)) return [];
  seen.add(v);
  const out: string[] = [];
  for (const key of Object.getOwnPropertyNames(v)) {
    out.push(key);
    let child: any;
    try {
      child = v[key];
    } catch {
      continue;
    }
    out.push(...deepText(child, seen));
  }
  return out;
}

function safeJson(v: any): string {
  try {
    return JSON.stringify(v) ?? '';
  } catch {
    return '';
  }
}

describe('S71 U13c -- camera /image/identify 401: one single-flight refresh, one retry', () => {
  let api: typeof import('../src/services/api');
  let sessionEvents: typeof import('../src/services/sessionEvents');
  let fetchMock: jest.Mock;
  let originalFetch: any;
  let emits: number;
  let IDENTIFY_URL: string;

  /** Queue fresh single-read responses, in order; any further fetch is a test-visible error. */
  function queue(...responses: [number, string][]) {
    for (const [status, body] of responses) {
      fetchMock.mockImplementationOnce(() => Promise.resolve(mkResponse(status, body)));
    }
    fetchMock.mockImplementation(() =>
      Promise.reject(new Error('U13C-TEST unexpected extra fetch call')),
    );
  }

  beforeEach(() => {
    jest.resetModules();
    mockRefreshSession.mockReset();
    mockGetToken.mockReset();
    mockClearSession.mockReset();
    mockClearSession.mockResolvedValue(undefined);
    mockManipulateAsync.mockReset();
    mockManipulateAsync.mockResolvedValue({ uri: 'file:///manipulated.jpg' });
    for (const fn of [...Object.values(mockSentryService), ...Object.values(mockSentryRN)]) {
      fn.mockClear();
    }
    // performRefresh reads the token AFTER refreshSession, so it sees NEW.
    mockGetToken.mockResolvedValueOnce('OLD-TOKEN').mockResolvedValue('NEW-TOKEN');
    originalFetch = (global as any).fetch;
    fetchMock = jest.fn();
    (global as any).fetch = fetchMock;
    // A fresh module registry per test: a fresh refresh singleton and listener set.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    api = require('../src/services/api');
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    sessionEvents = require('../src/services/sessionEvents');
    sessionEvents.__resetSessionListeners();
    emits = 0;
    sessionEvents.onSessionInvalid(() => {
      emits += 1;
    });
    api.__resetRefreshMutex();
    IDENTIFY_URL = `${api.API_BASE_URL}/api/v1/image/identify?region=bahrain`;
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    jest.useRealTimers();
  });

  // ---------------------------------------------------------------- RED --

  it('T1 401 then 200: one refresh, one retry with the new bearer, resolves the 200 data', async () => {
    mockRefreshSession.mockResolvedValue({ success: true });
    queue([401, AUTH_BODY], [200, OK_BODY]);

    await expect(api.identifyFromImages(URIS, 'bahrain')).resolves.toEqual(OK_DATA);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    const [first, second] = fetchMock.mock.calls;
    expect(first[1].headers.Authorization).toBe('Bearer OLD-TOKEN');
    expect(second[1].headers).toEqual({ Authorization: 'Bearer NEW-TOKEN' });
    expect(first[0]).toBe(IDENTIFY_URL);
    expect(second[0]).toBe(first[0]);
    expect(second[1].method).toBe('POST');
    // The SAME FormData instance and the SAME deadline signal.
    expect(second[1].body).toBe(first[1].body);
    expect(second[1].signal).toBe(first[1].signal);
    // Not rebuilt, not re-appended: 2 URIs -> 2 transcodes, 2 parts at the retry.
    expect(mockManipulateAsync).toHaveBeenCalledTimes(2);
    expect(second[1].body.getAll('images')).toHaveLength(2);
    expect(mockClearSession).not.toHaveBeenCalled();
    expect(emits).toBe(0);
  });

  it('T2 401 twice: exactly one refresh, no third request, rejects the auth error', async () => {
    mockRefreshSession.mockResolvedValue({ success: true });
    queue([401, AUTH_BODY], [401, AUTH_BODY_2]);

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(error?.message).toBe('Server error 401');
    expect(error.response.status).toBe(401);
    expect(error.response.data.code).toBe('AUTH_REQUIRED');
    // The retry's own body (R3: the existing handling of the retry response).
    expect(error.response.data).toEqual(AUTH_ENVELOPE_2);
    expect(classifyLoadFailure(error)).toBe('auth');
    expect(isCameraEngineOutage(error)).toBe(false);
    expect(mockClearSession).not.toHaveBeenCalled();
    expect(emits).toBe(0);
  });

  it('T3 dead session (refresh sessionInvalid): no retry, cleared and announced exactly once by performRefresh', async () => {
    mockRefreshSession.mockResolvedValue({
      success: false,
      error: 'No refresh token found',
      sessionInvalid: true,
    });
    queue([401, AUTH_BODY]);

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(mockClearSession).toHaveBeenCalledTimes(1);
    expect(emits).toBe(1);
    // The FIRST 401's axios-shaped error, its body read once (single-read fake).
    expect(error?.message).toBe('Server error 401');
    expect(error.response.status).toBe(401);
    expect(error.response.data).toEqual(AUTH_ENVELOPE);
    expect(classifyLoadFailure(error)).toBe('auth');
  });

  it('T4 transient refresh failure: no retry, nothing cleared, nothing announced', async () => {
    mockRefreshSession.mockResolvedValue({ success: false, error: 'Network Error' });
    queue([401, AUTH_BODY]);

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(mockClearSession).not.toHaveBeenCalled();
    expect(emits).toBe(0);
    expect(error?.message).toBe('Server error 401');
    expect(error.response.status).toBe(401);
    expect(error.response.data).toEqual(AUTH_ENVELOPE);
    expect(classifyLoadFailure(error)).toBe('auth');
  });

  it('T5 a rejecting refresh is swallowed into the 401 auth error, never the refresh error', async () => {
    mockRefreshSession.mockRejectedValue(
      Object.assign(new Error('boom'), { response: { status: 500 } }),
    );
    queue([401, AUTH_BODY]);

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(error?.message).toBe('Server error 401');
    expect(error.response.status).toBe(401);
    expect(error.response.status).not.toBe(500);
    expect(error.response.data.code).toBe('AUTH_REQUIRED');
    // A refresh 500 must never read as a camera engine outage.
    expect(isCameraEngineOutage(error)).toBe(false);
    expect(classifyLoadFailure(error)).toBe('auth');
    // performRefresh cleared and announced once; the camera added nothing.
    expect(mockClearSession).toHaveBeenCalledTimes(1);
    expect(emits).toBe(1);
  });

  it('T6 401 then 429 USAGE_LIMIT: the retry goes through the H3 tag', async () => {
    mockRefreshSession.mockResolvedValue({ success: true });
    queue([401, AUTH_BODY], [429, USAGE_BODY]);

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(error?.message).toBe('Usage limit reached');
    expect(error).toMatchObject({ code: 'USAGE_LIMIT', detail: { code: 'USAGE_LIMIT' } });
    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("T7 401 then 500 INTERNAL_ERROR: the retry's error is the existing engine-outage shape", async () => {
    mockRefreshSession.mockResolvedValue({ success: true });
    queue([401, AUTH_BODY], [500, INTERNAL_BODY]);

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(error?.message).toBe('Server error 500');
    expect(error.response.status).toBe(500);
    expect(error.response.data).toMatchObject({ code: 'INTERNAL_ERROR' });
    expect(isCameraEngineOutage(error)).toBe(true);
    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('T8 401 then 200 comparison_failed: the envelope is returned untouched', async () => {
    mockRefreshSession.mockResolvedValue({ success: true });
    queue([401, AUTH_BODY], [200, JSON.stringify(COMPARISON_FAILED)]);

    await expect(api.identifyFromImages(URIS, 'bahrain')).resolves.toEqual(COMPARISON_FAILED);

    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('T9 single flight: a refresh already in flight is joined, never a second refresh', async () => {
    // Every refreshSession() call gets its own deferred; all are settled below,
    // so a second (non-joined) refresh fails the count, never hangs the test.
    const pendingRefreshes: ((v: any) => void)[] = [];
    mockRefreshSession.mockImplementation(
      () =>
        new Promise((resolve) => {
          pendingRefreshes.push(resolve);
        }),
    );
    queue([401, AUTH_BODY], [200, OK_BODY]);

    // Another caller (the boot refresh / an axios 401) is already refreshing.
    const inFlight = api.__testRefreshDedup();
    const box = track(api.identifyFromImages(URIS, 'bahrain'));
    await flushReal();
    const refreshCallsWhilePending = mockRefreshSession.mock.calls.length;

    for (const resolve of pendingRefreshes) resolve({ success: true });
    await expect(inFlight).resolves.toEqual({ success: true, token: 'NEW-TOKEN' });
    await flushReal();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(refreshCallsWhilePending).toBe(1);
    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[1][1].headers).toEqual({ Authorization: 'Bearer NEW-TOKEN' });
    expect(box.outcome).toEqual({ status: 'resolved', value: OK_DATA });
  });

  it('T10 deadline during the refresh wait: TIMEOUT at the deadline, nothing sent, the late refresh (resolve or reject) is harmless', async () => {
    jest.useFakeTimers();
    const deadline = api.IDENTIFY_TIMEOUT_MS;

    for (const lateRefresh of ['resolves', 'rejects'] as const) {
      fetchMock.mockReset();
      mockRefreshSession.mockReset();
      mockGetToken.mockReset();
      mockGetToken.mockResolvedValueOnce('OLD-TOKEN').mockResolvedValue('NEW-TOKEN');
      api.__resetRefreshMutex();
      let settleRefresh: { resolve: (v: any) => void; reject: (e: any) => void } | undefined;
      mockRefreshSession.mockImplementation(
        () =>
          new Promise((resolve, reject) => {
            settleRefresh = { resolve, reject };
          }),
      );
      fetchMock.mockImplementationOnce(() => Promise.resolve(mkResponse(401, AUTH_BODY)));
      // Mirrors whatwg-fetch fetch.umd.js:536: an already-aborted signal rejects before any send.
      fetchMock.mockImplementation((_url: string, opts: any) =>
        opts.signal.aborted
          ? Promise.reject(abortError())
          : Promise.resolve(mkResponse(200, OK_BODY)),
      );

      const box = track(api.identifyFromImages(URIS, 'bahrain'));
      await flushReal();
      await jest.advanceTimersByTimeAsync(deadline + 1);
      await flushReal();

      // The refresh is still pending, yet the call has ALREADY ended as TIMEOUT.
      expect({ pass: lateRefresh, outcome: summarize(box.outcome) }).toEqual({
        pass: lateRefresh,
        outcome: TIMEOUT_SUMMARY,
      });
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(mockRefreshSession).toHaveBeenCalledTimes(1);

      // The refresh runs to completion on its own (P-A3) and changes nothing here.
      // A rejection left unhandled surfaces during these real yields and jest
      // fails this test with it (measured; see the U13c RED notes).
      if (lateRefresh === 'resolves') {
        settleRefresh?.resolve({ success: true });
      } else {
        settleRefresh?.reject(
          Object.assign(new Error('late refresh failure'), { response: { status: 500 } }),
        );
      }
      await flushReal();
      await jest.advanceTimersByTimeAsync(0);
      await flushReal();

      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(summarize(box.outcome)).toEqual(TIMEOUT_SUMMARY);
    }
  });

  it('T11 one shared deadline: a hung retry times out at IDENTIFY_TIMEOUT_MS from the start', async () => {
    jest.useFakeTimers();
    const deadline = api.IDENTIFY_TIMEOUT_MS;
    const firstAnswerAt = 60000;
    mockRefreshSession.mockResolvedValue({ success: true });
    fetchMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          setTimeout(() => resolve(mkResponse(401, AUTH_BODY)), firstAnswerAt);
        }),
    );
    fetchMock.mockImplementation((_url: string, opts: any) => hangUntilAbort(opts.signal));

    const box = track(api.identifyFromImages(URIS, 'bahrain'));
    await flushReal();
    await jest.advanceTimersByTimeAsync(firstAnswerAt);
    await flushReal();
    await jest.advanceTimersByTimeAsync(deadline + 1 - firstAnswerAt);
    await flushReal();

    expect(summarize(box.outcome)).toEqual(TIMEOUT_SUMMARY);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][1].signal.aborted).toBe(true);
    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    // A per-attempt timer re-armed at the 401 would still be pending here.
    expect(jest.getTimerCount()).toBe(0);
  });

  it('T17b a 401 with no stored token still refreshes and retries with the new bearer', async () => {
    mockGetToken.mockReset();
    mockGetToken.mockResolvedValueOnce(null).mockResolvedValue('NEW-TOKEN');
    mockRefreshSession.mockResolvedValue({ success: true });
    queue([401, AUTH_BODY], [200, OK_BODY]);

    const { value, error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(fetchMock.mock.calls[0][1].headers).toEqual({});
    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][1].headers).toEqual({ Authorization: 'Bearer NEW-TOKEN' });
    expect(error).toBeUndefined();
    expect(value).toEqual(OK_DATA);
  });

  it('T19 a 401 without the AUTH_REQUIRED envelope still refreshes and retries', async () => {
    mockRefreshSession.mockResolvedValue({ success: true });
    queue([401, 'Unauthorized'], [200, OK_BODY]);

    const { value, error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][1].headers).toEqual({ Authorization: 'Bearer NEW-TOKEN' });
    expect(error).toBeUndefined();
    expect(value).toEqual(OK_DATA);
  });

  // ---------------------------------------------------------------- PIN --

  it('T12 200 first: no refresh', async () => {
    queue([200, OK_BODY]);

    await expect(api.identifyFromImages(URIS, 'bahrain')).resolves.toEqual(OK_DATA);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it('T13 500 first: existing axios-shaped error, no refresh', async () => {
    queue([500, INTERNAL_BODY]);

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(error?.message).toBe('Server error 500');
    expect(error.response).toEqual({ status: 500, data: INTERNAL_ENVELOPE });
    expect(mockRefreshSession).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('T14 offline TypeError: passes through, no refresh', async () => {
    const offline = new TypeError('Network request failed');
    fetchMock.mockImplementationOnce(() => Promise.reject(offline));
    fetchMock.mockImplementation(() =>
      Promise.reject(new Error('U13C-TEST unexpected extra fetch call')),
    );

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(error).toBe(offline);
    expect(error.response).toBeUndefined();
    expect(classifyLoadFailure(error)).toBe('timeout');
    expect(mockRefreshSession).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('T15 429 USAGE_LIMIT first: H3 tag, no refresh', async () => {
    queue([429, USAGE_BODY]);

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(error?.message).toBe('Usage limit reached');
    expect(error).toMatchObject({ code: 'USAGE_LIMIT', detail: { code: 'USAGE_LIMIT' } });
    expect(mockRefreshSession).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('T16 no access token is ever logged or thrown', async () => {
    const previousDev = (globalThis as any).__DEV__;
    (globalThis as any).__DEV__ = true;
    const consoleMethods = ['log', 'info', 'warn', 'error', 'debug'] as const;
    const spies = consoleMethods.map((m) =>
      jest.spyOn(console, m).mockImplementation(() => undefined),
    );
    const thrown: any[] = [];
    try {
      mockRefreshSession.mockResolvedValue({ success: true });

      // Run 1: 401 -> refresh -> 200.
      queue([401, AUTH_BODY], [200, OK_BODY]);
      await api.identifyFromImages(URIS, 'bahrain').catch((e: any) => {
        thrown.push(e);
      });
      const firstRequestAuth = fetchMock.mock.calls[0][1].headers.Authorization;

      // Run 2: 401 -> refresh -> 401.
      fetchMock.mockReset();
      mockGetToken.mockResolvedValueOnce('OLD-TOKEN');
      queue([401, AUTH_BODY], [401, AUTH_BODY_2]);
      await api.identifyFromImages(URIS, 'bahrain').catch((e: any) => {
        thrown.push(e);
      });

      const recordedArgs: any[] = [];
      for (const spy of spies) recordedArgs.push(...spy.mock.calls);
      for (const fn of [...Object.values(mockSentryService), ...Object.values(mockSentryRN)]) {
        recordedArgs.push(...fn.mock.calls);
      }
      const haystack = [
        ...recordedArgs.map((args) => deepText(args).join('\n') + safeJson(args)),
        ...thrown.map(
          (e) =>
            deepText(e).join('\n') +
            safeJson(e) +
            String(e) +
            String(e?.message) +
            safeJson(e?.response),
        ),
      ].join('\n');

      // Positive controls: the __DEV__ toggle took effect, and a token existed to leak.
      expect(spies[0].mock.calls.some((c) => c[0] === '=== IDENTIFY FROM IMAGES ===')).toBe(true);
      expect(firstRequestAuth).toBe('Bearer OLD-TOKEN');

      expect(haystack).not.toContain('OLD-TOKEN');
      expect(haystack).not.toContain('NEW-TOKEN');
    } finally {
      (globalThis as any).__DEV__ = previousDev;
      for (const spy of spies) spy.mockRestore();
    }
  });

  it("T17a first request shape is today's", async () => {
    mockGetToken.mockReset();
    mockGetToken.mockResolvedValueOnce(null).mockResolvedValueOnce('OLD-TOKEN');
    queue([200, OK_BODY], [200, OK_BODY]);

    await api.identifyFromImages(URIS, 'bahrain');
    await api.identifyFromImages(URIS, 'bahrain');

    const [noToken, withToken] = fetchMock.mock.calls;
    for (const [url, opts] of [noToken, withToken]) {
      expect(url).toBe(IDENTIFY_URL);
      expect(Object.keys(opts)).toEqual(['method', 'body', 'headers', 'signal']);
      expect(opts.method).toBe('POST');
      expect(opts.body).toBeInstanceOf(FormData);
      expect(opts.body.getAll('images')).toHaveLength(2);
      expect(opts.signal).toBeInstanceOf(AbortSignal);
    }
    expect(noToken[1].headers).toEqual({});
    expect(withToken[1].headers).toEqual({ Authorization: 'Bearer OLD-TOKEN' });
    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it('T18 403 first: existing axios-shaped error, no refresh', async () => {
    queue([403, JSON.stringify(FORBIDDEN_ENVELOPE)]);

    const { error } = await settle(api.identifyFromImages(URIS, 'bahrain'));

    expect(error?.message).toBe('Server error 403');
    expect(error.response.status).toBe(403);
    expect(error.response.data).toEqual(FORBIDDEN_ENVELOPE);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(mockRefreshSession).not.toHaveBeenCalled();
  });
});
