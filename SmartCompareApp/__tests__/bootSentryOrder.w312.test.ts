/**
 * W3-12 — Sentry must be armed BEFORE the module graph, not from inside
 * App.tsx's module body.
 *
 * THE DEFECT. `App.tsx:9-10` reads:
 *
 *     import { initSentry } from './src/services/sentry';
 *     initSentry();
 *
 * which LOOKS like the first thing the app does. It is not. `initSentry()`
 * is a statement in App.tsx's module BODY, and a module body only runs after
 * its whole import graph has been evaluated — true under ES module semantics
 * (dependencies evaluated depth-first in source order) and equally true after
 * Babel's ESM->CJS transform, which hoists every `require()` above the body.
 * App.tsx imports `authService` (`:74`), which imports `src/services/api.ts`
 * (`authService.ts:52`), whose module body at `:22` calls
 * `setupCertificatePinning()`. On failure that path raises
 * `Sentry.captureMessage('[SECURITY] Certificate pinning init failed …')`
 * (`certificatePinning.ts:79-80`) — the one alarm that says a release fleet
 * is running unpinned — into a Sentry that does not exist yet. The same
 * window swallows any boot crash in any module App.tsx imports.
 *
 * The harness compiles the real entry point with the SHIPPED TWO-STAGE
 * pipeline — babel-preset-expo under Metro's caller flags with
 * `supportsStaticESM: true` (Expo sets `experimentalImportSupport: true`),
 * then Metro's own `importExportPlugin` for the CommonJS lowering — and
 * records module-evaluation order; see `helpers/w312BootSandbox.ts` for why a
 * plain `require('../index')` under ts-jest would be green and prove nothing.
 *
 * Assertions are on RECORDED ORDER, never on call counts: both things do
 * happen today, so counts are green — the defect is purely ordinal.
 *
 * HONEST LIMIT (inherited from the unit spec, narrowed by measurement): this
 * verifies module-evaluation order under the same Babel transform Metro uses,
 * driven by a sandbox `require` rather than by Metro's own runtime. It is not
 * a device boot. The on-device check belongs in the post-OTA walkthrough:
 * force a pinning failure on a release build and confirm the "running
 * unpinned" event arrives in Sentry.
 */

import * as fs from 'fs';
import * as path from 'path';

import {
  APP_ROOT,
  API_FILE,
  APP_FILE,
  AUTH_FILE,
  BOOTSTRAP_FILE,
  ENTRY,
  SENTRY_FILE,
  makeStub,
  resolveLocal,
  runBoot,
} from './helpers/w312BootSandbox';

const MARK_SENTRY = 'initSentry()';
const MARK_API = 'api.ts module body';

describe('W3-12 — Sentry is armed before the module graph (shipped Metro pipeline)', () => {
  const order: string[] = [];
  let emitted: Record<string, string>;

  beforeAll(() => {
    emitted = runBoot({
      executable: [ENTRY, APP_FILE, AUTH_FILE, BOOTSTRAP_FILE],
      localOverrides: {
        // Reaching this require IS the moment api.ts's module body would
        // run, so the marker is recorded here; the body itself is stubbed
        // (nothing in it is needed to establish ordering).
        [API_FILE]: () => {
          order.push(MARK_API);
          return makeStub();
        },
        [SENTRY_FILE]: () =>
          new Proxy(
            {},
            {
              get(_t, prop) {
                if (prop === '__esModule') return true;
                if (prop === 'initSentry') {
                  return () => {
                    order.push(MARK_SENTRY);
                  };
                }
                if (typeof prop === 'symbol') return undefined;
                return makeStub();
              },
            },
          ),
      },
    }).emitted;
  });

  it('the harness compiles CJS and the entry point reaches BOTH markers', () => {
    // Falsifier for the ordering tests below. If the transform silently
    // stayed ESM, or a stub / renamed path dropped either module out of the
    // boot chain, this fails FIRST — so an ordering failure below is known
    // not to be a wiring artifact.
    //
    // GREEN-PHASE RE-ANCHOR (W3-12): the arming side was originally anchored
    // on `App.tsx` requiring `./src/services/sentry`, because that is where
    // the RED-phase code armed Sentry. Removing that call from App.tsx is the
    // fix, so that exact string is gone by construction and the assertion had
    // to move to where the arming now happens — the entry point's own emitted
    // CJS. The falsifier is not weakened: it still proves (i) index.ts was
    // compiled to CJS and really requires the bootstrap, (ii) App.tsx was
    // compiled to CJS and really requires authService (the path to api.ts),
    // and (iii) both order markers were actually recorded.
    // Quote-agnostic: Metro's importExportPlugin emits single-quoted requires,
    // Babel's own commonjs transform emits double-quoted ones. The claim is
    // "the emitted CJS really requires this module", not "in these quotes".
    expect(emitted['index.ts']).toMatch(/require\(['"]\.\/src\/services\/sentryBootstrap['"]\)/);
    expect(emitted['App.tsx']).toMatch(/require\(['"]\.\/src\/services\/authService['"]\)/);
    expect(order).toContain(MARK_SENTRY);
    expect(order).toContain(MARK_API);
  });

  it('runs initSentry() BEFORE api.ts module body (RECORDED ORDER, not counts)', () => {
    // RED today: the recorded order is ['api.ts module body', 'initSentry()'].
    const sentryAt = order.indexOf(MARK_SENTRY);
    const apiAt = order.indexOf(MARK_API);
    expect(sentryAt).toBeGreaterThanOrEqual(0);
    expect(apiAt).toBeGreaterThanOrEqual(0);
    expect(sentryAt).toBeLessThan(apiAt);
  });

  it('arms Sentry as the FIRST recorded boot side effect', () => {
    // Same claim stated as the whole recorded sequence, so a failure names
    // the actual boot order instead of two integers. Stated positionally so
    // that merely moving api.ts later in App.tsx's import list — rather than
    // arming Sentry ahead of the graph — does not satisfy the unit.
    expect(order).toEqual([MARK_SENTRY, MARK_API]);
  });
});

describe('W3-12 — sentryBootstrap import-graph pin', () => {
  // Static assertion over the bootstrap module's own import list. This is
  // what stops a future edit from silently re-breaking the order: if
  // sentryBootstrap.ts ever reaches services/api — directly or transitively —
  // it recreates the exact problem it exists to solve.
  //
  // RED today: the module does not exist yet.
  const SRC_ROOT = path.join(APP_ROOT, 'src');

  function localImportsOf(file: string): string[] {
    const src = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
    const specs: string[] = [];
    const re = /(?:\bfrom|\brequire\(|\bimport)\s*['"](\.[^'"]+)['"]/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(src)) !== null) specs.push(m[1]);
    return specs;
  }

  function transitiveLocalGraph(entry: string): string[] {
    const seen = new Set<string>();
    const stack = [entry];
    while (stack.length) {
      const file = stack.pop() as string;
      if (seen.has(file)) continue;
      seen.add(file);
      for (const spec of localImportsOf(file)) {
        const resolved = resolveLocal(file, spec);
        if (resolved && !seen.has(resolved)) stack.push(resolved);
      }
    }
    seen.delete(entry);
    return [...seen];
  }

  it('src/services/sentryBootstrap.ts exists', () => {
    expect(fs.existsSync(BOOTSTRAP_FILE)).toBe(true);
  });

  it('sentryBootstrap.ts never reaches services/api, even transitively', () => {
    expect(fs.existsSync(BOOTSTRAP_FILE)).toBe(true);
    const graph = transitiveLocalGraph(BOOTSTRAP_FILE).map((f) =>
      path.relative(SRC_ROOT, f).replace(/\\/g, '/'),
    );
    expect(graph).not.toContain('services/api.ts');
    expect(graph.filter((f) => /(^|\/)api\.tsx?$/.test(f))).toEqual([]);
  });

  it('index.ts imports the bootstrap ahead of ./App', () => {
    const src = fs.readFileSync(ENTRY, 'utf8').replace(/\r\n/g, '\n');
    const bootstrapAt = src.search(/['"][^'"]*sentryBootstrap['"]/);
    const appAt = src.search(/['"]\.\/App['"]/);
    expect(bootstrapAt).toBeGreaterThanOrEqual(0);
    expect(appAt).toBeGreaterThanOrEqual(0);
    expect(bootstrapAt).toBeLessThan(appAt);
  });
});
