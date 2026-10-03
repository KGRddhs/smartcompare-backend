/**
 * U4d - the MYEZ mark in the winner reveal badge; QaranIcon removed; stale
 * brand comments reworded (issue #283).
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U4D_REVEAL_GLYPH_SPEC.md
 * section 5 rows R1-R9, as corrected (C3) and ruled (UR1, UR5, UR11, UR14).
 *
 * RED at base: R1, R2, R3, R5, R6, R8, R9. PIN (green at base and after): R4, R7.
 *
 * Binding conventions:
 * - the mark is the host whose type is 'Image' (QarenLogo renders the RN
 *   Image); R2 and R3 FIRST assert exactly one such host in the scope they
 *   test, then read every prop from that host (C3a / UR11);
 * - styles are flattened deeply (the repo StyleSheet mock flattens one level);
 * - source checks read the TypeScript AST with the installed `typescript`, as
 *   inAppMark.u4c does; whitespace-only JsxText is ignored (C3b / UR11);
 * - nothing this unit deletes is imported at file top: the icons barrel is
 *   required INSIDE R6 / R7 only (UR14). RevealBurst itself stays.
 *
 * No snapshot assertion, no wall-clock dependency.
 */
import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';
import { render } from '@testing-library/react-native';
import { RevealBurst } from '../../src/components/hero/RevealBurst';

const APP = path.resolve(__dirname, '..', '..');
const SRC = path.join(APP, 'src');
const REVEAL_BURST = path.join(SRC, 'components', 'hero', 'RevealBurst.tsx');

/**
 * Local structural type for a test-renderer node: the repo installs no
 * @types/react-test-renderer, so RNTL's `UNSAFE_root` is typed loosely.
 */
type TestNode = {
  type: unknown;
  props: Record<string, any>;
  parent: TestNode | null;
  findAll: (predicate: (node: TestNode) => boolean) => TestNode[];
};

type Style = Record<string, unknown>;

/** Deep StyleSheet.flatten (the repo mock flattens one array level only). */
function flattenStyle(style: unknown): Style {
  if (Array.isArray(style)) {
    return style.reduce<Style>((acc, s) => ({ ...acc, ...flattenStyle(s) }), {});
  }
  if (style && typeof style === 'object') return { ...(style as Style) };
  return {};
}

const isHost = (n: TestNode): boolean => typeof n.type === 'string';
const imageHosts = (scope: TestNode): TestNode[] => scope.findAll((n) => n.type === 'Image');

function hostCounts(scope: TestNode, types: readonly string[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const t of types) out[t] = scope.findAll((n) => n.type === t).length;
  return out;
}

function listSources(dir: string, out: string[] = []): string[] {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) listSources(p, out);
    else if (/\.tsx?$/.test(e.name) && !/\.d\.ts$/.test(e.name)) out.push(p);
  }
  return out;
}

const relApp = (file: string): string => path.relative(APP, file).split(path.sep).join('/');

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

/** The attribute names of every `<QarenLogo ...>` element ('...spread' for a spread). */
function qarenLogoAttributeNames(sf: ts.SourceFile): string[][] {
  const out: string[][] = [];
  walk(sf, (n) => {
    let attrs: ts.JsxAttributes | undefined;
    if (ts.isJsxSelfClosingElement(n) && n.tagName.getText(sf) === 'QarenLogo') attrs = n.attributes;
    else if (ts.isJsxElement(n) && n.openingElement.tagName.getText(sf) === 'QarenLogo') {
      attrs = n.openingElement.attributes;
    }
    if (attrs) {
      out.push(attrs.properties.map((p) => (ts.isJsxAttribute(p) ? p.name.getText(sf) : '...spread')));
    }
  });
  return out;
}

/** The JSX element whose opening tag carries testID="<id>" (a string literal). */
function jsxElementWithTestId(sf: ts.SourceFile, id: string): ts.JsxElement | undefined {
  let found: ts.JsxElement | undefined;
  walk(sf, (n) => {
    if (found || !ts.isJsxElement(n)) return;
    const hit = n.openingElement.attributes.properties.some(
      (p) =>
        ts.isJsxAttribute(p) &&
        p.name.getText(sf) === 'testID' &&
        !!p.initializer &&
        ts.isStringLiteral(p.initializer) &&
        p.initializer.text === id
    );
    if (hit) found = n;
  });
  return found;
}

/** A readable label for a JSX child (whitespace-only JsxText is filtered by the caller). */
function describeJsxChild(c: ts.JsxChild, sf: ts.SourceFile): string {
  if (ts.isJsxSelfClosingElement(c)) return c.tagName.getText(sf);
  if (ts.isJsxElement(c)) return c.openingElement.tagName.getText(sf);
  if (ts.isJsxText(c)) return `text:${c.text.trim()}`;
  return `${ts.SyntaxKind[c.kind]}:${c.getText(sf)}`;
}

describe('U4d reveal glyph - the RevealBurst badge carries the MYEZ mark', () => {
  it('R1 inside reveal-burst-badge: exactly one host Image and no Svg / Circle / Line / Path / G host', () => {
    const r = render(<RevealBurst />);
    const badge = r.getByTestId('reveal-burst-badge') as unknown as TestNode;
    expect(hostCounts(badge, ['Image', 'Svg', 'Circle', 'Line', 'Path', 'G'])).toEqual({
      Image: 1,
      Svg: 0,
      Circle: 0,
      Line: 0,
      Path: 0,
      G: 0,
    });
  });

  it('R2 the mark Image is 56 x 56 (size BADGE_R) for <RevealBurst /> and for the Results mount <RevealBurst size={220} />', () => {
    const cases: [string, React.ReactElement][] = [
      ['default', <RevealBurst key="default" />],
      ['size 220', <RevealBurst key="size220" size={220} />],
    ];
    for (const [where, element] of cases) {
      const r = render(element);
      const images = imageHosts(r.UNSAFE_root as unknown as TestNode);
      // C3a: exactly one Image host first; every prop is read from it.
      expect({ where, imageHosts: images.length }).toEqual({ where, imageHosts: 1 });
      expect({ where, style: flattenStyle(images[0].props.style) }).toEqual({
        where,
        style: { width: 56, height: 56 },
      });
      r.unmount();
    }
  });

  it('R3 the mark Image is hidden from accessibility, contain / fadeDuration 0, untinted, unlabelled up to the root, and shows the bundled mark', () => {
    const r = render(<RevealBurst />);
    const images = imageHosts(r.UNSAFE_root as unknown as TestNode);
    // C3a: exactly one Image host first; every prop is read from it.
    expect({ imageHosts: images.length }).toEqual({ imageHosts: 1 });
    const image = images[0];

    const labelledOrAccessible: string[] = [];
    for (let n: TestNode | null = image; n; n = n.parent) {
      if (!isHost(n)) continue;
      const label = `${String(n.type)}${n.props.testID ? `#${n.props.testID}` : ''}`;
      if (n.props.accessibilityLabel !== undefined) labelledOrAccessible.push(`${label} accessibilityLabel`);
      if (n.props.accessible === true) labelledOrAccessible.push(`${label} accessible`);
    }

    expect({
      accessibilityElementsHidden: image.props.accessibilityElementsHidden,
      importantForAccessibility: image.props.importantForAccessibility,
      resizeMode: image.props.resizeMode,
      fadeDuration: image.props.fadeDuration,
      tintColorProp: 'tintColor' in image.props,
      tintColorInStyle: 'tintColor' in flattenStyle(image.props.style),
      labelledOrAccessible,
    }).toEqual({
      accessibilityElementsHidden: true,
      importantForAccessibility: 'no-hide-descendants',
      resizeMode: 'contain',
      fadeDuration: 0,
      tintColorProp: false,
      tintColorInStyle: false,
      labelledOrAccessible: [],
    });

    // Sanity only: jest maps every PNG to the same stub module.
    const markSource = require('../../assets/brand/myez-mark.png');
    expect(image.props.source).toBe(markSource);
  });

  it('R4 [PIN] the badge itself is unchanged: #ECFDF5, 112 x 112, radius 56', () => {
    const r = render(<RevealBurst />);
    const style = flattenStyle(r.getByTestId('reveal-burst-badge').props.style);
    expect({
      backgroundColor: style.backgroundColor,
      width: style.width,
      height: style.height,
      borderRadius: style.borderRadius,
    }).toEqual({ backgroundColor: '#ECFDF5', width: 112, height: 112, borderRadius: 56 });
  });

  it("R5 [AST] RevealBurst.tsx: default import QarenLogo from '../QarenLogo', no icons specifier, one <QarenLogo size> and it is the badge's only child", () => {
    const sf = parse(REVEAL_BURST);
    const defaultQarenLogoImport = sf.statements.some(
      (s) =>
        ts.isImportDeclaration(s) &&
        ts.isStringLiteral(s.moduleSpecifier) &&
        s.moduleSpecifier.text === '../QarenLogo' &&
        s.importClause?.name?.text === 'QarenLogo'
    );
    const badge = jsxElementWithTestId(sf, 'reveal-burst-badge');
    const badgeChildren = badge
      ? badge.children
          // C3b: whitespace-only JsxText is formatting, not a child.
          .filter((c) => !(ts.isJsxText(c) && c.containsOnlyTriviaWhiteSpaces))
          .map((c) => describeJsxChild(c, sf))
      : ['<no reveal-burst-badge element>'];
    expect({
      defaultQarenLogoImport,
      iconsSpecifiers: moduleSpecifiers(sf).filter((s) => s.includes('icons')),
      qarenLogoAttributes: qarenLogoAttributeNames(sf),
      badgeChildren,
    }).toEqual({
      defaultQarenLogoImport: true,
      iconsSpecifiers: [],
      qarenLogoAttributes: [['size']],
      badgeChildren: ['QarenLogo'],
    });
  });

  it('R6 [O2] src/icons/QaranIcon.tsx is deleted and the icons barrel no longer exports QaranIcon', () => {
    // UR14: the barrel is required here, never at file top.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const icons: Record<string, unknown> = require('../../src/icons');
    expect({
      fileExists: fs.existsSync(path.join(SRC, 'icons', 'QaranIcon.tsx')),
      barrelExportsQaranIcon: 'QaranIcon' in icons,
    }).toEqual({ fileExists: false, barrelExportsQaranIcon: false });
  });

  it('R7 [PIN] the icons barrel keeps every other export (Back, Close, Search, Bell, Settings, Plus, Scan, Link, Type, flipForRTL)', () => {
    // UR14: the barrel is required here, never at file top.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const icons: Record<string, unknown> = require('../../src/icons');
    const kept = [
      'BackIcon',
      'CloseIcon',
      'SearchIcon',
      'BellIcon',
      'SettingsIcon',
      'PlusIcon',
      'ScanIcon',
      'LinkIcon',
      'TypeIcon',
      'flipForRTL',
    ];
    expect({ undefinedExports: kept.filter((name) => icons[name] === undefined) }).toEqual({
      undefinedExports: [],
    });
  });

  it('R8 [source] no file under src/ (.ts/.tsx) or App.tsx contains QaranIcon, x1="14.2" or M22 22 L27 27', () => {
    const needles = ['QaranIcon', 'x1="14.2"', 'M22 22 L27 27'];
    const files = [...listSources(SRC), path.join(APP, 'App.tsx')];
    const hits = files
      .flatMap((file) => {
        const text = fs.readFileSync(file, 'utf8');
        return needles.filter((needle) => text.includes(needle)).map((needle) => `${relApp(file)}: ${needle}`);
      })
      .sort();
    expect(hits).toEqual([]);
  });

  it("R9 [O4] no src file says Q-ring / Q logo / Q-mark, and HistoryScreen no longer claims `alignItems: 'baseline'`", () => {
    const needles = ['Q-ring', 'Q logo', 'Q-mark'];
    const staleBrandWords = listSources(SRC)
      .flatMap((file) => {
        const text = fs.readFileSync(file, 'utf8');
        return needles.filter((needle) => text.includes(needle)).map((needle) => `${relApp(file)}: ${needle}`);
      })
      .sort();
    const history = fs.readFileSync(path.join(SRC, 'screens', 'HistoryScreen.tsx'), 'utf8');
    expect({
      staleBrandWords,
      historyClaimsBaseline: history.includes("`alignItems: 'baseline'`"),
    }).toEqual({ staleBrandWords: [], historyClaimsBaseline: false });
  });
});
