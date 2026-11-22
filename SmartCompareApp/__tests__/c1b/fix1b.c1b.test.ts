/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1b FIX1b RED -- completes FIX1 (relay ruling ORCH-C1B-C on adversary
 * A-5; delta finding D-1): an authority that holds a backslash never sends a
 * piece of the url. WHATWG parsers end an http(s) authority at a backslash,
 * so the text after its last "@" may sit in the path; such a url gives the
 * fixed word 'unknown'. Rows X4, X5 fail at the FIX1 head; pin P-X4 passes
 * there and after. Ruling ORCH-C1B-D closes the class by construction: only a
 * strict host shape is sent (letters, digits, dots and hyphens, at most 253
 * characters with labels of at most 63). FIX1 already rejected a character
 * outside that shape (pin P-X5); the length bound is new (row X6), and pin
 * P-X6 keeps a 63-character label.
 *
 * Harness: as fix1.c1b (a recorder for @sentry/react-native, services/sentry
 * loaded fresh per call with jest.isolateModules). The backslash is built
 * from its char code, so this source holds none. Synthetic urls only.
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

const BS = String.fromCharCode(92);

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

describe('INC-C1b FIX1b rows (fail at the FIX1 head)', () => {
  it('X4 a backslash after the host and a retina file name: the fixed word, no path piece', () => {
    // Not 'product' or 'image': the breadcrumb message holds "product image".
    const r = crumbFor('https://cdn.example.com' + BS + 'images' + BS + 'product@2x.jpg');
    expect({ calls: r.calls, host: r.host, leaks: leaksOf(r.wire, ['2x', 'jpg', 'images']) }).toEqual({
      calls: 1,
      host: 'unknown',
      leaks: [],
    });
  });

  it('X5 a backslash before an "@" in the authority: the fixed word, neither name', () => {
    const r = crumbFor('https://evil.example' + BS + '@img43.example.com/p.jpg');
    expect({ calls: r.calls, host: r.host, leaks: leaksOf(r.wire, ['img43', 'evil']) }).toEqual({
      calls: 1,
      host: 'unknown',
      leaks: [],
    });
  });
});

describe('INC-C1b FIX1b length row (fails at the FIX1 head)', () => {
  it('X6 a host over the sane length (a 64-character label; more than 253 characters): the fixed word', () => {
    // Relay ruling ORCH-C1B-D: only a strict host shape is sent, by construction.
    const longLabel = crumbFor('https://' + 'a'.repeat(64) + '.example.com/p.jpg');
    const longHost = crumbFor('https://' + 'abcdefghij.'.repeat(25) + 'example.com/p.jpg');
    expect({
      label: longLabel.host,
      total: longHost.host,
      leaks: leaksOf(longLabel.wire + longHost.wire, ['aaaaaaaaaa', 'abcdefghij']),
    }).toEqual({ label: 'unknown', total: 'unknown', leaks: [] });
  });
});

describe('INC-C1b FIX1b pins (pass at the FIX1 head and after)', () => {
  it('P-X5 a character outside the shape (an underscore; a zero-width space): the fixed word', () => {
    const under = crumbFor('https://img_29.example.com/p.jpg');
    const zw = crumbFor('https://img' + String.fromCharCode(0x200b) + '30.example.com/p.jpg');
    expect({
      under: under.host,
      zw: zw.host,
      leaks: leaksOf(under.wire + zw.wire, ['img_29', '30.example']),
    }).toEqual({ under: 'unknown', zw: 'unknown', leaks: [] });
  });

  it('P-X6 a 63-character label is still a host and is sent (the bound is not too strict)', () => {
    const host = 'b'.repeat(63) + '.example.com';
    const r = crumbFor('https://' + host.toUpperCase() + '/p.jpg');
    expect(r.host).toBe(host);
  });
});

describe('INC-C1b FIX1b pin (passes at the FIX1 head and after)', () => {
  it('P-X4 "@" signs after the authority (path, query, fragment) do not move the host', () => {
    const r = crumbFor('https://img12.example.com/p/a@2x.jpg?u=x@y#z@w');
    expect({ host: r.host, leaks: leaksOf(r.wire, ['2x', 'jpg', 'x@y', 'z@w']) }).toEqual({
      host: 'img12.example.com',
      leaks: [],
    });
  });
});
