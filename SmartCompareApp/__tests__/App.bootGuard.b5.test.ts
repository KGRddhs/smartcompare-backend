/**
 * B5 — App.tsx's boot must release the splash gate on EVERY path.
 *
 * Before this fix, `init()` ran four awaits (saved language,
 * i18n.changeLanguage, stable id, auth) and only the LAST one was wrapped
 * in a try/catch; `setIsLoading(false)` was the final statement inside the
 * function. A rejection in any earlier step therefore skipped it, and the
 * render tree gates on `isLoading`:
 *
 *     if (!fontsLoaded || isLoading || showSplash) return <SplashScreen ... />
 *
 * — with no retry, no timeout and no error surface. The app would have sat
 * on the splash for the rest of the process.
 *
 * Rendering the real App tree is not practical here (NavigationContainer +
 * fonts + splash + auth init — see the note at the top of
 * App.referral.test.tsx), so this suite does the next best thing: it lifts
 * the ACTUAL boot block out of App.tsx and executes it against injected
 * stubs. That makes these behavioural assertions, not greps — if the
 * try/catch/finally is removed from the source, the extracted code strands
 * exactly as production would and the tests below fail.
 *
 * The boot block is plain JS (no TypeScript annotations inside init), which
 * is what makes the lift possible. If a future edit adds one, `new Function`
 * throws and the extraction test fails loudly — the right outcome, since the
 * guard would then need re-verifying by hand.
 */

import * as fs from 'fs';
import * as path from 'path';

const APP_PATH = path.resolve(__dirname, '../App.tsx');
// Normalised to LF so the block markers below behave the same on the
// Windows checkout (CRLF) and on CI (LF).
const appSrc: string = fs.readFileSync(APP_PATH, 'utf8').replace(/\r\n/g, '\n');

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

type Stubs = {
  getSavedLanguage: jest.Mock;
  changeLanguage: jest.Mock;
  getStableId: jest.Mock;
  initializeAuth: jest.Mock;
  setFlagStableId: jest.Mock;
  setStableUserId: jest.Mock;
  setUser: jest.Mock;
  setIsAuthenticated: jest.Mock;
  setNeedsPreferences: jest.Mock;
  setIsLoading: jest.Mock;
  tryRegisterPushToken: jest.Mock;
  I18nManager: { isRTL: boolean; allowRTL: jest.Mock; forceRTL: jest.Mock };
};

function makeStubs(overrides: Partial<Record<keyof Stubs, any>> = {}): Stubs {
  const stubs: Stubs = {
    getSavedLanguage: jest.fn().mockResolvedValue('en'),
    changeLanguage: jest.fn().mockResolvedValue(undefined),
    getStableId: jest.fn().mockResolvedValue('device-abc'),
    initializeAuth: jest.fn().mockResolvedValue(null),
    setFlagStableId: jest.fn(),
    setStableUserId: jest.fn(),
    setUser: jest.fn(),
    setIsAuthenticated: jest.fn(),
    setNeedsPreferences: jest.fn(),
    setIsLoading: jest.fn(),
    tryRegisterPushToken: jest.fn(() => Promise.resolve()),
    I18nManager: { isRTL: false, allowRTL: jest.fn(), forceRTL: jest.fn() },
  };
  return Object.assign(stubs, overrides);
}

/** Let the extracted promise chain (init → catch → finally) settle. */
async function settle(): Promise<void> {
  for (let i = 0; i < 5; i += 1) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise<void>((resolve) => setImmediate(resolve));
  }
}

async function runBootBlock(stubs: Stubs): Promise<void> {
  const block = extractBootBlock();
  // eslint-disable-next-line @typescript-eslint/no-implied-eval, no-new-func
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
    block
  );
  run(
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
    false // __DEV__ off so a failing step does not print to the test console
  );
  await settle();
}

describe('B5 — App boot releases the splash gate on every path', () => {
  it('lifts the real boot block out of App.tsx', () => {
    const block = extractBootBlock();
    expect(block).toContain('await getSavedLanguage()');
    expect(block).toContain('await initializeAuth(');
    expect(block).toContain('setIsLoading(false)');
  });

  it('happy path still clears isLoading exactly once', async () => {
    const stubs = makeStubs();
    await runBootBlock(stubs);

    expect(stubs.setIsLoading).toHaveBeenCalledTimes(1);
    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
  });

  it('a rejecting getSavedLanguage still clears isLoading', async () => {
    // The FIRST await in the chain — the furthest-upstream strand.
    const stubs = makeStubs({
      getSavedLanguage: jest.fn().mockRejectedValue(new Error('storage down')),
    });
    await runBootBlock(stubs);

    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
  });

  it('a rejecting i18n.changeLanguage still clears isLoading', async () => {
    const stubs = makeStubs({
      changeLanguage: jest.fn().mockRejectedValue(new Error('i18n init failed')),
    });
    await runBootBlock(stubs);

    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
  });

  it('a rejecting getStableId still clears isLoading', async () => {
    const stubs = makeStubs({
      getStableId: jest.fn().mockRejectedValue(new Error('no crypto')),
    });
    await runBootBlock(stubs);

    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
  });

  it('a throwing (not rejecting) boot step still clears isLoading', async () => {
    const stubs = makeStubs({
      getStableId: jest.fn(() => {
        throw new TypeError('synchronous blow-up');
      }),
    });
    await runBootBlock(stubs);

    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
  });

  it('a rejecting initializeAuth still clears isLoading (inner catch kept)', async () => {
    const stubs = makeStubs({
      initializeAuth: jest.fn().mockRejectedValue(new Error('401')),
    });
    await runBootBlock(stubs);

    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
    // The inner try/catch is what keeps a dead session from skipping the
    // rest of init; it must not have been collapsed into the outer guard.
    expect(extractBootBlock()).toMatch(/catch\s*\(\s*error\s*\)\s*\{[\s\S]{0,200}Auth initialization error/);
  });

  it('an authenticated boot still applies its auth state before clearing', async () => {
    const stubs = makeStubs({
      initializeAuth: jest
        .fn()
        .mockResolvedValue({ id: 'u-1', preferences_completed: true }),
    });
    await runBootBlock(stubs);

    expect(stubs.setStableUserId).toHaveBeenCalledWith('u-1');
    expect(stubs.setIsAuthenticated).toHaveBeenCalledWith(true);
    expect(stubs.setNeedsPreferences).toHaveBeenCalledWith(false);
    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
  });

  it('an Arabic boot still forces RTL before clearing', async () => {
    const stubs = makeStubs({
      getSavedLanguage: jest.fn().mockResolvedValue('ar'),
    });
    await runBootBlock(stubs);

    expect(stubs.changeLanguage).toHaveBeenCalledWith('ar');
    expect(stubs.I18nManager.forceRTL).toHaveBeenCalledWith(true);
    expect(stubs.setIsLoading).toHaveBeenCalledWith(false);
  });

  it('a rejecting boot is caught, so it never surfaces as an unhandled rejection', () => {
    // `.finally()` alone would release the gate but leave the rejection
    // unhandled (a red LogBox / Sentry noise on every failed boot).
    const block = extractBootBlock();
    expect(block).toMatch(/init\(\)[\s\S]{0,400}\.catch\(/);
    expect(block).toMatch(/\.finally\(\s*\(\)\s*=>\s*\{[\s\S]{0,200}setIsLoading\(false\)/);
  });

  it('does not release the gate from inside the awaited chain', () => {
    // If `setIsLoading(false)` is still the tail statement of init(), the
    // guard is decorative — an early rejection skips it just as before.
    const block = extractBootBlock();
    // Everything up to the closing brace of `async function init() { ... }`.
    const initBody = block.slice(0, block.indexOf('\n    }\n'));
    expect(initBody).toContain('await initializeAuth(');
    expect(initBody).not.toContain('setIsLoading');
  });
});

describe('B5 — App.tsx imports the i18n module exactly once', () => {
  it('no longer re-imports ./src/i18n dynamically inside init', () => {
    // The dynamic import resolved to the SAME module the static import at
    // the top had already evaluated, so it bought nothing and only added an
    // await to the boot chain.
    expect(appSrc).not.toMatch(/await\s+import\(\s*['"]\.\/src\/i18n['"]\s*\)/);
    expect(appSrc).not.toMatch(/\{\s*default:\s*i18n\s*\}/);
  });

  it('takes the i18n instance from the single static import', () => {
    expect(appSrc).toMatch(
      /^import\s+i18n,\s*\{[^}]*getSavedLanguage[^}]*\}\s+from\s+['"]\.\/src\/i18n['"];$/m
    );
    const imports = appSrc.match(/from\s+['"]\.\/src\/i18n['"]/g) ?? [];
    expect(imports).toHaveLength(1);
    expect(appSrc).not.toMatch(/^import\s+['"]\.\/src\/i18n['"];$/m);
  });

  it('the module really does default-export the configured i18n instance', () => {
    // Pins the precondition for collapsing the two imports: the default
    // export is the i18next instance whose changeLanguage() init() calls.
    // Checked at source level — requiring src/i18n pulls expo-localization's
    // untransformed ESM into this node-env suite.
    const i18nSrc: string = fs.readFileSync(
      path.resolve(__dirname, '../src/i18n/index.ts'),
      'utf8'
    );
    expect(i18nSrc).toMatch(/^import\s+i18n\s+from\s+'i18next';$/m);
    expect(i18nSrc).toMatch(/^export\s+default\s+i18n;$/m);
    expect(i18nSrc).toMatch(/^export\s+async\s+function\s+getSavedLanguage\(/m);
  });
});
