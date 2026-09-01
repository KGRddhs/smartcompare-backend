/**
 * #118 — streamComparison flag-OFF transport contract.
 *
 * THE INVARIANT: exactly ONE backend request per user compare on a
 * platform without a streaming fetch. React Native's global fetch is the
 * whatwg-fetch polyfill (no `response.body` ReadableStream), so the old
 * code's stream attempt ALWAYS threw after the backend had already run a
 * full comparison, and the catch block then issued a SECOND full REST
 * compare — double OpenAI + double Serper per tap.
 *
 * With ENABLE_EXPO_FETCH_SSE=false (the shipped default), streamComparison
 * must never touch global fetch at all: it goes straight to the single
 * axios GET /api/v1/text/compare.
 */

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

const axiosInstance = (require('axios') as any).__instance;

/** Yield to pending microtasks so the async subscribe body settles. */
async function flush(times = 25): Promise<void> {
  for (let i = 0; i < times; i++) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setImmediate(r));
  }
}

describe('streamComparison — #118 flag OFF (no-ReadableStream platform)', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = (global as any).fetch;
    (global as any).fetch = jest.fn();
    axiosInstance.get.mockReset();
    // Optional-call so this file is meaningfully RED (not import-broken)
    // at the pre-#118 base where the flag does not exist yet.
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(false);
  });

  afterEach(() => {
    (global as any).fetch = originalFetch;
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(null);
  });

  it('flag OFF: never touches global fetch and issues exactly one REST compare', async () => {
    axiosInstance.get.mockResolvedValue({
      data: { success: true, comparison: 'ok' },
    });
    const { streamComparison } = require('../src/services/api');

    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({
      onComplete,
      onError,
    });
    await flush();

    expect((global as any).fetch).not.toHaveBeenCalled();
    expect(axiosInstance.get).toHaveBeenCalledTimes(1);
    expect(axiosInstance.get).toHaveBeenCalledWith(
      '/api/v1/text/compare',
      expect.objectContaining({
        params: expect.objectContaining({
          product_a: 'a',
          product_b: 'b',
          region: 'bahrain',
        }),
      }),
    );
  });

  it('flag OFF: routes a success:true payload to onComplete and never to onError', async () => {
    const payload = { success: true, comparison: 'ok' };
    axiosInstance.get.mockResolvedValue({ data: payload });
    const { streamComparison } = require('../src/services/api');

    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({
      onComplete,
      onError,
    });
    await flush();

    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledWith(payload);
    expect(onError).not.toHaveBeenCalled();
  });

  it('flag OFF: a success:false payload keeps the synthetic axios-shaped error (code preserved)', async () => {
    axiosInstance.get.mockResolvedValue({
      data: { success: false, error: 'took too long', code: 'TIMEOUT' },
    });
    const { streamComparison } = require('../src/services/api');

    const onComplete = jest.fn();
    const onError = jest.fn();
    streamComparison({ product_a: 'a', product_b: 'b' }).subscribe({
      onComplete,
      onError,
    });
    await flush();

    expect(onComplete).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(1);
    const err = onError.mock.calls[0][0];
    expect(err.response).toEqual({
      status: 200,
      data: { code: 'TIMEOUT', error: 'took too long' },
    });
    expect((global as any).fetch).not.toHaveBeenCalled();
  });
});
