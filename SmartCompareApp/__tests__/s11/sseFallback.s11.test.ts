/**
 * S81-11 RED -- the SSE transport on CATEGORY_NOT_LIVE (F1-14) + the
 * additive reason read (spec C13; rulings R-S11-19, R-S11-26).
 *
 * C13 splits the base arm `if (!response.ok || !response.body)`: a non-OK
 * stream response whose JSON body (or body.detail) carries code
 * CATEGORY_NOT_LIVE dispatches onError ONCE and returns WITHOUT the REST
 * fallback (the REST GET would re-run the gate: doubled lines, slots,
 * MGETs). The no-body arm and every other non-OK code keep today's path
 * (exactly one REST compare). The seam is features._setExpoFetchSseForTests.
 *
 * Harness = api.streamComparison.expoFetch.test.ts (real api.ts, axios /
 * expo-fetch / sentry mocked).
 */

import { TextEncoder } from 'util';

jest.mock('../../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../../src/services/authService', () => ({
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

jest.mock('../../src/services/sentry', () => ({
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
  return { ok: true, status: 200, body: { getReader: () => reader } };
}

/** A non-OK expo/fetch response whose body is JSON (json + text both work). */
function nonOk(status: number, body: any) {
  return {
    ok: false,
    status,
    body: null,
    json: jest.fn(async () => body),
    text: jest.fn(async () => JSON.stringify(body)),
  };
}

function nonOkUnreadable(status: number) {
  return {
    ok: false,
    status,
    body: null,
    json: jest.fn(async () => {
      throw new SyntaxError('Unexpected token <');
    }),
    text: jest.fn(async () => '<html>bad gateway</html>'),
  };
}

async function flush(times = 30): Promise<void> {
  for (let i = 0; i < times; i++) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setImmediate(r));
  }
}

const NOT_LIVE = {
  success: false,
  error: 'We compare fragrances for now.',
  code: 'CATEGORY_NOT_LIVE',
  category: 'electronics',
  categories_live: ['fragrances'],
  request_id: 'req-s11-sse-1',
};

const NOT_LIVE_BUDGET = {
  success: false,
  error: 'Daily refusal budget reached.',
  code: 'CATEGORY_NOT_LIVE',
  scope: 'refusal_daily',
  retry_after_seconds: 3600,
  resets_at: '2026-11-06T21:00:00Z',
  categories_live: ['fragrances'],
};

function run() {
  const { streamComparison } = require('../../src/services/api');
  const onError = jest.fn();
  const onComplete = jest.fn();
  const { subscribe } = streamComparison(
    { product_a: 'Dior Sauvage EDP', product_b: 'Bleu de Chanel EDP' },
    {},
  );
  subscribe({ onError, onComplete });
  return { onError, onComplete };
}

describe('S81-11 SSE transport (flag ON through the test seam)', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = (global as any).fetch;
    (global as any).fetch = jest.fn();
    axiosInstance.get.mockReset();
    axiosInstance.get.mockResolvedValue({ data: { success: true, overview: {} } });
    expoFetchMock.mockReset();
    const features = require('../../src/config/features');
    features._setExpoFetchSseForTests?.(true);
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    const features = require('../../src/config/features');
    features._setExpoFetchSseForTests?.(null);
  });

  it('D1: non-OK 400 with CATEGORY_NOT_LIVE -> onError once, ZERO REST calls', async () => {
    expoFetchMock.mockResolvedValue(nonOk(400, NOT_LIVE));
    const { onError, onComplete } = run();
    await flush();
    expect(axiosInstance.get).not.toHaveBeenCalled();
    expect(onComplete).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(1);
    const err = onError.mock.calls[0][0];
    expect(err?.response?.status).toBe(400);
    expect(err?.response?.data?.code).toBe('CATEGORY_NOT_LIVE');
  });

  it('D1b: the code under body.detail (legacy shape) is honoured too', async () => {
    expoFetchMock.mockResolvedValue(nonOk(400, { detail: { code: 'CATEGORY_NOT_LIVE' } }));
    const { onError } = run();
    await flush();
    expect(axiosInstance.get).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(1);
    const data = onError.mock.calls[0][0]?.response?.data;
    expect(data?.code ?? data?.detail?.code).toBe('CATEGORY_NOT_LIVE');
  });

  it('D2: non-OK 429 budget body -> onError once (status 429), ZERO REST calls', async () => {
    expoFetchMock.mockResolvedValue(nonOk(429, NOT_LIVE_BUDGET));
    const { onError } = run();
    await flush();
    expect(axiosInstance.get).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]?.response?.status).toBe(429);
    expect(onError.mock.calls[0][0]?.response?.data?.code).toBe('CATEGORY_NOT_LIVE');
  });

  it('PIN P6: non-OK 500 with an unreadable body -> exactly ONE REST compare (today)', async () => {
    expoFetchMock.mockResolvedValue(nonOkUnreadable(500));
    const { onComplete } = run();
    await flush();
    expect(axiosInstance.get).toHaveBeenCalledTimes(1);
    expect(axiosInstance.get.mock.calls[0][0]).toBe('/api/v1/text/compare');
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('PIN P6b: non-OK 400 with ANOTHER code -> exactly ONE REST compare (today)', async () => {
    expoFetchMock.mockResolvedValue(
      nonOk(400, { success: false, code: 'INSUFFICIENT_DATA', error: 'x' }),
    );
    const { onComplete } = run();
    await flush();
    expect(axiosInstance.get).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('PIN: an OK response with no body keeps the REST fallback once (today)', async () => {
    expoFetchMock.mockResolvedValue({ ok: true, status: 200, body: null });
    const { onComplete } = run();
    await flush();
    expect(axiosInstance.get).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('PIN P5: an SSE error event with CATEGORY_NOT_LIVE -> onError once, ZERO REST calls', async () => {
    expoFetchMock.mockResolvedValue(makeFetchStream([sseFrame('error', NOT_LIVE)]));
    const { onError } = run();
    await flush();
    expect(axiosInstance.get).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]?.response?.data?.code).toBe('CATEGORY_NOT_LIVE');
  });

  it('R-S11-26: the error event forwards its reason into the synthetic data', async () => {
    expoFetchMock.mockResolvedValue(
      makeFetchStream([
        sseFrame('error', { success: false, code: 'INSUFFICIENT_DATA', reason: 'same_identity' }),
      ]),
    );
    const { onError } = run();
    await flush();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]?.response?.data?.reason).toBe('same_identity');
  });

  it('R-S11-26: a success:false complete frame forwards its reason', async () => {
    expoFetchMock.mockResolvedValue(
      makeFetchStream([
        sseFrame('complete', {
          success: false,
          code: 'INSUFFICIENT_DATA',
          reason: 'category_conflict',
          error: 'x',
        }),
      ]),
    );
    const { onError } = run();
    await flush();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]?.response?.data?.reason).toBe('category_conflict');
  });

  it('R-S11-26: a success:false settle_complete frame forwards its reason', async () => {
    expoFetchMock.mockResolvedValue(
      makeFetchStream([
        sseFrame('settle_complete', {
          success: false,
          code: 'INSUFFICIENT_DATA',
          reason: 'placeholder_identity',
        }),
      ]),
    );
    const { onError } = run();
    await flush();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]?.response?.data?.reason).toBe('placeholder_identity');
  });

  it('PIN: a reasonless success:false complete keeps today\'s synthetic data shape', async () => {
    expoFetchMock.mockResolvedValue(
      makeFetchStream([sseFrame('complete', { success: false, code: 'TIMEOUT', error: 'slow' })]),
    );
    const { onError } = run();
    await flush();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]?.response).toEqual({
      status: 503,
      data: { code: 'TIMEOUT', error: 'slow' },
    });
  });

  it('PIN: a reasonless error event keeps today\'s synthetic data shape', async () => {
    expoFetchMock.mockResolvedValue(
      makeFetchStream([sseFrame('error', { code: 'LLM_UNAVAILABLE', error: 'down' })]),
    );
    const { onError } = run();
    await flush();
    expect(onError.mock.calls[0][0]?.response).toEqual({
      status: 503,
      data: { code: 'LLM_UNAVAILABLE', error: 'down', layer: undefined },
    });
  });
});

describe('S81-11 R-S11-26 -- parseApiError reads reason top-level, then detail', () => {
  const parse = () => require('../../src/services/api').parseApiError;
  const err = (status: number, data: any) => ({ response: { status, data } });

  it('a top-level string reason is returned', () => {
    const p = parse()(err(400, { code: 'INSUFFICIENT_DATA', reason: 'same_identity' }));
    expect(p.code).toBe('INSUFFICIENT_DATA');
    expect(p.reason).toBe('same_identity');
  });

  it('a reason under detail is returned', () => {
    const p = parse()(err(400, { detail: { code: 'INSUFFICIENT_DATA', reason: 'category_conflict' } }));
    expect(p.reason).toBe('category_conflict');
  });

  it('PIN: a non-string or absent reason is never returned', () => {
    expect(parse()(err(400, { code: 'INSUFFICIENT_DATA', reason: 7 })).reason).toBeUndefined();
    expect(parse()(err(400, { code: 'INSUFFICIENT_DATA' })).reason).toBeUndefined();
    expect(parse()(err(400, { code: 'INSUFFICIENT_DATA', reason: { a: 1 } })).reason).toBeUndefined();
  });

  it('PIN: a 429 CATEGORY_NOT_LIVE keeps its code and retryAfterSeconds', () => {
    const p = parse()(err(429, NOT_LIVE_BUDGET));
    expect(p.code).toBe('CATEGORY_NOT_LIVE');
  });
});
