/**
 * splashMarkLayout — the pure geometry that puts the JS splash mark on the
 * native launch screen's pixels (U4c, D2).
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md
 * §2d, §3 R8 and §5 rows D1-D3, as ruled (UR10, UR14).
 *
 * The module src/utils/splashMarkLayout.ts is created by this unit, so it is
 * loaded INSIDE each `it` (UR14 / correction 3), never at file top: a missing
 * module reds the test, it never stops the suite from loading. The function
 * stays PHYSICAL and pure (UR10: the RTL mirror is SplashScreen's job).
 *
 * D2 measures pixels, not formulas: it decodes the COMMITTED
 * assets/splash-icon.png (what the iOS launch storyboard draws full-width,
 * scaleAspectFit, vertically centred) and assets/brand/myez-mark@3x.png (what
 * the JS splash draws at the layout rectangle), takes each alpha >= 128 ink
 * box, and requires every edge of the two on-screen ink rectangles to agree
 * within 0.5 pt on the four windows of the §2d table. PNGs are read with `fs`
 * and decoded with __tests__/helpers/pngDecode.ts, never `require`d.
 */
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';
import { decodePng } from '../helpers/pngDecode';

type Win = { width: number; height: number };
type Layout = { left: number; top: number; size: number };
type LayoutModule = { splashMarkLayout: (win: Win) => Layout };

const APP = path.resolve(__dirname, '..', '..');
const LAYOUT_TS = path.join(APP, 'src', 'utils', 'splashMarkLayout.ts');
const SPLASH_ICON = path.join(APP, 'assets', 'splash-icon.png');
const MARK_3X = path.join(APP, 'assets', 'brand', 'myez-mark@3x.png');

/** Spec §2d table (pt). */
const TABLE: readonly { win: Win; expected: Layout }[] = [
  { win: { width: 375, height: 667 }, expected: { size: 121.926, left: 129.495, top: 271.961 } },
  { win: { width: 390, height: 844 }, expected: { size: 126.803, left: 134.675, top: 358.0 } },
  { win: { width: 393, height: 852 }, expected: { size: 127.778, left: 135.711, top: 361.508 } },
  { win: { width: 430, height: 932 }, expected: { size: 139.808, left: 148.488, top: 395.436 } },
];
const TOLERANCE_PT = 0.01;
const HANDOFF_TOLERANCE_PT = 0.5;

/** Loaded inside the `it` (UR14). */
function loadLayout(): LayoutModule {
  return jest.requireActual<LayoutModule>('../../src/utils/splashMarkLayout');
}

/** Rows whose left / top / size miss the table by more than ± 0.01 pt. */
function tableMisses(fn: LayoutModule['splashMarkLayout'], rows: typeof TABLE): string[] {
  const misses: string[] = [];
  for (const { win, expected } of rows) {
    const got = fn({ width: win.width, height: win.height });
    for (const k of ['left', 'top', 'size'] as const) {
      if (typeof got?.[k] !== 'number' || Math.abs(got[k] - expected[k]) > TOLERANCE_PT) {
        misses.push(`${win.width}x${win.height} ${k}: got ${got?.[k]}, want ${expected[k]} ± ${TOLERANCE_PT}`);
      }
    }
  }
  return misses;
}

/** Alpha >= threshold bounding box, PIL getbbox convention: [left, top, right_excl, bottom_excl]. */
function alphaBbox(px: Uint8Array, width: number, height: number, threshold: number): number[] {
  let l = width;
  let t = height;
  let r = -1;
  let b = -1;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (px[(y * width + x) * 4 + 3] >= threshold) {
        if (x < l) l = x;
        if (x > r) r = x;
        if (y < t) t = y;
        if (y > b) b = y;
      }
    }
  }
  if (r < 0) throw new Error('alphaBbox: no pixel at or above the threshold');
  return [l, t, r + 1, b + 1];
}

describe('splashMarkLayout (U4c)', () => {
  it('D1 matches the §2d table on 375x667, 390x844, 393x852, 430x932 (± 0.01 pt)', () => {
    const { splashMarkLayout } = loadLayout();
    expect(tableMisses(splashMarkLayout, TABLE)).toEqual([]);
  });

  it('D2 [pixels] the JS ink rectangle lands on the native launch-screen ink within 0.5 pt on every edge', () => {
    expect({
      layoutModule: fs.existsSync(LAYOUT_TS),
      mark3x: fs.existsSync(MARK_3X),
    }).toEqual({ layoutModule: true, mark3x: true });
    const { splashMarkLayout } = loadLayout();

    const splash = decodePng(fs.readFileSync(SPLASH_ICON));
    const mark = decodePng(fs.readFileSync(MARK_3X));
    expect({ splash: [splash.width, splash.height, splash.channels], mark: [mark.width, mark.height, mark.channels] })
      .toEqual({ splash: [1024, 1024, 4], mark: [384, 384, 4] });
    const nb = alphaBbox(splash.pixels, splash.width, splash.height, 128);
    const jb = alphaBbox(mark.pixels, mark.width, mark.height, 128);

    const offenders: string[] = [];
    for (const { win } of TABLE) {
      // Native: the square splash-icon.png drawn scaleAspectFit into the full window.
      const D = Math.min(win.width, win.height);
      const k = D / splash.width;
      const ox = (win.width - D) / 2;
      const oy = (win.height - D) / 2;
      const native = [ox + nb[0] * k, oy + nb[1] * k, ox + nb[2] * k, oy + nb[3] * k];
      // JS: the @3x mark drawn at the layout rectangle.
      const { left, top, size } = splashMarkLayout({ width: win.width, height: win.height });
      const s = size / mark.width;
      const js = [left + jb[0] * s, top + jb[1] * s, left + jb[2] * s, top + jb[3] * s];
      ['left', 'top', 'right', 'bottom'].forEach((edge, i) => {
        const d = js[i] - native[i];
        if (!(Math.abs(d) <= HANDOFF_TOLERANCE_PT)) {
          offenders.push(`${win.width}x${win.height} ${edge}: js ${js[i].toFixed(3)} vs native ${native[i].toFixed(3)} (${d.toFixed(3)} pt)`);
        }
      });
    }
    expect(offenders).toEqual([]);
  });

  it('D3 [pure] no react-native import; same input gives deep-equal output; the result depends on the argument only', () => {
    const rel = path.relative(APP, LAYOUT_TS).split(path.sep).join('/');
    expect({ file: rel, exists: fs.existsSync(LAYOUT_TS) }).toEqual({ file: rel, exists: true });

    const sf = ts.createSourceFile(LAYOUT_TS, fs.readFileSync(LAYOUT_TS, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const specifiers: string[] = [];
    const visit = (n: ts.Node): void => {
      if ((ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) && n.moduleSpecifier && ts.isStringLiteral(n.moduleSpecifier)) {
        specifiers.push(n.moduleSpecifier.text);
      } else if (
        ts.isImportEqualsDeclaration(n) &&
        ts.isExternalModuleReference(n.moduleReference) &&
        ts.isStringLiteral(n.moduleReference.expression)
      ) {
        specifiers.push(n.moduleReference.expression.text);
      } else if (ts.isCallExpression(n) && n.arguments[0] && ts.isStringLiteralLike(n.arguments[0])) {
        const callee = n.expression;
        if ((ts.isIdentifier(callee) && callee.text === 'require') || callee.kind === ts.SyntaxKind.ImportKeyword) {
          specifiers.push(n.arguments[0].text);
        }
      }
      ts.forEachChild(n, visit);
    };
    visit(sf);
    expect(specifiers.filter((s) => s === 'react-native' || s.startsWith('react-native/'))).toEqual([]);

    const { splashMarkLayout } = loadLayout();
    const first = splashMarkLayout({ width: 390, height: 844 });
    const second = splashMarkLayout({ width: 390, height: 844 });
    expect(second).toEqual(first);
    // The jest react-native mock reports a 390 x 844 window; 430 x 932 must
    // still give its own row, so nothing but the argument is read.
    expect(tableMisses(splashMarkLayout, [TABLE[1], TABLE[3]])).toEqual([]);
  });
});
