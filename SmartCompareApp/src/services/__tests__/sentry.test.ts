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
    expect(out.exception.values[0].value).toBe('Auth failed with token [JWT_REDACTED]');
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
