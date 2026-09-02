/**
 * M18 mobile-network unit — the failure CLASSIFICATION matrix + client deadlines.
 *
 * Findings covered (docs/investigations/2026-09-01-m18-verified.json):
 *  - MB-perf-03 / MB-contract-06: `identifyFromImages` was a raw fetch with NO
 *    timeout and no AbortController (indefinite spinner on a stalled multipart
 *    upload), and the SSE stream had no client-side deadline (the backend's
 *    flag-OFF unbounded verdict tail could pin the loader with no escape).
 *  - MB-flows-05: an offline device or a bare `Error('Server error N')` (no
 *    `.response`) fell through to `vision_failed` — the user was told their
 *    PHOTOS were bad while the backend was down. `classifyLoadFailure` is the
 *    explicit matrix; every branch is pinned here.
 *  - MB-contract-09: `parseApiError` blanketed every 503 to TIMEOUT, overriding
 *    explicit non-timeout codes like FEATURE_DISABLED.
 *  - MB-contract-02: the SSE 'error' event handler dropped `code`/`layer`, so
 *    CONTENT_UNAVAILABLE never fired on the streaming path and raw backend
 *    exception text leaked to the user. (Dormant today — the streaming path is
 *    behind ENABLE_EXPO_FETCH_SSE default false — but it is a precondition for
 *    ever flipping that flag.)
 *
 * Harness mirrors api.streamComparison.expoFetch.test.ts (the precedent for
 * exercising src/services/api.ts without the network surface).
 */

import { TextEncoder } from 'util';

jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
}));

jest.mock('axios', () => {
  const instance = {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return { create: jest.fn(() => instance), __instance: instance };
});

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn().mockResolvedValue({ uri: 'file:///manipulated.jpg' }),
  SaveFormat: { JPEG: 'jpeg' },
}));

jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));

jest.mock('../src/services/sentry', () => ({
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: (s: string) => s,
  scrubBeforeSend: (e: any) => e,
}));

// Polyfill TextDecoder in jest's node env — RN ships it on device.
if (typeof (global as any).TextDecoder === 'undefined') {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  (global as any).TextDecoder = require('util').TextDecoder;
}

const axiosInstance = (require('axios') as any).__instance;
const expoFetchMock = (require('expo/fetch') as any).fetch as jest.Mock;

function sseFrame(event: string, data: any): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function makeFetchStream(frames: string[]) {
  const encoder = new TextEncoder();
  const chunks = frames.map((f) => encoder.encode(f));
  let i = 0;
  return {
    ok: true,
    body: {
      getReader: () => ({
        read: jest.fn().mockImplementation(() => {
          if (i < chunks.length) {
            const value = chunks[i++];
            return Promise.resolve({ done: false, value });
          }
          return Promise.resolve({ done: true, value: undefined });
        }),
      }),
    },
  };
}

async function flush(times = 25): Promise<void> {
  for (let i = 0; i < times; i++) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setImmediate(r));
  }
}

// ---------------------------------------------------------------------------
// 1. parseApiError — MB-contract-09: a coded 503 keeps its code
// ---------------------------------------------------------------------------

describe('parseApiError — MB-contract-09 503 no longer blankets explicit codes', () => {
  const { parseApiError } = require('../src/services/api');

  it('a 503 with an explicit NON-timeout code returns that code, not TIMEOUT', () => {
    const err = {
      response: {
        status: 503,
        data: { error: 'Referrals are not available right now', code: 'FEATURE_DISABLED' },
      },
    };
    const out = parseApiError(err);
    expect(out.code).toBe('FEATURE_DISABLED');
    expect(out.message).toBe('Referrals are not available right now');
  });

  it('a 503 with a nested detail.code non-timeout code returns that code', () => {
    const err = {
      response: { status: 503, data: { detail: { code: 'FEATURE_DISABLED' } } },
    };
    expect(parseApiError(err).code).toBe('FEATURE_DISABLED');
  });

  it('a bare 503 (no code) still normalizes to TIMEOUT with empty message', () => {
    const err = { response: { status: 503, data: { error: 'Service unavailable' } } };
    const out = parseApiError(err);
    expect(out.code).toBe('TIMEOUT');
    expect(out.message).toBe('');
  });

  it('a 503 with an explicit TIMEOUT code still normalizes to TIMEOUT', () => {
    const err = { response: { status: 503, data: { code: 'TIMEOUT', error: 'x' } } };
    expect(parseApiError(err).code).toBe('TIMEOUT');
  });
});

describe('parseApiError — MB-perf-03/MB-flows-05 transport-level failures map to TIMEOUT', () => {
  const { parseApiError } = require('../src/services/api');

  it('axios deadline (ECONNABORTED, no response) maps to TIMEOUT, message empty', () => {
    const err = Object.assign(new Error('timeout of 35000ms exceeded'), {
      code: 'ECONNABORTED',
    });
    const out = parseApiError(err);
    expect(out.code).toBe('TIMEOUT');
    // The raw axios string ("timeout of Nms exceeded") must never render.
    expect(out.message).toBe('');
  });

  it('offline (ERR_NETWORK, no response) maps to TIMEOUT', () => {
    const err = Object.assign(new Error('Network Error'), { code: 'ERR_NETWORK' });
    expect(parseApiError(err).code).toBe('TIMEOUT');
  });

  it('ETIMEDOUT (no response) maps to TIMEOUT', () => {
    const err = Object.assign(new Error('etimedout'), { code: 'ETIMEDOUT' });
    expect(parseApiError(err).code).toBe('TIMEOUT');
  });

  it('a deliberate cancel (ERR_CANCELED) is NOT relabelled TIMEOUT', () => {
    const err = Object.assign(new Error('canceled'), { code: 'ERR_CANCELED' });
    expect(parseApiError(err).code).not.toBe('TIMEOUT');
  });

  it('a transport code WITH a response defers to the response classification', () => {
    // The transport branch only fires when there is no response at all.
    const err = Object.assign(new Error('x'), {
      code: 'ECONNABORTED',
      response: { status: 422, data: { error: 'Not a product', code: 'CONTENT_UNAVAILABLE' } },
    });
    expect(parseApiError(err).code).toBe('CONTENT_UNAVAILABLE');
  });

  it('a bare error with no response and no code keeps the message fallback', () => {
    const out = parseApiError(new Error('some programming error'));
    expect(out.code).toBeNull();
    expect(out.message).toBe('some programming error');
  });
});

// ---------------------------------------------------------------------------
// 2. classifyLoadFailure — MB-flows-05: the explicit matrix, every branch
// ---------------------------------------------------------------------------

describe('classifyLoadFailure — MB-flows-05 explicit failure matrix', () => {
  const { classifyLoadFailure } = require('../src/services/failureClassification');

  it('USAGE_LIMIT (top-level err.code, camera raw-fetch shape) -> usage_limit', () => {
    const err = Object.assign(new Error('Usage limit reached'), {
      code: 'USAGE_LIMIT',
      detail: { code: 'USAGE_LIMIT' },
    });
    expect(classifyLoadFailure(err)).toBe('usage_limit');
  });

  it('USAGE_LIMIT (axios response.data.code shape) -> usage_limit', () => {
    const err = { response: { status: 429, data: { code: 'USAGE_LIMIT' } } };
    expect(classifyLoadFailure(err)).toBe('usage_limit');
  });

  it('404 -> not_found', () => {
    expect(classifyLoadFailure({ response: { status: 404, data: {} } })).toBe('not_found');
  });

  it('401 -> auth (interceptor territory, caller no-ops)', () => {
    expect(classifyLoadFailure({ response: { status: 401, data: {} } })).toBe('auth');
  });

  it('503 -> timeout (retryable)', () => {
    expect(classifyLoadFailure({ response: { status: 503, data: {} } })).toBe('timeout');
  });

  it('code TIMEOUT / STREAM_TIMEOUT -> timeout regardless of status', () => {
    expect(
      classifyLoadFailure({ response: { status: 200, data: { code: 'STREAM_TIMEOUT' } } })
    ).toBe('timeout');
    expect(
      classifyLoadFailure(Object.assign(new Error('identify_timeout'), { code: 'TIMEOUT' }))
    ).toBe('timeout');
  });

  it('any 5xx (500/502/504) -> timeout: the backend is down, NOT the user\'s photos', () => {
    for (const status of [500, 502, 504]) {
      expect(classifyLoadFailure({ response: { status, data: {} } })).toBe('timeout');
    }
  });

  it('offline / transport drop (no .response at all) -> timeout', () => {
    expect(classifyLoadFailure(new TypeError('Network request failed'))).toBe('timeout');
    expect(classifyLoadFailure(new Error('Server error 500: boom'))).toBe('timeout');
  });

  it('a plain 4xx with a response -> generic (never photo-blame, never retry-copy)', () => {
    expect(classifyLoadFailure({ response: { status: 400, data: { error: 'bad' } } })).toBe(
      'generic'
    );
    expect(classifyLoadFailure({ response: { status: 422, data: {} } })).toBe('generic');
  });
});

// ---------------------------------------------------------------------------
// 3. identifyFromImages — MB-perf-03: deadline + axios-shaped server errors
// ---------------------------------------------------------------------------

describe('identifyFromImages — MB-perf-03 camera path can always fail', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = (global as any).fetch;
    (global as any).fetch = jest.fn();
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    jest.useRealTimers();
  });

  it('a non-ok server response throws an axios-SHAPED error (response.status + data)', async () => {
    (global as any).fetch.mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => JSON.stringify({ error: 'boom', code: 'INTERNAL_ERROR' }),
    });
    const { identifyFromImages } = require('../src/services/api');

    await expect(identifyFromImages(['file:///a.jpg', 'file:///b.jpg'])).rejects.toMatchObject({
      response: { status: 500, data: { code: 'INTERNAL_ERROR' } },
    });
  });

  it('a non-ok response with a non-JSON body still carries response.status', async () => {
    (global as any).fetch.mockResolvedValue({
      ok: false,
      status: 502,
      text: async () => '<html>Bad Gateway</html>',
    });
    const { identifyFromImages } = require('../src/services/api');

    await expect(identifyFromImages(['file:///a.jpg', 'file:///b.jpg'])).rejects.toMatchObject({
      response: { status: 502 },
    });
  });

  it('the 429 USAGE_LIMIT tagged-error contract is preserved (H3)', async () => {
    (global as any).fetch.mockResolvedValue({
      ok: false,
      status: 429,
      text: async () => JSON.stringify({ code: 'USAGE_LIMIT', used: 3 }),
    });
    const { identifyFromImages } = require('../src/services/api');

    await expect(identifyFromImages(['file:///a.jpg', 'file:///b.jpg'])).rejects.toMatchObject({
      code: 'USAGE_LIMIT',
      detail: { code: 'USAGE_LIMIT' },
    });
  });

  it('a hung upload is aborted at IDENTIFY_TIMEOUT_MS and rejects with code TIMEOUT', async () => {
    jest.useFakeTimers();
    const api = require('../src/services/api');
    expect(typeof api.IDENTIFY_TIMEOUT_MS).toBe('number');

    (global as any).fetch.mockImplementation(
      (_url: string, opts: any) =>
        new Promise((_resolve, reject) => {
          opts.signal.addEventListener('abort', () =>
            reject(Object.assign(new Error('Aborted'), { name: 'AbortError' }))
          );
        })
    );

    const promise = api.identifyFromImages(['file:///a.jpg', 'file:///b.jpg']);
    // Swallow the rejection race before assertions (avoid unhandled warnings).
    promise.catch(() => undefined);
    await jest.advanceTimersByTimeAsync(api.IDENTIFY_TIMEOUT_MS + 1);

    await expect(promise).rejects.toMatchObject({ code: 'TIMEOUT' });
    // classifyLoadFailure must route this to the retryable timeout state.
    const { classifyLoadFailure } = require('../src/services/failureClassification');
    await promise.catch((err: any) => {
      expect(classifyLoadFailure(err)).toBe('timeout');
    });
  });

  it('an offline TypeError passes through with no .response (transport branch input)', async () => {
    (global as any).fetch.mockRejectedValue(new TypeError('Network request failed'));
    const { identifyFromImages } = require('../src/services/api');

    let caught: any = null;
    await identifyFromImages(['file:///a.jpg', 'file:///b.jpg']).catch((e: any) => {
      caught = e;
    });
    expect(caught).toBeTruthy();
    expect(caught.response).toBeUndefined();
    const { classifyLoadFailure } = require('../src/services/failureClassification');
    expect(classifyLoadFailure(caught)).toBe('timeout');
  });
});

// ---------------------------------------------------------------------------
// 4. SSE 'error' event — MB-contract-02: code/layer preserved
// ---------------------------------------------------------------------------

describe('streamComparison SSE error event — MB-contract-02 code/layer contract', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = (global as any).fetch;
    (global as any).fetch = jest.fn();
    axiosInstance.get.mockReset();
    expoFetchMock.mockReset();
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(true);
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(null);
    jest.useRealTimers();
  });

  it('a structured error event surfaces code + layer via the axios-shaped envelope', async () => {
    expoFetchMock.mockResolvedValue(
      makeFetchStream([
        sseFrame('error', {
          success: false,
          error: 'We only compare real products',
          code: 'CONTENT_UNAVAILABLE',
          layer: 'query_prefilter',
        }),
      ])
    );
    const { streamComparison, parseApiError } = require('../src/services/api');

    const onError = jest.fn();
    const onComplete = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onError, onComplete });
    await flush();

    expect(onError).toHaveBeenCalledTimes(1);
    const err = onError.mock.calls[0][0];
    expect(err.response?.data?.code).toBe('CONTENT_UNAVAILABLE');
    expect(err.response?.data?.layer).toBe('query_prefilter');
    // The HomeScreen branch condition — parseApiError must see the code.
    expect(parseApiError(err).code).toBe('CONTENT_UNAVAILABLE');
    // Terminal: no REST re-run after a delivered error.
    expect(axiosInstance.get).not.toHaveBeenCalled();
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('a codeless error event (backend generic catch, error=str(e)) classifies as TIMEOUT — raw text never renders', async () => {
    expoFetchMock.mockResolvedValue(
      makeFetchStream([
        sseFrame('error', { success: false, error: "TypeError: 'NoneType' object" }),
      ])
    );
    const { streamComparison, parseApiError } = require('../src/services/api');

    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onError });
    await flush();

    expect(onError).toHaveBeenCalledTimes(1);
    const parsed = parseApiError(onError.mock.calls[0][0]);
    // 503-no-code normalization: friendly copy path, empty message.
    expect(parsed.code).toBe('TIMEOUT');
    expect(parsed.message).toBe('');
  });
});

// ---------------------------------------------------------------------------
// 5. SSE watchdog — MB-contract-06: client-side deadline on the stream
// ---------------------------------------------------------------------------

describe('streamComparison watchdog — MB-contract-06 client-side stream deadline', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = (global as any).fetch;
    (global as any).fetch = jest.fn();
    axiosInstance.get.mockReset();
    expoFetchMock.mockReset();
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(true);
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(null);
    jest.useRealTimers();
  });

  it('a stream that never yields a terminal event errors out at STREAM_WATCHDOG_MS with STREAM_TIMEOUT', async () => {
    jest.useFakeTimers({ doNotFake: ['setImmediate'] });
    // A transport that accepts the request then hangs forever mid-read —
    // the exact pathology of the backend's unbounded verdict tail.
    expoFetchMock.mockResolvedValue({
      ok: true,
      body: { getReader: () => ({ read: () => new Promise(() => undefined) }) },
    });
    const api = require('../src/services/api');
    expect(typeof api.STREAM_WATCHDOG_MS).toBe('number');

    const onError = jest.fn();
    const onComplete = jest.fn();
    api.streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onError, onComplete });
    await flush();
    expect(onError).not.toHaveBeenCalled();

    await jest.advanceTimersByTimeAsync(api.STREAM_WATCHDOG_MS + 1);
    await flush();

    expect(onError).toHaveBeenCalledTimes(1);
    const parsed = api.parseApiError(onError.mock.calls[0][0]);
    expect(parsed.code).toBe('TIMEOUT');
    expect(onComplete).not.toHaveBeenCalled();
    // The watchdog must NOT buy a second (REST) compare after 60s.
    expect(axiosInstance.get).not.toHaveBeenCalled();
  });

  it('the watchdog is disarmed by a terminal complete — no late spurious error', async () => {
    jest.useFakeTimers({ doNotFake: ['setImmediate'] });
    expoFetchMock.mockResolvedValue(
      makeFetchStream([sseFrame('complete', { success: true, comparison: 'ok' })])
    );
    const api = require('../src/services/api');

    const onError = jest.fn();
    const onComplete = jest.fn();
    api.streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onError, onComplete });
    await flush();
    expect(onComplete).toHaveBeenCalledTimes(1);

    await jest.advanceTimersByTimeAsync(api.STREAM_WATCHDOG_MS + 1);
    await flush();
    expect(onError).not.toHaveBeenCalled();
  });
});
