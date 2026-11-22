/**
 * INC-C1b RED -- T7-09 one picture retry and a host-only breadcrumb
 * (INC_C1B_UNIT_SPEC_V2.md section 2 and 10.1: rows I1-I7, pin P-I1;
 * rulings RU-7, RU-8).
 *
 * The contract this file fixes for GREEN:
 *  - ProductImage: the first onError shows the placeholder at once (the
 *    state-4 contract of ProductImage.test.tsx stays) and arms ONE timer of
 *    1,500 ms; when it fires, a fresh Image mounts with the same uri (one
 *    retry). An onError on the retry is final: the placeholder stays for good
 *    and the breadcrumb runs. An onError while the retry timer is pending is
 *    ignored (one timer at most). A url change or an unmount clears a pending
 *    timer, and a url change resets the attempt, so a new url gets its own
 *    retry.
 *  - The breadcrumb leaves the app as Sentry.addBreadcrumb({ category:
 *    'image', level: 'warning', message: 'product image did not load after
 *    one retry', data: { host } }): host = the authority without user info
 *    or port, lower-cased, else 'unknown'; at most one per host per app
 *    session. Never the path, the query, the scheme, user info or the port.
 *
 * Harness: the ProductImage.test.tsx render pattern under fake timers;
 * @sentry/react-native (an existing path) is mocked per file with a lazy
 * addBreadcrumb recorder, and services/sentry stays real, so the breadcrumb
 * is observed where it leaves the app. F1: no new symbol is imported; a node
 * that is absent at base is read with queryBy* and fired only when present,
 * so every base failure is an expect assertion. The de-dup lives in module
 * state, so every row uses its own host. Synthetic urls only.
 */

import React from 'react';
import { View } from 'react-native';
import { act, fireEvent, render } from '@testing-library/react-native';

import { ProductImage } from '../../src/components/primitives/ProductImage';

const mockAddBreadcrumb = jest.fn();

// The global stub's surface (__mocks__/sentry-react-native.ts) with a lazy
// recorder: the factory runs when services/sentry first loads the package.
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

const RETRY_MS = 1500;
const CRUMB_MESSAGE = 'product image did not load after one retry';

type Rendered = ReturnType<typeof render>;

const advance = (ms: number) => {
  act(() => {
    jest.advanceTimersByTime(ms);
  });
};
const has = (r: Rendered, id: string) => r.queryByTestId(id) !== null;
/** The uri of the mounted Image, or null when the placeholder shows. */
const uriOf = (r: Rendered, id: string): string | null => {
  const n = r.queryByTestId(id);
  if (!n) return null;
  const source = n.props.source as { uri?: string } | undefined;
  return source?.uri ?? null;
};
/** One load error on the Image when it is mounted (at base a retry Image never mounts). */
const failIfMounted = (r: Rendered, id: string): boolean => {
  const n = r.queryByTestId(id);
  if (n) fireEvent(n, 'error');
  return n !== null;
};
/** Pending fake timers only: queued fake microtask jobs are run first so they never count. */
const pendingTimers = (): number => {
  jest.runAllTicks();
  return jest.getTimerCount();
};
const crumbs = (): any[] => mockAddBreadcrumb.mock.calls.map((call: any[]) => call[0]);
const hosts = (): unknown[] => crumbs().map((c: any) => c?.data?.host);
const wire = () => JSON.stringify(mockAddBreadcrumb.mock.calls);
const flatStyle = (style: unknown): Record<string, any> => {
  const arr = Array.isArray(style) ? style : [style];
  return Object.assign({}, ...arr.filter(Boolean));
};

beforeEach(() => {
  jest.useFakeTimers();
  // RU-8: jest.config.js sets no clearMocks, so the recorder is cleared here.
  mockAddBreadcrumb.mockClear();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('INC-C1b T7-09 rows (fail at base)', () => {
  it('I1 one error: the placeholder holds until 1,499 ms, then the same uri loads again at 1,500 ms', () => {
    const url = 'https://img1.example.com/p/a.jpg?sig=x';
    const r = render(<ProductImage testID="pi" imageUrl={url} />);
    fireEvent(r.getByTestId('pi-img'), 'error');
    advance(RETRY_MS - 1);
    // Passes at base: the placeholder shows at once and nothing retries early.
    expect({ img: has(r, 'pi-img'), placeholder: has(r, 'pi-placeholder') }).toEqual({
      img: false,
      placeholder: true,
    });
    advance(1);
    expect({ retryUri: uriOf(r, 'pi-img'), placeholder: has(r, 'pi-placeholder') }).toEqual({
      retryUri: url,
      placeholder: false,
    });
  });

  it('I2 an error on the retry is final: the placeholder stays and one breadcrumb carries the host only', () => {
    const url = 'https://img2.example.com/p/a.jpg?sig=x';
    const r = render(<ProductImage testID="pi" imageUrl={url} />);
    fireEvent(r.getByTestId('pi-img'), 'error');
    advance(RETRY_MS);
    expect({ retryUri: uriOf(r, 'pi-img') }).toEqual({ retryUri: url });
    failIfMounted(r, 'pi-img');
    advance(10000);
    expect({ img: has(r, 'pi-img'), placeholder: has(r, 'pi-placeholder') }).toEqual({
      img: false,
      placeholder: true,
    });
    expect(mockAddBreadcrumb).toHaveBeenCalledTimes(1);
    expect(crumbs()[0]).toEqual({
      category: 'image',
      level: 'warning',
      message: CRUMB_MESSAGE,
      data: { host: 'img2.example.com' },
    });
    expect(['/p/', 'sig=', '.jpg', 'https'].filter((s) => wire().includes(s))).toEqual([]);
  });

  it('I3 one error and a good retry: the Image stays and no breadcrumb is sent', () => {
    const url = 'https://img3.example.com/p/a.jpg?sig=x';
    const r = render(<ProductImage testID="pi" imageUrl={url} />);
    fireEvent(r.getByTestId('pi-img'), 'error');
    advance(RETRY_MS);
    expect({ retryUri: uriOf(r, 'pi-img') }).toEqual({ retryUri: url });
    advance(10000);
    expect({ retryUri: uriOf(r, 'pi-img'), crumbs: mockAddBreadcrumb.mock.calls.length }).toEqual({
      retryUri: url,
      crumbs: 0,
    });
  });

  it('I4 a url change clears the pending timer and resets the attempt: each new url gets its own retry', () => {
    // (a) A fails; B arrives before A's retry is due (A's timer must not fire later).
    const a = 'https://img4.example.com/p/a.jpg?sig=1';
    const b = 'https://img4.example.com/p/b.jpg?sig=2';
    const r = render(<ProductImage testID="pi" imageUrl={a} />);
    fireEvent(r.getByTestId('pi-img'), 'error');
    advance(500);
    r.rerender(<ProductImage testID="pi" imageUrl={b} />);
    // Passes at base: a new url loads at once.
    expect({ uri: uriOf(r, 'pi-img') }).toEqual({ uri: b });
    advance(RETRY_MS);
    expect({ count: r.queryAllByTestId('pi-img').length, uri: uriOf(r, 'pi-img') }).toEqual({
      count: 1,
      uri: b,
    });
    failIfMounted(r, 'pi-img');
    expect(has(r, 'pi-placeholder')).toBe(true);
    advance(RETRY_MS);
    expect({ bRetryUri: uriOf(r, 'pi-img') }).toEqual({ bRetryUri: b });
    // (b) B's retry is used; C arrives and fails once: C still gets its own retry.
    const c = 'https://img4.example.com/p/c.jpg?sig=3';
    r.rerender(<ProductImage testID="pi" imageUrl={c} />);
    expect({ uri: uriOf(r, 'pi-img') }).toEqual({ uri: c });
    failIfMounted(r, 'pi-img');
    advance(RETRY_MS);
    expect({ cRetryUri: uriOf(r, 'pi-img') }).toEqual({ cRetryUri: c });
  });

  it('I5 at most one breadcrumb per host per app session', () => {
    const r = render(
      <View>
        <ProductImage testID="pa" imageUrl="https://img5.example.com/p/a.jpg?sig=1" />
        <ProductImage testID="pb" imageUrl="https://img5.example.com/p/b.jpg?sig=2" />
        <ProductImage testID="pc" imageUrl="https://img6.example.com/p/c.jpg?sig=3" />
      </View>,
    );
    for (const id of ['pa', 'pb', 'pc']) {
      failIfMounted(r, `${id}-img`);
      advance(RETRY_MS);
      failIfMounted(r, `${id}-img`);
      advance(RETRY_MS);
    }
    expect(hosts()).toEqual(['img5.example.com', 'img6.example.com']);
  });

  it('I6 the host drops user info and port and is lower-cased; a url without an authority gives unknown', () => {
    const withCredentials = 'https://u:secret@IMG7.Example.COM:8443/p/a.jpg?sig=x';
    const inline = 'data:image/png;base64,AAAA';
    const r = render(
      <View>
        <ProductImage testID="pu" imageUrl={withCredentials} />
        <ProductImage testID="pd" imageUrl={inline} />
      </View>,
    );
    for (const id of ['pu', 'pd']) {
      fireEvent(r.getByTestId(`${id}-img`), 'error');
      advance(RETRY_MS);
      expect({ id, retry: has(r, `${id}-img`) }).toEqual({ id, retry: true });
      failIfMounted(r, `${id}-img`);
      advance(RETRY_MS);
    }
    expect(hosts()).toEqual(['img7.example.com', 'unknown']);
    const leaked = ['secret', 'u:', '8443', 'IMG7', 'Example', 'base64', 'AAAA', 'data:image'].filter((s) =>
      wire().includes(s),
    );
    expect(leaked).toEqual([]);
  });

  it('I7 a doubled error arms one retry timer; an unmount clears a pending timer (RU-8)', () => {
    const url = 'https://img8.example.com/p/a.jpg?sig=x';
    const r = render(<ProductImage testID="pi" imageUrl={url} />);
    const before = pendingTimers();
    const onError = r.getByTestId('pi-img').props.onError as () => void;
    // Two native errors in one tick, before React re-renders.
    act(() => {
      onError();
      onError();
    });
    expect({ armed: pendingTimers() - before, placeholder: has(r, 'pi-placeholder') }).toEqual({
      armed: 1,
      placeholder: true,
    });
    advance(RETRY_MS);
    expect({ retryUri: uriOf(r, 'pi-img'), pending: pendingTimers() - before }).toEqual({
      retryUri: url,
      pending: 0,
    });
    r.unmount();

    const url2 = 'https://img9.example.com/p/a.jpg?sig=x';
    const r2 = render(<ProductImage testID="pj" imageUrl={url2} />);
    const before2 = pendingTimers();
    fireEvent(r2.getByTestId('pj-img'), 'error');
    const armed2 = pendingTimers() - before2;
    r2.unmount();
    expect({ armed: armed2, afterUnmount: pendingTimers() - before2 }).toEqual({
      armed: 1,
      afterUnmount: 0,
    });
  });
});

describe('INC-C1b T7-09 pin (passes at base)', () => {
  it('P-I1 right after the first error the placeholder shows with its tone and the Image is gone', () => {
    const r = render(
      <ProductImage
        testID="pi"
        imageUrl="https://img10.example.com/p/a.jpg?sig=x"
        placeholderTone="#FFEAD4"
      />,
    );
    expect(has(r, 'pi-img')).toBe(true);
    fireEvent(r.getByTestId('pi-img'), 'error');
    const ph = r.queryByTestId('pi-placeholder');
    expect({
      img: has(r, 'pi-img'),
      placeholder: ph !== null,
      tone: ph ? flatStyle(ph.props.style).backgroundColor : null,
    }).toEqual({ img: false, placeholder: true, tone: '#FFEAD4' });
  });
});
