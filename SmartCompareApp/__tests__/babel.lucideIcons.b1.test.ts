/**
 * B1 — lucide barrel-import splitter (babel.config.js).
 *
 * 34 source files did `import { Camera, Star } from 'lucide-react-native'`.
 * That bare specifier resolves to the package barrel, which re-exports all
 * 1,703 icon modules lucide ships, so Metro kept every one of them for the 68
 * icons the app renders (measured: 8,259,431 B -> 6,510,149 B of iOS Hermes
 * bytecode, 3,832 -> 2,192 modules, once the inline plugin landed).
 *
 * lucide-react-native@1.14.0's `exports` map has exactly "." and "./icons",
 * so neither `lucide-react-native/icons/<kebab>` nor
 * `lucide-react-native/dist/esm/icons/<kebab>.mjs` resolves. The inline babel
 * plugin rewrites each named icon import to a RELATIVE FILE PATH instead — a
 * file path is not a package specifier, so the exports map never applies.
 *
 * What this suite pins:
 *   1. The plugin is wired into the config for dev + production, is OFF under
 *      `test` (jest maps the bare specifier to __mocks__/lucide-react-native.ts;
 *      a rewrite to a real file path would walk past that mock), and the
 *      reanimated plugin still runs LAST in every env.
 *   2. The name -> file map covers every identifier the app imports, including
 *      lucide's renames/aliases (Home -> house.mjs, AlertCircle ->
 *      circle-alert.mjs, BarChart3 -> chart-column.mjs).
 *   3. Running the plugin over EVERY real source file that imports lucide
 *      emits only paths that exist on disk, and rewrites every icon it found —
 *      a wrong or missing path is a runtime crash on that screen, so this is
 *      the load-bearing assertion.
 *   4. Non-icon named exports (`createLucideIcon`) and type-only imports are
 *      LEFT on the barrel rather than guessed at.
 */

import * as fs from 'fs';
import * as path from 'path';

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

/** Every .ts/.tsx under src/ plus App.tsx. */
function sourceFiles(): string[] {
  const found: string[] = [];
  const walk = (dir: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (/\.tsx?$/.test(entry.name)) found.push(full);
    }
  };
  walk(path.join(APP_ROOT, 'src'));
  found.push(path.join(APP_ROOT, 'App.tsx'));
  return found;
}

/**
 * Value identifiers imported from the lucide barrel by `code`, as
 * [exportedName, localName] (they differ for `import { X as XIcon }`).
 */
function barrelValueImports(code: string): Array<[string, string]> {
  const names: Array<[string, string]> = [];
  const re = /import\s+(type\s+)?\{([^}]*)\}\s+from\s+['"]lucide-react-native['"]/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(code)) !== null) {
    if (m[1]) continue; // `import type { ... }`
    for (const raw of m[2].split(',')) {
      const part = raw.replace(/\/\/.*/g, '').trim();
      if (!part || part.startsWith('type ')) continue;
      const [exported, local] = part.split(/\s+as\s+/).map((s) => s.trim());
      names.push([exported, local || exported]);
    }
  }
  return names;
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

  it('maps every identifier the app imports to an icon file that exists', () => {
    const map = babelConfig.buildLucideIconMap();
    expect(map).toBeTruthy();

    const imported = new Set<string>();
    for (const file of sourceFiles()) {
      for (const [exported] of barrelValueImports(fs.readFileSync(file, 'utf8'))) {
        imported.add(exported);
      }
    }
    expect(imported.size).toBeGreaterThan(50);

    const unmapped = [...imported].filter((name) => !map[name]);
    expect(unmapped).toEqual([]);

    const nonexistent = [...imported].filter((name) => !fs.existsSync(map[name]));
    expect(nonexistent).toEqual([]);

    // Alias-aware: lucide v1 renamed these, and only the barrel knows.
    expect(path.basename(map.Home)).toBe('house.mjs');
    expect(path.basename(map.AlertCircle)).toBe('circle-alert.mjs');
    expect(path.basename(map.BarChart3)).toBe('chart-column.mjs');
    expect(path.basename(map.Camera)).toBe('camera.mjs');
  });

  it('rewrites every real source file to icon paths that exist on disk', () => {
    const touched: string[] = [];

    for (const file of sourceFiles()) {
      const code = fs.readFileSync(file, 'utf8');
      const wanted = barrelValueImports(code);
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

    // 34 barrel sites when B1 landed; guard against a silent regression to 0.
    expect(touched.length).toBeGreaterThanOrEqual(30);
  });

  it('leaves non-icon and type-only lucide imports on the barrel', () => {
    const filename = path.join(APP_ROOT, 'src', 'screens', 'Sample.tsx');
    const output = transform(
      filename,
      [
        "import { Camera, Star as Rating } from 'lucide-react-native';",
        "import { createLucideIcon } from 'lucide-react-native';",
        "import type { LucideIcon } from 'lucide-react-native';",
        'export const used = [Camera, Rating, createLucideIcon];',
      ].join('\n')
    );

    expect(output).toMatch(/import Camera from "[^"]*icons\/camera\.mjs"/);
    expect(output).toMatch(/import Rating from "[^"]*icons\/star\.mjs"/);
    expect(output).toMatch(/import \{\s*createLucideIcon\s*\} from ['"]lucide-react-native['"]/);
    expect(output).toMatch(/import type \{\s*LucideIcon\s*\} from ['"]lucide-react-native['"]/);
  });
});
