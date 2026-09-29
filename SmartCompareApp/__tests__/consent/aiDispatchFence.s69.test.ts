/**
 * S69 U3 — dispatch-site fence: every path that sends what the user enters to
 * OpenAI (or opens the camera / photo picker that feeds such a path) sits
 * behind the one-time AI-processing consent gate, `withAiConsent(...)`.
 *
 * Source-level: a TypeScript AST walk over App.tsx and src/ (tests and mocks
 * excluded). It enumerates
 *   - calls to streamComparison / compareTextPair / identifyFromImages
 *     (services/api.ts: GET /text/compare, /text/compare/stream,
 *     POST /text/compare, POST /image/identify);
 *   - every string literal naming an OpenAI-bound backend route
 *     (/text/compare, /text/quick, /text/parse, /text/prices, /url/compare,
 *     /url/extract, /image/identify), e.g. HomeScreen's
 *     api.post('/api/v1/url/compare');
 *   - the camera + photo-picker entries: the 'ScanCamera' route literal (any
 *     navigate / push / replace), `vision_products` route params (Results turns
 *     them into identifyFromImages), launchImageLibraryAsync /
 *     launchCameraAsync / takePictureAsync, and camera / library permission
 *     requests (the second element of useCameraPermissions(), and
 *     request{Camera,MediaLibrary}PermissionsAsync).
 *
 * Each site is classified:
 *   gated     — lexically inside a function passed to withAiConsent(...), or
 *               inside a named function whose EVERY reference in the file is
 *               itself gated (HomeScreen.runTextCompare is only ever called as
 *               withAiConsent(() => runTextCompare(a, b)));
 *   impl:<fn> — the request itself, inside api.ts's dispatch function <fn>
 *               (its callers are the sites that must be gated);
 *   ungated   — anything else.
 *
 * The inventory is pinned EXACTLY. A new dispatch path anywhere, or a
 * HomeScreen path that slips outside withAiConsent, changes it and reddens CI.
 * The pinned `ungated` sites are reachable only through gated entries, and
 * the parts of that claim that live in source are asserted below:
 *   - ScanCameraScreen (shutter, gallery, its own permission pad, its two
 *     vision_products navigations) is reached only through the 'ScanCamera'
 *     route literal — every one of which is gated — and the deep-link config
 *     (src/navigation/linking.ts) has no ScanCamera entry;
 *   - ResultsScreen's identifyFromImages runs only for
 *     route.params.vision_products, produced only by gated HomeScreen code and
 *     by ScanCameraScreen; the Results deep link carries comparison_id only.
 *
 * If this test goes red on purpose (a new dispatch path): gate the new path
 * with withAiConsent and re-pin EXPECTED here — never pin a new `ungated`
 * site without a reason line proving it is reachable only after consent.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';

const APP = path.join(__dirname, '..', '..');
const HOME = 'src/screens/HomeScreen.tsx';
const SCAN = 'src/screens/ScanCameraScreen.tsx';
const API = 'src/services/api.ts';
const LINKING = 'src/navigation/linking.ts';

const DISPATCH_CALLS = new Set(['streamComparison', 'compareTextPair', 'identifyFromImages']);
const CAMERA_CALLS = new Set([
  'launchImageLibraryAsync',
  'launchCameraAsync',
  'takePictureAsync',
  'requestCameraPermissionsAsync',
  'requestMediaLibraryPermissionsAsync',
]);
const OPENAI_ROUTES = [
  '/text/compare',
  '/text/quick',
  '/text/parse',
  '/text/prices',
  '/url/compare',
  '/url/extract',
  '/image/identify',
];

interface Site {
  file: string;
  kind: string;
  context: string;
  line: number;
}

function sourceFiles(): string[] {
  const out = [path.join(APP, 'App.tsx')];
  const walk = (dir: string) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (e.name !== '__tests__' && e.name !== '__mocks__') walk(p);
      } else if (/\.tsx?$/.test(e.name) && !/\.d\.ts$/.test(e.name) && !/\.test\.tsx?$/.test(e.name)) {
        out.push(p);
      }
    }
  };
  walk(path.join(APP, 'src'));
  return out;
}

const rel = (p: string) => path.relative(APP, p).split(path.sep).join('/');

function parse(file: string): ts.SourceFile {
  return ts.createSourceFile(
    file,
    fs.readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true,
    file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
}

function calleeName(call: ts.CallExpression): string | undefined {
  const e = call.expression;
  if (ts.isIdentifier(e)) return e.text;
  if (ts.isPropertyAccessExpression(e)) return e.name.text;
  return undefined;
}

function isFunctionLike(n: ts.Node): boolean {
  return (
    ts.isArrowFunction(n) ||
    ts.isFunctionExpression(n) ||
    ts.isFunctionDeclaration(n) ||
    ts.isMethodDeclaration(n)
  );
}

/** `function X`, `const X = <fn>` or `const X = useCallback(<fn>, deps)`. */
function boundName(fn: ts.Node): ts.Identifier | undefined {
  if (ts.isFunctionDeclaration(fn)) return fn.name;
  let holder: ts.Node = fn;
  const parent = fn.parent;
  if (
    parent &&
    ts.isCallExpression(parent) &&
    calleeName(parent) === 'useCallback' &&
    parent.arguments[0] === fn
  ) {
    holder = parent;
  }
  const decl = holder.parent;
  if (decl && ts.isVariableDeclaration(decl) && decl.initializer === holder && ts.isIdentifier(decl.name)) {
    return decl.name;
  }
  return undefined;
}

/** A value use of an identifier (not a declaration, property name or import). */
function isReference(id: ts.Identifier): boolean {
  const p = id.parent;
  if (ts.isPropertyAccessExpression(p) && p.name === id) return false;
  if (
    (ts.isPropertyAssignment(p) ||
      ts.isPropertySignature(p) ||
      ts.isPropertyDeclaration(p) ||
      ts.isMethodDeclaration(p)) &&
    p.name === id
  ) {
    return false;
  }
  if (ts.isJsxAttribute(p) && p.name === id) return false;
  if (
    (ts.isVariableDeclaration(p) || ts.isFunctionDeclaration(p) || ts.isParameter(p)) &&
    p.name === id
  ) {
    return false;
  }
  if (ts.isBindingElement(p) && (p.name === id || p.propertyName === id)) return false;
  if (ts.isImportSpecifier(p) || ts.isImportClause(p) || ts.isExportSpecifier(p)) return false;
  return true;
}

function referencesOf(sf: ts.SourceFile, decl: ts.Identifier): ts.Identifier[] {
  const out: ts.Identifier[] = [];
  const visit = (n: ts.Node) => {
    if (ts.isIdentifier(n) && n !== decl && n.text === decl.text && isReference(n)) out.push(n);
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}

function isGated(sf: ts.SourceFile, node: ts.Node, seen: ReadonlySet<string> = new Set()): boolean {
  let child: ts.Node = node;
  for (let cur: ts.Node | undefined = node.parent; cur; child = cur, cur = cur.parent) {
    if (
      ts.isCallExpression(cur) &&
      ts.isIdentifier(cur.expression) &&
      cur.expression.text === 'withAiConsent' &&
      cur.arguments.some((a) => a === child)
    ) {
      return true;
    }
    if (isFunctionLike(cur)) {
      const name = boundName(cur);
      if (!name) continue; // an anonymous function: its lexical context decides
      if (seen.has(name.text)) return false;
      const next = new Set(seen);
      next.add(name.text);
      const refs = referencesOf(sf, name);
      return refs.length > 0 && refs.every((r) => isGated(sf, r, next));
    }
  }
  return false;
}

/** The outermost function declaration around `node` (api.ts dispatch functions). */
function outermostFunctionName(node: ts.Node): string | undefined {
  let name: string | undefined;
  for (let cur: ts.Node | undefined = node.parent; cur; cur = cur.parent) {
    if (ts.isFunctionDeclaration(cur) && cur.name) name = cur.name.text;
  }
  return name;
}

/** `const [permission, requestPermission] = useCameraPermissions()` -> requestPermission. */
function cameraPermissionBindings(sf: ts.SourceFile): ts.Identifier[] {
  const out: ts.Identifier[] = [];
  const visit = (n: ts.Node) => {
    if (
      ts.isVariableDeclaration(n) &&
      ts.isArrayBindingPattern(n.name) &&
      n.initializer &&
      ts.isCallExpression(n.initializer) &&
      calleeName(n.initializer) === 'useCameraPermissions'
    ) {
      const el = n.name.elements[1];
      if (el && ts.isBindingElement(el) && ts.isIdentifier(el.name)) out.push(el.name);
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}

function collect(file: string): Site[] {
  const sf = parse(file);
  const f = rel(file);
  const sites: Site[] = [];
  const add = (node: ts.Node, kind: string) => {
    let context: string;
    const impl = f === API ? outermostFunctionName(node) : undefined;
    if (kind.startsWith('endpoint:') && impl && DISPATCH_CALLS.has(impl)) context = `impl:${impl}`;
    else context = isGated(sf, node) ? 'gated' : 'ungated';
    const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
    sites.push({ file: f, kind, context, line });
  };
  const visit = (n: ts.Node) => {
    if (ts.isCallExpression(n)) {
      const name = calleeName(n);
      if (name && (DISPATCH_CALLS.has(name) || CAMERA_CALLS.has(name))) add(n, `call:${name}`);
    }
    if (
      ts.isStringLiteral(n) ||
      ts.isNoSubstitutionTemplateLiteral(n) ||
      ts.isTemplateHead(n) ||
      ts.isTemplateMiddle(n) ||
      ts.isTemplateTail(n)
    ) {
      const parent = n.parent;
      const inTypeOrImport =
        !!parent && (ts.isLiteralTypeNode(parent) || ts.isImportDeclaration(parent));
      if (!inTypeOrImport) {
        for (const r of OPENAI_ROUTES) if (n.text.includes(r)) add(n, `endpoint:${r}`);
        if (n.text === 'ScanCamera') {
          add(n, parent && ts.isJsxAttribute(parent) ? 'register:ScanCamera' : 'route:ScanCamera');
        }
      }
    }
    if (
      (ts.isPropertyAssignment(n) || ts.isShorthandPropertyAssignment(n)) &&
      (ts.isIdentifier(n.name) || ts.isStringLiteral(n.name)) &&
      n.name.text === 'vision_products'
    ) {
      add(n, 'param:vision_products');
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  for (const b of cameraPermissionBindings(sf)) {
    for (const r of referencesOf(sf, b)) add(r, 'camera-permission');
  }
  return sites;
}

const SITES: Site[] = sourceFiles().flatMap(collect);
const summary = (s: Site) => `${s.file} | ${s.kind} | ${s.context}`;

/**
 * The pinned inventory (order-free). Every HomeScreen row is `gated`.
 * Reasons for the non-gated rows:
 *   api.ts impl:*       — the requests themselves; their callers are pinned.
 *   App.tsx register    — the Stack.Screen registration, not a navigation.
 *   ScanCameraScreen    — reached only via the gated 'ScanCamera' literals.
 *   ResultsScreen       — identifyFromImages runs only for vision_products.
 */
const EXPECTED = [
  // services/api.ts — the dispatch functions (their request URLs)
  `${API} | endpoint:/image/identify | impl:identifyFromImages`,
  `${API} | endpoint:/text/compare | impl:streamComparison`,
  `${API} | endpoint:/text/compare | impl:streamComparison`,
  `${API} | endpoint:/text/compare | impl:compareTextPair`,
  // HomeScreen — every entry behind withAiConsent
  `${HOME} | call:streamComparison | gated`,
  `${HOME} | endpoint:/url/compare | gated`,
  `${HOME} | call:launchImageLibraryAsync | gated`,
  `${HOME} | param:vision_products | gated`,
  `${HOME} | route:ScanCamera | gated`,
  `${HOME} | route:ScanCamera | gated`,
  `${HOME} | camera-permission | gated`,
  // App.tsx — screen registration only
  `App.tsx | register:ScanCamera | ungated`,
  // ScanCameraScreen — reachable only through the gated route literals above
  `${SCAN} | call:takePictureAsync | ungated`,
  `${SCAN} | call:launchImageLibraryAsync | ungated`,
  `${SCAN} | call:launchImageLibraryAsync | ungated`,
  `${SCAN} | param:vision_products | ungated`,
  `${SCAN} | param:vision_products | ungated`,
  `${SCAN} | camera-permission | ungated`,
  // ResultsScreen — the camera identify request, driven by vision_products only
  'src/screens/ResultsScreen.tsx | call:identifyFromImages | ungated',
];

describe('S69 U3 — OpenAI dispatch sites are gated by withAiConsent', () => {
  it('the dispatch-site inventory over App.tsx + src/ is exactly the pinned one', () => {
    expect(SITES.map(summary).sort()).toEqual([...EXPECTED].sort());
  });

  it('every HomeScreen dispatch / camera / picker site sits inside withAiConsent', () => {
    const home = SITES.filter((s) => s.file === HOME);
    expect(home.length).toBeGreaterThanOrEqual(7);
    expect(home.filter((s) => s.context !== 'gated').map((s) => `${s.kind} @ line ${s.line}`)).toEqual([]);
  });

  it('every ScanCamera route literal, and every vision_products producer outside ScanCameraScreen, is gated', () => {
    const routes = SITES.filter((s) => s.kind === 'route:ScanCamera');
    expect(routes.length).toBeGreaterThan(0);
    const offenders = SITES.filter(
      (s) =>
        (s.kind === 'route:ScanCamera' || (s.kind === 'param:vision_products' && s.file !== SCAN)) &&
        s.context !== 'gated',
    ).map((s) => `${s.file} ${s.kind} @ line ${s.line}`);
    expect(offenders).toEqual([]);
  });

  it('the deep-link config opens neither ScanCamera nor a vision_products compare', () => {
    const sf = parse(path.join(APP, LINKING));
    const names: string[] = [];
    const visit = (n: ts.Node) => {
      if (ts.isIdentifier(n) || ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) {
        names.push(n.text);
      }
      ts.forEachChild(n, visit);
    };
    visit(sf);
    expect(names).toContain('Results'); // non-vacuous: the config was read
    expect(names.filter((t) => /ScanCamera|vision_products/.test(t))).toEqual([]);
  });

  it('the withAiConsent the fence trusts is the useAiConsentGate() gate from services/aiConsent, declared once', () => {
    const gatedFiles = Array.from(new Set(SITES.filter((s) => s.context === 'gated').map((s) => s.file)));
    expect(gatedFiles).toEqual([HOME]);
    for (const f of gatedFiles) {
      const sf = parse(path.join(APP, f));
      let importsGate = false;
      const decls: ts.Node[] = [];
      const visit = (n: ts.Node) => {
        if (
          ts.isImportDeclaration(n) &&
          ts.isStringLiteral(n.moduleSpecifier) &&
          /(^|\/)services\/aiConsent$/.test(n.moduleSpecifier.text) &&
          n.importClause?.namedBindings &&
          ts.isNamedImports(n.importClause.namedBindings)
        ) {
          importsGate =
            importsGate ||
            n.importClause.namedBindings.elements.some(
              (el) => el.name.text === 'useAiConsentGate' && !el.propertyName,
            );
        }
        if (ts.isIdentifier(n) && n.text === 'withAiConsent' && !isReference(n)) {
          const p = n.parent;
          const isName =
            ((ts.isVariableDeclaration(p) ||
              ts.isFunctionDeclaration(p) ||
              ts.isParameter(p) ||
              ts.isBindingElement(p)) &&
              p.name === n) ||
            ts.isImportSpecifier(p);
          if (isName) decls.push(p);
        }
        ts.forEachChild(n, visit);
      };
      visit(sf);
      expect({ f, importsGate }).toEqual({ f, importsGate: true });
      expect({ f, declarations: decls.length }).toEqual({ f, declarations: 1 });
      const d = decls[0];
      const fromGate =
        ts.isBindingElement(d) &&
        (!d.propertyName || (ts.isIdentifier(d.propertyName) && d.propertyName.text === 'withAiConsent')) &&
        ts.isObjectBindingPattern(d.parent) &&
        ts.isVariableDeclaration(d.parent.parent) &&
        !!d.parent.parent.initializer &&
        ts.isCallExpression(d.parent.parent.initializer) &&
        calleeName(d.parent.parent.initializer) === 'useAiConsentGate';
      expect({ f, fromGate }).toEqual({ f, fromGate: true });
    }
  });
});
