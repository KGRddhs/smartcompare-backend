const fs = require('fs');
const path = require('path');

/**
 * Production `console.*` strip (M13-55).
 *
 * Functionally equivalent to babel-plugin-transform-remove-console, but
 * implemented inline so we do NOT add an npm dependency: the committed
 * package-lock.json can't be regenerated in the CI/build environment without
 * a network install, and desyncing package.json from the lock would break
 * `npm ci`. This local plugin needs no lockfile change.
 *
 * It removes standalone `console.*(...)` STATEMENTS from PRODUCTION bundles
 * only (NODE_ENV/BABEL_ENV === 'production'); dev keeps them, and jest never
 * loads this file (the test runner is ts-jest, not babel). Belt-and-braces
 * with the `if (__DEV__)` guards in authService.ts — a diagnostic that ever
 * slips past a guard still never ships a token head to logcat / the iOS
 * unified log in a release build. It only touches console calls that stand
 * alone as expression statements, so it can never change the value of an
 * expression that happens to embed a console call.
 */
function removeConsolePlugin() {
  return {
    name: 'qaren-remove-console-production',
    visitor: {
      ExpressionStatement(nodePath) {
        const expr = nodePath.node.expression;
        if (
          expr &&
          expr.type === 'CallExpression' &&
          expr.callee &&
          expr.callee.type === 'MemberExpression' &&
          expr.callee.object &&
          expr.callee.object.type === 'Identifier' &&
          expr.callee.object.name === 'console'
        ) {
          nodePath.remove();
        }
      },
    },
  };
}

/**
 * Lucide barrel-import splitter (B1).
 *
 * 34 source files do `import { Camera, Star } from 'lucide-react-native'`.
 * That specifier resolves to `dist/esm/lucide-react-native.mjs`, which
 * re-exports every one of the 1,703 icon modules the package ships, and
 * Metro/Hermes keeps the whole set: ~1.2MB of a ~9.7MB JS graph for the 68
 * icons the app actually renders. Neither obvious fix works on
 * lucide-react-native@1.14.0 — its `exports` map has exactly "." and
 * "./icons", so `lucide-react-native/icons/<kebab>` and
 * `lucide-react-native/dist/esm/icons/<kebab>.mjs` are both blocked as bare
 * package subpaths, and there is no icons/ directory at the package root.
 *
 * So we rewrite at compile time instead. A *relative file path* is not a
 * package specifier, so the exports map never applies to it:
 *
 *   import { Camera } from 'lucide-react-native';
 *   -> import Camera from '../../node_modules/lucide-react-native/dist/esm/icons/camera.mjs';
 *
 * The name -> file map is parsed out of the package's own barrel
 * (`dist/esm/lucide-react-native.mjs`), so it is always in sync with the
 * installed version and covers every alias lucide exports (`AlertCircle` ->
 * `circle-alert.mjs`, `Home` -> `house.mjs`, `BarChart3` -> `chart-column.mjs`,
 * the `*Icon` and `Lucide*` aliases, ...). Anything the barrel does NOT map to
 * a real icon file (`createLucideIcon`, `Icon`, type-only imports, a future
 * rename) is LEFT ON THE ORIGINAL BARREL IMPORT rather than guessed at, so a
 * miss costs bundle bytes, never a runtime crash.
 *
 * Not applied under `test`: jest maps the bare `lucide-react-native`
 * specifier to `__mocks__/lucide-react-native.ts`, and rewriting the import to
 * a real file path would walk straight past that mock.
 *
 * No new npm dependency — same reasoning as removeConsolePlugin above.
 */
const LUCIDE_PACKAGE = 'lucide-react-native';

let lucideIconMap; // undefined = not built yet, null = unavailable

function lucideEsmDir() {
  // Prefer the in-project node_modules so the emitted path stays inside the
  // Metro project root; fall back to Node resolution for hoisted installs.
  const local = path.join(__dirname, 'node_modules', LUCIDE_PACKAGE, 'dist', 'esm');
  if (fs.existsSync(path.join(local, 'lucide-react-native.mjs'))) return local;
  try {
    // "." resolves to dist/cjs/lucide-react-native.js via the exports map.
    return path.join(path.dirname(require.resolve(LUCIDE_PACKAGE)), '..', 'esm');
  } catch {
    return null;
  }
}

function buildLucideIconMap() {
  if (lucideIconMap !== undefined) return lucideIconMap;
  lucideIconMap = null;

  const esmDir = lucideEsmDir();
  if (!esmDir) return lucideIconMap;

  let barrel;
  try {
    barrel = fs.readFileSync(path.join(esmDir, 'lucide-react-native.mjs'), 'utf8');
  } catch {
    return lucideIconMap;
  }

  const map = Object.create(null);
  // export { default as Camera, default as CameraIcon } from './icons/camera.mjs';
  const reExport = /export\s*\{([^}]*)\}\s*from\s*'\.\/(icons\/[^']+)'/g;
  let match;
  while ((match = reExport.exec(barrel)) !== null) {
    const file = path.join(esmDir, match[2]);
    if (!fs.existsSync(file)) continue;
    for (const raw of match[1].split(',')) {
      const named = /^default\s+as\s+([A-Za-z_$][\w$]*)$/.exec(raw.trim());
      if (named) map[named[1]] = file;
    }
  }

  if (Object.keys(map).length > 0) lucideIconMap = map;
  return lucideIconMap;
}

function lucideIconImportsPlugin({ types: t }) {
  return {
    name: 'qaren-lucide-icon-imports',
    visitor: {
      ImportDeclaration(nodePath, state) {
        const node = nodePath.node;
        if (!node.source || node.source.value !== LUCIDE_PACKAGE) return;
        if (node.importKind === 'type' || node.importKind === 'typeof') return;
        if (node.specifiers.length === 0) return; // side-effect import

        const filename = state.file.opts.filename;
        if (!filename) return;

        const map = buildLucideIconMap();
        if (!map) return;

        const fromDir = path.dirname(filename);
        const rewritten = [];
        const kept = [];

        for (const spec of node.specifiers) {
          const iconFile =
            spec.type === 'ImportSpecifier' &&
            spec.importKind !== 'type' &&
            spec.importKind !== 'typeof' &&
            spec.imported.type === 'Identifier'
              ? map[spec.imported.name]
              : undefined;

          if (!iconFile) {
            kept.push(spec);
            continue;
          }

          let relative = path.relative(fromDir, iconFile).split(path.sep).join('/');
          if (!relative.startsWith('.')) relative = './' + relative;
          rewritten.push(
            t.importDeclaration(
              [t.importDefaultSpecifier(t.identifier(spec.local.name))],
              t.stringLiteral(relative)
            )
          );
        }

        if (rewritten.length === 0) return;

        if (kept.length > 0) {
          node.specifiers = kept;
          nodePath.insertAfter(rewritten);
        } else {
          nodePath.replaceWithMultiple(rewritten);
        }
      },
    },
  };
}

module.exports = function (api) {
  // Cache keyed on the env vars the config reads, so the production-only strip
  // and the test-only lucide opt-out below are recomputed when the env changes
  // (a plain api.cache(true) freezes the first env seen).
  api.cache.using(() => process.env.NODE_ENV);
  api.cache.using(() => process.env.BABEL_ENV);

  const isProduction =
    process.env.NODE_ENV === 'production' ||
    process.env.BABEL_ENV === 'production';
  const isTest = process.env.NODE_ENV === 'test' || process.env.BABEL_ENV === 'test';

  const plugins = [];
  if (isProduction) {
    plugins.push(removeConsolePlugin);
  }
  if (!isTest) {
    plugins.push(lucideIconImportsPlugin);
  }
  // react-native-reanimated/plugin MUST remain last.
  plugins.push('react-native-reanimated/plugin');

  return {
    presets: ['babel-preset-expo'],
    plugins,
  };
};

// Exported for the B1 regression suite (__tests__/babel.lucideIcons.test.ts).
module.exports.lucideIconImportsPlugin = lucideIconImportsPlugin;
module.exports.buildLucideIconMap = buildLucideIconMap;
