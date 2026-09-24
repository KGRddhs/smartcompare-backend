/**
 * W3-11bcd — RTL-05 test 1(e), REACHABILITY PIN (spec FABLE ruling R2(c)).
 *
 * The invariant that makes HomeScreen's SSE `onComplete` success:false arm
 * (HomeScreen.tsx:418-434) unreachable: `streamComparison` routes a terminal
 * payload carrying `success:false` to `onError`, NEVER to `onComplete` —
 *   - SSE reader, `complete` / `settle_complete` frames → `dispatchTerminal`
 *     (api.ts:688-700);
 *   - REST compare (the shipped default, ENABLE_EXPO_FETCH_SSE=false)
 *     (api.ts:603-618).
 * The backend's streaming path emits its English prose ("We don't compare
 * this category", "Could not identify two products…") as `error` events, but
 * if a `success:false` payload ever arrives on a terminal frame it must still
 * land on HomeScreen's code-keyed onError path.
 *
 * GREEN AT BASE BY DESIGN: this is the named forward guard exempted by R8(c).
 * Mutation that reddens it: make `dispatchTerminal` call `onComplete`
 * unconditionally.
 *
 * Harness = __tests__/api.settleTerminalLatch.a7.test.ts.
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
  manipulateAsync: jest.fn(),
  SaveFormat: { JPEG: 'jpeg' },
}));

jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));

jest.mock('../src/services/sentry', () => ({
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: (s: string) => s,
  scrubBeforeSend: (e: any) => e,
}));

if (typeof (global as any).TextDecoder === 'undefined') {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  (global as any).TextDecoder = require('util').TextDecoder;
}

const axiosInstance = (require('axios') as any).__instance;
const expoFetchMock = (require('expo/fetch') as any).fetch as jest.Mock;

// Explicit budget for the api.ts require (beforeAll) and each case.
const API_REQUIRE_TIMEOUT_MS = 60_000;

const CATEGORY_BLOCK = {
  success: false,
  code: 'CONTENT_UNAVAILABLE',
  error: "We don't compare this category",
  layer: 'query_prefilter',
};

function sseFrame(event: string, data: any): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function makeFetchStream(frames: string[]) {
  const encoder = new TextEncoder();
  const chunks = frames.map((f) => encoder.encode(f));
  let i = 0;
  const reader = {
    read: jest.fn().mockImplementation(() => {
      if (i < chunks.length) {
        return Promise.resolve({ done: false, value: chunks[i++] });
      }
      return Promise.resolve({ done: true, value: undefined });
    }),
  };
  return { ok: true, body: { getReader: () => reader } };
}

async function flush(times = 30): Promise<void> {
  for (let i = 0; i < times; i++) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setImmediate(r));
  }
}

describe('W3-11 RTL-05 (e) — a success:false terminal payload never reaches onComplete', () => {
  let originalFetch: any;
  let streamComparison: (req: any) => { subscribe: (h: any) => void };

  // api.ts is required ONCE here, not inside a test body: ts-jest transforms
  // it on first require, which on a loaded box outran jest's default 5 s
  // per-test timeout (measured: the first it.each case timed out in a 12-file
  // run and passed alone in 54 s). The feature flag is read per call, so
  // setting it inside each test after this require is unchanged behaviour.
  beforeAll(() => {
    ({ streamComparison } = require('../src/services/api'));
  }, API_REQUIRE_TIMEOUT_MS);

  beforeEach(() => {
    originalFetch = (global as any).fetch;
    (global as any).fetch = jest.fn();
    axiosInstance.get.mockReset();
    expoFetchMock.mockReset();
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(null);
  });

  it.each(['complete', 'settle_complete'])(
    'SSE reader: a `%s` frame carrying success:false CONTENT_UNAVAILABLE fires onError, not onComplete',
    async (eventName) => {
      const features = require('../src/config/features');
      features._setExpoFetchSseForTests(true);
      expoFetchMock.mockResolvedValue(makeFetchStream([sseFrame(eventName, CATEGORY_BLOCK)]));
      axiosInstance.get.mockResolvedValue({ data: { success: true, comparison: 'REST' } });

      const onComplete = jest.fn();
      const onError = jest.fn();
      streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onComplete, onError });
      await flush();

      expect(onComplete).not.toHaveBeenCalled();
      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError.mock.calls[0][0]?.response?.data?.code).toBe('CONTENT_UNAVAILABLE');
    },
    API_REQUIRE_TIMEOUT_MS,
  );

  it('REST compare (shipped default, flag OFF): success:false fires onError, not onComplete', async () => {
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests(false);
    axiosInstance.get.mockResolvedValue({ data: CATEGORY_BLOCK });

    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onComplete, onError });
    await flush();

    expect(onComplete).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]?.response?.data?.code).toBe('CONTENT_UNAVAILABLE');
  }, API_REQUIRE_TIMEOUT_MS);
});
