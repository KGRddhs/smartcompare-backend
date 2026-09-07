/**
 * A9 — how the force-update gate is wired into App.tsx.
 *
 * The gate's BEHAVIOUR is pinned behaviourally elsewhere
 * (`versionCompare.a9`, `appVersionService.a9`, `hooks/useForcedUpdateGate.a9`,
 * `UpdateRequiredScreen.a9`). What those cannot reach is the root
 * component's render ORDER, because rendering the real App tree is not
 * practical here (NavigationContainer + fonts + splash + auth init — same
 * reasoning recorded at the top of `App.referral.test.tsx` and
 * `App.bootGuard.b5.test.ts`). So this suite is a structural fence over
 * App.tsx, and it guards three placement mistakes that would each break
 * the feature in a different way:
 *
 *   1. Gate BEFORE the splash return → the version check becomes a boot
 *      dependency, exactly the thing the fix is required not to do.
 *   2. Gate AFTER / inside the navigator → a dismissable modal over a
 *      fully usable app, i.e. not a block at all.
 *   3. Check awaited inside the `init()` boot block → boot waits on the
 *      network, and a hung request strands the splash.
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

describe('A9 — App.tsx force-update gate wiring', () => {
  it('imports the gate hook and the blocking screen', () => {
    expect(appSrc).toMatch(
      /import\s+UpdateRequiredScreen\s+from\s+'\.\/src\/screens\/UpdateRequiredScreen'/
    );
    expect(appSrc).toMatch(
      /import\s*\{\s*useForcedUpdateGate\s*\}\s*from\s+'\.\/src\/hooks\/useForcedUpdateGate'/
    );
  });

  it('calls the hook unconditionally, above every early return', () => {
    const hookCall = indexOf('const forcedUpdate = useForcedUpdateGate();');
    const splashReturn = indexOf('if (!fontsLoaded || isLoading || showSplash) {');

    // React hook rules: an early return above the hook would change the
    // hook order between renders.
    expect(hookCall).toBeLessThan(splashReturn);
  });

  it('renders the blocking screen AFTER the splash gate and INSTEAD of the navigator', () => {
    const splashReturn = indexOf('if (!fontsLoaded || isLoading || showSplash) {');
    const gateReturn = indexOf('if (forcedUpdate) {');
    const gateScreen = indexOf('<UpdateRequiredScreen updateUrl={forcedUpdate.updateUrl} />');
    const navigator = indexOf('<NavigationContainer');

    expect(gateReturn).toBeGreaterThan(splashReturn);
    expect(gateScreen).toBeGreaterThan(gateReturn);
    expect(gateScreen).toBeLessThan(navigator);
  });

  it('never registers the blocking screen as a dismissable route', () => {
    // A Stack.Screen entry would give the user a back gesture out of the
    // block, which is the whole thing the screen exists to prevent.
    expect(appSrc).not.toMatch(/<Stack\.Screen[^>]*UpdateRequired/);
    expect(appSrc).not.toMatch(/name="UpdateRequired"/);
  });

  it('keeps the check out of the awaited boot block', () => {
    // Same extraction markers B5's guard uses, so the two stay in step.
    const start = appSrc.indexOf('    async function init() {');
    const end = appSrc.indexOf('\n  }, []);', start);
    expect(start).toBeGreaterThan(-1);
    expect(end).toBeGreaterThan(start);

    const bootBlock = appSrc.slice(start, end);
    for (const forbidden of ['forcedUpdate', 'useForcedUpdateGate', 'checkForcedUpdate']) {
      expect(bootBlock).not.toContain(forbidden);
    }
  });

  it('the hook itself is fire-and-forget (no await on the check)', () => {
    const hookSrc = fs
      .readFileSync(path.resolve(__dirname, '../src/hooks/useForcedUpdateGate.ts'), 'utf8')
      .replace(/\r\n/g, '\n');

    expect(hookSrc).toMatch(/checkForcedUpdate\(\)\s*\n?\s*\.then\(/);
    expect(hookSrc).toMatch(/\.catch\(/);
    // An `await` would require an async effect callback, which React does
    // not support, and would signal someone tried to hold render on it.
    expect(hookSrc).not.toMatch(/await\s+checkForcedUpdate/);
  });
});
