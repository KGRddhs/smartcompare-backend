/**
 * A11 — failed comparison copy is chosen by CODE, never by the axios string.
 *
 * Finding (mobile checkup 2026-09-02, key `A11-raw-axios-error-copy`):
 * the text-compare path rendered `error.message` where the URL path
 * rendered `parsed.message`. M21 W2 hardened only the CODED arm of the
 * text path, which left two residuals:
 *   1. the CODELESS arm of the text path still rendered `error.message`,
 *      and the URL path rendered `parsed.message` UNCONDITIONALLY — and
 *      `parseApiError` falls through to `error?.message` whenever the
 *      response is not our envelope, so both leaked the raw axios string
 *      "Request failed with status code N" (forbidden token "failed");
 *   2. the backend's structured code was still discarded — `grep -rn
 *      INSUFFICIENT_DATA SmartCompareApp/src/` returned ZERO hits, so
 *      `text_routes._surface_comparison_failure`'s explicit "keep the code
 *      so the FE can branch" contract had no consumer, and a RATE_LIMITED
 *      user was told to retype ("try with brand or model") instead of wait.
 *
 * This file pins the WHOLE chain with no stub in it: a real axios-shaped
 * error -> the real `parseApiError` -> the real `friendlyErrorKey` -> the
 * real en.json / ar.json catalogs. Nothing here asserts on a mock.
 *
 * Harness mirrors api.networkMatrix.m18.test.ts — the precedent for
 * exercising src/services/api.ts without the network surface.
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
import { friendlyErrorKey } from '../src/services/errorCopy';
import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';

const EN = en as Record<string, string>;
const AR = ar as Record<string, string>;

/**
 * An axios rejection exactly as the interceptor hands it to the screens:
 * `.message` is axios's own generated string, `.response.data` is whatever
 * the server sent (or undefined when there was no parseable body).
 */
function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data };
  return err;
}

describe('A11 — INSUFFICIENT_DATA 400 never surfaces the raw axios string', () => {
  // The exact envelope `error_handler.http_exception_handler` builds from
  // `_surface_comparison_failure`'s `HTTPException(400, {"code":
  // "INSUFFICIENT_DATA", "error": ...})`.
  const insufficient = axiosError(400, {
    success: false,
    error: 'Not enough product data to compare',
    code: 'INSUFFICIENT_DATA',
    request_id: 'req-1',
  });

  it('parseApiError keeps the backend code (precondition for the branch)', () => {
    expect(parseApiError(insufficient).code).toBe('INSUFFICIENT_DATA');
  });

  it('resolves to the dedicated insufficient-data key, not the generic one', () => {
    const key = friendlyErrorKey(parseApiError(insufficient).code);
    expect(key).toBe('home.errors.insufficientData');
    expect(key).not.toBe('home.errors.comparison');
  });

  it('the rendered EN + AR copy is real catalog copy, never the axios string', () => {
    const key = friendlyErrorKey(parseApiError(insufficient).code);
    expect(EN[key]).toBeDefined();
    expect(AR[key]).toBeDefined();
    // The defect's exact symptom.
    expect(EN[key]).not.toMatch(/Request failed with status code/);
    expect(EN[key]).not.toBe(insufficient.message);
    // ...and not the backend's English sentence either (an AR user would
    // otherwise read English).
    expect(EN[key]).not.toBe('Not enough product data to compare');
    expect(AR[key]).not.toBe('Not enough product data to compare');
    // The two languages must be genuinely different strings, i.e. the AR
    // row is a translation and not an EN copy-paste.
    expect(AR[key]).not.toBe(EN[key]);
  });
});

describe('A11 — the codeless residual (no envelope) also gets catalog copy', () => {
  // Railway edge 502 with an HTML body: `data.error` / `data.detail` are
  // undefined on a string body, so parseApiError falls through to
  // `error.message` and `code` is null. This is the class that survived
  // M21 W2 on the text path and had NO guard at all on the URL path.
  const edge502 = axiosError(502, '<html><body>Bad gateway</body></html>');

  it('parseApiError DOES fall through to the raw axios string (the leak source)', () => {
    const parsed = parseApiError(edge502);
    expect(parsed.code).toBeNull();
    // Documents precisely why `.message` must never be rendered.
    expect(parsed.message).toBe('Request failed with status code 502');
  });

  it('a null code still resolves to catalog copy — no branch renders the string', () => {
    const key = friendlyErrorKey(parseApiError(edge502).code);
    expect(key).toBe('home.errors.comparison');
    expect(EN[key]).toBeDefined();
    expect(EN[key]).not.toBe('Request failed with status code 502');
  });

  it('is total: undefined, null, and unrecognized codes all map to a real key', () => {
    for (const code of [undefined, null, '', 'SERVER_ERROR', 'CONTENT_UNAVAILABLE', 'WAT']) {
      const key = friendlyErrorKey(code as any);
      expect(EN[key]).toBeDefined();
      expect(AR[key]).toBeDefined();
    }
  });
});

describe('A11 — RATE_LIMITED gets wait guidance, not retype guidance', () => {
  const limited = axiosError(429, {
    success: false,
    error: 'Rate limit exceeded: 10 per 1 minute',
    code: 'RATE_LIMITED',
    request_id: 'req-2',
  });

  it('maps to its own key, distinct from the generic compare nudge', () => {
    const key = friendlyErrorKey(parseApiError(limited).code);
    expect(key).toBe('home.errors.rateLimited');
    // The generic copy tells the user to retype ("try with brand or
    // model"), which is wrong when the only fix is to wait.
    expect(EN[key]).not.toBe(EN['home.errors.comparison']);
  });

  it('never surfaces the limiter internals', () => {
    const key = friendlyErrorKey(parseApiError(limited).code);
    expect(EN[key]).not.toMatch(/per 1 minute/);
    expect(EN[key]).not.toMatch(/Rate limit/i);
  });
});

describe('A11 — TIMEOUT keeps its existing soft copy', () => {
  it('both timeout codes resolve to the established key (no regression)', () => {
    expect(friendlyErrorKey('TIMEOUT')).toBe('home.errors.timeout');
    expect(friendlyErrorKey('STREAM_TIMEOUT')).toBe('home.errors.timeout');
  });

  it('a 503 with no code normalizes to TIMEOUT and keeps that copy', () => {
    const parsed = parseApiError(axiosError(503, { success: false, error: 'x' }));
    expect(parsed.code).toBe('TIMEOUT');
    expect(friendlyErrorKey(parsed.code)).toBe('home.errors.timeout');
  });
});

describe('A11 — every key this map can emit obeys the copy contract', () => {
  // Build Principle #4 / src/i18n/.copy-policy.json `scary_vocab_*`. The
  // raw axios string violated the EN list on the word "failed"; the whole
  // point of routing through the catalog is that it cannot.
  const SCARY_EN = [/couldn't/i, /try again/i, /failed/i, /failure/i, /error occurred/i];
  const SCARY_AR = ['تعذر', 'فشل'];

  const emittable = [
    friendlyErrorKey('INSUFFICIENT_DATA'),
    friendlyErrorKey('RATE_LIMITED'),
    friendlyErrorKey('TIMEOUT'),
    friendlyErrorKey(null),
  ];

  it.each(emittable)('%s is clean in EN and AR', (key) => {
    for (const pattern of SCARY_EN) expect(EN[key]).not.toMatch(pattern);
    for (const word of SCARY_AR) expect(AR[key]).not.toContain(word);
  });

  it('emits 4 distinct keys (the map is not collapsed to one)', () => {
    expect(new Set(emittable).size).toBe(4);
  });
});
