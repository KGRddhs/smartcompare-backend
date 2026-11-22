/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1b FIX1 RED -- the image breadcrumb never carries a piece of a url
 * that is not a parsed host (relay ruling ORCH-C1B-C on adversary finding
 * A-5; rows X1-X3 fail at the GREEN head, pins P-X1..P-X3 pass there and
 * after the fix).
 *
 * The contract this file fixes: addImageLoadBreadcrumb(url) sends
 * data.host = the url's parsed host name (the authority after its last "@",
 * without the port, lower case, letters, digits, dots and hyphens only), else
 * the fixed word 'unknown'. A malformed url with user info and no host, an
 * IPv6 literal, or a uri without "//" gives 'unknown', never the user name,
 * the password or any other part of the url.
 *
 * Harness: @sentry/react-native mocked with a recorder (the productImage.c1b
 * surface); services/sentry real, loaded fresh for each call with
 * jest.isolateModules, so the once-per-host de-dup of one row never hides the
 * next row's call. Synthetic urls only.
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

describe('INC-C1b FIX1 rows (fail at the GREEN head)', () => {
  it('X1 user info and no host ("zorro:secret@"): the fixed word, no user name, no password', () => {
    const r = crumbFor('https://zorro:secret@');
    expect({ calls: r.calls, host: r.host, leaks: leaksOf(r.wire, ['zorro', 'secret']) }).toEqual({
      calls: 1,
      host: 'unknown',
      leaks: [],
    });
  });

  it('X2 a user name and "@" with no host ("zorro@"): the fixed word', () => {
    const r = crumbFor('https://zorro@');
    expect({ calls: r.calls, host: r.host, leaks: leaksOf(r.wire, ['zorro']) }).toEqual({
      calls: 1,
      host: 'unknown',
      leaks: [],
    });
  });

  it('X3 an IPv6 literal is not a parsed host name: the fixed word', () => {
    const r = crumbFor('https://[2001:db8::1]/p.jpg');
    expect({ calls: r.calls, host: r.host, leaks: leaksOf(r.wire, ['2001', 'db8']) }).toEqual({
      calls: 1,
      host: 'unknown',
      leaks: [],
    });
  });
});

describe('INC-C1b FIX1 pins (pass at the GREEN head and after the fix)', () => {
  it('P-X1 several "@" before the host: the host after the last "@", no user part', () => {
    const r = crumbFor('https://a@b@img11.example.com/p.jpg');
    expect({ host: r.host, leaks: leaksOf(r.wire, ['a@', 'b@']) }).toEqual({
      host: 'img11.example.com',
      leaks: [],
    });
  });

  it('P-X2 user info, a port and upper case: the lower-case host only', () => {
    const r = crumbFor('HTTPS://u:secret@IMG7.Example.COM:8443/p/a.jpg?sig=x');
    expect({ host: r.host, leaks: leaksOf(r.wire, ['secret', 'u:', '8443', 'sig=', '/p/']) }).toEqual({
      host: 'img7.example.com',
      leaks: [],
    });
  });

  it('P-X3 no "//" (a data: uri) and an empty host with a port: the fixed word', () => {
    const a = crumbFor('data:image/png;base64,AAAA');
    const b = crumbFor('https://:8443/p.jpg');
    expect({ a: a.host, b: b.host, leaks: leaksOf(a.wire + b.wire, ['8443', 'AAAA', 'base64']) }).toEqual({
      a: 'unknown',
      b: 'unknown',
      leaks: [],
    });
  });
});
