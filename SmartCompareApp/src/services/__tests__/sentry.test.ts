/**
 * Tests for Sentry PII scrubbing.
 *
 * Mirrors the patterns in `app/services/sentry_service.py` so the mobile
 * SDK redacts the same secrets (JWTs, OpenAI / Firecrawl keys, generic
 * long-hex tokens, Bearer headers) before events leave the device.
 */

// Mock the native module so importing `sentry.ts` does not blow up under
// the node Jest environment (no native bridge). We only care about the
// pure JS scrubbing helpers here, not the SDK init side-effect.
jest.mock('@sentry/react-native', () => ({
  init: jest.fn(),
  wrap: <T,>(c: T): T => c,
}));

import { scrubString, scrubBeforeSend } from '../sentry';

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

  it('scrubs breadcrumb messages', () => {
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
