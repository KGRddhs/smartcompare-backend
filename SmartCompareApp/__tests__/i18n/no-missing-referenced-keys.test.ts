/**
 * i18n referenced-key fence — M13-15.
 *
 * Walks every src/ .ts/.tsx file for literal `t('key')` / `t("key")` calls and
 * asserts each referenced key exists in en.json (plural-aware). Guards the
 * regression M13-15 fixed: 63 keys were referenced by screens but absent from
 * the catalog, so ~a third of that copy rendered each call site's English
 * `defaultValue` to Arabic users — invisible to `__tests__/i18n.test.ts`,
 * which only compares the EN/AR key SETS to each other, never to the code.
 *
 * Scope (matches the finding's reproduction): STATIC single/double-quoted keys
 * whose argument is complete — the closing quote is immediately followed by
 * ',' or ')'. This deliberately EXCLUDES:
 *   - template-literal keys, e.g. t(`results.spec.${f.key}`) — dynamic
 *     families resolved at runtime via `defaultValue`, not statically
 *     enumerable; and
 *   - string-concat prefixes, e.g. t('results.spec.' + key) — the quote is
 *     followed by '+', not ',' or ')'.
 * i18next plural forms are honoured: a key referenced with `{ count }` resolves
 * to key_one / key_other, so a base key counts as present when it OR any plural
 * suffix exists (e.g. referrals.bonus.expiresInDays -> _one/_other).
 */
import * as fs from 'fs';
import * as path from 'path';
import en from '../../src/i18n/en.json';

const SRC_DIR = path.resolve(__dirname, '../../src');
const enRecord = en as Record<string, string>;
const PLURAL_SUFFIXES = ['_zero', '_one', '_two', '_few', '_many', '_other'];

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else if (/\.(ts|tsx)$/.test(entry.name)) out.push(full);
  }
  return out;
}

/** Map of referenced key -> first src file that references it. */
function referencedKeys(): Map<string, string> {
  const re = /\bt\(\s*(['"])([^'"]+?)\1\s*[,)]/g;
  const found = new Map<string, string>();
  for (const file of walk(SRC_DIR)) {
    const src = fs.readFileSync(file, 'utf8');
    let m: RegExpExecArray | null;
    while ((m = re.exec(src)) !== null) {
      const key = m[2];
      if (!found.has(key)) found.set(key, path.relative(SRC_DIR, file).replace(/\\/g, '/'));
    }
  }
  return found;
}

function isPresent(key: string): boolean {
  if (Object.prototype.hasOwnProperty.call(enRecord, key)) return true;
  return PLURAL_SUFFIXES.some((s) =>
    Object.prototype.hasOwnProperty.call(enRecord, key + s)
  );
}

describe('i18n referenced-key fence — M13-15', () => {
  it('every literal t() key referenced in src/ exists in en.json', () => {
    const refs = referencedKeys();
    const missing: string[] = [];
    for (const [key, file] of refs) {
      if (!isPresent(key)) missing.push(`${key}  (first referenced in ${file})`);
    }
    // A non-empty list means a screen references a key the catalog lacks, so
    // Arabic users get its English defaultValue. Add the key to en.json AND
    // ar.json (i18n.test.ts enforces the two stay set-equal).
    expect(missing).toEqual([]);
  });

  it('extraction still matches real call sites (fence is not a silent no-op)', () => {
    // Guards a future refactor that breaks the extraction regex and turns
    // this fence green-by-accident. The app referenced 460 static keys when
    // this fence was written.
    expect(referencedKeys().size).toBeGreaterThan(300);
  });
});
