/**
 * W3-12 boot sandbox — shared harness for the two red tests.
 *
 * NOT a test file (jest's `testMatch` only collects `*.test.ts(x)`).
 *
 * WHY THIS EXISTS. This repo's jest runs ts-jest, and TypeScript's CommonJS
 * emit does NOT hoist requires — it emits each `require()` in place, in
 * source order. Under that transform `initSentry()` at App.tsx:10 runs
 * BEFORE the line-74 import of authService, so a plain `require('../index')`
 * test is GREEN today and proves nothing. Metro bundles the app with
 * `babel-preset-expo`, whose CJS transform hoists every require above the
 * module body (babel.config.js's own header notes "jest never loads this
 * file (the test runner is ts-jest, not babel)").
 *
 * So this harness compiles the REAL entry point and the real modules on the
 * boot chain with the SHIPPED TWO-STAGE pipeline (babel-preset-expo under
 * Metro's caller
 * flags) and executes them in a sandbox whose `require` records what happens
 * in what order. Modules outside the chain under test are stubbed; each
 * suite asserts first that the markers it cares about were actually reached,
 * so a stub or a renamed path can never be mistaken for an ordering failure.
 */
import * as fs from 'fs';
import * as path from 'path';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const babel = require('@babel/core');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const importExportPlugin = require('metro-transform-plugins').importExportPlugin;

export const APP_ROOT = path.resolve(__dirname, '../..');
export const ENTRY = path.join(APP_ROOT, 'index.ts');
export const APP_FILE = path.join(APP_ROOT, 'App.tsx');
export const AUTH_FILE = path.join(APP_ROOT, 'src', 'services', 'authService.ts');
export const API_FILE = path.join(APP_ROOT, 'src', 'services', 'api.ts');
export const SENTRY_FILE = path.join(APP_ROOT, 'src', 'services', 'sentry.ts');
export const PINNING_FILE = path.join(APP_ROOT, 'src', 'services', 'certificatePinning.ts');
export const BOOTSTRAP_FILE = path.join(APP_ROOT, 'src', 'services', 'sentryBootstrap.ts');

/**
 * THE REAL TWO-STAGE METRO PIPELINE (Fable review, W3-12).
 *
 * An earlier version of this harness ran babel-preset-expo with
 * `supportsStaticESM: false` and called that "the shipped transform". It is
 * not. `@expo/metro-config` sets `experimentalImportSupport: true`
 * (ExpoMetroConfig.js:321) and its babel-transformer derives
 * `supportsStaticESM: options.experimentalImportSupport`
 * (babel-transformer.js:78) — so on device Babel is asked to LEAVE the module
 * as ESM, and Metro's own `importExportPlugin` does the CommonJS lowering.
 *
 * Measuring a different transform and claiming it is the shipped one is the
 * exact mistake that produced this unit's original (green, worthless) test, so
 * it is not repeated here: both stages are run, in order, as Metro runs them.
 *
 * `configFile: false` is deliberate — the project's own babel.config.js
 * plugins (lucide splitter, production console-strip, reanimated) rewrite
 * bodies and imports but cannot MOVE a module-level require, so they cannot
 * affect evaluation order. That is an argument, not a measurement, and it is
 * recorded here as such.
 */
export function emitCjs(file: string): string {
  // Stage 1 — what Metro actually asks babel-preset-expo for. ESM is preserved.
  const stage1 = babel.transformFileSync(file, {
    cwd: APP_ROOT,
    filename: file,
    configFile: false,
    babelrc: false,
    presets: ['babel-preset-expo'],
    caller: {
      name: 'metro',
      supportsStaticESM: true,
      supportsDynamicImport: true,
      platform: 'ios',
      isDev: false,
    },
  });

  // Stage 2 — Metro's own ESM -> CJS lowering, the step that decides order.
  const stage2 = babel.transform(stage1.code as string, {
    cwd: APP_ROOT,
    filename: file,
    configFile: false,
    babelrc: false,
    // The same options metro-transform-worker passes when
    // experimentalImportSupport is on (metro-transform-worker/src/index.js:150-157).
    // The two identifier names are only helper bindings; they cannot affect the
    // require ORDER these suites measure, but they are required or the plugin throws.
    plugins: [[importExportPlugin, { importAll: '_$$_IMPORT_ALL', importDefault: '_$$_IMPORT_DEFAULT', resolve: false }]],
  });

  return stage2.code as string;
}

/** A lazily-deep, callable stub standing in for modules outside the chain. */
export function makeStub(): any {
  const fn: any = function stub() {
    return makeStub();
  };
  return new Proxy(fn, {
    get(_target, prop) {
      if (prop === '__esModule') return true;
      if (typeof prop === 'symbol') return undefined;
      return makeStub();
    },
    apply() {
      return makeStub();
    },
    construct() {
      return makeStub();
    },
  });
}

export function resolveLocal(fromFile: string, spec: string): string | null {
  const base = path.resolve(path.dirname(fromFile), spec);
  const candidates = [
    base,
    `${base}.ts`,
    `${base}.tsx`,
    `${base}.js`,
    path.join(base, 'index.ts'),
    path.join(base, 'index.tsx'),
    path.join(base, 'index.js'),
  ];
  for (const cand of candidates) {
    if (fs.existsSync(cand) && fs.statSync(cand).isFile()) return cand;
  }
  return null;
}

export interface BootOptions {
  /** Local files whose real module body should be EXECUTED, not stubbed. */
  executable: string[];
  /** Local files whose require should be intercepted (body never executed). */
  localOverrides?: Record<string, () => any>;
  /** Bare package specifiers to intercept. Anything else is stubbed. */
  bareOverrides?: Record<string, () => any>;
}

export interface BootRun {
  /** Emitted CJS keyed by app-root-relative path — evidence the transform ran. */
  emitted: Record<string, string>;
}

/**
 * Compiles + executes the real `index.ts` boot chain under the shipped two-stage
 * pipeline. HONEST LIMIT: this is Metro's TRANSFORM, driven by a sandbox
 * `require` — Metro's own runtime (module registry, `__d`/`__r`, inline
 * requires) is NOT exercised, so this is still not a device boot. The post-OTA
 * on-device check remains a hard gate.
 */
export function runBoot(options: BootOptions): BootRun {
  const emitted: Record<string, string> = {};
  const registry = new Map<string, any>();
  const executable = new Set(options.executable.filter((f) => fs.existsSync(f)));
  const localOverrides = options.localOverrides ?? {};
  const bareOverrides = options.bareOverrides ?? {};

  function load(file: string): any {
    if (registry.has(file)) return registry.get(file);
    const moduleObj = { exports: {} as any };
    registry.set(file, moduleObj.exports);

    const code = emitCjs(file);
    emitted[path.relative(APP_ROOT, file).replace(/\\/g, '/')] = code;

    const sandboxRequire = (spec: string): any => {
      if (spec.startsWith('.')) {
        const resolved = resolveLocal(file, spec);
        if (resolved && localOverrides[resolved]) {
          // CACHE the override, exactly as a real module registry does
          // (Fable review, W3-12). A module body runs ONCE on device — Metro
          // caches by module id — so an override standing in for one must
          // fire once too. Uncached, a module required from two places
          // recorded its marker twice and the recorded boot sequence gained a
          // phantom entry that had nothing to do with ordering.
          if (!registry.has(resolved)) registry.set(resolved, localOverrides[resolved]());
          return registry.get(resolved);
        }
        if (resolved && executable.has(resolved)) return load(resolved);
        return makeStub();
      }
      if (bareOverrides[spec]) return bareOverrides[spec]();
      // Babel's own runtime helpers must be REAL or the emitted interop
      // wrappers misbehave. Every other package is stubbed.
      if (spec.startsWith('@babel/runtime')) {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        return require(spec);
      }
      return makeStub();
    };

    // Metro's ESM interop helpers. `importExportPlugin` emits calls to these
    // two globals (they are named by the `importAll` / `importDefault` options
    // metro-transform-worker passes it), and on device Metro's own require
    // polyfill provides them. The sandbox has to supply them or every emitted
    // module throws ReferenceError before it can record anything.
    const importDefault = (spec: string) => {
      const m: any = sandboxRequire(spec);
      return m && m.__esModule ? m.default : m;
    };
    const importAll = (spec: string) => {
      const m: any = sandboxRequire(spec);
      if (m && m.__esModule) return m;
      return { ...(m as object), default: m };
    };

    const factory = new Function(
      'require',
      'module',
      'exports',
      '__filename',
      '__dirname',
      '__DEV__',
      '_$$_IMPORT_DEFAULT',
      '_$$_IMPORT_ALL',
      code,
    );
    factory(
      sandboxRequire,
      moduleObj,
      moduleObj.exports,
      file,
      path.dirname(file),
      false,
      importDefault,
      importAll,
    );
    registry.set(file, moduleObj.exports);
    return moduleObj.exports;
  }

  load(ENTRY);
  return { emitted };
}
