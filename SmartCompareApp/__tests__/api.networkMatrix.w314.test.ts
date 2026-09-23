/**
 * W3-14 R4 — a 429 on a load path is a WAIT, not "No comparison loaded".
 *
 * `classifyLoadFailure` (src/services/failureClassification.ts) had no 429
 * branch, so a rate-limited history-detail fetch (`GET /api/v1/comparisons/{id}`
 * is 20/minute) or camera load fell to row 8 -> 'generic' -> ResultsScreen's
 * permanent "No comparison loaded" state with NO retry. Measured at b63a8368:
 * classifyLoadFailure(429 RATE_LIMITED) = 'generic'; (429, data {}) = 'generic'.
 *
 * Fix contract (spec §4): a 429 maps to the existing soft retryable
 * 'timeout' state (results.timeout.* + tap-to-retry) — inserted AFTER the
 * USAGE_LIMIT check so a metering 429 keeps routing to the Paywall.
 *
 * The module has zero imports, so it is exercised directly with no mocks.
 * Rows 400/422 -> generic duplicate api.networkMatrix.m18.test.ts:240-246 on
 * purpose: they are the "a 4xx that is NOT a 429 is unchanged" half of this
 * unit's contract and must live next to the new rows.
 */
import { classifyLoadFailure } from '../src/services/failureClassification';

describe('W3-14 R4 — 429 lands on the retryable timeout state', () => {
  it('429 RATE_LIMITED (slowapi envelope) -> timeout', () => {
    expect(
      classifyLoadFailure({
        response: {
          status: 429,
          data: {
            success: false,
            error: 'Rate limit exceeded. Please try again later.',
            code: 'RATE_LIMITED',
            retry_after_seconds: 61,
          },
        },
      }),
    ).toBe('timeout');
  });

  it('429 with data {} (codeless) -> timeout', () => {
    expect(classifyLoadFailure({ response: { status: 429, data: {} } })).toBe('timeout');
  });

  it('429 with the legacy detail.code RATE_LIMITED shape -> timeout', () => {
    expect(
      classifyLoadFailure({ response: { status: 429, data: { detail: { code: 'RATE_LIMITED' } } } }),
    ).toBe('timeout');
  });
});

describe('W3-14 R4 — preserve: ordering and the non-429 4xx rows', () => {
  it('429 USAGE_LIMIT (axios data.code) keeps usage_limit — the 429 line sits BELOW it', () => {
    expect(classifyLoadFailure({ response: { status: 429, data: { code: 'USAGE_LIMIT' } } })).toBe(
      'usage_limit',
    );
  });

  it('429 USAGE_LIMIT (legacy detail.code) keeps usage_limit', () => {
    expect(
      classifyLoadFailure({ response: { status: 429, data: { detail: { code: 'USAGE_LIMIT' } } } }),
    ).toBe('usage_limit');
  });

  it('USAGE_LIMIT tagged camera raw-fetch error (top-level err.code) keeps usage_limit', () => {
    const err = Object.assign(new Error('Usage limit reached'), {
      code: 'USAGE_LIMIT',
      detail: { code: 'USAGE_LIMIT' },
      response: { status: 429, data: { code: 'USAGE_LIMIT' } },
    });
    expect(classifyLoadFailure(err)).toBe('usage_limit');
  });

  it('plain 400 / 422 -> generic (unchanged)', () => {
    expect(classifyLoadFailure({ response: { status: 400, data: { error: 'bad' } } })).toBe(
      'generic',
    );
    expect(classifyLoadFailure({ response: { status: 422, data: {} } })).toBe('generic');
  });

  it('404 -> not_found and 401 -> auth (unchanged)', () => {
    expect(classifyLoadFailure({ response: { status: 404, data: {} } })).toBe('not_found');
    expect(classifyLoadFailure({ response: { status: 401, data: {} } })).toBe('auth');
  });
});
