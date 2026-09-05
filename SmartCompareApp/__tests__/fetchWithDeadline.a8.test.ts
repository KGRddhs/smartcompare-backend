/**
 * A8 — `fetchWithDeadline` bounds a raw fetch that never settles.
 *
 * THE DEFECT THIS PINS
 * React Native's fetch (whatwg-fetch over XHR, `timeout` default 0; Android
 * OkHttp connect/read/write all 0) applies NO deadline. A stalled socket does
 * not reject — it never settles — so a `try/catch` around a raw `fetch`
 * catches nothing and the caller's loading state is permanent. Every case
 * below therefore drives a fetch that NEVER SETTLES, which is exactly the
 * shape a `mockRejectedValue` cannot reproduce.
 *
 * Load-bearing detail: the helper must settle the CALLER (the race) *and*
 * release the socket (the abort). Both are asserted separately, because a
 * version that only aborts still hangs on a polyfill that swallows the
 * abort, and a version that only races leaks the in-flight upload.
 */

import {
  fetchWithDeadline,
  isDeadlineError,
  SOCIAL_LOGIN_TIMEOUT_MS,
  DEADLINE_ERROR_CODE,
} from '../src/services/fetchWithDeadline';

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

/** A promise that never settles — a stalled socket, not a rejected one. */
function neverSettles(): Promise<never> {
  return new Promise<never>(() => {});
}

beforeEach(() => {
  mockFetch.mockReset();
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('fetchWithDeadline — deadline expiry', () => {
  it('rejects with code TIMEOUT when the fetch never settles', async () => {
    mockFetch.mockImplementation(() => neverSettles());

    const pending = fetchWithDeadline('https://x.invalid/a', { method: 'POST' }, 25000);
    const assertion = expect(pending).rejects.toMatchObject({
      code: DEADLINE_ERROR_CODE,
      name: 'TimeoutError',
    });

    jest.advanceTimersByTime(25000);
    await assertion;
  });

  it('aborts the underlying request so the socket is released', async () => {
    mockFetch.mockImplementation(() => neverSettles());

    const pending = fetchWithDeadline('https://x.invalid/a', { method: 'POST' }, 25000);
    const assertion = expect(pending).rejects.toBeDefined();

    const signal = mockFetch.mock.calls[0][1].signal;
    expect(signal.aborted).toBe(false);

    jest.advanceTimersByTime(25000);
    await assertion;

    expect(signal.aborted).toBe(true);
  });

  it('does NOT fire one millisecond early', async () => {
    mockFetch.mockImplementation(() => neverSettles());

    const pending = fetchWithDeadline('https://x.invalid/a', {}, 25000);
    let settled = false;
    pending.catch(() => {
      settled = true;
    });

    jest.advanceTimersByTime(24999);
    await Promise.resolve();
    expect(settled).toBe(false);

    jest.advanceTimersByTime(1);
    await expect(pending).rejects.toMatchObject({ code: DEADLINE_ERROR_CODE });
  });

  it('still reports TIMEOUT when the transport rejects LATE, after the abort', async () => {
    // whatwg-fetch rejects on abort, but only once the XHR unwinds — i.e.
    // after the race has already settled. That late rejection must neither
    // change the reported outcome nor surface as an unhandled rejection.
    let rejectLate: (err: unknown) => void = () => {};
    mockFetch.mockImplementation(
      () =>
        new Promise((_resolve, reject) => {
          rejectLate = reject;
        })
    );

    const pending = fetchWithDeadline('https://x.invalid/a', {}, 25000);
    const assertion = expect(pending).rejects.toMatchObject({ code: DEADLINE_ERROR_CODE });

    jest.advanceTimersByTime(25000);
    rejectLate(Object.assign(new Error('Aborted'), { name: 'AbortError' }));

    await assertion;
  });
});

describe('fetchWithDeadline — happy path and pass-through', () => {
  it('resolves with the Response when the fetch completes in time', async () => {
    const response = { ok: true, status: 200 };
    mockFetch.mockResolvedValue(response);

    await expect(fetchWithDeadline('https://x.invalid/a', {}, 25000)).resolves.toBe(response);
  });

  it('clears the deadline timer on success (no timer left armed)', async () => {
    mockFetch.mockResolvedValue({ ok: true, status: 200 });

    await fetchWithDeadline('https://x.invalid/a', {}, 25000);

    // A missing clearTimeout leaves the abort armed: it would fire 25s later
    // and abort a request that already succeeded, on a controller the caller
    // may still be reading the body from.
    expect(jest.getTimerCount()).toBe(0);
  });

  it('propagates a NON-deadline transport error unchanged', async () => {
    // Offline TypeError / TLS / certificate-pinning failures must reach the
    // caller as themselves — authService branches its [B4-DIAG] Sentry
    // capture on exactly this distinction.
    const offline = new TypeError('Network request failed');
    mockFetch.mockRejectedValue(offline);

    await expect(fetchWithDeadline('https://x.invalid/a', {}, 25000)).rejects.toBe(offline);
    expect(isDeadlineError(offline)).toBe(false);
  });

  it('forwards method, headers and body while adding the signal', async () => {
    mockFetch.mockResolvedValue({ ok: true, status: 200 });

    await fetchWithDeadline(
      'https://x.invalid/api/v1/auth/social-login',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{"provider":"google"}',
      },
      25000
    );

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe('https://x.invalid/api/v1/auth/social-login');
    expect(init.method).toBe('POST');
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(init.body).toBe('{"provider":"google"}');
    expect(init.signal).toBeDefined();
  });
});

describe('isDeadlineError / SOCIAL_LOGIN_TIMEOUT_MS', () => {
  it('recognises only the deadline shape', () => {
    expect(isDeadlineError({ code: DEADLINE_ERROR_CODE })).toBe(true);
    expect(isDeadlineError(new Error('boom'))).toBe(false);
    expect(isDeadlineError(null)).toBe(false);
    expect(isDeadlineError(undefined)).toBe(false);
  });

  it('keeps the social-login budget generous enough for a slow GCC connection', () => {
    // An over-tight deadline converts a sign-in that WOULD have succeeded
    // into a spurious retry; an absent one is the defect A8 filed.
    expect(SOCIAL_LOGIN_TIMEOUT_MS).toBeGreaterThanOrEqual(20000);
    expect(SOCIAL_LOGIN_TIMEOUT_MS).toBeLessThanOrEqual(45000);
  });
});
