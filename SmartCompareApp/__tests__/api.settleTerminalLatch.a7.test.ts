/**
 * A7 — `settle_complete` is TERMINAL, and the terminal dispatch is latched.
 *
 * The backend yields `settle_complete` immediately followed by `complete`
 * carrying the SAME payload, and `text_routes.py` documents `complete` as
 * "BACKWARD COMPAT — duplicate of settle_complete for current EAS builds;
 * remove in Bundle F". The client used to treat ONLY `complete` as terminal,
 * so:
 *
 *   1. a transport failure in the gap between the two wire writes left
 *      `sawTerminal` false and fell through to `runRestCompare()` — a SECOND
 *      full backend compare (double OpenAI + double Serper + a second
 *      metering decrement) for a result the server had already produced; and
 *   2. the 60s stream watchdog was never disarmed on the settle frame, so a
 *      settle-only stream grew a spurious STREAM_TIMEOUT over a compare that
 *      actually succeeded, and delivered no result to any screen at all.
 *
 * These pin the fix: both events route through one first-wins terminal
 * dispatch, so the pair delivers exactly ONE result, at the FIRST final
 * payload, with the fallback closed and the watchdog disarmed.
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

/** A reader that emits `frames` then closes cleanly. */
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

/** A reader that emits `frames` then DIES mid-stream (transport failure). */
function makeDyingFetchStream(frames: string[], err: Error) {
  const encoder = new TextEncoder();
  const chunks = frames.map((f) => encoder.encode(f));
  let i = 0;
  const reader = {
    read: jest.fn().mockImplementation(() => {
      if (i < chunks.length) {
        return Promise.resolve({ done: false, value: chunks[i++] });
      }
      return Promise.reject(err);
    }),
  };
  return { ok: true, body: { getReader: () => reader } };
}

/** Drain the read loop under REAL timers. */
async function flush(times = 30): Promise<void> {
  for (let i = 0; i < times; i++) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setImmediate(r));
  }
}

/** Drain the read loop under FAKE timers (microtasks only — no setImmediate). */
async function microFlush(times = 80): Promise<void> {
  for (let i = 0; i < times; i++) {
    // eslint-disable-next-line no-await-in-loop
    await Promise.resolve();
  }
}

describe('streamComparison — A7 settle_complete terminal latch', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = (global as any).fetch;
    (global as any).fetch = jest.fn();
    axiosInstance.get.mockReset();
    expoFetchMock.mockReset();
    const sentry = require('../src/services/sentry');
    (sentry.addSseFallbackBreadcrumb as jest.Mock).mockReset();
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(true);
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(null);
  });

  it('a transport error AFTER settle_complete does NOT buy a second compare', async () => {
    // The double-spend window: settle_complete and complete are two separate
    // wire writes of the same multi-KB payload. A failure in between must not
    // re-request — the compare already succeeded and was already metered.
    const payload = { success: true, comparison: 'settled' };
    expoFetchMock.mockResolvedValue(
      makeDyingFetchStream(
        [sseFrame('settle_complete', payload)],
        new Error('transport died between settle_complete and complete'),
      ),
    );
    axiosInstance.get.mockResolvedValue({ data: { success: true, comparison: 'REST' } });

    const { streamComparison } = require('../src/services/api');
    const onComplete = jest.fn();
    const onSettleComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({
      onComplete,
      onSettleComplete,
      onError,
    });
    await flush();

    // THE INVARIANT: no REST re-run after a delivered result.
    expect(axiosInstance.get).not.toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledWith(payload);
    expect(onSettleComplete).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
  });

  it('the settle_complete + complete pair delivers exactly ONE onComplete, at the settle frame', async () => {
    // Both events coexist today and carry the IDENTICAL payload object. The
    // dispatch must fire once — and at the FIRST final payload, which the
    // interleaved `verdict` frame makes observable.
    const payload = { success: true, comparison: 'ok' };
    expoFetchMock.mockResolvedValue(
      makeFetchStream([
        sseFrame('settle_complete', payload),
        sseFrame('verdict', { product_index: 0 }),
        sseFrame('complete', payload),
      ]),
    );

    const { streamComparison } = require('../src/services/api');
    const onComplete = jest.fn();
    const onSettleComplete = jest.fn();
    const onVerdict = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({
      onComplete,
      onSettleComplete,
      onVerdict,
      onError,
    });
    await flush();

    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledWith(payload);
    expect(onSettleComplete).toHaveBeenCalledTimes(1);
    expect(onVerdict).toHaveBeenCalledTimes(1);
    // Dispatched on settle_complete, not on the duplicate that follows it.
    expect(onComplete.mock.invocationCallOrder[0]).toBeLessThan(
      onVerdict.mock.invocationCallOrder[0],
    );
    expect(onError).not.toHaveBeenCalled();
    expect(axiosInstance.get).not.toHaveBeenCalled();
  });

  it('the latch is FIRST-wins: a diverging duplicate never overwrites the delivered result', async () => {
    // Identical payloads are the contract today, so first-vs-last is invisible
    // — until the two diverge. First-wins keeps the result the user is already
    // looking at, and is what makes the pair idempotent.
    expoFetchMock.mockResolvedValue(
      makeFetchStream([
        sseFrame('settle_complete', { success: true, comparison: 'FIRST' }),
        sseFrame('complete', { success: true, comparison: 'SECOND' }),
      ]),
    );

    const { streamComparison } = require('../src/services/api');
    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onComplete, onError });
    await flush();

    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledWith({ success: true, comparison: 'FIRST' });
    expect(onError).not.toHaveBeenCalled();
  });

  it('a success:false settle_complete routes to the structured onError, never onComplete', async () => {
    // The hard-cap shape has to survive the move: HomeScreen substitutes the
    // friendly results.timeout.* copy off the CODE, so the synthetic
    // axios-shaped 503 must be preserved on the settle frame too.
    expoFetchMock.mockResolvedValue(
      makeFetchStream([
        sseFrame('settle_complete', {
          success: false,
          code: 'TIMEOUT',
          error: 'hard cap reached',
        }),
      ]),
    );

    const { streamComparison } = require('../src/services/api');
    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onComplete, onError });
    await flush();

    expect(onComplete).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(1);
    const err = onError.mock.calls[0][0];
    expect(err.response.status).toBe(503);
    expect(err.response.data.code).toBe('TIMEOUT');
    expect(axiosInstance.get).not.toHaveBeenCalled();
  });

  describe('watchdog disarm', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('a settle_complete-only stream disarms the 60s watchdog — no late timeout over a succeeded compare', async () => {
      // The Bundle-F shape: `complete` deleted server-side. Before the fix the
      // watchdog was armed for a full STREAM_WATCHDOG_MS and then fired a
      // STREAM_TIMEOUT onError over a compare that had already succeeded.
      const payload = { success: true, comparison: 'settle-only' };
      expoFetchMock.mockResolvedValue(
        makeFetchStream([
          sseFrame('first_paint', { progress: 50 }),
          sseFrame('settle_complete', payload),
        ]),
      );

      const { streamComparison, STREAM_WATCHDOG_MS } = require('../src/services/api');
      const onComplete = jest.fn();
      const onError = jest.fn();
      streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({ onComplete, onError });
      await microFlush();

      expect(onComplete).toHaveBeenCalledTimes(1);
      expect(onComplete).toHaveBeenCalledWith(payload);

      jest.advanceTimersByTime(STREAM_WATCHDOG_MS + 1000);
      await microFlush(10);

      expect(onError).not.toHaveBeenCalled();
      expect(onComplete).toHaveBeenCalledTimes(1);
    });
  });
});
