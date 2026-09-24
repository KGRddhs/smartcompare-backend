/**
 * W3-11bcd — MB-I18N-RTL-14(c): plural-family fence.
 *
 * i18next treats a key whose last segment ends in a reserved plural suffix
 * (_zero/_one/_two/_few/_many/_other) as a member of a plural family. Two
 * failure modes are caught here:
 *   (i)  a LONE suffixed key — `results.valueMatch.cheaper_of_two` is not a
 *        dual form of anything, it is a name that happens to end in `_two`
 *        (base b63a8368: the only such key, in both catalogs). The fix
 *        renames it `cheaperOfTwo`.
 *   (ii) an INCOMPLETE family — Arabic needs all six forms; a missing one
 *        silently falls back (measured on i18next 26.1.0: ar
 *        `referrals.bonus.expiresInDays` count 0/2/3/11 renders the ENGLISH
 *        "Expires in N days").
 *
 * Rule (ii) also carries an explicit REQUIRED-FAMILIES list (spec R8(a)) so
 * it can never be vacuously green: the three `time.*` families are added by
 * this unit (RTL-08) and must be complete in ar and at least _one+_other in
 * en. The en-side clause for `history.hero.count` / `home.savings.count` is
 * a named forward guard (R8(c)) — green at base by design.
 */
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';

const SUFFIXES = ['_zero', '_one', '_two', '_few', '_many', '_other'] as const;

// Dead — zero callers in src/ (grep `expiresIn` outside src/i18n/ → none).
// i18next 26.1.0 falls back to ENGLISH for ar counts 0/2/3-10/11-99
// (measured). Owned by W3-11 14(b): delete or complete, then drop from here.
const ALLOWLIST_INCOMPLETE = new Set([
  'referrals.bonus.expiresInDays',
  'referrals.bonus.expiresInHours',
  'referrals.bonus.expiresInMinutes',
]);

const REQUIRED_FAMILIES = [
  'time.minutesAgo',
  'time.hoursAgo',
  'time.daysAgo',
  'history.hero.count',
  'home.savings.count',
];

type Catalog = Record<string, string>;

function families(catalog: Catalog): Map<string, string[]> {
  const out = new Map<string, string[]>();
  for (const key of Object.keys(catalog)) {
    const last = key.split('.').pop() ?? '';
    const suffix = SUFFIXES.find((s) => last.endsWith(s));
    if (!suffix) continue;
    const base = key.slice(0, key.length - suffix.length);
    out.set(base, [...(out.get(base) ?? []), suffix]);
  }
  return out;
}

const CATALOGS: Array<[string, Catalog]> = [
  ['en.json', en as Catalog],
  ['ar.json', ar as Catalog],
];

describe('W3-11 RTL-14(c) — plural families', () => {
  it.each(CATALOGS)('(i) %s has no LONE key ending in a reserved plural suffix', (_name, catalog) => {
    const lone = [...families(catalog)]
      .filter(([, members]) => members.length === 1)
      .map(([base, members]) => base + members[0]);
    expect(lone).toEqual([]);
  });

  it('(ii) families are complete: six forms in ar.json, at least _one + _other in en.json (REQUIRED list included)', () => {
    // One assertion over (a) every discovered multi-member family and (b)
    // the REQUIRED list — (a) alone is vacuously green at base (R8(a)).
    const arFam = families(ar as Catalog);
    const enFam = families(en as Catalog);
    const problems: string[] = [];
    for (const [base, members] of arFam) {
      if (members.length < 2 || ALLOWLIST_INCOMPLETE.has(base)) continue;
      const missing = SUFFIXES.filter((s) => !members.includes(s));
      if (missing.length) problems.push(`ar ${base} missing ${missing.join(',')}`);
    }
    for (const [base, members] of enFam) {
      if (members.length < 2) continue;
      const missing = (['_one', '_other'] as const).filter((s) => !members.includes(s));
      if (missing.length) problems.push(`en ${base} missing ${missing.join(',')}`);
    }
    for (const base of REQUIRED_FAMILIES) {
      const arMissing = SUFFIXES.filter((s) => !(arFam.get(base) ?? []).includes(s));
      if (arMissing.length) problems.push(`ar ${base} missing ${arMissing.join(',')}`);
      const enMembers = enFam.get(base) ?? [];
      const enMissing = (['_one', '_other'] as const).filter((s) => !enMembers.includes(s));
      if (enMissing.length) problems.push(`en ${base} missing ${enMissing.join(',')}`);
    }
    expect([...new Set(problems)]).toEqual([]);
  });
});
