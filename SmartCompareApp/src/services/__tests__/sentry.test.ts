/**
 * Tests for Sentry PII scrubbing.
 *
 * Mirrors the patterns in `app/services/sentry_service.py` so the mobile
 * SDK redacts the same secrets (JWTs, OpenAI / Firecrawl keys, generic
 * long-hex tokens, Bearer headers) before events leave the device.
 *
 * M18 MB-security-01: the JS SDK (@sentry/core >= 8) types
 * `event.breadcrumbs` as a plain `Breadcrumb[]` — NOT the Python SDK's
 * `{values: [...]}` wrapper. The fixtures below pin the REAL array shape
 * so the breadcrumb scrub is exercised the way production events actually
 * arrive; the legacy dict shape is kept only as a tolerance case.
 *
 * M18 MB-security-02: R21 parity — user-typed query-string params
 * (q/query/email/search/text) are redacted like the backend's
 * _QUERY_STRING_SCRUB_PATTERN, and beforeBreadcrumb /
 * beforeSendTransaction hooks scrub URLs on breadcrumbs and http spans.
 */

jest.mock('@sentry/react-native', () => ({
  init: jest.fn(),
  wrap: <T,>(c: T): T => c,
  addBreadcrumb: jest.fn(),
}));

import * as Sentry from '@sentry/react-native';
import {
  scrubString,
  scrubBeforeSend,
  scrubBeforeBreadcrumb,
  scrubBeforeSendTransaction,
  initSentry,
} from '../sentry';

describe('scrubString', () => {
  it('redacts JWT tokens', () => {
    const jwt =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFobWVkIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
    const out = scrubString(`token=${jwt}`);
    expect(out).toBe('token=[JWT_REDACTED]');
  });

  it('redacts OpenAI project keys', () => {
    const key = 'sk-proj-abc123XYZ_test-DEF456';
    const out = scrubString(`OPENAI_KEY=${key}`);
    expect(out).toBe('OPENAI_KEY=[OPENAI_KEY_REDACTED]');
  });

  it('redacts Firecrawl API keys', () => {
    const key = 'fc-' + 'a'.repeat(32);
    const out = scrubString(`FIRECRAWL_KEY=${key}`);
    expect(out).toBe('FIRECRAWL_KEY=[FIRECRAWL_KEY_REDACTED]');
  });

  it('redacts generic long hex tokens (>=40 chars)', () => {
    const hex = 'a'.repeat(40);
    const out = scrubString(`token=${hex}`);
    expect(out).toBe('token=[TOKEN_REDACTED]');
  });

  it('redacts Bearer authorization headers', () => {
    const out = scrubString('Bearer abc.def-ghi_jkl123');
    expect(out).toBe('Bearer [REDACTED]');
  });

  it('passes clean strings through unchanged', () => {
    const clean = 'Hello world, this is a regular log message with no secrets.';
    expect(scrubString(clean)).toBe(clean);
  });

  // M18 MB-security-02 — R21 query-string parity with the backend's
  // _QUERY_STRING_PII_PARAMS ('q','query','email','search','text').
  describe('query-string PII params (R21 parity)', () => {
    it('redacts the user-typed compare query in an SSE URL', () => {
      const url =
        'https://web-production-58776.up.railway.app/api/v1/text/compare/stream?q=iPhone+15+vs+Galaxy+S24&nocache=true';
      expect(scrubString(url)).toBe(
        'https://web-production-58776.up.railway.app/api/v1/text/compare/stream?q=[QUERY_REDACTED]&nocache=true',
      );
    });

    it('redacts every listed param name, case-insensitively', () => {
      const url =
        'https://x.test/a?query=secret+wish&Email=me%40example.com&search=embarrassing&text=hello+world';
      expect(scrubString(url)).toBe(
        'https://x.test/a?query=[QUERY_REDACTED]&Email=[QUERY_REDACTED]&search=[QUERY_REDACTED]&text=[QUERY_REDACTED]',
      );
    });

    it('preserves bookkeeping params (nocache/limit/offset) untouched', () => {
      const url = 'https://x.test/a?nocache=true&limit=20&offset=40';
      expect(scrubString(url)).toBe(url);
    });

    it('does not match params that merely contain a listed name (fulltext/searchterm)', () => {
      const url = 'https://x.test/a?fulltext=keep&searchterm=keep';
      expect(scrubString(url)).toBe(url);
    });

    it('stops the redaction at a fragment boundary', () => {
      const url = 'https://x.test/a?q=secret#section';
      expect(scrubString(url)).toBe('https://x.test/a?q=[QUERY_REDACTED]#section');
    });
  });
});

describe('scrubBeforeSend', () => {
  it('scrubs exception values', () => {
    const jwt =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
    const event: any = {
      exception: {
        values: [
          { type: 'Error', value: `Auth failed with token ${jwt}` },
        ],
      },
    };
    const out = scrubBeforeSend(event, {});
    expect([out.exception.values[0].type, out.exception.values[0].value]).toEqual(['Error', '']);
  });

  // M18 MB-security-01 — THE shape production events actually have:
  // `breadcrumbs` is a plain array in the JS SDK. Before the fix the scrub
  // guarded on `Array.isArray(event.breadcrumbs.values)` (Python SDK shape)
  // and therefore never ran.
  it('scrubs breadcrumb messages on the REAL JS-SDK array shape', () => {
    const event: any = {
      breadcrumbs: [
        { message: 'Sending Bearer secret-token-abc to backend', data: {} },
      ],
    };
    const out = scrubBeforeSend(event, {});
    expect(out.breadcrumbs[0].message).toBe('Sending Bearer [REDACTED] to backend');
  });

  it('scrubs fetch-breadcrumb data.url query params on the array shape', () => {
    const event: any = {
      breadcrumbs: [
        {
          category: 'fetch',
          data: {
            url: 'https://api.test/api/v1/text/compare/stream?q=iPhone+15+vs+Galaxy',
            method: 'GET',
          },
        },
      ],
    };
    const out = scrubBeforeSend(event, {});
    expect(out.breadcrumbs[0].data.url).toBe(
      'https://api.test/api/v1/text/compare/stream?q=[QUERY_REDACTED]',
    );
    expect(out.breadcrumbs[0].data.method).toBe('GET');
  });

  // Legacy Python-SDK dict shape kept as a tolerance case only.
  it('still tolerates the legacy {values: [...]} dict shape', () => {
    const event: any = {
      breadcrumbs: {
        values: [
          { message: 'Sending Bearer secret-token-abc to backend', data: {} },
        ],
      },
    };
    const out = scrubBeforeSend(event, {});
    expect(out.breadcrumbs.values[0].message).toBe('Sending Bearer [REDACTED] to backend');
  });

  // M18 MB-security-02 — event.request.url carries the failing request's
  // full URL; the backend scrubs it (R21) and mobile must too.
  it('scrubs PII query params from event.request.url', () => {
    const event: any = {
      request: {
        url: 'https://api.test/api/v1/text/compare?q=private+thing&nocache=true',
      },
    };
    const out = scrubBeforeSend(event, {});
    expect(out.request.url).toBe(
      'https://api.test/api/v1/text/compare?q=[QUERY_REDACTED]&nocache=true',
    );
  });

  it('redacts sensitive headers, preserves non-sensitive ones', () => {
    const event: any = {
      request: {
        headers: {
          Authorization: 'Bearer some-token',
          'X-Admin-Key': 'admin-secret',
          Cookie: 'session=abc',
          'Content-Type': 'application/json',
          'X-Request-Id': 'req-12345',
        },
      },
    };
    const out = scrubBeforeSend(event, {});
    // Sensitive (case-insensitive match) redacted wholesale:
    expect(out.request.headers.Authorization).toBe('[REDACTED]');
    expect(out.request.headers['X-Admin-Key']).toBe('[REDACTED]');
    expect(out.request.headers.Cookie).toBe('[REDACTED]');
    // Non-sensitive preserved:
    expect(out.request.headers['Content-Type']).toBe('application/json');
    expect(out.request.headers['X-Request-Id']).toBe('req-12345');
  });
});

// M18 MB-security-02 — beforeBreadcrumb parity with the backend's
// _strip_tokens_from_breadcrumb: scrub at breadcrumb-creation time so the
// URL never sits unscrubbed in the ring buffer.
describe('scrubBeforeBreadcrumb', () => {
  it('scrubs data.url query params and tokens', () => {
    const crumb: any = {
      category: 'fetch',
      data: {
        url: 'https://api.test/stream?q=my+secret+search&nocache=true',
        method: 'GET',
        status_code: 200,
      },
    };
    const out = scrubBeforeBreadcrumb(crumb, {});
    expect(out.data.url).toBe('https://api.test/stream?q=[QUERY_REDACTED]&nocache=true');
    expect(out.data.status_code).toBe(200);
  });

  it('scrubs the breadcrumb message', () => {
    const out = scrubBeforeBreadcrumb({ message: 'auth Bearer abc.def123' }, {});
    expect(out.message).toBe('auth Bearer [REDACTED]');
  });

  it('passes a breadcrumb with no message/data through unchanged', () => {
    const crumb: any = { category: 'ui.click' };
    expect(scrubBeforeBreadcrumb(crumb, {})).toBe(crumb);
  });
});

// M18 MB-security-02 — tracesSampleRate is 0.1, so http spans ship with
// the same URLs; beforeSendTransaction applies the same scrub.
describe('scrubBeforeSendTransaction', () => {
  it('scrubs request.url, span descriptions and span data', () => {
    const event: any = {
      type: 'transaction',
      transaction: 'GET /api/v1/text/compare?q=secret',
      request: { url: 'https://api.test/compare?q=secret+stuff' },
      spans: [
        {
          op: 'http.client',
          description: 'GET https://api.test/stream?q=user+typed+this',
          data: { url: 'https://api.test/stream?q=user+typed+this' },
        },
      ],
    };
    const out = scrubBeforeSendTransaction(event, {});
    expect(out.transaction).toBe('GET /api/v1/text/compare?q=[QUERY_REDACTED]');
    expect(out.request.url).toBe('https://api.test/compare?q=[QUERY_REDACTED]');
    expect(out.spans[0].description).toBe(
      'GET https://api.test/stream?q=[QUERY_REDACTED]',
    );
    expect(out.spans[0].data.url).toBe('https://api.test/stream?q=[QUERY_REDACTED]');
  });

  it('scrubs contexts.trace.data (root span attributes)', () => {
    const event: any = {
      type: 'transaction',
      contexts: {
        trace: { data: { url: 'https://api.test/a?email=me%40example.com' } },
      },
    };
    const out = scrubBeforeSendTransaction(event, {});
    expect(out.contexts.trace.data.url).toBe('https://api.test/a?email=[QUERY_REDACTED]');
  });
});

describe('initSentry hook registration', () => {
  it('registers beforeSend, beforeBreadcrumb AND beforeSendTransaction', () => {
    (Sentry.init as jest.Mock).mockClear();
    initSentry('https://public@example.ingest.sentry.io/1');
    expect(Sentry.init).toHaveBeenCalledTimes(1);
    const opts = (Sentry.init as jest.Mock).mock.calls[0][0];
    expect(opts.beforeSend).toBe(scrubBeforeSend);
    expect(opts.beforeBreadcrumb).toBe(scrubBeforeBreadcrumb);
    expect(opts.beforeSendTransaction).toBe(scrubBeforeSendTransaction);
    expect(opts.sendDefaultPii).toBe(false);
  });
});

// S74 CLIENT-TRUTH (ruling UP1, FABLE_RULINGS_CLIENT_TRUTH.md CT9/CT11/CT12) -
// client parity with app/services/sentry_service.py: the query rung carries
// the backend's ten _QUERY_STRING_PII_PARAMS names in order (the client REST
// compare sends product_a / product_b as query params, api.ts:692-705), and
// scrubBeforeSend blanks every exception value except three axios-generated
// shapes matched whole, and scrubs event.message and the string values of
// event.extra (the B4-DIAG captureMessage sites, authService.ts:878/960/985/997).
// Every sentinel is built at runtime; no credential-shaped literal.
const ctFs: typeof import('fs') = jest.requireActual('fs');
const ctPath: typeof import('path') = jest.requireActual('path');
const ctEmail = () => 'shopper' + '@' + 'example.test';
const ctBearer = () => 'Bear' + 'er ' + 'abc' + '.def123';

describe('S74 CLIENT-TRUTH query rung parity (UP1)', () => {
  it('CT-Y1: product_a / product_b compare params are redacted; nocache is kept', () => {
    const url =
      'https://x.test/api/v1/text/compare?product_a=iPhone%2015&product_b=Galaxy%20S24&nocache=true';
    expect(scrubString(url)).toBe(
      'https://x.test/api/v1/text/compare?product_a=[QUERY_REDACTED]&product_b=[QUERY_REDACTED]&nocache=true',
    );
  });

  it('CT-Y2: url / url1 / url2 params are redacted', () => {
    const url =
      'https://x.test/api/v1/url/compare?url=https%3A%2F%2Fshop.test%2Fp%2F1&url1=https%3A%2F%2Fa.test%2Fx&url2=https%3A%2F%2Fb.test%2Fy';
    expect(scrubString(url)).toBe(
      'https://x.test/api/v1/url/compare?url=[QUERY_REDACTED]&url1=[QUERY_REDACTED]&url2=[QUERY_REDACTED]',
    );
  });

  it('CT-Y2 GUARD: params that merely start with a listed name stay untouched (urls / product_a_id)', () => {
    const url = 'https://x.test/a?urls=keep&product_a_id=keep';
    expect(scrubString(url)).toBe(url);
  });

  it('CT-Y3: the rung names (U8 parser regex over sentry.ts) equal the backend _QUERY_STRING_PII_PARAMS tuple, in order', () => {
    const src = ctFs.readFileSync(ctPath.resolve(__dirname, '../sentry.ts'), 'utf8');
    const rung = src.match(/\[\?&\]\(\?:([A-Za-z0-9_|]+)\)/);
    const py = ctFs.readFileSync(
      ctPath.resolve(__dirname, '../../../../app/services/sentry_service.py'),
      'utf8',
    );
    const tuple = py.match(/_QUERY_STRING_PII_PARAMS\s*=\s*\(([^)]*)\)/);
    expect(rung).not.toBeNull();
    expect(tuple).not.toBeNull();
    const backend = Array.from((tuple as RegExpMatchArray)[1].matchAll(/"([^"]+)"/g)).map((m) => m[1]);
    expect(backend.length).toBeGreaterThanOrEqual(10);
    expect((rung as RegExpMatchArray)[1].split('|')).toEqual(backend);
  });

  it('CT-Y5: beforeBreadcrumb redacts product_a / product_b on an XHR crumb data.url', () => {
    const crumb: any = {
      category: 'xhr',
      data: {
        url: 'https://x.test/api/v1/text/compare?product_a=Vitamin%20D3&product_b=Omega%203',
        method: 'GET',
        status_code: 200,
      },
    };
    const out = scrubBeforeBreadcrumb(crumb, {});
    expect(out.data.url).toBe(
      'https://x.test/api/v1/text/compare?product_a=[QUERY_REDACTED]&product_b=[QUERY_REDACTED]',
    );
    expect(out.data.method).toBe('GET');
    expect(out.data.status_code).toBe(200);
  });
});

describe('S74 CLIENT-TRUTH scrubBeforeSend exception values, message and extra (UP1 R1, CT11, CT12)', () => {
  const frames = () => [
    { filename: 'app:///index.android.bundle', function: 'compare', lineno: 1, colno: 2345 },
  ];

  it('CT-Y4: every non-allowlisted exception value is blanked; type, mechanism and stacktrace are kept; the breadcrumb scrub is unchanged', () => {
    const event: any = {
      exception: {
        values: [
          {
            type: 'Error',
            value: 'Compare failed for ' + ctEmail() + ' query iPhone 15 vs Galaxy S24',
            mechanism: { type: 'onunhandledrejection', handled: false },
            stacktrace: { frames: frames() },
          },
          { type: 'TypeError', value: "undefined is not an object (evaluating 'r.price.amount')" },
        ],
      },
      breadcrumbs: [{ message: 'Sending ' + ctBearer() + ' to backend', data: {} }],
    };
    const out = scrubBeforeSend(event, {});
    expect(out.exception.values.map((v: any) => v.value)).toEqual(['', '']);
    expect(out.exception.values.map((v: any) => v.type)).toEqual(['Error', 'TypeError']);
    expect(out.exception.values[0].mechanism).toEqual({ type: 'onunhandledrejection', handled: false });
    expect(out.exception.values[0].stacktrace).toEqual({ frames: frames() });
    expect(out.breadcrumbs[0].message).toBe('Sending Bearer [REDACTED] to backend');
  });

  it('CT11 GUARD: the three axios-generated shapes are kept verbatim', () => {
    const kept = ['Request failed with status code 500', 'Network Error', 'timeout of 15000ms exceeded'];
    const event: any = {
      exception: { values: kept.map((value) => ({ type: 'AxiosError', value })) },
    };
    const out = scrubBeforeSend(event, {});
    expect(out.exception.values.map((v: any) => v.value)).toEqual(kept);
  });

  it('CT11: a PII-bearing value and the near-misses of the allowlist are blanked (matched whole)', () => {
    const values = [
      'Lookup failed for ' + ctEmail(),
      'Network Error: ' + 'x',
      'Request failed with status code ' + '5000',
      'Request failed with status code 500 for ' + ctEmail(),
      'timeout of ms exceeded',
      'timeout of 15000ms exceeded at https://x.test/a?q=' + 'private+wish',
    ];
    const event: any = {
      exception: { values: values.map((value) => ({ type: 'Error', value })) },
    };
    const out = scrubBeforeSend(event, {});
    expect(out.exception.values.map((v: any) => v.value)).toEqual(values.map(() => ''));
  });

  it('CT12: event.message and every string value of event.extra get the scrub patterns; non-strings are untouched', () => {
    const event: any = {
      message:
        'b4_diag sign-in failed with ' +
        ctBearer() +
        ' at https://x.test/api/v1/text/compare?q=' +
        'private+wish',
      extra: {
        errMessage: 'Request failed for https://x.test/a?email=' + 'me%40example.test',
        server_error: 'upstream said ' + ctBearer(),
        attempt: 2,
        retried: true,
        note: null,
      },
    };
    const out = scrubBeforeSend(event, {});
    expect(out.message).toBe(
      'b4_diag sign-in failed with Bearer [REDACTED] at https://x.test/api/v1/text/compare?q=[QUERY_REDACTED]',
    );
    expect(out.extra.errMessage).toBe('Request failed for https://x.test/a?email=[QUERY_REDACTED]');
    expect(out.extra.server_error).toBe('upstream said Bearer [REDACTED]');
    expect(out.extra.attempt).toBe(2);
    expect(out.extra.retried).toBe(true);
    expect(out.extra.note).toBeNull();
  });
});

describe('S74 CLIENT-TRUTH allowlist near-misses (ruling G6: matched whole, case-sensitive, untrimmed)', () => {
  const blankedValues = (values: string[]) => {
    const event: any = {
      exception: { values: values.map((value) => ({ type: 'AxiosError', value })) },
    };
    return scrubBeforeSend(event, {}).exception.values.map((v: any) => v.value);
  };

  it('G6: a trailing-whitespace variant of an allowlisted shape is blanked', () => {
    const values = [
      'Network Error' + ' ',
      'Request failed with status code 500' + '\n',
      'timeout of 15000ms exceeded' + '\t',
    ];
    expect(blankedValues(values)).toEqual(values.map(() => ''));
  });

  it('G6: a case variant of an allowlisted shape is blanked', () => {
    const values = [
      'network error',
      'NETWORK ERROR',
      'request failed with status code 500',
      'Timeout of 15000ms exceeded',
    ];
    expect(blankedValues(values)).toEqual(values.map(() => ''));
  });
});

describe('S74 CLIENT-TRUTH allowlist prefix near-misses (ruling Y6: anchored at the start)', () => {
  it('Y6: an allowlisted shape with any text before it is blanked', () => {
    const values = [
      'x ' + 'Network Error',
      ctEmail() + ' ' + 'Request failed with status code ' + '500',
      'a ' + 'timeout of 1ms exceeded',
    ];
    const event: any = {
      exception: { values: values.map((value) => ({ type: 'AxiosError', value })) },
    };
    const out = scrubBeforeSend(event, {});
    expect(out.exception.values.map((v: any) => v.value)).toEqual(values.map(() => ''));
  });
});
