/**
 * Bundle D Task 1.F.1 — Refresh-token mutex (R9) — 401 interceptor wiring.
 *
 * api.refreshMutex.test.ts covers the mutex primitive in isolation.
 * This file captures the axios response-interceptor handler that api.ts
 * registers at module load time and invokes it end-to-end so the
 * mutex-consumer code path (lines 114-123 of api.ts at commit 03b9139)
 * is exercised:
 *
 *   - 401 → mutex returns success → retries originalRequest with new Bearer
 *   - 401 → mutex returns success=false → original 401 rejection propagates
 *   - 401 → mutex throws → refreshError rejection propagates
 *   - 401 already retried (_retry=true) → rejection without mutex call
 *   - 401 on auth-flow endpoint → skipped without mutex call
 *   - 429 USAGE_LIMIT (top-level + legacy detail.code) → propagates
 */

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

let capturedResponseHandler: ((err: any) => Promise<any>) | null = null;
const mockApiCall = jest.fn();

jest.mock('axios', () => {
  const instance = {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    request: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: {
        use: (_success: any, errorHandler: any) => {
          capturedResponseHandler = errorHandler;
        },
      },
    },
  };
  // Treat the axios instance itself as the retry-callable
  const instanceFn: any = (cfg: any) => mockApiCall(cfg);
  Object.assign(instanceFn, instance);
  return { create: jest.fn(() => instanceFn), __instance: instanceFn };
});

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(),
  SaveFormat: { JPEG: 'jpeg' },
}));

describe('api.ts — 401 response interceptor wiring (R9 mutex consumer)', () => {
  let api: typeof import('../src/services/api');

  beforeEach(() => {
    jest.resetModules();
    capturedResponseHandler = null;
    mockApiCall.mockReset();
    mockRefreshSession.mockReset();
    mockGetToken.mockReset();
    mockClearSession.mockReset();
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    api = require('../src/services/api');
    api.__resetRefreshMutex?.();
  });

  it('registers a response interceptor at module load', () => {
    expect(typeof capturedResponseHandler).toBe('function');
  });

  it('on 401 success path: refreshes, sets new Bearer, retries originalRequest', async () => {
    // M18 MB-flows-01 — performRefresh now gates on refreshSession()'s
    // result, so the mock returns the real AuthResponse success shape
    // (refreshSession never resolves undefined in production).
    mockRefreshSession.mockResolvedValueOnce({ success: true, token: 'fresh-token' });
    mockGetToken.mockResolvedValueOnce('fresh-token');
    mockApiCall.mockResolvedValueOnce({ status: 200, data: { ok: true } });

    const originalRequest: any = {
      url: '/api/v1/comparisons',
      headers: {},
    };
    const error = { response: { status: 401 }, config: originalRequest };

    const result = await capturedResponseHandler!(error);

    expect(originalRequest._retry).toBe(true);
    expect(originalRequest.headers.Authorization).toBe('Bearer fresh-token');
    expect(mockApiCall).toHaveBeenCalledWith(originalRequest);
    expect(result).toEqual({ status: 200, data: { ok: true } });
  });

  it('on 401 + mutex returns success=false: propagates the original 401 rejection', async () => {
    mockRefreshSession.mockResolvedValueOnce(undefined);
    mockGetToken.mockResolvedValueOnce(null);

    const error = {
      response: { status: 401 },
      config: { url: '/api/v1/comparisons', headers: {} },
    };

    await expect(capturedResponseHandler!(error)).rejects.toBe(error);
    expect(mockApiCall).not.toHaveBeenCalled();
  });

  it('on 401 + mutex throws: propagates the refresh error (not the original 401)', async () => {
    const refreshErr = new Error('refresh-blew-up');
    mockRefreshSession.mockRejectedValueOnce(refreshErr);
    mockClearSession.mockResolvedValueOnce(undefined);

    const error = {
      response: { status: 401 },
      config: { url: '/api/v1/comparisons', headers: {} },
    };

    await expect(capturedResponseHandler!(error)).rejects.toBe(refreshErr);
    expect(mockClearSession).toHaveBeenCalledTimes(1);
  });

  it('on 401 with _retry=true already: rejects without calling the mutex', async () => {
    const error = {
      response: { status: 401 },
      config: { url: '/api/v1/comparisons', headers: {}, _retry: true },
    };

    await expect(capturedResponseHandler!(error)).rejects.toBe(error);
    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it.each([
    '/auth/login',
    '/auth/register',
    '/auth/refresh',
    '/auth/logout',
    '/auth/social-login',
  ])('skips refresh for auth-flow endpoint %s', async (url) => {
    const error = {
      response: { status: 401 },
      config: { url, headers: {} },
    };

    await expect(capturedResponseHandler!(error)).rejects.toBe(error);
    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it('does NOT skip refresh for authenticated /auth/* endpoints like /auth/preferences', async () => {
    // M18 MB-flows-01 — real AuthResponse success shape (see above).
    mockRefreshSession.mockResolvedValueOnce({ success: true, token: 'preferences-token' });
    mockGetToken.mockResolvedValueOnce('preferences-token');
    mockApiCall.mockResolvedValueOnce({ status: 200, data: { saved: true } });

    const originalRequest: any = {
      url: '/api/v1/auth/preferences',
      headers: {},
    };
    const error = { response: { status: 401 }, config: originalRequest };

    await capturedResponseHandler!(error);

    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(originalRequest.headers.Authorization).toBe('Bearer preferences-token');
  });

  it('propagates 429 USAGE_LIMIT in unified top-level shape without invoking mutex', async () => {
    const error = {
      response: { status: 429, data: { code: 'USAGE_LIMIT' } },
      config: { url: '/api/v1/text/compare', headers: {} },
    };

    await expect(capturedResponseHandler!(error)).rejects.toBe(error);
    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it('propagates 429 USAGE_LIMIT in legacy FastAPI detail.code shape', async () => {
    const error = {
      response: { status: 429, data: { detail: { code: 'USAGE_LIMIT' } } },
      config: { url: '/api/v1/text/compare', headers: {} },
    };

    await expect(capturedResponseHandler!(error)).rejects.toBe(error);
    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it('lets non-USAGE_LIMIT 429 fall through (still no refresh — not a 401)', async () => {
    const error = {
      response: { status: 429, data: { code: 'RATE_LIMITED' } },
      config: { url: '/api/v1/text/compare', headers: {} },
    };

    await expect(capturedResponseHandler!(error)).rejects.toBe(error);
    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it('does not touch non-401 non-USAGE_LIMIT errors', async () => {
    const error = {
      response: { status: 500 },
      config: { url: '/api/v1/text/compare', headers: {} },
    };

    await expect(capturedResponseHandler!(error)).rejects.toBe(error);
    expect(mockRefreshSession).not.toHaveBeenCalled();
  });
});
