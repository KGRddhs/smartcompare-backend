/**
 * W4-14 A4 (`PO-CATEGORIES-I18N-12` residue) — the referral-expiry plural families
 * carry all six Arabic CLDR forms, so an Arabic reader never falls back to the
 * English string. Measured at the unit base 3985eaac with the real i18next under
 * ar: expiresInDays, expiresInHours and expiresInMinutes all render ENGLISH for
 * counts 0, 2, 3 and 11 (the families carry only _one/_other in ar.json). Zero call
 * sites in src today (latent), kept for the future bonus UI (ruling Q5).
 *
 * RED 16 = fails at the unit base. REAL i18next + REAL catalogs.
 */
import i18next from 'i18next';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';

const FAMILIES = [
  'referrals.bonus.expiresInDays',
  'referrals.bonus.expiresInHours',
  'referrals.bonus.expiresInMinutes',
];
const COUNTS = [0, 1, 2, 3, 11, 100];
const ASCII_LETTERS = /[A-Za-z]/;

function arT() {
  const inst = i18next.createInstance();
  inst.init({
    lng: 'ar',
    fallbackLng: 'en',
    resources: { en: { translation: en }, ar: { translation: ar } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  } as any);
  return inst.t.bind(inst) as any;
}

describe('W4-14 referral expiry plurals under lng=ar', () => {
  it('RED 16: referrals.bonus.expiresIn{Days,Hours,Minutes} never fall back to English for counts 0,1,2,3,11,100', () => {
    const t = arT();
    const english: string[] = [];
    for (const fam of FAMILIES) {
      for (const c of COUNTS) {
        const s: string = t(fam, { count: c });
        if (ASCII_LETTERS.test(s) || s === fam) english.push(`${fam}:${c}`);
      }
    }
    expect(english).toEqual([]);
  });

  // Ruling R2's two copy corrections are pinned by VALUE (RED 16 only proves "no
  // English fallback", so the rejected "Expires now" / AR "expires now" copy, which
  // reads as already expired, survived it - adversary mutant N13). The Arabic values
  // are written as \u escapes of the ruled text.
  const R2_ZERO: [string, string, string][] = [
    ['referrals.bonus.expiresInDays', 'Expires today',
      'تنتهي اليوم'],
    ['referrals.bonus.expiresInHours', 'Expires within the hour',
      'تنتهي خلال أقل من ساعة'],
    ['referrals.bonus.expiresInMinutes', 'Expires in under a minute',
      'تنتهي خلال أقل من دقيقة'],
  ];

  it('PIN (ruling R2): the _zero forms carry the ruled copy in both catalogs and ar renders it at count 0', () => {
    const t = arT();
    const enCat = en as unknown as Record<string, string>;
    const arCat = ar as unknown as Record<string, string>;
    for (const [fam, enZero, arZero] of R2_ZERO) {
      expect(enCat[`${fam}_zero`]).toBe(enZero);
      expect(arCat[`${fam}_zero`]).toBe(arZero);
      expect(t(fam, { count: 0 })).toBe(arZero);
    }
    // The rejected R2 copy never ships in either language.
    expect(Object.values(enCat).filter((v) => /^Expires now$/i.test(v))).toEqual([]);
  });

  // Fable pin (adversary r2 C3): the _two / _few / _many forms are pinned by VALUE too
  // (the R2 pin covered _zero only, so a wrong dual/plural copy survived). Arabic as
  // \u escapes of the shipped catalog text; _few/_many keep {{count}}.
  const R2_PLURALS: [string, string, string, string, string][] = [
    // family, EN _two, AR _two (count 2), AR _few (count 3), AR _many (count 11)
    ['referrals.bonus.expiresInDays', 'Expires in 2 days',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 \u064a\u0648\u0645\u064a\u0646',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u0623\u064a\u0627\u0645',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u064a\u0648\u0645\u064b\u0627'],
    ['referrals.bonus.expiresInHours', 'Expires in 2 hours',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 \u0633\u0627\u0639\u062a\u064a\u0646',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u0633\u0627\u0639\u0627\u062a',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u0633\u0627\u0639\u0629'],
    ['referrals.bonus.expiresInMinutes', 'Expires in 2 minutes',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 \u062f\u0642\u064a\u0642\u062a\u064a\u0646',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u062f\u0642\u0627\u0626\u0642',
      '\u062a\u0646\u062a\u0647\u064a \u062e\u0644\u0627\u0644 {{count}} \u062f\u0642\u064a\u0642\u0629'],
  ];

  it('PIN (Fable, adversary r2 C3): the _two/_few/_many forms carry the ruled copy and ar renders them at 2, 3 and 11', () => {
    const t = arT();
    const enCat = en as unknown as Record<string, string>;
    const arCat = ar as unknown as Record<string, string>;
    for (const [fam, enTwo, arTwo, arFew, arMany] of R2_PLURALS) {
      expect(enCat[`${fam}_two`]).toBe(enTwo);
      expect(arCat[`${fam}_two`]).toBe(arTwo);
      expect(arCat[`${fam}_few`]).toBe(arFew);
      expect(arCat[`${fam}_many`]).toBe(arMany);
      expect(t(fam, { count: 2 })).toBe(arTwo);
      expect(t(fam, { count: 3 })).toBe(arFew.replace('{{count}}', '3'));
      expect(t(fam, { count: 11 })).toBe(arMany.replace('{{count}}', '11'));
    }
  });
});
