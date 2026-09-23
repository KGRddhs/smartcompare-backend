/**
 * W3-14 R1 — `parseApiError` surfaces the backend's `retry_after_seconds`.
 *
 * Findings MB-NETWORK-CONTRACT-05/-06. W1-9 (#152, `a4e7b08b`) made the
 * backend emit `retry_after_seconds` (plus a `Retry-After` header) at the TOP
 * level of the error envelope on BOTH 429 classes — the slowapi limiter
 * (`error_handler.py::rate_limit_handler` -> `_build_error_response`) and the
 * ACCOUNT_LOCKED lockout (`http_exception_handler`). The client dropped it on
 * the floor: measured at b63a8368, `Object.keys(parseApiError(slowapi429))`
 * = ['message', 'code'].
 *
 * Contract pinned here (spec §4 + FABLE rulings R-3 / R-5):
 *  - `retryAfterSeconds` is read from `data.retry_after_seconds` (TOP level)
 *    in BOTH envelope branches (`data.error` and `data.detail`);
 *  - it is present ONLY for a positive integer (mirrors the backend's
 *    `_detail_retry_after`: bool / float / <= 0 / string rejected);
 *  - when absent or rejected the KEY is absent — `toStrictEqual` plus an
 *    `in` check, because `toEqual` treats `{k: undefined}` as `{}` (R-3).
 *
 * Harness = errorCopy.a11.test.ts (real api.ts, network surface mocked).
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
  manipulateAsync: jest.fn().mockResolvedValue({ uri: 'file:///manipulated.jpg' }),
  SaveFormat: { JPEG: 'jpeg' },
}));

jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));

jest.mock('../src/services/sentry', () => ({
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: (s: string) => s,
  scrubBeforeSend: (e: any) => e,
}));

import { parseApiError } from '../src/services/api';

/** An axios rejection exactly as the interceptor hands it to a screen. */
function axiosError(status: number, data: any, headers: Record<string, string> = {}): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data, headers };
  return err;
}

// The exact wire shape main's error_handler emits since W1-9 for the slowapi 429.
const slowapi429 = (retry: unknown = 61) =>
  axiosError(
    429,
    {
      success: false,
      error: 'Rate limit exceeded. Please try again later.',
      code: 'RATE_LIMITED',
      request_id: 'r1',
      retry_after_seconds: retry,
    },
    { 'retry-after': String(retry) },
  );

// ... and for the ACCOUNT_LOCKED 429 (PUT /password lockout, 900 s).
const locked429 = () =>
  axiosError(
    429,
    {
      success: false,
      error: 'Too many failed attempts. Try again in 15 minutes.',
      code: 'ACCOUNT_LOCKED',
      request_id: 'r2',
      retry_after_seconds: 900,
    },
    { 'retry-after': '900' },
  );

describe('W3-14 R1 — parseApiError reads retry_after_seconds (positive int only)', () => {
  it('slowapi 429 (RATE_LIMITED, 61) -> retryAfterSeconds === 61', () => {
    const parsed: any = parseApiError(slowapi429(61));
    expect(parsed.code).toBe('RATE_LIMITED');
    expect(parsed.retryAfterSeconds).toBe(61);
  });

  it('ACCOUNT_LOCKED 429 (900) -> retryAfterSeconds === 900', () => {
    const parsed: any = parseApiError(locked429());
    expect(parsed.code).toBe('ACCOUNT_LOCKED');
    expect(parsed.retryAfterSeconds).toBe(900);
  });

  it('legacy data.detail shape with the TOP-level field -> read too (R-5)', () => {
    const parsed: any = parseApiError(
      axiosError(429, {
        detail: { code: 'RATE_LIMITED', error: 'slow down' },
        retry_after_seconds: 61,
      }),
    );
    expect(parsed.code).toBe('RATE_LIMITED');
    expect(parsed.retryAfterSeconds).toBe(61);
  });

  it('envelope WITHOUT the field -> exactly {message, code}; the key is ABSENT (R-3)', () => {
    const parsed = parseApiError(
      axiosError(429, {
        success: false,
        error: 'Rate limit exceeded. Please try again later.',
        code: 'RATE_LIMITED',
      }),
    );
    expect(parsed).toStrictEqual({
      message: 'Rate limit exceeded. Please try again later.',
      code: 'RATE_LIMITED',
    });
    expect('retryAfterSeconds' in parsed).toBe(false);
  });

  it('data.detail envelope WITHOUT the field -> key absent as well', () => {
    const parsed = parseApiError(axiosError(400, { detail: 'Current password is incorrect' }));
    expect(parsed).toStrictEqual({ message: 'Current password is incorrect', code: null });
    expect('retryAfterSeconds' in parsed).toBe(false);
  });

  // Mirror of error_handler._detail_retry_after's rejection set. `0` also
  // keeps i18next's English `_zero` sibling unreachable (FABLE ruling R-6).
  it.each([
    ['zero', 0],
    ['negative', -5],
    ['float', 61.5],
    ['numeric string', '61'],
    ['boolean true', true],
    ['null', null],
  ])('rejects %s (%p): key absent, object strictly {message, code}', (_label, value) => {
    const parsed = parseApiError(slowapi429(value));
    expect('retryAfterSeconds' in parsed).toBe(false);
    expect(parsed).toStrictEqual({
      message: 'Rate limit exceeded. Please try again later.',
      code: 'RATE_LIMITED',
    });
  });

  it('a positive integer is accepted beyond the 429 set (1 s is still a value)', () => {
    const parsed: any = parseApiError(slowapi429(1));
    expect(parsed.retryAfterSeconds).toBe(1);
  });
});

describe('W3-14 R1 — preserve: the non-envelope branches never carry the field', () => {
  it('503 -> TIMEOUT contract stays exactly {message:"", code:"TIMEOUT"}', () => {
    const parsed = parseApiError(
      axiosError(503, { success: false, error: 'slow', retry_after_seconds: 30 }),
    );
    expect(parsed).toStrictEqual({ message: '', code: 'TIMEOUT' });
  });

  it('transport failure (ERR_NETWORK, no response) -> TIMEOUT, no extra key', () => {
    const err: any = new Error('Network Error');
    err.code = 'ERR_NETWORK';
    expect(parseApiError(err)).toStrictEqual({ message: '', code: 'TIMEOUT' });
  });

  it('codeless edge 502 falls through to the axios string with code null (unchanged)', () => {
    const parsed = parseApiError(axiosError(502, '<html>Bad gateway</html>'));
    expect(parsed).toStrictEqual({ message: 'Request failed with status code 502', code: null });
  });
});
