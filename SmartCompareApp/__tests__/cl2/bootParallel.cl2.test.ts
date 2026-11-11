/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R33, P11, P12 (spec section 5, RULINGS_S81_G6
 * R-G6-7): getStableId is STARTED before `await getSavedLanguage()` (a catch
 * attached) and awaited where it was, so the SecureStore read overlaps the
 * AsyncStorage read; every effect keeps its order; a rejecting or throwing
 * getStableId still rejects init (no initializeAuth), releases the splash and
 * leaves no unhandled rejection.
 *
 * Harness: the App.bootGuard.b5 extraction (the real init block lifted out of
 * App.tsx and run against injected stubs).
 */

import * as fs from 'fs';
import * as path from 'path';

const APP_PATH = path.resolve(__dirname, '../../App.tsx');
const appSrc: string = fs.readFileSync(APP_PATH, 'utf8').replace(/\r\n/g, '\n');

const BLOCK_START = '    async function init() {';
const BLOCK_END = '\n  }, []);';

function extractBootBlock(): string {
  const start = appSrc.indexOf(BLOCK_START);
  const end = appSrc.indexOf(BLOCK_END, start);
  expect(start).toBeGreaterThan(-1);
  expect(end).toBeGreaterThan(start);
  return appSrc.slice(start, end);
}

type Stubs = Record<string, any>;

function makeStubs(order: string[], overrides: Stubs = {}): Stubs {
  const rec = (name: string, impl: (...a: any[]) => any) =>
    jest.fn((...args: any[]) => {
      order.push(name + (args.length && typeof args[0] === 'string' ? ':' + args[0] : ''));
      return impl(...args);
    });
  const stubs: Stubs = {
    getSavedLanguage: rec('getSavedLanguage', () => Promise.resolve('ar')),
    changeLanguage: rec('changeLanguage', () => Promise.resolve(undefined)),
    getStableId: rec('getStableId', () => Promise.resolve('device-synthetic')),
    initializeAuth: rec('initializeAuth', () => Promise.resolve(null)),
    setFlagStableId: rec('setFlagStableId', () => undefined),
    setStableUserId: jest.fn(),
    setUser: jest.fn(),
    setIsAuthenticated: jest.fn(),
    setNeedsPreferences: jest.fn(),
    setIsLoading: rec('setIsLoading', () => undefined),
    tryRegisterPushToken: jest.fn(() => Promise.resolve()),
    I18nManager: { isRTL: false, allowRTL: jest.fn(), forceRTL: jest.fn() },
    bootstrapRtl: rec('bootstrapRtl', () => Promise.resolve()),
  };
  return Object.assign(stubs, overrides);
}

function startBootBlock(stubs: Stubs, PromiseImpl: PromiseConstructor = Promise): void {
  const block = extractBootBlock();
  const run = new Function(
    'Promise',
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
    'bootstrapRtl',
    block
  );
  run(
    PromiseImpl,
    stubs.getSavedLanguage,
    { changeLanguage: stubs.changeLanguage },
    stubs.I18nManager,
    stubs.getStableId,
    stubs.setFlagStableId,
    stubs.initializeAuth,
    stubs.setStableUserId,
    stubs.setUser,
    stubs.setIsAuthenticated,
    stubs.setNeedsPreferences,
    stubs.tryRegisterPushToken,
    stubs.setIsLoading,
    false,
    stubs.bootstrapRtl
  );
}

const macro = () => new Promise<void>((resolve) => setImmediate(resolve));

/**
 * A Promise binding injected into the boot block's scope. It records every
 * promise derived through `.then(getStableId, ...)` (the started stable-id
 * read) and every promise that was given a rejection handler, so P12 can
 * assert, as an assertion, that the started read carries its catch BEFORE
 * the boot yields to the event loop (otherwise its rejection is unhandled
 * across the getSavedLanguage macrotask). At base the boot block never calls
 * Promise.resolve(), so the tracked set is empty (vacuous).
 */
function makeTrackingPromise(getStableId: unknown) {
  const idPromises: Promise<unknown>[] = [];
  const handled = new Set<Promise<unknown>>();
  class TrackingPromise<T> extends Promise<T> {
    then<R1 = T, R2 = never>(
      onFulfilled?: ((value: T) => R1 | PromiseLike<R1>) | null,
      onRejected?: ((reason: any) => R2 | PromiseLike<R2>) | null
    ): Promise<R1 | R2> {
      if (typeof onRejected === 'function') handled.add(this);
      const derived = super.then(onFulfilled, onRejected);
      if (onFulfilled === getStableId) idPromises.push(derived);
      return derived;
    }
  }
  return { TrackingPromise: TrackingPromise as unknown as PromiseConstructor, idPromises, handled };
}

async function settle(): Promise<void> {
  for (let i = 0; i < 6; i += 1) {
    await macro();
  }
}

/** A getSavedLanguage that answers only after a macrotask (a real storage read). */
const slowLanguage = (lang: string) => () =>
  new Promise<string>((resolve) => setImmediate(() => resolve(lang)));

describe('CL2 boot parallel read (C7)', () => {
  it('R33 getStableId is called while getSavedLanguage is still pending', async () => {
    const order: string[] = [];
    let releaseLang: (v: string) => void = () => undefined;
    const stubs = makeStubs(order, {
      getSavedLanguage: jest.fn(
        () =>
          new Promise<string>((resolve) => {
            releaseLang = resolve;
          })
      ),
    });
    startBootBlock(stubs);
    for (let i = 0; i < 5; i += 1) {
      await Promise.resolve();
    }
    expect(stubs.getSavedLanguage).toHaveBeenCalledTimes(1);
    expect(stubs.getStableId).toHaveBeenCalledTimes(1);
    expect(stubs.initializeAuth).not.toHaveBeenCalled();
    releaseLang('en');
    await settle();
    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
  });

  it('P11 effect order: changeLanguage(ar) < bootstrapRtl(ar) < setFlagStableId < initializeAuth; isLoading released once', async () => {
    const order: string[] = [];
    const stubs = makeStubs(order, { getSavedLanguage: jest.fn(slowLanguage('ar')) });
    startBootBlock(stubs);
    await settle();
    const effects = order.filter((e) => !e.startsWith('getStableId') && !e.startsWith('getSavedLanguage'));
    expect(effects).toEqual([
      'changeLanguage:ar',
      'bootstrapRtl:ar',
      'setFlagStableId:device-synthetic',
      'initializeAuth',
      'setIsLoading',
    ]);
    expect(stubs.setIsLoading).toHaveBeenCalledTimes(1);
    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
    expect(stubs.getStableId).toHaveBeenCalledTimes(1);
  });

  it('P12 a rejecting or throwing getStableId: splash released, no auth, no unhandled rejection', async () => {
    const seen: unknown[] = [];
    const onUnhandled = (reason: unknown) => {
      seen.push(reason);
    };
    process.on('unhandledRejection', onUnhandled);
    try {
      for (const failing of [
        () => Promise.reject(new Error('synthetic secure store failure')),
        () => {
          throw new TypeError('synthetic sync failure');
        },
      ]) {
        const order: string[] = [];
        const stubs = makeStubs(order, {
          getSavedLanguage: jest.fn(slowLanguage('en')),
          getStableId: jest.fn(failing),
        });
        const tracking = makeTrackingPromise(stubs.getStableId);
        startBootBlock(stubs, tracking.TrackingPromise);
        // Microtasks only: getSavedLanguage answers after a macrotask.
        for (let i = 0; i < 10; i += 1) {
          await Promise.resolve();
        }
        const unhandledStarts = tracking.idPromises.filter((p) => !tracking.handled.has(p));
        // Observe the started reads now (after the check) so a missing catch
        // reports as this assertion, not as a runner-level unhandled rejection.
        tracking.idPromises.forEach((p) => p.catch(() => undefined));
        expect(unhandledStarts.length).toBe(0);
        await settle();
        expect(stubs.setIsLoading).toHaveBeenCalledTimes(1);
        expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
        expect(stubs.initializeAuth).not.toHaveBeenCalled();
        expect(stubs.setFlagStableId).not.toHaveBeenCalled();
      }
      await settle();
      expect(seen).toEqual([]);
    } finally {
      process.removeListener('unhandledRejection', onUnhandled);
    }
  });
});
