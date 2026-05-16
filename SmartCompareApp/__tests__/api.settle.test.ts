/**
 * api.streamComparison — Bundle E Phase 3 Task 3.6.
 *
 * Verifies that streamComparison() correctly dispatches the four new
 * settle-window SSE events from the design (§ Decision 8) — first_paint,
 * settle_update, settle_complete, confidence_upgrade — through to the
 * matching callback. The legacy `complete` callback path stays wired so
 * pre-scatter-gather backends keep working during the rollout window.
 *
 * The transport (fetch + ReadableStream) is faked with a controlled
 * Uint8Array stream so we can inject canned SSE frames byte-for-byte
 * without spinning up a server.
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

// Polyfill TextDecoder in jest's node env — RN ships it on device.
if (typeof (global as any).TextDecoder === 'undefined') {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  (global as any).TextDecoder = require('util').TextDecoder;
}

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

describe('streamComparison — Bundle E settle-window SSE dispatch', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = (global as any).fetch;
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    jest.resetModules();
  });

  it('dispatches first_paint, settle_update, confidence_upgrade, settle_complete to matching callbacks', async () => {
    const firstPaintPayload = { progress: 50, scoring_v2: { dimensions: [] } };
    const settleUpdatePayload = {
      field: 'products[0].price',
      new_value: { amount: 30, currency: 'BHD' },
      source_rank: 90,
    };
    const confidenceUpgradePayload = {
      dimension_key: 'price',
      confidence: 'high',
    };
    const settleCompletePayload = {
      success: true,
      comparison: 'ok',
    };

    (global as any).fetch = jest.fn().mockResolvedValue(
      makeFetchStream([
        sseFrame('first_paint', firstPaintPayload),
        sseFrame('settle_update', settleUpdatePayload),
        sseFrame('confidence_upgrade', confidenceUpgradePayload),
        sseFrame('settle_complete', settleCompletePayload),
      ]),
    );

    const { streamComparison } = await import('../src/services/api');

    const onFirstPaint = jest.fn();
    const onSettleUpdate = jest.fn();
    const onConfidenceUpgrade = jest.fn();
    const onSettleComplete = jest.fn();
    const onError = jest.fn();

    const { subscribe } = streamComparison('iphone vs galaxy', {});
    subscribe({
      onFirstPaint,
      onSettleUpdate,
      onConfidenceUpgrade,
      onSettleComplete,
      onError,
    });

    // Drain microtasks until the fake reader has emitted every chunk.
    // The streamComparison loop reads chunks asynchronously, so we yield
    // until either every callback fired or a soft deadline is hit.
    const deadline = Date.now() + 2000;
    while (Date.now() < deadline) {
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => setImmediate(r));
      if (onSettleComplete.mock.calls.length > 0) break;
    }

    expect(onFirstPaint).toHaveBeenCalledTimes(1);
    expect(onFirstPaint).toHaveBeenCalledWith(firstPaintPayload);
    expect(onSettleUpdate).toHaveBeenCalledTimes(1);
    expect(onSettleUpdate).toHaveBeenCalledWith(settleUpdatePayload);
    expect(onConfidenceUpgrade).toHaveBeenCalledTimes(1);
    expect(onConfidenceUpgrade).toHaveBeenCalledWith(confidenceUpgradePayload);
    expect(onSettleComplete).toHaveBeenCalledTimes(1);
    expect(onSettleComplete).toHaveBeenCalledWith(settleCompletePayload);
    expect(onError).not.toHaveBeenCalled();
  });

  it('keeps the legacy onComplete callback wired so older backends continue to work', async () => {
    const completePayload = { success: true, comparison: 'legacy-shape' };
    (global as any).fetch = jest.fn().mockResolvedValue(
      makeFetchStream([sseFrame('complete', completePayload)]),
    );

    const { streamComparison } = await import('../src/services/api');

    const onComplete = jest.fn();
    const onSettleComplete = jest.fn();
    const onError = jest.fn();

    const { subscribe } = streamComparison('a vs b', {});
    subscribe({ onComplete, onSettleComplete, onError });

    const deadline = Date.now() + 2000;
    while (Date.now() < deadline) {
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => setImmediate(r));
      if (onComplete.mock.calls.length > 0) break;
    }

    expect(onComplete).toHaveBeenCalledWith(completePayload);
    expect(onSettleComplete).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });
});
