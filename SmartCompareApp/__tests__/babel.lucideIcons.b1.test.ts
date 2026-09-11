/**
 * B1 — lucide barrel-import splitter (babel.config.js).
 *
 * 35 source files (34 under src/ + App.tsx) did
 * `import { Camera, Star } from 'lucide-react-native'`.
 * That bare specifier resolves to the package barrel, which re-exports all
 * 1,703 icon modules lucide ships, so Metro kept every one of them for the 68
 * icons the app renders (measured: 8,259,431 B -> 6,510,149 B of iOS Hermes
 * bytecode, 3,832 -> 2,192 modules, once the inline plugin landed).
 *
 * lucide-react-native@1.14.0's `exports` map has exactly "." and "./icons".
 * `lucide-react-native/icons/<kebab>` therefore resolves nowhere: Metro throws
 * FailedToResolveNameError, jest MODULE_NOT_FOUND, tsc leaves it unresolved.
 * `lucide-react-native/dist/esm/icons/<kebab>.mjs` is refused by jest and tsc
 * the same way — but NOT by Metro: metro-resolver 0.83.3 catches
 * PackagePathNotExportedError, logs a warning and falls back to file-based
 * resolution (measured; `resolve.js:343-351` then `:359`). The inline babel
 * plugin sidesteps all of it by rewriting each named icon import to a
 * RELATIVE FILE PATH instead — a file path is not a package specifier, so the
 * exports map never applies and all three resolvers agree.
 *
 * What this suite pins:
 *   1. The plugin is wired into the config for dev + production, is OFF under
 *      `test` (jest maps the bare specifier to __mocks__/lucide-react-native.ts;
 *      a rewrite to a real file path would walk past that mock), and the
 *      reanimated plugin still runs LAST in every env.
 *   2. The name -> file map resolves lucide's renames/aliases from the barrel
 *      itself (Home -> house.mjs, AlertCircle -> circle-alert.mjs,
 *      BarChart3 -> chart-column.mjs) rather than guessing kebab-case.
 *   3. Running the plugin over EVERY real source file that imports lucide
 *      emits only paths that exist on disk, and rewrites every icon it found —
 *      a wrong or missing path is a runtime crash on that screen, so this is
 *      the load-bearing assertion.
 *   4. Type-only imports are LEFT on the barrel rather than guessed at (the
 *      TS transform erases them downstream, so they cost nothing; rewriting
 *      one to a default import would be a crash).
 *   5. B1-FENCES — the barrel fence: the ONLY lucide imports in the bundled
 *      sources are named VALUE specifiers the map resolves to an icon file.
 *      This used to be a blessed escape hatch ("a miss costs bytes, never a
 *      crash"), but one surviving barrel import re-adds all 1,703 icon
 *      modules, i.e. the whole 1.75 MB win, with every other test green and
 *      no artifact-size assertion anywhere in the repo to notice. Checked
 *      when this fence landed: src/ + App.tsx + index.ts contain 68 value
 *      imports, 0 type-only imports and 0 `createLucideIcon` imports, so
 *      neither is excepted here — a future one has to face this fence and be
 *      a deliberate decision.
 *      W3-9 widened that fence's REACH and moved it to
 *      `__tests__/helpers/lucideFence.ts`: `require('lucide-react-native')`,
 *      a dynamic `import('lucide-react-native')`, `import x = require(...)`
 *      and `.js/.jsx/.mjs/.cjs` sources under src/ are fenced too. Each of
 *      them was invisible before — the classifier read `node.source` on
 *      top-level statements only, and the walk matched `/\.tsx?$/` only —
 *      and each one re-adds all 1,703 icon modules under Metro with every
 *      required CI check green.
 *   6. B1-FENCES — the mock fence: every one of those imported identifiers is
 *      a callable export of __mocks__/lucide-react-native.ts. B1 fenced the
 *      production list and not this one, and the two had already drifted
 *      (`Plus`, `TrendingUp` — both rendered, both absent from the mock, both
 *      `undefined` under jest, which tears the whole tree down).
 */

import * as fs from 'fs';
import * as path from 'path';

import { lucideRefs, sourceFiles, type LucideRef } from './helpers/lucideFence';

const babel = require('@babel/core');
const babelConfig = require('../babel.config.js');

const APP_ROOT = path.resolve(__dirname, '..');
const ICON_PATH_RE = /lucide-react-native\/dist\/esm\/icons\//;

function fakeApi() {
  return { cache: { using: () => undefined } };
}

function configFor(env: string) {
  // `''` stands in for "unset" — babel.config.js only ever compares these to
  // 'production' / 'test', so an empty string is indistinguishable from absent.
  const prevNode = process.env.NODE_ENV ?? '';
  const prevBabel = process.env.BABEL_ENV ?? '';
  process.env.NODE_ENV = env;
  process.env.BABEL_ENV = '';
  try {
    return babelConfig(fakeApi());
  } finally {
    process.env.NODE_ENV = prevNode;
    process.env.BABEL_ENV = prevBabel;
  }
}

function transform(filename: string, code: string): string {
  const out = babel.transformSync(code, {
    filename,
    configFile: false,
    babelrc: false,
    sourceType: 'module',
    plugins: [babelConfig.lucideIconImportsPlugin],
    parserOpts: { plugins: ['typescript', 'jsx'] },
  });
  return out.code as string;
}

function rel(file: string): string {
  return path.relative(APP_ROOT, file).split(path.sep).join('/');
}

/**
 * Value identifiers imported from the lucide barrel by `code`, as
 * [exportedName, localName] (they differ for `import { X as XIcon }`).
 */
function barrelValueImports(filename: string, code: string): Array<[string, string]> {
  return lucideRefs(filename, code)
    .filter((ref) => ref.shape === 'value')
    .map((ref) => [ref.exported, ref.local] as [string, string]);
}

/** Every value identifier the bundled sources import from the barrel. */
function importedIconNames(): Set<string> {
  const imported = new Set<string>();
  for (const file of sourceFiles(APP_ROOT)) {
    for (const [exported] of barrelValueImports(file, fs.readFileSync(file, 'utf8'))) {
      imported.add(exported);
    }
  }
  return imported;
}

/** Relative default imports the plugin emitted, as [local, resolvedAbsPath]. */
function emittedIconImports(filename: string, code: string): Array<[string, string]> {
  const out: Array<[string, string]> = [];
  const re = /import\s+(\w+)\s+from\s+["']([^"']+)["']/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(code)) !== null) {
    if (!ICON_PATH_RE.test(m[2])) continue;
    out.push([m[1], path.resolve(path.dirname(filename), m[2])]);
  }
  return out;
}

describe('B1 — lucide icon imports are split out of the barrel', () => {
  it('wires the plugin into dev + production and leaves it OFF under test', () => {
    const plugin = babelConfig.lucideIconImportsPlugin;
    expect(typeof plugin).toBe('function');

    expect(configFor('production').plugins).toContain(plugin);
    expect(configFor('development').plugins).toContain(plugin);
    // Under `test` jest's moduleNameMapper must keep resolving the bare
    // specifier to __mocks__/lucide-react-native.ts.
    expect(configFor('test').plugins).not.toContain(plugin);
  });

  it('keeps react-native-reanimated/plugin last in every env', () => {
    for (const env of ['production', 'development', 'test']) {
      const plugins = configFor(env).plugins;
      expect(plugins[plugins.length - 1]).toBe('react-native-reanimated/plugin');
    }
  });

  it('resolves lucide v1 renames from the barrel instead of guessing kebab-case', () => {
    const map = babelConfig.buildLucideIconMap();
    expect(map).toBeTruthy();
    expect(Object.keys(map).length).toBeGreaterThan(1000);

    // Alias-aware: lucide v1 renamed these, and only the barrel knows.
    expect(path.basename(map.Home)).toBe('house.mjs');
    expect(path.basename(map.AlertCircle)).toBe('circle-alert.mjs');
    expect(path.basename(map.BarChart3)).toBe('chart-column.mjs');
    expect(path.basename(map.Camera)).toBe('camera.mjs');
  });

  it('fences the barrel: the only lucide imports are icon names the map resolves', () => {
    const map = babelConfig.buildLucideIconMap();
    expect(map).toBeTruthy();

    const refs = sourceFiles(APP_ROOT).flatMap((file) =>
      lucideRefs(file, fs.readFileSync(file, 'utf8'))
    );
    const label = (ref: LucideRef) => `${rel(ref.file)}: ${ref.shape} '${ref.exported}'`;

    // Positive control: the walk really finds the imports it is fencing.
    const values = refs.filter((ref) => ref.shape === 'value');
    expect(values.length).toBeGreaterThan(50);

    // Anything that is not a named import — a default/namespace import, a
    // side-effect import, a re-export, a blocked subpath — pulls the barrel
    // in wholesale and re-adds all 1,703 icon modules (~1.75 MB).
    expect(refs.filter((ref) => !['value', 'type'].includes(ref.shape)).map(label)).toEqual([]);

    // …and so does ONE surviving value specifier the plugin cannot map to an
    // icon file (`createLucideIcon`, `Icon`, a non-`type` import of a type, a
    // future rename). The plugin deliberately leaves those on the barrel
    // rather than guessing — a miss must cost bytes, never a crash — so this
    // is the only thing standing between the 1.75 MB win and a silent
    // reversal: CI runs no bundle step and the repo has no size assertion.
    expect(values.filter((ref) => !map[ref.exported]).map(label)).toEqual([]);

    const nonexistent = values.filter((ref) => !fs.existsSync(map[ref.exported])).map(label);
    expect(nonexistent).toEqual([]);
  });

  it('rewrites every real source file to icon paths that exist on disk', () => {
    const touched: string[] = [];

    for (const file of sourceFiles(APP_ROOT)) {
      const code = fs.readFileSync(file, 'utf8');
      const wanted = barrelValueImports(file, code);
      if (wanted.length === 0) continue;
      touched.push(file);

      const output = transform(file, code);
      const emitted = emittedIconImports(file, output);

      // Every icon identifier the file imported is now a direct file import…
      const locals = emitted.map(([local]) => local);
      for (const [exported, local] of wanted) {
        expect([exported, locals.includes(local)]).toEqual([exported, true]);
      }
      // …and every emitted path points at a file that is really there.
      for (const [local, resolved] of emitted) {
        expect([local, fs.existsSync(resolved)]).toEqual([local, true]);
      }
    }

    // 35 barrel sites when B1 landed (34 under src/ + App.tsx; the header and
    // babel.config.js both say "34", which undercounts App.tsx by one).
    // Guard against a silent regression to 0.
    expect(touched.length).toBeGreaterThanOrEqual(30);
  });

  it('leaves type-only imports on the barrel and still splits the icons beside them', () => {
    const filename = path.join(APP_ROOT, 'src', 'screens', 'Sample.tsx');
    const output = transform(
      filename,
      [
        "import { Camera, Star as Rating, type LucideIcon } from 'lucide-react-native';",
        "import type { LucideProps } from 'lucide-react-native';",
        'export const used: LucideIcon[] = [Camera, Rating];',
        'export type Props = LucideProps;',
      ].join('\n')
    );

    expect(output).toMatch(/import Camera from "[^"]*icons\/camera\.mjs"/);
    expect(output).toMatch(/import Rating from "[^"]*icons\/star\.mjs"/);
    // A type-only name is erased downstream by the TS transform, so leaving it
    // on the barrel costs no bytes — and rewriting it to a default import
    // would be a crash, since there is no runtime export behind it. Non-icon
    // VALUE imports get no such pass any more: the barrel fence above forbids
    // them outright.
    expect(output).toMatch(/import\s*\{\s*type\s+LucideIcon\s*\}\s*from\s*['"]lucide-react-native['"]/);
    expect(output).toMatch(/import\s+type\s*\{\s*LucideProps\s*\}\s*from\s*['"]lucide-react-native['"]/);
  });

  it('exports every icon the app imports from the jest lucide mock', () => {
    // jest.config.js maps '^lucide-react-native$' to __mocks__/lucide-react-native.ts,
    // so this require is exactly what every other suite receives. A name that
    // is missing here comes back `undefined`, and React tears the whole tree
    // down the moment that branch renders.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mock = require('lucide-react-native') as Record<string, unknown>;
    const mockExports = Object.keys(mock).filter((name) => typeof mock[name] === 'function');
    expect(mockExports.length).toBeGreaterThan(50); // positive control

    const imported = importedIconNames();
    expect(imported.size).toBeGreaterThan(50); // positive control

    const missing = [...imported]
      .filter((name) => typeof mock[name] !== 'function')
      .sort();
    expect(missing).toEqual([]);
  });
});
