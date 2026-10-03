/**
 * QarenLogo — the in-app MYEZ mark (session 71, unit U4c).
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md
 * §3 R3/R4 and §5 rows A1-A8, as corrected (correction 2) and ruled (UR11).
 *
 * The component keeps its path and its `export default function QarenLogo`
 * but stops drawing the old Q-ring Svg: it renders exactly ONE React Native
 * `Image` of the bundled MYEZ mark PNG (rendered by
 * scripts/render_myez_icons.py), hidden from accessibility exactly as the
 * Svg was, never tinted, never faded.
 *
 * Binding (correction 2): A2-A7 first assert exactly one host whose type is
 * 'Image' and read every prop from THAT host. The a11y-hidden helper is used
 * only in A1, to show the hidden host is the Image and not an Svg.
 *
 * jest maps every `.png` to __mocks__/fileStub.ts, so `require` of ANY png
 * path (even a missing one) returns the same stub object (spec §2f probe).
 * A7 is therefore a sanity check only; the real source file is pinned by the
 * AST test A8 and by the asset / manifest tests in
 * __tests__/brand/inAppMark.u4c.test.ts.
 */
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';
import React from 'react';
import { render } from '@testing-library/react-native';
import QarenLogo from '../../src/components/QarenLogo';

/**
 * Local structural type for a test-renderer node: the repo installs no
 * @types/react-test-renderer, so RNTL's `UNSAFE_root` is typed `any`.
 */
type TestNode = {
  type: unknown;
  props: Record<string, any>;
  parent: TestNode | null;
  findAll: (predicate: (node: TestNode) => boolean) => TestNode[];
};

const QAREN_LOGO_TSX = path.resolve(__dirname, '..', '..', 'src', 'components', 'QarenLogo.tsx');
const MARK_REQUIRE_ARG = '../../assets/brand/myez-mark.png';
const SVG_HOST_TYPES = new Set(['Svg', 'Circle', 'Path', 'G']);

type Style = Record<string, unknown>;

/** Deep StyleSheet.flatten (the repo mock flattens one array level only). */
function flattenStyle(style: unknown): Style {
  if (Array.isArray(style)) {
    return style.reduce<Style>((acc, s) => ({ ...acc, ...flattenStyle(s) }), {});
  }
  if (style && typeof style === 'object') return { ...(style as Style) };
  return {};
}

function hostImages(root: TestNode): TestNode[] {
  return root.findAll((n) => n.type === 'Image');
}

/** Correction 2: exactly one host Image, then every prop is read from it. */
function theMarkImage(root: TestNode): TestNode {
  const images = hostImages(root);
  expect(images).toHaveLength(1);
  return images[0];
}

describe('QarenLogo — the MYEZ mark (U4c)', () => {
  it('A1 renders exactly one host Image and no Svg / Circle / Path / G host', () => {
    const root: TestNode = render(<QarenLogo />).UNSAFE_root;
    const svgParts = root
      .findAll((n) => typeof n.type === 'string' && SVG_HOST_TYPES.has(n.type))
      .map((n) => n.type);
    // The a11y helper of spec §5, used only here: the hidden host must be the
    // Image, never an Svg.
    const hiddenHosts = root
      .findAll((n) => typeof n.type === 'string' && n.props.accessibilityElementsHidden === true)
      .map((n) => n.type);
    expect({ images: hostImages(root).length, svgParts, hiddenHosts }).toEqual({
      images: 1,
      svgParts: [],
      hiddenHosts: ['Image'],
    });
  });

  it('A2 size={48} gives the Image style { width: 48, height: 48 }', () => {
    const { UNSAFE_root } = render(<QarenLogo size={48} />);
    const image = theMarkImage(UNSAFE_root);
    expect(flattenStyle(image.props.style)).toEqual({ width: 48, height: 48 });
  });

  it('A3 the default size is 32: style { width: 32, height: 32 }', () => {
    const { UNSAFE_root } = render(<QarenLogo />);
    const image = theMarkImage(UNSAFE_root);
    expect(flattenStyle(image.props.style)).toEqual({ width: 32, height: 32 });
  });

  it('A4 resizeMode is "contain" and fadeDuration is 0 (R4: no Android fade)', () => {
    const { UNSAFE_root } = render(<QarenLogo />);
    const image = theMarkImage(UNSAFE_root);
    expect({
      resizeMode: image.props.resizeMode,
      fadeDuration: image.props.fadeDuration,
    }).toEqual({ resizeMode: 'contain', fadeDuration: 0 });
  });

  it('A5 the mark is hidden from accessibility exactly as before (no label, not accessible)', () => {
    const { UNSAFE_root } = render(<QarenLogo />);
    const image = theMarkImage(UNSAFE_root);
    expect({
      accessibilityElementsHidden: image.props.accessibilityElementsHidden,
      importantForAccessibility: image.props.importantForAccessibility,
      hasAccessibilityLabel: 'accessibilityLabel' in image.props,
      accessibleIsTrue: image.props.accessible === true,
    }).toEqual({
      accessibilityElementsHidden: true,
      importantForAccessibility: 'no-hide-descendants',
      hasAccessibilityLabel: false,
      accessibleIsTrue: false,
    });
  });

  it('A6 the mark is never tinted: no tintColor prop and no tintColor in the flattened style', () => {
    const { UNSAFE_root } = render(<QarenLogo />);
    const image = theMarkImage(UNSAFE_root);
    expect({
      tintColorProp: 'tintColor' in image.props,
      tintColorStyle: 'tintColor' in flattenStyle(image.props.style),
    }).toEqual({ tintColorProp: false, tintColorStyle: false });
  });

  it('A7 source is the bundled mark (sanity only: every png maps to one jest stub)', () => {
    const { UNSAFE_root } = render(<QarenLogo />);
    const image = theMarkImage(UNSAFE_root);
    // Path relative to __tests__/components/ (spec §5 A7). The expo eslint
    // config allows a `require` of a .png without a disable comment (§2g).
    const stub = require('../../assets/brand/myez-mark.png');
    expect(image.props.source).toBe(stub);
  });

  it('A8 [AST] QarenLogo.tsx: one module-scope require of the mark PNG, no svg / expo-image, no color prop', () => {
    const text = fs.readFileSync(QAREN_LOGO_TSX, 'utf8');
    const sf = ts.createSourceFile(QAREN_LOGO_TSX, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

    const requireCalls: ts.CallExpression[] = [];
    const moduleSpecifiers: string[] = [];
    let propsDeclared = false;
    let propsHasColor = false;
    let defaultExportFunction: string | null = null;

    const hasColorMember = (node: ts.Node): boolean => {
      let found = false;
      const walk = (n: ts.Node): void => {
        if (
          (ts.isPropertySignature(n) || ts.isPropertyDeclaration(n)) &&
          n.name.getText(sf) === 'color'
        ) {
          found = true;
        }
        ts.forEachChild(n, walk);
      };
      walk(node);
      return found;
    };

    const visit = (node: ts.Node): void => {
      if (ts.isCallExpression(node)) {
        const callee = node.expression;
        const arg = node.arguments[0];
        if (ts.isIdentifier(callee) && callee.text === 'require') {
          requireCalls.push(node);
          if (arg && ts.isStringLiteralLike(arg)) moduleSpecifiers.push(arg.text);
        } else if (callee.kind === ts.SyntaxKind.ImportKeyword && arg && ts.isStringLiteralLike(arg)) {
          moduleSpecifiers.push(arg.text);
        }
      }
      if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) {
        moduleSpecifiers.push(node.moduleSpecifier.text);
      }
      if (
        ts.isImportEqualsDeclaration(node) &&
        ts.isExternalModuleReference(node.moduleReference) &&
        ts.isStringLiteral(node.moduleReference.expression)
      ) {
        moduleSpecifiers.push(node.moduleReference.expression.text);
      }
      if ((ts.isTypeAliasDeclaration(node) || ts.isInterfaceDeclaration(node)) && node.name.text === 'Props') {
        propsDeclared = true;
        if (hasColorMember(node)) propsHasColor = true;
      }
      if (
        ts.isFunctionDeclaration(node) &&
        (ts.getCombinedModifierFlags(node) & ts.ModifierFlags.ExportDefault) === ts.ModifierFlags.ExportDefault
      ) {
        defaultExportFunction = node.name ? node.name.text : '<anonymous>';
      }
      ts.forEachChild(node, visit);
    };
    visit(sf);

    const argOf = (call: ts.CallExpression): string => {
      const arg = call.arguments[0];
      return arg && ts.isStringLiteralLike(arg) ? arg.text : '<not a string literal>';
    };
    const atModuleScope = (call: ts.CallExpression): boolean => {
      for (let n: ts.Node | undefined = call.parent; n; n = n.parent) {
        if (ts.isFunctionLike(n) || ts.isClassStaticBlockDeclaration(n)) return false;
      }
      return true;
    };
    const isBanned = (s: string): boolean =>
      s === 'react-native-svg' ||
      s.startsWith('react-native-svg/') ||
      s === 'expo-image' ||
      s.startsWith('expo-image/');

    expect({
      requireCount: requireCalls.length,
      requireArgs: requireCalls.map(argOf),
      requireTargetsExistOnDisk: requireCalls.map((c) =>
        fs.existsSync(path.resolve(path.dirname(QAREN_LOGO_TSX), argOf(c)))
      ),
      requiresAtModuleScope: requireCalls.map(atModuleScope),
      bannedImports: moduleSpecifiers.filter(isBanned),
      propsDeclared,
      propsHasColor,
      defaultExportFunction,
    }).toEqual({
      requireCount: 1,
      requireArgs: [MARK_REQUIRE_ARG],
      requireTargetsExistOnDisk: [true],
      requiresAtModuleScope: [true],
      bannedImports: [],
      propsDeclared: true,
      propsHasColor: false,
      defaultExportFunction: 'QarenLogo',
    });
  });
});
