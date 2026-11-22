/**
 * INC-C1b RED -- strings (INC_C1B_UNIT_SPEC_V2.md section 9 and 10.6: rows
 * T1, T2, pin P-T1; ruling RU-10).
 *
 * The contract this file fixes for GREEN:
 *  - en.json / ar.json gain exactly two keys with the section 9 words, EN
 *    literal and AR decoded from the table's code points (T1):
 *      row 1 results.savedOn               "Saved on {{date}}"
 *      row 2 results.accordion.reviewsEach "Shown per product" (the primary
 *            words of RU-10; if the owner's read picks the alternative
 *            "For each product separately", row 2 moves with the catalogs).
 *  - Both keys exist non-empty in both catalogs (the control), carry no digit
 *    (ASCII, U+0660-0669, U+06F0-06F9), no time promise, no plural suffix,
 *    equal {{vars}} in EN and AR ({{date}} / none) and no .copy-policy.json
 *    hit (T2).
 *  - P-T1 (passes at base and after GREEN): equal key sets in EN and AR.
 *
 * Arabic is built from code points (String.fromCodePoint); this source stays
 * ASCII. F1: catalogs and the policy file only, no app import.
 */

import enCatalog from '../../src/i18n/en.json';
import arCatalog from '../../src/i18n/ar.json';
import policyFile from '../../src/i18n/.copy-policy.json';

const EN = enCatalog as unknown as Record<string, string>;
const AR = arCatalog as unknown as Record<string, string>;
const POLICY = policyFile as unknown as {
  banned_en?: { pattern: string; label: string }[];
  banned_ar?: { pattern: string; label: string }[];
  scary_vocab_en?: string[];
  scary_vocab_ar?: string[];
};

const u = (...cps: number[]) => String.fromCodePoint(...cps);

// Section 9 of the unit spec: [row, key, EN literal, AR from the code points, {{vars}}].
const ROWS: [number, string, string, string, string[]][] = [
  [
    1,
    'results.savedOn',
    'Saved on {{date}}',
    u(0x645, 0x62d, 0x641, 0x648, 0x638, 0x629, 0x20, 0x628, 0x62a, 0x627, 0x631, 0x64a, 0x62e, 0x20) +
      '{{date}}',
    ['date'],
  ],
  [
    2,
    'results.accordion.reviewsEach',
    'Shown per product',
    u(0x645, 0x639, 0x631, 0x648, 0x636, 0x629, 0x20, 0x644, 0x643, 0x644, 0x20, 0x645, 0x646, 0x62a, 0x62c),
    [],
  ],
];

const vars = (s: string) => [...s.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort();
const visibleCopy = (s: string) => s.replace(/\{\{[^}]+\}\}/g, '');

describe('INC-C1b strings (fail at base)', () => {
  it('T1 the two new keys equal the section 9 table (EN literal, AR decoded)', () => {
    const got: Record<string, unknown> = {};
    const want: Record<string, unknown> = {};
    for (const [n, key, en, ar] of ROWS) {
      got[`${n} ${key}`] = { en: EN[key], ar: AR[key] };
      want[`${n} ${key}`] = { en, ar };
    }
    expect(got).toEqual(want);
  });

  it('T2 both keys exist non-empty in both catalogs (control): no digit, no time promise, no plural suffix, equal vars, no copy-policy hit', () => {
    const present = ROWS.map(([n, key]) => ({
      n,
      key,
      en: typeof EN[key] === 'string' && EN[key].length > 0,
      ar: typeof AR[key] === 'string' && AR[key].length > 0,
    }));
    expect(present).toEqual(ROWS.map(([n, key]) => ({ n, key, en: true, ar: true })));

    const DIGIT = new RegExp('[0-9' + u(0x660) + '-' + u(0x669) + u(0x6f0) + '-' + u(0x6f9) + ']');
    const EN_TIME = /update|soon|shortly|next|minute|hour/i;
    const AR_TIME = [
      u(0x62a, 0x62d, 0x62f, 0x64a, 0x62b),
      u(0x642, 0x631, 0x64a, 0x628),
      u(0x628, 0x639, 0x62f, 0x20, 0x642, 0x644, 0x64a, 0x644),
    ];
    const PLURAL = /_(zero|one|two|few|many|other)$/;
    const ARABIC_LETTER = new RegExp('[' + u(0x621) + '-' + u(0x64a) + ']');
    const bannedEn = (POLICY.banned_en ?? []).map((e) => ({ re: new RegExp(e.pattern, 'i'), label: e.label }));
    const bannedAr = (POLICY.banned_ar ?? []).map((e) => ({ re: new RegExp(e.pattern), label: e.label }));
    const scaryEn = POLICY.scary_vocab_en ?? [];
    const scaryAr = POLICY.scary_vocab_ar ?? [];
    expect(bannedEn.length).toBeGreaterThan(0);
    expect(scaryAr.length).toBeGreaterThan(0);

    const hits: string[] = [];
    for (const [n, key, , , wantVars] of ROWS) {
      const en = String(EN[key]);
      const ar = String(AR[key]);
      if (PLURAL.test(key)) hits.push(`${n} ${key} plural suffix`);
      if (DIGIT.test(en)) hits.push(`${n} ${key} EN digit`);
      if (DIGIT.test(ar)) hits.push(`${n} ${key} AR digit`);
      if (EN_TIME.test(en)) hits.push(`${n} ${key} EN time word`);
      AR_TIME.forEach((w, i) => {
        if (ar.includes(w)) hits.push(`${n} ${key} AR time word ${i}`);
      });
      if (vars(en).join(',') !== wantVars.join(',')) hits.push(`${n} ${key} EN vars ${vars(en).join(',')}`);
      if (vars(ar).join(',') !== wantVars.join(',')) hits.push(`${n} ${key} AR vars ${vars(ar).join(',')}`);
      if (!ARABIC_LETTER.test(visibleCopy(ar))) hits.push(`${n} ${key} AR has no Arabic letter`);
      const ve = visibleCopy(en);
      const va = visibleCopy(ar);
      for (const b of bannedEn) if (b.re.test(ve)) hits.push(`${n} ${key} EN ${b.label}`);
      for (const w of scaryEn) if (ve.toLowerCase().includes(w.toLowerCase())) hits.push(`${n} ${key} EN ${w}`);
      for (const b of bannedAr) if (b.re.test(va)) hits.push(`${n} ${key} AR banned`);
      for (const w of scaryAr) if (va.includes(w)) hits.push(`${n} ${key} AR scary ${scaryAr.indexOf(w)}`);
    }
    expect(hits).toEqual([]);
  });
});

describe('INC-C1b strings pin (passes at base)', () => {
  it('P-T1 the EN and AR catalogs have equal key sets', () => {
    const enKeys = Object.keys(EN).sort();
    const arKeys = Object.keys(AR).sort();
    expect({
      enOnly: enKeys.filter((k) => !(k in AR)),
      arOnly: arKeys.filter((k) => !(k in EN)),
    }).toEqual({ enOnly: [], arOnly: [] });
  });
});
