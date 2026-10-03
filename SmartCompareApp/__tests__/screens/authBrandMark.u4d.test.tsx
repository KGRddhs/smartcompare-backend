/**
 * U4d - the auth screens' brand block is the MYEZ mark, never a text logo
 * (issue #283; OQ2 ruled R-a, UR2).
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U4D_REVEAL_GLYPH_SPEC.md
 * section 5 rows A1-A5, as corrected (C3) and ruled (UR2, UR11).
 *
 * RED at base: A1, A2, A3, A4. PIN (green at base and after): A5.
 *
 * Rule (UR2): no auth screen draws the app name as a text logo; where a screen
 * has a brand block it is <QarenLogo size={56} />. Register (both states) and
 * ForgotPassword swap the Text for the mark; Login has no brand block and
 * stays unchanged.
 *
 * Mocks follow RegisterScreen.emailConfirmation.m18.test.tsx: `t` returns the
 * key, authService / api / expo-screen-capture are mocked. A1 and A3 FIRST
 * assert exactly one host whose type is 'Image', then read every prop from it
 * (C3a / UR11). AST checks use the installed `typescript`, as inAppMark.u4c
 * does. No snapshot assertion, no wall-clock dependency.
 */
import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';
import { act, render } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: jest.fn(),
}));

jest.mock('../../src/services/authService', () => ({
  register: jest.fn().mockResolvedValue({ success: false }),
  signInWithGoogle: jest.fn().mockResolvedValue({ success: false }),
  signInWithApple: jest.fn().mockResolvedValue({ success: false }),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(false),
  requestPasswordReset: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../../src/services/api', () => ({
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const RegisterScreen = require('../../src/screens/RegisterScreen').default;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const ForgotPasswordScreen = require('../../src/screens/ForgotPasswordScreen').default;

const APP = path.resolve(__dirname, '..', '..');
const SCREENS = path.join(APP, 'src', 'screens');

const mockNavigation: any = {
  navigate: jest.fn(),
  goBack: jest.fn(),
};

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

const imageHosts = (root: TestNode): TestNode[] => root.findAll((n) => n.type === 'Image');

/** What A1 / A3 read from the one mark Image (the R3 a11y props, the size, no tint). */
function markFacts(image: TestNode) {
  const labelledOrAccessible: string[] = [];
  for (let n: TestNode | null = image; n; n = n.parent) {
    if (typeof n.type !== 'string') continue;
    const label = `${String(n.type)}${n.props.testID ? `#${n.props.testID}` : ''}`;
    if (n.props.accessibilityLabel !== undefined) labelledOrAccessible.push(`${label} accessibilityLabel`);
    if (n.props.accessible === true) labelledOrAccessible.push(`${label} accessible`);
  }
  const style = flattenStyle(image.props.style);
  return {
    accessibilityElementsHidden: image.props.accessibilityElementsHidden,
    importantForAccessibility: image.props.importantForAccessibility,
    labelledOrAccessible,
    width: style.width,
    height: style.height,
    tintColorProp: 'tintColor' in image.props,
    tintColorInStyle: 'tintColor' in style,
  };
}

const HIDDEN_MARK_56 = {
  accessibilityElementsHidden: true,
  importantForAccessibility: 'no-hide-descendants',
  labelledOrAccessible: [],
  width: 56,
  height: 56,
  tintColorProp: false,
  tintColorInStyle: false,
};

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

function countAppNameCalls(sf: ts.SourceFile): number {
  let count = 0;
  walk(sf, (n) => {
    if (isAppNameCall(n)) count += 1;
  });
  return count;
}

/** The `size` of a <QarenLogo>: 'numeric:<n>', 'expression:<text>', 'string:<s>', 'missing' or 'empty'. */
function sizeOf(attrs: ts.JsxAttributes, sf: ts.SourceFile): string {
  const size = attrs.properties.find(
    (p): p is ts.JsxAttribute => ts.isJsxAttribute(p) && p.name.getText(sf) === 'size'
  );
  if (!size || !size.initializer) return 'missing';
  if (ts.isStringLiteral(size.initializer)) return `string:${size.initializer.text}`;
  const expr = ts.isJsxExpression(size.initializer) ? size.initializer.expression : undefined;
  if (!expr) return 'empty';
  return ts.isNumericLiteral(expr) ? `numeric:${expr.text}` : `expression:${expr.getText(sf)}`;
}

/** The `style={...}` text of the JSX element that directly contains `el`, or a marker. */
function parentStyle(el: ts.Node, sf: ts.SourceFile): string {
  const container = el.parent;
  if (!container || !ts.isJsxElement(container)) return '<not a JSX element child>';
  const style = container.openingElement.attributes.properties.find(
    (p): p is ts.JsxAttribute => ts.isJsxAttribute(p) && p.name.getText(sf) === 'style'
  );
  if (!style || !style.initializer) return '<no style>';
  if (ts.isJsxExpression(style.initializer) && style.initializer.expression) {
    return style.initializer.expression.getText(sf);
  }
  return style.initializer.getText(sf);
}

/** Every <QarenLogo> of a file: its size and the style of the element it sits in. */
function qarenLogos(sf: ts.SourceFile): { size: string; parentStyle: string }[] {
  const out: { size: string; parentStyle: string }[] = [];
  walk(sf, (n) => {
    if (ts.isJsxSelfClosingElement(n) && n.tagName.getText(sf) === 'QarenLogo') {
      out.push({ size: sizeOf(n.attributes, sf), parentStyle: parentStyle(n, sf) });
    } else if (ts.isJsxElement(n) && n.openingElement.tagName.getText(sf) === 'QarenLogo') {
      out.push({ size: sizeOf(n.openingElement.attributes, sf), parentStyle: parentStyle(n, sf) });
    }
  });
  return out;
}

/** True when the file default-imports `QarenLogo` from '../components/QarenLogo'. */
function defaultImportsQarenLogo(sf: ts.SourceFile): boolean {
  return sf.statements.some(
    (s) =>
      ts.isImportDeclaration(s) &&
      ts.isStringLiteral(s.moduleSpecifier) &&
      s.moduleSpecifier.text === '../components/QarenLogo' &&
      s.importClause?.name?.text === 'QarenLogo'
  );
}

/** The property names of every object passed to StyleSheet.create(...) in the file. */
function styleSheetKeys(sf: ts.SourceFile): string[] {
  const out: string[] = [];
  walk(sf, (n) => {
    if (
      ts.isCallExpression(n) &&
      n.expression.getText(sf) === 'StyleSheet.create' &&
      n.arguments[0] &&
      ts.isObjectLiteralExpression(n.arguments[0])
    ) {
      for (const p of n.arguments[0].properties) if (p.name) out.push(p.name.getText(sf));
    }
  });
  return out;
}

function authScreenFacts(file: string) {
  const sf = parse(file);
  return {
    appNameCalls: countAppNameCalls(sf),
    defaultQarenLogoImport: defaultImportsQarenLogo(sf),
    qarenLogos: qarenLogos(sf),
    logoStyleDefined: styleSheetKeys(sf).includes('logo'),
  };
}

const MARK_IN_HEADER = { size: 'numeric:56', parentStyle: 'styles.header' };

beforeEach(() => {
  jest.clearAllMocks();
});

describe('U4d auth brand mark - Register and ForgotPassword show the mark, Login unchanged', () => {
  it("A1 Register (form): one hidden 56 x 56 mark Image, untinted; no 'app.name' text; the tagline is kept", async () => {
    const r = render(
      <RegisterScreen navigation={mockNavigation} route={{ params: undefined }} onRegisterSuccess={jest.fn()} />
    );
    // Flush the isAppleSignInAvailable() promise the screen awaits on mount.
    await act(async () => {});
    const images = imageHosts(r.UNSAFE_root as unknown as TestNode);
    // C3a: exactly one Image host first; every prop is read from it.
    expect({ imageHosts: images.length }).toEqual({ imageHosts: 1 });
    expect(markFacts(images[0])).toEqual(HIDDEN_MARK_56);
    expect({
      appNameText: r.queryAllByText('app.name').length,
      taglineText: r.queryAllByText('splash.tagline').length,
    }).toEqual({ appNameText: 0, taglineText: 1 });
  });

  it("A2 [AST] RegisterScreen.tsx: 0 t('app.name'), exactly 2 <QarenLogo size={56} /> each inside styles.header, no logo style", () => {
    expect(authScreenFacts(path.join(SCREENS, 'RegisterScreen.tsx'))).toEqual({
      appNameCalls: 0,
      defaultQarenLogoImport: true,
      qarenLogos: [MARK_IN_HEADER, MARK_IN_HEADER],
      logoStyleDefined: false,
    });
  });

  it("A3 ForgotPassword: one hidden 56 x 56 mark Image, untinted; no 'app.name' text; the reset title still renders", () => {
    const r = render(<ForgotPasswordScreen navigation={mockNavigation} />);
    const images = imageHosts(r.UNSAFE_root as unknown as TestNode);
    // C3a: exactly one Image host first; every prop is read from it.
    expect({ imageHosts: images.length }).toEqual({ imageHosts: 1 });
    expect(markFacts(images[0])).toEqual(HIDDEN_MARK_56);
    expect({
      appNameText: r.queryAllByText('app.name').length,
      resetPasswordAtLeastOnce: r.getAllByText('auth.resetPassword').length >= 1,
    }).toEqual({ appNameText: 0, resetPasswordAtLeastOnce: true });
  });

  it("A4 [AST] ForgotPasswordScreen.tsx: 0 t('app.name'), exactly 1 <QarenLogo size={56} /> inside styles.header, no logo style, default import", () => {
    expect(authScreenFacts(path.join(SCREENS, 'ForgotPasswordScreen.tsx'))).toEqual({
      appNameCalls: 0,
      defaultQarenLogoImport: true,
      qarenLogos: [MARK_IN_HEADER],
      logoStyleDefined: false,
    });
  });

  it("A5 [PIN] [AST] LoginScreen.tsx has no <QarenLogo> and no t('app.name') (Login unchanged under R-a)", () => {
    const facts = authScreenFacts(path.join(SCREENS, 'LoginScreen.tsx'));
    expect({ qarenLogos: facts.qarenLogos, appNameCalls: facts.appNameCalls }).toEqual({
      qarenLogos: [],
      appNameCalls: 0,
    });
  });
});
