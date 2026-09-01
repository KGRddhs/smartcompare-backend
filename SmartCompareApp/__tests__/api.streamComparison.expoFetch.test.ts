/**
 * #118 — streamComparison flag-ON transport contract.
 *
 * With ENABLE_EXPO_FETCH_SSE=true the SSE stream must ride `expo/fetch`
 * (Expo's winter-runtime fetch with a REAL ReadableStream body), never the
 * global whatwg-fetch polyfill — this pins that the streaming path is still
 * used where `response.body` DOES exist, so #118 is not a blanket
 * downgrade. A failing expo/fetch degrades to exactly ONE REST compare and
 * leaves a Sentry breadcrumb (production-visible; the old path only had a
 * __DEV__ console.log).
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
  const reader = {
    read: jest.fn().mockImplementation(() => {
      if (i < chunks.length) {
        const value = chunks[i++];
        return Promise.resolve({ done: false, value });
      }
      return Promise.resolve({ done: true, value: undefined });
    }),
  };
  return {
    ok: true,
    body: {
      getReader: () => reader,
    },
  };
}

async function flush(times = 25): Promise<void> {
  for (let i = 0; i < times; i++) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setImmediate(r));
  }
}

describe('streamComparison — #118 flag ON (expo/fetch SSE transport)', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = (global as any).fetch;
    (global as any).fetch = jest.fn();
    axiosInstance.get.mockReset();
    expoFetchMock.mockReset();
    const sentry = require('../src/services/sentry');
    (sentry.addSseFallbackBreadcrumb as jest.Mock).mockReset();
    // Optional-call so this file is meaningfully RED (not import-broken)
    // at the pre-#118 base where the flag does not exist yet.
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(true);
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(null);
  });

  it('flag ON: dispatches SSE frames through expo/fetch, not global fetch', async () => {
    expoFetchMock.mockResolvedValue(
      makeFetchStream([
        sseFrame('status', { message: 'x' }),
        sseFrame('specs', { specs: { a: 1 } }),
        sseFrame('prices', { prices: { a: 2 } }),
        sseFrame('complete', { success: true, comparison: 'ok' }),
      ]),
    );
    const { streamComparison } = require('../src/services/api');

    const onStatus = jest.fn();
    const onSpecs = jest.fn();
    const onPrices = jest.fn();
    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({
      onStatus,
      onSpecs,
      onPrices,
      onComplete,
      onError,
    });
    await flush();

    expect(expoFetchMock).toHaveBeenCalledTimes(1);
    expect((global as any).fetch).not.toHaveBeenCalled();
    expect(onStatus).toHaveBeenCalledTimes(1);
    expect(onSpecs).toHaveBeenCalledTimes(1);
    expect(onPrices).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledWith({ success: true, comparison: 'ok' });
    expect(onError).not.toHaveBeenCalled();
    // The streaming transport carried the whole compare — no REST re-run.
    expect(axiosInstance.get).not.toHaveBeenCalled();
  });

  it('flag ON: a rejecting expo fetch falls back to exactly one REST compare and breadcrumbs', async () => {
    expoFetchMock.mockRejectedValue(new Error('boom'));
    axiosInstance.get.mockResolvedValue({
      data: { success: true, comparison: 'ok' },
    });
    const { streamComparison } = require('../src/services/api');
    const { addSseFallbackBreadcrumb } = require('../src/services/sentry');

    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({
      onComplete,
      onError,
    });
    await flush();

    expect(axiosInstance.get).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
    expect(addSseFallbackBreadcrumb).toHaveBeenCalledTimes(1);
    expect((addSseFallbackBreadcrumb as jest.Mock).mock.calls[0][0].message).toBe('boom');
    expect((global as any).fetch).not.toHaveBeenCalled();
  });

  it('flag ON: a transport error AFTER `complete` does NOT buy a second compare', async () => {
    // Reviewer probe (#118): the read loop's outer catch could not tell "failed
    // before any result" from "failed AFTER the result was delivered", so a
    // transport error between the last frame and a clean close re-entered the
    // REST fallback — a SECOND full backend comparison (double OpenAI + double
    // Serper) for a result the user already had. The terminal latch closes it.
    const encoder = new TextEncoder();
    const frames = [sseFrame('complete', { success: true, comparison: 'ok' })];
    let i = 0;
    expoFetchMock.mockResolvedValue({
      ok: true,
      body: {
        getReader: () => ({
          read: jest.fn().mockImplementation(() => {
            if (i < frames.length) {
              return Promise.resolve({ done: false, value: encoder.encode(frames[i++]) });
            }
            return Promise.reject(new Error('transport died after complete'));
          }),
        }),
      },
    });
    axiosInstance.get.mockResolvedValue({ data: { success: true, comparison: 'REST' } });
    const { streamComparison } = require('../src/services/api');

    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onComplete, onError });
    await flush();

    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledWith({ success: true, comparison: 'ok' });
    // THE INVARIANT: no REST re-run after a delivered result.
    expect(axiosInstance.get).not.toHaveBeenCalled();
  });
});
