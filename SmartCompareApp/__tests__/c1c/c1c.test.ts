/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1c RED -- only http and https picture addresses are read for the image
 * breadcrumb's host (relay rulings ORCH-C1B-E and ORCH-C1C-A): any other kind
 * of address sends the fixed word 'unknown', so no other kind's parsing rules
 * can turn a piece of the address into a "host". Rows X7, X8 fail at main
 * 3046c652 (INC-C1b merged); pin P-X10 passes there and after the fix.
 *
 * Harness: as the c1b fix files (a recorder for @sentry/react-native,
 * services/sentry loaded fresh per call with jest.isolateModules). Synthetic
 * addresses only.
 */

const mockAddBreadcrumb = jest.fn();

jest.mock('@sentry/react-native', () => {
  const noop = () => undefined;
  const scope = {
    setTag: noop,
    setTags: noop,
    setContext: noop,
    setExtra: noop,
    setUser: noop,
    clear: noop,
  };
  const surface: Record<string, unknown> = {
    setTag: noop,
    setTags: noop,
    setContext: noop,
    setExtra: noop,
    setUser: noop,
    captureMessage: noop,
    captureException: noop,
    captureEvent: noop,
    addBreadcrumb: (...args: unknown[]) => mockAddBreadcrumb(...args),
    addIntegration: noop,
    init: noop,
    getCurrentScope: () => scope,
    withScope: (cb: (s: unknown) => void) => cb(scope),
    startSpan: (_opts: unknown, cb: (span: unknown) => unknown) => cb({ end: noop }),
    startInactiveSpan: () => ({ end: noop }),
    startSpanManual: (_opts: unknown, cb: (span: unknown) => unknown) => cb({ end: noop }),
    getClient: () => null,
    lastEventId: () => null,
  };
  return { __esModule: true, ...surface, default: surface };
});

/** One breadcrumb attempt for `url` on a fresh services/sentry module. */
function crumbFor(url: string): { calls: number; host: unknown; wire: string } {
  mockAddBreadcrumb.mockClear();
  jest.isolateModules(() => {
    const sentry = require('../../src/services/sentry') as {
      addImageLoadBreadcrumb: (u: string) => void;
    };
    sentry.addImageLoadBreadcrumb(url);
  });
  const calls = mockAddBreadcrumb.mock.calls;
  return {
    calls: calls.length,
    host: calls[0]?.[0]?.data?.host,
    wire: JSON.stringify(calls),
  };
}

const leaksOf = (wire: string, parts: string[]) => parts.filter((p) => wire.includes(p));

describe('INC-C1c rows (fail at main 3046c652)', () => {
  it('X7 a file: url with a drive letter: the fixed word, not the letter', () => {
    const r = crumbFor('file://Q:/Users/p.jpg');
    expect({ calls: r.calls, host: r.host, leaks: leaksOf(r.wire, ['"q"', 'Q:', 'Users']) }).toEqual({
      calls: 1,
      host: 'unknown',
      leaks: [],
    });
  });

  it('X8 a scheme other than http or https is not read: the fixed word', () => {
    const r = crumbFor('foo://img8.example.com/p.jpg');
    expect({ calls: r.calls, host: r.host, leaks: leaksOf(r.wire, ['img8']) }).toEqual({
      calls: 1,
      host: 'unknown',
      leaks: [],
    });
  });
});

describe('INC-C1c pin (passes at main 3046c652 and after)', () => {
  it('P-X10 http and https in any case are still read', () => {
    const a = crumbFor('HTTP://IMG9.example.com/x.png');
    const b = crumbFor('Https://img10.example.com/y.png');
    expect({ a: a.host, b: b.host }).toEqual({ a: 'img9.example.com', b: 'img10.example.com' });
  });
});
