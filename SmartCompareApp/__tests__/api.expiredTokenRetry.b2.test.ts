/**
 * B2 — the client half of the expired-token contract.
 *
 * Backend `ENABLE_STRICT_OPTIONAL_AUTH` makes `/api/v1/text/compare` answer a
 * PRESENTED-but-rejected Bearer token with 401 `AUTH_REQUIRED` instead of
 * silently running an anonymous, unmetered, unsaved compare. That is only a
 * repair if the client actually completes the loop, so this file drives the
 * REAL axios instance (real request + response interceptors, only the
 * transport swapped for a stub adapter) through the whole sequence:
 *
 *   compare with the stale token -> 401
 *     -> the response interceptor refreshes
 *     -> it RE-DRIVES the original compare, carrying the NEW Bearer
 *     -> onComplete fires ONCE with the result; onError never fires
 *
 * The sibling suite api.refreshInterceptor.test.ts captures the interceptor
 * handler in isolation against a fully mocked axios. This one is deliberately
 * end-to-end over the compare path — the request the usage bracket meters —
 * because that is the request B2 is about, and because a stub-axios test
 * cannot see the request interceptor re-attaching the refreshed token.
 */

jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

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

const EXPIRED = 'expired-token';
const FRESH = 'fresh-token';

let storedToken: string | null = EXPIRED;
const mockRefreshSession = jest.fn();
const mockClearSession = jest.fn(async () => {
  storedToken = null;
});

jest.mock('../src/services/authService', () => ({
  getToken: jest.fn(async () => storedToken),
  refreshSession: (...args: any[]) => mockRefreshSession(...args),
  clearSession: (...args: any[]) => mockClearSession(...(args as [])),
}));

/** Yield to pending microtasks so the async subscribe body settles. */
async function flush(times = 30): Promise<void> {
  for (let i = 0; i < times; i++) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setImmediate(r));
  }
}

function readAuthHeader(config: any): string | undefined {
  const h = config?.headers;
  if (!h) return undefined;
  if (typeof h.get === 'function') return h.get('Authorization') ?? h.Authorization;
  return h.Authorization;
}

const COMPARE_PAYLOAD = {
  success: true,
  products: [{ brand: 'A', name: '1' }, { brand: 'B', name: '2' }],
  metadata: { total_cost: 0 },
};

describe('B2 — expired token on the REST compare: 401 -> refresh -> retry', () => {
  let apiModule: typeof import('../src/services/api');
  let seenAuth: (string | undefined)[];
  let seenUrls: string[];

  beforeEach(() => {
    jest.resetModules();
    seenAuth = [];
    seenUrls = [];
    storedToken = EXPIRED;
    mockRefreshSession.mockReset();
    mockClearSession.mockClear();

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(false); // shipped default: REST path

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    apiModule = require('../src/services/api');
    apiModule.__resetRefreshMutex?.();

    // Swap ONLY the transport. Every interceptor api.ts registers still runs.
    (apiModule.api as any).defaults.adapter = async (config: any) => {
      const auth = readAuthHeader(config);
      seenAuth.push(auth);
      seenUrls.push(config.url);
      if (auth === `Bearer ${FRESH}`) {
        return {
          data: COMPARE_PAYLOAD,
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        };
      }
      // The strict-mode backend envelope for a presented-but-rejected token.
      const err: any = new Error('Request failed with status code 401');
      err.isAxiosError = true;
      err.config = config;
      err.response = {
        status: 401,
        statusText: 'Unauthorized',
        data: {
          success: false,
          error: 'Invalid or expired token',
          code: 'AUTH_REQUIRED',
          request_id: 'req-b2',
        },
        headers: {},
        config,
      };
      throw err;
    };
  });

  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const features = require('../src/config/features');
    features._setExpoFetchSseForTests?.(null);
  });

  it('re-drives the compare with the refreshed token and completes once', async () => {
    mockRefreshSession.mockImplementation(async () => {
      storedToken = FRESH;
      return { success: true };
    });

    const onComplete = jest.fn();
    const onError = jest.fn();
    apiModule.streamComparison('iPhone 15 vs Galaxy S24').subscribe({
      onComplete,
      onError,
    });
    await flush();

    // Exactly two transport hits: the rejected original and its retry.
    expect(seenAuth).toEqual([`Bearer ${EXPIRED}`, `Bearer ${FRESH}`]);
    // Both are the SAME compare request — the retry is a re-drive, not a
    // different call, so the backend meters/persists it exactly once.
    expect(seenUrls).toEqual([
      '/api/v1/text/compare',
      '/api/v1/text/compare',
    ]);
    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledWith(COMPARE_PAYLOAD);
    expect(onError).not.toHaveBeenCalled();
  });

  it('carries the original query params onto the retried compare', async () => {
    const seenParams: any[] = [];
    const inner = (apiModule.api as any).defaults.adapter;
    (apiModule.api as any).defaults.adapter = async (config: any) => {
      seenParams.push(config.params);
      return inner(config);
    };
    mockRefreshSession.mockImplementation(async () => {
      storedToken = FRESH;
      return { success: true };
    });

    apiModule
      .streamComparison(
        { product_a: 'iPhone 15', product_b: 'Galaxy S24' },
        { nocache: true, selected_category: 'Electronics' },
      )
      .subscribe({ onComplete: jest.fn(), onError: jest.fn() });
    await flush();

    expect(seenParams).toHaveLength(2);
    // A retry that dropped the pair / category would silently buy a DIFFERENT
    // comparison than the one the user asked for.
    expect(seenParams[1]).toEqual(seenParams[0]);
    expect(seenParams[1]).toMatchObject({
      product_a: 'iPhone 15',
      product_b: 'Galaxy S24',
      region: 'bahrain',
      selected_category: 'Electronics',
      nocache: true,
    });
  });

  it('a dead session surfaces the error instead of looping the compare', async () => {
    // refreshSession resolves success:false + sessionInvalid — the refresh
    // token itself is gone, so there is nothing to retry with.
    mockRefreshSession.mockResolvedValue({
      success: false,
      sessionInvalid: true,
      error: 'no refresh token',
    });

    const onComplete = jest.fn();
    const onError = jest.fn();
    apiModule.streamComparison('iPhone 15 vs Galaxy S24').subscribe({
      onComplete,
      onError,
    });
    await flush();

    expect(seenAuth).toEqual([`Bearer ${EXPIRED}`]); // no second compare
    expect(mockClearSession).toHaveBeenCalledTimes(1);
    expect(onComplete).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]?.response?.status).toBe(401);
  });

  describe('with the expo/fetch SSE transport enabled', () => {
    // The SSE branch attaches the token by hand and has NO interceptor, so a
    // strict-mode 401 arrives there as a bare `!response.ok`. It must still
    // heal — via the ONE REST fallback — and must not buy two compares.
    beforeEach(() => {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      require('../src/config/features')._setExpoFetchSseForTests?.(true);
    });

    it('a 401 on the stream falls back to exactly one REST compare that retries', async () => {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const expoFetch = require('expo/fetch').fetch as jest.Mock;
      expoFetch.mockReset();
      expoFetch.mockResolvedValue({ ok: false, status: 401, body: null });

      mockRefreshSession.mockImplementation(async () => {
        storedToken = FRESH;
        return { success: true };
      });

      const onComplete = jest.fn();
      const onError = jest.fn();
      apiModule.streamComparison('iPhone 15 vs Galaxy S24').subscribe({
        onComplete,
        onError,
      });
      await flush();

      expect(expoFetch).toHaveBeenCalledTimes(1);
      // One REST compare, rejected, then its single retry — never two
      // independent compares (the #118 double-spend).
      expect(seenAuth).toEqual([`Bearer ${EXPIRED}`, `Bearer ${FRESH}`]);
      expect(onComplete).toHaveBeenCalledTimes(1);
      expect(onComplete).toHaveBeenCalledWith(COMPARE_PAYLOAD);
      expect(onError).not.toHaveBeenCalled();
    });
  });
});
