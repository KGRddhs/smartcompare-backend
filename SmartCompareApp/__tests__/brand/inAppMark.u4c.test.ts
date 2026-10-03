/**
 * U4c — the in-app MYEZ mark: assets, manifest, renderer and the six sites.
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md
 * §3 R1/R2/R5/R6/R8/R10 and §5 rows B1-B13, as corrected (corrections 3 and 4)
 * and ruled (UR8, UR11, UR14).
 *
 * RED: B1-B5, B9-B11, B13. PIN (green at base and after): B6, B7, B8, B12.
 *
 * Binding (correction 3 / UR14): nothing this unit creates is imported at the
 * top of this file. PNG and JSON data are read with `fs` INSIDE each `it` and
 * decoded with __tests__/helpers/pngDecode.ts (never `require`d — w37 ruling
 * R14); B5 loads src/utils/splashMarkLayout inside its own `it`, so a missing
 * module reds B5 alone and the PINs stay green at base. Source checks read the
 * TypeScript AST with the installed `typescript`, as brand.hardcoded.s69 does.
 */
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';
import { decodePng, readIhdr } from '../helpers/pngDecode';

const APP = path.resolve(__dirname, '..', '..');
const REPO = path.resolve(APP, '..');
const SRC = path.join(APP, 'src');
const MANIFEST = path.join(REPO, 'docs', 'brand', 'myez-icons.manifest.json');
const RENDERER = path.join(REPO, 'scripts', 'render_myez_icons.py');

/** The three mark outputs, keyed exactly as the manifest keys them (§2h step 6). */
const MARK_ROWS: readonly (readonly [string, number])[] = [
  ['SmartCompareApp/assets/brand/myez-mark.png', 128],
  ['SmartCompareApp/assets/brand/myez-mark@2x.png', 256],
  ['SmartCompareApp/assets/brand/myez-mark@3x.png', 384],
];

/** §2h table, column pixels_sha256 — the binding pins (L8: file bytes may vary with zlib). */
const MARK_PIXELS_SHA256: Record<string, string> = {
  'SmartCompareApp/assets/brand/myez-mark.png':
    '0129d00820d78baa910ec8f50515d6cfd4ca6189283b320e51fee7f2a0f8a624',
  'SmartCompareApp/assets/brand/myez-mark@2x.png':
    '32f7c08105b36b0f1a292dba54d0925327d0ba6a31ff7686bf7f31f553a1702d',
  'SmartCompareApp/assets/brand/myez-mark@3x.png':
    'a06dbd98fb11d3559ef6b2b2482ca3fbce185bdf5a9c683a96735fe26777d867',
};

/** §2h step 6, the manifest's `mark_geometry` (UR8). */
const MARK_GEOMETRY = {
  ink_bbox_master_px: [483, 399, 1629, 1641],
  mark_square_master_px: [435, 399, 1242],
  master_px: 2048,
  splash_canvas_px: 1024,
  splash_mark_px: 549,
  splash_offset_px: 237,
};

/** The COMMITTED manifest's four launcher rows + params (U4b), byte-for-byte values. */
const COMMITTED_OUTPUTS = {
  'SmartCompareApp/assets/adaptive-icon.png': {
    height: 1024,
    mode: 'RGBA',
    pixels_sha256: 'a63c86c3e8f077063bcc603bb6de62eb531a8361419db41f92923fb5e646735b',
    sha256: 'b336b66be61f3c72a23404f201fdcb444f78aa2d9e8d5974069b306f26cb89ce',
    width: 1024,
  },
  'SmartCompareApp/assets/favicon.png': {
    height: 48,
    mode: 'RGBA',
    pixels_sha256: '7627680f1f4c635a40214d9d7f94fda643bfcea8390d405382f3cd0b23c2e655',
    sha256: '3d225c46961f8d45a0faa2828a41b7b4e355607971f4e060091ae52e8b21d4d5',
    width: 48,
  },
  'SmartCompareApp/assets/icon.png': {
    height: 1024,
    mode: 'RGB',
    pixels_sha256: '0453bb5b1b8cff0f4e906325656655559988bc6a06be0a2d20b30806f08dbd93',
    sha256: '2530d5b33098dac3b2aa417982c506d8b93e2bbe5b07d387d78eabc52edc5834',
    width: 1024,
  },
  'SmartCompareApp/assets/splash-icon.png': {
    height: 1024,
    mode: 'RGBA',
    pixels_sha256: '35ab76cc17743108d670ff82092f78eef442636fe1a4cf55def018b52cd706db',
    sha256: 'bf8df272011f8c374bbdd1b681c892a238fa487ad62dfa9df5e84cbb953976b7',
    width: 1024,
  },
};
const COMMITTED_PARAMS = {
  adaptive_margin_px: 8,
  canvas: 1024,
  favicon_px: 48,
  safe_radius_px: 312.889,
  splash_ink_width_fraction: 0.3,
  tile_white: '#ffffff',
};
const COMMITTED_MASTER = {
  path: 'docs/brand/myez-icon-master-2048.png',
  sha256: '70b2f8264d7eb07dbfe7627d332d991dc68429f3440615751bf99eacc05a4b41',
};

/** The nine sites of §2b, relative to src/ (R5). */
const SITE_FILES = [
  'components/hero/LoadingRings.tsx',
  'components/hero/RevealBurst.tsx',
  'screens/ForgotPasswordScreen.tsx',
  'screens/HistoryScreen.tsx',
  'screens/HomeScreen.tsx',
  'screens/ProfileScreen.tsx',
  'screens/RegisterScreen.tsx',
  'screens/SplashScreen.tsx',
  'screens/onboarding/Step01Welcome.tsx',
];

type AnyJson = any;

const sha256Of = (bytes: Uint8Array): string => crypto.createHash('sha256').update(bytes).digest('hex');
const readJson = (p: string): AnyJson => JSON.parse(fs.readFileSync(p, 'utf8'));
const abs = (rel: string): string => path.join(REPO, ...rel.split('/'));
const rel = (file: string): string => path.relative(SRC, file).split(path.sep).join('/');

function listSources(dir: string, out: string[] = []): string[] {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) listSources(p, out);
    else if (/\.tsx?$/.test(e.name) && !/\.d\.ts$/.test(e.name)) out.push(p);
  }
  return out;
}

function parse(file: string): ts.SourceFile {
  return ts.createSourceFile(
    file,
    fs.readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true,
    file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );
}

function walk(node: ts.Node, fn: (n: ts.Node) => void): void {
  fn(node);
  ts.forEachChild(node, (c) => walk(c, fn));
}

/** Every module specifier a file names: import / export-from / import = require / require() / import(). */
function moduleSpecifiers(sf: ts.SourceFile): string[] {
  const out: string[] = [];
  walk(sf, (n) => {
    if ((ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) && n.moduleSpecifier && ts.isStringLiteral(n.moduleSpecifier)) {
      out.push(n.moduleSpecifier.text);
    } else if (
      ts.isImportEqualsDeclaration(n) &&
      ts.isExternalModuleReference(n.moduleReference) &&
      ts.isStringLiteral(n.moduleReference.expression)
    ) {
      out.push(n.moduleReference.expression.text);
    } else if (ts.isCallExpression(n) && n.arguments[0] && ts.isStringLiteralLike(n.arguments[0])) {
      const callee = n.expression;
      if ((ts.isIdentifier(callee) && callee.text === 'require') || callee.kind === ts.SyntaxKind.ImportKeyword) {
        out.push(n.arguments[0].text);
      }
    }
  });
  return out;
}

type QarenLogoUse = { el: ts.JsxSelfClosingElement | ts.JsxElement; attrs: ts.JsxAttributes; line: number };

/** Every `<QarenLogo …>` JSX element of a file (self-closing or with children). */
function qarenLogoUses(sf: ts.SourceFile): QarenLogoUse[] {
  const out: QarenLogoUse[] = [];
  walk(sf, (n) => {
    if (ts.isJsxSelfClosingElement(n) && n.tagName.getText(sf) === 'QarenLogo') {
      out.push({ el: n, attrs: n.attributes, line: sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1 });
    } else if (ts.isJsxElement(n) && n.openingElement.tagName.getText(sf) === 'QarenLogo') {
      out.push({
        el: n,
        attrs: n.openingElement.attributes,
        line: sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1,
      });
    }
  });
  return out;
}

/** True for a call `t('app.name')` / `x.t('app.name')`. */
function isAppNameCall(n: ts.Node): boolean {
  if (!ts.isCallExpression(n)) return false;
  const callee = n.expression;
  const name = ts.isIdentifier(callee)
    ? callee.text
    : ts.isPropertyAccessExpression(callee)
      ? callee.name.text
      : '';
  const arg = n.arguments[0];
  return name === 't' && !!arg && ts.isStringLiteralLike(arg) && arg.text === 'app.name';
}

function countAppNameCalls(node: ts.Node): number {
  let count = 0;
  walk(node, (n) => {
    if (isAppNameCall(n)) count += 1;
  });
  return count;
}

/** Alpha >= threshold bounding box, PIL getbbox convention: [left, top, right_excl, bottom_excl]. */
function alphaBbox(px: Uint8Array, width: number, height: number, threshold: number): number[] | null {
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
  return r < 0 ? null : [l, t, r + 1, b + 1];
}

describe('U4c in-app mark — assets and manifest', () => {
  it('B1 the three mark PNGs exist: IHDR (n, n, 8-bit, RGBA colour type 6, non-interlaced) for 128 / 256 / 384', () => {
    const got = MARK_ROWS.map(([key, n]) => {
      const file = abs(key);
      const exists = fs.existsSync(file);
      return { key, exists, ihdr: exists ? readIhdr(fs.readFileSync(file)) : null, n };
    });
    expect(got).toEqual(
      MARK_ROWS.map(([key, n]) => ({
        key,
        exists: true,
        ihdr: { width: n, height: n, bitDepth: 8, colorType: 6, interlace: 0 },
        n,
      }))
    );
  });

  it('B2 manifest.mark_outputs keys the three files; each row matches the file sha256, the decoded pixels and its size/mode', () => {
    const manifest = readJson(MANIFEST);
    const markOutputs = manifest.mark_outputs ?? {};
    expect(Object.keys(markOutputs).sort()).toEqual(MARK_ROWS.map(([key]) => key));
    for (const [key, n] of MARK_ROWS) {
      const bytes = fs.readFileSync(abs(key));
      const decoded = decodePng(bytes);
      expect({ key, row: markOutputs[key] }).toEqual({
        key,
        row: {
          height: n,
          mode: 'RGBA',
          pixels_sha256: sha256Of(decoded.pixels),
          sha256: sha256Of(bytes),
          width: n,
        },
      });
    }
  });

  it('B3 the decoded pixels_sha256 of each mark PNG equals the binding §2h value', () => {
    const got = MARK_ROWS.map(([key]) => {
      const file = abs(key);
      return { key, pixels_sha256: fs.existsSync(file) ? sha256Of(decodePng(fs.readFileSync(file)).pixels) : 'MISSING' };
    });
    expect(got).toEqual(MARK_ROWS.map(([key]) => ({ key, pixels_sha256: MARK_PIXELS_SHA256[key] })));
  });

  it('B4 @3x pixels: transparent corners, centred full-height ink, emerald dot bottom-right, black wordmark', () => {
    const key = 'SmartCompareApp/assets/brand/myez-mark@3x.png';
    expect({ key, exists: fs.existsSync(abs(key)) }).toEqual({ key, exists: true });
    const { width, height, channels, pixels } = decodePng(fs.readFileSync(abs(key)));
    expect({ width, height, channels }).toEqual({ width: 384, height: 384, channels: 4 });

    const alphaAt = (x: number, y: number): number => pixels[(y * width + x) * 4 + 3];
    const bbox = alphaBbox(pixels, width, height, 128) ?? [0, 0, 0, 0];
    let emerald = 0;
    let emeraldOutsideBottomRight = 0;
    let nearBlack = 0;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const i = (y * width + x) * 4;
        const [r, g, b, a] = [pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3]];
        if (a >= 200 && g > r + 60) {
          emerald += 1;
          if (x < 192 || y < 192) emeraldOutsideBottomRight += 1;
        }
        if (a >= 200 && Math.max(r, g, b) < 40) nearBlack += 1;
      }
    }
    // Prototype measured (§2h, review): bbox (15,0,369,384), asymmetry 0;
    // emerald 1,289 px in x 305..344, y 343..382; near-black 57,520.
    expect({
      cornerAlphas: [alphaAt(0, 0), alphaAt(width - 1, 0), alphaAt(0, height - 1), alphaAt(width - 1, height - 1)],
      inkTop: bbox[1],
      inkBottom: bbox[3],
      inkHorizontalAsymmetryAtMost1: Math.abs(bbox[0] - (width - bbox[2])) <= 1,
      emeraldAtLeast500: emerald >= 500,
      emeraldOutsideBottomRight,
      nearBlackAtLeast10000: nearBlack >= 10000,
    }).toEqual({
      cornerAlphas: [0, 0, 0, 0],
      inkTop: 0,
      inkBottom: 384,
      inkHorizontalAsymmetryAtMost1: true,
      emeraldAtLeast500: true,
      emeraldOutsideBottomRight: 0,
      nearBlackAtLeast10000: true,
    });
  });

  it('B5 manifest.mark_geometry equals §2h AND the constants exported by src/utils/splashMarkLayout', () => {
    const manifest = readJson(MANIFEST);
    expect(manifest.mark_geometry).toEqual(MARK_GEOMETRY);
    // Correction 3 / UR14: loaded INSIDE this `it`, never at file top.
    const layout = jest.requireActual<Record<string, unknown>>('../../src/utils/splashMarkLayout');
    expect({
      MASTER_PX: layout.MASTER_PX,
      SPLASH_CANVAS_PX: layout.SPLASH_CANVAS_PX,
      SPLASH_MARK_PX: layout.SPLASH_MARK_PX,
      SPLASH_OFFSET_PX: layout.SPLASH_OFFSET_PX,
      MARK_SQUARE_MASTER_PX: layout.MARK_SQUARE_MASTER_PX,
    }).toEqual({
      MASTER_PX: manifest.mark_geometry.master_px,
      SPLASH_CANVAS_PX: manifest.mark_geometry.splash_canvas_px,
      SPLASH_MARK_PX: manifest.mark_geometry.splash_mark_px,
      SPLASH_OFFSET_PX: manifest.mark_geometry.splash_offset_px,
      MARK_SQUARE_MASTER_PX: manifest.mark_geometry.mark_square_master_px,
    });
  });

  it('B6 [PIN] manifest.outputs is exactly the four committed launcher rows; params / master / renderer / pillow unchanged', () => {
    const manifest = readJson(MANIFEST);
    expect({
      outputs: manifest.outputs,
      params: manifest.params,
      master: manifest.master,
      renderer: manifest.renderer,
      pillow: manifest.pillow,
    }).toEqual({
      outputs: COMMITTED_OUTPUTS,
      params: COMMITTED_PARAMS,
      master: COMMITTED_MASTER,
      renderer: 'scripts/render_myez_icons.py',
      pillow: '12.3.0',
    });
  });

  it('B7 [PIN] app.json launcher art + splash unchanged, no bundling patterns, no expo-splash-screen; package.json has no expo-image', () => {
    const expo = readJson(path.join(APP, 'app.json')).expo;
    const pkg = readJson(path.join(APP, 'package.json'));
    const pluginNames: string[] = (expo.plugins ?? []).map((p: AnyJson) => (Array.isArray(p) ? p[0] : p));
    const depNames = [
      ...Object.keys(pkg.dependencies ?? {}),
      ...Object.keys(pkg.devDependencies ?? {}),
      ...Object.keys(pkg.peerDependencies ?? {}),
      ...Object.keys(pkg.optionalDependencies ?? {}),
    ];
    expect({
      icon: expo.icon,
      splashImage: expo.splash?.image,
      splashResizeMode: expo.splash?.resizeMode,
      splashBackgroundColor: expo.splash?.backgroundColor,
      adaptiveForeground: expo.android?.adaptiveIcon?.foregroundImage,
      hasAssetBundlePatterns: 'assetBundlePatterns' in expo,
      hasAssetPatternsToBeBundled: 'assetPatternsToBeBundled' in (expo.updates ?? {}),
      hasExpoSplashScreenPlugin: pluginNames.includes('expo-splash-screen'),
      hasExpoImage: depNames.includes('expo-image'),
    }).toEqual({
      icon: './assets/icon.png',
      splashImage: './assets/splash-icon.png',
      splashResizeMode: 'contain',
      splashBackgroundColor: '#ffffff',
      adaptiveForeground: './assets/adaptive-icon.png',
      hasAssetBundlePatterns: false,
      hasAssetPatternsToBeBundled: false,
      hasExpoSplashScreenPlugin: false,
      hasExpoImage: false,
    });
  });

  it('B13 [SOURCE] the renderer writes the mark outputs + the two manifest keys and keeps OUTPUT_NAMES literal', () => {
    const text = fs.readFileSync(RENDERER, 'utf8');
    const needles = [
      'brand/myez-mark.png',
      '@2x',
      '@3x',
      'mark_outputs',
      'mark_geometry',
      'OUTPUT_NAMES = (ADAPTIVE, FAVICON_NAME, ICON, SPLASH)',
    ];
    expect({ missing: needles.filter((s) => !text.includes(s)) }).toEqual({ missing: [] });
  });
});

describe('U4c in-app mark — the six sites (AST over src/)', () => {
  it('B8 [PIN] exactly the nine site files import QarenLogo', () => {
    const importers = listSources(SRC)
      .filter((file) => moduleSpecifiers(parse(file)).some((s) => /(^|\/)QarenLogo$/.test(s)))
      .map(rel)
      .sort();
    expect(importers).toEqual(SITE_FILES);
  });

  it('B9 every <QarenLogo> size: Home 28, Profile 28, History 24, Welcome 40, LoadingRings Math.round(size * 0.22), Splash not a numeric literal, RevealBurst BADGE_R, Register 56 x2, ForgotPassword 56', () => {
    const got: Record<string, string[]> = {};
    for (const file of listSources(SRC)) {
      const sf = parse(file);
      const uses = qarenLogoUses(sf);
      if (uses.length === 0) continue;
      got[rel(file)] = uses.map(({ attrs }) => {
        const size = attrs.properties.find(
          (p): p is ts.JsxAttribute => ts.isJsxAttribute(p) && p.name.getText(sf) === 'size'
        );
        if (!size || !size.initializer) return 'missing';
        if (ts.isStringLiteral(size.initializer)) return `string:${size.initializer.text}`;
        const expr = ts.isJsxExpression(size.initializer) ? size.initializer.expression : undefined;
        if (!expr) return 'empty';
        return ts.isNumericLiteral(expr) ? `numeric:${expr.text}` : `expression:${expr.getText(sf)}`;
      });
    }
    expect(got).toEqual({
      'components/hero/LoadingRings.tsx': ['expression:Math.round(size * 0.22)'],
      'components/hero/RevealBurst.tsx': ['expression:BADGE_R'],
      'screens/ForgotPasswordScreen.tsx': ['numeric:56'],
      'screens/HistoryScreen.tsx': ['numeric:24'],
      'screens/HomeScreen.tsx': ['numeric:28'],
      'screens/ProfileScreen.tsx': ['numeric:28'],
      'screens/RegisterScreen.tsx': ['numeric:56', 'numeric:56'],
      'screens/SplashScreen.tsx': [expect.not.stringMatching(/^numeric:/)],
      'screens/onboarding/Step01Welcome.tsx': ['numeric:40'],
    });
  });

  it("B10 [D1] no t('app.name') beside any <QarenLogo>, and none at all in SplashScreen.tsx / HomeScreen.tsx", () => {
    const besideTheMark: string[] = [];
    for (const file of listSources(SRC)) {
      const sf = parse(file);
      for (const { el, line } of qarenLogoUses(sf)) {
        const container = el.parent;
        const siblings: readonly ts.Node[] =
          container && (ts.isJsxElement(container) || ts.isJsxFragment(container))
            ? container.children.filter((c) => c !== el)
            : [];
        if (siblings.some((s) => countAppNameCalls(s) > 0)) besideTheMark.push(`${rel(file)}:${line}`);
      }
    }
    expect({
      besideTheMark,
      splashScreenAppNameCalls: countAppNameCalls(parse(path.join(SRC, 'screens', 'SplashScreen.tsx'))),
      homeScreenAppNameCalls: countAppNameCalls(parse(path.join(SRC, 'screens', 'HomeScreen.tsx'))),
    }).toEqual({ besideTheMark: [], splashScreenAppNameCalls: 0, homeScreenAppNameCalls: 0 });
  });

  it('B11 no src file carries the old Q-tail path, and QarenLogo.tsx does not import react-native-svg', () => {
    const withQTail = listSources(SRC)
      .filter((file) => fs.readFileSync(file, 'utf8').includes('M22 22 L27 27'))
      .map(rel)
      .sort();
    const logoImportsSvg = moduleSpecifiers(parse(path.join(SRC, 'components', 'QarenLogo.tsx'))).some(
      (s) => s === 'react-native-svg' || s.startsWith('react-native-svg/')
    );
    expect({ withQTail, logoImportsSvg }).toEqual({ withQTail: [], logoImportsSvg: false });
  });

  it('B12 [PIN] no <QarenLogo> passes color (no color attribute, no spread)', () => {
    const passesColor: string[] = [];
    for (const file of listSources(SRC)) {
      const sf = parse(file);
      for (const { attrs, line } of qarenLogoUses(sf)) {
        const bad = attrs.properties.some(
          (p) => ts.isJsxSpreadAttribute(p) || (ts.isJsxAttribute(p) && p.name.getText(sf) === 'color')
        );
        if (bad) passesColor.push(`${rel(file)}:${line}`);
      }
    }
    expect(passesColor).toEqual([]);
  });
});
