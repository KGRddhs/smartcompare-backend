/**
 * W3-15 — how the push-tap wiring is attached to App.tsx.
 *
 * Structural fence, same technique and same reason as
 * `__tests__/App.updateGate.a9.test.ts` and `__tests__/App.bootGuard.b5.test.ts`:
 * rendering the real App tree is not practical here (NavigationContainer +
 * fonts + splash + auth init — the note is at the top of
 * `__tests__/App.referral.test.tsx`), so the placement facts are asserted over
 * the source. Each one guards a different way the feature breaks:
 *
 *   A1  the modules are not imported at all -> nothing is wired.
 *   A2  the linking config stays inline in App() as well as hoisted ->
 *       two LinkingOptions for one container (`useLinking.native.js:47-48`
 *       errors on that), and the config the listeners use is no longer the
 *       config the container uses.
 *   A3  the container has no `ref` -> `navigationRef.dispatch` reaches
 *       nothing; no `onReady` -> the parked tap and the cold-start replay are
 *       never drained.
 *   A4  the effect moved inside the awaited `init()` boot block -> a tap
 *       during the splash is blocked on auth, and B5's lifted boot block
 *       changes shape.
 *   A5  the effect below the splash early return -> React hook-order
 *       violation, and no listener at all while the splash is up, which is
 *       exactly the cold-start window a push tap lands in.
 */
import * as fs from 'fs';
import * as path from 'path';

const APP_PATH = path.resolve(__dirname, '../App.tsx');
// Normalised to LF so the markers behave the same on the Windows checkout
// (CRLF) and on CI (LF) — same treatment as App.bootGuard.b5.test.ts.
const appSrc: string = fs.readFileSync(APP_PATH, 'utf8').replace(/\r\n/g, '\n');

/** Index of `needle`, asserted present so ordering checks can't pass on -1. */
function indexOf(needle: string): number {
  const i = appSrc.indexOf(needle);
  expect({ needle, found: i !== -1 }).toEqual({ needle, found: true });
  return i;
}

// The same block markers App.bootGuard.b5.test.ts uses, so the two stay in step.
const BLOCK_START = '    async function init() {';
const BLOCK_END = '\n  }, []);';

describe('W3-15 A1 — App.tsx imports the hoisted config and the listeners', () => {
  it('imports { linking, navigationRef } from ./src/navigation/linking', () => {
    expect(appSrc).toMatch(
      /import\s*\{[^}]*\blinking\b[^}]*\bnavigationRef\b[^}]*\}\s*from\s+'\.\/src\/navigation\/linking'/
    );
  });

  it('imports installPushTapListeners + onNavigationReady from ./src/services/pushNavigation', () => {
    expect(appSrc).toMatch(
      /import\s*\{[^}]*\binstallPushTapListeners\b[^}]*\}\s*from\s+'\.\/src\/services\/pushNavigation'/
    );
    expect(appSrc).toMatch(
      /import\s*\{[^}]*\bonNavigationReady\b[^}]*\}\s*from\s+'\.\/src\/services\/pushNavigation'/
    );
  });
});

describe('W3-15 A2 — the inline linking config is gone (one config, one place)', () => {
  it('App.tsx no longer declares prefixes', () => {
    expect(appSrc).not.toContain('prefixes: [');
  });

  it('App.tsx no longer declares an inline LinkingOptions const', () => {
    expect(appSrc).not.toMatch(/const\s+linking\s*:/);
  });

  it('App.tsx no longer references getStateFromPath anywhere (the :16 import shrinks too)', () => {
    // Measured at ed75dc70: getStateFromPath appears only at :16/:366/:374/:377
    // and LinkingOptions only at :16/:350 — all inside the hoisted block. A
    // leftover import is not a tsc error (no noUnusedLocals) but is an
    // @typescript-eslint/no-unused-vars warning, and the unit's eslint budget
    // is "exactly one new warning, zero errors".
    expect(appSrc).not.toContain('getStateFromPath');
    expect(appSrc).not.toContain('LinkingOptions');
  });
});

describe('W3-15 A3 — the NavigationContainer is wired to the ref, the config and onReady', () => {
  function containerTag(): string {
    const start = indexOf('<NavigationContainer');
    const end = appSrc.indexOf('>', start);
    expect(end).toBeGreaterThan(start);
    return appSrc.slice(start, end + 1);
  }

  it('carries ref={navigationRef}', () => {
    expect(containerTag()).toContain('ref={navigationRef}');
  });

  // PIN — already true at base (App.tsx:382 `<NavigationContainer linking={linking}>`).
  // It is asserted here so the hoist cannot quietly drop the prop while moving
  // the config out of App().
  it('carries linking={linking} (pin: true today)', () => {
    expect(containerTag()).toContain('linking={linking}');
  });

  it('carries onReady={onNavigationReady}', () => {
    expect(containerTag()).toContain('onReady={onNavigationReady}');
  });
});

describe('W3-15 A4 — the listener install is its own effect, not part of the boot block', () => {
  it('installPushTapListeners is called from inside a useEffect', () => {
    // The CALL, not the import line — an import alone would satisfy a bare
    // substring check and make A4/A5 decoration.
    indexOf('installPushTapListeners()');
    expect(appSrc).toMatch(/useEffect\(\s*\(\)\s*=>[\s\S]{0,300}?installPushTapListeners\(\)/);
  });

  it('the effect returns the unsubscribe (a cleanup that actually unsubscribes)', () => {
    // Either the concise arrow form `useEffect(() => installPushTapListeners(), [])`
    // (implicit return) or a block body with an explicit `return`.
    const concise = /useEffect\(\s*\(\)\s*=>\s*installPushTapListeners\(\)\s*,\s*\[\]\s*\)/.test(
      appSrc
    );
    const block =
      /useEffect\(\s*\(\)\s*=>\s*\{[\s\S]{0,300}?installPushTapListeners\(\)[\s\S]{0,300}?return\s+[A-Za-z_$][\w$]*\s*;[\s\S]{0,100}?\}\s*,\s*\[\]\s*\)/.test(
        appSrc
      ) ||
      /useEffect\(\s*\(\)\s*=>\s*\{[\s\S]{0,300}?return\s+installPushTapListeners\(\)\s*;[\s\S]{0,100}?\}\s*,\s*\[\]\s*\)/.test(
        appSrc
      );
    expect({ concise, block }).not.toEqual({ concise: false, block: false });
  });

  // Vacuously true at base (neither name exists yet); it becomes the real
  // fence the moment the effect lands, and it is what keeps
  // App.bootGuard.b5.test.ts's lifted `init()` block executable.
  it('the awaited boot block never mentions it (pin: true today)', () => {
    const start = appSrc.indexOf(BLOCK_START);
    const end = appSrc.indexOf(BLOCK_END, start);
    expect(start).toBeGreaterThan(-1);
    expect(end).toBeGreaterThan(start);

    const bootBlock = appSrc.slice(start, end);
    for (const forbidden of ['installPushTapListeners', 'onNavigationReady']) {
      expect(bootBlock).not.toContain(forbidden);
    }
  });
});

describe('W3-15 A5 — the effect sits above the splash early return', () => {
  it('installPushTapListeners appears before the splash return', () => {
    const install = indexOf('installPushTapListeners()');
    const splashReturn = indexOf('if (!fontsLoaded || isLoading || showSplash) {');

    // Below the early return the effect would (a) break React's hook order
    // and (b) never arm during the splash — the exact window a cold-start
    // push tap lands in.
    expect(install).toBeLessThan(splashReturn);
  });
});
