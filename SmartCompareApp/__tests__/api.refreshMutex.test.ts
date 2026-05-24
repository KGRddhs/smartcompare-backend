/**
 * Bundle D Task 1.F.1 — Refresh-token mutex (R9).
 *
 * Verifies that concurrent 401-triggered refreshes share a single
 * module-scope singleton Promise<RefreshResult> rather than each spawning
 * an independent refreshSession() network call.
 *
 * Anti-regression contract:
 *   - 3 concurrent triggers → exactly 1 refreshSession() invocation
 *   - All 3 callers resolve with the same outcome
 *   - The mutex is released once the in-flight Promise settles
 *   - __resetRefreshMutex() clears the in-flight Promise (test hygiene)
 *   - __testRefreshDedup() exposes the cached Promise for assertions
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

describe('api.ts — refresh-token mutex (R9)', () => {
  let api: typeof import('../src/services/api');

  beforeEach(() => {
    jest.resetModules();
    mockRefreshSession.mockReset();
    mockGetToken.mockReset();
    mockClearSession.mockReset();
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    api = require('../src/services/api');
    if (typeof api.__resetRefreshMutex === 'function') {
      api.__resetRefreshMutex();
    }
  });

  it('exports the test hooks __resetRefreshMutex + __testRefreshDedup', () => {
    expect(typeof api.__resetRefreshMutex).toBe('function');
    expect(typeof api.__testRefreshDedup).toBe('function');
  });

  it('coalesces 3 concurrent refresh triggers into 1 refreshSession() call', async () => {
    let resolveRefresh: (v: any) => void = () => {};
    const refreshPromise = new Promise((res) => {
      resolveRefresh = res;
    });
    mockRefreshSession.mockReturnValue(refreshPromise);
    mockGetToken.mockResolvedValue('new-access-token');

    // Fire 3 concurrent triggers without awaiting
    const p1 = api.__testRefreshDedup();
    const p2 = api.__testRefreshDedup();
    const p3 = api.__testRefreshDedup();

    // All three should share the SAME underlying Promise
    expect(p1).toBe(p2);
    expect(p2).toBe(p3);

    // Resolve the in-flight refresh
    resolveRefresh({ success: true, token: 'new-access-token' });
    const [r1, r2, r3] = await Promise.all([p1, p2, p3]);

    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(r1.success).toBe(true);
    expect(r2.success).toBe(true);
    expect(r3.success).toBe(true);
  });

  it('releases the mutex after settle so a follow-up refresh runs fresh', async () => {
    mockRefreshSession.mockResolvedValue({ success: true });
    mockGetToken.mockResolvedValue('token-1');

    await api.__testRefreshDedup();
    expect(mockRefreshSession).toHaveBeenCalledTimes(1);

    // Follow-up after the first settles should invoke refreshSession again
    mockRefreshSession.mockResolvedValue({ success: true });
    mockGetToken.mockResolvedValue('token-2');
    await api.__testRefreshDedup();
    expect(mockRefreshSession).toHaveBeenCalledTimes(2);
  });

  it('releases the mutex even when refreshSession rejects', async () => {
    mockRefreshSession.mockRejectedValueOnce(new Error('boom'));
    mockGetToken.mockResolvedValue(null);

    await expect(api.__testRefreshDedup()).rejects.toThrow('boom');

    // mutex MUST be cleared on failure path
    mockRefreshSession.mockResolvedValueOnce({ success: true });
    mockGetToken.mockResolvedValueOnce('recovered-token');
    await api.__testRefreshDedup();
    expect(mockRefreshSession).toHaveBeenCalledTimes(2);
  });

  it('__resetRefreshMutex() forcibly clears the in-flight Promise', () => {
    // Kick off a refresh but never resolve it
    mockRefreshSession.mockReturnValue(new Promise(() => {}));
    mockGetToken.mockResolvedValue(null);
    void api.__testRefreshDedup();

    api.__resetRefreshMutex();

    // After reset, a new call must spawn a fresh Promise (different identity)
    mockRefreshSession.mockReturnValue(new Promise(() => {}));
    const fresh = api.__testRefreshDedup();
    expect(mockRefreshSession).toHaveBeenCalledTimes(2);
    expect(fresh).toBeInstanceOf(Promise);
  });
});
