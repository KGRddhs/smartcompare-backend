/**
 * W3-12 — the "running unpinned" alarm must survive boot.
 *
 * `certificatePinning.ts:79-80` raises
 *
 *   Sentry.captureMessage('[SECURITY] Certificate pinning init failed -
 *                          session is running unpinned', ...)
 *
 * from the release branch of `setupCertificatePinning`'s catch. That call is
 * the ONLY channel that makes an unpinned release fleet visible (console.* is
 * babel-stripped in production, see babel.config.js).
 *
 * It is reached from `api.ts:22`, which runs in api.ts's MODULE BODY, which
 * the module graph evaluates before App.tsx's body statement `initSentry()`
 * (App.tsx:10) ever executes. So the alarm is raised into a Sentry that has
 * not been initialised and is dropped.
 *
 * This suite runs the real boot chain under the SHIPPED Babel/Metro
 * transform (see `helpers/w312BootSandbox.ts` for why ts-jest's own TS->CJS
 * emit cannot reproduce the ordering), executes the real `api.ts`,
 * `certificatePinning.ts` and `sentry.ts` bodies, and forces
 * `initializeSslPinning` to throw. `initializeSslPinning` is stubbed to throw
 * SYNCHRONOUSLY — a missing / undefined native binding, which is the realistic
 * release-build failure — so the catch (and the captureMessage) run inside
 * api.ts's module body rather than a microtask later, which is exactly where
 * production would raise it.
 *
 * The assertion is on whether Sentry was ALREADY INITIALISED at the moment
 * captureMessage was called — not on whether captureMessage was called at all.
 * The latter is green today (see `bootRegressionPins.w312.test.ts`) and is
 * not the defect.
 */

import {
  API_FILE,
  APP_FILE,
  AUTH_FILE,
  BOOTSTRAP_FILE,
  ENTRY,
  PINNING_FILE,
  SENTRY_FILE,
  makeStub,
  runBoot,
} from './helpers/w312BootSandbox';

const UNPINNED_MESSAGE = '[SECURITY] Certificate pinning init failed';

type Capture = { message: string; sentryWasInitialized: boolean };

describe('W3-12 — the unpinned alarm reaches an initialised Sentry', () => {
  let captures: Capture[];
  let initCalls: number;
  let pinningAttempts: number;

  beforeAll(() => {
    captures = [];
    initCalls = 0;
    pinningAttempts = 0;
    let sentryInitialized = false;

    const sentryNative: any = {
      __esModule: true,
      init: () => {
        initCalls += 1;
        sentryInitialized = true;
      },
      captureMessage: (message: unknown) => {
        captures.push({ message: String(message), sentryWasInitialized: sentryInitialized });
      },
      captureException: () => undefined,
      addBreadcrumb: () => undefined,
      setTag: () => undefined,
      setUser: () => undefined,
      setContext: () => undefined,
      setExtra: () => undefined,
      withScope: (cb: (s: any) => void) => cb({}),
      getCurrentScope: () => ({ setTag: () => undefined, clear: () => undefined }),
    };

    runBoot({
      executable: [ENTRY, APP_FILE, AUTH_FILE, API_FILE, PINNING_FILE, SENTRY_FILE, BOOTSTRAP_FILE],
      bareOverrides: {
        '@sentry/react-native': () => sentryNative,
        'react-native-ssl-public-key-pinning': () => ({
          __esModule: true,
          initializeSslPinning: () => {
            pinningAttempts += 1;
            // Synchronous throw — the undefined-native-binding shape.
            throw new TypeError('native module unavailable');
          },
        }),
        axios: () => {
          const client: any = makeStub();
          return { __esModule: true, default: { create: () => client }, create: () => client };
        },
      },
    });
  });

  it('the boot chain really reached the alarm (guards against a mock/path mistake)', () => {
    // Falsifier: if api.ts never ran, or the pinning stub never got called,
    // or the message text changed, this fails FIRST — so the assertion below
    // is known to be about ordering and not about wiring.
    expect(pinningAttempts).toBeGreaterThan(0);
    expect(captures.map((c) => c.message).join('\n')).toContain(UNPINNED_MESSAGE);
    expect(initCalls).toBeGreaterThan(0);
  });

  it('raises the unpinned alarm while Sentry is initialised', () => {
    // RED today: Sentry.init has not run yet when the alarm fires, so the
    // one signal that a release fleet is unpinned is dropped on the floor.
    const alarm = captures.find((c) => c.message.includes(UNPINNED_MESSAGE));
    expect(alarm).toBeDefined();
    expect(alarm).toEqual({
      message: expect.stringContaining(UNPINNED_MESSAGE),
      sentryWasInitialized: true,
    });
  });
});
