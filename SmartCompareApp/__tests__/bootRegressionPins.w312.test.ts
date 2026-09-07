/**
 * W3-12 — REGRESSION PINS. Everything in this file is ALREADY GREEN at this
 * base and is kept deliberately.
 *
 * The consolidated report asked W3-12 for three red tests. Two of them
 * describe behaviour that already exists, so building them as "red tests"
 * would have produced green tests that prove nothing. They are pinned HERE
 * instead, because W3-12 reorders application boot and must not regress the
 * other session's B5 work while doing it.
 *
 *   (a) "a throwing getLocales strands the splash" — ALREADY FIXED.
 *       App.tsx now reads `init().catch(...).finally(() => setIsLoading(false))`,
 *       so the splash gate is released on every path.
 *       ALREADY GREEN, REGRESSION PIN — do not delete as trivial.
 *
 *   (c) "a synchronously-throwing initializeSslPinning still produces a
 *       captureMessage" — ALREADY TRUE, and as worded it does not describe a
 *       defect: certificatePinning.ts awaits inside a try, so a synchronous
 *       throw, a rejected promise and an undefined native binding are all
 *       caught identically and the catch calls Sentry.captureMessage.
 *       ALREADY GREEN, REGRESSION PIN — do not delete as trivial.
 *       (The REAL defect is that this call reaches an UNINITIALISED Sentry;
 *       that is red, and lives in `bootSentryAlarm.w312.test.ts`.)
 *
 *   (idempotence) The unit spec lists "calling initSentry() twice initialises
 *       once" among its red tests, but `sentry.ts` already carries the
 *       `_initialized` guard, so this is green at this base too.
 *       ALREADY GREEN, REGRESSION PIN — it becomes load-bearing the moment
 *       the fix adds a second arming site (index.ts's bootstrap) alongside
 *       any surviving call in App.tsx.
 */

import * as fs from 'fs';
import * as path from 'path';

jest.mock('@sentry/react-native', () => ({
  __esModule: true,
  init: jest.fn(),
  captureMessage: jest.fn(),
  captureException: jest.fn(),
  addBreadcrumb: jest.fn(),
  setTag: jest.fn(),
  setUser: jest.fn(),
  setContext: jest.fn(),
  setExtra: jest.fn(),
  withScope: jest.fn(),
  getCurrentScope: jest.fn(() => ({ setTag: jest.fn(), clear: jest.fn() })),
}));

const mockInitializeSslPinning = jest.fn();
jest.mock('react-native-ssl-public-key-pinning', () => ({
  __esModule: true,
  initializeSslPinning: (...args: unknown[]) => mockInitializeSslPinning(...args),
}));

// ---------------------------------------------------------------------------
// (a) ALREADY GREEN, REGRESSION PIN — the splash gate releases on every path.
// ---------------------------------------------------------------------------
describe('W3-12 pin (a) [ALREADY GREEN, REGRESSION PIN] — splash .finally() still releases', () => {
  const APP_PATH = path.resolve(__dirname, '../App.tsx');
  // Normalised to LF so the block markers behave the same on the Windows
  // checkout (CRLF) and on CI (LF).
  const appSrc = fs.readFileSync(APP_PATH, 'utf8').replace(/\r\n/g, '\n');
  const BLOCK_START = '    async function init() {';
  const BLOCK_END = '\n  }, []);';

  function extractBootBlock(): string {
    const start = appSrc.indexOf(BLOCK_START);
    if (start === -1) {
      throw new Error('App.tsx: could not find the `async function init()` boot block');
    }
    const end = appSrc.indexOf(BLOCK_END, start);
    if (end === -1) {
      throw new Error('App.tsx: could not find the end of the boot useEffect');
    }
    return appSrc.slice(start, end);
  }

  async function settle(): Promise<void> {
    for (let i = 0; i < 5; i += 1) {
      await new Promise<void>((resolve) => setImmediate(resolve));
    }
  }

  async function runBootBlock(getSavedLanguage: jest.Mock): Promise<jest.Mock> {
    const setIsLoading = jest.fn();
    const run = new Function(
      'getSavedLanguage',
      'i18n',
      'I18nManager',
      'getStableId',
      'setFlagStableId',
      'initializeAuth',
      'setStableUserId',
      'setUser',
      'setIsAuthenticated',
      'setNeedsPreferences',
      'tryRegisterPushToken',
      'setIsLoading',
      '__DEV__',
      extractBootBlock(),
    );
    run(
      getSavedLanguage,
      { changeLanguage: jest.fn().mockResolvedValue(undefined) },
      { isRTL: false, allowRTL: jest.fn(), forceRTL: jest.fn() },
      jest.fn().mockResolvedValue('device-abc'),
      jest.fn(),
      jest.fn().mockResolvedValue(null),
      jest.fn(),
      jest.fn(),
      jest.fn(),
      jest.fn(),
      jest.fn(() => Promise.resolve()),
      setIsLoading,
      false,
    );
    await settle();
    return setIsLoading;
  }

  it('the boot block still ends in a .finally() that clears isLoading', () => {
    const block = extractBootBlock();
    expect(block).toContain('.finally(');
    expect(block).toContain('setIsLoading(false)');
  });

  it('a SYNCHRONOUSLY throwing language read still releases the splash', async () => {
    // The report's "a throwing getLocales" case: getSavedLanguage is the
    // boot step that reads the device locale, and it is the FIRST await in
    // the chain — the furthest-upstream strand.
    const setIsLoading = await runBootBlock(
      jest.fn(() => {
        throw new Error('getLocales blew up');
      }),
    );
    expect(setIsLoading).toHaveBeenCalledWith(false);
  });

  it('a REJECTING language read still releases the splash', async () => {
    const setIsLoading = await runBootBlock(
      jest.fn().mockRejectedValue(new Error('storage down')),
    );
    expect(setIsLoading).toHaveBeenCalledWith(false);
  });
});

// ---------------------------------------------------------------------------
// (c) ALREADY GREEN, REGRESSION PIN — the pinning catch still fires.
// ---------------------------------------------------------------------------
describe('W3-12 pin (c) [ALREADY GREEN, REGRESSION PIN] — cert-pinning catch on a sync throw', () => {
  beforeEach(() => {
    jest.resetModules();
    mockInitializeSslPinning.mockReset();
  });

  it('a synchronously-throwing initializeSslPinning still produces a captureMessage', async () => {
    mockInitializeSslPinning.mockImplementation(() => {
      throw new TypeError('native module unavailable');
    });
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const Sentry = require('@sentry/react-native');
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { setupCertificatePinning } = require('../src/services/certificatePinning');

    await setupCertificatePinning();

    // __DEV__ is false in __tests__/setup.ts, so the release branch runs.
    expect(mockInitializeSslPinning).toHaveBeenCalledTimes(1);
    expect(Sentry.captureMessage).toHaveBeenCalledTimes(1);
    expect(String(Sentry.captureMessage.mock.calls[0][0])).toContain(
      '[SECURITY] Certificate pinning init failed',
    );
  });

  it('a REJECTING initializeSslPinning is caught identically', async () => {
    mockInitializeSslPinning.mockRejectedValue(new Error('handshake failed'));
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const Sentry = require('@sentry/react-native');
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { setupCertificatePinning } = require('../src/services/certificatePinning');

    await setupCertificatePinning();

    expect(Sentry.captureMessage).toHaveBeenCalledTimes(1);
    expect(String(Sentry.captureMessage.mock.calls[0][0])).toContain(
      '[SECURITY] Certificate pinning init failed',
    );
  });
});

// ---------------------------------------------------------------------------
// (idempotence) ALREADY GREEN, REGRESSION PIN — initSentry initialises once.
// ---------------------------------------------------------------------------
describe('W3-12 pin [ALREADY GREEN, REGRESSION PIN] — initSentry() is idempotent', () => {
  beforeEach(() => {
    jest.resetModules();
  });

  it('calling initSentry() twice initialises Sentry exactly once', () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const Sentry = require('@sentry/react-native');
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { initSentry } = require('../src/services/sentry');

    initSentry();
    initSentry();

    expect(Sentry.init).toHaveBeenCalledTimes(1);
  });

  it('resolves the committed fallback DSN and still initialises exactly once', () => {
    // The unit spec says "initSentry already no-ops without a DSN; preserve
    // that". At this base that branch (`if (!resolved) return`) is
    // UNREACHABLE: `resolved` falls through `dsn || EXPO_PUBLIC_SENTRY_DSN ||
    // FALLBACK_DSN`, and FALLBACK_DSN is a non-empty committed literal. So
    // the honest pin is the one that can actually fire — the resolution
    // order, and the single-init guard on top of it.
    const previous = process.env.EXPO_PUBLIC_SENTRY_DSN;
    delete process.env.EXPO_PUBLIC_SENTRY_DSN;
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const Sentry = require('@sentry/react-native');
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { initSentry } = require('../src/services/sentry');

      initSentry('');
      initSentry('');

      expect(Sentry.init).toHaveBeenCalledTimes(1);
      expect(String(Sentry.init.mock.calls[0][0].dsn)).toMatch(/^https:\/\/.+@.+\/\d+$/);
    } finally {
      if (previous === undefined) delete process.env.EXPO_PUBLIC_SENTRY_DSN;
      else process.env.EXPO_PUBLIC_SENTRY_DSN = previous;
    }
  });
});
