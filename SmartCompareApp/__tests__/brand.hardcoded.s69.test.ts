/**
 * S69 U-R — brand rename Qaren -> MYEZ (ميّز): hard-coded source fence (T2).
 *
 * Spec: docs/investigations/2026-09-29-session-69-state/UR_RENAME_MYEZ_SPEC.md §3 T2,
 * as corrected by its spec review (C5, C11).
 *
 * Syntax-aware on purpose: a grep over src/ for "Qaren" hits ~40 comment
 * lines, `QarenLogo` import paths and the i18n KEY string
 * 'referrals.landing.openQaren' — none of which is copy. This fence reads the
 * TypeScript AST (installed `typescript`, same instrument as
 * __tests__/config/nativeBundle.w37.test.ts) and inspects only the nodes a
 * user can see: JSX text, string / template literals that are not module
 * specifiers, not i18n key arguments and not code-only JSX attributes.
 *
 * It covers BOTH scripts: the three Arabic «قارن» logo literals
 * (ForgotPasswordScreen, RegisterScreen x2) show Arabic to English users and
 * would slip past a Latin-only fence. The Arabic word boundary is explicit
 * (JS \b ignores Arabic letters) so «مقارنة» etc. never trip it.
 *
 * Addresses are not copy (ruling R-B / D14; S76 moved them to getmyez.com): `support@qaren.app`,
 * `https://qaren.app/…`, `qaren://…` are stripped before matching — but only
 * the address itself, so a `?subject=Qaren%20Support` mailto query (copy) is
 * still caught.
 */
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';

const SRC = path.resolve(__dirname, '..', 'src');

const ADDRESS_RE =
  /qaren:\/\/[\w/.-]*|[\w.+-]*@qaren\.app|(?:https?:\/\/)?(?:[\w-]+\.)*qaren\.app(?:\/[\w/.%-]*)?/gi;
const LATIN_BRAND = /Qaren/;
const ARABIC_BRAND = /(?<![؀-ۿ])[بلو]?قارن(?![؀-ۿ])/u;
// Dotted i18n key shape, e.g. 'referrals.landing.openQaren'.
const I18N_KEY_SHAPE = /^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$/;
const CODE_ONLY_JSX_ATTRS = new Set(['testID', 'nativeID', 'key']);

function listSources(dir: string, out: string[] = []): string[] {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) listSources(p, out);
    else if (/\.tsx?$/.test(e.name) && !/\.d\.ts$/.test(e.name)) out.push(p);
  }
  return out;
}

function isModuleSpecifier(node: ts.Node): boolean {
  const p = node.parent;
  if (!p) return false;
  if ((ts.isImportDeclaration(p) || ts.isExportDeclaration(p)) && p.moduleSpecifier === node) return true;
  if (ts.isExternalModuleReference(p)) return true;
  if (ts.isImportTypeNode(p.parent ?? p)) return true;
  if (ts.isCallExpression(p) && p.arguments[0] === node) {
    const callee = p.expression;
    if (callee.kind === ts.SyntaxKind.ImportKeyword) return true;
    if (ts.isIdentifier(callee) && callee.text === 'require') return true;
  }
  return false;
}

function isTranslationKeyArg(node: ts.Node): boolean {
  const p = node.parent;
  if (!p || !ts.isCallExpression(p) || p.arguments[0] !== node) return false;
  const callee = p.expression;
  const name = ts.isIdentifier(callee)
    ? callee.text
    : ts.isPropertyAccessExpression(callee)
      ? callee.name.text
      : '';
  return name === 't';
}

function isCodeOnlyJsxAttr(node: ts.Node): boolean {
  const p = node.parent;
  return !!p && ts.isJsxAttribute(p) && CODE_ONLY_JSX_ATTRS.has(p.name.getText());
}

type Hit = { where: string; text: string };

function scan(): Hit[] {
  const hits: Hit[] = [];
  for (const file of listSources(SRC)) {
    const src = fs.readFileSync(file, 'utf8');
    if (!/Qaren|قارن/.test(src)) continue;
    const sf = ts.createSourceFile(
      file,
      src,
      ts.ScriptTarget.Latest,
      true,
      file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
    );
    const visit = (node: ts.Node): void => {
      let text: string | null = null;
      if (ts.isJsxText(node)) {
        text = node.text;
      } else if (
        ts.isStringLiteral(node) ||
        ts.isNoSubstitutionTemplateLiteral(node) ||
        ts.isTemplateHead(node) ||
        ts.isTemplateMiddle(node) ||
        ts.isTemplateTail(node)
      ) {
        if (
          !isModuleSpecifier(node) &&
          !isTranslationKeyArg(node) &&
          !isCodeOnlyJsxAttr(node) &&
          !I18N_KEY_SHAPE.test(node.text)
        ) {
          text = node.text;
        }
      }
      if (text !== null) {
        const visible = text.replace(ADDRESS_RE, ' ');
        if (LATIN_BRAND.test(visible) || ARABIC_BRAND.test(visible)) {
          const { line } = sf.getLineAndCharacterOfPosition(node.getStart(sf));
          hits.push({
            where: `${path.relative(SRC, file).split(path.sep).join('/')}:${line + 1}`,
            text: text.trim(),
          });
        }
      }
      ts.forEachChild(node, visit);
    };
    visit(sf);
  }
  return hits;
}

describe('S69 U-R T2 — no hard-coded Qaren / قارن copy in src', () => {
  const hits = scan();

  it('no user-visible string literal or JSX text carries the old brand (Latin or Arabic)', () => {
    // Sanity: the scanner really walks the source tree.
    expect(listSources(SRC).length).toBeGreaterThan(100);
    // The i18n KEY name stays (a code identifier; only its catalog value changes).
    const landing = fs.readFileSync(path.join(SRC, 'screens', 'ReferralLandingScreen.tsx'), 'utf8');
    expect(landing.includes("'referrals.landing.openQaren'")).toBe(true);
    expect(hits).toEqual([]);
  });

  it('the support mailto keeps its address but its subject says MYEZ', () => {
    const src = fs.readFileSync(path.join(SRC, 'screens', 'ContactUsScreen.tsx'), 'utf8');
    // S76 DOMAIN-MYEZ: the address is support@getmyez.com (owner decision 2026-10-10), held in
    // ONE constant that the mailto template interpolates.
    const address = (src.match(/const SUPPORT_EMAIL = '([^']*)'/) ?? ['', ''])[1];
    expect(address).toBe('support@getmyez.com');
    const mailto = (src.match(/mailto:[^'"`\s]*/) ?? [''])[0].replace(/\$\{SUPPORT_EMAIL\}/, address);
    expect(mailto).toBe('mailto:support@getmyez.com?subject=MYEZ%20Support');
  });
});
