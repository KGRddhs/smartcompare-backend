/**
 * W3-15 — the push-tap listeners (`src/services/pushNavigation.ts`).
 *
 * At base `ed75dc70` the client registers ZERO notification response
 * listeners and never calls `setNotificationHandler`
 * (`grep -rn "addNotificationResponseReceivedListener|setNotificationHandler|
 * getLastNotificationResponse|useLastNotificationResponse" src App.tsx index.ts`
 * = 0 hits). React Navigation's default `getInitialURL`/`subscribe` read only
 * `Linking` (`useLinking.native.js:13-35`), and a notification response is not
 * a `Linking` URL — so a tap on any Qaren push opens the app wherever it last
 * was, and `data.url` is never read. Separately, with no JS handler a
 * foreground push times out after 3 s and is never presented on either
 * platform (Android `SingleNotificationHandlerTask.java:32,116-123`; iOS
 * `SingleNotificationHandlerTask.swift:34-41,53-57`).
 *
 * Structure mirrors `__tests__/pushTokenService.test.ts:17-28`: per-test
 * `jest.resetModules()` + `jest.doMock('expo-notifications', ...)`, so the
 * require-throws case is reachable and the module's own `pending` /
 * `lastHandledIdentifier` slots are reset between tests.
 *
 * The REAL `src/navigation/linking.ts` is deliberately NOT mocked — the
 * dispatched action shape is exactly what depends on it. Only the exported
 * `navigationRef`'s methods are stubbed (`isReady`/`dispatch`/`resetRoot` are
 * own data properties on the object `createNavigationContainerRef()` returns,
 * `createNavigationContainerRef.js:14-61`, so `jest.spyOn` works).
 */

const DEFAULT_ACTION_IDENTIFIER = 'expo.modules.notifications.actions.DEFAULT';

type ResponseOpts = {
  identifier?: string;
  actionIdentifier?: string;
  /** omit the key entirely by passing `undefined` for `url` with omitUrl */
  omitUrl?: boolean;
};

function makeResponse(url: unknown, opts: ResponseOpts = {}): any {
  const data: Record<string, unknown> = opts.omitUrl ? { type: 'loop2' } : { url, type: 'loop2' };
  return {
    actionIdentifier: opts.actionIdentifier ?? DEFAULT_ACTION_IDENTIFIER,
    notification: {
      date: 0,
      request: {
        identifier: opts.identifier ?? 'n1',
        content: { title: 't', body: 'b', data },
        trigger: null,
      },
    },
  };
}

type Harness = {
  mod: any;
  notifications: any;
  isReady: jest.SpyInstance;
  dispatch: jest.SpyInstance;
  resetRoot: jest.SpyInstance;
  /** the callback handed to addNotificationResponseReceivedListener */
  listener: () => (response: any) => unknown;
  remove: jest.Mock;
  /** the REAL linking config from the same module registry pushNavigation sees */
  linking: any;
};

/** Build the expo-notifications double + load the module under test. */
function load(overrides: Record<string, unknown> = {}): Harness {
  const remove = jest.fn();
  let captured: ((response: any) => unknown) | undefined;

  const notifications: any = {
    DEFAULT_ACTION_IDENTIFIER,
    setNotificationHandler: jest.fn(),
    addNotificationResponseReceivedListener: jest.fn((cb: (r: any) => unknown) => {
      captured = cb;
      return { remove };
    }),
    getLastNotificationResponse: jest.fn(() => null),
    clearLastNotificationResponse: jest.fn(),
    ...overrides,
  };

  jest.doMock('expo-notifications', () => notifications, { virtual: true });

  // Same module registry -> pushNavigation sees this exact navigationRef.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { navigationRef, linking } = require('../../src/navigation/linking');
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const mod = require('../../src/services/pushNavigation');

  const isReady = jest.spyOn(navigationRef, 'isReady').mockReturnValue(false as never);
  const dispatch = jest.spyOn(navigationRef, 'dispatch').mockImplementation(() => undefined as never);
  const resetRoot = jest.spyOn(navigationRef, 'resetRoot').mockImplementation(() => undefined as never);

  return {
    mod,
    notifications,
    isReady,
    dispatch,
    resetRoot,
    listener: () => {
      if (!captured) throw new Error('no listener was registered');
      return captured;
    },
    remove,
    linking,
  };
}

// The exact actions measured through the real core 7.17.4 getActionFromState
// over the proposed config (unit probe 3).
const NAVIGATE_RESULTS = {
  type: 'NAVIGATE',
  payload: {
    name: 'Results',
    path: 'comparison/abc?banner=insight',
    params: { comparison_id: 'abc', banner: 'insight' },
  },
};
const NAVIGATE_PROFILE_TAB = {
  type: 'NAVIGATE',
  payload: {
    name: 'Main',
    params: { initial: true, screen: 'ProfileTab', path: 'profile/referrals' },
    pop: true,
  },
};

beforeEach(() => {
  jest.resetModules();
  jest.restoreAllMocks();
  jest.clearAllMocks();
});

describe('W3-15 P1 — cold start replays the stored response, then clears it', () => {
  it('dispatches NAVIGATE Results and calls clearLastNotificationResponse once', () => {
    const h = load({
      getLastNotificationResponse: jest.fn(() =>
        makeResponse('qaren://comparison/abc?banner=insight', { identifier: 'n1' })
      ),
    });
    h.isReady.mockReturnValue(true as never);

    h.mod.onNavigationReady();

    expect(h.dispatch).toHaveBeenCalledTimes(1);
    expect(h.dispatch.mock.calls[0][0]).toEqual(NAVIGATE_RESULTS);
    expect(h.notifications.clearLastNotificationResponse).toHaveBeenCalledTimes(1);
  });
});

describe('W3-15 P2 — a warm tap navigates', () => {
  it('registers one response listener and dispatches NAVIGATE Main{ProfileTab}', () => {
    const h = load();
    h.isReady.mockReturnValue(true as never);

    h.mod.installPushTapListeners();
    expect(h.notifications.addNotificationResponseReceivedListener).toHaveBeenCalledTimes(1);

    const handled = h.listener()(makeResponse('qaren://profile/referrals'));

    expect(handled).toBe(true);
    expect(h.dispatch).toHaveBeenCalledTimes(1);
    expect(h.dispatch.mock.calls[0][0]).toEqual(NAVIGATE_PROFILE_TAB);
  });
});

describe('W3-15 P3 — a tap before the container is ready is parked, then drained exactly once', () => {
  it('no dispatch while not ready; one after onNavigationReady; still one on a second call', () => {
    const h = load();
    h.isReady.mockReturnValue(false as never);

    h.mod.installPushTapListeners();
    h.listener()(makeResponse('qaren://profile/referrals'));
    expect(h.dispatch).not.toHaveBeenCalled();

    h.isReady.mockReturnValue(true as never);
    h.mod.onNavigationReady();
    expect(h.dispatch).toHaveBeenCalledTimes(1);
    expect(h.dispatch.mock.calls[0][0]).toEqual(NAVIGATE_PROFILE_TAB);

    h.mod.onNavigationReady();
    expect(h.dispatch).toHaveBeenCalledTimes(1);
  });
});

describe('W3-15 P4 — guards', () => {
  it('P4a PIN: a null/undefined response is ignored and never throws', () => {
    const h = load();
    h.isReady.mockReturnValue(true as never);

    expect(h.mod.handlePushResponse(null)).toBe(false);
    expect(h.mod.handlePushResponse(undefined)).toBe(false);
    expect(h.dispatch).not.toHaveBeenCalled();
    expect(h.resetRoot).not.toHaveBeenCalled();
  });

  // The ONE `typeof url === 'string'` guard is pathFromPushUrl's
  // (pushNavigation.ts); handlePushResponse routes data.url straight into it.
  // Removing that guard makes `url.toLowerCase()` throw on undefined / 42 → red.
  it('P4b: data without a url is ignored (NotificationContent.data is Record<string, unknown>)', () => {
    const h = load();
    h.isReady.mockReturnValue(true as never);

    expect(h.mod.handlePushResponse(makeResponse(undefined, { omitUrl: true }))).toBe(false);
    expect(h.mod.handlePushResponse(makeResponse(42, { identifier: 'n2' }))).toBe(false);
    expect(h.dispatch).not.toHaveBeenCalled();
    expect(h.resetRoot).not.toHaveBeenCalled();
  });

  it('P4c: a non-default actionIdentifier (an action button, not a tap) is ignored', () => {
    const h = load();
    h.isReady.mockReturnValue(true as never);

    const r = makeResponse('qaren://profile/referrals', { actionIdentifier: 'some.custom.action' });
    expect(h.mod.handlePushResponse(r)).toBe(false);
    expect(h.dispatch).not.toHaveBeenCalled();
    expect(h.resetRoot).not.toHaveBeenCalled();
  });

  it("P4e: the plain-tap identifier is the MODULE's DEFAULT_ACTION_IDENTIFIER, not a copied literal", () => {
    // A double whose constant differs from the 0.32.17 literal: the module
    // value must win, so a future SDK rename cannot silently turn every plain
    // tap into a "custom action" that is ignored.
    const h = load({ DEFAULT_ACTION_IDENTIFIER: 'sdk.renamed.DEFAULT' });
    h.isReady.mockReturnValue(true as never);

    const literal = makeResponse('qaren://profile/referrals', { identifier: 'n-literal' });
    expect(h.mod.handlePushResponse(literal)).toBe(false);
    expect(h.dispatch).not.toHaveBeenCalled();

    const renamed = makeResponse('qaren://profile/referrals', {
      identifier: 'n-renamed',
      actionIdentifier: 'sdk.renamed.DEFAULT',
    });
    expect(h.mod.handlePushResponse(renamed)).toBe(true);
    expect(h.dispatch).toHaveBeenCalledTimes(1);
    expect(h.dispatch.mock.calls[0][0]).toEqual(NAVIGATE_PROFILE_TAB);
  });

  it('P4d PIN: a foreign-origin url is ignored (no prefix match)', () => {
    const h = load();
    h.isReady.mockReturnValue(true as never);

    const r = makeResponse('https://evil.example/comparison/abc');
    expect(h.mod.handlePushResponse(r)).toBe(false);
    expect(h.dispatch).not.toHaveBeenCalled();
    expect(h.resetRoot).not.toHaveBeenCalled();
  });

  // P4f — the HOST BOUNDARY after `https://qaren.app`. A bare prefix match
  // accepts `https://qaren.appcomparison/abc` (host `qaren.appcomparison`)
  // and dispatches NAVIGATE Results{comparison_id:'abc'}. Mutation: drop the
  // boundary check in pathFromPushUrl -> this test (and P9b) go red.
  it('P4f: a host that merely STARTS with qaren.app is foreign, and is never navigated', () => {
    const h = load();
    h.isReady.mockReturnValue(true as never);

    const foreign = [
      'https://qaren.appcomparison/abc',
      'https://qaren.app.evil.com/comparison/abc',
      'https://evil.com/qaren.app/comparison/abc',
      'https://qaren.app@evil.com/comparison/abc',
    ];
    foreign.forEach((url, i) => {
      expect({ url, handled: h.mod.handlePushResponse(makeResponse(url, { identifier: `f${i}` })) }).toEqual({
        url,
        handled: false,
      });
    });
    // Bare `qaren://` belongs to the app but names no route.
    expect(h.mod.handlePushResponse(makeResponse('qaren://', { identifier: 'bare' }))).toBe(false);
    expect(h.dispatch).not.toHaveBeenCalled();
    expect(h.resetRoot).not.toHaveBeenCalled();

    // Positive control: the same path on the real host still navigates.
    const own = makeResponse('https://qaren.app/comparison/abc?banner=insight', { identifier: 'own' });
    expect(h.mod.handlePushResponse(own)).toBe(true);
    expect(h.dispatch).toHaveBeenCalledTimes(1);
    expect(h.dispatch.mock.calls[0][0]).toEqual(NAVIGATE_RESULTS);
  });
});

describe('W3-15 P5 — the foreground handler is installed', () => {
  it('sets a handler whose behaviour is banner+list, no sound, no badge, no shouldShowAlert', async () => {
    const h = load();

    h.mod.installPushTapListeners();

    expect(h.notifications.setNotificationHandler).toHaveBeenCalledTimes(1);
    const handler = h.notifications.setNotificationHandler.mock.calls[0][0];
    const behaviour = await handler.handleNotification({} as never);

    expect(behaviour).toEqual({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: false,
      shouldSetBadge: false,
    });
    // shouldShowAlert is deprecated on 0.32.17 and makes NotificationsHandler.js:65-66 warn.
    expect(Object.prototype.hasOwnProperty.call(behaviour, 'shouldShowAlert')).toBe(false);
  });
});

describe('W3-15 P6 — install is idempotent, and the unsubscribe really unsubscribes', () => {
  it('two installs register once; the returned unsubscribe removes once; a later install re-registers', () => {
    const h = load();

    const unsubscribe = h.mod.installPushTapListeners();
    h.mod.installPushTapListeners();

    expect(h.notifications.addNotificationResponseReceivedListener).toHaveBeenCalledTimes(1);
    expect(h.notifications.setNotificationHandler).toHaveBeenCalledTimes(1);

    expect(typeof unsubscribe).toBe('function');
    unsubscribe();
    expect(h.remove).toHaveBeenCalledTimes(1);

    // The unsubscribe must reset the installed flag, or a React StrictMode
    // cleanup->re-run of the effect leaves the app with NO listener.
    h.mod.installPushTapListeners();
    expect(h.notifications.addNotificationResponseReceivedListener).toHaveBeenCalledTimes(2);
  });

  it('P6b: a subscription whose remove() throws never breaks the effect cleanup, and still re-arms', () => {
    const h = load();
    h.remove.mockImplementation(() => {
      throw new Error('subscription already removed');
    });

    const unsubscribe = h.mod.installPushTapListeners();
    expect(() => unsubscribe()).not.toThrow();
    expect(h.remove).toHaveBeenCalledTimes(1);

    // The slot was still reset, so the next effect run registers again.
    h.mod.installPushTapListeners();
    expect(h.notifications.addNotificationResponseReceivedListener).toHaveBeenCalledTimes(2);
  });
});

describe('W3-15 P7 — a missing native module never breaks boot', () => {
  it('installPushTapListeners returns a function and onNavigationReady does not throw', () => {
    jest.doMock(
      'expo-notifications',
      () => {
        throw new Error('native module missing');
      },
      { virtual: true }
    );
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { navigationRef } = require('../../src/navigation/linking');
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require('../../src/services/pushNavigation');
    const dispatch = jest
      .spyOn(navigationRef, 'dispatch')
      .mockImplementation(() => undefined as never);

    let unsubscribe: unknown;
    expect(() => {
      unsubscribe = mod.installPushTapListeners();
    }).not.toThrow();
    expect(typeof unsubscribe).toBe('function');
    expect(() => (unsubscribe as () => void)()).not.toThrow();
    expect(() => mod.onNavigationReady()).not.toThrow();
    expect(dispatch).not.toHaveBeenCalled();
  });

  it('P7b: the module loads but a listener API throws on install => no throw, returns a function', () => {
    // The install runs from a useEffect in App(); a throw there is a render
    // error on boot. UnavailabilityError-shaped, like the emitter's own.
    const h = load({
      addNotificationResponseReceivedListener: jest.fn(() => {
        const e: any = new Error(
          'The method or property ExpoNotifications.addNotificationResponseReceivedListener is not available on this platform'
        );
        e.code = 'ERR_UNAVAILABLE';
        throw e;
      }),
    });

    let unsubscribe: unknown;
    expect(() => {
      unsubscribe = h.mod.installPushTapListeners();
    }).not.toThrow();
    expect(typeof unsubscribe).toBe('function');
    expect(() => (unsubscribe as () => void)()).not.toThrow();
  });
});

describe('W3-15 P8 — an unavailable native function is swallowed', () => {
  it('getLastNotificationResponse throwing UnavailabilityError does not propagate', () => {
    const h = load({
      getLastNotificationResponse: jest.fn(() => {
        const e: any = new Error(
          "The method or property ExpoNotifications.getLastNotificationResponse is not available on this platform"
        );
        e.code = 'ERR_UNAVAILABLE';
        throw e;
      }),
    });
    h.isReady.mockReturnValue(true as never);

    expect(() => h.mod.onNavigationReady()).not.toThrow();
    expect(h.dispatch).not.toHaveBeenCalled();
  });

  it('P8b: clearLastNotificationResponse throwing (second throw site, NotificationsEmitter.js:136-141) is swallowed', () => {
    // getLast works, clear does not: the tap must still navigate exactly once
    // and onReady (inside NavigationContainer) must not throw.
    const h = load({
      getLastNotificationResponse: jest.fn(() =>
        makeResponse('qaren://comparison/abc?banner=insight', { identifier: 'n1' })
      ),
      clearLastNotificationResponse: jest.fn(() => {
        const e: any = new Error(
          'The method or property ExpoNotifications.clearLastNotificationResponse is not available on this platform'
        );
        e.code = 'ERR_UNAVAILABLE';
        throw e;
      }),
    });
    h.isReady.mockReturnValue(true as never);

    expect(() => h.mod.onNavigationReady()).not.toThrow();
    expect(h.notifications.clearLastNotificationResponse).toHaveBeenCalledTimes(1);
    expect(h.dispatch).toHaveBeenCalledTimes(1);
    expect(h.dispatch.mock.calls[0][0]).toEqual(NAVIGATE_RESULTS);
  });
});

describe('W3-15 P11 — a resolver that throws never escapes handlePushResponse', () => {
  it('linking.getStateFromPath throwing => handlePushResponse returns false; onNavigationReady does not throw', () => {
    // actionFromPushUrl's try/catch is what keeps handlePushResponse's
    // "never throws" contract when the config's resolver (the custom redeem
    // rewrite, or a future parse fn) throws. Without it the throw escapes the
    // notification listener and, on cold start, NavigationContainer.onReady.
    const response = makeResponse('qaren://profile/referrals', { identifier: 'n-throw' });
    const h = load({ getLastNotificationResponse: jest.fn(() => response) });
    h.isReady.mockReturnValue(true as never);
    jest.spyOn(h.linking, 'getStateFromPath').mockImplementation(() => {
      throw new URIError('URI malformed');
    });

    let handled: unknown;
    expect(() => {
      handled = h.mod.handlePushResponse(response);
    }).not.toThrow();
    expect(handled).toBe(false);
    expect(() => h.mod.onNavigationReady()).not.toThrow();
    expect(h.dispatch).not.toHaveBeenCalled();
    expect(h.resetRoot).not.toHaveBeenCalled();
  });
});

describe('W3-15 P9 — pathFromPushUrl', () => {
  it('strips a matching prefix (scheme case-insensitively) and rejects foreign URLs', () => {
    const h = load();

    expect(h.mod.pathFromPushUrl('qaren://profile/referrals')).toBe('profile/referrals');
    expect(h.mod.pathFromPushUrl('https://qaren.app/c/T')).toBe('c/T');
    expect(h.mod.pathFromPushUrl('QAREN://x')).toBe('x');
    expect(h.mod.pathFromPushUrl('mailto:x')).toBeUndefined();
    // Non-strings (NotificationContent.data values are `unknown`) never throw.
    expect(h.mod.pathFromPushUrl(undefined)).toBeUndefined();
    expect(h.mod.pathFromPushUrl(42)).toBeUndefined();
    expect(h.mod.pathFromPushUrl({ toString: () => 'qaren://profile/referrals' })).toBeUndefined();
  });

  it('P9b: the host boundary — accepts/rejects exactly as the real extractPathFromURL 7.2.4 does', () => {
    const h = load();
    // The package's "exports" map hides lib/, so the real helper is reached by
    // absolute path (same technique as __tests__/navigation/linking.w315.test.ts).
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { extractPathFromURL } = require(require('path').resolve(
      __dirname,
      '../../node_modules/@react-navigation/native/lib/module/extractPathFromURL.js'
    ));
    const prefixes = h.linking.prefixes;

    const table: [string, string | undefined][] = [
      ['https://qaren.appcomparison/abc', undefined],
      ['https://qaren.app.evil.com/x', undefined],
      ['https://evil.com/qaren.app/x', undefined],
      ['https://qaren.app@evil.com/x', undefined],
      ['https://qaren.app:8443/x', undefined],
      ['qaren://', ''],
      ['https://qaren.app', ''],
      ['https://qaren.app/comparison/abc', 'comparison/abc'],
      ['https://qaren.app?code=QR-1', '?code=QR-1'],
      ['qaren://comparison/abc', 'comparison/abc'],
    ];
    for (const [url, expected] of table) {
      const ours = h.mod.pathFromPushUrl(url);
      expect({ url, ours }).toEqual({ url, ours: expected });
      // Accept/reject parity with the helper the Linking pipeline uses. (The
      // returned path can differ in leading-slash shape, e.g. '?code' vs
      // '/?code' — both resolve the same — so only definedness is compared.)
      expect({ url, rn: extractPathFromURL(prefixes, url) !== undefined }).toEqual({
        url,
        rn: expected !== undefined,
      });
    }
  });
});

describe('W3-15 P10 — one tap delivered through BOTH channels dispatches once', () => {
  // EmitterModule.swift:40-46 sets lastResponse AND sends the JS event in the
  // same didReceive; NotificationsEmitter.kt:70-83 does the same. A cold start
  // therefore parks the response AND finds it in the native slot.
  it('same notification identifier via the listener and the cold-start slot => one dispatch', () => {
    const sameResponse = makeResponse('qaren://profile/referrals', { identifier: 'n1' });
    const h = load({ getLastNotificationResponse: jest.fn(() => sameResponse) });

    h.isReady.mockReturnValue(false as never);
    h.mod.installPushTapListeners();
    h.listener()(sameResponse);
    expect(h.dispatch).not.toHaveBeenCalled();

    h.isReady.mockReturnValue(true as never);
    h.mod.onNavigationReady();

    expect(h.dispatch).toHaveBeenCalledTimes(1);
    expect(h.notifications.clearLastNotificationResponse).toHaveBeenCalledTimes(1);
  });
});

describe('W3-15 P12 — KNOWN-LIMIT PIN: a tap for comparison B while Results(A) is focused reuses the route', () => {
  // Documented follow-up, NOT a fix: must be closed (a `getId` on the Results
  // screen, or a refetch when comparison_id changes) BEFORE
  // ENABLE_REENGAGEMENT_PUSHES flips — only those dark pushes target Results.
  // Today the dispatched NAVIGATE Results{B}, applied by the real StackRouter to
  // [Main, Results(A)], keeps Results(A)'s KEY and swaps its params; the
  // mounted ResultsScreen's fetch effect then hits
  // `if (!comparisonId || result) return;` (A's result is already set) and
  // keeps showing A. Each assertion below goes red when one half of that
  // changes, so the fix cannot land without this pin (and the PR-body limit)
  // being updated.
  it('NAVIGATE Results{B} over [Main, Results(A)] keeps the key and swaps params; no getId; the fetch guard skips', () => {
    const h = load();
    h.isReady.mockReturnValue(true as never);

    expect(
      h.mod.handlePushResponse(makeResponse('qaren://comparison/B?banner=retrospective', { identifier: 'nB' }))
    ).toBe(true);
    expect(h.dispatch).toHaveBeenCalledTimes(1);
    const action = h.dispatch.mock.calls[0][0];

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { StackRouter } = require('@react-navigation/native');
    const router = StackRouter({});
    const options = { routeNames: ['Main', 'Results'], routeParamList: {}, routeGetIdList: {} };
    const focusedOnA = {
      stale: false,
      type: 'stack',
      key: 'stack-root',
      index: 1,
      routeNames: ['Main', 'Results'],
      preloadedRoutes: [],
      routes: [
        { key: 'Main-k', name: 'Main' },
        { key: 'Results-A', name: 'Results', params: { comparison_id: 'A' } },
      ],
    };
    const next = router.getStateForAction(focusedOnA, action, options);

    expect(next.routes.map((r: { key: string }) => r.key)).toEqual(['Main-k', 'Results-A']);
    expect(next.index).toBe(1);
    expect(next.routes[1].params).toEqual({ comparison_id: 'B', banner: 'retrospective' });

    // The two source facts that make the reused route keep showing A.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const fs = require('fs');
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const nodePath = require('path');
    const app: string = fs
      .readFileSync(nodePath.resolve(__dirname, '../../App.tsx'), 'utf8')
      .replace(/\r\n/g, '\n');
    const resultsScreenDecl = app.match(/<Stack\.Screen\s+name="Results"[\s\S]*?\/>/);
    expect(resultsScreenDecl).not.toBeNull();
    expect(resultsScreenDecl![0]).not.toMatch(/getId/);
    const results: string = fs.readFileSync(
      nodePath.resolve(__dirname, '../../src/screens/ResultsScreen.tsx'),
      'utf8'
    );
    expect(results).toContain('if (!comparisonId || result) return;');
  });
});
