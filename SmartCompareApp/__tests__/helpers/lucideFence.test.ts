/**
 * W3-9 / MB-STARTUP-BUNDLE-01 — self-test of the lucide barrel fence helper
 * (`__tests__/helpers/lucideFence.ts`), on synthetic source strings.
 *
 * The bundle defect itself is fixed on main by B1 (`e3d9adb5`, `8d8b9dc8`,
 * `cea9effa`; PR #138): the 35 barrel importers (34 under src/ + App.tsx) are
 * rewritten at compile time to 68 per-icon files, and
 * `babel.lucideIcons.b1.test.ts` "fences the barrel" so a default/namespace/
 * side-effect import, a re-export or a subpath cannot re-add the 1,703 icon
 * modules with CI green.
 *
 * That fence had two measured holes. Its `lucideRefs()` read only
 * `node.source` on `ast.program.body`, and its `sourceFiles()` walked only
 * `/\.tsx?$/`. So a `require('lucide-react-native')`, a dynamic
 * `import('lucide-react-native')`, an `import x = require(...)`, or any of
 * those in a `.js/.jsx/.mjs/.cjs` file under src/ (Metro's `sourceExts`) was
 * invisible to it — and equally invisible to the B1 plugin, which visits
 * `ImportDeclaration` only (babel.config.js:130). Under Metro every one of
 * those forms resolves to a full 1,703-icon barrel (the CJS barrel carries the
 * same 1,703 `require('./icons/…')` as the ESM one), so any single site
 * would silently restore the whole ~1.75 MB with every required CI check
 * green (CI eslint emits a non-blocking `no-require-imports` WARNING for the
 * two require shapes and nothing at all for a dynamic import or a subpath).
 *
 * The real tree has zero such sites today, so the real-tree fence cannot be
 * made red without editing src/ — hence this suite pins the helper's REACH on
 * synthetic inputs: R1–R4 are the holes, R5/R6 pin that extracting the helper
 * out of the b1 suite changed nothing it already caught.
 *
 * Helper contract this suite specifies:
 *   - `sourceFiles(root)` — every `/\.(tsx?|jsx?|mjs|cjs)$/` file under
 *     `<root>/src`, plus `<root>/App.tsx` and `<root>/index.ts` (today's walk,
 *     parameterised on the root so a temp dir can be swept).
 *   - `lucideRefs(filename, code)` — every reference to the lucide package in
 *     `code`, classified by shape; the existing shapes plus `'require'` and
 *     `'dynamic-import'`.
 */

import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

import { lucideRefs, sourceFiles, type LucideRef } from './lucideFence';

const APP_ROOT = path.resolve(__dirname, '../..');
const LUCIDE = 'lucide-react-native';

describe('lucideFence helper — lucideRefs() reach (W3-9)', () => {
  // R1 — mutation that must redden it: delete the CallExpression/`require` branch.
  it("R1: reports `const L = require('lucide-react-native')` as shape 'require'", () => {
    const refs = lucideRefs('x.ts', `const L = require('${LUCIDE}');`);
    expect(refs).toHaveLength(1);
    expect(refs[0]).toMatchObject({ file: 'x.ts', shape: 'require', exported: LUCIDE });
  });

  // R2 — mutation that must redden it: delete the `Import` callee /
  // ImportExpression branch. The installed @babel/parser (7.29.3) emits a
  // CallExpression whose `callee.type === 'Import'` with the specifier in
  // `arguments[0]`; it emits `ImportExpression` (specifier in `.source`) only
  // under `createImportExpressions: true`. The helper must read the literal
  // from the right field for whichever node type it is handed.
  it("R2: reports a dynamic `import('lucide-react-native')` inside a function body as shape 'dynamic-import'", () => {
    const refs = lucideRefs(
      'x.ts',
      `export async function f() { return import('${LUCIDE}'); }`
    );
    expect(refs).toHaveLength(1);
    expect(refs[0]).toMatchObject({ file: 'x.ts', shape: 'dynamic-import', exported: LUCIDE });
  });

  // R3 — mutation that must redden it: delete the TSImportEqualsDeclaration branch.
  it("R3: reports `import L = require('lucide-react-native')` as shape 'require'", () => {
    const refs = lucideRefs('x.ts', `import L = require('${LUCIDE}');`);
    expect(refs).toHaveLength(1);
    expect(refs[0]).toMatchObject({ file: 'x.ts', shape: 'require', exported: LUCIDE });
  });

  // R3 amendment (review ruling R-5): the `type` form parses with
  // `importKind: 'type'` and is erased by the TS transform, so it costs no
  // bytes — classify it 'type', never 'require', or the barrel fence at
  // babel.lucideIcons.b1.test.ts would redden on a form that ships nothing.
  it("R3: classifies `import type L = require('lucide-react-native')` as shape 'type', not 'require'", () => {
    const refs = lucideRefs('x.ts', `import type L = require('${LUCIDE}');`);
    expect(refs).toHaveLength(1);
    expect(refs[0]).toMatchObject({ file: 'x.ts', shape: 'type' });
    expect(refs[0].shape).not.toBe('require');
  });

  // R5 — regression PIN of the classifier as it was inside the b1 suite
  // (`:143-172`): extracting it must not change one branch. Mutation that
  // must redden it: remove any branch — that branch's case fails.
  describe('R5 (pin): the pre-existing import shapes classify exactly as before', () => {
    it("named value + inline `type` specifier → value 'Camera' + type 'LucideIcon'", () => {
      expect(lucideRefs('x.ts', `import { Camera, type LucideIcon } from '${LUCIDE}';`)).toEqual([
        { file: 'x.ts', shape: 'value', exported: 'Camera', local: 'Camera' },
        { file: 'x.ts', shape: 'type', exported: 'LucideIcon', local: 'LucideIcon' },
      ]);
    });

    it("`import type { X }` declaration → type, and `import { X as Y }` keeps both names", () => {
      expect(lucideRefs('x.ts', `import type { LucideProps } from '${LUCIDE}';`)).toEqual([
        { file: 'x.ts', shape: 'type', exported: 'LucideProps', local: 'LucideProps' },
      ]);
      expect(lucideRefs('x.ts', `import { User as UserIcon } from '${LUCIDE}';`)).toEqual([
        { file: 'x.ts', shape: 'value', exported: 'User', local: 'UserIcon' },
      ]);
    });

    it("`import * as L` → namespace", () => {
      expect(lucideRefs('x.ts', `import * as L from '${LUCIDE}'`)).toEqual([
        { file: 'x.ts', shape: 'namespace', exported: '*', local: 'L' },
      ]);
    });

    it("`import L from` → default; bare `import '…'` → side-effect", () => {
      expect(lucideRefs('x.ts', `import L from '${LUCIDE}';`)).toEqual([
        { file: 'x.ts', shape: 'default', exported: 'default', local: 'L' },
      ]);
      expect(lucideRefs('x.ts', `import '${LUCIDE}';`)).toEqual([
        { file: 'x.ts', shape: 'side-effect', exported: LUCIDE, local: LUCIDE },
      ]);
    });

    it("`export * from` → re-export", () => {
      expect(lucideRefs('x.ts', `export * from '${LUCIDE}'`)).toEqual([
        { file: 'x.ts', shape: 're-export', exported: LUCIDE, local: LUCIDE },
      ]);
    });

    it("`import x from 'lucide-react-native/icons'` → subpath", () => {
      expect(lucideRefs('x.ts', `import x from '${LUCIDE}/icons'`)).toEqual([
        { file: 'x.ts', shape: 'subpath', exported: `${LUCIDE}/icons`, local: `${LUCIDE}/icons` },
      ]);
    });

    it('ignores modules that merely share the prefix, and lucide named in a string or comment', () => {
      expect(
        lucideRefs(
          'x.ts',
          [
            `import { A } from '${LUCIDE}-extra';`,
            `const s = '${LUCIDE}';`,
            `// import { B } from '${LUCIDE}';`,
            `const r = require('react');`,
          ].join('\n')
        )
      ).toEqual([]);
    });
  });
});

describe('lucideFence helper — sourceFiles() reach (W3-9)', () => {
  // R4 — mutation that must redden it: revert the regex to /\.tsx?$/.
  // Temp-dir discipline (review ruling R-7): never a path under the worktree;
  // remove exactly the mkdtemp path in afterAll.
  describe('R4: sweeps every Metro script extension under <root>/src', () => {
    let root = '';

    beforeAll(() => {
      root = fs.mkdtempSync(path.join(os.tmpdir(), 'lucide-fence-'));
      fs.mkdirSync(path.join(root, 'src', 'nested'), { recursive: true });
      for (const name of ['a.tsx', 'b.js', 'c.jsx', 'd.json', 'e.mjs', 'f.cjs']) {
        fs.writeFileSync(path.join(root, 'src', name), '');
      }
      fs.writeFileSync(path.join(root, 'src', 'nested', 'g.ts'), '');
      fs.writeFileSync(path.join(root, 'App.tsx'), '');
      fs.writeFileSync(path.join(root, 'index.ts'), '');
    });

    afterAll(() => {
      if (root) fs.rmSync(root, { recursive: true, force: true });
    });

    it('returns a.tsx, b.js, c.jsx, e.mjs, f.cjs (+ nested) and NOT d.json', () => {
      const found = sourceFiles(root)
        .map((file) => path.relative(root, file).split(path.sep).join('/'))
        .sort();
      expect(found).toEqual([
        'App.tsx',
        'index.ts',
        'src/a.tsx',
        'src/b.js',
        'src/c.jsx',
        'src/e.mjs',
        'src/f.cjs',
        'src/nested/g.ts',
      ]);
      expect(found).not.toContain('src/d.json');
    });
  });

  // R6 — positive control on the REAL tree, GREEN once the helper exists.
  // Bounds, not exact counts (review ruling R-6): the existing suite pins
  // `> 50` / `>= 30` for the same reason. Measured 2026-09-11 at b63a8368:
  // 151 files, 136 value refs over 68 distinct names, 35 importer files,
  // 0 non-value/type shapes. Mutation that must redden it: replace the walk
  // with `[]`. A legitimate `import type { LucideIcon }` must NOT redden this
  // — the b1 fence deliberately permits 'type' (it is erased downstream and
  // costs no bytes), so the assertion is on the non-value/type shapes only,
  // never on the exact set of shapes present.
  describe('R6 (pin): the real tree still reports only value refs, and enough of them', () => {
    it('sourceFiles(APP_ROOT) walks src/ + App.tsx + index.ts (>= 150 files)', () => {
      const files = sourceFiles(APP_ROOT);
      expect(files.length).toBeGreaterThanOrEqual(150);
      expect(files).toContain(path.join(APP_ROOT, 'App.tsx'));
      expect(files).toContain(path.join(APP_ROOT, 'index.ts'));
      expect(files).toContain(path.join(APP_ROOT, 'src', 'screens', 'HomeScreen.tsx'));
    });

    it('the real-tree fence: > 50 value refs across >= 30 files and no other shape', () => {
      const refs = sourceFiles(APP_ROOT).flatMap((file) =>
        lucideRefs(file, fs.readFileSync(file, 'utf8'))
      );
      const values = refs.filter((ref) => ref.shape === 'value');
      expect(values.length).toBeGreaterThan(50);
      expect(new Set(values.map((ref) => ref.file)).size).toBeGreaterThanOrEqual(30);

      const label = (ref: LucideRef) =>
        `${path.relative(APP_ROOT, ref.file).split(path.sep).join('/')}: ${ref.shape} '${ref.exported}'`;
      expect(refs.filter((ref) => !['value', 'type'].includes(ref.shape)).map(label)).toEqual([]);
    });
  });
});
