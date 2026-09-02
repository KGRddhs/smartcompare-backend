/**
 * M18 MB-flows-01 — performRefresh must gate on refreshSession()'s
 * RESULT, not on the mere presence of SOME token in SecureStore.
 *
 * authService.refreshSession resolves (does not throw) with
 * `{ success: false }` on three paths that all leave the STALE access
 * token in SecureStore: no refresh token, 200-without-session, and
 * non-401 (network) errors. The old performRefresh ignored the result
 * and checked only `getToken()`, so the 401 interceptor re-attached the
 * IDENTICAL dead token and replayed the request — a doomed retry that
 * callers read as a request failure, never a session failure.
 *
 * New contract pinned here:
 *   - refreshSession -> {success:false, sessionInvalid:true}
 *       => performRefresh fails, clears the session, emits
 *          session-invalid (MB-flows-02 hook), interceptor does NOT
 *          replay even though a stale token is still readable.
 *   - refreshSession -> {success:false} (transient / network)
 *       => performRefresh fails WITHOUT clearing the session (a flaky
 *          network must never log the user out) and without emitting.
 *   - refreshSession -> {success:true} => unchanged success path.
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
  const instanceFn: any = (cfg: any) => mockApiCall(cfg);
  Object.assign(instanceFn, instance);
  return { create: jest.fn(() => instanceFn), __instance: instanceFn };
});

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(),
  SaveFormat: { JPEG: 'jpeg' },
}));

describe('api.ts — M18 MB-flows-01 refresh-result gate', () => {
  let api: typeof import('../src/services/api');
  let sessionEvents: typeof import('../src/services/sessionEvents');
  let sessionInvalidCalls: number;

  beforeEach(() => {
    jest.resetModules();
    capturedResponseHandler = null;
    mockApiCall.mockReset();
    mockRefreshSession.mockReset();
    mockGetToken.mockReset();
    mockClearSession.mockReset();
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    api = require('../src/services/api');
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    sessionEvents = require('../src/services/sessionEvents');
    sessionEvents.__resetSessionListeners();
    sessionInvalidCalls = 0;
    sessionEvents.onSessionInvalid(() => {
      sessionInvalidCalls += 1;
    });
    api.__resetRefreshMutex?.();
  });

  it('fails + clears session + emits when refreshSession reports the session invalid, even though a stale token is still stored', async () => {
    mockRefreshSession.mockResolvedValueOnce({
      success: false,
      error: 'No refresh token found',
      sessionInvalid: true,
    });
    // The stale access token is STILL readable — the old code turned
    // this into a fake success.
    mockGetToken.mockResolvedValue('stale-dead-token');

    const result = await api.__testRefreshDedup();

    expect(result.success).toBe(false);
    expect(result.token).toBeNull();
    expect(mockClearSession).toHaveBeenCalledTimes(1);
    expect(sessionInvalidCalls).toBe(1);
  });

  it('fails WITHOUT clearing or emitting on a transient (network) refresh failure', async () => {
    mockRefreshSession.mockResolvedValueOnce({
      success: false,
      error: 'Network Error',
    });
    mockGetToken.mockResolvedValue('stale-but-keep-me');

    const result = await api.__testRefreshDedup();

    expect(result.success).toBe(false);
    expect(result.token).toBeNull();
    expect(mockClearSession).not.toHaveBeenCalled();
    expect(sessionInvalidCalls).toBe(0);
  });

  it('interceptor does NOT replay the identical dead token when refresh reports failure', async () => {
    mockRefreshSession.mockResolvedValueOnce({
      success: false,
      error: 'Refresh failed',
      sessionInvalid: true,
    });
    mockGetToken.mockResolvedValue('stale-dead-token');

    const originalRequest: any = { url: '/api/v1/comparisons', headers: {} };
    const error = { response: { status: 401 }, config: originalRequest };

    await expect(capturedResponseHandler!(error)).rejects.toBe(error);
    // The doomed replay with the same dead token must be gone.
    expect(mockApiCall).not.toHaveBeenCalled();
    expect(originalRequest.headers.Authorization).toBeUndefined();
  });

  it('interceptor still replays with the fresh token on a genuine refresh success', async () => {
    mockRefreshSession.mockResolvedValueOnce({ success: true, token: 'fresh' });
    mockGetToken.mockResolvedValue('fresh');
    mockApiCall.mockResolvedValueOnce({ status: 200, data: { ok: true } });

    const originalRequest: any = { url: '/api/v1/comparisons', headers: {} };
    const error = { response: { status: 401 }, config: originalRequest };

    const result = await capturedResponseHandler!(error);

    expect(originalRequest.headers.Authorization).toBe('Bearer fresh');
    expect(mockApiCall).toHaveBeenCalledWith(originalRequest);
    expect(result).toEqual({ status: 200, data: { ok: true } });
    expect(sessionInvalidCalls).toBe(0);
  });

  it('emits session-invalid on the thrown-refresh path (existing clearSession site)', async () => {
    mockRefreshSession.mockRejectedValueOnce(new Error('refresh-blew-up'));
    mockClearSession.mockResolvedValueOnce(undefined);

    await expect(api.__testRefreshDedup()).rejects.toThrow('refresh-blew-up');
    expect(mockClearSession).toHaveBeenCalledTimes(1);
    expect(sessionInvalidCalls).toBe(1);
  });

  it('releases the mutex after an invalid-session outcome so a later login can refresh fresh', async () => {
    mockRefreshSession.mockResolvedValueOnce({
      success: false,
      sessionInvalid: true,
    });
    mockGetToken.mockResolvedValue(null);
    const first = await api.__testRefreshDedup();
    expect(first.success).toBe(false);

    mockRefreshSession.mockResolvedValueOnce({ success: true, token: 'recovered' });
    mockGetToken.mockResolvedValue('recovered');
    const second = await api.__testRefreshDedup();

    expect(second.success).toBe(true);
    expect(second.token).toBe('recovered');
    expect(mockRefreshSession).toHaveBeenCalledTimes(2);
  });
});
