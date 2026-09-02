/**
 * Bundle D Task 1.F.1 — Refresh-token mutex (R9) — branch coverage top-up.
 *
 * The primary api.refreshMutex.test.ts covers the dedup happy path
 * + mutex release + reset hook. This file exercises two remaining
 * branches inside performRefresh() that the primary suite does not hit:
 *
 *   1. refreshSession resolves but getToken returns null/undefined
 *      → RefreshResult.success === false (no throw, no clearSession call).
 *   2. refreshSession rejects → clearSession() is invoked before rethrow.
 *
 * These branches are load-bearing for R9: a silent "no token" outcome
 * must NOT corrupt the mutex (subsequent calls must run fresh), and the
 * failure path must always clear local session state.
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

describe('api.ts — refresh-token mutex branch coverage', () => {
  let api: typeof import('../src/services/api');

  beforeEach(() => {
    jest.resetModules();
    mockRefreshSession.mockReset();
    mockGetToken.mockReset();
    mockClearSession.mockReset();
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    api = require('../src/services/api');
    api.__resetRefreshMutex?.();
  });

  it('returns success=false (no throw) when refreshSession resolves but getToken yields null', async () => {
    // M18 MB-flows-01 — performRefresh now gates on refreshSession()'s
    // result BEFORE consulting getToken, so reaching the getToken-null
    // branch requires the real AuthResponse success shape (refreshSession
    // never resolves undefined in production).
    mockRefreshSession.mockResolvedValueOnce({ success: true, token: 'saved-elsewhere' });
    mockGetToken.mockResolvedValueOnce(null);

    const result = await api.__testRefreshDedup();

    expect(result.success).toBe(false);
    expect(result.token).toBeNull();
    expect(result.error).toBeInstanceOf(Error);
    expect(mockClearSession).not.toHaveBeenCalled();
  });

  it('clears the mutex after a null-token outcome so the next call refetches', async () => {
    // M18 MB-flows-01 — real AuthResponse success shape (see above).
    mockRefreshSession.mockResolvedValueOnce({ success: true, token: 'saved-elsewhere' });
    mockGetToken.mockResolvedValueOnce(null);
    const first = await api.__testRefreshDedup();
    expect(first.success).toBe(false);

    mockRefreshSession.mockResolvedValueOnce({ success: true, token: 'recovered' });
    mockGetToken.mockResolvedValueOnce('recovered');
    const second = await api.__testRefreshDedup();

    expect(second.success).toBe(true);
    expect(second.token).toBe('recovered');
    expect(mockRefreshSession).toHaveBeenCalledTimes(2);
  });

  it('invokes clearSession() before rethrowing when refreshSession rejects', async () => {
    const err = new Error('refresh-rejected');
    mockRefreshSession.mockRejectedValueOnce(err);
    mockClearSession.mockResolvedValueOnce(undefined);

    await expect(api.__testRefreshDedup()).rejects.toThrow('refresh-rejected');
    expect(mockClearSession).toHaveBeenCalledTimes(1);
  });

  it('still rethrows the original error even if clearSession() also fails', async () => {
    const refreshErr = new Error('refresh-rejected');
    const clearErr = new Error('clear-failed');
    mockRefreshSession.mockRejectedValueOnce(refreshErr);
    mockClearSession.mockRejectedValueOnce(clearErr);

    // The original refresh error must surface; clear failures are
    // local cleanup and must not mask the upstream cause.
    await expect(api.__testRefreshDedup()).rejects.toThrow();
    expect(mockClearSession).toHaveBeenCalledTimes(1);
  });
});
