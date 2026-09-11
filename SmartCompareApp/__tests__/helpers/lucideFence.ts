/**
 * W3-9 / MB-STARTUP-BUNDLE-01 — the lucide barrel fence, extracted from
 * `__tests__/babel.lucideIcons.b1.test.ts` and widened.
 *
 * Not a `.test.` file on purpose: `jest.config.js:4` collects only
 * `**\/__tests__/**\/*.test.ts(x)`, so this module is imported, never run as a
 * suite. Its own self-test is `__tests__/helpers/lucideFence.test.ts`.
 *
 * Why it exists. B1 (`e3d9adb5`, PR #138) rewrites each named icon import off
 * the lucide barrel at compile time, which is worth 1,749,282 B of iOS Hermes
 * bytecode and 1,640 modules — and the only thing standing between that win
 * and a silent reversal is the jest fence, because CI runs no bundle step and
 * the repo has no artifact-size assertion. That fence had two measured holes:
 * it read `node.source` on `ast.program.body` only, and it walked `/\.tsx?$/`
 * only. So `require('lucide-react-native')`, `await import('lucide-react-native')`,
 * `import L = require('lucide-react-native')`, and any of those inside a
 * `.js/.jsx/.mjs/.cjs` file under `src/` (all four are Metro `sourceExts`)
 * were invisible to it — and equally invisible to the B1 plugin, which visits
 * `ImportDeclaration` only (`babel.config.js:130`). Under Metro every one of
 * those forms resolves to a full 1,703-icon barrel (the CJS barrel carries the
 * same 1,703 `require('./icons/…')` as the ESM one), so a single such site
 * restores the whole ~1.75 MB with every required CI check green: CI eslint
 * emits a non-blocking `@typescript-eslint/no-require-imports` WARNING for the
 * two require shapes and nothing at all for a dynamic import or a subpath, and
 * under jest the same specifier resolves to `__mocks__/lucide-react-native.ts`
 * so no other suite notices either.
 *
 * There are zero such sites today (measured 2026-09-11 at b63a8368), so this
 * is a latent hole, not a live regression.
 */

import * as fs from 'fs';
import * as path from 'path';

export const LUCIDE_PACKAGE = 'lucide-react-native';

/**
 * Metro's script `sourceExts` minus json/css — the extensions Metro will
 * actually parse as a module under `src/`. `metro.config.js` resolves to
 * `["ts","tsx","mjs","js","jsx","json","cjs","scss","sass","css"]` (read from
 * the live config, not from docs).
 */
const SOURCE_FILE_RE = /\.(tsx?|jsx?|mjs|cjs)$/;

/** Only the babel-parser fields this module reads; the parser itself is `any`. */
type ParsedNode = {
  type: string;
  source?: { value?: unknown } | null;
  importKind?: string | null;
  specifiers?: ParsedSpecifier[];
  callee?: { type?: string; name?: string };
  arguments?: ParsedNode[];
  value?: unknown;
  moduleReference?: { type?: string; expression?: { type?: string; value?: unknown } };
  id?: { name?: string };
};

type ParsedSpecifier = {
  type: string;
  importKind?: string | null;
  imported?: { type?: string; name?: string; value?: unknown };
  local: { name: string };
};

type ParsedFile = { program: { body: ParsedNode[] } };
type Visitor = Record<string, (nodePath: { node: ParsedNode }) => void>;

// `@babel/parser` and `@babel/traverse` are transitive deps of `@babel/core`,
// not direct entries in package.json, so they are required the way this suite
// already requires `@babel/core`. `@babel/traverse`'s CommonJS export is a
// NAMESPACE object — the walker is `.default` (measured on 7.29.0).
// eslint-disable-next-line @typescript-eslint/no-require-imports
const parser = require('@babel/parser') as {
  parse: (code: string, options: Record<string, unknown>) => ParsedFile;
};
// eslint-disable-next-line @typescript-eslint/no-require-imports
const traverse = (require('@babel/traverse') as {
  default: (ast: ParsedFile, visitor: Visitor) => void;
}).default;

/**
 * Every reference to the lucide package in `code`, classified by shape.
 *
 * AST, not a regex: a regex over source cannot tell `import type { X }` from
 * `import { X }`, cannot see the per-specifier `type` modifier, and happily
 * matches inside a comment or a string. Only `shape: 'value'` costs bundle
 * bytes; `'type'` is erased downstream by the TS transform and costs none.
 * EVERYTHING ELSE keeps the entire 1,703-module barrel alive.
 */
export type LucideRef = {
  file: string;
  shape:
    | 'value'
    | 'type'
    | 'default'
    | 'namespace'
    | 'side-effect'
    | 're-export'
    | 'subpath'
    | 'require'
    | 'dynamic-import';
  exported: string;
  local: string;
};

/**
 * Every `/\.(tsx?|jsx?|mjs|cjs)$/` file under `<root>/src`, plus the two
 * bundled entry files beside it (`App.tsx`, `index.ts`).
 *
 * `root` is a parameter so the self-test can sweep an `os.tmpdir()` fixture
 * instead of writing into the worktree. The root-level `.js` config files
 * (`babel.config.js`, `metro.config.js`, …) are deliberately NOT walked: they
 * are build config, not bundled sources.
 */
export function sourceFiles(root: string): string[] {
  const found: string[] = [];
  const walk = (dir: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (SOURCE_FILE_RE.test(entry.name)) found.push(full);
    }
  };
  walk(path.join(root, 'src'));
  found.push(path.join(root, 'App.tsx'));
  found.push(path.join(root, 'index.ts'));
  return found;
}

function isLucideSpecifier(source: unknown): source is string {
  return (
    typeof source === 'string' && new RegExp(`^${LUCIDE_PACKAGE}(/|$)`).test(source)
  );
}

/** The sole string-literal argument of a call, or undefined. */
function soleStringArgument(node: ParsedNode): unknown {
  const args = node.arguments ?? [];
  if (args.length !== 1 || args[0].type !== 'StringLiteral') return undefined;
  return args[0].value;
}

export function lucideRefs(filename: string, code: string): LucideRef[] {
  const ast = parser.parse(code, {
    sourceType: 'module',
    plugins: ['typescript', 'jsx'],
  });

  const refs: LucideRef[] = [];
  const push = (shape: LucideRef['shape'], exported: string, local: string) =>
    refs.push({ file: filename, shape, exported, local });

  /** `import`/`export … from` — the shapes the original fence already saw. */
  const declaration = (node: ParsedNode) => {
    const source = node.source?.value;
    if (!isLucideSpecifier(source)) return;
    // `lucide-react-native/<anything>` is UNRESOLVABLE under jest and tsc, and
    // under Metro it resolves with an "not listed in the exports" warning and a
    // file-based fallback — either way the B1 plugin never rewrites it, since
    // the plugin matches the bare specifier only.
    if (source !== LUCIDE_PACKAGE) {
      push('subpath', source, source);
      return;
    }
    // `export { Camera } from 'lucide-react-native'` / `export * from ...`.
    if (node.type !== 'ImportDeclaration') {
      push('re-export', source, source);
      return;
    }
    const specifiers = node.specifiers ?? [];
    if (specifiers.length === 0) {
      push('side-effect', source, source);
      return;
    }

    const declIsType = node.importKind === 'type' || node.importKind === 'typeof';
    for (const spec of specifiers) {
      if (spec.type === 'ImportDefaultSpecifier') {
        push('default', 'default', spec.local.name);
        continue;
      }
      if (spec.type === 'ImportNamespaceSpecifier') {
        push('namespace', '*', spec.local.name);
        continue;
      }
      const imported = spec.imported ?? {};
      const exported =
        imported.type === 'Identifier' ? String(imported.name) : String(imported.value);
      const isType =
        declIsType || spec.importKind === 'type' || spec.importKind === 'typeof';
      push(isType ? 'type' : 'value', exported, spec.local.name);
    }
  };

  traverse(ast, {
    ImportDeclaration: ({ node }) => declaration(node),
    ExportNamedDeclaration: ({ node }) => declaration(node),
    ExportAllDeclaration: ({ node }) => declaration(node),

    // `const L = require('lucide-react-native')` and
    // `await import('lucide-react-native')`, at ANY depth — neither is a
    // top-level declaration, so the original `ast.program.body` loop never
    // saw either one.
    CallExpression: ({ node }) => {
      const callee = node.callee ?? {};
      const isRequire = callee.type === 'Identifier' && callee.name === 'require';
      const isDynamicImport = callee.type === 'Import';
      if (!isRequire && !isDynamicImport) return;
      const source = soleStringArgument(node);
      if (!isLucideSpecifier(source)) return;
      push(isRequire ? 'require' : 'dynamic-import', source, source);
    },

    // The same dynamic import when the parser is given
    // `createImportExpressions: true`: the specifier moves to `.source` and
    // the node type changes. This module does not pass that option, but a
    // caller handing us a foreign AST shape must not open the hole again.
    ImportExpression: ({ node }) => {
      const source = node.source?.value;
      if (!isLucideSpecifier(source)) return;
      push('dynamic-import', source, source);
    },

    // `import L = require('lucide-react-native')`. Parses as its own node with
    // `node.source === undefined`, so the original loop skipped it silently.
    // The `import type L = require(...)` form carries `importKind: 'type'` and
    // is erased by the TS transform, so it costs no bytes and must classify
    // 'type' — otherwise the barrel fence reddens on a form that ships nothing.
    TSImportEqualsDeclaration: ({ node }) => {
      const reference = node.moduleReference ?? {};
      if (reference.type !== 'TSExternalModuleReference') return;
      const source = reference.expression?.value;
      if (!isLucideSpecifier(source)) return;
      const local = node.id?.name ?? source;
      push(node.importKind === 'type' ? 'type' : 'require', source, local);
    },
  });

  return refs;
}
